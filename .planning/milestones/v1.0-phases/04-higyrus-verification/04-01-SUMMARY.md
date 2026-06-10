---
phase: 04-higyrus-verification
plan: 01
subsystem: higyrus-client
tags: [verification, higyrus-client, dual-sync-async, regression-tests, shape-mismatch, exception-fix, prophylactic]
dependency_graph:
  requires:
    - "higyrus_client.exceptions.HigyrusAPIError (pre-existing)"
    - "higyrus_client._request / aio._request (pre-existing)"
  provides:
    - "Defensa tipada contra shape mismatch en los 10 sites (5 sync + 5 async)"
    - "Sentinel `status_code=0` documentado para errores client-side"
    - "10 regression tests mockeados (5 sync + 5 async) que lockean el comportamiento"
  affects:
    - "packages/higyrus-client/src/higyrus_client/client.py"
    - "packages/higyrus-client/src/higyrus_client/aio.py"
    - "packages/higyrus-client/src/higyrus_client/exceptions.py"
    - "packages/higyrus-client/tests/test_client.py"
    - "packages/higyrus-client/tests/test_async_client.py"
tech-stack:
  added: []
  patterns:
    - "Reemplazo de `assert isinstance(raw, T)` por `if not isinstance: raise HigyrusAPIError(0, [...])` tipado (mitiga T-4-08: `python -O` strippea asserts; `raise` NO)"
    - "Sentinel `status_code=0` para errores detectados client-side (D-HIGY-8: sin nueva subclase)"
    - "Mirror exacto sync/async per CLAUDE.md (mismas 5 sustituciones byte-a-byte en client.py y aio.py)"
    - "Sección `# ------ Regressions ------` con docstring verbatim per D-HIGY-9"
key-files:
  created: []
  modified:
    - "packages/higyrus-client/src/higyrus_client/client.py — 5 sites de assert reemplazados (líneas finales: get_health ~205-220, get_movimientos ~243-254, get_posicion_valuada ~286-297, get_listado_cuentas ~322-333, get_posiciones ~353-364)"
    - "packages/higyrus-client/src/higyrus_client/aio.py — 5 sites espejo reemplazados (mismo patrón sync↔async)"
    - "packages/higyrus-client/src/higyrus_client/exceptions.py — docstring de HigyrusAPIError.status_code documenta sentinel 0 (D-HIGY-8)"
    - "packages/higyrus-client/tests/test_client.py — sección Regressions con 5 tests sync + import HigyrusAPIError"
    - "packages/higyrus-client/tests/test_async_client.py — sección Regressions con 5 tests async + import HigyrusAPIError"
decisions:
  - "D-HIGY-7 implementado verbatim: 10 sites reemplazados (5 client + 5 aio) con HigyrusAPIError(status_code=0, errors=[{'title':'shape mismatch','detail':f'expected {T}, got {type(raw).__name__}'}])"
  - "D-HIGY-8 implementado: docstring documenta el sentinel `status_code=0`; NO se agrega subclase HigyrusShapeError"
  - "D-HIGY-9 implementado: 10 regression tests (5 sync + 5 async) con docstring verbatim 'Regression: assert isinstance(raw, <T>) reemplazado por HigyrusAPIError tipado (finding F-NN).'"
metrics:
  duration: "4m 23s"
  tasks_completed: 4
  files_modified: 5
  files_created: 0
  commits: 4
  completed_date: "2026-06-06"
requirements: [HIGY-04]
---

# Phase 4 Plan 01: HIGY-04 Sync+Async Fix (assert isinstance → HigyrusAPIError) Summary

## One-liner

Reemplazo prophylactic de los 10 sites `assert isinstance(raw, list/dict)` en `higyrus_client.client` y `higyrus_client.aio` por `raise HigyrusAPIError(0, [{'title':'shape mismatch', ...}])` tipado, con documentación del sentinel `status_code=0` (D-HIGY-8) y 10 regression tests que lockean el comportamiento — cierra T-4-08 (T-4-08: `python -O` strippea asserts) y establece el contrato defensivo del fundamento del Phase 4 driver.

