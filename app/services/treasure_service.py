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


class TreasureService:
    """Service for managing treasures (mindmap images)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_treasure(
        self,
        chapter_id: UUID,
        subject_id: UUID,
        image_url: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        order: int = 0,
    ) -> Treasure:
        """Create a new treasure"""
        return await create_treasure(
            db=self.db,
            chapter_id=chapter_id,
            subject_id=subject_id,
            image_url=image_url,
            title=title,
            description=description,
            order=order,
        )

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
        Get treasures filtered by user's class, optionally by subject and chapter
        
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
        return await get_treasures_by_user_class(
            db=self.db,
            class_id=class_id,
            subject_id=subject_id,
            chapter_id=chapter_id,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )

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

