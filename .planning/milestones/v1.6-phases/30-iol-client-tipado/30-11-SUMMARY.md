---
phase: 30-iol-client-tipado
plan: 11
subsystem: testing
tags: [verification-harness, redaction, ast-lock, regression-lock, tdd, gap-closure]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado (plan 09)
    provides: "_raw_exception_renders + _OFFENDING_SOURCE / _COMPLIANT_SOURCE / _OFFENDING_LINES y la sección 3 de test_main_iol_exception_redaction.py"
  - phase: 30-iol-client-tipado (plan 10)
    provides: "_redacted_excepthook + _install_redacted_excepthook — el caso discriminante del censo de renderers (un consumidor anotado con un tipo de excepción que NO debe contarse)"
provides:
  - "_raw_exception_renders ampliado — 8 reglas: stringificación (repr/str/format), interpolación, kwarg de append_finding, lectura de atributo con fuga, delegación no sancionada, formateo por porcentaje, sys.exc_info() en handlers sin nombre, y alias de un nivel"
  - "_LEAKY_EXC_ATTRS + _SANCTIONED_DELEGATES + _STRINGIFYING_CALLS — la política del lock como tres decisiones nombradas en vez de literales dispersos por el walk"
  - "_declared_exception_renderers(source) -> list[str] — censo de renderers por FORMA (gate de anotación + predicado de lectura), FunctionDef y AsyncFunctionDef, a cualquier scope"
  - "matriz de falsificación _WR01_ROWS — las 11 filas de 30-REVIEW.md WR-01 como fuentes sintéticos completos, parametrizadas"
  - "6 casos de censo: auto-detección, consumidor-no-renderer, y las tres bypasses de WR-02, más control negativo"
affects: [30-VERIFICATION quinto ciclo, 33-LIVE-TYP-01 (audit de los otros cinco main_*.py)]

actuals:
  tokens: 26000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Flagging en el SITIO DE LLAMADA en vez de análisis del callee: la excepción sólo sale del handler por una arista, así que la decisión se toma donde es decidible"
    - "Gate de anotación como acotador del conjunto candidato — sin él, un predicado de lectura-de-atributo marca todos los probes"
    - "Aserción por igualdad contra el nombre sancionado, nunca contra una lista vacía: un censo que deja de detectar es tan roto como uno que no detecta al segundo"
    - "Una forma prohibida por LÍNEA en el control positivo, con la tupla de líneas pinneada, para que un doble-marcado sea visible como ambigüedad"
    - "Frontera declarada explícitamente en el docstring (aliasing multi-nivel y flujo fuera del handler = NO VERIFICADO, no permitido)"

key-files:
  created: []
  modified:
    - verification/test_main_iol_exception_redaction.py

key-decisions:
  - "AD-30-11-01 ejecutada tal como fue firmada, split por rol: el bypass del segundo renderer se cierra en DOS lugares con predicados distintos. (a) En el sitio de llamada dentro del handler — la regla de delegación no sancionada marca el nombre bindeado entregado a cualquier callee fuera de {_redacted_exc, type, isinstance, getattr}, sin analizar al callee. (b) En la declaración — el censo con gate de anotación. Se confirmó empíricamente por qué NO se puede hacer con un solo análisis whole-file: el snippet de fix de WR-02 aplicado verbatim devuelve [] contra este driver (el cuerpo de _redacted_exc no tiene repr/str ni .message/.args — usa getattr, type(exc).__name__ y cuatro lecturas de IOLDecodeError), y cualquier predicado laxo suficiente para atraparlo atrapa también todos los probes."
  - "status_code queda FUERA de _LEAKY_EXC_ATTRS por decisión, no por olvido, y el comentario del constante lo dice: WR-03 (22 lecturas inline de exc.status_code en argumentos diff=) sigue abierto y no escalado; incluirlo fallaría el lock del driver sobre 22 sitios pre-existentes. Cerrar WR-03 es lo que debe habilitar esa entrada, nunca al revés."
  - "El predicado del censo distingue RENDERIZAR de PASAR: leer un atributo del parámetro, llamar getattr sobre él, stringificarlo (repr/str/format) o interpolarlo directo cuenta; entregarlo a otra función NO cuenta. Esa es la única razón por la que _redacted_excepthook —anotado con un tipo de excepción por 30-10— queda correctamente afuera. Un predicado que contara la delegación habría hecho fallar el lock sobre el fix de 30-10 sin que existiera ninguna fuga."
  - "La RED de la Task 2 usa un PLACEHOLDER que reproduce la semántica shippeada (filtro de tree.body por nombre) en vez de dejar el símbolo indefinido: un NameError habría dejado el commit RED con 6 errores F821 de ruff, y el gate 10 exige ruff limpio. El placeholder es además una RED más informativa — los tres bypasses fallan devolviendo ['_redacted_exc'], que es exactamente el modo de falla que WR-02 documenta."
  - "El control positivo mantiene la invariante de UNA forma marcada por línea. La línea 15 (alias = exc) no marca nada por diseño: registra el alias, y la marca cae en la línea 16 donde el alias se stringifica. Sin eso, la aserción de la tupla de líneas sería ambigua."

