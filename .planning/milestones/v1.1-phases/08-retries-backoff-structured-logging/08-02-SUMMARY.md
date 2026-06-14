---
phase: 08-retries-backoff-structured-logging
plan: 02
subsystem: ambito-financiero-client
tags: [phase-08, ambito, canary, atomic-commit, rely, log]
requires: [phase-07 _core.py extraction, phase-08-01 cross-cutting scaffolding]
provides:
  - ambito_financiero_client._transport.RetryTransport (sync)
  - ambito_financiero_client._atransport.AsyncRetryTransport (async)
  - ambito_financiero_client._logging.RedactingFilter + attach()
  - Client/AsyncClient/configure() extended with max_retries + http_client kwargs
  - Per-business-call request_id propagation via request.extensions
  - Structured DEBUG/WARNING/ERROR log records with canonical D-09 fields
affects:
  - packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py (NEW)
  - packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py (NEW)
  - packages/ambito-financiero-client/src/ambito_financiero_client/_logging.py (NEW)
  - packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py (attach _logging)
  - packages/ambito-financiero-client/src/ambito_financiero_client/_core.py (RequestSpec extended)
  - packages/ambito-financiero-client/src/ambito_financiero_client/client.py (Client + _request + configure)
  - packages/ambito-financiero-client/src/ambito_financiero_client/aio.py (AsyncClient + _request + configure)
  - packages/ambito-financiero-client/tests/test_client_class.py (slots assertion updated)
  - packages/ambito-financiero-client/tests/test_transport.py (NEW)
  - packages/ambito-financiero-client/tests/test_logging.py (NEW)
  - verification/snapshots/ambito-financiero-client-surface.txt
tech-stack:
  added:
    - "tenacity Retrying / AsyncRetrying loop wired into RetryTransport (httpx.HTTPTransport subclass)"
    - "wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0) — full-jitter backoff per D-08"
    - "logging.getLogger('ambito_financiero_client') + NullHandler + RedactingFilter per LOG-01 / LOG-02"
  patterns:
    - "RequestSpec.idempotent + endpoint_name flow through request.extensions to transport layer"
    - "Per-business-call request_id (uuid.uuid4().hex) generated in shell _request() pre-send (D-30)"
    - "Mutation gate at top of RetryTransport.handle_request: non-idempotent → pass-through (D-01)"
    - "max_retries=N → max_attempts=N+1 (anthropic/openai SDK semantics, D-19)"
    - "http_client=user_supplied used AS-IS without auto-wrapping (D-16 contract)"
key-files:
  created:
    - packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/_logging.py
    - packages/ambito-financiero-client/tests/test_transport.py
    - packages/ambito-financiero-client/tests/test_logging.py
  modified:
    - packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/_core.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/client.py
    - packages/ambito-financiero-client/src/ambito_financiero_client/aio.py
    - packages/ambito-financiero-client/tests/test_client_class.py
    - verification/snapshots/ambito-financiero-client-surface.txt
decisions:
  - "D-01 mutation gate via request.extensions['idempotent'] — applied at top of RetryTransport.handle_request"
  - "D-04 Retry-After cap 60s — _parse_retry_after handles delta-seconds + HTTP-date, time.sleep(min(delay, 60))"
  - "D-07 retry_on= locked set — _RETRYABLE_STATUS = {408, 409, 429, *range(500,600)}; _RETRYABLE_EXC = (ConnectError, ConnectTimeout, ReadTimeout)"
  - "D-08 full-jitter backoff — tenacity.wait_exponential_jitter(initial=1, max=30, exp_base=2, jitter=1)"
  - "D-15 + D-16 minimal public API extension — max_retries=2 + http_client=None on Client/AsyncClient/configure()"
  - "D-19 max_retries=0 disable — max_attempts <= 1 bypasses retry loop entirely"
  - "D-30 request_id generated once per business-call in shell _request(), propagated via extensions to transport"
  - "D-32 async cancellation respect — await asyncio.sleep for Retry-After honor, AsyncRetrying uses native asyncio.sleep"
  - "Intra-package coupling _atransport ← _transport for constants/sentinel/parsers — saves ~50 LOC duplication WITHIN ámbito; iol/higyrus/matriz will replicate the same intra-package import pattern"
  - "Reordered __init__.py — _logging.attach() runs BEFORE other imports + del cleanup (Pitfall 8 prevention)"
