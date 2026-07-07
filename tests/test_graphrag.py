from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.core.graphrag.context import GraphContextBuilder
from backend.core.graphrag.expansion import GraphExpander
from backend.core.graphrag.graph import GraphBuilder
from backend.core.graphrag.models import GraphEdge, GraphNode, GraphSubgraph
from backend.core.graphrag.ranking import GraphRanker
from backend.core.graphrag.retriever import GraphRetriever
from backend.core.graphrag.traversal import GraphTraverser
from backend.database.models import Relationship as RelationshipModel


class TestGraphBuilder:
    """Test suite for the graph builder."""

    def setup_method(self) -> None:
        self.builder = GraphBuilder()

    def test_build_empty(self) -> None:
        nodes, adjacency = self.builder.build([])
        assert nodes == {}
        assert adjacency == {}

    def test_build_single_relationship(self) -> None:
        rels = [
            _make_rel("MyClass", "BaseClass", "INHERITS", "models.py"),
        ]
        nodes, adjacency = self.builder.build(rels)
        assert "MyClass" in nodes
        assert "BaseClass" in nodes
        assert len(adjacency["MyClass"]) == 1
        assert adjacency["MyClass"][0].type == "INHERITS"

    def test_build_multiple_relationships(self) -> None:
        rels = [
            _make_rel("func_a", "func_b", "CALLS", "app.py"),
            _make_rel("MyClass", "BaseClass", "INHERITS", "models.py"),
            _make_rel("app", "os", "IMPORTS", "app.py"),
        ]
        nodes, adjacency = self.builder.build(rels)
        # 3 edges = 6 nodes (source + target for each)
        assert len(nodes) == 6
        assert len(adjacency) == 3

    def test_infer_kind_class(self) -> None:
        kind = GraphBuilder._infer_kind("MyClass", "models.py")
        assert kind == "class"

    def test_infer_kind_function(self) -> None:
        kind = GraphBuilder._infer_kind("my_function", "utils.py")
        assert kind == "function"

    def test_infer_kind_method(self) -> None:
        kind = GraphBuilder._infer_kind("MyClass.my_method", "models.py")
        assert kind == "method"

    def test_edge_weight(self) -> None:
        assert GraphBuilder._get_edge_weight("DEFINES") == 1.5
        assert GraphBuilder._get_edge_weight("INHERITS") == 1.4
        assert GraphBuilder._get_edge_weight("UNKNOWN") == 1.0


class TestGraphTraverser:
    """Test suite for graph traversal."""

    def setup_method(self) -> None:
        self.traverser = GraphTraverser()

    def test_bfs_simple(self) -> None:
        nodes = {
            "A": GraphNode(id="A", label="A", kind="class"),
            "B": GraphNode(id="B", label="B", kind="function"),
            "C": GraphNode(id="C", label="C", kind="function"),
        }
        adjacency = {
            "A": [GraphEdge(source="A", target="B", type="CALLS")],
            "B": [GraphEdge(source="B", target="C", type="CALLS")],
        }
        subgraph = self.traverser.bfs(nodes, adjacency, ["A"], max_depth=2)
        assert len(subgraph.nodes) == 3
        assert len(subgraph.edges) == 2

    def test_bfs_depth_limit(self) -> None:
        nodes = {
            "A": GraphNode(id="A", label="A", kind="class"),
            "B": GraphNode(id="B", label="B", kind="function"),
            "C": GraphNode(id="C", label="C", kind="function"),
        }
        adjacency = {
            "A": [GraphEdge(source="A", target="B", type="CALLS")],
            "B": [GraphEdge(source="B", target="C", type="CALLS")],
        }
        subgraph = self.traverser.bfs(nodes, adjacency, ["A"], max_depth=1)
        assert len(subgraph.nodes) == 2  # A and B
        assert len(subgraph.edges) == 1

    def test_bfs_cycle_detection(self) -> None:
        nodes = {
            "A": GraphNode(id="A", label="A", kind="class"),
            "B": GraphNode(id="B", label="B", kind="function"),
        }
        adjacency = {
            "A": [GraphEdge(source="A", target="B", type="CALLS")],
            "B": [GraphEdge(source="B", target="A", type="CALLS")],
        }
        subgraph = self.traverser.bfs(nodes, adjacency, ["A"], max_depth=3)
        assert len(subgraph.nodes) == 2  # No infinite loop
        assert len(subgraph.edges) == 2

    def test_bfs_empty_entry(self) -> None:
        nodes = {"A": GraphNode(id="A", label="A", kind="class")}
        adjacency = {}
        subgraph = self.traverser.bfs(nodes, adjacency, ["NONEXISTENT"])
        assert len(subgraph.nodes) == 0

    def test_weighted_traversal(self) -> None:
        nodes = {
            "A": GraphNode(id="A", label="A", kind="class"),
            "B": GraphNode(id="B", label="B", kind="function"),
            "C": GraphNode(id="C", label="C", kind="function"),
        }
        adjacency = {
            "A": [
                GraphEdge(source="A", target="B", type="CALLS", weight=1.5),
                GraphEdge(source="A", target="C", type="REFERENCES", weight=0.5),
            ],
        }
        subgraph = self.traverser.weighted_traversal(
            nodes, adjacency, ["A"], min_weight=1.0
        )
        assert "B" in {n.id for n in subgraph.nodes}
        assert "C" not in {n.id for n in subgraph.nodes}  # Below min_weight


