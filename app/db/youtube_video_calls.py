"""YouTube Video database calls"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, desc
import random
from datetime import datetime

from app.models.youtube_video import YouTubeVideo


async def create_youtube_video(
    db: AsyncSession,
    chapter_id: UUID,
    subject_id: UUID,
    youtube_video_id: str,
    youtube_url: str,
    title: str,
    description: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    order: int = 0,
) -> YouTubeVideo:
    """Create a new YouTube video"""
    video = YouTubeVideo(
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
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


async def delete_youtube_video(
    db: AsyncSession,
    video_id: UUID,
) -> bool:
    """Delete a YouTube video"""
    result = await db.execute(
        delete(YouTubeVideo).where(YouTubeVideo.id == video_id)
    )
    await db.commit()
    return result.rowcount > 0


async def get_videos_by_subject(
    db: AsyncSession,
    subject_id: UUID,
) -> List[YouTubeVideo]:
    """Get all videos for a subject"""
    result = await db.execute(
        select(YouTubeVideo)
        .where(
            YouTubeVideo.subject_id == subject_id,
            YouTubeVideo.is_active == True,
        )
        .order_by(YouTubeVideo.order, YouTubeVideo.created_at)
    )
    return result.scalars().all()


async def get_videos_by_chapter(
    db: AsyncSession,
    chapter_id: UUID,
) -> List[YouTubeVideo]:
    """Get all videos for a chapter"""
    result = await db.execute(
        select(YouTubeVideo)
        .where(
            YouTubeVideo.chapter_id == chapter_id,
            YouTubeVideo.is_active == True,
        )
        .order_by(YouTubeVideo.order, YouTubeVideo.created_at)
    )
    return result.scalars().all()


async def get_random_video(
    db: AsyncSession,
) -> Optional[YouTubeVideo]:
    """Get a random active video"""
    result = await db.execute(
        select(YouTubeVideo)
        .where(YouTubeVideo.is_active == True)
    )
    videos = result.scalars().all()
    if not videos:
        return None
    
    return random.choice(videos)


async def get_youtube_video_by_id(
    db: AsyncSession,
    video_id: UUID,
) -> Optional[YouTubeVideo]:
    """Get a YouTube video by ID"""
    result = await db.execute(
        select(YouTubeVideo).where(YouTubeVideo.id == video_id)
    )
    return result.scalar_one_or_none()


async def update_youtube_video(
    db: AsyncSession,
    video_id: UUID,
    title: Optional[str] = None,
    description: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    order: Optional[int] = None,
    is_active: Optional[bool] = None,
    chapter_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
) -> Optional[YouTubeVideo]:
    """Update a YouTube video"""
    video = await get_youtube_video_by_id(db, video_id)
    if not video:
        return None
    
    if title is not None:
        video.title = title
    if description is not None:
        video.description = description
    if thumbnail_url is not None:
        video.thumbnail_url = thumbnail_url
    if duration_seconds is not None:
        video.duration_seconds = duration_seconds
    if order is not None:
        video.order = order
    if is_active is not None:
        video.is_active = is_active
    if chapter_id is not None:
        video.chapter_id = chapter_id
    if subject_id is not None:
        video.subject_id = subject_id
    
    video.updated_at = datetime.now()
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


async def get_latest_youtube_video(
    db: AsyncSession,
) -> Optional[YouTubeVideo]:
    """Get the latest YouTube video by created_at"""
    result = await db.execute(
        select(YouTubeVideo)
        .where(YouTubeVideo.is_active == True)
        .order_by(desc(YouTubeVideo.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()

