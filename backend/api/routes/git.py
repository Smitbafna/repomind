from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db, get_git_service
from backend.core.git.service import GitService
from backend.schemas.git import (
    BlameRequest,
    BlameResponse,
    CommitFileResponse,
    CommitResponse,
    HistoryCollectResponse,
    HistoryResponse,
    TimelineEventResponse,
    TimelineResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["git"])


@router.post("/{repository_id}/history", response_model=HistoryCollectResponse)
async def collect_history(
    repository_id: str,
    git_service: GitService = Depends(get_git_service),
) -> HistoryCollectResponse:
    """Collect complete git history for a repository.

    Walks all commits, extracts author, timestamp, message, parent,
    changed files, additions, deletions, and branch information.
    """
    try:
        count = await git_service.collect_history(repository_id)
        return HistoryCollectResponse(
            repository_id=repository_id,
            commits_collected=count,
            status="completed",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{repository_id}/history", response_model=HistoryResponse)
async def get_history(
    repository_id: str,
    git_service: GitService = Depends(get_git_service),
) -> HistoryResponse:
    """Return commit history for a repository."""
    try:
        commits = await git_service.get_commits(repository_id)
        return HistoryResponse(
            repository_id=repository_id,
            total_commits=len(commits),
            commits=[
                CommitResponse(
                    id=c.id,
                    hash=c.hash,
                    author_name=c.author_name,
                    author_email=c.author_email,
                    commit_message=c.commit_message,
                    committed_at=c.committed_at,
                    parent_hash=c.parent_hash,
                    branch=c.branch,
                    files=[
                        CommitFileResponse(
                            id=f.id,
                            file_path=f.file_path,
                            change_type=f.change_type,
                            additions=f.additions,
                            deletions=f.deletions,
                        )
                        for f in c.files
                    ],
                )
                for c in commits
            ],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{repository_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    repository_id: str,
    git_service: GitService = Depends(get_git_service),
) -> TimelineResponse:
    """Return a chronological timeline of repository events."""
    try:
        events = await git_service.get_timeline(repository_id)
        return TimelineResponse(
            repository_id=repository_id,
            total_events=len(events),
            events=[
                TimelineEventResponse(
                    commit_hash=e.commit_hash,
                    author_name=e.author_name,
                    author_email=e.author_email,
                    committed_at=e.committed_at,
                    commit_message=e.commit_message,
                    affected_files=e.affected_files,
                    symbols=e.symbols,
                )
                for e in events
            ],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{repository_id}/blame", response_model=BlameResponse)
async def blame_line(
    repository_id: str,
    payload: BlameRequest,
    git_service: GitService = Depends(get_git_service),
) -> BlameResponse:
    """Get blame information for a specific line in a file.

    Returns the commit, author, timestamp, and commit message
    for the last modification of the specified line.
    """
    try:
        blame_info = await git_service.get_blame(
            repository_id=repository_id,
            file_path=payload.file,
            line_number=payload.line,
        )
        if blame_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No blame info for {payload.file}:{payload.line}",
            )

        return BlameResponse(
            commit_hash=blame_info.commit_hash,
            author_name=blame_info.author_name,
            author_email=blame_info.author_email,
            committed_at=blame_info.committed_at,
            commit_message=blame_info.commit_message,
            line_number=blame_info.line_number,
            line_content=blame_info.line_content,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc