from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from backend.core.parser.models import ParsedFile


class BaseParser(ABC):
    """Abstract interface for all language parsers.

    Every language-specific parser must implement ``parse_file``.
    The interface is designed to support both AST-based parsers (e.g. Python's
    ``ast`` module) and external parsers (e.g. Tree-sitter) without requiring
    architectural changes.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """Return the set of file extensions this parser supports.

        Example: ``{".py"}`` for Python, ``{".ts", ".tsx"}`` for TypeScript.
        """
        ...

    @abstractmethod
    def parse_file(self, path: Path) -> ParsedFile:
        """Parse a single source file and return its structural information.

        Args:
            path: Absolute or relative path to the source file.

        Returns:
            A ``ParsedFile`` containing all extracted structural information.

        Raises:
            ParserError: If the file cannot be parsed.
        """
        ...