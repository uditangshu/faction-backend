"""Study streak and calendar endpoints"""

from fastapi import APIRouter, Query
from app.api.v1.dependencies import CurrentUser, StreakServiceDep
from app.schemas.streak import StreakResponse, CalendarResponse

router = APIRouter(prefix="/streaks", tags=["Streaks"])


@router.get("/me", response_model=StreakResponse)
async def get_my_streak(
    streak_service: StreakServiceDep,
    current_user: CurrentUser,
) -> StreakResponse:
    """
    Get current user's streak information.
    
    Returns current streak, longest streak, and related statistics.
    """
    streak_info = await streak_service.get_user_streak_info(current_user.id)
    return StreakResponse(**streak_info)


@router.get("/me/calendar", response_model=CalendarResponse)
async def get_my_calendar(
    streak_service: StreakServiceDep,
    current_user: CurrentUser,
    days: int = Query(365, ge=30, le=730, description="Number of days to include"),
) -> CalendarResponse:
    """
    Get GitHub-style study calendar.
    
    Returns daily activity data with intensity levels (0-4) for visualization.
    
    Query parameters:
    - days: Number of days to include (default: 365, max: 730)
    """
    calendar_data = await streak_service.get_study_calendar(current_user.id, days=days)
    return CalendarResponse(**calendar_data)

