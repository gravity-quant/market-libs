# Phase 6: Compat Safety Net + Client Class Skeleton — Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 23 new + 12 modified
**Analogs found:** 23 / 23 (100% coverage for new files)

## Overview

Phase 6 produces three classes of artifacts per package (× 4 packages: ámbito, iol, higyrus, matriz) plus two cross-package verification artifacts. Strict no-shared-code constraint: every `_state.py`, `Client`, `AsyncClient` skeleton lives inside its own package and **copy-pastes** the pattern instead of importing from a shared module. Sync/async parity is mandatory; matriz currently has no `aio.py` and ships a stub `AsyncClient` per CONTEXT.md success criterion 3 (research Open Q #1).

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `verification/test_public_surface.py` | snapshot-test (cross-pkg) | introspection | `packages/ambito-financiero-client/tests/test_harness_schema.py:18-60` | role-match (golden file harness pattern) |
| `verification/regen_snapshots.py` | utility script | introspection | `verification/schema.py:1-40` | role-match (verification harness module) |
| `verification/snapshots/<pkg>-surface.txt` (× 4) | snapshot fixture (text) | static | (none — first fixture of its kind in repo) | no analog (use RESEARCH.md format) |
| `packages/<pkg>/tests/test_fixture_reaches_production.py` (× 4) | guard-test (pytest-httpx) | request-response | `packages/iol-client/tests/test_client.py:30-40, 92-100` | exact (pytest-httpx + monkeypatch auth header assertion) |
| `packages/<pkg>/src/<pkg>/_state.py` (× 4) | dataclass module | static state | `packages/higyrus-client/src/higyrus_client/models.py:30-89, 92-113` (SafeModel pattern) + `client.py:50-56` (module globals being absorbed) | exact (slots dataclass + env-var defaults) |
| `Client` class in `packages/<pkg>/src/<pkg>/client.py` (× 4) | class | request-response | `packages/iol-client/src/iol_client/client.py:43-189` (entire module-level functions to absorb) | exact (same domain logic, new ownership) |
| `AsyncClient` class in `packages/<pkg>/src/<pkg>/aio.py` (× 3, +1 stub for matriz) | class | request-response (async) | `packages/iol-client/src/iol_client/aio.py:26-207` | exact for 3 pkgs; **stub** for matriz (no aio.py exists) |
| PEP 562 `__getattr__` shim in `client.py` and `aio.py` (× 4 + 3 + 1 stub) | module shim | attribute-forwarding | (no analog — PEP 562 not currently used in repo) | no analog (use RESEARCH.md Pattern 1) |
| Migrated `packages/<pkg>/tests/conftest.py` (× 4) | test fixture | test-setup | `packages/iol-client/tests/conftest.py:13-34` (current pattern being migrated) | exact (transform existing autouse fixtures) |

---

## Pattern Assignments

### 1. `verification/test_public_surface.py` (snapshot-test, cross-package introspection)

**Role:** Single pytest module that, for each of the 4 packages, enumerates public attributes (`__all__` + signatures), serializes to a text format, and compares against `verification/snapshots/<pkg>-surface.txt`.

**Closest analog:** `packages/ambito-financiero-client/tests/test_harness_schema.py` (golden-file harness test pattern; lives under `packages/<pkg>/tests/` rather than `verification/`, but the testing idiom matches).

**Excerpt — golden-file test idiom** (`packages/ambito-financiero-client/tests/test_harness_schema.py:14-44`):

```python
from __future__ import annotations

from pathlib import Path

from verification.capture import capture
from verification.schema import schema_of


def test_schema_of_dict_returns_keys_and_type_names_sorted() -> None:
    """Test 1: un dict se reduce a {clave: nombre-de-tipo}, ordenado, sin valores."""
    result = schema_of({"b": "1.415,00", "a": 5})
    assert result == {"a": "int", "b": "str"}
    # Ningún valor del payload aparece en el resultado (PII-free por construcción).
    assert "1.415,00" not in result.values()
    assert 5 not in result.values()


def test_schema_of_list_uses_first_element_and_handles_empty() -> None:
    """Test 2: una lista usa el primer elemento como muestra; vacía -> []."""
    assert schema_of([{"x": 1}]) == [{"x": "int"}]
    assert schema_of([]) == []
```

**Adaptation notes:**
- Move the new test file under `verification/` (not under any one package) so it sweeps all 4 packages. Note: `pyproject.toml` already configures `testpaths = ["packages", "tests"]`; **the planner must add `verification` to `testpaths` OR confirm the existing collect picks it up via `--import-mode=importlib`** (research Pattern 5 invokes it via `uv run pytest verification/test_public_surface.py` explicitly).
- Use `inspect.signature` + `inspect.isclass/isfunction/iscoroutinefunction` + sorted `__all__`. RESEARCH.md Pattern 5 (lines 540-609) provides the canonical code.
- Use `@pytest.mark.parametrize("pkg_name", _PACKAGES)` for the 4-package sweep.
- Wrap `inspect.signature(obj)` in try/except `(TypeError, ValueError)` for safety (research Pitfall 9).

---

### 2. `verification/regen_snapshots.py` (utility script)

**Role:** Operator-run script that re-derives the 4 snapshot files. Imports enumeration helpers from the test module.

**Closest analog:** `verification/schema.py` (small utility-only module living in `verification/` package).

**Excerpt — verification utility module shape** (`verification/schema.py:18-40`):

```python
from __future__ import annotations

from typing import Any

__all__ = ["schema_of"]


def schema_of(payload: Any) -> Any:
    """Reduce un payload a su estructura: claves + tipos, nunca valores.
    ...
    """
    if isinstance(payload, dict):
        return {k: schema_of(v) for k, v in sorted(payload.items())}
    if isinstance(payload, list):
        return [schema_of(payload[0])] if payload else []
    return type(payload).__name__
```

**Adaptation notes:**
- File ends with `if __name__ == "__main__": main()` so it runs as `python verification/regen_snapshots.py` (research Pattern 7, lines 685-707).
- Reuse `_PACKAGES`, `_enumerate_surface`, `_snapshot_path` symbols from `verification.test_public_surface`. To avoid circular import: import them inside `main()` (lazy).
- Write text with explicit `"\n".join(lines) + "\n"` (trailing newline) so `git diff` is stable.

---

### 3. `verification/snapshots/<pkg>-surface.txt` (× 4) (snapshot fixture, text)

**Role:** Committed golden file — one line per public symbol with `<name> : <kind> : <signature>`, sorted alphabetically, with a comment header documenting the regen command.

**Closest analog:** None in repo today — this is the first golden text fixture of this shape. The closest precedent is the JSON-schema snapshot pattern documented in `.planning/codebase/TESTING.md` (DRIFT-01) and the SafeModel diff golden artefacts mentioned in `verification/safemodel_diff.py`.

**Excerpt — header convention** (RESEARCH.md lines 937-945):

```
# Public surface snapshot for iol-client.
# Generated by: python verification/regen_snapshots.py
# Format: <name> : <kind> : <signature>
# Sort: stable alphabetical by name.
# DO NOT EDIT BY HAND. To accept an intentional change, run the regen script
# above and commit the diff alongside the source change that justifies it.
#
```

**Adaptation notes:**
- One file per package (file naming uses dashes, not underscores: `iol-client-surface.txt` not `iol_client-surface.txt`). Maps via `pkg_name.replace("_", "-")` (RESEARCH.md line 594).
- Plan 1 (REFAC-01) freezes the **pre-refactor** snapshot; Plans 2–5 (REFAC-02 per pkg) regenerate via `regen_snapshots.py` adding the new `Client`, `AsyncClient`, `close`, `aclose` lines.
- Symbol kind values: `class`, `function`, `coroutine`, `module`, or a type name fallback (RESEARCH.md lines 561-570).

---

### 4. `packages/<pkg>/tests/test_fixture_reaches_production.py` (× 4) (guard-test, request-response)

**Role:** 1 sync + 1 async pytest-httpx test per package. Configures a sentinel token via `pkg.configure(token=...)`, fires a real call, asserts the sentinel ends up in the outgoing wire request's auth header (iol/higyrus: `Authorization: Bearer`; matriz: `X-Auth-Token`; ambito: `base_url` in URL).

**Closest analog:** `packages/iol-client/tests/test_client.py` lines 30-99 — canonical pytest-httpx assertion idiom across the repo.

**Excerpt — pytest-httpx auth header pattern** (`packages/iol-client/tests/test_client.py:14-22, 30-40`):

```python
from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import IOLAuthError, IOLRateLimitError


def test_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert iol_client.login() == "tok-iol"
    assert iol_client.client._token == "tok-iol"


def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(IOLAuthError):
        iol_client.client._request("GET", "/api/anything")
```

**Excerpt — async test convention** (`packages/iol-client/tests/conftest.py:27-34`):

```python
@pytest.fixture(autouse=True)
async def _configure_async(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    aio.configure(base_url="https://api.test", username="u", password="p")
    monkeypatch.setattr(aio, "_token", "test-token", raising=False)
    monkeypatch.setattr(aio, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    await aio.aclose()
    aio.configure(base_url="https://api.test", username="", password="")
```

**Adaptation notes per package:**
- **iol:** assert `req.headers["Authorization"] == "Bearer SYNC-sentinel-iol"` (and `ASYNC-sentinel-iol` for the async test). RESEARCH.md Pattern 6 (lines 630-663) gives a complete code-ready template.
- **higyrus:** same header as iol (`Authorization: Bearer`); use `SYNC-sentinel-higyrus` / `ASYNC-sentinel-higyrus`. Endpoint URL must use a real existing one — recommend `get_listado_cuentas(estado="alta")` to stay consistent with current tests.
- **matriz:** header is `X-Auth-Token: <SENTINEL>` per CONTEXT.md D-12. Sync only (matriz has no `aio.py`). The async guard for matriz uses the new stub `AsyncClient` (Open Q #1 resolution) and must raise `NotImplementedError` on REST methods — OR the async guard is **deferred** for matriz only (planner decision). The default recommendation: ship the async guard against a stub `AsyncClient` and skip with `pytest.skip("matriz aio.py is Phase 10")` if invoking a REST method.
- **ambito:** no auth — assert `"configured.test" in str(req.url)` per RESEARCH.md lines 668-677. Sync + async tests both use `configure(base_url="https://configured.test")` and call `get_dollar_banco_nacion(dt.date(2026, 1, 2))`.
- Each test uses `pkg.configure(token=..., token_expires_at=...)` — this extension is a **prerequisite** added in Plan 1 (per Research Assumption A8 / Open Q #2). The 3-line addition to existing `configure()` lands in Plan 1 alongside the guards.

---

### 5. `packages/<pkg>/src/<pkg>/_state.py` (× 4) (dataclass module)

**Role:** New private module per package. Holds `@dataclass(slots=True) _ClientState` with all per-instance state (`base_url`, `username`, `password`, `token`, `token_expires_at`, optional `refresh_token`/`account_id`/`http_client`/`token_lock`). NOT frozen because `token` is mutated on refresh.

**Closest analog:** Two-pronged:
- **For dataclass shape / slots idiom:** `packages/higyrus-client/src/higyrus_client/models.py:30-89, 92-113` (SafeModel + frozen+slots dataclass).
- **For env-var defaults / TTL constants / wire identifiers being absorbed:** `packages/iol-client/src/iol_client/client.py:43-56` (module-level globals).

**Excerpt — slots dataclass with SafeModel parent** (`packages/higyrus-client/src/higyrus_client/models.py:30-45, 92-113`):

```python
class SafeModel:
    """Base class for Higyrus API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        data: dict[str, Any] = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for field in fields(cast(Any, cls)):
            kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cls(**kwargs)


@dataclass(frozen=True, slots=True)
class PosicionValuada(SafeModel):
    """Valued position row returned by ``GET /api/cuentas/{idCuenta}/posicionValuada``.
    ...
    """

    cuenta: str
    operador: str
    unidad: str
    lugar: str
    estado: str
    uso: str
    fecha: str
```

**Excerpt — module-level globals (to be absorbed into `_ClientState`)** (`packages/iol-client/src/iol_client/client.py:43-56`):

```python
load_dotenv()

DEFAULT_BASE_URL = "https://api.invertironline.com"
_REQUEST_TIMEOUT = 30.0
# Refrescamos un poco antes del vencimiento documentado (15 min).
_TOKEN_TTL_BUFFER_SECONDS = 60

_base_url: str = os.getenv("IOL_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
_user: str = os.getenv("IOL_USER", "")
_password: str = os.getenv("IOL_PASSWORD", "")
_token: str | None = None
_token_expires_at: float = 0.0
_refresh_token: str | None = None
_client = httpx.Client(timeout=_REQUEST_TIMEOUT)
```

**Adaptation notes:**
- `_state.py` uses `@dataclass(slots=True)` — NOT `frozen=True` (mutable token requires writes). Comment in the docstring explains why frozen is rejected.
- Defaults via `field(default_factory=_env_*)` helpers (RESEARCH.md Pattern 2, lines 384-429) — NOT `field(default=os.getenv(...))` at class definition time, otherwise env vars set after import don't take effect.
- Per-package field set (RESEARCH.md Per-Package Divergence Matrix):
  - **ambito:** `base_url`, `user_agent`, `http_client`. No token; no credentials.
  - **iol:** `base_url`, `username`, `password`, `token`, `token_expires_at`, `refresh_token`, `http_client`, `token_lock`.
  - **higyrus:** `base_url`, `client_id`, `username`, `password`, `token`, `token_expires_at` (rename from `_token_ts`), `account_id`, `http_client`, `token_lock`. RESEARCH.md "Conftest Migration Pattern" recommends the rename for cross-pkg consistency.
  - **matriz:** `base_url`, `username`, `password`, `token`, `token_expires_at` (rename from `_token_ts`), `http_client`. Renames `_session` → `http_client` per research Pitfall #5.
- Forward-declare `refresh_token: str | None = None` and `account_id: str | None = None` in **all** packages (research recommends staying schema-consistent across phases). Only iol populates `refresh_token` in Phase 6; only higyrus has `account_id` semantic (Phase 9 BUG-04).
- Must include `from __future__ import annotations` at the top (project convention).
- Module is private — leading underscore in filename AND class name `_ClientState`. NOT re-exported from `__init__.py`.

---

### 6. `Client` class in `packages/<pkg>/src/<pkg>/client.py` (× 4) (class, request-response)

**Role:** Sync class owning `_state: _ClientState`. Methods absorb the current top-level functions verbatim (renamed to instance methods reading `self._state.*` instead of module globals). Adds `__enter__`/`__exit__`/`close()`/`__repr__()` (redacted) / `__reduce__()` (raises) / `__deepcopy__()` (raises).

**Closest analog:** `packages/iol-client/src/iol_client/client.py:43-189` — the entire module-level pattern that becomes the body of `Client` methods.

**Excerpt — current module-level functions to absorb into `Client` methods** (`packages/iol-client/src/iol_client/client.py:155-189`):

```python
def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    # D-IOL-10: si tenemos refresh_token, intentar refresh antes de password grant.
    if _refresh_token:
        try:
            _refresh()
            return
        except IOLAuthError:
            # Refresh inválido (revocado, expirado, etc.) — fallback a password.
            pass
    login()


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    """Ejecuta una request autenticada (Bearer)."""
    _ensure_token()
    assert _token is not None

    resp = _client.request(
        method,
        f"{_base_url}{path}",
        params=params,
        json=json_body,
        headers={"Authorization": f"Bearer {_token}"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    return resp
```

**Excerpt — Client class skeleton with lifecycle** (RESEARCH.md Pattern 3, lines 436-499):

```python
from typing import Self

class Client:
    """Sync client; instance state in self._state.

    Pickle / deepcopy contract (D-23): NOT supported. Use multiprocessing
    fork start method or rebuild from configure() in worker.
    """
    __slots__ = ("_state",)

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
    ) -> None:
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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._state.http_client is not None:
            self._state.http_client.close()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18: redact credentials and token
        return (
            f"<IOLClient(base_url={self._state.base_url!r}, "
            f"username={self._state.username!r}, "
            f"password={'***' if self._state.password else ''!r}, "
            f"token={'***' if self._state.token else None!r})>"
        )

    def __reduce__(self):  # D-23
        raise TypeError(
            "IOLClient is not picklable; use multiprocessing's fork start "
            "method or recreate in worker via iol_client.Client(...)"
        )

    def __deepcopy__(self, memo):  # D-23
        raise TypeError("IOLClient is not deepcopy-safe (httpx.Client owns "
                        "TCP pool + SSL context)")
```

**Adaptation notes per package:**
- **`__init__` kwargs (per CONTEXT.md D-13):**
  - ambito: `(*, base_url=None)` (no creds, no token — but include `user_agent=None` to match existing `configure()` signature).
  - iol/higyrus/matriz: `(*, username=None, password=None, base_url=None, token=None, token_expires_at=None)`. higyrus additionally has `client_id=None`.
- **iol additionally:** absorbs `_refresh()` (private method `_refresh(self)`) and the OAuth refresh_token branch in `_ensure_token` (lines 122-152, 155-166 of current `client.py`). `__init__` does NOT accept `refresh_token=` in Phase 6 (D-13 defers to Phase 9), but the shim must forward `_refresh_token` reads (research Pitfall #3).
- **matriz additionally:** `Client.login()` parses `response.headers["X-Auth-Token"]` (CONTEXT.md D-22, current code at `client.py:117-121`). HTTP Basic Auth fallback (Risk API) becomes `Client._risk_auth(self)`.
- **higyrus:** `_request` keeps the verbatim URL-encoding logic at `client.py:182-198` (preserve `/` literal in query; `urlencode(..., doseq=True, quote_via=quote, safe="/")`).
- All `Client` classes use `__slots__ = ("_state",)` to prevent accidental attribute typos.
- Endpoint methods (`get_quote`, `get_listado_cuentas`, etc.) are migrated verbatim from current top-level functions, replacing module globals with `self._state.*` and `self._request(...)` with `self._request(...)`.

---

### 7. `AsyncClient` class in `packages/<pkg>/src/<pkg>/aio.py` (× 3 full + 1 stub) (class, async request-response)

**Role:** Async mirror of `Client`. Lazy `httpx.AsyncClient` (created on first `_ensure_http_client()`), per-instance `asyncio.Lock()` for token refresh, `__aenter__`/`__aexit__`/`aclose()`. State lives in same `_ClientState` dataclass (shared between sync/async surfaces by **shape**, but **NEVER shared by instance** — each module has its own `_default_async_client`).

**Closest analog:** `packages/iol-client/src/iol_client/aio.py:62-78, 162-207` — async lifecycle + double-checked locking pattern.

**Excerpt — async lazy http_client + per-instance lock** (`packages/iol-client/src/iol_client/aio.py:62-78`):

```python
async def _ensure_http_client() -> httpx.AsyncClient:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is not None:
            return _client
        _client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT)
        return _client


async def aclose() -> None:
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.aclose()
            _client = None
```

**Excerpt — async double-checked locking on token** (`packages/iol-client/src/iol_client/aio.py:162-207`):

```python
async def login() -> str:
    """Autentica contra ``POST /token`` y cachea el token."""
    async with _token_lock:
        return await _login_unlocked()


async def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    async with _token_lock:
        if _token and time.time() < _token_expires_at:
            return
        # D-IOL-10: dentro del mismo lock, intentar refresh antes de password grant.
        if _refresh_token:
            try:
                await _refresh_unlocked()
                return
            except IOLAuthError:
                # Refresh inválido (revocado, expirado, etc.) — fallback a password.
                pass
        await _login_unlocked()


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    await _ensure_token()
    async with _token_lock:
        token = _token
    assert token is not None

    client = await _ensure_http_client()
    resp = await client.request(
        method,
        f"{_base_url}{path}",
        params=params,
        json=json_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    return resp
```

**Excerpt — AsyncClient skeleton** (RESEARCH.md Pattern 4, lines 506-532):

```python
import asyncio

class AsyncClient:
    __slots__ = ("_state", "_client_lock")

    def __init__(self, *, base_url=None, username=None, password=None,
                 token=None, token_expires_at=None) -> None:
        self._state = _ClientState()
        # ... same field copy as sync Client ...
        # Locks created lazily on first use (avoid binding to a loop in __init__)
        self._client_lock: asyncio.Lock | None = None

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._state.http_client is not None:
            assert isinstance(self._state.http_client, httpx.AsyncClient)
            await self._state.http_client.aclose()
            self._state.http_client = None
```

**Adaptation notes:**
- **ambito/iol/higyrus:** full `AsyncClient` with all endpoint methods migrated from the current `aio.py` top-level functions. Replace module globals with `self._state.*`. Replace module-level `asyncio.Lock()` (research Pitfall #6) with lazy-created locks on `self._state.token_lock` and `self._client_lock`.
- **matriz STUB (Open Q #1, RESEARCH.md line 1033 recommendation):** create `packages/matriz-client/src/matriz_client/aio.py` as a new file with **only** `class AsyncClient` containing `__init__`, `__aenter__`/`__aexit__`/`aclose()`, `__repr__()`, `__reduce__()`, `__deepcopy__()`. No `_default_async_client`, no top-level `configure()` / `get_X()` shims, no REST methods. Phase 10 (REFAC-04) grows it. The stub satisfies the success criterion "los 4 paquetes exponen `Client` y `AsyncClient`".
- Async double-checked locking pattern is preserved verbatim — only the `global` mutations become `self._state.*` mutations. `_login_unlocked`/`_refresh_unlocked` become `Client._login_unlocked(self)` / `Client._refresh_unlocked(self)`.
- Add `from typing import Self` and use `Self` as the `__aenter__` return type (Python 3.11+ idiom — research State of the Art table).

---

### 8. PEP 562 `__getattr__` shim in `client.py` (× 4) and `aio.py` (× 3 + 1 stub) (module shim)

**Role:** Module-level read-only `__getattr__(name)` that forwards reads of legacy global names (`_token`, `_token_ts`/`_token_expires_at`, `_refresh_token` for iol, `_client`/`_session`) to `_get_default()._state.<field>`. Tests that read `pkg.client._token` post-refactor see the lazy default client's state.

**Closest analog:** None in the existing codebase — no module currently uses PEP 562 `__getattr__`. Use RESEARCH.md Pattern 1 verbatim (lines 325-377).

**Excerpt — RESEARCH.md Pattern 1 (canonical shim shape):**

```python
# packages/iol-client/src/iol_client/client.py
# Source: PEP 562 (peps.python.org/pep-0562/) + CONTEXT.md D-02

from __future__ import annotations

from typing import Any

from iol_client._state import _ClientState

# ... Client class definition ...

_default_client: Client | None = None


def _get_default() -> Client:
    global _default_client
    if _default_client is None:
        _default_client = Client()  # reads env vars via _ClientState defaults
    return _default_client


# PEP 562 shim — D-02 enumerates the forwarded names for iol-client.
_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_expires_at": "token_expires_at",
    "_refresh_token": "refresh_token",  # IOL-specific
}

_FORWARDED_HTTP_CLIENT = "_client"  # D-02 exception for main_higyrus.py


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim (D-01, D-02)."""
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**Per-package forwarded set (RESEARCH.md Per-Package Divergence Matrix):**

| Package | `_FORWARDED_TO_STATE` keys → state field | `_FORWARDED_HTTP_CLIENT` |
|---------|------------------------------------------|--------------------------|
| ambito | (none — no token) | `_client` → `state.http_client` |
| iol (client.py) | `_token` → `token`, `_token_expires_at` → `token_expires_at`, `_refresh_token` → `refresh_token` | `_client` → `state.http_client` |
| iol (aio.py) | same + `_token_lock` → `state.token_lock` | `_client` → `state.http_client` |
| higyrus (client.py) | `_token` → `token`, `_token_ts` → `token_expires_at` (rename) | `_client` → `state.http_client` |
| higyrus (aio.py) | same + `_token_lock` → `state.token_lock` | `_client` → `state.http_client` |
| matriz (client.py) | `_token` → `token`, `_token_ts` → `token_expires_at` (rename) | `_session` → `state.http_client` (or rename to `_client` per research Pitfall #5) |
| matriz (aio.py — stub) | (no shim — stub has no `_default_async_client`) | (none) |

**Adaptation notes:**
- **Read-only only** (D-01). PEP 562 does NOT intercept `__setattr__` — writes to `pkg.client._token` from test bodies hit the module dict and DON'T reach `_state` (research Pitfall #1, #4). This is mitigated by conftest migration + inline test-body rewrites in each per-package commit.
- **iol Pitfall #3 mitigation:** add `_refresh_token` to `_FORWARDED_TO_STATE` for iol (this is the planner's adoption of Research Assumption A5 / Open Q #3).
- **matriz `_base_url` is NOT in the forwarded set** (D-02), but `verification/mutation_gate.py:55` and `tests/test_harness_mutation_gate.py:30-31, 49-50, 70-71, 99, 110` read/write `matriz_client.client._base_url`. **Plan 5 must update both** to use `matriz_client._get_default()._state.base_url` (read) and `matriz_client.configure(base_url=...)` (write) — see Open Q #4 in research.
- The shim must NOT emit `DeprecationWarning` (D-03).

---

### 9. Migrated `packages/<pkg>/tests/conftest.py` (× 4) (test fixture)

**Role:** Replace `monkeypatch.setattr(pkg.client, "_token", "test-token", raising=False)` with `pkg.configure(token="<sentinel>", token_expires_at=9_999_999_999.0)`. Removes the need for `monkeypatch` parameter from autouse fixtures.

**Closest analog:** `packages/iol-client/tests/conftest.py` (current pattern being migrated).

**Excerpt — current pattern (to be replaced)** (`packages/iol-client/tests/conftest.py:13-34`):

```python
@pytest.fixture(autouse=True)
def _configure_sync(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
    )
    # Precargamos un token para evitar disparar login en endpoints autenticados.
    monkeypatch.setattr(iol_client.client, "_token", "test-token", raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    iol_client.configure(base_url="https://api.test", username="", password="")


@pytest.fixture(autouse=True)
async def _configure_async(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    aio.configure(base_url="https://api.test", username="u", password="p")
    monkeypatch.setattr(aio, "_token", "test-token", raising=False)
    monkeypatch.setattr(aio, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    await aio.aclose()
    aio.configure(base_url="https://api.test", username="", password="")
```

**Excerpt — post-Phase-6 target pattern** (RESEARCH.md "Conftest Migration Pattern" lines 768-779):

```python
@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    yield
    iol_client.configure(base_url="https://api.test", username="", password="")
```

**Adaptation notes per package:**
- **ambito:** trivial — no token to inject; only `base_url` (and `user_agent` if a test uses it). Conftest is already minimal at `tests/conftest.py:16-28`; no `monkeypatch` to remove.
- **iol:** add `token=` + `token_expires_at=` kwargs to both sync and async autouse fixtures. Drop `monkeypatch` parameter.
- **higyrus:** add `token=` + `token_expires_at=` (research recommends renaming the internal `_token_ts` field to `token_expires_at` for cross-pkg consistency). Drop `monkeypatch` parameter.
- **matriz:** sync only; add `token=` + `token_expires_at=`. Drop `monkeypatch` parameter.
- **Inline test-body monkeypatch sites (CRITICAL — research lines 791-815):** the 15+ inline `monkeypatch.setattr(pkg.client, "_token", X, raising=False)` calls inside `test_client.py`/`test_async_client.py` (e.g., `packages/iol-client/tests/test_client.py:147-149, 177-179, 215-217, 244-245, 275-277, 307, 314`) **land on a dead address** after the refactor. Each per-package REFAC-02 plan must migrate these to one of:
  - `pkg._get_default()._state.<field> = X` (direct state mutation; research recommendation)
  - `pkg.configure(token=X, ...)` (replace default with new instance)
  - Direct write: `pkg.client._password = "another"` at `packages/iol-client/tests/test_client.py:315` → also lands on a dead address; migrate to `pkg._get_default()._state.password = "another"`.

---

## Shared Patterns

### Module Header (every new and refactored `.py` file)

**Source:** Project convention from CLAUDE.md "Code Style" + every existing module.

**Apply to:** All new `_state.py`, `test_fixture_reaches_production.py`, `test_public_surface.py`, `regen_snapshots.py`, and modified `client.py`/`aio.py` files.

```python
"""<module summary>.

<usage example as :: block>

<env vars / auth notes>
"""

from __future__ import annotations  # MANDATORY first import (project-wide)

# imports grouped: stdlib, third-party, first-party
# NO relative imports (enforced by TID ruff rule)
# NO wildcard imports
```

Reference: every existing `packages/<pkg>/src/<pkg>/client.py` (lines 1-22 of iol).

---

### Exception Hierarchy (per package)

**Source:** Each package's `exceptions.py`. Phase 6 does NOT touch these but `Client` methods must keep raising the same types.

**Apply to:** All `Client` / `AsyncClient` method bodies.

| Package | Base | Auth | API | RateLimit |
|---------|------|------|-----|-----------|
| iol | `IOLClientError` | `IOLAuthError` | `IOLAPIError` | `IOLRateLimitError` |
| higyrus | `HigyrusClientError` | `HigyrusAuthError`, `HigyrusAuthorizationError` | `HigyrusAPIError` | `HigyrusRateLimitError` |
| matriz | (via `AuthenticationError`, `PrimaryAPIError`) | `AuthenticationError` | `PrimaryAPIError` | (no rate-limit class) |
| ambito | `AmbitoFinancieroAPIError` | `AmbitoFinancieroAuthError` | `AmbitoFinancieroAPIError` + `AmbitoFinancieroNoDataError` | `AmbitoFinancieroRateLimitError` |

Reference: `packages/iol-client/src/iol_client/client.py:78-84` (`_raise_for_response`).

---

### `load_dotenv()` at module top (preserved)

**Source:** CONTEXT.md D-19. `load_dotenv()` stays at module level of `client.py` ONLY. NOT in `aio.py` (already not there), NOT in `Client.__init__`, NOT in `_state.py`.

**Apply to:** Each refactored `packages/<pkg>/src/<pkg>/client.py`.

Reference: `packages/iol-client/src/iol_client/client.py:43`.

---

### `from typing import Self` for context managers (Python 3.11+ / PEP 673)

**Source:** RESEARCH.md State of the Art table; project supports 3.12+.

**Apply to:** `Client.__enter__`, `AsyncClient.__aenter__` return type annotations.

```python
from typing import Self

def __enter__(self) -> Self:
    return self
```

---

### Test Convention: function-level + `httpx_mock` fixture

**Source:** Every existing `tests/test_client.py` / `tests/test_async_client.py`. Class-based tests are not used in this repo.

**Apply to:** All new `test_fixture_reaches_production.py` files and `test_public_surface.py`.

Reference: `packages/iol-client/tests/test_client.py:14-22` (signature pattern: `def test_*(httpx_mock: HTTPXMock) -> None`).

---

### Async test convention (`asyncio_mode = "auto"`)

**Source:** `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"`. No `@pytest.mark.asyncio` decorator needed; an `async def test_*` is auto-detected.

**Apply to:** All new async tests in `test_fixture_reaches_production.py`.

Reference: `packages/iol-client/tests/conftest.py:27` (`async def _configure_async`).

---

## No Analog Found

| File | Role | Data Flow | Reason | Fallback |
|------|------|-----------|--------|----------|
| `verification/snapshots/<pkg>-surface.txt` (× 4) | static golden text fixture | static | No other golden text fixture exists in the repo. The schema-snapshot work (`.planning/codebase/TESTING.md` DRIFT-01) is JSON-based and not yet committed. | Use RESEARCH.md "Specific Ideas" snapshot format spec (CONTEXT.md lines 322-331) verbatim. |
| PEP 562 `__getattr__` shim in `client.py` and `aio.py` | module shim | attribute forwarding | PEP 562 has zero usage in the current codebase. | Use RESEARCH.md Pattern 1 (lines 325-377) verbatim. |

---

## Critical Risks to Address in Planning

These are **not** pattern questions but cross-pattern decisions the planner must lock:

1. **Inline test-body monkeypatch migration (15+ sites in iol).** RESEARCH.md lines 791-815 lists exact sites. Decide: rewrite to `pkg._get_default()._state.<field> = X` or extend `configure(refresh_token=...)`. Recommend the former for minimal `configure()` surface growth.
2. **`verification/mutation_gate.py:55` reads `matriz_client.client._base_url` which is NOT in D-02 forwarded set.** Plan 5 must update both `mutation_gate.py` and `tests/test_harness_mutation_gate.py:30-31, 49-50, 70-71, 99, 110` to the new accessor.
3. **matriz `AsyncClient` stub vs full.** Open Q #1: ship a stub with only lifecycle methods (recommended) so CONTEXT.md success criterion 3 is satisfied without Phase 10 scope creep.
4. **`testpaths` in `pyproject.toml`.** Currently `testpaths = ["packages", "tests"]` (not `verification`). Plan 1 must add `verification` to `testpaths` OR the test runs only via explicit `uv run pytest verification/test_public_surface.py` (which is the documented cadence per CONTEXT.md D-07). Verify this with the planner before commit.

---

## Metadata

**Analog search scope:**
- `packages/iol-client/` (src + tests + conftest)
- `packages/higyrus-client/` (src models + tests + conftest)
- `packages/matriz-client/` (src + tests + conftest)
- `packages/ambito-financiero-client/` (src + tests + conftest)
- `verification/` (schema, mutation_gate, redaction)
- `tests/` (test_cycle_report)

**Files scanned (full or targeted):** 14 source/test files

**Pattern extraction date:** 2026-06-10

**Snapshot of repo state:** branch `main`, clean working tree, HEAD `25a8244 docs(state): record phase 6 context session`.
