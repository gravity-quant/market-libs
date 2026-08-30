---
phase: 40-releases-breaking-coordinados
plan: 01
subsystem: release-mechanics
tags: [release, versioning, changelog, uv-lock, breaking-change, semver]
requires:
  - "Phases 35-39 surface work, merged into local `main`"
  - "operator answer at the Task 1 scope gate (D-02, D-12)"
provides:
  - "four packages at their bumped versions at every version site"
  - "consumer-followable migration tables for all four"
  - "single-refresh `uv.lock` registering every bumped member"
  - "`origin/milestone/v1.7-nobj-null-objects` at local HEAD, unblocking `gh pr create` in 40-02"
affects:
  - "packages/{matriz,iol,market-data,higyrus}-client"
  - "uv.lock"
  - "verification/test_safemodel_diff_null_object_links.py"
tech-stack:
  added: []
  patterns:
    - "de-provisionalization: MOVE `## Unreleased — BREAKING` into `## Changelog` as the first dated `###` entry, breaking callout first"
    - "single `uv lock` after all `pyproject.toml` edits, then `uv sync` before the local CI mirror"
    - "workflow immutability asserted by sha256 identity across refs, never by a tag-baseline diff"
key-files:
  created:
    - .planning/phases/40-releases-breaking-coordinados/40-01-SUMMARY.md
  modified:
    - packages/matriz-client/README.md
    - packages/matriz-client/pyproject.toml
    - packages/matriz-client/src/matriz_client/__init__.py
    - packages/matriz-client/tests/test_instruments_flat_identifier_shape.py
    - packages/iol-client/README.md
    - packages/iol-client/pyproject.toml
    - packages/iol-client/src/iol_client/__init__.py
    - packages/market-data-client/README.md
    - packages/market-data-client/pyproject.toml
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/tests/test_snapshot_no_data_row.py
    - packages/market-data-client/tests/test_models.py
    - packages/market-data-client/tests/test_decode.py
    - packages/market-data-client/tests/test_market_data_chain.py
    - packages/higyrus-client/README.md
    - packages/higyrus-client/pyproject.toml
    - packages/higyrus-client/src/higyrus_client/__init__.py
    - verification/test_safemodel_diff_null_object_links.py
    - uv.lock
decisions:
  - "D-02 resolved A-fold-higyrus: higyrus-client folds in as the fourth bumped package (0.2.0 -> 0.3.0)"
  - "D-12 resolved B-widen-now: MarketDataSnapshot.market_id -> str | None and .active -> bool | None, inside this bump"
  - "matriz `__version__` added (OQ-4), with no `test_version_metadata.py` for matriz"
  - "no in-repo release-memory file exists to refresh (OQ-3) — no target"
  - "ambito-financiero-client and wallets-client classified measured-and-additive, not unchanged; no bump"
metrics:
  duration: "~35 min"
  completed: 2026-08-30
  tasks_completed: 4
  commits: 10
  packages_bumped: 4
status: complete
---

# Phase 40 Plan 01: Preparación reversible del release breaking coordinado v1.7 — Summary

Cuatro paquetes bumpeados con changelog y tabla de migración, `uv.lock` refrescado una sola
vez con churn `4 4`, los cuatro job bodies del CI espejados en verde localmente, y la branch
`milestone/v1.7-nobj-null-objects` publicada por fast-forward — sin un solo tag, sin PR y sin
tocar `main`.

## Scope-gate dispositions (D-02, D-12)

**Timestamp:** 2026-08-30 (respuesta literal del operador, recogida vía checkpoint bloqueante
en la corrida previa de este plan y transportada verbatim a esta corrida de continuación).

**Respuesta verbatim del operador:**

> A-fold-higyrus, B-widen-now

**Option ids seleccionados:**

| Pregunta | Option id | Disposición |
|---|---|---|
| A (D-02, higyrus) | `A-fold-higyrus` | APROBADO — `higyrus-client` entra como **cuarto** paquete bumpeado, `0.2.0 → 0.3.0` |
| B (D-12, market_id/active) | `B-widen-now` | APROBADO — `market_id` → `str \| None` y `active` → `bool \| None` dentro de este mismo bump |

