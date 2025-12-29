"""Notification model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Text, ForeignKey
import sqlmodel
from typing import Optional
import enum


class NotificationType(str, enum.Enum):
    """Types of notifications"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CONTEST = "contest"
    ACHIEVEMENT = "achievement"
    STREAK = "streak"
    SYSTEM = "system"
    ANNOUNCEMENT = "announcement"


class Notification(SQLModel, table=True):
    """User notification"""
    
    __tablename__ = "notifications"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            sqlmodel.sql.sqltypes.GUID(),
            ForeignKey("users.id", ondelete="CASCADE"),
            index=True
        )
    )
    
    title: str = Field(..., max_length=200, description="Notification title")
    message: str = Field(sa_column=Column(Text), description="Notification message body")
    type: NotificationType = Field(default=NotificationType.INFO, description="Notification type")
    
    is_read: bool = Field(default=False, index=True, description="Whether notification has been read")
    
    # Optional metadata as JSON string
    data: Optional[str] = Field(None, description="Optional JSON metadata")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
