"""Streak Ranking endpoints"""

from typing import Optional
from fastapi import APIRouter, Query

from app.api.v1.dependencies import LeaderboardServiceDep, CurrentUser
from app.schemas.leaderboard import StreakRankingResponse
from app.models.user import TargetExam

router = APIRouter(prefix="/streak-ranking", tags=["Streak Ranking"])


@router.get("/", response_model=StreakRankingResponse)
async def get_streak_ranking(
    leaderboard_service: LeaderboardServiceDep,
    current_user: CurrentUser,
    exam_type: Optional[TargetExam] = Query(
        None,
        description="Filter users by target exam type (optional)"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> StreakRankingResponse:
    """
    Get streak ranking sorted by maximum current streak.
    
    Returns paginated list of users ranked by current study streak (descending),
    filtered by the current user's class and optionally by exam type,
    including both longest streak and current streak information.
    """
    return await leaderboard_service.get_streak_ranking(
        skip=skip,
        limit=limit,
        class_id=current_user.class_id,
        exam_type=exam_type.value if exam_type else None,
    )

