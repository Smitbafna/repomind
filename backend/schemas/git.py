from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CommitFileResponse(BaseModel):
    """A file changed in a commit."""

    id: str
    file_path: str
    change_type: str
    additions: int
    deletions: int

    model_config = {"from_attributes": True}


class CommitResponse(BaseModel):
    """A single commit in API responses."""

    id: str
    hash: str
    author_name: str
    author_email: str
    commit_message: str
    committed_at: datetime
    parent_hash: str | None = None
    branch: str | None = None
    files: list[CommitFileResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    """Response containing commit history."""

    repository_id: str
    total_commits: int
    commits: list[CommitResponse]


class HistoryCollectResponse(BaseModel):
    """Response after collecting git history."""

    repository_id: str
    commits_collected: int
    status: str = "completed"


class TimelineEventResponse(BaseModel):
    """A single timeline event."""

    commit_hash: str
    author_name: str
    author_email: str
    committed_at: datetime | None = None
    commit_message: str
    affected_files: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)


class TimelineResponse(BaseModel):
    """Response containing repository timeline."""

    repository_id: str
    total_events: int
    events: list[TimelineEventResponse]


class BlameRequest(BaseModel):
    """Request body for blame endpoint."""

    file: str = Field(..., description="Relative file path within the repository")
    line: int = Field(..., description="1-based line number", ge=1)


class BlameResponse(BaseModel):
    """Response from blame endpoint."""

    commit_hash: str
    author_name: str
    author_email: str
    committed_at: datetime
    commit_message: str
    line_number: int
    line_content: str