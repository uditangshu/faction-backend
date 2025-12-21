"""Contest Making model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from app.models.linking import ContestQuestions
from enum import Enum

class ContestStatus(str, Enum):
    active="active"
    finished="finished"
    not_started="not_started"

class Contest(SQLModel,table=True):

    id: UUID= Field(default_factory=uuid4, primary_key=True)
    questions: list["ContestQuestions"] = Relationship(back_populates="contest")
    name: str
    description: str | None = Field(default=None)
    total_time: int
    status: ContestStatus
    starts_at: datetime
    ends_at: datetime 
    
    created_at: datetime = Field(default_factory=datetime.now)

class ContestLeaderboard(SQLModel, table=True):
    """Combined model for contest leaderboard and submission analytics"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    contest_id: UUID = Field(foreign_key="contest.id")
    
    # Leaderboard fields
    score: float
    rank: int
    rating_before: int
    rating_after: int
    rating_delta: int
    missed: bool
    
    # Submission analytics fields
    accuracy: float
    total_questions: int
    attempted: int
    unattempted: int
    correct: int
    incorrect: int
    
    created_at: datetime = Field(default_factory=datetime.now)
