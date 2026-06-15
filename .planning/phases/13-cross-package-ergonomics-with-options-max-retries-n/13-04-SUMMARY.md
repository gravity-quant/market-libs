---
phase: 13-cross-package-ergonomics-with-options-max-retries-n
plan: 04
subsystem: matriz-client
tags: [with_options, view, is_view, max_attempts, ergonomics, erg-01, matriz, tokenstore, primary-api, merge-gate, anti-pitfall-14]

# Dependency graph
requires:
  - phase: 08-retries-backoff-structured-logging
    provides: "RetryTransport + AsyncRetryTransport reading req.extensions['max_attempts'] (extended by Phase 13 Plan 1); _validate_max_retries helper (WR-06); login marked idempotent=True (D-03) so view's max_attempts override is honored on auth-flow per D-T6; mutation gate (D-01) is the absolute authority on retry permission"
  - phase: 10-matriz-aio-py-creation-tokenstore
    provides: "TokenStore 3-way concurrency primitive (threading.Lock + asyncio.Lock per loop); build_token_store(state, *, max_retries) signature; _aensure_token double-checked locking inside per-loop asyncio.Lock; matriz aio.py 852 LOC including async login() with extensions block"
  - phase: 13-cross-package-ergonomics-with-options-max-retries-n
    plan: 01
    provides: "RetryTransport + AsyncRetryTransport actually read req.extensions['max_attempts'] (sync + async, matriz included); verification/test_with_options.py with 4 cross-cutting tests including CRITICAL test_with_options_does_not_bypass_mutation_gate_matriz (matriz-only, money-on-the-line)"
  - plan: 02
    provides: "ámbito reference implementation of with_options view shape (D-V1/D-V2/D-V3); per-package mocked-test patterns to mirror"
  - plan: 03
    provides: "higyrus reference implementation of with_options + auth-flow extension write (_send_auth_request); per-package test patterns; D-T6 confirmed working on auth-flow"
provides:
  - "matriz_client.Client.with_options(*, max_retries: int) -> Client — view returns fresh Client sharing _state (incl. token, token_expires_at, the shared 3-way token_store primitive, and http_client), with overridden _max_retries and _is_view=True"
  - "matriz_client.aio.AsyncClient.with_options(*, max_retries: int) -> AsyncClient — async mirror; same shared-state semantics + Phase 10 _aensure_token per-loop asyncio.Lock invariant preserved"
  - "_is_view slot on both Client and AsyncClient __slots__ (alphabetically sorted)"
  - "Lifecycle no-op guard: close() / aclose() / __exit__ / __aexit__ short-circuit when _is_view=True (anti-Pitfall 13 + D-T2 — parent's TCP pool, cached token, AND 3-way TokenStore primitive all intact)"
  - "THREE sync request-build sites set req.extensions['max_attempts'] = self._max_retries + 1: login() (D-T6), _request Risk API path (auth_basic), _request Token/Primary path"
  - "THREE async request-build sites mirror exactly: async login() (D-T6), async _request Risk path, async _request Token path"
  - "NEW _state.client_max_retries: int = 2 field on _ClientState (matriz only per D-T4); __init__ sets it from max_retries arg; _ensure_token (sync) + _aensure_token (async) consume it via build_token_store(state, max_retries=state.client_max_retries) — NOT self._max_retries (D-T1/D-T3 TokenStore isolation)"
  - "configure() mirrors max_retries into state.client_max_retries when the runtime override path rebuilds the TokenStore (sync + async)"
  - "__repr__ prefixes 'view of ' when _is_view=True; existing D-18 password/token redaction stays intact"
  - "Per-package mocked tests: 6 sync + 6 async + 4 D-T5/D-T6 matriz-specific (in NEW test_with_options.py). Total matriz suite: 305 → 321 tests."
  - "ALL 4 cross-cutting tests for matriz row GREEN — including CRITICAL test_with_options_does_not_bypass_mutation_gate_matriz (SC#2 ROADMAP / Anti-Pitfall 14 / money-on-the-line)"
affects:
  - "Plan 5 (with_options iol): last package + consolidated green gate at end of phase; iol must replicate the matriz Risk-API multi-site extension pattern adapted to iol's 401 re-auth-once shell"
  - "Phase 15 driver migration (REFAC-05): main_matriz.py can opt into client.with_options(max_retries=N) ergonomics for idempotent GETs (get_segments, get_market_data, etc.); mutation gate prevents accidental retry on new_order"
  - "Phase 17 LIVE-03: live re-verification ensures with_options on matriz does not regress observable wire behavior (esp. mutation gate for new_order/cancel_order — money-on-the-line)"

