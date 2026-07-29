# Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte - Research

**Researched:** 2026-07-29
**Domain:** Python HTTP client library scaffolding (httpx sync+async) mirroring an existing template; OAuth2 Auth0 `client_credentials` token lifecycle; transport retry/logging/exception foundations
**Confidence:** HIGH (the phase is a structured mirror of a fully-read in-repo template; the one external unknown — the Auth0 grant wire shape — is confirmed against official docs)

## Summary

Phase 20 stands up a new package `market-data-client` (import `market_data_client`, dist `market-data-client`) by **mirroring the `iol-client` layout module-for-module**, then applying a small, well-bounded set of deltas driven by two facts: (1) auth is Auth0 `client_credentials` — a **single-grant** flow with **no refresh token**, so roughly half of iol's auth machinery is deleted rather than copied; and (2) there are **anonymous health endpoints** (`GET /health`, `GET /health/feed`) — a request path that iol does not have, added via an `authenticated: bool = True` flag on the internal request spec.

The template was read in full. Every iol module has a concrete analog for market-data, and the transport (`_transport.py` / `_atransport.py`) and the redaction/logging scaffold (`_logging.py`) are copied verbatim except for a logger-name change and a change of credential patterns. The most error-prone areas are: the token endpoint is an **absolute Auth0 URL** (`MARKET_DATA_AUTH0_TOKEN_URL`), NOT `base_url + path` as in iol; the parser returns a **2-tuple** `(token, expires_at)` (no refresh slot); and the anonymous request path must be mirrored identically in `client.py` and `aio.py`.

**Primary recommendation:** Copy iol's `_transport.py`, `_atransport.py`, and the `RedactingFilter`/`attach()` scaffold of `_logging.py` verbatim (logger name + credential patterns are the only edits). Reduce `_core.py` to one auth builder + one parser + `raise_for_response` + `token_is_fresh` + health builders/parsers. Collapse iol's `login`/`_refresh`/`_ensure_token` trio into a single `_authenticate()` + `_ensure_token()` pair. Add `authenticated: bool` to `RequestSpec` and branch on it in the single `_request` code path (sync and async). Delete `_token_cache.py`, `platformdirs`, `refresh_token`, `with_options`, `models.py`, `types.py` entirely for this phase.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Module Decomposition & File Set**
- **D-01:** Mirror iol's private-module layout: `_core.py` (pure Auth0 builders/parsers + `raise_for_response` + token-freshness check), `_state.py` (`_ClientState` non-frozen dataclass, `slots=True`), `_transport.py` / `_atransport.py`, `_logging.py`, `client.py` (sync), `aio.py` (async), `exceptions.py`, `__init__.py` (`__all__` + `__version__="0.1.0"`), `py.typed`. Plus `.env.example`, `README.md`, `tests/`.
- **D-02:** **OMIT `_token_cache.py`** — disk token cache deferred to v1.5+; do NOT add `platformdirs`. Package runtime deps: `httpx>=0.27`, `python-dotenv>=1.0`, `tenacity>=9.1,<10` (build: hatchling).
- **D-03:** **Do NOT add `models.py` nor `types.py`** this phase — response models (`SafeModel` with `received_at`) are scheduled for Phases 21/22.
- **D-04:** The Auth0 token builder/parser lives in `_core.py`, next to `raise_for_response` (same home iol uses for its auth builders/parsers).

