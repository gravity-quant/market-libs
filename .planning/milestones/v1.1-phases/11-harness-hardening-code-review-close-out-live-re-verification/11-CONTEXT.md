# Phase 11: Harness Hardening + Code Review Close-out + Live Re-verification - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Cierre del milestone v1.1 con 3 vetas que se cruzan técnicamente pero pueden trabajarse en paralelo hasta el gate final:

**A. Harness hardening (HARN-07/08/09/10):**
- `verification/findings.py` se vuelve append-only con BEGIN/END zone parser + merge atómico → contenido fuera de la zona (operator content arriba/abajo) sobrevive a re-runs.
- Content-addressed dedupe by finding ID en los 4 drivers (`main_iol.py`, `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py`).
- `main_matriz.py` dedupe del `D-MATZ-27 EXPECTED` terminal — re-run 1× detecta duplicación (no N×).
- Operator fields (`Classification:`, `Rationale:`, `Regression:`, `Resolution:`) sobreviven verbatim a N re-runs.

**B. Code Review close-out (CR-01/02/04/06/07/08):**
- 6 fixes específicos en `main_matriz.py` (líneas concretas) + `main_higyrus.py` con regression tests proporcionales a la severidad.
- CR-03 y CR-05 ya cerrados en Phases 7 / 9 — NO se re-tocan acá.

**C. LIVE-01 final gate:**
- `main_*.py --live × 4 paquetes` (ámbito, iol, higyrus, matriz) pasa sin regresiones contra baseline `verification-cycle-2026-Q2` (Phase 5 close-out commit `4d48e07`).
- `verify_cycle_closure × 4 pkgs` reporta PASS para los 3 limpios + estado actualizado para matriz post-BUG-01.
- CI green final: ruff + mypy strict + pytest 3.12/3.13 + las regresiones acumuladas v1.1 (Phase 6/7/8/9/10).

**Out of scope (no scope creep):**
- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff) → v1.2 backlog
- `matriz_client.ws_client` live verification → v1.2 backlog
- IOL refresh_token disk persistence → v1.2 backlog
- Risk API auth_basic async (Phase 10 CR-08 territory) → v1.2 backlog

</domain>

<decisions>
## Implementation Decisions

### Code Review Fix Grouping (área discutida)

- **D-CR-01: 1 mega-plan con 6 tasks atómicos.** Los 6 CRs viven en un solo PLAN.md con un commit atómico por CR. Patrón consistente con Phase 8 CR fixes (commits `745503c` CR-01 + `625cb55` CR-02 cada uno como atomic unit). Contexto compartido reduce overhead; scope-guard claro.

- **D-CR-02: Test gating proporcional a severidad.**
  - **CR-07 (thread-safety event_hooks mutation)** + **CR-06 (bare except ≥20 sites)**: regression test PRIMERO (RED commit), luego fix (GREEN commit). Mismo patrón TDD que Phase 8 WR-06 + WR-07.
  - **CR-01 (snapshot path mismatch)** + **CR-02 (FAIL→FINDING uniformity)** + **CR-04 (`_first_dict` silent fallback)**: regression test mockeado O assertion en driver smoke test (no live required). RED+GREEN en un solo commit por CR (driver-level test scope).
  - **CR-08 (line-length >100 cols cosmetic)**: solo `uv run ruff check --no-fix && ruff format --check` como gate; no regression test específico necesario. Cosmetic fix.

- **D-CR-03: Orden risk-first dentro del mega-plan.**
  ```
  Task 1: CR-07 (higyrus event_hooks lock or per-request hook injection) — más riesgoso, atacar primero
  Task 2: CR-06 (bare except narrowing en main_matriz.py + main_higyrus.py, ≥20 sites split en 2 commits)
  Task 3: CR-04 (main_matriz.py:172-179 _first_dict distinguir no_data/wrong_type/ok)
  Task 4: CR-02 (probe_login_sync FAIL→FINDING uniformity)
  Task 5: CR-01 (probe_schema_snapshot sample_params vs snapshot path alignment)
  Task 6: CR-08 (main_higyrus.py:767 line-length cosmetic)
  ```
  Hard-first detecta issues estructurales temprano; CR-08 cosmetic al final como confidence-builder.

