"""Notes service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.models.notes import Notes
from app.db.notes_calls import (
    create_note,
    delete_note,
    get_note_by_id,
    get_notes_by_user_class,
)
from app.integrations.redis_client import RedisService
from app.core.config import settings


class NotesService:
    """Service for managing notes (PDF files)"""

    CACHE_PREFIX = "notes"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    async def create_note(
        self,
        chapter_id: UUID,
        subject_id: UUID,
        file_name: str,
        file_id: str,
        web_view_link: str,
        web_content_link: Optional[str] = None,
    ) -> Notes:
        """Create a new note and invalidate related caches"""
        note = await create_note(
            db=self.db,
            chapter_id=chapter_id,
            subject_id=subject_id,
            file_name=file_name,
            file_id=file_id,
            web_view_link=web_view_link,
            web_content_link=web_content_link,
        )
        
        # Invalidate all notes caches for this class/subject/chapter
        if self.redis_service:
            await self._invalidate_notes_cache()
        
        return note
    
    async def _invalidate_notes_cache(self):
        """Invalidate all notes caches by deleting all keys matching the pattern"""
        if not self.redis_service:
            return
        
        # Use Redis SCAN to find and delete all keys matching notes:*
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

    async def get_note_by_id(self, note_id: UUID) -> Optional[Notes]:
        """Get a note by ID"""
        return await get_note_by_id(self.db, note_id)

    async def delete_note(self, note_id: UUID) -> bool:
        """Delete a note"""
        return await delete_note(self.db, note_id)

    async def get_notes_by_user_class(
        self,
        class_id: UUID,
        subject_id: Optional[UUID] = None,
        chapter_id: Optional[UUID] = None,
        sort_order: str = "latest",
        skip: int = 0,
        limit: int = 100,
    ) -> List[Notes]:
        """
        Get notes filtered by user's class, optionally by subject and chapter (cached globally)
        
        Args:
            class_id: User's class ID
            subject_id: Optional subject ID to filter by
            chapter_id: Optional chapter ID to filter by
            sort_order: "latest" for newest first, "oldest" for oldest first
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of notes
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
                note_ids = [UUID(nid) for nid in cached]
                if note_ids:
                    from sqlalchemy import select
                    result = await self.db.execute(
                        select(Notes).where(Notes.id.in_(note_ids))
                    )
                    notes = list(result.scalars().all())
                    # Sort based on sort_order
                    if sort_order == "latest":
                        notes.sort(key=lambda n: n.created_at, reverse=True)
                    else:
                        notes.sort(key=lambda n: n.created_at)
                    return notes
                return []
        
        # Fetch from database
        notes = await get_notes_by_user_class(
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
            note_ids = [str(n.id) for n in notes]
            await self.redis_service.set_value(
                cache_key,
                note_ids,
                expire=settings.LONG_TERM_CACHE_TTL
            )
        
        return notes

