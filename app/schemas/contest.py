"""Contest schemas"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from app.models.contest import ContestStatus
from app.schemas.question import QuestionDetailedResponse


class ContestLeaderboardResponse(BaseModel):
    """Contest leaderboard entry response"""
    
    id: UUID
    contest_id: UUID
    user_id: UUID
    score: int
    rank: int
    rating_before: int
    rating_after: int
    rating_delta: int
    missed: bool

    class Config:
        from_attributes = True


class ContestLeaderboardListResponse(BaseModel):
    """List of contest leaderboard entries"""
    
    leaderboard_entries: List[ContestLeaderboardResponse]
    total: int


# ==================== Contest CRUD Schemas ====================

class ContestCreateRequest(BaseModel):
    """Request to create a new contest"""
    total_time: int
    status: ContestStatus
    starts_at: datetime
    ends_at: datetime
    question_ids: List[UUID]


class ContestUpdateRequest(BaseModel):
    """Request to update an existing contest"""
    total_time: Optional[int] = None
    status: Optional[ContestStatus] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class ContestResponse(BaseModel):
    """Contest response"""
    id: UUID
    total_time: int
    status: ContestStatus
    starts_at: datetime
    ends_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ContestWithQuestionsResponse(BaseModel):
    """Contest response with all linked questions"""
    id: UUID
    total_time: int
    status: ContestStatus
    starts_at: datetime
    ends_at: datetime
    created_at: datetime
    questions: List[QuestionDetailedResponse]

    class Config:
        from_attributes = True

