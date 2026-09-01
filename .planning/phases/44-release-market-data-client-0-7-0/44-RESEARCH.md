# Phase 44: Release `market-data-client` 0.7.0 — Research

**Researched:** 2026-09-01
**Domain:** Release mechanics (git/GitHub Actions/uv packaging) + GSD checkpoint-gate authoring semantics
**Confidence:** HIGH (all load-bearing claims measured in-session against this repo and this GSD runtime)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Los "4 sitios de versión" son `packages/market-data-client/pyproject.toml:3`,
  `packages/market-data-client/src/market_data_client/__init__.py:163`, y **dos** líneas de
  `README.md` — `:15` (URL de instalación `git+...@market-data-client-v0.6.0`) y `:24` (nombre del
  wheel `market_data_client-0.6.0-py3-none-any.whl`, que aparece dos veces en esa misma línea).
  **`uv.lock` NO es uno de los 4 sitios** — es un artefacto aparte, refrescado exactamente una vez
  (D-02). `test_version_metadata.py` tampoco es un sitio: parsea `pyproject.toml` en tiempo de
  ejecución y verifica consistencia, no hardcodea nada.
- **D-02:** `uv lock` corre **exactamente una vez**, después de bumpear los 4 sitios, antes de abrir
  el PR. `release.yml` **no se edita** — séptima reutilización sin cambios.
- **D-03:** Se agrega una sección `### v0.7.0` insertada **directamente arriba** de `### v0.6.0`
  (`README.md:125`) — **sin** sección "Unreleased" de staging. Formato exacto: párrafo en negrita con
  el callout de ruptura, luego tabla de migración de dos columnas, luego prosa — espejando
  literalmente la forma de la sección `### v0.6.0` (`README.md:127-152`).
- **D-04:** La tabla de migración se transcribe desde `43-DISPOSITION.md` § 1.1 (Instrument) y § 1.2
  (Segment), como **dos tablas separadas** — no una sola fusionada — convirtiendo el formato de 6
  columnas de ingeniería al formato de 2 columnas del README (expresión vieja → expresión nueva).
  - Fila de Instrument explícita: `marketId` se preserva como **alias aditivo** (nunca rename),
    remoción programada para el próximo MAJOR.
  - Filas de Segment: `segment`/`live_instruments` agregados; `marketSegmentId`/`marketId`/
    `description` removidos sin reemplazo (D-13).
- **D-05 [confirmado por el operador]:** Se **foldea** `SURF-MD-FEEDSUB-43`: agregar
  `"FeedSubscription"` al `__all__` de `__init__.py`. Verificar corriendo
  `uv run python tools/check_surface_types.py` inmediatamente después del edit, **antes** de pushear.
- **D-06:** Se **difiere** `DRV-MD-SEG-43` a la Phase 45. No tocar `main_market_data.py`.
- **D-07:** No existe branch ni PR de v1.8 hoy. Crear branch nueva con patrón `milestone/vX.Y-slug`,
  pushear los commits pendientes (fast-forward), abrir PR nuevo.
- **D-08 [ítem crítico]:** Exactamente **dos** checkpoints humanos bloqueantes, implementados como
  **dos `PLAN.md` separados** (`autonomous: false` cada uno): (a) antes de `gh pr merge --merge`
  (nunca squash, nunca rebase), (b) antes de pushear los tags anotados. Cada uno debe llevar
  literalmente `<task type="checkpoint:decision" gate="blocking-human">` o
  `<task type="checkpoint:human-verify" gate="blocking-human">` — **nunca** `gate="blocking"` a
  secas. Un grep post-hoc de `gate="blocking"` (sin `-human`) sobre los dos plans debe devolver cero
  resultados antes de considerar la fase cerrada.
- **D-09:** El tag anotado se crea sobre el SHA del merge commit **re-resuelto en vivo post-merge**.
  Una sola aprobación del checkpoint (b) cubre el push del único tag de esta ronda.
- **D-10:** Todos los bloques `<verify>` corren vía `bash -c`. Todo conteo se re-deriva en vivo,
  nunca se hardcodea. Baseline de tags pre-fase: `iol-client` 4, `higyrus-client` 3, `matriz-client`
  3, `ambito-financiero-client` 2, `wallets-client` 1, `market-data-client` 7. Post-fase: los cinco
  primeros **idénticos**, `market-data-client` a **8**.
- **D-11:** El gate de merge cuenta **15/15 checks de CI explícitamente**, nunca por
  ausencia-de-fallo.
- **D-12:** Verificación post-publicación: instalar desde el **wheel público** en un entorno
  descartable **fuera del repo** y ejercer una cadena profunda ya existente en el paquete instalado.

### Claude's Discretion

- Wording exacto de la prosa de la sección `### v0.7.0` del changelog (español, tabla antes/después,
  línea líder en negrita).
- Nombre exacto de la branch nueva (dentro del patrón `milestone/v1.8-...`) y título/body del PR.
- Si además de `SURF-MD-FEEDSUB-43` conviene agregar cosmética discrecional (ninguna identificada).
- Agrupamiento y orden de commits dentro de la fase.

### Deferred Ideas (OUT OF SCOPE)

- `DRV-MD-SEG-43` (`main_market_data.py:1541-1542`) — diferido explícitamente a la Phase 45 (D-06).
- Agregar `__version__` a `matriz_client/__init__.py` — de otro paquete, no toca esta fase.
- **Reviewed Todos (not folded):** Ninguno — `todo.match-phase 44` devolvió 0 matches.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PUB-01 | La corrección de forma llega a los consumidores como release publicada `0.7.0` con tabla de migración, tras dos gates humanos independientes escritos como tales en el plan | § Version Sites (4 sitios medidos), § Migration Table Source (contenido exacto listo para transcribir), § Gate Authoring Semantics (mecánica exacta de los dos gates, con la corrección crítica de D-08), § Release Pipeline Mechanics (regex de tag + version-match gate), § Common Pitfalls |
</phase_requirements>

---

## Summary

This phase is **release mechanics, not engineering**. Phase 43 already landed the `Instrument`/`Segment`
shape correction on `main` unpublished; Phase 44 bumps four version strings, writes a changelog with
two migration tables, folds a two-line export fix, opens a PR, and — behind two independent human
gates — merges it and pushes one annotated tag. Every technical fact in CONTEXT.md was re-measured
in this session and **all of them hold** except three, documented below.

The dominant risk is **not** the packaging. It is the gate-authoring defect that has now recurred
four times (Phase 34 ×2, Phase 40 ×3 plan files). CONTEXT.md D-08 correctly identifies
`gate="blocking-human"` as the fix, and that attribute **is** real and honoured — but only in one of
the two layers that can auto-approve a checkpoint, and only for one of the two checkpoint types D-08
permits. Authoring the plan exactly as D-08 literally specifies would produce a gate that the
**orchestrator** still auto-approves under `auto_advance: true`. This is the single highest-value
finding of this research and is written up in full in § Gate Authoring Semantics.

Two further traps: `workflow.human_verify_mode` is set to `end-of-phase`, which instructs the planner
to **suppress** `checkpoint:human-verify` tasks entirely; and the local `uv.lock` + `dist-info`
staleness will produce a false-red on the version-metadata test unless `uv sync` runs after the bump.

