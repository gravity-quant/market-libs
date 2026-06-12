# Phase 5: Matriz Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 05-matriz-verification
**Areas discussed:** A) Read-sweep samples + market-hours guard; B) Mock-only contract para order mutations (MATZ-06) + fixes opportunistic (MATZ-04 envelope, `_token` assert) + helper promotion; C) MATZ-05 error-path live (3 distinct conditions); D) DRIFT-02 closing report + prod-vs-remarkets gap

---

## A: Read-sweep — samples + market-hours guard

### Q1: Sample symbol para get_market_data/get_trades/get_instrument_detail

| Option | Description | Selected |
|--------|-------------|----------|
| Resuelto dinámicamente del 1er instrument | `_resolved_symbol = get_all_instruments()[0].instrumentId.symbol`. Cero hardcoding de tickers que expiran. Override opcional `MATRIZ_SAMPLE_SYMBOL`. | ✓ |
| Hardcoded en main_matriz.py | Mirror D-IOL-18. Estable pero requiere mantenimiento porque los futuros rotan. | |
| Env-var obligatoria | Operador decide. Más setup. | |

**User's choice:** Dinámico desde get_all_instruments()[0]
**Notes:** Razón: símbolos matriz son futuros con vencimiento (DLR/JUN26 caduca); el patrón dinámico se adapta. Override opcional MATRIZ_SAMPLE_SYMBOL queda disponible.

### Q2: Risk API account_name source

| Option | Description | Selected |
|--------|-------------|----------|
| Env var obligatoria PRIMARY_ACCOUNT | require_env gate; los 3 Risk SKIPPED si falta. | ✓ |
| Env var opcional | Solo SKIPPED selectivo, sin require_env. | |
| Derivar dinámicamente | Risky / descartado. | |

**User's choice:** Obligatoria PRIMARY_ACCOUNT — pero interpretado como SKIPPED selectivo (no hard-gate del driver entero)
**Notes:** Reinterpretado en discusión: PRIMARY_ACCOUNT obligatoria SOLO para los 6 probes que la necesitan (3 Risk API + 3 order account-scoped); el resto del driver corre aunque falte la env var. Mirror Phase 4 D-HIGY-11.

### Q3: Market-hours guard mechanism (MATZ-07)

| Option | Description | Selected |
|--------|-------------|----------|
| Probe-based: staleness del payload | LA.date > 2h → finding NO-DATA OPEN, downstream PASS-shape. Sin tabla horaria. | ✓ |
| Tabla horaria hardcoded MATBA | Determinístico pero requiere mantener tabla (feriados). | |
| Sin gate | Solo shape/type/presence. | |

**User's choice:** Probe-based staleness
**Notes:** Se adapta a feriados/sesiones cortas/imprevistos sin mantenimiento manual.

### Q4: get_instruments_by_cfi coverage (9 CFI codes)

| Option | Description | Selected |
|--------|-------------|----------|
| 1 baseline + 8 sanity-only | ESXXXX completo + type assertion sobre los 8. | ✓ |
| Solo 1 CFI | Sin sanity. | |
| Los 9 con snapshot por cada uno | Cobertura máxima. | |

**User's choice:** 1 baseline + 8 sanity
**Notes:** Mirror D-IOL-17.

### Q5: get_all_instruments vs get_instruments_details

| Option | Description | Selected |
|--------|-------------|----------|
| Ambos: 2 probes + 2 snapshots | Diff bidireccional sobre Instrument y InstrumentDetail. | ✓ |
| Solo get_all_instruments | Reduce ruido si detail es muy variable. | |
| Solo get_instruments_details | Solo el modelo más rico. | |

**User's choice:** Ambos
**Notes:** Tienen modelos diferentes (Instrument minimal vs InstrumentDetail 18 fields); el diff bidireccional necesita los 2.

### Q6: get_instruments_by_segment sample

