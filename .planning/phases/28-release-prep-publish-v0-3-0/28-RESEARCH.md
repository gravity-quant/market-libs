# Phase 28: Release prep + publish v0.4.0 — Research

**Researched:** 2026-08-01 (live-state re-verification, ~18:00 local)
**Domain:** Release engineering / ops (per-package tag pipeline, GitHub Actions, `gh` CLI, semver)
**Confidence:** HIGH — every claim below was produced by running a command in this repo in this session.

> **Naming:** the phase directory and the ROADMAP text say `v0.3.0`. The version this phase
> publishes is **`0.4.0`** (tag `market-data-client-v0.4.0`) per locked decision **D-01**.
> `v0.3.0` and `v0.3.1` are already published — **re-verified on `origin` this session** (see
> § Live World State). Directory name stays as-is so GSD tooling doesn't break.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Copied verbatim from `.planning/phases/28-release-prep-publish-v0-3-0/28-CONTEXT.md` `<decisions>`.
The planner MUST honor all of these. **Do not research or propose alternatives.**

**Versión y clasificación semver**

- **D-01:** La release es **`0.4.0`** (minor), tag exacto **`market-data-client-v0.4.0`**.
  **NO** `0.3.0` (tag ya existe en `origin` — el push sería rechazado y `release.yml` nunca
  dispararía), **NO** `0.3.2` (el diff sin publicar agrega **13 nombres públicos nuevos** a
  `__all__`: `add_holidays`, `delete_holiday`, `set_calendar_config`, `delete_calendar_config`,
  `preview_calendar_config`, `MarketHoursIn`, `HolidayIn`, `HolidaysIn` + sus contrapartes
  `aio` — un patch bump violaría semver para todo pin `~=0.3.1`), **NO** `1.0.0` (ver D-03).
  Pre-computado independientemente en `26-RESEARCH.md:910` y `27-CONTEXT.md:222-224`.

- **D-02:** **Re-apuntar `PUB-MUT-01`** en `.planning/REQUIREMENTS.md` (línea 28) y el texto de
  Phase 28 en `.planning/ROADMAP.md` de `v0.3.0` → `v0.4.0`, dejando constancia de que
  `v0.3.0`/`v0.3.1` se publicaron mid-milestone. El requisito se satisface por la publicación
  de `0.4.0`, no por la de `0.3.0` (que ya ocurrió fuera del flujo de fases).

- **D-03:** El bump se declara **minor no-breaking** bajo la decisión ya lockeada **D-13**
  (`27-CONTEXT.md:139-143`), **con un callout explícito en el changelog**. El lado symbols es
  verificadamente no-breaking; el lado `CalendarDay` es técnicamente source-breaking y se
  documenta en vez de blindarse con shim.
  - **Symbols — no-breaking (verificado):** `5cc9ac1` **ensancha** `symbol_id: str → int | str`
    en los cuatro routes (`_core.build_update_symbol_request`, `Client.update_symbol`,
    `AsyncClient.update_symbol`, ambos shims de módulo) y **preserva** `Symbol.marketId` como
    alias deprecado espejado desde el wire `market_id` vía override de `from_api`; los cinco
    campos nuevos de `Symbol` (`id`, `market_id`, `created_at`, `updated_at`, `received_at`)
    tienen defaults. `3c9d31c` desenvuelve el envelope preservando `list[Symbol]`.
    Re-verificado independientemente en `27-VERIFICATION.md:136-153`.
  - **`CalendarDay` — source-breaking, aceptado:** `831f44f` **removió** `date` / `marketId` /
    `isBusinessDay` y los reemplazó por `day` / `closed` / `description` / `open_time` /
    `close_time`. `CalendarDay` está en `__all__` desde v0.2.0, así que `d.date` en un consumidor
    v0.3.1 sería `AttributeError`. D-13 lo pre-autoriza como no-breaking porque
    `parse_calendar_response` iteraba las claves del envelope — ningún consumidor pudo haber
    tenido nunca una instancia poblada. **Riesgo residual conocido:** `27-VERIFICATION.md`
    re-verificó **sólo D-22**; D-13 es el único claim de no-breaking que nunca se auditó
    independientemente.
  - **Mitigación elegida (operator, 2026-08-01):** honrar D-13 y shippear minor, pero el
    changelog de `v0.4.0` **debe nombrar explícitamente** el reemplazo de campos de
    `CalendarDay` (viejos → nuevos) para que sea descubrible y no silencioso.
    **Rechazado:** compat shim con aliases deprecados (el patrón de `Symbol.marketId`) —
    considerado y descartado. **Rechazado:** escalar a `1.0.0` — contradice D-13/D-22 lockeados
    y quema el major que el docstring de `Symbol` en `models.py` reserva para remover el alias
    `marketId`.

**Superficie de edición (exactamente 5 sitios; cero archivos de workflow)**

- **D-04:** Los sitios de edición son **exactamente cinco**:
  1. `packages/market-data-client/pyproject.toml:3` — `version = "0.3.1"` → `"0.4.0"`
  2. `packages/market-data-client/src/market_data_client/__init__.py:134` —
     `__version__ = "0.3.1"` → `"0.4.0"`
  3. `packages/market-data-client/README.md:60-62` — insertar `### v0.4.0` inmediatamente
     **arriba** de `### v0.3.1` (formato establecido: español, línea líder en negrita que nombra
     la clase de bump, IDs de requisito citados inline — ver `README.md:84`
     `**Symbols write (MUT-MD-01):**` como modelo)
  4. `uv.lock:488` — refrescado vía `uv lock`
  5. El memory de releases **in-repo** en
     `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md`
     — `description:` del frontmatter (línea 3) + el bloque "**Latest published:**"

- **D-05:** **`uv.lock` SÍ necesita refresh** aunque ninguna dependencia haya cambiado:
  `uv.lock:487-489` carga el propio version string del workspace member
  (`name = "market-data-client"` / `version = "0.3.1"`). Precedente: el stat de PR #9 muestra
  `uv.lock | 2 +-` — exactamente el churn de dos líneas. Si no se refresca, falla el step
  "Verificar uv.lock sincronizado" (`ci.yml:32`) del job `lint`, bloqueando el PR en el check
  1 de 15.

- **D-06:** **No** tocar `.github/workflows/`. `ci.yml:103` ya lista `market-data-client` en
  `matrix.package` (agregado en Phase 24); `release.yml` es genérico —regex
  `^([a-z][a-z0-9-]*-client)-v([0-9]+\.[0-9]+\.[0-9]+...)$` en `release.yml:28`— y matchea
  `market-data-client-v0.4.0` sin edits. Hereda Phase 24 D-02.

- **D-07:** **No** tocar `CLAUDE.md:74` (que todavía dice `market-data-client v0.2.0`, dos
  releases atrás). Ningún release previo lo tocó: no aparece ni en `git show --stat ea92dd8`
  ni en `7b0e0b2`. Es un artefacto generado por `/gsd-map-codebase`, no un archivo de release
  mantenido a mano. Se deja como deuda de documentación conocida.

  **Nota:** `/Users/admin/.claude/projects/-Users-admin-development-market-libs/memory/` está
  **vacío** — el memory real vive **in-repo** bajo `.claude/projects/…` (ver D-04 sitio 5).

**Vehículo de release (branch + PR)**

- **D-08:** Shippear desde la branch existente **`milestone/v1.5-mutations`**. **Un** PR
  `milestone/v1.5-mutations` → `main`. Hereda Phase 24 D-06.

- **D-09:** **Mantener** los artefactos `.planning/` en el PR; **no** usar `/gsd-pr-branch`.
  Precedente directo en esta misma branch: `git show --stat ea92dd8` (PR #8) y `7b0e0b2` (PR #9)
  ambos arrastran `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md` y decenas
  de `.planning/phases/**`. Filtrarlos rompería la continuidad de artefactos de la que dependen
  las Fases 25-27 (`.planning/verification/market-data-client-findings.md`, ~60K de evidencia
  live, nunca llegaría a `main`). Hereda Phase 24 D-07.

- **D-10:** **No** rebasear ni mergear `origin/main` en la branch. El estado "2 behind" es
  **cosmético**: `origin/main^{tree}` == `7f051ae^{tree}` (commit propio de la branch y
  merge-base) == `b404a5dd526807d6934e499b16c3cb3da3ad25ad`, por lo que
  `git diff --stat HEAD...origin/main` sale **vacío** — `origin/main` no contiene ningún
  contenido que la branch no tenga; los dos commits "behind" son merge commits puros
  (`ea92dd8`, `7b0e0b2`). `git merge-tree --write-tree origin/main HEAD` da conflict-free.
  Un rebase de 95 commits sobre dos merge commits ya mergeados reescribiría historia publicada
  y podría orfanar la alcanzabilidad de los tags `v0.3.0`/`v0.3.1`.

- **D-11:** El PR se mergea con **merge commit real** (`gh pr merge --merge`) — **no** squash,
  **no** rebase — y el tag se pushea **sobre ese merge commit**. Hereda Phase 24 D-10.
  Precedente: `ea92dd8` es `Merge: 5903f75 cb67933`, `7b0e0b2` es `Merge: ea92dd8 7f051ae`.
  Un squash colapsaría 95 commits en uno, descartando el trail por-plan que los SUMMARY de
  `.planning/phases/27-*/` cross-referencian por SHA.

- **D-12:** Título del PR siguiendo la convención ya establecida en esta branch:
  `release: market-data-client v0.4.0 (<one-line scope>)`.

**Gate de CI**

- **D-13:** El gate es **15 checks verdes**: `ci.yml` define 4 jobs (`lint:23`, `pre-commit:52`,
  `typecheck:70`, `test:91`); `test` abre en `matrix.package` (6 entradas, `:98-103`) ×
  `matrix.python-version` (`["3.12","3.13"]`, `:104`) = 12 → 3 + 12 = **15**.

- **D-14:** Los **19 failures pre-existentes de matriz en `verification/`** (documentados en
  `27-deferred-items.md` items 1-2: drift de firma `probe_login_sync(client)` de Phase 15 —
  "19 failed, 19 errors, 220 passed") **no pueden bloquear este PR**: **ningún job de CI corre
  `verification/`**. La única invocación de pytest en CI es `ci.yml:112-118`, scoped a
  `pytest packages/${{ matrix.package }}`; el `testpaths = ["packages", "tests", "verification"]`
  del root (`pyproject.toml:106`) nunca se ejercita en workflow alguno. El hook mypy de
  `pre-commit` está scoped `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`), tampoco
  llega. **No esperar un full-suite verde antes de abrir el PR** — bloquearía indefinidamente
  sobre failures fuera de scope que CI nunca ve.

