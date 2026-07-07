from __future__ import annotations

import logging

from backend.core.graphrag.models import GraphSubgraph

logger = logging.getLogger(__name__)


class GraphContextBuilder:
    """Builds context from graph subgraphs for LLM consumption.

    Instead of returning isolated documents, returns connected
    code structures with provenance.
    """

    def build_context(
        self,
        subgraph: GraphSubgraph,
        max_nodes: int = 20,
    ) -> str:
        """Build a context string from a graph subgraph.

        Args:
            subgraph: The ranked subgraph.
            max_nodes: Maximum nodes to include.

        Returns:
            A formatted context string.
        """
        if not subgraph.nodes:
            return ""

        sections: list[str] = []
        nodes_by_kind: dict[str, list] = {}
        for node in subgraph.nodes[:max_nodes]:
            kind = node.kind
            if kind not in nodes_by_kind:
                nodes_by_kind[kind] = []
            nodes_by_kind[kind].append(node)

        # Order by kind priority.
        kind_order = ["class", "function", "method", "module", "import", "commit"]
        for kind in kind_order:
            if kind not in nodes_by_kind:
                continue
            for node in nodes_by_kind[kind]:
                score = subgraph.scores.get(node.id, 0.0)
                parts = [f"=== {node.label} ({node.kind}) ==="]
                if node.file_path:
                    parts.append(f"File: {node.file_path}")
                if score > 0:
                    parts.append(f"Relevance: {score:.3f}")

                # Find related edges.
                related = [
                    e for e in subgraph.edges
                    if e.source == node.id or e.target == node.id
                ]
                if related:
                    rel_strs = []
                    for e in related[:5]:
                        if e.source == node.id:
                            rel_strs.append(f"  → {e.type} → {e.target}")
                        else:
                            rel_strs.append(f"  ← {e.type} ← {e.source}")
                    parts.append("Relationships:")
                    parts.extend(rel_strs)

                sections.append("\n".join(parts))

        return "\n\n".join(sections)

    def build_context_with_sources(
        self,
        subgraph: GraphSubgraph,
        max_nodes: int = 20,
    ) -> tuple[str, list[dict]]:
        """Build context and return source metadata.

        Args:
            subgraph: The ranked subgraph.
            max_nodes: Maximum nodes to include.

        Returns:
            A tuple of (context_string, sources_list).
        """
        context = self.build_context(subgraph, max_nodes)
        sources = [
            {
                "symbol": n.id,
                "label": n.label,
                "kind": n.kind,
                "file": n.file_path,
                "score": subgraph.scores.get(n.id, 0.0),
            }
            for n in subgraph.nodes[:max_nodes]
        ]
        return context, sources