| Option | Description | Selected |
|--------|-------------|----------|
| Dinámico: get_segments()[0] | Mirror del patrón symbol. | ✓ |
| Hardcoded "MERV" | Determinístico. | |
| Iterar 7 segments con type-only | Analog al CFI sanity. | |

**User's choice:** Dinámico
**Notes:** Mismo patrón que symbol resolution (sin hardcoding).

### Q7: Staleness threshold para market-hours guard

| Option | Description | Selected |
|--------|-------------|----------|
| LA.date > 2h → NO-DATA OPEN, downstream PASS-shape | Threshold conservador, cubre intra-día. | ✓ |
| LA.date no es hoy → SKIPPED de valor | Más estricto. | |
| Sin umbral fijo, finding pasivo si LA.price es None | Más pasivo, ruidoso. | |

**User's choice:** 2h threshold + PASS-shape
**Notes:** MATZ-07 dice "shape/type/presence, no valores" — el guard valida shape siempre.

### Q8: get_trades date strategy

| Option | Description | Selected |
|--------|-------------|----------|
| date_from=today-7d, date_to=today | 7 días maximiza shape coverage. | ✓ |
| date=today | Single day, lista vacía probable. | |
| Sin params | Lista completa (pesado). | |

**User's choice:** 7d range

### Q9: Order *reads* sin orders reales

| Option | Description | Selected |
|--------|-------------|----------|
| 3 account-scoped con PRIMARY_ACCOUNT; 3 ID-scoped opt-in via env vars | Cobertura selectiva con SKIP claro. | ✓ |
| Los 6 con env-vars de sample | Cobertura máxima pero más setup. | |
| Solo get_active_orders | Mínimo, pierde envelope keys. | |

**User's choice:** 3 account-scoped + 3 ID-scoped opt-in
**Notes:** PRIMARY_ACCOUNT gates account-scoped; MATRIZ_SAMPLE_CL_ORD_ID/PROPRIETARY/EXEC_ID gates ID-scoped.

---

## B: Mock-only contract para order mutations (MATZ-06) + fixes opportunistic

### Q1: Invariantes mock-only para new_order/replace_order/cancel_order

| Option | Description | Selected |
|--------|-------------|----------|
| Wire shape + envelope + GET-as-write quirk + params verbatim | Full coverage del quirk. | ✓ |
| Solo wire shape + envelope | Conservador. | |
| Solo shape mínima | Mínimo. | |

**User's choice:** Full verbatim
**Notes:** Cubre URL exacto, método GET, envelope `["order"]`, str(bool) params, condicional de price/displayQty/expireDate.

### Q2: Cobertura combinaciones de new_order

| Option | Description | Selected |
|--------|-------------|----------|
| 5 tests: defaults + 4 optional toggled | Sistemático sin combinatoria. | ✓ |
| 2 tests: baseline + uno con todos los optional | Mínimo. | |
| Combinatoria completa 2^4 = 16 | Excesivo. | |

**User's choice:** 5 tests

### Q3: GET-as-write quirk documentation

| Option | Description | Selected |
|--------|-------------|----------|
| Docstring expandido + sentinel test que assert method='GET' | Test detecta refactor + docstring explica por qué. | ✓ |
| Solo docstring | Confia en code review. | |
| Comentario inline + assert en cada test | Verbose. | |

**User's choice:** Docstring + sentinel
**Notes:** Sentinel `test_new_order_uses_GET_method_per_primary_api_quirk` con docstring citing §6.3.

### Q4: MATZ-04 envelope fix scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix de fase: _unwrap helper + tests | Mirror HIGY-04. | ✓ |
| Solo documenta como finding OPEN | Sin fix in-cycle. | |
| Fix más suave: solo singular endpoints | Reducido. | |

**User's choice:** Fix de fase completo
**Notes:** 18 sites de `_get(...)[key]` reemplazados por `_unwrap(data, key, endpoint)` privado + 18 regression tests.

