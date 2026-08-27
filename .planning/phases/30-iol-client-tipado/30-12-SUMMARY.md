---
phase: 30-iol-client-tipado
plan: 12
subsystem: verification-driver
tags: [redaction, crash-path, fail-closed, excepthook, ast-lock, tdd, gap-closure]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado (plan 09)
    provides: "_redacted_exc — el único renderer sancionado (AD-30-09-01), más _raw_exception_renders y _called_name"
  - phase: 30-iol-client-tipado (plan 10)
    provides: "_redacted_excepthook + _install_redacted_excepthook + la sección 4 de test_main_iol_exception_redaction.py (el camino de crash y sus cinco tests de comportamiento)"
  - phase: 30-iol-client-tipado (plan 11)
    provides: "_declared_exception_renderers — el censo que clasifica al hook como consumidor y que este plan no puede romper"
provides:
  - "_HOOK_RENDER_FAILED — constante module-level con texto ESTÁTICO de fallback; ninguna expresión suya referencia exc, exc_type ni tb"
  - "_emit_crash_report(detail: str, tb: TracebackType | None) -> None — dos contextlib.suppress(BaseException) INDEPENDIENTES, uno por sink"
  - "_redacted_excepthook con la llamada al renderer adentro de un try/except BaseException que bindea el placeholder"
  - "sección 5 de test_main_iol_exception_redaction.py — 7 tests de comportamiento (3 de falla del renderer, 4 de falla del sink) + 5 del lock estructural"
  - "_unguarded_crash_path_calls(source) -> list[tuple[int, str]] — tercer detector AST de la fase, sobre string de fuente"
  - "_DecodeErrorMissingItsAttributes — fixture hostil que dispara el trigger (c) SIN monkeypatch"
  - "_StderrThatFailsOnWrite — stream con falla selectiva que hace observable la independencia de los dos guards"
affects: [30-VERIFICATION sexto ciclo, 30-13 (durabilidad del lock AST), 33-LIVE-TYP-01]

actuals:
  tokens: 31000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Fail-closed en una frontera de seguridad: cuando la maquinaria de redacción falla, degrada el TEXTO, nunca la frontera"
    - "except BaseException y no Exception en el último frame antes de un fallback del runtime — el contrato es que NADA se escapa, no que casi nada se escapa"
    - "Placeholder ESTÁTICO en el camino de fallback: cualquier valor derivado del objeto peligroso ahí es una fuga a través de la rama que existe para prevenirla"
    - "Un guard por sink, nunca uno compartido — falsificado con un stream de falla selectiva, no razonado"
    - "El helper de emisión recibe TEXTO YA RENDERIZADO y no la excepción, para no reclasificarse como segundo renderer bajo el censo de AD-30-09-01"
    - "Guard estructural que acepta ast.Try sólo por su body: una llamada en la rama except no está protegida por ese mismo try"

key-files:
  created: []
  modified:
    - main_iol.py
    - verification/test_main_iol_exception_redaction.py

key-decisions:
  - "AD-30-12-01 ejecutada tal como fue firmada: se envolvió el CUERPO DEL HOOK y _redacted_exc quedó byte-inalterado. La evidencia empírica la respalda — de los tres triggers nombrados, endurecer el renderer sólo habría cerrado el (c); el (b) falla en la escritura, no adentro del renderer, y el subproceso de stderr cerrado lo demostró en RED cayendo por ValueError('I/O operation on closed file.') en el print, no en el render."
  - "El fallback de CPython con stderr cerrado es PEOR que el fallback normal, y eso no estaba en el plan ni en la VERIFICATION. Medido en RED: cuando también falla la escritura del fallback, CPython cae a su ruta ``lost sys.stderr``, que vuelca el **repr del objeto excepción** directo al fd 2 — ``IOLAPIError('[500] <marker>-cuenta-999999')``, por un sink que ni siquiera es sys.stderr y que ninguna redacción de Python puede interceptar. Eso convierte al test de stderr cerrado en un falsificador genuino en vez del test potencialmente vacuo que se temía al escribirlo."
  - "La RED de la Task 3 shipea el detector como stub que levanta NotImplementedError en vez de dejar el símbolo indefinido. Un NameError habría dejado el commit RED con 4 errores F821 de ruff, y el gate 15 exige ruff limpio. La disciplina que la Task 3 pide —controles escritos y fijados ANTES del cuerpo del detector— se conserva intacta: el stub no tiene semántica que moldear."
  - "El texto de _HOOK_RENDER_FAILED no nombra la clase de la excepción ni su status. Se consideró incluir el nombre de clase (que _redacted_exc sí reporta como hecho sancionado) y se descartó: en la rama de fallback la maquinaria que decide qué es seguro mostrar YA FALLÓ, así que ninguna lectura sobre exc puede asumirse segura ahí — el trigger (c) es literalmente una excepción cuyos atributos hacen levantar al leerlos."
  - "El lock estructural acepta un ast.Try sólo cuando la llamada vive en su BODY. Aceptar cualquier ancestro Try dejaría pasar el edit realista de mover la llamada al renderer a la rama de fallback, que reabre la fuga entera; hay un contra-caso dedicado que lo falsifica."

patterns-established:
  - "Reproducción del verifier convertida en test de regresión verbatim: la evidencia que abrió el BLOCKER es ahora el test que impide reabrirlo"
  - "Trigger sin monkeypatch como respuesta a la objeción de contrivance: si la falla la produce la forma del propio objeto, el caso borde no es del test"
  - "Aserción por AUSENCIA del banner de fallo del runtime como evidencia positiva y falsable de que el renderer default nunca se alcanzó"

requirements-completed: []

coverage:
  - id: D1
    description: "Una falla de _redacted_exc adentro del hook degrada el texto a un placeholder estático en vez de rutear la excepción original al renderer default de CPython — forzada por monkeypatch (directa y por subproceso) y producida naturalmente por un IOLDecodeError que nunca corrió el __init__ de su padre"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "verification/test_main_iol_exception_redaction.py::test_the_hook_falls_closed_when_the_renderer_raises + ::test_the_hook_falls_closed_on_a_decode_error_missing_its_attributes (sin monkeypatch)"
        status: pass
      - kind: integration
        ref: "::test_the_installed_hook_falls_closed_when_the_renderer_raises — subproceso con CPython real; marker ausente de stdout y stderr, returncode != 0, banner 'Error in sys.excepthook:' ausente"
        status: pass
    human_judgment: false
  - id: D2
    description: "Un stderr roto, cerrado o de falla selectiva no puede escaparse del hook en ninguna de las dos direcciones, y los dos guards son provablemente independientes"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "::test_the_hook_survives_a_broken_stderr + ::test_the_hook_still_prints_frames_when_the_abort_line_fails + ::test_the_hook_survives_a_failing_frame_printer"
        status: pass
      - kind: integration
        ref: "::test_the_installed_hook_survives_a_closed_stderr — subproceso; pre-fix CPython volcaba el repr de la excepción por la ruta 'lost sys.stderr'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Los guards quedan fijados estructuralmente: sacar un guard, mover el renderer a una rama de fallback o renombrar una función del camino de crash falla un test"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "::test_the_crash_path_lock_flags_the_pre_fix_hook (3 offenders en (4,4,5)) + ::test_the_crash_path_lock_accepts_the_guarded_shape ([]) + ::test_the_crash_path_lock_does_not_accept_an_except_branch_as_a_guard + ::test_the_crash_path_region_is_not_empty_in_the_real_driver + ::test_no_crash_path_call_in_the_driver_runs_unguarded"
        status: pass
    human_judgment: false
  - id: D4
    description: "Los dos locks AST shippeados siguen verdes, el happy path de 30-10 queda byte-inalterado, y packages/ + .planning/verification/ no se tocan"
    verification:
      - kind: integration
        ref: "_raw_exception_renders == []; _declared_exception_renderers == ['_redacted_exc']; los cinco tests de la sección 4 pasan sin edits; git diff --exit-code packages/ .planning/verification/ exit 0; 242 passed en iol-client; mypy Success 25 files"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-08-23
