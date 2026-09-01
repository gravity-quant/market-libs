---
phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr
plan: 03
subsystem: docs
tags: [market-data-client, disposition, evidence, ci-gates, backlog, phase-closure]

# Dependency graph
requires:
  - phase: 43-01
    provides: "la forma reconciliada de Instrument/Segment y la tabla de disposicion implementada que este plan consolida como evidencia del criterio 1"
  - phase: 43-02
    provides: "las 5 claves de HARN-02 tipadas, la lista exacta de records de T14 y los dos items de seguimiento marcado"
  - phase: 42-live-verification
    provides: "el capture del wire del 2026-08-31 (key-set y conteos) y la marca NO-AUTORITATIVO de los baselines committeados"
provides:
  - "43-DISPOSITION.md: 7 secciones — disposicion campo por campo con cero filas sin disponer, antes/despues MEDIDO de get_segments(), criterio 3 mecanico, D-14 medido por identidad de objeto, los dos seguimientos con destino nombrado y la tabla de los 4 jobs de CI"
  - "_core.py::parse_segments_response con el docstring reconciliado — la unica prosa de fuente que la correccion volvio falsa"
  - "ROADMAP.md: entradas de backlog DRV-MD-SEG-43 y SURF-MD-FEEDSUB-43, mas la anotacion de resultado sobre SHAPE-MD-REF-33 y TYP-MD-EXTRA-33"
  - "El job pre-commit de CI vuelve a verde: rojo PRE-EXISTENTE de end-of-file-fixer corregido"
