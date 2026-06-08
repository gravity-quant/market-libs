---
phase: 04-higyrus-verification
fixed_at: 2026-06-08T00:00:00Z
review_path: .planning/phases/04-higyrus-verification/04-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-06-08T00:00:00Z
**Source review:** `.planning/phases/04-higyrus-verification/04-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (4 Critical + 5 Warning; Info excluido por `fix_scope=critical_warning`)
- Fixed: 9
- Skipped: 0

Las 9 fixes pasan `ruff check`, `ruff format --check`, `mypy --strict` y `pytest`
(51 tests, +7 vs baseline). Cada fix se commitea atómicamente con el formato
`fix(04): <ID> <descripción>` y todos los cambios espejan sync↔async cuando
aplica (CLAUDE.md "dual sync/async lock-step").

## Fixed Issues

### CR-01: `_request` regression — `list[str]` query params no longer split into repeated keys

**Files modified:** `packages/higyrus-client/src/higyrus_client/client.py`, `packages/higyrus-client/src/higyrus_client/aio.py`, `packages/higyrus-client/tests/test_client.py`, `packages/higyrus-client/tests/test_async_client.py`
**Commit:** `9b008db`
**Applied fix:** Añadido `doseq=True` al `urlencode(...)` en `_request` (sync + async).
Test de regresión paired (`test_request_doseq_splits_list_params_into_repeated_keys`
sync + async) que invoca `get_listado_cuentas(id_cuenta=["A","B"])` y verifica
que el query string contiene `idCuenta=A&idCuenta=B` y NO contiene `%5B`/`%5D`/`%27`.

### CR-02: `probe_login_sync` / `probe_login_async` only catch `HigyrusAuthError`, leak everything else

**Files modified:** `main_higyrus.py`
**Commit:** `c15254d`
**Applied fix:** Importado `HigyrusClientError` desde `higyrus_client`.
Catch en dos brackets: (1) `HigyrusClientError` cubre Auth/Authorization/RateLimit/APIError
(jerarquía del paquete), (2) `Exception` cubre network/transport (httpx.ConnectError,
TimeoutException, etc.). Ambos brackets setean `_auth_failed` para garantizar el
contrato cascade SKIPPED. Aplicado simétricamente en sync y async.

### CR-03: `probe_parity_sync_async` propagates network errors out of `main()`

**Files modified:** `main_higyrus.py`
**Commit:** `7413321`
**Applied fix:** Ampliado el `except` interno de `_capture_sync_query_string`
de `HigyrusAPIError` a `Exception` para alinear el contrato con el helper async
(consistencia preferida en el review). Mirror en `_capture_async_query_string`.

### CR-04: Driver sends `incluirParking="false"` (lowercase), public API requires `"False"`

**Files modified:** `main_higyrus.py`
**Commit:** `e4d73af`
**Applied fix:** Importado `format_bool` desde `higyrus_client._params`.
Reemplazado el literal `"false"` por `format_bool(False)` en los dos call sites
`_request` directos (sync + async, probes 11 y 12). Esto re-alinea el driver
con la wire-convention capitalizada que el test `test_get_posiciones_envia_booleano_capitalizado`
locking.

### WR-01: `login()` (sync + async) calls `resp.raise_for_status()` for non-401 errors

**Files modified:** `packages/higyrus-client/src/higyrus_client/client.py`, `packages/higyrus-client/src/higyrus_client/aio.py`, `packages/higyrus-client/tests/test_client.py`, `packages/higyrus-client/tests/test_async_client.py`
**Commit:** `cfc8f58`
**Applied fix:** Reemplazado el bloque `if resp.status_code == 401: _raise_for_response(resp); resp.raise_for_status()`
por `if not resp.is_success: _raise_for_response(resp)`. Ahora cualquier
non-2xx se mapea a la jerarquía `HigyrusClientError` en lugar de propagarse
como `httpx.HTTPStatusError`. Espejado en sync y async.
Tests de regresión añadidos: `test_login_403_levanta_authorization_error`,
`test_login_429_levanta_rate_limit`, `test_login_500_levanta_api_error` (sync)
+ `test_async_login_403_*` y `test_async_login_500_*` (async).

### WR-02: `_request` accepts `json_body=None` and forwards `json=None` to httpx

**Files modified:** `packages/higyrus-client/src/higyrus_client/client.py`, `packages/higyrus-client/src/higyrus_client/aio.py`, `packages/higyrus-client/tests/test_client.py`, `packages/higyrus-client/tests/test_async_client.py`
**Commit:** `3fe62c0`
**Applied fix:** Condicional sobre `json_body`: si no es `None`, se pasa en
`kwargs["json"]`; si es `None`, se omite (httpx no envía body ni `Content-Type:
application/json`). Espejado en sync y async.
Test de regresión añadido (`test_get_request_omits_body_and_content_type` sync +
async mirror) que verifica que GET emitido por `get_health()` tiene `req.content`
vacío y sin header `Content-Type`.

### WR-03: Driver's safe-print redaction silently drops short passwords

**Files modified:** `main_higyrus.py`
**Commit:** `0954d39`
**Applied fix:** Importado `sys`. El password se agrega SIEMPRE a la lista de
secrets (sin threshold). El username conserva `len(v) >= 4` y, si queda
excluido, se emite una warning a `stderr` con la primera letra (para que el
operador detecte el gap sin filtrar la credencial completa).

### WR-04: `_async_main` finally-block reads `result_login` only by virtue of try-completion order

**Files modified:** `main_higyrus.py`
**Commit:** `860129c`
**Applied fix:** Todos los locals referenciados por `_AsyncResults`
(`result_login`, `async_token_snapshot`, `result_health`, `health_raw`,
`result_listado`, `listado_raw`, `result_movs`, `result_pv`, `result_pos`,
`result_errors`, `async_query`) se inicializan ANTES del `try:` con sentinels
`ProbeResult(..., "SKIPPED", "(not executed)")` o `None` según corresponda.
Esto elimina el riesgo de `UnboundLocalError` en refactors futuros que muevan
el `return` después del `finally` o que necesiten devolver resultados
parciales.

### WR-05: `_capture_*_query_string` use `# type: ignore[method-assign]` to monkey-patch httpx

**Files modified:** `main_higyrus.py`
**Commit:** `28b9138`
**Applied fix:** Importado `httpx`. Reemplazado el monkey-patch del bound method
`_client.request` por `httpx.Client.event_hooks` / `httpx.AsyncClient.event_hooks`
(API pública estable). Eliminados los `# type: ignore[method-assign]`.
Preserva hooks pre-existentes (defensivo para componentes que registren sus
propios hooks). El spy recibe `httpx.Request` y extrae `request.url.query`
con el mismo tratamiento bytes/str que el patch original.

---

_Fixed: 2026-06-08T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
