"""Streak Ranking endpoints"""

from fastapi import APIRouter, Query

from app.api.v1.dependencies import LeaderboardServiceDep
from app.schemas.leaderboard import StreakRankingResponse

router = APIRouter(prefix="/streak-ranking", tags=["Streak Ranking"])


@router.get("/", response_model=StreakRankingResponse)
async def get_streak_ranking(
    leaderboard_service: LeaderboardServiceDep,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> StreakRankingResponse:
    """
    Get streak ranking sorted by maximum current streak.
    
    Returns paginated list of users ranked by current study streak (descending),
    including both longest streak and current streak information.
    """
    return await leaderboard_service.get_streak_ranking(
        skip=skip,
        limit=limit,
    )

