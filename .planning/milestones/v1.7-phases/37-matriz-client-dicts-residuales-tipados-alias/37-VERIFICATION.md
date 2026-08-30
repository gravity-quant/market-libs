---
phase: 37-matriz-client-dicts-residuales-tipados-alias
verified: 2026-08-29T18:06:06Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 37: `matriz-client` — dicts residuales tipados + alias Verification Report

**Phase Goal:** La implementación de referencia del patrón Null Object queda ella misma sin
`dict[str, Any]` en su superficie pública y expone la misma ergonomía de alias que market-data,
compartida por la superficie REST y los frames de WebSocket.
**Verified:** 2026-08-29T18:06:06Z
**Status:** passed
**Re-verification:** No — initial verification

**Context note:** this verification was explicitly asked to re-check the 10 code-review findings
(2 CRITICAL + 8 WARNING) found after the 5 plans landed and reportedly fixed in commits
`1c9a5bc..ca8b759`. All 10 fixes were independently re-derived against current source (not trusted
from the review's or SUMMARY's own claims) — see "Code Review Fix Re-Verification" below.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `InstrumentDetail.tickPriceRanges` is a typed model mapping, not `dict[str, Any]` | ✓ VERIFIED | `models.py:629` — `dict[str, TickPriceRange]`; `TickPriceRange` class at `:565`, baseline-captured provenance |
| 2 | `DetailedPosition.report` (ROADMAP/REQUIREMENTS say `AccountReport.report` — a documented naming slip, the real field is on `DetailedPosition`) is a typed two-level model mapping | ✓ VERIFIED | `models.py:902` — `dict[str, dict[str, InstrumentPositionReport]]`; naming slip explicitly documented in code comment and 37-03-PLAN.md/SUMMARY.md so no field was silently invented |
| 3 | `AccountReport.detailedAccountReports` is a typed one-level model mapping | ✓ VERIFIED | `models.py:970` — `dict[str, DetailedAccountReport]` |
| 4 | `AccountReport.portfolio` is a typed scalar, not a dict | ✓ VERIFIED | `models.py:980` — `portfolio: float \| None = None` |
| 5 | `check_surface_types.py` reports zero `dict[str, Any]` in matriz's public model fields, with exactly one exemption (`UnknownFrame.raw`) | ✓ VERIFIED | Executed: `0 violations`, `24 exempted (... ws-catch-all 1)`; `_FIELD_EXEMPTIONS = {"UnknownFrame.raw": "ws-catch-all"}` is the only entry; predicate independently re-executed against all 9 review-cited bypass shapes (`Union[dict[str,Any],None]`, `dict[str,dict[str,Any]]`, quoted, `defaultdict`, bare `dict`, etc.) — all now caught, `list[Any]` still correctly spared |
| 6 | `snapshot.last/.bids/.offers/.settlement/.close/.open_interest` work identically on REST- and WS-parsed `MarketDataSnapshot` | ✓ VERIFIED | Six `@property` aliases at `models.py:755-783`; `MarketDataFrame.marketData` field is typed `MarketDataSnapshot` (same class, `models.py:999`) — confirmed via `dataclasses.fields`; test `test_one_class_serves_both_surfaces_so_the_alias_set_is_shared` asserts `type(rest) is type(ws) is MarketDataSnapshot`; executed `MarketDataSnapshot.empty()` and all six aliases resolve without error |
| 7 | `mypy --strict` is clean over the matriz package | ✓ VERIFIED | Executed: `Success: no issues found in 17 source files` (src) and `27 source files` (tests); repo-wide `uv run mypy` also clean (75 files) |
| 8 | matriz test suite is green on REST and WS/daemon-thread paths, decode-mode propagation intact, deny-listed files untouched | ✓ VERIFIED | Executed: `578 passed` (matriz package); `44 passed` on `-k ws`; `git diff` on `_token_store.py`/`_refresh_policy.py`/`_refresh.py`/`ws_client.py` since baseline `851d3d4` is empty; `check_decode_intactness.py` Checks A-D green (`_decode.py` canonical hash unchanged across all 5 copies) |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/matriz-client/src/matriz_client/models.py` | 4 fields retyped, 3 new model classes, recursive mapping axis, 6 alias properties | ✓ VERIFIED | All present; substantive (full docstrings citing provenance); wired (used by `from_api`, exercised in 578 passing tests) |
| `packages/matriz-client/src/matriz_client/_core.py` | Risk parsers unwrap the vendor envelope | ✓ VERIFIED | `unwrap(data, "detailedPosition"/"accountData", path)` present, single-site (client.py/aio.py delegate, byte-unchanged) |
| `tools/check_surface_types.py` | Field-annotation dimension added, narrow predicate, class+field exemption | ✓ VERIFIED | `_field_annotation_is_untyped_mapping`, `_FIELD_EXEMPTIONS`, `_is_field_exempt` present and correct on execution |
| `packages/matriz-client/tests/test_surface_types_red.py` | RED fixture proving gate non-vacuity | ✓ VERIFIED | 19 tests, `19 passed`; includes exemption-reachability and exemption-is-class-qualified cases |
| `main_matriz.py` (live driver) | Risk probes pass explicit envelope keys, matching `_core.py` | ✓ VERIFIED | `envelope_key="detailedPosition"`/`"accountData"`; `envelope_key` parameter has no default (`str`, required); locked by `verification/test_main_matriz_risk_envelope_keys.py` (3 layers, all passing) and wired into CI's explicit `lint`-job test list |
| `verification/safemodel_diff.py` | Shape-differ gains a mapping branch (WR-06) | ✓ VERIFIED | Locked by `verification/test_safemodel_diff_mapping_recursion.py` (25 passed) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `models.py` mapping axis | `_decode.walk_field` | element-typed recursion, sink threaded through | ✓ WIRED | `_mapping_value` calls `_decode.walk_field(item, element, ..., sink=sink)`; self-recurses when element is itself a mapping (verified for `report`'s 2-level shape) |
| `_core.py` Risk parsers | `unwrap()` | envelope key lookup | ✓ WIRED | Both parsers call `unwrap(data, key, path)`; regression tests assert enveloped body populates and flat body raises `PrimaryAPIError` |
| `main_matriz.py` probes | `_core.py` parsers | matching envelope key | ✓ WIRED | Grep-asserted by `test_risk_probe_declares_the_envelope_key_core_unwraps` — driver and client cite the same literal keys |
| `MarketDataFrame.marketData` (WS) | `MarketDataSnapshot` (REST return type) | same class, both surfaces | ✓ WIRED | Field-type identity confirmed; `ws_client.py` untouched (no commit touches it in this phase) |

### Code Review Fix Re-Verification (independently re-derived, not trusted from claims)

| Finding | Fix Location | Verified How | Result |
|---------|-------------|---------------|--------|
| CR-01 (driver stale envelope_key=None) | `main_matriz.py` | grep for `envelope_key=None`; `envelope_key` signature inspection; ran `verification/test_main_matriz_risk_envelope_keys.py` | Fixed — no `None` call sites remain, param is required `str`, 3-layer lock passes |
| CR-02 (4 gate false negatives) | `tools/check_surface_types.py` | Executed `_field_annotation_is_untyped_mapping` against all 9 review-cited bypass shapes in a live Python REPL | Fixed — all 9 now caught; `list[Any]` still spared (D-01b preserved) |
| WR-01/WR-02 (Mapping/bare-dict blind spots) | `matriz_client/models.py::_is_mapping` | Read `_is_mapping` — now checks `_is_mapping_base` via `issubclass(..., collections.abc.Mapping)`, covers bare `dict` too | Fixed |
| WR-03 (Optional mapping force-collapsed) | `_apply_mapping_policy` | Read code — explicit `_is_optional(hint) and kwargs[f.name] is None: continue` guard present | Fixed |
| WR-04 (mapping key defeats lock-5 dedupe) | `_mapping_value` | Read code — `item_path = f"{path}{{}}"`, no key interpolation into path | Fixed |
| WR-05 (unwrap not self-diagnosing / null envelope) | `_core.py::unwrap` | Read docstring/code — error message now lists `sorted(data)` keys; null-envelope handling documented | Fixed |
| WR-06 (shape-differ blind to mappings) | `verification/safemodel_diff.py` | Ran `verification/test_safemodel_diff_mapping_recursion.py` (25 passed) — asserts wire-only reporting for deferred subtrees inside a mapping | Fixed |
| WR-07 (private-helper exemption leaks to fields) | `tools/check_surface_types.py` | Read code — `_is_field_exempt` is a separate function from `_is_exempt`, keyed only on `_FIELD_EXEMPTIONS`; RED test confirms `_payload`-style field reddens | Fixed |
| WR-08 (per-class checklist, not depth-agnostic) | `packages/matriz-client/tests/test_decode.py` | Read `_model_types_in` — recursive `get_args` walk, no hardcoded class names; asserts both new models are actually in the discovered set | Fixed |

No regressions found in the fixed areas — all matriz tests (578), the four cross-package CI gates
(`check_surface_types.py`, `check_decode_intactness.py`, `check_uniform_structure.py`,
`surface_parity.py`), mypy strict (workspace-wide), and ruff (check + format) are green as of HEAD
(`6df0dd6`).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| NOBJ-MTZ-01 | 37-01, 37-02, 37-03, 37-04 | 4 residual `dict[str, Any]` fields tipados against real payloads, single documented exemption | ✓ SATISFIED | Truths 1-5, 7-8 above |
| NOBJ-MTZ-02 | 37-05 | `MarketDataSnapshot` gains the 6 alias properties shared by REST + WS | ✓ SATISFIED | Truth 6 above |

No orphaned requirements — REQUIREMENTS.md traceability table already marks both `Complete` and
maps only these two IDs to Phase 37; both are claimed by plan frontmatter (`37-0{1,2,3,4}` →
NOBJ-MTZ-01, `37-05` → NOBJ-MTZ-02).

### Anti-Patterns Found

None. Grepped all phase-touched source files (`main_matriz.py`,
`packages/matriz-client/src/matriz_client/{__init__,_core,models}.py`,
`tools/check_surface_types.py`, `verification/safemodel_diff.py`) for `TBD`/`FIXME`/`XXX` — zero
hits. No placeholder returns, no empty-implementation stubs, no hardcoded empty data flowing to a
public API found in the reviewed diff.

**Residual info-level items from the code review, deliberately not required (Info severity, not
Critical/Warning) and confirmed still open — not blockers:**
- IN-01: gate docstring's "330 definitions scanned" is stale (measured 336) — cosmetic, does not
  affect the ratchet's behavior.
- IN-05: `matriz_client/__init__.py` still has no `__version__` — pre-existing gap, not introduced
  by this phase.
- IN-06: `verification/test_public_surface.py` still not in the CI `lint` job's explicit test list
  — pre-existing condition, `verification/` snapshot re-generation was confirmed manually
  (no-diff) per 37-05-SUMMARY.md.

### Pre-existing, Out-of-Scope Failures (confirmed, not a regression)

Running `pytest verification/` wholesale (which CI never does — it uses an explicit file list for
exactly this reason) shows 17+2 = 19 failures / 17+2 = 19 errors in
`verification/test_matriz_sweep_snapshot.py` and `verification/test_main_matriz_login_fail_uniformity.py`.
Root-caused: both files call `main_matriz.py` probes without the `client` positional argument
required since the Phase 15 `REFAC-05` migration. This is a long-documented, named backlog item
(`HARN-VERIF-01`, tracked since Phase 33, `.planning/ROADMAP.md` § Backlog "Deferred to v1.7+")
predating Phase 37 by several milestones and explicitly excluded from CI (`ci.yml`'s `lint` job
runs an explicit 4-file list, not `pytest verification/`). Confirmed unrelated to Phase 37: the
failure signature (`TypeError: probe_get_segments() missing 1 required positional argument:
'client'`) is identical to the pre-existing description, and every explicitly-listed CI guard
(including the two Phase 37 added) passes cleanly.

## Human Verification Required

None. All must-haves were verifiable programmatically (typed-surface behavior, gate execution,
test suite, mypy/ruff/CI-gate execution). No visual, live-network, or subjective-UX truths exist
in this phase — matriz-client remains blocked from live runs by D-MATZ-33, and the phase correctly
declared that constraint rather than working around it.

## Gaps Summary

None. All 8 derived truths (roadmap's 4 Success Criteria, expanded into 8 checkable items) are
verified against the current codebase, not against SUMMARY.md claims. All 10 code-review findings
(2 CRITICAL + 8 WARNING) claimed fixed in commits `1c9a5bc..ca8b759` were independently
re-executed/re-read against HEAD and confirmed genuinely fixed with no regression. The only open
items are Info-severity cosmetic gaps explicitly outside the Critical/Warning fix scope, and a
long-pre-existing, separately-tracked backlog rot (`HARN-VERIF-01`) unrelated to this phase.

---
_Verified: 2026-08-29T18:06:06Z_
_Verifier: Claude (gsd-verifier)_
