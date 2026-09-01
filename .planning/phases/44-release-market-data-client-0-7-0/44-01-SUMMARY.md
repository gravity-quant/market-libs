---
phase: 44-release-market-data-client-0-7-0
plan: 01
subsystem: infra
tags: [release, versioning, changelog, uv-lock, ci-mirror, market-data-client, git-branch]

# Dependency graph
requires:
  - phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr
    provides: "Instrument/Segment reconciliados contra el wire fresco; FeedSubscription en models.__all__; los 4 gates de CI verdes"
provides:
  - "market-data-client en 0.7.0 en los 4 sitios de versión (pyproject, __version__, 2 líneas de install del README)"
  - "market_data_client.FeedSubscription re-exportado desde la raíz del paquete (import binding + __all__) — superficie 186 → 187 nombres"
  - "Sección `### v0.7.0` del changelog con dos tablas de migración separadas (Instrument / Segment) + el flip de truthiness medido"
  - "uv.lock refrescado por un único run, churn exacto 1 1, registrando el member en 0.7.0"
  - "Branch pública nueva milestone/v1.8-cierre-deuda-post-v1.7 en origin, fast-forward, con los 94 commits pendientes del milestone"
affects: [44-02 (PR + gate de merge), 44-03 (tag + gate de publicación), 45 (limpieza del harness, DRV-MD-SEG-43)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Immutabilidad de workflow por identidad de digest sha256 entre refs (NO por diff contra el tag previo)"
    - "Scope de aserción por PLAN_BASE, no por origin/main...HEAD, en una rama con commits de fases anteriores del mismo milestone"

key-files:
  created:
    - .planning/phases/44-release-market-data-client-0-7-0/44-01-SUMMARY.md
  modified:
    - packages/market-data-client/pyproject.toml
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/README.md
    - uv.lock

key-decisions:
  - "El baseline `origin/main...HEAD` de las aserciones de alcance del plan es incorrecto por construcción en este milestone: ci.yml (Phase 42, 7cc103a) y main_market_data.py fueron modificados por commits pendientes ANTERIORES a esta fase. Se re-ancló a PLAN_BASE=bf606ba, más la aserción origin/main-scoped sobre release.yml específicamente, que sí es satisfacible y es el reclamo real de D-02."
  - "PUB-01 NO se marcó completo en REQUIREMENTS.md: el requisito exige la release publicada tras dos gates humanos, y este plan no publica, no mergea y no taggea. La marca corresponde a 44-03."
  - "El commit de SUMMARY/metadata se ordenó ANTES del push, de modo que el push es uno solo, el árbol queda limpio y HEAD == origin/branch — precondición de 44-02."
  - "Branch elegida: milestone/v1.8-cierre-deuda-post-v1.7 (patrón milestone/vX.Y-slug, precedentes #12 y #15)."

patterns-established:
  - "Aserción positiva por conteo en el gate de superficie (187 nombres), nunca por `0 violations` a secas"
  - "uv sync obligatorio entre uv lock y el mirror local, para que test_dunder_version_matches_installed_distribution_metadata lea un dist-info regenerado"

requirements-completed: []

# Metrics
duration: 6 min
completed: 2026-09-01
status: complete
---

# Phase 44 Plan 01: Preparación local de la release 0.7.0 Summary

**`market-data-client` queda en `0.7.0` en los cuatro sitios de versión, con `FeedSubscription` re-exportado (superficie 186 → 187), un changelog `### v0.7.0` de dos tablas de migración separadas, `uv.lock` refrescado por un único run con churn `1 1`, los 15 checks de CI espejados en verde localmente y la branch pública `milestone/v1.8-cierre-deuda-post-v1.7` empujada por fast-forward — sin PR, sin tag y sin merge.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-09-01T10:12:06Z
- **Completed:** 2026-09-01T10:18:30Z
- **Tasks:** 3
- **Files modified:** 4 (+1 SUMMARY creado)

## Accomplishments

- Los 4 sitios de versión pasan de `0.6.0` a `0.7.0`, cada uno verificado con el lector que le corresponde.
- `FeedSubscription` deja de ser un hueco de superficie: importado **y** en `__all__`, resuelto en runtime.
- Changelog `### v0.7.0` con **dos** tablas separadas y el flip de truthiness de `Segment` en la dirección **medida**.
- `uv.lock` refrescado una sola vez, con churn exacto `1 1`, y entorno re-sincronizado.
- Los 15 checks de CI espejados localmente en verde (2168 tests de paquete + 150 de la allowlist de `verification/`).
- `release.yml` probado byte-idéntico por sha256 entre `HEAD`, `origin/main` y `market-data-client-v0.6.0`.
- Scan de credenciales limpio sobre el diff completo que la branch publica.
- Branch nueva creada y empujada por fast-forward simple.

## Task Commits

1. **Task 1a: bump de los 4 sitios de versión** — `9e65699` (chore)
2. **Task 1b: fold del export de FeedSubscription** — `f28fc4a` (fix)
3. **Task 2: changelog v0.7.0 con las dos tablas de migración** — `70c494d` (docs)
4. **Task 3: refresco único de uv.lock** — `e3f55f1` (chore)

**Plan metadata:** commit `docs(44-01)` (este SUMMARY + STATE.md + ROADMAP.md)

## Transiciones de versión — los 4 sitios (D-01)

| # | Sitio | Antes | Ahora | Lector de la aserción |
|---|-------|-------|-------|------------------------|
| 1 | `packages/market-data-client/pyproject.toml:3` | `version = "0.6.0"` | `version = "0.7.0"` | el propio awk de `release.yml`: `awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'` → `0.7.0` |
| 2 | `src/market_data_client/__init__.py` (última línea) | `__version__ = "0.6.0"` | `__version__ = "0.7.0"` | `grep -qx` |
| 3 | `README.md` línea de install por git | `…@market-data-client-v0.6.0#subdirectory=…` | `…@market-data-client-v0.7.0#…` | conteo exacto |
| 4 | `README.md` línea del wheel (**dos** sustituciones) | `…/download/market-data-client-v0.6.0/market_data_client-0.6.0-py3-none-any.whl` | `…/download/market-data-client-v0.7.0/market_data_client-0.7.0-py3-none-any.whl` | conteo exacto |

Conteos medidos: `grep -c 'market-data-client-v0.7.0'` = **2**, `grep -c 'market_data_client-0.7.0-py3-none-any.whl'` = **1**, y supervivientes de la versión previa por encima de `## Changelog` = **0** (grep region-scoped, porque la sección nueva nombra legítimamente `0.6.0` en la etiqueta de su columna "Antes"). El defecto de la Phase 34 —changelog en la versión nueva con comando de install pineado a la vieja— no se repitió.

## Gate de superficie — conteos literales (D-05, D-11)

Baseline, medido **antes** de cualquier edit:

```
surface types: 6 packages, 186 `__all__` names, 337 definitions scanned, 452 fields scanned,
13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1),
0 violations
```

Post-fold, medido inmediatamente después del edit y antes de todo commit:

```
surface types: 6 packages, 187 `__all__` names, 337 definitions scanned, 467 fields scanned,
13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1),
0 violations
```

**186 → 187 nombres de `__all__`**, exactamente +1, aserción por conteo positivo y no por `0 violations`. `fields scanned` sube 452 → 467 (+15): los 15 campos de `FeedSubscription`, que antes no entraban al scan porque la clase no estaba en la superficie del paquete. El fold son **dos** edits (bloque de import + `__all__`), no uno: agregar sólo a `__all__` habría dejado un atributo no ligado. Verificado en runtime: `m.FeedSubscription is not None`, `m.__all__ == sorted(m.__all__)`, 54 nombres en el `__all__` del paquete.

`check_uniform_structure.py` y `surface_parity.py`: ambos verdes (el segundo silencioso en éxito).

## `uv.lock` — refresco único y churn medido (D-02)

`git show --numstat --format= e3f55f1 -- uv.lock`:

```
1	1	uv.lock
```

Una inserción, una deleción — la línea de versión del workspace member y nada más. Ninguna dependencia de terceros se re-resolvió. Commits que tocan `uv.lock` en `origin/main..HEAD`: **1**. `uv lock --check` sale 0. La línea siguiente a `name = "market-data-client"` lee `version = "0.7.0"`.

**Nota de honestidad sobre "exactamente un `uv lock`":** `uv run` hace un lock+sync implícito, así que el archivo ya estaba refrescado (con el mismo churn `1 1`) cuando se ejecutaron los gates del Task 1. El `uv lock` explícito del Task 3 corrió igual y fue un no-op (`Resolved 48 packages in 2ms`, sin cambios adicionales). Lo que D-02 protege se cumple íntegro: el refresco ocurrió **después** de bumpear los 4 sitios (nunca antes, que es lo que habría regenerado el lock en `0.6.0` y roto el check 1 de 15), hubo **un solo** commit tocando el lock, y el churn fue exactamente `1 1`.

## `uv sync` posterior al lock y la identidad de tres vías (RESEARCH Pitfall 3)

`uv sync --all-packages --all-extras --dev` corrió después del commit del lock y **antes** del mirror. El dist-info stale era real y se observó en la salida:

```
- market-data-client==0.6.0 (from file:///…/packages/market-data-client)
+ market-data-client==0.7.0 (from file:///…/packages/market-data-client)
```

Aserción posterior, exit 0:

```
from importlib.metadata import version; import market_data_client
assert version("market-data-client") == market_data_client.__version__ == "0.7.0"
→ three-way identity OK: metadata= 0.7.0 dunder= 0.7.0
```

Sin este sync, `test_dunder_version_matches_installed_distribution_metadata` habría dado un rojo local-only contra un CI verde, invitando a un "fix" espurio sobre un archivo ya correcto.

## Mirror local de CI — los 15 checks

Job `lint` (9 steps): `uv lock --check` ✅ · `ruff check .` ✅ · `ruff format --check .` (279 archivos) ✅ · `lint-imports` (5 contratos kept, 0 broken) ✅ · grep de logging sobre `packages/*/src/` sin match ✅ · `check_decode_intactness.py` (checks A–D) ✅ · `check_uniform_structure.py` ✅ · `check_surface_types.py` (187 nombres) ✅ · allowlist de `verification/` **re-derivada de `ci.yml` en tiempo de ejecución**: 13 archivos, el último `test_literal_census_venue_gate.py`, **150 passed** ✅.

Job `pre-commit`: 9 hooks, todos Passed, **cero reescrituras de archivo**.

Job `typecheck`: `uv run mypy` → `Success: no issues found in 75 source files`; `uv run mypy packages/<pkg>/tests` verde en los 6 paquetes (14/5/29/18/21/36 archivos).

Job `test`: `uv run pytest packages/<pkg> -q` en los 6 paquetes — higyrus 303, wallets 10, matriz 609, iol 311, ámbito 208 (+1 deselected), market-data 727. **2168 passed, 0 failed.**

**En ningún momento se corrió un `uv run pytest` pelado** (el `testpaths` raíz arrastra `verification/` entero, con fallas pre-existentes fuera de alcance — backlog `HARN-VERIF-01`).

## Inmutabilidad de `release.yml` (D-02, séptima reutilización sin edit)

sha256 idéntico en las tres refs — `sort -u` devuelve **una** línea:

```
HEAD                      7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
origin/main               7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
market-data-client-v0.6.0 7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113
```

Commits que tocan `release.yml` en `origin/main..HEAD`: **ninguno**. Archivos de `.github/workflows/` tocados por **este plan**: **ninguno**. Se usó la forma de identidad de digest y **no** la forma Phase-34 de diff contra el tag previo, que es stale-by-construction (ver Deviación 1).

## Scan de credenciales (T-44-02)

Sobre el diff completo `origin/main...HEAD` que la branch publica:

- Tokens con forma JWT (`eyJ[A-Za-z0-9_-]{20,}`): **sin hallazgos**
- Asignaciones estilo `client_secret` con valor de 20+ caracteres: **sin hallazgos**
- Archivos trackeados cuyo componente de path sea `.env`: **ninguno** (los 6 `.env.example` sí están trackeados, como corresponde)

Ningún valor, token OAuth de `gh` ni clave SSH fue impreso en ningún momento. `gh auth status` se usó sólo para confirmar la cuenta activa.

## Branch y conteo re-derivado (D-07, D-10)

- Branch creada con `git checkout -b`: **`milestone/v1.8-cierre-deuda-post-v1.7`**. No existía ninguna `milestone/v1.8-*` en `origin` (las únicas presentes eran `milestone/v1.5-mutations` y `milestone/v1.7-nobj-null-objects`).
- `main` local quedó en el mismo SHA; no se hizo `git push origin main` en ningún momento.
- Push: `git push origin milestone/v1.8-cierre-deuda-post-v1.7`, fast-forward simple, por nombre. **Sin** `--force`, **sin** `--force-with-lease`, **sin** rebase, **sin** merge de `origin/main`.

**Conteo de commits pendientes RE-DERIVADO en vivo** con `git rev-list --count origin/main..HEAD`:

> **94** al momento de crear la branch · **95** tras el commit de metadata de este plan (el que incluye este SUMMARY), que es el estado efectivamente empujado.

Los literales **84** (CONTEXT.md D-07), **86** (44-RESEARCH.md) y **88** (momento de escritura del plan) quedan **todos superados**. `HEAD..origin/main` = 0, así que el push es fast-forward puro. Esta es exactamente la deriva que D-10 existe para prevenir — y la razón por la que 44-02 debe volver a re-derivar el valor en vivo en vez de tomar el 95 de acá.

## Decisions Made

- **Baseline de las aserciones de alcance re-anclado a `PLAN_BASE`** (ver Deviación 1).
- **`PUB-01` queda `Pending`** hasta 44-03 (ver Deviación 2).
- **Orden commit-de-metadata → push** en vez de push → commit, para que haya un solo push, el árbol quede limpio y `HEAD == origin/branch` — precondición explícita de 44-02. Los artefactos de `.planning/` viajan con la release, como en toda release previa de este repo (acción (g) del plan).
- **Nombre de branch** `milestone/v1.8-cierre-deuda-post-v1.7`, dentro del patrón `milestone/vX.Y-slug` (discreción de Claude por CONTEXT.md).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] El baseline `origin/main...HEAD` de tres aserciones de alcance es insatisfacible por construcción**

