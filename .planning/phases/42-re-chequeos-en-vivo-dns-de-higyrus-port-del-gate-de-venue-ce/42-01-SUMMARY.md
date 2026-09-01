---
phase: 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce
plan: 01
subsystem: testing
tags: [security, hostname-allowlist, ast-guard, pytest, ci, verification-harness, matriz]

# Dependency graph
requires:
  - phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
    provides: "`main_matriz._VENUE_ALLOWLIST` + `_venue_token` (igualdad exacta de hostname, D-02), `verification/mutation_gate.py` con `_SANDBOX_HOST` remarkets-only (T-39-02), y la autorización de operador de `api.bbsa.matrizoms.com.ar` como sandbox no-producción (2026-08-29)"
  - phase: 33-live-typ-01
    provides: "`scripts/literal_census_33.py` (censo `Literal`) con el gate de venue en substring-match pre-Phase-39"
provides:
  - "Gate de venue del censo portado a igualdad exacta de hostname por IMPORT de la fuente única de `main_matriz.py` (D-01) — divergencia entre sitios estructuralmente imposible, no sólo detectada"
  - "`verification/test_literal_census_venue_gate.py`: 21 tests (13 casos de spoofing parametrizados, aserción AST anti-substring restringida a `census_matriz`, controles positivos de no-vacuidad, pin del gate de mutación)"
  - "Enrolamiento del lock en la allowlist explícita de `.github/workflows/ci.yml` (12 → 13 rutas) — sin esta línea el lock sería INERTE (WR-01)"
  - "`CENSUS-HEADER venue=… captured_at=… allowlist_size=…` + `CENSUS-DLOCK` emitidos antes de la primera request (criterio 3, gap de Pitfall 5)"
  - "Flag `--matriz-only` con retorno temprano (D-04) — corre sólo `census_matriz()`, sin disparar `census_iol()`"
  - "Aprobación humana explícita del operador, transcrita verbatim, que gatea el tráfico en vivo de 42-02/42-03/42-04"
affects: [42-02, 42-03, 42-04, 42-05, 42-06, 43-shape-01, 45-harn]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Política de seguridad compartida por import, pinneada por identidad de objeto (`is`) en vez de igualdad de contenido (`==`)"
    - "Aserción AST anti-substring restringida al `FunctionDef` sujeto, con control positivo del walker sobre snippet sintético"
    - "Header de procedencia (venue + timestamp UTC + conteo de allowlist) emitido antes de la primera request, con el venue derivado del gate y nunca hardcodeado"

key-files:
  created:
    - verification/test_literal_census_venue_gate.py
  modified:
    - scripts/literal_census_33.py
    - .github/workflows/ci.yml

key-decisions:
  - "Q4 cerrada en planificación, no en ejecución: el walk anti-substring se restringe al `FunctionDef` de `census_matriz`, NO al módulo entero — recorrer el módulo produce falsos positivos sobre el despacho de flags de `main()` (incluido el `--matriz-only` que esta misma fase agrega), y descubrirlo corriendo el test invita al reflejo de relajar la aserción"
  - "El gate se porta por `from main_matriz import _VENUE_ALLOWLIST, _venue_token` (no `import main_matriz` con uso calificado) precisamente para habilitar el pin de identidad `is` del lock"
  - "La posición del gate NO se movió: sigue después de `Client()` (que no hace IO) y ANTES de `login()` y de toda request — un host fuera del allowlist no cuesta ni un round trip"
  - "`allowlist_size` en el header es un CONTEO, nunca un hostname resuelto (T-42-04), y hace que el import de `_VENUE_ALLOWLIST` sea genuinamente usado en vez de un `# noqa: F401`"
  - "`--matriz-only` usa retorno temprano para no caer en `return 0 if (ran_matriz and ran_iol) else 1`, que daría exit 1 en una corrida exitosa con `ran_iol=False`"

patterns-established:
  - "Fuente única de política de venue por import: cualquier consumidor nuevo del allowlist importa de `main_matriz.py` y se pinnea por `is`, nunca re-declara la política"
  - "Todo guard nuevo bajo `verification/` se agrega a mano a la allowlist explícita del step 'driver locks' de `ci.yml` en el mismo commit que lo crea, y se prueba con `grep -c ... = 1`"

requirements-completed: [LIVE-02]

# Metrics
duration: 11min
completed: 2026-08-31
status: complete
---

# Phase 42 Plan 01: Port del gate de venue del censo `Literal` Summary

