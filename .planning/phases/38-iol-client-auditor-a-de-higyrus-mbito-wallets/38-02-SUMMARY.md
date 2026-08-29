---
phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
plan: 02
subsystem: tooling
tags: [python, ast, ci-gate, ratchet, null-object, mypy-strict, pytest, stdlib-only]

# Dependency graph
requires:
  - phase: 32-gate-de-tipos-de-superficie
    provides: "tools/check_surface_types.py, la dimensión de retornos, la semilla inyectable REPO_ROOT (D-04) y el fixture RED de iol"
  - phase: 37-market-data-null-objects
    provides: "La dimensión de campos (_field_annotation_is_untyped_mapping, _is_field_exempt, _FIELD_EXEMPTIONS), la disciplina de ratchet D-01b y el arreglo CR-02 de _strip_optional sobre las tres grafías de opcional"
  - phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
    plan: "01"
    provides: "Cotizacion.puntas: list[Punta] y Titulo.puntas: Punta — los 2 únicos sitios que el predicado ensanchado enrojece, ya arreglados"
provides:
  - "_field_annotation_is_optional_model — tercer predicado del gate: `Model | None` y `list[Model] | None` en campos de clases exportadas son violación"
  - "_class_names — clasificador estático de nombres ligados por `class` bajo el import root de cada paquete, computado una vez por paquete"
  - "_optional_inner — la señal «hubo wrapper opcional», hermana de _strip_optional y sin tocar su contrato"
  - "3 tests RED nuevos en el fixture de iol: 1 cota inferior (ambas formas) y 2 pins de angostura (alias Literal, list[Any])"
  - "Piso de no-vacuidad `result.fields >= 400` sobre el test de árbol real — la mitad ejecutable de NOBJ-AUD-01"
affects: [38-03-readme-breaking-callout, 38-04-censo, 39-contabilidad-triples, 40-bump-breaking-coordinado]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Discriminador estático de modelo por conjunto de nombres ClassDef, nunca por issubclass/get_type_hints — el gate no puede importar un módulo de paquete"
    - "Clasificador ≠ fuente de candidatos: los candidatos siguen resolviéndose desde __all__ hacia afuera; el walk del árbol completo sólo responde sí/no sobre una anotación ya encontrada"
    - "Predicados OR-eados con mensajes distintos, nunca fusionados: una violación de mapping y una de link siguen distinguibles en la salida de fallo"

key-files:
  created: []
  modified:
    - tools/check_surface_types.py
    - packages/iol-client/tests/test_surface_types_red.py

key-decisions:
  - "_optional_inner es hermana de _strip_optional, no una modificación: el predicado de mapping depende del peel incondicional, y delegar el peel mantiene las tres grafías en un solo code path (la clase de defecto CR-02)"
  - "El clasificador se construye con rglob('*.py') sobre el import root, no resolviendo por __all__: hoy todo modelo de respuesta está exportado, pero el roster de ClassDef no exportadas prueba que un modelo interno podría introducirse y la ruta __all__ lo perdonaría en silencio"
  - "`dict[str, Model] | None` queda deliberadamente fuera de alcance y documentado como exclusión declarada, no pre-baneado en silencio"
  - "`list` se compara como literal en vez de una constante nueva de módulo: la tabla de artefactos del plan declara sólo tres funciones net-new, y un `_LIST` sin declarar sería deriva"
  - "Task 3 no lleva commit: es verificación read-only y no produce cambio de archivo"

patterns-established:
  - "Prueba de colateral cero por identidad de línea de resumen: correr el gate PRE-widening contra el árbol committeado y exigir salida byte-idéntica"
  - "Criterio de aceptación por grep sobre el diff sustituido por chequeo AST cuando el grep cuenta la prosa que el propio plan manda escribir"

requirements-completed: [NOBJ-AUD-01]

# Metrics
duration: 7min
completed: 2026-08-29
status: complete
---

