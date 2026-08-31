# Phase 41: Validación Nyquist retroactiva de v1.7 - Research

**Researched:** 2026-08-31
**Domain:** Retroactive validation auditing of GSD `VALIDATION.md` artifacts (documentation + measurement, no product source changes)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Artifact shape & write target

- **D-01:** El resultado se escribe **in place** en los 5 `{N}-VALIDATION.md` existentes, archivados
  bajo `.planning/milestones/v1.7-phases/{35,36,37,38,39}-*/` — se les añade una sección fechada
  `## Validation Audit {date}`, no se crean cinco archivos `41-*` nuevos ni un documento
  consolidado como fuente de verdad. Un rollup consolidado, si se produce, es un índice secundario
  bajo `.planning/phases/41-*/`, no el artefacto autoritativo.
- **D-02:** El SHA declarado en cada artefacto es el commit del tag `v1.7`
  (`37a83fe693a303a551f4374f48fe6fc5521804f7`), acompañado de la prueba de que el árbol auditado
  sigue intacto: `git diff v1.7 HEAD -- . ':(exclude).planning'` está vacío (verificado en esta
  sesión — los tres commits desde el tag tocan sólo `.planning/`). Si por algún motivo se declara
  también el HEAD de la sesión de auditoría, se declaran **ambos**, nunca sólo HEAD sin la prueba
  de identidad del árbol.

#### Unit of disposition (denominador del criterio 2)

- **D-03:** El denominador de "cero filas sin disponer" (criterio 2) son las filas de la **Per-Task
  Verification Map** más las **Manual-Only Verifications** de cada `{N}-VALIDATION.md` — medido 51
  filas totales entre las 5 fases — **no** los 25 criterios de éxito ya cerrados en v1.7
  `ROADMAP.md`, y no una unión de ambos.
- **D-04:** Se espera que `VERIFIED-NOW` domine sobre `VERIFIED-HISTORICALLY`: los 15 archivos de
  test citados en los 4 mapas poblados (36-39) ya existen en disco y son re-ejecutables — las
  celdas `⬜`/`❌` son bookkeeping stale de plan-time, no gaps reales. Cada fila `VERIFIED-NOW` debe
  citar el comando **y su output real de esta sesión** — nunca flippear una celda sin re-ejecutar.
  `VERIFIED-HISTORICALLY` queda reservado para evidencia de artefacto único e irrepetible (p.ej. el
  doc-review de `38-CENSUS.md`). `NOT-VERIFIABLE-RETROACTIVELY` para filas que dependen de red en
  vivo o de un checkpoint humano que no se puede re-derivar (p.ej. las 4 filas manual-only de
  Phase 39).
- **D-05:** Phase 35 es una excepción estructural: su mapa tiene una única fila placeholder
  (`"(filled by planner)"`). Antes de disponer, sus ~14 bloques `<verify><automated>` reales deben
  reconstruirse desde `35-01..05-PLAN.md` y disponerse individualmente — nunca disponer la fila
  placeholder como si fuera la unidad completa (eso certificaría "1/1, 100%" sin decir nada).

#### Cómo se invoca `/gsd-validate-phase`

- **D-06:** El skill se invoca 5 veces (una por fase 35-39), con dos desviaciones obligatorias del
  camino stock:
  (a) en el gate de "fix gaps" **nunca** se toma la rama que spawnea `gsd-nyquist-auditor` para
  escribir tests nuevos — la auditoría es de lectura/disposición, no de reparación;
  (b) la resolución de requirements/roadmap apunta explícitamente a
  `.planning/milestones/v1.7-REQUIREMENTS.md` y `.planning/milestones/v1.7-ROADMAP.md` — **nunca**
  a los archivos raíz (`REQUIREMENTS.md`/`ROADMAP.md`), que hoy contienen el roster de v1.8
  (`NYQ-01`, `LIVE-01`, etc.) y no resuelven contra los IDs de v1.7 (`NOBJ-01`, `NOBJ-MD-01`, etc.)
  que las fases 35-39 referencian.
- **D-07:** Cada fila dispuesta como `VERIFIED-NOW`/`VERIFIED-HISTORICALLY` lleva una **cuarta
  columna** nombrando su superficie de enforcement real en CI (job + línea del `ci.yml`, o
  `NOT ENFORCED` si no corre en CI) — así es como el criterio 4 se satisface también para locks
  **pre-existentes**, no sólo para los que el auditor pudiera generar. (Medido: 52 archivos calzan
  `verification/test_*.py`; sólo 12 están en el allowlist explícito de `ci.yml`.)

#### Front-matter semantics & mechanical-closure risk

- **D-08:** "Lock" en el criterio 4 significa un **archivo de test ejecutable nuevo** que el
  auditor escribe a disco (el sentido ya establecido en el repo, p.ej. "AST lock" en
  `39-VALIDATION.md`) — no el propio `{N}-VALIDATION.md` ni el flag de front-matter. El conteo
  esperado es **cero**: el criterio 4 es una cláusula de contingencia, no un entregable esperado.
  Si de todas formas se escribe uno, queda declarado inerte por escrito con su enrolamiento en CI
  ruteado explícitamente a la Phase 45 (precondición ya registrada en `REQUIREMENTS.md`).
- **D-09:** El estado final esperado en front-matter es `status: draft → validated` en los 5, pero
  `nyquist_compliant` se queda en **`false`** en efectivamente los 5 (estado PARTIAL, no
  compliant) — Phase 39 sola tiene 4 filas manual-only no reproducibles (corridas en vivo contra
  red real). Ningún `nyquist_compliant` pasa a `true` salvo donde la disposición sea `VERIFIED-NOW`
  re-ejecutada en esta sesión (y aun así, sólo si **todas** las filas de esa fase cierran limpias,
  cosa que no se espera para ninguna de las 5).
- **D-10 (riesgo a vigilar — no una decisión de implementación, una restricción de calidad):**
  El riesgo principal es "staleness laundering" — flippear mecánicamente las ~45 casillas `⬜`
  stale a `✅` en un commit sin comando/output re-ejecutado. Contramedida: toda fila `VERIFIED-NOW`
  cita comando + output real de esta sesión. Además, la propia Phase 41 recibirá su propio
  `41-VALIDATION.md` auto-sembrado (`nyquist_validation: true` en `config.json`) — ese tampoco se
  flippea mecánicamente; se disponen sus filas con la misma vara que las cinco que audita.

### Claude's Discretion

- Formato exacto de la sección `## Validation Audit {date}` dentro de cada VALIDATION.md (tabla vs.
  prosa) — mientras cumpla D-01/D-07/D-09, queda a discreción del planner/executor.
- Si producir o no un rollup consolidado bajo `.planning/phases/41-*/` como índice de lectura
  rápida — no es requisito, es una conveniencia opcional (D-01).

### Deferred Ideas (OUT OF SCOPE)

- Reparar o regenerar tests que las celdas `⬜`/`❌` marcan como faltantes cuando en realidad ya
  existen (D-04) — no es trabajo de Phase 41, sólo se corrige el bookkeeping stale del mapa.
- Cualquier fix de código motivado por lo que la auditoría revele — fuera de esta fase por
  definición (Phase 41 no toca fuente).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NYQ-01 | Correr `/gsd-validate-phase` retroactivo sobre las 5 fases de v1.7 (35-39) que nunca lo ejecutaron, produciendo una disposición de 3 vías por hallazgo (`VERIFIED-NOW` / `VERIFIED-HISTORICALLY` / `NOT-VERIFIABLE-RETROACTIVELY`) — nunca un flip mecánico de `nyquist_compliant` a `true` | § Row Inventory (exact denominator, per-phase), § Re-Execution Results (all 45 automated rows re-run this session, 2 stale commands found), § Disposition Decision Rules, § CI Enforcement Map (D-07 fourth column), § Common Pitfalls 1-7, § Workflow Deviations Required |
</phase_requirements>

## Summary

This phase is **not** a code phase and not a research-heavy phase in the usual sense: every input is
local, readable, and measurable on disk. The productive research here was **measurement**, and it
produced four results that materially change how the phase should be planned.

**First, the denominator is not 51.** D-03 correctly measures 51 rows *as declared*, but D-05
requires Phase 35's single placeholder row to be expanded into its real verify blocks. Those blocks
were counted this session: `35-01..05-PLAN.md` contain **12** `<task>` elements, each with exactly
one `<verify><automated>` — not "~14". The post-reconstruction denominator is therefore
**62 rows** (13 + 11 + 14 + 9 + 15). The plan must state 62 and show the arithmetic, or criterion 2's
"el conteo por disposición cierra contra el total" cannot be checked.

**Second, D-04's expectation holds, and the measurement is stronger than expected.** All 23 distinct
test files / gate scripts cited across the 4 populated maps exist on disk, and every one of the 45
automated rows was re-executed in this session. All pass. But **two rows carry stale `-k` selectors
that select zero tests** (`37-04b -k alias_surfaces` → 74 deselected; `39-01-03 -k allowlist` → 9
deselected). pytest returns exit code **5** ("no tests were collected") for both — a chain that reads
as "no failures" to a careless eye. In both cases the *behavior* is genuinely covered, by tests under
different names; the *command in the map* is wrong. That is a bookkeeping correction (in scope per
D-04), not a coverage gap.

**Third, Phase 35 is harder than "reconstruct 12 rows".** Three of the 12 reconstructed commands are
**not re-runnable as written**: `35-01` Task 1 is a TDD RED-step assertion (`... && ! uv run pytest
-k "falsy_when_empty or ..."`) that inverts against the now-GREEN tree — re-running it today *fails
by design*; and `35-02` Tasks 1 and 2 assert against
`.planning/phases/35-.../35-RETIRED-TRIPLES.md`, a path the milestone archive move invalidated.
Those three need explicit dispositions (`VERIFIED-HISTORICALLY` for the RED step; `VERIFIED-NOW`
with a path-corrected command for the two artifact assertions) or the audit will report false red.

