"""Bookmark/Analysis endpoints"""

from uuid import UUID
from fastapi import APIRouter

from app.api.v1.dependencies import AnalysisServiceDep, CurrentUser
from app.schemas.question import (
    BookmarkCreateRequest,
    BookmarkResponse,
    BookmarkListResponse,
    BookmarkToggleResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException, ConflictException

router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])


@router.post("/", response_model=BookmarkResponse, status_code=201)
async def create_bookmark(
    analysis_service: AnalysisServiceDep,
    current_user: CurrentUser,
    request: BookmarkCreateRequest,
) -> BookmarkResponse:
    """Create a new bookmark for a question"""
    # Check if already bookmarked
    existing = await analysis_service.get_bookmark_by_user_and_question(
        current_user.id, request.question_id
    )
    if existing:
        raise ConflictException("Question is already bookmarked")
    
    try:
        bookmark = await analysis_service.create_bookmark(
            user_id=current_user.id,
            question_id=request.question_id,
        )
        return BookmarkResponse(
            id=bookmark.id,
            user_id=bookmark.user_id,
            question_id=bookmark.question_id,
            created_at=str(bookmark.created_at),
        )
    except Exception as e:
        raise BadRequestException(f"Failed to create bookmark: {str(e)}")


@router.get("/", response_model=BookmarkListResponse)
async def get_my_bookmarks(
    analysis_service: AnalysisServiceDep,
    current_user: CurrentUser,
) -> BookmarkListResponse:
    """Get all bookmarks for the current user"""
    bookmarks = await analysis_service.get_user_bookmarks(current_user.id)
    return BookmarkListResponse(
        bookmarks=[
            BookmarkResponse(
                id=b.id,
                user_id=b.user_id,
                question_id=b.question_id,
                created_at=str(b.created_at),
            )
            for b in bookmarks
        ],
        total=len(bookmarks),
    )


@router.get("/{bookmark_id}", response_model=BookmarkResponse)
async def get_bookmark(
    analysis_service: AnalysisServiceDep,
    current_user: CurrentUser,
    bookmark_id: UUID,
) -> BookmarkResponse:
    """Get a specific bookmark by ID"""
    bookmark = await analysis_service.get_bookmark_by_id(bookmark_id)
    if not bookmark:
        raise NotFoundException(f"Bookmark with ID {bookmark_id} not found")
    
    # Ensure user owns this bookmark
    if bookmark.user_id != current_user.id:
        raise NotFoundException(f"Bookmark with ID {bookmark_id} not found")
    
    return BookmarkResponse(
        id=bookmark.id,
        user_id=bookmark.user_id,
        question_id=bookmark.question_id,
        created_at=str(bookmark.created_at),
    )


@router.get("/question/{question_id}/status", response_model=BookmarkToggleResponse)
async def check_bookmark_status(
    analysis_service: AnalysisServiceDep,
    current_user: CurrentUser,
    question_id: UUID,
) -> BookmarkToggleResponse:
    """Check if a question is bookmarked by the current user"""
    bookmark = await analysis_service.get_bookmark_by_user_and_question(
        current_user.id, question_id
    )
    
    if bookmark:
        return BookmarkToggleResponse(
            is_bookmarked=True,
            bookmark=BookmarkResponse(
                id=bookmark.id,
                user_id=bookmark.user_id,
                question_id=bookmark.question_id,
                created_at=str(bookmark.created_at),
            ),
        )
    return BookmarkToggleResponse(is_bookmarked=False, bookmark=None)


@router.post("/question/{question_id}/toggle", response_model=BookmarkToggleResponse)
async def toggle_bookmark(
    analysis_service: AnalysisServiceDep,
    current_user: CurrentUser,
    question_id: UUID,
) -> BookmarkToggleResponse:
    """Toggle bookmark status for a question"""
    try:
        is_bookmarked, bookmark = await analysis_service.toggle_bookmark(
            user_id=current_user.id,
            question_id=question_id,
        )
        
        if is_bookmarked and bookmark:
            return BookmarkToggleResponse(
                is_bookmarked=True,
                bookmark=BookmarkResponse(
                    id=bookmark.id,
                    user_id=bookmark.user_id,
                    question_id=bookmark.question_id,
                    created_at=str(bookmark.created_at),
                ),
            )
        return BookmarkToggleResponse(is_bookmarked=False, bookmark=None)
    except Exception as e:
        raise BadRequestException(f"Failed to toggle bookmark: {str(e)}")


@router.delete("/{bookmark_id}", status_code=204)
async def delete_bookmark(
    analysis_service: AnalysisServiceDep,
    current_user: CurrentUser,
    bookmark_id: UUID,
) -> None:
    """Delete a bookmark by ID"""
    bookmark = await analysis_service.get_bookmark_by_id(bookmark_id)
    if not bookmark:
        raise NotFoundException(f"Bookmark with ID {bookmark_id} not found")
    
    # Ensure user owns this bookmark
    if bookmark.user_id != current_user.id:
        raise NotFoundException(f"Bookmark with ID {bookmark_id} not found")
    
    deleted = await analysis_service.delete_bookmark(bookmark_id)
    if not deleted:
        raise NotFoundException(f"Bookmark with ID {bookmark_id} not found")


@router.delete("/question/{question_id}", status_code=204)
async def delete_bookmark_by_question(
    analysis_service: AnalysisServiceDep,
    current_user: CurrentUser,
    question_id: UUID,
) -> None:
    """Delete a bookmark by question ID"""
    deleted = await analysis_service.delete_bookmark_by_user_and_question(
        user_id=current_user.id,
        question_id=question_id,
    )
    if not deleted:
        raise NotFoundException(f"Bookmark for question {question_id} not found")