# Phase 38 Plan 02: Ratchet de links de modelo opcionales en `check_surface_types.py` — Summary

**ROADMAP SC-3 dejó de ser una medición de una sola vez: un campo `Model | None` o `list[Model] | None` reintroducido en una dataclass exportada ahora enrojece el job `lint`, y el predicado ensanchado deja la línea de resumen del gate byte-idéntica sobre el árbol committeado — colateral cero, medido contra el gate previo, no supuesto.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-08-29T20:28:13Z
- **Completed:** 2026-08-29T20:35:14Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- El ratchet aterrizó con **cero exenciones agregadas** y sin tocar ningún paquete. `_FIELD_EXEMPTIONS` sigue con su única entrada (`UnknownFrame.raw`), la taxonomía sigue en `24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1)` y las `442 fields scanned` no bajaron.
- **Colateral cero probado por identidad, no por conteo.** Se ejecutó el gate PRE-widening (`HEAD~2:tools/check_surface_types.py`) contra el árbol committeado: su línea de resumen es **byte-idéntica** a la del gate ensanchado. El ensanchamiento no movió un solo número sobre el árbol real.
- Los 10 leaves `Literal | None` de matriz quedaron perdonados **estructuralmente y verificado sobre los campos reales**, no sobre una paráfrasis: se corrió `_field_annotation_is_optional_model` contra los 10 `AnnAssign` de `matriz_client/models.py` en las líneas 532, 552, 553, 561, 607, 619, 660, 661, 662 y 669 — los 10 dan `reddens=False`, y ninguno de los 8 alias (`MarketId`, `SegmentId`, `CFICode`, `Currency`, `OrderType`, `Side`, `TimeInForce`, `OrderStatus`) está en el conjunto `ClassDef`, mientras que `InstrumentId`/`Segment`/`Order` sí lo están.
- `packages/matriz-client/` quedó **intacto** (`git status --porcelain` vacío) y su propio fixture RED pasa sin una sola edición: 19 passed. Esa es la prueba de disjunción que el plan pedía.
- El gate sigue siendo **stdlib-`ast` puro**: un chequeo a nivel AST sobre el archivo entero encuentra 0 llamadas a `eval`/`exec`/`get_type_hints`/`issubclass`/`compile`/`__import__` y 0 imports fuera de `ast`/`sys`/`pathlib`/`dataclasses`/`collections`. Un paso de `lint` en CI sigue sin poder disparar `load_dotenv()` ni leer un `.env`.
- El grep de cierre de SC-3 bajó de 12 líneas (pre-38-01) a **10**, y las 10 son leaves de alias `Literal` en matriz permitidos por D-NO-03.

## Task Commits

1. **Task 1: RED — 3 fixtures nuevos + piso de conteo de campos** — `32a18d0` (test)
2. **Task 2: GREEN — predicado ensanchado con discriminador ClassDef y clasificador threaded** — `f50f19a` (feat)
3. **Task 3: prueba de colateral cero** — sin commit propio (verificación read-only; no produce cambio de archivo, como registra la tabla de reversibilidad del plan)

## Files Created/Modified

- `tools/check_surface_types.py` — tres funciones nuevas (`_optional_inner` junto a `_strip_optional`; `_class_names` y `_field_annotation_is_optional_model` justo después del predicado de mapping), un cuarto parámetro `class_names` en `_adjudicate_field` con mensaje distinto para el caso link, el clasificador computado una vez por paquete en `scan_surface_types` y pasado al único call site, y un párrafo nuevo en el docstring de módulo describiendo la tercera dimensión. `_strip_optional` no tiene una sola línea cambiada en su cuerpo (el hunk del diff es una inserción posterior).
- `packages/iol-client/tests/test_surface_types_red.py` — `test_an_optional_model_field_is_caught` (cota inferior, ambas formas sobre una clase, con `Leaf` deliberadamente NO exportada), `test_an_optional_literal_alias_field_is_spared` y `test_an_optional_list_of_any_field_is_spared` (pins de angostura, ambos afirmando que el campo perdonado sigue **contado**), más `assert result.fields >= 400` en `test_gate_is_green_on_the_real_tree`. El helper `_write_fake_package` se reusó, no se re-derivó ni se factorizó (DT-03).

