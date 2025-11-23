"""Authentication related exceptions"""

from fastapi import HTTPException, status
from app.exceptions.base import AppException


class UnauthorizedException(HTTPException):
    """Unauthorized access exception"""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class InvalidOTPException(HTTPException):
    """Invalid OTP exception"""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP",
        )


class OTPExpiredException(HTTPException):
    """OTP expired exception"""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one",
        )


class TooManyAttemptsException(HTTPException):
    """Too many attempts exception"""

    def __init__(self, detail: str = "Too many attempts. Please try again later"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class PhoneAlreadyExistsException(HTTPException):
    """Phone number already exists"""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )


class SessionExpiredException(HTTPException):
    """Session expired on another device"""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session expired because you logged in on another device. Please log in again.",
        )

