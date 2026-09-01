---
phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr
plan: 02
subsystem: api
tags: [market-data-client, models, safemodel, dataclasses, health-feed, divergence-census, pytest, tdd]

# Dependency graph
requires:
  - phase: 43-01
    provides: "models.py reconciliado de Instrument/Segment y models.__all__ deliberadamente sin tocar, para que la edicion de exports viajara entera aca"
  - phase: 42-live-verification
    provides: "la corrida en vivo del 2026-08-31 que produjo los findings F-67..F-71 / F-87..F-89 / F-202 — el blob medido del que sale todo el key-set de este plan"
  - phase: 35-nobj
    provides: "NOBJ-02: un modelo anidado no-opcional colapsa al Null Object bajo SILENT_SINK sin emitir record — la mecanica que permite tipar subscription sin flip extra->missing"
provides:
  - "FeedSubscription: modelo anidado tipado de 15 campos que devuelve ingestor.subscription al alcance del walker (antes un punto ciego permanente del censo)"
  - "Las 5 claves extra medidas declaradas con el tipo que su evidencia respalda; cero divergencias sobre el payload medido"
  - "_MEASURED_HEALTH_FEED_43 + _keys_recursive: la asercion fixture-subconjunto-de-medicion del criterio 4, sin tocar ningun baseline write-once"
  - "El conjunto cerrado de Optionals de health pasa de 2 a 4, con evidencia medida por par"
affects: [43-03, 44-pub-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "modelo anidado tipado en vez de mapping opaco (walk_field no tiene rama para mappings: un mapping es un punto ciego permanente del censo)"
    - "asuncion declarada sobre el tipo de elemento de una lista vacia medida, espejando a su hermana poblada"
    - "shim de import por getattr durante RED + refactor a import por nombre en GREEN, para que un RED valido nunca sea un fallo de COLECCION"

key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/tests/test_core.py
    - packages/market-data-client/tests/test_reference_models.py
    - packages/market-data-client/tests/test_models.py

key-decisions:
  - "FeedIngestor.last_error_age_seconds y .last_error_at se declaran nullables (D-09) porque estan AUSENTES del baseline sano y PRESENTES junto a un last_error poblado: son condicionales a que exista un error, y declararlas planas emitiria un missing en cada llamada sana"
  - "HealthFeed.symbols_never_delivered se declara PLANO (D-11) pese a que emite un missing contra la fixture congelada: la clave falta solo en el baseline stale del 2026-07-31 y esta poblada en las tres capturas posteriores; un Optional sobre-declarado absorberia un futuro null sin dejar record"
  - "subscription se tipa como modelo anidado no-opcional, nunca como dict[str, Any] ni como FeedSubscription | None: la primera forma es un punto ciego del walker y ambas estan redeneadas por check_surface_types"
  - "unconfirmed_symbols se tipa list[str] como ASUNCION DECLARADA — el wire mando la lista vacia; una eleccion equivocada aflora ruidosamente como record type en el proximo censo"
  - "FeedSubscription se enrola tambien en el lock de Optionals exactos (T-43-07), no solo en los tres parametrizados que el plan nombra"

patterns-established:
  - "Un unico _HEALTH_MODEL_CLASSES respalda los cuatro sitios que assertan sobre el conjunto cerrado de modelos de health — el modo de fallo que evita es que un modelo nuevo quede enrolado en tres locks y silenciosamente afuera del cuarto"
  - "Todo | None nuevo llega con su parrafo de evidencia medida citando el finding por ID, y con su contra-ejemplo (el campo hermano que NO se declara nullable y por que)"

requirements-completed: [HARN-02]

# Metrics
duration: 6min
completed: 2026-09-01
status: complete
---

# Phase 43 Plan 02: Las 5 claves `extra` medidas, tipadas Summary

**`ingestor.subscription` deja de ser un `extra` opaco y pasa a ser `FeedSubscription`, un modelo anidado de 15 campos que el walker sí camina; las otras cuatro claves medidas se declaran con el tipo que su evidencia respalda, y el payload medido del 2026-08-31 decodifica con CERO records de divergencia.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-09-01T01:00:13Z
- **Completed:** 2026-09-01T01:05:39Z
- **Tasks:** 2 planeados + 1 REFACTOR (ver Deviations)
- **Files modified:** 4

## Accomplishments

- Las cinco claves que el censo reportaba `extra` corrida tras corrida están declaradas y decodifican tipadas. El payload medido produce **cero** records — ni `extra`, ni `missing`, ni `type` —, probado por `test_measured_health_feed_payload_produces_zero_divergence_records` y no meramente afirmado.
- `FeedSubscription` devuelve un sub-objeto entero al alcance del censo. Antes, `ingestor.subscription` era **un** record `extra` y sus 15 campos no existían para el walker; un `dict[str, Any]` habría dejado ese punto ciego en su lugar de forma permanente, porque `walk_field` no tiene rama para mappings y cae al `return value` final sin caminar ni reportar.
- Ninguna de las cinco emite `missing` sobre un payload sano. El único `missing` que aparece es el de `symbols_never_delivered` contra la fixture congelada del 2026-07-31, y está pinneado con la explicación mecánica de por qué es correcto.
- El criterio 4 queda cerrado sin tocar un solo baseline write-once: `_MEASURED_HEALTH_FEED_43` es una fixture nueva, `_CAPTURED_HEALTH_FEED` sigue byte-idéntica, y `test_captured_payloads_match_the_committed_live_schemas` sigue verde sin edición.
- El conjunto cerrado de Optionals de health pasó de 2 a 4 con evidencia medida por par, y `FeedSubscription` quedó enrolado en ese lock además de en los tres parametrizados.

## Tabla de las 5 claves (input para el criterio 3 de la fase)

| Clave | Tipo final | Decision | Evidencia medida que lo respalda |
|---|---|---|---|
| `FeedIngestor.subscription` | `FeedSubscription` (modelo anidado, **no** opcional) | D-08 | `F-70` (sync): `- -> dict at FeedIngestor.ingestor.subscription`. El blob de `F-71`/`F-202` trae las 15 claves pobladas. No-opcional porque la ausencia ya está cubierta por el Null Object (NOBJ-02) y porque `D-NO-01` de `check_surface_types.py` reddenea `Model \| None` en clase exportada |
| `FeedIngestor.last_error_age_seconds` | `int \| None = None` | D-09 | `F-68` (sync) / `F-88` (async). **AUSENTE** del baseline sano del 2026-07-31 (donde `last_error` es `null`), **PRESENTE** en toda captura posterior junto a un `last_error` poblado → condicional a que exista un error |
| `FeedIngestor.last_error_at` | `str \| None = None` | D-09 | `F-69` (sync) / `F-89` (async). Misma condicionalidad, mismo par de estados medidos |
| `HealthFeed.symbols_never_delivered` | `int` (**plano**) | D-11 | `F-67` (sync) / `F-87` (async). Ausente **solo** del baseline stale del 2026-07-31; poblada como `int` en las tres capturas posteriores → doctrina option-b: un `Optional` sobre-declarado absorbería un futuro `null` sin dejar record |
| `Symbol.note` | `str \| None = None` | D-10 | `F-140` (sync) / `F-109` (async), ambos sobre `/symbols/{symbol_id}`. Presente en los acks de escritura, ausente de las filas de `GET /symbols`. Un solo modelo sirve los cuatro endpoints → condicional por forma de respuesta, mismo argumento que `created_at`/`updated_at` |

Los 15 campos de `FeedSubscription` van todos planos: las 15 volvieron pobladas en la captura medida. La única asunción declarada es el **tipo de elemento** de `unconfirmed_symbols`, que llegó como lista vacía y se tipa `list[str]` espejando a su hermana poblada `quarantined_symbols`; una elección equivocada aflora como record `type` en el próximo censo, no en silencio.

## La lista exacta de records que T14 asserta ahora

`test_health_feed_from_api_drops_an_undeclared_key_and_reports_it_once` pasó de un elemento a dos:

```python
assert [(r.field_path, r.divergence) for r in records] == [
    (".brand_new_wire_key", "extra"),
    (".symbols_never_delivered", "missing"),
]
```

El orden es el del walker, no una preferencia: `walk_model` calcula las claves sobrantes primero (ordenadas) y recién después camina los campos declarados en orden de declaración.

**Por qué ese único `missing` es correcto.** Este test maneja la fixture **congelada** del 2026-07-31, que es anterior a las cuatro claves de health que la corrida del 2026-08-31 midió. `symbols_never_delivered` es el único campo nuevo declarado **plano** (D-11), así que contra un payload que no trae la clave la rama escalar de `walk_field` llama al sink con `_kind_of(None) == "missing"`. Bajo la doctrina option-b eso es la señal que se quería: la clave está en el wire real, la fixture es vieja, y el record lo dice. Declararla `int | None` habría hecho desaparecer ese record **y** el de cualquier `null` futuro.

**Por qué los otros tres campos nuevos no contribuyen nada** — y esto es el criterio 3 mostrado mecánicamente, no afirmado:

- `last_error_age_seconds` y `last_error_at` son `| None`, y la rama `Union` de `walk_field` retorna temprano **sin** llamar al sink (`_decode.py:437-444`).
- `subscription` es un modelo anidado no-opcional, así que la clave ausente colapsa al Null Object bajo `SILENT_SINK` (`_decode.py:495-503`, NOBJ-02).

Si alguna vez aparece un `missing` de cualquiera de los dos campos de D-09 en esa lista, es que alguien los declaró planos contra la evidencia medida. El test falla y lo dice.

## Confirmacion de alcance (D-16)

`git diff --stat 1bc82b1~1..HEAD` — el diff acumulado del plan toca **4 archivos** y **ninguno** de los siguientes:

| Archivo | Estado |
|---|---|
| `packages/market-data-client/src/market_data_client/__init__.py` | **sin tocar** (incluido el `__version__` y el `__all__` del paquete — ver seguimiento marcado) |
| `packages/market-data-client/src/market_data_client/client.py` | **sin tocar** |
| `packages/market-data-client/src/market_data_client/aio.py` | **sin tocar** |
| `packages/market-data-client/src/market_data_client/_core.py` | **sin tocar** |
| `packages/market-data-client/pyproject.toml` | **sin tocar** (sitio de versión 2 de 3) |
| `uv.lock` | **sin tocar** — cero paquetes externos instalados o actualizados (T-43-SC confirmado como no-op) |
| `.planning/verification/schemas/market-data-client/*.json` | **sin tocar** — `git status --porcelain` sobre ese directorio no produjo salida en ninguno de los tres commits (D-25) |
| `main_market_data.py` | **sin tocar** |

Los tres sitios de versión (`pyproject.toml`, `__init__.py::__version__`, el tag) quedan intactos: el release es la Phase 44 por precedente lockeado.

## Task Commits

1. **Task 1: RED — fixture medida, helper de subconjunto y los tests de evidencia** — `1bc82b1` (test)
2. **Task 2: GREEN — FeedSubscription, los tres campos condicionales, el campo plano y `Symbol.note`** — `327b3ce` (feat)
3. **REFACTOR — retirar el shim de import de la mitad RED** — `8b4de5e` (refactor)

Secuencia de gates TDD completa: `test(...)` → `feat(...)` → `refactor(...)`.

## Files Created/Modified

- `packages/market-data-client/src/market_data_client/models.py` — `FeedSubscription` nueva (15 campos, sin override de `from_api`, sin `received_at`, sin campo mapping, declarada entre `FeedPipeline` y `FeedIngestor`); `FeedIngestor` gana `subscription` (antes del primer campo con default) más los dos condicionales de D-09; `HealthFeed` gana `symbols_never_delivered`; `Symbol` gana `note`; el bloque de veredicto de nulabilidad re-derivado de dos a cuatro Optionals con la evidencia por par; `models.__all__` gana `"FeedSubscription"` en orden alfabético estricto.
- `packages/market-data-client/tests/test_core.py` — `_MEASURED_HEALTH_FEED_43` (key-set y tipos del blob `F-202`/`F-71`, valores sintéticos, comentario de provenance explícito sobre no refrescar baselines); helper `_keys_recursive`; 4 tests nuevos; T14/T13/T11 re-derivados en su lugar sin renombrar; `_HEALTH_MODEL_CLASSES` compartido por los cuatro sitios que assertan sobre el conjunto cerrado de modelos de health.
- `packages/market-data-client/tests/test_reference_models.py` — `test_symbol_field_set_matches_reconciled_wire` gana `"note"`, con el comentario que nombra su procedencia distinta a la de las otras cinco claves wire-only.
- `packages/market-data-client/tests/test_models.py` — **no estaba en el plan**; ver Deviations.

## Conteo de tests del paquete

| Momento | Tests | Resultado |
|---|---|---|
| Antes (HEAD del plan, `b596d3c`) | 717 | 717 passed |
| Después del Task 1 (RED) | 199 en los dos archivos tocados | 6 failed, 193 passed |
| Después del REFACTOR (final) | **727** | 727 passed |

Delta neto: **+10 tests** — 4 funciones nuevas más 3 casos parametrizados nuevos (`FeedSubscription` en los tres estructurales)... y 3 más porque `_HEALTH_MODEL_CLASSES` extendió la parametrización. Los 4 re-derivados conservan nombre y conteo.

## Decisions Made

Ninguna decisión nueva de fase: D-08 a D-11 y D-13 se implementaron tal como el plan las especifica. Tres elecciones que el plan dejaba abiertas se resolvieron así:

- **La posición de `symbols_never_delivered` dentro de `HealthFeed`** — el plan no la fija. Se declaró junto a `symbols_with_data`, su vecino semántico. No es cosmético: la posición determina el orden en que el walker emite el record de T14, y agruparla con su hermana la hace legible en el `assert`.
- **`FeedSubscription` se enroló también en `test_health_models_declare_exactly_the_two_locked_optionals`**, no solo en los tres parametrizados que la sección E del plan nombra. Es la mitigación directa de T-43-07: sin eso, alguien podría agregar un `| None` a cualquiera de los 15 campos nuevos sin que ningún lock lo detecte. El conjunto asertado no cambia (la clase no tiene Optionals), la red sí.
- **Los cuatro sitios que assertan sobre el conjunto cerrado de modelos de health comparten una lista** en vez de mantener cuatro literales idénticos. El modo de fallo que evita es concreto y ya ocurrió en otros repos: un modelo nuevo enrolado en tres locks y silenciosamente afuera del cuarto.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_models.py` tenía un conteo exacto de roster que el análisis de rotura del plan no listaba**

- **Found during:** Task 2 (GREEN), al correr la suite del paquete
- **Issue:** `test_the_mapping_machinery_left_the_module_without_taking_anything_else` (`test_models.py`) asserta `len(roster) == 19` sobre el conjunto de subclases de `SafeModel` alcanzables por introspección del módulo. `FeedSubscription` lo lleva a 20. Es exactamente la misma clase de trampa que el plan documenta como Pitfall 2 y Pitfall 3 —un test con aserción exacta fuera de la lista de D-12— pero sobre un cuarto archivo.
- **Fix:** bump de 19 a 20 más `"FeedSubscription"` agregado a la aserción de subconjunto que lo acompaña (`{"BookLevel", "EntryValue", "MarketDataEntries", "FeedSubscription"} <= roster`), para que el conteo no sea el único testigo. El docstring se actualizó explicando que ese número es un piso de no-vacuidad para las aserciones de arriba, no un tope del módulo, y que se mueve con el roster en el mismo commit.
- **Files modified:** `packages/market-data-client/tests/test_models.py`
- **Commit:** `327b3ce`
- **Efecto sobre la verificación del plan:** el `<verification>` del plan dice que el diff acumulado contiene exactamente tres archivos. Contiene **cuatro**. Los cuatro están dentro de `packages/market-data-client/` y ninguno es fuente de producción salvo `models.py`; el alcance D-16 (`models.py` + tests) se respeta.

**2. [Rule 3 - Blocking] Dos criterios de aceptación del Task 1 eran mutuamente inconsistentes**

- **Found during:** Task 1 (RED), al escribir los tests
- **Issue:** el Task 1 exige que `pytest --collect-only` termine con exit code 0 ("un fallo de COLECCIÓN es un error de sintaxis, no un RED válido") **y** que los tests nuevos referencien `FeedSubscription`, que en ese momento no existe. Un `from ... import FeedSubscription` en la mitad RED es un `ImportError` en tiempo de colección: esconde los 171 tests del archivo detrás de un solo traceback. Y el Task 2 no podía arreglarlo, porque su criterio de aceptación exige que `git diff --name-only` liste exactamente `models.py`.
- **Fix:** se resolvió con el tercer gate del ciclo TDD que el plan ya autoriza por su `type: tdd`. En RED, `FeedSubscription` se resuelve por `getattr(models, "FeedSubscription", None)` con un comentario que declara que el default solo dispara en esa corrida; en un commit **REFACTOR** posterior al GREEN (`8b4de5e`) el shim se retira y queda un import por nombre. Los tres conjuntos de criterios de aceptación se cumplen literalmente: RED colecta en 0 y toca 2 archivos, GREEN toca solo `models.py` (más la desviación 1), el REFACTOR toca solo `test_core.py`.
- **Files modified:** `packages/market-data-client/tests/test_core.py`
- **Commits:** `1bc82b1` (shim), `8b4de5e` (retiro)

No se dispararon las reglas 1, 2 ni 4. No hubo gates de autenticación. No se instaló ni actualizó ninguna dependencia externa.

## Issues Encountered

- **`mypy` strict y `_decode.hints_for` sobre una lista tipada.** Anotar `_HEALTH_MODEL_CLASSES` como `list[type[SafeModel]]` rompe la llamada `hints_for(cls)`: el `lru_cache` exige `Hashable` y el `__hash__` de `SafeModel` no satisface la firma esperada. Se resolvió con `cast(Any, cls)` en el sitio de llamada — que es exactamente la disciplina que el propio archivo ya aplica en `test_health_models_declare_no_received_at` y que `_decode.hints_for` aplica internamente — en vez de degradar la anotación de la lista a `list[Any]`.
- No se corrió la suite del monorepo entero (excede los 10 minutos, precedente registrado en `43-01-SUMMARY.md`). La verificación es por paquete y corre en ~1 s; los cinco gates que el plan sí exige corrieron todos en verde, y ningún archivo fuera de `packages/market-data-client/` fue tocado.

## Verificacion final

| Gate | Comando | Resultado |
|---|---|---|
| Suite del paquete | `uv run pytest packages/market-data-client -q --no-cov` | **727 passed** |
| Surface types | `uv run python tools/check_surface_types.py` | `0 violations` (452 campos escaneados) |
| mypy (src) | `uv run mypy` | Success, 75 files |
| mypy (tests del paquete) | `uv run mypy packages/market-data-client/tests` | Success, 36 files |
| ruff lint | `uv run ruff check .` | All checks passed |
| ruff format | `uv run ruff format --check .` | 279 files already formatted |
| Baselines write-once | `git status --porcelain .planning/verification/schemas/ uv.lock` | sin salida |
| Field set `FeedSubscription` | `dataclasses.fields` | 15, los 15 nombres esperados |
| Sin override / sin `received_at` | introspección | `True` / `True` |
| Cola de `FeedIngestor` | últimos 4 campos | `['subscription', 'last_error', 'last_error_age_seconds', 'last_error_at']` |
| `models.__all__` | posición y orden | `FeedSubscription` justo después de `FeedPipeline`; lista ordenada |
| Fixtures sin captures | `grep -c 'verification/captures' test_core.py` | `0` |

## Seguimiento marcado — NO corregido aca

1. **`FeedSubscription` no está en el `__all__` del paquete** (`__init__.py`), solo en `models.__all__`. Es una inconsistencia con `FeedMarket` y `FeedPipeline`, que sí están en ambos. Ningún test lo exige y D-16 lockea el alcance. **Efecto secundario real:** `check_surface_types.py` resuelve candidatos desde el `__all__` de cada `__init__.py` hacia afuera, así que los 15 campos de la clase nueva **no** quedan escaneados por el gate — el `0 violations` de arriba es verdadero pero no cubre esta clase. Candidato para la Phase 44, que ya toca `__init__.py` para el bump de versión.
2. **`main_market_data.py:1541-1542`** — dereferencia `.marketSegmentId`, el campo que D-06 removió en el plan 43-01. Sigue sin tocar. Se consolida en `43-DISPOSITION.md` (plan 43-03).

## Known Stubs

Ninguno. Las cinco claves quedan cableadas de punta a punta contra el blob medido, y `test_feed_subscription_decodes_the_measured_blob` asserta VALORES de los 15 campos —no solo `isinstance`— precisamente para que no pueda pasar vacuamente sobre un Null Object.

## Threat Flags

Ninguna superficie de seguridad nueva. Los cambios son declaraciones de dataclass y aserciones de test dentro del límite de confianza ya registrado (`vendor HTTP response -> SafeModel.from_api`). Disposición del registro STRIDE del plan:

- **T-43-06** (mapping opaco como punto ciego) — **mitigado**: los 15 campos están tipados y el walker los camina; probado por el test de valores.
- **T-43-07** (over-declaración de `Optional`) — **mitigado**: el lock de conjunto exacto pasa a cuatro y ahora incluye `FeedSubscription` en su tupla de clases, así que un `| None` de más en cualquiera de los 15 campos nuevos también falla ahí.
- **T-43-08** (fixtures vs. captures con PII) — **mitigado**: `grep -c 'verification/captures'` devuelve `0`; los valores de `_MEASURED_HEALTH_FEED_43` son sintéticos.
- **T-43-09** (baselines write-once) — **mitigado**: `git status --porcelain .planning/verification/schemas/` sin salida en los tres commits.
- **T-43-10** (payload parcial o nulo) — **mitigado**: `FeedSubscription` hereda entera la tolerancia de `SafeModel`; el test parametrizado sobre las siete clases pinnea que `from_api(None)` no levanta.
- **T-43-SC** (instalaciones de paquetes) — **accept, no-op verificado**: `uv.lock` sin tocar, cero paquetes externos instalados.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- El plan 43-03 recibe como input directo la tabla de las 5 claves de arriba (criterio 3), la lista exacta de records de T14 con su explicación (evidencia de que el criterio 3 se está evaluando bien), y los dos ítems de seguimiento marcado para `43-DISPOSITION.md`.
- La Phase 44 recibe dos ítems concretos: el bump de versión en los tres sitios y el enrolamiento de `FeedSubscription` en el `__all__` del paquete, que es lo que la mete bajo el gate `surface-types`.
- **No** se bumpeó ninguna versión ni se tocó `uv.lock`.

## Self-Check: PASSED

Los 4 archivos declarados existen en disco y los 3 hashes de commit (`1bc82b1`, `327b3ce`, `8b4de5e`) existen en el historial de git.

---
*Phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr*
*Completed: 2026-09-01*
