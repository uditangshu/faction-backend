"""Question schemas"""

from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.question import QuestionType


class QuestionOptionResponse(BaseModel):
    """Question option response (without correct answer info for students)"""

    id: UUID
    option_text: str
    option_label: str

    class Config:
        from_attributes = True


class QuestionListResponse(BaseModel):
    """Question list item response"""

    id: UUID
    subject_id: UUID
    topic_id: UUID
    question_text: str
    question_type: QuestionType
    difficulty_level: int
    difficulty_rating: int
    time_limit: int
    points: int
    is_premium: bool

    class Config:
        from_attributes = True


class QuestionDetailResponse(QuestionListResponse):
    """Question detail response with options"""

    options: List[QuestionOptionResponse] = []

    class Config:
        from_attributes = True


class SubmitAnswerRequest(BaseModel):
    """Submit answer request"""

    user_answer: str = Field(..., description="User's answer (option label for MCQ, value for numerical, JSON array for multi-select)")
    time_taken: int = Field(..., description="Time taken in seconds", ge=0)


class SubmitAnswerResponse(BaseModel):
    """Submit answer response"""

    attempt_id: UUID
    is_correct: bool
    marks_obtained: int
    time_taken: int
    explanation: Optional[str] = None


class QuestionFilters(BaseModel):
    """Query filters for questions"""

    subject_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

