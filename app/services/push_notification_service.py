"""Push notification service using Expo Push Notifications"""

import httpx
from typing import List, Dict, Any
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service for sending push notifications via Expo"""
    
    EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
    
    async def send_logout_notification(self, push_token: str) -> bool:
        """
        Send a logout notification to a device
        This triggers immediate logout on the receiving device
        """
        try:
            # Validate push token format
            if not push_token:
                print(f"❌ Push token is empty or None")
                return False
            
            if not push_token.startswith("ExponentPushToken["):
                print(f"⚠️ Push token format may be invalid: {push_token[:50]}...")
                print(f"   Expected format: ExponentPushToken[xxxxx]")
            
            print(f"📤 Sending logout push notification to: {push_token}")
            
            message = {
                "to": push_token,
                "sound": "default",
                "title": "Session Expired",
                "body": "You have been logged out because you logged in from another device.",
                "data": {
                    "type": "FORCE_LOGOUT",
                    "timestamp": datetime.utcnow().isoformat()
                },
                "priority": "high",
                "channelId": "default",
            }
            
            print(f"📤 Push message payload: {message}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.EXPO_PUSH_URL,
                    json=message,
                    headers={
                        "Accept": "application/json",
                        "Accept-encoding": "gzip, deflate",
                        "Content-Type": "application/json",
                    },
                    timeout=10.0
                )
                
                print(f"📥 Expo API response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"📥 Expo API response body: {result}")
                    
                    # Check if notification was accepted
                    if isinstance(result, dict) and result.get("data"):
                        data = result["data"]
                        if isinstance(data, list) and len(data) > 0:
                            status = data[0].get("status")
                            details = data[0].get("details", {})
                            
                            if status == "ok":
                                print(f"✅ Push notification ACCEPTED by Expo")
                                return True
                            elif status == "error":
                                error_msg = data[0].get('message', 'Unknown error')
                                error_details = data[0].get('details', {})
                                print(f"❌ Push notification REJECTED by Expo: {error_msg}")
                                print(f"   Error details: {error_details}")
                                
                                # Common errors:
                                if "DeviceNotRegistered" in str(error_details):
                                    print(f"   ⚠️ Device token is no longer valid (app uninstalled or token expired)")
                                elif "InvalidCredentials" in str(error_details):
                                    print(f"   ⚠️ Push credentials are invalid")
                                
                                return False
                    return True
                else:
                    print(f"❌ Expo API HTTP error: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
        except httpx.TimeoutException as e:
            print(f"❌ Push notification TIMEOUT: {e}")
            return False
        except Exception as e:
            print(f"❌ Push notification EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            print(traceback.format_exc())
            return False
    
    async def send_batch_notifications(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Send multiple push notifications in a batch
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.EXPO_PUSH_URL,
                    json=messages,
                    headers={
                        "Accept": "application/json",
                        "Accept-encoding": "gzip, deflate",
                        "Content-Type": "application/json",
                    },
                    timeout=10.0
                )
                
                return response.status_code == 200
                    
        except Exception as e:
            print(f"Error sending batch push notifications: {e}")
            return False

