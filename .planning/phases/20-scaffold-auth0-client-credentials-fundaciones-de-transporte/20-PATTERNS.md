# Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte - Pattern Map

**Mapped:** 2026-07-29
**Files analyzed:** 15 (13 source/config + tests suite)
**Analogs found:** 15 / 15 — every new file mirrors a concrete `iol-client` counterpart (single-template phase)

> **Package identity:** new package `packages/market-data-client/src/market_data_client/`; import name `market_data_client`; dist name `market-data-client`. Every analog below is the `iol-client` file at the same relative path. This is a **mirror-with-deltas** phase — ~70% verbatim/near-verbatim copy plus the bounded delta set the research already isolated (D-01..D-14).

## File Classification

| New file (under `packages/market-data-client/`) | Role | Data Flow | Closest Analog | Match Quality |
|-------------------------------------------------|------|-----------|----------------|---------------|
| `src/market_data_client/_core.py` | pure builders/parsers (auth + health + error map) | transform / request-response | `packages/iol-client/src/iol_client/_core.py` | exact (heavy reduction) |
| `src/market_data_client/_state.py` | state (per-instance dataclass) | config | `iol_client/_state.py` | exact (reduce) |
| `src/market_data_client/_transport.py` | transport (sync retry) | request-response | `iol_client/_transport.py` | **exact — verbatim** |
| `src/market_data_client/_atransport.py` | transport (async retry) | request-response | `iol_client/_atransport.py` | **exact — verbatim** |
| `src/market_data_client/_logging.py` | middleware (log redaction filter) | event-driven | `iol_client/_logging.py` | exact (change patterns) |
| `src/market_data_client/client.py` | controller (sync client shell) | request-response | `iol_client/client.py` | exact (heavy reduction) |
| `src/market_data_client/aio.py` | controller (async client shell) | request-response | `iol_client/aio.py` | exact (heavy reduction) |
| `src/market_data_client/exceptions.py` | model (exception hierarchy) | — | `iol_client/exceptions.py` | exact (rename) |
| `src/market_data_client/__init__.py` | config (package entry / re-exports) | — | `iol_client/__init__.py` | exact (reduce) |
| `src/market_data_client/py.typed` | config (PEP 561 marker) | — | `iol_client/py.typed` (empty) | exact — verbatim (empty) |
| `pyproject.toml` | config (package metadata/build) | — | `packages/iol-client/pyproject.toml` | exact (adapt, subtract `platformdirs`) |
| `tests/conftest.py` | test (fixtures) | — | `iol-client/tests/conftest.py` | exact (adapt) |
| `tests/test_token_lifecycle*.py` | test | — | `iol-client/tests/test_refresh_token_lifecycle.py` | role-match (simplify) |
| `tests/test_logging.py` | test | — | `iol-client/tests/test_logging.py` | exact (adapt patterns) |
| `.env.example`, `README.md` | config / docs | — | iol counterparts | role-match |

---

## Pattern Assignments

### `_core.py` (pure builders/parsers, transform)

**Analog:** `packages/iol-client/src/iol_client/_core.py`

**Imports + `__all__`** (`_core.py:45-73`) — copy the import block; swap exception names and reduce `__all__` to the market-data surface (`RequestSpec`, `build_token_request`, `parse_token_response`, `build_health_request`, `build_health_feed_request`, `parse_health_response`, `raise_for_response`, `token_is_fresh`):
```python
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any
import httpx
from market_data_client._state import _TOKEN_TTL_BUFFER_SECONDS, _ClientState  # + _TOKEN_TTL_FALLBACK_SECONDS
from market_data_client.exceptions import MarketDataAPIError, MarketDataAuthError, MarketDataRateLimitError
```
> DELTA: iol imports `datetime as dt` and `Literal` for its endpoint builders — OMIT (no dated/enum endpoints this phase).

**`RequestSpec`** (`_core.py:81-104`) — copy the frozen slotted dataclass VERBATIM, then **ADD one field** `authenticated: bool = True` (D-09, net-new vs iol). Keep `data`, `idempotent`, `endpoint_name`, `params`, `headers`, `json_body`:
```python
@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    idempotent: bool = False
    endpoint_name: str = ""
    authenticated: bool = True   # NEW — health builders pass False (D-08/D-09)
```

