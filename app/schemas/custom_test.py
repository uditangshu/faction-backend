"""Custom Test Schemas"""

from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.custom_test import AttemptStatus
from app.models.Basequestion import QuestionType, DifficultyLevel
from app.models.user import TargetExam


# ==================== Custom Test Schemas ====================

from enum import Enum


class QuestionStatus(str, Enum):
    """Question Attempt Status"""
    ALL = "all"
    UNSOLVED = "unsolved"
    SOLVED = "solved"
    INCORRECT = "incorrect"


class QuestionNumber(int, Enum):
    """Number of questions for the Custom Test"""
    FIVE = 5
    TEN = 10
    FIFTEEN = 15
    TWENTY = 20
    TWENTY_FIVE = 25
    THIRTY = 30


class QuestionAppearance(str, Enum):
    """General Question vs PYQs"""
    PYQS = "pyqs"
    NON_PYQS = "non_pyqs"
    BOTH = "both"

class CustomTestCreateRequest(BaseModel):
    """Request to create a new custom test"""
    question_ids: List[UUID] = Field(..., min_length=1, description="List of question IDs to include in the test")


class CustomTestQuestionResponse(BaseModel):
    """Question in custom test response"""
    id: UUID
    question_id: UUID
    topic_id: UUID
    type: QuestionType
    difficulty: DifficultyLevel
    exam_type: List[TargetExam]
    question_text: str
    marks: int
    question_image: Optional[str] = None
    
    # MCQ fields
    mcq_options: Optional[List[str]] = None
    
    # SCQ fields
    scq_options: Optional[List[str]] = None

    class Config:
        from_attributes = True


class CustomTestResponse(BaseModel):
    """Custom test response"""
    id: UUID
    user_id: UUID
    status: AttemptStatus
    created_at: datetime
    updated_at: datetime
    question_count: int = 0

    class Config:
        from_attributes = True


class CustomTestDetailResponse(BaseModel):
    """Custom test with questions response"""
    id: UUID
    user_id: UUID
    status: AttemptStatus
    created_at: datetime
    updated_at: datetime
    questions: List[CustomTestQuestionResponse] = []
    total_marks: int = 0

    class Config:
        from_attributes = True


class CustomTestListResponse(BaseModel):
    """Paginated list of custom tests"""
    tests: List[CustomTestResponse]
    total: int
    skip: int
    limit: int


class CustomTestUpdateStatusRequest(BaseModel):
    """Request to update test status"""
    status: AttemptStatus


# ==================== Custom Test Answer Schemas ====================

class QuestionAnswerSubmit(BaseModel):
    """Single question answer submission"""
    question_id: UUID
    user_answer: Optional[List[str]] = None  # None for unattempted
    time_spent: int = Field(0, ge=0, description="Time spent on this question in seconds")
    

class CustomTestSubmitRequest(BaseModel):
    """Request to submit a custom test"""
    answers: List[QuestionAnswerSubmit]
    total_time_spent: int = Field(..., ge=0, description="Total time spent on the test in seconds")


class QuestionResultResponse(BaseModel):
    """Result for a single question"""
    question_id: UUID
    user_answer: Optional[List[str]] = None
    correct_answer: Optional[List[str]] = None
    is_correct: bool
    marks_obtained: int
    marks_possible: int


class CustomTestSubmitResponse(BaseModel):
    """Response after submitting a custom test"""
    test_id: UUID
    analysis_id: UUID
    marks_obtained: int
    total_marks: int
    correct: int
    incorrect: int
    unattempted: int
    total_time_spent: int
    accuracy: float
    results: List[QuestionResultResponse]


# ==================== Custom Test Analysis Schemas ====================

class CustomTestAnalysisResponse(BaseModel):
    """Custom test analysis response"""
    id: UUID
    user_id: UUID
    marks_obtained: int
    total_marks: int
    total_time_spent: int
    correct: int
    incorrect: int
    unattempted: int
    submitted_at: datetime
    accuracy: float = 0.0

    class Config:
        from_attributes = True


class CustomTestAnalysisListResponse(BaseModel):
    """Paginated list of custom test analyses"""
    analyses: List[CustomTestAnalysisResponse]
    total: int
    skip: int
    limit: int


# ==================== Custom Test Stats Schemas ====================

class CustomTestStatsResponse(BaseModel):
    """User's custom test statistics"""
    total_tests: int
    tests_completed: int
    tests_in_progress: int
    tests_not_started: int
    total_questions_attempted: int
    total_correct: int
    total_incorrect: int
    total_unattempted: int
    overall_accuracy: float
    total_time_spent: int  # in seconds
    average_score_percentage: float


# ==================== Custom Test Attempt Schemas ====================

class CustomTestAttemptResponse(BaseModel):
    """Question attempt response for custom test"""
    id: UUID
    user_id: UUID
    question_id: UUID
    user_answer: List[str]
    is_correct: bool
    marks_obtained: int
    time_taken: int
    attempted_at: datetime
    explanation_viewed: bool
    hint_used: bool

    class Config:
        from_attributes = True


class CustomTestAttemptsListResponse(BaseModel):
    """List of attempts for a custom test"""
    test_id: UUID
    attempts: List[CustomTestAttemptResponse]
    total_attempts: int
    total_correct: int
    total_incorrect: int
    total_marks_obtained: int
    total_time_taken: int

