"""Class service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.Basequestion import Class
from app.db.question_calls import create_class, delete_class, get_nested_class
from app.integrations.redis_client import RedisService
from app.core.config import settings


class ClassService:
    """Service for managing classes"""

    CACHE_PREFIX = "classes"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    async def create_class(self, name: str) -> Class:
        """Create a new class"""
        return await create_class(self.db, name)

    async def get_class_by_id(self, class_id: UUID) -> Optional[Class]:
        """Get a single class by ID"""
        query = select(Class).where(Class.id == class_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_class_with_subjects(self, class_id: UUID) -> Optional[Class]:
        """Get class with all nested subjects (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:{class_id}:subjects"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                # Return from DB using cached class_id
                return await get_nested_class(self.db, class_id)
        
        result = await get_nested_class(self.db, class_id)
        
        # Cache result (cache the class_id for quick lookup)
        if self.redis_service and result:
            await self.redis_service.set_value(cache_key, str(class_id), expire=settings.CACHE_SHARED)
        
        return result

    async def get_all_classes(self) -> List[Class]:
        """Get all classes (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:all"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                class_ids = [UUID(cid) for cid in cached]
                result = await self.db.execute(
                    select(Class).where(Class.id.in_(class_ids))
                )
                return list(result.scalars().all())
        
        query = select(Class)
        result = await self.db.execute(query)
        classes = list(result.scalars().all())
        
        # Cache result
        if self.redis_service:
            class_ids = [str(c.id) for c in classes]
            await self.redis_service.set_value(cache_key, class_ids, expire=settings.CACHE_SHARED)
        
        return classes

    async def delete_class(self, class_id: UUID) -> bool:
        """Delete a class by ID"""
        existing = await self.get_class_by_id(class_id)
        if not existing:
            return False
        await delete_class(self.db, class_id=class_id)
        await self.db.commit()
        return True