metrics:
  duration_minutes: 10
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 6
  test_count_baseline_ambito: 107
  test_count_after_ambito: 121
  new_ambito_unit_tests: 14
  completed_date: 2026-06-13
---

# Phase 08 Plan 02: ámbito canary — Retries + Structured Logging

**One-liner:** ámbito canary delivers Phase 8 end-to-end — `RetryTransport` (sync) + `AsyncRetryTransport` (async) + `RedactingFilter` per `_logging.py`, with `Client`/`AsyncClient`/`configure()` gaining `max_retries=2` + `http_client=None` kwargs and the shell `_request()` generating per-business-call UUID4 `request_id` propagated via `request.extensions`.

## Objective

Land the Phase 8 mechanical pattern in the simplest paquete (no auth, no token refresh, no account_id, no Risk API) so the pattern is mechanically verified before iol/higyrus/matriz replicate. Atomic per-package commit per D-21.

## Task Execution

### Task 1: Create _transport.py + _atransport.py + _logging.py + unit tests

- **`_transport.py` (179 LOC, NEW)** — `RetryTransport(httpx.HTTPTransport)` per RESEARCH §Pattern 1. Module-level constants `_RETRYABLE_EXC`, `_RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)})`, `_RETRY_AFTER_CAP_S = 60.0`, `_LOGGER_NAME = "ambito_financiero_client"`. Internal sentinel `_RetryableStatus(Exception)` carries `response` for D-05 exhaust-returns-last semantics. `_parse_retry_after()` handles RFC 9110 §10.2.3 delta-seconds AND HTTP-date via `parsedate_to_datetime`. Mutation gate at top + `max_attempts <= 1` bypass. WARNING per attempt with structured `extra={...}` carrying D-09 canonical fields. ERROR on terminal transport errors.

- **`_atransport.py` (139 LOC, NEW)** — `AsyncRetryTransport(httpx.AsyncHTTPTransport)` mirror. Imports `_RETRYABLE_EXC, _RETRY_AFTER_CAP_S, _RetryableStatus, _is_retryable_status, _parse_retry_after, _LOGGER_NAME` from `_transport.py` (intra-package coupling — saves ~50 LOC, ámbito constraint is per-PACKAGE not per-module). Uses `AsyncRetrying` + `async for attempt`, `await response.aread()`, `await asyncio.sleep(...)` for D-32 CancelledError propagation.

- **`_logging.py` (84 LOC, NEW)** — `RedactingFilter(logging.Filter)` + `attach()` per RESEARCH §Pattern 4. ámbito-baseline patterns: Bearer regex, URL-encoded password, JSON `"password":"..."` (forward-consistency baseline; iol/higyrus/matriz extend with package-specific patterns). `_REDACTION_MARKERS` tuple used to scan `record.__dict__` values. `attach()` idempotent — checks for existing `NullHandler` + `RedactingFilter` before adding.

- **`tests/test_transport.py` (153 LOC, NEW)** — 7 unit tests:
  - `test_non_idempotent_request_passes_through` — D-01 mutation gate
  - `test_idempotent_get_retries_on_503` — RELY-01 retry loop active
  - `test_idempotent_get_exhausts_and_returns_last_5xx` — D-05 exhaust returns last response
  - `test_retry_after_cap_60s` — D-04 Retry-After honored
  - `test_max_attempts_1_bypasses_loop` — D-19 bypass
  - `test_request_id_persists_in_extensions_across_attempts` — D-30 / Pitfall 9
  - `test_warning_log_contains_request_id_and_endpoint` — D-09 structured fields

