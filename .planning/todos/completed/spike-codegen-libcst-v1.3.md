---
category: spike
captured_date: 2026-06-14
triggering_decision: SPIKE-005 NO-GO (2026-06-14, sebadlf)
priority: high
target_milestone: v1.3
resolves_phase: 18
related: [REFAC-06]
area: codegen
title: "v1.3 spike — libcst AST-level codegen for sync/async parity"
tags: [spike, codegen, libcst, ast, sync-async, REFAC-06-v1.3]
---

# Pending Todo: Codegen Single-Source Spike — libcst (v1.3)

**Triggered by:** SPIKE-005 NO-GO on 2026-06-14. See
`.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md` for root cause analysis +
what was learned from the unasync 0.6.0 evaluation.

## Scope

Evaluate `libcst >=1.8.0,<2` as the codegen tool for REFAC-06 (single-source sync/async
transport shells × 4 packages). libcst is AST-level: it parses Python source into a
concrete syntax tree (preserving whitespace + comments natively), enables structured
node transforms via `CSTTransformer`, and regenerates code with full fidelity to the
original formatting.

The v1.3 spike answers: **can libcst close the gap where unasync 0.6.0 (token replacement)
returned NO-GO on items 1, 4, 6 of the SPIKE-005 D-RIGOR-01 evidence checklist?**

### Validation target

The validation target is **`packages/ambito-financiero-client/src/ambito_financiero_client/aio.py`
in its CURRENT v1.2-head shape** (i.e., NOT migrated). The v1.3 spike succeeds if libcst
can:

