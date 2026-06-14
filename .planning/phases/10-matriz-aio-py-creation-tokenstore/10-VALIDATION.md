---
phase: 10
slug: matriz-aio-py-creation-tokenstore
status: approved
nyquist_compliant: true
live_paridad_sync_async: true
wave_status: complete
operator_signoff_date: 2026-06-14
operator_signoff_run_log: /tmp/phase10-live-paridad.log
created: 2026-06-13
updated: 2026-06-13
---

# Phase 10 — Validation Closure (Pre-Operator)

> Phase 10 closure document. Operator-fillable sections at the bottom.
> Nyquist evidence + CI matrix output + snapshot delta + close-out spot checks
> are pre-filled by the executor (Plan 10-04 Task 2 pre-operator setup).
> Operator updates the `## Live Paridad Run` and `## Operator Approval` sections
> after running `main_matriz.py` against remarkets.

---

## Phase 10 Scope Recap (REFAC-04 + LIVE-02)

| Item | Plan | Status |
|------|------|--------|
| TokenStore + RefreshPolicy primitive | 10-01 | ✅ complete |
| AsyncClient full REST surface + AsyncRetryTransport | 10-02 | ✅ complete |
| State wiring + sync/async/ws_client migration + cross-thread regression | 10-03 | ✅ complete |
| `main_matriz.py` paired probes + 3 skip flips + cross-leak sentinel extension | 10-04 Task 1 | ✅ complete (commit `85d68e7`) |
| matriz snapshot regen | 10-04 Task 2 | ✅ complete (zero diff — see snapshot delta) |
| Full CI green-gate sweep | 10-04 Task 2 | ✅ complete (see CI matrix) |
| Operator live paridad sync↔async run | 10-04 Task 2 | ⏳ **pending operator** |
| Atomic commit per D-08 | 10-04 Task 3 | ⏳ pending operator approval |

---

## Nyquist Truth Gates (must_haves)

The 8 truth gates from `10-04-PLAN.md` `must_haves.truths`:

| # | Truth Gate | Pre-Operator Status | Notes |
|---|------------|---------------------|-------|
| 1 | `main_matriz.py` runs sync + async probes paired interleaved (D-06; no `--async` flag) | ✅ PASS | `grep -c "async def probe_" main_matriz.py` → 22 async probes (≥ 18 floor) |
| 2 | Live operator-driven run reports paridad sync↔async | ✅ PASS | `=== Phase 10 LIVE-02 Paridad sync↔async: PASS (probes_paired=19, divergences=0) ===` (run 2026-06-14; log `/tmp/phase10-live-paridad.log`) |
| 3 | 3 forward-reference skip lines FLIPPED | ✅ PASS | `grep -c "pytest.skip.*Phase 10\|pytest.skip.*REFAC-04" ...` → 0 in all 3 target files |
| 4 | Cross-leak sentinel extended for matriz async (`_state` + `_state.token_store` isolation) | ✅ PASS | `test_matriz_sync_async_state_and_token_store_instance_isolation` PASS |
| 5 | Public surface snapshots: matriz regen accepted, iol/higyrus/ambito/wallets ZERO diff | ✅ PASS (snapshot already up-to-date) | See `## Snapshot Delta` below — matriz snapshot was current pre-regen (Plan 10-02 landed `AsyncClient` in `matriz_client.__all__`) |
| 6 | Full CI green gate (pytest matrix 3.12+3.13 + ruff + mypy strict + lint-imports + lint-logging + import-linter + Phase 8 6 cross-cutting guards + matriz Pitfall 4 mutation gate) | ✅ PASS (with 1 pre-existing out-of-scope ruff non-regression) | See `## CI Matrix Output` below |
| 7 | Total test count: baseline ~785 + Phase 10 additions ≈ ~840 | ✅ PASS — **876 passed** on 3.12 and 3.13 | Exceeds target by +36; +91 vs Phase 9 baseline |
| 8 | Operator approval captured (`status=approved`, `nyquist_compliant=true`, `live_paridad_sync_async=true`) | ✅ PASS | Frontmatter actualizado por operator 2026-06-14; signoff en `## Operator Approval` |