- **`tests/test_logging.py` (95 LOC, NEW)** — 7 unit tests:
  - `test_attach_is_idempotent` — LOG-01 idempotency
  - `test_redact_bearer_token_in_msg` — LOG-02 Bearer redaction
  - `test_redact_password_urlencoded_in_msg` — LOG-02 password=
  - `test_redact_password_json_in_msg` — LOG-02 JSON password
  - `test_filter_always_returns_true` — record never dropped
  - `test_record_dict_scan_redacts_extra_field` — extra={} scan
  - `test_redact_bearer_in_tuple_args` — record.args scrub

All 14 new tests pass in isolation; ruff + mypy strict clean.

### Task 2: Extend _core.py + client.py + aio.py + __init__.py + snapshot (atomic per D-21)

- **`_core.py` extension (+8 LOC)** — `RequestSpec` gains `idempotent: bool = False` (forward-decl from Phase 7 D-13 now MATERIALIZED) + `endpoint_name: str = ""` (NEW). `build_get_dollar_banco_nacion_request` sets `idempotent=True` + `endpoint_name="get_dollar_banco_nacion"`. ámbito has only 1 endpoint, all GET, no auth flow — single builder updated.

- **`client.py` extension (+28 LOC)** — Imports: `uuid` + `_transport`. `Client.__slots__` extended to `("_max_retries", "_state")`. `__init__` signature gains `max_retries: int = 2` + `http_client: httpx.Client | None = None` (D-15 / D-16). `_ensure_http_client` wraps `httpx.Client(transport=_transport.RetryTransport(max_attempts=self._max_retries + 1))`. `_request()` migrated from `client.request(...)` to `client.build_request(...) + send(...)` so `request.extensions` can be set pre-send (per RESEARCH A7). NO 401 re-auth branch (ámbito no auth — D-02 N/A). `configure()` gains the 2 carry-forward kwargs.

- **`aio.py` extension (+28 LOC)** — Mirror sync deltas. Imports: `uuid` + `_atransport`. `AsyncClient.__slots__` extended. `__init__` signature mirror. `_ensure_http_client` wraps `httpx.AsyncClient(transport=_atransport.AsyncRetryTransport(max_attempts=self._max_retries + 1))`. `_request()` migrated to `build_request + await http.send(req)`. `configure()` mirror.

- **`__init__.py` extension (+8 LOC)** — Inserted `_logging.attach()` block at TOP of file (before other imports) with `del _logging_attach` cleanup. Reorder required because `attach()` should run before any heavy `client.py` import that could emit log records during module init. Subsequent imports tagged `# noqa: E402`.

- **`tests/test_client_class.py` (1 line modified)** — `test_async_client_has_no_client_lock_attribute` updated: `__slots__` no longer equals `("_state",)` — now `{"_state", "_max_retries"}` per D-15. Test invariant preserved (no `_client_lock` for ámbito B7 divergence).

- **`verification/snapshots/ambito-financiero-client-surface.txt` (3 lines modified)** — `Client.__init__`, `AsyncClient.__init__`, `configure()` signatures extended with the 2 new kwargs. Verified by `verification/regen_snapshots.py` producing identical output.

## LOC delta vs Phase 7 baseline

```
_transport.py:    0 → 179 (NEW)
_atransport.py:   0 → 139 (NEW)
_logging.py:      0 →  84 (NEW)
_core.py:       148 → 158 (+ 6.8%; RequestSpec.idempotent + endpoint_name + 1 builder flipped)
client.py:      190 → 230 (+21%; 2 kwargs + uuid + RetryTransport wire + extensions + configure)
aio.py:         195 → 235 (+21%; same mirror in async)
__init__.py:     47 →  55 (+17%; _logging.attach + del + noqa)
tests/test_transport.py: 0 → 153 (NEW; 7 unit tests)
tests/test_logging.py:   0 →  95 (NEW; 7 unit tests)
```

