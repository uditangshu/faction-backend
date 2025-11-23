"""Question attempt database calls"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import QuestionAttempt


async def create_attempt(
    db: AsyncSession,
    user_id: UUID,
    question_id: UUID,
    user_answer: str,
    is_correct: bool,
    marks_obtained: int,
    time_taken: int,
) -> QuestionAttempt:
    """Create a new question attempt"""
    attempt = QuestionAttempt(
        user_id=user_id,
        question_id=question_id,
        user_answer=user_answer,
        is_correct=is_correct,
        marks_obtained=marks_obtained,
        time_taken=time_taken,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt

