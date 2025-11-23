# Faction Backend Setup Guide

## Prerequisites

1. **Docker Desktop** - Must be running
2. **Python 3.11+** - Already installed
3. **Dependencies** - Already installed via `pip install -r requirements.txt`

## Quick Start (Recommended - Docker)

### Step 1: Start Docker Desktop
Ensure Docker Desktop is running on your system.

### Step 2: Start Services
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be healthy (about 10-15 seconds)
docker-compose ps
```

### Step 3: Create Environment File
Create `.env` file in the `backend/` directory:
```bash
# Copy the contents below to .env file

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
```

### Step 4: Run Database Migrations
```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### Step 5: Start FastAPI Server
```bash
# Development server with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 6: Access the Application
- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Alternative: Run Everything with Docker

```bash
# Start all services including FastAPI
docker-compose up -d

# Run migrations inside container
docker-compose exec backend alembic upgrade head

# View logs
docker-compose logs -f backend
```

## Testing the API

### 1. Signup Flow
```bash
# Step 1: Initiate signup (sends OTP)
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "name": "Test Student",
    "class_level": "12",
    "target_exam": "JEE_MAINS"
  }'

# Response: {"temp_token": "xxx", "otp_sent": true, "expires_in": 300}
# OTP will be printed in console (mock mode)

# Step 2: Verify OTP and complete signup
curl -X POST http://localhost:8000/api/v1/auth/verify-signup \
  -H "Content-Type: application/json" \
  -d '{
    "temp_token": "xxx",
    "otp": "123456"
  }'

# Response: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

### 2. Login Flow
```bash
# Step 1: Request OTP
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210"}'

# Step 2: Verify OTP
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "temp_token": "xxx",
    "otp": "123456"
  }'
```

### 3. Access Protected Endpoints
```bash
# Get current user profile
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <your_access_token>"

# Get study streak
curl -X GET http://localhost:8000/api/v1/streaks/me \
  -H "Authorization: Bearer <your_access_token>"

# Get study calendar
curl -X GET http://localhost:8000/api/v1/streaks/me/calendar \
  -H "Authorization: Bearer <your_access_token>"
```

## Database Management

### View Migrations
```bash
alembic history
```

### Create New Migration
```bash
alembic revision --autogenerate -m "Add new feature"
```

### Rollback Migration
```bash
alembic downgrade -1
```

### Reset Database
```bash
alembic downgrade base
alembic upgrade head
```

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

## Troubleshooting

### Docker Issues
```bash
# Check if Docker Desktop is running
docker ps

# Restart services
docker-compose restart

# View logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs backend
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
docker-compose exec postgres psql -U faction_user -d faction_db -c "SELECT 1;"

# Test Redis connection
docker-compose exec redis redis-cli -a redis_password ping
```

### Port Already in Use
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (use Task Manager or taskkill command)
```

## Next Steps

1. **Seed Data**: Create subjects, topics, and sample questions
2. **Admin Panel**: Create endpoints for content management
3. **SMS Integration**: Configure Twilio/MSG91 for production OTP
4. **Monitoring**: Setup logging and error tracking
5. **Deployment**: Configure production environment

## Project Status

✅ Complete:
- [x] Project structure and configuration
- [x] Database models (SQLModel)
- [x] Alembic migrations setup
- [x] Phone-based OTP authentication
- [x] Question bank APIs
- [x] Study streak system
- [x] GitHub-style calendar
- [x] Docker containerization
- [x] API documentation
- [x] Basic tests

🚧 TODO (Future):
- [ ] SMS provider integration (Twilio/MSG91)
- [ ] Admin endpoints for content management
- [ ] Leaderboard system
- [ ] Video integration
- [ ] Advanced analytics
- [ ] Push notifications

