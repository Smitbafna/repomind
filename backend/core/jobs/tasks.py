from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.config.settings import get_settings
from backend.core.jobs.manager import get_job_manager
from backend.core.jobs.models import JobStep

logger = logging.getLogger(__name__)


async def import_repository_task(
    job_id: str,
    url: str,
    user_id: str | None = None,
) -> dict:
    """Run the full repository import pipeline in the background.

    Args:
        job_id: The job ID to update progress on.
        url: The GitHub repository URL.
        user_id: Optional user ID for ownership.

    Returns:
        A dict with the import result.
    """
    manager = get_job_manager()
    settings = get_settings()

    try:
        # Step 1: Clone
        manager.update_job(job_id, progress=5.0, step=JobStep.CLONING.value, message="Cloning repository...")
        from backend.core.ingestion.clone import RepositoryCloner
        from backend.core.ingestion.types import ParsedGitHubUrl

        cloner = RepositoryCloner()
        parsed = cloner.parse_github_url(url)
        target_dir = Path(settings.repositories_base_path)
        local_path = cloner.clone(parsed, target_dir)

        # Step 2: Scan
        manager.update_job(job_id, progress=15.0, step=JobStep.SCANNING.value, message="Scanning repository...")
        from backend.core.ingestion.scanner import RepositoryScanner
        scanner = RepositoryScanner()
        scan_result = scanner.scan(local_path)

        # Step 3: Ingest (persist to DB)
        manager.update_job(job_id, progress=25.0, step=JobStep.PARSING.value, message="Persisting repository data...")
        from backend.database.database import get_sync_session
        from backend.core.ingestion.metadata import MetadataExtractor
        from backend.database.models import Repository as RepositoryModel
        from backend.database.models import File as FileModel
        from backend.database.repositories import RepositoryRepository, FileRepository

        session = get_sync_session()
        try:
            metadata_extractor = MetadataExtractor()
            default_branch = metadata_extractor.extract_default_branch(local_path)

            repo_model = RepositoryModel(
                owner=parsed.owner,
                name=parsed.name,
                local_path=str(local_path),
                default_branch=default_branch,
            )
            repo_repo = RepositoryRepository(session)  # type: ignore[arg-type]
            persisted_repo = repo_repo.add(repo_model)  # type: ignore[arg-type]

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
            file_repo = FileRepository(session)  # type: ignore[arg-type]
            file_repo.add_many(file_records)  # type: ignore[arg-type]
            session.commit()
            repo_id = persisted_repo.id
        finally:
            session.close()

        # Step 4: Parse
        manager.update_job(job_id, progress=35.0, step=JobStep.PARSING.value, message="Parsing source code...")
        from backend.core.parser.service import ParserService
        from backend.database.database import get_sync_session

        session = get_sync_session()
        try:
            parser_service = ParserService(session=session)  # type: ignore[arg-type]
            await asyncio.to_thread(parser_service.parse_repository, repo_id)
            session.commit()
        finally:
            session.close()

        # Step 5: Extract relationships
        manager.update_job(job_id, progress=50.0, step=JobStep.RELATIONSHIPS.value, message="Extracting relationships...")
        from backend.core.relationships.service import RelationshipService

        session = get_sync_session()
        try:
            rel_service = RelationshipService(session=session)  # type: ignore[arg-type]
            await asyncio.to_thread(rel_service.extract_relationships, repo_id)
            session.commit()
        finally:
            session.close()

        # Step 6: Git history
        manager.update_job(job_id, progress=65.0, step=JobStep.GIT.value, message="Collecting git history...")
        from backend.core.git.service import GitService

        session = get_sync_session()
        try:
            git_service = GitService(session=session)  # type: ignore[arg-type]
            await asyncio.to_thread(git_service.collect_commits, repo_id)
            session.commit()
        finally:
            session.close()

        # Step 7: GitHub sync (if enabled)
        if settings.enable_github_sync and settings.github_token:
            manager.update_job(job_id, progress=75.0, step=JobStep.GITHUB.value, message="Syncing GitHub data...")
            from backend.core.github.service import GitHubService

            session = get_sync_session()
            try:
                github_service = GitHubService(session=session)  # type: ignore[arg-type]
                await asyncio.to_thread(github_service.sync_repository, repo_id)
                session.commit()
            finally:
                session.close()

        # Step 8: Index
        manager.update_job(job_id, progress=85.0, step=JobStep.EMBEDDINGS.value, message="Generating embeddings...")
        from backend.core.indexing.vector_indexer import VectorIndexer

        session = get_sync_session()
        try:
            indexer = VectorIndexer(session=session)  # type: ignore[arg-type]
            await asyncio.to_thread(indexer.index_repository, repo_id)
            session.commit()
        finally:
            session.close()

        # Complete
        result = {
            "repository_id": repo_id,
            "owner": parsed.owner,
            "name": parsed.name,
            "file_count": len(scan_result.files),
        }
        manager.complete_job(job_id, result)
        return result

    except Exception as exc:
        logger.exception("Import job %s failed", job_id)
        manager.fail_job(job_id, str(exc))
        raise