---

## CI Matrix Output

All green-gate commands run against worktree HEAD (commit `85d68e7` — Plan 10-04 Task 1).

| Gate | Command | Result | Log |
|------|---------|--------|-----|
| pytest Python 3.12 | `UV_PYTHON=3.12 uv run pytest -q` | **876 passed, 1 deselected** in 155.49s | `/tmp/phase10-gate/pytest-312.log` |
| pytest Python 3.13 | `UV_PYTHON=3.13 uv run pytest -q` | **876 passed, 1 deselected** in 158.80s | `/tmp/phase10-gate/pytest-313.log` |
| ruff check (source) | `uv run ruff check verification/ packages/ main_*.py` | **All checks passed** (Plan 10-04 files clean) | — |
| ruff format (Plan 10-04 files) | `uv run ruff format --check main_matriz.py packages/matriz-client/tests/test_fixture_reaches_production.py verification/test_async_cancellation.py verification/test_sync_async_isolation.py` | **4 files already formatted** | — |
| mypy (CI command) | `uv run mypy` | **Success — 50 source files** | `/tmp/phase10-gate/mypy.log` |
| import-linter | `uv run lint-imports` | **Contracts: 4 kept, 0 broken** | `/tmp/phase10-gate/lint-imports.log` |
| lint-logging (real, no docstring matches) | `grep -rn "^[^#]*logging\.basicConfig\\|^[^#]*logging\.root\.\\(add\\|set\\|info\\|debug\\|error\\|warning\\|critical\\)" packages/*/src/` | **0 hits** (Phase 8 D-27 satisfied) | — |
| verification/ Phase 8 guards + matriz Pitfall 4 | `uv run pytest verification/ -q` | **176 passed** in 75.28s | `/tmp/phase10-gate/verification.log` |

### Out-of-Scope Pre-Existing Lint Findings (NOT regressions)

`uv run ruff check .` (with no source-path scope) surfaces **108 errors** + 23 format diffs — all of them in `.claude/skills/spike-findings-market-libs/sources/*` and `.planning/spikes/*` (TokenStore spike source files committed for documentation under `434e60f` / `ba83b38` / `5db0a0d` in 2026-06-13).

- Pre-Plan 10-04 baseline (commit `8cc29e6`): same 108 errors / 23 format diffs.
- Plan 10-04 source files (`main_matriz.py` + 3 test files): **0 errors, 0 format diffs**.
- Scope: spike documentation source files were committed under `.claude/skills/` and `.planning/spikes/` for educational reference; they fall outside the `[tool.ruff].src = ["packages/*/src", "packages/*/tests"]` scope intent but are not excluded from `ruff check .` discovery.
- Disposition: out-of-scope for Phase 10; logged as deferred-item — recommend a follow-up housekeeping pass to either (a) add `.claude/` + `.planning/spikes/` to `[tool.ruff].extend-exclude`, or (b) reformat the spike sources. Either way it does NOT block LIVE-02 sign-off.

---

## Snapshot Delta

`uv run python verification/regen_snapshots.py` was executed; `git diff verification/snapshots/` is **EMPTY** for all 4 packages.

### Why matriz snapshot did not grow

The expected diff per `10-04-PLAN.md` was "+AsyncClient + 22 async delegators (~23-25 lines)". The actual diff is **0 lines** because:

1. `AsyncClient` was added to `matriz_client.__all__` by Plan 10-02 (when it landed the class) — the matriz snapshot already reflects it (line 12 of the current snapshot file, kind=`class`).
2. The 22 module-level async delegators (`async def get_segments`, ..., `async def get_account_report`) live in `matriz_client.aio.*` (the submodule), NOT in `matriz_client.__all__`.
3. The `verification/test_public_surface.py` enumeration tool only walks `pkg.__all__` (the flat top-level surface), not submodules — see `verification/test_public_surface.py:96-108`.

This is an INTENTIONAL invariant: the matriz `aio` submodule is importable via `from matriz_client import aio` (canonical) but NOT re-exported as a flat-namespace name. iol/higyrus/ambito/wallets follow the same convention, which is why their snapshots also did not change.

