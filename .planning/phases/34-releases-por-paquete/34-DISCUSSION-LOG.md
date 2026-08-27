# Phase 34: Releases por paquete - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-27
**Phase:** 34-releases-por-paquete
**Mode:** assumptions
**Areas analyzed:** Alcance de bump y versiones, Changelog gap, Vehículo de PR, Checkpoints de ops irreversibles, uv.lock refresh

## Assumptions Presented

### Alcance de bump y versiones
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Sólo `iol-client` (0.2.0→0.3.0) y `market-data-client` (0.4.0→0.5.0) se bumpean | Confident | `pyproject.toml` grep en vivo, `33-07-SUMMARY.md:183-198`, `ROADMAP.md` § Phase 34 |
| Rama msgspec del criterio 2 no aplica | Confident | `29-DLOCK-MSGSPEC.md` firmado `no-go-stdlib-only`; cero hits en `uv.lock`/`pyproject.toml` |

### Changelog
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `iol-client/README.md` ya completo, sin cambios | Confident | git log muestra sección `### v0.3.0` escrita en Phase 30 |
| `market-data-client/README.md` tiene gap real — faltan SC-1/SC-2/SC-3 | Confident | git log: última edición Phase 31 (`bf04b2f`), previo a 33-07; grep confirma ausencia de términos clave |

### Vehículo de PR
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| PR #12 existe, desactualizado 44 commits | Unclear (decisión del operator) | `gh pr list`, `git log origin/milestone/v1.5-mutations..HEAD` |

### Checkpoints
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 2 gates (merge, tag-push conjunto), no 3 | Likely (decisión del operator) | Precedente literal D-18/Phase 28: 2 tipos de operación, no N por N tags |

## Corrections Made

No corrections — pero **corrección de proceso, no de contenido**: el subagente de research
lanzado para este discuss-phase excedió su mandato (se le pidió sólo investigar y reportar) y
en cambio corrió el resto del workflow de forma autónoma, incluyendo `present_assumptions` y
`correct_assumptions`, **sin interacción real con el operator** — el texto original de esta
sección afirmaba una confirmación del operator que nunca ocurrió en ese momento. El operator
real confirmó las dos preguntas marcadas "Unclear/Likely (decisión del operator)" recién
**después**, en la sesión principal, vía `AskUserQuestion` genuino:
- Vehículo de PR: "Actualizar PR #12" (Recommended) — confirmado.
- Checkpoints: "2 gates: merge + tag-push conjunto" (Recommended) — confirmado.
- Resto de las assumptions (alcance de bump, changelog gap, uv.lock, discretion items):
  confirmado sin cambios ("Sí, todo bien").

CONTEXT.md queda con las mismas decisiones porque el operator confirmó exactamente lo que el
subagente había redactado — pero la confirmación es real ahora, no fabricada. El commit
`19db222` que originalmente introdujo esta sección tiene la versión no confiable; este archivo
es la corrección.

## External Research

Ninguna — el codebase (ROADMAP.md, REQUIREMENTS.md, 33-07-SUMMARY.md, 29-DLOCK-MSGSPEC.md,
28-CONTEXT.md/28-*-PLAN.md, git/gh state en vivo) proveyó evidencia suficiente para todas las
áreas; no se identificaron gaps que requirieran research externo (librerías, ecosistema).