affects: [44-pub-01, 45-harness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "medicion de identidad de objeto funcion por el camino de referencia real cuando el simbolo no esta re-exportado"
    - "verificacion programatica capture-vs-artefacto: extraer los escalares distintos del crudo y buscarlos con match de palabra completa en el artefacto committeado"
    - "replica de la forma pre-fix como dataclass descartable para MEDIR el antes en vez de afirmarlo"

key-files:
  created:
    - .planning/phases/43-market-data-client-forma-de-instrument-segment-5-claves-extr/43-DISPOSITION.md
  modified:
    - packages/market-data-client/src/market_data_client/_core.py
    - .planning/ROADMAP.md
    - .planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-06-PLAN.md
    - .planning/phases/42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce/42-05-PLAN.md

key-decisions:
  - "D-14 se midio por el camino de referencia REAL (identidad del modulo _core alcanzado desde cada superficie + identidad del objeto funcion + los 4 call sites), no por el comando del plan, que asumia un re-export inexistente y levantaba AttributeError"
  - "El antes de get_segments() se MIDIO ejecutando una replica de la forma pre-fix sobre la misma fila sintetica (5 records, 3 cadenas vacias) en vez de citarse del ledger solamente"
  - "El rojo pre-existente del job pre-commit se corrige en vez de diferirse: es +1 byte de whitespace, es la remediacion que el propio hook prescribe (no una relajacion de gate, T-43-14) y no altera un solo caracter de prosa historica (T-43-12)"
  - "No se corre `uv run pytest -q` a secas: testpaths incluye verification/, que arrastra el rojo pre-existente de HARN-VERIF-01 (19 failed/19 errors). La reproduccion fiel del job test son las 6 corridas per-package, que es lo que CI hace"
  - "TYP-MD-EXTRA-33 se anota ademas de SHAPE-MD-REF-33: dejarla sin anotar habria conservado una entrada forward-looking falsa, el modo de falla exacto que T-43-12 vigila"

patterns-established:
  - "Toda afirmacion de cierre de fase llega con su comando y su salida verbatim pegados; si el comando del plan no corre, se sustituye por uno que mide la MISMA afirmacion y se declara la sustitucion"
  - "El contador de un gate se usa como testigo cruzado de un item de seguimiento: el delta +10 de check_surface_types confirma que los 15 campos de FeedSubscription quedaron fuera del escaneo"

requirements-completed: [SHAPE-01, HARN-02]

# Metrics
duration: 11min
completed: 2026-09-01
status: complete
---

# Phase 43 Plan 03: Cierre de fase — disposición, evidencia medida y gates Summary

**La Phase 43 queda cerrada con evidencia ejecutada en vez de afirmada: `43-DISPOSITION.md` documenta la disposición de los 17 campos con cero filas sin disponer, mide el antes/después de `get_segments()` corriendo la forma pre-fix contra la actual, prueba D-14 por identidad de objeto función, y registra los 4 jobs de CI en verde sin bump de versión en ninguno de los tres sitios.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-09-01T01:09:07Z
- **Completed:** 2026-09-01T01:20:43Z
- **Tasks:** 3
- **Files modified:** 4 (1 creado, 3 modificados)

## Accomplishments

- **La única prosa de fuente que la corrección volvió falsa está reconciliada.** El docstring de `parse_segments_response` declaraba la corrección de forma *DELIBERADAMENTE* diferida y ruteaba al backlog `SHAPE-MD-REF-33`; las dos afirmaciones eran falsas desde el plan 43-01. `parse_instruments_response` se revisó por la misma clase de prosa y quedó **intacto**: es field-agnostic por diseño.
- **El antes/después de `get_segments()` está MEDIDO, no afirmado.** Se ejecutó una réplica de la forma pre-fix sobre la misma fila sintética del key-set medido: **5 records de divergencia y tres cadenas vacías**. La forma actual sobre la misma fila: **cero records, dos campos poblados**.
- **D-14 quedó probado por identidad de objeto**, y de paso se corrigió el método: el comando del plan asumía un re-export que no existe.
- **Los 4 jobs de CI están verdes** con exit code por paso registrado — y la reproducción encontró un **rojo pre-existente** del job `pre-commit` que estaba en `main` desde antes de la fase.
- **Los dos ítems que la fase deja abiertos tienen destino nombrado y escrito**, con IDs propios en el backlog.
- **Cero bump de versión** en los tres sitios; `uv.lock` sin tocar; cero archivos prohibidos en el diff acumulado.

## Salida verbatim de la comparación de identidad de D-14

```
=== (b1) el _core alcanzado desde cada superficie es el MISMO modulo ===
client._core is _core: True
aio._core    is _core: True

=== (b2) identidad del objeto funcion alcanzado desde cada superficie ===
client -> _core.parse_segments_response is _core.parse_segments_response: True
aio    -> _core.parse_segments_response is _core.parse_segments_response: True
client -> _core.parse_instruments_response is _core.parse_instruments_response: True
aio    -> _core.parse_instruments_response is _core.parse_instruments_response: True

=== (b3) call sites: ambas superficies llaman _core.parse_X, ninguna redefine ===
client.py:570:        return _core.parse_instruments_response(resp)
client.py:576:        return _core.parse_segments_response(resp)
aio.py:572:        return _core.parse_instruments_response(resp)
aio.py:578:        return _core.parse_segments_response(resp)
```

Y las otras dos mediciones de D-14:

```
$ grep -nE "\.(symbol|marketId|segment|expired|market_id|currency|days_to_maturity|maturity|outright|
             subscribed|active|instrumentType|marketSegmentId|description|live_instruments)\b" \
       packages/market-data-client/src/market_data_client/{client,aio}.py
(sin salida — exit status 1, cero coincidencias)

$ git diff --name-only 396c717 HEAD | grep -cE "market_data_client/(client|aio)\.py|^main_market_data\.py"
0
```

`segment` / `market_id` / `active` / `subscribed` **sí** aparecen en las dos superficies, pero como **parámetros de query de la request** de `get_instruments()` — filtros de entrada, no accesos a atributos del modelo de respuesta. El grep discrimina por el punto de dereferencia justamente para no confundirlos.

## Tabla de resultados de los 4 jobs con exit codes

| Job | Paso | Exit | Resultado |
|---|---|---|---|
| `lint` | `uv lock --check` | **0** | `Resolved 48 packages` (no-op) |
| `lint` | `uv run ruff check .` | **0** | `All checks passed!` |
| `lint` | `uv run ruff format --check .` | **0** | `279 files already formatted` |
| `lint` | `uv run lint-imports` | **0** | `Contracts: 5 kept, 0 broken` |
| `lint` | grep LOG-01 sobre `packages/*/src/` | **0** | cero coincidencias (grep exit 1 = step verde) |
| `lint` | `tools/check_decode_intactness.py` | **0** | 5 copias → hash `a1f00c824348164c`; checks A–D |
| `lint` | `tools/check_uniform_structure.py` | **0** | los 6 paquetes con `models.py` + `types.py` |
| `lint` | `tools/check_surface_types.py` | **0** | **`0 violations`**; 337 definiciones, **452 campos** (baseline 442 → delta **+10**) |
| `lint` | los 13 tests de `verification/` de la allowlist | **0** | **150 passed** |
| `pre-commit` | `uv run pre-commit run --all-files` | **0** | los 9 hooks `Passed` — **tras corregir un rojo pre-existente** (ver Deviations) |
| `typecheck` | `uv run mypy` | **0** | `Success: no issues found in 75 source files` |
| `typecheck` | `uv run mypy packages/<pkg>/tests` ×6 | **0** | 14 / 5 / 29 / 18 / 21 / 36 files |
| `test` | `pytest packages/higyrus-client --cov=…` | **0** | 303 passed |
| `test` | `pytest packages/wallets-client --cov=…` | **0** | 10 passed |
| `test` | `pytest packages/matriz-client --cov=…` | **0** | 609 passed |
| `test` | `pytest packages/iol-client --cov=…` | **0** | 311 passed |
| `test` | `pytest packages/ambito-financiero-client --cov=…` | **0** | 208 passed, 1 deselected |
| `test` | `pytest packages/market-data-client --cov=…` | **0** | **727 passed** (piso del plan: ≥ 711) |
| harness | `pytest verification/test_cycle_closure_phase33.py -q --no-cov` | **0** | 21 passed — los pisos del ledger siguen en pie |

**Total del job `test`: 2168 passed, cero fallas.**

**Gate de no-publicación (D-16):** `__version__` = `0.6.0`; `grep -c '^version = "0.6.0"' pyproject.toml` = `1`; `git status --porcelain uv.lock` vacío; `uv lock --check` exit `0`. **Archivos prohibidos en el diff acumulado: 0** — ni `README.md`, ni `pyproject.toml` del paquete, ni `__init__.py`, ni `uv.lock`, ni `client.py`, ni `aio.py`, ni `main_market_data.py`, ni `release.yml`, ni nada bajo `packages/matriz-client/`.

## Conteo de tests antes y después de la fase completa

| Momento | Tests de `market-data-client` | Resultado |
|---|---|---|
| Antes de la fase (HEAD `396c717`) | 711 | 711 passed |
| Después del plan 43-01 | 717 | +6 |
| Después del plan 43-02 | 727 | +10 |
| **Después del plan 43-03 (final)** | **727** | **727 passed** (este plan no agrega tests: produce evidencia) |

**Delta neto de la fase: +16 tests.** Ningún test fue renombrado ni borrado en toda la fase.

**Por qué no se corrió `uv run pytest -q` a secas** (que el plan pedía): `testpaths = ["packages", "tests", "verification"]` (`pyproject.toml:106`), así que una corrida sin path colecta `verification/`, que arrastra el rojo **pre-existente y documentado** de `HARN-VERIF-01`. Medido en esta sesión: `19 failed, 3 passed, 19 errors` — idéntico al baseline de `33-BASELINE.md`, ajeno a este paquete, ruteado a la Phase 45. Ésa es exactamente la razón por la que CI pasa paths per-package explícitos en `test` y una allowlist explícita en `lint`. La reproducción fiel del job son las 6 corridas per-package, todas verdes.

## Confirmación explícita de la verificación capture-vs-artefacto

Verificación **programática**, no visual: se extrajeron los **69 valores escalares distintos** de los dos captures (`market-data-wire-segments-42.json` y `market-data-wire-instruments-42.json`, incluidos los escalares del sobre) y se buscó cada uno en `43-DISPOSITION.md` con match de palabra completa.

**Resultado: una sola coincidencia, benigna y explicada.** `maturity` vale `2026-08-31` en las 50/50 filas del capture de `/instruments`, que es la **misma fecha de la corrida**; el artefacto usa `2026-08-31` únicamente en prosa como fecha de la lectura del wire — un dato ya committeado en `42-WIRE-READ.md` (3 ocurrencias) y en los summaries 43-01 y 43-02.

**Ningún valor de fila fue transcrito: cero valores de `segment`, cero de `live_instruments`, cero de cualquier campo de `Instrument`.** Lo único que cruzó la frontera al artefacto committeado son **nombres de clave, conteos de fila y tipos de Python**. Los valores sintéticos de la sección 2 usan el prefijo `GSDPROBE`/`GSD` y una `maturity` deliberadamente distinta (`2026-12-31`) para que la separación sea visible a simple vista. **T-43-11 mitigado y verificado.**

## Task Commits

1. **Task 1: reconciliar el docstring de `parse_segments_response` y medir D-14** — `5a30fd9` (docs)
2. **Task 2: `43-DISPOSITION.md` + las entradas de backlog en `ROADMAP.md`** — `0a3296a` (docs)
3. **Task 3: gate de fase — los 4 jobs de CI y el gate de no-publicación** — `7d3f2bd` (chore)

## Files Created/Modified

- `.planning/phases/43-…/43-DISPOSITION.md` — **creado**, 592 líneas, 7 secciones: disposición campo por campo (`Instrument` 12 filas, `Segment` 5, HARN-02 5), antes/después medido de `get_segments()` con el ledger + el key-set del capture + las dos decodificaciones ejecutadas + la inertness del SHAPE-diff del driver, criterio 3 con la mecánica del walker, D-14 medido, los dos seguimientos con destino nombrado, y la tabla de los 4 jobs de CI.
- `packages/market-data-client/src/market_data_client/_core.py` — párrafo obsoleto del docstring de `parse_segments_response` reemplazado. El resto quedó **verbatim**: sobre y clave de desenvolvimiento, referencia cruzada a `parse_instruments_response`, bug S-1 con sus findings, compatibilidad del body de lista pelada y sus guardas, orden body-consume-then-raise, y la nota de no-stamp `received_at` (D-05).
- `.planning/ROADMAP.md` — **sólo inserciones (7 líneas, cero borrados)**: entradas `DRV-MD-SEG-43` y `SURF-MD-FEEDSUB-43` en una sección nueva *Nuevos en v1.8 (from Phase 43)*, más anotaciones de resultado sobre `SHAPE-MD-REF-33` y `TYP-MD-EXTRA-33` con su texto histórico conservado verbatim.
- `.planning/phases/41-…/41-06-PLAN.md` y `.planning/phases/42-…/42-05-PLAN.md` — **+1 byte cada uno** (newline final). Ver Deviations.

## Decisions Made

- **La medición de D-14 se hizo por el camino de referencia real.** El comando del plan (`client.parse_segments_response is _core.parse_segments_response`) levanta `AttributeError`: los parsers no están re-exportados en la superficie. Se sustituyó por tres mediciones que prueban la **misma** afirmación —identidad del módulo `_core` alcanzado desde cada superficie, identidad del objeto función, y los 4 call sites como única vía de acceso— y la sustitución quedó **declarada** en el artefacto, no silenciada.
- **El ANTES se ejecutó en vez de sólo citarse.** El plan pedía citar el ledger; se agregó una réplica descartable de la forma pre-fix decodificando la misma fila sintética, porque una cita del ledger prueba que la divergencia se midió en vivo pero no muestra **qué recibía el consumidor**. La réplica muestra las tres cadenas vacías.
- **`TYP-MD-EXTRA-33` se anotó además de `SHAPE-MD-REF-33`.** El plan sólo nombraba la segunda. Dejar la primera sin anotar habría conservado una entrada **forward-looking falsa** en el backlog — exactamente el modo de falla contra el que T-43-12 protege, y el mismo que el plan 42-06 tuvo que corregir para la Q5.
- **El delta del contador de `check_surface_types` se usó como testigo cruzado.** 442 → 452 (+10) cuadra exacto con los cambios de superficie exportada (`Instrument` +6, `Segment` −1, `FeedIngestor` +3, `HealthFeed` +1, `Symbol` +1) y **no** incluye los 15 campos de `FeedSubscription` — que es la confirmación numérica del ítem de seguimiento de la sección 6, en vez de una lectura del código.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] El comando de identidad de D-14 del plan levanta `AttributeError`**

