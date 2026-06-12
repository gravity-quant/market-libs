# Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 07-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 7-`_core.py` Extraction — Sync/Async Logic Dedup
**Areas discussed:** Shape de `_core.py`, Cierre CR-03 + CR-05, CI gates (import-linter + sentinel test), Plan slicing & métrica LOC, Endpoint group granularity, ámbito special case, Snapshot público preservation

---

## Shape de `_core.py`

### Question 1: ¿Qué fields tiene `RequestSpec`?

| Option | Description | Selected |
|--------|-------------|----------|
| Mínimo + idempotent forward-decl | Una sola dataclass cross-package: method/path/params/json_body/headers + idempotent=False forward Phase 8. matriz auth_basic opcional. | |
| Per-package shapes distintos | Cada paquete define su propio RequestSpec con fields propios. No shared internals. | ✓ |
| Generic Request dict | dict[str, Any] sin dataclass; más liviano pero sin type safety. | |

**User's choice:** Per-package shapes distintos — captured as D-01.
**Notes:** Consistent con project constraint "no shared internals between packages". Phase 8 RELY-03 (idempotent field) será replicado 4× independientemente.

### Question 2: ¿Cómo factorizamos el auth-flow?

| Option | Description | Selected |
|--------|-------------|----------|
| Builders+parsers puros | _core.build_login_request(state) → RequestSpec; transport hace HTTP; _core.parse_login_response(...) → tuple. _core.py 100% sin I/O. | ✓ |
| Inject request_callable | _core.do_login(state, request_fn). Menos funciones pero unión sync/async incomoda con mypy strict. | |
| Híbrido: builders+parsers + token_is_fresh puro | Mix de pure functions + transport orquesta. | |

**User's choice:** Builders+parsers puros — captured as D-02.

### Question 3: ¿Qué retorna `_request` (shell)?

| Option | Description | Selected |
|--------|-------------|----------|
| Devuelve httpx.Response cruda | Shell retorna Response; endpoint method llama _core.parse_X(resp). Cambia contrato actual de higyrus/matriz pero unifica las 4 surfaces. Phase 8 retry-friendly. | ✓ |
| Preservar contratos actuales | iol → Response, higyrus → dict|list|None, matriz → dict. Más back-compat, menos uniformidad. | |
| Devuelve typed result (parser inline) | _request_get_quote(...) → Quote directly. Sin parse_X layer. Choca con Phase 8 retry transport idea. | |

**User's choice:** Devuelve httpx.Response cruda — captured as D-03.

### Question 4: ¿Dónde aterrizan los helpers stateless (`_raise_for_response`, `_unwrap`)?

| Option | Description | Selected |
|--------|-------------|----------|
| Mover a _core.py + re-export shim | _core.raise_for_response / _core.unwrap fuentes únicas. client.py mantiene aliases module-level. Zero churn. | ✓ |
| Mover a _core.py sin shim | Tests y main_matriz.py se migran a `from <pkg>._core import unwrap`. Más limpio pero ~10 archivos por paquete. | |
| Dejar en client.py + _core.py los re-importa | Rompe success-criterion #1 (no imports de client.py/aio.py en _core.py). | |

**User's choice:** Mover a _core.py + re-export shim — captured as D-04.

---

## Cierre CR-03 + CR-05

### Question 1: CR-03 — ¿dónde se consume el body antes del raise?

| Option | Description | Selected |
|--------|-------------|----------|
| _core.parse_envelope_response(resp) absorbe todo | _core hace resp.read() + .json() + check status==ERROR. Body 100% consumido antes de raise. Futuro http2=True safe. | ✓ |
| Shell hace resp.read() explícito antes de raise | Decoupled pero requiere disciplina per call site. Riesgo de regresión en Phase 10. | |
| Usar `with http.send(...) as resp` context-manager | Idiomático pero churn significativo en shell pattern. | |

**User's choice:** _core.parse_envelope_response(resp) absorbe todo — captured as D-06.

### Question 2: CR-05 — ¿dónde aterriza `_envelope_probe`?

| Option | Description | Selected |
|--------|-------------|----------|
| Helper en main_matriz.py (driver-only) | Driver-local; otros drivers no necesitan el patrón. Preserva risk probes con envelope_key=None. | ✓ |
| Promover a verification/probes.py | Cross-package, anticipa adopción futura. Overhead: módulo más en harness. | |
| Inline en _core.py de matriz | Mezcla library helpers con driver helpers. Choca con success-criterion #1. | |

**User's choice:** Helper en main_matriz.py (driver-only) — captured as D-07.

### Question 3: ¿Refactor 18 probes atomic o incremental?

| Option | Description | Selected |
|--------|-------------|----------|
| Atomic en el plan matriz | 1 commit = matriz _core.py + _envelope_probe + 18 probes + snapshot guard. Revert atómico. | ✓ |
| Incremental (18 commits separados) | 1 probe a la vez, snapshot test pasa, commit. Forensic-grade pero pesado para PR. | |
| Plan separado (split CR-05 del plan matriz) | Plan A: matriz _core + CR-03; Plan B: CR-05 driver refactor. | |

**User's choice:** Atomic en el plan matriz — captured as D-08.

---

## CI gates — import-linter + cross-leak sentinel test

### Question 1: Mecanismo para bloquear `_core.py → client.py/aio.py` imports

| Option | Description | Selected |
|--------|-------------|----------|
| import-linter declarativo (.importlinter o pyproject.toml) | Library import-linter en dev deps. Reglas declarativas. Robusto, mypy-strict compat, escala. | ✓ |
| Grep CI rule en GitHub Actions | Cero deps nuevas. False-negatives con qualified imports + false-positives en comentarios. | |
| Test pytest que parsea AST | AST robust vs regex. Test code adicional. | |

**User's choice:** import-linter declarativo — captured as D-09.

### Question 2: ¿Dónde vive el cross-leak SYNC/ASYNC sentinel guard?

| Option | Description | Selected |
|--------|-------------|----------|
| verification/test_sync_async_isolation.py parametrizado | 1 archivo cross-cutting, parametrize sobre 4 paquetes. Alineado con verification/test_public_surface.py de Phase 6. | ✓ |
| 1 test por paquete en packages/<pkg>/tests/ | Más cercano al paquete protegido, pero replica boilerplate 4×. Phase 6 D-12 fixture-reaches-production usó esta forma. | |
| Extender verification/test_public_surface.py | Mezcla snapshot test con behavior test en mismo archivo. Churn semántico. | |

**User's choice:** verification/test_sync_async_isolation.py parametrizado — captured as D-10.

### Question 3: matriz aio.py REST stub — ¿cómo manejar el guard test?

| Option | Description | Selected |
|--------|-------------|----------|
| pytest.skip con motivo explícito | Visible en CI output, forward-tracked. Phase 10 plan re-habilita. | ✓ |
| Excluir matriz del parametrize | Más limpio pero olvidable en Phase 10. | |
| Test only-sync para matriz | Cierre parcial; mismo resultado neto que skip pero código activo. | |

**User's choice:** pytest.skip con motivo explícito — captured as D-11.

---

## Plan slicing & métrica LOC

### Question 1: Granularidad de planes

| Option | Description | Selected |
|--------|-------------|----------|
| 6 planes: 1 CI gate + 4 paquetes + 1 cross-leak test | Plan 1 = gates infra (tests-only). Plans 2-5 = ámbito → iol → higyrus → matriz. Plan 6 = CI green gate. | ✓ |
| 5 planes: 1 CI gate combo + 4 paquetes | CI green se valida como side-effect del Plan 5. Menos overhead, gate final menos explícito. | |
| 4 planes: 1 por paquete (gates en Plan 1 ámbito) | Plan ámbito carga gates infra que no son scope-ámbito. | |

**User's choice:** 6 planes — captured as D-12.

### Question 2: Orden serial de Plans 2-5

| Option | Description | Selected |
|--------|-------------|----------|
| ámbito → iol → higyrus → matriz | Canary ámbito, iol auth-flow complejo, higyrus URL quirks, matriz cierra con CR-03+CR-05. Idem Phase 6. | ✓ |
| iol → ámbito → higyrus → matriz | iol primero define auth-flow pattern. Más blast radius temprano. | |
| matriz primero (anti-canary) | Stress-test el patrón con el paquete más complejo primero. | |

**User's choice:** ámbito → iol → higyrus → matriz — captured as D-13.

### Question 3: Métrica LOC ≥30% drop

| Option | Description | Selected |
|--------|-------------|----------|
| Per-package vs Phase 6 post-refactor baseline | Cada plan SUMMARY.md incluye LOC drop client+aio agregado por paquete. ≥30% requerido. | ✓ |
| Agregado total (4 paquetes sumados) | Medida solo al final. Permite que ámbito tenga drop menor. Tarde para detectar regresión. | |
| Por endpoint group (≤30-50 LOC per group) | Métrica más estricta. Requiere taxonomía de endpoint groups. | |

