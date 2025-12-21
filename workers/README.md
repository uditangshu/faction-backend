# Contest Submission Workers

This directory contains worker processes that consume contest submissions from Redis queues and process them asynchronously.

## Architecture

- **Workers**: Independent processes that consume from Redis queues
- **Queue**: Redis lists (`contest:submissions:{contest_id}`)
- **Scalability**: Multiple workers can run simultaneously, each processing submissions independently

## Running Workers

### Using Docker Compose

#### Single Worker
```bash
docker-compose up worker
```

#### Multiple Workers (Scaled)
```bash
docker-compose up --scale worker=3
```

This will start 3 worker instances that will all consume from the same queues.

#### Specific Number of Workers
Edit `docker-compose.yml` and uncomment the worker-1, worker-2, etc. services, or use the scale command.

### Running Locally (Development)

```bash
# From the project root
python -m workers.entry_point
```

## Worker Behavior

1. **Queue Discovery**: Workers automatically discover queues matching `contest:submissions:*` using Redis SCAN
2. **Atomic Queue Operations**: Workers use Redis BRPOP (blocking right pop) which is atomic at the Redis level
   - Multiple workers can safely process from the same queue
   - Each item is guaranteed to be processed by exactly one worker
   - BRPOP listens to multiple queues simultaneously and returns the first available item
3. **Database Updates**: Each submission is processed and saved to the database using the same logic as direct submissions
4. **Error Handling**: Failed submissions are logged; consider implementing a dead-letter queue for production
5. **Graceful Shutdown**: Workers handle SIGTERM/SIGINT signals for clean shutdown

## Configuration

Workers use the same environment variables as the main application:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: JWT secret (for consistency)
- `APP_ENV`: Environment name (development/production)

## Monitoring

Workers log:
- Worker startup/shutdown
- Queue discovery
- Submission processing (success/failure)
- Errors with full stack traces

Check logs:
```bash
# Docker logs
docker-compose logs -f worker

# Or for specific worker instance
docker logs faction_worker_1 -f
```

## Scaling

Workers are designed to be horizontally scalable:
- Each worker independently polls Redis queues using atomic BRPOP operations
- **BRPOP is atomic at the Redis level** - when multiple workers call BRPOP on the same queue, Redis guarantees that only one worker will receive each item
- Workers can listen to multiple queues simultaneously using BRPOP with multiple queue arguments
- Add more workers to increase throughput - they will automatically share the workload

## Production Considerations

1. **Dead Letter Queue**: Implement a DLQ for failed submissions
2. **Monitoring**: Add metrics/monitoring (Prometheus, etc.)
3. **Health Checks**: Add health check endpoints
4. **Resource Limits**: Set appropriate CPU/memory limits in docker-compose
5. **Queue Registry**: Consider maintaining a registry of active contest queues instead of scanning

