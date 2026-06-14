# Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup - Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 11 new + 13 modified (across 4 paquetes + repo-root harness + CI)
**Analogs found:** 24 / 24 (100% — todos los archivos nuevos tienen analog Phase 6 o repo precedent)

## Overview

Phase 7 es un refactor mecánico (no es feature work): cada artefacto nuevo tiene un analog directo en el codebase post-Phase-6. Tres familias de archivos:

1. **Nuevos módulos `_core.py` por paquete (×4)** — analog directo: `_state.py` de Phase 6 (mismo header docstring, mismo `from __future__`, mismo `__all__`, mismas section-divider `# ---...---`). Difieren del `_state.py` en que `_core.py` contiene helpers stateless puros + `RequestSpec` frozen dataclass, no estado mutable.
2. **`client.py`/`aio.py` colapsados a transport shells (×7)** — el body actual se preserva en términos de class skeleton (Phase 6 `Client`/`AsyncClient` con `__slots__`/`__init__`/`_ensure_http_client`/`__enter__`/PEP 562 shim) y sólo cambian: (a) los endpoint methods se reescriben como 3-liner `spec = _core.build_X(...) ; resp = self._request(spec) ; return _core.parse_X(resp)`; (b) `_request` recibe `_core.RequestSpec` en vez de strings sueltos; (c) `_raise_for_response` (y `_unwrap` en matriz) se reemplazan por aliases module-level `= _core.raise_for_response`. matriz `aio.py` queda stub Phase 6 → Phase 10.
3. **Test harness nuevo (×2) + CI gates (×2)** — `verification/test_sync_async_isolation.py` mirror exacto del patrón `test_fixture_reaches_production.py` Phase 6 (mismo `httpx_mock.add_response` + `[req] = httpx_mock.get_requests()` + assert header). `verification/test_matriz_sweep_snapshot.py` mismo idiom + parametrize sobre 18 probes con canned payloads inline. `pyproject.toml` añade `import-linter` a `[dependency-groups]` + `[tool.importlinter]` siguiendo el shape ya establecido por `[tool.ruff]` / `[tool.mypy]` / `[tool.pytest.ini_options]`. `.github/workflows/ci.yml` añade un step `uv run lint-imports` al job `lint` siguiendo el shape de los steps `ruff check` / `ruff format --check` existentes.

**Strict no-shared-code constraint:** cada paquete copia el patrón `_core.py` independientemente. NO existe `verification/_core_shared.py` ni base class `_BaseRequestSpec`. Cada `RequestSpec` es un frozen dataclass per-package con sus fields propios (matriz: `auth_basic`; iol: `data` para form-encoded; higyrus: `json_body` + URL pre-encoded; ámbito: minimal).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` (NEW) | private helper module (builders/parsers, pure) | request-response (stateless) | `packages/ambito-financiero-client/src/ambito_financiero_client/_state.py:1-64` (module shape) + `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py` (private helper module) | exact (module shape) + role-match (helper module idiom) |
| `packages/iol-client/src/iol_client/_core.py` (NEW) | private helper module + auth-flow builder/parser | request-response + auth (stateless) | `packages/iol-client/src/iol_client/_state.py:1-89` (module shape, `__all__`, `from __future__`) | exact |
| `packages/higyrus-client/src/higyrus_client/_core.py` (NEW) | private helper module + URL-encoding quirk encapsulator | request-response (stateless) | `packages/higyrus-client/src/higyrus_client/_state.py:1-105` + `packages/higyrus-client/src/higyrus_client/_params.py` | exact (module shape) + role-match (private serialization helper) |
| `packages/matriz-client/src/matriz_client/_core.py` (NEW) | private helper module + envelope parser + CR-03 fix | request-response (stateless) + envelope-unwrap | `packages/matriz-client/src/matriz_client/_state.py:1-55` (module shape) + `packages/matriz-client/src/matriz_client/client.py:91-114` (current stateless helpers) | exact |
| `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (MODIFIED) | sync transport shell | request-response | `packages/ambito-financiero-client/src/ambito_financiero_client/client.py:78-186` (current Client class — preserved skeleton, endpoint body collapses) | exact (in-place collapse) |
| `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` (MODIFIED) | async transport shell | request-response | `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py:71-190` (current AsyncClient — preserved skeleton, endpoint body collapses) + B8 import line | exact |
| `packages/iol-client/src/iol_client/client.py` (MODIFIED) | sync transport shell + OAuth flow | request-response + auth | `packages/iol-client/src/iol_client/client.py:71-362` (current Client — preserved skeleton; auth-flow body collapses to `_core.build_login_request` + `_core.parse_login_response`) | exact |
| `packages/iol-client/src/iol_client/aio.py` (MODIFIED) | async transport shell + OAuth flow async | request-response + auth | `packages/iol-client/src/iol_client/aio.py:56-end` + B8 alias migration (D-04) | exact |
| `packages/higyrus-client/src/higyrus_client/client.py` (MODIFIED) | sync transport shell + URL-encoding quirk | request-response + auth | `packages/higyrus-client/src/higyrus_client/client.py:111-303` (current Client) | exact |
| `packages/higyrus-client/src/higyrus_client/aio.py` (MODIFIED) | async transport shell + URL-encoding quirk | request-response + auth | `packages/higyrus-client/src/higyrus_client/aio.py` (current AsyncClient) | exact |
| `packages/matriz-client/src/matriz_client/client.py` (MODIFIED) | sync transport shell + envelope handling + CR-03 close | request-response + envelope | `packages/matriz-client/src/matriz_client/client.py:122-536` (current Client) | exact (preserves skeleton; collapses endpoint bodies + moves CR-03 body-consume to `_core`) |
| `packages/matriz-client/src/matriz_client/aio.py` (UNCHANGED) | async stub (Phase 6 → Phase 10) | — | (n/a — stub kept identical) | (n/a) |
| `packages/ambito-financiero-client/tests/test_core.py` (NEW) | unit test (builders/parsers, pure) | introspection | `packages/ambito-financiero-client/tests/test_client_class.py` (test_client_class idiom) + `packages/ambito-financiero-client/tests/conftest.py:15-27` (autouse fixture pattern) | role-match (unit tests for new module) |
| `packages/iol-client/tests/test_core.py` (NEW) | unit test (builders/parsers + auth-flow) | introspection | `packages/iol-client/tests/test_client_class.py` + `packages/iol-client/tests/conftest.py:25-52` | role-match |
| `packages/higyrus-client/tests/test_core.py` (NEW) | unit test (builders/parsers + URL-encoding quirks) | introspection | `packages/higyrus-client/tests/test_client_class.py:340-352` (URL-encoding assertion idiom) | exact (URL-encoding quirk asserts) |
| `packages/matriz-client/tests/test_core.py` (NEW) | unit test (builders/parsers + envelope/CR-03) | introspection | `packages/matriz-client/tests/test_client.py` + `packages/matriz-client/tests/conftest.py:19-42` | role-match |
| `verification/test_sync_async_isolation.py` (NEW) | cross-leak guard test parametrizado (4 pkg) | request-response (pytest-httpx) | `packages/iol-client/tests/test_fixture_reaches_production.py:31-70` + `packages/matriz-client/tests/test_fixture_reaches_production.py:31-51` | exact (D-10 mirror) |
| `verification/test_matriz_sweep_snapshot.py` (NEW) | snapshot guard test (18 probes pre/post CR-05) | request-response (pytest-httpx) | `packages/matriz-client/tests/test_fixture_reaches_production.py` (mocking idiom) + `verification/test_public_surface.py:46-90` (parametrize/sweep idiom) | role-match (D-08 guard) |
| `main_matriz.py` (MODIFIED) | driver helper `_envelope_probe` x18 probes refactor | request-response | `main_matriz.py:300-350` (current `probe_get_segments` — anchor probe) + `main_matriz.py:520-590` (current `probe_get_instruments_by_cfi_ESXXXX`) | exact (in-place dedup) |
| `pyproject.toml` (MODIFIED) | dev dep `import-linter` + `[tool.importlinter]` config | static config | `pyproject.toml:23-32` (`[dependency-groups]`) + `:37-66` (`[tool.ruff]` / `[tool.mypy]` config shape) | exact (TOML section idiom) |
| `.github/workflows/ci.yml` (MODIFIED) | new CI step `lint-imports` | shell job | `.github/workflows/ci.yml:23-39` (job `lint` con steps `ruff check` + `ruff format --check`) | exact (in-place step addition) |