## Decisions Made

- **`_optional_inner` compara `ast.dump` antes/después en vez de reimplementar el peel.** Reimplementarlo habría duplicado el conocimiento de las tres grafías legales de opcional — exactamente la forma del defecto que Phase 37 CR-02 registró, donde `Union[X, None]` se cayó de una de las dos copias. Con la delegación, una cuarta grafía se agrega una vez.
- **El clasificador camina el árbol completo, no `__all__`.** Medido: hoy todo modelo de respuesta está exportado, así que la ruta `__all__` funcionaría. Pero el roster de `ClassDef` no exportadas (la dataclass de request-spec, el token store, los transportes, la policy de decode) muestra que un modelo interno *puede* introducirse, y esa ruta lo perdonaría en silencio. Queda dicho en el docstring que el walk es **clasificador, nunca fuente de candidatos** — el diseño «resolver desde la superficie exportada hacia afuera» sigue intacto.
- **Las tres notas de exclusión están en los DOS docstrings.** El plan las pide en `_class_names` (item 2 de la acción) y su criterio de aceptación las exige en `_field_annotation_is_optional_model`. Se escribieron completas en el clasificador y restatadas en el predicado, porque el predicado es la función a la que aterriza un lector desde una línea roja de CI.
- **`_class_names` se computa después del guard de `import_root is None` y antes del loop de nombres exportados**, tal como pide el plan. Se aceptó a sabiendas que un paquete sin `__init__.py` paga un walk antes de ser reportado como problema: es un checkout roto, no un caso caliente.
- **El re-parse de anotación citada se hace en dos puntos** (sobre la anotación completa y sobre el arm interno), no en uno. Un solo punto perdería una de las dos formas: `"Punta | None"` (todo citado) o `Optional["Punta"]` (el arm citado). El predicado de mapping cubre ambas por el mismo motivo, con su strip-luego-reparse-luego-strip.
- **Se agregó un párrafo al docstring de módulo.** No lo pide el plan, pero el archivo documenta cada dimensión en su cabecera y una tercera dimensión sin entrada ahí se leería como código huérfano.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] El criterio de aceptación por grep sobre el diff cuenta la prosa que el propio plan manda escribir**

- **Found during:** Task 2
- **Issue:** El criterio `git diff tools/check_surface_types.py | grep -cE '^\+.*(eval\(|exec\(|get_type_hints|issubclass)'` debía devolver 0, y devuelve **3**. Las tres coincidencias son prosa de docstring que explica por qué esas construcciones NO se usan — y el propio item 2 de la acción del plan ordena escribirla: *«This is why CONTEXT's third discretion item (`issubclass(SafeModel)` vs. the `Literal` roster) resolves to the ClassDef-name set: `issubclass` is not available here»*. El criterio y la acción se contradicen: es imposible satisfacer ambos con un grep textual.
- **Fix:** Se sustituyó la medición por un chequeo **a nivel AST** sobre el archivo entero (no sólo el diff), que es estrictamente más fuerte: parsea `tools/check_surface_types.py` y busca nodos `ast.Call` cuyo callee sea `eval`/`exec`/`get_type_hints`/`issubclass`/`compile`/`__import__`, más todo `Import`/`ImportFrom` fuera del set stdlib permitido. Resultado: **lista vacía**. La prohibición T-38-07 queda verificada por uso real, no por mención textual.
- **Files modified:** ninguno (corrección de método de medición, no de código). No se bajó ninguna cota ni se relajó ninguna prohibición.
- **Commit:** n/a (verificación)

**2. [Rule 3 - Blocking] `list` como literal en vez de constante de módulo nueva**

