---
phase: 23-verificaci-n-en-vivo-contra-develop-fixes
plan: 01
subsystem: testing
tags: [verification, market-data-client, auth0, httpx, ast-guard, safemodel-diff, schema-snapshot]

# Dependency graph
requires:
  - phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
    provides: market_data_client Auth0 client_credentials auth + sync/async shells + retry transport
  - phase: 21-market-data-lectura-modelos
    provides: get_market_data / get_latest / get_latest_batch + MarketDataSnapshot/Entry models + received_at stamp
  - phase: 22-instruments-symbols-read-calendar-read-modelos
    provides: get_instruments/segments/symbols/calendar/calendar_config + 5 reference SafeModels
provides:
  - "main_market_data.py — 6th live-verification driver exercising all 10 endpoint methods on sync + async surfaces"
  - "AST single-Client guard verification/test_main_market_data_uses_single_client_instance.py (1<=ctor<=2)"
  - "market-data-client appended to main_verify.py._DRIVERS (aggregate runner covers 6 drivers)"
  - "Bootstrapped .planning/verification/market-data-client-findings.md + schemas/market-data-client/ dir"
affects: [23-02, live-verification, cycle-closure, wave-2-live-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Driver apparatus mirrors main_ambito_financiero.py: ProbeResult + _next_fid + per-probe D-09 exception ladder + ONE Client()/ONE AsyncClient() threaded into probes"
    - "SHAPE detection on RAW payload via client._request(spec)+.json() BEFORE from_api coercion, diffed with diff_safemodel_bidirectional"
    - "received_at excluded from model-only SHAPE diff (client-stamped, never on wire — D-01)"
    - "Auth-fail probe exercises AUTH classification deterministically offline via synthetic 401 + _core.raise_for_response"
    - "Param-encoding probe asserts falsy-preservation offline via _core.build_instruments_request (no HTTP)"

key-files:
  created:
    - main_market_data.py
    - verification/test_main_market_data_uses_single_client_instance.py
    - .planning/verification/market-data-client-findings.md
    - .planning/verification/schemas/market-data-client/.gitkeep
  modified:
    - main_verify.py

key-decisions:
  - "No --live flag (D-01): offline/skip split realized by require_env early-return; preserves main_verify.py _ENV_SKIP + flag-less subprocess contract"
  - "Auth-fail + param-encoding probes are offline-deterministic (synthetic 401 mapping / builder-only) so they exercise the AUTH/PARAM classes without depending on a live auth failure or market state"
  - "Sync↔async parity anchored on segments (stable reference-data), not on live market-data (which shifts between calls) — avoids false SYNC-ASYNC-DRIFT"
  - "Schemas dir bootstrapped with .gitkeep (no live JSON producible offline; Wave 2 23-02 populates real write-once snapshots)"

patterns-established:
  - "6th driver consistent with the existing 5; single-Client AST guard is the merge-blocking invariant"
  - "Per-probe exception ladder: package exceptions → httpx.ConnectError/Timeout (NO-DATA) → broad Exception (ERROR-MAP)"

requirements-completed: [LIVE-MD-01]

# Metrics
duration: 8min
completed: 2026-07-30
status: complete
---

# Phase 23 Plan 01: market-data-client live-verification driver + harness integration Summary

**Six-th live-verification driver `main_market_data.py` exercising all 10 endpoint methods on both sync `Client` and async `AsyncClient` with Auth0 client-credentials, SHAPE-diff over the 7 SafeModels, param-encoding/no-data/auth-fail/parity probes, plus the AST single-Client guard and `_DRIVERS` append — offline-safe (require_env SKIP) and network-safe (D-09 per-probe catch).**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-30T20:01:03Z
- **Completed:** 2026-07-30T20:09:50Z
- **Tasks:** 3
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments
- `main_market_data.py` (941 lines): env-gate on the four Auth0 vars → `sys.exit(0)` clean SKIP (D-01); ONE `Client()` in `main()` + ONE `AsyncClient()` in `_async_main()` threaded into every probe (D-02); the full read surface (health + market-data + reference) on both surfaces (D-03).
- Coverage per D-04: happy-path, SHAPE-diff (all 7 SafeModels via `diff_safemodel_bidirectional` on raw pre-`from_api` payloads), param-encoding (falsy bool filters preserved: `offset=0` kept, `subscribed=None` dropped), no-data (empty → NO-DATA), auth-fail (401 → `MarketDataAuthError` → AUTH), sync↔async parity on segments (mismatch → SYNC-ASYNC-DRIFT), and write-once schema snapshots (DRIFT-01).
- Four D-08 harness artifacts landed: driver, AST guard (green), `_DRIVERS` append, bootstrapped findings file (+ schemas dir).
- D-09 honored: every probe catches broad `Exception` and classifies `httpx.ConnectError`/`ConnectTimeout` as NO-DATA so an unreachable develop or closed-market empty never flips `main_verify.py` to FAILED.

## Task Commits

Each task was committed atomically:

1. **Task 1: Driver skeleton + env-gate + single-Client orchestration + health probes** - `6527076` (feat)
2. **Task 2: Market-data + reference probes, SHAPE diff, param-encoding, no-data, schema snapshot** - `9d44508` (feat)
3. **Task 3: AST single-Client guard + main_verify.py _DRIVERS append** - `df2aba7` (test)

## Files Created/Modified
- `main_market_data.py` - Live-verification driver: `_next_fid`, `ProbeResult`, `_finding_for_exc` (D-09 ladder), `_write_schema_snapshot` (DRIFT-01 write-once), `_emit_shape` (SHAPE diff), sync+async probe families for all 10 endpoints, param-encoding/no-data/auth-fail/parity probes, `_async_main`, `main` with require_env gate.
- `verification/test_main_market_data_uses_single_client_instance.py` - AST guard asserting `1 <= (Client|AsyncClient) ctor calls <= 2` (mechanical port of the ambito guard).
- `main_verify.py` - `_DRIVERS` extended with `("market-data-client", "main_market_data.py")`.
- `.planning/verification/market-data-client-findings.md` - Bootstrapped findings skeleton (tool-generated by `write_findings`).
- `.planning/verification/schemas/market-data-client/.gitkeep` - Placeholder so the write-once schema-snapshot dir is a committable artifact (real JSON envelopes land in Wave 2).

## Decisions Made
- **No `--live` flag (D-01):** the offline/skip split is the `require_env` early-return; a flag would break `main_verify.py:41` `_ENV_SKIP` classification and the flag-less subprocess invocation.
- **Offline-deterministic AUTH + PARAM probes:** auth-fail uses a synthetic `httpx.Response(401)` through `_core.raise_for_response` (asserts it maps to `MarketDataAuthError`); param-encoding inspects `_core.build_instruments_request(...).params` with no HTTP. Both exercise their finding classes without depending on a live auth failure or market state.
- **Parity anchored on segments** (stable reference data) rather than live market-data, which changes between calls and would produce spurious SYNC-ASYNC-DRIFT findings.
- **`received_at` excluded from the model-only SHAPE diff** — it is client-stamped (D-01), never on the wire, so flagging it would be a guaranteed false SHAPE finding.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1 verify command mis-detects async functions**
- **Found during:** Task 1 (skeleton verification)
- **Issue:** The plan's Task 1 `<automated>` verify walks `ast.FunctionDef` only; `_async_main` is an `ast.AsyncFunctionDef`, so the `{'main','_async_main','_next_fid'} <= names` assertion failed even though `_async_main` is correctly defined.
- **Fix:** Ran an equivalent corrected check that also collects `ast.AsyncFunctionDef` (result: `ctors=2`, all three functions present). The true merge gate — the Task 3 AST guard (ctor count only) — passes green. Driver source unchanged for this item.
- **Files modified:** none (verification-command limitation only)
- **Verification:** corrected AST walk + Task 3 pytest guard both pass.
- **Committed in:** n/a (no source change)

**2. [Rule 3 - Blocking] `uv run mypy` transitive import errors in an unsynced env**
- **Found during:** Task 1 (mypy verification)
- **Issue:** `uv run --package market-data-client mypy main_market_data.py` reported `matriz_client`/submodule import-not-found from `verification/mutation_gate.py` and (for ambito) `ambito_financiero_client.client` — because that env lacked the sibling workspace packages. This is a pre-existing environment condition (the existing ambito driver hits the same), not a fault of the new file.
- **Fix:** Used the canonical CI invocation `uv run mypy` (global, all 51 src files, workspace synced) → `Success: no issues found`.
- **Files modified:** none
- **Verification:** `uv run mypy` clean; `uv run --all-packages mypy main_market_data.py` also clean.
- **Committed in:** n/a (no source change)

**3. [Rule 2 - Missing Critical] Parity probe lacked exception isolation**
- **Found during:** Task 2 (probe wiring)
- **Issue:** `probe_parity` did the id-comparison outside a `try/except`, so a malformed model could theoretically propagate an uncaught exception (violating the D-09 "every probe catches" invariant and Task 2 acceptance).
- **Fix:** Wrapped the `marketSegmentId` extraction in `try/except Exception` routed through `_finding_for_exc(surface="both")`.
- **Files modified:** main_market_data.py
- **Verification:** ruff/mypy clean; probe body now contains `except Exception`.
- **Committed in:** `9d44508` (Task 2 commit)

---

**Total deviations:** 3 (2 verification-command/environment limitations with no source change, 1 missing-critical source fix)
**Impact on plan:** No scope creep. The two verification-command items are limitations of the plan's `<automated>` snippets (async-detection + unsynced-env transitive imports) resolved by equivalent canonical checks; the parity fix hardens D-09 compliance.

## Issues Encountered
- The findings-file header renders `# Findings: market-data-client-client` because `new_findings` appends `-client` to the passed pkg slug (`market-data-client`). This is the established harness convention shared by all packages (e.g. `ambito-financiero-client-client`) — left as-is for consistency, not a market-data-specific defect.

## Deferred / Wave 2 (23-02) Notes
- **This plan is offline apparatus only.** No live Auth0 sweep was run (no develop creds in this worktree). The live probe execution, in-cycle `models.py`/`_core.py` divergence fixes, mocked pytest-httpx regressions (D-07 `regression=` links), and `verify_cycle_closure("market-data-client")` PASS gate are Wave 2 (Plan 02), not part of 23-01.
- Real write-once schema-snapshot JSON envelopes under `.planning/verification/schemas/market-data-client/` are produced by the first live run (Wave 2); the dir currently holds only `.gitkeep`.
- `_SAMPLE_SYMBOLS = ["GGAL"]` and `_NO_DATA_PREFIX` are placeholders to be reconciled against real develop payloads in Wave 2.

## Next Phase Readiness
- Apparatus complete and green: `uv run python main_verify.py` now includes market-data-client as the 6th driver; with creds absent it classifies SKIPPED (not FAILED).
- Ready for Wave 2 (23-02) live sweep + in-cycle fixes + cycle closure once Auth0 develop credentials are provided (see plan `user_setup`).

## Self-Check: PASSED

- Files: all 5 present (driver, AST guard, findings.md, schemas/.gitkeep, SUMMARY).
- Commits: `6527076`, `9d44508`, `df2aba7` all present in git history.
- Verification: AST guard pytest green, ruff check + format clean, `uv run mypy` Success (51 files), SKIP line matches `^SKIPPED market-data-client: missing` and exits 0, `_DRIVERS` contains the market-data-client tuple.

---
*Phase: 23-verificaci-n-en-vivo-contra-develop-fixes*
*Completed: 2026-07-30*
