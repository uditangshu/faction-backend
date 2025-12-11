"""Arena Ranking endpoints"""

from typing import Literal
from fastapi import APIRouter, Query

from app.api.v1.dependencies import LeaderboardServiceDep
from app.schemas.leaderboard import ArenaRankingResponse

router = APIRouter(prefix="/arena-ranking", tags=["Arena Ranking"])


@router.get("/", response_model=ArenaRankingResponse)
async def get_arena_ranking(
    leaderboard_service: LeaderboardServiceDep,
    time_filter: Literal["daily", "weekly", "all_time"] = Query(
        "all_time",
        description="Filter by time period: daily, weekly, or all_time"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> ArenaRankingResponse:
    """
    Get arena ranking by maximum submissions solved.
    
    Returns paginated list of users ranked by number of distinct questions solved,
    with optional time filtering (daily, weekly, or all_time).
    """
    return await leaderboard_service.get_arena_ranking(
        time_filter=time_filter,
        skip=skip,
        limit=limit,
    )

