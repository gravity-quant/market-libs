# Phase 10: matriz `aio.py` Creation + TokenStore — Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 16 (5 new src + 7 new tests + 4 modified src + 4 modified tests/scripts)
**Analogs found:** 16 / 16 (100% coverage — Phase 10 is "mirror-existing-patterns" by design)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/matriz-client/src/matriz_client/_token_store.py` (NEW) | concurrency primitive | request-response (lazy refresh) | `.claude/skills/spike-findings-market-libs/sources/001c-tokenstore-double-checked-locking/store.py` | exact (spike → prod port) |
| `packages/matriz-client/src/matriz_client/_refresh_policy.py` (NEW) | retry policy decorator | transform (refresh_fn → wrapped refresh_fn) | `.claude/skills/spike-findings-market-libs/sources/003-tokenstore-refresh-policy/policy.py` | exact (spike → prod port) |
| `packages/matriz-client/src/matriz_client/_refresh.py` (NEW) | adapter (httpx → RefreshError) | request-response | `packages/matriz-client/src/matriz_client/_core.py::build_login_request` + `parse_login_response` | role-match (auth flow) |
| `packages/matriz-client/src/matriz_client/_refresh_errors.py` (NEW) | exception hierarchy | n/a | `.claude/skills/spike-findings-market-libs/sources/003-tokenstore-refresh-policy/errors.py` | exact (spike → prod port) |
| `packages/matriz-client/src/matriz_client/_atransport.py` (NEW) | async HTTP transport | request-response (retry) | `packages/iol-client/src/iol_client/_atransport.py` | exact |
| `packages/matriz-client/src/matriz_client/aio.py` (REPLACE stub) | async REST surface | request-response | `packages/iol-client/src/iol_client/aio.py` | exact (full REST mirror) |
| `packages/matriz-client/src/matriz_client/_state.py` (MODIFY +1 field) | state container | n/a (dataclass schema) | `packages/iol-client/src/iol_client/_state.py` (Phase 6 idiom — `token_lock`/state) | role-match |
| `packages/matriz-client/src/matriz_client/client.py` (MODIFY `_ensure_token`) | sync REST surface | state mutation | iol `_ensure_token` doesn't apply (different pattern); use spike's `TokenStore.get_sync()` call shape | role-match |
| `packages/matriz-client/src/matriz_client/ws_client.py` (MODIFY lines 145-147) | ws integration | state mutation (token read) | `.claude/skills/spike-findings-market-libs/references/tokenstore-3way.md#integration-with-ws_clientpy` | exact |
| `main_matriz.py` (EXTEND probes async) | driver probe | request-response | `main_iol.py` (sync+async interleaved) | exact (driver pattern) |
| `packages/matriz-client/tests/test_token_store.py` (NEW) | unit + stress test | n/a | `.claude/skills/spike-findings-market-libs/sources/001c-.../test_store.py` + `sources/002-.../test_stress.py` | exact (spike → prod port) |
| `packages/matriz-client/tests/test_refresh_policy.py` (NEW) | unit test | n/a | `.claude/skills/spike-findings-market-libs/sources/003-.../test_policy.py` | exact (spike → prod port) |
| `packages/matriz-client/tests/test_refresh_errors.py` (NEW, opcional) | unit test | n/a | minimal (3-class hierarchy) — no analog needed | n/a |
| `packages/matriz-client/tests/test_async_client.py` (NEW, or split) | async test | n/a | `packages/iol-client/tests/test_async_client.py` | exact |
| `packages/matriz-client/tests/test_atransport.py` (NEW) | transport test | n/a | `packages/matriz-client/tests/test_transport.py` (sync) + `packages/higyrus-client/tests/test_async_client.py` (folds `AsyncRetryTransport` cases) | role-match |
| `packages/matriz-client/tests/test_token_store_integration.py` (NEW) | integration test | n/a | `.claude/skills/spike-findings-market-libs/sources/003-.../test_integration.py` (3-way under failure) | exact |
| `packages/matriz-client/tests/conftest.py` (EXTEND with `_configure_async`) | test fixture | n/a | `packages/iol-client/tests/conftest.py` lines 41-52 | exact |
| `packages/matriz-client/tests/test_fixture_reaches_production.py` (MODIFY line 64) | guard test | n/a | self (flip skip → active) | n/a (mechanical) |
| `verification/test_async_cancellation.py` (MODIFY line 82) | verification test | n/a | self (flip skip → active) | n/a (mechanical) |
| `verification/test_sync_async_isolation.py` (MODIFY line 176) | verification test | n/a | self (flip skip → active + extend cross-leak for matriz async) | n/a (mechanical) |
| `verification/snapshots/matriz-client-surface.txt` (REGEN) | snapshot artifact | n/a | self (regen — diff IS the deliverable) | n/a |

---

## Pattern Assignments

### `packages/matriz-client/src/matriz_client/_token_store.py` (concurrency primitive, NEW)

**Analog:** `.claude/skills/spike-findings-market-libs/sources/001c-tokenstore-double-checked-locking/store.py`

The spike `store.py` is the **production-ready blueprint** — Phase 10 ports it verbatim (rename `TokenStoreDCL` → `TokenStore`, add `build_token_store(state, *, max_retries)` factory, use the matriz-specific TTL = `23 * 3600`).

**Imports pattern** (lines 1-29 of spike `store.py`, plus matriz-specific composition):

```python
"""TokenStore — 3-way concurrent token store (Spike 001c winner).

Double-Checked Locking pattern (Phase 10 REFAC-04 / market-libs v1.1):

- threading.Lock guards the actual token state (cross-context atomicity).
- asyncio.Lock instances are created lazily per event loop (intra-loop
  thundering-herd prevention).
- Refresh runs in a worker thread via asyncio.to_thread to free the event
  loop during network I/O.

NB: `_async_locks` dict is NOT cleared on event-loop death (D-05 accept-and-document).
Production (1 long-lived loop) leaks 0 bytes. Multi-loop tests leak ~80B per
asyncio.run() invocation. Document in CONCERNS.md.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from matriz_client._refresh import MatrizRefresh
from matriz_client._refresh_policy import RefreshPolicy
```

**Core sync get_sync pattern** (spike store.py lines 60-88, port verbatim):

```python
def _read_state(self) -> tuple[str | None, float, int]:
    with self._state_lock:
        return self._token, self._refreshed_at, self._refresh_count

def _do_refresh_if_needed(self) -> TokenSnapshot:
    """Caller MUST hold state_lock."""
    now = time.monotonic()
    if self._token is None or (now - self._refreshed_at) > self._ttl:
        self._refresh_count += 1
        self._token = self._refresh_fn(self._refresh_count)
        self._refreshed_at = time.monotonic()
    return TokenSnapshot(
        value=self._token,
        refreshed_at=self._refreshed_at,
        refresh_call_id=self._refresh_count,
    )

def get_sync(self) -> TokenSnapshot:
    with self._state_lock:
        return self._do_refresh_if_needed()
```

