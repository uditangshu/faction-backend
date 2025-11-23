"""User endpoints"""

from uuid import UUID
from fastapi import APIRouter, Header
from typing import Annotated

from app.api.v1.dependencies import CurrentUser, DBSession
from app.core.security import decode_token
from app.schemas.user import UserProfileResponse
from app.schemas.auth import CurrentDeviceResponse
from app.db.session_calls import get_user_session
from app.exceptions.auth_exceptions import UnauthorizedException

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: CurrentUser) -> UserProfileResponse:
    return UserProfileResponse.from_orm(current_user)


@router.get("/current-device", response_model=CurrentDeviceResponse)
async def get_current_device(
    db: DBSession,
    current_user: CurrentUser,
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentDeviceResponse:
    """Get current device information"""
    if not authorization:
        # This case should technically not be reached if CurrentUser dependency works
        raise UnauthorizedException("Missing authorization header")

    try:
        _, token = authorization.split()
    except ValueError:
        raise UnauthorizedException("Invalid authorization header format")

    payload = decode_token(token)
    if not payload or "session_id" not in payload:
        raise UnauthorizedException("Invalid token payload")

    try:
        session_id = UUID(payload["session_id"])
    except ValueError:
        raise UnauthorizedException("Invalid session ID in token")

    session = await get_user_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise UnauthorizedException("Session not found or does not belong to user")

    return CurrentDeviceResponse(
        session_id=str(session.id),
        device_id=session.device_id,
        device_type=session.device_type,
        device_model=session.device_model,
        os_version=session.os_version,
        last_active=session.last_active.isoformat(),
        created_at=session.created_at.isoformat(),
    )

