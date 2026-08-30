---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
plan: 05
subsystem: testing
tags: [deep-chain, null-object, ast-lock, higyrus, zero-http, non-vacuity, ci]

# Dependency graph
requires:
  - phase: 39-04
    provides: "verification/test_main_iol_deep_chain.py — la variante hermana recién aterrizada, y la ubicación real de la allowlist (step de driver locks del job `lint`, no del job `test`)"
  - phase: 36-...
    provides: "verification/test_main_market_data_deep_chain.py — el analog exacto (_protected_node_ids, _chain_reaches, piso por probe WR-06)"
  - phase: 39-02
    provides: "packages/higyrus-client/tests/test_deep_chain_edges.py — la semántica mockeada de la rama poblada de parking, que una corrida en vivo no puede producir"
  - phase: 29-...
    provides: "SafeModel.from_api enrutado por _decode.walk_model con current_sink() y la ContextVar STRICT_DECODE que Client._request bindea sin resetear"
provides:
  - "verification/test_main_higyrus_deep_chain.py — lock AST de la cadena Posicion.parking en los 2 probes de posiciones de higyrus, en la allowlist de CI"
  - "main_higyrus.py construye Posicion.from_api(row) sobre el payload ya obtenido y desreferencia .parking[0].diasParking dentro del cuerpo del try (sync + async)"
  - "Un test de 'cero llamadas HTTP adicionales' que ninguna de las variantes hermanas tenía — pinea la propiedad que hace legítimo el diseño"
  - "La limitación de cobertura de incluirParking=False escrita en el código y marcada para el censo de 39-08"
