"""Question bank service"""

import json
from asyncio import gather
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional, Tuple

from app.models.question import Question, QuestionOption, QuestionType
from app.models.attempt import QuestionAttempt
from app.models.subject import Subject, Topic
from app.utils.exceptions import NotFoundException


class QOTDService:
    """Service for question operations"""
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_questions(
        self,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        difficulty_level: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Question]:    
        """
        Get list of questions with filters.

        Args:
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

        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    