status: complete
---

# Phase 30 Plan 12: El camino de crash falla cerrado Summary

**`_redacted_excepthook` —la función escrita para impedir que el body de error upstream llegue a stderr— emitía ese body verbatim en cuanto algo adentro suyo fallaba, porque el contrato de CPython ante un excepthook que levanta es caer al renderer default; ahora la llamada al renderer va adentro de un `try` que bindea un placeholder estático, cada sink va adentro de su propio `contextlib.suppress(BaseException)`, y un tercer detector AST impide que un edit futuro saque cualquiera de los tres guards en silencio.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-08-23T21:07:45Z
- **Completed:** 2026-08-23T21:13:41Z
- **Tasks:** 3 (las tres TDD, RED → GREEN)
- **Files modified:** 2 (`main_iol.py`, `verification/test_main_iol_exception_redaction.py`)

## Accomplishments

- **El BLOCKER del quinto ciclo cerrado en su forma general.** No se endureció el renderer (que habría cerrado 1 de los 3 triggers): se envolvió el cuerpo del hook, que es el último frame antes del fallback de CPython y por lo tanto el punto donde un guard es *provablemente suficiente* sin importar qué sub-paso falló.
- **La reproducción del verifier es ahora un test de regresión.** El subproceso que monkeypatchea `_redacted_exc` para que levante y después levanta `IOLAPIError(500, <marker>-cuenta-999999)` corría pre-fix con el marker completo en stderr; ahora corre limpio y además asierta la **ausencia** del banner `Error in sys.excepthook:`, que es la evidencia directa y falsable de que el renderer default nunca se alcanzó.
- **El trigger sin monkeypatch existe y está cubierto.** `_DecodeErrorMissingItsAttributes` hereda de `IOLDecodeError` y nunca corre el `__init__` de su padre; `_redacted_exc` lee `exc.model` sin condición y levanta `AttributeError` en `main_iol.py:321`. Eso responde la objeción de que el gap sería un caso borde sólo alcanzable desde un test: la falla la produce la forma del propio objeto excepción.
- **Los dos guards de sink son independientes, y se demostró falsificándolo** (gate 5, detalle abajo) — no razonándolo.
- **Se descubrió que el fallback con stderr cerrado es peor de lo documentado.** Ver "Hallazgos" abajo: CPython vuelca el `repr` del objeto excepción al fd 2 por una ruta que ninguna redacción de Python puede interceptar.
- **`packages/iol-client/` byte-inalterado**, como exige el `<scope_boundary>`. SC1-SC5 y las truths 1-7 no se tocan.

## Task Commits

| # | Tarea | RED | GREEN |
|---|---|---|---|
| 1 | El hook cae cerrado cuando el renderer levanta | `ee03b9b` | `21f5107` |
| 2 | El hook cae cerrado cuando el sink falla | `5f8f974` | `4d3e89e` |
| 3 | Lock estructural de los guards | `48dbce4` | `69fd730` |

RED estrictamente antes de GREEN en las tres tareas.

## Estados RED medidos

Los siete tests de comportamiento, con el modo de falla observado contra el hook pre-fix.

### Task 1 — falla del renderer (3 casos, todos failed en RED)

| Test | Excepción que se propagó fuera del hook |
|---|---|
| `test_the_hook_falls_closed_when_the_renderer_raises` | `RuntimeError: el renderer sancionado falló a mitad de camino` — se escapó del hook sin tocarse |
| `test_the_hook_falls_closed_on_a_decode_error_missing_its_attributes` | `AttributeError: '_DecodeErrorMissingItsAttributes' object has no attribute 'model'`, levantada en `main_iol.py:321` — **sin monkeypatch de por medio** |
| `test_the_installed_hook_falls_closed_when_the_renderer_raises` | No propagó: CPython la atrapó y cayó al renderer **default**. Evidencia verbatim abajo. |

