"""Streak and calendar schemas"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class StreakResponse(BaseModel):
    """User streak information response"""

    current_streak: int
    longest_streak: int
    last_study_date: str | None
    streak_active: bool
    next_milestone: int
    total_questions_solved: int
    accuracy_rate: float

class StreakRequest(BaseModel):
    """User Streak Information Request"""
    
    

class CalendarDayData(BaseModel):
    """Calendar day data"""

    count: int
    level: int  # 0-4 intensity level


class CalendarSummary(BaseModel):
    """Calendar summary statistics"""

    total_days: int
    active_days: int
    total_questions: int
    average_per_day: float


class CalendarResponse(BaseModel):
    """Study calendar response"""

    year: int
    data: Dict[str, CalendarDayData]
    summary: CalendarSummary

