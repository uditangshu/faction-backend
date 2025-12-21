"""Contest submission worker"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import UUID
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.integrations.redis_client import get_redis, RedisService
from app.db.attempt_calls import create_attempt
from app.core.config import settings

logger = logging.getLogger(__name__)


class ContestSubmissionWorker:
    """Worker that processes contest submissions from Redis queue"""

    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.redis_service: RedisService | None = None
        self.running = False
        self.queue_name_pattern = "contest:submissions:*"
        self.poll_interval = 1  # seconds
        self.blocking_timeout = 5  # seconds for BRPOP

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            redis_client = await get_redis()
            self.redis_service = RedisService(redis_client)
            logger.info(f"Worker {self.worker_id} initialized with Redis connection")
        except Exception as e:
            logger.error(f"Failed to initialize Redis for worker {self.worker_id}: {e}")
            raise

    async def process_submission(self, submission: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Process a single submission and save to database.
        
        Args:
            submission: Submission data from queue
            db: Database session
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user_id = UUID(submission["user_id"])
            question_id = UUID(submission["question_id"])
            
            await create_attempt(
                db=db,
                user_id=user_id,
                question_id=question_id,
                user_answer=submission["user_answer"],
                is_correct=submission["is_correct"],
                marks_obtained=submission["marks_obtained"],
                time_taken=submission["time_taken"],
                hint_used=submission.get("hint_used", False),
            )
            
            logger.info(
                f"Worker {self.worker_id} processed submission: "
                f"user={user_id}, question={question_id}, correct={submission['is_correct']}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Worker {self.worker_id} failed to process submission: {e}",
                exc_info=True
            )
            return False

    async def get_contest_queues(self) -> list[str]:
        """
        Get all contest submission queue names that have items.
        Uses Redis SCAN to find all queues matching the pattern.
        """
        try:
            queues = []
            cursor = 0
            pattern = "contest:submissions:*"
            
            # Use SCAN instead of KEYS for better performance
            while True:
                cursor, keys = await self.redis_service.client.scan(
                    cursor, match=pattern, count=100
                )
                for key in keys:
                    # Check if queue has items
                    length = await self.redis_service.get_queue_length(key)
                    if length > 0:
                        queues.append(key)
                
                if cursor == 0:
                    break
            
            return queues
        except Exception as e:
            logger.error(f"Failed to get contest queues: {e}")
            return []

    async def pop_from_queue_atomic(self, queue_name: str) -> Dict[str, Any] | None:
        """
        Atomically pop a value from the queue using BRPOP (blocking right pop).
        This is atomic and safe for multiple workers.
        
        BRPOP is atomic at the Redis level - only one worker will receive each item,
        even when multiple workers are polling the same queue simultaneously.
        
        Args:
            queue_name: Name of the queue/list
            
        Returns:
            Popped value or None if timeout
        """
        try:
            # Use the atomic BRPOP method from RedisService
            # This blocks until an item is available or timeout, and is atomic
            result = await self.redis_service.pop_from_queue_blocking(
                queue_name, 
                timeout=self.blocking_timeout
            )
            
            if result is None:
                return None
            
            # pop_from_queue_blocking returns (queue_name, value) tuple
            _, value = result
            return value
                
        except Exception as e:
            logger.error(f"Error popping from queue {queue_name}: {e}")
            return None

    async def run(self):
        """Main worker loop"""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")
        
        try:
            while self.running:
                try:
                    # Get all active contest queues
                    queues = await self.get_contest_queues()
                    
                    if not queues:
                        # No active queues, wait before checking again
                        await asyncio.sleep(self.poll_interval * 5)
                        continue
                    
                    # Process queues in round-robin fashion using atomic BRPOP
                    processed_any = False
                    for queue_name in queues:
                        if not self.running:
                            break
                        
                        # Atomically pop one item from this queue
                        # BRPOP is atomic - safe for multiple workers
                        submission = await self.pop_from_queue_atomic(queue_name)
                        
                        if submission:
                            processed_any = True
                            # Process submission with database session
                            async with AsyncSessionLocal() as db:
                                success = await self.process_submission(submission, db)
                                
                                if not success:
                                    logger.warning(
                                        f"Worker {self.worker_id} failed to process submission from {queue_name}"
                                    )
                            # Break after processing one item to allow round-robin
                            break
                    
                    # If no items were processed, wait a bit before checking again
                    if not processed_any:
                        await asyncio.sleep(self.poll_interval)
                        
                except Exception as e:
                    logger.error(
                        f"Worker {self.worker_id} error in main loop: {e}",
                        exc_info=True
                    )
                    await asyncio.sleep(self.poll_interval * 5)
                    
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} received shutdown signal")
        finally:
            self.running = False
            logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"Stopping worker {self.worker_id}...")
        self.running = False

