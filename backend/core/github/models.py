from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class GitHubSyncMetrics:
    """Observed metrics from a GitHub sync run."""

    api_requests: int = 0
    rate_limit_remaining: int | None = None
    rate_limit_reset: int | None = None
    sync_duration_ms: float = 0.0
    new_objects: int = 0
    updated_objects: int = 0


@dataclass(slots=True)
class GitHubSyncResult:
    """Result payload returned by the GitHub sync service."""

    repository_id: str
    status: str
    metrics: GitHubSyncMetrics = field(default_factory=GitHubSyncMetrics)
    synced_at: datetime | None = None
