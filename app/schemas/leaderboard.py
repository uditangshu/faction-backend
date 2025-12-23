"""Leaderboard and Best Performers Schemas"""

from uuid import UUID
from pydantic import BaseModel
from app.schemas.user import UserProfileResponse


class BestPerformerResponse(BaseModel):
    """Best performer response with user profile and metric value"""
    
    user: UserProfileResponse
    metric_value: int
    metric_type: str  # "max_rating", "max_delta", "max_questions_solved"


class BestPerformersListResponse(BaseModel):
    """List of best performers"""
    
    performers: list[BestPerformerResponse]
    total: int


class TopPerformersResponse(BaseModel):
    """Top performers in different categories"""
    
    highest_rating: BestPerformerResponse | None = None
    highest_delta: BestPerformerResponse | None = None
    most_questions_solved: BestPerformerResponse | None = None


class ArenaRankingUserResponse(BaseModel):
    """Arena ranking user response with solved count"""
    
    user_id: UUID
    user_name: str
    questions_solved: int


class ArenaRankingResponse(BaseModel):
    """Paginated arena ranking response"""
    
    users: list[ArenaRankingUserResponse]
    total: int
    skip: int
    limit: int


class StreakRankingUserResponse(BaseModel):
    """Streak ranking user response with streak count"""
    
    user_id: UUID
    user_name: str
    longest_streak: int
    current_streak: int


class StreakRankingResponse(BaseModel):
    """Paginated streak ranking response"""
    
    users: list[StreakRankingUserResponse]
    total: int
    skip: int
    limit: int


class ContestRankingUserResponse(BaseModel):
    """Contest ranking user response with contest performance"""
    
    user_id: UUID
    user_name: str
    score: float
    rank: int
    rating_before: int
    rating_after: int
    rating_delta: int
    accuracy: float
    attempted: int
    correct: int
    incorrect: int


class ContestRankingResponse(BaseModel):
    """Paginated contest ranking response"""
    
    users: list[ContestRankingUserResponse]
    total: int
    skip: int
    limit: int

