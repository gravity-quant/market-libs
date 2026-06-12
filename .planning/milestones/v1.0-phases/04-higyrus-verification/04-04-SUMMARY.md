---
phase: 04-higyrus-verification
plan: 04
subsystem: api
tags: [higyrus-client, httpx, url-encoding, iis-quirk, dual-sync-async, regression-tests]

requires:
  - phase: 04-higyrus-verification/04-02
    provides: live driver run que reveló F-01..F-06 (HTTP 400 "formato dd/mm/yyyy" por %2F en query)
provides:
  - Fix sync de higyrus_client.client._request (pre-attach query con literal `/`)
  - Fix async espejado en higyrus_client.aio._request
  - 2 regression tests dual sync+async que assertean wire-level literal `/` y ausencia de `%2F`
  - Cierre de findings F-01..F-06 (los re-runs del driver post-merge ahora pueden emitir PASS para los 6 probes cuenta-dependientes)
affects: [04-02 (continuation post-merge para re-run driver), 04-03, futuros refactors de _request en higyrus-client]

tech-stack:
  added: [urllib.parse.urlencode, urllib.parse.quote]
  patterns:
    - "URL pre-attach pattern: cuando un backend no tolera %2F en query, construir la URL como string con `urlencode(... safe='/')` y pasarla a httpx sin `params=`"
    - "Wire-encoding regression test pattern: inspeccionar httpx_mock.get_requests()[0].url.query.decode() y assertear contenido literal + ausencia de %2F"

key-files:
  created:
    - .planning/phases/04-higyrus-verification/04-04-SUMMARY.md
  modified:
    - packages/higyrus-client/src/higyrus_client/client.py
    - packages/higyrus-client/src/higyrus_client/aio.py
    - packages/higyrus-client/tests/test_client.py
    - packages/higyrus-client/tests/test_async_client.py

key-decisions:
  - "Pre-attach query a la URL con `urlencode(clean_params, quote_via=quote, safe='/')` en lugar de pasar `params=` a httpx; httpx por defecto encodea `/` como `%2F` y Higyrus IIS rechaza el formato"
  - "Mantener `drop_none(params)` upstream sin cambios — sólo el shape final del wire cambia, no el filtrado de Nones"
  - "Espejar el fix simultáneamente en `client.py` y `aio.py` (dual sync/async invariant del CLAUDE.md)"
  - "Comentario inline en castellano explica el porqué del workaround IIS para futuros readers (F-01..F-06)"

patterns-established:
  - "URL-string pre-attach con safe='/' como contramedida para backends IIS/ASP.NET que validan formato sobre el query raw sin URL-decode previo"
  - "Regression test que aserrea sobre `requests[0].url.query.decode()` para fijar el shape del wire (no solamente que el call funcione)"

requirements-completed: [HIGY-04, HIGY-06]

duration: 17min
completed: 2026-06-07
---

# Phase 04 Plan 04: httpx %2F-encoding workaround para Higyrus IIS Summary

**Fix dual sync+async: `_request` ahora pre-attachea el query string con `urlencode(... safe="/")` para preservar `/` literal en el wire, evitando que Higyrus IIS rechace el formato `dd/mm/yyyy` con HTTP 400.**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-06-07T00:54:00Z (aprox., al recibir el plan)
- **Completed:** 2026-06-08T01:12:00Z (post-final-verify + summary)
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `higyrus_client.client._request` pre-attachea query con `/` literal (sync surface).
- `higyrus_client.aio._request` espeja el cambio (async surface) — invariant dual mantenido.
- 2 regression tests nuevos (`test_request_preserves_literal_slash_in_query` sync + `test_request_preserves_literal_slash_in_query_async`) fijan el wire-level shape para evitar regresión futura.
- Findings F-01..F-06 (status OPEN, class ERROR-MAP) listos para pasar a RESOLVED tras el re-run del driver que la continuation de Plan 04-02 ejecutará post-merge.
- mypy strict, ruff check, ruff format, suite completa de 210 tests del repo — todo verde.

## Task Commits

Each task was committed atomically:

1. **Task 4-04-T1: Sync surface refactor de `_request`** — `c252eb1` (fix)
2. **Task 4-04-T2: Async surface espejo en `aio.py`** — `b2b3df9` (fix)
3. **Task 4-04-T3: Regression tests dual sync+async wire-encoding** — `78478d2` (test)

_Note: el commit de metadata final (incluye este SUMMARY.md) lo agrega execute-plan a continuación; no aparece todavía en la lista._

## Files Created/Modified

- `packages/higyrus-client/src/higyrus_client/client.py` — Importa `quote, urlencode` desde `urllib.parse`; `_request` reemplaza `params=drop_none(...)` por construcción de URL string con `urlencode(clean_params, quote_via=quote, safe="/")` pre-atachada.
- `packages/higyrus-client/src/higyrus_client/aio.py` — Espejo del cambio sync (mismos imports + misma refactorización dentro del `_request` async).
- `packages/higyrus-client/tests/test_client.py` — Agregado `import re` al tope; nueva sección `# ------ Wire encoding ------` con 1 test sync que verifica `fechaDesde=08/05/2026` literal y `%2F` ausente en el primer request capturado por `httpx_mock`.
- `packages/higyrus-client/tests/test_async_client.py` — Mismo cambio (mirror async), test `test_request_preserves_literal_slash_in_query_async`.
- `.planning/phases/04-higyrus-verification/04-04-SUMMARY.md` — Este archivo.

## Decisions Made

