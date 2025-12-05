"""Topic service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.Basequestion import Topic
from app.db.question_calls import create_topic, delete_topic, get_nested_topics


class TopicService:
    """Service for managing topics"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_topic(self, name: str, chapter_id: UUID) -> Topic:
        """Create a new topic"""
        return await create_topic(self.db, chapter_id, name)

    async def get_topic_by_id(self, topic_id: UUID) -> Optional[Topic]:
        """Get a single topic by ID"""
        query = select(Topic).where(Topic.id == topic_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_topics(self) -> List[Topic]:
        """Get all topics"""
        query = select(Topic)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_topics_by_chapter(self, chapter_id: UUID) -> List[Topic]:
        """Get all topics for a specific chapter"""
        query = select(Topic).where(Topic.chapter_id == chapter_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_topic_with_questions(self, topic_id: UUID) -> Optional[Topic]:
        """Get topic with all its questions"""
        return await get_nested_topics(self.db, topic_id)

    async def update_topic(
        self,
        topic_id: UUID,
        name: Optional[str] = None,
        chapter_id: Optional[UUID] = None,
    ) -> Optional[Topic]:
        """Update a topic"""
        topic = await self.get_topic_by_id(topic_id)
        if not topic:
            return None

        if name is not None:
            topic.name = name
        if chapter_id is not None:
            topic.chapter_id = chapter_id

        self.db.add(topic)
        await self.db.commit()
        await self.db.refresh(topic)
        return topic

    async def delete_topic(self, topic_id: UUID) -> bool:
        """Delete a topic by ID"""
        existing = await self.get_topic_by_id(topic_id)
        if not existing:
            return False
        await delete_topic(self.db, topic_id)
        await self.db.commit()
        return True

