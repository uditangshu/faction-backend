"""QOTD (Question of the Day) model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, List, Dict, Any


class QOTD(SQLModel, table=True):
    """Question of the Day model - stores daily questions in JSON format"""
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Class filter - required for QOTD
    class_id: UUID = Field(foreign_key="class.id", index=True)
    
    # Questions data stored as JSON (matches QOTDResponse format)
    questions: List[Dict[str, Any]] = Field(sa_column=Column(JSON))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: Optional[datetime] = None