**Evidencia verbatim de la fuga (subproceso, pre-fix), marker abreviado como `<MARKER>`:**

```
Error in sys.excepthook:
Traceback (most recent call last):
  File "/Users/.../main_iol.py", line 2081, in _redacted_excepthook
    print(f"ABORT: {_redacted_exc(exc)}", file=sys.stderr)
                    ^^^^^^^^^^^^^^^^^^
  File "<string>", line 8, in _boom
RuntimeError: el renderer sancionado falló

Original exception was:
Traceback (most recent call last):
  File "<string>", line 12, in <module>
iol_client.exceptions.IOLAPIError: [500] <MARKER>-cuenta-999999
```

Esa última línea es exactamente el modo de falla que el BLOCKER describe: `[<status>] <body>` completo, a stderr, por la única función escrita para impedirlo. Post-fix stderr no contiene ni el marker ni el banner.

### Task 2 — falla del sink (4 casos, todos failed en RED)

| Test | Modo de falla observado |
|---|---|
| `test_the_hook_survives_a_broken_stderr` | `BrokenPipeError: stderr roto` propagada fuera del hook |
| `test_the_hook_still_prints_frames_when_the_abort_line_fails` | `BrokenPipeError: stderr roto` propagada fuera del hook — los frames nunca llegaron a intentarse |
| `test_the_hook_survives_a_failing_frame_printer` | `RuntimeError: la extracción de frames falló` propagada fuera del hook |
| `test_the_installed_hook_survives_a_closed_stderr` | No propagó; CPython cayó a `lost sys.stderr`. Evidencia abajo. |

**Evidencia verbatim (subproceso con `sys.stderr.close()`, pre-fix):**

```
Error in sys.excepthook:
object address  : 0x10b6ca6e0
object type name: ValueError
object repr     : ValueError('I/O operation on closed file.')
lost sys.stderr

Original exception was:
object address  : 0x10b65fb60
object type name: IOLAPIError
object repr     : IOLAPIError('[500] <MARKER>-cuenta-999999')
lost sys.stderr
```

### Task 3 — lock estructural (4 failed, 1 passed en RED)

Los cuatro tests que consumen el detector fallaron con `NotImplementedError` (el stub). `test_the_crash_path_region_is_not_empty_in_the_real_driver` pasó en RED **por construcción** —asierta una propiedad del driver, no del detector—; su poder anti-vacuidad es prospectivo (un rename futuro).

## Baseline de tests y planner-verified fact 1

**Sin discrepancia.** La primera corrida midió **42 passed**, exactamente lo que la fact 1 predice, y no los 47 que registra la tabla de spot-check de `30-VERIFICATION.md`. Se usó 42 como baseline. Progresión: 42 → 45 (Task 1) → 49 (Task 2) → **54** (Task 3), es decir **+12** contra el mínimo de +10 que pide el gate 1.

## Gate 5 — cómo se confirmó la independencia de los guards

Copia de `main_iol.py` guardada en scratchpad. Los dos `with` de `_emit_crash_report` se colapsaron temporalmente en uno solo:

```python
with contextlib.suppress(BaseException):
    print(f"ABORT: {detail}", file=sys.stderr)
    traceback.print_tb(tb)
```

Resultado: **1 failed / 48 passed**. Falla exactamente el test que existe para esto, y por la razón exacta:

```
AssertionError: la falla de la línea de ABORT se llevó puestos los frames —
los dos guards no son independientes. Registrado: ''
assert 'File "' in ''
```

Los otros 48 —incluidos los tres casos de falla del renderer, los otros tres de sink y los cuatro subprocesos— siguen verdes bajo la forma colapsada, lo que confirma que **ningún otro test cubre esta propiedad**: sin este caso, la implementación de un solo guard habría pasado la suite entera. Revertido copiando desde el scratchpad; `pytest` → 54 passed, `ruff` limpio, `grep` de la forma colapsada → 0.

