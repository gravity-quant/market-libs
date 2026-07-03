---
spike: 006
name: libcst-codegen-tool-choice
type: standard
validates: "Given the CURRENT v1.2-head hand-written packages/ambito-financiero-client/.../client.py + matriz aio.py 959 LOC, when libcst CSTTransformers run against aio.py (async→sync, import-direction normalize, docstring localize, single-line import-order, suppressors) WITHOUT any source migration, then byte-identical round-trip + B8 identity preserved + ruff/mypy clean + mocked suite green + matriz construct audit zero unresolved + deny-list sha256 intact + marker grammar-neutral"
verdict: NO-GO
signoff_date: 2026-07-03
signoff_by: sebadlf
related: [001a, 001b, 001c, 001d]
tags: [codegen, libcst, ambito, matriz, B8-identity, phase-18, v1.3]
created: 2026-07-02
---

# Spike 006: libcst Codegen Tool Choice (v1.3 REFAC-06 revisit)

## What This Validates

**Given** the CURRENT v1.2-head hand-written
`packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (sync transport
shell) and `aio.py` (async transport shell), PLUS the CURRENT
`packages/matriz-client/src/matriz_client/aio.py` (959 LOC — grew from 852 since SPIKE-005;
the worst case for the codegen tool). **No source migration is applied** (D-02 STRICT bar):
`aio.py` is consumed as-is.

**When** `libcst >=1.8.0,<2` (Meta/Instagram's lossless CST codemod engine) parses each
`aio.py` and applies a suite of `CSTTransformer` passes — `AsyncToSync`, `ImportNormalizer`,
`DocstringLocalizer`, `ImportDirectionNormalizer`, and `Suppressors` (D-03) — re-emitting via
`Module.code` with **no `ruff format` post-pass** (libcst's lossless round-trip is the v1.3
premise), AND for matriz the 4-file deny-list is honored by **per-module transform scope**
(only `aio.py` is ever parsed), AND the `@generated` marker is inserted via `Module.header`.

**Then** the 10-item D-RIGOR-02 gate is evaluated (see `evidence-checklist.txt`):

1. The generated `client.py` is byte-identical to the current hand-written `client.py` (item 1, GO-det.).
2. B8 identity survives: `client._raise_for_response is aio._raise_for_response is _core.raise_for_response` (item 2).
3. `uv run ruff format --check` clean (item 3).
4. `uv run ruff check` clean incl. single-line import-order I001 + ASYNC1xx (item 4, GO-det.).
5. `uv run mypy --strict` clean (item 5).
6. Ámbito mocked suite green vs generated — no circular self-import (item 6, GO-det.).
7. `uv run lint-imports` 4 contracts intact (item 7).
8. `@generated` marker × `from __future__ import annotations` grammar-neutral (item 8).
9. CSTTransformer subclasses pure `CSTNode → CSTNode`, no global state / side-effects (item 9, new).
10. matriz construct audit 0 unresolved rows (item 10a) + 4 deny-list files sha256-byte-identical pre/post, `aio.py` transformed (item 10b).

## Research

See `.planning/phases/18-libcst-codegen-tool-choice-spike-spike-006/18-RESEARCH.md` for the full
architecture patterns (1–5), the Phase Requirements → Test Map, and Common Pitfalls. Key inputs:

| Question | Resolution |
|----------|------------|
| Tool | `libcst >=1.8.0,<2` (latest **1.8.6**, published 2025-11-03) — Meta/Instagram LibCST |
| Install | **Ephemeral only** via `uv run --with 'libcst>=1.8.0,<2' python <experiment>.py` (D-05 — NOT added to `[dependency-groups] dev` during the spike) |
| Legitimacy gate | libcst legitimacy `checkpoint:human-verify` cleared by operator (D-05): PyPI provenance + github.com/Instagram/LibCST confirmed; SUS verdict assessed as metadata-gap false positive |
| Canary | Ámbito (simplest — no auth, no token refresh, no envelope) |
| Worst case | Matriz aio.py 959 LOC |
| Source-migration bar | **STRICT (D-02)** — no aio.py source edits; consume as-is |
| Timebox | 1-day hard cap — overflow triggers AUTO-NO-GO |
| Decision binary | GO (v1.3 REFAC-06 proceeds with per-package CSTTransformer configs) / NO-GO (REFAC-06 shelved or re-scoped; D-08) |

## How to Run

```bash
cd /Users/admin/development/market-libs