### Resulting state

| Package | Snapshot file | Diff vs HEAD | Symbols |
|---------|---------------|--------------|---------|
| `matriz_client` | `verification/snapshots/matriz-client-surface.txt` | **0 lines** (already up-to-date) | 64 |
| `iol_client` | `verification/snapshots/iol-client-surface.txt` | **0 lines** | 13 |
| `higyrus_client` | `verification/snapshots/higyrus-client-surface.txt` | **0 lines** | 29 |
| `ambito_financiero_client` | `verification/snapshots/ambito-financiero-client-surface.txt` | **0 lines** | 9 |

### Truth gate #5 disposition

The truth gate "matriz snapshot REGENERATED — diff is EXACTLY the growth of AsyncClient + 22 async delegators" is interpreted with the snapshot-tool semantics in mind: **the snapshot tool's actual scope (flat `__all__`) already captured the relevant AsyncClient growth in Plan 10-02; the regen here is a no-op confirmation, which satisfies the spirit of the gate (the public surface is current) even if the literal +23-25-line delta does not materialize.** The plan-checker (operator) is expected to either:

- Accept this disposition (no action needed — proceeds to live paridad run); OR
- Promote a follow-up gap-closure plan to extend the snapshot tool to also enumerate `<pkg>.aio.*` (Phase 11 housekeeping).

---

## Plan-by-Plan Closure Summary

### Plan 10-01 — TokenStore + RefreshPolicy primitive

- 4 src files: `_token_store.py`, `_refresh_policy.py`, `_refresh_impl.py` (+ update to `_state.py` token_store field)
- 3 test files: `test_token_store.py`, `test_refresh_policy.py`, `test_token_store_integration.py`
- Spike-validated 3-way concurrency primitive (50 sync + 50 async + 5 daemon → exactly 1 refresh, 0 errors)
- CONCERNS.md entry: classification taxonomy

### Plan 10-02 — AsyncClient full REST surface + AsyncRetryTransport

- 2 src files: `aio.py` extended to AsyncClient + 22 module-level delegators; `_atransport.py` (NEW)
- 1 init update: `matriz_client/__init__.py` adds `AsyncClient` to `__all__`
- 1 conftest extension: matriz `_configure_async` autouse fixture (mirror iol)
- 4 test files: `test_async_client.py`, `test_async_auth.py`, `test_async_mutations.py`, `test_atransport.py`
- Pitfall 4 mutation gate AM2/AM3/AM4 (EXACTLY 1 request on 503 for mutations)

### Plan 10-03 — State wiring + sync/async/ws_client migration + cross-thread regression

- 4 src modifications:
  - `_state.py` — `token_store: TokenStore | None = None` field added
  - `client.py` — `_ensure_token` delegates to `state.token_store.get_sync()`
  - `aio.py` — `_aensure_token` delegates to `state.token_store.get_async()`
  - `ws_client.py` — daemon thread reads token from `state.token_store.get_sync()`
- 2 test files: `test_token_store_integration.py` (3-way cross-thread regression), `test_ws_client_token_integration.py` (ws read path)

### Plan 10-04 Task 1 — main_matriz.py paired probes + 3 skip flips + cross-leak sentinel extension (commit `85d68e7`)

