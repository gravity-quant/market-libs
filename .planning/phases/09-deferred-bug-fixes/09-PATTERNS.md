# Phase 9: Deferred Bug Fixes - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 11 (5 NEW, 4 MODIFIED, 2 UPDATED findings)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/iol-client/tests/test_refresh_token_lifecycle.py` | test (sync, regression) | request-response (mocked HTTP) | `packages/iol-client/tests/test_client.py:154-251` | exact (same idiom, same flow tested) |
| `packages/iol-client/tests/test_refresh_token_lifecycle_async.py` | test (async, regression) | request-response (mocked HTTP) | `packages/iol-client/tests/test_async_client.py:116-199` | exact (mirror del sync analog) |
| `packages/iol-client/src/iol_client/_state.py` (MODIFY: remove `account_id`) | model/config (per-instance state) | n/a (field cleanup) | `packages/higyrus-client/src/higyrus_client/_state.py:97-98` | exact (mismo field forward-declared) |
| `packages/higyrus-client/src/higyrus_client/_state.py` (MODIFY: remove `account_id`) | model/config (per-instance state) | n/a (field cleanup) | `packages/iol-client/src/iol_client/_state.py:84` | exact (mismo field forward-declared) |
| `packages/higyrus-client/tests/test_multi_account.py` | test (sync, regression) | request-response (mocked HTTP loop) | `packages/higyrus-client/tests/test_client.py:135-145` (`test_get_movimientos_serializa_fechas_dd_mm_yyyy`) | exact (mismo endpoint + idiom mock URL exacta) |
| `packages/higyrus-client/tests/test_listado_cuentas_regression.py` (CONDITIONAL bucket (c)) | test (sync, regression) | request-response (mocked HTTP) | `packages/higyrus-client/tests/test_client.py:130-132, 164-175` | exact (mismo endpoint envelope idiom) |
| `main_higyrus.py` (EXTEND: `probe_multi_account_iteration` + `HIGYRUS_SAMPLE_CUENTAS`) | driver (probe live) | request-response (live HTTP) | `main_higyrus.py:138-140` (env var) + `main_higyrus.py:657-746` (probe shape) | exact (mismo driver, idiom existente) |
| `packages/matriz-client/src/matriz_client/_core.py` (MODIFY: hybrid guard) | service (builder, pre-HTTP) | request-response (pure builder) | `packages/matriz-client/src/matriz_client/_core.py:423-441` (existing builder + parser) | exact (mismo sitio + builder idiom) |
| `packages/matriz-client/tests/test_core.py` (EXTEND: parametric CFI test) | test (sync, validation) | pure-function (no HTTP) | `packages/matriz-client/tests/test_core.py:106-120` (existing param tests) | exact (mismo archivo + paramétrico idiom) |
| `.planning/verification/matriz-client-findings.md` (UPDATE F-09) | doc (findings update) | n/a (manual edit) | `.planning/verification/higyrus-client-findings.md:20-27` (F-01 Resolution pattern) | exact (Resolution: idiom Phase 5 Op A) |
| `.planning/verification/higyrus-client-findings.md` (UPDATE F-02) | doc (findings update) | n/a (manual edit) | `.planning/verification/higyrus-client-findings.md:29-36` (F-02 current OPEN) | exact (self-update con bucket marker) |
| `.planning/phases/09-deferred-bug-fixes/09-VALIDATION.md` | doc (CI evidence) | n/a (markdown) | Previous phases VALIDATION (Phase 6/7/8 estructura) | role-match (VALIDATION.md de fases anteriores) |

## Pattern Assignments

### `packages/iol-client/tests/test_refresh_token_lifecycle.py` (test, sync regression)

**Analog:** `packages/iol-client/tests/test_client.py:154-251`

**Imports pattern** (lines 1-11):

```python
"""Smoke tests del cliente sincrónico de IOL (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import IOLAuthError, IOLRateLimitError
```

Para BUG-03 el module docstring debe describir los 4 paths del lifecycle. Mantener `from __future__ import annotations` mandatory (CONVENTIONS.md).

**Autouse fixture (via conftest.py — NO modificar)** (`conftest.py:25-38`):

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
    iol_client.client._get_default().close()
    iol_client.configure(base_url="https://api.test", username="", password="")
