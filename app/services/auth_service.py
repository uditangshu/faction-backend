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
from app.db.session_calls import invalidate_old_sessions
from app.utils.exceptions import (
    NotFoundException,
    PhoneAlreadyExistsException,
    UnauthorizedException,
    SMSDeliveryException,
    UserNotFoundException,
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

        # Check if user already exists
        existing_user = await self.get_user_by_phone(formatted_phone)
        if existing_user:
            raise PhoneAlreadyExistsException()

        temp_token = self.otp_service.generate_temp_token()
        
        # Hash password before storing
        password_hash = hash_password(password)

        # Store signup data including password hash
        await self.otp_service.redis.set_value(
            f"signup_data:{temp_token}",
            {
                "phone_number": formatted_phone,
                "name": name,
                "class_level": class_level,
                "role" : role,
                "target_exams": [exam.value for exam in target_exams],
                "password_hash": password_hash,
                "device_id": device_id,
                "device_type": device_type,
                "device_model": device_model,
                "os_version": os_version,
            },
            expire=300,  # 5 minutes
        )

        if settings.SMS_PROVIDER == "twilio":
            # Twilio generates its own OTP
            success = await self.otp_service.send_otp_sms(formatted_phone, "")
            if not success:
                raise SMSDeliveryException()
            return temp_token, ""  # No OTP returned for Twilio
        else:
            # Mock mode: generate and store our own OTP
            otp = self.otp_service.generate_otp()
            await self.otp_service.store_otp(formatted_phone, otp, temp_token, purpose="signup")
            success = await self.otp_service.send_otp_sms(formatted_phone, otp)
            if not success:
                raise SMSDeliveryException()
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

        # Create user with password hash
        user = User(
            phone_number=phone_number,
            password_hash=signup_data["password_hash"],
            name=signup_data["name"],
            class_level=ClassLevel(signup_data["class_level"]),
            target_exams=signup_data["target_exams"],
            role=signup_data["role"],
        )
        self.db.add(user)
        await self.db.flush()  # Get user.id without commit

        # Create session in same transaction (yadav)
        refresh_token = create_refresh_token({"sub": str(user.id), "session_id": str(uuid4())})
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()

        session = UserSession(
            user_id=user.id,
            device_id=signup_data["device_id"],
            device_type=DeviceType(signup_data["device_type"]),
            device_model=signup_data.get("device_model"),
            os_version=signup_data.get("os_version"),
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_active=True,
        )
        self.db.add(session)
        await self.db.commit()  # Single commit for user + session

        await self.otp_service.redis.delete_key(f"signup_data:{temp_token}")

        # Store active session in Redis (1 year TTL matching refresh token)
        await self.otp_service.redis.set_active_session(
            str(user.id), 
            str(session.id), 
            expire=86400 * settings.SESSION_TTL_DAYS
        )

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
        """Login with phone number and password (yadav)"""
        # Validate phone
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

        # Prepare new session (yadav)
        user_id_str = str(user.id)
        refresh_token = create_refresh_token({"sub": user_id_str, "session_id": str(uuid4())})
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()

        # Get old session data BEFORE changes - needed for logout notification (yadav)
        old_session_id = await self.otp_service.redis.get_active_session(user_id_str)
        old_push_token, old_device_id = None, None
        print(f"🔍 Old session from Redis: {old_session_id}")
        if old_session_id:
            result = await self.db.execute(
                select(UserSession.push_token, UserSession.device_id).where(UserSession.id == UUID(old_session_id))
            )
            row = result.first()
            if row:
                old_push_token, old_device_id = row[0], row[1]
                print(f"🔍 Old session data: device_id={old_device_id}, push_token={old_push_token[:20] if old_push_token else 'NONE'}...")

        # Create new session first (yadav)
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
        await self.db.flush()  # Get session.id without commit

        # Invalidate old sessions EXCLUDING the new one - single batch UPDATE (yadav)
        await invalidate_old_sessions(self.db, user.id, exclude_session_id=session.id, commit=False)
        
        user.updated_at = datetime.utcnow()
        await self.db.commit()

        # Cache active session in Redis
        await self.otp_service.redis.set_active_session(
            user_id_str, str(session.id), expire=86400 * settings.SESSION_TTL_DAYS
        )

        access_token = create_access_token({
            "sub": user_id_str,
            "phone": user.phone_number,
            "session_id": str(session.id)
        })

        # Send logout notification to old device in background (yadav)
        if device_id and old_session_id and old_device_id:
            asyncio.create_task(self._process_device_info_background(
                device_id=device_id,
                old_session_id=old_session_id,
                old_device_id=old_device_id,
                old_push_token=old_push_token,
            ))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "session_id": str(session.id),
        }

    async def _process_device_info_background(
        self,
        device_id: str,
        old_session_id: str,
        old_device_id: str,
        old_push_token: str | None,
    ) -> None:
        """Handle logout notification to old device (yadav)"""
        try:
            is_same_device = old_device_id == device_id
            print(f"🔍 Device check: old={old_device_id}, new={device_id}, same={is_same_device}")
            
            if not is_same_device:
                print(f"🚪 Different device - sending logout notification...")
                print(f"   old_push_token = {old_push_token[:30] if old_push_token else 'NONE'}...")
                await self.otp_service.redis.set_value(f"force_logout:{old_session_id}", "true", expire=300)
                
                if old_push_token:
                    await self._send_logout_notification_async(old_push_token, old_session_id)
                else:
                    print(f"⚠️ No push token on old device - cannot send notification")
        except Exception as e:
            print(f"❌ Background task error: {e}")

    async def _send_logout_notification_async(self, push_token: str, session_id: str) -> None:
        """Fire-and-forget logout notification (yadav)"""
        try:
            from app.services.push_notification_service import PushNotificationService
            success = await PushNotificationService().send_logout_notification(push_token)
            print(f"{'✅' if success else '⚠️'} Logout notification {'sent' if success else 'failed'} for {session_id}")
        except Exception as e:
            print(f"❌ Push notification error: {e}")

    async def register_push_token(self, user_id: str, push_token: str) -> bool:
        """Register push token for current active session (yadav)"""
        try:
            active_session_id = await self.otp_service.redis.get_active_session(user_id)
            if not active_session_id:
                print(f"⚠️ No active session for user {user_id}")
                return False
            
            result = await self.db.execute(
                select(UserSession).where(UserSession.id == UUID(active_session_id))
            )
            session = result.scalar_one_or_none()
            
            if not session or not session.is_active:
                print(f"⚠️ Session {active_session_id} invalid")
                return False
            
            await self.db.execute(
                update(UserSession).where(UserSession.id == UUID(active_session_id)).values(push_token=push_token)
            )
            await self.db.commit()
            print(f"✅ Push token registered for session {active_session_id}")
            return True
        except Exception as e:
            print(f"❌ Push token registration failed: {e}")
            return False

    async def logout(self, user_id: str, session_id: str | None = None) -> bool:
        """Logout user and clear session (yadav)"""
        try:
            if session_id:
                await self.db.execute(
                    update(UserSession).where(UserSession.id == UUID(session_id)).values(push_token=None, is_active=False)
                )
                await self.db.commit()
            
            await self.otp_service.redis.invalidate_user_session(user_id)
            print(f"✅ Logged out user {user_id}")
            return True
        except Exception as e:
            print(f"❌ Logout failed: {e}")
            return False

    async def initiate_forgot_password(self, phone_number: str) -> tuple[str, str]:
        """Initiate forgot password flow - send OTP to user's phone"""
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

        # Store phone number with temp token for password reset verification
        await self.otp_service.redis.set_value(
            f"reset_password:{temp_token}",
            {"phone_number": formatted_phone},
            expire=300,  # 5 minutes
        )

        if settings.SMS_PROVIDER == "twilio":
            # Twilio generates its own OTP
            success = await self.otp_service.send_otp_sms(formatted_phone, "")
            if not success:
                raise SMSDeliveryException()
            return temp_token, ""  # No OTP returned for Twilio
        else:
            # Mock mode: generate and store our own OTP
            otp = self.otp_service.generate_otp()
            await self.otp_service.store_otp(formatted_phone, otp, temp_token, purpose="reset_password")
            success = await self.otp_service.send_otp_sms(formatted_phone, otp)
            if not success:
                raise SMSDeliveryException()
            return temp_token, otp

    async def reset_password(self, temp_token: str, otp: str, new_password: str) -> bool:
        """Reset user password after OTP verification"""
        reset_data = await self.otp_service.redis.get_value(f"reset_password:{temp_token}")
        if not reset_data:
            raise UnauthorizedException("Password reset session expired")

        phone_number = reset_data["phone_number"]

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

        # Hash and update password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        await self.db.commit()

        # Clean up temp data
        await self.otp_service.redis.delete_key(f"reset_password:{temp_token}")

        # Invalidate all user sessions (force re-login on all devices)
        await invalidate_old_sessions(self.db, user.id)
        await self.otp_service.redis.invalidate_user_session(str(user.id))

        print(f"✅ Password reset successful for user {user.id}")
        return True

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token (yadav)"""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid or expired refresh token")
        
        user_id_str, session_id_str = payload.get("sub"), payload.get("session_id")
        if not user_id_str or not session_id_str:
            raise UnauthorizedException("Invalid token payload")
        
        try:
            user_id, session_id = UUID(user_id_str), UUID(session_id_str)
        except ValueError:
            raise UnauthorizedException("Invalid token format")
        
        # Validate session in DB (source of truth)
        result = await self.db.execute(select(UserSession).where(UserSession.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session or not session.is_active:
            raise UnauthorizedException("Session not found or inactive")
        if session.user_id != user_id:
            raise UnauthorizedException("Session does not belong to user")
        if session.expires_at < datetime.utcnow():
            raise UnauthorizedException("Session has expired")
        if sha256(refresh_token.encode()).hexdigest() != session.refresh_token_hash:
            raise UnauthorizedException("Invalid refresh token")
        
        # Re-sync Redis if needed (yadav)
        try:
            is_valid = await self.otp_service.redis.is_session_valid(user_id_str, session_id_str)
            if not is_valid:
                await self.otp_service.redis.set_active_session(user_id_str, session_id_str, expire=86400 * settings.SESSION_TTL_DAYS)
        except Exception:
            pass  # Redis optional, DB is truth
        
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

