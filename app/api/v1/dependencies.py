"""API v1 dependencies"""

from typing import Annotated
from uuid import UUID
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db_session
from app.integrations.redis_client import get_redis, RedisService
from app.core.security import decode_token
from app.models.user import User
from app.services.otp_service import OTPService
from app.services.auth_service import AuthService
from app.services.question_service import QuestionService
from app.services.streak_service import StreakService
from app.services.user_services import UserService
from app.exceptions.auth_exceptions import UnauthorizedException, SessionExpiredException
from app.services.chapter_service import ChapterService
from app.services.class_service import ClassService
from app.services.subject_service import SubjectService
from app.services.analysis_service import AnalysisService
from app.services.attempt_service import AttemptService
from app.services.pyq_service import PYQService
# Database session dependency
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


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


async def get_user_service(db: DBSession) -> UserService: 
    """Get user service"""
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_class_service(db: DBSession) -> ClassService:
    """Get class service"""
    return ClassService(db)


ClassServiceDep = Annotated[ClassService, Depends(get_class_service)]


async def get_subject_service(db: DBSession) -> SubjectService:
    """Get subject service"""
    return SubjectService(db)


SubjectServiceDep = Annotated[SubjectService, Depends(get_subject_service)]


async def get_chapter_service(db: DBSession) -> ChapterService:
    """Get chapter service"""
    return ChapterService(db)


ChapterServiceDep = Annotated[ChapterService, Depends(get_chapter_service)]


async def get_analysis_service(db: DBSession) -> AnalysisService:
    """Get analysis service"""
    return AnalysisService(db)


AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]


async def get_attempt_service(db: DBSession) -> AttemptService:
    """Get attempt service"""
    return AttemptService(db)


AttemptServiceDep = Annotated[AttemptService, Depends(get_attempt_service)]


async def get_pyq_service(db: DBSession) -> PYQService:
    """Get PYQ service"""
    return PYQService(db)


PYQServiceDep = Annotated[PYQService, Depends(get_pyq_service)]


bearer_scheme = HTTPBearer()

# Current user dependency
async def get_current_user(
    db: DBSession,
    redis: RedisServiceDep,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Get current authenticated user from JWT token with session validation"""
    authorization = creds.credentials
    print(authorization)
    if not authorization:
        raise UnauthorizedException("Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise UnauthorizedException("Invalid authentication scheme")
    except ValueError:
        raise UnauthorizedException("Invalid authorization header format")

    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    user_id_str = payload.get("sub")
    session_id = payload.get("session_id")
    
    if not user_id_str:
        raise UnauthorizedException("Invalid token payload")
    
    if not session_id:
        raise UnauthorizedException("Invalid token: missing session ID")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid user ID in token")

    # Check if this session has been force logged out (e.g., login from another device)
    should_logout = await redis.should_force_logout(session_id)
    if should_logout:
        # Clean up the force_logout flag
        await redis.delete_key(f"force_logout:{session_id}")
        raise SessionExpiredException()
    
    # Check if session is still the active one
    is_valid = await redis.is_session_valid(user_id_str, session_id)
    if not is_valid:
        raise SessionExpiredException()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("Account is inactive")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserDep = CurrentUser  

