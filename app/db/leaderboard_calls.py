"""Leaderboard database calls"""

from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from app.models.user import User
from app.models.contest import ContestLeaderboard
from app.models.attempt import QuestionAttempt


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


async def get_arena_ranking_by_submissions(
    db: AsyncSession,
    time_filter: str = "all_time",
    skip: int = 0,
    limit: int = 20,
) -> Tuple[List[Tuple[User, int]], int]:
    """
    Get arena ranking by maximum submissions solved with time filtering and pagination.
    
    Args:
        db: Database session
        time_filter: Time filter - "daily", "weekly", or "all_time"
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
    
    Returns:
        Tuple of (List of tuples (User, question_count), total_count)
    """
    # Calculate time threshold based on filter
    now = datetime.utcnow()
    if time_filter == "daily":
        threshold = now - timedelta(days=1)
    elif time_filter == "weekly":
        threshold = now - timedelta(weeks=1)
    else:  # all_time
        threshold = None
    
    # Build base query for counting distinct correct questions per user
    base_query = (
        select(
            QuestionAttempt.user_id,
            func.count(func.distinct(QuestionAttempt.question_id)).label("question_count")
        )
        .where(QuestionAttempt.is_correct == True)
    )
    
    # Add time filter if not all_time
    if threshold is not None:
        base_query = base_query.where(QuestionAttempt.attempted_at >= threshold)
    
    # Group by user_id
    base_query = base_query.group_by(QuestionAttempt.user_id)
    
    # Create subquery
    subquery = base_query.subquery()
    
    # Count total users for pagination
    count_query = (
        select(func.count(subquery.c.user_id))
        .select_from(subquery)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Get paginated results
    result = await db.execute(
        select(User, subquery.c.question_count)
        .join(subquery, User.id == subquery.c.user_id)
        .where(User.is_active == True)
        .order_by(desc(subquery.c.question_count))
        .offset(skip)
        .limit(limit)
    )
    
    return [(row[0], row[1]) for row in result.all()], total


async def get_contest_leaderboard_entry(
    db: AsyncSession,
    contest_id: UUID,
    user_id: UUID,
) -> Optional[ContestLeaderboard]:
    """
    Get contest leaderboard entry for a specific user and contest.
    
    Args:
        db: Database session
        contest_id: Contest ID
        user_id: User ID
    
    Returns:
        ContestLeaderboard entry or None if not found
    """
    result = await db.execute(
        select(ContestLeaderboard).where(
            ContestLeaderboard.contest_id == contest_id,
            ContestLeaderboard.user_id == user_id
        )
    )
    return result.scalar_one_or_none()