---

## Pattern Assignments

### 1. `_core.py` module shape (×4, one per package)

**Role:** Pure transport-agnostic helper module. Contains `RequestSpec` frozen dataclass + `build_<endpoint>_request(state, ...) → RequestSpec` builders + `parse_<endpoint>_response(resp) → typed_result` parsers + auth-flow primitives. **No I/O, no httpx.Client/AsyncClient imports.**

**Closest analog:** `_state.py` per paquete (Phase 6) — mismo module shape, mismo header docstring style con `::` code blocks, mismo `from __future__ import annotations`, mismo `__all__` listing public names + constants, mismas section-divider comments `# ---...---`.

**Excerpt — `_state.py` module-shape reference** (`packages/iol-client/src/iol_client/_state.py:1-50`):

```python
"""Per-instance state for ``iol-client`` Client/AsyncClient.

This module is **private** — only ``client.py`` and ``aio.py`` within
``iol_client`` may import it. It holds the absorption of the v1.0
module-level globals (``_base_url``, ``_user``, ``_password``, ``_token``,
``_token_expires_at``, ``_refresh_token``, ``_client``) into a single
``@dataclass(slots=True)`` instance that each ``Client`` / ``AsyncClient``
owns and mutates per-instance.

[... long docstring with sections ...]
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

import httpx

__all__ = [
    "DEFAULT_BASE_URL",
    "_REQUEST_TIMEOUT",
    "_TOKEN_TTL_BUFFER_SECONDS",
    "_ClientState",
]
```

**Adaptation notes for `_core.py`:**
- Header docstring same shape: purpose + privacy contract ("only `client.py` and `aio.py` within `<pkg>` may import it") + `::` code block with usage example + reference to Phase 7 D-01..D-06 (RequestSpec shape + body-consume-then-raise for CR-03).
- `from __future__ import annotations` mandatory (per CONVENTIONS.md).
- Imports: `dataclasses`, `typing.Any`, `httpx` (ONLY for `httpx.Response` type hint + matriz `httpx.BasicAuth`), package-internal `_state.py` (`_ClientState`), `exceptions.py`. **Never** `httpx.Client`, `httpx.AsyncClient`, `from <pkg>.client import ...`, `from <pkg>.aio import ...` — enforced by import-linter (D-09).
- `__all__` lists `RequestSpec` + all `build_*` + all `parse_*` + `raise_for_response` + (matriz) `unwrap`.
- Section dividers (idem matriz/higyrus current client.py):
  ```
  # ---------------------------------------------------------------------------
  # RequestSpec
  # ---------------------------------------------------------------------------
  # ---------------------------------------------------------------------------
  # Stateless helpers (D-04 — moved from client.py; alias preserved there)
  # ---------------------------------------------------------------------------
  # ---------------------------------------------------------------------------
  # Auth flow primitives (D-02)
  # ---------------------------------------------------------------------------
  # ---------------------------------------------------------------------------
  # Endpoint builders — <Group name> (§<N>)
  # ---------------------------------------------------------------------------
  # ---------------------------------------------------------------------------
  # Endpoint parsers — <Group name> (§<N>)
  # ---------------------------------------------------------------------------
  ```

**Excerpt — `_parsing.py` private-helper analog** (`packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py`):

> The leading underscore in `_parsing.py` and `_params.py` signals **package-private**: only callable from `client.py` and `aio.py` within the package. `_core.py` follows the same naming convention (single underscore, snake_case module). The shape is similar — pure helpers, no module state, no httpx.Client instantiation.

---

### 2. `RequestSpec` frozen dataclass (per-package fields)

**Role:** Inmutable spec capturing all that a transport shell needs to dispatch one HTTP call: method, URL path, params, headers, body. Per-package shape: matriz adds `auth_basic`; iol adds `data` (form-encoded for OAuth); higyrus adds `json_body` + URL pre-encoded variant; ámbito minimal.

**Closest analog:** `_ClientState` in `_state.py` per paquete — uses `@dataclass(slots=True)` (NOT frozen because state mutates), `field(default_factory=...)` for env-var-defaulted fields. `RequestSpec` mirrors **but**: `frozen=True, slots=True` (no mutation — spec is pure input), no `field(default_factory=...)` for env vars (state owns those; spec receives only the URL/params/body for one request).

**Excerpt — frozen dataclass + slots idiom (SafeModel models)** (`packages/matriz-client/src/matriz_client/models.py` per ARCHITECTURE.md §"Model Design"):

> Models in `<pkg>.models` are `@dataclass(frozen=True, slots=True)` per CONVENTIONS.md §"Model Design (SafeModel / dataclasses)". `RequestSpec` follows the exact same shape (frozen + slots) but is NOT a SafeModel (no `from_api` classmethod; builders construct it directly).

