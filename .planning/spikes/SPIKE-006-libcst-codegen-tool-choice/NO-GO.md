---
spike: 006
status: NO-GO (SIGNED — effective 2026-07-03)
signed: 2026-07-03
signed_by: sebadlf
tool: libcst
prior_spike: SPIKE-005 (unasync NO-GO, 2026-06-14)
related: [REFAC-06]
phase_19_status: DROPPED
refac_06_status: PERMANENTLY_SHELVED
tags: [spike, codegen, libcst, NO-GO, REFAC-06, v1.3, content-absence]
---

# SPIKE-006 — NO-GO Decision (libcst, v1.3)

> **EFFECTIVE CLOSE-OUT — the operator signed `DECISION.md` on 2026-07-03 (`sebadlf`).** The verdict
> below is the mechanically-computed strict D-04 aggregate, now ratified by operator signature (D-06 /
> T-18-07). Project-state governance edits (REQUIREMENTS/ROADMAP/18-03-SUMMARY) are applied in the
> post-signoff continuation of Plan 18-03.

**Tool evaluated:** `libcst >=1.8.0,<2` (Meta/Instagram AST-level CST codemod), ephemeral (D-05).
**Bar:** STRICT un-migrated D-02 — no `aio.py` source edits; consumed as-is.
**Timebox:** WITHIN-CAP (D-07 24h cap; ~28m since README start, cumulative Plans 01+02+03 far under
cap) — NOT a timebox-triggered NO-GO.

## Root Cause Analysis

The strict D-RIGOR-02 contract (D-04) requires **all 10 evidence items PASS** before GO. The
end-to-end aggregation captured **3 of 10 FAIL**:

| # | Item | GO-det | Strict Verdict | Root Cause |
|---|------|:------:|:--------------:|-----------|
| 1 | Byte-identical round-trip ámbito | ✅ | **FAIL** (13 hunks / 383 lines) | Content ABSENT from `aio.py`: `_validate_max_retries` def (defined only in `client.py:41-62`, imported at `aio.py:34`) + `load_dotenv()` bootstrap (absent per D-19) + independently hand-authored docstring prose. A pure single-file transform cannot synthesize source-absent content. |
| 3 | `uv run ruff format --check` clean | | **FAIL** | Length-changing `AmbitoFinancieroAsyncClient`→`...Client` swap shortened the `__reduce__`/`__deepcopy__` TypeError strings while libcst preserved `aio.py`'s original multi-line wrapping (the lossless-round-trip premise holds for untouched trivia but breaks on length change). |
| 6 | Ámbito mocked suite green vs generated | ✅ | **FAIL** | Because `_validate_max_retries` is absent from `aio.py`, `ImportDirectionNormalizer` honestly RETAINED the `aio.py:34` self-import → generated `client.py` imports the name FROM ITSELF → EXACT SPIKE-005 `ImportError: cannot import name '_validate_max_retries' from partially initialized module … circular import`. |

**All 3 FAILs trace to the SAME root cause SPIKE-005 found:** `aio.py`'s source shape (hand-written
sync-first in v1.1 Phase 7) is not codegen-friendly, and the decisive content (`_validate_max_retries`
def, `load_dotenv` bootstrap) lives in `client.py`, not `aio.py`. Two independent tools — token-level
`unasync` (SPIKE-005) and AST-level `libcst` (SPIKE-006) — now reach the SAME NO-GO for the SAME root
cause under the un-migrated D-02 bar.

**Critical distinction from SPIKE-005:** libcst is NOT a regression — it is a *partial capability gain*
that still cannot cross the content-absence boundary:

- **Item 4 (`ruff check`, I001 + ASYNC1xx) — which unasync FAILED — now PASSES under libcst.**
  `ImportNormalizer` closes the single-line import-order; `AsyncToSync` fully strips async (zero
  residual ASYNC1xx). This is a genuine AST-level advantage over token replacement.
- Items 5 (`mypy --strict`), 7 (`lint-imports`), 9 (transformer purity) also PASS.
- The remaining gap is exclusively *content that is not in the single source file* — a boundary no
  pure single-file codemod (token- or AST-level) can cross without either (a) editing `aio.py`
  (forbidden by D-03) or (b) reading `client.py` as a donor (defeats single-sourcing, D-02). Both
  escape hatches were left closed; the residual divergence IS the honest answer.

### Concrete failure transcripts

