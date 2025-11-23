"""OTP verification model"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class OTPPurpose(str, Enum):
    """OTP purpose enumeration"""
    SIGNUP = "signup"
    LOGIN = "login"
    PASSWORD_RESET = "password_reset"


class OTPVerification(SQLModel, table=True):
    """OTP verification records (DB fallback, primary storage is Redis)"""
    
    __tablename__ = "otp_verifications"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone_number: str = Field(index=True, max_length=15)
    otp_code: str = Field(max_length=6)
    purpose: OTPPurpose
    expires_at: datetime
    verified_at: datetime | None = None
    attempts: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

