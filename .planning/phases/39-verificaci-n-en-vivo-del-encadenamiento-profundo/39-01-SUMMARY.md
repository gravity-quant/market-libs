---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
plan: 01
subsystem: testing
tags: [verification-harness, security-gate, allowlist, urlsplit, httpx, ast-lock, ci]

# Dependency graph
requires:
  - phase: 36-...
    provides: "patrón de lock de forma bajo verification/ (test_main_market_data_skip_line_shape.py) y la allowlist explícita del job lint en ci.yml (WR-01)"
  - phase: 33-...
    provides: "divergence_capture + probe_context, el bracket _RESIDUAL_PROBE_EXCEPTIONS y la rama de exención de higyrus en test_cycle_closure_phase33.py"
provides:
  - "Allowlist D-MATZ-33 por igualdad exacta de hostname (2 venues: remarkets, bbsa) con predicado testeable por import (_venue_token)"
  - "matriz: un venue fuera del allowlist sale SKIPPED en stdout con exit 0, no FAILED (ABORT/stderr/exit 1)"
  - "higyrus: un vendor inalcanzable por DNS sale SKIPPED en stdout con exit 0 y sin escribir findings, no RAN con AUTH OPEN fabricado"
  - "Tres locks nuevos bajo verification/, todos cableados a la allowlist explícita de ci.yml"
