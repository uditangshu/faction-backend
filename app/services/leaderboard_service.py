"""Leaderboard Service"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.config import settings

from app.models.user import User
from app.integrations.redis_client import RedisService
from app.db.leaderboard_calls import (
    get_user_with_max_rating,
    get_top_users_by_rating,
    get_user_with_max_delta,
    get_top_users_by_delta,
    get_user_with_most_questions_solved,
    get_top_users_by_questions_solved,
    get_arena_ranking_by_submissions,
    get_user_arena_rank,
    get_contest_ranking_by_filter,
    get_contest_ranking_by_contest_id,
    get_rating_ranking_by_filter,
)
from app.schemas.leaderboard import (
    BestPerformerResponse,
    BestPerformersListResponse,
    TopPerformersResponse,
    ArenaRankingResponse,
    ArenaRankingUserResponse,
    StreakRankingResponse,
    StreakRankingUserResponse,
    ContestRankingResponse,
    ContestRankingUserResponse,
    RatingRankingResponse,
    RatingRankingUserResponse,
)
from app.db.streak_calls import get_streak_ranking, get_user_with_longest_streak
from app.schemas.user import UserProfileResponse
from app.core.config import settings


class LeaderboardService:
    """Service for leaderboard and best performers operations"""

    CACHE_PREFIX = "leaderboard"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    async def get_best_by_rating(self) -> Optional[BestPerformerResponse]:
        """Get user with highest maximum rating (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:best:rating"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
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
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_top_by_rating(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by maximum rating (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:top:rating:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
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
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_best_by_delta(self) -> Optional[BestPerformerResponse]:
        """Get user with highest rating delta from contests (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:best:delta"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
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
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_top_by_delta(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by maximum rating delta (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:top:delta:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
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
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_best_by_questions_solved(self) -> Optional[BestPerformerResponse]:
        """Get user with most correct questions solved (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:best:questions"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
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
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_top_by_questions_solved(self, limit: int = 10) -> BestPerformersListResponse:
        """Get top N users by number of correct questions solved (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:top:questions:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
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
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_top_performers_all_categories(self) -> TopPerformersResponse:
        """Get best performers in all categories (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:top:all"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                return TopPerformersResponse(**cached)
        
        highest_rating = await self.get_best_by_rating()
        highest_delta = await self.get_best_by_delta()
        most_questions = await self.get_best_by_questions_solved()
        
        response = TopPerformersResponse(
            highest_rating=highest_rating,
            highest_delta=highest_delta,
            most_questions_solved=most_questions,
        )
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_arena_ranking(
        self,
        time_filter: str = "all_time",
        skip: int = 0,
        limit: int = 20,
        class_id: Optional[UUID] = None,
        exam_type: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> ArenaRankingResponse:
        """
        Get arena ranking by maximum submissions solved with time filtering and pagination.
        
        Args:
            time_filter: Time filter - "daily", "weekly", or "all_time"
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            class_id: Optional class ID to filter users by class
            exam_type: Optional target exam type to filter users by matching exam
            user_id: Optional user ID to get current user's rank
        
        Returns:
            ArenaRankingResponse with paginated users and their solved counts
        """
        results, total = await get_arena_ranking_by_submissions(
            self.db,
            time_filter=time_filter,
            skip=skip,
            limit=limit,
            class_id=class_id,
            exam_type=exam_type,
        )
        
        users = [
            ArenaRankingUserResponse(
                user_id=user.id,
                user_name=user.name,
                avatar_url=user.avatar_url,
                questions_solved=count,
            )
            for user, count in results
        ]
        
        # Get user rank if user_id provided
        user_rank, user_data = None, None
        if user_id:
            user_rank, user_data = await get_user_arena_rank(self.db, user_id, time_filter, class_id, exam_type)
        
        response = ArenaRankingResponse(
            users=users,
            total=total,
            skip=skip,
            limit=limit,
            current_user_rank=user_rank,
            current_user=ArenaRankingUserResponse(
                user_id=user_data[0].id,
                user_name=user_data[0].name,
                avatar_url=user_data[0].avatar_url,
                questions_solved=user_data[1],
            ) if user_data else None,
        )
        
        return response

    async def get_streak_ranking(
        self,
        skip: int = 0,
        limit: int = 20,
        class_id: Optional[UUID] = None,
        exam_type: Optional[str] = None,
    ) -> StreakRankingResponse:
        """
        Get streak ranking sorted by longest streak with pagination (cached).
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            class_id: Optional class ID to filter users by class
            exam_type: Optional target exam type to filter users by matching exam
        
        Returns:
            StreakRankingResponse with paginated users and their streak counts
        """
        # Create cache key based on all parameters
        exam_type_str = exam_type if exam_type else "none"
        class_id_str = str(class_id) if class_id else "none"
        cache_key = f"{self.CACHE_PREFIX}:streak_ranking:{class_id_str}:{exam_type_str}:{skip}:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                return StreakRankingResponse(**cached)
        
        results, total = await get_streak_ranking(
            self.db,
            skip=skip,
            limit=limit,
            class_id=class_id,
            exam_type=exam_type,
        )
        
        users = [
            StreakRankingUserResponse(
                user_id=user.id,
                user_name=user.name,
                avatar_url=user.avatar_url,
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
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_best_by_longest_streak(self) -> Optional[BestPerformerResponse]:
        """Get user with longest study streak (cached)"""
        cache_key = f"{self.CACHE_PREFIX}:best:streak"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
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
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_contest_ranking(
        self,
        filter_type: str = "best_rating_first",
        skip: int = 0,
        limit: int = 20,
        class_id: Optional[UUID] = None,
        exam_type: Optional[str] = None,
    ) -> ContestRankingResponse:
        """
        Get contest ranking from the most recent contest with filter options (cached).
        
        Args:
            filter_type: Filter type - "best_rating_first" or "best_delta_first"
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            class_id: Optional class ID to filter users by class
            exam_type: Optional target exam type to filter users by matching exam
        
        Returns:
            ContestRankingResponse with paginated users and their contest performance
        """
        # Create cache key based on all parameters
        exam_type_str = exam_type if exam_type else "none"
        class_id_str = str(class_id) if class_id else "none"
        cache_key = f"{self.CACHE_PREFIX}:contest_ranking:{filter_type}:{class_id_str}:{exam_type_str}:{skip}:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                return ContestRankingResponse(**cached)
        
        results, total = await get_contest_ranking_by_filter(
            self.db,
            filter_type=filter_type,
            skip=skip,
            limit=limit,
            class_id=class_id,
            exam_type=exam_type,
            redis_service=self.redis_service,
        )
        
        users = [
            ContestRankingUserResponse(
                user_id=user.id,
                user_name=user.name,
                avatar_url=user.avatar_url,
                score=leaderboard_entry.score,
                rank=leaderboard_entry.rank,
                rating_before=leaderboard_entry.rating_before,
                rating_after=leaderboard_entry.rating_after,
                rating_delta=leaderboard_entry.rating_delta,
                accuracy=leaderboard_entry.accuracy,
                attempted=leaderboard_entry.attempted,
                correct=leaderboard_entry.correct,
                incorrect=leaderboard_entry.incorrect,
            )
            for leaderboard_entry, user in results
        ]
        
        response = ContestRankingResponse(
            users=users,
            total=total,
            skip=skip,
            limit=limit,
        )
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.CACHE_LEADER_TTL
            )
        
        return response

    async def get_contest_ranking_by_contest_id(
        self,
        contest_id: UUID,
        filter_type: str = "best_rating_first",
        skip: int = 0,
        limit: int = 20,
    ) -> ContestRankingResponse:
        """
        Get contest ranking for a specific contest by contest_id with filter options.
        
        Args:
            contest_id: Contest ID to get ranking for
            filter_type: Filter type - "best_rating_first" or "best_delta_first"
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
        
        Returns:
            ContestRankingResponse with paginated users and their contest performance
        """
        results, total = await get_contest_ranking_by_contest_id(
            self.db,
            contest_id=contest_id,
            filter_type=filter_type,
            skip=skip,
            limit=limit,
        )
        
        users = [
            ContestRankingUserResponse(
                user_id=user.id,
                user_name=user.name,
                avatar_url=user.avatar_url,
                score=leaderboard_entry.score,
                rank=leaderboard_entry.rank,
                rating_before=leaderboard_entry.rating_before,
                rating_after=leaderboard_entry.rating_after,
                rating_delta=leaderboard_entry.rating_delta,
                accuracy=leaderboard_entry.accuracy,
                attempted=leaderboard_entry.attempted,
                correct=leaderboard_entry.correct,
                incorrect=leaderboard_entry.incorrect,
            )
            for leaderboard_entry, user in results
        ]
        
        return ContestRankingResponse(
            users=users,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_rating_ranking(
        self,
        skip: int = 0,
        limit: int = 20,
        class_id: Optional[UUID] = None,
        exam_type: Optional[str] = None,
    ) -> RatingRankingResponse:
        """
        Get rating ranking filtered by class_id and exam_type (cached).
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            class_id: Optional class ID to filter users by class
            exam_type: Optional target exam type to filter users by matching exam
        
        Returns:
            RatingRankingResponse with paginated users and their rating information
        """
        # Create cache key based on class_id, exam_type, skip, and limit
        exam_type_str = exam_type if exam_type else "none"
        class_id_str = str(class_id) if class_id else "none"
        cache_key = f"{self.CACHE_PREFIX}:rating_ranking:{class_id_str}:{exam_type_str}:{skip}:{limit}"
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                return RatingRankingResponse(**cached)
        
        results, total = await get_rating_ranking_by_filter(
            self.db,
            skip=skip,
            limit=limit,
            class_id=class_id,
            exam_type=exam_type,
        )
        
        users = [
            RatingRankingUserResponse(
                user_id=user.id,
                user_name=user.name,
                avatar_url=user.avatar_url,
                current_rating=user.current_rating,
                max_rating=user.max_rating,
                title=user.title.value if user.title else None,
            )
            for user in results
        ]
        
        response = RatingRankingResponse(
            users=users,
            total=total,
            skip=skip,
            limit=limit,
        )
        
        # Cache result
        if self.redis_service:
            await self.redis_service.set_value(
                cache_key,
                response.model_dump(mode='json'),
                expire=settings.LONG_TERM_CACHE_TTL
            )
        
        return response

