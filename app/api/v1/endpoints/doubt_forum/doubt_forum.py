"""Doubt forum endpoints"""

from uuid import UUID
from datetime import timedelta
from fastapi import APIRouter, Query, File, UploadFile, Form
from typing import Optional
import re

from app.api.v1.dependencies import DoubtForumServiceDep, CurrentUser
from app.schemas.doubt_forum import (
    DoubtPostResponse,
    DoubtPostListResponse,
    DoubtPostDetailResponse,
    DoubtCommentResponse,
    DoubtCommentCreateRequest,
    DoubtLikeResponse,
    DoubtBookmarkResponse,
)
from app.integrations.cloudinary_client import upload_image, delete_image
from app.exceptions.http_exceptions import NotFoundException, BadRequestException


def extract_cloudinary_public_id(image_url: str) -> Optional[str]:
    """
    Extract public_id from Cloudinary URL.
    URL format: https://res.cloudinary.com/{cloud_name}/image/upload/{folder}/{public_id}.{format}
    Returns: {folder}/{public_id} (without extension)
    """
    if not image_url:
        return None
    
    # Pattern to match Cloudinary URL structure
    pattern = r'/(?:v\d+/)?([^/]+/[^/]+)\.(jpg|jpeg|png|gif|webp|svg)'
    match = re.search(pattern, image_url)
    
    if match:
        return match.group(1)
    return None

router = APIRouter(prefix="/doubt-forum", tags=["Doubt Forum"])


@router.post("/posts", response_model=DoubtPostResponse, status_code=201)
async def create_doubt_post(
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
    title: str = Form(..., max_length=200),
    content: str = Form(...),
    class_id: Optional[UUID] = Form(None, description="Class ID (optional, defaults to user's class_id)"),
    image: Optional[UploadFile] = File(None, description="Post image file"),
) -> DoubtPostResponse:
    """Create a new doubt post with optional image upload to Cloudinary"""
    try:
        # Use current_user.class_id if class_id is not provided
        if class_id is None:
            class_id = current_user.class_id
        
        # Handle image upload if provided
        image_url = None
        if image:
            # Validate file type
            if not image.content_type or not image.content_type.startswith('image/'):
                raise BadRequestException("File must be an image")
            
            # Upload image to Cloudinary
            try:
                image_url = await upload_image(
                    image.file,
                    folder=f"doubt-posts/{current_user.id}",
                    public_id=None  # Let Cloudinary generate the ID
                )
            except Exception as e:
                raise BadRequestException(f"Failed to upload image: {str(e)}")
        
        # Create the post
        post = await doubt_forum_service.create_post(
            user_id=current_user.id,
            class_id=class_id,
            title=title,
            content=content,
            image_url=image_url,
        )
        
        return DoubtPostResponse.model_validate(post)
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create post: {str(e)}")