**`scripts/literal_census_33.py` deja el substring-match `if "remarkets" not in base:` y pasa a decidir el venue por igualdad exacta de hostname contra el MISMO objeto que publica `main_matriz.py`, pinneado por identidad (`is`) y por 13 casos de spoofing en un lock enrolado en CI, más el header `CENSUS-HEADER`/`CENSUS-DLOCK` antes de la primera request y el flag `--matriz-only`.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-08-31T20:56:14Z
- **Completed:** 2026-08-31T21:07:44Z
- **Tasks:** 3 (2 de código TDD + 1 checkpoint humano bloqueante)
- **Files modified:** 3 (1 creado, 2 modificados)

## Accomplishments

- **T-42-01 mitigado.** El gate de venue del censo era un substring-match pre-Phase-39 que habría hecho saltear el script **en silencio** contra el sandbox `bbsa` ya desbloqueado. Ahora importa `_venue_token` y `_VENUE_ALLOWLIST` de `main_matriz.py`: no re-declara ninguna política, no hay `in`, no hay `endswith`, no hay regex de hostname nuevo.
- **Falsificación real, no cobertura decorativa.** Los 13 casos parametrizados incluyen el sufijo hostil (`api.bbsa.matrizoms.com.ar.attacker.example` → `None`), la variante userinfo (`https://api.bbsa.matrizoms.com.ar@attacker.example` → `None`), producción (`api.primary.com.ar` → `None`), fail-closed ante cadena vacía y ante base URL imparseable (`https://[oops/api` → `None`, T-42-05: `ValueError` capturado, nunca crash).
- **T-42-06 mitigado (el lock no es inerte).** La ruta quedó en la allowlist explícita de `.github/workflows/ci.yml` (12 → 13 rutas). `verification/` nunca corre entero en CI porque el job `test` pasa rutas explícitas que pisan `testpaths`; sin esa línea el lock estaría verde en local y muerto en CI.
- **T-42-07 mitigado (el lock no puede ser vacuo).** `_census_matriz_node()` levanta `AssertionError` si no encuentra `census_matriz`; `_membership_offenders()` tiene control positivo sobre un snippet sintético que SÍ contiene la forma prohibida; el gate de mutación tiene control positivo bajo remarkets.
- **Criterio 3 cubierto (gap que sólo el research encontró).** `_report()` no emitía ningún encabezado, así que un plan derivado sólo de CONTEXT.md habría fallado el criterio por una razón puramente mecánica. Ahora `_census_header(venue)` emite `CENSUS-HEADER venue=… captured_at=<UTC ISO> allowlist_size=2` y `CENSUS-DLOCK`, con el `venue` derivado de `_venue_token(base)` y nunca hardcodeado — el header no puede mentir sobre contra qué venue se midió.
- **T-42-02 mitigado.** `verification/mutation_gate.py` quedó **byte-idéntico**: el widening es del gate de LECTURA del censo, jamás del de mutación. El order entry sigue fail-closed bajo `bbsa` **sin cambio de código**.
- **T-42-03 mitigado.** El checkpoint se escribió `gate="blocking-human"` (nunca `gate="blocking"` a secas, forma que ya se auto-aprobó dos veces en este proyecto) y la aprobación se recogió explícitamente en sesión.

## Task Commits

Cada task se committeó atómicamente:

1. **Task 1: Lock de falsificación del gate de venue + enrolamiento en CI (RED)** — `7cc103a` (test)
   `verification/test_literal_census_venue_gate.py` (+272), `.github/workflows/ci.yml` (+3/−1)
2. **Task 2: Port del gate por import + header venue/timestamp + `--matriz-only` (GREEN)** — `99fb17c` (feat)
   `scripts/literal_census_33.py` (+91/−10) — un solo archivo, como exigía el criterio de aceptación
3. **Task 3: Checkpoint bloqueante — fidelidad del port y habilitación del tráfico en vivo (D-02)** — sin commit (checkpoint humano, `<files>` vacío por diseño)

**Plan metadata:** ver commit `docs(42-01)` que acompaña a este SUMMARY.

_Gates TDD verificados: `test(...)` (RED, `7cc103a`) precede a `feat(...)` (GREEN, `99fb17c`). Sin fase REFACTOR — no hizo falta._

## Checkpoint humano — respuesta del operador (transcripción verbatim)

El checkpoint `checkpoint:human-verify` con `gate="blocking-human"` de la Task 3 se presentó al operador **antes de que saliera cualquier llamada de red de la fase**, con el diff completo de las Tasks 1 y 2 y los seis puntos del `<how-to-verify>`.

Respuesta del operador, transcrita verbatim:

```
Approved
```

