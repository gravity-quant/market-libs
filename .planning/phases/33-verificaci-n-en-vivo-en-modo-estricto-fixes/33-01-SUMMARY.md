---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
plan: 01
subsystem: testing
tags: [logging, contextvars, decode-divergence, findings, harness, tdd, higyrus]

requires:
  - phase: 29-decoder-observable
    provides: "el walker observable y el record congelado de seis claves (`_decode._emit`), el contrato de agregación (locks 1-11) y el piso de sizing ratificado (>=96)"
  - phase: 31-endpoints-de-ops
    provides: "higyrus `get_health() -> Health`, el primer sitio de decode tipado del driver"
  - phase: 15-driver-migration
    provides: "el patrón ONE Client per main() que el kwarg `strict_decode` tiene que respetar"
provides:
  - "`verification/divergences.py` — el puente record-de-decode -> finding `SHAPE` que el criterio 1 de la fase no tenía"
  - "`DivergenceHandler` con `.seen` (unidad del censo) y `.errors` (fallas contables del sink)"
  - "`divergence_capture` — CM de instalación que sube los cinco loggers de paquete a INFO y restaura"
  - "`probe_context` — decorador sync+async que bindea endpoint/superficie y ofrece el seam `decode_error`/`on_decode_error`"
  - "`endpoint_scope` — re-binding de endpoint para probes multi-endpoint (P-5)"
  - "la convención de título lockeada que 33-02..33-07 leen sin re-derivar"
  - "`33-BASELINE.md` — la línea base roja de `verification/` con destino de reparación nombrado"
affects: [33-02, 33-03, 33-04, 33-05, 33-06, 33-07]

actuals:
  tokens: 10500
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "logging.Handler como adaptador record -> artefacto, con guard total en emit y fallas talladas en una lista contable"
    - "ContextVar como transporte de contexto lateral que el record congelado no puede llevar"
    - "seam de excepción inyectada (decode_error/on_decode_error) para que un módulo genérico no importe ningún paquete"

key-files:
  created:
    - verification/divergences.py
    - verification/test_divergences.py
    - .planning/phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-BASELINE.md
  modified:
    - verification/__init__.py
    - main_higyrus.py
    - .planning/ROADMAP.md

key-decisions:
  - "Convención de título lockeada: `surface-in-title-write-new` — la superficie VA en el título, así que la identidad de dedupe es de seis componentes y el conteo de findings es ~2x el de triples; el censo se cuenta de `DivergenceHandler.seen`, nunca del conteo de findings"
  - "matriz F-03..F-08: se escriben seis findings NUEVOS al lado y se triagean a NO-FIX referenciando los originales; ninguna tabla de matcheo de títulos dentro del handler (sería el patrón hand-rolled que D-07 borra en esta misma fase)"
  - "`probe_context` NO importa ningún `*_client`: la clase de decode-error y el fallback con forma de ProbeResult se inyectan por kwargs, porque la excepción difiere por paquete"
  - "El triple del censo se agrega a `.seen` ANTES de llamar al sink, para que una falla de escritura no se lea como un censo más chico"
  - "El nombre punteado del logger raíz no aparece en `divergences.py` ni en prosa — el criterio de aceptación del plan lo grepea y una mención en comentario se lee igual que una referencia en código (precedente 32-02)"
  - "El rot rojo de `verification/` se rutea a un ítem de backlog nombrado (`HARN-VERIF-01`) y no a una fase de v1.6: ni 33 (P-13 lo excluye por escrito) ni 34 (releases) pueden ser dueños honestos"

patterns-established:
  - "Handler auto-guardado: `emit` envuelve su cuerpo entero y tallya la falla, porque el emisor upstream corre dentro de un `contextlib.suppress` y un raise se pierde sin rastro"
  - "No-vacuidad por falsificación: cada endurecimiento se remueve temporalmente y se observa qué test enrojece, antes de dar el test por bueno"
  - "Línea base roja committeada: un suite fuera de CI se mide y se archiva con SHA, fecha, node ids y destino de reparación, para que una regresión futura sea mecánicamente distinguible del rot"

requirements-completed: []