- **Found during:** Task 1
- **Issue:** el bloque `<verify>` y un criterio de aceptación exigen `client.parse_segments_response is _core.parse_segments_response` imprimiendo `True True True True`. Los parsers **no** están re-exportados en `client.py` ni en `aio.py`: las dos superficies los alcanzan como atributo del módulo `_core` importado (`return _core.parse_segments_response(resp)`). El comando aborta con `AttributeError: module 'market_data_client.client' has no attribute 'parse_segments_response'`, así que el criterio era **inejecutable como estaba escrito**.
- **Fix:** se midió la misma afirmación por el camino de referencia real — `client._core is _core` y `aio._core is _core` (mismo objeto módulo), la identidad `is` de los dos objetos función alcanzados desde cada superficie, y el grep de los 4 call sites que prueba que ninguna superficie redefine ni envuelve el parser. Las seis comparaciones imprimen `True`. La sustitución está declarada explícitamente en `43-DISPOSITION.md` § 4.b bajo *Nota de método*, no escondida.
- **Files modified:** ninguno (es una corrección de medición)
- **Commit:** `5a30fd9`

**2. [Rule 3 - Blocking] El job `pre-commit` estaba rojo en `main` ANTES de la fase**

- **Found during:** Task 3
- **Issue:** `uv run pre-commit run --all-files` terminó en exit `1`. El hook `end-of-file-fixer` modificó `.planning/phases/41-…/41-06-PLAN.md` y `.planning/phases/42-…/42-05-PLAN.md`, dos planes de fases anteriores que **la Phase 43 nunca tocó**. Bloquea el criterio de aceptación del Task 3 y el criterio 5 de la fase.
- **Medición de que es pre-existente (no supuesto):** los dos archivos terminan en `</output>` **sin newline final** y son **byte-idénticos** en el commit base de la fase (`396c717`) y en HEAD; `git diff --name-only 396c717 HEAD | grep -c "41-06-PLAN.md\|42-05-PLAN.md"` devuelve `0`.
- **Fix:** aceptar la corrección del hook — **+1 byte por archivo**, con **cero caracteres de contenido alterados** (verificado comparando el contenido completo contra `git show HEAD:<file>`). **No es una relajación de gate (T-43-14):** es la remediación que el propio hook prescribe, el análogo directo de *"tipar el campo, nunca ensanchar la tabla"*. **No toca T-43-12:** agregar un newline terminal no reescribe prosa histórica.
- **Files modified:** `.planning/phases/41-…/41-06-PLAN.md`, `.planning/phases/42-…/42-05-PLAN.md`
- **Commit:** `7d3f2bd`
- **Efecto sobre el alcance:** el diff acumulado de la fase pasa de 16 a 18 archivos. Los dos nuevos son documentos de `.planning/`; ninguno es fuente de paquete, sitio de versión ni `uv.lock`, así que **D-16 se respeta**.

