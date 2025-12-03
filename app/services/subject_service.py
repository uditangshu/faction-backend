"""Subject service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.question import Subject, Subject_Type
from app.db.question_calls import create_subject, delete_subject, get_nested_subjects


class SubjectService:
    """Service for managing subjects"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subject(self, subject_type: Subject_Type, class_id: UUID) -> Subject:
        """Create a new subject"""
        return await create_subject(self.db, subject_type, class_id)

    async def get_subject_by_id(self, subject_id: UUID) -> Optional[Subject]:
        """Get a single subject by ID"""
        query = select(Subject).where(Subject.id == subject_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_subjects(self) -> List[Subject]:
        """Get all subjects"""
        query = select(Subject)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_subjects_by_class(self, class_id: UUID) -> List[Subject]:
        """Get all subjects for a specific class"""
        query = select(Subject).where(Subject.class_id == class_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_subject_with_chapters(self, subject_id: UUID) -> Optional[Subject]:
        """Get subject with all nested chapters and questions"""
        return await get_nested_subjects(self.db, subject_id)

    async def delete_subject(self, subject_id: UUID) -> bool:
        """Delete a subject by ID"""
        existing = await self.get_subject_by_id(subject_id)
        if not existing:
            return False
        await delete_subject(self.db, subject_id)
        await self.db.commit()
        return True