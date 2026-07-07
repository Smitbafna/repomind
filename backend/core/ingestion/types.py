from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedGitHubUrl:
    """Result of parsing a GitHub URL into its components."""

    owner: str
    name: str
    url: str


@dataclass(frozen=True)
class FileMetadata:
    """Metadata about a single file discovered during scanning."""

    path: str
    extension: str | None
    size: int
    is_binary: bool


@dataclass(frozen=True)
class ScanResult:
    """Result of scanning a cloned repository."""

    files: list[FileMetadata] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0