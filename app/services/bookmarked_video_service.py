"""Bookmarked Video service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from typing import List, Tuple, Optional
import json

from app.models.youtube_video import BookmarkedVideo, YouTubeVideo
from app.integrations.redis_client import RedisService


class BookmarkedVideoService:
    """Service for managing bookmarked videos with Redis caching"""

    CACHE_TTL = 300  # 5 minutes cache
    CACHE_PREFIX = "bookmarks"

    def __init__(self, db: AsyncSession, redis: Optional[RedisService] = None):
        self.db = db
        self.redis = redis

    def _cache_key(self, user_id: UUID) -> str:
        return f"{self.CACHE_PREFIX}:{user_id}"

    async def _invalidate_cache(self, user_id: UUID) -> None:
        """Invalidate user's bookmark cache"""
        if self.redis:
            await self.redis.delete_key(self._cache_key(user_id))

    async def create_bookmark(self, user_id: UUID, youtube_video_id: UUID) -> BookmarkedVideo:
        """Create a new bookmark"""
        # Check if bookmark already exists
        existing = await self.db.execute(
            select(BookmarkedVideo).where(
                and_(
                    BookmarkedVideo.user_id == user_id,
                    BookmarkedVideo.youtube_video_id == youtube_video_id
                )
            )
        )
        if existing.scalar_one_or_none():
            from app.exceptions.http_exceptions import ConflictException
            raise ConflictException("Video is already bookmarked")
        
        bookmark = BookmarkedVideo(user_id=user_id, youtube_video_id=youtube_video_id)
        self.db.add(bookmark)
        await self.db.commit()
        await self.db.refresh(bookmark)
        
        # Invalidate cache after creating bookmark
        await self._invalidate_cache(user_id)
        
        return bookmark

    async def get_bookmarks_by_user_id(self, user_id: UUID) -> List[Tuple[BookmarkedVideo, YouTubeVideo]]:
        """Get all bookmarks for a user with video details (cached)"""
        # Note: We don't cache the full result since it includes ORM objects
        # but we could cache just the IDs and fetch fresh data
        result = await self.db.execute(
            select(BookmarkedVideo, YouTubeVideo)
            .join(YouTubeVideo, BookmarkedVideo.youtube_video_id == YouTubeVideo.id)
            .where(BookmarkedVideo.user_id == user_id)
            .order_by(BookmarkedVideo.created_at.desc())
        )
        return list(result.all())

    async def get_bookmark_ids(self, user_id: UUID) -> List[str]:
        """Get just bookmark video IDs for a user (cached for quick lookup)"""
        cache_key = self._cache_key(user_id)
        
        # Try cache first
        if self.redis:
            cached = await self.redis.get_key(cache_key)
            if cached:
                return json.loads(cached)
        
        # Query database
        result = await self.db.execute(
            select(BookmarkedVideo.youtube_video_id)
            .where(BookmarkedVideo.user_id == user_id)
        )
        bookmark_ids = [str(row[0]) for row in result.all()]
        
        # Cache result
        if self.redis:
            await self.redis.set_key(cache_key, json.dumps(bookmark_ids), self.CACHE_TTL)
        
        return bookmark_ids

    async def delete_bookmark(self, user_id: UUID, youtube_video_id: UUID) -> bool:
        """Delete a bookmark"""
        stmt = delete(BookmarkedVideo).where(
            and_(
                BookmarkedVideo.user_id == user_id,
                BookmarkedVideo.youtube_video_id == youtube_video_id
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        # Invalidate cache after deleting bookmark
        await self._invalidate_cache(user_id)
        
        return result.rowcount > 0

