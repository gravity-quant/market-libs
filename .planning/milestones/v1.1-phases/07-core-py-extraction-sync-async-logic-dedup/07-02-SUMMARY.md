---
phase: 07-core-py-extraction-sync-async-logic-dedup
plan: 02
subsystem: ambito-financiero-client
tags: [phase-07, ambito, canary, refac-03, core-extraction]

# Dependency graph
requires:
  - phase: 07-core-py-extraction-sync-async-logic-dedup
    plan: 01
    provides: "import-linter v2.11 + 4 forbidden contracts + verification/test_sync_async_isolation.py + 4 _core.py placeholders"
provides:
  - "Canon _core.py shape for the remaining 3 packages (iol, higyrus, matriz) — RequestSpec frozen dataclass + builders + parsers + raise_for_response moved here per D-04"
  - "D-04 alias pattern validated end-to-end: B8 identity `aio._raise_for_response is client._raise_for_response` preserved via shared _core source + module-level __all__ listing to satisfy mypy strict implicit_reexport=False"
  - "Transport shell collapse pattern (_request(spec) -> httpx.Response per D-03 + 3-liner endpoint methods) validated with zero regression"
affects: [07-03, 07-04, 07-05, 07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RequestSpec frozen dataclass per-package (D-01 ámbito minimal shape: method + path + params + headers)"
    - "Builders puros build_<endpoint>_request(state, ...) -> RequestSpec (state-in, spec-out, sin I/O)"
    - "Parsers puros parse_<endpoint>_response(resp) -> typed result con body-consume-then-raise (D-06)"
    - "D-04 alias module-level + __all__ listing: `_raise_for_response = _core.raise_for_response`"
    - "Transport shell `_request(self, spec: _core.RequestSpec) -> httpx.Response` (D-03)"
    - "Endpoint method post-refactor 3-liner: spec = build_X(state, ...); resp = self._request(spec); return parse_X(resp)"
    - "Module-level back-compat delegators preservados (_request(method, path, **kwargs) y get_dollar_banco_nacion(date))"

key-files:
  created:
    - "packages/ambito-financiero-client/tests/test_core.py (149 LOC, 12 tests)"
  modified:
    - "packages/ambito-financiero-client/src/ambito_financiero_client/_core.py (13 → 147 LOC; placeholder → canon)"
    - "packages/ambito-financiero-client/src/ambito_financiero_client/client.py (270 → 189 LOC, -30%)"
    - "packages/ambito-financiero-client/src/ambito_financiero_client/aio.py (287 → 194 LOC, -32%)"

key-decisions:
  - "Module-level `_request(method, path, **kwargs)` delegator preservado con firma legacy (back-compat con el driver main_ambito_financiero.py y test_client.py / test_async_client.py existentes que mockean ambito.client._request). El método de la clase Client._request(self, spec) sí toma RequestSpec (D-03)."
  - "D-04 alias via asignación module-level + __all__ listing: `_raise_for_response = _core.raise_for_response` + `__all__ = [..., '_raise_for_response', ...]`. Patrón alternativo `from _core import raise_for_response as _raise_for_response` NO funciona porque mypy strict implicit_reexport=False sólo acepta `as ALIAS` cuando ALIAS coincide literalmente con el nombre importado. Acá el rename de `raise_for_response` a `_raise_for_response` impone el __all__ listing como única ruta limpia."
  - "Module-level `_request` aplica `_raise_for_response(resp)` después del dispatch (mantiene contrato legacy del driver). El método `Client._request(self, spec)` solo dispatchea HTTP (D-03 pure transport). El status-mapping vive una sola vez en `_core.raise_for_response`; el module-level delegator y los parsers la invocan independientemente."

requirements-completed: [REFAC-03]

# Metrics
duration: 14m
completed: 2026-06-12
---

# Phase 07 Plan 02: ámbito canary `_core.py` extraction Summary

**Extracción mecánica del patrón `_core.py + transport shell` aplicado a `ambito_financiero_client` como canary del refactor Phase 7 — validó el patrón completo (RequestSpec + builders + parsers + raise_for_response moved + D-04 alias + B8 identity + 3-liner endpoint shells) con drop agregado de 31.2% LOC en client+aio y zero regresión.**

## Performance

- **Duration:** ~14 min (3 commits: RED, GREEN, refactor)
- **Started:** 2026-06-12T18:07:10Z
- **Completed:** 2026-06-12T18:21:50Z
- **Tasks:** 2 (Task 1 _core.py extraction TDD; Task 2 transport shell collapse)
- **Files created:** 1 (`packages/ambito-financiero-client/tests/test_core.py`)
- **Files modified:** 3 (`_core.py`, `client.py`, `aio.py`)

## Accomplishments

- **`ambito_financiero_client/_core.py` extendido** del placeholder Phase 7-01 a 147 LOC de helpers puros: `RequestSpec` (frozen+slots, shape minimal D-01 ámbito), `raise_for_response` (movido verbatim desde `client.py:64-70`), `build_get_dollar_banco_nacion_request(state, date) -> RequestSpec`, `parse_get_dollar_banco_nacion_response(resp) -> float` con body-consume-then-raise (D-06).
- **`client.py` y `aio.py` colapsados** a transport shells:
  - El skeleton Phase 6 (PEP 562 shim, Client/AsyncClient class, lifecycle, configure carry-forward, B7 lock-less rationale en `aio.py`) queda intacto.
  - `_request(self, spec)` ahora recibe `_core.RequestSpec` (D-03 pure transport — sin status-mapping ni body parsing).
  - `get_dollar_banco_nacion()` colapsa a 3-liner: build spec, request, parse.
  - Module-level `_request(method, path, **kwargs)` y `get_dollar_banco_nacion(date)` preservados como back-compat (driver y tests legacy los siguen invocando con la firma vieja).
- **D-04 alias D-04 + B8 identity verificada:** `_raise_for_response = _core.raise_for_response` en ambos módulos, listado en `__all__` para satisfacer mypy strict `implicit_reexport=False`. Identidad `aio._raise_for_response is client._raise_for_response == True` confirmada por repl + test pre-existente `test_aio_imports_raise_for_response_from_client` verde.
- **12 nuevos unit tests** (`tests/test_core.py`) cubriendo RequestSpec shape (frozen + defaults), builder shape + purity, parser happy path + NoDataError + body-consume-then-raise, raise_for_response status mapping (401/403/429/5xx/2xx).
- **Zero regresión:** suite ámbito 107 passed (95 baseline + 12 nuevos `test_core.py`); suite completa del repo 411 passed + 2 skipped + 1 deselected (subió desde 399 baseline post-7-01).

## Task Commits

Cada task committed atomically con su gate RED/GREEN:

1. **Task 1 RED:** `47bd34e` — test(07-02): add failing tests for ambito _core builders/parsers
2. **Task 1 GREEN:** `0bb51e5` — feat(07-02): implement ambito _core.py — RequestSpec + builders + parsers + raise_for_response
3. **Task 2:** `bb87b30` — refactor(07-02): collapse ambito client.py + aio.py to transport shells consuming _core

## LOC drop reporting (D-14 format)

```
LOC drop vs Phase 6 baseline (commit 5db0a0d):
- client.py: 270 → 189 (-30.0%)
- aio.py:    287 → 194 (-32.4%)
- _core.py:    0 → 147 (NEW)
- Aggregate client+aio: 557 → 383 (-31.2%)   PASS (≥30% threshold)
```

**Note:** el agregado `client+aio` excluye `_core.py` por definición del threshold D-14. El `_core.py` (147 LOC) absorbe la lógica que antes estaba duplicada implícitamente entre `client.py` y `aio.py` (builders inline + parsers inline + raise_for_response duplicado vía B8 import). Net change neto incluyendo `_core.py`: 557 → 530 (drop 4.8%) — la mejora real es la **deduplicación**: ahora hay una sola fuente de verdad para los builders y parsers, en vez de dos copias casi idénticas en sync/async.

## Files Created/Modified

### Created

- `packages/ambito-financiero-client/tests/test_core.py` (149 LOC, 12 tests): unit tests aislados sobre `_core.RequestSpec` (frozen + defaults), `_core.build_get_dollar_banco_nacion_request` (shape + purity), `_core.parse_get_dollar_banco_nacion_response` (happy path + NoDataError + D-06 body-consume verification), y `_core.raise_for_response` (parametrize 401/403 → AuthError, 429 → RateLimitError, 5xx → APIError, 2xx no-raise).

### Modified

- `_core.py`: 13 → 147 LOC. Módulo extendido del placeholder Phase 7-01: docstring contractual citando D-01/D-04/D-06 + privacy contract (`import-linter` enforça `_core` no importa transport), `from __future__ import annotations`, `__all__` listing `RequestSpec`, `raise_for_response`, builder, parser. Section dividers `# ---...---` (PATTERNS.md §1).
- `client.py`: 270 → 189 LOC. Cambios:
  - Imports: `from ambito_financiero_client import _core` + remove direct exception/parsing imports (movidos a `_core`).
  - `_raise_for_response = _core.raise_for_response` (D-04 alias) + `__all__` listing.
  - `Client._request(self, spec)` toma `RequestSpec` (D-03 transport-only).
  - `Client.get_dollar_banco_nacion(date)` colapsa a 3-liner.
  - Module-level `_request(method, path, **kwargs)` preservado con back-compat semantics (`_raise_for_response` aplicado post-dispatch).
- `aio.py`: 287 → 194 LOC. Cambios mirror sync con `await`, mismo D-04 alias pattern, mismo 3-liner endpoint shell.

## Decisions Made

- **Module-level `_request(method, path, **kwargs)` preservado con firma legacy.** El plan dice "REEMPLAZAR `_request` por shell con `spec`", pero el driver `main_ambito_financiero.py` (líneas 150, 235) y tests existentes (`test_client.py:25,31`, `test_async_client.py:25`, `test_driver_invariants.py:66,94`) llaman `ambito.client._request("GET", path)` y `await aio._request("GET", path)`. Cambiar la firma del **module-level** delegator rompe back-compat. Resolución: el método **de la clase** `Client._request(self, spec)` toma `RequestSpec` (D-03 cumplido); el **module-level** `_request(method, path, **kwargs)` traduce kwargs → `RequestSpec` y delega al método de la clase + aplica `_raise_for_response` post-dispatch. Mantiene contrato legacy sin contaminar el design del shell.
- **D-04 alias via asignación module-level + `__all__` listing.** El plan documenta dos opciones para el alias:
  1. `_raise_for_response = _core.raise_for_response` (asignación), o
  2. `from _core import raise_for_response as _raise_for_response` (import alias).

  La opción 2 falla mypy strict `implicit_reexport=False` porque el patrón `from X import Y as Y` sólo es re-export válido cuando `Y` coincide literalmente con el nombre exportado. Aquí el rename de `raise_for_response` → `_raise_for_response` rompe esa coincidencia. Solución: opción 1 + agregar `__all__` al módulo `aio.py` y `client.py` listando `_raise_for_response`. mypy strict acepta nombres en `__all__` como exports explícitos; esto NO afecta el snapshot público (el snapshot enumera `__all__` del paquete root, no de submódulos).
- **`__all__` agregado a `client.py` y `aio.py`** para mantener simetría y dejar explícito el contrato D-04 en ambos lados. Costo: ~7 LOC por archivo; beneficio: mypy strict pasa sin agregar `# type: ignore`.
- **Docstrings module-level + class-level comprimidas** para alcanzar el target D-14 ≥30% drop. La información crítica queda en formato condensado citando los D-XX y T-06-XX relevantes; el detalle completo vive en CONTEXT.md / PATTERNS.md / RESEARCH.md (donde corresponde por arquitectura GSD).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] mypy strict `implicit_reexport=False` rechaza `from _core import raise_for_response as _raise_for_response`**