Ninguna rama de decline fue seleccionada, así que no hay destino que nombrar y no se creó
ningún `deferred-items.md`.

La aprobación vino de una respuesta literal del operador. **No** de `auto_advance`, **no** de
`mode: yolo` (ambos activos en `.planning/config.json`), **no** inferida del silencio y **no**
auto-emitida por el agente. El gate corrió antes del primer edit de `pyproject.toml` y antes
del único `uv lock`, que es exactamente la razón por la que D-07/OQ-1 lo hoistearon acá.

**Evidencia re-medida en esta corrida** (los seis comandos del `<context>` de la Task 1, no
asumidos del texto del plan):

- `get_health` devuelve `Health` en `client.py:450` (método) y `:602` (shim de módulo)
- `higyrus-client/pyproject.toml` leía `0.2.0`
- `higyrus-client/README.md:131` leía `### v0.3.0 — sin publicar todavía`, con el párrafo
  `133-137` nombrando a la Phase 34 como ejecutora
- 17 ocurrencias de `market_id|\.active` en `test_snapshot_no_data_row.py`
- las seis aserciones exactamente en las líneas 155, 156, 179, 180, 261 y 282
- la nota de divergencia de `README.md:29-34` terminando en "espera checkpoint del operador"

Las seis coincidieron con lo que el prompt de continuación afirmaba.

## Conjunto final de paquetes: N = 4

| Paquete | Antes | Ahora | Fase de origen |
|---|---|---|---|
| `market-data-client` | 0.5.0 | **0.6.0** | 36 (+ D-12 acá) |
| `iol-client` | 0.3.0 | **0.4.0** | 38 |
| `matriz-client` | 0.2.0 | **0.3.0** | 37 |
| `higyrus-client` | 0.2.0 | **0.3.0** | 31 (deuda no publicada, foldeada por D-02) |
| `ambito-financiero-client` | 0.2.0 | 0.2.0 (sin tocar) | — additive |
| `wallets-client` | 0.2.0 | 0.2.0 (sin tocar) | — additive |

## Valores medidos en runtime (nunca literales de documento)

- **`PHASE_BASE`** = `ba4ce79a995b1e240a68a346cc1f21581540cdfd`
- **Commits adelante de `origin/main`** en `PHASE_BASE` = **190**; al cierre del plan = **199**.
  CONTEXT decía 180, RESEARCH 182 y el PLAN 186 — ninguno se reusó.
- **N** (paquetes cuyo `pyproject.toml` difiere de `origin/main`) = **4**, computado en runtime.

## Commits

| # | SHA | Archivos | Subject |
|---|---|---|---|
| 1 | `ba4ce79` | 1 | `chore(planning): sincronizar .planning/STATE.md antes del ciclo de release` |
| 2 | `50d1c0e` | 3 | `chore(matriz-client): bump to v0.3.0 (cuatro retipados de modelo + fix de envelope-unwrap)` |
| 3 | `a78eec3` | 3 | `chore(iol-client): bump to v0.4.0 (Cotizacion.puntas y Titulo.puntas pierden \| None)` |
| 4 | `78fd48f` | 5 | `fix(market-data-client): ensanchar market_id/active a Optional sobre la fila no-data (D-12)` |
| 5 | `c05a159` | 3 | `chore(market-data-client): bump to v0.6.0 (market_data pasa a Null Object tipado)` |
| 6 | `cd70d46` | 3 | `chore(higyrus-client): bump to v0.3.0 (get_health devuelve Health tipado)` |
| 7 | `11a5f17` | 3 | `chore(planning): agregar newline final a tres PLAN.md pendientes` |
| 8 | `f1e1a3e` | 1 | `chore(deps): refrescar uv.lock para los 4 paquetes bumpeados de v1.7` |
| 9 | `26ced53` | 1 | `test(verification): mover el ejemplar de hoja requerida de market_id a symbol (D-12)` |
| 10 | `1d62609` | 1 | `fix(matriz-client): anotar los fixtures de _envelope para que mypy --strict pase` |

