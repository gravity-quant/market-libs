---
phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
plan: 02
subsystem: testing
tags: [harness, dedupe, drift, findings, tdd, market-data-client, fid]

# Dependency graph
requires:
  - phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
    plan: 01
    provides: "`main_market_data.py` ya tocado y verde (fix de `DRV-MD-SEG-43`), de modo que el diff de este plan sobre ese archivo es puro dedupe"
  - phase: 33-divergence-handler
    provides: "`verification/test_finding_count_consistency.py` (P-3) — el invariante de fids que D-03 no puede relajar, y el modelo de aislamiento por `monkeypatch(_FINDINGS_DIR)` que este test copia"
  - phase: 11-harness-findings
    provides: "`verification/findings.py::append_finding` — la primitiva de escritura cuyo orden interno (scan por título ARRIBA de la guarda de status humano) descalifica `idempotent_by_title` para la rama drift"
provides:
  - "`main_market_data._seen_drift_keys` + `_drift_digest()`: guarda de dedupe intra-proceso con clave `(client_function, digest)` consultada ANTES de `_next_fid()`"
  - "`verification/test_drift_dedupe_falsification.py`: los 3 arms de runtime de D-04 (colapso, NO-colapso, fid-no-quemado) sobre el driver real, con su no-vacuidad demostrada"
  - "El patrón de referencia para los 6 sitios de drift restantes de D-02 (planes 45-03/45-04), incluida la diferencia de forma del no-op (`return` desnudo vs. tupla vs. `ProbeResult`)"
