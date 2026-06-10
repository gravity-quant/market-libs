---
phase: 02-mbito-verification
plan: 02
subsystem: ambito-driver
tags: [verification, driver, probes, live-api, schema-snapshot, drift-01]
dependency-graph:
  requires:
    - verification.findings.append_finding (Plan 02-01)
    - verification.write_findings + safe_print + schema_of (Phase 1 + Plan 02-01 barrel)
    - ambito_financiero_client (sync) + ambito_financiero_client.aio (async)
    - ambito_financiero_client._parsing.parse_ar_decimal
    - ambito_financiero_client.exceptions (AmbitoFinancieroAuthError, AmbitoFinancieroNoDataError, AmbitoFinancieroAPIError)
  provides:
    - main_ambito_financiero.py (rewritten driver, 9 top-level callables incl. 7 probes + main + _last_business_day_with_day_gt_12)
    - .planning/verification/ambito-financiero-client-findings.md (generated at runtime via write_findings; NOT committed in this plan)
    - .planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json (generated at runtime, DRIFT-01; NOT committed in this plan)
  affects:
    - Plan 02-03 (live execution + checkpoint + artifact commit + mocked regression tests)
tech-stack:
  added: []
  patterns:
    - "@dataclass(frozen=True, slots=True) for ProbeResult — mirrors verification.anonymize.Denylist"
    - "Single asyncio.run() in main() wrapping _async_main with try/finally aio.aclose() — Pitfall 5"
    - "try/finally for ambito.configure(user_agent=...) restoration in probe_antibot — D-15"
    - "Read-only access to private module state (ambito.client._base_url, ambito.client._DEFAULT_USER_AGENT) — precedent verification/mutation_gate.py:55"
    - "module-level _fid_counter + _next_fid() helper for deterministic F-NN ids"
    - "schema_of(rows) + envelope D-21 with mkdir(parents=True, exist_ok=True) + write_text JSON — drift detection compares committed['schema'] vs actual, NEVER overwrites on drift (D-25)"
    - "safe_print(text, secrets=[]) for all stdout — uniform across packages even when no credentials (D-26)"
key-files:
  created:
    - .planning/phases/02-mbito-verification/02-02-SUMMARY.md
  modified:
    - main_ambito_financiero.py
decisions:
  - "rows_sync propagation: tuple-return from probe_happy_sync (ProbeResult, list[list[str]] | None) — explicit parameter passing to probes 3/4/6. No module-level cache; avoids global mutable state for cross-probe data flow."
  - "probe_happy_async returns tuple[ProbeResult, float | None] paralelo al sync; el _async_main lo desempaqueta y main() pasa el float a probe_parity_sync_async después del asyncio.run."
  - "_next_fid() = counter sequence (F-01, F-02, ...) module-level, incremented in order of finding emission. NOT derived from probe name. Deterministic dentro de un run; entre runs el orden depende de qué probes emiten findings (siempre asciende)."
  - "D-21 envelope kept verbatim from PATTERNS.md sketch: endpoint, client_function, captured_at (UTC isoformat), base_url (read from ambito.client._base_url), sample_date (fecha hábil isoformat), schema (last). No sort_keys — insertion order preserved."
  - "Bounds D-23 kept at draft values: _VENTA_MIN=100.0, _VENTA_MAX=100_000.0. Today USD/ARS ~1400; rango deja amplio margen. Si en el live run de 02-03 hay falso positivo, ajustar y documentar."
  - "Async happy probe re-pega el endpoint (await aio._request) en lugar de reusar rows_sync. Trade-off: 2x request al server vs verificar shape async independientemente. Elegido: pegada extra para que parity sea un check real, no tautológico."
  - "Wide except Exception en cada probe (con type(exc).__name__ + repr en el finding) para satisfacer D-04 (driver no corta). No swallow silencioso — siempre llama append_finding antes de devolver FINDING."
metrics:
  duration: ~13 min
  completed: "2026-06-02T23:44:24Z"
  commits: 1
  tasks_total: 1
  tasks_completed: 1
---

# Phase 2 Plan 02: Driver Rewrite con 7 Probes Nombrados Summary

One-liner: Reescribí `main_ambito_financiero.py` desde un smoke-test mínimo a un driver de verificación viva con 7 probes nombrados (D-01) que ejercen sync+async de `get_dollar_banco_nacion`, validan shape/paridad/parsing/no-data/schema/anti-bot, alimentan el findings markdown via `append_finding` y producen el primer schema snapshot DRIFT-01 con detección de drift no destructiva (D-25).