## Snapshot diff

```diff
-AsyncClient : class : (*, base_url: 'str | None' = None, user_agent: 'str | None' = None) -> 'None'
-Client : class : (*, base_url: 'str | None' = None, user_agent: 'str | None' = None) -> 'None'
-configure : function : (*, base_url: 'str | None' = None, user_agent: 'str | None' = None) -> 'None'
+AsyncClient : class : (*, base_url: 'str | None' = None, user_agent: 'str | None' = None, max_retries: 'int' = 2, http_client: 'httpx.AsyncClient | None' = None) -> 'None'
+Client : class : (*, base_url: 'str | None' = None, user_agent: 'str | None' = None, max_retries: 'int' = 2, http_client: 'httpx.Client | None' = None) -> 'None'
+configure : function : (*, base_url: 'str | None' = None, user_agent: 'str | None' = None, max_retries: 'int' = 2, http_client: 'httpx.Client | None' = None) -> 'None'
```

Exactly the 2 new kwargs on the 3 signatures per D-28; no other entries added/removed (Pitfall 8 prevention — `_logging`/`_transport`/`_atransport` NOT re-exported).

## Cross-cutting guard tests — ámbito branches

| Test | ámbito branch | After Plan 2 |
|------|---------------|--------------|
| `test_retry_mutation_gate.py::test_idempotent_get_retries_on_503` | not parametrized for ámbito (only iol/higyrus/matriz) | N/A |
| `test_retry_mutation_gate.py::test_mutating_call_never_retries_against_503` | not parametrized for ámbito (no mutating endpoints) | N/A |
| `test_logging_root_unchanged.py` | global; covers all 4 paquetes | **GREEN** (NullHandler attached to `ambito_financiero_client` logger only) |
| `test_logging_no_token_leak.py[ambito_financiero_client]` | GREEN | **GREEN** (no SECRET in any record after configure(base_url=...) + get_dollar_banco_nacion) |
| `test_async_cancellation.py[ambito_financiero_client]` | RED → **GREEN** | **GREEN** (AsyncRetryTransport + AsyncRetrying + await asyncio.sleep → TimeoutError in 0.5s) |
| `test_retry_after_cap.py` | uses iol_client; ámbito not exercised | RED (still — Plan 3 iol territory) |
| `test_public_surface.py[ambito_financiero_client]` | snapshot updated | **GREEN** |

ámbito-specific Wave 1 RED guards turned GREEN: 1 (async cancellation). Plans 3/4/5 turn the remaining 13 RED guards for iol/higyrus/matriz.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 — Bug] `__init__.py` import order — `_logging.attach()` must run BEFORE other imports**

- **Found during:** Task 2 — ruff `I001` import order rule failed.
- **Investigation:** Placing `_logging.attach()` AFTER the `from ambito_financiero_client.client import Client, ...` would mean any log records emitted during the import of `client.py` (e.g., from `load_dotenv()` chain or `httpx` warnings) bypass the `RedactingFilter`.
- **Fix applied:** Reordered `__init__.py` to attach the logger at the TOP, before `client.py` / `aio.py` / `exceptions.py` imports. Subsequent imports annotated `# noqa: E402` (module-level import not at top) which is the documented pattern for the library logger convention.
- **Trade-off acknowledged:** The `# noqa: E402` is intentional and matches the "Configuring logging for a library" cookbook recommendation.

**2. [Rule 1 — Bug-adjacent] `test_client_class.py::test_async_client_has_no_client_lock_attribute` asserted `__slots__ == ("_state",)`**

