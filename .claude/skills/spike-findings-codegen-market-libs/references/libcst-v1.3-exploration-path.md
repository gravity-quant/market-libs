# libcst v1.3 Exploration Path — Reference

The v1.3 libcst spike is captured in
`.planning/todos/pending/spike-codegen-libcst-v1.3.md`. This reference summarizes the
strategic direction and what the v1.3 spike inherits from SPIKE-005.

## Why libcst over unasync at v1.3?

Per locked decision D-NOGO-01 (Phase 12 CONTEXT.md): NO-GO on unasync defers REFAC-06
to v1.3 with a dedicated libcst spike. Inline evaluation of libcst during Phase 12 is
EXCLUDED because:

1. It would violate the D-SCOPE-03 1-day timebox (already used by unasync evaluation).
2. v1.2 milestone scope is already 5 phases + 1 conditional.
3. libcst is structurally different from unasync (AST-level vs token-level) — it needs
   its own RESEARCH/CONTEXT pair and a tailored D-RIGOR-02-equivalent gate.

## What libcst brings that unasync doesn't

| Capability | unasync 0.6.0 (SPIKE-005) | libcst >=1.8.0,<2 (v1.3 target) |
|------------|----------------------------|-----------------------------------|
| Model | Token-level replacement | AST-level concrete syntax tree |
| Source-shape asymmetry handling | Cannot (tokens are atomic) | CAN (CSTTransformer detects-and-rewrites multi-token patterns) |
| Whitespace/comment preservation | Post-process via ruff format | Native (libcst preserves trivia verbatim) |
| Import direction reversal | Cannot | CAN (analyze imports + definitions; move definitions across modules) |
| Single-line import-order normalization | Cannot (ruff doesn't converge either) | CAN (ImportNormalizer transformer) |
| Docstring localization (substring rewrites) | Cannot (string literals opaque) | CAN (rewrite cst.SimpleString value via transformer) |
| Rule expression model | `additional_replacements` dict (single-token only) | CSTTransformer subclasses (multi-pattern, Pythonic, testable) |
| Per-package config size | Bounded (Pitfall 8 warns >10) | No count cap (transformer rules are code, not data) |
| Performance | Fast (single tokenizer pass) | Slower (parse + transform + regen) — but codegen is offline |
| Ecosystem precedent | httpcore, elasticsearch-py, trio | Instagram (mypy ecosystem), Meta-scale codemods |

## What v1.3 libcst spike must address

The 3 SPIKE-005 FAIL items (1, 4, 6) all trace to ONE source-of-truth shape problem.
libcst's AST-level approach can close each:

### Item 1 / Item 6 — Import direction asymmetry

**Problem:** `aio.py` imports `_validate_max_retries` from `client.py`. unasync token-
replaces the line verbatim → self-import → circular collection.

**libcst approach:** AST analyzer identifies the import statement + the corresponding
definition's owning module; transformer moves the definition to the canonical async-first
location (aio.py) and rewrites client.py to import it from aio.py.

```python
class ImportDirectionNormalizer(cst.CSTTransformer):
    def leave_ImportFrom(self, orig, upd):
        # Detect "from <pkg>.client import _validate_max_retries" in aio.py.
        # Rewrite to "from <pkg>.aio import _validate_max_retries" when emitting client.py.
        ...

    def leave_FunctionDef(self, orig, upd):
        # If function is owned by client.py in current source, but we're emitting client.py
        # from aio.py, the definition should already be present in aio.py — verify and emit.
        ...
```

### Item 4 — Single-line import-order asymmetry

**Problem:** `aio.py` has `from <pkg> import _transport, _core` (non-alphabetical).
unasync preserves token sequence; ruff format does NOT converge on single-line imports.

**libcst approach:** ImportNormalizer transformer reorders the `cst.ImportAlias` list
inside `cst.ImportFrom` to alphabetical.

```python
class ImportNormalizer(cst.CSTTransformer):
    def leave_ImportFrom(self, orig, upd):
        aliases = sorted(upd.names, key=lambda a: a.evaluated_name)
        return upd.with_changes(names=tuple(aliases))
```

### Item 1 (H1/H8/H9) — Docstring localization

**Problem:** Hand-written sync docstrings use "sincrónico" (etc.); async uses
"asincrónico". Token replacement can't reach substrings inside docstrings.

**libcst approach:** DocstringLocalizer transformer rewrites the `cst.SimpleString` value
via direct string substitution on the docstring's text content.

```python
class DocstringLocalizer(cst.CSTTransformer):
    REPLACEMENTS = {"asincrónico": "sincrónico", "AsyncClient": "Client", ...}

    def leave_SimpleString(self, orig, upd):
        text = upd.evaluated_value
        for src, dst in self.REPLACEMENTS.items():
            text = text.replace(src, dst)
        return upd.with_changes(value=repr(text))
```

## What v1.3 libcst spike inherits unchanged (SPIKE-005 PASS)

These do NOT need re-evaluation at v1.3 (libcst trivially inherits):

- **B8 identity invariant** (SPIKE-005 item 2): the 5-token alias line
  `_raise_for_response = _core.raise_for_response` is preserved verbatim by token
  replacement; libcst's structured rewrite preserves the assignment AST node by default.
  Regression test (Pitfall 4 mitigation) is identical: `mod._raise_for_response is
  aio._raise_for_response is _core.raise_for_response`.
- **`@generated` marker design** (SPIKE-005 item 8): PEP 263 + PEP 236 compliant. libcst
  prepends as a leading `cst.SimpleStatementLine` with `cst.Comment(...)` children.
- **Matriz construct audit** (SPIKE-005 D-SCOPE-02): 109 rows, 0 unresolved. Re-run
  audit.py against current matriz aio.py at v1.3 spike start; if still PASS, no work.
- **Matriz deny-list intactness** (SPIKE-005 001d): adapts to libcst's per-CSTTransformer
  invocation scope. sha256 check is tool-agnostic.

## v1.3 D-RIGOR-02 gate (proposed)

8 items inherited from SPIKE-005 + 2 libcst-specific:

| # | Item | Inherited from | libcst-specific notes |
|---|------|----------------|------------------------|
| 1 | Byte-identical round-trip ámbito | SPIKE-005 | **MUST PASS** without source migration (the unasync gap) |
| 2 | B8 identity preserved | SPIKE-005 | trivially expected (AST node preserved) |
| 3 | `ruff format --check` clean | SPIKE-005 | trivially expected (libcst preserves whitespace) |
| 4 | `ruff check` clean (incl. ASYNC1xx) | SPIKE-005 | **MUST PASS** — ImportNormalizer transformer required |
| 5 | `mypy --strict` clean | SPIKE-005 | inherited |
| 6 | ámbito mocked suite green vs generated | SPIKE-005 | **MUST PASS** — ImportDirectionNormalizer required |
| 7 | `lint-imports` 4 contracts intact | SPIKE-005 | inherited |
| 8 | `@generated` marker × `from __future__` | SPIKE-005 | inherited |
| 9 | CSTTransformer pattern correctness | NEW | pure CSTNode → CSTNode, no side effects, fully testable |
| 10 | matriz audit + deny-list under libcst | NEW | parallel to 001c + 001d, libcst-flavor |

If items 1, 4, 6 PASS at v1.3 → libcst is the right tool, REFAC-06 ships in v1.3.

If items 1, 4, 6 STILL FAIL at v1.3 → codegen single-source may not be the right
architectural pattern for this codebase. Shelve REFAC-06 permanently; accept the
duplicate client.py/aio.py shells as a structural feature.

## Production integration (if v1.3 GO)

Inherited from SPIKE-005 DECISION.md per-package Rule config drafts + Phase 16
integration recommendations, adapted for libcst:

- **Marker syntax:** identical to SPIKE-005 (PEP 263 / PEP 236 compliant).
- **Pre-commit hook:** `head -1 packages/<pkg>/src/<pkg>/client.py | grep -q '^# @generated by libcst'`.
- **`make codegen` target:** invokes `uv run --with libcst python scripts/codegen.py`.
- **CI `lint-codegen` job:** `make codegen-check` → `git diff --exit-code`.
- **`pyproject.toml`:** root `[dependency-groups] dev` adds `libcst >=1.8.0,<2`.

## Linkage

- Pending todo (the spike scope): `.planning/todos/pending/spike-codegen-libcst-v1.3.md`
- SPIKE-005 NO-GO close-out: `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md`
- SPIKE-005 DECISION: `sources/DECISION.md`
- unasync failure mode reference: `references/unasync-failure-mode.md`
- @generated marker design + matriz scope details: `references/codegen-pitfalls.md`
