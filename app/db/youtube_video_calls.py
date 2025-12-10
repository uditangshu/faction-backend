"""YouTube Video database calls"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload, joinedload
import random

from app.models.youtube_video import YouTubeVideo
from app.models.Basequestion import Subject, Chapter


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
) -> List[Dict[str, Any]]:
    """Get all videos for a subject with subject and chapter names"""
    result = await db.execute(
        select(YouTubeVideo, Subject.subject_type, Chapter.name)
        .join(Subject, YouTubeVideo.subject_id == Subject.id)
        .join(Chapter, YouTubeVideo.chapter_id == Chapter.id)
        .where(
            YouTubeVideo.subject_id == subject_id,
            YouTubeVideo.is_active == True,
        )
        .order_by(YouTubeVideo.order, YouTubeVideo.created_at)
    )
    videos_with_names = []
    for video, subject_type, chapter_name in result.all():
        video_dict = {
            **video.__dict__,
            'subject_name': subject_type.value if subject_type else None,
            'chapter_name': chapter_name
        }
        videos_with_names.append(video_dict)
    return videos_with_names


async def get_videos_by_chapter(
    db: AsyncSession,
    chapter_id: UUID,
) -> List[Dict[str, Any]]:
    """Get all videos for a chapter with subject and chapter names"""
    result = await db.execute(
        select(YouTubeVideo, Subject.subject_type, Chapter.name)
        .join(Subject, YouTubeVideo.subject_id == Subject.id)
        .join(Chapter, YouTubeVideo.chapter_id == Chapter.id)
        .where(
            YouTubeVideo.chapter_id == chapter_id,
            YouTubeVideo.is_active == True,
        )
        .order_by(YouTubeVideo.order, YouTubeVideo.created_at)
    )
    videos_with_names = []
    for video, subject_type, chapter_name in result.all():
        video_dict = {
            **video.__dict__,
            'subject_name': subject_type.value if subject_type else None,
            'chapter_name': chapter_name
        }
        videos_with_names.append(video_dict)
    return videos_with_names


async def get_random_video(
    db: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """Get a random active video with subject and chapter names"""
    result = await db.execute(
        select(YouTubeVideo, Subject.subject_type, Chapter.name)
        .join(Subject, YouTubeVideo.subject_id == Subject.id)
        .join(Chapter, YouTubeVideo.chapter_id == Chapter.id)
        .where(YouTubeVideo.is_active == True)
    )
    videos_data = result.all()
    if not videos_data:
        return None
    
    video, subject_type, chapter_name = random.choice(videos_data)
    video_dict = {
        **video.__dict__,
        'subject_name': subject_type.value if subject_type else None,
        'chapter_name': chapter_name
    }
    return video_dict

