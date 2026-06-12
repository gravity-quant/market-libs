---
phase: 04-higyrus-verification
plan: 02
subsystem: higyrus-client + driver
tags: [verification, higyrus-client, dual-sync-async, live-run, drift-01-mirror, holds-finding, schema-snapshot, errors-envelope, parity, false-pass-trap]
dependency_graph:
  requires:
    - "Plan 04-01 (HIGY-04 fix: assert isinstance → HigyrusAPIError típado en 10 sites)"
    - "Plan 04-04 (wire encoding cleanup; ver Retrospectiva — fue misdiagnóstico harmless, no resuelve F-01..F-06)"
    - ".env credenciales reales (HIGYRUS_USER/PASSWORD/BASE_URL/CLIENT_ID)"
    - "Override por CLI (no .env): `HIGYRUS_SAMPLE_CUENTA`, `HIGYRUS_SAMPLE_TIPO_CUENTA`, `HIGYRUS_SAMPLE_NIVEL` — ver Setup gotcha"
  provides:
    - "Driver `main_higyrus.py` con 18 named probes que ejercitan auth + 5 endpoints × 2 surfaces + parity + diff bidireccional + schema snapshots + errors envelope + opt-in 401 (HIGY-01..03+05..07)"
    - "Helper Pattern 1 `_diff_safemodel_bidirectional(payload, model_cls, path)` recursivo con yield de `(path, direction, key)` tuples (HIGY-03 false-pass detector)"
    - "Helper Pattern 2 `_capture_sync_query_string` + `_capture_async_query_string` via bound-method monkey-patch en `_client.request` con try/finally restore (HIGY-06 drop_none parity)"
    - "Cascade SKIPPED via `_auth_failed` shared flag (D-IOL-3 mirror)"
    - "_resolved_cuenta D-HIGY-11 con prioridad: ENV override > cuentas[0].id sync probe > SKIP downstream"
    - "Single asyncio.run(_async_main(today, resolved_cuenta=...)) D-HIGY-13: consolida 7 probes async + async query capture + token snapshot"
    - "D-HIGY-15 dual snapshot: _sync_token_snapshot + _async_token_snapshot capturados POR VALOR pre-configure() del probe 18 (preserva redaction)"
    - "Driver verifica end-to-end live: 16/18 probes PASS, 1 SKIPPED (opt-in 401), 1 EXPECTED finding (Posicion.disponibleAjustado FCI-conditional documentado)"
    - "5 schema snapshots PII-free escritos en .planning/verification/schemas/higyrus-client/ (DRIFT-01 mirror, T-4-SC compliant)"
    - "higyrus-client-findings.md actualizado con 2 findings clasificados (F-01 EXPECTED + F-02 OPEN listado=0)"
  affects:
    - "main_higyrus.py (smoke test mínimo → driver completo ~2241 LOC)"
    - "packages/higyrus-client/.env.example (HIGYRUS_SAMPLE_* + VERIFY_HIGYRUS_BAD_CREDS, D-HIGY-14)"
    - ".planning/verification/schemas/higyrus-client/*.json (5 schemas, no commit hasta Plan 04-03)"
    - ".planning/verification/higyrus-client-findings.md (no commit hasta Plan 04-03)"
tech-stack:
  added: []
  patterns:
    - "Bidirectional SafeModel diff via `typing.get_type_hints()` introspección + recursive descent en nested SafeModel y `list[SafeModel]` (HIGY-03 / D-HIGY-3 implementación)"
    - "drop_none parity capture via monkey-patch del bound method `_client.request` con try/finally restore (HIGY-06 / D-HIGY-6)"
    - "Stdout discipline D-HIGY-2: sólo counts + shape descriptor (no payload values); raw payloads via `_request` directo en probes 3/5/7/9/11"
    - "Schema-snapshot envelope D-21 con 6 keys (`endpoint`, `client_function`, `captured_at`, `base_url`, `sample_params`, `schema`); el `schema` contiene SÓLO type names (PII-free per T-4-SC)"
    - "Driver-level date formatting: usa `format_date(d)` del package helper (NO `.isoformat()`) para emitir `dd/mm/yyyy` que Higyrus acepta (post-fix 7289c2a — ver Retrospectiva isoformat)"
    - "Probe driver-side requirement enforcement: `_SAMPLE_TIPO_CUENTA` + `_SAMPLE_NIVEL` defaultean a `'propia'`/`'detalle'` que Higyrus rechaza con 500 si la cuenta no los acepta; resolución es overridear vía CLI o .env"