## What Was Built

Single-file rewrite of `main_ambito_financiero.py` (38 → 675 líneas) que cumple las 7 reglas D-01..D-26 lockeadas en `02-CONTEXT.md`:

### 9 callables públicos al tope de módulo

| Símbolo | Firma | Rol |
|---|---|---|
| `probe_happy_sync` | `(today: dt.date) -> tuple[ProbeResult, list[list[str]] | None]` | Happy path sync; captura rows crudos para reutilizar en probes 3/4/6. |
| `probe_happy_async` | `async (today: dt.date) -> tuple[ProbeResult, float | None]` | Happy path async; devuelve precio para probe 3 (parity). |
| `probe_parity_sync_async` | `(today, rows_sync, precio_async) -> ProbeResult` | Compara `parse_ar_decimal(rows_sync[1][2])` vs `precio_async`. |
| `probe_parse_decimal_adversarial` | `(rows_sync) -> ProbeResult` | D-23 doble check: separador coma + rango plausible. |
| `probe_no_data` | `(today) -> ProbeResult` | `today + 60d` debe levantar `AmbitoFinancieroNoDataError`. |
| `probe_schema_snapshot` | `(today, rows_sync) -> ProbeResult` | DRIFT-01: escribe primera vez, compara siguientes (D-25 NO sobreescribe). |
| `probe_antibot` | `(today) -> ProbeResult` | Opt-in `VERIFY_ANTIBOT=1`; one-shot BAD_UA; D-15 try/finally restore. |
| `main` | `() -> None` | Orquesta los 7 en el orden D-13 + emite summary verbatim D-02. |
| `_last_business_day_with_day_gt_12` | `(today) -> dt.date` | Nuevo helper D-24 (AMB-03) adyacente al existente `_last_business_day`. |

### Estructura interna

- **`ProbeResult`** — `@dataclass(frozen=True, slots=True)` con `name: str`, `status: str` (`"PASS" | "FAIL" | "SKIPPED" | "FINDING"`), `detail: str`. Patrón cogido de `verification.anonymize.Denylist`.
- **`_fid_counter` + `_next_fid()`** — contador module-level que emite `F-01, F-02, ...` zero-padded a 2 dígitos. Mantiene orden de aparición de findings dentro de un run.
- **Constantes module-level**:
  - `_PKG = "ambito-financiero-client"`
  - `_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG` (D-19)
  - `_SCHEMA_FILE = _SCHEMA_DIR / "get-dollar-banco-nacion.json"` (D-20 slug = kebab-case del nombre de función)
  - `_ENDPOINT_TEMPLATE`, `_EXPECTED_HEADER`, `_VENTA_MIN=100.0`, `_VENTA_MAX=100_000.0`
- **`_async_main(today)`** — wrapper con `try / finally: await aio.aclose()` (Pitfall 5); invocado por `asyncio.run(...)` exactamente una vez desde `main()` (D-11).

### Cumplimiento de las reglas locked

| Regla | Cómo se cumple en el código |
|---|---|
| D-01 | 7 probes nombrados al tope; verificado por `import + hasattr`. |
| D-02 | `safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=[])` + `safe_print(f"SUMMARY: PASS={...} FAIL={...} SKIPPED={...} FINDING={...}", secrets=[])`. |
| D-03 | `write_findings(_PKG)` llamado al inicio de `main()` (helper es idempotente). |
| D-04 | Cada probe envuelve su lógica en `try/except` con clase apropiada del finding y nunca propaga. |
| D-10 | Cada finding va por `append_finding(...)` que refresca el ART block. |
| D-11 | Un único `asyncio.run(_async_main(today))` en `main()`. |
| D-12 | `probe_antibot` chequea `os.getenv("VERIFY_ANTIBOT") != "1"` y devuelve SKIPPED. |
| D-13 | `main()` invoca probes en orden 1..7 con `probe_antibot` último. |
| D-14 | Una sola llamada a `ambito.get_dollar_banco_nacion` dentro de `probe_antibot`; **`time.sleep` no aparece en el archivo**. |
| D-15 | `try / finally: ambito.configure(user_agent=good_ua)` restaura el cliente. |
| D-16 | `bad_ua = f"python-httpx/{httpx.__version__}"`. |
| D-17 | `probe_antibot` es sync (no `async def`). |
| D-18 | Tres ramas: 200 OK → OPEN, 403 → EXPECTED, otro → OPEN; todas via `append_finding`. |
| D-19 | Schema file en `.planning/verification/schemas/<pkg>/`. |
| D-20 | Slug `get-dollar-banco-nacion.json` (kebab-case de `get_dollar_banco_nacion`). |
| D-21 | Envelope JSON: `endpoint, client_function, captured_at, base_url, sample_date, schema` en este orden de inserción. |
| D-23 | Doble check: `if "," not in venta_raw` → PARAM OPEN; `if not (_VENTA_MIN <= venta <= _VENTA_MAX)` → SHAPE OPEN. |
| D-24 | `today + 60d` en `probe_no_data` + helper `_last_business_day_with_day_gt_12`. |
| D-25 | `if not _SCHEMA_FILE.exists(): write else compare; en drift NO write — append_finding SHAPE OPEN`. |
| D-26 | Todos los prints van por `safe_print(text, secrets=[])`. |