- **Found during:** Task 2
- **Issue:** El estilo del archivo prefiere constantes nombradas (`_ANY`, `_OPTIONAL`, `_UNION`, `_MAPPING_BASES`), lo que sugería un `_LIST`. Pero la tabla «Artifacts this phase produces» del plan declara exactamente tres funciones net-new y ningún dato; un `_LIST` sin declarar sería deriva contra la propia verificación del plan.
- **Fix:** Se comparó contra el literal `"list"` con un comentario que dice por qué no hay set de alias acá (no existe `typing.List[Model] | None` en el árbol, y RESEARCH F-6 midió la forma con el builtin).
- **Files modified:** `tools/check_surface_types.py`
- **Commit:** `f50f19a`

Fuera de esos dos puntos de método, el plan se ejecutó tal como está escrito. Los criterios numéricos salieron exactos sin ajuste: `1 failed` en RED con el node ID previsto y `Failed: DID NOT RAISE`, `292 / 289 / 208+1 deselected / 10` en las cuatro suites in-scope, `0 violations` con la taxonomía intacta y el grep D-11 en 10 líneas.

## Issues Encountered

Ninguno bloqueante. Una observación fuera de alcance, registrada y **no** arreglada (scope boundary): el bloque de medición histórica del docstring de módulo cita `330 definitions scanned` mientras el gate imprime `336`. Se verificó que la deriva es **preexistente** — el gate en `HEAD~2` también imprime 336 — y su origen es anterior a esta fase. Ningún criterio de este plan la asserta, y tocarla habría ensanchado el diff hacia un bloque que otra fase escribió.

## TDD Gate Compliance

Secuencia de gates verificada en el log:

1. **RED** — `32a18d0` `test(38-02): ...` — exactamente 1 fallo (`test_an_optional_model_field_is_caught`), y falla por `Failed: DID NOT RAISE <class 'tools.check_surface_types.CheckFailure'>`, no por ImportError ni error de colección. `git status --porcelain tools/` vacío en el momento del commit.
2. **GREEN** — `f50f19a` `feat(38-02): ...` — 15 passed en el fixture, gate en `0 violations`.
3. **REFACTOR** — no aplicado. El cambio GREEN es aditivo (tres funciones nuevas y un parámetro threaded) y no deja nada que limpiar; un commit `refactor` vacío sería ruido.

## Verification Results

| Check | Resultado |
|---|---|
| `pytest packages/iol-client/tests/test_surface_types_red.py -q` (RED, pre-Task 2) | `1 failed, 14 passed` — `DID NOT RAISE` |
| `pytest packages/iol-client/tests/test_surface_types_red.py -q` (GREEN) | `15 passed` |
| `pytest packages/iol-client -q` | `292 passed` (289 baseline + 3 tests nuevos) |
| `pytest packages/higyrus-client -q` | `289 passed` |
| `pytest packages/ambito-financiero-client -q` | `208 passed, 1 deselected` |
| `pytest packages/wallets-client -q` | `10 passed` |
| `pytest packages/matriz-client/tests/test_surface_types_red.py -q` | `19 passed`, archivo sin editar |
| `tools/check_surface_types.py` | exit 0 — `442 fields scanned`, `24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1)`, `0 violations` |
| Gate PRE-widening (`HEAD~2`) sobre el mismo árbol | línea de resumen **byte-idéntica** — colateral cero por identidad |
| `tools/check_decode_intactness.py` | exit 0 — 5 copias al hash canónico `a1f00c824348164c` |
| `tools/check_uniform_structure.py` | exit 0 |
| `mypy packages/iol-client` | `Success: no issues found in 30 source files` |
| `mypy packages/higyrus-client` | `Success: no issues found in 26 source files` |
| `ruff check` + `ruff format --check` (gate + iol) | limpio, 31 archivos |
| Grep D-11 sobre `packages/*/src/*/models.py` | `10` líneas, todas matriz en 532/552/553/561/607/619/660/661/662/669 |
| `git diff --name-only -- uv.lock` | vacío |
| `git status --porcelain` | vacío tras ambos commits |

