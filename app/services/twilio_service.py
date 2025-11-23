"""Twilio SMS service for OTP delivery"""

import httpx
from typing import Optional
from app.core.config import settings


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
            raise Exception("Twilio credentials not configured")

        url = f"{self.base_url}/Verifications"

        data = {
            "To": phone_number,
            "Channel": channel,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,
                auth=(self.account_sid, self.auth_token),
                timeout=10.0,
            )

            if response.status_code != 201:
                error_detail = response.json() if response.text else {}
                raise Exception(
                    f"Twilio API error: {response.status_code} - {error_detail}"
                )

            return response.json()

    async def verify_code(self, phone_number: str, code: str) -> dict:
       
        if not self.is_configured():
            raise Exception("Twilio credentials not configured")

        url = f"{self.base_url}/VerificationCheck"

        data = {
            "To": phone_number,
            "Code": code,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,
                auth=(self.account_sid, self.auth_token),
                timeout=10.0,
            )

            if response.status_code != 200:
                error_detail = response.json() if response.text else {}
                raise Exception(
                    f"Twilio verification error: {response.status_code} - {error_detail}"
                )

            result = response.json()

            # Twilio returns status: 'approved' or 'pending'
            if result.get("status") != "approved":
                raise Exception("Invalid verification code")

            return result