patterns-established:
  - "Matriz de falsificación derivada de una tabla de review: las 11 filas de WR-01 viven como constante parametrizada, así que la métrica del review (10 MISSED) es literalmente el criterio de la suite"
  - "Caso de AUTO-DETECCIÓN como guard anti-vacuidad de un detector: el censo debe probar que sigue detectando al primer renderer, no sólo que detecta al segundo"

requirements-completed: []

coverage:
  - id: D1
    description: "_raw_exception_renders marca las 11 formas de la tabla WR-01 de 30-REVIEW.md (era 3), incluida la lectura de exc.message que es literalmente resp.text, sin marcar el control conforme ni un solo sitio del main_iol.py post-30-10"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "verification/test_main_iol_exception_redaction.py::test_the_detector_flags_a_synthetic_offending_source (11 offenders en las líneas exactas) + ::test_the_detector_flags_every_shape_of_the_review_table (11 casos parametrizados)"
        status: pass
      - kind: unit
        ref: "::test_the_detector_accepts_a_synthetic_compliant_source ([]) + ::test_no_except_handler_in_the_driver_renders_its_exception_raw ([] con 22 type(exc).__name__ y 22 exc.status_code en el archivo)"
        status: pass
    human_judgment: false
  - id: D2
    description: "_declared_exception_renderers censa por forma y no por nombre: detecta _redacted_exc en el driver real, ignora su consumidor _redacted_excepthook, y devuelve un segundo nombre para cada una de las tres bypasses de WR-02"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "::test_the_census_detects_the_sanctioned_renderer_in_the_real_driver (== ['_redacted_exc']) + ::test_the_census_treats_the_excepthook_as_a_consumer_not_a_renderer"
        status: pass
      - kind: unit
        ref: "::test_the_census_catches_a_renderer_under_another_name / ::test_the_census_catches_an_async_renderer / ::test_the_census_catches_a_nested_or_conditional_renderer / ::test_the_census_ignores_ordinary_driver_shaped_functions"
        status: pass
    human_judgment: false
  - id: D3
    description: "main_iol.py, packages/ y .planning/verification/ byte-inalterados; las tres suites hermanas verdes y byte-idénticas; iol-client verde"
    verification:
      - kind: integration
        ref: "git diff --exit-code main_iol.py packages/ .planning/verification/ (exit 0); uv run pytest packages/iol-client -q (242 passed); ruff check + format --check limpios"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-08-23
status: complete
---

# Phase 30 Plan 11: El lock de regresión AST empieza a enforcear lo que dice enforcear Summary

**`_raw_exception_renders` pasa de marcar 3 de 11 formas de fuga a marcar las 11 —incluida `exc.message`, que es literalmente `resp.text`— y el conteo de renderers que matcheaba por nombre se reemplaza por un censo por forma que falsifica las tres bypasses documentadas y prueba, con una igualdad contra el nombre sancionado, que sigue detectando al primero.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-23T18:12:31Z
- **Completed:** 2026-08-23T18:20:52Z
- **Tasks:** 2 (ambas TDD, RED → GREEN)
- **Files modified:** 1 (`verification/test_main_iol_exception_redaction.py`) — superficie de test únicamente

## Accomplishments