```

El autouse precarga `token="test-token"`. **Cada test del Plan 09-01 debe mutar `state.token=None`, `state.token_expires_at=0.0`, `state.refresh_token=<seed>` explícitamente al inicio** para forzar el flow del refresh (Pitfall 6 RESEARCH.md).

**Core pattern — Path 1 (refresh→success) — copy literal of `test_refresh_token_success_path:154-186`:**

```python
def test_refresh_token_success_path(httpx_mock: HTTPXMock) -> None:
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-cached"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-cached&grant_type=refresh_token",
        json={
            "access_token": "tok-after-refresh",
            "refresh_token": "refresh-rotated",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    assert iol_client.client._token == "tok-after-refresh"
    assert iol_client.client._refresh_token == "refresh-rotated"
```

Plan 09-01 path 1 es exactamente esto — quizás expandir con `assert len(httpx_mock.get_requests()) == 2` para validar conteo explícito (research path 1).

**Core pattern — Path 2 (refresh→401→password fallback) — copy `test_refresh_fails_falls_back_to_password:189-223`:**

```python
def test_refresh_fails_falls_back_to_password(httpx_mock: HTTPXMock) -> None:
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-stale"

    # 1. Refresh attempt → 401
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-stale&grant_type=refresh_token",
        status_code=401,
        text="invalid_grant",
    )
    # 2. Fallback al password grant → success
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        json={
            "access_token": "tok-from-password",
            "refresh_token": "refresh-fresh",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    assert iol_client.client._token == "tok-from-password"
    assert iol_client.client._refresh_token == "refresh-fresh"
```

`match_content=b"..."` distingue los 2 mocks por body (Pitfall 3 RESEARCH.md). Plan 09-01 path 2 es exactamente esto.

**Paths 3 + 4 (CR-01 conditional rotation):**

Tests NEW — no hay analog literal del CR-01 conditional branch en test_client.py existente. RESEARCH.md §"Common Operation 2" (líneas 644-700) provee el template literal. Reusar el mismo idiom de paths 1+2: setup → mock refresh response (con o sin `refresh_token` field) → invoke endpoint → assert `state.refresh_token` preserved (path 3) o rotated (path 4).

**Existing pattern accesa `state` via `_get_default()._state`** (Phase 6 Pitfall #1):

```python
state = iol_client.client._get_default()._state  # NOT iol_client.client._token = ...
state.token = None
state.refresh_token = "seed-X"
```

El shim PEP 562 es read-only — escrituras deben hit `_state` directamente. Esto es **load-bearing** para todos los 8 tests del Plan 09-01 (`packages/iol-client/tests/conftest.py:1-13` documenta este pitfall).

---

### `packages/iol-client/tests/test_refresh_token_lifecycle_async.py` (test, async regression)

**Analog:** `packages/iol-client/tests/test_async_client.py:116-199`

**Imports pattern** (lines 1-11 of analog):

```python
"""Smoke tests del cliente asincrónico de IOL (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from iol_client import IOLAuthError, aio
```

Note: `from iol_client import ... aio` (NOT `import iol_client.aio`); luego accesar como `aio.<func>`.

**Autouse async fixture** (`conftest.py:41-52`):

```python
@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    yield
    await aio._get_default().aclose()
    aio.configure(base_url="https://api.test", username="", password="")
```

Nota: el async usa `aclose()` (await) en teardown — el aclose idiom para `AsyncClient` (Pitfall 6 cleanup).

**Async test pattern — Path 1 mirror — copy `test_async_refresh_token_success_path:116-148`:**

```python
async def test_async_refresh_token_success_path(httpx_mock: HTTPXMock) -> None:
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-cached"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-cached&grant_type=refresh_token",
        json={
            "access_token": "tok-after-refresh",
            "refresh_token": "refresh-rotated",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    await aio.get_instruments("argentina")

    assert aio._token == "tok-after-refresh"
    assert aio._refresh_token == "refresh-rotated"
```

Diferencias clave vs sync:
- `async def test_...` con `await aio.<func>()`
- `state = aio._get_default()._state` (NO `iol_client.client.<state>`)
- Reads via `aio._token` / `aio._refresh_token` (PEP 562 read-only shim)
- `pytest-asyncio` autodetect (`asyncio_mode = "auto"` global — no decorador necesario)

**Token-lock awareness (Phase 6 D-IOL-09):** El `_ensure_token()` async usa double-checked locking con `state.token_lock` (un `asyncio.Lock`). Los tests NO ejercitan concurrencia (basta con single-task), pero el flujo de refresh dentro del lock es lo que valida la regression.

---

### `packages/iol-client/src/iol_client/_state.py` (MODIFY: remove `account_id`)

**Analog (cross-package twin):** `packages/higyrus-client/src/higyrus_client/_state.py:97-98`

**Imports/header NO cambia.** Mantener `from __future__ import annotations`.

**Existing field declaration to REMOVE** (`_state.py:81-84`):

```python
    refresh_token: str | None = None
    # Forward-declared for Phase 9 BUG-04 (multi-account iteration). Not
    # populated in Phase 6 but kept in the schema for cross-package shape
    # consistency with higyrus.
    account_id: str | None = None
```

Plan 09-02 D-09:
- DELETE las líneas 81-84 (los 3 comment lines + el `account_id:` line).
- DEJAR `refresh_token: str | None = None` intacto en la línea 80.

**Existing docstring to UPDATE** (`_state.py:25-29`):

```python
The ``refresh_token`` and ``account_id`` fields are forward-declared for
schema consistency across packages (RESEARCH.md Per-Package Divergence
Matrix). Phase 6 ``Client.__init__`` does NOT accept them as kwargs
(D-13). ``refresh_token`` is mutated by ``Client.login()`` / ``_refresh()``
internally; ``account_id`` is populated by Phase 9 BUG-04.
```

Cambiar a:

```python
The ``refresh_token`` field is forward-declared for schema consistency
across packages (RESEARCH.md Per-Package Divergence Matrix). Phase 6
``Client.__init__`` does NOT accept it as a kwarg (D-13).
``refresh_token`` is mutated by ``Client.login()`` / ``_refresh()``
internally.
```

(Quitar las 2 menciones de `account_id` + frase "populated by Phase 9 BUG-04".)

**CRITICAL — NO tocar (cross-cutting, diferente field):**

`packages/iol-client/src/iol_client/_transport.py:133-188` y `_atransport.py:66-121` leen `request.extensions["account_id"]` — esto es Phase 8 D-11 log correlation **distinto** del `_state.account_id`. **NO se toca**. Pitfall 1 RESEARCH.md.

---

### `packages/higyrus-client/src/higyrus_client/_state.py` (MODIFY: remove `account_id`)

**Analog (cross-package twin):** `packages/iol-client/src/iol_client/_state.py:80-84`

**Existing field declaration to REMOVE** (`_state.py:96-98`):

```python
    token_expires_at: float = 0.0
    # Forward-declared for Phase 9 BUG-04 (multi-account iteration).
    account_id: str | None = None
```

Plan 09-02 D-09:
- DELETE líneas 97-98 (comment + field).
- DEJAR `token_expires_at: float = 0.0` intacto en línea 96.

**Existing docstring to UPDATE** (`_state.py:36-37`):

```python
- ``account_id``: forward-declared for Phase 9 BUG-04 (multi-account
  iteration). Unused in Phase 6.
```

Remover las 2 líneas completas. Quedan solo las menciones de los demás campos (`token`, `token_expires_at`, `http_client`, `token_lock`).

**CRITICAL — NO tocar (cross-cutting, diferente field):**

- `packages/higyrus-client/src/higyrus_client/_core.py:117, 132` (`RequestSpec.account_id` — Phase 8 D-11).
- `packages/higyrus-client/src/higyrus_client/_core.py:310, 353, 408` (builders que setean `account_id=id_cuenta` en `RequestSpec`).
- `packages/higyrus-client/src/higyrus_client/_transport.py:173-193`, `_atransport.py:102-121` (transport lee `request.extensions["account_id"]` para log correlation).
- `packages/higyrus-client/tests/test_transport.py:33-258` y `test_logging.py:166-177` (D-11 tests).

Esos son **otro field** y se quedan. Pitfall 1 RESEARCH.md.

---

### `packages/higyrus-client/tests/test_multi_account.py` (test, mocked 2-cuentas)

**Analog:** `packages/higyrus-client/tests/test_client.py:135-145` (`test_get_movimientos_serializa_fechas_dd_mm_yyyy`)

**Imports pattern** (líneas 1-12 de test_client.py — copy estructura, dropear no usados):

```python
"""Tests del cliente sincrónico de higyrus (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client
```

**Autouse fixture (via conftest.py — NO modificar):** ya configura `token="test-token"`, `token_expires_at=9_999_999_999.0` (`packages/higyrus-client/tests/conftest.py:22-34`). NO tocar.

**Core pattern — single-account mock URL idiom (analog):**

```python
def test_get_movimientos_serializa_fechas_dd_mm_yyyy(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/123/movimientos?fechaDesde=01%2F01%2F2026&fechaHasta=31%2F01%2F2026",
        json=[],
    )
    movs = higyrus_client.get_movimientos(
        id_cuenta="123",
        fecha_desde=dt.date(2026, 1, 1),
        fecha_hasta=dt.date(2026, 1, 31),
    )
    assert movs == []
```

**Extended pattern — Plan 09-02 multi-account loop (RESEARCH.md §"Common Operation 3"):**

```python
def test_multi_account_iteration_via_per_call_id_cuenta(
    httpx_mock: HTTPXMock,
) -> None:
    """BUG-04: iterate over ≥2 cuentas y assert wire requests targetean correctamente."""
    for acct in ("5208", "9999"):
        httpx_mock.add_response(
            method="GET",
            url=(
                f"https://api.test/api/cuentas/{acct}/movimientos"
                f"?fechaDesde=2026-06-13&fechaHasta=2026-06-13"
            ),
            json=[],
        )

    today = dt.date(2026, 6, 13)
    for acct in ("5208", "9999"):
        higyrus_client.get_movimientos(
            id_cuenta=acct,
            fecha_desde=today,
            fecha_hasta=today,
        )

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert "/5208/" in str(requests[0].url)
    assert "/9999/" in str(requests[1].url)
```

**CRITICAL — formato fecha:** El analog `test_get_movimientos_serializa_fechas_dd_mm_yyyy` muestra el wire format DD%2FMM%2FYYYY (URL-encoded `01/01/2026`). El research template usa `YYYY-MM-DD` (`2026-06-13`) que **NO matchea** el wire actual de higyrus. **Verificar al planificar:** Plan 09-02 debe usar el formato real `DD%2FMM%2FYYYY` (verificable en `_params.py::format_date`); de lo contrario, `httpx_mock` reportará "request did not match" en el primer call.

---

### `packages/higyrus-client/tests/test_listado_cuentas_regression.py` (CONDITIONAL — bucket (c) only)

**Analog:** `packages/higyrus-client/tests/test_client.py:130-132, 164-175`

**Existing happy-path pattern** (`test_client.py:164-175`):

```python
def test_get_listado_cuentas_url_con_estado_alta(httpx_mock: HTTPXMock) -> None:
    """Phase 4: locking URL exacta de get_listado_cuentas con estado=alta (HIGY-02)."""
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        method="GET",
        json=[{"id": "CTA-001", "titular": "<x>", "denominacion": "<y>"}],
    )
    cuentas = higyrus_client.get_listado_cuentas(estado="alta")
    assert isinstance(cuentas, list)
    assert len(cuentas) == 1
    assert isinstance(cuentas[0], Cuenta)
    assert cuentas[0].id == "CTA-001"
```

**Contract guard pattern (bucket b/c)** — el test verifica que **si** el server devuelve N cuentas, el cliente las propaga (no las descarta). Para bucket (c), agregar setup que reproduzca el client-side bug pre-fix y assert el comportamiento post-fix.

**Empty list path** (`test_client.py:130-132`):

```python
def test_get_listado_cuentas_204_devuelve_lista_vacia(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=204)
    assert higyrus_client.get_listado_cuentas() == []
```

Este es el guard del happy "empty" path — sirve para asegurar que `204 No Content` retorna `[]` correctamente (no levanta excepción, no devuelve `None`).

**Default action:** Si BUG-02 triage produce bucket (a) o (b), este archivo **NO se crea**. Se extiende `test_client.py` con UN test happy-path adicional ("returned cuentas count is preserved") como contract guard. Solo bucket (c) crea archivo separado para aislar el repro del client-side bug.

---

### `main_higyrus.py` (EXTEND: `probe_multi_account_iteration` + `HIGYRUS_SAMPLE_CUENTAS`)

**Analog:** `main_higyrus.py:138-140` (env var read pattern) + `main_higyrus.py:657-746` (`probe_get_listado_cuentas_sync` shape)

**Env var read pattern** (línea 138-140):

```python
# D-HIGY-14: env vars opcionales para sample params.
_SAMPLE_CUENTA: str | None = os.getenv("HIGYRUS_SAMPLE_CUENTA")
_SAMPLE_TIPO_CUENTA: str = os.getenv("HIGYRUS_SAMPLE_TIPO_CUENTA", "propia")
_SAMPLE_NIVEL: str = os.getenv("HIGYRUS_SAMPLE_NIVEL", "detalle")
```

Plan 09-02 D-10: agregar:

```python
# Phase 9 D-10: CSV de cuentas para multi-account iteration probe (BUG-04).
# Override de cuentas resueltas por get_listado_cuentas si lista vacía.
_SAMPLE_CUENTAS_CSV: str = os.getenv("HIGYRUS_SAMPLE_CUENTAS", "")
```

**ProbeResult shape + try/except idiom** (líneas 195-200, 657-731):

```python
@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Resultado de un probe; agregado al summary final."""

    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str

def probe_get_listado_cuentas_sync() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 5: ``higyrus_client.get_listado_cuentas(estado="alta")`` (HIGY-02).
    ...
    """
    global _resolved_cuenta
    if _auth_failed:
        return (
            ProbeResult("get_listado_cuentas_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = higyrus_client.client._base_url
    try:
        raw = higyrus_client.client._request("GET", "/api/cuentas/listadoCuentas", params={"estado": "alta"})
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(_PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
                       title="...", expected="...", actual=repr(exc),
                       diff=f"status_code={exc.status_code!r}", base_url=base_url)
        return (ProbeResult("get_listado_cuentas_sync", "FINDING", f"{fid} (OPEN)"), None)
    ...
```

Plan 09-02 `probe_multi_account_iteration` debe seguir el mismo shape (auth-failed skip + try/except con AuthError/APIError/Exception + append_finding al detectar discrepancia).

**Multi-account probe template (research §"Pattern 4")** — adaptar al idiom del driver existente:

```python
def probe_multi_account_iteration() -> ProbeResult:
    """Probe N (BUG-04): iterate over ≥2 cuentas y ejerce endpoint account-dep."""
    if _auth_failed:
        return ProbeResult("multi_account_iteration", "SKIPPED",
                           f"auth failed: {_auth_failure_reason}")
    base_url = higyrus_client.client._base_url
    # Source 1: env var override (CSV).
    if _SAMPLE_CUENTAS_CSV.strip():
        cuentas = [c.strip() for c in _SAMPLE_CUENTAS_CSV.split(",") if c.strip()]
    else:
        # Source 2: live get_listado_cuentas() — si non-empty, primeras 2.
        try:
            live = higyrus_client.get_listado_cuentas(estado="alta")
        except Exception as exc:  # cualquier error → skip + finding opcional
            return ProbeResult("multi_account_iteration", "SKIPPED",
                               f"listado_cuentas failed: {exc!r}")
        cuentas = [c.id for c in live[:2]] if len(live) >= 2 else []
    if len(cuentas) < 2:
        return ProbeResult("multi_account_iteration", "SKIPPED",
                           "need >=2 cuentas; set HIGYRUS_SAMPLE_CUENTAS=A,B")
    today = dt.date.today()
    for acct in cuentas[:2]:
        try:
            higyrus_client.get_movimientos(
                id_cuenta=acct, fecha_desde=today, fecha_hasta=today,
            )
        except HigyrusAPIError as exc:
            fid = _next_fid()
            append_finding(_PKG, fid=fid, class_="ERROR-MAP", surface="sync",
                           status="OPEN", title=f"multi_account: get_movimientos({acct})",
                           expected="200 OK", actual=repr(exc),
                           diff=f"status={exc.status_code!r}", base_url=base_url)
            return ProbeResult("multi_account_iteration", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("multi_account_iteration", "PASS",
                       f"iterated {len(cuentas[:2])} cuentas successfully")
```

**Register en `_D_HIGY_10_ORDER` (línea 144-163):** agregar el nuevo probe al tuple `_D_HIGY_10_ORDER` y al lifecycle de `main()` para que aparezca en el summary.

**CRITICAL — orden global state:** el probe usa `_resolved_cuenta` global (`main_higyrus.py:179`) o `_SAMPLE_CUENTAS_CSV` — verificar que el nuevo probe corra **después** de `probe_get_listado_cuentas_sync` para que `live = get_listado_cuentas()` pueda fallar gracefully al caer fuera de auth/orden.

---

### `packages/matriz-client/src/matriz_client/_core.py` (MODIFY: hybrid guard)

**Analog:** `packages/matriz-client/src/matriz_client/_core.py:423-441` (existing builder + parser sin guard)

**Existing builder** (lines 423-441):

```python
def build_get_instruments_by_cfi_request(
    state: _ClientState,
    cfi_code: CFICode,
) -> RequestSpec:
    """``GET /rest/instruments/byCFICode?CFICode=...``."""
    return RequestSpec(
        method="GET",
        path="/rest/instruments/byCFICode",
        params={"CFICode": cfi_code},
        idempotent=True,
        endpoint_name="get_instruments_by_cfi",
    )


def parse_get_instruments_by_cfi_response(resp: httpx.Response) -> list[Instrument]:
    """Parse envelope ``{instruments: [...]}`` → ``list[Instrument]``."""
    path = "/rest/instruments/byCFICode"
    data = parse_envelope_response(resp, path)
    return [Instrument.from_api(i) for i in unwrap(data, "instruments", path)]
```

**Imports to ADD** (file header, after stdlib imports around líneas 40-50):

```python
import re
from typing import Any, get_args
```

Note: `Any` ya está importado; agregar `get_args`. `re` se importa nuevo después de `time`.

**Module-level constants to ADD** (después de los imports, antes del primer `__all__`):

```python
# BUG-01: hybrid Literal + ISO 10962 regex guard para CFI validation pre-HTTP.
# 9 valores del Literal (source of truth en types.py:50-61) + forward-compat
# para CFIs ISO 10962:2021 (6 mayúsculas A-Z) que aún no estén en el Literal.
_CFI_ISO_RE = re.compile(r"^[A-Z]{6}$")
_CFI_LITERAL_VALUES = frozenset(get_args(CFICode))
```

**Modified builder** (replace lines 423-434):

```python
def build_get_instruments_by_cfi_request(
    state: _ClientState,
    cfi_code: CFICode,
) -> RequestSpec:
    """``GET /rest/instruments/byCFICode?CFICode=...``.

    BUG-01: hybrid Literal + ISO 10962 regex guard. Si ``cfi_code`` no está en
    el Literal ``CFICode`` Y no matchea ``^[A-Z]{6}$`` (ISO 10962:2021),
    levanta ``PrimaryAPIError(status="ERROR")`` pre-HTTP. Reverse de F-09:
    pre-fix, CFI inválido pasaba al wire y el server lo aceptaba silenciosamente.

    Deviation D-02: el guard vive aquí (NO en ``raise_for_response``) porque
    el cfi_code solo es visible en el builder; ``raise_for_response`` recibe
    ``httpx.Response`` y no ve el param. La excepción levantada es la misma
    contractual que ``raise_for_response`` produciría — el probe driver
    ``probe_error_malformed_cfi`` captura PrimaryAPIError(status="ERROR") → PASS.
    """
    if cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.match(cfi_code):
        raise PrimaryAPIError(
            status="ERROR",
            description=f"CFI inválido: {cfi_code!r} (no está en CFICode Literal ni matchea ^[A-Z]{{6}}$)",
            message=None,
        )
    return RequestSpec(
        method="GET",
        path="/rest/instruments/byCFICode",
        params={"CFICode": cfi_code},
        idempotent=True,
        endpoint_name="get_instruments_by_cfi",
    )
```

**No cambia el parser** (`parse_get_instruments_by_cfi_response:437-441`).

**No cambia `client.py` ni `aio.py`** — single-site fix Phase 7 REFAC-03 propaga automático.

**PrimaryAPIError signature** (`exceptions.py:23`):

```python
def __init__(self, status: str, description: str | None = None, message: str | None = None):
```

Soporta `status="ERROR"`, `description=...`, `message=None` explícito.

---

### `packages/matriz-client/tests/test_core.py` (EXTEND: parametric CFI test)

**Analog:** `packages/matriz-client/tests/test_core.py:106-120` (existing parametric / `pytest.raises` tests for envelope/shape)

**Imports already present** (lines 13-23):

```python
from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from matriz_client import _core
from matriz_client._state import _ClientState
from matriz_client.exceptions import AuthenticationError, PrimaryAPIError
```

Todo lo necesario ya está. NO agregar `cast` (el test pasa strings via paramétrico; el `# type: ignore[arg-type]` es la forma idiomática vs `cast`).

**Core pattern — parametric pytest pattern (existing en archivo):**

El archivo ya tiene paramétricos al estilo `pytest.raises(PrimaryAPIError) as exc_info:` (líneas 84-95, 109-112, 115-120) — reusable directamente. Ejemplo del idiom existente:

```python
def test_parse_envelope_response_raises_on_non_dict_root() -> None:
    resp = _make_response(json_body=[1, 2, 3])
    with pytest.raises(PrimaryAPIError) as exc_info:
        _core.parse_envelope_response(resp, "/oops")
    assert "expected JSON object body" in (exc_info.value.description or "")
    assert "list" in (exc_info.value.description or "")
```

**Extended pattern — Plan 09-03 paramétrico BUG-01 (RESEARCH.md §"Pattern 5"):**

```python
@pytest.mark.parametrize(
    "cfi,expect_raise",
    [
        # Literal-known bucket (2 valores del Literal CFICode)
        ("ESXXXX", False),
        ("DBXXXX", False),
        # Regex forward-compat bucket (6 mayúsculas, NO en Literal)
        ("ABXXXX", False),
        ("ZQXXXX", False),
        # Malformed bucket
        ("INVALID-CFI", True),  # hyphen + len 11
        ("esxxxx", True),       # lowercase
        ("E2XXXX", True),       # digit
        ("ABCDE", True),        # len 5
        ("ABCDEFG", True),      # len 7
        ("", True),             # empty
    ],
)
def test_get_instruments_by_cfi_validates_cfi_code(
    cfi: str, expect_raise: bool
) -> None:
    state = _ClientState(base_url="https://api.example.com")
    if expect_raise:
        with pytest.raises(PrimaryAPIError) as exc_info:
            _core.build_get_instruments_by_cfi_request(state, cfi)  # type: ignore[arg-type]
        assert exc_info.value.status == "ERROR"
        assert "CFI inválido" in (exc_info.value.description or "")
    else:
        spec = _core.build_get_instruments_by_cfi_request(state, cfi)  # type: ignore[arg-type]
        assert spec.params == {"CFICode": cfi}
```

**No imports nuevos** — `_core`, `_ClientState`, `PrimaryAPIError` ya están en el header.

---

### `.planning/verification/matriz-client-findings.md` (UPDATE F-09)

**Analog:** `.planning/verification/higyrus-client-findings.md:20-27` (F-01 Resolution pattern Phase 5 Op A)

**Existing F-01 (higyrus) — Resolution: line idiom** (lines 20-27):

```markdown
### F-01 -- .posicion.disponibleAjustado: model declara, wire no emite (documentado FCI-conditional)

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `EXPECTED`

- **Expected:** model declara `disponibleAjustado: float`
- **Actual:** wire payload no incluye la key
- **Diff:** ...
- **Classification rationale (Phase 5):** ...
- **Resolution:** Documented behavior per `Posicion` docstring (`packages/higyrus-client/src/higyrus_client/models.py:197-199`): "..." Closure: SafeModel safe-access es by-design. Polish futuro candidato: ...
```

**Plan 09-03 flip pattern para F-09:**

Existing F-09 (`matriz-client-findings.md:98-105`):

```markdown
### F-09 -- get_instruments_by_cfi con CFI inválido NO levantó excepción

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `CONFIRMED`

- **Expected:** PrimaryAPIError mapeado para CFI inválido
- **Actual:** ninguna excepción; el cliente retornó normalmente
- **Diff:** upstream aceptó CFI no válido; revisar validación
- **Classification rationale (Phase 5):** Gap real en el error mapping del cliente. ...
```

**Convert to** (status flip + add Resolution + Regression):

```markdown
### F-09 -- get_instruments_by_cfi con CFI inválido NO levantó excepción

**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `FIXED`

- **Expected:** PrimaryAPIError mapeado para CFI inválido
- **Actual:** ninguna excepción; el cliente retornó normalmente (pre-Phase 9)
- **Diff:** upstream aceptó CFI no válido; revisar validación
- **Classification rationale (Phase 5):** Gap real en el error mapping del cliente. ...
- **Resolution:** Phase 9 Plan 09-03 BUG-01 — hybrid Literal + ISO 10962 regex guard agregado pre-HTTP en `build_get_instruments_by_cfi_request` (`packages/matriz-client/src/matriz_client/_core.py:423-441`). Deviation D-02 vs ROADMAP literal `_core.raise_for_response()`: el guard vive en el builder porque `raise_for_response` solo ve `httpx.Response` y no ve el `cfi_code` param; el contrato observable (`PrimaryAPIError(status="ERROR")`) se preserva. Live re-run de `main_matriz.py` confirma `probe_error_malformed_cfi` reporta PASS post-fix; `cycle_closure_matriz_client` flipea FAIL → PASS.
- **Regression:** `tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` (10 casos paramétricos cubriendo 3 buckets: literal-known × 2, regex forward-compat × 2, malformed × 6).
```

**Update Cycle Closure section** (lines 115-135):

- Findings by status (this package): cambiar `CONFIRMED` count de 1 → 0, agregar `FIXED` count de 0 → 1.
- Add a row to "Regression tests linked to FIXED/CONFIRMED findings" table con F-09 → test path.
- `verify_cycle_closure("matriz-client")` returned: **FAIL** → flip to **PASS** (en next baseline run).
- Missing regressions: F-09 → empty.

---

### `.planning/verification/higyrus-client-findings.md` (UPDATE F-02)

**Analog:** `.planning/verification/higyrus-client-findings.md:29-36` (existing F-02 OPEN + self-update target)

**Existing F-02:**

```markdown
### F-02 -- get_listado_cuentas(estado="alta") devuelve 0 cuentas (era 8771 en smoke pre-fase)

...
- **Resolution:** OPEN — investigación deferida fuera de scope de Phase 4. Candidato para polish post-milestone: reproducir el discrepancy con un script aislado que loguee headers + body sobre múltiples corridas, contactar a Higyrus support si reproducible, o aceptar como `NO-FIX (account-state-conditional)` si no se puede repro.
```

**Plan 09-02 outcome flip — 3 buckets posibles:**

**Bucket (a) NO-FIX transient:**

```markdown
- **Status:** `NO-FIX`
- **Resolution:** Phase 9 Plan 09-02 BUG-02 quick triage (bucket a) — re-corrido `main_higyrus.py` con `logging.getLogger("higyrus_client").setLevel(DEBUG)` probe-scoped. Outcome: ... [describir N runs, qué se observó, por qué se clasifica como transient]. Phase 8 D-01 RetryTransport amortigua transients 5xx/connection-error. Mocked regression test extendido como contract guard para detectar regresiones futuras del happy path.
- **Regression:** `tests/test_client.py::test_get_listado_cuentas_url_con_estado_alta` (existing happy-path contract guard) + Phase 8 retries cubren transient 5xx.
```

**Bucket (b) FIXED-by-environment:**

```markdown
- **Status:** `FIXED`
- **Resolution:** Phase 9 Plan 09-02 BUG-02 quick triage (bucket b) — re-corrido `main_higyrus.py` con DEBUG logging devolvió N cuentas non-empty. Root cause exterior al cliente (transient en el server-side o estado de cuenta cambió post-baseline). Mocked regression test extendido como guard contra futures regresiones del happy path client-side.
- **Regression:** `tests/test_client.py::test_get_listado_cuentas_url_con_estado_alta` (existing) + bucket (b) confirmado por live re-run.
```

**Bucket (c) Client-side fix:**

```markdown
- **Status:** `FIXED`
- **Resolution:** Phase 9 Plan 09-02 BUG-02 quick triage (bucket c) — re-corrido reprodujo 100% el `[]` pre-Phase-9. Root cause en `<archivo>:<línea>`: ... [describir bug en `_core.py`]. Fix en single-site: `<diff descripción>`. Live re-run post-fix devolvió N cuentas.
- **Regression:** `tests/test_listado_cuentas_regression.py::test_<name>` (new mocked test bloquea el bug).
```

**Convention reference:** los 3 buckets siguen el FINDINGS-TEMPLATE.md Phase 5 Op A (`Resolution:` + opcional `Regression:`).

---

### `.planning/phases/09-deferred-bug-fixes/09-VALIDATION.md` (NEW, green gate)

**Analog:** Prior phases VALIDATION.md (Phase 6/7/8 — structure with CI evidence + snapshot zero-diff + test count delta)

**No code analog necesario** — markdown doc-only. Contenido esperado per CONTEXT.md D-11 Plan 09-04:

1. Full pytest matrix output (Python 3.12 + 3.13).
2. Ruff check + format clean.
3. Mypy strict clean.
4. Import-linter contract (Phase 7 D-09) holds.
5. Cross-leak sentinel (Phase 7 D-10) green.
6. Public surface zero-diff (Phase 6 D-09 — esperado en BUG-01..04).
7. Tests count delta: ~755 (baseline Phase 8) + ~20 (Phase 9 new) ≈ ~775.
8. Operator checkpoint.

NO toca código de paquetes.

---

## Shared Patterns

### Pattern S1 — `from __future__ import annotations` mandatory en nuevos archivos

**Source:** CONVENTIONS.md + verificable en cualquier archivo del repo.

**Apply to:** TODOS los archivos NEW (`test_refresh_token_lifecycle.py`, `test_refresh_token_lifecycle_async.py`, `test_multi_account.py`, `test_listado_cuentas_regression.py` si bucket c).

```python
"""<docstring del módulo>."""

from __future__ import annotations

...
```

### Pattern S2 — `_get_default()._state` access pattern (Phase 6 Pitfall #1)

**Source:** `packages/iol-client/tests/test_client.py:154-165` y `tests/test_async_client.py:116-127` + `tests/conftest.py:1-13` (doc del pitfall).

**Apply to:** Plan 09-01 (8 tests sync + async). NO usar `monkeypatch.setattr(pkg.client, "_token", X)` — el PEP 562 shim es read-only; las escrituras hit el dict del módulo, no `_state`.

```python
state = iol_client.client._get_default()._state  # sync
# state = aio._get_default()._state              # async
state.token = None
state.token_expires_at = 0.0
state.refresh_token = "seed-X"
```

### Pattern S3 — `pytest-httpx match_content` distingue 2 grants en mismo URL

**Source:** `packages/iol-client/tests/test_client.py:171, 208` (uso en producción de Phase 6).

**Apply to:** Plan 09-01 path 2 (refresh→401→password fallback). Sin `match_content`, pytest-httpx consume mocks FIFO y los 2 grants colisionan (Pitfall 3 RESEARCH.md).

```python
httpx_mock.add_response(
    url="https://api.test/token",
    method="POST",
    match_content=b"refresh_token=<seed>&grant_type=refresh_token",
    status_code=401,
    text="invalid_grant",
)
httpx_mock.add_response(
    url="https://api.test/token",
    method="POST",
    match_content=b"username=u&password=p&grant_type=password",
    json={"access_token": "...", "refresh_token": "...", "expires_in": 900},
)
```

### Pattern S4 — Single-site fix en `_core.py` propaga a sync + async (Phase 7 REFAC-03)

**Source:** `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-CONTEXT.md` D-09 + cualquier builder en `_core.py`.

**Apply to:** Plan 09-03 (BUG-01 hybrid guard). El cambio en `build_get_instruments_by_cfi_request` propaga a `client.get_instruments_by_cfi` (sync) — matriz no tiene aio.py REST aún (Phase 10 territory). El idiom de fix single-site se respeta: no se duplica lógica.

### Pattern S5 — Module-level constants (compiled regex + frozen literals)

**Source:** Phase 7 REFAC-03 idiom + RESEARCH.md Pattern 1 (verificado vía `uv run python`).

**Apply to:** Plan 09-03 (BUG-01). Compilar el regex una sola vez al import time; usar `frozenset` para los Literal values (inmutable + hashable).

```python
_CFI_ISO_RE = re.compile(r"^[A-Z]{6}$")
_CFI_LITERAL_VALUES = frozenset(get_args(CFICode))  # tupla → frozenset
```

### Pattern S6 — Probe shape para `main_<pkg>.py` driver (ProbeResult + try/except + append_finding)

**Source:** `main_higyrus.py:195-200` (`@dataclass ProbeResult`) + `main_higyrus.py:657-746` (`probe_get_listado_cuentas_sync` skeleton).

**Apply to:** Plan 09-02 (`probe_multi_account_iteration`).

```python
def probe_<name>() -> ProbeResult:
    if _auth_failed:
        return ProbeResult("<name>", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = higyrus_client.client._base_url
    try:
        ...
    except HigyrusAuthError as exc:
        fid = _next_fid()
        append_finding(_PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
                       title="...", expected="...", actual=repr(exc),
                       diff=f"status_code={exc.status_code!r}", base_url=base_url)
        return ProbeResult("<name>", "FINDING", f"{fid} (OPEN)")
    ...
    return ProbeResult("<name>", "PASS", "<detail>")
```

### Pattern S7 — Finding `Resolution:` + `Regression:` lines (Phase 5 Op A convention)

**Source:** `.planning/verification/FINDINGS-TEMPLATE.md` + `higyrus-client-findings.md:20-27` (F-01 example).

**Apply to:** Plan 09-02 (F-02 update — 3 buckets), Plan 09-03 (F-09 flip).

```markdown
- **Status:** `<FIXED|NO-FIX|EXPECTED>`
- **Resolution:** <descripción concisa + path:línea del fix + rationale opcional>
- **Regression:** `<test path>::<test name>` <opcional explicación>
```

### Pattern S8 — Probe-scoped DEBUG logging con `try/finally` (BUG-02 triage)

**Source:** Phase 8 `_logging.py` getLogger pattern + RESEARCH.md Pattern 3.

**Apply to:** Plan 09-02 BUG-02 triage probe (un nuevo probe en `main_higyrus.py` o re-uso de probe 5 con DEBUG envolvente).

```python
logger = logging.getLogger("higyrus_client")
original_level = logger.level
logger.setLevel(logging.DEBUG)
try:
    # ... probe body ...
finally:
    logger.setLevel(original_level)
```

Sin `finally`, una excepción salta del scope y el nivel queda en DEBUG para probes posteriores (Pitfall 5 RESEARCH.md).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/phases/09-deferred-bug-fixes/09-VALIDATION.md` | doc (CI evidence) | n/a | No code analog necesario — markdown doc-only. Sigue la estructura de las VALIDATION.md de Phase 6/7/8 (revisar phases anteriores). |

---

## Metadata

**Analog search scope:**
- `packages/iol-client/{src,tests}/`
- `packages/higyrus-client/{src,tests}/`
- `packages/matriz-client/{src,tests}/`
- `main_*.py` (root)
- `.planning/verification/*-findings.md`

**Files scanned:** 13 source files + 9 test files + 3 driver scripts + 4 findings files.

**Key cross-cutting insight:**
- `_state.account_id` (a remover por D-09) y `RequestSpec.account_id` / `request.extensions["account_id"]` (Phase 8 D-11 log correlation, NO se tocan) son **fields DISTINTOS con mismo nombre**. Pitfall 1 RESEARCH.md. El grep para D-09 debe limitarse a `*/src/*/_state.py` y docstrings; NUNCA tocar `_transport.py`, `_atransport.py`, `_core.py` ni `tests/test_transport.py`.
- El analog canónico para Plan 09-01 sync es `test_client.py:154-251` (4 tests refresh_token ya existentes); Plan 09-01 añade los 2 paths CR-01 que faltan (paths 3 + 4) + completa el set canónico.
- Plan 09-03 es 100% extensión idiomática: 1 builder modificado + 1 paramétrico añadido en archivo existente.

**Pattern extraction date:** 2026-06-13
