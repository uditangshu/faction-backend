"""User endpoints"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.dependencies import CurrentUser, UserServiceDep
from app.schemas.user import (
    UserProfileResponse,
    UserUpdateRequest,
    UserRatingResponse,
    UserRatingUpdateRequest
)
from app.utils.exceptions import ForbiddenException

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_user_info(current_user: CurrentUser) -> UserProfileResponse:
    """
    Get current authenticated user's profile.
    """
    return UserProfileResponse.from_orm(current_user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    request: UserUpdateRequest,
    current_user: CurrentUser,
    user_service: UserServiceDep,
) -> UserProfileResponse:
    """
    Update current authenticated user's profile.
    Allows updating name, class_level, and avatar_svg.
    """
    user = await user_service.update_user(
        user_id=current_user.id,
        name=request.name,
        class_level=request.class_level,
        avatar_svg=request.avatar_svg,
    )
    return UserProfileResponse.from_orm(user)


# @router.post("/", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
# async def create_user(
#     payload: UserCreate,
#     user_service: UserServiceDep,
# ) -> UserProfileResponse:
#     """
#     Create a new user. Validates payload, hashes password, and saves to DB.
#     Note: This endpoint should typically be used by admins only.
#     For regular signup, use the auth signup endpoint.
#     """
#     user = await user_service.create_user(
#         phone_number=payload.phone_number,
#         name=payload.name,
#         password=payload.password,
#         class_level=payload.class_level,
#         target_exams=payload.target_exams,
#         role=payload.role,
#     )
#     return UserProfileResponse.from_orm(user)


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(
    user_id: UUID,
    user_service: UserServiceDep,
    current_user: CurrentUser,
) -> UserProfileResponse:
    """
    Retrieve a user by UUID.
    Users can only view their own profile unless they are admins.
    """
    # Check if user is viewing their own profile or is an admin
    if current_user.id != user_id and current_user.role.value != "ADMIN":
        raise ForbiddenException("You can only view your own profile")

    user = await user_service.get_user_by_id(user_id)
    return UserProfileResponse.from_orm(user)


@router.get("/", response_model=List[UserProfileResponse])
async def list_users(
    user_service: UserServiceDep,
    q: Optional[str] = Query(None, description="Search term (name or phone number)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> List[UserProfileResponse]:
    """
    List users with optional search and pagination.
    Only admins can list all users.
    """
    # Check if user is admin
    # if current_user.role.value != "ADMIN":
    #     raise ForbiddenException("Only admins can list users")

    users = await user_service.list_users(q=q, skip=skip, limit=limit)
    return [UserProfileResponse.from_orm(user) for user in users]


# ==================== Rating Endpoints ====================

@router.get("/me/rating", response_model=UserRatingResponse)
async def get_my_rating(
    current_user: CurrentUser,
) -> UserRatingResponse:
    """
    Get current user's contest rating information.
    """
    return UserRatingResponse(
        user_id=current_user.id,
        current_rating=current_user.current_rating,
        max_rating=current_user.max_rating,
        title=current_user.title,
    )


@router.get("/{user_id}/rating", response_model=UserRatingResponse)
async def get_user_rating(
    user_id: UUID,
    user_service: UserServiceDep,
) -> UserRatingResponse:
    """
    Get a user's contest rating information by user ID.
    Public endpoint - anyone can view ratings.
    """
    user = await user_service.get_user_by_id(user_id)
    return UserRatingResponse(
        user_id=user.id,
        current_rating=user.current_rating,
        max_rating=user.max_rating,
        title=user.title,
    )


@router.patch("/{user_id}/rating", response_model=UserRatingResponse)
async def update_user_rating(
    user_id: UUID,
    request: UserRatingUpdateRequest,
    user_service: UserServiceDep,
    current_user: CurrentUser,
) -> UserRatingResponse:
    """
    Update a user's contest rating.
    Admin only endpoint.
    """
    # Only admins can update ratings
    if current_user.role.value != "ADMIN":
        raise ForbiddenException("Only admins can update user ratings")
    
    user = await user_service.update_user_rating(
        user_id=user_id,
        current_rating=request.current_rating,
        max_rating=request.max_rating,
        title=request.title,
    )
    return UserRatingResponse(
        user_id=user.id,
        current_rating=user.current_rating,
        max_rating=user.max_rating,
        title=user.title,
    )