### Claude's Discretion (áreas no discutidas — defaults aceptados por operator)

- **D-WAVE-01: Estructura de waves = Wave 1 (Plan A harness ∥ Plan B CR mega-plan) → Wave 2 (Plan C LIVE-01 × 4 paquetes).**
  - **Justificación:** ROADMAP dice explícitamente "harness changes pueden empezar en paralelo" con Phase 10. LIVE-01 es gate final dependiente de A+B. 3 plans en 2 waves balancea velocidad y aislamiento. Riesgo de colisión cross-plan: ambos tocan `main_matriz.py` — el planner debe declarar `files_modified` overlap explícitamente para que execute-phase serialice si hace falta (per Phase 10 intra-wave overlap check).
  - **Per-package serial pattern (Phase 6 D-05 / 7 D-13 / 8 D-21 / 9 D-10 / 10 D-X):** NO aplica acá — Phase 11 NO replica refactor 4×; HARN/CR son scope cross-cutting global, LIVE-01 ejercita los 4 paquetes en el run pero el código de drivers ya es por-paquete.

- **D-HARN-01: `findings.py` append-only architecture = HÍBRIDO.**
  - **Approach:** extender `_parse_findings` / `_serialize_findings` existentes (ya preservan "status humano" per docstring del módulo) agregando markers explícitos `<!-- BEGIN AUTO-GENERATED -->` y `<!-- END AUTO-GENERATED -->`.
  - **Contract:** todo lo que vive ENTRE los markers es zona regenerable por el driver; todo lo que vive ARRIBA del BEGIN o ABAJO del END (operator narrative, classification rationale, manual triage notes) es preservado verbatim en cada re-run.
  - **Migration:** los findings files existentes (`<pkg>-findings.md` committeados en Phase 5 close-out) NO tienen los markers todavía; el planner debe incluir un task de migración que inyecte los markers en los 4 files preservando el contenido actual.
  - **Justificación:** ROADMAP SC#1 explícito + minimum blast radius (no full rewrite) + alineado con docstring existente "no pisar status promovidos por humano".

- **D-LIVE-01: Baseline + acceptance bar.**
  - **Baseline canonical:** los `<pkg>-findings.md` committeados en commit `4d48e07` "verification-cycle-2026-Q2" (Phase 5 close-out) son la fuente de verdad por paquete. `verification/baselines/phase-06-baseline.txt` aplica solo para el snapshot textual de Phase 6.
  - **Acceptance bar:** **operator-gated** — cada NEW FINDING que aparezca en el LIVE-01 run requiere disposición explícita del operador antes del Phase 11 close (PASS / NEW-BUG-XX / EXPECTED / NO-FIX). Consistente con Phase 9 BUG-02 NO-FIX pattern (override autorizado en 09-VERIFICATION.md frontmatter).
  - **Regresión bloqueante:** wire URL changes en sync vs async, probe outcome flips PASS→FAIL para findings PRE-baseline, y cualquier credential leak en logs. Estos NO requieren operator decision — bloquean cierre.

### Folded Todos

- **`matriz-driver-findings-file-handling.md`** (score 0.6, `resolves_phase: 11` explícito en frontmatter).
  - **Original problem:** dos bugs en `main_matriz.py` re-runs — Bug 1: `D-MATZ-27 EXPECTED` terminal no se dedupea (N+1 duplicates después de N re-runs); Bug 2: classification rationale lines added by operator destroyed on re-run.
  - **Fit Phase 11 scope:** Bug 1 = HARN-10 exactly; Bug 2 = HARN-07/09 (operator field preservation). El todo es el documento source-of-truth de los root causes y fix sketches — el planner debe leerlo durante research/planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 11 scope sources
