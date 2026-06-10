# Phase 3: IOL Verification - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 9 (3 código modificado, 2 tests append, 4 artefactos generados, 0 barrel changes)
**Analogs found:** 9 / 9 — todos con match exacto o role-match fuerte en código que se mergeó en Phase 2 hace pocos días. PATTERNS.md de Phase 2 (`.planning/phases/02-mbito-verification/02-PATTERNS.md`) es el gold reference; este archivo lo refleja verbatim sustituyendo Ámbito-specific por IOL-specific (auth real, refresh_token, 4 endpoints, 4 snapshots).

---

## File Classification

| Archivo (nuevo/modificado) | Rol | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/iol-client/src/iol_client/client.py` | client surface modification (auth fix in-cycle) | request-response + OAuth token cache | `packages/iol-client/src/iol_client/client.py` (mismo archivo, `login()` lines 85-108 + `_ensure_token()` 111-114) + `verification.findings` pattern de validación | exact (in-place edit) |
| `packages/iol-client/src/iol_client/aio.py` | mirror async (auth fix) | request-response + asyncio.Lock double-checked | `packages/iol-client/src/iol_client/aio.py` (mismo archivo, `_login_unlocked()` 88-111 + `_ensure_token()` 120-126) | exact (in-place edit, mirror obligatorio) |
| `packages/iol-client/src/iol_client/__init__.py` | barrel re-export (sin cambio) | static re-export | `packages/iol-client/src/iol_client/__init__.py` (mismo archivo) | exact — D-IOL-8 explícito: NO se re-exporta `_refresh_token` |
| `main_iol.py` | driver rewrite (orchestrator, 15 probes) | request-response + file-I/O (findings + 4 schemas) | `main_ambito_financiero.py` (Phase 2 reference, 728 líneas, 7 probes) | role-match — analog directo, mismo lifecycle, 8 más probes |
| `packages/iol-client/tests/test_client.py` | test append (invariantes + regresiones) | request-response mock | `packages/iol-client/tests/test_client.py` (8 tests existentes con `httpx_mock.add_response(url=...)`) + `packages/ambito-financiero-client/tests/test_client.py` Phase 2 sections | exact (mismo archivo, append-only) |
| `packages/iol-client/tests/test_async_client.py` | test append (mirror async) | request-response mock async | `packages/iol-client/tests/test_async_client.py` (5 tests existentes) | exact (mismo archivo, append-only) |
| `packages/iol-client/tests/test_driver_invariants.py` (NUEVO opcional, recomendado) | unit test del driver | in-memory mock del driver | `packages/ambito-financiero-client/tests/test_driver_invariants.py` (Phase 2: WR-01/WR-03/IN-03 regressions) | exact (precedente Phase 2) |
| `.planning/verification/schemas/iol-client/{get-quote,get-historical-quotes,get-instruments,get-instruments-by-type}.json` (4 archivos) | generated artifacts (committeable) | one-shot JSON dump + drift detection | `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` (Phase 2 baseline, envelope D-21) | exact (mismo envelope D-21, mismo D-25 no-overwrite-on-drift) |
| `.planning/verification/iol-client-findings.md` | generated artifact (committeable) | esqueleto + appends idempotentes por fid | `.planning/verification/ambito-financiero-client-findings.md` + `verification.findings.write_findings`/`append_finding` | exact (helper hardened post Phase 2; preserva CR-01/CR-02/WR-04) |

---

## Pattern Assignments

### 1. `packages/iol-client/src/iol_client/client.py` — MODIFY (IOL-07 fix sync)

**Analog principal:** mismo archivo (`packages/iol-client/src/iol_client/client.py:85-114`). El fix extiende:
- `_refresh_token: str | None = None` (D-IOL-8) — nuevo singleton siguiendo el patrón existente de `_token: str | None = None` (línea 53).
- `configure()` resetea ambos (D-IOL-8).
- `login()` captura `refresh_token` además de `access_token` (D-IOL-9).
- `_refresh()` nuevo helper privado: `POST /token` con `grant_type=refresh_token`.
- `_ensure_token()` con fallback refresh → password (D-IOL-10).

**Convención obligatoria:** `from __future__ import annotations` ya en línea 22; mypy strict; double quotes; line-length=100; ruff format auto-aplicado; `__all__` por barrel (`__init__.py` no se re-exporta `_refresh_token`).

**Singleton state pattern existente** (`client.py:53-54`):

```python
_token: str | None = None
_token_expires_at: float = 0.0
```

**Nuevo singleton (D-IOL-8) — add after line 54:**

```python
_refresh_token: str | None = None
```

**Configure reset pattern existente** (`client.py:58-73`):

```python
def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> None:
    """Sobrescribe credenciales/URL en runtime y resetea el token cacheado."""
    global _base_url, _user, _password, _token, _token_expires_at
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if username is not None:
        _user = username
    if password is not None:
        _password = password
    _token = None
    _token_expires_at = 0.0
```

**Modificación D-IOL-8:**
- Agregar `_refresh_token` a la lista `global`.
- Setear `_refresh_token = None` en el reset (mismo bloque que `_token = None`).

**Login pattern existente** (`client.py:85-108`):

```python
def login() -> str:
    """Autentica contra ``POST /token`` (OAuth password grant) y cachea el token."""
    global _token, _token_expires_at

    if not _user or not _password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")

    resp = _client.post(
        f"{_base_url}/token",
        data={"username": _user, "password": _password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)

    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")

    _token = access_token
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token
```

**Modificación D-IOL-9:**
- Agregar `_refresh_token` a `global`.
- Después de `access_token = data.get("access_token")`, agregar `refresh_token = data.get("refresh_token")`.
- Después de setear `_token = access_token`, agregar la captura de refresh con narrowing PII-free para mypy (Pitfall 4 del RESEARCH §"mypy strict narrowing"):

```python
_token = access_token
new_refresh = data.get("refresh_token")
if isinstance(new_refresh, str) and new_refresh:
    _refresh_token = new_refresh
else:
    _refresh_token = None  # respuesta no incluye refresh_token (loggear como finding AUTH OPEN desde el driver)
_token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
```

**Nuevo helper `_refresh()` (RESEARCH Pattern 3, sync surface, sin lock):**

```python
def _refresh() -> str:
    """POST /token con grant_type=refresh_token. Mirror de login() con refresh body."""
    global _token, _refresh_token, _token_expires_at
    refresh_token = _refresh_token  # local copy para mypy narrowing (Pitfall 4)
    if not refresh_token:
        raise IOLAuthError(0, "No refresh_token cached")
    resp = _client.post(
        f"{_base_url}/token",
        data={"refresh_token": refresh_token, "grant_type": "refresh_token"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in refresh response")
    _token = access_token
    new_refresh = data.get("refresh_token")
    if isinstance(new_refresh, str) and new_refresh:
        _refresh_token = new_refresh  # rotación; sino keep existing (RESEARCH Pitfall 3)
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token
```

**`_ensure_token()` con fallback D-IOL-10** — patrón existente actualizado:

```python
def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    if _refresh_token:
        try:
            _refresh()
            return
        except IOLAuthError:
            pass  # fallback a password grant (D-IOL-10)
    login()
```

**Reuse de `_raise_for_response`** (`client.py:76-82`): el patrón existente cubre 401/403 → `IOLAuthError`, 429 → `IOLRateLimitError`, otros → `IOLAPIError`. `_refresh()` lo reusa sin cambios.

**Reuse de `_TOKEN_TTL_BUFFER_SECONDS`** (`client.py:48`): mismo buffer de 60s, refresh aplica idéntico cálculo de expiry.

**Anti-pattern documentado** (RESEARCH §"Anti-Patterns to Avoid"):
- Usar `assert _refresh_token is not None` — Python `-O` strips asserts. Usar `if _refresh_token is None: raise IOLAuthError(...)`.
- Resetear `_refresh_token = None` fuera de `configure()` o `_refresh()` success — rompe el singleton invariant.

---

### 2. `packages/iol-client/src/iol_client/aio.py` — MODIFY (IOL-07 fix async mirror)

**Analog principal:** mismo archivo (`packages/iol-client/src/iol_client/aio.py:88-126`). Mirror del sync con `_token_lock` double-checked locking (RESEARCH Pattern 2).

**Convención dual sync/async obligatoria** (CLAUDE.md): cualquier fix de lógica en `client.py` se duplica en `aio.py`. La duplicación es deuda conocida del proyecto.

**Singleton + lock state pattern existente** (`aio.py:35-39`):

```python
_token: str | None = None
_token_expires_at: float = 0.0
_client: httpx.AsyncClient | None = None
_token_lock = asyncio.Lock()
_client_lock = asyncio.Lock()
```

**Modificación D-IOL-8** — agregar después de línea 35:

```python
_refresh_token: str | None = None
```

**Configure pattern existente** (`aio.py:42-57`) — mismo patrón que sync, agregar `_refresh_token` a `global` y al reset.

**`_login_unlocked()` pattern existente** (`aio.py:88-111`):

```python
async def _login_unlocked() -> str:
    global _token, _token_expires_at

    if not _user or not _password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")

    client = await _ensure_http_client()
    resp = await client.post(
        f"{_base_url}/token",
        data={"username": _user, "password": _password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)

    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")

    _token = access_token
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token
```

**Modificación D-IOL-9** (mirror del sync): agregar `_refresh_token` a `global` + capturar new_refresh con narrowing.

**Nuevo `_refresh_unlocked()` (RESEARCH Pattern 2)** — el caller debe tener `_token_lock` adquirido:

```python
async def _refresh_unlocked() -> str:
    """Caller debe tener `_token_lock`. Mirror async de `_refresh()` sync."""
    global _token, _refresh_token, _token_expires_at
    refresh_token = _refresh_token  # local copy para mypy narrowing
    if not refresh_token:
        raise IOLAuthError(0, "No refresh_token cached")
    client = await _ensure_http_client()
    resp = await client.post(
        f"{_base_url}/token",
        data={"refresh_token": refresh_token, "grant_type": "refresh_token"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in refresh response")
    _token = access_token
    new_refresh = data.get("refresh_token")
    if isinstance(new_refresh, str) and new_refresh:
        _refresh_token = new_refresh
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token
```

**`_ensure_token()` con double-checked locking pattern existente** (`aio.py:120-126`):

```python
async def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    async with _token_lock:
        if _token and time.time() < _token_expires_at:
            return
        await _login_unlocked()
```

**Modificación D-IOL-10 (RESEARCH Pattern 2):**

```python
async def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    async with _token_lock:
        if _token and time.time() < _token_expires_at:
            return
        if _refresh_token:
            try:
                await _refresh_unlocked()  # dentro del mismo lock
                return
            except IOLAuthError:
                pass  # fallback a password grant
        await _login_unlocked()
```

**Reuse de `_ensure_http_client()`** (`aio.py:60-68`): mismo helper para refresh — el lock está separado (`_client_lock`), no entra en conflicto con `_token_lock`.

**Anti-pattern documentado** (RESEARCH §"Anti-Patterns to Avoid"): NO crear un segundo evento loop ni re-instanciar `_client` después de `aclose()`. El refresh comparte el `_client` activo.

---

### 3. `packages/iol-client/src/iol_client/__init__.py` — NO CHANGES

**Analog:** mismo archivo.

**Decisión D-IOL-8 explícita:** `_refresh_token` es state privado; el barrel NO lo re-exporta. El `__all__` actual cubre todo lo público:

```python
__all__ = [
    "IOLAPIError",
    "IOLAuthError",
    "IOLClientError",
    "IOLRateLimitError",
    "InstrumentType",
    "configure",
    "get_historical_quotes",
    "get_instruments",
    "get_instruments_by_type",
    "get_quote",
    "login",
]
```

El nuevo `_refresh()` también es privado (prefijo `_`), no se exporta. Tests acceden via `iol_client.client._refresh` directamente para mockear.

---

### 4. `main_iol.py` — REWRITE COMPLETO (smoke-test → 15 probes)

**Analog principal:** `main_ambito_financiero.py` (Phase 2, 728 líneas, 7 probes — el reference más cercano y más reciente).
**Analog secundario:** `main_iol.py` actual (33 líneas, smoke `require_env` + `redact`).
**Analog tercero:** `verification/findings.py::append_finding` (helper hardened post Phase 2, idempotente).

**Convención obligatoria:** `from __future__ import annotations` (mandatory CLAUDE.md); mypy strict; ruff line-length=100; double quotes; sin wildcard/relative imports; section dividers con `# --- ... ---`.

**Module docstring pattern** (`main_ambito_financiero.py:1-36`): docstring explícito enumerando los 15 probes en orden D-IOL-5 + opt-in `VERIFY_IOL_BAD_CREDS=1` (D-IOL-1) + artefactos generados (findings + 4 schemas).

```python
"""Driver de verificación en vivo del paquete `iol-client` (Phase 3).

Ejecuta 15 probes nombrados que ejercen la superficie pública sync+async del
cliente IOL contra ``api.invertironline.com`` y producen artefactos
committeable: el findings markdown clasificado y 4 schema snapshots (DRIFT-01
extendido a 4 endpoints).

Uso::

    uv run --package iol-client python main_iol.py

Requiere ``IOL_USER`` e ``IOL_PASSWORD`` en ``packages/iol-client/.env``.
``IOL_BASE_URL`` es opcional.

Probes en orden de ejecución (D-IOL-5):

1.  ``probe_login_sync``                 — login() explícito sync (IOL-01).
2.  ``probe_login_async``                — login() explícito async (IOL-01).
3.  ``probe_get_quote_sync``             — get_quote("GGAL") sync (IOL-02).
4.  ``probe_get_quote_async``            — get_quote("GGAL") async (IOL-02).
5.  ``probe_get_historical_quotes_sync`` — serie 5 dias hábiles sync (IOL-02).
6.  ``probe_get_historical_quotes_async``— serie 5 dias hábiles async (IOL-02).
7.  ``probe_get_instruments_sync``       — get_instruments("argentina") sync.
8.  ``probe_get_instruments_async``      — espejo async.
9.  ``probe_get_instruments_by_type_sync`` — acciones + envelope ["titulos"] sync.
10. ``probe_get_instruments_by_type_async``— espejo async.
11. ``probe_parity_sync_async``          — diff estructural por endpoint (IOL-06).
12. ``probe_field_type_map``             — schema_of(raw) vs _ASSUMED_*.
13. ``probe_schema_snapshot``            — 4 snapshots envelope D-21 + D-25.
14. ``probe_refresh_token``              — fuerza expiry y verifica refresh path.
15. ``probe_auth_401``                   — opt-in VERIFY_IOL_BAD_CREDS=1 (ÚLTIMO).
"""
```

**Imports pattern (carry-forward Phase 2 +  IOL-specific):**

```python
from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verification import require_env, safe_print, schema_of, write_findings
from verification.findings import append_finding

import iol_client
from iol_client import IOLAPIError, IOLAuthError, aio
```

**Notas:**
- Importar `require_env` (a diferencia de Ámbito que no usa credenciales).
- `IOLAPIError` + `IOLAuthError` para mapear excepciones (no `IOLRateLimitError` salvo que el driver lo mapee explícitamente — el `_raise_for_response` ya lo levantaría y se atrapa como `IOLAPIError` su padre).

**Module-level constants pattern** (`main_ambito_financiero.py:56-74`):

```python
_PKG = "iol-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG
_SCHEMA_FILES = {
    "get_quote": _SCHEMA_DIR / "get-quote.json",
    "get_historical_quotes": _SCHEMA_DIR / "get-historical-quotes.json",
    "get_instruments": _SCHEMA_DIR / "get-instruments.json",
    "get_instruments_by_type": _SCHEMA_DIR / "get-instruments-by-type.json",
}

# D-IOL-18: sample fixo, BCBA stock líquido.
_SAMPLE_SYMBOL = "GGAL"
# D-IOL-17: baseline para schema snapshot; sanity check de los 6 InstrumentType.
_SAMPLE_INSTRUMENT_TYPE = "acciones"
# D-IOL-17 sanity check de los 6 types.
_ALL_INSTRUMENT_TYPES: tuple[str, ...] = (
    "obligacionesNegociables",
    "titulosPublicos",
    "cedears",
    "acciones",
    "letras",
    "cauciones",
)

# D-IOL-14: caller assumptions hardcoded module-level — fácil de auditar en PR.
_ASSUMED_QUOTE_FIELDS: dict[str, str] = {
    "ultimoPrecio": "float",
    "simbolo": "str",
    # ... extender según code review del cliente
}
_ASSUMED_HISTORICAL_FIELDS: dict[str, str] = {
    "fechaHora": "str",
    "ultimoPrecio": "float",
}
_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE: dict[str, str] = {
    "titulos": "list",  # IOL-04 envelope key
}

# Contador module-level para asignar fids F-01, F-02, ... (Discretion).
_fid_counter: int = 0

# D-IOL-3: cascade SKIPPED — flag module-level si login() falla.
_auth_failed: bool = False
_auth_failure_reason: str = ""
```

**`_next_fid()` helper reusable verbatim** (`main_ambito_financiero.py:77-81`):

```python
def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"
```

**`ProbeResult` dataclass reusable verbatim** (`main_ambito_financiero.py:89-95`):

```python
@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Resultado de un probe; agregado al summary final."""

    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str
```

**Date helper reusable verbatim** (`main_ambito_financiero.py:103-108`) — D-IOL-19:

```python
def _last_business_day(today: dt.date) -> dt.date:
    """Lunes->viernes anterior; cualquier otro día -> el día previo."""
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d
```

**Day > 12 variant reusable verbatim** (`main_ambito_financiero.py:111-123`) — para Verified-live tests sync/async que verifican el formato del path histórico:

```python
def _last_business_day_with_day_gt_12(today: dt.date) -> dt.date:
    """Día hábil anterior con date.day > 12 (descarta ambigüedad MM/DD vs DD/MM)."""
    d = _last_business_day(today)
    while d.day <= 12:
        d -= dt.timedelta(days=1)
        while d.weekday() >= 5:
            d -= dt.timedelta(days=1)
    return d
```

**Cascade SKIPPED early-return pattern (D-IOL-3, RESEARCH Pattern 1):** cada probe downstream checkea el flag:

```python
def probe_get_quote_sync() -> tuple[ProbeResult, dict[str, Any] | None]:
    if _auth_failed:
        return (
            ProbeResult("get_quote_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    # ... lógica normal del probe
```

**Probe entry pattern (read `_base_url` from module-private state, WR-03 single-HTTP-call)** — heredado de `main_ambito_financiero.py:140-152`:

```python
def probe_get_quote_sync() -> tuple[ProbeResult, dict[str, Any] | None]:
    if _auth_failed:
        return (ProbeResult("get_quote_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"), None)
    base_url = iol_client.client._base_url  # estado resuelto en vivo; sólo lectura
    path = f"/api/v2/bcba/Titulos/{_SAMPLE_SYMBOL}/Cotizacion"
    try:
        # WR-03: una sola llamada HTTP por probe. Llamamos al wrapper público
        # get_quote (NO _request) porque su lógica es trivial (resp.json) y
        # queremos ejercitarlo en el live run para detectar regresiones.
        # Excepción: probe_field_type_map_envelope (IOL-04 swallow detection)
        # SÍ llama _request directamente — ver RESEARCH Pitfall 2.
        quote = iol_client.get_quote(_SAMPLE_SYMBOL)
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
            title="get_quote_sync recibió AuthError inesperado",
            expected="200 OK con Bearer cacheado", actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",  # WR-01: typed
            base_url=base_url,
        )
        return (ProbeResult("get_quote_sync", "FINDING", f"{fid} (OPEN)"), None)
    except IOLAPIError as exc:
        # ...
    except Exception as exc:
        # ...
    return (ProbeResult("get_quote_sync", "PASS", f"ultimoPrecio={quote.get('ultimoPrecio')!r}"), quote)
```

**Typed `exc.status_code` (WR-01 Phase 2 review fix)** — `IOLAPIError.__init__` siempre setea `self.status_code = status_code` (verificado en `packages/iol-client/src/iol_client/exceptions.py:13-16`). Usar `exc.status_code` directo, NUNCA fallback a `exc.args[0]`.

**Envelope check pattern (RESEARCH Pitfall 2)** — para IOL-04, llamar `_request` directamente NO el wrapper:

```python
def probe_field_type_map_envelope_check() -> ProbeResult:
    if _auth_failed:
        return ProbeResult("field_type_map_envelope", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = iol_client.client._base_url
    try:
        # CRÍTICO: _request directo. El wrapper get_instruments_by_type hace
        # data.get("titulos", []) — si el wire deja de emitir "titulos", el
        # wrapper devuelve [] silenciosamente y la detección de drift se pierde.
        resp = iol_client.client._request(
            "GET",
            f"/api/v2/Cotizaciones/{_SAMPLE_INSTRUMENT_TYPE}/argentina/Todos",
        )
        data: dict[str, Any] = resp.json()
    except Exception as exc:
        # ... append_finding ERROR-MAP OPEN
    if "titulos" not in data:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="SHAPE", surface="both", status="OPEN",
            title="missing envelope key 'titulos' in get_instruments_by_type",
            expected="dict con key 'titulos' (list[dict])",
            actual=f"keys={sorted(data.keys())}",
            diff="client.py:206 hace data.get('titulos', []) — drift invisible al caller",
            base_url=base_url,
        )
        return ProbeResult("field_type_map_envelope", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("field_type_map_envelope", "PASS", "envelope present")
```

**Refresh token probe (D-IOL-11) — IN-VIVO verification del fix IOL-07:**

```python
def probe_refresh_token() -> ProbeResult:
    if _auth_failed:
        return ProbeResult("refresh_token", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = iol_client.client._base_url
    refresh_before = iol_client.client._refresh_token
    if refresh_before is None:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
            title="login() no capturó refresh_token del payload",
            expected="_refresh_token != None tras login() exitoso",
            actual="_refresh_token=None",
            diff="el server no devolvió refresh_token o el cliente lo descartó",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
    token_before = iol_client.client._token
    # Forzar expiry para gatillar el branch refresh
    import iol_client.client as _client_mod
    _client_mod._token_expires_at = 0.0
    try:
        # Disparar un call autenticado para gatillar _ensure_token
        iol_client.get_instruments("argentina")
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
            title="refresh path no funciona en vivo",
            expected="refresh exitoso sin re-disparar password grant",
            actual=repr(exc), diff=f"status_code={getattr(exc, 'status_code', None)!r}",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
    token_after = iol_client.client._token
    refresh_after = iol_client.client._refresh_token
    if token_before == token_after:
        # El token no cambió → posiblemente el ensure encontró expires_at ok (race) o no funcionó
        # ... finding AUTH OPEN
    if refresh_after is None:
        # _refresh_token quedó None → bug en la rotación (Pitfall 3)
        # ... finding AUTH OPEN
    return ProbeResult("refresh_token", "PASS", "refresh path verified")
```

**Auth 401 probe pattern (D-IOL-1, D-IOL-2, D-IOL-4)** — mirror exacto del Phase 2 `probe_antibot` con try/finally restore:

```python
def probe_auth_401() -> ProbeResult:
    if _auth_failed:
        return ProbeResult("auth_401", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    if os.getenv("VERIFY_IOL_BAD_CREDS") != "1":
        return ProbeResult("auth_401", "SKIPPED", "(opt-in via VERIFY_IOL_BAD_CREDS=1)")
    base_url = iol_client.client._base_url
    original_password = os.getenv("IOL_PASSWORD", "")
    bad_password = original_password + "_INVALID"
    try:
        iol_client.configure(password=bad_password)
        try:
            iol_client.login()  # single-shot D-IOL-1, sin retry, sin sleep
        except IOLAuthError as exc:
            status_code = exc.status_code  # WR-01: typed, no fallback
            if status_code == 401:
                fid = _next_fid()
                append_finding(
                    _PKG, fid=fid, class_="AUTH", surface="sync", status="EXPECTED",
                    title="credenciales inválidas reciben 401",
                    expected="401 con password=IOL_PASSWORD+_INVALID",
                    actual=f"401 con password=...{redact_segment}...",
                    diff="ninguno; comportamiento esperado",
                    base_url=base_url,
                )
                return ProbeResult("auth_401", "FINDING", f"{fid} (EXPECTED)")
            # otro status → OPEN
            # ... append_finding
        # sin excepción → defensa relajada OPEN
    finally:
        # D-IOL-2: SIEMPRE restaurar el password original
        iol_client.configure(password=original_password)
```

**Schema snapshot pattern (D-IOL-16, 4 snapshots) — heredado verbatim de Phase 2 `probe_schema_snapshot` (`main_ambito_financiero.py:492-548`):**

```python
def _write_or_check_schema(
    func_name: str,
    endpoint_template: str,
    sample_params: dict[str, Any],
    raw_payload: Any,
    base_url: str,
) -> ProbeResult:
    """Helper común: write-on-first-run, compare-on-rerun (D-25 no-overwrite)."""
    schema_file = _SCHEMA_FILES[func_name]
    actual_schema = schema_of(raw_payload)
    envelope: dict[str, object] = {
        "endpoint": endpoint_template,
        "client_function": func_name,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "base_url": base_url,
        "sample_params": sample_params,
        "schema": actual_schema,
    }
    _SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    if not schema_file.exists():
        schema_file.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return ProbeResult(f"schema_{func_name}", "PASS", f"escrito {schema_file.name}")
    committed = json.loads(schema_file.read_text(encoding="utf-8"))
    if committed.get("schema") == actual_schema:
        return ProbeResult(f"schema_{func_name}", "PASS", "schema sin drift")
    fid = _next_fid()
    append_finding(
        _PKG, fid=fid, class_="SHAPE", surface="both", status="OPEN",
        title=f"Schema drift en {func_name}",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="comparar expected vs actual; NO se sobreescribe baseline (D-25)",
        base_url=base_url,
    )
    return ProbeResult(f"schema_{func_name}", "FINDING", f"{fid} (OPEN) — NO sobreescribe")
```

**`probe_schema_snapshot()` orquestador** — itera los 4 endpoints y emite un único ProbeResult agregado o per-endpoint. Discretion del implementador.

**Para `get_instruments_by_type` D-IOL-17:** el snapshot se hace con `_SAMPLE_INSTRUMENT_TYPE = "acciones"` SOLAMENTE. Sanity check de los 6:

```python
def _sanity_check_six_instrument_types(base_url: str) -> ProbeResult:
    """D-IOL-17: type-only assertion para los 6 InstrumentType, sin schema_of por cada uno."""
    discrepancies: list[str] = []
    for itype in _ALL_INSTRUMENT_TYPES:
        try:
            titulos = iol_client.get_instruments_by_type(itype)
        except Exception as exc:
            discrepancies.append(f"{itype}: {type(exc).__name__}")
            continue
        if not isinstance(titulos, list) or not titulos or not isinstance(titulos[0], dict):
            discrepancies.append(f"{itype}: shape={type(titulos).__name__}")
    if discrepancies:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="SHAPE", surface="both", status="OPEN",
            title="get_instruments_by_type devuelve shape inesperada para algún type",
            expected="list[dict] no vacío para los 6 InstrumentType",
            actual="; ".join(discrepancies), diff="ver actual",
            base_url=base_url,
        )
        return ProbeResult("sanity_6_types", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("sanity_6_types", "PASS", "los 6 types devuelven list[dict] no vacío")
```

**Field→type map pattern (D-IOL-13, D-IOL-14, D-IOL-15)** — comparar `schema_of(raw)` contra `_ASSUMED_*`:

```python
def probe_field_type_map(
    quote: dict[str, Any] | None,
    historical: list[dict[str, Any]] | None,
    instruments_by_type_raw: dict[str, Any] | None,
) -> ProbeResult:
    if _auth_failed:
        return ProbeResult("field_type_map", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = iol_client.client._base_url
    findings_emitted: list[str] = []
    # get_quote
    if quote is not None:
        observed = schema_of(quote)
        for key, expected_type in _ASSUMED_QUOTE_FIELDS.items():
            if key not in observed:
                fid = _next_fid()
                append_finding(
                    _PKG, fid=fid, class_="SHAPE", surface="both", status="OPEN",
                    title=f"missing assumed key {key!r} in get_quote",
                    expected=f"key '{key}' present", actual=f"keys={sorted(observed.keys())}",
                    diff=f"el caller asume {key}: {expected_type}",
                    base_url=base_url,
                )
                findings_emitted.append(fid)
            elif observed[key] != expected_type:
                fid = _next_fid()
                append_finding(
                    _PKG, fid=fid, class_="SHAPE", surface="both", status="OPEN",
                    title=f"type drift on {key!r} in get_quote: assumed {expected_type}, observed {observed[key]}",
                    expected=f"{key}: {expected_type}", actual=f"{key}: {observed[key]}",
                    diff="tipo wire cambió respecto al assumption del caller",
                    base_url=base_url,
                )
                findings_emitted.append(fid)
    # ... mismo para historical, instruments_by_type_raw envelope
    if findings_emitted:
        return ProbeResult("field_type_map", "FINDING", f"{', '.join(findings_emitted)} (OPEN)")
    return ProbeResult("field_type_map", "PASS", "sin drift detectado")
```

**Sync↔async parity pattern (D-IOL-20)** — estructural via `schema_of`, sin valores numéricos (`main_ambito_financiero.py:301-355` mirror adaptado a 4 endpoints):

```python
def probe_parity_sync_async(
    quote_sync: dict[str, Any] | None,
    quote_async: dict[str, Any] | None,
    historical_sync: list[dict[str, Any]] | None,
    historical_async: list[dict[str, Any]] | None,
    instruments_sync: Any,
    instruments_async: Any,
    instruments_by_type_sync: list[dict[str, Any]] | None,
    instruments_by_type_async: list[dict[str, Any]] | None,
) -> ProbeResult:
    if _auth_failed:
        return ProbeResult("parity_sync_async", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = iol_client.client._base_url
    findings_emitted: list[str] = []
    pairs = [
        ("get_quote", quote_sync, quote_async),
        ("get_historical_quotes", historical_sync, historical_async),
        ("get_instruments", instruments_sync, instruments_async),
        ("get_instruments_by_type", instruments_by_type_sync, instruments_by_type_async),
    ]
    for name, s, a in pairs:
        if s is None or a is None:
            continue
        if schema_of(s) != schema_of(a):
            fid = _next_fid()
            append_finding(
                _PKG, fid=fid, class_="SYNC-ASYNC-DRIFT", surface="both", status="OPEN",
                title=f"shape drift sync vs async en {name}",
                expected="schema_of(sync) == schema_of(async)",
                actual=f"sync_schema={schema_of(s)}, async_schema={schema_of(a)}",
                diff="comparación estructural difiere; valores no comparados (precio cambia mid-call)",
                base_url=base_url,
            )
            findings_emitted.append(fid)
    if findings_emitted:
        return ProbeResult("parity_sync_async", "FINDING", f"{', '.join(findings_emitted)} (OPEN)")
    return ProbeResult("parity_sync_async", "PASS", "shape sync == async en los 4 endpoints")
```

**Async lifecycle pattern (D-IOL-6, IN-03 fix de Phase 2)** — un único `asyncio.run`, `aclose()` en `contextlib.suppress(Exception)` (`main_ambito_financiero.py:654-672`):

```python
async def _async_main(
    today: dt.date,
) -> tuple[
    ProbeResult,  # login_async
    ProbeResult, dict[str, Any] | None,  # get_quote
    ProbeResult, list[dict[str, Any]] | None,  # get_historical_quotes
    ProbeResult, Any,  # get_instruments
    ProbeResult, list[dict[str, Any]] | None,  # get_instruments_by_type
]:
    """Compone los probes async y cierra el cliente al final (D-IOL-6)."""
    try:
        result_login_async = await probe_login_async()
        result_quote_async, quote_async = await probe_get_quote_async()
        result_historical_async, historical_async = await probe_get_historical_quotes_async(today)
        result_instruments_async, instruments_async = await probe_get_instruments_async()
        result_by_type_async, by_type_async = await probe_get_instruments_by_type_async()
    finally:
        # IN-03: aclose() en contextlib.suppress para no violar D-04
        with contextlib.suppress(Exception):
            await aio.aclose()
    return (
        result_login_async,
        result_quote_async, quote_async,
        result_historical_async, historical_async,
        result_instruments_async, instruments_async,
        result_by_type_async, by_type_async,
    )
```

**Main orchestrator pattern (`main_ambito_financiero.py:680-723`)** — `require_env` gate first, summary verbatim:

```python
def main() -> None:
    """Orquesta los 15 probes en el orden D-IOL-5 y emite el summary final."""
    if not require_env(_PKG, ["IOL_USER", "IOL_PASSWORD"]):
        # HARN-01: env_gate ya imprimió SKIPPED con formato verbatim; exit 0.
        return

    today = dt.date.today()
    write_findings(_PKG)  # idempotente

    results: list[ProbeResult] = []

    # 1. probe_login_sync (D-IOL-3: si falla, _auth_failed=True, cascade SKIPPED)
    results.append(probe_login_sync())

    # 2-10 + parts of async: un único asyncio.run (D-IOL-6)
    (result_login_async, result_quote_async, quote_async,
     result_historical_async, historical_async,
     result_instruments_async, instruments_async,
     result_by_type_async, by_type_async) = asyncio.run(_async_main(today))
    results.append(result_login_async)

    # 3-10 sync — captura payloads para reuse en 11/12/13
    result_quote_sync, quote_sync = probe_get_quote_sync()
    results.append(result_quote_sync)
    results.append(result_quote_async)
    result_historical_sync, historical_sync = probe_get_historical_quotes_sync(today)
    results.append(result_historical_sync)
    results.append(result_historical_async)
    result_instruments_sync, instruments_sync = probe_get_instruments_sync()
    results.append(result_instruments_sync)
    results.append(result_instruments_async)
    result_by_type_sync, by_type_sync = probe_get_instruments_by_type_sync()
    results.append(result_by_type_sync)
    results.append(result_by_type_async)

    # 11. parity sync ↔ async
    results.append(probe_parity_sync_async(
        quote_sync, quote_async, historical_sync, historical_async,
        instruments_sync, instruments_async, by_type_sync, by_type_async,
    ))

    # 12. field type map
    results.append(probe_field_type_map(quote_sync, historical_sync, ...))

    # 13. schema snapshot (4 endpoints)
    results.append(probe_schema_snapshot(quote_sync, historical_sync, instruments_sync, by_type_sync))

    # 14. refresh_token in-vivo
    results.append(probe_refresh_token())

    # 15. auth_401 (ÚLTIMO, opt-in D-IOL-4)
    results.append(probe_auth_401())

    # D-IOL-7: safe_print con lista de secrets NO vacía (incluye _refresh_token)
    secrets = [
        v for v in (
            os.getenv("IOL_USER"),
            os.getenv("IOL_PASSWORD"),
            iol_client.client._refresh_token,
        ) if v and len(v) >= 4
    ]
    for r in results:
        safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=secrets)

    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_skip = sum(1 for r in results if r.status == "SKIPPED")
    n_find = sum(1 for r in results if r.status == "FINDING")
    safe_print(
        f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find}",
        secrets=secrets,
    )


if __name__ == "__main__":
    main()
```

**`safe_print` con secrets dinámicos (D-IOL-7, D-IOL-22)** — diferencia vs Phase 2: la lista NO es vacía. `_refresh_token` se agrega al momento de imprimir (después de los probes), de modo que captura el valor cacheado por el primer `login()`.

---

### 5. `packages/iol-client/tests/test_client.py` — APPEND (Verified live + Regressions)

**Analog:** mismo archivo (`packages/iol-client/tests/test_client.py:1-87`, 8 tests existentes con `httpx_mock.add_response(url=...)`).
**Analog secundario:** `packages/ambito-financiero-client/tests/test_client.py` Phase 2 (mismo patrón de secciones).

**Convención obligatoria:** `from __future__ import annotations` (l.3); pytest-httpx con `url=...` full URL; autouse fixture `_configure_sync` precarga `_token` (l.14-24 de `conftest.py`); section dividers verbatim.

**Imports existentes** (`test_client.py:1-11`):

```python
"""Smoke tests del cliente sincrónico de IOL (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import IOLAuthError, IOLRateLimitError
```

**Cambio Phase 3:** sin nuevos imports en el header (los tests refresh-token import directamente desde `iol_client.client`). Si se agregan tests de envelope check, agregar `import iol_client.client` directo (acceso a `_request`).

**Existing test pattern (analog directo para Verified live)** (`test_client.py:42-48`):

```python
def test_get_quote_arma_url_y_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = iol_client.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5
```

**Sección nueva — `# ------ Verified live (Phase 3) ------`** (D-IOL-21):

```python
# ------ Verified live (Phase 3) ------


def test_get_quote_url_exacta_con_query_string(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking URL exacta de get_quote (IOL-02).

    Verificado en vivo el <fecha>: el cliente emite el path completo
    /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion con query params
    model.mercado, model.simbolo, model.plazo en ese orden.
    """
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = iol_client.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5
    # IOL-04: campo numérico llega como float / int (NO string)
    assert isinstance(quote["ultimoPrecio"], (int, float))


def test_get_historical_quotes_url_dia_gt_12(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking del formato YYYY-MM-DD del path histórico (IOL-04).

    Día > 12 descarta ambigüedad DD/MM vs MM/DD estructuralmente.
    """
    desde = dt.date(2026, 4, 15)
    hasta = dt.date(2026, 4, 20)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-15/2026-04-20/sinAjustar",
        json=[{"fechaHora": "2026-04-18T17:00:00", "ultimoPrecio": 999.9}],
    )
    serie = iol_client.get_historical_quotes("GGAL", desde, hasta)
    assert serie[-1]["ultimoPrecio"] == 999.9


def test_get_instruments_by_type_unwraps_titulos(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking del unwrap data["titulos"] (IOL-04 envelope).

    Verificado en vivo: el wire emite {"titulos": [...]}; el cliente devuelve
    la lista interna. Si el wire deja de emitir "titulos", el cliente
    devuelve [] silenciosamente — bug detectado por el field_type_map probe
    in-vivo, no por este test (que mockea el envelope correcto).
    """
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/acciones/argentina/Todos",
        json={"titulos": [{"simbolo": "GGAL"}, {"simbolo": "PAMP"}]},
    )
    titulos = iol_client.get_instruments_by_type("acciones")
    assert isinstance(titulos, list)
    assert all(isinstance(t, dict) for t in titulos)
    assert [t["simbolo"] for t in titulos] == ["GGAL", "PAMP"]


# ------ Regressions ------


def test_refresh_token_success_path(httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: IOL-07 — refresh path actualiza _token sin re-disparar password (finding F-NN).

    El autouse fixture precarga _token; el monkeypatch lo limpia y setea
    _refresh_token para forzar la rama refresh en _ensure_token.
    """
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-1", raising=False)

    # RESEARCH Pitfall 5: usar match_content para bind respuestas a bodies específicos
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-1&grant_type=refresh_token",
        json={"access_token": "tok-after-refresh", "refresh_token": "refresh-2", "expires_in": 900},
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )
    iol_client.get_instruments("argentina")
    assert iol_client.client._token == "tok-after-refresh"
    assert iol_client.client._refresh_token == "refresh-2"


def test_refresh_fails_falls_back_to_password(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — refresh inválido cae al password grant (finding F-NN)."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-bad", raising=False)

    # 1. Refresh attempt → 401
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-bad&grant_type=refresh_token",
        status_code=401,
        text="invalid_grant",
    )
    # 2. Fallback al password grant → success
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        json={"access_token": "tok-from-password", "refresh_token": "refresh-new", "expires_in": 900},
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )
    iol_client.get_instruments("argentina")
    assert iol_client.client._token == "tok-from-password"
    assert iol_client.client._refresh_token == "refresh-new"


def test_refresh_and_password_both_fail(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — ambos refresh y password fallan → IOLAuthError (finding F-NN)."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-bad", raising=False)

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-bad&grant_type=refresh_token",
        status_code=401,
    )
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        status_code=401,
    )
    with pytest.raises(IOLAuthError):
        iol_client.get_instruments("argentina")


def test_login_captures_refresh_token(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — login() captura refresh_token del payload (finding F-NN)."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", None, raising=False)

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={
            "access_token": "tok-initial",
            "refresh_token": "refresh-initial",
            "expires_in": 900,
        },
    )
    iol_client.login()
    assert iol_client.client._token == "tok-initial"
    assert iol_client.client._refresh_token == "refresh-initial"
```

**Autouse fixture reusable sin cambio** (`packages/iol-client/tests/conftest.py:13-24`):

```python
@pytest.fixture(autouse=True)
def _configure_sync(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    iol_client.configure(base_url="https://api.test", username="u", password="p")
    monkeypatch.setattr(iol_client.client, "_token", "test-token", raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    iol_client.configure(base_url="https://api.test", username="", password="")
```

Los tests de refresh **NO** necesitan modificar el fixture; usan `monkeypatch.setattr` per-test para sobreescribir `_token = None` y `_token_expires_at = 0.0`.

**`match_content` pattern (RESEARCH Pitfall 5)** — discriminar respuestas por body POST cuando hay 2 mocks al mismo URL:
- Sin `match_content`: pytest-httpx asigna respuestas en orden de registración. Si el código llama refresh primero pero el test registra password primero, el password mock se consume para el refresh request. Bug latente.
- Con `match_content=b"...&grant_type=refresh_token"`: la respuesta queda atada al body. Orden de registración deja de importar para distinguir refresh vs password.

---

### 6. `packages/iol-client/tests/test_async_client.py` — APPEND (mirror async)

**Analog:** mismo archivo (`packages/iol-client/tests/test_async_client.py:1-55`, 5 tests existentes).

**Imports existentes** (`test_async_client.py:1-11`):

```python
"""Smoke tests del cliente asincrónico de IOL (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from iol_client import IOLAuthError, aio
```

**Sin cambios en imports.**

**Existing async test pattern (analog directo)** (`test_async_client.py:28-34`):

```python
async def test_async_get_quote(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5},
    )
    quote = await aio.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5
```

**Sección nueva mirror exacto:**

```python
# ------ Verified live (Phase 3) ------


async def test_async_get_quote_url_exacta_con_query_string(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking URL exacta de aio.get_quote (IOL-02)."""
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = await aio.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5
    assert isinstance(quote["ultimoPrecio"], (int, float))


async def test_async_get_historical_quotes_url_dia_gt_12(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking del formato YYYY-MM-DD del path histórico async (IOL-04)."""
    desde = dt.date(2026, 4, 15)
    hasta = dt.date(2026, 4, 20)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-15/2026-04-20/sinAjustar",
        json=[{"fechaHora": "2026-04-18T17:00:00", "ultimoPrecio": 999.9}],
    )
    serie = await aio.get_historical_quotes("GGAL", desde, hasta)
    assert serie[-1]["ultimoPrecio"] == 999.9


async def test_async_get_instruments_by_type_unwraps_titulos(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking del unwrap data["titulos"] async (IOL-04 envelope)."""
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/acciones/argentina/Todos",
        json={"titulos": [{"simbolo": "GGAL"}, {"simbolo": "PAMP"}]},
    )
    titulos = await aio.get_instruments_by_type("acciones")
    assert isinstance(titulos, list)
    assert all(isinstance(t, dict) for t in titulos)
    assert [t["simbolo"] for t in titulos] == ["GGAL", "PAMP"]


# ------ Regressions ------


async def test_async_refresh_token_success_path(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — refresh path async actualiza _token (finding F-NN, mirror)."""
    monkeypatch.setattr(aio, "_token", None, raising=False)
    monkeypatch.setattr(aio, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(aio, "_refresh_token", "refresh-1", raising=False)

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-1&grant_type=refresh_token",
        json={"access_token": "tok-after-refresh", "refresh_token": "refresh-2", "expires_in": 900},
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )
    await aio.get_instruments("argentina")
    assert aio._token == "tok-after-refresh"
    assert aio._refresh_token == "refresh-2"


async def test_async_refresh_fails_falls_back_to_password(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — refresh inválido cae al password grant async (finding F-NN, mirror)."""
    # ... mirror del sync


async def test_async_refresh_and_password_both_fail(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — ambos fallan async → IOLAuthError (finding F-NN, mirror)."""
    # ... mirror del sync


async def test_async_login_captures_refresh_token(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — async login() captura refresh_token (finding F-NN, mirror)."""
    # ... mirror del sync
```

**Async autouse fixture reusable sin cambio** (`packages/iol-client/tests/conftest.py:27-34`):

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

**Async test sin decorador** (TESTING.md + `pyproject.toml` `asyncio_mode = "auto"`): los nuevos tests NO usan `@pytest.mark.asyncio`.

---

### 7. `packages/iol-client/tests/test_driver_invariants.py` — NEW (OPCIONAL, recomendado)

**Analog primario:** `packages/ambito-financiero-client/tests/test_driver_invariants.py` (Phase 2 regression tests del driver — WR-01, WR-03, IN-03).
**Analog secundario:** `packages/ambito-financiero-client/tests/test_findings_helper.py` (precedente: tests del harness viven bajo el paquete que primero los usa).

**Convención obligatoria:** `from __future__ import annotations`; mypy strict; tests viven bajo `packages/iol-client/tests/` porque `testpaths=["packages"]` los colecta; el driver `main_iol` se importa desde la raíz via `pythonpath=["."]`.

**Imports pattern (`test_driver_invariants.py:21-34` de Phase 2)** — adaptación literal:

```python
"""Tests de regresión sobre el driver `main_iol.py` (Phase 3 fixes).

El driver vive en la raíz del repo y no está en `testpaths` (D-05: NO se ejecuta
dentro de pytest), pero su comportamiento crítico se chequea acá vía tests de
regresión que mockean la superficie sync+async del cliente y assertean
invariantes del driver:

- **D-IOL-3 cascade SKIPPED:** si _auth_failed=True, todos los probes downstream
  retornan ProbeResult SKIPPED sin invocar HTTP.
- **D-IOL-7 redaction:** safe_print enmascara IOL_USER, IOL_PASSWORD,
  _refresh_token aun si aparecen en payloads/excepciones.
- **D-IOL-11 in-vivo refresh:** probe_refresh_token observa _token change +
  _refresh_token no None tras forzar expiry.
- **D-IOL-15 SHAPE finding emission:** field_type_map emite 1 finding por
  discrepancia (missing key, type drift, unexpected key).
- **WR-03 single-HTTP-call:** probes 3-10 hacen UNA sola llamada por probe.
- **IN-03 _async_main aclose() suppresses:** si aclose() levanta, exit 0.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import main_iol as driver
import pytest

from iol_client.exceptions import IOLAuthError
```

**Autouse fixture isolation pattern** (`test_driver_invariants.py:37-46` Phase 2):

```python
@pytest.fixture(autouse=True)
def _isolate_driver_state(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla el driver: redirige el directorio de findings y schemas a tmp_path."""
    from verification import findings

    monkeypatch.setattr(findings, "_FINDINGS_DIR", tmp_path)
    monkeypatch.setattr(driver, "_SCHEMA_DIR", tmp_path / "schemas")
    monkeypatch.setattr(driver, "_SCHEMA_FILES", {
        "get_quote": tmp_path / "schemas" / "get-quote.json",
        "get_historical_quotes": tmp_path / "schemas" / "get-historical-quotes.json",
        "get_instruments": tmp_path / "schemas" / "get-instruments.json",
        "get_instruments_by_type": tmp_path / "schemas" / "get-instruments-by-type.json",
    })
    monkeypatch.setattr(driver, "_fid_counter", 0)
    monkeypatch.setattr(driver, "_auth_failed", False)
    monkeypatch.setattr(driver, "_auth_failure_reason", "")
```

**Tests recomendados:**

```python
def test_cascade_skipped_when_auth_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-IOL-3: si _auth_failed=True, probe_get_quote_sync retorna SKIPPED sin HTTP."""
    monkeypatch.setattr(driver, "_auth_failed", True)
    monkeypatch.setattr(driver, "_auth_failure_reason", "test reason")
    import iol_client
    request_mock = MagicMock()
    monkeypatch.setattr(iol_client.client, "_request", request_mock)
    monkeypatch.setattr(iol_client, "get_quote", MagicMock())
    result, payload = driver.probe_get_quote_sync()
    assert result.status == "SKIPPED"
    assert "auth failed" in result.detail
    assert payload is None
    assert request_mock.call_count == 0  # NO HTTP


def test_field_type_map_emits_finding_on_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-IOL-15: missing assumed key → SHAPE finding OPEN."""
    quote = {"simbolo": "GGAL"}  # falta ultimoPrecio
    historical = []
    raw_envelope = {"titulos": []}
    result = driver.probe_field_type_map(quote, historical, raw_envelope)
    assert result.status == "FINDING"


def test_async_main_aclose_suppresses_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """IN-03 mirror: si aclose() levanta, no se propaga al run."""
    # ... mockear aio.aclose para que levante; verificar que asyncio.run no crashea
```

**Pattern de Phase 2 directamente reutilizable:** los probes async se mockean con `AsyncMock`, los sync con `MagicMock`, y los payloads se inyectan via `monkeypatch.setattr` sobre `iol_client.client._request`.

---

### 8. `.planning/verification/schemas/iol-client/{4 archivos}.json` — GENERATED (DRIFT-01 × 4)

**Analog primario:** `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` (Phase 2 baseline committed).
**Analog secundario:** `main_ambito_financiero.py:512-548` (`probe_schema_snapshot` envelope D-21 + drift D-25).

**Envelope D-21 obligatorio:**

```json
{
  "endpoint": "/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion",
  "client_function": "get_quote",
  "captured_at": "2026-06-...T...+00:00",
  "base_url": "https://api.invertironline.com",
  "sample_params": {
    "simbolo": "GGAL",
    "mercado": "bcba",
    "plazo": "t2"
  },
  "schema": {
    "fechaHora": "str",
    "moneda": "str",
    "simbolo": "str",
    "ultimoPrecio": "float"
  }
}
```

**Diferencias vs Phase 2 envelope:**

| Phase 2 | Phase 3 |
|---|---|
| `sample_date: "2026-05-..."` | `sample_params: {...}` (más rich; el sample no es solo fecha) |
| 1 archivo | 4 archivos (uno por endpoint) |
| sin auth ni sensitive data | base_url contiene `api.invertironline.com` (público OK) |

**JSON writing convention (verbatim Phase 2):**
- `json.dumps(envelope, indent=2, ensure_ascii=False) + "\n"`
- `encoding="utf-8"`
- Insertion order preservado (D-21 — no `sort_keys`).
- Sufijo `+ "\n"` para trailing newline (convención UNIX).

**D-25 no-overwrite-on-drift pattern (mismo bloque que Phase 2 `probe_schema_snapshot`):**

```python
if not schema_file.exists():
    schema_file.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ProbeResult(..., "PASS", f"escrito {schema_file.name}")
committed = json.loads(schema_file.read_text(encoding="utf-8"))
if committed.get("schema") == actual_schema:
    return ProbeResult(..., "PASS", "schema sin drift")
# D-25: NO sobreescribe; emite finding SHAPE OPEN.
append_finding(...)
return ProbeResult(..., "FINDING", f"{fid} (OPEN) — NO sobreescribe")
```

**Para `get-instruments-by-type.json` (D-IOL-17):** el schema debe ser el **raw envelope** `{"titulos": [{"simbolo": "str", ...}]}`, NO la lista unwrapped. Esto requiere capturar el payload via `_request` directo (Pitfall 2):

```json
{
  "endpoint": "/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos",
  "client_function": "get_instruments_by_type",
  "captured_at": "2026-06-...",
  "base_url": "https://api.invertironline.com",
  "sample_params": {
    "instrument_type": "acciones",
    "pais": "argentina"
  },
  "schema": {
    "titulos": [
      {
        "simbolo": "str",
        "...": "..."
      }
    ]
  }
}
```

**Para `get-historical-quotes.json`:** `sample_params` incluye `desde` y `hasta` derivados de `_last_business_day(today) - 5d` y `_last_business_day(today)`. Captured values van como strings ISO.

**Key ordering (RESEARCH Open Question Phase 2):** `json.dumps(..., indent=2)` SIN `sort_keys`. El campo `schema` ya viene ordenado por `schema_of` (`verification/schema.py:36`).

---

### 9. `.planning/verification/iol-client-findings.md` — GENERATED (esqueleto + appends)

**Analog primario:** `.planning/verification/ambito-financiero-client-findings.md` (Phase 2 committed).
**Analog secundario:** `verification/findings.py::write_findings` + `append_finding` (helper hardened).

**Generación inicial desde el driver (D-03):**

```python
write_findings(_PKG)  # idempotente — no-op si el archivo ya existe
```

**Estructura inicial generada** (`verification/findings.py:100-119`):

```markdown
# Findings: iol-client-client

## Run Context (ART)
- Timestamp: <ISO-8601>
- Resolved base URL / env: <url> (<remarkets|prod|public>)
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

<!-- Clases (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT -->
<!-- Estados (D-08): OPEN -> CONFIRMED -> FIXED (+ terminal EXPECTED/NO-FIX). Sin campo de severidad. -->

## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
```

**Doble sufijo `-client`** (mismo issue Phase 2): `# Findings: iol-client-client`. Phase 2 PATTERNS.md ya lo documentó: `write_findings` emite `{pkg}-client` verbatim. Para consistencia con el resto del repo (`ambito-financiero-client-client`, `higyrus-client`-...), mantener `_PKG = "iol-client"` y aceptar el doble sufijo en el header del archivo.

**Append-per-finding pattern** (helper `verification.findings.append_finding`, hardened post-CR-01/CR-02/WR-04):
- **Idempotente por `fid`:** re-llamada con mismo `fid` actualiza fila del Index + sección de detalle SIN duplicar.
- **Preserva status humano:** si `status != "OPEN"` (CONFIRMED/FIXED/EXPECTED/NO-FIX), el finding NO se toca; sólo el ART block (Timestamp, base_url, market_hours) se refresca.
- **Valida `pkg` slug:** `_PKG_SLUG_RE = r"^[a-z0-9][a-z0-9-]*$"` rechaza path traversal. `"iol-client"` matchea.
- **Valida `title` single-line:** `\n` o `\r` levantan `ValueError`.
- **Valida `class_` / `status`:** deben estar en `FINDING_CLASSES` / `STATUS_LIFECYCLE`; sino `ValueError`.

**Append call sites (driver `main_iol.py`):** cada probe que detecta una discrepancia llama `append_finding(_PKG, fid=fid, class_=..., surface=..., status="OPEN", title=..., expected=..., actual=..., diff=..., base_url=base_url)`. Documentado en RESEARCH §"Pattern 4: Phase 2 driver patterns (inheritance map)" — pattern reusable verbatim.

**Per-finding section format** — referencia `.planning/verification/FINDINGS-TEMPLATE.md:67-85`:

```markdown
### F-01 -- missing envelope key 'titulos' in get_instruments_by_type

**Class:** `SHAPE` . **Surface:** `both` . **Status:** `OPEN`

- **Expected:** dict con key 'titulos' (list[dict])
- **Actual:** keys=['cotizaciones', 'data']
- **Diff:** client.py:206 hace data.get('titulos', []) — drift invisible al caller
```

**Regression cross-reference** — D-07 sustituye `issue #NNN` por `finding F-NN`. Los tests de regression en `test_client.py` referencian el `F-NN` correspondiente en su docstring.

---

## Shared Patterns

### Convención obligatoria cross-archivos (CLAUDE.md / CONVENTIONS.md)

**Aplica a:** TODOS los archivos modificados/nuevos (`client.py`/`aio.py`, `main_iol.py`, tests).

```python
from __future__ import annotations    # primera línea de TODO módulo nuevo (mandatory)
```

- **Ruff:** `line-length = 100`, double quotes, 4 espacios.
- **Mypy strict:** `disallow_untyped_defs = true`, `warn_return_any = true`. Toda función nueva con firma completa incluyendo retorno.
- **Naming:** `snake_case` funciones/vars, `_snake_case` internals/module-state.
- **Imports:** no wildcard (`from x import *` prohibido), no relative (TID enforced).
- **Pre-commit hooks** (`.pre-commit-config.yaml`) corren ruff + mypy en cada commit.

### Pattern: dual sync/async espejado obligatorio

**Source:** CONVENTIONS.md + `packages/iol-client/src/iol_client/{client,aio}.py` (existing duplication).
**Apply to:** TODO fix de lógica en `client.py` (IOL-07: `_refresh_token`, `_refresh()`, `_ensure_token` fallback) se MIRRORA en `aio.py` (con `_refresh_unlocked()` + double-checked locking en `_token_lock`).

### Pattern: barrel `verification` import (no relative)

**Source:** `main_ambito_financiero.py:49-50`, `main_higyrus.py:14-19`.
**Apply to:** `main_iol.py`.

```python
from verification import require_env, safe_print, schema_of, write_findings
from verification.findings import append_finding
```

`require_env` se importa para IOL (a diferencia de Ámbito que no usa auth). `append_finding` se importa via su submódulo o via barrel — ambos válidos; Phase 2 usa el directo.

### Pattern: `safe_print` con secrets NO vacíos (D-IOL-7 vs Phase 2)

**Source:** `verification/redaction.py:43-61` + `main_higyrus.py:31-44`.
**Apply to:** `main_iol.py` final loop de stdout.

```python
secrets = [
    v for v in (
        os.getenv("IOL_USER"),
        os.getenv("IOL_PASSWORD"),
        iol_client.client._refresh_token,
    ) if v and len(v) >= 4
]
safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=secrets)
```

**Diferencia vs Phase 2 Ámbito:** Phase 2 usa `secrets=[]` porque Ámbito no tiene credenciales. Phase 3 IOL llena `secrets` con USER, PASSWORD, y `_refresh_token` cacheado (capturado dinámicamente del módulo después de los probes). El `_BEARER` regex sigue funcionando como segunda capa (cubre tokens reflejados aun sin enumerar).

### Pattern: módulo-privado `_base_url` lectura para `append_finding`

**Source:** `verification/mutation_gate.py:55` + `main_ambito_financiero.py:141`.
**Apply to:** TODO probe del driver `main_iol.py`.

```python
base_url = iol_client.client._base_url  # estado resuelto en vivo; sólo lectura
# luego pasar base_url=base_url a append_finding(...)
```

Python no enforce `_` prefix; el patrón ya está documentado en Phase 1/2. Sólo lectura — nunca print directo del valor.

### Pattern: `pytest-httpx` con URL completa + match_content para POSTs duplicados

**Source:** `test_client.py:42-48` (URL full) + RESEARCH Pitfall 5 (`match_content` para discriminar bodies).
**Apply to:** TODOS los tests Verified live + Regressions.

```python
httpx_mock.add_response(
    url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
    json={...},
)
# Para refresh tests con 2 POSTs al mismo URL:
httpx_mock.add_response(
    url="https://api.test/token",
    method="POST",
    match_content=b"refresh_token=...&grant_type=refresh_token",
    json={...},
)
```

URL completa con query string valida routing implícitamente. `match_content` binds responses to bodies → orden de registración deja de importar.

### Pattern: regression docstring (D-IOL-12 + D-07)

**Source:** `.planning/codebase/TESTING.md` convención `Regression: ... (issue #NNN)`.
**Apply to:** TODOS los tests de la sección `# ------ Regressions ------`.

```python
def test_refresh_token_success_path(...) -> None:
    """Regression: IOL-07 — refresh path actualiza _token sin re-disparar password (finding F-NN).

    <contexto adicional opcional>.
    """
```

D-07 sustituye `(issue #NNN)` por `(finding F-NN)` — el findings file es la fuente de verdad. F-NN se llena después del live run cuando el driver asigne el fid concreto.

### Pattern: async test sin decorador

**Source:** `test_async_client.py:13-19` + `pyproject.toml [tool.pytest.ini_options].asyncio_mode = "auto"`.
**Apply to:** TODOS los tests async nuevos en `test_async_client.py`.

```python
async def test_async_<name>(httpx_mock: HTTPXMock) -> None:
    """..."""
    ...
    await aio.get_quote(...)
```

No `@pytest.mark.asyncio` — `asyncio_mode = "auto"` lo aplica.

### Pattern: dataclass `frozen=True, slots=True` para `ProbeResult`

**Source:** `verification/anonymize.py:34-46` (`Denylist`) + `main_ambito_financiero.py:89-95`.
**Apply to:** `ProbeResult` en `main_iol.py` (verbatim copy).

```python
@dataclass(frozen=True, slots=True)
class ProbeResult:
    name: str
    status: str
    detail: str
```

### Pattern: `mkdir(parents=True, exist_ok=True)` + `write_text` (file-I/O idempotente)

**Source:** `verification/capture.py:48-51` + `verification/findings.py:127`.
**Apply to:** `main_iol.py::probe_schema_snapshot` (escritura de los 4 JSON envelopes).

```python
_SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
schema_file.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
```

`encoding="utf-8"` siempre; `ensure_ascii=False`; `indent=2`; trailing `"\n"`.

### Pattern: typed `exc.status_code` (WR-01 Phase 2 review)

**Source:** `packages/iol-client/src/iol_client/exceptions.py:13-16` (`IOLAPIError.__init__` siempre setea `self.status_code = status_code`).
**Apply to:** TODO probe del driver que inspecciona excepciones IOL.

```python
except IOLAuthError as exc:
    status_code = exc.status_code  # WR-01: typed, NO fallback a exc.args[0]
    if status_code == 401:
        ...
```

`IOLAPIError.__init__` formatea `super().__init__(f"[{status_code}] {message}")` así que `args[0]` es la string formateada, no el número — el fallback era código muerto + incorrecto.

### Pattern: `contextlib.suppress(Exception)` alrededor de `aclose()` (IN-03)

**Source:** `main_ambito_financiero.py:670-671`.
**Apply to:** `main_iol.py::_async_main`.

```python
finally:
    with contextlib.suppress(Exception):
        await aio.aclose()
```

D-04 guard: errores del teardown del AsyncClient no deben tirar abajo el run.

### Pattern: `try/finally` para state mutation (D-IOL-2 + D-15 Phase 2)

**Source:** `main_ambito_financiero.py:574-647` (`probe_antibot`).
**Apply to:** `main_iol.py::probe_auth_401`.

```python
try:
    iol_client.configure(password=bad_password)
    try:
        iol_client.login()
    except IOLAuthError as exc:
        ...
finally:
    iol_client.configure(password=original_password)  # SIEMPRE restaurar
```

### Pattern: single HTTP call per probe (WR-03)

**Source:** `main_ambito_financiero.py:150-152` + comentario.
**Apply to:** TODOS los probes 3-10 en `main_iol.py`.

**Excepción explícita:** `probe_field_type_map_envelope_check` (IOL-04) llama `_request` directamente PARA poder ver el envelope crudo `{"titulos": [...]}` sin que el wrapper haga el `data.get("titulos", [])` silencioso. Esto NO viola WR-03 porque es una llamada distinta semánticamente; el field type map cubre un endpoint cuyo wrapper destruye el shape detectable.

---

## No Analog Found

| File | Role | Razón |
|---|---|---|
| `_refresh()` private helper (sync) + `_refresh_unlocked()` (async) | OAuth refresh-token grant implementation | El paquete IOL implementa solo password grant hoy (línea 85 client.py). Sin analog directo dentro del paquete; el closest analog es el propio `login()` / `_login_unlocked()` (mismo paquete, diferente grant type) más la pattern documentada en RESEARCH Pattern 2/3. **No es un real "no analog"** — es analog interno (`login`) + nueva URL body. |
| `probe_refresh_token` (in-vivo refresh verification) | Probe que muta `_token_expires_at = 0.0` y observa `_token` change | No hay precedente. Phase 2 no tiene refresh tokens. Implementación es Discretion (D-IOL-11) — patrón sugerido: observar `_token` antes/después + `_refresh_token` no None + `_token_expires_at` renovado. |
| `probe_field_type_map` (caller assumptions vs observed schema) | Probe que compara `schema_of(raw)` contra `_ASSUMED_*` y emite 3 sub-clases de finding | Sin precedente directo. Phase 2 hace drift detection contra schema committed (DRIFT-01), no contra hardcoded assumptions. Phase 3 introduce el patrón D-IOL-13 + D-IOL-14 + D-IOL-15. El primitivo `schema_of` se reusa pero la comparación es nueva. |
| Cascade SKIPPED via module-level flag `_auth_failed` | Driver-wide pattern para gatear probes downstream | Sin precedente Phase 1/2. Discretion D-IOL-3 — alternativas: decorator, early-return en cada probe. Implementación más simple es flag module-level checkeado al inicio de cada probe (sugerido en RESEARCH Pattern 1). |

---

## Metadata

**Analog search scope:**
- `packages/iol-client/` (target principal)
- `packages/ambito-financiero-client/` (Phase 2 outputs ready-to-mirror)
- `verification/` (harness committed + hardened post-Phase-2)
- `main_*.py` (raíz, drivers)
- `.planning/phases/02-mbito-verification/02-PATTERNS.md` (gold reference)
- `.planning/phases/02-mbito-verification/02-CONTEXT.md` (D-01..D-26 lifecycle)
- `.planning/phases/03-iol-verification/03-CONTEXT.md` (D-IOL-1..22)
- `.planning/phases/03-iol-verification/03-RESEARCH.md` (9 pitfalls, 4 patterns)
- `.planning/codebase/{TESTING,CONVENTIONS,CONCERNS,INTEGRATIONS}.md`

**Files scanned (lectura directa):** 16

| Archivo | Propósito |
|---|---|
| `.planning/phases/03-iol-verification/03-CONTEXT.md` | D-IOL-1..22 + canonical refs + reusable assets |
| `.planning/phases/03-iol-verification/03-RESEARCH.md` | 4 Patrones técnicos + 5 Pitfalls + Architecture |
| `.planning/phases/02-mbito-verification/02-PATTERNS.md` | Gold reference — Phase 2 patterns para mirror verbatim |
| `packages/iol-client/src/iol_client/client.py` | Target sync — `login()`, `_ensure_token`, `_request`, 4 endpoints |
| `packages/iol-client/src/iol_client/aio.py` | Target async — `_login_unlocked()`, `_token_lock` double-checked, espejo de los 4 endpoints |
| `packages/iol-client/src/iol_client/exceptions.py` | Jerarquía: `IOLAPIError.__init__` siempre setea `status_code` |
| `packages/iol-client/src/iol_client/__init__.py` | `__all__` público; NO re-exportar `_refresh_token` |
| `packages/iol-client/tests/conftest.py` | Autouse fixtures precargan `_token = "test-token"` |
| `packages/iol-client/tests/test_client.py` | 8 tests existentes — pattern para append Verified-live + Regressions |
| `packages/iol-client/tests/test_async_client.py` | 5 tests existentes — espejo async para append |
| `main_iol.py` | Driver actual (33 líneas) — rewrite target |
| `main_ambito_financiero.py` | Phase 2 reference driver (728 líneas, 7 probes) — analog directo |
| `verification/findings.py` | `append_finding` hardened (CR-01/CR-02/WR-04); helper reusable |
| `verification/schema.py` | `schema_of` — primitivo D-IOL-13 |
| `verification/redaction.py` | `safe_print(text, secrets=[...])` — D-IOL-7/22 |
| `verification/env_gate.py` | `require_env(pkg, [vars])` — HARN-01 |
| `verification/__init__.py` | Barrel export — `append_finding` ya disponible |
| `packages/ambito-financiero-client/tests/test_findings_helper.py` | Analog para tests del helper si extiende |
| `packages/ambito-financiero-client/tests/test_driver_invariants.py` | Analog para test_driver_invariants IOL (recomendado) |

**Pattern extraction date:** 2026-06-06
