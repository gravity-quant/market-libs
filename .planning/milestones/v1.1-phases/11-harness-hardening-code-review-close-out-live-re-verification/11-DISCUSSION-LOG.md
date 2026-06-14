# Phase 11: Harness Hardening + Code Review Close-out + Live Re-verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 11-harness-hardening-code-review-close-out-live-re-verification
**Areas discussed:** Code Review fix grouping (3 questions); Claude's discretion accepted for the other 3 gray areas (waves structure, `findings.py` architecture, LIVE-01 baseline + acceptance)

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Estructura de waves (workstream ordering) | A→B→C secuencial vs A∥B → C vs per-package serial | |
| `findings.py` append-only architecture | Extend existing vs BEGIN/END marker vs hybrid | |
| LIVE-01 baseline + acceptance bar | What's canonical baseline + what counts as regression | |
| Code Review fix grouping (CR-01/02/04/06/07/08) | 6 fixes in 2 files con severidades mixtas | ✓ |

**User's choice:** Discutir solo "Code Review fix grouping"; aceptar defaults para los otros 3.

---

## Code Review Fix Grouping

### Question 1: Granularidad de plans

| Option | Description | Selected |
|--------|-------------|----------|
| 1 mega-plan, 6 tasks atómicos | Un solo plan con 6 commits atómicos por CR | ✓ |
| 2 plans agrupados por archivo | Plan A matriz + Plan B higyrus; paralelizable | |
| 6 plans (uno por CR) | Máxima granularidad; máxima rollback | |
| Otro | Operator-described alternative | |

**User's choice:** 1 mega-plan, 6 tasks atómicos.
**Notes:** Patrón consistente con Phase 8 CR fixes (commits `745503c` + `625cb55` por CR).

### Question 2: Política de regression tests

| Option | Description | Selected |
|--------|-------------|----------|
| Per-CR test gating proporcional | Test severity-matched: RED first para CR-07/06; mocked para CR-01/02/04; ruff para CR-08 | ✓ |
| Per-CR test gating uniforme | RED-GREEN estricto para los 6 incluido CR-08 | |
| Batch verify al final del plan | Fixes separados, tests en commit final | |
| Otro | Operator-described alternative | |

**User's choice:** Per-CR test gating proporcional.
**Notes:** Cost-benefit balance — CR-08 line-length cosmetic no merece RED test scaffolding.

### Question 3: Orden de los 6 tasks

| Option | Description | Selected |
|--------|-------------|----------|
| Risk-first: CR-07 → CR-06 → CR-04 → CR-02 → CR-01 → CR-08 | Hard-first detección temprana | ✓ |
| Per-file: matriz first (CR-01/02/04/06-matriz) → higyrus (CR-06-higyrus/07/08) | Contexto file-local | |
| Easy-first: CR-08 warm-up → CR-01/02/04 → CR-06 → CR-07 | Confidence-building | |
| Otro | Operator-described alternative | |

**User's choice:** Risk-first.
**Notes:** Si CR-07 (thread-safety) revela un issue estructural más profundo, lo descubrimos antes que CR-08 (cosmetic) consuma ciclos.

---

## Claude's Discretion (3 áreas no discutidas, defaults aceptados)

### D-WAVE-01: Estructura de waves
- **Default:** Wave 1 (Plan harness HARN-07..10 ∥ Plan CR mega-plan) → Wave 2 (Plan LIVE-01 × 4 paquetes)
- **Rationale:** ROADMAP dice "harness changes pueden empezar en paralelo"; LIVE-01 es gate final; 3 plans / 2 waves balancea velocidad y aislamiento.
- **Riesgo identificado:** Plan harness y Plan CR tocan ambos `main_matriz.py` → execute-phase intra-wave overlap check serializa si declara `files_modified` overlap.

### D-HARN-01: `findings.py` append-only architecture
- **Default:** HÍBRIDO — extender `_parse_findings`/`_serialize_findings` existentes + BEGIN/END markers explícitos
- **Rationale:** ROADMAP SC#1 + minimum blast radius + alineado con docstring existente "no pisar status promovidos por humano"
- **Migration:** los 4 findings files existentes requieren task de inyección de markers preservando contenido current

### D-LIVE-01: Baseline + acceptance bar
- **Default:** Baseline = `4d48e07` "verification-cycle-2026-Q2" commit (Phase 5 close-out) + acceptance = operator-gated (cada NEW FINDING requiere disposition)
- **Rationale:** Consistente con Phase 9 BUG-02 NO-FIX pattern (override en frontmatter)
- **Regresión bloqueante (sin operator decision):** wire URL changes sync vs async, probe outcome flips para findings pre-baseline, credential leaks en logs

---

## Folded Todos

- **`matriz-driver-findings-file-handling.md`** (score 0.6, `resolves_phase: 11` en frontmatter) → folded into HARN-08/09/10 scope. Document source-of-truth con root cause analysis + fix sketches.

## Deferred Ideas

None — scope stayed clean. No scope creep durante la discusión.
