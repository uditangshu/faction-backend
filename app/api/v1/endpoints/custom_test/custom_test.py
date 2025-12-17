"""Custom Test endpoints"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import CurrentUser, CustomTestServiceDep
from app.schemas.custom_test import (
    CustomTestGenerateRequest,
    CustomTestGenerateResponse,
    CustomTestQuestionResponse,
    CustomTestListPaginatedResponse,
    CustomTestListResponse,
    CustomTestDetailResponse,
)
from app.exceptions.http_exceptions import BadRequestException, NotFoundException

router = APIRouter(prefix="/custom-tests", tags=["Custom Tests"])


@router.post("/generate", response_model=CustomTestGenerateResponse, status_code=200)
async def generate_custom_test(
    custom_test_service: CustomTestServiceDep,
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
    - weakness_score: Optional minimum weakness score threshold (0-100). 
      Only used when weak_topics_only=True. If no weak topics match the threshold, 
      falls back to selecting from all topics in the requested chapters.
    
    Returns randomly selected questions from the filtered pool.
    """
    try:
        # Generate questions
        questions = await custom_test_service.generate_custom_test_questions(
            user_id=current_user.id,
            exam_type=request.exam_type,
            subject_ids=request.subject_ids,
            chapter_ids=request.chapter_ids,
            number_of_questions=request.number_of_questions,
            pyq_only=request.pyq_only,
            weak_topics_only=request.weak_topics_only,
            weakness_score=request.weakness_score,
        )
        
        # Create custom test in database
        question_ids = [q.id for q in questions]
        custom_test = await custom_test_service.create_custom_test(
            user_id=current_user.id,
            question_ids=question_ids,
            time_assigned=request.time_assigned,
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
            id=custom_test.id,
            user_id=custom_test.user_id,
            status=custom_test.status.value,
            time_assigned=custom_test.time_assigned,
            created_at=custom_test.created_at.isoformat(),
            updated_at=custom_test.updated_at.isoformat(),
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


@router.get("/", response_model=CustomTestListPaginatedResponse)
async def get_my_custom_tests(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> CustomTestListPaginatedResponse:
    """
    Get all custom tests for the current user with pagination.
    
    Returns a paginated list of custom tests with basic information.
    """
    try:
        tests, total = await custom_test_service.get_user_custom_tests(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
        
        # Get question count for each test
        test_responses = []
        for test in tests:
            question_count = await custom_test_service.get_test_question_count(test.id)
            
            test_responses.append(
                CustomTestListResponse(
                    id=test.id,
                    user_id=test.user_id,
                    status=test.status.value,
                    time_assigned=test.time_assigned,
                    created_at=test.created_at.isoformat(),
                    updated_at=test.updated_at.isoformat(),
                    question_count=question_count,
                )
            )
        
        return CustomTestListPaginatedResponse(
            tests=test_responses,
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch custom tests: {str(e)}"
        )


@router.get("/{test_id}", response_model=CustomTestDetailResponse)
async def get_custom_test_detail(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    test_id: UUID,
) -> CustomTestDetailResponse:
    """
    Get a specific custom test by ID with all question details.
    
    Returns the full custom test with all questions and their details.
    """
    try:
        test = await custom_test_service.get_custom_test_by_id(
            test_id=test_id,
            user_id=current_user.id,
        )
        
        if not test:
            raise NotFoundException(f"Custom test with ID {test_id} not found")
        
        # Build question responses
        question_responses = []
        total_marks = 0
        
        for test_question in test.questions:
            q = test_question.question
            total_marks += q.marks
            question_responses.append(
                CustomTestQuestionResponse(
                    id=test_question.id,
                    question_id=q.id,
                    topic_id=q.topic_id,
                    type=q.type,
                    difficulty=q.difficulty,
                    exam_type=q.exam_type,
                    question_text=q.question_text,
                    marks=q.marks,
                    question_image=q.question_image,
                    mcq_options=q.mcq_options,
                    scq_options=q.scq_options,
                )
            )
        
        return CustomTestDetailResponse(
            id=test.id,
            user_id=test.user_id,
            status=test.status.value,
            time_assigned=test.time_assigned,
            created_at=test.created_at.isoformat(),
            updated_at=test.updated_at.isoformat(),
            questions=question_responses,
            total_questions=len(question_responses),
            total_marks=total_marks,
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch custom test: {str(e)}"
        )

