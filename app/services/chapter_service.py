"""Chapter service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from typing import List, Optional

from app.models.Basequestion import Chapter
from app.db.question_calls import create_chaps, delete_chaps, get_nested_chapters


class ChapterService:
    """Service for managing chapters"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_chapter(self, name: str, subject_id: UUID) -> Chapter:
        """Create a new chapter"""
        return await create_chaps(self.db, subject_id, name)

    async def get_chapter_by_id(self, chapter_id: UUID) -> Optional[Chapter]:
        """Get a single chapter by ID"""
        query = select(Chapter).where(Chapter.id == chapter_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_chapters(self) -> List[Chapter]:
        """Get all chapters"""
        query = select(Chapter)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_chapters_by_subject(self, subject_id: UUID) -> List[Chapter]:
        """Get all chapters for a specific subject"""
        query = select(Chapter).where(Chapter.subject_id == subject_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_chapter_with_questions(self, chapter_id: UUID) -> Optional[Chapter]:
        """Get chapter with all its questions"""
        query = select(Chapter).where(
            Chapter.id == chapter_id
        ).options(
            selectinload(Chapter.questions)
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
