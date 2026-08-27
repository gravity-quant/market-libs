---
phase: 30-iol-client-tipado
plan: 03
subsystem: api
tags: [python, dataclasses, mypy, typing, iol-client, decode, tdd, re-mock]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado
    provides: "Plan 30-01 — `iol_client.models` con SafeModel (from_api + to_dict) y el ritual de export/snapshot"
  - phase: 30-iol-client-tipado
    provides: "Plan 30-02 — `_core._parse_list_or_raise`, el helper genérico dueño del DecodeScope per-response y sede del guard de forma"
  - phase: 29-decoder-observable
    provides: "`_decode.py` — el walker congelado (walk_model, POLICY, _response_parser, DecodeScope)"
provides:
  - "`iol_client.models.Instrumento` — 2 campos de texto, cada elemento de la lista top-level de `get_instruments`"
  - "`parse_get_instruments_response` → `list[Instrumento]` con guard de forma que levanta (D-06 / T-30-08)"
  - "`get_instruments` devolviendo `list[Instrumento]` en las 4 superficies (método y shim, sync y async)"
  - "Las 16 firmas de iol migradas a modelos: cero retornos sin tipar en la superficie pública (criterio 2 del ROADMAP)"
  - "16 payloads de mock alineados con la captura viva 2026-06-06; el envelope que la suite asumía ya no existe en ningún test"
affects: [30-04, 32-gate-ast, 33-live-strict-run, 34-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "El tercer parser delegante en `_parse_list_or_raise`: one-liner sin decorar con un local anotado que narra el genérico para mypy strict"
    - "Re-mock evidence-first: el payload de test se deriva del schema committeado, nunca de lo que el parser tolera"
    - "Los re-mocks van en un commit **anterior** al cambio de parser, para que la suite quede verde en cada frontera de commit"
key-files:
  created: []
  modified:
    - packages/iol-client/src/iol_client/models.py
    - packages/iol-client/src/iol_client/__init__.py
    - packages/iol-client/src/iol_client/_core.py
    - packages/iol-client/src/iol_client/client.py
    - packages/iol-client/src/iol_client/aio.py
    - packages/iol-client/tests/test_models.py
    - packages/iol-client/tests/test_core.py
    - packages/iol-client/tests/test_client.py
    - packages/iol-client/tests/test_async_client.py
    - packages/iol-client/tests/test_refresh_token_lifecycle.py
    - packages/iol-client/tests/test_refresh_token_lifecycle_async.py
    - packages/iol-client/tests/test_fixture_reaches_production.py
    - verification/snapshots/iol-client-surface.txt

key-decisions:
  - "Los 14 sitios incidentales usan lista vacía y los 2 con aserción de contenido usan elementos reales del corpus: el guard rechaza lo-que-no-es-lista, no lo-que-está-vacío, así que `[]` es un mock seguro y honesto"
  - "El guard no ganó tolerancia dict-o-lista para acomodar mocks viejos — se corrigieron los mocks, que era el lado equivocado del desajuste"
  - "Dos tests de round-trip se renombraron a singular (`_de_titulo`, `_de_instrumento`) para que el gate de envelope mida código y no el plural español del endpoint"
  - "`instrumento` y `pais` se declaran texto libre pese a tener vocabulario chico observable: ningún campo de RESPONSE gana conjunto cerrado en este milestone (D-09/DT-07)"

patterns-established:
  - "Pattern 4: cuando un re-mock masivo y un cambio de parser conviven en un plan, el re-mock va primero y solo; el parser viejo (permisivo) acepta la forma nueva, así que ninguna frontera de commit queda roja"

requirements-completed: [TYP-01]

# Metrics
duration: 6min
completed: 2026-08-20
status: complete
---

# Phase 30 Plan 03: `Instrumento` + cierre de las 16 firmas Summary

**El endpoint donde la suite y la API más divergían quedó reconciliado en favor de la API: 16 mocks que construían un envelope inexistente ahora reflejan la lista top-level capturada en vivo, el parser que pasaba el payload sin tipar devuelve `list[Instrumento]` y levanta ante cualquier otra forma, y con eso las 16 firmas de `iol-client` están migradas — cero retornos sin tipar en la superficie pública.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-20T02:58:15Z
- **Completed:** 2026-08-20T03:04:22Z
- **Tasks:** 3
- **Files modified:** 13 (0 creados, 13 modificados)

## Accomplishments

- `Instrumento` declarado en `models.py` con los dos campos de texto que el schema committeado registra, exportado desde la raíz del paquete y listado en un `__all__` que sigue ordenado.
- Los **16 payloads** de mock corregidos en 6 archivos de test, más las 2 aserciones de contenido asociadas. Ningún archivo de test conserva el envelope que la captura contradice.
- `parse_get_instruments_response` reescrito in place: delega en `_parse_list_or_raise(resp, Instrumento)` y por lo tanto **levanta** `IOLAPIError` ante un body que no es lista al tope, con test dedicado. Una lista vacía sigue siendo válida.
- Las 4 firmas restantes re-anotadas en un solo commit. **16 de 16 migradas** — criterio 2 del ROADMAP cerrado.
- La suite del paquete creció 229 → **237**, con mypy strict, ruff, ruff format, import-linter y el gate de intactness todos verdes.

## Task Commits

1. **Task 1: modelo `Instrumento`** — `8bc8e11` (test, RED) → `ecd99dd` (feat, GREEN). Refactor plegado en GREEN: `ruff format` / `check --fix` no produjeron cambios residuales.
2. **Task 2: re-mock de los 16 payloads** — `c9ca048` (test). Suite verde en este commit, antes del cambio de parser, tal como el plan lo secuenció.
3. **Task 3: guard de forma + las 4 firmas** — `3cfdd9d` (test, RED) → `0e920b0` (feat, GREEN).

## Files Created/Modified

- `packages/iol-client/src/iol_client/models.py` — `Instrumento` insertado entre `Cotizacion` y `Titulo`; sin override de `from_api` (Pitfall 7 respetado). El docstring registra que la captura contradice el envelope y por qué los dos campos quedan texto libre.
- `packages/iol-client/src/iol_client/__init__.py` — `Instrumento` en el bloque de imports de modelos y en `__all__`, ambos alfabéticos. `__version__` intacto en `0.2.0`.
- `packages/iol-client/src/iol_client/_core.py` — `parse_get_instruments_response` reescrito como one-liner delegante; `Instrumento` importado.
- `packages/iol-client/src/iol_client/client.py` / `aio.py` — 4 anotaciones de retorno (método + shim × sync/async); los shells siguen siendo delegaciones puras, cero lógica movida.
- `packages/iol-client/tests/test_models.py` — +5 tests (21 → 26); `_INSTRUMENTO_ROW` derivado del schema committeado.
- `packages/iol-client/tests/test_core.py` — +2 tests netos, 1 reescrito in place; el test de guard es el que fija D-06.
- `packages/iol-client/tests/test_client.py` / `test_async_client.py` — re-mock, aserción de contenido migrada a atributos, y +1 test de paridad async.
- `packages/iol-client/tests/test_refresh_token_lifecycle.py` / su espejo async / `test_fixture_reaches_production.py` — solo payload; ni un token centinela ni una aserción de header tocados.
- `verification/snapshots/iol-client-surface.txt` — regenerado dos veces (ver deviación 1).

## Plan-mandated records

### (a) El conteo real de sitios re-mockeados frente al "~12" de CONTEXT (FA-06)

**RESEARCH tenía razón; CONTEXT subcontaba.** El inventario ejecutado, verificado
por `grep -rn 'instrumentos' packages/iol-client/tests/` antes y después:

| Archivo | Payloads | Aserciones | Forma usada |
|---|---|---|---|
| `tests/test_refresh_token_lifecycle.py` | 4 | — | lista vacía |
| `tests/test_refresh_token_lifecycle_async.py` | 4 | — | lista vacía |
| `tests/test_client.py` | 3 | 1 | 2 vacías + 1 con dos elementos reales |
| `tests/test_async_client.py` | 2 | — | lista vacía |
| `tests/test_fixture_reaches_production.py` | 2 | — | lista vacía |
| `tests/test_core.py` | 1 (bytes) | 1 | un elemento real, literal de bytes |
| **Total** | **16** | **2** | 14 incidentales + 2 con contenido |

Son **18 líneas en 6 archivos**, no "~12". Un trabajo dimensionado para 12
habría dejado 4 payloads con el envelope viejo, y esos 4 habrían empezado a
levantar `IOLAPIError` en cuanto la tarea 3 instaló el guard — es decir, la
suite se habría roto justo en el commit que instala la mejora, y el síntoma
habría parecido un bug del guard en vez de un re-mock incompleto. FA-06 queda
**resuelta a favor de RESEARCH** con el conteo ejecutado como evidencia.

### (b) La verificación por introspección de las 16 firmas

Corrida sobre las 4 funciones públicas de cada superficie. Salida literal:

```
get_quote                  -> <class 'iol_client.models.Cotizacion'>
get_historical_quotes      -> list[iol_client.models.Cotizacion]
get_instruments            -> list[iol_client.models.Instrumento]
get_instruments_by_type    -> list[iol_client.models.Titulo]
aio.get_quote              -> <class 'iol_client.models.Cotizacion'>
aio.get_historical_quotes  -> list[iol_client.models.Cotizacion]
aio.get_instruments        -> list[iol_client.models.Instrumento]
aio.get_instruments_by_type -> list[iol_client.models.Titulo]
```

Ningún retorno cae fuera del conjunto de los 4 tipos de modelo. La mitad async
**no** estaba en el criterio de aceptación del plan (que solo introspecciona
`iol_client`) y se agregó acá: sin ella el criterio 2 quedaría demostrado sobre
la mitad de la superficie. El conteo estructural coincide: 8 anotaciones que
devuelven modelo en `client.py` y 8 en `aio.py` = las 16 firmas.

### (c) Conteo de tests antes/después

| Punto | `pytest packages/iol-client -q` |
|---|---|
| Baseline (cierre de 30-02) | **229** |
| Después de Task 1 | 234 (+5 en `test_models.py`, 21 → 26) |
| Después de Task 2 | 234 (re-mocks: payloads cambiados, cero tests nuevos) |
| Después de Task 3 | **237** (+2 netos en `test_core.py`, +1 de paridad en `test_async_client.py`) |

Acumulado en la fase: 205 (pre-30-01) → 237. El plan pedía ≥ 205 y ≥ 18 en
`test_models.py`; ambos superados con holgura.

## Decisions Made

- **La lista vacía es el mock correcto para los 14 sitios incidentales, no un
  atajo.** Esos tests afirman sobre el header de autorización o sobre el conteo
  de requests; el payload es genuinamente incidental. `[]` es seguro
  precisamente porque el guard discrimina **forma**, no cardinalidad — y esa
  distinción quedó pinneada por un test propio
  (`test_parse_get_instruments_response_lista_vacia_no_levanta`), así que si
  alguien endureciera el guard a "lista no vacía" en el futuro, fallarían a la
  vez ese test y los 14 sitios, no en silencio.
- **El desajuste se corrigió del lado del test, no del parser.** La alternativa
  —tolerancia dict-o-lista— habría puesto verde la suite sin tocar un mock, y es
  exactamente el bug del vacío silencioso que el milestone existe para eliminar.
  La prohibición del plan se sostuvo: `_parse_list_or_raise` sigue teniendo un
  único `isinstance(raw, list)`.
- **`instrumento` y `pais` quedan texto libre aunque el corpus sugiera un
  vocabulario chico.** Es el caso donde más tentador era cerrar el conjunto
  (dos claves, valores como `acciones`/`cedears`/`argentina`), y por eso el
  docstring lo dice explícitamente. Además deja anotado que el `pais` de la
  **respuesta** no es el parámetro `pais` de **entrada**: el segundo sí podría
  tener su propio dominio sin que D-09 lo alcance.
- **`parse_get_instruments_response` sí delega, a diferencia de
  `parse_get_instruments_by_type_response`.** La diferencia no es de estilo: la
  forma top-level de este endpoint **es** una lista, así que el guard del helper
  aplica; la del otro es un dict envelope, y el mismo guard rechazaría toda
  respuesta válida. Los dos parsers vecinos difieren porque sus wires difieren.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `verification/snapshots/iol-client-surface.txt` necesitó regenerarse — dos veces**
- **Found during:** Task 1 y Task 3 (verificación)
- **Issue:** `verification/test_public_surface.py` afirma que el snapshot committeado no driftea de la superficie viva. La superficie cambió legítimamente dos veces en este plan: en Task 1 al exportar la clase (`+Instrumento : class : (instrumento: 'str', pais: 'str') -> None`) y en Task 3 al re-anotar la firma (`get_instruments … -> 'Any'` → `-> 'list[Instrumento]'`). Es el carry-forward que 30-01 marcó y que 30-02 confirmó como ritual por plan; acá disparó **por tarea**, que es la novedad.
- **Fix:** regenerado con la herramienta sancionada (`uv run python verification/regen_snapshots.py`) y committeado junto al cambio de fuente que lo causó, en los dos casos. Solo el archivo de iol cambió en ambas corridas.
- **Files modified:** `verification/snapshots/iol-client-surface.txt`
- **Verification:** `pytest verification/test_public_surface.py` → 4 passed, después de cada regeneración.
- **Committed in:** `ecd99dd` (+1 línea de clase) y `0e920b0` (1 línea de función cambiada)

**2. [Rule 1 - Bug] El gate de envelope de la Task 2 medía prosa, no código**
- **Found during:** Task 2 (verificación)
- **Issue:** El criterio `grep -rc 'instrumentos' packages/iol-client/tests/ | grep -v ':0$'` debía salir vacío, y devolvía `test_models.py:3`. Ninguno de los 3 sitios era un envelope: dos eran **nombres de test** que usan el plural español del endpoint (`..._de_instrumentos_por_tipo`, escrito por el Plan 30-02, y su gemelo nuevo) y el tercero era un docstring que yo mismo acababa de escribir citando literalmente la sintaxis que el gate busca. Es exactamente la clase de falso positivo que 30-01 documentó en su deviación 5, reapareciendo en otro gate.
- **Fix:** el docstring se reformuló ("un envelope de una sola clave") sin perder el hecho documentado, y los dos round-trips se renombraron a **singular nombrando el modelo** (`test_round_trip_reproduce_el_schema_committeado_de_titulo` y `..._de_instrumento`). El nombre nuevo es además más preciso: esos tests afirman sobre un modelo, no sobre el listado. Ninguna aserción cambió.
- **Files modified:** `packages/iol-client/tests/test_models.py`
- **Verification:** el grep sale 1 (sin resultados) y los 26 tests de `test_models.py` siguen verdes.
- **Committed in:** `c9ca048`

**3. [Rule 1 - Bug] El gate de centinelas contaba encabezados de hunk**
- **Found during:** Task 2 (verificación)
- **Issue:** El criterio `git diff …test_fixture_reaches_production.py | grep -c 'sentinel'` debía imprimir `0` y imprimió `2`. Los dos matches son las líneas `@@ … @@ def test_iol_sync_sentinel_token_reaches_authorization_header` que git agrega como contexto de hunk — es decir, el gate contaba el **nombre de la función** que contiene el cambio, no el cambio.
- **Fix:** verificado con el mismo diff sin contexto, que es lo que el criterio quiere decir: `git diff -U0 … | grep -E '^[+-]' | grep -c 'sentinel'` → **0**. Cero líneas modificadas mencionan un centinela; las únicas líneas tocadas en ese archivo son los dos payloads. El gate se dejó como está en el plan y la intención queda verificada acá con la forma correcta.
- **Files modified:** ninguno (defecto del gate, no del código).
- **Verification:** diff completo del archivo revisado a mano: 2 hunks, `-json={"instrumentos": []}` / `+json=[]`, nada más.
- **Committed in:** n/a — verificación, sin cambio.

---

**Total deviations:** 3 auto-fixed (1 bloqueante recurrente, 2 defectos de gate). No surgió ninguna situación de Rule 4 y no se necesitó ningún `checkpoint:decision` — el plan predijo que no habría ninguno porque ninguna decisión de este plan es one-way.
**Impact on plan:** ninguno sobre el alcance. Nada fuera de `packages/iol-client` y el único snapshot de verificación fue tocado. Las tres deviaciones son de instrumentación (snapshots y greps), no de comportamiento.

## Prohibitions — status at close

| Prohibition | Status |
|---|---|
| El parser no adopta tolerancia dict-o-lista para acomodar mocks viejos | **held** — `_parse_list_or_raise` conserva su único `isinstance(raw, list)`; `parse_get_instruments_response` no tiene cuerpo propio donde meter una rama. El caso dict está pinneado como `pytest.raises(IOLAPIError)`. |
| La suite no se pone verde debilitando aserciones con equivalente tipado | **held** — las 2 aserciones de contenido se **fortalecieron**: pasaron de igualdad contra un dict crudo a `isinstance` por clase + lectura de atributos + cardinalidad. Se agregó una aserción de paridad async que antes no existía. |
| Los tokens centinela de los tests de propagación de fixtures no se tocan | **held** — ver deviación 3: cero líneas modificadas los mencionan; las únicas 2 líneas tocadas en ese archivo son payloads. |
| Ningún campo de RESPONSE gana tipo de conjunto cerrado; `pais` e `instrumento` son texto libre | **held** — ambos declarados `str`; sigue sin haber ningún `Literal` en `models.py`. El docstring de `Instrumento` registra la tentación y la difiere a F33. |
| `_decode.py` y `uv.lock` intactos | **held** — `git diff --exit-code` limpio en ambos en cada tarea; `tools/check_decode_intactness.py` sale 0 (checks A–D). |

## Issues Encountered

Ninguno. La nota operativa que 30-01 y 30-02 arrastran sigue vigente:
`verification/test_with_options.py` tarda ~12,5 minutos por naturaleza y no
forma parte del job de tests del CI (que corre por paquete). No se re-corrió acá
porque este plan no toca la superficie de retry/backoff.

## User Setup Required

Ninguno — no hay configuración de servicio externo. Cero paquetes instalados;
`uv.lock` byte-idéntico.

## Next Phase Readiness

- **El criterio 2 del ROADMAP queda cerrado.** Las 16 firmas devuelven modelos y
  la introspección lo demuestra en las dos superficies. `mypy --strict` sale 0
  sobre `src` y `tests` del paquete, y también repo-wide (56 archivos).
- **30-04 hereda el trabajo que este plan deliberadamente no hizo:** `main_iol.py`
  sigue consumiendo las 4 funciones sin migrar (D-07 — los 2 sitios de acceso por
  atributo y los ≥5 estructurales que deben recibir `to_dict()` antes de que la
  próxima corrida viva escriba `"schema": "Cotizacion"` en los baselines). Está
  fuera del `<files_modified>` de este plan y mypy no lo typechequea, así que su
  estado actual no rompe ningún gate — pero **sí rompería la próxima captura
  viva**, que es la razón operativa del criterio 5.
- **Un tercer consumidor de `_parse_list_or_raise` confirma el helper.** Tres
  endpoints de forma distinta pasaron por él sin necesitar una sola rama nueva;
  el cuarto (`titulos`) sigue justificando su cuerpo propio por su envelope.
- **Abierto por diseño (F33):** el vocabulario de `instrumento`/`pais` sin censo
  vivo (DT-07), más lo que 30-01 y 30-02 dejaron abierto (elemento de `Punta`,
  los tres campos nunca observados de `Titulo`, la asimetría int/float de
  `cantidadOperaciones`).
- **Sin blockers.**

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-20*

## Self-Check: PASSED

Los 13 archivos modificados existen en disco; los 5 commits de tarea resuelven en `git log`.
