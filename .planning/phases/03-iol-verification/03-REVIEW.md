---
phase: 03-iol-verification
reviewed: 2026-06-06T15:30:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - main_iol.py
  - packages/iol-client/src/iol_client/aio.py
  - packages/iol-client/src/iol_client/client.py
  - packages/iol-client/tests/test_async_client.py
  - packages/iol-client/tests/test_client.py
findings:
  critical: 3
  warning: 8
  info: 4
  total: 15
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-06-06T15:30:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 3 implementa el fix IOL-07 (`grant_type=refresh_token` con fallback a password grant) en `client.py` + `aio.py` con 4+4 regression tests y reescribe `main_iol.py` como driver de 15 probes. Se examinaron las superficies sync y async, el invariante de mirror semántico, los 6 pitfalls (especialmente 3/4/6), el orden D-IOL-5 de probes, la disciplina single-shot del probe 401, y la cobertura mocked de los caminos del fix.

**Lo bueno:** Pitfall 6 (anti-deadlock async) correctamente respetado — `_refresh_unlocked` solo llama `client.post` directo. Pitfall 4 (mypy narrowing) implementado vía local copy + isinstance gate. Pitfall 3 (rotación condicional) en `_refresh()` mantiene el refresh existente si el server no rota. WR-01 (typed `exc.status_code`), WR-03 (single HTTP per probe) y IN-03 (`contextlib.suppress` en `aclose`) heredados correctamente. Las URLs exactas, el unwrap de `data["titulos"]`, y el formato `YYYY-MM-DD` con day>12 quedan locked vía Verified-live tests duales.

**Lo problemático:** Hay tres BLOCKERs reales: (1) **divergencia semántica sync↔async en `login()`** sobre cómo se trata el `_refresh_token` cuando el server lo omite — sync **resetea a `None`**, async **también resetea a `None`** PERO el behavior intencional del Plan 03-01 difiere de `_refresh()`/`_refresh_unlocked()` y produce un falso positivo del probe 14 después de un fallback password→login; (2) **`probe_refresh_token` falsea como FINDING el caso correcto donde el server no rota el refresh token tras un fallback a password** — `_refresh_token` quedará `None` por la captura de `login()` y el probe emite "Pitfall 3 violation" cuando en realidad es comportamiento esperado; (3) **`probe_auth_401` viola D-IOL-2 al usar `iol_client.configure(...)` que resetea estado de auth no relacionado** — `_token`, `_refresh_token`, y `_token_expires_at` quedan a None en el finally, invalidando el cache que probes anteriores construyeron (irrelevante para el run actual porque va último, pero **leaka el `_refresh_token` previamente capturado fuera de la lista `secrets` en el SUMMARY**).

## Critical Issues

### CR-01: Divergencia sync↔async vs convención del CLAUDE.md — `login()` resetea `_refresh_token=None` si el server lo omite

**File:** `packages/iol-client/src/iol_client/client.py:113`, `packages/iol-client/src/iol_client/aio.py:115`
**Issue:** Ambas surfaces hacen:
```python
_refresh_token = new_refresh if isinstance(new_refresh, str) and new_refresh else None
```
en `login()` / `_login_unlocked()`. Esto es el comportamiento documentado en `03-01-SUMMARY.md` key-decisions ("In login() ... `_refresh_token` is RESET to None if server omits — login is the first/fresh capture point"), pero rompe el invariante del fallback flow del Pitfall 3.

Escenario que rompe: el cliente está corriendo, hay `_refresh_token = "X"` cacheado de un login previo, el token expira, `_ensure_token` intenta `_refresh()`, el server rechaza con 401 → fallback a `login()` (password grant). El payload del password grant **no incluye refresh_token** (escenario plausible — IOL Help page no documenta si siempre lo incluye; algunos OAuth providers solo emiten refresh_token en el grant inicial). Resultado: `_refresh_token` queda en `None`, perdiendo el último value cacheado. La próxima expiración cae directo a password grant otra vez — el cliente nunca puede recuperar el refresh path aunque el server siga emitiendo refresh tokens en sub-flujos.

