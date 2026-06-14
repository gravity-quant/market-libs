# Architecture Research — v1.1 Tech Debt Cleanup

**Domain:** HTTP client library refactor (module-singletons → `Client` class) with sync/async dedup, transport-layer retries, structured logging, and matriz `aio.py` creation
**Researched:** 2026-06-10
**Confidence:** HIGH (built on validated v1.0 architecture — `.planning/codebase/ARCHITECTURE.md`, 5 phases / 277 mocked tests / 14 live findings)

---

## 0. Scope and Constraints Recap

The v1.0 architecture is **frozen for v1.1**:

- 5 standalone uv workspace packages, **no shared internals between packages** (any helper must be duplicated 4x — by design).
- Per-package module-level singletons (`_token`, `_token_ts`/`_token_expires_at`, `_client`, `_base_url`, `_user`, `_password`).
- Dual surface: `client.py` (sync) and `aio.py` (async, independent state). matriz lacks `aio.py`.
- 277 mocked tests rely on `monkeypatch.setattr(pkg.client, "_token", "X", raising=False)` and `monkeypatch.setattr(pkg.aio, "_token", "X", raising=False)` — **back-compat MUST preserve module-attribute write semantics**.
- All public functions called as `pkg.fn(...)` and `await aio.fn(...)`. No `Client()` instantiation today.

The v1.1 milestone (`.planning/PROJECT.md`) layers SIX refactors on top, all non-breaking:

1. `Client` class per instance + module-level functions as compat layer.
2. Sync/async LOGIC dedup (param building, response parsing, error mapping, envelope unwrapping).
3. `aio.py` for matriz-client (mirroring REST surface; shares `_token` with `ws_client.py`).
4. Retries/backoff with jitter for 5xx/429/connection-errors, mutation-aware.
5. Structured stdlib `logging` integrated with `verification/redaction.py`.
6. Driver harness fix: `verification/findings.py` becomes merge-based.

---

## 1. System Overview — Target v1.1 Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                       Caller (application / notebook / test / driver)           │
└──────┬─────────────────────────┬────────────────────────────┬──────────────────┘
       │                         │                            │
   import pkg                from pkg import aio          pkg.Client(...)
   pkg.fn(...)               await aio.fn(...)           c = pkg.Client(...)
       │                         │                       c.fn(...)
       ▼                         ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  pkg/client.py (sync)          │   pkg/aio.py (async)        │ shared via:      │
│  ┌─────────────────────────┐   │   ┌────────────────────┐    │                   │
│  │ Module-functions        │   │   │ Module-functions   │    │                   │
│  │ (compat layer):         │   │   │ (compat layer):    │    │                   │
│  │  fn(...) →              │   │   │  async fn(...) →   │    │                   │
│  │   _default().fn(...)    │   │   │   _default().fn... │    │                   │
│  │                         │   │   │                    │    │                   │
│  │ _default(): Client      │   │   │ _default():        │    │                   │
│  │  - lazy singleton       │   │   │   AsyncClient      │    │                   │
│  │  - reads env on init    │   │   │  - lazy singleton  │    │                   │
│  │                         │   │   │                    │    │                   │
│  │ class Client:           │   │   │ class AsyncClient: │    │                   │
│  │  __init__(base_url,…)   │   │   │  __init__(…)       │    │                   │
│  │  fn(...)  ──────────────┼───┼───┼─►  uses _core.fn   │    │                   │
│  │  configure(...)         │   │   │  async fn(...)     │    │                   │
│  │  _request(...)          │   │   │  configure(...)    │    │                   │
│  │  _ensure_token()        │   │   │  _request(...)     │    │                   │
│  │  _state: _ClientState   │   │   │  _ensure_token()   │    │                   │
│  │                         │   │   │  _state: ...       │    │                   │
│  │ _DEFAULT: Client|None   │   │   │                    │    │                   │
│  │  (module-level, lazy)   │   │   │ _DEFAULT: AsyncCl. │    │                   │
│  │ _token, _client = ...   │◄──┼───┼── module-property  │    │                   │
│  │  (back-compat aliases   │   │   │   shim: aio._token │    │                   │
│  │   delegating to         │   │   │   reads from       │    │                   │
│  │   _DEFAULT._state)      │   │   │   _DEFAULT._state  │    │                   │
│  └─────────────────────────┘   │   └────────────────────┘    │                   │
└────────────────────────────────┴─────────────────────────────┴───────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  pkg/_core.py  (NEW — package-private, transport-agnostic)                       │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ build_login_request(state) → (method, path, headers, data)            │     │
│   │ parse_login_response(state, resp_status, headers, json) → new_token   │     │
│   │ build_quote_request(simbolo, *, mercado, plazo) → RequestSpec         │     │
│   │ parse_quote_response(json) → dict / Model                             │     │
│   │ build_movimientos_request(...) → RequestSpec                          │     │
│   │ parse_movimientos_response(json) → list[Movimiento]                   │     │
│   │ ...one builder/parser pair per endpoint                                │     │
│   │ raise_for_response(resp_status, body_text|json) → None | raises typed │     │
│   │ unwrap_envelope(data, key, endpoint) → Any | raises PrimaryAPIError   │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│   Pure functions: take state + inputs, return RequestSpec or parsed payload.    │
│   NO httpx.Client / no asyncio — transport-agnostic.                            │
│                                                                                  │
│  pkg/_transport.py (NEW — sync wrapper httpx.HTTPTransport subclass)            │
│   class RetryTransport(httpx.HTTPTransport):                                    │
│      handle_request(req) → retries 5xx/429/connect-err if req allows            │
│                                                                                  │
│  pkg/_atransport.py (NEW — async wrapper httpx.AsyncHTTPTransport subclass)     │
│   class AsyncRetryTransport(httpx.AsyncHTTPTransport): same logic               │
│                                                                                  │
│  pkg/_state.py (NEW — dataclass)                                                │
│   @dataclass class _ClientState:                                                │
│      base_url, user, password, token, token_expires_at, refresh_token, ...      │
│                                                                                  │
│  pkg/_logging.py (NEW — per-package logger setup)                               │
│   logger = logging.getLogger("pkg")  # NullHandler default                      │
│   log_event(event, **extra)   # structured, redaction-filter-applied            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                       ┌──────────────────────────┐
                       │  httpx.Client            │
                       │  httpx.AsyncClient       │
                       │  websocket-client (matriz only) │
                       └──────────────────────────┘
                                  │
                                  ▼
                       ┌──────────────────────────┐
                       │ External Financial APIs  │
                       └──────────────────────────┘