### Q5: `_token` assert fix

| Option | Description | Selected |
|--------|-------------|----------|
| Sí: reemplazar por if/raise + test | Cierra concern CONCERNS.md L52-55. | ✓ |
| Documentar como finding OPEN sin fix | Defer. | |
| Skip: aceptar el riesgo | No es bug real. | |

**User's choice:** Sí, fix + sentinel test

### Q6: Helper promotion (`_diff_safemodel_bidirectional`)

| Option | Description | Selected |
|--------|-------------|----------|
| Promover a verification/safemodel_diff.py + refactor main_higyrus.py | Elimina duplicación; Phase 4 deferred lo prometía. | ✓ |
| Copiar inline en main_matriz.py | YAGNI conservador. | |
| Promover sin refactor higyrus | Inconsistente. | |

**User's choice:** Promote + refactor higyrus
**Notes:** Phase 4 D-HIGY-4 explícitamente deferred a Phase 5 con la condicional "si Phase 5 confirma compatibilidad". Confirmado.

### Q7: `_unwrap` signature

| Option | Description | Selected |
|--------|-------------|----------|
| Módulo-privado en client.py: `_unwrap(data, key, endpoint)` | Sin nueva clase exception. | ✓ |
| Helper integrado en `_get`: `_get(path, key=..., **params)` | Reduce verbosity; acopla a GET. | |
| Nueva clase `PrimaryShapeError(PrimaryAPIError)` | Coherente con rechazo D-HIGY-8. | |

**User's choice:** Módulo-privado + PrimaryAPIError reuse
**Notes:** Reusa `status='ERROR'` + `description='missing envelope key X in Y'`.

### Q8: `_request` fix scope

| Option | Description | Selected |
|--------|-------------|----------|
| Solo el assert flagged (rama else) | Scope mínimo, 1 línea + 1 test. | ✓ |
| Refactor de `_request` completo | Más grande, fuera de scope. | |
| Validar auth_basic tuple no vacío | Scope creep. | |

**User's choice:** Solo el assert flagged

---

## C: MATZ-05 error-path live (3 distinct conditions)

### Q1: 3 escenarios concretos

| Option | Description | Selected |
|--------|-------------|----------|
| bogus symbol + invalid account + malformed CFI | Tres clases distintas. | ✓ |
| 3 bogus symbol en endpoints diferentes | Mismo escenario en 3 endpoints. | |
| bogus symbol + invalid account + malformed param en new_order (mock) | Incluye Risk API; new_order rompe semántica live. | |

**User's choice:** bogus symbol / invalid account / malformed CFI

### Q2: Always-on vs opt-in

| Option | Description | Selected |
|--------|-------------|----------|
| Always-on | Lookups read-only sin auth-flow. | ✓ |
| Opt-in via VERIFY_MATRIZ_ERRORS=1 | Conservador. | |
| Mixed: 2 always-on, 1 opt-in | Complejo. | |

**User's choice:** Always-on
**Notes:** Diferente de IOL/HIGY auth_401 que dispara intentos de login fallidos (lockout real); matriz error probes son lookups sin auth.

### Q3: Distinguir HTTP 4xx no mapeado

| Option | Description | Selected |
|--------|-------------|----------|
| Distinguir en el probe: HTTP 4xx → finding ERROR-MAP OPEN | Documenta sin fix in-cycle. | ✓ |
| Fix de fase: agregar mapping HTTP 4xx → PrimaryAPIError | Expande scope. | |
| Skip esta distinción | Inconsistente con IOL/HIGY. | |

**User's choice:** Distinguir + finding OPEN
**Notes:** Sin fix in-cycle (defer al downstream milestone si CONFIRMED).

### Q4: Posición en la secuencia

