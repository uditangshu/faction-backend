"""Custom exceptions module"""

from app.exceptions.base import AppException
from app.exceptions.auth_exceptions import (
    InvalidOTPException,
    OTPExpiredException,
    TooManyAttemptsException,
    PhoneAlreadyExistsException,
    UnauthorizedException,
)
from app.exceptions.http_exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    ConflictException,
)

__all__ = [
    "AppException",
    "InvalidOTPException",
    "OTPExpiredException",
    "TooManyAttemptsException",
    "PhoneAlreadyExistsException",
    "UnauthorizedException",
    "NotFoundException",
    "BadRequestException",
    "ForbiddenException",
    "ConflictException",
]