- `.planning/ROADMAP.md ### Phase 11` — goal, depends_on, 11 requirements, 5 success criteria
- `.planning/REQUIREMENTS.md ### Harness hardening (HARN-07+)` — HARN-07/08/09/10 descriptions con fix sketches
- `.planning/REQUIREMENTS.md ### Code Review concerns` — CR-01..08 con line-numbers exactos en `main_matriz.py` / `main_higyrus.py`
- `.planning/REQUIREMENTS.md ### Live re-verification (LIVE)` — LIVE-01 acceptance criteria

### Existing harness infrastructure (READ-ONLY for context)
- `verification/findings.py` — 494 LOC; ya tiene `_parse_findings`/`_serialize_findings`/`append_finding` con preservation path "status humano"; el módulo source-of-truth para HARN-07
- `verification/baselines/phase-06-baseline.txt` — snapshot textual de Phase 6 (referencia para LIVE-01 acceptance)
- `verification/CYCLE-REPORT.md` — open questions log; el planner debe extender Q#6 con HARN deferred items
- `.planning/todos/pending/matriz-driver-findings-file-handling.md` — root cause analysis + fix sketches para HARN-08/09/10 (FOLDED en scope)

### Phase 5 v1.0 baseline (LIVE-01 reference)
- Git commit `4d48e07` "docs(05): baseline DRIFT-02 cycle closure (verification-cycle-2026-Q2)" — canonical findings files baseline por paquete
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — deferred items context (4 quedan, todos resolved en v1.1)
- `.planning/phases/05-matriz-verification/` (archivado en v1.0) — Phase 5 SUMMARYs con el contexto original de los FINDINGs F-01..F-09

### Carry-forward invariants de Phases v1.1 (deben seguir GREEN post-Phase 11)
- `.planning/phases/06-compat-safety-net-client-class-skeleton/` — Pitfall #1 fixture-reaches-production guard
- `.planning/phases/07-core-py-extraction-sync-async-logic-dedup/` — import-linter contracts (`_core.py` no importa transport)
- `.planning/phases/08-retries-backoff-structured-logging/` — Pitfall #4 mutation gate (`idempotent=False`) + RedactingFilter + B8 lock-in
- `.planning/phases/09-deferred-bug-fixes/` — BUG-01..04 regression tests
- `.planning/phases/10-matriz-aio-py-creation-tokenstore/10-VALIDATION.md` — 39/39 SECURED + paridad sync↔async live; matriz async surface NO se re-toca

### Spike findings (auto-loaded; relevante si HARN-* requiere concurrency primitive — improbable)
- `.claude/skills/spike-findings-market-libs/SKILL.md` — TokenStore + RefreshPolicy patterns

### Deferred items log
- `.planning/v1.1-INTEGRATION-CHECK.md` — integration check pending v1.1 close
- `.planning/v1.1-MILESTONE-AUDIT.md` — milestone audit pending v1.1 close (Phase 11 outputs feed este audit)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`verification/findings.py::append_finding`** ya tiene "preservation path (status humano)" via `_parse_findings` parser. Extender este path con BEGIN/END markers es ~50 LOC delta; full rewrite NO es necesario.
- **`verification/findings.py::_serialize_findings`** ya separa Index table + per-finding sections con headers consistentes — la zona auto-generada está bien delimitada estructuralmente; los markers explícitos son contract documentation, no nuevo behavior.
- **`packages/matriz-client/src/matriz_client/_logging.py::RedactingFilter`** + 4× package loggers (Phase 8 LOG-02): los CR fixes NO deben emitir nuevos log records que esquiven el filtro; usar `logger.warning("...", extra={...})` estándar.
- **`main_matriz.py` sweep helper `_envelope_probe`** (Phase 7 CR-05): si CR-01 o CR-04 fixes requieren tocar sweep probes, usar el helper existente — NO reintroducir boilerplate duplicado.
- **`packages/*/tests/conftest.py` autouse fixtures** (Phase 7 / Phase 10): los regression tests CR-07 (event_hooks) deben usar `_configure_sync` / `_configure_async` para no recrear state setup.