- **WR-01 cerrado.** El detector recorre ahora **todo** `ast.ExceptHandler` —también los que no bindean nombre, que la versión de 30-09 salteaba con un `continue`— y aplica ocho reglas en vez de tres. La que carga el peso es la **lectura de atributo con fuga**: `IOLAPIError.__init__` guarda `resp.text` en `self.message` y lo mete adentro del mensaje que pasa a `super().__init__`, de donde sale `.args`; `append_finding(actual=exc.message)` estaba a un token de distancia de cada uno de los 32 sitios que 30-09 barrió y pasaba completamente sin marca.
- **WR-02 cerrado, en dos lugares y con predicados distintos** (AD-30-11-01). En el **sitio de llamada**, la regla de delegación no sancionada marca el nombre bindeado entregado a cualquier callee fuera de `{_redacted_exc, type, isinstance, getattr}` — cierra `print(exc)`, `safe_print(exc, ...)` y `_render(exc)` sin analizar al callee, porque un handler es la única forma que tiene el driver de obtener el objeto excepción. En la **declaración**, `_declared_exception_renderers` censa por forma, matcheando `FunctionDef` y `AsyncFunctionDef` a cualquier scope.
- **El caso que atrapa al bug del propio review.** `test_the_census_detects_the_sanctioned_renderer_in_the_real_driver` asierta `== ["_redacted_exc"]`, nunca contra una lista vacía. El snippet de fix que propone `30-REVIEW.md` WR-02, aplicado verbatim, devuelve `[]` contra este driver — su predicado busca `repr`/`str` o `.message`/`.args`, y el cuerpo de `_redacted_exc` no tiene ninguno de los dos. Escrito contra `[]` habría pasado verde para siempre censando nada.
- **Cero falsos positivos.** El control negativo quedó **byte-inalterado** y sigue verde, y el `main_iol.py` post-30-10 devuelve cero offenders pese a sus 22 `type(exc).__name__` y 22 `exc.status_code`.
- **Ambos detectores probados no-vacuos** por sondas temporales revertidas desde copias en scratchpad (gates 13 y 14, detalle abajo).

## Task Commits

1. **Task 1: ampliar el detector de sitios de handler** — `680af2a` (test, RED) → `641d325` (test, GREEN)
2. **Task 2: censo falsificable de renderers** — `cc82304` (test, RED) → `b9cf736` (test, GREEN)

RED estrictamente antes de GREEN en ambas tareas.

### Estados RED medidos

| Tarea | RED medido | Modo de falla observado |
|---|---|---|
| 1 | **11 failed / 25 passed** | Control positivo: `AssertionError: el detector encontró 3, se esperaban 11: [(6, 'repr() sobre exc'), (7, 'interpolación de exc'), (8, 'append_finding(actual=exc)')]`. Los otros 10 son las filas de `_WR01_ROWS` que el detector shippeado no marca — **exactamente las 10 que el review midió como MISSED**; la undécima (`f"{exc!r}"`) pasó en RED porque ya estaba cubierta. |
| 2 | **3 failed / 39 passed** | Los tres bypasses de WR-02 devuelven `censo: ['_redacted_exc']` — el segundo renderer es invisible en las tres formas. La auto-detección y el control negativo pasan en RED **por construcción** bajo el placeholder (el filtro por nombre sí detecta `_redacted_exc` y sí ignora funciones ordinarias): son los guards anti-vacuidad de GREEN, no falsificadores del estado shippeado. Su poder se demuestra en el gate 14. |

**Nota sobre la RED de la Task 2.** Se usó un **placeholder** que reproduce la semántica shippeada (filtro de `tree.body` por `ast.FunctionDef` llamado `_redacted_exc`) en vez de dejar el símbolo indefinido. Un `NameError` habría dejado el commit RED con **6 errores `F821`** de ruff y el gate 10 exige `ruff check verification` limpio en cada commit. El placeholder produce además una RED más informativa: falla por el modo de falla exacto que WR-02 documenta, no por un símbolo ausente.

## Gate 6 — cobertura fila por fila de la tabla WR-01

Las 11 filas viven como `_WR01_ROWS` (fuentes sintéticos completos) y corren parametrizadas en `test_the_detector_flags_every_shape_of_the_review_table`. **10 MISSED → 11 FLAGGED.**

