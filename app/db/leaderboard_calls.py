"""Leaderboard database calls"""

from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, and_, cast, or_
from sqlalchemy.dialects.postgresql import JSONB

from app.models.user import User
from app.models.contest import ContestLeaderboard, Contest
from app.models.attempt import QuestionAttempt
from app.integrations.redis_client import RedisService
from app.core.config import settings


async def get_user_with_max_rating(db: AsyncSession) -> Optional[Tuple[User, int]]:
    """
    Get user with maximum contest rating.
    Optimized to use index on (is_active, max_rating).
    
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
    Optimized to use index on (is_active, max_rating).
    
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
    class_id: Optional[UUID] = None,
    target_exams: Optional[List[str]] = None,
) -> Tuple[List[Tuple[User, int]], int]:
    """
    Get arena ranking by maximum submissions solved with time filtering and pagination.
    
    Args:
        db: Database session
        time_filter: Time filter - "daily", "weekly", or "all_time"
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        class_id: Optional class ID to filter users by class
        target_exams: Optional list of target exams to filter users by matching exams
    
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
    
    # Build user filter conditions
    user_filters = [User.is_active == True]
    
    # Filter by class_id if provided
    if class_id is not None:
        user_filters.append(User.class_id == class_id)
    
    # Filter by target_exams overlap if provided
    if target_exams and len(target_exams) > 0:
        # Check if any of the target_exams exist in the user's target_exams array
        # Using JSONB contains operator to check for overlap
        exam_conditions = [
            cast(User.target_exams, JSONB).contains([exam]) for exam in target_exams
        ]
        user_filters.append(or_(*exam_conditions))
    
    # Count total users for pagination
    count_query = (
        select(func.count(subquery.c.user_id))
        .select_from(subquery)
        .join(User, subquery.c.user_id == User.id)
        .where(and_(*user_filters))
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Get paginated results
    result = await db.execute(
        select(User, subquery.c.question_count)
        .join(subquery, User.id == subquery.c.user_id)
        .where(and_(*user_filters))
        .order_by(desc(subquery.c.question_count))
        .offset(skip)
        .limit(limit)
    )
    
    return [(row[0], row[1]) for row in result.all()], total


async def get_contest_ranking_by_filter(
    db: AsyncSession,
    filter_type: str = "best_rating_first",
    skip: int = 0,
    limit: int = 20,
    class_id: Optional[UUID] = None,
    target_exams: Optional[List[str]] = None,
    redis_service: Optional[RedisService] = None,
) -> Tuple[List[Tuple[ContestLeaderboard, User]], int]:
    """
    Get contest ranking from the most recent contest with filter options.
    
    Args:
        db: Database session
        filter_type: Filter type - "best_rating_first" or "best_delta_first"
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        class_id: Optional class ID to filter users by class
        target_exams: Optional list of target exams to filter users by matching exams
        redis_service: Optional Redis service for caching most recent contest
    
    Returns:
        Tuple of (List of tuples (ContestLeaderboard, User), total_count)
    """
    # Cache the most recent contest ID lookup
    cache_key = "leaderboard:most_recent_contest_id"
    contest_id = None
    
    if redis_service:
        cached_contest_id = await redis_service.get_value(cache_key)
        if cached_contest_id:
            try:
                contest_id = UUID(cached_contest_id)
            except (ValueError, TypeError):
                contest_id = None
    
    # If not cached, query for most recent contest
    if not contest_id:
        most_recent_contest_result = await db.execute(
            select(Contest)
            .order_by(desc(Contest.ends_at), desc(Contest.created_at))
            .limit(1)
        )
        most_recent_contest = most_recent_contest_result.scalar_one_or_none()
        
        if not most_recent_contest:
            return [], 0
        
        contest_id = most_recent_contest.id
        
        # Cache the contest ID for 5 minutes
        if redis_service:
            await redis_service.set_value(
                cache_key,
                str(contest_id),
                expire=300  # 5 minutes
            )
    
    # Build user filter conditions
    user_filters = [User.is_active == True]
    
    # Filter by class_id if provided
    if class_id is not None:
        user_filters.append(User.class_id == class_id)
    
    # Filter by target_exams overlap if provided
    if target_exams and len(target_exams) > 0:
        # Check if any of the target_exams exist in the user's target_exams array
        # Using JSONB contains operator to check for overlap
        exam_conditions = [
            cast(User.target_exams, JSONB).contains([exam]) for exam in target_exams
        ]
        user_filters.append(or_(*exam_conditions))
    
    # Count total leaderboard entries for this contest
    count_result = await db.execute(
        select(func.count(ContestLeaderboard.id))
        .where(
            ContestLeaderboard.contest_id == contest_id,
            ContestLeaderboard.user_id.in_(
                select(User.id).where(and_(*user_filters))
            )
        )
    )
    total = count_result.scalar() or 0
    
    # Build order_by clause based on filter_type
    if filter_type == "best_delta_first":
        order_by_clause = [
            desc(ContestLeaderboard.rating_delta),
            desc(ContestLeaderboard.rating_after)
        ]
    else:  # best_rating_first (default)
        order_by_clause = [
            desc(ContestLeaderboard.rating_after),
            desc(ContestLeaderboard.rating_delta)
        ]
    
    # Get paginated leaderboard entries with ordering
    # Join with User to get user information
    result = await db.execute(
        select(ContestLeaderboard, User)
        .join(User, ContestLeaderboard.user_id == User.id)
        .where(
            ContestLeaderboard.contest_id == contest_id,
            and_(*user_filters)
        )
        .order_by(*order_by_clause)
        .offset(skip)
        .limit(limit)
    )
    
    return [(row[0], row[1]) for row in result.all()], total


async def get_contest_ranking_by_contest_id(
    db: AsyncSession,
    contest_id: UUID,
    filter_type: str = "best_rating_first",
    skip: int = 0,
    limit: int = 20,
) -> Tuple[List[Tuple[ContestLeaderboard, User]], int]:
    """
    Get contest ranking for a specific contest by contest_id with filter options.
    
    Args:
        db: Database session
        contest_id: Contest ID to get ranking for
        filter_type: Filter type - "best_rating_first" or "best_delta_first"
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
    
    Returns:
        Tuple of (List of tuples (ContestLeaderboard, User), total_count)
    """
    # Count total leaderboard entries for this contest
    count_result = await db.execute(
        select(func.count(ContestLeaderboard.id))
        .where(ContestLeaderboard.contest_id == contest_id)
    )
    total = count_result.scalar() or 0
    
    # Build order_by clause based on filter_type
    if filter_type == "best_delta_first":
        order_by_clause = [
            desc(ContestLeaderboard.rating_delta),
            desc(ContestLeaderboard.rating_after)
        ]
    else:  # best_rating_first (default)
        order_by_clause = [
            desc(ContestLeaderboard.rating_after),
            desc(ContestLeaderboard.rating_delta)
        ]
    
    # Get paginated leaderboard entries with ordering
    # Join with User to get user information
    result = await db.execute(
        select(ContestLeaderboard, User)
        .join(User, ContestLeaderboard.user_id == User.id)
        .where(ContestLeaderboard.contest_id == contest_id)
        .order_by(*order_by_clause)
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


async def get_scholarship_ranking(
    db: AsyncSession,
    contest_id: UUID,
    skip: int = 0,
    limit: int = 20,
) -> Tuple[List[Tuple[ContestLeaderboard, User, Contest]], int]:
    """
    Get scholarship contest ranking ordered by score (desc) and total_time (asc).
    
    Fetches leaderboard entries for a specific scholarship contest (isScholarship=True),
    ordered by highest score first, then by lowest total_time for same scores.
    
    Args:
        db: Database session
        contest_id: Contest ID to get ranking for (must be a scholarship contest)
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
    
    Returns:
        Tuple of (List of tuples (ContestLeaderboard, User, Contest), total_count)
    """
    # Count total leaderboard entries for this scholarship contest
    count_result = await db.execute(
        select(func.count(ContestLeaderboard.id))
        .join(Contest, ContestLeaderboard.contest_id == Contest.id)
        .where(
            ContestLeaderboard.contest_id == contest_id,
            Contest.isScholarship == True
        )
    )
    total = count_result.scalar() or 0
    
    # Get paginated leaderboard entries with ordering
    # Order by score DESC, then total_time ASC (lower time is better)
    result = await db.execute(
        select(ContestLeaderboard, User, Contest)
        .join(User, ContestLeaderboard.user_id == User.id)
        .join(Contest, ContestLeaderboard.contest_id == Contest.id)
        .where(
            ContestLeaderboard.contest_id == contest_id,
            Contest.isScholarship == True
        )
        .order_by(
            desc(ContestLeaderboard.score),
            asc(ContestLeaderboard.total_time)
        )
        .offset(skip)
        .limit(limit)
    )
    
    return [(row[0], row[1], row[2]) for row in result.all()], total


async def get_rating_ranking_by_filter(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    class_id: Optional[UUID] = None,
    target_exams: Optional[List[str]] = None,
) -> Tuple[List[User], int]:
    """
    Get rating ranking filtered by class_id and target_exams.
    
    Args:
        db: Database session
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        class_id: Optional class ID to filter users by class
        target_exams: Optional list of target exams to filter users by matching exams
    
    Returns:
        Tuple of (List of Users, total_count) ordered by current_rating descending
    """
    # Build user filter conditions
    user_filters = [User.is_active == True]
    
    # Filter by class_id if provided
    if class_id is not None:
        user_filters.append(User.class_id == class_id)
    
    # Filter by target_exams overlap if provided
    if target_exams and len(target_exams) > 0:
        # Check if any of the target_exams exist in the user's target_exams array
        # Using JSONB contains operator to check for overlap
        exam_conditions = [
            cast(User.target_exams, JSONB).contains([exam]) for exam in target_exams
        ]
        user_filters.append(or_(*exam_conditions))
    
    # Count total users for pagination
    count_query = select(func.count(User.id)).where(and_(*user_filters))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Get paginated results ordered by current_rating descending, then max_rating descending
    result = await db.execute(
        select(User)
        .where(and_(*user_filters))
        .order_by(desc(User.current_rating), desc(User.max_rating))
        .offset(skip)
        .limit(limit)
    )
    
    return result.scalars().all(), total

