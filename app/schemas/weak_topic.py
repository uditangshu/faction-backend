"""Weak topics schemas"""

from datetime import datetime
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel


class WeakTopicResponse(BaseModel):
    """Weak topic response"""
    id: UUID
    user_id: UUID
    topic_id: UUID
    total_attempt: int
    incorrect_attempts: int
    correct_attempts: int
    weakness_score: float
    last_updated: datetime

    class Config:
        from_attributes = True


class WeakTopicListResponse(BaseModel):
    """List of weak topics response"""
    weak_topics: List[WeakTopicResponse]
    total: int
    skip: int
    limit: int

