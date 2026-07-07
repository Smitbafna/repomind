from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path

from backend.config.settings import get_settings
from backend.core.ingestion.types import FileMetadata, ScanResult

logger = logging.getLogger(__name__)

# Directories that should never be scanned.
_IGNORED_DIRECTORIES: set[str] = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".tox",
    ".eggs",
    "eggs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".gradle",
    "target",  # Rust / Java build output
    "build",
    "dist",
    ".next",
    ".nuxt",
    ".cache",
    ".husky",
    "vendor",
}

# File extensions that are universally considered binary.
_BINARY_EXTENSIONS: set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".webp",
    ".tiff",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".mkv",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".o",
    ".a",
    ".lib",
    ".pyc",
    ".pyo",
    ".class",
    ".jar",
    ".war",
    ".ear",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".DS_Store",
    ".gitignore",
    ".gitkeep",
}


class RepositoryScanner:
    """Walks a cloned repository and collects file metadata."""

    def __init__(self) -> None:
        self._settings = get_settings()
        mimetypes.init()

    def scan(self, repo_path: Path) -> ScanResult:
        """Recursively scan a repository directory.

        Args:
            repo_path: Root path of the cloned repository.

        Returns:
            A ``ScanResult`` containing metadata for every scanned file.
        """
        files: list[FileMetadata] = []
        total_size = 0

        if not repo_path.is_dir():
            logger.warning("Repository path does not exist: %s", repo_path)
            return ScanResult()

        for root_str, dirs, filenames in os.walk(str(repo_path)):
            root = Path(root_str)

            # Prune ignored directories in-place (affects os.walk behaviour).
            dirs[:] = [d for d in dirs if d not in _IGNORED_DIRECTORIES]

            for filename in filenames:
                file_path = root / filename
                try:
                    stat = file_path.stat()
                except OSError:
                    continue

                # Skip files that exceed the size limit.
                if stat.st_size > self._settings.max_file_size_bytes:
                    logger.debug(
                        "Skipping oversized file: %s (%d bytes)",
                        file_path,
                        stat.st_size,
                    )
                    continue

                # Compute the relative path from the repo root.
                try:
                    rel_path = str(file_path.relative_to(repo_path))
                except ValueError:
                    rel_path = str(file_path)

                ext = file_path.suffix.lower()
                is_binary = self._is_binary_file(file_path, ext)

                metadata = FileMetadata(
                    path=rel_path,
                    extension=ext if ext else None,
                    size=stat.st_size,
                    is_binary=is_binary,
                )
                files.append(metadata)
                total_size += stat.st_size

        return ScanResult(
            files=files,
            total_files=len(files),
            total_size_bytes=total_size,
        )

    @staticmethod
    def _is_binary_file(path: Path, ext: str) -> bool:
        """Determine whether a file should be considered binary."""
        if ext in _BINARY_EXTENSIONS:
            return True

        # Fall back to mimetype detection.
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and mime_type.startswith(("image/", "video/", "audio/", "font/")):
            return True

        return False