coverage:
  - id: D1
    description: "Un record de decode de seis claves emitido dentro de una llamada bindeada por probe_context produce exactamente un finding SHAPE que carga endpoint, modelo, ruta de campo y superficie"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_divergences.py::test_handler_maps_record_to_shape_finding"
        status: pass
    human_judgment: false
  - id: D2
    description: "probe_context bindea y resetea endpoint+superficie en superficie sync y en async def (D-02)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_divergences.py::test_probe_context_binding"
        status: pass
    human_judgment: false
  - id: D3
    description: "divergence_capture sube los cinco loggers de paquete a INFO, restaura nivel y handlers al salir, y deja el logger raíz intacto (P-1 / T-33-05)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_divergences.py::test_install_sets_level_and_restores"
        status: pass
      - kind: unit
        ref: "verification/test_logging_root_unchanged.py::test_importing_packages_does_not_modify_logging_root"
        status: pass
    human_judgment: false
  - id: D4
    description: "El record INFO de especie extra llega al handler con el nivel subido y provablemente NO llega sin él (P-1)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_divergences.py::test_extra_kind_is_captured"
        status: pass
    human_judgment: false
  - id: D5
    description: "Una falla del sink es una entrada contable en handler.errors, nunca una excepción perdida; el triple del censo sobrevive (P-2 / T-33-04)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_divergences.py::test_emit_never_raises[ValueError]"
        status: pass
      - kind: unit
        ref: "verification/test_divergences.py::test_emit_never_raises[OSError]"
        status: pass
    human_judgment: false
  - id: D6
    description: "main_higyrus.py seedea su allocator de fids por encima de los F-01/F-02 terminales, threadea strict_decode por los dos únicos sitios de constructor, y ya no tiene el catch hand-rolled de HigyrusDecodeError en ninguna superficie (P-3 / D-07)"
    requirement: "LIVE-TYP-01"
    verification:
      - kind: unit
        ref: "verification/test_main_higyrus_uses_single_client_instance.py::test_main_higyrus_uses_single_client_instance"
        status: pass
      - kind: unit
        ref: "verification/test_main_drivers_bare_except.py::test_no_bare_except_in_driver[main_higyrus.py]"
        status: pass
      - kind: other
        ref: "uv run --package higyrus-client python -c 'import main_higyrus as m; m._seed_fid_counter()' -> counter 0 -> 2, next fid F-03"
        status: pass
    human_judgment: false
  - id: D7
    description: "La línea base roja de verification/ queda committeada con SHA, fecha, node ids y destino de reparación nombrado (P-13)"
    verification:
      - kind: other
        ref: "uv run pytest verification -q --tb=no -rfE -> 19 failed, 368 passed, 19 errors in 830.31s @ 0a9fdae"
        status: pass
    human_judgment: true
    rationale: "Decidir que el rot es pre-existente y no absorbible por LIVE-TYP-01, y elegir su destino de reparación, es un juicio de scope, no un chequeo mecánico."

duration: 28min
completed: 2026-08-26
status: complete
---

# Phase 33 Plan 01: TRACER — divergence handler wired through higyrus get_health Summary

**El criterio 1 de la Phase 33 pasa de no tener mecanismo a tener uno probado end to end: un record de decode de seis claves emitido por `higyrus_client` dentro de una llamada bindeada aterriza como un finding `SHAPE` con endpoint, modelo, ruta de campo y superficie — y los tres canales de pérdida silenciosa que convertirían una corrida en vivo en un falso limpio quedan cerrados y pineados por falsificación desde el primer commit.**

## Title convention (locked)

**Selection (verbatim): `surface-in-title-write-new`**

Resolved under auto-mode (`workflow.auto_advance: true`, `mode: yolo`) as the first-listed
option of the Task 1 `checkpoint:decision`, which the plan itself annotates as
"the RESEARCH-recommended default (Open Question 1)". Recorded here per the task's
`<resume-signal>`: Task 2's title format and 33-05's census table both read from this section.

### (a) The surface IS embedded in the title

The exact f-string `DivergenceHandler.emit` uses, byte-for-byte:

```python
title=f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]"
```

where every interpolated name comes ONLY from the frozen six-key record
(`model`, `field_path`, `divergence`, `declared_type`, `observed_type`) plus the
`surface` this module itself bound via `_SURFACE` — never from a wire value
(prohibition P-01 / T-33-01 / Lock 11).

Consequences that downstream plans must honour:

- The cross-run `idempotent_by_title` dedupe identity is
  `(model, field_path, kind, declared, observed, surface)` — six components, surface included.
