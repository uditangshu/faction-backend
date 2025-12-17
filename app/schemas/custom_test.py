"""Custom Test Schemas"""

from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.Basequestion import QuestionType, DifficultyLevel
from app.models.user import TargetExam
from app.models.custom_test import AttemptStatus


class CustomTestGenerateRequest(BaseModel):
    """Request to generate a custom test"""
    exam_type: TargetExam = Field(..., description="Target exam type")
    subject_ids: List[UUID] = Field(..., min_length=1, description="List of subject UUIDs")
    chapter_ids: List[UUID] = Field(..., min_length=1, description="List of chapter UUIDs")
    number_of_questions: int = Field(..., ge=1, le=100, description="Number of questions to generate")
    pyq_only: bool = Field(False, description="If true, only PYQ questions; if false, all questions")
    weak_topics_only: bool = Field(False, description="If true, only questions from weak topics")
    weakness_score: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=100.0, 
        description="Minimum weakness score threshold (0-100). Only used when weak_topics_only=True. If no weak topics match, falls back to all topics in requested chapters."
    )
    time_assigned: int = Field(0, ge=0, description="Time assigned for the test in seconds (0 means no time limit)")


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


class CustomTestGenerateResponse(BaseModel):
    """Response after generating custom test"""
    id: UUID
    user_id: UUID
    status: str
    time_assigned: int
    created_at: str
    updated_at: str
    questions: List[CustomTestQuestionResponse]
    total_questions: int
    total_marks: int


class CustomTestListResponse(BaseModel):
    """Response for list of custom tests"""
    id: UUID
    user_id: UUID
    status: str
    time_assigned: int
    created_at: str
    updated_at: str
    question_count: int

    class Config:
        from_attributes = True


class CustomTestListPaginatedResponse(BaseModel):
    """Paginated list of custom tests"""
    tests: List[CustomTestListResponse]
    total: int
    skip: int
    limit: int


class CustomTestDetailResponse(BaseModel):
    """Response for custom test detail with questions"""
    id: UUID
    user_id: UUID
    status: str
    time_assigned: int
    created_at: str
    updated_at: str
    questions: List[CustomTestQuestionResponse]
    total_questions: int
    total_marks: int

    class Config:
        from_attributes = True

