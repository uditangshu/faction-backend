"""Notification service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import List, Optional, Tuple

from app.models.notification import Notification, NotificationType


class NotificationService:
    """Service for managing notifications"""

    def __init__(self, db: AsyncSession):
        self.db = db

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
        
        # Count unread
        unread_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
        )
        unread_count = unread_result.scalar() or 0
        
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
        """Get count of unread notifications for a user"""
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
        )
        return result.scalar() or 0

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
        return result.rowcount

    async def delete_notification(self, user_id: UUID, notification_id: UUID) -> bool:
        """Delete a notification"""
        notification = await self.db.get(Notification, notification_id)
        if notification and notification.user_id == user_id:
            await self.db.delete(notification)
            await self.db.commit()
            return True
        return False
