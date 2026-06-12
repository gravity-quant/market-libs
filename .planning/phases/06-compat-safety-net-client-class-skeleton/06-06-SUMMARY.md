---
phase: 06-compat-safety-net-client-class-skeleton
plan: 06
subsystem: api
tags: [matriz-client, primary-api, x-auth-token, websocket, pep-562, async-stub, dataclass]

# Dependency graph
requires:
  - phase: 06-compat-safety-net-client-class-skeleton
    provides: "Plan 01 baseline public-surface snapshot for matriz-client; Plan 02 per-package guard pattern (test_fixture_reaches_production.py)"
provides:
  - "matriz_client.Client (sync) — full REST surface with __slots__ + __enter__/__exit__/close lifecycle, D-22 X-Auth-Token-from-header login."
  - "matriz_client.AsyncClient (stub) — lifecycle-only async client (Open Q #1); Phase 10 REFAC-04 grows REST methods."
  - "matriz_client._state._ClientState — @dataclass(slots=True) holding base_url/username/password/token/token_expires_at/http_client/account_id."
  - "matriz_client.configure(token=..., token_expires_at=...) — D-04 extended kwargs for test fixtures."
  - "matriz_client.client PEP 562 read-only shim: _token/_token_ts/_base_url/_session/_client forward; _user/_password raise AttributeError."
  - "ws_client.py cross-module migration to _rest._get_default()._state.* (W5 closure removes module-level _ensure_token callable)."
  - "Cross-package ambito test_harness_mutation_gate.py migrated to matriz_client.configure(base_url=url) (Pitfall #4)."
affects:
  - 07-verification-and-mutation-gate-audit
  - 10-async-rest-surface-and-token-store

# Tech tracking
tech-stack:
  added:
    - "PEP 562 module __getattr__ shim (extended allowlist with _base_url for mutation_gate compatibility — Open Q #4)"
    - "@dataclass(slots=True) singleton state container (matriz variant: no token_lock, no refresh_token)"
  patterns:
    - "Stub AsyncClient pattern — lifecycle-only class deferring REST surface to a future phase (Open Q #1)"
    - "Cross-module access via explicit _get_default() accessor at the boundary instead of legacy module globals"
    - "configure() kwargs extended with token/token_expires_at for test fixture preloading (D-04)"

key-files:
  created:
    - "packages/matriz-client/src/matriz_client/_state.py"
    - "packages/matriz-client/src/matriz_client/aio.py"
    - "packages/matriz-client/tests/test_client_class.py"
  modified:
    - "packages/matriz-client/src/matriz_client/client.py"
    - "packages/matriz-client/src/matriz_client/ws_client.py"
    - "packages/matriz-client/src/matriz_client/__init__.py"
    - "packages/matriz-client/tests/conftest.py"
    - "packages/matriz-client/tests/test_client.py"
    - "packages/matriz-client/tests/test_ws_client.py"
    - "packages/matriz-client/tests/test_fixture_reaches_production.py"
    - "packages/ambito-financiero-client/tests/test_harness_mutation_gate.py"
    - "verification/snapshots/matriz-client-surface.txt"

key-decisions:
  - "PEP 562 shim allowlist EXTENDED for matriz only to forward _base_url, satisfying verification/mutation_gate.py:55 without touching that file (Open Q #4, B6 closure)."
  - "AsyncClient is a STUB with lifecycle only — no _ensure_token, no _request, no REST methods, no top-level shims. Phase 10 REFAC-04 grows it (Open Q #1)."
  - "ws_client.py uses explicit _rest._get_default()._state.* at the cross-module boundary for clarity in code review (not the PEP 562 shim path)."
  - "No module-level callable _ensure_token shim — W5 closure: ws_client.py is fully migrated to call the instance method, so the function form would be dead code. Tests patch Client._ensure_token on the class instead."
  - "configure() resets token cache when base/cred kwargs change without explicit token kwargs; preserves cache when token/token_expires_at provided (covers both 'rotate creds' and 'preload sentinel' use cases)."