**Fourth, the stock workflow actively fights criterion 3.** The project-local
`.claude/gsd-core/workflows/validate-phase.md` — which wins over the user-level copy per the skill's
`<execution_context>` — contains in §3: *"No gaps → skip to Step 6, set `nyquist_compliant: true`."*
Since the measurement shows effectively zero real gaps, running the skill unmodified would flip all
five flags mechanically. That is the exact failure criterion 3 forbids. This is a **third mandatory
deviation** alongside D-06(a) and D-06(b), and it is the single most important thing the plan must
encode. The same project-local copy also **lacks** the `**set status: validated**` instruction that
the user-level copy carries, so D-09's `draft → validated` transition must be an explicit plan task,
not an assumed workflow side effect.

**Primary recommendation:** Plan five sequential per-phase audit tasks (35 → 39) plus one arithmetic
close-out task, each following the `09-VALIDATION.md` precedent (§ Architecture Patterns, Pattern 1)
— a `## Validation Audit 2026-08-31` section carrying a per-row 4-column disposition table
(row · disposition · evidence · CI enforcement surface). Drive the audit **by hand against the
frozen tree**, using `/gsd-validate-phase {N}` only as a scaffold whose §3 auto-compliance branch and
§5 auditor-spawn branch are both explicitly disabled in the plan text.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Declaring which rows exist (the denominator) | Artifact tier — the 5 `{N}-VALIDATION.md` map/manual-only tables + `35-0*-PLAN.md` verify blocks | — | Criterion 2's denominator is defined by D-03/D-05 as the artifact's own rows; no other tier may add or remove rows |
| Producing `VERIFIED-NOW` evidence | Measurement tier — `uv run pytest` / `uv run mypy` / `uv run ruff` / `tools/check_*.py` run locally against the frozen tree | Artifact tier (transcribes output) | D-04 requires command + *this session's* output; only local execution can produce it |
| Producing `VERIFIED-HISTORICALLY` evidence | Artifact tier — `{N}-VERIFICATION.md`, `{N}-SUMMARY.md`, `{N}-CENSUS.md`, `.planning/verification/run-evidence/*.json` | Git tier (commit SHAs) | Irreproducible events already left dated artifacts on disk; the audit cites them, never re-derives them |
| Naming the enforcement surface (D-07 col. 4) | CI tier — `.github/workflows/ci.yml` jobs `lint`/`typecheck`/`test` | — | Whether a lock actually runs is a property of ci.yml, invisible from a local green (Pitfall 5) |
| Proving tree freshness (criterion 1) | Git tier — `git diff v1.7 HEAD -- . ':(exclude).planning'` | — | Attribution validity is a git property, not an artifact claim |
| Deciding front-matter end state | Artifact tier — front-matter of each `{N}-VALIDATION.md` | — | D-09; must NOT be delegated to the workflow's §3 auto-branch |
| Scope containment (criterion 5) | Artifact tier — `REQUIREMENTS.md § Out of Scope` row | — | `NYQUIST-32-33` is a row in that table; containment is proven by its bytes being unchanged |

## Project Constraints (from CLAUDE.md)

These are extracted from `./CLAUDE.md` and carry the same authority as CONTEXT.md's locked decisions.

| Directive | Applies to Phase 41? | How the plan must honor it |
|-----------|---------------------|----------------------------|
| **GSD Workflow Enforcement** — no direct repo edits outside a GSD workflow | YES | All edits go through `/gsd-execute-phase 41`; the `## Validation Audit` sections are written by plan tasks, not ad hoc |
| Tech stack Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict; every extension/fix must pass existing CI | Partially | Phase 41 writes **no Python**. If D-08's contingency fires and a lock file is written, it must be `snake_case` `test_*.py`, `from __future__ import annotations` first line, ruff-clean at 100 cols, mypy-strict-clean |
| Dual sync/async mirroring for any logic fix | NO | Phase 41 touches no `client.py`/`aio.py`. Any finding that would require a mirror is out of scope (Deferred Ideas) |
| Credentials live in per-package `.env`; never commit `.env`, never expose credentials in logs, reports or tests | **YES — critical** | Every re-executed command's output gets transcribed into a committed `.md`. Transcripts MUST be trimmed to summary lines (`N passed in Xs`), never full verbose output that could carry a host, token, or account id |
| Live external dependencies vary by market hours / rate limits | YES (as a constraint on what is verifiable) | No command in this phase may touch the network. Rows whose original evidence was network-bound get `VERIFIED-HISTORICALLY` or `NOT-VERIFIABLE-RETROACTIVELY`, never a fresh live run |
| No shared code between packages (by design) | N/A | — |

**Project skills checked:** `.claude/skills/` contains `spike-findings-market-libs` (Phase 10 matriz
TokenStore concurrency primitive + refresh policy) and `spike-findings-codegen-market-libs`
(SPIKE-005 codegen NO-GO). Both are **source-implementation blueprints** with no bearing on a
documentation-only audit phase. `senior-prompt-engineer` is likewise unrelated. No skill rules apply.
[VERIFIED: read `.claude/skills/*/SKILL.md` this session]

## Standard Stack

This phase installs nothing. The "stack" is the set of already-present tools the audit re-executes.

### Core

| Tool | Version measured | Purpose | Why standard |
|------|------------------|---------|--------------|
| `uv` | 0.11.3 | Runs every audited command in the locked workspace env | Project's only supported runner; `--frozen` guarantees the audit runs against `uv.lock` as shipped |
| `pytest` | 9.0.3 | Re-executes all 45 automated rows | Every automated row in all 5 maps is a pytest invocation or a `tools/` script |
| `mypy` | 1.20.2 (strict) | Rows `36-01-02`, `37-xx (SC-3)`, `38-03-01`, and 6 of the 12 Phase-35 rows | Static rows are re-runnable and cheap |
| `ruff` | 0.15.12 | Embedded in 6 of the 12 Phase-35 verify chains | Same |
| `git` | 2.39.5 | Tree-freshness proof (criterion 1), historical SHAs for `VERIFIED-HISTORICALLY` | Only source of truth for attribution |
| `gsd-tools.cjs` | project-local `.claude/gsd-core/bin/` | `init.phase-op {N}`, `query commit` | Resolves archived phase dirs correctly (verified below) |

[VERIFIED: all versions measured via `--version` this session]

### Supporting

| Artifact | Purpose | When to use |
|----------|---------|-------------|
| `.planning/milestones/v1.7-phases/{N}-*/{N}-VERIFICATION.md` | Independent, dated re-derivation of each phase's ROADMAP success criteria | Primary source for `VERIFIED-HISTORICALLY` |
| `.planning/verification/run-evidence/{pkg}.json` (4 files, 2026-08-29) | Live-run envelopes with `probes_executed` counts | Evidence for Phase 39's live-run manual rows |
| `.planning/milestones/v1.7-phases/39-*/39-CENSUS.md`, `38-*/38-CENSUS.md` | Per-cell provenance censuses | Evidence for the two census/doc-review manual rows |
| `.planning/milestones/v1.1-phases/09-deferred-bug-fixes/09-VALIDATION.md` | **The in-repo format precedent** for a retroactive audit section | Copy its shape (see Pattern 1) |
| `.planning/research/PITFALLS.md` §§ Pitfall 4, 5, 7 | Project's own pre-written analysis of this exact phase | Read before planning; it already locks the 3-disposition table and the enforcement column |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-driven audit with `/gsd-validate-phase` as scaffold | Running `/gsd-validate-phase {N}` verbatim ×5 | **Rejected.** Project-local §3 auto-sets `nyquist_compliant: true` on zero gaps — a direct criterion-3 violation. See § Workflow Deviations Required |
| In-place edit of the 5 archived files (D-01) | Five new `41-{N}-AUDIT.md` files | Locked out by D-01 |
| Per-row 4-column disposition table (D-07) | Stock `## Validation Audit` metric-count block only (workflow §6) | Stock block reports *counts*, not *per-row dispositions*; criterion 2 requires per-row. Use both: metric block + disposition table |

**Installation:** none — no package is added, removed, or upgraded by this phase.

## Package Legitimacy Audit

**Not applicable.** Phase 41 installs zero external packages. `uv.lock` is not touched; no
`pyproject.toml` dependency changes; no `npm`/`pip`/`cargo` invocation appears in any planned task.

- Packages removed due to `[SLOP]` verdict: **none** (no packages evaluated)
- Packages flagged as suspicious `[SUS]`: **none**

If the D-08 contingency fires and a new lock test file is authored, it may import only modules
already in `uv.lock` (`pytest`, stdlib `ast`/`pathlib`). Any new third-party import would itself be a
scope violation and must be refused.

## Architecture Patterns

### System Architecture Diagram

