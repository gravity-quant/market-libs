# Phase 2: Ámbito Verification - Research

**Researched:** 2026-05-31
**Domain:** verificación en vivo + driver-only loop + schema snapshot (`ambito-financiero-client`)
**Confidence:** HIGH (todo el material es codebase-local verificado por lectura directa)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Probes organizados como sub-funciones nombradas al tope de `main_ambito_financiero.py`: `probe_happy_sync`, `probe_happy_async`, `probe_parity_sync_async`, `probe_parse_decimal_adversarial`, `probe_no_data`, `probe_antibot`, `probe_schema_snapshot`. `main()` las invoca en orden.

**D-02:** Output a stdout = plain text, una línea por probe + summary final. Formato verbatim ej. `PROBE happy_sync: PASS`, `PROBE no_data: PASS`, `PROBE antibot: SKIPPED (opt-in via VERIFY_ANTIBOT=1)`, `PROBE parse_decimal: FINDING F-02 (OPEN)`. El summary final emite conteos por estado.

**D-03:** Driver auto-genera el findings file. Llama `write_findings("ambito-financiero-client")` al inicio (no-op si existe) y usa `append_finding(...)` (nuevo, D-10) para agregar cada hallazgo OPEN. El ART block del header se refresca con timestamp/base_url del run actual.

**D-04:** Driver continúa todos los probes; exit 0 siempre (salvo crash inesperado). Los hallazgos son el output esperado.

**D-05:** Driver-only para verificación viva. Los únicos tests bajo `packages/ambito-financiero-client/tests/` son mockeados: invariantes lockeados + regresiones de bugs FIXED.

**D-06:** Una regresión mockeada por superficie por bug FIXED: un test en `test_client.py` (sync) + uno en `test_async_client.py` (async), aun si el bug se observó solo en una superficie.

**D-07:** ID en `Regression: ...` = ID del finding (`Regression: parse_ar_decimal rompe ante dot-decimal '1415.00' (finding F-02).`). El findings file es la fuente de verdad — no hay dependencia de GitHub Issues.

**D-08:** Phase 2 agrega tests mockeados que codifican invariantes verificadas en vivo, aun si no se encuentra ningún bug. Mínimo:
- URL exacta emitida `/dolarnacion/historico-general/YYYY-MM-DD/YYYY-MM-DD` (un caso con día > 12, ej. `2026-04-21/2026-04-21`)
- Shape: `list[list[str]]`, row 0 = `["Fecha","Compra","Venta"]`, row 1+ datos
- `parse_ar_decimal("1.415,00") == 1415.0`
- `get_dollar_banco_nacion(date)` levanta `AmbitoFinancieroNoDataError` cuando `len(rows) < 2`

**D-09:** Tests nuevos viven en `test_client.py` y `test_async_client.py` existentes, con divisores: `# ------ Verified live (Phase 2) ------` para invariantes y `# ------ Regressions ------` para regresiones. Un archivo por superficie, una sola convención.

**D-10:** Phase 2 extiende `verification/findings.py` con `append_finding(...)`. Firma propuesta:

```python
def append_finding(
    pkg: str,
    *,
    fid: str,                  # "F-01", "F-02", ...
    class_: str,               # uno de FINDING_CLASSES
    surface: str,              # "sync" | "async" | "both"
    status: str,               # uno de STATUS_LIFECYCLE
    title: str,
    expected: str,
    actual: str,
    diff: str,
    regression: str | None = None,  # path al test si existe
) -> Path: ...
```

Idempotente por `fid` (no duplica). Si el archivo no existe, crea el esqueleto primero. Re-runs convergen sin pisar status humanos ya promovidos (CONFIRMED/FIXED/EXPECTED/NO-FIX).

**D-11:** Lifecycle async = un único `asyncio.run(_async_main())` al final. `_async_main` ejecuta probes async en serie y termina con `await aio.aclose()`. Un solo event loop, cliente compartido, cierre limpio.

**D-12:** Probe anti-bot opt-in via env var `VERIFY_ANTIBOT=1`. Sin la var → `PROBE antibot: SKIPPED (opt-in via VERIFY_ANTIBOT=1)` y sigue.

**D-13:** Probe anti-bot corre último.

**D-14:** Probe anti-bot = one-shot estructural, sin retry ni sleep. 403 → finding `EXPECTED` terminal clase `ANTI-BOT`. ≠ 403 → finding `OPEN` `ANTI-BOT` con la respuesta real observada.

**D-15:** Probe usa `configure(user_agent=BAD_UA)` antes de la llamada y `configure(user_agent=GOOD_UA)` dentro de `try/finally` para restaurar el estado del módulo aun si la llamada lanza.

**D-16:** UA inválida = default de httpx, `f"python-httpx/{httpx.__version__}"`. (Verificado en este host: `python-httpx/0.28.1` con `httpx==0.28.1`.)

**D-17:** Probe anti-bot solo sync. La defensa la implementa el servidor; no es dual del cliente.

**D-18:** Si la respuesta NO es 403 (200, 429, timeout, otro): `OPEN ANTI-BOT` con `actual` = detalle exacto de la respuesta real.

**D-19:** Ubicación schema snapshot: `.planning/verification/schemas/<pkg>/<slug>.json`. Para Phase 2: `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json`.

**D-20:** Slug = nombre de función del cliente (snake → kebab): `get-dollar-banco-nacion.json`.

**D-21:** Formato JSON con wrapper de metadata + schema (un solo archivo):

```json
{
  "endpoint": "/dolarnacion/historico-general/{from}/{to}",
  "client_function": "get_dollar_banco_nacion",
  "captured_at": "2026-05-29T...",
  "base_url": "https://mercados.ambito.com",
  "sample_date": "2026-05-21",
  "schema": [["str"]]
}
```

El campo `schema` es el output exacto de `verification.schema.schema_of(raw)` — PII-free por construcción.

**D-22:** Un solo archivo current por endpoint; git history es la historia. Cada re-corrida regenera el snapshot (sujeto a D-25).

**D-23:** AMB-02 doble check estructural + sanity de rango:
1. Estructural: string crudo `venta` debe contener `,` (separador decimal AR). Si no → finding `PARAM` OPEN.
2. Rango plausible: float resultante de `parse_ar_decimal(venta)` debe estar en `100 <= venta_parseada <= 100000`. Si fuera → finding `SHAPE`/`PARAM` OPEN. Bounds amplios sobre USD/ARS histórico y futuro razonable.

**D-24:** Fechas derivadas de `today` con helpers determinísticos, sin anchors hardcoded:
- happy / async / schema_snapshot: `_last_business_day(today)` (helper existente).
- parse_decimal_adversarial: reusar la misma fecha de happy.
- no_data: fecha futura conservadora (`today + 60d` como draft).
- AMB-03 sample con día > 12: helper nuevo `_last_business_day_with_day_gt_12(today)` que retrocede desde `_last_business_day(today)` hasta `date.day > 12`.

**D-25:** Si re-corrida del driver detecta drift (schema_of actual ≠ snapshot committeado):
1. Emite finding `SHAPE` OPEN con `expected` = schema committeado, `actual` = schema de este run.
2. NO sobreescribe el archivo. Deja el snapshot committeado intacto para revisión humana.

**D-26:** `safe_print(text, secrets=())` por uniformidad cross-paquetes. Ámbito no tiene credenciales; pasar todos los prints por `safe_print` mantiene el patrón.

### Claude's Discretion

- Nombres exactos de las sub-funciones probe más allá de las convenciones citadas en D-01 (p.ej., `probe_parse_decimal_adversarial` vs `probe_parse_ar_decimal`).
- Texto exacto de las líneas de status a stdout más allá de los verbatim heredados de Phase 1 (`SKIPPED <pkg>: missing X, Y`).
- Estructura interna de `append_finding` (parser tactic del markdown, dedup por `fid`, lugar exacto del insert en el índice y la sección detalle).
- Bounds finales del sanity de rango plausible en D-23 (100/100000 son draft).
- Convención de filename de snapshot cuando un endpoint sea compartido por dos funciones del cliente (Phase 2 tiene una sola función — no aplica acá).
- Schema exacto (keys, order, naming) del JSON envelope de D-21.
- Fecha futura para `probe_no_data` (D-24 sugiere `today + 60d`).
- Mecánica del `--accept-drift` o equivalente en D-25 (env var, flag, edición manual del archivo).
- Si `append_finding` modifica o no el ART block del header en cada call (vs un helper separado `refresh_art_block`).

