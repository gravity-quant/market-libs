---
phase: 30-iol-client-tipado
plan: 13
subsystem: verification-driver
tags: [redaction, ast-lock, durability, getattr, census, tdd, gap-closure]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado (plan 09)
    provides: "_raw_exception_renders, _called_name, _LEAKY_EXC_ATTRS, _SANCTIONED_DELEGATES — el detector de sitios de handler y sus constantes de política"
  - phase: 30-iol-client-tipado (plan 11)
    provides: "el widening de 8 reglas + el censo por forma (_declared_exception_renderers, _reads_the_exception, _WR01_ROWS, _OFFENDING_LINES) — la superficie exacta que este plan amplía"
  - phase: 30-iol-client-tipado (plan 12)
    provides: "la forma post-fix del camino de crash — _redacted_excepthook como consumidor y _emit_crash_report(detail: str, tb) que NO recibe la excepción; es el caso vivo que la regla de delegación genérica de este plan debe clasificar bien"
provides:
  - "regla 9 de _raw_exception_renders — getattr adjudicado sobre su argumento de nombre de atributo, ANTES del corto-circuito de _SANCTIONED_DELEGATES"
  - "regla 10 de _raw_exception_renders — getattr con nombre de atributo no constante, marcado conservadoramente"
  - "_LEAKY_EXC_ATTRS extendido con __dict__ — cubre las dos escrituras (directa e indirecta) de una sola constante"
  - "_CENSUS_SANCTIONED_DELEGATES — constante de política propia del censo, deliberadamente distinta de _SANCTIONED_DELEGATES (sin getattr)"
  - "_reads_the_exception con la regla de formateo % espejada de su detector hermano + una regla única de delegación no sancionada que subsume el caso especial de getattr/_STRINGIFYING_CALLS y cubre keywords"
  - "_FIFTH_CYCLE_BYPASS_ROWS (4 filas) + _FIFTH_CYCLE_ALLOWED_ROWS (2 filas) — la matriz de falsificación del quinto ciclo, separada de _WR01_ROWS"
  - "_CENSUS_PERCENT_DUPLICATE, _CENSUS_PRINTING_DUPLICATE, _CENSUS_KEYWORD_DUPLICATE, _CENSUS_SYNTHETIC_CONSUMER — cuatro fuentes sintéticos nuevos del censo"
affects: [30-VERIFICATION sexto ciclo, 33-LIVE-TYP-01 (parametrización de los tres detectores sobre los otros cinco main_*.py)]

actuals:
  tokens: 24000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Una exención de lock se keyea sobre la OPERACIÓN, nunca sobre el nombre del callee: sancionar `getattr` como callee permitió `getattr(exc, \"message\", \"\")` durante dos ciclos"
    - "Una sola constante gobierna las dos escrituras de la misma lectura (`<n>.message` y `getattr(<n>, \"message\")`), que es lo que impide que deriven"
    - "Lo no analizable se marca, no se permite: un nombre de atributo dinámico derrota el análisis del lock, así que la dirección estricta es el default correcto"
    - "Delegación invertida a deny-by-default en el censo: cuenta como render entregar la excepción a cualquiera salvo al renderer sancionado — al revés de la lista de formas reconocidas que tenía antes"
    - "Widening pinneado en las DOS direcciones: cada regla nueva llega con su fila positiva y su fila negativa, porque un lock que sobre-marca es un lock que el próximo autor borra"
    - "Dos constantes de política para dos preguntas distintas, explícitamente no fusionadas y con el porqué escrito en ambas"

key-files:
  created: []
  modified:
    - verification/test_main_iol_exception_redaction.py

