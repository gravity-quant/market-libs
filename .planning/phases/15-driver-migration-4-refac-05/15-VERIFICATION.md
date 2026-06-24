---
phase: 15-driver-migration-4-refac-05
verified: 2026-06-24T00:00:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
resolved_after_verification:
  - item: "matriz 18 sync sweep probes reaching a second Client via _get_default() (was human_verification item 1)"
    resolution: "Operator chose to fix (not accept the carve-out). Plan 15-05 (commit 1fbc83f) threaded the single sync `client` into _envelope_probe + all 18 sweep probes via a new `_sync_matriz_request(client, ...)` helper, removed the `_request as _matriz_request` / `_risk_auth` singleton imports, and added regression test `test_main_matriz_has_no_singleton_path_references`. main_matriz.py now constructs exactly one Client() + one AsyncClient(); zero `_get_default()`/`_matriz_request(` code refs remain; matriz package suite 322 passed; finding literals byte-unchanged. Truth #3 is now fully VERIFIED and enforced by a passing test."
human_verification:
  - test: "Confirm per-package LIVE smoke for all 4 drivers — operator runs main_ambito_financiero.py, main_iol.py, main_higyrus.py, main_matriz.py against live APIs and confirms exit 0."
    expected: "All 4 drivers exit 0 with findings written; IOL forced-refresh probe shows a real token refresh (not silenced no-op); matriz confirms TokenStore not corrupted."
    why_human: "Live API credentials not available in this environment. Per locked decision D-11, LIVE smokes are operator-driven."
---

# Phase 15: Driver Migration × 4 (REFAC-05) Verification Report

**Phase Goal:** An operator running any `main_*.py --live` constructs exactly one `Client()`/`AsyncClient()` instance per `main()` run; every probe shares that instance, finding-title stability is preserved against the v1.1 LIVE-01 baseline `71bf201`, and the v1.1 LOC-drop residual closes for iol and matriz.
**Verified:** 2026-06-24
**Status:** passed (automated must-haves 6/6; matriz scope gap closed by plan 15-05 — see Gap Closure Update below; per-package LIVE smokes operator-deferred per D-11, tracked in 15-HUMAN-UAT.md and gated by Phase 17 / LIVE-03)
**Re-verification:** Yes — initial verification returned `human_needed` (5/6) with a matriz scope question; operator chose to fix; plan 15-05 closed it and this report was updated to `passed`.

## Gap Closure Update (plan 15-05)

The initial verification flagged that 18 matriz **sync sweep probes** routed through the module singleton (`_matriz_request` → `_get_default()`), building a second sync `Client` (separate TokenStore → second remarkets login) at runtime — the exact OAuth-churn/TokenStore risk Criterion #1 targets. Both the gsd-plan-checker-class code review (WR-01) and the verifier converged on it. The operator chose to **fix** rather than accept the documented carve-out.

