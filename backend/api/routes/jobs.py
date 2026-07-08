from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.jobs.manager import get_job_manager
from backend.schemas.auth import JobResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "",
    response_model=list[JobResponse],
    summary="List jobs",
    description="Return all recent background jobs with their current status.",
)
async def list_jobs(limit: int = 50) -> list[JobResponse]:
    """Return all recent background jobs."""
    manager = get_job_manager()
    jobs = manager.list_jobs(limit=limit)
    return [JobResponse(**job) for job in jobs]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    description="Return the current status and progress of a background job.",
)
async def get_job(job_id: str) -> JobResponse:
    """Get the status of a specific background job.

    Returns progress, current_step, elapsed_time, errors, and completion status.
    """
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )
    return JobResponse(**job.to_dict())