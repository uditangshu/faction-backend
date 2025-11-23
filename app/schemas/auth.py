"""Authentication schemas"""

from pydantic import BaseModel, Field, field_validator
from app.models.user import ClassLevel, TargetExam
from app.models.session import DeviceType


class DeviceInfo(BaseModel):
    """Device information schema"""

    device_id: str = Field(..., description="Unique device identifier (UUID)", min_length=1, max_length=255)
    device_type: DeviceType = Field(..., description="Device type (mobile/tablet/desktop)")
    device_model: str | None = Field(None, description="Device model (e.g., iPhone 14, Samsung S23)", max_length=100)
    os_version: str | None = Field(None, description="OS version (e.g., iOS 17.1, Android 13)", max_length=50)


class SignupRequest(BaseModel):
    """Signup request schema"""

    phone_number: str = Field(..., description="Phone number with country code", min_length=10, max_length=15)
    name: str = Field(..., description="Full name", min_length=2, max_length=100)
    class_level: ClassLevel = Field(..., description="Student class")
    target_exams: list[TargetExam] = Field(..., description="Target entrance exams (at least 1 required)", min_length=1)
    device_info: DeviceInfo = Field(..., description="Device information")

    @field_validator('target_exams')
    @classmethod
    def validate_target_exams(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one target exam must be selected')
        return v


class SignupResponse(BaseModel):
    """Signup response schema"""

    temp_token: str
    otp_sent: bool
    expires_in: int = 300  # seconds


class LoginRequest(BaseModel):
    """Login request schema"""

    phone_number: str = Field(..., description="Phone number with country code", min_length=10, max_length=15)
    device_info: DeviceInfo = Field(..., description="Device information")


class LoginResponse(BaseModel):
    """Login response schema"""

    temp_token: str
    otp_sent: bool
    expires_in: int = 300  # seconds


class VerifyOTPRequest(BaseModel):
    """OTP verification request schema"""

    temp_token: str = Field(..., description="Temporary token from signup/login")
    otp: str = Field(..., description="4-digit OTP code", min_length=4, max_length=4)


class TokenResponse(BaseModel):
    """Token response schema"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # seconds (30 minutes)
    session_id: str = Field(..., description="Active session ID")


class CurrentDeviceResponse(BaseModel):
    """Current device information response"""

    session_id: str
    device_id: str
    device_type: DeviceType
    device_model: str | None
    os_version: str | None
    last_active: str
    created_at: str