**Excerpt — `_ClientState` shape to mirror** (`packages/matriz-client/src/matriz_client/_state.py:45-55`):

```python
@dataclass(slots=True)
class _ClientState:
    """Mutable singleton-state container for a single ``Client`` instance."""

    base_url: str = field(default_factory=_default_base_url)
    username: str = field(default_factory=_default_username)
    password: str = field(default_factory=_default_password)
    token: str | None = None
    token_expires_at: float = 0.0
    http_client: httpx.Client | httpx.AsyncClient | None = None
    account_id: str | None = None
```

**Target `RequestSpec` shape (matriz — richest):**

```python
@dataclass(frozen=True, slots=True)
class RequestSpec:
    """Pure description of an HTTP request — no transport coupling.

    Per-package shape (D-01 / no shared internals): matriz tiene
    ``auth_basic`` opcional para la Risk API (HTTP Basic Auth fallback).
    """

    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    auth_basic: tuple[str, str] | None = None
    # idempotent: bool = False  # Phase 8 RELY-03 forward-decl (D-13 planner discretion)
```

**Per-package field divergence — locked by RESEARCH.md Pattern 1:**

| Package | Required fields | Optional fields | Reason |
|---------|------------------|-------------------|--------|
| ámbito | `method`, `path` | `params`, `headers` | Sin auth, sin body, parser HTML/JSON simple |
| iol | `method`, `path` | `params`, `headers`, `json_body`, `data` | `data` para OAuth `POST /token` form-encoded (NO JSON) |
| higyrus | `method`, `path` | `params`, `headers`, `json_body`, `url_pre_encoded: str \| None` | URL-encoding quirk: `_core.build_*` retorna URL ya `urlencode(..., doseq=True, quote_via=quote, safe="/")` para preservar `/` literal (Higyrus IIS rechaza `%2F`) |
| matriz | `method`, `path` | `params`, `headers`, `auth_basic` | Risk API (§9) usa HTTP Basic; resto X-Auth-Token |

---

### 3. Pure parser with body-consume-then-raise (CR-03 fix)

**Role:** `parse_<endpoint>_response(resp) → T` consume body explícito vía `resp.read()`, decodifica JSON, valida shape, raise typed si aplica, retorna typed result. Cierra CR-03 (matriz `_request` resource leak con HTTP/2).

**Closest analog (current code that must be moved):** `packages/matriz-client/src/matriz_client/client.py:278-294` — current `_request` body shape check + status==ERROR check. Phase 7 lo MUEVE a `_core.parse_envelope_response` y prepende `resp.read()` explícito.

**Excerpt — current matriz `_request` envelope handling** (`packages/matriz-client/src/matriz_client/client.py:278-294`):

```python
        _raise_for_response(resp)
        raw = resp.json()
        if not isinstance(raw, dict):
            # Defense for CR-01: see prior comment in legacy module.
            raise PrimaryAPIError(
                status="ERROR",
                description=f"expected JSON object body at {path}, got {type(raw).__name__}",
                message=None,
            )
        data: dict[str, Any] = raw
        if data.get("status") == "ERROR":
            raise PrimaryAPIError(
                status="ERROR",
                description=data.get("description"),
                message=data.get("message"),
            )
        return data
```

**Target `_core.parse_envelope_response` shape (CR-03 fix — body-consume BEFORE raise):**

```python
def parse_envelope_response(resp: httpx.Response, endpoint: str) -> dict[str, Any]:
    """Body-consume-then-raise parser — cierra CR-03 (Pitfall 21).

    Orden CRÍTICO (D-06):
      1. ``resp.read()``  ← consume body EXPLICITLY (HTTP/2-safe)
      2. ``raise_for_response(resp)``  ← status check after body consumed
      3. ``resp.json()``  ← decode (raises ValueError si malformed JSON)
      4. shape check + status==ERROR check
      5. raise PrimaryAPIError if applicable
    """
    resp.read()           # ← CR-03 FIX: explicit body consume
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise PrimaryAPIError(
            status="ERROR",
            description=f"expected JSON object body at {endpoint}, got {type(raw).__name__}",
            message=None,
        )
    if raw.get("status") == "ERROR":
        raise PrimaryAPIError(
            status="ERROR",
            description=raw.get("description"),
            message=raw.get("message"),
        )
    return raw  # type: ignore[return-value]
```

---

### 4. D-04 alias re-export (B8 preservation — CRITICAL)

**Role:** Mover `_raise_for_response` (los 3 paquetes con auth) y `_unwrap` (matriz) a `_core.py` SIN romper el invariante B8 `aio._raise_for_response is client._raise_for_response`. `client.py` declara alias module-level `= _core.raise_for_response`; `aio.py` también lo aliasea desde `_core` directamente. Ambos aliases referencian el MISMO objeto → identidad (`is`) preservada.

**Closest analog (test que DEBE seguir verde):** `packages/higyrus-client/tests/test_client_class.py:359-369` y `packages/iol-client/tests/test_client_class.py:275-279`.

**Excerpt — B8 identity test (higyrus, must keep passing)** (`packages/higyrus-client/tests/test_client_class.py:359-369`):

```python
def test_aio_imports_raise_for_response_from_client() -> None:
    """B8 enforcement: ``aio._raise_for_response is client._raise_for_response``.

    aio.py importa el helper de client.py — no duplica la lógica de mapeo
    de errores. Esta es la single source of truth para
    ``HigyrusClientError`` mapping.
    """
    from higyrus_client.aio import _raise_for_response as a_impl
    from higyrus_client.client import _raise_for_response as c_impl

    assert a_impl is c_impl
```

**Excerpt — current B8 import in `aio.py`** (`packages/ambito-financiero-client/src/ambito_financiero_client/aio.py:55-60`):

```python
# B8: shared, not duplicated. The explicit re-export alias (`as _raise_for_response`)
# satisfies mypy --strict's `implicit_reexport=False` so callers can import the
# helper directly via `from ambito_financiero_client.aio import _raise_for_response`.
from ambito_financiero_client.client import (
    _raise_for_response as _raise_for_response,
)
```

**Target Phase 7 alias migration (both `client.py` and `aio.py` import from `_core.py`):**

```python
# packages/<pkg>/src/<pkg>/client.py — Phase 7 post-refactor
from <pkg> import _core

# D-04: preserve B8 identity. Tests `aio._raise_for_response is client._raise_for_response`
# stay green because BOTH aliases reference the SAME object (_core.raise_for_response).
_raise_for_response = _core.raise_for_response
# matriz only:
_unwrap = _core.unwrap
```

```python
# packages/<pkg>/src/<pkg>/aio.py — Phase 7 post-refactor
from <pkg> import _core

# D-04 mirror: aio.py also references _core directly. Identity with client.py
# preserved because both aliases point to _core.raise_for_response.
_raise_for_response = _core.raise_for_response
```

**Honesty flag:** the current ambito `aio.py` `from ambito_financiero_client.client import _raise_for_response as _raise_for_response` (explicit `as` re-export for mypy strict `implicit_reexport=False`) MUST be preserved in shape — Phase 7 only changes the source module from `client` to `_core`. The `as ALIAS` pattern is needed so mypy doesn't reject the import. Apply uniformly across all 3 paquetes con auth + ambito.

---

### 5. Transport shell `_request(spec: _core.RequestSpec) -> httpx.Response` (sync + async)

**Role:** El método `_request` recibe un `RequestSpec`, dispatcha el HTTP call, retorna `httpx.Response` cruda (D-03). El endpoint method luego llama `_core.parse_<endpoint>(resp)` que hace `resp.read()` + parsing + raise typed.

**Closest analog (sync, matriz — current `_request`):** `packages/matriz-client/src/matriz_client/client.py:249-294`. Phase 7 conserva la estructura general (lazy http_client + auth-basic branch vs token branch) pero (a) recibe `_core.RequestSpec` en vez de strings sueltos, (b) DELETE el body-shape/status check (movidos a `_core.parse_envelope_response`), (c) retorna `httpx.Response` en vez de `dict`.

**Excerpt — current matriz sync `_request` shape to evolve** (`packages/matriz-client/src/matriz_client/client.py:249-276`):

```python
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        auth_basic: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request and decode the JSON payload."""
        http = self._ensure_http_client()
        url = f"{self._state.base_url}{path}"
        if auth_basic:
            resp = http.request(
                method,
                url,
                params=params,
                auth=httpx.BasicAuth(*auth_basic),
            )
        else:
            self._ensure_token()
            if self._state.token is None:
                raise RuntimeError("matriz_client.client: _ensure_token() did not populate _token")
            resp = http.request(
                method,
                url,
                params=params,
                headers={"X-Auth-Token": self._state.token},
            )
```

**Target Phase 7 shell (matriz sync):**

```python
def _request(self, spec: _core.RequestSpec) -> httpx.Response:
    """Transport shell — única responsabilidad: dispatch HTTP."""
    http = self._ensure_http_client()
    url = f"{self._state.base_url}{spec.path}"
    if spec.auth_basic is not None:
        return http.request(
            spec.method,
            url,
            params=spec.params,
            auth=httpx.BasicAuth(*spec.auth_basic),
        )
    self._ensure_token()
    assert self._state.token is not None  # mypy narrowing
    headers = {"X-Auth-Token": self._state.token, **(spec.headers or {})}
    return http.request(spec.method, url, params=spec.params, headers=headers)
```

**Closest analog (async, iol — current `_request`):** `packages/iol-client/src/iol_client/aio.py` (`_request` async method, ya existe similar shape). Phase 7 mantiene `await` + locks, sólo cambia el shape del input (spec) y el output (returns `httpx.Response`).

---

### 6. Endpoint method post-refactor — 3-liner shell

**Role:** Después del refactor, cada endpoint method en `client.py`/`aio.py` queda ≤30-50 LOC por endpoint group (D-05). El body típico es 3 líneas: build spec, ejecutar request, parse response.

**Closest analog (current verbose body that collapses):** `packages/matriz-client/src/matriz_client/client.py:302-340` — `get_segments` / `get_all_instruments` / `get_instruments_details` / `get_instrument_detail` / `get_instruments_by_cfi` / `get_instruments_by_segment`. Currently 2-15 LOC each con `_get(path, ...)` + `_unwrap(...)` + `Model.from_api(...)`. Post-refactor: `spec = _core.build_<name>(self._state, ...)` + `resp = self._request(spec)` + `return [Model.from_api(x) for x in _core.parse_<name>(resp)]`.

**Excerpt — current matriz `get_segments`** (`packages/matriz-client/src/matriz_client/client.py:302-304`):

```python
def get_segments(self) -> list[Segment]:
    path = "/rest/segment/all"
    return [Segment.from_api(s) for s in _unwrap(self._get(path), "segments", path)]
```

**Target Phase 7 shape:**

```python
def get_segments(self) -> list[Segment]:
    spec = _core.build_get_segments_request(self._state)
    resp = self._request(spec)
    data = _core.parse_envelope_response(resp, spec.path)
    return [Segment.from_api(s) for s in _core.unwrap(data, "segments", spec.path)]
```

**Excerpt — current iol `get_quote`** (`packages/iol-client/src/iol_client/client.py:294-315`):

```python
def get_quote(
    self,
    simbolo: str,
    *,
    mercado: str = "bcba",
    plazo: str = "t2",
) -> dict[str, Any]:
    """Cotización actual de un título.

    Endpoint: ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion``.
    """
    resp = self._request(
        "GET",
        f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion",
        params={...},
    )
    data: dict[str, Any] = resp.json()
    return data
```

**Target Phase 7 shape (iol `get_quote`):**

```python
def get_quote(self, simbolo: str, *, mercado: str = "bcba", plazo: str = "t2") -> dict[str, Any]:
    spec = _core.build_get_quote_request(self._state, simbolo, mercado=mercado, plazo=plazo)
    resp = self._request(spec)
    return _core.parse_get_quote_response(resp)
```

---

### 7. Auth-flow factoring (`build_login_request` + `parse_login_response`)

**Role:** El flow `POST /token` queda factorizado en (a) builder puro que retorna `RequestSpec`, (b) parser puro que extrae `(token, expires_at, refresh_token?)` del response. Sync/async `login()` orchestran el HTTP call y escriben al state.

**Closest analog (current — iol login):** `packages/iol-client/src/iol_client/client.py:189-220`. La estructura es: validar credentials → build form-encoded body → POST → check is_error → extract `access_token` / `expires_in` / `refresh_token` → write to state. Phase 7 corta este flow en dos: builder retorna `RequestSpec(method="POST", path="/token", data={...}, headers={...})`; parser hace `resp.read()` + `raise_for_response(resp)` + `data = resp.json()` + extract tuple.

**Excerpt — current iol `login()`** (`packages/iol-client/src/iol_client/client.py:189-220`):

