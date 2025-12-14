"""Question schemas"""

from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.Basequestion import QuestionType, Class_level, Subject_Type, DifficultyLevel
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
    exam_type: List[TargetExam]

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
    exam_type: Optional[List[TargetExam]] = None


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


# ==================== Topic Schemas ====================

class TopicCreateRequest(BaseModel):
    """Request to create a new topic"""
    name: str
    chapter_id: UUID


class TopicResponse(BaseModel):
    """Single topic response"""
    id: UUID
    name: str
    chapter_id: UUID

    class Config:
        from_attributes = True


class TopicListResponse(BaseModel):
    """List of topics response"""
    topics: List[TopicResponse]
    total: int


class ChapterWithTopicsResponse(ChapterResponse):
    """Chapter with its topics"""
    topics: List[TopicResponse] = []


class QuestionResponse(BaseModel):
    """Question response"""
    id: UUID
    topic_id: UUID
    type: QuestionType
    difficulty: DifficultyLevel
    exam_type: List[TargetExam]
    question_text: str
    marks: int
    question_image: Optional[str] = None

    class Config:
        from_attributes = True


class TopicWithQuestionsResponse(TopicResponse):
    """Topic with its questions"""
    questions: List["QuestionResponse"] = []


# ==================== Question Schemas ====================

class QuestionCreateRequest(BaseModel):
    """Request to create a new question"""
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
    mcq_correct_option: Optional[int] = None

    scq_options: Optional[List[str]] = None
    scq_correct_options: Optional[List[int]] = None


class QuestionUpdateRequest(BaseModel):
    """Request to update an existing question"""
    topic_id: Optional[UUID] = None
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


# ==================== Bookmark/Analysis Schemas ====================

class BookmarkCreateRequest(BaseModel):
    """Request to create a bookmark"""
    question_id: UUID


class BookmarkResponse(BaseModel):
    """Bookmark response"""
    id: UUID
    user_id: UUID
    question_id: UUID
    created_at: str

    class Config:
        from_attributes = True


class BookmarkListResponse(BaseModel):
    """List of bookmarks response"""
    bookmarks: List[BookmarkResponse]
    total: int


class BookmarkToggleResponse(BaseModel):
    """Response for bookmark toggle"""
    is_bookmarked: bool
    bookmark: Optional[BookmarkResponse] = None


# ==================== Attempt Schemas ====================

class AttemptCreateRequest(BaseModel):
    """Request to create an attempt"""
    question_id: UUID
    user_answer: List[str]
    is_correct: bool
    marks_obtained: int = Field(..., description="Marks obtained for the attempt")
    time_taken: int = Field(0, ge=0, description="Time taken in seconds")
    hint_used: bool = False


class AttemptResponse(BaseModel):
    """Attempt response"""
    id: UUID
    user_id: UUID
    question_id: UUID
    user_answer: List[str]
    is_correct: bool
    marks_obtained: int
    time_taken: int
    attempted_at: str
    explanation_viewed: bool
    hint_used: bool

    class Config:
        from_attributes = True


class AttemptUpdateRequest(BaseModel):
    """Request to update an attempt"""
    explanation_viewed: Optional[bool] = None
    hint_used: Optional[bool] = None


class AttemptListResponse(BaseModel):
    """Paginated list of attempts"""
    attempts: List[AttemptResponse]
    total: int
    skip: int
    limit: int


class AttemptStatsResponse(BaseModel):
    """User attempt statistics"""
    total_attempts: int
    correct_attempts: int
    incorrect_attempts: int
    accuracy: float
    total_marks: int
    average_time_seconds: float


# ==================== PYQ Schemas ====================

class PYQCreateRequest(BaseModel):
    """Request to create a PYQ entry"""
    question_id: UUID
    year: int = Field(..., description="Year of the exam")
    exam_detail: List[str] = Field(..., description="List of exam details (e.g., ['JEE 2023', 'JEE 2022'])")


class PYQResponse(BaseModel):
    """PYQ response"""
    id: UUID
    question_id: UUID
    year: int
    exam_detail: List[str]
    created_at: str

    class Config:
        from_attributes = True


class PYQUpdateRequest(BaseModel):
    """Request to update a PYQ"""
    year: Optional[int] = None
    exam_detail: Optional[List[str]] = None


class PYQListResponse(BaseModel):
    """Paginated list of PYQs"""
    pyqs: List[PYQResponse]
    total: int
    skip: int
    limit: int


# ==================== QOTD Schemas ====================

class QOTDQuestionResponse(QuestionDetailedResponse):
    """QOTD question response with subject name"""
    subject_name: str

    class Config:
        from_attributes = True


class QOTDResponse(BaseModel):
    """Question of the Day response with 3 questions from different subjects"""
    questions: List[QOTDQuestionResponse]

    class Config:
        from_attributes = True
