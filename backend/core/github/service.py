from __future__ import annotations

import inspect
import logging
import time
from datetime import datetime, timezone
from typing import Any

from backend.core.github.collector import GitHubCollector
from backend.core.github.models import GitHubSyncMetrics, GitHubSyncResult
from backend.database import models as db_models

logger = logging.getLogger(__name__)


class GitHubService:
    """Persists GitHub engineering intelligence into the local database."""

    def __init__(self, session: Any, collector: GitHubCollector | None = None) -> None:
        self._session = session
        self._collector = collector or GitHubCollector()

    async def sync_repository(self, repository: Any, *, force: bool = False) -> GitHubSyncResult:
        """Synchronize GitHub issues, pull requests, reviews, comments, releases, labels."""
        repo_model = self._coerce_repository(repository)
        if repo_model is None:
            raise ValueError("Repository could not be resolved")

        owner = getattr(repo_model, "owner", None) or getattr(repository, "owner", None)
        name = getattr(repo_model, "name", None) or getattr(repository, "name", None)
        if not owner or not name:
            raise ValueError("Repository owner/name are required")

        since = None if force else getattr(repo_model, "github_last_sync_at", None)
        previous_sync_at = since
        started_at = time.monotonic()
        metrics = GitHubSyncMetrics()

        issues = await self._collector.collect_issues(owner, name, since=previous_sync_at)
        await self._persist_issues(repo_model, issues)
        self._count_objects(metrics, issues, previous_sync_at)

        pull_requests = await self._collector.collect_pull_requests(owner, name, since=previous_sync_at)
        await self._persist_pull_requests(repo_model, pull_requests)
        self._count_objects(metrics, pull_requests, previous_sync_at)

        reviews = await self._collector.collect_reviews(owner, name, since=previous_sync_at)
        await self._persist_reviews(repo_model, reviews)
        self._count_objects(metrics, reviews, previous_sync_at)

        comments = await self._collector.collect_comments(owner, name, since=previous_sync_at)
        await self._persist_comments(repo_model, comments)
        self._count_objects(metrics, comments, previous_sync_at)

        discussions = await self._collector.collect_discussions(owner, name, since=previous_sync_at)
        await self._persist_discussions(repo_model, discussions)
        self._count_objects(metrics, discussions, previous_sync_at)

        releases = await self._collector.collect_releases(owner, name, since=previous_sync_at)
        await self._persist_releases(repo_model, releases)
        self._count_objects(metrics, releases, previous_sync_at)

        labels = await self._collector.collect_labels(owner, name, since=previous_sync_at)
        await self._persist_labels(repo_model, labels)
        self._count_objects(metrics, labels, previous_sync_at)

        milestones = await self._collector.collect_milestones(owner, name, since=previous_sync_at)
        await self._persist_milestones(repo_model, milestones)
        self._count_objects(metrics, milestones, previous_sync_at)

        metadata = await self._collector.collect_repository_metadata(owner, name, since=since)
        if metadata:
            setattr(repo_model, "default_branch", metadata.get("default_branch"))

        if hasattr(repo_model, "_sa_instance_state"):
            repo_model.github_last_sync_at = datetime.now(timezone.utc)
        metrics.sync_duration_ms = round((time.monotonic() - started_at) * 1000, 2)
        metrics.api_requests = getattr(self._collector._client, "_request_count", 0)
        metrics.rate_limit_remaining = getattr(self._collector._client, "_rate_limit_remaining", None)
        metrics.rate_limit_reset = getattr(self._collector._client, "_rate_limit_reset", None)

        await self._await_if_needed(self._session.add(repo_model))
        await self._await_if_needed(self._session.flush())
        await self._await_if_needed(self._session.commit())

        logger.info(
            "GitHub sync completed for %s/%s in %.2fms",
            owner,
            name,
            metrics.sync_duration_ms,
        )
        return GitHubSyncResult(
            repository_id=repo_model.id,
            status="completed",
            metrics=metrics,
            synced_at=repo_model.github_last_sync_at,
        )

    async def search(
        self,
        repository_id: str,
        query: str,
        *,
        top_k: int = 10,
        entity_type: str | None = None,
    ) -> list[Any]:
        """Search synced GitHub objects using simple text matching."""
        if not query:
            return []
        lowered = query.lower()
        results: list[Any] = []
        for model in self._iter_search_models(entity_type):
            stmt = self._build_search_stmt(model, repository_id, lowered)
            if stmt is None:
                continue
            result = await self._session.execute(stmt)
            rows = result.scalars().all()
            results.extend(rows)
            if len(results) >= top_k:
                break
        return results[:top_k]

    async def _persist_issues(self, repository: Any, issues: list[dict[str, Any]]) -> None:
        for payload in issues:
            model = db_models.GitHubIssue(
                repository_id=repository.id,
                number=payload.get("number", 0),
                title=payload.get("title", ""),
                body=payload.get("body"),
                state=payload.get("state", "open"),
                author_login=(payload.get("user") or {}).get("login"),
                created_at=self._parse_datetime(payload.get("created_at")),
                updated_at=self._parse_datetime(payload.get("updated_at")),
                closed_at=self._parse_datetime(payload.get("closed_at")),
                html_url=payload.get("html_url"),
                labels=",".join(label.get("name", "") for label in payload.get("labels", []) if isinstance(label, dict)),
                pull_request_url=(payload.get("pull_request") or {}).get("url"),
            )
            self._session.add(model)

    async def _persist_pull_requests(self, repository: Any, pull_requests: list[dict[str, Any]]) -> None:
        for payload in pull_requests:
            model = db_models.GitHubPullRequest(
                repository_id=repository.id,
                number=payload.get("number", 0),
                title=payload.get("title", ""),
                body=payload.get("body"),
                state=payload.get("state", "open"),
                author_login=(payload.get("user") or {}).get("login"),
                created_at=self._parse_datetime(payload.get("created_at")),
                updated_at=self._parse_datetime(payload.get("updated_at")),
                merged_at=self._parse_datetime(payload.get("merged_at")),
                closed_at=self._parse_datetime(payload.get("closed_at")),
                draft=bool(payload.get("draft")),
                html_url=payload.get("html_url"),
                labels=",".join(label.get("name", "") for label in payload.get("labels", []) if isinstance(label, dict)),
                merge_commit_sha=payload.get("merge_commit_sha"),
                base_ref=(payload.get("base") or {}).get("ref"),
                head_ref=(payload.get("head") or {}).get("ref"),
            )
            self._session.add(model)

    async def _persist_reviews(self, repository: Any, reviews: list[dict[str, Any]]) -> None:
        for payload in reviews:
            model = db_models.GitHubReview(
                repository_id=repository.id,
                pull_request_number=payload.get("pull_request_url", "").split("/")[-1] or 0,
                reviewer_login=(payload.get("user") or {}).get("login"),
                state=payload.get("state", "commented"),
                body=payload.get("body"),
                submitted_at=self._parse_datetime(payload.get("submitted_at")),
                commit_id=payload.get("commit_id"),
                html_url=payload.get("html_url"),
            )
            self._session.add(model)

    async def _persist_comments(self, repository: Any, comments: list[dict[str, Any]]) -> None:
        for payload in comments:
            model = db_models.GitHubComment(
                repository_id=repository.id,
                subject_type="issue",
                subject_number=payload.get("issue_url", "").split("/")[-1] or 0,
                body=payload.get("body"),
                author_login=(payload.get("user") or {}).get("login"),
                created_at=self._parse_datetime(payload.get("created_at")),
                updated_at=self._parse_datetime(payload.get("updated_at")),
                html_url=payload.get("html_url"),
                commit_id=payload.get("commit_id"),
            )
            self._session.add(model)

    async def _persist_discussions(self, repository: Any, discussions: list[dict[str, Any]]) -> None:
        for payload in discussions:
            model = db_models.GitHubDiscussion(
                repository_id=repository.id,
                number=payload.get("number", 0),
                title=payload.get("title", ""),
                body=payload.get("body"),
                state=payload.get("state", "open"),
                author_login=(payload.get("user") or {}).get("login"),
                created_at=self._parse_datetime(payload.get("created_at")),
                updated_at=self._parse_datetime(payload.get("updated_at")),
                html_url=payload.get("html_url"),
            )
            self._session.add(model)

    async def _persist_releases(self, repository: Any, releases: list[dict[str, Any]]) -> None:
        for payload in releases:
            model = db_models.GitHubRelease(
                repository_id=repository.id,
                tag_name=payload.get("tag_name", ""),
                name=payload.get("name"),
                body=payload.get("body"),
                draft=bool(payload.get("draft")),
                prerelease=bool(payload.get("prerelease")),
                published_at=self._parse_datetime(payload.get("published_at")),
                html_url=payload.get("html_url"),
            )
            self._session.add(model)

    async def _persist_labels(self, repository: Any, labels: list[dict[str, Any]]) -> None:
        for payload in labels:
            model = db_models.GitHubLabel(
                repository_id=repository.id,
                name=payload.get("name", ""),
                color=payload.get("color"),
                description=payload.get("description"),
                default=bool(payload.get("default")),
            )
            self._session.add(model)

    async def _persist_milestones(self, repository: Any, milestones: list[dict[str, Any]]) -> None:
        for payload in milestones:
            model = db_models.GitHubLabel(
                repository_id=repository.id,
                name=payload.get("title", ""),
                color="",
                description=payload.get("description"),
                default=False,
            )
            self._session.add(model)

    def _coerce_repository(self, repository: Any) -> Any:
        if hasattr(repository, "id") and hasattr(repository, "owner") and hasattr(repository, "name"):
            return repository
        return None

    @staticmethod
    def _count_objects(metrics: GitHubSyncMetrics, items: list[Any], since: datetime | None) -> None:
        if since is None:
            metrics.new_objects += len(items)
        else:
            metrics.updated_objects += len(items)

    @staticmethod
    async def _await_if_needed(value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    def _iter_search_models(self, entity_type: str | None) -> list[type[Any]]:
        if entity_type == "issue":
            return [db_models.GitHubIssue]
        if entity_type == "pull_request":
            return [db_models.GitHubPullRequest]
        if entity_type == "review":
            return [db_models.GitHubReview]
        if entity_type == "discussion":
            return [db_models.GitHubDiscussion]
        if entity_type == "release":
            return [db_models.GitHubRelease]
        return [
            db_models.GitHubIssue,
            db_models.GitHubPullRequest,
            db_models.GitHubReview,
            db_models.GitHubComment,
            db_models.GitHubDiscussion,
            db_models.GitHubRelease,
        ]

    def _build_search_stmt(self, model: type[Any], repository_id: str, lowered: str):
        from sqlalchemy import or_, select

        if model is db_models.GitHubIssue:
            return select(model).where(
                model.repository_id == repository_id,
                or_(
                    model.title.ilike(f"%{lowered}%"),
                    model.body.ilike(f"%{lowered}%"),
                ),
            )
        if model is db_models.GitHubPullRequest:
            return select(model).where(
                model.repository_id == repository_id,
                or_(
                    model.title.ilike(f"%{lowered}%"),
                    model.body.ilike(f"%{lowered}%"),
                ),
            )
        if model is db_models.GitHubReview:
            return select(model).where(
                model.repository_id == repository_id,
                or_(
                    model.body.ilike(f"%{lowered}%"),
                    model.reviewer_login.ilike(f"%{lowered}%"),
                ),
            )
        if model is db_models.GitHubComment:
            return select(model).where(
                model.repository_id == repository_id,
                model.body.ilike(f"%{lowered}%"),
            )
        if model is db_models.GitHubDiscussion:
            return select(model).where(
                model.repository_id == repository_id,
                or_(
                    model.title.ilike(f"%{lowered}%"),
                    model.body.ilike(f"%{lowered}%"),
                ),
            )
        if model is db_models.GitHubRelease:
            return select(model).where(
                model.repository_id == repository_id,
                or_(
                    model.tag_name.ilike(f"%{lowered}%"),
                    model.body.ilike(f"%{lowered}%"),
                ),
            )
        return None