- **Found during:** Task 1 (gate de acceptance criteria)
- **Issue:** El plan exige que `git diff --name-only origin/main...HEAD -- main_market_data.py .github/workflows uv.lock` esté vacío. Medido, devuelve `.github/workflows/ci.yml` y `main_market_data.py` — **no** por nada que haga este plan, sino porque ambos fueron modificados por commits pendientes de fases **anteriores** del mismo milestone v1.8: `ci.yml` por `7cc103a` (Phase 42, el mismo commit que agregó la 13ª entrada a la allowlist de `verification/` que el propio plan manda re-derivar), y `main_market_data.py` por un commit de la Phase 41/43. Con 94 commits pendientes, `origin/main...HEAD` mide el milestone entero, no este plan. La aserción se contradice con el propio texto del plan.
- **Fix:** Re-anclar esas tres aserciones a `PLAN_BASE=bf606ba` (el HEAD previo al plan), que es el scope que la intención expresa —"este plan no tocó nada más"— y que da vacío. Se **conservó** además la aserción origin/main-scoped sobre `release.yml` específicamente, que sí es satisfacible (cero commits) y es el reclamo real de supply-chain de D-02, más la identidad de digest sha256 entre las tres refs.
- **Files modified:** ninguno — es una corrección de la aserción, no del código
- **Verification:** `git diff --name-only bf606ba..HEAD -- main_market_data.py .github/workflows uv.lock` → vacío al cierre del Task 1 y del Task 2; `git log --oneline origin/main..HEAD -- .github/workflows/release.yml` → vacío; digest sha256 idéntico en las 3 refs. `main_market_data.py` sigue intacto por este plan (D-06 respetado, `DRV-MD-SEG-43` diferido a la Phase 45).
- **Committed in:** n/a (aserción, no artefacto)

