---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
plan: 03
subsystem: testing
tags: [verification-harness, run-evidence, cycle-closure, non-vacuity, census, ci]

# Dependency graph
requires:
  - phase: 39-01
    provides: "las dos ramas de skip (gate D-MATZ-33 de matriz, vendor DNS de higyrus) donde el sobre de evidencia se reescribe con cero probes"
  - phase: 33-...
    provides: "DivergenceHandler.seen como unidad del censo + verification/test_cycle_closure_phase33.py"
  - phase: 36-...
    provides: "precedente de endurecimiento a nivel de probe (probe_cycle_closure de main_market_data) y la allowlist explícita de ci.yml"
provides:
  - "verification/run_evidence.py — sobre de evidencia de corrida por paquete (write/read/path/probes_executed)"
  - "Los MIEMBROS de DivergenceHandler.seen persistidos, no sólo su conteo: la diferencia de conjuntos del censo pasa a ser computable (D-10)"
  - "Cierre de ciclo no-vacuo: PASS sólo con probes_executed > 0; SKIPPED con causa medida y destino nombrado sin evidencia; FAIL sólo por regresiones faltantes"
  - "_cycle_closure_verdict / _cycle_closure_destination como predicado de módulo testeable por import"
  - "verification/test_cycle_closure_phase33.py verde (2 rojos previos por ruta obsoleta cerrados)"
