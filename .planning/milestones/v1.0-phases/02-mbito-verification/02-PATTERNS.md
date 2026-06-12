# Phase 2: Ámbito Verification - Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 8 (3 código, 2 tests append, 2 artefactos generados, 1 barrel)
**Analogs found:** 8 / 8 (todos con match exacto en el repo — no se necesita RESEARCH.md como fallback)

---

## File Classification

| Archivo (nuevo/modificado) | Rol | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `verification/findings.py` | extension (helper module) | file-I/O idempotente (markdown read→mutate→write) | `verification/findings.py` (mismo archivo: `new_findings` + `write_findings`) | exact |
| `verification/__init__.py` | barrel re-export | static re-export | `verification/__init__.py` (l.28–47) | exact (in-place edit) |
| `main_ambito_financiero.py` | driver rewrite (orchestrator) | request-response + file-I/O (findings + schema) | `main_higyrus.py` (driver con `safe_print` + sub-actions) + `main_verify.py` (orchestrator con summary RAN/SKIPPED/FAILED) + `main_ambito_financiero.py` actual (helper `_last_business_day`) | role-match (driver más complejo que cualquier analog actual; combina 3) |
| `packages/ambito-financiero-client/tests/test_client.py` | test append (invariantes + regresiones) | request-response mock | `packages/ambito-financiero-client/tests/test_client.py` (tests existentes con `httpx_mock.add_response(url=...)`) | exact (mismo archivo) |
| `packages/ambito-financiero-client/tests/test_async_client.py` | test append (mirror async) | request-response mock async | `packages/ambito-financiero-client/tests/test_async_client.py` (tests existentes; `async def test_...` sin decorador) | exact (mismo archivo) |
| `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` | generated artifact (committeable) | one-shot JSON dump | `verification/capture.py:42-51` (patrón `mkdir(parents=True) + write_text(json.dumps(...))`) | role-match (analog escribe a gitignored; este es committeable) |
| `.planning/verification/ambito-financiero-client-findings.md` | generated artifact (committeable) | esqueleto markdown + appends sucesivos | `verification/findings.py::write_findings` (l.70-80) + `.planning/verification/FINDINGS-TEMPLATE.md` | exact (template existente, helper existente) |
| `packages/ambito-financiero-client/tests/test_findings_helper.py` (OPCIONAL — recomendado en RESEARCH wave 1) | unit test del helper | in-memory model mutation | `packages/ambito-financiero-client/tests/test_harness_schema.py` + `test_harness_anonymize.py` | exact (precedente Phase 1: tests del harness viven bajo el paquete que primero los usa) |

---

## Pattern Assignments

### 1. `verification/findings.py` — EXTEND con `append_finding`

**Analog:** `verification/findings.py` (mismo archivo — `new_findings` / `write_findings` / `findings_path`).

**Convención obligatoria:** `from __future__ import annotations` ya está en línea 19; mypy strict; double quotes; line-length=100; helpers privados con prefijo `_`.

**Imports pattern** (`verification/findings.py:19-22`):

```python
from __future__ import annotations

from pathlib import Path
```

Para `append_finding` se agregan (RESEARCH Pattern 1):

```python
import datetime as dt
from dataclasses import dataclass
```

**Module-level constants pattern** (`verification/findings.py:25-41`):

```python
# Raíz del repo = el directorio que contiene el paquete ``verification/``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_FINDINGS_DIR = _REPO_ROOT / ".planning" / "verification"

# Clases fijas de hallazgos (D-09) — orden documentado.
FINDING_CLASSES: tuple[str, ...] = (
    "SHAPE",
    "AUTH",
    "ERROR-MAP",
    "PARAM",
    "SYNC-ASYNC-DRIFT",
    "NO-DATA",
    "ANTI-BOT",
)

# Ciclo de estados (D-08) — sin campo de severidad.
STATUS_LIFECYCLE: tuple[str, ...] = ("OPEN", "CONFIRMED", "FIXED", "EXPECTED", "NO-FIX")
```

**Path-resolution pattern para `append_finding`** (reusar `findings_path`, `verification/findings.py:44-46`):

```python
def findings_path(pkg: str) -> Path:
    """Ruta del archivo de hallazgos para ``pkg``: ``.planning/verification/<pkg>-findings.md``."""
    return _FINDINGS_DIR / f"{pkg}-findings.md"
```

**Skeleton-write pattern para idempotencia** (`verification/findings.py:70-80`):

```python
def write_findings(pkg: str, *, overwrite: bool = False) -> Path:
    """Crea ``.planning/verification/<pkg>-findings.md`` con el esqueleto y devuelve la ruta.

    Si el archivo ya existe y ``overwrite`` es ``False``, no lo sobreescribe.
    """
    _FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = findings_path(pkg)
    if path.exists() and not overwrite:
        return path
    path.write_text(new_findings(pkg), encoding="utf-8")
    return path
```

**`append_finding` debe extender este patrón:** llama `write_findings(pkg)` para garantizar esqueleto, luego lee, parsea a modelo interno, muta por `fid`, re-serializa completo y escribe.

**`__all__` pattern** (`verification/findings.py:23`):

```python
__all__ = ["FINDING_CLASSES", "STATUS_LIFECYCLE", "findings_path", "new_findings", "write_findings"]
```

Agregar `"append_finding"` (ordenado alfabéticamente). Si se crea `_Finding` dataclass público para tests, agregarlo también — si es privado, no.

**Module docstring pattern** (`verification/findings.py:1-17`):

```python
"""Helper de archivo de hallazgos clasificados (HARN-05/D-07/08/09).

El entregable primario es la plantilla documentada
``.planning/verification/FINDINGS-TEMPLATE.md``; este módulo es un helper de
conveniencia que renderiza el esqueleto de encabezado + índice para iniciar un
archivo de hallazgos por paquete en ``.planning/verification/<pkg>-findings.md``.

Clases fijas (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA,
ANTI-BOT. Ciclo de estados (D-08): OPEN -> CONFIRMED -> FIXED, más terminales
EXPECTED/NO-FIX. No hay campo de severidad.

Uso::

    from verification.findings import new_findings, write_findings

    write_findings("higyrus")   # crea .planning/verification/higyrus-findings.md
"""
```

Extender el docstring describiendo `append_finding` (uso, idempotencia por `fid`, preservación de status humano cuando `status not in {"OPEN"}`).

**Skeleton format que `append_finding` debe respetar** (`verification/findings.py:49-67`):

```python
def new_findings(pkg: str) -> str:
    """Renderiza el esqueleto (encabezado ART + índice vacío) de un archivo de hallazgos."""
    classes = ", ".join(FINDING_CLASSES)
    lifecycle = " -> ".join(("OPEN", "CONFIRMED", "FIXED")) + " (+ terminal EXPECTED/NO-FIX)"
    return (
        f"# Findings: {pkg}-client\n"
        "\n"
        "## Run Context (ART)\n"
        "- Timestamp: <ISO-8601>\n"
        "- Resolved base URL / env: <url> (<remarkets|prod|public>)\n"
        "- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>\n"
        "\n"
        f"<!-- Clases (D-09): {classes} -->\n"
        f"<!-- Estados (D-08): {lifecycle}. Sin campo de severidad. -->\n"
        "\n"
        "## Index\n"
        "| ID | Class | Surface | Status |\n"
        "|----|-------|---------|--------|\n"
    )
```

**Sección "## Detalle por hallazgo"** referencia plantilla `.planning/verification/FINDINGS-TEMPLATE.md:67-85` (formato exacto del per-finding block: header `### F-NN -- <título>`, líneas `**Class:** ... **Surface:** ... **Status:** ...`, bullets `- **Expected:**`, `- **Actual:**`, `- **Diff:**`, `- **Regression:**`).

**Idempotencia y preservación de status humano** — patrón nuevo derivado de `write_findings` + RESEARCH Pattern 1:

```python
# Pseudocódigo (RESEARCH Open Question 1 / Pitfall 1):
def append_finding(pkg, *, fid, class_, surface, status, title, expected, actual, diff,
                   regression=None, base_url=None, market_hours=None) -> Path:
    path = findings_path(pkg)
    if not path.exists():
        write_findings(pkg)  # crea esqueleto idempotente
    text = path.read_text(encoding="utf-8")
    findings_list, art = _parse_findings(text)
    art["Timestamp"] = dt.datetime.now(dt.UTC).isoformat()
    if base_url is not None:
        art["Resolved base URL / env"] = base_url
    if market_hours is not None:
        art["Market hours note"] = market_hours
    existing = {f.fid: f for f in findings_list}
    # Pitfall 1: NUNCA pisar status promovido por humano
    if fid in existing and existing[fid].status != "OPEN":
        path.write_text(_serialize_findings(pkg, findings_list, art), encoding="utf-8")
        return path
    new = _Finding(fid, class_, surface, status, title, expected, actual, diff, regression)
    if fid in existing:
        findings_list = [new if f.fid == fid else f for f in findings_list]
    else:
        findings_list.append(new)
    path.write_text(_serialize_findings(pkg, findings_list, art), encoding="utf-8")
    return path
```

**Validación obligatoria con `FINDING_CLASSES` / `STATUS_LIFECYCLE`** — `append_finding` debe levantar `ValueError` si `class_ not in FINDING_CLASSES` o `status not in STATUS_LIFECYCLE` (RESEARCH Open Question 1: contrato explícito; mypy strict no captura strings inválidos).

---

### 2. `verification/__init__.py` — EXTEND barrel

**Analog:** mismo archivo, líneas 28–47.

**Import + `__all__` pattern** (`verification/__init__.py:28-47`):

```python
from verification.anonymize import Denylist, anonymize
from verification.capture import capture
from verification.env_gate import require_env
from verification.findings import new_findings, write_findings
from verification.mutation_gate import mutating_allowed
from verification.redaction import redact, safe_print
from verification.schema import schema_of

__all__ = [
    "Denylist",
    "anonymize",
    "capture",
    "mutating_allowed",
    "new_findings",
    "redact",
    "require_env",
    "safe_print",
    "schema_of",
    "write_findings",
]
```

**Cambio Phase 2:** agregar `append_finding` a ambos: `from verification.findings import append_finding, new_findings, write_findings` y en `__all__` (orden alfabético — entre `anonymize` y `capture`).

**Docstring que también debe extenderse** (`verification/__init__.py:18-19`):

```python
- :mod:`verification.findings` — ``new_findings`` / ``write_findings``: plantilla
  de hallazgos (HARN-05).
```

Agregar `append_finding` a la descripción (HARN-05 + D-10).

---

### 3. `main_ambito_financiero.py` — REWRITE COMPLETO

**Analog principal:** `main_higyrus.py` (driver con `safe_print` + secrets vacíos OK por D-26).
**Analog secundario:** `main_verify.py` (orchestrator con summary aggregator).
**Analog tercero:** `main_ambito_financiero.py` actual (l.17-22 helper `_last_business_day` reusable + módulo docstring).

**Convención obligatoria:** `from __future__ import annotations`; mypy strict (firmas completas en cada `probe_*`); ruff line-length=100; double quotes; sin wildcard imports; sin relative imports.

**Module docstring pattern** (`main_ambito_financiero.py:1-8` actual):

```python
"""Smoke test del paquete `ambito-financiero-client`.

Uso::

    uv run --package ambito-financiero-client python main_ambito_financiero.py

No requiere credenciales: la API pública de Ámbito no usa auth.
"""
```

**Reescribir como** docstring que enumere los 7 probes (D-01) + opt-in `VERIFY_ANTIBOT=1` (D-12) + qué artefactos genera (findings markdown + schema JSON).

**Imports pattern** (combinación `main_higyrus.py:14-19` + `main_ambito_financiero.py:11-14` + RESEARCH Pattern 2):

```python
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

import ambito_financiero_client as ambito
from ambito_financiero_client import aio
from ambito_financiero_client._parsing import parse_ar_decimal
from verification import safe_print, schema_of, write_findings
from verification.findings import append_finding
```

**Convención cross-paquetes** (`main_higyrus.py:17`): `from verification import ...` (barrel), NO `from verification.redaction import safe_print` directo.

**Helper reusable existente** (`main_ambito_financiero.py:17-22`):

```python
def _last_business_day(today: dt.date) -> dt.date:
    """Lunes->viernes anterior; cualquier otro día -> el día previo."""
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:  # 5 = sábado, 6 = domingo
        d -= dt.timedelta(days=1)
    return d
```

Reusar tal cual. Agregar adyacente (D-24, AMB-03):

```python
def _last_business_day_with_day_gt_12(today: dt.date) -> dt.date:
    """Día hábil anterior con date.day > 12 (descarta MM/DD-vs-DD/MM ambigüedad)."""
    d = _last_business_day(today)
    while d.day <= 12:
        d -= dt.timedelta(days=1)
        while d.weekday() >= 5:
            d -= dt.timedelta(days=1)
    return d
```

**Acceso a estado privado del cliente** (precedente: `verification/mutation_gate.py:55`):

```python
base = matriz_client.client._base_url  # estado resuelto en vivo; sólo lectura
```

Phase 2 aplica el mismo patrón en el driver para leer `ambito.client._base_url` y `ambito.client._DEFAULT_USER_AGENT` (Pitfall 8: NO duplicar el UA). Subrayar comentario "sólo lectura" para mypy strict / ruff (no es violación; convención `_` por documentación, no enforcement).

**Acceso al payload crudo del endpoint** (`packages/ambito-financiero-client/src/ambito_financiero_client/client.py:66-69`):

```python
def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    resp = _client.request(method, f"{_base_url}{path}", **kwargs)
    _raise_for_response(resp)
    return resp
```

Patrón del probe (RESEARCH Pattern 2): el driver llama `ambito.client._request("GET", path)` directamente para inspeccionar el JSON crudo (`rows`) además del valor final de `ambito.get_dollar_banco_nacion(date)`. Coherente con el patrón ya usado en `tests/test_client.py:21,27` que también accede a `ambito.client._request` directo.

**Driver-orchestrator summary pattern** (`main_verify.py:83-97`):

```python
def main() -> None:
    print("== verificación agregada (RAN/SKIPPED/FAILED por paquete) ==")
    results: list[tuple[str, str]] = []
    for package, script in _DRIVERS:
        status = _run_driver(package, script)
        # Sólo el estado por paquete; nunca el payload completo del hijo.
        print(f"{status:<8} {package}")
        results.append((package, status))

    ran = sum(1 for _, s in results if s == "RAN")
    skipped = sum(1 for _, s in results if s == "SKIPPED")
    failed = sum(1 for _, s in results if s == "FAILED")
    print("== resumen ==")
    print(f"RAN: {ran}  SKIPPED: {skipped}  FAILED: {failed}  (total: {len(results)})")
```

Adaptar a Phase 2 (RESEARCH Pattern 2): `results: list[ProbeResult]`; en lugar de `RAN/SKIPPED/FAILED` por paquete, usar `PASS/FAIL/SKIPPED/FINDING` por probe; al final imprimir `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N` (D-02).

**`@dataclass` para `ProbeResult`** — sigue convención de `verification/anonymize.py:34-46` (`@dataclass(frozen=True, slots=True)`):

```python
@dataclass(frozen=True, slots=True)
class ProbeResult:
    name: str
    status: str   # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str
```

**`safe_print` con `secrets=[]` pattern** (`main_higyrus.py:38,44` adaptado a D-26):

```python
# main_higyrus.py l.31-44 (con secrets reales):
secrets = [
    v for v in (os.getenv("HIGYRUS_USER"), os.getenv("HIGYRUS_PASSWORD")) if v and len(v) >= 4
]
safe_print(f"   {higyrus_client.get_health()}", secrets)
```

**Cambio Phase 2 / D-26:** Ámbito no tiene credenciales → `safe_print(text, secrets=[])` (lista vacía) para uniformidad cross-paquetes. Verificado en `verification/redaction.py:55-59`: la lista vacía es benigna (loop no-op) + el `_BEARER` regex sigue funcionando como segunda capa.

**Driver "continúa todos los probes" pattern** (`main_verify.py:60-65,75-80` + D-04):

```python
try:
    result = subprocess.run(...)
except OSError as exc:
    print(f"   no se pudo ejecutar: {type(exc).__name__}")
    return "FAILED"
```

Cada probe en Phase 2 atrapa excepciones en su propio nivel (RESEARCH Pattern 2 — bloque `try/except` por probe que genera un `FINDING` + `ProbeResult`), nunca corta el run. Excepción única: crash inesperado fuera de un `probe_*` (entonces propaga). Esto cumple D-04: exit 0 siempre salvo crash inesperado.

**Async lifecycle pattern** (`packages/ambito-financiero-client/src/ambito_financiero_client/aio.py:69-74` + D-11):

```python
async def aclose() -> None:
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.aclose()
            _client = None
```

Patrón del driver Phase 2:

```python
async def _async_main(today: dt.date, results: list[ProbeResult]) -> None:
    try:
        results.append(await probe_happy_async(today))
        # ... otros probes async si los hubiera ...
    finally:
        await aio.aclose()  # Pitfall 5: nunca olvidar; try/finally garantiza cierre

def main() -> None:
    today = dt.date.today()
    write_findings(_PKG)  # idempotente
    results: list[ProbeResult] = []
    results.append(probe_happy_sync(today))
    asyncio.run(_async_main(today, results))  # único loop, D-11
    # ... probes 3-7 ...
```

**Anti-bot configure try/finally pattern** (D-15 + `client.py:47-54`):

```python
def configure(*, base_url: str | None = None, user_agent: str | None = None) -> None:
    """Sobrescribe la URL base o el User-Agent en runtime."""
    global _base_url, _user_agent, _client
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if user_agent is not None:
        _user_agent = user_agent
        _client.headers["User-Agent"] = user_agent
```

Patrón del probe (RESEARCH Pattern 3):

```python
def probe_antibot(today: dt.date) -> ProbeResult:
    if os.getenv("VERIFY_ANTIBOT") != "1":
        return ProbeResult("antibot", "SKIPPED", "(opt-in via VERIFY_ANTIBOT=1)")
    bad_ua = f"python-httpx/{httpx.__version__}"
    good_ua = ambito.client._DEFAULT_USER_AGENT  # leer del módulo, NO duplicar
    try:
        ambito.configure(user_agent=bad_ua)
        # ... una sola llamada, sin retry/sleep (D-14) ...
    finally:
        ambito.configure(user_agent=good_ua)  # restaurar SIEMPRE (Pitfall 8)
```

**Opt-in gate pattern** (precedente: `verification/mutation_gate.py:44-46`):

```python
def mutating_allowed() -> bool:
    """Solo permite mutaciones con flag opt-in Y base URL remarkets (D-16)."""
    if os.getenv("VERIFY_MUTATING") != "1":
        print("SKIPPED (mutating, guard off)")
        return False
```

Phase 2 usa el mismo patrón con `VERIFY_ANTIBOT=1` (D-12) pero **no imprime SKIPPED directo**: devuelve un `ProbeResult("antibot", "SKIPPED", "(opt-in via VERIFY_ANTIBOT=1)")` que entra al summary. Formato verbatim heredado de Phase 1 pero adaptado al contexto del probe.

**Schema-snapshot envelope pattern** (RESEARCH Pattern 4 + D-21):

```python
_PKG = "ambito-financiero-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG
_SCHEMA_FILE = _SCHEMA_DIR / "get-dollar-banco-nacion.json"

# Patrón análogo a verification/capture.py:42-51 — mkdir + write_text + json.dumps
def probe_schema_snapshot(today: dt.date, rows: list[list[str]] | None = None) -> ProbeResult:
    fecha = _last_business_day(today)
    if rows is None:
        resp = ambito.client._request(
            "GET",
            f"/dolarnacion/historico-general/{fecha:%Y-%m-%d}/{fecha:%Y-%m-%d}",
        )
        rows = resp.json()
    actual_schema = schema_of(rows)
    envelope = {
        "endpoint": "/dolarnacion/historico-general/{from}/{to}",
        "client_function": "get_dollar_banco_nacion",
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "base_url": ambito.client._base_url,
        "sample_date": fecha.isoformat(),
        "schema": actual_schema,
    }
    _SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    if not _SCHEMA_FILE.exists():
        _SCHEMA_FILE.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return ProbeResult("schema_snapshot", "PASS", f"escrito {_SCHEMA_FILE.name}")
    committed = json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))
    if committed["schema"] == actual_schema:
        return ProbeResult("schema_snapshot", "PASS", "schema sin drift")
    # D-25: NO sobreescribir cuando difiere
    append_finding(
        _PKG,
        fid="F-XX",
        class_="SHAPE",
        surface="both",
        status="OPEN",
        title="Schema drift en get_dollar_banco_nacion",
        expected=json.dumps(committed["schema"]),
        actual=json.dumps(actual_schema),
        diff="ver expected vs actual",
        base_url=ambito.client._base_url,
    )
    return ProbeResult("schema_snapshot", "FINDING", "F-XX (OPEN) — NO sobreescribe")
```

**JSON dump convention precedent** (`verification/capture.py:50`): `json.dumps(payload, indent=2, ensure_ascii=False)` + `path.write_text(..., encoding="utf-8")`. Phase 2 agrega `+ "\n"` final para que el archivo termine con newline (convención de archivos UNIX).

**Trailing newline pattern** ya está en uso en todos los archivos Python del repo (auto-aplicado por ruff format). Para el JSON committeable, se agrega explícito.

---

### 4. `packages/ambito-financiero-client/tests/test_client.py` — APPEND

**Analog:** mismo archivo, líneas 1-53. Misma convención de naming, fixture autouse, `httpx_mock.add_response(url=...)`.

**Convención obligatoria:** `from __future__ import annotations` (l.3); mypy strict; pytest-httpx con `url=` completa (TESTING.md); fecha fija en mocks (Pitfall 4); section dividers en comentarios.

**Imports pattern existente** (`test_client.py:1-15`):

```python
"""Smoke tests del cliente sincrónico de Ámbito Financiero (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import ambito_financiero_client as ambito
from ambito_financiero_client import (
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
    AmbitoFinancieroRateLimitError,
)
```

**Cambio Phase 2:** agregar `from ambito_financiero_client._parsing import parse_ar_decimal` (necesario para el test invariante AMB-02). NO re-exportar `parse_ar_decimal` desde el barrel del paquete (`__init__.py:27-35`) — sigue siendo internal helper.

**Test pattern existente** (`test_client.py:30-35` — analog DIRECTO para el nuevo test AMB-03):

```python
def test_get_dollar_banco_nacion_devuelve_venta(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1365,00", "1415,00"]],
    )
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 7)) == 1415.0
```

**Sección nueva — `# ------ Verified live (Phase 2) ------`** (D-09):

```python
# ------ Verified live (Phase 2) ------


def test_get_dollar_banco_nacion_emite_url_dia_gt_12(httpx_mock: HTTPXMock) -> None:
    """Phase 2: locking de URL emitida con día > 12 (AMB-03).

    Verificado en vivo el <fecha>: el formato es DD/MM (`21/04/2026`), no MM/DD.
    Día > 12 elimina la ambigüedad estructuralmente.
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0


def test_parse_ar_decimal_formato_real() -> None:
    """Phase 2: locking de parse_ar_decimal('1.415,00') == 1415.0 (AMB-02)."""
    from ambito_financiero_client._parsing import parse_ar_decimal
    assert parse_ar_decimal("1.415,00") == 1415.0


def test_get_dollar_banco_nacion_shape_list_of_list_str(httpx_mock: HTTPXMock) -> None:
    """Phase 2: locking de shape list[list[str]] y header row 0 (AMB-01/AMB-03).

    Verificado en vivo: row 0 == ["Fecha","Compra","Venta"], row 1+ datos.
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    # Validar que llega al parse y no rompe (proxy de shape correcto)
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0
```

**Sección nueva — `# ------ Regressions ------`** (D-09): vacío hasta Wave 4 (cuando un finding promovido a CONFIRMED se cierre como FIXED).

**Regression test pattern** (D-07: `Regression: ... (finding F-NN)`; precedente: `.planning/codebase/TESTING.md` convención original con `(issue #NNN)`):

```python
# ------ Regressions ------


def test_parse_ar_decimal_dot_decimal_no_corrompe(httpx_mock: HTTPXMock) -> None:
    """Regression: parse_ar_decimal rompe ante dot-decimal '1415.00' (finding F-02).

    El server emitió `"1415.00"` en lugar de `"1.415,00"` y parse_ar_decimal
    devolvió 141500.0 (×100 corruption). Fix: detectar coma; si falta, levantar.
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1365.00", "1415.00"]],
    )
    with pytest.raises(SomeExceptionDefinedInFix):
        ambito.get_dollar_banco_nacion(dt.date(2026, 4, 21))
```

**Autouse fixture pattern reusable sin cambio** (`packages/ambito-financiero-client/tests/conftest.py:15-19`):

```python
@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    ambito.configure(base_url=_DEFAULT_BASE_URL)
    yield
    ambito.configure(base_url=_DEFAULT_BASE_URL)
```

Los tests nuevos heredan el reset automático del `_base_url` antes/después del test → cualquier `configure(user_agent=BAD_UA)` accidental en un test queda limpio (defensa-en-profundidad para tests futuros si se agregaran).

**Pitfall 4 (RESEARCH):** tests mockeados deben derivar de payloads observados en vivo. Para AMB-02, el mock debe emitir `"1.415,00"` (string AR-decimal), no `"1.415"` ni `"1.41500"`. Para AMB-03, header exacto `["Fecha", "Compra", "Venta"]`.

**Pitfall — Anti-pattern (RESEARCH):** "Usar `today + 60d` como fecha por defecto en el test mockeado de no_data". Los tests mockeados usan fechas fijas (`dt.date(2026, 4, 4)` como ya hace `test_get_dollar_banco_nacion_sin_datos_levanta`). La fecha futura derivada de `today` es **solo para el driver vivo** (D-24).

---

### 5. `packages/ambito-financiero-client/tests/test_async_client.py` — APPEND (espejo async)

**Analog:** mismo archivo, líneas 1-37; convención análoga a sync pero con `async def test_...` sin decorador (por `asyncio_mode = "auto"`).

**Imports pattern existente** (`test_async_client.py:1-14`):

```python
"""Smoke tests del cliente asincrónico de Ámbito Financiero (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from ambito_financiero_client import (
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
    aio,
)
```

**Cambio Phase 2:** igual que sync, agregar `from ambito_financiero_client._parsing import parse_ar_decimal` (en el archivo async, el test de `parse_ar_decimal` puede o NO duplicarse — D-09 manda "una sola convención" pero la función es sync; recomendación: duplicar literalmente para mantener la simetría exacta sync↔async de Verified live).

**Async test pattern existente** (`test_async_client.py:23-28` — analog DIRECTO):

```python
async def test_async_get_dollar_banco_nacion_devuelve_venta(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-07/2026-04-07",
        json=[["Fecha", "Compra", "Venta"], ["07/04/2026", "1365,00", "1415,00"]],
    )
    assert await aio.get_dollar_banco_nacion(dt.date(2026, 4, 7)) == 1415.0
```

**Sección nueva — `# ------ Verified live (Phase 2) ------`** (espejo del sync, prefijo `async_` en los names):

```python
# ------ Verified live (Phase 2) ------


async def test_async_get_dollar_banco_nacion_emite_url_dia_gt_12(
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 2: locking de URL emitida con día > 12 (AMB-03, async)."""
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    assert await aio.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0
```

**Async autouse fixture pattern reusable sin cambio** (`packages/ambito-financiero-client/tests/conftest.py:22-27`):

```python
@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    aio.configure(base_url=_DEFAULT_BASE_URL)
    yield
    await aio.aclose()
    aio.configure(base_url=_DEFAULT_BASE_URL)
```

El `await aio.aclose()` en el teardown garantiza que cada test async limpia su cliente (Pitfall 5: nunca dejar sockets abiertos).

**Sección nueva — `# ------ Regressions ------`** (D-06: por cada bug FIXED en sync, mirror en async):

```python
# ------ Regressions ------


async def test_async_parse_ar_decimal_dot_decimal_no_corrompe(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: parse_ar_decimal rompe ante dot-decimal '1415.00' (finding F-02).

    Mirror async del bug observado en `client.py`; el fix se duplica en `aio.py`.
    """
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1365.00", "1415.00"]],
    )
    with pytest.raises(SomeExceptionDefinedInFix):
        await aio.get_dollar_banco_nacion(dt.date(2026, 4, 21))
```

---

### 6. `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` — GENERATED (DRIFT-01)

**Analog:** patrón de escritura JSON de `verification/capture.py:42-51` (escribe JSON a una ruta predecible bajo `.planning/verification/`).

**Diferencias clave vs capture:**

| | `capture.py` (Phase 1) | Phase 2 schema snapshot |
|---|---|---|
| Ubicación | `.planning/verification/captures/` (gitignored) | `.planning/verification/schemas/<pkg>/` (committeable) |
| Filename | `<pkg>-<endpoint>.json` | `<slug>.json` (slug = nombre de función kebab-case) |
| Contenido | raw payload (puede tener PII) | envelope D-21 (metadata + `schema_of`, PII-free) |
| Sobreescritura | siempre escribe | NO sobreescribe si ya existe y difiere (D-25) |