## Tasks Executed

| # | Task | Type | Commit | Files |
| - | ---- | ---- | ------ | ----- |
| 2.1 | Rewrite main_ambito_financiero.py con 7 named probes | auto | b9a8e24 | `main_ambito_financiero.py` |

## Verification Results

| Check | Command | Result |
| ----- | ------- | ------ |
| Import + 9 entries | `uv run python -c "import main_ambito_financiero; ..."` | "all 9 entries present" |
| Static (types) | `uv run mypy main_ambito_financiero.py` | Success: no issues found in 1 source file |
| Static (lint) | `uv run ruff check main_ambito_financiero.py` | All checks passed |
| Static (format) | `uv run ruff format --check main_ambito_financiero.py` | 1 file already formatted |
| D-14 (no sleep) | `python -c "src=open(...).read(); assert 'time.sleep' not in src"` | OK |
| D-11 (single event loop) | `python -c "assert src.count('asyncio.run(') == 1"` | OK |
| safe_print count | `grep -v '^#' main_ambito_financiero.py | grep -c 'safe_print('` | 2 (>=2 required) |
| Full suite | `uv run pytest -q` | 166 passed, 1 deselected — **no regressions** (same as baseline post-02-01) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff I001 import order**

- **Found during:** Task 2.1 verify step (`uv run ruff check`).
- **Issue:** Initial draft kept the planned order `httpx` → workspace packages → `verification`. Ruff's isort applies `known-third-party` heuristics that grouped `verification` together with `httpx` (third-party / single-letter import path heuristic) and put `ambito_financiero_client` in a separate "first-party" group.
- **Fix:** Ran `uv run ruff check --fix main_ambito_financiero.py`. The final order is `httpx` + `verification` + `verification.findings` (third-party group) → `ambito_financiero_client` group (first-party). Both groups separated by blank line; both alphabetical within group. Functionally equivalent; semantics unchanged.
- **Files modified:** `main_ambito_financiero.py`.
- **Commit:** b9a8e24 (single commit, before push).

**2. [Rule 3 - Blocking] ruff RUF100 unused noqa**

- **Found during:** Task 2.1 verify step (`uv run ruff check`).
- **Issue:** Initial draft annotated each `except Exception` with `# noqa: BLE001` defensively, assuming `BLE` was in the active ruff ruleset. Project `pyproject.toml` only enables `E, W, F, I, B, UP, SIM, RUF, ASYNC, PIE, PT, RET, TID` (no `BLE`), so RUF100 flagged the directives as unused.
- **Fix:** Removed all 6 `# noqa: BLE001` comments via `ruff check --fix`. Wide `except Exception` remains intact (it's legal under the active rules — `B902/B904` and family don't fire on this shape). Semantics unchanged.
- **Files modified:** `main_ambito_financiero.py`.
- **Commit:** b9a8e24.

Both fixes were applied automatically via `ruff check --fix` within the same task. No architectural changes, no functional differences.

### Authentication Gates

None — Ámbito es API pública sin credenciales.

## Key Decisions

