from __future__ import annotations


class GitError(Exception):
    """Base exception for all Git-related errors."""


class RepositoryNotClonedError(GitError):
    """Raised when the repository is not available locally."""