- **D-15:** Gates verificados verdes localmente sobre la branch (2026-08-01, pre-planning):
  `ruff check` → "All checks passed!"; `ruff format --check` → "201 files already formatted";
  `mypy` → "Success: no issues found in 51 source files"; `lint-imports` → "Contracts: 4 kept,
  0 broken"; `pytest packages/market-data-client -q` → **387 passed**. El archivo modificado más
  grande es `main_market_data.py` (144K), bien bajo el default de 500K de
  `check-added-large-files` (`.pre-commit-config.yaml:9`). Sin riesgo de CI conocido del diff
  sin publicar.

- **D-16:** `market-data-client` **permanece ausente** del `files` de mypy del root
  (`pyproject.toml:97`, lista 5 paquetes), de `root_packages` de import-linter
  (`pyproject.toml:141-146`, lista 4) y del loop mypy-tests per-package de `ci.yml:85`.
  Phase 28 **no** cierra ese follow-up — ver `27-CONTEXT.md:442-445` ("Follow-up documentado
  desde Phase 24 (sigue diferido, **no es un CI failure**)"); los checks package-scoped pasan
  hoy. **Decisión del operator (2026-08-01):** mantener diferido y **archivarlo explícitamente
  en el backlog de v1.6** (ROADMAP § Backlog) para que deje de rodar silenciosamente release
  tras release. **Rechazado:** enrolarlo en este PR (expandiría el diff del release).

**Ops irreversibles (gated por go/no-go humano)**

- **D-17:** El agente **conduce** todo el flujo: edits → `uv lock` → abrir PR → confirmar los
  15 checks verdes → mergear → pushear el tag. Hereda Phase 24 D-08.

- **D-18:** **Dos checkpoints humanos bloqueantes**, ambos explícitos: (a) antes de **mergear el
  PR**, y (b) antes de **pushear el tag**. Ambas ops son irrecuperables en la práctica — un tag
  pusheado dispara `release.yml` y crea un GitHub Release público. Hereda Phase 24 D-09; el
  patrón de checkpoint de operator sigue vigente en este milestone (ver la autorización
  "armed destructive run" en `27-deferred-items.md`, otorgada 2026-08-01). Requiere working tree
  limpio + auth `gh`.

### Claude's Discretion

- Wording exacto de la entrada `### v0.4.0` del changelog (siguiendo el formato establecido en
  `README.md:60-100`), siempre que incluya el callout de `CalendarDay` requerido por D-03.
- Cuerpo del PR (el GitHub Release usa `--generate-notes`).
- Agrupamiento y orden de commits dentro de la fase.
- Wording exacto de la entrada de backlog v1.6 requerida por D-16 y del re-apuntado de D-02.

### Deferred Ideas (OUT OF SCOPE)

- **Compat shim de `CalendarDay`** (re-agregar `date`/`marketId`/`isBusinessDay` como aliases
  deprecados espejando `day`/`""`/`not closed`, patrón de `Symbol.marketId`) — considerado y
  descartado en favor del callout de changelog (D-03). Candidato si aparece un consumidor real
  afectado.
- **Enrolar `market-data-client` en el mypy `files` del root + import-linter `root_packages` +
  el loop mypy-tests de `ci.yml:85`** — diferido desde Phase 24; **a archivar explícitamente en
  el backlog de v1.6** per D-16 (requiere autorar un contract de import-linter para
  `market_data_client._core`).
- **Actualizar `CLAUDE.md:74`** (dice `v0.2.0`, tres releases atrás) — fuera del scope del
  release PR per D-07; candidato a `/gsd-quick` docs task.
- **Reparar los 19 failures pre-existentes de matriz en `verification/`** (drift de firma
  `probe_login_sync(client)` de Phase 15) — fuera de scope, CI no los ve (D-14); ya trackeado
  en `27-deferred-items.md`.
- **Versionado repo-wide/workspace** — descartado desde Phase 24 D-11; sigue descartado.
- **SSE streaming (STREAM-MD-01), disk token cache (SEC-MD-01), JWT validation (SEC-MD-02)** —
  v1.6+.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PUB-MUT-01 | `market-data-client` se publica como `v0.3.0` (minor bump — features nuevas, no rompe la superficie de lectura v0.2.0) por el pipeline de tags — bump `pyproject`+`__version__`, README changelog, `uv.lock` refresh, CI verde, PR → merge → tag `market-data-client-v0.3.0` → GitHub Release con wheel + sdist. **(`REQUIREMENTS.md:28` — D-02 re-points `v0.3.0` → `v0.4.0`)** | § Live World State (exact current versions + tags on `origin`); § Public Surface Delta (what the changelog must describe, the 13 names, the `CalendarDay` swap); § Release Mechanics (exact command forms for every step: `uv lock`, push, `gh pr create`, `gh pr checks`, `gh pr merge --merge`, annotated tag, `gh release view`); § CI Gate Anatomy (the 15 check names verbatim, verified from PR #9); § Common Pitfalls (ordering hazards, tag-before-merge, version drift, the D-14 trap); § Contradictions with CONTEXT.md (3 live-state deltas the planner must absorb) |

**Traceability status after this phase:** `REQUIREMENTS.md:65` flips `PUB-MUT-01 | Phase 28 | Pending`
→ `Complete`, and `ROADMAP.md:19` flips `- [ ] **Phase 28: …**` → `- [x]`. Both are part of the
D-02 re-point edit surface.
</phase_requirements>

---

## Summary

This is a pure release/ops phase with an unusually complete CONTEXT.md — the 5 edit sites, the
semver call, the release vehicle, the CI gate shape, and the two human checkpoints are all
already locked. **Every substantive claim in CONTEXT.md was re-verified against the live repo
and `origin` this session and found TRUE**, with three exceptions documented under
§ Contradictions with CONTEXT.md. The most important of those: **the release branch has never
been pushed** — `origin/milestone/v1.5-mutations` is 96 commits behind local `HEAD`, and
CONTEXT.md contains no push step. `gh pr create` cannot open a PR from an unpushed branch.

The second material finding: **`main` has no branch protection at all** (`protected: false`,
protection API returns 404, `rulesets` is `[]`). CONTEXT.md flagged this as an unresolved
external unknown; it is now resolved. Consequence: GitHub will happily merge this PR with red
or still-running checks. The "15 checks green" gate is **entirely self-enforced by the agent**,
which raises the stakes on D-18's first checkpoint from "confirm a formality" to "the only thing
standing between a red build and `main`".

Third: D-04 site 5 (the release memory file) is under-specified. The v0.3.1 precedent commit
`ce77ed4` touched **six** regions of that file (+24/−14), not two — including both install
command lines that pin the tag and wheel URL, and two "Scope note" paragraphs that will become
factually false the moment v0.4.0 ships. Editing only the two regions D-04 names leaves the
memory telling consumers to install `v0.3.1` and asserting that calendar mutations are "NOT yet
done".

**Primary recommendation:** Structure the phase as **two plans** mirroring the Phase 24
precedent (recovered from git history at `b07a924` — the exact template is quoted in
§ Code Examples): Plan 01 = reversible release prep (5 edit sites + D-02 re-point + D-16 backlog
entry + `uv lock` + local gate re-run + **push the branch**), Plan 02 = `autonomous: false`, the
irreversible publish flow with the two blocking checkpoints. Order the Plan-01 steps so that
`uv lock` runs **after** the `pyproject.toml` bump, and gate every irreversible `gh`/`git push
<tag>` call behind a `checkpoint:human-verify`.

---

## Contradictions with CONTEXT.md

> **This is the highest-value section of this document.** Three of CONTEXT.md's live-state claims
> have drifted or were incomplete. The planner MUST absorb all three.

### C-1 — MISSING STEP: the release branch has never been pushed (BLOCKING)

CONTEXT.md D-08 says "Shippear desde la branch existente `milestone/v1.5-mutations`" and lists
no push. The remote branch exists but is stale:

```
$ git rev-parse origin/milestone/v1.5-mutations
ce77ed4a609c90de869e0b04e7fcc8e117653897

$ git rev-parse HEAD
6bbf2ce573aeeff7e406385f832e0eeba1ab6c83

$ git status -sb
## milestone/v1.5-mutations...origin/milestone/v1.5-mutations [ahead 96]

$ git rev-list --count ce77ed4..HEAD
96

$ git merge-base --is-ancestor ce77ed4 HEAD && echo "fast-forward possible"
fast-forward possible
```

`ce77ed4` is `docs(memory): update market-data-client latest release to v0.3.1` — the last thing
pushed, from the v0.3.1 release. **All 96 commits of Phases 25, 26, 27 and the Phase 28 context
are local-only.** `gh pr create` against an unpushed branch will either fail outright or prompt
interactively (which an agent cannot answer). [VERIFIED: `git rev-list`, `git merge-base`]

**Planner action:** add an explicit `git push origin milestone/v1.5-mutations` step in Plan 01,
after all release-prep commits, before any `gh pr create`. It is a plain fast-forward — no
`--force` needed, and `--force` must be forbidden (D-10's rationale about not rewriting published
history applies here too).

### C-2 — RESOLVED UNKNOWN: `main` has NO branch protection

CONTEXT.md `<specifics>` § Verification / Risk Notes calls this a "Blocker externo (no resoluble
desde el repo)". It is resolvable, and the answer is: **no protection exists.**

```
$ gh api repos/gravity-quant/market-libs/branches/main/protection
{"message":"Not Found", ... "status":"404"}

$ gh api repos/gravity-quant/market-libs/rulesets
[]

$ gh api repos/gravity-quant/market-libs/branches/main --jq '{name,protected}'
{"name":"main","protected":false}
```

[VERIFIED: GitHub REST API via `gh`, token scopes `gist, read:org, repo, workflow`]

The empty `rulesets` array is returned with `includes_parents` defaulting to true, so no
org-level ruleset from `gravity-quant` applies either.

**Consequences the planner must encode:**

1. The 15-green gate is **advisory**. `gh pr merge --merge` will succeed against a red or
   pending PR. Nothing in GitHub blocks it.
2. Therefore the D-18(a) checkpoint is the **only** enforcement point. The plan must make the
   pre-merge verification a hard automated assertion, not a glance — see § Release Mechanics for
   the exact `gh pr checks` assertion form.
3. Conversely: there is **no** "required status checks" list to satisfy, no CODEOWNERS review
   requirement, and no admin-bypass complication. The merge will not stall on approvals.

### C-3 — UNDER-SPECIFIED: D-04 site 5 (release memory) needs 6 edits, not 2

D-04 names two regions of `market-data-client-releases.md`: the frontmatter `description:`
(line 3) and the `**Latest published:**` block (line 13). The v0.3.1 precedent commit `ce77ed4`
changed **+24/−14 lines across six regions**: [VERIFIED: `git show ce77ed4 -- <memory file>`]

| # | Region | Current (HEAD) state | Why it must change |
|---|--------|----------------------|--------------------|
| 1 | frontmatter `description:` (L3) | "latest published release is v0.3.1 (patch — …)" | D-04 names it |
| 2 | `**Latest published:**` block (L13-15) | "`market-data-client-v0.3.1`** (2026-08-01, tag on merge commit `7b0e0b2`, PR #9, `release.yml` run `30674988499`)" | D-04 names it |
| 3 | version-specific "what it adds/fixes" section (L17-37) | "**v0.3.1 fixes (quick task `260731-t9o`):**" + "**v0.3.0 added …, carried forward into v0.3.1:**" | precedent added a new lead section per release |
| 4 | **two** "Scope note" paragraphs (L39-46) | "the mutation surface is **symbols-write only**. Calendar mutations (MUT-MD-02, Phase 26) and the live verification (LIVE-MUT-01, Phase 27) are **NOT yet done**… never live develop." | **Factually false after v0.4.0.** Both Phase 26 and Phase 27 are complete. Leaving this is a correctness bug in the artifact whose entire purpose is telling future agents what shipped. |
| 5 | `**Prior releases:**` paragraph (L48-53) | starts at `v0.3.0` | precedent demotes the previous "latest" into this list |
| 6 | **both** install command lines (L56-57) | pin `market-data-client-v0.3.1` (git URL) and `market_data_client-0.3.1-py3-none-any.whl` (wheel URL) | **Not updating these means the memory instructs consumers to install the superseded version.** |

**Planner action:** keep D-04's "exactly five sites" count intact (this is still one file), but
specify all six regions in the task's `<action>`. Region 4 and region 6 are the ones most likely
to be silently skipped and are the two with real downstream consequences.

### Minor drift (non-blocking, but do not hard-code the old numbers)

| Claim | CONTEXT.md | Verified now | Note |
|-------|-----------|--------------|------|
| commits ahead of `origin/main` | "95 commits ahead" (D-10, `<code_context>`) | **97** (`git rev-list --left-right --count origin/main...HEAD` → `2  97`) | +2 = the Phase 28 context commits `773e1ca`, `6bbf2ce` landed after the count was taken. D-10's *substance* is unaffected. |
| `__version__` line | D-04 says `__init__.py:134` | **134 ✓** | (`26-RESEARCH.md:910` cites `:118` — that citation is stale; D-04 is the correct one.) |

---

## Live World State (re-verified 2026-08-01)

Every row below is the literal output of a command run in this session.

### Git / branch

| Fact | Value | Command |
|------|-------|---------|
| Current branch | `milestone/v1.5-mutations` | `git status -sb` |
| Working tree | **clean** (0 entries) | `git status --porcelain \| wc -l` → `0` |
| Local `HEAD` | `6bbf2ce573aeeff7e406385f832e0eeba1ab6c83` | `git rev-parse HEAD` |
| vs `origin/main` | **2 behind / 97 ahead** | `git rev-list --left-right --count origin/main...HEAD` → `2  97` |
| vs `origin/milestone/v1.5-mutations` | **0 behind / 96 ahead** (fast-forward) | `git rev-list --left-right --count origin/milestone/v1.5-mutations...HEAD` → `0  96` |
| Remote | `git@github.com:gravity-quant/market-libs.git` (SSH), auth OK (`Hi sebadlf!`) | `git remote -v`; `ssh -T git@github.com` |

### D-10 verification — "2 behind is cosmetic" — **CONFIRMED**

```
$ git diff --stat HEAD...origin/main
                              (empty output)

$ git rev-parse origin/main^{tree}
b404a5dd526807d6934e499b16c3cb3da3ad25ad
$ git merge-base origin/main HEAD
7f051ae28d2f9526b3a329a619571f79fa7c6785
$ git rev-parse 7f051ae^{tree}
b404a5dd526807d6934e499b16c3cb3da3ad25ad          # identical

$ git merge-tree --write-tree origin/main HEAD    # exit 0 → conflict-free

$ git log --oneline origin/main ^HEAD
7b0e0b2 Merge pull request #9 from gravity-quant/milestone/v1.5-mutations
ea92dd8 Merge pull request #8 from gravity-quant/milestone/v1.5-mutations
```

Both "behind" commits are pure merge commits whose tree is already the merge-base tree.
D-10 stands exactly as written. [VERIFIED: git]

### Tags — `v0.3.0` and `v0.3.1` ARE published; `v0.4.0` does NOT exist

Local (`git tag -l 'market-data-client-v*'`): `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.3.1`.

On `origin` (`git ls-remote --tags origin`), all four are annotated tags:

| Tag | Tag object | Peeled commit (`^{}`) |
|-----|-----------|----------------------|
| `market-data-client-v0.1.0` | `3bd9a49…` | `1ea655db…` |
| `market-data-client-v0.2.0` | `df00a0c1…` | `5903f75a…` |
| `market-data-client-v0.3.0` | `65b5e8ac…` | `ea92dd89…` (PR #8 merge) |
| `market-data-client-v0.3.1` | `103277b2…` | `7b0e0b2f…` (PR #9 merge) |
| **`market-data-client-v0.4.0`** | **absent on local AND `origin`** | — |

D-01's core premise is confirmed: pushing `v0.3.0` would be rejected as an existing ref;
`v0.4.0` is free. [VERIFIED: `git ls-remote --tags origin`]

> Trivia (harmless): local tag `v1.3` exists but is not on `origin`. Unrelated to this phase.

### Version strings — in sync at `0.3.1`

```
packages/market-data-client/pyproject.toml:3      version = "0.3.1"
.../src/market_data_client/__init__.py:134        __version__ = "0.3.1"
uv.lock:487-488                                   name = "market-data-client"
                                                  version = "0.3.1"
```

All three agree. `README.md:60` is `## Changelog`, `:61` blank, `:62` `### v0.3.1` — so the
`### v0.4.0` entry is inserted starting at line 62. [VERIFIED: `grep -n`, `sed -n`]

### GitHub state

| Fact | Value |
|------|-------|
| `gh` auth | ✓ `sebadlf`, token scopes `gist, read:org, repo, workflow` |
| Repo | `gravity-quant/market-libs`, **visibility `public`**, default branch `main` |
| Open PRs | **none** — PRs #1-#9 all `MERGED`. A new PR must be created. |
| Merge methods allowed | `allow_merge_commit: true`, `allow_squash_merge: true`, `allow_rebase_merge: true` — D-11's `--merge` is available |
| `delete_branch_on_merge` | `false` — the branch survives the merge |
| Branch protection | **none** (see C-2) |

Last two PRs, for title convention (D-12):

- #9 — `release: market-data-client v0.3.1 (get_latest_batch envelope fix)` — merged 2026-08-01T00:11:30Z
- #8 — `release: market-data-client v0.3.0 (symbols write + mutating-gate)` — merged 2026-07-31T23:31:35Z

[VERIFIED: `gh pr list`, `gh api repos/gravity-quant/market-libs`]

### Local gates — all green on the current tree (re-run this session)

| Gate | Command | Result |
|------|---------|--------|
| uv.lock sync | `uv lock --check` | `Resolved 48 packages in 2ms` (in sync **at 0.3.1**) |
| ruff lint | `uv run ruff check .` | `All checks passed!` |
| ruff format | `uv run ruff format --check .` | `201 files already formatted` |
| import-linter | `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` |
| mypy (global src) | `uv run mypy` | `Success: no issues found in 51 source files` |
| package tests | `uv run pytest packages/market-data-client -q` | **387 passed in 0.51s** |
| pre-commit (all files) | `uv run pre-commit run --all-files` | all 9 hooks **Passed** |

D-15 confirmed and extended — the full `pre-commit run --all-files` (the exact command `ci.yml:68`
runs) passes with zero file rewrites. `main_market_data.py` is **146,495 bytes** (143 KB), under
`check-added-large-files`' 500 KB default. [VERIFIED: local execution]

### Toolchain

| Tool | Version | Notes |
|------|---------|-------|
| `uv` | 0.11.3 | repo CI uses `astral-sh/setup-uv@v3` (unpinned version) |
| `gh` | 2.90.0 | `pr create`, `pr checks`, `pr merge`, `release view`, `api`, `run` all available |
| `git` | 2.39.5 (Apple Git-154) | supports `merge-tree --write-tree` |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Version bump (`pyproject.toml`, `__version__`) | Repo / source-of-truth files | — | `release.yml:47` reads `pyproject.toml` with `awk`; `__version__` is the runtime-visible mirror |
| Lockfile version registration | uv workspace resolver (`uv.lock`) | — | Workspace members carry their own version in the lock; only `uv lock` may regenerate it |
| Changelog / consumer-facing docs | Package README | in-repo release memory | README ships in the sdist/wheel; the memory file is agent-facing only |
| Requirement/roadmap re-point (D-02) | `.planning/` artifacts | — | Planning tier, not shipped in the wheel |
| Quality gate | GitHub Actions (`ci.yml`) | local pre-commit | CI is the authority for the 15 checks; local run is a pre-flight to avoid a red PR |
| Integration into `main` | GitHub PR merge (`gh pr merge --merge`) | — | Merge commit is the tag anchor (D-11) |
| Artifact build + publication | GitHub Actions (`release.yml`), triggered by tag push | `uv build --package` inside the runner | Zero local build; the tag is the only trigger |
| Irreversibility control | Human operator (D-18 checkpoints) | — | No branch protection exists (C-2) — the human IS the gate |

---

## Standard Stack

No new packages. This phase installs nothing.

### Core (already present, unchanged)

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `uv` | 0.11.3 | `uv lock` refresh; `uv build --package` (in CI) | Already the workspace manager; `uv lock --check` is CI gate #1 [VERIFIED: `ci.yml:32-33`] |
| `gh` CLI | 2.90.0 | PR create/checks/merge, Release verification | Used by all 5 prior releases of this monorepo [VERIFIED: `24-02-SUMMARY.md`] |
| `git` | 2.39.5 | branch push, annotated tag, tag push | — |
| GitHub Actions | `ci.yml` + `release.yml` | the 15-check gate and the artifact pipeline | Generic and unedited since Phase 24 [VERIFIED: `release.yml` read in full] |
| `hatchling` | (per-package build backend) | wheel + sdist build inside `release.yml` | Declared in `packages/market-data-client/pyproject.toml` |

### Alternatives Considered

None. Every mechanism is locked by D-06/D-08/D-11 and has three prior successful runs in this
exact repo (`v0.1.0` run `30641107566`, `v0.3.0` run `30673218876`, `v0.3.1` run `30674988499`).

---

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.**

`uv lock` will be run, but it re-resolves the *existing* dependency set with only the local
workspace member's version string changed. The precedent commit `7f051ae` shows the exact
resulting diff: [VERIFIED: `git show 7f051ae -- uv.lock`]

```diff
@@ -485,7 +485,7 @@ wheels = [

 [[package]]
 name = "market-data-client"
-version = "0.3.0"
+version = "0.3.1"
 source = { editable = "packages/market-data-client" }
 dependencies = [
     { name = "httpx" },
```

**Two lines. Nothing else.** D-05's prediction is exact.

**Verification gate for the planner:** after `uv lock`, assert the churn is confined to the
version line — `git diff --stat uv.lock` must read `uv.lock | 2 +-`. Any larger diff means uv
re-resolved third-party dependencies (a version-range drift or a stale cache), which would smuggle
an unreviewed dependency change into a release PR. That is the only supply-chain risk this phase
carries, and it is cheap to detect.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Public Surface Delta (what the changelog must describe)

Computed by diffing tag `market-data-client-v0.3.1` against `HEAD`. [VERIFIED: `git diff`, `git show <tag>:<path>`]

### The 13 new public names (D-01)

**8 additions to the flat `__all__`** (`__init__.py`), from
`diff <(v0.3.1 __all__) <(HEAD __all__)`:

| Kind | Name |
|------|------|
| Request model | `MarketHoursIn` |
| Request model | `HolidayIn` |
| Request model | `HolidaysIn` |
| Function | `set_calendar_config` |
| Function | `delete_calendar_config` |
| Function | `preview_calendar_config` |
| Function | `add_holidays` |
| Function | `delete_holiday` |

**5 async counterparts** in `market_data_client.aio` (module-level shims, not re-exported into
the flat namespace per the monorepo convention):
`set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`, `add_holidays`,
`delete_holiday`.

**8 + 5 = 13.** D-01's count is exactly right. Commit `c92861b feat(26-04): re-export the 8
calendar-write public names` is the corroborating history.

Full signatures (sync `Client` methods + module shims are identical; `aio` mirrors with `async`):

```python
def set_calendar_config(config: MarketHoursIn) -> CalendarConfig: ...
def delete_calendar_config() -> CalendarConfig: ...
def preview_calendar_config(config: MarketHoursIn) -> CalendarConfig: ...
def add_holidays(holidays: HolidaysIn) -> dict[str, Any]: ...
def delete_holiday(day: str) -> dict[str, Any]: ...
```

### The `CalendarDay` field replacement — MUST be called out (D-03, non-negotiable)

| v0.3.1 (`models.py:313-323`) | HEAD (`models.py:506-532`) |
|------------------------------|----------------------------|
| `date: str` | `day: str` |
| `marketId: str` | `closed: bool` |
| `isBusinessDay: bool` | `description: str` |
| — | `open_time: str \| None = None` |
| — | `close_time: str \| None = None` |

Old field set **removed outright** — no aliases. The HEAD docstring states the rationale
(`models.py:518-522`): the old names "exist NOWHERE on the wire — they were the PROVISIONAL A1/A2
guess", and `parse_calendar_response` iterated the envelope's keys instead of `days[]`, so no
released consumer could ever have read a populated instance. This is D-13's argument, and D-03
requires the changelog to name the swap explicitly anyway.

### Non-breaking Phase-27 changes also shipping in v0.4.0

| Change | Evidence |
|--------|----------|
| `update_symbol(symbol_id: str)` → `int \| str` — **widened** at all 4 routes | `diff` of `client.py` + `aio.py` signature lists shows only `str` → `int \| str`; return type `list[Symbol]` unchanged on all 6 signatures |
| `Symbol` gains 5 fields, **all defaulted** | `id: int = 0`, `market_id: str = ""`, `created_at: str = ""`, `updated_at: str = ""`, `received_at: str \| None = None` |
| `Symbol.marketId` **preserved** as deprecated alias, mirrored from wire `market_id` via `from_api` override | `27-VERIFICATION.md:143-146` |
| Symbols-write envelope unwrapped, `list[Symbol]` preserved | `27-VERIFICATION.md:141-142` |

All strictly additive/widening → non-breaking. [VERIFIED: `git diff` of signatures + `models.py`]

### Diff scope of the PR

```
$ git diff --stat market-data-client-v0.3.1..HEAD | tail -1
 90 files changed, 23293 insertions(+), 312 deletions(-)
```

Package source + tests: 17 files, +3661/−63. Non-`.planning`, non-package: 13 files (notably
`main_market_data.py` +2418, the `verification/` harness, the release memory). The rest is
`.planning/` artifacts, deliberately kept per D-09. [VERIFIED: `git diff --stat`]

---

## CI Gate Anatomy

### The 15 checks — exact names, verified from PR #9

`gh pr checks 9` returned exactly 15 rows, all `pass`: [VERIFIED: `gh pr checks 9`]

```
Lint y formato (ruff)
pre-commit hooks
Type check (mypy)
Tests · ambito-financiero-client · py3.12
Tests · ambito-financiero-client · py3.13
Tests · higyrus-client · py3.12
Tests · higyrus-client · py3.13
Tests · iol-client · py3.12
Tests · iol-client · py3.13
Tests · market-data-client · py3.12
Tests · market-data-client · py3.13
Tests · matriz-client · py3.12
Tests · matriz-client · py3.13
Tests · wallets-client · py3.12
Tests · wallets-client · py3.13
```

D-13's arithmetic (3 + 6×2 = 15) is confirmed empirically, not just from the YAML. The two rows
the phase specifically owns are `Tests · market-data-client · py3.12` and `· py3.13`
(SC #2). Prior run took 12s and 13s respectively.

### What each job actually runs

| Job | Steps | Touches `verification/`? |
|-----|-------|--------------------------|
| `lint` (`ci.yml:23`) | `uv lock --check` → `uv sync --frozen` → `ruff check .` → `ruff format --check .` → `lint-imports` → inline grep for `logging.basicConfig`/`logging.root.` in `packages/*/src/` | `ruff check .` **does** lint `verification/` (it's `.`), but lint is green today |
| `pre-commit` (`ci.yml:52`) | `pre-commit run --all-files --show-diff-on-failure` | mypy hook scoped `files: ^packages/.*/src/`; whitespace/EOF/large-file hooks cover all files |
| `typecheck` (`ci.yml:70`) | `uv run mypy` (root `files` = 5 packages, **excludes market-data-client**) then a loop `mypy packages/$pkg/tests` over the same 5 | no |
| `test` × 12 (`ci.yml:91`) | `uv run --python <ver> pytest packages/<pkg> --cov=…` | **no** — scoped to `packages/<pkg>` |

**D-14 confirmed at the source level:** the root `testpaths = ["packages","tests","verification"]`
(`pyproject.toml:106`) is never exercised by any workflow — the only `pytest` invocation in CI is
`ci.yml:112-118` with an explicit `packages/${{ matrix.package }}` path argument, which overrides
`testpaths`. The 19 pre-existing matriz `verification/` failures are invisible to CI.
[VERIFIED: `ci.yml` read in full, `pyproject.toml:106`]

**D-16 confirmed:** `pyproject.toml:97` `files = [higyrus, wallets, matriz, iol, ambito]` — no
market-data-client. `[tool.importlinter] root_packages` (`:141-146`) lists 4 — no
market-data-client. `ci.yml:85` loop iterates the same 5. This is a *coverage gap*, not a
*failure*: nothing goes red. Real mypy coverage for this package comes from the pre-commit hook
(`files: ^packages/.*/src/`), which runs in the `pre-commit` job and passes.

### `ci.yml` trigger conditions — a subtlety worth knowing

```yaml
on:
  pull_request:
    branches: [main]
    paths-ignore: ["**.md", ".gitignore"]
```

A PR whose entire diff is Markdown would run **zero** checks, and `gh pr checks` would report
"no checks". This PR's diff contains 90 files including `.py`, `.toml`, and `uv.lock`, so all 15
run. **But:** if the plan ever splits the release into a docs-only PR, that PR would show no
checks at all — do not interpret "no checks" as "green". [CITED: `.github/workflows/ci.yml:9-13`]

Also: `concurrency: cancel-in-progress: true` (`ci.yml:20`). Pushing another commit to the branch
while checks are running **cancels** the in-flight run. A cancelled check is neither pass nor
fail; `gh pr checks` shows it as such and the assertion must not treat it as green.

### `release.yml` — exact gates the tag must satisfy

Read in full this session. Trigger: `on: push: tags: ["*-client-v*"]`. Four sequential gates:

1. **Regex** (`:28`):
   `^([a-z][a-z0-9-]*-client)-v([0-9]+\.[0-9]+\.[0-9]+([.+-][a-zA-Z0-9.+-]+)?)$`
   → `market-data-client-v0.4.0` matches: group 1 = `market-data-client`, group 2 = `0.4.0`.
   Failure message: `::error::Tag inválido: '<TAG>'. Esperado: <package>-client-v<version>`.
2. **Directory existence** (`:34`): `packages/market-data-client` must exist. ✓
3. **Version match** (`:42-51`):
   ```bash
   PYPROJECT_VERSION=$(awk -F\" '/^version[[:space:]]*=/{print $2; exit}' "packages/$PACKAGE/pyproject.toml")
   [[ "$PYPROJECT_VERSION" != "$TAG_VERSION" ]] && error "Tag ($TAG_VERSION) ≠ pyproject.toml ($PYPROJECT_VERSION)"
   ```
   Note the `awk` takes the **first** `^version =` line in the file — for
   `market-data-client/pyproject.toml` that's line 3, inside `[project]`. Correct.
   **This check runs against the tagged commit's tree**, which is why the tag must sit on the
   merge commit *after* the bump has landed on `main`.
4. **Build + publish** (`:58-70`): `uv build --package market-data-client --out-dir dist`, then
   `gh release create "$TAG" --title "market-data-client v0.4.0" --generate-notes dist/*`.

`--generate-notes` means the GitHub Release body is auto-generated from merged PRs — the PR body
(Claude's discretion per CONTEXT) does not need to be release-notes-shaped.
[VERIFIED: `.github/workflows/release.yml` full read]

**`__version__` is NOT checked by the pipeline.** Only `pyproject.toml` is. If `__init__.py:134`
drifts, the release ships silently mislabelled at runtime. Local verification is the only
defense — see § Common Pitfalls P-4.

---

## Release Mechanics — exact command forms

Derived from the recovered Phase 24 plan/summary (`b07a924`, `f79d350`) plus this session's
verification. These are the concrete steps the planner should encode.

### Phase A — release prep (reversible)

```bash
# 1. Bump pyproject FIRST (uv lock reads it)
#    packages/market-data-client/pyproject.toml:3   version = "0.3.1" -> "0.4.0"
# 2. Bump the runtime mirror
#    .../src/market_data_client/__init__.py:134     __version__ = "0.3.1" -> "0.4.0"
# 3. Insert the `### v0.4.0` changelog entry at README.md:62 (above `### v0.3.1`)
# 4. Update the release memory (6 regions — see C-3)
# 5. D-02 re-point: REQUIREMENTS.md:28 + :65, ROADMAP.md:19 + :188-198
# 6. D-16 backlog entry: ROADMAP.md § Backlog

# 7. Refresh the lock (AFTER the pyproject bump)
uv lock
git diff --stat uv.lock            # MUST be exactly: uv.lock | 2 +-

# 8. Assert the three version sites agree
grep -n '^version = ' packages/market-data-client/pyproject.toml
grep -n '__version__' packages/market-data-client/src/market_data_client/__init__.py
grep -n -A1 'name = "market-data-client"' uv.lock

# 9. Re-run the local mirror of the CI gate
uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run lint-imports
uv run mypy
uv run pytest packages/market-data-client -q
uv run pre-commit run --all-files

# 10. Commit, then PUSH (C-1 — required, missing from CONTEXT.md)
git push origin milestone/v1.5-mutations       # plain fast-forward; NEVER --force
```

Automated assertion for the version-sync step (usable verbatim in a `<verify><automated>` block):

```bash
V=$(awk -F\" '/^version[[:space:]]*=/{print $2; exit}' packages/market-data-client/pyproject.toml)
test "$V" = "0.4.0" \
  && grep -qx '__version__ = "0.4.0"' packages/market-data-client/src/market_data_client/__init__.py \
  && grep -A1 '^name = "market-data-client"$' uv.lock | grep -qx 'version = "0.4.0"' \
  && grep -qx '### v0.4.0' packages/market-data-client/README.md \
  && uv lock --check >/dev/null 2>&1 \
  && echo PASS
```

### Phase B — open the PR and wait for green (reversible)

```bash
gh auth status                       # must exit 0
test -z "$(git status --porcelain)"  # clean tree (D-18 precondition)

gh pr create --base main --head milestone/v1.5-mutations \
  --title "release: market-data-client v0.4.0 (calendar write + live-verified mutation fixes)" \
  --body "$(cat <<'EOF'
...
EOF
)"

# Enumerate + wait. `--watch` blocks until all checks settle.
gh pr checks --watch
gh pr checks                         # final snapshot: 15 rows
```

**Hard assertion for the 15-green gate** (because GitHub will not enforce it — C-2):

```bash
PR=$(gh pr view --json number --jq .number)
TOTAL=$(gh pr checks "$PR" | wc -l | tr -d ' ')
PASSED=$(gh pr checks "$PR" | awk -F'\t' '$2=="pass"' | wc -l | tr -d ' ')
MD=$(gh pr checks "$PR" | grep -c 'Tests · market-data-client · py3\.1[23]')
test "$TOTAL" = "15" && test "$PASSED" = "15" && test "$MD" = "2" && echo PASS
```

`gh pr checks` exits non-zero when any check is failing or pending, so `&& echo PASS` alone is not
sufficient — count explicitly. Statuses other than `pass` include `fail`, `pending`, `skipping`,
and `cancelled` (the last is reachable via `cancel-in-progress`).

### Phase C — CHECKPOINT (a), then merge (IRREVERSIBLE)

```bash
# Only after the operator replies "approved"
gh pr merge <N> --merge                 # NOT --squash, NOT --rebase (D-11)

git fetch origin main --tags
MERGE_SHA=$(git rev-parse origin/main)
git log -1 --format='%H %p %s' "$MERGE_SHA"   # must show TWO parents
```

### Phase D — CHECKPOINT (b), then tag (IRREVERSIBLE)

```bash
# Only after the operator replies "approved" a second time
git tag -a market-data-client-v0.4.0 "$MERGE_SHA" \
  -m "market-data-client v0.4.0 — calendar write (MUT-MD-02) + live-verified mutation fixes (LIVE-MUT-01)"
git push origin market-data-client-v0.4.0        # triggers release.yml
```

Phase 24 precedent: *"Created an annotated tag on the exact merge-commit SHA, not on branch HEAD,
so release.yml's version-match + regex gates run against the merged state."*
[VERIFIED: `24-02-SUMMARY.md` key-decisions, recovered from `f79d350`]

### Phase E — verify the Release

```bash
gh run list --workflow=release.yml --limit 3
gh run watch <run-id>

gh release view market-data-client-v0.4.0 --json assets --jq '.assets[].name'
# expect: market_data_client-0.4.0-py3-none-any.whl
#         market_data_client-0.4.0.tar.gz

git rev-list -n1 market-data-client-v0.4.0        # == $MERGE_SHA
```

Automated:

```bash
git fetch --tags origin >/dev/null 2>&1
git tag | grep -qx 'market-data-client-v0.4.0' \
  && gh release view market-data-client-v0.4.0 --json assets --jq '.assets[].name' | grep -q '\.whl$' \
  && gh release view market-data-client-v0.4.0 --json assets --jq '.assets[].name' | grep -q '\.tar\.gz$' \
  && echo PASS
```

---

## Architecture Patterns

### Release flow

```
                          ┌─ D-18(a) blocking human checkpoint ─┐
                          │                                     │
  local edits (5 sites)   │                                     │
  + D-02 re-point         │                                     ▼
  + D-16 backlog          │                            gh pr merge --merge
        │                 │                                     │
        ▼                 │                                     ▼
     uv lock  ──►  local gate re-run  ──►  git push  ──►  gh pr create  ──►  ci.yml (15 checks)
   (2-line churn)   (7 commands)          (96 commits,        │                    │
        │                                  fast-fwd)          └── gh pr checks ────┘
        │                                                                 │
        │                                                            all 15 pass
        │                                                                 │
        └──────────────────────────────────────────────────────► merge commit on main
                                                                          │
                          ┌─ D-18(b) blocking human checkpoint ────────────┤
                          │                                               ▼
                          └──────────────► git tag -a <merge-sha> ──► git push origin <tag>
                                                                          │
                                                              release.yml (tag push trigger)
                                                                          │
                                          ┌───────────────────────────────┼──────────────────────┐
                                          ▼                               ▼                      ▼
                                   regex + dir check          pyproject == tag version    uv build --package
                                                                                                 │
                                                                                                 ▼
                                                                            gh release create --generate-notes
                                                                                 (wheel + sdist assets)
```

### Pattern 1 — Two-plan phase (Phase 24 precedent)

**What:** Plan 01 = reversible release prep (`autonomous: true`). Plan 02 = the irreversible
publish (`autonomous: false`, `depends_on: [28-01]`, wave 2), with the human checkpoints inline.
**When to use:** any phase whose second half performs outward-facing irreversible ops.
**Why:** a failed prep can be amended freely; the irreversible half is isolated, small, and
re-entrant after a checkpoint (a continuation agent can execute only the post-approval task).

### Pattern 2 — Checkpoint task shape

The Phase 24 checkpoint (recovered verbatim from `b07a924`) is the template to copy:

```xml
<task type="checkpoint:human-verify" gate="blocking">
  <name>Task N: Blocking go/no-go gate before irreversible merge (D-18a)</name>
  <action>PAUSE. This is a blocking human checkpoint (autonomous:false). Do NOT merge the PR
    or push any tag until the operator explicitly replies "approved". If "abort", stop cleanly
    with no irreversible action taken. Present the PR link, `gh pr checks` status, and the
    exact tag string to be published.</action>
  <what-built>…</what-built>
  <how-to-verify>…numbered steps the human performs…</how-to-verify>
  <resume-signal>Type "approved" to proceed with merge, or "abort" (optionally describe
    blockers) to stop before any irreversible action.</resume-signal>
</task>
```

D-18 requires **two** of these — one before the merge, one before the tag push. Phase 24 used a
single combined gate; D-18 explicitly splits them. Do not collapse them back.

### Pattern 3 — Changelog entry shape (`README.md`)

The three prior entries establish the format exactly. Structure to match:

```markdown
### v0.4.0

**<Bold lead line naming the bump class and the headline change>**
(<parenthetical semver justification>).

- **<Feature area> (<REQ-ID>):** <prose, Spanish, backtick-quoted API names, wrapped ~95 cols,
  continuation lines indented 2 spaces>.
- **<Next area>:** …
```

Verbatim models from the file:

- `README.md:74-75` — `**Nueva superficie de escritura: symbols detrás de un mutating-gate de seguridad**` / `(features nuevas, minor bump — no rompe la superficie de lectura v0.2.0).`
- `README.md:84` — `- **Symbols write (MUT-MD-01):** \`create_symbol\` (\`NewSymbol\`), \`create_symbols\` …`
- `README.md:64` — `**Bugfix (patch):** \`get_latest_batch\` devolvía snapshots vacíos.`
- `README.md:92-93` — `**Breaking changes** (semver minor bump en línea 0.x) — reconciliación del cliente contra la API en vivo tras la verificación \`LIVE-MD-01\`:`

Note the v0.2.0 entry proves the repo already has a precedent for **naming a breaking model
change explicitly in the changelog while shipping it as a minor** — precisely the shape D-03
mandates for `CalendarDay`. Reuse that voice.

Conventions to hold: Spanish prose; requirement IDs inline in the bold lead (`(MUT-MD-02)`);
backticks on every identifier; bullet continuation lines indented exactly 2 spaces; blank line
between the entry heading and body, and between entries. Note that `trailing-whitespace` and
`end-of-file-fixer` pre-commit hooks run over this file in CI.

### Anti-Patterns to Avoid

- **Editing `.github/workflows/*`** — D-06. `release.yml` already matches; any edit re-opens a
  settled question and expands the release diff.
- **`git push --force`** on the release branch — the push is a plain fast-forward; a force-push
  would rewrite the 96 commits that Phase 25-27 SUMMARYs cross-reference by SHA.
- **Squash-merging** — D-11. Would collapse 97 commits and orphan every SHA citation in
  `.planning/phases/2[5-7]-*/`.
- **Tagging branch HEAD instead of the merge commit** — `release.yml`'s version check runs on the
  tagged tree; tagging the branch tip would produce a Release whose commit is not on `main`.
- **Rebasing onto `origin/main`** — D-10, and it would rewrite published history reachable from
  tags `v0.3.0`/`v0.3.1`.
- **Running `/gsd-pr-branch`** — D-09; filtering `.planning/` would strip ~60 KB of live-verification
  evidence from `main`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Building wheel + sdist | local `uv build` + manual upload | tag push → `release.yml` | The pipeline builds from the *tagged* tree in a clean runner; a local build could embed uncommitted state |
| Release notes | hand-written body | `--generate-notes` (already in `release.yml:69`) | Auto-derived from merged PRs; consistent with the 5 prior releases |
| Tag/version consistency check | ad-hoc grep script | `release.yml:42-51` (`awk` on pyproject vs tag) | Already an enforced pipeline gate; fails the build loudly on mismatch |
| Refreshing the lockfile version | hand-editing `uv.lock:488` | `uv lock` | Hand-editing risks desyncing the lock's internal hashes; `uv lock --check` is CI gate #1 |
| Enumerating CI checks | parsing `ci.yml` | `gh pr checks` | The YAML tells you what *should* run; `gh pr checks` tells you what *did* — the difference matters with `paths-ignore` + `cancel-in-progress` |
| Merge-commit creation | `git merge` + `git push origin main` locally | `gh pr merge --merge` | Goes through the PR (attribution, closes the PR, matches all prior releases) |

**Key insight:** every mechanism this phase needs already exists and has run successfully three
times for this exact package. The failure modes here are **sequencing and verification**, not
tooling. The plan's value is in ordering the steps correctly and asserting hard at each gate.

---

## Common Pitfalls

### P-1: Opening the PR before pushing the branch

**What goes wrong:** `gh pr create` fails or interactively prompts ("Where should we push the
`milestone/v1.5-mutations` branch?"), which an agent cannot answer, and the task hangs or errors.
**Why:** `origin/milestone/v1.5-mutations` is 96 commits stale (C-1) and CONTEXT.md has no push
step.
**How to avoid:** explicit `git push origin milestone/v1.5-mutations` as its own step at the end
of Plan 01.
**Warning signs:** `gh pr create` output mentioning "push" or "head branch"; `git status -sb`
showing `[ahead N]`.

### P-2: Running `uv lock` before the `pyproject.toml` bump

**What goes wrong:** `uv lock` regenerates the lock at the *old* version `0.3.1`; the later
pyproject edit then desyncs the lock, and CI check 1 of 15 (`uv lock --check`, `ci.yml:32`) fails.
**Why:** `uv lock` reads workspace member versions from `pyproject.toml`.
**How to avoid:** strict order — bump `pyproject.toml` → `uv lock` → assert `uv lock --check`.
**Warning signs:** `git diff uv.lock` shows no change, or `uv lock --check` reports out-of-date.

### P-3: Pushing the tag before the merge lands

**What goes wrong:** `release.yml` fires against a commit that is not on `main` (or, if tagging
branch HEAD before the merge, against a tree whose `pyproject.toml` may not match). Even when the
version matches, the Release permanently points at a commit outside `main`'s history. **Tags on
GitHub Releases cannot be cleanly re-pointed** — deleting the tag leaves the Release orphaned or
forces deleting a public Release.
**Why:** `on: push: tags:` fires immediately; there is no ordering guard in the workflow.
**How to avoid:** capture `MERGE_SHA=$(git rev-parse origin/main)` **after** `gh pr merge` +
`git fetch origin main`, and tag that SHA explicitly. Never `git tag <name>` with no commit-ish.
**Warning signs:** `git rev-list -n1 <tag>` not equal to `origin/main`; the merge commit having
one parent instead of two.

### P-4: `pyproject.version` and `__version__` drifting

**What goes wrong:** `release.yml` validates only `pyproject.toml` (`:47`). If `__init__.py:134`
still reads `0.3.1`, the pipeline goes green, the Release ships, and every consumer reading
`market_data_client.__version__` gets the wrong answer — undetectable until someone files a bug.
**Why:** the pipeline gate is one-sided by design.
**How to avoid:** the three-way assertion in § Release Mechanics Phase A step 8 (pyproject ==
`__version__` == uv.lock) as an automated `<verify>` in Plan 01.
**Warning signs:** none at release time — this is precisely why it must be asserted locally.

### P-5: The D-14 trap — waiting for a full-suite green

**What goes wrong:** the agent runs `uv run pytest` (root, `testpaths` includes `verification/`),
sees "19 failed, 19 errors", concludes the branch is not ready, and blocks indefinitely.
**Why:** the root `testpaths` is never used by CI (verified: the only pytest call passes an
explicit path argument that overrides it), but it *is* the default for a bare local `pytest`.
**How to avoid:** every local test command in the plan must be scoped —
`uv run pytest packages/market-data-client -q`. Never a bare `uv run pytest`. State the expected
count: **387 passed**.
**Warning signs:** a test run reporting ~258 tests with matriz `probe_login_sync` errors.

### P-6: Assuming GitHub enforces the 15-green gate

**What goes wrong:** the agent runs `gh pr merge --merge` while checks are pending or red, and
GitHub accepts it — no protection exists (C-2). Red code lands on `main` and gets tagged.
**Why:** `protected: false`, no rulesets, no required status checks.
**How to avoid:** the explicit count-based assertion (15 rows, 15 `pass`, 2 of them
market-data-client) as a hard gate before the D-18(a) checkpoint, and surface the counts to the
operator in the checkpoint's `<what-built>`.
**Warning signs:** `gh pr checks` output with fewer than 15 rows, or any row not `pass`.

### P-7: Pushing extra commits while CI is running

**What goes wrong:** `concurrency: cancel-in-progress: true` (`ci.yml:20`) cancels the in-flight
run. `gh pr checks` then shows cancelled/pending rows that are neither pass nor fail, and a naive
"no failures" assertion reads them as green.
**How to avoid:** finish all commits before `gh pr create`; if a fix is needed, re-run
`gh pr checks --watch` to completion and re-assert the 15/15 count.

### P-8: Leaving the release memory half-updated

**What goes wrong:** only D-04's two named regions get edited, so the file still tells future
agents to `uv add …@market-data-client-v0.3.1`, still links the `0.3.1` wheel URL, and still
asserts "Calendar mutations (MUT-MD-02, Phase 26) and the live mutation verification
(LIVE-MUT-01, Phase 27) are NOT yet done" — false as of this release.
**How to avoid:** enumerate all six regions in the task action (table in C-3). Assert with
`! grep -q '0\.3\.1' <memory file>` after the edit (no stray `0.3.1` outside the "Prior releases"
paragraph — note the assertion needs the "Prior releases" exemption, so prefer asserting on the
install lines specifically).

### P-9: A `uv lock` diff larger than 2 lines

**What goes wrong:** a dependency-range drift or stale uv cache causes `uv lock` to re-resolve
third-party packages, smuggling unreviewed dependency changes into a release PR.
**How to avoid:** assert `git diff --stat uv.lock` reads `uv.lock | 2 +-` exactly. If larger,
stop and inspect before committing.

---

## Code Examples

### Phase 24 Plan 02 — the exact irreversible-ops task template

Recovered from git history (`git show b07a924:.planning/phases/24-release-prep-publish-v0-1-0/24-02-PLAN.md`;
the directory was removed during milestone cleanup and is no longer on disk).

```yaml
---
phase: 24-release-prep-publish-v0-1-0
plan: 02
type: execute
wave: 2
depends_on: [24-01]
files_modified: []
autonomous: false
requirements: [PUB-MD-01]
user_setup:
  - service: github
    why: "Merging the PR and pushing the release tag are outward-facing GitHub operations"
    dashboard_config:
      - task: "Ensure `gh` CLI is authenticated (verified in Task 1)"
        location: "local shell — `gh auth status`"
must_haves:
  truths:
    - "A single PR … → main is open, carrying … plus this phase's edits, with .planning/ artifacts kept (D-06, D-07)"
    - "All CI checks on the PR are green, including the new market-data-client test jobs (SC-3)"
    - "The PR is merged to main only after an explicit human go/no-go at the merge point (D-08, D-09)"
    - "A tag market-data-client-v0.1.0 exists on the merge commit and triggers release.yml (D-10)"
    - "A GitHub Release market-data-client-v0.1.0 exists with wheel + sdist assets (SC-4)"
  artifacts:
    - path: "git-tag:market-data-client-v0.1.0"
      provides: "per-package release tag on the merge commit (verified via `git tag` + `git rev-list`)"
      contains: "market-data-client-v0.1.0"
    - path: "gh-release:market-data-client-v0.1.0"
      provides: "GitHub Release with wheel + sdist assets (verified via `gh release view`)"
      contains: ".whl"
  key_links:
    - from: "git-tag:market-data-client-v0.1.0"
      to: ".github/workflows/release.yml"
      via: "tag matching `*-client-v*` triggers release.yml which builds wheel+sdist and creates the Release"
      pattern: "market-data-client-v0.1.0"
---
```

Its Task 1 verify block (adapt the branch name and add the 15-count assertion):

```bash
test "$(git rev-parse --abbrev-ref HEAD)" = "release/v0.2.0-bump" \
  && gh auth status >/dev/null 2>&1 \
  && test -z "$(git status --porcelain)" \
  && gh pr view --json state,baseRefName | grep -q '"baseRefName":"main"' \
  && gh pr checks 2>/dev/null | grep -qi 'market-data-client' \
  && ! gh pr checks 2>/dev/null | grep -qiE '\bfail' \
  && echo PASS
```

> **Improve on this.** The `! grep -qiE '\bfail'` form passes when checks are *pending* or
> *cancelled*, and passes when `gh pr checks` returns nothing at all (the `paths-ignore` case).
> Given C-2 (no branch protection), replace it with the explicit 15/15 count assertion from
> § Release Mechanics Phase B.

### Its Task 3 verify block (the shape to reuse for the Release check)

```bash
git fetch --tags origin >/dev/null 2>&1
git tag | grep -qx 'market-data-client-v0.1.0' \
  && git rev-list -n1 market-data-client-v0.1.0 >/dev/null \
  && gh release view market-data-client-v0.1.0 --json assets 2>/dev/null | grep -q '\.whl' \
  && gh release view market-data-client-v0.1.0 --json assets 2>/dev/null | grep -q '\.tar\.gz' \
  && echo PASS
```

### The memory-file update precedent (`ce77ed4`)

```diff
-description: market-data-client latest published release is v0.3.0 (symbols write + mutating-gate, non-breaking over v0.2.0 read surface). v0.2.0 read-only superseded; v0.1.0 buggy. Install via git subdirectory or the GitHub Release wheel — not on PyPI.
+description: market-data-client latest published release is v0.3.1 (patch — get_latest_batch envelope-unwrap fix, on top of v0.3.0 symbols write + mutating-gate). v0.2.0/v0.3.0 superseded; v0.1.0 buggy. Install via git subdirectory or the GitHub Release wheel — not on PyPI.

-**Latest published: `market-data-client-v0.3.0`** (2026-07-31, tag on merge commit `ea92dd8`,
-PR #8, `release.yml` run `30673218876`). …
+**Latest published: `market-data-client-v0.3.1`** (2026-08-01, tag on merge commit `7b0e0b2`,
+PR #9, `release.yml` run `30674988499`). …

-- git, pinned to tag (recommended): `uv add "market-data-client @ git+…@market-data-client-v0.3.0#subdirectory=packages/market-data-client"` …
+- git, pinned to tag (recommended): `uv add "market-data-client @ git+…@market-data-client-v0.3.1#subdirectory=packages/market-data-client"` …
-- release wheel: `pip install "https://github.com/…/market-data-client-v0.3.0/market_data_client-0.3.0-py3-none-any.whl"`.
+- release wheel: `pip install "https://github.com/…/market-data-client-v0.3.1/market_data_client-0.3.1-py3-none-any.whl"`.
```

Note the "Latest published" block cites the `release.yml` **run ID** — so the plan must capture
that ID from `gh run list --workflow=release.yml` in Phase E before writing the memory update, or
sequence the memory edit into a follow-up commit. **Precedent: the v0.3.1 memory update was a
separate commit (`ce77ed4`) landed AFTER the release**, not part of the bump commit `7f051ae`.
This is the natural resolution: the memory file cannot cite a run ID that doesn't exist yet.

> **Planning consequence:** D-04 site 5 cannot be fully completed in Plan 01. Either (a) write the
> memory update in Plan 01 with the run ID/merge SHA left as a placeholder and amend in Plan 02
> (matching the `ce77ed4` precedent of a post-release commit), or (b) defer site 5 entirely to a
> final Plan 02 task after `gh release view` succeeds. **(b) matches the precedent exactly** and is
> recommended. Note this means the memory-update commit lands on `main`… actually on the release
> branch post-merge — precedent `ce77ed4` sits on `milestone/v1.5-mutations` after `7b0e0b2`, i.e.
> it was committed to the branch and shipped in the *next* PR. The planner should decide explicitly;
> the simplest correct option is to commit it to `milestone/v1.5-mutations` after the tag push, as
> `ce77ed4` did.

### The v0.3.1 bump commit — the exact prep-commit shape

```
$ git show --stat 7f051ae
    chore(market-data-client): bump to v0.3.1 (get_latest_batch envelope fix)

    Patch — fix parse_latest_response to unwrap the batch {items:[...]} envelope
    so get_latest_batch returns populated snapshots (was returning N empties).
    pyproject + __version__ + README changelog + uv.lock aligned at 0.3.1.

 packages/market-data-client/README.md                          | 10 ++++++++++
 packages/market-data-client/pyproject.toml                     |  2 +-
 packages/market-data-client/src/market_data_client/__init__.py |  2 +-
 uv.lock                                                        |  2 +-
 4 files changed, 13 insertions(+), 3 deletions(-)
```

Four files, one commit, `chore(market-data-client): bump to vX.Y.Z (<scope>)`. Reuse this shape.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dedicated `release/*` branch per release (PRs #4-#7) | Ship from the milestone branch `milestone/v1.5-mutations` (PRs #8, #9) | 2026-07-31 | D-08 follows the newer pattern; no branch creation step |
| Repo-wide version bump (PR #4 "bump all packages to 0.2.0") | Per-package version + per-package tag | Phase 24, 2026-07-31 | Only `market-data-client` version moves; the other 5 stay put |
| `v0.3.0` as the v1.5 release target | `v0.4.0` (v0.3.0/v0.3.1 shipped mid-milestone) | 2026-07-31 (PRs #8, #9) | The entire premise of D-01/D-02 |

**Deprecated/outdated in the artifacts:**

- `ROADMAP.md:19, :188-198` and `REQUIREMENTS.md:28` — say `v0.3.0`; D-02 re-points them.
- `CLAUDE.md:74` — says `market-data-client v0.2.0`, three releases stale. Explicitly out of
  scope (D-07).
- `26-RESEARCH.md:910` cites `__init__.py:118` for `__version__`; it is now line 134.
- The release memory's two "Scope note" paragraphs — will be false after this release (C-3).

---

## Runtime State Inventory

Not a rename/refactor phase, but this release does mutate **out-of-repo state**, so the same
discipline applies:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no databases or datastores carry the version string. Verified: no version-keyed state outside the four files listed. | none |
| Live service config | **GitHub remote refs**: `origin/main` (gains a merge commit), `origin/milestone/v1.5-mutations` (gains 96 commits + subsequent), `refs/tags/market-data-client-v0.4.0` (new). **GitHub Releases**: a new public Release object. None of these live in git working state — all are outward-facing and irreversible. | gated by D-18 checkpoints |
| OS-registered state | None — no scheduled tasks, daemons, or process managers reference this package. | none |
| Secrets/env vars | `GH_TOKEN` inside `release.yml` is `${{ github.token }}` (ephemeral, auto-scoped). Local `gh` token is `gho_…` with `repo, workflow, gist, read:org`. No `.env` is tracked (`git ls-files` returns only the six `.env.example` templates); `.gitignore:47-48` covers `.env`/`.env.local`. **No credential values in the release diff** — see § Security Domain. | none |
| Build artifacts | The wheel + sdist are built **inside the GitHub runner** from the tagged tree, not locally. No local `dist/`, `*.egg-info`, or installed-package staleness to reconcile. The editable workspace install picks up the new `__version__` on next import — no reinstall needed. | none |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` | branch push, tag creation | ✓ | 2.39.5 (Apple Git-154) | — |
| SSH auth to github.com | branch + tag push (`git@github.com:` remote) | ✓ | `Hi sebadlf!` | — |
| `gh` CLI | PR create/checks/merge, Release verification, API reads | ✓ | 2.90.0 | — |
| `gh` auth (`repo` scope) | merge PR, read protection API | ✓ | scopes `gist, read:org, repo, workflow` | — |
| `uv` | `uv lock`, local gate re-run | ✓ | 0.11.3 | — |
| GitHub Actions runners | the 15 CI checks + `release.yml` | ✓ (PR #9 ran 2026-08-01) | `ubuntu-latest` | — |
| Network to github.com | everything outward-facing | ✓ | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

---

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`. This phase ships **no
production code**, so "tests" here means the CI gate plus release-state assertions.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` (`:104-121`) |
| Quick run command | `uv run pytest packages/market-data-client -q` (387 tests, 0.51s) |
| Full suite command | `uv run pytest packages/market-data-client` (**scoped — never bare `uv run pytest`**, see P-5) |
| CI equivalent | `uv run --python <3.12\|3.13> pytest packages/market-data-client --cov=… ` (`ci.yml:112-118`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| PUB-MUT-01 | Three version sites read `0.4.0` and agree | assertion | `V=$(awk -F\" '/^version[[:space:]]*=/{print $2;exit}' packages/market-data-client/pyproject.toml); test "$V" = 0.4.0 && grep -qx '__version__ = "0.4.0"' packages/market-data-client/src/market_data_client/__init__.py && grep -A1 '^name = "market-data-client"$' uv.lock \| grep -qx 'version = "0.4.0"'` | ✅ inline |
| PUB-MUT-01 | `uv.lock` is in sync and churned by exactly 2 lines | assertion | `uv lock --check && git diff --stat uv.lock \| grep -q 'uv.lock | 2 +-'` | ✅ inline |
| PUB-MUT-01 | README changelog has a `### v0.4.0` entry naming the `CalendarDay` swap (D-03) | assertion | `grep -qx '### v0.4.0' packages/market-data-client/README.md && grep -q 'CalendarDay' packages/market-data-client/README.md` | ✅ inline |
| PUB-MUT-01 | Package tests still green (no accidental source edit) | unit | `uv run pytest packages/market-data-client -q` → `387 passed` | ✅ existing |
| PUB-MUT-01 | Local mirror of all four CI jobs is green | lint/type | `uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run mypy && uv run pre-commit run --all-files` | ✅ existing |
| PUB-MUT-01 | Branch is pushed (C-1) | assertion | `test "$(git rev-parse HEAD)" = "$(git rev-parse origin/milestone/v1.5-mutations)"` | ✅ inline |
| PUB-MUT-01 | PR open against `main` with 15/15 green (SC #2) | integration | the count-based assertion in § Release Mechanics Phase B | ✅ inline |
| PUB-MUT-01 | Merge commit on `main` has two parents (D-11) | assertion | `test "$(git rev-list --parents -n1 origin/main \| wc -w)" -eq 3` | ✅ inline |
| PUB-MUT-01 | Tag resolves to the merge commit (SC #3) | assertion | `test "$(git rev-list -n1 market-data-client-v0.4.0)" = "$(git rev-parse origin/main)"` | ✅ inline |
| PUB-MUT-01 | GitHub Release has wheel + sdist (SC #3) | integration | `gh release view market-data-client-v0.4.0 --json assets --jq '.assets[].name'` contains `.whl` and `.tar.gz` | ✅ inline |
| PUB-MUT-01 | Workflows untouched (D-06) | assertion | `git diff --name-only market-data-client-v0.3.1..HEAD -- .github/workflows \| wc -l` → `0` | ✅ inline |
| PUB-MUT-01 | v0.2.0 read surface intact (SC #4) | assertion | `uv run python -c "import market_data_client as m; assert all(n in m.__all__ for n in ('get_market_data','get_latest','get_calendar','CalendarDay','Symbol','MarketDataSnapshot'))"` | ✅ inline |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/market-data-client -q` (0.5s) + the version-sync assertion
- **Per wave merge:** full local CI mirror (6 commands, ~2 min)
- **Phase gate:** 15/15 green on the PR, then `gh release view` shows both assets

### Wave 0 Gaps

None — no new test files are needed. Every check is an assertion over release state or an
existing test suite. Existing infrastructure covers all phase requirements.

---

## Security Domain

`workflow.security_enforcement` is `true`, `security_asvs_level` is 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (tooling) | `gh` OAuth token (`gho_…`) + SSH key for git push. Never echo either. `release.yml` uses ephemeral `${{ github.token }}`, not a PAT. |
| V3 Session Management | no | no sessions in scope |
| V4 Access Control | yes | GitHub repo permissions are the only control — **`main` is unprotected (C-2)**, so the D-18 human checkpoints are the sole access gate on an irreversible public publish |
| V5 Input Validation | yes (pipeline) | `release.yml:28` regex-validates the tag before any action; `:34` validates the package directory; `:42-51` validates version equality. All three run before `uv build`. |
| V6 Cryptography | no | no crypto code changes; artifacts are unsigned (consistent with all 5 prior releases — sigstore/attestation is not in scope) |
| V14 Configuration | yes | `.env` files must never be committed; `.gitignore:47-48` covers them |

### Known Threat Patterns for this release

| Pattern | STRIDE | Standard Mitigation | Status |
|---------|--------|---------------------|--------|
| Credential leak into a **public** artifact (repo visibility is `public`; the PR ships ~60 KB of live-verification evidence and a 143 KB live driver to `main`) | Information Disclosure | scan the diff before merge | **VERIFIED CLEAN this session** — see below |
| Tag/version mismatch producing a mislabelled public artifact | Tampering | `release.yml:42-51` | Enforced by pipeline; `__version__` additionally asserted locally (P-4) |
| Malformed tag triggering an unintended Release | Tampering | `release.yml:28` regex + D-18(b) checkpoint | Enforced |
| Unreviewed dependency change smuggled via `uv.lock` | Supply Chain / Tampering | assert `uv.lock \| 2 +-` (P-9) | Plan must assert |
| Red code merged to `main` (no branch protection) | Tampering | D-18(a) checkpoint + explicit 15/15 assertion (P-6) | Plan must assert |
| Token echoed into logs by an agent | Information Disclosure | never `echo $GH_TOKEN`; use `gh auth status` (redacts) | Convention |

**Secret scan performed this session** over the full `origin/main...HEAD` diff (90 files):

```
$ git ls-files | grep -E '(^|/)\.env$'                        → (none; only 6 .env.example)
$ grep -n 'env' .gitignore                                     → .env, .env.local  (lines 47-48)
$ git diff origin/main...HEAD | grep -nE 'eyJ[A-Za-z0-9_-]{20,}'   → (no JWTs)
$ grep -rniE '(client_secret|CLIENT_SECRET)\s*[=:]\s*["']?[A-Za-z0-9_-]{20,}' <changed files>
                                                               → (no matches)
```

**Result: clean.** No Auth0 client secret, bearer token, or JWT appears in the release diff.
The develop hostname (`market-data-develop.bbsa.com.ar`) is already public in v0.2.0+ as the
default `base_url` — no new exposure. [VERIFIED: local grep over the diff]

**Recommendation for the planner:** re-run this scan as an automated verify step in Plan 01
immediately before the push, since the diff is the thing being published and it grows with every
commit added during the phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `gh pr create` from an unpushed branch fails or prompts interactively rather than auto-pushing. The push step is recommended regardless, so the failure mode is only "an unnecessary explicit step". | C-1, P-1 | Low — the explicit push is correct and harmless either way |
| A2 | `gh pr checks` reports `cancelled` as a distinct non-`pass` status string. The count-based assertion (`$2=="pass"` × 15) is robust to the exact string either way. | P-7, Release Mechanics | Low — the assertion form does not depend on the exact label |
| A3 | `check-added-large-files` default threshold is 500 KB. `.pre-commit-config.yaml:9` passes no `--maxkb`, and the largest changed file is 143 KB, so this holds with a 3.5× margin. Confirmed empirically: `pre-commit run --all-files` **passed** this session. | Live World State | None — empirically verified |
| A4 | GitHub Release tags cannot be cleanly re-pointed once a Release exists (deleting the tag orphans or requires deleting the public Release). | P-3 | Low — the mitigation (tag the correct SHA) is correct regardless |
| A5 | The v0.4.0 memory-file update should follow `ce77ed4`'s pattern of a post-release commit on the branch. D-04 does not specify timing; the run-ID dependency makes a post-release commit the only fully-correct option. | Code Examples, C-3 | Low — the planner should decide explicitly; either ordering satisfies D-04 |

---

## Open Questions

1. **Where does the release-memory commit land (D-04 site 5 timing)?**
   - *What we know:* the "Latest published" block cites the `release.yml` run ID and the merge
     commit SHA, neither of which exists until after the tag push. The v0.3.1 precedent
     (`ce77ed4`) committed the memory update to `milestone/v1.5-mutations` **after** the merge
     `7b0e0b2` — meaning it rode into `main` in the *next* PR.
   - *What's unclear:* whether the operator wants that same trailing-commit pattern (memory
     update on the branch, landing on `main` only in some future PR) or wants it on `main`
     immediately.
   - *Recommendation:* follow the precedent — a final Plan 02 task committing the memory update
     to `milestone/v1.5-mutations` after `gh release view` confirms the assets. Flag it in the
     phase SUMMARY so it isn't lost. Do not block the release on it.

2. **Should the D-02 re-point and D-16 backlog entry be one commit or two?**
   - *What we know:* both are `.planning/` edits, both are Claude's discretion for wording.
   - *Recommendation:* one `docs(28):` commit covering `REQUIREMENTS.md` + `ROADMAP.md`, separate
     from the `chore(market-data-client): bump to v0.4.0` commit (which should stay at the exact
     4-file shape of `7f051ae`).

3. **Does the residual D-03 risk need any pre-release probe?**
   - *What we know:* D-13's non-breaking claim for `CalendarDay` was never independently audited
     (`27-VERIFICATION.md` covered only D-22). The repo is public, so an unknown consumer is
     theoretically possible.
   - *What's unclear:* whether any real consumer of `market-data-client` exists outside this org.
   - *Recommendation:* none beyond the D-03 changelog callout — the mitigation is already locked
     and the probe (searching GitHub for dependents of an unpublished-to-PyPI, git-installed
     package) is not reliably answerable. Note the risk in the phase SUMMARY.

---

## Sources

### Primary (HIGH confidence — verified by command execution in this repo, this session)

- `git status -sb`, `git rev-list --left-right --count`, `git merge-base`, `git rev-parse`,
  `git diff --stat`, `git merge-tree --write-tree`, `git ls-remote --tags origin`, `git tag -l`,
  `git log`, `git show` — branch, tag, tree, and history state
- `gh auth status`, `gh pr list`, `gh pr checks 9`, `gh repo view`,
  `gh api repos/gravity-quant/market-libs`, `gh api …/branches/main`,
  `gh api …/branches/main/protection`, `gh api …/rulesets` — GitHub state and branch protection
- `.github/workflows/release.yml` (full read, 70 lines), `.github/workflows/ci.yml` (full read,
  124 lines), `.pre-commit-config.yaml` (full read), root `pyproject.toml:90-150`
- `packages/market-data-client/pyproject.toml`, `.../src/market_data_client/__init__.py`,
  `.../models.py`, `.../client.py`, `.../aio.py`, `.../README.md`, `uv.lock`
- `uv lock --check`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run lint-imports`,
  `uv run mypy`, `uv run pytest packages/market-data-client -q`, `uv run pre-commit run --all-files`
- Git history recovery: `git show b07a924:.planning/phases/24-release-prep-publish-v0-1-0/24-02-PLAN.md`,
  `git show f79d350:…/24-02-SUMMARY.md`, `git show 7f051ae`, `git show ce77ed4`

### Secondary (project artifacts read in full or in the cited ranges)

- `.planning/phases/28-release-prep-publish-v0-3-0/28-CONTEXT.md` (full)
- `.planning/REQUIREMENTS.md` (full), `.planning/ROADMAP.md:19, :188-198, :235-265`
- `.planning/STATE.md` (tail), `.planning/config.json` (full)
- `.planning/phases/27-verificaci-n-en-vivo-segura-fixes/27-CONTEXT.md:135-150, :210-228`
- `.planning/phases/27-verificaci-n-en-vivo-segura-fixes/27-VERIFICATION.md:130-158`
- `.planning/phases/26-calendar-write/26-RESEARCH.md:905-915`
- `./CLAUDE.md` (project instructions — stack, conventions, GSD workflow enforcement)

### Tertiary (LOW confidence)

None. No web search or external documentation was needed — this phase is entirely governed by
in-repo state and precedent.

---

## Project Constraints (from CLAUDE.md)

| Directive | Relevance to Phase 28 |
|-----------|----------------------|
| Tech stack: Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict — must pass existing CI | The 15-check gate is exactly this; no stack change |
| No shared code between packages; fixes stay inside each package | This phase touches only `market-data-client` files + `.planning/` + `uv.lock` |
| Dual sync/async mirroring required for logic fixes | N/A — no logic changes; the mirroring already landed in Phases 26-27 |
| Credentials live in per-package `.env`; **never commit `.env` or expose credentials in logs, reports, or tests** | Directly load-bearing — see § Security Domain; scan verified clean |
| GSD workflow enforcement: no direct repo edits outside a GSD command | Plan 01/02 execution satisfies this |
| Ruff: line-length 100, double quotes, 4-space indent | README/changelog is Markdown (unaffected); `.py` edits are one-line version strings |
| Every module starts with `from __future__ import annotations` | N/A — no new modules |

**No conflicts** between CLAUDE.md and any locked decision in CONTEXT.md.

---

## Metadata

**Confidence breakdown:**

- Live world state: **HIGH** — every value is literal command output from this session
- Release mechanics: **HIGH** — command forms recovered from the actual Phase 24 plan/summary that
  executed successfully, cross-checked against `release.yml` read in full
- CI gate: **HIGH** — the 15 check names were read off a real completed run (PR #9), not inferred
  from YAML
- Public surface delta: **HIGH** — computed by diffing the published tag against `HEAD`
- Contradictions (C-1/C-2/C-3): **HIGH** — each backed by a specific command output
- Pitfalls: **MEDIUM-HIGH** — P-1..P-6, P-8, P-9 are grounded in verified state; P-3's
  "tags can't be re-pointed" and P-7's exact `gh pr checks` label are [ASSUMED] (A2, A4), but the
  recommended mitigations are correct regardless

**Research date:** 2026-08-01
**Valid until:** **~24 hours.** This is a fast-moving live-ops phase — the branch is unpushed, no
PR is open, and no new tag exists. If more than a day elapses, re-run § Live World State's
commands before planning. In particular re-check: `git status -sb`, `git ls-remote --tags origin`,
`gh pr list`, and the two version sites.
