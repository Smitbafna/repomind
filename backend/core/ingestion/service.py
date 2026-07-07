from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.core.ingestion.clone import RepositoryCloneError, RepositoryCloner
from backend.core.ingestion.metadata import MetadataExtractor
from backend.core.ingestion.scanner import RepositoryScanner
from backend.core.ingestion.types import ParsedGitHubUrl
from backend.database.models import File as FileModel
from backend.database.models import Repository as RepositoryModel
from backend.database.repositories import FileRepository, RepositoryRepository

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result produced by the ingestion service."""

    repository: RepositoryModel
    file_count: int


class IngestionService:
    """Orchestrates the full repository ingestion pipeline.

    Steps:
        1. Parse the GitHub URL.
        2. Clone the repository.
        3. Scan the repository files.
        4. Extract metadata.
        5. Persist everything into the database.
    """

    def __init__(
        self,
        session: AsyncSession,
        cloner: RepositoryCloner | None = None,
        scanner: RepositoryScanner | None = None,
        metadata_extractor: MetadataExtractor | None = None,
        repo_repo: RepositoryRepository | None = None,
        file_repo: FileRepository | None = None,
    ) -> None:
        self._session = session
        self._cloner = cloner or RepositoryCloner()
        self._scanner = scanner or RepositoryScanner()
        self._metadata_extractor = metadata_extractor or MetadataExtractor()
        self._repo_repo = repo_repo or RepositoryRepository(session)
        self._file_repo = file_repo or FileRepository(session)

    async def ingest(self, url: str) -> IngestionResult:
        """Ingest a GitHub repository: clone, scan, and persist.

        Args:
            url: A GitHub repository URL (https://github.com/owner/repo).

        Returns:
            An ``IngestionResult`` containing the persisted repository record
            and the number of files discovered.

        Raises:
            RepositoryCloneError: If the URL is invalid or cloning fails.
        """
        settings = get_settings()
        target_dir = Path(settings.repositories_base_path)

        # 1. Parse
        parsed: ParsedGitHubUrl = self._cloner.parse_github_url(url)

        # 2. Clone
        local_path: Path = self._cloner.clone(parsed, target_dir)

        # 3. Scan
        scan_result = self._scanner.scan(local_path)

        # 4. Extract metadata
        default_branch = self._metadata_extractor.extract_default_branch(local_path)

        # 5. Persist repository
        repo_model = RepositoryModel(
            owner=parsed.owner,
            name=parsed.name,
            local_path=str(local_path),
            default_branch=default_branch,
        )
        persisted_repo = await self._repo_repo.add(repo_model)

        # 6. Persist files
        file_records = [
            FileModel(
                repository_id=persisted_repo.id,
                path=f.path,
                extension=f.extension,
                size=f.size,
                is_binary=f.is_binary,
            )
            for f in scan_result.files
        ]
        await self._file_repo.add_many(file_records)

        logger.info(
            "Ingested %s/%s — %d files",
            parsed.owner,
            parsed.name,
            scan_result.total_files,
        )

        return IngestionResult(
            repository=persisted_repo,
            file_count=scan_result.total_files,
        )