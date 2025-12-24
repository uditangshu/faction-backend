"""Badge endpoints"""

from uuid import UUID
from fastapi import APIRouter, File, UploadFile, Form
from typing import Optional

from app.api.v1.dependencies import BadgeServiceDep
from app.schemas.badge import (
    BadgeResponse,
    BadgeListResponse,
)
from app.models.badge import BadgeCategory
from app.integrations.cloudinary_client import upload_image, delete_image, extract_cloudinary_public_id
from app.exceptions.http_exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/badges", tags=["Badges"])


@router.get("/", response_model=BadgeListResponse)
async def get_all_badges(
    badge_service: BadgeServiceDep,
) -> BadgeListResponse:
    """Get all badges"""
    badges = await badge_service.get_all_badges()
    
    return BadgeListResponse(
        badges=[BadgeResponse.model_validate(badge) for badge in badges],
        total=len(badges),
    )


@router.post("/", response_model=BadgeResponse, status_code=201)
async def create_badge(
    badge_service: BadgeServiceDep,
    name: str = Form(...),
    description: str = Form(...),
    category: BadgeCategory = Form(...),
    icon_image: UploadFile = File(..., description="Badge icon image file"),
    icon_svg: Optional[str] = Form(None),
    requirement_value: Optional[int] = Form(None),
    requirement_description: str = Form(...),
    is_active: bool = Form(True),
) -> BadgeResponse:
    """Create a new badge with image upload to Cloudinary"""
    try:
        # Validate file type
        if not icon_image.content_type or not icon_image.content_type.startswith('image/'):
            raise BadRequestException("File must be an image")
        
        # Upload image to Cloudinary
        try:
            icon_url = await upload_image(
                icon_image.file,
                folder="badges",
                public_id=None  # Let Cloudinary generate the ID
            )
        except Exception as e:
            raise BadRequestException(f"Failed to upload image: {str(e)}")
        
        # Create badge with Cloudinary URL
        new_badge = await badge_service.create_badge(
            name=name,
            description=description,
            category=category,
            icon_url=icon_url,
            icon_svg=icon_svg,
            requirement_value=requirement_value,
            requirement_description=requirement_description,
            is_active=is_active,
        )
        return BadgeResponse.model_validate(new_badge)
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create badge: {str(e)}")


@router.delete("/{badge_id}", status_code=204)
async def delete_badge(
    badge_service: BadgeServiceDep,
    badge_id: UUID,
) -> None:
    """Delete a badge by ID and its image from Cloudinary"""
    # Get badge first to retrieve icon_url
    badge = await badge_service.get_badge_by_id(badge_id)
    if not badge:
        raise NotFoundException(f"Badge with ID {badge_id} not found")
    
    # Delete image from Cloudinary if icon_url exists
    if badge.icon_url:
        public_id = extract_cloudinary_public_id(badge.icon_url)
        if public_id:
            try:
                await delete_image(public_id)
            except Exception:
                # Log error but continue with badge deletion
                pass
    
    # Delete badge from database
    deleted = await badge_service.delete_badge(badge_id)
    if not deleted:
        raise NotFoundException(f"Badge with ID {badge_id} not found")

