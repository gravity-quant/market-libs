# Phase 5: Matriz Verification - Research

**Researched:** 2026-06-09
**Domain:** Verificación en vivo de cliente HTTP REST contra Primary API (MATBA ROFEX) / remarkets sandbox, sync-only, con superficie destructiva mock-only
**Confidence:** HIGH

## Summary

Phase 5 es el **cuarto y último ciclo** del proyecto de verificación. El target — `matriz-client` — tiene la **superficie más grande** (18 endpoints REST públicos + 11 modelos `_SafeModel`), la **única superficie destructiva** del proyecto (`new_order` / `replace_order` / `cancel_order` con quirk GET-as-write), un patrón de **auth dual** (X-Auth-Token por defecto, HTTP Basic Auth para Risk API §9), y un patrón de **envelope keys** consistente en 18 sitios (`["segments"]`, `["instruments"]`, `["instrument"]`, `["order"]`, `["orders"]`, `["marketData"]`, `["trades"]`, `["positions"]`) que actualmente generan `KeyError` no mapeado si faltan.

A diferencia de phases 2-4 (dual sync+async), matriz es **sync-only**: no hay `aio.py`, los fixes son single-surface, y el lifecycle del driver es más simple (sin `asyncio.run`). El loop **driver → finding → fix → mocked regression** ya está validado por phases 2-4; phase 5 lo aplica con seis complicaciones específicas — surface grande, mutaciones mock-only, market-hours dependency, dos fixes opportunistic up-front, helper promotion (`_diff_safemodel_bidirectional` → `verification/safemodel_diff.py`), y cierre del ciclo completo (DRIFT-02 + CYCLE-REPORT.md + prod-vs-remarkets gap EXPECTED terminal).

**Primary recommendation:** Reusar verbatim los patrones lockeados en phases 2-4 (CONTEXT.md tiene 33 decisiones explícitas D-MATZ-1..D-MATZ-34). Implementar el plan en 4-5 waves: (Wave 1) fix MATZ-04 envelope + fix `_token` assert + helper promotion + cycle_report module + 19 regression tests, en paralelo; (Wave 2) reescribir `main_matriz.py` con ~25 probes nombrados + .env.example update; (Wave 3) live run manual contra remarkets + Verified-live mocked tests + MATZ-06 mock-only contract (11 tests); (Wave 4) cierre del ciclo (Cycle Closure appends + CYCLE-REPORT.md + commit baseline DRIFT-02). Toda la implementación está pre-decidida en CONTEXT.md — el planner traduce, no inventa.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Read-sweep samples & resolution flow (Area A):**
- **D-MATZ-1:** Sample symbol resuelto dinámicamente del primer instrument vía `_resolved_symbol = primary.get_all_instruments()[0].instrumentId.symbol`. Override opcional `MATRIZ_SAMPLE_SYMBOL`.
- **D-MATZ-2:** Sample segment_id resuelto dinámicamente del primer segment vía `_resolved_segment = primary.get_segments()[0].marketSegmentId`. Sin override por env por ahora (YAGNI).
- **D-MATZ-3:** `PRIMARY_ACCOUNT` obligatoria SOLO para los 6 probes que la necesitan (3 Risk API + 3 order reads account-scoped), con SKIPPED selectivo si falta. NO hard-gate del driver entero.
- **D-MATZ-4:** Order reads ID-scoped (3 probes: `get_order_status`, `get_order_history`, `get_order_by_exec_id`) opt-in vía `MATRIZ_SAMPLE_CL_ORD_ID`, `MATRIZ_SAMPLE_PROPRIETARY`, `MATRIZ_SAMPLE_EXEC_ID`. Sin ellas → SKIPPED con razón.
- **D-MATZ-5:** Market-hours guard probe-based (MATZ-07): inspeccionar `LA.date` del payload de market data; si stale > 2h respecto a `time.time() * 1000` → finding `NO-DATA` OPEN, downstream PASS-shape (assertions solo de presencia/tipo, NO valor).
- **D-MATZ-6:** `get_instruments_by_cfi`: 1 CFI baseline (`ESXXXX`) con snapshot completo + sanity type-only de los 8 restantes (DBXXXX, OCASPS, OPASPS, FXXXSX, OPAFXS, OCAFXS, EMXXXX, DBXXFR).
- **D-MATZ-7:** `get_all_instruments` y `get_instruments_details` ambos cubiertos con 2 probes + 2 snapshots distintos (modelos diferentes: `Instrument` minimal vs `InstrumentDetail` 18 fields).
- **D-MATZ-8:** `get_trades` con `date_from=today-7d, date_to=today` (rango 7 días). Si lista vacía → finding `NO-DATA` OPEN + PASS-shape.

**MATZ-04 envelope fix (fix de fase):**
- **D-MATZ-9:** `_unwrap(data, key, endpoint)` helper privado en `client.py` que levanta `PrimaryAPIError(status="ERROR", description=f"missing envelope key '{key}' in response from {endpoint}")`. SIN nueva subclase `PrimaryShapeError` (consistencia con D-HIGY-8).
- **D-MATZ-10:** **18 sites** de `_get(...)[key]` reemplazados por `_unwrap(_get(path, ...), key, path)`. Lista exhaustiva en CONTEXT.md L322-345; verificado por grep contra client.py (líneas 194, 204, 209, 215, 223, 235, 282, 294, 301, 308, 316, 322, 327, 332, 337, 360, 384, 401). `get_detailed_positions` y `get_account_report` NO se tocan (retornan dict raíz directo al model).
- **D-MATZ-11:** 18 regression tests mockeados para MATZ-04 (uno por envelope key wrap reemplazado), sección `# ------ Regressions ------` en `test_client.py`. Docstring: `"""Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""`.

**`_token` assert fix (CONCERNS.md L52-55):**
- **D-MATZ-12:** `assert _token is not None` (line 157 client.py) reemplazado por `if _token is None: raise RuntimeError("matriz_client.client: _ensure_token() did not populate _token")`. Scope mínimo: solo el assert en la rama no-auth_basic; la rama `if auth_basic` queda intacta.
- **D-MATZ-13:** 1 sentinel test del `_token` RuntimeError. `test_request_raises_runtime_error_if_ensure_token_leaves_none(monkeypatch)`.

**MATZ-06 Mock-only contract para mutaciones (Area B):**
- **D-MATZ-14:** 5 tests de `new_order` cubriendo cada rama del param building (LIMIT baseline, MARKET sin price, iceberg+displayQty, GTD+expireDate, cancelPrevious=True).
- **D-MATZ-15:** 1 test de `replace_order` + 1 test de `cancel_order` con URL exacta + envelope unwrap `["order"]` + retorno typed `NewOrderResponse`.
- **D-MATZ-16:** 1 sentinel test del GET-as-write quirk (`test_new_order_uses_GET_method_per_primary_api_quirk`) con docstring que cita §6.3 spec. Idem 1 sentinel para `replace_order` y `cancel_order` (3 sentinels en total).
- **D-MATZ-17:** Docstring expand en `client.py` para new_order / replace_order / cancel_order con warning "WARNING: Submission uses HTTP GET per Primary API §6.3 spec — this is intentional, not a bug. Never refactor to POST without API confirmation."

**Helper promotion (DRIFT-02 antesala):**
- **D-MATZ-18:** Promover `_diff_safemodel_bidirectional` (inline en main_higyrus.py Phase 4) a `verification/safemodel_diff.py` con signature ya validada. Renombrar a `diff_safemodel_bidirectional` (sin underscore = público).
- **D-MATZ-19:** Barrel export en `verification/__init__.py`: agregar `diff_safemodel_bidirectional` a los exports existentes.
- **D-MATZ-20:** Refactor de `main_higyrus.py` para consumir el helper centralizado vía `from verification import diff_safemodel_bidirectional`. Tests pre-existentes Phase 4 deben seguir verdes.
- **D-MATZ-21:** `main_matriz.py` usa el helper desde el barrel sobre los 11 modelos `_SafeModel` matriz.

**MATZ-05 Error-path live (Area C):**
- **D-MATZ-22:** 3 error probes always-on con condiciones distintas: (1) bogus symbol en `get_market_data("ZZZZZZ-NOT-A-SYMBOL")`, (2) invalid account en `get_active_orders("INVALID-ACCT-XXXXX")`, (3) malformed CFI en `get_instruments_by_cfi(cast(CFICode, "INVALID-CFI"))`. Always-on (sin opt-in env var); NO replica el patrón opt-in `auth_401` de IOL/HIGY por riesgo de lockout.
- **D-MATZ-23:** Distinguir HTTP 4xx no mapeado (→ finding `ERROR-MAP` OPEN) de `{"status":"ERROR"}` mapeado (→ PASS). Sin fix in-cycle del wrapping (defer al downstream milestone si CONFIRMED).
- **D-MATZ-24:** Posición en la secuencia: después del happy-path sweep + field-type-map, antes de schema snapshots.

**DRIFT-02 closing report + prod-vs-remarkets gap (Area D):**
- **D-MATZ-25:** Append `## Cycle Closure` a `<pkg>-findings.md` para los 4 paquetes verificados (ambito-financiero-client, iol-client, higyrus-client, matriz-client). Sección con conteo de findings por status, lista de regression tests linkados a FIXED, validación automática.
- **D-MATZ-26:** Nuevo `.planning/verification/CYCLE-REPORT.md` consolidado con 4 dimensiones: (1) Stats per-package, (2) Cross-cycle, (3) Open questions for downstream milestone, (4) Schemas summary.
- **D-MATZ-27:** Gap prod-vs-remarkets como finding `EXPECTED` terminal en `matriz-client-findings.md` (class=`SHAPE`, status=`EXPECTED`, surface=`sync`, title="prod-vs-remarkets divergence acknowledged"). Mirror del patrón EXPECTED de Phase 2 anti-bot.
- **D-MATZ-28:** `verification/cycle_report.py` nuevo con `verify_cycle_closure(pkg: str) -> tuple[bool, list[str]]`. El driver lo invoca al final para los 4 paquetes; emite `PROBE cycle_closure_<pkg>: PASS|FAIL`; si falla algún CONFIRMED sin regression → finding `ERROR-MAP` OPEN.

**Driver structure & lifecycle:**
- **D-MATZ-29:** Secuencia de ~25 probes en `main_matriz.py` (orden ejecución en CONTEXT.md L658-707, tabla LITERAL).
- **D-MATZ-30:** No hay `_async_main` ni `asyncio.run` — matriz es sync-only. Lifecycle más simple que Phases 2-4.
- **D-MATZ-31:** Cascade SKIPPED tras `login()` failure (flag module-level `_auth_failed`, mirror D-IOL-3 / D-HIGY-DISCRETION).
- **D-MATZ-32:** `safe_print(text, secrets=[PRIMARY_USER, PRIMARY_PASSWORD, _token])`. `_token` se agrega dinámicamente tras login (mirror D-IOL-7 / D-HIGY-15).
- **D-MATZ-33:** Env vars del driver: `PRIMARY_USER`, `PRIMARY_PASSWORD` obligatorias; `PRIMARY_BASE_URL` opcional (default remarkets); `PRIMARY_ACCOUNT` opcional gate selectivo; `MATRIZ_SAMPLE_SYMBOL`, `MATRIZ_SAMPLE_CL_ORD_ID`, `MATRIZ_SAMPLE_PROPRIETARY`, `MATRIZ_SAMPLE_EXEC_ID` opcionales. **Belt-and-suspenders hostname assert remarkets** al inicio (ABORT si no contiene "remarkets").
- **D-MATZ-34:** Dos secciones verbatim en `test_client.py` (sin `test_async_client.py` — matriz no tiene async): `# ------ Verified live (Phase 5) ------` y `# ------ Regressions ------`.

