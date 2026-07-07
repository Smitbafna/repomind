from __future__ import annotations

import logging
from pathlib import Path

import git

from backend.core.git.diff_parser import DiffParser
from backend.core.git.exceptions import GitError, RepositoryNotClonedError
from backend.core.git.models import CommitFileInfo, CommitInfo

logger = logging.getLogger(__name__)


class GitCollector:
    """Collects git history from a local repository.

    Uses GitPython to extract:
        - Every commit (hash, author, timestamp, message, parent)
        - Changed files per commit
        - Additions/deletions per file
        - Branch information
    """

    def __init__(self, diff_parser: DiffParser | None = None) -> None:
        self._diff_parser = diff_parser or DiffParser()

    def collect(self, repo_path: Path) -> list[CommitInfo]:
        """Collect all commits from the repository.

        Args:
            repo_path: Path to the local git repository.

        Returns:
            A list of ``CommitInfo`` ordered by time descending.

        Raises:
            RepositoryNotClonedError: If the path is not a git repository.
        """
        if not repo_path.exists():
            raise RepositoryNotClonedError(
                f"Repository path does not exist: {repo_path}"
            )

        try:
            repo = git.Repo(str(repo_path))
        except git.InvalidGitRepositoryError as exc:
            raise RepositoryNotClonedError(
                f"Not a git repository: {repo_path}"
            ) from exc

        commits: list[CommitInfo] = []
        active_branch = self._get_active_branch(repo)

        try:
            for git_commit in repo.iter_commits(active_branch or "HEAD"):
                commit_info = self._extract_commit(repo, git_commit, active_branch)
                commits.append(commit_info)
        except git.GitCommandError as exc:
            raise GitError(f"Failed to iterate commits: {exc}") from exc

        logger.info(
            "Collected %d commits from %s", len(commits), repo_path
        )
        return commits

    def collect_from_hash(self, repo_path: Path, since_hash: str) -> list[CommitInfo]:
        """Collect commits from a specific hash onwards.

        Args:
            repo_path: Path to the local git repository.
            since_hash: Collect commits from this hash (inclusive).

        Returns:
            A list of ``CommitInfo``.
        """
        if not repo_path.exists():
            raise RepositoryNotClonedError(
                f"Repository path does not exist: {repo_path}"
            )

        try:
            repo = git.Repo(str(repo_path))
        except git.InvalidGitRepositoryError as exc:
            raise RepositoryNotClonedError(
                f"Not a git repository: {repo_path}"
            ) from exc

        commits: list[CommitInfo] = []
        active_branch = self._get_active_branch(repo)

        try:
            for git_commit in repo.iter_commits(
                f"{since_hash}..HEAD" if since_hash else "HEAD"
            ):
                commit_info = self._extract_commit(repo, git_commit, active_branch)
                commits.append(commit_info)
        except git.GitCommandError as exc:
            raise GitError(f"Failed to iterate commits: {exc}") from exc

        return commits

    # ── private helpers ─────────────────────────────────────────

    def _extract_commit(
        self, repo: git.Repo, git_commit: git.Commit, branch: str | None
    ) -> CommitInfo:
        """Extract structured commit info from a GitPython commit object."""
        files: list[CommitFileInfo] = []

        # Get parent for comparison.
        parent = git_commit.parents[0] if git_commit.parents else None

        if parent:
            try:
                diff_index = parent.diff(git_commit, create_patch=True)
                for diff_item in diff_index:
                    diff_text = diff_item.diff.decode("utf-8", errors="replace")
                    change_type = self._diff_parser.change_type_from_diff(diff_text)
                    parsed = self._diff_parser.parse(diff_text, diff_item.b_path or diff_item.a_path or "")
                    files.append(
                        CommitFileInfo(
                            file_path=diff_item.b_path or diff_item.a_path or "",
                            change_type=change_type,
                            additions=parsed.additions,
                            deletions=parsed.deletions,
                        )
                    )
            except Exception as exc:
                logger.warning("Failed to diff commit %s: %s", git_commit.hexsha[:8], exc)
        else:
            # Root commit — all files are added.
            try:
                for item in git_commit.tree.traverse():
                    if item.type == "blob":
                        files.append(
                            CommitFileInfo(
                                file_path=item.path,
                                change_type="ADDED",
                                additions=0,
                                deletions=0,
                            )
                        )
            except Exception as exc:
                logger.warning(
                    "Failed to list tree for root commit %s: %s",
                    git_commit.hexsha[:8], exc,
                )

        return CommitInfo(
            hash=git_commit.hexsha,
            author_name=git_commit.author.name,
            author_email=git_commit.author.email,
            commit_message=git_commit.message.strip(),
            committed_at=git_commit.committed_datetime,
            parent_hash=git_commit.parents[0].hexsha if git_commit.parents else None,
            branch=branch,
            files=files,
        )

    @staticmethod
    def _get_active_branch(repo: git.Repo) -> str | None:
        """Get the active branch name."""
        try:
            return repo.active_branch.name
        except (TypeError, ValueError):
            return None