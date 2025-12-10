"""YouTube Video schemas"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class YouTubeVideoBase(BaseModel):
    """Base YouTube video schema"""
    
    youtube_video_id: str = Field(..., description="YouTube video ID")
    youtube_url: str = Field(..., description="Full YouTube video URL")
    title: str = Field(..., max_length=200, description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    thumbnail_url: Optional[str] = Field(None, description="Video thumbnail URL")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Video duration in seconds")
    instructor_name: Optional[str] = Field(None, max_length=100, description="Instructor name")
    instructor_institution: Optional[str] = Field(None, max_length=100, description="Instructor institution")
    order: int = Field(default=0, ge=0, description="Order/sequence within chapter")


class YouTubeVideoCreateRequest(YouTubeVideoBase):
    """Request to create a new YouTube video"""
    
    chapter_id: UUID = Field(..., description="Chapter ID")
    subject_id: UUID = Field(..., description="Subject ID")


class YouTubeVideoUpdateRequest(BaseModel):
    """Request to update a YouTube video"""
    
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    chapter_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None


class SubjectInfo(BaseModel):
    """Subject information"""
    id: UUID
    subject_type: str
    
    class Config:
        from_attributes = True


class ChapterInfo(BaseModel):
    """Chapter information"""
    id: UUID
    name: str
    
    class Config:
        from_attributes = True


class YouTubeVideoResponse(YouTubeVideoBase):
    """YouTube video response"""
    
    id: UUID
    chapter_id: UUID
    subject_id: UUID
    subject: Optional[SubjectInfo] = None
    chapter: Optional[ChapterInfo] = None
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

