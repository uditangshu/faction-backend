"""Question attempt tracking model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class QuestionAttempt(SQLModel, table=True):
    """User question attempt records"""
    
    __tablename__ = "question_attempts"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    question_id: UUID = Field(foreign_key="questions.id", index=True)
    
    # Answer data
    user_answer: str  # Stored as JSON string for multi-select
    is_correct: bool
    marks_obtained: int = Field(default=0)
    time_taken: int  # seconds
    
    # Metadata
    attempted_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    explanation_viewed: bool = Field(default=False)

