"""PYQ Filtering service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, cast
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple

from app.models.pyq import PreviousYearProblems
from app.models.Basequestion import Question, QuestionType, DifficultyLevel, Topic, Chapter, Subject
from app.models.attempt import QuestionAttempt
from app.schemas.filters import YearWiseSorting, QuestionAppearance


class FilteringService:
    """Service for filtering PYQ questions"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_filtered_pyqs(
        self,
        user_id: Optional[UUID] = None,
        subject_ids: Optional[List[UUID]] = None,
        chapter_ids: Optional[List[UUID]] = None,
        difficulty: Optional[DifficultyLevel] = None,
        year_filter: Optional[List[int]] = None,
        question_appearance: QuestionAppearance = QuestionAppearance.BOTH,
        cursor: Optional[UUID] = None,
        limit: int = 20,
    ) -> Tuple[List[dict], int, Optional[UUID], bool]:
        """
        Get filtered questions with various filters. Filters on Question model.
        
        Args:
            user_id: User ID for last_practiced filtering
            subject_ids: Filter by list of subject IDs
            chapter_ids: Filter by list of chapter IDs
            difficulty: Filter by difficulty level
            year_filter: Filter by list of years (only applies to PYQ questions)
            question_appearance: Filter by PYQ_ONLY, NON_PYQ_ONLY, or BOTH
            cursor: Cursor for infinite scrolling (question ID)
            limit: Number of records to return
            
        Returns:
            Tuple of (list of question dicts, total count, next cursor, has_more)
        """
        # Base query starting from Question
        query = select(Question)
        count_query = select(func.count(Question.id))
        
        # Join with Topic, Chapter, Subject for filtering
        query = query.join(Topic, Question.topic_id == Topic.id)
        query = query.join(Chapter, Topic.chapter_id == Chapter.id)
        query = query.join(Subject, Chapter.subject_id == Subject.id)
        
        count_query = count_query.join(Topic, Question.topic_id == Topic.id)
        count_query = count_query.join(Chapter, Topic.chapter_id == Chapter.id)
        count_query = count_query.join(Subject, Chapter.subject_id == Subject.id)

        # Apply filters
        if subject_ids:
            query = query.where(Subject.id.in_(subject_ids))
            count_query = count_query.where(Subject.id.in_(subject_ids))
        
        if chapter_ids:
            query = query.where(Chapter.id.in_(chapter_ids))
            count_query = count_query.where(Chapter.id.in_(chapter_ids))
        
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
            count_query = count_query.where(Question.difficulty == difficulty)

        # Handle question_appearance filter
        all_pyq_question_ids = select(PreviousYearProblems.question_id).distinct()
        
        if question_appearance == QuestionAppearance.PYQ_ONLY:
            # Only questions that exist in PYQ table
            if year_filter:
                pyq_subquery = select(PreviousYearProblems.question_id).where(
                    PreviousYearProblems.year.in_(year_filter)
                ).distinct()
                query = query.where(Question.id.in_(pyq_subquery))
                count_query = count_query.where(Question.id.in_(pyq_subquery))
            else:
                query = query.where(Question.id.in_(all_pyq_question_ids))
                count_query = count_query.where(Question.id.in_(all_pyq_question_ids))
        elif question_appearance == QuestionAppearance.NON_PYQ_ONLY:
            # Only questions that do NOT exist in PYQ table
            query = query.where(~Question.id.in_(all_pyq_question_ids))
            count_query = count_query.where(~Question.id.in_(all_pyq_question_ids))
        elif question_appearance == QuestionAppearance.BOTH:
            # All questions, but if year_filter is provided, filter PYQ questions by year
            if year_filter:
                # Include non-PYQ questions OR PYQ questions matching year filter
                pyq_with_year_subquery = select(PreviousYearProblems.question_id).where(
                    PreviousYearProblems.year.in_(year_filter)
                ).distinct()
                query = query.where(
                    (~Question.id.in_(all_pyq_question_ids)) |
                    (Question.id.in_(pyq_with_year_subquery))
                )
                count_query = count_query.where(
                    (~Question.id.in_(all_pyq_question_ids)) |
                    (Question.id.in_(pyq_with_year_subquery))
                )

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply cursor-based pagination for infinite scrolling
        if cursor:
            query = query.where(Question.id > cursor)
        
        # Order by question ID for consistent pagination
        query = query.order_by(Question.id.asc())
        
        # Fetch one extra to check if there are more
        query = query.limit(limit + 1)
        
        result = await self.db.execute(query)
        questions_result = result.scalars().all()
        
        # Check if there are more results
        has_more = len(questions_result) > limit
        if has_more:
            # Get the cursor from the item after the limit (the one that indicates more)
            next_cursor = questions_result[limit].id
            questions_result = questions_result[:limit]
        else:
            next_cursor = None

        # Build response with PYQ and last practiced info
        questions = []
        question_ids = [q.id for q in questions_result]
        
        # Fetch PYQ data for all questions in one query
        pyq_map = {}
        if question_ids:
            pyq_result = await self.db.execute(
                select(PreviousYearProblems)
                .where(PreviousYearProblems.question_id.in_(question_ids))
            )
            pyqs = pyq_result.scalars().all()
            for pyq in pyqs:
                pyq_map[pyq.question_id] = pyq
        
        # Fetch last practiced dates if user_id is provided
        last_practiced_map = {}
        if user_id and question_ids:
            attempt_result = await self.db.execute(
                select(
                    QuestionAttempt.question_id,
                    func.max(QuestionAttempt.attempted_at).label('last_attempted_at')
                )
                .where(
                    QuestionAttempt.user_id == user_id,
                    QuestionAttempt.question_id.in_(question_ids)
                )
                .group_by(QuestionAttempt.question_id)
            )
            for row in attempt_result.all():
                last_practiced_map[row.question_id] = str(row.last_attempted_at)

        # Build response
        for question in questions_result:
            question_data = {
                "question_id": question.id,
                "question": question,
                "pyq_id": None,
                "year": None,
                "exam_detail": None,
                "pyq_created_at": None,
                "last_practiced_at": None,
            }
            
            # Add PYQ data if available
            if question.id in pyq_map:
                pyq = pyq_map[question.id]
                question_data["pyq_id"] = pyq.id
                question_data["year"] = pyq.year
                question_data["exam_detail"] = pyq.exam_detail or []
                question_data["pyq_created_at"] = str(pyq.created_at)
            
            # Add last practiced date if available
            if question.id in last_practiced_map:
                question_data["last_practiced_at"] = last_practiced_map[question.id]
            
            questions.append(question_data)

        return questions, total, next_cursor, has_more

    # Note: The following helper methods have been removed.
    # Use get_filtered_pyqs() with appropriate filters instead.

    async def get_pyq_stats(self, user_id: UUID) -> dict:
        """Get PYQ statistics for a user"""
        # Total PYQs
        total_result = await self.db.execute(
            select(func.count(PreviousYearProblems.id))
        )
        total_pyqs = total_result.scalar() or 0

        # Practiced PYQs by user
        practiced_result = await self.db.execute(
            select(func.count(func.distinct(QuestionAttempt.question_id)))
            .join(PreviousYearProblems, QuestionAttempt.question_id == PreviousYearProblems.question_id)
            .where(QuestionAttempt.user_id == user_id)
        )
        practiced_pyqs = practiced_result.scalar() or 0

        # Correct attempts on PYQs
        correct_result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .join(PreviousYearProblems, QuestionAttempt.question_id == PreviousYearProblems.question_id)
            .where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.is_correct == True,
            )
        )
        correct_attempts = correct_result.scalar() or 0

        return {
            "total_pyqs": total_pyqs,
            "practiced_pyqs": practiced_pyqs,
            "unpracticed_pyqs": total_pyqs - practiced_pyqs,
            "correct_attempts": correct_attempts,
            "completion_percentage": round((practiced_pyqs / total_pyqs * 100) if total_pyqs > 0 else 0, 2),
        }

    async def get_all_years(self) -> List[int]:
        """Get all distinct years present in PYQ database, sorted in descending order"""
        result = await self.db.execute(
            select(func.distinct(PreviousYearProblems.year))
            .order_by(desc(PreviousYearProblems.year))
        )
        years = [row[0] for row in result.all() if row[0] is not None]
        return years

