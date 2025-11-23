"""Import all models for Alembic"""

from sqlmodel import SQLModel

# Import all models to ensure they're registered with SQLModel.metadata
from app.models.user import User
from app.models.otp import OTPVerification
from app.models.session import UserSession
from app.models.subject import Subject, Topic, Concept
from app.models.question import Question, QuestionOption
from app.models.attempt import QuestionAttempt
from app.models.streak import UserStudyStats, UserDailyStreak

__all__ = [
    "SQLModel",
    "User",
    "OTPVerification",
    "UserSession",
    "Subject",
    "Topic",
    "Concept",
    "Question",
    "QuestionOption",
    "QuestionAttempt",
    "UserStudyStats",
    "UserDailyStreak",
]

