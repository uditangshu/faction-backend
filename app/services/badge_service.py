"""Badge service"""

from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.models.badge import Badge, BadgeCategory
from app.models.user_badge import UserBadge

class BadgeService:
    """Service for badge operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_badges(self, user_id: Optional[UUID] = None) -> List[dict]:
        """Get all badges, optionally with user progress"""
        # Get all badges
        result = await self.db.execute(
            select(Badge).order_by(Badge.created_at.desc())
        )
        badges = result.scalars().all()
        
        # If no user, return badges as is (with default unearned status)
        if not user_id:
            return badges
            
        # Get user earned badges
        user_badges_result = await self.db.execute(
            select(UserBadge).where(UserBadge.user_id == user_id)
        )
        user_badges_map = {ub.badge_id: ub for ub in user_badges_result.scalars().all()}
        
        # Merge data
        enhanced_badges = []
        for badge in badges:
            user_badge = user_badges_map.get(badge.id)
            badge_dict = badge.model_dump()
            
            if user_badge:
                badge_dict["is_earned"] = True
                badge_dict["earned_at"] = user_badge.earned_at
                badge_dict["progress"] = user_badge.progress
            else:
                badge_dict["is_earned"] = False
                badge_dict["progress"] = 0
                
            enhanced_badges.append(badge_dict)
            
        return enhanced_badges

    async def award_badge(self, user_id: UUID, badge_id: UUID, progress: int = 100) -> bool:
        """Award a badge to a user if not already earned"""
        # Check if already earned
        existing = await self.db.execute(
            select(UserBadge).where(
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge_id
            )
        )
        if existing.scalar_one_or_none():
            return False
            
        # Award badge
        user_badge = UserBadge(
            user_id=user_id,
            badge_id=badge_id,
            progress=progress,
            earned_at=datetime.utcnow(),
            is_seen=False
        )
        self.db.add(user_badge)
        await self.db.commit()
        return True

    async def get_badge_by_id(self, badge_id: UUID) -> Optional[Badge]:
        """Get badge by ID"""
        result = await self.db.execute(
            select(Badge).where(Badge.id == badge_id)
        )
        return result.scalar_one_or_none()

    async def create_badge(
        self,
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
        self.db.add(badge)
        await self.db.commit()
        await self.db.refresh(badge)
        return badge

    async def delete_badge(self, badge_id: UUID) -> bool:
        """Delete a badge by ID"""
        badge = await self.get_badge_by_id(badge_id)
        if not badge:
            return False
        
        stmt = delete(Badge).where(Badge.id == badge_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

