"""Chapter endpoints"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Query

from app.api.v1.dependencies import ChapterServiceDep
from app.schemas.question import (
    ChapterCreateRequest,
    ChapterResponse,
    ChapterListResponse,
)
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/chapters", tags=["Chapters"])


@router.post("/", response_model=ChapterResponse, status_code=201)
async def create_chapter(
    chapter_service: ChapterServiceDep,
    request: ChapterCreateRequest,
) -> ChapterResponse:
    """Create a new chapter"""
    try:
        new_chapter = await chapter_service.create_chapter(
            request.name,
            request.subject_id
        )
        return ChapterResponse.model_validate(new_chapter)
    except Exception as e:
        raise BadRequestException(f"Failed to create chapter: {str(e)}")


@router.get("/", response_model=ChapterListResponse)
async def get_all_chapters(
    chapter_service: ChapterServiceDep,
    subject_id: Optional[UUID] = Query(None, description="Filter chapters by subject ID"),
) -> ChapterListResponse:
    """Get all chapters, optionally filtered by subject ID"""
    if subject_id:
        chapters = await chapter_service.get_chapters_by_subject(subject_id)
    else:
        chapters = await chapter_service.get_all_chapters()
    
    return ChapterListResponse(
        chapters=[ChapterResponse.model_validate(c) for c in chapters],
        total=len(chapters)
    )


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    chapter_service: ChapterServiceDep,
    chapter_id: UUID,
) -> ChapterResponse:
    """Get a chapter by ID"""
    result = await chapter_service.get_chapter_by_id(chapter_id)
    if not result:
        raise NotFoundException(f"Chapter with ID {chapter_id} not found")
    return ChapterResponse.model_validate(result)



@router.delete("/{chapter_id}", status_code=204)
async def delete_chapter(
    chapter_service: ChapterServiceDep,
    chapter_id: UUID,
) -> None:
    """Delete a chapter by ID"""
    deleted = await chapter_service.delete_chapter(chapter_id)
    if not deleted:
        raise NotFoundException(f"Chapter with ID {chapter_id} not found")
