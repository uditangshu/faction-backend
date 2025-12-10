"""Leaderboard Service"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
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


class LeaderboardService:
    """Service for leaderboard and best performers operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_best_by_rating(self) -> Optional[BestPerformerResponse]:
        """Get user with highest maximum rating"""
        result = await get_user_with_max_rating(self.db)
        if not result:
            return None
        
        user, max_rating = result
        return BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=max_rating,
            metric_type="max_rating",
        )

    async def get_top_by_rating(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by maximum rating"""
        results = await get_top_users_by_rating(self.db, limit)
        
        performers = [
            BestPerformerResponse(
                user=UserProfileResponse.model_validate(user),
                metric_value=rating,
                metric_type="max_rating",
            )
            for user, rating in results
        ]
        
        return BestPerformersListResponse(
            performers=performers,
            total=len(performers),
        )

    async def get_best_by_delta(self) -> Optional[BestPerformerResponse]:
        """Get user with highest rating delta from contests"""
        result = await get_user_with_max_delta(self.db)
        if not result:
            return None
        
        user, max_delta = result
        return BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=max_delta,
            metric_type="max_delta",
        )

    async def get_top_by_delta(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by maximum rating delta"""
        results = await get_top_users_by_delta(self.db, limit)
        
        performers = [
            BestPerformerResponse(
                user=UserProfileResponse.model_validate(user),
                metric_value=delta,
                metric_type="max_delta",
            )
            for user, delta in results
        ]
        
        return BestPerformersListResponse(
            performers=performers,
            total=len(performers),
        )

    async def get_best_by_questions_solved(self) -> Optional[BestPerformerResponse]:
        """Get user with most correct questions solved"""
        result = await get_user_with_most_questions_solved(self.db)
        if not result:
            return None
        
        user, question_count = result
        return BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=question_count,
            metric_type="max_questions_solved",
        )

    async def get_top_by_questions_solved(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by number of correct questions solved"""
        results = await get_top_users_by_questions_solved(self.db, limit)
        
        performers = [
            BestPerformerResponse(
                user=UserProfileResponse.model_validate(user),
                metric_value=count,
                metric_type="max_questions_solved",
            )
            for user, count in results
        ]
        
        return BestPerformersListResponse(
            performers=performers,
            total=len(performers),
        )

    async def get_top_performers_all_categories(self) -> TopPerformersResponse:
        """Get best performers in all categories"""
        highest_rating = await self.get_best_by_rating()
        highest_delta = await self.get_best_by_delta()
        most_questions = await self.get_best_by_questions_solved()
        
        return TopPerformersResponse(
            highest_rating=highest_rating,
            highest_delta=highest_delta,
            most_questions_solved=most_questions,
        )

    async def get_top_by_streak(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by current study streak"""
        results = await get_top_users_by_streak(self.db, limit)
        
        performers = [
            BestPerformerResponse(
                user=UserProfileResponse.model_validate(user),
                metric_value=streak,
                metric_type="streak",
            )
            for user, streak in results
        ]
        
        return BestPerformersListResponse(
            performers=performers,
            total=len(performers),
        )

    async def get_user_rank(self, user_id: UUID, metric_type: str) -> Optional[UserRankResponse]:
        """Get user's rank for a specific metric type"""
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

    async def get_rating_leaderboard_with_rank(
        self, user_id: UUID, limit: int = 10
    ) -> LeaderboardWithUserRankResponse:
        """Get rating leaderboard with user's own rank"""
        leaderboard = await self.get_top_by_rating(limit)
        user_rank = await self.get_user_rank(user_id, "rating")
        
        return LeaderboardWithUserRankResponse(
            leaderboard=leaderboard,
            user_rank=user_rank,
        )

    async def get_questions_leaderboard_with_rank(
        self, user_id: UUID, limit: int = 10
    ) -> LeaderboardWithUserRankResponse:
        """Get questions leaderboard with user's own rank"""
        leaderboard = await self.get_top_by_questions_solved(limit)
        user_rank = await self.get_user_rank(user_id, "questions")
        
        return LeaderboardWithUserRankResponse(
            leaderboard=leaderboard,
            user_rank=user_rank,
        )

    async def get_streak_leaderboard_with_rank(
        self, user_id: UUID, limit: int = 10
    ) -> LeaderboardWithUserRankResponse:
        """Get streak leaderboard with user's own rank"""
        leaderboard = await self.get_top_by_streak(limit)
        user_rank = await self.get_user_rank(user_id, "streak")
        
        return LeaderboardWithUserRankResponse(
            leaderboard=leaderboard,
            user_rank=user_rank,
        )