affects: [39-06, 39-07, 39-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Construcción tipada sobre el payload en mano como forma de ejercitar una cadena sin gastar una segunda llamada HTTP: from_api enruta por el mismo walker, el mismo sink y la misma ContextVar de modo estricto que el parser del cliente"
    - "Lock AST que cuenta llamadas emisoras de HTTP por probe (_HTTP_CALL_NAMES + _MAX_HTTP_CALLS_PER_PROBE) para impedir que un refactor 'arregle' una cadena agregando un round trip"
    - "Piso por probe con el agregado DERIVADO por sum(), nunca re-tipeado (heredado del analog)"

key-files:
  created:
    - verification/test_main_higyrus_deep_chain.py
  modified:
    - main_higyrus.py
    - .github/workflows/ci.yml

key-decisions:
  - "La cadena se construye sobre el payload ya obtenido, no llamando a la función tipada: un segundo round trip duplicaría el request del concepto posiciones y rompería la convención de una llamada HTTP por concepto de probe — y no compraría nada, porque from_api enruta por el mismo walker/sink/ContextVar"
  - "El try es NUEVO, no el existente: la normalización de raw (None → [], chequeo de isinstance) vive fuera del try original, así que la cadena tipada quedó en su propio try/except _RESIDUAL_PROBE_EXCEPTIONS. El plan lo autoriza explícitamente; la condición dura (toda desreferencia en el CUERPO de un try) se cumple"
  - "HigyrusDecodeError NO se captura localmente: no es subclase de nada en _RESIDUAL_PROBE_EXCEPTIONS, así que un raise de modo estricto desde from_api sigue viajando al decorador probe_context (on_decode_error=_shape_probe_result_pair) y produce el finding SHAPE de siempre, sin doble emisión"
  - "_ALIAS_NAMES = {diasParking} solamente: Parking declara cuatro slots; ensanchar el set dejaría que un probe alcance el piso desreferenciando un campo que nadie lee (decisión de 39-04, heredada)"
  - "incluirParking sigue en False: flipearlo alteraría la forma de la respuesta y quemaría el baseline write-once de get_posiciones por deriva de schema, sin ganancia con la mitad en vivo bloqueada por DNS"
  - "La allowlist de CI está en el job `lint` (step de driver locks), no en el `test` — la corrección ya anticipada por 39-03 y 39-04, verificada por grep de test_main_iol_deep_chain.py antes de editar"

patterns-established:
  - "Cada archivo nuevo bajo verification/ entra a la allowlist de ci.yml en el MISMO commit que lo vuelve verde (no antes: en el commit RED queda deliberadamente fuera)"
  - "Una limitación de cobertura medida se escribe en el sitio de código que la produce, con destino explícito al censo, no sólo en el SUMMARY"

requirements-completed: [LIVE-NOBJ-01]

# Metrics
duration: 6min
completed: 2026-08-30
status: complete
---

# Phase 39 Plan 05: Cadena `Posicion.parking` gastada en los probes de posiciones de higyrus Summary

**Un lock AST que exige que los dos probes de `get_posiciones` de `main_higyrus.py` construyan `Posicion.from_api(row)` sobre el payload que ya obtuvieron y desreferencien `.parking[0].diasParking` dentro del cuerpo de un `try` — más un test que ninguna variante hermana tenía: la cadena debe costar CERO llamadas HTTP adicionales.**

## Performance

- **Duration:** ~6 min
- **Tasks:** 2 (1 RED, 1 GREEN — plan `type: tdd`)
- **Files modified:** 3 (1 creado, 2 modificados)

## Accomplishments

- **La asimetría D-04 está cerrada.** `main_higyrus.py` importaba `Posicion` desde hace fases pero sólo la usaba como *tipo* en el probe de diff bidireccional (línea 2091); ninguno de los probes de lectura la construía. Los dos probes de posiciones terminaban en `f"{len(raw)} items"` sobre un dict crudo, y `len()` nunca toca `parking`: todo el camino de decode de `Posicion → list[Parking] → diasParking` viajaba sin ejercitar mientras ambos probes reportaban PASS. Ahora la cadena se recorre de verdad, en sync y en async.
- **El diseño de cero HTTP adicional quedó pinneado, no sólo documentado.** `test_the_typed_chain_adds_no_http_call` cuenta por AST toda llamada emisora de request dentro de cada probe (`_raw_request_sync`, `_raw_request_async`, `get_posiciones`) y exige exactamente una — la que ya existía. Es lo que impide que un refactor futuro "arregle" la cadena llamando al endpoint tipado una segunda vez: eso duplicaría el request del concepto posiciones, duplicaría la emisión de divergencias y rompería la convención del driver mientras todos los demás tests de este módulo seguían verdes. Los tres tests que ya pasaban en RED incluían éste: la propiedad valía hoy y el lock la congela.
- **La construcción tipada es gratis por razones estructurales, no por casualidad.** `SafeModel.from_api` enruta por `_decode.walk_model` con `_decode.current_sink()` — el mismo walker y el mismo sink que el parser del cliente — y hereda la `ContextVar` `STRICT_DECODE` que `Client._request` bindea y deliberadamente **no** resetea (el reset en un `finally` desbindearía el modo antes de que el decoder lo lea). Una construcción hecha después del request y en el mismo contexto sigue viendo el modo estricto y emite exactamente los registros que la función tipada habría emitido.
- **El lock corre en CI:** entró a la allowlist explícita del step de driver locks del job `lint` en el mismo commit que lo volvió verde (T-39-19). Un guard bajo `verification/` fuera de esa lista es **inerte** — el hallazgo WR-01 del code review de la Phase 36.
- **La limitación de cobertura está en el código, no sólo en el SUMMARY.** El comentario junto a cada comprensión dice, con esas palabras, que `incluirParking` sigue en `False` a propósito y que **en una corrida en vivo la rama poblada de `parking` no se ejercita**, y nombra la suite mockeada del plan 39-02 como la evidencia de esa rama, con destino explícito al censo del 39-08.

## Task Commits

1. **Task 1 (RED): lock AST de la cadena `Posicion.parking`** — `636619c` (test)
2. **Task 2 (GREEN): construcción tipada + desreferencia en los 2 probes + cableado a CI** — `b1654af` (feat)

_TDD: RED verificado antes del GREEN — **5 failed / 3 passed**. Los 3 verdes son los que no dependen de la cadena: presencia de los dos probes por nombre, el gate de `try` (vacuamente cierto sin accesos) y el de cero-HTTP-adicional (la propiedad ya valía; el lock la congela). Los 5 rojos nombraron los dos probes sin `Posicion.from_api`, los dos sin desreferencia, el piso por probe, el agregado y las dos colecciones `posiciones` sin encadenar. Tras el GREEN: 8 passed._

## Files Created/Modified

- `verification/test_main_higyrus_deep_chain.py` (nuevo, 8 tests, ~370 líneas). Constantes de módulo: `_DRIVER` = `main_higyrus.py`; `_ALIAS_NAMES` = `{diasParking}`; `_READ_PROBES` = los dos nombres de probe; `_MIN_CHAINED_ACCESSES_BY_PROBE` = `{sync: 1, async: 1}` con `_MIN_CHAINED_ACCESSES = sum(...)`; `_CHAINED_COLLECTIONS_BY_PROBE` = `{posiciones}` para ambos; `_TYPED_CONSTRUCTOR = ("Posicion", "from_api")`; `_HTTP_CALL_NAMES` + `_MAX_HTTP_CALLS_PER_PROBE = 1`. Helpers `_protected_node_ids` y `_chain_reaches` copiados verbatim del analog; helpers nuevos `_typed_constructor_calls` y `_http_calls`. El driver se `ast.parse`-a, nunca se importa (`load_dotenv` de import-time); el archivo no contiene ningún `import main_higyrus`.
- `main_higyrus.py` — dos sitios byte-paralelos, inmediatamente después de la normalización de `raw` a lista y **dentro del cuerpo de un `try`**:
  - `posiciones = [Posicion.from_api(row) for row in raw]`
  - `parking_entries = sum(len(posicion.parking) for posicion in posiciones)`
  - `primer_dias_parking = next((posicion.parking[0].diasParking for posicion in posiciones if posicion.parking), None)`
  - `except _RESIDUAL_PROBE_EXCEPTIONS` → `append_finding(class_="ERROR-MAP")` + `ProbeResult(..., "FINDING", ...)`, siguiendo la escalera existente del probe.
  - Los dos `ProbeResult` de PASS de cada probe (rama vacía y rama poblada) incorporan `parking={parking_entries}`; la rama poblada suma además `diasParking={primer_dias_parking}`. Ningún nombre de probe cambió (clave de findings).
- `.github/workflows/ci.yml` — `verification/test_main_higyrus_deep_chain.py` agregado a la lista explícita del step "driver locks" del job `lint` (ahora 10 archivos).

## Decisions Made

- **El `try` es nuevo, y tenía que serlo.** La normalización de `raw` (`if raw is None: raw = []` y el chequeo de `isinstance`) vive **fuera** del `try` original, que sólo envuelve el helper de request crudo. Meter la cadena en el `try` original habría exigido mover la normalización dentro, cambiando la ruta de las tres ramas de `except` existentes. El plan autoriza explícitamente un `try` propio y fija la condición dura: toda desreferencia en el **cuerpo** de un `try`, nunca en `except`/`else`/`finally`. `test_every_chained_access_sits_inside_the_probe_try_body` lo verifica con `_protected_node_ids`.
- **`HigyrusDecodeError` no se captura localmente, a propósito.** Es subclase de `HigyrusClientError`, que no está en `_RESIDUAL_PROBE_EXCEPTIONS` (`httpx.HTTPError`, `OSError`, `AttributeError`, `TypeError`, `ValueError`, `KeyError`). Un raise de modo estricto desde `from_api` sigue viajando al decorador `probe_context(..., decode_error=HigyrusDecodeError, on_decode_error=_shape_probe_result_pair)` y produce el finding `SHAPE` de siempre. Capturarlo acá habría minteado un segundo finding bajo otro título y roto el `idempotent_by_title` del lock 10 — el mismo error que el docstring de `_shape_probe_result` documenta.
- **Guarda por veracidad, nunca `is None`.** `Posicion.parking` está declarado `list[Parking]` sin `| None`: con la clave ausente o `null` el Null Object entrega `[]`. Una guarda de nulidad sería código muerto demostrable y contradiría el tipo. Misma decisión que 39-04.
- **`next(...)` sobre generador con default `None`, no indexado defensivo.** Produce exactamente una desreferencia de `diasParking` dentro de una comprensión que itera el `Name` local `posiciones` — que es lo que `test_every_fetched_position_collection_is_chained` (WR-06) exige — y devuelve `None` limpio cuando ninguna fila trae parking, que es el caso normal con `incluirParking=False`.
- **`incluirParking` no se tocó.** Flipearlo alteraría la forma de la respuesta y quemaría el baseline write-once de `get_posiciones` por deriva de schema. La consecuencia (rama poblada no ejercitada en vivo) quedó escrita en el sitio y marcada para el censo.
- **La captura de payloads crudos por función que `main()` usa para el mapa de tipos y el snapshot de schema quedó intacta:** ambos probes siguen devolviendo `raw` como segundo elemento de la tupla. La cadena tipada se **suma**, no reemplaza.

## Deviations from Plan

Ninguna de contenido. Dos precisiones de ubicación, ambas ya anticipadas por el prompt de ejecución y por 39-04:

1. **La allowlist explícita está en el job `lint`** (step de driver locks, `ci.yml:79-90`), no en el job `test`. Verificado por `grep` de `test_main_iol_deep_chain.py` antes de editar, como indicaba la corrección conocida del plan.
2. **El `try` de la cadena es nuevo** en vez del existente, por la posición de la normalización de `raw` — rama explícitamente contemplada por el `<action>` del plan.

Cero dependencias nuevas (T-39-SC). Cero probes nuevos, cero llamadas HTTP nuevas, cero cambios en las escaleras de excepciones, cero renombres de probe, cero deleciones en los dos commits.

## Issues Encountered

Ninguno. `ruff check`, `ruff format --check` y `mypy` salieron limpios a la primera sobre los tres archivos tocados; no hizo falta reformatear (a diferencia de 39-04).

## Verificación

| Criterio | Resultado |
|---|---|
| `pytest -q verification/test_main_higyrus_deep_chain.py` (RED, Task 1) | 5 failed / 3 passed |
| `pytest -q verification/test_main_higyrus_deep_chain.py` (GREEN, Task 2) | 8 passed |
| `pytest -q packages/higyrus-client` | 303 passed |
| `pytest -q verification/test_main_higyrus_skip_line_shape.py` (39-01 intacto) | 8 passed |
| `pytest -q verification/test_main_higyrus_uses_single_client_instance.py` | 1 passed |
| Allowlist completa de CI (10 archivos, incluido el nuevo) | 98 passed |
| `ruff check .` / `ruff format --check .` / `mypy` | 0 / 276 files formatted / Success: no issues found in 75 source files |
| `grep -c 'test_main_higyrus_deep_chain.py' .github/workflows/ci.yml` | 1 (≥ 1) |
| `grep -c 'Posicion.from_api' main_higyrus.py` | 2 (exactamente 2: sync + async) |
| `grep -c 'import main_higyrus' verification/test_main_higyrus_deep_chain.py` | 0 |
| `grep -c 'sum(_MIN_CHAINED_ACCESSES_BY_PROBE.values())'` | 1 |
| Deletions en los 2 commits de tarea | ninguna |
| Untracked tras los 2 commits | ninguno |

## TDD Gate Compliance

Secuencia completa en el historial: `636619c` `test(39-05): ...` (RED) → `b1654af` `feat(39-05): ...` (GREEN). Sin fase REFACTOR (no hizo falta). El RED se corrió y se verificó rojo **por la razón correcta** antes de escribir una línea de implementación: los mensajes nombraron los dos probes sin `Posicion.from_api`, los dos sin desreferencia, y las dos colecciones `posiciones` sin encadenar.

## Known Stubs

Ninguno. Las desreferencias son código en el camino caliente de ambos probes.

Lo que el lock **no** puede afirmar, y que el censo del 39-08 debe registrar como limitación medida:

- **La rama poblada de `parking` no se ejercita en vivo.** El probe envía `incluirParking=False` por decisión explícita (baseline write-once), así que la corrida real devolverá `parking=0 diasParking=None` incluso si el host resolviera. Esa evidencia la aporta la suite mockeada del plan 39-02, `packages/higyrus-client/tests/test_deep_chain_edges.py`.
- **El host vendor de higyrus no resuelve por DNS** (`LIVE-HIGY-33`, re-medido en la sesión de research de esta fase). El plan 39-07 re-sondea al inicio (asunción A2: re-medir, no asumir) y, si sigue sin resolver, emite `SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-33` por la rama que dejó el plan 39-01.

## Threat Flags

Ninguno. Las cuatro superficies tocadas ya estaban en el `<threat_model>` del plan:

- **T-39-16** (eslabón roto fuera del `try`) — mitigado: las dos desreferencias viven en el cuerpo de un `try` y `test_every_chained_access_sits_inside_the_probe_try_body` lo pinea con `_protected_node_ids`, que excluye `except`/`else`/`finally`.
- **T-39-17** (conteos de posiciones en el detalle del `ProbeResult`) — mitigado: lo que se agrega es un **conteo** de entradas de parking y un entero de días. Cero identificadores de cuenta, cero montos, cero credenciales; el driver ya emite todo por `safe_print(..., secrets=[...])`.
- **T-39-18** (doble emisión por construir el wrapper dos veces) — accepted, tal como el plan lo dispuso: `from_api` enruta por el mismo sink, `DivergenceHandler.seen` deduplica por 4-tupla y `append_finding` usa `idempotent_by_title=True`.
- **T-39-19** (lock sin cablear) — mitigado: la entrada en la allowlist ocurrió en el mismo commit que volvió verde el lock (`b1654af`), verificada por `grep -c`.
- **T-39-SC** — cero dependencias nuevas.

## Next Phase Readiness

- **higyrus ya no es la asimetría de la fase.** Los cuatro drivers verificables (iol, matriz, market-data, higyrus) tienen ahora al menos una cadena `.modelo.campo` real gastada en su sitio de probe, con lock AST y cableada a CI. SC-1 queda satisfecho en su mitad de código para los cuatro.
- **El lock es estructural, no de corrida.** Garantiza que el código existe, está bien ubicado y no cuesta un request extra; no garantiza que la API haya devuelto una posición. Con higyrus bloqueado por DNS eso es precisamente lo que el plan buscaba: un artefacto verificable en vez de un aplazamiento.
- **Insumo directo para el censo (39-08):** el detalle de PASS de ambos probes transcribe `parking=N` (y `diasParking=V` en la rama poblada), leíble del stdout sin instrumentación extra. Y la limitación de `incluirParking` está escrita en el código con destino explícito al censo — el 39-08 debe copiarla, no re-derivarla.
- **`Parking` sigue siendo forma inobservada.** Ningún capture registró una entrada poblada. Una divergencia de tipo sobre `diasParking` en una eventual corrida en vivo sería esa asunción corrigiéndose sola, no un defecto del modelo.

## Self-Check: PASSED

- `verification/test_main_higyrus_deep_chain.py` — FOUND en disco.
- Commit `636619c` — FOUND en el historial.
- Commit `b1654af` — FOUND en el historial.

---
*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo*
*Completed: 2026-08-30*
