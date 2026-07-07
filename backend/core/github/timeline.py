from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class GitHubTimelineEntry:
    """Represents a timeline event derived from GitHub metadata."""

    title: str
    kind: str
    created_at: str | None = None


class GitHubTimelineBuilder:
    """Builds a lightweight timeline from GitHub objects."""

    def build(self, items: list[Any]) -> list[GitHubTimelineEntry]:
        timeline: list[GitHubTimelineEntry] = []
        for item in items:
            created_at = getattr(item, "created_at", None)
            title = getattr(item, "title", None) or getattr(item, "tag_name", None) or ""
            kind = getattr(item, "kind", "github")
            timeline.append(
                GitHubTimelineEntry(
                    title=title,
                    kind=kind,
                    created_at=str(created_at) if created_at else None,
                )
            )
        return timeline