### Deferred Ideas (OUT OF SCOPE)

- **Anonymize() para el payload de Ámbito** — las cotizaciones FX son información pública (sin PII); el pipeline `capture → anonymize → fixture` se ejercita en pleno en Phases 3-5. En Phase 2 `verification.capture.capture` puede usarse opcionalmente para staging, pero `anonymize` no es necesario.
- **`@pytest.mark.live` tests para Ámbito** — disponibles para uso futuro pero esta fase elige driver-only (D-05).
- **DRIFT-02 (informe final + cierre de fixes per-package)** — anclado a Phase 5.
- **Mecánica de `--accept-drift`** en D-25 — Phase 2 implementa el flujo "detectar + no sobreescribir + emitir finding"; el comando para aceptar el drift queda a discreción.
- **Refactor a clase `Client` por instancia / deduplicación sync-async** — fuera de scope para todo el ciclo.
- **Disparar 403/429/5xx en vivo con loops** — anti-feature documentada; el probe anti-bot es one-shot por D-14.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AMB-01 | Verificar llamada real exitosa con UA actual, sync y async | `probe_happy_sync` + `probe_happy_async` (D-01); estado 200 + payload `list[list[str]]`; PASS si llega float; el caso live se ancla con tests mockeados de invariante (D-08) en `test_client.py` / `test_async_client.py` |
| AMB-02 | Verificar `parse_ar_decimal` contra formato real `"1.415,00"` (detectar cambio del server a `1415.00`) | `probe_parse_decimal_adversarial` con doble check (D-23): estructural (presencia de `,`) + rango (`100 <= x <= 100000`). Test mockeado de invariante: `parse_ar_decimal("1.415,00") == 1415.0` |
| AMB-03 | Verificar formato de fecha en URL y forma `list[list[str]]` de la respuesta | `probe_happy_sync` valida shape; URL se ancla con test mockeado usando `_last_business_day_with_day_gt_12(today)` (D-24) — caso con día > 12 que descarta MM/DD vs DD/MM ambigüedad |
| AMB-04 | Verificar que `NoDataError` se dispara para fecha sin cotización | `probe_no_data` con `today + 60d` (D-24); contrato: client levanta `AmbitoFinancieroNoDataError` cuando `len(rows) < 2`. Test mockeado existente ya lo cubre + se agrega en sección `Verified live` |
| AMB-05 | Verificar paridad sync↔async | `probe_parity_sync_async`: llama ambas superficies a la misma fecha, compara estructuralmente (tipo, claves, float parseado) |
| AMB-06 | Probe anti-bot (UA correcto pasa; UA inválido reproduce 403, sin loops) | `probe_antibot` opt-in via `VERIFY_ANTIBOT=1` (D-12); one-shot (D-14); `BAD_UA = f"python-httpx/{httpx.__version__}"` (D-16); try/finally restaura `GOOD_UA` (D-15); solo sync (D-17); clasifica 403 → EXPECTED, ≠403 → OPEN (D-18) |
| DRIFT-01 | Commitear snapshot estructural por endpoint verificado | `probe_schema_snapshot`: `schema_of(rows)` → JSON envelope D-21 en `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json`. Drift detection D-25: no sobreescribe si difiere, emite finding SHAPE OPEN |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Directives extraídas del `./CLAUDE.md` que el planner DEBE respetar:

- **Tech stack:** Python 3.12+, uv, httpx (sync+async), pytest + pytest-httpx, ruff, mypy strict. Toda extensión y fix DEBE respetar el stack y pasar el CI existente.
- **Arquitectura:** estado singleton a nivel de módulo; sin código compartido entre paquetes (por diseño). Los fixes se aplican dentro de cada paquete, sin introducir dependencias cruzadas.
- **Dual sync/async:** cualquier fix de lógica DEBE espejarse en `client.py` y `aio.py` del mismo paquete (deuda conocida: lógica duplicada).
- **Seguridad:** las credenciales viven en `.env` por paquete; nunca commitear `.env` ni exponer credenciales en logs, reportes o tests. (Ámbito no tiene credenciales; aun así D-26 manda usar `safe_print(text, secrets=())` uniformemente.)
- **Dependencias externas en vivo:** la verificación depende de la disponibilidad y el estado real de servicios de terceros; resultados pueden variar por horario de mercado, datos disponibles o rate limits.
- **GSD Workflow Enforcement:** antes de Edit/Write, el trabajo se canaliza por un comando GSD; esta fase ya está dentro de `/gsd-plan-phase`.
- **Ruff:** `line-length = 100`, double quotes, 4 espacios. `from __future__ import annotations` al tope de cada módulo nuevo. No relative imports. No wildcard imports.
- **Mypy strict:** firmas completas en `append_finding`, en cada probe, en JSON dumps. `disallow_untyped_defs = true`.
- **Sección `Regression: ... (issue #NNN)`** en docstring de cada test de regresión; **D-07 sustituye `(issue #NNN)` por `(finding F-NN)`** porque el findings file es la fuente de verdad.

## Summary

Phase 2 ejecuta el **primer ciclo end-to-end** del harness ya construido en Phase 1 (`verification/{findings,schema,capture,redaction,env_gate,mutation_gate,anonymize}.py`) sobre `ambito-financiero-client` — el target de menor riesgo (sin auth, una sola función pública, payload público). El trabajo se concentra en **tres slices verticales**: (1) extender `verification/findings.py` con `append_finding(...)` re-exportado por el barrel; (2) re-escribir `main_ambito_financiero.py` con 7 probes nombrados que poblan el findings file y, para `probe_schema_snapshot`, escriben/comparan `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json`; (3) appender en `tests/test_client.py` + `tests/test_async_client.py` las secciones `# ------ Verified live (Phase 2) ------` (invariantes lockeados por D-08) y `# ------ Regressions ------` (un test por superficie por bug FIXED, con docstring `Regression: ... (finding F-NN)`).

Todo el material está disponible en el repo: la plantilla de findings ya está documentada (`FINDINGS-TEMPLATE.md`), el `schema_of` es el único primitivo necesario para DRIFT-01, el `safe_print` ya está wired, y la convención sync/async dual está consolidada en el cliente actual. **No hay incertidumbre técnica externa** — todas las decisiones técnicas son codebase-local y las decisiones de producto fueron lockeadas en CONTEXT.md.

**Primary recommendation:** Plan en 4 waves verticales — Wave 1: `append_finding` + tests del helper (DRY para Phases 3-5). Wave 2 (paralelo a 1 si no comparten archivos): probes del driver (`main_ambito_financiero.py` reescrito). Wave 3 (depende de 1 + 2): correr el driver una vez, commitear el snapshot inicial + tests de invariante (D-08). Wave 4: para cada finding que escale a CONFIRMED → fix dual sync/async + 2 tests de regresión.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Llamadas HTTP en vivo a `mercados.ambito.com` | driver (`main_ambito_financiero.py`) | — | Por D-05, la verificación viva es driver-only |
| Parsing del payload `list[list[str]]` y conversión a float | cliente sync (`client.py`) + cliente async (`aio.py`) | — | Lógica espejada (deuda conocida); fixes van en ambos |
| Clasificación de hallazgos en markdown | helper (`verification/findings.py::append_finding`) | barrel (`verification/__init__.py`) | DRY: el patrón debe servir para Phases 3-5 |
| Snapshot de schema estructural | helper (`verification/schema.py::schema_of`) + driver | repo (commit del JSON) | `schema_of` ya existe; el driver lo serializa + envelope D-21 |
| Tests mockeados de invariantes | tests del paquete (`tests/test_client.py`, `tests/test_async_client.py`) | pytest-httpx | Locking down de invariantes ejercitados en vivo |
| Tests mockeados de regresiones | tests del paquete | pytest-httpx + `Regression: ... (finding F-NN)` | Convención existente (TESTING.md) reusada con la variante D-07 |
| Redacción de credenciales | `verification.redaction.safe_print(text, secrets=())` | — | Patrón uniforme cross-paquetes (D-26) |
| Anti-bot probe | driver (sync only, D-17) | servidor de Ámbito | La defensa la implementa el servidor; el cliente solo cambia UA |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 [VERIFIED: `uv run python -c "import httpx; print(httpx.__version__)"`] | Sync + async HTTP del cliente | Ya stack del monorepo; el cliente lo usa |
| pytest | >=8.3 [VERIFIED: `pyproject.toml`] | Runner | Ya configurado |
| pytest-httpx | >=0.34 [VERIFIED: `pyproject.toml`] | Mock de HTTP en tests | Ya patrón establecido (`httpx_mock.add_response(url=...)`) |
| pytest-asyncio | >=0.24 [VERIFIED: `pyproject.toml`] | Soporte async | `asyncio_mode = "auto"` — tests async sin decorador |
| ruff | >=0.7 [VERIFIED: `pyproject.toml`] | Lint + format | line-length=100, double quotes |
| mypy | >=1.13 [VERIFIED: `pyproject.toml`] | Type check strict | `strict = true` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | >=1.0 [VERIFIED: cliente lo usa] | Carga `.env` por paquete | El cliente ya hace `load_dotenv()` en import; el driver puede asumirlo. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Markdown ad-hoc para findings | YAML/JSON estructurado | Rechazado: la plantilla `FINDINGS-TEMPLATE.md` ya está en markdown y es human-readable para revisión. |
| Snapshot en YAML | JSON | D-21 lockea JSON; diff-friendly, deterministic con `sort_keys` controlado. |
| `responses` o `vcrpy` | pytest-httpx | Ya stack establecido; reusar el patrón. |

**Installation:** Ningún paquete nuevo. Todas las deps ya están en `pyproject.toml` y `uv.lock`.

**Version verification:** Confirmado vía `uv run python -c "import httpx; print(httpx.__version__)"` → `0.28.1`. El BAD_UA esperado por D-16 = `python-httpx/0.28.1`.

## Package Legitimacy Audit

> No se instalan paquetes externos en esta fase. Toda la nueva funcionalidad usa solo dependencias ya bloqueadas en `uv.lock`. Tabla vacía intencionalmente.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| _(none)_ | — | — | — | — | — | — |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                            +------------------------+
   user shell  ----run----> | main_ambito_financiero |  (driver, manual run)
                            +-----------+------------+
                                        |
                  +---------------------+--------------------+
                  | Para cada probe (en orden D-01):                            |
                  | 1. probe_happy_sync         --HTTP--> mercados.ambito.com   |
                  | 2. probe_happy_async        --HTTP--> mercados.ambito.com   |
                  | 3. probe_parity_sync_async  --reuso datos previos--         |
                  | 4. probe_parse_decimal_adversarial (D-23)                   |
                  | 5. probe_no_data            --HTTP--> mercados.ambito.com   |
                  | 6. probe_schema_snapshot    --schema_of-->                  |
                  |    .planning/verification/schemas/.../get-dollar-...json    |
                  | 7. probe_antibot (gated)    --HTTP con BAD_UA-->            |
                  +---------------------+--------------------+
                                        |
                            +-----------v------------+
                            | verification.findings: |
                            | write_findings()       |  (no-op si existe)
                            | append_finding(...)    |  (idempotente por fid)
                            +-----------+------------+
                                        |
                            +-----------v------------+
                            | .planning/verification/|
                            | ambito-financiero-     |
                            | client-findings.md     |
                            +-----------+------------+
                                        |
            (cada FINDING que humano escala a CONFIRMED)
                                        |
                            +-----------v------------+
                            | Fix dual sync+async    |  (Wave 4)
                            | en client.py + aio.py  |
                            +-----------+------------+
                                        |
                            +-----------v------------+
                            | Regression tests:      |
                            | test_client.py +       |
                            | test_async_client.py   |
                            | docstring: Regression: |
                            | ... (finding F-NN)     |
                            +------------------------+


    (pytest sin --live, en CI o local) -----> solo tests mockeados:
                  invariantes (D-08) + regresiones (D-06)
```

### Recommended Project Structure

```
market-libs/
├── main_ambito_financiero.py             # (reescrito) 7 probes + summary
├── verification/
│   ├── findings.py                       # (extendido) +append_finding
│   ├── __init__.py                       # (extendido) +append_finding en __all__
│   └── ...                               # resto Phase 1 sin tocar
├── .planning/verification/
│   ├── FINDINGS-TEMPLATE.md              # (sin cambio)
│   ├── ambito-financiero-client-findings.md   # (autogenerado por driver, committeable)
│   └── schemas/
│       └── ambito-financiero-client/
│           └── get-dollar-banco-nacion.json   # (DRIFT-01, committeable)
└── packages/ambito-financiero-client/
    ├── src/ambito_financiero_client/
    │   ├── client.py                     # (target de fixes Wave 4)
    │   ├── aio.py                        # (target de fixes Wave 4, espejado)
    │   └── _parsing.py                   # (potencial target AMB-02)
    └── tests/
        ├── test_client.py                # (extendido: Verified live + Regressions)
        ├── test_async_client.py          # (extendido: ídem)
        └── test_findings_helper.py       # (NUEVO opcional) unit tests de append_finding
```

### Pattern 1: `append_finding` como serializer-completo (no parser)

**What:** En lugar de parsear el markdown existente con regex (frágil), la implementación recomendada mantiene un **modelo interno** de "lista de findings" leída a partir del markdown, lo muta (insert o skip por fid), y **re-serializa el archivo completo** desde el modelo.

**When to use:** Toda mutación de un archivo markdown estructurado donde la estructura es conocida y estable.

**Why:** Idempotencia por construcción (un fid pre-existente con status humano no se sobrescribe porque el modelo lo preserva). Re-serializar el archivo entero también permite refrescar el ART block (timestamp + base_url + market-hours) en cada llamada sin riesgo de duplicarlo.

**Source:** patrón derivado del propio `verification/findings.py::new_findings` que ya genera el esqueleto completo desde código.

**Bosquejo de implementación (pseudo-Python):**

```python
# verification/findings.py - extensión propuesta

@dataclass(frozen=True, slots=True)
class _Finding:
    fid: str
    class_: str
    surface: str
    status: str
    title: str
    expected: str
    actual: str
    diff: str
    regression: str | None

def _parse_findings(text: str) -> tuple[list[_Finding], dict[str, str]]:
    """Parsea el findings file existente. Devuelve (lista de findings, ART metadata).

    Tactic: lee el archivo línea por línea, captura ART block (líneas '- Timestamp:',
    '- Resolved base URL...', '- Market hours note:'), detecta el índice por header
    '## Index', y captura cada finding por header '### F-NN -- <título>'.
    """
    ...

def _serialize_findings(
    pkg: str,
    findings: list[_Finding],
    art: dict[str, str],
) -> str:
    """Render completo: header + ART block + tabla índice + sección por finding."""
    ...

