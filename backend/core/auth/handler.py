from __future__ import annotations

import hashlib
import secrets
from typing import Any


def get_password_hash(password: str) -> str:
    """Hash a password using SHA-256 with a random salt.

    Args:
        password: The plain-text password.

    Returns:
        A string in the format ``salt:hash``.
    """
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: The plain-text password to check.
        hashed_password: The stored ``salt:hash`` string.

    Returns:
        ``True`` if the password matches.
    """
    try:
        salt, pwd_hash = hashed_password.split(":", 1)
        computed = hashlib.sha256(f"{salt}{plain_password}".encode()).hexdigest()
        return computed == pwd_hash
    except (ValueError, AttributeError):
        return False


class AuthHandler:
    """Handles user authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password.

        Args:
            password: The plain-text password.

        Returns:
            The hashed password string.
        """
        return get_password_hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: The plain-text password.
            hashed_password: The stored hash.

        Returns:
            ``True`` if the password matches.
        """
        return verify_password(plain_password, hashed_password)