**2. [Rule 1 - Bug] `requirements mark-complete PUB-01` marcó como cumplido un requisito que este plan no cumple**

- **Found during:** cierre del plan (state updates)
- **Issue:** El paso estándar de GSD toma el campo `requirements:` del frontmatter (`[PUB-01]`) y marcó PUB-01 como `[x]` / `Complete` en `REQUIREMENTS.md`. Pero PUB-01 dice literalmente *"Publicar `market-data-client-v0.7.0` … doble gate humano independiente"*: este plan no publica, no mergea, no taggea y no atraviesa ningún gate. Dejarlo marcado le diría a una auditoría posterior que la release ya salió.
- **Fix:** Revertido con `git checkout -- .planning/REQUIREMENTS.md`. PUB-01 vuelve a `Pending`. La marca corresponde a 44-03, que es el plan que efectivamente publica.
- **Files modified:** `.planning/REQUIREMENTS.md` (revertido a su estado previo)
- **Verification:** `grep -n "PUB-01" .planning/REQUIREMENTS.md` → `- [ ] **PUB-01**…` y `| PUB-01 | Phase 44 | Pending |`
- **Committed in:** n/a (revertido, no committeado)

**3. [Rule 3 - Blocking] `record-metric` con args posicionales devolvió error de argumentos**