**Procedencia de la aprobación (exigido por `<acceptance_criteria>` y por T-42-03):** la respuesta fue dada explícitamente por el operador en esta sesión, en respuesta a este checkpoint. **NO** se derivó de `workflow.auto_advance: true`, **NO** se derivó de `mode: yolo`, y **NO** se derivó de `workflow.human_verify_mode: "end-of-phase"` — ese modo no aplica acá porque el criterio 1 del ROADMAP exige que la autorización ocurra *antes de que salga tráfico*, y una verificación de fin de fase no puede gatear tráfico que ya ocurrió.

**Consecuencia:** los planes 42-02, 42-03 y 42-04 quedan habilitados para emitir tráfico en vivo dentro del alcance declarado en el punto 5 del `<how-to-verify>` — (a) `main_higyrus.py` completo contra higyrus, (b) `scripts/literal_census_33.py --matriz-only` contra `bbsa` (cinco endpoints de LECTURA, cero órdenes, cero mutaciones; D-10 / P-05 vigentes), (c) `main_market_data.py` completo. `census_iol()` **no** corre (D-04).

**Riesgo residual A1, declarado y aceptado:** la seguridad y el carácter no-producción del sandbox `api.bbsa.matrizoms.com.ar` son una **aserción del operador**, no verificable por máquina. Es la mayor dependencia de confianza de esta fase.

En el momento del checkpoint, `git status --porcelain` no mostraba cambios en `verification/mutation_gate.py` (única entrada: ` M .planning/STATE.md`, marcadores de ejecución del orquestador).

## Verificación del plan — resultados medidos

| # | Chequeo | Resultado |
|---|---------|-----------|
| 1 | `uv run --frozen ruff check .` | `All checks passed!` |
| 2 | `uv run --frozen ruff format --check .` | `279 files already formatted` |
| 3 | `uv run --frozen mypy` | `Success: no issues found in 75 source files` |
| 4 | `uv run pytest -q` sobre las **13** rutas de la allowlist de `ci.yml` | **`150 passed`, 0 failed** |
| 5 | `uv run python scripts/literal_census_33.py --selftest` | `SELFTEST: PASS`, exit `0` |
| 6 | `git hash-object verification/mutation_gate.py` | `6bdaec006cc16f7c8dbfac41701712a9085c691b` |
| 7 | Respuesta del operador transcrita verbatim | Sí — sección de arriba |
| 8 | Llamadas de red durante este plan | **Cero** |

### Conteo `passed` vs baseline (exigido por `<output>`)

- **Baseline medido en HEAD (12 rutas):** `129 passed`
- **Medido al cierre (13 rutas):** **`150 passed`, `0 failed`**
- **Delta:** **+21**, estrictamente mayor que el baseline — se cumple el criterio de aceptación de la Task 2. Los 21 tests nuevos son exactamente el contenido de `verification/test_literal_census_venue_gate.py`: los 11 tests declarados en el plan, donde `test_venue_token_resolves_by_exact_hostname` expande a los 13 casos parametrizados (10 tests no parametrizados + 13 casos − 2 = 21 nodos ejecutados).

### `git hash-object` de `verification/mutation_gate.py` medido al cierre (exigido por `<output>`)

```
6bdaec006cc16f7c8dbfac41701712a9085c691b
```

Idéntico al valor pinneado en el `<verify>` de las tres tasks y en T-42-02. El archivo **no se modificó en ninguna task de la fase**, que es exactamente lo que el criterio 4 exige: el gate de mutación mantiene el order entry fail-closed bajo `bbsa` sin cambio de código.

## Files Created/Modified

- `verification/test_literal_census_venue_gate.py` *(creado, 272 líneas)* — Lock de falsificación del gate de venue del censo. Cinco capas: identidad de fuente única (`census._venue_token is main_matriz._venue_token`, `census._VENUE_ALLOWLIST is main_matriz._VENUE_ALLOWLIST`), allowlist de exactamente dos hosts, 13 casos de resolución exacta de hostname, aserción AST anti-substring restringida a `census_matriz` con su control positivo, orden header-antes-de-request, contenido del header, y el pin del gate de mutación con control positivo. Importa `scripts.literal_census_33 as census` como namespace package gracias a `pythonpath = ["."]` — sin hacks de `sys.path` y sin ningún `# noqa`.
- `scripts/literal_census_33.py` *(modificado, +91/−10)* — `from main_matriz import _VENUE_ALLOWLIST, _venue_token  # noqa: E402` (línea 90, después del bloque `sys.path.insert`); `import datetime as dt`; gate portado a `venue = _venue_token(base)` / `if venue is None:` en la misma posición pre-login (línea 234); `_census_header_lines()` / `_census_header()` (líneas 189-208) llamado en la línea 248, antes del `try:` de las requests; despacho `--matriz-only` con retorno temprano (línea 428); `_selftest()` extendido con cobertura offline del criterio 3 y del criterio 1; docstring de módulo actualizado.
- `.github/workflows/ci.yml` *(modificado, +3/−1)* — la ruta del lock nuevo agregada a la allowlist explícita del step "driver locks" del job `lint`, con la misma indentación de 12 espacios que las 12 rutas existentes.

