"""User schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.user import UserRole, TargetExam, SubscriptionType, ContestRank


class UserBase(BaseModel):
    """Base user schema"""

    phone_number: str
    name: str
    class_id: UUID
    target_exams: list[TargetExam]


class UserResponse(UserBase):
    """User response schema"""

    id: UUID
    role: UserRole
    subscription_type: SubscriptionType
    is_active: bool
    avatar_url: Optional[str] = None
    
    # Profile fields
    school: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
 
    email: Optional[str] = None
    
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
    class_id: Optional[UUID] = None
    target_exams: Optional[list[TargetExam]] = Field(None, description="List of target exams")
    avatar_url: Optional[str] = Field(None, max_length=500, description="URL to user's avatar image")
    school: Optional[str] = Field(None, max_length=200, description="User's school name")
    state: Optional[str] = Field(None, max_length=100, description="User's state")
    city: Optional[str] = Field(None, max_length=100, description="User's city")
    email: Optional[str] = Field(None, max_length=255, description="User's email address")


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
    title: ContestRank = ContestRank.NEWBIE

    class Config:
        from_attributes = True


class RatingFluctuationEntry(BaseModel):
    """Single rating fluctuation entry from a contest"""
    
    contest_id: UUID
    contest_name: str
    rating_before: int
    rating_after: int
    rating_delta: int
    rank: int
    score: float
    created_at: datetime

    class Config:
        from_attributes = True


class RatingFluctuationResponse(BaseModel):
    """User rating fluctuation history response"""
    
    user_id: UUID
    total_contests: int
    fluctuations: list[RatingFluctuationEntry]

    class Config:
        from_attributes = True

