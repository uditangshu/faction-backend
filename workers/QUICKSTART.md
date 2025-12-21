# Quick Start Guide for Workers

## Running Workers

### Option 1: Docker Compose (Recommended)

#### Start a single worker:
```bash
docker-compose up worker
```

#### Start multiple workers (scaled):
```bash
docker-compose up --scale worker=3
```

This will start 3 worker instances that will process submissions in parallel.

#### Start all services including workers:
```bash
docker-compose up
```

### Option 2: Local Development

```bash
# Make sure Redis and PostgreSQL are running
python -m workers.entry_point
```

## How It Works

1. **API receives submissions** → Pushes to Redis queue `contest:submissions:{contest_id}`
2. **Workers poll queues** → Discover all active contest queues using Redis SCAN
3. **Workers process submissions** → Use atomic BRPOP to pop items from queues and save to database
4. **Multiple workers** → Can run simultaneously - BRPOP is atomic, so each item is processed by exactly one worker

## Scaling

Workers are designed to be horizontally scalable. Each worker:
- Independently polls Redis queues
- Uses atomic Redis operations (no duplicate processing)
- Processes submissions in parallel

To scale up, simply add more worker instances:
```bash
docker-compose up --scale worker=5  # 5 workers
```

## Monitoring

View worker logs:
```bash
# All workers
docker-compose logs -f worker

# Specific worker instance
docker logs <container_name> -f
```

## Environment Variables

Workers use the same environment variables as the backend:
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection  
- `JWT_SECRET_KEY`: JWT secret
- `APP_ENV`: Environment (development/production)
- `WORKER_ID`: Optional worker identifier

## Testing

1. Submit contest answers via API: `POST /api/v1/contests/submit`
2. Check Redis queue: `redis-cli LLEN contest:submissions:{contest_id}`
3. Watch worker logs to see processing
4. Verify database: Check `question_attempts` table

