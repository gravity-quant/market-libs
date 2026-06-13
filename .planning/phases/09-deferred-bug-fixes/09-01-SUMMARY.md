---
phase: 09-deferred-bug-fixes
plan: 01
subsystem: testing
tags: [iol-client, oauth, refresh-token, regression-tests, pytest-httpx, sync, async, cr-01, phase-09]

# Dependency graph
requires:
  - phase: 06-class-refactor-and-compat-safety-net
    provides: "_state.refresh_token field + CR-01 conditional rotation guard + _ensure_token refresh→password fallback (D-IOL-09, D-IOL-10)"
  - phase: 07-core-extraction
    provides: "_core.parse_login_response / parse_refresh_response retornando tuple[str, float, str | None] (D-04 alias)"
  - phase: 08-retries-and-logging
    provides: "_request shell con 401 re-auth-once + body-consume-then-raise (WR-02)"
provides:
  - "8 regression tests (4 sync + 4 async) lockeando los 4 paths del _state.refresh_token lifecycle (BUG-03)"
  - "Forensic-localizable guards para CR-01 conditional rotation (rama TRUE + rama FALSE)"
  - "Regression guards para refresh→password fallback silencioso (D-IOL-10)"
  - "Async mirror que ejercita el double-checked locking (D-IOL-09) end-to-end"
affects: ["phase-09-02", "phase-09-03", "phase-09-04", "phase-11"]

# Tech tracking
tech-stack:
  added: []  # NO new dependencies — uses existing pytest + pytest-httpx + pytest-asyncio
  patterns:
    - "Pattern S1: from __future__ import annotations mandatory header"
    - "Pattern S2: state = (iol_client.client | aio)._get_default()._state direct access (Phase 6 Pitfall #1)"
    - "Pattern S3: match_content=b'<body>' distinguishes 2 mocks on same URL (refresh vs password grants)"
    - "Pattern: tests count outgoing requests (len(httpx_mock.get_requests()) == N) to lock exact wire behavior"

key-files:
  created:
    - "packages/iol-client/tests/test_refresh_token_lifecycle.py (218 lines, 4 sync tests)"
    - "packages/iol-client/tests/test_refresh_token_lifecycle_async.py (195 lines, 4 async tests)"
  modified: []  # NO source modification (confirmed via git diff packages/iol-client/src/ HEAD~1 HEAD = empty)

key-decisions:
  - "1 atomic commit per D-12 combinando ambos test files (sync + async) — granularidad per-task pero coherente con el contrato BUG-03"
  - "Path 5 (refresh+password both fail → IOLAuthError) NO incluido en este plan — los acceptance criteria explícitamente lo excluyen; test cubierto en test_client.py:226 existing"
  - "Pitfall 6 (cross-test contamination de state.refresh_token) mitigado por explicit seed al inicio de cada test; NO se modifica conftest.py (cross-cutting, defer si emerge)"

patterns-established:
  - "4-path lifecycle lock template: success-rotates / 401-fallback / preserve-on-omit / rotate-on-provide. Replicable para futuras superficies con refresh_token rotation (higyrus, matriz si lo agregan)"
  - "Sync + async mirror con substituciones mecánicas mínimas (async def + await + aio._get_default + iol_client.client._get_default → cumple cross-package parity sync↔async"
  - "match_content literal como discriminador entre 2 mocks del mismo POST /token endpoint (evita FIFO collision)"

requirements-completed: [BUG-03]

# Metrics
duration: ~7min
completed: 2026-06-13
---

# Phase 09 Plan 01: BUG-03 Refresh Token Lifecycle Regression Tests Summary

**8 mocked regression tests (4 sync + 4 async) lockean los 4 paths del `_state.refresh_token` lifecycle en `iol-client` — CR-01 conditional rotation guard + D-IOL-10 refresh→password fallback + D-IOL-09 async double-checked locking quedan fijados sin tocar `_core.py` / `client.py` / `aio.py` / `_state.py`.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-06-13T16:17:57Z
- **Completed:** 2026-06-13T16:24:22Z
- **Tasks:** 2 (Task 1 sync, Task 2 async — combinados en 1 commit atómico per D-12)
- **Files modified:** 2 (ambos creados, ninguno modificado)