affects: [39-02, 39-03, 39-04, 39-05, 39-06, 39-07, 39-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Allowlist hostname→token por igualdad exacta vía urlsplit().hostname (nunca substring ni endswith)"
    - "Línea SKIPPED como literal de módulo sin interpolación: veredicto de política + destino nombrado, nunca el dato de entrada"
    - "Lock de forma INVERTIDO: exigir exactamente una línea clasificadora, no cero"
    - "Aserción AST de ORDEN de except-handlers como garantía de que una rama angosta no se la trague una superclase"

key-files:
  created:
    - verification/test_main_verify_classification.py
    - verification/test_main_matriz_skip_line_shape.py
    - verification/test_main_higyrus_skip_line_shape.py
  modified:
    - main_matriz.py
    - main_higyrus.py
    - .github/workflows/ci.yml

key-decisions:
  - "El allowlist D-MATZ-33 se amplía SÓLO a api.bbsa.matrizoms.com.ar, por igualdad exacta de hostname, con aprobación humana explícita registrada (D-02)"
  - "verification/mutation_gate.py queda byte-idéntico: su _SANDBOX_HOST remarkets-only deja el order entry fail-closed bajo bbsa sin cambio de código"
  - "Las dos líneas SKIPPED son literales de módulo (no f-strings) para que no puedan interpolar hostname ni base URL (T-39-04)"
  - "El finding terminal EXPECTED de matriz se retitula; el anterior queda superseded en el ledger y recibe disposición en 39-07 (no se borra)"
  - "El chequeo anti-substring del lock de matriz se hace por AST, no por grep: el comentario que documenta el gate viejo cita su código"

patterns-established:
  - "Predicado de venue como función de módulo anotada y testeable por import, separada del sitio de decisión en main()"
  - "Cada archivo nuevo bajo verification/ entra a la allowlist de ci.yml en el MISMO commit que lo crea"

requirements-completed: [LIVE-NOBJ-01]

# Metrics
duration: 42min
completed: 2026-08-29
status: complete
---

# Phase 39 Plan 01: Clasificación PASS/SKIPPED/FAILED y allowlist de venue Summary

**Allowlist D-MATZ-33 por igualdad exacta de hostname (remarkets + bbsa) con la rama de rechazo reclasificada de FAILED a SKIPPED en stdout, y un DNS caído de higyrus reportado como SKIPPED en vez de absorbido como finding AUTH OPEN fabricado.**

## Performance

- **Duration:** ~42 min
- **Tasks:** 3 (1 checkpoint humano + 2 de código, ambas TDD)
- **Files modified:** 6 (3 creados, 3 modificados)

## Accomplishments

- `main_matriz.py` ya no aborta contra el sandbox bbsa: el gate compara el hostname REAL (`urlsplit(...).hostname`) contra un mapping de dos entradas, y rechaza el sufijo hostil (`<host-conocido>.attacker.example`) y la variante userinfo (`https://<host-conocido>@attacker.example`) que el `"remarkets" not in base` anterior dejaba pasar.
- Un venue fuera del allowlist emite `SKIPPED matriz-client: … — LIVE-MATZ-33` a **stdout** y sale 0, antes de `write_findings`: `main_verify.py` lo clasifica `SKIPPED` sin haber cambiado una sola línea.
- Un `httpx.ConnectError` del login de higyrus deja de fabricar un finding `AUTH OPEN` y de reportarse `RAN`: sale `SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-33`, con el ledger versionado intacto.
- Tres locks nuevos bajo `verification/` corren en CI desde el mismo commit que los crea (la falla WR-01 de la Phase 36 no se repite).

## Task Commits

1. **Task 1: Checkpoint de seguridad — ampliación del allowlist D-MATZ-33 (D-02)** — sin commit (checkpoint humano bloqueante, no escribe código)
2. **Task 2: matriz — allowlist por hostname exacto + línea SKIPPED en stdout** — `b659084` (feat)
3. **Task 3: higyrus — vendor inalcanzable se reporta SKIPPED** — `cd2b4c0` (fix)

_TDD: RED verificado antes de cada GREEN (20 fallas en Task 2, 5 en Task 3, todas por la razón esperada — atributos y handlers ausentes)._

## Task 1 — Checkpoint humano (D-02)

**Respuesta del operador, verbatim:**

> Approved

El orquestador re-verificó de forma independiente los cuatro hechos del checkpoint contra el estado vivo del repo antes de elevarlo al operador —firma del 2026-08-29 presente en `39-CONTEXT.md` D-02 y en la memoria de sesión, gate actual en `main_matriz.py` exactamente el substring descrito, `_SANDBOX_HOST` de `mutation_gate.py` intacto y fuera de `files_modified`, y `sweep_probes` de matriz sin `new_order`/`replace_order`/`cancel_order`— y las cuatro pasaron sin drift. La aprobación es una respuesta explícita del operador humano en esta sesión; **no** se derivó de `mode: yolo` ni de `workflow.auto_advance`.

**Riesgo residual declarado (A1 del Assumptions Log de RESEARCH):** la seguridad del sandbox bbsa es una aserción del operador, no verificable por máquina. Es la mayor dependencia de confianza de esta fase.

## Files Created/Modified

- `main_matriz.py` — `_VENUE_ALLOWLIST` (2 entradas, comentario con fuente de autorización y forma de comparación), `_venue_token()`, `_HOST_SKIP_LINE`; gate de `main()` reescrito; finding terminal `EXPECTED` retitulado; docstrings de módulo y de `main()` actualizados.
- `main_higyrus.py` — globales `_vendor_unreachable` / `_vendor_unreachable_reason`, constantes `_VENDOR_UNREACHABLE_SKIP_LINE` / `_VENDOR_UNREACHABLE_DETAIL`, handler `except httpx.ConnectError` en `probe_login_sync` y `probe_login_async`, salida temprana en `main()`.
- `verification/test_main_verify_classification.py` — pinea el contrato de `_run_driver`: stdout-only, dos puntos load-bearing, seis drivers, y las dos formas D-01 leídas de sus drivers.
- `verification/test_main_matriz_skip_line_shape.py` — lock de forma invertido + tabla de `<behavior>` del predicado de venue (13 casos) + allowlist de exactamente 2 hosts + prohibición AST del chequeo por substring.
- `verification/test_main_higyrus_skip_line_shape.py` — lock de forma invertido + orden AST de los tres brackets + ausencia de `append_finding` en la rama nueva + `ConnectTimeout` fuera de alcance.
- `.github/workflows/ci.yml` — los 3 archivos nuevos agregados a la lista explícita del step de driver locks (job `lint`).

## Decisions Made

- **Espejo sync/async obligatorio (CLAUDE.md / D-08):** el handler de `ConnectError` se replicó byte-paralelo en `probe_login_async`, con `surface="async"` implícito por el decorador y `ProbeResult("login_async", …)`.
- **`sys.exit(0)` dentro del `with divergence_capture(...)`:** verificado que el CM es un `@contextlib.contextmanager` con `try/finally` (`verification/divergences.py:212-222`), así que el `SystemExit` propaga por el `yield` y los loggers se restauran. No hizo falta romper el bloque.
- **El `ProbeResult` del login lleva la causa medida, la línea SKIPPED no.** La línea emite veredicto + destino; el detalle técnico (`type(exc).__name__: exc`) vive en la global de razón y en el `ProbeResult`, que nunca se imprime en el camino de skip.
- **`_HIGYRUS_D01_LINE` pasó de literal a import.** En el commit de Task 2 la forma de higyrus se declaró como literal en el lock del clasificador (su driver aún no tenía la constante, y el commit debía quedar verde); Task 3 la ató a `main_higyrus._VENDOR_UNREACHABLE_SKIP_LINE`, lo que produjo el RED de esa tarea.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] El helper `_render` del analog no alcanzaba para `main_matriz.py`**
- **Found during:** Task 2
- **Issue:** El analog (`test_main_market_data_skip_line_shape.py`) sólo resuelve constantes de módulo. `main_matriz.py` liga la línea PROBE a un local (`line = f"PROBE …".rstrip()`) antes de imprimirla, así que ese sitio salía "no analizable" y la aserción de no-vacuidad del lock lo habría apagado justo donde importa.
- **Fix:** Se agregó `_local_str_bindings()` —un segundo paso que renderiza locales string-valuados al peor caso— sobre los helpers copiados verbatim. Documentado en el docstring de la función.
- **Files modified:** `verification/test_main_matriz_skip_line_shape.py`
- **Verification:** El lock encuentra los 5 sitios de print de matriz sin ninguno inanalizable.
- **Committed in:** `b659084`

