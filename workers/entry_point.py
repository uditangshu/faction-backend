"""Worker entry point script"""

import asyncio
import logging
import sys
import signal
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from workers.contest_worker import ContestSubmissionWorker
from workers.grading_worker import GradingWorker
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
worker = None
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down worker...")
    shutdown_event.set()


async def main():
    """Main entry point for worker"""
    global worker
    
    # Get worker type from environment (default: "submission")
    worker_type = os.getenv("WORKER_TYPE", "submission").lower()
    
    # Simple integer worker ID (using process ID for uniqueness)
    worker_id = str(os.getpid())
    
    if worker_type == "grading":
        worker = GradingWorker(worker_id=worker_id)
        logger.info(f"Starting grading worker: {worker_id}")
    else:
        worker = ContestSubmissionWorker(worker_id=worker_id)
        logger.info(f"Starting submission worker: {worker_id}")
    
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

