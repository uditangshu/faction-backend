"""Doubt forum database calls"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models.doubt_forum import DoubtPost, DoubtComment, DoubtBookmark


async def create_doubt_post(
    db: AsyncSession,
    user_id: UUID,
    class_id: UUID,
    title: str,
    content: str,
    image_url: Optional[str] = None,
) -> DoubtPost:
    """Create a new doubt post"""
    post = DoubtPost(
        user_id=user_id,
        class_id=class_id,
        title=title,
        content=content,
        image_url=image_url,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def get_doubt_post_by_id(
    db: AsyncSession,
    post_id: UUID,
) -> Optional[DoubtPost]:
    """Get a doubt post by ID with comments"""
    result = await db.execute(
        select(DoubtPost)
        .where(DoubtPost.id == post_id)
        .options(selectinload(DoubtPost.comments))
    )
    return result.scalar_one_or_none()


async def get_doubt_posts(
    db: AsyncSession,
    class_id: Optional[UUID] = None,
    is_solved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    sort_order: str = "latest",
) -> List[DoubtPost]:
    """Get doubt posts with optional filters and pagination"""
    query = select(DoubtPost)
    
    # Apply filters
    conditions = []
    if class_id:
        conditions.append(DoubtPost.class_id == class_id)
    if is_solved is not None:
        conditions.append(DoubtPost.is_solved == is_solved)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply sorting
    if sort_order == "latest":
        query = query.order_by(desc(DoubtPost.created_at))
    elif sort_order == "oldest":
        query = query.order_by(asc(DoubtPost.created_at))
    else:
        query = query.order_by(desc(DoubtPost.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_filtered_doubt_posts(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    class_id: Optional[UUID] = None,
    content_search: Optional[str] = None,
    is_solved: Optional[bool] = None,
    my_posts_only: bool = False,
    bookmarked_only: bool = False,
    skip: int = 0,
    limit: int = 20,
    sort_order: str = "latest",
) -> List[DoubtPost]:
    """Get filtered doubt posts with advanced filters"""
    query = select(DoubtPost).distinct()
    
    # Apply filters
    conditions = []
    
    # Filter by class_id (required)
    if class_id:
        conditions.append(DoubtPost.class_id == class_id)
    
    # Content search (search in title and content)
    if content_search:
        search_pattern = f"%{content_search}%"
        conditions.append(
            or_(
                DoubtPost.title.ilike(search_pattern),
                DoubtPost.content.ilike(search_pattern)
            )
        )
    
    # Solved/unsolved filter
    if is_solved is not None:
        conditions.append(DoubtPost.is_solved == is_solved)
    
    # My posts only filter
    if my_posts_only and user_id:
        conditions.append(DoubtPost.user_id == user_id)
    
    # Bookmarked posts only filter
    if bookmarked_only and user_id:
        subquery = select(DoubtBookmark.post_id).where(
            DoubtBookmark.user_id == user_id
        )
        conditions.append(DoubtPost.id.in_(subquery))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply sorting
    if sort_order == "latest":
        query = query.order_by(desc(DoubtPost.created_at))
    elif sort_order == "oldest":
        query = query.order_by(asc(DoubtPost.created_at))
    else:
        query = query.order_by(desc(DoubtPost.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_doubt_post(
    db: AsyncSession,
    post_id: UUID,
) -> bool:
    """Delete a doubt post by ID"""
    post = await get_doubt_post_by_id(db, post_id)
    if not post:
        return False
    
    stmt = delete(DoubtPost).where(DoubtPost.id == post_id)
    await db.execute(stmt)
    await db.commit()
    return True


async def mark_post_as_solved(
    db: AsyncSession,
    post_id: UUID,
) -> Optional[DoubtPost]:
    """Mark a doubt post as solved"""
    post = await get_doubt_post_by_id(db, post_id)
    if not post:
        return None
    
    post.is_solved = True
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


# ==================== Comment Functions ====================

async def create_doubt_comment(
    db: AsyncSession,
    user_id: UUID,
    post_id: UUID,
    content: str,
    image_url: Optional[str] = None,
) -> DoubtComment:
    """Create a new comment on a doubt post"""
    comment = DoubtComment(
        user_id=user_id,
        post_id=post_id,
        content=content,
        image_url=image_url,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def get_doubt_comment_by_id(
    db: AsyncSession,
    comment_id: UUID,
) -> Optional[DoubtComment]:
    """Get a doubt comment by ID"""
    result = await db.execute(
        select(DoubtComment).where(DoubtComment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def delete_doubt_comment(
    db: AsyncSession,
    comment_id: UUID,
) -> bool:
    """Delete a doubt comment by ID"""
    comment = await get_doubt_comment_by_id(db, comment_id)
    if not comment:
        return False
    
    stmt = delete(DoubtComment).where(DoubtComment.id == comment_id)
    await db.execute(stmt)
    await db.commit()
    return True


# ==================== Like Functions ====================

async def increment_doubt_post_likes(
    db: AsyncSession,
    post_id: UUID,
) -> Optional[DoubtPost]:
    """Increment likes_count for a doubt post"""
    post = await get_doubt_post_by_id(db, post_id)
    if not post:
        return None
    
    post.likes_count += 1
    post.updated_at = datetime.utcnow()
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def decrement_doubt_post_likes(
    db: AsyncSession,
    post_id: UUID,
) -> Optional[DoubtPost]:
    """Decrement likes_count for a doubt post"""
    post = await get_doubt_post_by_id(db, post_id)
    if not post:
        return None
    
    post.likes_count = max(0, post.likes_count - 1)  # Ensure it doesn't go below 0
    post.updated_at = datetime.utcnow()
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


# ==================== Bookmark Functions ====================

async def get_doubt_bookmark_by_user_and_post(
    db: AsyncSession,
    user_id: UUID,
    post_id: UUID,
) -> Optional[DoubtBookmark]:
    """Check if a user has bookmarked a specific doubt post"""
    result = await db.execute(
        select(DoubtBookmark).where(
            DoubtBookmark.user_id == user_id,
            DoubtBookmark.post_id == post_id,
        )
    )
    return result.scalar_one_or_none()


async def create_doubt_bookmark(
    db: AsyncSession,
    user_id: UUID,
    post_id: UUID,
) -> DoubtBookmark:
    """Create a bookmark for a doubt post"""
    bookmark = DoubtBookmark(
        user_id=user_id,
        post_id=post_id,
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)
    return bookmark


async def delete_doubt_bookmark(
    db: AsyncSession,
    user_id: UUID,
    post_id: UUID,
) -> bool:
    """Delete a bookmark for a doubt post"""
    bookmark = await get_doubt_bookmark_by_user_and_post(db, user_id, post_id)
    if not bookmark:
        return False
    
    stmt = delete(DoubtBookmark).where(
        DoubtBookmark.user_id == user_id,
        DoubtBookmark.post_id == post_id,
    )
    await db.execute(stmt)
    await db.commit()
    return True

