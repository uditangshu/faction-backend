"""Database models"""

from app.models.user import User, UserRole, ClassLevel, TargetExam, SubscriptionType, ContestRank
from app.models.otp import OTPVerification
from app.models.session import UserSession
from app.models.Basequestion import Question, QuestionType, DifficultyLevel, Subject_Type, Class_level, Class, Subject, Chapter
from app.models.attempt import QuestionAttempt
from app.models.streak import UserStudyStats, UserDailyStreak
from app.models.analysis import BookMarkedQuestion
from app.models.pyq import PreviousYearProblems
from app.models.custom_test import CustomTest, CustomTestAnalysis
from app.models.linking import CustomTestQuestion
from app.models.contest import Contest, ContestLeaderboard, ContestQuestions 
from app.models.youtube_video import YouTubeVideo
from app.models.badge import Badge, BadgeCategory
from app.models.weak_topic import UserWeakTopic
__all__ = [
    "User",
    "UserRole",
    "ContestRank",
    "ClassLevel",
    "Class",
    "Subject",
    "Chapter",
    "Subject_Type",
    "Class_level",
    "TargetExam",
    "SubscriptionType",
    "OTPVerification",
    "UserSession",
    "Question",
    "QuestionType",
    "DifficultyLevel",
    "QuestionAttempt",
    "UserStudyStats",
    "UserDailyStreak",
    "BookMarkedQuestion",
    "PreviousYearProblems",
    "CustomTest",
    "CustomTestAnalysis",
    "CustomTestQuestion",
    "Contest",
    "ContestQuestions",
    "ContestLeaderboard",
    "YouTubeVideo",
    "Badge",
    "BadgeCategory",
    "UserWeakTopic",
]

