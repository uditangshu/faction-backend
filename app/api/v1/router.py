"""Main v1 router combining all endpoints"""

from fastapi import APIRouter
from app.api.v1.endpoints.auth import auth
from app.api.v1.endpoints.users import users
from app.api.v1.endpoints.streaks import streaks
from app.api.v1.endpoints.curriculum import questions, classes, subjects, chapter, topics
from app.api.v1.endpoints.analysis import analysis
from app.api.v1.endpoints.attempt import attempt
from app.api.v1.endpoints.pyq import pyq, filtering
from app.api.v1.endpoints.leaderboard import leaderboard, arena_ranking, streak_ranking, contest_ranking
from app.api.v1.endpoints.youtube_video import youtube_video, video_embed
from app.api.v1.endpoints.badge import badge
from app.api.v1.endpoints.weak_topic import weak_topic
from app.api.v1.endpoints.custom_test import custom_test
from app.api.v1.endpoints.contest import contest
from app.api.v1.endpoints.doubt_forum import doubt_forum

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(streaks.router)

# Curriculum routes
api_router.include_router(classes.router)
api_router.include_router(subjects.router)
api_router.include_router(chapter.router)
api_router.include_router(topics.router)
api_router.include_router(questions.router)

# Analysis, Attempt, PYQ routes
api_router.include_router(analysis.router)
api_router.include_router(attempt.router)
api_router.include_router(pyq.router)

api_router.include_router(filtering.router)


# Leaderboard routes
api_router.include_router(leaderboard.router)
api_router.include_router(arena_ranking.router)
api_router.include_router(streak_ranking.router)
api_router.include_router(contest_ranking.router)

# YouTube Video routes
api_router.include_router(youtube_video.router)
api_router.include_router(video_embed.router)

# Badge routes
api_router.include_router(badge.router)

# Weak Topics routes
api_router.include_router(weak_topic.router)

# Custom Test routes
api_router.include_router(custom_test.router)

# Contest routes
api_router.include_router(contest.router)

# Doubt Forum routes
api_router.include_router(doubt_forum.router)