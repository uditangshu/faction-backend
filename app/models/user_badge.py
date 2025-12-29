"""User Badge model"""

from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel

class UserBadge(SQLModel, table=True):
    """Link table between User and Badge to track earned badges"""
    
    __tablename__ = "user_badges"
    
    user_id: UUID = Field(foreign_key="users.id", primary_key=True)
    badge_id: UUID = Field(foreign_key="badges.id", primary_key=True)
    
    earned_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Progress towards the badge (e.g. 3/5 days)
    # This can be used even before the badge is earned to show progress bars
    progress: int = Field(default=0)
    
    # Whether the badge has been seen/acknowledged by the user (for notifications)
    is_seen: bool = Field(default=False)