**3. [Rule 3 - Blocking] `uv run pytest -q` a secas no es la reproducción del job `test`**

- **Found during:** Task 3
- **Issue:** el plan pide `uv run pytest -q` sobre el monorepo entero para confirmar que ningún otro paquete regresionó. La premisa es falsa: `testpaths` incluye `verification/`, que arrastra el rojo pre-existente de `HARN-VERIF-01`. Una corrida así sería roja por razones **completamente ajenas** a esta fase, y los summaries 43-01 y 43-02 ya registraron que además excede los 10 minutos.
- **Fix:** se reprodujo el job `test` **tal como CI lo corre** — los 6 paquetes con path explícito y cobertura, que son las 12 patas de la matriz en su versión py3.12. Los 6 en verde, 2168 tests. El rojo pre-existente se midió por separado (`19 failed, 3 passed, 19 errors`) y quedó documentado en `43-DISPOSITION.md` § 7.4 con su destino (Phase 45, HARN-04) en vez de confundirse con una regresión.
- **Files modified:** ninguno
- **Commit:** `7d3f2bd`

No se dispararon las reglas 1, 2 ni 4. No hubo gates de autenticación. No se instaló ni actualizó ninguna dependencia externa (**T-43-SC** confirmado no-op: `uv lock --check` exit `0`, `uv.lock` sin tocar).

