"""Notification endpoints"""

from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import NotificationServiceDep, CurrentUser
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    current_user: CurrentUser,
    notification_service: NotificationServiceDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
) -> NotificationListResponse:
    """Get paginated notifications for the current user"""
    notifications, total, unread_count = await notification_service.get_notifications(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
    )
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: CurrentUser,
    notification_service: NotificationServiceDep,
) -> UnreadCountResponse:
    """Get count of unread notifications"""
    count = await notification_service.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


@router.patch("/{notification_id}/read", status_code=204)
async def mark_as_read(
    notification_id: UUID,
    current_user: CurrentUser,
    notification_service: NotificationServiceDep,
) -> None:
    """Mark a single notification as read"""
    await notification_service.mark_as_read(current_user.id, notification_id)


@router.patch("/read-all", status_code=204)
async def mark_all_as_read(
    current_user: CurrentUser,
    notification_service: NotificationServiceDep,
) -> None:
    """Mark all notifications as read"""
    await notification_service.mark_all_as_read(current_user.id)


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: UUID,
    current_user: CurrentUser,
    notification_service: NotificationServiceDep,
) -> None:
    """Delete a notification"""
    await notification_service.delete_notification(current_user.id, notification_id)
