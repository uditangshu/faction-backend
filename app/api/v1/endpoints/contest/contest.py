"""Contest endpoints"""

from uuid import UUID
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.v1.dependencies import DBSession
from app.models.contest import ContestLeaderboard
from app.schemas.contest import (
    ContestLeaderboardResponse,
    ContestLeaderboardListResponse,
)

router = APIRouter(prefix="/contests", tags=["Contests"])


@router.get("/leaderboard/user/{user_id}", response_model=ContestLeaderboardListResponse)
async def get_user_contest_leaderboards(
    user_id: UUID,
    db: DBSession,
) -> ContestLeaderboardListResponse:
    """
    Get all contest leaderboard entries for a specific user.
    Returns all contests the user has participated in with their scores, ranks, and rating changes.
    """
    result = await db.execute(
        select(ContestLeaderboard)
        .where(ContestLeaderboard.user_id == user_id)
        .order_by(desc(ContestLeaderboard.score), desc(ContestLeaderboard.rank))
    )
    entries = list(result.scalars().all())
    
    return ContestLeaderboardListResponse(
        leaderboard_entries=[
            ContestLeaderboardResponse.model_validate(entry)
            for entry in entries
        ],
        total=len(entries),
    )

