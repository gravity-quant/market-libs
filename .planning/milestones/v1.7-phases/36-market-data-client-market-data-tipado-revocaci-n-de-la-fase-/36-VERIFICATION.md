---
phase: 36-market-data-client-market-data-tipado-revocacion-de-la-fase-33
verified: 2026-08-29T13:57:02Z
status: passed
score: 5/5 must-haves verified (ROADMAP SC-1..SC-5), 2/2 requirements satisfied (NOBJ-MD-01, NOBJ-MD-02)
behavior_unverified: 0
overrides_applied: 0
---

# Phase 36: `market-data-client` — `market_data` tipado + revocación de la Fase 33 — Verification Report

**Phase Goal:** El consumidor de `market-data-client` escribe `snapshot.market_data.last.price` y
esa expresión compila bajo mypy strict y nunca lanza — con el payload real, con un `market_data`
ausente, con `null` y con la fila no-data.

**Verified:** 2026-08-29T13:57:02Z
**Status:** passed
**Re-verification:** No — initial verification

This verification does not trust SUMMARY.md claims. Every check below was re-run independently
against the current working tree (`uv run pytest`, `uv run mypy`, `uv run ruff`, the three
cross-cutting `tools/check_*.py` gates, blob-hash pins, and direct reads of `models.py`,
`main_market_data.py`, `.github/workflows/ci.yml` and the committed live-capture baselines).

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the authoritative contract)

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|---|---|---|
| 1 | SC-1: `snapshot.market_data.last.price` / `.bids[0].price` / `.offers` / `.settlement` / `.close` / `.open_interest` pass `mypy --strict` and never raise against the four matrix payloads (wire real, `market_data` absent, `market_data: null`, `market_data: {}`) on both `client.py` and `aio.py` | ✓ VERIFIED | `uv run mypy packages/market-data-client/src packages/market-data-client/tests` → `Success: no issues found in 49 source files` (re-run live). `packages/market-data-client/tests/test_market_data_chain.py` — 38 tests, all pass (re-run live), including `strict_decode=True` arms on both surfaces (`grep -c 'strict_decode=True'` in the module ≥ 2, parametrized × sync/async/strict-sync/strict-async). |
| 2 | SC-2: `MarketDataEntries` (`BI`/`OF: list[BookLevel]`, `LA`/`SE`/`CL`/`OI: EntryValue`, `OP`/`HI`/`LO`/`TV: float \| None`), `BookLevel{price,size}`, `EntryValue{price,size,date}` exist as a **local copy** of the matriz pattern with read-only alias properties; `MarketDataSnapshot.market_data: MarketDataEntries` admits no `None` | ✓ VERIFIED | Read `packages/market-data-client/src/market_data_client/models.py:272-484` directly: three `@dataclass(frozen=True, slots=True)` classes subclassing the local `SafeModel`, six `@property` aliases (`bids`/`offers`/`last`/`settlement`/`close`/`open_interest`), `MarketDataSnapshot.market_data: MarketDataEntries` (no `\| None`). Structural check re-run live: `f & a == set()` and `f == {BI,CL,HI,LA,LO,OF,OI,OP,SE,TV}` — alias/field disjointness confirmed. Barrel re-export confirmed: `grep -n 'BookLevel\|EntryValue\|MarketDataEntries' __init__.py` shows import + `__all__` entries. |
| 3 | SC-3: Phase-33 widening revoked only where it breaks the chain — `entries` (both `MarketDataSnapshot` and `LatestRequest`) back to `list[str]` default `[]`; `staleness_seconds` / `note` stay `\| None`; revocation recorded in the docstring against the 33-07 checkpoint | ✓ VERIFIED | `models.py:447-475` — `**REVOKED IN PART since Phase 36**` block names checkpoint `33-07 Task 1 (fix-shape-now)` and the source plan, additively beneath the kept Phase-33 `BREAKING` block. `entries: list[str]` (no default, required), `staleness_seconds: float \| None`, `note: str \| None = None` confirmed at `models.py:477-484`. `LatestRequest.entries: list[str] = field(default_factory=list)` confirmed at `:547`, guard is `if self.entries:` (truthiness, not `is not None`). |
| 4 | SC-4: no-data row of `/marketdata/latest` keeps full expressive power without `None` — `bool(snapshot.market_data) is False`, `note` populated; `test_snapshot_no_data_row.py` migrated, not deleted | ✓ VERIFIED | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -v` → 8 passed (re-run live), same test count the phase started with (SC-4's "migrado en vez de eliminado"). `test_no_data_row_keeps_its_nulls` asserts `bool(row.market_data) is False` and `note` populated. Fixture `_NO_DATA_ROW` verified byte-for-byte against the committed baseline `.planning/verification/schemas/market-data-client/get-latest.json` (both read directly — identical key set and null pattern). |
| 5 | SC-5: `_mapping_value` / `_apply_mapping_policy` and their precondition test disappear from `market-data-client` without moving the `_decode.py` digest; `main_market_data.py` consumes by deep-chaining at its real probe sites | ✓ VERIFIED | `uv run python tools/check_decode_intactness.py` → digest `a1f00c824348164c == CANONICAL_DIGEST` (re-run live, unchanged). `hasattr(models, '_mapping_value')` etc. all `False` (grep confirms zero occurrences). `main_market_data.py` — `grep -c 'market_data\.\(last\|bids\|offers\|settlement\|close\|open_interest\)'` → 30 dereferences across the four probes, inside their `try` bodies (including the `batch` collection, WR-06 fix). `verification/test_main_market_data_deep_chain.py` (4 structural tests) passes and — critically — **is now wired into CI** (`.github/workflows/ci.yml:81-82`, `lint` job), closing WR-01 which found the original lock inert. |

**Score:** 5/5 ROADMAP Success Criteria verified — no overrides used.

### Requirements Coverage (NOBJ-MD-01, NOBJ-MD-02)

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| NOBJ-MD-01 | 36-02, 36-03 | `snapshot.market_data.last.price` compiles under mypy strict and never raises with any real payload or `None`; `market_data` moves from `dict[str, Any] \| None` to typed `MarketDataEntries` with alias properties | ✓ SATISFIED | Same evidence as SC-1/SC-2 above, re-verified live. |
| NOBJ-MD-02 | 36-01, 36-02, 36-03 | `MarketDataSnapshot.entries` reverts to `list[str]` default `[]`; `LatestRequest.entries` aligned; no-data row exposes falsy `market_data` + populated `note`; `_mapping_value`/`_apply_mapping_policy` and precondition tests removed | ✓ SATISFIED | Same evidence as SC-3/SC-4/SC-5 above, re-verified live. |

Both requirement IDs are declared in the frontmatter of at least one plan (`36-01`, `36-02`, `36-03`) and both are marked `Complete` in `REQUIREMENTS.md`'s traceability table — consistent with the codebase evidence above. **No orphaned requirements**: `REQUIREMENTS.md` maps only NOBJ-MD-01 and NOBJ-MD-02 to Phase 36, and both are claimed by the plans.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `packages/market-data-client/src/market_data_client/models.py` | `BookLevel`, `EntryValue`, `MarketDataEntries` + 6 aliases, revoked `MarketDataSnapshot` annotations, mapping machinery gone | ✓ VERIFIED | Read directly; all elements present; `grep -c '_mapping_value\|_apply_mapping_policy\|_is_mapping\|_strip_optional'` → 0 in `models.py` (only 3 have any prose mention, none are call sites). |
| `packages/market-data-client/src/market_data_client/__init__.py` | Barrel re-export of the three new names | ✓ VERIFIED | Present in import block and `__all__`, alphabetical. |
| `packages/market-data-client/tests/test_market_data_chain.py` | SC-1 4×2 matrix + 8 edge cases | ✓ VERIFIED | 38 tests, all pass live (includes the CR-02 fix: `_MEASURED_NO_DATA_ROW` pinned key-for-key against the committed baseline). |
| `packages/market-data-client/tests/test_snapshot_no_data_row.py` | Migrated to truthiness semantics, not deleted | ✓ VERIFIED | 8 tests, all pass live; fixture matches baseline verbatim after the CR-02 fix. |
| `verification/test_main_market_data_deep_chain.py` | AST lock — 4 probes dereference the chain inside their `try` body | ✓ VERIFIED and WIRED into CI | 4 tests pass live; `ci.yml` `lint` job runs it explicitly (WR-01 fix). |
| `verification/safemodel_diff.py` + `verification/test_safemodel_diff_null_object_links.py` | Differ no longer fabricates `model-only` findings for non-optional Null Object links | ✓ VERIFIED | New module (CR-01 fix) present, 43-test aggregate run (driver locks + differ regression) passes live. |
| `.github/workflows/ci.yml` | Deep-chain lock + differ regression wired into a job that actually runs | ✓ VERIFIED | `lint` job, explicit file list (not `pytest verification/`, which stays pre-existing-red per `deferred-items.md`). |
| `packages/market-data-client/README.md` | `## Unreleased — BREAKING` migration table (WR-04 fix, self-describing artifact ahead of Phase 40's bump) | ✓ VERIFIED | `grep` confirms the section and the `market_data["LA"]["price"]` → `market_data.last.price` migration row. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `models.py::MarketDataSnapshot.from_api` | `_decode.py::walk_model` | nested-model branch owns `market_data` | ✓ WIRED | `_decode.py` untouched (blob hash pinned, unchanged); `models.py` `SafeModel.from_api`/`empty` are form A (bare walk). |
| `main_market_data.py` (4 probes) | `market_data_client.models` aliases | direct attribute dereference inside `try` | ✓ WIRED | 30 dereferences confirmed by grep, inside `try` bodies per the AST lock (re-run live, passing). |
| `__init__.py` barrel | `models.py` | re-export | ✓ WIRED | Confirmed importable: `from market_data_client import MarketDataEntries, BookLevel, EntryValue` succeeds live. |
| `verification/safemodel_diff.py` | `_decode.py`'s link/leaf distinction | non-optional nested SafeModel/list is a link, not a divergence | ✓ WIRED | CR-01 fix reproduced: before the fix a partial `market_data` row produced 5 false `model-only` tuples; after, 0 — re-confirmed by the passing `test_safemodel_diff_null_object_links.py` in this session. |