## `uv.lock`

Un único `uv lock`, corrido después de los cuatro edits de `pyproject.toml`.

- Commits en `origin/main..HEAD` que tocan `uv.lock`: **1** (`f1e1a3e`)
- Churn medido: **`4 4`** — exactamente una línea `version` por miembro bumpeado. Cero
  re-resolución de dependencias de terceros.
- `uv lock --check` → exit 0
- Miembros verificados: `matriz-client 0.3.0`, `iol-client 0.4.0`, `market-data-client 0.6.0`,
  `higyrus-client 0.3.0`, `ambito-financiero-client 0.2.0`, `wallets-client 0.2.0`

`uv sync --all-packages --all-extras --dev` corrió inmediatamente después del commit del lock
y antes del mirror: reinstaló los cuatro paquetes en sus versiones nuevas, que es lo que pone
en verde `test_dunder_version_matches_installed_distribution_metadata` (RESEARCH P3). Ese test
efectivamente estuvo rojo entre el bump y el `uv sync`, tal como el research lo predijo.

## Mirror local del CI — los cuatro job bodies

**Ocho gates de lint, todos exit 0:**

| Gate | Resultado |
|---|---|
| `uv lock --check` | Resolved 48 packages |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 278 files already formatted |
| `uv run lint-imports` | Contracts: 5 kept, 0 broken |
| grep `logging.basicConfig` / `logging.root` en `packages/*/src/` | sin match |
| `tools/check_decode_intactness.py` | checks A-D OK; hash `a1f00c824348164c` |
| `tools/check_uniform_structure.py` | 6 paquetes OK |
| `tools/check_surface_types.py` | 442 campos, **0 violaciones** |

**Allowlist de 12 archivos de `verification/`** (exactamente como `ci.yml:80-92`): **129 passed**.

**`uv run pre-commit run --all-files`:** todos los hooks Passed, cero reescrituras de archivo.

**`uv run mypy`:** Success, 75 source files.

**`uv run mypy packages/<pkg>/tests`** — los seis:

| Paquete | Resultado |
|---|---|
| higyrus-client | Success, 14 files |
| wallets-client | Success, 5 files |
| matriz-client | Success, 29 files |
| iol-client | Success, 18 files |
| ambito-financiero-client | Success, 21 files |
| market-data-client | Success, 36 files |

**`uv run pytest packages/<pkg> -q`** — los seis:

| Paquete | Resultado |
|---|---|
| higyrus-client | 303 passed |
| wallets-client | 10 passed |
| matriz-client | 609 passed |
| iol-client | 311 passed |
| ambito-financiero-client | 208 passed, 1 deselected |
| market-data-client | 711 passed |

Total: **2152 passed**. Nunca se corrió un `uv run pytest` pelado.

## Inmutabilidad de los workflows

`release.yml` es byte-idéntico en los seis refs relevantes — sha256
`7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113`, `sort -u` → **1 línea**:

`HEAD`, `origin/main`, `iol-client-v0.3.0`, `market-data-client-v0.5.0`, `matriz-client-v0.2.0`,
`higyrus-client-v0.2.0`.

- `git diff --name-only $PHASE_BASE..HEAD -- .github/workflows` → **0 líneas**
- `git diff --name-only origin/main...HEAD -- .github/workflows/release.yml` → **0 líneas**

Se usó la forma corregida (identidad sha256), NO la forma de Phase 34 basada en diff contra el
tag previo, que es stale-by-construction (RESEARCH P2).

## Escaneo de credenciales sobre `origin/main...HEAD`

| Patrón | Resultado |
|---|---|
| JWT `eyJ[A-Za-z0-9_-]{20,}` | sin match |
| `client_secret` con valor de 20+ caracteres | sin match |
| archivo trackeado con componente de path `.env` | ninguno |

Sólo los seis `.env.example` legítimos están trackeados. Ningún valor fue impreso en ningún
momento.