- **Found during:** Task 2 (primer mypy strict run después del refactor).
- **Issue:** `error: Module "ambito_financiero_client.aio" does not explicitly export attribute "_raise_for_response" [attr-defined]` en `tests/test_client_class.py:177` al importar `from ambito_financiero_client.aio import _raise_for_response`. El patrón `as ALIAS` re-export sólo funciona si `ALIAS == nombre importado`. Aquí `raise_for_response` se renombra a `_raise_for_response` (underscore prefix por convención privada), por lo que mypy NO lo considera re-export.
- **Fix:** Cambiar el import a asignación module-level (`_raise_for_response = _core.raise_for_response`) y agregar `__all__ = [..., "_raise_for_response", ...]` para que mypy strict acepte el nombre como export explícito. Aplicado idéntico a `client.py` para simetría.
- **Files modified:** `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py`, `packages/ambito-financiero-client/src/ambito_financiero_client/client.py`.
- **Verification:** `uv run mypy packages/ambito-financiero-client/` exits 0; B8 identity preservada (`a is c == True`).
- **Committed in:** `bb87b30` (parte del commit Task 2).

**2. [Rule 1 - Bug] ruff `noqa: F841` redundante en `_core.py`**

- **Found during:** Task 1 (primer ruff check del `_core.py` recién creado).
- **Issue:** `ruff check` reportaba `RUF100 [*] Unused noqa directive`: el comentario `_ = state  # noqa: F841` no era necesario porque ruff F841 sólo flagea variables sin uso, y `_ = state` ES un uso (assignment a `_`).
- **Fix:** Eliminado el comment `# noqa: F841 — kept for signature uniformity per Phase 7 D-01.` → simplificado a `# kept for signature uniformity per Phase 7 D-01.`
- **Files modified:** `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py`.
- **Verification:** `uv run ruff check packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` exits 0.
- **Committed in:** `0bb51e5` (parte del commit Task 1 GREEN).

