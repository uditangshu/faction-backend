"""Weak topics model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import UniqueConstraint, Index
from typing import Optional

class UserWeakTopic(SQLModel, table=True):
    """User's weak topics aggregated from wrong attempts"""
    
    __tablename__ = "user_weak_topics"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    topic_id: UUID = Field(foreign_key="topic.id", index=True)
    
    # Performance Metrics
    total_attempt: int = Field(default=0)
    incorrect_attempts: int = Field(default=0)
    correct_attempts: int = Field(default=0)
    weakness_score: float = Field(default=0.0, index=True)  # (incorrect/total) * 100
    
    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.now, index=True)
    
    
    # Composite unique constraint and index
    __table_args__ = (
        UniqueConstraint('user_id', 'topic_id', name='uq_user_topic'),
        Index('idx_user_weakness', 'user_id', 'weakness_score'),
    )