**Core async get_async pattern** (spike store.py lines 92-141, port verbatim):

```python
def _get_async_lock(self, loop: asyncio.AbstractEventLoop) -> asyncio.Lock:
    key = id(loop)
    lock = self._async_locks.get(key)
    if lock is not None:
        return lock
    with self._state_lock:           # init under threading.Lock — cross-loop safe
        lock = self._async_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._async_locks[key] = lock
    return lock

async def get_async(self) -> TokenSnapshot:
    loop = asyncio.get_running_loop()
    async_lock = self._get_async_lock(loop)
    # Fast path
    token, refreshed_at, _ = self._read_state()
    now = time.monotonic()
    if token is not None and (now - refreshed_at) <= self._ttl:
        return TokenSnapshot(value=token, refreshed_at=refreshed_at,
                             refresh_call_id=self._refresh_count)
    # Slow path
    async with async_lock:
        token, refreshed_at, _ = self._read_state()
        now = time.monotonic()
        if token is not None and (now - refreshed_at) <= self._ttl:
            return TokenSnapshot(value=token, refreshed_at=refreshed_at,
                                 refresh_call_id=self._refresh_count)
        # Offload refresh to worker thread — frees the event loop > 5ms budget
        return await asyncio.to_thread(self._refresh_under_state_lock)
```

**Composition factory** (CONTEXT.md decision D-01 → matches blueprint in `references/tokenstore-3way.md` integration section):

```python
def build_token_store(state: _ClientState, *, max_retries: int) -> TokenStore:
    """Phase 10 — wire RefreshPolicy + MatrizRefresh into TokenStore."""
    adapter = MatrizRefresh(
        http_client=state.http_client,
        base_url=state.base_url,
        username=state.username,
        password=state.password,
    )
    policy = RefreshPolicy(
        max_retries=max_retries,
        base_backoff_s=1.0,
        max_backoff_s=30.0,
        jitter=0.25,
        fail_cache_s=30.0,
    )
    return TokenStore(
        ttl_seconds=23 * 3600,  # matches matriz _TOKEN_TTL = 23h
        refresh_fn=policy.wrap(adapter),
    )
```

**Adaptation notes:**
- Spike uses `time.monotonic()` for elapsed-time comparison — KEEP. Matriz `_state.token_expires_at` uses `time.time()` (wall clock); the two are independent because TokenStore now owns the TTL accounting.
- Rename `TokenStoreDCL` → `TokenStore` per CONTEXT decisions.
- Add `__all__ = ["TokenStore", "TokenSnapshot", "build_token_store"]`.
- Mandatory `from __future__ import annotations` (CONTEXT D-08 idiom).

---

### `packages/matriz-client/src/matriz_client/_refresh_policy.py` (retry policy decorator, NEW)

**Analog:** `.claude/skills/spike-findings-market-libs/sources/003-tokenstore-refresh-policy/policy.py`

Port the spike `RefreshPolicy` class verbatim. Only delta: fix the import path (spike uses `from errors import ...`; production must be `from matriz_client._refresh_errors import ...`).

**Imports pattern** (spike lines 26-38, adjusted):

```python
from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable

from matriz_client._refresh_errors import (
    PermanentRefreshError,
    RateLimitedRefreshError,
    RefreshError,
    TransientRefreshError,
)
```

**Core decorator pattern** (spike lines 115-170, port verbatim):

```python
class RefreshPolicy:
    def __init__(
        self,
        *,
        max_retries: int = 3,
        base_backoff_s: float = 1.0,
        max_backoff_s: float = 30.0,
        jitter: float = 0.25,
        fail_cache_s: float = 30.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        ...
        self._lock = threading.Lock()
        self._cached_failure_at: float | None = None
        self._cached_failure_exc: BaseException | None = None

    def wrap(self, refresh_fn: Callable[[int], str]) -> Callable[[int], str]:
        def wrapped(call_id: int) -> str:
            cached = self._read_fail_cache()
            if cached is not None:
                raise cached       # DOS prevention
            last_exc: BaseException | None = None
            for attempt in range(self.max_retries + 1):
                try:
                    return refresh_fn(call_id)
                except PermanentRefreshError:
                    raise          # NO retry, NO fail-cache
                except RateLimitedRefreshError as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        self._sleep(self._compute_backoff(attempt, exc.retry_after_seconds))
                        continue
                    break
                except TransientRefreshError as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        self._sleep(self._compute_backoff(attempt, None))
                        continue
                    break
            assert last_exc is not None
            self._store_fail_cache(last_exc)
            raise last_exc
        return wrapped
```

**Adaptation notes:**
- The spike uses `from errors import ...` (local sibling); production fixes to `from matriz_client._refresh_errors import ...`.
- Keep `sleep_fn` injection for tests (validated pattern in spike `test_policy.py`).
- Mypy strict: annotate `_cached_failure_exc: BaseException | None` (spike uses bare `BaseException` — that satisfies strict).
- Mandatory `from __future__ import annotations`.

---

### `packages/matriz-client/src/matriz_client/_refresh_errors.py` (exception hierarchy, NEW)

**Analog:** `.claude/skills/spike-findings-market-libs/sources/003-tokenstore-refresh-policy/errors.py`

Port verbatim — 3-class hierarchy, no domain logic to adapt.

**Full file** (spike `errors.py` lines 1-45, port verbatim):

```python
"""Exception classification for the refresh policy (Phase 10 REFAC-04).

Production code maps HTTP status codes / network errors to these in the
MatrizRefresh adapter (_refresh.py). The RefreshPolicy decides retry vs.
propagate based on these classes.
"""

from __future__ import annotations


class RefreshError(Exception):
    """Base class for refresh failures."""


class PermanentRefreshError(RefreshError):
    """Auth-level failure that retrying won't fix (401, 400, 403)."""


class TransientRefreshError(RefreshError):
    """Server/network failure that may succeed on retry (5xx, network timeout)."""


class RateLimitedRefreshError(TransientRefreshError):
    """429 Too Many Requests — retry MUST respect the Retry-After header."""

    def __init__(self, message: str, retry_after_seconds: float) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
```

**Adaptation notes:**
- Add `__all__ = ["RefreshError", "PermanentRefreshError", "TransientRefreshError", "RateLimitedRefreshError"]`.
- Mandatory `from __future__ import annotations`.
- These DO NOT inherit from `MatrizClientError` (existing matriz exception base) — they are an INTERNAL classification used by the policy only. The policy unwraps to known matriz exceptions OR to fresh httpx exceptions at the call site if needed. Confirm with planner.