### Behavioral Spot-Checks (re-run live, not merely re-stated from SUMMARY)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Package suite green | `uv run pytest packages/market-data-client -q` | 711 passed | ✓ PASS |
| mypy strict clean | `uv run mypy packages/market-data-client/src packages/market-data-client/tests` | Success: no issues found in 49 source files | ✓ PASS |
| Decode digest unmoved | `uv run python tools/check_decode_intactness.py` | digest `a1f00c824348164c == CANONICAL_DIGEST` | ✓ PASS |
| Surface-types gate | `uv run python tools/check_surface_types.py` | 0 violations | ✓ PASS |
| Uniform-structure gate | `uv run python tools/check_uniform_structure.py` | clean, all 6 packages | ✓ PASS |
| Driver + differ locks (CI's actual `lint`-job command) | `uv run pytest verification/test_main_market_data_deep_chain.py verification/test_safemodel_diff_null_object_links.py verification/test_main_market_data_postprocess_guarded.py ... -q` | 43 passed | ✓ PASS |
| Whole-workspace package suite | `uv run pytest packages -q` | 1995 passed, 1 deselected | ✓ PASS |
| Whole-workspace mypy | `uv run mypy` | Success: no issues found in 75 source files | ✓ PASS |
| Alias/field adjacency (structural) | inline Python: `f & a == set()`, `f == {ten wire names}` | `ok` | ✓ PASS |
| Public-surface enforcement | `uv run pytest packages/market-data-client/tests/test_public_surface_market_data.py -q` | 6 passed | ✓ PASS |
| Blob-hash pins (D-09, no scope creep) | `git rev-parse HEAD:<_core.py,_decode.py,client.py,aio.py,pyproject.toml,uv.lock>` | all 6 hashes match exactly what SUMMARY/REVIEW-FIX claim | ✓ PASS |

### Requirements Coverage

Covered above — both NOBJ-MD-01 and NOBJ-MD-02 satisfied, no orphans.

### Anti-Patterns Found

None. `grep -n -E "TBD|FIXME|XXX"` over `models.py`, `__init__.py`, `main_market_data.py`,
`verification/test_main_market_data_deep_chain.py`, `verification/safemodel_diff.py` returns zero
matches. `ruff check` is clean across the touched surface. No hardcoded empty return flowing to a
consumer was found — the `MarketDataEntries.empty()` / `[]` values are the Null Object semantics
the requirement itself asks for, backed by a real walker, not a stub.

### Code Review Process Verified (not just claimed)

Phase 36 went through `gsd-code-review` (`36-REVIEW.md`, standard depth, 2 critical + 6 warning
findings) and `gsd-code-fixer` (`36-REVIEW-FIX.md`, all 8 fixed). This verification independently
re-confirmed every fix landed in the working tree, not merely in the fix report's narrative:

- **CR-01** (SHAPE-diff fabricated `model-only` findings for non-optional Null Object links) —
  `verification/safemodel_diff.py` carries the link/leaf skip; `verification/test_safemodel_diff_null_object_links.py` exists and passes live.
- **CR-02** (no-data-row fixtures didn't match the committed baseline they claimed to mirror) —
  `_NO_DATA_ROW` and `_MEASURED_NO_DATA_ROW` verified byte-identical to `get-latest.json`, live.
- **WR-01** (SC-5 lock shipped inert, never run in CI) — confirmed wired into `ci.yml`'s `lint` job.
- **WR-02** (11th key silently discarded) — documented in the class docstring with the three blocked
  mitigations named; detection path (wire-only record to the committed ledger) pinned by a test.
- **WR-03** (stale cross-package docstring in `matriz_client.models`) — commit `db4b9fa` present in
  `git log`; not independently re-diffed here (out of this phase's touched-file scope for market-data,
  but the commit exists in history).
- **WR-04** (source-incompatible `0.5.0` with no marker) — README `## Unreleased — BREAKING` section
  with migration table confirmed present.
- **WR-05** (`chained=N` detail term tautological) — superseded by `with_last=` at all 4 sites,
  confirmed via the driver's chain dereference grep matching the WR-06-updated pattern.
- **WR-06** (batch collection unchained while guard reported probe covered) — per-probe non-vacuity
  floor (`_MIN_CHAINED_ACCESSES_BY_PROBE`, 6/12/6/12) and `_CHAINED_COLLECTIONS_BY_PROBE` confirmed
  live in `verification/test_main_market_data_deep_chain.py`; `main_market_data.py` chains both
  `latest` and `batch` (30 total dereferences, up from the original 24).

### Deferred / Documented Residual Risk (not a gap against this phase's SC-1..SC-5)

**`MarketDataSnapshot.market_id` (`str`) and `.active` (`bool`) are over-declared leaves.** On the
real committed `get-latest.json` no-data row both arrive `null`; the walker manufactures `""` /
`False` in normal decode (never raises), but under `strict_decode=True` the object construction
raises on `.market_id` **before** a `MarketDataSnapshot` instance — and therefore its `.market_data`
chain — can ever be reached. This is real and independently reproduced in this session
(`test_the_measured_no_data_row_still_raises_on_an_over_declared_leaf` passes, asserting exactly
that raise at `field_path == ".market_id"`).

This does **not** fail SC-1 (whose four-payload matrix uses `market_data: {}` as its "no data" case,
not the literal captured row with its unrelated over-declared leaves) or SC-4 (which only claims
`market_data` truthiness + `note`, not whole-row strict-mode success). The phase's informal Goal
prose ("...con la fila no-data") is a looser paraphrase of SC-1's four-case matrix and is satisfied
by the formal SC wording; the strict-mode leaf raise is a distinct, correctly-scoped-out issue.

It was **found by this phase's own code review (CR-02)**, is **fully documented** with the exact
measurement in `36-DEFERRED-market-data-leaves.md`, is **asserted in the test suite** (so Phase 39's
live run will find it predicted rather than discover it as a surprise), and is **explicitly held back
from an autonomous fix** because widening a published field's annotation requires the same kind of
blocking operator checkpoint every prior source-breaking shape change in this repo went through
(33-07 Task 1, 31-04 Task 1). This is the correct escalation-gate behavior, not a gap — but it is
flagged here for visibility ahead of Phase 39/40, since no phase in the current ROADMAP (37-40)
explicitly claims this item.

### Human Verification Required

None. Every truth in this phase is backed by an executable test that was independently re-run in
this session (not merely re-read from a report), and no visual/real-time/external-service behavior
is in scope for this phase.

### Gaps Summary

None. All five ROADMAP Success Criteria are independently verified against the current working
tree. All 8 code-review findings (2 critical, 6 warning) are confirmed fixed in the code, not just
claimed in the fix report. Requirements NOBJ-MD-01 and NOBJ-MD-02 are both satisfied with no
orphaned requirement IDs. One residual risk (`market_id`/`active` over-declaration under strict
mode) is correctly out of this phase's formal scope, was proactively found and documented by the
phase's own review process, and is filed for a future operator checkpoint rather than silently
dropped.

---

_Verified: 2026-08-29T13:57:02Z_
_Verifier: Claude (gsd-verifier)_
