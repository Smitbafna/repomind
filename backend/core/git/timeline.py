from __future__ import annotations

import logging
from pathlib import Path

import git

from backend.core.git.exceptions import GitError, RepositoryNotClonedError
from backend.core.git.models import BlameInfo, TimelineEvent

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """Builds a chronological timeline of repository events."""

    def build(
        self,
        repo_path: Path,
        commits: list,
    ) -> list[TimelineEvent]:
        """Build a timeline from commit data.

        Args:
            repo_path: Path to the local git repository.
            commits: List of ``CommitInfo`` or ORM commit objects with file data.

        Returns:
            A list of ``TimelineEvent`` in chronological order.
        """
        events: list[TimelineEvent] = []
        for commit in commits:
            affected_files = [
                cf.file_path for cf in commit.files
            ] if hasattr(commit, "files") and commit.files else []
            events.append(
                TimelineEvent(
                    commit_hash=commit.hash if hasattr(commit, "hash") else str(getattr(commit, "hash", "")),
                    author_name=commit.author_name if hasattr(commit, "author_name") else "",
                    author_email=commit.author_email if hasattr(commit, "author_email") else "",
                    committed_at=commit.committed_at if hasattr(commit, "committed_at") else None,
                    commit_message=commit.commit_message if hasattr(commit, "commit_message") else "",
                    affected_files=affected_files,
                )
            )
        return events


class BlameService:
    """Provides blame information for specific lines in files."""

    def blame(
        self,
        repo_path: Path,
        file_path: str,
        line_number: int,
    ) -> BlameInfo | None:
        """Get blame information for a specific line.

        Args:
            repo_path: Path to the local git repository.
            file_path: Relative file path within the repository.
            line_number: 1-based line number.

        Returns:
            A ``BlameInfo`` or ``None`` if not found.
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

        full_path = repo_path / file_path
        if not full_path.exists():
            return None

        try:
            # Use git blame with porcelain format for structured output.
            blame_output = repo.git.blame(
                "--porcelain",
                "-L",
                f"{line_number},{line_number}",
                str(full_path),
            )
            return self._parse_porcelain_line(blame_output, line_number)
        except git.GitCommandError:
            return None

    @staticmethod
    def _parse_porcelain_line(blame_output: str, line_number: int) -> BlameInfo | None:
        """Parse a single line from git blame --porcelain output."""
        if not blame_output.strip():
            return None

        lines = blame_output.splitlines()
        if not lines:
            return None

        # The first line contains: commit_hash line_number_original line_number_final group_size
        parts = lines[0].split()
        if len(parts) < 4:
            return None
        commit_hash = parts[0]

        # Find the content line (prefixed with a tab).
        content = ""
        author_name = ""
        author_email = ""
        commit_time = ""
        commit_message = ""

        for line in lines[1:]:
            if line.startswith("author "):
                author_name = line[7:]
            elif line.startswith("author-mail "):
                author_email = line[12:].strip("<>")
            elif line.startswith("author-time "):
                commit_time = line[12:]
            elif line.startswith("summary "):
                commit_message = line[8:]
            elif line.startswith("\t"):
                content = line[1:]

        import datetime
        timestamp = datetime.datetime.fromtimestamp(
            int(commit_time), tz=datetime.timezone.utc
        ) if commit_time else datetime.datetime.now(datetime.timezone.utc)

        return BlameInfo(
            commit_hash=commit_hash,
            author_name=author_name,
            author_email=author_email,
            committed_at=timestamp,
            commit_message=commit_message,
            line_number=line_number,
            line_content=content,
        )