---

### `packages/matriz-client/src/matriz_client/_refresh.py` (adapter, NEW)

**Analog:** Two combined:
1. `packages/matriz-client/src/matriz_client/_core.py::build_login_request` (lines 311-334) + `parse_login_response` (lines 335-356) — for the matriz endpoint specifics (POST `/auth/getToken`, headers `X-Username`/`X-Password`, token in response header `X-Auth-Token`).
2. `.claude/skills/spike-findings-market-libs/references/refresh-policy.md` MatrizRefresh blueprint (lines 181-228) — for the adapter shape that maps httpx exceptions to RefreshError subclasses.

**Adapter call signature** (from blueprint):

```python
class MatrizRefresh:
    """Pluggable adapter — exercises matriz /auth/getToken endpoint, maps
    httpx exceptions to RefreshError subclasses for the RefreshPolicy.

    The contract is: __call__(call_id: int) -> str. The RefreshPolicy decorates
    this. The TokenStore receives policy.wrap(adapter) as its refresh_fn.
    """

    def __init__(
        self,
        http_client: httpx.Client,
        base_url: str,
        username: str,
        password: str,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url
        self._username = username
        self._password = password

    def __call__(self, call_id: int) -> str:
        try:
            response = self._http_client.post(
                f"{self._base_url}/auth/getToken",
                headers={"X-Username": self._username, "X-Password": self._password},
                timeout=10.0,
            )
        except httpx.TimeoutException as exc:
            raise TransientRefreshError("timeout during /auth/getToken") from exc
        except httpx.NetworkError as exc:
            raise TransientRefreshError(f"network error: {exc}") from exc

        if response.status_code == 401:
            raise PermanentRefreshError("invalid credentials (401)")
        if response.status_code == 403:
            raise PermanentRefreshError("forbidden (403)")
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", "10"))
            raise RateLimitedRefreshError(
                f"rate-limited (429); Retry-After={retry_after}",
                retry_after_seconds=retry_after,
            )
        if 500 <= response.status_code < 600:
            raise TransientRefreshError(
                f"server error {response.status_code}: {response.text[:200]}"
            )
        response.raise_for_status()
        token = response.headers.get("X-Auth-Token")
        if not token:
            raise TransientRefreshError("response missing X-Auth-Token header")
        return token
```

**Adaptation from matriz `_core.build_login_request` / `parse_login_response`**:

```python
# _core.py:311-334 (matriz canonical login pattern):
def build_login_request(state: _ClientState) -> RequestSpec:
    return RequestSpec(
        method="POST",
        path="/auth/getToken",
        headers={"X-Username": state.username, "X-Password": state.password},
        idempotent=True,  # D-03: replay-safe
        endpoint_name="login",
    )

# _core.py:335-356:
def parse_login_response(resp: httpx.Response) -> tuple[str, float]:
    raise_for_response(resp)
    token = resp.headers.get("X-Auth-Token")
    if not token:
        raise AuthenticationError("ERROR", "Login response missing X-Auth-Token header")
    return token, time.time() + _TOKEN_TTL
```

**Adaptation notes:**
- The adapter REUSES the credentials (`state.username`, `state.password`) and base_url path (`/auth/getToken`) from the canonical `_core.build_login_request`/`parse_login_response` pair.
- The adapter does NOT use `RequestSpec` — it calls `httpx.Client.post(...)` directly (the spike pattern). Rationale: the refresh path is OWNED by the TokenStore; it does NOT flow through `Client._request()` / `RetryTransport` because retry semantics are handled by `RefreshPolicy`, NOT by the transport.
- Coordinate with the planner: should the adapter share the `httpx.Client` with `Client._ensure_http_client()`? Recommendation: yes (single connection pool); inject via `state.http_client` (lazy-created by the time TokenStore is built).
- Mandatory `from __future__ import annotations`.

---

### `packages/matriz-client/src/matriz_client/_atransport.py` (async transport, NEW)

**Analog:** `packages/iol-client/src/iol_client/_atransport.py` (132 LOC)

Mechanical mirror — only deltas vs iol: change package logger name from `"iol_client"` → `"matriz_client"` (already established by sync `_transport.py:78`) and import the matriz `_transport` constants.

**Imports pattern** (iol `_atransport.py` lines 16-39 — copy verbatim, swap `iol_client` → `matriz_client`):

```python
"""AsyncRetryTransport — async httpx transport mirror of ``_transport.RetryTransport``.

Phase 10 matriz Plan 10-02. Mirror of the Phase 8 sync RetryTransport (D-25
carve-out closed). Mirrors the sync semantics over ``httpx.AsyncHTTPTransport``
using ``tenacity.AsyncRetrying`` (``async for`` + ``async with``) and
``await asyncio.sleep`` for the Retry-After honor (D-32 — preserves
``asyncio.CancelledError`` propagation, Pitfall 16).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from matriz_client._transport import (
    _LOGGER_NAME,
    _RETRY_AFTER_CAP_S,
    _RETRYABLE_EXC,
    _is_retryable_status,
    _parse_retry_after,
    _RetryableStatus,
)

__all__ = ["AsyncRetryTransport"]
```

**Core class shape** (iol `_atransport.py` lines 43-131 — copy verbatim, MUST also include the matriz-specific `auth_basic` extensions propagation for D-22 log redaction — see sync `_transport.py` lines 162-228):

```python
class AsyncRetryTransport(httpx.AsyncHTTPTransport):
    def __init__(self, *, max_attempts: int = 2, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._max_attempts = max(max_attempts, 1)
        self._logger = logging.getLogger(_LOGGER_NAME)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # D-01 mutation gate.
        if not request.extensions.get("idempotent", False):
            return await super().handle_async_request(request)
        # D-19 bypass.
        if self._max_attempts <= 1:
            return await super().handle_async_request(request)

        request_id = request.extensions.get("request_id", "")
        endpoint_name = request.extensions.get("endpoint_name", "")
        account_id = request.extensions.get("account_id")
        # CR-02 matriz delta: propagate auth_basic for D-22 RedactingFilter.
        auth_basic = request.extensions.get("auth_basic")
        start = time.monotonic()
        attempt_number = 0

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0),
                retry=(
                    retry_if_exception_type(_RETRYABLE_EXC)
                    | retry_if_exception_type(_RetryableStatus)
                ),
                reraise=True,
            ):
                with attempt:
                    attempt_number = attempt.retry_state.attempt_number
                    response = await super().handle_async_request(request)
                    await response.aread()
                    if _is_retryable_status(response):
                        retry_after = response.headers.get("Retry-After")
                        if retry_after is not None:
                            delay = _parse_retry_after(retry_after)
                            if delay is not None and delay > 0:
                                # D-32: asyncio.sleep — CancelledError-aware (Pitfall 16).
                                await asyncio.sleep(min(delay, _RETRY_AFTER_CAP_S))
                        extra: dict[str, Any] = {...}  # D-09 fields
                        if account_id: extra["account_id"] = account_id
                        if auth_basic is not None: extra["auth_basic"] = auth_basic
                        self._logger.warning("retry attempt", extra=extra)
                        raise _RetryableStatus(response)
                    return response
        except _RetryableStatus as exc:
            return exc.response
        except _RETRYABLE_EXC:
            ...  # ERROR log + auth_basic propagation + raise
```

