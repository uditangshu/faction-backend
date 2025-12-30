"""Chapter service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from typing import List, Optional

from app.models.Basequestion import Chapter, Topic
from app.db.question_calls import create_chaps, delete_chaps, get_nested_chapters
from app.integrations.redis_client import RedisService
from app.core.config import settings


class ChapterService:
    """Service for managing chapters"""

    CACHE_PREFIX = "chapters"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    async def create_chapter(self, name: str, subject_id: UUID) -> Chapter:
        """Create a new chapter"""
        return await create_chaps(self.db, subject_id, name)

    async def get_chapter_by_id(self, chapter_id: UUID) -> Optional[Chapter]:
        """Get a single chapter by ID"""
        query = select(Chapter).where(Chapter.id == chapter_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_chapters(self) -> List[Chapter]:
        """Get all chapters (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:all"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                chapter_ids = [UUID(cid) for cid in cached]
                result = await self.db.execute(
                    select(Chapter).where(Chapter.id.in_(chapter_ids))
                )
                return list(result.scalars().all())
        
        query = select(Chapter)
        result = await self.db.execute(query)
        chapters = list(result.scalars().all())
        
        # Cache result
        if self.redis_service:
            chapter_ids = [str(c.id) for c in chapters]
            await self.redis_service.set_value(cache_key, chapter_ids, expire=settings.CACHE_SHARED)
        
        return chapters

    async def get_chapters_by_subject(self, subject_id: UUID) -> List[Chapter]:
        """Get all chapters for a specific subject (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:subject:{subject_id}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                chapter_ids = [UUID(cid) for cid in cached]
                result = await self.db.execute(
                    select(Chapter).where(Chapter.id.in_(chapter_ids))
                )
                return list(result.scalars().all())
        
        query = select(Chapter).where(Chapter.subject_id == subject_id)
        result = await self.db.execute(query)
        chapters = list(result.scalars().all())
        
        # Cache result
        if self.redis_service:
            chapter_ids = [str(c.id) for c in chapters]
            await self.redis_service.set_value(cache_key, chapter_ids, expire=settings.CACHE_SHARED)
        
        return chapters

    async def get_chapter_with_questions(self, chapter_id: UUID) -> Optional[Chapter]:
        """Get chapter with all its questions"""
        query = select(Chapter).where(
            Chapter.id == chapter_id
        ).options(
            selectinload(Chapter.topics)
                .selectinload(Topic.questions)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_chapter(self, chapter_id: UUID) -> bool:
        """Delete a chapter by ID"""
        existing = await self.get_chapter_by_id(chapter_id)
        if not existing:
            return False
        await delete_chaps(self.db, chapter_id)
        await self.db.commit()
        return True
