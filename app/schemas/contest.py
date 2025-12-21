"""Contest Schemas"""

from uuid import UUID
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.contest import ContestStatus
from app.models.Basequestion import QuestionType, DifficultyLevel
from app.models.user import TargetExam


class ContestCreateRequest(BaseModel):
    """Request to create a contest"""
    name: str = Field(..., description="Contest name")
    description: str | None = Field(None, description="Contest description")
    question_ids: List[UUID] = Field(..., min_length=1, description="List of question UUIDs")
    total_time: int = Field(..., ge=1, description="Total time for the contest in seconds")
    status: ContestStatus = Field(..., description="Contest status")
    starts_at: datetime = Field(..., description="Contest start datetime")
    ends_at: datetime = Field(..., description="Contest end datetime")


class ContestResponse(BaseModel):
    """Contest response"""
    id: UUID
    name: str
    description: str | None
    total_time: int
    status: ContestStatus
    starts_at: datetime
    ends_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ContestListResponse(BaseModel):
    """Response for list of contests"""
    contests: List[ContestResponse]

    class Config:
        from_attributes = True


class ContestQuestionResponse(BaseModel):
    """Question response with full details for contest"""
    id: UUID
    topic_id: UUID
    type: QuestionType
    difficulty: DifficultyLevel
    exam_type: List[TargetExam]
    question_text: str
    marks: int
    solution_text: str
    question_image: Optional[str] = None
    integer_answer: Optional[int] = None
    mcq_options: Optional[List[str]] = None
    mcq_correct_option: Optional[List[int]] = None
    scq_options: Optional[List[str]] = None
    scq_correct_options: Optional[int] = None
    questions_solved: int

    class Config:
        from_attributes = True


class ContestQuestionsResponse(BaseModel):
    """Response for contest questions"""
    questions: List[ContestQuestionResponse]


class ContestSubmissionAttempt(BaseModel):
    """Single submission attempt for contest"""
    question_id: UUID
    user_answer: List[str]
    time_taken: int = Field(0, ge=0, description="Time taken in seconds")
    hint_used: bool = Field(default=False, description="Whether hint was used")


class ContestSubmissionRequest(BaseModel):
    """Request to submit contest answers"""
    contest_id: UUID = Field(..., description="Contest ID")
    submissions: List[ContestSubmissionAttempt] = Field(..., min_length=1, description="Array of submission attempts")


class ContestSubmissionResponse(BaseModel):
    """Response for contest submission"""
    message: str
    submissions_count: int
    queue_name: str

