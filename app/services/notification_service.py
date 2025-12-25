"""Notification service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import List, Optional, Tuple

from app.models.notification import Notification, NotificationType
from app.integrations.redis_client import RedisService


class NotificationService:
    """Service for managing notifications with Redis caching"""

    CACHE_TTL = 60  # 1 minute cache for unread count
    CACHE_PREFIX = "notifications"

    def __init__(self, db: AsyncSession, redis: Optional[RedisService] = None):
        self.db = db
        self.redis = redis

    def _unread_count_key(self, user_id: UUID) -> str:
        return f"{self.CACHE_PREFIX}:unread:{user_id}"

    async def _invalidate_unread_cache(self, user_id: UUID) -> None:
        """Invalidate user's unread count cache"""
        if self.redis:
            await self.redis.delete_key(self._unread_count_key(user_id))

    async def create_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        data: Optional[str] = None,
    ) -> Notification:
        """Create a new notification for a user"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            data=data,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        # Invalidate unread count cache
        await self._invalidate_unread_cache(user_id)
        
        return notification

    async def get_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False,
    ) -> Tuple[List[Notification], int, int]:
        """
        Get notifications for a user with pagination.
        Returns (notifications, total_count, unread_count)
        """
        # Base query
        base_query = select(Notification).where(Notification.user_id == user_id)
        
        # Count total
        total_result = await self.db.execute(
            select(func.count(Notification.id)).where(Notification.user_id == user_id)
        )
        total = total_result.scalar() or 0
        
        # Get unread count (cached)
        unread_count = await self.get_unread_count(user_id)
        
        # Apply unread filter if requested
        if unread_only:
            base_query = base_query.where(Notification.is_read == False)
        
        # Get paginated notifications
        query = (
            base_query
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())
        
        return notifications, total, unread_count

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user (cached)"""
        cache_key = self._unread_count_key(user_id)
        
        # Try cache first
        if self.redis:
            cached = await self.redis.get_key(cache_key)
            if cached is not None:
                return int(cached)
        
        # Query database
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
        )
        count = result.scalar() or 0
        
        # Cache result
        if self.redis:
            await self.redis.set_key(cache_key, str(count), self.CACHE_TTL)
        
        return count

    async def mark_as_read(self, user_id: UUID, notification_id: UUID) -> bool:
        """Mark a single notification as read"""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
            .values(is_read=True)
        )
        await self.db.commit()
        
        # Invalidate cache
        await self._invalidate_unread_cache(user_id)
        
        return result.rowcount > 0

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user"""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            .values(is_read=True)
        )
        await self.db.commit()
        
        # Invalidate cache
        await self._invalidate_unread_cache(user_id)
        
        return result.rowcount

    async def delete_notification(self, user_id: UUID, notification_id: UUID) -> bool:
        """Delete a notification"""
        notification = await self.db.get(Notification, notification_id)
        if notification and notification.user_id == user_id:
            was_unread = not notification.is_read
            await self.db.delete(notification)
            await self.db.commit()
            
            # Invalidate cache if it was unread
            if was_unread:
                await self._invalidate_unread_cache(user_id)
            
            return True
        return False