```
                            ┌───────────────────────────────┐
      criterion 1 gate ───► │ git: tag v1.7 = 37a83fe…       │
                            │ git diff v1.7 HEAD             │
                            │   -- . ':(exclude).planning'   │
                            │        must be EMPTY           │
                            └───────────┬───────────────────┘
                                        │ (frozen tree proven)
                                        ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │                     ROW INVENTORY (denominator = 62)                 │
  │                                                                      │
  │  35-VALIDATION.md ──┐   [1 placeholder row]                          │
  │                     └──► reconstruct from 35-01..05-PLAN.md          │
  │                          12 <task>/<verify><automated> ──► 12 rows   │
  │                          + 1 manual-only row            = 13         │
  │  36-VALIDATION.md ──────► 11 map + 0 manual             = 11         │
  │  37-VALIDATION.md ──────► 14 map + 0 manual             = 14         │
  │  38-VALIDATION.md ──────►  8 map + 1 manual             =  9         │
  │  39-VALIDATION.md ──────► 11 map + 4 manual             = 15         │
  └────────────────────────────────┬─────────────────────────────────────┘
                                   │ each row routed by ONE rule
             ┌─────────────────────┼──────────────────────┐
             ▼                     ▼                      ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐
   │  VERIFIED-NOW    │  │ VERIFIED-        │  │ NOT-VERIFIABLE-        │
   │                  │  │   HISTORICALLY   │  │   RETROACTIVELY        │
   │ re-run command   │  │ cite dated       │  │ name why; no ✅;       │
   │ capture output   │  │ artifact + SHA   │  │ no grade               │
   │ (non-zero        │  │                  │  │                        │
   │  selected count) │  │ VERIFICATION.md  │  │                        │
   │                  │  │ SUMMARY.md       │  │                        │
   │ pytest/mypy/ruff │  │ CENSUS.md        │  │                        │
   │ tools/check_*.py │  │ run-evidence/*.js│  │                        │
   └────────┬─────────┘  └────────┬─────────┘  └───────────┬────────────┘
            └─────────────────────┼────────────────────────┘
                                  ▼
              ┌────────────────────────────────────────────┐
              │  D-07 4th column: CI ENFORCEMENT SURFACE   │
              │  ci.yml job + line  |  or  NOT ENFORCED    │
              └────────────────────┬───────────────────────┘
                                   ▼
              ┌────────────────────────────────────────────┐
              │  WRITE IN PLACE (D-01)                     │
              │  ## Validation Audit 2026-08-31            │
              │  appended to each of the 5 archived        │
              │  {N}-VALIDATION.md files                   │
              │  + front-matter: status draft→validated    │
              │  + nyquist_compliant: evidence-driven only │
              └────────────────────┬───────────────────────┘
                                   ▼
              ┌────────────────────────────────────────────┐
              │  CLOSE-OUT: sum(dispositions) == 62         │
              │  criterion 5: NYQUIST-32-33 row byte-intact │
              └────────────────────────────────────────────┘
```

### Recommended Artifact Structure

```
.planning/milestones/v1.7-phases/
├── 35-fundaci-n-null-object-bool-pol-tica-del-walker/
│   └── 35-VALIDATION.md          # EDIT IN PLACE: map rebuilt (12 rows) + audit section
├── 36-market-data-client-.../
│   └── 36-VALIDATION.md          # EDIT IN PLACE: 11 rows disposed + audit section
├── 37-matriz-client-.../
│   └── 37-VALIDATION.md          # EDIT IN PLACE: 14 rows (1 command re-pointed)
├── 38-iol-client-.../
│   └── 38-VALIDATION.md          # EDIT IN PLACE: 9 rows disposed
└── 39-verificaci-n-en-vivo-.../
    └── 39-VALIDATION.md          # EDIT IN PLACE: 15 rows (1 command re-pointed)

.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/
├── 41-RESEARCH.md                # this file
├── 41-VALIDATION.md              # seeded by plan-phase from template; audited by same bar (D-10)
├── 41-0N-PLAN.md                 # plan files
└── 41-ROLLUP.md                  # OPTIONAL secondary index only (D-01) — not authoritative
```

### Pattern 1: The `09-VALIDATION.md` retroactive-audit section (the in-repo precedent)

**What:** This repo has already run exactly this operation once. `09-VALIDATION.md` carries a
`## Validation Audit 2026-06-13` section that opens by naming the mechanism and input state, gives a
metric table, then a per-requirement coverage table, then an explicit paragraph on why the
manual-only rows stay manual, then a verdict line.

**When to use:** As the skeleton for all five `## Validation Audit 2026-08-31` sections. It is the
only in-repo example of the *retroactive, zero-gap, no-subagent* path that D-06(a) mandates.

**Example (verbatim opening from the precedent):**

```markdown
<!-- Source: .planning/milestones/v1.1-phases/09-deferred-bug-fixes/09-VALIDATION.md -->
## Validation Audit 2026-06-13

Retroactive Nyquist audit run via `/gsd-validate-phase 9`. Input state A
(VALIDATION.md existed pre-audit). No subagent required (zero gaps).

| Metric | Count |
|--------|-------|
| Requirements audited | 4 (BUG-01..04) |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated to manual-only | 0 |
| Test files re-verified on disk | 5 |
| Targeted regression suite | 26 passed in 0.09s |
```

Note what it already does right and Phase 41 must keep: it records *"Test files re-verified on
disk"* and *"26 passed in 0.09s"* — re-execution evidence, not a checkbox flip. It also does **not**
rename `status` on audit (it stayed `approved`). Phase 41 diverges here only because D-09 explicitly
requires `draft → validated`.

Two other precedents exist and are weaker: `01-VALIDATION.md` (metric block + one prose gap
paragraph) and `06-VALIDATION.md` (richer — criterion table + secondary-gaps table + gaps-resolved
table + explicit "Escalations: None"). `06`'s three-table shape is the closest to what criterion 2
needs; borrow its structure and add D-07's enforcement column.

### Pattern 2: The four-column disposition row (D-07)

**What:** Every row in the audited map gets four audit columns appended (or a parallel table keyed by
Task ID, if widening the existing 10-column table is unwieldy).

**When to use:** Every one of the 62 rows. No exceptions — criterion 2 says "cero filas sin disponer".

**Example:**

```markdown
| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| 36-01-01 | VERIFIED-NOW | `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x` → `38 passed in 0.11s` | job `test`, `ci.yml:154-161` (market-data-client × py3.12/3.13) |
| 36-03-02 | VERIFIED-NOW | `uv run python tools/check_decode_intactness.py` → exit 0 | job `lint`, `ci.yml:55` |
| 38-05-01 | VERIFIED-HISTORICALLY | `38-VERIFICATION.md` front-matter `human_verification[0].confirmed: 2026-08-29T22:04:57Z`; census read recorded in the same file | NOT ENFORCED (doc-review by nature) |
| 39-03-02 | VERIFIED-HISTORICALLY | `39-CENSUS.md` exists at `…/39-verificaci-n-.../39-CENSUS.md`, cited by `39-VERIFICATION.md` truth #8 | NOT ENFORCED |
```

### Pattern 3: Re-pointing a stale command instead of declaring a gap

**What:** When a map row's `Automated Command` selects zero tests but the *behavior* is covered by a
differently-named test, correct the command in the map, re-run the corrected command, and dispose
`VERIFIED-NOW` — recording both the old and the new command.

**When to use:** Exactly twice, at rows `37-04b` and `39-01-03` (both measured this session). Do not
generalize: any *third* zero-select row found during execution is a real finding and must be
escalated, not silently re-pointed.

**Example:**

```markdown
| 37 (alias_surfaces) | VERIFIED-NOW (command corrected) | Map command `pytest …/test_null_object.py -k alias_surfaces -x` selects **0 of 74** tests (pytest exit 5). Behavior is covered by `test_each_alias_returns_the_identical_object_on_a_rest_parsed_snapshot` + `…_on_a_ws_frame_parsed_snapshot`. Corrected command `uv run pytest packages/matriz-client/tests/test_null_object.py -k "rest_parsed_snapshot or ws_frame_parsed_snapshot" -x` → 2 passed | job `test`, `ci.yml:154-161` (matriz-client) |
```

### Anti-Patterns to Avoid

- **Running `/gsd-validate-phase {N}` unmodified.** Project-local workflow §3 line: *"No gaps → skip
  to Step 6, set `nyquist_compliant: true`."* With effectively zero gaps measured, this fires on all
  five and mechanically flips all five flags. Direct criterion-3 violation.
- **Spawning `gsd-nyquist-auditor`.** Its charter is *"generate a real behavioral test"* and
  *"Only create/modify: test files, fixtures, VALIDATION.md"*. Its output is new test files —
  D-08's expected count is zero. Forbidden by D-06(a).
- **Reading `nyquist_compliant: true` from `40-VALIDATION.md` as a validate-phase precedent.** It is
  not. `git log` shows commit `6e83d29 docs(phase-40): mark validation strategy nyquist-compliant
  post plan-check` — the flag was set by **plan-check**, not by validate-phase, and `40-VALIDATION.md`
  contains no `## Validation Audit` section. There is **no** validate-phase-produced artifact
  anywhere in v1.6 or v1.7.
- **Disposing Phase 35's placeholder row as a unit.** Certifies "1/1, 100%" while auditing nothing
  (D-05).
- **Transcribing full verbose pytest output into a committed `.md`.** CLAUDE.md forbids exposing
  credentials in reports; trim to summary lines.
- **Widening scope to phases 18, 25, 29, 30, 32, 33.** These *also* sit at `status: draft` /
  `nyquist_compliant: false` (measured — see § State of the Art). They are out of scope by
  criterion 5 and `REQUIREMENTS.md § Out of Scope`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Locating each archived phase's directory | Hard-coded slug strings copied by hand | `gsd_run query init.phase-op {N}` → `.phase_dir` | **Verified this session:** `init.phase-op 35` correctly returns `.planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker` with `phase_found: true`. The seam already handles archived phases; a hand-copied slug will drift |
