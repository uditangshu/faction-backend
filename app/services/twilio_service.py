"""Twilio SMS service for OTP delivery"""

import httpx
from typing import Optional
from app.core.config import settings
from app.utils.exceptions import InvalidOTPException, SMSDeliveryException

class TwilioService:
    """Service for sending SMS via Twilio Verify API"""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID
        self.base_url = f"https://verify.twilio.com/v2/Services/{self.verify_service_sid}"

    def is_configured(self) -> bool:
        """Check if Twilio is properly configured"""
        return bool(
            self.account_sid and self.auth_token and self.verify_service_sid
        )

    async def send_verification_code(
        self, phone_number: str, channel: str = "sms"
    ) -> dict:
        if not self.is_configured():
            raise SMSDeliveryException("SMS service not configured")

        url = f"{self.base_url}/Verifications"

        data = {
            "To": phone_number,
            "Channel": channel,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                    timeout=10.0,
                )

                if response.status_code != 201:
                    error_detail = response.json() if response.text else {}
                    print(f"❌ Twilio send error: {response.status_code} - {error_detail}")
                    raise SMSDeliveryException("Failed to send OTP. Please try again.")

                return response.json()
        except httpx.TimeoutException:
            raise SMSDeliveryException("SMS service timeout. Please try again.")
        except SMSDeliveryException:
            raise
        except Exception as e:
            print(f"❌ Twilio send exception: {e}")
            raise SMSDeliveryException("Failed to send OTP. Please try again.")

    async def verify_code(self, phone_number: str, code: str) -> dict:
        """Verify OTP code with Twilio Verify service"""
        if not self.is_configured():
            raise SMSDeliveryException("SMS service not configured")

        url = f"{self.base_url}/VerificationCheck"

        data = {
            "To": phone_number,
            "Code": code,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                    timeout=10.0,
                )

                result = response.json() if response.text else {}
                
                # Log for debugging
                print(f"📱 Twilio verify response: status={response.status_code}, result={result}")

                if response.status_code != 200:
                    # Handle specific Twilio errors
                    error_code = result.get("code")
                    if error_code == 60202:  # Max check attempts reached
                        raise InvalidOTPException()
                    elif error_code == 20404:  # Verification not found (expired)
                        raise InvalidOTPException()
                    else:
                        print(f"❌ Twilio verify error: {response.status_code} - {result}")
                        raise InvalidOTPException()

                # Twilio returns status: 'approved' or 'pending'
                if result.get("status") != "approved":
                    print(f"❌ Twilio OTP not approved: status={result.get('status')}")
                    raise InvalidOTPException()

                return result
                
        except httpx.TimeoutException:
            raise SMSDeliveryException("Verification service timeout. Please try again.")
        except (InvalidOTPException, SMSDeliveryException):
            raise
        except Exception as e:
            print(f"❌ Twilio verify exception: {e}")
            raise InvalidOTPException()