**Primary recommendation:** Author both gates as `<task type="checkpoint:human-action" gate="blocking-human">`.
`human-action` is the only checkpoint type that stops at **both** the executor and the orchestrator
layer under `auto_advance: true`; the `gate="blocking-human"` attribute is retained so that ROADMAP
criterion 4's literal in-file grep passes. This deviates from D-08's enumerated types and is flagged
as OQ-1 for user confirmation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Version string bump (4 sites) | Repo source tree | — | Hand-edited files; no build step derives them |
| Lockfile consistency | uv (`uv.lock`) | CI lint job | `uv lock --check` is an enforced CI gate |
| Changelog + migration table | `README.md` (package tier) | — | Consumer-facing doc shipped inside the wheel via `readme = "README.md"` |
| Public export surface | `__init__.py` (package tier) | `tools/check_surface_types.py` | `__all__` is the published surface; the gate scans it |
| Merge authorization | Human operator | GSD checkpoint mechanism | Irreversible; `main` has no branch protection |
| Tag-push authorization | Human operator | GSD checkpoint mechanism | Irreversible; a GitHub Release cannot be cleanly unpublished |
| Build + publish | GitHub Actions (`release.yml`) | — | Tag-triggered; reads `pyproject.toml` only |
| Post-publish proof | Throwaway venv outside repo | — | Must exercise the installed distribution, not the checkout |

---

## Standard Stack

No new libraries. This phase uses only tooling already pinned in the workspace.

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `uv` | 0.9.0 | Lockfile refresh, workspace sync, build | Project standard per CLAUDE.md `[VERIFIED: CLAUDE.md tech stack + uv.lock present]` |
| `git` | system | Branch, annotated tag, merge commit | — |
| `gh` | authenticated as `sebadlf` | PR create, check counting, merge | `[VERIFIED: gh auth status in-session]` |
| GitHub Actions | `release.yml` (unmodified) | Build wheel + sdist, create Release | `[VERIFIED: read .github/workflows/release.yml]` |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `tools/check_surface_types.py` | Export-surface gate | Immediately after the `__init__.py` edit (D-05) |
| `tools/check_uniform_structure.py` | models.py/types.py presence | Part of CI lint; re-run locally before push |
| `tools/surface_parity.py` | sync/async surface parity | Part of CI lint; silent = pass |
| `tools/check_decode_intactness.py` | `_decode.py` hash collapse | Part of CI lint |
| `pytest` | Package test suite incl. `test_version_metadata.py` | After `uv sync`, before push |

**Installation:** None. No external package is added by this phase.

---

## Package Legitimacy Audit

**Not applicable — this phase installs no third-party packages.**

The only install performed is of the **first-party** artifact this phase itself publishes
(`market_data_client-0.7.0-py3-none-any.whl`), fetched from the repo's own GitHub Release URL under
`github.com/gravity-quant/market-libs` into a throwaway venv (D-12). It is not a registry lookup and
carries no slopsquatting exposure. Phase 43 recorded the identical disposition:
`T-43-SC (instalaciones de paquetes) — accept, no-op verificado: cero paquetes externos instalados`
`[VERIFIED: 43-03-SUMMARY.md:255]`.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Gate Authoring Semantics

> This is the section the phase exists for. Read it before writing either checkpoint plan.

### What is actually implemented in this GSD runtime

`gate="blocking-human"` is **real** and **is** honoured — CONTEXT.md D-08 is correct that it is the
right attribute. But it appears in exactly four places in the entire installed runtime
`[VERIFIED: grep -rn 'blocking-human' .claude/]`:

| File | Line | Role |
|------|------|------|
| `.claude/agents/gsd-planner.md` | 468 | Instructs planner to emit it for package-legitimacy checkpoints |
| `.claude/agents/gsd-executor.md` | 207 | Example emission |
| `.claude/agents/gsd-executor.md` | 219 | "Use `gate=\"blocking-human\"` … unambiguously excluded from auto-approval" |
| `.claude/agents/gsd-executor.md` | 316 | **The only behavioural rule that reads it** |

Aggregate gate-value census across the runtime: `gate="blocking"` ×19, `gate="blocking-human"` ×4,
`gate="advisory"` ×1 `[VERIFIED: grep -rhoE 'gate="[a-z-]+"' .claude/]`.

### The two layers that can auto-approve

**Layer 1 — the executor agent** (`.claude/agents/gsd-executor.md:314-318`), when `AUTO_CFG` is true:

| Checkpoint type | Behaviour | Honours `blocking-human`? |
|---|---|---|
| `checkpoint:human-verify` | Auto-approve **except** if `gate="blocking-human"` or package-legitimacy purpose | **YES** |
| `checkpoint:decision` | Auto-select first option. *(no exception clause of any kind)* | **NO** |
| `checkpoint:human-action` | "STOP normally. Auth gates cannot be automated." | N/A — always stops |

**Layer 2 — the execute-phase orchestrator** (`.claude/gsd-core/workflows/execute-phase.md:1057-1061`),
when `AUTO_MODE` is true and the executor returns a checkpoint:

| Checkpoint type | Behaviour | Honours `blocking-human`? |
|---|---|---|
| `human-verify` | Auto-spawn continuation with `{user_response}` = `"approved"`. Log `⚡ Auto-approved checkpoint`. | **NO** |
| `decision` | Auto-spawn continuation with `{user_response}` = first option. Log `⚡ Auto-selected: [option]`. | **NO** |
| `human-action` | "Present to user (existing behavior below). Auth gates cannot be automated." | N/A — always stops |

The string `blocking-human` **never appears anywhere under `.claude/gsd-core/workflows/`**. The
orchestrator is structurally unaware of the attribute.

### The consequence — three distinct failure modes

**FM-1 — `checkpoint:decision` + `gate="blocking-human"` is auto-selected at both layers.**
CONTEXT.md D-08 offers `checkpoint:decision gate="blocking-human"` as co-equal with the human-verify
form. It is not. The `blocking-human` exception clause exists **only** inside the human-verify branch
at executor line 316; the decision branch at line 317 has no exception. Authoring gate (a) as a
`checkpoint:decision` — even with the correct attribute — reproduces the Phase-34/40 failure exactly,
as a fifth occurrence. `[VERIFIED: gsd-executor.md:317 + execute-phase.md:1060]`

**FM-2 — `checkpoint:human-verify` + `gate="blocking-human"` stops at layer 1 but is auto-approved
at layer 2.** The executor correctly refuses to self-approve and returns the checkpoint upward. The
orchestrator then sees `type: human-verify`, reads `AUTO_MODE == true`, and spawns a continuation
agent with `{user_response} = "approved"` — without ever inspecting the gate attribute. The
irreversible merge proceeds. `[VERIFIED: execute-phase.md:1059]`

**FM-3 — `human_verify_mode: end-of-phase` suppresses the emission entirely.**
`.planning/config.json` sets `workflow.human_verify_mode: "end-of-phase"`
`[VERIFIED: read config.json]`. `.claude/gsd-core/references/planner-human-verify-mode.md:7-9`
instructs the planner under that mode: *"Do **not** emit any `<task type="checkpoint:human-verify">`
tasks"*, folding them into `<verify><human-check>` blocks harvested at end-of-phase into a UAT file.
A planner that follows that reference literally will emit **zero** human-verify checkpoints — the
gates vanish rather than collapse. That same file line 51 confirms the escape hatch:
*"`checkpoint:decision` and `checkpoint:human-action` tasks are still emitted in `end-of-phase` mode."*

### Live values confirming these paths are hot

```
workflow.auto_advance        = true    [VERIFIED: .planning/config.json]
workflow._auto_chain_active  = true    [VERIFIED: .planning/config.json]
mode                         = "yolo"  [VERIFIED: .planning/config.json]
workflow.human_verify_mode   = "end-of-phase"  [VERIFIED: .planning/config.json]
gsd-tools query check auto-mode --pick active → true   [VERIFIED: executed in-session]
```

### Recommended construct

Only `checkpoint:human-action` stops unconditionally at **both** layers, and it is explicitly exempt
from `end-of-phase` suppression. Author both gates as:

```xml
<task type="checkpoint:human-action" gate="blocking-human">
  <name>Task N: FIRST blocking go/no-go gate — before the IRREVERSIBLE merge (D-08a)</name>
  <files>none — this task modifies no file</files>
  <action>PAUSE. …</action>
  <instructions>…</instructions>
  <verification>…</verification>
  <resume-signal>Reply "approved" to authorize the merge, or "abort"</resume-signal>
</task>
```

