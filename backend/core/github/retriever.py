from __future__ import annotations

from backend.core.github.service import GitHubService
from backend.core.retrieval.retriever import BaseRetriever, RetrievalResult


class GitHubRetriever(BaseRetriever):
    """Retrieves GitHub engineering context from synced repository metadata."""

    def __init__(self, service: GitHubService | None = None) -> None:
        self._service = service

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        repository_id: str | None = None,
    ) -> list[RetrievalResult]:
        if not query or not repository_id:
            return []
        if self._service is None:
            return []

        matches = await self._service.search(
            repository_id=repository_id,
            query=query,
            top_k=top_k,
        )
        results: list[RetrievalResult] = []
        for match in matches:
            content = self._render_content(match)
            if not content:
                continue
            results.append(
                RetrievalResult(
                    content=content,
                    score=1.0,
                    document_type=self._document_type(match),
                    file="",
                    symbol=getattr(match, "title", "") or getattr(match, "tag_name", ""),
                )
            )
        return results

    @staticmethod
    def _render_content(match: object) -> str:
        title = getattr(match, "title", None) or getattr(match, "tag_name", None) or ""
        body = getattr(match, "body", None) or ""
        if title and body:
            return f"{title}\n\n{body}"
        if title:
            return title
        return str(body)

    @staticmethod
    def _document_type(match: object) -> str:
        if hasattr(match, "tag_name"):
            return "release"
        if hasattr(match, "reviewer_login"):
            return "review"
        if hasattr(match, "subject_type"):
            return "comment"
        if hasattr(match, "merge_commit_sha"):
            return "pull_request"
        if hasattr(match, "number") and hasattr(match, "body") and hasattr(match, "author_login"):
            return "issue"
        return "github"