- **`rows_sync` propagation** — Tuple-return from `probe_happy_sync` + explicit param passing to probes 3/4/6. Considerada y descartada: cache module-level (rompe testabilidad y la convención del repo de no mantener estado cruzado entre probes); re-fetch en cada probe (extra latencia + potencial drift de fechas si el run cruza medianoche). El tuple es el más simple y testeable.
- **`probe_happy_async` retorna tuple `(ProbeResult, float | None)`** — Espejo del sync. El `_async_main` desempaqueta y `main()` pasa el float a `probe_parity_sync_async` después del `asyncio.run(...)`. Único event loop preservado (D-11).
- **`_next_fid()` = counter sequence, no naming convention** — Más simple, deterministic dentro del run, y respeta el "naming" del findings file (`F-01`, `F-02`, ...). Si dos runs emiten findings distintos, el ID se asigna por orden de emisión en ese run; humanos promueven status via edición manual y el `append_finding` preserva (D-10).
- **D-21 envelope verbatim** — Sin sort_keys; orden de inserción Python 3.7+ preservado. Esquema: `endpoint, client_function, captured_at, base_url, sample_date, schema`. JSON committeable con `+ "\n"` trailing newline (convención UNIX).
- **Bounds D-23 sin ajustar** — `_VENTA_MIN=100.0`, `_VENTA_MAX=100_000.0` mantenidos del plan. Hoy USD/ARS ~1400; ambos bordes a >10× de distancia. Si en el live run de 02-03 hay falso positivo, ajustar.
- **Async happy probe re-pega el endpoint** — `await aio._request(...)` independiente del sync. Trade-off: 2 requests al server vs un check de parity tautológico (mismo payload mockeado). El propósito del probe es detectar drift sync↔async real, así que la pegada independiente es la elección correcta.
- **Wide `except Exception` por probe** — Necesario para satisfacer D-04 (driver no corta). Mitigación: cada except llama `append_finding` con `type(exc).__name__ + repr(exc)` antes de devolver FINDING, así no hay swallowing silencioso.
- **Lectura de estado privado `ambito.client._base_url` y `ambito.client._DEFAULT_USER_AGENT`** — Precedente: `verification/mutation_gate.py:55`. Solo lectura; comentado inline. mypy strict / ruff no se quejan (el `_` prefix es convención de documentación, no enforcement en Python).

## Threat Flags

None. El plan's `<threat_model>` (T-2-06 a T-2-12) fue la baseline de diseño:

- **T-2-06 (DoS/IP-ban)** — mitigado por D-12 opt-in + D-14 one-shot + D-13 antibot último. Verificado: `time.sleep` no aparece en el archivo, una sola llamada en `probe_antibot`.
- **T-2-07 (tampering UA)** — mitigado por `try/finally` con `ambito.configure(user_agent=good_ua)` en finally. Verificado: el bloque try/finally es estructural en `probe_antibot`.
- **T-2-08 (schema overwrite en drift)** — mitigado por D-25: `if not _SCHEMA_FILE.exists(): write else compare; en drift, NO write — append_finding SHAPE OPEN`.
- **T-2-09 (PII disclosure en prints)** — mitigado por D-26: todos los prints via `safe_print(text, secrets=[])`. `_BEARER` regex cubre tokens reflejados aun con secrets vacíos.
- **T-2-10 (repudiation ART)** — mitigado por T-2-03 ya cubierto en `append_finding` (Plan 02-01).
- **T-2-11 (fechas hardcodeadas obsoletas)** — mitigado por D-24: `_last_business_day(today)` + `_last_business_day_with_day_gt_12(today)` + `today + 60d`.
- **T-2-12 (schema con valores reales)** — mitigado por `schema_of` (Phase 1; PII-free by construction).
- **T-2-SC** — N/A; no se instalan packages.

## Known Stubs

None. El driver está completo desde la perspectiva del plan: cumple las 9 callables requeridas, mypy/ruff verdes, tests del suite pre-existente sin regresiones, y genera dos artefactos committeable cuando se corre. **Pendiente para 02-03**: ejecución viva (`python main_ambito_financiero.py`) con checkpoint humano para inspeccionar los artefactos generados (findings + schema) antes de commitearlos.

## Self-Check: PASSED

Verified files exist:

- `main_ambito_financiero.py` (modified) — FOUND
- `.planning/phases/02-mbito-verification/02-02-SUMMARY.md` — FOUND (this file)

Verified commit exists:

- b9a8e24 — FOUND (`git log --oneline -1 b9a8e24`)

Generated artifacts (created at runtime by `python main_ambito_financiero.py`, NOT committed in this plan):

- `.planning/verification/ambito-financiero-client-findings.md` — NOT YET (no live run in this plan)
- `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` — NOT YET (no live run in this plan)

Both artifacts will materialize in Plan 02-03 after the human verification checkpoint.
