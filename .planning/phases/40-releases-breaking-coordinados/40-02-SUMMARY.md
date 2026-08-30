---
phase: 40-releases-breaking-coordinados
plan: 02
subsystem: release-mechanics
tags: [release, pull-request, ci-gate, checkpoint, blocking-human, merge-commit, semver]
requires:
  - "plan 40-01 complete: four packages bumped, single `uv.lock` refresh, `origin/milestone/v1.7-nobj-null-objects` at local HEAD"
  - "authenticated `gh` CLI"
  - "operator go/no-go at the D-07(a) pre-merge gate — RESOLVED: literal reply `approved`"
provides:
  - "gh-pr:15 — the v1.7 release PR, created against `main` and now MERGED"
  - "a count-asserted 15/15 CI green gate on that PR, re-verified live immediately before the merge"
  - "git-ref:origin/main == 8e0013f2ac7f0361df1ad4893cf0de8f6c773751 — a REAL two-parent merge commit, the shared tag anchor for every tag in plan 40-03"
affects:
  - "github.com/gravity-quant/market-libs PR #15 (MERGED)"
  - "github.com/gravity-quant/market-libs branch `main` (advanced 20ebb78 → 8e0013f)"
tech-stack:
  added: []
  patterns:
    - "assert CI green by explicit positive count (total == 15, pass == 15, 2 matrix rows per bumped package), never by absence of the word `fail`"
    - "a blocking human gate on an irreversible operation is not satisfiable by `auto_advance`, yolo mode, silence, or agent self-issue"
    - "prove a merge was real by parent COUNT (`git rev-list --parents -n1` → 3 fields), never by the subject line"
    - "on continuation after a checkpoint, re-verify every gate live before the irreversible step — never trust the pre-checkpoint snapshot"
    - "bind the green CI run to the exact SHA being merged (`actions/runs/<id>.head_sha` == `pr.headRefOid`), so the gate cannot belong to a different commit"
key-files:
  created:
    - .planning/phases/40-releases-breaking-coordinados/40-02-SUMMARY.md
  modified: []
decisions:
  - "D-05 exercised as a CREATE: `gh pr create` (no v1.7 PR existed to edit) — PR #15"
  - "D-06 gate asserted by count: 15 total rows / 15 `pass` / 2 matrix rows for each of the FOUR bumped packages — asserted twice, once at Task 1 and again live at the continuation before merging"
  - "D-07(a) satisfied by a literal operator reply `approved`; recorded verbatim, not auto-issued"
  - "D-08 honoured: `gh pr merge 15 --merge`; MERGE_SHA 8e0013f has exactly two parents"
  - "PLAN assumption corrected by measurement: `.github/workflows/ci.yml` DOES appear in the PR diff — the delta comes from Phases 36-39, not Phase 40, and adds a step (not a job), so the 15-check invariant holds"
  - "The two local planning commits (825c0e4, 0168fa3) were deliberately NOT pushed to the PR head — pushing a .md-only diff would have re-pointed the head at a SHA that `paths-ignore` gives ZERO checks"
metrics:
  duration: "~4 min (Task 1) + ~3 min (continuation: re-verify + merge + summary)"
  completed: 2026-08-30
  tasks_completed: 3
  tasks_total: 3
  commits: 1
status: complete
---

# Phase 40 Plan 02: PR de release v1.7 + gate humano pre-merge + merge — Summary

PR #15 abierto contra `main`, gate de CI asertado **por conteo positivo explícito** (15 filas /
15 `pass` / 2 filas de matrix por cada uno de los cuatro paquetes bumpeados), detenido en el gate
humano bloqueante D-07(a), reanudado con un **`approved` literal del operador**, y mergeado con un
**merge commit real de dos padres**: `origin/main` avanzó `20ebb78` → **`8e0013f`**. Cero tags.

## Estado del plan

| Task | Tipo | Estado |
|---|---|---|
| 1 — Crear el PR y asertar 15/15 por conteo | `auto` | ✅ COMPLETA |
| 2 — Gate humano bloqueante pre-merge (D-07a) | `checkpoint:human-verify` `gate="blocking"` | ✅ RESUELTA — `approved` literal del operador |
| 3 — Merge con merge commit real (D-08, D-09) | `auto` | ✅ COMPLETA — `MERGE_SHA` = `8e0013f`, dos padres |