async def index_repository_task(job_id: str, repository_id: str) -> dict:
    """Index a repository in the background.

    Args:
        job_id: The job ID.
        repository_id: The repository to index.

    Returns:
        A dict with the index result.
    """
    manager = get_job_manager()
    try:
        manager.update_job(job_id, progress=10.0, step="Indexing", message="Building documents...")
        from backend.core.indexing.vector_indexer import VectorIndexer
        from backend.database.database import get_sync_session

        session = get_sync_session()
        try:
            indexer = VectorIndexer(session=session)  # type: ignore[arg-type]
            count = await asyncio.to_thread(indexer.index_repository, repository_id)
            session.commit()
        finally:
            session.close()

        result = {"repository_id": repository_id, "documents_indexed": count}
        manager.complete_job(job_id, result)
        return result
    except Exception as exc:
        logger.exception("Index job %s failed", job_id)
        manager.fail_job(job_id, str(exc))
        raise


async def extract_relationships_task(job_id: str, repository_id: str) -> dict:
    """Extract relationships in the background.

    Args:
        job_id: The job ID.
        repository_id: The repository.

    Returns:
        A dict with the result.
    """
    manager = get_job_manager()
    try:
        manager.update_job(job_id, progress=10.0, step="Extracting", message="Extracting relationships...")
        from backend.core.relationships.service import RelationshipService
        from backend.database.database import get_sync_session

        session = get_sync_session()
        try:
            rel_service = RelationshipService(session=session)  # type: ignore[arg-type]
            count = await asyncio.to_thread(rel_service.extract_relationships, repository_id)
            session.commit()
        finally:
            session.close()

        result = {"repository_id": repository_id, "relationships_extracted": count}
        manager.complete_job(job_id, result)
        return result
    except Exception as exc:
        logger.exception("Relationship extraction job %s failed", job_id)
        manager.fail_job(job_id, str(exc))
        raise


async def sync_github_task(job_id: str, repository_id: str) -> dict:
    """Sync GitHub data in the background.

    Args:
        job_id: The job ID.
        repository_id: The repository.

    Returns:
        A dict with the result.
    """
    manager = get_job_manager()
    try:
        manager.update_job(job_id, progress=10.0, step="Syncing", message="Syncing GitHub data...")
        from backend.core.github.service import GitHubService
        from backend.database.database import get_sync_session

        session = get_sync_session()
        try:
            github_service = GitHubService(session=session)  # type: ignore[arg-type]
            result = await asyncio.to_thread(github_service.sync_repository, repository_id)
            session.commit()
        finally:
            session.close()

        manager.complete_job(job_id, {"repository_id": repository_id, "status": "synced"})
        return {"repository_id": repository_id, "status": "synced"}
    except Exception as exc:
        logger.exception("GitHub sync job %s failed", job_id)
        manager.fail_job(job_id, str(exc))
        raise