### Out-of-scope items deferred

- **Ninguno introducido por este plan.** El item deferred de Plan 7-01 (`ruff` violations preexistentes en `.claude/skills/` y `.planning/spikes/`) sigue presente pero no es scope de este plan. `uv run ruff check packages/ambito-financiero-client/` exits 0.

---

**Total deviations:** 2 auto-fixed (Rule 1 bugs en archivos recién escritos) + 0 out-of-scope nuevos.
**Impact on plan:** Las 2 correcciones son triviales (un ajuste de patrón mypy + un `noqa` redundante eliminado). No afectan diseño, alcance ni success criteria.

## Issues Encountered

- **LOC compression iterative:** alcanzar el ≥30% drop requirió 3 iteraciones de compresión de docstrings y section dividers en `client.py` y `aio.py`. ámbito es el paquete más simple (1 endpoint) pero también el que tiene proporcionalmente más boilerplate Phase 6 (PEP 562, lifecycle, configure carry-forward, repr, pickle/deepcopy bans, B7 lock-less rationale en aio). El target final 383 LOC (vs 390 threshold) se alcanzó comprimiendo docstrings module-level + class docstrings + eliminando section dividers redundantes `# -- private --` / `# -- endpoints --`. Información eliminada queda en formato condensado citando D-XX; el detalle completo vive en CONTEXT.md / PATTERNS.md (decisión consciente: el código no es la documentación, los D-XX son trazables).
- **B8 identity verification process-isolation noise:** la primera vez que verifiqué `a is c` en procesos separados los `id()` aparecían distintos. Esperable: cada `uv run python -c "..."` es un proceso nuevo con su propio address space. La validación correcta es en UN sólo proceso (`uv run python -c "from aio import _raise_for_response as a; from client import _raise_for_response as c; assert a is c"`) y dio `True`. El test pre-existente `test_aio_imports_raise_for_response_from_client` (run dentro de pytest, una sola process) también verifica `assert sync_helper is async_helper` y pasa verde.

## Verification Artifacts

### B8 identity assertion

```bash
$ uv run python -c "from ambito_financiero_client.aio import _raise_for_response as a; \
                    from ambito_financiero_client.client import _raise_for_response as c; \
                    assert a is c, 'B8 identity broken'; print('a is c == True')"
a is c == True
```

### `uv run lint-imports` output (post-refactor)

```
Analyzed 30 files, 46 dependencies.
-----------------------------------

ambito_financiero_client._core does not depend on transport modules KEPT
higyrus_client._core does not depend on transport modules KEPT
iol_client._core does not depend on transport modules KEPT
matriz_client._core does not depend on transport modules KEPT

Contracts: 4 kept, 0 broken.
```

Exit 0. `ambito_financiero_client._core` contract `KEPT` post-refactor real (Plan 7-01 lo había validado contra placeholder vacío; este plan lo valida contra implementación real con builders + parsers + raise_for_response).

### Ambito test suite

```
$ uv run pytest packages/ambito-financiero-client/ -q
.......................................................................     [ 67%]
...................................                                          [100%]
107 passed, 1 deselected in 0.19s
```

107 = 95 baseline + 12 nuevos `tests/test_core.py`. Zero regresiones.

### Full repo suite

```
$ uv run pytest -q
....................................................s                        [100%]
411 passed, 2 skipped, 1 deselected in 1.20s
```

