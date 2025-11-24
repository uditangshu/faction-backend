"""Security utilities for JWT tokens and authentication"""

from datetime import datetime, timedelta
from typing import Any, Dict
from hashlib import sha256
from jose import jwt, JWTError
import bcrypt

from app.core.config import settings


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """
    Hash a password using SHA256 + bcrypt.
    SHA256 pre-hash ensures any length password works (bcrypt has 72-byte limit).
    """
    # Pre-hash with SHA256 to get fixed 32-byte output
    password_digest = sha256(password.encode('utf-8')).digest()
    # Hash with bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_digest, salt)
    # Return as string for storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (with SHA256 pre-hashing)"""
    # Pre-hash the same way
    password_digest = sha256(plain_password.encode('utf-8')).digest()
    # Verify with bcrypt
    return bcrypt.checkpw(password_digest, hashed_password.encode('utf-8'))

