"""Question attempt tracking model"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel

class BookMarkedQuestion(SQLModel, table=True):
    """User marked question"""

    __tablename__ = "question_bookmarked"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    question_id: UUID = Field(foreign_key="question.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
