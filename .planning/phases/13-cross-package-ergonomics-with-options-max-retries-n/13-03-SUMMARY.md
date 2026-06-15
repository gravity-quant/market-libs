---
phase: 13-cross-package-ergonomics-with-options-max-retries-n
plan: 03
subsystem: higyrus-client
tags: [with_options, view, is_view, max_attempts, ergonomics, erg-01, higyrus, auth, redacting_filter]

# Dependency graph
requires:
  - phase: 08-retries-backoff-structured-logging
    provides: "RetryTransport + AsyncRetryTransport reading req.extensions['max_attempts'] (extended by Phase 13 Plan 1); _validate_max_retries helper (WR-06); RedactingFilter LOG-02 + attach() (anchor for T-13-03-01 mitigation); _send_auth_request shape with extensions block (D-29); D-03 login marked idempotent=True so view's max_attempts override is honored on auth-flow per D-T6"
  - phase: 13-cross-package-ergonomics-with-options-max-retries-n
    plan: 01
    provides: "RetryTransport + AsyncRetryTransport actually read req.extensions['max_attempts'] (sync + async, 4 packages); verification/test_with_options.py with 13 cross-cutting RED-in-HEAD tests"
  - phase: 13-cross-package-ergonomics-with-options-max-retries-n
    plan: 02
    provides: "ámbito reference implementation of with_options view shape (D-V1/D-V2/D-V3); per-package mocked-test patterns to mirror; single-line guard pattern with noqa: E701 + fmt: skip; snapshot-no-diff result documented (D-V5 discrepancy)"
provides:
  - "higyrus_client.Client.with_options(*, max_retries: int) -> Client — view returns fresh Client sharing _state (token + refresh state via token_expires_at + account_id propagation), with overridden _max_retries and _is_view=True"
  - "higyrus_client.AsyncClient.with_options(*, max_retries: int) -> AsyncClient — async mirror; shares parent's _client_lock so double-checked locking goes through the same asyncio.Lock"
  - "_is_view slot on both Client and AsyncClient __slots__ (alphabetically sorted)"
  - "Lifecycle no-op guard: close() / aclose() / __exit__ / __aexit__ short-circuit when _is_view=True (anti-Pitfall 13 — parent's TCP pool + cached token intact)"
  - "Shell _request() / async _request() set req.extensions['max_attempts'] = self._max_retries + 1 uniformly (parent or view, no shell branches)"
  - "Shell _send_auth_request() / async _send_auth_request() ALSO set req.extensions['max_attempts'] (per D-T6 — auth-flow requests are idempotent=True per Phase 8 D-03, so view's per-call cap MUST apply to login/refresh)"
  - "__repr__ prefixes 'view of ' when _is_view=True; existing D-18 password/token redaction stays intact"
  - "Per-package mocked tests: 6 sync + 6 async, INCLUDING new RedactingFilter integrity test (T-13-03-01 mitigation; sync + async). Total higyrus suite: 147 → 159 tests."
affects:
  - "Plan 4 (with_options matriz + D-T1..T6): same view shape + new field _state.client_max_retries (matriz only); auth_basic Risk API shell uses same extension passthrough; matriz adds CRITICAL mutation-gate test (Anti-Pitfall 14, money-on-the-line)"
  - "Plan 5 (with_options iol): same shape + 401 re-auth path in shell preserved; green-gate consolidation at end of phase"
  - "Phase 15 driver migration (REFAC-05): main_higyrus.py can opt into client.with_options(max_retries=N) ergonomics — see Forward References"
  - "Phase 17 LIVE-03: live re-verification ensures with_options on higyrus does not regress observable wire behavior (esp. token + refresh + account_id propagation)"

# Tech tracking
tech-stack:
  added: []  # No new runtime deps
  patterns:
    - "View constructor copied verbatim from Plan 13-02 ámbito reference impl: type(self).__new__(type(self)) + share _state + override _max_retries + flag _is_view=True"
    - "Single-line guard `if getattr(self, \"_is_view\", False): return  # noqa: E701  # fmt: skip` — Plan 13-02 precedent; placed at top of close() AND aclose()"
    - "Uniform extension set in shell: req.extensions['max_attempts'] = self._max_retries + 1 — parent or view both set this (no branching)"
    - "AUTH-FLOW EXTENSION (higyrus delta vs ámbito): _send_auth_request ALSO sets max_attempts extension because login is idempotent=True (Phase 8 D-03). D-T6 in CONTEXT.md formalizes this — view's per-call cap MUST apply to auth-flow calls. The cross-cutting test_with_options_max_attempts_extension_honored validates this end-to-end."
    - "Async _client_lock sharing: view inherits parent's _client_lock so first-call double-checked locking on view goes through the SAME asyncio.Lock as the parent (no second lock per view; preserves the per-loop binding established by the parent)"
    - "RedactingFilter integrity test pattern (NEW for higyrus): _attach_higyrus_logger() before exercising the view's retry path; assert >=1 WARNING records (non-vacuous) AND assert sentinel literal absent from record.getMessage(), record.args, record.__dict__ values"

key-files:
  created: []  # All output via existing files
  modified:
    - "packages/higyrus-client/src/higyrus_client/client.py (+89 / -2): Client.with_options + _is_view slot + __init__ default + close() no-op guard + __repr__ prefix + _request() extension set + _send_auth_request() extension set (D-T6)"
    - "packages/higyrus-client/src/higyrus_client/aio.py (+67 / -4): AsyncClient.with_options + _is_view slot + __init__ default + aclose() no-op guard + __repr__ prefix + async _request() extension set + async _send_auth_request() extension set"
    - "packages/higyrus-client/tests/test_client.py (+203): 6 sync mocked tests for view shape including NEW RedactingFilter integrity test"
    - "packages/higyrus-client/tests/test_async_client.py (+169): 6 async mocked tests for view shape including NEW async RedactingFilter integrity test"

key-decisions:
  - "Uniform extension set in BOTH _request and _send_auth_request shells (sync + async). Per D-T6: 'view's extensions[\"max_attempts\"] SÍ se honra para esos calls' because login/refresh are idempotent=True (Phase 8 D-03). Without this, the view's bumped retry cap would NOT apply to auth-flow calls, breaking the cross-cutting test_with_options_max_attempts_extension_honored when it triggers a stale-token re-auth path."
  - "Async view shares parent's _client_lock (view._client_lock = self._client_lock). The lock is per-loop; the view runs on the same loop as the parent (cross-loop usage is unsupported per Phase 6 + 7 invariant). Sharing prevents two competing locks racing to create the http_client (defense in depth even though the double-check inside _ensure_http_client would catch the race anyway)."
  - "RedactingFilter integrity test is NEW for higyrus (sync + async) — ámbito Plan 13-02 did not have this test because ámbito has no auth/token surface. Higyrus has Bearer + JSON password/token + cuit query patterns (per _logging.py module docstring); the new test asserts none of these leak under a view's retry path."
  - "Non-vacuous WARNING-records assertion BEFORE the sentinel-absent assertion (per CR-02 pattern from verification/test_logging_no_token_leak.py:194). If max_retries=2 view triggers but produces zero WARNINGs, the absence-of-sentinel assertion is vacuously true; the explicit `assert warning_records` catches the misconfiguration."
  - "Snapshot regen produced ZERO body diff across all 4 packages (expected per D-V5 discrepancy documented in Plan 13-02 Summary). The snapshot enumerator only walks __all__ at module level; with_options is a method on Client/AsyncClient, not a module-level export. Snapshot test stays GREEN as a __all__-drift regression net; method addition is invisible to the snapshot."
  - "Type annotation for max_retries=1.5 still needs # type: ignore[arg-type] (float is NOT a subclass of int). Type annotation for max_retries=True does NOT need it (bool IS a subclass of int). Mypy reports 'unused type: ignore' on the True call if the comment is present. Followed Plan 13-02 precedent."

requirements-completed: []  # ERG-01 spans Plans 2-5; reported by orchestrator after Plan 5 lands the iol piece.

# Metrics
duration: ~10min (excluding the 3-minute cross-cutting test that exercises 11 wire retries with full-jitter backoff)
completed: 2026-06-15
---

# Phase 13 Plan 03: with_options higyrus Summary