**Adaptation notes:**
- Important matriz delta vs iol: include the `auth_basic` extensions propagation (sync `_transport.py` lines 162-228). iol's `_atransport.py` does NOT have it because iol has no Risk API. Matriz Risk API uses BasicAuth via `RequestSpec.auth_basic` — the WARNING/ERROR log records must split `auth_basic` into `auth_basic_user` (operational) + `auth_basic_password=***` (redacted) per D-22.
- Mandatory `from __future__ import annotations`.
- Import constants from sync `_transport` (intra-package coupling is allowed at module boundary per project constraint — same pattern as iol).

---

### `packages/matriz-client/src/matriz_client/aio.py` (REPLACE stub, async REST surface)

**Analog:** `packages/iol-client/src/iol_client/aio.py` (594 LOC)

This is the LARGEST diff in Phase 10. The iol `aio.py` is the reference for: AsyncClient class shape, lifecycle methods, `_ensure_token` double-checked locking, module-level singleton + delegators, PEP 562 shim back-compat.

**Imports pattern** (iol `aio.py` lines 40-65, adapted):

```python
from __future__ import annotations

import asyncio
import time
import uuid
import warnings
from collections.abc import Sequence
from typing import Any, Self

import httpx

from matriz_client import _atransport, _core
from matriz_client._core import RequestSpec
# B8 D-04: import the shared, stateless helper from _core (NOT from client.py).
from matriz_client._core import raise_for_response as _raise_for_response
from matriz_client._state import _REQUEST_TIMEOUT, _ClientState, _TOKEN_TTL
from matriz_client._token_store import build_token_store
from matriz_client.client import _validate_max_retries  # shared utility
from matriz_client.exceptions import AuthenticationError, PrimaryAPIError
from matriz_client.models import (
    AccountReport, DetailedPosition, Instrument, InstrumentDetail,
    MarketDataSnapshot, NewOrderResponse, Order, Position, Segment, Trade,
)
from matriz_client.types import (
    CFICode, MarketDataEntry, MarketId, OrderType, SegmentId, Side, TimeInForce,
)
from matriz_client.ws_client import DEFAULT_MARKET_DATA_ENTRIES

_ = _raise_for_response  # suppress ruff F401 for re-export alias

__all__ = [
    "AsyncClient", "configure", "login",
    "get_segments", "get_all_instruments", "get_instruments_details",
    "get_instrument_detail", "get_instruments_by_cfi", "get_instruments_by_segment",
    "new_order", "replace_order", "cancel_order",
    "get_order_status", "get_order_history",
    "get_active_orders", "get_filled_orders", "get_all_orders",
    "get_order_by_exec_id",
    "get_market_data", "get_trades",
    "get_positions", "get_detailed_positions", "get_account_report",
    "aclose",
]
```

**AsyncClient `__init__` pattern** (iol `aio.py` lines 87-119):

```python
class AsyncClient:
    __slots__ = ("_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        _validate_max_retries(max_retries)
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if username is not None:
            self._state.username = username
        if password is not None:
            self._state.password = password
        if token is not None:
            self._state.token = token
        if token_expires_at is not None:
            self._state.token_expires_at = token_expires_at
        self._max_retries = max_retries
        if http_client is not None:
            self._state.http_client = http_client
        # token_store: lazy in _aensure_token() (matches _default_client idiom).
```

**Lifecycle pattern** (iol `aio.py` lines 121-163, copy verbatim adapting class name `IOLAsyncClient` → `AsyncClient` + replace `refresh_token` references — matriz has no refresh_token):

```python
async def __aenter__(self) -> Self: return self
async def __aexit__(self, exc_type, exc, tb) -> None: await self.aclose()

async def aclose(self) -> None:
    http_client = self._state.http_client
    if http_client is not None:
        assert isinstance(http_client, httpx.AsyncClient)
        await http_client.aclose()
        self._state.http_client = None

def __repr__(self) -> str:
    return (
        f"AsyncClient(base_url={self._state.base_url!r}, "
        f"username={self._state.username!r}, "
        f"password='***', token='***')"
    )

def __reduce__(self) -> Any:
    raise TypeError("matriz_client.aio.AsyncClient is not picklable...")

def __deepcopy__(self, memo: dict[int, Any]) -> AsyncClient:
    raise TypeError("matriz_client.aio.AsyncClient cannot be deep-copied...")
```

**`_ensure_http_client` async pattern** (iol `aio.py` lines 169-195, swap to `_atransport.AsyncRetryTransport`):

```python
async def _ensure_http_client(self) -> httpx.AsyncClient:
    """Lazily create the AsyncClient with AsyncRetryTransport (Phase 10 D-25 closed)."""
    http_client = self._state.http_client
    if http_client is not None:
        assert isinstance(http_client, httpx.AsyncClient)
        return http_client
    # Note: matriz aio doesn't need a separate _client_lock — TokenStore
    # handles all locking. We just create eagerly if needed (no thundering
    # herd risk since this is called inside _aensure_token which is gated
    # by TokenStore's per-loop asyncio.Lock).
    new_client = httpx.AsyncClient(
        timeout=_REQUEST_TIMEOUT,
        transport=_atransport.AsyncRetryTransport(max_attempts=self._max_retries + 1),
    )
    self._state.http_client = new_client
    return new_client
```