**Auth0 client_credentials Token Lifecycle**
- **D-05:** Single `client_credentials` grant: in `_core.py`, ONE builder (`build_token_request`, `grant_type=client_credentials`, form-encoded with `client_id` + `client_secret` + `audience`, POST to `MARKET_DATA_AUTH0_TOKEN_URL`) and ONE parser (`parse_token_response` → `(token, expires_at)`). **No** `build_refresh_request`, **no** `refresh_token` state field, **no** conditional rotation logic (iol's CR-01). Re-running the same grant IS the refresh.
- **D-06:** `_ensure_token()` re-runs the `client_credentials` grant when the cached token is stale. TTL derived from the response: `expires_at = time.time() + expires_in - buffer` with `buffer ≈ 60s` (constant `_TOKEN_TTL_BUFFER_SECONDS`, mirroring iol `_state.py`).
- **D-07:** **Fallback when `expires_in` is absent = ~1 hour (3600s).** Conservative midpoint (not iol's 900s, which would trigger needless hourly re-auth on ~24h Auth0 tokens; not a loud failure either). Applies ONLY to the absent-field case; the normal case always derives from `expires_in`.

**Health Endpoints (anonymous path)**
- **D-08:** `GET /health` and `GET /health/feed` require an **unauthenticated request path**: no `Authorization` header and **without** triggering `_ensure_token()`.
- **D-09:** Implement via an **`authenticated: bool = True` flag on the internal request spec** — health passes `authenticated=False` to skip token injection. A single code path (NOT a separate `_request_anonymous` helper), mirrored sync/async.

**Transport, Retry, Logging & Concurrency**
- **D-10:** Mirror iol's `_transport.py` / `_atransport.py` **verbatim**: retryable set (`408/409/429/5xx` + `ConnectError`/`ConnectTimeout`/`ReadTimeout`), `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)`, `Retry-After` cap at 60s, idempotent mutation-gate. Only change: `_LOGGER_NAME = "market_data_client"`.
- **D-11:** `_logging.py` reuses iol's `RedactingFilter` / `attach()` structure but **changes credential patterns**: redact `Bearer` / `access_token` (JSON) **plus `client_secret`** (form-encoded token body + JSON). Zero credential leakage in logs is a CORE-MD-01 gate.
- **D-12:** Concurrency via iol's per-loop **`asyncio.Lock` double-checked** pattern (`aio.py`) — **NOT** matriz's `TokenStore` (scoped to 3-way concurrency with the WebSocket daemon thread, deferred here). **No** `RefreshPolicy` fail-cache decorator this phase.

**Env Vars & Exceptions**
- **D-13:** `.env.example` with: `MARKET_DATA_CLIENT_ID`, `MARKET_DATA_CLIENT_SECRET`, `MARKET_DATA_AUDIENCE`, `MARKET_DATA_AUTH0_TOKEN_URL`, `MARKET_DATA_BASE_URL` (default `https://market-data-develop.bbsa.com.ar/api`).
- **D-14:** Exception hierarchy: `MarketDataError → MarketDataAPIError → MarketDataAuthError`, `MarketDataRateLimitError`. Mapping in `raise_for_response`: 401/403→Auth, 429→RateLimit, other errors→APIError.

### Claude's Discretion
- Exact names of internal constants/functions within the iol pattern (as long as they respect the monorepo naming conventions).
- Concrete test strategy within what the success criteria require: mock of the Auth0 token endpoint (pytest-httpx), TTL-expiry refresh test in sync + async, redaction test with `caplog`, health smoke.

### Deferred Ideas (OUT OF SCOPE)
- `_token_cache.py` (disk token cache + `platformdirs`) and JWT signature validation → v1.5+.
- `models.py` / `types.py` with response `SafeModel` → Phases 21/22.
- `with_options(max_retries=N)` (shared-view clone, Phase 13 pattern) → Phase 21.
- `refresh_token` machine / conditional rotation (CR-01) → N/A for client_credentials (does not apply).
- Market data / instruments / symbols / calendar endpoints → Phases 21-22.
- SSE streaming `GET /marketdata/stream`, mutations (symbols/calendar) → v1.5+.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-MD-01 | Package authenticates against Auth0 via `client_credentials` grant (`client_id` + `client_secret` + `audience`), caches the access token, and auto-refreshes when TTL expires (derived from `expires_in`), in both sync and async surfaces | Auth0 grant wire shape confirmed (Standard Stack + Code Examples §Auth0 token exchange); TTL/buffer/fallback logic mapped to iol `_state.py:59` + `_core.py:194`; dual sync/async lifecycle mapped to `client.py::_ensure_token` and `aio.py::_aensure_token` double-checked lock (Mirror Map rows `_state.py`, `_core.py`, `client.py`, `aio.py`) |
| CORE-MD-01 | Package provides shared foundations — full-jitter retry transport (mutation-gate-safe), structured logging with credential redaction, typed exception hierarchy, `configure()` runtime override, health endpoints (`GET /health`, `GET /health/feed`) | `_transport.py`/`_atransport.py` verbatim-copy analysis (D-10, Code Examples §retry transport); `_logging.py` redaction pattern deltas (D-11); exception hierarchy mapping (D-14, Mirror Map `exceptions.py`); anonymous health path design (Architecture Pattern 3) |
</phase_requirements>

## Architectural Responsibility Map

This is a single-tier client library; "tier" here means the owning module within the package. Mapping capabilities to their module owner prevents mis-placing logic (e.g. putting auth dispatch in `_core.py`, which must stay pure/IO-free).

| Capability | Primary Owner | Secondary Owner | Rationale |
|------------|---------------|-----------------|-----------|
| Auth0 request/response shaping (pure) | `_core.py` | — | Pure builder/parser; NO I/O dispatch (iol contract: `_core.py:8-13`) |
| Token dispatch + cache + TTL check | `client.py` / `aio.py` | `_core.py` (`token_is_fresh`) | Transport shell owns `httpx` send + state mutation; freshness check is pure in `_core` |
| Per-instance state (creds, token, expiry, locks) | `_state.py` | — | `_ClientState` dataclass; env-var default factories |
| Retry / backoff / Retry-After | `_transport.py` / `_atransport.py` | — | `httpx.HTTPTransport` subclass; mutation-gate on `request.extensions["idempotent"]` |
| Credential redaction in logs | `_logging.py` | — | `logging.Filter` attached to package logger only, never root |
| HTTP-status → typed exception | `_core.raise_for_response` | `exceptions.py` | Mapping lives in `_core`, alias'd module-level in `client.py`/`aio.py` for B8 identity |
| Anonymous health request path | `client.py` / `aio.py` | `_core.py` (health builders) | Same `_request` code path branched on `spec.authenticated` (D-09) |
| Runtime credential/URL override | `client.py::configure` / `aio.py::configure` | `_state.py` | Sole controlled mutation entry; resets cached token |

## Standard Stack

### Core
| Library | Version (locked) | Purpose | Why Standard |
|---------|------------------|---------|--------------|
| `httpx` | 0.28.1 (`>=0.27`) | Sync (`httpx.Client`) + async (`httpx.AsyncClient`) HTTP transport | Sole HTTP transport across all 5 packages; custom transport subclassing is the retry seam |
| `python-dotenv` | 1.x (`>=1.0`) | `load_dotenv()` at module import to populate `MARKET_DATA_*` env vars | Every client module in the monorepo loads `.env` this way |
| `tenacity` | 9.1.4 (`>=9.1,<10`) | `Retrying`/`AsyncRetrying` + `wait_exponential_jitter` inside the retry transport | Already the retry engine for iol/ámbito `_transport.py` |

### Supporting (test-only)
| Library | Version (locked) | Purpose | When to Use |
|---------|------------------|---------|-------------|
| `pytest` | 8.x (`>=8.3`) | Test runner | All tests |
| `pytest-asyncio` | (`>=0.24`, `asyncio_mode="auto"`) | Async test support | `aio.py` tests |
| `pytest-httpx` | 0.36.2 (`>=0.34`) | Mock httpx requests (`HTTPXMock`, `match_content`, `match_url`) | Token endpoint + health mocks |
| `pytest-cov` | (`>=6.0`) | Coverage | Optional |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `RetryTransport` (tenacity) | httpx built-in `transport=HTTPTransport(retries=N)` | httpx's built-in retries only cover connection errors, not retryable status codes (429/5xx) or `Retry-After` — insufficient for D-10. Keep the tenacity transport. |
| `authlib` / `requests-oauthlib` for Auth0 | hand-rolled form POST | Project constraint: no shared/extra deps; the grant is a single form POST — a library is overkill and adds a dep. Mirror iol's manual `_core` builder. |

**Installation** (per-package `pyproject.toml`; already present in monorepo `uv.lock`):
```bash
# Runtime deps declared in packages/market-data-client/pyproject.toml:
#   httpx>=0.27, python-dotenv>=1.0, tenacity>=9.1.0,<10
# Then, from repo root:
uv sync --all-packages --all-extras --dev --frozen
```

**Version verification:** All three runtime deps and all test deps are already pinned in the repo `uv.lock` and consumed by the 5 existing packages. `tenacity 9.1.4` satisfies `>=9.1,<10`; `httpx 0.28.1` satisfies `>=0.27`. No new/unknown packages are introduced this phase.

## Package Legitimacy Audit

> No new external packages are introduced. Every dependency is already present in the monorepo `uv.lock` and used by the 5 existing packages — legitimacy is established by in-repo usage (a stronger signal than registry lookup).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| httpx | PyPI | mature | very high | github.com/encode/httpx | OK | Approved (already in lockfile) |
| python-dotenv | PyPI | mature | very high | github.com/theskumar/python-dotenv | OK | Approved (already in lockfile) |
| tenacity | PyPI | mature | very high | github.com/jd/tenacity | OK | Approved (already in lockfile) |
| pytest-httpx | PyPI | mature | high | github.com/Colin-b/pytest_httpx | OK | Approved (test-only, in lockfile) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
**Deliberately SUBTRACTED from the iol template:** `platformdirs` (iol `pyproject.toml:25`) — deferred with `_token_cache.py` to v1.5+ (D-02).

## Architecture Patterns

### System Architecture Diagram

```text
Caller
  │  import market_data_client                        from market_data_client import aio
  │  market_data_client.get_health()                  await aio.get_health()
  ▼                                                    ▼
┌──────────────────────────┐                ┌──────────────────────────┐
│ client.py (sync shell)   │                │ aio.py (async shell)     │
│  Client / module shims   │                │  AsyncClient / shims     │
│  configure()             │                │  configure()             │
│  _ensure_token() ────────┼──┐          ┌──┼─ _aensure_token()        │
│  _request(spec)          │  │          │  │  (asyncio.Lock double-   │
└─────────┬────────────────┘  │          │  │   checked, per-loop)     │
          │                    │          │  └─────────┬────────────────┘
          │ spec.authenticated │          │            │
          │  True → inject      │  token   │  token     │
          │  Bearer + ensure    ▼  fetch   ▼  fetch     │
          │  False → skip   ┌────────────────────────┐  │
          │                 │ _core.py (PURE)        │  │
          │                 │  build_token_request   │  │  ← POST form-encoded to
          │                 │  parse_token_response  │  │    MARKET_DATA_AUTH0_TOKEN_URL
          │                 │  build_health_request  │  │    (ABSOLUTE Auth0 URL)
          │                 │  raise_for_response     │  │
          │                 │  token_is_fresh         │  │
          │                 └────────────────────────┘  │
          ▼                                              ▼
┌──────────────────────────────────────────────────────────┐
│ _transport.py / _atransport.py  (RetryTransport)          │
│  mutation-gate → full-jitter backoff → Retry-After cap    │
│  emits structured WARNING/ERROR ─────────────┐            │
└──────────────────┬───────────────────────────┼───────────┘
                   │ httpx over network         ▼
                   ▼                    ┌────────────────────┐
        MARKET_DATA_BASE_URL            │ _logging.py        │
        (/health, /health/feed)        │ RedactingFilter    │
        + Auth0 token URL              │ scrubs Bearer /     │
                                        │ access_token /      │
                                        │ client_secret       │
                                        └────────────────────┘
State: _state.py::_ClientState (base_url, client_id, client_secret, audience,
       auth0_token_url, token, token_expires_at, http_client, token_lock, client_lock)
```

### Recommended Project Structure
```
packages/market-data-client/
├── pyproject.toml            # hatchling, deps (httpx, python-dotenv, tenacity), py.typed
├── README.md                 # usage, env vars, Auth0 client_credentials note
├── .env.example              # MARKET_DATA_* vars (D-13)
├── src/market_data_client/
│   ├── __init__.py           # attach() logging FIRST, then re-exports; __all__ + __version__="0.1.0"
│   ├── py.typed              # empty marker (PEP 561)
│   ├── _core.py              # PURE: RequestSpec, build_token_request, parse_token_response,
│   │                         #       build_health_request(+feed), parse_health_response,
│   │                         #       raise_for_response, token_is_fresh
│   ├── _state.py             # _ClientState (slots=True, non-frozen) + constants
│   ├── _transport.py         # RetryTransport (verbatim from iol; logger name only)
│   ├── _atransport.py        # AsyncRetryTransport (verbatim; imports from _transport)
│   ├── _logging.py           # RedactingFilter + attach() (patterns changed per D-11)
│   ├── client.py             # sync Client + module-level shims + configure()
│   └── aio.py                # async AsyncClient + module-level shims + configure()
└── tests/
    ├── conftest.py           # autouse configure() sync+async fixtures; close transport on teardown
    ├── test_core.py          # pure builder/parser + raise_for_response mapping
    ├── test_client.py        # sync dispatch, health, 401 mapping
    ├── test_async_client.py  # async dispatch, health
    ├── test_token_lifecycle.py        # sync: fetch → cache → TTL-expiry refetch
    ├── test_token_lifecycle_async.py  # async mirror (double-checked lock)
    ├── test_logging.py       # RedactingFilter unit (Bearer/access_token/client_secret)
    └── test_transport.py     # retry semantics (optional — can copy iol's)
```

### Pattern 1: Pure builder/parser + transport shell (iol D-01/D-02/D-03)
**What:** `_core.py` functions are PURE — state in → `RequestSpec` (builders), or `httpx.Response` in → typed result (parsers). NO `httpx.send`/`await`. All I/O dispatch lives in `client.py`/`aio.py`.
**When to use:** Every endpoint and the auth flow.
**Example:** (mirror of iol `_core.py:112-195` and `client.py:359-380`, reduced to a single grant)
```python
# _core.py — Source: mirror of packages/iol-client/src/iol_client/_core.py:142-195
def build_token_request(state: _ClientState) -> RequestSpec:
    if not state.client_id or not state.client_secret or not state.audience:
        raise MarketDataAuthError(0, "MARKET_DATA_CLIENT_ID/SECRET/AUDIENCE requeridos")
    return RequestSpec(
        method="POST",
        path="",  # dispatched to the ABSOLUTE state.auth0_token_url (see Pitfall 1)
        data={
            "grant_type": "client_credentials",
            "client_id": state.client_id,
            "client_secret": state.client_secret,
            "audience": state.audience,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        idempotent=True,          # replay-safe grant → 5xx retry-eable
        endpoint_name="token",
        authenticated=False,      # NEW field (D-09): the token request has no Bearer
    )

def parse_token_response(resp: httpx.Response) -> tuple[str, float]:
    resp.read()                    # body-consume-then-raise (iol D-06)
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise MarketDataAuthError(resp.status_code, "No access_token in response")
    expires_in = data.get("expires_in", _TOKEN_TTL_FALLBACK_SECONDS)  # D-07: 3600 fallback
    expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token, expires_at   # 2-tuple — NO refresh slot (D-05)
```

### Pattern 2: Collapsed token lifecycle (single grant, D-05/D-06)
**What:** Replace iol's `login()` + `_refresh()` + `_ensure_token()` trio with `_authenticate()` (runs the grant, writes state) + `_ensure_token()` (freshness check → `_authenticate()`).
**When to use:** Once, in each of `client.py` and `aio.py`.
**Example:**
```python
# client.py — Source: reduction of packages/iol-client/src/iol_client/client.py:405-427
def _authenticate(self) -> str:
    spec = _core.build_token_request(self._state)
    resp = self._send_auth_request(spec)              # dispatches to auth0_token_url
    token, expires_at = _core.parse_token_response(resp)
    self._state.token = token
    self._state.token_expires_at = expires_at
    return token

def _ensure_token(self) -> None:
    if _core.token_is_fresh(self._state):
        return
    self._authenticate()          # re-running the grant IS the refresh (D-05)
```
```python
# aio.py — Source: reduction of packages/iol-client/src/iol_client/aio.py:401-432
async def _aensure_token(self) -> None:
    if _core.token_is_fresh(self._state):
        return
    lock = self._ensure_token_lock()          # lazy, per-loop (Pitfall 2)
    async with lock:
        if _core.token_is_fresh(self._state):  # double-check inside lock (D-12)
            return
        await self._authenticate_unlocked()
```

### Pattern 3: Anonymous request path via `authenticated` flag (D-08/D-09) — NET-NEW vs iol
**What:** Add `authenticated: bool = True` to `RequestSpec`. In the single `_request` code path, gate `_ensure_token()` + the `Authorization` header on `spec.authenticated`. Health builders set `authenticated=False`.
**When to use:** `GET /health`, `GET /health/feed`.
**Example:**
```python
# client.py::_request — Source: adaptation of iol client.py:429-491
def _request(self, spec: RequestSpec) -> httpx.Response:
    headers = dict(spec.headers or {})
    if spec.authenticated:
        self._ensure_token()
        assert self._state.token is not None
        headers["Authorization"] = f"Bearer {self._state.token}"
    http = self._ensure_http_client()
    req = http.build_request(spec.method, f"{self._state.base_url}{spec.path}",
                             params=spec.params, json=spec.json_body, headers=headers)
    req.extensions["idempotent"] = spec.idempotent
    req.extensions["endpoint_name"] = spec.endpoint_name
    req.extensions["request_id"] = uuid.uuid4().hex
    resp = http.send(req)
    try:
        _raise_for_response(resp)
    except MarketDataAuthError:
        if not spec.authenticated:
            raise                      # health 401 is a real error, no re-auth
        resp.read()
        self._state.token = None       # exactly-one re-auth (Pitfall 4)
        self._ensure_token()
        req.headers["Authorization"] = f"Bearer {self._state.token}"
        resp = http.send(req); resp.read(); _raise_for_response(resp)
    return resp
```
> Health builders live in `_core.py`:
> ```python
> def build_health_request(state) -> RequestSpec:
>     del state
>     return RequestSpec(method="GET", path="/health", idempotent=True,
>                        endpoint_name="health", authenticated=False)
> # + build_health_feed_request → path="/health/feed"
> ```

### Anti-Patterns to Avoid
- **Copying `_token_cache.py`, `refresh_token`, `with_options`, `platformdirs`, or the PEP 562 legacy shim** from iol. iol carries Phase 13/14 machinery (disk cache, refresh rotation, shared-view clones, legacy back-compat) that this greenfield package must NOT inherit (D-02, deferred list). Start clean.
- **Dispatching the token request to `base_url + path`.** The Auth0 token endpoint is a **separate absolute URL** (`MARKET_DATA_AUTH0_TOKEN_URL`), unlike iol's `/token` under `base_url`. See Pitfall 1.
- **Creating `asyncio.Lock()` in `__init__`.** Must be lazy (bound to the running loop on first async use) — see Pitfall 2.
- **A separate `_request_anonymous` helper.** D-09 mandates a single branched code path.
- **Calling `logging.basicConfig` or touching `logging.root`** in package src — CI has a grep gate (`.github/workflows/ci.yml:42-48`) that fails the build. `attach()` touches only `getLogger("market_data_client")`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff + Retry-After | A custom loop | Copy iol `_transport.py`/`_atransport.py` verbatim (tenacity) | Full-jitter, mutation-gate, RFC 9110 Retry-After (delta + HTTP-date), cap logic already correct and tested |
| Credential redaction | New regex from scratch | Copy iol `RedactingFilter`/`attach()`, change only the pattern set | Idempotent attach, `record.__dict__`/`args`/`msg` scan, NullHandler convention already correct |
| OAuth2 form POST | `authlib` / manual URL-encoding | httpx `data={...}` (form-encodes automatically) | httpx handles `application/x-www-form-urlencoded` serialization |
| Token endpoint mocking | Live Auth0 in tests | `pytest-httpx` `HTTPXMock` + `match_content` | Deterministic; the exact mock recipe is in Code Examples |
| Exception hierarchy | ad-hoc exceptions | Mirror iol `exceptions.py` renamed | 4-class hierarchy + `status_code`/`message` attrs proven |

**Key insight:** ~70% of this phase is verbatim/near-verbatim copy of a package that already passes all 4 CI gates. Hand-rolling any of the copied pieces re-introduces bugs the iol package already fixed across Phases 6-14.

## Mirror Map: iol source → market-data analog

| iol file | Copy verbatim? | Concrete deltas for market-data |
|----------|----------------|----------------------------------|
| `_core.py` (361 lines) | NO — heavy reduction | KEEP: `RequestSpec` (add `authenticated: bool = True` field), `raise_for_response` (rename exceptions), `token_is_fresh`. REPLACE auth: ONE `build_token_request` (client_credentials, absolute token URL) + ONE `parse_token_response`→2-tuple. REMOVE: `build_login_request`, `parse_login_response`, `build_refresh_request`, `parse_refresh_response`, all 4 endpoint builders/parsers (Phase 21+). ADD: `build_health_request`, `build_health_feed_request`, `parse_health_response`. Drop the CR-01 docstring. |
| `_state.py` (104 lines) | NO — reduce | KEEP: `DEFAULT_BASE_URL` (→`https://market-data-develop.bbsa.com.ar/api`), `_REQUEST_TIMEOUT=30.0`, `_TOKEN_TTL_BUFFER_SECONDS=60`, `_ClientState(slots=True)` with `token`, `token_expires_at`, `http_client`, `token_lock`, `client_lock` (lazy). ADD: `client_id`, `client_secret`, `audience`, `auth0_token_url` (env factories for `MARKET_DATA_*`); constant `_TOKEN_TTL_FALLBACK_SECONDS=3600` (D-07). REMOVE: `username`, `password`, `refresh_token`, `token_cache_path`, `pathlib` import. |
| `_transport.py` (202 lines) | **YES — verbatim** | Only `_LOGGER_NAME = "market_data_client"`; rename the internal sentinel doc refs. Constants stay: `_RETRYABLE_STATUS=frozenset({408,409,429,*range(500,600)})` (`:59`), `_RETRY_AFTER_CAP_S=60.0` (`:60`), `_RETRYABLE_EXC=(ConnectError,ConnectTimeout,ReadTimeout)` (`:54-58`), `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)` (`:142`). |
| `_atransport.py` (134 lines) | **YES — verbatim** | Imports `_LOGGER_NAME` etc. from `_transport` (intra-package coupling is allowed — `:31-38`). No edits beyond the import path. |
| `_logging.py` (112 lines) | NO — change patterns (D-11) | KEEP structure: `RedactingFilter` (msg/args/`__dict__` scan), `attach()` (idempotent, NullHandler + filter on `getLogger("market_data_client")` only). CHANGE patterns: KEEP `_BEARER_RE`, `_ACCESS_TOKEN_JSON_RE`. REMOVE `_PASSWORD_*`, `_REFRESH_TOKEN_*`, `_X_AUTH_TOKEN_RE`. ADD `_CLIENT_SECRET_URLENC_RE = re.compile(r"(client_secret=)[^&\s]+")` and `_CLIENT_SECRET_JSON_RE = re.compile(r'("client_secret"\s*:\s*")[^"]+(")')`. Update `_REDACTION_MARKERS` to `("Bearer ", "client_secret=", '"client_secret"', '"access_token"')`. |
| `client.py` (757 lines) | NO — heavy reduction | KEEP: `Client` class shell, `_ensure_http_client` (RetryTransport), `_send_auth_request` (→ **dispatch to `state.auth0_token_url`**, not `base_url+path`), `_request` (add `authenticated` branch), `configure()`, module-level `_get_default()` + shims. COLLAPSE auth to `_authenticate()`+`_ensure_token()`. REMOVE: `_validate_max_retries`, `with_options`, `_is_view`/view logic, `__reduce__`/`__deepcopy__` (optional keep), `_token_cache`, `refresh_token`, PEP 562 `__getattr__` shim + `_FORWARDED_*`/`_DENIED_LEGACY`, all endpoint methods. ADD: `get_health()`, `get_health_feed()`. |
| `aio.py` (~760 lines) | NO — heavy reduction | Mirror of `client.py` deltas. KEEP: double-checked `_ensure_http_client` (`:213-240`), lazy `_ensure_token_lock`/`_ensure_client_lock` (`:242-256`), `_aensure_token` (`:401-432`, reduced to single grant), `_request` (`:434-512`, add `authenticated` branch). Split auth into `_authenticate_unlocked()` (caller holds lock). REMOVE same items as client.py. ADD async `get_health()`/`get_health_feed()`. |
| `exceptions.py` (25 lines) | NO — rename | `MarketDataError(Exception)` → `MarketDataAPIError(MarketDataError)` with `(status_code, message)` → `MarketDataAuthError(MarketDataAPIError)`, `MarketDataRateLimitError(MarketDataAPIError)`. Same structure as iol `:6-24`. |
| `__init__.py` (74 lines) | NO — reduce | KEEP the critical ordering: `from market_data_client import _logging as _la; _la.attach(); del _la` BEFORE other imports (iol `:27-30`). Re-export `Client`, `AsyncClient`, the 4 exceptions, `configure`, `get_health`, `get_health_feed`. `__all__` list. `__version__ = "0.1.0"`. REMOVE `InstrumentType`, endpoint shims, `_get_default` re-export (optional keep for tests). |
| `pyproject.toml` (45 lines) | NO — adapt | `name="market-data-client"`, `version="0.1.0"`, deps `httpx>=0.27`, `python-dotenv>=1.0`, `tenacity>=9.1.0,<10` (**SUBTRACT `platformdirs`**), `[tool.hatch.build.targets.wheel] packages=["src/market_data_client"]`, test extras same as iol `:28-34`. Update description/keywords. |
| `conftest.py` (60 lines) | NO — adapt | autouse sync + async fixtures calling `configure(base_url=..., client_id="cid", client_secret="csec", audience="aud", auth0_token_url="https://auth.test/oauth/token", token="test-token", token_expires_at=NEVER_EXPIRES)`; close/aclose transport on teardown (iol `:32-59`). Keep `NEVER_EXPIRES = 9_999_999_999.0`. |
| `test_refresh_token_lifecycle.py` | NO — replace | Simplify to a token fetch → cache → TTL-expiry refetch test (no refresh_token 4-path matrix). Use `match_content` to assert the client_credentials form body. Async mirror likewise. |
| `test_logging.py` (144 lines) | NO — adapt | Keep the `_make_record` helper + attach-idempotency + Bearer + access_token tests. Replace password/refresh_token tests with `client_secret` (urlenc + JSON) tests. |
| `_token_cache.py` | **OMIT entirely** | Deferred v1.5+ (D-02). |
| `models.py` / `types.py` | **DO NOT CREATE** | Phases 21/22 (D-03). |

## Common Pitfalls

### Pitfall 1: Token endpoint is an absolute Auth0 URL, not `base_url + path`
**What goes wrong:** Copying iol's `_send_auth_request` (`client.py:344-349`) verbatim dispatches the grant to `f"{self._state.base_url}{spec.path}"` = `https://market-data-develop.bbsa.com.ar/api/token`, which is NOT the Auth0 token endpoint.
**Why it happens:** iol's `/token` lives under its own `base_url`; Auth0's token endpoint is a wholly separate host (`MARKET_DATA_AUTH0_TOKEN_URL`, e.g. `https://<tenant>.auth0.com/oauth/token`).
**How to avoid:** In `_send_auth_request`, dispatch to `self._state.auth0_token_url` directly (the token `RequestSpec.path` is unused / empty). Keep `MARKET_DATA_BASE_URL` for `/health*` and all Phase 21+ endpoints.
**Warning signs:** 404 on the token request in the live smoke; the mock passing but live auth failing.

### Pitfall 2: `asyncio.Lock` bound to the wrong event loop
**What goes wrong:** Creating `asyncio.Lock()` in `AsyncClient.__init__` binds it to whatever loop is alive at construction; a later `asyncio.run(...)` uses a different loop → `RuntimeError` or a lock that guards nothing.
**Why it happens:** Module-level singleton + `asyncio.run` per call is the common test/usage shape.
**How to avoid:** Mirror iol exactly — lazy `_ensure_token_lock()`/`_ensure_client_lock()` create the lock on first async use and store it on `_state` (iol `aio.py:242-256`).
**Warning signs:** Async tests pass individually but fail in-suite with "got Future attached to a different loop."

### Pitfall 3: Two mocks on the same token URL collide (FIFO)
**What goes wrong:** A TTL-refresh test registers two responses for the same token URL; without `match_content`/`match_url` discrimination pytest-httpx serves them FIFO and assertions on "which grant fired" become order-dependent.
**Why it happens:** Both the initial fetch and the refetch hit the same `auth0_token_url` with the same body.
**How to avoid:** Use `httpx_mock.add_response(..., is_reusable=True)` for a stable grant, or register distinct responses and assert `len(httpx_mock.get_requests())`. See iol `test_refresh_token_lifecycle.py:54-63` for the `match_content` idiom. For client_credentials the body is identical across fetch+refetch, so assert on request COUNT (expiry drives the second call), not on ordering.
**Warning signs:** Test flakiness when reordered; wrong assertion on token value.

### Pitfall 4: Health 401 must NOT trigger re-auth; authenticated 401 must re-auth exactly once
**What goes wrong:** A 401 on `/health` (anonymous) that falls into the re-auth branch would attempt a token grant it should never need; conversely, an authenticated 401 that doesn't re-auth loses the auto-recovery guarantee.
**Why it happens:** The `authenticated` flag must gate BOTH the initial token injection AND the 401 re-auth carve-out.
**How to avoid:** In `_request`'s `except MarketDataAuthError` block, `if not spec.authenticated: raise` before any re-auth; otherwise clear token, `_ensure_token()`, retry exactly once (no recursion — a second 401 re-raises). Mirror both in `client.py` and `aio.py`.
**Warning signs:** Infinite loop on persistent 401; health smoke making spurious token calls.

### Pitfall 5: TTL fallback semantics (D-07)
**What goes wrong:** Applying the 3600s fallback unconditionally (even when `expires_in` is present) truncates real ~24h Auth0 tokens to 1h; or using iol's 900s default causes hourly re-auth.
**Why it happens:** Copy-paste of iol `parse_login_response` which hard-codes `data.get("expires_in", 900)`.
**How to avoid:** `expires_in = data.get("expires_in", _TOKEN_TTL_FALLBACK_SECONDS)` where the constant is `3600`; the present-field case always wins. Buffer (`-60s`) applies in both cases.
**Warning signs:** Token re-fetched far more often than `expires_in` implies.

### Pitfall 6: Cross-test state contamination via module-level singleton
**What goes wrong:** The module-level `_default_client` caches a token across tests; a test that mutates `token_expires_at` leaks into the next.
**Why it happens:** Process-wide singleton per surface (project constraint).
**How to avoid:** autouse `conftest.py` fixtures `configure(...)` at setup and close the transport + reset creds at teardown (iol `conftest.py:32-59`). Each lifecycle test sets `state.token`/`token_expires_at` explicitly at the top.
**Warning signs:** Tests green in isolation, red in suite.

## Code Examples

### Auth0 client_credentials token exchange (wire shape)
```text
# Source: Auth0 official docs — Client Credentials Flow  [CITED: auth0.com/docs get-started/.../client-credentials-flow]
POST https://<tenant>.auth0.com/oauth/token           # == MARKET_DATA_AUTH0_TOKEN_URL
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=<id>&client_secret=<secret>&audience=<api-identifier>

# 200 response:
{ "access_token": "eyJ...", "token_type": "Bearer", "expires_in": 86400 }
```
Note: Auth0 machine-to-machine tokens default to `expires_in: 86400` (24h). The D-07 3600s fallback only applies if `expires_in` is absent (non-standard server) — Auth0 always returns it.

### pytest-httpx mock for fetch + TTL-expiry refetch (sync)
```python
# Source: adaptation of packages/iol-client/tests/test_refresh_token_lifecycle.py
def test_token_fetched_cached_and_refetched_on_ttl_expiry(httpx_mock: HTTPXMock) -> None:
    state = market_data_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0     # force initial fetch

    httpx_mock.add_response(
        url="https://auth.test/oauth/token", method="POST",
        match_content=(b"grant_type=client_credentials&client_id=cid"
                       b"&client_secret=csec&audience=aud"),
        json={"access_token": "TOK-1", "token_type": "Bearer", "expires_in": 3600},
        is_reusable=True,
    )
    httpx_mock.add_response(url="https://market-data-develop.test/api/health",
                            json={"status": "ok"}, is_reusable=True)

    market_data_client.get_health()          # health is anonymous → but exercise an authed call for token
    # For the token path, call an authenticated endpoint or assert token cached:
    assert state.token == "TOK-1"

    state.token_expires_at = 0.0             # simulate TTL expiry
    # next authenticated call re-runs the grant → assert a second token POST occurred
```
> For the token lifecycle specifically, drive it through an authenticated request (or expose `login()`/`_ensure_token()` for the test). Health is anonymous and does NOT fetch a token — use it only for the health-smoke test, not the token-refresh test.

### Redaction unit (client_secret, D-11)
```python
# Source: adaptation of packages/iol-client/tests/test_logging.py
def test_redact_client_secret_urlenc() -> None:
    f = RedactingFilter()
    rec = _make_record("token form: grant_type=client_credentials&client_secret=sup3r-s3cret&audience=aud")
    f.filter(rec)
    assert "sup3r-s3cret" not in rec.msg
    assert "client_secret=***" in rec.msg

def test_redact_client_secret_json() -> None:
    f = RedactingFilter()
    rec = _make_record('body={"client_secret":"sup3r-s3cret"}')
    f.filter(rec)
    assert "sup3r-s3cret" not in rec.msg
    assert '"client_secret":"***"' in rec.msg
```

## State of the Art

| Old Approach (iol carries) | Current Approach (market-data) | Why Changed | Impact |
|----------------------------|-------------------------------|-------------|--------|
| OAuth password + refresh_token rotation (CR-01) | Auth0 single `client_credentials` grant | Headless machine-to-machine; no user, no refresh token | ~half the auth code deleted; parser is a 2-tuple |
| Disk token cache (`_token_cache.py` + `platformdirs`, flock, 0600) | In-memory token only | Deferred to v1.5+ (SEC-MD-01) | No `platformdirs` dep; no cold-start disk read |
| All requests authenticated | `authenticated: bool` flag; health anonymous | Health endpoints are public | New branch in `_request`, mirrored sync/async |
| `with_options(max_retries=N)` shared-view clone | Not present | Deferred to Phase 21 | Simpler `Client`; no `_is_view` machinery |

**Deprecated/outdated for this package (do NOT carry from iol):**
- PEP 562 read-only module shim (`__getattr__`, `_FORWARDED_TO_STATE`, `_DENIED_LEGACY`) — iol back-compat for v1.0 globals; the new package has no legacy globals.
- `_validate_max_retries` + `__reduce__`/`__deepcopy__` guards — optional; not required by Phase 20 success criteria.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Health endpoints are reached at `{MARKET_DATA_BASE_URL}/health` and `/health/feed` (base URL includes `/api`, so effective `.../api/health`) | Pattern 3 / Mirror Map `_core.py` | If health lives at host root (not under `/api`), the health builder path must be absolute or base_url must be split. Confirm the exact health URL against the OpenAPI/live develop server before implementing the smoke test. |
| A2 | `MARKET_DATA_AUTH0_TOKEN_URL` is a full absolute URL (e.g. `https://<tenant>.auth0.com/oauth/token`), dispatched directly (not `base_url + path`) | Pitfall 1 | If it were a path relative to some auth base, `_send_auth_request` dispatch differs. D-05 phrasing ("POST a `MARKET_DATA_AUTH0_TOKEN_URL`") strongly implies absolute; confirm the `.env` value shape. |
| A3 | Auth0 returns `expires_in` in the response (so the 3600s fallback is rarely exercised) | Pitfall 5 / D-07 | Low risk — Auth0 always returns `expires_in`. The fallback is defensive only. |
| A4 | The `configure()` surface for market-data takes `client_id`/`client_secret`/`audience`/`auth0_token_url`/`base_url`/`token`/`token_expires_at` (no username/password/refresh_token) | Mirror Map `client.py`, conftest | If the planner wants a narrower `configure()`, adjust the conftest fixture accordingly. Naming is Claude's Discretion. |
| A5 | `expires_in` may arrive as int or numeric string; `float(expires_in)` coerces both | Code Examples | iol uses `float(expires_in)`; Auth0 returns an int. Safe. |

## Open Questions

1. **Exact health endpoint URL (under `/api` or host root?)**
   - What we know: source plan lists `GET /health`, `GET /health/feed` as anonymous; base URL default is `https://market-data-develop.bbsa.com.ar/api`.
   - What's unclear: whether health is `.../api/health` or `.../health`.
   - Recommendation: Default to `{base_url}/health` (mirrors iol's `{base_url}{path}`); add a `checkpoint:human-verify` or confirm against the OpenAPI spec / a live curl before the live smoke (Phase 23). For Phase 20 the mock makes this test-internal, so pick `{base_url}/health` and note it.

2. **Shape of `MARKET_DATA_AUTH0_TOKEN_URL` (.env value)**
   - What we know: D-05 says POST to this variable.
   - What's unclear: absolute URL vs path.
   - Recommendation: Treat as absolute (A2). The `.env.example` should show a full `https://.../oauth/token` placeholder.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.12.11 (venv) | — |
| uv | workspace mgmt | ✓ | 0.9.0 | — |
| httpx | transport | ✓ (in uv.lock) | 0.28.1 | — |
| tenacity | retry transport | ✓ (in uv.lock) | 9.1.4 | — |
| python-dotenv | env loading | ✓ (in uv.lock) | 1.x | — |
| pytest-httpx | test mocking | ✓ (in uv.lock) | 0.36.2 | — |
| Auth0 tenant / live develop server | Phase 23 live verification only | N/A this phase | — | Phase 20 uses mocks exclusively |

**Missing dependencies with no fallback:** none — Phase 20 is fully mockable; no live service needed.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode="auto"`) + pytest-httpx |
| Config file | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run --package market-data-client pytest packages/market-data-client/tests -x -q` |
| Full suite command | `uv run pytest packages/market-data-client/tests` |

### Phase Requirements → Test Map
| Success Criterion | Behavior | Test Type | Automated Command | File Exists? |
|-------------------|----------|-----------|-------------------|-------------|
| SC1 | `import market_data_client` + `from market_data_client import aio`; `__version__=="0.1.0"`; `py.typed` present; deps in pyproject | unit/smoke | `uv run --package market-data-client python -c "import market_data_client as m, market_data_client.aio; assert m.__version__=='0.1.0'"` | ❌ Wave 0 |
| SC2 (AUTH-MD-01) | client_credentials token fetch + cache + TTL-expiry refetch (sync) | unit | `pytest tests/test_token_lifecycle.py -x` | ❌ Wave 0 |
| SC2 (AUTH-MD-01) | same, async with `asyncio.Lock` double-checked | unit | `pytest tests/test_token_lifecycle_async.py -x` | ❌ Wave 0 |
| SC3 (CORE-MD-01) | `GET /health` + `/health/feed` via retry transport, anonymous (no token fetch) | unit | `pytest tests/test_client.py::test_health -x` | ❌ Wave 0 |
| SC3 (CORE-MD-01) | exception mapping 401/403→Auth, 429→RateLimit, other→APIError | unit | `pytest tests/test_core.py::test_raise_for_response -x` | ❌ Wave 0 |
| SC4 (CORE-MD-01) | zero credential leakage — Bearer / access_token / client_secret redacted (caplog + RedactingFilter) | unit | `pytest tests/test_logging.py -x` | ❌ Wave 0 |
| SC5 | 4 gates green for the package | gate | `uv run ruff check packages/market-data-client && uv run ruff format --check packages/market-data-client && uv run mypy packages/market-data-client/src && uv run pytest packages/market-data-client/tests` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** quick run (`pytest ... -x -q` for the touched test file) + `ruff check` on changed files.
- **Per wave merge:** full package suite + `mypy` strict on `src`.
- **Phase gate:** all 4 gates green (ruff, ruff format, mypy strict, pytest) for `packages/market-data-client` before `/gsd-verify-work`. Also confirm the CI logging grep gate (`.github/workflows/ci.yml:42-48`) is not violated (no `logging.basicConfig`/`logging.root.*` in src).

### Wave 0 Gaps
- [ ] `tests/conftest.py` — autouse sync + async `configure()` fixtures (client_id/secret/audience/auth0_token_url/base_url + seeded token), transport close on teardown; `NEVER_EXPIRES` constant.
- [ ] `tests/test_core.py` — pure builder/parser + `raise_for_response` mapping (all 4 status→exception rows).
- [ ] `tests/test_token_lifecycle.py` + `tests/test_token_lifecycle_async.py` — fetch/cache/TTL-refetch, mocked.
- [ ] `tests/test_client.py` + `tests/test_async_client.py` — dispatch + health anonymous + 401 re-auth-once.
- [ ] `tests/test_logging.py` — Bearer/access_token/client_secret redaction + attach idempotency.
- [ ] `tests/test_transport.py` — (optional) copy iol's retry-semantics tests.
- [ ] Framework: no install needed (test deps already in `uv.lock`); add `market-data-client` to the workspace so `uv sync --all-packages` picks it up. NOTE: adding it to the CI matrix (`ci.yml`) + `uv.lock` regeneration is Phase 24 (PUB-MD-01), but local gates must pass now.

## Security Domain

`security_enforcement: true` — this section is required.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OAuth2 `client_credentials` against Auth0; credentials from env (`python-dotenv`), never hard-coded |
| V3 Session Management | partial | Bearer access token cached in-memory only (no disk this phase, D-02); TTL-bounded with 60s refresh buffer |
| V4 Access Control | no (this phase) | Read-only endpoints; health is intentionally public |
| V5 Input Validation | minimal | No user-supplied input beyond env config; JSON parse guarded (`parse_token_response` type-checks `access_token`) |
| V6 Cryptography | no | TLS handled by httpx; JWT signature validation explicitly deferred (SEC-MD-02, v1.5+) — tokens are trusted from Auth0 over TLS, not decoded |
| V7 Error Handling & Logging | yes | `RedactingFilter` scrubs Bearer/access_token/client_secret; NullHandler; no `logging.root` (CI gate) |
| V9 Communications | yes | httpx TLS by default; Auth0 token URL and base URL are HTTPS |

### Known Threat Patterns for market-data-client
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `client_secret` leaked in logs (form body or JSON) | Information Disclosure | `RedactingFilter` `client_secret` patterns (D-11) — CORE-MD-01 gate, tested via caplog |
| `access_token` / Bearer leaked in logs | Information Disclosure | `_BEARER_RE` + `_ACCESS_TOKEN_JSON_RE` redaction |
| Credentials committed to git | Information Disclosure | `.env` gitignored; only `.env.example` with placeholders committed (project constraint) |
| Token grant retried on 401 (credential brute path) | — | 401 from the token endpoint is NOT retryable (mutation-gate + `raise_for_response` raises `MarketDataAuthError` before the retry loop sees it) |
| Auth-server hammering on repeated failures | Denial of Service | RefreshPolicy fail-cache is deferred (D-12); single-grant + TTL buffer bounds re-auth frequency; retries are full-jitter capped |
| Stale token reuse after expiry | Spoofing | `token_is_fresh` checks `time.time() < token_expires_at` with 60s safety buffer |

## Sources

### Primary (HIGH confidence)
- `packages/iol-client/src/iol_client/` — full read of `_core.py`, `_state.py`, `_transport.py`, `_atransport.py`, `_logging.py`, `client.py`, `aio.py`, `exceptions.py`, `__init__.py`, `pyproject.toml`, `tests/conftest.py`, `tests/test_refresh_token_lifecycle.py`, `tests/test_logging.py` — the template being mirrored.
- `.planning/phases/20-.../20-CONTEXT.md` — 14 locked decisions (D-01..D-14).
- `.planning/REQUIREMENTS.md` — AUTH-MD-01, CORE-MD-01 acceptance criteria.
- `.planning/ROADMAP.md` § Phase 20 — 5 success criteria.
- `.future_plans/market_data.md` — source milestone plan (D-01..D-07, scope).
- `uv.lock` — verified locked versions (tenacity 9.1.4, httpx 0.28.1, pytest-httpx 0.36.2).
- `.github/workflows/ci.yml` — CI gates incl. logging grep gate (`:42-48`) and per-package mypy/test matrix.

### Secondary (MEDIUM confidence)
- Auth0 official docs — Client Credentials Flow token endpoint request/response shape [CITED: auth0.com/docs/get-started/authentication-and-authorization-flow/client-credentials-flow].

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — deps already in the repo lockfile and used by 5 packages.
- Architecture / Mirror Map: HIGH — template read in full; deltas are bounded and driven by explicit D-locks.
- Auth0 grant wire shape: HIGH — confirmed against official Auth0 docs; matches D-05.
- Pitfalls: HIGH — derived from actual iol source line references + the two structural deltas (absolute token URL, anonymous path).
- Open questions (health URL, token URL shape): MEDIUM — resolvable from OpenAPI/`.env` before implementation; do not block Phase 20 (mocked).

**Research date:** 2026-07-29
**Valid until:** 2026-08-28 (stable domain; iol template and locked deps unlikely to shift within 30 days).
