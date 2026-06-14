---
status: complete
phase: 10-matriz-aio-py-creation-tokenstore
source:
  - 10-01-SUMMARY.md
  - 10-02-SUMMARY.md
  - 10-03-SUMMARY.md
  - 10-04-SUMMARY.md
started: 2026-06-14T01:08:00Z
updated: 2026-06-14T01:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold-start smoke — importar `matriz_client.aio` y configurar
expected: |
  En una sesión Python fresca, `from matriz_client import aio` no levanta excepción
  y `aio.configure(base_url=..., username=..., password=...)` deja la singleton lista
  para llamar endpoints async sin más set-up. `dir(aio)` muestra `AsyncClient`,
  `configure`, `login`, `aclose` y los 22 delegators async (`get_segments`, etc.).
result: pass
evidence: |
  `uv run --package matriz-client python -c "from matriz_client import aio; aio.configure(...); ..."`
  → `import OK / configure OK / all 24 symbols present in aio` (24 = AsyncClient + configure + login + aclose + 20 endpoints; new_order/replace_order/cancel_order también presentes — total 22 endpoints).

### 2. AsyncClient REST surface usable
expected: |
  `from matriz_client.aio import AsyncClient; async with AsyncClient() as c: await c.get_segments()`
  devuelve `list[Segment]`. Misma forma que la sync (`matriz_client.get_segments()`),
  con las 22 funciones del cliente. Reemplaza el stub de 103 LOC con superficie
  completa (~837 LOC AsyncClient).
result: pass
evidence: |
  35 tests async (test_async_queries.py + test_async_auth.py + test_async_mutations.py) pass
  in 2.05s. Live spot-check confirmado en `/tmp/phase10-live-paridad.log`:
  `PROBE get_segments_async: PASS 19 items`, `PROBE login_async: PASS token obtenido en 0.16s`.

### 3. TokenStore comparte token entre 3 superficies concurrentes
expected: |
  Con 5 hilos sync llamando `client._ensure_token()` + 5 corutinas async llamando
  `await asyncio.get_running_loop()` → `aio._aensure_token()` + 1 daemon thread de
  `ws_client._acquire_token_for_ws(default)` simultáneamente, los 11 callers ven
  EXACTAMENTE 1 refresh (no thundering herd).
result: pass
evidence: |
  17 tests TokenStore + integration pass. Notably:
  - `test_3way_concurrent_sync_async_daemon` PASS — 50 sync + 50 async + 5 daemon → 1 refresh.
  - `test_async_caller_waits_for_concurrent_sync_refresh` PASS — cross-thread blocking semántica.
  - `test_sync_caller_waits_for_concurrent_async_refresh` PASS — bidireccional.
  - `test_3way_race_after_ttl_expiry` PASS — TTL expiry no rompe la atomicidad.
  - `test_event_loop_not_blocked_during_refresh` PASS — p95 < 5ms cached read.

### 4. Live paridad sync↔async contra remarkets PASS
expected: |
  `uv run --package matriz-client python main_matriz.py` corre los 19 pares de probes
  (sync_probe + async_probe) interleaved en el mismo `main()` y al final imprime:
  `=== Phase 10 LIVE-02 Paridad sync↔async: PASS (probes_paired=N, divergences=0) ===`
  donde el set de outcomes (PASS / FINDING / SKIPPED) coincide entre sync y async.
result: pass
evidence: |
  Live run 2026-06-14 (log `/tmp/phase10-live-paridad.log`):
  ```
  SUMMARY: PASS=31 FAIL=0 SKIPPED=18 FINDING=1
  === Phase 10 LIVE-02 Paridad sync↔async: PASS (probes_paired=19, divergences=0) ===
  ```
  19 pares paired, divergences=0, 0 FAIL. Risk API endpoints (positions /
  detailed_positions / account_report) correctamente SKIPPED async con razón
  "D-09: Risk API auth_basic out-of-scope for Phase 10 async paridad; Phase 11 CR-08".
  Operator signoff capturado en `10-VALIDATION.md` con `status: approved`,
  `live_paridad_sync_async: true`.

### 5. 3 forward-reference skips activados
expected: |
  Las 3 líneas de `pytest.skip(...)` referenciando "Phase 10 REFAC-04" fueron
  removidas. Los 3 tests activos pasan.
result: pass
evidence: |
  - `grep -c "pytest.skip.*Phase 10\|pytest.skip.*REFAC-04"` retorna `0` en cada uno
    de los 3 archivos target.
  - `uv run pytest -q --collect-only | grep -cE "SKIPPED.*Phase 10|SKIPPED.*REFAC-04"`
    retorna `0`.

### 6. Cross-leak sentinel matriz async — `_state` y `token_store` aislados
expected: |
  `matriz_client.client._get_default()._state.token_store is not
   matriz_client.aio._get_default()._state.token_store`. Sync y async sentinels
  mutuamente invisibles entre superficies.
result: pass
evidence: |
  3 tests matriz selected en `verification/test_sync_async_isolation.py` pasan:
  - `test_sync_token_isolation_in_wire_request[matriz_client-X-Auth-Token-]` PASS
  - `test_async_token_isolation_in_wire_request[matriz_client-X-Auth-Token-]` PASS
  - `test_matriz_sync_async_state_and_token_store_instance_isolation` PASS
    (instancia distinta del token_store + state per surface).

### 7. CI green matrix Python 3.12 + 3.13
expected: |
  Pytest 3.12 + 3.13 verde, mypy strict, ruff, lint-imports, lint-logging,
  Phase 8 6 cross-cutting guards.
result: pass
evidence: |
  - `UV_PYTHON=3.12 uv run pytest -q` → 876 passed, 1 deselected (155.49s — capturado
    en `10-VALIDATION.md ## CI Matrix Output`)
  - `UV_PYTHON=3.13 uv run pytest -q` → 876 passed, 1 deselected (158.80s)
  - `uv run mypy` → Success: no issues found in 50 source files
  - `uv run lint-imports` → Contracts: 4 kept, 0 broken
  - `uv run ruff check` Plan 10-04 files + `packages/matriz-client/src/` → All checks passed
  - `uv run pytest verification/` → 176 passed (Phase 8 6 cross-cutting guards + Pitfall 4
    mutation gate + matriz cross-leak sentinel + CR-03 parse_envelope_consumes_body +
    CR-05 envelope_probe matriz sweep)

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none — 7/7 PASS]