**`_aensure_token` pattern** (NEW shape — uses TokenStore instead of iol's `token_lock` double-check):

```python
async def _aensure_token(self) -> None:
    """Phase 10 — delegate to TokenStore.get_async() (lazy-init the store)."""
    await self._ensure_http_client()  # ensure http_client exists before adapter wires it
    if self._state.token_store is None:
        self._state.token_store = build_token_store(
            self._state, max_retries=self._max_retries
        )
    snap = await self._state.token_store.get_async()
    self._state.token = snap.value     # mirror into state for legacy reads
```

**`_request` pattern** (iol `aio.py` lines 275-350, adapt for matriz auth_basic + 401 re-auth, mirroring sync `client.py:242-337`):

```python
async def _request(self, spec: RequestSpec) -> httpx.Response:
    http = await self._ensure_http_client()
    url = f"{self._state.base_url}{spec.path}"
    request_id = uuid.uuid4().hex

    if spec.auth_basic is not None:
        # Risk API path — D-23: no re-auth (static creds).
        req = http.build_request(spec.method, url, params=spec.params)
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        if spec.account_id is not None: req.extensions["account_id"] = spec.account_id
        req.extensions["auth_basic"] = spec.auth_basic
        resp = await http.send(req, auth=httpx.BasicAuth(*spec.auth_basic))
        if resp.status_code == 401:
            await resp.aread()
            raise AuthenticationError("ERROR", f"401 Unauthorized (Risk API)...")
        return resp

    # Token path — D-02 401 re-auth-once via TokenStore.
    await self._aensure_token()
    assert self._state.token is not None
    headers = {"X-Auth-Token": self._state.token, **(spec.headers or {})}
    req = http.build_request(spec.method, url, params=spec.params, headers=headers)
    req.extensions["idempotent"] = spec.idempotent
    req.extensions["request_id"] = request_id
    req.extensions["endpoint_name"] = spec.endpoint_name
    if spec.account_id is not None: req.extensions["account_id"] = spec.account_id
    resp = await http.send(req)
    if resp.status_code != 401: return resp

    # 401 re-auth-once — force TokenStore refresh (clear token, re-call).
    await resp.aread()
    self._state.token = None
    # Force TokenStore to refresh: clear its cached state via internal contract
    # (TokenStore.invalidate() or recreate). Plan-time decision: simplest is to
    # call build_token_store again to discard the old store, OR add an
    # explicit invalidate() method to TokenStore. Recommendation: add
    # TokenStore.invalidate() — single-line method, clear semantics.
    if self._state.token_store is not None:
        self._state.token_store.invalidate()
    await self._aensure_token()
    new_token = self._state.token
    assert new_token is not None
    req.headers["X-Auth-Token"] = new_token
    resp = await http.send(req)
    if resp.status_code == 401:
        await resp.aread()
        raise AuthenticationError("ERROR", "401 after re-auth...")
    return resp
```

**Endpoint method pattern** (iol `aio.py` lines 356-399 — 3-liner shells that delegate to `_core`):

```python
async def get_segments(self) -> list[Segment]:
    """Async mirror of Client.get_segments()."""
    spec = _core.build_get_segments_request(self._state)
    resp = await self._request(spec)
    return _core.parse_get_segments_response(resp)

async def get_all_instruments(self) -> list[Instrument]:
    spec = _core.build_get_all_instruments_request(self._state)
    resp = await self._request(spec)
    return _core.parse_get_all_instruments_response(resp)

# ... 20 more endpoints following the same shell pattern, mirroring sync
# client.py:340..540 1:1.
```

**Module-level singleton + delegators pattern** (iol `aio.py` lines 407-536):

```python
_default_async_client: AsyncClient | None = None

def _get_default() -> AsyncClient:
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = AsyncClient()
    return _default_async_client

def configure(*, base_url=None, username=None, password=None, token=None,
              token_expires_at=None, max_retries=None,
              http_client=None) -> None:
    """Mirror of matriz_client.configure() — but applies to the async singleton."""
    if max_retries is not None: _validate_max_retries(max_retries)
    client = _get_default()
    if base_url is not None: client._state.base_url = base_url.rstrip("/")
    if username is not None: client._state.username = username
    if password is not None:
        client._state.password = password
        client._state.token = None
        client._state.token_expires_at = 0.0
        client._state.token_store = None   # force TokenStore re-init with new creds
    if token is not None: client._state.token = token
    if token_expires_at is not None: client._state.token_expires_at = token_expires_at
    if max_retries is not None:
        # Same warning-then-drop pattern as iol aio.py lines 466-480.
        client._max_retries = max_retries
        client._state.http_client = None
        client._state.token_store = None   # rebuild store with new policy
    if http_client is not None:
        client._state.http_client = http_client

async def login() -> str: return (await _get_default()._aensure_token() or _get_default()._state.token)
async def aclose() -> None: await _get_default().aclose()
async def get_segments() -> list[Segment]: return await _get_default().get_segments()
# ... 21 more module-level async delegators ...
```

**PEP 562 shim pattern** (iol `aio.py` lines 564-593):

```python
_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_expires_at": "token_expires_at",
    "_base_url": "base_url",
}
_FORWARDED_HTTP_CLIENT = "_client"

def __getattr__(name: str) -> Any:
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**Adaptation notes:**
- Matriz has NO `refresh_token` and NO `token_lock` — strip those from iol pattern.
- 22 endpoints — see CONTEXT.md line 22-28 for the exact list. Each is a 3-liner shell: build spec → await `_request` → parse response.
- `_aensure_token` is the BIG semantic change vs iol — delegates to TokenStore instead of doing `token_lock` double-check inline.
- Mutation gate: `new_order`/`cancel_order`/`replace_order` builders MUST keep `idempotent=False` per `_core` builders (Phase 8 D-15 / D-24 carry-forward). AsyncRetryTransport reads `req.extensions["idempotent"]` from same protocol.
- B8 lock-in: import `raise_for_response` from `_core`, NEVER from `client.py`.

---

### `packages/matriz-client/src/matriz_client/_state.py` (MODIFY +1 field)

**Analog:** `packages/iol-client/src/iol_client/_state.py` (Phase 6 — `token_lock`/state pattern)

**Existing state schema** (matriz `_state.py:45-55`):

```python
@dataclass(slots=True)
class _ClientState:
    base_url: str = field(default_factory=_default_base_url)
    username: str = field(default_factory=_default_username)
    password: str = field(default_factory=_default_password)
    token: str | None = None
    token_expires_at: float = 0.0
    http_client: httpx.Client | httpx.AsyncClient | None = None
    account_id: str | None = None  # ORP-01 (NOT touched in Phase 10)
```

**Modification pattern** (single +1 field, mirror Phase 6 iol idiom):

```python
# Add at line ~26 (top of file):
from matriz_client._token_store import TokenStore

# Add to dataclass after line 55:
    token_store: TokenStore | None = None  # Phase 10 REFAC-04: lazy-init.
```

**Adaptation notes:**
- DO NOT touch `account_id` field — that is ORP-01 / Phase 11 CR-08 scope per CONTEXT decisions.
- DO NOT rename or reorder any existing field — `slots=True` makes the layout invariant.
- Forward-reference issue: `TokenStore` is defined in `_token_store.py` which imports... nothing from `_state.py` directly (only through `build_token_store(state, *, max_retries)` which is called LAZY). No circular import.
- Mypy strict: `TokenStore | None = None` is fine.

---

### `packages/matriz-client/src/matriz_client/client.py` (MODIFY `_ensure_token` + `_get_default`)

**Analog:** Existing matriz `client.py:232-235` (current `_ensure_token`) for the BEFORE state; CONTEXT.md D-07 + `references/tokenstore-3way.md` integration section lines 158-165 for the AFTER state.

**Current pattern** (matriz `client.py:232-235`):

```python
def _ensure_token(self) -> None:
    if _core.token_is_fresh(self._state):
        return
    self.login()
```

**Phase 10 pattern** (replace body to delegate to TokenStore):

```python
def _ensure_token(self) -> None:
    """Phase 10 — delegate to TokenStore.get_sync().

    Replaces the Phase 6 inline ``token_is_fresh`` check + ``self.login()``
    call with a single TokenStore call. The store handles refresh policy
    (retry/backoff/fail-cache) and atomicity vs ws_client daemon thread +
    async REST surface.
    """
    self._ensure_http_client()  # adapter needs http_client
    if self._state.token_store is None:
        self._state.token_store = build_token_store(
            self._state, max_retries=self._max_retries
        )
    snap = self._state.token_store.get_sync()
    self._state.token = snap.value
    # token_expires_at is no longer the source of truth — TokenStore owns it.
    # We mirror to state for back-compat reads (PEP 562 shim, ws_client legacy).
```

**Import addition** (top of `client.py`):

```python
from matriz_client._token_store import build_token_store
```

**Adaptation notes:**
- KEEP `Client.login()` as-is (lines 207-230) — it still works as an eager-login entry point and is exposed in the public API via `_get_default().login()`.
- The semantic shift: `login()` now writes directly to state via the old path (idempotent — TokenStore will see fresh token on next `get_sync()` because `_do_refresh_if_needed()` checks TTL).
- Alternative: route `login()` THROUGH `get_sync()` for unified path. Recommendation to planner: keep separate for back-compat (existing tests assert `Client.login()` returns the token directly).

---

### `packages/matriz-client/src/matriz_client/ws_client.py` (MODIFY lines 145-147)

**Analog:** `.claude/skills/spike-findings-market-libs/references/tokenstore-3way.md` lines 149-155 (integration with ws_client.py)

**Current pattern** (matriz `ws_client.py:145-147`):

```python
default = _rest._get_default()
default._ensure_token()
assert default._state.token is not None
```

**Phase 10 pattern**:

```python
default = _rest._get_default()
# Phase 10: read token via TokenStore (3-way safe — same TokenStore used by
# sync REST callers from main thread AND by async REST callers from event
# loops). ws_client daemon thread calls get_sync() directly.
if default._state.token_store is None:
    default._ensure_token()    # lazy-init the store via sync path
snap = default._state.token_store.get_sync()
default._state.token = snap.value  # mirror for back-compat reads (line 157)
assert default._state.token is not None
```

**Adaptation notes:**
- The `_state.token = snap.value` mirror preserves line 157's read (`header={"X-Auth-Token": default._state.token}`).
- Alternative simpler form (CONTEXT specifics line 996-998):
  ```python
  default = _rest._get_default()
  default._state.token = default._state.token_store.get_sync()  # if get_sync returns str
  ```
  BUT — the spike's TokenStore returns `TokenSnapshot`, not `str`. Either:
  - Change spec: `get_sync() -> str` (drop the snapshot wrapper)
  - Use `.value` attribute access (as shown above)
- DO NOT refactor the daemon thread lifecycle — only swap lines 145-147.
- Preserve line 157 (`header={"X-Auth-Token": default._state.token}`) — back-compat path.

---

### `main_matriz.py` (EXTEND with probes async paired)

**Analog:** `main_iol.py` (1666 LOC — uses interleaved sync+async probes with the same `main()`)

**Pattern** (per CONTEXT D-06):

For each existing matriz probe (e.g., `probe_get_segments_sync()`), add a paired `probe_get_segments_async()` that mirrors signature and outcome reporting. Both run in `main()` interleaved (sync, then async equivalent). Probes that depend on `ws_client` SKIP async with documented reason.

**Outcome reporter pattern** (from `main_iol.py`):

```python
def probe_get_segments_sync() -> ProbeResult:
    try:
        segments = matriz_client.get_segments()
        return PASS("get_segments returned %d segments" % len(segments))
    except Exception as e:
        return FINDING(f"get_segments failed: {e}")

async def probe_get_segments_async() -> ProbeResult:
    try:
        segments = await matriz_client.aio.get_segments()
        return PASS("aio.get_segments returned %d segments" % len(segments))
    except Exception as e:
        return FINDING(f"aio.get_segments failed: {e}")

# main() runs both, side-by-side:
def main():
    ...
    report.append(probe_get_segments_sync())
    report.append(asyncio.run(probe_get_segments_async()))
    ...
```

**Adaptation notes:**
- LIVE-02 outcome = "the async run reproduces the same PASS/FINDING/SKIPPED set as the sync".
- 22 sync probes (estimated) → 22 async pairs (some may skip).
- Probe-async naming convention: `probe_X_async()` per CONTEXT Claude's-Discretion recommendation.

---

### `packages/matriz-client/tests/test_token_store.py` (NEW)

**Analog:** Two combined:
1. `.claude/skills/spike-findings-market-libs/sources/001c-tokenstore-double-checked-locking/test_store.py` (7 scenarios — single caller, thundering herd, 3-way, multiple loops)
2. `.claude/skills/spike-findings-market-libs/sources/002-tokenstore-3way-integration-stress/test_stress.py` (205-caller stress; trim to ~50+50+5 for CI speed)

**Test scaffolding pattern** (spike test_store.py — adapt):

```python
"""Unit + stress tests for matriz_client._token_store.TokenStore."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from matriz_client._token_store import TokenStore, TokenSnapshot


def test_single_caller_refresh_once() -> None:
    """Single sync caller triggers exactly 1 refresh."""
    count = 0
    def refresh(cid: int) -> str:
        nonlocal count
        count += 1
        return f"TOKEN-{count}"
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)
    snap = store.get_sync()
    assert snap.value == "TOKEN-1"
    assert count == 1
    # Second call within TTL — no refresh.
    snap2 = store.get_sync()
    assert snap2.value == "TOKEN-1"
    assert count == 1


def test_thundering_herd_sync() -> None:
    """N sync threads concurrent → exactly 1 refresh."""
    ...

@pytest.mark.asyncio
async def test_thundering_herd_async() -> None:
    """N async coroutines concurrent → exactly 1 refresh."""
    ...

@pytest.mark.asyncio
async def test_3way_concurrent_sync_async_daemon() -> None:
    """50 sync + 50 async + 5 daemon threads → exactly 1 refresh, 0 errors."""
    ...

@pytest.mark.asyncio
async def test_event_loop_not_blocked_during_refresh() -> None:
    """asyncio.to_thread frees the loop > 5ms budget during 100ms refresh."""
    ...
```

**Adaptation notes:**
- Spike count target: 7 (from 001c) + 1 stress (trimmed from 002) ≈ 8 unit tests.
- CONTEXT.md "Tests-count delta target" line 1008: +20 tests for Plan 10-01 (TokenStore + RefreshPolicy).
- Use pytest-asyncio markers per existing matriz conftest pattern (`asyncio_mode = "auto"` in root `pyproject.toml`).

---

### `packages/matriz-client/tests/test_refresh_policy.py` (NEW)

**Analog:** `.claude/skills/spike-findings-market-libs/sources/003-tokenstore-refresh-policy/test_policy.py`

Port the spike tests; adapt import path.

**Test scaffolding pattern** (CONTEXT.md line 102-106 — 4 test scenarios):

```python
def test_classification_permanent_propagates_immediately() -> None:
    """PermanentRefreshError raised → no retry, no fail-cache."""
    ...

def test_classification_transient_retries_with_backoff() -> None:
    """TransientRefreshError → retry with exp backoff."""
    ...

def test_rate_limited_honors_retry_after() -> None:
    """RateLimitedRefreshError uses retry_after_seconds for next sleep."""
    ...

def test_fail_cache_after_exhausted_retries() -> None:
    """N concurrent callers post-failure → 0 new refresh_fn invocations."""
    ...

def test_permanent_error_not_fail_cached() -> None:
    """Verify caching does NOT happen for PermanentRefreshError (DOS-prevent design)."""
    ...
```

**Adaptation notes:**
- Inject `sleep_fn=lambda s: None` for instant tests (spike pattern).
- Use `time.monotonic` mocking via `freezegun` or direct injection if needed.

---

### `packages/matriz-client/tests/test_async_client.py` (NEW — or split per concern)

**Analog:** `packages/iol-client/tests/test_async_client.py`

**Imports pattern** (iol test_async_client.py lines 1-11):

```python
from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from matriz_client import AuthenticationError, aio
```

**Test signature pattern** (iol test_async_client.py — copy idiom):

```python
async def test_async_login_obtiene_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "tok-matriz"},
    )
    assert await aio.login() == "tok-matriz"


async def test_async_get_segments(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": [{"marketSegmentId": "DDF", "marketId": "ROFX"}]},
    )
    segments = await aio.get_segments()
    assert segments[0].marketSegmentId == "DDF"


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    """Phase 8 D-02 async mirror: 401 → re-auth-once → 401 still raises AuthenticationError."""
    ...
```

**Adaptation notes:**
- CONTEXT.md Claude's-Discretion recommends 3 files per concern: `test_async_auth.py`, `test_async_queries.py`, `test_async_mutations.py` — affinity with sync test structure.
- Mutations must use `idempotent=False` mock pattern from sync `test_transport.py` for new_order/cancel_order/replace_order.
- Tests target: +30 (CONTEXT line 1009).

---

### `packages/matriz-client/tests/test_atransport.py` (NEW)

**Analog:** Two combined:
1. `packages/matriz-client/tests/test_transport.py` (sync RetryTransport tests) — for the scenario list (retry on 5xx, mutation gate, Retry-After honor, etc.)
2. `packages/higyrus-client/tests/test_async_client.py` (the ONLY existing test file across all packages that exercises `AsyncRetryTransport`) — for the async-specific assertions

**Adaptation notes:**
- CONTEXT.md mentions `test_atransport.py` as a possible NEW file (line 648). Recommended scope: D-32 CancelledError propagation, async Retry-After via `asyncio.sleep`, mutation gate pass-through, `_RetryableStatus` sentinel sync vs async parity.
- 5-7 tests likely sufficient (mirror the sync `test_transport.py` cases that exercise transport-level concerns).

---

### `packages/matriz-client/tests/test_token_store_integration.py` (NEW)

**Analog:** `.claude/skills/spike-findings-market-libs/sources/003-tokenstore-refresh-policy/test_integration.py` (3-way scenarios)

**Cross-thread regression test** (CONTEXT.md lines 939-983 — the canonical case):

```python
"""Cross-thread refresh regression for the matriz Phase 10 TokenStore.

Validates that a sync caller holding the refresh-lock for 100ms blocks an
async caller from issuing a redundant refresh — both see the SAME token.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from matriz_client._token_store import TokenStore


@pytest.mark.asyncio
async def test_async_caller_waits_for_concurrent_sync_refresh() -> None:
    refresh_count = 0
    def refresh_fn(cid: int) -> str:
        nonlocal refresh_count
        time.sleep(0.1)  # simulate 100ms network call
        refresh_count += 1
        return f"TOKEN-{refresh_count}"

    store = TokenStore(ttl_seconds=10, refresh_fn=refresh_fn)
    sync_token_holder: list[str] = []
    def sync_caller() -> None:
        sync_token_holder.append(store.get_sync().value)

    t = threading.Thread(target=sync_caller, daemon=True)
    t.start()
    await asyncio.sleep(0.01)         # ensure sync has the lock
    async_snap = await store.get_async()
    t.join()
    assert async_snap.value == sync_token_holder[0] == "TOKEN-1"
    assert refresh_count == 1
```

**Adaptation notes:**
- CONTEXT.md target: +5 tests for Plan 10-03 (cross-thread + ws_client wiring).
- Add `test_ws_client_token_integration.py` (mocked WS) as a sibling — verify ws_client.py reads from `state.token_store.get_sync()` correctly.

---

### `packages/matriz-client/tests/conftest.py` (EXTEND with `_configure_async`)

**Analog:** `packages/iol-client/tests/conftest.py` lines 41-52

**Extension pattern** (copy lines 41-52 of iol conftest, adapt module names):

```python
from collections.abc import AsyncIterator, Iterator

import pytest
import matriz_client
from matriz_client import aio


@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    yield
    matriz_client.client._get_default().close()
    matriz_client.configure(base_url="https://api.test", username="", password="")


@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    aio.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    yield
    await aio._get_default().aclose()
    aio.configure(base_url="https://api.test", username="", password="")
```

**Adaptation notes:**
- Current matriz conftest only has `_configure_sync` (lines 19-41). Add the autouse `_configure_async` mirror.
- The autouse pair is the EXACT same idiom as iol — both fixtures run for every test (the sync one is a no-op for pure async tests, and vice versa).
- Need `AsyncIterator` import — adjust the existing import block at line 12.

---

### `packages/matriz-client/tests/test_fixture_reaches_production.py` (MODIFY line 64)

**Analog:** Self — line 64 is a permanent `pytest.skip` waiting on Phase 10. Flip the skip:

**BEFORE** (line 64):
```python
pytest.skip(
    "matriz async REST surface is Phase 10 REFAC-04; "
    ...
)
```

**AFTER** (mechanical flip):
- Remove the `pytest.skip(...)` call.
- The body of the test (lines 56-63) should now exercise the real async surface (mirror sync guard at the top of the same file).

---

### `verification/test_async_cancellation.py` (MODIFY line 82)

**Analog:** Self — flip skip line 82.

**BEFORE**:
```python
pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore")
```

**AFTER**: remove the skip; verify the test body actually exercises matriz async with `asyncio.CancelledError` (mirror iol's analogue earlier in the file).

---

### `verification/test_sync_async_isolation.py` (MODIFY line 176)

**Analog:** Self + iol async cross-leak sentinel pattern earlier in the same file.

**BEFORE** (line 176):
```python
pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore")
```

**AFTER**: remove the skip; extend the matriz-specific cross-leak sentinel to cover the async path (mirror the iol/higyrus/ámbito sentinels already in the file).

---

### `verification/snapshots/matriz-client-surface.txt` (REGEN)

**Pattern:** Mechanical regeneration via the existing snapshot tool (`make snapshot` or `uv run python verification/snapshot.py matriz_client`).

**Expected diff** (CONTEXT.md "Specifics" snapshot diff section):
- +1 class line: `AsyncClient`
- +22 module-level `async def` delegators
- Possibly +3 helper internals (lazy `_get_default`, `aclose`, etc.)
- Total: ~23-25 new lines.
- Plan 10-04 VALIDATION.md must inline-document the diff.

---

## Shared Patterns

### From `__future__` import annotations (mandatory in all new files)

**Source:** Project convention (CLAUDE.md "Every module starts with `from __future__ import annotations`")
**Apply to:** ALL 5 new src files + 5 new test files.

```python
from __future__ import annotations
```

---

### B8 lock-in: import `raise_for_response` from `_core`, NEVER from `client.py`

**Source:** `packages/iol-client/src/iol_client/aio.py:57` (canonical pattern, Phase 7 D-04)
**Apply to:** `packages/matriz-client/src/matriz_client/aio.py`

```python
from matriz_client._core import raise_for_response as _raise_for_response
# ...
_ = _raise_for_response  # suppress ruff F401
```

**Rationale:** preserves invariant `aio._raise_for_response is client._raise_for_response` so monkeypatch in tests works across both surfaces (both alias the same `_core.raise_for_response` function).

---

### Mutation gate: `idempotent=False` for `new_order`/`cancel_order`/`replace_order`

**Source:** `packages/matriz-client/src/matriz_client/_core.py` (existing builders set `idempotent=False` per Phase 8 D-15/D-24)
**Apply to:** `packages/matriz-client/src/matriz_client/_atransport.py` (mutation gate check at top of `handle_async_request`) + `packages/matriz-client/src/matriz_client/aio.py` (passes `spec.idempotent` to `req.extensions["idempotent"]`)

```python
# In AsyncRetryTransport.handle_async_request:
if not request.extensions.get("idempotent", False):
    return await super().handle_async_request(request)  # no retry
```

**Rationale:** matriz `new_order`/`cancel_order`/`replace_order` are HTTP GET (Primary API quirk) but MUST NOT retry on 503 — duplicate-order risk (Pitfall 4).

---

### RedactingFilter auto-coverage (LOG-02 — no regex change in Phase 10)

**Source:** `packages/matriz-client/src/matriz_client/_logging.py` (RedactingFilter attached to `matriz_client` logger in `__init__.py:22-25`)
**Apply to:** `_atransport.py`, `_refresh.py`, `aio.py` (all use `logging.getLogger("matriz_client")` directly OR transitively)

**Rationale:** the regex patterns (Bearer, X-Auth-Token, X-Username/X-Password, Authorization Basic, D-22 `auth_basic` tuple split) cover all NEW async log records automatically — NO update needed because new code uses the same logger name.

---

### `assert state.token is not None` after `_ensure_token`/`_aensure_token` (mypy strict narrowing)

**Source:** `packages/iol-client/src/iol_client/aio.py:291` + `packages/matriz-client/src/matriz_client/client.py:302-303`
**Apply to:** `packages/matriz-client/src/matriz_client/aio.py::_request`

```python
await self._aensure_token()
assert self._state.token is not None
headers = {"X-Auth-Token": self._state.token, **(spec.headers or {})}
```

**Rationale:** `_state.token: str | None` — without the assert, mypy strict refuses the `dict[str, str]` headers construction.

---

### `_state` per-instance (NO cross-instance state sharing)

**Source:** `packages/iol-client/src/iol_client/aio.py:102` (`self._state = _ClientState()`) — Phase 6 D-IOL-09 idiom
**Apply to:** `packages/matriz-client/src/matriz_client/aio.py::AsyncClient.__init__`

```python
self._state = _ClientState()  # new instance — NOT shared with sync Client
```

**Rationale:** the cross-leak sentinel test (`verification/test_sync_async_isolation.py`) asserts that sync and async surfaces NEVER share token cache.

---

## No Analog Found

None — every Phase 10 file has an analog (spike sources, iol patterns, or self for mechanical flips).

---

## Metadata

**Analog search scope:**
- `packages/iol-client/src/iol_client/` (canonical async pattern reference)
- `packages/iol-client/tests/` (test patterns)
- `packages/matriz-client/src/matriz_client/` (existing sync — for modify locations)
- `packages/matriz-client/tests/` (existing test conftest)
- `packages/higyrus-client/tests/` (one cross-reference for `AsyncRetryTransport` test scope)
- `.claude/skills/spike-findings-market-libs/sources/001c-...`, `002-...`, `003-...` (production-ready blueprints)
- `verification/` (skip-flip locations)

**Files scanned (read):** 11
- `packages/iol-client/src/iol_client/aio.py` (594 LOC)
- `packages/iol-client/src/iol_client/_atransport.py` (132 LOC)
- `packages/iol-client/tests/conftest.py` (53 LOC)
- `packages/iol-client/tests/test_async_client.py` (first 100 LOC)
- `packages/matriz-client/src/matriz_client/_transport.py` (240 LOC)
- `packages/matriz-client/src/matriz_client/aio.py` (104 LOC current stub)
- `packages/matriz-client/src/matriz_client/_state.py` (56 LOC)
- `packages/matriz-client/src/matriz_client/client.py` (key sections)
- `packages/matriz-client/src/matriz_client/ws_client.py` (lines 130-180)
- `packages/matriz-client/tests/conftest.py` (42 LOC)
- `.claude/skills/spike-findings-market-libs/sources/001c-.../store.py` (153 LOC)
- `.claude/skills/spike-findings-market-libs/sources/003-.../policy.py` (180 LOC) + `errors.py` (45 LOC)

**Pattern extraction date:** 2026-06-13