- A sync-only or async-only divergence is therefore visible as its own finding, which is
  what criterion 1 asks for.
- **The finding count is roughly 2× the distinct-triple count.** `33-CENSUS.md` (plan 33-04)
  and `33-LITERALS.md` (plan 33-05) MUST report and label BOTH numbers so the ≥96 floor
  contrast is not misread.
- **The census unit is never the finding count.** It is `DivergenceHandler.seen`, a set of
  distinct `(slug, model, field_path, kind)` 4-tuples — the only unit directly comparable
  to `29-SIZING.md` without translation (D-06, aggregation-contract locks 1 and 5).

### (b) matriz `F-03`..`F-08` disposition: write six NEW findings

The six hand-written `NO-FIX` records `F-03`..`F-08` in
`.planning/verification/matriz-client-findings.md` (the S-4 `extra` keys on
`InstrumentDetail`: `securityIdSource`, `securityType`, `settlType`, `strike`, `symbol`,
`underlying`) are **NOT** absorbed by title matching.

- The handler writes six new `OPEN` `SHAPE` findings alongside them, under the deterministic
  title format above.
- Those six are then triaged to `NO-FIX` **referencing the original fid** in their triage prose.
- No bespoke per-finding title table is introduced inside the handler — that would be the exact
  hand-rolled pattern D-07 deletes elsewhere in this phase, and any drift between the table and
  the real titles would silently revert to writing duplicates anyway.
- The six original records keep their operator prose and their `NO-FIX` disposition untouched:
  `append_finding`'s non-`OPEN` short-circuit preserves them byte-identically.

### Task 1 acceptance

No source file was modified by this task — `git status --porcelain verification/ main_higyrus.py`
was empty at the end of it. The only artifact was this section (commit `29de6b8`).

## Firma pública final (lo que 33-02, 33-03 y 33-04 aplican sin re-derivar)

```python
from verification import DivergenceHandler, divergence_capture, endpoint_scope, probe_context
from verification.divergences import PACKAGE_LOGGERS

PACKAGE_LOGGERS: tuple[str, ...]   # los 5 _LOGGER_NAME verificados en cada _decode.py

class DivergenceHandler(logging.Handler):
    def __init__(self, next_fid: Callable[[str], str]) -> None: ...
    seen: set[tuple[str, str, str, str]]   # (slug, model, field_path, kind) — LA unidad del censo
    errors: list[str]                      # "<TipoDeExcepción>: <mensaje>" por falla del sink

@contextlib.contextmanager
def divergence_capture(
    logger_names: Sequence[str], *, next_fid: Callable[[str], str]
) -> Iterator[DivergenceHandler]: ...

def probe_context(
    endpoint: str,
    surface: str,
    *,
    decode_error: type[BaseException] | None = None,
    on_decode_error: Callable[[str, str, BaseException], Any] | None = None,
) -> Callable[[_F], _F]: ...

@contextlib.contextmanager
def endpoint_scope(endpoint: str) -> Iterator[None]: ...
```

Notas de uso que los planes siguientes necesitan:

- **`next_fid` recibe el slug.** Los `_next_fid()` de los drivers no toman argumentos, así
  que el sitio de instalación adapta: `next_fid=lambda slug: _next_fid()`.
- **`on_decode_error` recibe `(fn.__name__, surface, exc)`** y el wrapper devuelve su
  retorno **sin tocarlo**. En higyrus eso es `_shape_probe_result`, que devuelve el
  2-tuple `(ProbeResult(name, "FINDING", detail), None)` del driver. El nombre del probe
  llega con el prefijo `probe_` puesto; el helper lo saca con `removeprefix`.
- **`on_decode_error` NO debe escribir un finding.** El `SHAPE` ya lo escribió el handler
  desde el record que `_decode` emitió justo antes de levantar. Mintear uno acá duplicaría
  la divergencia bajo otro título y rompería el `idempotent_by_title` del lock 10 (D-07).
- **Si se pasa `decode_error` sin `on_decode_error`, la excepción se re-levanta.** El
  decorador nunca traga silenciosamente.
- **`endpoint_scope` re-bindea sólo el endpoint**, para los probes que golpean más de uno
  bajo una misma superficie (P-5, p.ej. `main_market_data.py::probe_health_sync`).

## Línea de resumen de `33-BASELINE.md`

```
19 failed, 368 passed, 19 errors in 830.31s (0:13:50)
```