### Claude's Discretion

- Texto exacto del docstring expand en `client.py` para new_order/replace_order/cancel_order (contenido del warning a discreción; debe citar §6.3 spec y "never refactor without API confirmation").
- Texto exacto del RuntimeError message en `_token` fix.
- Tactic exacta de la cascade SKIPPED tras login failure (flag module-level vs decorator vs early-return).
- Formato exacto del path qualifier en `diff_safemodel_bidirectional` (e.g., `.snapshot.LA.price` vs `snapshot.LA.price`).
- Cómo el probe `field_type_map` itera los 11 modelos: una pasada por endpoint vs una pasada por modelo.
- String literal de bogus symbol (`"ZZZZZZ-NOT-A-SYMBOL"` sugerido), invalid account (`"INVALID-ACCT-XXXXX"` sugerido), malformed CFI (`"INVALID-CFI"` sugerido) — ajustables mientras sean sintácticamente válidos pero semánticamente inválidos.
- Conteo exacto de regression tests de MATZ-04: el conteo real es 18 (confirmado por grep), no 13. La decisión locked es "1 regression test por cada `_get(...)[key]` wrap reemplazado".
- Si el helper promovido se llama `diff_safemodel_bidirectional` (sugerido) o conserva underscore.
- Si el CFI sanity probe emite findings por cada CFI con shape divergente o solo el baseline tiene snapshot.
- Si el `cycle_closure` probe usa `ERROR-MAP` class (sugerido por proximidad) o agrega `CYCLE-CLOSURE` al vocabulary de findings.
- Si el assert hostname remarkets (D-MATZ-33) usa `assert` o `if/raise` — recomendado `if/raise` por consistencia con D-MATZ-12.
- Conteo exacto de schemas committeados: cubre cada endpoint del happy path + ID-scoped condicionales (~16-19 snapshots).

### Deferred Ideas (OUT OF SCOPE)

