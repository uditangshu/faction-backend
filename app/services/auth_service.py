"""Authentication service"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4
from hashlib import sha256
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole, ClassLevel, TargetExam
from app.models.session import DeviceType
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
from app.services.otp_service import OTPService
from app.services.twilio_service import TwilioService
from app.db.session_calls import create_user_session, invalidate_old_sessions
from app.utils.exceptions import (
    NotFoundException,
    PhoneAlreadyExistsException,
    UnauthorizedException,
)
from app.utils.phone import validate_indian_phone


class AuthService:
    """Service for authentication operations"""

    def __init__(self, db: AsyncSession, otp_service: OTPService):
        self.db = db
        self.otp_service = otp_service

    async def get_user_by_phone(self, phone_number: str) -> User | None:
        """Get user by phone number"""
        result = await self.db.execute(select(User).where(User.phone_number == phone_number))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def initiate_signup(
        self,
        phone_number: str,
        name: str,
        class_level: ClassLevel,
        target_exams: list[TargetExam],
        device_id: str,
        device_type: DeviceType,
        device_model: str | None = None,
        os_version: str | None = None,
    ) -> tuple[str, str]:
        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise UnauthorizedException("Invalid phone number")

        # Check if user already exists
        existing_user = await self.get_user_by_phone(formatted_phone)
        if existing_user:
            raise PhoneAlreadyExistsException()

        temp_token = self.otp_service.generate_temp_token()

        # Store signup data
        await self.otp_service.redis.set_value(
            f"signup_data:{temp_token}",
            {
                "phone_number": formatted_phone,
                "name": name,
                "class_level": class_level,
                "target_exams": [exam.value for exam in target_exams],
                "device_id": device_id,
                "device_type": device_type,
                "device_model": device_model,
                "os_version": os_version,
            },
            expire=300,  # 5 minutes
        )

        if settings.SMS_PROVIDER == "twilio":
            # Twilio generates its own OTP
            await self.otp_service.send_otp_sms(formatted_phone, "")
            return temp_token, ""  # No OTP returned for Twilio
        else:
            # Mock mode: generate and store our own OTP
            otp = self.otp_service.generate_otp()
            await self.otp_service.store_otp(formatted_phone, otp, temp_token, purpose="signup")
            await self.otp_service.send_otp_sms(formatted_phone, otp)
            return temp_token, otp

    async def verify_signup(self, temp_token: str, otp: str, ip_address: str | None = None, user_agent: str | None = None) -> dict:
        signup_data = await self.otp_service.redis.get_value(f"signup_data:{temp_token}")
        if not signup_data:
            raise UnauthorizedException("Signup session expired")

        phone_number = signup_data["phone_number"]

        # Verify OTP based on provider
        if settings.SMS_PROVIDER == "twilio":
            # Verify with Twilio
            twilio_service = TwilioService()
            await twilio_service.verify_code(phone_number, otp)
        else:
            # Verify with our OTP system (mock mode)
            await self.otp_service.verify_otp(temp_token, otp)

        # Create user
        user = User(
            phone_number=phone_number,
            name=signup_data["name"],
            class_level=ClassLevel(signup_data["class_level"]),
            target_exams=signup_data["target_exams"],
            role=UserRole.STUDENT,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Delete signup data
        await self.otp_service.redis.delete_key(f"signup_data:{temp_token}")

        # Create session
        session_id = uuid4()
        refresh_token = create_refresh_token({"sub": str(user.id), "session_id": str(session_id)})
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()

        session = await create_user_session(
            db=self.db,
            user_id=user.id,
            device_id=signup_data["device_id"],
            device_type=DeviceType(signup_data["device_type"]),
            device_model=signup_data.get("device_model"),
            os_version=signup_data.get("os_version"),
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        # Store active session in Redis
        await self.otp_service.redis.set_active_session(str(user.id), str(session.id))

        # Generate access token with session_id
        access_token = create_access_token({
            "sub": str(user.id),
            "phone": user.phone_number,
            "session_id": str(session.id)
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "session_id": str(session.id),
            "user": user,
        }

    async def initiate_login(
        self,
        phone_number: str,
        device_id: str,
        device_type: DeviceType,
        device_model: str | None = None,
        os_version: str | None = None,
    ) -> tuple[str, str]:
        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise UnauthorizedException("Invalid phone number")

        # Check if user exists
        user = await self.get_user_by_phone(formatted_phone)
        if not user:
            raise NotFoundException("Phone number not registered")

        if not user.is_active:
            raise UnauthorizedException("Account is inactive")

        temp_token = self.otp_service.generate_temp_token()

        # Store phone number with temp token for verification
        await self.otp_service.redis.set_value(
            f"login_phone:{temp_token}",
            {
                "phone_number": formatted_phone,
                "device_id": device_id,
                "device_type": device_type,
                "device_model": device_model,
                "os_version": os_version,
            },
            expire=300,
        )

        if settings.SMS_PROVIDER == "twilio":
            # Twilio generates its own OTP
            await self.otp_service.send_otp_sms(formatted_phone, "")
            return temp_token, ""  # No OTP returned for Twilio
        else:
            # Mock mode: generate and store our own OTP
            otp = self.otp_service.generate_otp()
            await self.otp_service.store_otp(formatted_phone, otp, temp_token, purpose="login")
            await self.otp_service.send_otp_sms(formatted_phone, otp)
            return temp_token, otp

    async def verify_login(self, temp_token: str, otp: str, ip_address: str | None = None, user_agent: str | None = None) -> dict:
        login_data = await self.otp_service.redis.get_value(f"login_phone:{temp_token}")
        if not login_data:
            raise UnauthorizedException("Login session expired")

        phone_number = login_data["phone_number"]

        # Verify OTP based on provider
        if settings.SMS_PROVIDER == "twilio":
            # Verify with Twilio
            twilio_service = TwilioService()
            await twilio_service.verify_code(phone_number, otp)
        else:
            # Verify with our OTP system (mock mode)
            await self.otp_service.verify_otp(temp_token, otp)

        # Get user
        user = await self.get_user_by_phone(phone_number)
        if not user:
            raise NotFoundException("User not found")

        # Clean up temp data
        await self.otp_service.redis.delete_key(f"login_phone:{temp_token}")

        # Invalidate all old sessions for this user (enforce single device)
        await invalidate_old_sessions(self.db, user.id)

        # Create new session
        session_id = uuid4()
        refresh_token = create_refresh_token({"sub": str(user.id), "session_id": str(session_id)})
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()

        session = await create_user_session(
            db=self.db,
            user_id=user.id,
            device_id=login_data["device_id"],
            device_type=DeviceType(login_data["device_type"]),
            device_model=login_data.get("device_model"),
            os_version=login_data.get("os_version"),
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        # Store active session in Redis (overwrites old session)
        await self.otp_service.redis.set_active_session(str(user.id), str(session.id))

        # Update last login
        user.updated_at = datetime.utcnow()
        await self.db.commit()

        # Generate access token with session_id
        access_token = create_access_token({
            "sub": str(user.id),
            "phone": user.phone_number,
            "session_id": str(session.id)
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "session_id": str(session.id),
            "user": user,
        }

