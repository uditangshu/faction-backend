"""Question Attempt service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from typing import List, Optional, Tuple

from app.models.attempt import QuestionAttempt

from app.db.attempt_calls import create_attempt, remove_attempt, update_attempt

class AttemptService:
    """Service for question attempt operations - stateless, accepts db as method parameter"""

    async def create_attempt(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
        user_answer: List[str],
        is_correct: bool,
        marks_obtained: int = 0,
        time_taken: int = 0,
        hint_used: bool = False,
    ) -> QuestionAttempt:
        """Create a new question attempt"""
        result = await create_attempt(db, user_id, question_id, user_answer, is_correct, marks_obtained, time_taken, hint_used)
        return result

    async def get_attempt_by_id(self, db: AsyncSession, attempt_id: UUID) -> Optional[QuestionAttempt]:
        """Get an attempt by ID"""
        result = await db.execute(
            select(QuestionAttempt).where(QuestionAttempt.id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def get_user_attempts(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[QuestionAttempt], int]:
        """Get all attempts for a user with pagination"""
        # Count query
        count_result = await db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Data query
        result = await db.execute(
            select(QuestionAttempt)
            .where(QuestionAttempt.user_id == user_id)
            .order_by(QuestionAttempt.attempted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_attempts_for_question(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
    ) -> QuestionAttempt:
        """Get all attempts by a user for a specific question"""
        result = await db.execute(
            select(QuestionAttempt)
            .where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.question_id == question_id,
            )
            .order_by(QuestionAttempt.attempted_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_latest_attempt(
        self,
        db: AsyncSession,
        user_id: UUID,
        question_id: UUID,
    ) -> Optional[QuestionAttempt]:
        """Get the latest attempt by a user for a specific question"""
        result = await db.execute(
            select(QuestionAttempt)
            .where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.question_id == question_id,
            )
            .order_by(QuestionAttempt.attempted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_attempt(
        self,
        db: AsyncSession,
        attempt_id: UUID,
        explanation_viewed: Optional[bool] = None,
        hint_used: Optional[bool] = None,
    ) -> Optional[QuestionAttempt]:
        """Update an attempt (mainly for tracking explanation views)"""
        attempt = await self.get_attempt_by_id(db, attempt_id)
        if not attempt:
            return None

        if explanation_viewed is not None:
            attempt.explanation_viewed = explanation_viewed
        if hint_used is not None:
            attempt.hint_used = hint_used

        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)
        return attempt

    async def delete_attempt(self, db: AsyncSession, attempt_id: UUID) -> bool:
        """Delete an attempt by ID"""
        attempt = await self.get_attempt_by_id(db, attempt_id)
        if not attempt:
            return False

        result = await remove_attempt(db, attempt_id)
        return result

    async def get_user_stats(self, db: AsyncSession, user_id: UUID) -> dict:
        """Get user attempt statistics"""
        # Total attempts
        total_result = await db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.user_id == user_id)
        )
        total_attempts = total_result.scalar() or 0

        # Correct attempts
        correct_result = await db.execute(
            select(func.count(QuestionAttempt.id))
            .where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.is_correct == True,
            )
        )
        correct_attempts = correct_result.scalar() or 0

        # Total marks
        marks_result = await db.execute(
            select(func.sum(QuestionAttempt.marks_obtained))
            .where(QuestionAttempt.user_id == user_id)
        )
        total_marks = marks_result.scalar() or 0

        # Average time
        time_result = await db.execute(
            select(func.avg(QuestionAttempt.time_taken))
            .where(QuestionAttempt.user_id == user_id)
        )
        avg_time = time_result.scalar() or 0

        return {
            "total_attempts": total_attempts,
            "correct_attempts": correct_attempts,
            "incorrect_attempts": total_attempts - correct_attempts,
            "accuracy": (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0,
            "total_marks": total_marks,
            "average_time_seconds": round(avg_time, 2),
        }

    async def has_attempted(self, db: AsyncSession, user_id: UUID, question_id: UUID) -> bool:
        """Check if a user has attempted a specific question"""
        result = await db.execute(
            select(func.count(QuestionAttempt.id))
            .where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.question_id == question_id,
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def get_user_solved_count(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> dict:
        """Get total number of distinct questions solved by a user"""
        result = await db.execute(
            select(func.count(func.distinct(QuestionAttempt.question_id)))
            .where(QuestionAttempt.user_id == user_id)
        )
        count = result.scalar() or 0
        return {"user_id": str(user_id), "total_solved": count}
