"""Doubt forum schemas"""

from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# ==================== Doubt Post Schemas ====================

class DoubtPostCreateRequest(BaseModel):
    """Request to create a new doubt post"""
    title: str = Field(..., max_length=200)
    content: str
    class_id: UUID


class DoubtPostResponse(BaseModel):
    """Doubt post response"""
    id: UUID
    user_id: UUID
    class_id: UUID
    title: str
    content: str
    image_url: Optional[str]
    is_solved: bool
    likes_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DoubtPostListResponse(BaseModel):
    """List of doubt posts response with pagination"""
    posts: List[DoubtPostResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class DoubtPostDetailResponse(DoubtPostResponse):
    """Detailed doubt post response with comments"""
    comments: List["DoubtCommentResponse"] = []


# ==================== Doubt Comment Schemas ====================

class DoubtCommentCreateRequest(BaseModel):
    """Request to create a new comment"""
    post_id: UUID
    content: str


class DoubtCommentResponse(BaseModel):
    """Doubt comment response"""
    id: UUID
    user_id: UUID
    post_id: UUID
    content: str
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


DoubtPostDetailResponse.model_rebuild()

# ==================== Doubt Like Schemas ====================

class DoubtLikeResponse(BaseModel):
    """Doubt like response"""
    likes_count: int
    is_liked: bool


# ==================== Doubt Bookmark Schemas ====================

class DoubtBookmarkResponse(BaseModel):
    """Doubt bookmark response"""
    is_bookmarked: bool

