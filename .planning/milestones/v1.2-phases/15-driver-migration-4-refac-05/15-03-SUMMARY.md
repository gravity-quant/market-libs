---
phase: 15-driver-migration-4-refac-05
plan: 03
subsystem: testing
tags: [higyrus-client, ast-guard, tdd, driver-migration, single-client, sync-async, httpx]

# Dependency graph
requires:
  - phase: 15-02
    provides: "AST-guard test idiom (dual ast.Name/ast.Attribute ctor walker, 1<=count<=2) + the RequestSpec-adaptation pattern for raw _request from a driver"
provides:
  - "main_higyrus.py migrated to single sync Client() + single async AsyncClient() threaded into all 19 probes + both query-capture helpers"
  - "verification/test_main_higyrus_uses_single_client_instance.py — AST guard capping client ctors at 2 (D-01/D-02)"
  - "The method-call-on-default site (_ensure_http_client) migrated to the threaded aclient (D-03)"
affects: [15-04, phase-17]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Driver single-Client invariant enforced by an AST gate (mirrors waves 1-2)"
    - "Raw _request from a driver: _raw_request_sync/_async helpers build RequestSpec + call instance Client._request + replicate the legacy module-shim raise-on-error + JSON-parse semantics"
    - "configure()-mutating probe (auth_401) keeps configure()/login() module-level by design; threaded client used only for the base_url read"

key-files:
  created:
    - verification/test_main_higyrus_uses_single_client_instance.py
  modified:
    - main_higyrus.py
    - packages/higyrus-client/tests/test_event_hooks_thread_safety.py

key-decisions:
  - "Raw _request shim adaptation (mirror of wave-2 iol): the 5 sync + 5 async raw higyrus_client.client._request / aio._request calls became two driver-local helpers (_raw_request_sync/_async) that build a RequestSpec, call the instance Client._request, raise via raise_for_response on non-2xx, and return None on 204/empty or resp.json() — replicating the legacy module shim exactly (instance _request returns the raw response un-raised)"
  - "probe_auth_401: configure()/login() stay module-level (D-03/T-15-05 — configure is out of scope and the probe deliberately mutates the default-client creds to force a 401); the threaded client is used only for the base_url read"
  - "Removed the `aio` import from the driver; kept `higyrus_client` (still used by probe_auth_401's configure()/login())"
  - "Rethreaded shared test_event_hooks_thread_safety.py (3 tests) to construct real Client()/AsyncClient() instances and pass them to the capture helpers, reading event_hooks from the instance's materialized httpx client — no-corruption invariant preserved"

patterns-established:
  - "Pattern 1: every sync probe_* takes a `client: Client`; every async probe_* takes an `aclient: AsyncClient`; no probe reaches _get_default()"
  - "Pattern 2: the method-call-on-default (_ensure_http_client) and the event-hook capture both operate on the threaded instance's own httpx client"

requirements-completed: [REFAC-05]

# Metrics
duration: 28min
completed: 2026-06-24
status: complete
---

# Phase 15 Plan 03: higyrus Driver Migration Summary

**main_higyrus.py now builds exactly one sync `Client()` and one async `AsyncClient()`, threaded into all 19 probes and both query-capture helpers — including the one method-call-on-default (`_ensure_http_client`) beyond the plain `_state` reads — guarded by a new RED-first AST test.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-06-24
- **Completed:** 2026-06-24
- **Tasks:** 2 (TDD: RED AST test + GREEN migration)
- **Files modified:** 3 (1 created, 2 migrated)

## Accomplishments
- Authored `verification/test_main_higyrus_uses_single_client_instance.py` as a RED-first AST guard (count 0 on un-migrated driver → fails; count 2 post-migration → passes). Matches both `ast.Name` (bare) and `ast.Attribute` (qualified) ctor spellings (D-05).
- Migrated `main_higyrus.py`: `main()` builds one `Client()`, `_async_main()` builds one `AsyncClient()`, both threaded as params into every `probe_*`. Eliminated all 21 `_get_default()` code sites (19 `_state` reads + the `_ensure_http_client` method-call + the schema-snapshot base_url read).
- D-03 method-call-on-default: `await aio._get_default()._ensure_http_client()` → `await aclient._ensure_http_client()` (count 1, verified). The sync capture helper's `higyrus_client.client._get_default()._ensure_http_client()` similarly became `client._ensure_http_client()`.
- Raw `_request` calls (5 sync + 5 async) adapted to instance `Client._request(RequestSpec)` via two driver-local helpers (`_raw_request_sync`/`_raw_request_async`) replicating the legacy module-shim raise+parse semantics.
- Rethreaded the shared `test_event_hooks_thread_safety.py` (3 tests) to construct real instances; no-corruption invariant preserved.
- ruff check + format + mypy strict green on `main_higyrus.py`; AST guards (4 drivers + bare-except walker) and the full higyrus package suite (160 tests) pass.

