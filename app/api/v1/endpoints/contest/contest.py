"""Contest endpoints"""

from uuid import UUID
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.v1.dependencies import DBSession, ContestServiceDep
from app.models.contest import ContestLeaderboard
from app.schemas.contest import (
    ContestLeaderboardResponse,
    ContestLeaderboardListResponse,
    ContestCreateRequest,
    ContestUpdateRequest,
    ContestResponse,
    ContestWithQuestionsResponse,
)
from app.schemas.question import QuestionDetailedResponse
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/contests", tags=["Contests"])


@router.post("/", response_model=ContestResponse, status_code=201)
async def create_contest(
    contest_service: ContestServiceDep,
    request: ContestCreateRequest,
) -> ContestResponse:
    """Create a new contest"""
    try:
        new_contest = await contest_service.create_contest(
            total_time=request.total_time,
            status=request.status,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
            question_ids=request.question_ids,
        )
        return ContestResponse.model_validate(new_contest)
    except Exception as e:
        raise BadRequestException(f"Failed to create contest: {str(e)}")


@router.put("/{contest_id}", response_model=ContestResponse)
async def update_contest(
    contest_service: ContestServiceDep,
    contest_id: UUID,
    request: ContestUpdateRequest,
) -> ContestResponse:
    """Update an existing contest"""
    updated_contest = await contest_service.update_contest(
        contest_id=contest_id,
        total_time=request.total_time,
        status=request.status,
        starts_at=request.starts_at,
        ends_at=request.ends_at,
    )
    
    if not updated_contest:
        raise NotFoundException(f"Contest with ID {contest_id} not found")
    
    return ContestResponse.model_validate(updated_contest)


@router.delete("/{contest_id}", status_code=204)
async def delete_contest(
    contest_service: ContestServiceDep,
    contest_id: UUID,
) -> None:
    """Delete a contest by ID"""
    deleted = await contest_service.delete_contest(contest_id)
    if not deleted:
        raise NotFoundException(f"Contest with ID {contest_id} not found")


@router.get("/{contest_id}", response_model=ContestWithQuestionsResponse)
async def get_contest_with_questions(
    contest_service: ContestServiceDep,
    contest_id: UUID,
) -> ContestWithQuestionsResponse:
    """Get a contest by ID with all linked questions and their details"""
    result = await contest_service.get_contest_with_questions(contest_id)
    
    if not result:
        raise NotFoundException(f"Contest with ID {contest_id} not found")
    
    contest, questions = result
    
    return ContestWithQuestionsResponse(
        id=contest.id,
        total_time=contest.total_time,
        status=contest.status,
        starts_at=contest.starts_at,
        ends_at=contest.ends_at,
        created_at=contest.created_at,
        questions=[QuestionDetailedResponse.model_validate(question) for question in questions],
    )
