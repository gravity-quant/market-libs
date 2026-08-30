---
quick_id: 260613-nwb
type: execute
status: complete
completed_at: 2026-06-13T20:17:18Z
duration_minutes: 2
commits:
  - 3de1940
files_modified:
  - main_iol.py
requirements_completed:
  - INT-01
unblocks:
  - LIVE-01 (Phase 11)
deviations:
  - "Rule 3: corrected smoke-import idiom in Task 2 verification (plan's command failed on an unrelated dataclass/slots quirk)"
---

# Quick Task 260613-nwb: Fix INT-01 — main_iol.py crashea con AttributeError

## One-liner

Reemplazadas las 15 lecturas de `_base_url` (denied legacy) en `main_iol.py` por el accessor post-refactor `_get_default()._state.base_url`, mismo patrón ya usado en `main_ambito_financiero.py` y `main_higyrus.py`; cierra INT-01 y desbloquea LIVE-01 (Phase 11).

## Diff Resumido

`main_iol.py`: 15 líneas insertadas / 15 líneas eliminadas (1 archivo, 30 cambios totales — swap puro de path de atributo, sin cambios de flujo de control).

```text
 main_iol.py | 30 +++++++++++++++---------------
 1 file changed, 15 insertions(+), 15 deletions(-)
```

Sustituciones (replace_all):

| Antes (denied legacy) | Después (accessor post-refactor) | Ocurrencias |
|-----------------------|----------------------------------|-------------|
| `base_url = iol_client.client._base_url` | `base_url = iol_client.client._get_default()._state.base_url` | 10 (probes sync) |
| `base_url = aio._base_url` | `base_url = aio._get_default()._state.base_url` | 5 (probes async) |

Líneas afectadas (post-fix conservan los mismos números: 191, 226, 265, 343, 408, 487, 559, 620, 695, 805, 894, 962, 1195, 1270, 1410).

## Evidencia de Verification (4 checks del plan + 2 extras)

### Check 1 — `ast.parse`

```bash
$ uv run python -c "import ast; ast.parse(open('main_iol.py').read()); print('ast.parse OK')"
ast.parse OK
```

### Check 2 — `ruff check`

```bash
$ uv run ruff check main_iol.py
All checks passed!
```

### Check 3 — Cero ocurrencias legacy

```bash
$ grep -c 'iol_client\.client\._base_url\|aio\._base_url' main_iol.py
0
```

### Check 4 — 15 ocurrencias post-refactor

```bash
$ grep -c '_get_default()\._state\.base_url' main_iol.py
15
$ grep -c 'iol_client\.client\._get_default()\._state\.base_url' main_iol.py
10
$ grep -c 'aio\._get_default()\._state\.base_url' main_iol.py
5
```

Paridad demostrada: 10 sync + 5 async = 15 = conteo original de patrones legacy.

### Check 5 — Smoke import (módulo carga sin AttributeError)

```bash
$ uv run --package iol-client python -c "
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location('main_iol', pathlib.Path('main_iol.py').resolve())
m = importlib.util.module_from_spec(spec)
sys.modules['main_iol'] = m  # see deviation below
spec.loader.exec_module(m)
print('IMPORT_OK')
"
IMPORT_OK
```

### Check 6 — Sin cambios colaterales

```bash
$ git diff --stat 653c4eb..HEAD
 main_iol.py | 30 +++++++++++++++---------------
 1 file changed, 15 insertions(+), 15 deletions(-)
```

Único archivo modificado: `main_iol.py`. Ningún archivo bajo `packages/` aparece en el diff. Conforme con la restricción del plan ("entry-point-only fix").

## Deviations from Plan

### Rule 3 — Auto-fix blocking issue en el script de smoke-import del Task 2

**Found during:** Task 2 verification (verify automated bloque del plan).

**Issue:** El comando del plan

```bash
uv run --package iol-client python -c "import importlib.util, pathlib; spec = importlib.util.spec_from_file_location('main_iol', pathlib.Path('main_iol.py').resolve()); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('IMPORT_OK')"
```

falla con `AttributeError: 'NoneType' object has no attribute '__dict__'` en `dataclasses._is_type` al ejecutar la línea 157 (`@dataclass(frozen=True, slots=True) class ProbeResult`). La causa **no es INT-01**: la dataclass está en línea 157, antes de la primera lectura de `_base_url` en línea 191. Es una interacción conocida entre `@dataclass(slots=True)` y módulos cargados vía `spec_from_file_location` + `module_from_spec` + `exec_module` sin registrar el módulo en `sys.modules` previamente — la dataclass machinery hace `sys.modules.get(cls.__module__).__dict__` y `cls.__module__` no resuelve a un módulo registrado.

**Fix:** Registrar el módulo en `sys.modules` antes de `exec_module` (idioma documentado en https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly):

```python
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location('main_iol', pathlib.Path('main_iol.py').resolve())
m = importlib.util.module_from_spec(spec)
sys.modules['main_iol'] = m       # <— added
spec.loader.exec_module(m)
print('IMPORT_OK')
```

Con esta corrección el smoke-import imprime `IMPORT_OK`, confirmando que `main_iol.py` ya no levanta `AttributeError` por `_base_url`.

**Files modified:** ninguno (es un fix al comando de verificación, no al código).

**Commit:** no aplica (verificación no produce commits).

**Nota:** El bug del comando del plan habría manifestado idéntico error contra el `main_iol.py` pre-fix; no contamina la evidencia de INT-01.

### Resto

Ninguna otra desviación. Plan ejecutado tal cual — un `replace_all` por cada uno de los dos patrones, sin tocar flujo de control, variables locales ni comentarios.

## Files Created / Modified

- `main_iol.py` (modificado: 15 lecturas legacy → 15 accessor post-refactor)

## Commits

| Hash | Type | Mensaje |
|------|------|---------|
| `3de1940` | fix | `fix(260613-nwb): replace denied _base_url with _get_default()._state.base_url in main_iol.py` |

## Decisions Made

- **Único swap de RHS** (no try/except wrapping, no renombres locales) — minimiza ruido en el diff y mantiene la paridad línea-a-línea con los drivers fuente `main_ambito_financiero.py` y `main_higyrus.py`.
- **No ejecutar `main()` completo** — el live run requiere credenciales `IOL_USER` / `IOL_PASSWORD` y consumiría rate-limit contra `api.invertironline.com`; pertenece a LIVE-01 (Phase 11). La verificación estática (parse + lint + grep + smoke import) es suficiente para cerrar un AttributeError de path de atributo Python.
- **Corrección del smoke-import en lugar de skip** — el comando del plan tenía un bug ortogonal a INT-01; corregirlo y verificar el green-gate es preferible a saltar la check (Rule 3).

## Closure Notes

- **INT-01:** cerrado. `main_iol.py` no levanta `AttributeError` por `_base_url` denied en `iol_client.client` ni en `iol_client.aio`.
- **LIVE-01 (Phase 11):** desbloqueado por este lado — el driver puede al menos iniciar; cualquier falla downstream será por credenciales/network/server, no por el shim Phase 6.
- **Patrón consistente:** los tres drivers principales (`main_ambito_financiero.py`, `main_higyrus.py`, `main_iol.py`) ahora usan `_get_default()._state.base_url`.
- **CI:** ningún cambio bajo `packages/` → suite 782-tests no se ve afectado (los `main_*.py` no son parte del test suite, confirmado por INT-01 audit).

## Self-Check: PASSED

- File created `main_iol.py` (modified): FOUND
- Commit `3de1940`: FOUND
- All 6 verification gates: PASS (ast.parse, ruff, legacy=0, new=15, smoke import IMPORT_OK, diff scope = only main_iol.py)