## Gate 11 — anti-vacuidad del lock estructural

Misma técnica: copia en scratchpad, y `return []` insertado inmediatamente después de `ast.parse(source)` en `_unguarded_crash_path_calls`.

Resultado: **2 failed / 3 passed** dentro del grupo del lock.

- **Falla** `test_the_crash_path_lock_flags_the_pre_fix_hook` — el control positivo, que es precisamente el guard anti-vacuidad.
- **Falla** `test_the_crash_path_lock_does_not_accept_an_except_branch_as_a_guard` — el contra-caso, con `Right contains one more item: '_redacted_exc() sin guard en _redacted_excepthook'`.
- Siguen verdes el control negativo y el lock del driver, que asertan **ausencia** y que un detector mudo satisface por construcción — que es exactamente por qué el control positivo tiene que existir.

Revertido desde el scratchpad. Verificado: `grep -n "    return \[\]$"` sobre el archivo → **NONE**; el archivo committeado no lleva rastro de la sonda; `pytest` → 54 passed.

## El valor de `_HOOK_RENDER_FAILED`

```python
_HOOK_RENDER_FAILED = "el render de la excepción falló; detalle suprimido a propósito"
```

Es un literal fijo. **Ninguna** expresión suya referencia `exc`, `exc_type`, `tb` ni atributo alguno de ellos — confirmado por lectura directa de la constante. Se consideró incluir el nombre de clase (un hecho que `_redacted_exc` sí reporta como sancionado) y se descartó: en la rama de fallback la maquinaria que decide qué es seguro mostrar ya falló, y el trigger (c) es literalmente una excepción cuyos atributos levantan al leerlos.

## Hallazgos

### H1 — `contextlib` ya estaba importado (drift contra planner-verified fact 6)

La fact 6 afirma que `contextlib` es un import nuevo. **No lo es:** `main_iol.py:74` ya lo importaba, y `main_iol.py:1895` ya lo usaba (`with contextlib.suppress(Exception):`, para honrar D-04). El paso 1 del GREEN de la Task 1 resultó un no-op. Sin impacto: no hubo cambio de dependencia, ni edit de `pyproject.toml`, ni refresh de lockfile — que es lo que la fact protegía. Las facts 1 a 5 y 7 se verificaron correctas.

### H2 — con stderr cerrado, CPython filtra por un sink que Python no controla

No estaba en el plan ni en `30-VERIFICATION.md`. Cuando la escritura del **fallback** también falla, CPython no se rinde en silencio: cae a su ruta `lost sys.stderr` y escribe el **repr del objeto excepción** directo al fd 2 — `IOLAPIError('[500] <MARKER>-cuenta-999999')`. Ese sink no es `sys.stderr` y ninguna redacción a nivel Python puede interceptarlo.

Dos consecuencias. Primera, el test de stderr cerrado resultó un falsificador **genuino**, no el test potencialmente vacuo que se temía al escribirlo (con stderr cerrado, uno esperaría que nada sea observable). Segunda, refuerza la elección de AD-30-12-01: contra esta ruta la única defensa posible es que **nada se escape del hook**, porque una vez que CPython toma el control ya no hay nada que redactar.

### H3 — RED de la Task 3 con stub en vez de símbolo indefinido (deviación, Rule 3)

La Task 3 pide escribir los controles antes de que el detector exista. Hacerlo literalmente dejaba el commit RED con **4 errores `F821`** de ruff, y el gate 15 exige `ruff check` limpio. Se shipeó el detector como stub que levanta `NotImplementedError`. La disciplina que la tarea busca —que el detector no pueda moldearse para calzar con lo que le salga producir— queda intacta: el stub no tiene semántica que moldear, y los cinco controles estaban escritos y fijados antes de escribir el cuerpo. Es el mismo patrón que 30-11 usó por la misma razón (su key-decision sobre el placeholder de la Task 2), y está documentado en el docstring del propio stub-commit.

## Verification — todos los gates medidos