| # | Forma (30-REVIEW.md WR-01) | Antes | Después | Regla que la marca (etiqueta emitida) |
|---|---|---|---|---|
| 1 | `append_finding("p", actual=exc.message)` | MISSED | **FLAGGED** | atributo con fuga — `lectura de exc.message` |
| 2 | `append_finding("p", actual=f"{exc.message}")` | MISSED | **FLAGGED** | atributo con fuga — `lectura de exc.message` |
| 3 | `reason = f"login: {exc.args}"` | MISSED | **FLAGGED** | atributo con fuga — `lectura de exc.args` |
| 4 | `append_finding("p", actual="%s" % exc)` | MISSED | **FLAGGED** | formateo por porcentaje — `formateo % sobre exc` |
| 5 | `append_finding("p", actual="{}".format(exc))` | MISSED | **FLAGGED** | stringificación ampliada — `format() sobre exc` |
| 6 | `print(exc)` | MISSED | **FLAGGED** | delegación no sancionada — `delegación de exc a print()` |
| 7 | `safe_print(exc, secrets=[])` | MISSED | **FLAGGED** | delegación no sancionada — `delegación de exc a safe_print()` |
| 8 | `def _render(e): return str(e)` + `actual=_render(exc)` | MISSED | **FLAGGED** | delegación no sancionada — `delegación de exc a _render()` |
| 9 | `e2 = exc; append_finding("p", actual=str(e2))` | MISSED | **FLAGGED** | alias de un nivel + stringificación — `str() sobre e2` |
| 10 | `except Exception:` + `str(sys.exc_info()[1])` | MISSED | **FLAGGED** | `sys.exc_info()` en handler sin nombre |
| 11 | `return ProbeResult("n","FINDING", f"{exc!r}")` | FLAGGED | **FLAGGED** | interpolación (regla pre-existente) — `interpolación de exc` |

### Control positivo — una forma por línea, líneas pinneadas

`_OFFENDING_SOURCE` pasó de 3 a **11** ocurrencias plantadas, `_OFFENDING_LINES = (6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 18)`, y el control asierta **tanto la cantidad como la tupla exacta**. La invariante de *una entrada marcada por línea* se sostuvo sin necesidad de partir ninguna línea: la línea 15 (`alias = exc`) no marca nada por diseño —registra el alias— y la marca cae en la 16, donde el alias se stringifica.

```
(6,  'repr() sobre exc')                      (12, 'delegación de exc a print()')
(7,  'interpolación de exc')                  (13, 'formateo % sobre exc')
(8,  'append_finding(actual=exc)')            (14, 'format() sobre exc')
(9,  'lectura de exc.message')                (16, 'str() sobre alias')
(10, 'lectura de exc.args')                   (18, 'sys.exc_info() dentro de un handler')
(11, 'delegación de exc a _render()')
```

## Gate 7 — las tres bypasses de WR-02, falsificadas

Cada caso asierta la **lista devuelta**, no su largo.

| Bypass | Por qué era alcanzable | Fuente sintético | Censo devuelto |
|---|---|---|---|
| **1 — otro nombre** | Filtraba por `node.name == "_redacted_exc"`. Peor: el cuerpo del duplicado también es invisible para `_raw_exception_renders`, porque ahí la excepción llega como **parámetro** y nunca queda bindeada por un `ast.ExceptHandler`. | `_CENSUS_RENAMED_DUPLICATE` | `['_redacted_exc', '_fmt_exc']` |
| **2 — `async def`** | Sólo se matcheaba `ast.FunctionDef`. | `_CENSUS_ASYNC_DUPLICATE` | `['_redacted_exc', '_redacted_exc']` |
| **3 — anidada / condicional** | Sólo se escaneaba `tree.body` (nivel de módulo). | `_CENSUS_NESTED_DUPLICATE` | `['_redacted_exc', '_inner_exc', '_debug_exc']` |
| **Control negativo** | — | `_CENSUS_NEGATIVE_CONTROL` | `[]` |
| **Driver real** | — | `main_iol.py` | `['_redacted_exc']` |

El control negativo es lo que impide que el censo degenere en ruido: contiene un probe con forma de driver (`probe_get_quote_sync(client: Client)`) que lee atributos de su parámetro e interpola en un f-string, y un consumidor (`_report(exc: IOLAPIError)`) que sólo entrega su excepción al renderer sancionado. Ninguno cuenta. `_redacted_excepthook` y `_install_redacted_excepthook` están ausentes del censo del driver real por la misma razón — **pasar no es renderizar**, y ése es el caso discriminante que 30-10 introdujo.

## Verification — todos los gates medidos

