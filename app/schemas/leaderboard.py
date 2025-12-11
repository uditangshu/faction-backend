"""Leaderboard and Best Performers Schemas"""

from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from app.schemas.user import UserProfileResponse


class BestPerformerResponse(BaseModel):
    """Best performer response with user profile and metric value"""
    
    user: UserProfileResponse
    metric_value: int
    metric_type: str  # "max_rating", "max_delta", "max_questions_solved", "streak"


class BestPerformersListResponse(BaseModel):
    """List of best performers"""
    
    performers: list[BestPerformerResponse]
    total: int


class TopPerformersResponse(BaseModel):
    """Top performers in different categories"""
    
    highest_rating: BestPerformerResponse | None = None
    highest_delta: BestPerformerResponse | None = None
    most_questions_solved: BestPerformerResponse | None = None


class UserRankResponse(BaseModel):
    """User's own rank in a leaderboard"""
    
    rank: int
    metric_value: int
    total_users: int
    percentile: float  # e.g., 60 means "better than 60% of peers"
    metric_type: str


class LeaderboardWithUserRankResponse(BaseModel):
    """Full leaderboard with user's own rank"""
    
    leaderboard: BestPerformersListResponse
    user_rank: Optional[UserRankResponse] = None


class StreakRankingResponse(BaseModel):
    """Streak ranking response"""
    
    performers: list[BestPerformerResponse]
    total: int