## Task Commits

1. **Task 1: RED — AST guard for single Client in main_higyrus.py** - `412e9c3` (test) — fails RED (count 0 < lower bound)
2. **Task 2: GREEN — thread single Client/AsyncClient through main_higyrus.py** - `e096d51` (feat) — AST guard passes (count 2)

_TDD: RED `test(...)` commit precedes GREEN `feat(...)` commit; no REFACTOR commit needed._

## Files Created/Modified
- `verification/test_main_higyrus_uses_single_client_instance.py` - AST-walker asserting `1 <= (Client|AsyncClient) ctor Calls <= 2` in main_higyrus.py; lower bound makes RED non-vacuous.
- `main_higyrus.py` - Single sync + single async client threaded into all 19 probes and both capture helpers; method-call-on-default migrated; raw `_request` adapted to `RequestSpec`; configure()/finding literals untouched.
- `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` - 3 tests rethreaded to construct real `Client()`/`AsyncClient()` and pass them to the capture helpers (the helpers' new signatures); reads `event_hooks` from the instance's materialized httpx client.

## Decisions Made
- **Raw `_request` adaptation (Rule 3, mirror of wave-2 iol):** The driver used the module-level `higyrus_client.client._request(method, path, params=...)` / `aio._request(...)` shims, which build a `RequestSpec`, call the instance `_request`, raise via `raise_for_response` on non-2xx, and return `None` on 204/empty else `resp.json()`. The instance `Client._request(RequestSpec)` returns the raw response **un-raised**, so a naive swap would change error-handling semantics. Two driver-local helpers (`_raw_request_sync`/`_raw_request_async`) replicate the shim exactly. `RequestSpec` and `raise_for_response` imported from `higyrus_client._core`.
- **probe_auth_401 keeps configure()/login() module-level:** This probe deliberately calls `higyrus_client.configure(password=bad)` then `higyrus_client.login()` on the **module default** to exercise the 401 path. Per D-03/T-15-05, `configure()` is out of scope and the bad-cred login must hit the default, not the threaded good-cred `client`. The threaded `client` is used only for the `base_url` read. Documented inline.
- **`aio` import removed:** After threading `AsyncClient`, no `aio.*` code references remain (only docstring prose + the `aio._request` finding-literal string at `:1756`, which is D-06 byte-stable). Removed to keep ruff/CI green. `higyrus_client` retained (probe_auth_401).
- **Shared thread-safety test rethreaded (Rule 1/3):** The capture helpers' signatures changed (now take a `Client`/`AsyncClient`), breaking 3 tests in `test_event_hooks_thread_safety.py`. Per predecessor-wave convention, they were rethreaded to construct real instances seeded with the same dummy token/base_url the conftest applies, preserving the asserted no-corruption invariant on the exact instance the helper mutates.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Raw `_request` signature mismatch under mypy strict**
- **Found during:** Task 2 (migration)
- **Issue:** Instance `Client._request` expects one `RequestSpec` arg (not positional `method, path, params`) and does not raise on error status (the module shim did). A naive swap would fail mypy strict and silently change error-handling.
- **Fix:** Added `_raw_request_sync`/`_raw_request_async` helpers building `RequestSpec`, calling the instance `_request`, replicating raise-on-error + JSON-parse. Imports `RequestSpec, raise_for_response` from `higyrus_client._core`.
- **Files modified:** main_higyrus.py
- **Verification:** `mypy --follow-imports=silent main_higyrus.py` clean; higyrus suite (160) green.
- **Committed in:** `e096d51` (Task 2)

**2. [Rule 3 - Blocking] Unused `aio` import after AsyncClient threading**
- **Found during:** Task 2 (migration)
- **Issue:** Threading `AsyncClient` removed all `aio.*` code references; the `aio` import became unused (ruff F401, CI-blocking).
- **Fix:** Removed `aio` from the `from higyrus_client import ...` line. Kept `higyrus_client` (probe_auth_401's configure/login).
- **Files modified:** main_higyrus.py
- **Verification:** `ruff check main_higyrus.py` — all checks passed.
- **Committed in:** `e096d51` (Task 2)

**3. [Rule 1 - Test rethread] Shared thread-safety test broke on new helper signatures**
- **Found during:** Task 2 (higyrus package suite)
- **Issue:** `test_event_hooks_thread_safety.py` called `_capture_sync_query_string`/`_capture_async_query_string` with the pre-migration signature (no client/aclient param) → `TypeError` in 3 tests.
- **Fix:** Rethreaded the 3 tests to construct real `Client()`/`AsyncClient()` (seeded with the conftest's dummy token/base_url), pass them to the helpers, and read `event_hooks` from each instance's materialized httpx client. No-corruption invariant preserved; added a `finally: await aclient.aclose()` to the async test for clean teardown.
- **Files modified:** packages/higyrus-client/tests/test_event_hooks_thread_safety.py
- **Verification:** higyrus package suite — 160 passed.
- **Committed in:** `e096d51` (Task 2)

---

**Total deviations:** 3 auto-fixed (Rule 3 ×2 blocking, Rule 1 ×1 shared-test rethread — all mandated by the plan's own CI-green criteria and the predecessor-wave convention). No scope creep — finding literals, probe names, and asserted invariants are byte-stable.

## Note on the PATTERNS.md reference
The plan's `<files_to_read>` and Task 2 `<read_first>` reference `15-PATTERNS.md` (line ranges for the higyrus recipe). **That file does not exist in the phase directory** (only `15-CONTEXT.md`, `15-DISCUSSION-LOG.md`, `15-LOC-ATTESTATION.md`, and the plans/summaries). Migration proceeded from the plan's own detailed Task-2 action block (which enumerates every site), the wave-2 `15-02-SUMMARY.md` (RequestSpec-adaptation precedent), and direct inspection of `main_higyrus.py` + the higyrus `client.py`/`aio.py` instance APIs. All sites the plan enumerated were located and migrated; the absence of PATTERNS.md did not block any step.

## Threat Flags
None — migration changes only client acquisition. No new network endpoints, auth paths, or trust-boundary surface introduced. T-15-01 (credentials), T-15-02 (≤2-ctor cap), T-15-05 (configure() untouched) all mitigated as planned (verified: `git diff` shows zero `configure()` body edits and zero finding-literal changes).

## Known Stubs
None.

## User Setup Required

**The per-package LIVE smoke (D-11, Criterion #4) is operator-deferred.** It requires higyrus credentials (`HIGYRUS_USER`, `HIGYRUS_PASSWORD`, `HIGYRUS_BASE_URL`) in `packages/higyrus-client/.env`, which is **ABSENT** in this environment. The live smoke (`uv run --package higyrus-client python main_higyrus.py`, confirming exit 0 + findings written) **CANNOT run here** and is **NOT a plan failure** — it is operator-driven, not the Phase 17 gate. All static work is complete: AST test (RED→GREEN), full driver migration, ruff + format + mypy strict, the 4-driver AST guards + bare-except walker, and the higyrus package suite (160 tests). No credentials were logged or committed.

## Next Phase Readiness
- higyrus driver migration complete and CI-green; wave-3 serial order (D-11) satisfied.
- Ready for 15-04 (remaining driver migration — matriz). The single-Client AST-guard idiom is now established for ámbito (w1), iol (w2), and higyrus (w3).
- Blocker for full phase sign-off: operator must run the higyrus LIVE smoke with real credentials (deferred, see User Setup Required).

---
*Phase: 15-driver-migration-4-refac-05*
*Completed: 2026-06-24*

## Self-Check: PASSED

- FOUND: verification/test_main_higyrus_uses_single_client_instance.py
- FOUND: main_higyrus.py (migrated)
- FOUND: packages/higyrus-client/tests/test_event_hooks_thread_safety.py (rethreaded)
- FOUND commit 412e9c3 (test — RED AST guard)
- FOUND commit e096d51 (feat — GREEN migration)
- aclient._ensure_http_client() count == 1 (method-call-on-default migrated)
- No _get_default() / aio. / higyrus_client.client. CODE sites remain (docstrings/finding-literals only)
- STATE.md / ROADMAP.md untouched (worktree mode — orchestrator owns those writes)
