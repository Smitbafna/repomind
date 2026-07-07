from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from backend.core.parser.exceptions import ParseFileError
from backend.core.parser.python_parser import PythonParser


class TestPythonParser:
    """Test suite for the Python AST-based parser."""

    def setup_method(self) -> None:
        self.parser = PythonParser()

    def test_supported_extensions(self) -> None:
        assert self.parser.supported_extensions == {".py"}

    def test_parse_empty_file(self) -> None:
        result = self.parser.parse_file(_make_file(""))
        assert result.language == "python"
        assert result.classes == []
        assert result.functions == []
        assert result.imports == []

    def test_parse_simple_function(self) -> None:
        source = """
def greet(name: str) -> str:
    return f"Hello, {name}!"
"""
        result = self.parser.parse_file(_make_file(source))
        assert len(result.functions) == 1
        fn = result.functions[0]
        assert fn.name == "greet"
        assert fn.line_start > 0
        assert fn.line_end >= fn.line_start
        assert fn.is_async is False
        assert fn.docstring is None

    def test_parse_async_function(self) -> None:
        source = """
async def fetch_data(url: str) -> dict:
    return {"data": "mock"}
"""
        result = self.parser.parse_file(_make_file(source))
        assert len(result.functions) == 1
        fn = result.functions[0]
        assert fn.name == "fetch_data"
        assert fn.is_async is True

    def test_parse_class_with_methods(self) -> None:
        source = '''
class Calculator:
    """A simple calculator class."""

    def add(self, a: int, b: int) -> int:
        return a + b

    async def multiply(self, a: int, b: int) -> int:
        return a * b
'''
        result = self.parser.parse_file(_make_file(source))
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "Calculator"
        assert cls.docstring == "A simple calculator class."
        assert len(cls.methods) == 2

        method_names = {m.name for m in cls.methods}
        assert method_names == {"add", "multiply"}

        add_method = next(m for m in cls.methods if m.name == "add")
        assert add_method.is_async is False

        mult_method = next(m for m in cls.methods if m.name == "multiply")
        assert mult_method.is_async is True

        # Top-level functions should be empty (all functions are methods)
        assert len(result.functions) == 0

    def test_parse_class_inheritance(self) -> None:
        source = """
class Animal:
    pass

class Dog(Animal):
    pass

class GoldenRetriever(Dog, Animal):
    pass
"""
        result = self.parser.parse_file(_make_file(source))
        assert len(result.classes) == 3

        animal = result.classes[0]
        assert animal.name == "Animal"
        assert animal.bases == []

        dog = result.classes[1]
        assert dog.name == "Dog"
        assert dog.bases == ["Animal"]

        golden = result.classes[2]
        assert golden.name == "GoldenRetriever"
        assert set(golden.bases) == {"Dog", "Animal"}

    def test_parse_imports(self) -> None:
        source = """
import os
import sys as system
from datetime import datetime
from typing import Optional, List as ListType
"""
        result = self.parser.parse_file(_make_file(source))
        assert len(result.imports) == 5  # noqa: PLR2004

        imports_by_alias = {imp.alias or imp.imported_name: imp for imp in result.imports}

        assert imports_by_alias["os"].module == "os"
        assert imports_by_alias["os"].alias is None

        assert imports_by_alias["system"].module == "sys"
        assert imports_by_alias["system"].alias == "system"

        assert imports_by_alias["datetime"].module == "datetime.datetime"
        assert imports_by_alias["datetime"].alias is None

        assert imports_by_alias["Optional"].module == "typing.Optional"
        assert imports_by_alias["Optional"].alias is None

        assert imports_by_alias["ListType"].module == "typing.List"
        assert imports_by_alias["ListType"].alias == "ListType"

    def test_parse_decorators(self) -> None:
        source = """
@staticmethod
@some_decorator("arg")
def my_method():
    pass

@dataclass
class Config:
    pass
"""
        result = self.parser.parse_file(_make_file(source))
        assert len(result.functions) == 1
        fn = result.functions[0]
        assert "staticmethod" in fn.decorators
        assert "some_decorator('arg')" in fn.decorators or 'some_decorator("arg")' in fn.decorators

        assert len(result.classes) == 1
        cls = result.classes[0]
        assert "dataclass" in cls.decorators

    def test_parse_docstrings(self) -> None:
        source = '''
def documented():
    """This function has a docstring."""
    pass

class Documented:
    """This class has a docstring."""
    pass
'''
        result = self.parser.parse_file(_make_file(source))
        assert len(result.functions) == 1
        assert result.functions[0].docstring == "This function has a docstring."
        assert len(result.classes) == 1
        assert result.classes[0].docstring == "This class has a docstring."

    def test_parse_syntax_error(self) -> None:
        with pytest.raises(ParseFileError):
            self.parser.parse_file(_make_file("def broken("))

    def test_parse_nonexistent_file(self) -> None:
        with pytest.raises(ParseFileError):
            self.parser.parse_file(Path("/nonexistent/file.py"))

    def test_top_level_and_method_functions_separated(self) -> None:
        source = """
def top_level():
    pass

class MyClass:
    def method(self):
        pass

def another_top_level():
    pass
"""
        result = self.parser.parse_file(_make_file(source))
        assert len(result.functions) == 2
        assert {f.name for f in result.functions} == {"top_level", "another_top_level"}

        assert len(result.classes) == 1
        assert len(result.classes[0].methods) == 1
        assert result.classes[0].methods[0].name == "method"


def _make_file(source: str) -> Path:
    """Create a temporary Python file with the given source code."""
    tmp = NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    tmp.write(source)
    tmp.close()
    return Path(tmp.name)