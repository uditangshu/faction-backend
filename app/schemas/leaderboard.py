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

