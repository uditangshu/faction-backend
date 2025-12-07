"""YouTube Video endpoints"""

from uuid import UUID
from fastapi import APIRouter, Query
from typing import Optional

from app.api.v1.dependencies import DBSession
from app.db.youtube_video_calls import (
    create_youtube_video,
    delete_youtube_video,
    get_videos_by_subject,
    get_videos_by_chapter,
    get_random_video,
)
from app.schemas.youtube_video import (
    YouTubeVideoCreateRequest,
    YouTubeVideoResponse,
    YouTubeVideoListResponse,
)
from app.exceptions.http_exceptions import NotFoundException

router = APIRouter(prefix="/youtube-videos", tags=["YouTube Videos"])


@router.post("/", response_model=YouTubeVideoResponse, status_code=201)
async def create_video(
    request: YouTubeVideoCreateRequest,
    db: DBSession,
) -> YouTubeVideoResponse:
    """Create a new YouTube video"""
    video = await create_youtube_video(
        db=db,
        chapter_id=request.chapter_id,
        subject_id=request.subject_id,
        youtube_video_id=request.youtube_video_id,
        youtube_url=request.youtube_url,
        title=request.title,
        description=request.description,
        thumbnail_url=request.thumbnail_url,
        duration_seconds=request.duration_seconds,
        order=request.order,
    )
    return YouTubeVideoResponse.model_validate(video)


@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: UUID,
    db: DBSession,
) -> None:
    """Delete a YouTube video"""
    deleted = await delete_youtube_video(db, video_id)
    if not deleted:
        raise NotFoundException(f"Video with ID {video_id} not found")


@router.get("/", response_model=YouTubeVideoListResponse)
async def get_videos(
    db: DBSession,
    subject_id: Optional[UUID] = Query(None, description="Filter by subject ID"),
    chapter_id: Optional[UUID] = Query(None, description="Filter by chapter ID"),
) -> YouTubeVideoListResponse:
    """Get videos by subject_id or chapter_id"""
    if chapter_id:
        videos = await get_videos_by_chapter(db, chapter_id)
        return YouTubeVideoListResponse(
            videos=[YouTubeVideoResponse.model_validate(v) for v in videos],
            total=len(videos),
            chapter_id=chapter_id,
        )
    elif subject_id:
        videos = await get_videos_by_subject(db, subject_id)
        return YouTubeVideoListResponse(
            videos=[YouTubeVideoResponse.model_validate(v) for v in videos],
            total=len(videos),
            subject_id=subject_id,
        )
    else:
        return YouTubeVideoListResponse(videos=[], total=0)


@router.get("/suggestion", response_model=YouTubeVideoResponse)
async def get_suggestion(
    db: DBSession,
) -> YouTubeVideoResponse:
    """Get a random video suggestion"""
    video = await get_random_video(db)
    if not video:
        raise NotFoundException("No videos available")
    return YouTubeVideoResponse.model_validate(video)