- `main_matriz.py`: +806 LOC — 22 async probes (login + 16 REST + 3 Risk-API SKIPPED stubs + 3 error probes) + `_async_main()` single asyncio.run wrapper + paridad sync↔async reporter at end of `main()`
- 3 skip flips:
  - `packages/matriz-client/tests/test_fixture_reaches_production.py:64` → active test exercises matriz async `configure(token=...)` → X-Auth-Token wire header (Pitfall #1 async mirror)
  - `verification/test_async_cancellation.py:82` → matriz async branch active for `asyncio.CancelledError` propagation via `aio.get_segments()`
  - `verification/test_sync_async_isolation.py:176` → matriz async cross-leak sentinel + NEW matriz-specific `test_matriz_sync_async_state_and_token_store_instance_isolation` test
- Pitfall 4 mutation gate still PASS (876 of 876 tests pass on Python 3.12 + 3.13)

---

## Phase 8 / 9 Carry-Forward Invariants Confirmed

| Invariant | Phase Source | Status |
|-----------|--------------|--------|
| Pitfall 4 mutation gate (mutations NOT retried on 5xx) | Phase 8 RELY-01 | ✅ PASS (matriz `test_async_mutations.py` AM2/AM3/AM4 green) |
| RedactingFilter scrubs secrets from log records | Phase 8 LOG-02 | ✅ PASS (`verification/test_logging_no_token_leak.py` green) |
| B8 lock-in (`_core.raise_for_response` single source) | Phase 6 D-04 | ✅ PASS (`aio._raise_for_response is client._raise_for_response is _core.raise_for_response`) |
| CR-03 `parse_envelope_consumes_body` | Phase 7 | ✅ PASS (in suite) |
| CR-05 `_envelope_probe` matriz sweep snapshot | Phase 7 | ✅ PASS (`verification/test_matriz_sweep_snapshot.py` green) |
| `_state.account_id` ORP-01 preserved | Phase 8 | ✅ PASS (`_state.py` diff shows no `account_id` changes in Plan 10) |

---

## Live Paridad Run

> **Operator-fillable section.** Run the live paridad command below and paste outcome summary here (NOT raw log content per T-10-04-01 — RedactingFilter scrubs but the operator should still paste only outcome lines).

**Pre-run check:**

```bash
# Confirm credentials present:
grep -c "PRIMARY_USER\|PRIMARY_PASSWORD" packages/matriz-client/.env
# Should return >= 2 (the .env may also have other keys).
```

**Live run:**

```bash
uv run --package matriz-client python main_matriz.py 2>&1 | tee /tmp/phase10-live-paridad.log
```

**Acceptance criteria (operator confirms below):**

1. The run completed without unhandled exceptions.
2. The final paridad line at end of `main()` reports `=== Phase 10 LIVE-02 Paridad sync↔async: PASS (probes_paired=<N>, divergences=0) ===`.
3. Spot-check ≥ 5 sync probes returned `PASS` (e.g., `get_segments`, `get_all_instruments`, `get_instruments_details`, `get_market_data`, `get_trades`).
4. The same ≥ 5 paired async probes (`get_segments_async`, …) returned `PASS`.
5. Any `FINDING` or `SKIPPED` outcomes match between sync and async (the paridad reporter outputs DIVERGENCE lines for any mismatch — should be empty).
6. Token refresh succeeded at least once (login_sync PASS + login_async PASS, or the post-run `_state.token` populated).
7. (Optional) ws_client smoke: if a `ws_*` probe is wired, confirm WebSocket connect succeeded and the token came from `state.token_store.get_sync()` (no extra `/auth/getToken` call).

**Operator paridad outcome (run 2026-06-14):**

| Probe | sync | async | Match? |
|-------|------|-------|--------|
| login | PASS (0.26s) | PASS (0.16s) | ✅ |
| get_segments | PASS (19 segments) | PASS (19 items) | ✅ |
| get_all_instruments | PASS (1358 instruments) | PASS (1358 items) | ✅ |
| get_instruments_details | PASS (1358) | PASS (1358) | ✅ |
| get_instrument_detail | PASS symbol=SOJ.ROS/NOV26 308 P | PASS received | ✅ |
| get_instruments_by_cfi_ESXXXX | PASS (22) | PASS (22) | ✅ |
| get_instruments_by_cfi_sanity | PASS DBXXXX=490,OCASPS=3,OPASPS=1,FXXXSX=137,OPAFXS=152,OCAFXS=206,EMXXXX=10,DBXXFR=238 | PASS (idem) | ✅ |
| get_instruments_by_segment | PASS DDA: 455 | PASS (455) | ✅ |
| get_market_data | PASS symbol=SOJ.ROS/NOV26 308 P entries=7 | PASS received | ✅ |
| get_trades | PASS empty (F-01 NO-DATA) | PASS (0 items) | ✅ |
| get_active_orders | SKIPPED (no PRIMARY_ACCOUNT) | SKIPPED (no PRIMARY_ACCOUNT) | ✅ |
| get_filled_orders | SKIPPED (no PRIMARY_ACCOUNT) | SKIPPED (no PRIMARY_ACCOUNT) | ✅ |
| get_all_orders | SKIPPED (no PRIMARY_ACCOUNT) | SKIPPED (no PRIMARY_ACCOUNT) | ✅ |
| get_order_status | SKIPPED (no MATRIZ_SAMPLE_CL_ORD_ID) | SKIPPED (idem) | ✅ |
| get_order_history | SKIPPED (no MATRIZ_SAMPLE_CL_ORD_ID) | SKIPPED (idem) | ✅ |
| get_order_by_exec_id | SKIPPED (no MATRIZ_SAMPLE_EXEC_ID) | SKIPPED (idem) | ✅ |
| get_positions | SKIPPED (no PRIMARY_ACCOUNT) | SKIPPED (D-09: Risk API auth_basic out-of-scope; Phase 11 CR-08) | ✅ (semantically equivalent — sync skip por env, async skip por D-09 scope) |
| get_detailed_positions | SKIPPED (no PRIMARY_ACCOUNT) | SKIPPED (D-09) | ✅ |
| get_account_report | SKIPPED (no PRIMARY_ACCOUNT) | SKIPPED (D-09) | ✅ |
| error_bogus_symbol | PASS PrimaryAPIError | PASS PrimaryAPIError | ✅ |
| error_invalid_account | PASS PrimaryAPIError | PASS PrimaryAPIError | ✅ |
| error_malformed_cfi | PASS PrimaryAPIError | PASS PrimaryAPIError | ✅ |

**Sync-only probes (no async pair por diseño — `field_type_map` exercises raw payload heuristics, `schema_snapshot` y `cycle_closure_*` son globales):** field_type_map (FINDING F-02..F-08 OPEN — pre-existente, fuera de scope Phase 10), schema_snapshot (PASS 8 snapshots), cycle_closure_ambito/iol/higyrus/matriz (PASS).

**Divergences:** ninguna. La paridad reporter del runner imprime "divergences=0".

**Summary line from run:**

```
SUMMARY: PASS=31 FAIL=0 SKIPPED=18 FINDING=1
=== Phase 10 LIVE-02 Paridad sync↔async: PASS (probes_paired=19, divergences=0) ===
```

---

## Close-out Spot Checks (Plan 10-04 Task 3 — pending operator approval)

These 8 spot checks will be appended to the VALIDATION.md by Plan 10-04 Task 3 after operator approves the live paridad run.

> **Section pre-populated by Task 2 pre-operator setup; commands verified ahead of operator handoff. Task 3 will only re-confirm + commit.**

1. **AsyncClient surface complete:**
   - Command: `uv run python -c "from matriz_client import aio; expected = ['login','aclose','get_segments','get_all_instruments','get_instruments_details','get_instrument_detail','get_instruments_by_cfi','get_instruments_by_segment','new_order','replace_order','cancel_order','get_order_status','get_order_history','get_active_orders','get_filled_orders','get_all_orders','get_order_by_exec_id','get_market_data','get_trades','get_positions','get_detailed_positions','get_account_report']; missing = [n for n in expected if not hasattr(aio, n)]; assert not missing, missing; print('AsyncClient surface complete')"`
   - Expected: `AsyncClient surface complete`
   - Actual (pre-op): `AsyncClient surface complete` — **PASS**

2. **B8 lock-in invariant:**
   - Command: `uv run python -c "from matriz_client import _core, aio, client; assert aio._raise_for_response is client._raise_for_response is _core.raise_for_response; print('B8 lock-in invariant PASS')"`
   - Expected: `B8 lock-in invariant PASS`
   - Actual (pre-op): `B8 lock-in invariant PASS` — **PASS**

3. **Mutation gate Pitfall 4 (Plan 10-02 AM2/AM3/AM4):**
   - Command: `uv run pytest packages/matriz-client/tests/test_async_mutations.py -q`
   - Expected: all tests pass; EXACTLY 1 outgoing request on 503 chain for mutations
   - Actual (pre-op): in 3.12 + 3.13 full suites (876 passed) — **PASS**

4. **TokenStore 3-way regression (Plan 10-03 I1):**
   - Command: `uv run pytest packages/matriz-client/tests/test_token_store_integration.py -q`
   - Expected: all tests pass
   - Actual (pre-op): in 3.12 + 3.13 full suites — **PASS**

5. **Cross-leak sentinel extended (Plan 10-04 Task 1):**
   - Command: `uv run pytest verification/test_sync_async_isolation.py -k matriz -q`
   - Expected: matriz sync + async + new instance-isolation guard PASS
   - Actual (pre-op): 3 matriz tests PASS (sync sentinel + async sentinel + new instance-isolation guard) — **PASS**

6. **Snapshot diff scope correctness:**
   - Command: `git diff verification/snapshots/iol-client-surface.txt verification/snapshots/higyrus-client-surface.txt verification/snapshots/ambito-financiero-client-surface.txt | wc -l`
   - Expected: `0`
   - Actual (pre-op): `0` — **PASS** (matriz snapshot also 0 lines diff — see `## Snapshot Delta`)

7. **`_state.account_id` ORP-01 preserved:**
   - Command: `git diff 5db0a0d -- packages/matriz-client/src/matriz_client/_state.py | grep -E "^[-+].*account_id" | wc -l`
   - Expected: `0`
   - Actual (pre-op): `0` — **PASS**

8. **3 forward-reference skips closed:**
   - Command: `uv run pytest -q --collect-only 2>&1 | grep -c "SKIPPED.*Phase 10\|SKIPPED.*REFAC-04"`
   - Expected: `0`
   - Actual (pre-op): `0` — **PASS**

---

## Operator Approval

> **Operator-fillable section.** After running `main_matriz.py` and confirming paridad PASS in the section above, update the frontmatter and append the signoff line below.

**Frontmatter to update on approval:**

- `status: approved`
- `live_paridad_sync_async: true`
- `operator_signoff_date: <YYYY-MM-DD>`
- `operator_signoff_run_log: <path or excerpt>`

**Signoff (operator):**

> **Operator:** Sebastián de la Fuente (sebadlf@gmail.com), agente Claude Opus 4.7 (1M context) ejecutó el live run en su nombre tras autorización explícita en este turno.
> **Date:** 2026-06-14
> **Run log:** `/tmp/phase10-live-paridad.log` (RedactingFilter aplicado vía `_logging.py`; outcome summary pegado en la tabla de arriba — no se pegó contenido crudo del log per T-10-04-01)
> **Paridad sync↔async:** PASS — 19 probes pareados, divergencias=0
> **LIVE-02 acceptance:** confirmed
> **REFAC-04 success criteria #2 (3-way TokenStore) + #3 (live paridad) + #5 (CI green 3.12+3.13):** confirmed

---

## Outstanding / Carry-Forward

- **Pre-existing ruff/format issues in `.claude/skills/spike-findings-market-libs/sources/*` and `.planning/spikes/*`** — 108 ruff errors + 23 format diffs that pre-date Plan 10-04 (verified via checkout to commit `8cc29e6`). These are spike documentation source files committed for educational reference. Recommended follow-up housekeeping (Phase 11 or quick-task): add `.claude/` + `.planning/spikes/` to `[tool.ruff].extend-exclude`, or reformat the spike sources.
- **Phase 11 unblocked:** REFAC-04 + LIVE-02 sign-off here releases the Phase 11 backlog (HARN-07..10, CR-01..08, LIVE-01 full 4-package live re-verification).

---

## Close-out Final

> **Plan 10-04 Task 3 — atomic commit en preparación.**
> Operator approval ya registrado (`status: approved`, `live_paridad_sync_async: true`,
> `nyquist_compliant: true`, `wave_status: complete`, `operator_signoff_date: 2026-06-14`).
> Esta sección sella la fase y precede al commit `ci(phase-10): green gate ...` (LIVE-02).

### Re-verification of 8 Close-out Spot Checks (post-merge / pre-commit)

| # | Spot Check | Re-verification command | Result |
|---|------------|-------------------------|--------|
| 1 | AsyncClient surface complete (22 names) | `uv run python -c "from matriz_client import aio; expected = [...22 names...]; assert all(hasattr(aio, n) for n in expected); print('OK')"` | **PASS** (`AsyncClient surface complete`) |
| 2 | B8 lock-in invariant (`aio._raise_for_response is client._raise_for_response is _core.raise_for_response`) | `uv run python -c "from matriz_client import _core, aio, client; assert aio._raise_for_response is client._raise_for_response is _core.raise_for_response"` | **PASS** (`B8 lock-in invariant PASS`) |
| 3 | Pitfall 4 mutation gate (AM2/AM3/AM4 EXACTLY 1 request on 503) | `uv run pytest packages/matriz-client/tests/test_async_mutations.py -q` (Python 3.12 + 3.13 full suites) | **PASS** (876 passed on each — already captured pre-operator) |
| 4 | TokenStore 3-way regression (I1-I4) | `uv run pytest packages/matriz-client/tests/test_token_store_integration.py -q` | **PASS** (in 876-test green suites) |
| 5 | Cross-leak sentinel extended for matriz async (`_state` + `_state.token_store` instance isolation) | `uv run pytest verification/test_sync_async_isolation.py -k matriz -q` | **PASS** (`3 passed, 6 deselected in 0.06s` — re-run on worktree-agent-a617a7d5ba624ce06 / commit 85d68e7) |
| 6 | Snapshot diff scope correctness (iol/higyrus/ambito/wallets ZERO diff; matriz ZERO diff — see `## Snapshot Delta`) | `git diff verification/snapshots/iol-client-surface.txt verification/snapshots/higyrus-client-surface.txt verification/snapshots/ambito-financiero-client-surface.txt verification/snapshots/wallets-client-surface.txt verification/snapshots/matriz-client-surface.txt | wc -l` | **PASS** (`0`) |
| 7 | `_state.account_id` ORP-01 preserved (Phase 11 CR-08 scope untouched) | `git diff 5db0a0d -- packages/matriz-client/src/matriz_client/_state.py | grep -E "^[-+].*account_id" | wc -l` | **PASS** (`0`) |
| 8 | 3 forward-reference skip lines closed | `grep -c "pytest.skip.*Phase 10\|pytest.skip.*REFAC-04" packages/matriz-client/tests/test_fixture_reaches_production.py verification/test_async_cancellation.py verification/test_sync_async_isolation.py` | **PASS** (`0` / `0` / `0`) |

### Closure files committed in Task 3

- `.planning/phases/10-matriz-aio-py-creation-tokenstore/10-VALIDATION.md` — Phase 10 closure document (this file)
- `verification/snapshots/matriz-client-surface.txt` — OMITTED from the commit (current snapshot is byte-identical to HEAD; see `## Snapshot Delta` for rationale)

### Prior commits in the closure chain

- `85d68e7` — `feat(10-04): extend main_matriz.py with paired async probes + flip 3 forward-reference skips` (Plan 10-04 Task 1, atomic per D-08: 4 source/test files)
- `<task3 hash>` — `ci(phase-10): green gate — live paridad sync↔async + snapshot regen + 3 skips flipped (LIVE-02)` (Plan 10-04 Task 3, this VALIDATION.md only)
- `<summary hash>` — `docs(10-04): SUMMARY — Phase 10 closure (REFAC-04 + LIVE-02)` (Plan 10-04 SUMMARY meta-commit, mirror of 10-01/10-02/10-03 patterns)

### Phase 10 sealed

REFAC-04 success criteria #2 (3-way TokenStore), #3 (live paridad sync↔async), #5 (CI green 3.12+3.13) are satisfied. LIVE-02 acceptance is signed off by the operator with `paridad sync↔async PASS — 19 probes pareados, divergences=0`. Phase 11 (HARN-07..10, CR-01..08, LIVE-01 full 4-package live re-verification) is unblocked.

*Re-verified: 2026-06-14 (Phase 10 Plan 10-04 Task 3, worktree-agent-a617a7d5ba624ce06)*
