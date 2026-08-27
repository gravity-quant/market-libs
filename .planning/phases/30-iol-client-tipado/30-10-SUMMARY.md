---
phase: 30-iol-client-tipado
plan: 10
subsystem: testing
tags: [verification-harness, redaction, sys-excepthook, traceback, ast-lock, findings, tdd]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado (plan 08)
    provides: "_capture_raw_wire + el marker de body de wire y la disciplina de tests offline (test_main_iol_raw_wire_drift.py)"
  - phase: 30-iol-client-tipado (plan 09)
    provides: "_redacted_exc — el único renderer sancionado del driver (AD-30-09-01) — y las secciones 1-3 de test_main_iol_exception_redaction.py"
  - phase: 11 (HARN-07/08/10)
    provides: "verification/findings.py::append_finding con short-circuit de status humano promovido + max_existing_fid (D-16/D-24)"
provides:
  - "main_iol._seed_fid_counter() — el allocator de fids del driver arranca por encima de todo fid ya registrado en el findings file committeado"
  - "main_iol._redacted_excepthook — el camino de crash (excepción NO atrapada → sys.excepthook → stderr → logs de CI) deja de renderizar el body de error upstream"
  - "main_iol._install_redacted_excepthook — instalador nombrado, invocado como primer statement del guard __main__"
  - "verification/test_main_iol_fid_seed.py — suite de regresión driver-level (5 casos) con lock AST de wiring y control de no-vacuidad"
  - "sección 4 de verification/test_main_iol_exception_redaction.py — contrato del camino de crash (7 casos) incl. subproceso end-to-end por la maquinaria real de CPython"
affects: [30-VERIFICATION quinto ciclo, 30-11 (widening del lock AST), 33-LIVE-TYP-01 (audit de los otros cinco main_*.py)]

actuals:
  tokens: 21500
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Excepthook redactado que DELEGA al renderer sancionado en vez de reimplementar la redacción"
    - "traceback.print_tb (frames only) en vez de print_exception/print_exc — la cadena de causas nunca se renderiza"
    - "Lock AST de wiring: una función definida-pero-no-llamada falla el test, igual que una llamada fuera de orden"
    - "Control de no-vacuidad por caso gemelo: el mismo drive con y sin el fix, asertando el daño exacto en la mitad sin fix"

key-files:
  created:
    - verification/test_main_iol_fid_seed.py
  modified:
    - main_iol.py
    - verification/test_main_iol_exception_redaction.py

key-decisions:
  - "AD-30-10-01 ejecutada tal como fue firmada: el camino de crash se cierra con un sys.excepthook nombrado instalado desde el guard __main__, NO con un try/except alrededor de main(). Un try/except bindearía la excepción dentro de un ast.ExceptHandler — exactamente la forma de nodo que _raw_exception_renders recorre — así que el fix tendría que sobrevivir a su propio lock de regresión; además sólo cubriría lo que se levanta bajo main(), y el módulo corre load_dotenv() a través de la cadena de import de iol_client antes de eso."
  - "El hook usa traceback.print_tb (toma el objeto traceback → imprime SÓLO frames). Los helpers que toman la excepción o el triple de exc_info agregan la línea del mensaje y recorren __cause__/__context__, reintroduciendo la fuga. El costo aceptado es el mensaje de una causa encadenada: costo de triage, no fuga."
  - "El hook imprime y RETORNA: CPython sigue matando el proceso con exit code != 0. El intent D-04 (un tipo inesperado aborta el run, no se degrada a finding) sobrevive intacto; lo único que cambia es el texto."
  - "El camino de crash es la única salida del driver que NO pasa por safe_print — safe_print escribe sólo a stdout y no toma parámetro de archivo, y mezclar la salida del crash en stdout corrompería la línea SUMMARY. Registrado como bullet explícito en las 'Reglas de seguridad' del module docstring para que el próximo revisor no lo lea como violación."
  - "_seed_fid_counter espeja main_market_data.py verbatim en forma (global + max_existing_fid(_PKG)) y en intención del docstring; no se inventó una variante."

patterns-established:
  - "Lock AST de wiring como criterio que falla HOY: los dos casos que fallaban en RED por wiring (seed no llamado; guard __main__ sin instalador) son la evidencia de que el gap era de binding y no de existencia de helper"
  - "Caso de control de no-vacuidad que documenta el daño pre-fix y DEBE seguir verde post-fix, porque saltea deliberadamente el fix"
  - "Subproceso con sys.executable -c para probar contra la maquinaria real de crash de CPython, con el body construido desde una variable para que la línea que levanta no pueda cargar el marker"

