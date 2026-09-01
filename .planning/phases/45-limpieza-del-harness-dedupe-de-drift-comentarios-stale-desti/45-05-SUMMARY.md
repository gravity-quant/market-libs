---
phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
plan: 05
subsystem: ci-harness
tags: [harn-01, harn-03, harn-04, ci-allowlist, d-11, censo, backlog-v1.9, cierre-de-fase]
requires:
  - "45-01 (HARN-03 mecánico: D-05 ENMENDADA, D-09, D-07) — dejó IN-06 abierto a propósito para este plan"
  - "45-02 / 45-03 (HARN-01: guarda (func, digest) en los 7 sitios + verification/test_drift_dedupe_falsification.py con 6 arms)"
  - "45-04 (45-HARN-04-DECISION.md) — NOMBRA el enrolamiento de test_probe_context_coverage.py y la entrada de backlog v1.9 de Q5 que este plan debía aterrizar"
provides:
  - "Allowlist explícito del job `lint` extendido de 13 a 18 archivos en UN solo commit (D-11)"
  - "IN-06 cerrado: verification/test_public_surface.py corre en CI"
  - "Transferencia REAL del canario de probe_context: verification/test_probe_context_coverage.py corre en CI"
  - "El lock de falsificación de D-04 y el invariante P-3 corren en CI, no sólo en local"
  - "45-HARN-04-DECISION.md § 7 — censo post-fase medido + re-declaración de los 36 inertes"
  - "ROADMAP: HARN-VERIF-01 resuelto por decisión escrita; entrada nueva de backlog v1.9 GATE-DRV-MYPY-45"
affects:
  - "v1.9 — GATE-DRV-MYPY-45 (ningún gate de CI mira los 5 drivers main_*.py de la raíz) queda ruteado con su primer paso de medición nombrado"
  - "Cierre de la Phase 45: HARN-01, HARN-03 y HARN-04 quedan completos con todas sus piezas aterrizadas"
tech-stack:
  added: []
  patterns:
    - "Allowlist EXPLÍCITO de pytest dentro del job `lint`, nunca `pytest verification/` (el directorio arrastra rojo pre-existente aceptado como deuda)"
    - "Gates cross-package como *step* del job `lint`, nunca como job nuevo (precedente Phase 32 D-05, Phase 42-01)"
    - "Precondición antes de enrolar: cada archivo se corre SOLO y su salida se pega (D-06)"
    - "Gate de git sobre el criterio de consolidación: `git log --oneline <base>..HEAD -- <archivo> | wc -l` == 1"
key-files:
  created:
    - .planning/phases/45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti/45-05-SUMMARY.md
  modified:
    - .github/workflows/ci.yml
    - .planning/ROADMAP.md
    - .planning/phases/45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti/45-HARN-04-DECISION.md
decisions:
  - "El allowlist de CI queda en 18 archivos y sigue siendo explícito: los 36 verification/ restantes se re-declaran por escrito como inertes y fuera de alcance de v1.8 (D-10), con la cifra medida después del edit"
  - "El censo post-fase medido es 54/18/36, que CORRIGE la proyección 53/18/35 del handoff de 45-04: la base de disco se movió a 54 porque la propia fase creó verification/test_drift_dedupe_falsification.py en 45-02"
  - "HARN-VERIF-01 se marca resuelto por decisión escrita (aceptar deuda documentada, no reparar) sin borrar la entrada: su medición de causa raíz es la evidencia que cita el documento de decisión"
  - "El gap de gate de mypy sobre los 5 drivers de la raíz se rutea a v1.9 como GATE-DRV-MYPY-45, con su primer paso declarado como una MEDICIÓN del conteo de errores, no como una estimación"
metrics:
  duration: ~20 min
  completed: 2026-09-01
  tasks: 3
  commits: 2
  files_touched: 4
status: complete
---

# Phase 45 Plan 05: Edit consolidado de `ci.yml` (13 → 18) y cierre de fase Summary

**Los cinco locks que esta fase produjo o rescató dejaron de ser inertes: corren en CI desde un
único commit sobre `ci.yml` (`d6b34f0`), que es lo que el criterio 5 exigía; y lo que queda afuera
queda contado —36 archivos— y re-declarado por escrito, no silenciado.**

## Tasks Completed

