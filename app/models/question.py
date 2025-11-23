"""Question bank models"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class QuestionType(str, Enum):
    """Question type enumeration"""
    MCQ = "mcq"
    NUMERICAL = "numerical"
    MULTI_SELECT = "multi_select"
    ASSERTION_REASON = "assertion_reason"


class DifficultyLevel(int, Enum):
    """Difficulty level (1-5 scale)"""
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4
    MASTER = 5


class Question(SQLModel, table=True):
    """Question model"""
    
    __tablename__ = "questions"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    subject_id: UUID = Field(foreign_key="subjects.id", index=True)
    topic_id: UUID = Field(foreign_key="topics.id", index=True)
    concept_id: UUID | None = Field(default=None, foreign_key="concepts.id", index=True)
    
    question_text: str
    question_type: QuestionType
    difficulty_level: int = Field(ge=1, le=5, default=1)
    difficulty_rating: int = Field(default=1200)  # ELO-style rating (800-2000+)
    
    # For numerical questions
    correct_numerical_value: float | None = None
    numerical_tolerance: float | None = Field(default=0.01)
    
    # Metadata
    time_limit: int = Field(default=120)  # seconds
    points: int = Field(default=10)
    explanation: str | None = None
    solution_video_url: str | None = None
    image_url: str | None = None
    
    # Stats
    solved_count: int = Field(default=0)
    attempt_count: int = Field(default=0)
    
    created_by: UUID = Field(foreign_key="users.id")
    is_active: bool = Field(default=True)
    is_premium: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QuestionOption(SQLModel, table=True):
    """Question options for MCQ and Multi-Select questions"""
    
    __tablename__ = "question_options"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question_id: UUID = Field(foreign_key="questions.id", index=True)
    option_text: str
    option_label: str = Field(max_length=2)  # A, B, C, D
    is_correct: bool = Field(default=False)
    option_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

