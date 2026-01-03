"""Arena Ranking endpoints"""

from typing import Literal, Optional
from fastapi import APIRouter, Query

from app.api.v1.dependencies import LeaderboardServiceDep, CurrentUser
from app.schemas.leaderboard import ArenaRankingResponse
from app.models.user import TargetExam

router = APIRouter(prefix="/arena-ranking", tags=["Arena Ranking"])


@router.get("/", response_model=ArenaRankingResponse)
async def get_arena_ranking(
    leaderboard_service: LeaderboardServiceDep,
    current_user: CurrentUser,
    time_filter: Literal["daily", "weekly", "all_time"] = Query(
        "all_time",
        description="Filter by time period: daily, weekly, or all_time"
    ),
    exam_type: Optional[TargetExam] = Query(
        None,
        description="Filter users by target exam type (optional)"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> ArenaRankingResponse:
    """
    Get arena ranking by maximum submissions solved.
    
    Returns paginated list of users ranked by number of distinct questions solved,
    filtered by the current user's class and optionally by exam type,
    with optional time filtering (daily, weekly, or all_time).
    
    Note: current_user_rank is only returned if exam_type is None or if current user has that exam_type.
    """
    exam_type_value = exam_type.value if exam_type else None
    
    # Only get user rank if exam_type is None OR if current user has the exam_type
    should_get_user_rank = exam_type_value is None or (exam_type_value in (current_user.target_exams or []))
    
    return await leaderboard_service.get_arena_ranking(
        time_filter=time_filter,
        skip=skip,
        limit=limit,
        class_id=current_user.class_id,
        exam_type=exam_type_value,
        user_id=current_user.id if should_get_user_rank else None,
    )

