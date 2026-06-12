---
phase: 04-higyrus-verification
reviewed: 2026-06-08T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - main_higyrus.py
  - packages/higyrus-client/src/higyrus_client/client.py
  - packages/higyrus-client/src/higyrus_client/aio.py
  - packages/higyrus-client/src/higyrus_client/exceptions.py
  - packages/higyrus-client/tests/test_client.py
  - packages/higyrus-client/tests/test_async_client.py
  - packages/higyrus-client/.env.example
findings:
  critical: 0
  warning: 0
  info: 3
status: clean
---

# Phase 04: Code Review Report — higyrus-verification (re-review iter-3 tras iter-2 fix)

**Reviewed:** 2026-06-08T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** clean (sólo INFO carryovers; 0 BLOCKER + 0 WARNING)

## Summary

Re-revisión adversarial iter-3 tras commit `1f7127b` (iter-2 fix de WR-NEW-01).

**WR-NEW-01 resuelto.** El commit aplicó filtrado por path en ambos
helpers `_capture_sync_query_string` (líneas 320-330 de `main_higyrus.py`)
y `_capture_async_query_string` (líneas 375-381). El guard
`if not request.url.path.endswith("/movimientos"): return` previene que el
spy registrado vía `event_hooks` capture el query del `POST /api/login`
(`""`) durante el refresh de token, evitando el FINDING `SYNC-ASYNC-DRIFT`
espurio descrito en el reporte iter-2. La paridad sync/async se preservó
(filtro idéntico en ambos helpers, con docstrings consistentes que
referencian explícitamente `WR-NEW-01`).

**Verificación de correctitud del fix:**

- `request.url.path` en httpx es siempre `str` (verificado dinámicamente
  con `httpx.Request(...).url.path`); el `.endswith()` no levanta ni
  retorna falso-positivos.
- Los otros endpoints del cliente NO terminan en `/movimientos`:
  `/api/login`, `/api/health`, `/api/cuentas/listadoCuentas`,
  `/api/cuentas/{id}/posicionValuada`, `/api/cuentas/{id}/posiciones`.
  El filtro NO descarta ningún request objetivo del helper.
- Casos extremos verificados manualmente:
  - `id_cuenta` vacío (`""`) → URL `/api/cuentas//movimientos` → matchea ✓
  - `id_cuenta` con `/foo` interno → URL `/api/cuentas/X/foo/movimientos` → matchea ✓
  - El production path NUNCA construye trailing-slash (`f"/api/cuentas/{id_cuenta}/movimientos"`
    en `client.py:257` y `aio.py:274`), así que la única limitación teórica
    del filtro (rechaza `/movimientos/` con barra final) no es alcanzable
    desde el cliente — sólo desde una redirección HTTP, escenario que httpx
    típicamente sigue antes de invocar el hook.
- La paridad sync↔async se preservó: filtro idéntico, docstring espejo,
  ambos comentarios cite `WR-NEW-01` con la misma justificación.

**Test verification:**
- `uv run pytest packages/higyrus-client/tests/ -q` — **51 passed**.
- `uv run ruff check main_higyrus.py packages/higyrus-client/` — clean.
- `uv run mypy main_higyrus.py packages/higyrus-client/src/higyrus_client/` — clean.

**No se introdujeron nuevos BLOCKER ni WARNING en iter-2.** El commit
`1f7127b` es quirúrgico (+16 líneas en un solo archivo, ningún cambio en
los clientes), y la única superficie nueva (la condición `endswith`) está
correctamente targeted al endpoint que el helper exercita por contrato.

**Nota sobre falta de cobertura específica del fix:** El guard agregado no
tiene un test unitario dedicado (e.g., un test que instale el spy, dispare
un login + GET, y aserta que `captured["query"]` retiene el query del GET
y no el del login). El helper `_capture_*_query_string` vive en
`main_higyrus.py` que es el driver de verificación en vivo — no es parte
del package distribuible — así que la convención del repo es que su
correctitud se valide en runtime contra el server real, no con
`pytest-httpx`. Levantar este punto como una mejora futura (sin
clasificarlo como WARNING porque el costo-beneficio de cubrir el driver
con tests pesa más que la regresión que potencialmente atrapa).

