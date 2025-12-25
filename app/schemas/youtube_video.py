"""YouTube Video schemas"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class YouTubeVideoCreateRequest(BaseModel):
    """Request to create a new YouTube video - only URL and IDs required, metadata auto-fetched"""
    
    youtube_url: str = Field(..., description="YouTube video URL (any format)")
    chapter_id: UUID = Field(..., description="Chapter ID")
    subject_id: UUID = Field(..., description="Subject ID")
    order: int = Field(default=0, ge=0, description="Order/sequence within chapter")


class YouTubeVideoBase(BaseModel):
    """Base YouTube video schema"""
    
    youtube_video_id: Optional[str] = Field(None, description="YouTube video ID (auto-extracted from URL if not provided)")
    youtube_url: str = Field(..., description="Full YouTube video URL")
    title: Optional[str] = Field(None, max_length=200, description="Video title (auto-fetched from YouTube if not provided)")
    description: Optional[str] = Field(None, description="Video description (auto-fetched from YouTube if not provided)")
    thumbnail_url: Optional[str] = Field(None, description="Video thumbnail URL (auto-fetched from YouTube if not provided)")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Video duration in seconds (auto-fetched from YouTube if not provided)")
    order: int = Field(default=0, ge=0, description="Order/sequence within chapter")


class YouTubeVideoUpdateRequest(BaseModel):
    """Request to update a YouTube video"""
    
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    youtube_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    chapter_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None


class YouTubeVideoResponse(YouTubeVideoBase):
    """YouTube video response"""
    
    id: UUID
    chapter_id: UUID
    subject_id: UUID
    is_active: bool
    views_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class YouTubeVideoListResponse(BaseModel):
    """List of YouTube videos response"""
    
    videos: list[YouTubeVideoResponse]
    total: int
    chapter_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None


class YouTubeVideoDetailResponse(YouTubeVideoResponse):
    """Detailed YouTube video response with additional info"""
    
    pass

