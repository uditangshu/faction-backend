"""Study streak calculation service"""

from datetime import datetime, date, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Dict, Any

from app.models.streak import UserStudyStats, UserDailyStreak
from app.models.attempt import QuestionAttempt


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

    async def update_streak_on_correct_answer(self, user_id: UUID) -> UserStudyStats:
        """
        Update user streak after a correct answer.

        Args:
            user_id: User UUID

        Returns:
            Updated UserStudyStats
        """
        stats = await self.get_or_create_user_stats(user_id)
        today = date.today()

        # Get or create today's streak record
        result = await self.db.execute(
            select(UserDailyStreak).where(
                and_(UserDailyStreak.user_id == user_id, UserDailyStreak.streak_date == today)
            )
        )
        daily_streak = result.scalar_one_or_none()

        if not daily_streak:
            daily_streak = UserDailyStreak(
                user_id=user_id,
                streak_date=today,
                problems_solved=1,
                first_solve_time=datetime.utcnow(),
                last_solve_time=datetime.utcnow(),
                streak_maintained=True,
            )
            self.db.add(daily_streak)

            # Update streak count
            if stats.last_study_date == today - timedelta(days=1):
                # Consecutive day
                stats.current_study_streak += 1
            elif stats.last_study_date != today:
                # Streak broken, start new
                stats.current_study_streak = 1

            stats.last_study_date = today
        else:
            # Update existing daily streak
            daily_streak.problems_solved += 1
            daily_streak.last_solve_time = datetime.utcnow()

        # Update overall stats
        stats.questions_solved += 1
        stats.total_attempts += 1

        # Update longest streak
        if stats.current_study_streak > stats.longest_study_streak:
            stats.longest_study_streak = stats.current_study_streak

        # Recalculate accuracy
        correct_attempts = await self._count_correct_attempts(user_id)
        if stats.total_attempts > 0:
            stats.accuracy_rate = (correct_attempts / stats.total_attempts) * 100

        stats.updated_at = datetime.utcnow()

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
        end_date = date.today()
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

        return {
            "current_streak": stats.current_study_streak,
            "longest_streak": stats.longest_study_streak,
            "last_study_date": stats.last_study_date.isoformat() if stats.last_study_date else None,
            "streak_active": stats.last_study_date == date.today()
            or stats.last_study_date == date.today() - timedelta(days=1),
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

