---
phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
plan: 04
subsystem: harness-verification
tags: [harn-04, deuda-documentada, matriz, ast-lock, ci-allowlist, decision-artifact]
requires:
  - "45-RESEARCH.md Hallazgos 7-11 (evidencia medida por archivo)"
  - "45-CONTEXT.md D-08 / D-08 ENMENDADA / D-10 / D-11 (locks de decisión)"
provides:
  - "45-HARN-04-DECISION.md — decisión escrita y fechada de HARN-04 (criterio 3 del ROADMAP)"
  - "test_login_sync_probe_returns_finding_never_fail — guardián de la taxonomía CR-02 dentro de un archivo ya enrolado en CI"
  - "Punteros in-code al documento de decisión en los 2 archivos aceptados como deuda"
affects:
  - "45-05 (edit consolidado de ci.yml): el documento NOMBRA el enrolamiento de test_probe_context_coverage.py y la entrada de backlog v1.9 de Q5 que 45-05 debe aterrizar"
tech-stack:
  added: []
  patterns:
    - "Lock por AST sobre el driver, nunca por substring del fuente (el docstring del test cita el literal prohibido)"
    - "Piso de no-vacuidad + techo de triage en el mismo assert de conteo"
    - "Aceptar deuda documentada sin git rm: archivo en disco + puntero al documento fechado"
key-files:
  created:
    - .planning/phases/45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti/45-HARN-04-DECISION.md
  modified:
    - verification/test_main_matriz_skip_line_shape.py
    - verification/test_matriz_sweep_snapshot.py
    - verification/test_main_matriz_login_fail_uniformity.py
decisions:
  - "HARN-04 se cierra aceptando los 2 archivos de matriz como deuda documentada (no reparar, no borrar); los archivos quedan en disco con puntero al documento fechado"
  - "Q4 se cierra POR IMPLEMENTACIÓN, no por descarte: la única aserción huérfana (probe_login_sync devuelve FINDING, no FAIL) vive ahora en verification/test_main_matriz_skip_line_shape.py, ya enrolado en CI"
  - "Q5 (ningún gate de CI mira los 5 drivers main_*.py de la raíz) se declara con medición pegada y destino backlog v1.9; NO se cierra en esta fase"
  - "El censo re-declarado es 53/13/40 medido hoy, que corrige el 52/12/40 heredado de 41-ROLLUP.md"
metrics:
  duration: ~15 min
  completed: 2026-09-01
  tasks: 2
  commits: 2
  files_touched: 4
status: complete
---

# Phase 45 Plan 04: Cierre escrito de HARN-04 (destino de `verification/` de matriz) Summary

Los 2 archivos de `verification/` de matriz rotos desde la Phase 15 quedan aceptados como deuda
documentada por escrito y fechado, con los tres ítems de D-08 respondidos por archivo sobre
evidencia medida en esta corrida; y la única fila de deuda que la investigación encontró REAL —que
`probe_login_sync` devuelve `FINDING` y no `FAIL`— queda cerrada por un lock AST dentro de un
archivo que ya corría en CI, sin enrolar nada nuevo ni reparar nada.

## Tasks Completed

| Task | Nombre | Commit | Archivos |
|---|---|---|---|
| 1 | Lock de taxonomía de `probe_login_sync` (Q4) | `8f34c40` | `verification/test_main_matriz_skip_line_shape.py` |
| 2 | `45-HARN-04-DECISION.md` fechado + punteros in-code | `4911e93` | `45-HARN-04-DECISION.md`, `verification/test_matriz_sweep_snapshot.py`, `verification/test_main_matriz_login_fail_uniformity.py` |

## Task 1 — conteos antes/después y no-vacuidad

**Conteo de tests en `verification/test_main_matriz_skip_line_shape.py`:**

| | Comando | Salida |
|---|---|---|
| Línea base (antes) | `uv run pytest -q verification/test_main_matriz_skip_line_shape.py` | `19 passed in 0.06s` |
| Después | `uv run pytest -q verification/test_main_matriz_skip_line_shape.py` | `20 passed in 0.08s` |

Subió **exactamente en 1**, como exigía el criterio. El test nuevo es
`test_login_sync_probe_returns_finding_never_fail` (una sola función con las tres aserciones i/ii/iii).

