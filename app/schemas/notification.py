"""Notification schemas"""

from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    """Response schema for a notification"""
    id: UUID
    user_id: UUID
    title: str
    message: str
    type: NotificationType
    is_read: bool
    data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response schema for paginated notification list"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Response for unread notification count"""
    count: int


class MarkAsReadRequest(BaseModel):
    """Request to mark notifications as read"""
    notification_ids: List[UUID]


class NotificationCreateRequest(BaseModel):
    """Request to create a notification (internal use)"""
    user_id: UUID
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    data: Optional[str] = None
