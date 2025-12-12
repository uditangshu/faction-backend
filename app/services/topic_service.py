"""Topic service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.Basequestion import Topic
from app.db.question_calls import create_topic, delete_topic, get_nested_topics


class TopicService:
    """Service for managing topics - stateless, accepts db as method parameter"""

    async def create_topic(self, db: AsyncSession, name: str, chapter_id: UUID) -> Topic:
        """Create a new topic"""
        return await create_topic(db, chapter_id, name)

    async def get_topic_by_id(self, db: AsyncSession, topic_id: UUID) -> Optional[Topic]:
        """Get a single topic by ID"""
        query = select(Topic).where(Topic.id == topic_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_topics(self, db: AsyncSession) -> List[Topic]:
        """Get all topics"""
        query = select(Topic)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_topics_by_chapter(self, db: AsyncSession, chapter_id: UUID) -> List[Topic]:
        """Get all topics for a specific chapter"""
        query = select(Topic).where(Topic.chapter_id == chapter_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_topic_with_questions(self, db: AsyncSession, topic_id: UUID) -> Optional[Topic]:
        """Get topic with all its questions"""
        return await get_nested_topics(db, topic_id)

    async def update_topic(
        self,
        db: AsyncSession,
        topic_id: UUID,
        name: Optional[str] = None,
        chapter_id: Optional[UUID] = None,
    ) -> Optional[Topic]:
        """Update a topic"""
        topic = await self.get_topic_by_id(db, topic_id)
        if not topic:
            return None

        if name is not None:
            topic.name = name
        if chapter_id is not None:
            topic.chapter_id = chapter_id

        db.add(topic)
        await db.commit()
        await db.refresh(topic)
        return topic

    async def delete_topic(self, db: AsyncSession, topic_id: UUID) -> bool:
        """Delete a topic by ID"""
        existing = await self.get_topic_by_id(db, topic_id)
        if not existing:
            return False
        await delete_topic(db, topic_id)
        await db.commit()
        return True
