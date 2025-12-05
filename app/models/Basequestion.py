"""Question bank models"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import List, Optional
from app.models.user import TargetExam

class QuestionType(str, Enum):
    INTEGER = "integer"
    MCQ = "mcq"
    MATCH = "match_the_column"
    SCQ = "scq"

class Class_level(int, Enum) : 
    """Class Level enumeration"""
    Ninth = 9
    Tenth = 10
    Eleventh = 11
    Twelth = 12

class Subject_Type(str, Enum):
    PHYSICS = "Physics"
    CHEMISTRY = "Chemistry"
    MATHS = "Maths"
    BIOLOGY = "Biology"


class DifficultyLevel(int, Enum):
    """Difficulty level (1-5 scale)"""
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4
    MASTER = 5


class Class(SQLModel, table=True):
    """Class Model"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    class_level: Class_level
    subjects: List["Subject"] = Relationship(back_populates="subject_class_lvl")


class Subject(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    subject_type: Subject_Type
    
    # Foreign Key
    class_id: UUID = Field(foreign_key="class.id")
    
    # Relationships
    subject_class_lvl: Optional[Class] = Relationship(back_populates="subjects")
    chapters: List["Chapter"] = Relationship(back_populates="subject")
    
class Chapter(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    
    # Foreign Key
    subject_id: UUID = Field(foreign_key="subject.id")
    
    # Relationships
    subject: Optional[Subject] = Relationship(back_populates="chapters")
    topics: List["Topic"] = Relationship(back_populates="chapter")

class Topic(SQLModel, table= True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str

    #Foreign Key
    chapter_id: UUID = Field(foreign_key="chapter.id")

    #Relationships
    chapter: Optional[Chapter] = Relationship(back_populates="topics")
    questions: List["Question"] = Relationship(back_populates="topic")


class Question(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign Key
    topic_id: UUID = Field(foreign_key="topic.id")
    topic: Optional[Topic] = Relationship(back_populates="questions")

    # Core Attributes
    type: QuestionType
    difficulty: DifficultyLevel

    # Storing a list of Enums using JSON column
    # Example data: ["JEE", "NEET"]
    exam_type: List[TargetExam] = Field(sa_column=Column(JSON)) 

    # Common Fields
    question_text: str
    marks: int
    solution_text: str
    
    # Optional / Specific Fields
    question_image: Optional[str] = None
    
    # Integer type
    integer_answer: Optional[int] = None
    
    # MCQ type (Lists stored as JSON)
    mcq_options: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    mcq_correct_option: Optional[int] = None # Index of the correct option
    
    # SCQ / Multiple Correct type
    scq_options: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    scq_correct_options: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))

    #stats
    questions_solved: int
