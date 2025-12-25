"""Notification endpoints"""

from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import NotificationServiceDep, CurrentUser, DBSession
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    AdminNotificationRequest,
    BroadcastNotificationRequest,
    AdminNotificationResponse,
)
from app.models.notification import NotificationType

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


# ========== Admin Endpoints ==========

@router.post("/admin/send", response_model=AdminNotificationResponse)
async def admin_send_notification(
    request: AdminNotificationRequest,
    notification_service: NotificationServiceDep,
) -> AdminNotificationResponse:
    """
    [ADMIN] Send notification to specific users.
    
    Use this to send targeted notifications to selected users.
    """
    sent_count = 0
    for user_id in request.user_ids:
        try:
            await notification_service.create_notification(
                user_id=user_id,
                title=request.title,
                message=request.message,
                notification_type=request.type,
                data=request.data,
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send notification to {user_id}: {e}")
    
    return AdminNotificationResponse(
        success=sent_count > 0,
        sent_count=sent_count,
        message=f"Sent {sent_count}/{len(request.user_ids)} notifications",
    )


@router.post("/admin/broadcast", response_model=AdminNotificationResponse)
async def admin_broadcast_notification(
    request: BroadcastNotificationRequest,
    notification_service: NotificationServiceDep,
    db: DBSession,
) -> AdminNotificationResponse:
    """
    [ADMIN] Broadcast notification to ALL users.
    
    Use sparingly - this sends to every user in the system.
    """
    from sqlalchemy import select
    from app.models.user import User
    
    # Get all user IDs
    result = await db.execute(select(User.id))
    user_ids = [row[0] for row in result.all()]
    
    sent_count = 0
    for user_id in user_ids:
        try:
            await notification_service.create_notification(
                user_id=user_id,
                title=request.title,
                message=request.message,
                notification_type=request.type,
                data=request.data,
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send broadcast to {user_id}: {e}")
    
    return AdminNotificationResponse(
        success=sent_count > 0,
        sent_count=sent_count,
        message=f"Broadcast sent to {sent_count}/{len(user_ids)} users",
    )

