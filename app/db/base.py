"""Import all models for Alembic"""

from sqlmodel import SQLModel

# Import all models to ensure they're registered with SQLModel.metadata
from app.models.user import User
from app.models.otp import OTPVerification
from app.models.session import UserSession
from app.models.Basequestion import Question, Subject, Chapter, Class
from app.models.attempt import QuestionAttempt
from app.models.analysis import BookMarkedQuestion
from app.models.pyq import PreviousYearProblems
from app.models.streak import UserStudyStats, UserDailyStreak

__all__ = [
    "SQLModel",
    "Chapter",
    "Class",
    "User",
    "OTPVerification",
    "UserSession",
    "Subject",
    "Question",
    "QuestionOption",
    "QuestionAttempt",
    "UserStudyStats",
    "UserDailyStreak",
    "PreviousYearProblems",
    "BookMarkedQuestion"
]