key-decisions:
  - "AD-30-13-01 ejecutada tal como fue firmada: `getattr` queda sancionado a nivel de callee y la decisión se toma sobre su argumento de nombre de atributo. Sacarlo del allow-list habría marcado `getattr(exc, \"status_code\", None)` — la forma que usa el propio renderer sancionado (main_iol.py:331) y que `_COMPLIANT_SOURCE` contiene a propósito como control negativo. Medido: las dos filas negativas devuelven `[]` y el driver devuelve `[]`."
  - "Las dos constantes de callees sancionados NO se fusionan, y la asimetría es la parte deliberada. `_SANCTIONED_DELEGATES` incluye `getattr`; `_CENSUS_SANCTIONED_DELEGATES` no. Contestan preguntas distintas: la primera pregunta si un sitio de handler filtra (y `getattr` se adjudica sobre su atributo), la segunda si una FUNCIÓN está decidiendo cómo se ve una excepción — y ahí cualquier introspección del parámetro cuenta. Fusionarlas rompería el censo del propio renderer sancionado, cuyo cuerpo es exactamente un `getattr` más un `type(...)`."
  - "La regla de delegación del censo se invirtió a deny-by-default en vez de agregar `print` a una lista de formas reconocidas. La versión anterior enumeraba qué callees contaban (`getattr` + `_STRINGIFYING_CALLS`); la nueva enumera qué callees NO cuentan. Un enumerar-lo-permitido sobre un espacio infinito de nombres de función es el modo de falla que este ciclo encontró, no una instancia de él."
  - "La cuarta fila positiva (getattr con nombre de atributo no constante) no la reprodujo el verifier: la agrega este plan porque la lectura estricta de la regla 9 la exige. Un lock que permite justo la escritura que derrota su propio análisis es el gap que la regla 9 cierra, en miniatura."
  - "`status_code` sigue FUERA de `_LEAKY_EXC_ATTRS` en las dos escrituras, y el comentario de la constante lo dice extendido, no contradicho. WR-03 (22 lecturas inline en argumentos `diff=`) sigue abierto y no escalado; cerrarlo es lo que debe habilitar esa entrada."

patterns-established:
  - "La tabla de bypasses de cada ciclo de review vive en su propia constante nombrada por el ciclo, no por un número WR: la fase arrastra tres esquemas de numeración incompatibles y fusionar las tablas volvería imposible saber qué pasada encontró qué"
  - "Cada exención nueva llega con su gemelo sintético además del caso vivo: si el caso vivo cambia de forma y se vuelve vacuo, el sintético no"

requirements-completed: []

coverage:
  - id: D1
    description: "La escritura indirecta de una lectura con fuga —`getattr(<n>, \"message\"/\"args\", …)`— se marca, adjudicada sobre el nombre de atributo y no sobre el callee, mientras `getattr(<n>, \"status_code\", None)` sigue sin marcar"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "::test_the_detector_flags_every_shape_of_the_fifth_cycle[getattr con atributo con fuga y default] + [... sin default, stringificado] + ::test_the_detector_leaves_sanctioned_introspection_unflagged[getattr(<n>, \"status_code\", None) — WR-03 sigue abierto]"
        status: pass
    human_judgment: false
  - id: D2
    description: "`<n>.__dict__` es una lectura con fuga en las dos escrituras, porque el dict de instancia expone `message` y todo lo demás que el constructor asignó de una sola lectura"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "::test_the_detector_flags_every_shape_of_the_fifth_cycle[el dict de instancia]; `_LEAKY_EXC_ATTRS == ('message', 'args', 'response', 'request', '__dict__')`"
        status: pass
    human_judgment: false
  - id: D3
    description: "Un nombre de atributo que llega a `getattr` por una variable se marca conservadoramente en vez de permitirse"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "::test_the_detector_flags_every_shape_of_the_fifth_cycle[getattr con nombre de atributo no constante]"
        status: pass
    human_judgment: false
  - id: D4
    description: "El censo marca un segundo renderer que formatea su parámetro con `%` y uno que lo entrega a cualquier callee fuera del conjunto sancionado, posicionalmente o por keyword"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "::test_the_census_catches_a_percent_formatting_renderer + ::test_the_census_catches_a_printing_renderer + ::test_the_census_catches_a_renderer_that_delegates_by_keyword — los tres por igualdad de lista en orden de fuente"
        status: pass
    human_judgment: false
  - id: D5
    description: "El widening no sobre-marca: `_COMPLIANT_SOURCE` byte-inalterado y verde, el driver real sin offenders, el censo del driver devolviendo exactamente el nombre sancionado con el hook post-30-12 todavía clasificado como consumidor"
    requirement: TYP-01
    verification:
      - kind: integration
        ref: "`_raw_exception_renders(main_iol.py) == []`; `_declared_exception_renderers(main_iol.py) == ['_redacted_exc']`; ::test_the_census_treats_the_excepthook_as_a_consumer_not_a_renderer sin editar; ::test_the_census_treats_a_synthetic_delegating_consumer_as_a_consumer"
        status: pass
    human_judgment: false
  - id: D6
    description: "Los controles de 30-11 quedan imperturbados y ninguno de los dos detectores es vacuo"
    verification:
      - kind: integration
        ref: "`_raw_exception_renders(_OFFENDING_SOURCE)` → 11 offenders en (6,7,8,9,10,11,12,13,14,16,18); las 11 filas de `_WR01_ROWS` siguen marcadas; sondas de vacuidad forzada: 16 failed / 48 passed y 9 failed / 55 passed, revertidas sin rastro"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-08-23
