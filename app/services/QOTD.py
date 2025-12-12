"""Question bank service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.Basequestion import Question


class QOTDService:
    """Service for question operations - stateless, accepts db as method parameter"""
    
    async def get_questions(
        self,
        db: AsyncSession,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        difficulty_level: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Question]:    
        """
        Get list of questions with filters.

        Args:
            db: Database session
            subject_id: Filter by subject
            topic_id: Filter by topic
            difficulty_level: Filter by difficulty (1-5)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of questions
        """
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