---

## Task 1 — PR creado y gate de CI asertado por conteo

### Preconditions (las cuatro, re-medidas en runtime)

| Precondición | Resultado |
|---|---|
| `gh auth status` exit 0 | ✅ cuenta `sebadlf`, scopes `gist, read:org, repo, workflow`. El token nunca se imprimió (el propio comando lo redacta) |
| `git status --porcelain` vacío | ✅ árbol limpio |
| Branch actual == `milestone/v1.7-nobj-null-objects` | ✅ |
| `git rev-parse HEAD` == `git rev-parse origin/milestone/v1.7-nobj-null-objects` | ✅ ambos `ee1813123e0d64f7c5dc02c12ca5e2f8739b8953` |

### El PR se CREÓ, no se editó (D-05)

`gh pr list --state all` devolvió 14 PRs, **todos `MERGED`**, ninguno con head
`milestone/v1.7-nobj-null-objects` y ninguno abierto.
`gh pr list --state open --base main --json number --jq 'length'` → `0` antes de crear. Se corrió
`gh pr create --base main --head milestone/v1.7-nobj-null-objects`. **No** se intentó ningún
`gh pr edit` sobre un PR preexistente — ésta es la delta estructural contra la Phase 34, cuyo
`34-02` Task 1 corrió `gh pr edit 12`.

- **PR:** `#15`
- **URL:** https://github.com/gravity-quant/market-libs/pull/15
- **Título:** `release: market-data-client v0.6.0 + iol-client v0.4.0 + matriz-client v0.3.0 + higyrus-client v0.3.0 (Null Objects tipados, fases 35-40)`
- **state al abrir:** `OPEN` · **base:** `main` · **head:** `milestone/v1.7-nobj-null-objects`
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

| Paquete | `origin/main` (pre-merge) | HEAD del PR |
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

**No se pusheó ningún commit mientras los checks corrían.** Al cierre de la Task 1
`git rev-parse HEAD` seguía igual a `git rev-parse origin/milestone/v1.7-nobj-null-objects`
(`ee18131`), así que ninguna corrida en vuelo fue cancelada.

### Lo que Task 1 NO hizo

Ningún `gh pr merge`, ningún `git tag`, ningún `git push`, y ningún archivo bajo
`.github/workflows/` modificado.

---

## Task 2 — Gate humano bloqueante D-07(a): RESUELTO con un `approved` literal

### Respuesta del operador, verbatim

> approved

- **Timestamp de la resolución:** 2026-08-30
- **Canal:** respuesta directa del operador humano al checkpoint bloqueante
- **Explícitamente NO auto-emitida.** `auto_advance: true` y `mode: yolo` están **ambos activos**
  en `.planning/config.json` y **ninguno de los dos** produjo esta aprobación. No se infirió del
  silencio, no se derivó de una respuesta ambigua, no fue una selección por defecto y el agente no
  la auto-emitió. La corrida de la Task 1 se **detuvo** en el checkpoint y devolvió el control; la
  aprobación llegó del operador y esta corrida de continuación la transporta verbatim.
- Este es el **primero** de los dos gates bloqueantes de la fase. El segundo (push de tags +
  Releases públicas, D-07(b)) sigue **pendiente** en el plan 40-03. Los dos **no** se colapsaron.

### Lo que el operador vio antes de responder

PR #15 con su URL, la salida literal de `gh pr checks 15` con los conteos (15 filas / 15 `pass` /
2 filas de matrix por paquete bumpeado), el diff stat (215 archivos, +48912/−771, 200 commits), las
cuatro transiciones de versión exactas, la desviación de `ci.yml` surfaceada en vez de silenciada,
y el aviso explícito de que **`main` no tiene branch protection** — `gh api …/branches/main/protection`
devuelve **404** — de modo que esta aprobación era el único gate.

### Disposiciones de alcance re-presentadas como HECHOS RESUELTOS (no re-abiertas)

