"""Filtering Schemas"""

from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.Basequestion import QuestionType, DifficultyLevel, Question
from app.models.user import TargetExam
from enum import Enum



class YearWiseSorting(str, Enum):
    """Year-wise sorting options"""
    ASCENDING = "ascending"
    DESCENDING = "descending"


class PYQQuestionResponse(BaseModel):
    """PYQ Question response with question details"""
    pyq_id: UUID
    question_id: UUID
    year: int
    exam_detail: List[str]
    pyq_created_at: str
    
    # Question details
    question: Question
    
    # Last practiced info (if available)
    last_practiced_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class PYQFilteredListResponse(BaseModel):
    """Filtered PYQ list response"""
    questions: List[PYQQuestionResponse]
    total: int
    skip: int
    limit: int


class PYQFilterRequest(BaseModel):
    """Request filters for PYQ questions"""
    difficulty: Optional[DifficultyLevel] = None
    question_type: Optional[QuestionType] = None
    year_wise_sorting: Optional[YearWiseSorting] = None
    last_practiced_first: bool = False
    exam_filter: Optional[List[str]] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
