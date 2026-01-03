"""Scholarship Test Models"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint
from typing import TYPE_CHECKING
from app.models.user import TargetExam
from enum import Enum

if TYPE_CHECKING:
    from app.models.linking import ScholarshipQuestion


class AttemptStatus(str, Enum):
    """Scholarship test attempt status"""
    active = "active"
    finished = "finished"
    not_started = "not_started"


class Scholarship(SQLModel, table=True):
    """
    Scholarship test model - similar to CustomTest.
    Each user can only have one scholarship test (enforced by unique constraint on user_id).
    """
    
    __tablename__ = "scholarship"
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_scholarship_user_id'),
    )
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign Keys
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    class_id: UUID = Field(foreign_key="class.id", index=True)
    
    # Exam type for which scholarship is being attempted
    exam_type: TargetExam = Field(index=True, description="Target exam type for scholarship")
    
    # Relationships
    questions: list["ScholarshipQuestion"] = Relationship(back_populates="scholarship")
    
    # Test configuration
    time_assigned: int = Field(description="Time assigned for the test in seconds")
    status: AttemptStatus = Field(default=AttemptStatus.not_started)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ScholarshipResult(SQLModel, table=True):
    """
    Stores scholarship test results for users.
    Contains score, time_taken, and detailed analysis.
    """
    
    __tablename__ = "scholarship_results"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign Keys
    user_id: UUID = Field(foreign_key="users.id", index=True)
    scholarship_id: UUID = Field(foreign_key="scholarship.id", index=True)
    
    # Result fields
    score: float = Field(description="Total score obtained in the scholarship test")
    total_marks: int = Field(description="Total marks possible in the test")
    time_taken: int = Field(description="Total time taken in seconds")
    
    # Analysis fields
    correct: int = Field(description="Number of correct answers")
    incorrect: int = Field(description="Number of incorrect answers")
    unattempted: int = Field(description="Number of unattempted questions")
    accuracy: float = Field(description="Accuracy percentage")
    
    # Code field
    code: str | None = Field(default=None, description="Code associated with the scholarship result")
    
    # Timestamps
    submitted_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

