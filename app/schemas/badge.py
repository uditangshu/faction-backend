"""Badge schemas"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from app.models.badge import BadgeCategory


class BadgeCreateRequest(BaseModel):
    """Request to create a new badge"""
    name: str
    description: str
    category: BadgeCategory
    icon_url: Optional[str] = None
    icon_svg: Optional[str] = None
    requirement_value: Optional[int] = None
    requirement_description: str
    is_active: bool = True


class BadgeResponse(BaseModel):
    """Badge response"""
    id: UUID
    name: str
    description: str
    category: BadgeCategory
    icon_url: Optional[str] = None
    icon_svg: Optional[str] = None
    requirement_value: Optional[int] = None
    requirement_description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BadgeListResponse(BaseModel):
    """List of badges"""
    badges: List[BadgeResponse]
    total: int

