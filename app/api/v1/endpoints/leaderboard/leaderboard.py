"""Leaderboard and Best Performers endpoints"""

from typing import Optional
from fastapi import APIRouter, Query

from app.api.v1.dependencies import LeaderboardServiceDep, ReadOnlyDBSession
from app.schemas.leaderboard import (
    BestPerformerResponse,
    BestPerformersListResponse,
    TopPerformersResponse,
)
from app.exceptions.http_exceptions import NotFoundException

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("/top-performers", response_model=TopPerformersResponse)
async def get_top_performers_all(
    leaderboard_service: LeaderboardServiceDep, 
    db: ReadOnlyDBSession,
) -> TopPerformersResponse:
    """
    Get best performers in all categories:
    - Highest maximum rating
    - Highest rating delta from contests
    - Most questions solved
    """
    return await leaderboard_service.get_top_performers_all_categories(db)


@router.get("/best-rating", response_model=BestPerformerResponse)
async def get_best_by_rating(
    leaderboard_service: LeaderboardServiceDep,
    db: ReadOnlyDBSession,
) -> BestPerformerResponse:
    """
    Get user with the highest maximum contest rating.
    """
    result = await leaderboard_service.get_best_by_rating(db)
    if not result:
        raise NotFoundException("No users found with ratings")
    return BestPerformerResponse.model_validate(result)


@router.get("/top-rating", response_model=BestPerformersListResponse)
async def get_top_by_rating(
    leaderboard_service: LeaderboardServiceDep,
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
) -> BestPerformersListResponse:
    """
    Get top N users by maximum contest rating.
    """
    return await leaderboard_service.get_top_by_rating(db, limit)


@router.get("/best-delta", response_model=BestPerformerResponse)
async def get_best_by_delta(
    leaderboard_service: LeaderboardServiceDep,
    db: ReadOnlyDBSession,
) -> BestPerformerResponse:
    """
    Get user with the highest rating delta achieved in any contest.
    """
    result = await leaderboard_service.get_best_by_delta(db)
    if not result:
        raise NotFoundException("No contest leaderboard entries found")
    return result


@router.get("/top-delta", response_model=BestPerformersListResponse)
async def get_top_by_delta(
    leaderboard_service: LeaderboardServiceDep,
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
    db: ReadOnlyDBSession,
) -> BestPerformersListResponse:
    """
    Get top N users by maximum rating delta from contests.
    """
    return await leaderboard_service.get_top_by_delta(db, limit)


@router.get("/best-questions", response_model=BestPerformerResponse)
async def get_best_by_questions_solved(
    leaderboard_service: LeaderboardServiceDep,
    db: ReadOnlyDBSession,
) -> BestPerformerResponse:
    """
    Get user with the most correct questions solved.
    """
    result = await leaderboard_service.get_best_by_questions_solved(db)
    if not result:
        raise NotFoundException("No question attempts found")
    return BestPerformerResponse.model_validate(result)


@router.get("/top-questions", response_model=BestPerformersListResponse)
async def get_top_by_questions_solved(
    leaderboard_service: LeaderboardServiceDep,
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
    db: ReadOnlyDBSession,
) -> BestPerformersListResponse:
    """
    Get top N users by number of correct questions solved.
    """
    return await leaderboard_service.get_top_by_questions_solved(db, limit)


@router.get("/best-streak", response_model=BestPerformerResponse)
async def get_best_by_longest_streak(
    leaderboard_service: LeaderboardServiceDep,
    db: ReadOnlyDBSession,
) -> BestPerformerResponse:
    """
    Get user with the longest study streak.
    """
    result = await leaderboard_service.get_best_by_longest_streak(db)
    if not result:
        raise NotFoundException("No users found with study streaks")
    return BestPerformerResponse.model_validate(result)