**Escritura desde el driver** (RESEARCH Pattern 4):

```python
envelope = {
    "endpoint": "/dolarnacion/historico-general/{from}/{to}",
    "client_function": "get_dollar_banco_nacion",
    "captured_at": dt.datetime.now(dt.UTC).isoformat(),
    "base_url": ambito.client._base_url,
    "sample_date": fecha.isoformat(),
    "schema": schema_of(rows),  # list[list[str]] -> [["str"]]
}
_SCHEMA_FILE.write_text(
    json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
```

**Drift-detection pattern (D-25)** — sin precedente directo en el harness; nuevo en Phase 2:

```python
if not _SCHEMA_FILE.exists():
    _SCHEMA_FILE.write_text(...)  # primer run: escribe
    return ProbeResult("schema_snapshot", "PASS", ...)
committed = json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))
if committed["schema"] == actual_schema:
    return ProbeResult(...)  # sin drift: PASS
# Drift: NO sobreescribe; emite finding
append_finding(...)
return ProbeResult("schema_snapshot", "FINDING", ...)
```

**Esperado contenido** (Phase 2, primer commit):

```json
{
  "endpoint": "/dolarnacion/historico-general/{from}/{to}",
  "client_function": "get_dollar_banco_nacion",
  "captured_at": "2026-05-31T...+00:00",
  "base_url": "https://mercados.ambito.com",
  "sample_date": "2026-05-...",
  "schema": [
    [
      "str"
    ]
  ]
}
```

**Key ordering** (RESEARCH Open Question 2): preservar orden insertion (D-21) — Python 3.7+ dict respeta orden; `json.dumps(envelope, indent=2)` SIN `sort_keys`. El campo `schema` ya viene ordenado por `schema_of` (`verification/schema.py:36`).

---

### 7. `.planning/verification/ambito-financiero-client-findings.md` — GENERATED (esqueleto + appends)

**Analog primario:** `verification/findings.py::write_findings` (l.70-80) + `new_findings` (l.49-67).
**Analog secundario:** plantilla `.planning/verification/FINDINGS-TEMPLATE.md` (estructura completa documentada).

**Generación inicial** desde el driver (D-03):

```python
write_findings(_PKG)  # idempotente — no-op si el archivo ya existe
```

**Estructura inicial generada** (`verification/findings.py:49-67`):

```markdown
# Findings: ambito-financiero-client-client

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

**Nota importante** (`verification/findings.py:54`): el helper actual emite `# Findings: {pkg}-client` literal, con `-client` sufijo. Para `_PKG = "ambito-financiero-client"`, el header queda `# Findings: ambito-financiero-client-client` (con doble `-client`). El planner debe decidir si modificar `new_findings` para evitar el doble sufijo o usar `_PKG = "ambito-financiero"` en el driver. **Recomendación:** mantener `_PKG = "ambito-financiero-client"` y aceptar el doble sufijo (consistencia: `write_findings("higyrus")` produce `# Findings: higyrus-client`, así que el slug ya incluye el `-client`).

**Estructura final del archivo durante el run** — append_finding agrega filas al `## Index` table y secciones `### F-NN -- <título>` después (formato copiado de `.planning/verification/FINDINGS-TEMPLATE.md:67-85`):