Medido el 2026-08-26 sobre `0a9fdae`. **Los conteos de falla y error no se movieron** contra
la medición de RESEARCH (`19 failed, 362 passed, 19 errors`): el delta de +6 passed son
exactamente los seis casos nuevos de este plan. El 100% del rojo tiene **una sola** causa
raíz — dos archivos que llaman probes de `main_matriz.py` sin el parámetro `client` que la
migración REFAC-05 de la Phase 15 introdujo. Destino de reparación nombrado:
`HARN-VERIF-01` en `ROADMAP.md` § Backlog → *Deferred to v1.7+*.

**Ambos archivos son el canario de esta misma fase**: invocan los probes directamente y no
vía `main()`, así que los planes 33-02 y 33-03 deben re-correrlos tras aplicar el decorador
y comparar contra 17/17 y 2/2.

## Performance

- **Duration:** 28 min
- **Started:** 2026-08-26T23:08:33Z
- **Completed:** 2026-08-26T23:37:28Z
- **Tasks:** 3 de 3
- **Files created/modified:** 7 (1026 insertions, 35 deletions)

## Accomplishments

- **El puente que faltaba existe y está probado.** `verification/divergences.py` (319 líneas,
  stdlib-only, sin importar ningún `*_client`, sin referencia al logger raíz) traduce el
  record congelado de seis claves a un finding `SHAPE`, con endpoint y superficie viajando
  por `ContextVar` — el contexto de D-02 que el record no puede llevar.
- **Los tres canales de pérdida silenciosa quedan cerrados desde el primer commit, no
  retrofiteados.** P-1 (el CM sube los cinco loggers de paquete de NOTSET a INFO y restaura),
  P-2 (`emit` envuelve su cuerpo entero y tallya la falla en `.errors`), P-3 (el allocator de
  fids se inyecta y `main_higyrus.py` lo seedea por encima de sus dos fids terminales).
- **Cada endurecimiento está pineado por falsificación, no por afirmación.** Se removió cada
  uno temporalmente y se observó qué test enrojece: quitar la subida de nivel → 2 rojos;
  quitar el restore del `finally` → 2 rojos; angostar el guard de `emit` → 2 rojos; mover el
  `seen.add()` después del sink → 2 rojos. Con todo restaurado, 6 verdes.
- **El tracer corre end to end contra un probe real.** `probe_get_health_sync` y
  `probe_get_health_async` de higyrus están decorados, el catch hand-rolled de
  `HigyrusDecodeError` se borró de las dos superficies (D-07), y `strict_decode=_STRICT`
  viaja por los dos únicos sitios de constructor sin romper el gate AST de single-Client.
- **El rojo pre-existente de `verification/` deja de ser folclore y pasa a ser artefacto.**
  `33-BASELINE.md` fija el número, la lista de node ids, el SHA, la causa raíz única y un
  destino de reparación nombrado y greppable.

## Task Commits

1. **Task 1: Lock the finding-title convention and the matriz F-03..F-08 disposition** — `29de6b8` (docs)
2. **Task 2: TRACER — divergence handler wired end to end through higyrus get_health** — `f194ac8` (test, RED) → `8f891ca` (feat, GREEN)
3. **Task 3: Hardening suite for the three silent-loss channels + the verification/ red baseline** — `0a9fdae` (test) → `97eb04b` (docs, baseline)

## Files Created/Modified

- `verification/divergences.py` *(nuevo, 319 líneas)* — `DivergenceHandler`, `divergence_capture`,
  `probe_context`, `endpoint_scope`, `PACKAGE_LOGGERS`, `_SLUG_BY_LOGGER`, y los dos
  `ContextVar` module-private.
- `verification/test_divergences.py` *(nuevo, 343 líneas)* — los cinco tests de la Wave 0 de
  `33-VALIDATION.md` (6 casos: `test_emit_never_raises` está parametrizado sobre `ValueError`
  y `OSError`).
- `verification/__init__.py` — bullet de docstring, bloque de import alfabético y los cuatro
  nombres públicos en el `__all__` ordenado.
- `main_higyrus.py` — `_seed_fid_counter()`, `_STRICT`, `_shape_probe_result()`, los dos
  decoradores `probe_context`, el `strict_decode=_STRICT` en ambos constructores, y la
  eliminación de los dos bloques `except HigyrusDecodeError` hand-rolled.
