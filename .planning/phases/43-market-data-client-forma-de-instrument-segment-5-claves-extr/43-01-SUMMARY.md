---
phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr
plan: 01
subsystem: api
tags: [market-data-client, models, safemodel, dataclasses, shape-reconciliation, pytest]

# Dependency graph
requires:
  - phase: 42-live-verification
    provides: "la lectura fresca del wire del 2026-08-31 (42-WIRE-READ.md seccion 2, 50 filas de /instruments y 4 de /instruments/segments, findings F-205..F-218)"
  - phase: 33-live-typ-01
    provides: "el desenvolvimiento del sobre de /instruments y /instruments/segments en _core.py, sin el cual las filas nunca llegaban al modelo"
  - phase: 27-live-mut-01
    provides: "el precedente D-22 de Symbol.marketId — alias camelCase aditivo con espejo en from_api, copiado verbatim aca"
provides:
  - "Instrument reconciliado: 11 campos (10 medidos del wire + el alias camelCase deprecado), con override propio de from_api que espeja market_id sobre marketId"
  - "Segment reemplazado por completo: segment: str + live_instruments: int — get_segments() deja de devolver filas de tres strings vacios"
  - "6 archivos de test re-derivados al key-set medido con valores sinteticos; ninguno renombrado ni borrado"
  - "el conjunto exacto de clases de market_data_client.models con override propio de from_api pasa a tres: Instrument, MarketDataSnapshot, Symbol"
affects: [43-02, 43-03, 44-pub-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "alias camelCase aditivo con espejo pre-walker (D-04 / precedente D-22)"
    - "fixture de test con key-set y tipos medidos y valores sinteticos (el capture crudo esta gitignored)"

key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/tests/test_reference_models.py
    - packages/market-data-client/tests/test_reference_core.py
    - packages/market-data-client/tests/test_reference_client.py
    - packages/market-data-client/tests/test_reference_async_client.py
    - packages/market-data-client/tests/test_decode.py
    - packages/market-data-client/tests/test_reference_envelope_unwrap.py

key-decisions:
  - "Instrument.active se declara bool | None = None (D-03): el wire mando null en 50/50 filas medidas; un bool plano habria convertido una extra medida en una missing permanente sobre cada lectura de catalogo"
  - "Instrument.marketId se conserva como alias aditivo deprecado con espejo en from_api (D-04), nunca renombrado — es superficie publicada"
  - "Segment se reemplaza por completo en vez de alias-mapearse (D-06): D-22 cubre UNA clave con variante de spelling, y marketSegmentId vs segment son nombres distintos"
  - "instrumentType se remueve como cambio no-breaking (D-05/D-13): el wire nunca mando esa clave, asi que toda instancia liberada la leia como cadena vacia"
  - "Las fixtures llevan valores sinteticos con key-set y tipos reales: el capture crudo de la Phase 42 esta gitignored (PII) y un test que lo abriera fallaria en CI con FileNotFoundError"

patterns-established:
  - "Espejo de alias pre-walker: from_api copia el dict (nunca muta el del caller) y solo RELLENA una clave camelCase ausente — un valor explicito del payload siempre gana"
  - "Aserciones de VALOR sobre las filas desenvueltas del sobre, no solo de conteo y tipo — un test que solo hace isinstance pasa vacuamente sobre una fila vacia"

requirements-completed: [SHAPE-01]

# Metrics
duration: 15min
completed: 2026-09-01
status: complete
---

# Phase 43 Plan 01: Forma reconciliada de `Instrument` y `Segment` Summary

**`Instrument` gana los 6 campos wire-only medidos mas `active` nullable y espeja `market_id` sobre su alias camelCase deprecado; `Segment` se reemplaza por `{segment, live_instruments}` y `get_segments()` deja de devolver filas enteramente vacias.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-01T00:40:17Z
- **Completed:** 2026-09-01T00:55:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- `Instrument` pasa de 5 campos declarados a 11: los tres que ya estaban en el wire (`symbol`, `segment`, `expired`), los seis que el servidor mandaba y el cliente descartaba en silencio (`market_id`, `currency`, `days_to_maturity`, `maturity`, `outright`, `subscribed`), `active: bool | None` y el alias `marketId` conservado.
- `Instrument.from_api` es ahora el tercer override de la clase en el paquete: espeja `market_id` sobre `marketId` **antes** de que el walker vea el payload, asi que el alias deja de estar permanentemente vacio y no dispara un record `extra` espurio.
- `Segment` se reemplaza por completo. Los tres campos declarados eran **disjuntos** del key-set del wire, asi que toda fila que un consumidor liberado leyo fue tres cadenas vacias. Ahora lleva `segment` y `live_instruments` poblados.
- Los seis archivos de test afectados quedaron re-derivados al key-set medido con valores sinteticos. **Ninguno se renombro ni se borro** para que la suite siguiera pasando.
- Los cuatro tests de desenvolvimiento de sobre (sync y async, instruments y segments) assertan ahora VALORES de fila, no solo conteo y tipo — el criterio 2 de la fase queda reproducible desde la suite sola.

## Tabla de disposicion campo por campo (input para el criterio 1 de la fase)

### `Instrument` — `GET /instruments` (50 filas medidas, 2026-08-31)

| Campo | Tipo final | Disposicion | Decision | Nota |
|---|---|---|---|---|
| `symbol` | `str` | **mantener** | D-01 | medido en 50/50 filas |
| `segment` | `str` | **mantener** | D-01 | medido en 50/50 filas |
| `expired` | `bool` | **mantener** | D-01 | medido en 50/50 filas |
| `marketId` | `str` | **alias aditivo** | D-04 | camelCase deprecado, NO renombrado (superficie publicada); poblado por el espejo de `from_api`; remocion programada para el proximo MAJOR |
| `market_id` | `str` | **agregar** | D-02 | wire-only medido; la ortografia real del wire |
| `currency` | `str` | **agregar** | D-02 | wire-only medido; antes descartado |
| `days_to_maturity` | `int` | **agregar** | D-02 | wire-only medido; antes descartado |
| `maturity` | `str` | **agregar** | D-02 | wire-only medido; antes descartado |
| `outright` | `bool` | **agregar** | D-02 | wire-only medido; antes descartado |
| `subscribed` | `bool` | **agregar** | D-02 | wire-only medido; antes descartado |
| `active` | `bool \| None = None` | **agregar (nullable)** | D-03 | `null` en 50/50 filas; el miembro `bool` de la union es una ASUNCION DECLARADA, autocorrectiva via el censo de divergencias |
| `instrumentType` | — | **remover** | D-05 | el wire nunca mando la clave; toda instancia liberada la leia `""` → remocion no-breaking (argumento D-13) |

Orden de declaracion (load-bearing): los diez sin default primero, `active` ultimo y unico con default.

### `Segment` — `GET /instruments/segments` (4 filas medidas, 2026-08-31)

| Campo | Tipo final | Disposicion | Decision | Nota |
|---|---|---|---|---|
| `segment` | `str` | **agregar** | D-06 | medido en 4/4 filas |
| `live_instruments` | `int` | **agregar** | D-06 | medido en 4/4 filas |
| `marketSegmentId` | — | **remover** | D-06 | key-set declarado y medido DISJUNTOS → ninguna fila liberada pudo tener valor poblado |
| `marketId` | — | **remover** | D-06 | idem |
| `description` | — | **remover** | D-06 | idem |

`Segment` **no** se alias-mapea bajo D-22: la precondicion de ese precedente es UNA misma clave con variante de spelling camelCase/snake_case, y `marketSegmentId` vs `segment` son nombres distintos. Rechazo explicito registrado en el docstring de la clase. No lleva override de `from_api`.

## Conteo de tests del paquete

| Momento | Tests | Resultado |
|---|---|---|
| Antes (baseline en HEAD del plan) | 711 | 711 passed |
| Despues del Task 1 (RED) | 717 colectados | 8 failed, 20 passed en el archivo tocado |
| Despues del Task 3 (final) | **717** | 717 passed |

Delta neto: **+6 tests** (los seis nuevos de `test_reference_models.py`). Los 9 re-derivados conservan su nombre y su conteo.

## Confirmacion de alcance (D-14 / D-16)

Verificado con `git diff --stat 396c717..HEAD` — el diff completo del plan toca **7 archivos** y **ninguno** de los siguientes:

| Archivo | Estado |
|---|---|
| `packages/market-data-client/src/market_data_client/client.py` | **sin tocar** (D-14: los parsers de `_core.py` son field-agnostic; la correccion llega a la superficie sync con cero cambios de fuente) |
| `packages/market-data-client/src/market_data_client/aio.py` | **sin tocar** (idem para la superficie async; los gemelos sync/async de los tests lo miden) |
| `main_market_data.py` | **sin tocar** (D-16; el sitio `:1541-1542` queda como seguimiento marcado — ver abajo) |
| `packages/market-data-client/pyproject.toml` (version) | **sin tocar** |
| `packages/market-data-client/src/market_data_client/__init__.py` (`__version__`) | **sin tocar** |
| `uv.lock` | **sin tocar** |
| `packages/market-data-client/src/market_data_client/_core.py` | **sin tocar** (el docstring de `parse_segments_response` pertenece al plan 43-02/03) |
| `packages/market-data-client/src/market_data_client/models.py` `__all__` | **sin tocar** (pertenece al plan 43-02, que agrega `FeedSubscription`) |

## Task Commits

1. **Task 1: RED — field-set exacto, par de alias-mirror y fixtures medidas** — `52fe007` (test)
2. **Task 2: GREEN — reemplazar `Instrument` y `Segment` en `models.py`** — `2a3de99` (feat)
3. **Task 3: re-derivar los 5 archivos de test restantes + aserciones de valor del criterio 2** — `1caee63` (test)

No hubo commit de REFACTOR: el codigo salio en su forma final del GREEN (es una copia verbatim del analog `Symbol`, sin deuda que limpiar).

## Files Created/Modified

- `packages/market-data-client/src/market_data_client/models.py` — `Instrument` (11 campos + override `from_api` con el espejo D-04) y `Segment` (2 campos, sin override) reconciliados; docstrings de provenance reales (lectura del 2026-08-31), justificacion `| None` de `active` bajo doctrina option-b, y el argumento de remocion no-breaking para `instrumentType` y para los tres campos viejos de `Segment`.
- `packages/market-data-client/tests/test_reference_models.py` — fixtures `_WIRE_INSTRUMENT_ROW` / `_WIRE_SEGMENT_ROW`, 6 tests nuevos (dos de field-set exacto, el par de alias-mirror, dos de fila poblada), T1/T2 re-derivados en su lugar.
- `packages/market-data-client/tests/test_reference_core.py` — los dos parsers de coleccion re-derivados; el de segments deja de pasar vacuamente.
- `packages/market-data-client/tests/test_reference_client.py` — bodies de instruments y segments al key-set medido; aserciones de request intactas.
- `packages/market-data-client/tests/test_reference_async_client.py` — gemelo async, simetrico linea a linea.
- `packages/market-data-client/tests/test_decode.py` — el test de `missing` gana la mitad "el espejo elimina el record"; el de `extra` usa el key-set real de `Segment`; `overriding == {"Instrument", "MarketDataSnapshot", "Symbol"}`.
- `packages/market-data-client/tests/test_reference_envelope_unwrap.py` — helper `_assert_instrument_row_is_populated` compartido por los gemelos sync/async, aserciones de valor en los cuatro tests de sobre, y `test_bare_list_bodies_still_parse` re-derivado conservando su `marketId` explicito (el caso valido de "una fixture vieja gana sobre el espejo").

## Decisions Made

Ninguna decision nueva: las seis decisiones locked de la fase (D-01..D-06) mas la mitad de fixtures de D-12 se implementaron tal como el plan las especifica. Las dos elecciones de redaccion que el plan dejaba abiertas se resolvieron copiando el analog:

- El docstring del `| None` de `active` sigue el patron de `FeedIngestor.last_error` (asuncion declarada sobre el miembro no observado de la union), no el de `FeedPipeline.last_write_at`.
- En `test_reference_envelope_unwrap.py` las aserciones de valor de los gemelos sync/async se factorizaron en un helper de modulo en vez de duplicarse doce lineas — mantiene la simetria sync/async por construccion en vez de por revision.

## Deviations from Plan

None - plan executed exactly as written.

Los tres tasks corrieron en el orden y con la disposicion planeados; no se dispararon las reglas 1-4 de desviacion, no hubo gates de autenticacion y no se instalo ni actualizo ninguna dependencia externa (T-43-SC confirmado como no-op: `uv.lock` sin tocar).

## Issues Encountered

- El criterio de aceptacion `grep -c 'verification/captures'` igual a `0` (T-43-02) fallo en la primera pasada del Task 1: el comentario de provenance de las fixtures citaba la ruta del directorio gitignored **como texto**, sin abrirlo. Se reescribio el comentario para nombrar el hecho ("los captures crudos de la Phase 42 estan gitignored") sin la ruta literal. Corregido antes del commit del Task 1; el grep devuelve `0`.
- `uv run pytest -q --no-cov` sobre el **monorepo entero** (fuera de lo que el plan pide) excedio los 10 minutos y se aborto. La verificacion del plan es por paquete (`packages/market-data-client`) y corre en ~1 s; los gates globales que el plan si exige (`mypy` sobre `src`, `mypy` sobre los tests del paquete, `ruff check .`, `ruff format --check .`, `tools/check_surface_types.py`) corrieron todos en verde. El comportamiento del suite global no fue alterado por este plan (ningun archivo fuera de `packages/market-data-client/` fue tocado).

## Verificacion final

| Gate | Comando | Resultado |
|---|---|---|
| Suite del paquete | `uv run pytest packages/market-data-client -q --no-cov` | 717 passed |
| Surface types | `uv run python tools/check_surface_types.py` | `0 violations` |
| mypy (src) | `uv run mypy` | Success, 75 files |
| mypy (tests del paquete) | `uv run mypy packages/market-data-client/tests` | Success, 36 files |
| ruff lint | `uv run ruff check .` | All checks passed |
| ruff format | `uv run ruff format --check .` | 279 files already formatted |
| Field set `Instrument` | `dataclasses.fields(Instrument)` | los 11 nombres esperados |
| Field set `Segment` | `dataclasses.fields(Segment)` | `['live_instruments', 'segment']` |
| Espejo de alias | `Instrument.from_api({...})` con y sin `marketId` explicito | `ROFX` / `LEGACY` — rellena una clave ausente, respeta una explicita |

## Seguimiento marcado — NO corregido aca

`main_market_data.py:1541-1542` dereferencia `.marketSegmentId`, el campo que D-06 remueve. Sigue **sin tocar** por D-16 (el alcance de este plan es `models.py` + tests). Ningun gate estatico lo detecta (`mypy` con `files = ["packages/*/src"]`, hook de pre-commit con `files: ^packages/.*/src/`) y el sitio vive dentro de un `try/except Exception` que lo degrada a un FINDING silencioso de handler en vez de un crash. Su disposicion se documenta en `43-DISPOSITION.md` (plan 43-03, Task 2) y como entrada de backlog en `ROADMAP.md`.

## Known Stubs

Ninguno. `Instrument` y `Segment` quedan cableados de punta a punta contra el wire medido, y las aserciones de valor de `test_reference_envelope_unwrap.py` lo demuestran sobre las dos superficies.

## Threat Flags

Ninguna superficie de seguridad nueva. Los cambios son declaraciones de dataclass y aserciones de test dentro del limite de confianza ya registrado (`vendor HTTP response -> SafeModel.from_api`). T-43-01 (Tampering sobre el espejo del alias) queda mitigado y pinneado por `test_instrument_explicit_camel_case_payload_key_still_wins`; T-43-02 (fixtures vs. captures con PII) queda mitigado y verificado por `grep -c 'verification/captures'` igual a `0`; T-43-05 (orden de campos) queda verificado por la coleccion de pytest en verde.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- El plan 43-02 puede arrancar: toca `Symbol.note` (D-10), `FeedSubscription` (D-08), `FeedIngestor` (D-09), `HealthFeed.symbols_never_delivered` (D-11) y los cuatro sitios de `__all__` — todos disjuntos de lo que este plan modifico. `models.__all__` quedo deliberadamente sin tocar para que la edicion de exports viaje entera en 43-02.
- El plan 43-03 recibe la tabla de disposicion campo por campo de arriba como input directo para el criterio 1 de la fase, y el item de seguimiento de `main_market_data.py:1541-1542` para `43-DISPOSITION.md`.
- **No** se bumpeo ninguna version ni se toco `uv.lock`: el release es la Phase 44 por precedente lockeado.

## Self-Check: PASSED

Los 7 archivos de fuente/test declarados existen en disco y los 3 hashes de commit de tarea (`52fe007`, `2a3de99`, `1caee63`) existen en el historial de git.

---
*Phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr*
*Completed: 2026-09-01*
