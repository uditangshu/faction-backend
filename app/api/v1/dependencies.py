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
from app.services.topic_service import TopicService
from app.services.analysis_service import AnalysisService
from app.services.attempt_service import AttemptService
from app.services.pyq_service import PYQService
from app.services.filtering_service import FilteringService
from app.services.leaderboard_service import LeaderboardService
from app.services.badge_service import BadgeService
from app.services.youtube_video_service import YouTubeVideoService
from app.services.bookmarked_video_service import BookmarkedVideoService
from app.services.weak_topic_service import WeakTopicService
from app.services.custom_test_service import CustomTestService
from app.services.contest_service import ContestService
from app.services.doubt_forum_service import DoubtForumService
from app.services.notification_service import NotificationService
from app.services.treasure_service import TreasureService
from app.services.notes_service import NotesService
from app.services.scholarship_service import ScholarshipService

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


async def get_class_service(db: DBSession, redis_service: RedisServiceDep) -> ClassService:
    """Get class service with Redis caching"""
    return ClassService(db, redis_service)


ClassServiceDep = Annotated[ClassService, Depends(get_class_service)]


async def get_subject_service(db: DBSession, redis_service: RedisServiceDep) -> SubjectService:
    """Get subject service with Redis caching"""
    return SubjectService(db, redis_service)


SubjectServiceDep = Annotated[SubjectService, Depends(get_subject_service)]


async def get_chapter_service(db: DBSession, redis_service: RedisServiceDep) -> ChapterService:
    """Get chapter service with Redis caching"""
    return ChapterService(db, redis_service)


ChapterServiceDep = Annotated[ChapterService, Depends(get_chapter_service)]


async def get_topic_service(db: DBSession, redis_service: RedisServiceDep) -> TopicService:
    """Get topic service with Redis caching"""
    return TopicService(db, redis_service)


TopicServiceDep = Annotated[TopicService, Depends(get_topic_service)]


async def get_analysis_service(db: DBSession) -> AnalysisService:
    """Get analysis service"""
    return AnalysisService(db)


AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]


async def get_attempt_service(db: DBSession) -> AttemptService:
    """Get attempt service"""
    return AttemptService(db)


AttemptServiceDep = Annotated[AttemptService, Depends(get_attempt_service)]


async def get_pyq_service(db: DBSession, redis_service: RedisServiceDep) -> PYQService:
    """Get PYQ service with Redis caching"""
    return PYQService(db, redis_service)


PYQServiceDep = Annotated[PYQService, Depends(get_pyq_service)]


async def get_filtering_service(db: DBSession) -> FilteringService:
    """Get filtering service"""
    return FilteringService(db)


FilteringServiceDep = Annotated[FilteringService, Depends(get_filtering_service)]


async def get_leaderboard_service(db: DBSession, redis_service: RedisServiceDep) -> LeaderboardService:
    """Get leaderboard service with Redis caching"""
    return LeaderboardService(db, redis_service)


LeaderboardServiceDep = Annotated[LeaderboardService, Depends(get_leaderboard_service)]


async def get_badge_service(db: DBSession, redis_service: RedisServiceDep) -> BadgeService:
    """Get badge service with Redis caching"""
    return BadgeService(db, redis_service)


BadgeServiceDep = Annotated[BadgeService, Depends(get_badge_service)]


async def get_youtube_video_service(db: DBSession) -> YouTubeVideoService:
    """Get YouTube video service"""
    return YouTubeVideoService(db)


YouTubeVideoServiceDep = Annotated[YouTubeVideoService, Depends(get_youtube_video_service)]


async def get_bookmarked_video_service(db: DBSession, redis_service: RedisServiceDep) -> BookmarkedVideoService:
    """Get bookmarked video service with Redis caching"""
    return BookmarkedVideoService(db, redis_service)


BookmarkedVideoServiceDep = Annotated[BookmarkedVideoService, Depends(get_bookmarked_video_service)]


async def get_weak_topic_service(db: DBSession) -> WeakTopicService:
    """Get weak topic service"""
    return WeakTopicService(db)