```markdown
### F-01 -- <titulo>

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

> Estado: uno de OPEN -> CONFIRMED -> FIXED, o terminal EXPECTED / NO-FIX.

- **Expected:** <lo que el cliente asume (forma, tipo, codigo, parametro)>
- **Actual:** <lo que devolvio la API en vivo>
- **Diff:** <campos/tipos/codigos divergentes -- el delta concreto>
- **Regression:** `<test path>` . `Regression: ... (issue #NNN)`
```

**Cambio Phase 2 / D-07:** sustituir `issue #NNN` por `finding F-NN` en la sección Regression (el findings file es la fuente de verdad).

---

### 8. `packages/ambito-financiero-client/tests/test_findings_helper.py` (OPCIONAL pero recomendado en RESEARCH Wave 1)

**Analog primario:** `packages/ambito-financiero-client/tests/test_harness_schema.py` (precedente Phase 1: tests del harness viven bajo el paquete que primero los usa).
**Analog secundario:** `packages/ambito-financiero-client/tests/test_harness_anonymize.py` (estructura de tests con `from verification.X import Y`).

**Imports + módulo docstring pattern** (`test_harness_schema.py:1-19`):

```python
"""Tests del harness de verificación: schema_of (D-12) y capture (HARN-06/D-11).

Estos tests prueban estructuralmente la propiedad PII-safe del pipeline:

- ``schema_of`` reduce cualquier payload a claves + nombres de tipo, nunca valores.
- ``capture`` escribe el payload crudo SÓLO bajo el staging gitignored
  ``.planning/verification/captures/`` (la ruta cruda nunca es committeable).

Viven bajo ``packages/<pkg>/tests/`` porque ``testpaths=["packages"]`` no colecta
``verification/``; el módulo ``verification`` se resuelve porque la raíz del repo
está en ``sys.path`` (Patrón 1 de la investigación).
"""

from __future__ import annotations

from pathlib import Path

from verification.capture import capture
from verification.schema import schema_of
```

**Test pattern reusable** (`test_harness_schema.py:22-29`):

```python
def test_schema_of_dict_returns_keys_and_type_names_sorted() -> None:
    """Test 1: un dict se reduce a {clave: nombre-de-tipo}, ordenado, sin valores."""
    result = schema_of({"b": "1.415,00", "a": 5})
    assert result == {"a": "int", "b": "str"}
```

**Pattern de uso de `tmp_path` para tests con I/O** (`test_harness_schema.py:47-66`):

```python
def test_capture_writes_under_gitignored_staging_dir(tmp_path: Path) -> None:
    """Test 4: capture escribe bajo .planning/verification/captures/ (gitignored)."""
    payload = {"sample": "value", "n": 1}
    path = capture("ambito", "dollar", payload)
    try:
        # ... asserts ...
        assert path.exists()
    finally:
        # No dejar el probe en disco (de todas formas está gitignored).
        if path.exists():
            path.unlink()
```

**Cambio Phase 2:** `append_finding` escribe a `.planning/verification/<pkg>-findings.md` que NO es gitignored. Los tests deben usar un `pkg` único de test (p.ej. `pkg="test-pkg-{unique}"`) y limpiar el archivo en `finally`. O alternativamente, usar `monkeypatch` para redirigir `_FINDINGS_DIR` a `tmp_path` — patrón más limpio, recomendado para preservar el invariante de que el helper escribe siempre al path canónico.

**Tests sugeridos** (cubre D-10 invariantes críticos):

```python
def test_append_finding_creates_skeleton_if_missing(tmp_path: Path, monkeypatch) -> None:
    """append_finding crea el esqueleto si el archivo no existe."""
    ...

def test_append_finding_is_idempotent_by_fid(tmp_path: Path, monkeypatch) -> None:
    """Dos calls con el mismo fid OPEN: el segundo sobreescribe campos (no duplica)."""
    ...

def test_append_finding_preserves_human_promoted_status(tmp_path: Path, monkeypatch) -> None:
    """Pitfall 1: status CONFIRMED/FIXED/EXPECTED/NO-FIX nunca se pisa con OPEN."""
    ...

def test_append_finding_refreshes_art_block(tmp_path: Path, monkeypatch) -> None:
    """ART Timestamp/base_url se refresca en cada call (D-03)."""
    ...

def test_append_finding_rejects_invalid_class(tmp_path: Path, monkeypatch) -> None:
    """class_ debe estar en FINDING_CLASSES; ValueError si no."""
    ...

def test_append_finding_rejects_invalid_status(tmp_path: Path, monkeypatch) -> None:
    """status debe estar en STATUS_LIFECYCLE; ValueError si no."""
    ...
```

---

## Shared Patterns

### Convención obligatoria cross-archivos (CONVENTIONS.md / CLAUDE.md)

**Aplica a:** todo módulo nuevo (`verification/findings.py` extensión, `main_ambito_financiero.py` rewrite, tests nuevos, opcional `test_findings_helper.py`).

```python
from __future__ import annotations    # primera línea de todo módulo nuevo (mandatory)
```

- **Ruff:** `line-length = 100`, double quotes, 4 espacios.
- **Mypy strict:** `disallow_untyped_defs = true`, `warn_return_any = true`. Toda función nueva con firma completa incluyendo retorno.
- **Naming:** `snake_case` para funciones/variables, `_snake_case` para internals/module-state.
- **Imports:** no wildcard (`from x import *` prohibido); no relative (`from .foo import bar` prohibido — usar `from verification.foo import bar` o `from ambito_financiero_client.foo import bar`).

### Pattern: import del barrel `verification`

**Source:** `main_higyrus.py:17` + `main_iol.py:15`
**Apply to:** `main_ambito_financiero.py` (rewrite)

```python
from verification import require_env, safe_print
```

Phase 2 agrega `from verification import safe_print, schema_of, write_findings` (Ámbito no usa `require_env`) + `from verification.findings import append_finding` (re-exportado via barrel pero también accesible directo).

### Pattern: `safe_print` con `secrets=[]` por uniformidad cross-paquetes (D-26)

**Source:** `verification/redaction.py:43-61`
**Apply to:** todos los prints del driver `main_ambito_financiero.py`

```python
def safe_print(text: str, secrets: list[str]) -> None:
    masked = text
    for secret in secrets:
        if secret and len(secret) >= 4:
            masked = masked.replace(secret, _REDACTED)
    masked = _BEARER.sub(rf"\1{_REDACTED}", masked)
    print(masked)
```

Ámbito sin credenciales → `safe_print(text, secrets=[])`. El loop sobre `secrets` es no-op pero el `_BEARER` regex sigue funcionando como segunda capa de defensa. Patrón uniforme para Phases 3-5 donde `secrets` se llena con `(IOL_PASSWORD, IOL_USER, ...)`.

### Pattern: acceso a estado `_module-private` del cliente (precedente harness)

**Source:** `verification/mutation_gate.py:55`
**Apply to:** driver `main_ambito_financiero.py` (lectura de `ambito.client._base_url` y `ambito.client._DEFAULT_USER_AGENT`)

```python
base = matriz_client.client._base_url  # estado resuelto en vivo; sólo lectura
```

Python no enforce `_` prefix; el harness ya usa este patrón. **Solo lectura para chequeos**, nunca print directo del valor (D-26 + Pitfall 1 de mutation_gate.py).

### Pattern: `pytest-httpx` con URL completa (TESTING.md)

**Source:** `test_client.py:30-34` + `test_async_client.py:24-27`
**Apply to:** todos los tests Verified live + Regressions

```python
httpx_mock.add_response(
    url="https://mercados.ambito.com/dolarnacion/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>",
    json=[["Fecha", "Compra", "Venta"], ["DD/MM/YYYY", "...", "..."]],
)
```

URL completa con query string (Ámbito no tiene query); valida routing implícitamente.

### Pattern: regression docstring (TESTING.md adaptado por D-07)

**Source:** `.planning/codebase/TESTING.md` convención `Regression: ... (issue #NNN)`
**Apply to:** todos los tests de la sección `# ------ Regressions ------`

```python
def test_<bug-described>(httpx_mock: HTTPXMock) -> None:
    """Regression: <descripción del bug en vivo> (finding F-NN).

    <contexto adicional opcional>.
    """
```

D-07 sustituye `(issue #NNN)` por `(finding F-NN)` — el findings file es la fuente de verdad.

### Pattern: async test sin decorador (TESTING.md)

**Source:** `test_async_client.py:17-20` + `pyproject.toml [tool.pytest.ini_options].asyncio_mode = "auto"`
**Apply to:** todos los tests async nuevos en `test_async_client.py`

```python
async def test_async_<name>(httpx_mock: HTTPXMock) -> None:
    """..."""
    ...
    await aio.get_dollar_banco_nacion(...)
```

No `@pytest.mark.asyncio` — `asyncio_mode = "auto"` lo aplica automáticamente.

### Pattern: dataclass para estructuras inmutables del driver

**Source:** `verification/anonymize.py:34-46` (`Denylist`)
**Apply to:** `ProbeResult` en `main_ambito_financiero.py`

```python
@dataclass(frozen=True, slots=True)
class Denylist:
    """..."""
    pkg: str
    keys: frozenset[str]
    replacements: dict[str, str] = field(default_factory=dict)
```

Convención del harness: dataclass `frozen=True, slots=True`. Phase 2 lo aplica para `ProbeResult` y opcionalmente para `_Finding` interno en `findings.py`.

### Pattern: `mkdir(parents=True, exist_ok=True)` + `write_text(...)` (file-I/O idempotente)

**Source:** `verification/capture.py:48-51` + `verification/findings.py:75-79`
**Apply to:** `main_ambito_financiero.py::probe_schema_snapshot` (escritura del JSON envelope)

```python
_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
path = _CAPTURES_DIR / f"{pkg}-{endpoint}.json"
path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
```

Phase 2: encoding=`utf-8` siempre; `ensure_ascii=False` para no escapar accentos; `indent=2` para diff-friendly; agregar `+ "\n"` al final para archivos JSON committeables.

---

## No Analog Found

| File | Role | Razón |
|---|---|---|
| `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` (formato envelope D-21) | committeable JSON con metadata + schema | El precedente `verification/capture.py` escribe a gitignored y sin envelope. El formato D-21 (endpoint + client_function + captured_at + base_url + sample_date + schema) es nuevo en Phase 2; el planner DEBE usar el envelope literal de RESEARCH Pattern 4 / D-21. No hay analog committeable previo en el repo. |
| Drift detection en re-runs (D-25 — comparar `schema_of` actual vs committed, NO sobreescribir, emitir finding `SHAPE` OPEN) | comparación + finding emission | Sin precedente directo en el harness. Phase 2 establece el patrón usando solo primitivos existentes (`schema_of`, `append_finding`, comparación de dict por igualdad). |
| Drift detection en `append_finding` (preservar status humano CONFIRMED/FIXED/EXPECTED/NO-FIX en re-runs) | parser + mutation idempotente | Sin precedente. RESEARCH Pattern 1 propone "modelo interno + re-serializar el archivo completo" — Phase 2 lo construye desde cero. Para la convención de testing, los analogs son `test_harness_schema.py` + `test_harness_anonymize.py`. |

---

## Metadata

**Analog search scope:**
- `verification/` (raíz del repo, módulo no publicable)
- `packages/ambito-financiero-client/` (target)
- `main_*.py` (raíz, drivers)
- `.planning/verification/FINDINGS-TEMPLATE.md` (plantilla documentada)
- `.planning/codebase/{TESTING,CONVENTIONS}.md` (convenciones generales)
- `.planning/phases/01-*/01-04-SUMMARY.md` (qué dejó Phase 1)

**Files scanned (lectura directa):** 17

| Archivo | Propósito |
|---|---|
| `.planning/phases/02-mbito-verification/02-CONTEXT.md` | Decisiones D-01..D-26 + canonical refs + code context |
| `.planning/phases/02-mbito-verification/02-RESEARCH.md` | 4 Patrones técnicos + Pitfalls + Validation Architecture + Open Questions |
| `.planning/phases/01-safety-harness-verification-infrastructure/01-CONTEXT.md` | Precedentes LOCK Phase 1 (parcial — primeras 100 líneas) |
| `.planning/phases/01-safety-harness-verification-infrastructure/01-04-SUMMARY.md` | Outputs de `verification/{schema,capture,anonymize,findings}.py` |
| `verification/findings.py` | Helper a extender — patrón mock para `append_finding` |
| `verification/__init__.py` | Barrel a actualizar |
| `verification/schema.py` | `schema_of` — primitivo DRIFT-01 |
| `verification/redaction.py` | `safe_print` con `secrets=[]` |
| `verification/mutation_gate.py` | Patrón de acceso a `_base_url` privado del cliente |
| `verification/capture.py` | Patrón mkdir + write_text + json.dumps |
| `verification/anonymize.py` | Patrón @dataclass(frozen=True, slots=True) |
| `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` | Superficie sync target |
| `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` | Superficie async target |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py` | `parse_ar_decimal` (AMB-02 target) |
| `packages/ambito-financiero-client/src/ambito_financiero_client/exceptions.py` | `AmbitoFinancieroNoDataError` |
| `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py` | `__all__` del paquete |
| `packages/ambito-financiero-client/tests/test_client.py` | Tests sync existentes (append target) |
| `packages/ambito-financiero-client/tests/test_async_client.py` | Tests async existentes (append target) |
| `packages/ambito-financiero-client/tests/conftest.py` | Autouse fixtures `_configure_sync`/`_configure_async` |
| `packages/ambito-financiero-client/tests/test_harness_schema.py` | Precedente Phase 1: tests del harness viven bajo el paquete |
| `packages/ambito-financiero-client/tests/test_harness_anonymize.py` | Idem |
| `main_ambito_financiero.py` | Driver actual a reescribir; `_last_business_day` reusable |
| `main_verify.py` | Orchestrator con summary pattern |
| `main_higyrus.py` | Driver con `safe_print(secrets)` pattern |
| `main_iol.py` | Driver simple con `require_env` + `redact` |
| `.planning/verification/FINDINGS-TEMPLATE.md` | Formato de findings markdown |

**Pattern extraction date:** 2026-05-31