class TestGraphRanker:
    """Test suite for graph ranking."""

    def setup_method(self) -> None:
        self.ranker = GraphRanker()

    def test_rank_empty(self) -> None:
        scores = self.ranker.rank(GraphSubgraph())
        assert scores == {}

    def test_rank_single_node(self) -> None:
        subgraph = GraphSubgraph(
            nodes=[GraphNode(id="A", label="A", kind="class")],
            traversal_order=["A"],
        )
        scores = self.ranker.rank(subgraph)
        assert "A" in scores
        assert scores["A"] > 0

    def test_rank_keyword_boost(self) -> None:
        subgraph = GraphSubgraph(
            nodes=[
                GraphNode(id="Parser", label="Parser", kind="class"),
                GraphNode(id="Helper", label="Helper", kind="function"),
            ],
            traversal_order=["Parser", "Helper"],
        )
        scores = self.ranker.rank(subgraph, query_keywords=["Parser"])
        assert scores["Parser"] > scores["Helper"]

    def test_rank_and_sort(self) -> None:
        subgraph = GraphSubgraph(
            nodes=[
                GraphNode(id="A", label="A", kind="class"),
                GraphNode(id="B", label="B", kind="function"),
                GraphNode(id="C", label="C", kind="function"),
            ],
            traversal_order=["A", "B", "C"],
        )
        ranked = self.ranker.rank_and_sort(subgraph, top_k=2)
        assert len(ranked.nodes) == 2


class TestGraphExpander:
    """Test suite for graph expansion."""

    def setup_method(self) -> None:
        self.expander = GraphExpander()

    def test_expand_empty(self) -> None:
        result = self.expander.expand({}, {}, GraphSubgraph())
        assert len(result.nodes) == 0

    def test_expand_adds_nodes(self) -> None:
        nodes = {
            "A": GraphNode(id="A", label="A", kind="class"),
            "B": GraphNode(id="B", label="B", kind="function"),
            "C": GraphNode(id="C", label="C", kind="function"),
        }
        adjacency = {
            "A": [GraphEdge(source="A", target="B", type="CALLS")],
            "B": [GraphEdge(source="B", target="C", type="CALLS")],
        }
        subgraph = GraphSubgraph(
            nodes=[nodes["A"]],
            entry_points=["A"],
            traversal_order=["A"],
        )
        expanded = self.expander.expand(nodes, adjacency, subgraph, max_depth=2)
        assert len(expanded.nodes) == 3


class TestGraphContextBuilder:
    """Test suite for graph context builder."""

    def setup_method(self) -> None:
        self.builder = GraphContextBuilder()

    def test_build_empty(self) -> None:
        context = self.builder.build_context(GraphSubgraph())
        assert context == ""

    def test_build_with_nodes(self) -> None:
        subgraph = GraphSubgraph(
            nodes=[
                GraphNode(id="MyClass", label="MyClass", kind="class", file_path="models.py"),
                GraphNode(id="my_func", label="my_func", kind="function", file_path="utils.py"),
            ],
            edges=[
                GraphEdge(source="MyClass", target="my_func", type="CALLS"),
            ],
            scores={"MyClass": 0.9, "my_func": 0.5},
        )
        context = self.builder.build_context(subgraph)
        assert "MyClass" in context
        assert "my_func" in context
        assert "CALLS" in context

    def test_build_with_sources(self) -> None:
        subgraph = GraphSubgraph(
            nodes=[GraphNode(id="A", label="A", kind="class", file_path="a.py")],
            scores={"A": 0.8},
        )
        context, sources = self.builder.build_context_with_sources(subgraph)
        assert len(sources) == 1
        assert sources[0]["symbol"] == "A"
        assert sources[0]["score"] == 0.8


class TestGraphRetriever:
    """Test suite for graph retriever."""

    def setup_method(self) -> None:
        self.retriever = GraphRetriever()

    def test_retrieve_empty(self) -> None:
        result = self.retriever.retrieve([], "test query")
        assert len(result.nodes) == 0

    def test_retrieve_with_relationships(self) -> None:
        rels = [
            _make_rel("Parser", "BaseParser", "INHERITS", "parser.py"),
            _make_rel("Parser", "parse_file", "DEFINES", "parser.py"),
            _make_rel("parse_file", "read_file", "CALLS", "parser.py"),
        ]
        result = self.retriever.retrieve(rels, "How does Parser work?")
        assert len(result.nodes) > 0
        assert len(result.edges) > 0

    def test_retrieve_fallback_entry(self) -> None:
        rels = [
            _make_rel("A", "B", "CALLS", "a.py"),
            _make_rel("B", "C", "CALLS", "b.py"),
            _make_rel("C", "D", "CALLS", "c.py"),
        ]
        result = self.retriever.retrieve(rels, "unrelated query")
        # Should fall back to degree-based entry points
        assert len(result.nodes) > 0


def _make_rel(
    source: str, target: str, rel_type: str, file_path: str
) -> RelationshipModel:
    """Create a mock relationship model for testing."""
    return RelationshipModel(
        id=f"{source}-{target}",
        repository_id="test-repo",
        source_symbol=source,
        target_symbol=target,
        relationship_type=rel_type,
        source_file=file_path,
        target_file=file_path,
        line_number=1,
    )