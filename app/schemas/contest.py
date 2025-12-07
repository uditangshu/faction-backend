"""Contest schemas"""

from uuid import UUID
from pydantic import BaseModel
from typing import List


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