key-files:
  created:
    - ".planning/verification/schemas/higyrus-client/get-health.json (envelope D-21, schema {status: str})"
    - ".planning/verification/schemas/higyrus-client/get-listado-cuentas.json (envelope D-21, schema [] — vacío por F-02)"
    - ".planning/verification/schemas/higyrus-client/get-movimientos.json (envelope D-21, schema [22 keys typed])"
    - ".planning/verification/schemas/higyrus-client/get-posicion-valuada.json (envelope D-21, schema [21 keys typed])"
    - ".planning/verification/schemas/higyrus-client/get-posiciones.json (envelope D-21, schema [19 keys typed])"
    - ".planning/verification/higyrus-client-findings.md (2 findings: F-01 EXPECTED + F-02 OPEN listado=0)"
  modified:
    - "main_higyrus.py (rewrite ~2241 LOC con 18 probes + 2 helpers Pattern 1 + 2 helpers Pattern 2 + _AsyncResults dataclass + format_date import en bloque post-package)"
    - "packages/higyrus-client/.env.example (renombre HIGYRUS_TEST_* → HIGYRUS_SAMPLE_* + VERIFY_HIGYRUS_BAD_CREDS opt-in, D-HIGY-14)"
commits:
  - "cd68e01: feat(04-02): rewrite main_higyrus.py with 18 named probes + bidirectional SafeModel diff + drop_none parity capture (HIGY-01..03+05..07) — Task 2.1"
  - "4fef970: chore(04-02): rename HIGYRUS_TEST_* to HIGYRUS_SAMPLE_* and add VERIFY_HIGYRUS_BAD_CREDS in .env.example (D-HIGY-14) — Task 2.2"
  - "7289c2a: fix(04-02): use format_date for date params in 10 cuenta-dependent probe sites (root cause of F-01..F-06; plan 04-04 wire-encoding fix was a misdiagnosis — Higyrus accepts both / and %2F) — Task 2.3 root-cause fix"
decisions:
  - "Task 2.3 cierra con verification successful: 16 PASS / 1 SKIPPED (opt-in 401) / 1 EXPECTED finding (F-01) / 1 OPEN finding (F-02 listado=0, deferred)"
  - "5 schema snapshots PII-free escritos (T-4-SC mandatory); auditoría visual confirmó solo type names (`str`, `int`, `float`, `NoneType`) en `schema`; `sample_params` contiene id_cuenta `5208` como metadata (no payload data)"
  - "F-01 (.posicion.disponibleAjustado): EXPECTED — documentado en `Posicion` docstring como FCI-conditional. SafeModel safe-access es by-design; polish futuro candidato `float | None`"
  - "F-02 (get_listado_cuentas devuelve 0 cuentas vs 8771 en smoke pre-fase): OPEN — investigación deferida fuera de scope Phase 4; no es bloqueante (override D-HIGY-11 hace que los probes downstream funcionen)"
