"""Question attempt database calls"""

from uuid import UUID
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func, and_
from typing import List
from app.models.attempt import QuestionAttempt
from app.models.streak import UserStudyStats, UserDailyStreak


async def create_attempt(
    db: AsyncSession,
    user_id: UUID,
    question_id: UUID,
    user_answer: List[str],
    is_correct: bool,
    marks_obtained: int,
    time_taken: int,
    hint_used: bool,
) -> QuestionAttempt:
    """Create a new question attempt and update streak if answer is correct.
    This is transactional - if any operation fails, everything is rolled back.
    """
    try:
        # Create attempt
        attempt = QuestionAttempt(
            user_id=user_id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct,
            marks_obtained=marks_obtained,
            time_taken=time_taken,
            hint_used=hint_used
        )
        db.add(attempt)
        
        # Update streak only if answer is correct
        if is_correct:
            # Get or create user stats
            result = await db.execute(select(UserStudyStats).where(UserStudyStats.user_id == user_id))
            stats = result.scalar_one_or_none()
            
            if not stats:
                stats = UserStudyStats(user_id=user_id)
                db.add(stats)
            
            today = date.today()
            
            # Get or create today's streak record
            streak_result = await db.execute(
                select(UserDailyStreak).where(
                    and_(UserDailyStreak.user_id == user_id, UserDailyStreak.streak_date == today)
                )
            )
            daily_streak = streak_result.scalar_one_or_none()
            
            if not daily_streak:
                daily_streak = UserDailyStreak(
                    user_id=user_id,
                    streak_date=today,
                    problems_solved=1,
                    first_solve_time=datetime.utcnow(),
                    last_solve_time=datetime.utcnow(),
                    streak_maintained=True,
                )
                db.add(daily_streak)
                
                # Update streak count
                if stats.last_study_date == today - timedelta(days=1):
                    # Consecutive day
                    stats.current_study_streak += 1
                elif stats.last_study_date != today:
                    # Streak broken, start new
                    stats.current_study_streak = 1
                
                stats.last_study_date = today
            else:
                # Update existing daily streak
                daily_streak.problems_solved += 1
                daily_streak.last_solve_time = datetime.utcnow()
            
            # Update overall stats
            stats.questions_solved += 1
            stats.total_attempts += 1
            
            # Update longest streak
            if stats.current_study_streak > stats.longest_study_streak:
                stats.longest_study_streak = stats.current_study_streak
            
            # Recalculate accuracy
            # Count correct attempts (the current attempt hasn't been committed yet, so we add 1 if correct)
            correct_attempts_result = await db.execute(
                select(func.count(QuestionAttempt.id)).where(
                    and_(QuestionAttempt.user_id == user_id, QuestionAttempt.is_correct == True)
                )
            )
            correct_attempts = (correct_attempts_result.scalar() or 0) + 1  # Add 1 for current correct attempt
            if stats.total_attempts > 0:
                stats.accuracy_rate = (correct_attempts / stats.total_attempts) * 100
            
            stats.updated_at = datetime.utcnow()
        
        # Commit both attempt and streak updates together
        await db.commit()
        await db.refresh(attempt)
        return attempt
    except Exception as e:
        # Rollback transaction on any error
        await db.rollback()
        raise e


async def remove_attempt(
        db: AsyncSession,
        attempt_id: UUID,
):
    stmt= delete(QuestionAttempt).where(QuestionAttempt.id == attempt_id)
    await db.execute(stmt)


async def update_attempt(
        db: AsyncSession,
        updated_attempt: QuestionAttempt,
) -> QuestionAttempt:
    
    db.merge(updated_attempt)
    await db.commit()
    await db.refresh(updated_attempt)
    return updated_attempt