def append_finding(
    pkg: str,
    *,
    fid: str,
    class_: str,
    surface: str,
    status: str,
    title: str,
    expected: str,
    actual: str,
    diff: str,
    regression: str | None = None,
    base_url: str | None = None,    # para refrescar ART en cada call
    market_hours: str | None = None,
) -> Path:
    """Agrega o actualiza un finding en el archivo del paquete.

    Idempotencia:
    - Si `fid` no existe -> agrega.
    - Si `fid` existe y su status es OPEN -> sobreescribe campos (el driver puede
      iterar y refinar mientras esté en OPEN).
    - Si `fid` existe y su status es CONFIRMED/FIXED/EXPECTED/NO-FIX -> NO-OP.
      (Status promovido por humano nunca lo pisa el driver.)

    Refresca el ART block con `base_url`, `market_hours` y el timestamp actual.
    """
    path = findings_path(pkg)
    if not path.exists():
        write_findings(pkg)
    text = path.read_text(encoding="utf-8")
    findings_list, art = _parse_findings(text)
    art["Timestamp"] = dt.datetime.now(dt.UTC).isoformat()
    if base_url is not None:
        art["Resolved base URL / env"] = base_url
    if market_hours is not None:
        art["Market hours note"] = market_hours
    # Idempotencia por fid:
    existing = {f.fid: f for f in findings_list}
    if fid in existing and existing[fid].status not in {"OPEN"}:
        # Status promovido por humano -> no tocar
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

### Pattern 2: Driver con sub-funciones nombradas + summary acumulado

**What:** Cada probe es una función top-level con firma uniforme y registra su resultado en un acumulador local que `main()` resume al final.

**Bosquejo:**

```python
# main_ambito_financiero.py (reescrito)

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
from verification.findings import append_finding  # nuevo, Wave 1

_PKG = "ambito-financiero-client"
_SCHEMA_DIR = Path(__file__).resolve().parent / ".planning" / "verification" / "schemas" / _PKG
_SCHEMA_FILE = _SCHEMA_DIR / "get-dollar-banco-nacion.json"
_GOOD_UA = ambito.client._DEFAULT_USER_AGENT  # leer del módulo, no duplicar
_BAD_UA = f"python-httpx/{httpx.__version__}"

# Bounds D-23 (draft, ajustables por Claude durante implementación)
_VENTA_MIN, _VENTA_MAX = 100.0, 100_000.0


@dataclass
class ProbeResult:
    name: str
    status: str        # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str        # texto que sigue al ':' en la línea
    # para el summary final


def _last_business_day(today: dt.date) -> dt.date:
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def _last_business_day_with_day_gt_12(today: dt.date) -> dt.date:
    d = _last_business_day(today)
    while d.day <= 12:
        d -= dt.timedelta(days=1)
        while d.weekday() >= 5:
            d -= dt.timedelta(days=1)
    return d


def probe_happy_sync(today: dt.date) -> ProbeResult:
    fecha = _last_business_day(today)
    try:
        # Para inspeccionar el payload crudo (no solo el float final), llamamos
        # al _request interno; el resultado del API público se valida también.
        resp = ambito.client._request("GET",
            f"/dolarnacion/historico-general/{fecha:%Y-%m-%d}/{fecha:%Y-%m-%d}")
        rows = resp.json()
        # Invariante AMB-03: list[list[str]] con header.
        assert isinstance(rows, list) and len(rows) >= 2
        assert rows[0] == ["Fecha", "Compra", "Venta"]
        # Cross-check vs API pública:
        precio = ambito.get_dollar_banco_nacion(fecha)
        return ProbeResult("happy_sync", "PASS", f"precio={precio}")
    except Exception as exc:
        append_finding(_PKG, fid="F-XX", class_="SHAPE", surface="sync",
                       status="OPEN", title="...",
                       expected="...", actual=str(exc), diff="...",
                       base_url=ambito.client._base_url)
        return ProbeResult("happy_sync", "FINDING", "F-XX (OPEN)")


async def _async_main(today: dt.date, results: list[ProbeResult]) -> None:
    results.append(await probe_happy_async(today))
    # probe_parity reusa el resultado sync y este async
    await aio.aclose()


def main() -> None:
    today = dt.date.today()
    write_findings(_PKG)              # idempotente (no sobreescribe)
    results: list[ProbeResult] = []
    results.append(probe_happy_sync(today))
    asyncio.run(_async_main(today, results))
    # probes 3, 4, 5, 6, 7...
    for r in results:
        safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=[])
    # summary
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    summary = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    safe_print(f"SUMMARY: {summary}", secrets=[])
```

### Pattern 3: Probe anti-bot con try/finally + lectura del default

**What:** `probe_antibot` lee `_DEFAULT_USER_AGENT` desde `ambito.client` (no lo duplica), configura `BAD_UA`, hace una sola llamada, y restaura `GOOD_UA` en `finally`.

**Bosquejo:**

```python
def probe_antibot(today: dt.date) -> ProbeResult:
    if os.getenv("VERIFY_ANTIBOT") != "1":
        return ProbeResult("antibot", "SKIPPED", "(opt-in via VERIFY_ANTIBOT=1)")
    fecha = _last_business_day(today)
    bad_ua = f"python-httpx/{httpx.__version__}"
    try:
        ambito.configure(user_agent=bad_ua)
        try:
            ambito.get_dollar_banco_nacion(fecha)
            # Si NO levanta -> respuesta 2xx con BAD_UA -> D-18 OPEN
            append_finding(_PKG, fid="F-XX", class_="ANTI-BOT", surface="sync",
                           status="OPEN", title="UA inválido NO recibió 403",
                           expected="403 con UA=python-httpx/...",
                           actual="200 OK (defensa relajada)", diff="...",
                           base_url=ambito.client._base_url)
            return ProbeResult("antibot", "FINDING", "F-XX (OPEN)")
        except ambito.AmbitoFinancieroAuthError as exc:
            # status_code 403 esperado
            if getattr(exc, "status_code", None) == 403:
                append_finding(_PKG, fid="F-XX", class_="ANTI-BOT", surface="sync",
                               status="EXPECTED", title="UA inválido recibe 403",
                               expected="403", actual="403",
                               diff="ninguno; comportamiento esperado",
                               base_url=ambito.client._base_url)
                return ProbeResult("antibot", "FINDING", "F-XX (EXPECTED)")
            raise
        except Exception as exc:
            # 429 / timeout / red -> D-18 OPEN con detalle real
            append_finding(_PKG, fid="F-XX", class_="ANTI-BOT", surface="sync",
                           status="OPEN", title=f"UA inválido produjo {type(exc).__name__}",
                           expected="403", actual=repr(exc), diff="...",
                           base_url=ambito.client._base_url)
            return ProbeResult("antibot", "FINDING", "F-XX (OPEN)")
    finally:
        ambito.configure(user_agent=_GOOD_UA)
```

### Pattern 4: `probe_schema_snapshot` con drift detection

**Bosquejo:**

```python
def probe_schema_snapshot(today: dt.date, rows: list[list[str]] | None = None) -> ProbeResult:
    fecha = _last_business_day(today)
    if rows is None:
        # Standalone path: vuelve a llamar
        resp = ambito.client._request("GET",
            f"/dolarnacion/historico-general/{fecha:%Y-%m-%d}/{fecha:%Y-%m-%d}")
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
        _SCHEMA_FILE.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
        return ProbeResult("schema_snapshot", "PASS", f"escrito {_SCHEMA_FILE.name}")
    committed = json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))
    if committed["schema"] == actual_schema:
        return ProbeResult("schema_snapshot", "PASS", "schema sin drift")
    append_finding(_PKG, fid="F-XX", class_="SHAPE", surface="both",
                   status="OPEN", title="Schema drift en get_dollar_banco_nacion",
                   expected=json.dumps(committed["schema"]),
                   actual=json.dumps(actual_schema),
                   diff="ver expected vs actual",
                   base_url=ambito.client._base_url)
    return ProbeResult("schema_snapshot", "FINDING", "F-XX (OPEN) — NO sobreescribe")
```

### Pattern 5: Tests mockeados de invariante (D-08) + regresión (D-06)

**Bosquejo:**

