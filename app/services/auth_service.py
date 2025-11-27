"""Authentication service"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4
from hashlib import sha256
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole, ClassLevel, TargetExam
from app.models.session import DeviceType
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
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
        device_type: DeviceType,
        role : UserRole,
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

    async def login(
        self,
        phone_number: str,
        password: str,
        device_id: str,
        device_type: DeviceType,
        device_model: str | None = None,
        os_version: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Login with phone number and password - returns tokens immediately"""
        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise UnauthorizedException("Invalid phone number")

        # Get user
        user = await self.get_user_by_phone(formatted_phone)
        if not user:
            raise UserNotFoundException("User not found. Please sign up to create an account")

        if not user.is_active:
            raise UnauthorizedException("Account is inactive")

        # Verify password
        if not user.password_hash:
            raise UnauthorizedException("Please set up your password first")
        
        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid phone number or password")

        # Get old active session before invalidating (for force logout and push notification)
        old_session_id = await self.otp_service.redis.get_active_session(str(user.id))
        print(f"🔍 Old active session ID: {old_session_id}")
        
        # Get old session's push token before invalidating
        old_push_token = None
        if old_session_id:
            from app.models.session import UserSession
            result = await self.db.execute(
                select(UserSession).where(UserSession.id == UUID(old_session_id))
            )
            old_session = result.scalar_one_or_none()
            if old_session:
                old_push_token = old_session.push_token
                print(f"📱 Found old push token for session {old_session_id}: {old_push_token[:20] if old_push_token else 'None'}...")
        
        # Invalidate all old sessions for this user (enforce single device)
        # This happens BEFORE creating the new session to ensure old sessions are marked inactive
        invalidated_count = await invalidate_old_sessions(self.db, user.id)
        print(f"🔒 Invalidated {invalidated_count} old session(s)")

        # Mark old session for immediate force logout (if it existed)
        if old_session_id:
            await self.otp_service.redis.set_force_logout(old_session_id)
            print(f"🚪 Marked old session {old_session_id} for force logout")
            
        # Send push notification to OLD device to force logout
        # This notification goes ONLY to the old device, not the new one
        if old_push_token:
            print(f"📱 Sending logout notification to OLD device (token: {old_push_token[:20]}...)")
            try:
                from app.services.push_notification_service import PushNotificationService
                push_service = PushNotificationService()
                success = await push_service.send_logout_notification(old_push_token)
                if success:
                    print("✅ Logout push notification sent successfully to OLD device")
                else:
                    print("⚠️ Logout push notification failed")
            except Exception as e:
                print(f"❌ Failed to send logout push notification: {e}")
                # Don't block login if push notification fails
        else:
            print("⚠️ No push token found for old session - old device won't receive logout notification")

        # Create NEW session for the NEW device
        session_id = uuid4()
        print(f"🆕 Creating new session for NEW device: {session_id}")
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
            expires_at=datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        # Store active session in Redis (overwrites old session)
        # This ensures the new device's session is now the active one
        await self.otp_service.redis.set_active_session(str(user.id), str(session.id))
        print(f"✅ New session {session.id} set as active (old session {old_session_id} is no longer active)")

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

    async def register_push_token(self, user_id: str, push_token: str) -> bool:
        """
        Register push notification token for the current active session.
        This ensures the push token is only registered to the NEW device's session,
        not the old one that was just invalidated.
        """
        try:
            print(f"📱 Registering push token for user {user_id}: {push_token[:20]}...")
            
            # Get the active session ID from Redis
            # This will be the NEW session if user just logged in from a new device
            active_session_id = await self.otp_service.redis.get_active_session(user_id)
            if not active_session_id:
                print(f"⚠️ No active session found for user {user_id}")
                return False
            
            print(f"📱 Active session ID: {active_session_id} (this is the NEW device's session)")
            
            # Verify the session exists and is active
            from app.models.session import UserSession
            result = await self.db.execute(
                select(UserSession).where(UserSession.id == UUID(active_session_id))
            )
            session = result.scalar_one_or_none()
            
            if not session:
                print(f"❌ Session {active_session_id} not found in database")
                return False
            
            if not session.is_active:
                print(f"⚠️ Session {active_session_id} is not active - this shouldn't happen")
                return False
            
            # Update the session with push token
            from sqlalchemy import update
            
            stmt = (
                update(UserSession)
                .where(UserSession.id == UUID(active_session_id))
                .values(push_token=push_token)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            
            print(f"✅ Push token registered successfully for NEW device's session {active_session_id}")
            print(f"✅ This push token will receive notifications for future logins from other devices")
            return True
        except Exception as e:
            print(f"❌ Failed to register push token: {e}")
            import traceback
            print(traceback.format_exc())
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

