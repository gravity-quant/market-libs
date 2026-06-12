<!-- refreshed: 2026-05-27 -->
# Architecture

**Analysis Date:** 2026-05-27

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    Caller (application / notebook / test)                │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  ambito_ │ │higyrus_│ │  iol_  │ │ matriz_│ │wallets_│
│ financiero│ │ client │ │ client │ │ client │ │ client │
│  _client │ │        │ │        │ │        │ │        │
│`packages/│ │`pkg/   │ │`pkg/   │ │`pkg/   │ │`pkg/   │
│ambito-fin│ │higyrus-│ │iol-    │ │matriz- │ │wallets-│
│-client/` │ │client/`│ │client/`│ │client/`│ │client/`│
└──────────┘ └────────┘ └────────┘ └────────┘ └────────┘
       │          │          │          │          │
       └──────────┴──────────┴──────────┴──────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   httpx (sync   │
                    │   & AsyncClient)│
                    │  websocket-     │
                    │  client (matriz)│
                    └────────┬────────┘
                             │
                             ▼
               ┌─────────────────────────────┐
               │    External Financial APIs   │
               │  IOL · Higyrus · Primary     │
               │  Ámbito Financiero · Wallets │
               └─────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| `ambito_financiero_client` | Public FX rate scraping (no auth) | `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` |
| `higyrus_client` | Brokerage back-office (accounts, positions, movements) | `packages/higyrus-client/src/higyrus_client/client.py` |
| `iol_client` | IOL trading platform (quotes, instruments, OAuth) | `packages/iol-client/src/iol_client/client.py` |
| `matriz_client` | MATBA ROFEX Primary API (orders, market data, WS streaming) | `packages/matriz-client/src/matriz_client/client.py` |
| `wallets_client` | Internal wallets service (Bearer token, stub) | `packages/wallets-client/src/wallets_client/client.py` |
| `<pkg>.aio` | Async counterpart for ambito, higyrus, iol, wallets clients | `*/src/*/aio.py` |
| `matriz_client.ws_client` | WebSocket streaming (market data + execution reports) | `packages/matriz-client/src/matriz_client/ws_client.py` |
| `<pkg>.models` | Frozen safe-access dataclasses for API responses | `higyrus_client/models.py`, `matriz_client/models.py` |
| `<pkg>.exceptions` | Package-scoped exception hierarchy | `*/src/*/exceptions.py` |
| `<pkg>._params` / `<pkg>._parsing` | Internal serialization helpers | `higyrus_client/_params.py`, `ambito_financiero_client/_parsing.py` |

## Pattern Overview

**Overall:** Module-level singleton pattern — each package exposes a flat function API with state held in module-level globals (credentials, token, HTTP client instance).

**Key Characteristics:**
- No class instances required by the caller; import the package and call functions directly
- Dual sync/async surface: `import pkg` (sync) and `from pkg import aio` (async) with independent state
- Lazy authentication: the token is obtained on the first API call, cached, and refreshed before expiry; callers may call `login()` eagerly but it is not required
- No shared code between packages; each package is self-contained with its own copy of auth and HTTP logic
- `configure()` is the runtime override point for credentials and base URL in all packages

## Layers

**Public API Layer (`__init__.py`):**
- Purpose: Re-exports all public symbols from `client.py`, `aio.py`, `models.py`, `exceptions.py`, `types.py`; defines `__version__`
- Location: `packages/<name>/src/<pkg>/__init__.py`
- Contains: `__all__` list, version string, star-import re-exports
- Depends on: client, aio, models, exceptions, types modules within the same package
- Used by: callers — application code, notebooks, tests

**Sync Client Layer (`client.py`):**
- Purpose: Module-level state, auth flow, HTTP dispatch, domain function implementations
- Location: `packages/<name>/src/<pkg>/client.py`
- Contains: `_base_url`, `_token`, `_client` (httpx.Client) globals; `configure()`, `login()`, `_ensure_token()`, `_request()`, public domain functions
- Depends on: `httpx`, `python-dotenv`, exceptions module, models (where present), params/parsing helpers
- Used by: `__init__.py`, `aio.py` (for shared types like `InstrumentType` in iol)

**Async Client Layer (`aio.py`):**
- Purpose: Async mirror of `client.py` with independent module-level state and asyncio locks
- Location: `packages/<name>/src/<pkg>/aio.py` (present in ambito, higyrus, iol, wallets; absent in matriz)
- Contains: Same globals as sync but typed as `httpx.AsyncClient | None`; `asyncio.Lock()` for token and client; `aclose()` coroutine
- Depends on: same deps as `client.py`; imports shared types from `client.py` (e.g., `InstrumentType`)
- Used by: `__init__.py`

**Models Layer (`models.py`):**
- Purpose: Typed, frozen, safe-access dataclasses for deserializing API payloads
- Location: `packages/higyrus-client/src/higyrus_client/models.py`, `packages/matriz-client/src/matriz_client/models.py`
- Contains: `SafeModel` base class (higyrus); frozen `@dataclass` classes with `from_api(payload)` classmethods
- Depends on: `types.py` (matriz), stdlib dataclasses/typing
- Used by: `client.py`, `aio.py`, `__init__.py`

