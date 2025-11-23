"""Question endpoints"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Query
from app.api.v1.dependencies import CurrentUser, QuestionServiceDep, StreakServiceDep
from app.schemas.question import (
    QuestionListResponse,
    QuestionDetailResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    QuestionOptionResponse,
)

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get("", response_model=List[QuestionListResponse])
async def list_questions(
    question_service: QuestionServiceDep,
    current_user: CurrentUser,
    subject_id: UUID | None = Query(None),
    topic_id: UUID | None = Query(None),
    difficulty_level: int | None = Query(None, ge=1, le=5),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> List[QuestionListResponse]:
    """
    Get list of questions with filters.
    
    Query parameters:
    - subject_id: Filter by subject UUID
    - topic_id: Filter by topic UUID
    - difficulty_level: Filter by difficulty (1-5)
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    """
    questions = await question_service.get_questions(
        subject_id=subject_id,
        topic_id=topic_id,
        difficulty_level=difficulty_level,
        skip=skip,
        limit=limit,
    )
    
    return [QuestionListResponse.from_orm(q) for q in questions]


@router.get("/{question_id}", response_model=QuestionDetailResponse)
async def get_question(
    question_id: UUID,
    question_service: QuestionServiceDep,
    current_user: CurrentUser,
) -> QuestionDetailResponse:
    """
    Get question details with options.
    
    Returns question with all options (without correct answer info).
    """
    question = await question_service.get_question_by_id(question_id)
    options = await question_service.get_question_options(question_id)
    
    response = QuestionDetailResponse.from_orm(question)
    response.options = [QuestionOptionResponse.from_orm(opt) for opt in options]
    
    return response


@router.post("/{question_id}/submit", response_model=SubmitAnswerResponse)
async def submit_answer(
    question_id: UUID,
    request: SubmitAnswerRequest,
    question_service: QuestionServiceDep,
    streak_service: StreakServiceDep,
    current_user: CurrentUser,
) -> SubmitAnswerResponse:
    """
    Submit answer for a question.
    
    Evaluates the answer and updates user statistics and study streak.
    """
    result = await question_service.submit_answer(
        user_id=current_user.id,
        question_id=question_id,
        user_answer=request.user_answer,
        time_taken=request.time_taken,
    )
    
    # Update streak if answer is correct
    if result["is_correct"]:
        await streak_service.update_streak_on_correct_answer(current_user.id)
    
    return SubmitAnswerResponse(**result)

