"""Doubt forum service"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from typing import List, Optional

from app.models.doubt_forum import DoubtPost, DoubtComment, DoubtBookmark
from app.db.doubt_forum_calls import (
    create_doubt_post,
    get_doubt_post_by_id,
    get_doubt_posts,
    delete_doubt_post,
    create_doubt_comment,
    get_doubt_comment_by_id,
    delete_doubt_comment,
    increment_doubt_post_likes,
    decrement_doubt_post_likes,
    get_doubt_bookmark_by_user_and_post,
    create_doubt_bookmark,
    delete_doubt_bookmark,
    get_filtered_doubt_posts,
)
from app.integrations.redis_client import RedisService
from app.core.config import settings


class DoubtForumService:
    """Service for managing doubt forum operations"""

    CACHE_PREFIX = "doubt_forum"

    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    async def create_post(
        self,
        user_id: UUID,
        class_id: UUID,
        title: str,
        content: str,
        image_url: Optional[str] = None,
    ) -> DoubtPost:
        """Create a new doubt post and invalidate related caches"""
        post = await create_doubt_post(
            self.db,
            user_id=user_id,
            class_id=class_id,
            title=title,
            content=content,
            image_url=image_url,
        )
        
        # Invalidate all doubt forum caches when new post is created
        if self.redis_service:
            await self._invalidate_doubt_forum_cache()
        
        return post
    
    async def _invalidate_doubt_forum_cache(self):
        """Invalidate all doubt forum caches by deleting all keys matching the pattern"""
        if not self.redis_service:
            return
        
        # Use Redis SCAN to find and delete all keys matching doubt_forum:*
        cursor = 0
        pattern = f"{self.CACHE_PREFIX}:*"
        
        while True:
            cursor, keys = await self.redis_service.client.scan(cursor, match=pattern, count=100)
            
            if keys:
                await self.redis_service.client.delete(*keys)
            
            if cursor == 0:
                break

    async def get_post_by_id(self, post_id: UUID) -> Optional[DoubtPost]:
        """Get a doubt post by ID"""
        return await get_doubt_post_by_id(self.db, post_id)

    async def get_posts(
        self,
        class_id: Optional[UUID] = None,
        is_solved: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
        sort_order: str = "latest",
    ) -> List[DoubtPost]:
        """Get doubt posts with optional filters and pagination (cached globally)"""
        # Build cache key from all filter parameters
        cache_key_parts = [
            self.CACHE_PREFIX,
            "posts",
            str(class_id) if class_id else "all",
            str(is_solved) if is_solved is not None else "all",
            sort_order,
            str(skip),
            str(limit),
        ]
        cache_key = ":".join(cache_key_parts)
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                post_ids = [UUID(pid) for pid in cached]
                if post_ids:
                    result = await self.db.execute(
                        select(DoubtPost).where(DoubtPost.id.in_(post_ids))
                    )
                    posts = list(result.scalars().all())
                    # Sort based on sort_order
                    if sort_order == "latest":
                        posts.sort(key=lambda p: p.created_at, reverse=True)
                    else:
                        posts.sort(key=lambda p: p.created_at)
                    return posts
                return []
        
        # Fetch from database
        posts = await get_doubt_posts(
            self.db,
            class_id=class_id,
            is_solved=is_solved,
            skip=skip,
            limit=limit,
            sort_order=sort_order,
        )
        
        # Cache result
        if self.redis_service:
            post_ids = [str(p.id) for p in posts]
            await self.redis_service.set_value(
                cache_key,
                post_ids,
                expire=settings.LONG_TERM_CACHE_TTL
            )
        
        return posts

    async def delete_post(self, post_id: UUID) -> bool:
        """Delete a doubt post"""
        return await delete_doubt_post(self.db, post_id)

    async def get_filtered_posts(
        self,
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
        """Get filtered doubt posts with advanced filters (cached globally)"""
        # Build cache key from all filter parameters
        # Note: content_search is not included in cache key as it's text search
        # If content_search is provided, skip caching
        if content_search:
            # Skip cache for text search queries
            return await get_filtered_doubt_posts(
                self.db,
                user_id=user_id,
                class_id=class_id,
                content_search=content_search,
                is_solved=is_solved,
                my_posts_only=my_posts_only,
                bookmarked_only=bookmarked_only,
                skip=skip,
                limit=limit,
                sort_order=sort_order,
            )
        
        cache_key_parts = [
            self.CACHE_PREFIX,
            "filtered",
            str(user_id) if user_id else "all",
            str(class_id) if class_id else "all",
            str(is_solved) if is_solved is not None else "all",
            str(my_posts_only),
            str(bookmarked_only),
            sort_order,
            str(skip),
            str(limit),
        ]
        cache_key = ":".join(cache_key_parts)
        
        # Try cache first
        if self.redis_service:
            cached = await self.redis_service.get_value(cache_key)
            if cached is not None:
                post_ids = [UUID(pid) for pid in cached]
                if post_ids:
                    result = await self.db.execute(
                        select(DoubtPost).where(DoubtPost.id.in_(post_ids))
                    )
                    posts = list(result.scalars().all())
                    # Sort based on sort_order
                    if sort_order == "latest":
                        posts.sort(key=lambda p: p.created_at, reverse=True)
                    else:
                        posts.sort(key=lambda p: p.created_at)
                    return posts
                return []
        
        # Fetch from database
        posts = await get_filtered_doubt_posts(
            self.db,
            user_id=user_id,
            class_id=class_id,
            content_search=content_search,
            is_solved=is_solved,
            my_posts_only=my_posts_only,
            bookmarked_only=bookmarked_only,
            skip=skip,
            limit=limit,
            sort_order=sort_order,
        )
        
        # Cache result
        if self.redis_service:
            post_ids = [str(p.id) for p in posts]
            await self.redis_service.set_value(
                cache_key,
                post_ids,
                expire=settings.LONG_TERM_CACHE_TTL
            )
        
        return posts

    async def mark_as_solved(self, post_id: UUID) -> Optional[DoubtPost]:
        """Mark a doubt post as solved"""
        from app.db.doubt_forum_calls import mark_post_as_solved
        return await mark_post_as_solved(self.db, post_id)

    # ==================== Comment Methods ====================

    async def create_comment(
        self,
        user_id: UUID,
        post_id: UUID,
        content: str,
        image_url: Optional[str] = None,
    ) -> DoubtComment:
        """Create a new comment on a doubt post"""
        return await create_doubt_comment(self.db, user_id, post_id, content, image_url)

    async def get_comment_by_id(self, comment_id: UUID) -> Optional[DoubtComment]:
        """Get a comment by ID"""
        return await get_doubt_comment_by_id(self.db, comment_id)

    async def delete_comment(self, comment_id: UUID) -> bool:
        """Delete a comment"""
        return await delete_doubt_comment(self.db, comment_id)

    # ==================== Like Methods ====================

    async def like_post(self, post_id: UUID) -> Optional[DoubtPost]:
        """Like a doubt post (increment likes_count)"""
        return await increment_doubt_post_likes(self.db, post_id)

    async def dislike_post(self, post_id: UUID) -> Optional[DoubtPost]:
        """Dislike a doubt post (decrement likes_count)"""
        return await decrement_doubt_post_likes(self.db, post_id)

    # ==================== Bookmark Methods ====================

    async def toggle_bookmark(
        self,
        user_id: UUID,
        post_id: UUID,
    ) -> tuple[bool, Optional[DoubtBookmark]]:
        """
        Toggle bookmark status for a doubt post.
        Returns (is_bookmarked, bookmark_object)
        """
        existing = await get_doubt_bookmark_by_user_and_post(self.db, user_id, post_id)
        
        if existing:
            # Remove bookmark
            await delete_doubt_bookmark(self.db, user_id, post_id)
            return False, None
        else:
            # Add bookmark
            bookmark = await create_doubt_bookmark(self.db, user_id, post_id)
            return True, bookmark