Verificación empírica adicional del predicado (script descartable, no commiteado):

| Anotación | `reddens` |
|---|---|
| `Punta \| None` | `True` |
| `list[Punta] \| None` | `True` |
| `Punta` | `False` (el wrapper es la violación, no el link) |
| `list[Punta]` | `False` |
| `list[Any] \| None` | `False` (D-01b intacto) |
| `dict[str, Punta] \| None` | `False` (exclusión declarada) |
| `str \| None` | `False` |

## Threat Mitigations Verified

| Threat ID | Verificación |
|---|---|
| T-38-06 (Tampering / el control mismo) | 0 entradas agregadas a `_FIELD_EXEMPTIONS` (`git diff \| grep -c '^+.*_FIELD_EXEMPTIONS\['` → 0), ninguna cota bajada, `packages/matriz-client/` intacto, y los dos pins de angostura hacen visible un sobre-angostamiento igual que la cota inferior hace visible un sobre-ensanchamiento. |
| T-38-07 (Info Disclosure / Elevation, ASVS V14) | Chequeo AST sobre el archivo entero: 0 llamadas a `eval`/`exec`/`get_type_hints`/`issubclass`/`compile`/`__import__`, 0 imports fuera de `ast`/`sys`/`pathlib`/`dataclasses`/`collections`. El grep anclado de import de paquete devuelve 0. Un paso de `lint` no puede leer un `.env`. |
| T-38-08 (DoS / runtime de CI) | Aceptado. `_class_names` agrega un `rglob("*.py")` + parse por paquete, computado **una vez** por paquete y no por campo. La suite completa de los 4 paquetes in-scope y los 3 gates corren en el mismo orden de tiempo que antes. |
| T-38-09 (Repudiation / línea de resumen) | Taxonomía y conteos afirmados sin cambio y, más fuerte, la línea entera probada byte-idéntica contra el gate previo. El piso `result.fields >= 400` impide que un scan colapsado reporte verde. |
| T-38-10 (Spoofing) | Aceptado sin cambio — no hay identidad, sesión ni token en ningún camino de este plan. |
| T-38-SC (supply chain) | Aceptado. Cero instalaciones de paquetes; `git diff --name-only -- uv.lock` vacío. |

## Known Stubs

Ninguno. Las tres funciones nuevas están cableadas al único call site del gate y ejercitadas por tres tests que afirman valores medidos sobre árboles sintéticos y sobre el árbol real.

## Threat Flags

Ninguna superficie nueva. El plan no toca fuente de ningún paquete cliente, ningún endpoint, ningún camino de auth ni ningún handler de entrada de usuario: agrega tres funciones puras sobre nodos `ast` y tres tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **38-03 (callout BREAKING en el README de iol)** desbloqueado: sin dependencia sobre este plan más allá de que el árbol sigue verde.
- **38-04 (censo)** desbloqueado y con la evidencia que cita ya producida: el grep D-11 en 10 líneas con su salida verbatim, la línea de resumen del gate y la prueba de intactness de matriz están todas en la tabla de arriba.
- **Phase 39 (contabilidad de triples)**: la aritmética de F-10 no se movió — este plan no agrega ni retira triples, sólo un control.
- **Phase 40** sigue siendo dueña del bump: ni `__version__` ni ningún `pyproject.toml` se tocó.
- Sin blockers.

## Self-Check: PASSED

- `tools/check_surface_types.py` y `packages/iol-client/tests/test_surface_types_red.py` verificados en disco; `38-02-SUMMARY.md` verificado en disco.
- Commits `32a18d0` y `f50f19a` verificados con `git log --oneline`.
- Las 10 líneas de matriz citadas re-verificadas ejecutando el predicado nuevo contra esos mismos `AnnAssign` por número de línea, no por grep de texto.

---
*Phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets*
*Completed: 2026-08-29*
</content>
</invoke>