## Decisions Made

Ninguna decisión nueva durante la ejecución — el plan cerró por adelantado la única decisión abierta que existía (Q4: alcance del walk AST), precisamente para que no se tomara bajo la presión de un test rojo. Las decisiones que el plan traía se aplicaron sin modificación:

- El walk anti-substring quedó restringido al `FunctionDef` de `census_matriz`. Esto resultó necesario en la práctica: la Task 2 agregó un segundo despacho de flags (`if "--matriz-only" in argv:`) de la misma forma sintáctica que el `--selftest` preexistente, así que un walk a nivel de módulo habría producido dos falsos positivos.
- El gate no se movió de posición. El docstring de `census_matriz` lo declara: *"un SKIP no debe costar ni un round trip contra un host fuera de política"*.
- La razón del `_skip` nombra el allowlist sin interpolar hostname ni base URL (T-39-04 / C-4 / T-42-04).

## Deviations from Plan

None — plan executed exactly as written. Cero deviaciones bajo las Reglas 1-3, cero escalaciones bajo la Regla 4.

**Total deviations:** 0
**Impact on plan:** Ninguno. Las tres tasks corrieron con la forma exacta que el plan especificaba, incluidos los conteos de archivos por task (Task 1: 2 archivos; Task 2: **un solo** archivo, como pedía el criterio de aceptación; Task 3: cero).

## Issues Encountered

Ninguno.

Nota de continuación: este plan se completó en dos tramos de agente. Las Tasks 1 y 2 corrieron en un tramo, el checkpoint bloqueante de la Task 3 detuvo la ejecución (comportamiento correcto y esperado para `gate="blocking-human"`), y un agente fresco retomó tras la aprobación del operador. El `<verify>` automatizado de la Task 3 se re-corrió al retomar para confirmar que nada había derivado durante la espera: hash del gate de mutación intacto, import de la política presente, 21 tests verdes.

## Known Stubs

Ninguno. No hay valores hardcodeados vacíos, texto placeholder ni componentes sin fuente de datos en los archivos de este plan.

## Threat Flags

Ninguno. Los archivos tocados no introducen superficie de seguridad fuera del `<threat_model>` del plan: no hay endpoints de red nuevos, ni rutas de auth nuevas, ni patrones de acceso a archivos nuevos, ni cambios de schema en fronteras de confianza. El único cruce de red que este plan habilita —y no ejecuta— está declarado en T-42-03 y gateado por la aprobación humana transcrita arriba.

## User Setup Required

None — no external service configuration required. La autorización del sandbox `api.bbsa.matrizoms.com.ar` ya existía a nivel de sistema desde Phase 39 D-02 (2026-08-29); este plan sólo confirmó la **fidelidad del port**, no re-autorizó el host desde cero.

## Next Phase Readiness

**Listo para 42-02 / 42-03 / 42-04.** El tráfico en vivo está habilitado por la aprobación explícita del operador registrada arriba. Lo que estos planes reciben:

- `scripts/literal_census_33.py --matriz-only` corre contra `bbsa` sin saltear en silencio, emitiendo header de procedencia verificable, y devuelve exit `0` en corrida exitosa / `1` si queda SKIPPED.
- El veredicto de higyrus debe ser **medido** (resuelto o `SKIPPED` con causa re-confirmada), nunca cero — precedente D-13 / 33-05.
- 42-04 produce la lectura fresca del wire (`wire-instruments-42` / `wire-segments-42`) que consume la Phase 43 para la tabla de disposición campo-por-campo de SHAPE-01.

**Vigilar:** el header emite `allowlist_size=2`. Si un plan futuro amplía el allowlist, ese conteo cambia y el lock lo detecta (`test_venue_allowlist_has_exactly_the_two_known_hosts`) — la ampliación es una decisión humana explícita, no un efecto lateral. Y el widening del gate de LECTURA nunca arrastra al de mutación: `verification/mutation_gate.py` debe seguir en `6bdaec00…` al cierre de la fase (gate del plan 42-06).

## Self-Check: PASSED

- `verification/test_literal_census_venue_gate.py` — FOUND
- `scripts/literal_census_33.py` — FOUND
- `.github/workflows/ci.yml` — FOUND
- Commit `7cc103a` — FOUND en `git log`
- Commit `99fb17c` — FOUND en `git log`

---
*Phase: 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce*
*Completed: 2026-08-31*
