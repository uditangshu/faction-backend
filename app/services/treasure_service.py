"""Treasure service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.models.treasure import Treasure
from app.db.treasure_calls import (
    create_treasure,
    delete_treasure,
    get_treasure_by_id,
    get_treasures_by_subject,
    get_treasures_by_chapter,
    get_treasures_by_user_class,
    update_treasure,
)
from app.integrations.redis_client import RedisService
from app.core.config import settings


class TreasureService:
    """Service for managing treasures (mindmap images)"""

    CACHE_PREFIX = "treasures"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    async def create_treasure(
        self,
        chapter_id: UUID,
        subject_id: UUID,
        image_url: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        order: int = 0,
    ) -> Treasure:
        """Create a new treasure and invalidate related caches"""
        treasure = await create_treasure(
            db=self.db,
            chapter_id=chapter_id,
            subject_id=subject_id,
            image_url=image_url,
            title=title,
            description=description,
            order=order,
        )
        
        # Invalidate all treasures caches
        if self.redis_service:
            await self._invalidate_treasures_cache()
        
        return treasure
    
    async def _invalidate_treasures_cache(self):
        """Invalidate all treasures caches by deleting all keys matching the pattern"""
        if not self.redis_service:
            return
        
        # Use Redis SCAN to find and delete all keys matching treasures:*
        # This is more efficient than deleting individual keys
        cursor = 0
        pattern = f"{self.CACHE_PREFIX}:*"
        deleted_count = 0
        
        while True:
            # SCAN returns (cursor, [keys])
            cursor, keys = await self.redis_service.client.scan(cursor, match=pattern, count=100)
            
            if keys:
                # Delete all matching keys
                deleted = await self.redis_service.client.delete(*keys)
                deleted_count += deleted
            
            if cursor == 0:
                break

    async def get_treasure_by_id(self, treasure_id: UUID) -> Optional[Treasure]:
        """Get a treasure by ID"""
        return await get_treasure_by_id(self.db, treasure_id)

    async def delete_treasure(self, treasure_id: UUID) -> bool:
        """Delete a treasure"""
        return await delete_treasure(self.db, treasure_id)

    async def get_treasures_by_subject(
        self,
        subject_id: UUID,
        chapter_id: Optional[UUID] = None,
    ) -> List[Treasure]:
        """Get all treasures for a subject, optionally filtered by chapter"""
        return await get_treasures_by_subject(
            self.db,
            subject_id,
            chapter_id=chapter_id,
        )

    async def get_treasures_by_chapter(self, chapter_id: UUID) -> List[Treasure]:
        """Get all treasures for a chapter"""
        return await get_treasures_by_chapter(self.db, chapter_id)

    async def get_treasures_by_user_class(
        self,
        class_id: UUID,
        subject_id: Optional[UUID] = None,
        chapter_id: Optional[UUID] = None,
        sort_order: str = "latest",
        skip: int = 0,
        limit: int = 100,
    ) -> List[Treasure]:
        """
        Get treasures filtered by user's class, optionally by subject and chapter (cached globally)
        
        Args:
            class_id: User's class ID
            subject_id: Optional subject ID to filter by
            chapter_id: Optional chapter ID to filter by
            sort_order: "latest" for newest first, "oldest" for oldest first
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of treasures
        """
        # Build cache key from all filter parameters
        cache_key_parts = [
            self.CACHE_PREFIX,
            str(class_id),
            str(subject_id) if subject_id else "all",
            str(chapter_id) if chapter_id else "all",
            sort_order,
            str(skip),
            str(limit),
        ]
        cache_key = ":".join(cache_key_parts)
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                treasure_ids = [UUID(tid) for tid in cached]
                if treasure_ids:
                    from sqlalchemy import select
                    result = await self.db.execute(
                        select(Treasure).where(Treasure.id.in_(treasure_ids))
                    )
                    treasures = list(result.scalars().all())
                    # Sort based on sort_order
                    if sort_order == "latest":
                        treasures.sort(key=lambda t: t.created_at, reverse=True)
                    else:
                        treasures.sort(key=lambda t: t.created_at)
                    return treasures
                return []
        
        # Fetch from database
        treasures = await get_treasures_by_user_class(
            db=self.db,
            class_id=class_id,
            subject_id=subject_id,
            chapter_id=chapter_id,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )
        
        # Cache result
        if self.redis_service:
            treasure_ids = [str(t.id) for t in treasures]
            await self.redis_service.set_value(
                cache_key,
                treasure_ids,
                expire=settings.LONG_TERM_CACHE_TTL
            )
        
        return treasures

    async def update_treasure(
        self,
        treasure_id: UUID,
        image_url: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        order: Optional[int] = None,
        is_active: Optional[bool] = None,
        chapter_id: Optional[UUID] = None,
        subject_id: Optional[UUID] = None,
    ) -> Optional[Treasure]:
        """Update a treasure"""
        return await update_treasure(
            db=self.db,
            treasure_id=treasure_id,
            image_url=image_url,
            title=title,
            description=description,
            order=order,
            is_active=is_active,
            chapter_id=chapter_id,
            subject_id=subject_id,
        )