**Docstring de módulo:** leído y confirmado — decía *"Dos capas:"* y ahora dice *"Tres capas:"*, con
el ítem 3 declarando el alcance nuevo (taxonomía de retorno de `probe_login_sync`) y su procedencia
(`45-RESEARCH.md` Hallazgo 9 → cierre de Q4 dentro de un archivo ya enrolado, sin reparar los 2
archivos rotos, cuya disposición apunta a `45-HARN-04-DECISION.md`).

**`grep -c 'login_sync' verification/test_main_matriz_skip_line_shape.py` → `7`** (≥ 1, cumplido).

### Demostración de no-vacuidad (mutación + reversión)

Se mutó el status del handler de `AuthenticationError` en `main_matriz.py:807` **dos veces**, para
aislar dos aserciones distintas del test. Ambas mutaciones fueron revertidas; `git diff main_matriz.py`
quedó **vacío** y `main_matriz.py` **no aparece en ninguno de los 2 commits del plan**.

**Mutación A — `"FINDING"` → `"FAIL"` (dispara la aserción (ii), el conjunto de statuses):**

```
E       AssertionError: main_matriz.py: los statuses de ``ProbeResult('login_sync', ...)`` deben ser
        exactamente ['FINDING', 'PASS']; medidos ['FAIL', 'FINDING', 'PASS']. Un status nuevo (o no
        literal) en este probe es una decisión de taxonomía que merece triage, no un cambio
        silencioso: ``main_verify.py`` clasificaría el probe distinto y la uniformidad que fijó CR-02
        de la Phase 11 se rompería sin que ningún gate lo note.
E       assert {'FAIL', 'FINDING', 'PASS'} == {'FINDING', 'PASS'}
E         Extra items in the left set:
E         'FAIL'
verification/test_main_matriz_skip_line_shape.py:352: AssertionError
FAILED verification/test_main_matriz_skip_line_shape.py::test_login_sync_probe_returns_finding_never_fail
1 failed in 0.05s
```

**Mutación B — `"FINDING"` → `"PASS"` (pasa (ii) y aísla la aserción (iii), la específica de CR-02):**

```
E       AssertionError: main_matriz.py:807: el handler de ``AuthenticationError`` de
        ``probe_login_sync`` devolvió status 'PASS', no ``'FINDING'``. CR-02 de la Phase 11 movió
        este retorno de ``'FAIL'`` a ``'FINDING'`` para uniformar la taxonomía del driver: si vuelve
        atrás, ``main_verify.py`` clasifica este probe distinto del resto de la ruta diagnóstica y la
        regresión no reddea ninguna pata de CI.
E       assert 'PASS' == 'FINDING'
E         - FINDING
E         + PASS
verification/test_main_matriz_skip_line_shape.py:380: AssertionError
FAILED verification/test_main_matriz_skip_line_shape.py::test_login_sync_probe_returns_finding_never_fail
1 failed in 0.05s
```

Tras restaurar: `git diff --stat main_matriz.py` → sin salida; `uv run pytest -q ...` → `20 passed`.

**Nota de gate TDD.** El plan marca la Task 1 como `tdd="true"`. Es un **lock de caracterización**
sobre conducta que ya está presente y correcta en HEAD (`main_matriz.py:807`, con el comentario
`# Phase 11 CR-02` encima) — no hay código de producción que escribir, así que no hay un par
RED→GREEN de commits. La puerta RED se satisface por la demostración de mutación de arriba, que es
exactamente lo que el `<acceptance_criteria>` del plan pide en vez de un RED trivial. De ahí que el
commit sea `test(...)` sin un `feat(...)` que lo siga.

## Task 2 — las tres mediciones pegadas en el documento

Todas medidas en la corrida de este plan, nunca heredadas de un reporte:

| # | Comando | Salida |
|---|---|---|
| M1 | `uv run pytest -q verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py` | `19 failed, 3 passed, 19 errors in 0.13s` |
| M2 | `uv run pytest -q verification/test_probe_context_coverage.py` | `6 passed in 0.09s` |
| M3a | `ls verification/test_*.py \| wc -l` | `53` |
| M3b | conteo del allowlist del job `lint` (`ci.yml:80-93`) | `13` enrolados → **40 inertes** |

