---
phase: 13-cross-package-ergonomics-with-options-max-retries-n
plan: 05
subsystem: iol-client
tags: [with_options, view, is_view, max_attempts, ergonomics, erg-01, iol, oauth, refresh_token, 401-reauth, green-gate, phase-13-complete]

# Dependency graph
requires:
  - phase: 08-retries-backoff-structured-logging
    provides: "RetryTransport + AsyncRetryTransport reading req.extensions['max_attempts'] (extended by Phase 13 Plan 1); _validate_max_retries helper (WR-06); login + refresh marked idempotent=True (D-03) so view's max_attempts override is honored on auth-flow per D-T6"
  - phase: 09-bug-03-d-13-completion
    provides: "iol 401 re-auth-once shell + body-consume-then-raise contract (D-06); refresh_token field on _state with CR-01 conditional rotation"
  - phase: 13-cross-package-ergonomics-with-options-max-retries-n
    plan: 01
    provides: "RetryTransport + AsyncRetryTransport actually read req.extensions['max_attempts']; verification/test_with_options.py with 13 cross-cutting tests"
  - plan: 02
    provides: "ámbito reference implementation of with_options view shape (D-V1..D-V3)"
  - plan: 03
    provides: "higyrus reference: _send_auth_request also writes max_attempts extension (D-T6)"
  - plan: 04
    provides: "matriz reference: with_options + CRITICAL merge gate Anti-Pitfall 14 GREEN; matriz Plan 4 was supposed to clean up Plan 1's RED-in-HEAD '# type: ignore[attr-defined]' on the mutation-gate call but didn't"
provides:
  - "iol_client.Client.with_options(*, max_retries: int) -> Client — view returns fresh Client sharing _state (token + refresh_token + http_client) with overridden _max_retries and _is_view=True"
  - "iol_client.AsyncClient.with_options(*, max_retries: int) -> AsyncClient — async mirror; view also inherits parent's _client_lock so the first call reuses the per-loop asyncio.Lock"
  - "_is_view slot on both Client and AsyncClient __slots__ (alphabetically sorted)"
  - "Lifecycle no-op: close() / __exit__ / aclose() / __aexit__ short-circuit when _is_view=True (anti-Pitfall 13)"
  - "Shell _request() / async _request() set req.extensions['max_attempts'] = self._max_retries + 1"
  - "Shell _send_auth_request() / async _send_auth_request() ALSO set req.extensions['max_attempts'] (D-T6 — login + refresh are idempotent=True per Phase 8 D-03)"
  - "401 re-auth path of _request UNCHANGED — view shares _state.refresh_token with parent; _ensure_token uses parent's refresh_token; new tokens written back to shared state.token + state.refresh_token (visible to parent — INTENDED, shared _state semantics)"
  - "__repr__ prefixes 'view of ' when _is_view=True; existing D-18 + T-06-05 redaction (password, token, refresh_token) preserved on views"
  - "Per-package iol mocked tests: 6 sync + 6 async (124 → 136 tests in iol suite), including the iol-specific test_with_options_view_401_triggers_reauth_via_shared_refresh_token (sync + async)"
  - "All 3 cross-cutting [iol_client] parametrize rows GREEN (shares_http_client_and_token, max_attempts_extension_honored, chaining_inner_wins)"
  - "PHASE 13 FINAL GREEN GATE PASSING — 970 tests passed, 1 deselected, 0 failures; ruff check + format --check + lint-imports + pre-commit (idempotent) all exit 0"

affects:
  - "Phase 14 (SEC-01 IOL refresh-token disk persistence) — view shares _state which will include the disk-cache state; views continue sharing the cache without per-view duplication. iol-last position in serial proven correct."
  - "Phase 15 (REFAC-05 driver migration) — main_iol.py can adopt client.with_options(max_retries=N) ergonomics; mutation gate (none in iol today — all endpoints are idempotent GETs) prevails for any future POST/PATCH."
  - "Phase 17 (LIVE-03 final live re-verification) — re-runs main_*.py against live APIs with the with_options surface in place."

# Tech tracking
tech-stack:
  added: []  # No new runtime deps
  patterns:
    - "View constructor copied verbatim from Plans 13-02/13-03/13-04: type(self).__new__(type(self)) + share _state + override _max_retries + flag _is_view=True"
    - "Single-line guard `if getattr(self, \"_is_view\", False): return  # noqa: E701  # fmt: skip` on close() AND aclose()"
    - "Uniform extension set in shell: req.extensions['max_attempts'] = self._max_retries + 1 — parent or view both set this (no branching)"
    - "AUTH-FLOW EXTENSION (iol uses _send_auth_request, like higyrus — NOT login() directly like matriz): The IDIOM is the same — extension write at the auth-flow site. iol has BOTH login() and _refresh() routes that both go through _send_auth_request (sync) or build_login_request/build_refresh_request both go through _send_auth_request (async) so a single extension write per file covers both."
    - "Async view inherits parent's _client_lock so the view's first call reuses the per-loop asyncio.Lock (defense in depth — the double-check inside _ensure_http_client would catch the race anyway, but sharing the lock is cheaper and more correct semantically)"
    - "iol-specific 401 re-auth test pattern: stale-GET (401) → /token refresh (200) → fresh-GET (200) — exactly 3 wire requests; new tokens visible on parent's state (shared _state semantics confirmed)"