# Tech tracking
tech-stack:
  added: []  # No new runtime deps
  patterns:
    - "View constructor copied from Plans 13-02/13-03: type(self).__new__(type(self)) + share _state + override _max_retries + flag _is_view=True"
    - "Single-line guard `if getattr(self, \"_is_view\", False): return  # noqa: E701  # fmt: skip` on close() AND aclose()"
    - "Uniform extension set in shell: req.extensions['max_attempts'] = self._max_retries + 1 — parent or view both set this (no branching)"
    - "AUTH-FLOW EXTENSION (matriz delta vs higyrus): matriz uses login() directly (NOT _send_auth_request like higyrus). The IDIOM is the same but the METHOD NAME differs — extension write is in login() body (Site 1 of THREE per file)"
    - "D-T1/D-T3 TokenStore isolation: matriz-only new field _state.client_max_retries: int = 2. Constructor (sync + async) sets it from max_retries arg. _ensure_token + _aensure_token call build_token_store(state, max_retries=state.client_max_retries) — view's HTTP-only override does NOT rebind the TokenStore retry cap (auth-server retries stay gobernado por the Client constructor)."
    - "D-T2 TokenStore 3-way primitive shared: view shares _state.token_store (Phase 10 threading.Lock + asyncio.Lock per loop both operate on the SAME instance); spike-findings-market-libs SKILL.md remains accurate"
    - "configure() mirror: when max_retries= kwarg is passed at runtime, both default._max_retries AND default._state.client_max_retries are updated so the rebuilt TokenStore (post-reset) uses the new cap"

key-files:
  created:
    - "packages/matriz-client/tests/test_with_options.py (+212 LOC): 4 matriz-specific tests covering D-T5 TokenStore isolation (sync + async) and D-T6 login extension propagation (sync + async)"
    - "packages/matriz-client/tests/test_async_client.py (+165 LOC): 6 async-mirror per-package mocked tests for AsyncClient.with_options (matriz did not have an async test file before this plan; the existing test_async_auth.py / test_async_queries.py / test_async_mutations.py cover Phase 10 behaviors)"
  modified:
    - "packages/matriz-client/src/matriz_client/_state.py (+3 LOC): new client_max_retries: int = 2 field on _ClientState (D-T3 matriz only)"
    - "packages/matriz-client/src/matriz_client/client.py (+99 LOC): __init__ sets state.client_max_retries + _is_view=False; close() short-circuits on view; __repr__ prefix; new with_options method with extensive docstring; THREE sites add max_attempts extension (login + Risk path + Token path); _ensure_token rebinds to state.client_max_retries; configure() mirrors max_retries into state.client_max_retries"
    - "packages/matriz-client/src/matriz_client/aio.py (+91 LOC): async mirror of all of the above (async _aensure_token rebind, async with_options, aclose() no-op, async __repr__ prefix, THREE async sites add extension, async configure() mirror)"
    - "packages/matriz-client/tests/test_client.py (+140 LOC): 6 new mocked tests for sync Client.with_options including D-T2 TokenStore-sharing test"

key-decisions:
  - "Matriz uses login() directly (NOT _send_auth_request like higyrus) per the explicit plan callout. The IDIOM is the same — extension write at the auth-flow site — but the METHOD NAME differs. Site 1 of THREE per file is login() (sync) / async login() (async). Negative grep `def _send_auth_request` returns 0 in matriz src files."
  - "D-T3 field placement: client_max_retries lives on _ClientState (mutable dataclass) — NOT on the Client instance — because the TokenStore is shared cross-surface (sync Client + async AsyncClient + ws_client daemon thread) via state.token_store. Keeping the cap on _ClientState ensures it travels with the state instance, and the view (which shares _state by construction) cannot accidentally rebind it from its own _max_retries override."
  - "configure() mirror update: when configure(max_retries=N) is called, BOTH default._max_retries and default._state.client_max_retries are updated. Without the second update, the rebuilt TokenStore (after default._state.token_store = None) would consume the stale state.client_max_retries instead of the new constructor cap. This is a matriz-specific runtime override path not covered by the constructor path."
  - "test_with_options.py is a NEW file (not appended to an existing test file) per the plan. The D-T5 + D-T6 tests are matriz-specific and live cleanly in their own module. The 2 cross-cutting tests test_with_options_does_not_rebind_tokenstore_max_retries (sync + async) implement the exact body documented in CONTEXT.md <specifics> D-T5. The 2 D-T6 tests close the login-site coverage gap identified by the plan-checker."
  - "test_async_client.py is also a NEW file. Matriz did not have a single async test entry point — Phase 10 split async tests into auth/queries/mutations/atransport. Creating test_async_client.py for Phase 13 ERG-01 keeps the with_options-shape tests cohesive and follows the higyrus pattern (Plan 13-03)."
  - "monkeypatch target is matriz_client.client.build_token_store (NOT matriz_client._token_store.build_token_store) because client.py imports the symbol at module load. Patching the source module would NOT intercept the call. Same reasoning for the async path: patch aio.build_token_store (the binding that aio.py imported at module load)."
  - "D-T2 sync test uses an in-test Client + _ensure_token to build the store. D-T2 async test uses the module-level default singletons because _aensure_token needs the sync default Client's http_client for MatrizRefresh (which runs inside asyncio.to_thread). The conftest autouse fixture seeds the sync default credentials so the swap inside the lazy-init block has a valid sync httpx.Client to read from."
  - "Snapshot regen produced ZERO body diff across all 4 packages (expected per D-V5 discrepancy documented in Plans 13-02 + 13-03). The snapshot enumerator only walks __all__ at module level; with_options is a method on Client/AsyncClient, not a module-level export. Snapshot test stays GREEN as a __all__-drift regression net."

