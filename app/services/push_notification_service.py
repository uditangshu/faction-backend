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
            logger.info(f"Sending logout push notification to token: {push_token[:20]}...")
            
            message = {
                "to": push_token,
                "sound": "default",
                "title": "Session Expired",
                "body": "You have been logged out. This may be because you logged in from another device.",
                "data": {
                    "type": "FORCE_LOGOUT",
                    "timestamp": datetime.utcnow().isoformat()
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
                
                logger.info(f"Push notification response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Push notification response: {result}")
                    
                    # Check if notification was accepted
                    if isinstance(result, dict) and result.get("data"):
                        data = result["data"]
                        if isinstance(data, list) and len(data) > 0:
                            status = data[0].get("status")
                            if status == "ok":
                                logger.info("✅ Push notification sent successfully")
                                return True
                            else:
                                error_msg = data[0].get('message', 'Unknown error')
                                logger.error(f"❌ Push notification failed: {error_msg}")
                                return False
                    return True
                else:
                    logger.error(f"❌ Failed to send push notification: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error sending push notification: {e}")
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