### Established Patterns

- **Per-CR atomic commits** (Phase 8 precedent): `feat(11-XX): CR-NN fix — <one-liner> (close-out v1.1)` con bullets del test + the fix en commit body. Phase 8 commits `745503c` (CR-01) + `625cb55` (CR-02) son los templates.
- **RED commit before GREEN para thread-safety / multi-site changes** (Phase 8 D-21 / Phase 9 D-04): CR-07 + CR-06 siguen este patrón.
- **Append-only verification cycle** (Phase 5 D-08): los `<pkg>-findings.md` NUNCA se sobreescriben; la regression test de HARN-07 debe verificar esto con N re-runs vs estado inicial (assertion: post-N-runs SHA256 == post-1-run SHA256).
- **`_core.py` import-linter contract** (Phase 7 D-05): los fixes en drivers (`main_*.py`) NO deben importar de `_core` directamente (pre-existing contract); usar la API pública del package.
- **Mutation gate Pitfall #4 (Phase 8)**: cualquier fix en `main_matriz.py` que toque order endpoints debe preservar `idempotent=False` — verificable con `grep "idempotent=False" main_matriz.py` antes/después del commit.

### Integration Points

- **Plan harness (A) + Plan CR (B) ambos tocan `main_matriz.py`**: el planner debe declarar `files_modified: [main_matriz.py]` en ambos plans; execute-phase intra-wave overlap check serializa la wave 1 si detecta overlap (sin riesgo de race condition en worktrees).
- **Plan LIVE-01 (C) consume los outputs de A+B**: los 4 drivers ejecutan con `findings.py` post-HARN; las regresiones detectables por LIVE-01 son las de A o B, no nuevas.
- **CI green-gate dependency:** los 4 paquetes deben tener tests green ANTES de correr LIVE-01 (Phase 10 closure ya garantiza esto; Plan B regression tests no deben reducirlo).
- **`.claude/skills/spike-findings-market-libs/sources/*` ruff errors (108 pre-existing):** Phase 11 housekeeping debe agregar `extend-exclude` a `pyproject.toml [tool.ruff]` O reformatear los spike sources; sin esto el CI lint job sigue rojo y bloquea `CI green final` (success criterion #5).

</code_context>

<specifics>
## Specific Ideas

- **HARN-10 fix sketch del todo:** `if "prod-vs-remarkets divergence acknowledged" not in path.read_text(): append_finding(...)` — driver-side guard. Alternativa: extender `append_finding` con `idempotent_by_title=True` flag (preferred por symmetry — funcionaría para los 4 drivers).
- **HARN-09 regression test contract:** "N veces re-run vs estado inicial" sugerido en el todo. Implementación: pytest fixture que (a) commit canonical state con operator fields presentes, (b) run driver 3 veces, (c) assert SHA256 file == initial SHA256.
- **CR-07 alternative implementations:** ROADMAP cita "lock OR per-request hook injection". Per-request hook injection es preferred (no shared state mutation cross-event-loop), pero requiere refactor más invasivo. El planner decide based on minimal blast radius.
- **CR-06 multi-site:** ≥20 sites entre `main_matriz.py` + `main_higyrus.py` — el task probablemente se split en 2 commits (uno por archivo) para granularidad. El plan PLAN.md debe especificar.
- **Spike artifacts housekeeping:** opción A `extend-exclude = [".claude/skills/spike-findings-market-libs/sources/**", ".planning/spikes/**"]` (preferred — 1-line change). Opción B reformat las 108 ruff errors (mayor delta, mayor riesgo de cambiar contenido educational).

</specifics>

<deferred>
## Deferred Ideas

[None mentioned in this discussion — scope stayed clean.]

### Reviewed Todos (not folded)
[None — el único todo con score >= 0.4 fue folded above.]

</deferred>

---

*Phase: 11-harness-hardening-code-review-close-out-live-re-verification*
*Context gathered: 2026-06-14*
