"""Push notification service using Expo Push Notifications"""

import httpx
from typing import List, Dict, Any
from app.core.config import settings


class PushNotificationService:
    """Service for sending push notifications via Expo"""
    
    EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
    
    async def send_logout_notification(self, push_token: str) -> bool:
        """
        Send a logout notification to a device
        This triggers immediate logout on the receiving device
        """
        try:
            message = {
                "to": push_token,
                "sound": "default",
                "title": "Session Expired",
                "body": "You have been logged out. This may be because you logged in from another device.",
                "data": {
                    "type": "FORCE_LOGOUT",
                    "timestamp": str(httpx.URL(""))  # Get current timestamp
                },
                "priority": "high",
                "channelId": "default",
            }
            
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
                
                if response.status_code == 200:
                    result = response.json()
                    # Check if notification was accepted
                    if isinstance(result, dict) and result.get("data"):
                        data = result["data"]
                        if isinstance(data, list) and len(data) > 0:
                            status = data[0].get("status")
                            if status == "ok":
                                return True
                            else:
                                print(f"Push notification failed: {data[0].get('message')}")
                                return False
                    return True
                else:
                    print(f"Failed to send push notification: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"Error sending push notification: {e}")
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

