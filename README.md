# Faction Digital Backend

FastAPI backend for Faction Digital Ecosystem - A JEE/NEET exam preparation platform with gamification and adaptive learning.

## Features

- 🔐 **Phone-based OTP Authentication** - Secure login without passwords
- 📚 **Question Bank** - MCQ, Numerical, and Multi-Select questions
- 🔥 **Study Streaks** - GitHub-style contribution calendar
- 📊 **Performance Tracking** - Real-time statistics and analytics
- 🎯 **Adaptive Learning** - Personalized question recommendations
- ⚡ **High Performance** - Async/await, Redis caching, connection pooling

## Tech Stack

- **Framework**: FastAPI 0.109+
- **ORM**: SQLModel (SQLAlchemy 2.0 + Pydantic)
- **Database**: PostgreSQL 15+ with Asyncpg
- **Cache**: Redis 7+
- **Migrations**: Alembic
- **Testing**: Pytest + Httpx
- **Code Quality**: Black, Ruff, MyPy

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Option 1: Docker Compose (Recommended)

1. **Clone and setup**
   ```bash
   cd backend
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Run migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Option 2: Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database**
   ```bash
   # Create PostgreSQL database
   createdb faction_db
   
   # Run migrations
   alembic upgrade head
   ```

3. **Start Redis**
   ```bash
   redis-server
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run the server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Config, DB, Security, Redis
│   ├── models/          # SQLModel database models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic
│   ├── utils/           # Utilities and exceptions
│   └── main.py          # FastAPI app
├── alembic/             # Database migrations
├── tests/               # Pytest tests
├── docker-compose.yml   # Docker services
├── Dockerfile           # Production container
└── requirements.txt     # Python dependencies
```

## API Documentation

### Authentication Endpoints

#### Signup Flow
```
POST /api/v1/auth/signup
{
  "phone_number": "+919876543210",
  "name": "John Doe",
  "class_level": "12",
  "target_exam": "JEE_MAINS"
}
→ Returns temp_token, sends OTP to phone

POST /api/v1/auth/verify-signup
{
  "temp_token": "xxx",
  "otp": "123456"
}
→ Returns access_token, refresh_token
```

#### Login Flow
```
POST /api/v1/auth/login
{
  "phone_number": "+919876543210"
}
→ Returns temp_token, sends OTP

POST /api/v1/auth/verify-otp
{
  "temp_token": "xxx",
  "otp": "123456"
}
→ Returns access_token, refresh_token
```

### Question Bank Endpoints

```
GET /api/v1/questions
  ?subject_id={uuid}
  &topic_id={uuid}
  &difficulty_level={1-5}
  &skip=0
  &limit=20

GET /api/v1/questions/{id}

POST /api/v1/questions/{id}/submit
{
  "user_answer": "A",
  "time_taken": 45
}
```

### Study Streak Endpoints

```
GET /api/v1/streaks/me
→ Current streak, longest streak, statistics

GET /api/v1/streaks/me/calendar?days=365
→ GitHub-style calendar data with intensity levels
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

## Code Quality

```bash
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type checking
mypy app/

# Run all pre-commit hooks
pre-commit run --all-files
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | Required |
| `JWT_ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry | 30 |
| `OTP_LENGTH` | OTP code length | 6 |
| `OTP_EXPIRE_MINUTES` | OTP expiration time | 5 |
| `SMS_PROVIDER` | SMS provider (mock/twilio) | mock |

## Deployment

### Production Checklist

- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Configure production database
- [ ] Setup Redis with password
- [ ] Configure SMS provider (Twilio/MSG91)
- [ ] Enable HTTPS
- [ ] Setup monitoring and logging
- [ ] Configure backup strategy
- [ ] Review CORS settings

### Docker Production Build

```bash
# Build production image
docker build -t faction-backend:latest .

# Run with environment file
docker run -d \
  --name faction-backend \
  --env-file .env.production \
  -p 8000:8000 \
  faction-backend:latest
```

## Contributing

1. Create a feature branch
2. Make changes and add tests
3. Run code quality checks
4. Submit pull request

## License

Proprietary - Faction Digital Ecosystem

## Support

For issues and questions, contact the development team.

