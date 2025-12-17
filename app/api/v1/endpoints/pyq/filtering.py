"""Filter PYQ endpoints"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import FilteringServiceDep, CurrentUser
from app.schemas.filters import (
    QuestionAppearance,
    QuestionResponse,
    QuestionFilteredListResponse,
)
from app.models.Basequestion import DifficultyLevel
from app.exceptions.http_exceptions import BadRequestException

router = APIRouter(prefix="/question/filter", tags=["Filter Questions"])


@router.get("/", response_model=QuestionFilteredListResponse)
async def get_filtered_pyqs(
    filtering_service: FilteringServiceDep,
    current_user: CurrentUser,
    subject_ids: Optional[List[UUID]] = Query(None, description="Filter by subject IDs (comma-separated)"),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level"),
    year_filter: Optional[List[int]] = Query(None, description="Filter by years (e.g., 2023,2022,2021)"),
    question_appearance: QuestionAppearance = Query(
        QuestionAppearance.BOTH, 
        description="Filter by question appearance: pyq_only, non_pyq_only, or both"
    ),
    cursor: Optional[UUID] = Query(None, description="Cursor for infinite scrolling (question ID from previous response)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> QuestionFilteredListResponse:
    """
    Get filtered questions with various filters. Supports infinite scrolling.
    
    Filters:
    - subject_ids: Filter by list of subject IDs
    - chapter_ids: Filter by list of chapter IDs
    - difficulty: Filter by difficulty level (EASY, MEDIUM, HARD, EXPERT, MASTER)
    - year_filter: Filter by years (only applies to PYQ questions)
    - question_appearance: Filter by PYQ_ONLY, NON_PYQ_ONLY, or BOTH
    - cursor: For infinite scrolling - use the cursor from previous response to get next page
    - limit: Number of records to return
    
    Returns questions with optional PYQ information and supports infinite scrolling via cursor.
    """
    try:
        questions, total, next_cursor, has_more = await filtering_service.get_filtered_pyqs(
            user_id=current_user.id,
            subject_ids=subject_ids,
            chapter_ids=chapter_ids,
            difficulty=difficulty,
            year_filter=year_filter,
            question_appearance=question_appearance,
            cursor=cursor,
            limit=limit,
        )
        
        return QuestionFilteredListResponse(
            questions=[QuestionResponse(**q) for q in questions],
            total=total,
            cursor=next_cursor,
            has_more=has_more,
        )
    except Exception as e:
        raise BadRequestException(f"Failed to filter questions: {str(e)}")


# Note: The following endpoints have been replaced by the main filtering endpoint above
# which supports all filtering options including difficulty, question type, and more.
# Use the main endpoint with appropriate filters instead.


@router.get("/stats")
async def get_pyq_stats(
    filtering_service: FilteringServiceDep,
    current_user: CurrentUser,
) -> dict:
    """Get PYQ statistics for the current user"""
    return await filtering_service.get_pyq_stats(current_user.id)
