from __future__ import annotations

import logging
from pathlib import Path

import git

from backend.core.ingestion.types import ParsedGitHubUrl, ScanResult

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts repository-level metadata from a cloned repo."""

    @staticmethod
    def extract_default_branch(repo_path: Path) -> str | None:
        """Read the default branch name from the local git repository.

        Args:
            repo_path: Path to the cloned repository.

        Returns:
            The default branch name, or ``None`` if it cannot be determined.
        """
        try:
            repo = git.Repo(repo_path)
            # GitPython's active_branch may fail in detached HEAD state.
            try:
                return repo.active_branch.name
            except (TypeError, ValueError):
                # Fall back to reading HEAD ref.
                head_ref = repo.head.ref
                return head_ref.name if head_ref else None
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as exc:
            logger.warning("Unable to read git metadata from %s: %s", repo_path, exc)
            return None

    @staticmethod
    def build_repo_info(
        parsed: ParsedGitHubUrl,
        local_path: Path,
        scan_result: ScanResult,
        default_branch: str | None,
    ) -> dict:
        """Assemble a dictionary of repository information.

        This is used by the ingestion service to populate the database model.
        """
        return {
            "owner": parsed.owner,
            "name": parsed.name,
            "local_path": str(local_path),
            "default_branch": default_branch,
            "file_count": scan_result.total_files,
        }