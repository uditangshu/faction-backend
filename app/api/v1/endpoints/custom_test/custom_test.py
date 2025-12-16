"""Custom Test endpoints"""

from uuid import UUID
from fastapi import APIRouter, HTTPException

from app.api.v1.dependencies import DBSession, CurrentUser
from app.services.custom_test_service import CustomTestService
from app.schemas.custom_test import (
    CustomTestGenerateRequest,
    CustomTestGenerateResponse,
    CustomTestQuestionResponse,
)
from app.exceptions.http_exceptions import BadRequestException, NotFoundException

router = APIRouter(prefix="/custom-tests", tags=["Custom Tests"])


@router.post("/generate", response_model=CustomTestGenerateResponse, status_code=200)
async def generate_custom_test(
    db: DBSession,
    current_user: CurrentUser,
    request: CustomTestGenerateRequest,
) -> CustomTestGenerateResponse:
    """
    Generate a custom test with filtered questions.
    
    Filters questions based on:
    - exam_type: Target exam type (JEE_MAINS, JEE_ADVANCED, NEET, etc.)
    - subject_ids: List of subject UUIDs
    - chapter_ids: List of chapter UUIDs
    - number_of_questions: Number of questions to generate
    - pyq_only: If true, only PYQ questions; if false, all questions
    - weak_topics_only: If true, only questions from weak topics
    
    Returns randomly selected questions from the filtered pool.
    """
    try:
        service = CustomTestService(db)
        
        questions = await service.generate_custom_test_questions(
            user_id=current_user.id,
            exam_type=request.exam_type,
            subject_ids=request.subject_ids,
            chapter_ids=request.chapter_ids,
            number_of_questions=request.number_of_questions,
            pyq_only=request.pyq_only,
            weak_topics_only=request.weak_topics_only,
        )
        
        # Build response
        question_responses = []
        total_marks = 0
        
        for question in questions:
            total_marks += question.marks
            question_responses.append(
                CustomTestQuestionResponse(
                    id=question.id,  # Using question.id as id for response
                    question_id=question.id,
                    topic_id=question.topic_id,
                    type=question.type,
                    difficulty=question.difficulty,
                    exam_type=question.exam_type,
                    question_text=question.question_text,
                    marks=question.marks,
                    question_image=question.question_image,
                    mcq_options=question.mcq_options,
                    scq_options=question.scq_options,
                )
            )
        
        return CustomTestGenerateResponse(
            questions=question_responses,
            total_questions=len(question_responses),
            total_marks=total_marks,
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate custom test: {str(e)}"
        )