| Committing the 5 edited files | `git add` + `git commit` by hand | `gsd_run query commit "docs(41): …" --files …` | Project convention; `commit_docs: true` in config |
| Proving the tree is frozen | Comparing file mtimes or `git status` | `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | Only pathspec-excluded diff proves *source* identity while `.planning/` legitimately churns |
| Resolving the v1.7 tag to a commit | `git rev-parse v1.7` | `git rev-parse v1.7^{commit}` | `v1.7` is an **annotated tag**: `git rev-parse v1.7` returns the *tag object* `c4dc6ea…`, not the commit `37a83fe…`. D-02's SHA is the commit — confirmed this session |
| Deciding whether a lock actually runs | Local `pytest verification/…` green | Reading `.github/workflows/ci.yml:79-92` | `testpaths` includes `verification`, CI overrides it with an explicit 12-file list. Local green proves nothing about enforcement (Pitfall 5) |
| Detecting a vacuously-green `-k` selector | Eyeballing "no failures" | Requiring a non-zero *selected/passed* count in the captured output | pytest returns exit 5 with output `74 deselected in 0.01s` — no failure line, but nothing ran |
| Re-writing the audit section format | Inventing a schema | `09-VALIDATION.md` / `06-VALIDATION.md` sections | Two dated in-repo precedents already exist |

**Key insight:** Every ingredient of this audit already exists on disk and is already correct. The
work is *disposition and arithmetic*, not construction. The two dangers are both about **what the
audit says**, not what it builds: mechanically flipping stale boxes (Pitfall 4), and certifying locks
that CI never runs (Pitfall 5). Both are addressed by evidence columns, not by new code.

## Runtime State Inventory

> Phase 41 is not a rename phase, but it *audits a tree whose planning artifacts were relocated by
> the v1.7 milestone archive*. That relocation broke on-disk paths embedded in the very verify
> commands the audit must re-run. This section captures that.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None** — no database, cache, or datastore holds validation state. All state is markdown front-matter in `.planning/`. Verified by inspecting the 30 `*-VALIDATION.md` files; there is no index, no sqlite, no `.json` state file | none |
| Live service config | **None** — the audit runs entirely offline. No n8n / Datadog / Tailscale / cloud config carries Phase-41 state. Verified: every one of the 45 automated rows is a local `pytest`/`mypy`/`ruff`/`python tools/…` invocation; zero touch the network | none |
| OS-registered state | **None** — no scheduler, launchd, pm2, or systemd registration involved | none |
| Secrets / env vars | Per-package `.env` files exist in `packages/higyrus-client/` and `packages/matriz-client/`. **They are not read by any audited command** — the network-bound rows are the 4 Phase-39 manual-only rows, which are *not* re-run. Risk is one-directional: credential leakage into a committed transcript | Trim all captured output to summary lines before writing to `.md` (CLAUDE.md security constraint) |
| Build artifacts / stale paths | **2 stale planning paths** inside `35-02-PLAN.md` verify blocks: both assert on `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md`, which **no longer exists** (archive move). File is present at `.planning/milestones/v1.7-phases/35-…/35-RETIRED-TRIPLES.md` (58 `^\| ` rows; the assertion floor is `-ge 35`, so it passes once re-pointed) | Re-point the path in the reconstructed row's command; dispose `VERIFIED-NOW`. Do **not** edit `35-02-PLAN.md` itself (historical artifact) |
| Working-tree mutation risk | Row `38-03-02` runs `uv run python verification/regen_snapshots.py`, which **writes 4 files** to `verification/snapshots/`. Measured this session: output is byte-identical, `git status --porcelain` stayed empty, `git diff --stat` empty | Safe to re-run, but the plan must re-check `git status --porcelain` is empty after it, so a dirty tree cannot silently invalidate criterion 1 |

**The canonical question, answered:** After every artifact edit is made, what still holds the *old*
truth? Only two things: (a) the two stale `.planning/phases/35-…` path literals embedded in
`35-02-PLAN.md`'s verify blocks — deliberately left as-is, since plan files are historical record;
and (b) the stale `pytest 8.3` string in the Test Infrastructure table of `35-VALIDATION.md` (actual:
pytest 9.0.3). Neither affects any disposition; both should be *named* in the audit section rather
than silently corrected.

## Row Inventory (the denominator — criterion 2)

Measured this session by direct count of table rows in each file.

| Phase | Per-Task Map rows (as declared) | Manual-Only rows | As-declared total | Post-D-05 total |
|-------|--------------------------------|------------------|-------------------|-----------------|
| 35 | 1 (placeholder `"(filled by planner)"`) | 1 (snapshot byte-identity) | 2 | **13** (12 reconstructed + 1) |
| 36 | 11 | 0 (*"All phase behaviors have automated verification"*) | 11 | 11 |
| 37 | 14 | 0 (*"None: all phase behaviors have automated verification"*) | 14 | 14 |
| 38 | 8 | 1 (`38-CENSUS.md` disposition completeness) | 9 | 9 |
| 39 | 11 | 4 | 15 | 15 |
| **Total** | **45** | **6** | **51** *(matches D-03)* | **62** |

**Phase 35 reconstruction (D-05), measured:** `grep -c '<task '` over `35-01..05-PLAN.md` →
3 + 2 + 2 + 3 + 2 = **12**; `grep -c '<automated>'` → identical 12. All 12 are `type="auto"`; zero
`type="checkpoint"`. CONTEXT D-05 says "~14" — the measured number is **12**. [VERIFIED: local
`grep` this session]

| # | Plan | Task | Verify command shape | Re-runnable today? |
|---|------|------|----------------------|--------------------|
| 1 | 35-01 | Write higyrus Null Object suite RED | `pytest -k "not_vacuous or …" && ! pytest -k "falsy_when_empty or truthy_when_populated or empty_emits_nothing"` | **NO — inverts.** The 3 negated tests now pass (measured: `45 passed, 3 deselected`), so the `!` half exits 1 |
| 2 | 35-01 | higyrus `empty()` + `__bool__` | `pytest packages/higyrus-client -q && mypy … && ruff check … && ruff format --check …` | yes |
| 3 | 35-01 | Pin wrong-type falsification | `pytest …/test_decode.py -k "wrong_typed_list or still_raises_on_a_wrong_typed_list" && pytest packages/higyrus-client -q` | yes |
| 4 | 35-02 | Derive 35-row retired-triples table | `test -f .planning/phases/35-…/35-RETIRED-TRIPLES.md && test "$(grep -c '^\| ' …)" -ge 35` | **NO as written** — stale path. Yes after re-point (file has 58 rows) |
| 5 | 35-02 | Per-package subtraction + iol zero row | `grep -q "iol-client" … && grep -q "wallets-client" … && grep -qi "phase 39" …` | **NO as written** — same stale path. Yes after re-point |
| 6 | 35-03 | Port suite to iol-client | `pytest packages/iol-client -q && mypy … && ruff …` | yes |
| 7 | 35-03 | Port to market-data-client (form B) | `pytest packages/market-data-client -q && mypy … && ruff …` | yes |
| 8 | 35-04 | matriz `_SafeModel.__bool__` + 17-class suite | `pytest packages/matriz-client -q && mypy … && ruff …` | yes |
| 9 | 35-04 | ámbito zero roster | `pytest packages/ambito-financiero-client -q && mypy … && ruff …` | yes |
| 10 | 35-04 | wallets zero roster | `pytest packages/wallets-client -q && ruff …` | yes |
| 11 | 35-05 | ATOMIC walker edits ×5 + digest | `tools/check_decode_intactness.py && pytest packages -q && ruff check/format && mypy …` | yes (~93 s) |
| 12 | 35-05 | Phase gate — no public surface moved | `check_decode_intactness && check_uniform_structure && check_surface_types && tools/surface_parity.py && pytest …` | yes |

## Re-Execution Results (measured 2026-08-31, frozen v1.7 tree)

All 45 declared automated rows plus the 10 re-runnable Phase-35 rows were executed this session.
**Not a single row failed for a coverage reason.**

### File existence

All 23 distinct test files / gate scripts cited across the maps of Phases 36-39 exist on disk.
[VERIFIED: `test -e` loop this session] This confirms D-04: the `❌ Wave 0` / `⬜ pending` cells are
plan-time bookkeeping, not gaps.

### Phase 36 (11 rows) — all green

| Row | Command | Result |
|-----|---------|--------|
| 36-01-01 | `pytest …/test_market_data_chain.py -x` | 38 passed in 0.11s |
| 36-01-02 | `mypy packages/market-data-client/src …/tests` | (static, green — same as 38-03-01 pattern) |
| 36-01-03 | `pytest …/test_models.py -k entries -x` | 2 passed, 35 deselected |
| 36-01-04 | `pytest …/test_null_object.py -x` | 61 passed |
| 36-02-01 | `pytest …/test_models.py -k field_set -x` | 1 passed, 36 deselected |
| 36-02-02 | `pytest …/test_models.py -k latest_request -x` | 3 passed, 34 deselected |
| 36-02-03 | `pytest …/test_snapshot_no_data_row.py -x` | 8 passed |
| 36-02-04 | `pytest …/test_snapshot_no_data_row.py -k wrong_typed -x` | 1 passed, 7 deselected |
| 36-03-01 | `pytest …/test_models.py -k mapping_machinery -x` | 1 passed, 36 deselected |
| 36-03-02 | `python tools/check_decode_intactness.py` | exit 0 |
| 36-03-03 | *(map says "planner decide: AST … or assertion")* — **no command in the map** | Resolvable: `verification/test_main_market_data_deep_chain.py` exists and is in the CI allowlist (`ci.yml:81`). Re-point and dispose `VERIFIED-NOW` |

### Phase 37 (14 rows) — 13 green, 1 zero-select

All green except:

- **`-k alias_surfaces` selects 0 of 74 tests → pytest exit 5.** Behavior *is* covered:
  `test_each_alias_returns_the_identical_object_on_a_rest_parsed_snapshot` and
  `…_on_a_ws_frame_parsed_snapshot` both exist and pass. Apply Pattern 3.

Notable greens: `test_surface_types_red.py` 19 passed; `-k exempt` 3 passed;
`iol …::test_gate_is_green_on_the_real_tree` 1 passed; `-k envelope` 10 passed; `-k tickPriceRange`
3 passed; `-k portfolio` 3 passed; `-k extra` 9 passed; `-k mapping` 24 passed; `-k convert` 4
passed; `-k alias` 11 passed; `::test_adding_a_property_alias_does_not_change_the_divergence_count`
1 passed; ws suites 35 passed.

### Phase 38 (9 rows) — all green

`-k optional_model_field` 1 passed · `-k optional_literal_alias` 1 passed · `-k puntas` 5 passed ·
`-k round_trip` 4 passed · `mypy packages/iol-client` → *Success: no issues found in 31 source
files* · matriz `test_surface_types_red.py` 19 passed · `regen_snapshots.py` → 4 files written,
byte-identical, `git status --porcelain` empty. The one manual-only row (`38-CENSUS.md` doc review)
has a **recorded, timestamped human confirmation** in `38-VERIFICATION.md` front-matter
(`confirmed: 2026-08-29T22:04:57Z`) → `VERIFIED-HISTORICALLY`.

### Phase 39 (15 rows) — 10 automated green, 1 zero-select, 4 manual

| Row | Result |
|-----|--------|
| 39-01-01 | `verification/test_main_verify_classification.py` → 7 passed |
| 39-01-02 | matriz skip-line-shape 19 passed; higyrus 8 passed |
| 39-01-03 | **`-k allowlist` selects 0 of 9 → exit 5.** The D-MATZ-33 allowlist behavior lives in a *different* file: `verification/test_main_matriz_skip_line_shape.py` carries `test_venue_allowlist_has_exactly_the_two_known_hosts`, `test_venue_token_resolves_by_exact_hostname` (14 params incl. `…attacker.example` superstring and `…@attacker.example` userinfo variants), and `test_no_substring_membership_check_over_a_host_literal`. Apply Pattern 3 |
| 39-01-04 | `test_cycle_closure_phase33.py` → 21 passed |
| 39-02-01 | `test_main_iol_deep_chain.py` → 6 passed |
| 39-02-02 | `test_main_higyrus_deep_chain.py` → 8 passed |
| 39-02-03 | `test_main_matriz_deep_chain.py` → 9 passed |
| 39-02-04 | `test_cycle_closure_phase33.py -k ambito` → 2 passed, 19 deselected |
| 39-02-05 | 3× `test_deep_chain_edges.py` → 50 passed |
| 39-03-01 | `packages/matriz-client/tests/test_instruments_flat_identifier_shape.py` → 13 passed (the F-43/F-44 in-cycle fix regression) |
| 39-03-02 | `39-CENSUS.md` exists → `VERIFIED-HISTORICALLY` |
| 4 manual-only rows | see § Disposition Decision Rules |

### Cross-cutting

- `uv run pytest packages -q` → **2152 passed, 1 deselected in 92.90s** (matches the ~95 s estimate
  in `35-VALIDATION.md`)
- All four `tools/` gates green: `check_decode_intactness`, `check_uniform_structure`,
  `check_surface_types`, `surface_parity`
- The full CI 12-file `verification/` allowlist → **129 passed in 0.53 s**

## CI Enforcement Map (D-07 fourth column)

Measured against `.github/workflows/ci.yml` at HEAD (identical to v1.7 — `git diff v1.7 HEAD` shows
no `.github/` change).

| Command surface appearing in the maps | CI enforcement |
|---------------------------------------|----------------|
| `pytest packages/<pkg>` | job `test`, `ci.yml:133-165` — matrix of 6 packages × py3.12/3.13 = **12 legs** |
| `mypy` (src global) | job `typecheck`, `ci.yml:122-123` |
| `mypy packages/<pkg>/tests` | job `typecheck`, `ci.yml:124-131` (loop over all 6) |
| `ruff check .` / `ruff format --check .` | job `lint`, `ci.yml:36-39` |
| `lint-imports` | job `lint`, `ci.yml:40-41` |
| `tools/check_decode_intactness.py` | job `lint`, `ci.yml:55` |
| `tools/check_uniform_structure.py` | job `lint`, `ci.yml:60` |
| `tools/check_surface_types.py` | job `lint`, `ci.yml:66` |
| **`tools/surface_parity.py`** | **NOT ENFORCED** as a script — not present anywhere in `ci.yml`. The per-package `packages/*/tests/test_surface_parity.py` (6 files) *are* covered by job `test`. Row 35-05-T2 must say this precisely |
| The 12 allowlisted `verification/test_*.py` | job `lint`, `ci.yml:79-92` |
| The other **40** `verification/test_*.py` | **NOT ENFORCED** (52 files match `verification/test_*.py`; 12 are listed) |
| `verification/regen_snapshots.py` + `git diff` | **NOT ENFORCED** |
| `verification/test_public_surface.py` | **NOT ENFORCED** — this is the open `IN-06` gap routed to Phase 45 (HARN-03) |
| `checkpoint:human-verify`, doc review, live driver run | **NOT ENFORCED** by nature |

The 12 allowlisted files, verbatim (`ci.yml:81-92`): `test_main_market_data_deep_chain.py`,
`test_safemodel_diff_null_object_links.py`, `test_main_matriz_risk_envelope_keys.py`,
`test_safemodel_diff_mapping_recursion.py`, `test_main_verify_classification.py`,
`test_main_matriz_skip_line_shape.py`, `test_main_higyrus_skip_line_shape.py`,
`test_run_evidence.py`, `test_main_iol_deep_chain.py`, `test_main_higyrus_deep_chain.py`,
`test_main_matriz_deep_chain.py`, `test_cycle_closure_phase33.py`.

**Every `verification/` row cited by Phase 39's map is inside the allowlist.** Phase 39 already
closed WR-01. The `NOT ENFORCED` count in this audit will therefore come almost entirely from
Phase 35's `surface_parity.py` row, the `regen_snapshots` row (38-03-02), and the 6 manual rows —
not from the deep-chain locks.

## Workflow Deviations Required

The `/gsd-validate-phase` skill resolves its spec **project-local first**
(`<execution_context>` in `~/.claude/skills/gsd-validate-phase/SKILL.md`). The project-local copy at
`.claude/gsd-core/workflows/validate-phase.md` **differs from the user-level copy** and is the one
that will run. [VERIFIED: `diff` this session]

| # | Stock behavior (project-local `validate-phase.md`) | Required deviation | Source |
|---|---------------------------------------------------|--------------------|--------|
| 1 | §5 spawns `gsd-nyquist-auditor` on "Fix all gaps" | **Never take that branch.** Choose the non-fix path; the audit reads and disposes, it does not repair | D-06(a) |
| 2 | §0 `init.phase-op` returns `roadmap_path: .planning/ROADMAP.md`, `requirements_path: .planning/REQUIREMENTS.md` — **confirmed by running it**; both now hold the v1.8 roster | Override to `.planning/milestones/v1.7-ROADMAP.md` / `v1.7-REQUIREMENTS.md`. (`phase_dir` **is** correct — it resolves to the archived dir; do not override that) | D-06(b) |
| 3 | §3: *"No gaps → skip to Step 6, set `nyquist_compliant: true`."* Since measurement shows ~zero gaps, this fires on all five | **Disable.** `nyquist_compliant` changes only under D-09's evidence rule. This is the criterion-3 tripwire and must be written into the plan as a prohibition, not left implicit | Criterion 3 / D-09 / D-10 |
| 4 | §6 (project-local) says only *"update frontmatter"* — it **lacks** the user-level copy's `**set status: validated**` instruction | Make `status: draft → validated` an **explicit plan task per phase**, not an assumed side effect | D-09 |
| 5 | §6 audit trail is a 3-metric block (Gaps found / Resolved / Escalated) | Keep the metric block **and** add the per-row disposition table (Pattern 2) — criterion 2 needs per-row, not counts | Criterion 2 / D-07 |
| 6 | §4 calls `AskUserQuestion` with a gap table | `workflow.text_mode` is `false` and `mode: yolo` + `auto_advance: true`. The gate will not block. Plan must not rely on a human answering it | `config.json` |
| 7 | §7 commits test files separately then VALIDATION.md | Expected test-file count is **zero** (D-08). Plan one docs commit; if the contingency fires, the extra commit is the signal that D-08's contingency triggered | D-08 |

**Prerequisite confirmed:** §0 exits if no active `verify:post` step hook exists for
`validate-phase`. `gsd_run loop render-hooks verify:post --raw` returns an active
`{ capId: "nyquist", kind: "step", ref.skill: "validate-phase", when: "workflow.nyquist_validation" }`
and `workflow.nyquist_validation` is `true`. The skill will not exit early. [VERIFIED this session]

## Disposition Decision Rules (recommended — resolves the ambiguity in D-04)

D-04 names examples but not a boundary. The measurement exposes rows that sit between the
definitions. Recommend the plan lock these rules explicitly:

| Rule | Disposition | Rationale |
|------|-------------|-----------|
| Command re-runs today, selects ≥1 test, exits 0 | `VERIFIED-NOW` | D-04 |
| Command's `-k` selects 0 tests, but a differently-named test covers the same behavior; corrected command re-runs green | `VERIFIED-NOW (command corrected)` | Coverage is real; the map's bookkeeping was stale, which D-04 explicitly puts in scope |
| Command is a TDD **RED-step** assertion that inverts against the post-implementation tree (35-01 T1) | `VERIFIED-HISTORICALLY` | The RED gate genuinely ran once, at plan time, and cannot be reproduced against a GREEN tree. Cite `35-01-SUMMARY.md` + commit `ece3a3c` (the measured 11-failure red set, cross-checked in `35-VERIFICATION.md` truth #2) |
| Command asserts on a `.planning/` path invalidated by the archive move (35-02 T1/T2) | `VERIFIED-NOW` with the path corrected | The artifact exists and satisfies the assertion (58 rows ≥ 35 floor) |
| Behavior is a one-off doc review with a **dated, recorded human confirmation** (38-05-01) | `VERIFIED-HISTORICALLY` | `38-VERIFICATION.md` front-matter `human_verification[0].confirmed: 2026-08-29T22:04:57Z` — a named, irreproducible artifact |
| Behavior is a census/artifact authored once, still on disk (39-03-02) | `VERIFIED-HISTORICALLY` | `39-CENSUS.md` exists and is cited by `39-VERIFICATION.md` truth #8 |
| Behavior required a **live network run** that *did* happen and left a dated evidence envelope | **Open question — see § Open Questions #1.** Recommend `VERIFIED-HISTORICALLY` | 4 envelopes exist at `.planning/verification/run-evidence/*.json` (2026-08-29) with `probes_executed` counts; plus `39-07-SUMMARY.md` transcripts. This is "artefacto único e irrepetible" — D-04's own definition of `VERIFIED-HISTORICALLY` |
| Behavior required a live run that **never happened** (higyrus SKIPPED for DNS) or a market-hours window that cannot be recreated | `NOT-VERIFIABLE-RETROACTIVELY` | No artifact evidences the behavior; only the *skip* was measured |

## Common Pitfalls

### Pitfall 1: The stock workflow flips all five flags for you

**What goes wrong:** `.claude/gsd-core/workflows/validate-phase.md` §3 line: *"No gaps → skip to
Step 6, set `nyquist_compliant: true`."* The measurement in this document shows there are
effectively no gaps. Running the skill as written therefore produces exactly the outcome
criterion 3 forbids — and it happens *silently*, inside a step the operator reads as routine.
**Why it happens:** the deviation lives in a single sentence buried in §3, not in the fix-gaps gate
(§4/§5) that D-06(a) already flags. It is easy to guard §5 and miss §3.
**How to avoid:** write the prohibition into the plan task text, and make the front-matter edit a
separate explicit task with its own evidence requirement.
**Warning signs:** a diff that changes `nyquist_compliant:` on more than one file in one commit; any
`nyquist_compliant: true` on a phase whose audit section lists a `NOT-VERIFIABLE-RETROACTIVELY` row.

### Pitfall 2: A `-k` selector that matches nothing reads as green

**What goes wrong:** `pytest … -k alias_surfaces -q` prints `74 deselected in 0.01s` — no dots, no
`failed`, no traceback. It returns **exit code 5** ("No tests were collected"), so a `&&` chain does
break, but a transcript pasted into a report looks clean. Two of the 45 rows have this shape
(measured: `37-04b`, `39-01-03`).
**Why it happens:** `-k` expressions in the maps were written at plan time against test names that
were later chosen differently.
**How to avoid:** the `VERIFIED-NOW` evidence cell must carry a **non-zero passed count**, not merely
"no failures". Reject any evidence string of the form `N deselected` with no `passed`.
**Warning signs:** an evidence cell whose output line contains `deselected` but not `passed`.
[VERIFIED: exit code 5 reproduced locally; CITED: docs.pytest.org/en/stable/reference/exit-codes.html]

### Pitfall 3: Re-running a TDD RED step and calling it a failure

**What goes wrong:** `35-01` Task 1's verify command is
`pytest -k "not_vacuous or …" && ! pytest -k "falsy_when_empty or truthy_when_populated or
empty_emits_nothing"`. The `!` asserts those three tests **fail** — true only before the
implementation landed. Today they pass (measured: `45 passed, 3 deselected`), so the chain exits 1.
An auditor who reads that as red will either mis-dispose the row or, worse, "fix" a test.
**Why it happens:** `tdd_mode: true` means RED-step verify blocks are a normal shape in this repo's
plans; nothing in the block marks it as non-reproducible.
**How to avoid:** scan every reconstructed Phase-35 command for a `!` or a negated assertion before
running it. Dispose those `VERIFIED-HISTORICALLY`.
**Warning signs:** any verify command containing `&& !` or `|| exit 1` on a passing test selector.

### Pitfall 4: Grading against what shipped instead of against the criterion

*(Verbatim from `.planning/research/PITFALLS.md` § Pitfall 4 — the project already wrote this.)*
**What goes wrong:** `VALIDATION.md` is by its own text a *pre-execution* sampling contract. Run
afterwards, the only honest deliverable is a coverage audit. Flipping `draft → validated` +
`false → true` on the strength of "the suite is green today" erases the historical record and
redefines each phase's criterion as "whatever the shipped artifact satisfies".
**How to avoid:** three dispositions, zero undisposed rows, per-row evidence.
**Warning signs:** a commit that flips five `nyquist_compliant` flags with no per-row evidence table;
any ✅ on a row whose Test Type column reads `manual`.

### Pitfall 5: "Green locally" certifying a lock that CI never runs

*(Verbatim from `.planning/research/PITFALLS.md` § Pitfall 5.)*
**What goes wrong:** 52 files match `verification/test_*.py`; the `ci.yml` allowlist runs 12.
`testpaths` in `pyproject.toml` includes `verification`, so local `pytest` picks them all up. CI
overrides with explicit paths. The two environments disagree by design and the disagreement is
invisible from a local green.
**How to avoid:** the D-07 enforcement column on every row. Expect a non-trivial `NOT ENFORCED`
count — *that count is the finding*.
**Warning signs:** an audit that reports 100% green; a report citing `testpaths` as proof of CI
coverage.

### Pitfall 6: Resolving the annotated tag to the wrong object

**What goes wrong:** `git rev-parse v1.7` returns `c4dc6eafdc9e37032c6513f624745b270e2156ec` — the
**tag object**, because `v1.7` is annotated (`git cat-file -t v1.7` → `tag`). D-02's SHA is
`37a83fe693a303a551f4374f48fe6fc5521804f7`, the *commit*. Declaring the tag-object SHA in five
artifacts would make criterion 1 unverifiable by anyone re-checking it.
**How to avoid:** always `git rev-parse v1.7^{commit}`.
**Warning signs:** a declared SHA beginning `c4dc6ea`.

### Pitfall 7: Silently widening scope to the other draft phases

**What goes wrong:** Six *other* `VALIDATION.md` files are also `status: draft` /
`nyquist_compliant: false` — phases **18, 25, 29, 30, 32, 33** (measured). It is one grep away to
"just do them too". Criterion 5 forbids it, and `REQUIREMENTS.md § Out of Scope` names
`NYQUIST-32-33` specifically.
**How to avoid:** the close-out task asserts exactly five files changed under
`.planning/milestones/v1.7-phases/`, and that the `NYQUIST-32-33` row in `REQUIREMENTS.md` is
byte-unchanged.
**Warning signs:** `git diff --name-only` listing any `{18,25,29,30,32,33}-VALIDATION.md`.

**Note on criterion 5's wording:** there is **no backlog entry literally named `NYQUIST-32-33`** in
`ROADMAP.md § Backlog`. The backlog entry there is `NYQUIST-35-39` — which *is* this phase's scope.
`NYQUIST-32-33` exists only as a row in `REQUIREMENTS.md § Out of Scope` (line 44), exactly as
criterion 5's parenthetical says. The plan must verify *that* row, and must not go hunting for a
nonexistent backlog entry. [VERIFIED: grep across `ROADMAP.md`, `REQUIREMENTS.md`, `MILESTONES.md`]

## Code Examples

Verified command patterns, all re-run in this session.

### Criterion 1: prove the tree is frozen and declare both SHAs

```bash
# Source: measured this session; D-02
TAG_COMMIT=$(git rev-parse v1.7^{commit})     # 37a83fe693a303a551f4374f48fe6fc5521804f7
AUDIT_HEAD=$(git rev-parse HEAD)
git diff --quiet v1.7 HEAD -- . ':(exclude).planning' \
  && echo "FROZEN: source tree identical to v1.7 (${TAG_COMMIT})" \
  || { echo "ABORT: v1.8 source changed before the audit closed"; exit 1; }
```

### Resolve an archived phase directory (never hard-code the slug)

```bash
# Source: gsd-tools seam, verified this session — returns the v1.7-phases archive path
INIT=$(node .claude/gsd-core/bin/gsd-tools.cjs query init.phase-op 35)
# .phase_dir => .planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker
# .phase_found => true
# NOTE: .roadmap_path / .requirements_path point at the v1.8 ROOT files — override per D-06(b)
```

### Capture `VERIFIED-NOW` evidence with a non-vacuity guard

```bash
# Source: pytest exit-code semantics (docs.pytest.org) + measured locally
run_row() {                       # $1 = row id, rest = pytest args
  local row="$1"; shift
  local out rc
  out=$(uv run pytest "$@" -q 2>&1 | tail -2 | tr '\n' ' ')
  rc=${PIPESTATUS[0]}
  case "$out" in
    *" passed"*) : ;;             # ok — at least one test actually ran
    *) echo "VACUOUS ROW $row: $out" >&2; return 1 ;;
  esac
  [ "$rc" -eq 0 ] || { echo "RED ROW $row (rc=$rc): $out" >&2; return 1; }
  printf '%s | %s\n' "$row" "$out"
}
```

### Reconstruct Phase 35's rows from its plan files (D-05)

```bash
# Source: measured this session — 12 tasks, 12 <automated> blocks, zero checkpoints
D=.planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker
grep -h -c '<task '      "$D"/35-0*-PLAN.md   # 3 2 2 3 2  -> 12
grep -h -c '<automated>' "$D"/35-0*-PLAN.md   # 3 2 2 3 2  -> 12
awk '/<task /{t++} /<name>/{gsub(/<\/?name>/,"");print "T"t": "$0}
     /<automated>/{gsub(/<\/?automated>/,"");print "  cmd: "$0}' "$D"/35-0*-PLAN.md
```

### Prove no `verification/` lock was left inert (criterion 4)

```bash
# Source: ci.yml:79-92, measured this session
TOTAL=$(ls verification/test_*.py | wc -l)                       # 52
ENROLLED=$(grep -c 'verification/test_' .github/workflows/ci.yml) # 12
echo "verification locks: ${ENROLLED}/${TOTAL} enrolled in the CI allowlist"
# Criterion 4 gate: the audit must add ZERO new files here (D-08 expected count).
git status --porcelain verification/   # must be empty at phase end
```

### Scope containment (criterion 5)

```bash
# Source: REQUIREMENTS.md:44, verified this session
grep -F 'NYQUIST-32-33' .planning/REQUIREMENTS.md   # row must be present, byte-unchanged
git diff --quiet .planning/REQUIREMENTS.md && echo "Out-of-Scope table untouched"
# Exactly five VALIDATION.md files may change:
git diff --name-only | grep -c 'v1.7-phases/3[5-9]-.*-VALIDATION\.md'   # must be 5
git diff --name-only | grep -E 'v1\.[0-6]-phases/.*-VALIDATION\.md' && echo "SCOPE CREEP" || true
```

## State of the Art

| Old assumption | Measured reality | Impact |
|----------------|------------------|--------|
| "Phase 40 reached `nyquist_compliant: true` via validate-phase" (`v1.7-MILESTONE-AUDIT.md:43`) | Flag was set by **plan-check** — commit `6e83d29 docs(phase-40): mark validation strategy nyquist-compliant post plan-check`. `40-VALIDATION.md` has **no** `## Validation Audit` section and its map has no Status column | There is **no** validate-phase-produced precedent in v1.6/v1.7. The format precedents are `01-`, `06-` and `09-VALIDATION.md`, all from v1.0/v1.1 |
| Phase 35 has "~14" reconstructable rows (D-05) | **12** `<task>` / 12 `<automated>` blocks | Denominator is 62, not 64 |
| The 5 draft phases are the only unvalidated ones | **11** files sit at `status: draft`/`nyquist_compliant: false`: 18, 25, 29, 30, 32, 33, 35, 36, 37, 38, 39 | Scope-creep pressure is real; criterion 5 is a live constraint, not ceremony |
| `status` lifecycle is `draft → validated` (template + D-09) | **No file in the repo uses `validated`.** Observed values: `complete`, `closed`, `approved`, `verified`, `ready_for_verify`, `populated`, `planned`, `ready`, `draft`. `09-VALIDATION.md` ran a retroactive audit and left `status: approved` | D-09 introduces a *new* value to this repo. Fine, but the plan should say so, and note the divergent precedent rather than pretend `validated` is established |
| `nyquist_compliant` is boolean | `07-VALIDATION.md` uses `nyquist_compliant: partial` — a third value already precedented in-repo | An alternative to D-09's binary `false` exists. See Open Question #2 |
| Test infra is "pytest 8.3" (`35-VALIDATION.md`) | pytest **9.0.3**, mypy **1.20.2**, ruff **0.15.12**, uv **0.11.3** | Stale Test Infrastructure rows; name them in the audit section rather than silently rewriting them |
| `-k alias_surfaces` / `-k allowlist` are valid selectors | Both select **zero** tests | Two rows need Pattern 3 |

**Deprecated / superseded:**
- `.planning/phases/35-…/` paths inside `35-02-PLAN.md` — superseded by
  `.planning/milestones/v1.7-phases/35-…/` after the v1.7 archive.
- The claim in `39-VALIDATION.md` Wave 0 that `ci.yml:80-84` is the allowlist — it is now
  `ci.yml:81-92` (12 files, widened by Phase 39's own WR-01 fix at commit `0f45508`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Both zero-select rows (`37-04b`, `39-01-03`) are bookkeeping errors, not coverage gaps — the behavior is covered by differently-named tests I identified by reading the collected test names | Re-Execution Results; Pattern 3 | If the named substitutes do not actually assert the same behavior, two rows would be falsely disposed `VERIFIED-NOW`. Mitigation: the plan should require reading the substitute test bodies, not just their names |
| A2 | The 4 live-run evidence envelopes in `.planning/verification/run-evidence/` are sufficient evidence for `VERIFIED-HISTORICALLY` on Phase 39's live-run manual rows | Disposition Decision Rules | Conflicts with D-04's explicit example, which pre-assigns those 4 rows to `NOT-VERIFIABLE-RETROACTIVELY`. Escalated as Open Question #1 rather than assumed |
| A3 | Phases 36 and 37 could legitimately close with zero non-`VERIFIED-NOW` rows, making `nyquist_compliant: true` the *honest* answer for them under D-09's own rule | Open Questions #2 | D-09's parenthetical predicts `false` for all five. If 36/37 close clean and the plan forces `false` anyway, the artifact under-reports; if it flips to `true` without the operator having anticipated it, it may read as the mechanical flip criterion 3 forbids |
| A4 | `status: validated` is the correct new front-matter value despite no in-repo precedent | State of the Art | Low — D-09 locks it. Only risk is that `audit-milestone §5.5`'s parser expects a different token; the inline comment in the front-matter of 35-38 cites `validated` explicitly, so this is low risk |
| A5 | The audit will produce zero new test files (D-08's expected count) | Package Legitimacy Audit; Workflow Deviations #7 | Low — every re-run passed, so no gap motivates a new lock |

## Open Questions

1. **Are Phase 39's four manual-only rows `VERIFIED-HISTORICALLY` or `NOT-VERIFIABLE-RETROACTIVELY`?**
   - *What we know:* D-04 names them as the example for `NOT-VERIFIABLE-RETROACTIVELY`. But the
     evidence they would need for `VERIFIED-HISTORICALLY` **exists on disk**: four dated run-evidence
     envelopes (`.planning/verification/run-evidence/{iol,higyrus,ambito-financiero,matriz}-client.json`,
     2026-08-29), `39-07-SUMMARY.md` transcripts, `39-CENSUS.md` § "Casos límite de D-12", and — for
     the D-02 operator checkpoint row — a recorded sign-off cited in `39-VALIDATION.md` itself and in
     memory `project_matriz_bbsa_sandbox.md`. D-04's own definition of `VERIFIED-HISTORICALLY` is
     "evidencia de artefacto único e irrepetible", which these envelopes are.
   - *What's unclear:* whether D-04's example was a *rule* or an *expectation formed before the
     envelopes were noticed*.
   - *Recommendation:* Split the four rows rather than treating them as a block. Rows 1
     (live driver run), 3 (census contrast) and 4 (D-02 operator checkpoint) → `VERIFIED-HISTORICALLY`
     with the envelope/artifact path cited. Row 2 (matriz D-12 market-closed vs. mis-modelled
     discrimination, which requires a specific trading-session window) → `NOT-VERIFIABLE-RETROACTIVELY`.
     That keeps at least one `NOT-VERIFIABLE-RETROACTIVELY` on Phase 39, which is what D-09's
     `nyquist_compliant: false` prediction rests on, while not discarding real evidence.

2. **Do Phases 36 and 37 close clean — and if they do, does `nyquist_compliant: true` violate
   criterion 3 or satisfy it?**
   - *What we know:* Both files declare zero manual-only rows. All 11 of Phase 36's rows and all 14 of
     Phase 37's re-ran green this session (37 after one command re-point; 36's row `36-03-03` after
     re-pointing to the existing, CI-enrolled `verification/test_main_market_data_deep_chain.py`).
     Under D-09's stated rule — *"sólo cambia donde la disposición es `VERIFIED-NOW` re-ejecutada en
     esta sesión … sólo si **todas** las filas de esa fase cierran limpias"* — 36 and 37 qualify.
   - *What's unclear:* D-09's parenthetical says this is *"cosa que no se espera para ninguna de las
     5"*. That is a **prediction**, and the measurement contradicts it for two phases.
   - *Recommendation:* Treat D-09's *rule* as binding and its *prediction* as non-binding. Let the
     evidence decide per phase. If 36 and 37 close with 25/25 `VERIFIED-NOW` rows, `true` is the
     honest value and is **not** a mechanical flip — criterion 3 forbids flips *"por flip mecánico"*,
     not evidenced ones. Surface this to the operator at plan time so the outcome is not a surprise.
     If the operator prefers, `nyquist_compliant: partial` (already precedented in
     `07-VALIDATION.md`) is a third option that reports honestly without claiming full compliance.

3. **Does the `## Validation Audit` section belong before or after `## Validation Sign-Off`?**
   - *What we know:* `01-` and `09-VALIDATION.md` append it at the end (after Sign-Off); `06-` places
     it after Sign-Off too. Workflow §6 says "Append audit trail".
   - *Recommendation:* Append at end of file, matching all three precedents. Leave the original
     Sign-Off checklist **unchecked and untouched** — it is a plan-time artifact; ticking it
     retroactively is a species of the same laundering D-10 warns about. Say so explicitly in the
     audit section.

4. **Should the reconstructed Phase-35 map replace the placeholder row, or sit beside it?**
   - *What we know:* D-05 says the placeholder must not be disposed as a unit; it does not say the row
     must be deleted.
   - *Recommendation:* Keep the placeholder row visible with a struck-through note
     (`superseded by the 12 reconstructed rows below — see Validation Audit 2026-08-31`) and add the
     12 rows beneath it. Deleting it erases the evidence that Phase 35 shipped with an unfilled map,
     which is itself an audit finding worth preserving.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | every re-executed row | ✓ | 0.11.3 | — |
| `pytest` (via uv) | 45 automated rows | ✓ | 9.0.3 | — |
| `mypy` (via uv) | ~9 static rows | ✓ | 1.20.2 | — |
| `ruff` (via uv) | ~6 Phase-35 chains | ✓ | 0.15.12 | — |
| `git` | criterion 1 + historical SHAs | ✓ | 2.39.5 | — |
| `node` (for `gsd-tools.cjs`) | `init.phase-op`, `query commit` | ✓ | v24.15.0 | — |
| `gh` | not required by this phase | ✓ | 2.90.0 | — |
| Network / live APIs | **not required** | n/a | — | All network-bound rows dispose from artifacts, never from a fresh live run |
| `.env` credentials | **not required** | n/a | — | No audited command reads them |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

**Timing budget (measured):** full `uv run pytest packages -q` = **92.9 s** (2152 tests); CI
verification allowlist = **0.53 s** (129 tests); all four `tools/` gates < 5 s combined; every
targeted `-k` row < 0.3 s. A complete re-execution of all 55 runnable rows is comfortably under
5 minutes, dominated by the two full-suite invocations in Phase 35 rows 11 and 12.

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`, so Phase 41 receives its own
seeded `41-VALIDATION.md` (plan-phase §6 writes it from
`.claude/gsd-core/templates/VALIDATION.md`). Per D-10, that file is held to the same bar as the five
it audits.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (+ pytest-asyncio `asyncio_mode = "auto"`, pytest-httpx, pytest-cov) |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` (`--import-mode=importlib`, `--strict-markers`, `pythonpath = ["."]`) |
| Quick run command | `uv run pytest -q verification/test_cycle_closure_phase33.py` — but note **Phase 41 adds no pytest cases**; its "quick run" is really the shell/grep assertions below |
| Full suite command | `uv run pytest packages -q` (92.9 s) — used only as an audited row, not as this phase's own gate |

### Phase Requirements → Test Map

Phase 41 produces **documentation artifacts**, so most of its own verification is shell assertion
over file state, following the `40-VALIDATION.md` precedent (which did the same for a release phase).

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NYQ-01 (crit. 1a) | Five audit sections exist, one per phase | shell | `for n in 35 36 37 38 39; do grep -q '^## Validation Audit ' .planning/milestones/v1.7-phases/$n-*/$n-VALIDATION.md \|\| exit 1; done` | ✅ (shell) |
| NYQ-01 (crit. 1b) | Each declares the v1.7 commit SHA | shell | `grep -l '37a83fe693a303a551f4374f48fe6fc5521804f7' .planning/milestones/v1.7-phases/3[5-9]-*/3?-VALIDATION.md \| wc -l` == 5 | ✅ (shell) |
| NYQ-01 (crit. 1c) | No v1.8 source changed before the last artifact was written | shell | `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` | ✅ (shell) |
| NYQ-01 (crit. 2a) | Every row carries exactly one disposition | shell | per-file: count of `VERIFIED-NOW`+`VERIFIED-HISTORICALLY`+`NOT-VERIFIABLE-RETROACTIVELY` occurrences in the disposition table == that phase's row count | ✅ (shell) |
| NYQ-01 (crit. 2b) | Dispositions sum to the enumerated total (62) | shell | sum across 5 files == 62 | ✅ (shell) |
| NYQ-01 (crit. 3a) | No `nyquist_compliant` flipped without evidence | shell | for each file where `nyquist_compliant: true`: assert zero `NOT-VERIFIABLE-RETROACTIVELY` rows AND every row cites a command+output | ✅ (shell) |
| NYQ-01 (crit. 3b) | Phases retaining `NOT-VERIFIABLE-RETROACTIVELY` say so in front-matter | shell | grep front-matter for an explicit marker on those files | ❌ Wave 0 — front-matter key name must be chosen by the planner |
| NYQ-01 (crit. 4) | Zero new locks left inert | shell | `git status --porcelain verification/` empty AND `ls verification/test_*.py \| wc -l` == 52 (unchanged) | ✅ (shell) |
| NYQ-01 (crit. 5) | `NYQUIST-32-33` row intact; exactly 5 VALIDATION.md changed | shell | `grep -F 'NYQUIST-32-33' .planning/REQUIREMENTS.md` && `git diff --name-only \| grep -c 'v1.7-phases/3[5-9]-.*VALIDATION\.md'` == 5 | ✅ (shell) |
| NYQ-01 (anti-vacuity) | No evidence cell is vacuously green | shell | `grep -n 'deselected' <audit sections> \| grep -v 'passed'` must return nothing | ✅ (shell) |

### Sampling Rate

- **Per task commit:** the task's own shell assertion (all < 1 s except the two full-suite rows)
- **Per wave merge:** re-run `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` (criterion 1 is a
  *continuous* invariant, not a one-shot gate — it must hold until the fifth artifact is written)
- **Phase gate:** the arithmetic close-out (62 == sum of dispositions) + all criterion assertions green

### Wave 0 Gaps

- [ ] Choose and document the front-matter marker for "this phase retains NOT-VERIFIABLE-RETROACTIVELY
      items" (criterion 3b). Candidates: a `not_verifiable_retroactively: N` key, or a
      `nyquist_compliant: partial` value (precedented in `07-VALIDATION.md`). Must be decided before
      the first artifact is written, or the five will be inconsistent.
- [ ] Fix the row-count baseline in the plan text: **62**, with the 13/11/14/9/15 breakdown, so
      criterion 2's arithmetic has a stated denominator.

*(No test-framework install needed; no `conftest.py` changes; no new pytest files expected.)*

## Security Domain

`workflow.security_enforcement` is `true`, `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase writes markdown; no auth surface touched |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | No untrusted input is parsed; all inputs are repo-local artifacts |
| V6 Cryptography | no | No crypto |
| **V7 Error Handling & Logging** | **yes** | Command output is transcribed into committed markdown. Trim to summary lines; never paste verbose output that could contain a hostname, token, account id, or `.env`-derived value. CLAUDE.md: *"nunca commitear `.env` ni exponer credenciales en logs, reportes o tests"* |
| **V14 Configuration** | **yes** | The audit's *finding* is partly a security-configuration statement: 40 of 52 `verification/` locks are NOT ENFORCED in CI, including `test_mutation_gate_parametrized.py` and `test_main_matriz_login_fail_uniformity.py`. Report the count; do not "fix" it (Phase 45 owns that) |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential leakage via transcribed command output into a committed `.md` | Information Disclosure | Capture only `tail -2` summary lines; grep the diff for `://`, `@`, `token`, `password`, `Bearer` before committing |
| Certifying a security lock that CI never runs (e.g. the D-MATZ-33 hostname allowlist tests) as "covered" | Repudiation / false assurance | D-07 enforcement column. Measured: the allowlist tests *are* enrolled (`ci.yml:86`), so this row is genuinely enforced — but the general pattern must be checked per row |
| Re-running a network-touching command during the audit and hitting a live financial API | Tampering (against a third party) | **No audited command touches the network.** Every network-bound row disposes from artifacts. If any re-run would open a socket, dispose it historically instead |
| Mechanically flipping `nyquist_compliant` producing false assurance downstream (`audit-milestone` reads it) | Repudiation | Criterion 3; Workflow Deviation #3 |

