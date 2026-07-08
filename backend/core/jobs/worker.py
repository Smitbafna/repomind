"""Background worker for processing async jobs."""
import asyncio
import logging
import signal
import sys

from backend.config.settings import get_settings
from backend.core.jobs.manager import get_job_manager
from backend.core.jobs.tasks import (
    import_repository_task,
    index_repository_task,
    extract_relationships_task,
    sync_github_task,
)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
_shutdown_event = asyncio.Event()


async def process_job(job_id: str, job_type: str, job_data: dict) -> None:
    """Process a single job based on its type.

    Args:
        job_id: The job ID.
        job_type: The type of job.
        job_data: The job data/parameters.
    """
    manager = get_job_manager()

    try:
        if job_type == "import":
            await import_repository_task(
                job_id=job_id,
                url=job_data.get("url", ""),
                user_id=job_data.get("user_id"),
            )
        elif job_type == "index":
            await index_repository_task(
                job_id=job_id,
                repository_id=job_data.get("repository_id", ""),
            )
        elif job_type == "relationships":
            await extract_relationships_task(
                job_id=job_id,
                repository_id=job_data.get("repository_id", ""),
            )
        elif job_type == "github_sync":
            await sync_github_task(
                job_id=job_id,
                repository_id=job_data.get("repository_id", ""),
            )
        else:
            logger.warning("Unknown job type: %s", job_type)
            manager.fail_job(job_id, f"Unknown job type: {job_type}")
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        manager.fail_job(job_id, str(exc))


async def main() -> None:
    """Main worker loop that polls for jobs."""
    settings = get_settings()
    manager = get_job_manager()

    logger.info("Worker started, waiting for jobs...")

    # Setup signal handlers for graceful shutdown
    def handle_shutdown(signum, frame):
        logger.info("Received shutdown signal, finishing in-progress jobs...")
        _shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Simple polling loop (in production, use Redis pub/sub or similar)
    while not _shutdown_event.is_set():
        try:
            # Check for pending jobs
            jobs = manager.list_jobs(limit=100)
            pending_jobs = [
                j for j in jobs
                if j.get("status") == "pending"
            ]

            for job_dict in pending_jobs:
                if _shutdown_event.is_set():
                    break

                job_id = job_dict["id"]
                job_type = job_dict["type"]
                job_data = job_dict.get("data", {})

                logger.info("Processing job %s of type %s", job_id, job_type)
                await process_job(job_id, job_type, job_data)

            # Wait before next poll
            try:
                await asyncio.wait_for(
                    _shutdown_event.wait(),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                pass  # Normal polling cycle

        except Exception as exc:
            logger.exception("Error in worker loop: %s", exc)
            await asyncio.sleep(5)

    logger.info("Worker shutting down gracefully...")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())