requirements-completed: []

coverage:
  - id: D1
    description: "main_iol.py seedea su allocator de fids desde el findings file committeado, entre write_findings(_PKG) y el primer probe — un run vivo contra F-01 (OPEN) / F-02 (FIXED) archiva desde F-03 sin pisar ni perder nada"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "verification/test_main_iol_fid_seed.py (5 passed)"
        status: pass
      - kind: unit
        ref: "verification/test_findings_fid_seed.py (7 passed, byte-idéntico)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Una excepción que escapa de cualquier probe llega a _redacted_excepthook, que emite una línea ABORT: con sólo la clase y un status code int-guardeado más frames sin cadena de causas, y el proceso igual muere con exit code != 0"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "verification/test_main_iol_exception_redaction.py sección 4 (7 casos nuevos; 25 passed en total)"
        status: pass
      - kind: e2e
        ref: "verification/test_main_iol_exception_redaction.py::test_the_installed_hook_survives_the_real_crash_machinery (subproceso, marker ausente de stdout y stderr, returncode != 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "packages/ y .planning/verification/ byte-inalterados; las cuatro suites de regresión previas verdes y las dos cuya identidad byte importa, byte-idénticas"
    verification:
      - kind: integration
        ref: "git diff --exit-code packages/ .planning/verification/ (exit 0); uv run pytest packages/iol-client -q (242 passed); uv run mypy packages/iol-client/{src,tests} (25 source files)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-08-23
status: complete
---

# Phase 30 Plan 10: Cierre de los dos BLOCKERs del cuarto ciclo Summary

**`main_iol.py` deja de destruir su propio entregable (el allocator de fids ahora arranca por encima de los findings ya triageados) y deja de filtrar el body de error upstream por el camino de crash (un `sys.excepthook` redactado que delega en `_redacted_exc` y sigue matando el proceso).**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-23T18:00:26Z
- **Completed:** 2026-08-23T18:06:52Z
- **Tasks:** 2 (ambas TDD, RED → GREEN)
- **Files modified:** 3 (1 creado, 2 modificados)

## Accomplishments

- **Gap 1 (truth 7 / CR-01) cerrado.** `main_iol.py` importa `max_existing_fid`, define `_seed_fid_counter()` inmediatamente arriba de `_next_fid`, y lo llama dentro de `main()` entre `write_findings(_PKG)` y el primer probe. Contra el archivo committeado real (`F-01` OPEN + `F-02` FIXED) la próxima corrida viva archiva desde `F-03`: ni reescribe el triage que el operador arrastra desde la Phase 17, ni pierde en silencio un finding mientras el `SUMMARY` reporta éxito.
- **Gap 2 (truth 8 / CR-02) cerrado.** `_redacted_excepthook` + `_install_redacted_excepthook` cierran el último sink conocido del body de wire en este repo. El camino no-atrapado —que 30-08 y 30-09 dejaron abierto al cerrar 32 sitios atrapados— ahora emite una sola línea `ABORT: IOLAPIError status_code=500` más frames de traceback, a stderr, y el proceso sigue muriendo con exit code distinto de cero.
- **Los dos fixes quedan bajo lock AST de wiring.** No basta con que las funciones existan: `test_main_calls_the_seed_between_the_bootstrap_and_the_first_probe` falla si el seed se define y no se llama (o se llama fuera de orden), y `test_the_main_guard_installs_the_hook_before_running_main` falla si el hook se define y no se instala (o se instala después de `main()`). Esos dos casos son precisamente los que fallaban en RED — la evidencia de que el gap era de *binding*, no de existencia de helper.
- **Ambas suites probadas no-vacuas** por sondas temporales revertidas desde copias en scratchpad (gates 11 y 12, detalle abajo).

## Task Commits

1. **Task 1: Seed the driver's fid allocator** — `5f03767` (test, RED) → `0839708` (feat, GREEN)
2. **Task 2: Redact the crash path** — `95ab598` (test, RED) → `3b2ace2` (feat, GREEN)

RED estrictamente antes de GREEN en ambas tareas.

### Conteos RED medidos

