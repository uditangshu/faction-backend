"""Topic endpoints"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import TopicServiceDep
from app.schemas.question import (
    TopicCreateRequest,
    TopicResponse,
    TopicListResponse,
    TopicWithQuestionsResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.post("/", response_model=TopicResponse, status_code=201)
async def create_topic(
    topic_service: TopicServiceDep,
    request: TopicCreateRequest,
) -> TopicResponse:
    """Create a new topic"""
    try:
        new_topic = await topic_service.create_topic(
            name=request.name,
            chapter_id=request.chapter_id,
        )
        return TopicResponse.model_validate(new_topic)
    except Exception as e:
        raise BadRequestException(f"Failed to create topic: {str(e)}")


@router.get("/", response_model=TopicListResponse)
async def get_all_topics(
    topic_service: TopicServiceDep,
    chapter_id: Optional[UUID] = Query(None, description="Filter topics by chapter ID"),
) -> TopicListResponse:
    """Get all topics, optionally filtered by chapter ID"""
    if chapter_id:
        topics = await topic_service.get_topics_by_chapter(chapter_id)
    else:
        topics = await topic_service.get_all_topics()
    
    return TopicListResponse(
        topics=[TopicResponse.model_validate(t) for t in topics],
        total=len(topics)
    )


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_service: TopicServiceDep,
    topic_id: UUID,
) -> TopicResponse:
    """Get a topic by ID"""
    result = await topic_service.get_topic_by_id(topic_id)
    if not result:
        raise NotFoundException(f"Topic with ID {topic_id} not found")
    return TopicResponse.model_validate(result)


@router.get("/{topic_id}/questions", response_model=TopicWithQuestionsResponse)
async def get_topic_with_questions(
    topic_service: TopicServiceDep,
    topic_id: UUID,
) -> TopicWithQuestionsResponse:
    """Get a topic with all its questions"""
    result = await topic_service.get_topic_with_questions(topic_id)
    if not result:
        raise NotFoundException(f"Topic with ID {topic_id} not found")
    return TopicWithQuestionsResponse.model_validate(result)


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_service: TopicServiceDep,
    topic_id: UUID,
    request: TopicCreateRequest,
) -> TopicResponse:
    """Update a topic"""
    updated_topic = await topic_service.update_topic(
        topic_id=topic_id,
        name=request.name,
        chapter_id=request.chapter_id,
    )
    if not updated_topic:
        raise NotFoundException(f"Topic with ID {topic_id} not found")
    return TopicResponse.model_validate(updated_topic)


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(
    topic_service: TopicServiceDep,
    topic_id: UUID,
) -> None:
    """Delete a topic by ID"""
    deleted = await topic_service.delete_topic(topic_id)
    if not deleted:
        raise NotFoundException(f"Topic with ID {topic_id} not found")

