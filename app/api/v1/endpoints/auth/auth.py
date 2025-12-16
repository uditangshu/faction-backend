"""Authentication endpoints"""

from typing import Annotated
import json
from fastapi import APIRouter, status, Request, BackgroundTasks
from pydantic import BaseModel
from app.api.v1.dependencies import AuthServiceDep, CurrentUserDep
from app.schemas.auth import (
    SignupRequest,
    SignupResponse,
    LoginRequest,
    VerifyOTPRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.user import UserResponse


class PushTokenRequest(BaseModel):
    """Request schema for registering push token"""
    push_token: str


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token"""
    refresh_token: str

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_200_OK)
async def signup(
    request: SignupRequest,
    auth_service: AuthServiceDep,
) -> SignupResponse:
    temp_token, otp = await auth_service.initiate_signup(
        phone_number=request.phone_number,
        name=request.name,
        class_level=request.class_level,
        target_exams=request.target_exams,
        password=request.password,
        role= request.role,
        device_id=request.device_info.device_id,
        device_type=request.device_info.device_type,
        device_model=request.device_info.device_model,
        os_version=request.device_info.os_version,
    )
    
    return SignupResponse(
        temp_token=temp_token,
        otp_sent=True,
        expires_in=300,
    )


@router.post("/verify-signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def verify_signup(
    verify_request: VerifyOTPRequest,
    http_request: Request,
    auth_service: AuthServiceDep,
) -> dict:
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    
    result = await auth_service.verify_signup(
        temp_token=verify_request.temp_token,
        otp=verify_request.otp,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": result["token_type"],
        "session_id": result["session_id"],
        "expires_in": 90 * 24 * 60 * 60,  # 3 months (7,776,000 seconds)
    }


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: AuthServiceDep,
    background_tasks: BackgroundTasks,
) -> dict:
    """Login - returns tokens immediately, push notification runs in background (yadav)"""
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    device_info = request.device_info
   
    result = await auth_service.login(
        phone_number=request.phone_number,
        password=request.password,
        device_id=device_info.device_id if device_info else None,
        device_type=device_info.device_type if device_info else None,
        device_model=device_info.device_model if device_info else None,
        os_version=device_info.os_version if device_info else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    size=len(json.dumps(result).encode("utf-8"))
    print(size)

    # Schedule push notification in background AFTER response is sent (yadav)
    if result.get("background_task_data"):
        data = result["background_task_data"]
        background_tasks.add_task(
            auth_service._process_device_info_background,
            device_id=data["device_id"],
            old_session_id=data["old_session_id"],
            old_device_id=data["old_device_id"],
            old_push_token=data["old_push_token"],
        )
    
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": result["token_type"],
        "session_id": result["session_id"],
        "expires_in": 90 * 24 * 60 * 60,
    }


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthServiceDep,
) -> dict:
    """Refresh access token using refresh token"""
    try:
        result = await auth_service.refresh_access_token(request.refresh_token)
        return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "session_id": result["session_id"],
            "expires_in": 90 * 24 * 60 * 60,  # 3 months (7,776,000 seconds)
        }
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Token refresh failed: {str(e)}")
        raise


@router.get("/session-check", status_code=status.HTTP_200_OK)
async def session_check(current_user: CurrentUserDep) -> dict:
    """
    Lightweight endpoint to check if session is still valid.
    Returns 401 if session has been invalidated (e.g., from another device login).
    """
    return {
        "valid": True,
        "user_id": str(current_user.id),
    }


@router.post("/register-push-token", status_code=status.HTTP_200_OK)
async def register_push_token(
    request: PushTokenRequest,
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> dict:
    """
    Register push notification token for the current session.
    Used for instant logout notifications when user logs in from another device.
    """
    await auth_service.register_push_token(str(current_user.id), request.push_token)
    return {"success": True}

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
    request: Request,
) -> dict:
    """
    Logout the current user.
    - Invalidates the current session
    - Clears the push token (prevents logout notifications on re-login from same device)
    - Removes the active session from Redis
    """
    # Extract session_id from JWT token in Authorization header
    session_id = None
    authorization = request.headers.get("authorization")
    if authorization:
        try:
            from app.core.security import decode_token
            # HTTPBearer format: "Bearer <token>"
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() == "bearer":
                payload = decode_token(token)
                session_id = payload.get("session_id") if payload else None
        except Exception:
            pass

    await auth_service.logout(str(current_user.id), session_id)
    return {"success": True, "message": "Logged out successfully"}


@router.post("/forgot-password", response_model=SignupResponse, status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: AuthServiceDep,
) -> SignupResponse:
    """Initiate forgot password flow - sends OTP to user's phone"""
    temp_token, otp = await auth_service.initiate_forgot_password(
        phone_number=request.phone_number
    )
    
    return SignupResponse(
        temp_token=temp_token,
        otp_sent=True,
        expires_in=300,
    )


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthServiceDep,
) -> dict:
    """Reset password after OTP verification"""
    await auth_service.reset_password(
        temp_token=request.temp_token,
        otp=request.otp,
        new_password=request.new_password,
    )
    
    return {
        "success": True,
        "message": "Password reset successfully. Please login with your new password."
    }