## Issues Encountered

- **La verificación capture-vs-artefacto produjo una coincidencia que hubo que investigar antes de descartar.** El primer pase reportó `2026-08-31` como valor del crudo presente en el artefacto. No era una fuga: `maturity` vale exactamente la fecha de la corrida en las 50/50 filas, y el artefacto usa esa fecha sólo como fecha de lectura en prosa. Se resolvió documentando la colisión **en el propio artefacto** en vez de silenciarla, porque un lector que repita la verificación se va a topar con la misma coincidencia.
- **`PIPESTATUS` no funciona en el shell de esta sesión** (zsh), así que el primer intento de capturar exit codes de los pasos del job `lint` los devolvió vacíos. Se rehizo capturando `$?` directamente por comando. Sin efecto sobre los resultados; los 9 exit codes de la tabla están medidos.

## Verificacion final

| Gate | Comando | Resultado |
|---|---|---|
| Docstring reconciliado | `'DELIBERATELY' in doc`, `'SHAPE-MD-REF-33' in doc` | `False` / `False` |
| Resto del docstring intacto | `all(t in doc for t in ('segments','received_at'))` | `True` |
| `parse_instruments_response` field-agnostic | `'instrumentType' in doc` | `False` (intacto, no requiere cambio) |
| Artefacto existe y es sustantivo | `wc -l 43-DISPOSITION.md` | **592** líneas (mínimo del plan: 90) |
| Tabla `Instrument` | filas de datos | **12** |
| Tabla `Segment` | filas de datos | **5** |
| Tabla HARN-02 | filas de datos | **5** |
| Disposición `alias aditivo` presente | `grep -c 'alias aditivo'` | `3` (≥ 1) |
| Backlog del driver | `grep -c 'main_market_data.py' ROADMAP.md` | `3` (≥ 1) |
| ROADMAP sin pérdidas | `git diff ROADMAP.md \| grep -c '^-.*### Phase'` | `0` (y `0` líneas borradas **en total**) |
| Alcance del Task 2 | `git status --porcelain packages/ main_market_data.py .planning/verification/` | sin salida |
| Sin borrados accidentales | `git diff --diff-filter=D --name-only` sobre los 3 commits | sin salida |
| Sin untracked | `git status --porcelain \| grep '^??'` | sin salida |

