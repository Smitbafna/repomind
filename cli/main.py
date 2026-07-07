from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from backend.config.settings import get_settings
from backend.database.database import get_sync_session
from backend.database.models import Base, Repository, File

app = typer.Typer(
    name="repomind",
    help="RepoMind CLI — Agentic Code Intelligence Platform",
)


@app.command()
def init_db() -> None:
    """Create all database tables."""
    settings = get_settings()
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    typer.echo(f"Database initialised at {settings.database_url}")


@app.command()
def ingest(url: str) -> None:
    """Ingest a GitHub repository (synchronous variant)."""
    from backend.core.ingestion.clone import RepositoryCloner
    from backend.core.ingestion.metadata import MetadataExtractor
    from backend.core.ingestion.scanner import RepositoryScanner
    from backend.database.repositories import RepositoryRepository, FileRepository
    from backend.database.models import File as FileModel
    from backend.database.models import Repository as RepositoryModel

    settings = get_settings()
    target_dir = Path(settings.repositories_base_path)

    cloner = RepositoryCloner()
    scanner = RepositoryScanner()
    metadata_extractor = MetadataExtractor()

    parsed = cloner.parse_github_url(url)
    local_path = cloner.clone(parsed, target_dir)
    scan_result = scanner.scan(local_path)
    default_branch = metadata_extractor.extract_default_branch(local_path)

    session = get_sync_session()
    try:
        repo_repo = RepositoryRepository(session)  # type: ignore[arg-type]
        file_repo = FileRepository(session)  # type: ignore[arg-type]

        repo_model = RepositoryModel(
            owner=parsed.owner,
            name=parsed.name,
            local_path=str(local_path),
            default_branch=default_branch,
        )
        persisted = session.add(repo_model)
        session.flush()

        file_records = [
            FileModel(
                repository_id=repo_model.id,
                path=f.path,
                extension=f.extension,
                size=f.size,
                is_binary=f.is_binary,
            )
            for f in scan_result.files
        ]
        session.add_all(file_records)
        session.commit()

        typer.echo(
            f"Ingested {parsed.owner}/{parsed.name} — "
            f"{scan_result.total_files} files"
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def list_repos() -> None:
    """List all ingested repositories."""
    session = get_sync_session()
    try:
        repos = session.query(Repository).order_by(Repository.created_at.desc()).all()
        if not repos:
            typer.echo("No repositories ingested yet.")
            return

        for repo in repos:
            file_count = session.query(File).filter(
                File.repository_id == repo.id
            ).count()
            typer.echo(
                f"{repo.id[:8]}  {repo.owner}/{repo.name}  "
                f"[{file_count} files]  ({repo.local_path})"
            )
    finally:
        session.close()


if __name__ == "__main__":
    app()