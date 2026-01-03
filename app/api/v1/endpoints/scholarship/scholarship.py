"""Scholarship Test endpoints"""

from uuid import UUID
from fastapi import APIRouter, HTTPException

from app.api.v1.dependencies import CurrentUser, ScholarshipServiceDep
from app.schemas.scholarship import (
    ScholarshipTestCreateRequest,
    ScholarshipTestCreateResponse,
    ScholarshipQuestionResponse,
    ScholarshipSubmitRequest,
    ScholarshipResultResponse,
)
from app.exceptions.http_exceptions import BadRequestException, NotFoundException

router = APIRouter(prefix="/scholarship", tags=["Scholarship"])


@router.post("/create-scholarship-test", response_model=ScholarshipTestCreateResponse, status_code=201)
async def create_scholarship_test(
    scholarship_service: ScholarshipServiceDep,
    current_user: CurrentUser,
    request: ScholarshipTestCreateRequest,
) -> ScholarshipTestCreateResponse:
    """
    Create a scholarship test.
    
    Generates 5 questions from 3 randomly selected subjects based on:
    - class_id: Class to filter subjects
    - exam_type: Exam type to filter subjects and questions
    
    Returns questions without answers (no solution_text, no correct options).
    """
    try:
        # Create scholarship test with questions
        scholarship, questions = await scholarship_service.create_scholarship_test(
            user_id=current_user.id,
            class_id=request.class_id,
            exam_type=request.exam_type,
        )
        
        # Build response - questions without answers
        question_responses = []
        total_marks = 0
        
        for question in questions:
            total_marks += question.marks
            question_responses.append(
                ScholarshipQuestionResponse(
                    id=question.id,
                    question_id=question.id,
                    topic_id=question.topic_id,
                    type=question.type,
                    difficulty=question.difficulty,
                    exam_type=question.exam_type,
                    question_text=question.question_text,
                    marks=question.marks,
                    question_image=question.question_image,
                    mcq_options=question.mcq_options,  # Options only, no correct_answer
                    scq_options=question.scq_options,  # Options only, no correct_answer
                    # Explicitly exclude: solution_text, mcq_correct_option, scq_correct_options, integer_answer
                )
            )
        
        return ScholarshipTestCreateResponse(
            id=scholarship.id,
            user_id=scholarship.user_id,
            class_id=scholarship.class_id,
            exam_type=scholarship.exam_type,
            status=scholarship.status.value,
            time_assigned=scholarship.time_assigned,
            created_at=scholarship.created_at.isoformat(),
            updated_at=scholarship.updated_at.isoformat(),
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
            detail=f"Failed to create scholarship test: {str(e)}"
        )


@router.get("/{scholarship_id}", response_model=ScholarshipTestCreateResponse)
async def get_scholarship_test(
    scholarship_service: ScholarshipServiceDep,
    current_user: CurrentUser,
    scholarship_id: UUID,
) -> ScholarshipTestCreateResponse:
    """
    Get a scholarship test by ID with all questions.
    
    Returns questions without answers (no solution_text, no correct options).
    """
    try:
        scholarship = await scholarship_service.get_scholarship_by_id(
            scholarship_id=scholarship_id,
            user_id=current_user.id,
        )
        
        if not scholarship:
            raise NotFoundException(f"Scholarship test with ID {scholarship_id} not found")
        
        # Extract questions from scholarship-question links
        questions = [sq.question for sq in scholarship.questions]
        
        # Build response - questions without answers
        question_responses = []
        total_marks = 0
        
        for question in questions:
            total_marks += question.marks
            question_responses.append(
                ScholarshipQuestionResponse(
                    id=question.id,
                    question_id=question.id,
                    topic_id=question.topic_id,
                    type=question.type,
                    difficulty=question.difficulty,
                    exam_type=question.exam_type,
                    question_text=question.question_text,
                    marks=question.marks,
                    question_image=question.question_image,
                    mcq_options=question.mcq_options,  # Options only, no correct_answer
                    scq_options=question.scq_options,  # Options only, no correct_answer
                    # Explicitly exclude: solution_text, mcq_correct_option, scq_correct_options, integer_answer
                )
            )
        
        return ScholarshipTestCreateResponse(
            id=scholarship.id,
            user_id=scholarship.user_id,
            class_id=scholarship.class_id,
            exam_type=scholarship.exam_type,
            status=scholarship.status.value,
            time_assigned=scholarship.time_assigned,
            created_at=scholarship.created_at.isoformat(),
            updated_at=scholarship.updated_at.isoformat(),
            questions=question_responses,
            total_questions=len(question_responses),
            total_marks=total_marks,
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scholarship test: {str(e)}"
        )


@router.post("/submit", response_model=ScholarshipResultResponse, status_code=200)
async def submit_scholarship_test(
    scholarship_service: ScholarshipServiceDep,
    current_user: CurrentUser,
    request: ScholarshipSubmitRequest,
) -> ScholarshipResultResponse:
    """
    Submit scholarship test with answers.
    
    Validates answers, calculates marks, and stores results in ScholarshipResult.
    """
    try:
        # Convert submissions to dict format
        submissions_data = [
            {
                "question_id": str(sub.question_id),
                "user_answer": sub.user_answer,
                "time_taken": sub.time_taken,
            }
            for sub in request.submissions
        ]
        
        # Submit scholarship test
        result = await scholarship_service.submit_scholarship_test(
            scholarship_id=request.scholarship_id,
            user_id=current_user.id,
            submissions_data=submissions_data,
        )
        
        return ScholarshipResultResponse(
            id=result.id,
            user_id=result.user_id,
            scholarship_id=result.scholarship_id,
            score=result.score,
            total_marks=result.total_marks,
            time_taken=result.time_taken,
            correct=result.correct,
            incorrect=result.incorrect,
            unattempted=result.unattempted,
            accuracy=result.accuracy,
            submitted_at=result.submitted_at.isoformat(),
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit scholarship test: {str(e)}"
        )


@router.get("/{scholarship_id}/result", response_model=ScholarshipResultResponse)
async def get_scholarship_result(
    scholarship_service: ScholarshipServiceDep,
    current_user: CurrentUser,
    scholarship_id: UUID,
) -> ScholarshipResultResponse:
    """
    Get scholarship test result by scholarship ID.
    
    Raises exception if scholarship ID does not exist for the user.
    """
    try:
        result = await scholarship_service.get_scholarship_result(
            scholarship_id=scholarship_id,
            user_id=current_user.id,
        )
        
        return ScholarshipResultResponse(
            id=result.id,
            user_id=result.user_id,
            scholarship_id=result.scholarship_id,
            score=result.score,
            total_marks=result.total_marks,
            time_taken=result.time_taken,
            correct=result.correct,
            incorrect=result.incorrect,
            unattempted=result.unattempted,
            accuracy=result.accuracy,
            submitted_at=result.submitted_at.isoformat(),
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scholarship result: {str(e)}"
        )

