from __future__ import annotations

import time
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from backend.config.settings import get_settings
from backend.database.database import get_async_session
from backend.database.models import User as UserModel

security = HTTPBearer()


def create_access_token(data: dict[str, Any], expires_delta: int | None = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data (must include ``sub``).
        expires_delta: Expiration time in minutes.

    Returns:
        The encoded JWT string.
    """
    settings = get_settings()
    to_encode = data.copy()
    expire = time.time() + (expires_delta or settings.access_token_expire_minutes) * 60
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT string.

    Returns:
        The decoded payload.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session),
) -> UserModel:
    """FastAPI dependency that returns the authenticated user.

    Args:
        credentials: The bearer token from the request.
        session: The database session.

    Returns:
        The authenticated ``UserModel``.

    Raises:
        HTTPException: If the token is invalid or user not found.
    """
    payload = decode_access_token(credentials.credentials)
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    from backend.database.repositories import UserRepository

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# Optional auth dependency (doesn't require auth)
async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    session: AsyncSession = Depends(get_async_session),
) -> UserModel | None:
    """FastAPI dependency that returns the authenticated user or None.

    Args:
        credentials: Optional bearer token.
        session: The database session.

    Returns:
        The authenticated ``UserModel`` or ``None``.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None