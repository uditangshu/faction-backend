"""Worker entry point script"""

import asyncio
import logging
import sys
import signal
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from workers.contest_worker import ContestSubmissionWorker
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Global worker instance for signal handling
worker: ContestSubmissionWorker | None = None
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down worker...")
    shutdown_event.set()


async def main():
    """Main entry point for worker"""
    global worker
    
    # Get worker ID from environment or use default
    worker_id = os.getenv("WORKER_ID", f"{settings.APP_ENV}-worker-{os.getpid()}")
    
    # Create worker instance
    worker = ContestSubmissionWorker(worker_id=worker_id)
    
    try:
        # Initialize worker
        await worker.initialize()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create task to monitor shutdown event
        async def monitor_shutdown():
            await shutdown_event.wait()
            await worker.stop()
        
        # Run worker and monitor shutdown in parallel
        await asyncio.gather(
            worker.run(),
            monitor_shutdown(),
            return_exceptions=True
        )
        
    except Exception as e:
        logger.error(f"Worker failed to start: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Worker process exiting")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

