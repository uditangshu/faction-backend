"""Notes schemas"""

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class NotesResponse(BaseModel):
    """Notes response"""
    
    id: UUID
    chapter_id: UUID
    subject_id: UUID
    file_name: str
    file_id: str
    web_view_link: str
    web_content_link: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotesListResponse(BaseModel):
    """List of notes response"""
    
    notes: List[NotesResponse]
    total: int
    class_id: UUID
    subject_id: Optional[UUID] = None
    chapter_id: Optional[UUID] = None

