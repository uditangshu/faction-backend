"""User endpoints"""

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.v1.dependencies import CurrentUser, UserServiceDep, DBSession
from app.schemas.user import (
    UserProfileResponse,
    UserRatingResponse,
    UserRatingUpdateRequest,
    RatingFluctuationResponse,
    RatingFluctuationEntry,
    TargetExam
)
from app.db.user_calls import get_user_rating_fluctuation
from app.utils.exceptions import ForbiddenException, BadRequestException

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_user_info(current_user: CurrentUser) -> UserProfileResponse:
    """
    Get current authenticated user's profile.
    """
    return UserProfileResponse.from_orm(current_user.model_dump())


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    current_user: CurrentUser,
    user_service: UserServiceDep,
    avatar_file: Optional[UploadFile] = File(None, description="Avatar image file"),
    name: Optional[str] = Form(None),
    class_id: Optional[str] = Form(None, description="Class ID (UUID)"),
    target_exams: Optional[str] = Form(None, description="JSON array of target exams"),
    school: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
) -> UserProfileResponse:
    """
    Update current authenticated user's profile.
    Allows updating name, class_id, target_exams, avatar (via file upload), school, location, and email.
    All fields are optional. If avatar_file is provided, it will be uploaded to Cloudinary.
    """
    from app.integrations.cloudinary_client import upload_image, delete_image
    
    # Handle avatar file upload
    avatar_url = None
    if avatar_file:
        # Validate file type
        if not avatar_file.content_type or not avatar_file.content_type.startswith('image/'):
            raise BadRequestException("File must be an image")
        
        # Delete old avatar if it exists
        if current_user.avatar_url:
            try:
                # Construct the public_id using the same format as upload
                # Format: avatars/{user_id}/{user_id}_avatar
                old_public_id = f"avatars/{current_user.id}/{current_user.id}_avatar"
                await delete_image(old_public_id)
            except Exception:
                # Log but don't fail if deletion fails (image might not exist)
                pass
        
        # Upload new image to Cloudinary
        try:
            avatar_url = await upload_image(
                avatar_file.file,
                folder=f"avatars/{current_user.id}",
                public_id=f"{current_user.id}_avatar"
            )
        except Exception as e:
            raise BadRequestException(f"Failed to upload avatar: {str(e)}")
    
    # Parse target_exams if provided
    target_exams_list = None
    if target_exams:
        try:
            target_exams_data = json.loads(target_exams)
            if isinstance(target_exams_data, list):
                target_exams_list = [TargetExam(exam) for exam in target_exams_data]
        except (json.JSONDecodeError, ValueError) as e:
            raise BadRequestException(f"Invalid target_exams format: {str(e)}")
    
    # Parse class_id if provided
    class_id_uuid = None
    if class_id:
        try:
            class_id_uuid = UUID(class_id)
        except ValueError:
            raise BadRequestException(f"Invalid class_id: {class_id}")
    
    user = await user_service.update_user(
        user_id=current_user.id,
        name=name,
        class_id=class_id_uuid,
        target_exams=target_exams_list,
        avatar_url=avatar_url,
        school=school,
        state=state,
        city=city,
        email=email,
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
#         class_id=payload.class_id,
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


@router.get("/me/rating/graph", response_model=RatingFluctuationResponse)
async def get_my_rating_fluctuation(
    current_user: CurrentUser,
    db: DBSession,
) -> RatingFluctuationResponse:
    """
    Get current user's rating fluctuation history from all contests.
    
    Returns a chronological list of rating changes showing:
    - Contest name and ID
    - Rating before and after each contest
    - Rating delta (change)
    - Rank and score in each contest
    - Date of the contest
    """
    results = await get_user_rating_fluctuation(db, current_user.id)
    
    fluctuations = [
        RatingFluctuationEntry(
            contest_id=contest.id,
            contest_name=contest.name,
            rating_before=leaderboard_entry.rating_before,
            rating_after=leaderboard_entry.rating_after,
            rating_delta=leaderboard_entry.rating_delta,
            rank=leaderboard_entry.rank,
            score=leaderboard_entry.score,
            created_at=leaderboard_entry.created_at,
        )
        for leaderboard_entry, contest in results
    ]
    
    return RatingFluctuationResponse(
        user_id=current_user.id,
        total_contests=len(fluctuations),
        fluctuations=fluctuations,
    )


@router.get("/{user_id}/rating/graph", response_model=RatingFluctuationResponse)
async def get_user_rating_fluctuation(
    user_id: UUID,
    db: DBSession,
) -> RatingFluctuationResponse:
    """
    Get a user's rating fluctuation history from all contests by user ID.
    Public endpoint - anyone can view rating history.
    """
    results = await get_user_rating_fluctuation(db, user_id)
    
    fluctuations = [
        RatingFluctuationEntry(
            contest_id=contest.id,
            contest_name=contest.name,
            rating_before=leaderboard_entry.rating_before,
            rating_after=leaderboard_entry.rating_after,
            rating_delta=leaderboard_entry.rating_delta,
            rank=leaderboard_entry.rank,
            score=leaderboard_entry.score,
            created_at=leaderboard_entry.created_at,
        )
        for leaderboard_entry, contest in results
    ]
    
    return RatingFluctuationResponse(
        user_id=user_id,
        total_contests=len(fluctuations),
        fluctuations=fluctuations,
    )

