from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub API rejects a request."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub rate limiting blocks the request."""


class GitHubClient:
    """Thin, authenticated wrapper around the GitHub REST API."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = get_settings()
        self._token = token or self._settings.github_token
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._request_count = 0
        self._rate_limit_remaining: int | None = None
        self._rate_limit_reset: int | None = None

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._request("GET", path, params=params)
        return response.json()

    async def get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        since: datetime | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all pages from a paginated GitHub endpoint."""
        query_params = dict(params or {})
        if since is not None:
            query_params["since"] = since.isoformat()
        query_params["per_page"] = per_page

        items: list[dict[str, Any]] = []
        page = 1
        while True:
            query_params["page"] = page
            response = await self._request("GET", path, params=query_params)
            payload = response.json()
            if isinstance(payload, list):
                items.extend(payload)
            elif payload:
                items.append(payload)
            if not self._has_next_page(response.headers):
                break
            page += 1

        return items

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "repomind/0.1",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"

        for attempt in range(3):
            response = await self._client.get(url, headers=headers, params=params)
            self._request_count += 1
            self._rate_limit_remaining = self._parse_int_header(
                response.headers.get("x-ratelimit-remaining")
            )
            self._rate_limit_reset = self._parse_int_header(
                response.headers.get("x-ratelimit-reset")
            )

            if response.status_code == 429:
                await self._sleep_for_rate_limit(response)
                continue
            if response.status_code >= 400:
                logger.warning("GitHub API request failed: %s %s", response.status_code, response.text)
                raise GitHubAPIError(response.text)
            return response

        raise GitHubRateLimitError("GitHub API rate limiting exceeded")

    @staticmethod
    def _has_next_page(headers: httpx.Headers) -> bool:
        link_header = headers.get("link", "")
        return 'rel="next"' in link_header

    async def _sleep_for_rate_limit(self, response: httpx.Response) -> None:
        retry_after = self._parse_int_header(response.headers.get("retry-after"))
        reset_seconds = self._rate_limit_reset - int(datetime.now(timezone.utc).timestamp())
        wait_seconds = max(retry_after or 0, reset_seconds if reset_seconds > 0 else 5)
        await asyncio.sleep(wait_seconds)

    @staticmethod
    def _parse_int_header(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None
