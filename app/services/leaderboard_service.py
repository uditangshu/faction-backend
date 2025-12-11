from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.leaderboard_calls import (
    get_user_with_max_rating,
    get_top_users_by_rating,
    get_user_with_max_delta,
    get_top_users_by_delta,
    get_user_with_most_questions_solved,
    get_top_users_by_questions_solved,
    get_top_users_by_streak,
    get_user_rank_by_rating,
    get_user_rank_by_questions,
    get_user_rank_by_streak,
)
from app.schemas.leaderboard import (
    BestPerformerResponse,
    BestPerformersListResponse,
    TopPerformersResponse,
    UserRankResponse,
    LeaderboardWithUserRankResponse,
)
from app.schemas.user import UserProfileResponse
from app.integrations.redis_client import RedisService

CACHE_TTL = 300


class LeaderboardService:
    def __init__(self, db: AsyncSession, redis: Optional[RedisService] = None):
        self.db = db
        self.redis = redis

    async def _get_cached(self, key: str) -> Optional[dict]:
        if not self.redis:
            return None
        return await self.redis.get_value(key)

    async def _set_cached(self, key: str, data: dict) -> None:
        if self.redis:
            await self.redis.set_value(key, data, expire=CACHE_TTL)

    async def get_best_by_rating(self) -> Optional[BestPerformerResponse]:
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
        response = BestPerformersListResponse(performers=performers, total=len(performers))
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_best_by_delta(self) -> Optional[BestPerformerResponse]:
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
        response = BestPerformersListResponse(performers=performers, total=len(performers))
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_best_by_questions_solved(self) -> Optional[BestPerformerResponse]:
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
        response = BestPerformersListResponse(performers=performers, total=len(performers))
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_top_performers_all_categories(self) -> TopPerformersResponse:
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

    async def get_top_by_streak(self, limit: int = 10) -> BestPerformersListResponse:
        cache_key = f"leaderboard:top:streak:{limit}"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformersListResponse(**cached)

        results = await get_top_users_by_streak(self.db, limit)
        performers = [
            BestPerformerResponse(
                user=UserProfileResponse.model_validate(user),
                metric_value=streak,
                metric_type="streak",
            )
            for user, streak in results
        ]
        response = BestPerformersListResponse(performers=performers, total=len(performers))
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_best_by_longest_streak(self) -> Optional[BestPerformerResponse]:
        cache_key = "leaderboard:best:streak"
        cached = await self._get_cached(cache_key)
        if cached:
            return BestPerformerResponse(**cached)

        results = await get_top_users_by_streak(self.db, limit=1)
        if not results:
            return None

        user, streak = results[0]
        response = BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=streak,
            metric_type="streak",
        )
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_user_rank(self, user_id: UUID, metric_type: str) -> Optional[UserRankResponse]:
        if metric_type == "rating":
            result = await get_user_rank_by_rating(self.db, user_id)
        elif metric_type == "questions":
            result = await get_user_rank_by_questions(self.db, user_id)
        elif metric_type == "streak":
            result = await get_user_rank_by_streak(self.db, user_id)
        else:
            return None

        if not result:
            return None

        rank, metric_value, total_users = result
        percentile = ((total_users - rank) / total_users) * 100 if total_users > 0 else 0

        return UserRankResponse(
            rank=rank,
            metric_value=metric_value,
            total_users=total_users,
            percentile=round(percentile, 1),
            metric_type=metric_type,
        )

    async def get_rating_leaderboard_with_rank(self, user_id: UUID, limit: int = 10) -> LeaderboardWithUserRankResponse:
        leaderboard = await self.get_top_by_rating(limit)
        user_rank = await self.get_user_rank(user_id, "rating")
        return LeaderboardWithUserRankResponse(leaderboard=leaderboard, user_rank=user_rank)

    async def get_questions_leaderboard_with_rank(self, user_id: UUID, limit: int = 10) -> LeaderboardWithUserRankResponse:
        leaderboard = await self.get_top_by_questions_solved(limit)
        user_rank = await self.get_user_rank(user_id, "questions")
        return LeaderboardWithUserRankResponse(leaderboard=leaderboard, user_rank=user_rank)

    async def get_streak_leaderboard_with_rank(self, user_id: UUID, limit: int = 10) -> LeaderboardWithUserRankResponse:
        leaderboard = await self.get_top_by_streak(limit)
        user_rank = await self.get_user_rank(user_id, "streak")
        return LeaderboardWithUserRankResponse(leaderboard=leaderboard, user_rank=user_rank)
