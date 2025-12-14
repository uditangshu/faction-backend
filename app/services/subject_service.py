"""Subject service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional

from app.models.Basequestion import Subject, Subject_Type
from app.models.user import TargetExam
from app.db.question_calls import create_subject, delete_subject, get_nested_subjects


class SubjectService:
    """Service for managing subjects"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subject(self, subject_type: Subject_Type, class_id: UUID, exam_type: Optional[List[TargetExam]] = None) -> Subject:
        """Create a new subject"""
        return await create_subject(self.db, subject_type, class_id, exam_type)

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

    async def get_subjects_by_exam_type(self, exam_type: TargetExam) -> List[Subject]:
        """Get all subjects that contain the specified exam type in their exam_type list"""
        # Query subjects where exam_type JSON array contains the target exam
        query = select(Subject).where(
            cast(Subject.exam_type, JSONB).contains([exam_type.value])
        )
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