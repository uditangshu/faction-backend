"""Notification schemas"""

from uuid import UUID
from pydantic import BaseModel, Field
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


class AdminNotificationRequest(BaseModel):
    """Admin request to send notification to specific user(s)"""
    user_ids: List[UUID] = Field(..., description="List of user IDs to send notification to")
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1000)
    type: NotificationType = Field(default=NotificationType.INFO)
    data: Optional[str] = Field(None, description="Optional JSON metadata")


class BroadcastNotificationRequest(BaseModel):
    """Admin request to broadcast notification to all users"""
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1000)
    type: NotificationType = Field(default=NotificationType.ANNOUNCEMENT)
    data: Optional[str] = Field(None, description="Optional JSON metadata")


class AdminNotificationResponse(BaseModel):
    """Response after sending admin notification"""
    success: bool
    sent_count: int
    message: str

