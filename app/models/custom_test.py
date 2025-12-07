"""Custom Test Making model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from app.models.linking import CustomTestQuestion
from enum import Enum

class AttemptStatus(str, Enum):
    active="active"
    finished="finished"
    not_started="not_started"

class CustomTest(SQLModel,table=True):

    id: UUID= Field(default_factory=uuid4, primary_key=True)
    user_id : UUID = Field(foreign_key="users.id")
    questions: list["CustomTestQuestion"] = Relationship(back_populates="test")
    time_assigned: int
    status: AttemptStatus
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)



class CustomTestAnalysis(SQLModel, table=True):

    id: UUID= Field(default_factory=uuid4, primary_key=True)
    user_id : UUID = Field(foreign_key="users.id")
    custom_test_id: UUID = Field(foreign_key="customtest.id", index=True)
    marks_obtained: int
    total_marks: int
    total_time_spent: int
    correct: int
    incorrect: int
    unattempted: int
    submitted_at: datetime = Field(default_factory=datetime.now)




