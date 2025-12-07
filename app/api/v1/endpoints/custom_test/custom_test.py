"""Custom Test endpoints"""

from uuid import UUID
from fastapi import APIRouter, Query
from typing import Optional

from app.api.v1.dependencies import CustomTestServiceDep, CurrentUser
from app.models.custom_test import AttemptStatus, CustomTestAnalysis
from app.schemas.custom_test import (
    QuestionStatus,
    QuestionNumber,
    QuestionAnswerSubmit,
    QuestionAppearance,
    CustomTestResponse,
    CustomTestDetailResponse,
    CustomTestListResponse,
    CustomTestQuestionResponse,
    CustomTestSubmitRequest,
    CustomTestSubmitResponse,
    CustomTestAnalysisResponse,
    CustomTestAttemptResponse,
    CustomTestAttemptsListResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException
from app.models.Basequestion import TargetExam

router = APIRouter(prefix="/custom-tests", tags=["Custom Tests"])


# ==================== Test CRUD Endpoints ====================

@router.post("/", response_model=CustomTestResponse, status_code=201)
async def create_custom_test(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    exam_type: TargetExam,
    chapters: list[UUID],
    question_type: QuestionAppearance,
    question_status: QuestionStatus,
    number_of_question: QuestionNumber,
    time_duration: int,
) -> CustomTestResponse:
    """Create a new custom test with selected questions"""
    try:
        test = await custom_test_service.create_test(
            user_id=current_user.id,
            exam_type=exam_type,
            chapters=chapters,
            question_status=question_status,
            number_of_question=number_of_question,
            time_duration=time_duration,
            question_type=question_type
        )
        question_count = await custom_test_service.get_test_question_count(test.id)
        
        return CustomTestResponse(
            id=test.id,
            user_id=test.user_id,
            status=test.status,
            created_at=test.created_at,
            updated_at=test.updated_at,
            question_count=question_count,
        )
    except ValueError as e:
        raise BadRequestException(str(e))


@router.get("/", response_model=CustomTestListResponse)
async def get_my_tests(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    status: Optional[AttemptStatus] = Query(None, description="Filter by test status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
) -> CustomTestListResponse:
    """Get all custom tests for the current user"""
    tests, total = await custom_test_service.get_user_tests(
        user_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit,
    )
    
    test_responses = []
    for test in tests:
        question_count = await custom_test_service.get_test_question_count(test.id)
        test_responses.append(CustomTestResponse(
            id=test.id,
            user_id=test.user_id,
            status=test.status,
            created_at=test.created_at,
            updated_at=test.updated_at,
            question_count=question_count,
        ))
    
    return CustomTestListResponse(
        tests=test_responses,
        total=total,
        skip=skip,
        limit=limit,
    )

@router.get("/{test_id}", response_model=CustomTestDetailResponse)
async def get_test_detail(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    test_id: UUID,
) -> CustomTestDetailResponse:
    """Get a specific custom test with all its questions"""
    test = await custom_test_service.get_test_with_questions(test_id)
    if not test:
        raise NotFoundException(f"Test with ID {test_id} not found")
    
    # Verify ownership
    if test.user_id != current_user.id:
        raise NotFoundException(f"Test with ID {test_id} not found")
    
    # Build question responses
    questions = []
    total_marks = 0
    
    for test_question in test.questions:
        q = test_question.question
        total_marks += q.marks
        questions.append(CustomTestQuestionResponse(
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
        ))
    
    return CustomTestDetailResponse(
        id=test.id,
        user_id=test.user_id,
        status=test.status,
        created_at=test.created_at,
        updated_at=test.updated_at,
        questions=questions,
        total_marks=total_marks,
    )


@router.post("/{test_id}/start", response_model=CustomTestResponse)
async def start_test(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    test_id: UUID,
) -> CustomTestResponse:
    """Start a custom test (change status from not_started to active)"""
    try:
        test = await custom_test_service.start_test(test_id, current_user.id)
        if not test:
            raise NotFoundException(f"Test with ID {test_id} not found")
        
        question_count = await custom_test_service.get_test_question_count(test.id)
        
        return CustomTestResponse(
            id=test.id,
            user_id=test.user_id,
            status=test.status,
            created_at=test.created_at,
            updated_at=test.updated_at,
            question_count=question_count,
        )
    except ValueError as e:
        raise BadRequestException(str(e))


@router.patch("/{test_id}/status", response_model=CustomTestResponse)
async def update_test_status(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    test_id: UUID,
    request: AttemptStatus,
) -> CustomTestResponse:
    """Update the status of a custom test"""
    test = await custom_test_service.update_test_status(
        test_id=test_id,
        user_id=current_user.id,
        status=request,
    )
    if not test:
        raise NotFoundException(f"Test with ID {test_id} not found")
    
    question_count = await custom_test_service.get_test_question_count(test.id)
    
    return CustomTestResponse(
        id=test.id,
        user_id=test.user_id,
        status=test.status,
        created_at=test.created_at,
        updated_at=test.updated_at,
        question_count=question_count,
    )


@router.delete("/{test_id}", status_code=204)
async def delete_test(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    test_id: UUID,
) -> None:
    """Delete a custom test"""
    deleted = await custom_test_service.delete_test(test_id, current_user.id)
    if not deleted:
        raise NotFoundException(f"Test with ID {test_id} not found")


# ==================== Test Submission Endpoints ====================

@router.post("/{test_id}/submit", response_model=CustomTestSubmitResponse)
async def submit_test(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    test_id: UUID,
    request: CustomTestSubmitRequest,
) -> CustomTestSubmitResponse:
    """Submit a custom test with answers and get results"""
    try:
        analysis, results = await custom_test_service.submit_test(
            test_id=test_id,
            user_id=current_user.id,
            answers=request.answers,
            total_time_spent=request.total_time_spent,
        )
        
        total_questions = analysis.correct + analysis.incorrect + analysis.unattempted
        accuracy = round((analysis.correct / total_questions * 100) if total_questions > 0 else 0, 2)
        
        return CustomTestSubmitResponse(
            test_id=test_id,
            analysis_id=analysis.id,
            marks_obtained=analysis.marks_obtained,
            total_marks=analysis.total_marks,
            correct=analysis.correct,
            incorrect=analysis.incorrect,
            unattempted=analysis.unattempted,
            total_time_spent=analysis.total_time_spent,
            accuracy=accuracy,
            results=results,
        )
    except ValueError as e:
        raise BadRequestException(str(e))


# ==================== Attempts Endpoints ====================

# ==================== submission Endpoints ====================

@router.post("/create", response_model=CustomTestAnalysis)
async def create_submission(
    custom_test_service: CustomTestServiceDep,
    test_id: UUID,   
    current_user: CurrentUser,
    answers: list[QuestionAnswerSubmit],
    total_time_spent : int,
) -> CustomTestAnalysis:
    try:
        analysis,results = await custom_test_service.submit_test(
            test_id=test_id,
            user_id=CurrentUser.id,
            answers=answers,
            total_time_spent=total_time_spent
        )

        total_questions = analysis.correct + analysis.incorrect + analysis.unattempted
        accuracy = round((analysis.correct / total_questions * 100) if total_questions > 0 else 0, 2)

        return CustomTestSubmitResponse(
            test_id=test_id,
            analysis_id=analysis.id,
            marks_obtained=analysis.marks_obtained,
            total_marks=analysis.total_marks,
            correct=analysis.correct,
            incorrect=analysis.incorrect,
            unattempted=analysis.unattempted,
            total_time_spent=analysis.total_time_spent,
            accuracy=accuracy,
            results=results,
        )
    except ValueError as e:
        raise BadRequestException(str(e))


@router.get("/{test_id}/attempts", response_model=CustomTestAttemptsListResponse)
async def get_test_attempts(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    test_id: UUID,
) -> CustomTestAttemptsListResponse:
    """Get all question attempts for a specific custom test"""
    try:
        attempts, summary = await custom_test_service.get_test_attempts(
            test_id=test_id,
            user_id=current_user.id,
        )
        
        return CustomTestAttemptsListResponse(
            test_id=test_id,
            attempts=[
                CustomTestAttemptResponse(
                    id=a.id,
                    user_id=a.user_id,
                    question_id=a.question_id,
                    user_answer=a.user_answer,
                    is_correct=a.is_correct,
                    marks_obtained=a.marks_obtained,
                    time_taken=a.time_taken,
                    attempted_at=a.attempted_at,
                    explanation_viewed=a.explanation_viewed,
                    hint_used=a.hint_used,
                )
                for a in attempts
            ],
            total_attempts=summary["total_attempts"],
            total_correct=summary["total_correct"],
            total_incorrect=summary["total_incorrect"],
            total_marks_obtained=summary["total_marks_obtained"],
            total_time_taken=summary["total_time_taken"],
        )
    except ValueError as e:
        raise BadRequestException(str(e))


# ==================== Analysis Endpoints ====================


@router.get("/analyses/{analysis_id}", response_model=CustomTestAnalysisResponse)
async def get_analysis(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    analysis_id: UUID,
) -> CustomTestAnalysisResponse:
    """Get a specific test analysis"""
    analysis = await custom_test_service.get_analysis_by_id(analysis_id)
    if not analysis:
        raise NotFoundException(f"Analysis with ID {analysis_id} not found")
    
    # Verify ownership
    if analysis.user_id != current_user.id:
        raise NotFoundException(f"Analysis with ID {analysis_id} not found")
    
    total = analysis.correct + analysis.incorrect + analysis.unattempted
    
    return CustomTestAnalysisResponse(
        id=analysis.id,
        user_id=analysis.user_id,
        marks_obtained=analysis.marks_obtained,
        total_marks=analysis.total_marks,
        total_time_spent=analysis.total_time_spent,
        correct=analysis.correct,
        incorrect=analysis.incorrect,
        unattempted=analysis.unattempted,
        submitted_at=analysis.submitted_at,
        accuracy=round((analysis.correct / total * 100) if total > 0 else 0, 2),
    )


@router.delete("/analyses/{analysis_id}", status_code=204)
async def delete_analysis(
    custom_test_service: CustomTestServiceDep,
    current_user: CurrentUser,
    analysis_id: UUID,
) -> None:
    """Delete a test analysis"""
    deleted = await custom_test_service.delete_analysis(analysis_id, current_user.id)
    if not deleted:
        raise NotFoundException(f"Analysis with ID {analysis_id} not found")