| # | Gate | Esperado | **Medido** |
|---|------|----------|-----------|
| 1 | `pytest verification/test_main_iol_exception_redaction.py -q` | 0 failed, 0 skipped, ≥ 52 | **54 passed**, 0 failed, 0 skipped (42 + 12) |
| 2 | Evidencia RED de falla del renderer | registrada verbatim | **registrada arriba**, marker abreviado |
| 3 | Banner de fallo del excepthook | ausente en todo subproceso | **ausente** en los tres (`test_the_installed_hook_survives_the_real_crash_machinery`, `..._falls_closed_when_the_renderer_raises`, `..._survives_a_closed_stderr`) |
| 4 | Trigger sin monkeypatch | pasa y no usa `monkeypatch` | **pasa**; su firma es `(capsys)` — no recibe `monkeypatch` |
| 5 | Independencia de los guards | confirmada colapsando y revirtiendo | **confirmada** — 1 failed / 48 passed bajo la forma colapsada |
| 6 | Exit code preservado (D-04) | `!= 0` en los tres subprocesos | **`!= 0`** en los tres |
| 7 | Happy path intacto | los cinco tests de la sección 4 pasan sin edits | **pasan**; `git diff dd9b4f8..HEAD` sobre el archivo no remueve ni altera **ninguna** línea de test — las únicas 5 líneas removidas son las dos del docstring de módulo que se reemplazaron (conteo de secciones y provenencia) |
| 8 | Lock shippeado 1 | `_raw_exception_renders == []` | **`[]`** |
| 9 | Lock shippeado 2 | `_declared_exception_renderers == ["_redacted_exc"]` | **`['_redacted_exc']`** — `_emit_crash_report` ausente, `_redacted_excepthook` sigue siendo consumidor |
| 10 | Lock estructural nuevo | `[]` sobre el driver; 3 offenders en líneas pinneadas | **`[]`** sobre el driver; control positivo → `[(4, '_redacted_exc() sin guard...'), (4, 'print() sin guard...'), (5, 'print_tb() sin guard...')]`; no-vacuidad de región pasa |
| 11 | Anti-vacuidad del lock nuevo | el `[]` forzado falla el control positivo; revertido sin rastro | **demostrado** — 2 failed; `grep` post-restore → NONE |
| 12 | Cinco suites hermanas | all passed, sin cambio vs 30-11 | **37 passed** |
| 13 | `pytest packages/iol-client -q` | `242 passed` | **242 passed** |
| 14 | `mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` | **`Success: no issues found in 25 source files`** |
| 15 | `ruff check packages/iol-client main_iol.py verification` + `ruff format --check` | limpio | **`All checks passed!` / `49 files already formatted`** |
| 16 | Cero `try`/`except`/`pass` introducidos | los dos sinks son `contextlib.suppress` | **cero** — `grep -c "^\s*pass$" main_iol.py` → 0; los dos guards son `with contextlib.suppress(BaseException):` |
| 17 | **Reversibilidad** — `git diff --exit-code packages/ .planning/verification/` | exit 0 | **exit 0** |
| 18 | `git status --porcelain` | sólo los dos archivos del plan, más el SUMMARY | **OK** — los dos archivos quedaron committeados; lo pendiente (`.planning/STATE.md`, `.gsd/`, cache de research) es todo pre-existente al arranque del plan |

## Deviations from Plan

### 1. `[Rule 3 - Blocking]` La RED de la Task 3 shipea un stub en vez de un símbolo indefinido

- **Found during:** Task 3, RED
- **Issue:** `uv run ruff check verification` devolvió 4 × `F821 Undefined name '_unguarded_crash_path_calls'`. El gate 15 exige `ruff check` limpio y el hook de pre-commit corre ruff, así que el commit RED literal no era committeable.
- **Fix:** el detector se agregó como stub con `raise NotImplementedError` y un docstring que explica por qué. Los cuatro tests que lo consumen siguen fallando en RED, ahora por `NotImplementedError`.
- **Files modified:** `verification/test_main_iol_exception_redaction.py`
- **Commit:** `48dbce4`

