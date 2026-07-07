from __future__ import annotations


class ParserError(Exception):
    """Base exception for all parser-related errors."""


class UnsupportedLanguageError(ParserError):
    """Raised when no parser is available for a given file extension."""


class ParseFileError(ParserError):
    """Raised when parsing a specific file fails."""