affects: [45-03, 45-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guarda de dedupe intra-proceso con clave `(identidad, digest-de-contenido)`: estado module-level junto al allocator de fids, consultada antes de consumir el fid"
    - "Digest de divergencia sobre el PAR expected/actual (no sólo actual), con `default=str` para que el camino de dedupe no pueda levantar dentro de la ladder D-09"
    - "Test de dedupe con arm de falsificación obligatorio: el arm de NO-colapso convierte al de colapso en una aserción de dedupe en vez de una de supresión"
    - "RED autoexplicativo: `assert hasattr(driver, '<artefacto>')` en la fixture, sin `raising=False`, para que el rojo diga qué falta en vez de estallar con un `AttributeError` pelado"

key-files:
  created:
    - verification/test_drift_dedupe_falsification.py
  modified:
    - main_market_data.py

key-decisions:
  - "La clave NO incluye `surface` (D-01 ENMENDADA): incluirla colapsaría 0 bloques, porque dentro de un proceso cada par función-superficie se visita una sola vez"
  - "El digest cubre el PAR `[committed_schema, actual_schema]`, no sólo el actual: dos drifts con el mismo `actual` pero distinto `expected` son findings distintos y no pueden colapsarse"
  - "No se usó `idempotent_by_title=True`: su scan corre arriba de la guarda de status humano (`findings.py:664-670`) y colapsaría un drift nuevo contra bloques `EXPECTED`/`NO-FIX` ya triageados"
  - "La rama `except (OSError, json.JSONDecodeError)` (baseline ilegible) NO recibe guarda: su título es otro y su hazard también"
  - "`.planning/config.json` apareció modificado por el harness durante la corrida (`_auto_chain_active`); NO se stageó — está fuera del alcance de ambas tareas"

patterns-established:
  - "Demostración de no-vacuidad como criterio de aceptación: invertir temporalmente el orden que el test protege, pegar el rojo, restaurar, y verificar por `grep` que la reversión no quedó en el árbol"

requirements-completed: []  # HARN-01 queda PARCIAL — 1 de 7 sitios de D-02
requirements-partial:
  - "HARN-01 — el mecanismo y su test de falsificación están entregados sobre el único sitio que puede duplicar in-process; los 6 sitios restantes de D-02 (iol ×3, higyrus, matriz, ámbito) pertenecen al plan 45-03"

# Metrics
duration: 3min
completed: 2026-09-01
status: complete
---

# Phase 45 Plan 02: Dedupe intra-proceso de schema drift (HARN-01, TDD) Summary

**El driver de market-data deja de escribir dos bloques `### F-` por una sola divergencia de schema —sync y async colapsan bajo la clave `(func, digest)`— sin poder tragarse una divergencia distinta sobre el mismo endpoint y sin quemar un fid en el no-op, con las tres propiedades pineadas por un test de falsificación cuya no-vacuidad está demostrada.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-09-01T15:30:02Z
- **Completed:** 2026-09-01T15:33:31Z
- **Tasks:** 2 (RED + GREEN)
- **Files created:** 1 · **Files modified:** 1

## Accomplishments

- **El arm de falsificación existe y es el que manda.** `verification/test_drift_dedupe_falsification.py` no prueba sólo que la repetición colapsa: prueba que una divergencia **distinta** sobre el **mismo** endpoint sigue escribiendo un bloque nuevo. Sin ese segundo arm, un `return` incondicional en el sitio de drift pasaría el primero con honores mientras se traga toda divergencia posterior — que es literalmente el modelo de amenaza del proyecto.
- **La guarda decide antes de consumir el fid.** `_next_fid()` se llama después de la pertenencia en `_seen_drift_keys`, así que un bloque no escrito tampoco gasta un número. El arm `fid_not_burned` lo pinea, y se demostró que lo detecta invirtiendo el orden a propósito.
- **La clave es la ENMENDADA, no la literal.** `(client_function, digest)` sin `surface`, sobre el PAR `expected`/`actual`. La clave original de D-01 (con superficie) habría colapsado exactamente cero bloques.

## Mediciones pedidas por el `<output>` del plan

### 1. Salida RED de la Task 1 (antes de que `_seen_drift_keys` existiera) — exit 1

```
        monkeypatch.setattr(main_market_data, "_fid_counter", 0)
>       assert hasattr(main_market_data, "_seen_drift_keys"), (
            "main_market_data no expone `_seen_drift_keys`: la guarda de dedupe "
            "intra-proceso de HARN-01 (D-01 ENMENDADA) todavía no existe en el "
            "driver. Es el artefacto que la Task 2 de 45-02 entrega; hasta entonces "
            "este archivo está RED por diseño."
        )
E       AssertionError: main_market_data no expone `_seen_drift_keys`: la guarda de dedupe intra-proceso de HARN-01 (D-01 ENMENDADA) todavía no existe en el driver. Es el artefacto que la Task 2 de 45-02 entrega; hasta entonces este archivo está RED por diseño.
E       assert False
E        +  where False = hasattr(main_market_data, '_seen_drift_keys')

verification/test_drift_dedupe_falsification.py:122: AssertionError
=========================== short test summary info ============================
ERROR verification/test_drift_dedupe_falsification.py::test_same_drift_on_both_surfaces_collapses_to_one_block
ERROR verification/test_drift_dedupe_falsification.py::test_distinct_drift_on_same_endpoint_does_not_collapse
ERROR verification/test_drift_dedupe_falsification.py::test_dedupe_no_op_leaves_the_fid_not_burned
3 errors in 0.04s
```

El rojo dice **qué falta**, no `AttributeError`. Los 3 tests se recogían correctamente en ese mismo estado (`--collect-only -q` → `3 tests collected in 0.04s`).

### 2. Salida GREEN de la Task 2

```
...                                                                      [100%]
3 passed in 0.04s
```

Y las primitivas vecinas, en la misma corrida (`test_drift_dedupe_falsification` + `test_finding_count_consistency` + `test_findings_dedupe_by_title` + `test_findings_fid_seed`):

```
........................                                                 [100%]
24 passed in 0.07s
```

`git diff --quiet HEAD -- verification/test_finding_count_consistency.py` → **exit 0**: el invariante P-3 sigue verde y **sin un solo carácter editado** (criterio 2 del ROADMAP / criterio de éxito 4 del plan).

### 3. Demostración de no-vacuidad del arm `fid_not_burned` (orden invertido) — ROJO

Con `fid = _next_fid()` movido temporalmente ARRIBA de la guarda:

```
>       assert main_market_data._fid_counter == 1, (
            f"`_fid_counter` quedó en {main_market_data._fid_counter} tras un solo "
            ...
        )
E       AssertionError: `_fid_counter` quedó en 2 tras un solo bloque escrito: el no-op del dedupe quemó un fid. D-03 exige que `_next_fid()` se llame DESPUÉS de la decisión de dedupe — si no, el driver reporta en su SUMMARY un censo mayor que el que escribió, que es exactamente la pérdida silenciosa que P-3 pinea para el allocator sin seedear.
E       assert 2 == 1
E        +  where 2 = main_market_data._fid_counter

=========================== short test summary info ============================
FAILED verification/test_drift_dedupe_falsification.py::test_dedupe_no_op_leaves_the_fid_not_burned
1 failed, 2 deselected in 0.04s
```

`2 == 1` es la lectura exacta del hazard: **un** bloque escrito, **dos** fids consumidos. Nótese que con el orden invertido los arms (a) y (b) **seguían pasando** — el conteo de bloques no se mueve — que es precisamente por qué D-03 necesitaba su propio arm y por qué P-3 no puede cubrirlo (property test con allocator local, no importa ningún driver; `45-RESEARCH.md` Pitfall B).

Tras restaurar el orden: `grep -c 'TEMPORAL' main_market_data.py` → **0** (la reversión no quedó en el árbol), y los 3 arms vuelven a verde (ver §2).

### 4. Los dos números de línea (guarda vs. `_next_fid()`)

`grep -n` sobre `main_market_data.py` en HEAD post-GREEN:

| Sitio | Línea |
|---|---|
| `if drift_key in _seen_drift_keys:` (guarda de pertenencia) | **544** |
| `fid = _next_fid()` del sitio de drift | **549** |

544 < 549 — el fid se asigna **después** de la decisión (D-03).

### 5. Gates

```
uv run mypy main_market_data.py       → Success: no issues found in 1 source file   (exit 0)
uv run ruff check .                   → All checks passed!
uv run ruff format --check .          → 280 files already formatted
git status --porcelain .planning/verification/   → (vacío)
```

## Task Commits

Cada tarea se commiteó atómicamente, respetando la secuencia de gates TDD:

1. **Task 1 (RED): test de falsificación de D-04** — `bda2bec` (`test(45-02): add failing falsification test for drift dedupe (D-04)`)
2. **Task 2 (GREEN): guarda `_seen_drift_keys` + `_drift_digest`** — `e3ab4e5` (`feat(45-02): dedupe intra-proceso de schema drift en main_market_data (HARN-01)`)

No hubo fase REFACTOR: la implementación GREEN son 38 líneas añadidas (0 borradas), sin duplicación que limpiar.

## Files Created/Modified

- **`verification/test_drift_dedupe_falsification.py` (nuevo, 216 líneas).** Docstring de módulo que nombra los DOS escenarios con la misma explicitud (`grep -c 'no debe colapsar'` → 1), declara el aislamiento por `monkeypatch(verification.findings._FINDINGS_DIR)` y declara que el archivo corre desde la lista explícita del job `lint` (lo enrola el plan 45-05). Una fixture de aislamiento compartida por los 3 arms: patchea `_FINDINGS_DIR`, patchea el `_SCHEMA_DIR` del driver, escribe un baseline `get-health.json` cuyo `"schema"` es `schema_of(_BASELINE_PAYLOAD)` y **difiere** de los tres payloads de test (si no, el helper saldría por la rama "sin drift" y los arms medirían otra cosa), y resetea `_fid_counter`/`_seen_drift_keys`.
- **`main_market_data.py` (+38 / −0).** `import hashlib` en el bloque stdlib (entre `datetime as dt` y `json`, donde lo ubica ruff `I`); `_seen_drift_keys` y `_drift_digest()` junto a `_fid_counter`; y 7 líneas en el sitio de drift entre el `return` de "sin drift" y `fid = _next_fid()`.

**Lo que deliberadamente NO se tocó:** el `title=f"schema drift en {client_function}"` (el round-trip del parser de `findings.py` y la invariante CR-02 de título single-line quedan intactos), la firma de `append_finding` (ningún kwarg nuevo), y la rama `except (OSError, json.JSONDecodeError)` de baseline ilegible.

## Decisions Made

- **`(func, digest)` sin `surface`.** Es D-01 ENMENDADA, y la razón está pegada en el comentario del propio `_seen_drift_keys`: dentro de un proceso cada par función-superficie se visita una sola vez, así que una clave con superficie no puede colapsar nada. Es también lo que hace que el arm (a) tenga sujeto: sync y async comparan contra el MISMO baseline y producen el MISMO schema.
- **El digest cubre el par `[expected, actual]`.** Dos drifts con el mismo `actual` pero distinto `expected` son findings distintos. Un digest sólo sobre `actual` los habría colapsado — una pérdida de censo silenciosa del mismo tipo que la fase existe para eliminar.
- **`default=str` en el `json.dumps` del digest.** No es defensivo por costumbre: el sitio de drift vive dentro del contrato de la ladder D-09 ("una divergencia de forma degrada a finding, jamás a crash"). Un `TypeError` de serialización en la clave de dedupe rompería un camino que hoy no levanta (T-45-07).
- **`idempotent_by_title=True` descartado, con la mecánica medida.** El scan por título de `append_finding` corre ARRIBA de la guarda de status humano (`findings.py:664-670`), así que bajo `schema drift en get_market_data` —donde conviven F-37 `EXPECTED`, F-74 `NO-FIX` y F-203 `OPEN`— un drift nuevo haría no-op contra el bloque terminal y desaparecería de la cola OPEN.
- **El `.planning/config.json` modificado por el harness no se stageó.** Es un flag de orquestación (`_auto_chain_active`), ajeno a ambas tareas; incluirlo en un commit de código habría mezclado alcance.

## Deviations from Plan

None — plan executed exactly as written. Sin auto-fixes bajo Rules 1-3; sin instalación de paquetes (consistente con `T-45-SC`: la fase no instala nada).

## TDD Gate Compliance

Secuencia de gates verificada en `git log`:

1. **RED** — `bda2bec` `test(45-02): ...` con el archivo de test en estado rojo (3 errors, exit 1) y el motivo del rojo pegado arriba.
2. **GREEN** — `e3ab4e5` `feat(45-02): ...` posterior al RED, con los 3 arms en verde.
3. **REFACTOR** — no aplicó (ver § Task Commits).

Ningún test pasó inesperadamente durante RED: los 3 arms fallaron por la ausencia del artefacto, con el mensaje que la fixture provee.

## Verificación de las amenazas del `<threat_model>`

| Threat ID | Mitigación entregada | Evidencia |
|---|---|---|
| T-45-05 (divergencia real tragada) | arm `does_not_collapse` | verde, y su assert exige exactamente 2 bloques |
| T-45-06 (fid quemado / censo inflado) | arm `fid_not_burned` + guarda antes de `_next_fid()` | líneas 544 < 549, y el rojo `assert 2 == 1` con el orden invertido |
| T-45-07 (DoS del run por serialización) | `json.dumps(..., default=str)` en `_drift_digest` | ningún tipo no serializable puede levantar en ese camino |
| T-45-08 (tampering del ledger committeado) | `monkeypatch(_FINDINGS_DIR)` + `_SCHEMA_DIR` a `tmp_path` | `git status --porcelain .planning/verification/` vacío tras cada corrida |
| T-45-09 / T-45-SC | accept (sin cambios) | ni el título ni `expected`/`actual` cambian; sin dependencias nuevas (`hashlib`/`json` son stdlib) |

## Issues Encountered

Ninguno. La única fricción esperable —que la fixture escribiera en los findings committeados— quedó cerrada por diseño con los dos `monkeypatch`, y el gate de `git status` lo confirma en cada corrida.

## Requirements

**`HARN-01` queda PARCIAL — su checkbox en `REQUIREMENTS.md` se deja abierto deliberadamente.** Este plan entrega el mecanismo, su test de falsificación y el reordenamiento del fid sobre **1 de los 7 sitios de D-02** — el único que puede duplicar dentro de un mismo proceso y por lo tanto el único donde los arms de runtime tienen sujeto real. Los 6 restantes (`main_iol.py` ×3, `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py`) pertenecen al plan 45-03, y su no-op tiene **forma distinta**: tres devuelven `tuple[str, str]`, uno devuelve `ProbeResult` y dos son inline en un bucle acumulando `finding_fids` (donde el no-op es `continue` sin `append`). Marcar el requisito completo acá afirmaría en el ledger justo el tipo de estado escrito que el código todavía no respalda.

## User Setup Required

None — no external service configuration required. Este plan no corre drivers en vivo ni lee ningún `.env`; todo el ejercicio es contra `tmp_path`.

## Next Phase Readiness

- **45-03 tiene el patrón de referencia y la advertencia de forma.** El bloque de 7 líneas de `main_market_data.py:540-549` es el molde; lo que NO se puede copiar literal es el `return` desnudo (ver § Requirements).
- **45-05 tiene un archivo más para el allowlist consolidado de `ci.yml` (D-11):** `verification/test_drift_dedupe_falsification.py`, ya verde standalone. El docstring del archivo ya declara ese enrolamiento como pendiente de ese plan.
- **Sin bloqueos.** `uv run ruff check . && uv run ruff format --check .` limpio sobre 280 archivos; `uv run mypy main_market_data.py` limpio; `git status --porcelain .planning/verification/` vacío.

## Self-Check: PASSED

- `verification/test_drift_dedupe_falsification.py` — FOUND (creado, 3 arms verdes)
- `main_market_data.py` — FOUND (modificado, mypy limpio)
- `.planning/phases/45-.../45-02-SUMMARY.md` — FOUND (este archivo)
- Commit `bda2bec` — FOUND (RED)
- Commit `e3ab4e5` — FOUND (GREEN)

---
*Phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti*
*Completed: 2026-09-01*
