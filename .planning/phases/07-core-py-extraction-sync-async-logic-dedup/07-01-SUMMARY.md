---
phase: 07-core-py-extraction-sync-async-logic-dedup
plan: 01
subsystem: testing-infra
tags: [phase-07, import-linter, ci-gate, cross-leak, REFAC-03]

# Dependency graph
requires:
  - phase: 06-compat-safety-net-client-class-skeleton
    provides: "393 tests baseline + Phase 6 D-12 sentinel naming (SYNC-/ASYNC-sentinel-<pkg>) + _state.py module shape"
provides:
  - "import-linter v2.11 instalado + 4 forbidden contracts en pyproject.toml `[tool.importlinter]`"
  - "4 `_core.py` placeholders (ambito, iol, higyrus, matriz) — base sobre la que Plans 7-02..7-06 construyen RequestSpec / builders / parsers / auth-flow primitives"
  - "verification/test_sync_async_isolation.py — cross-leak runtime guard parametrizado sobre 4 paquetes"
  - "CI step `uv run lint-imports` en `.github/workflows/ci.yml` job `lint`"
affects: [07-02, 07-03, 07-04, 07-05, 07-06, 10-matriz-async]

# Tech tracking
tech-stack:
  added: ["import-linter>=2.11,<3", "grimp", "click", "rich", "markdown-it-py", "mdurl"]
  patterns:
    - "Declarative import boundary enforcement vía [tool.importlinter] forbidden contracts"
    - "Cross-leak sentinel test parametrizado: _PACKAGES list of (pkg_name, header_name | None, value_prefix)"
    - "Per-package _configure_sync/_configure_async helper para centralizar kwargs específicos de cada configure()"

key-files:
  created:
    - "packages/ambito-financiero-client/src/ambito_financiero_client/_core.py (placeholder, 13 LOC)"
    - "packages/iol-client/src/iol_client/_core.py (placeholder, 13 LOC)"
    - "packages/higyrus-client/src/higyrus_client/_core.py (placeholder, 13 LOC)"
    - "packages/matriz-client/src/matriz_client/_core.py (placeholder, 14 LOC)"
    - "verification/test_sync_async_isolation.py (208 LOC, 7 passed + 1 skipped)"
  modified:
    - "pyproject.toml (+43 lines: dev dep + [tool.importlinter] block + 4 contracts)"
    - "uv.lock (+132 lines: import-linter 2.11 transitively)"
    - ".github/workflows/ci.yml (+2 lines: new step in `lint` job)"

key-decisions:
  - "D-09 (Phase 7): `import-linter` declarativo con 4 `forbidden` contracts vía `[tool.importlinter]` en pyproject.toml raíz (no .importlinter file separado, por consistencia con [tool.ruff]/[tool.mypy]/[tool.pytest])"
  - "D-12 (Phase 7): Plan 7-01 NO bloquea Plans 7-02..7-06 — los contracts pasan vacíos contra placeholders (verificado: '4 kept, 0 broken' exit 0)"
  - "Pitfall 6 mitigation: contracts contra módulo inexistente reportan WARN silente — los 4 `_core.py` placeholder evitan ese estado fantasma"
  - "D-11 (Phase 7): matriz async pytest.skip con reason literal 'matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore' (no falla, no se elimina; sirve de recordatorio visible en CI output)"

patterns-established:
  - "Pattern: `_core.py` placeholder shape — module docstring (citando REFAC-03 + D-01/D-04 + import-linter contract) + `from __future__ import annotations` + `__all__: list[str] = []` para que Plans 7-02..7-06 lo pueblen incremental"
  - "Pattern: Cross-leak sentinel parametrize — _PACKAGES list[tuple[pkg_name, header_name|None, value_prefix]] consumida por dos tests (sync + async), con per-package helpers `_configure_sync` / `_configure_async` que conocen el contrato de configure() de cada paquete"
  - "Pattern: case-insensitive URL hostname assertion — `assert sentinel.lower() in str(req.url).lower()` (httpx lowercasea hostnames per RFC 3986)"

requirements-completed: [REFAC-03]