**Types Layer (`types.py`):**
- Purpose: `Literal` type aliases for enum-like API parameters
- Location: `packages/matriz-client/src/matriz_client/types.py`
- Contains: `Side`, `OrderType`, `TimeInForce`, `MarketId`, `SegmentId`, `CFICode`, etc.
- Depends on: stdlib `typing` only
- Used by: `models.py`, `client.py`, `ws_client.py`, `__init__.py`

**Internal Helpers Layer (`_*.py`):**
- Purpose: Private serialization utilities that should not be imported by callers
- Location: `packages/higyrus-client/src/higyrus_client/_params.py`, `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py`
- Contains: `format_date()`, `format_bool()`, `drop_none()` (higyrus); `parse_ar_decimal()` (ambito)
- Depends on: stdlib only
- Used by: `client.py` and `aio.py` within the same package

**Exceptions Layer (`exceptions.py`):**
- Purpose: Package-scoped exception hierarchy
- Location: `packages/<name>/src/<pkg>/exceptions.py`
- Contains: Base `<Pkg>ClientError(Exception)` → `<Pkg>APIError` → `<Pkg>AuthError`, `<Pkg>RateLimitError`
- Depends on: stdlib only
- Used by: `client.py`, `aio.py`, `__init__.py`

**WebSocket Layer (`ws_client.py`):**
- Purpose: Real-time streaming over WebSocket (market data + execution reports + WS order entry); uses background daemon thread
- Location: `packages/matriz-client/src/matriz_client/ws_client.py`
- Contains: `ws_connect()`, `ws_disconnect()`, `ws_subscribe_market_data()`, `ws_subscribe_order_reports()`, `ws_new_order()`, `ws_cancel_order()`
- Depends on: `websocket-client` library, `matriz_client.client` (for token), `matriz_client.models`
- Used by: `__init__.py`

## Data Flow

### Primary Request Path (sync)

1. Caller invokes domain function (e.g., `iol_client.get_quote("GGAL")`) via `packages/iol-client/src/iol_client/client.py`
2. `_ensure_token()` checks module-level `_token` and expiry timestamp; calls `login()` if needed (`client.py:111`)
3. `login()` POSTs credentials to auth endpoint, caches token in `_token` and expiry in `_token_expires_at` (`client.py:85`)
4. `_request()` constructs the authenticated HTTP request with Bearer/X-Auth-Token header and dispatches via the shared `httpx.Client` singleton (`client.py:117`)
5. On HTTP error, `_raise_for_response()` maps status codes to typed exceptions (`client.py:76`)
6. Response JSON is deserialized — either returned as raw `dict`/`list` (iol, ambito, wallets) or mapped through `Model.from_api()` (higyrus, matriz)
7. Caller receives typed result

### Primary Request Path (async)

1. Caller awaits domain function via `from <pkg> import aio`
2. `_ensure_token()` is async; uses `asyncio.Lock()` to prevent concurrent login races (`aio.py`)
3. `_ensure_http_client()` lazily creates `httpx.AsyncClient` with a separate `asyncio.Lock()` (`aio.py`)
4. All subsequent steps mirror the sync path but with `await` and the async client

### WebSocket Streaming Path (matriz only)

1. `ws_connect()` triggers `_rest.login()` if no cached token (`ws_client.py`)
2. Derives WebSocket URL from REST base URL (swaps `https` → `wss`)
3. Starts `websocket.WebSocketApp` in a background daemon thread
4. Inbound frames are dispatched to user-provided callbacks (`on_message`, `on_error`, `on_close`)
5. `ws_subscribe_market_data()` / `ws_subscribe_order_reports()` send JSON subscription frames over the open connection

**Token Refresh:**
- Each package defines its own `_TOKEN_TTL_*` constant (IOL: 900s with 60s buffer; Higyrus/Matriz: 23h)
- Sync clients: checked synchronously in `_ensure_token()` using `time.time()`
- Async clients: double-checked locking pattern inside `asyncio.Lock()` to prevent thundering herd

## Key Abstractions

**Module-Level Singleton State:**
- Purpose: Holds credentials, cached token, and a persistent HTTP client per package; eliminates the need for the caller to manage objects
- Examples: `_token`, `_base_url`, `_client` in every `client.py` and `aio.py`
- Pattern: `global` statement to mutate; `configure()` as the controlled mutation entry point

**`SafeModel` / `from_api()` pattern:**
- Purpose: Tolerant deserialization — absent or wrong-type fields fall back to typed zero-values instead of raising
- Examples: `packages/higyrus-client/src/higyrus_client/models.py:30`, `packages/matriz-client/src/matriz_client/models.py`
- Pattern: `@dataclass(frozen=True)` + `from_api(cls, payload: Any) -> Self` classmethod using `get_type_hints()` introspection

