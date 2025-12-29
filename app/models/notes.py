"""Notes model for PDF files"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional


class Notes(SQLModel, table=True):
    """Notes model for storing PDF files chapter-wise and subject-wise"""
    
    __tablename__ = "notes"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign Keys
    chapter_id: UUID = Field(foreign_key="chapter.id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id", index=True)
    
    # File Information
    file_name: str = Field(..., description="Name of the PDF file")
    file_id: str = Field(..., description="Supabase Storage file path")
    web_view_link: str = Field(..., description="Public URL to access the PDF file")
    web_content_link: Optional[str] = Field(None, description="Public content URL for the PDF file")
    
    # Metadata
    is_active: bool = Field(default=True, index=True, description="Whether note is active")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

