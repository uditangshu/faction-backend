"""Weak topics service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_
from typing import List, Optional, Tuple

from app.models.weak_topic import UserWeakTopic
from app.models.attempt import QuestionAttempt
from app.models.Basequestion import Question
from app.db.weak_topic_calls import (
    create_user_weak_topic,
    get_user_weak_topic_by_id,
    get_user_weak_topic_by_user_and_topic,
    get_user_weak_topics,
    update_user_weak_topic,
    upsert_user_weak_topic,
    delete_user_weak_topic,
    delete_user_weak_topic_by_user_and_topic,
    delete_all_user_weak_topics,
)


class WeakTopicService:
    """Service for weak topic operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== CRUD Methods ====================

    async def create_weak_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
        total_attempt: int = 0,
        incorrect_attempts: int = 0,
        correct_attempts: int = 0,
        weakness_score: float = 0.0,
    ) -> UserWeakTopic:
        """Create a new user weak topic"""
        return await create_user_weak_topic(
            self.db,
            user_id=user_id,
            topic_id=topic_id,
            total_attempt=total_attempt,
            incorrect_attempts=incorrect_attempts,
            correct_attempts=correct_attempts,
            weakness_score=weakness_score,
        )

    async def get_weak_topic_by_id(
        self,
        weak_topic_id: UUID,
    ) -> Optional[UserWeakTopic]:
        """Get a weak topic by ID"""
        return await get_user_weak_topic_by_id(self.db, weak_topic_id)

    async def get_weak_topic_by_user_and_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> Optional[UserWeakTopic]:
        """Get a weak topic by user_id and topic_id"""
        return await get_user_weak_topic_by_user_and_topic(
            self.db, user_id, topic_id
        )

    async def get_user_weak_topics(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        min_weakness_score: float = 0.0,
    ) -> Tuple[List[UserWeakTopic], int]:
        """Get all weak topics for a user with pagination"""
        return await get_user_weak_topics(
            self.db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            min_weakness_score=min_weakness_score,
        )

    async def update_weak_topic(
        self,
        weak_topic: UserWeakTopic,
    ) -> UserWeakTopic:
        """Update an existing weak topic"""
        return await update_user_weak_topic(self.db, weak_topic)

    async def upsert_weak_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
        total_attempt: int,
        incorrect_attempts: int,
        correct_attempts: int,
        weakness_score: float,
    ) -> UserWeakTopic:
        """Insert or update a weak topic (upsert)"""
        return await upsert_user_weak_topic(
            self.db,
            user_id=user_id,
            topic_id=topic_id,
            total_attempt=total_attempt,
            incorrect_attempts=incorrect_attempts,
            correct_attempts=correct_attempts,
            weakness_score=weakness_score,
        )

    async def delete_weak_topic(
        self,
        weak_topic_id: UUID,
    ) -> bool:
        """Delete a weak topic by ID"""
        return await delete_user_weak_topic(self.db, weak_topic_id)

    async def delete_weak_topic_by_user_and_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> bool:
        """Delete a weak topic by user_id and topic_id"""
        return await delete_user_weak_topic_by_user_and_topic(
            self.db, user_id, topic_id
        )

    async def delete_all_user_weak_topics(
        self,
        user_id: UUID,
    ) -> int:
        """Delete all weak topics for a user"""
        return await delete_all_user_weak_topics(self.db, user_id)

    # ==================== Update Methods ====================

    async def update_weak_topics_from_attempts(
        self,
        user_id: UUID,
    ) -> None:
        """
        Update weak topics based on student attempts.
        Queries all QuestionAttempt records for the user, extracts topic IDs,
        calculates metrics, and updates the weak topics table.
        """
        # Query all attempts grouped by topic with aggregated metrics
        query = (
            select(
                Question.topic_id,
                func.count(QuestionAttempt.id).label('total_attempt'),
                func.sum(
                    case((QuestionAttempt.is_correct == False, 1), else_=0)
                ).label('incorrect_attempts'),
                func.sum(
                    case((QuestionAttempt.is_correct == True, 1), else_=0)
                ).label('correct_attempts'),
            )
            .join(Question, QuestionAttempt.question_id == Question.id)
            .where(QuestionAttempt.user_id == user_id)
            .group_by(Question.topic_id)
        )

        # Execute query
        result = await self.db.execute(query)
        topic_stats = result.all()

        # Update or create weak topic records for each topic
        for row in topic_stats:
            topic_id = row.topic_id
            total_attempt = row.total_attempt or 0
            incorrect_attempts = row.incorrect_attempts or 0
            correct_attempts = row.correct_attempts or 0

            # Calculate weakness score: (incorrect / total) * 100
            if total_attempt > 0:
                weakness_score = round((incorrect_attempts / total_attempt) * 100, 2)
            else:
                weakness_score = 0.0

            # Upsert the weak topic record
            await upsert_user_weak_topic(
                self.db,
                user_id=user_id,
                topic_id=topic_id,
                total_attempt=total_attempt,
                incorrect_attempts=incorrect_attempts,
                correct_attempts=correct_attempts,
                weakness_score=weakness_score,
            )

