"""Bookmarked Video service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from typing import List, Tuple

from app.models.youtube_video import BookmarkedVideo, YouTubeVideo


class BookmarkedVideoService:
    """Service for managing bookmarked videos"""

    def __init__(self, db: AsyncSession):
        self.db = db

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
        return bookmark

    async def get_bookmarks_by_user_id(self, user_id: UUID) -> List[Tuple[BookmarkedVideo, YouTubeVideo]]:
        """Get all bookmarks for a user with video details"""
        result = await self.db.execute(
            select(BookmarkedVideo, YouTubeVideo)
            .join(YouTubeVideo, BookmarkedVideo.youtube_video_id == YouTubeVideo.id)
            .where(BookmarkedVideo.user_id == user_id)
            .order_by(BookmarkedVideo.created_at.desc())
        )
        return list(result.all())

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
        return result.rowcount > 0

