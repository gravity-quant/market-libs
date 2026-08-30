# Phase 40: Releases breaking coordinados - Research

**Researched:** 2026-08-30
**Domain:** Release engineering — coordinated multi-package breaking release over a git-tag pipeline
**Confidence:** HIGH (every load-bearing fact re-measured live in this session against the working tree, `origin`, and the GitHub API)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Alcance del bump**

- **D-01:** Se bumpean **exactamente tres** paquetes confirmados por evidencia de v1.7:
  `market-data-client` **0.5.0 → 0.6.0** (Phase 36 — `market_data` dict→Null Object tipado),
  `iol-client` **0.3.0 → 0.4.0** (Phase 38 — `Cotizacion.puntas`/`Titulo.puntas` pierden
  `| None`), `matriz-client` **0.2.0 → 0.3.0** (Phase 37 — `AccountReport.portfolio` retipado +
  dos campos `dict[str, Any]` → modelos tipados + fix de envelope-unwrap). `ambito-financiero-client`
  y `wallets-client` NO se tocan — Phase 38 (NOBJ-AUD-01) midió 0 violaciones en ambos.

- **D-02 [checkpoint explícito, no resuelto en discuss]:** `higyrus-client` carga una ruptura
  **ya shippeada en código pero nunca publicada**: `get_health()` devuelve `Health` tipado desde
  Phase 31 (v1.5, commit `bf04b2f`), `pyproject.toml` sigue en `0.2.0`, y el README todavía dice
  "el bump lo hace la Phase 34" — afirmación que Phase 34 mismo invalidó (D-01 de `34-CONTEXT.md`
  excluyó higyrus explícitamente; `34-01-SUMMARY.md` clasificó el diff como "aditivo", no
  ameritando bump). Ningún artefacto de planning reasigna esta deuda a ninguna fase. Consistente
  con el precedente del proyecto (D-08/D-18: nunca resolver en silencio una decisión
  scope-adjacent), esto **no se decide acá** — se presenta como pregunta explícita en el primer
  checkpoint (pre-merge) de esta fase:
  - Si el operador aprueba foldear: higyrus se suma como **cuarto** paquete bumpeado
    (`0.2.0 → 0.3.0`), con su sección de changelog reescrita al formato `## Unreleased —
    BREAKING` (reemplazando la sección obsoleta `### v0.3.0 — sin publicar todavía`).
  - Si el operador declina: la sección del README se corrige de todos modos (deja de citar
    "Phase 34" como ejecutor, ya shippeada sin este cambio) y se reasigna a un destino concreto
    o se marca explícitamente "pendiente, sin fase asignada" — no se re-difiere en silencio una
    tercera vez.

**Changelog de `matriz-client` — se escribe desde cero**

- **D-03:** `packages/matriz-client/README.md` no tiene ninguna sección de Changelog hoy (a
  diferencia de iol-client/market-data-client, que ya tienen `## Unreleased — BREAKING` escrito
  por sus propias fases). Esta fase debe **autoría completa** de esa sección, cubriendo lo medido
  en `37-01-SUMMARY.md`…`37-05-SUMMARY.md`:
  - `AccountReport.portfolio`: `dict[str, Any]` (vía mapping) → `float | None` (hoja escalar).
  - `InstrumentDetail.tickPriceRanges`: `dict[str, Any]` → `dict[str, TickPriceRange]`.
  - `DetailedPosition.report`: `dict[str, Any]` → `dict[str, dict[str, InstrumentPositionReport]]`.
  - `AccountReport.detailedAccountReports`: `dict[str, Any]` → `dict[str, DetailedAccountReport]`.
  - Fix de envelope-unwrap en `get_detailed_positions`/`get_account_report` (antes decodificaban
    desde el nivel de anidamiento equivocado, devolviendo modelos con todos los campos en su
    default) — documentar como corrección de comportamiento, no solo de tipo.
  - Las **6 alias properties** nuevas (`bids`/`offers`/`last`/`settlement`/`close`/
    `open_interest`) van documentadas aparte como **aditivas, no breaking** — no entran en la
    tabla de migración.

- **D-04:** `matriz-client` es el único de los 6 paquetes sin `__version__` en `__init__.py`.
  Verificado: `release.yml:47` lee la versión **solo** de `pyproject.toml` (nunca de
  `__init__.py`), y matriz ya publicó dos releases (`v0.1.1`, `v0.2.0`) sin `__version__` sin
  incidente. **No es un requisito** para pasar el pipeline — agregarlo es discrecional, solo por
  consistencia con la convención de Exports documentada en `CLAUDE.md`.

**Vehículo de PR — branch nueva, no reuse**

