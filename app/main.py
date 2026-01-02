from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.config import settings
from app.db.session import init_db, close_db, engine
from app.integrations.redis_client import get_redis, close_redis
from app.api.v1.router import api_router
from app.middleware.timing_middleware import TimingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n🚀 Starting Faction Digital Backend...")
    print("-" * 50)
    
    # Test Redis connection
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        print(" Redis: Connected")
    except Exception as e:
        print(f" Redis: Disconnected")
        print(f"   → {str(e)[:80]}")
        print(f"   → Update REDIS_URL in .env file")
    
    # Test database connection
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("PostgreSQL: Connected")
    except Exception as e:
        print(f"⚠️  PostgreSQL: Connection failed")
        print(f"   → {str(e)[:80]}")
    
    print("-" * 50)
    print(f"🎉 Server ready: http://localhost:8000")
    print(f"📚 API docs: http://localhost:8000/docs")
    print("-" * 50)
    
    yield

    print("\n🛑 Shutting down...")
    try:
        await close_redis()
    except:
        pass
    try:
        await close_db()
    except:
        pass
    print("✓ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI backend for Faction Digital Ecosystem - JEE/NEET preparation platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add timing middleware (first, so it wraps everything)
app.add_middleware(TimingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=3600,
)


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Faction Digital Backend API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "healthy",
    }


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS requests for CORS preflight"""
    return {"message": "OK"}


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    if settings.DEBUG:
        raise exc
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_error",
        },
    )

