"""Treasure database calls"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, asc
from datetime import datetime

from app.models.treasure import Treasure
from app.models.Basequestion import Subject, Chapter


async def create_treasure(
    db: AsyncSession,
    chapter_id: UUID,
    subject_id: UUID,
    image_url: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    order: int = 0,
) -> Treasure:
    """Create a new treasure"""
    treasure = Treasure(
        chapter_id=chapter_id,
        subject_id=subject_id,
        image_url=image_url,
        title=title,
        description=description,
        order=order,
    )
    db.add(treasure)
    await db.commit()
    await db.refresh(treasure)
    return treasure


async def delete_treasure(
    db: AsyncSession,
    treasure_id: UUID,
) -> bool:
    """Delete a treasure"""
    result = await db.execute(
        delete(Treasure).where(Treasure.id == treasure_id)
    )
    await db.commit()
    return result.rowcount > 0


async def get_treasure_by_id(
    db: AsyncSession,
    treasure_id: UUID,
) -> Optional[Treasure]:
    """Get a treasure by ID"""
    result = await db.execute(
        select(Treasure).where(Treasure.id == treasure_id)
    )
    return result.scalar_one_or_none()


async def get_treasures_by_subject(
    db: AsyncSession,
    subject_id: UUID,
    chapter_id: Optional[UUID] = None,
) -> List[Treasure]:
    """Get all treasures for a subject, optionally filtered by chapter"""
    query = select(Treasure).where(
        Treasure.subject_id == subject_id,
        Treasure.is_active == True,
    )
    
    if chapter_id:
        query = query.where(Treasure.chapter_id == chapter_id)
    
    query = query.order_by(Treasure.order, Treasure.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_treasures_by_chapter(
    db: AsyncSession,
    chapter_id: UUID,
) -> List[Treasure]:
    """Get all treasures for a chapter"""
    result = await db.execute(
        select(Treasure)
        .where(
            Treasure.chapter_id == chapter_id,
            Treasure.is_active == True,
        )
        .order_by(Treasure.order, Treasure.created_at)
    )
    return list(result.scalars().all())


async def get_treasures_by_user_class(
    db: AsyncSession,
    class_id: UUID,
    subject_id: Optional[UUID] = None,
    chapter_id: Optional[UUID] = None,
    sort_order: str = "latest",
    skip: int = 0,
    limit: int = 100,
) -> List[Treasure]:
    """
    Get treasures filtered by user's class, optionally by subject and chapter
    
    Args:
        db: Database session
        class_id: User's class ID
        subject_id: Optional subject ID to filter by
        chapter_id: Optional chapter ID to filter by
        sort_order: "latest" for newest first, "oldest" for oldest first
        skip: Number of records to skip
        limit: Maximum number of records to return
    
    Returns:
        List of treasures
    """
    # Start with subjects in the user's class
    query = (
        select(Treasure)
        .join(Subject, Treasure.subject_id == Subject.id)
        .where(
            Subject.class_id == class_id,
            Treasure.is_active == True,
        )
    )
    
    # Filter by subject if provided
    if subject_id:
        query = query.where(Treasure.subject_id == subject_id)
    
    # Filter by chapter if provided
    if chapter_id:
        query = query.where(Treasure.chapter_id == chapter_id)
    
    # Apply sorting
    if sort_order == "latest":
        query = query.order_by(desc(Treasure.created_at))
    elif sort_order == "oldest":
        query = query.order_by(asc(Treasure.created_at))
    else:
        # Default to latest
        query = query.order_by(desc(Treasure.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_treasure(
    db: AsyncSession,
    treasure_id: UUID,
    image_url: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    order: Optional[int] = None,
    is_active: Optional[bool] = None,
    chapter_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
) -> Optional[Treasure]:
    """Update a treasure"""
    treasure = await get_treasure_by_id(db, treasure_id)
    if not treasure:
        return None
    
    if image_url is not None:
        treasure.image_url = image_url
    if title is not None:
        treasure.title = title
    if description is not None:
        treasure.description = description
    if order is not None:
        treasure.order = order
    if is_active is not None:
        treasure.is_active = is_active
    if chapter_id is not None:
        treasure.chapter_id = chapter_id
    if subject_id is not None:
        treasure.subject_id = subject_id
    
    treasure.updated_at = datetime.utcnow()
    db.add(treasure)
    await db.commit()
    await db.refresh(treasure)
    return treasure