| Tarea | RED medido | Modo de falla observado |
|---|---|---|
| 1 | **4 failed / 1 passed** (de 5 casos; `--collect-only` exit 0, la RED fue de runtime y nunca error de colección) | 3 casos con `AttributeError: module 'main_iol' has no attribute '_seed_fid_counter'. Did you mean: '_fid_counter'?`; 1 caso (lock AST) con `AssertionError: se esperaba exactamente un _seed_fid_counter(), hay []`. **El caso que pasó en RED es el control** (`test_unseeded_run_clobbers_f01_and_silently_drops_the_second_finding`): documenta el daño pre-fix salteando el seed a propósito, así que debe pasar en RED **y** en GREEN. |
| 2 | **7 failed / 18 passed** (los 18 pre-existentes de las secciones 1-3 quedaron verdes todo el tiempo) | 4 casos con `AttributeError: module 'main_iol' has no attribute '_redacted_excepthook'`; el caso de subproceso con `AttributeError: module 'main_iol' has no attribute '_install_redacted_excepthook'` observado en el `stderr` del hijo (`returncode=1`, `stdout=''`); el caso del instalador con el mismo `AttributeError`; el lock AST con `AssertionError: el guard __main__ debe instalar el hook y después llamar a main(); es: ['main']`. |

## Files Created/Modified

- `main_iol.py` — nuevo import `max_existing_fid`; nuevos imports stdlib `sys`, `traceback`, `types.TracebackType`; `_seed_fid_counter()`; llamada al seed en `main()`; `_redacted_excepthook()` + `_install_redacted_excepthook()` arriba del guard; guard `__main__` reescrito a instalar-y-después-`main()`; comentario del `_fid_counter` extendido; bullet nuevo en las "Reglas de seguridad" del module docstring registrando la excepción a `safe_print`.
- `verification/test_main_iol_fid_seed.py` — **nuevo** (297 líneas): fixture autouse de tres cinturones (`_FINDINGS_DIR` → `tmp_path`, `IOL_TOKEN_CACHE_PATH` → `tmp_path`, reset del state del driver), helper que construye el fixture pasando por el serializador real, y 5 casos.
- `verification/test_main_iol_exception_redaction.py` — sección 4 apendeada (7 casos) + docstring del módulo de "tres secciones" a cuatro. Secciones 1-3 sin renumerar, sin reordenar y sin tocar `_WIRE_BODY_MARKER` / `_OFFENDING_SOURCE` / `_COMPLIANT_SOURCE` / `_OFFENDING_LINES` (30-11 es dueña de esas).

## Verification — todos los gates medidos

| # | Gate | Esperado | **Medido** |
|---|------|----------|-----------|
| 1 | `uv run pytest verification/test_main_iol_fid_seed.py -q` | 0 failed, ≥5 passed, 0 skipped | **5 passed, 0 failed, 0 skipped** |
| 2 | `uv run pytest verification/test_main_iol_exception_redaction.py -q` | 0 failed, ≥25 passed, 0 skipped | **25 passed, 0 failed, 0 skipped** |
| 3 | `uv run pytest verification/test_findings_fid_seed.py verification/test_main_iol_raw_wire_drift.py -q` | 7 + 22 passed | **29 passed** (7 + 22) |
| 4 | `git diff --exit-code` sobre esos dos archivos | exit 0 | **exit 0 — byte-idénticos** |
| 5 | `uv run pytest verification/test_main_iol_uses_single_client_instance.py verification/test_main_drivers_bare_except.py -q` | all passed | **3 passed** |
| 6 | `uv run pytest packages/iol-client -q` | `242 passed` | **242 passed** |
| 7 | `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` | **`Success: no issues found in 25 source files`** |
| 8 | `uv run ruff check main_iol.py verification` + `ruff format --check` | clean | **`All checks passed!` / `49 files already formatted`** |
| 9 | **Reversibilidad** — `git diff --exit-code packages/ .planning/verification/` | exit 0 | **exit 0** |
| 10 | `git status --porcelain` | sólo los 3 archivos del plan | **OK** — los 3 archivos quedaron committeados; lo único pendiente es state/artefactos de planning previos al plan (`.planning/STATE.md` tocado por el orquestador, `30-VERIFICATION.md` y el cache de research, todos pre-existentes al arranque) |
| 11 | No-vacuidad de la suite de fid | el caso swallowed falla cuando el seed SÍ se aplica | **demostrado** (detalle abajo) |
| 12 | No-vacuidad de la suite de crash | con el hook mudo, las aserciones de `ABORT:` y de frames fallan | **demostrado** (detalle abajo) |