| # | Gate | Esperado | **Medido** |
|---|------|----------|-----------|
| 1 | `uv run pytest verification/test_main_iol_exception_redaction.py -q` | 0 failed, 0 skipped, ≥ 25+6 = 31 passed | **42 passed, 0 failed, 0 skipped** (+17 vs 30-10) |
| 2 | Control positivo | 11 offenders, tupla de líneas exacta | **11 offenders**, `(6,7,8,9,10,11,12,13,14,16,18)` |
| 3 | Control negativo | `[]` y `_COMPLIANT_SOURCE` byte-inalterado | **`[]`**; el diff no toca ninguna línea de `_COMPLIANT_SOURCE` |
| 4 | Lock del driver | `[]` contra el `main_iol.py` real | **`[]`** — cero falsos positivos sobre 22 `type(exc).__name__` y 22 `exc.status_code` |
| 5 | Censo de renderers | `== ["_redacted_exc"]` | **`['_redacted_exc']`** |
| 6 | Tabla de cobertura WR-01 | 10 MISSED → 11 FLAGGED | **registrada arriba, fila por fila** |
| 7 | Tabla de bypasses WR-02 | las tres falsificadas | **registrada arriba, con las listas devueltas** |
| 8 | `pytest verification/test_main_iol_fid_seed.py test_main_iol_raw_wire_drift.py test_findings_fid_seed.py -q` | all passed, sin cambio vs 30-10 | **34 passed** (5 + 22 + 7); `git diff --exit-code` sobre los tres → **exit 0** |
| 9 | `uv run pytest packages/iol-client -q` | `242 passed` | **242 passed** |
| 10 | `ruff check verification` + `ruff format --check verification` | limpio | **`All checks passed!` / `48 files already formatted`** |
| 11 | **Reversibilidad** — `git diff --exit-code main_iol.py packages/ .planning/verification/` | exit 0 | **exit 0** |
| 12 | `git status --porcelain` | sólo el archivo del plan modificado | **OK** — el archivo del plan quedó committeado; lo pendiente es state/artefactos previos al plan (`30-VERIFICATION.md`, `.gsd/`, cache de research), todos pre-existentes al arranque |
| 13 | No-vacuidad del detector ampliado | el control positivo falla con el detector mudo | **demostrado** (detalle abajo) |
| 14 | No-vacuidad del censo | el gate 5 falla con el censo mudo | **demostrado** (detalle abajo) |

### Gate 13 — cómo se demostró y cómo se revirtió

Copia del archivo guardada en scratchpad; se insertó `return []  # GATE-13 PROBE` inmediatamente después de `ast.parse(source)` en `_raw_exception_renders`. Resultado: **12 failed / 24 passed**.

Caen las 12 aserciones que dependen de que el detector marque algo: el control positivo y **las 11 filas de `_WR01_ROWS` sin excepción**, incluida la fila 11 que ya estaba cubierta antes de este plan. Los tres tests que siguen verdes son los que asertan **ausencia** (el control negativo y el lock del driver, que un detector mudo satisface por construcción) — ésa es precisamente la razón por la que el control positivo existe.

Revertido copiando de vuelta desde el scratchpad. Verificado: `grep -c "GATE-13 PROBE"` → `0`, `pytest` → 42 passed, `ruff` limpio.

### Gate 14 — cómo se demostró y cómo se revirtió

Misma técnica: `return []  # GATE-14 PROBE` después de `ast.parse(source)` en `_declared_exception_renderers`. Resultado: **5 failed / 37 passed**.

Los 5 que caen son la auto-detección, los tres bypasses y el lock `test_the_driver_declares_exactly_one_exception_renderer` (`== ["_redacted_exc"]` contra `[]`). **Ése es el punto entero del gate:** un censo que no detecta nada falla acá de forma ruidosa en vez de pasar verde — es el modo de falla del snippet de fix del propio review. Los dos que siguen verdes son los que asertan ausencia (el consumidor `_redacted_excepthook` y el control negativo), satisfechos por construcción por un censo mudo.

Revertido copiando de vuelta desde el scratchpad. Verificado: `grep -c "GATE-14 PROBE"` → `0`, `pytest` → 42 passed, `ruff` limpio.

## Decisions Made

