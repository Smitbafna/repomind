from __future__ import annotations

from backend.core.github.service import GitHubService


class GitHubSearchService:
    """Convenience wrapper for repository scoped GitHub searches."""

    def __init__(self, service: GitHubService | None = None) -> None:
        self._service = service

    async def search(self, repository_id: str, query: str, *, top_k: int = 10) -> list[object]:
        if self._service is None:
            return []
        return await self._service.search(repository_id=repository_id, query=query, top_k=top_k)