Citadas verbatim desde `40-01-SUMMARY.md` § *Scope-gate dispositions (D-02, D-12)*. Respuesta
literal del operador en aquel gate, timestamp **2026-08-30**:

> A-fold-higyrus, B-widen-now

| Pregunta | Option id | Disposición |
|---|---|---|
| D-02 (fold-in de higyrus) | `A-fold-higyrus` | APROBADO — `higyrus-client` entra como **cuarto** paquete bumpeado, `0.2.0 → 0.3.0` |
| D-12 (`market_id` / `active`) | `B-widen-now` | APROBADO — `market_id → str \| None` y `active → bool \| None` dentro de este mismo bump |

Ninguna rama de decline fue seleccionada, así que no hay fase destino que nombrar.
**Ninguna de las dos se re-abrió en este gate** — re-decidirlas acá forzaría un segundo `uv lock`
(contra D-10) y enrojecería aserciones hoy verdes, que es exactamente por qué el gate se hoisteó
al arranque de 40-01 (RESEARCH P1 / OQ-1).

### Verificación de que nada irreversible ocurrió antes de la respuesta

En el momento de la respuesta del operador: PR #15 `OPEN`; `origin/main` todavía en
`20ebb78d9fbc7a0517693c2b9d9fdad733d15667` y exactamente igual al `merge-base` con el head del PR
(no avanzó); cero tags para los cuatro paquetes de la ronda; árbol limpio.

---

## Task 3 — Merge con merge commit real (D-08, D-09)

### Re-verificación en vivo ANTES del merge (nada stale)

Esta corrida es un agente de continuación **fresco**. Todo se volvió a medir contra el estado vivo;
no se confió en un solo valor del snapshot pre-checkpoint.