- `.planning/phases/33-.../33-BASELINE.md` *(nuevo)* — la línea base roja committeada.
- `.planning/ROADMAP.md` — nueva sección de backlog *Deferred to v1.7+* con `HARN-VERIF-01`.

## Decisions Made

Además de la decisión lockeada de la Task 1 (arriba), en implementación:

1. **El triple del censo se agrega a `.seen` ANTES de llamar al sink.** Si se agregara después,
   una falla de escritura del archivo de findings haría que el censo reporte un número más
   chico — que se lee como "menos divergencias", es decir un falso limpio, en vez de como un
   error. Falsificado: mover el `add` después del sink enrojece `test_emit_never_raises`.
2. **`probe_context` no lleva un `except` de decode hardcodeado.** La clase de excepción
   difiere por paquete y el harness no puede importar ninguno. El seam
   `decode_error` / `on_decode_error` deja que cada driver aporte la suya y su propio
   fallback con forma de `ProbeResult`. Implementado con un centinela `_NeverRaised`
   inatrapable, para escribir **una** forma de wrapper por superficie en vez de dos.
3. **`emit` guarda el cuerpo entero, no sólo el `append_finding`.** Una lectura de atributo
   fallida sobre un record malformado es tan perdible como una falla del sink, porque el
   `suppress` upstream traga las dos igual.
4. **`_shape_probe_result` lee sólo los cuatro atributos certificados por T-29-36**
   (`model`, `field_path`, `declared_type`, `observed_type`) y nada más de la excepción
   (T-33-07). El `isinstance` que los narrowea deja una rama de fallback que no toca la
   excepción en absoluto.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `verification/divergences.py` mencionaba el nombre punteado del logger raíz en prosa**

- **Found during:** Task 2
- **Issue:** El criterio de aceptación del plan dice literalmente *"`verification/divergences.py`
  contains no reference to `logging.root`"*, y ese criterio se verifica con un grep. El módulo
  tenía tres menciones —todas en docstring/comentario, explicando justamente que NO se toca ese
  logger— así que el grep daba 3 y el criterio fallaba.
- **Fix:** Reescrita la prosa para hablar de "el logger raíz" sin el nombre punteado, con una
  nota explícita de por qué. Es exactamente el precedente que la Phase 32 (plan 32-02) ya
  estableció: *"ningún nombre de paquete aparece en el código del gate, docstring incluido —
  una mención en prosa se lee como roster hardcodeado para cualquiera que grepee uno"*.
- **Files modified:** `verification/divergences.py`
- **Verification:** `grep -c "logging\.root" verification/divergences.py` → `0`
- **Committed in:** `8f891ca`

**2. [Rule 2 - Missing critical] El destino de reparación nombrado del baseline no existía**

- **Found during:** Task 3
- **Issue:** La Task 3 exige rutear la reparación del rot de `verification/` a un destino
  nombrado "rather than absorbing it silently" (P-03: diferir sin destino no es una opción).
  Pero ninguna de las dos fases restantes de v1.6 puede ser dueña honesta: la Phase 33 excluye
  esta reparación de su scope por escrito (P-13) y la Phase 34 es releases por paquete, donde
  meter una reparación de harness repetiría el error que la Phase 28 ya rechazó una vez.
  Nombrar en el artefacto una fase que no puede recibirlo habría sido una ruta falsa —
  literalmente el mismo defecto de "reportar un destino que no inspecciona nada" que P-02
  prohíbe.
- **Fix:** Creado el ítem de backlog **`HARN-VERIF-01`** en `.planning/ROADMAP.md` § Backlog →
  nueva sección *Deferred to v1.7+ (from v1.6)*, con paquete, archivos, conteos, causa raíz,
  el gap gemelo de mypy y la advertencia de canario registrados. `33-BASELINE.md` explica por
  qué es un ítem de backlog y no una fase.
- **Files modified:** `.planning/ROADMAP.md`, `33-BASELINE.md`
- **Verification:** `grep -q "HARN-VERIF-01" .planning/ROADMAP.md`
- **Committed in:** `97eb04b`

**3. [Rule 1 - Bug] `PT022` y dos `type: ignore` no usados en el archivo de tests**

- **Found during:** Task 2
- **Issue:** El fixture `isolated_findings` usaba `yield` sin teardown (ruff `PT022`), y dos
  `# type: ignore[assignment]` sobre la asignación del sink resultaban innecesarios
  (`unused-ignore` bajo mypy strict, que `warn_unused_ignores` convierte en error).