Adicional: este reset-on-omission contradice la rotación CONDICIONAL del `_refresh()` (que mantiene el existente si no viene uno nuevo, Pitfall 3). Dos políticas diferentes para el mismo invariante en el mismo archivo.

**Fix:** Aplicar la **misma política condicional** en `login()` que en `_refresh()`. Si el server omite `refresh_token` en el payload de `login()`, **mantener el existente** (que probablemente es lo que el caller esperaba) en vez de resetear a `None`. Si la primera vez `login()` no captura refresh_token, el estado inicial `_refresh_token = None` ya lo refleja correctamente.

```python
# client.py:113 (mismo cambio en aio.py:115)
new_refresh = data.get("refresh_token")
if isinstance(new_refresh, str) and new_refresh:
    _refresh_token = new_refresh
# else: keep existing _refresh_token (mismo comportamiento que _refresh()/Pitfall 3)
```

Si la decisión de Phase 3 (`login() reset`) es deliberada, **debe estar documentada en el código con un comentario justificando por qué `login()` rompe la simetría con `_refresh()`** y debe haber un test que cubra el caso "password grant sin refresh_token preserva el cached" o "lo resetea, según corresponda".

---

### CR-02: `probe_refresh_token` emite falso FINDING cuando login fallback exitoso resetea `_refresh_token`

**File:** `main_iol.py:1326-1340`
**Issue:** El probe asume que tras un refresh exitoso el `_refresh_token` queda no-None:
```python
if refresh_after is None:
    fid = _next_fid()
    append_finding(
        ...
        title="refresh path borró _refresh_token (Pitfall 3 violation)",
        ...
    )
    return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
```

Pero hay un escenario válido en el que `_refresh_token` queda `None` sin violación de Pitfall 3: si el `_refresh()` falla y el fallback a `login()` se ejecuta exitosamente PERO el server no devuelve `refresh_token` en el payload de password grant, `_refresh_token` queda en `None` por CR-01 (la política reset-on-omit de `login()`).

Esto produce un finding spurious que aparenta una violación cuando es el flujo `refresh-fails → password-fallback → password-omits-refresh-token` (válido). El probe no distingue entre "rotación borró el refresh" y "fallback exitoso resetea por política de `login()`".

Adicional: el probe usa la heurística "si `_token` cambió" para concluir "refresh path verified". Pero esta heurística también pasa si el flujo fue `refresh-fails → password-fallback-success`, no solo si el refresh path funcionó. El detail final "refresh path verified — token rotated" sería engañoso en ese caso.

**Fix:** Observar el comportamiento más finamente. Dos opciones:

1. **Capturar bytes de la red:** instrumentar `iol_client.client._client` con un transport interceptor que loggee qué body fue enviado al `/token`, así el probe puede distinguir refresh vs password grant. Esto es overhead.

2. **Más simple — comparar `refresh_after` contra `refresh_before`**: si `refresh_after == refresh_before` (no rotación) o `refresh_after != refresh_before and refresh_after is not None` (rotación), reportar PASS. Si `refresh_after is None`, **discriminar** entre dos sub-casos:
   - `refresh_before is not None and refresh_after is None`: ambiguo — podría ser violación de Pitfall 3 en `_refresh()` O fallback `login()` que omitió refresh.
   - Emitir el finding como **INFO** o "INDETERMINATE", no OPEN — con detail explícito "ambiguous: could be Pitfall 3 violation or password-fallback omitted refresh_token".

```python
# main_iol.py:1326 (recomendado)
if refresh_after is None:
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="AUTH",
        surface="sync",
        status="OPEN",
        title="_refresh_token quedó None tras refresh path — ambiguo",
        expected="_refresh_token preservado o rotado",
        actual="_refresh_token=None",
        diff=(
            "ambiguo: posible violación de Pitfall 3 en _refresh(), "
            "o fallback exitoso a login() con payload sin refresh_token; "
            "necesita inspección manual de network trace para discriminar"
        ),
        base_url=base_url,
    )
    return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN, ambiguous)")
```

Adicionalmente: arreglar CR-01 (login con política condicional) elimina la causa ambigüedad de raíz — en ese caso, `refresh_after is None` solo sucede si el `_refresh()` borró el cached (violación real).

---

### CR-03: `probe_auth_401` filtra `_refresh_token` original del set `secrets` al ejecutar antes del SUMMARY

**File:** `main_iol.py:1462-1464` (finally restore) + `main_iol.py:1606-1614` (secrets list)
**Issue:** `probe_auth_401` invoca:
```python
finally:
    iol_client.configure(password=original_password)
```
y `configure()` en client.py:73-75 hace `_token = None; _refresh_token = None; _token_expires_at = 0.0`.

Tras esto, en `main()` línea 1606-1614 se calcula el set de secrets para `safe_print`:
```python
secrets = [
    v
    for v in (
        os.getenv("IOL_USER"),
        os.getenv("IOL_PASSWORD"),
        iol_client.client._refresh_token,  # <-- yields None
    )
    if v and len(v) >= 4
]
```

Como `_refresh_token` quedó en `None` por el `configure()` del finally, **el refresh_token capturado por el primer `login()` (que estuvo cacheado durante todos los probes 1-14) NO está en la lista de secrets** cuando se imprimen los `PROBE` results y el `SUMMARY`.

Si CUALQUIER probe detail incluye el valor literal del refresh_token (defense-in-depth: hoy ningún probe lo hace, pero un detail futuro como `f"_refresh_token={iol_client.client._refresh_token}"` lo expondría) → leak. Esto viola la disciplina de redacción D-IOL-22 ("la lista se EXTIENDE dinámicamente con `_refresh_token` tras el primer login").

Adicional: `probe_auth_401` también destruye el `_token` cacheado por el login inicial — irrelevante porque va último, pero **fragiliza el invariante "auth-once discipline"** declarado en el docstring de main_iol.py:38-40. Si en el futuro alguien agrega un probe 16 después de probe_auth_401, ese probe re-disparará password grant (consumiendo un attempt contra el server).

**Fix:** Capturar el `_refresh_token` ANTES de cualquier `configure()` mutation:

```python
# main_iol.py:1602 (antes de probe_auth_401 si querés ser estrictamente correcto;
# o snapshot en main() inmediatamente después del primer login que funcionó)
captured_refresh_token = iol_client.client._refresh_token

# ... corren probes incluido probe_auth_401 ...

secrets = [
    v
    for v in (
        os.getenv("IOL_USER"),
        os.getenv("IOL_PASSWORD"),
        captured_refresh_token,  # <-- snapshot, no live read
    )
    if v and len(v) >= 4
]
```

Alternativa más robusta: `probe_auth_401` debe usar un método de inyección que **NO toque el estado de tokens cacheados** — por ejemplo, mutar `iol_client.client._password` directamente con `monkeypatch`-like semántica y restaurarlo en el finally sin pasar por `configure()`. Esto preserva el auth state cacheado y respeta el espíritu del D-IOL-2 mirror ("auth-once discipline").

## Warnings

### WR-01: `_auth_failed` y `_fid_counter` no se resetean al inicio de `main()` (Pitfall 7)

**File:** `main_iol.py:137`, `main_iol.py:141`
**Issue:** Pitfall 7 del RESEARCH.md ya documenta este caso: si `main_iol.py` se importa como módulo en un long-running session (notebook, repeated test invocation), los flags `_auth_failed: bool`, `_auth_failure_reason: str`, y `_fid_counter: int` persisten entre invocaciones. Una run #2 después de una run #1 que tuvo auth failure verá TODOS los probes como SKIPPED aunque la auth nueva funcione. Asimismo el counter de fids saltará de F-NN al fid siguiente.

**Fix:** Resetear al inicio de `main()`:
```python
def main() -> None:
    global _auth_failed, _auth_failure_reason, _fid_counter
    _auth_failed = False
    _auth_failure_reason = ""
    _fid_counter = 0
    if not require_env(_PKG, ["IOL_USER", "IOL_PASSWORD"]):
        return
    ...
```

### WR-02: Mock test `test_refresh_token_success_path` solo cubre la rama de rotación — falta cobertura de "non-rotating refresh response preserva el cached"

