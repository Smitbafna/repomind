from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CommitFileInfo:
    """Information about a file changed in a commit."""

    file_path: str
    change_type: str  # ADDED, MODIFIED, RENAMED, DELETED
    additions: int
    deletions: int


@dataclass(frozen=True)
class CommitInfo:
    """Information about a single commit."""

    hash: str
    author_name: str
    author_email: str
    commit_message: str
    committed_at: datetime
    parent_hash: str | None
    branch: str | None
    files: list[CommitFileInfo] = field(default_factory=list)


@dataclass(frozen=True)
class BlameInfo:
    """Information about who last modified a line."""

    commit_hash: str
    author_name: str
    author_email: str
    committed_at: datetime
    commit_message: str
    line_number: int
    line_content: str


@dataclass(frozen=True)
class TimelineEvent:
    """A single event in the repository timeline."""

    commit_hash: str
    author_name: str
    author_email: str
    committed_at: datetime
    commit_message: str
    affected_files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)