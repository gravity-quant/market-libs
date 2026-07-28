# Phase 12: Codegen Spike - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 12-codegen-spike
**Areas discussed:** Spike experiment scope

---

## Area Selection (multi-select gate)

| Option | Description | Selected |
|--------|-------------|----------|
| Spike experiment scope | ¿Qué paquetes corren el spike end-to-end? Cambia el time-budget del spike y la confianza de la decisión. | ✓ |
| GO decision rigor | Beyond el byte-identical modulo ruff format, ¿qué evidencia adicional setea GO? | (Claude's discretion) |
| NO-GO contingency: libcst here or v1.3? | Si unasync da NO-GO en ámbito, ¿evaluamos libcst en el mismo spike o cerramos NO-GO + dejamos libcst exploration para v1.3? | (Claude's discretion) |
| Spike artifact + wrap-up pattern | ¿Seguir el pattern v1.1 Phase 10 (`.planning/spikes/SPIKE-XXX-codegen/` + Skill auto-cargada) o lighter pattern? | (Claude's discretion) |

**User's choice:** Solo `Spike experiment scope`. Las otras 3 áreas se delegan a Claude's discretion siguiendo patrones v1.1 Phase 10.

---

## Spike experiment scope

### Sub-decision A: Package coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Ámbito round-trip + matriz construct audit | Mínimo del ROADMAP. Ámbito canary; matriz audit en papel. iol+higyrus inferidos. Fastest. | ✓ (Recommended) |
| Ámbito + matriz ambos round-trip | Más rigor. Ámbito round-trip + matriz round-trip 852 LOC. iol+higyrus inferidos. | |
| Los 4 packages round-trip | Máxima confianza. Cost ~3-4x. Borra límite spike vs implementación. | |

**User's choice:** Ámbito round-trip + matriz construct audit (mínimo del ROADMAP, Recommended).

**Captured as:** D-SCOPE-01

### Sub-decision B: Matriz construct audit depth

| Option | Description | Selected |
|--------|-------------|----------|
| Enumeration + manual proof | Enumerar TODOS los async-only constructs, cada uno (a) deny-list yes/no, (b) si no deny-list → sync equivalent verificado. Cero constructs sin clasificar. | ✓ (Recommended) |
| Enumeration solo (papel) | Listar + flag deny-list. Constructs no-deny-list quedan TBD para Phase 16. Más rápido, más riesgo. | |
| Full round-trip de matriz | Correr unasync con deny-list configurada. Trade-off: si matriz no round-trippea, decisión bloqueante. | |

**User's choice:** Enumeration + manual proof (Recommended).

**Captured as:** D-SCOPE-02

### Sub-decision C: Time-budget cap

| Option | Description | Selected |
|--------|-------------|----------|
| 1 día | Si después de ~1 día no converge a GO claro → NO-GO automático. Patrón v1.1 Phase 10 spikes. Mantiene velocity. | ✓ (Recommended) |
| 2 días | Más buffer. Riesgo: extiende v1.2 (v1.1 tomó 3.5 días). | |
| Sin cap explícito | Spike corre hasta converger. Riesgo: rabbit hole. Contradice spike philosophy. | |

**User's choice:** 1 día (Recommended).

**Captured as:** D-SCOPE-03

---

## Claude's Discretion

### GO decision rigor (D-RIGOR-01)

Operator delegó por default. Decisión tomada: el spike report DEBE presentar 8 evidence items
(byte-identical + B8 identity + ruff format + ruff check + mypy strict + suite ámbito green +
import-linter contracts unbroken + `@generated` marker compatible con `from __future__ import annotations`)
antes del GO signoff. Matches v1.1 Phase 10 rigor.

### NO-GO contingency (D-NOGO-01, D-NOGO-02)

Operator delegó por default. Decisión tomada: si unasync NO-GO → cerrar spike + defer libcst a v1.3.
NO extender Phase 12 para evaluar libcst inline (rompería el 1-day cap, scope creep al milestone).
Close-out artifacts: NO-GO.md + REQUIREMENTS.md/ROADMAP.md updates difiriendo REFAC-06 a v1.3 +
pending todo `spike-codegen-libcst-v1.3.md` capturando scope futuro.

### Spike artifact + wrap-up pattern (D-ARTIFACT-01..03)

Operator delegó por default. Decisión tomada: pattern v1.1 Phase 10 carry-forward exacto.
Spikes viven en `.planning/spikes/SPIKE-005-codegen-tool-choice/`; wrap-up vía `/gsd-spike --wrap-up`
produce nuevo project-local skill `spike-findings-codegen-market-libs` auto-cargado en CLAUDE.md.
Phase 16 consume el skill. Phase 12 SUMMARY.md cierra el phase con link al spike + skill.

### Heredadas (no se re-discuten)

- Source-of-truth direction = async-first (`aio.py` → `client.py`). Locked por SUMMARY.md research.
- Tool primario = unasync; fallback = libcst (deferred a v1.3 per D-NOGO-01).
- Codegen deny-list matriz = `_token_store.py` + `_refresh_policy.py` + `ws_client.py`. Locked por ARCHITECTURE research.
- Per-package serial Phase 16 = ámbito → iol → higyrus → matriz. Locked por v1.0/v1.1 pattern.
- Operational pre-gate = v1.1 head `71bf201` CI-green en Python 3.13 antes de Phase 12 start.

## Deferred Ideas

- libcst exploration → v1.3 spike (capturado como pending todo si NO-GO).
- Driver migration codegen (`main_*.py`) → fuera de scope; v1.2 Phase 15 manual migration.
- Per-package Rule completeness iol+higyrus+matriz → Phase 16 cristaliza.
- CI `lint-codegen` job + pre-commit hook setup → Phase 16 deliverables.
- Codegen para `_core.py` → `_core.py` ya es single-source desde v1.1 Phase 7; defer permanente.
- Generated-code parity tooling más allá de unasync (Jinja2, custom AST) → research ya los rechazó.