**File:** `packages/iol-client/tests/test_client.py:141-170`, `packages/iol-client/tests/test_async_client.py:109-140`
**Issue:** Los 4 tests de IOL-07 cubren: (1) refresh success con rotación, (2) refresh fails → password fallback, (3) ambos fallan, (4) login captura refresh. Falta el caso explícito (mocked) "_refresh() succeeds pero el server NO devuelve `refresh_token` en el payload → mantiene el cached" — la rama `if isinstance(new_refresh, str) and new_refresh: _refresh_token = new_refresh` (sin `else`) implementada por Pitfall 3.

Si alguien refactoriza el cliente y agrega un `else: _refresh_token = None` (regresión a la política reset-on-omit), ningún test atrapa el bug.

**Fix:** Agregar un quinto test por surface:
```python
def test_refresh_succeeds_without_rotation_preserves_cached(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: Pitfall 3 — server no rota, cliente mantiene el cached."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-original", raising=False)
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-original&grant_type=refresh_token",
        json={"access_token": "tok-new", "expires_in": 900},  # SIN refresh_token
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )
    iol_client.get_instruments("argentina")
    assert iol_client.client._token == "tok-new"
    assert iol_client.client._refresh_token == "refresh-original"  # PRESERVED
```

### WR-03: Filtro `len(v) >= 4` en la lista `secrets` permite leaks de credenciales cortas

**File:** `main_iol.py:1613`
**Issue:**
```python
secrets = [v for v in (...) if v and len(v) >= 4]
```
Si `IOL_USER` o `IOL_PASSWORD` tiene menos de 4 caracteres (por ejemplo durante un test con un username corto, o por configuración de un sandbox), no se incluye en el set de redacción. El comentario inline no justifica el threshold de 4.

**Fix:** Bajar el threshold a 1 o quitar el gate (`len(v) >= 1` ya está implícito en `v` truthy). El threshold parece ser un guard contra valores degenerados pero termina creando un agujero de redacción:
```python
secrets = [v for v in (...) if v]
```

### WR-04: `_async_main()` propaga excepciones sin recolectar `aio._refresh_token` para el set `secrets`

**File:** `main_iol.py:1490-1509`
**Issue:** Cuando `_async_main` corre sus probes, si alguno raisea no-caught (no IOLAuthError/IOLAPIError, sino otra cosa), el finally ejecuta `aclose()` y la excepción propaga, abortando el `asyncio.run(...)` en main(). El driver crashea con un traceback completo — pero la traceback **no pasa por `safe_print`** y puede contener referencias a `_refresh_token` que se reflejaron en algún payload async.

Adicional: la lista `secrets` solo incluye `iol_client.client._refresh_token` (sync), no `aio._refresh_token` (async). Si los dos están sincronizados, es lo mismo; pero si por algún path divergen (e.g., `aio._refresh_token` se rotó pero `iol_client.client._refresh_token` no porque solo el sync se ejercitó), una línea de salida puede leakear el async refresh.

**Fix:** Incluir ambos en `secrets`:
```python
secrets = [
    v
    for v in (
        os.getenv("IOL_USER"),
        os.getenv("IOL_PASSWORD"),
        iol_client.client._refresh_token,
        aio._refresh_token,
    )
    if v
]
```

### WR-05: Inconsistencia probe sync vs async — `probe_get_quote_async` no replica el plausibility check del sync

**File:** `main_iol.py:336-392` (async) vs `main_iol.py:254-333` (sync)
**Issue:** `probe_get_quote_sync` aplica el bounds check `_PRICE_MIN < ultimo < _PRICE_MAX` (líneas 315-332). `probe_get_quote_async` solo extrae `ultimo = quote.get("ultimoPrecio")` y reporta. Esto viola implícitamente la convención dual sync/async mirror del CLAUDE.md.

CONTEXT.md lo lista como Discretion del implementador ("Discrecionalmente: si añadir o no este check"), pero la decisión final debe ser **una** — o ambas surfaces hacen el check, o ninguna. La asimetría actual hace que un mismo bug de magnitud (e.g., precio devuelto x100) sea detectado solo si llega a la sync surface, no async.

**Fix:** Espejar el check en `probe_get_quote_async`, o eliminarlo del sync. Recomendado espejar (más cobertura). Extraer el bounds check a un helper:
```python
def _check_price_bounds(probe_name: str, surface: str, ultimo: Any, base_url: str) -> str | None:
    """Returns fid string if out of bounds, None if OK."""
    if isinstance(ultimo, int | float) and not (_PRICE_MIN < float(ultimo) < _PRICE_MAX):
        fid = _next_fid()
        append_finding(...)
        return fid
    return None
```
Y llamarlo desde ambos probes.

### WR-06: `probe_login_async` y `_auth_failed` global comparte fail-cascade entre surfaces (acknowledged Discretion pero costoso)

**File:** `main_iol.py:225-251`
**Issue:** Cuando `probe_login_sync` PASS pero `probe_login_async` FAIL, el flag `_auth_failed = True` queda set, lo cual hace que TODOS los probes sync downstream (3, 5, 7, 9) emitan SKIPPED aunque el sync token sea válido. CONTEXT.md lo documenta como Discretion D-IOL-3 ("flag único compartido, no surface-segregated"), pero el costo es: una corrida cuya sync auth funciona pero async no funciona pierde TODA la cobertura sync (4 endpoints × IOL-02 + IOL-03 + IOL-04 + IOL-06 partials).

Dada la inversión en la dual surface, el flag debería ser por-surface.

**Fix:** Dos flags separados:
```python
_auth_failed_sync: bool = False
_auth_failed_async: bool = False
_auth_failure_reason_sync: str = ""
_auth_failure_reason_async: str = ""
```
Cada probe checkea solo el flag de su surface. Esto preserva la cobertura cross-surface cuando solo una de las dos falla.

### WR-07: `probe_field_type_map` hace HTTP call EXTRA al endpoint `by_type` — semánticamente Pitfall 1 (doubling HTTP calls)

**File:** `main_iol.py:962-976`
**Issue:** Comentario inline dice "ÚNICA HTTP call duplicada permitida (Pitfall 2)" pero ya hay un call previo en `probe_get_instruments_by_type_sync` (línea 697) y otro en el sanity check de 6 types (línea 757). Total: **8 HTTP calls al endpoint `/api/v2/Cotizaciones/{itype}/argentina/Todos`** por corrida (probe 9: 1 sample + 6 sanity, probe 12: 1 envelope check). Esto es 8x lo que documenta D-IOL-5 ("9. probe_get_instruments_by_type_sync — `instrument_type='acciones'`").

Para WR-03 (single HTTP per probe-CONCEPT) la justificación de Pitfall 2 cubre **1** call extra; pero combinado con el sanity check de 6 types ya es **7** calls al mismo endpoint solo en probe 9. El total de 8 incrementa rate-limit risk contra `api.invertironline.com` sin proporción.

**Fix:** El sanity check de los 6 types puede usar **type-only assertion sin HTTP call** si el envelope check de probe 12 ya tiene el sample crudo de `acciones`. Para los otros 5, una opción es muestrear UN sub-set rotativo por run (e.g., 2 random types por corrida en lugar de los 6), o diferir el sanity completo a una cron-job separada.

Mínimo recomendable: cachear el `wrapper_result` del primer call de probe 9 y reusar el envelope crudo en probe 12 vía un segundo path (pasarlo como argumento a `probe_field_type_map`). Actualmente probe 12 recibe `None` para `instruments_by_type_envelope` (línea 1582) lo cual fuerza el re-fetch. Si en cambio capturáramos el envelope en probe 9 vía `_request` directo y lo pasáramos a probe 12, ahorramos 1 call.

### WR-08: Status_code en `IOLAuthError(0, ...)` cuando el cliente rechaza pre-HTTP

**File:** `packages/iol-client/src/iol_client/client.py:92,125`, `packages/iol-client/src/iol_client/aio.py:94,127`
**Issue:** Cuando faltan credenciales o `_refresh_token`, el código levanta `IOLAuthError(0, "...")` con `status_code=0`. Esto es semánticamente incorrecto — 0 no es un HTTP status code real. Si un caller hace `except IOLAuthError as exc: if exc.status_code == 401: ...`, no atrapará este caso. Y el probe `probe_auth_401` chequea `if status_code == 401` (línea 1403), por lo que un IOLAuthError(0) ahí se clasifica como "status inesperado".

