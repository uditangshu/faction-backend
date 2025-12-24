"""Bookmarked Video endpoints"""

from uuid import UUID
from fastapi import APIRouter

from app.api.v1.dependencies import BookmarkedVideoServiceDep, CurrentUser
from app.schemas.bookmarked_video import (
    BookmarkedVideoCreateRequest,
    BookmarkedVideoResponse,
    BookmarkedVideoListResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException, ConflictException
from app.schemas.youtube_video import YouTubeVideoResponse

router = APIRouter(prefix="/bookmarked-videos", tags=["Bookmarked Videos"])


@router.post("/", response_model=BookmarkedVideoResponse, status_code=201)
async def create_bookmark(
    request: BookmarkedVideoCreateRequest,
    current_user: CurrentUser,
    bookmarked_video_service: BookmarkedVideoServiceDep,
) -> BookmarkedVideoResponse:
    """Create a new bookmark"""
    try:
        bookmark = await bookmarked_video_service.create_bookmark(
            current_user.id, request.youtube_video_id
        )
        return BookmarkedVideoResponse(
            id=bookmark.id,
            user_id=bookmark.user_id,
            youtube_video_id=bookmark.youtube_video_id,
            created_at=str(bookmark.created_at),
        )
    except ConflictException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create bookmark: {str(e)}")


@router.get("/", response_model=BookmarkedVideoListResponse)
async def get_bookmarks(
    current_user: CurrentUser,
    bookmarked_video_service: BookmarkedVideoServiceDep,
) -> BookmarkedVideoListResponse:
    """Get all bookmarks for the current user"""
    
    bookmarks = await bookmarked_video_service.get_bookmarks_by_user_id(current_user.id)
    return BookmarkedVideoListResponse(
        bookmarks=[
            BookmarkedVideoResponse(
                id=b.id,
                user_id=b.user_id,
                youtube_video_id=b.youtube_video_id,
                created_at=str(b.created_at),
                youtube_video=YouTubeVideoResponse.model_validate(v),
            )
            for b, v in bookmarks
        ],
        total=len(bookmarks),
    )


@router.delete("/{youtube_video_id}", status_code=204)
async def delete_bookmark(
    youtube_video_id: UUID,
    current_user: CurrentUser,
    bookmarked_video_service: BookmarkedVideoServiceDep,
) -> None:
    """Delete a bookmark"""
    deleted = await bookmarked_video_service.delete_bookmark(
        current_user.id, youtube_video_id
    )
    if not deleted:
        raise NotFoundException(f"Bookmark not found")

