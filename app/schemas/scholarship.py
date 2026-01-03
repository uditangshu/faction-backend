"""Scholarship Test Schemas"""

from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.Basequestion import QuestionType, DifficultyLevel
from app.models.user import TargetExam


class ScholarshipTestCreateRequest(BaseModel):
    """Request to create a scholarship test"""
    class_id: UUID = Field(..., description="Class ID to filter subjects")
    exam_type: TargetExam = Field(..., description="Target exam type")


class ScholarshipQuestionResponse(BaseModel):
    """Question in scholarship test response (without answers)"""
    id: UUID
    question_id: UUID
    topic_id: UUID
    type: QuestionType
    difficulty: DifficultyLevel
    exam_type: List[TargetExam]
    question_text: str
    marks: int
    question_image: Optional[str] = None
    
    # MCQ fields (options only, no correct answer)
    mcq_options: Optional[List[str]] = None
    
    # SCQ fields (options only, no correct answer)
    scq_options: Optional[List[str]] = None
    
    # No solution_text, no correct_option, no integer_answer

    class Config:
        from_attributes = True


class ScholarshipTestCreateResponse(BaseModel):
    """Response after creating scholarship test"""
    id: UUID
    user_id: UUID
    class_id: UUID
    exam_type: TargetExam
    status: str
    time_assigned: int
    created_at: str
    updated_at: str
    questions: List[ScholarshipQuestionResponse]
    total_questions: int
    total_marks: int

    class Config:
        from_attributes = True


class ScholarshipSubmissionAttempt(BaseModel):
    """Single submission attempt for scholarship"""
    question_id: UUID
    user_answer: List[str]
    time_taken: int = Field(0, ge=0, description="Time taken in seconds")


class ScholarshipSubmitRequest(BaseModel):
    """Request to submit scholarship test"""
    scholarship_id: UUID = Field(..., description="Scholarship ID")
    submissions: List[ScholarshipSubmissionAttempt] = Field(..., min_length=1, description="Array of submission attempts")


class ScholarshipResultResponse(BaseModel):
    """Response after submitting scholarship test"""
    id: UUID
    user_id: UUID
    scholarship_id: UUID
    score: float
    total_marks: int
    time_taken: int
    correct: int
    incorrect: int
    unattempted: int
    accuracy: float
    submitted_at: str

    class Config:
        from_attributes = True

