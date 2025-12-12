"""Authentication service"""

import asyncio
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
    """Service for authentication operations - stateless, accepts db as method parameter"""

    def __init__(self, otp_service: OTPService):
        self.otp_service = otp_service

    async def get_user_by_phone(self, db: AsyncSession, phone_number: str) -> User | None:
        """Get user by phone number"""
        result = await db.execute(select(User).where(User.phone_number == phone_number))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        """Get user by ID"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def initiate_signup(
        self,
        db: AsyncSession,
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
        existing_user = await self.get_user_by_phone(db, formatted_phone)
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

    async def verify_signup(self, db: AsyncSession, temp_token: str, otp: str, ip_address: str | None = None, user_agent: str | None = None) -> dict:
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

        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Delete signup data
        await self.otp_service.redis.delete_key(f"signup_data:{temp_token}")

        # Create session
        session_id = uuid4()
        refresh_token = create_refresh_token({"sub": str(user.id), "session_id": str(session_id)})
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()

        session = await create_user_session(
            db=db,
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
        db: AsyncSession,
        phone_number: str,
        password: str,
        device_id: str | None = None,
        device_type: DeviceType | None = None,
        device_model: str | None = None,
        os_version: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Login with phone number and password - returns tokens immediately, processes device info in background"""
        # STEP 1: Validate credentials (fast path - no device info needed)
        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise UnauthorizedException("Invalid phone number")

        # Get user
        user = await self.get_user_by_phone(db, formatted_phone)
        if not user:
            raise UserNotFoundException("User not found. Please sign up to create an account")

        if not user.is_active:
            raise UnauthorizedException("Account is inactive")

        # Verify password
        if not user.password_hash:
            raise UnauthorizedException("Please set up your password first")
        
        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid phone number or password")

        # STEP 2: Create minimal session and return tokens immediately
        # Device info processing happens in background if not provided
        session_id = uuid4()
        refresh_token = create_refresh_token({"sub": str(user.id), "session_id": str(session_id)})
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()

        # Invalidate old sessions (without commit - will commit with session creation)
        invalidated_count = await invalidate_old_sessions(db, user.id, commit=False)
        
        # Update user.updated_at
        user.updated_at = datetime.utcnow()
        
        # Create new session (with device info if provided, temporary UUID otherwise)
        # If device_id not provided, use temporary UUID - will be updated in background
        from app.models.session import UserSession
        temp_device_id = device_id or str(uuid4())  # Temporary UUID if device info not provided
        session = UserSession(
            user_id=user.id,
            device_id=temp_device_id,
            device_type=device_type or DeviceType.MOBILE,  # Default to mobile
            device_model=device_model,
            os_version=os_version,
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_active=True,
        )
        db.add(session)
        
        # Single commit for: invalidate old sessions + create new session + update user
        await db.commit()
        await db.refresh(session)

        # Store active session in Redis immediately (1 year TTL matching refresh token)
        user_id_str = str(user.id)
        await self.otp_service.redis.set_active_session(
            user_id_str, 
            str(session.id),
            expire=86400 * settings.SESSION_TTL_DAYS
        )

        # Generate access token with session_id
        access_token = create_access_token({
            "sub": str(user.id),
            "phone": user.phone_number,
            "session_id": str(session.id)
        })

        # STEP 3: Process device info and old session logic in background (non-blocking)
        # Note: Background task must create its own session - cannot use request session
        if device_id:
            # Only process old session logic if device_id is provided
            asyncio.create_task(self._process_device_info_background(
                user_id=user.id,
                session_id=session.id,
                device_id=device_id,
            ))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "session_id": str(session.id),
        }

    async def _process_device_info_background(
        self,
        user_id: UUID,
        session_id: UUID,
        device_id: str,
    ) -> None:
        """Process device info and old session logic in background (non-blocking)
        
        NOTE: This method creates its own database session since it runs in background
        and cannot use the request session which is already closed.
        """
        from app.db.session import AsyncSessionLocal
        from app.models.session import UserSession
        
        async with AsyncSessionLocal() as db:
            try:
                # Get old active session ID from Redis
                old_session_id = await self.otp_service.redis.get_active_session(str(user_id))
                
                # Get old session details if exists
                old_push_token = None
                old_device_id = None
                is_same_device = False
                
                if old_session_id and str(old_session_id) != str(session_id):
                    result = await db.execute(
                        select(UserSession.push_token, UserSession.device_id).where(UserSession.id == UUID(old_session_id))
                    )
                    row = result.first()
                    if row:
                        old_push_token = row[0]
                        old_device_id = row[1]
                        is_same_device = old_device_id == device_id
                        
                        # Handle different device login
                        if not is_same_device:
                            # Mark old session for force logout
                            await self.otp_service.redis.set_value(
                                f"force_logout:{old_session_id}",
                                "true",
                                expire=300
                            )
                            
                            # Send push notification to OLD device (non-blocking)
                            if old_push_token:
                                asyncio.create_task(self._send_logout_notification_async(old_push_token, str(old_session_id)))
            except Exception as e:
                print(f"❌ Error processing device info in background: {e}")
                # Non-critical - login already succeeded

    async def _send_logout_notification_async(self, push_token: str, session_id: str) -> None:
        """Send logout notification asynchronously (fire and forget)"""
        try:
            from app.services.push_notification_service import PushNotificationService
            push_service = PushNotificationService()
            success = await push_service.send_logout_notification(push_token)
            if success:
                print(f"✅ Logout push notification sent successfully for session {session_id}")
            else:
                print(f"⚠️ Logout push notification failed for session {session_id}")
        except Exception as e:
            print(f"❌ Failed to send logout push notification for session {session_id}: {e}")

    async def register_push_token(self, db: AsyncSession, user_id: str, push_token: str) -> bool:
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
            result = await db.execute(
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
            await db.execute(stmt)
            await db.commit()
            
            print(f"✅ Push token registered successfully for NEW device's session {active_session_id}")
            print(f"✅ This push token will receive notifications for future logins from other devices")
            return True
        except Exception as e:
            print(f"❌ Failed to register push token: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    async def logout(self, db: AsyncSession, user_id: str, session_id: str | None = None) -> bool:
        
        try:
            print(f"🔓 Logging out user {user_id}, session {session_id}")
            
            from app.models.session import UserSession
            from sqlalchemy import update
            
            # If we have a session_id, clear the push token and mark it inactive
            if session_id:
                # Clear push token first - this prevents logout notification on re-login
                stmt = (
                    update(UserSession)
                    .where(UserSession.id == UUID(session_id))
                    .values(push_token=None, is_active=False)
                )
                await db.execute(stmt)
                await db.commit()
                print(f"✅ Session {session_id} push token cleared and marked inactive")
            
            # Invalidate the active session in Redis
            await self.otp_service.redis.invalidate_user_session(user_id)
            print(f"✅ Active session removed from Redis for user {user_id}")
            
            return True
        except Exception as e:
            print(f"❌ Failed to logout: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    async def initiate_forgot_password(self, db: AsyncSession, phone_number: str) -> tuple[str, str]:
        """Initiate forgot password flow - send OTP to user's phone"""
        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise UnauthorizedException("Invalid phone number")

        # Check if user exists
        user = await self.get_user_by_phone(db, formatted_phone)
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

    async def reset_password(self, db: AsyncSession, temp_token: str, otp: str, new_password: str) -> bool:
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
        user = await self.get_user_by_phone(db, phone_number)
        if not user:
            raise NotFoundException("User not found")

        # Hash and update password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        await db.commit()

        # Clean up temp data
        await self.otp_service.redis.delete_key(f"reset_password:{temp_token}")

        # Invalidate all user sessions (force re-login on all devices)
        await invalidate_old_sessions(db, user.id)
        await self.otp_service.redis.invalidate_user_session(str(user.id))

        print(f"✅ Password reset successful for user {user.id}")
        return True

    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        from app.core.security import decode_token
        from app.models.session import UserSession
        
        # Decode and validate refresh token
        payload = decode_token(refresh_token)
        if not payload:
            raise UnauthorizedException("Invalid or expired refresh token")
        
        # Check token type
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")
        
        # Get user_id and session_id from token
        user_id_str = payload.get("sub")
        session_id_str = payload.get("session_id")
        
        if not user_id_str or not session_id_str:
            raise UnauthorizedException("Invalid token payload")
        
        try:
            user_id = UUID(user_id_str)
            session_id = UUID(session_id_str)
        except ValueError:
            raise UnauthorizedException("Invalid token format")
        
        # Get session from database
        result = await db.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise UnauthorizedException("Session not found")
        
        if not session.is_active:
            raise UnauthorizedException("Session is inactive")
        
        # Check if session belongs to the user
        if session.user_id != user_id:
            raise UnauthorizedException("Session does not belong to user")
        
        # Check if session has expired
        if session.expires_at < datetime.utcnow():
            raise UnauthorizedException("Session has expired")
        
        # Verify refresh token hash
        refresh_token_hash = sha256(refresh_token.encode()).hexdigest()
        if session.refresh_token_hash != refresh_token_hash:
            raise UnauthorizedException("Invalid refresh token")
        
        # Verify session is still active in Redis
        is_valid = await self.otp_service.redis.is_session_valid(user_id_str, session_id_str)
        if not is_valid:
            raise UnauthorizedException("Session is no longer valid")
        
        # Get user for token generation
        user = await self.get_user_by_id(db, user_id)
        if not user:
            raise UnauthorizedException("User not found")
        
        if not user.is_active:
            raise UnauthorizedException("Account is inactive")
        
        # Generate new access token with same session_id
        access_token = create_access_token({
            "sub": str(user.id),
            "phone": user.phone_number,
            "session_id": str(session.id)
        })
        
        # Optionally rotate refresh token (for now, reuse the same one)
        # To rotate: generate new refresh token, update hash in DB
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,  # Reuse same refresh token
            "token_type": "bearer",
            "session_id": str(session.id),
        }
