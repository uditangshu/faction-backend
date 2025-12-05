"""Filter PYQ endpoints"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import FilteringServiceDep, CurrentUser
from app.schemas.filters import (
    YearWiseSorting,
    PYQQuestionResponse,
    PYQFilteredListResponse,
)
from app.models.Basequestion import DifficultyLevel, QuestionType
from app.exceptions.http_exceptions import BadRequestException

router = APIRouter(prefix="/pyq/filter", tags=["Filter Previous Year Questions"])


@router.get("/", response_model=PYQFilteredListResponse)
async def get_filtered_pyqs(
    filtering_service: FilteringServiceDep,
    current_user: CurrentUser,
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level"),
    question_type: Optional[QuestionType] = Query(None, description="Filter by question type"),
    year_wise_sorting: Optional[YearWiseSorting] = Query(None, description="Sort by year (ascending/descending)"),
    last_practiced_first: bool = Query(False, description="Sort by last practiced date (most recent first)"),
    exam_filter: Optional[List[str]] = Query(None, description="Filter by exam name (comma-separated for multiple)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> PYQFilteredListResponse:
    """
    Get filtered PYQ questions with various filters.
    
    Filters:
    - difficulty: Filter by difficulty level (EASY, MEDIUM, HARD, EXPERT, MASTER)
    - question_type: Filter by question type (INTEGER, MCQ, MATCH, SCQ)
    - year_wise_sorting: Sort by PYQ creation date (ascending/descending)
    - last_practiced_first: Sort by user's last practiced date
    - exam_filter: Filter by exam names (comma-separated, e.g., "JEE 2023,JEE 2022")
    """
    try:
        # Parse exam filter if provided
        
        questions, total = await filtering_service.get_filtered_pyqs(
            user_id=current_user.id,
            difficulty=difficulty,
            question_type=question_type,
            year_wise_sorting=year_wise_sorting,
            last_practiced_first=last_practiced_first,
            exam_filter=exam_filter,
            skip=skip,
            limit=limit,
        )
        
        return PYQFilteredListResponse(
            questions=[PYQQuestionResponse(**q) for q in questions],
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        raise BadRequestException(f"Failed to filter PYQs: {str(e)}")


@router.get("/by-difficulty/{difficulty}", response_model=PYQFilteredListResponse)
async def get_pyqs_by_difficulty(
    filtering_service: FilteringServiceDep,
    difficulty: DifficultyLevel,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> PYQFilteredListResponse:
    """Get PYQs filtered by difficulty level"""
    questions, total = await filtering_service.get_pyqs_by_difficulty(
        difficulty=difficulty,
        skip=skip,
        limit=limit,
    )
    return PYQFilteredListResponse(
        questions=[PYQQuestionResponse(**q) for q in questions],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/by-type/{question_type}", response_model=PYQFilteredListResponse)
async def get_pyqs_by_question_type(
    filtering_service: FilteringServiceDep,
    question_type: QuestionType,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> PYQFilteredListResponse:
    """Get PYQs filtered by question type"""
    questions, total = await filtering_service.get_pyqs_by_question_type(
        question_type=question_type,
        skip=skip,
        limit=limit,
    )
    return PYQFilteredListResponse(
        questions=[PYQQuestionResponse(**q) for q in questions],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/practiced", response_model=PYQFilteredListResponse)
async def get_practiced_pyqs(
    filtering_service: FilteringServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> PYQFilteredListResponse:
    """Get PYQs that the current user has practiced, sorted by last practiced date"""
    questions, total = await filtering_service.get_user_practiced_pyqs(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return PYQFilteredListResponse(
        questions=[PYQQuestionResponse(**q) for q in questions],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats")
async def get_pyq_stats(
    filtering_service: FilteringServiceDep,
    current_user: CurrentUser,
) -> dict:
    """Get PYQ statistics for the current user"""
    return await filtering_service.get_pyq_stats(current_user.id)