**Phase 13 second wave: `higyrus_client.Client.with_options(*, max_retries)` + `AsyncClient.with_options` land. View shares `_state` (token + refresh state via `token_expires_at` + `account_id`) and parent's `httpx.Client` (no re-auth, no TCP pool fragmentation — anti-Pitfall 13). Per D-T6, the view's `extensions["max_attempts"]` flows through BOTH `_request()` AND `_send_auth_request()` because login/refresh are `idempotent=True` (Phase 8 D-03). RedactingFilter (Phase 8 LOG-02) integrity test added (sync + async) — view's retry log under 503 does NOT leak the token sentinel. 3 of 4 cross-cutting tests for [higyrus_client] parametrize row flip RED → GREEN.**

## Performance

- **Duration:** ~10 min (excluding the 3-minute wall-clock cross-cutting `test_with_options_max_attempts_extension_honored[higyrus_client]` which exercises 11 wire retries with full-jitter exponential backoff)
- **Tasks:** 2 (atomic per-task commits)
- **Files modified:** 4 (2 src + 2 tests)
- **Files created:** 0
- **LOC delta:** +528 / -6 across all 4 files

## Accomplishments

### Sync client (Task 1 — `client.py`)

- **`Client.__slots__`** extended to `("_is_view", "_max_retries", "_state")` (alphabetized, mirroring Plan 13-02 ámbito).
- **`Client.__init__`** sets `self._is_view = False` after the existing `self._max_retries = max_retries`. Docstring explains shared-state implications (token + refresh + http_client all flow through `_state`).
- **`Client.close()`** short-circuits when `_is_view=True` via the single-line guard `if getattr(self, "_is_view", False): return  # noqa: E701  # fmt: skip`. Identical pattern to Plan 13-02. `__exit__` calls `close()` so the guard covers it automatically (no change to `__exit__` body needed).
- **New `Client.with_options(*, max_retries: int) -> Self`** method placed between `_ensure_http_client` and `_send_auth_request`:
  - `_validate_max_retries(max_retries)` is the FIRST call (WR-06 carry-forward — rejects bool, negative int, non-int BEFORE view construction).
  - View constructed via `type(self).__new__(type(self))` — fresh `Client` instance with no `__init__` invocation.
  - `view._state = self._state` — SHARES `_state` (including `token`, `token_expires_at`, `account_id` propagation).
  - `view._max_retries = max_retries`, `view._is_view = True`.
  - Docstring (~55 lines) covers: shared-state semantics with explicit mention of `token`/`refresh state via token_expires_at`/`account_id`, lifecycle no-op, D-V2 chaining inner-wins, D-V4 configure-invariance, D-T6 auth-flow override, mutation gate authority.
- **`Client.__repr__`** prefixes `"view of "` when `_is_view=True` (Claude's Discretion from Plan 13-02; carried forward). The existing D-18 redaction of `password` and `token` stays intact — view's repr shows `'***'` for both.
- **`Client._request()` shell** adds `req.extensions["max_attempts"] = self._max_retries + 1` AFTER the existing `endpoint_name` extension. Placed BEFORE the optional `account_id` set so uniform regardless of whether `spec.account_id` is set.
- **`Client._send_auth_request()` shell** ALSO sets `req.extensions["max_attempts"] = self._max_retries + 1` (HIGYRUS DELTA vs ámbito Plan 13-02). Per D-T6 in CONTEXT.md: auth-flow requests carry `idempotent=True` (Phase 8 D-03), so the view's per-call cap MUST apply to `login` and any future refresh path too. Without this, a view created with `max_retries=10` would silently fall back to the parent's `_max_retries` on auth-flow calls, breaking the cross-cutting `test_with_options_max_attempts_extension_honored` test.

### Async client (Task 1 — `aio.py`)

Async mirror of sync — zero divergence sync↔async surface (D-V3 parity):

- **`AsyncClient.__slots__`** extended to `("_client_lock", "_is_view", "_max_retries", "_state")`.
- **`AsyncClient.__init__`** sets `self._is_view = False`.
- **`AsyncClient.aclose()`** short-circuits when `_is_view=True` via the same single-line guard pattern. `__aexit__` calls `aclose()` so the guard covers it.
- **New `AsyncClient.with_options(*, max_retries: int) -> Self`** — sync method even on the async class (returns view in-memory; the subsequent endpoint call is async). Same body as sync, plus one additional line:
  - `view._client_lock = self._client_lock` — view shares parent's `asyncio.Lock` (None at construction, populated lazily by parent's first call). Prevents two competing locks racing to create the `httpx.AsyncClient` (defense in depth — the double-check inside `_ensure_http_client` would catch the race anyway, but sharing the lock is cheaper and more correct semantically).