## Accomplishments

- **4 sync tests** en `packages/iol-client/tests/test_refresh_token_lifecycle.py`:
  1. `test_refresh_token_success_path_rotates`
  2. `test_refresh_401_falls_back_to_password`
  3. `test_refresh_preserves_token_when_server_omits_refresh_field` (CR-01 rama FALSE)
  4. `test_refresh_rotates_when_server_provides_new_field` (CR-01 rama TRUE)
- **4 async mirror tests** en `packages/iol-client/tests/test_refresh_token_lifecycle_async.py`:
  1. `test_async_refresh_token_success_path_rotates`
  2. `test_async_refresh_401_falls_back_to_password`
  3. `test_async_refresh_preserves_token_when_server_omits_refresh_field`
  4. `test_async_refresh_rotates_when_server_provides_new_field`
- **Zero source modifications** — `git diff HEAD~1 HEAD packages/iol-client/src/` returns empty (confirmado).
- **Forensic-localizable** — cada test tiene assertion específica: si alguien edita `if refresh is not None:` accidentalmente, path 3 falla con `state.refresh_token is None`; si removen el catch en `_ensure_token`, path 2 propaga `IOLAuthError`; si rompen el conditional CR-01, paths 3 y 4 divergen del expected.

## Task Commits

Un único commit atómico per D-12 combinando ambos test files (sync + async):

1. **Task 1 + Task 2: BUG-03 refresh_token lifecycle tests** — `8591e76` (test)

**Plan metadata:** (pendiente — orquestador hace el final commit con SUMMARY.md tras merge)

## Files Created/Modified

### Created
- `packages/iol-client/tests/test_refresh_token_lifecycle.py` (218 líneas) — 4 sync tests para los 4 paths del refresh_token lifecycle. Usa `state = iol_client.client._get_default()._state` (Pattern S2) + `match_content=b"..."` para distinguir refresh vs password grants (Pattern S3).
- `packages/iol-client/tests/test_refresh_token_lifecycle_async.py` (195 líneas) — 4 async mirror tests con `state = aio._get_default()._state` + `await aio.get_instruments("argentina")`. Ejercita el `_ensure_token` async double-checked locking end-to-end.

### Modified
- Ninguno — `git diff HEAD~1 HEAD packages/iol-client/src/` returns empty (confirmado).

## Test Suite Evidence

```text
$ uv run pytest packages/iol-client/tests/ --no-header
============================= 124 passed in 14.55s =============================
```

**Tests count delta:**
- Baseline (post-Phase-8): 116 tests
- Post-Plan-09-01: 124 tests
- Delta: **+8** (4 sync + 4 async, exactly matching plan spec)

**Ruff:** All checks passed (0 errors) en ambos nuevos files.
**Mypy strict:** Success: no issues found (0 errors) en ambos nuevos files.

## Source-Modification Verification

```text
$ git diff HEAD~1 HEAD packages/iol-client/src/ | wc -l
0
```

Confirma cero cambios en `packages/iol-client/src/` — el plan NO toca `_core.py`, `client.py`, `aio.py` ni `_state.py`. Solo adds test files.

## Decisions Made

