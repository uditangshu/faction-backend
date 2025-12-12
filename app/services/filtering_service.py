"""PYQ Filtering service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, cast
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple

from app.models.pyq import PreviousYearProblems
from app.models.Basequestion import Question, QuestionType, DifficultyLevel
from app.models.attempt import QuestionAttempt
from app.schemas.filters import YearWiseSorting


class FilteringService:
    """Service for filtering PYQ questions"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_filtered_pyqs(
        self,
        user_id: Optional[UUID] = None,
        difficulty: Optional[DifficultyLevel] = None,
        question_type: Optional[QuestionType] = None,
        year_wise_sorting: Optional[YearWiseSorting] = None,
        last_practiced_first: bool = False,
        exam_filter: Optional[List[str]] = None,
        year_filter: Optional[List[int]] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[dict], int]:
        """
        Get filtered PYQ questions with various filters.
        
        Args:
            user_id: User ID for last_practiced filtering
            difficulty: Filter by difficulty level
            question_type: Filter by question type
            year_wise_sorting: Sort by year (ascending/descending)
            last_practiced_first: Sort by last practiced date
            exam_filter: Filter by exam names in exam_detail
            year_filter: Filter by list of years
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (list of question dicts, total count)
        """
        # Base query joining PYQ with Question
        query = (
            select(
                PreviousYearProblems,
                Question,
            )
            .join(Question, PreviousYearProblems.question_id == Question.id)
        )
        
        count_query = (
            select(func.count(PreviousYearProblems.id))
            .join(Question, PreviousYearProblems.question_id == Question.id)
        )

        # Apply filters
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
            count_query = count_query.where(Question.difficulty == difficulty)
        
        if question_type:
            query = query.where(Question.type == question_type)
            count_query = count_query.where(Question.type == question_type)
        
        if exam_filter:
            # Filter by any of the exam names in exam_detail
            for exam in exam_filter:
                query = query.filter(cast(PreviousYearProblems.exam_detail, JSONB).contains([exam]))
                count_query = count_query.filter(cast(PreviousYearProblems.exam_detail, JSONB).contains([exam]))

        if year_filter:
            # Filter by years - match if year is in the provided list
            query = query.where(PreviousYearProblems.year.in_(year_filter))
            count_query = count_query.where(PreviousYearProblems.year.in_(year_filter))

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        if year_wise_sorting:
            if year_wise_sorting == YearWiseSorting.ASCENDING:
                query = query.order_by(asc(PreviousYearProblems.year))
            else:
                query = query.order_by(desc(PreviousYearProblems.year))
        else:
            # Default: newest first (by year descending, then by created_at)
            query = query.order_by(desc(PreviousYearProblems.year), desc(PreviousYearProblems.created_at))

        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()

        # Build response with last practiced info if user_id is provided
        questions = []
        for pyq, question in rows:
            question_data = {
                "pyq_id": pyq.id,
                "question_id": question.id,
                "year": pyq.year,
                "exam_detail": pyq.exam_detail or [],
                "pyq_created_at": str(pyq.created_at),
                "question": question, 
                "last_practiced_at": None,
            }
            
            # Get last practiced date if user_id is provided
            if user_id:
                attempt_result = await self.db.execute(
                    select(QuestionAttempt.attempted_at)
                    .where(
                        QuestionAttempt.user_id == user_id,
                        QuestionAttempt.question_id == question.id,
                    )
                    .order_by(desc(QuestionAttempt.attempted_at))
                    .limit(1)
                )
                last_attempt = attempt_result.scalar_one_or_none()
                if last_attempt:
                    question_data["last_practiced_at"] = str(last_attempt)
            
            questions.append(question_data)

        # Sort by last practiced if requested
        if last_practiced_first and user_id:
            # Sort: practiced questions first (most recent), then unpracticed
            questions.sort(
                key=lambda x: (
                    x["last_practiced_at"] is None,  # Unpracticed last
                    x["last_practiced_at"] or "",  # Then by date descending
                ),
                reverse=False
            )
            # Reverse the practiced ones to get most recent first
            practiced = [q for q in questions if q["last_practiced_at"]]
            unpracticed = [q for q in questions if not q["last_practiced_at"]]
            practiced.sort(key=lambda x: x["last_practiced_at"], reverse=True)
            questions = practiced + unpracticed

        return questions, total

    async def get_pyqs_by_difficulty(
        self,
        difficulty: DifficultyLevel,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[dict], int]:
        """Get PYQs filtered by difficulty level"""
        return await self.get_filtered_pyqs(
            difficulty=difficulty,
            skip=skip,
            limit=limit,
        )

    async def get_pyqs_by_question_type(
        self,
        question_type: QuestionType,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[dict], int]:
        """Get PYQs filtered by question type"""
        return await self.get_filtered_pyqs(
            question_type=question_type,
            skip=skip,
            limit=limit,
        )

    async def get_user_practiced_pyqs(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[dict], int]:
        """Get PYQs that user has practiced, sorted by last practiced"""
        return await self.get_filtered_pyqs(
            user_id=user_id,
            last_practiced_first=True,
            skip=skip,
            limit=limit,
        )

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

