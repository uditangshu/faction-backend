"""Contest grading worker - calculates ranks and ratings after submissions are processed"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import UUID
from typing import List
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
        self.queue_name_pattern = "contest:submissions:*"
        self.check_interval = 30  # Check every 30 seconds
        self.empty_threshold = 60  # Queues must be empty for 60 seconds before grading

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            redis_client = await get_redis()
            self.redis_service = RedisService(redis_client)
            logger.info(f"Grading worker {self.worker_id} initialized with Redis connection")
        except Exception as e:
            logger.error(f"Failed to initialize Redis for grading worker {self.worker_id}: {e}")
            raise

    async def get_contest_queues(self) -> List[str]:
        """
        Get all contest submission queue names that have items.
        Uses Redis SCAN to find all queues matching the pattern.
        """
        if not self.redis_service:
            return []
        
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

    async def are_all_queues_empty(self) -> bool:
        """
        Check if all contest submission queues are empty.
        
        Returns:
            bool: True if all queues are empty, False otherwise
        """
        if not self.redis_service:
            return True
        
        try:
            queues = await self.get_contest_queues()
            return len(queues) == 0
        except Exception as e:
            logger.error(f"Failed to check queue status: {e}")
            return False

    async def get_all_contest_ids_from_queues(self) -> List[UUID]:
        """
        Get all contest IDs that have queues (even if empty).
        Used to identify which contests need grading.
        
        Returns:
            List of contest UUIDs
        """
        if not self.redis_service:
            return []
        
        try:
            contest_ids = []
            cursor = 0
            pattern = "contest:submissions:*"
            
            while True:
                cursor, keys = await self.redis_service.client.scan(
                    cursor, match=pattern, count=100
                )
                for key in keys:
                    # Extract contest_id from key: contest:submissions:{contest_id}
                    try:
                        contest_id_str = key.split(":")[-1]
                        contest_ids.append(UUID(contest_id_str))
                    except (ValueError, IndexError):
                        continue
                
                if cursor == 0:
                    break
            
            # Remove duplicates
            return list(set(contest_ids))
        except Exception as e:
            logger.error(f"Failed to get contest IDs from queues: {e}")
            return []

    async def calculate_ratings_for_contests(self, contest_ids: List[UUID]) -> None:
        """
        Calculate and update ratings for all specified contests.
        
        Args:
            contest_ids: List of contest IDs to process
        """
        if not contest_ids:
            return
        
        try:
            async with AsyncSessionLocal() as db:
                for contest_id in contest_ids:
                    try:
                        logger.info(
                            f"Grading worker {self.worker_id} calculating ratings for contest {contest_id}"
                        )
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
                f"Grading worker {self.worker_id} error in calculate_ratings_for_contests: {e}",
                exc_info=True
            )

    async def run(self):
        """Main grading worker loop"""
        self.running = True
        logger.info(f"Grading worker {self.worker_id} started")
        
        # Track contest IDs that have been graded (to avoid duplicate calculations)
        graded_contests = set()
        
        # Track when queues became empty (to ensure they stay empty for threshold period)
        queues_empty_since = None
        
        try:
            while self.running:
                try:
                    # Check if all queues are empty
                    all_empty = await self.are_all_queues_empty()
                    
                    if all_empty:
                        current_time = asyncio.get_event_loop().time()
                        
                        # Track when queues became empty
                        if queues_empty_since is None:
                            queues_empty_since = current_time
                            logger.debug(f"Queues became empty at {current_time}")
                        
                        # Check if queues have been empty long enough
                        time_empty = current_time - queues_empty_since
                        
                        if time_empty >= self.empty_threshold:
                            # Get all contest IDs that had queues
                            all_contest_ids = await self.get_all_contest_ids_from_queues()
                            
                            # Calculate ratings for contests that haven't been graded yet
                            ungraded_contests = [
                                cid for cid in all_contest_ids 
                                if cid not in graded_contests
                            ]
                            
                            if ungraded_contests:
                                logger.info(
                                    f"Grading worker {self.worker_id}: All queues empty for {time_empty:.1f}s. "
                                    f"Grading {len(ungraded_contests)} contests"
                                )
                                await self.calculate_ratings_for_contests(ungraded_contests)
                                graded_contests.update(ungraded_contests)
                            else:
                                logger.debug(
                                    f"Grading worker {self.worker_id}: All contests already graded"
                                )
                        else:
                            logger.debug(
                                f"Grading worker {self.worker_id}: Queues empty for {time_empty:.1f}s "
                                f"(need {self.empty_threshold}s)"
                            )
                    else:
                        # Queues are not empty, reset the timer
                        if queues_empty_since is not None:
                            logger.debug("Queues are no longer empty, resetting timer")
                            queues_empty_since = None
                        
                        # Remove contests from graded set if queues have items again
                        # (in case new submissions come in)
                        active_queues = await self.get_contest_queues()
                        for queue_name in active_queues:
                            try:
                                contest_id_str = queue_name.split(":")[-1]
                                contest_id = UUID(contest_id_str)
                                graded_contests.discard(contest_id)
                            except (ValueError, IndexError):
                                pass
                    
                    # Wait before checking again
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(
                        f"Grading worker {self.worker_id} error in main loop: {e}",
                        exc_info=True
                    )
                    await asyncio.sleep(self.check_interval)
                    
        except KeyboardInterrupt:
            logger.info(f"Grading worker {self.worker_id} received shutdown signal")
        finally:
            self.running = False
            logger.info(f"Grading worker {self.worker_id} stopped")

    async def stop(self):
        """Stop the grading worker gracefully"""
        logger.info(f"Stopping grading worker {self.worker_id}...")
        self.running = False

