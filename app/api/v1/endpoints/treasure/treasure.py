"""Treasure endpoints"""

from uuid import UUID
from fastapi import APIRouter, Query, File, UploadFile, Form
from typing import Optional

from app.api.v1.dependencies import TreasureServiceDep, CurrentUser
from app.schemas.treasure import (
    TreasureResponse,
    TreasureListResponse,
)
from app.integrations.cloudinary_client import upload_image, delete_image, extract_cloudinary_public_id
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/treasures", tags=["Treasures"])


@router.post("/", response_model=TreasureResponse, status_code=201)
async def create_treasure(
    treasure_service: TreasureServiceDep,
    current_user: CurrentUser,
    chapter_id: UUID = Form(..., description="Chapter ID"),
    subject_id: UUID = Form(..., description="Subject ID"),
    mindmap_image: UploadFile = File(..., description="Mindmap image file"),
    title: Optional[str] = Form(None, max_length=200, description="Optional title for the treasure"),
    description: Optional[str] = Form(None, description="Optional description for the treasure"),
    order: int = Form(0, ge=0, description="Order/sequence within chapter"),
) -> TreasureResponse:
    """Create a new treasure (mindmap image)"""
    try:
        # Validate file type
        if not mindmap_image.content_type or not mindmap_image.content_type.startswith('image/'):
            raise BadRequestException("File must be an image")
        
        # Upload image to Cloudinary
        try:
            image_url = await upload_image(
                mindmap_image.file,
                folder=f"treasures/{current_user.id}",
                public_id=None  # Let Cloudinary generate the ID
            )
        except Exception as e:
            raise BadRequestException(f"Failed to upload image: {str(e)}")
        
        # Create the treasure
        treasure = await treasure_service.create_treasure(
            chapter_id=chapter_id,
            subject_id=subject_id,
            image_url=image_url,
            title=title,
            description=description,
            order=order,
        )
        
        return TreasureResponse.model_validate(treasure)
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create treasure: {str(e)}")


@router.delete("/{treasure_id}", status_code=204)
async def delete_treasure(
    treasure_id: UUID,
    treasure_service: TreasureServiceDep,
    current_user: CurrentUser,
) -> None:
    """Delete a treasure"""
    # Get the treasure first to extract the image URL for deletion from Cloudinary
    treasure = await treasure_service.get_treasure_by_id(treasure_id)
    if not treasure:
        raise NotFoundException(f"Treasure with ID {treasure_id} not found")
    
    # Delete the image from Cloudinary
    if treasure.image_url:
        public_id = extract_cloudinary_public_id(treasure.image_url)
        if public_id:
            try:
                await delete_image(public_id)
            except Exception:
                # Log error but continue with database deletion
                pass
    
    # Delete from database
    deleted = await treasure_service.delete_treasure(treasure_id)
    if not deleted:
        raise NotFoundException(f"Treasure with ID {treasure_id} not found")


@router.get("/", response_model=TreasureListResponse)
async def get_treasures(
    treasure_service: TreasureServiceDep,
    current_user: CurrentUser,
    subject_id: Optional[UUID] = Query(None, description="Filter by subject ID"),
    chapter_id: Optional[UUID] = Query(None, description="Filter by chapter ID"),
    sort_order: str = Query("latest", description="Sort order: 'latest' or 'oldest'"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records"),
) -> TreasureListResponse:
    """
    Get treasures filtered by user's class, optionally by subject and chapter.
    
    The treasures are automatically filtered by the user's class. You can further filter by:
    - subject_id: Filter by specific subject
    - chapter_id: Filter by specific chapter (requires subject_id to be in user's class)
    """
    if sort_order not in ["latest", "oldest"]:
        raise BadRequestException("sort_order must be 'latest' or 'oldest'")
    
    # Get treasures filtered by user's class
    treasures = await treasure_service.get_treasures_by_user_class(
        class_id=current_user.class_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    
    return TreasureListResponse(
        treasures=[TreasureResponse.model_validate(t) for t in treasures],
        total=len(treasures),
        subject_id=subject_id,
        chapter_id=chapter_id,
    )


@router.get("/{treasure_id}", response_model=TreasureResponse)
async def get_treasure_by_id(
    treasure_id: UUID,
    treasure_service: TreasureServiceDep,
) -> TreasureResponse:
    """Get a treasure by ID"""
    treasure = await treasure_service.get_treasure_by_id(treasure_id)
    if not treasure:
        raise NotFoundException(f"Treasure with ID {treasure_id} not found")
    return TreasureResponse.model_validate(treasure)