status: complete
---

# Phase 30 Plan 13: Durabilidad del lock AST — la exención de `getattr` y los dos puntos ciegos del censo Summary

**El lock que 30-11 amplió sancionaba `getattr` mirando sólo el nombre del callee, con lo cual `getattr(exc, "message", "")` —el body de error upstream verbatim— quedaba tan permitido como el `getattr(exc, "status_code", None)` del renderer sancionado; ahora la decisión se toma sobre el argumento de nombre de atributo con la misma constante que gobierna la escritura directa, `__dict__` entró a esa constante, y el censo de renderers dejó de enumerar qué delegaciones cuentan para enumerar la única que no.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-08-23T21:19:00Z (aprox.)
- **Completed:** 2026-08-23T21:24:06Z
- **Tasks:** 2 (las dos TDD, RED → GREEN)
- **Files modified:** 1 (`verification/test_main_iol_exception_redaction.py`)

## Baseline de tests (post-30-12)

**54 passed.** Es el número que dejó 30-12, y coincide con la nota del planner (fact 1) de que los 47 de la tabla de spot-check de `30-VERIFICATION.md` estaban desactualizados: 30-12 midió 42 de baseline y sumó 12.

Progresión de este plan: **54 → 60 (Task 1, +6) → 64 (Task 2, +4)**, es decir **+10**, exactamente el mínimo que pide el gate 1.

## Task Commits

| # | Tarea | RED | GREEN |
|---|---|---|---|
| 1 | `getattr` adjudicado sobre su atributo + `__dict__` | `6792bb5` | `e656662` |
| 2 | El censo gana `%`-format y delegación genérica | `3fd42fb` | `393a4c2` |

RED estrictamente antes de GREEN en las dos tareas.

## Task 1 — tabla de bypasses del quinto ciclo (formato de la tabla WR-01 de 30-11)

Medido llamando a `_raw_exception_renders` sobre cada fuente sintético, antes y después del GREEN.

| # | Forma | Antes (post-30-11) | Después | Etiqueta emitida |
|---|---|---|---|---|
| 1 | `append_finding("p", actual=getattr(exc, "message", ""))` | **MISSED** (`[]`) | **FLAGGED** | `getattr(exc, "message") — atributo con fuga por la vía indirecta` |
| 2 | `append_finding("p", actual=str(getattr(exc, "args")))` | **MISSED** (`[]`) | **FLAGGED** | `getattr(exc, "args") — atributo con fuga por la vía indirecta` |
| 3 | `append_finding("p", actual=str(exc.__dict__))` | **MISSED** (`[]`) | **FLAGGED** | `lectura de exc.__dict__` |
| 4 | `append_finding("p", actual=getattr(exc, attr_name))` | **MISSED** (`[]`) | **FLAGGED** | `getattr(exc, <nombre de atributo dinámico>)` |

Estado RED medido: **4 failed / 56 passed**, las cuatro filas fallando por `assert []`.

**Un offender por fila, no dos.** La fila 2 es el caso a chequear que el plan nombra: el argumento de `str(...)` es un `ast.Call` y no un `ast.Name`, así que no tripa la regla de stringificación y la línea produce exactamente una entrada. La aserción por tupla de líneas de `_OFFENDING_SOURCE` queda por lo tanto intacta.

### Las dos filas negativas — el widening fijado en la dirección contraria

| Forma | Esperado | **Medido** |
|---|---|---|
| `getattr(exc, "status_code", None)` adentro de un handler | `[]` | **`[]`** |
| `type(exc).__name__` adentro de un handler | `[]` | **`[]`** |

Las dos pasaban ya en RED y siguen pasando: son pins, no falsificadores. Existen porque el modo de falla por sobre-marcado (T-30-11-05 / T-30-13-07) es tan real como el de sub-marcado, y la primera es literalmente la forma que usa `_redacted_exc` en `main_iol.py:331`.

## Task 2 — tabla de bypasses del censo (formato de la tabla WR-02 de 30-11)

Medido llamando a `_declared_exception_renderers` sobre cada fuente sintético.