| Option | Description | Selected |
|--------|-------------|----------|
| Después de happy + field-type-map, antes de schema snapshots | Snapshots ya generados si error probe rompe state. | ✓ |
| Al final (mirror IOL/HIGY auth_401) | Coherente pero matriz error probes son seguros. | |
| Antes del happy-path sweep | Empezar con errores. | |

**User's choice:** Después del happy + field-type-map

---

## D: DRIFT-02 closing report + prod-vs-remarkets gap

### Q1: DRIFT-02 formato

| Option | Description | Selected |
|--------|-------------|----------|
| Append "## Cycle Closure" a cada findings file + nuevo CYCLE-REPORT.md | Drill-down per-package + vista agregada. | ✓ |
| Solo CYCLE-REPORT.md consolidado | Simple pero pierde drill-down. | |
| Solo append a findings files | Pierde vista agregada. | |

**User's choice:** Append + consolidado

### Q2: Prod-vs-remarkets gap registro

| Option | Description | Selected |
|--------|-------------|----------|
| Finding EXPECTED terminal + nota en CYCLE-REPORT.md | Coherente con lifecycle existing. | ✓ |
| Solo nota en CYCLE-REPORT.md sin finding | El gap es límite consciente, no hallazgo. | |
| Defer al milestone siguiente sin tocar Phase 5 | Contradice ROADMAP SC#4. | |

**User's choice:** Finding EXPECTED terminal
**Notes:** Mirror del patrón EXPECTED de Phase 2 anti-bot (terminal, no acción downstream).

### Q3: CYCLE-REPORT.md dimensiones

| Option | Description | Selected |
|--------|-------------|----------|
| Stats per-package + cross-cycle + open questions + schemas summary | 4 dimensiones complete. | ✓ |
| Solo stats + open questions (minimal) | Pierde cross-cycle patterns. | |
| Solo open questions + action items | Pierde dimensión histórica. | |

**User's choice:** 4 dimensiones

### Q4: Validación regression coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Script verification/cycle_report.py + ejecutado en driver | Mecánico, sin revisión manual. | ✓ |
| Validación manual | Pierde garantía. | |
| Solo conteo en CYCLE-REPORT.md sin verificación | Pasivo. | |

**User's choice:** Script + driver invocation
**Notes:** `verify_cycle_closure(pkg) -> (bool, list[str])` parsea findings files, asserta regression test path per CONFIRMED/FIXED finding.

---

## Claude's Discretion

Documentado en CONTEXT.md §Decisions §"Claude's Discretion". Incluye:
- Texto exacto del docstring expand en client.py para mutations
- Texto exacto del RuntimeError message
- Tactic de cascade SKIPPED
- Formato del path qualifier en diff_safemodel_bidirectional
- Cómo iterar 11 modelos en probe field_type_map
- Strings literales de bogus symbol/account/CFI
- Conteo exacto de regression tests MATZ-04 (~18, depende del inspect)
- Nombre del helper promovido (sugerido `diff_safemodel_bidirectional` sin underscore)
- Class del cycle_closure finding (`ERROR-MAP` sugerido vs nuevo `CYCLE-CLOSURE`)
- Estilo del hostname assert (`if/raise` recomendado)
- Conteo exacto de schemas committeados (~16-19)

## Deferred Ideas

Documentado en CONTEXT.md §Deferred. Resumen:
- Verificación live contra prod (api.primary.com.ar) — milestone futuro con safety harness apropiado
- Probe auth_401 / HTTP Basic con bad creds — anti-feature lockout
- WebSocket live (`ws_client.py`) y async surface — milestones propios
- Fix wrapping HTTP 4xx → PrimaryAPIError — defer si CONFIRMED por live run
- Multi-account / multi-symbol sweep paramétrico
- Token persistencia disco
- Test auth-once discipline live
- Plausibility bounds en market data values
- Refactor `_request` a token + basic split
- `PrimaryShapeError` subclass
- Snapshot per-CFI individual
- Anti-bot probe (matriz no usa UA filtering)
- Retries/backoff
