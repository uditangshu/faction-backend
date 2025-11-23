"""User schemas"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.user import UserRole, ClassLevel, TargetExam, SubscriptionType


class UserBase(BaseModel):
    """Base user schema"""

    phone_number: str
    name: str
    class_level: ClassLevel
    target_exam: TargetExam


class UserResponse(UserBase):
    """User response schema"""

    id: UUID
    role: UserRole
    subscription_type: SubscriptionType
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    """Extended user profile response"""

    updated_at: datetime

    class Config:
        from_attributes = True

