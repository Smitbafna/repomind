from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.git.collector import GitCollector
from backend.core.git.models import BlameInfo, CommitInfo, TimelineEvent
from backend.core.git.timeline import BlameService, TimelineBuilder
from backend.database.models import (
    Commit as CommitModel,
    CommitFile as CommitFileModel,
    CommitRelationship as CommitRelationshipModel,
    Repository,
)
from backend.database.repositories import (
    CommitFileRepository,
    CommitRelationshipRepository,
    CommitRepository,
    RepositoryRepository,
)

logger = logging.getLogger(__name__)


class GitService:
    """Orchestrates Git intelligence operations.

    Responsibilities:
        1. Collect git history and persist to database.
        2. Query commit history.
        3. Build repository timelines.
        4. Provide blame information.
    """

    def __init__(
        self,
        session: AsyncSession,
        collector: GitCollector | None = None,
        timeline_builder: TimelineBuilder | None = None,
        blame_service: BlameService | None = None,
        repo_repo: RepositoryRepository | None = None,
        commit_repo: CommitRepository | None = None,
        commit_file_repo: CommitFileRepository | None = None,
        commit_rel_repo: CommitRelationshipRepository | None = None,
    ) -> None:
        self._session = session
        self._collector = collector or GitCollector()
        self._timeline_builder = timeline_builder or TimelineBuilder()
        self._blame_service = blame_service or BlameService()
        self._repo_repo = repo_repo or RepositoryRepository(session)
        self._commit_repo = commit_repo or CommitRepository(session)
        self._commit_file_repo = commit_file_repo or CommitFileRepository(session)
        self._commit_rel_repo = commit_rel_repo or CommitRelationshipRepository(session)

    async def collect_history(self, repository_id: str) -> int:
        """Collect and persist complete git history for a repository.

        Args:
            repository_id: The primary key of the repository.

        Returns:
            The number of commits collected.

        Raises:
            ValueError: If the repository ID is not found.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        repo_path = Path(repo.local_path)
        commit_infos = self._collector.collect(repo_path)

        # Clear previous history.
        await self._commit_repo.delete_by_repository(repository_id)

        for ci in commit_infos:
            commit_model = CommitModel(
                repository_id=repository_id,
                hash=ci.hash,
                author_name=ci.author_name,
                author_email=ci.author_email,
                commit_message=ci.commit_message,
                committed_at=ci.committed_at,
                parent_hash=ci.parent_hash,
                branch=ci.branch,
            )
            persisted = await self._commit_repo.add(commit_model)

            if ci.files:
                file_models = [
                    CommitFileModel(
                        commit_id=persisted.id,
                        file_path=f.file_path,
                        change_type=f.change_type,
                        additions=f.additions,
                        deletions=f.deletions,
                    )
                    for f in ci.files
                ]
                await self._commit_file_repo.add_many(file_models)

        await self._session.flush()
        logger.info(
            "Collected %d commits for repository %s", len(commit_infos), repository_id
        )
        return len(commit_infos)

    async def get_commits(self, repository_id: str) -> list[CommitModel]:
        """Return all commits for a repository.

        Args:
            repository_id: The primary key of the repository.

        Returns:
            A list of ``CommitModel`` instances with file data.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        return list(await self._commit_repo.get_by_repository(repository_id))

    async def get_timeline(self, repository_id: str) -> list[TimelineEvent]:
        """Build a timeline for a repository.

        Args:
            repository_id: The primary key of the repository.

        Returns:
            A list of ``TimelineEvent`` instances.
        """
        commits = await self.get_commits(repository_id)
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        return self._timeline_builder.build(Path(repo.local_path), commits)

    async def get_blame(
        self, repository_id: str, file_path: str, line_number: int
    ) -> BlameInfo | None:
        """Get blame information for a specific line.

        Args:
            repository_id: The primary key of the repository.
            file_path: Relative file path within the repository.
            line_number: 1-based line number.

        Returns:
            A ``BlameInfo`` or ``None``.
        """
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository not found: {repository_id}")

        return self._blame_service.blame(
            Path(repo.local_path), file_path, line_number
        )