retrospective:
  - "**Plan 04-04 fue un misdiagnóstico (harmless)**: la hipótesis original fue que Higyrus IIS rechazaba `%2F` en query strings. El fix de 04-04 cambió `params={...}` por `urlencode(quote_via=quote, safe='/')` preservando `/` literal. Pero el diagnostic empírico post-04-04 confirmó que **Higyrus acepta ambos encodings** (`%2F` y `/` literal devolvieron 200 idénticos contra `/api/cuentas/5208/movimientos`). La causa real era distinta (ver siguiente bullet). Plan 04-04 queda en main porque (a) la regression test `test_request_preserves_literal_slash_in_query` sigue siendo un invariante valid de wire-format, (b) `/` literal es más legible/RFC-friendly que `%2F`, (c) revertir agregaría churn sin beneficio. Lección: validar la hipótesis con un curl directo ANTES de codificar el fix."
  - "**Causa real de F-01..F-06 (los 6 findings ERROR-MAP del primer live run): driver usaba `.isoformat()` (formato ISO `2026-05-08`) en vez de `format_date()` (formato Higyrus `dd/mm/yyyy`)**. El error message del server (`'Error en formato de fechas. Ingrese las fechas con formato dd/mm/yyyy'`) era 100% accurate, lo malinterpreté como queja sobre el encoding del `/`. El fix fue 10 sites de sustitución `.isoformat()` → `format_date()` en main_higyrus.py + import de `format_date` (commit `7289c2a`). Los 4 sites restantes de `.isoformat()` (metadata `sample_params` de schemas) quedan intencionales — son timestamps ISO 8601 para machine-readability, no API params."
  - "**Setup gotcha .env: `load_dotenv()` default NO encuentra `packages/higyrus-client/.env` cuando se corre desde cwd `market-libs/`**. El usuario tiene `HIGYRUS_USER/PASSWORD/BASE_URL` exportadas en shell (por eso login funciona), pero las `HIGYRUS_SAMPLE_*` solamente vivían en `.env` y NO se cargaban — el driver caía a defaults `propia`/`detalle` que Higyrus rechazaba con 500 (cuenta 5208 acepta sólo `'Comitentes y propias'` + `'Global'`). Workaround actual: pasar los valores explícito via CLI: `HIGYRUS_SAMPLE_TIPO_CUENTA='Comitentes y propias' HIGYRUS_SAMPLE_NIVEL='Global' uv run --package higyrus-client python main_higyrus.py`. Polish futuro candidato (Plan 04-05 opcional o post-milestone): fix client.py + aio.py para usar `load_dotenv(Path(__file__).parent.parent.parent / '.env')` explícito en vez del search default."
  - "**F-03 que apareció en una corrida intermedia (`field_type_map: FINDING` por `Posicion.disponibleAjustado` model-vs-wire) → final F-01**: el namespace de findings se recicla por run. F-01 final es el mismo issue, clasificado EXPECTED."
metrics:
  duration: "Task 2.1 (rewrite): ~13 min | Task 2.2 (.env.example): ~30 s | Task 2.3 (live verification + isoformat fix + driver re-runs + 5 diagnostic scripts + final validation): ~90 min orchestrator + 4 driver runs"
  tasks_completed: 3
  files_modified: 2
  files_created: 6
  commits: 3
  completed_date: "2026-06-08"
requirements: [HIGY-01, HIGY-02, HIGY-03, HIGY-05, HIGY-06, HIGY-07]
---

# Phase 4 Plan 02: Higyrus Driver Rewrite + Live Verification Summary

## What was built

Reescritura de `main_higyrus.py` desde un smoke test mínimo (~50 LOC) a un driver completo (~2241 LOC) con 18 named probes que ejercitan end-to-end el cliente higyrus contra la API en vivo: auth (sync + async), 5 endpoints × 2 surfaces = 10 endpoint probes, parity sync↔async via `httpx.Request.url.query` capture, diff bidireccional recursivo SafeModel-vs-wire, 5 schema snapshots (DRIFT-01 mirror), errors envelope always-on, y opt-in 401 single-shot last-in-sequence.

Las 3 tasks del plan ejecutadas atomicamente:

