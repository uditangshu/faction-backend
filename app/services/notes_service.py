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


class NotesService:
    """Service for managing notes (PDF files)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_note(
        self,
        chapter_id: UUID,
        subject_id: UUID,
        file_name: str,
        file_id: str,
        web_view_link: str,
        web_content_link: Optional[str] = None,
    ) -> Notes:
        """Create a new note"""
        return await create_note(
            db=self.db,
            chapter_id=chapter_id,
            subject_id=subject_id,
            file_name=file_name,
            file_id=file_id,
            web_view_link=web_view_link,
            web_content_link=web_content_link,
        )

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
        Get notes filtered by user's class, optionally by subject and chapter
        
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
        return await get_notes_by_user_class(
            db=self.db,
            class_id=class_id,
            subject_id=subject_id,
            chapter_id=chapter_id,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )

