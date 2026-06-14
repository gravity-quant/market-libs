# Phase 8: Retries, Backoff, Structured Logging - Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 36 (29 source + 6 new guard tests + 1 CI config) across 4 packages
**Analogs found:** 32 with strong matches / 36 (4 brand-new modules without exact analogs use research SUMMARY shape)

## Scope summary

Phase 8 lands a fixed pattern (4 paquetes × 3 nuevos archivos + 4 modificados) plus 6 cross-cutting guard tests. Per-package serial order (ámbito → iol → higyrus → matriz) keeps slicing identical to Phase 6 D-05 / Phase 7 D-13. matriz ships sync-only (no `_atransport.py` per D-25); ámbito has no auth so it skips the 401 re-auth branch (still gets RetryTransport + RedactingFilter).

The 4 brand-new private modules per package (`_transport.py`, `_atransport.py`, `_logging.py`) have **no existing codebase analog** — the closest references are:
- the `_state.py` / `_core.py` shape (private module convention, `from __future__ import annotations`, `__all__` list, docstring style)
- the research SUMMARY §"Architecture Patterns" Pattern 1/4 (which embeds the canonical RetryTransport + RedactingFilter code Phase 8 must replicate)

Everything that touches `client.py` / `aio.py` / `_core.py` / `__init__.py` / `pyproject.toml` / `verification/*` has an **exact existing analog** in Phase 6/7 deliveries — those are the load-bearing references to copy verbatim.

## File Classification

### Per-package source (4× replicado, matriz = sync only)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py` | new module / sync transport | sync transport subclass + retry loop | RESEARCH.md §Pattern 1 (canonical excerpt) + `packages/ambito-financiero-client/src/ambito_financiero_client/_state.py` (private module shape) | partial — no existing httpx transport subclass anywhere in the repo |
| `packages/iol-client/src/iol_client/_transport.py` | new module / sync transport | sync transport subclass + retry loop | mismo + `packages/iol-client/src/iol_client/_state.py` shape | partial |
| `packages/higyrus-client/src/higyrus_client/_transport.py` | new module / sync transport | sync transport subclass + retry loop | mismo + `packages/higyrus-client/src/higyrus_client/_state.py` shape | partial |
| `packages/matriz-client/src/matriz_client/_transport.py` | new module / sync transport | sync transport subclass + retry loop + matriz-specific status==ERROR no-retry guard | mismo + `packages/matriz-client/src/matriz_client/_state.py` shape | partial |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py` | new module / async transport | async transport subclass + tenacity AsyncRetrying | RESEARCH.md §Pattern 1 (async variant) — D-32 `asyncio.sleep` | partial |
| `packages/iol-client/src/iol_client/_atransport.py` | new module / async transport | async transport subclass | mismo | partial |
| `packages/higyrus-client/src/higyrus_client/_atransport.py` | new module / async transport | async transport subclass | mismo | partial |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_logging.py` | new module / observability | logging.Filter + attach() factory | RESEARCH.md §Pattern 4 (canonical excerpt) | partial — `verification/redaction.py` exists but is a print-redaction utility NOT a `logging.Filter`; D-10 forbids importing from `verification/` |
| `packages/iol-client/src/iol_client/_logging.py` | new module / observability | logging.Filter + attach() factory + IOL refresh_token patterns | mismo + IOL OAuth `refresh_token` regex | partial |
| `packages/higyrus-client/src/higyrus_client/_logging.py` | new module / observability | logging.Filter + attach() factory + Higyrus JSON password + cuit URL scrub | mismo + Higyrus JSON `"password":"..."` regex + cuit query param redaction | partial |
| `packages/matriz-client/src/matriz_client/_logging.py` | new module / observability | logging.Filter + attach() factory + matriz auth_basic Basic header redaction (D-22) | mismo + `Authorization: Basic` regex + auth_basic tuple splitter | partial |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` | extend | add `endpoint_name: str` to RequestSpec, flip `idempotent=True` (forward-declared via D-13 P7) on GETs | `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` (self) | exact |
| `packages/iol-client/src/iol_client/_core.py` | extend | RequestSpec + endpoint_name + flip idempotent=True (GET builders + login/refresh per D-03) | `packages/iol-client/src/iol_client/_core.py` (self) | exact |
| `packages/higyrus-client/src/higyrus_client/_core.py` | extend | RequestSpec + endpoint_name + `account_id: str \| None = None` (D-11) + flip idempotent=True | `packages/higyrus-client/src/higyrus_client/_core.py` (self) | exact |
| `packages/matriz-client/src/matriz_client/_core.py` | extend | RequestSpec + endpoint_name + `account_id: str \| None = None` (D-11) + flip idempotent=True (GET) + login. POST orders mantienen idempotent=False (D-24) | `packages/matriz-client/src/matriz_client/_core.py` (self) | exact |
| `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` | extend | shell `_request()` adds `request_id` gen + `extensions["idempotent"/"request_id"/"endpoint_name"]`; `Client.__init__` + `configure()` + 2 new kwargs; `_ensure_http_client` instala RetryTransport | `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (self) | exact — no 401 re-auth branch (ámbito no auth) |
| `packages/iol-client/src/iol_client/client.py` | extend | shell `_request()` + 2 kwargs + 401 re-auth-once with `_ensure_token()` (D-02). Login flow ya pasa por `_ensure_http_client()` con RetryTransport (D-29). | `packages/iol-client/src/iol_client/client.py` (self) | exact |
| `packages/higyrus-client/src/higyrus_client/client.py` | extend | shell `_request()` + 2 kwargs + 401 re-auth + `account_id` propagation via spec.account_id | `packages/higyrus-client/src/higyrus_client/client.py` (self) | exact |
| `packages/matriz-client/src/matriz_client/client.py` | extend | shell `_request()` + 2 kwargs + 401 re-auth (skip si `spec.auth_basic` per D-23) + `account_id` propagation | `packages/matriz-client/src/matriz_client/client.py` (self) | exact |
| `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` | extend | mirror sync; AsyncRetryTransport via `_atransport.py` | `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` (self) | exact |
| `packages/iol-client/src/iol_client/aio.py` | extend | mirror sync; double-checked locking ya existente intacto; 401 re-auth integrado en `_request` async | `packages/iol-client/src/iol_client/aio.py` (self) | exact |
| `packages/higyrus-client/src/higyrus_client/aio.py` | extend | mirror sync | `packages/higyrus-client/src/higyrus_client/aio.py` (self) | exact |
| `packages/matriz-client/src/matriz_client/aio.py` | NOT TOUCHED — Phase 10 territory per D-25 | N/A | N/A | N/A — explicitly forward-deferred |
| `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py` | extend | add `from ambito_financiero_client import _logging; _logging.attach(); del _logging` | `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py` (self) | exact |
| `packages/iol-client/src/iol_client/__init__.py` | extend | mismo | `packages/iol-client/src/iol_client/__init__.py` (self) | exact |
| `packages/higyrus-client/src/higyrus_client/__init__.py` | extend | mismo | `packages/higyrus-client/src/higyrus_client/__init__.py` (self) | exact |
| `packages/matriz-client/src/matriz_client/__init__.py` | extend | mismo | `packages/matriz-client/src/matriz_client/__init__.py` (self) | exact |
| `packages/<pkg>/pyproject.toml` (×4) | extend | add `tenacity>=9.1.0,<10` a `[project] dependencies` | `packages/ambito-financiero-client/pyproject.toml` (canónico shape) | exact |

### Cross-cutting verification/ + snapshots + config

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `verification/test_retry_mutation_gate.py` | new test | parametrize × 4 paquetes; mock 503 POST → assert 1 wire request; mock 503 GET → assert N attempts | `verification/test_sync_async_isolation.py` (parametrize × 4 paquetes + pytest-httpx idiom) | exact |
| `verification/test_retry_401_reauth.py` | new test | parametrize × auth paquetes; mock 401→200 → 2 wire requests refreshed header; 401→401 → AuthError | `verification/test_sync_async_isolation.py` parametrize pattern + `iol_client/tests/conftest.py` configure(token=...) pattern | exact |
| `verification/test_logging_root_unchanged.py` | new test | record `logging.root.handlers` before/after import; assert unchanged | none — unique cross-cutting; use plain pytest function (no parametrize) | partial — no direct analog, planner uses `verification/test_public_surface.py` shape (module import + state check) |
| `verification/test_logging_no_token_leak.py` | new test | caplog × 4 paquetes; configure(token="SECRET-LITERAL-12345"); assert NO record contains literal | `verification/test_sync_async_isolation.py` + pytest `caplog` fixture | role-match |
| `verification/test_retry_after_cap.py` | new test | mock 429 `Retry-After: 600` → assert delay ≤ 60s + retry happens | `verification/test_sync_async_isolation.py` (pytest-httpx pattern) | role-match |
| `verification/test_async_cancellation.py` | new test | parametrize × async paquetes; matriz skip; `asyncio.wait_for(client.get_X(), timeout=0.5)` cuando 503→503 → TimeoutError | `verification/test_sync_async_isolation.py` test_async_token_isolation_in_wire_request (async parametrize + matriz skip pattern) | exact |
| `verification/snapshots/<pkg>-surface.txt` (×4) | extend | add 2 new kwargs (`max_retries`, `http_client`) to Client/AsyncClient/configure() signatures | `verification/snapshots/ambito-financiero-client-surface.txt` (canónico format) | exact |
| `pyproject.toml` root | extend (optional D-27) | maybe add ruff `LOG` ruleset; import-linter contracts unchanged | `pyproject.toml` root (self) | exact |
| `.github/workflows/ci.yml` | extend (D-27 alt-b) | add `lint-logging` step: `! grep -rn 'logging\.basicConfig\|logging\.root' packages/*/src/` | `.github/workflows/ci.yml` (self) lint job | exact |

---

## Pattern Assignments

### `packages/<pkg>/src/<pkg>/_transport.py` (new module, sync transport)

**Primary analog:** RESEARCH.md §"Architecture Patterns" Pattern 1 lines 348-504 (the canonical `RetryTransport(httpx.HTTPTransport)` excerpt, ambito canary). Phase 8 must duplicate verbatim per paquete with package-specific imports (logger name, RedactingFilter).

**Secondary analog (project convention shell):** `packages/ambito-financiero-client/src/ambito_financiero_client/_state.py` lines 1-65 (private module convention — leading underscore filename, `from __future__ import annotations`, module-level `__all__`, docstring describing purpose + cross-pkg consistency note).

**Imports / module-prelude pattern** (sourced from `_state.py:27-32` + research Pattern 1):
```python
"""RetryTransport subclass — sync. RELY-01..04 + Phase 8 D-01/D-07/D-08.

Mutation gate vía request.extensions["idempotent"] (set por shell _request()).
Backoff full-jitter (base=1s, max=30s, exp=2) — tenacity wait_exponential_jitter.
Retry-After cap 60s (RFC 9110 §10.2.3 delta-seconds; HTTP-date logged WARNING).
"""

from __future__ import annotations

import logging
import time
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)
```

**Retryable set (locked LOCK per D-07)** — copy verbatim across the 4 paquetes:
```python
_RETRYABLE_EXC = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
)
_RETRYABLE_STATUS = frozenset({408, 409, 429, *range(500, 600)})
_RETRY_AFTER_CAP_S = 60.0


class _RetryableStatus(Exception):
    """Internal sentinel — NOT a subclass of <Pkg>APIError (D-07 invariant)."""
    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"retryable status: {response.status_code}")
        self.response = response
```

**Core handle_request loop** — research Pattern 1 lines 414-503 (the canonical excerpt). The planner copies into each package with only the logger name + `extra["package"]` value changing. Critical invariants:
- Mutation gate at top: `if not request.extensions.get("idempotent", False): return super().handle_request(request)` — pass-through.
- `max_attempts <= 1` short-circuit: `return super().handle_request(request)` (D-19 `max_retries=0`).
- `response.read()` BEFORE status check (Phase 7 D-06 alignment — body-consume-then-raise inside transport too).
- `Retry-After` cap 60s BEFORE re-raising sentinel.
- WARNING log per attempt with structured fields (D-09: package, method, url, status_code, attempt, request_id, endpoint_name, retry_reason, optional account_id).
- ERROR log on terminal failure (D-12).

**Differences from analog (research excerpt is the analog):**
- Per paquete: `logger = logging.getLogger("<pkg>")` (4 distinct loggers per D-13).
- Per paquete: `extra["package"] = "<pkg>"` literal string matches logger name.
- matriz `_transport.py` (D-24): no special-case here — `status=="ERROR"` is a 200 OK response that NEVER hits `_RETRYABLE_STATUS`, so the transport never sees it. PrimaryAPIError raised in `_core.parse_envelope_response` happens AFTER transport returns. NO change required.

---

### `packages/<pkg>/src/<pkg>/_atransport.py` (new module, async transport — 3 paquetes; matriz NOT in Phase 8)

**Primary analog:** RESEARCH.md §"Architecture Patterns" Pattern 1 + tenacity `AsyncRetrying`. Same structure as sync but:
- `class AsyncRetryTransport(httpx.AsyncHTTPTransport)`
- `async def handle_async_request(self, request)` (httpx's async transport method)
- `async for attempt in AsyncRetrying(...)` + `async with attempt:`
- `await asyncio.sleep(...)` for Retry-After (D-32) — `asyncio.CancelledError` propagates naturally.

**Secondary analog (async double-checked locking shape):** `packages/iol-client/src/iol_client/aio.py` lines 154-218 (`_ensure_http_client` + `_login_unlocked` + `_refresh_unlocked` — shows the async lock + await pattern Phase 8 must mirror for AsyncRetryTransport calls).

**Mirror with sync, only async-specific deltas:**
```python
import asyncio
from tenacity import AsyncRetrying  # NOT Retrying

class AsyncRetryTransport(httpx.AsyncHTTPTransport):
    def __init__(self, *, max_attempts: int = 2, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._max_attempts = max(max_attempts, 1)
        self._logger = logging.getLogger("<pkg>")

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if not request.extensions.get("idempotent", False):
            return await super().handle_async_request(request)
        if self._max_attempts <= 1:
            return await super().handle_async_request(request)
        # ... (mirror sync; use AsyncRetrying + async for + async with)
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0),
            retry=(
                retry_if_exception_type(_RETRYABLE_EXC)
                | retry_if_exception_type(_RetryableStatus)
            ),
            reraise=True,
        ):
            async with attempt:
                response = await super().handle_async_request(request)
                await response.aread()  # body-consume async variant
                # ... Retry-After honoring with await asyncio.sleep(min(delay, _RETRY_AFTER_CAP_S))
                # ... raise _RetryableStatus(response) o return
```

**Differences from analog:**
- **matriz NOT created** (D-25): Phase 10 REFAC-04 lo tape. matriz's `aio.py` permanece stub Phase 6.
- The `_RETRYABLE_EXC`, `_RETRYABLE_STATUS`, `_RETRY_AFTER_CAP_S`, `_RetryableStatus`, `_parse_retry_after` may be **duplicated in `_atransport.py`** OR **factorized into `_transport.py` and imported** — planner's call (Claude's Discretion section of CONTEXT.md). Recommendation: duplicate verbatim per paquete (mirrors sync `_transport.py`); avoid one-direction coupling between transport modules.

---

### `packages/<pkg>/src/<pkg>/_logging.py` (new module, observability — 4 paquetes)

**Primary analog:** RESEARCH.md §"Architecture Patterns" Pattern 4 lines 605-682 (canonical `RedactingFilter` + `attach()` excerpt — iol example). Planner duplicates 4× verbatim with per-paquete patterns.

**Critical anti-pattern to avoid:** `verification/redaction.py` exists at `/Users/sebadlf/development/becerra/market-libs/verification/redaction.py` but it is a **print-redaction utility** (`safe_print()` / `redact()`) — NOT a `logging.Filter`. **D-10 forbids importing from `verification/`** in package source. The `_BEARER` regex shape in `verification/redaction.py:31` (`r"(Bearer\s+)[A-Za-z0-9._~+/=-]+"`) is a useful reference for the Bearer redaction pattern but must be **re-implemented** inside each `_logging.py`.

**Imports + filter shape** (research Pattern 4 lines 622-672 verbatim):
```python
"""RedactingFilter + attach() factory — Phase 8 LOG-01/02/03.

LOG-01: NullHandler attached to logging.getLogger("<pkg>") in __init__.py;
NEVER logging.basicConfig nor logging.root touched (Pitfall 6).

LOG-02: RedactingFilter scrubs Bearer / X-Auth-Token / password= / refresh_token /
JSON password / matriz auth_basic password from record.msg/args/__dict__.
Duplicated 4× per package (NO importable de verification/).
"""

from __future__ import annotations

import logging
import re

# Per-package patterns — see "Per-package redaction recipes" below.
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")
_X_AUTH_TOKEN_RE = re.compile(r"(X-Auth-Token\s*:\s*)[A-Za-z0-9._\-]+", re.IGNORECASE)
_PASSWORD_URLENC_RE = re.compile(r"(password=)[^&\s]+")
_PASSWORD_JSON_RE = re.compile(r'("password"\s*:\s*")[^"]+(")')


def _redact(text: str) -> str:
    text = _BEARER_RE.sub("Bearer ***", text)
    text = _X_AUTH_TOKEN_RE.sub(r"\1***", text)
    text = _PASSWORD_URLENC_RE.sub(r"\1***", text)
    text = _PASSWORD_JSON_RE.sub(r"\1***\2", text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _redact(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            else:
                record.args = tuple(
                    _redact(a) if isinstance(a, str) else a for a in record.args
                )
        # Scan record.__dict__ for sentinel substrings in extra= values.
        for key, value in list(record.__dict__.items()):
            if isinstance(value, str) and any(
                marker in value
                for marker in ("Bearer ", "password=", "refresh_token=", "X-Auth-Token")
            ):
                record.__dict__[key] = _redact(value)
        return True


def attach() -> None:
    logger = logging.getLogger("<pkg>")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
```

**Per-package redaction recipes (D-10 + D-22):**

| Package | Extra patterns beyond the Bearer/X-Auth-Token/password baseline |
|---------|------------------------------------------------------------------|
| `ambito_financiero_client` | None (no auth, no credenciales en URL/headers) |
| `iol_client` | OAuth `refresh_token=...` URL-encoded (D-10 IOL refresh_token) AND JSON `"refresh_token":"..."` — login response includes both formats; see `_core.py:175-178` for the IOL payload shape |
| `higyrus_client` | JSON `{"password":"..."}` (login body, see `_core.py:189-197`); url query `cuit=...` redaction (Higyrus PII, not in roadmap LOCK but research §Pattern 4 mention); JSON `{"token":"..."}` (login response) |
| `matriz_client` | D-22: `Authorization: Basic <base64>` header redaction (Risk API); when `record.__dict__` contains `auth_basic` tuple, split to `auth_basic_user=<user>` + `auth_basic_password='<redacted>'`. `X-Username`/`X-Password` headers (login per `_core.py:255-262`). |

---

### `packages/<pkg>/src/<pkg>/_core.py` (extend — 4 paquetes)

**Analog:** the file itself (extension, not new).

**ámbito** — current shape (`_core.py:59-72` excerpt):
```python
@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
```

Phase 8 delta:
```python
@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    idempotent: bool = False  # Phase 7 D-13 forward-decl (already exists per CONTEXT.md)
    endpoint_name: str = ""  # Phase 8 NEW
```
Plus: every `build_get_dollar_banco_nacion_request` flips `idempotent=True` and sets `endpoint_name="get_dollar_banco_nacion"` (D-03/D-07).

**iol** — current shape (`_core.py:81-95`):
```python
@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
```
Phase 8 delta: add `idempotent: bool = False` + `endpoint_name: str = ""`. Flip `idempotent=True` on:
- `build_get_quote_request` (`_core.py:211-228`)
- `build_get_historical_quotes_request` (`_core.py:231-251`)
- `build_get_instruments_request` (`_core.py:254-263`)
- `build_get_instruments_by_type_request` (`_core.py:266-277`)
- `build_login_request` (`_core.py:133-149`) per D-03
- `build_refresh_request` (`_core.py:181-194`) per D-03

**higyrus** — current shape (`_core.py:89-113`):
```python
@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    url_pre_encoded: bool = False
```
Phase 8 delta: add `idempotent: bool = False` + `endpoint_name: str = ""` + `account_id: str | None = None` (D-11). Builders with `id_cuenta` parameter (movimientos, posicion_valuada, posiciones) set `account_id=id_cuenta` in the returned spec. Flip `idempotent=True` on all GET builders + `build_login_request`.

**matriz** — current shape (`_core.py:128-142`):
```python
@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    auth_basic: tuple[str, str] | None = None
```
Phase 8 delta: add `idempotent: bool = False` + `endpoint_name: str = ""` + `account_id: str | None = None`. Flip `idempotent=True` on:
- GETs (`build_get_segments_request`, `build_get_all_instruments_request`, etc.)
- `build_login_request` (`_core.py:246-262`)
- POST mutating builders (`build_new_order_request`, `build_replace_order_request`, `build_cancel_order_request`) keep `idempotent=False` — mutation gate per D-01/D-07/D-24. Note: these are HTTP method GET on the Primary API (quirk), so HTTP-method-based gates would FAIL. The explicit flag is non-negotiable.

Builders with `account` / `account_name` / `account_id` parameter set `spec.account_id` in their returned RequestSpec.

---

### `packages/<pkg>/src/<pkg>/client.py` shell `_request()` (extend — 4 paquetes)

**Analog:** the file itself.

**ámbito** — current shape (`client.py:106-114` excerpt):
```python
def _request(self, spec: _core.RequestSpec) -> httpx.Response:
    """Transport shell — dispatch HTTP only (D-03). Status / body handled by `_core`."""
    client = self._ensure_http_client()
    return client.request(
        spec.method,
        f"{self._state.base_url}{spec.path}",
        params=spec.params,
        headers=spec.headers,
    )
```

Phase 8 delta (no 401 re-auth — ámbito no auth):
```python
def _request(self, spec: _core.RequestSpec) -> httpx.Response:
    http = self._ensure_http_client()
    request_id = uuid.uuid4().hex
    req = http.build_request(
        spec.method,
        f"{self._state.base_url}{spec.path}",
        params=spec.params,
        headers=spec.headers,
    )
    req.extensions["idempotent"] = spec.idempotent
    req.extensions["request_id"] = request_id
    req.extensions["endpoint_name"] = spec.endpoint_name
    return http.send(req)
```

**iol** — current shape (`client.py:237-251`):
```python
def _request(self, spec: RequestSpec) -> httpx.Response:
    """Ejecuta una request autenticada (Bearer) — D-03 retorna Response."""
    self._ensure_token()
    assert self._state.token is not None
    http = self._ensure_http_client()
    url = f"{self._state.base_url}{spec.path}"
    headers = {"Authorization": f"Bearer {self._state.token}", **(spec.headers or {})}
    return http.request(
        spec.method,
        url,
        params=spec.params,
        json=spec.json_body,
        headers=headers,
    )
```

Phase 8 delta (RESEARCH.md §Pattern 3 lines 564-602 is the canonical excerpt for iol):
```python
def _request(self, spec: RequestSpec) -> httpx.Response:
    self._ensure_token()
    assert self._state.token is not None
    request_id = uuid.uuid4().hex
    http = self._ensure_http_client()
    url = f"{self._state.base_url}{spec.path}"
    headers = {"Authorization": f"Bearer {self._state.token}", **(spec.headers or {})}
    req = http.build_request(
        spec.method, url,
        params=spec.params, json=spec.json_body, headers=headers,
    )
    req.extensions["idempotent"] = spec.idempotent
    req.extensions["request_id"] = request_id
    req.extensions["endpoint_name"] = spec.endpoint_name
    resp = http.send(req)
    try:
        _raise_for_response(resp)
    except IOLAuthError:
        # D-02 exactly-one re-auth (iol has no Risk API, so no auth_basic branch).
        self._state.token = None
        self._ensure_token()
        assert self._state.token is not None
        req.headers["Authorization"] = f"Bearer {self._state.token}"
        resp = http.send(req)
        _raise_for_response(resp)
    return resp
```

**higyrus** — analogous to iol but with `_state.account_id` propagation. Current `_request()` at `client.py:176-200`. Add `req.extensions["account_id"] = spec.account_id` when non-None. WR-03 fix (raise `HigyrusAuthError` if `_ensure_token()` returns with token=None) preserved.

**matriz** — D-23 branch on `spec.auth_basic`. Current `_request()` at `client.py:184-196`. Phase 8:
```python
def _request(self, spec: RequestSpec) -> httpx.Response:
    http = self._ensure_http_client()
    url = f"{self._state.base_url}{spec.path}"
    request_id = uuid.uuid4().hex
    if spec.auth_basic is not None:
        # Risk API path — D-23 says: RetryTransport YES, 401 re-auth NO.
        req = http.build_request(spec.method, url, params=spec.params)
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        return http.send(req, auth=httpx.BasicAuth(*spec.auth_basic))
    # Token path
    self._ensure_token()
    if self._state.token is None:
        raise RuntimeError("matriz_client.client: _ensure_token() did not populate _token")
    headers = {"X-Auth-Token": self._state.token, **(spec.headers or {})}
    req = http.build_request(spec.method, url, params=spec.params, headers=headers)
    req.extensions["idempotent"] = spec.idempotent
    req.extensions["request_id"] = request_id
    req.extensions["endpoint_name"] = spec.endpoint_name
    if spec.account_id is not None:
        req.extensions["account_id"] = spec.account_id
    resp = http.send(req)
    try:
        _raise_for_response(resp)
    except AuthenticationError:
        # D-23: skip re-auth for Risk API (auth_basic path returned above).
        # For token path: exactly-one re-auth.
        self._state.token = None
        self._ensure_token()
        req.headers["X-Auth-Token"] = self._state.token
        resp = http.send(req)
        _raise_for_response(resp)
    return resp
```

---

### `packages/<pkg>/src/<pkg>/client.py` Client.__init__ + configure() (extend — 4 paquetes)

**Analog (ámbito canon, `client.py:58-68`):**
```python
def __init__(
    self,
    *,
    base_url: str | None = None,
    user_agent: str | None = None,
) -> None:
    self._state = _ClientState()
    if base_url is not None:
        self._state.base_url = base_url.rstrip("/")
    if user_agent is not None:
        self._state.user_agent = user_agent
```

Phase 8 delta — add 2 kwargs (D-15/D-16/D-19):
```python
def __init__(
    self,
    *,
    base_url: str | None = None,
    user_agent: str | None = None,
    max_retries: int = 2,           # Phase 8 D-15/D-20
    http_client: httpx.Client | None = None,  # Phase 8 D-16
) -> None:
    self._state = _ClientState()
    if base_url is not None:
        self._state.base_url = base_url.rstrip("/")
    if user_agent is not None:
        self._state.user_agent = user_agent
    self._max_retries = max_retries  # used by _ensure_http_client
    if http_client is not None:
        # D-16: use AS-IS, no RetryTransport wrap.
        self._state.http_client = http_client
```

**`_ensure_http_client` delta** — wraps `httpx.HTTPTransport` with `RetryTransport`:
```python
def _ensure_http_client(self) -> httpx.Client:
    if self._state.http_client is None:
        self._state.http_client = httpx.Client(
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": self._state.user_agent},
            transport=_transport.RetryTransport(max_attempts=self._max_retries + 1),
        )
    assert isinstance(self._state.http_client, httpx.Client)
    return self._state.http_client
```
Note: `max_retries=2` → `max_attempts=3` (D-06 says default = "2 total req count" but Phase 8 RESEARCH/D-19 clarify `max_retries=0` → 1 request total, so `max_attempts = max_retries + 1`). Planner must reconcile the off-by-one carefully — see CONTEXT.md D-06 vs D-19 vs RESEARCH §"D-06" (line 27: "max_attempts=2 uniform" but D-19 says "max_retries=0 → 1 outgoing"). **Recommendation:** map `max_retries=N` → `max_attempts=N+1` (matches anthropic/openai semantics where `max_retries` excludes the initial attempt).

**configure() delta** — mirror analog (`client.py:140-153` for ámbito; `client.py:333-373` for iol; etc.). Add `max_retries=None` + `http_client=None` carry-forward params. Update `_default_client = Client(base_url=..., max_retries=..., http_client=...)` replacement to pass through new kwargs.

**`Client.__slots__` delta** — add `_max_retries` to `__slots__` (currently just `("_state",)` per `client.py:56` for ámbito, `client.py:103` for iol). Slots are mandatory per project convention; missing the addition causes AttributeError at assignment.

---

### `packages/<pkg>/src/<pkg>/aio.py` (extend — 3 paquetes; matriz NOT)

**Analog:** the file itself. Mirror sync `client.py` deltas. Use `AsyncRetryTransport` from `_atransport.py` and `httpx.AsyncClient(transport=...)`.

Reference for the async double-checked locking pattern that must be preserved: `packages/iol-client/src/iol_client/aio.py:158-172` (`_ensure_http_client` with `self._client_lock`). The RetryTransport instantiation slots into the `httpx.AsyncClient(...)` constructor call.

**matriz `aio.py`** — NO change per D-25. Snapshot test for matriz only adds the 2 new kwargs to `Client.__init__` and `configure()`. `AsyncClient.__init__` keeps its current Phase 6 stub signature (no `max_retries`/`http_client` until Phase 10).

---

### `packages/<pkg>/src/<pkg>/__init__.py` (extend — 4 paquetes)

**Analog:** `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py:21-47` (canonical re-export shape) + RESEARCH.md §Pattern 4 lines 614-619 (the `attach()` invocation).

Phase 8 delta — insert AFTER the existing imports but BEFORE `__all__`:
```python
# Phase 8 LOG-01: attach NullHandler + RedactingFilter to package logger.
# Library convention per Python Logging HOWTO. NEVER touches logging.root.
from <pkg> import _logging as _logging_attach
_logging_attach.attach()
del _logging_attach  # NOT re-exported — internal wiring only
```

Note: do NOT add `_logging` to `__all__`. The `del` statement prevents accidental re-exports. iol's existing `__init__.py:62` (`_ = _get_default`) is the analog for "intentionally private re-export with ruff F401 suppression".

---

### `packages/<pkg>/pyproject.toml` (extend — 4 paquetes)

**Analog:** `packages/ambito-financiero-client/pyproject.toml:21-24` (canonical `[project] dependencies` shape):
```toml
dependencies = [
    "httpx>=0.27",
    "python-dotenv>=1.0",
]
```

Phase 8 delta — add tenacity:
```toml
dependencies = [
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "tenacity>=9.1.0,<10",  # Phase 8 RELY-01..04 retries
]
```

Apply to all 4 paquetes. Run `uv sync --all-packages --all-extras --dev --frozen` post-edit to refresh `uv.lock`.

---

### Cross-cutting guard tests (6 files in `verification/`)

#### `verification/test_retry_mutation_gate.py` (NEW)

**Analog:** `verification/test_sync_async_isolation.py:41-46` (parametrize tuples + helper config + pytest-httpx idiom). Phase 8 mirrors this structure exactly.

**Mutation gate test pattern** — research SUMMARY §Pitfall 4 + CONTEXT.md D-26 + `verification/test_sync_async_isolation.py:130-161`:
```python
import importlib
import pytest
from pytest_httpx import HTTPXMock

# Packages with mutating endpoints to test. matriz new_order is HTTP GET (Primary
# API quirk) — must NOT retry without idempotent=True per D-01/D-07/D-24.
_PACKAGES_WITH_MUTATING = [
    ("iol_client", "login"),  # login marked idempotent=True per D-03 — should retry
    ("matriz_client", "new_order"),  # matriz quirk — must NOT retry
]

@pytest.mark.parametrize(...)
def test_mutating_post_never_retries(pkg_name, ..., httpx_mock: HTTPXMock) -> None:
    pkg = importlib.import_module(pkg_name)
    # configure(token=..., token_expires_at=9_999_999_999.0) per conftest pattern
    httpx_mock.add_response(status_code=503)
    with pytest.raises(getattr(pkg, "<PkgAPIError>")):
        pkg.new_order(...)
    assert len(httpx_mock.get_requests()) == 1  # NO retry (mutation gate)
```

The "GET retries N times" half follows the same pattern but with `pkg.get_X(...)` + mock 503 multiple times + `assert len(httpx_mock.get_requests()) == 3` (max_attempts=3 default).

#### `verification/test_retry_401_reauth.py` (NEW)

**Analog:** `verification/test_sync_async_isolation.py:112-161` (parametrize + auth config setup). Skip ámbito (no auth).

**Pattern** — combine config from `iol_client/tests/conftest.py:25-39` (configure with token sentinel) + httpx_mock chain:
```python
@pytest.mark.parametrize("pkg_name", ["iol_client", "higyrus_client", "matriz_client"])
def test_401_triggers_single_reauth(pkg_name, httpx_mock: HTTPXMock) -> None:
    pkg = importlib.import_module(pkg_name)
    # configure with expired token to force initial _ensure_token() login call,
    # then 401 → re-auth → 200 chain.
    httpx_mock.add_response(status_code=200, ...)  # login resp
    httpx_mock.add_response(status_code=401, ...)  # first call fails
    httpx_mock.add_response(status_code=200, ...)  # login retry
    httpx_mock.add_response(status_code=200, ...)  # call succeeds
    result = pkg.get_X(...)
    assert result == expected
    assert len(httpx_mock.get_requests()) == 4  # initial login + 401 + re-login + 200
```

For matriz Risk API (D-23): config with `auth_basic=...` and mock 401 → assert AuthError raised WITHOUT re-auth attempt (only 1 outgoing request).

#### `verification/test_logging_root_unchanged.py` (NEW)

**Analog:** no direct analog — closest is `verification/test_public_surface.py:153-170` (cross-package module import + state check pattern). Standalone test, no parametrize.

```python
import logging
import importlib

def test_logging_root_handlers_unchanged_after_package_imports() -> None:
    handlers_before = list(logging.root.handlers)
    filters_before = list(logging.root.filters)
    level_before = logging.root.level
    for pkg in ["ambito_financiero_client", "iol_client", "higyrus_client", "matriz_client"]:
        importlib.import_module(pkg)
    assert list(logging.root.handlers) == handlers_before
    assert list(logging.root.filters) == filters_before
    assert logging.root.level == level_before
```

Note: pytest's caplog fixture installs a handler on logging.root by design. Use `monkeypatch` or capture root handlers via the LogRecord stream — the planner verifies pytest 8.3 behavior here.

#### `verification/test_logging_no_token_leak.py` (NEW)

**Analog:** `verification/test_sync_async_isolation.py:112-161` (parametrize × 4 paquetes + configure(token=sentinel)). Combine with pytest `caplog` fixture.

```python
@pytest.mark.parametrize("pkg_name", ["iol_client", "higyrus_client", "matriz_client"])
def test_token_never_leaks_to_caplog(pkg_name, httpx_mock, caplog) -> None:
    pkg = importlib.import_module(pkg_name)
    SECRET = "SECRET-LITERAL-12345"
    # config with token=SECRET via _configure_sync helper (copy from test_sync_async_isolation)
    httpx_mock.add_response(...)  # mock a successful response
    caplog.set_level(logging.DEBUG, logger=pkg_name)
    pkg.get_X(...)  # fire request
    for record in caplog.records:
        assert SECRET not in record.getMessage()
        # Also check structured fields:
        for k, v in record.__dict__.items():
            if isinstance(v, str):
                assert SECRET not in v
```

For ámbito (no auth), the sentinel is injected via `base_url=f"https://{SECRET}.test"` and the test asserts the secret IS visible (since base_url is not redacted) — this is a sanity check that the parametrize works even for the no-auth package.

#### `verification/test_retry_after_cap.py` (NEW)

**Analog:** `verification/test_sync_async_isolation.py:130-138` (pytest-httpx pattern + single-package). Cross-cutting, uses one paquete (recommendation: iol_client since it has a quick GET endpoint).

```python
import time
def test_retry_after_capped_at_60s(httpx_mock: HTTPXMock) -> None:
    import iol_client
    iol_client.configure(token="X", token_expires_at=9_999_999_999.0, ...)
    # First response: 429 with Retry-After: 600 (10 minutes — server bug or hostile)
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "600"})
    httpx_mock.add_response(status_code=200, json={"instrumentos": []})
    t0 = time.monotonic()
    iol_client.get_instruments("argentina")
    elapsed = time.monotonic() - t0
    assert elapsed < 65, f"Retry delay was {elapsed}s; expected cap at 60s"
    assert len(httpx_mock.get_requests()) == 2  # retry happened
```

#### `verification/test_async_cancellation.py` (NEW)

**Analog:** `verification/test_sync_async_isolation.py:164-208` (async parametrize + matriz skip). Phase 8 mirrors:

```python
@pytest.mark.parametrize("pkg_name", ["ambito_financiero_client", "iol_client", "higyrus_client"])
async def test_cancellation_during_retry(pkg_name, httpx_mock) -> None:
    if pkg_name == "matriz_client":
        pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore")
    pkg = importlib.import_module(pkg_name)
    aio = pkg.aio
    # _configure_async per analog
    # 503 → 503 chain (would normally trigger backoff sleep)
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(aio.get_X(...), timeout=0.5)
    # Assertion: cancellation interrupted the backoff sleep — total elapsed < 1s.
```

---

### `verification/snapshots/<pkg>-surface.txt` (extend — 4 paquetes)

**Analog (ámbito canon):** `verification/snapshots/ambito-financiero-client-surface.txt` (8-line header invariant + sorted body lines).

Phase 8 delta — update lines for `Client`, `AsyncClient`, `configure` to include the 2 new kwargs. Example for ámbito:
```
# Before (current):
Client : class : (*, base_url: 'str | None' = None, user_agent: 'str | None' = None) -> 'None'
# After Phase 8:
Client : class : (*, base_url: 'str | None' = None, user_agent: 'str | None' = None, max_retries: 'int' = 2, http_client: 'httpx.Client | None' = None) -> 'None'
```

Same delta for `AsyncClient` (3 paquetes) and `configure()` (4 paquetes). Per D-28, snapshot updates are atomic with each per-package plan.

**Special case matriz** per D-25: only `Client` + `configure()` get the new kwargs in the snapshot. `AsyncClient` line stays at the current Phase 6 stub signature.

**Regen tool:** `verification/regen_snapshots.py` (Phase 6) — invoked manually after edits; planner verifies diff matches expected delta.

---

### `pyproject.toml` root + `.github/workflows/ci.yml` (D-27 CI rule)

**Analog (root pyproject):** `pyproject.toml:38-67` (ruff config block). If planner picks D-27 alternative (a) — ruff LOG ruleset — extend `[tool.ruff.lint] select = [...]` adding `"LOG"`. Ruff `LOG015` covers root-logger calls; `logging.basicConfig` is NOT in the LOG rule set (verified in RESEARCH §"D-27" line 101) — needs an explicit grep step as well.

**Analog (CI):** `.github/workflows/ci.yml:23-41` (`lint` job structure). Add a step:
```yaml
      - name: lint-logging (Phase 8 LOG-01 — no logging.basicConfig / logging.root in package src)
        run: |
          if grep -rn 'logging\.basicConfig\|logging\.root' packages/*/src/; then
            echo "::error::Phase 8 LOG-01 violated — package source must not call logging.basicConfig or logging.root.*"
            exit 1
          fi
```

The import-linter contracts in `pyproject.toml:129-162` stay unchanged. Optional: add `_transport.py`/`_logging.py` to forbidden module list (planner discretion).

---

## Shared Patterns

### `from __future__ import annotations` mandatory

**Source:** every Python source file in `packages/*/src/`. Verified in `_state.py:27`, `_core.py:29`, `client.py:18`, `aio.py:23`, `__init__.py` (omitted only when no annotations present — `__init__.py` files).

**Apply to:** all new `_transport.py`, `_atransport.py`, `_logging.py` files. NOT optional.

### Module docstring + `__all__` list

**Source:** `packages/iol-client/src/iol_client/_state.py:1-45` + `_core.py:1-73`.

**Pattern:**
```python
"""<One-line summary>.

<Multi-paragraph block describing the module's responsibility, the decisions
it implements (e.g., D-XX), and any cross-package invariants it preserves.>

NOT re-exported from __init__.py — this is a private module (leading underscore).
"""

from __future__ import annotations
# imports...

__all__ = ["RetryTransport", ...]
```

**Apply to:** all new modules.

### Private module file naming convention

**Source:** `packages/<pkg>/src/<pkg>/_state.py`, `_core.py`, `_params.py`, `_parsing.py`.

**Convention:** leading underscore in filename indicates private module. Never re-exported via `from <pkg> import *`. Imports are explicit absolute paths (e.g., `from iol_client import _transport` not `from . import _transport` — per project TID rule).

**Apply to:** `_transport.py`, `_atransport.py`, `_logging.py`.

### `@dataclass(frozen=True, slots=True) RequestSpec` extension contract

**Source:** Phase 7 D-13 forward-declared `idempotent: bool = False` in all 4 `_core.py` files (per CONTEXT.md "Carry-forward Phase 7"). Phase 8 ADDS fields but never removes — and all new fields have defaults to preserve back-compat with positional or kwarg call sites.

**Apply to:** all 4 `_core.py` RequestSpec definitions.

### Test fixture autouse `configure(token=..., token_expires_at=9_999_999_999.0)`

**Source:** `packages/iol-client/tests/conftest.py:25-52` + `packages/matriz-client/tests/conftest.py:19-41` + `packages/higyrus-client/tests/conftest.py` (same shape).

**Apply to:** all new tests in `verification/`. The 9.99e9 sentinel epoch is year 2286 — never expires during a test run.

### pytest-httpx `httpx_mock.add_response` + `httpx_mock.get_requests()`

**Source:** `verification/test_sync_async_isolation.py:131-208`. Mock responses queued FIFO; `httpx_mock.get_requests()[-1]` returns the last outgoing request for header/URL assertions.

**Apply to:** all new `verification/test_retry_*.py` and `test_logging_no_token_leak.py` files.

### Async parametrize + matriz skip with literal reason

**Source:** `verification/test_sync_async_isolation.py:175-176`:
```python
if pkg_name == "matriz_client":
    pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore")
```

**Apply to:** `test_async_cancellation.py` per D-26. Skip reason is verbatim — same line in test_sync_async_isolation.py.

### Snapshot file format (W3 pinning)

**Source:** `verification/test_public_surface.py:88-150` (8-line `#` header + sorted body lines + trailing newline).

**Apply to:** each per-package snapshot update in Plans 2-5.

---

## No Analog Found

Files with no close existing match in the codebase. Planner uses RESEARCH.md research patterns instead.

| File | Role | Data Flow | Reason / Source of truth |
|------|------|-----------|--------------------------|
| `_transport.py` (RetryTransport class body) | sync transport subclass + tenacity Retrying iterator | No existing httpx transport subclass in the repo. ALL existing `_ensure_http_client` calls create `httpx.Client(timeout=_REQUEST_TIMEOUT)` with default transport. → use RESEARCH.md §Pattern 1 lines 348-504 verbatim |
| `_atransport.py` (AsyncRetryTransport) | async transport subclass | mismo — no async transport subclass exists. → RESEARCH.md §Pattern 1 + tenacity AsyncRetrying docs cited in RESEARCH §"D-32" |
| `_logging.py` (RedactingFilter + attach()) | logging.Filter implementation | `verification/redaction.py` is a print-redaction utility — NOT a logging.Filter; D-10 prohibits importing from verification/. → RESEARCH.md §Pattern 4 lines 605-682 verbatim |
| `_RetryableStatus` sentinel exception | internal control-flow signal | No existing internal sentinel pattern in the repo. → RESEARCH §"D-31" + §Pattern 1 line 386-396 |
| Retry-After parsing (`_parse_retry_after`) | RFC 9110 §10.2.3 delta-seconds + HTTP-date parser | None — first time the repo touches `Retry-After`. → RESEARCH §Pattern 1 lines 402-411 + Claude's Discretion |
| tenacity `wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0)` formula | full-jitter backoff config | None — Phase 8 is first retry mechanism. → RESEARCH §"D-08" + §Pattern 1 |

---

## Metadata

**Analog search scope:**
- `packages/*/src/*/_state.py` (4 files; Phase 6 baseline)
- `packages/*/src/*/_core.py` (4 files; Phase 7 baseline)
- `packages/*/src/*/client.py` (4 files; Phase 6/7 shells)
- `packages/*/src/*/aio.py` (3 files; matriz aio is stub)
- `packages/*/src/*/__init__.py` (4 files; Phase 6 re-export shape)
- `packages/*/tests/conftest.py` (4 files; configure(token=...) autouse fixtures)
- `packages/*/pyproject.toml` (4 files; dependencies + build config)
- `verification/test_sync_async_isolation.py` (parametrize × 4 paquetes pattern)
- `verification/test_public_surface.py` (snapshot diff pattern)
- `verification/snapshots/*-surface.txt` (4 files; format invariant)
- `verification/redaction.py` (sanity check — confirmed NOT a logging.Filter; D-10 must not import)
- `pyproject.toml` (root config: ruff, mypy, importlinter, pytest)
- `.github/workflows/ci.yml` (lint + typecheck + test jobs)

**Files scanned:** 36 source + 4 snapshots + 2 config = 42 files inspected.

**Pattern extraction date:** 2026-06-12