# Metrics
duration: 31m
completed: 2026-06-12
---

# Phase 07 Plan 01: CI Gates Infrastructure (import-linter + cross-leak guard) Summary

**Instalación + configuración de `import-linter` v2.11 con 4 forbidden contracts declarativos + 4 `_core.py` placeholders + runtime cross-leak guard parametrizado — las dos CI gates de Phase 7 (REFAC-03) quedan operativas antes del primer refactor.**

## Performance

- **Duration:** ~31 min (operator-clock; includes checkpoint dwell time)
- **Started:** 2026-06-12T17:28:05Z (PLAN_START_TIME del agente anterior)
- **Completed:** 2026-06-12T17:58:47Z
- **Tasks:** 3 (Task 1 = blocking human-verify checkpoint, "approved" por operator; Tasks 2 + 3 = code work)
- **Files created:** 5 (4 `_core.py` placeholders + 1 cross-leak test)
- **Files modified:** 3 (pyproject.toml, uv.lock, .github/workflows/ci.yml)

## Accomplishments

- **import-linter v2.11 instalado** y configurado declarativamente en `pyproject.toml` con 4 forbidden contracts (uno por paquete cliente). `uv run lint-imports` exits 0 con "Contracts: 4 kept, 0 broken" (output literal — confirma Pitfall 6 cleared).
- **4 `_core.py` placeholder seeded** (`ambito_financiero_client`, `iol_client`, `higyrus_client`, `matriz_client`) — base sobre la que Plans 7-02..7-06 extienden RequestSpec / builders / parsers / auth-flow primitives sin romper la gate (D-12).
- **`verification/test_sync_async_isolation.py`** parametrizado sobre 4 paquetes — 7 passed + 1 skipped (matriz async, D-11 reason literal). Es el detector runtime que complementa los contracts declarativos contra bypass por importlib dinámico.
- **CI gate `uv run lint-imports`** agregado al job `lint` del workflow (`.github/workflows/ci.yml`) — boundary enforcement empujado a CI, no a un manual check del developer.
- **393 baseline tests** preserved (Pitfall 4 / A5): suite final 399 passed + 2 skipped + 1 deselected = **402 collected** (393 + 9 nuevos). Zero regressions; ruff/mypy/format pasan en el scope del plan.

## Task Commits

Each task was committed atomically:

1. **Task 1: Blocking human-verify checkpoint** — NO commit (gate). Operator confirmó "approved": `import-linter 2.11+` verificado en PyPI (`https://pypi.org/project/import-linter/`) + GitHub (`seddonym/import-linter`, repo público, LICENSE Apache-2.0, releases desde 2017). T-7-SC mitigated.
2. **Task 2: Add import-linter to dev deps + 4 forbidden contracts + 4 `_core.py` placeholders** — `c53e0eb` (feat)
3. **Task 3: Cross-leak sentinel test + CI step `lint-imports`** — `685c5dc` (test)

## Files Created/Modified

### Created

- `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` — placeholder (docstring + `from __future__ import annotations` + `__all__: list[str] = []`)
- `packages/iol-client/src/iol_client/_core.py` — placeholder (same shape)
- `packages/higyrus-client/src/higyrus_client/_core.py` — placeholder (same shape)
- `packages/matriz-client/src/matriz_client/_core.py` — placeholder (docstring menciona Phase 10 REFAC-04 conexión futura)
- `verification/test_sync_async_isolation.py` — 208 LOC. Module docstring + `_PACKAGES` constant + `_configure_sync`/`_configure_async` helpers + 2 funciones `@pytest.mark.parametrize` (1 sync, 1 async). D-11 reason literal en `pytest.skip` para matriz async.

### Modified

- `pyproject.toml` — `import-linter>=2.11,<3` en `[dependency-groups] dev` + `[tool.importlinter]` block con `root_packages` (4 paquetes) y 4 `[[tool.importlinter.contracts]]` forbidden (cada uno `source_modules = ["<pkg>._core"]`, `forbidden_modules = ["<pkg>.client", "<pkg>.aio"]`).
- `uv.lock` — regenerado con `uv lock`; +6 paquetes resueltos (`import-linter==2.11`, `grimp==3.14`, `click==8.4.1`, `markdown-it-py==4.2.0`, `mdurl==0.1.2`, `rich==15.0.0`).
- `.github/workflows/ci.yml` — nuevo step en el job `lint` (después de `ruff format --check`):
  ```yaml
  - name: import-linter (boundary enforcement, Phase 7 REFAC-03)
    run: uv run lint-imports
  ```

