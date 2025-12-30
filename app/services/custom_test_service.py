"""Custom Test Service"""

import random
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional

from app.models.Basequestion import Question, Topic, Chapter, Subject
from app.models.pyq import PreviousYearProblems
from app.models.weak_topic import UserWeakTopic
from app.models.user import TargetExam
from app.models.custom_test import CustomTest, AttemptStatus, CustomTestAnalysis
from app.models.linking import CustomTestQuestion
from app.exceptions.http_exceptions import BadRequestException, NotFoundException
from app.db.attempt_calls import create_attempt
from app.integrations.redis_client import RedisService
from app.core.config import settings
from sqlalchemy.orm import selectinload
from datetime import datetime


class CustomTestService:
    """Service for custom test operations"""

    CACHE_PREFIX = "custom_tests"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    async def generate_custom_test_questions(
        self,
        user_id: UUID,
        exam_type: TargetExam,
        subject_ids: List[UUID],
        chapter_ids: List[UUID],
        number_of_questions: int,
        pyq_only: bool = False,
        weak_topics_only: bool = False,
        weakness_score: Optional[float] = None,
    ) -> List[Question]:
        """
        Generate custom test questions based on filters.
        
        Args:
            user_id: User ID for weak topics filtering
            exam_type: Target exam type
            subject_ids: List of subject UUIDs
            chapter_ids: List of chapter UUIDs
            number_of_questions: Number of questions to return
            pyq_only: If True, only PYQ questions; if False, all questions
            weak_topics_only: If True, only questions from weak topics
            weakness_score: Optional minimum weakness score threshold (0-100).
                Only used when weak_topics_only=True. If no weak topics match
                the threshold, falls back to all topics in requested chapters.
            
        Returns:
            List of randomly selected questions
            
        Raises:
            BadRequestException: If no questions match the criteria
            NotFoundException: If subjects or chapters don't exist
        """
        # Validate subjects exist
        subject_result = await self.db.execute(
            select(Subject).where(Subject.id.in_(subject_ids))
        )
        subjects = list(subject_result.scalars().all())
        if len(subjects) != len(subject_ids):
            found_ids = {s.id for s in subjects}
            missing_ids = set(subject_ids) - found_ids
            raise NotFoundException(f"Subjects not found: {missing_ids}")

        # Validate chapters exist
        chapter_result = await self.db.execute(
            select(Chapter).where(Chapter.id.in_(chapter_ids))
        )
        chapters = list(chapter_result.scalars().all())
        if len(chapters) != len(chapter_ids):
            found_ids = {c.id for c in chapters}
            missing_ids = set(chapter_ids) - found_ids
            raise NotFoundException(f"Chapters not found: {missing_ids}")

        # Verify chapters belong to specified subjects
        chapter_subject_ids = {c.subject_id for c in chapters}
        if not chapter_subject_ids.issubset(set(subject_ids)):
            invalid_chapters = [
                c.id for c in chapters if c.subject_id not in subject_ids
            ]
            raise BadRequestException(
                f"Chapters do not belong to specified subjects: {invalid_chapters}"
            )

        # Build base query - no DISTINCT needed as Question.id is unique
        query = select(Question)
        
        # Join with Topic, Chapter, Subject for filtering
        query = query.join(Topic, Question.topic_id == Topic.id)
        query = query.join(Chapter, Topic.chapter_id == Chapter.id)
        query = query.join(Subject, Chapter.subject_id == Subject.id)

        # Apply filters
        # Filter by subjects
        query = query.where(Subject.id.in_(subject_ids))
        
        # Filter by chapters
        query = query.where(Chapter.id.in_(chapter_ids))
        
        # Filter by exam_type (using JSONB @> operator)
        # The exam_type column is stored as JSON, so we cast to JSONB for comparison
        # Use jsonb_build_array to properly create JSONB array
        query = query.where(
            cast(Question.exam_type, JSONB).contains([exam_type.value])
        )

        # Filter by PYQ status
        all_pyq_question_ids = select(PreviousYearProblems.question_id).distinct()
        
        if pyq_only:
            # Only PYQ questions
            query = query.where(Question.id.in_(all_pyq_question_ids))
        # If pyq_only is False, we include all questions (no filter needed)

        # Filter by weak topics if requested
        weak_topic_query = None
        weak_topic_count = 0
        
        if weak_topics_only:
            # Build query for weak topics that belong to the specified chapters
            weak_topic_query = (
                select(UserWeakTopic.topic_id)
                .join(Topic, UserWeakTopic.topic_id == Topic.id)
                .where(
                    UserWeakTopic.user_id == user_id,
                    Topic.chapter_id.in_(chapter_ids)
                )
            )
            
            # Apply weakness_score filter if provided
            if weakness_score is not None:
                weak_topic_query = weak_topic_query.where(
                    UserWeakTopic.weakness_score >= weakness_score
                )
            
            # Check if there are any weak topics matching the criteria
            weak_topic_check_query = (
                select(func.count(UserWeakTopic.id))
                .join(Topic, UserWeakTopic.topic_id == Topic.id)
                .where(
                    UserWeakTopic.user_id == user_id,
                    Topic.chapter_id.in_(chapter_ids)
                )
            )
            
            # Apply weakness_score filter if provided
            if weakness_score is not None:
                weak_topic_check_query = weak_topic_check_query.where(
                    UserWeakTopic.weakness_score >= weakness_score
                )
            
            weak_topic_check = await self.db.execute(weak_topic_check_query)
            weak_topic_count = weak_topic_check.scalar() or 0
            
            # If no weak topics match, fall back to all topics in requested chapters
            # (Don't fail, just use all topics from the chapters)
            if weak_topic_count > 0:
                # Filter questions to only those from weak topics in the specified chapters
                query = query.where(Topic.id.in_(weak_topic_query))
            # If weak_topic_count == 0, we don't add the filter, so it uses all topics from chapters

        # First, check if we have enough questions (fast count query)
        count_query = select(func.count(Question.id))
        count_query = count_query.join(Topic, Question.topic_id == Topic.id)
        count_query = count_query.join(Chapter, Topic.chapter_id == Chapter.id)
        count_query = count_query.join(Subject, Chapter.subject_id == Subject.id)
        count_query = count_query.where(Subject.id.in_(subject_ids))
        count_query = count_query.where(Chapter.id.in_(chapter_ids))
        count_query = count_query.where(
            cast(Question.exam_type, JSONB).contains([exam_type.value])
        )
        
        if pyq_only:
            count_query = count_query.where(Question.id.in_(all_pyq_question_ids))
        
        if weak_topics_only and weak_topic_count > 0 and weak_topic_query is not None:
            count_query = count_query.where(Topic.id.in_(weak_topic_query))
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        if total_count == 0:
            raise BadRequestException(
                "No questions found matching the specified criteria. "
                "Please adjust your filters (subjects, chapters, exam type, PYQ status, or weak topics)."
            )
        
        if total_count < number_of_questions:
            raise BadRequestException(
                f"Only {total_count} questions found matching the criteria, "
                f"but {number_of_questions} questions requested. "
                "Please reduce the number of questions or adjust your filters."
            )

        # Use PostgreSQL's ORDER BY RANDOM() for efficient random selection
        # This is faster than loading all questions into memory
        query = query.order_by(func.random()).limit(number_of_questions)
        
        # Execute query to get randomly selected questions
        result = await self.db.execute(query)
        selected_questions = list(result.scalars().all())

        return selected_questions

    async def create_custom_test(
        self,
        user_id: UUID,
        question_ids: List[UUID],
        time_assigned: int = 0,
    ) -> CustomTest:
        """
        Create a custom test with questions in the database.
        
        Args:
            user_id: User ID who owns the test
            question_ids: List of question IDs to include
            time_assigned: Time assigned for the test in seconds
            
        Returns:
            Created CustomTest instance
        """
        # Create the test
        test = CustomTest(
            user_id=user_id,
            time_assigned=time_assigned,
            status=AttemptStatus.not_started,
        )
        self.db.add(test)
        await self.db.flush()  # Get the test ID
        
        # Bulk insert questions for better performance
        if question_ids:
            # Use bulk insert for better performance with many questions
            from sqlalchemy.dialects.postgresql import insert
            test_questions = [
                CustomTestQuestion(
                    test_id=test.id,
                    question_id=question_id
                )
                for question_id in question_ids
            ]
            self.db.add_all(test_questions)
        
        await self.db.commit()
        await self.db.refresh(test)
        
        # Invalidate user's custom tests cache when new test is created
        if self.redis_service:
            await self._invalidate_user_tests_cache(user_id)
        
        return test
    
    async def _invalidate_user_tests_cache(self, user_id: UUID):
        """Invalidate all custom tests caches for a user"""
        if not self.redis_service:
            return
        
        # Use Redis SCAN to find and delete all keys matching custom_tests:user:{user_id}:*
        cursor = 0
        pattern = f"{self.CACHE_PREFIX}:user:{user_id}:*"
        
        while True:
            cursor, keys = await self.redis_service.client.scan(cursor, match=pattern, count=100)
            
            if keys:
                await self.redis_service.client.delete(*keys)
            
            if cursor == 0:
                break

    async def get_custom_test_by_id(
        self,
        test_id: UUID,
        user_id: UUID,
    ) -> Optional[CustomTest]:
        """
        Get a custom test by ID with all questions.
        
        Args:
            test_id: Custom test ID
            user_id: User ID to verify ownership
            
        Returns:
            CustomTest with questions loaded, or None if not found
        """
        result = await self.db.execute(
            select(CustomTest)
            .where(CustomTest.id == test_id, CustomTest.user_id == user_id)
            .options(
                selectinload(CustomTest.questions)
                .selectinload(CustomTestQuestion.question)
            )
        )
        return result.scalar_one_or_none()

    async def get_user_custom_tests(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[CustomTest], int]:
        """
        Get all custom tests for a user with pagination (cached globally).
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (list of tests, total count)
        """
        # Build cache key
        cache_key = f"{self.CACHE_PREFIX}:user:{user_id}:{skip}:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                test_ids = [UUID(tid) for tid in cached.get("test_ids", [])]
                total = cached.get("total", 0)
                
                if test_ids:
                    result = await self.db.execute(
                        select(CustomTest)
                        .where(CustomTest.id.in_(test_ids))
                        .order_by(CustomTest.created_at.desc())
                    )
                    tests = list(result.scalars().all())
                    return tests, total
                return [], total
        
        # Count query
        count_result = await self.db.execute(
            select(func.count(CustomTest.id))
            .where(CustomTest.user_id == user_id)
        )
        total = count_result.scalar() or 0
        
        # Data query with question count
        result = await self.db.execute(
            select(CustomTest)
            .where(CustomTest.user_id == user_id)
            .order_by(CustomTest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        tests = list(result.scalars().all())
        
        # Cache result
        if self.redis_service:
            test_ids = [str(t.id) for t in tests]
            await self.redis_service.set_value(
                cache_key,
                {"test_ids": test_ids, "total": total},
                expire=settings.LONG_TERM_CACHE_TTL
            )
        
        return tests, total

    async def get_test_question_count(self, test_id: UUID) -> int:
        """
        Get the number of questions in a test.
        
        Args:
            test_id: Custom test ID
            
        Returns:
            Number of questions in the test
        """
        result = await self.db.execute(
            select(func.count(CustomTestQuestion.id))
            .where(CustomTestQuestion.test_id == test_id)
        )
        return result.scalar() or 0

    async def submit_custom_test(
        self,
        test_id: UUID,
        user_id: UUID,
        attempts_data: List[dict],
    ) -> CustomTestAnalysis:
        """
        Submit a custom test by creating attempts iteratively and updating analysis.
        
        This method:
        1. Validates the test exists and belongs to the user
        2. Validates all attempts are for questions in the test
        3. Creates attempts iteratively using create_attempt (which handles streaks)
        4. Calculates analysis metrics
        5. Creates/updates CustomTestAnalysis
        6. Updates test status to finished
        
        Args:
            test_id: Custom test ID
            user_id: User ID (must match test owner)
            attempts_data: List of attempt data dicts with keys:
                - question_id: UUID
                - user_answer: List[str]
                - is_correct: bool
                - marks_obtained: int
                - time_taken: int
                - hint_used: bool (optional)
        
        Returns:
            CustomTestAnalysis instance
            
        Raises:
            NotFoundException: If test not found or doesn't belong to user
            BadRequestException: If test is already finished or invalid data
        """
        # Get the test with questions - single query with eager loading
        test = await self.get_custom_test_by_id(test_id=test_id, user_id=user_id)
        if not test:
            raise NotFoundException(f"Custom test with ID {test_id} not found")
        
        # Check if test is already finished
        if test.status == AttemptStatus.finished:
            raise BadRequestException("Test has already been submitted")
        
        # Get all question IDs in the test - efficient set lookup
        test_question_ids = {q.question_id for q in test.questions}
        
        # Validate that all attempts are for questions in the test
        attempt_question_ids = {attempt["question_id"] for attempt in attempts_data}
        invalid_questions = attempt_question_ids - test_question_ids
        if invalid_questions:
            raise BadRequestException(
                f"Attempts contain questions not in this test: {invalid_questions}"
            )
        
        # Calculate total marks from all questions in the test
        total_marks = sum(q.question.marks for q in test.questions)
        
        # Create attempts iteratively - each call to create_attempt handles streaks
        # This is the most efficient approach as create_attempt already optimizes streak updates
        created_attempts = []
        for attempt_data in attempts_data:
            attempt = await create_attempt(
                db=self.db,
                user_id=user_id,
                question_id=attempt_data["question_id"],
                user_answer=attempt_data["user_answer"],
                is_correct=attempt_data["is_correct"],
                marks_obtained=attempt_data["marks_obtained"],
                time_taken=attempt_data["time_taken"],
                hint_used=attempt_data.get("hint_used", False),
            )
            created_attempts.append(attempt)
        
        # Calculate analysis metrics efficiently
        marks_obtained = sum(attempt.marks_obtained for attempt in created_attempts)
        total_time_spent = sum(attempt.time_taken for attempt in created_attempts)
        correct = sum(1 for attempt in created_attempts if attempt.is_correct)
        incorrect = len(created_attempts) - correct
        
        # Calculate unattempted questions
        attempted_question_ids = {attempt.question_id for attempt in created_attempts}
        unattempted = len(test_question_ids) - len(attempted_question_ids)
        
        # Check if analysis already exists (shouldn't, but handle it)
        analysis_result = await self.db.execute(
            select(CustomTestAnalysis).where(
                CustomTestAnalysis.custom_test_id == test_id
            )
        )
        existing_analysis = analysis_result.scalar_one_or_none()
        
        if existing_analysis:
            # Update existing analysis
            existing_analysis.marks_obtained = marks_obtained
            existing_analysis.total_marks = total_marks
            existing_analysis.total_time_spent = total_time_spent
            existing_analysis.correct = correct
            existing_analysis.incorrect = incorrect
            existing_analysis.unattempted = unattempted
            existing_analysis.submitted_at = datetime.utcnow()
            analysis = existing_analysis
        else:
            # Create new analysis
            analysis = CustomTestAnalysis(
                user_id=user_id,
                custom_test_id=test_id,
                marks_obtained=marks_obtained,
                total_marks=total_marks,
                total_time_spent=total_time_spent,
                correct=correct,
                incorrect=incorrect,
                unattempted=unattempted,
            )
            self.db.add(analysis)
        
        # Update test status to finished
        test.status = AttemptStatus.finished
        test.updated_at = datetime.utcnow()
        
        # Commit analysis and test status update
        await self.db.commit()
        await self.db.refresh(analysis)
        
        return analysis

    async def get_test_analysis(
        self,
        test_id: UUID,
        user_id: UUID,
    ) -> Optional[CustomTestAnalysis]:
        """
        Get the analysis for a completed test.
        
        Args:
            test_id: Custom test ID
            user_id: User ID to verify ownership
            
        Returns:
            CustomTestAnalysis if found, None otherwise
        """
        result = await self.db.execute(
            select(CustomTestAnalysis).where(
                CustomTestAnalysis.custom_test_id == test_id,
                CustomTestAnalysis.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