WeakTopicServiceDep = Annotated[WeakTopicService, Depends(get_weak_topic_service)]


async def get_custom_test_service(db: DBSession, redis_service: RedisServiceDep) -> CustomTestService:
    """Get custom test service with Redis caching"""
    return CustomTestService(db, redis_service)


CustomTestServiceDep = Annotated[CustomTestService, Depends(get_custom_test_service)]


async def get_contest_service(db: DBSession, redis_service: RedisServiceDep) -> ContestService:
    """Get contest service"""
    return ContestService(db, redis_service)


ContestServiceDep = Annotated[ContestService, Depends(get_contest_service)]


async def get_doubt_forum_service(db: DBSession, redis_service: RedisServiceDep) -> DoubtForumService:
    """Get doubt forum service with Redis caching"""
    return DoubtForumService(db, redis_service)


DoubtForumServiceDep = Annotated[DoubtForumService, Depends(get_doubt_forum_service)]


async def get_notification_service(db: DBSession, redis_service: RedisServiceDep) -> NotificationService:
    """Get notification service with Redis caching"""
    return NotificationService(db, redis_service)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


async def get_treasure_service(db: DBSession, redis_service: RedisServiceDep) -> TreasureService:
    """Get treasure service with Redis caching"""
    return TreasureService(db, redis_service)


TreasureServiceDep = Annotated[TreasureService, Depends(get_treasure_service)]


async def get_notes_service(db: DBSession, redis_service: RedisServiceDep) -> NotesService:
    """Get notes service with Redis caching"""
    return NotesService(db, redis_service)


NotesServiceDep = Annotated[NotesService, Depends(get_notes_service)]


async def get_scholarship_service(db: DBSession) -> ScholarshipService:
    """Get scholarship service"""
    return ScholarshipService(db)


ScholarshipServiceDep = Annotated[ScholarshipService, Depends(get_scholarship_service)]


bearer_scheme = HTTPBearer()

# Current user dependency
async def get_current_user(
    db: DBSession,
    redis: RedisServiceDep,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Get current authenticated user from JWT token with session validation"""
    # HTTPBearer already extracts the token from "Bearer <token>" format
    # creds.credentials contains just the token string
    token = creds.credentials
    
    if not token:
        raise UnauthorizedException("Missing authorization header")

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

    # Check session validity using Redis pipeline (batches multiple operations)
    pipeline_commands = [
        ("exists", f"force_logout:{session_id}"),
        ("get", f"active_session:{user_id_str}"),
    ]
    pipeline_results = await redis.execute_pipeline(pipeline_commands)
    should_logout = pipeline_results[0] > 0 if pipeline_results[0] is not None else False
    active_session = pipeline_results[1]
    
    if should_logout:
        # Clean up the force_logout flag
        await redis.delete_key(f"force_logout:{session_id}")
        raise SessionExpiredException()
    
    # Check if session is still the active one
    if active_session is None:
        is_valid = False
    else:
        is_valid = str(active_session) == str(session_id)
    
    if not is_valid:
        raise SessionExpiredException()

    # CACHE USER: Fast path - avoid DB query
    user_cache_key = f"user:{user_id_str}:{session_id}"
    cached_user = await redis.get_value(user_cache_key)
    
    if cached_user is not None:
        # Direct return - cached data is already in correct format for User model
        # Pydantic/SQLModel will handle type conversion automatically
        user = User.model_validate(cached_user)
        if not user.is_active:
            raise UnauthorizedException("Account is inactive")
        return user

    # Cache miss - fetch from database
    user = await db.get(User, user_id)
    if not user:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("Account is inactive")

    # Cache user using model_dump (handles all serialization automatically)
    from app.core.config import settings
    await redis.set_value(
        user_cache_key,
        user.model_dump(mode='json'),  # Automatically converts UUIDs, datetimes, enums to JSON-compatible types
        expire=settings.CACHE_USER_TTL
    )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserDep = CurrentUser  

