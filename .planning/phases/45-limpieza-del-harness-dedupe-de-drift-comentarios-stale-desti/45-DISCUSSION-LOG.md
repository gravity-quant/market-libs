# Phase 45: Limpieza del harness — dedupe de drift, comentarios stale, destino de `verification/` de matriz - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-09-01
**Phase:** 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
**Mode:** assumptions
**Areas analyzed:** HARN-01 (mecanismo de dedupe, alcance de sitios, reorder de fid +
falsificación), HARN-03 (comentario stale + IN-06 + retiro IN-05), HARN-04 (destino de
`verification/` de matriz), Alcance (`DRV-MD-SEG-43` fold-in), Alcance (los 40 locks inertes de
`verification/`)

## Assumptions Presented

### HARN-01 — mecanismo de dedupe
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Dedupe intra-run únicamente (no título content-addressed cross-run) | Unclear (recomendación) | `PITFALLS.md:349-384` Pitfall 9; el problema medido (22 bloques / 8 snapshots) es de un run de dos pases, resuelto por completo con dedupe intra-run |

### HARN-01 — alcance de sitios
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Los 5 sitios "schema drift" nombrados en el backlog | Confident | `ROADMAP.md:281` `HARN-DRIFT-33`, `STACK.md:196-204` (tabla AST-measured) |
| Incluir además los 2 sitios hermanos "type drift" de `main_iol.py` (:1617, :1685) | Unclear (recomendación) | `STACK.md:204` — "the phase should consciously include or exclude rather than miss"; mismo hazard de título libre de contenido verificado por lectura directa del código |

### HARN-01 — reorder de fid + falsificación
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `_next_fid()` se mueve a después de la decisión de dedupe en los 7 sitios; nunca relajar P-3 | Confident | `PITFALLS.md:387-406` Pitfall 10; `verification/findings.py:583-700`, `main_market_data.py:511-512` (orden actual medido: fid antes del append) |

### HARN-03
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `330`→`336` en `tools/check_surface_types.py:47,58`; IN-06 cerrado agregando `test_public_surface.py` al allowlist de `ci.yml`; IN-05 retirado | Confident | Grep directo de las líneas 47/58; `matriz_client/__init__.py:186` ya tiene `__version__` (medido en HEAD); `.github/workflows/ci.yml:81-92` no incluye `test_public_surface.py` (medido) |

### HARN-04 — destino de `verification/` de matriz
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Aceptar como deuda formalmente documentada (no reparar) | Unclear (recomendación) | `PITFALLS.md:439-476` Pitfall 12; corrida real: 19 failed / 19 errors / 3 passed en los 2 archivos, causa única (firmas pre-REFAC-05); reparar re-derivaría mocks sobre comportamiento ya verificado en vivo en 4 milestones |

### Alcance — `DRV-MD-SEG-43`
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Fold-in explícito en esta fase | Unclear (recomendación) | `44-CONTEXT.md:83-88` D-06 lo difirió explícitamente a la Phase 45; `43-DISPOSITION.md § 5`; verificado en HEAD que `main_market_data.py:1541-1542` sigue dereferenciando `Segment.marketSegmentId`, campo removido por Phase 43 |

### Alcance — los 40 locks inertes de `verification/`
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Enrolar sólo lo que HARN-01/03/04 tocan directamente; re-declarar el resto (~33-35) como inerte y fuera de alcance, no disponer los 40 individualmente | Unclear (recomendación) | `41-ROLLUP.md:160-276` — 52 en disco, 12 enrolados, 40 declarados inertes y ruteados a esta fase; `REQUIREMENTS.md § Out of Scope` ya excluye el enrolamiento mypy completo por el mismo principio; `PITFALLS.md` advierte contra enrolamiento en bloque |

## Corrections Made

Ninguna — el operador seleccionó "Yes, proceed" sobre el set completo, incluidas las
recomendaciones marcadas "Unclear (recomendación)" arriba, que quedan grabadas como decisión en
`45-CONTEXT.md` D-01/D-02/D-08/D-09/D-10.

## Auto-Resolved

No aplica — no se usó `--auto`.

## External Research

No se despachó un agente de investigación externa en esta sesión: toda la evidencia necesaria
ya estaba first-party en el repo (`ROADMAP.md`, `REQUIREMENTS.md`, y la investigación de
milestone `.planning/research/{STACK,FEATURES,PITFALLS}.md`, producida 2026-08-31
específicamente para v1.8 e incluyendo HARN-01..04 con mecánica citada por archivo y línea). No
se detectaron gaps que requirieran research nuevo.
