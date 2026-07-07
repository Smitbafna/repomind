from __future__ import annotations

from pathlib import Path

import pytest

from backend.core.parser.exceptions import UnsupportedLanguageError
from backend.core.parser.factory import ParserFactory
from backend.core.parser.python_parser import PythonParser


class TestParserFactory:
    """Test suite for the parser factory."""

    def setup_method(self) -> None:
        self.factory = ParserFactory()

    def test_get_parser_python(self) -> None:
        parser = self.factory.get_parser(Path("main.py"))
        assert isinstance(parser, PythonParser)

    def test_get_parser_unsupported(self) -> None:
        with pytest.raises(UnsupportedLanguageError):
            self.factory.get_parser(Path("main.rs"))

    def test_supports_python(self) -> None:
        assert self.factory.supports(Path("main.py")) is True
        assert self.factory.supports(Path("path/to/module.py")) is True

    def test_supports_unsupported(self) -> None:
        assert self.factory.supports(Path("main.go")) is False
        assert self.factory.supports(Path("file.unknown")) is False

    def test_supported_extensions(self) -> None:
        exts = self.factory.supported_extensions
        assert ".py" in exts

    def test_register_new_parser(self) -> None:
        class MockParser(PythonParser):
            @property
            def supported_extensions(self) -> set[str]:
                return {".foo", ".bar"}

        self.factory.register(MockParser())
        assert self.factory.supports(Path("test.foo")) is True
        assert self.factory.supports(Path("test.bar")) is True
        # Original parsers still work.
        assert self.factory.supports(Path("test.py")) is True

    def test_get_parser_case_insensitive_extension(self) -> None:
        parser = self.factory.get_parser(Path("main.PY"))
        assert isinstance(parser, PythonParser)

    def test_register_duplicate_extension(self) -> None:
        """Registering a parser with an existing extension should work."""
        class AnotherPythonParser(PythonParser):
            pass

        self.factory.register(AnotherPythonParser())
        parser = self.factory.get_parser(Path("test.py"))
        # Should return the first registered parser (PythonParser).
        assert isinstance(parser, PythonParser)