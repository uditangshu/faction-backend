"""Custom Test Making model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Basequestion import Question
    from custom_test import CustomTest
    from contest import Contest

class CustomTestQuestion(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    test_id: UUID = Field(foreign_key="customtest.id", index=True)
    question_id: UUID = Field(foreign_key="question.id", index=True)

    test: "CustomTest" = Relationship(back_populates="questions")
    question: "Question" = Relationship(back_populates="tests")

class ContestQuestions(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    contest_id: UUID = Field(foreign_key="contest.id", index=True)
    question_id: UUID = Field(foreign_key="question.id", index=True)

    contest: "Contest" = Relationship(back_populates="questions")
    question: "Question" = Relationship(back_populates="contest")