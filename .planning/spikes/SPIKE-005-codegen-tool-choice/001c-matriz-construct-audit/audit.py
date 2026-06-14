"""Spike 001c: matriz async-only construct audit (Recipe 4 from 12-RESEARCH.md).

Walks ``packages/matriz-client/src/matriz_client/aio.py`` with stdlib ``ast`` and emits
a classification table of every async-only construct. D-SCOPE-02 merge gate: zero
TBD/REVIEW/DENY-LIST-VIOLATION rows.

Constants:

- ``DENY_LIST`` — 4 files explicitly excluded from any future codegen scope. Their
  async primitives live in those files; matriz ``aio.py`` only delegates via imports.
- ``KNOWN_SYNC_EMISSIONS`` — constructs with a known sync emission rule
  (unasync default replacement OR matriz-specific additional_replacements).
- ``HARD_DENY`` — bare references to deny-listed primitives in aio.py module body
  (NOT via re-export import) are FATAL: classified ``DENY-LIST-VIOLATION``.

Read-only: never mutates ``packages/matriz-client/`` (Anti-Pitfall 2).

Run from the audit dir to capture audit-run.log:

    cd .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit
    uv run python audit.py 2>&1 | tee audit-run.log

After the automated run, the operator manually edits ``matriz-aio-constructs.md`` to
flip ``REVIEW`` rows to either ``deny-list-confirmed`` (with import-source pointer) or
``comment-only`` (with docstring line pointer). The merge gate then re-checks:

    grep -cE '\\| (REVIEW|TBD|DENY-LIST-VIOLATION) \\|' matriz-aio-constructs.md  # must be 0
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# --- paths ----------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE = REPO_ROOT / "packages/matriz-client/src/matriz_client/aio.py"
OUTPUT = Path(__file__).resolve().parent / "matriz-aio-constructs.md"

# --- constants (Recipe 4) ------------------------------------------------

# Files explicitly excluded from any future codegen scope (architectural invariant
# per ARCHITECTURE.md; locked by Phase 10 spike research):
DENY_LIST: frozenset[str] = frozenset(
    {
        "_token_store.py",  # 3-way TokenStore: threading.Lock + asyncio.Lock + ws thread
        "_refresh_policy.py",  # retry + backoff + fail-cache; sync-only by design
        "_refresh.py",  # MatrizRefresh adapter
        "ws_client.py",  # WebSocket daemon thread
    }
)

# Constructs with a known sync emission via unasync defaults + additional_replacements:
KNOWN_SYNC_EMISSIONS: dict[str, str] = {
    "AsyncFunctionDef": "FunctionDef (async stripped — unasync default)",
    "AsyncWith": "With (async with stripped — unasync default)",
    "AsyncFor": "For (async for stripped — unasync default)",
    "Await": "removed (await keyword stripped — unasync default)",
    "__aenter__": "__enter__ (unasync default)",
    "__aexit__": "__exit__ (unasync default)",
    "__aiter__": "__iter__ (unasync default)",
    "__anext__": "__next__ (unasync default)",
    "aclose": "close (additional_replacements)",
    "aread": "read (additional_replacements)",
    "AsyncClient": "Client (additional_replacements)",
    "AsyncRetryTransport": "RetryTransport (additional_replacements)",
    "_atransport": "_transport (additional_replacements)",
    "_aensure_token": "_ensure_token (additional_replacements)",
}

# Bare references to deny-listed primitives in module body (NOT via re-export import)
# would be a deny-list violation — codegen cannot rewrite these:
HARD_DENY: dict[str, str] = {
    "asyncio.Lock": "lives in _token_store.py — deny-listed",
    "asyncio.to_thread": "lives in _token_store.py — deny-listed",
    "_get_async_lock": "lives in _token_store.py — deny-listed",
    "_async_locks": "lives in _token_store.py — deny-listed",
}

# --- helpers --------------------------------------------------------------


def _collect_string_literal_lines(tree: ast.AST) -> set[int]:
    """Return the set of line numbers covered by every string literal in the AST.

    A bare ``"asyncio.to_thread"`` mention inside a docstring or string literal is
    preserved verbatim by the unasync tokenizer (the tokenizer never descends into
    string contents). Lines inside string literals are tagged comment-only.
    """
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            for ln in range(start, end + 1):
                lines.add(ln)
    return lines


def _collect_deny_list_imports(tree: ast.AST, deny_list: frozenset[str]) -> dict[str, str]:
    """Return {imported_name: source_module} for symbols re-exported from deny-listed files."""
    deny_modules: set[str] = {deny.removesuffix(".py") for deny in deny_list}
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for deny_mod in deny_modules:
                if node.module.endswith(deny_mod):
                    for alias in node.names:
                        imports[alias.asname or alias.name] = node.module
                    break
    return imports


# --- main ----------------------------------------------------------------


def main() -> int:
    source = SOURCE.read_text()
    tree = ast.parse(source)

    string_lines = _collect_string_literal_lines(tree)
    deny_list_imports = _collect_deny_list_imports(tree, DENY_LIST)

    rows: list[tuple[int, str, str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            rows.append(
                (
                    node.lineno,
                    f"async def {node.name}",
                    "manual-sync-proof",
                    KNOWN_SYNC_EMISSIONS["AsyncFunctionDef"],
                )
            )
        elif isinstance(node, ast.AsyncWith):
            rows.append(
                (
                    node.lineno,
                    "async with ...",
                    "manual-sync-proof",
                    KNOWN_SYNC_EMISSIONS["AsyncWith"],
                )
            )
        elif isinstance(node, ast.AsyncFor):
            rows.append(
                (
                    node.lineno,
                    "async for ... in ...",
                    "manual-sync-proof",
                    KNOWN_SYNC_EMISSIONS["AsyncFor"],
                )
            )
        elif isinstance(node, ast.Await):
            rows.append(
                (
                    node.lineno,
                    "await <expr>",
                    "manual-sync-proof",
                    KNOWN_SYNC_EMISSIONS["Await"],
                )
            )
        elif isinstance(node, ast.Attribute):
            # asyncio.<attr> attribute access in module body. ast Constant string
            # nodes do NOT decompose into Attribute nodes, so any Attribute here
            # IS bare code (not inside a docstring).
            if isinstance(node.value, ast.Name) and node.value.id == "asyncio":
                name = f"asyncio.{node.attr}"
                if name in HARD_DENY:
                    rows.append(
                        (node.lineno, name, "DENY-LIST-VIOLATION", HARD_DENY[name])
                    )
                else:
                    rows.append((node.lineno, name, "REVIEW", "operator classifies"))

    # Detect any bare ``import asyncio`` / ``from asyncio import ...`` (would be
    # surprising; matriz aio.py is expected to delegate via _token_store):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "asyncio":
                    rows.append(
                        (
                            node.lineno,
                            "import asyncio",
                            "REVIEW",
                            "operator classifies — asyncio import in module body",
                        )
                    )
        elif isinstance(node, ast.ImportFrom) and node.module == "asyncio":
            for alias in node.names:
                rows.append(
                    (
                        node.lineno,
                        f"from asyncio import {alias.name}",
                        "REVIEW",
                        "operator classifies — asyncio symbol import",
                    )
                )

    # Docstring mentions: scan raw source lines that fall inside an ast.Constant(str)
    # node span and emit a `comment-only` row per token mention. This reflects the
    # FULL grep universe (Recipe 4 records ~128 hits; AST-visible constructs are
    # ~120). The remaining ~8 are docstring asyncio.* mentions.
    DOCSTRING_TOKENS = ("asyncio.Lock", "asyncio.to_thread", "asyncio.")
    src_lines = source.splitlines()
    for idx, line in enumerate(src_lines, start=1):
        if idx not in string_lines:
            continue
        for tok in DOCSTRING_TOKENS:
            if tok in line:
                rows.append(
                    (
                        idx,
                        f"docstring mention: {tok}",
                        "comment-only",
                        "inside string literal — tokenizer preserves verbatim",
                    )
                )
                break  # only one row per line

    # Sort by (line, construct)
    rows.sort(key=lambda r: (r[0], r[1]))

    # --- emit markdown table ---------------------------------------------

    loc = len(src_lines)
    md_lines = [
        "# Matriz aio.py — async-only construct audit\n",
        "\n",
        f"**Source:** `packages/matriz-client/src/matriz_client/aio.py` ({loc} LOC)\n",
        f"**Found:** {len(rows)} async-only construct occurrences\n",
        "**Generated by:** `audit.py` (stdlib `ast.walk` — read-only against source)\n",
        "\n",
        "| Line | Construct | Classification | Evidence |\n",
        "|------|-----------|----------------|----------|\n",
    ]
    for line, construct, classification, evidence in rows:
        md_lines.append(f"| {line} | `{construct}` | {classification} | {evidence} |\n")

    unresolved = [r for r in rows if r[2] in {"TBD", "REVIEW", "DENY-LIST-VIOLATION"}]
    md_lines.append(f"\n## Unresolved rows: {len(unresolved)}\n")
    if unresolved:
        md_lines.append(
            "\n**MERGE GATE FAILURE:** D-SCOPE-02 requires zero unresolved rows.\n"
            "The operator must triage each `REVIEW`/`TBD`/`DENY-LIST-VIOLATION` row by\n"
            "editing this file directly (see audit.py docstring + Triage Notes in\n"
            "FINDING.md).\n"
        )
    else:
        md_lines.append("\n**MERGE GATE PASS:** zero unresolved rows.\n")

    OUTPUT.write_text("".join(md_lines))
    print(f"Audit written to {OUTPUT}")
    print(f"Total rows: {len(rows)}")
    print(f"Unresolved (REVIEW/TBD/DENY-LIST-VIOLATION): {len(unresolved)}")
    print(
        f"Deny-list imports detected in aio.py (re-exports): "
        f"{sorted(deny_list_imports.keys())}"
    )
    return 0 if not unresolved else 1


if __name__ == "__main__":
    sys.exit(main())