- **`AsyncClient.__repr__`** prefixes `"view of "`.
- **Async `_request()` shell** sets `req.extensions["max_attempts"] = self._max_retries + 1`.
- **Async `_send_auth_request()` shell** ALSO sets the extension (HIGYRUS DELTA).
- **No new imports:** `_validate_max_retries` was already imported from `.client` (Phase 8 D-15 precedent); `Self` was already imported from `typing`.

### Per-package mocked tests (Task 2 — `tests/`)

**6 sync + 6 async tests** added to `packages/higyrus-client/tests/`:

| Test | Asserts |
|------|---------|
| `test_with_options_close_is_noop` | After `view.close()`, parent's `_state.http_client` AND `_state.token` are both intact. Higyrus-specific token assertion. |
| `test_with_options_exit_is_noop` | `with view:` block exit mirror. |
| `test_with_options_chaining_inner_wins_local` | `c.with_options(5).with_options(10)._max_retries == 10`. |
| `test_with_options_repr_shows_view_prefix` | `repr(view).startswith("view of <higyrus_client.Client(")`; D-18 password/token redaction (`'***'`) preserved on view. |
| `test_with_options_invalid_max_retries_raises_value_error` | `with_options(-1)`, `with_options(True)`, `with_options(1.5)` all raise `ValueError(match="max_retries")`. |
| **`test_with_options_view_retry_log_still_redacts_token`** (NEW for higyrus) | T-13-03-01 mitigation. Configures sentinel token `HIGYRUS-TOKEN-SENTINEL-DO-NOT-LEAK`, mocks 503 forever, triggers `view.get_movimientos()` with `max_retries=2`. Asserts >=1 WARNING records emitted (non-vacuous) AND sentinel substring absent from `record.getMessage()`, `record.args`, and `record.__dict__` string values. Uses `_attach_higyrus_logger()` to ensure the Phase 8 LOG-02 `RedactingFilter` is wired BEFORE the retry path runs. |

Async mirrors of all 6: `aclose_is_noop`, `aexit_is_noop`, `chaining_inner_wins_local_async`, `async_repr_shows_view_prefix`, `async_invalid_max_retries_raises_value_error`, and `view_async_retry_log_still_redacts_token`.

### Snapshot regen (D-P4)

Ran `uv run python verification/regen_snapshots.py` per D-P4 atomicity discipline. Result: **zero body diff for all 4 packages** including higyrus. Same reasoning as Plan 13-02 — the snapshot enumerator at `verification/test_public_surface.py::_enumerate_surface` only walks `getattr(pkg, "__all__", [])` and emits one line per top-level name. `Client.with_options` is a METHOD on `Client`, not a module-level export. The snapshot file is regenerated atomically but produces no git diff. Snapshot test stays GREEN as a regression net for `__all__` drift; method addition is invisible to the snapshot.

D-V5 discrepancy (CONTEXT.md said "gain exactly 2 entries per Plan 2-5") is the same mechanism mismatch documented at length in Plan 13-02 Summary.

## Task Commits

| Task | Description | Commit | Type |
|------|-------------|--------|------|
| 1 | Client.with_options + AsyncClient.with_options + _is_view slot + lifecycle no-op + _request + _send_auth_request extensions | `df15e4d` | `feat` |
| 2 | Per-package mocked tests (6 sync + 6 async) + RedactingFilter integrity tests | `1a2af26` | `test` |

## Files Created/Modified

### Created

(none)

### Modified

- `packages/higyrus-client/src/higyrus_client/client.py` (+89 / -2)
- `packages/higyrus-client/src/higyrus_client/aio.py` (+67 / -4)
- `packages/higyrus-client/tests/test_client.py` (+203 / 0)
- `packages/higyrus-client/tests/test_async_client.py` (+169 / 0)

### Untouched (per plan scope)

- `_state.py` (no `client_max_retries` field added — D-T4: matriz only in Plan 4)
- `_transport.py` / `_atransport.py` (Plan 1 wiring already in place; transport already reads `request.extensions.get("max_attempts", self._max_attempts)`)
- `_logging.py` (RedactingFilter unchanged — view shares the same logger namespace `"higyrus_client"` via shared package, so the filter applies automatically)
- `_core.py`, `exceptions.py`, `models.py`, `_params.py`, `__init__.py` (out of scope)
- `verification/snapshots/higyrus-client-surface.txt` (regen produced zero diff — expected)
- `verification/snapshots/{ambito-financiero,iol,matriz}-client-surface.txt` (also zero diff)
- `verification/test_with_options.py` (Plan 1 owns it; Plan 3 only flips its higyrus rows GREEN)
- `pyproject.toml` (no new runtime deps)

