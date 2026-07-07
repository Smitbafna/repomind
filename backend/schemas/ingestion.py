from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    """Request body for the repository ingestion endpoint."""

    url: str = Field(
        ...,
        description="GitHub repository URL (e.g. https://github.com/owner/repo)",
        examples=["https://github.com/fastapi/fastapi"],
    )


class FileResponse(BaseModel):
    """A single file record returned in API responses."""

    id: str
    path: str
    extension: str | None = None
    size: int
    is_binary: bool

    model_config = {"from_attributes": True}


class IngestResponse(BaseModel):
    """Response returned after a repository is ingested."""

    id: str
    name: str
    owner: str
    files: int
    path: str
    status: str = "completed"


class RepositoryResponse(BaseModel):
    """A repository record returned in list/detail responses."""

    id: str
    name: str
    owner: str
    local_path: str
    default_branch: str | None = None
    created_at: datetime
    file_count: int = 0

    model_config = {"from_attributes": True}


class RepositoryListResponse(BaseModel):
    """Wrapper for a list of repositories."""

    repositories: list[RepositoryResponse]
    total: int