**INFO carryovers de iter-1 que sobreviven** (los 3 vienen de iter-2 sin
cambios): duplicate logic entre `client.py` y `aio.py` (IN-01), test
matcher poco fiel a su nombre en `test_request_preserves_literal_slash_in_query`
(IN-02), y la entrada de trazabilidad para el iter-1 IN-03 invalidado
(IN-03).

Status: **clean**. Los 4 BLOCKER y 5 WARNING del reporte iter-1 (review
original) más el WARNING introducido por iter-1 (WR-NEW-01 detectado en
iter-2) están todos resueltos y blindados por tests donde aplica.

## Info

### IN-01: Carryover — duplicate logic entre `client.py` y `aio.py` aumenta superficie de drift

**File:** `packages/higyrus-client/src/higyrus_client/client.py:168-207` y
`packages/higyrus-client/src/higyrus_client/aio.py:192-229`

**Issue:** La función `_request` queda byte-por-byte idéntica entre sync
y async (modulo `async/await`). Las correcciones CR-01/WR-01/WR-02 de
iter-1 debieron aplicarse en dos lugares para evitar drift. CLAUDE.md
reconoce el patrón como "deuda conocida" del monorepo. `probe_parity_sync_async`
es el ÚNICO safeguard que sería capaz de detectar drift en runtime, y
depende del helper `_capture_*_query_string` que tiene su propio gotcha
ya resuelto (WR-NEW-01).

**Fix (largo plazo):** Extraer `_compose_request_url(base, path, params)`
a `_params.py` (el único módulo que ya comparten sync+async). Mantiene
la duplicación de body/headers pero reduce el surface de URL-encoding
bugs a un único lugar.

### IN-02: Carryover — `test_request_preserves_literal_slash_in_query` no afirma encoding del path

**File:** `packages/higyrus-client/tests/test_client.py:320-340` y
`packages/higyrus-client/tests/test_async_client.py:249-269`

**Issue:** El matcher `re.compile(r"^https://api\.test/api/cuentas/5208/movimientos\?.*")`
acepta cualquier query, incluido uno con `%2F`. Las afirmaciones
siguientes sólo chequean `query_str` — un futuro regreso que encode `/`
en el **path** (e.g., en `id_cuenta`) seguiría pasando el test. El
defecto es minor porque `id_cuenta` rara vez contendría `/`, pero el
matcher pierde fidelidad respecto al nombre del test.

**Fix:**

```python
httpx_mock.add_response(
    url="https://api.test/api/cuentas/5208/movimientos?fechaDesde=08/05/2026&fechaHasta=07/06/2026",
    method="GET",
    json=[],
)
```

Drop `re.compile` — pytest-httpx canonicaliza el query order via
`httpx.URL` y permite exact-URL match.

### IN-03: Carryover trazabilidad iter-1 — los imports flagged sí se usan

**File:** `packages/higyrus-client/tests/test_async_client.py:11-20`

**Issue:** El finding iter-1 IN-03 marcó posible F401 en
`HigyrusAuthorizationError` / `Posicion` / `PosicionValuada`. Re-validado
en iter-2 con `ruff check` clean. Tras re-inspección en iter-3:

- `HigyrusAuthorizationError` se usa en `test_async_request_propaga_authorization_error`
  (línea 40) y `test_async_login_403_levanta_authorization_error` (línea 307).
- `Posicion` y `PosicionValuada` se usan en `test_async_safemodel_from_api_typed_defaults`
  (líneas 86-87) y `test_async_get_posiciones_raises_on_dict_payload` (línea 240).

`uv run ruff check packages/higyrus-client/tests/test_async_client.py`
sigue clean (0 warnings).

**Fix:** N/A — verificado clean iter-2 e iter-3. Entrada mantenida sólo
para trazabilidad iter-1 → iter-2 → iter-3.

---

_Reviewed: 2026-06-08T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 3 of 3 (final)_
