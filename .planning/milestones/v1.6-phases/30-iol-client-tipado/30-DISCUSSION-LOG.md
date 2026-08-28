# Phase 30: `iol-client` tipado - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-19
**Phase:** 30-iol-client-tipado
**Mode:** assumptions
**Areas analyzed:** Diseño de modelos, Wiring _core/decoder, Migración driver+harness, Gates/RED/release

## Assumptions Presented

### Diseño de modelos
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 4 dataclasses sobre 2 formas wire; SafeModel template = higyrus (mínimo, 14 líneas); `Cotizacion` unificada quote+histórico | Likely | `.planning/verification/schemas/iol-client/get-quote.json` = `get-historical-quotes.json` (20 claves); `higyrus_client/models.py:41-54`; `iol_client/_decode.py:140` POLICY typed-zeros |
| `puntas` = `list[Punta]` en Cotizacion / `Punta` singular en Titulo; 4 campos float | Unclear | 3 formas registradas: `[]` (elemento inobservado), objeto 4-float, `NoneType`; único candidato con evidencia |
| Campos `NoneType` del corpus → `T \| None` | Confident | `_decode.py:436-442` Optional sin sink; clase S-5 de F29 ruteada a F33 |
| `cantidadOperaciones` int en Cotizacion / float en Titulo (per-modelo) | Confident | corpus por endpoint |

### Wiring _core/decoder
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 4 parsers reescritos in place con `@_decode._response_parser` | Confident | dedupe DecodeScope per-response (`_decode.py:286-324`); patrón `higyrus_client/_core.py:457-500`; import-linter sin contrato nuevo |
| Envelope `titulos` no se modela; `get_instruments` gana guard `isinstance(raw, list)`; ~12 tests re-mockeados a lista | Likely | `_core.py:354-360`; schema real = lista top-level; 12+ mocks dict en 6 archivos de tests |

### Migración driver+harness
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 2 sitios de atributo (`main_iol.py:316`, `:395`) + ≥5 sitios `schema_of` que requieren `to_dict()` | Confident | `verification/schema.py:34-41` reduce objeto a nombre de clase; baselines committeados en `:1164`/`:1182` |
| `to_dict()` = `dataclasses.asdict(self)` recursivo | Likely | primer to_dict de response-model; los de market-data son request models; asdict recurre nested dataclasses |

### Gates/RED/release
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Intactness gate sin cambios; regenerar surface snapshot; ruff sin exención N | Confident | `tools/check_decode_intactness.py:175-181,217`; `verification/test_public_surface.py:153-165`; `pyproject.toml:52-70` |
| Fixture RED en `packages/iol-client/tests/` vía `# type: ignore[attr-defined]` + `warn_unused_ignores` | Likely | `ci.yml:85-94` typechequea tests; mypy `files`=`packages/*/src` (main_iol.py fuera); `pyproject.toml:87` |
| Sin bump de versión (F34); changelog `### v0.3.0` en README; fix del README ficticio en el mismo commit | Likely | ROADMAP asigna bump a F34; precedente `market-data-client/README.md:123-193`; README iol documenta API inexistente |

## Corrections Made

No corrections — all assumptions confirmed ("Sí, proceder").

## External Research

None performed — codebase evidence sufficient. Gap real pero live-only: elemento de `puntas` en `get_quote` (captura vacía), ruteado a F33.