Aunque CR-03 cubre la mutation issue de `probe_auth_401`, el wire de signaling sigue ambiguo: 0 es un sentinel implícito sin documentación.

**Fix:** Usar un sentinel explícito o una excepción separada:
- Opción A: `IOLAuthError(-1, ...)` para client-side rejection.
- Opción B: nueva subclass `IOLCredentialsError(IOLAuthError)` para los casos donde el cliente rechaza antes del HTTP, y dejar `IOLAuthError(status_code, ...)` solo para HTTP responses.

Opción B es más limpia y compatible con el `except` hierarchy (`IOLCredentialsError` sigue siendo `IOLAuthError`).

## Info

### IN-01: Comentario inline en `main_iol.py:1008` referencia número de línea frágil

**File:** `main_iol.py:1008`
**Issue:** `diff="client.py:254 hace data.get('titulos', []) y devuelve [] silenciosamente"` — la referencia a `client.py:254` es frágil; si alguien refactoriza client.py este texto queda desactualizado y el finding emitido a humanos referencia una línea incorrecta.

**Fix:** Usar referencia simbólica:
```python
diff="get_instruments_by_type wrapper hace data.get('titulos', []) y devuelve [] silenciosamente",
```

### IN-02: `dt.UTC` usage requiere Python 3.11+ (OK para el proyecto pero documentar)

**File:** `main_iol.py:1149`
**Issue:** `dt.datetime.now(dt.UTC)` — `datetime.UTC` se agregó en Python 3.11 ([PEP 615 era TZ data; UTC alias era 3.11](https://docs.python.org/3/library/datetime.html#datetime.UTC)). Proyecto declara Python 3.12+ así que está OK, pero si en algún momento el CI matrix vuelve a 3.10, esto rompe.

**Fix:** Defensive: `dt.datetime.now(dt.timezone.utc)` funciona igual en 3.10+. Cosmético.

### IN-03: Magic numbers `_PRICE_MIN = 0.0` y `_PRICE_MAX = 1_000_000.0`

**File:** `main_iol.py:123-124`
**Issue:** Bounds plausibles para el sanity check del precio (Discretion D-IOL-20). No hay justificación inline del por qué `1_000_000` y no `10_000_000` o `100_000`. Si GGAL cotiza a más de 1M en pesos argentinos en algún momento (no imposible con inflación de varios años), el probe emitirá un finding PARAM false-positive.

**Fix:** Documentar la razón inline:
```python
# Bounds plausibles para AR equity en ARS al 2026 (~ARS 5_000-50_000 típico para GGAL).
# El upper bound es generoso (x20) contra inflación; ajustar si AR pesos se denominan.
_PRICE_MIN: float = 0.0
_PRICE_MAX: float = 1_000_000.0
```

### IN-04: Sección `# ------ Verified live (Phase 3) ------` agregada con notación de "espejo del sync" no aporta cobertura nueva async

**File:** `packages/iol-client/tests/test_async_client.py:60-103`
**Issue:** Los tests `test_async_get_quote_url_exacta_con_query_string`, `test_async_get_instruments_by_type_unwraps_titulos`, y `test_async_get_historical_quotes_url_dia_gt_12` son funcionales pero literalmente copian las mismas aserciones del sync, sin verificar invariantes específicos del async (e.g., que `await aio.get_quote(...)` no acumula tareas pendientes, que el lock no se queda adquirido tras error, etc.).

Esto refleja la deuda conocida de "lógica duplicada sync/async" del CLAUDE.md, pero el conjunto de tests Verified-live podría ser leaner sin perder valor: bastaría con UN test async que ejercite las 3 invariantes en un solo flujo (cuando todos los invariantes son URL exactness + envelope unwrap + isinstance, son ortogonales y se pueden agrupar).

**Fix:** Opcional. Si se priorizan tests de async-specific concerns (cancel-safety, lock-release-on-exception), agregar un test cuarto que cubra `await aio.aclose()` durante un `_request` in-flight (Pitfall potencial no documentado: si `aclose()` se llama mientras un `_request` está en flight, ¿qué pasa con el `_token_lock`?).

---

_Reviewed: 2026-06-06T15:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