**`configure()` Runtime Override:**
- Purpose: Replaces env-var credentials and resets cached token without restarting the process; used heavily in tests via `monkeypatch`
- Examples: Every `client.py` and `aio.py` in the monorepo
- Pattern: keyword-only args, `global` mutation, sets `_token = None` to force re-auth

**Exception Hierarchy:**
- Purpose: Package-scoped typed errors; callers can catch at `<Pkg>ClientError` base or at specific subclass
- Examples: `packages/iol-client/src/iol_client/exceptions.py`
- Pattern: `ClientError(Exception)` → `APIError(ClientError)` → `AuthError(APIError)`, `RateLimitError(APIError)`

## Entry Points

**Smoke-test scripts (development only):**
- Location: `main_iol.py`, `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py`, `main_wallets.py` at repo root
- Triggers: `uv run --package <pkg> python main_<name>.py`
- Responsibilities: Import the package, call one or two functions, print results; not part of any package distribution

**Package import entry point:**
- Location: `packages/<name>/src/<pkg>/__init__.py`
- Triggers: `import <pkg>` or `from <pkg> import aio`
- Responsibilities: Execute `load_dotenv()` (via `client.py` import), populate module-level globals from env vars

## Architectural Constraints

- **Threading:** Sync clients are single-threaded; `httpx.Client` is not shared across threads. Async clients use `asyncio.Lock()` to serialize token refresh and client creation. The `ws_client.py` runs a daemon thread for the WebSocket event loop — the REST token is shared between the REST module and the WS module within `matriz_client`.
- **Global state:** Every `client.py` and `aio.py` holds module-level singletons (`_token`, `_client`, etc.). State is process-wide per package. Test fixtures must `configure()` and monkeypatch to isolate state.
- **Circular imports:** None detected. `aio.py` may import shared types from `client.py` (e.g., `iol_client.aio` imports `InstrumentType` from `iol_client.client`) but `client.py` never imports from `aio.py`.
- **No shared library:** There is no shared internal package in this monorepo by design. Auth logic, exception hierarchies, and HTTP boilerplate are intentionally duplicated across packages to keep each publishable package self-contained.
- **No async support in matriz:** `matriz_client` has no `aio.py`. Async use requires the WebSocket layer (`ws_client.py`) or calling REST functions from a thread executor.

## Anti-Patterns

### Importing `aio` module in sync context

**What happens:** Calling `await aio.some_function()` from synchronous code causes `RuntimeError: This event loop is already running` in Jupyter or `RuntimeError: no running event loop` in plain scripts.
**Why it's wrong:** `aio.py` modules require an event loop to exist and be running.
**Do this instead:** Use the sync `client.py` surface (`import pkg; pkg.some_function()`) from sync contexts, or ensure an event loop is running (e.g., `asyncio.run(main())`).

### Mutating module state without `configure()`

**What happens:** Directly assigning `pkg._token = "..."` or `pkg._base_url = "..."` outside of `configure()`.
**Why it's wrong:** `configure()` also resets `_token` and `_token_expires_at` atomically, ensuring the next request re-authenticates with the new credentials.
**Do this instead:** Always use `pkg.configure(base_url=..., username=..., password=...)` — as demonstrated in `conftest.py` (`packages/iol-client/tests/conftest.py`).

### Using the same `aio` state across multiple event loops

**What happens:** Calling `aio.configure(...)` in one test and then reusing the cached `_client` (an `httpx.AsyncClient`) in a different event loop.
**Why it's wrong:** `httpx.AsyncClient` is bound to the event loop it was created in; reuse across loops raises.
**Do this instead:** Call `await aio.aclose()` in test teardown to destroy the client, then `configure()` will create a fresh one on the next request. Fixture in `packages/iol-client/tests/conftest.py` shows the correct pattern.

## Error Handling

**Strategy:** Fail-fast with typed exceptions mapped from HTTP status codes; no silent swallowing.

**Patterns:**
- `_raise_for_response(resp)` is called after every HTTP response; maps 401/403 → `AuthError`, 429 → `RateLimitError`, any other error status → `APIError`
- `matriz_client` additionally checks the JSON payload for `"status": "ERROR"` (application-level errors from Primary API) and raises `PrimaryAPIError`
- `higyrus_client` parses the `"errors"` key from the JSON body and passes structured error details into the exception constructor
- Missing/malformed auth credentials raise the respective `AuthError` before any HTTP call is made
- `SafeModel.from_api()` never raises on missing fields — it substitutes safe defaults

## Cross-Cutting Concerns

**Logging:** Not implemented. No logging calls in any package. Diagnostic output is through exceptions only.
**Validation:** Input validation is minimal — credentials are checked for empty string before auth requests. Parameter types are enforced by mypy at development time (strict mode).
**Authentication:** Each package implements its own auth strategy: OAuth 2.0 password grant (IOL), Bearer via JSON login (Higyrus), proprietary X-Auth-Token header (Matriz/Primary), static Bearer token (Wallets), no auth (Ámbito Financiero).

---

*Architecture analysis: 2026-05-27*
