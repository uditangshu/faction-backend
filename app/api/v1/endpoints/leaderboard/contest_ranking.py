"""Contest Ranking endpoints"""

from typing import Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Query, Path

from app.api.v1.dependencies import LeaderboardServiceDep, CurrentUser
from app.schemas.leaderboard import ContestRankingResponse
from app.models.user import TargetExam

router = APIRouter(prefix="/contest-ranking", tags=["Contest Ranking"])


@router.get("/", response_model=ContestRankingResponse)
async def get_contest_ranking(
    leaderboard_service: LeaderboardServiceDep,
    current_user: CurrentUser,
    filter_type: Literal["best_rating_first", "best_delta_first"] = Query(
        "best_rating_first",
        description="Filter by ranking: best_rating_first or best_delta_first"
    ),
    exam_type: Optional[TargetExam] = Query(
        None,
        description="Filter users by target exam type (optional)"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> ContestRankingResponse:
    """
    Get contest ranking from the most recent contest.
    
    Returns paginated list of all users who attended the contest, filtered by the current user's class and optionally by exam type, ranked by:
    - best_rating_first: Highest rating after contest first, then highest delta
    - best_delta_first: Highest rating delta first, then highest rating
    
    Includes contest performance metrics like score, rank, accuracy, etc.
    """
    return await leaderboard_service.get_contest_ranking(
        filter_type=filter_type,
        skip=skip,
        limit=limit,
        class_id=current_user.class_id,
        exam_type=exam_type.value if exam_type else None,
    )


@router.get("/{contest_id}", response_model=ContestRankingResponse)
async def get_contest_ranking_by_id(
    contest_id: UUID,
    leaderboard_service: LeaderboardServiceDep,
    filter_type: Literal["best_rating_first", "best_delta_first"] = Query(
        "best_rating_first",
        description="Filter by ranking: best_rating_first or best_delta_first"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> ContestRankingResponse:
    """
    Get contest ranking for a specific contest by contest_id.
    
    Returns paginated list of all users who attended the specified contest, ranked by:
    - best_rating_first: Highest rating after contest first, then highest delta
    - best_delta_first: Highest rating delta first, then highest rating
    
    Includes contest performance metrics like score, rank, accuracy, etc.
    """
    return await leaderboard_service.get_contest_ranking_by_contest_id(
        contest_id=contest_id,
        filter_type=filter_type,
        skip=skip,
        limit=limit,
    )
