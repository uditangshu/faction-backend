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
    get_arena_ranking_by_submissions,
    get_contest_ranking_by_filter,
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
)
from app.db.streak_calls import get_streak_ranking, get_user_with_longest_streak
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

    async def get_arena_ranking(
        self,
        time_filter: str = "all_time",
        skip: int = 0,
        limit: int = 20,
        class_id: Optional[UUID] = None,
        target_exams: Optional[List[str]] = None,
    ) -> ArenaRankingResponse:
        """
        Get arena ranking by maximum submissions solved with time filtering and pagination.
        
        Args:
            time_filter: Time filter - "daily", "weekly", or "all_time"
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            class_id: Optional class ID to filter users by class
            target_exams: Optional list of target exams to filter users by matching exams
        
        Returns:
            ArenaRankingResponse with paginated users and their solved counts
        """
        results, total = await get_arena_ranking_by_submissions(
            self.db,
            time_filter=time_filter,
            skip=skip,
            limit=limit,
            class_id=class_id,
            target_exams=target_exams,
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
        
        return ArenaRankingResponse(
            users=users,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_streak_ranking(
        self,
        skip: int = 0,
        limit: int = 20,
        class_id: Optional[UUID] = None,
        target_exams: Optional[List[str]] = None,
    ) -> StreakRankingResponse:
        """
        Get streak ranking sorted by longest streak with pagination.
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            class_id: Optional class ID to filter users by class
            target_exams: Optional list of target exams to filter users by matching exams
        
        Returns:
            StreakRankingResponse with paginated users and their streak counts
        """
        results, total = await get_streak_ranking(
            self.db,
            skip=skip,
            limit=limit,
            class_id=class_id,
            target_exams=target_exams,
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
        
        return StreakRankingResponse(
            users=users,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_best_by_longest_streak(self) -> Optional[BestPerformerResponse]:
        """Get user with longest study streak"""
        result = await get_user_with_longest_streak(self.db)
        if not result:
            return None
        
        user, longest_streak = result
        return BestPerformerResponse(
            user=UserProfileResponse.model_validate(user),
            metric_value=longest_streak,
            metric_type="longest_streak",
        )

    async def get_contest_ranking(
        self,
        filter_type: str = "best_rating_first",
        skip: int = 0,
        limit: int = 20,
        class_id: Optional[UUID] = None,
        target_exams: Optional[List[str]] = None,
    ) -> ContestRankingResponse:
        """
        Get contest ranking from the most recent contest with filter options.
        
        Args:
            filter_type: Filter type - "best_rating_first" or "best_delta_first"
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            class_id: Optional class ID to filter users by class
            target_exams: Optional list of target exams to filter users by matching exams
        
        Returns:
            ContestRankingResponse with paginated users and their contest performance
        """
        results, total = await get_contest_ranking_by_filter(
            self.db,
            filter_type=filter_type,
            skip=skip,
            limit=limit,
            class_id=class_id,
            target_exams=target_exams,
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