| Fuente | Segundo renderer | Antes (post-30-11) | Después |
|---|---|---|---|
| `_CENSUS_PERCENT_DUPLICATE` | `return "ABORT: %s" % e` | **MISSED** — `['_redacted_exc']` | **`['_redacted_exc', '_fmt_abort']`** |
| `_CENSUS_PRINTING_DUPLICATE` | `print(e)` | **MISSED** — `['_redacted_exc']` | **`['_redacted_exc', '_shout_exc']`** |
| `_CENSUS_KEYWORD_DUPLICATE` | `append_finding("pkg", actual=e)` | **MISSED** — `['_redacted_exc']` | **`['_redacted_exc', '_emit_exc']`** |
| `_CENSUS_SYNTHETIC_CONSUMER` | (ninguno — es la exención) | `['_redacted_exc']` | **`['_redacted_exc']`** |

Estado RED medido: **3 failed / 61 passed**. Los tres fallos con `Right contains one more item`. El cuarto caso pasa en RED **y** en GREEN a propósito: es el pin de la exención, y su valor está en que la regla nueva no lo haya volteado.

Las tres aserciones son por **igualdad de lista en orden de fuente**, nunca por largo ni por pertenencia — la posición T-30-11-04, que un widening no puede debilitar.

## Las dos constantes de callees sancionados, y por qué difieren

```python
_SANCTIONED_DELEGATES        = ("_redacted_exc", "type", "isinstance", "getattr")
_CENSUS_SANCTIONED_DELEGATES = ("_redacted_exc", "type", "isinstance")
```

La única diferencia es `getattr`, y es deliberada. Las dos contestan preguntas distintas:

- **`_SANCTIONED_DELEGATES`** decide si un **sitio de handler** filtra. `getattr` sigue sancionado *como callee*, pero desde este plan la llamada se adjudica sobre su argumento de nombre de atributo (reglas 9 y 10) antes de llegar a ese corto-circuito. Sacarlo de la lista habría marcado la forma conforme.
- **`_CENSUS_SANCTIONED_DELEGATES`** decide si una **función** está tomando una decisión de render. Ahí cualquier `getattr` sobre el parámetro cuenta como lectura: una función que introspecciona su excepción está decidiendo cómo se ve, sin importar qué atributo mire. Fusionar las constantes rompería el censo del propio `_redacted_exc`, cuyo cuerpo es exactamente un `getattr` más un `type(...)`.

Ambas llevan el porqué escrito en su comentario, incluida la advertencia de no fusionarlas.

## Gates 11 y 12 — anti-vacuidad, demostrada y revertida

Copia de la versión buena en scratchpad antes de cada sonda; restaurada por copia después.

**Gate 11 — `_raw_exception_renders`.** `return []` insertado inmediatamente después de `ast.parse(source)`. Resultado: **16 failed / 48 passed**. Fallan el control positivo line-pinned de 30-11, las 11 filas de `_WR01_ROWS` y las 4 filas nuevas del quinto ciclo. Siguen verdes el control negativo, las dos filas permitidas nuevas y el lock del driver — que asertan **ausencia** y que un detector mudo satisface por construcción, que es exactamente por qué el control positivo tiene que existir.

**Gate 12 — `_declared_exception_renderers`.** Misma técnica. Resultado: **9 failed / 55 passed**. Falla la aserción de igualdad contra el driver (gate 8) por las dos vías: `test_the_census_detects_the_sanctioned_renderer_in_the_real_driver` y `test_the_driver_declares_exactly_one_exception_renderer`. Fallan también los tres casos de bypass de 30-11, los tres nuevos y el consumidor sintético. Sigue verde `test_the_census_ignores_ordinary_driver_shaped_functions` (asierta `[]`) y sigue verde el caso del excepthook (asierta ausencia de un nombre) — la razón exacta por la que la aserción del driver es una **igualdad** y no una lista vacía.

Restauración verificada: `grep -n "^    return \[\]$"` sobre el archivo → **NONE**, `git diff` contra HEAD → vacío, `pytest` → **64 passed**.

## Verification — todos los gates medidos

