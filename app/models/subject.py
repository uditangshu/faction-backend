"""Educational structure models: Subject, Topic, Concept"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class Subject(SQLModel, table=True):
    """Subject model (e.g., Physics, Chemistry, Mathematics, Biology)"""
    
    __tablename__ = "subjects"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    code: str = Field(max_length=20, unique=True)
    description: str | None = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now())


class Topic(SQLModel, table=True):
    """Topic/Chapter model under a subject"""
    
    __tablename__ = "topics"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    subject_id: UUID = Field(foreign_key="subjects.id", index=True)
    name: str = Field(max_length=200)
    description: str | None = None
    difficulty_level: int = Field(ge=1, le=5, default=1)  # 1-5 scale
    parent_topic_id: UUID | None = Field(default=None, foreign_key="topics.id")
    order_sequence: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Concept(SQLModel, table=True):
    """Concept model (sub-topics under a topic)"""
    
    __tablename__ = "concepts"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    topic_id: UUID = Field(foreign_key="topics.id", index=True)
    name: str = Field(max_length=200)
    description: str | None = None
    difficulty_level: int = Field(ge=1, le=5, default=1)
    weightage: float = Field(ge=0.0, le=1.0, default=0.1)  # Importance weightage
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now())

