from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.core.agent.planner import Planner
from backend.core.github.client import GitHubClient
from backend.core.github.retriever import GitHubRetriever
from backend.core.github.service import GitHubService
from backend.core.retrieval.retriever import RetrievalResult


class TestPlannerGitHubIntegration:
    def test_engineering_history_questions_select_github_tool(self) -> None:
        planner = Planner()

        for question in [
            "Why was this feature added?",
            "Which PR introduced authentication?",
            "Who reviewed this implementation?",
            "What release introduced this change?",
        ]:
            plan = planner.plan(question)
            assert "github_retriever_tool" in plan.selected_tools


class TestGitHubClient:
    @pytest.mark.asyncio
    async def test_paginates_results_and_collects_all_pages(self) -> None:
        client = GitHubClient(token=None)
        client._client = AsyncMock()

        first_response = SimpleNamespace(
            status_code=200,
            headers={"link": '<https://api.github.com/items?page=2>; rel="next"'},
            json=lambda: [{"id": 1}],
        )
        second_response = SimpleNamespace(
            status_code=200,
            headers={},
            json=lambda: [{"id": 2}],
        )
        client._client.get = AsyncMock(side_effect=[first_response, second_response])

        results = await client.get_paginated("/items")

        assert len(results) == 2
        assert [item["id"] for item in results] == [1, 2]


class TestGitHubService:
    @pytest.mark.asyncio
    async def test_incremental_sync_passes_since_window(self) -> None:
        collector = AsyncMock()
        collector.collect_issues.return_value = []
        collector.collect_pull_requests.return_value = []
        collector.collect_reviews.return_value = []
        collector.collect_comments.return_value = []
        collector.collect_discussions.return_value = []
        collector.collect_releases.return_value = []
        collector.collect_labels.return_value = []
        collector.collect_milestones.return_value = []
        collector.collect_repository_metadata.return_value = {}

        service = GitHubService(session=AsyncMock(), collector=collector)
        repository = SimpleNamespace(
            id="repo-1",
            owner="octo",
            name="demo",
            github_last_sync_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        await service.sync_repository(repository)

        collector.collect_issues.assert_awaited_once()
        assert collector.collect_issues.await_args.kwargs["since"] == repository.github_last_sync_at


class TestGitHubRetriever:
    @pytest.mark.asyncio
    async def test_retriever_maps_matches_to_retrieval_results(self) -> None:
        service = AsyncMock()
        service.search.return_value = [
            SimpleNamespace(
                title="Auth PR",
                body="Introduced authentication",
                kind="pull_request",
                html_url="https://github.com/octo/demo/pull/1",
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
        ]
        retriever = GitHubRetriever(service=service)

        results = await retriever.retrieve("authentication", repository_id="repo-1", top_k=3)

        assert len(results) == 1
        assert isinstance(results[0], RetrievalResult)
        assert "authentication" in results[0].content.lower()
