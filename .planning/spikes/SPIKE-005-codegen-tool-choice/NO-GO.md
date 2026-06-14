---
spike: 005
status: NO-GO
signed: 2026-06-14
signed_by: sebadlf
defer_to_milestone: v1.3
defer_to_pending_todo: .planning/todos/pending/spike-codegen-libcst-v1.3.md
related: [REFAC-06]
tags: [spike, codegen, NO-GO, libcst-handoff, v1.3]
---

# SPIKE-005 — NO-GO Decision

**Decided:** 2026-06-14
**Signed off by:** sebadlf
**Time spent:** ~19m cumulative wall-clock (Plan 01 ~10m + Plan 02 ~9m + Plan 03 ~6m); D-SCOPE-03 cap: 24h — well under cap, NOT a timebox-triggered NO-GO.

## Root Cause Analysis

The strict D-RIGOR-01 contract requires **all 8 evidence items PASS** before GO. The
re-run captured 3 of 8 FAIL:

| # | Item | Strict Verdict | Recipe-2 Class | Root Cause |
|---|------|----------------|----------------|-----------|
| 1 | Byte-identical round-trip ámbito | **FAIL** | 7 class-4 (inherent-asymmetry) + 2 class-1 (cosmetic) + 1 semantic-consistent-extension; 0 class-3 NO-GO triggers | `aio.py` was authored sync-first in v1.1 Phase 7. Codegen direction is async-first. Source-shape asymmetry produces 10 diff hunks. |
| 4 | `uv run ruff check` clean (incl. ASYNC1xx) | **FAIL** | 1 hunk H3 (class 1 — cosmetic) — single-line import order `_transport, _core` (non-alphabetical, inherited from aio.py) | Same source-shape asymmetry: aio.py import order is non-canonical relative to alphabetical. ruff format does NOT converge on single-line import order. Zero ASYNC1xx false-positives (unasync tokenizer is clean on the ruleset). |
| 6 | Ámbito mocked suite green vs generated | **FAIL** | Recipe-2 class 4 — H4/H5 inherent-asymmetry | Generated `client.py` tries to import `_validate_max_retries` from itself → circular import at collection. Root cause: aio.py imports `_validate_max_retries` FROM client.py; codegen token-replaces the import line verbatim into a self-import. |

**All 3 FAILs trace to a SINGLE root cause:** `aio.py` source-of-truth shape is not yet
**codegen-friendly** — it was hand-written sync-first in v1.1 Phase 7 (sync was the
primary, async mirrored), but unasync 0.6.0 codegen is async-first (aio.py is the canonical
source, client.py is generated from it). The strict NO-GO is the operator's deliberate
choice to honor the gate rather than soft-relax.

**Critically — zero Recipe-2 class-3 hunks** (the only class that signals an unfixable
unasync failure mode). All hunks classify as class 1 (cosmetic), class 2/4 (inherent
asymmetry from source-shape), or semantic-consistent-extension. The tool itself works;
the gap is source-shape compatibility.

### Concrete failure transcripts

**Item 1 (byte-identical):**
```
$ diff -u packages/ambito-financiero-client/src/ambito_financiero_client/client.py \
          .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py
exit code: 1
hunk count: 10
```
Full transcript: `001a-ambito-round-trip/diff_vs_v1.1_client.txt`.

**Item 4 (ruff check):**
```
$ uv run ruff check .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py
I001 [*] Import block is un-sorted or un-formatted
  --> .../client_generated.py:23:1
   |
23 | / from __future__ import annotations
...
32 | | from ambito_financiero_client import _transport, _core
33 | | from ambito_financiero_client._state import _ClientState
34 | | from ambito_financiero_client.client import _validate_max_retries
   | |_________________________________________________________________^
Found 1 error.
exit code: 1
```
Single-line import order inherited from aio.py source order.

**Item 6 (ámbito pytest sandbox):**
```
ImportError while loading conftest '/private/tmp/.../tests/conftest.py'.
src/ambito_financiero_client/client.py:34: in <module>
    from ambito_financiero_client.client import _validate_max_retries
E   ImportError: cannot import name '_validate_max_retries' from partially initialized module
    'ambito_financiero_client.client' (most likely due to a circular import)
exit code: 2 (collection error before any test ran)
```

## What Was Learned (Wave 2-4 PASS evidence)

The spike was NOT a waste — it produced 5 of 8 PASS items and 3 unconditional Wave 2-4
PASSes that the v1.3 libcst spike inherits:

- **B8 identity (item 2):** PASS — unasync 0.6.0 tokenizer preserves the alias line
  `_raise_for_response = _core.raise_for_response` verbatim. All three identities resolve
  to the same Python object id. Pitfall 4 (B8 thunk-wrapper failure mode) does not
  surface with token-replacement codegen.
- **`@generated` marker × `from __future__ import annotations` (item 8):** PASS —
  marker is grammar-neutral per PEP 263/PEP 236; ast.parse + ruff format --check + ruff
  check + mypy --strict all show IDENTICAL per-command exit codes between baseline (no
  marker) and marked. The 3-line marker block shifts line numbers +3 but adds zero
  diagnostics. v1.3 libcst spike inherits this marker design verbatim.