**`raise_for_response`** (`_core.py:112-125`) — copy VERBATIM, rename exceptions (D-14 mapping is identical to iol: 401/403→Auth, 429→RateLimit, other error→APIError):
```python
def raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise MarketDataAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise MarketDataRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise MarketDataAPIError(resp.status_code, resp.text)
```

**`token_is_fresh`** (`_core.py:128-134`) — copy VERBATIM (only the type-hint import name changes):
```python
def token_is_fresh(state: _ClientState) -> bool:
    return bool(state.token and time.time() < state.token_expires_at)
```

**Auth builder — REPLACE iol's `build_login_request` (`_core.py:142-166`).** The shape (validate creds → form-encoded `data` → `Content-Type: x-www-form-urlencoded` → `idempotent=True`) is the model, but the grant is `client_credentials` and `path=""` (dispatched to the ABSOLUTE `state.auth0_token_url`, see Shared Pattern “Absolute token URL”). Set `authenticated=False`:
```python
def build_token_request(state: _ClientState) -> RequestSpec:
    if not state.client_id or not state.client_secret or not state.audience:
        raise MarketDataAuthError(0, "MARKET_DATA_CLIENT_ID/SECRET/AUDIENCE requeridos")
    return RequestSpec(
        method="POST",
        path="",  # dispatched to the ABSOLUTE state.auth0_token_url (Pitfall 1)
        data={
            "grant_type": "client_credentials",
            "client_id": state.client_id,
            "client_secret": state.client_secret,
            "audience": state.audience,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        idempotent=True,
        endpoint_name="token",
        authenticated=False,
    )
```

**Auth parser — REPLACE iol's `parse_login_response` (`_core.py:169-195`).** Keep the body-consume-then-raise order (`resp.read()` → `raise_for_response` → `resp.json()`) and the `access_token` type-guard. COLLAPSE to a **2-tuple** (no refresh slot, D-05) and change the `expires_in` default from `900` to the **3600s fallback** (D-07, Pitfall 5):
```python
def parse_token_response(resp: httpx.Response) -> tuple[str, float]:
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise MarketDataAuthError(resp.status_code, "No access_token in response")
    expires_in = data.get("expires_in", _TOKEN_TTL_FALLBACK_SECONDS)  # 3600 — D-07
    expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token, expires_at
```

**Health builders — NET-NEW (no iol analog; model on the state-independent endpoint builders `_core.py:234-256, 286-300`** which use `del state` + `idempotent=True` + `endpoint_name`):
```python
def build_health_request(state: _ClientState) -> RequestSpec:
    del state
    return RequestSpec(method="GET", path="/health", idempotent=True,
                       endpoint_name="health", authenticated=False)

def build_health_feed_request(state: _ClientState) -> RequestSpec:
    del state
    return RequestSpec(method="GET", path="/health/feed", idempotent=True,
                       endpoint_name="health_feed", authenticated=False)

def parse_health_response(resp: httpx.Response) -> dict[str, Any]:  # model on parse_get_quote_response :327-332
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    return data
```

**OMIT entirely:** `build_refresh_request`/`parse_refresh_response` (`_core.py:198-226`), all 4 endpoint builders (`:234-319`) + parsers (`:327-360`), the CR-01 docstring block (`:36-42`), and the `Literal`/`datetime` imports.

---

### `_state.py` (state dataclass, config)

**Analog:** `iol_client/_state.py`

**Constants** (`_state.py:56-59`) — keep `_REQUEST_TIMEOUT=30.0` and `_TOKEN_TTL_BUFFER_SECONDS=60` verbatim; change `DEFAULT_BASE_URL`; ADD the D-07 fallback constant:
```python
DEFAULT_BASE_URL = "https://market-data-develop.bbsa.com.ar/api"   # was iol's api.invertironline.com
_REQUEST_TIMEOUT = 30.0
_TOKEN_TTL_BUFFER_SECONDS = 60
_TOKEN_TTL_FALLBACK_SECONDS = 3600   # NEW — D-07 (only when expires_in absent)
```

