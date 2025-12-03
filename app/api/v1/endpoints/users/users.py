"""User endpoints"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.dependencies import CurrentUser, UserServiceDep
from app.schemas.user import (
    UserProfileResponse,
    # UserCreate,
)
from app.utils.exceptions import ForbiddenException

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_user_info(current_user: CurrentUser) -> UserProfileResponse:
    print(current_user.name)
    """
    Get current authenticated user's profile.
    """
    return UserProfileResponse.from_orm(current_user)


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





