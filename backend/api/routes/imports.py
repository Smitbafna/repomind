from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.core.jobs.manager import get_job_manager
from backend.core.jobs.tasks import import_repository_task
from backend.database.models import User as UserModel
from backend.schemas.auth import ImportRequest, ImportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["import"])


@router.post(
    "/import",
    response_model=ImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Import a repository",
    description="Unified import pipeline: clone, scan, parse, extract relationships, "
    "collect git history, sync GitHub, and index. Runs in the background.",
)
async def import_repository(
    payload: ImportRequest,
    session: AsyncSession = Depends(get_db),
) -> ImportResponse:
    """Import a GitHub repository using the full pipeline.

    The import runs in the background. Returns a ``job_id`` that can be
    used to track progress via ``GET /jobs/{id}``.
    """
    manager = get_job_manager()
    job = manager.create_job("import")

    # Launch background task
    asyncio.create_task(
        import_repository_task(job.id, payload.url)
    )

    return ImportResponse(
        job_id=job.id,
        status="queued",
    )