affects: [39-04, 39-05, 39-06, 39-07, 39-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sobre de evidencia de corrida por paquete: JSON reescrito (no append) con conteo de probes + miembros ordenados, versionado porque sólo lleva metadata de tipo"
    - "Predicado de no-vacuidad por EVIDENCIA POSITIVA DE CORRIDA (conteo de probes), no por conteo de findings promovidos"
    - "Guarda de slug REUTILIZADA (import de _validate_pkg_slug) en vez de un segundo regex que puede divergir"
    - "Escritura interina del sobre propio antes del consumidor in-process, reescrita al final con los conteos completos"

key-files:
  created:
    - verification/run_evidence.py
    - verification/test_run_evidence.py
  modified:
    - verification/__init__.py
    - verification/test_cycle_closure_phase33.py
    - main_iol.py
    - main_higyrus.py
    - main_matriz.py
    - main_ambito_financiero.py
    - .github/workflows/ci.yml

key-decisions:
  - "La costura de no-vacuidad se implanta en el loop de 4 paquetes de main_matriz.py, NO en verification/cycle_report.py: tres tests pinean el contrato (True, []) de la librería y editarla los enrojece sin ganancia"
  - "El predicado es probes_executed > 0, NO 'al menos un finding CONFIRMED/FIXED': ese criterio (el de main_market_data.py) reprobaría a ámbito por estar limpio y a higyrus por no haber sido medido — dos causas opuestas con el mismo veredicto (Pitfall 6)"
  - "El sobre se REESCRIBE en cada corrida, incluidos los dos caminos de skip: una corrida saltada invalida el sobre anterior en vez de dejarlo en pie (T-39-12)"
  - "matriz escribe un sobre INTERINO antes del loop de cierre de ciclo (deviación Rule 1): sin eso se juzgaría a sí mismo por la corrida anterior, o saldría SKIPPED 'sin evidencia' en el mismo output donde acaba de imprimir 24 probes"
  - "El predicado vive en dos funciones de módulo anotadas y testeables por import, no inline en main(): mismo patrón que _venue_token del plan 39-01"
  - "El set de claves del sobre está pineado por un test: agregar un campo que transporte un valor de wire no puede pasar inadvertido (T-39-10)"

patterns-established:
  - "Cada archivo nuevo bajo verification/ entra a la allowlist de ci.yml en el MISMO commit que lo crea"
  - "Un guard cuya ruta quedó obsoleta se REPUNTA, no se relaja: un rojo permanente se aprende a ignorar y deja de ser un guard"

requirements-completed: [LIVE-NOBJ-01]

# Metrics
duration: 8min
completed: 2026-08-30
status: complete
---

# Phase 39 Plan 03: Evidencia de corrida y cierre de ciclo no-vacuo Summary

**Un sobre de evidencia de corrida por paquete que persiste los MIEMBROS de `DivergenceHandler.seen` (no sólo su conteo) y el número de probes ejecutados, con el loop de cierre de ciclo de matriz endurecido para que PASS exija evidencia positiva de corrida y la ausencia de corrida salga SKIPPED con destino nombrado.**

## Performance

- **Duration:** ~8 min
- **Tasks:** 3 (2 TDD, 1 de cableado)
- **Files modified:** 9 (2 creados, 7 modificados)

## Accomplishments

- `verify_cycle_closure` devolvía `(True, [])` tanto con todo enlazado como con el archivo de findings ausente. El loop de cuatro paquetes ya no promueve ese `ok` a `PASS` sin más: consulta `probes_executed(pkg)` primero y, con cero, emite `SKIPPED` con la causa medida y el destino nombrado (`LIVE-HIGY-33` / `LIVE-MATZ-33` / `LIVE-NOBJ-01`).
- Los cuatro drivers en alcance imprimían `DIVERGENCES=N` —un conteo que muere con el proceso— y nunca los miembros. Ahora escriben `sorted(handler.seen)` al sobre: la diferencia de conjuntos que D-10 exige contra `33-CENSUS.md` pasa de incomputable a computable.
- Las **dos ramas de skip** que dejó el plan 39-01 reescriben el sobre con cero probes y causa medida antes de `sys.exit(0)`. Un sobre positivo de una corrida anterior no puede sobrevivir a una corrida saltada (T-39-12).
- `verification/test_cycle_closure_phase33.py` pasó de **2 failed / 9 passed** a **0 failed / 21 passed**: `_CENSUS` repuntado al censo archivado más 11 tests nuevos que pinean el predicado.
- El predicado erróneo está pineado como prohibido: un test AST falla si el loop empieza a leer el archivo de findings o a referenciar un regex de estados cerrados — el criterio de `main_market_data.py`, correcto allá (50 promociones) y destructivo acá.

## Task Commits

1. **Task 1: `verification/run_evidence.py` — sobre de evidencia de corrida** — `33b11e9` (feat)
2. **Task 2: cablear los 4 drivers en alcance** — `8f53558` (feat)
3. **Task 3: cierre de ciclo no-vacuo + repunte de `test_cycle_closure_phase33.py`** — `dde0f10` (feat)

_TDD: RED verificado antes de cada GREEN. Task 1 — `ImportError: cannot import name 'run_evidence'` (25 tests sin colectar). Task 3 — 9 fallas por la razón esperada (`_cycle_closure_verdict` / `_cycle_closure_destination` ausentes, `probes_executed` no presente en el fuente), con los 2 rojos históricos ya cerrados por el repunte de `_CENSUS`._

## Files Created/Modified

- `verification/run_evidence.py` — `write_run_evidence` / `read_run_evidence` / `run_evidence_path` / `probes_executed`. Sólo stdlib (`json`, `datetime`, `pathlib`). Directorio derivado de `__file__`; guarda de slug importada de `verification.findings`. Docstring de módulo con las tres justificaciones que pide el plan: por qué el sobre existe, por qué es seguro versionarlo, y por qué el predicado es el conteo de probes.
- `verification/test_run_evidence.py` — 25 tests: round-trip, set de claves pineado, `probes_executed` = suma de conteos, `captured_at` ISO-8601 UTC, orden estable (lista, lista invertida y `set`), dedupe, reescritura-no-append, sobre ausente, cero probes con causa, JSON corrupto, JSON no-objeto, `probes_executed` no entero, 8 slugs hostiles con aserción de "ningún archivo escrito", identidad del validador de slug, forma del directorio real, y los 4 re-exports.
- `verification/__init__.py` — 4 nombres nuevos en `__all__` (orden alfabético) + entrada en el docstring de módulo.
- `main_iol.py`, `main_ambito_financiero.py`, `main_higyrus.py`, `main_matriz.py` — escritura del sobre junto al `SUMMARY`, con el dict de conteos por estado. Las líneas `SUMMARY` quedaron **intactas** en los cuatro.
- `main_higyrus.py` — `_VENDOR_UNREACHABLE_EVIDENCE` + escritura del sobre en la rama de vendor inalcanzable.
- `main_matriz.py` — `_HOST_SKIP_EVIDENCE`, `_CYCLE_CLOSURE_DESTINATION` (+ default), `_cycle_closure_destination()`, `_cycle_closure_verdict()`, escritura en la rama del gate D-MATZ-33, sobre interino antes del loop, y el loop reescrito con el acoplamiento declarado en prosa.
- `verification/test_cycle_closure_phase33.py` — `_CENSUS` repuntado + 11 tests nuevos + docstring de módulo corregido.
- `.github/workflows/ci.yml` — `verification/test_run_evidence.py` en la allowlist del step de driver locks (job `lint`).

## Decisions Made

- **La costura vive en el driver, no en la librería.** `verification/cycle_report.py` quedó **byte-idéntico** (`git diff --stat` vacío) y `verification/test_cycle_closure_market_data.py` sigue verde: la señal de que el contrato `(True, [])` de la librería no se tocó. El endurecimiento **envuelve** `verify_cycle_closure`, no lo rodea — el loop sigue llamándola, así que su guarda de path traversal sobre el bullet `Regression:` sigue en el camino (T-39-11), y un test AST falla si esa llamada desaparece.
- **La allowlist de CI está en el job `lint`, no en el job `test`.** El plan dice "job `test`"; la lista explícita real (la que el plan cita por línea, `ci.yml:70-85`) es el step de driver locks del job `lint`, donde el plan 39-01 puso sus tres archivos. El job `test` corre per-package y nunca vería `verification/`. Se siguió el sitio real.
- **El destino no se concatena dos veces.** La causa que escriben los caminos de skip ya termina en su destino (`… — LIVE-HIGY-33`); el veredicto sólo lo agrega si no está presente. Pineado por `detail.count("LIVE-HIGY-33") == 1`.
- **`probes_executed` es fail-closed hacia SKIPPED.** Un sobre ilegible, un JSON no-objeto o un `probes_executed` no entero devuelven `0`, nunca un número que promueva un `PASS`. `read_run_evidence` no lanza por estado del disco: un `ValueError` a mitad del loop dejaría a los paquetes restantes sin veredicto.
- **El detalle del `PASS` transcribe la evidencia.** `"{n} probes ejecutados, evidencia de {captured_at}"` en vez del `""` anterior: ese par es lo que el censo copia. El nombre de cada `ProbeResult` (`cycle_closure_<slug>`) y el orden de los cuatro slugs quedaron sin cambios — los findings downstream están keyeados por nombre de probe.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] matriz se juzgaba a sí mismo por la corrida ANTERIOR**

