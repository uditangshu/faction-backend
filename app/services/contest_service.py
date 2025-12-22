"""Contest Service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any
from datetime import datetime

from app.models.contest import Contest, ContestStatus
from app.models.linking import ContestQuestions
from app.models.Basequestion import Question
from app.exceptions.http_exceptions import BadRequestException, NotFoundException
from app.integrations.redis_client import RedisService

class ContestService:
    """Service for contest operations"""

    def __init__(self, db: AsyncSession, redis_service: RedisService | None = None):
        self.db = db
        self.redis_service = redis_service

    async def create_contest(
        self,
        name: str,
        description: str | None,
        question_ids: List[UUID],
        total_time: int,
        status: ContestStatus,
        starts_at: datetime,
        ends_at: datetime,
    ) -> Contest:
        """
        Create a contest with questions in the database.
        
        Args:
            name: Contest name
            description: Contest description
            question_ids: List of question IDs to include
            total_time: Total time for the contest in seconds
            status: Contest status
            starts_at: Contest start datetime
            ends_at: Contest end datetime
            
        Returns:
            Created Contest instance
        """
        # Validate that all questions exist
        if not question_ids:
            raise BadRequestException("At least one question is required")
        
        # Check if all questions exist
        result = await self.db.execute(
            select(Question).where(Question.id.in_(question_ids))
        )
        existing_questions = result.scalars().all()
        existing_question_ids = {q.id for q in existing_questions}
        
        if len(existing_questions) != len(question_ids):
            missing_ids = set(question_ids) - existing_question_ids
            raise NotFoundException(f"Questions not found: {missing_ids}")
        
        # Validate datetime
        if starts_at >= ends_at:
            raise BadRequestException("starts_at must be before ends_at")
        
        # Convert timezone-aware datetimes to timezone-naive for database compatibility
        # The database uses TIMESTAMP WITHOUT TIME ZONE
        if starts_at.tzinfo is not None:
            starts_at = starts_at.replace(tzinfo=None)
        if ends_at.tzinfo is not None:
            ends_at = ends_at.replace(tzinfo=None)
        
        # Create the contest
        contest = Contest(
            name=name,
            description=description,
            total_time=total_time,
            status=status,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        self.db.add(contest)
        await self.db.flush()  # Get the contest ID
        
        # Bulk insert contest questions
        contest_questions = [
            ContestQuestions(
                contest_id=contest.id,
                question_id=question_id
            )
            for question_id in question_ids
        ]
        self.db.add_all(contest_questions)
        
        await self.db.commit()
        await self.db.refresh(contest)
        return contest

    async def get_upcoming_contests(self) -> List[Contest]:
        """
        Get all upcoming contests (contests that haven't started yet).
        
        Returns:
            List of upcoming Contest instances
        """
        from datetime import datetime as dt
        
        now = dt.now()
        result = await self.db.execute(
            select(Contest)
            .where(Contest.starts_at > now)
            .order_by(Contest.starts_at.asc())
        )
        return list(result.scalars().all())

    async def get_past_contests(self) -> List[Contest]:
        """
        Get all past contests (contests that have ended).
        
        Returns:
            List of past Contest instances
        """
        from datetime import datetime as dt
        
        now = dt.now()
        result = await self.db.execute(
            select(Contest)
            .where(Contest.ends_at < now)
            .order_by(Contest.ends_at.desc())
        )
        return list(result.scalars().all())

    async def get_contest_questions_with_details(
        self,
        contest_id: UUID,
        cache_ttl: int = 3600,  # 1 hour default
    ) -> List[Dict[str, Any]]:
        """
        Get contest questions with full details, using Redis caching.
        
        Args:
            contest_id: Contest ID
            cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)
            
        Returns:
            List of question dictionaries with full details
            
        Raises:
            NotFoundException: If contest not found
        """
        # Redis cache key
        cache_key = f"contest:questions:{contest_id}"
        
        # Try to get from Redis cache first
        if self.redis_service:
            cached_data = await self.redis_service.get_value(cache_key)
            if cached_data is not None:
                return cached_data
        
        # If not in cache, query database
        
        # Get contest with questions relationship
        result = await self.db.execute(
            select(Contest)
            .where(Contest.id == contest_id)
            .options(selectinload(Contest.questions).selectinload(ContestQuestions.question))
        )
        contest = result.scalar_one_or_none()
        
        if not contest:
            raise NotFoundException(f"Contest with id {contest_id} not found")
        
        # Extract questions from contest_questions relationship
        questions = []
        for contest_question in contest.questions:
            question = contest_question.question
            # Convert question to dictionary with all fields
            # Serialize enums as their string values for JSON compatibility
            # Handle exam_type: it might be enum objects or strings (from JSON deserialization)
            exam_type_values = []
            if question.exam_type:
                for exam in question.exam_type:
                    # If it's already a string, use it directly; otherwise get .value
                    if isinstance(exam, str):
                        exam_type_values.append(exam)
                    else:
                        exam_type_values.append(exam.value)
            
            question_dict = {
                "id": str(question.id),
                "topic_id": str(question.topic_id),
                "type": question.type.value if hasattr(question.type, 'value') else str(question.type),
                "difficulty": question.difficulty.value if hasattr(question.difficulty, 'value') else str(question.difficulty),
                "exam_type": exam_type_values,
                "question_text": question.question_text,
                "marks": question.marks,
                "solution_text": question.solution_text,
                "question_image": question.question_image,
                "integer_answer": question.integer_answer,
                "mcq_options": question.mcq_options,
                "mcq_correct_option": question.mcq_correct_option,
                "scq_options": question.scq_options,
                "scq_correct_options": question.scq_correct_options,
                "questions_solved": question.questions_solved,
            }
            questions.append(question_dict)
        
        # Store in Redis cache
        if self.redis_service:
            await self.redis_service.set_value(cache_key, questions, expire=cache_ttl)
        
        return questions

    async def push_submissions_to_queue(
        self,
        contest_id: UUID,
        user_id: UUID,
        submissions: List[Dict[str, Any]],
    ) -> str:
        """
        Push contest submissions to Redis queue for async processing.
        All submissions from a single user are grouped into a single queue item.
        
        Args:
            contest_id: Contest ID
            user_id: User ID
            submissions: List of submission dictionaries
            
        Returns:
            Queue name used for storing submissions
            
        Raises:
            BadRequestException: If Redis service is not available
        """

        if not self.redis_service:
            raise BadRequestException("Redis service is not available")
                
        # Queue name for contest submissions
        queue_name = f"contest:submissions:{contest_id}"
        
        # Format individual submissions (without contest_id and user_id, they'll be in the parent object)
        formatted_submissions = []
        for submission in submissions:
            formatted_submission = {
                "question_id": str(submission["question_id"]),
                "user_answer": submission["user_answer"],
                "time_taken": submission["time_taken"],
                "hint_used": submission.get("hint_used", False),
            }
            formatted_submissions.append(formatted_submission)
        
        # Group all submissions from this user into a single queue item
        user_submission_group = {
            "contest_id": str(contest_id),
            "user_id": str(user_id),
            "submissions": formatted_submissions,
        }
        
        # Push single grouped item to Redis queue
        await self.redis_service.push_to_queue(queue_name, user_submission_group)
        
        return queue_name

