"""Weak topic endpoints"""

from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import WeakTopicServiceDep, CurrentUser
from app.schemas.weak_topic import WeakTopicResponse, WeakTopicListResponse

router = APIRouter(prefix="/weak-topics", tags=["Weak Topics"])


@router.get("/", response_model=WeakTopicListResponse)
async def get_weak_topics(
    weak_topic_service: WeakTopicServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    min_weakness_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum weakness score to filter"),
) -> WeakTopicListResponse:
    """Get weak topics for the current user"""
    await weak_topic_service.update_weak_topics_from_attempts(current_user.id)
    
    weak_topics, total = await weak_topic_service.get_user_weak_topics(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        min_weakness_score=min_weakness_score,
    )
    
    return WeakTopicListResponse(
        weak_topics=[
            WeakTopicResponse(
                id=wt.id,
                user_id=wt.user_id,
                topic_id=wt.topic_id,
                total_attempt=wt.total_attempt,
                incorrect_attempts=wt.incorrect_attempts,
                correct_attempts=wt.correct_attempts,
                weakness_score=wt.weakness_score,
                last_updated=wt.last_updated,
            )
            for wt in weak_topics
        ],
        total=total,
        skip=skip,
        limit=limit,
    )