## Decisions Made

### `_send_auth_request` also sets `extensions["max_attempts"]` (HIGYRUS DELTA vs ámbito)

Per **D-T6 in CONTEXT.md**: "view's `extensions["max_attempts"]` SÍ se honra para esos calls" — auth-flow requests carry `idempotent=True` (Phase 8 D-03), so the view's per-call retry cap MUST apply to login (and any future refresh path). Without this, a `view = c.with_options(max_retries=10)` would silently fall back to the parent's `_max_retries` on a stale-token re-auth path triggered by the next endpoint call.

This is the **only** semantic divergence between higyrus Plan 13-03 and the ámbito reference impl Plan 13-02. The ámbito package has no auth surface, so its shell only has one `_request()` extension write. Higyrus's `_send_auth_request` adds the second write — same expression `req.extensions["max_attempts"] = self._max_retries + 1` for textual uniformity. The cross-cutting `test_with_options_max_attempts_extension_honored` exercises this end-to-end via the higyrus `get_movimientos` path; if `_send_auth_request` omitted the extension, the test would fail at the first stale-token retry.

### Async view shares parent's `_client_lock`

The async client class declares `_client_lock: asyncio.Lock | None = None` lazy-initialized inside the event loop. A view constructed via `type(self).__new__(...)` does NOT go through `__init__`, so its `_client_lock` would be uninitialized (raising `AttributeError` on first access via `_ensure_client_lock`).

Solution: `view._client_lock = self._client_lock` — the view inherits whatever the parent has (None or a live `asyncio.Lock`). This:

1. Prevents `AttributeError`.
2. If the parent has already opened its lock, the view shares the lock (no second lock per view — semantically correct since the view's first call runs on the same loop as the parent).
3. If the parent has NOT yet opened its lock, the view's `_ensure_client_lock` will create one and assign it to `self._client_lock` (the view's slot only — does NOT propagate back to parent). The double-checked locking inside `_ensure_http_client` still catches any race because both view and parent check `self._state.http_client` BEFORE acquiring their lock.

The defensive layering matches Phase 6 + 7 conventions: cross-loop usage is unsupported (the lock is bound to a specific loop); within a single loop, sharing minimizes contention.

### RedactingFilter integrity test: non-vacuous assertion + explicit `attach()`

