"""Streak database calls"""

from datetime import date, timedelta
from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.streak import UserStudyStats, UserDailyStreak
from app.models.attempt import QuestionAttempt


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
        select(UserDailyStreak).where(
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

