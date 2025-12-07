"""User schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.user import UserRole, ClassLevel, TargetExam, SubscriptionType, ContestRank


class UserBase(BaseModel):
    """Base user schema"""

    phone_number: str
    name: str
    class_level: ClassLevel
    target_exams: list[TargetExam]


class UserResponse(UserBase):
    """User response schema"""

    id: UUID
    role: UserRole
    subscription_type: SubscriptionType
    is_active: bool
    avatar_svg: Optional[str] = None
    
    # Contest rating fields
    current_rating: int = 0
    max_rating: int = 0
    title: Optional[ContestRank] = ContestRank.NEWBIE
    
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    """Extended user profile response"""

    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Request to update user profile"""
    
    name: Optional[str] = Field(None, max_length=100)
    class_level: Optional[ClassLevel] = None
    avatar_svg: Optional[str] = Field(None, description="SVG string for user avatar")


class UserRatingUpdateRequest(BaseModel):
    """Request to update user rating (admin/system only)"""
    
    current_rating: int = Field(..., ge=0, description="User's current contest rating")
    max_rating: Optional[int] = Field(None, ge=0, description="User's maximum rating achieved")
    title: Optional[ContestRank] = Field(None, description="User's contest rank title")


class UserRatingResponse(BaseModel):
    """User rating info response"""
    
    user_id: UUID
    current_rating: int
    max_rating: int
    title: ContestRank

    class Config:
        from_attributes = True

