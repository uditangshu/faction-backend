"""YouTube Video service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc
from typing import List, Optional

from app.models.youtube_video import YouTubeVideo
from app.models.Basequestion import Chapter
from app.db.youtube_video_calls import (
    create_youtube_video,
    delete_youtube_video,
    get_videos_by_subject,
    get_videos_by_chapter,
    get_random_video,
    get_youtube_video_by_id,
    update_youtube_video,
    get_latest_youtube_video,
    get_chapters_with_youtube_videos,
)
from app.utils.youtube_api import extract_video_id, get_metadata_from_url


class YouTubeVideoService:
    """Service for managing YouTube videos"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_video(
        self,
        chapter_id: UUID,
        subject_id: UUID,
        youtube_url: str,
        youtube_video_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        order: int = 0,
    ) -> YouTubeVideo:
        """
        Create a new YouTube video.
        
        If youtube_video_id, title, description, thumbnail_url, or duration_seconds
        are not provided, they will be auto-fetched from the YouTube API.
        """
        # Extract video ID from URL if not provided
        if not youtube_video_id:
            youtube_video_id = extract_video_id(youtube_url)
            if not youtube_video_id:
                raise ValueError(f"Could not extract video ID from URL: {youtube_url}")
        
        # Auto-fetch metadata from YouTube API if any fields are missing
        if not title or not description or not thumbnail_url or not duration_seconds:
            metadata = await get_metadata_from_url(youtube_url)
            if metadata:
                title = title or metadata.title
                description = description or metadata.description
                thumbnail_url = thumbnail_url or metadata.thumbnail_url
                duration_seconds = duration_seconds or metadata.duration_seconds
        
        # Ensure we have at least a title
        if not title:
            title = f"YouTube Video {youtube_video_id}"
        
        return await create_youtube_video(
            db=self.db,
            chapter_id=chapter_id,
            subject_id=subject_id,
            youtube_video_id=youtube_video_id,
            youtube_url=youtube_url,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            duration_seconds=duration_seconds,
            order=order,
        )

    async def get_video_by_id(self, video_id: UUID) -> Optional[YouTubeVideo]:
        """Get a YouTube video by ID"""
        return await get_youtube_video_by_id(self.db, video_id)

    async def update_video(
        self,
        video_id: UUID,
        title: Optional[str] = None,
        youtube_url: Optional[str]=None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        order: Optional[int] = None,
        is_active: Optional[bool] = None,
        chapter_id: Optional[UUID] = None,
        subject_id: Optional[UUID] = None,
    ) -> Optional[YouTubeVideo]:
        """Update a YouTube video"""
        return await update_youtube_video(
            db=self.db,
            video_id=video_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            youtube_url=youtube_url,
            duration_seconds=duration_seconds,
            order=order,
            is_active=is_active,
            chapter_id=chapter_id,
            subject_id=subject_id,
        )

    async def delete_video(self, video_id: UUID) -> bool:
        """Delete a YouTube video"""
        return await delete_youtube_video(self.db, video_id)

    async def get_videos_by_subject(self, subject_id: UUID) -> List[YouTubeVideo]:
        """Get all videos for a subject"""
        return await get_videos_by_subject(self.db, subject_id)

    async def get_videos_by_chapter(self, chapter_id: UUID) -> List[YouTubeVideo]:
        """Get all videos for a chapter"""
        return await get_videos_by_chapter(self.db, chapter_id)

    async def get_latest_video(
        self,
        class_id: Optional[UUID] = None,
        target_exams: Optional[List[str]] = None,
    ) -> Optional[YouTubeVideo]:
        """Get the latest YouTube video"""
        return await get_latest_youtube_video(
            self.db,
            class_id=class_id,
            target_exams=target_exams
        )

    async def get_random_video(self) -> Optional[YouTubeVideo]:
        """Get a random active video"""
        return await get_random_video(self.db)

    async def get_all_videos(self) -> List[YouTubeVideo]:
        """Get all active videos"""
        query = select(YouTubeVideo).where(YouTubeVideo.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_filtered_videos(
        self,
        chapter_ids: Optional[List[UUID]] = None,
        sort_order: str = "latest",  # "latest" or "oldest"
        skip: int =0,
        limit: int =20,
    ) -> List[YouTubeVideo]:
        """
        Get filtered videos by chapter IDs with sorting
        
        Args:
            chapter_ids: List of chapter IDs to filter by
            sort_order: "latest" for newest first, "oldest" for oldest first
            
        Returns:
            List of YouTube videos
        """
        query = select(YouTubeVideo).where(YouTubeVideo.is_active == True)
        
        # Filter by chapter IDs if provided
        if chapter_ids:
            query = query.where(YouTubeVideo.chapter_id.in_(chapter_ids))
        
        # Apply sorting
        if sort_order == "latest":
            query = query.order_by(desc(YouTubeVideo.created_at))
        elif sort_order == "oldest":
            query = query.order_by(asc(YouTubeVideo.created_at))
        else:
            # Default to latest
            query = query.order_by(desc(YouTubeVideo.created_at))
        
        query= query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_chapters_with_youtube_videos(self) -> List[Chapter]:
        """Get all chapters that have YouTube videos where youtube_video_id is not null"""
        return await get_chapters_with_youtube_videos(self.db)