Per the CR-02 pattern from `verification/test_logging_no_token_leak.py:194`, the new redaction test asserts `warning_records, "expected >=1 WARNING ..."` BEFORE the absence-of-sentinel loop. Without this gate, the absence-of-sentinel assertion is vacuously true when the retry path emits zero records (e.g., the view's `max_attempts` extension fails to reach the transport).

The test explicitly calls `_attach_higyrus_logger()` (which is idempotent per LOG-01) to ensure the Phase 8 LOG-02 `RedactingFilter` is wired BEFORE the retry path runs. In production, the consuming application would call `attach()` at import time. Without it, raw record contents would reach `caplog` and the assertion could leak credentials in test failure messages.

### `# type: ignore[arg-type]` removed on `max_retries=True` calls

`bool` is a subclass of `int` in Python, so mypy accepts `with_options(max_retries=True)` without complaint. The runtime `_validate_max_retries(True)` call still rejects it explicitly (the existing Phase 8 WR-06 helper checks `isinstance(value, bool)` BEFORE the int check). Mypy emits an "unused `# type: ignore`" error if the comment is present. The `# type: ignore[arg-type]` is preserved on `with_options(max_retries=1.5)` because `float` is NOT a subclass of `int`. Plan 13-02 precedent.

### No need to update existing slot-membership assertions

Plan 13-02 ámbito had to update `test_client_class.py::test_async_client_has_no_client_lock_attribute` (Rule 1) because that test literally pinned `set(AsyncClient.__slots__) == {"_state", "_max_retries"}`. Higyrus's `test_client_class.py` has NO equivalent pinned-set assertion (verified via `grep -rn "__slots__" packages/higyrus-client/tests/` → no matches). Adding `_is_view` to slots is a pure extension; no Rule 1 fix needed.

## Deviations from Plan

None — plan executed exactly as written.

The Plan task action explicitly mentioned the `_send_auth_request` second extension write (Task 1 step 6 in the plan body); that was implemented. The Plan's `<read_first>` section flagged the RedactingFilter intact under view as a hard constraint; the new redaction test (sync + async) validates it directly.

## Issues Encountered

### 3-minute wall-clock for `test_with_options_max_attempts_extension_honored[higyrus_client]`

Same as Plan 13-02 — the test exercises 11 wire requests with full-jitter exponential backoff (1s initial, 30s max, exp base 2, jitter 1.0). Total ~186s. Not a defect; this is the cost of validating end-to-end retry behavior. Plans 4-5 will see the same cost per package. The fast cross-cutting tests (`test_with_options_shares_http_client_and_token` + `test_with_options_chaining_inner_wins`) take <0.1s each.

### No other issues

Ruff + ruff-format + mypy strict all GREEN on first try (no PT011 friction, no unused-ignore, no slot assertion to update — Plan 13-02 absorbed the patterns).

## Forward References for Plans 4-5 (and Phase 15 driver migration)

### Plan 4 (matriz + D-T1..T6)

- Same view shape + new field `_state.client_max_retries: int` (matriz only).
- `_ensure_token()` (sync line 253 + async line ~306) consumes `state.client_max_retries` instead of `self._max_retries` when calling `build_token_store(state, max_retries=...)`.
- The matriz-specific `test_with_options_does_not_rebind_tokenstore_max_retries` lives in `packages/matriz-client/tests/`.
- **CRITICAL merge gate:** `test_with_options_does_not_bypass_mutation_gate_matriz` (cross-cutting) flips GREEN in Plan 4. Money-on-the-line; do NOT skip the assertion `len(httpx_mock.get_requests()) == 1`. matriz `new_order` declares `qty` (3 letters); the longer-form `quantity` would raise `TypeError` BEFORE the mutation gate is exercised, silently neutralizing the SC#2 ROADMAP merge gate.
- Auth-flow extension write (matriz Risk API auth_basic path): mirror higyrus Plan 13-03 — `_send_auth_request` (or matriz's equivalent shell) also sets `extensions["max_attempts"]`.

### Plan 5 (iol)

- Same view shape + 401 re-auth path in shell preserved.
- iol is LAST in serial because Phase 14 SEC-01 disk persistence interacts with iol's shell.
- Green-gate consolidation at end of phase: all 4 packages GREEN on all 4 cross-cutting tests (4 × 4 = 16 GREEN; the matriz mutation-gate test is row 2, column matriz_client only).

### Phase 15 driver migration examples

`main_higyrus.py` can adopt the view ergonomics:

```python
# Bump retries for a flaky historical date range that occasionally 503s:
movs = higyrus_client.Client(...).with_options(max_retries=5).get_movimientos(
    "CTA-001", date(2024, 1, 1), date(2024, 1, 31)
)

# Disable retries entirely for debug iteration:
movs = higyrus_client.Client(...).with_options(max_retries=0).get_movimientos(...)
```

Phase 15 (REFAC-05) decides adoption per driver.

## Next Plan Readiness

- **Plan 4 (matriz)** ready to start from this HEAD. Plans 13-02 + 13-03 establish the per-package view-shape precedent + the `_send_auth_request` second extension write pattern. Plan 4 introduces the matriz-specific `_state.client_max_retries` field for TokenStore isolation (D-T1..T6) and the critical mutation-gate cross-cutting test.
- The Phase 13 cross-cutting test file `verification/test_with_options.py` has all 4 tests already; Plans 4-5 do not modify it — each plan just flips its row(s) GREEN incrementally. After Plan 4: 12 of 13 rows GREEN. After Plan 5: 13 of 13 GREEN.

## Self-Check: PASSED

### Files exist
- `packages/higyrus-client/src/higyrus_client/client.py` — FOUND (has `def with_options`, `_is_view`, `req.extensions["max_attempts"]` 2 occurrences, `getattr(self, "_is_view", False)`)
- `packages/higyrus-client/src/higyrus_client/aio.py` — FOUND (has all 4 sentinels + 2 extension writes)
- `packages/higyrus-client/tests/test_client.py` — FOUND (has 6 new `test_with_options_*` tests including `test_with_options_view_retry_log_still_redacts_token`)
- `packages/higyrus-client/tests/test_async_client.py` — FOUND (has 6 new async `test_with_options_*` tests including `test_with_options_view_async_retry_log_still_redacts_token`)
- `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/13-03-SUMMARY.md` — THIS FILE

### Commits exist
- `df15e4d` — feat(13-03): Client+AsyncClient.with_options for higyrus (Task 1)
- `1a2af26` — test(13-03): per-package with_options tests + RedactingFilter integrity (Task 2)

### Acceptance criteria (Task 1)
- `grep -c "def with_options" client.py` = 1 ✓
- `grep -c "def with_options" aio.py` = 1 ✓
- `grep -c "_is_view" client.py` = 5 (≥4) ✓
- `grep -c "_is_view" aio.py` = 5 (≥4) ✓
- `grep -c 'req.extensions["max_attempts"] = self._max_retries + 1' client.py` = 2 (≥2: `_request` + `_send_auth_request`) ✓
- `grep -c 'req.extensions["max_attempts"] = self._max_retries + 1' aio.py` = 2 (≥2: async `_request` + async `_send_auth_request`) ✓
- `python -c "from higyrus_client import Client, AsyncClient; assert '_is_view' in Client.__slots__ and '_is_view' in AsyncClient.__slots__"` exits 0 ✓
- Higyrus tests GREEN: 159 passed ✓
- Cross-cutting GREEN: `test_with_options_shares_http_client_and_token[higyrus_client]` ✓
- Cross-cutting GREEN: `test_with_options_max_attempts_extension_honored[higyrus_client]` (3-min wall-clock) ✓
- Cross-cutting GREEN: `test_with_options_chaining_inner_wins[higyrus_client]` ✓
- `uv run ruff check packages/higyrus-client/` exits 0 ✓
- `uv run mypy --strict packages/higyrus-client/src` exits 0 ✓

### Acceptance criteria (Task 2)
- `grep -c "def test_with_options_close_is_noop" test_client.py` = 1 ✓
- `grep -c "def test_with_options_view_retry_log_still_redacts_token" test_client.py` = 1 ✓
- `grep -c "def test_with_options_aclose_is_noop" test_async_client.py` = 1 ✓
- `grep -c "def test_with_options_view_async_retry_log_still_redacts_token" test_async_client.py` = 1 ✓
- `grep -rc "HIGYRUS-TOKEN-SENTINEL-DO-NOT-LEAK" packages/higyrus-client/tests/` returns ≥ 2 (sync + async, 1 each) ✓
- `uv run --package higyrus-client pytest packages/higyrus-client/tests/ -x -q` → 159 passed ✓
- `uv run pytest verification/test_public_surface.py -x -q` → 4 passed (snapshot still GREEN) ✓
- Cross-cutting (3 of 4 GREEN for higyrus): `uv run pytest verification/test_with_options.py -k "higyrus_client"` → 3 passed ✓
- Snapshot integrity: `git diff verification/snapshots/higyrus-client-surface.txt` reports empty ✓
- Other packages' snapshots untouched: `git diff verification/snapshots/{ambito,matriz,iol}-client-surface.txt` reports empty ✓
- `uv run ruff check packages/higyrus-client/ verification/` exits 0 ✓
- `uv run mypy --strict packages/higyrus-client/src packages/higyrus-client/tests` exits 0 ✓

### Quality gates
- `uv run ruff check packages/higyrus-client/ verification/` → All checks passed ✓
- `uv run ruff format --check packages/higyrus-client/` → 21 files already formatted ✓
- `uv run mypy --strict packages/higyrus-client/src packages/higyrus-client/tests` → Success: no issues found in 21 source files ✓

### Scope discipline
- No modifications to `_state.py` (D-T4: matriz only)
- No modifications to `_transport.py` / `_atransport.py` (Plan 1 scope)
- No modifications to `_logging.py` (RedactingFilter unchanged; view shares the logger namespace)
- No modifications to other 3 packages
- No modifications to `verification/test_with_options.py` (Plan 1 owns it)
- No modifications to `pyproject.toml`
- No modifications to STATE.md or ROADMAP.md (orchestrator owns these after wave merge)

---
*Phase: 13-cross-package-ergonomics-with-options-max-retries-n*
*Completed: 2026-06-15*
