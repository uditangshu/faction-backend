"""User session model for device tracking"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class DeviceType(str, Enum):
    """Device type enumeration"""
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"


class UserSession(SQLModel, table=True):
    """User session for device management and refresh tokens"""
    
    __tablename__ = "user_sessions"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    device_id: str = Field(max_length=255)
    device_type: DeviceType
    device_model: str | None = Field(default=None, max_length=100)
    os_version: str | None = Field(default=None, max_length=50)
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None)
    refresh_token_hash: str
    push_token: str | None = Field(default=None)  # Expo push notification token
    is_active: bool = Field(default=True, index=True)
    expires_at: datetime
    last_active: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