- **1 atomic commit combinando Task 1 + Task 2** — D-12 del plan explicita "1 commit atómico" cubriendo ambos tasks como un contrato BUG-03 cohesivo. Granularidad per-task se preserva en el plan (acceptance criteria son per-task), pero la unidad de revert es el contrato completo.
- **Path 5 NO incluido** — los acceptance criteria del Task 1 explícitamente listan 4 paths; el path "refresh+password both fail" ya existe en `test_client.py:226` (`test_refresh_and_password_both_fail`) y en `test_async_client.py:186` (mirror). Duplicar acá agregaría redundancia sin nuevo locking.
- **NO modificar `conftest.py`** — el autouse fixture maneja `_configure_sync` + `_configure_async` con `token="test-token"` precargado. Cada test mutar `state.token = None; state.token_expires_at = 0.0; state.refresh_token = "<seed>"` explícitamente al inicio (Pattern S2). Si emerge contaminación cross-test de `state.refresh_token` (Pitfall 6), defer al plan que se descubra.
- **`from iol_client.exceptions import IOLAuthError` removido del sync file** — inicialmente importado por si futuro Path 5, pero genera ruff F401 + mypy `_ = IOLAuthError` collision con `pytest` namespace. Removido — el path 5 vive en `test_client.py` ya.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `IOLAuthError` import from sync file**
- **Found during:** Task 1 verification (mypy strict run)
- **Issue:** El plan instruye `from iol_client.exceptions import IOLAuthError` "por si el autocheck del read_first lo requiere para futuro path 5" + `_ = IOLAuthError`. mypy strict detectó conflicto con `_ = pytest` line (multiple type assignments to `_`). Plan path 5 NO está en scope.
- **Fix:** Removed both the import and the suppression line. El path 5 ya está cubierto por `test_client.py:226-251` existing.
- **Files modified:** `packages/iol-client/tests/test_refresh_token_lifecycle.py`
- **Verification:** ruff + mypy strict clean post-fix; 4 sync tests still GREEN.
- **Committed in:** `8591e76` (parte del commit del task, pre-commit edit).

**2. [Rule 1 - Bug] Docstring substring "@pytest.mark.asyncio" disparaba acceptance criterion grep == 0**
- **Found during:** Task 2 verification (acceptance criteria grep check)
- **Issue:** Docstring en async file contenía "NO ``@pytest.mark.asyncio`` decorator necesario" como nota explicativa. El grep literal del acceptance criterion (`grep -c "@pytest.mark.asyncio"` returns 0) hit el docstring → falso positivo.
- **Fix:** Reescribió la oración a "NO hace falta el decorator pytest-asyncio (mode auto lo aplica implícito)" — semánticamente equivalente, sin el substring literal.
- **Files modified:** `packages/iol-client/tests/test_refresh_token_lifecycle_async.py`
- **Verification:** `grep -c "@pytest.mark.asyncio"` now returns 0; 4 async tests still GREEN.
- **Committed in:** `8591e76` (parte del commit del task, pre-commit edit).

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bug — ambos cosméticos: dead-code import + docstring wording que confundía un grep check)
**Impact on plan:** Ningún cambio funcional. Tests, ruff, mypy, acceptance criteria todos GREEN post-fix.

## Issues Encountered

- **Test count baseline divergente** del plan (760 vs 116) — el plan citaba "760 tests baseline (Phase 8 final)" como total monorepo-wide, pero la verificación per-package fue contra `packages/iol-client/tests/` solamente (116 baseline). El delta +8 (116 → 124) cumple el spec del plan ("tests count delta +8 esperado"). Resolved.

## User Setup Required

None - solo añade test files; ninguna configuración externa.

## Next Phase Readiness

- **Plan 09-02 / 09-03 (live re-verification)** — los regression tests proveen el contrato observable que el live re-verification debe seguir validando. Si el live behavior diverge de los 4 paths lockeados, los tests in-vivo deberían capturarlo (e.g., si IOL elimina rotación de refresh_token, Path 4 live cae).
- **Plan 09-04 (public surface zero-diff)** — Plan 09-01 NO toca signatures públicas; Phase 6 D-09 snapshot debería estar intacto. Plan 09-04 valida formalmente.

## Self-Check

- File `packages/iol-client/tests/test_refresh_token_lifecycle.py`: **FOUND** (218 lines, 4 tests)
- File `packages/iol-client/tests/test_refresh_token_lifecycle_async.py`: **FOUND** (195 lines, 4 async tests)
- Commit `8591e76`: **FOUND** in `git log --oneline -3`
- Full iol suite `124 passed`: **CONFIRMED** (116 baseline + 8 new)
- Source diff `packages/iol-client/src/`: **EMPTY** (confirmed)
- Ruff + mypy strict: **CLEAN** on both new files

## Self-Check: PASSED

---
*Phase: 09-deferred-bug-fixes*
*Completed: 2026-06-13*
