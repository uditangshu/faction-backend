"""Question endpoints"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import QuestionServiceDep, DBSession, ReadOnlyDBSession
from app.schemas.question import (
    QuestionCreateRequest,
    QuestionUpdateRequest,
    QuestionResponse,
    QuestionDetailedResponse,
    QuestionPaginatedResponse,
    QOTDResponse,
    QOTDQuestionResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post("/", response_model=QuestionDetailedResponse, status_code=201)
async def create_question(
    question_service: QuestionServiceDep,
    db: DBSession,
    request: QuestionCreateRequest,
) -> QuestionDetailedResponse:
    """Create a new question"""
    try:
        print(request)
        new_question = await question_service.create_question(
            db,
            topic_id=request.topic_id,
            type=request.type,
            difficulty=request.difficulty,
            exam_type=request.exam_type,
            question_text=request.question_text,
            marks=request.marks,
            solution_text=request.solution_text,
            question_image=request.question_image,
            integer_answer=request.integer_answer,
            mcq_options=request.mcq_options,
            mcq_correct_option=request.mcq_correct_option,
            scq_options=request.scq_options,
            scq_correct_options=request.scq_correct_options,
        )
        return QuestionDetailedResponse.model_validate(new_question)
    except Exception as e:
        raise BadRequestException(f"Failed to create question: {str(e)}")


@router.get("/", response_model=QuestionPaginatedResponse)
async def get_questions(
    question_service: QuestionServiceDep,
    db: ReadOnlyDBSession,
    topic_id: Optional[UUID] = Query(None, description="Filter by topic ID"),
    chapter_id: Optional[UUID] = Query(None, description="Filter by chapter ID"),
    subject_id: Optional[UUID] = Query(None, description="Filter by subject ID"),
    difficulty: Optional[int] = Query(None, ge=1, le=5, description="Filter by difficulty level (1-5)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> QuestionPaginatedResponse:
    """Get all questions with optional filters and pagination"""
    questions, total = await question_service.get_questions(
        db,
        topic_id=topic_id,
        chapter_id=chapter_id,
        subject_id=subject_id,
        difficulty_level=difficulty,
        skip=skip,
        limit=limit,
    )
    
    return QuestionPaginatedResponse(
        questions=[QuestionResponse.model_validate(q) for q in questions],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/qotd", response_model=QOTDResponse)
async def get_qotd(
    question_service: QuestionServiceDep,
    db: ReadOnlyDBSession,
) -> QOTDResponse:
    """Get Question of the Day: 3 random questions from 3 different subjects"""
    questions_with_subjects = await question_service.get_qotd_questions(db)
    questions = [
        QOTDQuestionResponse(
            **QuestionDetailedResponse.model_validate(question).model_dump(),
            subject_name=subject_name
        )
        for question, subject_name in questions_with_subjects
    ]
    return QOTDResponse(questions=questions)


@router.get("/{question_id}", response_model=QuestionDetailedResponse)
async def get_question(
    question_service: QuestionServiceDep,
    db: ReadOnlyDBSession,
    question_id: UUID,
) -> QuestionDetailedResponse:
    """Get a question by ID"""
    question = await question_service.get_question_by_id(db, question_id)
    if not question:
        raise NotFoundException(f"Question with ID {question_id} not found")
    return QuestionDetailedResponse.model_validate(question)


@router.put("/{question_id}", response_model=QuestionDetailedResponse)
async def update_question(
    question_service: QuestionServiceDep,
    db: DBSession,
    question_id: UUID,
    request: QuestionUpdateRequest,
) -> QuestionDetailedResponse:
    """Update an existing question"""
    updated_question = await question_service.update_question(
        db,
        question_id=question_id,
        topic_id=request.topic_id,
        type=request.type,
        difficulty=request.difficulty,
        exam_type=request.exam_type,
        question_text=request.question_text,
        marks=request.marks,
        solution_text=request.solution_text,
        question_image=request.question_image,
        integer_answer=request.integer_answer,
        mcq_options=request.mcq_options,
        mcq_correct_option=request.mcq_correct_option,
        scq_options=request.scq_options,
        scq_correct_options=request.scq_correct_options,
    )
    
    if not updated_question:
        raise NotFoundException(f"Question with ID {question_id} not found")
    
    return QuestionDetailedResponse.model_validate(updated_question)


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_service: QuestionServiceDep,
    db: DBSession,
    question_id: UUID,
) -> None:
    """Delete a question by ID"""
    deleted = await question_service.delete_question(db, question_id)
    if not deleted:
        raise NotFoundException(f"Question with ID {question_id} not found")
