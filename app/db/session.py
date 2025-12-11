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
engine = create_async_engine(
    database_url,
    echo=settings.DB_ECHO,
    future=True,
    pool_pre_ping=True,
    pool_size=30,  # Increased since max_overflow is ignored in asyncpg session mode
    max_overflow=20,  # Kept for documentation, but not used in session mode
    connect_args={
        "ssl": "require",  # SSL is required for Aivennigga
        "server_settings": {"application_name": "faction_backend"}
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
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            try:
                await session.rollback()
                if settings.DEBUG:
                    print(f"⚠️ Database session rolled back due to exception: {type(e).__name__}")
            except Exception as rollback_error:
                if settings.DEBUG:
                    print(f"❌ Failed to rollback session: {rollback_error}")
            raise

async def init_db() -> None:
    """Initialize database tables (for development only)"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()