M1 reproduce exactamente el `19 failed / 3 passed / 19 errors` que predijo `PITFALLS.md` Pitfall 12.
M3 corrige el `52 / 12 / 40` heredado de `41-ROLLUP.md`; los 40 inertes no se movieron.

**Los 3 tests verdes están nombrados individualmente** en el documento (contados al leer: 3 de 3,
todos en `test_matriz_sweep_snapshot.py`; `test_main_matriz_login_fail_uniformity.py` tiene **cero**):

1. `test_matriz_sweep_snapshot_count_matches_18_minus_cfi_sanity` — auto-referencial
   (`len(_PROBE_FIXTURES) == 17` sobre una tabla del propio archivo); cero cobertura de producción.
2. `test_matriz_envelope_probe_helper_exists` — subsumido por la capa 1 del enrolado
   `test_main_matriz_risk_envelope_keys.py` (`ci.yml:83`), que es estrictamente más fuerte.
3. `test_matriz_risk_probes_unwrap_their_envelope_key` — subsumido por la capa 3 del mismo enrolado,
   y el propio test lo **auto-declara** en su docstring (citado verbatim en el documento).

**Conteo rojo antes vs. después del edit de puntero** (el puntero es sólo docstring; no repara ni
empeora nada):

| | Salida |
|---|---|
| Antes del edit | `19 failed, 3 passed, 19 errors in 0.13s` |
| Después del edit | `19 failed, 3 passed, 19 errors in 0.13s` |

Idéntico (T-45-17 mitigado por medición, no por promesa).

**Greps de aceptación:**

```
test -f .../45-HARN-04-DECISION.md                              → existe (307 líneas, min_lines 60)
grep -c 'test_probe_context_coverage.py' .../45-HARN-04-DECISION.md → 4   (≥ 1)
grep -c '45-05'                          .../45-HARN-04-DECISION.md → 8   (≥ 1)
grep -c '45-HARN-04-DECISION' verification/test_matriz_sweep_snapshot.py            → 1
grep -c '45-HARN-04-DECISION' verification/test_main_matriz_login_fail_uniformity.py → 1
```

Las 6 secciones obligatorias están presentes: (1) Decisión, (2) los tres ítems de D-08 por archivo
+ § 2.3 canario, (3) alcance no reparado, (4) Q5, (5) censo y re-declaración de D-10, (6) los dos
límites de alcance. Más una § 0 de mediciones y una tabla de trazabilidad al final.

## Verificación del plan

| Criterio | Comando | Resultado |
|---|---|---|
| Lock nuevo verde, +1 sobre la base | `uv run pytest -q verification/test_main_matriz_skip_line_shape.py` | `20 passed` (base 19) |
| Precondición del enrolamiento de 45-05 | `uv run pytest -q verification/test_probe_context_coverage.py` | `6 passed` |
| Lint repo-wide | `uv run ruff check . && uv run ruff format --check .` | `All checks passed!` / `279 files already formatted` |
| Documento fechado con evidencia pegada | lectura | header `**Fecha:** 2026-09-01`, comando + salida en § 0 y § 4 |

## Deviations from Plan

Ninguna de las Reglas 1-4 se activó. Dos precisiones de ejecución, ambas dentro de la discreción que
el plan concede y ninguna que cambie alcance:

**1. Dos mutaciones de no-vacuidad en vez de una.** El plan pedía *"cambiar temporalmente el status
del handler de `AuthenticationError` por otro valor"*. Con un solo valor (`FAIL`) la aserción (ii)
—el conjunto de statuses— dispara **antes** que la aserción (iii), que es la específica de CR-02 y
la razón de ser del lock; una demostración de una sola mutación habría dejado (iii) sin evidencia de
no-vacuidad. Se corrieron ambas (`FAIL` y `PASS`) y las dos salidas rojas están pegadas arriba.
Ambas revertidas; `main_matriz.py` sin diff.

