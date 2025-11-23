"""Question database calls"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.question import Question, QuestionOption


async def get_question_by_id(db: AsyncSession, question_id: UUID) -> Optional[Question]:
    """Get question by ID"""
    result = await db.execute(
        select(Question).where(Question.id == question_id, Question.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_questions(
    db: AsyncSession,
    subject_id: Optional[UUID] = None,
    topic_id: Optional[UUID] = None,
    difficulty_level: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[Question]:
    """Get questions with filters"""
    query = select(Question).where(Question.is_active == True)

    if subject_id:
        query = query.where(Question.subject_id == subject_id)
    if topic_id:
        query = query.where(Question.topic_id == topic_id)
    if difficulty_level:
        query = query.where(Question.difficulty_level == difficulty_level)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_question_options(db: AsyncSession, question_id: UUID) -> List[QuestionOption]:
    """Get options for a question"""
    result = await db.execute(
        select(QuestionOption)
        .where(QuestionOption.question_id == question_id)
        .order_by(QuestionOption.option_order)
    )
    return list(result.scalars().all())


async def increment_question_stats(
    db: AsyncSession, question_id: UUID, is_correct: bool
) -> None:
    """Increment question statistics"""
    question = await get_question_by_id(db, question_id)
    if question:
        question.attempt_count += 1
        if is_correct:
            question.solved_count += 1
        db.add(question)
        await db.commit()

