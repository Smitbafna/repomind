"""
analyzer.py
-----------
Walks a local repository and builds a graph of nodes (files) and edges
(import dependencies).  Supports Python, JavaScript/TypeScript, and C/C++.
"""

import os
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple


# ---------------------------------------------------------------------------
# Language-specific import extractors
# ---------------------------------------------------------------------------

def _extract_python_imports(lines: List[str]) -> List[str]:
    """Return bare module names from `import x` / `from x import y`."""
    imports = []
    for line in lines:
        m = re.match(r'^\s*(?:import|from)\s+([\w.]+)', line)
        if m:
            imports.append(m.group(1))
    return imports


def _extract_js_imports(lines: List[str]) -> List[str]:
    """
    Capture:
      import ... from './foo'
      import ... from '../bar/baz'
      const x = require('./qux')
    Returns the raw specifier string.
    """
    imports = []
    from_re = re.compile(r"""(?:import|export)\s+.*?\s+from\s+['"]([^'"]+)['"]""")
    req_re  = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
    for line in lines:
        for pat in (from_re, req_re):
            m = pat.search(line)
            if m:
                imports.append(m.group(1))
    return imports


def _extract_c_imports(lines: List[str]) -> List[str]:
    """Capture `#include "local.h"` (skip angle-bracket system headers)."""
    imports = []
    inc_re = re.compile(r'^\s*#include\s+"([^"]+)"')
    for line in lines:
        m = inc_re.match(line)
        if m:
            imports.append(m.group(1))
    return imports


_LANGUAGE_MAP: Dict[str, Tuple[str, callable]] = {
    ".py":   ("Python",     _extract_python_imports),
    ".js":   ("JavaScript", _extract_js_imports),
    ".jsx":  ("JavaScript", _extract_js_imports),
    ".ts":   ("TypeScript", _extract_js_imports),
    ".tsx":  ("TypeScript", _extract_js_imports),
    ".c":    ("C",          _extract_c_imports),
    ".cpp":  ("C++",        _extract_c_imports),
    ".h":    ("C/C++",      _extract_c_imports),
    ".hpp":  ("C++",        _extract_c_imports),
}

_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".next",
    ".nuxt", "coverage", ".tox",
}


# ---------------------------------------------------------------------------
# Complexity heuristic  (simple cyclomatic-like proxy)
# ---------------------------------------------------------------------------

_COMPLEXITY_RE = re.compile(
    r'\b(if|elif|else|for|while|case|catch|except|&&|\|\|)\b'
)

def _complexity(lines: List[str]) -> int:
    """Count branch-point keywords as a rough complexity score."""
    score = 1
    for line in lines:
        score += len(_COMPLEXITY_RE.findall(line))
    return score


# ---------------------------------------------------------------------------
# Edge resolution helpers
# ---------------------------------------------------------------------------

def _resolve_python_edge(imp: str, node_ids) -> str | None:
    guessed = imp.replace(".", "/") + ".py"
    return guessed if guessed in node_ids else None


def _resolve_js_edge(imp: str, source_rel: str, node_ids) -> str | None:
    """
    Resolve relative JS/TS import specifiers to a known node id.
    Tries several extensions and index files.
    """
    if not imp.startswith("."):
        return None          # third-party package — skip

    source_dir = os.path.dirname(source_rel)
    base = os.path.normpath(os.path.join(source_dir, imp)).replace("\\", "/")

    candidates = [
        base,
        base + ".js",
        base + ".jsx",
        base + ".ts",
        base + ".tsx",
        base + "/index.js",
        base + "/index.ts",
        base + "/index.jsx",
        base + "/index.tsx",
    ]
    for c in candidates:
        if c in node_ids:
            return c
    return None


def _resolve_c_edge(imp: str, source_rel: str, node_ids) -> str | None:
    source_dir = os.path.dirname(source_rel)
    candidate = os.path.normpath(os.path.join(source_dir, imp)).replace("\\", "/")
    return candidate if candidate in node_ids else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_repo(root_path: str) -> dict:
    root_path = os.path.abspath(root_path)
    if not os.path.isdir(root_path):
        raise FileNotFoundError(root_path)

    nodes = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune directories in-place so os.walk doesn't descend into them
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in _SKIP_DIRS
        ]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in _LANGUAGE_MAP:
                continue

            language, extractor = _LANGUAGE_MAP[ext]
            full_path = os.path.join(dirpath, filename)
            rel_path  = os.path.relpath(full_path, root_path).replace("\\", "/")

            try:
                with open(full_path, "r", errors="ignore") as fh:
                    lines = fh.readlines()
            except OSError:
                continue

            loc        = len(lines)
            imports    = extractor(lines)
            complexity = _complexity(lines)

            nodes.append({
                "id":         rel_path,
                "label":      filename,
                "language":   language,
                "loc":        loc,
                "complexity": complexity,
                "imports":    imports,
                "full_path":  full_path,   # included so frontend can POST /summarize
            })

    # Build edges
    node_ids = {n["id"] for n in nodes}
    edges = []
    seen  = set()

    for node in nodes:
        ext = os.path.splitext(node["id"])[1].lower()
        for imp in node["imports"]:
            if ext == ".py":
                target = _resolve_python_edge(imp, node_ids)
            elif ext in (".js", ".jsx", ".ts", ".tsx"):
                target = _resolve_js_edge(imp, node["id"], node_ids)
            elif ext in (".c", ".cpp", ".h", ".hpp"):
                target = _resolve_c_edge(imp, node["id"], node_ids)
            else:
                target = None

            if target and target != node["id"]:
                key = (node["id"], target)
                if key not in seen:
                    seen.add(key)
                    edges.append({"source": node["id"], "target": target})

    return {
        "root":  root_path,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_files": len(nodes),
            "total_edges": len(edges),
            "languages":   _count_languages(nodes),
        },
    }


def _count_languages(nodes) -> dict:
    counts: Dict[str, int] = {}
    for n in nodes:
        counts[n["language"]] = counts.get(n["language"], 0) + 1
    return counts