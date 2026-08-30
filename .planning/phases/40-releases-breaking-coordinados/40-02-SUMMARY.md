---
phase: 40-releases-breaking-coordinados
plan: 02
subsystem: release-mechanics
tags: [release, pull-request, ci-gate, checkpoint, blocking-human, semver]
requires:
  - "plan 40-01 complete: four packages bumped, single `uv.lock` refresh, `origin/milestone/v1.7-nobj-null-objects` at local HEAD"
  - "authenticated `gh` CLI"
  - "operator go/no-go at the D-07(a) pre-merge gate — OUTSTANDING"
provides:
  - "gh-pr:15 — the single open release PR for v1.7 against `main`"
  - "a count-asserted 15/15 CI green gate on that PR"
affects:
  - "github.com/gravity-quant/market-libs PR #15"
tech-stack:
  added: []
  patterns:
    - "assert CI green by explicit positive count (total == 15, pass == 15, 2 matrix rows per bumped package), never by absence of the word `fail`"
    - "a blocking human gate on an irreversible operation is not satisfiable by `auto_advance`, yolo mode, silence, or agent self-issue"
key-files:
  created:
    - .planning/phases/40-releases-breaking-coordinados/40-02-SUMMARY.md
  modified: []
decisions:
  - "D-05 exercised as a CREATE: `gh pr create` (no v1.7 PR existed to edit) — PR #15"
  - "D-06 gate asserted by count: 15 total rows / 15 `pass` / 2 matrix rows for each of the FOUR bumped packages"
  - "PLAN assumption corrected by measurement: `.github/workflows/ci.yml` DOES appear in the PR diff — the delta comes from Phases 36-39, not Phase 40, and adds a step (not a job), so the 15-check invariant holds"
metrics:
  duration: "~4 min (to the checkpoint)"
  completed: null
  tasks_completed: 1
  tasks_total: 3
  commits: 0
status: blocked-on-checkpoint
---

# Phase 40 Plan 02: PR de release v1.7 + gate humano pre-merge — Summary (parcial, detenido en el checkpoint)

PR #15 abierto contra `main` desde `milestone/v1.7-nobj-null-objects`, con los 15 checks del CI
verificados **por conteo positivo explícito** (15 filas / 15 `pass` / 2 filas de matrix por cada
uno de los cuatro paquetes bumpeados). **Detenido en el gate humano bloqueante D-07(a) antes del
merge irreversible — el merge NO se ejecutó y no se auto-aprobó nada.**

## Estado del plan

| Task | Tipo | Estado |
|---|---|---|
| 1 — Crear el PR y asertar 15/15 por conteo | `auto` | ✅ COMPLETA |
| 2 — Gate humano bloqueante pre-merge (D-07a) | `checkpoint:human-verify` `gate="blocking"` | ⏸️ **DETENIDO — esperando respuesta literal del operador** |
| 3 — Merge con merge commit real (D-08, D-09) | `auto` | ⛔ NO EJECUTADA — depende de un "approved" explícito |

## Task 1 — PR creado y gate de CI asertado por conteo

### Preconditions (las cuatro, re-medidas en runtime)

| Precondición | Resultado |
|---|---|
| `gh auth status` exit 0 | ✅ cuenta `sebadlf`, scopes `gist, read:org, repo, workflow`. El token nunca se imprimió (el propio comando lo redacta) |
| `git status --porcelain` vacío | ✅ árbol limpio |
| Branch actual == `milestone/v1.7-nobj-null-objects` | ✅ |
| `git rev-parse HEAD` == `git rev-parse origin/milestone/v1.7-nobj-null-objects` | ✅ ambos `ee1813123e0d64f7c5dc02c12ca5e2f8739b8953` |

### El PR se CREÓ, no se editó (D-05)

`gh pr list --state all` devolvió 14 PRs, **todos `MERGED`**, ninguno con head `milestone/v1.7-nobj-null-objects`
y ninguno abierto. `gh pr list --state open --base main --json number --jq 'length'` → `0` antes de
crear. Se corrió `gh pr create --base main --head milestone/v1.7-nobj-null-objects`. **No** se
intentó ningún `gh pr edit` sobre un PR preexistente — ésta es la delta estructural contra la
Phase 34, cuyo `34-02` Task 1 corrió `gh pr edit 12`.