```

**Cross-package status:** This entire diagram **replicates 4 times** (iol, higyrus, ambito, matriz). No shared package — by design constraint. Each refactor is a 4× change.

---

## 2. New Modules Per Package (Delta vs v1.0)

| New File | Purpose | Per-Package | Imports From | Imported By |
|----------|---------|-------------|--------------|-------------|
| `_state.py` | `@dataclass _ClientState`: token, base_url, creds, expiry, refresh_token, log adapter | Yes (4×) | stdlib only | `client.py`, `aio.py` |
| `_core.py` | Pure transport-agnostic builders & parsers; one pair per endpoint; `raise_for_response`, envelope unwrap, param-building (`drop_none`) | Yes (4×) | `_state.py`, `exceptions.py`, `models.py`, `_params.py`/`_parsing.py` | `client.py`, `aio.py` |
| `_transport.py` | `class RetryTransport(httpx.HTTPTransport)`: backoff + jitter for 5xx/429/connect-err, mutation-aware via Request extension | Yes (4×) | `httpx`, stdlib `random` | `client.py` (Client.__init__) |
| `_atransport.py` | `class AsyncRetryTransport(httpx.AsyncHTTPTransport)` mirror | Yes (4×) | `httpx`, stdlib `asyncio`/`random` | `aio.py` (AsyncClient.__init__) |
| `_logging.py` | `logger = logging.getLogger(...)` with NullHandler; `LoggerAdapter` for structured extras; redaction filter | Yes (4×) | stdlib `logging`, `verification/redaction.py` patterns reused but redaction logic duplicated since `verification/` is non-published | `client.py`, `aio.py`, `_transport.py`, `_atransport.py` |

| Modified File | Change |
|---------------|--------|
| `client.py` | Adds `class Client` (instance state via `_state.py`); module-functions become thin `def fn(...): return _default().fn(...)`. **Keeps** module-level aliases `_token`, `_client`, `_base_url`, etc., implemented as **module `__getattr__`/`__setattr__` shims** that delegate to `_DEFAULT._state` — preserves `monkeypatch.setattr(pkg.client, "_token", ...)` semantics. |
| `aio.py` | Same as `client.py` for `class AsyncClient`. matriz `aio.py` is created from scratch. |
| `__init__.py` | Exports `Client` (and `AsyncClient` from aio submodule). Adds the new class names to `__all__`. Public functional API unchanged. |
| `exceptions.py` | Unchanged (4× duplication preserved). |
| `models.py` | Unchanged. `from_api` already pure — safe to call from `_core.py` parsers. |
| `ws_client.py` (matriz only) | Migrated from `_rest._token` / `_rest._ensure_token` to `_rest._default().state.token` / `_rest._default().ensure_token()`. Module-level alias `_rest._token` continues to resolve via the `__getattr__` shim, so `ws_client.py` keeps working unchanged — but should be cleaned up. |

---

## 3. Pattern A — Client Class + Back-Compat Layer

### 3.1 Pattern

```python
# pkg/client.py

from __future__ import annotations
import os
from dotenv import load_dotenv
import httpx
from pkg._state import _ClientState
from pkg._transport import RetryTransport
from pkg._core import build_quote_request, parse_quote_response, raise_for_response
from pkg.exceptions import IOLAuthError

load_dotenv()