@router.get("/posts", response_model=DoubtPostListResponse)
async def get_doubt_posts(
    doubt_forum_service: DoubtForumServiceDep,
    class_id: Optional[UUID] = Query(None, description="Filter by class ID (UUID)"),
    is_solved: Optional[bool] = Query(None, description="Filter by solved status"),
    skip: int = Query(0, ge=0, description="Number of records to skip (for pagination)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    sort_order: str = Query("latest", description="Sort order: 'latest' or 'oldest'"),
) -> DoubtPostListResponse:
    """Get all doubt posts with infinite scrolling (pagination)"""
    if sort_order not in ["latest", "oldest"]:
        raise BadRequestException("sort_order must be 'latest' or 'oldest'")
    
    # Get posts
    posts = await doubt_forum_service.get_posts(
        class_id=class_id,
        is_solved=is_solved,
        skip=skip,
        limit=limit + 1,  # Fetch one extra to check if there are more
        sort_order=sort_order,
    )
    
    # Check if there are more posts
    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]  # Remove the extra post
    
    return DoubtPostListResponse(
        posts=[DoubtPostResponse.model_validate(p) for p in posts],
        total=len(posts),
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


# ==================== Filter API ====================
# NOTE: This MUST be defined BEFORE /posts/{post_id} for correct route matching

@router.get("/posts/filter", response_model=DoubtPostListResponse)
async def filter_doubt_posts(
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
    content_search: Optional[str] = Query(None, description="Search in title and content"),
    is_solved: Optional[bool] = Query(None, description="Filter by solved status (true for solved, false for unsolved)"),
    my_posts_only: bool = Query(False, description="Show only posts created by current user"),
    bookmarked_only: bool = Query(False, description="Show only bookmarked posts"),
    skip: int = Query(0, ge=0, description="Number of records to skip (for pagination)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    sort_order: str = Query("latest", description="Sort order: 'latest' or 'oldest'"),
) -> DoubtPostListResponse:
    """
    Filter doubt posts with advanced filters:
    - content_search: Search in title and content
    - is_solved: Filter by solved/unsolved status
    - my_posts_only: Show only posts created by current user
    - bookmarked_only: Show only bookmarked posts
    """
    if sort_order not in ["latest", "oldest"]:
        raise BadRequestException("sort_order must be 'latest' or 'oldest'")
    
    # Get filtered posts - filtered by user's class_id
    posts = await doubt_forum_service.get_filtered_posts(
        user_id=current_user.id,
        class_id=current_user.class_id,
        content_search=content_search,
        is_solved=is_solved,
        my_posts_only=my_posts_only,
        bookmarked_only=bookmarked_only,
        skip=skip,
        limit=limit + 1,  # Fetch one extra to check if there are more
        sort_order=sort_order,
    )
    
    # Check if there are more posts
    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]  # Remove the extra post
    
    # Get user's timezone offset (in minutes from UTC)
    timezone_offset = current_user.timezone_offset or 330  # Default to IST if None
    
    # Adjust datetime fields using user's timezone offset
    adjusted_posts = []
    for post in posts:
        # Convert post to dict and adjust datetime fields
        post_dict = post.model_dump() if hasattr(post, 'model_dump') else {
            'id': post.id,
            'user_id': post.user_id,
            'class_id': post.class_id,
            'title': post.title,
            'content': post.content,
            'image_url': post.image_url,
            'is_solved': post.is_solved,
            'likes_count': post.likes_count,
            'created_at': post.created_at,
            'updated_at': post.updated_at,
        }
        # Adjust created_at and updated_at with timezone offset
        if post_dict.get('created_at'):
            post_dict['created_at'] = post_dict['created_at'] + timedelta(minutes=timezone_offset)
        if post_dict.get('updated_at'):
            post_dict['updated_at'] = post_dict['updated_at'] + timedelta(minutes=timezone_offset)
        adjusted_posts.append(DoubtPostResponse.model_validate(post_dict))
    
    return DoubtPostListResponse(
        posts=adjusted_posts,
        total=len(adjusted_posts),
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.get("/posts/{post_id}", response_model=DoubtPostDetailResponse)
async def get_doubt_post_by_id(
    post_id: UUID,
    doubt_forum_service: DoubtForumServiceDep,
) -> DoubtPostDetailResponse:
    """Get a doubt post by ID with its comments"""
    post = await doubt_forum_service.get_post_by_id(post_id)
    if not post:
        raise NotFoundException(f"Post with ID {post_id} not found")
    
    # Convert comments to response format
    comments = [
        DoubtCommentResponse.model_validate(comment) for comment in post.comments
    ]
    
    post_dict = DoubtPostResponse.model_validate(post).model_dump()
    post_dict["comments"] = comments
    
    return DoubtPostDetailResponse(**post_dict)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_doubt_post(
    post_id: UUID,
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
) -> None:
    """Delete a doubt post (only by the post owner) and delete image from Cloudinary if exists"""
    post = await doubt_forum_service.get_post_by_id(post_id)
    if not post:
        raise NotFoundException(f"Post with ID {post_id} not found")
    
    # Check if user owns the post
    if post.user_id != current_user.id:
        raise NotFoundException(f"Post with ID {post_id} not found")
    
    # Delete image from Cloudinary if exists
    if post.image_url:
        try:
            public_id = extract_cloudinary_public_id(post.image_url)
            if public_id:
                await delete_image(public_id)
        except Exception:
            # Log but don't fail if image deletion fails
            pass
    
    deleted = await doubt_forum_service.delete_post(post_id)
    if not deleted:
        raise NotFoundException(f"Post with ID {post_id} not found")


@router.patch("/posts/{post_id}/solve", response_model=DoubtPostResponse)
async def mark_post_as_solved(
    post_id: UUID,
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
) -> DoubtPostResponse:
    """Mark a doubt post as solved (only by the post owner)"""
    post = await doubt_forum_service.get_post_by_id(post_id)
    if not post:
        raise NotFoundException(f"Post with ID {post_id} not found")
    
    # Check if user owns the post
    if post.user_id != current_user.id:
        raise BadRequestException("Only the post owner can mark it as solved")
    
    # Update is_solved to True
    updated_post = await doubt_forum_service.mark_as_solved(post_id)
    if not updated_post:
        raise NotFoundException(f"Post with ID {post_id} not found")
    
    return DoubtPostResponse.model_validate(updated_post)


# ==================== Comment APIs ====================

@router.post("/comments", response_model=DoubtCommentResponse, status_code=201)
async def create_doubt_comment(
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
    post_id: UUID = Form(...),
    content: str = Form(...),
    image: Optional[UploadFile] = File(None, description="Comment image file"),
) -> DoubtCommentResponse:
    """Create a comment on a doubt post with optional image upload to Cloudinary"""
    try:
        # Verify post exists
        post = await doubt_forum_service.get_post_by_id(post_id)
        if not post:
            raise NotFoundException(f"Post with ID {post_id} not found")
        
        # Handle image upload if provided
        image_url = None
        if image:
            # Validate file type
            if not image.content_type or not image.content_type.startswith('image/'):
                raise BadRequestException("File must be an image")
            
            # Upload image to Cloudinary
            try:
                image_url = await upload_image(
                    image.file,
                    folder=f"doubt-comments/{current_user.id}",
                    public_id=None  # Let Cloudinary generate the ID
                )
            except Exception as e:
                raise BadRequestException(f"Failed to upload image: {str(e)}")
        
        comment = await doubt_forum_service.create_comment(
            user_id=current_user.id,
            post_id=post_id,
            content=content,
            image_url=image_url,
        )
        
        return DoubtCommentResponse.model_validate(comment)
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create comment: {str(e)}")


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_doubt_comment(
    comment_id: UUID,
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
) -> None:
    """Delete a comment (only by the comment owner) and delete image from Cloudinary if exists"""
    comment = await doubt_forum_service.get_comment_by_id(comment_id)
    if not comment:
        raise NotFoundException(f"Comment with ID {comment_id} not found")
    
    # Check if user owns the comment
    if comment.user_id != current_user.id:
        raise NotFoundException(f"Comment with ID {comment_id} not found")
    
    # Delete image from Cloudinary if exists
    if comment.image_url:
        try:
            public_id = extract_cloudinary_public_id(comment.image_url)
            if public_id:
                await delete_image(public_id)
        except Exception:
            # Log but don't fail if image deletion fails
            pass
    
    deleted = await doubt_forum_service.delete_comment(comment_id)
    if not deleted:
        raise NotFoundException(f"Comment with ID {comment_id} not found")


# ==================== Like APIs ====================

@router.post("/posts/{post_id}/like", response_model=DoubtLikeResponse)
async def like_doubt_post(
    post_id: UUID,
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
) -> DoubtLikeResponse:
    """Like a doubt post (increment likes_count)"""
    try:
        # Verify post exists
        post = await doubt_forum_service.get_post_by_id(post_id)
        if not post:
            raise NotFoundException(f"Post with ID {post_id} not found")
        
        # Increment likes
        updated_post = await doubt_forum_service.like_post(post_id)
        if not updated_post:
            raise NotFoundException(f"Post with ID {post_id} not found")
        
        return DoubtLikeResponse(likes_count=updated_post.likes_count, is_liked=True)
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to like post: {str(e)}")


@router.post("/posts/{post_id}/dislike", response_model=DoubtLikeResponse)
async def dislike_doubt_post(
    post_id: UUID,
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
) -> DoubtLikeResponse:
    """Dislike a doubt post (decrement likes_count)"""
    try:
        # Verify post exists
        post = await doubt_forum_service.get_post_by_id(post_id)
        if not post:
            raise NotFoundException(f"Post with ID {post_id} not found")
        
        # Decrement likes
        updated_post = await doubt_forum_service.dislike_post(post_id)
        if not updated_post:
            raise NotFoundException(f"Post with ID {post_id} not found")
        
        return DoubtLikeResponse(likes_count=updated_post.likes_count, is_liked=False)
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to dislike post: {str(e)}")


# ==================== Bookmark APIs ====================

@router.post("/posts/{post_id}/bookmark", response_model=DoubtBookmarkResponse)
async def toggle_doubt_bookmark(
    post_id: UUID,
    doubt_forum_service: DoubtForumServiceDep,
    current_user: CurrentUser,
) -> DoubtBookmarkResponse:
    """Bookmark or remove bookmark from a doubt post"""
    try:
        # Verify post exists
        post = await doubt_forum_service.get_post_by_id(post_id)
        if not post:
            raise NotFoundException(f"Post with ID {post_id} not found")
        
        # Toggle bookmark
        is_bookmarked, _ = await doubt_forum_service.toggle_bookmark(
            user_id=current_user.id,
            post_id=post_id,
        )
        
        return DoubtBookmarkResponse(is_bookmarked=is_bookmarked)
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to toggle bookmark: {str(e)}")
