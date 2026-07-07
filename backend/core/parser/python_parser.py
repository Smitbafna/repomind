from __future__ import annotations

import ast
import logging
from pathlib import Path

from backend.core.parser.exceptions import ParseFileError
from backend.core.parser.models import ParsedClass, ParsedFile, ParsedFunction, ParsedImport
from backend.core.parser.parser import BaseParser

logger = logging.getLogger(__name__)


class PythonParser(BaseParser):
    """Parses Python source files using the built-in ``ast`` module.

    Extracts classes, functions, methods, imports, decorators, docstrings,
    line numbers, class inheritance, and async functions without executing code.
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".py"}

    def parse_file(self, path: Path) -> ParsedFile:
        """Parse a single Python file and extract structural information.

        Args:
            path: Path to the ``.py`` file.

        Returns:
            A ``ParsedFile`` with all extracted structures.

        Raises:
            ParseFileError: If the file cannot be read or parsed.
        """
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ParseFileError(f"Failed to read {path}: {exc}") from exc

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise ParseFileError(f"Syntax error in {path}: {exc}") from exc

        imports: list[ParsedImport] = []
        functions: list[ParsedFunction] = []
        classes: list[ParsedClass] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.extend(self._extract_imports(node))
            elif isinstance(node, ast.FunctionDef) and not self._is_method(node, tree):
                functions.append(self._extract_function(node))
            elif isinstance(node, ast.AsyncFunctionDef) and not self._is_method(node, tree):
                functions.append(self._extract_function(node))
            elif isinstance(node, ast.ClassDef):
                classes.append(self._extract_class(node))

        return ParsedFile(
            path=str(path),
            language="python",
            classes=classes,
            functions=functions,
            imports=imports,
        )

    # ── internal helpers ──────────────────────────────────────────

    @staticmethod
    def _extract_imports(node: ast.Import | ast.ImportFrom) -> list[ParsedImport]:
        """Extract import information from an AST Import or ImportFrom node."""
        result: list[ParsedImport] = []

        if isinstance(node, ast.Import):
            for alias in node.names:
                result.append(
                    ParsedImport(
                        module=alias.name,
                        imported_name=alias.name,
                        alias=alias.asname,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_base = node.module or ""
            for alias in node.names:
                module = f"{module_base}.{alias.name}" if module_base else alias.name
                result.append(
                    ParsedImport(
                        module=module,
                        imported_name=alias.name,
                        alias=alias.asname,
                    )
                )

        return result

    @staticmethod
    def _extract_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ParsedFunction:
        """Extract function information from a FunctionDef or AsyncFunctionDef node."""
        decorators = [ast.unparse(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)
        is_async = isinstance(node, ast.AsyncFunctionDef)

        return ParsedFunction(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            is_async=is_async,
            docstring=docstring,
            decorators=decorators,
        )

    @staticmethod
    def _extract_class(node: ast.ClassDef) -> ParsedClass:
        """Extract class information from a ClassDef node."""
        decorators = [ast.unparse(d) for d in node.decorator_list]
        bases = [ast.unparse(b) for b in node.bases]
        docstring = ast.get_docstring(node)
        methods: list[ParsedFunction] = []

        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef):
                methods.append(PythonParser._extract_function(child))
            elif isinstance(child, ast.AsyncFunctionDef):
                methods.append(PythonParser._extract_function(child))

        return ParsedClass(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=docstring,
            decorators=decorators,
            bases=bases,
            methods=methods,
        )

    @staticmethod
    def _is_method(node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.Module) -> bool:
        """Check whether a function definition is a method inside a class."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in ast.iter_child_nodes(parent):
                    if child is node:
                        return True
        return False