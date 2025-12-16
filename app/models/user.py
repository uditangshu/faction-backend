"""User model and related enums"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON
from typing import Optional

class UserRole(str, Enum):
    """User role enumeration"""
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class ClassLevel(str, Enum):
    """Student class level"""
    CLASS_9 = "9"
    CLASS_10 = "10"
    CLASS_11 = "11"
    CLASS_12 = "12"
    DROPPER = "Dropper"


class TargetExam(str, Enum):
    """Target entrance exam"""
    JEE_ADVANCED = "JEE_ADVANCED"
    JEE_MAINS = "JEE_MAINS"
    NEET = "NEET"
    OLYMPIAD = "OLYMPIAD"
    CBSE = "CBSE"


class SubscriptionType(str, Enum):
    """Subscription tier"""
    FREE = "free"
    PREMIUM = "premium"

class ContestRank(str, Enum):
    """Subscription tier"""
    NEWBIE = "Newbie"
    SPECIALIST = "Specialist"
    EXPERT = "Expert"
    CANDIDATE_MASTER = "Candidate Master"
    MASTER = "Master"
    GRANDMASTER = "Grandmaster"
    LEGENDARY_GRANDMASTER = "Legendary Grandmaster"
    

class User(SQLModel, table=True):
    """User model"""
    
    __tablename__ = "users"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone_number: str = Field(unique=True, index=True, max_length=15)
    password_hash: str | None = Field(default=None)  # Nullable for migration, will be required for new users
    name: str = Field(max_length=100)
    class_level: ClassLevel
    target_exams: list[str] = Field(sa_column=Column(JSON), default=[])
    avatar_url: str | None = Field(default=None, max_length=500)
    
    # Profile fields
    school: str | None = Field(default=None, max_length=200)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)

    current_rating: int = Field(default=0, nullable=False)
    max_rating: int = Field(default=0, nullable=False)
    title: ContestRank | None = Field(default=ContestRank.NEWBIE)

    role: UserRole = Field(default=UserRole.STUDENT, index=True, 
        description="User's permission level within the application")
    
    subscription_type: SubscriptionType = Field(default=SubscriptionType.FREE)
    is_active: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