- **Fix:** `yield` → `return` con la razón documentada (`monkeypatch` deshace el `setattr` en su
  propio teardown), y los dos `type: ignore` removidos.
- **Files modified:** `verification/test_divergences.py`
- **Verification:** `uv run ruff check .` limpio; `uv run mypy verification | grep -c "^verification/(divergences|test_divergences)\.py"` → `0`
- **Committed in:** `f194ac8` / `8f891ca`

---

**4. [Rule 1 - Bug] `requirements.mark-complete` cerró LIVE-TYP-01 en el plan 1 de 7**

- **Found during:** actualización de estado, después de la Task 3
- **Issue:** El paso de state-update del workflow marca los IDs del frontmatter `requirements`
  del plan, y los siete planes de la Phase 33 cargan `LIVE-TYP-01`. Cerrarlo acá sería una
  **completitud falsa**: este plan no entrega nada del scope declarado del requisito (ni corrida
  en vivo, ni evidencia de `Literal`, ni cycle closure) — construye el mecanismo que lo hace
  posible.
- **Fix:** Revertido `.planning/REQUIREMENTS.md` a `[ ] LIVE-TYP-01` / `Pending`. Es exactamente
  el precedente que la Phase 32 dejó escrito para GATE-TYP-01: *"cerrarlo en el plan 1 de 6
  sería una completitud falsa. Queda para el plan 32-06."* Acá queda para el plan 33-07.
- **Files modified:** `.planning/REQUIREMENTS.md` (revertido a HEAD; el commit final no lo toca)
- **Verification:** `grep "LIVE-TYP-01" .planning/REQUIREMENTS.md` → `- [ ]` y `| Pending |`;
  `git status --porcelain .planning/REQUIREMENTS.md` vacío
- **Committed in:** n/a — la corrección es la ausencia del cambio

---

**Total deviations:** 4 auto-fixed (2× Rule 1, 1× Rule 2, 1× Rule 3)
**Impact on plan:** Ninguno sobre el scope. Las tres son correcciones necesarias para que los
criterios de aceptación escritos en el plan se cumplan de verdad y para que el ruteo del
diferimiento no sea una referencia colgada. Cero scope creep: no se reparó ninguna de las 19
fallas ni ninguno de los 43 errores de mypy pre-existentes.

## Issues Encountered

- **La Task 3 no podía ser RED de la forma habitual.** Sus tres tests se escriben contra el
  módulo de la Task 2, que ya trae el endurecimiento — así que pasan al escribirse. En vez de
  fingir un RED, la no-vacuidad se demostró por **falsificación**: se removió cada
  endurecimiento y se registró qué test enrojece (4 experimentos, cada uno revertido con
  `git checkout -- <archivo>`). Eso es lo que el `<done>` de la task realmente pide
  ("pinned by a test that fails if the hardening is removed").
- **P-3 no queda pineado por un test en este plan.** El seed de fids vive en `main_higyrus.py`,
  fuera de los `<files>` de la Task 3, y el gate a nivel driver es de la Plan 33-04
  (`verification/test_probe_context_coverage.py`, `test_finding_count_consistency.py`). Acá se
  verificó **empíricamente**: sin seed el próximo fid sería `F-01` (que está `EXPECTED`,
  terminal → no-op silencioso de `append_finding`); con seed es `F-03`. Ver el carry-forward
  abajo.
- **`uv run pytest verification` tarda ~14 minutos.** Se corrió una sola vez, en background, y
  el resultado quedó archivado. Ninguna task gatea sobre él, por instrucción explícita de
  `33-VALIDATION.md`.

## Carry-forwards

1. **`verification/` está fuera de los dos scopes de mypy.** El `files` de `[tool.mypy]` lista
   sólo las seis raíces `packages/*/src` y el hook de pre-commit está scopeado
   `files: ^packages/.*/src/`, así que `verification/divergences.py` sólo se sostiene contra la
   barra estricta por el paso manual `uv run mypy verification` del bloque de verificación de
   este plan. Enrolarlo era trabajo de GATE-TYP-01 / D-16 y eso está cerrado; **es un gap de
   cobertura, no un CI failure**, y está explícitamente fuera del scope de LIVE-TYP-01 (P-9,
   RESEARCH Open Question 5). Medido hoy: 43 errores en 8 archivos, de los cuales **0** son de
   los dos archivos nuevos de este plan. Rutado a `HARN-VERIF-01`.
