from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.database import AsyncSessionLocal


class DatabaseSessionManager:
    """Thin wrapper around async session lifecycle."""

    @staticmethod
    @asynccontextmanager
    async def session() -> AsyncIterator[AsyncSession]:
        """Provide an async session with automatic commit/rollback."""
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise