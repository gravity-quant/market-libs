# Phase 13: Cross-Package Ergonomics (`with_options(max_retries=N)`) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 13-Cross-Package Ergonomics (`with_options(max_retries=N)`)
**Areas discussed:** View lifecycle + chaining, matriz TokenStore × view interaction, Driver smoke / canary use, Plan slicing

---

## View lifecycle + chaining

### Q1: View `close()` footgun prevention

| Option | Description | Selected |
|--------|-------------|----------|
| `_is_view` flag + close() no-op (Recommended) | Track `_is_view: bool` en __slots__. view.close() es no-op si _is_view=True. __enter__/__exit__ también no-op. Anthropic SDK pattern. | ✓ |
| Documentar y no proteger | Solo docstring "do not call close() on a with_options view". Más simple pero footgun. | |
| view.close() raise TypeError | Fail-loud: raise TypeError('cannot close with_options view'). | |

**User's choice:** `_is_view` flag + close() no-op
**Notes:** Idiomatic anthropic/openai pattern; cero foot-gun; ~3 LOC extra por clase.

### Q2: Chaining semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Inner wins, view-of-view OK (Recommended) | Each `with_options(N)` produces fresh shallow clone; chaining inner wins; padre intacto. | ✓ |
| Inner wins pero solo desde padre | view.with_options(N) raise TypeError. | |
| Cualquiera (You decide) | Inclinarse hacia inner-wins; planner decide test shape exact. | |

**User's choice:** Inner wins, view-of-view OK

### Q3: AsyncClient symmetry

| Option | Description | Selected |
|--------|-------------|----------|
| Mismo idiomático async (Recommended) | _is_view flag protege aclose()/__aexit__. Mirror exacto del sync. | ✓ |
| Solo sync, async defer a v1.3 | Reduce surface pero rompe simetría Phase 8 D-15. | |
| Solo sync ahora, async en mismo phase | Mismo commit atómico per-paquete. | |

**User's choice:** Mismo idiomático async

### Q4: configure() + view interaction

| Option | Description | Selected |
|--------|-------------|----------|
| View ve _state viejo (no afectado por configure) (Recommended) | View es snapshot; documentar. | ✓ |
| View debería reflejar configure() | Complejo; no matchea anthropic; edge-case marginal. | |
| No me importa / Claude discretion | Planner decide y documenta. | |

**User's choice:** View es snapshot

### Q5 (extra): Snapshot público scope

| Option | Description | Selected |
|--------|-------------|----------|
| Solo Client/AsyncClient.with_options (Recommended) | Class method per-paquete; NO top-level function. | ✓ |
| Class method + top-level function | Rompe principio de instance-method. | |
| Solo class method, sin tocar snapshot | Rompe el patrón existente. | |

**User's choice:** Solo Client/AsyncClient.with_options

---

## matriz TokenStore × view interaction

### Q1: HTTP retry vs TokenStore refresh isolation

| Option | Description | Selected |
|--------|-------------|----------|
| View max_retries es HTTP-only; TokenStore usa padre (Recommended) | `_state.client_max_retries` field cacheado por constructor; view solo afecta extensions['max_attempts']. | ✓ |
| View max_retries fluye a TokenStore | Status quo; primer view en triggear _ensure_token define TokenStore.max_retries (long-lived leak). | |
| Force eager TokenStore creation en __init__ | Refactor más invasivo; posible regresión Phase 10. | |

**User's choice:** HTTP-only isolation
**Notes:** Anti-Pitfall extendido al auth server load.

### Q2: 3-way concurrency impact

| Option | Description | Selected |
|--------|-------------|----------|
| No — view comparte _state.token_store, locks unchanged (Recommended) | View shallow-clone NO crea TokenStore propio; Phase 10 spike-findings intacto. | ✓ |
| Necesita test de regresión explícita | Belt-and-suspenders sobre spike-findings ya validados. | |
| Otra cosa (Other) | Duda específica no cubierta. | |

**User's choice:** No — locks unchanged

### Q3: Storage location for parent_max_retries

| Option | Description | Selected |
|--------|-------------|----------|
| Nuevo field `_state.client_max_retries: int` (Recommended) | Constructor lo setea; view NO toca; ~3 LOC matriz. | ✓ |
| View skip _ensure_token TokenStore re-bind | Restrictivo; rompe UX. | |
| Lazy + first-call wins, con warning | Half-measure. | |

**User's choice:** Field en _state

### Q4: Field duplication scope

| Option | Description | Selected |
|--------|-------------|----------|
| Solo matriz — mínimo cambio (Recommended) | Solo matriz tiene `build_token_store(state, max_retries=...)`. | ✓ |
| Los 4 paquetes — simetría | Beneficio: codegen v1.3 uniforme. Trade-off YAGNI. | |
| Solo matriz por ahora; revisar v1.3 codegen | Misma como (a) + decisión documentada. | |

**User's choice:** Solo matriz

### Q5: Regression test placement