**2. Q5 se declara con la medición del ALCANCE del gate, no con un error vivo de mypy.**
`45-RESEARCH.md` Hallazgo 12 pegaba el error de `DRV-MD-SEG-43` (`uv run mypy main_market_data.py`)
como prueba del gap. Ese defecto **ya está corregido en HEAD por el plan 45-01** (`4039551`), así que
hoy ese comando sale `Success`. Pegar el error de research como si fuera una medición de esta corrida
habría sido exactamente la clase de cifra heredada que esta fase existe para cerrar. En su lugar el
documento mide el gap directamente y lo pega: los seis paths de `files` en `pyproject.toml:97` (todos
`packages/*/src`), el `files: ^packages/.*/src/` del hook de pre-commit, el `run: uv run mypy` sin
argumentos del job `typecheck` (`ci.yml:123-124`), el `Success: no issues found in 75 source files`
que ese invoque produce (ninguno de ellos un `main_*.py`), y el hecho de que
`verification/test_main_market_data_deep_chain.py:147` parsea el driver por AST **sin importarlo**.
Conclusión idéntica a la de research, evidencia propia: ningún gate de CI mira los 5 drivers de la
raíz (13.370 líneas entre los cinco).

## Deferred Issues

Ninguno descubierto. Lo que queda diferido está **declarado por escrito dentro del propio artefacto**,
que es el punto del plan:

- Reparación de los 2 archivos → diferida; requiere presupuesto declarado por adelantado, y la
  estimación heredada de "38 firmas de argumento" **no fue re-medida** en esta fase (dicho así en § 3).
- Q5, gate de mypy sobre los drivers de la raíz → destino **backlog v1.9**; el plan **45-05** debe
  agregar la entrada al `ROADMAP.md` (§ 4).
- Los ~35 archivos `verification/` restantes → siguen inertes, fuera de alcance de v1.8 (§ 5).
- Red parcial de `test_public_surface.py` (4/6 paquetes, sin market-data ni wallets) y las 4 ramas
  hermanas `missing assumed key …` de `main_iol.py` → declaradas como límites de alcance (§ 6).

## Handoff al plan 45-05

El documento de decisión **nombra** dos cosas que 45-05 tiene que aterrizar para que sus afirmaciones
dejen de ser promesas:

1. `verification/test_probe_context_coverage.py` **al allowlist del job `lint`** de
   `.github/workflows/ci.yml` (D-08 ENMENDADA / D-10 ENMENDADA / D-11). Precondición ya verificada:
   `6 passed`. Sin ese enrolamiento, la transferencia del canario declarada en § 2.3 sería el
   "renombre del abandono" que `45-RESEARCH.md` Hallazgo 10 advierte.
2. La **entrada de backlog v1.9** para el gap de mypy sobre los 5 drivers de la raíz (§ 4).

Cuando 45-05 aterrice, el censo pasa de 53/13/40 a 53/18/35.

## Known Stubs

Ninguno. No se creó superficie nueva de producción; el único código nuevo es un test de lock, y su
no-vacuidad está demostrada por mutación arriba.

## Threat Flags

Ninguna. El plan no introduce endpoints, rutas de auth, accesos a archivo ni cambios de schema en
ningún límite de confianza. `main_matriz.py` se **lee** (por AST) y no se modifica. El documento cita
sólo nombres de test, fids, rutas del repo y conteos — cero credenciales y cero base URLs de vendor
(T-45-18, disposición `accept`, verificado por lectura).

## Self-Check: PASSED

Archivos declarados, verificados en disco:

```
FOUND: .planning/phases/45-.../45-HARN-04-DECISION.md
FOUND: verification/test_main_matriz_skip_line_shape.py
FOUND: verification/test_matriz_sweep_snapshot.py
FOUND: verification/test_main_matriz_login_fail_uniformity.py
```

Commits declarados, verificados en `git log`:

```
FOUND: 8f34c40  test(45-04): lock de taxonomía de retorno de probe_login_sync (HARN-04 Q4)
FOUND: 4911e93  docs(45-04): decisión escrita y fechada de HARN-04 + punteros en los 2 archivos aceptados
```

Sin deleciones de archivos en ninguno de los 2 commits
(`git diff --diff-filter=D --name-only HEAD~2 HEAD` → vacío). Sin archivos untracked generados.