This satisfies every constraint simultaneously:

- ROADMAP criterion 4 ("autorizados literalmente como `gate=\"blocking-human\"` en el archivo de
  plan") — the attribute is present verbatim and greppable in-file.
- D-08's post-hoc check (`grep 'gate="blocking"'` without `-human` returns zero) — passes.
- PITFALLS Pitfall 14's prescription ("Author the release plan with `gate=\"blocking-human\"`
  literally") — satisfied.
- Mechanical safety at both layers — satisfied, which none of D-08's two enumerated types achieves.

**Belt-and-suspenders (recommended in addition):** keep the Phase-40 prose armour verbatim in
`<action>` and `must_haves.prohibitions` — the sentence *"This gate is never auto-approvable:
`auto_advance: true` and `mode: yolo` are both active … silence does not satisfy it … and the agent
may not self-issue it."* That prose is what actually saved the previous four occurrences via
orchestrator override. It is a defence in depth, not a substitute for the correct type.

**Deviation flag:** using `human-action` instead of D-08's two enumerated types is a deviation from a
locked decision. See OQ-1.

---

## Version Sites — Measured

D-01's claim of **exactly 4 sites** is **empirically confirmed**. Full census of `0.6.0` in the
package, excluding the historical changelog body (`README.md:12x-15x`) which must NOT change
`[VERIFIED: grep -rn "0\.6\.0" packages/market-data-client/]`:

| # | File:line | Current content | Change to |
|---|-----------|-----------------|-----------|
| 1 | `pyproject.toml:3` | `version = "0.6.0"` | `version = "0.7.0"` |
| 2 | `src/market_data_client/__init__.py:163` | `__version__ = "0.6.0"` | `__version__ = "0.7.0"` |
| 3 | `README.md:15` | `…@market-data-client-v0.6.0#subdirectory=…` | `…@market-data-client-v0.7.0#…` |
| 4 | `README.md:24` | `…/download/market-data-client-v0.6.0/market_data_client-0.6.0-py3-none-any.whl` | **two** substitutions on this one line |

**Non-sites correctly excluded (do NOT edit):**

- `models.py:477` — `**BREAKING since 0.6.0 (Phase 40, D-12).**` is a historical docstring record.
- `README.md` `### v0.6.0` changelog body (lines ~125-152) — historical.
- `packages/market-data-client/tests/test_version_metadata.py` — parses `pyproject.toml` at runtime;
  hardcodes nothing. Three test functions: `test_pyproject_is_readable_from_the_package_dir`,
  `test_dunder_version_matches_pyproject`,
  `test_dunder_version_matches_installed_distribution_metadata` `[VERIFIED: read file]`.

**`uv.lock` is a separate artifact, and it DOES carry the version:** `uv.lock:487-489` reads
`name = "market-data-client"` / `version = "0.6.0"` / `source = { editable = ... }`
`[VERIFIED: grep uv.lock]`. CI's lint job runs `uv lock --check` as its first step
(`.github/workflows/ci.yml:32-33`) `[VERIFIED: read ci.yml]`, so an unrefreshed lockfile is a **hard
CI failure**, not a cosmetic omission. D-02's single `uv lock` after the four bumps is therefore
mandatory, not optional.

**Correction to an upstream artifact:** `43-03-SUMMARY.md:264` says Phase 44 receives *"el bump en
los **tres** sitios de versión"*. That count is stale/wrong; the measured count is 4, matching D-01.
Trust CONTEXT.md D-01, not the Phase 43 summary. `[VERIFIED: in-session grep]`

---

## The `FeedSubscription` Fold (D-05) — It Is a Two-Line Fix

D-05 describes this as "un fix de una línea … agregar `FeedSubscription` al `__all__`". Measured, it
is **two edits in two blocks**, because the name is absent from the import block as well:

| Location | Current | Needed |
|---|---|---|
| `__init__.py` import block from `market_data_client.models` (lines 72-90) | `FeedIngestor, FeedMarket, FeedPipeline, Health, …` — **no `FeedSubscription`** | insert `FeedSubscription,` after `FeedPipeline,` (alphabetical) |
| `__init__.py` `__all__` (lines 114-119) | `"FeedIngestor", "FeedMarket", "FeedPipeline", "HealthFeed", …` — **no `"FeedSubscription"`** | insert `"FeedSubscription",` after `"FeedPipeline",` |

`[VERIFIED: grep -n "Feed" on both files]`. `models.__all__:106` already exports it
`[VERIFIED: models.py:103-109]`; the class is defined at `models.py:1372`.

**Adding only to `__all__` would be a defect**, not a fix: `__all__` would name an unbound module
attribute, breaking `from market_data_client import *` and any surface tooling that resolves the
names. Both edits are required.

**Baseline for the gate assertion** — measured before any edit:

```
surface types: 6 packages, 186 `__all__` names, 337 definitions scanned, 452 fields scanned,
13 constant/alias exports, 24 exempted (…), 0 violations
```

`[VERIFIED: uv run python tools/check_surface_types.py, in-session]`. After the fold the count must
read **187 `__all__` names / 0 violations**. Assert the *count*, per D-11's positive-assertion
doctrine — not merely "0 violations", which would also hold if the edit silently did nothing.

Companion gates, both green at baseline: `check_uniform_structure.py` →
`"all 6 packages … carry models.py, types.py"`; `surface_parity.py` → silent (pass)
`[VERIFIED: executed in-session]`.

---

## Migration Table Source (D-04)

Source of truth is `43-DISPOSITION.md` § 1.1 (12 rows) and § 1.2 (5 rows), already written
`[VERIFIED: read lines 29-110]`. Convert 6-column engineering format → 2-column README format.

### Shipped shape to describe (measured from source, not from the disposition doc)

`Instrument` (`models.py:788`) now declares, in order: `symbol: str`, `marketId: str`, `segment: str`,
`expired: bool`, `market_id: str`, `currency: str`, `days_to_maturity: int`, `maturity: str`,
`outright: bool`, `subscribed: bool`, `active: bool | None = None`. It carries a `from_api` override
mirroring wire `market_id` into `marketId` when `marketId` is absent — fill-never-overwrite, copies
the dict `[VERIFIED: models.py:788-861]`.

`Segment` (`models.py:870`) now declares exactly `segment: str`, `live_instruments: int`, with no
`from_api` override `[VERIFIED: models.py:870-896]`.

### Rows to emit

**Instrument** — additive plus one removal:

| Old | New |
|---|---|
| `inst.instrumentType` | *removed — the key never existed on the wire; always decoded `""`* |
| `inst.marketId` | still works — **additive alias**, now carries the real value instead of `""`; prefer `inst.market_id`; removal scheduled for the next MAJOR |
| — | `inst.market_id`, `inst.currency`, `inst.days_to_maturity`, `inst.maturity`, `inst.outright`, `inst.subscribed` are new |
| — | `inst.active` is new and is `bool \| None` — check `is None`, do not assume `bool` |

**Segment** — whole-model replacement (disjoint key sets):

| Old | New |
|---|---|
| `seg.marketSegmentId` | *removed, no replacement — always decoded `""`* |
| `seg.marketId` | *removed, no replacement — always decoded `""`* |
| `seg.description` | *removed, no replacement — always decoded `""`* |
| — | `seg.segment` (`str`) is new |
| — | `seg.live_instruments` (`int`) is new |

**Do not merge the two tables** (D-04). The confusable pair is `Segment.marketId` (removed, no
replacement) vs `Instrument.marketId` (preserved as additive alias) — merging invites exactly that
confusion.

### An additional row CONTEXT.md does not enumerate — measured behavioural flip

`SafeModel.__bool__` (`models.py:183`) implements Null-Object truthiness: *"falsy iff the model
carries nothing … A model equal to its own `empty()` answers `False`"* `[VERIFIED: models.py:183-200]`.
Executed against a real wire row `{"segment": "DDA", "live_instruments": 3}`:

```
OLD Segment shape → OldSegment(marketSegmentId='', marketId='', description='')  → bool = False
NEW Segment shape → Segment(segment='DDA', live_instruments=3)                   → bool = True
```

`[VERIFIED: executed in-session under uv run python]`

Because the old and new key sets were disjoint, **every** `Segment` a released consumer ever decoded
equalled its own `empty()` and was therefore **falsy**. Post-0.7.0 the same rows are **truthy**. A
consumer holding `if seg:` or `[s for s in segs if s]` silently received an empty result before and
receives every row now. This is a real, silent, consumer-visible behaviour change and warrants a
migration row:

| Old | New |
|---|---|
| `if seg:` was always `False` (every row decoded to three empty strings ⇒ equal to `empty()`) | `if seg:` is `True` for any populated row — a filter that silently dropped everything now keeps everything |

**PITFALLS states this flip in the wrong direction.** `.planning/research/PITFALLS.md` "Looks Done
But Isn't" § SHAPE-01 reads *"`Segment` rows go from always-truthy-with-empty-strings to
falsy-when-empty"*. Measured, it is the inverse: falsy-on-real-data → truthy-on-real-data. Write the
changelog from the measurement, not from the checklist wording. `[VERIFIED: in-session execution]`

---

## Release Pipeline Mechanics

### `release.yml` — do not edit (D-02)

`[VERIFIED: read .github/workflows/release.yml]`

- **Trigger:** `on.push.tags: ["*-client-v*"]`
- **Tag regex:** `^([a-z][a-z0-9-]*-client)-v([0-9]+\.[0-9]+\.[0-9]+([.+-][a-zA-Z0-9.+-]+)?)$`.
  `market-data-client-v0.7.0` matches → `PACKAGE=market-data-client`, `VERSION=0.7.0`.
- **Directory gate:** fails unless `packages/$PACKAGE` exists.
- **Version-match gate:** `awk -F\" '/^version[[:space:]]*=/{print $2; exit}' "packages/$PACKAGE/pyproject.toml"`
  must equal the tag version. It reads **`pyproject.toml` only** — it will *not* catch a stale
  `__init__.py` or a stale README. Those are caught by `test_version_metadata.py` and by human
  review respectively. This is precisely the hole that shipped the Phase-34 README defect.
- **Build:** `uv build --package <pkg> --out-dir dist` → wheel + sdist.
- **Concurrency:** `group: release-${{ github.ref }}`, `cancel-in-progress: false`.

Verify non-modification by **sha256 digest identity** across HEAD, `origin/main`, prior release tags
and the new tag — not by the Phase-34 tag-baseline diff form, which PITFALLS records as
"stale-by-construction and failed three times".

### `ci.yml` — the 15 checks (D-11 confirmed)

`[VERIFIED: read .github/workflows/ci.yml]`

| Job | Count | Notes |
|---|---|---|
| `lint` (Lint y formato — ruff) | 1 | Includes `uv lock --check`, ruff check/format, import-linter, lint-logging, decode-intactness, uniform-structure, surface-types, driver locks |
| `pre-commit` | 1 | |
| `typecheck` (mypy) | 1 | src global + tests per package |
| `test` — matrix | 12 | 6 packages × 2 Python versions |
| **Total** | **15** | |

Matrix packages, verbatim in file order: `higyrus-client`, `wallets-client`, `matriz-client`,
`iol-client`, `ambito-financiero-client`, `market-data-client`. Python versions `["3.12", "3.13"]`.
Test job display name: `Tests · ${{ matrix.package }} · py${{ matrix.python-version }}`.

Note `concurrency.cancel-in-progress: true` on CI — pushing a commit mid-run cancels in-flight
checks. Phase 40's plan asserted `git rev-parse HEAD == git rev-parse origin/<branch>` at the gate
for exactly this reason; keep that assertion.

### Git / GitHub state — measured now

| Fact | Measured value |
|---|---|
| Current branch | `main` `[VERIFIED]` |
| `origin/main..HEAD` | **86** commits ahead |
| `HEAD..origin/main` | 0 |
| Open PRs | none |
| Highest PR | #15, MERGED, `milestone/v1.7-nobj-null-objects` → next PR will be **#16** |
| `gh auth status` | logged in as `sebadlf`, https protocol |

**The commit count already drifted from CONTEXT.md.** D-07 measured 84; the live value is **86**.
This is a live demonstration of D-10's re-derive rule — do not hardcode 84 or 86 in any `<verify>`
block; re-derive at execution time. `[VERIFIED: git rev-list --count, in-session]`

### Tag baseline — measured, matches D-10 exactly

| Package | Pre-phase count | Post-phase expected |
|---|---|---|
| `iol-client` | 4 | 4 (unchanged) |
| `higyrus-client` | 3 | 3 (unchanged) |
| `matriz-client` | 3 | 3 (unchanged) |
| `ambito-financiero-client` | 2 | 2 (unchanged) |
| `wallets-client` | 1 | 1 (unchanged) |
| `market-data-client` | 7 | **8** |

`market-data-client` existing tags: `v0.1.0, v0.2.0, v0.3.0, v0.3.1, v0.4.0, v0.5.0, v0.6.0`
`[VERIFIED: git tag -l, in-session]`. New tag string, character for character:
`market-data-client-v0.7.0`.

---

## Architecture Patterns

### Plan decomposition (3 plans, 3 waves) — precedent-locked

```
Wave 1 ── 44-01-PLAN.md   autonomous: true    PREP (fully reversible)
          ├─ bump 4 version sites
          ├─ FeedSubscription fold (2 edits) + surface gate → 187 names
          ├─ README ### v0.7.0 + 2 migration tables
          ├─ uv lock  (exactly once, after bumps)   ─── D-02
          ├─ uv sync  (regenerate dist-info)        ─── see Pitfall 3
          ├─ full local gate + test run
          └─ create branch, push, gh pr create → PR #16

Wave 2 ── 44-02-PLAN.md   autonomous: false   GATE (a) + MERGE   ◄── irreversible
          ├─ Task 1 (auto): count 15/15 checks positively; assert HEAD==origin/branch
          ├─ Task 2 CHECKPOINT — blocking-human, human-action
          └─ Task 3 (auto): gh pr merge <n> --merge   (never --squash, never --rebase)

Wave 3 ── 44-03-PLAN.md   autonomous: false   GATE (b) + TAG     ◄── irreversible
          ├─ Task 1 CHECKPOINT — blocking-human, human-action
          │    (re-resolve MERGE_SHA live: git fetch && git rev-parse origin/main)
          ├─ Task 2 (auto): git tag -a on re-resolved SHA; git push origin <tag> BY NAME
          ├─ Task 3 (auto): watch release.yml; assert wheel + sdist by exact filename
          └─ Task 4 (auto): install from PUBLIC wheel URL into throwaway venv OUTSIDE repo
```

Mirrors `40-01/02/03` structure exactly, with the gate type corrected. Keeping prep in its own
autonomous plan and each irreversible op in its own `autonomous: false` plan is also PITFALLS'
explicit prescription ("Do not co-locate the release with autonomous plans").

### Frontmatter template (from `40-02`/`40-03`, verified)

```yaml
---
phase: 44-release-market-data-client-0-7-0
plan: 02
type: execute
wave: 2
depends_on: [44-01]
files_modified: []
autonomous: false
requirements: [PUB-01]
user_setup:
  - service: github
    why: "..."
    dashboard_config:
      - task: "Be available to answer the FIRST blocking go/no-go checkpoint before the merge (D-08a)"
        location: "the executing terminal session"
must_haves:
  truths:   [...]
  prohibitions: [...]
---
```

`must_haves.prohibitions` on the checkpoint plans must carry the Phase-40 sentence verbatim:
*"Neither of this phase's two blocking human checkpoints on irreversible operations may be satisfied
by the agent itself, by `auto_advance`, by yolo mode, or by inferring approval from silence or from
an ambiguous reply. Only a literal operator response counts, and it is recorded verbatim."*

### Checkpoint task anatomy (from `40-02:259`, `40-03:172`)

Both precedent checkpoints carry `<name>`, `<files>none</files>`, `<read_first>`,
`<acceptance_criteria>` (7 and 6 items respectively), `<action>` opening with literal `PAUSE.`, and
`<what-built>`. Reuse this shape; change only the task `type` and the `gate` attribute.

The `<acceptance_criteria>` for each gate must include, at minimum:
1. The exact facts shown to the operator (PR URL/number, literal `gh pr checks` output with counted
   totals, diff stat, exact version transitions, or — for gate (b) — the re-resolved merge SHA with
   both parents and the exact tag string).
2. That no irreversible command ran before the reply.
3. That the reply is recorded verbatim with a timestamp.
4. That the approval came from a literal operator response — not `auto_advance`, not yolo, not
   silence, not self-issued.
5. That this approval is recorded **separately** from the other gate's — the two were not collapsed.
6. That execution continues only on an explicit "approved".

### Anti-Patterns to Avoid

- **`gate="blocking"` anywhere in a plan that merges or tags** — PITFALLS' literal warning sign.
- **`checkpoint:decision` for either gate** — auto-selected at both layers regardless of gate value.
- **Collapsing the two gates into one approval** — D-08 requires independence.
- **`--squash` / `--rebase` / any force push** — dozens of SUMMARY files across Phases 35-43 cite
  SHAs by value; rewriting history reachable from published tags breaks them.
- **`git push --tags`** — would publish the milestone tags `v1.1…v1.6` and stale local package tags.
  Push the one tag **by name**.
- **Tagging branch HEAD pre-merge** — D-09 requires the re-resolved post-merge SHA.
- **Reading the `release.yml` run report as post-publish proof** — D-12 requires installing the
  public wheel outside the repo.
- **Asserting checks by absence of `fail`** — D-11 requires a positive count of 15.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Version consistency across sites | A bespoke bump script | Edit 4 sites + `uv lock`; let `test_version_metadata.py` + `release.yml`'s awk gate assert | Both assertions already exist and run in CI |
| Export-surface correctness | Manual reading of `__all__` | `tools/check_surface_types.py` | Enforced in CI lint; counts names |
| Wheel/sdist build | `python -m build` / manual `twine` | `release.yml`'s `uv build --package` | Seventh unmodified reuse; editing it is out of scope (D-02) |
| CI check status | Parsing HTML / bespoke polling | `gh pr checks <n>` piped through `awk`/`wc -l` | Precedent-proven; positive counting |
| Merge-commit SHA | Copying a SHA from a SUMMARY | `git fetch origin main --tags && git rev-parse origin/main` | D-09; the recorded value is the cross-check, not the source |
| Human authorization on irreversible ops | Prose in `<action>` alone | `checkpoint:human-action` + `gate="blocking-human"` + prose | Prose alone failed 4× |

**Key insight:** every mechanical assertion this phase needs already exists as a repo tool or a CI
job. The only genuinely new authoring work is the changelog prose, the two migration tables, and the
two checkpoint plans — and the checkpoints are where all the historical risk lives.

---

## Common Pitfalls

### Pitfall 1: The gate collapses — fifth occurrence
**What goes wrong:** A checkpoint authored as `gate="blocking"`, or as `checkpoint:decision` with any
gate, or suppressed entirely by `human_verify_mode: end-of-phase`, is auto-approved and the
irreversible merge/tag proceeds unattended.
**Why it happens:** Four prior occurrences (`40-01:305` decision/blocking, `40-02:259`
human-verify/blocking, `40-03:172` human-verify/blocking, plus Phase 34's two per `PROJECT.md:71`)
were caught only by manual orchestrator override. The follow-up to fix the template was never done.
**How to avoid:** Use `checkpoint:human-action` + `gate="blocking-human"` (see § Gate Authoring
Semantics). Post-hoc verify: `bash -c 'grep -n "gate=\"blocking\"" .planning/phases/44-*/44-0*-PLAN.md'`
must return **zero** rows (note: `blocking-human` will not match this pattern because of the closing
quote), and `grep -c 'gate="blocking-human"'` must return exactly the number of checkpoint tasks.
**Warning signs:** `gate="blocking"` in a merging/tagging plan; an `autonomous: true` plan containing
a merge or tag; a plan file with zero `checkpoint:` tasks in waves 2-3.
**Recovery cost:** HIGH / irreversible — a published GitHub Release cannot be cleanly unpublished.

### Pitfall 2: `uv.lock` not refreshed → CI lint fails on step 1
**What goes wrong:** `uv.lock:488` still reads `version = "0.6.0"`; `uv lock --check`
(`ci.yml:32-33`) fails; the PR shows a red `lint` check and the 15/15 count is unreachable.
**How to avoid:** Run `uv lock` **once**, after all four version sites are bumped, before pushing
(D-02). Verify: `bash -c 'grep -A1 "name = \"market-data-client\"" uv.lock | grep "0.7.0"'`.
**Warning signs:** `uv lock --check` non-zero locally.

### Pitfall 3: Stale `dist-info` → false-red on the version-metadata test
**What goes wrong:** After bumping, `test_dunder_version_matches_installed_distribution_metadata`
(`test_version_metadata.py:52`) fails locally, and the failure looks like a real bug.
**Why it happens:** The editable install's metadata directory is literally
`.venv/lib/python3.12/site-packages/market_data_client-0.6.0.dist-info` with `Version: 0.6.0` inside
`[VERIFIED: find + grep, in-session]`. `importlib.metadata.version("market-data-client")` reads that
directory, and `uv lock` does **not** regenerate it — only `uv sync` (or a reinstall) does.
**How to avoid:** After `uv lock`, run `uv sync --all-packages --all-extras --dev` **before** running
the package tests locally. Then assert
`uv run python -c "from importlib.metadata import version; import market_data_client; assert version('market-data-client') == market_data_client.__version__ == '0.7.0'"`.
**Note:** CI is unaffected — a fresh runner regenerates the metadata from the bumped `pyproject.toml`.
This is a *local-only* false-red, which makes it more dangerous, not less: it invites a spurious
"fix".

### Pitfall 4: `<verify>` blocks fail under zsh
**What goes wrong:** Verify blocks assume bash word-splitting and fail on this machine (`Shell: zsh`).
**How to avoid:** Wrap every verify block in `bash -c '...'` (D-10). PITFALLS records this as measured
in Phase 40. Confirmed again in this session: a bare `grep --include=*.py` invocation failed with
`(eval):1: no matches found` under zsh and succeeded verbatim under `bash -c`.

### Pitfall 5: Hardcoded counts go stale between planning and execution
**What goes wrong:** A `<verify>` block asserts a literal count measured at planning time; the repo
moves; the assertion fails or, worse, passes vacuously.
**Why it happens:** Phase 40 found a `wallets-client-v*` count hardcoded at 2 when the real value was
1. In *this* session the pending-commit count moved from CONTEXT.md's 84 to a measured 86.
**How to avoid:** Re-derive every count in-line at execution time (D-10). The only literals safe to
hardcode are the ones the phase itself sets: the tag string `market-data-client-v0.7.0`, the target
version `0.7.0`, the CI check total `15` (structural, from `ci.yml`), and the post-fold surface count
`187`.

### Pitfall 6: The README install command left pointing at the old tag
**What goes wrong:** Ships a README whose changelog says v0.7.0 but whose install command still pins
`market-data-client-v0.6.0`.
**Why it happens:** Site 4 (`README.md:24`) contains the version **twice on one line** — once in the
tag path, once in the wheel filename. A single-substitution edit fixes one and leaves the other.
**Precedent:** Phase 34 shipped exactly this defect (README changelog v0.5.0, install command v0.4.0)
— a code-review Critical, fixed in follow-up PR #13.
**How to avoid:** After editing, assert zero survivors:
`bash -c 'grep -n "v0\.6\.0\|0\.6\.0-py3" packages/market-data-client/README.md | grep -v "^1[2-9][0-9]:"'`
must return nothing outside the historical changelog body.

### Pitfall 7: `FeedSubscription` added to `__all__` only
**What goes wrong:** `__all__` names an unbound attribute; `from market_data_client import *` raises.
**How to avoid:** Two edits — import block **and** `__all__` (see § The `FeedSubscription` Fold).
Assert the surface gate reports **187** names, up from the measured 186 baseline.

### Pitfall 8: CI cancels in-flight checks on a mid-gate push
**What goes wrong:** `ci.yml` sets `concurrency.cancel-in-progress: true`. A commit pushed while the
operator is deciding cancels the run; the 15/15 count silently becomes unreachable.
**How to avoid:** Assert `git rev-parse HEAD == git rev-parse origin/<branch>` inside the gate's
acceptance criteria (Phase 40 precedent), and push nothing between the count and the merge.

---

## Code Examples

Patterns verified against this repo's precedent plans and tooling.

### Positive check counting (D-11)
```bash
bash -c '
  set -euo pipefail
  PR=16
  TOTAL=$(gh pr checks "$PR" | wc -l | tr -d " ")
  PASS=$(gh pr checks "$PR" | awk -F"\t" "\$2==\"pass\"" | wc -l | tr -d " ")
  MDC=$(gh pr checks "$PR" | grep -c "Tests · market-data-client · py3\.1[23]")
  echo "total=$TOTAL pass=$PASS market-data-rows=$MDC"
  [ "$TOTAL" -eq 15 ] && [ "$PASS" -eq 15 ] && [ "$MDC" -eq 2 ]
'
```

### Merge, never squash / never rebase (D-08a)
```bash
bash -c 'gh pr merge 16 --merge'
```

### Re-resolve the merge SHA live and confirm two parents (D-09)
```bash
bash -c '
  set -euo pipefail
  git fetch origin main --tags
  MERGE_SHA=$(git rev-parse origin/main)
  PARENTS=$(git rev-list --parents -n1 "$MERGE_SHA" | wc -w | tr -d " ")
  echo "merge_sha=$MERGE_SHA parents_plus_self=$PARENTS"
  [ "$PARENTS" -eq 3 ]   # self + exactly two parents
'
```

### Annotated tag on the re-resolved SHA, pushed by name (D-09, D-10)
```bash
bash -c '
  set -euo pipefail
  MERGE_SHA=$(git rev-parse origin/main)
  git tag -a market-data-client-v0.7.0 "$MERGE_SHA" \
    -m "market-data-client v0.7.0 — Instrument/Segment shape correction (Phase 43)"
  [ "$(git cat-file -t market-data-client-v0.7.0)" = "tag" ]   # annotated, not lightweight
  git push origin market-data-client-v0.7.0                     # BY NAME — never --tags
'
```

### Tag-count invariance for the other five packages (D-10, criterion 5)
```bash
bash -c '
  set -euo pipefail
  for p in iol-client higyrus-client matriz-client ambito-financiero-client wallets-client; do
    printf "%-28s %s\n" "$p" "$(git tag -l "${p}-v*" | wc -l | tr -d " ")"
  done
  printf "%-28s %s\n" market-data-client "$(git tag -l "market-data-client-v*" | wc -l | tr -d " ")"
'
# Expected post-phase: 4 / 3 / 3 / 2 / 1 / 8
```

### `release.yml` non-modification by digest identity
```bash
bash -c '
  set -euo pipefail
  for ref in HEAD origin/main market-data-client-v0.6.0 market-data-client-v0.7.0; do
    printf "%-32s %s\n" "$ref" "$(git show "$ref:.github/workflows/release.yml" | shasum -a 256 | cut -d" " -f1)"
  done
'
# All four digests must be identical.
```

### Post-publish proof from the PUBLIC wheel, outside the repo (D-12)
```bash
bash -c '
  set -euo pipefail
  WORK=$(mktemp -d /tmp/mdc-verify-XXXXXX)   # outside the repo
  cd "$WORK"
  uv venv --python 3.12 .venv
  ./.venv/bin/pip install \
    "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.7.0/market_data_client-0.7.0-py3-none-any.whl"
  ./.venv/bin/python -c "
import market_data_client as m
from importlib.metadata import version
assert m.__version__ == version(\"market-data-client\") == \"0.7.0\"
from market_data_client import Instrument, Segment, FeedSubscription
s = Segment.from_api({\"segment\": \"DDA\", \"live_instruments\": 3})
assert (s.segment, s.live_instruments) == (\"DDA\", 3) and bool(s) is True
i = Instrument.from_api({\"symbol\": \"X\", \"market_id\": \"ROFX\"})
assert i.market_id == \"ROFX\" and i.marketId == \"ROFX\"   # additive alias mirrored
assert not hasattr(s, \"marketSegmentId\") and not hasattr(i, \"instrumentType\")
print(\"installed-distribution deep chain OK\")
"
'
```

### The post-hoc gate-authorship audit (ROADMAP criterion 4)
```bash
bash -c '
  set -euo pipefail
  cd .planning/phases/44-release-market-data-client-0-7-0
  echo "bad (must be 0):  $(grep -ho "gate=\"blocking\"" 44-0*-PLAN.md | wc -l | tr -d " ")"
  echo "good (must be 2): $(grep -ho "gate=\"blocking-human\"" 44-0*-PLAN.md | wc -l | tr -d " ")"
'
```

---

## Runtime State Inventory

Not a rename/refactor/migration phase in the code sense, but it does mutate published, externally
visible state. Inventory follows the same discipline.

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | **None** — no database, cache, or datastore holds the version string. Verified: no `.env`, no persisted state in this package beyond module-level singletons reset per process. | none |
| Live service config | **GitHub Releases + git tags on `origin`** — the irreversible surface. One new tag `market-data-client-v0.7.0` and one new Release. Not revertible cleanly. | Both gates guard exactly this |
| OS-registered state | **None** — no scheduler, daemon, or service registration references this package. | none |
| Secrets / env vars | `gh` token present in `~/.config/gh/hosts.yml` (auth confirmed as `sebadlf`). Never echo it, never place it in a plan, SUMMARY, or verify block. No package `.env` is touched. | none — read-only use |
| Build artifacts / installed packages | `.venv/lib/python3.12/site-packages/market_data_client-0.6.0.dist-info` embeds the old version and does **not** auto-update on a `pyproject.toml` edit. `__pycache__/*.pyc` under the package also contain `0.6.0` string literals. | `uv sync` after `uv lock` — see Pitfall 3 |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `gate="blocking"` on release checkpoints | `gate="blocking-human"` | GSD runtime added the attribute; honoured at `gsd-executor.md:316` | Necessary but **not sufficient** — see § Gate Authoring Semantics |
| Mid-flight `checkpoint:human-verify` halts | `human_verify_mode: end-of-phase` folds them into `<verify><human-check>` | GSD issue #3309 | Planner must **not** rely on human-verify for a hard barrier in this project |
| README `## Unreleased` staging section | Direct `### vX.Y.Z` insertion | Never adopted here — no README in the monorepo has one | D-03: do not introduce the pattern |
| `Segment` = `marketSegmentId`/`marketId`/`description` | `Segment` = `segment`/`live_instruments` | Phase 43 | Whole-model replacement; truthiness flips falsy→truthy on real data |
| `Instrument.marketId` as the only market id | `market_id` canonical + `marketId` additive alias | Phase 43 (D-22 precedent) | Alias mirrored in `from_api`; removal at next MAJOR |

**Deprecated/outdated:**
- `43-03-SUMMARY.md:264`'s "tres sitios de versión" — measured count is 4.
- PITFALLS' Segment truthiness direction — measured inverse.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | The orchestrator's auto-approve branch (`execute-phase.md:1059`) is reached for a `human-verify` checkpoint returned by an executor that refused to self-approve — i.e. the two layers compose as read. | Gate Authoring Semantics / FM-2 | If the orchestrator in practice surfaces such a checkpoint to the user anyway, the `human-action` recommendation is belt-and-suspenders rather than necessary — no harm either way, since `human-action` is strictly safer. |
| A2 | `market-data-client` 0.7.0 (minor, not patch) is the right bump. | Summary | Sourced from PITFALLS' debt table: *"Patch bump for SHAPE-01 → **never** — 0.7.0"*, and consistent with the 0.4.0/0.5.0/0.6.0 breaking-minor chain. Low risk. |
| A3 | The branch name follows `milestone/v1.8-<slug>`; the milestone is v1.8. | Architecture Patterns | Inferred from D-07's stated pattern and the v1.7 predecessor. Branch naming is explicitly Claude's discretion, so the risk is cosmetic. |
| A4 | The changelog table's "Antes" column should be labelled against `0.6.0 publicado`, mirroring `### v0.6.0`'s `| Antes (0.5.0 publicado) | Ahora (0.6.0) |`. | Migration Table Source | Cosmetic; wording is Claude's discretion per CONTEXT.md. |

Everything else in this document was measured in-session.

---

## Open Questions

**OQ-1 — Checkpoint type deviates from D-08's enumeration. [requires user confirmation]**
- *What we know:* D-08 mandates `gate="blocking-human"` (correct, and the ROADMAP criterion 4 grep
  depends on it) and enumerates two permitted task types: `checkpoint:decision` and
  `checkpoint:human-verify`. Measured, `checkpoint:decision` ignores the gate attribute at both
  layers, and `checkpoint:human-verify` is honoured at the executor but auto-approved at the
  orchestrator; additionally `human_verify_mode: end-of-phase` instructs the planner to suppress
  human-verify tasks entirely.
- *What's unclear:* Whether the operator prefers (a) `checkpoint:human-action gate="blocking-human"`
  — mechanically safe at both layers, satisfies criterion 4's literal in-file grep, but is a type
  outside D-08's enumeration; or (b) `checkpoint:human-verify gate="blocking-human"` — literal
  compliance with D-08, but relies on an orchestrator override for the second layer, which is
  precisely the accident-of-prosa this phase exists to eliminate.
- *Recommendation:* **(a)**. D-08's *intent* — "no auto-approval of an irreversible operation" — is
  served only by (a). D-08's *letter* on the type list appears to have been written from the Phase-40
  precedent without the two-layer measurement now available. Option (b) would make Phase 44 the fifth
  occurrence of the same class of defect while appearing compliant on a grep.
- *Fallback if (b) is chosen:* keep the Phase-40 orchestrator-override prose verbatim and add an
  explicit `must_haves.prohibitions` line naming `execute-phase.md:1059` as the specific auto-approve
  path that must not fire.

**OQ-2 — Does an extra migration row for the `Segment` truthiness flip belong in the README?**
- *What we know:* Measured, old `Segment` on real wire was falsy and new is truthy; a consumer's
  `if seg:` silently inverts. CONTEXT.md D-04 enumerates the field rows but not this behavioural row.
  PITFALLS' SHAPE-01 checklist calls for the flip to be "called out" but states its direction
  backwards.
- *What's unclear:* Whether adding the row exceeds D-04's locked table content.
- *Recommendation:* Add it, as a row in the Segment table with the measured direction. D-04 locks the
  *source* of the field rows and the two-table split; it does not forbid documenting a measured
  consumer-visible consequence of those same rows. Omitting it would ship a migration table that a
  consumer can follow field-by-field and still break silently — the exact failure criterion 3 targets.

**OQ-3 — README non-changelog `0.6.0` survivors beyond lines 15 and 24.**
- *What we know:* The in-session census found exactly two outside the changelog body, matching D-01.
- *What's unclear:* Whether the prose body of the new `### v0.7.0` section will itself mention
  `0.6.0` (it should, as the "Antes" column label), which would make a naive "zero survivors" grep
  fail.
- *Recommendation:* Scope the survivor assertion to lines above the `## Changelog` heading, e.g.
  `sed -n '1,/^## Changelog/p'`, rather than to the whole file.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| `uv` | lock, sync, build, run | ✓ | 0.9.0 (per CLAUDE.md; workspace synced) | — |
| Python 3.12 | venv, tests, throwaway install | ✓ | 3.12.11 (`.venv`) | 3.13 also in CI matrix |
| `git` | branch, tag, merge SHA resolution | ✓ | system | — |
| `gh` | PR create, checks, merge | ✓ | authenticated as `sebadlf`, https | — |
| `bash` | all `<verify>` blocks (D-10) | ✓ | system (`/bin/bash`) | none — zsh is NOT a fallback |
| GitHub Actions | `ci.yml`, `release.yml` | ✓ | remote | — |
| Network to `github.com` | PR, tag push, wheel download | ✓ | — | — |
| `shasum` | `release.yml` digest identity check | ✓ | macOS system | `sha256sum` on Linux |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

---

## Validation Architecture

`workflow.nyquist_validation` is `true` `[VERIFIED: .planning/config.json]`.

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| Config file | root `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `bash -c 'uv run pytest packages/market-data-client -q'` |
| Full suite command | `bash -c 'uv run pytest packages/market-data-client && uv run ruff check . && uv run ruff format --check . && uv run mypy packages/market-data-client && uv run python tools/check_surface_types.py && uv run python tools/check_uniform_structure.py && uv run python tools/surface_parity.py && uv run python tools/check_decode_intactness.py && uv lock --check'` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| PUB-01 | `__version__` == pyproject == installed dist == `0.7.0` | unit | `uv run pytest packages/market-data-client/tests/test_version_metadata.py -x` | ✅ (3 tests) |
| PUB-01 | `FeedSubscription` exported from package root | smoke | `uv run python -c "from market_data_client import FeedSubscription"` | ✅ inline |
| PUB-01 | Export surface clean, 187 names | gate | `uv run python tools/check_surface_types.py` | ✅ tool |
| PUB-01 | `uv.lock` in sync with bumped pyproject | gate | `uv lock --check` | ✅ CI step |
| PUB-01 | README carries `### v0.7.0` + both migration tables | doc | `bash -c 'grep -c "^### v0.7.0" packages/market-data-client/README.md'` == 1 | ✅ inline |
| PUB-01 | No stale `0.6.0` in README install commands | doc | scoped grep above `## Changelog` (see OQ-3) | ✅ inline |
| PUB-01 | 15/15 CI checks pass, counted positively | integration | `gh pr checks` pipeline (§ Code Examples) | ✅ inline |
| PUB-01 | Tag annotated, on two-parent merge commit | integration | `git cat-file -t` + `git rev-list --parents -n1` | ✅ inline |
| PUB-01 | Release carries wheel **and** sdist by exact filename | integration | `gh release view market-data-client-v0.7.0 --json assets` | ✅ inline |
| PUB-01 | Public wheel installs and deep chain runs outside repo | e2e | throwaway-venv script (§ Code Examples) | ✅ inline |
| PUB-01 | Other five packages' tag counts unchanged | integration | tag-count loop (§ Code Examples) | ✅ inline |
| PUB-01 | Both gates authored `blocking-human`, zero `blocking` | meta | gate-authorship audit (§ Code Examples) | ✅ inline |
| PUB-01 | `release.yml` byte-identical across refs | integration | digest identity (§ Code Examples) | ✅ inline |

### Sampling Rate

- **Per task commit:** `bash -c 'uv run pytest packages/market-data-client -q'`
- **Per wave merge:** full suite command above (all four gates + lock check + mypy + ruff)
- **Phase gate:** all 15 CI checks green on PR #16, counted positively, before checkpoint (a)

### Wave 0 Gaps

None — existing test infrastructure covers every phase requirement. `test_version_metadata.py`
already asserts the three-way version identity, the four repo gate tools already exist and are green
at baseline, and every remaining criterion is an inline shell assertion against git/gh state rather
than new test code. No new test file, fixture, or framework install is required.

---

## Security Domain

`workflow.security_enforcement` is `true`, `security_asvs_level: 1` `[VERIFIED: .planning/config.json]`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | No auth code changes; the package's Auth0 client-credentials flow is untouched |
| V3 Session Management | no | No session surface in this phase |
| V4 Access Control | **yes** (operational) | The two human gates ARE the access control on irreversible public operations. `main` has **no branch protection**, so the checkpoint is the only gate |
| V5 Input Validation | no | No input-handling code changes; `SafeModel`/`_decode` untouched |
| V6 Cryptography | no | No crypto. `shasum -a 256` is used for file-identity comparison only, not as a security control |
| V7 Error Handling & Logging | **yes** (narrow) | The `gh` token must never be echoed into a plan, SUMMARY, verify-block output, or commit message |
| V14 Configuration | **yes** | `release.yml` and `ci.yml` must remain unmodified; a workflow edit inside a release PR is a supply-chain change |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Unauthorized publish of an artifact consumers auto-pin (`~=`) | Elevation of Privilege | Two independent `blocking-human` gates; annotated tag only on a re-resolved merge SHA |
| Credential leakage via echoed `gh` token or `git remote -v` output | Information Disclosure | Never echo tokens; `gh auth status` only (it masks). Precedent wording in Phase 40 `user_setup` |
| Workflow-file tampering smuggled inside a release PR | Tampering | sha256 digest identity of `release.yml` across HEAD / `origin/main` / prior tags / new tag |
| History rewrite invalidating SHAs cited across Phases 35-43 | Tampering / Repudiation | `--merge` only; `--squash`/`--rebase`/force-push prohibited in `must_haves.prohibitions` |
| Accidental publication of unrelated tags (`v1.1…v1.6`, stale local tags) | Information Disclosure | Push the single tag **by name**; `git push --tags` prohibited |
| Committing a `.env` or credential alongside the release | Information Disclosure | CLAUDE.md constraint; `git status` clean-tree assertion before push |

---

## Project Constraints (from CLAUDE.md)

Directives extracted from `./CLAUDE.md` that bind this phase:

- **Tech stack is fixed:** Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict. Any change
  must pass the existing CI. This phase adds no dependency.
- **No cross-package shared code.** This phase touches only `packages/market-data-client/` plus
  `uv.lock` at the root. It must not introduce any dependency between packages.
- **Dual sync/async mirroring:** any logic fix must be mirrored in `client.py` and `aio.py`. *Not
  triggered here* — Phase 44 changes no client logic; Phase 43 already mirrored the model change.
- **Credentials live in per-package `.env`; never commit `.env`, never expose credentials in logs,
  reports, or tests.** Binding on every gate briefing and every SUMMARY.
- **Every module starts with `from __future__ import annotations`** — mandatory and uniform. The
  `__init__.py` edit adds only names to an existing import block and `__all__`; it must not disturb
  this line.
- **Ruff:** line-length 100, double quotes, 4-space indent, `target-version = "py312"`. The
  `__init__.py` import list and `__all__` are alphabetically ordered — insert `FeedSubscription` in
  the correct alphabetical slot (after `FeedPipeline`) or `ruff check` (rule `I`) will fail.
- **mypy strict** across `src` and per-package tests.
- **GSD Workflow Enforcement:** file changes go through a GSD command; this phase runs under
  `/gsd-execute-phase`.
- **Naming:** models are `PascalCase`; `__all__` is an explicit list; `__version__` is a string.

---

## Sources

### Primary (HIGH confidence — measured in-session against this repo/runtime)
- `.claude/agents/gsd-executor.md:198-333` — auto-mode checkpoint behaviour, `blocking-human` rule
- `.claude/gsd-core/workflows/execute-phase.md:1049-1080` — orchestrator checkpoint handling
- `.claude/gsd-core/references/checkpoints.md:11` — auto-mode bypass summary
- `.claude/gsd-core/references/planner-human-verify-mode.md` — `end-of-phase` suppression
- `.claude/gsd-core/references/gates.md` — gate taxonomy
- `.planning/config.json` — `auto_advance`, `_auto_chain_active`, `mode`, `human_verify_mode`
- `gsd-tools query check auto-mode --pick active` → `true`
- `.github/workflows/release.yml`, `.github/workflows/ci.yml`
- `packages/market-data-client/{pyproject.toml, README.md, src/market_data_client/{__init__.py, models.py}, tests/test_version_metadata.py}`
- `uv.lock:487-489`
- `git tag -l`, `git rev-list --count`, `git branch --show-current`, `gh auth status`, `gh pr list`
- `tools/check_surface_types.py`, `check_uniform_structure.py`, `surface_parity.py` — executed
- Live Python execution of `Segment`/`OldSegment` truthiness under `uv run python`
- `.venv/lib/python3.12/site-packages/market_data_client-0.6.0.dist-info/METADATA`

### Secondary (HIGH confidence — project artifacts read verbatim)
- `.planning/phases/44-.../44-CONTEXT.md`
- `.planning/phases/43-.../43-DISPOSITION.md` §§ 1.1, 1.2, 1.3
- `.planning/phases/43-.../43-03-SUMMARY.md`
- `.planning/milestones/v1.7-phases/40-releases-breaking-coordinados/40-0{1,2,3}-PLAN.md`
- `.planning/research/PITFALLS.md` — Pitfall 14, debt table, "Looks Done But Isn't" § Release,
  Integration Gotchas, Recovery Strategies
- `./CLAUDE.md`

### Tertiary (LOW confidence)
- None. No external web source was needed or consulted; this phase's domain is entirely internal to
  this repository and this GSD runtime installation.

---

## Metadata

**Confidence breakdown:**
- Gate authoring semantics: **HIGH** — read directly from the installed agent and workflow
  definitions; the decisive asymmetry (`blocking-human` absent from `workflows/`) confirmed by an
  exhaustive grep returning exactly four hits, none in the orchestrator.
- Version sites: **HIGH** — exhaustive in-repo census; D-01's count of 4 reproduced exactly.
- Release/CI mechanics: **HIGH** — both workflow files read in full; the 15-check arithmetic derived
  from the matrix definition rather than from a remembered run.
- Migration table content: **HIGH** — source disposition tables read verbatim; shipped model shapes
  re-read from `models.py`; the truthiness flip executed rather than reasoned.
- Baselines (tags, surface count, gates): **HIGH** — all executed in-session.
- `FeedSubscription` fold scope: **HIGH** — the two-line correction to D-05 measured directly.
- Pitfalls: **HIGH** — each traced to a measured artifact or an executed command; the local
  `dist-info` staleness confirmed by reading the on-disk metadata directory name and contents.

**Research date:** 2026-09-01
**Valid until:** 2026-09-15 — but the volatile facts (pending-commit count, PR number, tag counts,
surface-name count) must be **re-derived at execution time** per D-10 regardless of this date. The
commit count already moved 84 → 86 between CONTEXT.md and this research.