- **D-05:** A diferencia de Phase 34 (que actualizó el PR #12 existente sobre una branch de
  milestone ya viva), **no existe ninguna branch ni PR de v1.7** hoy: `main` local está 180
  commits adelante de `origin/main` (HEAD remoto = merge de PR #14, cierre de v1.6), sin PR
  abierto (`gh pr list` vacío) y sin branch remota de v1.7. Esta fase crea una branch nueva —
  `milestone/v1.7-nobj-null-objects` (seleccionado, sigue el patrón `milestone/v1.5-mutations`
  ya usado) — pushea los 180 commits pendientes, y abre un PR nuevo a `main` cubriendo las Fases
  35-40 y las versiones bumpeadas.

- **D-06:** Conteo de CI verde = **exactamente 15 checks** (12 del matrix de test — 6 paquetes ×
  py3.12/py3.13 — más 3 jobs no-matrix: `lint`, `pre-commit`, `typecheck`), mismo cálculo que
  Phase 34 sobre el mismo `ci.yml` sin editar desde entonces. El criterio 2 del ROADMAP
  ("6 paquetes × py3.12/py3.13 más los 4 gates") se lee como 4 **job definitions** (`lint`,
  `pre-commit`, `typecheck`, `test` — este último fan-out en 12), no 4 jobs adicionales sobre el
  matrix.

**Ops irreversibles — dos gates, no tres**

- **D-07:** Exactamente **dos checkpoints humanos bloqueantes**, implementados como dos
  `PLAN.md` separados (`autonomous: false` cada uno), espejando literalmente el split
  `34-02-PLAN.md`/`34-03-PLAN.md`: (a) antes de mergear el PR, (b) antes de pushear los tags.
  Nunca colapsados, nunca auto-aprobados pese a `auto_advance: true` + `mode: yolo` (confirmados
  activos en `.planning/config.json`). El checkpoint (a) incluye la pregunta D-02 (higyrus)
  explícitamente.

- **D-08:** El merge usa **merge commit real** (`gh pr merge --merge`) — nunca squash, nunca
  rebase.

- **D-09:** Cada tag es una **annotated tag** creada sobre el SHA del merge commit **re-resuelto
  en vivo post-merge** (no la branch HEAD pre-merge). Una sola aprobación de checkpoint (b) cubre
  el push de **todos** los tags de esta ronda (3 o 4, según D-02) en una misma operación.

- **D-10:** `uv.lock` se refresca **exactamente una vez**, después de bumpear todos los
  `pyproject.toml` de la ronda, antes de abrir el PR.

- **D-11:** Verificación post-publicación: instalar desde el wheel público de cada paquete
  publicado y ejercer una cadena profunda ya existente en el paquete instalado (criterio 3 del
  ROADMAP).

**Divergencia sin corregir de `market-data-client` (`market_id`/`active`)**

- **D-12 [checkpoint explícito, no resuelto en discuss]:** `36-DEFERRED-market-data-leaves.md`
  documenta una divergencia medida y no corregida (`market_id`/`active` llegan `null` sobre
  campos no-`Optional`, `strict_decode` levanta) y nombra explícitamente "el bump coordinado de
  Phase 40" como el checkpoint natural para resolverla. Pero el alcance de esta fase
  (`PUB-NOBJ-01`) es **publicar rupturas ya decididas**, no decidir rupturas nuevas — Phase 39 no
  tocó ni resolvió este ítem. No se resuelve en silencio en ninguna dirección: se presenta como
  ítem adicional en el checkpoint (a) (pre-merge).
  - Si el operador aprueba ensanchar los campos ahora: se suma como una fila más a la tabla de
    migración de `market-data-client`, dentro del mismo bump breaking.
  - Si declina: la nota "espera checkpoint del operador" del README se corrige para no seguir
    apuntando a "Phase 40" como destino futuro (esta fase deja de ser un destino vigente en
    cuanto se publique) — se reasigna a una fase concreta o se marca "pendiente, sin fase
    asignada".

### Claude's Discretion

- Wording exacto de la nueva sección de changelog de `matriz-client` (seguir la voz/formato ya
  establecido por iol-client/market-data-client: español, tabla antes/después, línea líder en
  negrita).
- Título y body exactos del PR nuevo.
- Si agregar o no `__version__` a `matriz_client/__init__.py` (discrecional per D-04).
- Agrupamiento y orden de commits dentro de la fase.

### Deferred Ideas (OUT OF SCOPE)

- Cualquier corrección funcional a `market_id`/`active` de `market-data-client` más allá de lo
  que el operador apruebe en el checkpoint — si se declina, se convierte en una fase futura
  correctamente nombrada, no en un carry-forward silencioso (D-12).
- Agregar `__version__` a `matriz_client/__init__.py` — discrecional, no requerido (D-04).
- El bump de `higyrus-client` — si el operador declina foldearlo, necesita una reasignación real,
  no un "en algún momento" tácito (D-02).

**Fuera de alcance (Phase Boundary):** cualquier cambio funcional nuevo a los paquetes; editar
`.github/workflows/release.yml` o `.github/workflows/ci.yml`; versionado repo-wide (`v1.1`…`v1.6`
son tags de milestone, no de paquete, y no se tocan).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| `PUB-NOBJ-01` | "los paquetes cuya superficie pública cambió se publican por el pipeline de tags con bump breaking + changelog callout + tabla de migración, bajo doble gate humano (precedente D-08/D-18, nunca colapsado ni auto-aprobado)" | § Bump Set (surface-diff evidence per package, measured against each package's published tag), § Migration Table Content (locked before/after rows for all 4 candidate packages), § Release Playbook (the 3-plan mechanical sequence with the two blocking gates), § Common Pitfalls P1 (why the two scope questions cannot live at the pre-merge gate without a re-loop) |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

| Directive | Effect on this phase |
|-----------|----------------------|
| Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict — "toda extensión y fix debe respetar el stack y pasar el CI existente" | The local CI mirror is mandatory before the push; no gate may be patched to pass. |
| "sin código compartido entre paquetes (por diseño). Los fixes se aplican dentro de cada paquete" | If D-12 is approved, the widening lands only inside `market-data-client`. No cross-package touch. |
| "cualquier fix de lógica debe espejarse en `client.py` y `aio.py` del mismo paquete" | If D-12 is approved: the change is in `models.py` (shared by both surfaces), so the *mirror* obligation is satisfied structurally — but the sync **and** async regression tests both need updating (`test_snapshot_no_data_row.py` has `_async` twins for every affected test). |
| "las credenciales viven en `.env` por paquete; nunca commitear `.env` ni exponer credenciales en logs, reportes o tests" | The credential scan over the full `origin/main...HEAD` diff is mandatory immediately before the push (this diff is 182 commits and becomes public). |
| Versioning convention: "Explicit `__all__` list … `__version__` string" | matriz-client violates this today (D-04). Adding it is discretionary; do **not** add a `test_version_metadata.py` for matriz as a side effect. |
| **GSD Workflow Enforcement**: "Do not make direct repo edits outside a GSD workflow" | All edits land through the phase's PLAN tasks. |

---

## Summary

This is a **release-engineering phase with zero new product code**. Every line of the surface being
published was built and live-verified by Phases 35-39. The work is: (1) author/de-provisionalize
four changelog sections, (2) bump three (or four) `pyproject.toml` version sites, (3) refresh
`uv.lock` exactly once, (4) create a brand-new branch + PR, (5) prove CI green by explicit count,
(6) merge with a real merge commit behind a human gate, (7) annotate-tag the re-resolved merge SHA
and push behind a **second** human gate, (8) verify each public wheel installs and its deep chain
works. The direct precedent — `.planning/milestones/v1.6-phases/34-releases-por-paquete/` — is a
three-plan split (prep / merge-gate / tag-gate) that this phase should mirror almost verbatim.

There are **four structural deltas from Phase 34**, and each one is a place where copying 34
verbatim produces a wrong plan:

1. **The 182 pending commits sit on local `main` itself**, not on a milestone branch. Phase 34
   pushed an existing branch; this phase must `git checkout -b milestone/v1.7-nobj-null-objects`
   first, and every "HEAD == origin/<branch>" precondition re-points accordingly.
2. **Three tags on one merge commit, not two** (four if D-02 folds higyrus). Mechanically identical
   — `release.yml`'s concurrency group is per-`github.ref` so the runs do not serialize — but the
   `uv.lock` churn expectation moves from `2 2` to `3 3` (or `4 4`), and the count-based CI
   assertion needs three (or four) per-package row counts, not two.
3. **Criterion 3 demands a post-publish wheel-install verification as part of the phase.** Phase 34
   did that work in **UAT**, not in a PLAN task. Phase 40 must make it an explicit `<task type="auto">`
   after the tag push. Concrete, already-verified deep-chain assertions are supplied below.
4. **Two real scope questions (D-02 higyrus, D-12 `market_id`/`active`) are parked at the pre-merge
   gate.** An "approve" on either forces a full re-loop of prep → `uv lock` → push → CI → re-assert
   15/15 — and in higyrus's case a *second* `uv lock`, which directly contradicts D-10. This is the
   single highest-value planning problem in the phase and is treated at length in Pitfall P1 and
   Open Question OQ-1.

The working tree is measurably green as of this research run (every CI gate mirrored locally,
1934 package tests + 128 driver-lock tests passing), `release.yml` is byte-identical at every
relevant ref, and `gh` is authenticated with `repo` + `workflow` scopes. Nothing blocks execution.

**Primary recommendation:** Mirror Phase 34's three-plan split (`40-01` prep / `40-02` merge gate /
`40-03` tag gate + post-publish verification), but **hoist the two scope questions (D-02, D-12) into
a `checkpoint:decision` gate at the top of `40-01`**, before any version bump, and re-present their
resolved answers as read-back facts inside the `40-02` pre-merge briefing. That keeps `uv lock`
single-run (D-10), keeps CI running once against final content, and still leaves exactly two
blocking gates on irreversible operations (D-07). Resolve this with the operator before planning —
see OQ-1.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Version declaration (source of truth) | Package metadata (`packages/<pkg>/pyproject.toml`) | — | `release.yml:47` reads the version **only** from `pyproject.toml` via `awk -F\" '/^version[[:space:]]*=/{print $2; exit}'`. Nothing else is authoritative. [VERIFIED: `.github/workflows/release.yml:47`] |
| Version mirror for consumers | Package source (`__init__.py:__version__`) | — | Convention only, not a pipeline gate. Enforced by a test in exactly one package (`market-data-client`). matriz has none and has published twice without it. [VERIFIED: grep across all 6 `__init__.py`] |
| Workspace-member version registration | `uv.lock` (repo root) | — | `ci.yml:33` runs `uv lock --check`; a stale lock reddens check 1 of 15. One line per member. [VERIFIED: `ci.yml:32-33`, `uv.lock` member blocks] |
| Consumer-facing break documentation | Package `README.md` `## Changelog` | Package `__init__.py` module comments | Criterion 1 requires the source-breaking callout **first** in the changelog plus a migration table. Stale "the bump happens in Phase 40" prose also lives in `market_data_client/__init__.py:163-177`. |
| Quality gate | GitHub Actions `ci.yml` (4 job definitions → 15 checks) | Local mirror before push | `main` has **no branch protection** (API returns 404), so GitHub enforces nothing. The count assertion is the only gate. [VERIFIED: `gh api repos/gravity-quant/market-libs/branches/main/protection` → 404] |
| Irreversible publish | GitHub Actions `release.yml` (tag-triggered) | — | Trigger `on: push: tags: ["*-client-v*"]`. One run per tag. Read-only in this phase. |
| Access control on irreversible ops | Human operator (two blocking checkpoints) | — | No branch protection, no required reviewers, all three merge methods allowed. The operator's literal "approved" is the sole control. [VERIFIED: `gh api repos/gravity-quant/market-libs`] |
| Post-publish proof | Throwaway venv + public wheel URL | — | Criterion 3 / D-11. Must exercise the installed artifact, never local source. |

---

## Standard Stack

### Core (no packages are installed by this phase)

| Tool | Version (verified live) | Purpose | Why standard |
|------|------------------------|---------|--------------|
| `git` | 2.39.5 (Apple Git-154) | branch, annotated tags, merge-commit topology assertions | Repo's only VCS |
| `gh` | 2.90.0 | PR create/edit, `gh pr checks` count gate, `gh pr merge --merge`, `gh run watch`, `gh release view` | Used by every prior release in this repo (PRs #8-#14) |
| `uv` | 0.11.3 | `uv lock` (single refresh), `uv sync`, `uv run <gate>`, `uv build` (in CI only) | Workspace/lockfile owner; `astral-sh/setup-uv@v3` in both workflows |
| GitHub Actions | `ci.yml` + `release.yml`, both **read-only** this phase | 15-check gate; wheel+sdist publish | `release.yml` is generic by tag regex — sixth reuse without an edit |
| `pytest` / `ruff` / `mypy` / `pre-commit` / `lint-imports` | per `uv.lock` | local CI mirror | Mirrors the exact CI job bodies |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `gh pr merge --merge` | `--squash` / `--rebase` | **Forbidden by D-08.** Squash orphans the SHAs that dozens of Phase 35-39 SUMMARY files cite by value; rebase rewrites history already reachable from published tags. Both are enabled on the repo (`allow_squash_merge: true`, `allow_rebase_merge: true`), so nothing but the plan text prevents the wrong one. [VERIFIED: `gh api repos/gravity-quant/market-libs`] |
| Annotated tags on the merge SHA | Lightweight tags / tags on branch HEAD | `release.yml`'s version-match gate runs against the **tagged tree**. A tag on branch HEAD produces a Release pointing at a commit outside `main`'s history. D-09 mandates annotated + merge SHA. |
| One `uv lock` after all bumps | One `uv lock` per package | D-10 forbids it; also produces N-1 intermediate desynced lockfiles. |
| Reusing a milestone branch | New branch `milestone/v1.7-nobj-null-objects` | Locked by D-05 — no v1.7 branch or PR exists (verified: `gh pr list` empty; remote heads are only `main`, `milestone/v1.5-mutations`, `release/v0.2.0`). |

**Installation:** none. This phase installs no external package.

---

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.**

The only `install`-shaped operation is the post-publish verification (D-11), which installs
**this repository's own** wheels from their public GitHub Release URLs into a throwaway venv. Those
artifacts are produced by `release.yml` from `uv build --package <pkg>` on the tagged tree in this
same run; provenance is the tag, not a third-party registry.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

**Guard rail for the verification task:** none of the six packages is on PyPI, and
`packages/market-data-client/README.md:38-40` already warns that a bare `uv add market-data-client`
would resolve *something else* if that name ever appears on PyPI. The post-publish install task must
use the **full release-asset URL**, never a bare package name.

---

## Live State Inventory

> Everything in this section was re-measured on 2026-08-30 against the working tree, `origin`, and
> the GitHub API. CONTEXT.md figures that drifted are flagged.

### Bump set — surface delta measured against each package's published tag

| Package | `pyproject` | `__version__` | Last tag | Surface delta vs tag | Class | Disposition |
|---------|-------------|---------------|----------|----------------------|-------|-------------|
| `market-data-client` | `0.5.0` | `0.5.0` | `market-data-client-v0.5.0` | `MarketDataSnapshot.market_data`, `.entries`; `LatestRequest.entries`; +3 exports | **source-breaking** | → **0.6.0** (D-01) |
| `iol-client` | `0.3.0` | `0.3.0` | `iol-client-v0.3.0` | `Cotizacion.puntas`, `Titulo.puntas` | **source-breaking** | → **0.4.0** (D-01) |
| `matriz-client` | `0.2.0` | *(absent)* | `matriz-client-v0.2.0` | 4 model field retypes + envelope-unwrap behavior fix; +4 exports; `strict_decode` kwarg | **source-breaking** | → **0.3.0** (D-01) |
| `higyrus-client` | `0.2.0` | `0.2.0` | `higyrus-client-v0.2.0` | `get_health() -> dict[str, Any]` → `-> Health`; +`Health`, +`HigyrusDecodeError`; `strict_decode` kwarg | **source-breaking** | **checkpoint D-02** |
| `ambito-financiero-client` | `0.2.0` | `0.2.0` | `ambito-financiero-client-v0.2.0` | +`AmbitoFinancieroDecodeError`; `strict_decode` kwarg on `Client`/`AsyncClient`/`configure`; new empty `models.py`/`types.py` | **additive only** | no bump (D-01 confirmed) |
| `wallets-client` | `0.2.0` | `0.2.0` | `wallets-client-v0.2.0` | new `models.py` + `types.py` (56 lines, no exports) | **additive only** | no bump (D-01 confirmed) |

[VERIFIED: `awk` over each `pyproject.toml`; `grep '^__version__'` over each `__init__.py`;
`diff <(git show <tag>:verification/snapshots/<pkg>-surface.txt) verification/snapshots/<pkg>-surface.txt`
for ambito/higyrus/iol/matriz; `git diff --stat <tag>..HEAD -- packages/<pkg>/src` and `__all__` diff
for market-data/wallets, which have no committed surface snapshot]

**Correction to D-01's evidence basis (does not change the conclusion):** D-01 justifies excluding
ambito and wallets by "Phase 38 midió 0 violaciones". That is true for *NOBJ violations*, but both
packages' exported surfaces **did** move since their published tags — additively (a new keyword-only
`strict_decode: bool | None = None` parameter, and a new exported exception class in ambito's case).
Under the project's own precedent — Phase 34 classified higyrus's diff as "aditivo, no
bump-worthy" (`34-01-SUMMARY.md` deviation 1) — the no-bump disposition stands. The plan should
state this as *measured and classified additive*, not as *unchanged*, so a future reader is not
surprised by a non-empty diff.

### Git / GitHub topology

| Fact | Value | Note |
|------|-------|------|
| Current local branch | `main` @ `f66c049a5a94` (`docs(state): record phase 40 context session`) | **The 182 pending commits are on `main` itself, not a milestone branch** |
| `origin/main` | `20ebb78d9fbc` | merge of PR #14 (close of v1.6) |
| Ahead / behind | **182 / 0** | CONTEXT.md D-05 says 180 — recompute at run time, never trust the literal |
| Remote heads | `main`, `milestone/v1.5-mutations`, `release/v0.2.0` | no v1.7 branch (D-05 confirmed) |
| Open PRs | **none** (`gh pr list` → `[]`) | D-05 confirmed |
| Working tree | dirty: `.planning/config.json` (1 line: `_auto_chain_active: true` → `false`) | must be committed or reverted before the clean-tree precondition |
| Repo | `gravity-quant/market-libs`, **public** | remote is `git@github.com:...` (SSH) |
| Branch protection on `main` | **none** — API returns 404 | the human gate is the only access control |
| Merge methods allowed | merge ✓, squash ✓, rebase ✓ | nothing prevents the wrong one but the plan text (D-08) |
| `delete_branch_on_merge` | `false` | the release branch survives the merge |
| `gh auth` | `sebadlf`, scopes `gist, read:org, repo, workflow` | no auth blocker |
| Existing `*-client-v*` tags | 15 locally, 28 refs on origin | includes `wallets-client-v0.2.0`; also milestone tags `v1.1`…`v1.6` (**not** package tags — never `git push --tags`) |

### `uv.lock` member blocks (the lines a correct refresh changes)

| Member | `name` line | `version` line | Current |
|--------|-------------|----------------|---------|
| `ambito-financiero-client` | 21 | 22 | `0.2.0` |
| `higyrus-client` | 283 | 284 | `0.2.0` |
| `iol-client` | 383 | 384 | `0.3.0` |
| `market-data-client` | 487 | 488 | `0.5.0` |
| `matriz-client` | 548 | 549 | `0.2.0` |
| `wallets-client` | 906 | 907 | `0.2.0` |

**Expected churn:** `git show --numstat --format= HEAD -- uv.lock` must report **`3 3`** (three
members, one version line each) — or **`4 4`** if D-02 folds higyrus. Phase 34 measured `2 2` for
two members, confirming one line per member. Anything larger means `uv` re-resolved third-party
dependencies → STOP.

### CI structure — 15 checks, exact names

`.github/workflows/ci.yml` defines 4 jobs; `test` fans out 6 × 2 = 12.

| Check name (as it appears in `gh pr checks`) | Count |
|---|---|
| `Lint y formato (ruff)` | 1 |
| `pre-commit hooks` | 1 |
| `Type check (mypy)` | 1 |
| `Tests · <pkg> · py3.12` / `· py3.13` for `higyrus-client`, `wallets-client`, `matriz-client`, `iol-client`, `ambito-financiero-client`, `market-data-client` | 12 |
| **Total** | **15** |

Triggers: `push` to `main` and `pull_request` to `main`, both with
`paths-ignore: ["**.md", ".gitignore"]`. `concurrency.cancel-in-progress: true`.
[VERIFIED: `ci.yml:3-20, 22-146`]

The `lint` job body has grown since Phase 34 — it now runs **eight** repo-specific gates beyond
ruff. The local mirror must reproduce all of them:

```
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
grep -rnE 'logging\.basicConfig\s*\(|logging\.root\.\w' packages/*/src/   # must find nothing
uv run python tools/check_decode_intactness.py
uv run python tools/check_uniform_structure.py
uv run python tools/check_surface_types.py
uv run pytest -q verification/<12 explicit files>      # ci.yml:80-92 — an ALLOWLIST, not the dir
```

The 12-file allowlist at `ci.yml:80-92` is: `test_main_market_data_deep_chain.py`,
`test_safemodel_diff_null_object_links.py`, `test_main_matriz_risk_envelope_keys.py`,
`test_safemodel_diff_mapping_recursion.py`, `test_main_verify_classification.py`,
`test_main_matriz_skip_line_shape.py`, `test_main_higyrus_skip_line_shape.py`,
`test_run_evidence.py`, `test_main_iol_deep_chain.py`, `test_main_higyrus_deep_chain.py`,
`test_main_matriz_deep_chain.py`, `test_cycle_closure_phase33.py`.

### Baseline: the tree is green right now

Measured in this session on `f66c049`:

| Gate | Result |
|------|--------|
| `uv lock --check` | OK |
| `uv run ruff check .` | OK |
| `uv run ruff format --check .` | 278 files already formatted |
| `uv run lint-imports` | Contracts: 5 kept, 0 broken |
| `tools/check_decode_intactness.py` | OK (5 in-scope packages; wallets exempt) |
| `tools/check_uniform_structure.py` | OK (6/6 carry `models.py` + `types.py`) |
| `tools/check_surface_types.py` | 186 `__all__` names, 336 defs, 442 fields, 24 exempted, **0 violations** |
| logging gate grep | no match |
| `uv run mypy` | Success: no issues found in 75 source files |
| `pytest -q verification/<12>` | 128 passed |
| `pytest packages/market-data-client` | 711 passed |
| `pytest packages/iol-client` | 311 passed |
| `pytest packages/matriz-client` | 609 passed |
| `pytest packages/higyrus-client` | 303 passed |

Not run in this session (cheap, but slow and environment-sensitive): `uv run pre-commit run --all-files`,
`uv run mypy packages/<pkg>/tests` × 6, and the ambito/wallets suites. The plan must include them.

### Workflow-file immutability — the assertion form matters

| Ref | `release.yml` sha256 (first 16) | `ci.yml` sha256 (first 16) |
|-----|---------------------------------|-----------------------------|
| `HEAD` | `7109ff0b6819c596` | `40bc11b8e5404376` |
| `origin/main` | `7109ff0b6819c596` | `3641ac1d410ab9ce` |
| `iol-client-v0.3.0` | `7109ff0b6819c596` | `3641ac1d410ab9ce` |
| `market-data-client-v0.5.0` | `7109ff0b6819c596` | — |
| `matriz-client-v0.2.0` | `7109ff0b6819c596` | `78ff78484833f341` |
| `higyrus-client-v0.2.0` | `7109ff0b6819c596` | — |

`release.yml` is **byte-identical everywhere**. `ci.yml` legitimately differs across refs (Phases
36/37/39 added lint steps). This is why the assertion form used in `34-01-PLAN.md` (f) and
`34-03-PLAN.md` (f) — `git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` must be
empty — **is wrong and failed three times during Phase 34**. See P2.

---

## Migration Table Content (locked by D-03; wording is Claude's discretion)

All before/after types below were read directly from `git show <tag>:...models.py` vs the working
tree, and every "after" behavior was executed live (see § Code Examples).

### `market-data-client` 0.5.0 → 0.6.0 — already authored, needs de-provisionalizing

Section exists at `packages/market-data-client/README.md:7-34` as `## Unreleased — BREAKING`.

| Antes (0.5.0 publicado) | Ahora (0.6.0) |
|---|---|
| `snapshot.market_data["LA"]["price"]` | `snapshot.market_data.last.price` |
| `snapshot.market_data["BI"]` | `snapshot.market_data.bids` (`list[BookLevel]`) |
| `if snapshot.market_data is None:` | `if not snapshot.market_data:` |
| `snapshot.entries is None` | `snapshot.entries == []` (nunca `None`) |
| `LatestRequest(entries=None)` | `LatestRequest(entries=[])` — la clave `entries` sigue sin viajar cuando la lista está vacía |

Declared-type facts: `MarketDataSnapshot.market_data`: `dict[str, Any] | None` → `MarketDataEntries`;
`MarketDataSnapshot.entries`: `list[str] | None` → `list[str]`; `LatestRequest.entries`:
`list[str] | None = None` → `list[str] = field(default_factory=list)`. `staleness_seconds` is
**unchanged** (`float | None` at both refs). Additive: `BookLevel`, `EntryValue`,
`MarketDataEntries` joined `__all__`; six alias `@property` views (`bids`/`offers`/`last`/
`settlement`/`close`/`open_interest`) over `BI`/`OF`/`LA`/`SE`/`CL`/`OI`.

### `iol-client` 0.3.0 → 0.4.0 — already authored, needs de-provisionalizing

Section exists at `packages/iol-client/README.md:5-42` as `## Unreleased — BREAKING`.

| Antes (0.3.0 publicado) | Ahora (0.4.0) |
|---|---|
| `quote.puntas is None` / `quote.puntas or []` | `quote.puntas == []` — el fallback `or []` ya no hace falta |
| `titulo.puntas is None` | `not titulo.puntas` (o `titulo.puntas == Punta.empty()`) |

Declared-type facts: `Cotizacion.puntas`: `list[Punta] | None` → `list[Punta]`; `Titulo.puntas`:
`Punta | None` → `Punta`. The existing prose correctly flags the asymmetry the typechecker cannot
catch (`Titulo.puntas` stops being the language's null value, so `is None` branches go silently
dead) — keep it.

### `matriz-client` 0.2.0 → 0.3.0 — **to author from scratch** (D-03)

`packages/matriz-client/README.md` has no `## Changelog` section at all (it ends at
`## Desarrollo`, line 131). Source: `37-01-SUMMARY.md`…`37-05-SUMMARY.md`.

| Antes (0.2.0 publicado) | Ahora (0.3.0) |
|---|---|
| `report.portfolio` era `dict[str, Any]` (siempre `{}` en la práctica) | `report.portfolio` es `float \| None` — chequear `is None`, no `== {}` |
| `detail.tickPriceRanges["0"]["tick"]` | `detail.tickPriceRanges["0"].tick` (`dict[str, TickPriceRange]`) |
| `pos.report["<acct>"]["<sym>"]["instrumentCurrentSize"]` | `pos.report["<acct>"]["<sym>"].instrumentCurrentSize` (`dict[str, dict[str, InstrumentPositionReport]]` — **dos** niveles) |
| `acct.detailedAccountReports["<k>"]["settlementDate"]` | `acct.detailedAccountReports["<k>"].settlementDate` (`dict[str, DetailedAccountReport]` — **un** nivel) |

Verified declared types at `matriz-client-v0.2.0` → `HEAD`:
`InstrumentDetail.tickPriceRanges` `dict[str, Any]` → `dict[str, TickPriceRange]`;
`DetailedPosition.report` `dict[str, Any]` → `dict[str, dict[str, InstrumentPositionReport]]`;
`AccountReport.detailedAccountReports` `dict[str, Any]` → `dict[str, DetailedAccountReport]`;
`AccountReport.portfolio` `dict[str, Any]` → `float | None`.

**Behavior fix, not just typing** (D-03 requires this be documented as such): `get_detailed_positions`
and `get_account_report` previously decoded from the wrong nesting level, returning models with
every field at its default. `37-01` fixed this by unwrapping the vendor envelope keys
`detailedPosition` / `accountData` via the existing `unwrap()` helper. Operator-ratified disposition
id `strict-unwrap`: a **flat (unenveloped) Risk body now RAISES** rather than silently decoding.
Consumers that were tolerating all-default Risk models will now see real data — or a
`PrimaryAPIError` where they previously saw an empty model.

**Additive, documented separately, NOT in the migration table** (D-03): the six alias `@property`
views on `MarketDataSnapshot` — `bids`/`offers` → `list[MarketDataLevel]`,
`last`/`settlement`/`close`/`open_interest` → `MarketDataEntryValue`, over wire keys
`BI`/`OF`/`LA`/`SE`/`CL`/`OI`. Note `OP` and matriz's seven extra scalars were **deliberately
excluded** (37-05 named exclusion decision). Also additive: `TickPriceRange`,
`InstrumentPositionReport`, `DetailedAccountReport`, `MatrizDecodeError` on `__all__`, and the
`strict_decode: bool | None = None` kwarg on `Client`, `AsyncClient` and `configure`.

### `higyrus-client` 0.2.0 → 0.3.0 — **conditional on D-02**

Section already written at `packages/higyrus-client/README.md:131-162`, but titled
`### v0.3.0 — sin publicar todavía` and its body says "El bump de `pyproject.toml` y el tag los hace
la Phase 34" — an assertion Phase 34 itself invalidated.

| Antes (0.2.0 publicado) | Ahora (0.3.0) |
|---|---|
| `health["status"]` | `health.status` |

Plus: truthiness flip (empty dict is falsy; a dataclass instance is always truthy), new exported
`Health` model, `health.to_dict()` escape hatch, `204`/empty body collapses to zero-valued `Health`
and raises `HigyrusDecodeError` under `strict_decode`. Also additive since the tag:
`HigyrusDecodeError` on `__all__` and the `strict_decode` kwarg.
Verified in production code: `packages/higyrus-client/src/higyrus_client/client.py` — the surface
snapshot at `HEAD` reads `get_health : function : () -> 'Health'`.

---

## Edit-Site Inventory

Every file the phase touches, with the specific line ranges that are stale today.

| Package | Site | What changes |
|---------|------|--------------|
| market-data | `pyproject.toml:3` | `0.5.0` → `0.6.0` |
| market-data | `src/market_data_client/__init__.py:178` | `__version__ = "0.5.0"` → `"0.6.0"` |
| market-data | `src/market_data_client/__init__.py:163-177` | **"NO BUMPEAR ACÁ (Phase 36 code review, WR-04)"** comment block — 15 lines instructing every future agent *not* to bump and naming Phase 40 as the owner. Becomes false on bump. **Delete or rewrite.** Easy to miss: it is a comment, not prose, and no grep for "Unreleased" or "Fase 40" in Markdown finds it. |
| market-data | `README.md:7-34` | `## Unreleased — BREAKING` → the `### v0.6.0` changelog entry; delete the "`main` NO es el `0.5.0` publicado" framing and the "lo hace la Fase 40" sentence (`:12`) |
| market-data | `README.md:29-34` | the `market_id`/`active` divergence note ending "espera checkpoint del operador" — **must be resolved per D-12** (either a new migration row, or a re-pointed destination) |
| market-data | `README.md:44` and `:53` | install pins: `@market-data-client-v0.5.0` → `-v0.6.0`, and the wheel URL + filename `market_data_client-0.5.0-py3-none-any.whl` → `-0.6.0-`. **This is the only package with version-pinned install commands.** Leaving them stale reproduces Phase 34's CR-01 defect verbatim. |
| market-data | `README.md:152` (`## Changelog`) | new `### v0.6.0` entry inserted **first**, above `### v0.5.0` (`:154`) |
| iol | `pyproject.toml:3` | `0.3.0` → `0.4.0` |
| iol | `src/iol_client/__init__.py:87` | `__version__ = "0.3.0"` → `"0.4.0"` |
| iol | `README.md:5-42` | `## Unreleased — BREAKING` → `### v0.4.0` changelog entry; drop "lo hace la Fase 40" (`:10`) |
| iol | `README.md:149` (`## Changelog`) | new `### v0.4.0` entry inserted first, above `### v0.3.0` (`:151`) |
| iol | install commands | **none pinned** — `README.md:47` is a bare `uv add iol-client`. No edit needed. |
| matriz | `pyproject.toml:3` | `0.2.0` → `0.3.0` |
| matriz | `src/matriz_client/__init__.py` | **no `__version__` exists** (D-04). Adding one is discretionary; if added, add it *and* nothing else — do not add a `test_version_metadata.py`. |
| matriz | `README.md` (after `:131` `## Desarrollo`) | **create `## Changelog` from scratch** with `### v0.3.0` as its only entry |
| matriz | install commands | none pinned. No edit needed. |
| higyrus *(if D-02 folds)* | `pyproject.toml:3`, `__init__.py:109`, `README.md:131-162` | `0.2.0` → `0.3.0`; retitle `### v0.3.0 — sin publicar todavía` → `### v0.3.0`; delete the "los hace la Phase 34" paragraph (`:133-137`) |
| higyrus *(if D-02 declines)* | `README.md:133-137` | correct the paragraph anyway — it must stop naming Phase 34 as the executor, and must name a concrete destination or say "pendiente, sin fase asignada" |
| root | `uv.lock` | one `version = ` line per bumped member |

No test, tool, or CI gate asserts any README section title — `grep -rn 'Unreleased' --include='*.py' .`
finds exactly one hit, the comment block above. So the changelog restructuring is free of hidden
test coupling. [VERIFIED]

---

## Architecture Patterns

### Release flow

```
      [40-01  autonomous: true*]                    * see OQ-1: recommend one
                                                      checkpoint:decision at the TOP
  commit dirty .planning/config.json
            │
            ├─ (OQ-1) resolve D-02 (higyrus fold?) + D-12 (widen market_id/active?)
            │            └─ if either approves → the bump set / code set changes HERE,
            │                                    before anything downstream is computed
            ▼
  author matriz changelog (from scratch)
  de-provisionalize iol + market-data changelog blocks
  strip "NO BUMPEAR ACÁ" comment + "Fase 40" prose
  bump N × pyproject.toml (+ N-1 × __version__; matriz has none)
  bump market-data install pins
            ▼
  uv lock          ←── EXACTLY ONCE (D-10); churn must be N insertions / N deletions
  uv sync          ←── REQUIRED so market-data's dist-metadata test sees the new version (P3)
            ▼
  local CI mirror (all 4 job bodies) → credential scan over origin/main...HEAD
            ▼
  git checkout -b milestone/v1.7-nobj-null-objects   (HEAD is on `main` today — P6)
  git push origin milestone/v1.7-nobj-null-objects   (plain FF; --force forbidden)

      [40-02  autonomous: false]
  gh pr create --base main --head milestone/v1.7-nobj-null-objects
  gh pr checks <n> --watch  →  assert BY COUNT: 15 rows / 15 pass / 2 rows per bumped pkg
            ▼
  ╔══ GATE (a) — BLOCKING HUMAN — D-07(a) ═══════════════════════╗
  ║  never auto-approvable; auto_advance + yolo do NOT satisfy it ║
  ╚═══════════════════════════════════════════════════════════════╝
            ▼
  gh pr merge <n> --merge      (never --squash, never --rebase — D-08)
  assert: rev-list --parents -n1 origin/main  →  3 fields (commit + 2 parents)
  assert: merged tree carries every bumped version under release.yml's own awk

      [40-03  autonomous: false]
  ╔══ GATE (b) — BLOCKING HUMAN — D-07(b) ═══════════════════════╗
  ║  ONE approval covers ALL N tags; never split per package      ║
  ╚═══════════════════════════════════════════════════════════════╝
            ▼
  MERGE_SHA=$(git rev-parse origin/main)   ←── RE-RESOLVED live, never a SUMMARY literal (D-09)
  git tag -a <pkg>-client-v<X.Y.Z> "$MERGE_SHA" -m "…"   × N
  git push origin <tag>   × N, BY NAME (never --tags: v1.1…v1.6 are milestone tags)
            ▼
  N independent release.yml runs → gh run watch each → N public Releases (wheel + sdist)
            ▼
  POST-PUBLISH VERIFICATION (criterion 3 / D-11) — no Phase-34 plan-task precedent
  uv venv --python 3.12 (throwaway) → pip install <full public wheel URL> × N
  assert installed __version__ (where it exists) + a deep chain per package
```

### Pattern 1: Assert CI green by explicit count, never by absence of failure

**What:** count rows and count `pass` rows; require both to equal 15, plus a per-package row count.
**When:** every time before the merge gate, and again from scratch after any commit lands mid-run.
**Why:** `pending`, `skipping` and `cancelled` all read as green under an absence-of-`fail` check.
`cancel-in-progress: true` (`ci.yml:20`) makes `cancelled` genuinely reachable, and
`paths-ignore: ["**.md", ".gitignore"]` makes a **zero-check** run reachable for a docs-only diff —
and "no checks" is not green. (For this specific PR the diff carries `uv.lock`, `pyproject.toml` and
182 commits of `.py`, so zero-checks is not a live risk — but assert `TOTAL == 15` anyway.)

```bash
PR=<n>
TOTAL=$(gh pr checks "$PR" | wc -l | tr -d ' ')
PASSED=$(gh pr checks "$PR" | awk -F'\t' '$2=="pass"' | wc -l | tr -d ' ')
MD=$(gh pr checks "$PR" | grep -c 'Tests · market-data-client · py3\.1[23]')
IOL=$(gh pr checks "$PR" | grep -c 'Tests · iol-client · py3\.1[23]')
MTZ=$(gh pr checks "$PR" | grep -c 'Tests · matriz-client · py3\.1[23]')
test "$TOTAL" = 15 && test "$PASSED" = 15 && test "$MD" = 2 && test "$IOL" = 2 && test "$MTZ" = 2
```

### Pattern 2: Tag the re-resolved merge SHA, annotated, pushed by name

```bash
git fetch origin main --tags
MERGE_SHA=$(git rev-parse origin/main)                      # re-resolved, never a literal
test "$(git rev-list --parents -n1 "$MERGE_SHA" | wc -w)" -eq 3
git show "$MERGE_SHA":packages/matriz-client/pyproject.toml \
  | awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'      # must read 0.3.0 — release.yml's own expression
git tag -a matriz-client-v0.3.0 "$MERGE_SHA" -m "matriz-client v0.3.0 — …"
git push origin matriz-client-v0.3.0                         # BY NAME. never --tags, never --force
test "$(git cat-file -t matriz-client-v0.3.0)" = tag         # annotated, not lightweight
test "$(git rev-list -n1 matriz-client-v0.3.0)" = "$MERGE_SHA"
```

### Pattern 3: The two blocking gates as two separate `autonomous: false` PLAN.md files

Copy the literal shape from `34-02-PLAN.md` Task 2 and `34-03-PLAN.md` Task 1:
`<task type="checkpoint:human-verify" gate="blocking">` with `<what-built>`, `<how-to-verify>`, and
`<resume-signal>` sub-elements; the plan frontmatter carries `autonomous: false` and a `user_setup`
entry for GitHub. The `<action>` text must state, in these words, that `auto_advance` and yolo mode
do not satisfy the gate, that silence does not satisfy it, and that the agent may not self-issue it.
Phase 34 executed both gates correctly under the same `auto_advance: true` + `mode: yolo` config
(STATE.md:384, :386) — the pattern is proven, not aspirational.

### Anti-Patterns to Avoid

- **Bare `uv run pytest`.** The root `testpaths` collects `verification/`, which carries known
  pre-existing failures no CI job ever runs. Use per-package paths and the 12-file allowlist.
- **`git push --tags`.** Milestone tags `v1.1`…`v1.6` and 15 package tags exist locally; a wholesale
  push publishes whatever is stale.
- **Patching `ci.yml` to make a check pass.** Phase 34 hit a red `Type check (mypy)` and fixed it by
  narrowing in the test (`e5eeb8a`), never by touching the workflow (STATE.md:385). Same rule here.
- **Deleting or re-pointing a tag to "try again".** Once a Release exists, the tag cannot be cleanly
  re-pointed; the remedy is publishing a new version.
- **Trusting a SUMMARY's literal SHA or ahead-count.** CONTEXT.md's "180 commits" is already 182.
  Recompute at run time.
- **Pushing the phase commits directly to `main`.** The merge must go through the PR so attribution,
  PR closure and the two-parent merge shape match every prior release.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| Reading a package's version | a TOML parser, a regex, `importlib.metadata` | `awk -F'"' '/^version[[:space:]]*=/{print $2; exit}' packages/<pkg>/pyproject.toml` | This is **literally the expression `release.yml:47` runs**. Any other reader can disagree with the gate that decides whether the release publishes. |
| Refreshing the lockfile | hand-editing the `version = ` lines | `uv lock` (once) | A hand edit passes `grep` but can fail `uv lock --check`, reddening check 1 of 15. |
| Building the wheel/sdist | `uv build` locally + `gh release create` by hand | pushing the tag; `release.yml` does it | Read-only workflow, sixth reuse. The version-match gate is the point. |
| Deciding "CI is green" | `! gh pr checks | grep fail` | the explicit count in Pattern 1 | `pending` / `cancelled` / zero-rows all pass the negative check. |
| Proving the merge was a real merge | reading the subject line | `test "$(git rev-list --parents -n1 origin/main | wc -w)" -eq 3` | A squash also produces a `Merge pull request …`-looking history in some UIs; parent count cannot lie. |
| Proving the workflows were untouched | `git diff <prior-release-tag>..HEAD -- .github/workflows` | sha256 of `release.yml` across refs + `git diff <phase-base>..HEAD -- .github/workflows` | The tag-baseline form is **wrong** and failed three times in Phase 34 (P2). |
| Proving the release is consumable | reading the Release page | install the public wheel into a throwaway venv and run a deep chain | Criterion 3 / D-11 requires exercising the *installed* artifact. |

**Key insight:** every assertion in this phase should be written so it agrees, expression for
expression, with whatever GitHub Actions will run against the same artifact. Where the plan invents
its own reader, the plan and the pipeline can disagree — and the pipeline wins after the tag is
already public.

---

## Common Pitfalls

### P1 — The two scope questions sit at the pre-merge gate, but an "approve" on either forces a full re-loop

**What goes wrong:** D-07 puts the D-02 (higyrus fold-in) and D-12 (`market_id`/`active` widening)
questions inside checkpoint (a), which by construction fires *after* the bumps, *after* the single
`uv lock`, *after* the branch push, and *after* 15/15 CI has been asserted. An "approve" on either
invalidates all of it.

**Blast radius, measured:**

- **D-02 approve** ⇒ a fourth `pyproject.toml` bump + `__version__` bump + changelog rewrite ⇒ a
  **second `uv lock` run**. That is a direct contradiction of D-10 ("`uv.lock` se refresca
  **exactamente una vez**") and of ROADMAP criterion 2, which is asserted by the phase's own
  verification. Also: new commits ⇒ new CI run ⇒ the 15/15 assertion must be redone from scratch
  ⇒ checkpoint (a) must be presented a second time.
- **D-12 approve** ⇒ widening `MarketDataSnapshot.market_id: str` → `str | None` and
  `.active: bool` → `bool | None` is a **code change**, and it turns at least six existing
  assertions RED in `packages/market-data-client/tests/test_snapshot_no_data_row.py`:
  `assert row.market_id == ""` (`:155`, `:179`) and
  `assert exc.value.field_path == ".market_id"` (`:261`, `:282`), each with an `_async` twin, plus
  the module docstring at `:61-63` which states in prose that these fields are "still" over-declared.
  Those tests exist *specifically* to pin the un-widened behavior (36-REVIEW CR-02). New commits ⇒
  new CI run ⇒ re-assert ⇒ re-present the gate.

**How to avoid:** hoist both questions into a `checkpoint:decision` gate at the **top of plan 40-01**,
before the first version bump. Then re-present their already-resolved answers inside the 40-02
pre-merge briefing as read-back facts (satisfying CONTEXT's requirement that they be visible and
explicit at checkpoint (a)) rather than as open questions. This keeps the count of *blocking gates on
irreversible operations* at exactly two (D-07's actual concern), keeps `uv lock` at one run (D-10),
and lets CI run once against final content. **This deviates from the letter of D-07/D-12 and must be
confirmed with the operator before planning — see OQ-1.**

**Warning signs:** a plan whose 40-02 checkpoint text asks an open question *and* whose 40-02 Task 3
merges unconditionally; a `uv lock` task that appears in more than one plan.

### P2 — The "workflows untouched" assertion form inherited from Phase 34 is wrong

**What goes wrong:** `34-01-PLAN.md` (c) and `34-03-PLAN.md` (f) assert
`git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` is empty. `.github/workflows/ci.yml`
legitimately changes between releases: sha256 is `78ff7848…` at `matriz-client-v0.2.0`,
`3641ac1d…` at `origin/main`/`iol-client-v0.3.0`, and `40bc11b8…` at `HEAD` (Phases 36/37/39 added
lint steps). The assertion fails on work this phase did not do.

**Evidence it already bit:** STATE.md:389 — *"La aserción (f) del plan … usa baseline obsoleto y falla
sobre ci.yml por commits de Phases 24/29/31/32 … **tercera aparición del mismo baseline obsoleto en la
fase**, conviene corregir la forma de la aserción en el patrón."*

**How to avoid — the corrected form:**

```bash
# 1. release.yml is byte-identical everywhere (this is the real D-11 invariant)
for R in HEAD origin/main iol-client-v0.3.0 market-data-client-v0.5.0 matriz-client-v0.2.0; do
  git show "$R:.github/workflows/release.yml" | shasum -a 256 | cut -d' ' -f1
done | sort -u | wc -l          # must be 1;  the value today is 7109ff0b6819c596…
# 2. THIS PHASE touched no workflow file
test "$(git diff --name-only f66c049a5a946eeda2bda27fce6cf0b6774ce076..HEAD -- .github/workflows | wc -l)" -eq 0
```

(`f66c049…` is the phase-40 base commit; recompute it rather than hard-coding if commits land first.)

### P3 — Bumping `market-data-client` breaks its own version test until `uv sync` re-installs

**What goes wrong:** `packages/market-data-client/tests/test_version_metadata.py` has
`test_dunder_version_matches_installed_distribution_metadata`, which compares
`market_data_client.__version__` against `importlib.metadata.version("market-data-client")`. After
editing `__init__.py` to `0.6.0`, the editable install's `.dist-info` still reports `0.5.0` until the
environment is re-synced. The local mirror goes red; CI stays green (it does a fresh
`uv sync --frozen`). An agent seeing a red local test after a "docs-only" bump can easily
misdiagnose it as a real break.

**How to avoid:** run `uv sync --all-packages --all-extras --dev` immediately after `uv lock` and
before the local mirror. **Only `market-data-client` has this test** — no other package binds
`__version__` to distribution metadata, and matriz has no `__version__` at all.

### P4 — Never `uv run pytest` bare

Root `testpaths` includes `verification/`, which carries pre-existing failures that no CI job runs
(backlog `HARN-VERIF-01`). CI's `lint` job runs an explicit 12-file allowlist (`ci.yml:80-92`), and
the `test` job runs `pytest packages/<pkg>` per matrix cell. A bare run blocks the release on
out-of-scope failures indefinitely.

### P5 — Zero checks and cancelled checks both read as "not failed"

See Pattern 1. Additionally: do **not** push a commit while checks are in flight —
`cancel-in-progress: true` cancels the run, and `cancelled` is not `fail`.

### P6 — The branch topology is different from Phase 34's, and getting it wrong pushes 182 commits to `main`

**What goes wrong:** Phase 34's 47 pending commits were on `milestone/v1.5-mutations` with local
`main` as a separate ref. Here, **HEAD is on local `main`** (`f66c049`) and the 182 commits are on
that branch. A copy-paste of 34-01 Task 3's `git push origin <branch>` with the branch name swapped,
without first moving HEAD, is ambiguous; a `git push origin main` would publish 182 commits directly
to the public default branch with no PR, no CI gate and no human approval.

**How to avoid:**

```bash
git checkout -b milestone/v1.7-nobj-null-objects   # moves HEAD; local `main` stays at the same SHA
# ... all phase commits land here ...
git push origin milestone/v1.7-nobj-null-objects   # plain FF; --force and --force-with-lease FORBIDDEN
```

Precondition assertion for 40-02 becomes
`test "$(git rev-parse HEAD)" = "$(git rev-parse origin/milestone/v1.7-nobj-null-objects)"`.
Post-merge, local `main` sits one commit behind `origin/main` (the merge commit) and fast-forwards
cleanly — no divergence to resolve. `delete_branch_on_merge` is `false`, so the release branch
survives for any follow-up commit.

### P7 — Dirty working tree blocks the clean-tree precondition

`.planning/config.json` is modified right now (`_auto_chain_active: true → false`, one line). Commit
or revert it in the first task; do not let it ride along silently into a release commit.

### P8 — Stale "the bump happens in Phase 40" prose in three places, one of which greps invisible

`packages/market-data-client/README.md:12` and `packages/iol-client/README.md:10` both say the bump
is done by "la Fase 40". `packages/market_data_client/src/market_data_client/__init__.py:163-177` is
a 15-line **comment block** headed `# NO BUMPEAR ACÁ` that names Phase 40 as the owner and points at
the README's "Unreleased — BREAKING" section. All three become false at bump time. The comment block
is the one that gets missed — a Markdown-scoped grep never sees it. Phase 34 had the identical class
of defect (a `### v0.5.0 — sin publicar todavía` heading) and caught it only via an explicit
de-provisionalization task.

### P9 — Three (or four) tags on one merge commit has no executed precedent in this repo

Phase 34 executed two; every release before that executed one. Mechanically it is fine —
`release.yml`'s `concurrency.group` is `release-${{ github.ref }}`, i.e. per-tag, so the N runs do
not serialize or cancel each other. Completion order is unspecified and irrelevant. **Watch each run
individually to `success` and verify each Release's assets by exact filename**; do not infer from one
run that the others succeeded. Asset naming (confirmed against four prior Releases):
`<underscored_name>-<version>-py3-none-any.whl` and `<underscored_name>-<version>.tar.gz`.

### P10 — Post-publish verification must install from the public URL, in a fresh interpreter

The verification is only meaningful against the published artifact. Installing the workspace, or
importing from the repo checkout, proves nothing. Use `uv venv --python 3.12` in a scratch directory
and `pip install "<full release download URL>"`. Note `python3` on this machine is **3.9.6** — the
packages require `>=3.12`, so the venv's `--python 3.12` flag is load-bearing, not cosmetic.

### P11 — `higyrus-client` and `ambito-financiero-client` were re-verified as *changed but additive*, not as *unchanged*

If someone re-runs a surface diff during verification and finds a non-empty result for ambito
(`AmbitoFinancieroDecodeError` + `strict_decode`) or wallets (new `models.py`/`types.py`), that is
**expected**. Document the classification in the plan so it does not read as a discovered defect
mid-release.

---

## Code Examples

### Post-publish deep chains — all four verified live on `HEAD` in this session

These are the assertions the D-11 verification task should run **inside the throwaway venv against
the installed wheels**. Every printed value below was produced by executing the code, not inferred.

```python
# market-data-client 0.6.0 — the Null Object chain (Phase 36)
from market_data_client.models import MarketDataSnapshot
s = MarketDataSnapshot.from_api(None)
assert s.market_data.last.price is None      # deep chain, no None-guard needed
assert s.market_data.bids == []
assert not s.market_data                     # falsy Null Object — the `is None` replacement
assert s.entries == []                       # never None

# iol-client 0.4.0 — puntas lost `| None` (Phase 38)
from iol_client.models import Titulo, Cotizacion
assert Titulo.from_api(None).puntas.precioCompra == 0.0   # was: `titulo.puntas is None`
assert Cotizacion.from_api(None).puntas == []             # was: `quote.puntas or []`

# matriz-client 0.3.0 — the four retypes (Phase 37)
from matriz_client.models import (
    AccountReport, InstrumentDetail, DetailedPosition, MarketDataSnapshot as MtzSnapshot,
)
a = AccountReport.from_api(None)
assert a.portfolio is None                                # was dict[str, Any] -> now float | None
assert a.detailedAccountReports == {}                     # dict[str, DetailedAccountReport]
assert InstrumentDetail.from_api(None).tickPriceRanges == {}   # dict[str, TickPriceRange]
assert DetailedPosition.from_api(None).report == {}       # dict[str, dict[str, InstrumentPositionReport]]
m = MtzSnapshot.from_api(None)
assert m.bids == [] and m.last.price is None              # additive alias views

# higyrus-client 0.3.0 (only if D-02 folds it in)
from higyrus_client.models import Health
assert Health.from_api(None).status == ""                 # was: health["status"]
```

Also assert `<pkg>.__version__` for the three packages that carry it (**not** matriz — D-04).

### The throwaway-venv shape (Phase 34 UAT precedent, promoted to a plan task here)

```bash
BASE=https://github.com/gravity-quant/market-libs/releases/download
WORK=$(mktemp -d) && cd "$WORK"
uv venv --python 3.12                       # system python3 is 3.9.6 — this flag is load-bearing
uv pip install \
  "$BASE/market-data-client-v0.6.0/market_data_client-0.6.0-py3-none-any.whl" \
  "$BASE/iol-client-v0.4.0/iol_client-0.4.0-py3-none-any.whl" \
  "$BASE/matriz-client-v0.3.0/matriz_client-0.3.0-py3-none-any.whl"
uv run python - <<'PY'
# ... the deep-chain assertions above ...
PY
```

### Release asset verification (per tag)

```bash
gh release view matriz-client-v0.3.0 --json assets --jq '.assets[].name' \
  | grep -qx 'matriz_client-0.3.0-py3-none-any.whl'
gh release view matriz-client-v0.3.0 --json assets --jq '.assets[].name' \
  | grep -qx 'matriz_client-0.3.0.tar.gz'
```

### `uv.lock` churn assertion (N = 3, or 4 if higyrus folds)

```bash
uv lock                       # exactly once, after ALL pyproject edits
uv lock --check
grep -A1 '^name = "matriz-client"$'      uv.lock | grep -qx 'version = "0.3.0"'
grep -A1 '^name = "iol-client"$'         uv.lock | grep -qx 'version = "0.4.0"'
grep -A1 '^name = "market-data-client"$' uv.lock | grep -qx 'version = "0.6.0"'
test "$(git show --numstat --format= HEAD -- uv.lock | awk '{print $1, $2}')" = "3 3"
uv sync --all-packages --all-extras --dev     # P3: refresh dist-metadata before the mirror
```

---

## State of the Art

| Old approach (Phase 28/34) | Current approach (Phase 40) | Why changed |
|---|---|---|
| Update an existing PR (`gh pr edit 12`) | Create a new PR (`gh pr create`) | No v1.7 branch or PR exists (D-05, verified) |
| Two tags on one merge commit | Three (or four) | v1.7 moved three surfaces |
| Workflows-untouched via `git diff <prior-release-tag>..HEAD` | `release.yml` sha256 identity + `git diff <phase-base>..HEAD` | The tag-baseline form is stale-by-construction and failed 3× in Phase 34 (STATE.md:389) |
| Post-publish install proved in UAT | Post-publish install proved by a plan task | Criterion 3 / D-11 makes it in-phase |
| Changelog entry created by the phase that shipped the code | Two of three entries pre-authored as `## Unreleased — BREAKING`; matriz's authored here | Phases 36/38 adopted the "declare the break where it lands" pattern; matriz (37) did not |
| Release memory files refreshed post-publish (34-03 Task 3) | Discretionary | Only `market-data-client-releases.md` exists; refreshing it keeps install instructions from misdirecting future agents. Not a ROADMAP criterion. Check `.claude/projects/-Users-admin-development-market-libs/memory/` at plan time — a stale file there is the exact defect T-34-12 tracked. |

**Deprecated / no longer valid:**
- `packages/higyrus-client/README.md:133` — "El bump … los hace la Phase 34". False since 2026-08-27.
- `packages/market-data-client/README.md:12`, `packages/iol-client/README.md:10` — "lo hace la Fase 40". True until this phase merges; false the instant it does.
- `market_data_client/__init__.py:163-177` — "NO BUMPEAR ACÁ". Must be removed by this phase.
- CONTEXT.md D-05's "180 commits" — now 182.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | The correct bump for each package is **minor** on a 0.x line (0.5.0→0.6.0, 0.3.0→0.4.0, 0.2.0→0.3.0), matching the project's established "breaking = minor on 0.x" convention | Bump set | Low — D-01 locks the exact target versions verbatim, so this is a rationale, not a decision. |
| A2 | `pip install`/`uv pip install` from a GitHub Release asset URL still works unauthenticated for a public repo | Post-publish verification | Low — the repo is public and Phase 34's UAT did exactly this on 2026-08-27. If it ever fails, fall back to `gh release download`. |
| A3 | `release.yml`'s `concurrency: release-${{ github.ref }}` means N simultaneous tag pushes produce N parallel non-cancelling runs | P9 | Low — `github.ref` differs per tag, so the groups are distinct. Worst case the runs serialize, which changes nothing but wall time. |
| A4 | No GitHub Actions minutes / rate limit will throttle 3-4 simultaneous `release.yml` runs | P9 | Low — each run is a checkout + `uv build` + `gh release create`; Phase 34 ran two concurrently without incident. |
| A5 | Hoisting D-02/D-12 to a `checkpoint:decision` in 40-01 is compatible with D-07's "exactly two blocking checkpoints" (read as: two gates on *irreversible operations*) | OQ-1 / P1 | **Medium** — this is an interpretation of a locked decision, not a measurement. Must be confirmed by the operator before planning. See OQ-1. |
| A6 | Refreshing `.claude/projects/.../memory/market-data-client-releases.md` (if it exists) is desirable but not required | State of the Art | Low — not a ROADMAP criterion; Phase 34 treated it as in-scope hygiene. Verify the file's existence at plan time rather than inheriting either claim. |

---

## Open Questions

### OQ-1 (BLOCKING for plan structure) — Where do the D-02 and D-12 scope questions actually live?

- **What we know:** D-07 and D-12 both place these questions inside checkpoint (a), the pre-merge
  gate. Both are genuine, unresolved operator decisions and neither may be auto-resolved (precedent
  D-08/D-18). Both are asked *after* the bumps, the single `uv lock`, the branch push and the 15/15
  CI assertion have already happened.
- **What's unclear:** an "approve" on D-02 requires a **second** `uv lock`, which contradicts D-10
  and ROADMAP criterion 2. An "approve" on D-12 requires a code change plus updating ≥6 existing
  assertions in `test_snapshot_no_data_row.py`, then a fresh CI run and a second presentation of
  checkpoint (a). Neither branch is currently expressible in a plan that also satisfies D-10.
- **Recommendation:** hoist both questions into a `checkpoint:decision` gate at the top of plan
  40-01, and re-present the resolved answers as read-back facts inside the 40-02 pre-merge briefing.
  Blocking gates on *irreversible operations* stay at exactly two (D-07's actual concern); `uv lock`
  stays single-run (D-10); CI runs once against final content. **Confirm with the operator before
  planning.** If the operator insists the questions stay at checkpoint (a), the plan must
  additionally define the explicit re-loop path (re-bump → second `uv lock` with a documented D-10
  deviation → re-push → re-assert 15/15 → re-present gate (a)) rather than leaving it implicit.

### OQ-2 — If D-12 is declined, what concrete destination does the README note get re-pointed to?

- **What we know:** D-12 requires that on decline, the note stops naming "Phase 40" and is either
  reassigned to a named phase or explicitly marked "pendiente, sin fase asignada".
- **What's unclear:** whether a v1.8 milestone/phase exists to name. `.planning/ROADMAP.md` ends at
  Phase 40; `.planning/REQUIREMENTS.md` § Deferred/v-next lists the existing backlog.
- **Recommendation:** default to the explicit "pendiente, sin fase asignada" wording plus a
  `deferred-items.md` entry in the phase directory, unless the operator names a destination at the
  same checkpoint. Same treatment for D-02's decline branch.

### OQ-3 — Does an in-repo release-memory file exist, and should it be refreshed?

- **What we know:** Phase 34-03 Task 3 refreshed
  `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md` and
  deliberately did **not** create one for iol. That file's install lines would now be stale again
  (they pin `market-data-client-v0.5.0`).
- **What's unclear:** whether the file survives in the current checkout, and whether iol/matriz
  memory files were created in v1.7.
- **Recommendation:** `ls` the memory directory during planning. If
  `market-data-client-releases.md` exists, add a post-publish refresh task mirroring 34-03 Task 3
  (all six regions, with exact-occurrence-count assertions on both install lines). Do not create new
  memory files — that remains the deferred item.

### OQ-4 — Should matriz-client gain `__version__` in this phase?

- **What we know:** D-04 makes it explicitly discretionary; `release.yml:47` never reads it; matriz
  published `v0.1.1` and `v0.2.0` without it.
- **Recommendation:** **add it** (one line, `__version__ = "0.3.0"`), because `CLAUDE.md`'s Exports
  convention documents it as standard and the bump commit is the natural place. But do **not** add a
  `test_version_metadata.py` for matriz — that would import the P3 dist-metadata coupling into a
  fifth package for no gate benefit.

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` | branch/tag/merge topology | ✓ | 2.39.5 (Apple Git-154) | — |
| `gh` (authenticated) | PR, checks, merge, run watch, release view | ✓ | 2.90.0; `sebadlf`, scopes `gist, read:org, repo, workflow` | — |
| `uv` | lock, sync, run, venv | ✓ | 0.11.3 | — |
| Python 3.12 toolchain | local mirror + throwaway verification venv | ✓ (via uv-managed 3.12.11) | system `python3` is **3.9.6** | `uv venv --python 3.12` — mandatory flag |
| Network to `github.com` (SSH push + HTTPS API) | push, PR, release, wheel download | ✓ | remote `git@github.com:gravity-quant/market-libs.git` | — |
| GitHub Actions runners | 15 CI checks + N release runs | ✓ (assumed) | — | none — a runner outage blocks the phase; surface, do not bypass |
| Live financial APIs | **not needed** | n/a | — | Phase 39 owns live verification; Phase 40's deep chains are `from_api(None)` and require no network |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** system `python3` is 3.9.6 — always pass `--python 3.12` to
`uv venv` / `uv run`.

---

## Validation Architecture

### Test framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| Config file | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`, `pythonpath = ["."]`) |
| Quick run command | `uv run pytest packages/<pkg> -q` |
| Full suite command | `uv run pytest packages/<pkg>` × 6 **plus** `uv run pytest -q verification/<12-file allowlist>` — **never** a bare `uv run pytest` |

### Phase requirement → verification map

This phase ships no product code, so the "tests" are shell assertions over git/gh/registry state,
not pytest cases. Every one is automatable in well under 30 seconds except the CI watch and the
release-run watch.

| Criterion | Behavior | Type | Automated command | Exists? |
|-----------|----------|------|-------------------|---------|
| SC-1 | Only changed packages bumped | shell | `for p in packages/*/; do awk -F'"' '/^version/{print $2;exit}' $p/pyproject.toml; done` compared to the locked target table | ✅ |
| SC-1 | Breaking callout is **first** in each `## Changelog` | shell | `grep -n -A2 '^## Changelog' packages/<pkg>/README.md` → first `###` is the new version; body's first non-blank line is the bold breaking callout | ✅ |
| SC-1 | Migration table present and executable | shell | per-package `grep -q` on each locked before/after token (e.g. `market_data.last.price`, `not snapshot.market_data`, `titulo.puntas`, `tickPriceRanges\["0"\].tick`) | ✅ |
| SC-1 | Unchanged packages NOT re-published | shell | `git tag -l 'ambito-financiero-client-v*'` and `'wallets-client-v*'` unchanged from the pre-phase set | ✅ |
| SC-2 | `uv.lock` refreshed exactly once | shell | `git log --oneline <base>..HEAD -- uv.lock \| wc -l` == 1, **and** `git show --numstat --format= <that commit> -- uv.lock` == `N N` | ✅ |
| SC-2 | CI green asserted by explicit count | shell | Pattern 1 (15 total / 15 pass / 2 per bumped package) | ✅ |
| SC-2 | Merge is a real merge commit | shell | `test "$(git rev-list --parents -n1 origin/main \| wc -w)" -eq 3` and `gh pr view <n> --json state` == `MERGED` | ✅ |
| SC-3 | Annotated tag on the re-resolved merge SHA | shell | `git cat-file -t <tag>` == `tag`; `git rev-list -n1 <tag>` == `git rev-parse origin/main`; per tag | ✅ |
| SC-3 | `release.yml` unedited | shell | sha256 identity across refs (P2 corrected form) | ✅ |
| SC-3 | Wheel + sdist published per package | shell | `gh release view <tag> --json assets --jq '.assets[].name'` matches both exact filenames | ✅ |
| SC-3 | Post-publish install + deep chain | shell + python | throwaway `uv venv --python 3.12` + `uv pip install <public wheel URL>` + the § Code Examples assertions | ❌ **Wave 0 — no precedent task exists** |
| SC-4 | Two independent, never-collapsed human gates | artifact | two `autonomous: false` PLAN.md files, each with exactly one `<task type="checkpoint:human-verify" gate="blocking">`; each SUMMARY records the operator's reply **verbatim with timestamp** and states the approval was not auto-issued | ✅ (34-02/34-03 template) |

### Sampling rate

- **Per task commit:** the specific shell assertion in that task's `<verify><automated>` block.
- **Per plan:** the full local CI mirror (all four job bodies, including the eight lint gates and the
  12-file allowlist) before any push.
- **Phase gate:** 15/15 by count on the PR, then post-publish install verification, then
  `/gsd-verify-work`.

### Wave 0 gaps

- [ ] **Post-publish wheel-install verification task** — no precedent as a PLAN task (Phase 34 did it
      in UAT). Must be authored: throwaway venv, public URLs, per-package `__version__` assertion
      (skip matriz per D-04), and the deep chains from § Code Examples.
- [ ] **Corrected workflow-immutability assertion** — the Phase 34 form is broken (P2). The sha256
      form must be written fresh.
- [ ] **`uv sync` step after `uv lock`** — absent from `34-01-PLAN.md` Task 3; required here by P3.
- [ ] No new pytest files or fixtures are needed. Framework install: none.

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high`.

### Applicable ASVS categories

| ASVS category | Applies | Standard control |
|---------------|---------|------------------|
| V2 Authentication | yes | `gh auth status` only — **never echo the token**; the command already redacts it. No credential enters a commit, a PR body, a tag message, a Release note (`--generate-notes`), or a SUMMARY. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | **yes — the phase's central control** | `main` has **no branch protection** (API 404) and all three merge methods are enabled. The two blocking human checkpoints are the *only* access control on the merge and on the tag push. Neither may be satisfied by `auto_advance`, yolo mode, silence, ambiguity, or agent self-issue. |
| V5 Input Validation | yes | The tag string must satisfy `release.yml:28`'s regex exactly; the version it captures must equal the tagged tree's `pyproject.toml` version, read with the pipeline's own `awk`. |
| V6 Cryptography | no | No crypto is written. sha256 is used only as a file-identity check. |
| V14 Configuration | yes | `.github/workflows/*` is read-only. No gate may be patched to pass. |

### Threat patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---------|--------|---------------------|
| Merging red / pending / cancelled / zero-check CI into an unprotected public `main` | Tampering | Assert by explicit count (15/15 + per-package rows), never by absence of `fail` |
| Publishing a secret in the 182-commit diff that becomes public on merge | Information Disclosure | Credential scan over `git diff origin/main...HEAD` immediately before the push: JWT shape `eyJ[A-Za-z0-9_-]{20,}`; `client_secret`-style assignment of a 20+ char value; `git ls-files \| grep -E '(^\|/)\.env$'` empty. Report file+line only, never the value. Per CLAUDE.md, per-package `.env` files exist on disk — confirm none is tracked. |
| Squash/rebase orphaning cross-referenced SHAs | Tampering | `--merge` mandated; parent count asserted == 2. Dozens of Phase 35-39 SUMMARY files cite SHAs by value. |
| Tag placed on branch HEAD instead of the merge commit | Tampering | Tag the **re-resolved** `git rev-parse origin/main`; assert `git rev-list -n1 <tag>` equals it |
| Force-push rewriting published history | Tampering | `--force` and `--force-with-lease` forbidden on every push; a rejected push halts the phase |
| `git push --tags` publishing stale local tags | Tampering | Push each tag **by name**; `v1.1`…`v1.6` are milestone tags that must not ride along |
| Agent self-approving an irreversible operation despite `auto_advance: true` + `mode: yolo` | Elevation of Privilege / Repudiation | Two `autonomous: false` plans, one blocking `checkpoint:human-verify` each; operator reply recorded **verbatim with timestamp**; explicit statement in the gate text that auto-advance and yolo do not satisfy it. Proven under identical config in Phase 34 (STATE.md:384, :386). |
| A slopsquatted `market-data-client` on PyPI | Supply chain | The post-publish install uses the **full release-asset URL**, never a bare package name. `packages/market-data-client/README.md:38-40` already documents this risk. |

---

## Sources

### Primary (HIGH confidence — measured live in this session)

- Working tree at `f66c049a5a94`: `packages/*/pyproject.toml`, `packages/*/src/*/__init__.py`, `packages/*/README.md`, `uv.lock`, `packages/*/src/*/models.py`
- `git show <tag>:...` for `matriz-client-v0.2.0`, `iol-client-v0.3.0`, `market-data-client-v0.5.0`, `higyrus-client-v0.2.0`, `ambito-financiero-client-v0.2.0`, `wallets-client-v0.2.0`
- `verification/snapshots/{ambito-financiero,higyrus,iol,matriz}-client-surface.txt` diffed tag→HEAD
- `.github/workflows/ci.yml` (full), `.github/workflows/release.yml` (full)
- `gh api repos/gravity-quant/market-libs` (merge methods, `delete_branch_on_merge`, visibility)
- `gh api repos/gravity-quant/market-libs/branches/main/protection` → HTTP 404
- `gh pr list`, `gh auth status`, `gh release view <tag> --json assets` × 4
- `git ls-remote --heads origin`, `git tag -l`, `git rev-list --left-right --count origin/main...HEAD`
- Local CI mirror run: `uv lock --check`, `ruff check`, `ruff format --check`, `lint-imports`, the three `tools/check_*.py`, the logging grep, `mypy`, the 12-file verification allowlist, four per-package pytest suites
- Live Python execution of every deep-chain assertion in § Code Examples

### Primary (HIGH confidence — project artifacts)

- `.planning/phases/40-releases-breaking-coordinados/40-CONTEXT.md`
- `.planning/milestones/v1.6-phases/34-releases-por-paquete/{34-CONTEXT,34-01-PLAN,34-02-PLAN,34-03-PLAN,34-01-SUMMARY,34-UAT}.md`
- `.planning/phases/37-matriz-client-dicts-residuales-tipados-alias/37-0{1,2,3,4,5}-SUMMARY.md`
- `.planning/phases/36-market-data-client-.../36-DEFERRED-market-data-leaves.md`
- `.planning/phases/39-.../deferred-items.md`
- `.planning/{REQUIREMENTS,STATE}.md`, `.planning/config.json`
- `./CLAUDE.md`
- `packages/market-data-client/tests/test_version_metadata.py`, `.../test_snapshot_no_data_row.py`

### Secondary (MEDIUM confidence)

- STATE.md decision log lines 263-266, 384-389 (Phase 28/34 execution facts, including the
  corrected workflow-immutability assertion form)

### Tertiary (LOW confidence)

- None. No external web source was consulted; nothing in this phase depends on third-party
  documentation.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Bump set + version targets | HIGH | Every current version, published tag and surface delta re-measured against the tags |
| Migration table content | HIGH | Before/after declared types read from `git show <tag>:models.py` vs the tree; every "after" behavior executed live |
| Release mechanics (branch/PR/CI/merge/tag/publish) | HIGH | Phase 34 executed the identical playbook 3 days ago; repo settings, workflow contents and asset naming re-verified |
| Edit-site inventory | HIGH | Grepped and line-numbered; the invisible `__init__.py` comment block was found by a Python-scoped grep |
| Pitfalls P2, P3, P6 | HIGH | P2 is documented as a Phase-34 execution failure; P3 read from the test source; P6 measured from the current branch topology |
| P1 / OQ-1 (checkpoint sequencing) | MEDIUM | The blast radius is measured (6 red assertions, second `uv lock`); the *resolution* is a recommendation that reinterprets a locked decision and needs operator confirmation |
| Post-publish verification shape | HIGH | Deep chains executed live; the venv/URL shape matches Phase 34's UAT which succeeded |
| Timing / runner behavior for 3-4 concurrent release runs | MEDIUM | Extrapolated from Phase 34's two concurrent runs; the concurrency group is provably per-tag |

**Research date:** 2026-08-30
**Valid until:** 2026-09-06 — short window on purpose. The ahead-count (182), the phase base SHA
(`f66c049`), `origin/main` (`20ebb78`), and the dirty-file list all move with the next commit.
Every SHA and count in this document must be recomputed at execution time, never trusted as a literal.
