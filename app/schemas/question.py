"""Question schemas"""

from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.question import QuestionType, Class_level, Subject_Type, DifficultyLevel
from app.models.user import TargetExam


# ==================== Class Schemas ====================

class ClassCreateRequest(BaseModel):
    """Request to create a new class"""
    class_level: Class_level


class ClassResponse(BaseModel):
    """Single class response"""
    id: UUID
    class_level: Class_level

    class Config:
        from_attributes = True


class ClassListResponse(BaseModel):
    """List of classes response"""
    classes: List[ClassResponse]
    total: int

class SubjectResponse(BaseModel):
    """Single subject response"""
    id: UUID
    subject_type: Subject_Type
    class_id: UUID

    class Config:
        from_attributes = True

class ClassWithSubjectsResponse(ClassResponse):
    """Class with its subjects"""
    subjects: List["SubjectResponse"] = []


# ==================== Subject Schemas ====================

class SubjectCreateRequest(BaseModel):
    """Request to create a new subject"""
    subject_type: Subject_Type
    class_id: UUID


class SubjectListResponse(BaseModel):
    """List of subjects response"""
    subjects: List[SubjectResponse]
    total: int

class ChapterResponse(BaseModel):
    """Single chapter response"""
    id: UUID
    name: str
    subject_id: UUID

    class Config:
        from_attributes = True


class SubjectWithChaptersResponse(SubjectResponse):
    """Subject with its chapters"""
    chapters: List["ChapterResponse"] = []


# ==================== Chapter Schemas ====================

class ChapterCreateRequest(BaseModel):
    """Request to create a new chapter"""
    name: str
    subject_id: UUID


class ChapterListResponse(BaseModel):
    """List of chapters response"""
    chapters: List[ChapterResponse]
    total: int


class QuestionResponse(BaseModel):
    """Question response"""
    id: UUID
    chapter_id: UUID
    type: QuestionType
    difficulty: DifficultyLevel
    exam_type: List[TargetExam]
    question_text: str
    marks: int
    question_image: Optional[str] = None

    class Config:
        from_attributes = True


class ChapterWithQuestionsResponse(ChapterResponse):
    """Chapter with its questions"""
    questions: List["QuestionResponse"] = []


# ==================== Question Schemas ====================

class QuestionCreateRequest(BaseModel):
    """Request to create a new question"""
    chapter_id: UUID
    type: QuestionType
    difficulty: DifficultyLevel
    exam_type: List[TargetExam]

    question_text: str
    marks: int
    solution_text: str
    question_image: Optional[str] = None

    integer_answer: Optional[int] = None
    mcq_options: Optional[List[str]] = None
    mcq_correct_option: Optional[int] = None

    scq_options: Optional[List[str]] = None
    scq_correct_options: Optional[List[int]] = None


class QuestionUpdateRequest(BaseModel):
    """Request to update an existing question"""
    chapter_id: Optional[UUID] = None
    type: Optional[QuestionType] = None
    difficulty: Optional[DifficultyLevel] = None
    exam_type: Optional[List[TargetExam]] = None

    question_text: Optional[str] = None
    marks: Optional[int] = None
    solution_text: Optional[str] = None
    question_image: Optional[str] = None

    integer_answer: Optional[int] = None
    mcq_options: Optional[List[str]] = None
    mcq_correct_option: Optional[int] = None

    scq_options: Optional[List[str]] = None
    scq_correct_options: Optional[List[int]] = None


class QuestionDetailedResponse(BaseModel):
    """Detailed question response with all fields"""
    id: UUID
    chapter_id: UUID
    type: QuestionType
    difficulty: DifficultyLevel
    exam_type: List[TargetExam]
    question_text: str
    marks: int
    solution_text: str
    question_image: Optional[str] = None
    integer_answer: Optional[int] = None
    mcq_options: Optional[List[str]] = None
    mcq_correct_option: Optional[int] = None
    scq_options: Optional[List[str]] = None
    scq_correct_options: Optional[List[int]] = None
    questions_solved: int

    class Config:
        from_attributes = True


class QuestionPaginatedResponse(BaseModel):
    """Paginated list of questions"""
    questions: List[QuestionResponse]
    total: int
    skip: int
    limit: int


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

