"""Question endpoints"""

import re
import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query, Form, File, UploadFile

from app.api.v1.dependencies import QuestionServiceDep, CurrentUser
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
from app.integrations.cloudinary_client import upload_image, delete_image
from app.models.Basequestion import QuestionType, DifficultyLevel
from app.models.user import TargetExam

router = APIRouter(prefix="/questions", tags=["Questions"])


def extract_cloudinary_public_id(image_url: str) -> Optional[str]:
    """
    Extract public_id from Cloudinary URL.
    URL format: https://res.cloudinary.com/{cloud_name}/image/upload/{folder}/{public_id}.{format}
    Returns: {folder}/{public_id} (without extension)
    """
    if not image_url:
        return None
    
    # Pattern to match Cloudinary URL structure
    pattern = r'/(?:v\d+/)?([^/]+/[^/]+)\.(jpg|jpeg|png|gif|webp|svg)'
    match = re.search(pattern, image_url)
    
    if match:
        return match.group(1)
    return None


@router.post("/", response_model=QuestionDetailedResponse, status_code=201)
async def create_question(
    question_service: QuestionServiceDep,
    topic_id: UUID = Form(...),
    type: QuestionType = Form(...),
    difficulty: DifficultyLevel = Form(...),
    exam_type: str = Form(..., description="JSON array of target exams"),
    question_text: str = Form(...),
    marks: int = Form(...),
    solution_text: str = Form(...),
    question_image: Optional[UploadFile] = File(None, description="Question image file"),
    integer_answer: Optional[int] = Form(None),
    mcq_options: Optional[str] = Form(None, description="JSON array of MCQ options"),
    mcq_correct_option: Optional[str] = Form(None, description="JSON array of correct option indices"),
    scq_options: Optional[str] = Form(None, description="JSON array of SCQ options"),
    scq_correct_options: Optional[int] = Form(None),
) -> QuestionDetailedResponse:
    """Create a new question with optional image upload to Cloudinary"""
    try:        
        # Handle image upload if provided
        image_url = None
        if question_image:
            # Validate file type
            if not question_image.content_type or not question_image.content_type.startswith('image/'):
                raise BadRequestException("File must be an image")
            
            # Upload image to Cloudinary
            try:
                image_url = await upload_image(
                    question_image.file,
                    folder="questions",
                    public_id=None  # Let Cloudinary generate the ID
                )
            except Exception as e:
                raise BadRequestException(f"Failed to upload image: {str(e)}")
        
        new_question = await question_service.create_question(
            topic_id=topic_id,
            type=type,
            difficulty=difficulty,
            exam_type=exam_type_list,
            question_text=question_text,
            marks=marks,
            solution_text=solution_text,
            question_image=image_url,
            integer_answer=integer_answer,
            mcq_options=mcq_options_list,
            mcq_correct_option=mcq_correct_option_list,
            scq_options=scq_options_list,
            scq_correct_options=scq_correct_options,
        )
        return QuestionDetailedResponse.model_validate(new_question)
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create question: {str(e)}")


@router.get("/", response_model=QuestionPaginatedResponse)
async def get_questions(
    question_service: QuestionServiceDep,
    topic_id: Optional[UUID] = Query(None, description="Filter by topic ID"),
    chapter_id: Optional[UUID] = Query(None, description="Filter by chapter ID"),
    subject_id: Optional[UUID] = Query(None, description="Filter by subject ID"),
    difficulty: Optional[int] = Query(None, ge=1, le=5, description="Filter by difficulty level (1-5)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> QuestionPaginatedResponse:
    """Get all questions with optional filters and pagination"""
    questions, total = await question_service.get_questions(
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
    current_user: CurrentUser,
) -> QOTDResponse:
    """Get Question of the Day: 3 random questions from 3 different subjects from the user's class"""
    questions_with_subjects = await question_service.get_qotd_questions(class_id=current_user.class_id)
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
    question_id: UUID,
) -> QuestionDetailedResponse:
    """Get a question by ID"""
    question = await question_service.get_question_by_id(question_id)
    if not question:
        raise NotFoundException(f"Question with ID {question_id} not found")
    return QuestionDetailedResponse.model_validate(question)


@router.put("/{question_id}", response_model=QuestionDetailedResponse)
async def update_question(
    question_service: QuestionServiceDep,
    question_id: UUID,
    request: QuestionUpdateRequest,
) -> QuestionDetailedResponse:
    """Update an existing question"""
    updated_question = await question_service.update_question(
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
    question_id: UUID,
) -> None:
    """Delete a question by ID and delete image from Cloudinary if exists"""
    # Get question first to check for image
    question = await question_service.get_question_by_id(question_id)
    if not question:
        raise NotFoundException(f"Question with ID {question_id} not found")
    
    # Delete image from Cloudinary if exists
    if question.question_image:
        try:
            public_id = extract_cloudinary_public_id(question.question_image)
            if public_id:
                await delete_image(public_id)
        except Exception:
            # Log but don't fail if deletion fails (image might not exist)
            pass
    
    deleted = await question_service.delete_question(question_id)
    if not deleted:
        raise NotFoundException(f"Question with ID {question_id} not found")