```python
# packages/ambito-financiero-client/tests/test_client.py

# ... tests existentes ...

# ------ Verified live (Phase 2) ------

def test_get_dollar_banco_nacion_emite_url_dia_gt_12(httpx_mock: HTTPXMock) -> None:
    """Phase 2: locking de URL emitida con día > 12 (AMB-03)."""
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0


def test_parse_ar_decimal_formato_real(httpx_mock: HTTPXMock) -> None:
    """Phase 2: locking de parse_ar_decimal('1.415,00') == 1415.0 (AMB-02)."""
    from ambito_financiero_client._parsing import parse_ar_decimal
    assert parse_ar_decimal("1.415,00") == 1415.0


# ------ Regressions ------

# (vacío hasta que un finding promovido a CONFIRMED se cierre como FIXED)
```

### Anti-Patterns to Avoid

- **Parsear el markdown existente con regex frágil para `append_finding`:** una nueva fila en el índice o un campo "Diff:" multilínea rompe el regex silenciosamente. Usar el patrón 1 (modelo interno + re-serializar el archivo completo).
- **Sobreescribir el JSON de schema en cada run:** rompe D-25. El driver SOLO escribe si `_SCHEMA_FILE` no existe; si existe, compara y emite finding sin tocar el archivo.
- **Reusar `httpx.Client` con `BAD_UA` y olvidar el `finally`:** los probes posteriores empezarían con UA roto. El cliente sync mantiene `_client` global; `configure(user_agent=...)` escribe en `_client.headers["User-Agent"]`, así que el `finally` con `GOOD_UA` es crítico.
- **Olvidar `await aio.aclose()`:** deja el cliente async con sockets abiertos al fin del proceso. D-11 lo manda explícito.
- **`asyncio.run(...)` dos veces en el driver:** D-11 obliga un único loop. Los probes async corren todos en serie dentro de `_async_main()`.
- **Tests mockeados con URL sin query string explícita:** el endpoint de Ámbito no tiene query, pero el patrón TESTING.md exige `url=` completa para validar routing. Mantenerlo.
- **`print(...)` directo sin `safe_print`:** rompe D-26. Aunque Ámbito no tenga secrets, todos los prints pasan por `safe_print(text, secrets=[])`.
- **Usar `today + 60d` como fecha por defecto en el test mockeado de no_data:** los tests son determinísticos y no dependen de `today`; usar fechas fijas (`dt.date(2026, 4, 4)` como ya hace el test existente). La fecha futura derivada de `today` es **solo para el driver vivo** (D-24).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Snapshot estructural de payload | Parser ad-hoc claves+tipos | `verification.schema.schema_of` | Ya construido en Phase 1, PII-free por construcción |
| Esqueleto del findings file | Concatenación de strings en el driver | `verification.findings.write_findings(pkg)` | Ya devuelve la `Path`, idempotente |
| Redacción de prints | f-string + replace manual | `verification.redaction.safe_print(text, secrets=[])` | Defense-in-depth + patrón cross-paquete |
| Mock de HTTP en tests | `monkeypatch` de `httpx.Client.request` | `pytest_httpx.HTTPXMock` | Stack establecido; `url=` valida routing |
| Detección de drift | Diff custom de strings | `==` sobre `schema_of` dicts | El `schema_of` produce dict con claves ordenadas |
| Capture del payload crudo | `open(...).write(...)` manual | `verification.capture.capture(pkg, ep, payload)` (opcional) | Va al staging gitignored, nunca a git |
| Parseo de decimal AR en tests | Re-implementar el `.replace` | `from ambito_financiero_client._parsing import parse_ar_decimal` | Importable; mantiene paridad con producción |

**Key insight:** Phase 1 dejó **todos** los primitivos necesarios; el trabajo de Phase 2 es **componerlos** en un flujo end-to-end + extender solo el helper de findings con `append_finding`. No re-implementar.

## Runtime State Inventory

> No aplica — esta fase no es rename/refactor/migration. No hay state stored externo (Ámbito sin auth, sin DB, sin servicio registrado, sin secret manager). El driver es process-wide; `ambito.configure(...)` en el probe anti-bot se restaura con try/finally en el mismo proceso.

Categorías auditadas (vacías por construcción):

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no DB, no cache externo | None |
| Live service config | None — Ámbito API es read-only public | None |
| OS-registered state | None — driver es script manual | None |
| Secrets/env vars | None — `.env` opcional con `AMBITO_BASE_URL` solamente | None |
| Build artifacts | None — no se rebuild ningún wheel | None |

## Common Pitfalls

### Pitfall 1: Pisar status promovido por humano en re-runs

**What goes wrong:** El driver re-corre, encuentra el mismo discrepancy, llama `append_finding(fid="F-02", status="OPEN")` y borra el status `CONFIRMED` que el humano había escrito manualmente.

**Why it happens:** Implementaciones naïve de `append_finding` sobreescriben el row de la tabla por fid sin chequear el status existente.

**How to avoid:** Patrón 1 — leer el modelo existente; si `existing[fid].status not in {"OPEN"}`, **no tocar** el finding existente (refrescar ART y serializar igual). El driver solo puede mutar findings en estado OPEN.

**Warning signs:** Un commit del findings file que retrocede un row de `CONFIRMED` a `OPEN` es la firma del bug.

### Pitfall 2: Disparar 403 repetidamente contra `mercados.ambito.com`

**What goes wrong:** IP-ban temporal del entorno de desarrollo si el probe anti-bot se corre en loop.

**Why it happens:** Falta de gate y/o un retry implícito.

**How to avoid:** D-12 (env var opt-in `VERIFY_ANTIBOT=1`), D-14 (one-shot, sin retry ni sleep), D-13 (probe corre último). El probe escribe el finding y termina. El driver SOLO llama a la API una vez por probe; no hay backoff.

**Warning signs:** Múltiples líneas `PROBE antibot: FINDING ...` en el mismo run → bug en el driver.

### Pitfall 3: Fix solo en `client.py`, olvidando `aio.py`

**What goes wrong:** El bug queda corregido en sync pero el async sigue roto. La regresión mockeada del sync pasa, la del async falla, o peor: si solo se escribe el test sync, el bug async queda silencioso.

**Why it happens:** La duplicación intencional (deuda conocida) hace fácil que el fix se aplique a una sola superficie.

**How to avoid:** D-06 obliga **dos tests** por bug (uno por superficie). El plan de Wave 4 explícita "fix en `client.py` + `aio.py` + dos tests".

**Warning signs:** Una sola línea de fix nueva en el diff; falta el espejo. CI pasa porque la regresión async no fue escrita.

### Pitfall 4: Tests mockeados que pasan pero el cliente fallaría en vivo

**What goes wrong:** Tests mockeados afirman `{"foo": 1}` pero el wire emite `{"foo": "1"}`. El mock pasa, producción rompe.

**Why it happens:** Los mocks se inventan en lugar de derivarse del payload real observado en vivo.

**How to avoid:** D-08 obliga que los tests `Verified live (Phase 2)` codifiquen lo que el driver vio en vivo. Para AMB-02, `"1.415,00"` (no `"1.415"` ni `"1.41500"`). Para AMB-03, el header row exacto `["Fecha", "Compra", "Venta"]`. Para AMB-01, el shape `list[list[str]]` (todos strings, no floats).

**Warning signs:** El payload mock difiere en tipos del schema snapshot — sintomático.

### Pitfall 5: Async test sin `aclose()` deja sockets abiertos

**What goes wrong:** Warnings de `RuntimeWarning: coroutine '...aclose' was never awaited` y leaks intermitentes.

**Why it happens:** El driver olvida `await aio.aclose()` en `_async_main`.

**How to avoid:** D-11 lo lockea. El bosquejo del driver lo incluye.

**Warning signs:** mensaje "Unclosed client session" al fin del run del driver.

### Pitfall 6: `from __future__ import annotations` olvidado

**What goes wrong:** Mypy strict pasa pero ruff levanta UP037 / E501 inconsistente entre módulos.

**How to avoid:** Convención existente (CONVENTIONS.md). Cualquier módulo nuevo (incluyendo tests de regresión y el driver reescrito) lo lleva como primera línea.

