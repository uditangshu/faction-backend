"""Subject service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, func, exists
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional

from app.models.Basequestion import Subject, Subject_Type
from app.models.user import TargetExam
from app.db.question_calls import create_subject, delete_subject, get_nested_subjects
from app.integrations.redis_client import RedisService
from app.core.config import settings


class SubjectService:
    """Service for managing subjects"""

    CACHE_PREFIX = "subjects"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    async def create_subject(self, subject_type: Subject_Type, class_id: UUID, exam_type: Optional[List[TargetExam]] = None) -> Subject:
        """Create a new subject"""
        return await create_subject(self.db, subject_type, class_id, exam_type)

    async def get_subject_by_id(self, subject_id: UUID) -> Optional[Subject]:
        """Get a single subject by ID"""
        query = select(Subject).where(Subject.id == subject_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_subjects(self) -> List[Subject]:
        """Get all subjects (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:all"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                subject_ids = [UUID(sid) for sid in cached]
                result = await self.db.execute(
                    select(Subject).where(Subject.id.in_(subject_ids))
                )
                return list(result.scalars().all())
        
        query = select(Subject)
        result = await self.db.execute(query)
        subjects = list(result.scalars().all())
        
        # Cache result
        if self.redis_service:
            subject_ids = [str(s.id) for s in subjects]
            await self.redis_service.set_value(cache_key, subject_ids, expire=settings.CACHE_SHARED)
        
        return subjects

    async def get_subjects_by_class(self, class_id: UUID) -> List[Subject]:
        """Get all subjects for a specific class (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:class:{class_id}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                subject_ids = [UUID(sid) for sid in cached]
                result = await self.db.execute(
                    select(Subject).where(Subject.id.in_(subject_ids))
                )
                return list(result.scalars().all())
        
        query = select(Subject).where(Subject.class_id == class_id)
        result = await self.db.execute(query)
        subjects = list(result.scalars().all())
        
        # Cache result
        if self.redis_service:
            subject_ids = [str(s.id) for s in subjects]
            await self.redis_service.set_value(cache_key, subject_ids, expire=settings.CACHE_SHARED)
        
        return subjects

    async def get_subjects_by_exam_type(self, exam_type: TargetExam) -> List[Subject]:
        """Get all subjects that contain the specified exam type in their exam_type list (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:exam:{exam_type.value}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                subject_ids = [UUID(sid) for sid in cached]
                result = await self.db.execute(
                    select(Subject).where(Subject.id.in_(subject_ids))
                )
                return list(result.scalars().all())
        
        # Query subjects where exam_type JSON array contains the target exam
        # The @> operator checks if the left JSONB array contains the right JSONB value
        # Cast the exam_type column to JSONB and check if it contains an array with the exam_type value
        query = select(Subject).where(
            cast(Subject.exam_type, JSONB).contains(
                func.jsonb_build_array(exam_type.value)
            )
        )
        result = await self.db.execute(query)
        subjects = list(result.scalars().all())
        
        # Cache result
        if self.redis_service:
            subject_ids = [str(s.id) for s in subjects]
            await self.redis_service.set_value(cache_key, subject_ids, expire=settings.CACHE_SHARED)
        
        return subjects

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