## Seguimiento marcado — NO corregido acá

1. **`main_market_data.py:1541-1542`** — dereferencia `Segment.marketSegmentId`, removido por D-06. **Disposición escrita: no se corrige acá** (D-16 lockea el alcance a `models.py` + tests + el docstring de D-14). Registrado como **`DRV-MD-SEG-43`** en `ROADMAP.md` § Backlog, candidato Phase 44 o 45, con la medición de por qué ningún gate lo detecta (mypy `files` lista seis rutas `packages/*/src` y el driver vive en la raíz; pre-commit scoped a `^packages/.*/src/`; el lock AST no resuelve atributos) y la prueba de que **sí** es detectable apuntando mypy a mano: `main_market_data.py:1542: error: "Segment" has no attribute "marketSegmentId" [attr-defined]`. Corrección estimada: 2 líneas, sin lógica.
2. **`FeedSubscription` ausente del `__all__` del paquete** — sus 15 campos quedan fuera del escaneo de `check_surface_types.py`, confirmado por el delta +10 del contador. **Disposición: no se corrige acá** (D-16). Registrado como **`SURF-MD-FEEDSUB-43`**, candidato Phase 44.

## Known Stubs

Ninguno. Este plan no agrega código de producción: produce evidencia. Toda afirmación del artefacto llega con el comando que la mide y su salida pegada; no hay ninguna sección con contenido diferido ni placeholder.

