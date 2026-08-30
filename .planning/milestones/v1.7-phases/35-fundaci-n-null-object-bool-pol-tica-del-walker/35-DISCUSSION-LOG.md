# Phase 35: Fundación Null Object — `__bool__` + política del walker - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-28
**Phase:** 35-fundaci-n-null-object-bool-pol-tica-del-walker
**Mode:** assumptions
**Areas analyzed:** Mecanismo del walker (NOBJ-02), Superficie de las bases SafeModel (NOBJ-01), Gates/snapshots/hash canónico, Blast radius de tests

## Assumptions Presented

### Mecanismo del walker (NOBJ-02)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Disposición por anotación sola; edit = borrar `sink(...)` en 2 sitios (lista gateado a `value is None`) | Confident | `matriz_client/_decode.py:434-440`, `:442-445`, `:482-484`, `:363-367` |
| `strict_decode` cae solo — único choke point, sin código nuevo | Confident | `_decode.py:205-221` |
| non_dict top-level y eje mapping quedan sin tocar; null-elemento-de-lista se silencia con la misma regla | Likely | `_decode.py:575-582`, `matriz_client/models.py:145-156`, tests pineados en `test_decode.py` |

### Superficie de las bases SafeModel (NOBJ-01)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 4 jerarquías a tocar; ámbito/wallets no ganan base (models.py vacíos por decisión) | Confident | docstrings de `ambito…/models.py:1-27`, `wallets…/models.py:1-27`; roster en `check_decode_intactness.py:188-206` |
| `__bool__ = self != type(self).empty()` funciona hoy: probe sobre 52 clases, 0 mismatches | Confident | probe ejecutado en vivo; frozen dataclasses = igualdad estructural |
| `empty()` necesita 2 formas (mapping pass en market-data/matriz); prohibido `cls.from_api(None)` | Likely | `matriz…/models.py:238-250`, `market_data…/models.py:220-222`, T-29-33 |
| `UnknownFrame` necesita disposición explícita (no hereda `_SafeModel`) | Confident | `matriz…/models.py:504-530`, union `PrimaryWsMessage:533` |

### Gates, snapshots y hash canónico

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 4 gates verdes hoy; solo intactness se mueve (bump de digest); comentarios hasheados, docstrings no | Confident | los 4 gates corridos en vivo; `check_decode_intactness.py:222`, `:402-469`, `:76-82` |
| Snapshots byte-idénticos sin esfuerzo (formato no enumera métodos); asertar por git diff (verification/ no corre en CI) | Confident | `verification/test_public_surface.py:104-122`, `snapshots/*.txt` |

### Blast radius de tests

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Criterio 4 no puede ser literal: 10 aserciones (2 tests × 5 paquetes) contradicen la nueva disposición; su inversión = evidencia de falsificación del criterio 2 | Confident | greps con file:line en los 5 `test_decode.py` |
| Pisos de 29-SIZING.md bajan; registrar triples retirados (35 campos) para Phase 39 | Likely | `29-SIZING.md:302-304`; enumeración en vivo de campos no-opcionales |
| Criterio 5 ya es verdadero; solo pinearlo con test con la forma de los alias 36-38 | Confident | probe `get_type_hints()` + `@property` + `slots=True` ejecutado |

## Corrections Made

No corrections — all assumptions confirmed ("Sí, proceder"). Las dos decisiones abiertas se
resolvieron con la opción recomendada, explicitada en la pregunta de confirmación:
- Criterio 4 rescopeado a tests de superficie pública (D-13).
- `UnknownFrame` gana `__bool__` a mano (D-08).
- Null como elemento de lista se silencia con la regla uniforme (D-04).

## External Research

None — todo se resolvió contra el working tree, los artefactos archivados de la Phase 29 y probes
en vivo.