- **Matriz construct audit (D-SCOPE-02 merge gate):** PASS — 109 rows enumerated, 0
  REVIEW/TBD/DENY-LIST-VIOLATION. The audit classifier resolved every row
  deterministically. Critically: matriz `aio.py` has ZERO bare `asyncio.<attr>`
  references in code body — all are inside docstrings (lines 42, 235, 267); the async
  primitives are entirely encapsulated inside `_token_store.py` (deny-listed). This is a
  stronger guarantee than fpath_list scope alone. v1.3 inherits the audit script + result.
- **Matriz deny-list intactness (001d):** PASS — 4 of 4 deny-listed files
  (`_token_store.py`, `_refresh_policy.py`, `_refresh.py`, `ws_client.py`)
  sha256-byte-identical pre/post simulated codegen; `aio.py` itself transformed. The
  unasync `fpath_list` scope mechanism is structurally sufficient. v1.3 inherits this
  scope pattern for libcst's equivalent (`libcst.MetadataWrapper` per-file scope).
- **B8 identity, ruff format --check, mypy --strict, lint-imports (items 2, 3, 5, 7):**
  all PASS in canonical D-RIGOR-01 invocation. unasync 0.6.0 is structurally sound for
  this codebase; the failure modes are at source-shape level (items 1, 4, 6), not at
  tool level.

## Why Not Extend Phase 12?

Per D-NOGO-01 (CONTEXT.md locked decision): libcst exploration requires AST-level
reasoning (not token-replacement). It needs its own dedicated spike. Adding it inline to
Phase 12 violates:

1. **D-SCOPE-03 1-day timebox** — evaluating 2 tools serially would exceed cap (the
   cumulative ~19m for unasync evaluation is well under cap, but adding libcst
   evaluation inline is scope creep).
2. **v1.2 milestone scope** — v1.2 has 5 phases active + 1 conditional. Adding libcst
   spike inline expands milestone scope.
3. **AST-level vs token-level** — libcst is structurally different (parses to concrete
   syntax tree, transforms nodes, regenerates code). It cannot be evaluated with the
   same 8-item D-RIGOR-01 gate because the failure modes differ (e.g., libcst preserves
   whitespace + comments natively, eliminating items 1's "byte-identical" class-1
   cosmetic failures; but libcst introduces new failure modes around CSTTransformer
   pattern correctness that the 8-item gate does not cover).

The right answer is a fresh spike (SPIKE-006 or similar) in v1.3 with its own
RESEARCH/CONTEXT and a tailored D-RIGOR-02-equivalent gate.

## What's Deferred to v1.3

- **libcst AST-level codemod evaluation** for unasync alternatives — captured in
  `.planning/todos/pending/spike-codegen-libcst-v1.3.md`.
- **REFAC-06 entire scope** (single-source sync/async transport shells × 4 packages) —
  remains an open requirement, moved from v1.2 active to "Future Requirements (Defer to
  v1.3+)" in REQUIREMENTS.md.

The v1.3 spike should pre-load with the ~30 LOC ámbito source-migration sketch from
`001a-ambito-round-trip/FINDING.md` (§"Ámbito Rule Config Draft" → "Phase 16
source-migration setup steps"). That sketch is the validation target — libcst should
either (a) produce byte-identical output without requiring source migration (its AST-level
nature makes it well-suited to handle source-shape asymmetries that token-replacement
cannot), or (b) reproduce unasync's source-migration constraint, in which case the v1.3
gate is still NO-GO and the team must reconsider whether codegen single-source is the
right architectural pattern for this codebase at all.

## Impact on v1.2 Roadmap

- **Phase 16 (Codegen Single-Source)** — DROPPED from v1.2 schedule.
- **Phase 17 (LIVE-03 Final Live Re-verification × 4)** — UNBLOCKED; runs immediately
  after Phases 14 + 15. Previously gated behind Phase 16 in the conditional schedule.
- **REFAC-06** moved from v1.2 active requirements → v1.2 "Future Requirements (Defer to
  v1.3+)" in REQUIREMENTS.md. Traceability table: Phase TBD (v1.3); Status: Deferred
  (Phase 12 NO-GO 2026-06-14).
- **v1.2 milestone scope** — 4 of 5 requirements (REFAC-05, SEC-01, ERG-01, LIVE-03) ship
  as planned. Milestone audit will note REFAC-06 deferred per Phase 12 NO-GO.

(The actual REQUIREMENTS.md + ROADMAP.md + CLAUDE.md + 12-SUMMARY.md edits land in
Task 12-03-04b, which depends on this NO-GO.md being written first.)

## Linkage

- `evidence-checklist.txt` — 8-item re-run transcript with PASS/FAIL per item.
- `DECISION.md` — operator-signed NO-GO (frontmatter + Operator Signoff section).
- `001a-ambito-round-trip/FINDING.md` — Recipe-2 hunk classification + Phase 16
  source-migration setup steps (v1.3 libcst spike validation target).
- `001b-ambito-marker-future-compat/FINDING.md` — marker × future-import PASS;
  v1.3 inherits the marker design.
- `001c-matriz-construct-audit/FINDING.md` — matriz 852 LOC audit, 109 rows
  0 unresolved; v1.3 inherits the audit script + result.
- `001d-matriz-deny-list-config/FINDING.md` — deny-list intactness PASS via fpath_list
  scope; v1.3 adapts to libcst MetadataWrapper per-file scope.
- `.planning/todos/pending/spike-codegen-libcst-v1.3.md` — v1.3 libcst spike scope.
- `.claude/skills/spike-findings-codegen-market-libs/SKILL.md` — auto-loaded skill that
  carries the NO-GO learnings into the v1.3 spike planning context.
