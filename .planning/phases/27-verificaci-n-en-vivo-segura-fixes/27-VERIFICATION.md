---
phase: 27-verificaci-n-en-vivo-segura-fixes
verified: 2026-08-01T16:45:45Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: none
  note: "No prior VERIFICATION.md existed for this phase — initial verification."
---

# Phase 27: Verificación en vivo segura + fixes — Verification Report

**Phase Goal:** Toda la superficie de mutación (sync + async) se ejercita en vivo contra
develop de forma destructiva pero segura (create→verify→revert), la idempotencia asumida se
revalida, y toda divergencia se corrige en el mismo ciclo.

**Verified:** 2026-08-01T16:45:45Z
**Status:** passed
**Re-verification:** No — initial verification.

## Method

This report is built from direct codebase inspection (not from SUMMARY.md claims). Every
factual assertion below was independently reproduced against the merged tree on
`milestone/v1.5-mutations` (HEAD `bf178c3`):

- Read `main_market_data.py` (3311 lines), `verification/mutation_gate.py`,
  `packages/market-data-client/src/market_data_client/{_core,models,client,aio}.py`, and the
  full findings corpus `.planning/verification/market-data-client-findings.md`.
- Ran the package suite, the harness/driver AST guards, `verify_cycle_closure`, and a full
  monorepo `pytest` sweep (excluding the real-sleeping `test_retry_after_cap.py`) live, in this
  session — not taken from a prior transcript.
- Did **not** re-run the armed destructive cycle against `market-data-develop.bbsa.com.ar`
  (that would create a new live mutation event without a fresh operator authorization scoped to
  this verification pass); instead the recorded evidence (transcripts, sha256-pinned
  before/after findings-file diffs, an independent read-only residue sweep) was inspected for
  internal consistency and cross-checked against the code that would have produced it.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `main_market_data.py` exercises all mutations (symbols + calendar) sync+async behind the mutating-gate (env-gate + exact develop host) | ✓ VERIFIED | `mutating_allowed_for(env_var=..., base_url=..., expected_host=...)` (`verification/mutation_gate.py`) is computed once in `main()`/`_async_main()` and threaded into the two ctor sites `Client(mutating_allowed=..., expected_host=_EXPECTED_DEVELOP_HOST)` / `AsyncClient(...)` (`main_market_data.py:3148,3236`). Both `_env_var == "1"` and `urlsplit(base_url).hostname == "market-data-develop.bbsa.com.ar"` (exact match, fail-closed on parse error) are required. 17 `probe_*` functions cover create/update/batch symbols and preview/add/delete calendar+holidays on both `probe_..._sync` and `probe_..._async` names (grepped and enumerated). `verification/test_main_market_data_uses_single_client_instance.py` (exactly 2 ctor sites) passes. |
