"""Study streak and calendar endpoints"""

from fastapi import APIRouter, Query
from app.api.v1.dependencies import CurrentUser, StreakServiceDep
from app.schemas.streak import StreakResponse, CalendarResponse
from app.schemas.general import Successful_Query

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


@router.post("/me/create_study_stats",response_model= Successful_Query)
async def create_study_entry(
    streakService: StreakServiceDep,
    current_user: CurrentUser,
) -> Successful_Query:
    """
    This api will create a new study stats entry for any
    question is solved
    """
    result = await streakService.get_or_create_user_stats(current_user.id)
    return Successful_Query(
        msg= "Successfully updated the streak",
        id= result.id,
    )

    
@router.post("/me/update_study_stats", response_model= Successful_Query )
async def update_study_stats(
    streakService: StreakServiceDep,
    current_user: CurrentUser,
) -> Successful_Query:
    result = await streakService.update_streak_on_correct_answer(current_user.id)
    return Successful_Query(
        msg= "Successfully updated the streak",
        id= result.id,
    )