2. **El gate de P-3 a nivel driver es de la Plan 33-04.** `main_higyrus.py::_seed_fid_counter`
   existe y funciona, pero ningún test asevera el orden obligatorio
   `write_findings` < `_seed_fid_counter` < primer probe, como sí hace
   `verification/test_main_iol_fid_seed.py` para iol. La Plan 33-04 debería espejarlo para los
   cuatro drivers restantes.
3. **Los planes 33-02 y 33-03 deben re-correr los dos archivos canario** tras aplicar
   `probe_context` sobre `main_matriz.py`, y comparar contra **17 FAILED / 17 ERROR** y
   **2 FAILED / 2 ERROR** exactos. Un número distinto no es "más del rojo que ya estaba".
4. **El conteo de findings ≠ el conteo del censo.** Con la superficie en el título hay ~2
   findings por triple. `33-CENSUS.md` y `33-LITERALS.md` tienen que reportar y **etiquetar**
   los dos números; el contraste contra el piso ≥96 se hace contra `DivergenceHandler.seen`.

## Known Stubs

Ninguno. Todo lo que este plan entrega está cableado a una fuente de datos real: el handler se
alimenta del logger de paquete real, los tests escriben findings reales sobre `tmp_path`, y el
driver de higyrus llama a los probes reales. No hay valores hardcodeados vacíos ni componentes
sin fuente.

## TDD Gate Compliance

Secuencia de gates verificable en `git log`:

| Gate | Commit | Evidencia |
|---|---|---|
| RED | `f194ac8` | `test(33-01)` — ambos tests fallan con `ModuleNotFoundError: No module named 'verification.divergences'`, observado antes de escribir el módulo |
| GREEN | `8f891ca` | `feat(33-01)` — implementación mínima hasta que ambos pasan |
| RED/GREEN (Task 3) | `0a9fdae` | `test(33-01)` — no-vacuidad demostrada por falsificación (4 experimentos revertidos) en lugar de un RED sintético |

Sin fase REFACTOR: no hizo falta.

## Verification Evidence

| Gate | Resultado |
|---|---|
| `uv run pytest verification/test_divergences.py -q` | 6 passed (5 nombres, 1 parametrizado ×2) |
| `uv run pytest verification/test_main_higyrus_uses_single_client_instance.py verification/test_main_drivers_bare_except.py verification/test_logging_root_unchanged.py -q` | 4 passed |
| `uv run python tools/check_decode_intactness.py` | exit 0 — Checks A/B/C/D verdes, ninguna copia de `_decode.py` tocada |
| `uv run python tools/check_surface_types.py && uv run python tools/check_uniform_structure.py` | ambos exit 0 |
| `uv run pytest packages/higyrus-client -q` | 239 passed |
| `uv run pytest packages -q` (equivalente CI) | 1736 passed, 1 deselected |
| `uv run mypy` | Success: no issues found in 75 source files |
| `uv run mypy verification` | 43 errores pre-existentes en 8 archivos; **0** en los dos archivos nuevos |
| `uv run ruff check . && uv run ruff format --check .` | limpio, 245 archivos formateados |
| `verification/__all__` re-exporta los 4 nombres | `['DivergenceHandler', 'divergence_capture', 'endpoint_scope', 'probe_context']` |
| `grep -c 'logging\.root' verification/divergences.py` | 0 |
| `grep -E '^\s*(from\|import)\s+\w*_client' verification/divergences.py` | vacío |
| `grep -v '^#' main_higyrus.py \| grep -c '_seed_fid_counter'` | 5 (≥2 requerido) |
| `grep -v '^#' main_higyrus.py \| grep -c 'strict_decode=_STRICT'` | 2 |
| `grep -c 'except HigyrusDecodeError' main_higyrus.py` | 0 |
| `git status --porcelain .planning/verification/` | vacío tras la corrida completa |

## Self-Check: PASSED

- Los 6 archivos declarados en `key-files` existen en disco.
- Los 5 hashes de commit declarados existen en `git log`.
- La sección `## Title convention (locked)` de la Task 1 está preservada verbatim, con el
  id de opción `surface-in-title-write-new` que 33-02..33-07 leen.
