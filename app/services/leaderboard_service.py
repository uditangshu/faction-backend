"""Leaderboard Service"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.models.user import User
from app.db.leaderboard_calls import (
    get_user_with_max_rating,
    get_top_users_by_rating,
    get_user_with_max_delta,
    get_top_users_by_delta,
    get_user_with_most_questions_solved,
    get_top_users_by_questions_solved,
    get_arena_ranking_by_submissions,
)
from app.schemas.leaderboard import (
    BestPerformerResponse,
    BestPerformersListResponse,
    TopPerformersResponse,
    ArenaRankingResponse,
    ArenaRankingUserResponse,
    StreakRankingResponse,
    StreakRankingUserResponse,
)
from app.db.streak_calls import get_streak_ranking, get_user_with_longest_streak
from app.schemas.user import UserProfileResponse
from app.integrations.redis_client import RedisService

CACHE_TTL = 300


class LeaderboardService:
    """Service for leaderboard and best performers operations"""

    def __init__(self, db: AsyncSession, redis: Optional[RedisService] = None):
        self.db = db
        self.redis = redis

    async def _get_cached(self, key: str) -> Optional[dict]:
        """Get cached data from Redis"""
        if not self.redis:
            return None
        cached_data = await self.redis.get_value(key)
        if isinstance(cached_data, dict):
            return cached_data
        return None

    async def _set_cached(self, key: str, data: dict) -> None:
        """Cache data in Redis"""
        if self.redis:
            await self.redis.set_value(key, data, expire=CACHE_TTL)

    async def get_best_by_rating(self) -> Optional[BestPerformerResponse]:
        """Get user with highest maximum rating"""
        cache_key = "leaderboard:best:rating"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformerResponse(**cached)

        result = await get_user_with_max_rating(self.db)
        if not result:
            return None
        
        user, max_rating = result
        response = BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=max_rating,
            metric_type="max_rating",
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_top_by_rating(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by maximum rating"""
        cache_key = f"leaderboard:top:rating:{limit}"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformersListResponse(**cached)

        results = await get_top_users_by_rating(self.db, limit)
        
        performers = [
            BestPerformerResponse(
                user=UserProfileResponse.model_validate(user),
                metric_value=rating,
                metric_type="max_rating",
            )
            for user, rating in results
        ]
        
        response = BestPerformersListResponse(
            performers=performers,
            total=len(performers),
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_best_by_delta(self) -> Optional[BestPerformerResponse]:
        """Get user with highest rating delta from contests"""
        cache_key = "leaderboard:best:delta"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformerResponse(**cached)

        result = await get_user_with_max_delta(self.db)
        if not result:
            return None
        
        user, max_delta = result
        response = BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=max_delta,
            metric_type="max_delta",
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_top_by_delta(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by maximum rating delta"""
        cache_key = f"leaderboard:top:delta:{limit}"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformersListResponse(**cached)

        results = await get_top_users_by_delta(self.db, limit)
        
        performers = [
            BestPerformerResponse(
                user=UserProfileResponse.model_validate(user),
                metric_value=delta,
                metric_type="max_delta",
            )
            for user, delta in results
        ]
        
        response = BestPerformersListResponse(
            performers=performers,
            total=len(performers),
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_best_by_questions_solved(self) -> Optional[BestPerformerResponse]:
        """Get user with most correct questions solved"""
        cache_key = "leaderboard:best:questions"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformerResponse(**cached)

        result = await get_user_with_most_questions_solved(self.db)
        if not result:
            return None
        
        user, question_count = result
        response = BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=question_count,
            metric_type="max_questions_solved",
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_top_by_questions_solved(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by number of correct questions solved"""
        cache_key = f"leaderboard:top:questions:{limit}"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformersListResponse(**cached)

        results = await get_top_users_by_questions_solved(self.db, limit)
        
        performers = [
            BestPerformerResponse(
                user=UserProfileResponse.model_validate(user),
                metric_value=count,
                metric_type="max_questions_solved",
            )
            for user, count in results
        ]
        
        response = BestPerformersListResponse(
            performers=performers,
            total=len(performers),
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_top_performers_all_categories(self) -> TopPerformersResponse:
        """Get best performers in all categories"""
        cache_key = "leaderboard:top:performers:all"
        cached = await self._get_cached(cache_key)
        if cached:
            return TopPerformersResponse(**cached)

        highest_rating = await self.get_best_by_rating()
        highest_delta = await self.get_best_by_delta()
        most_questions = await self.get_best_by_questions_solved()
        
        response = TopPerformersResponse(
            highest_rating=highest_rating,
            highest_delta=highest_delta,
            most_questions_solved=most_questions,
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_arena_ranking(
        self,
        time_filter: str = "all_time",
        skip: int = 0,
        limit: int = 20,
    ) -> ArenaRankingResponse:
        """
        Get arena ranking by maximum submissions solved with time filtering and pagination.
        
        Args:
            time_filter: Time filter - "daily", "weekly", or "all_time"
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
        
        Returns:
            ArenaRankingResponse with paginated users and their solved counts
        """
        cache_key = f"leaderboard:arena:{time_filter}:{skip}:{limit}"
        cached = await self._get_cached(cache_key)
        if cached:
            return ArenaRankingResponse(**cached)

        results, total = await get_arena_ranking_by_submissions(
            self.db,
            time_filter=time_filter,
            skip=skip,
            limit=limit,
        )
        
        users = [
            ArenaRankingUserResponse(
                user_id=user.id,
                user_name=user.name,
                questions_solved=count,
            )
            for user, count in results
        ]
        
        response = ArenaRankingResponse(
            users=users,
            total=total,
            skip=skip,
            limit=limit,
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_streak_ranking(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> StreakRankingResponse:
        """
        Get streak ranking sorted by longest streak with pagination.
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
        
        Returns:
            StreakRankingResponse with paginated users and their streak counts
        """
        cache_key = f"leaderboard:streak:{skip}:{limit}"
        cached = await self._get_cached(cache_key)
        if cached:
            return StreakRankingResponse(**cached)

        results, total = await get_streak_ranking(
            self.db,
            skip=skip,
            limit=limit,
        )
        
        users = [
            StreakRankingUserResponse(
                user_id=user.id,
                user_name=user.name,
                longest_streak=longest_streak,
                current_streak=current_streak,
            )
            for user, longest_streak, current_streak in results
        ]
        
        response = StreakRankingResponse(
            users=users,
            total=total,
            skip=skip,
            limit=limit,
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_best_by_longest_streak(self) -> Optional[BestPerformerResponse]:
        """Get user with longest study streak"""
        cache_key = "leaderboard:best:streak"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformerResponse(**cached)

        result = await get_user_with_longest_streak(self.db)
        if not result:
            return None
        
        user, longest_streak = result
        response = BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=longest_streak,
            metric_type="longest_streak",
        )
        await self._set_cached(cache_key, response.model_dump())
        return response
