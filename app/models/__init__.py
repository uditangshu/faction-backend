"""Database models"""

from app.models.user import User, UserRole, TargetExam, SubscriptionType, ContestRank
from app.models.otp import OTPVerification
from app.models.session import UserSession
from app.models.Basequestion import Question, QuestionType, DifficultyLevel, Subject_Type, Class_level, Class, Subject, Chapter
from app.models.attempt import QuestionAttempt
from app.models.streak import UserStudyStats, UserDailyStreak
from app.models.analysis import BookMarkedQuestion
from app.models.pyq import PreviousYearProblems
from app.models.custom_test import CustomTest, CustomTestAnalysis
from app.models.linking import CustomTestQuestion, ScholarshipQuestion
from app.models.contest import Contest, ContestLeaderboard, ContestQuestions 
from app.models.youtube_video import YouTubeVideo, BookmarkedVideo
from app.models.badge import Badge, BadgeCategory
from app.models.weak_topic import UserWeakTopic
from app.models.doubt_forum import DoubtPost, DoubtComment, DoubtBookmark
from app.models.notification import Notification, NotificationType
from app.models.treasure import Treasure
from app.models.notes import Notes
from app.models.user_badge import UserBadge
from app.models.qotd import QOTD
from app.models.scholarship import Scholarship, ScholarshipResult

__all__ = [
    "User",
    "UserRole",
    "ContestRank",
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
    "ScholarshipQuestion",
    "Contest",
    "ContestQuestions",
    "ContestLeaderboard",
    "YouTubeVideo",
    "BookmarkedVideo",
    "Badge",
    "BadgeCategory",
    "UserWeakTopic",
    "DoubtPost",
    "DoubtComment",
    "DoubtBookmark",
    "Notification",
    "NotificationType",
    "Treasure",
    "Notes",
    "UserBadge",
    "QOTD",
    "Scholarship",
    "ScholarshipResult",
]