- **Found during:** Task 2 (detectado al mapear el orden de ejecución para Task 3)
- **Issue:** El loop de cierre de ciclo corre **dentro** del sweep, antes del bloque del `SUMMARY`. Con la escritura del sobre sólo al final (que es lo que el plan literal pide), en el momento del loop el sobre de `matriz-client` en disco es todavía el de la corrida anterior — o no existe. En el primer run tras este cambio, matriz habría emitido `PROBE cycle_closure_matriz_client: SKIPPED sin evidencia de corrida — LIVE-MATZ-33` en el mismo output donde acababa de imprimir 24 probes propios: un veredicto que se contradice con su propia salida.
- **Fix:** Escritura **interina** del sobre de `_PKG` inmediatamente antes del loop, con los conteos de los resultados ya recolectados. El bloque del `SUMMARY` lo reescribe al final con los conteos completos (incluidos los probes async y el propio veredicto de cierre). Documentado en prosa en el sitio.
- **Files modified:** `main_matriz.py`
- **Verification:** `grep -c write_run_evidence main_matriz.py` = 4 (import + skip + interino + final); las suites de los 3 locks de matriz siguen verdes.
- **Committed in:** `8f53558`

**2. [Rule 2 - Missing Critical] El docstring de `test_cycle_closure_phase33.py` afirmaba lo contrario del archivo**

- **Found during:** Task 3
- **Issue:** El docstring de módulo decía "No package is imported". Los tests nuevos importan `main_matriz` para ejercitar el predicado (patrón establecido: `test_main_matriz_skip_line_shape.py` ya lo hace desde el plan 39-01). Dejarlo así reproduce exactamente la deuda que Pitfall 5 identificó en el finding terminal de matriz: fuente que contradice su propio comportamiento.
- **Fix:** Docstring reescrito describiendo las tres técnicas reales (regex sobre markdown, `ast.parse`, import del predicado puro) y qué se sigue garantizando (ni red, ni cliente, ni `main()`).
- **Files modified:** `verification/test_cycle_closure_phase33.py`
- **Verification:** Revisión manual; suite verde.
- **Committed in:** `dde0f10`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing-critical)
**Impact on plan:** La primera es necesaria para que el veredicto de matriz no sea auto-contradictorio; la segunda para que el guard no mienta sobre sí mismo. Sin scope creep: cero dependencias nuevas, `verification/cycle_report.py` y `main_market_data.py` byte-idénticos, líneas `SUMMARY` de los cuatro drivers intactas.

## Issues Encountered

Ninguno. El baseline de `verification/test_cycle_closure_phase33.py` se re-midió al inicio (2 failed, 9 passed) sin recurrir a `git stash` — el comando prohibido que el plan 39-01 registró haber usado.

## Verificación

| Criterio | Resultado |
|---|---|
| `pytest -q` sobre los 10 archivos del success criteria | 107 passed |
| `verification/test_cycle_closure_phase33.py` | 21 passed (baseline: 2 failed / 9 passed) |
| `verification/test_run_evidence.py` | 25 passed |
| `verification/test_cycle_closure_market_data.py` | verde (señal de que `cycle_report.py` no se editó) |
| `ruff check .` / `ruff format --check .` / `mypy` | 0 |
| `git diff --stat verification/cycle_report.py main_market_data.py` | vacío (byte-idénticos) |
| `git grep write_run_evidence main_market_data.py` | sin resultados (D-07) |
| `grep -l write_run_evidence` sobre los 4 drivers | los cuatro |
| `grep -c write_run_evidence main_matriz.py` / `main_higyrus.py` | 4 / 3 (ambos ≥ 2) |
| `grep -c 'LIVE-MATZ-33' main_matriz.py` | 4 (≥ 2) |
| `grep -c 'test_run_evidence.py' .github/workflows/ci.yml` | 1 |
| `git check-ignore .planning/verification/run-evidence/*.json` | no ignorado (versionable) |
| Deletions en los 3 commits de tarea | ninguna |
| Untracked tras los 3 commits | ninguno |

## Known Stubs

Ninguno.

`.planning/verification/run-evidence/` todavía no existe en disco: `write_run_evidence` lo crea con `mkdir(parents=True, exist_ok=True)` en la primera corrida real de cualquier driver. No hay regla de `.gitignore` que lo excluya (verificado con `git check-ignore`), así que los sobres quedarán versionados como el resto de `.planning/verification/`. Los cuatro `<slug>.json` son artefactos de las corridas en vivo de los planes siguientes, no de éste.

## Threat Flags

Ninguno. Las tres superficies tocadas ya estaban en el `<threat_model>` del plan:

- **T-39-09** (path traversal por slug) — mitigado: directorio derivado de `__file__`, validador importado de `verification.findings` (no reescrito, con test de identidad), 8 slugs hostiles parametrizados con aserción de "ningún archivo escrito en `tmp_path`".
- **T-39-10** (information disclosure del sobre versionado) — mitigado: set de claves pineado por test con mensaje que prohíbe explícitamente agregar campos que transporten payload. Cero valores de wire, cero base URLs, cero hostnames.
- **T-39-11** (ruta `Regression:`) — sin cambio: `verify_cycle_closure` sigue en el camino y un test AST falla si el loop deja de llamarla.
- **T-39-12** (sobre viejo leído como evidencia de esta corrida) — mitigado: escritura reemplazante + reescritura en los dos caminos de skip + `captured_at` transcrito al detalle del `PASS`.
- **T-39-SC** — cero dependencias nuevas; sólo stdlib.

## Next Phase Readiness

- **Costura lista, evidencia pendiente:** las funciones existen y están pineadas, pero `.planning/verification/run-evidence/` se puebla recién con las corridas en vivo de los planes siguientes. Hasta entonces, `probes_executed` devuelve 0 para los cuatro y el loop —si corriera— emitiría cuatro `SKIPPED` con destino. Eso es el comportamiento correcto, no una regresión.
- **Acoplamiento a registrar en el censo (39-08):** el cierre de ciclo de los cuatro paquetes vive dentro del driver de matriz. Si matriz sale por el gate D-MATZ-33, el loop no corre y ninguno de los cuatro recibe veredicto; el censo debe registrar `cycle_closure: NO CORRIÓ — LIVE-MATZ-33` para los cuatro. La nota está en el fuente y un test la pinea.
- **Insumo para el contraste de censo (D-10):** cada `<slug>.json` lleva `triples` ordenadas y determinísticas. El plan que compute la diferencia contra `33-CENSUS.md` puede leerlas con `read_run_evidence` sin volver a correr nada.
- **Orden de escritura de matriz:** el sobre final se escribe DESPUÉS del `SUMMARY` y reemplaza al interino. Cualquier consumidor in-process que se agregue entre medio debe tener en cuenta que el sobre en ese punto todavía no incluye los probes async.

## Self-Check: PASSED

Los 2 archivos creados existen en disco (`verification/run_evidence.py`, `verification/test_run_evidence.py`) y los 3 hashes de commit de tarea (`33b11e9`, `8f53558`, `dde0f10`) existen en el historial.

---
*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo*
*Completed: 2026-08-30*