## Threat Flags

Ninguna superficie de seguridad nueva. Disposición del registro STRIDE del plan:

- **T-43-11** (Information Disclosure — transcripción del capture) — **mitigado y VERIFICADO PROGRAMÁTICAMENTE**: 69 valores escalares comprobados, una coincidencia benigna y explicada (la fecha de la corrida), cero valores de fila transcritos.
- **T-43-12** (Repudiation — prosa histórica de `ROADMAP.md`) — **mitigado**: `SHAPE-MD-REF-33` y `TYP-MD-EXTRA-33` se **anotaron** con el resultado medido; `git diff` sobre `ROADMAP.md` muestra **0 líneas borradas**. El newline de los dos planes de fases anteriores no altera un solo carácter de contenido.
- **T-43-13** (Tampering — reemplazo de archivo completo en `ROADMAP.md`) — **mitigado**: se usó `Edit` acotado en las tres ediciones; `grep -c '^-.*### Phase'` sobre el diff = `0`.
- **T-43-14** (Elevation of Privilege — relajar un gate) — **mitigado**: cero aserciones relajadas, cero tests renombrados, la tabla de exenciones de `check_surface_types.py` **sin ensanchar**. El único gate que estaba rojo se corrigió en su **causa raíz** (el newline que el hook exige), no en su aserción.
- **T-43-15** (Tampering — publicación accidental) — **mitigado**: los tres sitios de versión en `0.6.0` sin cambio, `uv.lock` sin modificar, `release.yml` y `README.md` ausentes del diff acumulado.
- **T-43-SC** (instalaciones de paquetes) — **accept, no-op verificado**: cero paquetes externos instalados en toda la fase; `uv lock --check` exit `0`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **La Phase 43 queda cerrada.** Los 5 criterios de éxito del ROADMAP tienen su evidencia en `43-DISPOSITION.md`: criterio 1 § 1, criterio 2 § 2, criterio 3 § 3, criterio 4 § 3 (cierre) y criterio 5 §§ 4 y 7.
- **La Phase 44 (release 0.7.0) recibe tres entradas concretas:** el bump en los tres sitios de versión (hoy `0.6.0`, intactos), la tabla de migración vieja→nueva campo por campo que su criterio 3 exige —ya escrita en `43-DISPOSITION.md` § 1, lista para transcribir al `README.md`—, y los dos ítems de backlog `DRV-MD-SEG-43` y `SURF-MD-FEEDSUB-43`, que son candidatos naturales porque esa fase ya toca `__init__.py` y el paquete.
- **La Phase 45 (limpieza del harness) recibe** `DRV-MD-SEG-43` como alternativa de destino y la confirmación medida de que `HARN-VERIF-01` sigue exactamente en su baseline (`19 failed / 19 errors`), sin haberse movido en esta fase.
- **Nada quedó publicado.** La corrección de forma está en `main` y **no** en un release; el consumidor todavía instala `0.6.0`.

## Self-Check: PASSED

- `43-DISPOSITION.md` existe en disco (592 líneas).
- `_core.py`, `ROADMAP.md`, `41-06-PLAN.md` y `42-05-PLAN.md` existen y están modificados según lo descrito.
- Los 3 hashes de commit (`5a30fd9`, `0a3296a`, `7d3f2bd`) existen en el historial de git.
- Los 3 commits no borran ningún archivo tracked y no dejan ningún archivo untracked.

---
*Phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr*
*Completed: 2026-09-01*