### 2. Paso no-op: `contextlib` ya estaba importado

- **Found during:** Task 1, GREEN, paso 1
- **Issue:** drift contra planner-verified fact 6 — ver H1.
- **Fix:** ninguno necesario; el paso se omitió.
- **Files modified:** ninguno

Fuera de estas dos, el plan se ejecutó tal como fue escrito. Ningún guard agregado hizo fallar un test pre-existente, así que no hubo nada que reconciliar bajo la cláusula de cierre del `<scope_boundary>`.

## Frontera residual — explícita

- **WR-03 sigue abierto y no escalado.** `sys.unraisablehook`, `threading.excepthook` y el handler default de excepciones del loop de asyncio son **tres sinks hermanos que siguen sin guard**. Este plan no instaló ningún hook adicional, por instrucción explícita del `<scope_boundary>`. Siguen no alcanzables con un payload que cargue datos de IOL —`iol_client` no spawnea threads y el driver no crea tasks async sueltas— pero eso es una propiedad del código de hoy, no una garantía.
- **El lock estructural verifica que un guard EXISTE, no que atrapa lo correcto.** Un `except ValueError:` alrededor de la llamada al renderer pasaría `_unguarded_crash_path_calls` y fallaría los tests de comportamiento de las Tasks 1 y 2. Que existan los dos mecanismos es exactamente la razón: el chequeo estático fija la **forma**, los tests fijan el **comportamiento**, y ninguno subsume al otro. El docstring del detector lo dice explícitamente.
- **También sin verificar por el lock:** un guard instalado por un caller (la búsqueda se corta en la propia función contenedora, a propósito, porque a `_redacted_excepthook` lo invoca CPython) y el aliasing del callee (`p = print; p(...)`), invisible igual que en los otros dos detectores del archivo.
- **WR-04, WR-05 y WR-06** siguen intactos como carry-forwards trackeados por separado. La durabilidad del lock AST (la exención de nombre de atributo de `getattr`, `exc.__dict__`, las reglas de formato `%` y de delegación genérica del censo) es **30-13**, que depende de este plan.

## `TYP-01` — deliberadamente NO marcado como completo

`.planning/REQUIREMENTS.md` no se tocó. La fase debe un sexto ciclo de verificación, y flipear ese checkbox es la decisión del verifier, no de un plan. `30-VERIFICATION.md` registra que `30-10-SUMMARY.md` y `30-11-SUMMARY.md` declinaron correctamente por la misma razón, y la deviation 3 de `30-09-SUMMARY.md` registra que un `mark-complete` prematuro sobre este mismo requisito ya tuvo que revertirse una vez.

## Nota para el orquestador

**30-13 depende de este plan y debe correr después.** Ambos modifican `verification/test_main_iol_exception_redaction.py`, y el control negativo del censo de 30-13 asierta contra la forma del camino de crash que este plan establece —`_emit_crash_report` con firma `(str, TracebackType | None)` y `_redacted_excepthook` como consumidor.

## Self-Check: PASSED

Archivos declarados como modificados, verificados en disco y en el árbol de git:

- `main_iol.py` — FOUND, modificado en `21f5107` y `4d3e89e`
- `verification/test_main_iol_exception_redaction.py` — FOUND, modificado en `ee03b9b`, `5f8f974`, `48dbce4`, `69fd730`

Commits declarados, verificados con `git log`:

- `ee03b9b` FOUND · `21f5107` FOUND · `5f8f974` FOUND · `4d3e89e` FOUND · `48dbce4` FOUND · `69fd730` FOUND

Símbolos declarados como provistos, verificados por import y por AST:

- `main_iol._HOOK_RENDER_FAILED` FOUND · `main_iol._emit_crash_report` FOUND
- `_unguarded_crash_path_calls` FOUND · `_DecodeErrorMissingItsAttributes` FOUND · `_StderrThatFailsOnWrite` FOUND
