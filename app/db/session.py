from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from app.core.config import settings

database_url = settings.DATABASE_URL
if "?sslmode=" in database_url or "&sslmode=" in database_url:
    import re
    database_url = re.sub(r'[?&]sslmode=\w+', '', database_url)

engine = create_async_engine(
    database_url,
    echo=settings.DB_ECHO,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=5,
    connect_args={
        "ssl": "require",
        "server_settings": {"application_name": "faction_backend"},
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                if session.in_transaction():
                    await session.rollback()
            except Exception:
                pass


async def get_readonly_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                if session.in_transaction():
                    await session.rollback()
            except Exception:
                pass


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
