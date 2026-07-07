from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from backend.api.dependencies import get_github_service
from backend.core.github.service import GitHubService
from backend.database import models as db_models
from backend.schemas.github import (
    GitHubIssueResponse,
    GitHubPullRequestResponse,
    GitHubReleaseResponse,
    GitHubSearchRequest,
    GitHubSearchResponse,
    GitHubSyncResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["github"])


@router.post("/{repository_id}/github/sync", response_model=GitHubSyncResponse)
async def sync_github_repository(
    repository_id: str,
    github_service: GitHubService = Depends(get_github_service),
) -> GitHubSyncResponse:
    """Synchronize repository engineering metadata from GitHub."""
    repository = await github_service._session.get(db_models.Repository, repository_id)
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    result = await github_service.sync_repository(repository)
    return GitHubSyncResponse(
        repository_id=repository_id,
        status=result.status,
        synced_at=result.synced_at,
        api_requests=result.metrics.api_requests,
        rate_limit_remaining=result.metrics.rate_limit_remaining,
        rate_limit_reset=result.metrics.rate_limit_reset,
        sync_duration_ms=result.metrics.sync_duration_ms,
        new_objects=result.metrics.new_objects,
        updated_objects=result.metrics.updated_objects,
    )


@router.get("/{repository_id}/github/issues", response_model=list[GitHubIssueResponse])
async def list_github_issues(
    repository_id: str,
    github_service: GitHubService = Depends(get_github_service),
) -> list[GitHubIssueResponse]:
    """List synced GitHub issues for a repository."""
    stmt = select(db_models.GitHubIssue).where(db_models.GitHubIssue.repository_id == repository_id)
    result = await github_service._session.execute(stmt)
    issues = result.scalars().all()
    return [GitHubIssueResponse.model_validate(issue) for issue in issues]


@router.get("/{repository_id}/github/pulls", response_model=list[GitHubPullRequestResponse])
async def list_github_pull_requests(
    repository_id: str,
    github_service: GitHubService = Depends(get_github_service),
) -> list[GitHubPullRequestResponse]:
    """List synced GitHub pull requests for a repository."""
    stmt = select(db_models.GitHubPullRequest).where(
        db_models.GitHubPullRequest.repository_id == repository_id
    )
    result = await github_service._session.execute(stmt)
    pull_requests = result.scalars().all()
    return [GitHubPullRequestResponse.model_validate(pr) for pr in pull_requests]


@router.get("/{repository_id}/github/releases", response_model=list[GitHubReleaseResponse])
async def list_github_releases(
    repository_id: str,
    github_service: GitHubService = Depends(get_github_service),
) -> list[GitHubReleaseResponse]:
    """List synced GitHub releases for a repository."""
    stmt = select(db_models.GitHubRelease).where(db_models.GitHubRelease.repository_id == repository_id)
    result = await github_service._session.execute(stmt)
    releases = result.scalars().all()
    return [GitHubReleaseResponse.model_validate(release) for release in releases]


@router.post("/{repository_id}/github/search", response_model=GitHubSearchResponse)
async def search_github_repository(
    repository_id: str,
    payload: GitHubSearchRequest,
    github_service: GitHubService = Depends(get_github_service),
) -> GitHubSearchResponse:
    """Search synced GitHub engineering context for a repository."""
    matches = await github_service.search(
        repository_id=repository_id,
        query=payload.query,
        top_k=payload.top_k,
        entity_type=payload.entity_type,
    )
    return GitHubSearchResponse(
        repository_id=repository_id,
        total_results=len(matches),
        results=[
            {
                "kind": getattr(match, "__class__", type(match)).__name__,
                "title": getattr(match, "title", None) or getattr(match, "tag_name", None) or "",
                "body": getattr(match, "body", None),
                "url": getattr(match, "html_url", None),
            }
            for match in matches
        ],
    )
