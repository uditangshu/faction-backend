"""Authentication endpoints"""

from fastapi import APIRouter, status, Request
from app.api.v1.dependencies import AuthServiceDep
from app.schemas.auth import (
    SignupRequest,
    SignupResponse,
    LoginRequest,
    LoginResponse,
    VerifyOTPRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse

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
        "expires_in": 1800,  # 30 minutes
    }


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    auth_service: AuthServiceDep,
) -> LoginResponse:
    temp_token, otp = await auth_service.initiate_login(
        phone_number=request.phone_number,
        device_id=request.device_info.device_id,
        device_type=request.device_info.device_type,
        device_model=request.device_info.device_model,
        os_version=request.device_info.os_version,
    )
    
    return LoginResponse(
        temp_token=temp_token,
        otp_sent=True,
        expires_in=300,
    )


@router.post("/verify-otp", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def verify_otp(
    verify_request: VerifyOTPRequest,
    http_request: Request,
    auth_service: AuthServiceDep,
) -> dict:
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    
    result = await auth_service.verify_login(
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
        "expires_in": 1800,  # 30 minutes
    }

