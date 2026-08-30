# Phase 36: `market-data-client` — `market_data` tipado + revocación de la Fase 33 - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-29
**Phase:** 36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-33
**Mode:** assumptions
**Areas analyzed:** Modelos nuevos + alias (D-NO-05), Reversión SC-2 + baja de la maquinaria de
mapping, `test_snapshot_no_data_row.py`, Versionado, `LatestRequest.entries`

## Assumptions Presented

### Modelos nuevos + alias (D-NO-05)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 3 clases nuevas (`BookLevel`, `EntryValue`, `MarketDataEntries`), copia local del patrón matriz | Confident | `packages/market-data-client/tests/test_null_object.py:191-201,217-226` — fixture ya escrito, comentario "The exact shape Phase 36 introduces" |
| Alias `@property` simples sin caché | Confident | `test_null_object.py::test_property_aliases_are_invisible_to_get_type_hints` |
| Roster de escalares = solo las 10 claves observadas (`BI,CL,HI,LA,LO,OF,OI,OP,SE,TV`), no el set completo de matriz | Likely | `.planning/verification/schemas/market-data-client/get-market-data.json` (captura Phase 33) |

### Reversión SC-2 + baja de la maquinaria de mapping

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `entries`/`market_data` vuelven a non-Optional; walker colapsa null silenciosamente | Confident | `_decode.py:436-506`; `models.py:259` dice explícitamente "Phase 36 retires this paquete's mapping machinery outright" |
| `_mapping_value`/`_apply_mapping_policy`/`_is_mapping`/`_strip_optional` + tests de precondición se eliminan enteros | Confident | grep de todos los call sites — sin otro uso |
| `LatestRequest.entries` vuelve a `list[str] = field(default_factory=list)`; `to_dict()` sigue omitiendo la clave si vacía | Likely | `to_dict()` actual ya omite `None`-valued optionals; sin evidencia del comportamiento real del servidor ante `"entries": []` explícito |

### `test_snapshot_no_data_row.py`

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `is None` → `== []` / `bool(...) is False`; `staleness_seconds` sin cambios | Confident | Roadmap SC4 ("mismo poder expresivo sin `None`") |

### Versionado

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Sin bump de versión ni publicación en esta fase — diferido a Phase 40 | Confident | ROADMAP Phase 40 goal; REQUIREMENTS.md mapea `PUB-NOBJ-01` a Phase 40; precedente v1.6 (Phase 30 → Phase 34) |

## Corrections Made

No corrections — todas las asunciones confirmadas ("Sí, proceder").

## External Research

No se realizó investigación externa — el codebase (incluidos los comentarios forward-looking
dejados deliberadamente por Phase 35) y el plan fuente `.future_plans/api-tipada-null-objects.md`
proveyeron evidencia suficiente para todas las áreas.
