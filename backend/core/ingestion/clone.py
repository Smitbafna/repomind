from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import git

from backend.config.settings import get_settings
from backend.core.ingestion.types import ParsedGitHubUrl

logger = logging.getLogger(__name__)

_GITHUB_URL_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[a-zA-Z0-9._-]+)/(?P<name>[a-zA-Z0-9._-]+?)(?:\.git)?/?$"
)


class RepositoryCloneError(Exception):
    """Raised when cloning or parsing a GitHub URL fails."""


class RepositoryCloner:
    """Responsible for parsing GitHub URLs and cloning repositories."""

    @staticmethod
    def parse_github_url(url: str) -> ParsedGitHubUrl:
        """Parse a GitHub URL into owner/repo components.

        Args:
            url: The GitHub repository URL.

        Returns:
            A ``ParsedGitHubUrl`` named tuple.

        Raises:
            RepositoryCloneError: If the URL does not match the expected pattern.
        """
        match = _GITHUB_URL_PATTERN.match(url.strip())
        if not match:
            raise RepositoryCloneError(
                f"Invalid GitHub URL: '{url}'. "
                "Expected format: https://github.com/owner/repo"
            )
        return ParsedGitHubUrl(
            owner=match.group("owner"),
            name=match.group("name"),
            url=url.strip(),
        )

    @staticmethod
    def clone(parsed: ParsedGitHubUrl, target_dir: Path) -> Path:
        """Clone a repository to the local filesystem.

        Args:
            parsed: The parsed GitHub URL components.
            target_dir: Directory under which the clone will be placed.

        Returns:
            The path to the cloned repository root.

        Raises:
            RepositoryCloneError: If cloning fails.
        """
        repo_path = target_dir / parsed.owner / parsed.name

        if repo_path.exists():
            logger.info("Repository already exists at %s, pulling latest…", repo_path)
            try:
                repo = git.Repo(repo_path)
                origin = repo.remotes.origin
                origin.pull()
                return repo_path
            except git.GitCommandError as exc:
                raise RepositoryCloneError(
                    f"Failed to pull existing repository: {exc}"
                ) from exc

        repo_path.parent.mkdir(parents=True, exist_ok=True)

        clone_url = f"https://github.com/{parsed.owner}/{parsed.name}.git"
        logger.info("Cloning %s into %s…", clone_url, repo_path)

        try:
            git.Repo.clone_from(clone_url, repo_path)
        except git.GitCommandError as exc:
            raise RepositoryCloneError(
                f"Failed to clone repository {clone_url}: {exc}"
            ) from exc

        return repo_path