| Task | Nombre | Commit | Archivos |
|---|---|---|---|
| 1 | Pre-flight: los 5 archivos pasan SOLOS (D-06) | *(sin commit — tarea de medición, cero archivos)* | — |
| 2 | Edit consolidado ÚNICO de `.github/workflows/ci.yml`, 13 → 18 | `d6b34f0` | `.github/workflows/ci.yml` |
| 3 | Censo post-fase, `HARN-VERIF-01` resuelto, backlog v1.9, gate de D-11 | `19e1bbb` | `45-HARN-04-DECISION.md`, `.planning/ROADMAP.md` |

---

## Task 1 — pre-flight: las 5 salidas, cada una con su comando

D-06 condiciona el enrolamiento a que el archivo **pase solo**. Los 5 se corrieron **por separado**
(no en un solo comando: si uno fallara, hace falta saber cuál y por qué). Ninguno reporta `failed`
ni `error`:

```
$ uv run pytest -q verification/test_public_surface.py
....                                                                     [100%]
4 passed in 0.04s

$ uv run pytest -q verification/test_finding_count_consistency.py
..                                                                       [100%]
2 passed in 0.01s

$ uv run pytest -q verification/test_findings_dedupe_by_title.py
............                                                             [100%]
12 passed in 0.02s

$ uv run pytest -q verification/test_drift_dedupe_falsification.py
......                                                                   [100%]
6 passed in 0.17s

$ uv run pytest -q verification/test_probe_context_coverage.py
......                                                                   [100%]
6 passed in 0.11s
```

**Contraste con la línea base que midió research/pattern-map:** 4 / 2 / 12 / (nuevo) / 6 →
**coincidencia exacta en los cuatro heredados**. Y el archivo nuevo,
`verification/test_drift_dedupe_falsification.py`, reporta **6 passed**: los 3 arms del plan 45-02
(colapso, NO-colapso, fid no quemado) más los 3 del plan 45-03 (locks por AST de orden y forma sobre
los 7 sitios). Es exactamente lo que exigía el criterio de aceptación.

**Censo PREVIO al edit, registrado para la Task 3:**

```
$ ls verification/test_*.py | wc -l
      54
$ grep -c 'verification/test_.*\.py' .github/workflows/ci.yml
13
$ grep -c '^  [a-z-]*:$' .github/workflows/ci.yml       # línea base de jobs, para el criterio "sin jobs nuevos"
5
$ git log --oneline 6b9b3b6..HEAD -- .github/workflows/ci.yml | wc -l
       0
```

Es decir: **54 en disco / 13 enrolados / 41 inertes**, y **cero** commits sobre `ci.yml` en toda la
fase hasta acá — la precondición limpia para que el gate de D-11 pueda dar exactamente 1.

---

## Task 2 — el edit consolidado único (13 → 18)

Un solo `Edit` acotado sobre el bloque `run: |` del step *"driver locks"* del job `lint`, con la
misma indentación y la misma continuación con backslash que las 13 líneas existentes. Las cinco
líneas agregadas, con su procedencia:

| Archivo enrolado | Por qué | Lock de decisión |
|---|---|---|
| `verification/test_public_surface.py` | Cierra `IN-06` | D-06 (HARN-03) |
| `verification/test_finding_count_consistency.py` | Para que el criterio 2 de HARN-01 (*"el invariante de fids sigue verde"*) signifique algo **fuera de local** | D-10 |
| `verification/test_findings_dedupe_by_title.py` | Primitiva que HARN-01 consume; inerte pese a estar escrita desde la Phase 11 | D-10 |
| `verification/test_drift_dedupe_falsification.py` | El lock de falsificación de D-04 (6 arms, 45-02 + 45-03) | D-04 / D-10 |
| `verification/test_probe_context_coverage.py` | El transferee del canario — sin esto, § 2.3 del documento de decisión sería *"renombrar el abandono"* | D-08 / D-10 **ENMENDADAS** |

**Lo que NO se hizo, y era lo prohibido:** no se reemplazó la lista por `pytest verification/` (habría
enrolado de golpe ~36 archivos que nunca corrieron, entre ellos los 2 con **19 failed / 19 errors**
que D-08 acepta como deuda, poniendo rojo el job `lint` del repo entero); no se creó ningún job
nuevo; no se movió el step; y el comentario de `ci.yml:76-78` —la razón escrita de por qué la lista
es EXPLÍCITA— quedó **intacto**.

### Criterios de aceptación, medidos