- **Found during:** cierre del plan
- **Issue:** `state.record-metric "44" "01" "6 min" "3" "4"` devolvió `{"error": "phase, plan, and duration required"}`; el handler espera flags con nombre.
- **Fix:** Re-ejecutado como `--phase 44 --plan 01 --duration "6 min" --tasks 3 --files 4`.
- **Files modified:** `.planning/STATE.md`
- **Verification:** salida `{"phase": "44", "plan": "01", "duration": "6 min"}`
- **Committed in:** commit de metadata del plan

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** Ninguna toca el artefacto de release. Las dos primeras **impiden** afirmaciones falsas (un alcance mal medido y un requisito prematuramente cerrado); la tercera es mecánica de tooling. Cero scope creep: no se tocó `main_market_data.py`, ni ningún workflow, ni ningún otro paquete.

## Issues Encountered

Ninguno bloqueante. El único hallazgo notable es que el dist-info stale de `RESEARCH` Pitfall 3 **era real** y se observó en vivo (`market-data-client==0.6.0` desinstalado, `0.7.0` instalado): sin el `uv sync` intermedio, el test de metadata habría dado un rojo local-only.

## Nota sobre lo que este plan NO hizo

Explícitamente, y por diseño (D-08 — todo lo irreversible queda tras su propio gate humano):