key-files:
  created:
    - ".planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/deferred-items.md (44 LOC): documents 11 pre-existing mypy strict errors in verification/ predating Phase 13"
  modified:
    - "packages/iol-client/src/iol_client/client.py (+96 / -6): Client.with_options + _is_view slot + __init__ default + close() no-op guard + __repr__ prefix + _request() extension set + _send_auth_request() extension set"
    - "packages/iol-client/src/iol_client/aio.py (+83 / -6): AsyncClient.with_options + _is_view slot + __init__ default + aclose() no-op guard + async __repr__ prefix + async _request() extension set + async _send_auth_request() extension set + view inherits _client_lock"
    - "packages/iol-client/tests/test_client.py (+186 LOC): 6 mocked sync tests for view shape including iol-specific 401-re-auth-with-view"
    - "packages/iol-client/tests/test_async_client.py (+169 LOC): 6 mocked async tests for view shape including async iol-specific 401-re-auth-with-view"
    - "verification/test_with_options.py (1 line cleanup): removed stale '# type: ignore[attr-defined]' from line 226 (Plan 13-01 RED-in-HEAD artifact; matriz Plan 13-04 should have removed it)"

key-decisions:
  - "iol uses _send_auth_request (NOT login() directly like matriz) — same IDIOM as higyrus Plan 13-03. Both login() and _refresh() route through _send_auth_request, so a single extension write in _send_auth_request body covers both auth-flow request paths. Negative grep `def login\\(self\\)` calling `http.send` directly returns 0 in iol src files."
  - "D-T4 negative confirmation: NO `client_max_retries` field added to iol _state.py / client.py / aio.py. Verified via grep — D-T4 in CONTEXT.md explicitly excludes iol from the matriz-only `client_max_retries` field because iol does not have a parametrized TokenStore. Matriz's TokenStore isolation pattern does NOT apply to iol."
  - "401 re-auth path of _request UNCHANGED — the view's `_request` shell calls `_ensure_token()` which uses the parent's SHARED `_state.refresh_token` to obtain a fresh access token. The new tokens are written back to the SHARED `_state.token` and `_state.refresh_token` — visible to the parent and any sibling views. This is INTENDED, shared-state semantics (Phase 6 D-13). Cross-cutting test_with_options_view_401_triggers_reauth_via_shared_refresh_token (sync + async) validates this end-to-end."
  - "Async view also inherits parent's _client_lock (view._client_lock = self._client_lock) — the lock is per-loop; the view runs on the same loop as the parent (cross-loop usage is unsupported per Phase 6 + 7 invariant). Sharing prevents two competing locks racing to create the httpx.AsyncClient. Plan 13-03 (higyrus) precedent."
  - "Async view shares parent's _state.token_lock via shared _state (no separate field assignment needed) — the token_lock is on _state, so sharing _state automatically shares token_lock. The view's 401 re-auth path therefore goes through the SAME asyncio.Lock as the parent, preserving the WR-01 atomic-clear-and-reauth invariant from Phase 8."
  - "Plan-attributable mypy fix: removed `# type: ignore[attr-defined]` from verification/test_with_options.py:226. Plan 13-01 placed it as a RED-in-HEAD artifact (matriz.Client had no with_options); Plan 13-04 added it but did not remove the now-unused ignore. Plan 13-05 noticed the warn_unused_ignores violation during the green gate and removed it (Rule 1 auto-fix). Same logic applied to no other plans because no other plans had `# type: ignore[attr-defined]` on with_options call sites in this file."
  - "Snapshot regen produced ZERO body diff across all 4 packages (expected per D-V5 discrepancy documented in Plans 13-02/13-03/13-04). The snapshot enumerator only walks __all__ at module level; with_options is a method on Client/AsyncClient, not a module-level export. Snapshot test stays GREEN as a __all__-drift regression net."

requirements-completed: [ERG-01]  # Last plan in Phase 13; ERG-01 spans Plans 2-5 and is now complete.

# Metrics
duration: ~38min (incl ~15min for the full pytest gate run; ~3min for the cross-cutting test_with_options_max_attempts_extension_honored[iol_client] which exercises 11 wire retries with full-jitter backoff)
completed: 2026-06-15
---

# Phase 13 Plan 05: with_options iol + Phase 13 Consolidated Green Gate Summary

**Phase 13 Wave 5 + Final Green Gate — `iol_client.Client.with_options(*, max_retries)` + `AsyncClient.with_options` land as the LAST per-package roll-out in Phase 13's serial. iol-specific: view's 401 path uses parent's SHARED `_state.refresh_token` (CR-01 conditional rotation preserved); shell `_request()` + `_send_auth_request()` (sync + async) set `req.extensions["max_attempts"]` uniformly. D-T4 NEGATIVE confirmed: NO `client_max_retries` field added to iol (matriz-only). 3 of 3 cross-cutting `[iol_client]` parametrize rows flip RED → GREEN, completing the 4-package serial. Plan 13-05 also executes the Phase 13 consolidated green gate (D-P1): `uv run pytest` → 970 passing (≥ 907 v1.1 baseline preserved per SC#5); `ruff check` + `ruff format --check` + `lint-imports` + `pre-commit run --all-files` (idempotent) all exit 0. Phase 13 COMPLETE. Phase 14 (SEC-01 IOL disk persistence) can begin.**

