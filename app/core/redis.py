"""Redis client configuration and utilities"""

import json
from typing import Any
import redis.asyncio as aioredis

from app.core.config import settings

# Global Redis client
redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """
    Get Redis client instance.
    
    Returns:
        Redis client
    """
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
        """
        Set a value in Redis.
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if not string)
            expire: Expiration time in seconds
            
        Returns:
            bool: Success status
        """
        if not isinstance(value, str):
            value = json.dumps(value)
        
        if expire:
            return await self.client.setex(key, expire, value)
        return await self.client.set(key, value)
    
    async def get_value(self, key: str) -> Any | None:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Stored value or None if not found
        """
        value = await self.client.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    async def delete_key(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            bool: Success status
        """
        return await self.client.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Redis key
            
        Returns:
            bool: True if key exists
        """
        return await self.client.exists(key) > 0
    
    async def increment(self, key: str) -> int:
        """
        Increment a counter in Redis.
        
        Args:
            key: Redis key
            
        Returns:
            int: New counter value
        """
        return await self.client.incr(key)