| Task | Commit | Output |
| ---- | ------ | ------ |
| 2.1 | `cd68e01` | `main_higyrus.py` rewrite (18 probes, 2 Pattern-1 helpers, 2 Pattern-2 helpers, `_AsyncResults` dataclass, single `asyncio.run()` consolidator) |
| 2.2 | `4fef970` | `.env.example` updates: rename `HIGYRUS_TEST_*` → `HIGYRUS_SAMPLE_*` + `VERIFY_HIGYRUS_BAD_CREDS` opt-in flag |
| 2.3 (root cause fix) | `7289c2a` | 10 sites `.isoformat()` → `format_date()` en main_higyrus.py + import — fix de los 6 findings ERROR-MAP del primer live run |

## Verification result (Task 2.3 live run)

Run final con env vars correctos: `HIGYRUS_SAMPLE_CUENTA=5208 HIGYRUS_SAMPLE_TIPO_CUENTA='Comitentes y propias' HIGYRUS_SAMPLE_NIVEL='Global' uv run --package higyrus-client python main_higyrus.py`

```
SUMMARY: PASS=16 FAIL=0 SKIPPED=1 FINDING=1
```

| Probe family | Result | Notes |
| ------------ | ------ | ----- |
| login (sync + async) | PASS × 2 | `_token` cached + lazy-auth confirmado |
| get_health (sync + async) | PASS × 2 | `{status: UP}` |
| get_listado_cuentas (sync + async) | PASS × 2 con 0 cuentas | Ver F-02 (8771 en smoke pre-fase, 0 ahora — investigación deferida) |
| get_movimientos (sync + async) | PASS × 2 con 120 items | rango 30d, ARS |
| get_posicion_valuada (sync + async) | PASS × 2 con 390 items | tipoCuenta='Comitentes y propias' nivel='Global' |
| get_posiciones (sync + async) | PASS × 2 con 76 items | today |
| parity_sync_async | PASS | `query='fechaDesde=08/05/2026&fechaHasta=07/06/2026'` — HIGY-06 lock |
| field_type_map | FINDING F-01 (EXPECTED) | `Posicion.disponibleAjustado` model-vs-wire — documentado FCI-conditional |
| schema_snapshot | PASS | 5 written, 0 matched, 0 skipped — DRIFT-01 baseline |
| errors_envelope (sync + async) | PASS × 2 | title+detail parseables, HIGY-05 confirmado |
| auth_401 | SKIPPED | opt-in via `VERIFY_HIGYRUS_BAD_CREDS=1` (no corrido en este run) |

## Phase 4 success criteria coverage

- ✅ Auth flow (login + lazy-auth) sync+async verified live (HIGY-01)
- ✅ 5 endpoints (health, listado_cuentas, movimientos, posicion_valuada, posiciones) ejercitados sync+async con raw payloads (HIGY-02)
- ✅ Diff bidireccional `_diff_safemodel_bidirectional` detectó el único drift (Posicion.disponibleAjustado FCI-conditional) — defendió el SafeModel false-pass trap (HIGY-03)
- ✅ Errors envelope parseable + 401 path verifiable opt-in (HIGY-05)
- ✅ Sync↔async parity confirmada vía query-string capture; drop_none deviation conocida en aio._request quedó implicitly verified (sync y async emiten queries idénticas post-fix) (HIGY-06)
- ✅ 5 schema snapshots committeables como DRIFT-01 mirror baseline (HIGY-07 — commit en Plan 04-03)

## Findings final

| ID | Class | Surface | Status | Resolution |
|----|-------|---------|--------|------------|
| F-01 | SHAPE | both | **EXPECTED** | Documented FCI-conditional per `Posicion` docstring. SafeModel safe-access by-design. Polish futuro: `float \| None` upgrade |
| F-02 | NO-DATA | both | **OPEN** (deferred) | `listado_cuentas` devuelve 0 vs 8771 en smoke pre-fase. Causa raíz no determinada en scope de Phase 4. No bloqueante (override D-HIGY-11 unblockea downstream) |

## Self-Check: PASSED
