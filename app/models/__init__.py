"""Database models"""

from app.models.user import User, UserRole, ClassLevel, TargetExam, SubscriptionType
from app.models.otp import OTPVerification
from app.models.session import UserSession
from app.models.subject import Subject, Topic, Concept
from app.models.question import Question, QuestionOption, QuestionType, DifficultyLevel
from app.models.attempt import QuestionAttempt
from app.models.streak import UserStudyStats, UserDailyStreak

__all__ = [
    "User",
    "UserRole",
    "ClassLevel",
    "TargetExam",
    "SubscriptionType",
    "OTPVerification",
    "UserSession",
    "Subject",
    "Topic",
    "Concept",
    "Question",
    "QuestionOption",
    "QuestionType",
    "DifficultyLevel",
    "QuestionAttempt",
    "UserStudyStats",
    "UserDailyStreak",
]

