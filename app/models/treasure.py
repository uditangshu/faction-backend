"""Treasure model for mindmap images"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional


class Treasure(SQLModel, table=True):
    """Treasure model for storing mindmap images chapter-wise and subject-wise"""
    
    __tablename__ = "treasures"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign Keys
    chapter_id: UUID = Field(foreign_key="chapter.id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id", index=True)
    
    # Image Information
    image_url: str = Field(..., description="Cloudinary URL of the mindmap image")
    title: Optional[str] = Field(None, max_length=200, description="Optional title for the treasure")
    description: Optional[str] = Field(None, description="Optional description for the treasure")
    
    # Metadata
    is_active: bool = Field(default=True, index=True, description="Whether treasure is active")
    order: int = Field(default=0, description="Order/sequence within chapter")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