- **Found during:** Task 2 — `test_async_client_has_no_client_lock_attribute` failed after `__slots__` gained `_max_retries`.
- **Root cause:** Phase 6 invariant test pinned the exact tuple. Phase 8 D-15 (max_retries kwarg) requires `_max_retries` in slots (else AttributeError at assignment).
- **Fix applied:** Updated the assertion to verify the SET equality `{"_state", "_max_retries"}` while preserving the original B7 invariant (`"_client_lock" not in __slots__`). The B7 divergence rationale (ámbito has no async token refresh lock) is unaffected.
- **Files modified:** `packages/ambito-financiero-client/tests/test_client_class.py` (1 test, 2 line change).

**3. [Documented — not a deviation] `verification/test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` fails pre-commit**

- **Found during:** Full verification suite run.
- **Cause:** The test runs `verification/regen_snapshots.py` and then `git diff --exit-code verification/snapshots/`. Pre-commit, the diff is non-empty because the snapshot was edited but not committed.
- **Resolution:** This is a temporal artifact, not a regression. Verified that `regen_snapshots.py` produces EXACTLY the edited snapshot (same byte-for-byte). After the atomic commit lands, the diff is empty and the test passes. No code change needed.

### Other deviations

**4. [Sub-optimal but acceptable] Intra-package import in `_atransport.py`**

- The CONTEXT.md "Claude's Discretion" section (line 164) allowed either approach. I chose **import** rather than verbatim **duplication** of `_RETRYABLE_EXC`, `_RETRYABLE_STATUS`, `_RETRY_AFTER_CAP_S`, `_RetryableStatus`, `_parse_retry_after`, `_is_retryable_status` between `_transport.py` and `_atransport.py`.
- **Rationale:** "No shared internals between packages" applies at the PACKAGE boundary. Within ámbito, intra-package coupling between sync/async transports is acceptable and reduces ~50 LOC duplication. iol/higyrus/matriz will replicate the SAME intra-package import pattern.
- **Risk:** If `_atransport.py` ever needs to change a constant independently from `_transport.py`, the coupling must be broken first. Low risk — the constants are RFC-locked (status codes) or D-locked (cap, logger name).

## Verification

- 121 ámbito tests passing (107 baseline + 14 new transport/logging unit tests); 1 deselected (driver invariants — unchanged); 0 failures, 0 errors.
- `uv run ruff check packages/ambito-financiero-client/ verification/` — exits 0.
- `uv run ruff format --check packages/ambito-financiero-client/` — exits 0.
- `uv run mypy --strict packages/ambito-financiero-client/` — Success: no issues found in 28 source files.
- `uv run lint-imports` — Contracts: 4 kept, 0 broken (ámbito `_core` STILL does not import `_transport`/`_atransport`/`client`/`aio`/`_logging`).
- `verification/test_public_surface.py[ambito_financiero_client]` — PASSED (snapshot reflects 2 new kwargs).
- Full suite (`packages/ + verification/`): 546 passed + 3 skipped + 14 failed (all 14 are documented Plan 1 RED guards for iol/higyrus/matriz pending Plans 3-5; baseline was 532 + 3 + 14 → +14 ámbito unit tests).

## Self-Check: PASSED

**Files created (verified via test -f):**
- `packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py` — FOUND
- `packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py` — FOUND
- `packages/ambito-financiero-client/src/ambito_financiero_client/_logging.py` — FOUND
- `packages/ambito-financiero-client/tests/test_transport.py` — FOUND
- `packages/ambito-financiero-client/tests/test_logging.py` — FOUND
- `.planning/phases/08-retries-backoff-structured-logging/08-02-SUMMARY.md` — FOUND (this file)

**Files modified (verified via git status):**
- `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py` — VERIFIED
- `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` — VERIFIED
- `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` — VERIFIED
- `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` — VERIFIED
- `packages/ambito-financiero-client/tests/test_client_class.py` — VERIFIED
- `verification/snapshots/ambito-financiero-client-surface.txt` — VERIFIED

ámbito canary established — pattern verified mechanically for Plan 3 (iol auth-flow) replication.
