---
phase: 07-core-py-extraction-sync-async-logic-dedup
reviewed: 2026-06-12T18:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - .github/workflows/ci.yml
  - pyproject.toml
  - main_matriz.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_core.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/aio.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/client.py
  - packages/ambito-financiero-client/tests/test_core.py
  - packages/higyrus-client/src/higyrus_client/_core.py
  - packages/higyrus-client/src/higyrus_client/aio.py
  - packages/higyrus-client/src/higyrus_client/client.py
  - packages/higyrus-client/tests/test_core.py
  - packages/iol-client/src/iol_client/_core.py
  - packages/iol-client/src/iol_client/aio.py
  - packages/iol-client/src/iol_client/client.py
  - packages/iol-client/tests/test_core.py
  - packages/matriz-client/src/matriz_client/_core.py
  - packages/matriz-client/src/matriz_client/client.py
  - packages/matriz-client/tests/test_client.py
  - packages/matriz-client/tests/test_client_class.py
  - packages/matriz-client/tests/test_core.py
  - verification/test_matriz_sweep_snapshot.py
  - verification/test_sync_async_isolation.py
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-06-12T18:00:00Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

Revisión de la extracción Phase 7 de `_core.py` (builders/parsers/auth-flow) en los cuatro paquetes.
La implementación es sólida en líneas generales: CR-03 (body-consume-before-raise) está correctamente
aplicado en `ambito`, `iol` y `matriz`; CR-05 (`_envelope_probe`) está cerrado; los invariantes D-04
(alias B8), D-06 (orden crítico en parsers) y D-07 (risk probes sin envelope key) están respetados.

Se detectaron **dos blockers** y **cuatro warnings**. El más crítico es un error de semántica en
`higyrus_client._core.raise_for_response`: la función **siempre levanta** una excepción (incluyendo
respuestas 2xx), lo cual viola el contrato establecido por los otros tres paquetes y cualquier caller
directo recibiría una excepción inesperada en un happy-path. El segundo blocker es que esa misma
función viola D-06 al llamar `resp.json()` antes de `resp.read()` explícito cuando el status es error.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `higyrus_client._core.raise_for_response` siempre levanta — no es no-op para 2xx

**File:** `packages/higyrus-client/src/higyrus_client/_core.py:121-151`

**Issue:** La función `raise_for_response` en higyrus no tiene ninguna guarda de status: llama
`resp.json()` incondicionalmente y termina siempre en `raise exc_cls(...)` (línea 151).
En los otros tres paquetes (`ambito`, `iol`, `matriz`) la función es un no-op para respuestas 2xx
(`if resp.is_error: raise ...`). En higyrus, si cualquier caller invoca `raise_for_response` sobre una
respuesta 200 OK, obtendrá una excepción `HigyrusAPIError(status_code=200, errors=None, ...)` de forma
silenciosa. El error está enmascarado hoy porque todos los parsers y el shim `_request` la envuelven en
`if not resp.is_success:`, pero la función expuesta en `__all__` no tiene ese contrato documentado y
diverge del resto del monorepo — cualquier test futuro del estilo de
`test_raise_for_response_does_not_raise_on_2xx` fallará inmediatamente.

Además, `resp.json()` en la línea 134 se llama **antes** de cualquier `resp.read()` explícito (D-06),
lo que en un futuro `httpx.Client(http2=True)` podría dejar el body stream abierto si el JSON decode
falla antes de consumirlo (aunque en la práctica httpx bufferea la respuesta antes de `.json()`,
no es el orden defensivo documentado en el contrato D-06 del proyecto).

**Fix:**
```python
def raise_for_response(resp: httpx.Response) -> None:
    """Mapea respuestas non-2xx a la jerarquía ``HigyrusClientError``.

    D-06: body ya consumido por ``_consume_and_check`` antes de llamar aquí.
    No-op para respuestas 2xx (contrato compartido con ambito/iol/matriz).
    """
    if not resp.is_error:
        return  # no-op para 2xx/3xx — consistente con el resto del monorepo

    try:
        payload: dict[str, Any] = resp.json()
    except ValueError:
        payload = {}

    errors = payload.get("errors") if isinstance(payload, dict) else None
    timestamp = payload.get("timestamp") if isinstance(payload, dict) else None

    exc_cls: type[HigyrusAPIError]
    if resp.status_code == 401:
        exc_cls = HigyrusAuthError
    elif resp.status_code == 403:
        exc_cls = HigyrusAuthorizationError
    elif resp.status_code == 429:
        exc_cls = HigyrusRateLimitError
    else:
        exc_cls = HigyrusAPIError

    raise exc_cls(resp.status_code, errors, timestamp)
```

Luego agregar el test faltante en `test_core.py`:
```python
def test_raise_for_response_does_not_raise_on_2xx() -> None:
    """2xx responses must be a no-op — consistent contract with ambito/iol/matriz."""
    resp = httpx.Response(200, json={"token": "abc"})
    _core.raise_for_response(resp)  # no exception
```

---

### CR-02: `higyrus_client._core.parse_get_health_response` levanta en body vacío incluso en 204 esperado

**File:** `packages/higyrus-client/src/higyrus_client/_core.py:356-382`

**Issue:** `parse_get_health_response` llama `_consume_and_check` que retorna el body. Si el status es
204 o el body está vacío, en vez de retornar `{}` (o la representación canónica de "salud sin cuerpo"),
levanta `HigyrusAPIError(status_code=0, errors=[{"title": "shape mismatch", ...}])`. El docstring dice
"se preserva el comportamiento legacy", pero el efecto real es que un endpoint `/api/health` que
responda 204 (perfectamente válido — health check sin body) resulta en una excepción con código
`status_code=0` y sin información útil de diagnóstico. La inconsistencia es que todos los demás parsers
de lista tratan 204 + body vacío como `[]` (normal), mientras que el health parser trata 204 como error.
Si el servidor alguna vez cambia de 200 a 204 en health, el cliente romperá silenciosamente.

Este es BLOCKER porque rompe el contrato de HTTP (204 No Content es una respuesta válida para health) y
produce una excepción confusa (`status_code=0`) que el caller no puede distinguir de un error real.

**Fix:**
```python
def parse_get_health_response(resp: httpx.Response) -> dict[str, Any]:
    """Parser ``GET /api/health`` → dict. 204 → ``{}`` (sin body = healthy)."""
    _consume_and_check(resp)
    if resp.status_code == 204 or not resp.content:
        return {}  # sin body = healthy, no levantar excepción
    raw = resp.json()
    if not isinstance(raw, dict):
        raise HigyrusAPIError(
            status_code=0,
            errors=[{"title": "shape mismatch", "detail": f"expected dict, got {type(raw).__name__}"}],
        )
    return raw
```

## Warnings

### WR-01: `higyrus_client._core.raise_for_response` hace doble-decode del body en error path

**File:** `packages/higyrus-client/src/higyrus_client/_core.py:134`

**Issue:** `_consume_and_check` llama `resp.read()` para consumir el body (línea 350), y luego
`raise_for_response` vuelve a llamar `resp.json()` (línea 134). En httpx, `resp.json()` es idempotente
una vez que el body está buffered, pero el docstring de `raise_for_response` dice "body-consume implícito:
`resp.json()` ya consume el stream del body" — esto ya no es preciso porque el stream siempre fue
consumido por `_consume_and_check` antes. El double-decode es inofensivo pero el comentario desactualizado
induce a pensar que `raise_for_response` puede invocarse sobre un body no consumido, lo cual contradice
D-06.

**Fix:** Actualizar el docstring para dejar claro que `raise_for_response` asume que el body ya fue
consumido por el caller (via `_consume_and_check`):
```python
def raise_for_response(resp: httpx.Response) -> None:
    """Mapea respuestas non-2xx a la jerarquía ``HigyrusClientError``.

    Precondición: ``resp.read()`` (o ``_consume_and_check``) ya fue llamado
    antes de este helper — el body está en buffer. ``resp.json()`` acá es
    idempotente sobre el buffer en memoria (D-06 caller responsibilidad).
    """
```

---

### WR-02: `test_sync_async_isolation.py` — URL para higyrus `get_listado_cuentas` asume encoding estándar pero el spec usa `url_pre_encoded=True`

**File:** `verification/test_sync_async_isolation.py:148`

**Issue:** El test monta el mock con la URL
`"https://api.test/api/cuentas/listadoCuentas?estado=alta"` y llama
`pkg.get_listado_cuentas(estado="alta")`. La quirk `url_pre_encoded=True` significa que el transport
shell hace `http.request(method, url, params=None)` donde la URL ya incluye `?estado=alta` pre-encoded.
httpx en ese caso concatena la URL verbatim — pero `pytest-httpx` matchea por URL exacta. El test
probablemente pasa hoy (porque `estado=alta` no tiene caracteres especiales), pero si el parámetro
`estado` contuviera un `/` (e.g. `"alta/especial"`), el pre-encoding produciría `estado=alta/especial`
mientras que un mock de `pytest-httpx` con `?estado=alta%2Fespecial` no matchearía. El test no ejercita
explícitamente la condición de `url_pre_encoded` — solo verifica el happy-path sin caracteres especiales.

**Fix:** Agregar un caso parametrizado en `test_core.py` que verifique que `estado="alta/test"` produce
`%2F` ausente en el spec.path (consistent con el patrón de los otros tests de quirk encapsulation).
El isolation test es suficiente para el happy path pero el contrato de quirk debería tener cobertura
dedicada en `test_core.py` (ya existe para movimientos/posiciones, falta para `get_listado_cuentas`
con `estado` que contenga `/`).

---

### WR-03: `higyrus_client.aio._request` shim toma el token bajo lock pero no verifica que sea non-None antes del assert