**Env factories** (`_state.py:62-72`) — copy the `_env_base_url()` shape (`os.getenv(..., DEFAULT).rstrip("/")`); replace `_env_user`/`_env_password` with `MARKET_DATA_*` factories: `_env_client_id` (`MARKET_DATA_CLIENT_ID`), `_env_client_secret` (`MARKET_DATA_CLIENT_SECRET`), `_env_audience` (`MARKET_DATA_AUDIENCE`), `_env_auth0_token_url` (`MARKET_DATA_AUTH0_TOKEN_URL`). Base-url factory reads `MARKET_DATA_BASE_URL`.

**`_ClientState`** (`_state.py:75-103`) — copy the `@dataclass(slots=True)` (non-frozen — the docstring rationale at `:9-18` applies verbatim) with `field(default_factory=...)`. KEEP: `base_url`, `token`, `token_expires_at`, `http_client`, `token_lock`, `client_lock` (all lazy-lock semantics `:91-100`). ADD: `client_id`, `client_secret`, `audience`, `auth0_token_url` (env factories). **REMOVE:** `username`, `password` (`:85-86`), `refresh_token` (`:89`), `token_cache_path` (`:103`), and the `from pathlib import Path` import (`:45`).

---

### `_transport.py` (sync retry transport) — **COPY VERBATIM**

**Analog:** `iol_client/_transport.py` (202 lines)

Copy the ENTIRE file. The **only** edit is the logger-name constant (`_transport.py:61`):
```python
_LOGGER_NAME = "market_data_client"   # was "iol_client"
```
Everything else stays byte-for-byte — the retryable set and backoff constants (`_transport.py:54-60`, `:142`):
```python
_RETRYABLE_EXC = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)     # :54-58
_RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)})                    # :59
_RETRY_AFTER_CAP_S = 60.0                                                            # :60
wait=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)          # :142
```
KEEP the mutation gate (`:125` `if not request.extensions.get("idempotent", False): return super().handle_request(request)`), the `max_attempts <= 1` bypass (`:128`), `_RetryableStatus` sentinel (`:69-80`), `_parse_retry_after` RFC-9110 delta+HTTP-date (`:88-101`), and the `Retry-After` cap application (`:154-158`). Update docstring references from iol→market-data (cosmetic).
> NOTE: iol reads `request.extensions.get("account_id")` (`:133`, `:169`) and `max_attempts` override (`:135`) — these are harmless no-ops for market-data (specs never set them). Copying verbatim is fine; the `max_attempts` extension is simply never populated (no `with_options` this phase).

---

### `_atransport.py` (async retry transport) — **COPY VERBATIM**

**Analog:** `iol_client/_atransport.py` (134 lines)

Copy the ENTIRE file. The intra-package import block (`_atransport.py:31-38`) pulls `_LOGGER_NAME`, `_RETRY_AFTER_CAP_S`, `_RETRYABLE_EXC`, `_is_retryable_status`, `_parse_retry_after`, `_RetryableStatus` from the sibling `_transport` — change ONLY the package path:
```python
from market_data_client._transport import (   # was iol_client._transport
    _LOGGER_NAME, _RETRY_AFTER_CAP_S, _RETRYABLE_EXC,
    _is_retryable_status, _parse_retry_after, _RetryableStatus,
)
```
No other edits. (Intra-package module coupling is allowed by design — `_atransport.py:9-13`.)

---

### `_logging.py` (redaction filter, middleware) — change patterns (D-11)

**Analog:** `iol_client/_logging.py` (112 lines)

**KEEP the structure verbatim:** `RedactingFilter.filter()` (`_logging.py:81-95`, scans `record.msg` / `record.args` dict|tuple / `record.__dict__` for sentinels) and `attach()` (`:98-111`, idempotent `NullHandler` + filter on `getLogger("market_data_client")` ONLY — never `logging.root`). Change `getLogger("iol_client")` → `getLogger("market_data_client")` at `:107`.

