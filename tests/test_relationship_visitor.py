from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from backend.core.relationships.extractor import RelationshipExtractor
from backend.core.relationships.models import RelationshipType


class TestRelationshipExtractor:
    """Test suite for the relationship extractor."""

    def setup_method(self) -> None:
        self.extractor = RelationshipExtractor()

    def test_extract_function_calls(self) -> None:
        source = """
def greet(name: str) -> str:
    return format_greeting(name)

def format_greeting(name: str) -> str:
    return f"Hello, {name}!"
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        calls = [r for r in rels if r.relationship_type == RelationshipType.CALLS]
        assert len(calls) == 1
        assert calls[0].source_symbol == "greet"
        assert calls[0].target_symbol == "format_greeting"

    def test_extract_method_calls(self) -> None:
        source = """
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

    def double_add(self, a: int, b: int) -> int:
        return self.add(a, b)
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        calls = [r for r in rels if r.relationship_type == RelationshipType.CALLS]
        assert len(calls) == 1
        assert calls[0].source_symbol == "Calculator.double_add"
        assert "add" in calls[0].target_symbol

    def test_extract_class_inheritance(self) -> None:
        source = """
class Animal:
    pass

class Dog(Animal):
    pass

class GoldenRetriever(Dog, Animal):
    pass
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        inherits = [r for r in rels if r.relationship_type == RelationshipType.INHERITS]
        # Animal has no bases, Dog inherits Animal, GoldenRetriever inherits Dog and Animal
        assert len(inherits) == 3

        inherits_by_source = {r.source_symbol: r.target_symbol for r in inherits}
        assert inherits_by_source["Dog"] == "Animal"
        # GoldenRetriever has two bases, so two INHERITS relationships
        golden_inherits = [r for r in inherits if r.source_symbol == "GoldenRetriever"]
        assert len(golden_inherits) == 2
        golden_targets = {r.target_symbol for r in golden_inherits}
        assert golden_targets == {"Dog", "Animal"}

    def test_extract_class_inheritance_count(self) -> None:
        source = """
class Animal:
    pass

class Dog(Animal):
    pass
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        inherits = [r for r in rels if r.relationship_type == RelationshipType.INHERITS]
        assert len(inherits) == 1
        assert inherits[0].source_symbol == "Dog"
        assert inherits[0].target_symbol == "Animal"

    def test_extract_imports(self) -> None:
        source = """
import os
from typing import Optional, List
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        imports = [r for r in rels if r.relationship_type == RelationshipType.IMPORTS]
        assert len(imports) == 3

        import_targets = {r.target_symbol for r in imports}
        assert "os" in import_targets
        assert "typing.Optional" in import_targets
        assert "typing.List" in import_targets

    def test_extract_return_annotations(self) -> None:
        source = """
def get_user(user_id: int) -> User:
    return User(id=user_id)
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        returns = [r for r in rels if r.relationship_type == RelationshipType.RETURNS]
        assert len(returns) >= 1
        assert any(r.source_symbol == "get_user" and r.target_symbol == "User" for r in returns)

    def test_extract_parameter_annotations(self) -> None:
        source = """
def process(data: dict, config: Config) -> None:
    pass
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        uses = [r for r in rels if r.relationship_type == RelationshipType.USES]
        # 'data' has annotation 'dict', 'config' has annotation 'Config', and 'Config' is referenced in function body
        param_uses = [r for r in uses if r.source_symbol == "process"]
        param_targets = {r.target_symbol for r in param_uses}
        assert "dict" in param_targets
        assert "Config" in param_targets

    def test_extract_references(self) -> None:
        source = """
x = 10
y = x
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        refs = [r for r in rels if r.relationship_type == RelationshipType.REFERENCES]
        # x is referenced (assigned, then loaded), y is assigned
        ref_targets = {r.target_symbol for r in refs}
        assert "x" in ref_targets
        assert "y" in ref_targets

    def test_extract_defines(self) -> None:
        source = """
class MyClass:
    def method_a(self):
        pass

    def method_b(self):
        pass
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        defines = [r for r in rels if r.relationship_type == RelationshipType.DEFINES]
        assert len(defines) == 2
        define_targets = {r.target_symbol for r in defines}
        assert "MyClass.method_a" in define_targets
        assert "MyClass.method_b" in define_targets

    def test_graph_construction(self) -> None:
        source = """
import os

class BaseModel:
    pass

class User(BaseModel):
    def get_name(self) -> str:
        return os.getenv("NAME")
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        graph = self.extractor.extract_graph(rels)

        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

        # Verify nodes have required fields
        for node in graph.nodes:
            assert node.id
            assert node.label
            assert node.kind

        # Verify edges have required fields
        for edge in graph.edges:
            assert edge.source
            assert edge.target
            assert edge.type

    def test_empty_file(self) -> None:
        rels = self.extractor.extract_relationships(_make_file(""))
        assert rels == []

    def test_syntax_error(self) -> None:
        rels = self.extractor.extract_relationships(_make_file("def broken("))
        assert rels == []

    def test_extract_async_function_calls(self) -> None:
        source = """
async def fetch_data():
    return await load_data()

async def load_data():
    return {"data": "mock"}
"""
        rels = self.extractor.extract_relationships(_make_file(source))
        calls = [r for r in rels if r.relationship_type == RelationshipType.CALLS]
        assert len(calls) == 1
        assert calls[0].source_symbol == "fetch_data"
        assert calls[0].target_symbol == "load_data"


def _make_file(source: str) -> Path:
    """Create a temporary Python file with the given source code."""
    tmp = NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    tmp.write(source)
    tmp.close()
    return Path(tmp.name)