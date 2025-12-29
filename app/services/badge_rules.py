"""Badge Awarding Service with Notification Integration"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.badge_service import BadgeService
from app.services.notification_service import NotificationService
from app.services.push_notification_service import PushNotificationService
from app.models.badge import BadgeCategory
from app.models.notification import NotificationType
from app.models.session import UserSession
import logging

logger = logging.getLogger(__name__)


class BadgeAwardingService:
    """Service to check rules, award badges, and send notifications"""

    # Thresholds for "close to earning" notifications
    STREAK_CLOSE_THRESHOLD = 1  # N-1 days to go
    PRACTICE_CLOSE_THRESHOLD = 10  # 10 questions to go

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.badge_service = BadgeService(db)
        self.notification_service = NotificationService(db, redis)
        self.push_service = PushNotificationService()

    async def _get_user_push_token(self, user_id: UUID) -> str | None:
        """Get active push token for a user"""
        result = await self.db.execute(
            select(UserSession.push_token)
            .where(UserSession.user_id == user_id, UserSession.is_active == True, UserSession.push_token.isnot(None))
            .order_by(UserSession.last_active.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _send_badge_earned_notification(self, user_id: UUID, badge_name: str) -> None:
        """Send notification when a badge is earned"""
        title = "🏆 Badge Earned!"
        message = f"Congratulations! You've earned the '{badge_name}' badge!"
        
        # Create in-app notification
        await self.notification_service.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.ACHIEVEMENT,
            data=f'{{"badge_name": "{badge_name}"}}'
        )
        
        # Send push notification
        push_token = await self._get_user_push_token(user_id)
        if push_token:
            try:
                await self.push_service.send_batch_notifications([{
                    "to": push_token,
                    "sound": "default",
                    "title": title,
                    "body": message,
                    "data": {"type": "BADGE_EARNED", "badge_name": badge_name},
                    "priority": "high",
                    "channelId": "achievements"
                }])
            except Exception as e:
                logger.error(f"Failed to send push notification: {e}")

    async def _send_close_to_earning_notification(
        self, user_id: UUID, badge_name: str, remaining: int, unit: str
    ) -> None:
        """Send notification when user is close to earning a badge"""
        title = "🔥 Almost There!"
        message = f"Just {remaining} {unit} away from earning the '{badge_name}' badge! Keep going!"
        
        # Create in-app notification
        await self.notification_service.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.INFO,
            data=f'{{"badge_name": "{badge_name}", "remaining": {remaining}}}'
        )
        
        # Send push notification
        push_token = await self._get_user_push_token(user_id)
        if push_token:
            try:
                await self.push_service.send_batch_notifications([{
                    "to": push_token,
                    "sound": "default",
                    "title": title,
                    "body": message,
                    "data": {"type": "BADGE_PROGRESS", "badge_name": badge_name, "remaining": remaining},
                    "priority": "default",
                    "channelId": "progress"
                }])
            except Exception as e:
                logger.error(f"Failed to send push notification: {e}")

    async def check_streak_badges(self, user_id: UUID, current_streak: int) -> list[str]:
        """Check and award streak badges, send notifications"""
        awarded = []
        badges = await self.badge_service.get_all_badges(user_id=user_id)
        streak_badges = [b for b in badges if b['category'] == BadgeCategory.STREAK and b['requirement_value']]
        
        for badge_data in streak_badges:
            req_value = badge_data.get('requirement_value')
            badge_id = badge_data.get('id')
            badge_name = badge_data.get('name')
            is_earned = badge_data.get('is_earned')
            
            if is_earned:
                continue
                
            remaining = req_value - current_streak
            
            if remaining <= 0:
                # User earned the badge
                success = await self.badge_service.award_badge(
                    user_id=user_id, 
                    badge_id=badge_id,
                    progress=current_streak
                )
                if success:
                    awarded.append(badge_name)
                    await self._send_badge_earned_notification(user_id, badge_name)
            elif remaining <= self.STREAK_CLOSE_THRESHOLD:
                # User is close to earning
                unit = "day" if remaining == 1 else "days"
                await self._send_close_to_earning_notification(user_id, badge_name, remaining, unit)
                    
        return awarded

    async def check_practice_badges(self, user_id: UUID, total_solved: int) -> list[str]:
        """Check and award practice arena badges, send notifications"""
        awarded = []
        badges = await self.badge_service.get_all_badges(user_id=user_id)
        practice_badges = [b for b in badges if b['category'] == BadgeCategory.PRACTICE_ARENA and b['requirement_value']]
        
        for badge_data in practice_badges:
            req_value = badge_data.get('requirement_value')
            badge_id = badge_data.get('id')
            badge_name = badge_data.get('name')
            is_earned = badge_data.get('is_earned')
            
            if is_earned:
                continue
                
            remaining = req_value - total_solved
            
            if remaining <= 0:
                # User earned the badge
                success = await self.badge_service.award_badge(
                    user_id=user_id, 
                    badge_id=badge_id,
                    progress=total_solved
                )
                if success:
                    awarded.append(badge_name)
                    await self._send_badge_earned_notification(user_id, badge_name)
            elif remaining <= self.PRACTICE_CLOSE_THRESHOLD:
                # User is close to earning
                unit = "question" if remaining == 1 else "questions"
                await self._send_close_to_earning_notification(user_id, badge_name, remaining, unit)
                    
        return awarded