| 2 | Every destructive probe uses dedicated test identifiers and completes a create→verify→revert cleanup cycle; real market config is never touched without `confirm` | ✓ VERIFIED | Six stable `GSDPROBE/P27-*` symbol ids + two dedicated 2099 holiday dates. Symbols cleanup is `PATCH active=false` (no `DELETE /symbols` exists on the live spec — confirmed by 27-06's live openapi re-fetch); holidays get a full `POST`→`GET`→`DELETE` cycle. `PUT`/`DELETE /calendar/config` are **structurally unreachable**: `verification/test_main_market_data_no_config_write.py` walks the driver AST and asserts (a) no call site, (b) no attribute/name reference at all (blocks the `fn = client.x; fn()` escape), (c) non-vacuity (the preview surface **is** referenced). Independently re-run in this session: `3 passed`. Grep confirms the two banned names appear only inside comments/docstrings in `main_market_data.py`, never as code. |
| 3 | Per-endpoint idempotency (DM-03) is revalidated against live behaviour before trusting retry-behaviour; retry-safety confirmed or corrected | ✓ VERIFIED | All 8 mutation builders were measured live by row-count in the 27-06 armed run (transcript inspected: `PROBE add_holidays_*: ... refire_status=200`, `PROBE delete_holiday_*: ... second_status=404`, etc.). `build_add_holidays_request` was flipped `False→True` on measured evidence (upsert-by-date; 1 row after double-fire, both surfaces) — confirmed in `_core.py:688-718`. The flip removed the package's only `idempotent=False` builder; the short-circuit itself is now re-pinned directly at the transport in `packages/market-data-client/tests/test_transport.py` with a synthetic `RequestSpec(idempotent=False)` proving **exactly 1 request / 0 sleeps** under 3 queued 503s, plus a positive-control `idempotent=True` twin proving 3 requests / 2 sleeps — independently re-run in this session on both sync and async: `4 passed`. |
| 4 | Every divergence documented in findings and fixed in-cycle, mirrored sync/async, with a mocked regression test per fix | ✓ VERIFIED | Findings file has **0 OPEN** blocks (66 total, verified by grep). `symbol_id` widened to `int \| str` at all 4 call routes (`_core.build_update_symbol_request`, `Client.update_symbol`, `AsyncClient.update_symbol`, both module shims — grepped and confirmed). `Symbol` gained 5 wire fields (`id`, `market_id`, `created_at`, `updated_at`, `received_at`) with defaults; `marketId` kept and now populated via a wire mirror in `from_api`. `parse_symbols_response` rewritten to unwrap real mutation bodies while preserving `list[Symbol]` return type (`_core.py:958-998`). Every fix has a dedicated regression test with a deliberately relevant assertion (sampled `F-55`→`test_symbol_field_set_matches_reconciled_wire`, an exact-field-set assertion chosen specifically to catch both additive and silent-removal regressions — not the merely-present-and-green kind the phase context warned about). Package suite: `387 passed`. `ruff check` / `ruff format --check` / `mypy` on `packages/market-data-client/src main_market_data.py`: all clean. |
| 5 | Cycle closure PASS | ✓ VERIFIED | `verify_cycle_closure("market-data-client")` invoked live in this session → `(True, [])`. Not a vacuous pass: the findings file has 66 blocks, 52 `Regression:` bullets, and the sampled links resolve to genuinely relevant tests (see criterion 4 evidence and the F-37→F-62 relevance sample below). |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `main_market_data.py` | Gate + 17 sync/async mutation probes + residue sweep + cycle-closure terminal | ✓ VERIFIED | 3311 lines; `mutating_allowed_for` imported and used; `verify_cycle_closure` imported and called as the last probe; both ctor sites carry `mutating_allowed`/`expected_host`. |
| `verification/mutation_gate.py` | Package-agnostic two-leg gate, no client-package hard-import | ✓ VERIFIED | `mutating_allowed_for(*, env_var, base_url, expected_host)` present; imports no client package (`grep -c 'import matriz_client'` → 1, confined to the back-compat `mutating_allowed()` wrapper). |
| `packages/market-data-client/src/market_data_client/_core.py` | `parse_symbols_response` fixed, idempotency flags corrected | ✓ VERIFIED | Envelope-unwrap ladder present (`items[]` → flat `symbol` key → bare list → `[]`); `build_add_holidays_request` `idempotent=True`; comment at line 712 confirms package has no `idempotent=False` builder left, and points at the transport-level pinning test. |
| `packages/market-data-client/src/market_data_client/models.py` | `Symbol` reconciled against live wire | ✓ VERIFIED | 5 new wire fields with defaults; `marketId` alias preserved and populated via `from_api` mirror; docstring records the D-22 non-breaking rationale. |
| `packages/market-data-client/src/market_data_client/client.py` / `aio.py` | `symbol_id: int \| str` mirrored on both surfaces | ✓ VERIFIED | Grepped both files: identical signature on `update_symbol` methods and module shims. |
| `.planning/verification/market-data-client-findings.md` | 0 OPEN, all promotions linked to a resolvable, relevant test | ✓ VERIFIED | `grep -c "^### F-"` → 66; `grep "Status:.* OPEN"` → 0 matches. |
| `verification/test_main_market_data_no_config_write.py` | AST guard making D-06 non-vacuous | ✓ VERIFIED | Re-run live: 3 passed (call-site ban, reference ban, non-vacuity positive-control). |
| `packages/market-data-client/tests/test_transport.py` | Transport-level pin of the `idempotent=False` short-circuit | ✓ VERIFIED | Re-run live: 4 passed (`idempotent=False`/`True` × sync/async, exact request-count and sleep-count assertions). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `main_market_data.py` gate computation | `Client()`/`AsyncClient()` constructors | `mutating_allowed=<gate>, expected_host=_EXPECTED_DEVELOP_HOST` | WIRED | Exactly 2 ctor sites, both carrying the kwargs — reconfirmed by the AST guard, re-run live. |
| `_mutate_raw_sync`/`_mutate_raw_async` | `_ensure_mutation_allowed()` → `_request()` | gate-first dispatch | WIRED | `verification/test_main_market_data_no_gate_bypass.py` (taint-tracking AST walk, including through local-variable reassignment) — re-run live: passes as part of the 58-test harness-guard batch below. |
| Findings promotions (`Regression:` bullets) | Actual test functions | `verify_cycle_closure` resolution | WIRED | `(True, [])` reproduced live; sampled links (F-41/F-51 → `test_create_symbol_returns_real_rows_not_key_blanks`, F-55/F-45 → `test_symbol_field_set_matches_reconciled_wire`) read and confirmed non-vacuous (would fail without the corresponding fix). |
| `build_add_holidays_request(idempotent=True)` | Transport retry loop | `request.extensions["idempotent"]` short-circuit | WIRED | Re-pinned at `test_transport.py` with synthetic specs, independent of any package builder's current flag value — re-run live, 4/4 pass. |

### Behavioral Spot-Checks / Live Gates Reproduced This Session

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| D-06 AST guard non-vacuous | `pytest verification/test_main_market_data_no_config_write.py -q` | 3 passed | ✓ PASS |
| Idempotency short-circuit pin | `pytest packages/market-data-client/tests/test_transport.py -q -k idempotent` | 4 passed | ✓ PASS |
| Package suite | `pytest packages/market-data-client/tests -q` | 387 passed | ✓ PASS |
| mypy strict | `mypy packages/market-data-client/src main_market_data.py` | no issues, 12 files | ✓ PASS |
| ruff check/format | `ruff check .` / `ruff format --check .` | all clean | ✓ PASS |
| Cycle closure | `verify_cycle_closure("market-data-client")` | `(True, [])` | ✓ PASS |
| All phase-27 harness/AST guards | 10 files (`test_main_market_data_uses_single_client_instance`, `_postprocess_guarded`, `_no_gate_bypass`, `_cleanup_emits_finding`, `_skip_line_shape`, `_snapshot_identifiers`, `test_mutation_gate_parametrized`, `test_findings_fid_seed`, `test_findings_append_only`, `test_cycle_closure_market_data`) | 58 passed | ✓ PASS |
| Full monorepo suite (excl. real-sleeping retry test) | `pytest -q --ignore=verification/test_retry_after_cap.py` | 19 failed, 1413 passed, 19 errors | ✓ PASS (all 19 failed + 19 errors are the documented pre-existing matriz Phase-15 signature drift — see below) |

**Pre-existing failure confirmation.** The live full-suite run reproduced exactly the documented
signature: `test_main_matriz_login_fail_uniformity.py` (2 failed + 2 errors) and
`test_matriz_sweep_snapshot.py` (17 failed + 17 errors) — every failure/error is
`TypeError: probe_get_X() missing 1 required positional argument: 'client'`, matching
`deferred-items.md`'s account of Phase-15 (`main_matriz.py`) probes gaining a required `client`
argument that the two verification test files were never updated to pass. Nothing in Phase 27
touches `main_matriz.py` or these two test files (confirmed by `git log --oneline -- main_matriz.py verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py` showing no phase-27 commits). This is a real pre-existing gap in the repo but is explicitly out of Phase 27's scope and does not block this phase's goal.

### F-37..F-62 Relevance Sample (guarding against a vacuous cycle-closure PASS)

`cycle_report.py` only checks that a `Regression:` path resolves and contains `def <name>(` — it
cannot judge relevance. Sampled independently:

- **F-41/F-51** (`create_symbol` misparse) → `test_create_symbol_returns_real_rows_not_key_blanks`:
  asserts `len(result) == 1`, populated fields, and `len(result) != len(_CREATE_SYMBOL_BODY)` —
  this would fail against the pre-fix all-default-per-key behaviour. **Relevant, non-vacuous.**
- **F-55/F-45** (`Symbol.market_id` wire-only) → `test_symbol_field_set_matches_reconciled_wire`:
  deliberately asserts the **exact field set** via `dataclasses.fields(Symbol)` rather than merely
  reading the new field, specifically because a test that only reads the new fields would stay
  green even if a field were dropped or `marketId` silently renamed. This is exactly the pattern
  that plan 27-01 established (and explicitly avoided a fabricated link for) two waves earlier in
  this same phase. **Relevant, non-vacuous, and deliberately hardened.**
- **F-59/F-49** (holidays idempotency flip) → `test_add_holidays_retries_three_times_on_repeated_503`:
  asserts 3 requests / 2 sleeps against 3 queued 503s — the observable consequence of the flag
  flip, and it explicitly replaces a Phase-26 test that asserted the opposite. **Relevant,
  non-vacuous.**
- **F-60/F-50** (`DELETE /calendar/holidays/{day}` idempotent=True kept, not flipped) → EXPECTED,
  not FIXED, with `test_delete_holiday_retry_after_lost_response_surfaces_404` pinning the
  documented consequence (503→404 → `MarketDataAPIError`, 2 requests). Correctly **not** claimed
  as a fix since no code changed — avoids the T-27-40 false-PASS the phase itself names.

No fabricated or merely-well-formed link was found in the sample.

### Judgement Call Assessment — `DELETE /calendar/holidays/{day}` kept `idempotent=True`

27-07 examined this rather than mechanically flipping it and concluded the flag should stay
`True` even though the second fire returns `404`. Independently assessed: the reasoning is sound.
The flag governs *replay safety of state* (a retried DELETE cannot delete a second day, duplicate
anything, or resurrect a row), and the `404` on a lost-response retry only changes the *identity*
of the raised error (`MarketDataAPIError` from the 404 vs. whatever the original transient error
would have raised without a retry) — no caller path exists where retry produces a false "success"
belief, and no caller path is created where a non-retried failure would have succeeded silently.
Flipping to `False` trades away real transient-failure retry coverage for zero data-safety gain.
This is the correct call: it is marked `EXPECTED` (not `FIXED`) because no code changed, which is
the accurate classification and avoids a false "fixed" claim.

### D-22 Non-Breaking Verification (load-bearing for Phase 28)

Confirmed directly in the codebase, not from the SUMMARY narrative:

- `symbol_id` is `int | str` at all 4 call routes (`_core.build_update_symbol_request`,
  `Client.update_symbol`, `AsyncClient.update_symbol`, both module-level shims) — **widened**,
  never narrowed from the published `str`.
- `create_symbol` / `create_symbols` / `update_symbol` still declare `-> list[Symbol]` on both
  shells (6 signatures grepped and confirmed).
- `Symbol.marketId` still exists as a field (not renamed/removed); `market_id` was added
  alongside and `from_api` fills `marketId` from `market_id` only when the payload doesn't
  already carry an explicit `marketId` key (verified by reading the `from_api` override).
- `market-data-client` is currently tagged/published at `v0.3.1` (git tags confirmed:
  `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.3.1`), consistent with 27-07's note that D-22's premise
  (v0.3.0 already ships `create_symbol`/`create_symbols`/`update_symbol` as public contract) is
  correct and that the widen-don't-narrow approach was the only non-breaking option available.

No evidence found that would invalidate Phase 28's planned non-breaking minor bump.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| LIVE-MUT-01 | 27-01..27-07 | Full mutation surface exercised live behind the gate, dedicated identifiers + cleanup, DM-03 revalidated, divergences fixed in-cycle (mirrored, tested), cycle closure PASS | ✓ SATISFIED | All 5 ROADMAP success criteria independently verified above against the live codebase and a live re-run of every automatable gate. |

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX` markers in any phase-modified source file
(`_core.py`, `models.py`, `client.py`, `aio.py`, `main_market_data.py`,
`verification/mutation_gate.py`). No placeholder returns, no hardcoded-empty stubs found in the
mutation dispatch or parser code inspected.

### Human Verification Required

None. Every must-have was either statically confirmed against the source (gate wiring, type
signatures, AST guards) or reproduced live in this verification session (test suites, mypy,
ruff, `verify_cycle_closure`). No visual, real-time, or subjective-UX truths are in scope for
this phase.

### Deferred Items (not gaps — explicitly out of this phase's scope)

- **Pre-existing matriz Phase-15 signature drift** (`test_main_matriz_login_fail_uniformity.py`,
  `test_matriz_sweep_snapshot.py`, 19 failed + 19 errors) — reproduced live in this session,
  confirmed unrelated to any Phase 27 commit, tracked in `deferred-items.md`. Recommend a
  dedicated matriz-scoped fix or `/gsd-audit-fix` before Phase 28, since it means the matriz
  sweep-snapshot regression guard currently guards nothing — but this is not a Phase 27 blocker.
- **`get-market-data.json` type-only schema drift** (F-37/F-39/F-63/F-65) — key-set identical,
  only inferred types differ by market-open/closed state at read time; correctly classified
  EXPECTED and explicitly flagged by 27-07 as a harness-design item (a baseline that tolerates
  both states), not a Phase 27 fix.
- **`PUT`/`DELETE /calendar/config` live coverage** (F-62) — remains structurally unreachable
  from the driver by design (D-06); still requires a future operator decision to alter shared
  develop config, which Phase 27 correctly declined to make unilaterally.
- **PUB-MUT-01 premise is stale** — `market-data-client` v0.3.0/v0.3.1 are already tagged and
  published (confirmed via `git tag`), so Phase 28 needs to re-target its version number. This
  is a Phase 28 planning concern, not a Phase 27 gap.

### Gaps Summary

None found. All 5 ROADMAP success criteria are independently verified against the live
codebase, not merely asserted by SUMMARY.md. Every fix is mirrored sync/async with a genuinely
relevant (not merely well-formed) regression test, `verify_cycle_closure("market-data-client")`
reproducibly returns `(True, [])`, the D-06 config-write guard is a real, non-vacuous AST guard,
the idempotency short-circuit that the flip could have silently un-covered was re-pinned at the
transport level and reproducibly proven live, and the D-22 non-breaking claims hold under direct
source inspection. The one operator judgement call reviewed (`DELETE /calendar/holidays/{day}`
kept idempotent) is well-reasoned and correctly classified as EXPECTED rather than FIXED.

---

*Verified: 2026-08-01T16:45:45Z*
*Verifier: Claude (gsd-verifier)*
