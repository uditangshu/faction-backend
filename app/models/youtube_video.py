"""YouTube Video model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional


class YouTubeVideo(SQLModel, table=True):
    """YouTube video linked to chapter and subject"""
    
    __tablename__ = "youtube_videos"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign Keys
    chapter_id: UUID = Field(foreign_key="chapter.id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id", index=True)
    
    # Video Information
    youtube_video_id: str = Field(..., description="YouTube video ID (extracted from URL)")
    youtube_url: str = Field(..., description="Full YouTube video URL")
    title: str = Field(..., max_length=200, description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    thumbnail_url: Optional[str] = Field(None, description="Video thumbnail URL")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Video duration in seconds")
    
    # Metadata
    order: int = Field(default=0, description="Order/sequence within chapter")
    is_active: bool = Field(default=True, index=True, description="Whether video is active")
    views_count: int = Field(default=0, description="Number of views")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

