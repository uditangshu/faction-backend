"""Custom exception classes"""

from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    """Resource not found exception"""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(HTTPException):
    """Bad request exception"""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(HTTPException):
    """Unauthorized exception"""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(HTTPException):
    """Forbidden exception"""

    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ConflictException(HTTPException):
    """Conflict exception (e.g., duplicate resource)"""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InvalidOTPException(BadRequestException):
    """Invalid OTP exception"""

    def __init__(self):
        super().__init__(detail="Invalid or expired OTP")


class OTPExpiredException(BadRequestException):
    """OTP expired exception"""

    def __init__(self):
        super().__init__(detail="OTP has expired. Please request a new one")


class TooManyAttemptsException(HTTPException):
    """Too many attempts exception"""

    def __init__(self, detail: str = "Too many attempts. Please try again later"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class PhoneAlreadyExistsException(ConflictException):
    """Phone number already exists"""

    def __init__(self):
        super().__init__(detail="Phone number already registered")


class SMSDeliveryException(HTTPException):
    """SMS delivery failed exception"""

    def __init__(self, detail: str = "Failed to send OTP. Please try again later"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class UserNotFoundException(NotFoundException):
    """User not found exception (for new user detection)"""

    def __init__(self, detail: str = "User not found. Please sign up to create an account"):
        super().__init__(detail=detail)