### Gate 11 — cómo se demostró y cómo se revirtió

Copia de `verification/test_main_iol_fid_seed.py` guardada en scratchpad; dentro de `test_unseeded_run_clobbers_f01_and_silently_drops_the_second_finding` se reemplazó el comentario "Seed deliberadamente NO llamado" + su assert por una llamada real a `main_iol._seed_fid_counter()`. Resultado: **1 failed, 4 passed**.

**La aserción que cargó la prueba** es la de la línea 236, `assert _OPERATOR_TITLE not in text` ("se esperaba que el write ingenuo reescribiera F-01 (OPEN) en el lugar"): con el seed aplicado el título del operador **sobrevive**, así que el caso que afirma el daño destructivo falla. Eso es exactamente lo que hace no-vacuo al caso gemelo `test_seeded_run_files_new_findings_above_the_committed_ones` — los dos drives son idénticos salvo por el seed, y producen resultados opuestos sobre el archivo.

Revertido copiando de vuelta desde el scratchpad. Verificado: `grep -c "GATE-11 PROBE"` → `0`, y `git diff --exit-code` sobre el archivo → exit 0.

### Gate 12 — cómo se demostró y cómo se revirtió

Copia de `main_iol.py` guardada en scratchpad; el cuerpo de `_redacted_excepthook` se reemplazó por un `del exc_type, exc, tb` (el hook no imprime nada). Resultado: **5 failed, 20 passed**.

Los 5 que caen son los 5 que asertan salida: los tres casos directos que exigen `IOLAPIError status_code=500` / `_ExceptionWithNonIntegerStatus status_code=None` en stderr, el caso de frames (`File "` + `line `), y el caso de subproceso (`CompletedProcess(..., returncode=1, stdout='', stderr='')` — el proceso murió, pero **sin una sola línea de salida**, que es justo el falso-verde que la aserción de `ABORT:` bloquea). Los 2 que siguen verdes son los correctos: el lock AST del guard y el test del instalador asertan **estructura**, no salida, así que un hook mudo pero bien cableado los satisface por diseño.

Revertido copiando de vuelta desde el scratchpad. Verificado: `grep -c "GATE-12 PROBE"` → `0`, y `git diff --exit-code main_iol.py` → exit 0.

## Decisions Made

Ver `key-decisions` en el frontmatter. La sustantiva es **AD-30-10-01**, ejecutada tal como fue firmada en el plan: excepthook nombrado instalado desde el guard, no un `try/except` alrededor de `main()`. Las dos razones se sostuvieron en la ejecución: (a) un `try/except` bindearía la excepción dentro de un `ast.ExceptHandler`, que es la forma de nodo que `_raw_exception_renders` recorre, así que el fix tendría que sobrevivir a su propio lock; (b) un wrapper en `main()` no cubre nada levantado en tiempo de import, y el cuerpo del módulo corre `load_dotenv()` a través de la cadena de import de `iol_client`.

Detalle de implementación que vale registrar: el hook hace `del exc_type` con comentario, espejando la forma que el driver ya usa en sus handlers mock (`del request`), porque el nombre de la clase ya viaja adentro de `_redacted_exc(exc)`.

## Deviations from Plan

**None — plan executed exactly as written.**

No hubo auto-fixes bajo las Reglas 1-3, ni escalaciones bajo la Regla 4, ni gates de autenticación. Cero instalaciones de paquetes (`sys`, `traceback` y `types.TracebackType` son stdlib; `pytest`/`httpx` ya estaban en `uv.lock`), así que el Package Legitimacy Gate se satisface por construcción tal como el `<threat_model>` anticipó (T-30-10-SC).

## Issues Encountered

Uno, trivial y resuelto en el momento: el `# noqa: BLE001` que acompañaba al `except BaseException as caught` del helper `_caught` fue rechazado por ruff con `RUF100 Unused 'noqa' directive (non-enabled: BLE001)` — `BLE` no está en el conjunto de reglas del repo. Se quitó el directive; el handler es legítimo (re-captura deliberada del mismo objeto para que cargue un `__traceback__` real) y ninguna regla habilitada lo marca.

## Carry-forwards deliberadamente NO cerrados en este plan

Registrados acá explícitamente para que el quinto ciclo de verificación no vuelva a derivar el límite de scope desde cero:

| Item | Origen | Por qué queda abierto |
|---|---|---|
| **WR-03** | 30-REVIEW.md | 22 lecturas inline de `exc.status_code` en argumentos `diff=`. No escalado a BLOCKER; fuera del `gaps:` block de 30-VERIFICATION.md. |
| **WR-04** | 30-REVIEW.md | `_redacted_exc` puede levantar si `status_code` es una property que levanta. Fuera de scope por instrucción explícita del plan ("do not touch `_redacted_exc`'s body"). Nota: este plan **reduce** su blast radius — una falla de `_redacted_exc` dentro de un handler ahora escapa hacia el hook redactado en vez de hacia el default. |
| **WR-05** | 30-REVIEW.md | Sin cobertura end-to-end de redacción async. |
| **WR-06** (numeración de 30-REVIEW) | 30-REVIEW.md | Un `ultimoPrecio` legítimamente cero emite un finding OPEN permanente. |
| **IN-01 .. IN-05** | 30-REVIEW.md | Ninguno escalado a BLOCKER. |
| **Widening del lock AST** | 30-REVIEW.md `WR-01` (numeración **actual**) | **Planificado como 30-11**, explícitamente prohibido de adelantar acá. Las constantes `_OFFENDING_SOURCE` / `_COMPLIANT_SOURCE` / `_OFFENDING_LINES` / `_WIRE_BODY_MARKER` quedaron intactas para esa plan. |
| Anti-vacuidad del probe 13, numeral del detalle PASS, binding de `DecodeScope` | 30-09-SUMMARY.md | Carry-forwards viejos, sin cambio. |

**Riesgo de numeración, re-registrado:** la lista de carry-forwards de 30-09-SUMMARY.md usa la numeración WR de la revisión *anterior*, donde `WR-01` significaba "anti-vacuidad del probe 13". El `30-REVIEW.md` actual reusa `WR-01` para la ceguera del lock AST. Son ítems distintos.

**`TYP-01` NO se marcó completo en `.planning/REQUIREMENTS.md`**, por instrucción explícita del `<output>` del plan y por el precedente de la deviación 3 de 30-09-SUMMARY.md: el operador ya revirtió un `mark-complete` prematuro de este requisito, la fase debe otro ciclo de verificación, y 30-11 está planificada pero no ejecutada.

## Known Stubs

Ninguno. Ninguna función nueva devuelve un valor placeholder ni tiene una fuente de datos sin cablear; los dos wirings que este plan agrega (`_seed_fid_counter()` en `main()` y `_install_redacted_excepthook()` en el guard) están cada uno bajo un lock AST que falla si el cableado desaparece.

## Threat Flags

Ninguna superficie de seguridad nueva fuera del `<threat_model>` del plan. Los tres símbolos agregados no abren endpoints de red, ni caminos de auth, ni patrones de acceso a archivos, ni cambios de esquema en una frontera de confianza. `_redacted_excepthook` escribe a stderr, que es un sink que el threat model ya declara en scope y para el cual T-30-10-01 / T-30-10-03 son la mitigación implementada y pinneada.

## Next Phase Readiness

- **30-11** (widening del lock AST, WR-01 de la numeración actual) está desbloqueada y sus constantes objetivo quedaron byte-intactas a propósito.
- **Quinto ciclo de 30-VERIFICATION.md**: los dos BLOCKERs del cuarto ciclo (truths 7 y 8) están cerrados con evidencia offline reproducible. La corrida viva contra `api.invertironline.com` sigue siendo del operador; cuando ocurra, los findings nuevos deben aparecer desde `F-03` y `F-01`/`F-02` deben quedar verbatim — ése es el chequeo de una línea que confirma D1 en vivo.
- **Phase 33** hereda el audit de los otros cinco `main_*.py`: `_raw_exception_renders` toma un *string* de fuente y no un path, precisamente para que ese audit lo apunte sin reescribirlo; el mismo argumento aplica ahora al camino de crash, que ningún otro driver tiene cerrado.

## Self-Check: PASSED

- Archivos: `main_iol.py`, `verification/test_main_iol_fid_seed.py`, `verification/test_main_iol_exception_redaction.py`, `.planning/phases/30-iol-client-tipado/30-10-SUMMARY.md` — los 4 presentes en disco.
- Commits: `5f03767`, `0839708`, `95ab598`, `3b2ace2` — los 4 presentes en `git log`.

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-23*