### Pitfall 7: Anchor de fecha hardcodeado en el driver

**What goes wrong:** El driver pasa a fallar el día que la fecha hardcodeada queda muy lejos en el pasado y el server cambia la disponibilidad.

**How to avoid:** D-24 lo lockea con helpers determinísticos derivados de `today`. Los tests mockeados, en cambio, sí usan fechas fijas (son deterministas y no dependen del calendario).

### Pitfall 8: `_DEFAULT_USER_AGENT` duplicado en el driver

**What goes wrong:** El día que se cambia el UA en `client.py`, el driver sigue con el viejo `_GOOD_UA` y los probes no reflejan el cliente.

**How to avoid:** El driver lee `_GOOD_UA = ambito.client._DEFAULT_USER_AGENT` (es módulo-privado pero accesible — patrón ya usado por el resto del harness, ej. `mutating_allowed` lee `matriz_client.client._base_url`).

## Code Examples

### Generar el path del schema desde el driver

```python
# Source: D-19, D-20 (CONTEXT.md)
from pathlib import Path

_SCHEMA_DIR = (
    Path(__file__).resolve().parent
    / ".planning" / "verification" / "schemas" / "ambito-financiero-client"
)
_SCHEMA_FILE = _SCHEMA_DIR / "get-dollar-banco-nacion.json"
_SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
```

### Envelope JSON D-21

```python
# Source: D-21 (CONTEXT.md)
import datetime as dt
import json

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

### Patrón pytest-httpx con URL completa (TESTING.md)

```python
# Source: .planning/codebase/TESTING.md
def test_url_emitida_dia_gt_12(httpx_mock: HTTPXMock) -> None:
    """Phase 2: AMB-03 - URL emitida con día > 12 descarta MM/DD ambiguity."""
    httpx_mock.add_response(
        url="https://mercados.ambito.com/dolarnacion/historico-general/2026-04-21/2026-04-21",
        json=[["Fecha", "Compra", "Venta"], ["21/04/2026", "1.365,00", "1.415,00"]],
    )
    assert ambito.get_dollar_banco_nacion(dt.date(2026, 4, 21)) == 1415.0
```

### Convención de regresión (TESTING.md + D-07)

```python
# Source: .planning/codebase/TESTING.md (convención original)
#         + D-07 (CONTEXT.md) que sustituye `(issue #NNN)` por `(finding F-NN)`
def test_parse_ar_decimal_dot_decimal_no_corrompe(httpx_mock: HTTPXMock) -> None:
    """Regression: parse_ar_decimal rompe ante dot-decimal '1415.00' (finding F-02).

    El server emitió `"1415.00"` en lugar de `"1.415,00"` y parse_ar_decimal
    devolvió 141500.0 (×100 corruption). Fix: detectar coma; si falta, levantar.
    """
    ...
```

### Llamada idempotente a `write_findings` y `append_finding`

```python
# Source: verification/findings.py (Phase 1) + D-10 (CONTEXT.md)
from verification import write_findings
from verification.findings import append_finding

