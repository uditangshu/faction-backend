"""Class service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.Basequestion import Class, Class_level
from app.db.question_calls import create_class, delete_class, get_nested_class


class ClassService:
    """Service for managing classes"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_class(self, class_level: Class_level) -> Class:
        """Create a new class"""
        return await create_class(self.db, class_level)

    async def get_class_by_id(self, class_id: UUID) -> Optional[Class]:
        """Get a single class by ID"""
        query = select(Class).where(Class.id == class_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_class_with_subjects(self, class_id: UUID) -> Optional[Class]:
        """Get class with all nested subjects, chapters, and questions"""
        return await get_nested_class(self.db, class_id)

    async def get_all_classes(self) -> List[Class]:
        """Get all classes"""
        query = select(Class)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_class(self, class_id: UUID) -> bool:
        """Delete a class by ID"""
        existing = await self.get_class_by_id(class_id)
        if not existing:
            return False
        await delete_class(self.db, class_id=class_id)
        await self.db.commit()
        return True
