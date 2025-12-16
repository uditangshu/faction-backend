"""Custom Test Schemas"""

from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.Basequestion import QuestionType, DifficultyLevel
from app.models.user import TargetExam
from app.schemas.filters import QuestionAppearance


class CustomTestGenerateRequest(BaseModel):
    """Request to generate a custom test"""
    exam_type: TargetExam = Field(..., description="Target exam type")
    subject_ids: List[UUID] = Field(..., min_length=1, description="List of subject UUIDs")
    chapter_ids: List[UUID] = Field(..., min_length=1, description="List of chapter UUIDs")
    number_of_questions: int = Field(..., ge=1, le=100, description="Number of questions to generate")
    pyq_only: bool = Field(False, description="If true, only PYQ questions; if false, all questions")
    weak_topics_only: bool = Field(False, description="If true, only questions from weak topics")


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
    questions: List[CustomTestQuestionResponse]
    total_questions: int
    total_marks: int

