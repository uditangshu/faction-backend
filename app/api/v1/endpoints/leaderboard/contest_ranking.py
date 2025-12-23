"""Contest Ranking endpoints"""

from typing import Literal
from fastapi import APIRouter, Query

from app.api.v1.dependencies import LeaderboardServiceDep
from app.schemas.leaderboard import ContestRankingResponse

router = APIRouter(prefix="/contest-ranking", tags=["Contest Ranking"])


@router.get("/", response_model=ContestRankingResponse)
async def get_contest_ranking(
    leaderboard_service: LeaderboardServiceDep,
    filter_type: Literal["best_rating_first", "best_delta_first"] = Query(
        "best_rating_first",
        description="Filter by ranking: best_rating_first or best_delta_first"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> ContestRankingResponse:
    """
    Get contest ranking from the most recent contest.
    
    Returns paginated list of all users who attended the contest, ranked by:
    - best_rating_first: Highest rating after contest first, then highest delta
    - best_delta_first: Highest rating delta first, then highest rating
    
    Includes contest performance metrics like score, rank, accuracy, etc.
    """
    return await leaderboard_service.get_contest_ranking(
        filter_type=filter_type,
        skip=skip,
        limit=limit,
    )
