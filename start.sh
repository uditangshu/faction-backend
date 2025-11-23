#!/bin/bash
# Faction Backend - Quick Start Script for Linux/Mac

echo "🚀 Faction Digital Backend - Quick Start"
echo ""

# Check if Docker is running
echo "Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "Please start Docker and run this script again."
    exit 1
fi
echo "✓ Docker is running"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠ .env file not found!"
    echo "Creating .env file..."
    
    cat > .env << 'EOF'
APP_NAME=Faction Digital Backend
APP_ENV=development
DEBUG=True
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+asyncpg://faction_user:faction_password@localhost:5432/faction_db
DB_ECHO=False

REDIS_URL=redis://:redis_password@localhost:6379/0

JWT_SECRET_KEY=dev-secret-key-change-in-production-12345
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

OTP_LENGTH=6
OTP_EXPIRE_MINUTES=5
OTP_MAX_ATTEMPTS=3

SMS_PROVIDER=mock

BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

RATE_LIMIT_ENABLED=True
RATE_LIMIT_PER_MINUTE=60
EOF
    
    echo "✓ .env file created"
fi

# Start Docker services
echo ""
echo "Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

if [ $? -ne 0 ]; then
    echo "❌ Failed to start Docker services"
    exit 1
fi

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10
echo "✓ Services started"

# Check if migrations exist
if [ -z "$(ls -A alembic/versions/*.py 2>/dev/null)" ]; then
    echo ""
    echo "Creating initial database migration..."
    alembic revision --autogenerate -m "Initial migration with all core models"
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create migration"
        exit 1
    fi
    echo "✓ Migration created"
fi

# Run migrations
echo ""
echo "Running database migrations..."
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ Failed to run migrations"
    exit 1
fi
echo "✓ Migrations applied"

# All done
echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the FastAPI server, run:"
echo "  uvicorn app.main:app --reload"
echo ""
echo "API Documentation will be available at:"
echo "  http://localhost:8000/docs"
echo ""

