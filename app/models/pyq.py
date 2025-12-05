"""Question attempt tracking model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column, JSON

from typing import List

class PreviousYearProblems(SQLModel, table=True):
    """User marked question"""

    __tablename__ = "previous_year_problems"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question_id: UUID = Field(foreign_key="question.id", index=True)

    exam_detail: List[str] = Field(default=None,sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)


    