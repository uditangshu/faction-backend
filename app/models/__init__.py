"""Database models"""

from app.models.user import User, UserRole, ClassLevel, TargetExam, SubscriptionType, ContestRank
from app.models.otp import OTPVerification
from app.models.session import UserSession
from app.models.Basequestion import Question, QuestionType, DifficultyLevel, Subject_Type, Class_level, Class, Subject, Chapter
from app.models.attempt import QuestionAttempt
from app.models.streak import UserStudyStats, UserDailyStreak
from app.models.analysis import BookMarkedQuestion
from app.models.pyq import PreviousYearProblems
from app.models.custom_test import CustomTest, CustomTestAnalysis, CustomTestQuestion
from app.models.contest import Contest, ContestSubmissionAnalytics, ContestLeaderboard, ContestQuestions 
from app.models.youtube_video import YouTubeVideo
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
    "ContestSubmissionAnalytics",
    "ContestQuestions",
    "ContestLeaderboard",
    "YouTubeVideo"
]

