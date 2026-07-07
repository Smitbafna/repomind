from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedImport:
    """Represents a single import statement extracted from source code."""

    module: str
    imported_name: str
    alias: str | None = None


@dataclass(frozen=True)
class ParsedFunction:
    """Represents a function or method extracted from source code."""

    name: str
    line_start: int
    line_end: int
    is_async: bool = False
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedClass:
    """Represents a class extracted from source code."""

    name: str
    line_start: int
    line_end: int
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    methods: list[ParsedFunction] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedFile:
    """Represents the result of parsing a single source code file.

    This is the return type of every language parser implementation.
    """

    path: str
    language: str
    classes: list[ParsedClass] = field(default_factory=list)
    functions: list[ParsedFunction] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)