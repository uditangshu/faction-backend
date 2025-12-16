"""Custom Test Service"""

import random
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from typing import List

from app.models.Basequestion import Question, Topic, Chapter, Subject
from app.models.pyq import PreviousYearProblems
from app.models.weak_topic import UserWeakTopic
from app.models.user import TargetExam
from app.exceptions.http_exceptions import BadRequestException, NotFoundException


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

        # Build base query
        query = select(Question).distinct()
        
        # Join with Topic, Chapter, Subject for filtering
        query = query.join(Topic, Question.topic_id == Topic.id)
        query = query.join(Chapter, Topic.chapter_id == Chapter.id)
        query = query.join(Subject, Chapter.subject_id == Subject.id)

        # Apply filters
        # Filter by subjects
        query = query.where(Subject.id.in_(subject_ids))
        
        # Filter by chapters
        query = query.where(Chapter.id.in_(chapter_ids))
        
        # Filter by exam_type (using JSONB contains)
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
        if weak_topics_only:
            # Get user's weak topic IDs that belong to the specified chapters
            weak_topic_subquery = (
                select(UserWeakTopic.topic_id)
                .join(Topic, UserWeakTopic.topic_id == Topic.id)
                .where(
                    UserWeakTopic.user_id == user_id,
                    Topic.chapter_id.in_(chapter_ids)
                )
            )
            
            # Check if there are any weak topics for the user in the specified chapters
            weak_topic_check = await self.db.execute(
                select(func.count(UserWeakTopic.id))
                .join(Topic, UserWeakTopic.topic_id == Topic.id)
                .where(
                    UserWeakTopic.user_id == user_id,
                    Topic.chapter_id.in_(chapter_ids)
                )
            )
            weak_topic_count = weak_topic_check.scalar() or 0
            
            if weak_topic_count == 0:
                raise BadRequestException(
                    "No weak topics found for the user in the specified chapters. "
                    "Cannot generate test with weak_topics_only=True."
                )
            
            # Filter questions to only those from weak topics in the specified chapters
            query = query.where(Topic.id.in_(weak_topic_subquery))

        # Execute query to get all matching questions
        result = await self.db.execute(query)
        all_questions = list(result.scalars().all())

        if not all_questions:
            raise BadRequestException(
                "No questions found matching the specified criteria. "
                "Please adjust your filters (subjects, chapters, exam type, PYQ status, or weak topics)."
            )

        # Check if we have enough questions
        if len(all_questions) < number_of_questions:
            raise BadRequestException(
                f"Only {len(all_questions)} questions found matching the criteria, "
                f"but {number_of_questions} questions requested. "
                "Please reduce the number of questions or adjust your filters."
            )

        # Randomly select the requested number of questions
        selected_questions = random.sample(all_questions, number_of_questions)

        return selected_questions

