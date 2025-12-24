"""Bookmarked Video schemas"""

from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional

from app.schemas.youtube_video import YouTubeVideoResponse


class BookmarkedVideoCreateRequest(BaseModel):
    youtube_video_id: UUID


class BookmarkedVideoResponse(BaseModel):
    id: UUID
    user_id: UUID
    youtube_video_id: UUID
    created_at: str
    youtube_video: Optional[YouTubeVideoResponse] = None

    class Config:
        from_attributes = True


class BookmarkedVideoListResponse(BaseModel):
    bookmarks: List[BookmarkedVideoResponse]
    total: int

