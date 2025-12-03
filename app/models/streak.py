"""Study statistics and streak tracking models"""

from datetime import datetime, date
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column, JSON
from typing import Dict, Any


class UserStudyStats(SQLModel, table=True):
    """User study statistics and streak information"""
    
    __tablename__ = "user_study_stats"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    
    # Question solving stats
    questions_solved: int = Field(default=0)
    total_attempts: int = Field(default=0)
    accuracy_rate: float = Field(default=0.0)
    
    # Difficulty-wise breakdown
    easy_solved: int = Field(default=0)
    medium_solved: int = Field(default=0)
    hard_solved: int = Field(default=0)
    
    # Streak tracking
    current_study_streak: int = Field(default=0)
    longest_study_streak: int = Field(default=0)
    last_study_date: date | None = None
    
    # Performance rating (ELO-style)
    performance_rating: int = Field(default=1200)
    
    # Calendar data for GitHub-style visualization
    study_activity_graph: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserDailyStreak(SQLModel, table=True):
    """Daily streak records for calendar visualization"""
    
    __tablename__ = "user_daily_streaks"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    streak_date: date = Field(index=True)
    problems_solved: int = Field(default=0)
    first_solve_time: datetime | None = None
    last_solve_time: datetime | None = None
    streak_maintained: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)