## Performance

- **Duration:** ~38 min (incl ~15-min full pytest gate run; ~3-min cross-cutting `test_with_options_max_attempts_extension_honored[iol_client]` wall-clock)
- **Tasks:** 3 (atomic per-task commits)
- **Files modified:** 5 (2 src + 2 tests + 1 verification cleanup)
- **Files created:** 1 (`deferred-items.md`)
- **LOC delta:** +578 / -12 across all 6 files
- **iol test count:** 124 → 136 (+12 new tests)

## Accomplishments

### Sync client (Task 1 — `client.py`)

- **`Client.__slots__`** extended to `("_is_view", "_max_retries", "_state")` (alphabetized, mirroring Plans 13-02/13-03/13-04).
- **`Client.__init__`** sets `self._is_view = False` after the existing `self._max_retries = max_retries`.
- **`Client.close()`** short-circuits when `_is_view=True` via the single-line guard `if getattr(self, "_is_view", False): return  # noqa: E701  # fmt: skip`. Docstring explicitly mentions iol-specific implication: "never tear down the parent's shared TCP pool nor invalidate the parent's cached OAuth token (anti-Pitfall 13)". `__exit__` calls `close()` so the guard covers it.
- **`Client.__repr__`** prefixes `"view of "` when `_is_view=True`. The existing D-18 + T-06-05 redaction of `password`, `token`, AND `refresh_token` stays intact.
- **New `Client.with_options(*, max_retries: int) -> Self`** method placed between `_ensure_http_client` and `_send_auth_request`:
  - `_validate_max_retries(max_retries)` is the FIRST call (WR-06 carry-forward).
  - View constructed via `type(self).__new__(type(self))` — fresh `Client` instance with no `__init__` invocation.
  - `view._state = self._state` — SHARES `_state` (including cached `token`, `refresh_token`, `token_expires_at`).
  - `view._max_retries = max_retries`, `view._is_view = True`.
  - Docstring (~55 lines) covers: shared-state semantics with explicit mention of OAuth `token` + `refresh_token`, lifecycle no-op, D-V2 chaining inner-wins, D-V4 configure-invariance, mutation gate authority, **iol-specific 401 re-auth path** with shared `_state.refresh_token`, and **Phase 14 SEC-01 forward-reference** ("when the IOL refresh-token disk persistence lands, the view will continue sharing `_state` (and therefore the disk-cached refresh_token) without modification").
