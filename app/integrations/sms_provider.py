"""SMS provider abstraction"""

from app.core.config import settings
from app.integrations.twilio_client import TwilioClient


class SMSProvider:
    """Unified SMS provider interface"""

    def __init__(self):
        self.provider = settings.SMS_PROVIDER
        self.twilio_client = TwilioClient() if self.provider == "twilio" else None

    async def send_otp(self, phone_number: str, otp: str) -> bool:
        """Send OTP via configured provider"""
        if self.provider == "mock":
            return self._send_mock_sms(phone_number, otp)
        elif self.provider == "twilio":
            return await self._send_via_twilio(phone_number)
        return False

    async def verify_otp_with_provider(self, phone_number: str, otp: str) -> bool:
        """Verify OTP with external provider (Twilio)"""
        if self.provider == "twilio" and self.twilio_client:
            try:
                await self.twilio_client.verify_code(phone_number, otp)
                return True
            except Exception as e:
                print(f"Twilio verification failed: {e}")
                return False
        return False

    async def _send_via_twilio(self, phone_number: str) -> bool:
        """Send OTP via Twilio"""
        try:
            if not self.twilio_client or not self.twilio_client.is_configured():
                print("Twilio not configured, falling back to mock")
                return False

            result = await self.twilio_client.send_verification_code(phone_number)
            print(f"Twilio SMS sent to {phone_number}")
            print(f"   SID: {result.get('sid')}")
            print(f"   Status: {result.get('status')}")
            return True
        except Exception as e:
            print(f"Twilio SMS failed: {e}")
            return False

    def _send_mock_sms(self, phone_number: str, otp: str) -> bool:
        """Mock SMS for development"""
        print(f"\n{'='*50}")
        print(f"SMS to {phone_number}")
        print(f"Your Faction OTP is: {otp}")
        print(f"Valid for {settings.OTP_EXPIRE_MINUTES} minutes")
        print(f"{'='*50}\n")
        return True

