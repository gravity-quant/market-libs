---
phase: 03-iol-verification
fixed_at: 2026-06-06T16:45:00Z
review_path: .planning/phases/03-iol-verification/03-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
fix_scope: critical_warning
findings_total: 15
findings_critical: 3
findings_warning: 8
findings_info: 4
warnings_deferred: 8
infos_deferred: 4
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-06-06T16:45:00Z
**Source review:** `.planning/phases/03-iol-verification/03-REVIEW.md`
**Iteration:** 1
**Scope:** critical_warning (decisión usuario: BLOCKERs en este pase; WARNINGs a separate pass)

## Summary

- Findings in scope: 3 (los 3 BLOCKERs / Critical)
- Fixed: 3
- Skipped: 0
- Status: all_fixed

WARNINGs (8) e Infos (4) **diferidos** explícitamente por el usuario para una próxima pasada. Ver "Deferred Findings" abajo.

## Fixed Issues

### CR-01: Divergencia sync↔async — login() reseteaba `_refresh_token=None` cuando el server lo omitía

**Files modified:**
- `packages/iol-client/src/iol_client/client.py`
- `packages/iol-client/src/iol_client/aio.py`
- `packages/iol-client/tests/test_client.py`
- `packages/iol-client/tests/test_async_client.py`

**Commit:** `e80bc35`

**Applied fix:** Política condicional simétrica en `login()`/`_login_unlocked()` con `_refresh()`/`_refresh_unlocked()` (Pitfall 3 alignment). Cuando el server omite `refresh_token` en el payload del password grant, ahora **mantiene el `_refresh_token` cacheado** en vez de resetear a `None`. `configure()` sigue siendo la única vía para resetear explícitamente (rotación de credenciales).

Regression tests agregados (sync + async):
- `test_login_preserves_cached_refresh_token_when_server_omits`
- `test_async_login_preserves_cached_refresh_token_when_server_omits`

Ambos verifican: `_refresh_token = "refresh-original"` precargado → `login()` con payload sin `refresh_token` → cached value preservado. Si alguien revierte el fix, los tests fallan inmediatamente.

---

### CR-02: `probe_refresh_token` emitía falso FINDING con flow password-fallback legítimo

**Files modified:**
- `main_iol.py`

**Commit:** `82ea256`

**Applied fix:** Tras CR-01, el flujo "refresh fails → password fallback → server omits refresh_token" preserva el cached (no resetea a `None`). El caso `refresh_after is None` ahora **sólo puede ser una violación real de Pitfall 3 en `_refresh()`** (devuelve éxito pero descarta el cached). Actualizado:
- El `diff` del finding refleja que el caso es violación real (no ambigüedad falsa) tras CR-01.
- El `detail` del PASS final distingue explícitamente "rotated" vs "preserved (refresh path o password fallback)" — la heurística "_token cambió" ya no diferencia ambos caminos válidos, y eso queda documentado en el detail para auditoría humana.

No requirió regression test adicional al nivel del driver: la corrección del comportamiento subyacente está cubierta por los regression tests de CR-01 (que aseguran que `login()` preserva el cached). Si CR-01 regresara, el probe volvería a emitir el falso FINDING que CR-02 cierra.

---

### CR-03: `probe_auth_401` filtraba `_refresh_token` original del set `secrets`

**Files modified:**
- `main_iol.py`
- `packages/iol-client/tests/test_client.py`

**Commit:** `0cae4e6`

**Applied fix:** Dos cambios complementarios para cerrar el agujero de redaction:

1. **`probe_auth_401`:** reemplazado `iol_client.configure(password=bad_password)` por mutación directa de atributos del módulo (`_password`, `_token`, `_token_expires_at`). `configure()` resetea `_refresh_token = None` como parte de su semántica de rotación de credenciales — usarlo en el `try`/`finally` del probe wipeaba el `_refresh_token` cacheado por el primer `login()`, removiendo el valor del set `secrets` del SUMMARY. El `finally` restore ahora también muta `_password` directamente, preservando el cached `_refresh_token` a través del probe.

2. **`main()`:** captura snapshot de `iol_client.client._refresh_token` **antes** de que `probe_auth_401` corra y pasa el snapshot (no un live-read) a la lista `secrets`. Defense-in-depth — si algún cambio futuro re-introduce un wipe path, la redaction sigue funcionando.

Nota auth-once discipline: `probe_auth_401` corre ÚLTIMO (D-IOL-4); no hay probes downstream que necesiten el `_token` cacheado. El bad-creds login falla y deja `_token = None` / `_token_expires_at = 0.0`, que es el state correcto después de un login intent fallido.