| Re-verificación | Resultado |
|---|---|
| `gh auth status` | ✅ exit 0, cuenta `sebadlf`, token nunca impreso |
| `git status --porcelain` | ✅ vacío |
| Branch actual | ✅ `milestone/v1.7-nobj-null-objects` |
| PR #15 `state` | ✅ sigue `OPEN` |
| PR #15 `baseRefName` / `headRefName` | ✅ `main` / `milestone/v1.7-nobj-null-objects` |
| PR #15 `mergeable` / `mergeStateStatus` | ✅ `MERGEABLE` / `CLEAN` |
| PRs abiertos contra `main` | ✅ exactamente **1** (el #15) |
| `gh pr checks 15 \| wc -l` | ✅ **15** (recontado en vivo) |
| `gh pr checks 15 \| awk -F'\t' '$2=="pass"' \| wc -l` | ✅ **15** (recontado en vivo) |
| Filas de matrix por paquete bumpeado (los 4) | ✅ **2 / 2 / 2 / 2** (recontadas en vivo) |
| `origin/main` == `merge-base(origin/main, head)` | ✅ `20ebb78…` en ambos — **`main` no avanzó** |
| Tags de la ronda | ✅ los cuatro vacíos |
| **`actions/runs/33310141465.head_sha` == `pr.headRefOid`** | ✅ ambos `ee1813123e0d64f7c5dc02c12ca5e2f8739b8953`, `status: completed`, `conclusion: success` |

Esa última fila es la que cierra un agujero que el plan no pedía explícitamente: **liga la corrida
verde al SHA exacto que se iba a mergear**. Un 15/15 que pertenezca a otro commit es un gate que no
gatea nada. Coinciden.

### El merge

```
gh pr merge 15 --merge
```

- **`--merge` y sólo `--merge`.** Cero `--squash`, cero `--rebase`, cero flag de borrado de branch
  (`delete_branch_on_merge` es `false` en el repo y se respetó sin sobreescribirlo).
- Los tres métodos de merge están habilitados en el repo (`allow_merge_commit: true`,
  `allow_squash_merge: true`, `allow_rebase_merge: true`), así que nada más que esta instrucción
  impedía el método equivocado.
- Momento del merge: **2026-08-30T12:58:08Z**, por `sebadlf`.

### `MERGE_SHA` re-resuelto EN VIVO desde `origin/main` después del merge

No se asumió igual a ningún SHA calculado antes del merge. Se corrió `git fetch origin main --tags`
y después `git rev-parse origin/main`:

| Campo | Valor |
|---|---|
| **`MERGE_SHA`** | **`8e0013f2ac7f0361df1ad4893cf0de8f6c773751`** |
| Padre 1 (`main` previo) | `20ebb78d9fbc7a0517693c2b9d9fdad733d15667` |
| Padre 2 (head del PR) | `ee1813123e0d64f7c5dc02c12ca5e2f8739b8953` |
| Subject | `Merge pull request #15 from gravity-quant/milestone/v1.7-nobj-null-objects` |
| Autor | `Sebastián de la Fuente <sebadlf@gmail.com>` |
| Fecha | `2026-08-30T09:58:08-03:00` |
| `gh pr view 15 --json mergeCommit.oid` | `8e0013f2ac7f0361df1ad4893cf0de8f6c773751` — coincide |

**Prueba de que el merge fue real, por conteo de padres (no por el subject):**

```
$ git rev-list --parents -n1 origin/main
8e0013f2ac7f0361df1ad4893cf0de8f6c773751 20ebb78d9fbc7a0517693c2b9d9fdad733d15667 ee1813123e0d64f7c5dc02c12ca5e2f8739b8953
$ git rev-list --parents -n1 origin/main | wc -w
3
```

**3 campos = el commit + exactamente DOS padres.** Un squash o un rebase habrían dado 2 campos. El
subject line no se usó como prueba porque algunas UIs renderizan un squash con un subject que
parece merge; el conteo de padres no puede mentir.

### El árbol mergeado, leído con la expresión awk de `release.yml:47`

`awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'` — nunca un parser de TOML, nunca
`importlib.metadata`, nunca un regex propio, porque cualquier otro lector puede discrepar con el
gate que decide si el release publica.

| Paquete | `git show origin/main:packages/<pkg>/pyproject.toml` | Exigido | Resultado |
|---|---|---|---|
| `market-data-client` | **0.6.0** | 0.6.0 | ✅ |
| `iol-client` | **0.4.0** | 0.4.0 | ✅ |
| `matriz-client` | **0.3.0** | 0.3.0 | ✅ |
| `higyrus-client` | **0.3.0** | 0.3.0 (por `A-fold-higyrus`) | ✅ |
| `ambito-financiero-client` | **0.2.0** | 0.2.0 (sin bump) | ✅ |
| `wallets-client` | **0.2.0** | 0.2.0 (sin bump) | ✅ |

Los cuatro tags de la ronda pasarán el version-match gate de `release.yml`; ninguno de los dos
paquetes sin cambios puede ser tagueado por error desde este árbol.

### Bloque `<automated>` completo de la Task 3

```
PASS
```

Incluye, además de lo de arriba: `gh pr list --state merged --base main --head milestone/v1.7-nobj-null-objects`
devuelve `15`; `gh pr view 15 --json state` es **`MERGED`**;
`git ls-remote --heads origin milestone/v1.7-nobj-null-objects` sigue devolviendo un ref
(`ee18131` — la branch **sobrevivió** al merge, como corresponde con
`delete_branch_on_merge: false`); y los cuatro `git tag -l` de la ronda siguen vacíos.

### Diff efectivo del merge sobre `main`

| Métrica | Valor |
|---|---|
| `git diff --shortstat 20ebb78 8e0013f` | **215 archivos, +48912 / −771** |
| Paths bajo `.planning/` publicados | **140** |
| Paths bajo `.github/workflows/` | 1 (`ci.yml` — ver Deviations; `release.yml` **no** cambió) |

### Lo que Task 3 NO hizo

Ningún `git tag`, ningún `git push --tags`, ningún `git push origin main` (el merge fue por el PR,
así que atribución, cierre del PR y forma del merge commit coinciden con todos los releases
previos), ningún flag de borrado de branch, ningún `--force` de ninguna clase, y ningún credential
impreso en ningún momento.

---

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
- **Por qué NO invalidó el gate de 15 checks:** el cambio agrega un **step** al job `lint` (la
  allowlist explícita de 12 archivos de `verification/`, que de otro modo nunca corre en CI), no un
  **job**. El conjunto de jobs es idéntico entre `origin/main` y el head — `lint`, `pre-commit`,
  `typecheck`, `test` — y `matrix.package` sigue listando los 6 paquetes × 2 versiones de Python.
  12 + 3 = **15**, invariante confirmada empíricamente por el snapshot y re-confirmada en vivo antes
  del merge.
- **`release.yml` es byte-idéntico:** `git diff --name-only 20ebb78 8e0013f -- .github/workflows/`
  devuelve sólo `ci.yml`. El gate de version-match que decide si cada release publica **no cambió**,
  que es lo que importa para el plan 40-03.
- **Fix aplicado:** ninguno al código. Revertir el cambio de `ci.yml` habría deshecho trabajo
  entregado y verificado por la Phase 39 — el plan prohíbe **patchear** workflows para poner un
  check en verde, no prohíbe que un cambio de una fase anterior viaje en el diff. Se documentó en el
  body del PR y se elevó en el briefing del checkpoint para que el operador lo viera antes de aprobar.
- **Commit:** ninguno (no se modificó ningún archivo).

### 2. [Rule 3 - Blocking, evitado] Los dos commits locales de planning se dejaron deliberadamente SIN pushear

- **Found during:** re-verificación de la Task 3, antes del merge.
- **Situación:** al reanudar, el HEAD local estaba **2 commits adelante** de
  `origin/milestone/v1.7-nobj-null-objects`: `825c0e4` (SUMMARY parcial de 40-02) y `0168fa3`
  (punto de detención en `STATE.md`). Ambos tocan **únicamente** archivos `.md` bajo `.planning/`.
- **Por qué no se pushearon:** `ci.yml` fija `paths-ignore: ["**.md", ".gitignore"]`. Pushear un
  diff exclusivamente `.md` habría re-apuntado el head del PR a un SHA nuevo que dispara **CERO
  checks** — convirtiendo un gate contado de 15/15 en un head sin ningún check, exactamente el
  falso-verde que D-06 existe para prevenir. Además habría invalidado la ligadura
  `run.head_sha == pr.headRefOid` que esta corrida verificó.
- **Decisión:** no pushear. El PR se mergeó con el head `ee18131` que el operador revisó y que la
  corrida verde de CI cubre. Los commits de planning quedan locales en la branch y se publicarán
  por la vía normal de bookkeeping; no bloquean al plan 40-03, que taguea `origin/main`.
- **Commit:** ninguno.

### 3. [Nota] El conteo de commits del `<scope_decisions>` estaba desactualizado

- El plan menciona "186 commits"; `40-01-SUMMARY.md` registró 190 en `PHASE_BASE` y 199 al cierre.
  **Medido en vivo al abrir el PR: 200** (el commit de docs del propio 40-01 se suma). Se recomputó
  en runtime, no se reusó ningún literal.

---

## Verificación del plan — 9/9

1. ✅ Exactamente un PR abierto contra `main` antes del merge, **creado** (no editado) desde
   `milestone/v1.7-nobj-null-objects` — D-05
2. ✅ Título empieza con `release: ` y nombra los cuatro paquetes con sus transiciones; el body
   nombra el span 35-40 y las dos disposiciones de alcance registradas
3. ✅ `gh pr checks 15` → 15 filas, 15 `pass`, 2 filas por paquete bumpeado — contado dos veces
   (Task 1 y re-verificación pre-merge)
4. ✅ El diff contiene 140 paths de `.planning/`; el único path de `.github/workflows/` es `ci.yml`,
   heredado de las Fases 36-39 y surfaceado (Deviation 1) — `release.yml` intacto
5. ✅ El operador respondió `approved` de forma explícita y literal antes de que corriera cualquier
   comando de merge; la respuesta está registrada verbatim con su timestamp — D-07(a)
6. ✅ El briefing citó D-02 y D-12 como hechos resueltos con sus option ids; ninguna se re-abrió
7. ✅ `git rev-list --parents -n1 origin/main | wc -w` == **3** — D-08
8. ✅ El árbol mergeado lee 0.6.0 / 0.4.0 / 0.3.0 / 0.3.0 para los bumpeados y 0.2.0 para ámbito y
   wallets, todos con la expresión awk de `release.yml`
9. ✅ Cero tags para cualquier paquete al cierre de este plan

## Known Stubs

Ninguno. Este plan no produce código de producto — sólo operaciones de git/gh y un artefacto de
planning.

## Threat Flags

Ninguna superficie de seguridad nueva. Mitigaciones del `<threat_model>` ejercidas:

- **T-40-10** (mergear rojo/pending/cancelled/cero-checks) — **mitigada**: gate asertado por conteo
  positivo, 15/15 + 2 filas por paquete bumpeado, contado dos veces, y ligado por `head_sha` al SHA
  exacto que se mergeó.
- **T-40-11** (el merge irreversible) — **mitigada**: checkpoint bloqueante ejercido de verdad; el
  merge corrió **sólo** después de un `approved` literal del operador, con `auto_advance: true` y
  `mode: yolo` activos y sin que ninguno de los dos lo satisficiera.
- **T-40-12** (squash / rebase reescribiendo historia) — **mitigada**: `gh pr merge 15 --merge`;
  dos padres probados por conteo, no por subject. Los SHAs que las SUMMARYs de las Fases 35-39 citan
  por valor siguen alcanzables.
- **T-40-13** (re-abrir o citar mal D-02 / D-12) — **mitigada**: ambas citadas verbatim con sus
  option ids desde `40-01-SUMMARY.md`, como hechos resueltos.
- **T-40-14** (taguear el commit equivocado) — **mitigada hasta donde llega este plan**: cero tags
  creados; el árbol mergeado ya lee todas las versiones target bajo el awk de `release.yml`, y los
  dos paquetes sin bump quedaron en 0.2.0 para que ninguno pueda tagearse por error en 40-03.
- **T-40-15** (fuga de credenciales) — **mitigada**: `gh auth status` en vez de imprimir el token;
  el body del PR no lleva ningún secreto; nada se echoeó.
- **T-40-16** (patchear `ci.yml`) — **mitigada**: cero workflows tocados por esta fase; la delta
  preexistente se surfaceó en vez de revertirse o silenciarse.

---

## Handoff al plan 40-03

**`MERGE_SHA` = `8e0013f2ac7f0361df1ad4893cf0de8f6c773751`**

Los **cuatro** tags anotados de la ronda van sobre este commit:

| Tag | Versión en el árbol mergeado |
|---|---|
| `market-data-client-v0.6.0` | 0.6.0 ✅ |
| `iol-client-v0.4.0` | 0.4.0 ✅ |
| `matriz-client-v0.3.0` | 0.3.0 ✅ |
| `higyrus-client-v0.3.0` | 0.3.0 ✅ |

Son **cuatro**, no tres — `higyrus-client` entró por la disposición `A-fold-higyrus`.

40-03 debe **recomputar** `MERGE_SHA` con `git rev-parse origin/main` en vez de confiar en este
literal; el valor de arriba es el cross-check.

## Estado del segundo gate

**PENDIENTE.** Los cuatro tags y las cuatro GitHub Releases están detrás del segundo checkpoint
bloqueante e independiente del plan **40-03** (D-07(b) / D-09). Este plan **no** creó ni pusheó
ningún tag, y los dos gates **no** se colapsaron: el primero se ejerció acá con un `approved`
literal, el segundo todavía no se le presentó al operador.

## Nota transportada verbatim desde 40-01

`PUB-NOBJ-01` debe permanecer **"Pending"** hasta que la publicación efectivamente ocurra en
**40-03**. No se marca como completo en este plan.

## Self-Check: PASSED

- `.planning/phases/40-releases-breaking-coordinados/40-02-SUMMARY.md` — existe en disco.
- PR #15 existe y su `state` es **`MERGED`**; `mergeCommit.oid` == `8e0013f2ac7f…`.
- `origin/main` == `8e0013f2ac7f0361df1ad4893cf0de8f6c773751`, con dos padres
  (`20ebb78…`, `ee18131…`) — verificado por `git rev-list --parents -n1` → 3 campos.
- `git ls-remote --heads origin milestone/v1.7-nobj-null-objects` devuelve `ee18131…` — la branch
  sobrevivió.
- `git tag -l` vacío para los cuatro tags de la ronda.
- Árbol limpio.
