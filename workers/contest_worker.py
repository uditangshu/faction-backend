"""Contest submission worker"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import UUID
from typing import Dict, Any, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.integrations.redis_client import get_redis, RedisService
from app.db.attempt_calls import create_attempt
from app.core.config import settings
from app.models.Basequestion import Question, QuestionType
from app.models.contest import Contest, ContestLeaderboard
from app.models.user import User
from app.models.linking import ContestQuestions
from sqlalchemy import select, func, desc

logger = logging.getLogger(__name__)


class ContestSubmissionWorker:
    """Worker that processes contest submissions from Redis queue"""

    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.redis_service: RedisService | None = None
        self.running = False
        self.queue_name_pattern = "contest:submissions:*"
        self.poll_interval = 1  # seconds
        self.blocking_timeout = 5  # seconds for BRPOP

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            redis_client = await get_redis()
            self.redis_service = RedisService(redis_client)
            logger.info(f"Worker {self.worker_id} initialized with Redis connection")
        except Exception as e:
            logger.error(f"Failed to initialize Redis for worker {self.worker_id}: {e}")
            raise

    def _validate_answer(self, question_data: Dict[str, Any], user_answer: List[str]) -> Tuple[bool, int]:
        """
        Validate user answer against question and calculate marks.
        Handles string-based answers, partial marking for MCQ, and negative marking.
        
        Args:
            question_data: Dictionary with question data (type, answers, etc.)
            user_answer: List of user's answer strings
            
        Returns:
            Tuple of (is_correct: bool, marks_obtained: int)
        """
        is_correct = False
        marks_obtained = 0
        
        if question_data["type"] == QuestionType.INTEGER:
            # Integer type: user_answer should be a list with one integer string
            if user_answer and len(user_answer) == 1:
                try:
                    user_int = int(user_answer[0])
                    if question_data["integer_answer"] is not None:
                        if user_int == question_data["integer_answer"]:
                            is_correct = True
                            marks_obtained = question_data["marks"]
                        else:
                            # Incorrect integer answer - negative marking
                            marks_obtained = -1
                except ValueError:
                    # Invalid integer format - treat as incorrect
                    marks_obtained = -1
            else:
                # Empty or multiple answers for integer type - negative marking
                marks_obtained = -1
                    
        elif question_data["type"] == QuestionType.MCQ:
            # MCQ type: Partial marking with negative marking
            # If only correct options chosen (all correct, no incorrect) → full marks
            # If some correct options chosen (and no incorrect) → +1 mark per correct option
            # If any incorrect option chosen → -2 marks total (regardless of correct options)
            # NOTE: User sends option text, need to map to index, then compare with zero-indexed correct_option
            if question_data["mcq_correct_option"] is not None and question_data["mcq_options"] is not None:
                try:
                    # Map user_answer option texts to their indices in mcq_options
                    user_indices = set()
                    for ans in user_answer:
                        # Find the index of this option text in mcq_options
                        found = False
                        for idx, option_text in enumerate(question_data["mcq_options"]):
                            if ans.strip() == option_text.strip():
                                user_indices.add(idx)  # idx is already zero-indexed
                                found = True
                                break
                        if not found:
                            # Option text not found - might be invalid, skip it
                            logger.warning(f"Option text not found in mcq_options: {ans}")
                    
                    # correct_option is already zero-indexed (0 = first option, 1 = second option, etc.)
                    correct_indices = set(question_data["mcq_correct_option"])
                    all_option_indices = set(range(len(question_data["mcq_options"])))
                    
                    # Calculate partial marks
                    correct_selected = user_indices & correct_indices
                    incorrect_selected = user_indices - correct_indices
                    
                    # If any incorrect option is selected, give -2 marks total
                    if len(incorrect_selected) > 0:
                        marks_obtained = -2
                    else:
                        # No incorrect options selected
                        if len(correct_selected) == len(correct_indices):
                            # All correct options selected - full marks
                            is_correct = True
                            marks_obtained = question_data["marks"]
                        else:
                            # Some correct options selected - +1 mark per correct option
                            marks_obtained = len(correct_selected)
                        
                except (ValueError, TypeError, IndexError):
                    # Invalid format - no marks
                    marks_obtained = 0
            else:
                # No correct options defined - no marks
                marks_obtained = 0
                    
        elif question_data["type"] == QuestionType.SCQ:
            # SCQ type: user_answer should be a list with one option text
            # NOTE: User sends option text, need to map to index, then compare with zero-indexed scq_correct_options
            if user_answer and len(user_answer) == 1:
                try:
                    # Map user_answer option text to its index in scq_options
                    user_index = None
                    if question_data.get("scq_options") is not None:
                        for idx, option_text in enumerate(question_data["scq_options"]):
                            if user_answer[0].strip() == option_text.strip():
                                user_index = idx  # idx is already zero-indexed
                                break
                    
                    if question_data["scq_correct_options"] is not None and user_index is not None:
                        # scq_correct_options is already zero-indexed (0 = first option, 1 = second option, etc.)
                        if user_index == question_data["scq_correct_options"]:
                            is_correct = True
                            marks_obtained = question_data["marks"]
                        else:
                            # Incorrect option selected - negative marking
                            marks_obtained = -1
                    else:
                        # Invalid option text or no correct option defined
                        marks_obtained = -1
                except (ValueError, TypeError, IndexError):
                    # Invalid format - treat as incorrect
                    marks_obtained = -1
            else:
                # Empty or multiple answers for SCQ - negative marking
                marks_obtained = -1
                    
        # For other types (match_the_column, etc.), treat as MCQ format
        elif question_data["type"] == QuestionType.MATCH:
            # NOTE: User sends option texts, need to map to indices, then compare with zero-indexed mcq_correct_option
            if question_data["mcq_correct_option"] is not None and question_data.get("mcq_options") is not None:
                try:
                    # Map user_answer option texts to their indices in mcq_options
                    user_indices = []
                    for ans in user_answer:
                        for idx, option_text in enumerate(question_data["mcq_options"]):
                            if ans.strip() == option_text.strip():
                                user_indices.append(idx)  # idx is already zero-indexed
                                break
                    
                    user_indices = sorted(user_indices)
                    correct_indices = sorted(question_data["mcq_correct_option"])
                    if user_indices == correct_indices:
                        is_correct = True
                        marks_obtained = question_data["marks"]
                    else:
                        # Incorrect match - negative marking
                        marks_obtained = -1
                except (ValueError, TypeError, IndexError):
                    # Invalid format - treat as incorrect
                    marks_obtained = -1
            else:
                # No correct options defined - treat as incorrect
                marks_obtained = -1
        
        return is_correct, marks_obtained

    async def process_user_submissions(self, user_submission_group: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Process all submissions for a single user and save to database.
        Tracks analytics locally and populates leaderboard with single DB call.
        
        Args:
            user_submission_group: Grouped submission data from queue containing:
                - contest_id: Contest ID
                - user_id: User ID
                - submissions: List of submission dictionaries
            db: Database session
            
        Returns:
            bool: True if all submissions processed successfully, False otherwise
        """
        try:
            user_id = UUID(user_submission_group["user_id"])
            contest_id = UUID(user_submission_group["contest_id"])
            submissions = user_submission_group["submissions"]
            
            processed_count = 0
            failed_count = 0
            
            # Local variables to track analytics
            total_score = 0.0
            correct_count = 0
            incorrect_count = 0
            attempted_count = 0
            total_time = 0  # Total time taken across all submissions
            
            # Get contest and total questions count
            contest_result = await db.execute(
                select(Contest).where(Contest.id == contest_id)
            )
            contest = contest_result.scalar_one_or_none()
            
            if not contest:
                logger.error(f"Worker {self.worker_id} contest not found: {contest_id}")
                return False
            
            # Get total questions count
            total_questions_result = await db.execute(
                select(func.count(ContestQuestions.id)).where(
                    ContestQuestions.contest_id == contest_id
                )
            )
            total_questions = total_questions_result.scalar() or 0
            
            # Fetch all questions for this batch to avoid N+1 queries
            question_ids = [UUID(sub["question_id"]) for sub in submissions]
            result = await db.execute(
                select(Question).where(Question.id.in_(question_ids))
            )
            questions_list = result.scalars().all()
            
            # Extract all needed attributes while still in async context to avoid lazy loading issues
            questions_data = {}
            for q in questions_list:
                questions_data[q.id] = {
                    "type": q.type,
                    "integer_answer": q.integer_answer,
                    "mcq_options": q.mcq_options,
                    "mcq_correct_option": q.mcq_correct_option,
                    "scq_options": q.scq_options,
                    "scq_correct_options": q.scq_correct_options,
                    "marks": q.marks,
                }
            
            # Process each submission for this user
            for submission in submissions:
                try:
                    question_id = UUID(submission["question_id"])
                    question_data = questions_data.get(question_id)
                    
                    if not question_data:
                        logger.warning(
                            f"Worker {self.worker_id} question not found: {question_id}"
                        )
                        failed_count += 1
                        continue
                    
                    # Validate answer and calculate marks
                    is_correct, marks_obtained = self._validate_answer(
                        question_data, submission["user_answer"]
                    )
                    
                    await create_attempt(
                        db=db,
                        user_id=user_id,
                        question_id=question_id,
                        user_answer=submission["user_answer"],
                        is_correct=is_correct,
                        marks_obtained=marks_obtained,
                        time_taken=submission["time_taken"],
                        hint_used=submission.get("hint_used", False),
                    )
                    
                    # Update local analytics
                    total_score += marks_obtained
                    attempted_count += 1
                    total_time += submission.get("time_taken", 0)  # Sum up time taken for all submissions
                    if is_correct:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                    
                    processed_count += 1
                except Exception as e:
                    logger.error(
                        f"Worker {self.worker_id} failed to process individual submission: "
                        f"user={user_id}, question={submission.get('question_id')}, error={e}",
                        exc_info=True
                    )
                    failed_count += 1
            
            # Populate leaderboard with single DB call
            if processed_count > 0:
                await self._populate_user_leaderboard(
                    db=db,
                    user_id=user_id,
                    contest_id=contest_id,
                    total_score=total_score,
                    total_questions=total_questions,
                    attempted_count=attempted_count,
                    correct_count=correct_count,
                    incorrect_count=incorrect_count,
                    total_time=total_time,
                )
                # Commit leaderboard update
                await db.commit()
            
            logger.info(
                f"Worker {self.worker_id} processed user submissions: "
                f"user={user_id}, contest={contest_id}, "
                f"processed={processed_count}, failed={failed_count}"
            )
            
            # Return True if at least some submissions were processed
            return processed_count > 0
        except Exception as e:
            logger.error(
                f"Worker {self.worker_id} failed to process user submission group: {e}",
                exc_info=True
            )
            return False

    async def _populate_user_leaderboard(
        self,
        db: AsyncSession,
        user_id: UUID,
        contest_id: UUID,
        total_score: float,
        total_questions: int,
        attempted_count: int,
        correct_count: int,
        incorrect_count: int,
        total_time: int,
    ):
        """
        Populate or update contest leaderboard entry for a user with single DB call.
        
        Args:
            db: Database session
            user_id: User ID
            contest_id: Contest ID
            total_score: Total marks obtained
            total_questions: Total questions in contest
            attempted_count: Number of questions attempted
            correct_count: Number of correct answers
            incorrect_count: Number of incorrect answers
            total_time: Total time taken by user in seconds
        """
        try:
            # Get user's current rating
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found for leaderboard")
                return
            
            rating_before = user.current_rating
            
            # Calculate analytics
            unattempted = total_questions - attempted_count
            accuracy = (correct_count / attempted_count * 100) if attempted_count > 0 else 0.0
            
            # Simple rating delta calculation (adjust as needed)
            rating_delta = 0
            rating_after = rating_before + 0
            
            # Check if leaderboard entry exists
            existing_result = await db.execute(
                select(ContestLeaderboard).where(
                    ContestLeaderboard.user_id == user_id,
                    ContestLeaderboard.contest_id == contest_id
                )
            )
            leaderboard_entry = existing_result.scalar_one_or_none()
            
            if leaderboard_entry:
                # Update existing entry
                leaderboard_entry.score = total_score
                leaderboard_entry.accuracy = accuracy
                leaderboard_entry.total_questions = total_questions
                leaderboard_entry.attempted = attempted_count
                leaderboard_entry.unattempted = unattempted
                leaderboard_entry.correct = correct_count
                leaderboard_entry.incorrect = incorrect_count
                leaderboard_entry.total_time = total_time
                leaderboard_entry.rating_before = rating_before
                leaderboard_entry.rating_after = rating_after
                leaderboard_entry.rating_delta = rating_delta
                leaderboard_entry.missed = False
                # Rank will be recalculated separately after all users are processed
            else:
                # Create new entry
                leaderboard_entry = ContestLeaderboard(
                    user_id=user_id,
                    contest_id=contest_id,
                    score=total_score,
                    accuracy=accuracy,
                    total_questions=total_questions,
                    attempted=attempted_count,
                    unattempted=unattempted,
                    correct=correct_count,
                    incorrect=incorrect_count,
                    total_time=total_time,
                    rating_before=rating_before,
                    rating_after=rating_after,
                    rating_delta=rating_delta,
                    rank=0,  # Will be calculated later
                    missed=False,
                )
                db.add(leaderboard_entry)
            
            logger.debug(
                f"Updated leaderboard for user {user_id} in contest {contest_id}: "
                f"score={total_score}, correct={correct_count}, incorrect={incorrect_count}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to populate leaderboard for user {user_id}: {e}",
                exc_info=True
            )
            # Don't raise - allow submission processing to continue

    async def get_contest_queues(self) -> list[str]:
        """
        Get all contest submission queue names that have items.
        Uses Redis SCAN to find all queues matching the pattern.
        """
        try:
            queues = []
            cursor = 0
            pattern = "contest:submissions:*"
            
            # Use SCAN instead of KEYS for better performance
            while True:
                cursor, keys = await self.redis_service.client.scan(
                    cursor, match=pattern, count=100
                )
                for key in keys:
                    # Check if queue has items
                    length = await self.redis_service.get_queue_length(key)
                    if length > 0:
                        queues.append(key)
                
                if cursor == 0:
                    break
            
            return queues
        except Exception as e:
            logger.error(f"Failed to get contest queues: {e}")
            return []

    async def pop_from_queue_atomic(self, queue_name: str) -> Dict[str, Any] | None:
        """
        Atomically pop a value from the queue using BRPOP (blocking right pop).
        This is atomic and safe for multiple workers.
        
        BRPOP is atomic at the Redis level - only one worker will receive each item,
        even when multiple workers are polling the same queue simultaneously.
        
        Args:
            queue_name: Name of the queue/list
            
        Returns:
            Popped value or None if timeout
        """
        try:
            # Use the atomic BRPOP method from RedisService
            # This blocks until an item is available or timeout, and is atomic
            result = await self.redis_service.pop_from_queue_blocking(
                queue_name, 
                timeout=self.blocking_timeout
            )
            
            if result is None:
                return None
            
            # pop_from_queue_blocking returns (queue_name, value) tuple
            _, value = result
            return value
                
        except Exception as e:
            logger.error(f"Error popping from queue {queue_name}: {e}")
            return None

    async def run(self):
        """Main worker loop"""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")
        
        # Track which contest queues we've seen (to detect when they become empty)
        seen_queues = set()
        
        try:
            while self.running:
                try:
                    # Get all active contest queues (queues with items)
                    queues = await self.get_contest_queues()
                    current_queue_set = set(queues)
                    
                    # Check if any previously seen queue is now empty (all submissions processed)
                    queues_to_remove = []
                    for queue_name in seen_queues:
                        if queue_name not in current_queue_set:
                            # Queue is now empty - push contest_id to grading queue
                            try:
                                contest_id_str = queue_name.split(":")[-1]
                                contest_id = UUID(contest_id_str)
                                grading_queue = "contest:grading"
                                await self.redis_service.push_to_queue(grading_queue, str(contest_id))
                                logger.info(
                                    f"Worker {self.worker_id}: Contest {contest_id} queue empty, "
                                    f"pushed to grading queue"
                                )
                                # Remove from seen_queues after successful push
                                queues_to_remove.append(queue_name)
                            except (ValueError, IndexError) as e:
                                logger.warning(f"Failed to extract contest_id from queue {queue_name}: {e}")
                                # Remove even on error to avoid retrying
                                queues_to_remove.append(queue_name)
                    
                    # Remove processed queues from seen_queues
                    for queue_name in queues_to_remove:
                        seen_queues.discard(queue_name)
                    
                    # Update seen queues to include current active queues
                    seen_queues.update(current_queue_set)
                    
                    if not queues:
                        # No active queues, wait before checking again
                        await asyncio.sleep(self.poll_interval * 5)
                        continue
                    
                    # Process queues in round-robin fashion using atomic BRPOP
                    processed_any = False
                    for queue_name in queues:
                        if not self.running:
                            break
                        
                        # Atomically pop one item from this queue
                        # BRPOP is atomic - safe for multiple workers
                        submission = await self.pop_from_queue_atomic(queue_name)
                        
                        if submission:
                            processed_any = True
                            # Process user submission group with database session
                            async with AsyncSessionLocal() as db:
                                success = await self.process_user_submissions(submission, db)
                                
                                if not success:
                                    logger.warning(
                                        f"Worker {self.worker_id} failed to process user submission group from {queue_name}"
                                    )
                            # Break after processing one item to allow round-robin
                            break
                    
                    # If no items were processed, wait a bit before checking again
                    if not processed_any:
                        await asyncio.sleep(self.poll_interval)
                        
                except Exception as e:
                    logger.error(
                        f"Worker {self.worker_id} error in main loop: {e}",
                        exc_info=True
                    )
                    await asyncio.sleep(self.poll_interval * 5)
                    
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} received shutdown signal")
        finally:
            self.running = False
            logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"Stopping worker {self.worker_id}...")
        self.running = False