- **`Client._request()` shell** adds `req.extensions["max_attempts"] = self._max_retries + 1` AFTER the existing `endpoint_name` extension. The 401 re-auth branch (lines 327-348 — `_state.token = None` + `_ensure_token()` + retry once) is UNCHANGED. The view's 401 retry goes through this same path using shared `_state.refresh_token`.
- **`Client._send_auth_request()` shell** ALSO sets `req.extensions["max_attempts"] = self._max_retries + 1` (per D-T6 — login + refresh requests carry `idempotent=True` per Phase 8 D-03, so the view's per-call cap MUST apply).

### Async client (Task 1 — `aio.py`)

Async mirror of sync — zero divergence sync↔async surface (D-V3 parity):

- **`AsyncClient.__slots__`** extended to `("_client_lock", "_is_view", "_max_retries", "_state")`.
- **`AsyncClient.__init__`** sets `self._is_view = False`.
- **`AsyncClient.aclose()`** short-circuits when `_is_view=True` via the same single-line guard pattern.
- **New `AsyncClient.with_options(*, max_retries: int) -> Self`** — sync method even on the async class. Same body as sync, plus one additional line:
  - `view._client_lock = self._client_lock` — view shares parent's `asyncio.Lock` (Plan 13-03 higyrus precedent).
- **`AsyncClient.__repr__`** prefixes `"view of "`; D-18 + T-06-05 redaction preserved on the async surface too.
- **Async `_request()` shell** sets `req.extensions["max_attempts"] = self._max_retries + 1`. The async 401 re-auth carve-out (lines 311-349 — atomic clear-and-reauth under `token_lock` per WR-01) is UNCHANGED. The view shares `_state.token_lock` via shared `_state`, preserving the WR-01 invariant.
- **Async `_send_auth_request()` shell** ALSO sets the extension (D-T6 mirror).
- **No new imports:** `_validate_max_retries` was already imported from `.client` (Phase 8 D-15 precedent); `Self` was already imported from `typing`.

### Per-package mocked tests (Task 2 — `tests/`)

**6 sync tests** appended to `packages/iol-client/tests/test_client.py`:

| Test | Asserts |
|------|---------|
| `test_with_options_close_is_noop` | After `view.close()`, parent's `_state.http_client` AND `_state.token` are both intact (no re-auth on close). |
| `test_with_options_exit_is_noop` | `with view:` block exit mirror. |
| `test_with_options_chaining_inner_wins_local` | `c.with_options(5).with_options(10)._max_retries == 10`. |
| `test_with_options_repr_shows_view_prefix` | `repr(view).startswith("view of IOLClient(")`; D-18 + T-06-05 redaction preserved on view (password, token, refresh_token all `'***'`). |
| `test_with_options_invalid_max_retries_raises_value_error` | `with_options(-1)`, `with_options(True)`, `with_options(1.5)` all raise `ValueError(match="max_retries")`. |
| **`test_with_options_view_401_triggers_reauth_via_shared_refresh_token`** (iol-specific) | Mock sequence: stale-GET (401) → /token refresh (200) → fresh-GET (200). Constructs `Client(username="u", password="p", token="stale-token", token_expires_at=9_999_999_999.0)` and sets `client._state.refresh_token = "fresh-refresh"` post-construction (per revision iter 2 — iol Client kwargs are username/password, NOT client_id/client_secret; refresh_token is a `_state` field). Asserts (i) returned quote is the success body; (ii) `client._state.token == "new-token"` (parent updated by view's re-auth — shared `_state` semantics); (iii) `client._state.refresh_token == "new-refresh"` (rotated value visible on parent); (iv) `view._state is client._state` (shared); (v) exactly 3 wire requests. |

**6 async-mirror tests** in `packages/iol-client/tests/test_async_client.py`: same six but with `aclose`/`aexit`/`chaining_inner_wins_local_async`/`async_repr`/`async_invalid_max_retries`/**`async_view_401_triggers_reauth_via_shared_refresh_token`**.

### Snapshot regen (D-P4)

Ran `uv run python verification/regen_snapshots.py` per D-P4 atomicity discipline. Result: **zero body diff for all 4 packages** including iol. Same reasoning as Plans 13-02/13-03/13-04 — the snapshot enumerator at `verification/test_public_surface.py::_enumerate_surface` only walks `getattr(pkg, "__all__", [])`. `Client.with_options` is a METHOD on `Client`, not a module-level export. Snapshot test stays GREEN as a `__all__`-drift regression net.

### Phase 13 Consolidated Green Gate (Task 3 — D-P1)

All 6 gate commands PASS:

| Gate | Command | Result | Notes |
|------|---------|--------|-------|
| 1 | `uv run pytest` (full monorepo) | **970 passed, 1 deselected, 0 failures** in 925.26s (~15 min) | ≥ 907 v1.1 baseline preserved (SC#5 ROADMAP); +63 net-additive tests across Phases 8-13 |
| 2 | `uv run ruff check` | **All checks passed** | exit 0 |
| 3 | `uv run ruff format --check` | **151 files already formatted** | exit 0 |
| 4 | `uv run mypy --strict packages/*/src` | **47 source files clean** | exit 0 (Phase 13 deliverables) |
| 5 | `uv run lint-imports` | **4 contracts kept, 0 broken** | exit 0 (no internal-package transport leaks) |
| 6 | `uv run pre-commit run --all-files` | **all hooks Passed (trailing-whitespace, eof, yaml, toml, large-files, merge-conflict, ruff, ruff-format, mypy)** | exit 0; second run also exit 0 (idempotent — Quick task 260614-r1x invariant preserved) |

**All 13 cross-cutting `verification/test_with_options.py` tests GREEN** (4 packages × 3 row-tests + 1 matriz-only mutation gate test):
- `test_with_options_shares_http_client_and_token` × 4 packages → SC#1
- `test_with_options_does_not_bypass_mutation_gate_matriz` → **SC#2 CRITICAL anti-Pitfall 14 (money-on-the-line)**
- `test_with_options_max_attempts_extension_honored` × 4 packages → SC#3
- `test_with_options_chaining_inner_wins` × 4 packages → D-V2

### Pre-existing mypy strict errors in `verification/` — documented as deferred

`uv run mypy --strict packages/*/src verification/` reported 11 pre-existing errors in 5 `verification/` files originating from Phase 8 + Phase 11 commits. Provenance verified via `git log --oneline -- <file>`. These are NOT caused by Phase 13 and are out of scope per the SCOPE BOUNDARY rule. Documented in `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/deferred-items.md` with file-by-file provenance and a suggested cleanup path (future `/gsd-quick` task — ~15 min estimate). The Phase 13 deliverables themselves pass mypy strict cleanly when scoped to the actually-modified files (`packages/*/src` + `verification/test_with_options.py`).

### Plan-attributable cleanup (Rule 1 auto-fix)

Plan 13-05 noticed a stale `# type: ignore[attr-defined]` at `verification/test_with_options.py:226` on the matriz mutation-gate call. The comment was placed by Plan 13-01 as a RED-in-HEAD artifact (matriz.Client lacked `with_options` at that point). Plan 13-04 added matriz `with_options` but did not remove the comment; mypy's `warn_unused_ignores = true` flagged it as unused during Plan 13-05's gate. Removed per Rule 1. This is Phase-13-attributable (Plan 13-01 artifact), distinct from the pre-existing Phase 8/11 mypy errors.

## Task Commits

| Task | Description | Commit | Type |
|------|-------------|--------|------|
| 1 | Client+AsyncClient.with_options + _is_view slot + lifecycle no-op + 2 sync sites + 2 async sites + __repr__ prefix | `d0c0ffb` | `feat` |
| 2 | Per-package mocked tests (6 sync + 6 async) including iol-specific 401-re-auth-with-view | `0ce7550` | `test` |
| 3 | Phase 13 consolidated green gate + Plan-1 stale type-ignore cleanup + deferred-items.md | `3eaa5f4` | `chore` |

## Files Created/Modified

### Created

- `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/deferred-items.md` (+44 LOC)

### Modified

- `packages/iol-client/src/iol_client/client.py` (+96 LOC, -6)
- `packages/iol-client/src/iol_client/aio.py` (+83 LOC, -6)
- `packages/iol-client/tests/test_client.py` (+186 LOC, 0)
- `packages/iol-client/tests/test_async_client.py` (+169 LOC, 0)
- `verification/test_with_options.py` (+1 LOC, -1 — removed stale `# type: ignore[attr-defined]`)

### Untouched (per plan scope)

- `_state.py` (D-T4 NEGATIVE: NO `client_max_retries` field added — matriz only)
- `_transport.py` / `_atransport.py` (Plan 1 wiring already in place)
- `_core.py`, `exceptions.py`, `__init__.py` (out of scope)
- `verification/snapshots/iol-client-surface.txt` (regen produced zero diff)
- `verification/snapshots/{ambito-financiero,higyrus,matriz}-client-surface.txt` (also zero diff)
- Other 3 packages' src + tests
- `pyproject.toml` (no new runtime deps)
- `STATE.md`, `ROADMAP.md` (orchestrator owns these after wave merge)

## Decisions Made

### iol uses `_send_auth_request` (NOT `login()` directly like matriz)

Negative grep `grep -n "def login(self)" packages/iol-client/src/iol_client/client.py` returns one location (line 251). The body calls `self._send_auth_request(spec)`. Same for `_refresh()` (line 264). All iol auth-flow requests route through `_send_auth_request`, so a single extension write in `_send_auth_request`'s body covers BOTH login AND refresh paths. Same pattern as higyrus Plan 13-03. matriz Plan 13-04 had to instrument THREE sites because matriz's `login()` builds the request inline (no `_send_auth_request` helper).

### D-T4 NEGATIVE: no `client_max_retries` field in iol

Verified via:

```bash
grep -c "client_max_retries" packages/iol-client/src/iol_client/_state.py
# → 0

grep -c "client_max_retries" packages/iol-client/src/iol_client/client.py packages/iol-client/src/iol_client/aio.py
# → 0
```

CONTEXT.md D-T4 explicitly excludes iol from the matriz-only `client_max_retries` field because iol does not have a `build_token_store(state, max_retries=N)`-style parametrized auth-server retry cap. iol's auth-flow retries are governed by the same `RetryTransport` `max_attempts` extension as endpoint requests; the view's `_max_retries` flows through the same path.

### 401 re-auth path of `_request` UNCHANGED

The plan called out that the view's 401 path must use the parent's shared `_state.refresh_token`. The mechanism is automatic via shared `_state` — the view's `_request` calls `self._ensure_token()` which reads `self._state.refresh_token` (shared with parent). No code change needed in the 401 carve-out itself. The cross-cutting test `test_with_options_view_401_triggers_reauth_via_shared_refresh_token` exercises this end-to-end with the exact mock sequence (stale-GET → /token refresh → fresh-GET) and asserts new tokens are visible on parent's `_state`.

### Async view shares parent's `_client_lock`

The async class declares `_client_lock: asyncio.Lock | None = None` lazy-initialized. A view constructed via `type(self).__new__(...)` does NOT go through `__init__`, so its `_client_lock` would be uninitialized (`AttributeError` on first access). Solution: `view._client_lock = self._client_lock` — same pattern as higyrus Plan 13-03. Three benefits: (1) prevents `AttributeError`; (2) if parent has already opened its lock, view shares it (no second lock per view); (3) if parent has not yet opened its lock, view's `_ensure_http_client` creates one in its own slot. The double-checked locking inside `_ensure_http_client` still catches any race.

### Async view shares parent's `_state.token_lock` via shared `_state`

`_state.token_lock` lives on `_state`, so sharing `_state` automatically shares `token_lock`. The view's 401 re-auth path therefore goes through the SAME `asyncio.Lock` as the parent, preserving the WR-01 atomic-clear-and-reauth invariant from Phase 8. Validated in `test_with_options_async_view_401_triggers_reauth_via_shared_refresh_token` by asserting `view._state is client._state`.

### URL pattern in tests required `?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2` query string

Initial test draft used the bare endpoint URL (`https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion`). pytest-httpx failed to match because iol's `_core.build_get_quote_request` adds 3 query params (`model.mercado`, `model.simbolo`, `model.plazo`). Updated all test mocks to include the query string, matching the precedent in existing iol tests (e.g., `test_get_quote_url_exacta_con_query_string`).

### Plan-attributable mypy cleanup vs scope boundary

Three mypy `[unused-ignore]` errors surfaced during the green gate:

1. `verification/test_with_options.py:226` — **Phase-13-attributable** (Plan 13-01 RED-in-HEAD artifact). Removed.
2. `verification/test_main_matriz_schema_snapshot_alignment.py:59` — pre-existing Phase 11 issue. Deferred.
3-11. Other 9 errors — pre-existing Phase 8/11 issues. Deferred.

The Phase-13-attributable error (#1) is in scope under Rule 1 (auto-fix bugs / artifacts caused by Phase 13 plans). The others are out of scope per the SCOPE BOUNDARY rule and documented in `deferred-items.md`.

## Deviations from Plan

### Rule 1 — removed stale `# type: ignore[attr-defined]` from `verification/test_with_options.py:226`

**Found during:** Task 3 (Phase 13 green gate mypy strict run).
**Issue:** `verification/test_with_options.py:226` carried `# type: ignore[attr-defined]` on `client.with_options(...)` placed by Plan 13-01 as a RED-in-HEAD marker (matriz.Client lacked `with_options` then). Plan 13-04 added matriz `with_options`, making the ignore unused. mypy's `warn_unused_ignores = true` reported `[unused-ignore]` error.
**Fix:** Removed the `# type: ignore[attr-defined]` comment, keeping the `# fmt: skip` (which is still needed to satisfy the literal acceptance grep + prevent ruff from splitting the line).
**Files modified:** `verification/test_with_options.py` (+1 / -1).
**Commit:** `3eaa5f4` (folded into Task 3 because it's part of the green gate cleanup atomic unit).
**Justification:** The comment is Phase-13-attributable (Plan 13-01 artifact), distinct from pre-existing errors. Removing it aligns the file with the post-Phase-13 reality where all 4 packages have `with_options`.

### No other deviations

The plan task actions executed verbatim. The two micro-adjustments above were both in scope.

## Issues Encountered

### URL mock pattern mismatch (RED on first test run)

Initial draft of the 6+6 per-package tests used bare endpoint URLs without query strings. iol's `get_quote` builder appends `?model.mercado=...&model.simbolo=...&model.plazo=...` to the URL, so pytest-httpx failed to match. Fixed by updating all mocks to the full URL with query string, matching the precedent in existing iol tests (`test_get_quote_url_exacta_con_query_string` at `test_client.py:105`).

### Pre-existing mypy strict errors in `verification/`

11 errors across 5 files predating Phase 13 (Phase 8 commits `43cdda9` + `a8342e7`; Phase 11 commit `967b868` + `383d000` + `bc4acc1`). Documented in `deferred-items.md` with provenance and suggested cleanup path. The pre-commit mypy hook (which only checks `packages/*/src` per workspace config) passes idempotently — the verification-directory strictness mismatch is a known project debt independent of Phase 13.

### 15-minute wall-clock for full `uv run pytest`

The full pytest run takes ~15 min because each per-package `test_with_options_max_attempts_extension_honored` parametrize test exercises 11 wire retries with full-jitter exponential backoff (1s initial, 30s max, exp base 2, jitter 1.0). 4 packages × ~3 min each = ~12 min just for the cross-cutting `max_attempts_extension_honored` row. Not a defect; this is the cost of validating end-to-end retry behavior.

## Cross-Cutting Test Status — Phase 13 Complete

| Cross-cutting test | ambito row | higyrus row | matriz row | iol row |
|---|---|---|---|---|
| `test_with_options_shares_http_client_and_token` | **GREEN** | **GREEN** | **GREEN** | **GREEN** |
| `test_with_options_does_not_bypass_mutation_gate_matriz` | n/a | n/a | **GREEN** (CRITICAL) | n/a |
| `test_with_options_max_attempts_extension_honored` | **GREEN** | **GREEN** | **GREEN** | **GREEN** |
| `test_with_options_chaining_inner_wins` | **GREEN** | **GREEN** | **GREEN** | **GREEN** |

**13 of 13 collected cross-cutting items GREEN.** The CRITICAL merge gate (Anti-Pitfall 14 / SC#2 ROADMAP / money-on-the-line) is met on matriz Plan 13-04 and reconfirmed by the green gate's full pytest run in Plan 13-05.

## All 5 ROADMAP Phase 13 success criteria met

- **SC#1 (resource leak / anti-Pitfall 13):** `test_with_options_shares_http_client_and_token` × 4 GREEN. View shares `_state` and `_state.http_client` with parent — no second TCP pool, no re-auth.
- **SC#2 (anti-Pitfall 14 / mutation gate / money-on-the-line):** `test_with_options_does_not_bypass_mutation_gate_matriz` GREEN. matriz `new_order` under 503 with `view.with_options(max_retries=10)` emits EXACTLY 1 outgoing request.
- **SC#3 (RetryTransport reads `max_attempts` extension):** `test_with_options_max_attempts_extension_honored` × 4 GREEN. Parent `max_retries=2` → 3 wire requests; view `max_retries=10` → 11 wire requests.
- **SC#4 (per-package serial roll-out complete):** ámbito → higyrus → matriz → iol all delivered, each in its own atomic Plan. Plan 13-05 closes the serial.
- **SC#5 (v1.1 907-test baseline preserved):** `uv run pytest` reports **970 passing** (+63 net-additive from Phases 8-13), 0 failures. Baseline preserved + extended.

## Anti-Pitfall confirmation

- **Anti-Pitfall 13 (resource leak):** mitigated via `_is_view` lifecycle no-op guard on close/aclose/__exit__/__aexit__ across all 4 packages × 2 surfaces. `view.close()` does NOT touch parent's `http_client` nor `token`. Per-package `test_with_options_close_is_noop` validates this; cross-cutting `test_with_options_shares_http_client_and_token` validates the identity contract.
- **Anti-Pitfall 14 (mutation gate / money-on-the-line):** mitigated by Phase 8 D-01 mutation gate evaluating `extensions["idempotent"]` FIRST inside `RetryTransport.handle_request`, with `extensions["max_attempts"]` consumed only on the idempotent path. Plan 1 wired the read order; Plan 4 (matriz) provided the only package with a non-idempotent endpoint (`new_order`); the CRITICAL test `test_with_options_does_not_bypass_mutation_gate_matriz` proves the gate holds under `view.with_options(max_retries=10).new_order(...)` → exactly 1 outgoing request under 503.

## Forward References — Phase 14 + Phase 15 (D-D2)

### Phase 14 SEC-01 — IOL disk persistence

Phase 13 positioned iol LAST in the serial precisely because Phase 14 will add disk-cached `refresh_token` storage on `_state` (likely as a `token_cache_path` field or similar). The view's shared `_state` semantics ensure:

1. **Zero view-side changes needed:** views share `_state`, so they automatically share the disk-cache state.
2. **CR-01 conditional rotation preserved:** the view's 401 re-auth path writes new `refresh_token` to shared `_state.refresh_token`, which Phase 14's persistence layer will flush to disk transparently.
3. **No coordination locks needed across views:** the existing `_state.token_lock` (async) already serializes refresh-token writes; Phase 14 can layer its disk-write atop the same lock without view-specific plumbing.

### Phase 15 driver migration — example usage (per CONTEXT.md D-D2)

```python
# 1. Bump retries for a flaky idempotent GET (e.g., a rare symbol that 503s):
quote = iol_client.Client(...).with_options(max_retries=5).get_quote("RARE")

# 2. Disable retries entirely for debug iteration:
movs = iol_client.Client(...).with_options(max_retries=0).get_historical_quotes(
    "GGAL", date(2024, 1, 1), date(2024, 1, 31)
)

# 3. matriz — mutation gate prevails; new_order under 503 emits EXACTLY 1 request:
order = matriz_client.Client(...).with_options(max_retries=10).new_order(
    symbol="GGAL", side="BUY", qty=1, price=100.0, account="acct"
)
```

Phase 15 (REFAC-05) decides adoption per driver. Phase 17 (LIVE-03) re-verifies against live APIs.

## Next Phase Readiness

- **Phase 14 (SEC-01 IOL disk persistence)** ready to start from this HEAD. The iol view shape is fully concrete; Phase 14 planning can see the exact `_state.refresh_token` sharing pattern in code before designing the disk-cache integration.
- All 5 ROADMAP Phase 13 success criteria met.
- All 13 cross-cutting tests GREEN.
- Phase 13 final green gate passing.
- iol-last serial position proven correct.

## Self-Check: PASSED

### Files exist

- `packages/iol-client/src/iol_client/client.py` — FOUND (has `def with_options`, `_is_view`, 2× `req.extensions["max_attempts"] = self._max_retries + 1`, `getattr(self, "_is_view", False)`)
- `packages/iol-client/src/iol_client/aio.py` — FOUND (has `def with_options`, `_is_view`, 2× `max_attempts` extension write, `view._client_lock = self._client_lock`)
- `packages/iol-client/tests/test_client.py` — FOUND (6 new `test_with_options_*` tests including `test_with_options_view_401_triggers_reauth_via_shared_refresh_token`)
- `packages/iol-client/tests/test_async_client.py` — FOUND (6 new async `test_with_options_*` tests including `test_with_options_async_view_401_triggers_reauth_via_shared_refresh_token`)
- `verification/test_with_options.py` — FOUND (stale `# type: ignore[attr-defined]` removed)
- `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/deferred-items.md` — CREATED
- `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/13-05-SUMMARY.md` — THIS FILE

### Commits exist (verified via `git log --oneline -5`)

- `d0c0ffb` — feat(13-05): Client+AsyncClient.with_options for iol + _is_view lifecycle + max_attempts extension (Task 1)
- `0ce7550` — test(13-05): per-package with_options tests + iol-specific 401-re-auth-with-view (Task 2)
- `3eaa5f4` — chore(13-05): Phase 13 consolidated green gate — cleanup Plan-1 stale type-ignore (Task 3)

### Acceptance criteria (Task 1)

- `grep -c "def with_options" packages/iol-client/src/iol_client/client.py` = 1 ✓
- `grep -c "def with_options" packages/iol-client/src/iol_client/aio.py` = 1 ✓
- `grep -c "_is_view" packages/iol-client/src/iol_client/client.py` = 5 (≥ 4) ✓
- `grep -c "_is_view" packages/iol-client/src/iol_client/aio.py` = 6 (≥ 4) ✓
- `grep -c 'req.extensions\["max_attempts"\] = self._max_retries + 1' packages/iol-client/src/iol_client/client.py` = 2 (≥ 2) ✓
- `grep -c 'req.extensions\["max_attempts"\] = self._max_retries + 1' packages/iol-client/src/iol_client/aio.py` = 2 (≥ 2) ✓
- Slot correctness: `python -c "from iol_client import Client, AsyncClient; assert '_is_view' in Client.__slots__ and '_is_view' in AsyncClient.__slots__"` exits 0 ✓
- D-T4 negative (iol does NOT get client_max_retries field): `grep -c "client_max_retries" packages/iol-client/src/iol_client/_state.py` = 0 ✓
- D-T4 negative: `grep -c "client_max_retries" packages/iol-client/src/iol_client/client.py packages/iol-client/src/iol_client/aio.py` = 0 ✓
- Behavior (Phase 6/8/9 iol tests still GREEN): `uv run --package iol-client pytest packages/iol-client/tests/` → 136 passed ✓
- Behavior (401 re-auth path UNCHANGED): `uv run pytest verification/test_retry_401_reauth.py -x -q` → 7 passed ✓
- Cross-cutting GREEN: `uv run pytest verification/test_with_options.py -k "iol_client"` → 3 passed, 10 deselected ✓
- Quality: `uv run ruff check packages/iol-client/` exits 0 ✓
- Quality: `uv run mypy --strict packages/iol-client/src` exits 0 ✓

### Acceptance criteria (Task 2)

- `grep -c "def test_with_options_close_is_noop" packages/iol-client/tests/test_client.py` = 1 ✓
- `grep -c "def test_with_options_view_401_triggers_reauth_via_shared_refresh_token" packages/iol-client/tests/test_client.py` = 1 ✓
- `grep -c "def test_with_options_async_view_401_triggers_reauth_via_shared_refresh_token" packages/iol-client/tests/test_async_client.py` = 1 ✓
- Behavior: `uv run --package iol-client pytest packages/iol-client/tests/` → 136 passed ✓
- Behavior: `uv run pytest verification/test_public_surface.py -x -q` → 4 passed ✓
- Cross-cutting (3 of 4 GREEN for iol): `uv run pytest verification/test_with_options.py -k "iol_client"` → 3 passed ✓
- Snapshot integrity: `git diff verification/snapshots/iol-client-surface.txt` reports empty ✓
- Negative (other packages untouched): `git diff verification/snapshots/{ambito-financiero,higyrus,matriz}-client-surface.txt` reports empty ✓
- Quality: `uv run ruff check packages/iol-client/ verification/` exits 0 ✓
- Quality: `uv run mypy --strict packages/iol-client/` exits 0 ✓

### Acceptance criteria (Task 3 — Phase 13 final green gate)

- `uv run pytest` → **970 passed, 1 deselected** in 925.26s. Exit 0. **≥ 907 baseline confirmed.** ✓
- `uv run ruff check` exits 0 ✓
- `uv run ruff format --check` → 151 files already formatted; exits 0 ✓
- `uv run mypy --strict packages/ambito-financiero-client/src packages/higyrus-client/src packages/matriz-client/src packages/iol-client/src` exits 0 ✓ (Phase 13 deliverables clean; `verification/` extension has pre-existing errors documented in deferred-items.md)
- `uv run lint-imports` → 4 contracts kept, 0 broken; exits 0 ✓
- `uv run pre-commit run --all-files` → all hooks Passed; exits 0 ✓
- `uv run pre-commit run --all-files` (second run) → idempotent, exits 0 ✓ (Quick task 260614-r1x invariant preserved)
- All 13 cross-cutting `verification/test_with_options.py` items GREEN ✓
- The CRITICAL `test_with_options_does_not_bypass_mutation_gate_matriz` GREEN ✓
- All per-package `test_with_options_*` tests GREEN across 4 packages × 2 surfaces ✓
- `13-05-SUMMARY.md` documents: exact pytest count (970); all 6 gate outputs; Phase 13 complete; forward reference to Phase 14 (SEC-01 disk persistence next) ✓

### Scope discipline

- No modifications to `_state.py` (D-T4 NEGATIVE: matriz only)
- No modifications to `_transport.py` / `_atransport.py` (Plan 1 scope)
- No modifications to `_core.py` / `exceptions.py` / `__init__.py` of iol
- No modifications to other 3 packages
- No modifications to `pyproject.toml` (no new runtime deps)
- No modifications to STATE.md or ROADMAP.md (orchestrator owns these after wave merge)
- Pre-existing mypy strict errors in `verification/` (5 files, 11 errors from Phases 8 + 11) deliberately left in place per SCOPE BOUNDARY; logged in `deferred-items.md`

---
*Phase: 13-cross-package-ergonomics-with-options-max-retries-n*
*Completed: 2026-06-15*
