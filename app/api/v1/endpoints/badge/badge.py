"""Badge endpoints"""

from uuid import UUID
from fastapi import APIRouter

from app.api.v1.dependencies import BadgeServiceDep
from app.schemas.badge import (
    BadgeCreateRequest,
    BadgeResponse,
    BadgeListResponse,
)
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
    request: BadgeCreateRequest,
) -> BadgeResponse:
    """Create a new badge"""
    try:
        new_badge = await badge_service.create_badge(
            name=request.name,
            description=request.description,
            category=request.category,
            icon_url=request.icon_url,
            icon_svg=request.icon_svg,
            requirement_value=request.requirement_value,
            requirement_description=request.requirement_description,
            is_active=request.is_active,
        )
        return BadgeResponse.model_validate(new_badge)
    except Exception as e:
        raise BadRequestException(f"Failed to create badge: {str(e)}")


@router.delete("/{badge_id}", status_code=204)
async def delete_badge(
    badge_service: BadgeServiceDep,
    badge_id: UUID,
) -> None:
    """Delete a badge by ID"""
    deleted = await badge_service.delete_badge(badge_id)
    if not deleted:
        raise NotFoundException(f"Badge with ID {badge_id} not found")