| Decisión | Rationale | Outcome |
|----------|-----------|---------|
| Pre-attach query a la URL (no `params=`) | httpx normaliza `/` a `%2F` y Higyrus IIS no decoda antes de validar formato → 400 | F-01..F-06 RESOLVED-pending-driver-rerun |
| `safe="/"` en `urlencode` | Mantiene literal `/` en wire; el resto de los reserved chars se encodea normalmente | Wire preserva semántica de la fecha dd/mm/yyyy |
| Espejado simultáneo sync+async | CLAUDE.md dual-sync/async invariant; cualquier divergencia en `_request` se convertiría en bug latente | Las dos surfaces se mantienen en paridad |
| Regression tests sobre `url.query.decode()` raw | Los matchers de pytest-httpx (`url=...`) normalizan `%2F`/`/` y harían pasar tests aún con el bug regresado — el assert sobre el query crudo es la única manera de fijar el shape | Tests fallarán si alguien revierte el fix |

## Deviations from Plan

**None — plan ejecutado exactamente como estaba escrito.**

Verificaciones extra realizadas (no son deviaciones, son confirmaciones del plan):

- **Pre-flight comprobación del comportamiento de pytest-httpx con `%2F` vs `/`:** Antes de empezar T1 dudé de la afirmación del plan "los tests pre-existentes... siguen verdes" porque los 3 tests pre-existentes que mockean URLs con `%2F` (`test_get_movimientos_serializa_fechas_dd_mm_yyyy`, `test_async_get_movimientos_serializa_fechas`, `test_get_posiciones_envia_booleano_capitalizado`) comparaban URLs en formato `%2F`. Tras T1 corrí los 17 tests sync — todos pasaron. La razón empírica: pytest-httpx compara `httpx.URL` con normalización que trata `%2F` y `/` como equivalentes en URL matching, aunque las representaciones canónicas de `.query` difieren. El plan tenía razón; ningún cambio necesario en tests pre-existentes.
- **Quote-style en `safe='/'`:** El plan especifica `safe='/'` (single quote) en el ejemplo de código pero la verificación grep usa `safe="/"` (double quote). Resolví extrayendo el `urlencode(...)` a su propia línea (`query = urlencode(clean_params, quote_via=quote, safe="/")`) para usar comillas dobles consistentes con el style del proyecto (ruff `quote-style="double"`), y verifiqué que el grep `grep -c 'safe="/"'` retorna `1` en ambos archivos.

## Issues Encountered

- **Workspace install inicial vacío:** El primer `uv run mypy` falló con "Cannot find implementation or library stub for module named 'dotenv'" porque el venv recién creado en el worktree no tenía las dependencias del workspace. Resolución: corrí `uv sync --all-packages --all-extras --dev --frozen` una vez al inicio. Tras eso todos los runs subsiguientes pasaron. No afectó la corrección de código.

## User Setup Required

None — no se necesita configuración externa.

## Next Phase Readiness

**Ready for post-merge:**

- El re-run del driver `HIGYRUS_SAMPLE_CUENTA=5208 uv run --package higyrus-client python main_higyrus.py` (responsabilidad de la continuation de Plan 04-02 que el orquestador correrá post-merge) ahora debe emitir PASS para los 6 probes cuenta-dependientes (`get_movimientos`, `get_posicion_valuada`, `get_posiciones` en sync+async) — F-01..F-06 RESOLVED.
- `higyrus-client-findings.md` queda pendiente de actualización por la continuation de Plan 04-02 con: F-01..F-06 → `Status: RESOLVED` + `commit_ref: c252eb1` (sync) / `b2b3df9` (async) + `regression_tests: tests/test_client.py::test_request_preserves_literal_slash_in_query, tests/test_async_client.py::test_request_preserves_literal_slash_in_query_async`; y la creación de F-07 OPEN para `get_listado_cuentas returns 0 cuentas vs smoke test 8771` (causa raíz fuera de scope, investigación deferida).

**Sin blockers nuevos.**

## Self-Check: PASSED

- `packages/higyrus-client/src/higyrus_client/client.py` — FOUND (modificado, commit c252eb1)
- `packages/higyrus-client/src/higyrus_client/aio.py` — FOUND (modificado, commit b2b3df9)
- `packages/higyrus-client/tests/test_client.py` — FOUND (modificado, commit 78478d2)
- `packages/higyrus-client/tests/test_async_client.py` — FOUND (modificado, commit 78478d2)
- Commit c252eb1 — FOUND en `git log`
- Commit b2b3df9 — FOUND en `git log`
- Commit 78478d2 — FOUND en `git log`
- Grep verificaciones del plan:
  - `params=drop_none` count en client.py == 0 — PASS
  - `urlencode` count en client.py == 2 — PASS
  - `safe="/"` count en client.py == 1 — PASS
  - `params=drop_none` count en aio.py == 0 — PASS
  - `urlencode` count en aio.py == 2 — PASS
  - `safe="/"` count en aio.py == 1 — PASS
  - `# ------ Wire encoding ------` count en test_client.py == 1 — PASS
  - `# ------ Wire encoding ------` count en test_async_client.py == 1 — PASS
  - `fechaDesde=08/05/2026` count en tests dir == 2 — PASS

Static checks (todos verdes):
- `uv run mypy packages/higyrus-client` — Success
- `uv run mypy packages/higyrus-client/tests` — Success
- `uv run ruff check packages/higyrus-client/{src,tests}` — All checks passed
- `uv run ruff format --check packages/higyrus-client/{src,tests}` — Already formatted

Test suite:
- `uv run pytest packages/higyrus-client/ -q` — 29 passed (17 sync + 10 async + 2 wire encoding)
- `uv run pytest -q` (todo el repo) — 210 passed, 1 deselected (sin regresiones cross-package)

---
*Phase: 04-higyrus-verification*
*Completed: 2026-06-07*