**File:** `packages/higyrus-client/src/higyrus_client/aio.py:211-217`

**Issue:** El método `AsyncClient._request` hace:
```python
await self._ensure_token()
token_lock = self._ensure_token_lock()
async with token_lock:
    token = self._state.token
assert token is not None
```
Si `_ensure_token()` falla (excepción en login — `HigyrusAuthError`), la excepción se propaga y el assert
no se ejecuta. Pero si `_ensure_token()` retorna sin excepción y `self._state.token` es `None` (estado
inconsistente improbable pero posible si el servidor responde con 200 pero sin token), el `assert` se
dispara con un `AssertionError` genérico que no está en la jerarquía de excepciones del paquete. La
versión sync (`client.py:178`) tiene el mismo patrón pero al menos es más simple. El riesgo es bajo pero
en producción los `AssertionError` son difíciles de diagnosticar versus un `HigyrusAuthError`.

**Fix:** Reemplazar el `assert` por un raise tipado:
```python
if token is None:
    raise HigyrusAuthError(
        0, [{"title": "auth", "detail": "_ensure_token() returned without populating token"}]
    )
```

---

### WR-04: `main_matriz.py` — `_envelope_probe` no protege contra `_auth_failed` para risk probes con `auth_basic_fn` cuando la auth falló

**File:** `main_matriz.py:272-273`

**Issue:** `_envelope_probe` tiene el guard `if _auth_failed: return SKIPPED` en la línea 272-273.
Sin embargo, las risk probes (`probe_get_positions`, `probe_get_detailed_positions`,
`probe_get_account_report`) pasan `auth_basic_fn=_risk_auth` — que usa credenciales de Basic Auth
independientes del token. La decisión de skipear en `_auth_failed` cuando hay `auth_basic_fn` es
discutible: las risk probes podrían funcionar incluso si el token está caído. Hoy el comportamiento
agresivamente skipea las risk probes cuando la auth falló, aunque podrían ser ejecutables. Esto es un
falso SKIPPED que reduce la cobertura de validación.

El impacto es que si `probe_login_sync` falla (token inválido) pero las creds Basic son válidas, las
18 probes downstream (incluyendo las 3 risk) se skipean innecesariamente, ocultando potenciales errores
en el Risk API.

**Fix:** Separar la guarda: para probes con `auth_basic_fn` no aplicar el cascade SKIPPED por token:
```python
if _auth_failed and auth_basic_fn is None:
    return (ProbeResult(name, "SKIPPED", f"auth failed: {_auth_failure_reason}"), None)
```

## Info

### IN-01: `matrices_client._core.raise_for_response` delega en `resp.raise_for_status()` sin enrichment

**File:** `packages/matriz-client/src/matriz_client/_core.py:148-155`

**Issue:** La función hace únicamente `resp.raise_for_status()` lo que levanta
`httpx.HTTPStatusError` — no el `PrimaryAPIError` del paquete. Los otros paquetes (ambito, iol) también
hacen esto, pero higyrus sí enriquece el error con el payload JSON. Para matriz, el test
`test_parse_envelope_response_raises_on_http_error_status` en `test_core.py:127-129` verifica
explícitamente que se levanta `httpx.HTTPStatusError`, no `PrimaryAPIError`. Esto es una elección
consciente pero rompe el principio de "single typed exception hierarchy" — un caller de
`raise_for_response` tiene que capturar `httpx.HTTPStatusError` Y `PrimaryAPIError` por separado.
No es un bug activo, pero reduce la usabilidad de la jerarquía de excepciones del paquete.

**Fix (opcional):** Wrappear el raise en un `PrimaryAPIError` con la info del status HTTP, similar
a cómo lo hace higyrus (post CR-01 fix):
```python
def raise_for_response(resp: httpx.Response) -> None:
    if not resp.is_error:
        return
    raise PrimaryAPIError(
        status=str(resp.status_code),
        description=f"HTTP {resp.status_code}",
        message=resp.text[:200] if resp.text else None,
    )
```

---

### IN-02: `test_higyrus_core.py` — ausencia de test `raise_for_response_does_not_raise_on_2xx`

**File:** `packages/higyrus-client/tests/test_core.py` (línea faltante)

**Issue:** El test suite de higyrus `_core` no incluye un caso que verifique que `raise_for_response`
es un no-op en 2xx. Los otros paquetes (ambito, iol) tienen este test:
```python
def test_raise_for_response_does_not_raise_on_2xx() -> None:
    resp = httpx.Response(200, content=b"ok")
    _core.raise_for_response(resp)  # no exception
```
Con el bug descrito en CR-01, este test FALLA hoy en higyrus. La ausencia del test es lo que permite
que el bug pase inadvertido.

**Fix:** Agregar el test al suite. Si el test falla, el CR-01 debe corregirse primero.

---

_Reviewed: 2026-06-12T18:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
