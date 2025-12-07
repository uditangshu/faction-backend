"""Main v1 router combining all endpoints"""

from fastapi import APIRouter
from app.api.v1.endpoints.auth import auth
from app.api.v1.endpoints.users import users
from app.api.v1.endpoints.streaks import streaks
from app.api.v1.endpoints.curriculum import questions, classes, subjects, chapter, topics
from app.api.v1.endpoints.analysis import analysis
from app.api.v1.endpoints.attempt import attempt
from app.api.v1.endpoints.pyq import pyq, filtering
from app.api.v1.endpoints.custom_test import custom_test

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

api_router.include_router(custom_test.router)