| # | Gate | Esperado | **Medido** |
|---|------|----------|-----------|
| 1 | `pytest verification/test_main_iol_exception_redaction.py -q` | 0 failed, 0 skipped, ≥ 64 | **64 passed**, 0 failed, 0 skipped (54 + 10) |
| 2 | Tabla de bypasses del quinto ciclo | fila por fila MISSED → FLAGGED | **registrada arriba**, las 4 con su etiqueta |
| 3 | Filas negativas | `[]` las dos | **`[]` / `[]`** |
| 4 | Control positivo de 30-11 imperturbado | mismo conteo y misma tupla | **11 offenders**, líneas `(6,7,8,9,10,11,12,13,14,16,18)` — idénticas |
| 5 | Control negativo de 30-11 imperturbado | `[]` y byte-inalterado | **`[]`**; `git diff` no toca ni una línea de `_COMPLIANT_SOURCE` |
| 6 | Lock del driver | `[]` | **`[]`** — incluido el `getattr` sancionado de `main_iol.py:331` y todo lo que agregó 30-12 |
| 7 | Tabla de bypasses del censo | dos nombres cada uno | **registrada arriba**, con las listas devueltas (3 fuentes, no 2) |
| 8 | Carve-out del censo | `['_redacted_exc']` sobre el driver; el consumidor sintético igual | **`['_redacted_exc']`** en los dos |
| 9 | Cobertura de `_WR01_ROWS` intacta | las 11 filas siguen marcadas, test sin editar | **11/11**; el test no se tocó |
| 10 | Seis tests de censo pre-existentes | pasan sin editar | **pasan**; `git diff 04047a1..HEAD` no remueve **ninguna** línea de cuerpo de test — las 21 líneas removidas son 2 constantes, 15 de docstring y 2 del predicado viejo |
| 11 | Anti-vacuidad del detector | el `[]` forzado falla el control positivo | **16 failed / 48 passed**; revertido sin rastro |
| 12 | Anti-vacuidad del censo | el `[]` forzado falla el gate 8 | **9 failed / 55 passed**; revertido sin rastro |
| 13 | Cinco suites hermanas | all passed, sin cambio vs 30-12 | **37 passed** |
| 14 | `pytest packages/iol-client -q` | `242 passed` | **242 passed** |
| 15 | `ruff check packages/iol-client main_iol.py verification` + `ruff format --check verification` | limpio | **`All checks passed!` / `48 files already formatted`** |
| 16 | **Reversibilidad** — `git diff --exit-code main_iol.py packages/ .planning/verification/` | exit 0 | **exit 0** — superficie de test solamente |
| 17 | `git status --porcelain` | sólo el archivo del plan, más el SUMMARY | **OK** — el archivo quedó committeado; lo pendiente (`.gsd/`, cache de research) es pre-existente al arranque del plan |

## Nota de metodología — ¿la cobertura converge o la enumeración es ad hoc?

El verifier pidió esto explícitamente, porque es el **segundo widening consecutivo** del mismo lock que encuentra puntos ciegos nuevos.

**Qué se enumeró esta vez, y por qué método.** Las cuatro formas no salieron de una misma fuente:

1. **Tres las reprodujo el verifier**, llamando al detector post-30-11 directamente sobre fuentes sintéticos y observando `[]`. Método: prueba empírica sobre el artefacto, no lectura del código. Es el método más fuerte de los tres y es el que produjo el hallazgo.
2. **Una salió de la lectura estricta de la regla nueva** (`getattr` con nombre de atributo no constante). Método: preguntarle a la regla recién escrita cuál es la escritura que la derrota. Esto es más barato que (1) y sistemático, pero sólo alcanza al vecindario inmediato de lo que se acaba de tocar.
3. **Una salió de comparar los dos detectores entre sí** (el keyword vs. posicional del censo, y la regla de `%` que ya vivía en el detector hermano). Método: diff de política entre dos implementaciones de la misma idea.

**Señal de convergencia.** Los hallazgos de los tres ciclos tienen **una sola causa estructural**: dos detectores implementando políticas solapadas con conjuntos de reglas independientes, y exenciones keyeadas sobre el *nombre del callee* en vez de sobre la *operación*. Este plan ataca la causa y no las instancias: la exención de `getattr` pasó a decidirse sobre su argumento con la misma constante que gobierna la escritura directa (las dos escrituras ya no pueden derivar), y la delegación del censo se **invirtió** de enumerar-lo-que-cuenta a enumerar-lo-que-no-cuenta. Un allow-list sobre el espacio infinito de nombres de función era, en sí mismo, el generador de los bypasses de este ciclo; la forma deny-by-default no tiene ese generador.

**Señal en contra.** No se hizo ninguna enumeración exhaustiva sobre la gramática de nodos del AST. Nadie recorrió los tipos de `ast` que pueden consumir un `ast.Name` para preguntarse cuáles faltan; las cuatro formas siguen viniendo de intuición estructurada, aunque bien fundada. Un método que **sí** convergería, y que un ciclo futuro debería considerar antes de un tercer widening ad hoc: generar mecánicamente un fuente sintético por cada nodo del AST capaz de recibir el nombre bindeado (`Subscript`, `Starred`, `comprehension`, `JoinedStr` anidado, `assert`, `raise ... from <n>`, `yield <n>`, `return <n>`) y correr los dos detectores sobre la matriz completa. Eso convierte "no se nos ocurrió" en una lista finita y auditable.

**Lectura honesta:** la corrección de este ciclo es estructural y por lo tanto es razonable esperar menos hallazgos del mismo tipo; la *enumeración* sigue siendo ad hoc y por lo tanto no hay base para afirmar que la cobertura sea completa.

## Frontera residual — explícita

- **El aliasing de más de un nivel** (`a = exc; b = a; str(b)`) sigue **sin verificar**, igual que después de 30-11. El docstring del detector lo dice explícitamente; esa frontera declarada es la mitigación.
- **El flujo de datos que sale del handler** (guardar el nombre bindeado en un atributo, una lista o un global y leerlo en otro lado) sigue sin verificar.
- **`status_code` sigue fuera de `_LEAKY_EXC_ATTRS`**, en las dos escrituras, mientras **WR-03** (22 lecturas inline en argumentos `diff=`) siga abierto y no escalado. Agregarlo hoy haría fallar el lock sobre 22 sitios pre-existentes. Cerrar WR-03 es lo que debe habilitar esa entrada, nunca al revés.
- **El valor de un nombre de atributo que llega a `getattr` por una variable no se resuelve**: se marca. Es una decisión estricta, no un análisis, y así está escrito en el docstring.
- **Ninguno de los tres detectores apunta a los otros cinco `main_*.py`.** Los tres toman un string de fuente precisamente para que el audit de la **Phase 33** necesite una parametrización y no una reescritura.
- **WR-04, WR-05, WR-06** y los carry-forwards INFO IN-01..IN-03 siguen intactos, listados como no escalados en la tabla de Anti-Patterns de `30-VERIFICATION.md`.

## Deviations from Plan

Ninguna. El plan se ejecutó tal como fue escrito.

Los siete `planner_verified_facts` se confirmaron contra el árbol, con un solo drift cosmético: el `getattr` sancionado del driver está en **`main_iol.py:331`**, no en la 324 que registra la fact 2 — las siete líneas de diferencia las agregó 30-12 más arriba en el archivo. La sustancia de la fact (un solo `getattr` sobre una excepción, el sancionado, fuera de todo `ast.ExceptHandler`) es correcta. La fact 3 (cero `__dict__` en el driver) se confirmó verbatim.

Ningún widening marcó un sitio real del driver, así que no hubo nada que escalar bajo la cláusula de cierre del `<scope_boundary>`.

## `TYP-01` — deliberadamente NO marcado como completo

`.planning/REQUIREMENTS.md` no se tocó. Flipear ese checkbox es la decisión del verifier, no de un plan: `30-09-SUMMARY.md` registra en su deviation 3 que un `mark-complete` prematuro sobre este mismo requisito ya tuvo que revertirse una vez, y `30-10`, `30-11` y `30-12` declinaron por la misma razón.

## Self-Check: PASSED

Archivo declarado como modificado, verificado en disco y en git:

- `verification/test_main_iol_exception_redaction.py` — FOUND, modificado en `6792bb5`, `e656662`, `3fd42fb`, `393a4c2`

Commits declarados, verificados con `git log`:

- `6792bb5` FOUND · `e656662` FOUND · `3fd42fb` FOUND · `393a4c2` FOUND

Símbolos declarados como provistos, verificados por carga del módulo:

- `_CENSUS_SANCTIONED_DELEGATES` FOUND (`('_redacted_exc', 'type', 'isinstance')`)
- `_LEAKY_EXC_ATTRS` FOUND (`('message', 'args', 'response', 'request', '__dict__')`)
- `_FIFTH_CYCLE_BYPASS_ROWS` (4 filas) FOUND · `_FIFTH_CYCLE_ALLOWED_ROWS` (2 filas) FOUND
- `_CENSUS_PERCENT_DUPLICATE` · `_CENSUS_PRINTING_DUPLICATE` · `_CENSUS_KEYWORD_DUPLICATE` · `_CENSUS_SYNTHETIC_CONSUMER` FOUND