## Decisions Made

- **Helper functions sobre dict-of-callables**: en lugar de un `_PACKAGES` que cargue lambdas/callables por paquete (más rígido, peor lectura), elegí `_configure_sync(pkg, pkg_name, sentinel)` y `_configure_async(aio, pkg_name, sentinel)` que centralizan los kwargs específicos por paquete (ambito `base_url=...`, iol `base_url+username+password+token+token_expires_at`, higyrus `+client_id`, matriz `username=test-user/password=test-pass`). El cuerpo del test queda focalizado en disparar el request + assertar el wire.
- **D-11 reason en código solamente**: la reason literal `"matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"` aparece sólo en `pytest.skip(...)` (línea 176). Originalmente quedaba duplicada en el docstring del módulo pero eso violaba el acceptance criterion `grep -c 'pytest.skip' verification/test_sync_async_isolation.py == 1` — la docstring ahora dice "se skipea con reason literal (D-11)" en prosa.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] httpx (RFC 3986) lowercases hostnames; sentinel literal NO aparece raw en `str(req.url)` para ámbito**

- **Found during:** Task 3 (primera ejecución del test)
- **Issue:** El test ámbito (`assert f"{sentinel}.test" in str(req.url)`) fallaba con `AssertionError: assert 'SYNC-sentinel-ambito_financiero_client.test' in 'https://sync-sentinel-ambito_financiero_client.test/...'`. httpx (per RFC 3986: hostnames son case-insensitive) lowercasea el hostname al construir la URL, así que el sentinel literal `SYNC-sentinel-...` se transforma en `sync-sentinel-...`.
- **Fix:** Cambiar el assertion a case-insensitive comparison: `assert f"{sentinel}.test".lower() in str(req.url).lower()`. Aplicado tanto a `test_sync_token_isolation_in_wire_request` como a `test_async_token_isolation_in_wire_request`.
- **Files modified:** `verification/test_sync_async_isolation.py` (líneas ámbito sync + ámbito async)
- **Verification:** Suite del test pasa: 7 passed + 1 skipped.
- **Committed in:** `685c5dc` (parte del commit Task 3)

**2. [Rule 1 - Bug] Unused `# type: ignore[attr-defined]` en `aio = pkg.aio`**

- **Found during:** Task 3 (mypy strict run)
- **Issue:** `mypy verification/test_sync_async_isolation.py` reportaba `error: Unused "type: ignore" comment [unused-ignore]` en la línea `aio = pkg.aio  # type: ignore[attr-defined]`. Mypy moderno (1.13+) resuelve `pkg.aio` como `Any` (porque `importlib.import_module` devuelve `Any`), así que el ignore es redundante.
- **Fix:** Eliminado el comment `# type: ignore[attr-defined]`.
- **Files modified:** `verification/test_sync_async_isolation.py` línea ~179
- **Verification:** `uv run mypy verification/test_sync_async_isolation.py` exits 0.
- **Committed in:** `685c5dc`

### Out-of-scope items deferred

- **Ruff/format violations pre-existentes en `.claude/skills/` y `.planning/spikes/`**: `uv run ruff check .` reporta 108 errores y `uv run ruff format --check .` reporta 22 archivos. **Todos** son en spike artifacts copiados a skill sources (NOT touched by Plan 7-01). Pre-existen en `main` (verificado: 54 errores ya estaban antes). Loggeados en `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/deferred-items.md` con recomendación de seguimiento (exclude spike paths from ruff scope o cleanup en quick task separado). `uv run ruff check packages/` y `uv run ruff check verification/test_sync_async_isolation.py` pasan clean — el plan no introduce ningún error de ruff en su scope.

---