**User's choice:** Per-package vs Phase 6 post-refactor baseline — captured as D-14. (La submétrica por endpoint group la captura D-05.)

### Question 4: Matriz plan atómico o split

| Option | Description | Selected |
|--------|-------------|----------|
| 1 plan atómico | Plan 5 matriz: _core + CR-03 + CR-05 + 18 probes + snapshot test guard + cross-leak skip update. 1 commit revertible. | ✓ |
| Split 5a (_core + CR-03) + 5b (CR-05 driver) | Más commits, scope cada uno más chico. Total Phase 7 = 7 plans. | |
| Split 5a (sin CR-03) + 5b (_core + CR-03 + CR-05) | Permite revert parcial si CR-03 introduce regresión live. | |

**User's choice:** 1 plan atómico — captured en D-08 + D-12 (consistente con Área 2).

---

## Endpoint group granularity

### Question 1: ¿Qué es un endpoint group?

| Option | Description | Selected |
|--------|-------------|----------|
| Sección de docstring del API | matriz §4 Segments / §5 Instruments / §6 Orders / §7 Market Data. higyrus Cuentas/Movimientos/Posiciones. iol Quotes/Instruments. Groups naturales del API. | ✓ |
| Por públicas method count (5-10 methods per group) | Mecánico pero menos semántico. | |
| No applies — métrica agregada per package | Ignorar la submétrica por endpoint group. Success-criterion literal queda sin medir explícito. | |

**User's choice:** Sección de docstring del API — captured as D-05.

---

## ámbito-financiero special case

### Question 1: ¿Refactor _core.py para ámbito o excluído?

| Option | Description | Selected |
|--------|-------------|----------|
| Incluir ámbito (full refactor) | Plan 2 canary. Parsing HTML/JSON duplicado. Drop ≥30% probable. Cumple success-criterion #1 literal. | ✓ |
| Excluir ámbito (skip Plan 2) | ámbito sin auth ni token-refresh, marginal value. Incumple "por cada paquete". | |
| Incluir ámbito con scope reducido | _core.py SOLO para parsers (no RequestSpec, no auth). Compromiso. | |

**User's choice:** Incluir ámbito (full refactor) — captured as D-15.

---

## Snapshot público preservation

### Question 1: ¿Cómo se trata `_core.py` en el snapshot público?

| Option | Description | Selected |
|--------|-------------|----------|
| _core.py NO entra al snapshot; re-export shims preservados | Phase 6 D-09: snapshot solo __all__ + signatures públicas. _core.py privado. Aliases `_raise_for_response` mantienen back-compat. Snapshot 1:1 vs Phase 6. | ✓ |
| Agregar _core.py al snapshot como módulo explícito | Documenta el módulo nuevo. Mismo argumento que Phase 6 NO usó para _state.py. | |
| Eliminar el _raise_for_response shim para forzar churn | Snapshot público cambia (entrada desaparece) — falla success-criterion 'no breaking change'. | |

**User's choice:** _core.py NO entra al snapshot; re-export shims preservados — captured as D-16.

---

## Claude's Discretion

Items dejados al planner basado en research + Phase 6 patterns:
- Estructura interna exacta de cada `_core.py` (orden, agrupación)
- Naming exacto de funciones builder/parser (`build_get_quote_request` vs `quote_request`)
- Ubicación exacta del snapshot test guard para 18 matriz probes (`verification/` vs `packages/matriz-client/tests/`)
- `pyproject.toml` vs `.importlinter` file para import-linter config (preferencia: pyproject.toml)
- Forward-decl de Phase 8 `idempotent` field en RequestSpec (preferencia: declarar ahora)
- Snapshot test mechanics para 18 matriz probes (pytest-httpx vs MockTransport, inline payloads vs JSON fixtures)
- Test cadence per plan (mismo idiom Phase 6 D-07)

## Deferred Ideas

Ver `<deferred>` en 07-CONTEXT.md:
- `_envelope_probe` cross-package promotion (v1.2+)
- `RequestSpec.idempotent` forward-decl si planner difiere (Phase 8 RELY-03 lo asume)
- Generated-code parity tooling (unasync/codegen) → v1.2+
- import-linter `independence`/`layered` contracts → v1.2+
- Cross-leak sentinel test des-skipear matriz → Phase 10 plan
- `Client.with_options(max_retries=N)` per-call override → v1.2+ (Phase 8 mentions)
- `_request` con `with http.send(...) as resp:` context-manager → descartada (CR-03 cubre el riesgo con menos churn)