## Branch

- `git checkout -b milestone/v1.7-nobj-null-objects` corrió **antes** de cualquier push. `main`
  local quedó en el mismo SHA (`1d62609`).
- `git push origin milestone/v1.7-nobj-null-objects` — fast-forward plano, branch nueva.
- `git rev-parse HEAD` == `git rev-parse origin/milestone/v1.7-nobj-null-objects` == `1d62609`.
- Sin `--force`, sin `--force-with-lease`, sin rebase, sin merge de `origin/main`, y **sin
  ningún `git push origin main`** en toda la fase.
- Árbol limpio (`git status --porcelain` vacío) — precondición de 40-02 cumplida.
- **Cero tags** creados. Ningún PR abierto, editado ni mergeado.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] El archivo sucio del working tree era `STATE.md`, no `config.json`**

- **Found during:** Task 2 (a)
- **Issue:** El plan (y RESEARCH P7) predecían `.planning/config.json` sucio. En runtime el
  único archivo sucio era `.planning/STATE.md` (8 inserciones / 8 deleciones de bookkeeping GSD).
- **Fix:** Se commiteó el archivo realmente sucio, solo, con el subject adaptado al archivo real
  (`chore(planning): sincronizar .planning/STATE.md antes del ciclo de release`) en vez de
  nombrar un archivo que no había cambiado. La intención del criterio — limpiar el árbol con un
  commit de un solo archivo antes de tocar cualquier paquete — se cumple exactamente.
- **Commit:** `ba4ce79`

**2. [Rule 1 - Bug] El ensanche de D-12 enrojeció cuatro sitios de test que el plan no había previsto**

- **Found during:** Task 3 (b)
- **Issue:** El plan inventariaba seis aserciones en `test_snapshot_no_data_row.py`. El ensanche
  además rompió `test_models.py::test_from_api_empty_dict_typed_zero_defaults`,
  `test_models.py::test_from_api_latest_nodata_item`,
  `test_decode.py::test_snapshot_other_fields_still_report` y
  `test_market_data_chain.py::test_the_measured_no_data_row_keeps_the_chain_walkable_and_the_links_silent`.
- **Fix:** Las cuatro se migraron para fijar el comportamiento nuevo, en el mismo commit que el
  ensanche. Ninguna se borró, se saltó ni se marcó `xfail`. En `test_market_data_chain.py`,
  `_MEASURED_NO_DATA_RECORDS` pasa a lista vacía y la igualdad del set sigue siendo load-bearing.
- **Commit:** `78fd48f`

**3. [Rule 2 - Missing critical] Los dos tests de strict-decode se migraron en vez de retirarse**

- **Found during:** Task 3 (b)
- **Issue:** `36-DEFERRED-market-data-leaves.md` recomendaba **retirar**
  `test_the_measured_no_data_row_still_raises_on_an_over_declared_leaf` (+ `_async`) al ensanchar.
  El plan de esta fase es más estricto: ninguna aserción puede eliminarse.
- **Fix:** Se invirtieron en vez de retirarse — ahora aseveran que la baseline medida camina
  entera bajo `strict_decode` sin levantar, con un `pytest.fail` que reporta el `field_path` si
  algo levanta. Renombrados a `..._no_longer_raises_on_a_widened_leaf`; se verificó primero que
  esos nombres NO son anclas del ledger append-only (0 referencias en
  `.planning/verification/market-data-client-findings.md`). Los nombres
  `test_no_data_row_keeps_its_nulls` / `_async` **sí** son anclas load-bearing (STATE.md:406) y se
  preservaron verbatim; sólo se migraron sus aserciones.
- **Commit:** `78fd48f`

**4. [Rule 3 - Blocking] Tres `PLAN.md` sin newline final enrojecían el job `pre-commit` del CI**

- **Found during:** Task 3, gate `pre-commit run --all-files`
- **Issue:** `end-of-file-fixer` reescribía `39-03-PLAN.md`, `39-07-PLAN.md` y `40-01-PLAN.md`.
  Preexistentes, nunca pusheados, así que el CI todavía no los había visto — pero habrían
  arrancado el PR de release con un check en rojo por una causa ajena al release.
