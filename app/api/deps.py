"""Shared API dependencies"""

from typing import Annotated
from uuid import UUID
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.redis import get_redis, RedisService
from app.core.security import decode_token
from app.models.user import User
from app.services.otp_service import OTPService
from app.services.auth_service import AuthService
from app.services.question_service import QuestionService
from app.services.streak_service import StreakService
from app.utils.exceptions import UnauthorizedException
from sqlalchemy import select


# Database session dependency
async def get_db() -> AsyncSession:
    """Get database session"""
    async for session in get_session():
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


# Redis service dependency
async def get_redis_service() -> RedisService:
    """Get Redis service"""
    redis_client = await get_redis()
    return RedisService(redis_client)


RedisServiceDep = Annotated[RedisService, Depends(get_redis_service)]


# OTP service dependency
async def get_otp_service(redis_service: RedisServiceDep) -> OTPService:
    """Get OTP service"""
    return OTPService(redis_service)


OTPServiceDep = Annotated[OTPService, Depends(get_otp_service)]


# Auth service dependency
async def get_auth_service(db: DBSession, otp_service: OTPServiceDep) -> AuthService:
    """Get auth service"""
    return AuthService(db, otp_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# Question service dependency
async def get_question_service(db: DBSession) -> QuestionService:
    """Get question service"""
    return QuestionService(db)


QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]


# Streak service dependency
async def get_streak_service(db: DBSession) -> StreakService:
    """Get streak service"""
    return StreakService(db)


StreakServiceDep = Annotated[StreakService, Depends(get_streak_service)]


# Current user dependency
async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: DBSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        authorization: Authorization header with Bearer token
        db: Database session

    Returns:
        Current user

    Raises:
        UnauthorizedException: If token is invalid or user not found
    """
    if not authorization:
        raise UnauthorizedException("Missing authorization header")

    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise UnauthorizedException("Invalid authentication scheme")
    except ValueError:
        raise UnauthorizedException("Invalid authorization header format")

    # Decode token
    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    # Get user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Invalid token payload")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid user ID in token")

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("Account is inactive")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

