"""User service for user management operations"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.models.user import User, UserRole, ClassLevel, TargetExam, SubscriptionType, ContestRank
from app.db.user_calls import (
    get_user_by_id as db_get_user_by_id,
    get_user_by_phone as db_get_user_by_phone,
    create_user as db_create_user,
    update_user as db_update_user,
)
from app.core.security import hash_password, verify_password
from app.utils.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    UnauthorizedException,
)
from app.utils.phone import validate_indian_phone


class UserService:
    """Service for all User relating Operations - stateless, accepts db as method parameter"""
    
    async def create_user(
        self,
        db: AsyncSession,
        phone_number: str,
        name: str,
        password: str,
        class_level: ClassLevel,
        target_exams: List[TargetExam],
        role: UserRole = UserRole.STUDENT,
    ) -> User:

        is_valid, formatted_phone = validate_indian_phone(phone_number)
        if not is_valid:
            raise BadRequestException("Invalid phone number format")

        # Check if user already exists
        existing_user = await db_get_user_by_phone(db, formatted_phone)
        if existing_user:
            raise ConflictException("Phone number already registered")

        # Hash password
        password_hash = hash_password(password)

        # Convert target_exams to list of strings
        target_exams_list = [exam.value for exam in target_exams]

        # Create user
        user = User(
            phone_number=formatted_phone,
            password_hash=password_hash,
            name=name,
            class_level=class_level,
            target_exams=target_exams_list,
            role=role,
            subscription_type=SubscriptionType.FREE,
            is_active=True,
        )

        return await db_create_user(db, user)

    async def get_user_by_id(self, db: AsyncSession, user_id: UUID) -> User:
        """
        Get user by ID.
        
        Args:
            db: Database session
            user_id: User UUID
            
        Returns:
            User object
            
        Raises:
            NotFoundException: If user not found
        """
        user = await db_get_user_by_id(db, user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    async def list_users(
        self,
        db: AsyncSession,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[User]:
        """
        List users with optional search and pagination.
        
        Args:
            db: Database session
            q: Search query (searches in name and phone_number)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of User objects
        """
        query = select(User)

        # Apply search filter if provided
        if q:
            search_term = f"%{q.lower()}%"
            query = query.where(
                or_(
                    func.lower(User.name).like(search_term),
                    func.lower(User.phone_number).like(search_term),
                )
            )

        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        name: Optional[str] = None,
        class_level: Optional[ClassLevel] = None,
        subscription_type: Optional[SubscriptionType] = None,
        avatar_svg: Optional[str] = None,
    ) -> User:
        """
        Update user profile.
        
        Args:
            db: Database session
            user_id: User UUID
            name: Optional new name
            class_level: Optional new class level
            subscription_type: Optional new subscription type
            avatar_svg: Optional SVG string for user avatar
            
        Returns:
            Updated User object
            
        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user_by_id(db, user_id)

        # Update fields if provided
        if name is not None:
            user.name = name
        if class_level is not None:
            user.class_level = class_level
        if subscription_type is not None:
            user.subscription_type = subscription_type
        if avatar_svg is not None:
            user.avatar_svg = avatar_svg

        user.updated_at = datetime.utcnow()

        return await db_update_user(db, user)

    async def update_user_rating(
        self,
        db: AsyncSession,
        user_id: UUID,
        current_rating: int,
        max_rating: Optional[int] = None,
        title: Optional[ContestRank] = None,
    ) -> User:
        """
        Update user's contest rating.
        
        Args:
            db: Database session
            user_id: User UUID
            current_rating: New current rating
            max_rating: Optional new max rating (auto-calculated if not provided)
            title: Optional new title (auto-calculated based on rating if not provided)
            
        Returns:
            Updated User object
            
        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user_by_id(db, user_id)

        user.current_rating = current_rating
        
        # Update max_rating if new rating is higher or if explicitly provided
        if max_rating is not None:
            user.max_rating = max_rating
        elif current_rating > user.max_rating:
            user.max_rating = current_rating
        
        # Update title based on max_rating if not explicitly provided
        if title is not None:
            user.title = title
        else:
            user.title = self._calculate_title(user.max_rating)

        user.updated_at = datetime.utcnow()

        return await db_update_user(db, user)

    def _calculate_title(self, rating: int) -> ContestRank:
        """
        Calculate contest rank title based on rating.
        
        Rating thresholds (similar to Codeforces):
        - Newbie: 0 - 1199
        - Specialist: 1200 - 1399
        - Expert: 1400 - 1599
        - Candidate Master: 1600 - 1899
        - Master: 1900 - 2099
        - Grandmaster: 2100 - 2399
        - Legendary Grandmaster: 2400+
        """
        if rating >= 2400:
            return ContestRank.LEGENDARY_GRANDMASTER
        elif rating >= 2100:
            return ContestRank.GRANDMASTER
        elif rating >= 1900:
            return ContestRank.MASTER
        elif rating >= 1600:
            return ContestRank.CANDIDATE_MASTER
        elif rating >= 1400:
            return ContestRank.EXPERT
        elif rating >= 1200:
            return ContestRank.SPECIALIST
        else:
            return ContestRank.NEWBIE