Plan 15-05 (`refactor(15-05): route matriz sync sweep probes through threaded Client`, commit `1fbc83f`):
- Added driver-local `_sync_matriz_request(client, method, path, *, params, auth_basic)` (mirrors `main_higyrus.py`'s `_raw_request_sync`; builds `RequestSpec`, calls instance `Client._request`, parses via `_core.parse_envelope_response`).
- Threaded the single sync `client` into `_envelope_probe` and all 18 sweep probes; `main()` passes it through.
- Moved the 3 risk probes from module `_risk_auth` to instance `client._risk_auth`; removed the singleton imports.
- Strengthened the AST guard with `test_main_matriz_has_no_singleton_path_references` (WR-02) — asserts zero `_get_default(` / `_matriz_request(` / singleton-import references, so this regression cannot silently return.
- Fixed the stale `_async_main` "default singleton" comment (WR-03).

**Post-fix evidence (on `main`):** zero singleton-path code refs in `main_matriz.py`; exactly 1 `Client()` + 1 `AsyncClient()`; all driver AST guards + bare-except + the new enforcement test = 7 passed; matriz package suite 322 passed; finding `title=`/`fid=`/`class_=` literals byte-unchanged vs pre-execution baseline; collection 989 ≥ 907. Truth #3 ("every probe shares one instance / no probe reaches `_get_default()`") is now fully achieved for matriz and enforced by a passing test.

Remaining open item: per-package LIVE smokes (operator-driven, credentials absent here) — deferred by locked decision D-11; the milestone-final live re-verification is Phase 17 (LIVE-03).

## Goal Achievement

### Observable Truths

All truths are derived from the 5 ROADMAP Success Criteria for Phase 15.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CRITICAL merge gate: AST-walker tests assert at most 2 Client()/AsyncClient() ctor calls per driver, all 4 pass GREEN | VERIFIED | `uv run pytest verification/test_main_*_uses_single_client_instance.py -v` → 4/4 PASSED; each test file is 58-66 lines, well above min_lines 25; walker covers both ast.Name and ast.Attribute per D-05; 1 <= count <= 2 assertion non-vacuous (RED confirmed on un-migrated driver per SUMMARY) |
| 2 | CRITICAL merge gate: static git diff vs baseline 71bf201 shows ZERO title/fid/probe-name changes across all 4 findings files | VERIFIED | `git diff 71bf201..HEAD -- .planning/verification/*-findings.md | grep '^[-+]### F-[0-9]'` returns no output; iol-client-findings.md delta contains only a run-timestamp and F-02 OPEN→FIXED status change from Phase 11 (4d2d23e), both documented as out of scope per D-06/D-07; 15-STABILITY-GATE.md records this with the exact command and result |
| 3 | Per-driver serial migration complete: all `pkg.get_X(...)` top-level delegators + `_get_default()._state.<attr>` INT-01 reads replaced with `client.get_X()` + `client._state.<attr>` direct access; back-compat shims intact | VERIFIED with nuance — see Human Verification item 1 | INT-01 reads (`_get_default()._state.<attr>`): zero remaining in all 4 drivers (confirmed via grep). Top-level `pkg.get_X(...)` delegators: replaced with `client.get_X()` in all 4 drivers. PEP 562 `__getattr__` shims confirmed present in `client.py` and `aio.py` for all 4 packages. NUANCE: 18 sync sweep probes in main_matriz.py call `_matriz_request` (a module-level back-compat function that transitively calls `_get_default()`), documented as intentional scope in 15-04-SUMMARY. Per REQUIREMENTS.md REFAC-05 text ("no more top-level pkg.get_X(...) nor _get_default()._state.<attr> patterns"), both prohibited patterns are eliminated. The ROADMAP cross-cutting note "no probe reaches _get_default()" is violated transitively — operator judgment needed. |
| 4 | Per-package serial complete; >=907-test baseline preserved; per-package LIVE smokes (operator-driven) | PARTIALLY VERIFIED | Test collection: 988/989 collected (comfortably >= 907 baseline). All 4 package unit suites pass: ambito+iol+higyrus=428 passed, matriz=322 passed. Per-package LIVE smokes: operator-deferred (no .env credentials in this environment, per locked decision D-11). Live smokes require human verification. |
| 5 | LOC-drop residual documented: iol + matriz LOC delta attested vs v1.0 baseline | VERIFIED (attestation mode per locked decision D-08) | 15-LOC-ATTESTATION.md exists; pins Phase 6/7 baseline anchor (iol aggregate 947); records current iol aggregate 1511 (+59.6% grown); documents -30% is structurally unreachable (library LOC grew with Phases 8/10/13; Phase 16 codegen DROPPED per Phase 12 NO-GO); states shims STAY; references >=907 obligation. Physical LOC reduction intentionally not performed per D-08. |
| 6 | IOL forced-refresh write-site (probe_refresh_token :1313) writes to the SAME threaded client instance that :1315 reads — no silent no-op | VERIFIED | `grep -n 'token_expires_at\|get_instruments' main_iol.py`: line 1313 is `client._state.token_expires_at = 0.0`, line 1315 is `client.get_instruments("argentina")` — both reference the `client` parameter of `probe_refresh_token(client: Client)`; confirmed same object. D-03 comment in code confirms the rationale. |

**Score:** 5/6 truths verified (1 present but requires human judgment on scope acceptability)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Physical library LOC reduction -30% | Phase 16 (DROPPED) / v1.3 | Phase 16 DROPPED per Phase 12 NO-GO 2026-06-14; REFAC-06 deferred to v1.3 libcst spike. D-08 makes Phase 15 attestation-only. |
| 2 | Full live re-verification (LIVE-03) | Phase 17 | ROADMAP Phase 17 LIVE-03 is the milestone-final gate post-migration, not Phase 15. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `verification/test_main_ambito_financiero_uses_single_client_instance.py` | AST-walker asserting <=2 Client/AsyncClient ctors; min 25 lines | VERIFIED | 58 lines; test function `test_main_ambito_financiero_uses_single_client_instance`; _CTOR_NAMES frozenset; covers ast.Name and ast.Attribute; assertion 1<=count<=2 |
| `verification/test_main_iol_uses_single_client_instance.py` | AST-walker asserting <=2 Client/AsyncClient ctors; min 25 lines | VERIFIED | 59 lines; test function `test_main_iol_uses_single_client_instance`; same idiom |
| `verification/test_main_higyrus_uses_single_client_instance.py` | AST-walker asserting <=2 Client/AsyncClient ctors; min 25 lines | VERIFIED | 60 lines; test function `test_main_higyrus_uses_single_client_instance`; same idiom |
| `verification/test_main_matriz_uses_single_client_instance.py` | AST-walker asserting <=2 Client/AsyncClient ctors; min 25 lines | VERIFIED | 66 lines; test function `test_main_matriz_uses_single_client_instance`; same idiom |
| `main_ambito_financiero.py` | Migrated driver; bare `Client()` import; `contains: "Client()"` | VERIFIED | Line 53: `from ambito_financiero_client import AsyncClient, Client`; line 719: `client = Client()`; line 692: `aclient = AsyncClient()`; all 7 sync+async probes carry client/aclient param |
| `main_iol.py` | Migrated driver; bare `Client()` import | VERIFIED | Line 78: `from iol_client import AsyncClient, Client, ...`; line 1593: `client = Client()`; line 1552: `aclient = AsyncClient()`; all 14 probes carry client/aclient param |
| `main_higyrus.py` | Migrated driver; bare `Client()` import | VERIFIED | Lines 108-114: `from higyrus_client import AsyncClient, Client, ...`; line 2439: `client = Client()`; line 2318: `aclient = AsyncClient()`; all 19 probes carry client/aclient param |
| `main_matriz.py` | Migrated driver; bare `Client()` import; hostname-safety read migrated | VERIFIED with nuance | Lines 79-80: `import matriz_client as primary` + `from matriz_client import AsyncClient, Client, ...`; line 2104: `client = Client()`; line 2043: `aclient = AsyncClient()`; 4 sync probes + 22 async probes carry param; hostname read at line 2107 uses `client._state.base_url`; 18 sweep probes use `_envelope_probe`/`_matriz_request` — documented scope note in SUMMARY |
| `.planning/phases/15-driver-migration-4-refac-05/15-LOC-ATTESTATION.md` | Baseline anchor + LOC delta attestation; `contains: "baseline anchor"` and "1511" | VERIFIED | File exists 140 lines; contains "Baseline anchor" (section heading); contains 1511 (3 occurrences); documents D-08 measure-only disposition; states shims STAY |
| `.planning/phases/15-driver-migration-4-refac-05/15-STABILITY-GATE.md` | STATIC diff result vs 71bf201; `contains: "71bf201"` | VERIFIED | File exists 122 lines; contains "71bf201" (baseline anchor); records exact git diff command and result "zero title-header lines changed"; documents Criterion #2 CLOSED and Criterion #4 CLOSED (988 collected) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main_ambito_financiero.py` | `ambito_financiero_client (Client/AsyncClient)` | bare `Client()` / `AsyncClient()` threaded into every probe signature | VERIFIED | Lines 692, 719; grep for `Client()` finds exactly 2 instances |
| `verification/test_main_ambito_financiero_uses_single_client_instance.py` | `main_ambito_financiero.py` | `ast.parse + ast.walk counting ast.Call ctor nodes` | VERIFIED | File contains `ast.walk`; test PASSES GREEN; count==2 |
| `main_iol.py probe_refresh_token` | the threaded client instance | `client._state.token_expires_at = 0.0` then `client.get_instruments()` on the SAME object | VERIFIED | Line 1313: write; line 1315: read; same `client` param of `probe_refresh_token(client: Client)` |
| `verification/test_main_iol_uses_single_client_instance.py` | `main_iol.py` | `ast.parse + ast.walk` | VERIFIED | PASSES GREEN |
| `main_higyrus.py` | threaded aclient | `await aclient._ensure_http_client()` replaces `await aio._get_default()._ensure_http_client()` | VERIFIED | Line 393: `http_client = await aclient._ensure_http_client()`; no `aio._get_default()` in code lines |
| `verification/test_main_higyrus_uses_single_client_instance.py` | `main_higyrus.py` | `ast.parse + ast.walk` | VERIFIED | PASSES GREEN |
| `main_matriz.py main() hostname assert` | threaded sync client | `client._state.base_url` at line 2107; `if "remarkets" not in base` preserved | VERIFIED | Line 2107: `base = client._state.base_url`; assertion preserved intact |
| `main_matriz.py _ainvoke async probes` | single aclient | `_ainvoke(aclient, name, aclient.get_X)` threading pattern | VERIFIED | `_ainvoke(aclient: AsyncClient, ...)` at line 1510; all 22 async probes pass `aclient` explicitly |
| `verification/test_main_matriz_uses_single_client_instance.py` | `main_matriz.py` | `ast.parse + ast.walk` | VERIFIED | PASSES GREEN; count==2 (1 Client + 1 AsyncClient) |
| PEP 562 `__getattr__` shims | all 4 library packages | shims in `client.py` and `aio.py` of each package | VERIFIED | grep confirms `__getattr__` in: `ambito_financiero_client/client.py:325`, `ambito_financiero_client/aio.py:281`, `higyrus_client/client.py:681`, `higyrus_client/aio.py:687`, `iol_client/client.py:737`, `iol_client/aio.py:743`, `matriz_client/client.py:916`, `matriz_client/aio.py:953` |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces driver scripts and AST-guard tests, not components rendering dynamic data. The drivers produce terminal output, not rendered UI state.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 4 AST guard tests PASS GREEN | `uv run --frozen pytest verification/test_main_*_uses_single_client_instance.py verification/test_main_drivers_bare_except.py -v` | 6 passed in 0.06s | PASS |
| Ambito + IOL + Higyrus unit suites pass (non-live) | `uv run --frozen pytest packages/ambito-financiero-client/tests/ packages/iol-client/tests/ packages/higyrus-client/tests/ -q` | 428 passed, 1 deselected in 62.40s | PASS |
| Matriz unit suite passes (non-live) | `uv run --frozen pytest packages/matriz-client/tests/ -q` | 322 passed in 25.23s | PASS |
| Test collection >= 907 | `uv run --frozen --all-packages pytest --collect-only -q` | 988/989 collected (1 deselected) | PASS |
| Stability gate diff: zero title drift | `git diff 71bf201..HEAD -- .planning/verification/*-findings.md \| grep '^[-+]### F-[0-9]'` | No output — zero title-header lines changed | PASS |
| Per-package LIVE smokes | Operator-driven; requires `.env` credentials | SKIP | SKIP (human-needed) |

### Probe Execution

Step 7c (probe execution) not applicable — no `scripts/*/tests/probe-*.sh` files and no phase-declared probes in PLAN frontmatter.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REFAC-05 | 15-01, 15-02, 15-03, 15-04 | Driver migration × 4 packages; ONE Client per main() run; AST guard per driver; probe names UNCHANGED | PARTIALLY SATISFIED | Core invariants (AST gate, stability gate, single ctor) all achieved; nuance on 18 matriz sweep probes reaching `_get_default()` transitively — see Human Verification item 1; physical LOC reduction intentionally deferred per D-08 |

No ORPHANED requirements — REFAC-05 is the only requirement ID declared across all 4 plans, and it is mapped to Phase 15 in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `main_matriz.py` (lines 134, 660, 666, 669, 676-682, 1122, 1216, 1593, 1874) | `XXX` strings | INFO | Domain-specific CFI code values (ESXXXX, DBXXXX, FXXXSX, EMXXXX, EMXXXX) and test probe names in the MATBA ROFEX API; `INVALID-ACCT-XXXXX` is an intentional bogus value for error probe. NOT code-quality debt markers — no blocker. |
| `main_higyrus.py` line 2118 | `higyrus_client.login()` (module-level call in probe_auth_401) | INFO | Intentional deviation documented in code comment (lines 2110-2115): this probe deliberately mutates the module-level default-client state to test 401 response; using the threaded `client` would interfere with its credentials. Documented design, not a migration omission. |
| `main_matriz.py` lines 357, 528, 582, 702, 781, 887, 1063 and `_envelope_probe` line 357 | `primary.client._base_url` reads in 18 sweep probes | WARNING | Module-attribute reads via PEP 562 `__getattr__` → `_get_default()._state.base_url` transitively. Documented as intentional scope in 15-04-SUMMARY. Not a BLOCKER given REQUIREMENTS.md REFAC-05 text only prohibits `pkg.get_X(...)` and `_get_default()._state.<attr>` — both eliminated. ROADMAP cross-cutting note (line 178) is stricter. See Human Verification item 1. |

No TBD/FIXME/XXX debt markers found in any of the 9 modified files (main_*.py × 4 + AST tests × 4 + 15-LOC-ATTESTATION.md; the ESXXXX/XXXXX occurrences are domain strings, not markers).

### Human Verification Required

#### 1. Scope Acceptability: 18 Unmigrated Sweep Probes in main_matriz.py

**Test:** Review `main_matriz.py` probe functions `probe_get_segments`, `probe_get_all_instruments`, `probe_get_instruments_details`, `probe_get_instrument_detail`, `probe_get_instruments_by_cfi_ESXXXX`, `probe_get_instruments_by_cfi_sanity`, `probe_get_instruments_by_segment`, `probe_get_market_data`, `probe_get_trades`, `probe_get_active_orders`, `probe_get_filled_orders`, `probe_get_all_orders`, `probe_get_order_status`, `probe_get_order_history`, `probe_get_order_by_exec_id`, `probe_get_positions`, `probe_get_detailed_positions`, `probe_get_account_report` (lines 517-1050). These 18 probes have no `client` parameter and call `_envelope_probe` or directly call `_matriz_request`. `_matriz_request` is the module-level back-compat function at `packages/matriz-client/src/matriz_client/client.py:889` which calls `_get_default()._matriz_legacy_request(...)`. They also read `primary.client._base_url` (PEP 562 → `_get_default()._state.base_url`).

**Expected:** Operator confirms one of:
- (A) The scope note in 15-04-SUMMARY is accepted: REFAC-05's prohibition of "top-level `pkg.get_X(...)` and `_get_default()._state.<attr>` patterns" is satisfied because both are eliminated; the `_matriz_request` back-compat function is outside that scope; the ROADMAP cross-cutting note is informative, not contractually binding at this phase level. Phase 15 is complete.
- (B) The ROADMAP cross-cutting note "no probe reaches `_get_default()`" is a hard requirement; the 18 sweep probes must be migrated in a follow-up task.

**Why human:** The PLAN-04 must_have truths do not include a truth about the 18 sweep probes — the plan's own SC#3 analog only states "All 6 async _state reads and the _ainvoke threading migrate to the single aclient." The REQUIREMENTS.md text is satisfied. Only the ROADMAP cross-cutting note (lines 178-179) is violated transitively. The SUMMARY explicitly documents this as an accepted scope restriction. This is a judgment call on whether the cross-cutting constraint is binding at Phase 15 level or is addressed by the existing scope rationale.

#### 2. Per-Package LIVE Smokes (D-11)

**Test:** Operator runs each driver against live APIs:
- `uv run --package ambito-financiero-client python main_ambito_financiero.py` (no auth required)
- `uv run --package iol-client python main_iol.py` (requires IOL_USERNAME, IOL_PASSWORD; confirm forced-refresh probe shows real token refresh, not no-op)
- `uv run --package higyrus-client python main_higyrus.py` (requires HIGYRUS_USERNAME, HIGYRUS_PASSWORD)
- `uv run --package matriz-client python main_matriz.py` (requires PRIMARY_USER, PRIMARY_PASSWORD; confirm exit 0 and no TokenStore corruption)

**Expected:** All 4 drivers exit 0 with findings written; no new unexpected findings vs baseline 71bf201; IOL probe_refresh_token shows a real token refresh in the debug log; matriz confirms exactly 1 Client + 1 AsyncClient were constructed (the AST gate confirms statically, but live behavior confirms no TokenStore churn).

**Why human:** Live financial API credentials are not available in the verification environment. Per locked decision D-11, live smokes are operator-driven. Phase 17 (LIVE-03) is the milestone-final live gate.

---

### Gaps Summary

No hard gaps (FAILED or MISSING artifacts) were found. The `human_needed` status arises from two items:

1. **Scope judgment** on 18 unmigrated sync sweep probes in `main_matriz.py` that reach `_get_default()` transitively through `_matriz_request`. The PLAN explicitly scoped these out; the REQUIREMENTS.md text is satisfied; only the ROADMAP cross-cutting note is stricter. This is a verifier escalation for operator decision.

2. **Operator-deferred live smokes** (4 drivers × live API) per locked decision D-11.

All structural deliverables are present and substantive. The AST gates pass. The stability gate is verified statically. The test baseline is met. The LOC attestation is documented with the operator-accepted D-08 measure-only disposition.

---

_Verified: 2026-06-24_
_Verifier: Claude (gsd-verifier)_
