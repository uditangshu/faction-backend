"""Badge and achievement models"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from user import User


class BadgeCategory(str, Enum):
    """Badge category - either for streak or practice arena"""
    STREAK = "streak"
    PRACTICE_ARENA = "practice_arena"


class BadgeType(str, Enum):
    """Types of badges available"""
    QUESTIONS_SOLVED = "questions_solved"
    ACCURACY = "accuracy"
    DIFFICULTY_MASTER = "difficulty_master"
    STREAK = "streak"
    PERFECT_SCORE = "perfect_score"
    SPEED_DEMON = "speed_demon"
    CONSISTENCY = "consistency"
    SUBJECT_MASTER = "subject_master"
    WEEKLY_CHALLENGE = "weekly_challenge"
    MONTHLY_CHALLENGE = "monthly_challenge"


class BadgeRarity(str, Enum):
    """Badge rarity levels"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class Badge(SQLModel, table=True):
    """Badge model for practice arena and streak achievements"""
    
    __tablename__ = "badges"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)
    
    # Category: either for streak or practice arena
    category: BadgeCategory = Field(index=True, description="Whether badge is for streak or practice arena")
    
    # Badge type and rarity
    badge_type: BadgeType = Field(index=True)
    rarity: BadgeRarity = Field(default=BadgeRarity.COMMON)
    
    # Visual representation
    icon_url: Optional[str] = Field(default=None, max_length=500)
    icon_svg: Optional[str] = Field(default=None)
    
    # Requirements to earn the badge
    requirement_value: Optional[int] = Field(default=None, description="Required value to earn badge (e.g., 100 questions, 7 day streak)")
    requirement_description: str = Field(max_length=500)
    
    # Reward points
    points_reward: int = Field(default=0, description="Points awarded when badge is earned")
    
    # Metadata
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user_badges: list["UserBadge"] = Relationship(back_populates="badge")


class UserBadge(SQLModel, table=True):
    """Linking table for users and badges they've earned"""
    
    __tablename__ = "user_badges"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    badge_id: UUID = Field(foreign_key="badges.id", index=True)
    
    # Metadata
    earned_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    progress: Optional[float] = Field(default=None, description="Progress percentage if badge is not yet fully earned (0-100)")
    is_earned: bool = Field(default=False, index=True)
    
    # Relationships
    badge: "Badge" = Relationship(back_populates="user_badges")