## Goal Met

Sí. Los 4 tasks del plan se ejecutaron en orden sin desviaciones; todos los acceptance criteria, las verificaciones whole-plan y la non-regression de repositorio completo pasan.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1.1 | Sync surface — replace 5 assert isinstance sites in client.py | `b286ce8` | `packages/higyrus-client/src/higyrus_client/client.py` |
| 1.2 | Async surface — replace 5 assert isinstance sites in aio.py | `be1d14b` | `packages/higyrus-client/src/higyrus_client/aio.py` |
| 1.3 | Document status_code=0 sentinel in HigyrusAPIError docstring | `dd1cad6` | `packages/higyrus-client/src/higyrus_client/exceptions.py` |
| 1.4 | Add Regressions section with 5+5 HIGY-04 tests | `b71a0a3` | `packages/higyrus-client/tests/test_client.py`, `packages/higyrus-client/tests/test_async_client.py` |

## Sync Fix (Task 1.1) — client.py

Los 5 sites originales (`assert isinstance(raw, list/dict)`) en `get_health`, `get_movimientos`, `get_posicion_valuada`, `get_listado_cuentas`, `get_posiciones` fueron reemplazados por bloques `if not isinstance(raw, T): raise HigyrusAPIError(status_code=0, errors=[{"title":"shape mismatch","detail": f"expected {T}, got {type(raw).__name__}"}])`. No se modificaron imports (HigyrusAPIError ya estaba importado), firmas públicas ni `_request`/`_ensure_token`/`login`. Grep final confirmado: `assert isinstance == 0`, `shape mismatch == 5`, `status_code=0 == 5`, `raise HigyrusAPIError == 5`.

## Async Mirror (Task 1.2) — aio.py

Espejo exacto de la sustitución sync: 5 sites en `get_health` (async), `get_movimientos`, `get_posicion_valuada`, `get_listado_cuentas`, `get_posiciones`. Los bloques `raise HigyrusAPIError(...)` son textualmente idénticos a los de client.py. No se modificaron `_token_lock`, `_client_lock`, `_ensure_http_client`, `aclose`. Grep final confirmado.

## Docstring Sentinel (Task 1.3) — exceptions.py

Modificación de UNA línea en el docstring de `HigyrusAPIError`:
- Antes: `status_code: HTTP status devuelto.`
- Después: `status_code: HTTP status devuelto, o 0 si el error fue detectado client-side (e.g., shape mismatch tras un 2xx exitoso).`

NO se agregó subclase `HigyrusShapeError` (D-HIGY-8 rechaza). NO se modificó la firma de `__init__` ni el resto de la jerarquía.

## Regression Tests (Task 1.4)

### Sync — test_client.py

Nueva sección `# ------ Regressions ------` al final con 5 tests:
- `test_get_health_raises_on_list_payload` — mock devuelve list, espera dict
- `test_get_movimientos_raises_on_dict_payload` — mock devuelve dict, espera list
- `test_get_listado_cuentas_raises_on_dict_payload` — mock devuelve dict, espera list
- `test_get_posicion_valuada_raises_on_dict_payload` — mock devuelve dict, espera list
- `test_get_posiciones_raises_on_dict_payload` — mock devuelve dict, espera list

Cada test usa el docstring verbatim per D-HIGY-9: `"""Regression: assert isinstance(raw, <T>) reemplazado por HigyrusAPIError tipado (finding F-NN)."""`. Verifica `exc_info.value.status_code == 0`, `exc_info.value.errors[0]["title"] == "shape mismatch"`, y `"expected ... got ..." in exc_info.value.errors[0]["detail"]`.

### Async — test_async_client.py

Espejo exacto: 5 tests `test_async_get_*_raises_on_*_payload` con firma `async def`, mismas aserciones. Import del barrel actualizado en ambos archivos: ahora incluye `HigyrusAPIError`.

