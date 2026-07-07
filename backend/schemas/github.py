from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GitHubSearchRequest(BaseModel):
    """Request body for GitHub search."""

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    entity_type: str | None = None


class GitHubSyncResponse(BaseModel):
    """Response payload after syncing GitHub data."""

    repository_id: str
    status: str
    synced_at: datetime | None = None
    api_requests: int = 0
    rate_limit_remaining: int | None = None
    rate_limit_reset: int | None = None
    sync_duration_ms: float = 0.0
    new_objects: int = 0
    updated_objects: int = 0


class GitHubIssueResponse(BaseModel):
    id: str
    number: int
    title: str
    body: str | None = None
    state: str = "open"
    author_login: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    html_url: str | None = None
    labels: str | None = None

    model_config = {"from_attributes": True}


class GitHubPullRequestResponse(BaseModel):
    id: str
    number: int
    title: str
    body: str | None = None
    state: str = "open"
    author_login: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    merged_at: datetime | None = None
    closed_at: datetime | None = None
    draft: bool = False
    html_url: str | None = None
    labels: str | None = None
    merge_commit_sha: str | None = None

    model_config = {"from_attributes": True}


class GitHubReleaseResponse(BaseModel):
    id: str
    tag_name: str
    name: str | None = None
    body: str | None = None
    draft: bool = False
    prerelease: bool = False
    published_at: datetime | None = None
    html_url: str | None = None

    model_config = {"from_attributes": True}


class GitHubSearchResponse(BaseModel):
    repository_id: str
    total_results: int
    results: list[dict[str, object]]