| Option | Description | Selected |
|--------|-------------|----------|
| Test mocked en matriz/tests/ (Recommended) | `test_with_options_does_not_rebind_tokenstore_max_retries`; mocked, fast, focused. | ✓ |
| Test cross-cutting en verification/ | Parametrize × paquetes (3 skip); descubrible para futuros. | |
| Ambos | Máxima cobertura, más overhead. | |

**User's choice:** matriz/tests/

### Q6: Other auth-flow leaks

| Option | Description | Selected |
|--------|-------------|----------|
| No — solo matriz tiene parameterized auth state (Recommended) | iol/higyrus auth-flow ya cubierto por mutation-gate cross-cutting Phase 8. | ✓ |
| Auditar iol _send_auth_request también | Cubrir caso de view's max_attempts en login/refresh. | |
| Otra cosa (Other) | Caso específico. | |

**User's choice:** No — Phase 8 ya cubre

---

## Driver smoke / canary use

### Q1: Driver changes scope

| Option | Description | Selected |
|--------|-------------|----------|
| Cero cambios a drivers (Recommended) | Surface only en packages/*/src/; Phase 15 decide adoption. | ✓ |
| 1 driver canary probe (main_ambito) | Validates surface contra API real antes de Phase 17. | |
| matriz canary probe (anti-Pitfall 14 live) | Riesgoso (mocking en driver), valor incierto. | |

**User's choice:** Cero cambios a drivers
**Notes:** Phase scope limpia; tests mocked cubren behavior; LIVE-03 vive en Phase 17.

### Q2: Phase 15 handoff docs

| Option | Description | Selected |
|--------|-------------|----------|
| Sí — nota en 13-SUMMARY.md (Recommended) | Forward references section con 2-3 ejemplos de uso. | ✓ |
| Documentar solo en docstrings | Phase 15 descubre via researcher. | |
| No necesario | Sin docs especiales. | |

**User's choice:** Nota en 13-SUMMARY.md

---

## Plan slicing

### Q1: Plan structure

| Option | Description | Selected |
|--------|-------------|----------|
| 5 planes — 1 cross-cutting + 4 per-package serial (Recommended) | Idiom Phase 6/7/8; Plan 5 (iol) último por Phase 14 interaction. Sin Plan 6 (scope chico). | ✓ |
| 6 planes — +1 CI gate consolidation | Plan 6 puede ser overkill para scope de Phase 13. | |
| 3 planes — 1 cross-cutting + 1 unified + 1 final | Atomicidad reducida; si Plan 2 rompe, 4 paquetes regresan juntos. | |

**User's choice:** 5 planes serial

### Q2: Cross-cutting tests in Plan 1

| Option | Description | Selected |
|--------|-------------|----------|
| shares_http_client_and_token × 4 (anti-Pitfall 13) | Resource sharing. | ✓ |
| does_not_bypass_mutation_gate_matriz (anti-Pitfall 14, CRITICAL) | CRITICAL merge gate. | ✓ |
| max_attempts_extension_honored × idempotent GETs | View's max_retries reflected. | ✓ |
| chaining_inner_wins × 4 | Cubre D-V2. | ✓ |

**User's choice:** All 4 tests in Plan 1

### Q3: close-is-noop test placement

| Option | Description | Selected |
|--------|-------------|----------|
| Per-paquete mocked tests (Plans 2-5) (Recommended) | Sigue idiom Phase 6 lifecycle tests; focused. | ✓ |
| Cross-cutting parametrizado en Plan 1 | Belt-and-suspenders; rompe patrón existente. | |

**User's choice:** Per-paquete tests

### Q4: Snapshot regen cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Per-paquete atómico (Recommended) | Cada Plan 2-5 actualiza su snapshot; idiom Phase 6/8 D-28. | ✓ |
| Bulk al final (Plan 5 cierra todos) | Rompe atomicidad. | |

**User's choice:** Per-paquete atómico

---

## Claude's Discretion

- Naming exacto del extension key (`"max_attempts"` recomendado vs `"max_retries"`)
- Ubicación de setear `request.extensions["max_attempts"]` (uniforme vs solo views)
- `_max_retries` accessor desde el shell (translation `N → N+1`)
- `__repr__` del view (cosmético; planner decide)
- PEP 562 shim impact (Phase 13 NO toca el shim)
- Mocking pattern para D-T5 test (`monkeypatch` vs direct setattr)
- Endpoint selection per paquete para `test_with_options_max_attempts_extension_honored`

## Deferred Ideas

- `with_options(timeout=...)` per-call timeout → v1.3
- `with_options(headers={...})` per-call headers → v1.3
- `with_options(http_client=...)` per-call httpx swap → v1.3
- `Client.from_env()` classmethod × 4 packages → SKIPPED en v1.2 (industry survey)
- `request.extensions["max_attempts"]` per-call override sin view → v1.3+
- Top-level `<pkg>.with_options(...)` module function → reject explícito
- `_is_view` flag a 4 paquetes uniforme vía codegen → v1.3 libcst spike
- TokenStore rebind explícito vía `client.with_options(token_refresh_retries=N)` → v1.3+
- Driver smoke probe con `with_options` → Phase 15 driver migration
- `__repr__` del view explícito → planner decide; v1.3 refina
