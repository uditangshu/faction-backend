"""Main v1 router combining all endpoints"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, questions, streaks

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(questions.router)
api_router.include_router(streaks.router)
