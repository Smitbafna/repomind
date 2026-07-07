from __future__ import annotations

from pathlib import Path

from backend.core.parser.exceptions import UnsupportedLanguageError
from backend.core.parser.parser import BaseParser
from backend.core.parser.python_parser import PythonParser


class ParserFactory:
    """Factory responsible for selecting the correct parser for a given file.

    New language parsers are registered here. To add support for a new language,
    create a new parser class implementing ``BaseParser`` and register it with
    the ``register`` method or pass it via the constructor.

    This design ensures that adding new languages requires zero changes to
    existing code (Open/Closed Principle).
    """

    def __init__(self, parsers: list[BaseParser] | None = None) -> None:
        self._parsers: list[BaseParser] = parsers or [
            PythonParser(),
        ]

    def register(self, parser: BaseParser) -> None:
        """Register a new language parser.

        Args:
            parser: An instance of a ``BaseParser`` implementation.
        """
        self._parsers.append(parser)

    def get_parser(self, path: Path) -> BaseParser:
        """Return the appropriate parser for the given file path.

        Args:
            path: Path to the source file.

        Returns:
            A ``BaseParser`` implementation capable of parsing the file.

        Raises:
            UnsupportedLanguageError: If no parser supports the file extension.
        """
        ext = path.suffix.lower()
        for parser in self._parsers:
            if ext in parser.supported_extensions:
                return parser

        raise UnsupportedLanguageError(
            f"No parser available for file extension '{ext}': {path}"
        )

    def supports(self, path: Path) -> bool:
        """Check whether a parser is available for the given file.

        Args:
            path: Path to the source file.

        Returns:
            ``True`` if a parser supports this file, ``False`` otherwise.
        """
        try:
            self.get_parser(path)
            return True
        except UnsupportedLanguageError:
            return False

    @property
    def supported_extensions(self) -> set[str]:
        """Return the union of all registered parser extensions."""
        exts: set[str] = set()
        for parser in self._parsers:
            exts.update(parser.supported_extensions)
        return exts