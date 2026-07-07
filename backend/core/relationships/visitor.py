from __future__ import annotations

import ast
from typing import Any

from backend.core.relationships.models import Relationship, RelationshipType


class RelationshipVisitor(ast.NodeVisitor):
    """AST visitor that extracts relationships from Python source code.

    Uses the visitor pattern to walk the AST and collect relationships
    without duplicating traversal logic. This implementation is specific
    to Python's AST but the output ``Relationship`` dataclass is language-
    agnostic, making it extensible to Tree-sitter later.
    """

    def __init__(self, source_file: str = "") -> None:
        self.source_file = source_file
        self.relationships: list[Relationship] = []
        self._current_function: str | None = None
        self._current_class: str | None = None

    def visit_Module(self, node: ast.Module) -> None:
        """Walk all top-level statements and class/function bodies."""
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        previous_class = self._current_class
        self._current_class = node.name
        full_class = f"{self._current_class}"

        # Record INHERITS relationships
        for base in node.bases:
            base_name = ast.unparse(base)
            self._add_relationship(
                source=full_class,
                target=base_name,
                rel_type=RelationshipType.INHERITS,
                lineno=node.lineno,
            )

        # Record DEFINES relationship (class defines its methods)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_name = f"{full_class}.{child.name}"
                self._add_relationship(
                    source=full_class,
                    target=method_name,
                    rel_type=RelationshipType.DEFINES,
                    lineno=child.lineno,
                )

        self.generic_visit(node)
        self._current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        previous_function = self._current_function
        func_name = (
            f"{self._current_class}.{node.name}"
            if self._current_class
            else node.name
        )
        self._current_function = func_name

        # Record RETURNS relationships from return annotations
        if node.returns:
            return_type = ast.unparse(node.returns)
            self._add_relationship(
                source=func_name,
                target=return_type,
                rel_type=RelationshipType.RETURNS,
                lineno=node.lineno,
            )

        # Record USES relationships from parameter type annotations
        for arg in node.args.args:
            if arg.annotation:
                param_type = ast.unparse(arg.annotation)
                self._add_relationship(
                    source=func_name,
                    target=param_type,
                    rel_type=RelationshipType.USES,
                    lineno=arg.lineno if hasattr(arg, "lineno") else node.lineno,
                )

        self.generic_visit(node)
        self._current_function = previous_function

    def visit_Call(self, node: ast.Call) -> None:
        """Record CALLS relationships."""
        caller = self._current_function or self._current_class or "<module>"
        callee = ast.unparse(node.func)

        self._add_relationship(
            source=caller,
            target=callee,
            rel_type=RelationshipType.CALLS,
            lineno=node.lineno,
        )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Record IMPORT relationships."""
        source = self._current_class or self._current_function or "<module>"
        for alias in node.names:
            self._add_relationship(
                source=source,
                target=alias.name,
                rel_type=RelationshipType.IMPORTS,
                lineno=node.lineno,
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Record IMPORT relationships for from-imports."""
        source = self._current_class or self._current_function or "<module>"
        module_base = node.module or ""
        for alias in node.names:
            target = f"{module_base}.{alias.name}" if module_base else alias.name
            self._add_relationship(
                source=source,
                target=target,
                rel_type=RelationshipType.IMPORTS,
                lineno=node.lineno,
            )

    def visit_Assign(self, node: ast.Assign) -> None:
        """Record REFERENCES relationships for assigned names."""
        source = self._current_function or self._current_class or "<module>"
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._add_relationship(
                    source=source,
                    target=target.id,
                    rel_type=RelationshipType.REFERENCES,
                    lineno=node.lineno,
                )
            elif isinstance(target, ast.Attribute):
                attr_name = ast.unparse(target)
                self._add_relationship(
                    source=source,
                    target=attr_name,
                    rel_type=RelationshipType.REFERENCES,
                    lineno=node.lineno,
                )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Record USES relationships for attribute access."""
        source = self._current_function or self._current_class or "<module>"
        attr_name = ast.unparse(node)
        self._add_relationship(
            source=source,
            target=attr_name,
            rel_type=RelationshipType.USES,
            lineno=node.lineno,
        )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Record REFERENCES relationships for name references in load context."""
        source = self._current_function or self._current_class or "<module>"
        if isinstance(node.ctx, ast.Load):
            self._add_relationship(
                source=source,
                target=node.id,
                rel_type=RelationshipType.REFERENCES,
                lineno=node.lineno,
            )
        self.generic_visit(node)

    # ── helpers ──────────────────────────────────────────────────

    def _add_relationship(
        self,
        source: str,
        target: str,
        rel_type: RelationshipType,
        lineno: int,
    ) -> None:
        """Add a relationship, avoiding trivial self-references and duplicates."""
        if source == target:
            return
        # Avoid duplicates in the same batch
        for rel in self.relationships:
            if (
                rel.source_symbol == source
                and rel.target_symbol == target
                and rel.relationship_type == rel_type
            ):
                return

        self.relationships.append(
            Relationship(
                source_symbol=source,
                target_symbol=target,
                relationship_type=rel_type,
                source_file=self.source_file,
                target_file="",
                line_number=lineno,
            )
        )