"""Class service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.Basequestion import Class, Class_level
from app.db.question_calls import create_class, delete_class, get_nested_class


class ClassService:
    """Service for managing classes - stateless, accepts db as method parameter"""

    async def create_class(self, db: AsyncSession, class_level: Class_level) -> Class:
        """Create a new class"""
        return await create_class(db, class_level)

    async def get_class_by_id(self, db: AsyncSession, class_id: UUID) -> Optional[Class]:
        """Get a single class by ID"""
        query = select(Class).where(Class.id == class_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_class_with_subjects(self, db: AsyncSession, class_id: UUID) -> Optional[Class]:
        """Get class with all nested subjects"""
        return await get_nested_class(db, class_id)

    async def get_all_classes(self, db: AsyncSession) -> List[Class]:
        """Get all classes"""
        query = select(Class)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def delete_class(self, db: AsyncSession, class_id: UUID) -> bool:
        """Delete a class by ID"""
        existing = await self.get_class_by_id(db, class_id)
        if not existing:
            return False
        await delete_class(db, class_id=class_id)
        await db.commit()
        return True
