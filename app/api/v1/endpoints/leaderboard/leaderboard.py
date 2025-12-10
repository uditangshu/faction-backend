"""Leaderboard and Best Performers endpoints"""

from typing import Optional
from fastapi import APIRouter, Query

from app.api.v1.dependencies import LeaderboardServiceDep, CurrentUser
from app.schemas.leaderboard import (
    BestPerformerResponse,
    BestPerformersListResponse,
    TopPerformersResponse,
    UserRankResponse,
    LeaderboardWithUserRankResponse,
)
from app.exceptions.http_exceptions import NotFoundException

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("/top-performers", response_model=TopPerformersResponse)
async def get_top_performers_all(
    leaderboard_service: LeaderboardServiceDep,
) -> TopPerformersResponse:
    """
    Get best performers in all categories:
    - Highest maximum rating
    - Highest rating delta from contests
    - Most questions solved
    """
    return await leaderboard_service.get_top_performers_all_categories()


@router.get("/best-rating", response_model=BestPerformerResponse)
async def get_best_by_rating(
    leaderboard_service: LeaderboardServiceDep,
) -> BestPerformerResponse:
    """
    Get user with the highest maximum contest rating.
    """
    result = await leaderboard_service.get_best_by_rating()
    if not result:
        raise NotFoundException("No users found with ratings")
    return result


@router.get("/top-rating", response_model=BestPerformersListResponse)
async def get_top_by_rating(
    leaderboard_service: LeaderboardServiceDep,
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
) -> BestPerformersListResponse:
    """
    Get top N users by maximum contest rating.
    """
    return await leaderboard_service.get_top_by_rating(limit)


@router.get("/best-delta", response_model=BestPerformerResponse)
async def get_best_by_delta(
    leaderboard_service: LeaderboardServiceDep,
) -> BestPerformerResponse:
    """
    Get user with the highest rating delta achieved in any contest.
    """
    result = await leaderboard_service.get_best_by_delta()
    if not result:
        raise NotFoundException("No contest leaderboard entries found")
    return result


@router.get("/top-delta", response_model=BestPerformersListResponse)
async def get_top_by_delta(
    leaderboard_service: LeaderboardServiceDep,
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
) -> BestPerformersListResponse:
    """
    Get top N users by maximum rating delta from contests.
    """
    return await leaderboard_service.get_top_by_delta(limit)


@router.get("/best-questions", response_model=BestPerformerResponse)
async def get_best_by_questions_solved(
    leaderboard_service: LeaderboardServiceDep,
) -> BestPerformerResponse:
    """
    Get user with the most correct questions solved.
    """
    result = await leaderboard_service.get_best_by_questions_solved()
    if not result:
        raise NotFoundException("No question attempts found")
    return result


@router.get("/top-questions", response_model=BestPerformersListResponse)
async def get_top_by_questions_solved(
    leaderboard_service: LeaderboardServiceDep,
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
) -> BestPerformersListResponse:
    """
    Get top N users by number of correct questions solved.
    """
    return await leaderboard_service.get_top_by_questions_solved(limit)


@router.get("/top-streak", response_model=BestPerformersListResponse)
async def get_top_by_streak(
    leaderboard_service: LeaderboardServiceDep,
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
) -> BestPerformersListResponse:
    """
    Get top N users by current study streak.
    """
    return await leaderboard_service.get_top_by_streak(limit)


@router.get("/my-rank/{metric_type}", response_model=UserRankResponse)
async def get_my_rank(
    metric_type: str,
    leaderboard_service: LeaderboardServiceDep,
    current_user: CurrentUser,
) -> UserRankResponse:
    """
    Get current user's rank for a specific metric.
    
    metric_type can be: "rating", "questions", or "streak"
    """
    if metric_type not in ["rating", "questions", "streak"]:
        raise NotFoundException(f"Unknown metric type: {metric_type}")
    
    result = await leaderboard_service.get_user_rank(current_user.id, metric_type)
    if not result:
        raise NotFoundException(f"No rank found for metric: {metric_type}")
    return result


@router.get("/contest", response_model=LeaderboardWithUserRankResponse)
async def get_contest_leaderboard(
    leaderboard_service: LeaderboardServiceDep,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100, description="Number of top users to return"),
) -> LeaderboardWithUserRankResponse:
    """
    Get contest rating leaderboard with current user's rank.
    """
    return await leaderboard_service.get_rating_leaderboard_with_rank(current_user.id, limit)


@router.get("/practice", response_model=LeaderboardWithUserRankResponse)
async def get_practice_leaderboard(
    leaderboard_service: LeaderboardServiceDep,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100, description="Number of top users to return"),
) -> LeaderboardWithUserRankResponse:
    """
    Get practice (questions solved) leaderboard with current user's rank.
    """
    return await leaderboard_service.get_questions_leaderboard_with_rank(current_user.id, limit)


@router.get("/streak", response_model=LeaderboardWithUserRankResponse)
async def get_streak_leaderboard(
    leaderboard_service: LeaderboardServiceDep,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100, description="Number of top users to return"),
) -> LeaderboardWithUserRankResponse:
    """
    Get streak leaderboard with current user's rank.
    """
    return await leaderboard_service.get_streak_leaderboard_with_rank(current_user.id, limit)

