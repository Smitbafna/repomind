from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session as SyncSession

from backend.config.settings import get_settings

settings = get_settings()


def _get_async_url() -> str:
    """Convert the configured database URL to an async-compatible URL.

    Supports both SQLite and PostgreSQL URLs.
    """
    url = settings.database_url

    # If already async, return as-is.
    if "+aiosqlite" in url or "+asyncpg" in url:
        return url

    # Convert sync SQLite to async.
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

    # Convert sync PostgreSQL to async.
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


# ── Async engine (used by FastAPI) ────────────────────────────────
Engine = create_async_engine(_get_async_url(), echo=settings.debug, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=Engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync engine (used by CLI / scripts) ──────────────────────────
_sync_engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)


def get_sync_session() -> SyncSession:
    """Return a synchronous SQLAlchemy session (useful for CLI and tests)."""
    return SyncSession(bind=_sync_engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, Any]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise