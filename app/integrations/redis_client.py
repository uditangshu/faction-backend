"""Redis client integration"""

import json
from typing import Any
import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


async def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()


class RedisService:
    """Redis operations wrapper"""

    def __init__(self, client: aioredis.Redis):
        self.client = client

    async def set_value(self, key: str, value: Any, expire: int | None = None) -> bool:
        """Set a value in Redis with optional expiration"""
        if not isinstance(value, str):
            value = json.dumps(value)

        if expire:
            return await self.client.setex(key, expire, value)
        return await self.client.set(key, value)

    async def get_value(self, key: str) -> Any | None:
        """Get a value from Redis"""
        value = await self.client.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def delete_key(self, key: str) -> bool:
        """Delete a key from Redis"""
        return await self.client.delete(key) > 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        return await self.client.exists(key) > 0

    async def increment(self, key: str) -> int:
        """Increment a counter in Redis"""
        return await self.client.incr(key)

    async def set_active_session(self, user_id: str, session_id: str, expire: int = 86400 * 7) -> bool:
        """Set active session for user (7 days default)"""
        # Store session_id as plain string (not JSON encoded) for consistency
        key = f"active_session:{user_id}"
        if expire:
            return await self.client.setex(key, expire, str(session_id))
        return await self.client.set(key, str(session_id))

    async def get_active_session(self, user_id: str) -> str | None:
        """Get active session ID for user"""
        # Session IDs are stored as plain strings, so get directly without JSON parsing
        key = f"active_session:{user_id}"
        value = await self.client.get(key)
        if value is None:
            return None
        try:
            parsed = json.loads(value)
            return str(parsed) if parsed is not None else None
        except json.JSONDecodeError:
            return value

    async def invalidate_user_session(self, user_id: str) -> bool:
        """Invalidate all sessions for a user"""
        return await self.delete_key(f"active_session:{user_id}")

    async def is_session_valid(self, user_id: str, session_id: str) -> bool:
        """Check if session is the active one for this user"""
        active_session = await self.get_active_session(user_id)
        if active_session is None:
            return False
        return str(active_session) == str(session_id)
    
    async def set_force_logout(self, session_id: str, expire: int = 300) -> bool:
        """Mark a session for forced logout (5 min TTL)"""
        return await self.set_value(f"force_logout:{session_id}", "true", expire)
    
    async def should_force_logout(self, session_id: str) -> bool:
        """Check if session should be force logged out"""
        return await self.exists(f"force_logout:{session_id}")

