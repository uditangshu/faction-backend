"""Chapter service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from typing import List, Optional

from app.models.Basequestion import Chapter, Topic
from app.db.question_calls import create_chaps, delete_chaps, get_nested_chapters


class ChapterService:
    """Service for managing chapters - stateless, accepts db as method parameter"""

    async def create_chapter(self, db: AsyncSession, name: str, subject_id: UUID) -> Chapter:
        """Create a new chapter"""
        return await create_chaps(db, subject_id, name)

    async def get_chapter_by_id(self, db: AsyncSession, chapter_id: UUID) -> Optional[Chapter]:
        """Get a single chapter by ID"""
        query = select(Chapter).where(Chapter.id == chapter_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_chapters(self, db: AsyncSession) -> List[Chapter]:
        """Get all chapters"""
        query = select(Chapter)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_chapters_by_subject(self, db: AsyncSession, subject_id: UUID) -> List[Chapter]:
        """Get all chapters for a specific subject"""
        query = select(Chapter).where(Chapter.subject_id == subject_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_chapter_with_questions(self, db: AsyncSession, chapter_id: UUID) -> Optional[Chapter]:
        """Get chapter with all its questions"""
        query = select(Chapter).where(
            Chapter.id == chapter_id
        ).options(
            selectinload(Chapter.topics)
                .selectinload(Topic.questions)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def delete_chapter(self, db: AsyncSession, chapter_id: UUID) -> bool:
        """Delete a chapter by ID"""
        existing = await self.get_chapter_by_id(db, chapter_id)
        if not existing:
            return False
        await delete_chaps(db, chapter_id)
        await db.commit()
        return True