**Total deviations:** 2 auto-fixed (2 × Rule 1 bugs en el test recién creado) + 1 out-of-scope deferred
**Impact on plan:** Los dos auto-fixes son fixes triviales del test recién escrito — no afectan diseño ni alcance. El item deferred es pre-existente del repo y fuera del file_modified del plan.

## Issues Encountered

- **Worktree no tenía los planning artifacts de Phase 7**: el worktree branch `worktree-agent-a0663ef68432dcc5b` fue creado desde un commit anterior a la escritura de `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/` en main. Solución: `git checkout main -- .planning/phases/07-core-py-extraction-sync-async-logic-dedup/` + `git reset HEAD ...` para tener los archivos en el working tree del worktree (untracked) y leerlos. NO se committearon en el branch del worktree (corresponden al orquestador).
- **Worktree no tenía workspace sincronizado**: `uv run pytest --collect-only -q` inicialmente devolvía `ModuleNotFoundError: No module named 'iol_c...'`. Solución: `uv sync --all-packages --all-extras --dev` (resuelto en segundos, no requirió re-sync más adelante).
- **393 baseline confirmado** (Pitfall 4 / A5): `uv run pytest --collect-only -q` → `393/394 tests collected (1 deselected) in 0.34s`. Post-Plan: 402 collected (399 passed + 2 skipped + 1 deselected). Delta neto: +9 tests, sin regresiones.

## Verification Artifacts

### import-linter version

```
Name: import-linter
Version: 2.11
Required-by: (none — dev tool, not packaged)
```

### `uv run lint-imports` literal output

```
Analyzed 30 files, 46 dependencies.
-----------------------------------

ambito_financiero_client._core does not depend on transport modules KEPT
higyrus_client._core does not depend on transport modules KEPT
iol_client._core does not depend on transport modules KEPT
matriz_client._core does not depend on transport modules KEPT

Contracts: 4 kept, 0 broken.
```

Exit 0. **A2 / Pitfall 6 / Open Q #4 cleared**: los 4 contracts pasan KEPT contra placeholders (no WARN silente "Could not find package").

### `uv run pytest --collect-only -q` baseline (pre-plan observado)

```
393/394 tests collected (1 deselected) in 0.34s
```

### `uv run pytest -q` final (post-plan)

```
399 passed, 2 skipped, 1 deselected in 1.07s
```

402 collected total = 393 baseline + 9 nuevos (4 sync + 3 async pass + 1 sync matriz que ya existía siendo + 1 async matriz skipped). Coverage de las 4 superficies con sentinel runtime detection.

### Threat register closure

| Threat ID | Component | Mitigation evidence |
|-----------|-----------|---------------------|
| T-7-SC | import-linter PyPI supply chain | Task 1 — operator "approved" tras verificar PyPI + GitHub público + releases desde 2017 |
| T-7-01 | `_core.py` accidental import of transport | `[tool.importlinter]` 4 forbidden contracts + CI step `lint-imports` (Tasks 2 + 3) |
| T-7-02 | Sync/async token cross-contamination | `verification/test_sync_async_isolation.py` parametrize 4 pkgs (matriz async skip D-11) |
| T-7-06 | Contracts vacíos contra módulo inexistente (Pitfall 6) | Task 2 crea 4 placeholders; output literal "4 kept, 0 broken" verifica detection |

## Self-Check

Files asserted to exist:

- `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` — present
- `packages/iol-client/src/iol_client/_core.py` — present
- `packages/higyrus-client/src/higyrus_client/_core.py` — present
- `packages/matriz-client/src/matriz_client/_core.py` — present
- `verification/test_sync_async_isolation.py` — present
- `pyproject.toml` modified (4 contracts + dev dep) — confirmed
- `.github/workflows/ci.yml` modified (lint-imports step) — confirmed

Commits asserted to exist:

- `c53e0eb` — feat(07-01): add import-linter + 4 forbidden contracts + 4 _core.py placeholders — confirmed in `git log`
- `685c5dc` — test(07-01): cross-leak sentinel test + CI step lint-imports — confirmed in `git log`

## Self-Check: PASSED
