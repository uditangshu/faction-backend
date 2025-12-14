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


class QuestionAppearance(str, Enum):
    """Question appearance filter options"""
    PYQ_ONLY = "pyq_only"  # Only questions that are in PYQ
    NON_PYQ_ONLY = "non_pyq_only"  # Only questions that are NOT in PYQ
    BOTH = "both"  # All questions regardless of PYQ status


class QuestionResponse(BaseModel):
    """Question response with optional PYQ details"""
    question_id: UUID
    question: Question
    
    # PYQ details (if question is a PYQ)
    pyq_id: Optional[UUID] = None
    year: Optional[int] = None
    exam_detail: Optional[List[str]] = None
    pyq_created_at: Optional[str] = None
    
    # Last practiced info (if available)
    last_practiced_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class QuestionFilteredListResponse(BaseModel):
    """Filtered question list response with infinite scrolling support"""
    questions: List[QuestionResponse]
    total: int
    cursor: Optional[UUID] = None  # Last question ID for infinite scrolling
    has_more: bool  # Whether there are more questions to load


class PYQFilterRequest(BaseModel):
    """Request filters for PYQ questions"""
    difficulty: Optional[DifficultyLevel] = None
    question_type: Optional[QuestionType] = None
    year_wise_sorting: Optional[YearWiseSorting] = None
    last_practiced_first: bool = False
    exam_filter: Optional[List[str]] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
