"""Streak database calls"""

from datetime import date, timedelta, datetime
from uuid import UUID
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.models.streak import UserStudyStats, UserDailyStreak
from app.models.attempt import QuestionAttempt
from app.models.user import User


async def get_user_stats(db: AsyncSession, user_id: UUID) -> Optional[UserStudyStats]:
    """Get user study stats"""
    result = await db.execute(
        select(UserStudyStats).where(UserStudyStats.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user_stats(db: AsyncSession, user_id: UUID) -> UserStudyStats:
    """Create user study stats"""
    stats = UserStudyStats(user_id=user_id)
    db.add(stats)
    await db.commit()
    await db.refresh(stats)
    return stats


async def get_or_create_user_stats(db: AsyncSession, user_id: UUID) -> UserStudyStats:
    """Get or create user study stats"""
    stats = await get_user_stats(db, user_id)
    if not stats:
        stats = await create_user_stats(db, user_id)
    return stats


async def update_user_stats(db: AsyncSession, stats: UserStudyStats) -> UserStudyStats:
    """Update user stats"""
    db.add(stats)
    await db.commit()
    await db.refresh(stats)
    return stats


async def get_daily_streak(
    db: AsyncSession, user_id: UUID, streak_date: date
) -> Optional[UserDailyStreak]:
    """Get daily streak for a specific date"""
    result = await db.execute(
        select().where(
            and_(
                UserDailyStreak.user_id == user_id,
                UserDailyStreak.streak_date == streak_date,
            )
        )
    )
    return result.scalar_one_or_none()


async def create_daily_streak(
    db: AsyncSession, user_id: UUID, streak_date: date
) -> UserDailyStreak:
    """Create daily streak"""
    daily_streak = UserDailyStreak(
        user_id=user_id,
        streak_date=streak_date,
        problems_solved=1,
        streak_maintained=True,
    )
    db.add(daily_streak)
    await db.commit()
    await db.refresh(daily_streak)
    return daily_streak


async def update_daily_streak(
    db: AsyncSession, daily_streak: UserDailyStreak
) -> UserDailyStreak:
    """Update daily streak"""
    db.add(daily_streak)
    await db.commit()
    await db.refresh(daily_streak)
    return daily_streak


async def get_daily_streaks_range(
    db: AsyncSession, user_id: UUID, start_date: date, end_date: date
) -> List[UserDailyStreak]:
    """Get daily streaks for a date range"""
    result = await db.execute(
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
    return list(result.scalars().all())


async def count_correct_attempts(db: AsyncSession, user_id: UUID) -> int:
    """Count total correct attempts for a user"""
    result = await db.execute(
        select(func.count(QuestionAttempt.id)).where(
            and_(QuestionAttempt.user_id == user_id, QuestionAttempt.is_correct == True)
        )
    )
    return result.scalar() or 0


async def get_streak_ranking(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
) -> Tuple[List[Tuple[User, int, int]], int]:
    """Get streak ranking sorted by current streak descending with pagination"""
    total_result = await db.execute(
        select(func.count(UserStudyStats.id))
        .join(User, UserStudyStats.user_id == User.id)
        .where(User.is_active == True)
    )
    total = total_result.scalar() or 0
    
    result = await db.execute(
        select(User, UserStudyStats.longest_study_streak, UserStudyStats.current_study_streak)
        .join(UserStudyStats, User.id == UserStudyStats.user_id)
        .where(User.is_active == True)
        .order_by(desc(UserStudyStats.current_study_streak))
        .offset(skip)
        .limit(limit)
    )
    return [(row[0], row[1], row[2]) for row in result.all()], total


async def get_user_with_longest_streak(db: AsyncSession) -> Optional[Tuple[User, int]]:
    """
    Get user with the longest study streak.
    
    Returns:
        Tuple of (User, longest_streak) or None if no users found
    """
    result = await db.execute(
        select(User, UserStudyStats.longest_study_streak)
        .join(UserStudyStats, User.id == UserStudyStats.user_id)
        .where(User.is_active == True)
        .order_by(desc(UserStudyStats.longest_study_streak))
        .limit(1)
    )
    row = result.first()
    if row:
        return (row[0], row[1])
    return None

async def update_streak_on_correct_answer(self, user_id: UUID) -> UserStudyStats:
        """
        Update user streak after a correct answer.

        Args:
            user_id: User UUID

        Returns:
            Updated UserStudyStats
        """
        result = await self.db.execute(select(UserStudyStats).where(UserStudyStats.user_id == user_id))
        stats = result.scalar_one_or_none()

        if not stats:
            stats = UserStudyStats(user_id=user_id)
            self.db.add(stats)
            await self.db.commit()
            await self.db.refresh(stats)

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
        # Note: This is called only when answer is correct, so we can optimize
        # by incrementing a counter instead of counting all attempts every time
        correct_attempts = await self._count_correct_attempts(user_id)
        if stats.total_attempts > 0:
            stats.accuracy_rate = (correct_attempts / stats.total_attempts) * 100

        stats.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(stats)

        return stats
