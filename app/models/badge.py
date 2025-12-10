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


class Badge(SQLModel, table=True):
    """Badge model for practice arena and streak achievements"""
    
    __tablename__ = "badges"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)
    
    # Category: either for streak or practice arena
    category: BadgeCategory = Field(index=True, description="Whether badge is for streak or practice arena")
    
    # Visual representation
    icon_url: Optional[str] = Field(default=None, max_length=500)
    icon_svg: Optional[str] = Field(default=None)
    
    # Requirements to earn the badge
    requirement_value: Optional[int] = Field(default=None, description="Required value to earn badge (e.g., 100 questions, 7 day streak)")
    requirement_description: str = Field(max_length=500)

    # Metadata
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    