Regression test agregado:
- `test_configure_resets_refresh_token_but_direct_password_mutation_preserves_it`

Lockea la invariante que motiva el fix: `configure(password=...)` SÍ resetea `_refresh_token = None` (comportamiento intencional para rotación), y mutar `_password` directamente NO afecta `_refresh_token`. Si alguien refactoriza `probe_auth_401` para volver a usar `configure()`, otros tests downstream no atrapan el bug pero este test sí (al nivel del invariante semántico del cliente).

---

## Skipped Issues

Ninguno. Los 3 BLOCKERs fueron arreglados todos in-cycle según feedback memory `feedback_fix_blockers_in_cycle`.

## Deferred Findings

Por decisión del usuario, los siguientes findings **NO fueron arreglados** en este pase y quedan disponibles para un próximo ciclo:

### Warnings (8) — diferidos

- **WR-01:** `_auth_failed` y `_fid_counter` no se resetean al inicio de `main()` (Pitfall 7) — `main_iol.py:137,141`. Riesgo de notebook/long-running session contaminada entre invocaciones.
- **WR-02:** falta test "refresh succeeds sin rotación preserva cached" — `tests/test_client.py:141-170`, `tests/test_async_client.py:109-140`. Cobertura del invariante Pitfall 3 sin rotación.
- **WR-03:** filtro `len(v) >= 4` en `secrets` permite leaks de credenciales cortas — `main_iol.py:1613` (la línea cambió levemente tras CR-03; el threshold sigue).
- **WR-04:** `_async_main()` no recolecta `aio._refresh_token` para `secrets` — `main_iol.py:1490-1509`.
- **WR-05:** `probe_get_quote_async` no replica plausibility check del sync — `main_iol.py:336-392` vs `254-333`. Asimetría dual sync/async.
- **WR-06:** `probe_login_async` y `_auth_failed` global comparten fail-cascade entre surfaces — `main_iol.py:225-251`. Costo de cobertura cuando solo una surface falla.
- **WR-07:** `probe_field_type_map` hace HTTP call EXTRA al endpoint `by_type` — `main_iol.py:962-976`. Total ~8 HTTP calls al endpoint vs lo documentado.
- **WR-08:** `status_code=0` en `IOLAuthError` cuando el cliente rechaza pre-HTTP — `client.py:92,125`, `aio.py:94,127`. Sentinel implícito sin documentación.

### Info (4) — diferidos

- **IN-01:** comentario inline en `main_iol.py:1008` referencia número de línea frágil.
- **IN-02:** `dt.UTC` usage requiere Python 3.11+ (OK para el proyecto, cosmético).
- **IN-03:** magic numbers `_PRICE_MIN = 0.0` y `_PRICE_MAX = 1_000_000.0` sin justificación inline — `main_iol.py:123-124`.
- **IN-04:** sección "Verified live (Phase 3)" async no aporta cobertura nueva más allá del espejo del sync — `tests/test_async_client.py:60-103`.

## Verification

Para cada fix:

**Tier 1 (re-read):** confirmado en todos los archivos modificados.

**Tier 2 (gates completos):** ejecutados después de cada commit:
- `uv run ruff check` → All checks passed
- `uv run ruff format --check` → 68 files already formatted
- `uv run mypy packages/iol-client main_iol.py` → Success, no issues
- `uv run pytest -q` → 198 passed, 1 deselected

Tests totales antes del fix: 195. Tests totales después del fix: 198 (3 nuevos):
- `test_login_preserves_cached_refresh_token_when_server_omits` (CR-01 sync)
- `test_async_login_preserves_cached_refresh_token_when_server_omits` (CR-01 async)
- `test_configure_resets_refresh_token_but_direct_password_mutation_preserves_it` (CR-03)

**Tier 3 (logic verification):** los tres fixes incluyen verificación semántica:
- CR-01 + tests: el flujo password-fallback ahora preserva el cached, verificado directamente por dos tests mockeados (sync + async).
- CR-02 + chain: CR-02 depende de CR-01 — si CR-01 falla, el detail de CR-02 se vuelve impreciso pero el behavior funcional sigue intacto.
- CR-03 + invariante test: el test de invariante sobre `configure()` vs mutación directa lockea el motivo del fix; si alguien refactoriza el probe para volver a usar `configure()`, el test no atrapa el bug del probe pero el invariante semántico del cliente queda documentado.

---

_Fixed: 2026-06-06T16:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
