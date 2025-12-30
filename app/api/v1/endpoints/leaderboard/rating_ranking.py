"""Rating Ranking endpoints"""

from fastapi import APIRouter, Query

from app.api.v1.dependencies import LeaderboardServiceDep, CurrentUser
from app.schemas.leaderboard import RatingRankingResponse

router = APIRouter(prefix="/rating-ranking", tags=["Rating Ranking"])


@router.get("/", response_model=RatingRankingResponse)
async def get_rating_ranking(
    leaderboard_service: LeaderboardServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> RatingRankingResponse:
    """
    Get rating ranking filtered by the current user's class and target exams.
    
    Returns paginated list of users with the same class_id as the current user,
    and where at least one target_exam matches, ranked by current_rating (descending).
    
    Includes rating information: current_rating, max_rating, and title.
    """
    return await leaderboard_service.get_rating_ranking(
        skip=skip,
        limit=limit,
        class_id=current_user.class_id,
        target_exams=current_user.target_exams,
    )

