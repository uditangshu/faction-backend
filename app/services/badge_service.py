"""Badge service"""

from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.models.badge import Badge, BadgeCategory
from app.models.user_badge import UserBadge
from app.integrations.redis_client import RedisService
from app.core.config import settings

class BadgeService:
    """Service for badge operations"""

    CACHE_PREFIX = "badge"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    def _badge_to_cache_dict(self, badge: Badge, user_badge: Optional[UserBadge] = None) -> dict:
        """Convert badge to cache dict - STRINGS ONLY, no type conversions on read"""
        badge_dict = {
            "id": str(badge.id),
            "name": badge.name,
            "description": badge.description,
            "category": badge.category.value if hasattr(badge.category, 'value') else str(badge.category),
            "icon_url": badge.icon_url,
            "icon_svg": badge.icon_svg,
            "requirement_value": badge.requirement_value,
            "requirement_description": badge.requirement_description,
            "is_active": badge.is_active,
            "created_at": badge.created_at.isoformat() if badge.created_at else None,
            "updated_at": badge.updated_at.isoformat() if badge.updated_at else None,
        }
        if user_badge:
            badge_dict["is_earned"] = True
            badge_dict["earned_at"] = user_badge.earned_at.isoformat() if user_badge.earned_at else None
            badge_dict["progress"] = user_badge.progress
        else:
            badge_dict["is_earned"] = False
            badge_dict["progress"] = 0
        return badge_dict

    async def _get_base_badges_cached(self) -> List[dict]:
        """Get base badges list (shared cache, longer TTL) - returns cached format directly"""
        base_cache_key = f"{self.CACHE_PREFIX}:base"
        
        # FAST PATH: Return cached data directly, ZERO processing
        if self.redis_service:
            cached = await self.redis_service.get_value(base_cache_key)
            if cached is not None:
                return cached  # Return as-is, no type conversions
        
        # Cache miss - fetch from database
        result = await self.db.execute(
            select(Badge)
            .where(Badge.is_active == True)
            .order_by(Badge.created_at.desc())
        )
        badges = result.scalars().all()
        
        # Serialize for cache (strings only)
        base_badges = [
            self._badge_to_cache_dict(badge, None)
            for badge in badges
        ]
        
        # Cache base badges with longer TTL (they change rarely)
        if self.redis_service:
            await self.redis_service.set_value(
                base_cache_key,
                base_badges,
                expire=settings.LONG_TERM_CACHE_TTL  # 1 hour
            )
        
        # Return cache format directly (Pydantic will handle type conversion)
        return base_badges

    async def get_all_badges(self, user_id: Optional[UUID] = None) -> List[dict]:
        """Get all badges, optionally with user progress (optimized for 20ms cache hits)"""
        # If no user, return base badges directly from cache
        if not user_id:
            return await self._get_base_badges_cached()
        
        # User-specific cache key
        cache_key = f"{self.CACHE_PREFIX}:user:{user_id}"
        
        # FAST PATH: Return cached data directly, ZERO processing
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                return cached  # Return as-is, no type conversions, no processing
        
        # Cache miss - get base badges (from cache if available)
        base_badges = await self._get_base_badges_cached()
        
        # Get user badges efficiently (only needed fields)
        user_badges_result = await self.db.execute(
            select(UserBadge.badge_id, UserBadge.earned_at, UserBadge.progress)
            .where(UserBadge.user_id == user_id)
        )
        # Use STRING keys (not UUID) for fast lookup
        user_badges_map = {
            str(row[0]): {
                "earned_at": row[1].isoformat() if row[1] else None,
                "progress": row[2]
            }
            for row in user_badges_result.all()
        }
        
        # Merge user badge data (fast dict lookup, strings only)
        enhanced_badges = []
        for badge_dict in base_badges:
            # Create a copy to avoid mutating cached data
            enhanced = badge_dict.copy()
            badge_id_str = enhanced["id"]  # Already a string from cache
            user_badge_data = user_badges_map.get(badge_id_str)
            
            if user_badge_data:
                enhanced["is_earned"] = True
                enhanced["earned_at"] = user_badge_data["earned_at"]  # Already ISO string
                enhanced["progress"] = user_badge_data["progress"]
            else:
                enhanced["is_earned"] = False
                enhanced["progress"] = 0
            
            enhanced_badges.append(enhanced)
        
        # Cache user-specific result (already in cache format - strings only)
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                enhanced_badges,
                expire=settings.CACHE_SHARED
            )
            
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
        
        # Invalidate cache for this user (badge earned status changed)
        if self.redis_service:
            cache_key = f"{self.CACHE_PREFIX}:user:{user_id}"
            await self.redis_service.delete_key(cache_key)
        
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
        
        # Invalidate all badge caches (new badge added)
        
        return badge

    async def delete_badge(self, badge_id: UUID) -> bool:
        """Delete a badge by ID"""
        badge = await self.get_badge_by_id(badge_id)
        if not badge:
            return False
        
        stmt = delete(Badge).where(Badge.id == badge_id)
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Invalidate all badge caches (badge deleted)
        
        return True

