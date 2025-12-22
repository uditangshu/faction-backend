"""Contest grading worker - calculates ranks and ratings after submissions are processed"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.integrations.redis_client import get_redis, RedisService
from app.services.rating_calculation import calculate_contest_ratings

logger = logging.getLogger(__name__)


class GradingWorker:
    """Worker that calculates ranks and ratings after all submissions are processed"""

    def __init__(self, worker_id: str = "grading-worker-1"):
        self.worker_id = worker_id
        self.redis_service: RedisService | None = None
        self.running = False
        self.grading_queue = "contest:grading"
        self.blocking_timeout = 5  # seconds for BRPOP

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            redis_client = await get_redis()
            self.redis_service = RedisService(redis_client)
            logger.info(f"Grading worker {self.worker_id} initialized with Redis connection")
        except Exception as e:
            logger.error(f"Failed to initialize Redis for grading worker {self.worker_id}: {e}")
            raise

    async def run(self):
        """Main grading worker loop"""
        self.running = True
        logger.info(f"Grading worker {self.worker_id} started")
        
        try:
            while self.running:
                try:
                    # Pop contest_id from grading queue (blocking)
                    result = await self.redis_service.pop_from_queue_blocking(
                        self.grading_queue,
                        timeout=self.blocking_timeout
                    )
                    
                    if result is None:
                        # Timeout - no items in queue, continue loop
                        continue
                    
                    # Extract contest_id from queue result
                    _, contest_id_str = result
                    try:
                        contest_id = UUID(contest_id_str)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid contest_id in grading queue: {contest_id_str}")
                        continue
                    
                    # Calculate ratings for this contest
                    logger.info(
                        f"Grading worker {self.worker_id} calculating ratings for contest {contest_id}"
                    )
                    
                    async with AsyncSessionLocal() as db:
                        try:
                            success = await calculate_contest_ratings(db, contest_id)
                            if success:
                                logger.info(
                                    f"Grading worker {self.worker_id} successfully calculated ratings for contest {contest_id}"
                                )
                            else:
                                logger.warning(
                                    f"Grading worker {self.worker_id} failed to calculate ratings for contest {contest_id}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Grading worker {self.worker_id} error calculating ratings for contest {contest_id}: {e}",
                                exc_info=True
                            )
                    
                except Exception as e:
                    logger.error(
                        f"Grading worker {self.worker_id} error in main loop: {e}",
                        exc_info=True
                    )
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info(f"Grading worker {self.worker_id} received shutdown signal")
        finally:
            self.running = False
            logger.info(f"Grading worker {self.worker_id} stopped")

    async def stop(self):
        """Stop the grading worker gracefully"""
        logger.info(f"Stopping grading worker {self.worker_id}...")
        self.running = False