### Signatures Notes

- `get_posicion_valuada` toma 5 positional args (`id_cuenta`, `tipo_cuenta`, `nivel`, `desde`, `hasta`), no kwargs como sugería el bosquejo del plan. Los tests pasan positionally: `get_posicion_valuada("CTA-001", "propia", "detalle", dt.date(...), dt.date(...))`. Sin desviación funcional — solo ajuste de invocación.
- `get_posiciones` toma 2 positional (`id_cuenta`, `fecha`). Tests pasan positionally igual.

## Verification Results

| Check | Expected | Actual |
|-------|----------|--------|
| `grep -c "assert isinstance" client.py` | 0 | 0 |
| `grep -c "shape mismatch" client.py` | 5 | 5 |
| `grep -c "status_code=0" client.py` | 5 | 5 |
| `grep -c "assert isinstance" aio.py` | 0 | 0 |
| `grep -c "shape mismatch" aio.py` | 5 | 5 |
| `grep -c "status_code=0" aio.py` | 5 | 5 |
| `grep -F "o 0 si el error fue detectado" exceptions.py` | match | match |
| Sync regression test count | 5 | 5 |
| Async regression test count | 5 | 5 |
| `uv run mypy packages/higyrus-client` | clean | Success: no issues found in 9 source files |
| `uv run ruff check .` | clean | All checks passed! |
| `uv run ruff format --check .` | clean | 68 files already formatted |
| `uv run pytest packages/higyrus-client -q` | ≥ 27 | 27 passed |
| `uv run pytest -q` (whole repo) | clean | 208 passed, 1 deselected |

## Deviations from Plan

Ninguna. Plan ejecutado exactamente como escrito.

Único ajuste menor (no es desviación): el bosquejo del plan en Task 1.4 sugería `get_posicion_valuada("CTA-001", tipo_cuenta="propia", ...)` pero la firma real es `def get_posicion_valuada(id_cuenta, tipo_cuenta, nivel, desde, hasta, *, ...)`, con los 5 args como positional. Los tests pasan los 5 positionally; el plan ya contemplaba este caso ("ajustar args si la firma actual difiere del bosquejo").

## Auth Gates

Ninguno. Plan totalmente mockeado; no se hicieron llamadas a APIs vivas.

## Threat Surface

- **T-4-08 (Tampering, mitigate):** Closed. `assert isinstance` reemplazado por `raise HigyrusAPIError(...)` en los 10 sites; el raise NO se strippea con `python -O`. Tests Regression con docstring `'Regression: assert isinstance(raw, <T>)...'` lockean el behavior y detectan cualquier reintroducción.
- **T-4-01 (Information Disclosure, accept):** El `errors[0]["detail"]` contiene solo el nombre del tipo Python (`list`, `dict`) — no PII, no valores del payload.
- **T-4-03 (Repudiation, accept):** Documentado en D-HIGY-7 que la jerarquía pública es `HigyrusClientError → HigyrusAPIError`; quien catcheaba `AssertionError` consumía implementation detail no contractual.

No se introdujeron nuevas superficies de amenaza. No hay flags adicionales que escalar.

## Known Stubs

Ninguno.

## Self-Check: PASSED

- `packages/higyrus-client/src/higyrus_client/client.py` modificado y commiteado en `b286ce8` (FOUND).
- `packages/higyrus-client/src/higyrus_client/aio.py` modificado y commiteado en `be1d14b` (FOUND).
- `packages/higyrus-client/src/higyrus_client/exceptions.py` modificado y commiteado en `dd1cad6` (FOUND).
- `packages/higyrus-client/tests/test_client.py` y `packages/higyrus-client/tests/test_async_client.py` modificados y commiteados en `b71a0a3` (FOUND).
- Los 4 commits visibles en `git log --oneline` de la rama `worktree-agent-a24aac0b1d1b77d16`.
- Plan duration: 4m 23s desde 2026-06-06T22:37:26Z hasta 2026-06-06T22:41:49Z.
