"""Streak database calls"""

from datetime import date, timedelta, datetime
from uuid import UUID
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, cast, or_
from sqlalchemy.dialects.postgresql import JSONB

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
    class_id: Optional[UUID] = None,
    exam_type: Optional[str] = None,
) -> Tuple[List[Tuple[User, int, int]], int]:
    """
    Get streak ranking sorted by current streak descending with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        class_id: Optional class ID to filter users by class
        exam_type: Optional target exam type to filter users by matching exam
    
    Returns:
        Tuple of (List of tuples (User, longest_streak, current_streak), total_count)
    """
    # Build user filter conditions
    user_filters = [User.is_active == True]
    
    # Filter by class_id if provided
    if class_id is not None:
        user_filters.append(User.class_id == class_id)
    
    # Filter by exam_type if provided
    if exam_type:
        # Check if the exam_type exists in the user's target_exams array
        # Using JSONB contains operator to check for the exam type
        user_filters.append(cast(User.target_exams, JSONB).contains([exam_type]))
    
    total_result = await db.execute(
        select(func.count(UserStudyStats.id))
        .join(User, UserStudyStats.user_id == User.id)
        .where(and_(*user_filters))
    )
    total = total_result.scalar() or 0
    
    result = await db.execute(
        select(User, UserStudyStats.longest_study_streak, UserStudyStats.current_study_streak)
        .join(UserStudyStats, User.id == UserStudyStats.user_id)
        .where(and_(*user_filters))
        .order_by(desc(UserStudyStats.current_study_streak))
        .offset(skip)
        .limit(limit)
    )
    return [(row[0], row[1], row[2]) for row in result.all()], total


async def get_user_streak_rank(
    db: AsyncSession,
    user_id: UUID,
    class_id: Optional[UUID] = None,
    exam_type: Optional[str] = None,
) -> Tuple[Optional[int], Optional[Tuple[User, int, int]]]:
    """Get user's streak rank efficiently. Returns (rank, user_data)."""
    from app.models.streak import UserStudyStats
    
    filters = [User.is_active == True]
    if class_id:
        filters.append(User.class_id == class_id)
    if exam_type:
        filters.append(cast(User.target_exams, JSONB).contains([exam_type]))
    
    user_data = (await db.execute(select(User, UserStudyStats.longest_study_streak, UserStudyStats.current_study_streak).join(UserStudyStats, User.id == UserStudyStats.user_id).where(and_(User.id == user_id, *filters)))).first()
    if not user_data:
        return None, None
    
    user_rank = (await db.execute(select(func.count(UserStudyStats.id)).join(User, UserStudyStats.user_id == User.id).where(and_(UserStudyStats.current_study_streak > user_data[2], *filters)))).scalar() or 0
    return user_rank + 1, (user_data[0], user_data[1], user_data[2])


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