class Client:
    """Stateful HTTP client. Multiple instances are independent."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        http_client: httpx.Client | None = None,
        retries: int = 2,
        backoff_base: float = 0.5,
    ) -> None:
        self._state = _ClientState(
            base_url=(base_url or os.getenv("IOL_BASE_URL", DEFAULT_BASE_URL)).rstrip("/"),
            user=username or os.getenv("IOL_USER", ""),
            password=password or os.getenv("IOL_PASSWORD", ""),
            token=None,
            token_expires_at=0.0,
            refresh_token=None,
        )
        self._http = http_client or httpx.Client(
            transport=RetryTransport(retries=retries, backoff_base=backoff_base),
            timeout=_REQUEST_TIMEOUT,
        )

    def configure(self, *, base_url=None, username=None, password=None) -> None:
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if username is not None:
            self._state.user = username
        if password is not None:
            self._state.password = password
        self._state.token = None
        self._state.refresh_token = None
        self._state.token_expires_at = 0.0

    def login(self) -> str: ...           # uses _core.build_login_request / parse
    def _ensure_token(self) -> None: ...  # operates on self._state
    def _request(self, method, path, *, params=None, json_body=None) -> httpx.Response: ...

    def get_quote(self, simbolo: str, *, mercado="bcba", plazo="t2") -> dict[str, Any]:
        spec = build_quote_request(simbolo, mercado=mercado, plazo=plazo)
        resp = self._request(spec.method, spec.path, params=spec.params)
        return parse_quote_response(resp.json())


# ----- Back-compat layer: module-level default + delegating functions -----

_DEFAULT: Client | None = None


def _default() -> Client:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Client()
    return _DEFAULT


def configure(*, base_url=None, username=None, password=None) -> None:
    _default().configure(base_url=base_url, username=username, password=password)


def login() -> str:
    return _default().login()


def get_quote(simbolo, *, mercado="bcba", plazo="t2") -> dict[str, Any]:
    return _default().get_quote(simbolo, mercado=mercado, plazo=plazo)


# ----- Module __getattr__ / __setattr__ shim: preserves monkeypatch semantics -----

_STATE_ALIASES = {
    "_token": "token",
    "_token_expires_at": "token_expires_at",
    "_refresh_token": "refresh_token",
    "_base_url": "base_url",
    "_user": "user",
    "_password": "password",
}


def __getattr__(name: str) -> Any:
    if name in _STATE_ALIASES:
        return getattr(_default()._state, _STATE_ALIASES[name])
    if name == "_client":
        return _default()._http
    raise AttributeError(name)
```

**Caveat:** Python module `__setattr__` is **not** invoked for attribute assignment on modules in CPython — only `__getattr__` is supported (PEP 562). To support test code that does `monkeypatch.setattr(pkg.client, "_token", "X", raising=False)`, we exploit the fact that `monkeypatch.setattr` writes to `module.__dict__` directly via `setattr(module, name, value)`. That assignment **does** land in `module.__dict__` and from then on `__getattr__` is bypassed (since the attribute now exists). So the contract becomes:

- **Read:** `pkg.client._token` → if not in `__dict__`, `__getattr__` returns `_default()._state.token`.
- **Write via monkeypatch:** `monkeypatch.setattr(pkg.client, "_token", "X")` → writes `"X"` into `pkg.client.__dict__["_token"]`. Subsequent reads return `"X"` (shim bypassed).
- **Test teardown:** `monkeypatch` undoes its writes → `_token` removed from `__dict__` → shim resumes.

Net effect: **monkeypatch tests keep working unchanged**, but the shim must mirror reads back to `_state` only when the attribute is **not** in the module dict. This is a known correctness pattern (PEP 562; used by e.g. `attrs`, `dataclasses` for deprecation aliases).

**Alternative pattern (safer if monkeypatch behavior surprises us):** Use a fixture-detected shim where tests must call `pkg.test_setattr("_token", "X")` instead. Rejected — would break 277 existing tests. Stay with PEP 562 + `__dict__` interception.

### 3.2 `configure()` Semantics With Multiple Clients

| Scenario | Behavior |
|----------|----------|
| `pkg.configure(...)` | Affects the **module default** Client only. Existing user-instantiated `c = pkg.Client(...)` instances are unaffected. |
| `c = pkg.Client(base_url=..., username=..., password=...)` | Independent instance, env vars used only as fallback at `__init__`. |
| `c.configure(...)` | Mutates only `c._state`. Module default and other instances unaffected. |
| User instantiates `c1 = pkg.Client()` after `pkg.configure(...)` was called | `c1` reads env vars at init — **does not** inherit module-default's overrides. Document this clearly in the `Client` docstring. |

**Decision:** `configure()` on the default is module-scoped; instance `configure()` is instance-scoped. This is the only consistent model with "independent instances."

### 3.3 Threading (Sync)

Unchanged from v1.0:
- `httpx.Client` is **not** thread-safe for concurrent requests on the same client. The library docs and common practice ([encode/httpx#1633](https://github.com/encode/httpx/issues/1633)) say: do not share a single `Client` across threads.
- **v1.1 stance:** A `Client` instance is single-threaded. Multiple threads → multiple `Client` instances. This is the **same restriction as today** — the singleton was already single-threaded.
- Token refresh is non-locked in sync (was non-locked in v1.0 too). Adding a `threading.Lock` is **out of scope** for v1.1 unless we discover a regression — flagged in PITFALLS.

### 3.4 Mapping Existing Tests Onto The Refactor

| Existing test pattern | Continues to work because |
|-----------------------|---------------------------|
| `iol_client.configure(base_url=..., username=..., password=...)` | Module function delegates to `_default().configure(...)` — same effect. |
| `monkeypatch.setattr(iol_client.client, "_token", "X", raising=False)` | Writes into `module.__dict__["_token"]`. Reads bypass shim. Internal Client methods read `self._state.token` — **must** check module dict first, OR the shim must mirror writes back. **See section 3.5.** |
| `monkeypatch.setattr(aio, "_token", "X", raising=False)` | Same as above. |
| `_client._ensure_token()` called as private (some tests) | Module-level alias `_ensure_token = lambda: _default()._ensure_token()` keeps this working. |

### 3.5 The `monkeypatch._token` Round-Trip Problem (CRITICAL)

**Problem:** If `Client._request(...)` reads `self._state.token` directly, but the test did `monkeypatch.setattr(pkg.client, "_token", "X")`, the override **lives in module `__dict__` not in `self._state`** — internal reads bypass the override.

**Solution options:**

1. **Internal reads through module property** — `Client._request` reads `pkg.client._token` (via module-level access). Ugly, couples Client to its hosting module. **Rejected.**
2. **Sync the override into `_state` via PEP 562 `__getattr__`** — won't work for writes.
3. **Compat-layer adapter:** Internal Client reads `self._state.token`. The **test fixture is updated** to use `pkg.configure(...)` to pre-load tokens (which writes through to `_state.token`). 277 tests have a one-time conftest update — `monkeypatch.setattr` lines are replaced with `pkg.configure(token=...)` (extending `configure` to accept a `token` kw for tests). **CHOSEN — clean, no test churn beyond conftest.**
4. **Hybrid:** Keep `monkeypatch.setattr(...)` working via a custom `__setattr__`-equivalent. Python doesn't support module `__setattr__` natively — would require replacing the module with a `class`-subclassed module (advanced, fragile). **Rejected** as risky.

**Adopted:** Option 3. Each of the 5 conftest.py files (per-package, sync + async) gets the same 2-line change:

```python
# Before (v1.0)
monkeypatch.setattr(iol_client.client, "_token", "test-token", raising=False)
monkeypatch.setattr(iol_client.client, "_token_expires_at", 9_999_999_999.0, raising=False)

# After (v1.1) — extend Client.configure to accept these for testing
iol_client.configure(token="test-token", token_expires_at=9_999_999_999.0)
```

Net delta: ~20 lines of conftest changes across 5 packages × 2 surfaces. The shim from §3.1 is **still useful** for any caller that does `pkg._token` reads (rare, but matriz `ws_client.py` does it — see §6.1).

---

## 4. Pattern B — Sync/Async Logic Dedup

### 4.1 Where Shared Logic Lives

| Module | Contains | Why pure (transport-agnostic) |
|--------|----------|-------------------------------|
| `_core.py` | Per-endpoint `build_X_request(...) → RequestSpec(method, path, params, json_body, headers, idempotent: bool)` and `parse_X_response(json_body) → typed result`; `raise_for_response(status, body)` exceptions mapping; `unwrap_envelope(data, key, endpoint)` for matriz/higyrus; auth-flow primitives `build_login_request(state)`, `parse_login_response(state, resp) → new_state_fields` | Returns specs, not Responses; takes JSON dicts, not httpx.Response objects. No `await`. No I/O. |
| `_state.py` | Mutable `@dataclass _ClientState` | No I/O. |
| `_params.py` / `_parsing.py` | Already exist for higyrus + ambito. Stay as-is. | Already pure. |

`Client` (sync) and `AsyncClient` (async) become **transport shells**: ~30-50 LOC each per endpoint group, mostly:

```python
# sync Client
def get_quote(self, simbolo, *, mercado="bcba", plazo="t2"):
    spec = _core.build_quote_request(simbolo, mercado=mercado, plazo=plazo)
    resp = self._request(spec)            # httpx.Client.request
    _core.raise_for_response(resp.status_code, resp.text)
    return _core.parse_quote_response(resp.json())

# async AsyncClient
async def get_quote(self, simbolo, *, mercado="bcba", plazo="t2"):
    spec = _core.build_quote_request(simbolo, mercado=mercado, plazo=plazo)
    resp = await self._request(spec)      # httpx.AsyncClient.request
    _core.raise_for_response(resp.status_code, resp.text)
    return _core.parse_quote_response(resp.json())
```

Identical bodies except for the transport step. The bug-prone divergences from v1.0 (e.g., higyrus envelope unwrap missing in async only) **become impossible** because there's one builder/parser.

### 4.2 Import Topology

```
exceptions.py ─────────────────────────────┐
models.py ─────┐                            │
_params.py ────┤                            │
_parsing.py ───┤                            │
_state.py ─────┤                            │
               ▼                            ▼
            _core.py ◄──── used by ──── client.py  (sync, has class Client)
                      ◄──── used by ──── aio.py    (async, has class AsyncClient)
            _transport.py ◄────────────── client.py
            _atransport.py ◄───────────── aio.py
            _logging.py ◄──────────────── client.py + aio.py + _transport + _atransport
```

**No circular imports.** `_core.py` imports nothing transport-specific. `client.py` and `aio.py` never import from each other (preserves v1.0 constraint).

**One exception:** `iol_client.aio` currently imports the `InstrumentType` Literal from `iol_client.client`. In v1.1, move `InstrumentType` to a new `pkg/_typing.py` or `pkg/types.py` (iol does not have `types.py` yet — would create) so both client and aio import from there. Trivial.

### 4.3 Auth Flow Sharing

Auth has TWO concerns that split cleanly:

- **Pure (in `_core.py`):**
  - `build_login_request(state) → RequestSpec` — builds `POST /token` body + headers.
  - `parse_login_response(state, status, headers, json_body) → tuple[new_token, expires_at, new_refresh_token]` — extracts and validates.
- **Transport (in `Client` / `AsyncClient`):**
  - Acquires lock (asyncio for async, none for sync).
  - Calls `self._http.post(...)` or `await self._http.post(...)`.
  - Writes results into `self._state`.

```python
# Client (sync)
def login(self) -> str:
    spec = _core.build_login_request(self._state)
    resp = self._http.request(spec.method, spec.url, data=spec.data, headers=spec.headers)
    _core.raise_for_response(resp.status_code, resp.text)
    token, expires_at, refresh = _core.parse_login_response(resp.status_code, resp.headers, resp.json())
    self._state.token = token
    self._state.token_expires_at = expires_at
    if refresh:
        self._state.refresh_token = refresh
    return token

# AsyncClient (async)
async def login(self) -> str:
    async with self._token_lock:
        return await self._login_unlocked()

async def _login_unlocked(self) -> str:
    spec = _core.build_login_request(self._state)
    client = await self._ensure_http_client()
    resp = await client.request(spec.method, spec.url, data=spec.data, headers=spec.headers)
    _core.raise_for_response(resp.status_code, resp.text)
    token, expires_at, refresh = _core.parse_login_response(resp.status_code, resp.headers, resp.json())
    self._state.token = token
    self._state.token_expires_at = expires_at
    if refresh:
        self._state.refresh_token = refresh
    return token
```

**Double-checked locking** for `_ensure_token` async stays at the AsyncClient layer (locks are transport-specific). The decision **whether** to refresh (state check) goes into `_core.is_token_fresh(state, now) → bool` — pure, callable from both.

### 4.4 What Stays Duplicated (And Why It's OK)

- The transport-specific glue (`self._http.request(...)` vs `await self._http.request(...)`) — irreducibly different.
- `asyncio.Lock()` vs no-lock — transport-specific.
- `httpx.Client` vs `httpx.AsyncClient` instantiation — transport-specific.
- `aclose()` (async only) — transport-specific.
- The 30-40 LOC of public endpoint wrappers — duplicated SHELLS but **call shared `_core.build_X / parse_X`**, so any logic bug fix is one place.

Estimated LOC reduction in `client.py + aio.py` per package: **30-40% smaller** (depending on package; higyrus and matriz have the most duplicated logic — higyrus particularly because of the 10-site envelope unwrap bug fixed in Phase 4 that exemplifies why dedup matters).

---

## 5. Pattern C — Retries Integration

### 5.1 Layer Decision

Implement as a **custom `httpx.HTTPTransport` subclass** (and `httpx.AsyncHTTPTransport` mirror). **Rationale:**

- `httpx.HTTPTransport(retries=N)` only retries `ConnectError`/`ConnectTimeout` (verified against httpx 0.27+ docs — HIGH confidence). It does **not** retry 5xx/429. So we cannot just pass `retries=2` to the built-in.
- A custom Transport sits at the right layer:
  - Below `httpx.Client.request` so it sees the final wire request (after auth headers injected).
  - Above the socket so it can sleep + retry transparently.
  - Independent of whether `Client` or `AsyncClient` is the caller.
- Decorator on `_request` (alternative): would couple retries to the API method layer, would need separate sync/async wrappers, and would interfere cleanly with `_ensure_token` flow.

### 5.2 Mutation Awareness — The Double-Gate

The harness has a `mutating_allowed` double-gate that prevents POST/PUT/DELETE against prod by default. The retry layer **must respect** this, but in a different way: even when `mutating_allowed=True`, we should **not** retry mutations except idempotent ones (PUT, DELETE — sometimes; POST — never).

**Mechanism — request extension:**

```python
# pkg/_core.py
class RequestSpec(NamedTuple):
    method: str
    url: str
    params: dict | None
    data: dict | None
    json_body: dict | None
    headers: dict
    idempotent: bool  # True for GET/HEAD/OPTIONS; False for POST/PUT/DELETE by default

# pkg/_transport.py
class RetryTransport(httpx.HTTPTransport):
    def __init__(self, *args, retries=2, backoff_base=0.5, **kwargs):
        super().__init__(*args, **kwargs)
        self._retries = retries
        self._backoff_base = backoff_base

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        idempotent = request.extensions.get("idempotent", request.method in ("GET","HEAD","OPTIONS"))
        attempts = 0
        last_exc: Exception | None = None
        while True:
            try:
                resp = super().handle_request(request)
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                if attempts >= self._retries:
                    raise
                _sleep_with_jitter(self._backoff_base, attempts)
                attempts += 1
                last_exc = e
                continue
            # Status-based retry — only if idempotent OR explicitly retry-safe
            if resp.status_code in (502, 503, 504) and idempotent and attempts < self._retries:
                _sleep_with_jitter(self._backoff_base, attempts)
                attempts += 1
                continue
            if resp.status_code == 429 and attempts < self._retries:
                # Honor Retry-After if present
                delay = _parse_retry_after(resp.headers.get("Retry-After")) or _sleep_with_jitter_value(self._backoff_base, attempts)
                time.sleep(delay)
                attempts += 1
                continue
            return resp
```

`Client._request` and `AsyncClient._request` set `request.extensions["idempotent"] = spec.idempotent` before dispatch.

**No backdoor to `mutating_allowed`:** The retry layer never checks the harness flag — it checks the per-request `idempotent` extension, set by `_core.RequestSpec`. POST endpoints have `idempotent=False` by default → never retried regardless of harness flag.

### 5.3 Retries + Token Refresh Interaction

**Problem:** If a request 401s because the token expired between `_ensure_token()` and the wire call, retrying the same request with the same (now-stale) header is pointless.

**Resolution:** The retry transport does **not** retry on 401. 401 returns immediately and `_raise_for_response` in `_core.py` raises `AuthError`. The next call (or a higher-level retry-on-AuthError-once policy in `_request`) re-triggers `_ensure_token()`. **Out of scope for v1.1:** automatic re-login on 401-mid-request. Document as Phase Y consideration.

### 5.4 Counter Reset

Per-call. Each new `Client._request(...)` call constructs a new `httpx.Request`, which enters `handle_request` with `attempts=0`. No cross-call counter state.

### 5.5 Logging Integration

The transport logs retry attempts via the package logger (`pkg/_logging.py`):

```python
logger.warning("retry", extra={"event": "retry", "attempt": attempts, "url": str(request.url), "status": resp.status_code})
```

Redaction filter (§7.3) scrubs the URL of credentials before output.

---

## 6. Pattern D — Structured Logging Integration

### 6.1 Logger Naming

Per-package single namespaced logger:

```python
# pkg/_logging.py
import logging
logger = logging.getLogger("iol_client")   # 4× per package
logger.addHandler(logging.NullHandler())   # silent unless caller configures handlers
```

**Decision:** ONE logger per package (not per submodule). Sub-events tagged via `extra={"event": "..."}`, not via logger name. Rationale: simpler for consumers to enable (`logging.getLogger("iol_client").setLevel(logging.INFO)` covers everything). Submodule sub-loggers add operational complexity without clear value at this scale.

### 6.2 Where Log Calls Live

| Site | Level | Event tag | Extras |
|------|-------|-----------|--------|
| `Client.login()` after success | INFO | `auth.login.ok` | `expires_in`, `has_refresh_token` |
| `Client.login()` on 401 | WARNING | `auth.login.failed` | `status_code` |
| `Client._ensure_token()` triggers refresh | DEBUG | `auth.token.refresh` | `reason="expired"\|"absent"` |
| `Client._request()` start | DEBUG | `http.request.start` | `method`, `path` (NOT full URL with query, see redaction) |
| `Client._request()` on 5xx | WARNING | `http.request.error` | `method`, `path`, `status_code` |
| `RetryTransport.handle_request` retry | WARNING | `http.retry` | `attempt`, `delay_seconds`, `reason` |
| `RetryTransport` exhausted | ERROR | `http.retry.exhausted` | `attempts`, `last_status` |

Log calls live in: `_transport.py` / `_atransport.py` (HTTP layer), `client.py` / `aio.py` (auth + high-level endpoints). NOT inside `_core.py` (pure functions — must remain side-effect free).

### 6.3 Redaction

`verification/redaction.py` already implements Bearer + credential patterns. Since `verification/` is **not** published with the packages, the redaction LOGIC must be duplicated per-package in `_logging.py`. The patterns are identical and stable (Bearer regex, basic-auth tuples, `Authorization` header values).

```python
# pkg/_logging.py
import re

_BEARER_RE = re.compile(r"(Bearer\s+)([A-Za-z0-9._\-]+)")
_AUTH_TOKEN_HEADERS = {"authorization", "x-auth-token", "x-password"}

class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Scrub msg + extras
        if isinstance(record.msg, str):
            record.msg = _BEARER_RE.sub(r"\1***", record.msg)
        for k in list(record.__dict__):
            v = record.__dict__[k]
            if isinstance(v, str):
                record.__dict__[k] = _BEARER_RE.sub(r"\1***", v)
        return True
```

Filter is attached to the package logger by default. Even with handlers installed by consumers, secrets are scrubbed at filter time before formatter.

**Alternative considered:** Scrub at formatter level. **Rejected** — formatters are consumer-controlled; filter at our logger guarantees redaction regardless of consumer config.

### 6.4 Testing Log Events Without Format Coupling

Pattern: use `caplog` fixture and assert on `record.extra` (event tag + structured fields), not formatted message:

```python
def test_login_logs_success(httpx_mock, caplog):
    caplog.set_level(logging.INFO, logger="iol_client")
    httpx_mock.add_response(url=..., json={"access_token": "tok", "expires_in": 900})
    iol_client.login()
    auth_logs = [r for r in caplog.records if getattr(r, "event", None) == "auth.login.ok"]
    assert len(auth_logs) == 1
    assert auth_logs[0].expires_in == 900
```

Format-agnostic. The structured `extra={"event": "auth.login.ok", ...}` becomes the testing contract.

---

## 7. Pattern E — matriz aio.py Specifics

### 7.1 Shared Token Cache With ws_client.py

v1.0: `ws_client.py` does `from matriz_client import client as _rest; _rest._ensure_token(); _rest._token`.

v1.1 with `Client` class:
- `matriz_client.client` exposes a module-level default Client via `_default()`.
- The PEP 562 `__getattr__` shim (§3.1) makes `_rest._token` continue to read from `_default()._state.token` — **`ws_client.py` keeps working with zero changes**.
- New `matriz_client.aio` exposes `_default_async()` returning an `AsyncClient` with its **own** `_state` (independent from sync, just like iol/higyrus).
- **DECISION:** The sync and async `_state` are independent — they do **NOT** share a token cache. Mirror of v1.0 iol/higyrus/ambito design. The user of async must `await aio.login()` once even if sync already has a cached token.
- Cleanup migration: `ws_client.py` migrates to `_rest._default().ensure_token()` and `_rest._default().state.token` directly (no shim) as a low-risk follow-up commit.

**Why not share state sync↔async?** Two reasons:
1. `httpx.Client` and `httpx.AsyncClient` cannot share a connection pool — they're different objects with different lifecycles.
2. `asyncio.Lock()` cannot be acquired from sync context. A shared state would force one or the other to give up its concurrency-safety primitive.

The price: two logins (once sync, once async) if both surfaces are used in the same process. Already the case for iol/higyrus/ambito. Acceptable.

### 7.2 asyncio.Lock Acquisition

matriz `AsyncClient` mirrors iol/higyrus async pattern (§4.3):
- `_token_lock = asyncio.Lock()` per instance.
- `_client_lock = asyncio.Lock()` per instance for lazy `httpx.AsyncClient` creation.
- WebSocket caller (`ws_client.py`) does NOT coordinate with async REST — it uses the sync client's token only. If a future v1.2 introduces an async WebSocket layer, it would need its own lock or share with `AsyncClient` — out of scope.

### 7.3 Live Verification for matriz async

**Decision:** Extend `main_matriz.py` with an `--async` flag (or a `verify_async()` function in the same script) that re-runs the same probes through the async surface. Rationale:
- Same env, same gates, same mutation policy.
- Same findings file (`matriz-findings.md`) — the source of one bug whether sync or async surfaces it.
- iol / higyrus already use one `main_*.py` for sync + async. Consistent.

`main_matriz_async.py` (separate file) would duplicate ~1500 LOC. Rejected.

### 7.4 matriz Bug Bundle Interaction

The deferred fixes (F-09 ERROR-MAP, F-02 higyrus envelope, IOL refresh_token, HIGY multi-account) **block on `_core.py`**:
- F-09 (matriz ERROR-MAP): pure logic — implement in `_core.raise_for_response()` once, async surface gets it for free.
- F-02 (higyrus): logic — implement in `_core.parse_listado_cuentas()`.
- IOL refresh_token persistence: already fixed (D-IOL-9/D-IOL-10 in Phase 3); v1.1 may add disk-persistence — pure state.
- HIGY multi-account: pagination loop in `_core.iter_movements_pages(...)` generator; both surfaces wrap.

All four fixes become **simpler** post-dedup. Build order recommendation: do `_core.py` extraction **before** F-09/F-02 to avoid 2× fix application.

---

## 8. Build Order & Phase Decomposition

### 8.1 Dependency DAG

```
                    [Phase 0: Compat & Tests Safety Net]
                     - Golden public-surface tests (snapshot all module attrs/sigs)
                     - Document monkeypatch.setattr migration plan
                                │
                                ▼
                    [Phase 1: Client class skeleton + back-compat shim]
                     - One pkg at a time (iol → higyrus → ambito → matriz)
                     - Module shim (PEP 562 __getattr__) preserves _token reads
                     - configure() extended to accept token / token_expires_at kwargs
                     - All 277 mocked tests pass (conftest updated to use configure(token=...))
                                │
                                ▼
                    [Phase 2: _core.py extraction (sync/async dedup)]
                     - Per package: extract builders/parsers
                     - client.py and aio.py become shells over _core
                     - Existing tests still pass (golden test catches regressions)
                                │
            ┌───────────────────┼────────────────────┐
            ▼                   ▼                    ▼
[Phase 3a: matriz aio.py]  [Phase 3b: retries]  [Phase 3c: structured logging]
 - New AsyncClient         - RetryTransport      - Logger + redaction filter
 - mirror REST surface     - _core.RequestSpec   - Wire into _request + login
 - independent _state        carries idempotent  - Caplog tests
                                │                    │
                                └────────┬───────────┘
                                         ▼
                    [Phase 4: Deferred fixes leveraging the new arch]
                     - F-09 matriz ERROR-MAP (single _core fix → both surfaces)
                     - F-02 higyrus get_listado_cuentas=0
                     - IOL refresh_token persistence
                     - HIGY multi-account iteration
                                │
                                ▼
                    [Phase 5: Driver harness fixes]
                     - verification/findings.py merge-based parser/writer
                     - D-MATZ-27 dedupe across drivers
                     - WR-01..WR-08 code review concerns
                                │
                                ▼
                    [Phase 6: Live re-verification (no findings expected)]
                     - Re-run main_*.py against live APIs
                     - Confirm no regressions vs v1.0 cycle
                     - Update verification baselines if needed
```

### 8.2 Why This Order

- **Phase 0 first:** Without a golden test snapshot, we cannot prove non-breaking. This phase deserves a research flag.
- **Phase 1 before Phase 2:** Extracting `_core.py` is much easier when the class shell exists to hold the wired-in pure-function calls.
- **Phase 2 before retries/logging:** `_core.RequestSpec.idempotent` is required by retries. Endpoint metadata centralization is a prereq.
- **Phase 2 before matriz aio:** Creating `matriz_client.aio` is cheap once `_core.py` exists — most of its body becomes "async shell over _core."
- **Phase 4 after Phase 2:** Fixes applied once in `_core.py` automatically fix both surfaces.
- **Phase 5 last (before verification):** Harness fixes don't depend on the package refactors, but they depend on test stability. Doing them after the structural work keeps the harness ergonomic for the re-verification step.

### 8.3 Parallelization Opportunities

- Phase 3a / 3b / 3c can run in parallel after Phase 2 closes.
- Across packages within Phase 1 (and Phase 2), each package is independent — could parallelize across packages, but recommend **serial** because each is a learning opportunity (apply lessons from iol → higyrus → ambito → matriz, the most complex).

### 8.4 Bug Fixes vs Refactors — Can They Be Done In Parallel?

| Fix | Independent of refactor? | Recommendation |
|-----|--------------------------|----------------|
| F-09 matriz ERROR-MAP | Yes, but applying twice (once now in v1.0 client.py, once after Phase 2 in _core.py) doubles work | **Defer to Phase 4** (after _core.py exists). |
| F-02 higyrus get_listado_cuentas=0 | Same | **Defer to Phase 4.** |
| IOL refresh_token persistence | Yes — modifies `_state`, orthogonal to class refactor | Could ship in **Phase 1** if low risk; **prefer Phase 4** for consistency. |
| HIGY multi-account iteration | Touches pagination logic — best as `_core` generator | **Defer to Phase 4.** |
| WR-01..WR-08 (code review) | Mix — some are docs, some are code | Triage per-item. Docs: Phase 0. Code: Phase 5 (lumped with harness). |
| Driver bug bundle (D-MATZ-27 + findings.py merge) | Independent of packages — touches `verification/` and main_*.py | **Phase 5.** |

---

## 9. Backward-Compatibility Verification Strategy

### 9.1 Golden Public-Surface Test

A `tests/test_public_api_surface.py` (one per package, conceptually but lives in `verification/` since cross-cuts) that snapshots **EVERY** public symbol's name and signature:

```python
# verification/test_public_surface.py (not part of pkg dist)
import inspect
import iol_client, higyrus_client, ambito_financiero_client, matriz_client
import iol_client.aio, higyrus_client.aio, ambito_financiero_client.aio  # noqa
from matriz_client import client as _matriz_sync

EXPECTED = {
    "iol_client": {
        "module_attrs": {"configure", "login", "get_quote", "get_historical_quotes",
                          "get_instruments", "get_instruments_by_type",
                          "IOLClientError", "IOLAPIError", "IOLAuthError", "IOLRateLimitError",
                          "__version__"},
        "function_sigs": {
            "get_quote": "(simbolo: str, *, mercado: str = 'bcba', plazo: str = 't2') -> dict[str, Any]",
            ...
        },
    },
    ...
}

def test_module_attrs_unchanged():
    for module_name, spec in EXPECTED.items():
        mod = importlib.import_module(module_name)
        actual = {a for a in dir(mod) if not a.startswith("_")}
        # v1.1 may ADD names (e.g., "Client") but must not REMOVE.
        missing = spec["module_attrs"] - actual
        assert not missing, f"{module_name} missing: {missing}"

def test_signatures_unchanged():
    for module_name, spec in EXPECTED.items():
        mod = importlib.import_module(module_name)
        for fn_name, expected_sig in spec["function_sigs"].items():
            fn = getattr(mod, fn_name)
            actual_sig = str(inspect.signature(fn))
            assert actual_sig == expected_sig, f"{module_name}.{fn_name}: {actual_sig} != {expected_sig}"
```

Snapshot v1.0 surface in Phase 0. Any signature drift fails CI before merge.

### 9.2 277 Mocked Tests as the Primary Net

Each phase must keep the existing test suite green. The conftest migration in §3.5 is one-time per phase. After that, no test should change.

### 9.3 main_*.py Drivers as Smoke

Drivers exercise the full public surface against live APIs. Running each driver (with creds + `--live` flag) before and after each phase smoke-tests the surface end-to-end. No assertion changes needed — the drivers print structured probe results.

### 9.4 Python 3.12 + 3.13 Matrix

Both supported. Architectural risks specific to 3.13:
- PEP 562 `__getattr__` is stable since 3.7 — no risk.
- `asyncio.Lock()` behavior unchanged in 3.13 — no risk.
- `typing.get_type_hints()` (used by `SafeModel.from_api`) — 3.13 has stricter handling of `from __future__ import annotations` resolution; **flag** in PITFALLS, run `SafeModel` tests in both versions to confirm.
- `httpx 0.27+` supports both — no risk.

CI matrix continues to run 3.12 + 3.13 for all 5 packages; that's the safety net.

### 9.5 Downstream Consumer Snapshot

Optionally: maintain a separate `verification/test_downstream_imports.py` that imports the packages exactly as a downstream consumer would (no internal imports), exercises the documented surface, and `mypy`-type-checks itself. This validates that the public type hints remain backward-compatible (e.g., a function whose return type narrows from `dict[str, Any]` to `Mapping[str, Any]` would be type-incompatible for callers).

---

## 10. Architectural Constraints Recap (v1.1)

| Constraint (from v1.0) | v1.1 enforcement |
|------------------------|-------------------|
| No shared code between packages | `_core.py`, `_state.py`, `_transport.py`, `_atransport.py`, `_logging.py` are duplicated 4× per package. CI lints for cross-package imports. |
| Threading: sync `Client` single-threaded | Inherited. Documented in `Client.__init__` docstring. |
| `aio` independent state from sync | Inherited. `AsyncClient` is independent from `Client`. matriz follows suit. |
| No `client.py` → `aio.py` import | Inherited. `_typing.py` (new) is the shared-types home for cross-surface Literals (iol `InstrumentType`). |
| `configure()` resets token | Inherited. Both `Client.configure()` and module-level `configure()` reset state. |
| Module-level `__init__.py` re-exports | Inherited. Adds `Client` and `AsyncClient` to `__all__`. |
| `SafeModel.from_api` tolerant deserialization | Unchanged. Models module untouched. |
| Exception hierarchy per package | Unchanged. |

---

## 11. Integration Points Summary

| Integration | v1.0 | v1.1 change | Risk |
|-------------|------|--------------|------|
| Caller → `pkg.fn(...)` | Direct module function | Delegates to `_default()` Client | None — back-compat guaranteed by test surface snapshot |
| Caller → `from pkg import aio; await aio.fn()` | Direct async module function | Delegates to `_default()` AsyncClient | None |
| Caller → `c = pkg.Client(...); c.fn()` | **N/A** | New surface | Net-new, documented |
| `monkeypatch.setattr(pkg.client, "_token", ...)` | Write to module global | Reads bypass shim (PEP 562) but internal Client reads `self._state.token`. Conftest migrates to `configure(token=...)`. | Medium — requires conftest pass per package; mitigated by Phase 0 golden test |
| matriz `ws_client.py` reads `_rest._token` | Direct module global | Reads via PEP 562 shim → `_default()._state.token` | Low |
| matriz `ws_client.py` calls `_rest._ensure_token()` | Direct module function | Module-level alias delegates to `_default()._ensure_token()` | Low |
| `verification/` consumes packages | Imports public API + private `client._token` for diagnostics | Public API unchanged; private reads via shim | Low |
| `main_*.py` drivers | Imports public API + matriz-specific helpers | Public API unchanged; matriz gets new `aio` surface for driver to exercise | Net-new test surface |

---

## 12. Open Architectural Questions (Roadmap Flags)

1. **Should `Client.__init__` accept `transport=` for full custom transport override?** Yes for testability — but check if any consumer needs to opt-out of `RetryTransport`. Default-on with opt-out path.
2. **Should retry counters be exposed via the logger or as `Client.metrics`?** Defer — Phase 6 may want this for the cycle report. Today: logger-only.
3. **Should `pkg.AsyncClient` and `pkg.Client` share an exception instance for typed `except`?** Already share `pkg.ClientError` hierarchy — no work needed.
4. **Threading-safety for sync `Client`:** If we ever multi-thread, `_ensure_token` needs a `threading.Lock`. Deferred. Document as risk in `PITFALLS.md`.
5. **What if `httpx` 0.28+ changes Transport API?** Pin major version in pyproject (`httpx>=0.27,<0.30`)? Or maintain transport wrappers compatible with both. **Recommend** pinning narrower range for v1.1 release; revisit on httpx 1.0.
6. **Per-package `_logging.py` redaction patterns drift:** the four copies could diverge over time. Add a single regression test fixture that asserts the BEARER_RE pattern is identical across packages (string equality of the source pattern). Cheap insurance.

---

## 13. Sources

- `.planning/codebase/ARCHITECTURE.md` (v1.0 architecture, HIGH confidence — validated through 277 tests + live verification)
- `.planning/codebase/CONVENTIONS.md` (file naming, future annotations, mypy strict)
- `.planning/codebase/TESTING.md` (autouse conftest patterns, monkeypatch usage, caplog)
- `.planning/codebase/STRUCTURE.md` (per-package directory layout)
- `.planning/PROJECT.md` (v1.1 milestone scope and constraints)
- `packages/iol-client/src/iol_client/client.py` (canonical sync singleton pattern, with D-IOL-9/D-IOL-10 refresh-token logic)
- `packages/iol-client/src/iol_client/aio.py` (canonical async mirror with double-checked locking)
- `packages/matriz-client/src/matriz_client/client.py` (no aio counterpart — pattern target for v1.1)
- `packages/matriz-client/src/matriz_client/ws_client.py` (consumes `_rest._token` directly — back-compat critical)
- All 5 `packages/*/tests/conftest.py` (monkeypatch.setattr pattern — migration target)
- httpx 0.27 docs ([transports](https://www.python-httpx.org/advanced/transports/)) — confirmed `HTTPTransport(retries=N)` only retries `ConnectError`/`ConnectTimeout`, NOT 5xx/429 (HIGH confidence)
- PEP 562 (module `__getattr__`, stable since Python 3.7)

---

*Architecture research for: market-libs v1.1 Tech Debt Cleanup*
*Researched: 2026-06-10*
