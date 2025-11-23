"""User database calls"""

from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


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

