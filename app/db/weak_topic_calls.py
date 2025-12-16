"""Weak topics database calls"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_

from app.models.weak_topic import UserWeakTopic


# ==================== CRUD Operations ====================

async def create_user_weak_topic(
    db: AsyncSession,
    user_id: UUID,
    topic_id: UUID,
    total_attempt: int = 0,
    incorrect_attempts: int = 0,
    correct_attempts: int = 0,
    weakness_score: float = 0.0,
) -> UserWeakTopic:
    """Create a new user weak topic record"""
    weak_topic = UserWeakTopic(
        user_id=user_id,
        topic_id=topic_id,
        total_attempt=total_attempt,
        incorrect_attempts=incorrect_attempts,
        correct_attempts=correct_attempts,
        weakness_score=weakness_score,
        last_updated=datetime.now(),
    )
    db.add(weak_topic)
    await db.commit()
    await db.refresh(weak_topic)
    return weak_topic


async def get_user_weak_topic_by_id(
    db: AsyncSession,
    weak_topic_id: UUID,
) -> Optional[UserWeakTopic]:
    """Get a user weak topic by ID"""
    return await db.get(UserWeakTopic, weak_topic_id)


async def get_user_weak_topic_by_user_and_topic(
    db: AsyncSession,
    user_id: UUID,
    topic_id: UUID,
) -> Optional[UserWeakTopic]:
    """Get a user weak topic by user_id and topic_id"""
    result = await db.execute(
        select(UserWeakTopic).where(
            and_(
                UserWeakTopic.user_id == user_id,
                UserWeakTopic.topic_id == topic_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_user_weak_topics(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
    min_weakness_score: float = 0.0,
) -> tuple[List[UserWeakTopic], int]:
    """Get all weak topics for a user with pagination"""
    # Count query
    count_query = select(func.count(UserWeakTopic.id)).where(
        and_(
            UserWeakTopic.user_id == user_id,
            UserWeakTopic.weakness_score >= min_weakness_score,
        )
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Data query
    query = (
        select(UserWeakTopic)
        .where(
            and_(
                UserWeakTopic.user_id == user_id,
                UserWeakTopic.weakness_score >= min_weakness_score,
            )
        )
        .order_by(UserWeakTopic.weakness_score.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_user_weak_topic(
    db: AsyncSession,
    weak_topic: UserWeakTopic,
) -> UserWeakTopic:
    """Update an existing user weak topic"""
    weak_topic.last_updated = datetime.now()
    db.add(weak_topic)
    await db.commit()
    await db.refresh(weak_topic)
    return weak_topic


async def upsert_user_weak_topic(
    db: AsyncSession,
    user_id: UUID,
    topic_id: UUID,
    total_attempt: int,
    incorrect_attempts: int,
    correct_attempts: int,
    weakness_score: float,
) -> UserWeakTopic:
    """Insert or update user weak topic (upsert)"""
    existing = await get_user_weak_topic_by_user_and_topic(db, user_id, topic_id)
    
    if existing:
        existing.total_attempt = total_attempt
        existing.incorrect_attempts = incorrect_attempts
        existing.correct_attempts = correct_attempts
        existing.weakness_score = weakness_score
        existing.last_updated = datetime.now()
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        return await create_user_weak_topic(
            db,
            user_id=user_id,
            topic_id=topic_id,
            total_attempt=total_attempt,
            incorrect_attempts=incorrect_attempts,
            correct_attempts=correct_attempts,
            weakness_score=weakness_score,
        )


async def delete_user_weak_topic(
    db: AsyncSession,
    weak_topic_id: UUID,
) -> bool:
    """Delete a user weak topic by ID"""
    result = await db.execute(
        delete(UserWeakTopic).where(UserWeakTopic.id == weak_topic_id)
    )
    await db.commit()
    return result.rowcount > 0


async def delete_user_weak_topic_by_user_and_topic(
    db: AsyncSession,
    user_id: UUID,
    topic_id: UUID,
) -> bool:
    """Delete a user weak topic by user_id and topic_id"""
    result = await db.execute(
        delete(UserWeakTopic).where(
            and_(
                UserWeakTopic.user_id == user_id,
                UserWeakTopic.topic_id == topic_id,
            )
        )
    )
    await db.commit()
    return result.rowcount > 0


async def delete_all_user_weak_topics(
    db: AsyncSession,
    user_id: UUID,
) -> int:
    """Delete all weak topics for a user"""
    result = await db.execute(
        delete(UserWeakTopic).where(UserWeakTopic.user_id == user_id)
    )
    await db.commit()
    return result.rowcount

