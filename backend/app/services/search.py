"""Repository file search and a lightweight code outline (stdlib ast for Python, regex for TS/JS).

Tree-sitter is not used in this MVP; ast/regex cover the generated languages without native deps.
"""

from __future__ import annotations

import ast
import re

from app.services.workspace import Workspace

TS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(function|class|const|interface|type)\s+([A-Za-z_$][\w$]*)",
    re.M,
)


def search(ws: Workspace, query: str, limit: int = 50) -> list[dict]:
    q = query.lower()
    hits: list[dict] = []
    for rel in ws.list_files():
        text = ws.read(rel) or ""
        for i, line in enumerate(text.splitlines(), 1):
            if q in line.lower():
                hits.append({"path": rel, "line": i, "text": line.strip()[:200]})
                if len(hits) >= limit:
                    return hits
    return hits


def outline(ws: Workspace) -> list[dict]:
    result: list[dict] = []
    for rel in ws.list_files():
        text = ws.read(rel) or ""
        symbols: list[dict] = []
        if rel.endswith(".py"):
            try:
                for node in ast.walk(ast.parse(text)):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        kind = "class" if isinstance(node, ast.ClassDef) else "function"
                        symbols.append({"kind": kind, "name": node.name, "line": node.lineno})
            except SyntaxError:
                symbols.append({"kind": "error", "name": "syntax error", "line": 0})
        elif rel.endswith((".ts", ".tsx", ".js", ".jsx")):
            for m in TS_SYMBOL_RE.finditer(text):
                symbols.append({"kind": m.group(1), "name": m.group(2), "line": text[: m.start()].count("\n") + 1})
        if symbols:
            result.append({"path": rel, "symbols": sorted(symbols, key=lambda s: s["line"])})
    return result