```
$ grep -c 'verification/test_.*\.py' .github/workflows/ci.yml
18
$ grep -c 'test_public_surface.py\|test_finding_count_consistency.py\|test_findings_dedupe_by_title.py\|test_drift_dedupe_falsification.py\|test_probe_context_coverage.py' .github/workflows/ci.yml
5
$ grep -c 'Es una lista EXPLÍCITA' .github/workflows/ci.yml
1
$ grep -c '^  [a-z-]*:$' .github/workflows/ci.yml
5                     # línea base: 5 — SIN CAMBIO, no se agregó ningún job
$ grep -c 'driver locks de market-data' .github/workflows/ci.yml
1                     # un solo step de driver locks
$ uv run python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK, jobs:', list(d['jobs'].keys()))"
YAML OK, jobs: ['lint', 'pre-commit', 'typecheck', 'test']
```

### Espejo completo del comando de CI, en local

```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
280 files already formatted

$ uv run lint-imports
market_data_client._core does not depend on transport modules KEPT
Contracts: 5 kept, 0 broken.

$ uv run python tools/check_decode_intactness.py
Check B  filter scan-region intactness: 5 marker-delimited regions (54 lines each) reduce to one hash 684191c7cdc5ff9c
Check C  ban list: `strict=False` (in `_decode.py`), `msgspec.field(` absent from 75 package source files
Check D  package roster: 5 in-scope packages carry a `_decode.py`; `wallets-client` exempt (…)

$ uv run python tools/check_uniform_structure.py
uniform structure: all 6 packages under `packages/` carry `models.py`, `types.py` in their import root

$ uv run python tools/check_surface_types.py
surface types: 6 packages, 187 `__all__` names, 337 definitions scanned, 467 fields scanned, 13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1), 0 violations
```

Y el `pytest -q` con **las 18 rutas exactamente como quedaron escritas en el YAML**:

```
$ uv run pytest -q verification/test_main_market_data_deep_chain.py verification/test_safemodel_diff_null_object_links.py \
    verification/test_main_matriz_risk_envelope_keys.py verification/test_safemodel_diff_mapping_recursion.py \
    verification/test_main_verify_classification.py verification/test_main_matriz_skip_line_shape.py \
    verification/test_main_higyrus_skip_line_shape.py verification/test_run_evidence.py \
    verification/test_main_iol_deep_chain.py verification/test_main_higyrus_deep_chain.py \
    verification/test_main_matriz_deep_chain.py verification/test_cycle_closure_phase33.py \
    verification/test_literal_census_venue_gate.py verification/test_public_surface.py \
    verification/test_finding_count_consistency.py verification/test_findings_dedupe_by_title.py \
    verification/test_drift_dedupe_falsification.py verification/test_probe_context_coverage.py
........................................................................ [ 39%]
........................................................................ [ 79%]
.....................................                                    [100%]
181 passed in 0.82s
```

**181 passed** — el step de CI corre verde con el allowlist nuevo. Deliberadamente **no** se corrió
`uv run pytest -q` a secas como gate de fase: esa forma arrastra los 19 failed / 19 errors
pre-existentes que D-08 decidió NO reparar, así que *"suite completa verde"* no es un gate alcanzable
ni deseable en esta fase, y fingir que lo es habría sido la clase exacta de mentira que la fase
existe para cerrar.

---

## Task 3 — cierre

### (a) Censo post-fase, medido

```
$ ls verification/test_*.py | wc -l
      54
$ grep -c 'verification/test_.*\.py' .github/workflows/ci.yml
18
```

| Medida | § 0 / M3 (plan 45-04) | Al arrancar 45-05 | **Después del edit** |
|---|---|---|---|
| En disco | 53 | **54** | **54** |
| Enrolados | 13 | 13 | **18** |
| **Inertes** | 40 | **41** | **36** |

**El delta 53 → 54 se explica en vez de redondearse.** El archivo nuevo es
`verification/test_drift_dedupe_falsification.py`, creado por el plan **45-02** (`bda2bec`, la puerta
RED del TDD) y extendido a 6 arms por el **45-03** (`a573a91`) — nació **después** de la medición M3,
que corrió en el plan 45-04. Por eso la proyección *"53 / 13 / 40 → 53 / 18 / 35"* del final de § 2.3
del documento de decisión queda **corregida a 54 / 13 / 41 → 54 / 18 / 36** por su § 7 nueva. El
enrolamiento sí fue de **+5 exactos**, como estaba declarado; lo que se movió es la base de disco,
porque la propia fase agregó un archivo. Es la misma clase de corrección que § 0 le hizo al
`52 / 12 / 40` de `41-ROLLUP.md`.

**La re-declaración de los inertes está escrita** (`45-HARN-04-DECISION.md` § 7): los **36** archivos
`verification/test_*.py` que quedan en disco y no corren en CI siguen **formalmente fuera de alcance
de v1.8**, con la razón nombrada (`PITFALLS.md` contra *"enrolar `verification/` en bloque"* + el rojo
pre-existente de 19 failed / 19 errors que un `pytest verification/` importaría al job `lint`), la
constancia de que los 2 archivos de deuda **siguen sin enrolarse**, y la declaración de que la
*"declaración inerte"* que la Phase 41 dejó ruteada acá queda **satisfecha por re-declaración medida,
no por enrolamiento total**.

### (b) `HARN-VERIF-01` — resuelto por decisión escrita, sin borrar la entrada

Editado con `Edit` acotado (`.planning/ROADMAP.md`, entrada de *Deferred to v1.7+*). El texto
original se conserva **verbatim**: su medición de causa raíz es la evidencia que cita el documento.
La nota agregada dice explícitamente que la disposición fue **`ACEPTAR COMO DEUDA DOCUMENTADA`, NO
`reparar`**, con ruta y fecha (`45-HARN-04-DECISION.md`, 2026-09-01), los tres ítems de D-08
respondidos por archivo, el cierre de Q4 **por implementación**, y que **el gemelo de mypy sobre
`verification/` sigue fuera de alcance por escrito** (`REQUIREMENTS.md § Out of Scope`).

### (c) Entrada de backlog v1.9 — `GATE-DRV-MYPY-45`

Sección nueva `### Deferred to v1.9+ (from v1.8)` en `.planning/ROADMAP.md`, con las cuatro piezas
que el plan pedía: **el hecho medido** (apuntar mypy a mano a un driver de la raíz levanta errores
reales — así se detectó `DRV-MD-SEG-43`), **la causa de alcance** (los seis paths `packages/*/src` del
`files` de mypy en `pyproject.toml:97`, el hook de pre-commit scoped a `^packages/.*/src/`, el
`uv run mypy` sin argumentos del job `typecheck` que hereda ese `files` con sus 75 source files sin
un solo `main_*.py`, y el lock de deep-chain que parsea el driver **por AST sin importarlo**), **por
qué NO se cerró acá** (apuntar mypy a 5 archivos de miles de líneas dentro de una fase de limpieza es
scope creep de tamaño no medido) y **el destino: v1.9**. Se agregó además el primer paso al
retomarlo: **medir** el conteo de errores sobre los 5 drivers antes de decidir la forma del gate — el
presupuesto sale de esa medición, no de una estimación.

### (d) Gate del criterio 5 (D-11)

```
$ git log --oneline 6b9b3b6..HEAD -- .github/workflows/ci.yml | wc -l
1
$ git log --oneline 6b9b3b6..HEAD -- .github/workflows/ci.yml
d6b34f0 ci(45-05): enrolar 5 locks en el allowlist explícito del job lint (13 → 18)
```

**Exactamente 1.** Toda la fase tocó `ci.yml` una sola vez, y fue este plan.

---

## (e) Los 5 criterios de éxito del ROADMAP, con su evidencia

**Criterio 1 — el dedupe colapsa lo repetido y NO colapsa lo distinto.**
Cubierto por los planes 45-02 (guarda `(func, digest)` en `main_market_data.py`, por TDD) y 45-03
(los 6 sitios restantes con el no-op de SU contrato de retorno). El lock de falsificación
`verification/test_drift_dedupe_falsification.py` corre **6 passed** y —lo que importa— **ahora corre
en CI** (`ci.yml`, línea nueva). La aritmética esperada es **22 → 11** sobre la corrida medida de
33-05: es lo que el mecanismo `(func, digest)` entrega colapsando el par sync/async idéntico dentro
de un proceso. **No es un colapso cross-proceso, y eso es deliberado:** D-01 ENMENDADA lo rechaza
explícitamente (una clave que incluyera `surface` colapsaría 0 bloques; un título content-addressed
cross-run es exactamente la superficie donde `PITFALLS.md` Pitfall 9 advierte que un bug se tragaría
una divergencia real). El arm (b) del test prueba el no-colapso: divergencia **distinta** sobre el
**mismo** endpoint sigue escribiendo bloque nuevo, porque el digest cambia.

**Criterio 2 — el invariante de fids sigue verde SIN aflojarse.**
`verification/test_finding_count_consistency.py` (P-3) quedó verde y **sin un solo carácter editado**
en los dos planes que tocaron los drivers: `git diff --quiet HEAD -- verification/test_finding_count_consistency.py`
→ **exit 0** en 45-02 y en 45-03. Y el arm de fid del test de falsificación **sí detecta la
violación**: con `_next_fid()` llamado antes de la decisión de dedupe, falla con `2 == 1` —un bloque
escrito, dos fids consumidos—, mientras los arms (a) y (b) **seguían pasando**; por eso D-03
necesitaba su propio arm y por eso P-3 no puede cubrirlo (es un property test con allocator local que
no importa ningún driver). Desde este plan, P-3 **corre en CI**, así que el criterio significa algo
fuera de local.

**Criterio 3 — `HARN-04` resuelto con decisión escrita y fechada.**
`.planning/phases/45-…/45-HARN-04-DECISION.md`, fechado **2026-09-01** (plan 45-04), con los tres
ítems de D-08 respondidos por archivo sobre evidencia medida en su propia corrida, y ampliado por
este plan con su **§ 7 de censo post-fase**. La cláusula *"reparar sin enrolar no es admisible"* del
criterio queda satisfecha por la otra rama: se **aceptó la deuda** con su razón, y lo que sí se
transfirió (el canario) **sí quedó enrolado**.

**Criterio 4 — cifra medida, `IN-06` cerrado, `IN-05` retirado.**
La cifra del docstring del gate dice el valor **medido** (`187 / 337 / 467`, plan 45-01, re-verificado
en este plan: `uv run python tools/check_surface_types.py` → `187 … 337 … 467, 0 violations`).
`IN-05` quedó **retirado** del backlog contra el código (`matriz_client.__version__` → `0.3.0`), no
contra el reporte. Y **`IN-06` queda cerrado en este plan**: `verification/test_public_surface.py`
está dentro del allowlist explícito de `ci.yml` desde `d6b34f0`. *(Límite declarado, no silenciado:
sus snapshots cubren 4 de los 6 paquetes — sin `market-data-client` ni `wallets-client`; ver
`45-HARN-04-DECISION.md` § 6.1. "Public surface enrolado en CI" no debe leerse como cobertura total.)*

**Criterio 5 — un solo cambio consolidado + CI verde.**
`git log --oneline 6b9b3b6..HEAD -- .github/workflows/ci.yml | wc -l` → **1** (`d6b34f0`). El espejo
completo del comando de CI corre verde en local: `ruff check`, `ruff format --check`, `lint-imports`,
los 3 gates de `tools/`, y `pytest -q` con las 18 rutas → **181 passed**. **La mitad de matriz de este
criterio queda pendiente de verificación humana:** el espejo local **no** ejercita las 12 patas
(6 paquetes × py3.12/py3.13) ni los jobs `pre-commit` y `typecheck` en el runner — hay que
confirmarlo en GitHub Actions tras el push (ver *Human check pendiente* abajo).

---

## Verificación del plan

| Ítem | Comando | Resultado |
|---|---|---|
| Los 5 archivos pasan solos | 5 invocaciones separadas de `uv run pytest -q` | 4 / 2 / 12 / 6 / 6 passed |
| Allowlist en 18 | `grep -c 'verification/test_.*\.py' .github/workflows/ci.yml` | `18` |
| Las 5 rutas nuevas presentes | grep de las 5 | `5` |
| Comentario explicativo intacto | `grep -c 'Es una lista EXPLÍCITA'` | `1` |
| Sin jobs nuevos | `grep -c '^  [a-z-]*:$'` | `5` (línea base `5`) |
| YAML parsea | `uv run python -c "import yaml; yaml.safe_load(...)"` | `YAML OK, jobs: ['lint','pre-commit','typecheck','test']` |
| Espejo de CI en local | ruff ×2 + lint-imports + 3 gates de `tools/` + pytest 18 rutas | todo verde, `181 passed` |
| Gate de D-11 | `git log --oneline 6b9b3b6..HEAD -- .github/workflows/ci.yml \| wc -l` | `1` |
| Ledger sin ensuciar | `git status --porcelain .planning/verification/` | vacío |
| Edits acotados | `git diff --stat` de la Task 3 | `ROADMAP.md` +5, `45-HARN-04-DECISION.md` +79, **0 deleciones** |

## Human check pendiente

**Tras el push de la rama, confirmar en GitHub Actions que quedan verdes las 12 patas de la matriz
(6 paquetes × py3.12 / py3.13) más los jobs `lint`, `pre-commit` y `typecheck`, con el allowlist de
18 archivos.** Es la mitad del criterio 5 que el espejo local no puede ejercitar: los `uv run` de
esta corrida usan el venv local sobre CPython 3.12.11 y no reproducen ni la matriz de versiones ni el
runner de Ubuntu.

## Deviations from Plan

Ninguna de las Reglas 1-4 se activó. Una única precisión de ejecución, que es una **corrección de
cifra heredada** y no un cambio de alcance:

**1. El censo "antes" medido es 54 / 13 / 41, no el 53 / 13 / 40 que el plan citaba como referencia
esperada.** El plan escribía *"la referencia esperada es 53/13/40 antes y 54/18/36 después, pero se
escribe lo MEDIDO"*. Lo medido al arrancar fue **54 en disco**, porque
`verification/test_drift_dedupe_falsification.py` nació en el plan 45-02 (`bda2bec`) —**después** de
la medición M3 del plan 45-04, de donde venía el 53. El "después" del plan (**54 / 18 / 36**) coincide
exactamente con lo medido. Se escribió lo medido en ambas columnas y se nombró la causa del delta,
tanto en el SUMMARY como en la § 7 nueva del documento de decisión, que además **corrige
explícitamente** la proyección `53 / 18 / 35` que el propio documento había dejado escrita en § 2.3.
Esta corrección es exactamente el comportamiento que la fase existe para instalar: la cifra stale se
re-mide y se dice cuál corrige a cuál.

## Deferred Issues

Ninguno descubierto en esta corrida. Lo diferido queda **declarado por escrito**, con destino
nombrado:

- **`GATE-DRV-MYPY-45`** — ningún gate de CI mira los 5 drivers `main_*.py` de la raíz (13.370 líneas)
  → **backlog v1.9**, entrada nueva en `ROADMAP.md`, con su primer paso declarado como medición.
- **Los 36 archivos `verification/` inertes** → siguen fuera de alcance de v1.8, re-declarados con la
  cifra medida (`45-HARN-04-DECISION.md` § 7).
- **Reparación de los 2 archivos de matriz** → diferida; requiere presupuesto declarado y la
  estimación heredada de "38 firmas de argumento" **debe re-medirse** antes de planificarla.
- **Red parcial de `test_public_surface.py`** (4 de 6 paquetes) y **las 4 ramas hermanas
  `missing assumed key …` de `main_iol.py`** → límites de alcance declarados en
  `45-HARN-04-DECISION.md` § 6.

## Known Stubs

Ninguno. Este plan no crea superficie de producción: el único cambio de código es una lista de rutas
en un workflow de CI, y sus 5 líneas nuevas están verificadas ejercitando el comando completo en
local (`181 passed`).

## Threat Flags

Ninguna. Contra el registro STRIDE del plan: **T-45-19** (DoS del pipeline) mitigado por medición —
los 5 archivos se corrieron SOLOS antes de enrolarlos y el espejo completo de CI corrió verde;
**T-45-20** (tampering del allowlist) mitigado — no se colapsó a `pytest verification/`, el conteo
quedó pinneado en 18 y el comentario de política sigue presente; **T-45-21** (repudiation del
criterio 5) mitigado por el gate de git con salida pegada (`1`); **T-45-22** (elevation) `accept` —
el edit es una lista de rutas dentro de un step existente: sin jobs nuevos, sin `permissions`, sin
acciones de terceros, sin secretos (verificado por diff: +6 / −1 en un solo bloque `run:`);
**T-45-SC** `accept` — cero dependencias nuevas.

## Self-Check: PASSED

Archivos declarados, verificados en disco:

```
FOUND: .github/workflows/ci.yml
FOUND: .planning/ROADMAP.md
FOUND: .planning/phases/45-…/45-HARN-04-DECISION.md
FOUND: .planning/phases/45-…/45-05-SUMMARY.md
```

Commits declarados, verificados en `git log`:

```
FOUND: d6b34f0  ci(45-05): enrolar 5 locks en el allowlist explícito del job lint (13 → 18)
FOUND: 19e1bbb  docs(45-05): censo post-fase medido, HARN-VERIF-01 resuelto y backlog v1.9 del gap de mypy
```

Sin deleciones de archivos en ninguno de los 2 commits
(`git diff --diff-filter=D --name-only HEAD~2 HEAD` → vacío). Sin archivos untracked generados; el
ledger `.planning/verification/` quedó sin tocar por las corridas de pytest.
