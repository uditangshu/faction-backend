"""Question attempt tracking model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, JSON, Column
from typing import List, Optional

class QuestionAttempt(SQLModel, table=True):
    """User question attempt records"""
    
    __tablename__ = "question_attempts"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    question_id: UUID = Field(foreign_key="question.id", index=True)
    
    # Answer data
    user_answer: List[str] = Field(sa_column=Column(JSON))
    is_correct: bool = Field(index=True)
    marks_obtained: int = Field(default=0)
    time_taken: int  = Field(default=0)
    
    # Metadata
    attempted_at: datetime = Field(default_factory=datetime.utcnow)
    explanation_viewed: bool = Field(default=False)
    hint_used: bool = Field(default=True)