```python
def login(self) -> str:
    """Autentica contra ``POST /token`` (OAuth password grant)."""
    if not self._state.username or not self._state.password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")

    client = self._ensure_http_client()
    resp = client.post(
        f"{self._state.base_url}/token",
        data={
            "username": self._state.username,
            "password": self._state.password,
            "grant_type": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)

    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")

    self._state.token = access_token
    # CR-01: política condicional simétrica con _refresh() (Pitfall 3).
    new_refresh = data.get("refresh_token")
    if isinstance(new_refresh, str) and new_refresh:
        self._state.refresh_token = new_refresh
    self._state.token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token
```

**Target Phase 7 `_core` factoring (iol):**

```python
# iol_client/_core.py
def build_login_request(state: _ClientState) -> RequestSpec:
    if not state.username or not state.password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")
    return RequestSpec(
        method="POST",
        path="/token",
        data={"username": state.username, "password": state.password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def parse_login_response(resp: httpx.Response) -> tuple[str, float, str | None]:
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")
    new_refresh = data.get("refresh_token")
    refresh_out = new_refresh if isinstance(new_refresh, str) and new_refresh else None
    expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token, expires_at, refresh_out
```

```python
# iol_client/client.py shell consume — Phase 7
def login(self) -> str:
    spec = _core.build_login_request(self._state)
    http = self._ensure_http_client()
    resp = http.post(f"{self._state.base_url}{spec.path}", data=spec.data, headers=spec.headers)
    token, expires_at, refresh = _core.parse_login_response(resp)
    self._state.token = token
    self._state.token_expires_at = expires_at
    if refresh is not None:
        self._state.refresh_token = refresh  # CR-01 conditional rotation preserved
    return token
```

**iol-specific extra:** `build_refresh_request` + `parse_refresh_response` mirror `build_login_request` + `parse_login_response` (same shape, distinct body). Existing `_refresh` (`packages/iol-client/src/iol_client/client.py:222-251`) is the analog to follow.

---

### 8. `verification/test_sync_async_isolation.py` — cross-leak sentinel test

**Role:** Cross-package guard parametrizado: por paquete, configure sync con `SYNC-sentinel-<pkg>`, configure async con `ASYNC-sentinel-<pkg>`, fire 1 request en cada surface, assert wire header tiene el sentinel correspondiente. matriz `pytest.skip` con reason `"matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"`.

**Closest analog:** `packages/iol-client/tests/test_fixture_reaches_production.py:31-70` (Phase 6 baseline). Phase 7 replica el patrón EXACTO pero (a) parametrizado sobre 4 paquetes en 1 archivo cross-cutting, (b) vive en `verification/`, (c) usa **dos sentinels distintos** (sync vs async) simultáneamente para detectar cross-leak.

**Excerpt — Phase 6 sync sentinel guard (iol)** (`packages/iol-client/tests/test_fixture_reaches_production.py:31-49`):

```python
def test_iol_sync_sentinel_token_reaches_authorization_header(httpx_mock: HTTPXMock) -> None:
    """SYNC: sentinel injected via ``configure(token=...)`` reaches the Authorization header."""
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="SYNC-sentinel-iol",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer SYNC-sentinel-iol"
```

**Excerpt — Phase 6 matriz sync sentinel (different auth header)** (`packages/matriz-client/tests/test_fixture_reaches_production.py:31-51`):

```python
def test_matriz_sync_sentinel_token_reaches_x_auth_token_header(
    httpx_mock: HTTPXMock,
) -> None:
    """SYNC: sentinel pushed via ``configure(token=...)`` reaches the X-Auth-Token header."""
    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="SYNC-sentinel-matriz",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )

    matriz_client.get_segments()

    [req] = httpx_mock.get_requests()
    assert req.headers["X-Auth-Token"] == "SYNC-sentinel-matriz"
```

**Target shape (verification/test_sync_async_isolation.py — D-10):**

```python
"""Cross-leak sentinel test: sync token MUST NOT bleed into async surface and viceversa.

Phase 7 D-10: parametrizado sobre 4 paquetes. matriz `pytest.skip` con reason explícito
hasta Phase 10 REFAC-04 + TokenStore (D-11 / forward-track).
"""
from __future__ import annotations

import importlib
import pytest
from pytest_httpx import HTTPXMock

# (pkg_name, header_name, value_prefix, sync_url, async_url, sync_call, async_call_factory)
_PACKAGES = [
    ("iol_client", "Authorization", "Bearer ", ...),
    ("higyrus_client", "Authorization", "Bearer ", ...),
    ("ambito_financiero_client", None, None, ...),  # no auth — usa base_url proxy
    ("matriz_client", "X-Auth-Token", "", ...),
]

@pytest.mark.parametrize("pkg_name,header,prefix,...", _PACKAGES)
def test_sync_async_token_isolation(pkg_name, header, prefix, httpx_mock: HTTPXMock):
    if pkg_name == "matriz_client":
        pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore")
    pkg = importlib.import_module(pkg_name)
    sync_sentinel = f"SYNC-sentinel-{pkg_name}"
    async_sentinel = f"ASYNC-sentinel-{pkg_name}"
    pkg.configure(token=sync_sentinel, token_expires_at=9_999_999_999.0, ...)
    pkg.aio.configure(token=async_sentinel, token_expires_at=9_999_999_999.0, ...)
    # 1. fire sync — assert wire header == sync_sentinel
    # 2. fire async — assert wire header == async_sentinel
    # 3. CROSS-LEAK CHECK: ensure they are distinct in the captured requests
```

**Adaptation notes:**
- 1 parametrize value per package; matriz `pytest.skip` inside the function (not at parametrize level — visible in CI output per D-11).
- ámbito has no auth → uses `base_url` proxy (`"https://sync-sentinel-ambito.test"` vs `"https://async-sentinel-ambito.test"`); assert the wire URL contains the respective sentinel.
- mypy strict: function signature must be precise; planner decides if parametrize values use a TypedDict / tuple.

---

### 9. `verification/test_matriz_sweep_snapshot.py` — 18 probes snapshot guard

**Role:** Pre/post CR-05 refactor guard. Mocks `_matriz_request` (or the underlying httpx.Client) via pytest-httpx with canned payloads for each of the 18 probes, runs both the pre-refactor (verbose) and post-refactor (`_envelope_probe`-based) versions, asserts `ProbeResult` shape identical. D-08: vive en `verification/` (consistente con `verification/test_public_surface.py`).

**Closest analog (mocking idiom):** `packages/matriz-client/tests/test_fixture_reaches_production.py` (httpx_mock + canned `{"status": "OK", "segments": []}` response) + `verification/test_public_surface.py:46-90` (parametrize sweep + per-package iteration idiom).

**Excerpt — canned matriz envelope payload** (`packages/matriz-client/tests/test_fixture_reaches_production.py:43-45`):

```python
httpx_mock.add_response(
    url="https://api.test/rest/segment/all",
    json={"status": "OK", "segments": []},
)
```

**Excerpt — parametrize sweep idiom** (`verification/test_public_surface.py:46-51`):

```python
_PACKAGES = [
    "ambito_financiero_client",
    "iol_client",
    "higyrus_client",
    "matriz_client",
]
```

**Target shape (D-08 snapshot guard):**

```python
"""Snapshot guard: 18 main_matriz.py probes (CR-05) preserve ProbeResult shape pre/post refactor.

Phase 7 D-08: registrado pre-refactor con payloads canned vía pytest-httpx.
Post-refactor _envelope_probe(envelope_key=...) DEBE producir el mismo ProbeResult.
Las 2 risk probes (probe_get_detailed_positions, probe_get_account_report)
preservan envelope_key=None (D-07).
"""
from __future__ import annotations
import pytest
from pytest_httpx import HTTPXMock

import main_matriz
import matriz_client

# (probe_callable, mock_url, mock_response, expected_status, expected_detail_substring)
_PROBE_FIXTURES = [
    (main_matriz.probe_get_segments, "https://api.test/rest/segment/all",
     {"status": "OK", "segments": [{"marketSegmentId": "DDF"}]}, "PASS", "segments"),
    (main_matriz.probe_get_all_instruments, ...),
    # ... 16 more
]

@pytest.mark.parametrize("probe,url,response,expected_status,detail_sub", _PROBE_FIXTURES)
def test_matriz_probe_envelope_shape_preserved(probe, url, response, expected_status, detail_sub,
                                                httpx_mock: HTTPXMock):
    matriz_client.configure(token="sentinel", token_expires_at=9_999_999_999.0,
                            base_url="https://api.test", username="u", password="p")
    httpx_mock.add_response(url=url, json=response)
    result, _payload = probe()
    assert result.status == expected_status
    assert detail_sub in result.detail
```

**Adaptation notes:**
- Inline canned payloads (small) — Phase 6 06-02-PLAN.md established this idiom over JSON-fixture-files.
- 2 risk probes assertion must explicitly test `envelope_key=None` path (no envelope unwrap) — these are the failure-mode probes.
- The 3 honesty-flagged probes (`probe_get_instruments_by_cfi_sanity`, `probe_get_market_data`, side-effect setters) have complex logic that may NOT fit the helper exactly — research recommends keeping them custom + snapshot test mocking them at the same level as the others. Planner decides exact split (research §Pattern 7 honesty flag).

---

### 10. Per-package `tests/test_core.py` (×4) — unit tests for builders/parsers

**Role:** Each `tests/test_core.py` tests the per-package `_core.py` in isolation: `build_<endpoint>_request` returns correct `RequestSpec` shape; `parse_<endpoint>_response` correctly decodes canned `httpx.Response`. Pure unit tests, no transport involvement.

**Closest analog (fixture style):** `packages/<pkg>/tests/conftest.py` autouse fixture pattern + `packages/<pkg>/tests/test_client_class.py` (test class structure + assertion style).

**Excerpt — conftest autouse fixture (matriz)** (`packages/matriz-client/tests/conftest.py:19-42`):

```python
@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    """Configura creds dummy y precarga un token cacheado."""
    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    yield
    matriz_client.configure(
        base_url="https://api.test",
        username="",
        password="",
    )
```

**Excerpt — URL-encoding quirk assertion idiom (higyrus)** (`packages/higyrus-client/tests/test_client_class.py:340-352`):

```python
    assert "fechaHasta=07/06/2026" in query_str
    assert "%2F" not in query_str
```

**Target `tests/test_core.py` shape (higyrus example — URL-encoding quirk):**

```python
"""Unit tests for higyrus_client._core builders/parsers (Phase 7 REFAC-03)."""
from __future__ import annotations
import datetime as dt
import httpx

from higyrus_client import _core
from higyrus_client._state import _ClientState


def test_build_get_movimientos_request_preserves_slash_in_query() -> None:
    state = _ClientState(base_url="https://api.test", token="t")
    spec = _core.build_get_movimientos_request(
        state, "A1", dt.date(2026, 6, 1), dt.date(2026, 6, 7),
    )
    assert spec.method == "GET"
    # Phase 6 URL-encoding quirk preserved by builder (Higyrus IIS rechaza %2F):
    assert "fechaHasta=07/06/2026" in spec.path  # or spec.url_pre_encoded
    assert "%2F" not in spec.path


def test_parse_get_movimientos_response_returns_list_on_204() -> None:
    resp = httpx.Response(204, content=b"")
    result = _core.parse_get_movimientos_response(resp)
    assert result == []
```

**Adaptation notes:**
- The autouse fixture from `conftest.py` will load even in `test_core.py` — `_core` does not depend on default-client state but tests using `_ClientState()` directly bypass it. mypy strict still applies (`disallow_untyped_defs = true`).
- Per CONVENTIONS.md, test files start with `from __future__ import annotations`.

---

### 11. `main_matriz.py` `_envelope_probe` helper (CR-05 close)

**Role:** Driver-only helper en `main_matriz.py` que dedupea las 18 sweep probes. Signature `_envelope_probe(name, path, *, envelope_key=None, model_from_api=None, ...)`. Las 2 risk probes pasan `envelope_key=None` (D-07).

**Closest analog (current — `probe_get_segments` shape to dedup):** `main_matriz.py:300-350` — el "anchor" probe. Casi todas las otras 17 probes son copias del shape:

```text
def probe_get_<name>() -> tuple[ProbeResult, <payload type>]:
    if _auth_failed:
        return (ProbeResult("get_<name>", "SKIPPED", f"auth failed: {_auth_failure_reason}"), None)
    base_url = primary.client._base_url
    path = "/rest/<...>"
    try:
        raw = _matriz_request("GET", path, params={...})
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(_PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                       title=f"get_<name> levantó PrimaryAPIError inesperado", ...)
        return (ProbeResult("get_<name>", "FINDING", f"{fid} (OPEN)"), None)
    payload = raw.get("<envelope_key>")
    if not isinstance(payload, list):  # or dict for some
        fid = _next_fid()
        append_finding(_PKG, fid=fid, class_="SHAPE", surface="sync", status="OPEN", ...)
        return (ProbeResult("get_<name>", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("get_<name>", "PASS", f"{len(payload)} items"), payload)
```

**Excerpt — current `probe_get_segments`** (`main_matriz.py:300-350`):

```python
def probe_get_segments() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 2 (D-MATZ-29 #2): ``GET /rest/segment/all``.

    Setea ``_resolved_segment`` = ``segments[0].marketSegmentId`` (D-MATZ-2).
    """
    global _resolved_segment
    if _auth_failed:
        return (
            ProbeResult("get_segments", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = primary.client._base_url
    path = "/rest/segment/all"
    try:
        raw = _matriz_request("GET", path)
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_segments levantó PrimaryAPIError inesperado",
            expected="200 OK con envelope {segments: [...]}",
            actual=f"PrimaryAPIError: {exc}",
            diff="error de upstream o envelope key ausente",
            base_url=base_url,
        )
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)
    segments = raw.get("segments")
    if not isinstance(segments, list):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_segments envelope shape incorrecto",
            expected="raw['segments'] es list",
            actual=f"raw['segments']={type(segments).__name__}",
            diff="envelope key 'segments' ausente o no-list",
            base_url=base_url,
        )
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)
    if segments and isinstance(segments[0], dict):
        seg_id = segments[0].get("marketSegmentId")
        if isinstance(seg_id, str):
            _resolved_segment = seg_id
    return (ProbeResult("get_segments", "PASS", f"{len(segments)} segments"), segments)
```

**Target Phase 7 `_envelope_probe` helper signature (RESEARCH.md Pattern 7):**

```python
def _envelope_probe(
    name: str,
    path: str,
    *,
    envelope_key: str | None = None,
    model_from_api: Callable[[Any], Any] | None = None,
    request_params: dict[str, Any] | None = None,
    auth_basic_fn: Callable[[], tuple[str, str]] | None = None,
) -> tuple[ProbeResult, Any | None]:
    """Sweep probe helper: GET path, optionally unwrap envelope_key, emit ProbeResult.

    envelope_key=None preserves risk probes (D-07): payload root IS the result dict.
    """
```

**Migration map (18 probes — RESEARCH.md Pattern 7):**

- 13 clean probes → migrated to `_envelope_probe(envelope_key="segments|instruments|orders|trades|marketData|positions|order")`.
- 2 risk probes (`probe_get_detailed_positions`, `probe_get_account_report`) → `envelope_key=None`.
- 3 honesty-flagged custom (planner decides): `probe_get_instruments_by_cfi_sanity` (loops over 8 CFI codes), `probe_get_market_data` (market-hours guard), side-effect setters (`_resolved_symbol`/`_resolved_segment`). **Recommendation:** keep these 3 custom + migrate the remaining 15 cleanly. Snapshot test covers all 18 regardless.

---

### 12. `pyproject.toml` — `import-linter` config

**Role:** Add `import-linter>=2.11,<3` to `[dependency-groups] dev` + add `[tool.importlinter]` config with 4 `forbidden` contracts (one per package: `<pkg>._core` forbids `<pkg>.client` and `<pkg>.aio`).

**Closest analog (TOML section idiom):** `pyproject.toml:23-32` (`[dependency-groups]`) for the dep addition; `pyproject.toml:37-66` (`[tool.ruff]` + `[tool.ruff.lint]`) for the `[tool.X]` section idiom; `pyproject.toml:71-85` (`[tool.mypy]` strict mode w/ `files = [...]`) for the per-package `files` listing.

**Excerpt — current `[dependency-groups] dev`** (`pyproject.toml:23-32`):

```toml
[dependency-groups]
dev = [
    "ruff>=0.7",
    "mypy>=1.13",
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "pytest-asyncio>=0.24",
    "pytest-httpx>=0.34",
    "pre-commit>=4.0",
]
```