**Item 1 (byte-identical):**
```
$ diff -u packages/ambito-financiero-client/src/ambito_financiero_client/client.py \
          .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py
exit code: 1
hunk count: 13   (383 lines; more than SPIKE-005's 10/295, as RESEARCH predicted)
```
Full transcript: `001a-ambito-round-trip/diff_vs_current_client.txt` (baseline REGENERATED vs
current v1.2-head `client.py` — Pitfall 1, SPIKE-005's stale diff NOT reused).

**Item 6 (ámbito pytest sandbox):**
```
ImportError while loading conftest '/tmp/spike-006-ambito-.../tests/conftest.py'.
src/ambito_financiero_client/client.py: in <module>
    from ambito_financiero_client.client import _validate_max_retries
E   ImportError: cannot import name '_validate_max_retries' from partially initialized module
    'ambito_financiero_client.client' (most likely due to a circular import)
```

## What Was Learned (Wave-1 PASS evidence, inherited + confirmed)

The spike was NOT a waste — 7 of 10 items PASS, including all inherited Wave-1 evidence and a NEW
libcst capability gain:

- **Item 4 capability gain:** libcst passes `ruff check` (I001 + ASYNC1xx) where unasync failed —
  documented for any future codegen revisit.
- **B8 identity (item 2):** PASS — `_raise_for_response = _core.raise_for_response` emitted verbatim;
  `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` (Pitfall 4 avoided).
- **`@generated` marker × `from __future__` (item 8):** STRICT PASS — marker inserted via libcst
  `Module.header` (never `str.replace`); all 4 verification commands exit 0, marker-neutral vs baseline.
- **Matriz construct audit (item 10a):** PASS — 110 rows (aio.py grew 852→959 LOC since SPIKE-005),
  0 unresolved; verbatim SPIKE-005 `audit.py` (pure stdlib `ast`). D-SCOPE-02 merge gate satisfied.
- **Matriz deny-list intactness (item 10b):** PASS — 4 deny-listed files (`_token_store.py`,
  `_refresh_policy.py`, `_refresh.py`, `ws_client.py`) sha256-byte-identical pre/post; `aio.py`
  transformed. Per-module libcst scope = the `fpath_list` equivalent; deny-list (D-09) CONFIRMED out
  of codegen scope, not renegotiated.
- **Transformer purity (item 9):** PASS at the class level — five pure `CSTNode → CSTNode` subclasses;
  cross-module orchestration isolated in the impure driver.
- **Item 5 (`mypy --strict`), item 7 (`lint-imports`):** PASS.

## Impact on v1.3 Milestone

- **REFAC-06** (single-source sync/async transport shells × 4 packages) — **PERMANENTLY SHELVED.**
  Two dedicated spikes (unasync + libcst) now independently return NO-GO for the same content-absence
  root cause under the un-migrated bar. The duplicate `client.py`/`aio.py` shells are **accepted as a
  structural feature** of the codebase (the known dual-surface duplication documented in CLAUDE.md).
- **Phase 19 (Codegen Single-Source rollout, GO-branch)** — **DROPPED.** It was conditional on this
  spike returning GO; it does not run.
- **The `001a/transformers/` classes are NOT promoted** as Phase 19 drafts. They remain in-tree as
  canary-proven evidence that libcst closes the mechanical asymmetries (items 4/5/7/9) but cannot
  cross the content-absence boundary (items 1/6) under D-03.
- **Zero production footprint:** `git diff --exit-code packages/` and `git diff --exit-code uv.lock`
  both CLEAN across the entire spike (libcst ephemeral, D-05; canary transforms on `/tmp` sandbox
  copies; deny-list files read-only sha256 targets). No `.env` read.

(The actual REQUIREMENTS.md + ROADMAP.md + CLAUDE.md + `spike-findings-codegen-market-libs` Skill +
18-SUMMARY.md edits land in the post-signoff continuation, which depends on this NO-GO.md and the
signed DECISION.md.)

## Why This Is a Valid Deliverable (D-08)

Per D-08 and 18-RESEARCH.md §Primary Recommendation, a second NO-GO for the same source-shape root
cause was the honest likely outcome under the STRICT un-migrated D-02 bar — an explicitly valid,
guaranteed milestone deliverable. The spike surfaced data (libcst's item-4 gain + the exact
content-absence boundary) without softening the gate to manufacture a GO. The architectural question
is now settled with two independent tool evaluations: single-source codegen of the transport shells is
not viable without a source migration the operator has chosen not to pursue.

## Linkage

- `DECISION.md` — operator-signed GO/NO-GO (frontmatter map + Operator Signoff + Q2/Q3 ratification).
- `evidence-checklist.txt` — 10-item end-to-end transcript with PASS/FAIL + aggregate.
- `001a-ambito-round-trip/FINDING.md` — items 1/2/3/4/5/6/7/9; Q1 content-absence, Q2 purity, Q3 docstring.
- `001a-ambito-round-trip/diff_vs_current_client.txt` — item-1 13-hunk diff transcript.
- `001b-…/FINDING.md` — item 8 marker STRICT PASS.
- `001c-matriz-construct-audit/FINDING.md` — item 10a 110 rows / 0 unresolved.
- `001d-matriz-deny-list-config/FINDING.md` — item 10b 4/4 sha256 intact.
- `.planning/spikes/SPIKE-005-codegen-tool-choice/` — prior unasync NO-GO (2026-06-14) the same root
  cause parallels.
- `.claude/skills/spike-findings-codegen-market-libs/SKILL.md` — auto-loaded skill to be updated with
  the libcst verdict in the post-signoff continuation.