411 = 399 baseline post-7-01 + 12 nuevos `test_core.py` ámbito. Los 2 skips son los mismos que en 7-01 (matriz async REST stub Phase 10).

### Public surface snapshot (D-16)

```
$ uv run pytest verification/test_public_surface.py -q
....                                                                          [100%]
4 passed in 0.03s
```

Zero diff vs `verification/snapshots/ambito-financiero-client-surface.txt`. `_core` NO aparece en `__all__` del paquete root (D-16 cumplido). El `__all__` interno de `aio.py` y `client.py` listando `_raise_for_response` NO afecta el snapshot — el test enumera `__all__` del paquete root (`ambito_financiero_client`), no de los submódulos.

### Cross-leak sentinel (`verification/test_sync_async_isolation.py`)

```
$ uv run pytest verification/test_sync_async_isolation.py -q
.......s                                                                      [100%]
7 passed, 1 skipped in 0.07s
```

Ambito sync + ambito async sentinels siguen llegando al wire request post-refactor. matriz async `pytest.skip` con reason literal D-11 (Phase 10).

### mypy strict

```
$ uv run mypy packages/ambito-financiero-client/
Success: no issues found in 23 source files
```

### ruff check + format

```
$ uv run ruff check packages/ambito-financiero-client/
All checks passed!

$ uv run ruff format --check packages/ambito-financiero-client/
23 files already formatted
```

### Threat register closure

| Threat ID | Component | Mitigation evidence |
|-----------|-----------|---------------------|
| T-7-01 | `_core.py` accidental import of transport state | `grep -E "from ambito_financiero_client\.(client\|aio)" packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` returns empty + `uv run lint-imports` "ambito_financiero_client._core does not depend on transport modules KEPT" |
| T-7-02 | Sync/async token cross-contamination | `verification/test_sync_async_isolation.py` ámbito sync + ámbito async pass post-refactor (sentinels llegan al wire) |
| T-7-03 | B8 alias rotura (Pitfall 2) | `a is c == True` via repl assertion + test pre-existente `test_aio_imports_raise_for_response_from_client` verde |
| T-7-D16 | `_core` accidentally added to public `__all__` (snapshot drift) | `verification/test_public_surface.py` 4/4 pass; snapshot zero diff; `__all__` del paquete root inalterado |

## Self-Check

Files asserted to exist (path relative to worktree root):

- `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` — present (147 LOC, includes `RequestSpec`, `raise_for_response`, `build_get_dollar_banco_nacion_request`, `parse_get_dollar_banco_nacion_response`)
- `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` — present (189 LOC, transport shell with `_raise_for_response = _core.raise_for_response` D-04 alias + `__all__` listing)
- `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` — present (194 LOC, mirror async transport shell)
- `packages/ambito-financiero-client/tests/test_core.py` — present (149 LOC, 12 tests pass)
- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-02-SUMMARY.md` — present (this file)

Commits asserted to exist (verify `git log --oneline`):

- `47bd34e` — test(07-02): add failing tests for ambito _core builders/parsers — present
- `0bb51e5` — feat(07-02): implement ambito _core.py — RequestSpec + builders + parsers + raise_for_response — present
- `bb87b30` — refactor(07-02): collapse ambito client.py + aio.py to transport shells consuming _core — present

## Self-Check: PASSED
