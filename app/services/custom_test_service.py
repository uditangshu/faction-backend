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
from app.models.custom_test import CustomTest, AttemptStatus
from app.models.linking import CustomTestQuestion
from app.exceptions.http_exceptions import BadRequestException, NotFoundException
from sqlalchemy.orm import selectinload


class CustomTestService:
    """Service for custom test operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

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
        return test

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
        Get all custom tests for a user with pagination.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (list of tests, total count)
        """
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

