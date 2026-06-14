# Phase 9: Deferred Bug Fixes - Research

**Researched:** 2026-06-13
**Domain:** Python HTTP client testing + targeted bug fixes en 3 paquetes (matriz, higyrus, iol)
**Confidence:** HIGH (D-01..D-13 ya decididos en CONTEXT.md; research valida primitivas técnicas y aterriza patrones de implementación/test)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BUG-01 | F-09 matriz ERROR-MAP — `get_instruments_by_cfi` con CFI inválido no levanta `PrimaryAPIError`. Fix single-site en `_core.py` (cubre sync+async) + regression test mockeado; live re-run flipea `verify_cycle_closure(matriz)` FAIL→PASS | §"Standard Stack" (`re` + `typing.get_args`), §"Code Examples" (hybrid Literal+regex guard), §"Validation Architecture" (3-bucket parametric coverage), §"Common Pitfalls" (`get_args` ordering, regex unicode), §"State of the Art" (ISO 10962:2021 estándar canónico) |
| BUG-02 | F-02 higyrus `get_listado_cuentas=0` — quick triage con DEBUG logging probe-scoped; outcome decide (a) NO-FIX transient, (b) FIXED-by-environment, (c) client-side fix en `_core.py`. Regression test mockeado bloquea el bug en cualquier bucket | §"Architecture Patterns" (probe-scoped logging context manager), §"Code Examples" (3-bucket classification template), §"Validation Architecture" (contract guard mocked), §"Common Pitfalls" (httpx event_hooks + dual-flow login session) |
| BUG-03 | IOL refresh_token in-instance — código YA implementado (Phase 6 D-IOL-10); Phase 9 entrega **solo** los regression tests mockeados que cubren los 4 paths críticos (refresh→success, refresh→401→password fallback, server omite refresh_token, server rota refresh_token), sync + async mirror | §"Standard Stack" (`pytest-httpx` + `match_content`), §"Code Examples" (4 paths × 2 surfaces = 8 tests), §"Validation Architecture" (CR-01 conditional rotation both branches), §"Common Pitfalls" (autouse fixture state leakage), §"State of the Art" (RFC 6749 §6 OAuth2 refresh grant) |
| BUG-04 | HIGY multi-account iteration — per-call only (D-08): los 4 endpoints account-dependent mantienen `id_cuenta` per-call; `_state.account_id` removed (D-09 cross-package iol + higyrus); nuevo `probe_multi_account_iteration` en `main_higyrus.py` + mocked regression test 2 cuentas + `HIGYRUS_SAMPLE_CUENTAS` env var override | §"Architecture Patterns" (driver probe idiom), §"Code Examples" (CSV env var parse + mock 2-cuenta loop), §"Common Pitfalls" (`RequestSpec.account_id` ≠ `_state.account_id` distinction), §"Runtime State Inventory" (cleanup scope) |

</phase_requirements>

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**BUG-01 — matriz F-09 ERROR-MAP:**
- **D-01:** Hybrid `Literal` + ISO 10962 regex guard en `build_get_instruments_by_cfi_request` (NO en `raise_for_response`). Si `cfi_code` está en `CFICode` Literal (9 valores) → pass. Si matchea `^[A-Z]{6}$` (ISO 10962 forward-compat) → pass. Si ninguna → `raise PrimaryAPIError(status="ERROR", description=f"CFI inválido: {cfi_code!r}", message=None)` pre-HTTP. Tres buckets: literal-known / regex-forward-compat / malformed.
- **D-02:** Deviation explícito vs literal ROADMAP `_core.raise_for_response()` — el guard vive en el builder porque `raise_for_response` solo recibe `httpx.Response` (no ve `cfi_code`). El contrato observable (`PrimaryAPIError(status="ERROR")`) se preserva.
- **D-03:** Live re-verification dentro de Phase 9 — corre `uv run python main_matriz.py`, espera probe `probe_error_malformed_cfi` PASS, flipea F-09 CONFIRMED → FIXED con `Regression: tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code`. `cycle_closure_matriz_client` flipea FAIL → PASS.

**BUG-02 — higyrus F-02 `get_listado_cuentas=0`:**
- **D-04:** Quick triage time-boxed (1 plan). Re-correr `main_higyrus.py` con `logging.getLogger("higyrus_client").setLevel(logging.DEBUG)` probe-scoped. Outcome → 3 buckets: (a) transient → NO-FIX clasificación; (b) NO reproducible → FIXED-by-environment; (c) client-side root cause → fix en `_core.py` + regression test.
- **D-05:** Decision criteria documentado: empty `[]` + Phase 8 logs muestran 200 OK + envelope vacío + transient → bucket (a); non-empty list → bucket (b); 100% reproducible client-side → bucket (c); HTTP 4xx/5xx unexpected → escalación fuera de scope.

**BUG-03 — IOL refresh_token in-instance:**
- **D-06:** Código ya implementado (Phase 6 D-IOL-10): `_state.refresh_token` per instancia, `_ensure_token()` con refresh→password fallback, CR-01 conditional rotation. Phase 9 entrega **solo** regression tests; NO toca `_core.py`/`client.py`/`aio.py`/`_state.py`.
- **D-07:** Cuatro paths críticos × sync + async mirror = 8 tests. Files: `packages/iol-client/tests/test_refresh_token_lifecycle.py` (sync) + `test_refresh_token_lifecycle_async.py` (async).

**BUG-04 — HIGY multi-account iteration:**
- **D-08:** Operator decision: **per-call only** (NO constructor `Client(account_id=X)`). Los 4 endpoints account-dependent mantienen `id_cuenta` per-call. Iteración multi-cuenta = caller loopea.
- **D-09:** Remover `_state.account_id` forward-declared de higyrus + iol (cross-package cleanup). NO toca `RequestSpec.account_id` (campo distinto para log correlation, Phase 8 D-11).
- **D-10:** Live regression con ≥2 cuentas usando `.env` actual. Driver `main_higyrus.py` extendido con `probe_multi_account_iteration` + opcional `HIGYRUS_SAMPLE_CUENTAS` CSV env var override. Mocked regression: 2 cuentas mockeadas, loop, assert wire requests correctas.

**Plan slicing & wave orchestration:**
- **D-11:** 4 planes en 3 waves: Wave 1 paralelo (Plan 09-01 iol BUG-03, Plan 09-02 higyrus BUG-02+BUG-04+`_state.account_id` cross-pkg), Wave 2 (Plan 09-03 matriz BUG-01), Wave 3 (Plan 09-04 green gate).
- **D-12:** 1 commit atómico por plan.
- **D-13:** Live re-verification bug-driven solamente — Plan 09-02 `main_higyrus.py` live, Plan 09-03 `main_matriz.py` live. Full 4-pkg live es Phase 11 LIVE-01.

### Claude's Discretion

- Layout sync/async iol regression tests: 2 archivos vs 1 paramétrizado. Recomendación: 2 archivos (Phase 6 conftest idiom).
- Naming de probe nuevo en `main_higyrus.py`: `probe_multi_account_iteration` o `..._sweep`.
- `HIGYRUS_SAMPLE_CUENTAS` format: CSV vs whitespace. Recomendación: CSV (portable con `.env`, `python-dotenv` no soporta arrays nativos).
- Live re-run de `main_matriz.py` ubicación: step pre-commit vs operator-manual. Recomendación: operator-manual + paste evidence.
- Mocked test file BUG-01: extender `tests/test_core.py` vs nuevo `tests/test_cfi_validation.py`. Recomendación: extender `test_core.py` (affinity).
- Formato `Resolution:` line BUG-02: free-text + `(a)/(b)/(c)` marker.
- Si `_state.account_id` removal rompe algún test preexistente: extender Plan 09-02 (default atomic).
- Verbosidad del finding update post-fix: mínimo `Resolution:` + `Regression:` + 1-2 lines rationale.

### Deferred Ideas (OUT OF SCOPE)

- `Client(account_id=X)` constructor pattern para higyrus + iol → v1.2 si UX feedback.
- `Client(account_id=X)` propagation a `request.extensions["account_id"]` para log correlation sin afectar routing → v1.2.
- Disk persistence del IOL `refresh_token` cross-process → v1.2 (REQUIREMENTS BUG-03 lit).
- Extend Literal-runtime-validation a otros params (`MarketId`, `SegmentId`, `Side`, `OrderType`, `TimeInForce`) → v1.2/v1.3 si emerge evidencia.
- Higyrus support contact para BUG-02 si quick triage no resuelve → v1.2.
- BUG-02 isolated replay script + multi-session capture → v1.2 (probable NO).
- `HIGYRUS_SAMPLE_CUENTAS` promote a `verification/env_gate.py` registry → v1.2.
- Probe-scoped DEBUG logging context manager helper (`with debug_logging_for("higyrus_client"):`) → v1.2.
- Sub-loggers por concern (`<pkg>.refresh`, `<pkg>.auth`) → v1.2 si DEBUG noise inmanejable.
- Per-test `httpx-mock` factory for refresh flow → v1.2 si emerge duplicación significativa.
- `matriz_client/aio.py` REST surface y `_atransport.py` → Phase 10.
- TokenStore 3-way concurrent → Phase 10.
- HARN-07/08/09/10 y CR-01..08 → Phase 11.
- Full `main_*.py --live` × 4 → Phase 11 LIVE-01.

</user_constraints>

## Summary

Phase 9 cierra 4 bugs diferidos de v1.0 sin re-arquitecturizar nada. Toda la infraestructura habilitante (Client class per-instance Phase 6, `_core.py` single-site Phase 7, retries + structured logging Phase 8) ya está en producción. La fase es **80% testing + 1 fix de lógica real (BUG-01 matriz) + 1 triage clasificatorio (BUG-02 higyrus) + 1 cleanup de field muerto (`_state.account_id`)**.

Los 4 entregables tienen perfil de riesgo bajo: BUG-03 es solo regression tests (código ya validado por Phase 6 conftest migration); BUG-04 es operator decision "per-call only" + driver extension; BUG-01 es un guard de 5 líneas en el builder; BUG-02 es un quick triage time-boxed con outcome conocido (3 buckets). El único riesgo cross-package es `_state.account_id` removal en higyrus + iol (D-09), que mitigamos con grep del field name antes del delete.

**Primary recommendation:** Implementar el plan slicing tal como decidido (Wave 1 Plan 09-01 iol + Plan 09-02 higyrus paralelos → Wave 2 Plan 09-03 matriz → Wave 3 Plan 09-04 green gate). El único punto que el planner debe vigilar es el orden del live re-run de `main_matriz.py` en Plan 09-03 (operator-manual antes del commit del finding update). Confirmado vía CFI runtime testing: `^[A-Z]{6}$` regex es canónico ISO 10962 (Wikipedia, ISO 10962:2021), `typing.get_args(CFICode)` retorna los 9 valores en orden de declaración del Literal, `pytest-httpx` con `match_content=b"..."` ya está in-use para el flow refresh (tests existentes en `test_client.py`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CFI validation pre-HTTP (BUG-01) | `_core.py` builder | — | El cfi_code es input al builder; `raise_for_response` solo ve response (D-02). Single-site fix por Phase 7 REFAC-03 propaga a sync + async automáticamente. |
| Triage diagnostic logging (BUG-02) | Driver (`main_higyrus.py`) | `_logging.py` getLogger | Driver invoca `logging.getLogger("higyrus_client").setLevel(DEBUG)` probe-scoped. `_logging.py` ya provee NullHandler + RedactingFilter — driver solo eleva el nivel. |
| Refresh token lifecycle (BUG-03) | `_state.py` (campo) + `_core.py` (parser CR-01) + transport shell (CR-01 guard) | — | Código ya en place (Phase 6). Tests viven en `tests/` y ejercitan el flow end-to-end vía `pytest-httpx`. |
| Multi-account iteration (BUG-04) | API caller (loop) | Driver probe | Per-call only (D-08): los endpoints reciben `id_cuenta` como param. Driver loopea sobre cuentas. Mocked test valida wire requests. |
| Dead-field cleanup (D-09) | `_state.py` (delete field + docstring) | — | `_state.account_id` es field muerto post-D-08; remove cross-package (higyrus + iol). NO afecta `RequestSpec.account_id` (Phase 8 D-11). |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | 8.3+ | Test runner | [CITED: pyproject.toml root] — ya es el runner del repo |
| `pytest-httpx` | 0.34+ | Mock HTTPX requests | [CITED: pyproject.toml; tests existentes en `test_client.py`/`test_async_client.py` ya usan `httpx_mock` fixture] — convención del repo Phase 6-8 |
| `pytest-asyncio` | 0.24+ | Async test support, `asyncio_mode = "auto"` | [CITED: root pyproject.toml] — convención del repo |
| `re` (stdlib) | Python 3.12+ | Regex `^[A-Z]{6}$` para CFI validation | [VERIFIED: stdlib, verified via `uv run python` con CFICode + regex] — no requiere paquete externo |
| `typing.get_args` (stdlib) | Python 3.12+ | Extraer valores del `CFICode` Literal a runtime | [VERIFIED: stdlib, verified via `uv run python -c "from typing import get_args, Literal; ..."` retorna tupla en orden de declaración] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | 0.27+ | Transport ya existente | No se modifica — los tests usan `httpx_mock` que intercepta el transport |
| `python-dotenv` | 1.0+ | Carga env vars del `.env` | Para `HIGYRUS_SAMPLE_CUENTAS` CSV — `python-dotenv` no soporta arrays nativos [CITED: docs python-dotenv]; CSV es el idiom estándar |
| `logging` (stdlib) | Python 3.12+ | DEBUG-level probe-scoped triage para BUG-02 | `logging.getLogger("higyrus_client").setLevel(DEBUG)` — RedactingFilter (Phase 8 D-10) ya activo |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `re.compile(r"^[A-Z]{6}$")` module-level | `re.match()` en cada call | Module-level constant es Phase 7 idiom + zero runtime overhead post-import; descartado el inline match. |
| `frozenset(get_args(CFICode))` | `set(get_args(CFICode))` | `frozenset` es inmutable + hashable; previene mutación accidental del catálogo de Literal values. |
| `re.fullmatch(r"[A-Z]{6}", x)` | `re.match(r"^[A-Z]{6}$", x)` | Equivalentes; CONTEXT.md decide `^...$` explícito por legibilidad. |
| `match_content=` bytes literal | `match_json=` dict | El flow OAuth refresh usa form-encoded body (`grant_type=refresh_token&...`), NO JSON; `match_content=b"..."` es el idiom en uso. |

**Installation:**
No installs nuevos. Toda la dependencia del Phase 9 ya está en `uv.lock` post-Phase-8. `uv sync --frozen` suficiente.

**Version verification:**
```bash
uv run python -c "import pytest_httpx; print(pytest_httpx.__version__)"  # 0.34+
uv run python -c "import re; print(re.compile(r'^[A-Z]{6}$').match('ESXXXX'))"  # <re.Match object>
uv run python -c "from typing import get_args, Literal; T = Literal['A', 'B']; print(get_args(T))"  # ('A', 'B')
```

Resultado obtenido (verified 2026-06-13):
- `re.compile(r'^[A-Z]{6}$').match('ESXXXX')` → match object ✓
- `re.compile(r'^[A-Z]{6}$').match('INVALID-CFI')` → None ✓
- `re.compile(r'^[A-Z]{6}$').match('esxxxx')` → None ✓
- `re.compile(r'^[A-Z]{6}$').match('E2XXXX')` → None ✓
- `typing.get_args(CFICode)` → tupla con 9 valores en orden de declaración ✓

## Package Legitimacy Audit

Phase 9 **NO instala paquetes nuevos**. Toda dependencia (stdlib `re`, stdlib `typing`, `pytest`, `pytest-httpx`, `pytest-asyncio`, `httpx`, `python-dotenv`, `logging`) ya está en `uv.lock` post-Phase-8 con verificaciones de slopcheck previas (Phases 6/7/8). No corresponde nuevo audit en esta fase.

**Disposition:** N/A — sin instalaciones nuevas.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 9 Bug Fix Surfaces                        │
└─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
  │   BUG-01        │    │   BUG-02        │    │   BUG-03 + 04   │
  │   matriz CFI    │    │   higyrus       │    │   iol + higyrus │
  │   validation    │    │   triage        │    │   tests + cleanup│
  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
           │                      │                      │
           ▼                      ▼                      ▼
  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
  │ _core.py        │    │ Driver-level    │    │ tests/ files +  │
  │ builder guard   │    │ probe + DEBUG   │    │ _state.py field │
  │ (pre-HTTP)      │    │ logging         │    │ delete          │
  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
           │                      │                      │
           ▼                      ▼                      ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  Shared infrastructure (Phase 6-8, untouched in Phase 9)        │
  │                                                                  │
  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
  │  │ Client class │  │ _core.py     │  │ RetryTransport +       │ │
  │  │ per-instance │  │ single-site  │  │ RedactingFilter +      │ │
  │  │ (Phase 6)    │  │ (Phase 7)    │  │ _logging.py (Phase 8)  │ │
  │  └──────────────┘  └──────────────┘  └────────────────────────┘ │
  └─────────────────────────────────────────────────────────────────┘

           │
           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │   Verification gates (Plan 09-04 green gate)                    │
  │                                                                  │
  │  ┌─────────────────────────────┐  ┌────────────────────────────┐│
  │  │ verification/               │  │ verification/              ││
  │  │   test_public_surface.py    │  │   test_sync_async_         ││
  │  │   (Phase 6 D-09)            │  │   isolation.py             ││
  │  │   → zero diff               │  │   (Phase 7 D-10)           ││
  │  │     expected                │  │   → still GREEN            ││
  │  └─────────────────────────────┘  └────────────────────────────┘│
  └─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (Phase 9 deltas only)

```
packages/iol-client/tests/
├── test_refresh_token_lifecycle.py        # NEW (Plan 09-01, 4 tests sync)
└── test_refresh_token_lifecycle_async.py  # NEW (Plan 09-01, 4 tests async)

packages/iol-client/src/iol_client/
└── _state.py                              # MODIFY (D-09 delete account_id field + docstring)

packages/higyrus-client/src/higyrus_client/
└── _state.py                              # MODIFY (D-09 delete account_id field + docstring)

packages/higyrus-client/tests/
└── test_multi_account.py                  # NEW (Plan 09-02, mocked 2-cuenta loop)

packages/matriz-client/src/matriz_client/
└── _core.py                               # MODIFY (Plan 09-03 add hybrid guard at line 423-441)

packages/matriz-client/tests/
└── test_core.py                           # EXTEND (Plan 09-03 add test_get_instruments_by_cfi_validates_cfi_code)

main_higyrus.py                            # EXTEND (Plan 09-02 add probe_multi_account_iteration)
.planning/verification/
├── matriz-client-findings.md              # UPDATE (F-09 CONFIRMED → FIXED + Regression: link)
└── higyrus-client-findings.md             # UPDATE (F-02 OPEN → bucket outcome + Regression: link)

.planning/phases/09-deferred-bug-fixes/
└── 09-VALIDATION.md                       # NEW (Plan 09-04 CI evidence)
```

### Pattern 1: Single-Site Guard in `_core.py` Builder (BUG-01)

**What:** El builder `build_get_instruments_by_cfi_request` valida `cfi_code` antes de construir el `RequestSpec`. Si inválido, levanta `PrimaryAPIError(status="ERROR")` pre-HTTP. El cliente sync y async reusan el mismo builder vía Phase 7 REFAC-03.

**When to use:** Pre-condition checks que dependen de input del caller (no del response). El single-site fix propaga a sync + async sin duplicación.

**Example:**
```python
# packages/matriz-client/src/matriz_client/_core.py
# Source: CONTEXT.md D-01 + verified via uv run python smoke test
from __future__ import annotations
import re
from typing import get_args
from .exceptions import PrimaryAPIError
from .types import CFICode

# Module-level constants (Phase 7 idiom + zero runtime overhead post-import)
_CFI_ISO_RE = re.compile(r"^[A-Z]{6}$")
_CFI_LITERAL_VALUES = frozenset(get_args(CFICode))  # 9 valores actuales


def build_get_instruments_by_cfi_request(
    state: _ClientState,
    cfi_code: CFICode,
) -> RequestSpec:
    """``GET /rest/instruments/byCFICode?CFICode=...`` con guard hybrid (BUG-01)."""
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

### Pattern 2: pytest-httpx Mock for OAuth Refresh Flow (BUG-03)

**What:** Tests del lifecycle del refresh_token usan `httpx_mock.add_response(..., match_content=b"...")` para distinguir el grant `refresh_token` del grant `password`. El autouse fixture en `conftest.py` precarga el state vía `configure(token=..., token_expires_at=...)`.

**When to use:** Cualquier test que ejercite el flow `_ensure_token()` → `_refresh()` vs `login()`. Patrón ya en uso en `test_client.py:154-251` y `test_async_client.py:116-...`.

**Example:**
```python
# packages/iol-client/tests/test_refresh_token_lifecycle.py
# Source: pattern derived from existing test_client.py:154-251
from __future__ import annotations

import pytest
import iol_client
from iol_client.exceptions import IOLAuthError
from pytest_httpx import HTTPXMock


def test_refresh_success_path_uses_refresh_token_grant(httpx_mock: HTTPXMock) -> None:
    """Path 1: refresh→success — refresh_token grant succeeds, token rotated.

    Seed: state.refresh_token="seed-refresh-XYZ", state.token_expires_at=0.0 (expired).
    Mock: POST /token (refresh grant) → 200 {access_token, expires_in, refresh_token}.
    Assert: state.token updated, state.refresh_token rotated, exactly 1 outgoing request.
    """
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "seed-refresh-XYZ"

    httpx_mock.add_response(
        method="POST",
        url="https://api.test/token",
        match_content=b"refresh_token=seed-refresh-XYZ&grant_type=refresh_token",
        status_code=200,
        json={"access_token": "NEW-TOK", "expires_in": 900, "refresh_token": "ROTATED-REFRESH"},
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    assert state.refresh_token == "ROTATED-REFRESH"
    # Exactly 2 outgoing requests: refresh + endpoint
    assert len(httpx_mock.get_requests()) == 2
```

### Pattern 3: Probe-Scoped DEBUG Logging (BUG-02 triage)

**What:** Activar `logging.DEBUG` solo durante el probe específico, evitando contaminación cross-test. Usa `logging.getLogger("higyrus_client").setLevel(DEBUG)` con `try/finally` para reset al final.

**When to use:** Diagnostic triage que requiere visibilidad de wire request/response sin habilitar DEBUG globalmente.

**Example:**
```python
# main_higyrus.py — driver probe pattern (Plan 09-02 BUG-02 triage)
import logging

def probe_get_listado_cuentas_with_debug() -> ProbeResult:
    """BUG-02 quick triage: DEBUG-level logging probe-scoped."""
    logger = logging.getLogger("higyrus_client")
    original_level = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        cuentas = higyrus_client.get_listado_cuentas(estado="alta")
        # Bucket classification logic (a/b/c) goes here
        return classify_outcome(cuentas)
    finally:
        logger.setLevel(original_level)
```

### Pattern 4: Multi-Account Driver Probe (BUG-04)

**What:** Driver loopea sobre N cuentas (source: env var override, live `get_listado_cuentas`, o hardcoded fallback) y ejercita endpoints account-dependent por cada una. Acumula outcome y reporta PASS/FINDING/SKIPPED.

**When to use:** Live verification que la API soporta multi-account iteration end-to-end.

**Example:**
```python
# main_higyrus.py — Plan 09-02 BUG-04
import os

def probe_multi_account_iteration() -> ProbeResult:
    """Probe BUG-04: iterate over ≥2 cuentas y ejerce endpoint account-dep."""
    cuentas_str = os.getenv("HIGYRUS_SAMPLE_CUENTAS", "").strip()
    if cuentas_str:
        cuentas = [c.strip() for c in cuentas_str.split(",") if c.strip()]
    else:
        live_cuentas = higyrus_client.get_listado_cuentas(estado="alta")
        cuentas = [c.idCuenta for c in live_cuentas[:2]] if len(live_cuentas) >= 2 else []
    if len(cuentas) < 2:
        return ProbeResult(
            "multi_account_iteration",
            "SKIPPED",
            "need ≥2 cuentas; set HIGYRUS_SAMPLE_CUENTAS=A,B",
        )
    for acct in cuentas[:2]:
        try:
            higyrus_client.get_movimientos(
                id_cuenta=acct,
                fecha_desde=dt.date.today(),
                fecha_hasta=dt.date.today(),
            )
        except HigyrusAPIError as exc:
            return ProbeResult("multi_account_iteration", "FINDING", f"{acct}: {exc}")
    return ProbeResult(
        "multi_account_iteration",
        "PASS",
        f"iterated {len(cuentas[:2])} cuentas successfully",
    )
```

### Pattern 5: Parametric Test for Bucket Coverage (BUG-01)

**What:** Single `@pytest.mark.parametrize` test cubre los 3 buckets (literal-known, regex-forward-compat, malformed) con N casos por bucket.

**When to use:** Validación de input categórica donde hay clases distintas de valid/invalid.

**Example:**
```python
# packages/matriz-client/tests/test_core.py — Plan 09-03 BUG-01
import pytest
from matriz_client._core import build_get_instruments_by_cfi_request
from matriz_client._state import _ClientState
from matriz_client.exceptions import PrimaryAPIError

@pytest.mark.parametrize(
    "cfi,expect_raise",
    [
        # Literal-known bucket (5 valores del Literal CFICode)
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
            build_get_instruments_by_cfi_request(state, cfi)  # type: ignore[arg-type]
        assert exc_info.value.status == "ERROR"
        assert "CFI inválido" in (exc_info.value.description or "")
    else:
        spec = build_get_instruments_by_cfi_request(state, cfi)  # type: ignore[arg-type]
        assert spec.params == {"CFICode": cfi}
```

### Anti-Patterns to Avoid

- **Validating CFI in `raise_for_response`:** Anti-pattern. `raise_for_response` solo recibe `httpx.Response` — no ve el `cfi_code` param. El guard tiene que vivir aguas arriba en el builder donde el input es visible (D-02 deviation rationale).
- **Removing `_state.account_id` sin verificar `_state.account_id` vs `RequestSpec.account_id`:** Anti-pattern. Son fields DISTINTOS — `RequestSpec.account_id` es para log correlation (Phase 8 D-11) y NO se toca. El planner debe grep ambos cuidadosamente.
- **DEBUG logging módulo-level en triage:** Anti-pattern. Habilitar `logger.setLevel(DEBUG)` a nivel módulo contamina tests. Probe-scoped con `try/finally` es el patrón seguro.
- **Test que asume server siempre rota refresh_token:** Anti-pattern. CR-01 conditional rotation: el server PUEDE omitir refresh_token. Tests deben cubrir ambos branches (path 3 omite, path 4 rota).
- **Driver dual-flow (`login_sync()` + `login_async()`) sin reset entre flows:** Anti-pattern documentado en Phase 4 BUG-02 hypothesis (a) — `_capture_*_query_string` mutaba `event_hooks` shared (CR-07). Phase 9 NO arregla CR-07 (Phase 11 territory) pero el triage debe tenerlo en mente como hipótesis.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CFI Literal value extraction at runtime | Hardcoded list duplicado en `_core.py` | `frozenset(get_args(CFICode))` | El Literal en `types.py` es source of truth; duplicarlo introduce drift latente. |
| Regex CFI validation | Manual char-by-char loop | `re.compile(r"^[A-Z]{6}$")` module-level | stdlib `re` está optimizado; compile-once pattern es Phase 7 idiom. |
| Form-encoded body matching en tests | Construir bytes manualmente con `urllib.parse` | `match_content=b"refresh_token=...&grant_type=..."` (pytest-httpx) | El test ya conoce el body exacto que el cliente genera (CR-01 path); literal bytes es expressivo y forensic-localizable. |
| Multi-account env var parsing | Custom JSON o YAML config | `os.getenv("HIGYRUS_SAMPLE_CUENTAS", "").split(",")` | `python-dotenv` no soporta arrays nativos; CSV es el idiom estándar (Phase 4 D-HIGY-11 precedent). |
| OAuth refresh flow logic | Custom retry/fallback en `client.py` | `_ensure_token()` con refresh→password fallback ya implementado (Phase 6 D-IOL-10) | Código ya validado por Phase 6 conftest migration + Phase 8 401-re-auth-once integration. |
| Probe-scoped DEBUG context manager | Custom `_logging.py` helper en Phase 9 | `try/finally` con `setLevel(DEBUG)` literal en el probe | Helper es scope-creep — defer a v1.2 si emerge necesidad. |

**Key insight:** Phase 9 explota infraestructura YA construida (Phase 6 `_state`, Phase 7 `_core`, Phase 8 logging/retries). El error sería re-implementar primitivas que ya existen o agregar capas de abstracción nuevas. **Cuando dudes, busca primero si existe el helper** — `pytest-httpx.match_content`, `typing.get_args`, `re.compile`, `_logging.RedactingFilter` cubren los 4 bugs.

## Runtime State Inventory

Phase 9 toca pocos archivos pero implica un campo cross-package muerto + algunas inversiones de findings. El siguiente inventario completa el "qué cambia en runtime" post-Phase 9:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | None — no DB/datastores en este monorepo (clientes HTTP). Findings files (`*-findings.md`) son texto editado manualmente, NO datastore runtime. | None |
| **Live service config** | None — Phase 9 NO toca env vars existentes (`HIGYRUS_USER`, `HIGYRUS_PASSWORD`, `IOL_USER`, etc.). | Operator opcional: setear `HIGYRUS_SAMPLE_CUENTAS=A,B` para el live re-run de Plan 09-02 si `get_listado_cuentas` retorna `[]` (Phase 4 BUG-02 baseline). |
| **OS-registered state** | None — sin task schedulers, daemons, registros de OS. `ws_client.py` daemon thread (matriz) NO se toca en Phase 9 (Phase 10 territory). | None |
| **Secrets/env vars** | `_state.account_id` field referenced en CONTEXT.md/docstrings de `_state.py` (iol + higyrus). NO secrets ni env vars relacionados con el campo. | Plan 09-02: D-09 cleanup — delete field declaration + update module docstring removing "forward-declared for Phase 9 BUG-04" comment. |
| **Build artifacts / installed packages** | None — Phase 9 no instala paquetes nuevos. `uv.lock` no cambia. Snapshot público (`verification/snapshots/<pkg>-surface.txt`) NO cambia (BUG-01..04 no modifican signatures públicas; `_state` es privado). | Plan 09-04 valida zero diff de snapshots vía `verification/test_public_surface.py`. |

**Cross-package state field cleanup (D-09):**
```bash
# Sites a tocar (grep verificado):
packages/iol-client/src/iol_client/_state.py:25      # docstring mention
packages/iol-client/src/iol_client/_state.py:29      # docstring mention
packages/iol-client/src/iol_client/_state.py:84      # field declaration
packages/higyrus-client/src/higyrus_client/_state.py:36   # docstring mention
packages/higyrus-client/src/higyrus_client/_state.py:97   # docstring mention
packages/higyrus-client/src/higyrus_client/_state.py:98   # field declaration

# NO tocar (verificado, son RequestSpec.account_id distinto field):
packages/higyrus-client/src/higyrus_client/client.py:254-306  # D-11 propagation
packages/higyrus-client/tests/test_transport.py:33-258        # D-11 tests
packages/higyrus-client/tests/test_logging.py:166-177         # D-11 sanity
verification/snapshots/matriz-client-surface.txt:47-51        # public API params (Orders endpoints — diferente)
```

## Common Pitfalls

### Pitfall 1: Removing `_state.account_id` confunde con `RequestSpec.account_id`

**What goes wrong:** El planner busca `account_id` y encuentra ~30 referencias entre `_state.py`, `_core.py`, `client.py`, tests/, snapshots/. Algunas son el field a remover (D-09); la mayoría son `RequestSpec.account_id` (Phase 8 D-11 log correlation) que NO se toca.

**Why it happens:** Mismo nombre, dos features completamente distintos. La separación está documentada en CONTEXT.md pero requiere disciplina.

**How to avoid:**
1. Grep solo en `_state.py` files: `grep -n "account_id" packages/*/src/*/state.py`
2. Confirmar que el delete toca SOLO `field declaration + docstring` — NUNCA `RequestSpec`, `request.extensions["account_id"]`, o tests de transport.
3. Snapshot público debe quedar idéntico post-delete (Plan 09-04 valida).

**Warning signs:** Cualquier diff en `verification/snapshots/*-surface.txt`, en `tests/test_transport.py`, o en `tests/test_logging.py::test_account_id_not_redacted` indica que el alcance se descontroló.

### Pitfall 2: Autouse `configure()` fixture leaks token state entre tests

**What goes wrong:** Test A precarga `state.token=None`, `state.refresh_token="seed"`. Test B asume el autouse fixture lo resetea a `token="test-token"`. Si A no resetea o B falla esperando refresh_token=None, hay contaminación cross-test.

**Why it happens:** El autouse fixture en `conftest.py` llama `configure(token="test-token", token_expires_at=9_999_999_999.0)` AL ENTRAR pero el teardown llama `configure(base_url=..., username="", password="")` SIN tocar token. Si un test mutó `state.token=None` para forzar refresh, el siguiente test no ve token cacheado.

**How to avoid:**
- Cada test del Plan 09-01 (BUG-03) muta el state explícitamente en su body (`state.token = None; state.refresh_token = "seed-X"`). No dependas de defaults entre tests.
- En el teardown, considerá agregar `state.refresh_token = None` explícito si quedan side effects (verificar caso por caso).
- `httpx_mock.assert_all_responses_were_requested=True` (default) detectará si un test mockeó responses no consumidas — bueno para detectar tests que fallan silenciosamente.

**Warning signs:** Tests que pasan individualmente pero fallan en suite, o tests que muestran "request count = N+1" cuando esperan N.

### Pitfall 3: `httpx_mock.add_response` order matters cuando hay múltiples mocks por URL

**What goes wrong:** Path 2 (refresh→401→password fallback) requiere DOS mocks para `POST /token`: primero 401, luego 200. pytest-httpx consume mocks **en orden de registro** cuando los matchers (URL+method) coinciden.

**Why it happens:** `pytest-httpx` no usa LIFO ni LRU — usa FIFO con matcher resolution. Si registramos primero el password grant 200, el refresh 401 nunca se consume.

**How to avoid:**
- Usá `match_content=b"refresh_token=..."` vs `match_content=b"username=...&password=..."` para DISTINGUIR los 2 mocks. Esto es el patrón en uso en `test_client.py:171, 208`.
- Verificá `len(httpx_mock.get_requests()) == 2` al final del test.

**Warning signs:** Tests donde el assert `state.token == "tok-from-password"` falla y `state.token` resulta ser `"tok-after-refresh"` — el cliente reusó el primer mock (que registramos como password en vez de refresh).

### Pitfall 4: `typing.get_args(CFICode)` orden no-determinístico en versiones antiguas de Python

**What goes wrong:** Pre-Python 3.10, `typing.get_args` podía retornar valores en orden diferente al de declaración del Literal. Tests que asumen orden pueden fallar.

**Why it happens:** PEP 586 (Literal types) garantiza orden de declaración solo a partir de Python 3.10+. El proyecto target es Python 3.12+ así que esto NO aplica.

**How to avoid:**
- Usar `frozenset(get_args(CFICode))` en vez de `tuple(get_args(...))` — frozenset es order-independent.
- Verified via `uv run python -c "from typing import get_args, Literal; T = Literal['A', 'B', 'C']; print(get_args(T))"` retorna `('A', 'B', 'C')` en Python 3.12+. Sin sorpresas.

**Warning signs:** Tests que comparan `get_args(CFICode)` con un tuple literal en orden — re-hacelo a `set(get_args(CFICode)) == {"A", "B", ...}`.

### Pitfall 5: Probe-scoped logging level leak via library loggers

**What goes wrong:** El probe `probe_get_listado_cuentas_with_debug` activa `logger.setLevel(DEBUG)`. Si el probe lanza una excepción no capturada antes del `setLevel(original_level)` final, el nivel queda en DEBUG para el resto del driver run y leakea a probes posteriores.

**Why it happens:** Sin `try/finally`, una excepción salta del scope y el nivel original nunca se restaura.

**How to avoid:**
- SIEMPRE envolver el body en `try/finally` con `logger.setLevel(original_level)` en el `finally`.
- Alternativa: `with` context manager helper (NO en scope Phase 9 — defer a v1.2).

**Warning signs:** Output del driver muestra DEBUG records de probes que no eran objetivo de triage.

### Pitfall 6: `_state.refresh_token` autouse fixture cleanup

**What goes wrong:** Los tests del Plan 09-01 mutan `state.refresh_token = "seed-X"`. Si el teardown del autouse fixture (líneas 37-38 de `conftest.py`) no resetea explícitamente refresh_token, el siguiente test arranca con `state.refresh_token = "seed-X"` de un test previo.

**Why it happens:** El autouse fixture llama `iol_client.configure(base_url=..., username="", password="")` sin tocar refresh_token. Cierre del default client + reconfigure no resetea state.refresh_token a None.

**How to avoid:**
- Cada test del Plan 09-01 hace setup explícito de `state.refresh_token` al inicio. Test 3 y 4 (CR-01 paths) hardcodean `state.refresh_token="STABLE-REFRESH"` o `"OLD-REFRESH"` antes de iniciar.
- Considerar agregar `state.refresh_token = None` al teardown del conftest si los tests detectan contaminación. Verificar caso por caso — quizás los tests existentes (`test_refresh_token_success_path` etc) ya manejan esto bien.

**Warning signs:** Tests que pasan en isolation (`pytest test_refresh_token_lifecycle.py::test_X`) pero fallan en suite full.

### Pitfall 7: `should_be_used=False` no aplica a `add_response` (solo a fixture-level config)

**What goes wrong:** El planner intenta agregar un mock "opcional" con `add_response(..., should_be_used=False)`. Esto no es un parámetro válido en `add_response`.

**Why it happens:** Confusión entre `assert_all_responses_were_requested=False` (fixture-level config, vía `@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)`) vs un per-response flag inexistente.

**How to avoid:**
- Si necesitas que algún mock pueda no consumirse, decorá el test con `@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)`. Patrón ya en uso en `tests/test_transport.py:41, 104` de los 3 paquetes.
- Mejor: diseñá los tests para que TODOS los mocks registrados se consuman exactamente una vez. Es el contract más limpio.

**Warning signs:** `pytest_httpx.exceptions.TimeoutException` o assertion errors sobre responses no consumidas.

### Pitfall 8: BUG-02 hipótesis (a) — dual sync+async login en el driver mismo proceso

**What goes wrong:** `main_higyrus.py` ejecuta `probe_login_sync` luego `probe_login_async` en el mismo proceso. Si el server Higyrus invalida la session anterior cuando hay un re-login, el segundo flow ve `[]` mientras el primero veía `8771 cuentas`.

**Why it happens:** Hipótesis sin confirmar — la Phase 4 documentó 4 hipótesis (a/b/c/d). Esta es (a). El triage de Plan 09-02 mide específicamente: ¿el listado vuelve a 0 después de que async login mata la sesión sync?

**How to avoid:**
- DEBUG logging probe-scoped captura headers + body. Si el sync recibe `[]` POST-async-login en logs, confirmamos hipótesis (a).
- Si confirmamos (a): el fix podría ser (i) serializar para que solo haya UN login por proceso, o (ii) documentar como "do-not-mix-sync-and-async-in-same-process".
- En bucket (c), el fix vive en `_core.py` (D-04 path). En bucket (a) con resolución NO-FIX, el finding queda como `account-state-conditional` documentado.

**Warning signs:** Reproducible 100% cuando sync runs first vs async; NO reproducible cuando solo uno corre — indicador fuerte de hipótesis (a).

### Pitfall 9: matriz live re-run timing — `cycle_closure` no es side-effect-free

**What goes wrong:** Plan 09-03 dice "live re-run de `main_matriz.py` flipea cycle_closure FAIL→PASS". Pero `main_matriz.py` hace 30+ probes contra la API live de remarkets. Si el operador corre el re-run varias veces sin esperar, hay risk de rate-limit lockout.

**Why it happens:** Phase 5 v1.0 estableció D-MATZ-22 (read-only-only probes para evitar lockout). El probe `probe_error_malformed_cfi` que verificamos en Plan 09-03 es READ-ONLY (intenta GET con CFI inválido) pero el resto del driver corre todos los probes en cada run.

**How to avoid:**
- Plan 09-03 documenta el comando EXACTO: `uv run python main_matriz.py` (SIN flag `--live` que es para mutations).
- Operator-manual run con paste evidence (CONTEXT.md recommendation). NO automatizar en step de la phase para evitar accidental re-runs.
- Si rate-limit hit, esperar el cooldown documentado en Higyrus/Matriz support docs antes de retry.

**Warning signs:** HTTP 429 con `Retry-After` headers en los logs del re-run, o probes que reportan SKIPPED por auth_failed cuando previamente reportaron PASS.

### Pitfall 10: Snapshot público diff inesperado post-Phase-9

**What goes wrong:** Plan 09-04 corre `verification/test_public_surface.py` esperando zero diff. Pero un diff aparece (ej: `_state.account_id` removal ripple-effected a un atributo público).

**Why it happens:** `_state` es privado pero a veces dataclass fields se exponen vía `dataclasses.fields()` o reflection. Si algún test/utility deriva surface info del state, el diff aparece.

**How to avoid:**
- Plan 09-04 corre el snapshot test EXPLÍCITAMENTE y captura cualquier diff antes del operator checkpoint.
- Si hay diff: investigation block — revisar si el `_state.account_id` accidentalmente leakea via `client.__init__` signature o algún `**kwargs` propagation.
- Default expected: zero diff. Si hay diff, el plan NO se mergea sin revisión.

**Warning signs:** Cualquier line modified/added/removed en los 4 snapshots de `verification/snapshots/*-surface.txt`.

## Code Examples

### Common Operation 1: Async test mirror with token_lock awareness

```python
# packages/iol-client/tests/test_refresh_token_lifecycle_async.py
# Source: pattern derived from existing test_async_client.py:116-148
from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import aio
from iol_client.exceptions import IOLAuthError


async def test_refresh_success_path_async(httpx_mock: HTTPXMock) -> None:
    """Path 1 async mirror — respeta el token_lock double-checked locking."""
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "seed-refresh-XYZ"

    httpx_mock.add_response(
        method="POST",
        url="https://api.test/token",
        match_content=b"refresh_token=seed-refresh-XYZ&grant_type=refresh_token",
        json={"access_token": "NEW-TOK", "expires_in": 900, "refresh_token": "ROTATED-REFRESH"},
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    await aio.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    assert state.refresh_token == "ROTATED-REFRESH"
    assert len(httpx_mock.get_requests()) == 2
```

### Common Operation 2: CR-01 conditional rotation — server omits refresh_token

```python
def test_refresh_preserves_refresh_token_when_server_omits(httpx_mock: HTTPXMock) -> None:
    """Path 3 (CR-01): server NO rota refresh_token → preserve cached value."""
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "STABLE-REFRESH"

    httpx_mock.add_response(
        method="POST",
        url="https://api.test/token",
        match_content=b"refresh_token=STABLE-REFRESH&grant_type=refresh_token",
        # NO refresh_token field in response — CR-01 conditional rotation
        json={"access_token": "NEW-TOK", "expires_in": 900},
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    # CRITICAL: refresh_token PRESERVED (CR-01 conditional rotation branch FALSE)
    assert state.refresh_token == "STABLE-REFRESH"


def test_refresh_rotates_refresh_token_when_server_rotates(httpx_mock: HTTPXMock) -> None:
    """Path 4 (CR-01): server SÍ rota refresh_token → update cached value."""
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "OLD-REFRESH"

    httpx_mock.add_response(
        method="POST",
        url="https://api.test/token",
        match_content=b"refresh_token=OLD-REFRESH&grant_type=refresh_token",
        json={
            "access_token": "NEW-TOK",
            "expires_in": 900,
            "refresh_token": "NEW-ROTATED-REFRESH",  # server rotates
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    # CRITICAL: refresh_token ROTATED (CR-01 conditional rotation branch TRUE)
    assert state.refresh_token == "NEW-ROTATED-REFRESH"
```

### Common Operation 3: Multi-account mocked iteration (BUG-04)

```python
# packages/higyrus-client/tests/test_multi_account.py
# Source: pattern derived from existing higyrus tests + CONTEXT.md specifics
from __future__ import annotations

import datetime as dt
import pytest
from pytest_httpx import HTTPXMock

import higyrus_client


def test_multi_account_iteration_via_per_call_id_cuenta(
    httpx_mock: HTTPXMock,
) -> None:
    """BUG-04: iterate over ≥2 cuentas y assert wire requests targetean correctamente."""
    # Autouse fixture ya configuró state.token (conftest.py:25-34)
    # Mock 2 cuentas — el endpoint movimientos toma id_cuenta en el path.
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

### Common Operation 4: BUG-02 probe-scoped triage harness

```python
# main_higyrus.py — Plan 09-02 BUG-02 quick triage
import logging

def probe_get_listado_cuentas_triage_sync() -> ProbeResult:
    """BUG-02 quick triage: DEBUG-level capture + 3-bucket classification."""
    logger = logging.getLogger("higyrus_client")
    original_level = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        try:
            cuentas = higyrus_client.get_listado_cuentas(estado="alta")
        except Exception as exc:
            # Bucket DROPPED: unexpected exception → escalación fuera de scope.
            return ProbeResult(
                "get_listado_cuentas_triage",
                "FINDING",
                f"unexpected {type(exc).__name__}: {exc}",
            )
        # Bucket (b): non-empty → FIXED-by-environment.
        if cuentas:
            return ProbeResult(
                "get_listado_cuentas_triage",
                "PASS",
                f"bucket (b) FIXED-by-environment: returned {len(cuentas)} cuentas",
            )
        # Bucket (a) or (c): empty list — operator decide based on N runs.
        # Recommendation: run probe N=3 times. If empty 3/3 → bucket (c).
        # If empty 0-2/3 → bucket (a) transient.
        return ProbeResult(
            "get_listado_cuentas_triage",
            "FINDING",
            "bucket (a) or (c): empty [] — re-run N=3x to classify",
        )
    finally:
        logger.setLevel(original_level)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Defer F-09 with CONFIRMED status indefinitely | Phase 9 BUG-01 fix in `_core.py` builder + regression test + cycle_closure flip | 2026-06-13 (Phase 9) | F-09 closes; matriz no tiene Open ERROR-MAP findings sin Regression |
| Open F-02 with 4 hipótesis sin classify | Phase 9 BUG-02 quick triage time-boxed con 3-bucket outcome | 2026-06-13 (Phase 9) | F-02 cierra OPEN → bucket (a/b/c) explicit |
| Defer IOL refresh_token "para más adelante" | Phase 6 D-IOL-10 code + Phase 9 regression tests cover 4 critical paths | 2026-06-11 (code) + 2026-06-13 (tests) | refresh→success + refresh→401-fallback + CR-01 both branches tested |
| Sin patrón documentado para multi-account higyrus | Per-call only (D-08) — caller loopea sobre cuentas | 2026-06-13 (Phase 9) | Pattern documentado; `Client(account_id=X)` constructor deferred a v1.2 |
| ISO 10962:2015 reference | ISO 10962:2021 [CITED: ISO website] | 2021 (standard update) | Spec confirmed: 6 uppercase Latin letters canonical |
| Custom HTTPX mocking | `pytest-httpx >=0.34` con `match_content` + `assert_all_responses_were_requested` | Project baseline | Idiom estable, en uso desde Phase 1 |
| Module-level globals state | `_ClientState` per-instance dataclass (slots=True) | Phase 6 REFAC-02 | Test isolation via `configure(token=...)` |

**Deprecated/outdated:**
- `monkeypatch.setattr(pkg.client, "_token", X)` Phase 6 Pitfall #1 — el shim PEP 562 es read-only. **No usar** en Plan 09-* tests; usar `configure(token=..., token_expires_at=...)` o mutación directa de `state.token` via `_get_default()._state`.
- `should_be_used=False` per-response flag — **no existe** en pytest-httpx. Usar `@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)` fixture-level.
- "Validate CFI en `raise_for_response`" — descartado por D-02 deviation; el guard vive en el builder pre-HTTP.
- "Constructor `Client(account_id=X)` en Phase 9" — descartado por D-08; defer a v1.2.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Higyrus API endpoint para `get_listado_cuentas` (`/api/cuentas/listadoCuentas`) NO requiere headers especiales o scopes que cambien entre runs | BUG-02 triage | Si requiere scope/header, bucket (c) fix podría no aplicar; triage outcome cambiaría a "escalación HIGY support" (v1.2) |
| A2 | El operator tiene ≥2 cuentas disponibles en su `HIGYRUS_USER` actual (operator confirmó en CONTEXT.md D-10) | BUG-04 live | Si solo 1 cuenta disponible, probe `multi_account_iteration` reporta SKIPPED y BUG-04 cierre depende solo del mocked test |
| A3 | El probe `probe_error_malformed_cfi` (`main_matriz.py:1194`) sigue activo en el lifecycle del driver post-Phase-8 | BUG-01 live | Si el probe fue removido/renombrado en Phase 8, Plan 09-03 debe re-introducirlo. Grep en main_matriz.py confirma que aún existe en línea 1194 (verified). |
| A4 | `assert_all_responses_were_requested=True` default de pytest-httpx no causa false positives en los nuevos tests Plan 09-01 | BUG-03 tests | Si tests mockean 3 responses pero solo consumen 2, el test fallaría con "response not consumed". Plan 09-01 diseña tests con N mocks == N requests esperados. |
| A5 | `_state.account_id` no es leído por código de runtime en producción (solo es field forward-declared) | D-09 cleanup | Si algún site lee `state.account_id` y dispara AttributeError post-delete, Plan 09-02 detectará en CI (mypy strict). Grep verificado: 0 lecturas runtime en `packages/*/src/`. |
| A6 | Phase 8 D-11 (`RequestSpec.account_id` para log correlation) NO depende de `_state.account_id` | D-09 cleanup | Confirmado por grep: `RequestSpec.account_id` se construye en builders desde `id_cuenta` param, no desde `_state.account_id`. |
| A7 | `ISO 10962:2021` no agrega caracteres no-A-Z al CFI format (ej. dígitos, símbolos) | BUG-01 regex | Si versions futuras lo permiten, el regex `^[A-Z]{6}$` rechazará incorrectamente. Wikipedia + onixs.biz confirman: solo A-Z 6 caracteres. Forward-compat segura para next 5+ años. |

**Si esta tabla tiene assumptions:** El discuss-phase YA cerró las decisiones load-bearing (D-01..D-13). Los `[ASSUMED]` aquí son detalles de implementación que el planner puede verificar al planificar — no requieren re-discusión con el usuario.

## Open Questions

1. **¿BUG-02 triage produce bucket (a), (b) o (c) determinístico?**
   - What we know: 4 hipótesis (a/b/c/d) documentadas en Phase 4 finding. 3 runs consecutivos pre-Phase-9 dieron `[]`. Phase 8 retries pueden amortiguar (a) silenciosamente.
   - What's unclear: el outcome del live re-run con DEBUG logging (Plan 09-02 step ejecuta este triage).
   - Recommendation: Plan 09-02 documenta las 3 decision criteria inline (CONTEXT.md D-05). Operator decide al ver el output del live run. Si el outcome es ambiguo (ej: 2 runs dan `[]` + 1 da non-empty), default a bucket (a) NO-FIX + mocked regression test como contract guard.

2. **¿El planner debe agregar `should_consume_credentials` cleanup al teardown del conftest.py de iol-client para tests del Plan 09-01?**
   - What we know: El autouse fixture llama `configure()` con `token="test-token"` pero NO toca `refresh_token` al teardown.
   - What's unclear: Si los 4 nuevos tests del Plan 09-01 (que setean `state.refresh_token` explícito) introducen flakiness sin reset de refresh_token al teardown.
   - Recommendation: Plan 09-01 incluye un test de inspección que corre primero (`test_refresh_token_state_isolated_between_tests`) para detectar contaminación. Si flaky, agregar `state.refresh_token = None` al teardown (defensive).

3. **¿El live re-run de `main_matriz.py` en Plan 09-03 debe correr operador o automation?**
   - What we know: CONTEXT.md Claude's Discretion recommends operator-manual + paste evidence.
   - What's unclear: Si el operator prefiere automation por consistency.
   - Recommendation: operator-manual default. Documentar el comando exacto + expected probe outcomes en el `09-03-PLAN.md` para que paste evidence sea trivial.

4. **¿Plan 09-04 debe incluir un `Step` que regenere snapshots si hay diff intencional?**
   - What we know: CONTEXT.md espera zero diff. Plan 09-04 valida.
   - What's unclear: Si el operator quiere un escape hatch para diff intencional (ej: rename de algún parámetro descubierto durante triage).
   - Recommendation: NO incluir regen en Plan 09-04. Si hay diff, BLOQUEAR y resolver por investigación (operator decision). Diff intencional indica un cambio público no documentado, debe llevarse a discuss-phase si emerge.

## Environment Availability

Phase 9 NO instala paquetes nuevos. Dependencias críticas:

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All tests + runtime | ✓ | 3.12.11 (`.venv/`) | Python 3.13 supported (CI matrix) |
| `uv` package manager | All commands | ✓ | 0.9.0+ | — |
| `pytest` | Test runner | ✓ | 8.3+ | — |
| `pytest-httpx` | Mock HTTPX | ✓ | 0.34+ | — |
| `pytest-asyncio` | Async tests | ✓ | 0.24+ | — |
| `httpx` | Transport | ✓ | 0.27+ | — |
| `python-dotenv` | `.env` loading | ✓ | 1.0+ | — |
| `tenacity` | Retries (Phase 8 inherit) | ✓ | 9.1.4 | — |
| `ruff` | Lint + format | ✓ | 0.7+ | — |
| `mypy` strict | Type check | ✓ | 1.13+ | — |
| Higyrus API live (remarkets-equiv sandbox) | BUG-02 live triage + BUG-04 live probe | ✓ (operator confirms) | — | If down: bucket triage outcome = SKIPPED; multi-account probe SKIPPED; live re-run deferred. Mocked tests still cover regression bases. |
| Matriz API live (remarkets sandbox) | BUG-01 live re-run + cycle_closure flip | ✓ (operator confirms; established baseline `verification-cycle-2026-Q2`) | — | If down: live re-run deferred; mocked test still validates fix; cycle_closure flip happens on next available re-run window. |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Live services (Higyrus + Matriz APIs) en caso de outage — mocked regression tests siempre pasan y bloquean el bug; live re-runs solo necesarios para flipear status de findings (no para correctness del fix).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 8.3+` + `pytest-asyncio 0.24+` (asyncio_mode=auto) + `pytest-httpx 0.34+` |
| Config file | Root `pyproject.toml` [tool.pytest.ini_options] (already present) |
| Quick run command | `uv run pytest packages/<pkg>/tests/<file>.py -x` |
| Full suite command | `uv run pytest --cov` (matrix Python 3.12 + 3.13 en CI) |

### Phase Requirements → Test Map

#### BUG-01 (matriz CFI validation)

| Code path under test | `build_get_instruments_by_cfi_request()` (`_core.py:423-441`) |
|---|---|
| **Failure mode coverage** | (1) literal-known happy path (2) regex forward-compat happy path (3) malformed: lowercase, hyphen, digit, wrong-length, empty — 6 negative cases |
| **State observability** | `pytest.raises(PrimaryAPIError) as exc_info` + `exc_info.value.status == "ERROR"` + `"CFI inválido" in exc_info.value.description` |
| **Sample rate (Nyquist)** | 10 parametric cases cover 3 buckets (literal × 2, regex × 2, malformed × 6) — spans full input categorization |
| **Regression preservation** | If this test had existed pre-Phase 9, F-09 would have failed CI at the point where `_core.py` introduced the un-validated builder — bug blocked from shipping. |

Automated command: `uv run pytest packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code -x`. File exists ✓ (extended in Plan 09-03).

#### BUG-02 (higyrus get_listado_cuentas triage + contract guard)

| Code path under test | `build_get_listado_cuentas_request()` (`_core.py:357-384`) + `parse_get_listado_cuentas_response()` (`_core.py:487-490`) |
|---|---|
| **Failure mode coverage** | (1) happy path: envelope con `[{cuenta}, {cuenta}]` → parsed correctamente (2) [bucket (c) only]: client-side bug que descarta resultados — depende de outcome del triage |
| **State observability** | `len(httpx_mock.get_requests()) == 1` + `len(returned_cuentas) >= 1` para happy path; teardown del DEBUG level |
| **Sample rate (Nyquist)** | Contract guard test mockea el happy path (server returns N cuentas) — si el client devuelve `[]` cuando server devolvió N, contradicción detectada en test. Cubre bucket (c) si el bug es client-side. Live re-run cubre buckets (a)/(b). |
| **Regression preservation** | Si bucket (c), el test bloquea futuras regresiones del fix. Si bucket (a)/(b), el test funciona como guard contra future client-side regressions (no captura el bug original pero previene similares). |

Automated command: `uv run pytest packages/higyrus-client/tests/test_listado_cuentas.py -x` (file new in Plan 09-02 si bucket (c)). File exists: ❌ (creado en Wave 0 dentro de Plan 09-02 si triage produce bucket (c); else extends existing test_client.py).

#### BUG-03 (IOL refresh_token lifecycle — 4 paths × 2 surfaces = 8 tests)

| Code path under test | `_ensure_token()` (`client.py:277-289` sync, `aio.py:259-273` async) + `_refresh()` (`client.py:264-275`, `aio.py:241-252`) + `parse_login_response`/`parse_refresh_response` (`_core.py:169-226`) |
|---|---|
| **Failure mode coverage** | (1) refresh→success: refresh_token grant 200 OK (2) refresh→401→password fallback: refresh revocado + password recovery (3) CR-01 server omits refresh_token: parser retorna None → state.refresh_token preserved (4) CR-01 server rotates refresh_token: parser retorna new value → state.refresh_token updated |
| **State observability** | `state.token`, `state.refresh_token` post-call + `len(httpx_mock.get_requests())` |
| **Sample rate (Nyquist)** | 4 paths span: success branch, fallback branch, CR-01 both branches. Mirror sync + async = 8 tests total. Full lifecycle covered. |
| **Regression preservation** | Si CR-01 conditional rotation se rompe (ej: alguien edita `if refresh is not None:` a `state.refresh_token = refresh`), path 3 falla inmediatamente: `assert state.refresh_token == "STABLE-REFRESH"` se convierte en `state.refresh_token is None`. Bug bloqueado. |

Automated commands:
- `uv run pytest packages/iol-client/tests/test_refresh_token_lifecycle.py -x`
- `uv run pytest packages/iol-client/tests/test_refresh_token_lifecycle_async.py -x`

Files exist: ❌ Wave 0 (new in Plan 09-01).

#### BUG-04 (HIGY multi-account mocked iteration)

| Code path under test | `get_movimientos()` shell (`client.py:348-365`) + `build_get_movimientos_request` con `id_cuenta` param |
|---|---|
| **Failure mode coverage** | (1) 2 cuentas distintas → 2 wire requests con paths distintos (`/5208/movimientos`, `/9999/movimientos`); (2) `RequestSpec.account_id` propaga correctamente al log correlation field (verificar `req.extensions["account_id"]`) |
| **State observability** | `httpx_mock.get_requests()` length + URL inspection per request |
| **Sample rate (Nyquist)** | 2 cuentas mockeadas cubren el caso minimal (single != multi). Más cuentas no agrega cobertura. |
| **Regression preservation** | Si alguien introduce caché de id_cuenta entre calls (ej: `Client(account_id=X)` accidentalmente), el test detecta porque el 2do request iría al primer id_cuenta. |

Automated command: `uv run pytest packages/higyrus-client/tests/test_multi_account.py -x`. File exists: ❌ Wave 0 (new in Plan 09-02).

### Sampling Rate
- **Per task commit:** quick run para el package modificado: `uv run pytest packages/<pkg>/tests/ -x --no-header -q`
- **Per wave merge:** full per-package suite: `uv run pytest packages/<pkg>/tests/ --cov`
- **Phase gate:** Full matrix + ruff + mypy strict + lint-imports + cross-leak sentinel + public surface zero-diff before Plan 09-04 closes.

### Wave 0 Gaps

Plan 09-01:
- [ ] `packages/iol-client/tests/test_refresh_token_lifecycle.py` — covers BUG-03 paths 1+2+3+4 sync
- [ ] `packages/iol-client/tests/test_refresh_token_lifecycle_async.py` — covers BUG-03 paths 1+2+3+4 async

Plan 09-02:
- [ ] `packages/higyrus-client/tests/test_multi_account.py` — covers BUG-04 (mocked 2-cuenta)
- [ ] (Conditional, bucket (c) only) `packages/higyrus-client/tests/test_listado_cuentas_regression.py` — covers BUG-02 client-side fix

Plan 09-03:
- [ ] Extend `packages/matriz-client/tests/test_core.py` con `test_get_instruments_by_cfi_validates_cfi_code` (paramétrico, 10 casos)

Framework install: None — already in `uv.lock` post-Phase 8.

## Security Domain

`security_enforcement: true` (Phase 8 inherited convention). Phase 9 surface check:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (BUG-03 OAuth flow tests) | Existing `_ensure_token()` con refresh→password fallback (Phase 6); tests NO introducen nuevas auth surfaces |
| V3 Session Management | yes (BUG-03 token lifecycle) | `_ClientState.token` + `_ClientState.refresh_token` per-instance; tests validan que CR-01 conditional rotation no leakea tokens |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes (BUG-01 CFI validation) | Hybrid Literal+regex guard pre-HTTP; tests cubren malformed input rejection |
| V6 Cryptography | no | N/A — no crypto hand-roll en Phase 9 |
| V7 Error Handling | yes (BUG-01 `PrimaryAPIError(status="ERROR")`) | Estructurado, tipado, no leakea internals; existing pattern preservado |
| V9 Communication | no | N/A |
| V10 Malicious Code | no | N/A |
| V11 Business Logic | yes (BUG-04 multi-account) | Per-call `id_cuenta` evita cross-account state leak; D-09 elimina field muerto que podría confundir caller en futuro |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hardcoded refresh_token en tests leakea a logs | Information Disclosure | RedactingFilter (Phase 8 D-10) ya activo; tests usan literals como `"seed-refresh-XYZ"` (no real tokens); CI grep rule de Phase 8 confirma no `logging.basicConfig` |
| Token state cross-test contamination (Pitfall 6) | Tampering | Autouse fixture cleanup + test setup explícito; D-09 cleanup de `_state.account_id` reduce surface de error |
| CFI validation bypass via cast (`cast(CFICode, "INVALID-CFI")`) | Input Validation Bypass | Runtime guard hybrid Literal+regex (BUG-01); ya no es bypass-eable post-fix |
| Multi-account cross-account leak | Authorization Bypass | Per-call `id_cuenta` (D-08): el caller siempre pasa la cuenta explícita; sin caché en `_state` (D-09 cleanup) |
| Server omits refresh_token in response (CR-01 case) | Session Management Confusion | `parse_login_response` retorna `None` cuando absent (Phase 6 D-IOL-10); shell guard `if refresh is not None:` preserva el cached value (tests path 3 valida) |

## Sources

### Primary (HIGH confidence)

- **CONTEXT.md (Phase 9):** `.planning/phases/09-deferred-bug-fixes/09-CONTEXT.md` — D-01..D-13 decisions, all canonical references
- **REQUIREMENTS.md §"Bug fixes (BUG)":** `.planning/REQUIREMENTS.md` — BUG-01..BUG-04 literal text + Out of Scope confirmations
- **ROADMAP.md §"Phase 9":** `.planning/ROADMAP.md` — 5 success criteria + Plans TBD slot
- **STATE.md:** `.planning/STATE.md` — current focus + Phase 8 closure context
- **Existing tests baseline (verified via `uv run pytest --collect-only`):** 760 tests collected, 1 deselected post-Phase 8
- **Source code (verified via Read):**
  - `packages/matriz-client/src/matriz_client/_core.py:423-441` (BUG-01 fix site)
  - `packages/matriz-client/src/matriz_client/types.py:50-61` (CFICode Literal — 9 values)
  - `packages/matriz-client/src/matriz_client/exceptions.py:10-28` (PrimaryAPIError signature)
  - `packages/iol-client/src/iol_client/_state.py:80-84` (refresh_token + account_id fields)
  - `packages/iol-client/src/iol_client/client.py:251-289` (login + _refresh + _ensure_token)
  - `packages/iol-client/src/iol_client/aio.py:240-273` (async mirror)
  - `packages/iol-client/src/iol_client/_core.py:142-226` (parse_login_response CR-01)
  - `packages/iol-client/tests/test_client.py:154-251` (existing refresh_token tests — patterns for Plan 09-01)
  - `packages/iol-client/tests/test_async_client.py:116-199` (existing async refresh tests)
  - `packages/iol-client/tests/conftest.py:25-52` (autouse configure fixture)
  - `packages/higyrus-client/src/higyrus_client/_state.py:82-105` (account_id field)
  - `packages/higyrus-client/src/higyrus_client/_core.py:357-384, 487-490` (get_listado_cuentas builder + parser)
  - `packages/higyrus-client/src/higyrus_client/client.py:340-423` (4 account-dependent endpoints)
  - `packages/higyrus-client/tests/conftest.py` (higyrus autouse fixture)
  - `main_matriz.py:1194-1271` (probe_error_malformed_cfi)
  - `main_higyrus.py:138-140, 657-746` (driver structure + env var pattern + probe_get_listado_cuentas)
- **Runtime verification (verified via `uv run python`):**
  - `typing.get_args(Literal['A', 'B', 'C'])` returns tuple in declaration order ✓
  - `re.compile(r'^[A-Z]{6}$').match(...)` produces expected results on 7 input samples ✓
- **Findings files:**
  - `.planning/verification/matriz-client-findings.md` F-09 CONFIRMED detail
  - `.planning/verification/higyrus-client-findings.md` F-02 OPEN + 4 hypotheses
  - `.planning/verification/CYCLE-REPORT.md` DRIFT-02 cycle_closure baseline

### Secondary (MEDIUM confidence)

- **ISO 10962:2015 / ISO 10962:2021 standard** [CITED: [Wikipedia ISO 10962](https://en.wikipedia.org/wiki/ISO_10962), [ISO standard listing](https://www.iso.org/standard/44799.html)] — confirms 6 uppercase Latin letters canonical
- **CFI code FIX Dictionary** [CITED: [Onixs Solutions FIX 5.0 SP2 Appendix 6-D](https://www.onixs.biz/fix-dictionary/5.0.sp2/app_6_d.html)] — confirms format invariance
- **pytest-httpx documentation** [CITED: [pytest-httpx GitHub docs](https://github.com/Colin-b/pytest_httpx)] — `match_content` + `assert_all_responses_were_requested` patterns
- **RFC 6749 §6 OAuth 2.0 Refresh Token grant** [CITED: training knowledge] — `grant_type=refresh_token` form body + response shape (`access_token`, `expires_in`, optional `refresh_token` rotation)

### Tertiary (LOW confidence)

- **Higyrus API session-mutating side effect hypothesis** — BUG-02 hypothesis (a). Sin documentación pública del comportamiento; el triage de Plan 09-02 lo valida empíricamente. Tagged `[ASSUMED]` en Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in `uv.lock`, verified at runtime in current Python 3.12.11 environment
- Architecture: HIGH — Phase 6/7/8 patterns established; Phase 9 reuses without modification of core surfaces
- Pitfalls: HIGH — derived from existing codebase patterns (Phase 6 Pitfall 1, Phase 7 Pitfall 3, Phase 8 Pitfall 4) + new pitfalls (1, 8, 9) specific to Phase 9 boundary conditions
- BUG-02 outcome: LOW — depends on live re-run with DEBUG logging; 3-bucket classification is the methodology, but specific bucket cannot be determined pre-execution
- Live re-run availability: HIGH — Higyrus + Matriz sandboxes have been stable in cycle-2026-Q2 baseline

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (30 days — stable infrastructure, low rate of change in client lib ecosystem)

---

*Phase 9 RESEARCH complete — planner can now create 4 PLAN.md files per CONTEXT.md D-11 (Wave 1 parallel: 09-01 + 09-02; Wave 2: 09-03; Wave 3: 09-04).*