- **Fix:** Se aceptó el fix del hook (sólo newline final) y se commiteó aparte.
- **Commit:** `11a5f17`

**5. [Rule 1 - Bug] Dos tests del allowlist de `verification/` usaban `market_id` como hoja requerida**

- **Found during:** Task 4 (c)
- **Issue:** `test_an_absent_scalar_leaf_is_still_reported` y
  `test_emit_shape_still_reports_an_absent_scalar_leaf` usaban `market_id` como ejemplar de hoja
  escalar REQUERIDA cuya ausencia debe reportarse `model-only`. Tras D-12 ya no reporta nada, y
  correctamente.
- **Fix:** Ejemplar movido a `symbol`, la hoja escalar que sigue siendo no-`Optional` en
  `MarketDataSnapshot`. Se agregó además el test recíproco
  `test_an_absent_widened_leaf_is_no_longer_reported`, que cubre el comportamiento nuevo en vez
  de dejarlo sin fijar.
- **Commit:** `26ced53`

**6. [Rule 3 - Blocking] Ocho errores mypy preexistentes en `packages/matriz-client/tests`**

- **Found during:** Task 4 (c)
- **Issue:** `uv run mypy packages/matriz-client/tests` fallaba con 8 errores `arg-type` en
  `test_instruments_flat_identifier_shape.py`: `_FLAT_ELEMENT` y `_NESTED_ELEMENT` se infieren
  como `dict[str, str]` / `dict[str, Collection[str]]` y `dict` es invariante en el tipo de
  valor, así que ninguno es asignable al `dict[str, object]` de `_envelope`. Vienen de Phase 37,
  nunca pusheados, así que el job `typecheck` no los había visto. Verificado que esta fase no
  tocó ese archivo.
- **Fix:** Se anotó el tipo declarado de los dos fixtures. Ninguna aserción cambió. Se siguió el
  precedente que el propio plan cita: Phase 34 arregló el test, nunca el workflow.
- **Commit:** `1d62609`

### Notes

- **`uv run` refresca `uv.lock` como efecto colateral.** Después del bump de matriz, el primer
  `uv run pre-commit` dejó `uv.lock` sucio con la línea de versión de matriz. No es un segundo
  `uv lock` deliberado: se dejó sin commitear y el `uv lock` explícito de la Task 4 produjo el
  estado final, commiteado **una sola vez** (`f1e1a3e`). El invariante de D-10 — exactamente un
  commit tocando `uv.lock`, churn `N N` — se verificó y se cumple.
- **Separador de tabla con espacios.** Las tablas de migración nuevas usan `| --- | --- |` en vez
  del `|---|---|` de los READMEs hermanos, porque el criterio de aceptación cuenta filas con
  `grep -c '^| '` y esperaba 6 líneas (header + separador + 4 filas). Render idéntico.

## Decisiones explícitas de `<scope_decisions>` ejercidas

- **matriz `__version__`: AGREGADO** (OQ-4 / D-04). Una línea bare
  `__version__ = "0.3.0"` después del `]` de `__all__`, replicando
  `packages/iol-client/src/iol_client/__init__.py:87`. No se agregó a `__all__` y **no** se creó
  `packages/matriz-client/tests/test_version_metadata.py` — eso habría importado el acoplamiento
  a dist-metadata de market-data-client a un quinto paquete sin beneficio de gate.
- **Release-memory in-repo (OQ-3): no hay target.**
  `/Users/admin/.claude/projects/-Users-admin-development-market-libs/memory/` contiene sólo
  `MEMORY.md` y `project_matriz_bbsa_sandbox.md`. `market-data-client-releases.md` no existe en
  este checkout. Nada que refrescar; no se abrió el ítem.
