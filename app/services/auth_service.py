"""Authentication service"""

import asyncio
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from hashlib import sha256
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.user import User, UserRole, ClassLevel, TargetExam
from app.models.session import DeviceType, UserSession
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password, decode_token
from app.core.config import settings
from app.services.otp_service import OTPService
from app.services.twilio_service import TwilioService
from app.db.session_calls import create_user_session, invalidate_old_sessions
from app.utils.exceptions import (
    NotFoundException,
    PhoneAlreadyExistsException,
    UnauthorizedException,
    SMSDeliveryException,
    UserNotFoundException,
)
from app.utils.phone import validate_indian_phone


class AuthService:
    def __init__(self, db: AsyncSession, otp_service: OTPService):
        self.db = db
        self.otp_service = otp_service

    async def get_user_by_phone(self, phone_number: str) -> User | None:
        result = await self.db.execute(select(User).where(User.phone_number == phone_number))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _send_otp(self, phone_number: str, temp_token: str, purpose: str) -> str:
        if settings.SMS_PROVIDER == "twilio":
            success = await self.otp_service.send_otp_sms(phone_number, "")
            if not success:
                raise SMSDeliveryException()
            return ""
        else:
            otp = self.otp_service.generate_otp()
            await self.otp_service.store_otp(phone_number, otp, temp_token, purpose=purpose)
            success = await self.otp_service.send_otp_sms(phone_number, otp)
            if not success:
                raise SMSDeliveryException()
            return otp

    async def _verify_otp(self, phone_number: str, temp_token: str, otp: str) -> None:
        if settings.SMS_PROVIDER == "twilio":
            twilio_service = TwilioService()
            await twilio_service.verify_code(phone_number, otp)
        else:
            await self.otp_service.verify_otp(temp_token, otp)

    async def _create_session_and_tokens(
        self,
        user: User,
        device_id: str,
        device_type: DeviceType,
        device_model: str | None,
        os_version: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> dict:
        session_id = uuid4()
        refresh_token = create_refresh_token({"sub": str(user.id), "session_id": str(session_id)})
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()

        session = await create_user_session(
            db=self.db,
            user_id=user.id,
            device_id=device_id,
            device_type=device_type,
            device_model=device_model,
            os_version=os_version,
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        await self.otp_service.redis.set_active_session(
            str(user.id),
            str(session.id),
            expire=86400 * settings.SESSION_TTL_DAYS
        )

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
        }

    async def initiate_signup(
        self,
        phone_number: str,
        name: str,
        class_level: ClassLevel,
        target_exams: list[TargetExam],
        password: str,
        device_id: str,
        role: UserRole,
        device_type: DeviceType,
        device_model: str | None = None,
        os_version: str | None = None,
    ) -> tuple[str, str]:
        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise UnauthorizedException("Invalid phone number")

        existing_user = await self.get_user_by_phone(formatted_phone)
        if existing_user:
            raise PhoneAlreadyExistsException()

        temp_token = self.otp_service.generate_temp_token()

        await self.otp_service.redis.set_value(
            f"signup_data:{temp_token}",
            {
                "phone_number": formatted_phone,
                "name": name,
                "class_level": class_level,
                "role": role,
                "target_exams": [exam.value for exam in target_exams],
                "password_hash": hash_password(password),
                "device_id": device_id,
                "device_type": device_type,
                "device_model": device_model,
                "os_version": os_version,
            },
            expire=300,
        )

        otp = await self._send_otp(formatted_phone, temp_token, "signup")
        return temp_token, otp

    async def verify_signup(self, temp_token: str, otp: str, ip_address: str | None = None, user_agent: str | None = None) -> dict:
        signup_data = await self.otp_service.redis.get_value(f"signup_data:{temp_token}")
        if not signup_data:
            raise UnauthorizedException("Signup session expired")

        phone_number = signup_data["phone_number"]
        await self._verify_otp(phone_number, temp_token, otp)

        user = User(
            phone_number=phone_number,
            password_hash=signup_data["password_hash"],
            name=signup_data["name"],
            class_level=ClassLevel(signup_data["class_level"]),
            target_exams=signup_data["target_exams"],
            role=signup_data["role"],
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        await self.otp_service.redis.delete_key(f"signup_data:{temp_token}")

        result = await self._create_session_and_tokens(
            user=user,
            device_id=signup_data["device_id"],
            device_type=DeviceType(signup_data["device_type"]),
            device_model=signup_data.get("device_model"),
            os_version=signup_data.get("os_version"),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        result["user"] = user
        return result

    async def login(
        self,
        phone_number: str,
        password: str,
        device_id: str | None = None,
        device_type: DeviceType | None = None,
        device_model: str | None = None,
        os_version: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise UnauthorizedException("Invalid phone number")

        user = await self.get_user_by_phone(formatted_phone)
        if not user:
            raise UserNotFoundException("User not found. Please sign up to create an account")

        if not user.is_active:
            raise UnauthorizedException("Account is inactive")

        if not user.password_hash:
            raise UnauthorizedException("Please set up your password first")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid phone number or password")

        session_id = uuid4()
        refresh_token = create_refresh_token({"sub": str(user.id), "session_id": str(session_id)})
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()

        await invalidate_old_sessions(self.db, user.id, commit=False)
        user.updated_at = datetime.utcnow()

        session = UserSession(
            user_id=user.id,
            device_id=device_id or str(uuid4()),
            device_type=device_type or DeviceType.MOBILE,
            device_model=device_model,
            os_version=os_version,
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_active=True,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        await self.otp_service.redis.set_active_session(
            str(user.id),
            str(session.id),
            expire=86400 * settings.SESSION_TTL_DAYS
        )

        access_token = create_access_token({
            "sub": str(user.id),
            "phone": user.phone_number,
            "session_id": str(session.id)
        })

        if device_id:
            asyncio.create_task(self._process_device_info_background(user.id, session.id, device_id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "session_id": str(session.id),
        }

    async def _process_device_info_background(self, user_id: UUID, session_id: UUID, device_id: str) -> None:
        try:
            old_session_id = await self.otp_service.redis.get_active_session(str(user_id))
            if not old_session_id or str(old_session_id) == str(session_id):
                return

            result = await self.db.execute(
                select(UserSession.push_token, UserSession.device_id).where(UserSession.id == UUID(old_session_id))
            )
            row = result.first()
            if row and row[1] != device_id:
                await self.otp_service.redis.set_value(f"force_logout:{old_session_id}", "true", expire=300)
                if row[0]:
                    asyncio.create_task(self._send_logout_notification_async(row[0], str(old_session_id)))
        except Exception:
            pass

    async def _send_logout_notification_async(self, push_token: str, session_id: str) -> None:
        try:
            from app.services.push_notification_service import PushNotificationService
            push_service = PushNotificationService()
            await push_service.send_logout_notification(push_token)
        except Exception:
            pass

    async def register_push_token(self, user_id: str, push_token: str) -> bool:
        try:
            active_session_id = await self.otp_service.redis.get_active_session(user_id)
            if not active_session_id:
                return False

            result = await self.db.execute(
                select(UserSession).where(UserSession.id == UUID(active_session_id))
            )
            session = result.scalar_one_or_none()
            if not session or not session.is_active:
                return False

            await self.db.execute(
                update(UserSession).where(UserSession.id == UUID(active_session_id)).values(push_token=push_token)
            )
            await self.db.commit()
            return True
        except Exception:
            return False

    async def logout(self, user_id: str, session_id: str | None = None) -> bool:
        try:
            if session_id:
                await self.db.execute(
                    update(UserSession).where(UserSession.id == UUID(session_id)).values(push_token=None, is_active=False)
                )
                await self.db.commit()

            await self.otp_service.redis.invalidate_user_session(user_id)
            return True
        except Exception:
            return False

    async def initiate_forgot_password(self, phone_number: str) -> tuple[str, str]:
        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise UnauthorizedException("Invalid phone number")

        user = await self.get_user_by_phone(formatted_phone)
        if not user:
            raise NotFoundException("Phone number not registered")

        if not user.is_active:
            raise UnauthorizedException("Account is inactive")

        temp_token = self.otp_service.generate_temp_token()
        await self.otp_service.redis.set_value(
            f"reset_password:{temp_token}",
            {"phone_number": formatted_phone},
            expire=300,
        )

        otp = await self._send_otp(formatted_phone, temp_token, "reset_password")
        return temp_token, otp

    async def reset_password(self, temp_token: str, otp: str, new_password: str) -> bool:
        reset_data = await self.otp_service.redis.get_value(f"reset_password:{temp_token}")
        if not reset_data:
            raise UnauthorizedException("Password reset session expired")

        phone_number = reset_data["phone_number"]
        await self._verify_otp(phone_number, temp_token, otp)

        user = await self.get_user_by_phone(phone_number)
        if not user:
            raise NotFoundException("User not found")

        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        await self.db.commit()

        await self.otp_service.redis.delete_key(f"reset_password:{temp_token}")
        await invalidate_old_sessions(self.db, user.id)
        await self.otp_service.redis.invalidate_user_session(str(user.id))
        return True

    async def refresh_access_token(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid or expired refresh token")

        user_id_str = payload.get("sub")
        session_id_str = payload.get("session_id")
        if not user_id_str or not session_id_str:
            raise UnauthorizedException("Invalid token payload")

        try:
            user_id = UUID(user_id_str)
            session_id = UUID(session_id_str)
        except ValueError:
            raise UnauthorizedException("Invalid token format")

        result = await self.db.execute(select(UserSession).where(UserSession.id == session_id))
        session = result.scalar_one_or_none()

        if not session or not session.is_active:
            raise UnauthorizedException("Session not found or inactive")

        if session.user_id != user_id:
            raise UnauthorizedException("Session does not belong to user")

        if session.expires_at < datetime.utcnow():
            raise UnauthorizedException("Session has expired")

        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()
        if session.refresh_token_hash != refresh_token_hash:
            raise UnauthorizedException("Invalid refresh token")

        is_valid = await self.otp_service.redis.is_session_valid(user_id_str, session_id_str)
        if not is_valid:
            raise UnauthorizedException("Session is no longer valid")

        user = await self.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

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
        }
