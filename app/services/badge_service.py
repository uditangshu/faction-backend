"""Badge service"""

from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.models.badge import Badge, BadgeCategory


class BadgeService:
    """Service for badge operations - stateless, accepts db as method parameter"""

    async def get_all_badges(self, db: AsyncSession) -> List[Badge]:
        """Get all badges"""
        result = await db.execute(
            select(Badge).order_by(Badge.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_badge_by_id(self, db: AsyncSession, badge_id: UUID) -> Optional[Badge]:
        """Get badge by ID"""
        result = await db.execute(
            select(Badge).where(Badge.id == badge_id)
        )
        return result.scalar_one_or_none()

    async def create_badge(
        self,
        db: AsyncSession,
        name: str,
        description: str,
        category: BadgeCategory,
        requirement_description: str,
        icon_url: Optional[str] = None,
        icon_svg: Optional[str] = None,
        requirement_value: Optional[int] = None,
        is_active: bool = True,
    ) -> Badge:
        """Create a new badge"""
        badge = Badge(
            name=name,
            description=description,
            category=category,
            icon_url=icon_url,
            icon_svg=icon_svg,
            requirement_value=requirement_value,
            requirement_description=requirement_description,
            is_active=is_active,
        )
        db.add(badge)
        await db.commit()
        await db.refresh(badge)
        return badge

    async def delete_badge(self, db: AsyncSession, badge_id: UUID) -> bool:
        """Delete a badge by ID"""
        badge = await self.get_badge_by_id(db, badge_id)
        if not badge:
            return False
        
        stmt = delete(Badge).where(Badge.id == badge_id)
        await db.execute(stmt)
        await db.commit()
        return True