Ver `key-decisions` en el frontmatter. La sustantiva es **AD-30-11-01**, ejecutada tal como fue firmada — *both, split by role* — y la predicción del planner se confirmó en la ejecución: no existe un único análisis whole-file que distinga al renderer sancionado de los probes ordinarios. `_redacted_exc` no contiene ni `repr`/`str` ni lecturas de `.message`/`.args`; usa `getattr`, `type(exc).__name__` y cuatro lecturas de atributos de `IOLDecodeError`. Cualquier predicado laxo suficiente para atraparlo por "lee atributos de un parámetro" atrapa también todos los probes, que leen atributos de su parámetro `client`. Por eso el bypass se cierra en el **sitio de llamada** (donde es decidible sin analizar al callee) y el censo sólo tiene que atrapar un duplicado del renderer, lo que el **gate de anotación** hace limpiamente.

La segunda decisión que vale registrar es la exclusión deliberada de `status_code` de `_LEAKY_EXC_ATTRS`, documentada en el comentario de la constante misma: agregarlo haría fallar el lock del driver sobre los 22 sitios `diff=f"status_code={exc.status_code!r}"` que WR-03 enumera y que siguen abiertos y **no escalados**. Cerrar WR-03 es lo que debe habilitar esa entrada, nunca al revés.

## Deviations from Plan

**Una sola, menor, bajo Regla 3 (desbloqueo) — la forma de la RED de la Task 2.**

El plan pedía escribir los seis casos del censo "contra el código shippeado", lo que literalmente implica que `_declared_exception_renderers` no exista todavía y los casos fallen con `NameError`. Medido: eso deja el commit RED con **6 errores `F821`** de ruff, y el gate 10 del propio plan exige `ruff check verification` limpio. Se resolvió introduciendo en la RED un **placeholder** que reproduce verbatim la semántica shippeada (filtro de `tree.body` por `ast.FunctionDef` llamado `_redacted_exc`), reemplazado por la implementación real en GREEN.

Consecuencia sobre lo que la RED demuestra, registrada con honestidad: bajo el placeholder fallan **3** casos (los tres bypasses) en vez de 6 — la auto-detección y el control negativo pasan por construcción, porque el filtro por nombre efectivamente detecta `_redacted_exc` e ignora funciones ordinarias. El poder falsificador de esos dos casos no queda sin demostrar: es exactamente lo que mide el **gate 14**, donde ambos… más precisamente la auto-detección y el lock del driver, caen en cuanto el censo enmudece. La RED resultante es además más informativa que un `NameError`: falla por el modo de falla concreto que WR-02 documenta.

No hubo auto-fixes bajo las Reglas 1-2, ni escalaciones bajo la Regla 4, ni gates de autenticación. **Cero instalaciones de paquetes** (`ast` y `pathlib` son stdlib; `pytest` ya estaba en `uv.lock`), así que el Package Legitimacy Gate se satisface por construcción tal como el `<threat_model>` anticipó (T-30-11-SC). Ningún archivo fuera de `verification/test_main_iol_exception_redaction.py` fue tocado (T-30-11-06, gate 11 exit 0).

## Issues Encountered

Ninguno más allá del `F821` descrito arriba. En particular, **ninguna regla ampliada marcó un sitio real de `main_iol.py`** — el escenario que el `<scope_boundary>` obligaba a escalar en vez de resolver editando el driver no llegó a ocurrir: el lock del driver devuelve `[]` desde el primer run de GREEN.

## Frontera residual — lo que este plan deja explícitamente SIN VERIFICAR

Declarado en el docstring de `_raw_exception_renders` con esas palabras, porque WR-01 pide precisamente eso en su párrafo de cierre: una frontera honesta es la mitigación, y la redacción anterior sugería una cobertura que no existía.

- **Aliasing de más de un nivel** (`a = exc`; `b = a`; `str(b)`): el segundo eslabón es invisible. El censo de alias es de **una** pasada, sin punto fijo.
- **Flujo de datos que sale del handler**: guardar el nombre bindeado en un atributo, una lista o un global y leerlo en otro lado.
- **El cuerpo de un callee sancionado**: se confía en `_redacted_exc` por su contrato propio (sección 1) y por el censo, no por el detector de handlers.
- **Anotaciones escritas como string literal** (`def f(e: "IOLAPIError")`): el gate de anotación no las resuelve. El repo entero corre con `from __future__ import annotations`, que deja las anotaciones como expresiones reales en el AST, así que la forma no aparece.

## Carry-forwards deliberadamente NO cerrados

