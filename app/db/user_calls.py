"""User database calls"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.user import User
from app.models.contest import ContestLeaderboard, Contest


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get user by ID - optimized using get() for primary key lookup"""
    return await db.get(User, user_id)


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> Optional[User]:
    """Get user by phone number"""
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one_or_none()


async def user_exists_by_phone(db: AsyncSession, phone_number: str) -> bool:
    """Check if user exists by phone number"""
    user = await get_user_by_phone(db, phone_number)
    return user is not None


async def create_user(db: AsyncSession, user: User) -> User:
    """Create new user"""
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User) -> User:
    """Update existing user"""
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_rating_fluctuation(
    db: AsyncSession,
    user_id: UUID,
) -> List[Tuple[ContestLeaderboard, Contest]]:
    """
    Get user's rating fluctuation history from all contests.
    
    Args:
        db: Database session
        user_id: User ID to get rating history for
    
    Returns:
        List of tuples (ContestLeaderboard, Contest) ordered by created_at descending
    """
    result = await db.execute(
        select(ContestLeaderboard, Contest)
        .join(Contest, ContestLeaderboard.contest_id == Contest.id)
        .where(ContestLeaderboard.user_id == user_id)
        .order_by(desc(ContestLeaderboard.created_at))
    )
    
    return [(row[0], row[1]) for row in result.all()]