- **No se abrió ningún PR.** `gh pr list --state open --base main` → `0`.
- **No se creó ningún tag.** `git tag -l 'market-data-client-v0.7.0'` → vacío.
- **No se pusheó ningún tag.**
- **No se mergeó nada.**
- **No se pusheó a `main`.**
- **No se reescribió historia** (sin `--force`, sin `--force-with-lease`, sin rebase).

Todo lo hecho acá es reversible con un commit, o borrando una branch que no mergea ni publica nada. Las dos operaciones irreversibles siguen íntegramente gateadas en 44-02 (merge) y 44-03 (tag/publicación).

## User Setup Required

Ninguno pendiente. El único requisito externo del plan —autenticación de `gh`/git para el push de la branch— ya estaba satisfecho: `gh auth status` confirma la cuenta `sebadlf` activa en github.com y el remote `origin` resuelve por SSH. Ningún token fue impreso.

## Next Phase Readiness

- Árbol limpio, `HEAD == origin/milestone/v1.8-cierre-deuda-post-v1.7`, los 15 checks verdes localmente: **44-02 puede abrir el PR**.
- 44-02 debe re-derivar en vivo el número de PR y el conteo de checks (15/15 por conteo positivo, D-11), y verificar que su propio checkpoint esté escrito literalmente como `gate="blocking-human"`.
- 44-03 es el plan que debe marcar `PUB-01` completo, no antes.
- `DRV-MD-SEG-43` (`main_market_data.py`) sigue diferido a la Phase 45, intacto y nombrado.

## Self-Check: PASSED

Archivos declarados, verificados en disco con `[ -f ]`: `44-01-SUMMARY.md`, `pyproject.toml`, `__init__.py`, `README.md`, `uv.lock` — los 5 FOUND.

Commits declarados, verificados con `git log --oneline --all`: `9e65699`, `f28fc4a`, `70c494d`, `e3f55f1`, `08c9681` — los 5 FOUND.

Gate final de acceptance criteria del Task 3, salida literal:

```
lock_member_version=0.7.0 OK
lock_commits=1
lock_churn=[1 1]
release_yml_digest_identity=OK
this_plan_touched_no_workflow_no_driver=OK
credential_scan=CLEAN
branch=milestone/v1.8-cierre-deuda-post-v1.7  HEAD==origin/milestone/v1.8-cierre-deuda-post-v1.7
tree=CLEAN
tag_0.7.0=ABSENT
open_prs=0
PASS
```

---
*Phase: 44-release-market-data-client-0-7-0*
*Completed: 2026-09-01*