patterns-established:
  - "matriz PEP 562 shim extended allowlist — _base_url forwarded specifically to keep verification/mutation_gate.py syntactically unchanged. Other packages should NOT forward _base_url; this is a matriz-only mitigation for Open Q #4."
  - "Stub AsyncClient docstring documents B8 forward-looking rule: when Phase 10 grows the REST surface, _raise_for_response MUST be imported from client.py — do NOT duplicate."
  - "Tests that need to override Client.login or Client._ensure_token monkeypatch the CLASS (not instance, since __slots__ disallows new instance attributes)."

requirements-completed: [REFAC-02]

# Metrics
duration: 13min
completed: 2026-06-11
---

# Phase 06 Plan 06: Matriz Compat-Safety-Net Client-Class Skeleton Summary

**Matriz-client `Client` (sync, full REST) + stub `AsyncClient` (lifecycle only) on a shared `_ClientState` dataclass, with PEP 562 shim forwarding `_base_url` for `verification/mutation_gate.py`, `ws_client.py` migrated to `_get_default()._state.*`, and the cross-package ambito mutation-gate test on `configure(base_url=...)`.**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-06-11T02:44:05Z
- **Completed:** 2026-06-11T02:56:14Z
- **Tasks:** 2
- **Files modified:** 9 (3 created, 6 modified) + 1 regenerated snapshot

## Accomplishments