# libcst legitimacy gate (D-05) — cleared by operator before any ephemeral install.

# 001a — canary round-trip (Plan 02)
uv run --with 'libcst>=1.8.0,<2' python .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/experiment.py

# 001b — @generated marker × future-compat (Plan 01, item 8)
uv run --with 'libcst>=1.8.0,<2' python .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001b-ambito-marker-future-compat/experiment.py

# 001c — matriz construct audit (Plan 01, item 10a) — pure stdlib ast, NO libcst
uv run python .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001c-matriz-construct-audit/audit.py

# 001d — matriz deny-list sha256 intactness (Plan 01, item 10b)
uv run --with 'libcst>=1.8.0,<2' python .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001d-matriz-deny-list-config/experiment.py

# evidence checklist + DECISION.md (Plan 03)
```

## What to Expect

Each sub-experiment emits a `FINDING.md` with a `**Verdict:**` line (PASS / FAIL). The aggregate
verdict is computed in Plan 03 by re-running the 10-item D-RIGOR-02 evidence items end-to-end into
`evidence-checklist.txt`, then operator-signed in `DECISION.md`.

- **GO** iff 10/10 items PASS AND matriz audit unresolved rows == 0 AND timebox status == `WITHIN-CAP`.
- **NO-GO** if ANY of: any item FAILs, matriz unresolved rows > 0, timebox `OVER-CAP`.

Per 18-RESEARCH.md §Primary Recommendation, the honest likely outcome under the STRICT
un-migrated D-02 bar is a **second NO-GO for the same source-shape root cause** as SPIKE-005 —
which is an explicitly valid, guaranteed milestone deliverable (D-08). The spike does NOT soften
the gate to manufacture a GO.

## Sub-Experiments

| # | Name | Type | Plan | What it proves |
|---|------|------|------|----------------|
| 001a | ambito-round-trip | comparison | 02 | Byte-identical round-trip vs CURRENT client.py + B8 identity + item 9 purity (the canary) |
| 001b | ambito-marker-future-compat | standard | 01 | `@generated` marker via `Module.header` compatible with `from __future__ import annotations` (ruff/mypy/ast.parse) |
| 001c | matriz-construct-audit | enumeration | 01 | Zero TBD / REVIEW / DENY-LIST-VIOLATION rows in matriz aio.py 959 LOC walk (item 10a) |
| 001d | matriz-deny-list-config | standard | 01 | Per-module libcst transform scope; 4 deny-listed files sha256-byte-identical, aio.py transformed (item 10b) |

## Forward References

- **v1.3 REFAC-06** (codegen × transport shells): CONDITIONAL on this spike returning GO. If NO-GO, REFAC-06 is shelved or re-scoped per D-08.
- **CLAUDE.md auto-loaded Skill** `spike-findings-codegen-market-libs` (already present from SPIKE-005) to be updated by Plan 03 close-out with the libcst verdict.

## Inheritance From SPIKE-005 (NO-GO, 2026-06-14)

~60% of the D-RIGOR-02 harness is inherited verbatim or near-verbatim (per CONTEXT D-01):

- **item 8** (`001b`): marker text proven neutral in SPIKE-005; re-inserted via libcst `Module.header`.
- **item 10a** (`001c`): `audit.py` copied **verbatim** (pure stdlib `ast`), `SOURCE` re-points at current matriz `aio.py` (959 LOC) via `REPO_ROOT`. Gate is "0 unresolved," NOT a fixed row count (Pitfall 2).
- **item 10b** (`001d`): `shutil.copytree` → sha256 harness adapted; `unasync.unasync_files` dropped for a per-module `cst.parse_module(...).visit(...).code` transform of the sandbox `aio.py` only.

The matriz 4-file deny-list (`_token_store.py`, `_refresh_policy.py`, `_refresh.py`, `ws_client.py`)
is CONFIRMED out of codegen scope (D-09) — this spike does not renegotiate it.
