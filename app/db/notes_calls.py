"""Notes database calls"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, asc

from app.models.notes import Notes
from app.models.Basequestion import Subject, Chapter


async def create_note(
    db: AsyncSession,
    chapter_id: UUID,
    subject_id: UUID,
    file_name: str,
    file_id: str,
    web_view_link: str,
    web_content_link: Optional[str] = None,
) -> Notes:
    """Create a new note"""
    note = Notes(
        chapter_id=chapter_id,
        subject_id=subject_id,
        file_name=file_name,
        file_id=file_id,
        web_view_link=web_view_link,
        web_content_link=web_content_link,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(
    db: AsyncSession,
    note_id: UUID,
) -> bool:
    """Delete a note"""
    result = await db.execute(
        delete(Notes).where(Notes.id == note_id)
    )
    await db.commit()
    return result.rowcount > 0


async def get_note_by_id(
    db: AsyncSession,
    note_id: UUID,
) -> Optional[Notes]:
    """Get a note by ID"""
    result = await db.execute(
        select(Notes).where(Notes.id == note_id)
    )
    return result.scalar_one_or_none()


async def get_notes_by_user_class(
    db: AsyncSession,
    class_id: UUID,
    subject_id: Optional[UUID] = None,
    chapter_id: Optional[UUID] = None,
    sort_order: str = "latest",
    skip: int = 0,
    limit: int = 100,
) -> List[Notes]:
    """
    Get notes filtered by user's class, optionally by subject and chapter
    
    Args:
        db: Database session
        class_id: User's class ID
        subject_id: Optional subject ID to filter by
        chapter_id: Optional chapter ID to filter by
        sort_order: "latest" for newest first, "oldest" for oldest first
        skip: Number of records to skip
        limit: Maximum number of records to return
    
    Returns:
        List of notes
    """
    # Start with subjects in the user's class
    query = (
        select(Notes)
        .join(Subject, Notes.subject_id == Subject.id)
        .where(
            Subject.class_id == class_id,
            Notes.is_active == True,
        )
    )
    
    # Filter by subject if provided
    if subject_id:
        query = query.where(Notes.subject_id == subject_id)
    
    # Filter by chapter if provided
    if chapter_id:
        query = query.where(Notes.chapter_id == chapter_id)
    
    # Apply sorting
    if sort_order == "latest":
        query = query.order_by(desc(Notes.created_at))
    elif sort_order == "oldest":
        query = query.order_by(asc(Notes.created_at))
    else:
        # Default to latest
        query = query.order_by(desc(Notes.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())

