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

# ── Async engine (used by FastAPI) ────────────────────────────────
_async_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
Engine = create_async_engine(_async_url, echo=settings.debug, future=True)
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