**CHANGE the pattern set (`_logging.py:40-59`).** KEEP `_BEARER_RE` (`:40`) and `_ACCESS_TOKEN_JSON_RE` (`:49`). REMOVE `_X_AUTH_TOKEN_RE` (`:41`), `_PASSWORD_*` (`:42-43`), `_REFRESH_TOKEN_*` (`:46-47`). ADD `client_secret` in both wire shapes (D-11, CORE-MD-01 zero-leakage gate):
```python
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")                          # KEEP
_ACCESS_TOKEN_JSON_RE = re.compile(r'("access_token"\s*:\s*")[^"]+(")')        # KEEP
_CLIENT_SECRET_URLENC_RE = re.compile(r"(client_secret=)[^&\s]+")             # NEW (form body)
_CLIENT_SECRET_JSON_RE = re.compile(r'("client_secret"\s*:\s*")[^"]+(")')     # NEW (JSON)

_REDACTION_MARKERS = ("Bearer ", "client_secret=", '"client_secret"', '"access_token"')
```
Update `_redact()` (`:62-70`) to run exactly these four passes (Bearer, client_secret urlenc `\1***`, client_secret JSON `\1***\2`, access_token JSON `\1***\2`).
> **CI GATE:** `.github/workflows/ci.yml` greps `packages/*/src/` for `logging.basicConfig(` and `logging.root.\w` (regex `logging\.basicConfig\s*\(|logging\.root\.\w`). `attach()` must touch only `getLogger("market_data_client")` — never `basicConfig`/`root`. Docstring mentions of "logging.root" are fine (the grep only matches the call/attribute form).

---

### `client.py` (sync client shell, controller)

**Analog:** `iol_client/client.py` (757 lines — heavy reduction)

**Module-level alias (B8 identity)** (`client.py:81`) — copy verbatim, rename:
```python
_raise_for_response = _core.raise_for_response
```

**`_ensure_http_client`** (`client.py:244-262`) — copy the lazy-create pattern; wrap `_transport.RetryTransport`. Since `with_options`/`_max_retries` are OUT (deferred to Phase 21), hard-code `max_attempts` to a module default (e.g. `3` = 2 retries) or read a `_DEFAULT_MAX_ATTEMPTS` constant instead of `self._max_retries + 1`:
```python
new_client = httpx.Client(timeout=_REQUEST_TIMEOUT,
    transport=_transport.RetryTransport(max_attempts=_DEFAULT_MAX_ATTEMPTS))
```

**Auth dispatch — `_send_auth_request`** (`client.py:331-357`) — copy the extension-propagation body BUT **change the dispatch URL** from `f"{self._state.base_url}{spec.path}"` (`:346`) to the ABSOLUTE `self._state.auth0_token_url` (Pitfall 1 — CRITICAL). Drop the `max_attempts` extension line (`:356`).

**COLLAPSE auth trio → pair.** Replace `login`/`_refresh`/`_ensure_token` (`client.py:359-427`) with:
```python
def _authenticate(self) -> str:                          # reduction of login() :359-380
    spec = _core.build_token_request(self._state)
    resp = self._send_auth_request(spec)
    token, expires_at = _core.parse_token_response(resp)  # 2-tuple
    self._state.token = token
    self._state.token_expires_at = expires_at
    return token

def _ensure_token(self) -> None:                          # reduction of :405-427
    if _core.token_is_fresh(self._state):
        return
    self._authenticate()   # re-running the grant IS the refresh (D-05)
```
OMIT: all `refresh_token` writes, the `if refresh is not None` CR-01 guard, and every `_token_cache.*` call (`:374-379`, `:397-402`, `:406-411`, `:422-424`).

**`_request` — add the `authenticated` branch (D-08/D-09, Pitfall 4).** Model on iol `client.py:429-491` but gate BOTH the token injection AND the 401 re-auth carve-out on `spec.authenticated`:
```python
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
    req.extensions["request_id"] = uuid.uuid4().hex
    req.extensions["endpoint_name"] = spec.endpoint_name
    resp = http.send(req)
    try:
        _raise_for_response(resp)
    except MarketDataAuthError:
        if not spec.authenticated:
            raise                       # health 401 is a real error — NO re-auth (Pitfall 4)
        resp.read()
        self._state.token = None        # exactly-one re-auth (iol :481-490)
        self._ensure_token()
        assert self._state.token is not None
        req.headers["Authorization"] = f"Bearer {self._state.token}"
        resp = http.send(req); resp.read(); _raise_for_response(resp)
    return resp
```