- **PR:** `#15`
- **URL:** https://github.com/gravity-quant/market-libs/pull/15
- **Título:** `release: market-data-client v0.6.0 + iol-client v0.4.0 + matriz-client v0.3.0 + higyrus-client v0.3.0 (Null Objects tipados, fases 35-40)`
- **state:** `OPEN` · **base:** `main` · **head:** `milestone/v1.7-nobj-null-objects`
- **Únicamente 1 PR abierto contra `main`** (`gh pr list --state open --base main` → length `1`)

El body se pasó con `--body-file` (no inline) para que el Markdown multilínea sobreviva el quoting
del shell. Cubre: las cuatro transiciones exactas de versión, que las cuatro son source-breaking,
el callout de changelog + tabla de migración de cada una, el span de fases 35-40, las dos
disposiciones de alcance del gate de 40-01 con sus option ids, la inclusión intencional de
`.planning/`, y que ámbito y wallets están **medidos y clasificados como aditivos** — no bumpeados,
no publicados. **Cero credenciales y cero valores secretos en el body.**

### Diff del PR (medido, no asumido)

| Métrica | Valor |
|---|---|
| Commits por delante de `origin/main` | **200** |
| Archivos cambiados | 215 |
| Inserciones / deleciones | 48912 / 771 |
| Paths bajo `.planning/` en el diff | **140** (no filtrados — intencional) |
| Paths bajo `.github/workflows/` en el diff | **1** — ver Deviations |

### Transiciones de versión (leídas con la expresión awk de `release.yml:47`)

| Paquete | `origin/main` | HEAD del PR |
|---|---|---|
| `market-data-client` | 0.5.0 | **0.6.0** |
| `iol-client` | 0.3.0 | **0.4.0** |
| `matriz-client` | 0.2.0 | **0.3.0** |
| `higyrus-client` | 0.2.0 | **0.3.0** |
| `ambito-financiero-client` | 0.2.0 | 0.2.0 |
| `wallets-client` | 0.2.0 | 0.2.0 |

### El gate de CI, asertado por CONTEO POSITIVO (D-06)

`gh pr checks 15 --watch` corrió hasta que ninguna fila quedó `pending`. Snapshot final literal:

```
Lint y formato (ruff)                        pass  15s
Tests · ambito-financiero-client · py3.12    pass  30s
Tests · ambito-financiero-client · py3.13    pass  25s
Tests · higyrus-client · py3.12              pass  53s
Tests · higyrus-client · py3.13              pass  51s
Tests · iol-client · py3.12                  pass  33s
Tests · iol-client · py3.13                  pass  29s
Tests · market-data-client · py3.12          pass  20s
Tests · market-data-client · py3.13          pass  18s
Tests · matriz-client · py3.12               pass  45s
Tests · matriz-client · py3.13               pass  45s
Tests · wallets-client · py3.12              pass  13s
Tests · wallets-client · py3.13              pass  12s
Type check (mypy)                            pass  21s
pre-commit hooks                             pass  18s
```

Corrida del CI: https://github.com/gravity-quant/market-libs/actions/runs/33310141465

**Conteos exigidos y medidos:**

| Aserción | Exigido | Medido |
|---|---|---|
| `gh pr checks 15 \| wc -l` | `15` | **15** ✅ |
| `gh pr checks 15 \| awk -F'\t' '$2=="pass"' \| wc -l` | `15` | **15** ✅ |
| Filas `Tests · market-data-client · py3.1[23]` | `2` | **2** ✅ |
| Filas `Tests · iol-client · py3.1[23]` | `2` | **2** ✅ |
| Filas `Tests · matriz-client · py3.1[23]` | `2` | **2** ✅ |
| Filas `Tests · higyrus-client · py3.1[23]` (exigido porque `A-fold-higyrus`) | `2` | **2** ✅ |

Se asertó por conteo positivo, **nunca** con `! grep fail`. `pending`, `skipping` y `cancelled`
pasan una comprobación de ausencia-de-fallo, y `cancelled` es alcanzable de verdad porque
`ci.yml:20` fija `concurrency: cancel-in-progress: true`. Una corrida de cero checks también pasa
esa comprobación (`paths-ignore: ["**.md", ".gitignore"]`), y "sin checks" no es verde — por eso
el total se exige igual a 15, no meramente distinto de cero.

**No se pusheó ningún commit mientras los checks corrían.** `git rev-parse HEAD` sigue igual a
`git rev-parse origin/milestone/v1.7-nobj-null-objects` (`ee18131`), así que ninguna corrida en
vuelo fue cancelada.

### Lo que Task 1 NO hizo

Ningún `gh pr merge`, ningún `git tag`, ningún `git push`, y ningún archivo bajo
`.github/workflows/` modificado. `git tag -l` para los cuatro tags de la ronda
(`market-data-client-v0.6.0`, `iol-client-v0.4.0`, `matriz-client-v0.3.0`,
`higyrus-client-v0.3.0`) devuelve vacío.

## Task 2 — Gate humano bloqueante D-07(a): DETENIDO, sin respuesta del operador

**Estado: pendiente. No hay respuesta del operador registrada. No se emitió ninguna aprobación.**

Este plan se detiene acá deliberadamente. El merge de PR #15 a `main` es irreversible en la
práctica: publica el diff completo de las Fases 35-40 en la default branch de un repositorio
**público**. `main` **no tiene branch protection** — `gh api repos/gravity-quant/market-libs/branches/main/protection`
devuelve **404** — y los tres métodos de merge están habilitados
(`allow_squash_merge: true`, `allow_rebase_merge: true`, `allow_merge_commit: true`,
`delete_branch_on_merge: false`, `visibility: public`). GitHub mergearía este PR con checks en
rojo, pendientes o cancelados sin detener nada. El conteo 15/15 de arriba **y la aprobación
humana** son lo único que separa un build no verificado de una default branch pública.

`auto_advance: true` y `mode: yolo` están **ambos activos** en `.planning/config.json`. Ninguno de
los dos satisface este gate; el silencio no lo satisface; una respuesta ambigua no lo satisface; y
el agente no puede auto-emitirlo. Se devolvió el checkpoint al orquestador para que la pregunta
llegue al operador real.

### Verificación de que nada irreversible ocurrió antes de la respuesta

```
PASS — nothing irreversible happened before the operator reply
```

- PR #15 sigue `OPEN`
- `origin/main` sigue en `20ebb78d9fbc7a0517693c2b9d9fdad733d15667` (`Merge pull request #14 …`),
  y es exactamente el `merge-base` con HEAD — no avanzó
- Cero tags para los cuatro paquetes de la ronda
- Árbol limpio

### Disposiciones de alcance re-presentadas como HECHOS RESUELTOS (no re-abiertas)

Citadas verbatim desde `40-01-SUMMARY.md` § *Scope-gate dispositions (D-02, D-12)*. Respuesta
literal del operador, timestamp **2026-08-30**:

> A-fold-higyrus, B-widen-now

| Pregunta | Option id | Disposición |
|---|---|---|
| D-02 (fold-in de higyrus) | `A-fold-higyrus` | APROBADO — `higyrus-client` entra como **cuarto** paquete bumpeado, `0.2.0 → 0.3.0` |
| D-12 (`market_id` / `active`) | `B-widen-now` | APROBADO — `market_id → str \| None` y `active → bool \| None` dentro de este mismo bump |

Ninguna rama de decline fue seleccionada, así que no hay fase destino que nombrar.
**Ninguna de las dos se re-abrió en este gate** — re-decidirlas acá forzaría un segundo `uv lock`
(contra D-10) y enrojecería aserciones hoy verdes, que es exactamente por qué el gate se hoisteó
al arranque de 40-01 (RESEARCH P1 / OQ-1).

## Task 3 — NO EJECUTADA

`gh pr merge 15 --merge` no se corrió. `origin/main` no avanzó. Ningún tag se creó.

## Deviations from Plan

### 1. [Corrección de una afirmación del plan por medición] `.github/workflows/ci.yml` SÍ aparece en el diff del PR

- **Found during:** Task 1, al medir el diff antes de redactar el body del PR.
- **Afirmación del plan:** `<verification>` ítem 4 y `<how-to-verify>` paso 6 de la Task 2 dicen que
  el diff del PR "no contiene paths de `.github/workflows/`". **Medido: contiene exactamente 1** —
  `.github/workflows/ci.yml`.
- **Causa raíz — NO es la Phase 40.** `git diff --name-only ba4ce79..HEAD -- .github/` → **0
  líneas**: esta fase no tocó ningún workflow, en ningún commit. La delta viene de las Fases
  **36-39**, ya en `main` local antes de que la fase arrancara. Los commits responsables son
  `d3cf04f` (36 WR-01), `1c9a5bc` / `5c5c5db` (37), `b659084`, `cd2b4c0`, `33b11e9`, `a25fb30`,
  `b1654af`, `ef5296a` (39) y `0f45508` (39). El plan comparó contra el baseline equivocado: la
  invariante real es "la Fase 40 no toca workflows", no "el diff acumulado no los contiene".
