from typing import Annotated
from uuid import UUID
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db_session, get_readonly_db_session
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
from app.services.custom_test_service import CustomTestService
from app.services.leaderboard_service import LeaderboardService
from app.services.contest_service import ContestService
from app.services.badge_service import BadgeService

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
ReadOnlyDBSession = Annotated[AsyncSession, Depends(get_readonly_db_session)]


async def get_redis_service() -> RedisService:
    redis_client = await get_redis()
    return RedisService(redis_client)


RedisServiceDep = Annotated[RedisService, Depends(get_redis_service)]


async def get_otp_service(redis_service: RedisServiceDep) -> OTPService:
    return OTPService(redis_service)


OTPServiceDep = Annotated[OTPService, Depends(get_otp_service)]


async def get_auth_service(db: DBSession, otp_service: OTPServiceDep) -> AuthService:
    return AuthService(db, otp_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_question_service(db: DBSession) -> QuestionService:
    return QuestionService(db)


QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]


async def get_streak_service(db: DBSession) -> StreakService:
    return StreakService(db)


StreakServiceDep = Annotated[StreakService, Depends(get_streak_service)]


async def get_user_service(db: DBSession) -> UserService: 
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_class_service(db: DBSession) -> ClassService:
    return ClassService(db)


ClassServiceDep = Annotated[ClassService, Depends(get_class_service)]


async def get_subject_service(db: DBSession) -> SubjectService:
    return SubjectService(db)


SubjectServiceDep = Annotated[SubjectService, Depends(get_subject_service)]


async def get_chapter_service(db: DBSession) -> ChapterService:
    return ChapterService(db)


ChapterServiceDep = Annotated[ChapterService, Depends(get_chapter_service)]


async def get_topic_service(db: DBSession) -> TopicService:
    return TopicService(db)


TopicServiceDep = Annotated[TopicService, Depends(get_topic_service)]


async def get_analysis_service(db: DBSession) -> AnalysisService:
    return AnalysisService(db)


AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]


async def get_attempt_service(db: DBSession) -> AttemptService:
    return AttemptService(db)


AttemptServiceDep = Annotated[AttemptService, Depends(get_attempt_service)]


async def get_pyq_service(db: DBSession) -> PYQService:
    return PYQService(db)


PYQServiceDep = Annotated[PYQService, Depends(get_pyq_service)]


async def get_filtering_service(db: DBSession) -> FilteringService:
    return FilteringService(db)


FilteringServiceDep = Annotated[FilteringService, Depends(get_filtering_service)]


async def get_custom_test_service(db: DBSession) -> CustomTestService:
    return CustomTestService(db)


CustomTestServiceDep = Annotated[CustomTestService, Depends(get_custom_test_service)]


async def get_leaderboard_service(db: ReadOnlyDBSession, redis: RedisServiceDep) -> LeaderboardService:
    return LeaderboardService(db, redis)


LeaderboardServiceDep = Annotated[LeaderboardService, Depends(get_leaderboard_service)]


async def get_contest_service(db: DBSession) -> ContestService:
    return ContestService(db)


ContestServiceDep = Annotated[ContestService, Depends(get_contest_service)]


async def get_badge_service(db: DBSession) -> BadgeService:
    return BadgeService(db)


BadgeServiceDep = Annotated[BadgeService, Depends(get_badge_service)]


bearer_scheme = HTTPBearer()


async def get_current_user(
    db: DBSession,
    redis: RedisServiceDep,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
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

    pipeline_commands = [
        ("exists", f"force_logout:{session_id}"),
        ("get", f"active_session:{user_id_str}"),
    ]
    pipeline_results = await redis.execute_pipeline(pipeline_commands)
    should_logout = pipeline_results[0] > 0 if pipeline_results[0] is not None else False
    active_session = pipeline_results[1]
    
    if should_logout:
        await redis.delete_key(f"force_logout:{session_id}")
        raise SessionExpiredException()
    
    if active_session is None or str(active_session) != str(session_id):
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
