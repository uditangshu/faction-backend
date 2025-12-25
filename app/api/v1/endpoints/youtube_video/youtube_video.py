"""YouTube Video endpoints"""

from uuid import UUID
from fastapi import APIRouter, Query
from typing import Optional, List

from app.api.v1.dependencies import YouTubeVideoServiceDep
from app.schemas.youtube_video import (
    YouTubeVideoCreateRequest,
    YouTubeVideoResponse,
    YouTubeVideoListResponse,
    YouTubeVideoUpdateRequest,
)
from app.schemas.question import ChapterResponse, ChapterListResponse
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/youtube-videos", tags=["YouTube Videos"])


@router.post("/", response_model=YouTubeVideoResponse, status_code=201)
async def create_video(
    request: YouTubeVideoCreateRequest,
    youtube_video_service: YouTubeVideoServiceDep,
) -> YouTubeVideoResponse:
    """
    Create a new YouTube video.
    
    Only youtube_url, chapter_id, and subject_id are required.
    Title, description, thumbnail, and duration will be auto-fetched from YouTube API.
    """
    video = await youtube_video_service.create_video(
        chapter_id=request.chapter_id,
        subject_id=request.subject_id,
        youtube_url=request.youtube_url,
        order=request.order,
    )
    return YouTubeVideoResponse.model_validate(video)


@router.put("/{video_id}", response_model=YouTubeVideoResponse)
async def update_video(
    video_id: UUID,
    request: YouTubeVideoUpdateRequest,
    youtube_video_service: YouTubeVideoServiceDep,
) -> YouTubeVideoResponse:
    """Update a YouTube video"""
    video = await youtube_video_service.update_video(
        video_id=video_id,
        youtube_url=request.youtube_url,
        title=request.title,
        description=request.description,
        thumbnail_url=request.thumbnail_url,
        duration_seconds=request.duration_seconds,
        order=request.order,
        is_active=request.is_active,
        chapter_id=request.chapter_id,
        subject_id=request.subject_id,
    )
    if not video:
        raise NotFoundException(f"Video with ID {video_id} not found")
    return YouTubeVideoResponse.model_validate(video)


@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: UUID,
    youtube_video_service: YouTubeVideoServiceDep,
) -> None:
    """Delete a YouTube video"""
    deleted = await youtube_video_service.delete_video(video_id)
    if not deleted:
        raise NotFoundException(f"Video with ID {video_id} not found")


@router.get("/", response_model=YouTubeVideoListResponse)
async def get_videos(
    youtube_video_service: YouTubeVideoServiceDep,
    subject_id: Optional[UUID] = Query(None, description="Filter by subject ID"),
    chapter_id: Optional[UUID] = Query(None, description="Filter by chapter ID"),
) -> YouTubeVideoListResponse:
    """Get videos by subject_id or chapter_id"""
    if chapter_id:
        videos = await youtube_video_service.get_videos_by_chapter(chapter_id)
        return YouTubeVideoListResponse(
            videos=[YouTubeVideoResponse.model_validate(v) for v in videos],
            total=len(videos),
            chapter_id=chapter_id,
        )
    elif subject_id:
        videos = await youtube_video_service.get_videos_by_subject(subject_id)
        return YouTubeVideoListResponse(
            videos=[YouTubeVideoResponse.model_validate(v) for v in videos],
            total=len(videos),
            subject_id=subject_id,
        )
    else:
        return YouTubeVideoListResponse(videos=[], total=0)


@router.get("/latest", response_model=YouTubeVideoResponse)
async def get_latest_video(
    youtube_video_service: YouTubeVideoServiceDep,
) -> YouTubeVideoResponse:
    """Get the latest YouTube video"""
    video = await youtube_video_service.get_latest_video()
    if not video:
        raise NotFoundException("No videos available")
    return YouTubeVideoResponse.model_validate(video)


@router.get("/suggestion", response_model=YouTubeVideoResponse)
async def get_suggestion(
    youtube_video_service: YouTubeVideoServiceDep,
) -> YouTubeVideoResponse:
    """Get a random video suggestion"""
    video = await youtube_video_service.get_random_video()
    if not video:
        raise NotFoundException("No videos available")
    return YouTubeVideoResponse.model_validate(video)


@router.get("/filter", response_model=YouTubeVideoListResponse)
async def get_filtered_videos(
    youtube_video_service: YouTubeVideoServiceDep,
    chapter_ids: Optional[List[UUID]] = Query(None, description="Filter by chapter IDs (comma-separated)"),
    sort_order: str = Query("latest", description="Sort order: 'latest' or 'oldest'"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> YouTubeVideoListResponse:
    """
    Get filtered YouTube videos by chapter IDs with sorting.
    
    Filters:
    - chapter_ids: List of chapter IDs to filter by
    - sort_order: "latest" for newest first (default), "oldest" for oldest first
    """
    if sort_order not in ["latest", "oldest"]:
        raise BadRequestException("sort_order must be 'latest' or 'oldest'")
    
    videos = await youtube_video_service.get_filtered_videos(
        chapter_ids=chapter_ids,
        sort_order=sort_order,
        skip=skip,
        limit=limit
    )
    
    return YouTubeVideoListResponse(
        videos=[YouTubeVideoResponse.model_validate(v) for v in videos],
        total=len(videos),
    )


@router.get("/chapters", response_model=ChapterListResponse)
async def get_chapters_with_youtube_videos(
    youtube_video_service: YouTubeVideoServiceDep,
) -> ChapterListResponse:
    """Get all chapters that have YouTube videos where youtube_video_id is not null"""
    chapters = await youtube_video_service.get_chapters_with_youtube_videos()
    return ChapterListResponse(
        chapters=[ChapterResponse.model_validate(c) for c in chapters],
        total=len(chapters),
    )


@router.get("/{video_id}", response_model=YouTubeVideoResponse)
async def get_video_with_id(
    video_id: UUID,
    youtube_video_service: YouTubeVideoServiceDep,
) -> YouTubeVideoResponse:
    """Get a YouTube video by ID"""
    video = await youtube_video_service.get_video_by_id(video_id)
    if not video:
        raise NotFoundException(f"Video with ID {video_id} not found")
    return YouTubeVideoResponse.model_validate(video)