**`configure()`** (`client.py:573-639`) — copy the carry-forward `None`-ignore skeleton; change the kwarg set to `base_url, client_id, client_secret, audience, auth0_token_url, token, token_expires_at, http_client`. On credential rotation, reset `token=None` + `token_expires_at=0.0` (mirror `:614-619` but with the new creds; drop `refresh_token`). REMOVE `username`/`password`/`refresh_token`/`max_retries` kwargs, `_validate_max_retries` (`:86-108`, `:606-608`).

**Module-level surface** (`client.py:565-570, 642-682`) — copy `_get_default()` verbatim; replace the endpoint shims with `get_health()` / `get_health_feed()` delegating to the default `Client`.

**OMIT:** `_validate_max_retries` (`:86`), `with_options`/`_is_view` (`:264-329`), `__reduce__`/`__deepcopy__` (`:227-243`, optional), all endpoint methods (`:497-563`), the PEP 562 `__getattr__` shim (`:737+`) and legacy `_request` shim (`:685+`).

---

### `aio.py` (async client shell, controller)

**Analog:** `iol_client/aio.py` (~760 lines — heavy reduction; mirror of `client.py` deltas)

**KEEP verbatim:** double-checked `_ensure_http_client` (`aio.py:213-240`, wraps `_atransport.AsyncRetryTransport`), lazy `_ensure_client_lock` (`:242-251`) and `_ensure_token_lock` (`:253-256`) — these ARE the D-12 per-loop `asyncio.Lock` pattern; DO NOT use matriz's `TokenStore` (Pitfall 2: lazy lock binds to the running loop).

**`_send_auth_request`** (`aio.py:312-337`) — copy; **change dispatch URL** to `self._state.auth0_token_url` (`:326` is the line to change); drop the `max_attempts` extension.

**COLLAPSE async auth.** Replace `_login_unlocked`/`_refresh_unlocked`/`login`/`_aensure_token` (`aio.py:339-432`) with `_authenticate_unlocked()` (caller holds lock) + the double-checked `_aensure_token`:
```python
async def _authenticate_unlocked(self) -> str:       # reduction of _login_unlocked :339-...
    spec = _core.build_token_request(self._state)
    resp = await self._send_auth_request(spec)
    token, expires_at = _core.parse_token_response(resp)
    self._state.token = token
    self._state.token_expires_at = expires_at
    return token

async def _aensure_token(self) -> None:              # reduction of :401-432
    if _core.token_is_fresh(self._state):
        return
    lock = self._ensure_token_lock()
    async with lock:
        if _core.token_is_fresh(self._state):        # double-check inside lock (D-12)
            return
        await self._authenticate_unlocked()
```
OMIT the `_token_cache` disk-load/delete branches (`:402-411`, `:427-428`) and the refresh_token fork.

