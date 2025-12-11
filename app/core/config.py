import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Faction Digital Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 90 * 24 * 60  # 3 months (129,600 minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 365  # 1 year
    SESSION_TTL_DAYS: int = 365  # 1 year (matches refresh token)

    # OTP
    OTP_LENGTH: int = 4
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 3

    # SMS Provider
    SMS_PROVIDER: str = "twilio"  # Options: 'mock', 'twilio'
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_VERIFY_SERVICE_SID: str | None = None

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8081",  # Expo web default port
        "http://localhost:19006",  # Expo web alternative port
        "http://127.0.0.1:8081",
        "http://127.0.0.1:19006",
        "http://10.145.13.125:8081",
        "http://10.145.13.125:19006",
        "*" # Allow all for development
    ]

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