requirements-completed: []  # ERG-01 spans Plans 2-5; reported by orchestrator after Plan 5 lands the iol piece.

# Metrics
duration: ~30min (excluding the 3-minute cross-cutting test_with_options_max_attempts_extension_honored[matriz_client] which exercises 11 wire retries with full-jitter backoff)
completed: 2026-06-15
---

# Phase 13 Plan 04: with_options matriz Summary

**Phase 13 Wave 4 — THE merge gate of Phase 13 (CRITICAL / Anti-Pitfall 14 / SC#2 ROADMAP / money-on-the-line) lands. matriz `Client.with_options(*, max_retries)` + `AsyncClient.with_options` ship with three matriz-specific properties on top of the higyrus/ámbito shape: (1) D-T3 new field `_state.client_max_retries: int` providing TokenStore retry-cap isolation; (2) D-T1/D-T2 TokenStore 3-way concurrency primitive UNCHANGED — view shares `state.token_store` and does NOT rebind it; (3) view's `extensions["max_attempts"]` flows through ALL THREE matriz request-build sites per file (`login()` per D-T6 + `_request` Risk path + `_request` Token path; sync × 3 + async × 3). `test_with_options_does_not_bypass_mutation_gate_matriz` flips RED → GREEN — view's `max_retries=10` on `new_order(...)` under persistent 503 still emits EXACTLY 1 wire request, mutation gate (Phase 8 D-01) remains the absolute authority. ALL 4 cross-cutting tests for matriz row GREEN.**

## Performance

- **Duration:** ~30 min (excluding the 3-minute wall-clock cross-cutting `test_with_options_max_attempts_extension_honored[matriz_client]` which exercises 11 wire retries with full-jitter exponential backoff)
- **Tasks:** 3 (atomic per-task commits — see Task Commits table)
- **Files modified:** 4 (3 src + 1 test)
- **Files created:** 2 (test_with_options.py + test_async_client.py)
- **LOC delta:** +565 LOC across 6 files (heaviest: client.py +99, aio.py +91, test_client.py +140, test_with_options.py +212, test_async_client.py +165, _state.py +3)
- **Test count:** matriz suite 305 → 321 (+16 new tests)

## Accomplishments

### `_state.py` — D-T3 field (Task 1)

- New `client_max_retries: int = 2` field added to `_ClientState` after the existing `token_store: TokenStore | None = None` field.
- Comment cites Phase 13 D-T3: "TokenStore retry cap source (separate from HTTP-level `_max_retries` which view can override via `with_options`)".
- Matriz-only per D-T4 — other packages do NOT need this field because they don't parameterize their auth-flow with `max_retries`.

### Sync client (Task 1 + Task 2)

- **`Client.__slots__`** extended to `("_is_view", "_max_retries", "_state")` (alphabetized, mirroring Plans 13-02 + 13-03).
- **`Client.__init__`** now sets:
  - `self._max_retries = max_retries` (existing)
  - `self._state.client_max_retries = max_retries` (NEW — Task 1, D-T3)
  - `self._is_view = False` (NEW — Task 2)
- **`Client.close()`** short-circuits when `_is_view=True` via the single-line guard `if getattr(self, "_is_view", False): return  # noqa: E701  # fmt: skip`. Identical pattern to Plans 13-02 + 13-03. `__exit__` calls `close()` so the guard covers it automatically.
- **`Client.__repr__`** prefixes `"view of "` when `_is_view=True` (Claude's Discretion). The existing D-18 redaction of `password` and `token` (always `'***'`) stays intact.
- **New `Client.with_options(*, max_retries: int) -> Self`** method (placed between `_ensure_http_client` and `login`):
  - `_validate_max_retries(max_retries)` is the FIRST call (WR-06 carry-forward).
  - View constructed via `type(self).__new__(type(self))` — fresh `Client` instance with no `__init__` invocation.
  - `view._state = self._state` — SHARES `_state` (including `token`, `token_expires_at`, `account_id`, AND `token_store` — D-T2 Phase 10 3-way primitive).
  - `view._max_retries = max_retries`, `view._is_view = True`.
  - Docstring (~70 lines) covers: shared-state semantics, **CRITICAL mutation gate authority for `new_order(...)`** (Anti-Pitfall 14 / SC#2 ROADMAP / money-on-the-line), **D-T1/D-T3 TokenStore isolation**, **D-T2 token_store sharing**, D-V2 chaining, D-V4 configure-invariance.
- **`Client._ensure_token`** now calls `build_token_store(self._state, max_retries=self._state.client_max_retries)` — reads the parent's constructor value, NOT `self._max_retries` (Task 1, D-T1/D-T3 isolation).
- **`Client.login()`** — Site 1 of THREE — adds `req.extensions["max_attempts"] = self._max_retries + 1` after the existing `endpoint_name` extension (Task 2, D-T6 because login is `idempotent=True` per Phase 8 D-03).
- **`Client._request()` Risk API path** — Site 2 of THREE — adds the extension uniformly.
- **`Client._request()` Token/Primary path** — Site 3 of THREE — adds the extension uniformly. NOTE: the mutation gate (Phase 8 D-01 `idempotent` extension) is still the absolute authority; `new_order` carries `idempotent=False` so the transport skips the Retrying loop regardless of `max_attempts`.
- **`configure()`** updates `default._state.client_max_retries = max_retries` when the runtime override path rebuilds the TokenStore (so the new TokenStore uses the new cap).

### Async client (Task 1 + Task 2)

Async mirror of sync — zero divergence sync↔async surface (D-V3 parity):

- **`AsyncClient.__slots__`** extended to `("_is_view", "_max_retries", "_state")`.
- **`AsyncClient.__init__`** mirrors sync — sets `_max_retries`, `state.client_max_retries`, `_is_view=False`.
- **`AsyncClient.aclose()`** short-circuits when `_is_view=True` via the same single-line guard pattern. `__aexit__` calls `aclose()` so the guard covers it.
- **New `AsyncClient.with_options(*, max_retries: int) -> Self`** — sync method on the async class (returns view in-memory; the subsequent endpoint call is async). Same body as sync.
- **`AsyncClient.__repr__`** prefixes `"view of "`; D-18 redaction preserved.
- **`AsyncClient._aensure_token`** calls `build_token_store(state, max_retries=state.client_max_retries)` — Task 1 D-T3 async mirror.
- **Async `login()`** — Async Site 1 of THREE — adds the extension.
- **Async `_request()` Risk path** — Async Site 2 of THREE — adds the extension.
- **Async `_request()` Token path** — Async Site 3 of THREE — adds the extension.
- **Async `configure()`** mirrors `state.client_max_retries` update.

### Per-package mocked tests (Task 3)

**6 sync tests** appended to `packages/matriz-client/tests/test_client.py`:

| Test | Asserts |
|------|---------|
| `test_with_options_close_is_noop` | After `view.close()`, parent's `_state.http_client` AND `_state.token` are both intact. |
| `test_with_options_exit_is_noop` | `with view:` block exit mirror. |
| `test_with_options_chaining_inner_wins_local` | `c.with_options(5).with_options(10)._max_retries == 10`. |
| `test_with_options_repr_shows_view_prefix` | `repr(view).startswith("view of Client(")`; D-18 redaction preserved. |
| `test_with_options_invalid_max_retries_raises_value_error` | `with_options(-1)`, `with_options(True)`, `with_options(1.5)` all raise `ValueError(match="max_retries")`. |
| **`test_with_options_view_shares_token_store_3way_primitive`** (matriz-specific, D-T2) | After parent's first `_ensure_token` builds `state.token_store`, asserts `view._state.token_store is parent._state.token_store` (identity, NOT clone). |

**6 async-mirror tests** in NEW `packages/matriz-client/tests/test_async_client.py`: same six but with `aclose` / `aexit` / `chaining_inner_wins_local_async` / `async_repr` / `async_invalid_max_retries` / **`async_view_shares_token_store_3way_primitive`**.

### NEW `test_with_options.py` — D-T5 + D-T6 (Task 3)

**4 tests** in NEW `packages/matriz-client/tests/test_with_options.py`:

| Test | Asserts |
|------|---------|
| **`test_with_options_does_not_rebind_tokenstore_max_retries`** (D-T5 sync) | Monkeypatches `matriz_client.client.build_token_store` with a spy. Constructs `Client(max_retries=2)`, creates `view = c.with_options(max_retries=10)`, forces first `_ensure_token` from view (clears token + token_store), mocks `/auth/getToken`, calls `view._ensure_token()`. Asserts `build_calls == [2]` — confirming parent's `state.client_max_retries=2` was used, NOT view's `_max_retries=10`. |
| **`test_with_options_does_not_rebind_tokenstore_max_retries_async`** (D-T5 async) | Async mirror — monkeypatches `aio.build_token_store`. |
| **`test_with_options_view_login_request_carries_max_attempts_extension`** (D-T6 sync) | Constructs `Client(max_retries=2)` + `view = c.with_options(max_retries=10)`, mocks `/auth/getToken`, calls `view.login()`, captures the outgoing request via `httpx_mock.get_requests()[0]`, asserts `request.extensions["max_attempts"] == 11`. This proves Site 1 of THREE (matriz `login()`) honors view's per-call cap end-to-end. |
| **`test_with_options_async_view_login_request_carries_max_attempts_extension`** (D-T6 async) | Async mirror of D-T6 — `await view.login()` and assert async login request has `extensions["max_attempts"] == 11`. |

The 4 D-T5/D-T6 assertions cover the matriz-specific bits the cross-cutting tests in `verification/test_with_options.py` cannot reach (the cross-cutting tests are parametrized across all 4 packages and target the public retry-count behavior; the matriz TokenStore-isolation + login-extension-propagation are package-internal contracts).

### Snapshot regen (D-P4)

Ran `uv run python verification/regen_snapshots.py` per D-P4 atomicity discipline. Result: **zero body diff for all 4 packages**. Same reasoning as Plans 13-02 + 13-03: the snapshot enumerator at `verification/test_public_surface.py::_enumerate_surface` only walks `getattr(pkg, "__all__", [])`. `Client.with_options` is a METHOD on `Client`, not a module-level export. Snapshot test stays GREEN as a `__all__`-drift regression net.

## Task Commits

| Task | Description | Commit | Type |
|------|-------------|--------|------|
| 1 | _state.client_max_retries field (D-T3) + __init__ wire + _ensure_token/_aensure_token rebind + configure() mirror | `e7f0194` | `feat` |
| 2 | Client+AsyncClient.with_options + _is_view slot + lifecycle no-op + THREE sync sites + THREE async sites + __repr__ prefix | `7b6add1` | `feat` |
| 3 | test_with_options.py (D-T5 + D-T6, sync + async) + per-package mocked tests (6 sync + 6 async, incl D-T2 TokenStore-sharing) + snapshot regen | `cdaea59` | `test` |

## Files Created/Modified

### Created

- `packages/matriz-client/tests/test_with_options.py` (+212 LOC) — D-T5 + D-T6 tests, sync + async
- `packages/matriz-client/tests/test_async_client.py` (+165 LOC) — async-mirror per-package mocked tests

### Modified

- `packages/matriz-client/src/matriz_client/_state.py` (+3 LOC, -0)
- `packages/matriz-client/src/matriz_client/client.py` (+99 LOC, -4)
- `packages/matriz-client/src/matriz_client/aio.py` (+91 LOC, -4)
- `packages/matriz-client/tests/test_client.py` (+140 LOC, -0)

### Untouched (per plan scope)

- `_token_store.py` (D-T2 — Phase 10 3-way concurrency primitive UNCHANGED; spike-findings-market-libs SKILL.md remains accurate)
- `_transport.py` / `_atransport.py` (Plan 1 wiring already in place; transport reads `request.extensions.get("max_attempts", self._max_attempts)`)
- `ws_client.py` (out of Phase 13 scope per CONTEXT.md `<deferred>` — "WebSocket layer queda intacta")
- `_core.py`, `_refresh.py`, `_refresh_policy.py`, `exceptions.py`, `models.py`, `types.py`, `__init__.py` (out of scope)
- `verification/test_with_options.py` (Plan 1 owns it; Plan 4 only flips its matriz rows GREEN)
- Other 3 packages' src + tests
- `pyproject.toml` (no new runtime deps)
- `verification/snapshots/matriz-client-surface.txt` (regen produced zero diff)
- `verification/snapshots/{ambito,higyrus,iol}-client-surface.txt` (also zero diff)

## Decisions Made

### Matriz uses `login()` directly, not `_send_auth_request` (matriz delta vs higyrus)

Per the explicit plan callout (Task 2 step 6): matriz does NOT define a `_send_auth_request` helper method — the auth shell is `login()` itself. The IDIOM is the same as higyrus (Plan 13-03 set the extension in `_send_auth_request`), but the METHOD NAME differs. Site 1 of THREE per file is the body of `login()` (sync) / `async def login()` (async). Negative grep `def _send_auth_request` returns 0 in matriz `client.py` and `aio.py`. The D-T6 test in `test_with_options.py` proves this end-to-end by capturing the outgoing login request and asserting `extensions["max_attempts"] == 11`.

### D-T3 field placement: `_ClientState`, not `Client` instance

`client_max_retries` lives on `_ClientState` (the mutable dataclass shared across surfaces) — NOT on the `Client` instance — for three reasons:

1. **Cross-surface visibility:** the TokenStore is shared between sync `Client`, async `AsyncClient`, and the `ws_client` daemon thread via `state.token_store`. Keeping the cap on `_ClientState` ensures it travels with the state instance, accessible from all three surfaces.
2. **View isolation:** because the view (which shares `_state` by construction per anti-Pitfall 13) accesses `state.client_max_retries` instead of `self._max_retries`, the view cannot accidentally rebind the TokenStore retry cap via its HTTP-only override. The view's `_max_retries` only affects the HTTP-level transport.
3. **D-T2 preservation:** the TokenStore primitive itself stays untouched. Plan 4 only changes the SOURCE of the `max_retries` argument at construction time — the TokenStore + RefreshPolicy internals are unchanged. spike-findings-market-libs SKILL.md remains accurate.

### `configure()` mirror update

When `configure(max_retries=N)` is called at runtime, BOTH `default._max_retries` AND `default._state.client_max_retries` are updated. Without the second update, the rebuilt TokenStore (after `default._state.token_store = None`) would consume the stale `state.client_max_retries` instead of the new constructor cap. This is a matriz-specific runtime override path that the constructor-only D-T3 field assignment does not cover. Same mirror is applied to async `configure()`.

### Monkeypatch target choice (D-T5)

The D-T5 spy patches `matriz_client.client.build_token_store` (and `aio.build_token_store` for async), NOT `matriz_client._token_store.build_token_store`. Reason: `client.py` does `from matriz_client._token_store import build_token_store` at module load time, creating a binding in `client`'s namespace. Patching the source module (`_token_store.build_token_store = spy`) would NOT intercept the call because the client module already resolved the reference. The same reasoning applies to the async path — patch `aio.build_token_store`.

### `test_async_client.py` is a NEW file

Matriz did not have a single async test entry point before this plan — Phase 10 split async tests into `test_async_auth.py` / `test_async_queries.py` / `test_async_mutations.py` / `test_atransport.py`. Creating `test_async_client.py` for Phase 13 ERG-01 keeps the `with_options`-shape tests cohesive in their own module, following the higyrus Plan 13-03 pattern. The new file is small (~165 LOC, 6 tests) and clearly scoped to view-shape concerns.

### D-T2 async test uses module-level default singletons

The sync D-T2 test (`test_with_options_view_shares_token_store_3way_primitive`) constructs an in-test `Client` because the sync `_ensure_token` is straightforward — it builds a TokenStore using the Client's own state.http_client. The async D-T2 test (`test_with_options_async_view_shares_token_store_3way_primitive`) uses the module-level default singletons because `_aensure_token` needs the sync default `Client`'s `_state.http_client` for `MatrizRefresh` (which runs inside `asyncio.to_thread`). The conftest autouse fixture (`_configure_sync`) seeds the sync default credentials so the swap inside the lazy-init block has a valid sync `httpx.Client` to read from. Constructing a fresh `AsyncClient` for the async test would have required also wiring a fresh sync default — more setup, same outcome.

### `# type: ignore[arg-type]` removed on `with_options(max_retries=True)` calls

`bool` is a subclass of `int` in Python, so mypy accepts the call without complaint. The runtime `_validate_max_retries(True)` still rejects it (the existing Phase 8 WR-06 helper checks `isinstance(value, bool)` BEFORE the int check). Mypy emits an "unused `# type: ignore`" error if the comment is present. The `# type: ignore[arg-type]` is preserved on `with_options(max_retries=1.5)` because `float` is NOT a subclass of `int`. Plans 13-02 + 13-03 precedent.

## Deviations from Plan

None — plan executed exactly as written.

The Plan's Task 2 step 4 mentioned `configure()` parity check; the actual `configure()` body was reviewed (lines 573-631 sync, 616-684 async) and required a small additional update (one line per surface) to mirror `max_retries` into `state.client_max_retries`. This was applied during Task 1 along with the constructor update because both changes are intrinsic to D-T3 (the runtime override path must keep the constructor-derived cap consistent). Plan body called this out as a Task 1 step ("`configure()` parity check"); it was correctly executed there.

## Issues Encountered

### 3-minute wall-clock for `test_with_options_max_attempts_extension_honored[matriz_client]`

Same as Plans 13-02 + 13-03 — the test exercises 11 wire requests with full-jitter exponential backoff (1s initial, 30s max, exp base 2, jitter 1.0). Total ~188s. Not a defect; this is the cost of validating end-to-end retry behavior. The fast cross-cutting tests (`test_with_options_shares_http_client_and_token`, `test_with_options_chaining_inner_wins`, `test_with_options_does_not_bypass_mutation_gate_matriz`) take <0.1s each.

### Initial ruff + mypy friction on test_with_options.py

The first version of `test_with_options.py` was missing type annotations on `pytest.MonkeyPatch` + `HTTPXMock` fixtures and the `spy` inner function, and had unsorted imports. Both issues were caught immediately by the post-write quality gate run and fixed in place before the Task 3 commit. The final file passes `ruff check + format --check + mypy --strict` cleanly.

### No other issues

305 → 321 tests, all green on first integration run after the source changes. The mutation gate (Anti-Pitfall 14) test passed on first run after Task 2 — confirming the view shape correctly threads through to `_request()` Token path without bypassing the `idempotent` extension check inside `RetryTransport.handle_request`.

## Cross-Cutting Test Status — Phase 13 Merge Gate

| Cross-cutting test | matriz_client row |
|---|---|
| `test_with_options_shares_http_client_and_token` | **GREEN** |
| `test_with_options_does_not_bypass_mutation_gate_matriz` | **GREEN** (CRITICAL merge gate; SC#2 ROADMAP / Anti-Pitfall 14 / money-on-the-line) |
| `test_with_options_max_attempts_extension_honored` | **GREEN** (~3min wall-clock) |
| `test_with_options_chaining_inner_wins` | **GREEN** |

**ALL 4 rows GREEN. The Phase 13 merge gate is met.** Plan 5 (iol) can proceed from this stable HEAD.

## Forward References for Plan 5 (and Phase 15 driver migration)

### Plan 5 (iol)

- Same view shape as Plans 13-02/13-03/13-04 + iol-specific 401 re-auth-once path in shell preserved.
- iol is LAST in serial because Phase 14 SEC-01 disk persistence interacts with iol's shell.
- iol does NOT have a matriz-style `_state.client_max_retries` field (D-T4 — matriz only).
- iol's `_send_auth_request` (if present — verify) follows the higyrus pattern (Plan 13-03) for the auth-flow extension write.
- Green-gate consolidation at end of Plan 5: all 4 packages GREEN on all 4 cross-cutting tests (4 × 4 = 16; matriz mutation-gate test is matriz-only column).

### Phase 15 driver migration examples (matriz)

`main_matriz.py` can adopt the view ergonomics:

```python
# Bump retries for a flaky idempotent GET (segments occasionally 503 during
# market open):
segs = matriz_client.Client(...).with_options(max_retries=5).get_segments()

# Disable retries entirely for debug iteration:
md = matriz_client.Client(...).with_options(max_retries=0).get_market_data("GGAL")

# CRITICAL — mutation gate is still authoritative; this does NOT bypass it:
# new_order under transient 503 still executes EXACTLY 1 outgoing request:
order = matriz_client.Client(...).with_options(max_retries=10).new_order(
    symbol="GGAL", side="BUY", qty=1, price=100.0, account="acct"
)
```

Phase 15 (REFAC-05) decides adoption per driver.

## Next Plan Readiness

- **Plan 5 (iol)** ready to start from this HEAD. Plans 13-02 + 13-03 + 13-04 establish the per-package view-shape precedent + the auth-flow extension write pattern (matriz delta: `login()` instead of `_send_auth_request`) + the matriz-specific TokenStore isolation pattern (D-T1..T6). Plan 5 only needs the iol-specific 401 re-auth-once accommodation and the final consolidated green-gate run.
- The Phase 13 cross-cutting test file `verification/test_with_options.py` retains all 4 tests; Plan 5 does not modify it — Plan 5 just flips the iol_client row(s) GREEN. After Plan 5: ALL 4 cross-cutting tests GREEN for ALL 4 packages.
- TokenStore 3-way concurrency primitive is unchanged. spike-findings-market-libs SKILL.md remains accurate. No follow-up SKILL update needed.

## Self-Check: PASSED

### Files exist
- `packages/matriz-client/src/matriz_client/_state.py` — FOUND (has `client_max_retries: int`)
- `packages/matriz-client/src/matriz_client/client.py` — FOUND (has `def with_options`, `_is_view`, 3× `req.extensions["max_attempts"] = self._max_retries + 1`, `state.client_max_retries`, `getattr(self, "_is_view", False)`)
- `packages/matriz-client/src/matriz_client/aio.py` — FOUND (has all sentinels: `def with_options`, `_is_view`, 3× `max_attempts` extension write, `state.client_max_retries`)
- `packages/matriz-client/tests/test_with_options.py` — FOUND (4 tests: D-T5 sync + async, D-T6 sync + async)
- `packages/matriz-client/tests/test_async_client.py` — FOUND (6 async-mirror tests including D-T2 token_store sharing)
- `packages/matriz-client/tests/test_client.py` — FOUND (6 new tests including D-T2 token_store sharing)
- `verification/snapshots/matriz-client-surface.txt` — REGEN (zero diff)
- `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/13-04-SUMMARY.md` — THIS FILE

### Commits exist
- `e7f0194` — feat(13-04): add _state.client_max_retries (D-T3) + rebind matriz _ensure_token (Task 1)
- `7b6add1` — feat(13-04): Client+AsyncClient.with_options for matriz + _is_view lifecycle (Task 2)
- `cdaea59` — test(13-04): matriz with_options test_with_options.py + per-package mocked tests (Task 3)

### Acceptance criteria (Task 1)
- `grep -c "client_max_retries: int" _state.py` = 1 ✓
- `grep -c "self._state.client_max_retries = max_retries" client.py` = 2 (init + configure) ≥1 ✓
- `grep -c "self._state.client_max_retries = max_retries" aio.py` = 2 (init + configure) ≥1 ✓
- `grep -c "build_token_store(self._state, max_retries=self._state.client_max_retries)" client.py` = 1 ✓
- `grep -c "build_token_store(self._state, max_retries=self._state.client_max_retries)" aio.py` = 1 ✓
- `grep -c "build_token_store(self._state, max_retries=self._max_retries)" client.py` = 0 (replaced) ✓
- `grep -c "build_token_store(self._state, max_retries=self._max_retries)" aio.py` = 0 (replaced) ✓
- `python -c "from matriz_client._state import _ClientState; assert _ClientState().client_max_retries == 2"` exits 0 ✓
- matriz/tests after Task 1 = 305 passed ✓
- `verification/test_retry_mutation_gate.py` = 4 passed ✓
- ruff check + format --check + mypy --strict = clean ✓

### Acceptance criteria (Task 2)
- `grep -c "def with_options" client.py` = 1 ✓
- `grep -c "def with_options" aio.py` = 1 ✓
- `grep -c "_is_view" client.py` = 5 (≥4) ✓
- `grep -c "_is_view" aio.py` = 5 (≥4) ✓
- `grep -c 'req.extensions["max_attempts"] = self._max_retries + 1' client.py` = 3 ✓
- `grep -c 'req.extensions["max_attempts"] = self._max_retries + 1' aio.py` = 3 ✓
- `grep -c "def _send_auth_request" client.py aio.py` = 0 (matriz uses login() directly) ✓
- `'_is_view' in Client.__slots__ and AsyncClient.__slots__` ✓
- matriz/tests = 305 passed ✓
- **CRITICAL merge gate GREEN:** `test_with_options_does_not_bypass_mutation_gate_matriz` PASS ✓
- Cross-cutting GREEN: `test_with_options_shares_http_client_and_token[matriz_client]` ✓
- Cross-cutting GREEN: `test_with_options_max_attempts_extension_honored[matriz_client]` (~3min wall-clock) ✓
- Cross-cutting GREEN: `test_with_options_chaining_inner_wins[matriz_client]` ✓
- ruff check + format --check + mypy --strict = clean ✓

### Acceptance criteria (Task 3)
- `test -f packages/matriz-client/tests/test_with_options.py` exits 0 ✓
- `grep -c "def test_with_options_does_not_rebind_tokenstore_max_retries" test_with_options.py` = 2 (sync + async, both contain the prefix) ≥1 ✓
- `grep -c "def test_with_options_does_not_rebind_tokenstore_max_retries_async" test_with_options.py` = 1 ✓
- `grep -c "def test_with_options_view_login_request_carries_max_attempts_extension" test_with_options.py` = 1 ✓
- `grep -c "def test_with_options_async_view_login_request_carries_max_attempts_extension" test_with_options.py` = 1 ✓
- `grep -c 'extensions["max_attempts"] == 11' test_with_options.py` = 4 (≥1) ✓
- `grep -c "assert build_calls == \[2\]" test_with_options.py` = 2 (≥1) ✓
- `grep -c "def test_with_options_view_shares_token_store_3way_primitive" test_client.py` = 1 ✓
- `grep -c "def test_with_options_async_view_shares_token_store_3way_primitive" test_async_client.py` = 1 ✓
- `grep -c "from __future__ import annotations" test_with_options.py` = 1 ✓
- matriz/tests = 321 passed (was 305; +16) ✓
- `verification/test_public_surface.py` = 4 passed (snapshot unchanged) ✓
- `verification/test_async_cancellation.py` = 4 passed (Phase 8 D-32 unchanged) ✓
- ALL 4 cross-cutting tests for matriz row GREEN ✓
- Snapshot integrity: `git diff verification/snapshots/matriz-client-surface.txt` empty ✓
- Other packages' snapshots untouched ✓
- `ruff check packages/matriz-client/ verification/` exits 0 ✓
- `mypy --strict packages/matriz-client/` exits 0 (src + tests) ✓

### Scope discipline
- No modifications to `_token_store.py` (D-T2 — Phase 10 primitive UNCHANGED)
- No modifications to `_transport.py` / `_atransport.py` (Plan 1 scope)
- No modifications to `ws_client.py` (out of phase scope per CONTEXT.md `<deferred>`)
- No modifications to other 3 packages
- No modifications to `verification/test_with_options.py` (Plan 1 owns it)
- No modifications to `pyproject.toml` (no new runtime deps)
- No modifications to STATE.md or ROADMAP.md (orchestrator owns these after wave merge)

---
*Phase: 13-cross-package-ergonomics-with-options-max-retries-n*
*Completed: 2026-06-15*
