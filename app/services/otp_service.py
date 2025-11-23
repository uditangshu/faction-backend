"""OTP generation and validation service"""

import random
import secrets
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.redis import RedisService
from app.utils.exceptions import InvalidOTPException, OTPExpiredException, TooManyAttemptsException
from app.services.twilio_service import TwilioService


class OTPService:
    """Service for OTP operations"""

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
        self.otp_length = settings.OTP_LENGTH
        self.otp_expire_minutes = settings.OTP_EXPIRE_MINUTES
        self.max_attempts = settings.OTP_MAX_ATTEMPTS

    def generate_otp(self) -> str:
        # Generate cryptographically secure random OTP
        otp = ''.join([str(random.SystemRandom().randint(0, 9)) for _ in range(self.otp_length)])
        return otp

    def generate_temp_token(self) -> str:
        return secrets.token_urlsafe(32)

    async def store_otp(
        self, phone_number: str, otp: str, temp_token: str, purpose: str = "login"
    ) -> None:
        key = f"otp:{temp_token}"
        data = {
            "phone_number": phone_number,
            "otp": otp,
            "purpose": purpose,
            "attempts": 0,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store with expiration
        expire_seconds = self.otp_expire_minutes * 60
        await self.redis.set_value(key, data, expire=expire_seconds)

    async def verify_otp(self, temp_token: str, otp: str) -> Optional[dict]:
        key = f"otp:{temp_token}"
        data = await self.redis.get_value(key)

        if not data:
            raise OTPExpiredException()

        # Check attempts
        if data.get("attempts", 0) >= self.max_attempts:
            await self.redis.delete_key(key)
            raise TooManyAttemptsException("Maximum OTP attempts exceeded")

        # Increment attempts
        data["attempts"] = data.get("attempts", 0) + 1
        expire_seconds = self.otp_expire_minutes * 60
        await self.redis.set_value(key, data, expire=expire_seconds)

        # Verify OTP
        if data.get("otp") != otp:
            raise InvalidOTPException()

        # OTP is valid, delete it
        await self.redis.delete_key(key)

        return data

    async def send_otp_sms(self, phone_number: str, otp: str) -> bool:
        if settings.SMS_PROVIDER == "mock":
            return await self._send_mock_sms(phone_number, otp)

        elif settings.SMS_PROVIDER == "twilio":
            return await self._send_via_twilio(phone_number, otp)

        return False

    async def _send_mock_sms(self, phone_number: str, otp: str) -> bool:
        """Mock SMS sending for development"""
        print(f"\n{'='*50}")
        print(f"📱 SMS to {phone_number}")
        print(f"Your Faction OTP is: {otp}")
        print(f"Valid for {self.otp_expire_minutes} minutes")
        print(f"{'='*50}\n")
        return True

    async def _send_via_twilio(self, phone_number: str, otp: str) -> bool:
        try:
            twilio_service = TwilioService()

            if not twilio_service.is_configured():
                print(" Twilio not configured - credentials missing")
                return False

            # Send verification code via Twilio
            result = await twilio_service.send_verification_code(phone_number)

            if not result or result.get('status') != 'pending':
                print(f" Twilio SMS failed - unexpected status: {result.get('status') if result else 'None'}")
                return False

            print(f" Twilio SMS sent to {phone_number}")
            print(f"   SID: {result.get('sid')}")
            print(f"   Status: {result.get('status')}")

            return True

        except Exception as e:
            print(f"❌ Twilio SMS failed: {e}")
            return False

