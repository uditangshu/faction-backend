"""Leaderboard database calls"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.user import User
from app.models.contest import ContestLeaderboard
from app.models.attempt import QuestionAttempt
from app.models.streak import UserStudyStats


async def get_user_with_max_rating(db: AsyncSession) -> Optional[Tuple[User, int]]:
    """
    Get user with maximum contest rating.
    
    Returns:
        Tuple of (User, max_rating) or None if no users found
    """
    result = await db.execute(
        select(User, User.max_rating)
        .where(User.is_active == True)
        .order_by(desc(User.max_rating))
        .limit(1)
    )
    row = result.first()
    if row:
        return (row[0], row[1])
    return None


async def get_top_users_by_rating(
    db: AsyncSession,
    limit: int = 10,
) -> List[Tuple[User, int]]:
    """
    Get top N users by maximum rating.
    
    Returns:
        List of tuples (User, max_rating)
    """
    result = await db.execute(
        select(User, User.max_rating)
        .where(User.is_active == True)
        .order_by(desc(User.max_rating))
        .limit(limit)
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_user_with_max_delta(db: AsyncSession) -> Optional[Tuple[User, int]]:
    """
    Get user with maximum rating delta from contest leaderboard.
    
    Returns:
        Tuple of (User, max_delta) or None if no leaderboard entries found
    """
    # Subquery to get max delta per user
    subquery = (
        select(
            ContestLeaderboard.user_id,
            func.max(ContestLeaderboard.rating_delta).label("max_delta")
        )
        .group_by(ContestLeaderboard.user_id)
        .subquery()
    )
    
    # Get user with highest max_delta
    result = await db.execute(
        select(User, subquery.c.max_delta)
        .join(subquery, User.id == subquery.c.user_id)
        .where(User.is_active == True)
        .order_by(desc(subquery.c.max_delta))
        .limit(1)
    )
    row = result.first()
    if row:
        return (row[0], row[1])
    return None


async def get_top_users_by_delta(
    db: AsyncSession,
    limit: int = 10,
) -> List[Tuple[User, int]]:
    """
    Get top N users by maximum rating delta.
    
    Returns:
        List of tuples (User, max_delta)
    """
    # Subquery to get max delta per user
    subquery = (
        select(
            ContestLeaderboard.user_id,
            func.max(ContestLeaderboard.rating_delta).label("max_delta")
        )
        .group_by(ContestLeaderboard.user_id)
        .subquery()
    )
    
    result = await db.execute(
        select(User, subquery.c.max_delta)
        .join(subquery, User.id == subquery.c.user_id)
        .where(User.is_active == True)
        .order_by(desc(subquery.c.max_delta))
        .limit(limit)
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_user_with_most_questions_solved(db: AsyncSession) -> Optional[Tuple[User, int]]:
    """
    Get user with most correct questions solved.
    
    Returns:
        Tuple of (User, question_count) or None if no attempts found
    """
    # Subquery to count correct attempts per user
    subquery = (
        select(
            QuestionAttempt.user_id,
            func.count(QuestionAttempt.id).label("question_count")
        )
        .where(QuestionAttempt.is_correct == True)
        .group_by(QuestionAttempt.user_id)
        .subquery()
    )
    
    # Get user with highest question count
    result = await db.execute(
        select(User, subquery.c.question_count)
        .join(subquery, User.id == subquery.c.user_id)
        .where(User.is_active == True)
        .order_by(desc(subquery.c.question_count))
        .limit(1)
    )
    row = result.first()
    if row:
        return (row[0], row[1])
    return None


async def get_top_users_by_questions_solved(
    db: AsyncSession,
    limit: int = 10,
) -> List[Tuple[User, int]]:
    """
    Get top N users by number of correct questions solved.
    
    Returns:
        List of tuples (User, question_count)
    """
    # Subquery to count correct attempts per user
    subquery = (
        select(
            QuestionAttempt.user_id,
            func.count(QuestionAttempt.id).label("question_count")
        )
        .where(QuestionAttempt.is_correct == True)
        .group_by(QuestionAttempt.user_id)
        .subquery()
    )
    
    result = await db.execute(
        select(User, subquery.c.question_count)
        .join(subquery, User.id == subquery.c.user_id)
        .where(User.is_active == True)
        .order_by(desc(subquery.c.question_count))
        .limit(limit)
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_top_users_by_streak(
    db: AsyncSession,
    limit: int = 10,
) -> List[Tuple[User, int]]:
    """
    Get top N users by current study streak.
    
    Returns:
        List of tuples (User, streak_days)
    """
    result = await db.execute(
        select(User, UserStudyStats.current_study_streak)
        .join(UserStudyStats, User.id == UserStudyStats.user_id)
        .where(User.is_active == True)
        .order_by(desc(UserStudyStats.current_study_streak))
        .limit(limit)
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_user_rank_by_rating(db: AsyncSession, user_id: UUID) -> Optional[Tuple[int, int, int]]:
    """
    Get user's rank by max rating.
    
    Returns:
        Tuple of (rank, user_rating, total_users) or None
    """
    # Get user's rating
    user_result = await db.execute(
        select(User.max_rating).where(User.id == user_id, User.is_active == True)
    )
    user_rating = user_result.scalar_one_or_none()
    if user_rating is None:
        return None
    
    # Count users with higher rating
    higher_count = await db.execute(
        select(func.count(User.id))
        .where(User.is_active == True, User.max_rating > user_rating)
    )
    rank = higher_count.scalar() + 1
    
    # Get total users
    total_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    total_users = total_result.scalar()
    
    return (rank, user_rating, total_users)


async def get_user_rank_by_questions(db: AsyncSession, user_id: UUID) -> Optional[Tuple[int, int, int]]:
    """
    Get user's rank by questions solved.
    
    Returns:
        Tuple of (rank, questions_solved, total_users) or None
    """
    # Subquery for all users' question counts
    subquery = (
        select(
            QuestionAttempt.user_id,
            func.count(QuestionAttempt.id).label("question_count")
        )
        .where(QuestionAttempt.is_correct == True)
        .group_by(QuestionAttempt.user_id)
        .subquery()
    )
    
    # Get user's question count
    user_result = await db.execute(
        select(subquery.c.question_count)
        .where(subquery.c.user_id == user_id)
    )
    user_questions = user_result.scalar_one_or_none() or 0
    
    # Count users with more questions
    higher_result = await db.execute(
        select(func.count(subquery.c.user_id))
        .where(subquery.c.question_count > user_questions)
    )
    rank = higher_result.scalar() + 1
    
    # Get total users who have solved at least one question
    total_result = await db.execute(
        select(func.count(subquery.c.user_id))
    )
    total_users = total_result.scalar() or 1
    
    return (rank, user_questions, total_users)


async def get_user_rank_by_streak(db: AsyncSession, user_id: UUID) -> Optional[Tuple[int, int, int]]:
    """
    Get user's rank by current streak.
    
    Returns:
        Tuple of (rank, streak_days, total_users) or None
    """
    # Get user's streak
    user_result = await db.execute(
        select(UserStudyStats.current_study_streak)
        .where(UserStudyStats.user_id == user_id)
    )
    user_streak = user_result.scalar_one_or_none() or 0
    
    # Count users with higher streak
    higher_result = await db.execute(
        select(func.count(UserStudyStats.id))
        .where(UserStudyStats.current_study_streak > user_streak)
    )
    rank = higher_result.scalar() + 1
    
    # Get total users with streaks
    total_result = await db.execute(
        select(func.count(UserStudyStats.id))
    )
    total_users = total_result.scalar() or 1
    
    return (rank, user_streak, total_users)