| Item | Origen | Por qué queda abierto |
|---|---|---|
| **WR-03** | 30-REVIEW.md | 22 lecturas inline de `exc.status_code` en argumentos `diff=`. No escalado a BLOCKER. `status_code` queda fuera de `_LEAKY_EXC_ATTRS` por eso; la exclusión está documentada en el comentario de la constante para que el próximo lector no la lea como olvido. |
| **WR-04** | 30-REVIEW.md | `_redacted_exc` puede levantar si `status_code` es una property que levanta. Fuera de scope. |
| **WR-05** | 30-REVIEW.md | Sin cobertura end-to-end de redacción async. |
| **WR-06** (numeración de 30-REVIEW) | 30-REVIEW.md | Un `ultimoPrecio` legítimamente cero emite un finding OPEN permanente. |
| **IN-01 .. IN-05** | 30-REVIEW.md | Ninguno escalado a BLOCKER. |
| **Los otros cinco `main_*.py`** | 30-08 threat register | Es el audit de la **Phase 33**. Los **dos** detectores toman un string de fuente precisamente para que ese audit sea una parametrización sobre nombres de archivo y no una reescritura. |
| Anti-vacuidad del probe 13, numeral del detalle PASS, binding de `DecodeScope` | 30-09-SUMMARY.md | Carry-forwards viejos, sin cambio. |

**Riesgo de numeración, re-registrado por tercera vez:** la lista de carry-forwards de 30-09-SUMMARY.md usa la numeración WR de la revisión *anterior*, donde `WR-01` significaba "anti-vacuidad del probe 13". El `30-REVIEW.md` actual reusa `WR-01` para la ceguera del lock AST y `WR-02` para el conteo de renderers — los dos ítems cerrados acá. Son ítems distintos.

**`TYP-01` NO se marcó completo en `.planning/REQUIREMENTS.md`**, por instrucción explícita del `<output>` del plan: la fase debe un quinto ciclo de verificación y el operador ya revirtió un `mark-complete` prematuro de este requisito una vez (deviación 3 de 30-09-SUMMARY.md). Flipearlo es decisión del verifier, no de un plan.

## Known Stubs

Ninguno. Las tres funciones nuevas (`_bound_names`, `_annotates_an_exception`, `_reads_the_exception`) y las dos reescritas devuelven resultados computados sobre el AST real; ninguna tiene una rama placeholder ni una fuente de datos sin cablear. El placeholder que existió durante la RED de la Task 2 fue reemplazado en GREEN (`b9cf736`) — `grep -c "PLACEHOLDER RED"` sobre el archivo committeado devuelve `0`.

## Threat Flags

Ninguna superficie de seguridad nueva fuera del `<threat_model>` del plan. El plan no toca código de producción: no abre endpoints de red, ni caminos de auth, ni patrones de acceso a archivos, ni cambios de esquema en una frontera de confianza. Las mitigaciones T-30-11-01 a T-30-11-06 están todas implementadas y pinneadas por un test; T-30-11-SC se satisface por construcción (cero instalaciones de paquetes).

## Next Phase Readiness

- **Quinto ciclo de 30-VERIFICATION.md**: el WARNING del cuarto ciclo sobre la fila 6 de `Required Artifacts` (`_raw_exception_renders` ciego a `ast.Attribute`) y el de `test_the_driver_declares_exactly_one_exception_renderer` están cerrados con evidencia offline reproducible. La afirmación de 30-09-SUMMARY.md de que AD-30-09-01 queda "enforced going forward" ahora es cierta del lock, no sólo del código.
- **Phase 33** hereda el audit de los otros cinco drivers con **dos** detectores listos para apuntar: ambos toman un string de fuente, así que el trabajo es una parametrización sobre nombres de archivo. Se anticipa que los otros cinco drivers **fallarán** el lock — ninguno pasó por el barrido de 30-08/30-09 — y ése es el punto del audit.
- La corrida viva contra `api.invertironline.com` sigue siendo del operador y este plan no la mueve: es superficie de test únicamente.

## Self-Check: PASSED

- Archivos: `verification/test_main_iol_exception_redaction.py`, `.planning/phases/30-iol-client-tipado/30-11-SUMMARY.md` — los 2 presentes en disco.
- Commits: `680af2a`, `641d325`, `cc82304`, `b9cf736` — los 4 presentes en `git log`.

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-23*
