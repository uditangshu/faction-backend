"""Database session management"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings

# Parse DATABASE_URL and handle SSL
database_url = settings.DATABASE_URL
# Remove sslmode from URL if present (asyncpg doesn't support it in URL)
if "?sslmode=" in database_url or "&sslmode=" in database_url:
    import re
    database_url = re.sub(r'[?&]sslmode=\w+', '', database_url)
    print(f"DATABASE_URL: {database_url}")

# Create async engine with SSL configuration
# Optimized for high RPS (200+ requests/second)
# Note: max_overflow is ignored with asyncpg, so pool_size is the total connection limit
engine = create_async_engine(
    database_url,
    echo=settings.DB_ECHO,
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=200,  # Increased for high RPS - ensure PostgreSQL max_connections >= 250
    max_overflow=0,  # Not used with asyncpg, but kept for clarity
    pool_recycle=3600,  # Recycle connections after 1 hour to prevent stale connections
    pool_timeout=30,  # Wait up to 30 seconds for a connection from the pool
    connect_args={
        "ssl": "require",  # SSL is required for Aivennigga
        "server_settings": {"application_name": "faction_backend"},
        # Enable statement caching for better performance (reduces query planning overhead)
        "statement_cache_size": 0,  # Cache up to 100 prepared statements
        "prepared_statement_cache_size": 0,  # Cache prepared statements
        "max_cached_statement_lifetime": 0,  # Cache for 5 minutes
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper cleanup.
    The async context manager automatically handles session closing."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            try:
                await session.rollback()
            except:
                pass
            raise


async def init_db() -> None:
    """Initialize database tables (for development only)"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()