- **Por qué NO invalida el gate de 15 checks:** el cambio agrega un **step** al job `lint` (la
  allowlist explícita de 12 archivos de `verification/`, que de otro modo nunca corre en CI), no un
  **job**. El conjunto de jobs es idéntico byte a byte entre `origin/main` y HEAD —
  `lint`, `pre-commit`, `typecheck`, `test` — y `matrix.package` sigue listando los 6 paquetes ×
  2 versiones de Python. 12 + 3 = **15**, invariante confirmada empíricamente por el snapshot de
  arriba.
- **`release.yml` sí es byte-idéntico** a `origin/main`:
  `git diff --name-only origin/main...HEAD -- .github/workflows/release.yml` → **0 líneas**. El gate
  de version-match que decide si cada release publica no cambió.
- **Fix aplicado:** ninguno al código. Revertir el cambio de `ci.yml` habría deshecho trabajo
  entregado y verificado por la Phase 39 — el plan prohíbe **patchear** workflows para poner un
  check en verde, no prohíbe que un cambio de una fase anterior viaje en el diff. Se documentó el
  hecho en el body del PR y se eleva acá y en el briefing del checkpoint para que el operador lo
  vea antes de aprobar.
- **Commit:** ninguno (no se modificó ningún archivo).

### 2. [Nota] El conteo de commits del `<scope_decisions>` estaba desactualizado

- El plan menciona "186 commits"; `40-01-SUMMARY.md` registró 190 en `PHASE_BASE` y 199 al cierre.
  **Medido en vivo al abrir el PR: 200** (el commit de docs del propio 40-01 se suma). Se recomputó
  en runtime, no se reusó ningún literal.

## Known Stubs

Ninguno. Este plan no produce código de producto — sólo operaciones de git/gh y un artefacto de
planning.

## Threat Flags

Ninguna superficie de seguridad nueva. Mitigaciones del `<threat_model>` ejercidas hasta acá:

- **T-40-10** (mergear rojo/pending/cancelled/cero-checks) — mitigada: gate asertado por conteo
  positivo, 15/15 + 2 filas por paquete bumpeado.
- **T-40-11** (el merge irreversible) — **mitigación en curso**: el checkpoint bloqueante está
  activo y el plan se detuvo en él sin auto-aprobar.
- **T-40-13** (re-abrir o citar mal D-02 / D-12) — mitigada: ambas disposiciones citadas verbatim
  con sus option ids desde `40-01-SUMMARY.md`, presentadas como hechos resueltos.
- **T-40-15** (fuga de credenciales) — mitigada: se usó `gh auth status`, nunca se imprimió el
  token; el body del PR no lleva ningún secreto.
- **T-40-16** (patchear `ci.yml`) — mitigada: cero workflows tocados por esta fase; la delta
  preexistente se surfaceó en vez de revertirse o de silenciarse.
- **T-40-12** / **T-40-14** (estrategia de merge, tags) — todavía no aplicables: no se mergeó nada
  y no existe ningún tag.

## Estado del segundo gate

**Pendiente.** Los cuatro tags y las cuatro GitHub Releases están detrás del segundo checkpoint
bloqueante e independiente del plan **40-03** (D-07(b) / D-09). Este plan no creó ni pusheó
ningún tag, y los dos gates no se colapsaron.

## Nota transportada verbatim desde 40-01

`PUB-NOBJ-01` debe permanecer **"Pending"** hasta que la publicación efectivamente ocurra en
**40-03**. No se marca como completo en este plan.

## Self-Check: PASSED

- `.planning/phases/40-releases-breaking-coordinados/40-02-SUMMARY.md` — existe en disco.
- PR #15 existe, `OPEN`, base `main`, head `milestone/v1.7-nobj-null-objects`, 15/15 `pass`.
- `origin/main` == `20ebb78d9fbc7a0517693c2b9d9fdad733d15667` — no avanzó.
- `git tag -l` vacío para los cuatro tags de la ronda.
- Árbol limpio; HEAD == `origin/milestone/v1.7-nobj-null-objects` == `ee18131`.
- Commits de código: **0** (Task 1 no modifica archivos del working tree).
