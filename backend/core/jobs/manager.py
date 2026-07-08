from __future__ import annotations

import threading
from typing import Any

from backend.core.jobs.models import Job, JobStatus

# In-memory job storage (in production, use Redis)
_jobs: dict[str, Job] = {}
_lock = threading.Lock()


class JobManager:
    """Manages background job lifecycle.

    Stores jobs in memory for simplicity. In production, this would
    use Redis or the database.
    """

    def create_job(self, job_type: str) -> Job:
        """Create a new job.

        Args:
            job_type: The type of job (e.g. "import", "index").

        Returns:
            The created ``Job`` instance.
        """
        job = Job(type=job_type)
        with _lock:
            _jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID.

        Args:
            job_id: The job's unique identifier.

        Returns:
            The ``Job`` instance, or ``None`` if not found.
        """
        with _lock:
            return _jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        progress: float | None = None,
        step: str | None = None,
        message: str | None = None,
    ) -> None:
        """Update a job's progress fields.

        Args:
            job_id: The job's unique identifier.
            progress: Progress percentage (0-100).
            step: Current step name.
            message: Status message.
        """
        with _lock:
            job = _jobs.get(job_id)
            if job is None:
                return
            if progress is not None:
                job.progress = progress
            if step is not None:
                job.current_step = step
            if message is not None:
                job.message = message

    def complete_job(self, job_id: str, result: dict | None = None) -> None:
        """Mark a job as completed.

        Args:
            job_id: The job's unique identifier.
            result: Optional result data.
        """
        with _lock:
            job = _jobs.get(job_id)
            if job is None:
                return
            job.complete(result)

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark a job as failed.

        Args:
            job_id: The job's unique identifier.
            error: Error description.
        """
        with _lock:
            job = _jobs.get(job_id)
            if job is None:
                return
            job.fail(error)

    def list_jobs(self, limit: int = 50) -> list[dict]:
        """List recent jobs.

        Args:
            limit: Maximum number of jobs to return.

        Returns:
            A list of job dictionaries.
        """
        with _lock:
            all_jobs = list(_jobs.values())
            all_jobs.sort(key=lambda j: j.created_at, reverse=True)
            return [j.to_dict() for j in all_jobs[:limit]]


_global_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    """Get the global JobManager singleton."""
    global _global_manager  # noqa: PLW0603
    if _global_manager is None:
        _global_manager = JobManager()
    return _global_manager