1. Produce a `client.py` byte-identical to v1.1 hand-written `client.py` WITHOUT requiring
   the ~30 LOC of aio.py source migration that unasync needed (see
   `.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/FINDING.md`
   §"Ámbito Rule Config Draft" → "Phase 16 source-migration setup steps" for the migration
   sketch — that's the gap unasync left open).
2. Handle the **import-direction asymmetry** (aio.py imports `_validate_max_retries` from
   client.py; the codegen should detect this and emit the definition into client.py while
   rewriting aio.py's import accordingly).
3. Handle the **docstring asymmetry** (sincrónico ↔ asincrónico labels, docstring example
   updates) via an AST-level docstring transformer that token-replacement could not reach.
4. Handle the **single-line import order asymmetry** (aio.py uses `_transport, _core`
   non-alphabetical; libcst should normalize to canonical order via an `ImportNormalizer`
   transformer or equivalent).

### Inherited evidence (from SPIKE-005)

The v1.3 spike inherits these PASS items unchanged (do not re-do):

- **B8 identity invariant** — same `client._raise_for_response is aio._raise_for_response
  is _core.raise_for_response` test (Pitfall 4 mitigation). libcst's structured rewrite
  should also preserve the alias assignment verbatim — if not, the spike fails fast on
  the same B8 test SPIKE-005 used.
- **`@generated` marker design** (PEP 263 / PEP 236 compliant per 001b/FINDING.md). Marker
  syntax and placement carry forward unchanged — libcst's CSTTransformer can prepend a
  leading comment via `cst.SimpleStatementLine` with `cst.Comment(...)` children.
- **Matriz construct audit (D-SCOPE-02)** — 109 rows, 0 unresolved. The audit is
  source-of-truth-derived and tool-agnostic; libcst inherits it directly.
- **Matriz deny-list intactness** — 4 of 4 deny-listed files byte-intact under fpath_list
  scope. libcst's equivalent is per-file CSTTransformer invocation; the deny-list scope
  guarantee is the same shape.

## Why libcst over unasync at v1.3?

| Capability | unasync 0.6.0 (SPIKE-005) | libcst >=1.8.0,<2 (v1.3 target) |
|------------|----------------------------|-----------------------------------|
| Tokenization model | Token-level replacement | AST-level transform (concrete syntax tree) |
| Source-shape asymmetry handling | Cannot — token replacement matches single tokens | CAN — AST transformer can detect-and-rewrite multi-token patterns (e.g., import direction reversal, docstring localization) |
| Whitespace/comment preservation | Requires post-process via `ruff format` | Native; libcst preserves trivia verbatim |
| `additional_replacements` table size | Bounded (Pitfall 8 warning at >10) | Replaced by transformer rules — more expressive, no count cap |
| Maintenance burden | Per-package replacement dict | Per-package CSTTransformer subclass (more code, but Pythonic + testable) |
| Performance | Fast (single tokenizer pass) | Slower (AST parse + transform + regen) — but codegen is offline, not hot path |
| Ecosystem precedent | httpcore, elasticsearch-py, trio | Instagram (mypy ecosystem), Meta-scale codemods |

The v1.3 spike's value is determining whether the AST-level approach actually closes the
gap, or whether it just shifts the same source-of-truth asymmetry into a different
failure shape. If libcst ALSO requires the ~30 LOC source migration, then the team must
reconsider whether codegen single-source is the right architectural pattern for this
codebase at all — REFAC-06 may be permanently shelved in favor of accepting the duplicate
client.py/aio.py shells.

## Acceptance Criteria for v1.3 libcst Spike

The v1.3 spike's RESEARCH.md / CONTEXT.md should define a `D-RIGOR-02` 8-item gate
adapted for libcst:

1. **Byte-identical round-trip ámbito** — same as SPIKE-005 item 1; v1.3 target: pass
   without source migration.
2. **B8 identity preserved** — same as SPIKE-005 item 2; trivially expected to pass.
3. **`uv run ruff format --check` clean** — same as SPIKE-005 item 3; libcst's whitespace
   preservation should make this trivially PASS.
4. **`uv run ruff check` clean** — same as SPIKE-005 item 4; libcst's CSTTransformer should
   handle the single-line import-order asymmetry that token replacement could not.
5. **`uv run mypy --strict` clean** — same as SPIKE-005 item 5.
6. **Ámbito mocked suite green vs generated** — same as SPIKE-005 item 6; libcst should
   detect-and-rewrite the import-direction asymmetry (`_validate_max_retries` definition
   migration) automatically via AST analysis.
7. **`uv run lint-imports` 4 contracts intact** — same as SPIKE-005 item 7.
8. **`@generated` marker × `from __future__ import annotations` compatibility** — same as
   SPIKE-005 item 8; pre-confirmed PASS in 001b/FINDING.md, but re-verify with libcst's
   marker-insertion mechanism.

Plus:

9. **NEW libcst-specific: CSTTransformer pattern correctness** — verify that the
   transformer subclasses (one per package) are pure functions of `CSTNode → CSTNode`,
   no global state, no side effects.
10. **NEW libcst-specific: matriz Rule equivalent under libcst** — re-run 001c + 001d
    against libcst's deny-list mechanism (`fpath_list` equivalent is per-CSTTransformer
    invocation; sha256-byte-identical pre/post is the gate).

## Out of Scope for v1.3 Spike

- Production codegen integration (CI hook, pre-commit hook, Makefile target) — that's the
  Phase-equivalent if v1.3 returns GO. Spike only produces the binary decision + per-package
  CSTTransformer drafts.
- Re-evaluating unasync — already NO-GO per SPIKE-005. Do not re-run unasync experiments
  inline.
- Driver migration (REFAC-05) — that's already shipped in v1.2 Phase 15.
- Matriz `_token_store.py` / `_refresh_policy.py` / `_refresh.py` / `ws_client.py` — these
  remain in the architectural deny-list. The spike CONFIRMS, does NOT renegotiate.
- libcst evaluation for `_core.py` — already single-source since v1.1 Phase 7. Codegen does
  not apply here.

## References

- SPIKE-005 (NO-GO) — `.planning/spikes/SPIKE-005-codegen-tool-choice/`
  - `NO-GO.md` — root cause analysis + what was learned + v1.3 handoff.
  - `DECISION.md` — operator-signed NO-GO + per-package Rule config drafts (informative;
    libcst's analogue is per-package CSTTransformer).
  - `evidence-checklist.txt` — 8-item D-RIGOR-01 transcripts (libcst inherits items 2, 3,
    5, 7, 8 as expected-pass; v1.3 spike's contribution is closing items 1, 4, 6).
  - `001a/FINDING.md` — Recipe-2 hunk classification + the ~30 LOC source-migration sketch
    (the v1.3 validation target: libcst must avoid this migration).
  - `001b/FINDING.md` — @generated marker design (carried forward unchanged).
  - `001c/FINDING.md` — matriz construct audit (tool-agnostic; inherited).
  - `001d/FINDING.md` — deny-list intactness pattern (adapted to libcst MetadataWrapper).
- `.claude/skills/spike-findings-codegen-market-libs/SKILL.md` — auto-loaded skill carrying
  the NO-GO learnings into the v1.3 spike planning context.
- `.planning/REQUIREMENTS.md` §"Future Requirements (Defer to v1.3+)" — REFAC-06 deferred
  entry.
- `.planning/ROADMAP.md` §Phase 16 — DROPPED (v1.2) entry.