**Note:** `verification/mutation_gate.py` and its parametrized spoofing test are **not** re-run by
this phase and must remain byte-identical (they are Phase 42's concern). `git status --porcelain
verification/` empty at phase end covers this.

## Sources

### Primary (HIGH confidence — measured or read directly this session)

- `.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-CONTEXT.md` — locked decisions D-01..D-10
- `.planning/ROADMAP.md` § Phase 41 (lines 66-78) — the five success criteria
- `.planning/REQUIREMENTS.md` — NYQ-01, traceability, cross-phase precondition table (lines 79-84), Out of Scope row for `NYQUIST-32-33` (line 44)
- `.planning/milestones/v1.7-phases/{35,36,37,38,39}-*/{N}-VALIDATION.md` — the 5 target artifacts; row counts measured
- `.planning/milestones/v1.7-phases/{35,36,37,38,39}-*/{N}-VERIFICATION.md` — independent historical evidence, all `status: passed`
- `.planning/milestones/v1.7-phases/35-*/35-0{1..5}-PLAN.md` — 12 tasks / 12 `<automated>` blocks, extracted
- `.planning/milestones/v1.1-phases/09-deferred-bug-fixes/09-VALIDATION.md` — **the retroactive-audit format precedent**
- `.planning/milestones/v1.1-phases/06-compat-safety-net-client-class-skeleton/06-VALIDATION.md` — richer 3-table audit precedent
- `.planning/milestones/v1.0-phases/01-safety-harness-verification-infrastructure/01-VALIDATION.md` — metric-block precedent
- `.planning/research/PITFALLS.md` §§ Pitfall 4, 5, 7 — the project's own pre-written analysis of this phase
- `.planning/milestones/v1.7-MILESTONE-AUDIT.md` § Nyquist Coverage — the origin of NYQ-01
- `.github/workflows/ci.yml` — enforcement map, exact line numbers
- `.claude/gsd-core/workflows/validate-phase.md` (project-local, **wins**) vs `~/.claude/gsd-core/workflows/validate-phase.md` — diffed
- `~/.claude/skills/gsd-validate-phase/SKILL.md` — `<execution_context>` resolution order
- `.claude/agents/gsd-nyquist-auditor.md` — charter (test generation), confirming D-06(a)
- `.claude/gsd-core/templates/VALIDATION.md` — the seeded shape for `41-VALIDATION.md`
- `./CLAUDE.md` — project constraints
- Live tool output this session: `git rev-parse v1.7^{commit}`, `git diff v1.7 HEAD -- . ':(exclude).planning'`, `gsd-tools query init.phase-op 35/41`, `gsd-tools loop render-hooks verify:post`, `uv run pytest` ×40+, `uv run mypy`, `tools/check_*.py` ×4, `verification/regen_snapshots.py`

### Secondary (MEDIUM confidence)

- [docs.pytest.org — Exit codes](https://docs.pytest.org/en/stable/reference/exit-codes.html) — exit code 5 = "No tests were collected"; no core flag converts it to a failure (third-party `pytest-custom_exit_code` is the documented option). **Cross-confirmed locally**: `pytest -k alias_surfaces` returned exit 5 in this session, which raises this specific claim to HIGH.

### Tertiary (LOW confidence)

- None. No claim in this document rests on training data alone; every factual assertion was either
  measured in this session or read from a repo file cited above.

## Metadata

**Confidence breakdown:**

- Row inventory / denominator (62): **HIGH** — counted directly from the five files and the five plan files
- Re-execution results: **HIGH** — every command was run in this session; outputs transcribed
- CI enforcement map: **HIGH** — line numbers grepped from `ci.yml` at HEAD, which is byte-identical to v1.7
- Workflow deviations: **HIGH** — project-local vs user-level workflow diffed; skill resolution order read from `SKILL.md`; `init.phase-op` and `render-hooks` executed
- Disposition decision rules: **MEDIUM** — the rules are derived from D-04's definitions plus measured artifact availability; the live-run boundary (Open Question #1) is genuinely ambiguous and is escalated rather than resolved
- `nyquist_compliant` end state for 36/37: **MEDIUM** — the measurement is solid, but whether `true` is desired conflicts with D-09's prediction; escalated as Open Question #2
- Security domain: **HIGH** — the phase has no code surface; the applicable controls are output-hygiene and honest reporting

**Research date:** 2026-08-31
**Valid until:** the moment any v1.8 source commit lands. This document's measurements are only true
against the frozen v1.7 tree (`37a83fe6…`). Re-measure if `git diff v1.7 HEAD -- . ':(exclude).planning'`
is ever non-empty.
