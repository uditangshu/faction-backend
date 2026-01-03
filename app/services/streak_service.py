"""Study streak calculation service"""

from datetime import datetime, date, timedelta, time
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Dict, Any

from app.models.streak import UserStudyStats, UserDailyStreak
from app.models.attempt import QuestionAttempt
from app.models.attempt import QuestionAttempt
from app.models.user import User
from app.models.qotd import QOTD
from app.services.badge_rules import BadgeAwardingService


async def is_question_from_qotd(
    db: AsyncSession,
    question_id: UUID,
    class_id: UUID,
    timezone_offset: int
) -> bool:
    """
    Quick check if a question is from today's QOTD for the given class.
    
    Args:
        db: Database session
        question_id: Question ID to check
        class_id: User's class ID
        timezone_offset: User's timezone offset in minutes from UTC
    
    Returns:
        True if question is from today's QOTD, False otherwise
    """
    # Calculate today's start in UTC
    utc_now = datetime.utcnow()
    user_local_date = (utc_now + timedelta(minutes=timezone_offset)).date()
    today_start_utc = datetime.combine(user_local_date, time(0, 0, 0)) - timedelta(minutes=timezone_offset)
    
    # Get today's QOTD for this class
    qotd_result = await db.execute(
        select(QOTD)
        .where(and_(QOTD.class_id == class_id, QOTD.created_at >= today_start_utc))
        .order_by(QOTD.created_at.desc())
        .limit(1)
    )
    qotd = qotd_result.scalar_one_or_none()
    
    if not qotd or not qotd.questions:
        return False
    
    # Check if question_id exists in QOTD questions
    question_id_str = str(question_id)
    return any(str(q.get("id", "")) == question_id_str for q in qotd.questions)


class StreakService:
    """Service for streak calculations and calendar generation"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_user_stats(self, user_id: UUID) -> UserStudyStats:
        """Get or create user study stats"""
        result = await self.db.execute(select(UserStudyStats).where(UserStudyStats.user_id == user_id))
        stats = result.scalar_one_or_none()

        if not stats:
            stats = UserStudyStats(user_id=user_id)
            self.db.add(stats)
            await self.db.commit()
            await self.db.refresh(stats)

        return stats

    async def _count_correct_attempts(self, user_id: UUID) -> int:
        """Count total correct attempts for a user"""
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id)).where(
                and_(QuestionAttempt.user_id == user_id, QuestionAttempt.is_correct == True)
            )
        )
        return result.scalar() or 0

    async def get_study_calendar(self, user_id: UUID, days: int = 365) -> Dict[str, Any]:
        """
        Generate GitHub-style study calendar.

        Args:
            user_id: User UUID
            days: Number of days to include (default 365)

        Returns:
            Dict with calendar data and summary
        """
        # Get user's timezone offset
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        timezone_offset = user.timezone_offset if user else 330  # Default to IST
        
        # Calculate user's local date (UTC + offset)
        utc_now = datetime.utcnow()
        user_local_time = utc_now + timedelta(minutes=timezone_offset)
        end_date = user_local_time.date()  # Use user's local date
        start_date = end_date - timedelta(days=days - 1)

        # Get daily streaks for the period
        result = await self.db.execute(
            select(UserDailyStreak)
            .where(
                and_(
                    UserDailyStreak.user_id == user_id,
                    UserDailyStreak.streak_date >= start_date,
                    UserDailyStreak.streak_date <= end_date,
                )
            )
            .order_by(UserDailyStreak.streak_date)
        )
        daily_streaks = result.scalars().all()

        # Build calendar data
        calendar_data = {}
        total_questions = 0
        active_days = 0

        for streak in daily_streaks:
            date_str = streak.streak_date.isoformat()
            count = streak.problems_solved
            total_questions += count
            active_days += 1

            # Calculate intensity level (0-4) like GitHub contributions
            if count == 0:
                level = 0
            elif count <= 3:
                level = 1
            elif count <= 6:
                level = 2
            elif count <= 10:
                level = 3
            else:
                level = 4

            calendar_data[date_str] = {"count": count, "level": level}

        # Fill in missing dates with zero activity
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            if date_str not in calendar_data:
                calendar_data[date_str] = {"count": 0, "level": 0}
            current_date += timedelta(days=1)

        # Calculate average
        avg_per_day = total_questions / days if days > 0 else 0

        return {
            "year": end_date.year,
            "data": calendar_data,
            "summary": {
                "total_days": days,
                "active_days": active_days,
                "total_questions": total_questions,
                "average_per_day": round(avg_per_day, 2),
            },
        }

    async def get_user_streak_info(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get user's current streak information.

        Args:
            user_id: User UUID

        Returns:
            Dict with streak information
        """
        stats = await self.get_or_create_user_stats(user_id)
        
        # Get user's timezone offset for streak_active calculation
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        timezone_offset = user.timezone_offset if user else 330
        
        # Calculate user's local date
        utc_now = datetime.utcnow()
        user_local_time = utc_now + timedelta(minutes=timezone_offset)
        user_local_date = user_local_time.date()
        yesterday_date = user_local_date - timedelta(days=1)

        return {
            "current_streak": stats.current_study_streak,
            "longest_streak": stats.longest_study_streak,
            "last_study_date": stats.last_study_date.isoformat() if stats.last_study_date else None,
            "streak_active": stats.last_study_date == user_local_date or stats.last_study_date == yesterday_date if stats.last_study_date else False,
            "next_milestone": self._calculate_next_milestone(stats.current_study_streak),
            "total_questions_solved": stats.questions_solved,
            "accuracy_rate": round(stats.accuracy_rate, 2),
        }

    def _calculate_next_milestone(self, current_streak: int) -> int:
        """Calculate next streak milestone"""
        milestones = [7, 15, 30, 50, 100, 200, 365]
        for milestone in milestones:
            if current_streak < milestone:
                return milestone
        return current_streak + 100  # After 365, increment by 100