**Excerpt — current `[tool.ruff]` section shape** (`pyproject.toml:37-50`):

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
src = ["packages/*/src", "packages/*/tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "SIM", "RUF", "ASYNC", "PIE", "PT", "RET", "TID"]
ignore = ["E501"]
```

**Target Phase 7 additions:**

```toml
[dependency-groups]
dev = [
    "ruff>=0.7",
    "mypy>=1.13",
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "pytest-asyncio>=0.24",
    "pytest-httpx>=0.34",
    "pre-commit>=4.0",
    "import-linter>=2.11,<3",  # NUEVO: Phase 7 REFAC-03 enforcement
]

# ... (otras secciones) ...

# ---------------------------------------------------------------------------
# import-linter: bloquea _core.py → client.py/aio.py imports (Phase 7 D-09).
# ---------------------------------------------------------------------------
[tool.importlinter]
root_packages = [
    "ambito_financiero_client",
    "iol_client",
    "higyrus_client",
    "matriz_client",
]

[[tool.importlinter.contracts]]
name = "ambito_financiero_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["ambito_financiero_client._core"]
forbidden_modules = ["ambito_financiero_client.client", "ambito_financiero_client.aio"]

[[tool.importlinter.contracts]]
name = "iol_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["iol_client._core"]
forbidden_modules = ["iol_client.client", "iol_client.aio"]

[[tool.importlinter.contracts]]
name = "higyrus_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["higyrus_client._core"]
forbidden_modules = ["higyrus_client.client", "higyrus_client.aio"]

[[tool.importlinter.contracts]]
name = "matriz_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["matriz_client._core"]
forbidden_modules = ["matriz_client.client", "matriz_client.aio"]
```

---

### 13. `.github/workflows/ci.yml` — `lint-imports` step

**Role:** New step in the `lint` job (or new job): `uv run lint-imports` after `uv sync`. Fails CI if any `_core.py → client.py/aio.py` import lands.

**Closest analog:** `.github/workflows/ci.yml:23-39` — `lint` job with `ruff check` + `ruff format --check` steps. Add `lint-imports` as a 3rd step. Plan 1 (D-12) can either add to existing `lint` job (simpler — keeps single job for "linting") or add a new job `lint-imports` (clearer in CI UI). Preferencia operacional: **add to existing `lint` job** as a step (research SUMMARY recommendation).

**Excerpt — current `lint` job** (`.github/workflows/ci.yml:23-39`):

```yaml
jobs:
  lint:
    name: Lint y formato (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Instalar uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - name: Verificar uv.lock sincronizado
        run: uv lock --check
      - name: Sync workspace
        run: uv sync --all-packages --all-extras --dev --frozen
      - name: ruff check
        run: uv run ruff check .
      - name: ruff format --check
        run: uv run ruff format --check .
```

**Target Phase 7 addition (append to `lint` job steps):**

```yaml
      - name: import-linter (boundary enforcement, Phase 7 REFAC-03)
        run: uv run lint-imports
```

**Honesty flag:** the job name `Lint y formato (ruff)` will become slightly misleading once `lint-imports` is added. Planner may either rename to `Lint y formato (ruff + import-linter)` or split into 2 jobs. Either is acceptable per D-09.

---

## Shared Patterns

### Module-level docstring + `from __future__ import annotations`

**Source:** CONVENTIONS.md §"Code Style" + `packages/<pkg>/src/<pkg>/_state.py:1-30`
**Apply to:** Every new `_core.py` (×4); every new `tests/test_core.py` (×4); both new `verification/*.py` files.

```python
"""<one-line module purpose>.

<longer description with sections, env vars, usage examples as ``::``
blocks, references to phase decisions D-XX>.
"""

from __future__ import annotations
```

### Section dividers `# ---...---`

**Source:** `packages/matriz-client/src/matriz_client/client.py:86-88, 117-119, 199-201, 209-211, 247-249, 300-301, 306-307, 342-343, 454-455, 507-508`
**Apply to:** Every new `_core.py` (group RequestSpec, helpers, auth-flow, per endpoint-group builders/parsers).

```python
# ------------------------------------------------------------------
# <Section name>
# ------------------------------------------------------------------
```

### `__all__` listing pattern

**Source:** `packages/iol-client/src/iol_client/_state.py:40-45` + `packages/matriz-client/src/matriz_client/client.py:59-83`
**Apply to:** Every new `_core.py` (lists `RequestSpec` + all `build_*` + all `parse_*` + `raise_for_response` + matriz `unwrap`).

```python
__all__ = [
    "DEFAULT_BASE_URL",
    "_REQUEST_TIMEOUT",
    "_TOKEN_TTL_BUFFER_SECONDS",
    "_ClientState",
]
```

### B8 alias preservation (D-04 critical)

**Source:** `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py:55-60` + test `packages/higyrus-client/tests/test_client_class.py:359-369`
**Apply to:** All 3 paquetes con auth (iol, higyrus, ambito) — both `client.py` and `aio.py` alias from `_core.py`. matriz `client.py` aliases `_unwrap` from `_core.py`.

```python
from <pkg> import _core
_raise_for_response = _core.raise_for_response  # D-04 — preserves B8 identity
# matriz only:
_unwrap = _core.unwrap
```

### PEP 562 shim untouched (Phase 6 D-01..D-04)

**Source:** `packages/matriz-client/src/matriz_client/client.py:726-754` (matriz shim + denied names) + `packages/ambito-financiero-client/src/ambito_financiero_client/client.py:261-271` (ambito shim — only `_client` forwarded).
**Apply to:** Phase 7 does NOT touch `__getattr__` in any module. The shim is a closed invariant; aliases like `_raise_for_response` are normal module-level attributes (accessed BEFORE the shim runs).

### Test fixture autouse (conftest.py) — unchanged

**Source:** `packages/<pkg>/tests/conftest.py` for all 4 paquetes
**Apply to:** Phase 7 does NOT modify per-package `conftest.py`. The `configure(token=..., token_expires_at=...)` autouse fixture established in Phase 6 already covers all use cases.

### Sentinel naming convention (D-12 Phase 6 / D-10 Phase 7)

**Source:** `packages/iol-client/tests/test_fixture_reaches_production.py:37` (`"SYNC-sentinel-iol"`), `packages/matriz-client/tests/test_fixture_reaches_production.py:40` (`"SYNC-sentinel-matriz"`)
**Apply to:** `verification/test_sync_async_isolation.py` MUST use `f"SYNC-sentinel-{pkg_name}"` and `f"ASYNC-sentinel-{pkg_name}"` exactly. This is the convention locked in Phase 6 D-12 / specifics.

### Honest error reporting / docstring purpose section

**Source:** CONVENTIONS.md §"Comments" — "Every module has a module-level docstring describing: purpose, API usage examples (as `::` code blocks), environment variables, and any auth flow specifics"
**Apply to:** Every new module (`_core.py`, `test_core.py`, `verification/test_sync_async_isolation.py`, `verification/test_matriz_sweep_snapshot.py`) MUST start with this docstring shape.

---

## No Analog Found

All 24 files have at least a role-match analog. Specifically, all new files reuse Phase 6 idioms or pre-existing repo patterns. Nothing in Phase 7 requires inventing a pattern de novo.

Closest "weaker analog" notes:

| File | Analog quality | Compensation |
|------|----------------|--------------|
| `pyproject.toml` `[tool.importlinter]` block | role-match (TOML section idiom, but `import-linter` config is new to this repo) | RESEARCH.md `## Standard Stack` cites official docs (import-linter.readthedocs.io v2.7+) with verified `forbidden` contract type spec; planner can copy from there. |
| `verification/test_matriz_sweep_snapshot.py` parametrize over 18 probes with canned payloads | role-match (combines `verification/test_public_surface.py` parametrize sweep + `test_fixture_reaches_production.py` httpx_mock idiom) | Both component patterns exist; the only new thing is combining them. RESEARCH.md §Pattern 7 honesty flag covers the 3 probes that don't fit the helper exactly. |
| `_envelope_probe` helper in `main_matriz.py` | role-match (no driver helper of this exact shape exists today — current 18 probes are all bespoke) | The shape comes from the 13 mostly-identical probes themselves (`probe_get_segments` is the anchor at line 300-350). RESEARCH.md §Pattern 7 documents the signature. |

---

## Metadata

**Analog search scope:**
- `packages/<pkg>/src/<pkg>/_state.py` (×4) — Phase 6 module shape baseline
- `packages/<pkg>/src/<pkg>/client.py` (×4) — current code to collapse
- `packages/<pkg>/src/<pkg>/aio.py` (×3 + 1 stub) — current async code to collapse (matriz untouched)
- `packages/<pkg>/tests/conftest.py` (×4) — fixture conventions
- `packages/<pkg>/tests/test_client_class.py` (×4) — test class idiom + B8 identity assertion
- `packages/<pkg>/tests/test_fixture_reaches_production.py` (×4) — pytest-httpx sentinel guard idiom
- `verification/test_public_surface.py` — cross-package parametrize sweep
- `main_matriz.py` lines 300-1402 — 18 probes inventory (3 risk + 15 envelope)
- `pyproject.toml` — TOML section shape (`[dependency-groups]`, `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`)
- `.github/workflows/ci.yml` — `lint` job step shape

**Files scanned:** ~26 source files + ~12 test files + 2 config files = 40 files total.

**Pattern extraction date:** 2026-06-12

**Phase 7 next step:** `gsd-planner` consumes this PATTERNS.md to produce 6 PLAN.md files (D-12). Each plan's action section references the specific analog file + line range listed above and copies the excerpt as the "look like this" anchor. The atomic Plan 5 (matriz REFAC-03 + CR-03 + CR-05) references Patterns 3, 6, 7, 11 simultaneously.
