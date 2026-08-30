---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
plan: 04
subsystem: testing
tags: [deep-chain, null-object, ast-lock, iol, non-vacuity, ci]

# Dependency graph
requires:
  - phase: 38-...
    provides: "Cotizacion.puntas: list[Punta] (rama de colapso NOBJ-02) y Titulo.puntas: Punta singular Null Object, ambos no-Optional"
  - phase: 36-...
    provides: "verification/test_main_market_data_deep_chain.py — el analog exacto (_protected_node_ids, _chain_reaches, piso por probe WR-06) y la allowlist explícita de ci.yml"
  - phase: 39-03
    provides: "el precedente de cablear cada archivo nuevo de verification/ a la allowlist en el mismo commit + la ubicación real de esa lista (job lint)"
provides:
  - "verification/test_main_iol_deep_chain.py — lock AST de la cadena .puntas en los 4 probes tipados de iol, en la allowlist de CI"
  - "main_iol.py desreferencia .puntas dentro del cuerpo del try de los 4 probes tipados (sync + async, quote + instrumentos por tipo)"
  - "Los valores de la cadena (compra, venta, profundidad) observables en el detalle de cada ProbeResult PASS, transcribibles al censo"
affects: [39-05, 39-06, 39-07, 39-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lock AST tolerante a DOS formas de la misma cadena: Subscript (lista) y Attribute directo (Null Object singular), con la razón escrita en el docstring para que nadie 'arregle' el helper"
    - "Piso por probe con el agregado DERIVADO por sum(), nunca re-tipeado, de modo que los dos números no puedan discrepar"
    - "_CHAINED_COLLECTIONS_BY_PROBE vacío y documentado donde el probe no itera una colección local — un nombre inventado ahí haría el test rojo-infalsificable en vez de significativo"

key-files:
  created:
    - verification/test_main_iol_deep_chain.py
  modified:
    - main_iol.py
    - .github/workflows/ci.yml

key-decisions:
  - "La allowlist de CI está en el job `lint` (step de driver locks), no en el job `test`: el job `test` corre per-package y nunca ve verification/. Mismo sitio donde 39-01 y 39-03 pusieron sus archivos"
  - "_ALIAS_NAMES lista SOLO los dos campos de Punta que el driver gasta (precioCompra, precioVenta), no los cuatro: ensanchar el set dejaría que un probe satisfaga el piso con un campo que nadie lee"
  - "Los probes de quote quedan con _CHAINED_COLLECTIONS_BY_PROBE vacío a propósito: lo que obtienen es una Cotizacion sola y la colección que recorren (quote.puntas) se alcanza por subscript sobre el modelo, no iterando un Name local"
  - "La rama se decide por truthiness del Null Object / de la lista, nunca por `is None`: ambos campos están declarados sin `| None` y una guarda de nulidad sería código muerto que contradice el tipo que la Phase 38 entregó"
  - "Los probes de instrumentos usan una comprensión sobre wrapper_result, no un len(): con len() solo el decode de cada Punta de cada fila viajaría sin ejercitar y el probe reportaría PASS igual (WR-06)"

patterns-established:
  - "Cada archivo nuevo bajo verification/ entra a la allowlist de ci.yml en el MISMO commit que lo vuelve verde (no antes: en el commit RED el archivo queda deliberadamente fuera)"

requirements-completed: [LIVE-NOBJ-01]

# Metrics
duration: 3min
completed: 2026-08-30
status: complete
---

# Phase 39 Plan 04: Cadena `.puntas` gastada en los probes tipados de iol Summary

**Un lock AST que exige que los cuatro probes tipados de `main_iol.py` desreferencien `.puntas` hasta un campo de `Punta` dentro del cuerpo de su propio `try`, y las desreferencias que lo vuelven verde — dos formas distintas de la misma clave, lista en `Cotizacion` y Null Object singular en `Titulo`.**

## Performance

- **Duration:** ~3 min
- **Tasks:** 2 (1 RED, 1 GREEN — plan `type: tdd`)
- **Files modified:** 3 (1 creado, 2 modificados)

## Accomplishments

- `main_iol.py` no referenciaba `.puntas` en **ningún** lugar. La Phase 38 tipó la clave en dos modelos y ninguno de los cuatro probes tipados la tocaba: los probes de quote terminaban en `ultimoPrecio` y los de instrumentos en `len(wrapper_result)`. Un `len()` nunca toca la cadena, así que el decode completo de `Punta` viajaba sin ejercitar mientras los cuatro probes reportaban PASS.
- Las **dos formas** de la cadena quedan cubiertas por un solo lock: `quote.puntas[0].precioCompra` (lista, pasa por un `Subscript`) y `titulo.puntas.precioCompra` (Null Object singular, atributo directo). `_chain_reaches` del analog ya atraviesa `Attribute`, `Subscript` y `Call`, así que no hizo falta modificarlo — y el docstring del módulo dice exactamente eso, para que un lector futuro no lo "arregle" a una sola forma y deje de ver los dos probes de quote en silencio.
- El piso por probe (2/2/1/1) es lo que impide que un refactor adelgace la cadena: 6 accesos repartidos 5/1/0/0 satisfacen el agregado y dejan dos probes sin ejercitar. El agregado se **deriva** con `sum(...)`, así que no puede discrepar del desglose.
- El lock corre en CI: entró a la allowlist explícita del step de driver locks en el mismo commit que lo volvió verde. Un guard bajo `verification/` fuera de esa lista es **inerte** — exactamente lo que el code review de la Phase 36 encontró (WR-01) con el primer lock de deep-chain.
- Cero probes nuevos, cero llamadas HTTP nuevas: los cuatro probes ya tenían el objeto tipado en mano. Las escaleras de excepciones (`IOLAuthError` → `IOLAPIError` → `IOLDecodeError` → `except Exception`) y los nombres de probe quedaron intactos.

## Task Commits

1. **Task 1 (RED): lock AST de la cadena `.puntas`** — `5820fd9` (test)
2. **Task 2 (GREEN): desreferencias en los 4 probes + cableado a CI** — `a25fb30` (feat)

_TDD: RED verificado antes del GREEN — **4 failed / 2 passed**. Los 2 verdes son los que no dependen de la cadena (presencia de los cuatro probes por nombre, y el gate de `try` que es vacuamente cierto sin accesos). Los 4 rojos nombraron exactamente los cuatro probes sin desreferencia y las dos colecciones `wrapper_result` sin encadenar. Tras el GREEN: 6 passed._

## Files Created/Modified

- `verification/test_main_iol_deep_chain.py` — 6 tests. Constantes de módulo: `_DRIVER` = `main_iol.py`; `_ALIAS_NAMES` = `{precioCompra, precioVenta}`; `_READ_PROBES` = los cuatro nombres; `_MIN_CHAINED_ACCESSES_BY_PROBE` = `{quote_sync: 2, quote_async: 2, instruments_sync: 1, instruments_async: 1}` con `_MIN_CHAINED_ACCESSES = sum(...)`; `_CHAINED_COLLECTIONS_BY_PROBE` = `{wrapper_result}` para los dos de instrumentos y **vacío** para los dos de quote. Helpers `_protected_node_ids` y `_chain_reaches` copiados verbatim del analog. El driver se `ast.parse`-a, nunca se importa (`load_dotenv` de import-time); el archivo no contiene ningún `import main_iol`.
- `main_iol.py` — cuatro sitios, todos **dentro del cuerpo del `try` existente**, inmediatamente después de la llamada que ya estaba:
  - `probe_get_quote_sync` / `probe_get_quote_async`: `niveles_libro = len(quote.puntas)`, `mejor_compra` y `mejor_venta` desde `quote.puntas[0]` con guarda de veracidad sobre la lista.
  - `probe_get_instruments_by_type_sync` / `_async`: `compras_libro = [titulo.puntas.precioCompra for titulo in wrapper_result]` y `mejor_compra = compras_libro[0] if compras_libro else None`.
  - Los cuatro `ProbeResult` de PASS incorporan los valores obtenidos sin cambiar el nombre del probe ni romper la forma existente del detalle.
- `.github/workflows/ci.yml` — `verification/test_main_iol_deep_chain.py` agregado a la lista explícita del step "driver locks" del job `lint`.

## Decisions Made

- **La allowlist real vive en el job `lint`, no en el `test`.** El texto del plan dice "job `test`"; la lista explícita a la que 39-01 y 39-03 agregaron sus archivos es el step de driver locks del job `lint` (`ci.yml:79-89`). El job `test` corre per-package y pasa un path explícito que pisa `testpaths`, así que nunca colectaría `verification/`. Se siguió el sitio real, verificado por `grep` de `test_main_verify_classification.py` antes de editar.
- **El set de alias es angosto a propósito.** `Punta` declara cuatro campos decimales; `_ALIAS_NAMES` lista los dos que el driver gasta. Con los cuatro, un probe podría alcanzar su piso desreferenciando `cantidadCompra` — un campo que nadie lee — y el lock lo daría por cubierto.
- **`_CHAINED_COLLECTIONS_BY_PROBE` vacío para los probes de quote, y documentado.** Lo que obtienen es una `Cotizacion` sola; la colección que recorren (`quote.puntas`) se alcanza por subscript sobre el modelo, no iterando un `Name` local, así que ninguna comprensión podría satisfacer ese test. Poner ahí un nombre que el probe nunca bindea lo volvería rojo-infalsificable en vez de significativo. Su cobertura la asegura el piso por probe.
- **Guarda por veracidad, nunca `is None`.** `Cotizacion.puntas` es `list[Punta]` no-Optional (la rama de colapso NOBJ-02 cubre el `null` del wire y la clave ausente) y `Titulo.puntas` es un `Punta` declarado sin `| None`. Una guarda de nulidad sería código muerto demostrable y contradiría el tipo que la Phase 38 entregó — el mismo razonamiento que ya había eliminado el guard de tipo sobre `ultimoPrecio` (TYP-01).
- **Comprensión, no `len()`, en los probes de instrumentos.** El propio test `test_every_fetched_titulo_collection_is_chained` es el que lo exige, y por la razón que el docstring del analog enuncia (WR-06): una colección consumida por `len()` solo embarca todo su camino de decode sin ejercitar mientras el probe sigue reportando PASS.
- **La ubicación dentro del `try` es load-bearing y quedó escrita en el sitio.** Fuera del `try` un eslabón roto se propagaría sin capturar y tumbaría `iol-client` a FAILED en `main_verify.py` en vez de degradar a FINDING (D-09, T-39-13). El lock lo pinea con `_protected_node_ids`, que excluye deliberadamente `except` / `else` / `finally`.

## Deviations from Plan

Ninguna. El plan se ejecutó tal como está escrito, con una única precisión de ubicación ya anticipada por el ejecutor de 39-03 y registrada arriba: la allowlist explícita está en el job `lint`, no en el `test`. No es una desviación del contenido del plan sino de una referencia imprecisa a un nombre de job.

Cero dependencias nuevas (T-39-SC). Cero probes nuevos, cero llamadas HTTP nuevas, cero cambios en las escaleras de excepciones y cero renombres de probe.

## Issues Encountered

Uno menor, resuelto en el acto: tras las ediciones, `ruff format --check .` pidió reformatear `main_iol.py` (los f-strings largos del detalle de los `ProbeResult`). Se corrió `ruff format main_iol.py` y se re-verificó el lock (6 passed) antes de commitear — el formateo no movió ninguna desreferencia fuera de su `try`.

## Verificación

| Criterio | Resultado |
|---|---|
| `pytest -q verification/test_main_iol_deep_chain.py` (RED, Task 1) | 4 failed / 2 passed |
| `pytest -q verification/test_main_iol_deep_chain.py` (GREEN, Task 2) | 6 passed |
| `pytest -q packages/iol-client` | 311 passed |
| Los 3 locks previos del driver de iol (`fid_seed`, `exception_redaction`, `raw_wire_drift`) | 91 passed |
| `test_iol_disk_persistence.py` + `test_main_iol_uses_single_client_instance.py` | 12 passed |
| Allowlist completa de CI (9 archivos, incluido el nuevo) | 90 passed |
| `ruff check .` / `ruff format --check .` / `mypy` | 0 / 0 / Success: no issues found in 75 source files |
| `grep -c 'test_main_iol_deep_chain.py' .github/workflows/ci.yml` | 1 (≥ 1) |
| `grep -c puntas main_iol.py` | 14 (≥ 6) |
| `grep -c 'import main_iol' verification/test_main_iol_deep_chain.py` | 0 |
| `grep -c 'sum(_MIN_CHAINED_ACCESSES_BY_PROBE.values())'` | 1 |
| Deletions en los 2 commits de tarea | ninguna |
| Untracked tras los 2 commits | ninguno |

## Known Stubs

Ninguno. Las cuatro desreferencias son código en el camino caliente de los probes; se ejercitan en la primera corrida en vivo del driver.

Nota sobre lo que el lock **no** exige: la colección `titulos` del sanity loop de los 6 `InstrumentType` (dentro de `probe_get_instruments_by_type_sync`) no está en `_CHAINED_COLLECTIONS_BY_PROBE`. Ese loop es un chequeo de **forma, no de cardinalidad** —una lista vacía es legítima fuera de horario de mercado— y encadenar ahí duplicaría el concepto que `wrapper_result` ya cubre. Es la elección que el plan nombra explícitamente ("el resultado del wrapper en los probes de instrumentos"), no un olvido.

## Threat Flags

Ninguno. Las tres superficies tocadas ya estaban en el `<threat_model>` del plan:

- **T-39-13** (eslabón roto fuera del `try`) — mitigado: las cuatro desreferencias viven en el cuerpo del `try` y `test_every_chained_access_sits_inside_the_probe_try_body` lo pinea con `_protected_node_ids`, que excluye `except` / `else` / `finally`.
- **T-39-14** (valores de cadena en el detalle del `ProbeResult`) — mitigado: lo que se agrega son precios y un conteo de niveles. Cero campos de identidad, cero credenciales, cero base URLs; el driver ya emite todo por `safe_print(..., secrets=[...])`.
- **T-39-15** (lock sin cablear) — mitigado: la entrada en la allowlist ocurrió en el mismo commit que volvió verde el lock (`a25fb30`), verificado por `grep -c`.
- **T-39-SC** — cero dependencias nuevas.

## Next Phase Readiness

- **La cadena está gastada pero todavía no corrida en vivo.** El lock es estructural: garantiza que el código existe y está bien ubicado, no que la API haya devuelto un libro. La primera corrida real es la que dirá si `puntas` llega poblada — el corpus del 2026-06-06 registró `[]` para `get_quote` y `null` para la serie histórica, así que el detalle de PASS puede legítimamente salir `puntas=0 compra=None venta=None` sin que nada esté roto. Eso es evidencia del camino vacío, no un fallo de la cadena.
- **`Punta` sigue siendo forma inobservada (D-02 / FA-03).** Los cuatro campos decimales nunca se vieron poblados en ningún capture. Una divergencia de tipo sobre `precioCompra` / `precioVenta` en la corrida en vivo es **esa asunción corrigiéndose sola**, no un defecto del modelo — el censo de 39-08 debe registrarla como tal.
- **`F-01` (`missing simbolo` en `get_quote`, OPEN) se re-emitirá.** Es una hoja escalar que la política Null Object no colapsa; verla otra vez en la corrida en vivo no es una regresión nueva.
- **Insumo para el censo (39-08):** el detalle de PASS de los cuatro probes transcribe ahora los valores de la cadena, así que la profundidad de libro y las dos puntas del top of book son leíbles directo del stdout de la corrida, sin instrumentación extra.

## Self-Check: PASSED

- `verification/test_main_iol_deep_chain.py` — FOUND en disco.
- Commit `5820fd9` — FOUND en el historial.
- Commit `a25fb30` — FOUND en el historial.

---
*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo*
*Completed: 2026-08-30*