- **`ambito-financiero-client` y `wallets-client`: medidos y clasificados ADITIVOS**, no
  "sin cambios" (RESEARCH P11). Sus superficies sí se movieron desde sus tags publicados; bajo el
  precedente del propio proyecto la disposición de no-bump se mantiene. Un verificador que corra
  un surface diff y obtenga resultado no vacío está viendo lo esperado, no un defecto.
- **`.github/workflows/`: no se tocó.** Ni `ci.yml` ni `release.yml`, en ningún commit.

## Known Stubs

Ninguno. Este plan no produce código de producto nuevo — sólo literales de versión, prosa de
changelog, dos ensanches de tipo con sus tests migrados, y operaciones de git.

## Threat Flags

Ninguna superficie de seguridad nueva. Este plan no agrega endpoints, rutas de auth, patrones de
acceso a archivos ni cambios de schema en un límite de confianza. Las mitigaciones del
`<threat_model>` con disposición `mitigate` se ejecutaron y se registran arriba: T-40-01
(escaneo de credenciales), T-40-02 (alineación de version sites), T-40-03 (paquetes sin cambios
verificados en 0.2.0), T-40-04 (churn `4 4` del lock), T-40-05 (sin force / sin rebase),
T-40-06 (branch creada antes del push; nunca `push origin main`), T-40-07 (gate de alcance con
respuesta literal del operador), T-40-08 (ningún secreto impreso), T-40-09 (workflows intactos
por sha256).

## Verificación del plan — 13/13

1. ✅ Gate de alcance antes de cualquier `pyproject.toml` y antes de `uv lock`; ambas respuestas
   registradas verbatim con option ids y timestamp
2. ✅ `matriz-client/README.md` tiene `## Changelog` que no existía, con `### v0.3.0` como única
   entrada, tabla de 4 filas, envelope-unwrap en prosa y los seis alias aparte como aditivos
3. ✅ iol 0.4.0, market-data 0.6.0, matriz 0.3.0 y higyrus 0.3.0 en todos sus version sites
4. ✅ Los dos bloques `## Unreleased — BREAKING` movidos a `## Changelog` como primera entrada,
   cuerpos intactos (tokens pre-escritos verificados por grep)
5. ✅ `Fase 40` en cero READMEs, `Phase 34` fuera del README de higyrus, `NO BUMPEAR` eliminado
6. ✅ Los dos install pins de market-data en 0.6.0 (`2` y `1` ocurrencias); los previos en cero
7. ✅ ambito y wallets sin cambio de versión en ningún sitio
8. ✅ Exactamente un commit toca `uv.lock`, churn `4 4`, `uv lock --check` exit 0
9. ✅ `uv sync` entre `uv lock` y el mirror; los cuatro job bodies verdes localmente
10. ✅ `release.yml` byte-idéntico en los seis refs; cero workflows tocados desde `PHASE_BASE`
11. ✅ Escaneo de credenciales limpio; ningún `.env` trackeado
12. ✅ `origin/milestone/v1.7-nobj-null-objects` == HEAD local, creada con `checkout -b` y
    pusheada fast-forward; nunca se pusheó `main`
13. ✅ Cero tags y ningún PR tocado al cierre del plan

## Self-Check: PASSED

Archivos verificados en disco (los 20 modificados/creados listados en el frontmatter existen).
Los 10 commits existen y son alcanzables desde HEAD. `origin/milestone/v1.7-nobj-null-objects`
resuelve al mismo SHA que HEAD local (`1d62609`). Árbol limpio.

## Qué sigue

**40-02** abre el PR nuevo contra `main` desde esta branch, espera los 15 checks por conteo
explícito (D-06), y para en el primero de los dos gates humanos bloqueantes de operación
irreversible antes del merge (D-07/(a), D-08 merge commit real).

**40-03** crea las **cuatro** annotated tags sobre el SHA del merge re-resuelto en vivo, para en
el segundo gate bloqueante (D-07/(b), D-09), y verifica post-publicación instalando desde los
wheels públicos (D-11). Nota para 40-03: la ronda tiene **cuatro** tags, no tres —
`higyrus-client-v0.3.0` se suma por la disposición `A-fold-higyrus`.