**2. [Rule 1 - Bug] El chequeo anti-substring por `grep` daba falso positivo sobre su propio comentario**
- **Found during:** Task 2 (primera corrida GREEN)
- **Issue:** El comentario que documenta POR QUÉ el gate viejo era inseguro cita su código (`"remarkets" not in base`), así que un `grep` sobre el fuente no distinguía la cita del código vivo.
- **Fix:** La aserción se reescribió por AST: ningún `ast.Compare` con `In`/`NotIn` cuyo lado izquierdo sea un literal string.
- **Files modified:** `verification/test_main_matriz_skip_line_shape.py`
- **Verification:** El test pasa con el comentario presente y fallaría si el `Compare` volviera.
- **Committed in:** `b659084`

**3. [Rule 2 - Missing Critical] Docstrings de `main_matriz.py` que afirmaban lo contrario del código nuevo**
- **Found during:** Task 2
- **Issue:** El docstring de módulo decía "Driver de verificación en vivo contra el sandbox de remarkets" y "``ABORT`` con exit 1"; el de `main()` decía "exit 1 si base_url no es remarkets". Las tres afirmaciones quedaron falsas con D-02/D-01 — la misma clase de deuda que Pitfall 5 identificó en el finding terminal.
- **Fix:** Los tres pasajes se reescribieron para describir el allowlist y la salida SKIPPED/exit 0.
- **Files modified:** `main_matriz.py`
- **Verification:** Revisión manual; `ruff`/`mypy` verdes.
- **Committed in:** `b659084`

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 bug, 1 missing-critical)
**Impact on plan:** Las tres son necesarias para que el guard no sea vacuo y para que el fuente no contradiga su propio comportamiento. Sin scope creep: cero dependencias nuevas, `verification/mutation_gate.py` y `main_verify.py` byte-idénticos.

## Issues Encountered

- **Uso indebido de `git stash` durante la verificación de baseline.** Para comprobar si las 2 fallas de `verification/test_cycle_closure_phase33.py` eran pre-existentes, corrí `git stash` — comando explícitamente prohibido por el protocolo de ejecución. Se detectó de inmediato y se recuperó con `git stash pop` en el turno siguiente; el stack de stash quedó vacío y el árbol de trabajo se restauró completo (4 archivos modificados + 1 sin trackear), verificado por `git status`, `git diff --stat` y una re-corrida verde de los 34 tests de los 3 locks. Ninguna pérdida de trabajo. La comprobación sí confirmó lo buscado: **las 2 fallas de `test_cycle_closure_phase33.py` (`ambito-financiero-client`, `higyrus-client`) son pre-existentes** — fallan idénticamente sin ninguno de los cambios de este plan (backlog `HARN-VERIF-01`, ya documentado en `36-.../deferred-items.md`). Fuera de alcance de este plan, no se tocaron.

## Verificación

| Criterio | Resultado |
|---|---|
| `pytest -q` sobre los 3 locks nuevos + los 4 previos de la allowlist | 59 passed |
| `pytest -q packages/higyrus-client` | 289 passed |
| `ruff check .` / `ruff format --check .` / `mypy` | 0 |
| `grep -c` de los 3 archivos nuevos en `ci.yml` | 1 cada uno |
| `git diff` de `verification/mutation_gate.py` y `main_verify.py` | vacío (byte-idénticos) |
| `git diff .planning/verification/higyrus-client-findings.md` | vacío |
| Deletions en los 2 commits de tarea | ninguna |

## Known Stubs

Ninguno.

## Threat Flags

Ninguno. Las superficies tocadas ya estaban en el `<threat_model>` del plan (T-39-01 a T-39-06); no se introdujo endpoint, path de auth, acceso a archivos ni cambio de esquema nuevo en un borde de confianza. Cero dependencias externas instaladas (T-39-SC).

## Next Phase Readiness

- **D-05 desbloqueado:** la corrida en vivo de matriz contra bbsa ya no aborta. Lo que verifica este plan es el gate; la corrida real es de los planes siguientes.
- **Pendiente explícito para 39-07:** el finding terminal `EXPECTED` anterior de matriz (`prod-vs-remarkets divergence acknowledged`) queda **superseded** en `.planning/verification/matriz-client-findings.md`. Como el dedupe es `idempotent_by_title=True`, el título nuevo (`prod-vs-sandbox divergence acknowledged`) crea un finding NUEVO en la primera corrida en vivo: el viejo debe recibir disposición explícita en 39-07, **no** borrarse.
- **Sin cambios en:** `verification/mutation_gate.py` (order entry sigue fail-closed bajo bbsa por hostname exacto remarkets-only) y `main_verify.py`.
- **Deuda ajena confirmada, no tocada:** `verification/test_cycle_closure_phase33.py` falla en 2 casos por causas pre-existentes (backlog `HARN-VERIF-01`).

## Self-Check: PASSED

Los 7 archivos declarados existen en disco y los 2 hashes de commit de tarea (`b659084`, `cd2b4c0`) existen en el historial.

---
*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo*
*Completed: 2026-08-29*
