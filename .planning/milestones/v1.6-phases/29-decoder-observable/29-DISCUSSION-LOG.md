# Phase 29: Decoder observable - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-18
**Phase:** 29-decoder-observable
**Mode:** assumptions
**Areas analyzed:** Motor del decoder, Topología de copia, Portador del modo estricto, Registro de divergencia + RedactingFilter, Reconciliación de semánticas, Corrida de sizing, D-lock Literal RESPONSE

## Assumptions Presented

### Motor del decoder (D-lock a)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| stdlib-only un-motor; D-lock msgspec firmado NO-GO | Likely | msgspec cero hits en `uv.lock` + todos los `pyproject.toml`; sin benchmarks ni requisito de perf en el repo; verificación msgspec previa no cubre matriz (18 frozen, 0 slots) |

### Topología de copia
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Helper verbatim en 5 paquetes; wallets con exención documentada | Confident | wallets sin `_logging.py`/`_state.py`/`_core.py`/`models.py`/`tests/test_logging.py`; solo 5 copias de cada sustrato existen |

### Portador del modo estricto
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `strict_decode` en `_ClientState` + ContextVar `.set()` sin reset al tope de `_request` | Confident | Precedente D-14 en market-data `_state.py:100-107`; `_request` retorna antes del decode (`client.py:450-451`) — un reset haría strict no-op |
| ws_client daemon thread necesita propagación explícita, no herencia | Confident | `ws_client.py:90-93` decodifica en el thread (línea 184) sin pasar por `_request`; thread nuevo = Context vacío; `contextvars` cero hits en el repo |

### Registro de divergencia + RedactingFilter
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Fix del filter dos-partes; el contrato type-not-value carga la garantía | Confident | Cuerpo de `filter` byte-idéntico ×5; `isinstance(value, str)` saltea dicts; markers literales anclados; `_redact` regex marker-anchored |
| Vocabulario derivado de `schema_of` + compatible con `findings.py` | Likely | `verification/schema.py:24-30` ya implementa claves+tipos-nunca-valores; `safemodel_diff` duck-typed cross-package |

### Reconciliación de semánticas
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Tabla 6-way sobre `from_api` (+2 `empty()`), no 3-way | Confident | 6 `def from_api` en el grep: 2 SafeModel base no-byte-idénticos, `MarketDataSnapshot` firma extendida, `Symbol` pre-proceso, matriz `_SafeModel`, `UnknownFrame` raw; 872 tests merge gate |

### Corrida de sizing
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Corpus re-basado en `.planning/verification/schemas/` (43 JSON type-only); piso keyset/tipo | Confident | `verification/snapshots/` = 4 `.txt` de superficie sin payloads; `captures/` vacío |

### D-lock Literal RESPONSE
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| D-lock 4b behaviorally-free para matriz | Confident | 9 aliases `Literal` en `types.py` pasan sin validar por el `return value` final de `_convert` |

## Corrections Made

### Motor del decoder (D-lock a)
- **Original assumption:** Firmar el D-lock stdlib-only NO-GO con la ausencia de requisito de perf como evidencia.
- **User correction:** **Spike de timing en fase** — la Phase 29 incluye un micro-benchmark descartable (walker vs `msgspec.convert()` sobre payloads sintéticos representativos) y el D-lock se firma con esos números como evidencia del lado pro-msgspec.
- **Reason:** El criterio 4 exige evidencia de ambos lados; el operator prefirió números medidos a una declaración de ausencia de requisito.

Las otras 8 suposiciones fueron confirmadas sin cambios ("Sí, proceder").

## External Research

No se spawneó agente de research externo. Los 3 topics flaggeados por el analyzer se resolvieron así:
- Evidencia pro-msgspec → resuelto por la corrección del operator (spike de timing in-fase).
- Cobertura de wheels msgspec por plataforma → condicional a un GO del spike; queda como ítem del spike si aplica.
- Freshness de los schemas (~2.5 meses iol) → documentado en D-08 como caveat del piso; re-captura diferida a F33.
