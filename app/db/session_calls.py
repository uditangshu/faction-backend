"""Database operations for user sessions"""

from datetime import datetime
from uuid import UUID
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.session import UserSession, DeviceType


async def create_user_session(
    db: AsyncSession,
    user_id: UUID,
    device_id: str,
    device_type: DeviceType,
    device_model: str | None,
    os_version: str | None,
    ip_address: str | None,
    user_agent: str | None,
    refresh_token_hash: str,
    expires_at: datetime,
) -> UserSession:
    """Create a new user session"""
    session = UserSession(
        user_id=user_id,
        device_id=device_id,
        device_type=device_type,
        device_model=device_model,
        os_version=os_version,
        ip_address=ip_address,
        user_agent=user_agent,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_user_session(db: AsyncSession, session_id: UUID) -> UserSession | None:
    """Get session by ID"""
    statement = select(UserSession).where(UserSession.id == session_id)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_active_user_session(db: AsyncSession, user_id: UUID) -> UserSession | None:
    """Get user's current active session"""
    statement = (
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.is_active == True)
        .order_by(UserSession.created_at.desc())
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def update_session_activity(db: AsyncSession, session_id: UUID) -> bool:
    """Update session last_active timestamp"""
    session = await get_user_session(db, session_id)
    if not session:
        return False
    
    session.last_active = datetime.utcnow()
    db.add(session)
    await db.commit()
    return True


async def invalidate_old_sessions(db: AsyncSession, user_id: UUID, exclude_session_id: UUID | None = None, commit: bool = True) -> int:
    """Mark old sessions as inactive for a user - optimized with single UPDATE query"""
    from sqlalchemy import update
    
    # Use a single UPDATE query instead of fetch-then-update
    update_stmt = (
        update(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.is_active == True)
        .values(is_active=False)
    )
    
    if exclude_session_id:
        update_stmt = update_stmt.where(UserSession.id != exclude_session_id)
    
    result = await db.execute(update_stmt)
    
    if commit:
        await db.commit()
    
    # Return the number of rows affected
    return result.rowcount

