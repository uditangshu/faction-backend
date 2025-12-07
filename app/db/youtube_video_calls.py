"""YouTube Video database calls"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
import random

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
    return list(result.scalars().all())


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
    return list(result.scalars().all())


async def get_random_video(
    db: AsyncSession,
) -> Optional[YouTubeVideo]:
    """Get a random active video"""
    result = await db.execute(
        select(YouTubeVideo)
        .where(YouTubeVideo.is_active == True)
    )
    videos = list(result.scalars().all())
    if not videos:
        return None
    return random.choice(videos)