- `matriz_client.Client` synchronous class with the full REST surface (segments, instruments, orders, market data, trades, risk API) plus context-manager lifecycle and redacted `__repr__`.
- `matriz_client.AsyncClient` stub class (Open Q #1 resolution) — `__init__`/`__aenter__`/`__aexit__`/`aclose`/`__repr__`/`__reduce__`/`__deepcopy__` only. Phase 10 REFAC-04 will grow the REST surface.
- `_state.py` `@dataclass(slots=True) _ClientState` shared between sync and stub async; legacy `_token_ts` renamed to `token_expires_at` (D-04); `_session` absorbed into `http_client` (Pitfall #5).
- PEP 562 read-only shim on `matriz_client.client` forwards `_token`/`_token_ts`/`_base_url`/`_session`/`_client` to the default singleton's state, raising `AttributeError` for `_user`/`_password` (security hardening). The `_base_url` forwarding (Open Q #4) means `verification/mutation_gate.py:55` continues to work syntactically unchanged.
- `ws_client.py` cross-module reads migrated to `_rest._get_default()._state.base_url` / `_rest._get_default()._ensure_token()` / `_rest._get_default()._state.token`. W5 closure: no module-level callable `_ensure_token` shim.
- `matriz_client.configure()` extended with `token` and `token_expires_at` keyword arguments (D-04) — test fixtures preload sentinel tokens through the public API instead of monkeypatching module globals.
- Cross-package `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py` migrated from `monkeypatch.setattr(matriz_client.client, "_base_url", url)` to `matriz_client.configure(base_url=url)` (Pitfall #4).
- Per-package guard `packages/matriz-client/tests/test_fixture_reaches_production.py` migrated to `configure(token=..., token_expires_at=...)` (B3 — owned exclusively by this plan in Wave 1). Async guard remains `pytest.skip` for Phase 10.
- Public-surface snapshot regenerated: matriz now lists `Client` and `AsyncClient`; baseline preserved (D-06).

## Task Commits

Each task was committed atomically:

1. **Task 1: `_state.py` + `Client` sync + `ws_client.py` + sync test migration + cross-package mutation_gate migration** — `f838348` (feat)
2. **Task 2: stub `AsyncClient` in `aio.py` + `__init__.py` re-export + snapshot regen + per-package guard migration** — `36267d3` (feat)

_Note: both tasks were TDD — RED tests added then GREEN implementation in the same commit (single-commit cycle per task)._

## Files Created/Modified

### Created
- `packages/matriz-client/src/matriz_client/_state.py` — `@dataclass(slots=True) _ClientState` with `base_url/username/password/token/token_expires_at/http_client/account_id` + env factories + `_TOKEN_TTL`/`_REQUEST_TIMEOUT` constants.
- `packages/matriz-client/src/matriz_client/aio.py` — stub `AsyncClient` class (lifecycle only) + module docstring documenting Phase 10 REFAC-04 plan and B8 rule for future REST surface.
- `packages/matriz-client/tests/test_client_class.py` — skeleton tests for sync `Client` (lifecycle, repr redaction, pickle/deepcopy raise, configure carry-forward, instance isolation, D-22 X-Auth-Token header semantics, PEP 562 shim coverage including `_base_url`, W5 closure, mutation_gate via shim, ws_client url derivation, source-grep regression) + async stub tests.

### Modified
- `packages/matriz-client/src/matriz_client/client.py` — replaced module-global state with `Client` class + lazy default singleton + top-level shims; PEP 562 `__getattr__` shim with matriz-specific `_base_url` extension and `_session`/`_client` forwarding; CR-01 dict-body guard + `_unwrap` envelope helper preserved; `_raise_for_response` extracted as stateless module helper (B8 forward-looking).
- `packages/matriz-client/src/matriz_client/ws_client.py` — `_ws_url()` now reads `_rest._get_default()._state.base_url`; `ws_connect()` uses `default._ensure_token()` and `default._state.token` for token-gate + header injection.
- `packages/matriz-client/src/matriz_client/__init__.py` — re-export `Client`, `AsyncClient`, `_get_default`; `__all__` adds `Client` and `AsyncClient`.
- `packages/matriz-client/tests/conftest.py` — autouse fixture switched to `matriz_client.configure(token=..., token_expires_at=...)`; teardown resets via `configure(base_url=..., username="", password="")` (token cache auto-resets when no explicit token kwarg).
- `packages/matriz-client/tests/test_client.py` — migrate `monkeypatch.setattr(_client, "_token"|"_token_ts"|"_user"|"_password", ...)` to direct writes on `_get_default()._state`; instance-method patches on `Client.login`/`Client._ensure_token`; `_request`/`_get` callers use `matriz_client._get_default()._request(...)`.
- `packages/matriz-client/tests/test_ws_client.py` — `monkeypatch.setattr(_rest, "_base_url", ...)` migrated to `matriz_client.configure(base_url=...)`.
- `packages/matriz-client/tests/test_fixture_reaches_production.py` — sync guard migrated to `configure(token=..., token_expires_at=...)`; docstring updated; async guard remains `pytest.skip` (Phase 10).
- `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py` — all 6 write sites migrated from `monkeypatch.setattr(matriz_client.client, "_base_url", url)` to `matriz_client.configure(base_url=url)`.
- `verification/snapshots/matriz-client-surface.txt` — adds `Client` and `AsyncClient`; `configure()` signature updated for D-04 kwargs; baseline entries preserved.

## Decisions Made

- **Token rename absorbed in configure semantics.** `configure()` now treats `(token, token_expires_at)` as optional explicit-override kwargs (D-04 extension). When omitted but `(base_url, username, password)` change, the token cache resets to `None`/`0.0` — keeping the legacy "rotate creds" semantic. This avoids the corner-case where conftest teardown leaves a stale token. Result: tests pre-seed token through `configure(token=...)` instead of writing to module globals.
- **PEP 562 shim allowlist extended for matriz only.** `_FORWARDED_TO_STATE` includes `_base_url` in addition to the standard `_token`/`_token_ts`. This is matriz-specific because `verification/mutation_gate.py:55` reads that exact attribute path. Documented as the Open Q #4 mitigation; other packages should NOT mirror this addition.
- **`ws_client.py` uses explicit accessor, not the shim.** `_rest._get_default()._state.base_url` makes the cross-module dependency obvious in code review. The PEP 562 shim would also work, but the explicit form is clearer ownership.
- **No module-level `_ensure_token` callable.** W5 closure: the shim only handles attribute reads; adding a callable would be dead code post-migration. Tests that previously did `monkeypatch.setattr(_client, "_ensure_token", fn)` now patch `_client.Client._ensure_token` (the class method).
- **Instance method patches use `monkeypatch.setattr(Client, name, fn)` not `monkeypatch.setattr(instance, name, fn)`.** `__slots__` disallows new instance attributes; patching at the class level is the supported route and is fixture-scoped by pytest's monkeypatch teardown.

## Deviations from Plan

None — the plan executed exactly as written, including all called-out wrinkles:
- D-22 X-Auth-Token-from-header login implemented verbatim.
- Open Q #1 stub `AsyncClient` with lifecycle only.
- Pitfall #5 `_session` → `http_client` rename absorbed.
- Open Q #4 `_base_url` shim extension added; `verification/mutation_gate.py` untouched (B6).
- W5 closure: no module-level `_ensure_token` shim function (`'_ensure_token' in matriz_client.client.__dict__` → `False`).
- B3 ownership: `packages/matriz-client/tests/test_fixture_reaches_production.py` migrated by this plan exclusively.
- Cross-package ambito test migrated.
- Snapshot regenerated; baseline preserved.

## Issues Encountered

- **`pytest.MonkeyPatch.setattr` on a `__slots__` instance fails silently for non-slot attributes.** Initially attempted `monkeypatch.setattr(default, "login", fake_login.__get__(default))` to override the bound method on the singleton; switched to `monkeypatch.setattr(_client.Client, "login", fake_login)` (patching the class method). Resolution baked into Task 1 commit.
- **`configure(token=None, token_expires_at=0.0)` ambiguity.** The first iteration of the conftest teardown passed both kwargs explicitly, but `token=None` was indistinguishable from "no override." Fixed by relying on the elif branch in `configure()` that auto-resets the token cache when `base/cred` changes without explicit token kwargs.

## User Setup Required

None — no external services or credentials added by this plan.

## Next Phase Readiness

- **Plan 07 (verification audit):** `verification/mutation_gate.py:55` is unchanged syntactically; the matriz PEP 562 shim's `_base_url` forwarding makes the gate logic transparent. Plan 07 owns any further audit. The smoke test `test_mutation_gate_reads_via_shim` in `test_client_class.py` proves the path still works.
- **Phase 10 REFAC-04 (matriz async REST):** The stub `AsyncClient` is ready to absorb the REST surface; `_state.py` already exposes `http_client` typed as `httpx.Client | httpx.AsyncClient | None`. When Phase 10 starts, the stub's docstring already calls out the B8 rule (import `_raise_for_response` from `client.py`, do NOT duplicate).
- **No blockers.** Full test suite (318 + 1 skip) is green; ruff + mypy strict clean.

## Self-Check: PASSED

Files exist:
- `packages/matriz-client/src/matriz_client/_state.py` — FOUND
- `packages/matriz-client/src/matriz_client/aio.py` — FOUND
- `packages/matriz-client/tests/test_client_class.py` — FOUND
- `packages/matriz-client/src/matriz_client/client.py` (modified) — FOUND
- `packages/matriz-client/src/matriz_client/ws_client.py` (modified) — FOUND
- `packages/matriz-client/src/matriz_client/__init__.py` (modified) — FOUND
- `packages/matriz-client/tests/conftest.py` (modified) — FOUND
- `packages/matriz-client/tests/test_client.py` (modified) — FOUND
- `packages/matriz-client/tests/test_ws_client.py` (modified) — FOUND
- `packages/matriz-client/tests/test_fixture_reaches_production.py` (modified) — FOUND
- `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py` (modified) — FOUND
- `verification/snapshots/matriz-client-surface.txt` (modified) — FOUND

Commits exist on worktree branch:
- `f838348` — FOUND (Task 1)
- `36267d3` — FOUND (Task 2)

---
*Phase: 06-compat-safety-net-client-class-skeleton*
*Completed: 2026-06-11*
