from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.ingestion.clone import RepositoryCloneError
from backend.core.ingestion.service import IngestionService
from backend.database.repositories import RepositoryRepository
from backend.schemas.ingestion import (
    IngestRequest,
    IngestResponse,
    RepositoryListResponse,
    RepositoryResponse,
)

from backend.api.dependencies import get_db, get_ingestion_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_repository(
    payload: IngestRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    """Ingest a GitHub repository: clone, scan, and store metadata."""
    try:
        result = await ingestion_service.ingest(url=payload.url)
    except RepositoryCloneError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return IngestResponse(
        id=result.repository.id,
        name=result.repository.name,
        owner=result.repository.owner,
        files=result.file_count,
        path=result.repository.local_path,
        status="completed",
    )


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    session: AsyncSession = Depends(get_db),
) -> RepositoryListResponse:
    """Return all ingested repositories with their file counts."""
    repo_repo = RepositoryRepository(session)
    repositories = await repo_repo.list_all()

    items: list[RepositoryResponse] = []
    for repo in repositories:
        from backend.database.repositories import FileRepository
        file_repo = FileRepository(session)
        file_count = await file_repo.count_by_repository(repo.id)
        items.append(
            RepositoryResponse(
                id=repo.id,
                name=repo.name,
                owner=repo.owner,
                local_path=repo.local_path,
                default_branch=repo.default_branch,
                created_at=repo.created_at,
                file_count=file_count,
            )
        )

    return RepositoryListResponse(repositories=items, total=len(items))