write_findings("ambito-financiero-client")  # no-op si existe
append_finding(
    "ambito-financiero-client",
    fid="F-02",
    class_="PARAM",
    surface="both",
    status="OPEN",
    title="parse_ar_decimal rompe ante dot-decimal '1415.00'",
    expected="server emite '1.415,00' (AR-decimal con coma decimal)",
    actual="server emitió '1415.00' (dot-decimal); parse_ar_decimal -> 141500.0",
    diff="separador decimal ',' ausente; rango plausible 100..100000 superado",
    base_url=ambito.client._base_url,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `main_ambito_financiero.py` ejecuta 1 llamada (smoke) | 7 probes nombrados + summary + findings | Phase 2 (esta) | Cierra el loop completo de verificación |
| Findings file generado manualmente | `write_findings()` + `append_finding()` automáticos | Phase 1 (`write_findings`) + Phase 2 (`append_finding`) | Idempotencia + cero deriva con template |
| Sin snapshot estructural | JSON envelope D-21 con `schema_of` | Phase 2 (DRIFT-01) | Drift detection en re-runs futuros |

**Deprecated/outdated:**
- Llamada directa a `print(...)` en drivers: reemplazada por `safe_print(text, secrets=[])` por D-26.
- Asunción "snapshot vive en un solo file timestamped": D-22 explícita un solo archivo current; git history es la historia.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `safe_print` admite `secrets=[]` (lista vacía) y no truena | Pattern 2 / D-26 | Bajo — `safe_print` recorre la lista, el caso vacío es benigno. Verificado leyendo `verification/redaction.py`. [VERIFIED: redaction.py:55] |
| A2 | `ambito.client._DEFAULT_USER_AGENT` es legible desde el driver (módulo-privado por convención, no por enforcement) | Pattern 3 | Bajo — Python no enforce `_`; el harness ya usa este patrón (`mutation_gate` lee `matriz_client.client._base_url`). [VERIFIED: client.py:36 + mutation_gate.py:55] |
| A3 | Bounds `100 <= venta <= 100000` no generan falsos positivos en la vida útil esperada del ciclo | D-23 | Medio — USD/ARS hoy ~1300 (~mid-2026); el bound bajo (100) cubre histórico desde 2015; el bound alto (100k) cubre hiperinflación moderada. Ajustable durante implementación por Claude (Discretion). [ASSUMED] |
| A4 | El payload `list[list[str]]` no contiene PII en ningún campo | Deferred Ideas (no anonymize) | Bajo — el payload es FX pública (fecha + dos floats serializados como string AR). No hay nombre, cuenta, ID. [VERIFIED: client.py:84, payload doc] |
| A5 | El header del payload es exactamente `["Fecha","Compra","Venta"]` | Pattern 5 / D-08 | Bajo-Medio — está documentado en el docstring del cliente (client.py:76); confirma con el primer run vivo. Si el server cambia, el invariante de Phase 2 lo detecta (D-08 mismo). [CITED: client.py:76] |
| A6 | El probe anti-bot con `python-httpx/0.28.1` produce 403 (no 404 ni 200) | D-14 / D-18 | Bajo — el docstring del cliente lo cita textual: "La API responde 403 con UA tipo `python-httpx/...`". Si no fuera 403, D-18 lo captura como `OPEN ANTI-BOT`. [CITED: client.py:35] |
| A7 | `dt.datetime.now(dt.UTC)` produce un ISO-8601 aceptable como timestamp ART | Patterns 1, 4 | Bajo — Python 3.12 estable; `.isoformat()` devuelve `"2026-05-31T...+00:00"`. [VERIFIED: stdlib] |
| A8 | `pytest.mark.live` no se usa en esta fase | D-05 | Bajo — el marker queda disponible para uso futuro; Phase 2 es driver-only. [CITED: D-05] |

## Open Questions

1. **¿`append_finding` debe refrescar el ART block en cada call, o tener un helper separado `refresh_art_block(pkg, base_url=..., market_hours=...)`?**
   - **What we know:** D-03 dice "el ART block del header se refresca con el timestamp/base_url del run actual" pero deja el cómo a discreción. Llamar `append_finding` 0..N veces por run → si refresca, el ART queda con timestamp del último finding del run; si nunca encuentra findings, el ART nunca se refresca.
   - **What's unclear:** Si el driver no encuentra findings (todo PASS), ¿cómo se actualiza el ART block?
   - **Recommendation:** Implementar **dos helpers**: `refresh_art_block(pkg, *, base_url, market_hours=None)` separable, y `append_finding(...)` lo invoca internamente. El driver llama `refresh_art_block` al inicio del run (después de `write_findings`) para garantizar ART actualizado aun en happy run sin findings.

2. **Schema snapshot: ¿`json.dumps(..., sort_keys=False)` o `sort_keys=True`?**
   - **What we know:** D-22 dice "un solo archivo current; git history es la historia". El campo `schema` ya viene con keys ordenadas por `schema_of` (verification/schema.py:36 — `sorted(payload.items())`). El envelope tiene 6 keys top-level con un orden natural lectura (endpoint, client_function, captured_at, base_url, sample_date, schema).
   - **What's unclear:** ¿Diff-friendly prefiere envelope ordenado alfabéticamente o en el orden natural propuesto en D-21?
   - **Recommendation:** Usar el orden de D-21 (preserva ese orden con `dict` literal en Python 3.7+; `json.dumps(envelope, indent=2)` sin `sort_keys` lo respeta). El campo `schema` ya viene ordenado por construcción. El diff queda estable.

3. **Mecánica del `--accept-drift` (D-25 deja a discreción)**
   - **What we know:** Cuando hay drift, el driver NO sobreescribe el snapshot committeado. El humano necesita una manera de aceptar el drift como nueva baseline.
   - **What's unclear:** ¿Env var `ACCEPT_DRIFT=1`? ¿flag `--accept-drift` (requiere argparse en el driver)? ¿Edición manual del JSON + re-run?
   - **Recommendation:** **Edición manual + re-run** para Phase 2 (mínimo cambio de superficie en el driver; el humano borra/edita el JSON, re-corre, el driver lo re-escribe porque pasa el check `not _SCHEMA_FILE.exists()` o porque ya coincide). Si se vuelve recurrente en Phases 3-5, introducir env var `ACCEPT_DRIFT=1` consistente con `VERIFY_*` ya existente.

4. **Fecha para `probe_no_data`: `today + 60d` (D-24 draft) cae a veces en fin de semana — ¿matters?**
   - **What we know:** El cliente levanta `NoDataError` cuando `len(rows) < 2`. Una fecha futura tiene 0 rows (header solo), independiente del día de la semana.
   - **Recommendation:** Usar `today + dt.timedelta(days=60)` literal (D-24 draft) — el resultado es invariante al día de la semana porque está garantizado en el futuro.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | todo | ✓ | 3.12.11 (`uv`) | — |
| uv | comandos | ✓ | 0.9.0+ | — |
| httpx | cliente | ✓ | 0.28.1 [VERIFIED: `uv run python -c "import httpx; print(httpx.__version__)"`] | — |
| pytest + pytest-httpx + pytest-asyncio | tests | ✓ | >=8.3 / >=0.34 / >=0.24 | — |
| ruff | format/lint | ✓ | >=0.7 | — |
| mypy | type check strict | ✓ | >=1.13 | — |
| `verification/` módulo | helpers harness | ✓ | Phase 1 commiteado | — |
| `mercados.ambito.com` | probes vivos | ✓ | Servicio público | Si está caído, los probes vivos generan findings `OPEN` (clase ANTI-BOT o ERROR-MAP); el resto del flujo sigue (D-04) |
| `httpx.__version__` accesible desde Python | D-16 BAD_UA | ✓ | `0.28.1` | — |

**Missing dependencies with no fallback:** ninguna.

**Missing dependencies with fallback:** ninguna.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ + pytest-httpx 0.34+ + pytest-asyncio 0.24+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode=auto, importlib, pythonpath=["."]) |
| Quick run command | `uv run pytest packages/ambito-financiero-client -q` |
| Full suite command | `uv run pytest -q` |
| Phase gate | Full suite verde + `uv run mypy verification packages/ambito-financiero-client/src` + `uv run ruff check verification main_ambito_financiero.py packages/ambito-financiero-client` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AMB-01 | Llamada real exitosa sync+async; payload `list[list[str]]` | live driver (probe) + mocked invariant (Verified live) | live: `uv run --package ambito-financiero-client python main_ambito_financiero.py` (manual) — mocked: `uv run pytest packages/ambito-financiero-client/tests/test_client.py::test_get_dollar_banco_nacion_devuelve_venta -x` (existente) + nuevo `test_get_dollar_banco_nacion_emite_url_dia_gt_12` | ✅ existing (sync + async happy); ❌ nuevo `_emite_url_dia_gt_12` (Wave 3) |
| AMB-02 | `parse_ar_decimal` contra formato real `"1.415,00"`; detección ×100 corruption | live driver (probe_parse_decimal_adversarial con D-23) + mocked invariant + mocked regression (cuando FIXED) | live: manual (driver) — mocked: `uv run pytest packages/ambito-financiero-client/tests/test_client.py::test_parse_ar_decimal_formato_real -x` (Wave 3 nuevo) | ❌ nuevo (Wave 3) |
| AMB-03 | URL `/dolarnacion/historico-general/YYYY-MM-DD/YYYY-MM-DD` con día > 12 | live driver (probe_happy_*) + mocked invariant | mocked: `uv run pytest packages/ambito-financiero-client/tests/test_client.py::test_get_dollar_banco_nacion_emite_url_dia_gt_12 -x` | ❌ nuevo (Wave 3) |
| AMB-04 | `NoDataError` para fecha sin cotización | live driver (probe_no_data) + mocked invariant (existing) | mocked: `uv run pytest packages/ambito-financiero-client/tests/test_client.py::test_get_dollar_banco_nacion_sin_datos_levanta -x` (existente) + async equivalente | ✅ sync existente, ✅ async existente |
| AMB-05 | Paridad sync↔async | live driver (probe_parity_sync_async) + mocked: ambos test files exhiben el mismo set de invariantes | mocked: pares en `test_client.py` y `test_async_client.py` (D-09) | ❌ nuevo (Wave 3): cada test de `Verified live (Phase 2)` se duplica en `test_async_client.py` |
| AMB-06 | Probe anti-bot one-shot estructural | live driver (probe_antibot, gated por `VERIFY_ANTIBOT=1`) | live: `VERIFY_ANTIBOT=1 uv run --package ambito-financiero-client python main_ambito_financiero.py` (manual) | N/A (driver-only, gated) |
| DRIFT-01 | Snapshot estructural committeado | live driver (probe_schema_snapshot) + commit del JSON | live: manual (driver); commit del archivo `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` es el artefacto | N/A (artefacto, no test) |
| **append_finding** (helper de Wave 1) | Idempotencia por fid; preservación de status humano; re-serialización completa; refresco de ART | unit | `uv run pytest -k append_finding -x` (nuevo, opcional pero recomendado en Wave 1 — `test_findings_helper.py`) | ❌ nuevo |
| **mypy strict** del código nuevo | Cubre `verification/findings.py`, `main_ambito_financiero.py`, tests nuevos | static | `uv run mypy verification && uv run mypy packages/ambito-financiero-client/src && uv run mypy packages/ambito-financiero-client/tests` | ✅ infra existente |
| **ruff** del código nuevo | Lint + format | static | `uv run ruff check verification main_ambito_financiero.py packages/ambito-financiero-client && uv run ruff format --check verification main_ambito_financiero.py packages/ambito-financiero-client` | ✅ infra existente |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/ambito-financiero-client -q` (suite mockeada del paquete; tarda < 2s, valida regresiones e invariantes nuevos).
- **Per wave merge:** `uv run pytest -q` (suite completa del monorepo — 123+ tests pre-Phase 2; se mantiene verde).
- **Phase gate:** Suite completa verde + `uv run mypy ...` + `uv run ruff ...` + commit del schema snapshot + driver corrido al menos 1 vez manualmente (`uv run --package ambito-financiero-client python main_ambito_financiero.py`) con el findings file committeado.
- **Driver vivo:** se corre **manualmente**, NO en CI (D-02 de Phase 1: live work never enters CI). El probe anti-bot requiere `VERIFY_ANTIBOT=1` adicional.

### Wave 0 Gaps

> Phase 2 NO necesita Wave 0 separado — la infra de tests ya existe completa (Phase 1).

- [x] `pyproject.toml [tool.pytest.ini_options]` con `asyncio_mode = "auto"` — existente
- [x] `pyproject.toml pythonpath = ["."]` — existente (para que tests importen `verification/`)
- [x] `packages/ambito-financiero-client/tests/conftest.py` con `_configure_sync` / `_configure_async` autouse — existente
- [x] `conftest.py` (root) con `--live` flag y marker `live` — existente
- [x] `pytest-httpx` instalado — existente
- [x] `verification/findings.py::write_findings` + `verification/schema.py::schema_of` — existentes (Phase 1)

**Únicos test files nuevos:** opcionalmente `verification/tests/test_findings_helper.py` o `packages/ambito-financiero-client/tests/test_findings_helper.py` para tests de `append_finding` (no requerido por el CONTEXT pero recomendado para asegurar el invariante de idempotencia D-10). Si se crea, debe ir en una ubicación importable por pytest — la convención de Phase 1 (`packages/ambito-financiero-client/tests/test_harness_schema.py`, `test_harness_anonymize.py`) es el precedente: tests del harness viven bajo el paquete que primero los usa.

**Live verification (no es un "test gap" sino un "deliverable manual"):**
- [ ] Correr el driver al menos una vez para generar `.planning/verification/ambito-financiero-client-findings.md` y `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json`. Sin esto, DRIFT-01 no se cumple.

## Security Domain

> `security_enforcement = true` en `.planning/config.json`. ASVS Level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Ámbito es API pública sin auth |
| V3 Session Management | no | No hay sesión |
| V4 Access Control | no | No hay control de acceso |
| V5 Input Validation | yes | `parse_ar_decimal` valida formato; D-23 doble check estructural + rango |
| V6 Cryptography | no | No hay cripto en este flujo |
| V7 Error Handling & Logging | yes | `safe_print` (D-26) garantiza que ningún campo accidental se imprima sin máscara; redaction `_BEARER` regex cubre tokens reflejados aun sin secrets explícitos |
| V8 Data Protection | yes | El payload de Ámbito es público (FX rates), sin PII — anonymize no requerido (Deferred Idea) |
| V11 Business Logic | yes | El probe anti-bot one-shot (D-14) evita ataques accidentales al servicio (loop de 403 → potential IP-ban) — defense by design |
| V14 Configuration | yes | `configure(user_agent=BAD_UA)` con try/finally (D-15) garantiza no dejar el módulo en estado roto entre probes |

### Known Threat Patterns for stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Mock-pass + live-fail (tests mockeados consistentes pero el wire emite distinto) | Repudiation / silent failure | D-08 obliga que los mocks deriven de payloads observados en vivo; el schema snapshot detecta drift post-commit |
| Driver re-run sobrescribe finding promovido a CONFIRMED por humano | Tampering | Idempotencia por fid en `append_finding` (Pattern 1, Pitfall 1): driver solo muta findings en OPEN |
| Print accidental de un payload con campo sensible | Information Disclosure | `safe_print(text, secrets=[])` por D-26 + `_BEARER` regex de defensa-en-profundidad (cubre tokens aun sin enumeración) |
| Loop accidental de probes con `BAD_UA` → IP ban | DoS-against-self | `VERIFY_ANTIBOT=1` opt-in (D-12) + one-shot (D-14) + último en la secuencia (D-13) |
| Snapshot committeado con datos accidentales (valores en lugar de tipos) | Information Disclosure / data leak | `schema_of` produce solo tipos por construcción (verification/schema.py:36-40); test unitario en Phase 1 ya lo verifica |
| `configure(user_agent=BAD_UA)` deja estado roto al fallar | Availability / continuation bug | try/finally (D-15) garantiza restauración aun con excepción |
| Marker `@pytest.mark.live` activado accidentalmente en CI | DoS al servicio externo / lockout | D-03 Phase 1: `--live` off por default; CI nunca pasa `--live` |

## Sources

### Primary (HIGH confidence)
- `verification/findings.py` — `FINDING_CLASSES`, `STATUS_LIFECYCLE`, `findings_path`, `new_findings`, `write_findings` [VERIFIED: read]
- `verification/schema.py` — `schema_of(payload)` [VERIFIED: read]
- `verification/redaction.py` — `safe_print(text, secrets)` con defensa en profundidad [VERIFIED: read]
- `verification/__init__.py` — barrel exports [VERIFIED: read]
- `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` — superficie sync, `_DEFAULT_USER_AGENT`, `configure`, `_request`, `get_dollar_banco_nacion` [VERIFIED: read]
- `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` — superficie async espejada [VERIFIED: read]
- `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py` — `parse_ar_decimal` [VERIFIED: read]
- `packages/ambito-financiero-client/src/ambito_financiero_client/exceptions.py` — jerarquía completa [VERIFIED: read]
- `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py` — `__all__` y `__version__` [VERIFIED: read]
- `packages/ambito-financiero-client/tests/test_client.py` y `test_async_client.py` — tests existentes (smoke + auth/ratelimit/parsing/no-data) [VERIFIED: read]
- `packages/ambito-financiero-client/tests/conftest.py` — autouse fixtures `_configure_sync`/`_configure_async` [VERIFIED: read]
- `main_ambito_financiero.py` — driver actual (smoke); `_last_business_day` reusable [VERIFIED: read]
- `.planning/verification/FINDINGS-TEMPLATE.md` — plantilla con ART + 7 clases + 5 estados + pipeline anonymize [VERIFIED: read]
- `.planning/phases/02-mbito-verification/02-CONTEXT.md` — 26 decisiones D-01..D-26 + Discretion + Canonical refs + Code context + Specifics + Deferred [VERIFIED: read]
- `.planning/REQUIREMENTS.md` — AMB-01..06 y DRIFT-01 [VERIFIED: read]
- `.planning/ROADMAP.md` — Phase 2 goal + 5 success criteria + dependencies (Phase 1) [VERIFIED: read]
- `.planning/STATE.md` — last_updated 2026-05-30, focus Phase 2 [VERIFIED: read]
- `.planning/codebase/INTEGRATIONS.md` — sección Ámbito Financiero [VERIFIED: read]
- `.planning/codebase/TESTING.md` — pytest config + pytest-httpx pattern + Regression convención + async sin decorador [VERIFIED: read]
- `.planning/codebase/CONVENTIONS.md` — naming + ruff line-length=100 + mypy strict + `from __future__` mandatory [VERIFIED: read]
- `pyproject.toml` — `pythonpath = ["."]`, `asyncio_mode = "auto"`, `--import-mode=importlib`, `--strict-markers` [VERIFIED: read]
- `conftest.py` (root) — `--live` flag, marker `live`, `sys.path` con `_REPO_ROOT` [VERIFIED: read]
- `verification/env_gate.py` — `require_env(pkg, names)` (no usado en Ámbito por no requerir creds) [VERIFIED: read]
- `verification/mutation_gate.py` — patrón de import perezoso + `urlsplit().hostname` (referenciado solo como precedente) [VERIFIED: read]
- `verification/capture.py` — `capture(pkg, endpoint, payload)` (opcional para staging) [VERIFIED: read]
- `verification/anonymize.py` — pipeline (no requerido en Phase 2, Deferred Idea) [VERIFIED: read]
- `.planning/phases/01-safety-harness-verification-infrastructure/01-04-SUMMARY.md` — verificación que `verification.findings` está completo [VERIFIED: read]
- `.gitignore` — confirma `.planning/verification/captures/` ignorado [VERIFIED: read]

### Secondary (MEDIUM confidence)
- `uv run python -c "import httpx; print(httpx.__version__)"` → `0.28.1` (BAD_UA esperado = `python-httpx/0.28.1`) [VERIFIED: executed]

### Tertiary (LOW confidence)
- (ninguna)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — todo está commiteado y verificado vía lectura directa del repo
- Architecture: HIGH — los patrones existentes (Phase 1) y el bosquejo de `append_finding` se anclan en `new_findings`/`write_findings` ya implementados
- Pitfalls: HIGH — todos derivados de constraints explícitas del CONTEXT.md + observaciones del código actual
- Open Questions: MEDIUM — son decisiones de detalle interno (no de scope) que el CONTEXT ya marca como Discretion

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (30 días — stack estable, no dependencias frescas; revisar si Ámbito Financiero cambia su UA filter o el shape del payload)