- Verificación live de Matriz contra prod (`api.primary.com.ar`) — registrado como finding EXPECTED terminal D-MATZ-27. Milestone futuro.
- Probe `auth_401` con bad creds en Matriz — NO se implementa. REQUIREMENTS.md Out of Scope explícito.
- Probe HTTP Basic Auth con bad creds en Risk API — mismo razonamiento; mock-only.
- Verificación live de WebSocket (`ws_client.py`) — toda la capa WS fuera de scope para todo el ciclo.
- Verificación async de `matriz-client` — `aio.py` NO existe por diseño (sync-only).
- Fix del wrapping HTTP 4xx → `PrimaryAPIError` (concerns potencial de D-MATZ-23) — finding OPEN para downstream milestone si CONFIRMED.
- Iteración multi-account / multi-symbol — samples fijos en Phase 5.
- Persistencia del token Matriz a disco entre invocaciones.
- Test de auth-once discipline live — los tests precargan `_token`.
- Plausibility bounds en `LA.price` / `OF[0].price` / `BI[0].price` — Phase 5 valida shape/type/presence únicamente (MATZ-07).
- Refactor de `_request` a `_request_token()` + `_request_basic()` — PROJECT.md fuera de scope.
- Promote new `PrimaryShapeError(PrimaryAPIError)` subclass — D-MATZ-9 rechaza.
- Verificación de `get_instruments_by_cfi` con cada uno de los 9 CFI codes como snapshot independiente.
- Anti-bot probe en matriz — Primary no usa UA-filtering.
- Throttling / rate-limit-aware retries en `_ensure_token` — anti-feature.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MATZ-01 | Verificar contra Primary/remarkets en vivo el flujo de auth (login + lazy-auth), sync REST | Standard Stack §Auth + Architecture Pattern §Live Driver (probe `probe_login_sync` + cascade SKIPPED D-MATZ-31) |
| MATZ-02 | Barrido happy-path read-only de toda la superficie REST (segments, instruments en sus variantes, market data, trades, order reads, risk positions/report) reteniendo payload | Standard Stack §HTTP client + Architecture §Driver Probes (probes 2-19 D-MATZ-29) |
| MATZ-03 | Diff bidireccional payload crudo vs campos `from_api` (field-drop silencioso) | Architecture Pattern §SafeModel diff bidireccional (helper promotion D-MATZ-18 + reuse en `probe_field_type_map` D-MATZ-29 #20) |
| MATZ-04 | Verificar envelope keys (`order`/`orders`/`marketData`/`trades`/`positions`); `KeyError` no mapeado → candidato a fix | Fix in-cycle D-MATZ-9/10 (`_unwrap` helper + 18 sites) + 18 regression tests D-MATZ-11 |
| MATZ-05 | Cobertura `{"status":"ERROR"}` → `PrimaryAPIError` en 3 condiciones distintas (bogus symbol, invalid account, malformed param) | 3 error probes always-on D-MATZ-22 + distinción HTTP 4xx vs `{"status":"ERROR"}` D-MATZ-23 |
| MATZ-06 | Verificación mock-only de `new_order`/`replace_order`/`cancel_order` con quirk GET-as-write preservado; nunca live | 5 tests new_order + 1 replace + 1 cancel + 3 sentinels GET-quirk = **11 tests mock-only** D-MATZ-14..16 + docstring warning D-MATZ-17 |
| MATZ-07 | Market data assertions solo shape/type/presencia (no valores), con guarda de horario | Probe-based staleness guard D-MATZ-5 (`LA.date` > 2h → finding NO-DATA OPEN + PASS-shape downstream) |
| DRIFT-02 | Per-package findings report con cada bug confirmado fixed + tested | Cycle closure D-MATZ-25..28: append `## Cycle Closure` a 4 findings files + `CYCLE-REPORT.md` consolidado + `verify_cycle_closure` automated check + prod-vs-remarkets EXPECTED terminal |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

| Directive | Source | Phase 5 Impact |
|-----------|--------|----------------|
| Python 3.12+, uv, httpx (sync+async), pytest+pytest-httpx, ruff, mypy strict | Stack | Toda extensión y fix debe pasar `uv run pytest -q` + `mypy --strict` + `ruff check` + `ruff format` |
| Estado singleton a nivel de módulo; sin código compartido entre paquetes | Architecture | Fixes en `client.py` quedan dentro de `matriz-client`; sin dependencias cruzadas. El módulo raíz `verification/` NO es un paquete uv (es un helper local al monorepo) y SÍ puede contener código compartido entre drivers |
| Dual sync/async: cualquier fix de lógica debe espejarse en `client.py` y `aio.py` | Architecture | **NO APLICA a matriz** — matriz es sync-only por diseño. Fixes son single-surface. Los Verified-live + Regressions tests viven solo en `test_client.py` (sin `test_async_client.py`) |
| Credenciales en `.env` por paquete; nunca commitear `.env` ni exponer en logs/reportes/tests | Security | `safe_print(secrets=[PRIMARY_USER, PRIMARY_PASSWORD, _token])` D-MATZ-32 cubre stdout discipline. Findings files emiten solo conteos + shape descriptors (mirror Phase 4 D-HIGY-2). Schemas son PII-free por construcción (`schema_of`) |
| Dependencias externas en vivo — disponibilidad varía por horario/datos/rate-limit | Reliability | Market-hours guard D-MATZ-5 + `NO-DATA` finding class + SKIPPED selectivo para probes account-scoped/ID-scoped si faltan env vars |
| `from __future__ import annotations` obligatorio al tope de todo módulo | CONVENTIONS.md | Aplica a `main_matriz.py` reescrito + `verification/safemodel_diff.py` + `verification/cycle_report.py` (todos archivos nuevos/modificados) |
| Ruff `line-length=100`, double quotes, 4 espacios | Style | Toda PR-en-curso pasa por ruff format antes del commit |
| Mypy strict (`strict = true`, `disallow_untyped_defs = true`) | Types | El nuevo helper `diff_safemodel_bidirectional` y `verify_cycle_closure` deben tener type hints completos |
| Pytest config: `asyncio_mode = "auto"`, `--import-mode=importlib`, `--strict-markers` | Tests | Los tests mockeados nuevos (18 MATZ-04 + 11 MATZ-06 + 1 _token sentinel + Verified-live invariants) siguen este config; sin `@pytest.mark.live` (mockeados) |
| GSD Workflow Enforcement: antes de editar archivos, comenzar por un GSD command | Workflow | Phase 5 ejecuta via `/gsd-execute-phase` con waves de plans. El planner crea los PLAN.md; el ejecutor los aplica |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Auth (token X-Auth-Token + 23h TTL) | matriz-client (`client.py:_ensure_token`, `login`) | — | Singleton de módulo; verificado via `probe_login_sync` |
| Auth Basic (Risk API §9) | matriz-client (`client.py:_request(auth_basic=)`) | — | Dual-mode auth dentro del mismo `_request` |
| HTTP transport | httpx.Client (sync only) | — | Single `_session` global; sync-only (sin asyncio) |
| Envelope unwrap | matriz-client (`client.py:_unwrap` NUEVO D-MATZ-9) | — | 18 sites a refactorear; reemplaza `_get(...)[key]` raw indexing |
| Error mapping (`{"status":"ERROR"}` → `PrimaryAPIError`) | matriz-client (`client.py:_request` L167-172, pre-existente) | matriz-client (`exceptions.py:PrimaryAPIError`) | Pre-existente, NO se toca. MATZ-05 ejercita esta lógica |
| Models (safe-access) | matriz-client (`models.py:_SafeModel + 11 dataclasses`) | — | `from_api()` + `get_type_hints()` es el objeto del diff bidireccional |
| WebSocket streaming | matriz-client (`ws_client.py`) | — | **OUT OF SCOPE** — Phase 5 NO toca |
| Verification harness (env_gate, redaction, findings, schema, mutation_gate, capture, anonymize) | `verification/` (raíz del repo, no paquete uv) | — | Pre-existente Phases 1-4. Phase 5 agrega 2 módulos: `safemodel_diff.py`, `cycle_report.py` |
| Live driver (probes nombrados, stdout verbatim, findings file + schemas) | `main_matriz.py` (raíz del repo) | — | Reescritura completa de smoke a ~25 probes nombrados (D-MATZ-29) |
| Mocked invariants + regressions | `packages/matriz-client/tests/test_client.py` | — | 2 secciones nuevas: Verified-live + Regressions. NO se crea `test_async_client.py` (matriz es sync-only) |
| Cycle closure | `verification/cycle_report.py` (NUEVO D-MATZ-28) + `main_matriz.py` invocation | `.planning/verification/<pkg>-findings.md` × 4 + `CYCLE-REPORT.md` (NUEVO) | Cierra DRIFT-02 |

## Standard Stack

### Core (sin cambios respecto a Phases 1-4)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Workspace lock (`uv.lock`). Soporta `from __future__ import annotations`, `Self`, `slots=True`, `get_type_hints` con `Optional`/`Union` introspection |
| `httpx` | >=0.27 | HTTP transport sync+async | Stack del proyecto; matriz usa solo `httpx.Client` sync. `httpx.BasicAuth` para Risk API §9 |
| `pytest` | >=8.3 | Test runner | Configurado en root `pyproject.toml` con `asyncio_mode="auto"`, `--strict-markers`, `--import-mode=importlib` |
| `pytest-httpx` | >=0.34 | HTTP mocking en tests | Pattern estándar de los 5 paquetes: `httpx_mock.add_response(url=..., method=..., json=...)`. Imprescindible para los 11 tests MATZ-06 (mock-only) + 18 regression tests MATZ-04 |
| `python-dotenv` | >=1.0 | Carga `.env` al importar el cliente | `load_dotenv()` ya en `matriz_client.client` L55. Driver hereda |
| `uv` | 0.9.0+ | Package manager + workspace runner | `uv run --package matriz-client python main_matriz.py` |
| `ruff` | >=0.7 | Linter + formatter | Line-length 100, double quotes, py312 target |
| `mypy` | >=1.13 | Strict type checker | `strict = true` para toda la fase |

### Supporting (helpers ya construidos en Phases 1-4 — reusar, no reinventar)

| Helper | Module | Purpose | When to Use in Phase 5 |
|--------|--------|---------|------------------------|
| `require_env(pkg, names)` | `verification.env_gate` | Skip-and-continue si faltan creds | Al inicio del driver: `require_env("matriz-client", ["PRIMARY_USER", "PRIMARY_PASSWORD"])` (D-MATZ-33) |
| `mutating_allowed()` | `verification.mutation_gate` | Doble gate `VERIFY_MUTATING=1` + hostname remarkets | Disponible para belt-and-suspenders, pero **MATZ-06 es mock-only por diseño** → mutation gate NO se ejercita live. El hostname assert manual D-MATZ-33 es complementario |
| `safe_print(text, secrets)` | `verification.redaction` | Redacción de credenciales en stdout | TODOS los prints del driver pasan por `safe_print(text, secrets=[PRIMARY_USER, PRIMARY_PASSWORD, _token])` D-MATZ-32 |
| `redact(value)` | `verification.redaction` | Prefijo + elipsis | Para mostrar token resumido si es necesario |
| `schema_of(payload)` | `verification.schema` | Snapshot de claves + tipos, PII-free por construcción | Generar los ~16-19 schema snapshots committeables (`.planning/verification/schemas/matriz-client/<func>.json`) con envelope D-21 |
| `append_finding(pkg, **kwargs)` | `verification.findings` | Append idempotent por `fid`; preserva status humano | Toda emisión de finding del driver. Hardened en Phase 2 (CR-01/CR-02/WR-04: preserva prosa humana, valida pkg slug, single-line title) |
| `write_findings(pkg)` | `verification.findings` | Esqueleto del archivo | Llamado implícito por `append_finding` si el archivo no existe |
| `FINDING_CLASSES` | `verification.findings` | Tupla fija (D-09): SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT | Validación al emitir findings; **considerar agregar `CYCLE-CLOSURE` o usar `ERROR-MAP` per Discretion D-MATZ-28** |
| `STATUS_LIFECYCLE` | `verification.findings` | Tupla fija (D-08): OPEN → CONFIRMED → FIXED + terminales EXPECTED/NO-FIX | Asignar status al emitir findings |
| `capture(pkg, endpoint, payload)` | `verification.capture` | Volcar raw payload a staging gitignored | **Phase 5 NO commitea fixtures crudos** (mirror Phase 2/3/4). Disponible para inspección manual |
| `anonymize(payload, Denylist)` | `verification.anonymize` | Reemplazo de PII | **NO usado en Phase 5** — matriz no tiene PII (accountId es ID interno tenant) |
| `diff_safemodel_bidirectional(payload, model_cls, path)` | `verification.safemodel_diff` (**NUEVO D-MATZ-18**) | Yield `(path, direction, key)` tuples para divergencias model↔wire, recursivo en nested SafeModels | Probe `field_type_map` D-MATZ-29 #20 sobre los 11 modelos matriz; refactor in-cycle de `main_higyrus.py` D-MATZ-20 |
| `verify_cycle_closure(pkg)` | `verification.cycle_report` (**NUEVO D-MATZ-28**) | Parsea `<pkg>-findings.md`, valida que cada CONFIRMED/FIXED tenga regression test linkeado | Invocado al final del driver D-MATZ-28; emite `PROBE cycle_closure_<pkg>: PASS|FAIL` para los 4 paquetes |

### Alternatives Considered

| Instead of | Could Use | Why we don't |
|------------|-----------|--------------|
| `_unwrap` helper privado | Nueva subclase `PrimaryShapeError(PrimaryAPIError)` | D-MATZ-9 rechaza: callers que catchean `PrimaryAPIError` siguen funcionando; distinción via string-based `description` (mirror Phase 4 D-HIGY-8 sentinel `status_code=0`) |
| `if _token is None: raise RuntimeError(...)` | Mantener `assert _token is not None` | CONCERNS.md L52-55: `python -O` strippea asserts; en producción se convertiría en `NoneType has no attribute` (peor diagnóstico) |
| Probe `auth_401` opt-in (mirror IOL/HIGY) | Sin probe live de bad-creds | REQUIREMENTS.md Out of Scope explícito: Primary login fallido afecta rate-limit del tenant (riesgo de lockout más alto que IOL). Cobertura solo mock |
| Live mutación de órdenes en remarkets | Mock-only (MATZ-06) | PROJECT.md / REQUIREMENTS.md Out of Scope: nunca live, ni siquiera en sandbox; mock-only contract verbatim |
| Tabla horaria hardcoded MATBA para market-hours guard | Probe-based via staleness de `LA.date` D-MATZ-5 | Sin tabla horaria que mantener; se adapta a feriados, sesiones cortas, imprevistos. 2h threshold cubre intra-día con margen |
| Sample symbol hardcoded (mirror D-IOL-18) | Dinámico desde `get_all_instruments()[0]` D-MATZ-1 | Símbolos matriz son futuros con vencimiento (DLR/JUN26 caduca cada mes); hardcoding requiere mantenimiento |

**Installation:**

```bash
# No new packages required. Phase 5 reusa el stack ya instalado en uv.lock.
uv sync --all-packages --all-extras --dev --frozen
```

**Version verification:** El proyecto usa `uv.lock` committeado (758 líneas). No se agregan dependencias nuevas en Phase 5. Verificación contra ecosistema correcto:

```bash
uv tree --package matriz-client  # confirma httpx, python-dotenv, pytest, pytest-httpx
```

[VERIFIED: codebase] No new packages — all helpers (`verification/*`) son módulos del propio repo.

## Package Legitimacy Audit

Phase 5 **NO instala packages externos**. Toda la lógica nueva (`verification/safemodel_diff.py`, `verification/cycle_report.py`) usa stdlib + módulos pre-existentes del repo.

| Package | Source | Status | Disposition |
|---------|--------|--------|-------------|
| `httpx >=0.27` | uv.lock (Phase 0) | Approved | Pre-existing |
| `pytest-httpx >=0.34` | uv.lock (Phase 0) | Approved | Pre-existing |
| `python-dotenv >=1.0` | uv.lock (Phase 0) | Approved | Pre-existing |
| `pytest >=8.3` | uv.lock (Phase 0) | Approved | Pre-existing |

**Packages removed:** none
**Packages flagged as suspicious:** none

*Phase 5 NO requiere `slopcheck` porque no agrega dependencias externas. Toda la superficie nueva es código local sobre stdlib.*

## Architecture Patterns

### System Architecture Diagram

```text
                             .env (PRIMARY_USER/PASSWORD/BASE_URL/ACCOUNT/SAMPLES)
                              │
                              ▼
                   ┌─────────────────────────┐
                   │ require_env() gate      │  HARN-01: skip-clean if missing
                   └────────────┬────────────┘
                                │
                                ▼
                   ┌─────────────────────────┐
                   │ hostname assert         │  D-MATZ-33: ABORT if not remarkets
                   │ (belt-and-suspenders)   │
                   └────────────┬────────────┘
                                │
                                ▼
                   ┌─────────────────────────┐
                   │ probe_login_sync        │  MATZ-01 (sets _auth_failed flag)
                   └────────────┬────────────┘
                                │ if auth OK
                                ▼
            ┌────────────────────────────────────────────────────────┐
            │ ~25 PROBES en orden D-MATZ-29 (sync-only, no asyncio)  │
            │                                                        │
            │  Read sweep (16-17 probes):                            │
            │   ├─ segments / instruments (5 variants) / mkt data /  │
            │   │  trades / orders (3 account + 3 ID-scoped opt-in)/ │
            │   │  risk (3 Basic Auth)                               │
            │   └─ each: PrimaryAPI → _unwrap envelope → SafeModel   │
            │                                                        │
            │  Cross-cutting probes:                                 │
            │   ├─ probe_field_type_map (diff bidir 11 models)       │  MATZ-03
            │   ├─ probe_error_bogus_symbol/invalid_acct/bad_cfi     │  MATZ-05
            │   ├─ probe_schema_snapshot (16-19 archivos)            │  DRIFT-01 mirror
            │   └─ probe_cycle_closure × 4 packages                  │  DRIFT-02
            └────────────────────────────────────┬───────────────────┘
                                                 │
                       ┌─────────────────────────┼──────────────────────────┐
                       │                         │                          │
                       ▼                         ▼                          ▼
            ┌──────────────────────┐  ┌────────────────────┐    ┌──────────────────────┐
            │ stdout verbatim      │  │ findings.md        │    │ schemas/matriz/*.json │
            │ PROBE x: PASS|FAIL|  │  │ (idempotent append)│    │ envelope D-21 +       │
            │ SKIPPED|FINDING      │  │ + ## Cycle Closure │    │ D-25 no-overwrite-on- │
            │ SUMMARY: ...         │  │ × 4 pkgs           │    │ drift                 │
            └──────────────────────┘  └──────────┬─────────┘    └──────────────────────┘
                                                 │
                                                 ▼
                                    ┌────────────────────────┐
                                    │ verify_cycle_closure() │  D-MATZ-28
                                    │ for each of 4 pkgs     │
                                    └──────────┬─────────────┘
                                               │
                                               ▼
                                  CYCLE-REPORT.md (D-MATZ-26)
                                  4 dims: stats / cross-cycle /
                                  open questions / schemas summary
```

### Recommended Project Structure

```text
market-libs/
├── main_matriz.py                                          # REWRITE: ~25 probes
├── main_higyrus.py                                         # REFACTOR (D-MATZ-20): use helper from barrel
├── verification/
│   ├── __init__.py                                          # UPDATE: add diff_safemodel_bidirectional + verify_cycle_closure exports
│   ├── safemodel_diff.py                                    # NEW (D-MATZ-18)
│   ├── cycle_report.py                                      # NEW (D-MATZ-28)
│   ├── findings.py                                          # (unchanged unless CYCLE-CLOSURE class agregada — discretion D-MATZ-28)
│   ├── env_gate.py                                          # (unchanged)
│   ├── mutation_gate.py                                     # (unchanged)
│   ├── redaction.py                                         # (unchanged)
│   ├── schema.py                                            # (unchanged)
│   ├── capture.py                                           # (unchanged)
│   └── anonymize.py                                         # (unchanged, no usage in Phase 5)
├── packages/matriz-client/
│   ├── src/matriz_client/
│   │   ├── client.py                                        # MODIFY: + _unwrap helper, 18 sites refactored, _token assert→raise, docstring warnings new_order/replace/cancel
│   │   ├── exceptions.py                                    # (unchanged; possible micro-edit docstring de PrimaryAPIError.description per discretion)
│   │   ├── models.py                                        # (unchanged)
│   │   ├── types.py                                         # (unchanged)
│   │   ├── ws_client.py                                     # (OUT OF SCOPE — no se toca)
│   │   └── __init__.py                                      # (unchanged)
│   ├── tests/
│   │   ├── conftest.py                                      # (unchanged — autouse _configure_sync precarga _token)
│   │   ├── test_client.py                                   # MODIFY: append # ------ Verified live (Phase 5) ------ + # ------ Regressions ------ + MATZ-06 mock-only contract
│   │   └── test_*.py                                        # (other test files unchanged)
│   └── .env.example                                         # MODIFY: append 5 opt-in env vars (PRIMARY_ACCOUNT, MATRIZ_SAMPLE_*)
├── .planning/verification/
│   ├── matriz-client-findings.md                            # NEW (generado por driver + EXPECTED terminal D-MATZ-27 + ## Cycle Closure)
│   ├── ambito-financiero-client-findings.md                 # MODIFY: append ## Cycle Closure
│   ├── iol-client-findings.md                               # MODIFY: append ## Cycle Closure
│   ├── higyrus-client-findings.md                           # MODIFY: append ## Cycle Closure
│   ├── CYCLE-REPORT.md                                      # NEW (D-MATZ-26)
│   └── schemas/matriz-client/                               # NEW (~16-19 archivos)
│       ├── get-segments.json
│       ├── get-all-instruments.json
│       ├── get-instruments-details.json
│       ├── get-instrument-detail.json
│       ├── get-instruments-by-cfi-ESXXXX.json
│       ├── get-instruments-by-segment.json
│       ├── get-market-data.json
│       ├── get-trades.json
│       ├── get-active-orders.json  (si PRIMARY_ACCOUNT presente)
│       ├── get-filled-orders.json  (idem)
│       ├── get-all-orders.json     (idem)
│       ├── get-positions.json      (idem)
│       ├── get-detailed-positions.json
│       ├── get-account-report.json
│       └── (3 ID-scoped opt-in si MATRIZ_SAMPLE_* presentes)
```

### Pattern 1: `_unwrap` Envelope Helper (MATZ-04 fix de fase)

**What:** Helper privado en `client.py` que reemplaza `_get(...)[key]` raw indexing. Si la envelope key falta, levanta `PrimaryAPIError(status="ERROR", description="missing envelope key 'X' in response from <path>")` en vez de `KeyError` no mapeado.

**When to use:** En cada uno de los 18 sites enumerados D-MATZ-10. NO usar en `get_detailed_positions` ni `get_account_report` (retornan dict raíz directo al model — sin envelope key).

**Example:**

```python
# Source: D-MATZ-9 verbatim (CONTEXT.md L295-313)
# packages/matriz-client/src/matriz_client/client.py

def _unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    """Return ``data[key]`` or raise ``PrimaryAPIError`` if missing.

    Args:
        data: Decoded JSON response from ``_request``/``_get``.
        key: Envelope key expected to wrap the payload (e.g., ``"order"``).
        endpoint: Path that produced the response, used for error context.

    Raises:
        PrimaryAPIError: If ``key`` is absent from ``data``.
    """
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=f"missing envelope key '{key}' in response from {endpoint}",
            message=None,
        )
    return data[key]
```

**Refactor pattern (one of 18 sites):**

```python
# Antes:
def get_segments() -> list[Segment]:
    return [Segment.from_api(s) for s in _get("/rest/segment/all")["segments"]]

# Después:
def get_segments() -> list[Segment]:
    return [
        Segment.from_api(s)
        for s in _unwrap(_get("/rest/segment/all"), "segments", "/rest/segment/all")
    ]
```

**Regression test pattern (one per site, 18 total) — D-MATZ-11:**

```python
def test_get_segments_raises_primary_api_error_on_missing_envelope_key(httpx_mock: HTTPXMock) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={"some_other_key": []},  # missing "segments"
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_segments()
    assert "missing envelope key 'segments'" in (exc_info.value.description or "")
```

### Pattern 2: Bidirectional SafeModel Diff (MATZ-03, helper promotion D-MATZ-18)

**What:** Generador que itera `(path, direction, key)` por cada divergencia entre wire payload y declared model fields. `direction ∈ {'model-only', 'wire-only'}`:
- `'model-only'` = FALSE PASS riesgo (modelo declara, wire no emite → `SafeModel.from_api` sustituye default tipado sin levantar)
- `'wire-only'` = info (wire emite, modelo no declara → backend posiblemente agregó campo nuevo)

Recursivo en nested `_SafeModel` y en `list[_SafeModel]` (samplea primer elemento, consistente con `schema_of`).

**When to use:** En el probe `field_type_map` D-MATZ-29 #20 sobre los 11 modelos `_SafeModel` matriz, recursivo en nested (`InstrumentDetail.segment`, `Order.instrumentId`, `MarketDataSnapshot.{BI,OF,LA,SE,OI,CL}` → `MarketDataLevel` o `MarketDataEntryValue`, etc.).

**Example:**

```python
# Source: Phase 4 main_higyrus.py L234-293 (proven signature)
# verification/safemodel_diff.py — NEW D-MATZ-18

from __future__ import annotations

from collections.abc import Iterator
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

__all__ = ["diff_safemodel_bidirectional"]


def diff_safemodel_bidirectional(
    payload: Any,
    model_cls: type,
    path: str = "",
) -> Iterator[tuple[str, str, str]]:
    """Yield ``(path, direction, key)`` tuples for each model↔wire divergence.

    direction ∈ {'model-only' (FALSE PASS risk), 'wire-only' (info)}.

    Recursive on nested ``_SafeModel`` fields. For ``list[X]`` with
    ``X`` a ``_SafeModel`` subclass, samples first element of payload.
    """
    if not isinstance(payload, dict):
        return

    hints = get_type_hints(model_cls)
    model_keys = set(hints.keys())
    wire_keys = set(payload.keys())

    # Direction A: model declares, wire omits — FALSE PASS risk
    for key in sorted(model_keys - wire_keys):
        hint = hints[key]
        if _is_optional(hint):  # opt-in nullable, ausencia es esperada
            continue
        yield (path, "model-only", key)

    # Direction B: wire emits, model lacks — info only
    for key in sorted(wire_keys - model_keys):
        yield (path, "wire-only", key)

    # Recurse into nested SafeModels and list[SafeModel]
    for key in model_keys & wire_keys:
        hint = hints[key]
        nested_payload = payload[key]
        nested_cls = _nested_safemodel_class(hint)
        if nested_cls is None:
            continue
        if _is_list_of_safemodel(hint):
            if isinstance(nested_payload, list) and nested_payload:
                yield from diff_safemodel_bidirectional(
                    nested_payload[0], nested_cls, f"{path}.{key}[0]"
                )
        else:
            yield from diff_safemodel_bidirectional(
                nested_payload, nested_cls, f"{path}.{key}"
            )
```

**Critical:** El helper consume `_SafeModel` subclass (base de modelos higyrus/matriz). El check `isinstance(hint, type) and issubclass(hint, SafeModel)` requiere conocer la base. **Decisión de planner:** importar `SafeModel` desde el cliente que llama, o usar duck-typing via `hasattr(cls, "from_api")` + `dataclasses.fields()`. Phase 4 usó import directo de `higyrus_client.models.SafeModel`. Phase 5 puede:
1. Hacer el helper genérico (duck-typed): `hasattr(cls, "from_api") and dataclasses.is_dataclass(cls)` — recomendado para reusabilidad cross-package
2. Pasar la base class como parámetro: `diff_safemodel_bidirectional(payload, model_cls, *, base_cls=_SafeModel)`

Mirror exacto de Phase 4 (import directo de la base del paquete que se está testeando) es lo más fácil de migrar — el helper recibe la model_cls y puede importar perezosamente la base. Decidir en planning si vale generalizar.

### Pattern 3: Live Driver Probes (D-MATZ-29 lifecycle)

**What:** ~25 funciones nombradas `probe_<name>()` que retornan `ProbeResult(name, status, detail)`. El `main()` las ejecuta en orden y al final imprime las líneas `PROBE <name>: <status> <detail>` + `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`.

**When to use:** `main_matriz.py` rewrite completo (D-MATZ-29). Lifecycle es síncrono puro (no `asyncio.run`, D-MATZ-30).

**Example pattern (per Phase 4 main_higyrus.py L191-198):**

```python
@dataclass(frozen=True, slots=True)
class ProbeResult:
    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str


def probe_get_segments() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe N: read + envelope ["segments"]; resuelve _resolved_segment."""
    if _auth_failed:
        return (ProbeResult("get_segments", "SKIPPED", f"auth failed: {_auth_failure_reason}"), None)

    global _resolved_segment
    base_url = matriz_client.client._base_url
    try:
        raw = matriz_client.client._request("GET", "/rest/segment/all")
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(_PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                       title="get_segments PrimaryAPIError inesperado",
                       expected="200 OK + dict con envelope 'segments'",
                       actual=repr(exc), diff=f"description={exc.description!r}",
                       base_url=base_url)
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)

    segments_raw = raw.get("segments")
    if not isinstance(segments_raw, list):
        fid = _next_fid()
        # ... finding SHAPE OPEN
        return (ProbeResult("get_segments", "FINDING", f"{fid} (OPEN)"), None)

    # Resolve _resolved_segment from first segment for downstream probes
    if segments_raw:
        first = segments_raw[0]
        if isinstance(first, dict):
            _resolved_segment = first.get("marketSegmentId")

    return (ProbeResult("get_segments", "PASS", f"{len(segments_raw)} segments"), segments_raw)
```

**Verbatim stdout strings (D-02 Phase 2):**
- `PROBE <name>: PASS [<detail>]`
- `PROBE <name>: FAIL [<detail>]`
- `PROBE <name>: SKIPPED (<reason>)`
- `PROBE <name>: FINDING <fid>[, <fid>...] (<status>)`
- `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`

### Pattern 4: Schema Snapshot Envelope D-21 + D-25 No-Overwrite-on-Drift

**What:** Cada snapshot file en `.planning/verification/schemas/matriz-client/<func>.json` es un envelope con 6 keys: `endpoint`, `client_function`, `captured_at`, `base_url`, `sample_params`, `schema`. El `schema` viene de `schema_of(raw)` — solo nombres de tipo, PII-free por construcción.

**When to use:** Probe `schema_snapshot` D-MATZ-29 #24 + cada Risk API endpoint. Genera ~16-19 archivos committeables.

**D-25 no-overwrite-on-drift:** Si el archivo existe y el `schema` actual difiere del committed, NO sobreescribir — emitir finding `SHAPE` OPEN con expected/actual JSON, dejando que el operador clasifique.

**Example envelope (verbatim Phase 4 baseline):**

```json
{
  "endpoint": "/rest/segment/all",
  "client_function": "get_segments",
  "captured_at": "2026-06-10T15:32:01.234567+00:00",
  "base_url": "https://api.remarkets.primary.com.ar",
  "sample_params": {},
  "schema": {
    "segments": [
      {"marketId": "str", "marketSegmentId": "str"}
    ],
    "status": "str"
  }
}
```

### Pattern 5: MATZ-06 Mock-Only Contract — GET-as-Write Quirk Lock

**What:** 11 tests mockeados en `test_client.py` que verifican: (1) URL exacta con query string verbatim para los 5 escenarios de `new_order` + 1 `replace_order` + 1 `cancel_order`; (2) 3 sentinels que asertan `request.method == "GET"` para documentar el quirk §6.3.

**When to use:** Sección `# ------ Verified live (Phase 5) ------` o `# ------ Regressions ------` (decidible por planner; recomendado Verified-live para los 7 happy-path + sentinel para los 3 GET-quirk).

**Example (D-MATZ-16 verbatim):**

```python
def test_new_order_uses_GET_method_per_primary_api_quirk(httpx_mock: HTTPXMock) -> None:
    """GET-as-write quirk: Primary API mandates GET for order mutations (§6.3).

    Never refactor to POST without explicit API confirmation — this test
    breaks if anyone changes the method.
    """
    httpx_mock.add_response(
        url=(
            "https://api.test/rest/order/newSingleOrder"
            "?marketId=ROFX&symbol=X&side=BUY&orderQty=1&ordType=LIMIT"
            "&timeInForce=DAY&account=ACC&cancelPrevious=False&iceberg=False&price=100.0"
        ),
        method="GET",
        json={"order": {"clientId": "C", "proprietary": "P"}},
    )
    result = matriz_client.new_order("X", "BUY", 1, "ACC", price=100.0)
    [request] = httpx_mock.get_requests()
    assert request.method == "GET", "Primary API §6.3 mandates GET for order submission"
    assert result.clientId == "C"
    assert result.proprietary == "P"
```

### Pattern 6: Cascade SKIPPED tras login failure (D-MATZ-31, mirror D-IOL-3)

**What:** Flag module-level `_auth_failed: bool = False`. Cada probe downstream checkea al inicio: `if _auth_failed: return ProbeResult("<name>", "SKIPPED", "auth failed")`.

**When to use:** Todos los probes después del `probe_login_sync`. Implementación discrecional (flag, decorator, early-return) — D-MATZ-31 sugiere flag por simplicidad y mirror de IOL/HIGY.

### Anti-Patterns to Avoid

- **No retries / loops contra Primary** — Anti-feature (rate-limit/lockout risk). Cada probe es single-shot; el driver corre una sola vez por sesión.
- **No ejercitar mutaciones live, ni siquiera con `VERIFY_MUTATING=1`** — MATZ-06 es mock-only por diseño. El hostname remarkets assert + `mutating_allowed()` son belt-and-suspenders, pero **el driver Phase 5 NO debe contener llamadas a `new_order`/`replace_order`/`cancel_order` reachables**.
- **No imprimir payloads crudos en stdout** — Discipline D-HIGY-2 inherited: solo conteos + shape descriptors. El `safe_print(secrets=[...])` D-MATZ-32 es defensa en profundidad.
- **No commitear `.env`** — `.gitignore` cubre; verificar pre-commit.
- **No assumir `_token is not None` con `assert`** — CONCERNS.md L52-55; usar `raise RuntimeError` D-MATZ-12.
- **No agregar `aio.py` a matriz** — sync-only por diseño.
- **No ejercitar `auth_401` live** — REQUIREMENTS.md Out of Scope; mock-only.
- **No usar mismatch silencioso entre conteo "13" del context inicial y los 18 reales** — verificado por grep: hay 18 sites `_get(...)[key]`, no 13. El conteo real manda.
- **No ejecutar el driver contra prod (`api.primary.com.ar`)** — Hostname assert D-MATZ-33 aborta antes del primer call.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detectar field drift wire↔model | Loop manual + `dataclasses.fields()` | `verification.safemodel_diff.diff_safemodel_bidirectional` (NUEVO D-MATZ-18, signature ya validada Phase 4) | Recursivo en nested + list[Model], maneja Optional/Union, sample primer elemento — todo edge case ya cubierto |
| Snapshot de estructura JSON sin valores | `json.dumps(payload)` directo (filtra PII manual) | `verification.schema.schema_of` | PII-free por construcción; reemplaza valores por nombres de tipo |
| Generar / actualizar `findings.md` | Markdown manual con regex | `verification.findings.append_finding` | Idempotent por fid; preserva status humano CONFIRMED/FIXED/EXPECTED/NO-FIX; refresca ART block; valida class/status; CR-01/CR-02/WR-04 hardened |
| Skip-clean si faltan credenciales | `sys.exit(1)` con mensaje custom | `verification.env_gate.require_env` | Stdout verbatim "SKIPPED <pkg>: missing X, Y" + return False (caller decide exit con código 0) |
| Redactar tokens en logs | `replace(token, "...")` manual | `verification.redaction.safe_print(text, secrets=[...])` | Defensa en profundidad: secrets list + regex `Bearer <token>` pattern; threshold de 4 chars previene bug `replace("", marker)` |
| Mutación-gate para órdenes (defense in depth) | `if os.getenv("VERIFY_MUTATING") == "1"` directo | `verification.mutation_gate.mutating_allowed` | Doble gate (env + hostname); hostname check via `urlsplit().hostname` exacto (no substring vulnerable) |
| Validar cycle closure end-to-end | Script ad-hoc por paquete | `verification.cycle_report.verify_cycle_closure` (NUEVO D-MATZ-28) | Parsea findings.md, valida regression test paths; reusable cross-package; emite tuple `(ok, missing_regressions)` |
| Mirror sync↔async test files para matriz | Crear `test_async_client.py` | **NO crear** — matriz es sync-only | `aio.py` no existe; CLAUDE.md "dual sync/async" NO aplica a matriz; Verified-live + Regressions van solo en `test_client.py` |
| URL building con query string para tests | Construir URL string manual | `httpx_mock.add_response(url="https://api.test/rest/...?param1=v1&param2=v2", method="GET", json={...})` | pytest-httpx normaliza URL comparison; permite verificar URL completa verbatim incluyendo query string para los 11 tests MATZ-06 |

**Key insight:** Phase 5 reusa 100% del harness construido en Phases 1-4. Los dos módulos nuevos (`safemodel_diff.py`, `cycle_report.py`) son extensiones del harness — el patrón `verification.<helper>` es el mecanismo de extensión, no se cambia. **No se reinventa nada del lifecycle, redacción, gating, ni helpers.**

## Common Pitfalls

### Pitfall 1: Conteo desactualizado de envelope sites (13 vs 18)

**What goes wrong:** El draft inicial de CONTEXT.md menciona "13 sites" para MATZ-04; el conteo real es 18 (verificado por `grep -n '\[".*"\]' client.py`).
**Why it happens:** Estimación temprana antes de inspección exhaustiva. La discusión en CONTEXT.md ya nota: "el conteo real son 18 sites; el conteo '13' inicial era un estimado".
**How to avoid:** Antes de codificar el refactor, el planner ejecuta `grep` exacto contra `client.py` y enumera los 18 sites verbatim. Las 18 regression tests deben ser 1:1 con los sites refactoreados.
**Warning signs:** Si el conteo final de regression tests es 13 y no 18, faltan 5 wraps sin coverage.

### Pitfall 2: HTTP Basic Auth en Risk API requiere `auth_basic` kwarg

**What goes wrong:** Si un probe Risk API (positions, detailedPosition, accountReport) olvida pasar `auth_basic=_risk_auth()`, falla con 401 porque envía `X-Auth-Token` en lugar de HTTP Basic.
**Why it happens:** `_get` por defecto usa token; solo `_request(method, path, auth_basic=...)` explícito invoca HTTP Basic.
**How to avoid:** En los 3 probes Risk API D-MATZ-29 #17-19, llamar `_request("GET", path, auth_basic=_risk_auth())` directo (NO `_get`).
**Warning signs:** Risk API probes fallan con 401 a pesar de credenciales válidas (las mismas que login token funciona).

### Pitfall 3: Market hours guard como gate del probe, no del run completo

**What goes wrong:** Implementar el guard D-MATZ-5 como check que aborta el driver si market cerrado; pierde shape coverage.
**Why it happens:** Confundir "MATZ-07 dice no asertar valores fuera de horas" con "no correr el probe".
**How to avoid:** El probe `get_market_data` SIEMPRE corre; el guard valida shape/type/presencia siempre. Solo emite finding `NO-DATA` OPEN si `LA.date` es stale > 2h, y skippea asserts de valor (no skippea el probe entero).
**Warning signs:** Si en horario cerrado el driver imprime `PROBE get_market_data: SKIPPED`, está mal — debe imprimir `PROBE get_market_data: PASS shape OK (LA.date stale 5h, no-value asserts)` o similar.

### Pitfall 4: Test de GET-as-write se "corrige" accidentalmente a POST

**What goes wrong:** Future contributor lee el código de `new_order` y "arregla" el método a POST porque "GET no debería mutar". Rompe el cliente contra Primary.
**Why it happens:** El quirk §6.3 es contraintuitivo; sin sentinel test, no hay defensa.
**How to avoid:** Los 3 sentinel tests D-MATZ-16 con docstring que cita §6.3 spec y `assert request.method == "GET"` rompen si alguien cambia el método. El docstring expand D-MATZ-17 en el cliente refuerza el warning.
**Warning signs:** Sentinel tests fallan después de un refactor "limpio" de mutación — el refactor es el bug.

### Pitfall 5: SafeModel false-pass trap (heredado de Phase 4)

**What goes wrong:** `SafeModel.from_api(payload)` con `payload` que omite un campo declared del modelo NO levanta — sustituye un default tipado (`None`/`0`/`""`/`[]`). El test `model = Model.from_api(raw); assert isinstance(model, Model)` siempre pasa, aún si el wire dropeó la mitad del payload.
**Why it happens:** Diseño deliberado para tolerancia (CLAUDE.md "tolerant deserialization"); pero rompe la verificación si el test es type-only.
**How to avoid:** Probe `field_type_map` D-MATZ-29 #20 con `diff_safemodel_bidirectional` detecta `model-only` keys → finding `SHAPE` OPEN con prefijo `(FALSE PASS riesgo)`. Mirror exacto del Phase 4 mechanism que detectó `Posicion.disponibleAjustado` ausente.
**Warning signs:** Si el driver imprime `PROBE field_type_map: PASS` cuando los modelos tienen Optional fields ausentes en wire, el helper no está recurseando en nested.

### Pitfall 6: ID-scoped order reads requieren orders pre-existentes que no se pueden descubrir

**What goes wrong:** `get_order_status(cl_ord_id, proprietary)`, `get_order_history(cl_ord_id, proprietary)`, `get_order_by_exec_id(exec_id)` requieren IDs tenant-specific. No hay API para listar IDs de órdenes existentes a priori (los account-scoped reads sí, pero requieren PRIMARY_ACCOUNT).
**Why it happens:** Tenant del operador puede no tener órdenes; en remarkets los datasets son volátiles.
**How to avoid:** D-MATZ-4 los marca opt-in vía `MATRIZ_SAMPLE_CL_ORD_ID` / `MATRIZ_SAMPLE_PROPRIETARY` / `MATRIZ_SAMPLE_EXEC_ID`. Sin estas env vars → SKIPPED con razón clara `(no orders to query — set MATRIZ_SAMPLE_CL_ORD_ID/PROPRIETARY/EXEC_ID to enable)`.
**Warning signs:** Si los 3 probes ID-scoped emiten FINDING en vez de SKIPPED cuando faltan las env vars, el driver está fail-closed en vez de skip-clean.

### Pitfall 7: `auth_basic` mode con _ensure_token() puede generar `_token = None` correcto

**What goes wrong:** El fix `_token` D-MATZ-12 (raise RuntimeError si `_token is None`) podría disparar incorrectamente en la rama `auth_basic` donde `_token = None` es esperado.
**Why it happens:** La rama `auth_basic` salta `_ensure_token()` enteramente; solo la rama no-auth_basic ejecuta `_ensure_token()` y luego asume `_token is not None`.
**How to avoid:** D-MATZ-12 verbatim — el `if _token is None: raise RuntimeError(...)` va DENTRO de la rama `else` (no-auth_basic), después de `_ensure_token()`. La rama `if auth_basic` queda intacta.
**Warning signs:** Risk API probes (que usan `auth_basic`) fallan con `RuntimeError: did not populate _token` aún teniendo creds válidas → el fix se aplicó fuera de la rama correcta.

### Pitfall 8: Driver corrido contra prod por error de configuración

**What goes wrong:** Operador setea `PRIMARY_BASE_URL=https://api.primary.com.ar` (sin "remarkets" en el host) y el driver dispara verificación contra prod, violando la safety policy del proyecto.
**Why it happens:** Override de env var es trivialmente fácil; sin guard, no hay detección.
**How to avoid:** D-MATZ-33 belt-and-suspenders hostname assert al inicio del driver. Si `"remarkets"` no está en `matriz_client.client._base_url`, ABORT con loud message + `sys.exit(1)`. Complementa el `mutating_allowed()` check existente (pero `mutating_allowed` solo se invoca antes de mutaciones live, y MATZ-06 es mock-only — así que el assert manual cubre el gap).
**Warning signs:** Si el operador pasa `PRIMARY_BASE_URL=https://api.primary.com.ar` y el driver NO aborta, falta el guard.

### Pitfall 9: Doble `-client` en findings file header (cosmético, Phase 3-4 inherited)

**What goes wrong:** El helper `write_findings("matriz-client")` emite `# Findings: matriz-client-client` (doble `-client`) en line 1 del findings file.
**Why it happens:** Cosmético; el header se construye con `f"# Findings: {pkg}-client"` pero el `pkg` ya tiene `-client` en el slug del proyecto (`matriz-client`, `iol-client`, etc.). Observado en Phases 3-4.
**How to avoid:** Aceptar la convención por consistencia con findings files existentes (ambito-financiero-client, iol-client, higyrus-client TODOS tienen doble `-client`). NO arreglar en Phase 5 — no bloquea, cualquier polish va a un milestone futuro.
**Warning signs:** Si el plan-checker exige header `# Findings: matriz-client` literal, falla el match. La convención del repo es match por substring `grep -F "# Findings: matriz-client"` (que pasa para `matriz-client-client`).

## Code Examples

Verified patterns from official sources (Phase 4 actual production code):

### Live driver structure (Phase 4 mirror, sync-only adaptation)

```python
# Source: main_higyrus.py lifecycle adapted for sync-only matriz
# market-libs/main_matriz.py

"""Driver de verificación en vivo del paquete ``matriz-client`` (Phase 5).

Ejecuta ~25 probes nombrados que ejercitan la superficie sync del cliente
Matriz contra ``https://api.remarkets.primary.com.ar`` (sandbox).
... [docstring completo según D-MATZ-29 sequence]
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from verification import (
    append_finding,
    diff_safemodel_bidirectional,
    require_env,
    safe_print,
    schema_of,
    write_findings,
)
from verification.cycle_report import verify_cycle_closure

import matriz_client as primary
from matriz_client import PrimaryAPIError
from matriz_client.types import CFICode

_PKG = "matriz-client"
_auth_failed: bool = False
_auth_failure_reason: str = ""
_resolved_symbol: str | None = None
_resolved_segment: str | None = None
_fid_counter: int = 0


def _next_fid() -> str:
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"


@dataclass(frozen=True, slots=True)
class ProbeResult:
    name: str
    status: str
    detail: str


# ... ~25 probe functions per D-MATZ-29 ...


def main() -> None:
    # Step 1: env gate
    if not require_env(_PKG, ["PRIMARY_USER", "PRIMARY_PASSWORD"]):
        sys.exit(0)

    # Step 2: belt-and-suspenders hostname assert (D-MATZ-33)
    base = primary.client._base_url
    if "remarkets" not in base:
        print(f"ABORT: PRIMARY_BASE_URL={base!r} is not a remarkets sandbox URL — "
              "Phase 5 verification is remarkets-only by safety policy")
        sys.exit(1)

    # Step 3: write skeleton if findings file missing
    write_findings(_PKG)

    # Step 4: execute probes in D-MATZ-29 order
    results: list[ProbeResult] = []
    today = dt.date.today()

    r1 = probe_login_sync()
    results.append(r1)

    # ... probes 2-25 ...

    # Step 5: cycle closure for 4 packages (D-MATZ-28)
    for pkg in ("ambito-financiero-client", "iol-client", "higyrus-client", "matriz-client"):
        ok, missing = verify_cycle_closure(pkg)
        status = "PASS" if ok else "FAIL"
        detail = "" if ok else f" — missing regressions: {', '.join(missing)}"
        results.append(ProbeResult(f"cycle_closure_{pkg.replace('-', '_')}", status, detail))
        if not ok:
            fid = _next_fid()
            append_finding(
                pkg, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                title=f"cycle closure: {len(missing)} CONFIRMED/FIXED without regression test",
                expected="every CONFIRMED/FIXED finding linked to existing test path",
                actual=f"missing regressions: {', '.join(missing)}",
                diff="see verify_cycle_closure output",
            )

    # Step 6: D-MATZ-27 EXPECTED terminal for prod-vs-remarkets gap
    fid = _next_fid()
    append_finding(
        _PKG, fid=fid, class_="SHAPE", surface="sync", status="EXPECTED",
        title="prod-vs-remarkets divergence acknowledged",
        expected=("verification limited to remarkets sandbox by safety policy "
                  "(REQUIREMENTS.md Out of Scope)"),
        actual=("prod (api.primary.com.ar) shape unverified; sandbox shape "
                "committed in .planning/verification/schemas/matriz-client/"),
        diff="N/A (acknowledged limitation, not detected drift)",
    )

    # Step 7: emit verbatim PROBE lines + SUMMARY
    secrets = [os.getenv("PRIMARY_USER") or "", os.getenv("PRIMARY_PASSWORD") or ""]
    token = getattr(primary.client, "_token", None)
    if token:
        secrets.append(token)

    counts = {"PASS": 0, "FAIL": 0, "SKIPPED": 0, "FINDING": 0}
    for r in results:
        line = f"PROBE {r.name}: {r.status} {r.detail}".strip()
        safe_print(line, secrets)
        counts[r.status] = counts.get(r.status, 0) + 1

    summary = (
        f"SUMMARY: PASS={counts['PASS']} FAIL={counts['FAIL']} "
        f"SKIPPED={counts['SKIPPED']} FINDING={counts['FINDING']}"
    )
    safe_print(summary, secrets)


if __name__ == "__main__":
    main()
```

### `_unwrap` site refactor (one of 18, full pattern)

```python
# Source: D-MATZ-10 #16 verbatim — get_market_data
# packages/matriz-client/src/matriz_client/client.py

# Antes:
def get_market_data(
    symbol: str,
    entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
    *,
    market_id: MarketId = "ROFX",
    depth: int | None = None,
) -> MarketDataSnapshot:
    """Return real-time market data for an instrument (§8.1)."""
    return MarketDataSnapshot.from_api(
        _get(
            "/rest/marketdata/get",
            marketId=market_id,
            symbol=symbol,
            entries=",".join(entries),
            depth=depth,
        )["marketData"]
    )

# Después:
def get_market_data(
    symbol: str,
    entries: Sequence[MarketDataEntry] = DEFAULT_MARKET_DATA_ENTRIES,
    *,
    market_id: MarketId = "ROFX",
    depth: int | None = None,
) -> MarketDataSnapshot:
    """Return real-time market data for an instrument (§8.1)."""
    path = "/rest/marketdata/get"
    return MarketDataSnapshot.from_api(
        _unwrap(
            _get(path, marketId=market_id, symbol=symbol,
                 entries=",".join(entries), depth=depth),
            "marketData",
            path,
        )
    )
```

### Error probe with HTTP 4xx vs `{"status":"ERROR"}` distinction (D-MATZ-23)

```python
# Source: D-MATZ-23 verbatim (CONTEXT.md L498-519)

def probe_error_bogus_symbol() -> ProbeResult:
    """Probe error #1: bogus symbol → expect PrimaryAPIError, distinguish HTTP 4xx unmapped."""
    if _auth_failed:
        return ProbeResult("error_bogus_symbol", "SKIPPED", f"auth failed: {_auth_failure_reason}")

    base_url = primary.client._base_url
    try:
        primary.get_market_data("ZZZZZZ-NOT-A-SYMBOL")
    except PrimaryAPIError as e:
        if e.status == "ERROR":
            return ProbeResult(
                "error_bogus_symbol", "PASS",
                f"PrimaryAPIError as expected: {e.description}",
            )
        # Otherwise unexpected status — finding
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
            title="PrimaryAPIError with non-ERROR status",
            expected="PrimaryAPIError(status='ERROR') for bogus symbol",
            actual=f"PrimaryAPIError(status={e.status!r}, description={e.description!r})",
            diff="status != 'ERROR'", base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")
    except httpx.HTTPStatusError as e:
        # FINDING: bug — error HTTP no mapeado a la jerarquía
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
            title="HTTP 4xx not mapped to PrimaryAPIError",
            expected="PrimaryAPIError wrap for any error response",
            actual=f"httpx.HTTPStatusError {e.response.status_code} raw",
            diff="error mapping bypass — _raise_for_response missing or order incorrect",
            base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")
    except Exception as e:
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
            title=f"unexpected {type(e).__name__} from get_market_data bogus symbol",
            expected="PrimaryAPIError(status='ERROR')",
            actual=repr(e), diff=f"type={type(e).__name__}", base_url=base_url,
        )
        return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")

    # Si no levantó nada, también es finding
    fid = _next_fid()
    append_finding(
        _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
        title="get_market_data bogus symbol did not raise",
        expected="PrimaryAPIError(status='ERROR') for ZZZZZZ-NOT-A-SYMBOL",
        actual="no exception raised",
        diff="error path bypass", base_url=base_url,
    )
    return ProbeResult("error_bogus_symbol", "FINDING", f"{fid} (OPEN)")
```

## Runtime State Inventory

Phase 5 NO es un rename/refactor/migration phase puro. Es una phase de verificación + 2 fixes opportunistic in-cycle (MATZ-04 envelope + `_token` assert) + 2 módulos nuevos del harness + 1 refactor in-cycle de `main_higyrus.py`. La sección es relevante para los fixes opportunistic — completa los 5 categories:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — matriz no usa storage local; `_token` está en memoria del proceso, sin persistencia | None |
| Live service config | Primary API tenant config (cuenta, perms) vive en el servidor Primary, NO en código local; el operador setea `PRIMARY_USER/PASSWORD/ACCOUNT` por env | None desde código — operador gestiona su propio tenant |
| OS-registered state | None — driver es CLI one-shot; no daemon, no service, no scheduled task | None |
| Secrets/env vars | `.env` files en `packages/matriz-client/.env` (gitignored). Phase 5 agrega 5 env vars OPCIONALES: `PRIMARY_ACCOUNT`, `MATRIZ_SAMPLE_SYMBOL`, `MATRIZ_SAMPLE_CL_ORD_ID`, `MATRIZ_SAMPLE_PROPRIETARY`, `MATRIZ_SAMPLE_EXEC_ID`. Toda nueva env var debe documentarse en `.env.example` | Append 5 vars a `packages/matriz-client/.env.example` con comentarios D-MATZ-33; el `.env` del operador opcionalmente las setea, sin breakage si están ausentes |
| Build artifacts / installed packages | Pre-existing: `verification/__pycache__/` (gitignored). NUEVOS: `verification/safemodel_diff.py` + `verification/cycle_report.py` requieren que `verification/__init__.py` actualice exports D-MATZ-19 para ser importables desde el driver | Edit `verification/__init__.py` para exportar 2 helpers nuevos; nada que reinstalar — `verification/` no es paquete uv (es módulo local) |

**Nothing found in category:** Para Stored data, Live service config, y OS-registered state — explícitamente verificado.

## Common Pitfalls

(Ya incluidos arriba en sección Common Pitfalls — 9 pitfalls completos.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw `_get(path)[key]` indexing → `KeyError` no mapeado | `_unwrap(_get(path), key, path)` → `PrimaryAPIError` tipado | Phase 5 (MATZ-04 fix de fase) | Callers que catchean `PrimaryAPIError` siguen funcionando; shape-mismatch se distingue via `description.startswith("missing envelope key")` |
| `assert _token is not None` (stripped por `python -O`) | `if _token is None: raise RuntimeError(...)` | Phase 5 (D-MATZ-12, CONCERNS.md L52-55) | En producción con `-O`, crash con NoneType convierte a RuntimeError con diagnóstico claro |
| `_diff_safemodel_bidirectional` inline en `main_higyrus.py` (Phase 4) | Promovido a `verification/safemodel_diff.py` con barrel export | Phase 5 (D-MATZ-18..20, condicional ya cumplida) | Reusable cross-package; `main_higyrus.py` y `main_matriz.py` consumen del mismo helper centralizado |
| Findings independientes por paquete sin cierre cross-cycle | `## Cycle Closure` appended + `CYCLE-REPORT.md` consolidado + `verify_cycle_closure` automated check | Phase 5 (DRIFT-02, D-MATZ-25..28) | Cierre del ciclo es verificable automáticamente; el driver detecta CONFIRMED/FIXED sin regression test y emite finding nuevo |
| Sample tickers/cuentas hardcoded en drivers | Resolución dinámica desde primer elemento de listado, con override env var | Phase 5 (D-MATZ-1, D-MATZ-2, mirror D-IOL-18) | Cero mantenimiento de tickers que expiran; mismo patrón que Higyrus D-HIGY-11 |
| Mock testing de mutaciones sin sentinel del método HTTP | Sentinel `assert request.method == "GET"` con docstring citando §6.3 spec | Phase 5 (D-MATZ-16, NUEVO en el ciclo) | Defense contra refactor "limpio" que cambie GET→POST por intuición; el cliente queda bloqueado contra Primary |

**Deprecated/outdated:**
- Conteo "13 sites" del CONTEXT.md draft inicial — conteo real es **18** (verificado vía grep, ya documentado en CONTEXT.md L344 nota).
- Tabla horaria MATBA hardcoded (alternativa considerada Q3 discussion) — rechazada en favor de probe-based staleness D-MATZ-5.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SafeModel` base class (matriz) y `SafeModel` base class (higyrus) son **diferentes clases con misma signature** — `from_api`/`empty` clasmethods + `__dataclass_fields__`. El helper promovido `diff_safemodel_bidirectional` debe funcionar con ambas vía duck typing o aceptando `base_cls` parámetro | Pattern 2 Bidirectional SafeModel Diff | Helper podría no aplicar correctamente a matriz si asume estructura higyrus-specific. Mitigación: usar duck typing (`hasattr(model_cls, 'from_api')`) en lugar de `issubclass(cls, SafeModel)`. La estructura de `matriz_client.models._SafeModel` es estructuralmente idéntica a `higyrus_client.models.SafeModel` (verificado leyendo ambos models.py) |
| A2 | Threshold 2h para `LA.date` staleness es suficiente para cubrir horario de mercado intra-día sin generar falsos `NO-DATA` | D-MATZ-5 / Pitfall 3 | Si remarkets tiene gaps de actualización > 2h durante horas de mercado, el guard emite falsos positivos. Discrecional en CONTEXT.md ("threshold discrecional pero documentado"). Mitigación: 2h es conservador; si surgen falsos positivos en prácticа, ajustar a 4h o usar timezone-aware check |
| A3 | El `## Cycle Closure` append a los 4 findings files preexistentes NO rompe el parser de `append_finding` en runs futuros | D-MATZ-25 / Pitfall 9 | `append_finding` hace re-serialización full del archivo a partir del modelo interno (`_serialize_findings`); la sección `## Cycle Closure` no está en su vocabulario → al próximo `append_finding` sobre el mismo paquete, la sección Cycle Closure podría ser dropeada (Phase 2 review-04 CR-01: "preservación de prosa humana SOLO funciona si status del finding != OPEN"). Mitigación: el append `## Cycle Closure` se hace como **última operación** del Phase 5 driver, después de cualquier `append_finding` sobre ese paquete. Phases futuras NO deben volver a llamar `append_finding` sobre paquetes ya cerrados — el cycle ya cerró |
| A4 | El conteo `~16-19` schema snapshots es correcto | Standard Stack + Project Structure | Si el operador no setea PRIMARY_ACCOUNT, los 4 Risk API + 3 account-scoped order reads no generan snapshot → conteo baja a ~11. Si tampoco setea MATRIZ_SAMPLE_*, los 3 ID-scoped no generan snapshot → ~11. Rango real depende de configuración. No es bloqueante: el plan acepta el rango |
| A5 | `verify_cycle_closure` no requiere import de pytest para verificar test paths existen | D-MATZ-28 | El parse es estructural (text del findings file), no requiere ejecutar pytest. CONTEXT.md verbatim: "el parse es estructural, no de pytest". El validador solo checkea que `<test_file>::<test_name>` matchee un path existente en el filesystem + que el test name aparezca como `def test_<name>` en el file. Mitigación: si el operador prefiere validación más estricta (pytest collect), eso queda fuera de scope |
| A6 | Los 3 error probes always-on D-MATZ-22 con bogus symbol/account/CFI NO disparan rate-limit ni lockout en remarkets | D-MATZ-22 / Out of Scope | Primary remarkets no documenta thresholds de rate-limit explícitos; 3 calls con inputs inválidos en una sesión es marginal. CONTEXT.md verbatim: "always-on (sin opt-in env var) porque son lookups read-only sin auth-flow involucrado — diferente de IOL/HIGY `auth_401` que dispara intentos de login fallidos (lockout risk real)". Mitigación: si el operador observa rate-limit en práctica, agregar opt-in env var |
| A7 | `httpx.HTTPStatusError` es la exception que Primary devuelve para HTTP 4xx no mapeado | Pattern 3 Live Driver + Pitfall 7 | El cliente actual hace `resp.raise_for_status()` en `_request` L165, lo cual sí levanta `httpx.HTTPStatusError`. Pero si Primary devuelve un body con `{"status":"ERROR"}` aún con HTTP 4xx, el chequeo posterior `if data.get("status") == "ERROR"` levanta `PrimaryAPIError` (NO `HTTPStatusError`). El orden importa: `raise_for_status` corre PRIMERO; si HTTP es 4xx, ya levantó. Solo si HTTP es 2xx + body tiene `status="ERROR"`, levanta `PrimaryAPIError`. El error probe D-MATZ-23 debe estar preparado para ambas exceptions (verbatim ejemplo en CONTEXT.md L498-519 cubre los dos) |

## Open Questions

1. **¿Cuántos snapshot files se commiten exactamente?**
   - What we know: el rango `~16-19` depende de PRIMARY_ACCOUNT (gate 6 probes) + MATRIZ_SAMPLE_* (gate 3 probes ID-scoped).
   - What's unclear: el operador puede correr el driver con o sin estas vars; el plan debe aceptar ambos paths.
   - Recommendation: el plan instruye al driver a generar snapshot solo para probes que PASS-aron. Skipped probes no generan snapshot. CYCLE-REPORT.md Schemas summary lista los que se generaron en el run final. **Aceptar variabilidad ~11-19**.

2. **¿Debe agregar `CYCLE-CLOSURE` al vocabulary `FINDING_CLASSES` o reusar `ERROR-MAP`?**
   - What we know: D-MATZ-28 discrecional; CONTEXT.md verbatim "El test class no está en el FINDING_CLASSES vocabulary de Phase 1 (`SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT/NO-DATA/ANTI-BOT`); usamos `ERROR-MAP` como el más cercano".
   - What's unclear: agregar `CYCLE-CLOSURE` requiere edit minimal en `verification/findings.py` L76-84 (`FINDING_CLASSES` tuple). Es un edit de 1 línea a un módulo LOCKEADO en Phase 1.
   - Recommendation: **Reusar `ERROR-MAP`** por YAGNI. Si futuros ciclos necesitan distinguir, extender vocabulary en ese momento. La validación de class is `if class_ not in FINDING_CLASSES: raise ValueError`, así que el reuso es trivial. Decidir en planning según preferencia del implementador.

3. **¿`diff_safemodel_bidirectional` debe ser duck-typed o aceptar base_cls?**
   - What we know: Phase 4 usa import directo de `higyrus_client.models.SafeModel`. Phase 5 reusa el helper pero con modelos de matriz cuya base se llama `_SafeModel` (con underscore, distinto del higyrus).
   - What's unclear: cómo el helper detecta "is this a SafeModel subclass" de forma cross-package.
   - Recommendation: **Duck typing** via `hasattr(cls, 'from_api') and dataclasses.is_dataclass(cls)`. Más reusable, menos imports cíclicos. Las 11 model classes matriz + 4 model classes higyrus son TODAS dataclasses con `from_api` classmethod → duck typing cubre ambas. Alternativa: parámetro opcional `base_cls` con default `None` (= duck-typed). El planner decide en el momento de implementar D-MATZ-18.

4. **¿La micro-edit del docstring de `PrimaryAPIError.description` es load-bearing?**
   - What we know: CONTEXT.md L1121-1123 sugiere "Posible micro-edit del docstring de `PrimaryAPIError.description` para documentar la convención 'missing envelope key X' como string-based marker (discrecional)".
   - What's unclear: discrecional según CONTEXT.md; no es requisito locked.
   - Recommendation: **Skip por YAGNI**. La convención queda documentada en el docstring del `_unwrap` helper + en los 18 regression tests. Si futuros callers necesitan distinguir programáticamente, agregar después.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Toda la fase | ✓ | 3.12.11 (active venv) | — |
| uv | Build/run | ✓ | 0.9.0 | — |
| `.env` con PRIMARY_USER + PRIMARY_PASSWORD | Live driver run (MATZ-01 y siguientes) | Operador-dependiente | — | `require_env` skip-clean si falta + `SKIPPED matriz-client: missing PRIMARY_USER, PRIMARY_PASSWORD` (sin breakage) |
| `.env` con PRIMARY_ACCOUNT | 6 probes account-scoped (Risk + order reads) | Operador-dependiente | — | SKIPPED selectivo si falta; el resto del driver corre normal (D-MATZ-3) |
| `.env` con MATRIZ_SAMPLE_CL_ORD_ID/PROPRIETARY/EXEC_ID | 3 probes ID-scoped order reads | Operador-dependiente | — | SKIPPED si faltan (D-MATZ-4); el resto del driver corre normal |
| Conexión a `api.remarkets.primary.com.ar` | Live driver run | Operador-dependiente | — | Sin fallback — el live driver no se ejecuta sin red. Mocked tests (test_client.py) son CI offline y no requieren red |
| `httpx`, `pytest-httpx`, `python-dotenv` | Toda la fase | ✓ | locked en `uv.lock` | — |
| Acceso a worktree git con permisos de commit | Plan workflow | ✓ | — | — |

**Missing dependencies with no fallback:** none (el driver es opt-in; sin `.env` corre tests mockeados y skipea live).

**Missing dependencies with fallback:** PRIMARY_ACCOUNT y MATRIZ_SAMPLE_* son todas opcionales con SKIPPED handling.

## Validation Architecture

Phase 5 SÍ tiene `nyquist_validation` enabled (config.json L23: `"nyquist_validation": true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ + pytest-httpx 0.34+ |
| Config file | `pyproject.toml` (root): `asyncio_mode="auto"`, `--strict-markers`, `--import-mode=importlib`, `addopts="-ra"` |
| Quick run command | `uv run pytest packages/matriz-client/ -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MATZ-01 | Login + lazy auth verified live | smoke (live driver) | `uv run --package matriz-client python main_matriz.py` (operador checkea SUMMARY: login_sync PASS) | Wave 2 — main_matriz.py rewrite |
| MATZ-02 | Read sweep cubierto por mocked invariants | unit | `uv run pytest packages/matriz-client/tests/test_client.py -k "verified_live" -x` | Wave 3 — append sección `# ------ Verified live (Phase 5) ------` |
| MATZ-03 | Bidirectional diff sin field-drops sin clasificar | smoke (live driver) + unit | live: probe_field_type_map; unit: helper tests si se promueve nuevo | Wave 1 — verification/safemodel_diff.py NEW + tests del helper |
| MATZ-04 | `_unwrap` levanta PrimaryAPIError tipado | unit | `uv run pytest packages/matriz-client/tests/test_client.py -k "missing_envelope" -x` | Wave 1 — 18 regression tests new |
| MATZ-05 | `{"status":"ERROR"}` → PrimaryAPIError en 3 condiciones | smoke (live driver) | live: probe_error_*; unit fallback mockeado existente | Wave 2 — main_matriz.py probes 21-23 |
| MATZ-06 | new/replace/cancel mock-only con GET-as-write quirk | unit | `uv run pytest packages/matriz-client/tests/test_client.py -k "new_order or replace_order or cancel_order" -x` | Wave 3 — append 11 tests mock-only |
| MATZ-07 | Market data shape/type/presence asserts (no values) | smoke (live driver) + unit | live: probe_get_market_data with staleness guard; unit: mocked shape assertion | Wave 2 — driver; Wave 3 — Verified-live mocked invariant |
| DRIFT-02 | Per-package cycle closure verified automatically | smoke (live driver) + unit | live: probe_cycle_closure × 4; unit: `uv run pytest verification/tests/test_cycle_report.py -x` | Wave 1 — verification/cycle_report.py NEW + tests; Wave 4 — driver invokes + CYCLE-REPORT.md commit |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/matriz-client/tests/test_client.py -q` (~50-70 tests post-Phase-5)
- **Per wave merge:** `uv run pytest -q` (full repo; ~250+ tests post-Phase-5, +18 MATZ-04 regressions +11 MATZ-06 mock-only +1 sentinel _token + N Verified-live invariants)
- **Phase gate:** `uv run pytest -q` + `uv run mypy --strict packages/matriz-client verification` + `uv run ruff check .` + `uv run ruff format --check .` — todo verde antes de `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `verification/safemodel_diff.py` — NEW (helper extracted from main_higyrus.py)
- [ ] `verification/cycle_report.py` — NEW (verify_cycle_closure implementation)
- [ ] Test file for `safemodel_diff` — recomendado tests propios (mirror Phase 2 plan 01 `test_findings_helper.py` precedent). Posible location: `packages/matriz-client/tests/test_safemodel_diff_helper.py` (sigue convention Phase 2)
- [ ] Test file for `cycle_report` — idem
- [ ] `main_matriz.py` rewrite — Wave 2
- [ ] Sección `# ------ Verified live (Phase 5) ------` en `test_client.py` — Wave 3
- [ ] Sección `# ------ Regressions ------` en `test_client.py` — Wave 1 (18 MATZ-04 + 1 sentinel _token)
- [ ] Append `## Cycle Closure` × 4 a findings files — Wave 4
- [ ] `CYCLE-REPORT.md` — Wave 4

*Framework install: none needed; pytest + pytest-httpx ya están en `uv.lock`.*

## Security Domain

Phase 5 `security_enforcement: true` (config.json L49). ASVS Level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `safe_print(secrets=[PRIMARY_USER, PRIMARY_PASSWORD, _token])` D-MATZ-32 protege Information Disclosure de credenciales; `_token` se agrega dinámicamente tras login exitoso (mirror D-IOL-7 / D-HIGY-15). Hostname assert D-MATZ-33 previene exfiltración cross-environment |
| V3 Session Management | yes | `_token` 23h TTL refreshed antes de 24h server-side; cached in module state, sin persistencia a disco. `configure()` resetea token cacheado |
| V4 Access Control | partial | El driver ejecuta READ-ONLY surface contra remarkets. La superficie destructiva (MATZ-06 new/replace/cancel) es mock-only por diseño (no reachable live). Belt-and-suspenders: `mutating_allowed()` + hostname assert D-MATZ-33 |
| V5 Input Validation | yes | Los 3 error probes always-on D-MATZ-22 ejercitan inputs inválidos (bogus symbol, invalid account, malformed CFI) y verifican que el cliente NO crashea inesperadamente (PrimaryAPIError vs HTTPStatusError). MATZ-04 fix promueve `KeyError` no mapeado a `PrimaryAPIError` típado |
| V6 Cryptography | n/a | Sin cripto nuevo. httpx maneja TLS contra remarkets |
| V7 Error Handling and Logging | yes | Toda emisión de finding usa `append_finding` que valida class/status/title (CR-01/CR-02/WR-04 hardened en Phase 2). Toda emisión de stdout usa `safe_print(secrets)` D-MATZ-32. Schemas committeables son PII-free por construcción (`schema_of`) |
| V8 Data Protection | yes | Matriz **NO tiene PII** (datos de trading sin información personal; accountId es ID interno tenant). Schema-only commit policy (no fixtures crudos). `verification.capture` disponible pero gitignored. `verification.anonymize` NO usado en Phase 5 |
| V12 File and Resources | yes | Findings file path validado por `_PKG_SLUG_RE` (WR-04 anti path-traversal). Schema files en path predecible bajo `.planning/verification/schemas/<pkg>/` |
| V13 Configuration | yes | `.env` files gitignored; `.env.example` documenta vars; `require_env` fail-clean si faltan; nunca echo de credenciales |
| V14 Data Validation Sanitization | partial | Inputs inválidos manejados via PrimaryAPIError; output del schema_of es PII-free |

### Known Threat Patterns for Phase 5 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credenciales leak en stdout/logs | Information Disclosure (T-5-I) | `safe_print(secrets=[PRIMARY_USER, PRIMARY_PASSWORD, _token])` D-MATZ-32; `_BEARER` regex en `redaction.py` cubre tokens reflejados |
| Mutation accidental contra prod | Tampering | Hostname assert D-MATZ-33 al inicio (ABORT); `mutating_allowed()` doble gate; MATZ-06 mock-only por diseño (no live reachable) |
| Schema drift no detectado | Tampering | D-25 no-overwrite-on-drift: si schema actual ≠ committed → finding SHAPE OPEN, NO se sobreescribe baseline |
| KeyError no mapeado expone internals | Information Disclosure / Repudiation | MATZ-04 fix: `_unwrap` levanta `PrimaryAPIError` típado con `description` controlled. Callers que catchean `PrimaryAPIError` no ven internals; el `description` es string predecible |
| `assert` stripped por `python -O` (T-4-08 inherited) | Tampering | `if _token is None: raise RuntimeError` D-MATZ-12. `raise` no se strippea |
| GET-as-write quirk "corregido" accidentalmente | Tampering | 3 sentinel tests D-MATZ-16 + docstring warning D-MATZ-17. Cualquier refactor a POST rompe los tests |
| Cycle closure incompleta (CONFIRMED sin regression test) | Repudiation | `verify_cycle_closure` D-MATZ-28 emite finding ERROR-MAP OPEN si detecta gap. CYCLE-REPORT.md documenta el cierre cross-package |
| Rate-limit / lockout en remarkets | DoS (T-5-D) | Single-shot driver, sin retries, sin loops; 3 error probes always-on son lookups simples; no auth-failed deliberado live |
| Path traversal en findings_path | Tampering | `_PKG_SLUG_RE` validation en `verification.findings` (WR-04 hardened Phase 2) |
| Prod-vs-sandbox gap unverified | Repudiation | D-MATZ-27 registra finding EXPECTED terminal; D-MATZ-33 hostname assert previene corrida accidental contra prod |

## Sources

### Primary (HIGH confidence — sources verified in this session)

- `/Users/sebadlf/development/becerra/market-libs/.planning/phases/05-matriz-verification/05-CONTEXT.md` (1273 líneas, lectura completa) — 33 decisiones lockeadas D-MATZ-1..D-MATZ-34
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/client.py` (416 líneas) — superficie sync REST, 18 envelope sites confirmados via grep
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/models.py` (395 líneas) — 11 modelos `_SafeModel` con `get_type_hints` introspection
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/exceptions.py` (33 líneas) — jerarquía `MatrizClientError` → `PrimaryAPIError` → `AuthenticationError`
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/types.py` (131 líneas) — 9 Literals + market data entries
- `/Users/sebadlf/development/becerra/market-libs/packages/matriz-client/src/matriz_client/__init__.py` (155 líneas) — 19 REST funcs + 11 modelos + 9 Literals + WS exports
- `/Users/sebadlf/development/becerra/market-libs/main_matriz.py` (current smoke driver, 58 líneas)
- `/Users/sebadlf/development/becerra/market-libs/main_higyrus.py` (Phase 4 driver, ~2200 líneas — pattern source for D-MATZ-29 rewrite)
- `/Users/sebadlf/development/becerra/market-libs/verification/findings.py` (495 líneas — `append_finding` hardened)
- `/Users/sebadlf/development/becerra/market-libs/verification/env_gate.py`, `mutation_gate.py`, `redaction.py`, `schema.py`, `__init__.py` — todos los helpers existentes
- `/Users/sebadlf/development/becerra/market-libs/.planning/REQUIREMENTS.md` — MATZ-01..07 + DRIFT-02 verbatim
- `/Users/sebadlf/development/becerra/market-libs/.planning/ROADMAP.md` — Phase 5 goal + 5 success criteria
- `/Users/sebadlf/development/becerra/market-libs/.planning/STATE.md` — current position + blockers
- `/Users/sebadlf/development/becerra/market-libs/.planning/verification/{ambito,iol,higyrus}-client-findings.md` — Phase 2-4 findings files (targets del cycle closure append)
- `/Users/sebadlf/development/becerra/market-libs/.planning/phases/04-higyrus-verification/04-04-SUMMARY.md` + `04-01-SUMMARY.md` + `04-02-SUMMARY.md` + `04-03-SUMMARY.md` — Phase 4 patterns + retrospective
- `/Users/sebadlf/development/becerra/market-libs/.planning/phases/03-iol-verification/03-03-SUMMARY.md` — Phase 3 patterns
- `/Users/sebadlf/development/becerra/market-libs/.planning/phases/02-mbito-verification/02-01-SUMMARY.md` — `append_finding` foundation
- `/Users/sebadlf/development/becerra/market-libs/CLAUDE.md` — project constraints (tech stack, security, dependencies)
- `/Users/sebadlf/development/becerra/market-libs/.planning/config.json` — workflow flags (nyquist_validation, security_enforcement, code_review, etc.)

### Secondary (MEDIUM confidence — inferred from patterns)

- Patrón "dual sync/async" del CLAUDE.md NO aplica a matriz (verified by reading both `client.py` y la ausencia de `aio.py`) — Phase 5 es single-surface
- Conteo de 18 envelope sites (vs CONTEXT.md draft "13") — verified via `grep -n '\[.*"\]' client.py | grep -v "^[[:space:]]*#"` returning 19 hits, of which 1 (`params["price"]`) es asignación no envelope unwrap → 18 envelope sites reales

### Tertiary (LOW confidence — none required)

None. Toda la phase está pre-decidida; el research valida e inventa patrones.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — todos los helpers preexistentes leídos verbatim; sin packages externos nuevos
- Architecture: HIGH — todas las decisiones D-MATZ-1..34 lockeadas en CONTEXT.md (1273 líneas); el research solo traduce
- Pitfalls: HIGH — derivados de patterns reales observados en Phases 2-4 (e.g., Pitfall 5 SafeModel false-pass is the very mechanism Phase 4 caught Higyrus `Posicion.disponibleAjustado`)
- Security: HIGH — toda la categoría tiene mitigación pre-existente o decisión D-MATZ-* específica
- Validation: HIGH — el patrón Verified-live + Regressions sections está implementado en Phases 2-4; matriz singularizado por ausencia de async

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (30 días — stack stable, CONTEXT.md frozen)

---

*Phase: 05-matriz-verification*
*Research completed: 2026-06-09*