**`_request`** (`aio.py:434-512`) — mirror the sync `authenticated` branch. Gate `await self._aensure_token()` + the `Authorization` header on `spec.authenticated`; on `MarketDataAuthError`, `if not spec.authenticated: raise` first, else clear-then-reauth under the token_lock exactly once (simplify iol's `:493-505` shared-view logic to a single grant). ADD async `get_health()` / `get_health_feed()`.

**`configure()`** + `_get_default()` (`aio.py:572-655`) — same delta as `client.py::configure`, async surface with independent module state.

---

### `exceptions.py` (exception hierarchy, model) — rename (D-14)

**Analog:** `iol_client/exceptions.py` (`:1-24`) — copy the 4-class structure verbatim, rename:
```python
class MarketDataError(Exception): ...
class MarketDataAPIError(MarketDataError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message
class MarketDataAuthError(MarketDataAPIError): ...       # 401/403
class MarketDataRateLimitError(MarketDataAPIError): ...  # 429
```
> Base class is `MarketDataError` (not `MarketDataClientError`) per D-14 wording. iol's base is `IOLClientError` — the rename target per CONTEXT is `MarketDataError`.

---

### `__init__.py` (package entry, config) — reduce

**Analog:** `iol_client/__init__.py` (`:1-73`)

**KEEP the critical ordering VERBATIM** (`__init__.py:23-30`) — `_logging.attach()` MUST run BEFORE any other import:
```python
from market_data_client import _logging as _logging_attach
_logging_attach.attach()
del _logging_attach
from market_data_client.aio import AsyncClient  # noqa: E402
from market_data_client.client import Client, _get_default, configure, get_health, get_health_feed  # noqa: E402
from market_data_client.exceptions import (  # noqa: E402
    MarketDataAPIError, MarketDataAuthError, MarketDataError, MarketDataRateLimitError,
)
```
Re-export `Client`, `AsyncClient`, the 4 exceptions, `configure`, `get_health`, `get_health_feed` in `__all__`. Set `__version__ = "0.1.0"` (iol `:73` has `"0.2.0"`). REMOVE `InstrumentType` + endpoint shims from the imports/`__all__` (`:38-43`, `:59-67`). Keep the `_get_default` private re-export idiom (`:51-53, 71`) for tests (optional).

---

### `pyproject.toml` (config) — adapt

**Analog:** `packages/iol-client/pyproject.toml` (`:1-45`)

Copy the whole file; change `name="market-data-client"`, `version="0.1.0"`, description/keywords. **SUBTRACT `platformdirs`** (iol `:25`) — deferred with `_token_cache.py`. Runtime deps become exactly:
```toml
dependencies = [
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "tenacity>=9.1.0,<10",
]
```
Keep `[project.optional-dependencies].test` verbatim (`:28-34`), `[build-system]` hatchling (`:36-38`), and `[tool.hatch.build.targets.wheel] packages = ["src/market_data_client"]` (`:40-41`) + sdist include (`:43-44`). Name must satisfy the release-tag regex `*-client-v*` — `market-data-client` does.
> iol carries an `import-linter` contract referenced in `_core.py:12-13`; iol's own `pyproject.toml` shown here does not include the `[tool.importlinter]` block (it lives in the root config). No action needed for Phase 20 beyond keeping `_core.py` free of `client`/`aio` imports.

---

### `tests/conftest.py` (test fixtures) — adapt

**Analog:** `iol-client/tests/conftest.py` (`:1-59`)

Copy the two autouse fixtures (`_configure_sync` `:32-46`, `_configure_async` `:48-59`) and the `NEVER_EXPIRES = 9_999_999_999.0` sentinel (`:29`). Change the `configure(...)` kwargs to the market-data set and seed a token:
```python
market_data_client.configure(
    base_url="https://market-data-develop.test/api",
    client_id="cid", client_secret="csec", audience="aud",
    auth0_token_url="https://auth.test/oauth/token",
    token="test-token", token_expires_at=NEVER_EXPIRES,
)
```
Keep the teardown `close()`/`aclose()` on the default client + reset creds (Pitfall 6 — cross-test singleton contamination).

---

### `tests/test_token_lifecycle.py` + `_async.py` — simplify

**Analog:** `iol-client/tests/test_refresh_token_lifecycle.py` (`:40-75` is the model)

Reduce the 4-path refresh matrix to a single **fetch → cache → TTL-expiry refetch** test. Seed `state.token=None; state.token_expires_at=0.0`, mock the token URL with `match_content` on the client_credentials body, assert token cached, then force `token_expires_at=0.0` and assert a SECOND token POST (assert on `len(httpx_mock.get_requests())`, NOT ordering — Pitfall 3; the body is identical across fetch+refetch). Use `is_reusable=True` (research Code Examples). Mirror async with the double-checked lock. Drive the token path through an authenticated request or `_ensure_token()` directly — **health is anonymous and does NOT fetch a token**.

---

### `tests/test_logging.py` — adapt patterns

**Analog:** `iol-client/tests/test_logging.py` (`:1-60`)

Keep the `_make_record` helper (`:19-34`, change `name="market_data_client"`), the attach-idempotency test (`:37-46`), the Bearer test (`:49-55`), and the access_token JSON test. REPLACE the password/refresh_token tests with `client_secret` urlenc + JSON tests (research Code Examples §Redaction unit):
```python
def test_redact_client_secret_urlenc() -> None:
    rec = _make_record("grant_type=client_credentials&client_secret=sup3r-s3cret&audience=aud")
    RedactingFilter().filter(rec)
    assert "sup3r-s3cret" not in rec.msg and "client_secret=***" in rec.msg
```

---

## Shared Patterns

### Absolute Auth0 token URL (CRITICAL — Pitfall 1)
**Source of the anti-pattern:** `iol_client/client.py:346` and `aio.py:326` dispatch auth to `f"{self._state.base_url}{spec.path}"`.
**Apply to:** `client.py::_send_auth_request`, `aio.py::_send_auth_request`.
**Rule:** market-data dispatches the token grant to the ABSOLUTE `self._state.auth0_token_url` (a separate host), NOT `base_url + path`. `base_url` is reserved for `/health*` and Phase 21+ endpoints. Verbatim copy would POST to `.../api/token` and 404.

### B8 identity — module-level `_raise_for_response` alias
**Source:** `iol_client/client.py:81` (`_raise_for_response = _core.raise_for_response`); referenced by both `client.py` and `aio.py`.
**Apply to:** both shells — alias the SAME `_core.raise_for_response` object so `aio._raise_for_response is client._raise_for_response`. Do not re-implement the mapping in each module.

### Credential redaction (CORE-MD-01 gate)
**Source:** `iol_client/_logging.py:81-111` (`RedactingFilter` + `attach()`).
**Apply to:** all modules (via `__init__.py` `attach()` at import). Scrub `Bearer` / `access_token` / `client_secret` (urlenc + JSON). Filter attaches only to `getLogger("market_data_client")`. CI grep gate forbids `logging.basicConfig(`/`logging.root.*` in `src/`.

### Body-consume-then-raise (Phase 7 D-06)
**Source:** every `_core.py` parser (`:185-186`, `:329-330`) and the transport retry loop (`_transport.py:152`).
**Apply to:** `parse_token_response`, `parse_health_response`, and the `_request` 401 carve-out — always `resp.read()` before `raise_for_response(resp)`.

### Lazy per-loop `asyncio.Lock` (D-12, Pitfall 2)
**Source:** `iol_client/aio.py:242-256` (`_ensure_client_lock`/`_ensure_token_lock`) backed by `_state.token_lock`/`_state.client_lock`.
**Apply to:** `aio.py` — create locks on first async use, never in `__init__`. Double-check `token_is_fresh` inside the token_lock before authenticating.

### Anonymous request path via `authenticated` flag (D-08/D-09, NET-NEW)
**Source:** no iol analog — extends `RequestSpec` (`_core.py:81-104`) + branches `_request` (`client.py:429-491`, `aio.py:434-512`).
**Apply to:** `RequestSpec.authenticated: bool = True`; health builders set `False`; both `_request` shells gate token injection AND the 401 re-auth carve-out on it (Pitfall 4). Single code path — NO separate `_request_anonymous`.

---

## No Analog Found

No file lacks an analog. Two constructs are **net-new deltas within existing analogs** (not standalone no-analog files):

| Construct | Home file | iol analog | Why new |
|-----------|-----------|-----------|---------|
| `RequestSpec.authenticated` flag + anonymous branch | `_core.py` / `client.py` / `aio.py` | none (iol authenticates every call) | Health endpoints are public (D-08/D-09) |
| Absolute `auth0_token_url` dispatch | `client.py` / `aio.py` `_send_auth_request` | `base_url+path` dispatch (`client.py:346`) | Auth0 token endpoint is a separate host (Pitfall 1) |

Files iol carries that market-data must **NOT create** (deferred / N/A): `_token_cache.py`, `models.py`, `types.py`, and iol's `platformdirs` dep, `refresh_token` machinery, `with_options`/`_is_view`, PEP 562 `__getattr__` shim.

---

## Metadata

**Analog search scope:** `packages/iol-client/src/iol_client/` (all modules), `packages/iol-client/tests/`, `packages/iol-client/pyproject.toml`, `.github/workflows/ci.yml` (logging grep gate).
**Files scanned (read in full or targeted):** `_core.py`, `_state.py`, `_transport.py`, `_atransport.py` (header + import block), `_logging.py`, `exceptions.py`, `__init__.py`, `pyproject.toml`, `client.py` (auth/request/configure/shims sections), `aio.py` (lock/auth/request sections), `tests/conftest.py`, `tests/test_refresh_token_lifecycle.py`, `tests/test_logging.py`, `ci.yml`.
**Pattern extraction date:** 2026-07-29
