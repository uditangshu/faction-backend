"""Question Attempt endpoints"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.api.v1.dependencies import AttemptServiceDep, CurrentUser
from app.models.attempt import QuestionAttempt
from app.schemas.question import (
    AttemptCreateRequest,
    AttemptResponse,
    AttemptUpdateRequest,
    AttemptListResponse,
    AttemptStatsResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/attempts", tags=["Attempts"])


@router.post("/", response_model=AttemptResponse, status_code=201)
async def create_attempt(
    attempt_service: AttemptServiceDep,
    current_user: CurrentUser,
    request: AttemptCreateRequest,
) -> AttemptResponse:
    """Record a new question attempt (streak is updated automatically if answer is correct)"""
    try:
        attempt = await attempt_service.create_attempt(
            user_id=current_user.id,
            question_id=request.question_id,
            user_answer=request.user_answer,
            is_correct=request.is_correct,
            marks_obtained=request.marks_obtained,
            time_taken=request.time_taken,
            hint_used=request.hint_used,
        )
        return AttemptResponse(
            id=attempt.id,
            user_id=attempt.user_id,
            question_id=attempt.question_id,
            user_answer=attempt.user_answer,
            is_correct=attempt.is_correct,
            marks_obtained=attempt.marks_obtained,
            time_taken=attempt.time_taken,
            attempted_at=str(attempt.attempted_at),
            explanation_viewed=attempt.explanation_viewed,
            hint_used=attempt.hint_used,
        )
    except Exception as e:
        raise BadRequestException(f"Failed to create attempt: {str(e)}")


@router.get("/", response_model=AttemptListResponse)
async def get_my_attempts(
    attempt_service: AttemptServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> AttemptListResponse:
    """Get all attempts for the current user with pagination"""
    attempts, total = await attempt_service.get_user_attempts(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return AttemptListResponse(
        attempts=[
            AttemptResponse(
                id=a.id,
                user_id=a.user_id,
                question_id=a.question_id,
                user_answer=a.user_answer,
                is_correct=a.is_correct,
                marks_obtained=a.marks_obtained,
                time_taken=a.time_taken,
                attempted_at=str(a.attempted_at),
                explanation_viewed=a.explanation_viewed,
                hint_used=a.hint_used,
            )
            for a in attempts
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=AttemptStatsResponse)
async def get_my_stats(
    attempt_service: AttemptServiceDep,
    current_user: CurrentUser,
) -> AttemptStatsResponse:
    """Get attempt statistics for the current user"""
    stats = await attempt_service.get_user_stats(current_user.id)
    return AttemptStatsResponse(**stats)


@router.get("/user/{user_id}/solved-count")
async def get_user_solved_count(
    user_id: UUID,
    attempt_service: AttemptServiceDep
) -> dict:
    """Get total number of distinct questions solved by a user"""
    result = await attempt_service.get_user_solved_count(user_id=user_id)
    return result


@router.get("/{attempt_id}", response_model=AttemptResponse)
async def get_attempt(
    attempt_service: AttemptServiceDep,
    current_user: CurrentUser,
    attempt_id: UUID,
) -> AttemptResponse:
    """Get a specific attempt by ID"""
    attempt = await attempt_service.get_attempt_by_id(attempt_id)
    if not attempt:
        raise NotFoundException(f"Attempt with ID {attempt_id} not found")
    
    # Ensure user owns this attempt
    if attempt.user_id != current_user.id:
        raise NotFoundException(f"Attempt with ID {attempt_id} not found")
    
    return AttemptResponse(
        id=attempt.id,
        user_id=attempt.user_id,
        question_id=attempt.question_id,
        user_answer=attempt.user_answer,
        is_correct=attempt.is_correct,
        marks_obtained=attempt.marks_obtained,
        time_taken=attempt.time_taken,
        attempted_at=str(attempt.attempted_at),
        explanation_viewed=attempt.explanation_viewed,
        hint_used=attempt.hint_used,
    )


@router.get("/question/{question_id}", response_model=AttemptResponse)
async def get_attempt_for_question(
    attempt_service: AttemptServiceDep,
    current_user: CurrentUser,
    question_id: UUID,
) -> AttemptResponse:
    """Get the latest attempt for a specific question"""
    attempt = await attempt_service.get_latest_attempt(
        user_id=current_user.id,
        question_id=question_id,
    )
    if not attempt:
        raise NotFoundException(f"No attempt found for question {question_id}")
    
    return AttemptResponse(
        id=attempt.id,
        user_id=attempt.user_id,
        question_id=attempt.question_id,
        user_answer=attempt.user_answer,
        is_correct=attempt.is_correct,
        marks_obtained=attempt.marks_obtained,
        time_taken=attempt.time_taken,
        attempted_at=str(attempt.attempted_at),
        explanation_viewed=attempt.explanation_viewed,
        hint_used=attempt.hint_used,
    )


@router.get("/question/{question_id}/status")
async def check_attempt_status(
    attempt_service: AttemptServiceDep,
    current_user: CurrentUser,
    question_id: UUID,
) -> dict:
    """Check if the current user has attempted a specific question"""
    has_attempted = await attempt_service.has_attempted(
        user_id=current_user.id,
        question_id=question_id,
    )
    return {"has_attempted": has_attempted, "question_id": str(question_id)}


@router.patch("/{attempt_id}", response_model=AttemptResponse)
async def update_attempt(
    attempt_service: AttemptServiceDep,
    current_user: CurrentUser,
    attempt_id: UUID,
    request: AttemptUpdateRequest,
) -> AttemptResponse:
    """Update an attempt (mark explanation as viewed, etc.)"""
    # First check if attempt exists and belongs to user
    existing = await attempt_service.get_attempt_by_id(attempt_id)
    if not existing:
        raise NotFoundException(f"Attempt with ID {attempt_id} not found")
    
    if existing.user_id != current_user.id:
        raise NotFoundException(f"Attempt with ID {attempt_id} not found")
    
    attempt = await attempt_service.update_attempt(
        attempt_id=attempt_id,
        explanation_viewed=request.explanation_viewed,
        hint_used=request.hint_used,
    )
    
    if not attempt:
        raise NotFoundException(f"Attempt with ID {attempt_id} not found")
    
    return AttemptResponse(
        id=attempt.id,
        user_id=attempt.user_id,
        question_id=attempt.question_id,
        user_answer=attempt.user_answer,
        is_correct=attempt.is_correct,
        marks_obtained=attempt.marks_obtained,
        time_taken=attempt.time_taken,
        attempted_at=str(attempt.attempted_at),
        explanation_viewed=attempt.explanation_viewed,
        hint_used=attempt.hint_used,
    )


@router.delete("/{attempt_id}", status_code=204)
async def delete_attempt(
    attempt_service: AttemptServiceDep,
    current_user: CurrentUser,
    attempt_id: UUID,
) -> None:
    """Delete an attempt by ID"""
    # First check if attempt exists and belongs to user
    existing = await attempt_service.get_attempt_by_id(attempt_id)
    if not existing:
        raise NotFoundException(f"Attempt with ID {attempt_id} not found")
    
    if existing.user_id != current_user.id:
        raise NotFoundException(f"Attempt with ID {attempt_id} not found")
    
    deleted = await attempt_service.delete_attempt(attempt_id)
    if not deleted:
        raise NotFoundException(f"Attempt with ID {attempt_id} not found")

