from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.core.github.client import GitHubAPIError, GitHubClient


class GitHubCollector:
    """Collects engineering metadata from GitHub for a repository."""

    def __init__(self, client: GitHubClient | None = None) -> None:
        self._client = client or GitHubClient()

    async def collect_issues(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/repos/{owner}/{repo}/issues"
        return await self._client.get_paginated(path, params={"state": "all"}, since=since)

    async def collect_pull_requests(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/repos/{owner}/{repo}/pulls"
        return await self._client.get_paginated(path, params={"state": "all"}, since=since)

    async def collect_reviews(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        pull_requests = await self.collect_pull_requests(owner, repo, since=since)
        reviews: list[dict[str, Any]] = []
        for pull_request in pull_requests:
            number = pull_request.get("number")
            if not number:
                continue
            path = f"/repos/{owner}/{repo}/pulls/{number}/reviews"
            reviews.extend(await self._client.get_paginated(path, since=since))
        return reviews

    async def collect_comments(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/repos/{owner}/{repo}/issues/comments"
        try:
            return await self._client.get_paginated(path, since=since)
        except GitHubAPIError:
            return []

    async def collect_discussions(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/repos/{owner}/{repo}/discussions"
        try:
            return await self._client.get_paginated(path, since=since)
        except GitHubAPIError:
            return []

    async def collect_releases(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/repos/{owner}/{repo}/releases"
        return await self._client.get_paginated(path, since=since)

    async def collect_labels(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/repos/{owner}/{repo}/labels"
        return await self._client.get_paginated(path, since=since)

    async def collect_milestones(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/repos/{owner}/{repo}/milestones"
        return await self._client.get_paginated(path, params={"state": "all"}, since=since)

    async def collect_repository_metadata(
        self,
        owner: str,
        repo: str,
        *,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        path = f"/repos/{owner}/{repo}"
        return await self._client.get_json(path)
