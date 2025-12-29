"""Treasure schemas"""

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TreasureBase(BaseModel):
    """Base treasure schema"""
    
    title: Optional[str] = Field(None, max_length=200, description="Optional title for the treasure")
    description: Optional[str] = Field(None, description="Optional description for the treasure")
    order: int = Field(default=0, ge=0, description="Order/sequence within chapter")


class TreasureCreateRequest(BaseModel):
    """Request to create a new treasure"""
    
    chapter_id: UUID = Field(..., description="Chapter ID")
    subject_id: UUID = Field(..., description="Subject ID")
    title: Optional[str] = Field(None, max_length=200, description="Optional title for the treasure")
    description: Optional[str] = Field(None, description="Optional description for the treasure")
    order: int = Field(default=0, ge=0, description="Order/sequence within chapter")


class TreasureResponse(BaseModel):
    """Treasure response"""
    
    id: UUID
    chapter_id: UUID
    subject_id: UUID
    image_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TreasureListResponse(BaseModel):
    """List of treasures response"""
    
    treasures: List[TreasureResponse]
    total: int
    subject_id: Optional[UUID] = None
    chapter_id: Optional[UUID] = None


class TreasureDetailResponse(TreasureResponse):
    """Detailed treasure response with additional info"""
    
    pass

