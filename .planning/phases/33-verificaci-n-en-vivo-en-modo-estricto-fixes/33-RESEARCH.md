# Phase 33: Verificación en vivo en modo estricto + fixes - Research

**Researched:** 2026-08-26
**Domain:** Live API verification harness · Python `logging` handler bridging · strict-mode decode · findings pipeline
**Confidence:** HIGH (this is an internal-codebase phase; nearly every claim was read from the working tree or executed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Divergence handler architecture (`verification/divergences.py`)**

- **D-01:** El handler es una subclase de `logging.Handler` colgada del logger de cada uno de
  los 5 paquetes tipados (`ambito_financiero_client`, `higyrus_client`, `iol_client`,
  `matriz_client`, `market_data_client`), que mapea el `extra` de 6 claves (`package`,
  `divergence`, `field_path`, `declared_type`, `observed_type`, `model`) a
  `append_finding(pkg, class_="SHAPE", status="OPEN", idempotent_by_title=True, expected=…,
  actual=…, diff=…, …)` — diseño ya firmado en `29-AGGREGATION-CONTRACT.md` Lock 10, no se
  re-discute. `SHAPE` ya existe en `FINDING_CLASSES` (`verification/findings.py`), no se crea
  clase nueva.
- **D-02:** `endpoint` y `surface` (sync|async) llegan al handler vía un mecanismo owned by
  `verification/divergences.py` (contextvar o equivalente) que el driver setea antes de cada
  llamada al probe, reusando la convención existente `_ENDPOINT_TEMPLATES` /
  `probe_<func>_<sync|async>` — NUNCA agregando claves al registro de 6 claves de `_decode.py`
  (frozen por el gate de intactness 6-way entre paquetes). Recomendado: un decorator
  `@probe(endpoint, surface)` que en un solo edit por función de probe (a) bindea el contexto y
  (b) captura `<Pkg>DecodeError` para que el modo estricto no mate el driver — resuelve D-02 y
  D-05 en el mismo lugar.
- **D-03:** `main_market_data.py` necesita un `_ENDPOINT_TEMPLATES` nuevo (hoy solo tiene
  `_ENDPOINT_OPTIONAL`, no relacionado); los otros 4 drivers reusan el suyo existente.

**Modo estricto: modelo de ejecución y supervivencia del driver**

- **D-04:** El modo estricto solo no alcanza para el censo completo — levanta en la PRIMERA
  divergencia por respuesta (ej. S-2 predice 9 campos fabricados en `CalendarConfig`, estricto
  reporta 1). La corrida de cada driver es de **dos pasadas**: pasada observable
  (`strict_decode=False`, handler activo) primero para el censo completo, pasada estricta
  después para probar que el raise efectivamente dispara. Esto es lo que hace comparable el
  censo vivo contra el piso `≥ 96` de la Phase 29 (D-06 de 29-CONTEXT).
- **D-05:** `<Pkg>DecodeError` es HERMANO de `<Pkg>APIError` (no subclase) en los 5 paquetes —
  ningún manejo de excepciones existente en ningún driver lo captura hoy. Activar
  `strict_decode=True` sin más cambios mata el driver con traceback y cero findings. Fix:
  agregar `<Pkg>DecodeError` al tuple de excepciones capturadas por cada probe (via el
  decorator de D-02, o equivalente).
- **D-06:** NO se agrega un `except Exception` de nivel superior a `main_matriz.py` ni a
  `main_higyrus.py` — `verification/test_main_drivers_bare_except.py` lo prohíbe explícitamente
  vía AST gate para esos dos drivers y es una regresión de CI si se intenta. El catch debe ser
  por-probe (o por el decorator compartido), nunca un guard global bare-except.
- **D-07:** El catch manual existente de `HigyrusDecodeError` en `probe_get_health_sync`/`_async`
  (Phase 31) se elimina y se reemplaza por el mecanismo compartido — mantenerlo generaría un
  finding duplicado del que ya produce el handler automático (rompe el `idempotent_by_title`
  de Lock 10). No se replica ese patrón hand-rolled en los ~130 probes restantes.

**Cierre de Literals con evidencia real (criterio 3)**

- **D-08:** El walker NO emite ningún registro para un valor `Literal` fuera de set con tipo de
  runtime correcto (`policy.literal_enforced=False` en las 5 copias corta antes del sink). El
  stream de divergencias del handler de D-01 por sí solo NO produce el censo de Literals que
  pide el criterio 3 — se necesita un mecanismo separado: recolectar los valores crudos del wire
  que los drivers ya capturan (schema snapshots / raw payloads), no derivarlo de los findings
  SHAPE.
- **D-09:** Los 7 campos RESPONSE de matriz ya tipados con los 4 Literal aliases pre-existentes
  (`marketId`/`cficode`/`currency`/`orderTypes`/`ordType` en `models.py`) se resuelven
  **confirmando que decodean sin enforcement y registrando los valores observados** — NUNCA
  ampliando ni cerrando los aliases (D-09/`29-DLOCK-RESPONSE-LITERAL.md` lo prohíbe
  explícitamente este milestone; una ampliación sería su propia decisión con su propio artefacto
  firmado, fuera de este ciclo).
- **D-10:** `mercado`/`plazo` de iol (DT-07) quedan **`str` permanente, documentado como decisión
  explícita** — los drivers solo envían los defaults actuales (`"bcba"`/`"t2"`), sin evidencia
  del conjunto aceptado por el vendor. Un `Literal` incompleto rompe llamadas legítimas (peor que
  `str`). NO se agrega un sweep de prueba de valores candidatos contra la cuenta real de
  brokerage en este ciclo — la ausencia de evidencia ES la evidencia que cierra `str`.

**Vacuidad del gate, alcance del censo y disponibilidad de credenciales (criterios 4-5)**

- **D-11:** `verify_cycle_closure` solo inspecciona findings con status `CONFIRMED`/`FIXED`
  (`verification/cycle_report.py`) — un finding recién escrito por el handler en `OPEN` no
  cuenta. El criterio 4 solo es significativo DESPUÉS de que la triage (humana u operator-driven,
  igual que en fases previas) promueva las divergencias confirmadas a `CONFIRMED`/`FIXED` con
  link de regresión. No reportar "criterio 4 PASS" de una corrida donde el gate nunca inspeccionó
  un finding real.
- **D-12:** `ambito-financiero-client` es un no-op estructural bajo modo estricto (cero clases de
  modelo, cero llamadas al walker) — contribuye cero divergencias por construcción. Se incluye en
  el criterio 1 solo como smoke-test (correr en modo estricto y confirmar cero findings), sin
  presupuesto de triage/fix.
- **D-13:** Las corridas credencializadas están disponibles in-repo para iol/higyrus/matriz/
  market-data (`.env` presente en los 4 paquetes; ausente solo en ambito, consistente con su
  diseño sin auth) — market-data YA NO depende del workaround operator-paste de la Phase 23. La
  validez real de las credenciales es no verificable desde este entorno (contenido de `.env` no
  legible por permisos). El plan de Phase 33 debe incluir un pre-flight check por driver que
  confirme autenticación real (no-SKIP) antes de que cualquier número de censo cuente como
  válido; si un driver SKIPea por falta/expiración de creds, cae al fallback operator-runs-and-
  pastes documentado en Phase 23 para ese paquete específicamente.
- **D-14:** El riesgo de corrupción de schema snapshots por sitios estructurales de iol
  (30-CONTEXT D-07) YA ESTÁ CERRADO — `to_dict()` está confinado al parity probe
  (`main_iol.py:1215-1216`); los 4 sitios de snapshot consumen wire crudo vía
  `_capture_raw_wire`, sin cambios necesarios. No es un blocker de criterio 4.

### Claude's Discretion

- Forma exacta del decorator/mecanismo de D-02 (nombre, firma, si vive en
  `verification/divergences.py` o en un módulo nuevo) — research/planning decide la
  implementación concreta, la restricción es solo "no toca el registro de 6 claves de
  `_decode.py`".
- Formato exacto del censo de Literals de D-08/D-09/D-10 (script ad-hoc vs. extensión de un
  probe existente) — igual que el spike de sizing de la Phase 29, puede ser artefacto no
  committeado si el reporte final sí queda documentado.

### Deferred Ideas (OUT OF SCOPE)

- Ampliar o cerrar (enforcement) los Literal aliases pre-existentes de matriz
  (`CFICode`/`MarketId`/`OrderType`/`Currency`) — explícitamente fuera de este milestone
  (D-09), requeriría su propio artefacto firmado en una fase futura si se decide alguna vez.
- Sweep de prueba de valores candidatos de `mercado`/`plazo` contra la cuenta real de iol para
  intentar cerrar el `Literal` con más confianza — descartado en D-10 por generar tráfico 4xx
  deliberado contra un brokerage en vivo; si se hiciera, sería un plan aparte, no parte de este
  ciclo.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-TYP-01 | La nueva decodificación queda verificada contra las APIs reales (ámbito, iol, higyrus, matriz; market-data contra develop con creds del operator) en modo estricto; los `Literal` de DT-07 se cierran con evidencia real; toda divergencia se documenta como finding y se corrige in-cycle, espejada sync/async, con test de regresión mockeado; cycle closure PASS por paquete. | §Architecture Patterns (handler + probe-context decorator, two-pass runner), §Common Pitfalls P-1..P-3 (silent census loss — the three mechanisms that would make a live run report a false clean), §Pattern 5 (Literal census from raw wire, incl. the zero-risk `Titulo.mercado`/`Titulo.plazo` evidence source), §Validation Architecture (regression-test placement so `verify_cycle_closure` resolves), §Environment Availability (all 4 credential sets load; pre-flight recipe) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Directives extracted verbatim in force for this phase; the planner must verify compliance:

| # | Directive | Impact on Phase 33 |
|---|-----------|--------------------|
| C-1 | Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict — toda extensión y fix debe pasar el CI existente | No new runtime deps. `verification/divergences.py` must be stdlib-only. Regression tests use `pytest-httpx`. |
| C-2 | Estado singleton a nivel de módulo; **sin código compartido entre paquetes (por diseño)**. Los fixes se aplican dentro de cada paquete, sin dependencias cruzadas | The handler lives in `verification/` (repo-root harness, not a package) — that is legal. A fix to `_decode.py` would have to be applied 5× and re-pin the canonical digest. |
| C-3 | **Dual sync/async**: cualquier fix de lógica debe espejarse en `client.py` y `aio.py` del mismo paquete | Every in-cycle fix is a 2-file edit minimum (matriz now HAS `aio.py` — see State of the Art). |
| C-4 | Credenciales en `.env` por paquete; **nunca commitear `.env` ni exponer credenciales en logs, reportes o tests** | Findings files are committed. The 6-key record is type-not-value by construction (Lock 11) — do not widen it. `_redacted_exc` (iol) is the only authorized exception→text boundary in that driver. |
| C-5 | Dependencias externas en vivo: resultados varían por horario de mercado, datos disponibles o rate limits | The matriz run must be scheduled inside a trading session to resolve S-5; the ART block's `Market hours note` must be populated per run. |
| C-6 | GSD Workflow Enforcement: no direct repo edits outside a GSD workflow | Execution happens under `/gsd-execute-phase`. |
| C-7 | `from __future__ import annotations` mandatory in every module; ruff line-length 100, double quotes, 4 spaces; explicit `__all__` | Applies to `verification/divergences.py` and every new test file. |
| C-8 | Auto-loaded knowledge: `spike-findings-market-libs`, `spike-findings-codegen-market-libs` | **Checked — neither is relevant to this phase.** The first covers the matriz TokenStore 3-way concurrency primitive + refresh policy (Phase 10, already shipped and not touched here); the second is the codegen NO-GO close-out (permanently archived per DT-04). Neither informs strict-mode live verification. |

---

## Summary

Phase 33 is **not a feature phase**. Almost nothing needs to be *built*: the walker, the strict-mode
`ContextVar`, the `strict_decode` kwarg on all five `Client`/`AsyncClient` pairs, the six-key
divergence record, `append_finding`, `verify_cycle_closure` and the ~130 probes across five drivers
all exist and were verified in the working tree today. What Phase 33 must build is **one bridge**
(`verification/divergences.py`: `logging.Handler` → `append_finding`) plus **one per-probe context
mechanism**, and then run the drivers and triage what falls out.

The entire risk of the phase is therefore concentrated in **silent census loss** — a live run that
completes, prints a green SUMMARY, and reports far fewer divergences than actually occurred. This
research found **three independent, currently-live mechanisms** that each cause exactly that, and all
three are invisible from the driver's output:

1. **The package loggers are at `NOTSET` → effective level `WARNING`.** Every `extra`-kind divergence
   is emitted at `INFO` (Lock 3) and is therefore **dropped before any handler runs**. That is 32 of
   the 96 records in the ratified sizing floor — 33% — silently absent. Verified by execution.
2. **`_decode._emit` wraps the whole emission in `contextlib.suppress(Exception)`** (Lock 9). Any
   exception raised inside the new handler — a `ValueError` from `append_finding`'s class/status
   validation, an `OSError` on the findings file, a slug-validation failure — is swallowed with no
   trace. Verified by execution.
3. **Three of the five drivers never seed their fid allocator.** `main_higyrus.py`,
   `main_matriz.py` and `main_ambito_financiero.py` start `_fid_counter = 0`, while their committed
   findings files already hold `F-01…F-02`, `F-01…F-10` and `F-01` respectively — with statuses
   `NO-FIX`/`EXPECTED`/`FIXED` that trigger `append_finding`'s preservation short-circuit. Every
   finding those drivers emit at a colliding fid is a **silent no-op while the driver still counts it
   in `FINDING=N`**. `main_iol.py` and `main_market_data.py` already fixed this (`_seed_fid_counter`,
   D-16/D-24); the other three did not inherit the fix.

A fourth mechanism is not silent but is just as capable of derailing the phase: **`verification/` — the
directory this phase adds code to — is red today.** A full run measured `19 failed, 362 passed, 19
errors in 828s (13:48)`; **17 failures + 17 errors trace to a single stale test**,
`test_matriz_sweep_snapshot.py`, which still calls `probe_get_segments()` with no arguments and has
been broken since the Phase 15 driver migration threaded a `client` parameter into every probe.
Nothing caught it because that directory has never executed in CI. That is precisely the rot Phase 33
risks re-creating when it wraps ~130 probes in a decorator. The plan must **baseline the failures in
Wave 0**, audit every harness test that calls a probe directly, and gate on `packages/**` (what CI
actually enforces) plus a targeted subset — never on an unqualified `uv run pytest`, and never on a
14-minute full `verification/` run per commit.

The second-order finding is that **the strict-mode surface is not uniform across drivers**.
`main_iol.py` (12 `except Exception` sites), `main_market_data.py` (55) and
`main_ambito_financiero.py` (6) already *survive* strict mode today — they just misclassify the
`DecodeError` as `ERROR-MAP`/`NO-DATA` and mint a fresh fid per probe, polluting the census.
`main_higyrus.py` and `main_matriz.py` have **zero** `except Exception` (the AST gate forbids it) and
their `_RESIDUAL_PROBE_EXCEPTIONS` tuples do not include the decode error — those two, and only those
two, die on the first strict divergence. CONTEXT D-05's "ningún driver lo captura hoy" is accurate
for higyrus and matriz and inaccurate for the other three; the work is the same shape but the failure
mode differs, and the planner should size it accordingly.

Finally, the `Literal` census (criterion 3) genuinely needs its own mechanism, exactly as CONTEXT
D-08 states — but this research found a **zero-risk live evidence source for iol's `mercado`/`plazo`
that CONTEXT D-10 did not account for**: the `Titulo` model returned by
`get_instruments_by_type` (`/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos`) declares
`mercado: str` and `plazo: str` on *every instrument of the requested type across the venue*, and
`main_iol.py` already captures that endpoint's raw wire. That is a real RESPONSE-side census of both
vocabularies at zero extra traffic and zero deliberate-4xx risk. It does not overturn D-10 (the set a
vendor *emits* is not provably the set it *accepts*), but it converts D-10 from "closed for absence
of evidence" into "closed with evidence, and here is the evidence" — a materially stronger artifact.

**Primary recommendation:** Build `verification/divergences.py` as a self-counting, self-guarding
`logging.Handler` installed via a context manager that also raises each package logger to `INFO`;
pair it with one `@probe_context(endpoint, surface)` decorator that binds two `ContextVar`s and
extends each driver's existing exception tuple with its `<Pkg>DecodeError`; seed the fid allocator in
all five drivers from a **single shared allocator** the handler and driver both call; and gate the
whole census on a per-driver pre-flight that proves real authentication before any number is counted.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Divergence detection (model vs wire) | Package library (`<pkg>/_decode.py`) | — | Already shipped and hash-pinned. Phase 33 **reads** this tier; it must not write to it. |
| Strict-mode disposition (raise vs substitute) | Package library (`_decode.DecodeScope.__call__`) | Package `_ClientState.strict_decode` | Shipped. Activation is a constructor kwarg, nothing more. |
| Divergence transport | Python stdlib `logging` (package logger + `extra`) | — | Lock 1. The 6-key record is the frozen wire between tiers. |
| Divergence → finding translation | **Repo-root harness (`verification/divergences.py`) — NEW** | `verification/findings.py` | Lock 10 assigns this tier explicitly. It must not live in a package (C-2, no shared internals). |
| Endpoint + surface attribution | **Driver (`main_*.py`) — NEW per-probe binding** | `verification/divergences.py` (owns the ContextVars) | The record registry is frozen; the driver is the only tier that knows which endpoint a probe hits. |
| Probe survival under strict mode | Driver (`main_*.py` exception tuples) | shared decorator | Per-probe isolation is the established driver pattern (D-09/CR-06); a global guard is forbidden by the AST gate. |
| Census counting + floor contrast | Repo-root harness (in-run counters) + phase artifact | `29-SIZING.md` | The count unit must match the floor's unit: distinct `(model, field_path, kind)` triples per package. |
| Literal value census | **Ad-hoc script over raw wire / schema captures — NEW** | driver `_capture_raw_wire` / `.planning/verification/captures/` | The walker structurally cannot produce it (D-08). |
| In-cycle fixes | Package library (`client.py` + `aio.py`, `models.py`, `_core.py`) | — | C-3: mirrored sync/async, inside the owning package only. |
| Regression proof | `packages/<pkg>/tests/` (pytest + pytest-httpx) | `verification/cycle_report.py` | **Only `packages/**/tests/` runs in CI** — see Pitfall P-9. |

---

## Standard Stack

### Core

| Library | Version (verified installed) | Purpose | Why Standard |
|---------|------|---------|--------------|
| Python stdlib `logging` | 3.12.11 | `logging.Handler` subclass, `Logger.setLevel`, `LogRecord.__dict__` | Lock 1 already fixed `logging` as the transport; the handler is the receiving half of a contract that shipped in Phase 29. `[VERIFIED: 29-AGGREGATION-CONTRACT.md Lock 1]` |
| Python stdlib `contextvars` | 3.12.11 | `ContextVar` for `endpoint` / `surface` per-probe binding | The repo already uses `ContextVar` for exactly this shape (`_decode.STRICT_DECODE`, `_decode.DECODE_SCOPE`). Async-task-safe and thread-safe by construction. `[VERIFIED: packages/higyrus-client/src/higyrus_client/_decode.py:248-251]` |
| Python stdlib `functools.wraps` | 3.12.11 | Probe decorator identity preservation | `_decode._response_parser` is the in-repo precedent for a `functools.wraps` decorator around a probe-shaped callable. `[VERIFIED: _decode.py:310-322]` |
| `verification.findings.append_finding` | in-repo | Finding sink | Lock 10 names it as the target, `idempotent_by_title=True` already exists and does exactly the cross-driver dedupe the handler needs. `[VERIFIED: verification/findings.py:583-706]` |
| `pytest` | 9.0.3 | Regression tests | Already the repo runner. `[VERIFIED: uv run python -c "import pytest"]` |
| `pytest-httpx` | (installed, workspace dev dep) | Mocked regression tests per fix | The convention for every v1.0–v1.5 fix; `packages/higyrus-client/tests/test_decode.py:870+` is the exact template. `[VERIFIED: grep httpx_mock]` |
| `httpx` | 0.28.1 | Transport (unchanged) | `[VERIFIED: uv run python -c "import httpx"]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `json` | 3.12 | Literal-census script I/O over `.planning/verification/schemas/` + captures | The census script; same as `29-SIZING.md`'s throwaway script. |
| `verification.capture.capture` | in-repo | Dump raw wire to the gitignored staging dir | Feeding the Literal census with real values without committing them. `.planning/verification/captures/` is in `.gitignore` line 51. `[VERIFIED: .gitignore:51]` |
| `verification.schema.schema_of` | in-repo | Type-only snapshots (values never included) | Already wired into every driver; **cannot** serve the Literal census (it reduces every value to `"str"`). `[VERIFIED: verification/schema.py:27-40]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ContextVar` for endpoint/surface | Adding `endpoint`/`surface` keys to the `extra` registry | **Forbidden.** `tools/check_decode_intactness.py` pins the five `_decode.py` copies to a `CANONICAL_DIGEST`; any edit fails the `lint` CI job unless the digest is re-pinned, and Lock 1 freezes the key set. CONTEXT D-02 rules it out explicitly. |
| `ContextVar` | A module-global `_current_endpoint` string | Breaks under `asyncio` if any probe is ever gathered, and under the sync/async interleave in `main()`. `ContextVar` is the same primitive `_decode.py` already chose for the same problem. |
| One `@probe_context` decorator | Editing ~130 probes by hand | Hand-editing 130 probes is the D-07 anti-pattern (the `probe_get_health_sync` precedent) at 65× scale, and each edit is an independent chance to drift sync from async. |
| Two-pass by process re-run | Mutating `client._state.strict_decode` mid-run | A second pass in the same process reuses a client whose token/`httpx` pool/`_auth_failed` cascade already carry pass-1 state, and the driver's probe ordering (`main_market_data.py:3354-3365` — destructive sweep strictly after reads) is load-bearing. Two processes is cleaner and keeps the single-ctor AST gate satisfied. |
| Handler on the package logger | Handler on `logging.root` | **Forbidden.** `verification/test_logging_root_unchanged.py` + the CI `lint-logging` grep + ruff `LOG` rules are a three-layer guard. |

**Installation:** none. **This phase adds zero third-party dependencies.**

```bash
# no install step — verification only
uv sync --all-packages --all-extras --dev --frozen
```

**Version verification:** performed against the live workspace, not training data:

```bash
uv --version                       # uv 0.11.3
uv run python -c "import pytest, httpx; print(pytest.__version__, httpx.__version__)"
                                   # 9.0.3 0.28.1
uv run python -c "import sys; print(sys.version)"   # 3.12.11 (venv healthy)
```

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.**

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| *(none)* | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

Every module Phase 33 touches is either Python stdlib (`logging`, `contextvars`, `functools`, `json`,
`contextlib`) or already-committed in-repo code. The `.env`-driven live APIs are the only external
surface and they are pre-existing.

---

## Architecture Patterns

### System Architecture Diagram

```text
        ┌──────────────────────────── PASS 1: observable (strict_decode=False) ───┐
        │                                                                          │
   env / CLI flag                                                                  │
        │                                                                          │
        v                                                                          │
 ┌──────────────┐   require_env + live login pre-flight   ┌───────────────────┐    │
 │  main_<x>.py │ ────────────────────────────────────────>│ SKIP (exit 0) if  │    │
 │   main()     │                     (fails)              │ creds absent/dead │    │
 └──────┬───────┘                                          └───────────────────┘    │
        │ install_divergence_handler(pkgs, fid_allocator)                           │
        │   ├─ logger.setLevel(INFO)      <-- P-1: without this, 33% is dropped     │
        │   ├─ addHandler(DivergenceHandler)                                        │
        │   └─ seed fid allocator from max_existing_fid(pkg)   <-- P-3              │
        v                                                                           │
 ┌──────────────────────────────────────────────┐                                   │
 │  @probe_context(endpoint=..., surface=...)   │  binds ENDPOINT / SURFACE CVs     │
 │  def probe_get_movimientos_sync(client):     │  catches <Pkg>DecodeError -> SHAPE│
 └──────┬───────────────────────────────────────┘                                   │
        │ client.get_movimientos(...)                                               │
        v                                                                           │
 ┌───────────────────────────┐                                                      │
 │ <pkg>.Client._request     │  STRICT_DECODE.set(state.strict_decode)              │
 │                           │  open_request_scope()  -> fresh DecodeScope          │
 └──────┬────────────────────┘                                                      │
        │ httpx  ──────────────>  LIVE VENDOR API  ──────────>  raw JSON            │
        v                                                                           │
 ┌───────────────────────────┐                                                      │
 │ _core.parse_*  (@_response_parser)                                               │
 │   └─ models.from_api -> _decode.walk_model / walk_field                          │
 │        └─ sink(model, path, kind, declared, observed)                            │
 │             ├─ dedupe on (model, field_path, kind)   [Lock 5, per response]      │
 │             ├─ _emit(...)  inside contextlib.suppress(Exception)   <-- P-2       │
 │             │    ├─ kind=="extra"  -> logger.INFO                                │
 │             │    └─ else           -> logger.WARNING                             │
 │             └─ if strict and kind!="extra": raise <Pkg>DecodeError               │
 └──────┬────────────────────┘                                                      │
        │ LogRecord(extra = 6 keys)                                                 │
        v                                                                           │
 ┌────────────────────────────────────────────────────────────────────┐             │
 │ verification/divergences.py :: DivergenceHandler.emit(record)      │             │
 │   reads: record.package/divergence/field_path/declared_type/       │             │
 │          observed_type/model   +  ENDPOINT_CV.get() / SURFACE_CV   │             │
 │   counts: distinct (model, field_path, kind)  -> live census       │             │
 │   writes: append_finding(pkg, class_="SHAPE", status="OPEN",       │             │
 │                          idempotent_by_title=True, fid=alloc())    │             │
 │   NEVER raises out of emit()  (own try/except + error tally)       │             │
 └──────┬─────────────────────────────────────────────────────────────┘             │
        v                                                                           │
 .planning/verification/<pkg>-findings.md   +   schemas/<pkg>/*.json                │
        └──────────────────────────────────────────────────────────────────────────┘
                                       │
                                       v
        ┌──────────────── PASS 2: strict (strict_decode=True, mutations OFF) ───────┐
        │ proves the raise fires; probes degrade to SHAPE findings, driver survives │
        └──────────────────────────────────────────────────────────────────────────┘
                                       │
                                       v
              operator/agent triage: OPEN -> CONFIRMED/FIXED + Regression: link
                                       │
                                       v
              in-cycle fix (client.py + aio.py, mirrored)  +  packages/<pkg>/tests/…
                                       │
                                       v
              verify_cycle_closure(pkg) -> (True, [])   [non-vacuous]  +  census vs ≥96 floor
```

### Recommended Project Structure

```text
verification/
├── divergences.py                    # NEW — handler + ContextVars + probe decorator + install CM
├── test_divergences.py               # NEW — unit tests (NOTE: verification/ does NOT run in CI)
├── findings.py                       # unchanged  (append_finding target)
├── cycle_report.py                   # unchanged  (verify_cycle_closure)
└── __init__.py                       # MOD — export the public divergence names via the barrel

main_ambito_financiero.py             # MOD — strict flag, fid seed, probe decorator (smoke only)
main_higyrus.py                       # MOD — strict flag, fid seed, decorator, remove D-07 catches
main_iol.py                           # MOD — strict flag, decorator (fid seed already present)
main_matriz.py                        # MOD — strict flag, fid seed, decorator
main_market_data.py                   # MOD — strict flag, _ENDPOINT_TEMPLATES (D-03), decorator

packages/<pkg>/src/<pkg>/{client,aio,models,_core}.py   # MOD — per confirmed fix, mirrored
packages/<pkg>/tests/test_<fix>.py                      # NEW — one mocked regression per fix

.planning/phases/33-.../33-CENSUS.md   # NEW artifact — live census vs the ≥96 floor + re-scope
.planning/phases/33-.../33-LITERALS.md # NEW artifact — Literal census + DT-07 closure evidence
```

### Pattern 1: The divergence handler (Lock 10, hardened)

**What:** A `logging.Handler` subclass that translates the frozen 6-key record into an
`append_finding` call, augmented with the endpoint/surface `ContextVar`s.
**When to use:** Installed once per driver run, around the whole probe sweep.

The three hardening requirements are not optional — each closes a verified silent-loss channel:

```python
# verification/divergences.py  (sketch — planner owns the final shape)
from __future__ import annotations

import contextvars
import logging
from collections.abc import Callable, Iterator

_ENDPOINT: contextvars.ContextVar[str] = contextvars.ContextVar("gsd_probe_endpoint", default="-")
_SURFACE: contextvars.ContextVar[str] = contextvars.ContextVar("gsd_probe_surface", default="-")

# Logger name -> findings-file package slug. `_PKG_SLUG_RE` in findings.py rejects
# anything else, and a ValueError there is swallowed by _emit's suppress (P-2).
_SLUG_BY_LOGGER = {
    "ambito_financiero_client": "ambito-financiero-client",
    "higyrus_client": "higyrus-client",
    "iol_client": "iol-client",
    "matriz_client": "matriz-client",
    "market_data_client": "market-data-client",
}


class DivergenceHandler(logging.Handler):
    """6-key decode record -> SHAPE finding. MUST NOT raise (see P-2)."""

    def __init__(self, next_fid: Callable[[str], str]) -> None:
        super().__init__(level=logging.INFO)      # accept the INFO `extra` kind too
        self._next_fid = next_fid
        self.seen: set[tuple[str, str, str, str]] = set()   # (slug, model, field_path, kind)
        self.errors: list[str] = []                          # self-reported handler failures

    def emit(self, record: logging.LogRecord) -> None:
        try:
            slug = _SLUG_BY_LOGGER.get(getattr(record, "package", ""))
            kind = getattr(record, "divergence", None)
            if slug is None or kind is None:
                return                       # not our record; the package logs nothing else today
            model = record.model            # type: ignore[attr-defined]
            path = record.field_path        # type: ignore[attr-defined]
            declared = record.declared_type  # type: ignore[attr-defined]
            observed = record.observed_type  # type: ignore[attr-defined]
            surface = _SURFACE.get()
            endpoint = _ENDPOINT.get()

            triple = (slug, model, path, kind)
            first_time = triple not in self.seen
            self.seen.add(triple)            # census unit == the sizing floor's unit

            append_finding(
                slug,
                fid=self._next_fid(slug),
                class_="SHAPE",
                surface=surface,
                status="OPEN",
                # Deterministic + identity-bearing: this string IS the cross-run dedupe key.
                title=f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]",
                expected=f"model declares {declared}",
                actual=f"wire sent {observed}",
                diff=f"{declared} -> {observed} at {model}{path} via {endpoint}",
                idempotent_by_title=True,
            )
            _ = first_time
        except Exception as exc:             # noqa: BLE001 — see P-2; NEVER propagate
            self.errors.append(f"{type(exc).__name__}: {exc}")
```

**Anti-requirement:** do **not** call `self.handleError(record)` and stop there — that writes to
stderr and is easy to miss in a 3000-line driver transcript. Keep the `errors` list and print its
length in the SUMMARY, so a handler failure is a visible number, not a scrollback artifact.

### Pattern 2: The install context manager (closes P-1)

```python
@contextlib.contextmanager
def divergence_capture(
    logger_names: Sequence[str], *, next_fid: Callable[[str], str]
) -> Iterator[DivergenceHandler]:
    """Attach the handler and RAISE THE LOGGER LEVEL. Restores both on exit.

    `logging.getLogger("<pkg>")` is NOTSET today, so its effective level is root's
    WARNING and every INFO-level `extra` record is discarded before any handler runs.
    Verified by execution: getEffectiveLevel() == WARNING, isEnabledFor(INFO) is False.
    Never touches logging.root (test_logging_root_unchanged.py + the CI lint-logging grep).
    """
    handler = DivergenceHandler(next_fid)
    restore: list[tuple[logging.Logger, int]] = []
    for name in logger_names:
        lg = logging.getLogger(name)
        restore.append((lg, lg.level))
        lg.setLevel(logging.INFO)      # INFO, not DEBUG — the packages log nothing at INFO
        lg.addHandler(handler)
    try:
        yield handler
    finally:
        for lg, level in restore:
            lg.removeHandler(handler)
            lg.setLevel(level)
```

`INFO` (not `DEBUG`) is the right level: a grep across all five packages found **no** `_LOGGER.info`
or `_LOGGER.debug` call sites, so `INFO` admits the divergence stream and nothing else. `DEBUG` would
additionally admit `_transport.py`'s structured request records (`method`/`url`/`status_code`), which
are redaction-sensitive and would bury the signal.

### Pattern 3: The probe-context decorator (resolves D-02 + D-05 in one edit)

**What:** One decorator applied once per probe, binding the two ContextVars and extending the
driver's existing exception ladder with its `<Pkg>DecodeError`.
**When to use:** Every `probe_*` function in all five drivers.

```python
# in each main_*.py — the decode-error class differs per package, the shape does not.
def probe(endpoint: str, surface: str) -> Callable[[F], F]:
    def deco(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            ep, sf = _ENDPOINT.set(endpoint), _SURFACE.set(surface)
            try:
                return fn(*a, **kw)
            except HigyrusDecodeError as exc:      # strict-mode disposition
                return _shape_finding(fn.__name__, surface, exc)
            finally:
                _ENDPOINT.reset(ep)
                _SURFACE.reset(sf)
        return wrapper
    return deco
```

Two properties that make this safe, both verified:

- **The handler reads the ContextVar at emit time and sees the caller's binding.** `logging` dispatches
  handlers synchronously in the emitting frame's context. Executed check:
  `set("/api/health") -> logger.info(...) -> handler observed "/api/health"`; after `reset`, the
  handler observed `None`.
- **Async probes are awaited sequentially inside a single `asyncio.run`** in all five drivers (no
  `asyncio.gather`, no `TaskGroup` over probes), so `set`/`reset` inside one coroutine is correct and
  contexts do not interleave.

`async def` probes need an `async` twin of the wrapper (same body, `await fn(...)`) — that is the
established sync/async mirroring cost in this repo (C-3).

### Pattern 4: Two-pass execution without breaking the single-ctor AST gate

Each driver constructs **exactly one** `Client` and one `AsyncClient`; `verification/test_main_*_uses_single_client_instance.py`
asserts `1 <= ctor_calls <= 2` by AST. Passing the mode as a constructor kwarg keeps the gate green:

```python
_STRICT = os.getenv("MARKET_LIBS_STRICT_DECODE") == "1"     # module constant
...
client = Client(strict_decode=_STRICT)                       # still ONE ctor site
```

Runner:

```bash
# pass 1 — observable, full census, mutations as configured
uv run --package higyrus-client python main_higyrus.py
# pass 2 — strict, proves the raise fires; mutations deliberately OFF
MARKET_LIBS_STRICT_DECODE=1 uv run --package higyrus-client python main_higyrus.py
```

For `main_market_data.py`, pass 2 **must** run without `MARKET_DATA_VERIFY_MUTATING=1`: its
destructive symbol/holiday cycle would otherwise fire twice against `develop` in one session, and the
driver's own comment records that an active test symbol can surface as `last_error` in `/health/feed`
and skew a health baseline.

`Client.with_options()` is **not** an alternative carrier — it accepts only `max_retries` and shares
`_state` with the parent, so it cannot express a per-call decode mode.

### Pattern 5: The Literal census (criterion 3) — separate mechanism, per D-08

The walker structurally cannot supply it. Read the shipped `Literal` branch:

```python
# packages/*/src/*/_decode.py:521-534  (identical in all five copies)
if origin is Literal:
    member_types = {type(arg) for arg in args}
    member_ok = value in args if policy.literal_enforced else True   # POLICY is False, always
    if member_ok and (not args or type(value) in member_types):
        return value                       # <-- out-of-set `str` returns HERE. No sink call.
    sink(model, path, _kind_of(value), _name_of(hint), type(value).__name__)
```

With `literal_enforced=False` in all five `POLICY` constants, an out-of-set value of the correct
runtime type takes the `return value` branch and **emits nothing**. `29-DLOCK-RESPONSE-LITERAL.md`
lines 140-142 assert the opposite ("the observable divergence stream is the census-gathering
mechanism"); that assertion is falsified by the shipped code. CONTEXT D-08 already caught this — this
research confirms it at the source line.

The census therefore reads **raw wire values**, from the two sources the drivers already produce:

| Target | Evidence source | Risk | Notes |
|--------|-----------------|------|-------|
| matriz `marketId` (×2), `cficode` (×2), `currency`, `orderTypes`, `ordType` — 7 RESPONSE fields, 4 aliases | Raw wire of `get_all_instruments`, `get_instruments_details`, `get_instrument_detail`, `get_active_orders`/`get_all_orders`/`get_order_status`, `get_segments` | zero (reads only) | `models.py:262,283,291,303,315,316,352`. D-09: **record the values, never widen or close the alias.** |
| iol `mercado` / `plazo` (DT-07, INPUT params) | **`Titulo.mercado: str` and `Titulo.plazo: str`** from `get_instruments_by_type` → `/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos` | **zero** — read-only, already in `_capture_raw_wire`'s 4 endpoints | `models.py:187,228,231`; parser `_core.parse_get_instruments_by_type_response:413`. Returns *every* instrument of a type across the venue, so the value set is genuinely observed, not echoed back. |
| iol `mercado` / `plazo` — echo-only (weak) | `Cotizacion.plazo: str \| None` (`models.py:151`) from `get_quote` | zero | Echoes what we sent (`"bcba"`/`"t2"`). **Not evidence** — record it as such so a later reader does not mistake it for a census. |

**Why this does not overturn D-10.** The set a vendor *emits* in responses is not provably the set it
*accepts* as an input parameter — case variants, aliases and deprecated-but-accepted values are all
possible and none is observable without the deliberate-4xx sweep D-10 rejects. The recommendation
therefore stands with D-10's conclusion (`str`, permanent, documented) while upgrading its basis:
write the observed value set into `33-LITERALS.md`, state that it is RESPONSE-side, state why it is
insufficient to close an INPUT `Literal`, and cite that as the evidence. "Closed with evidence that
the evidence is insufficient" is a far stronger artifact than "closed for absence of evidence", and
it costs one script run.

The census script may be **uncommitted** (Claude's Discretion, matching `29-SIZING.md`'s throwaway
`sizing.py`) as long as the report is committed and the method is reproducible from the report.

### Pattern 6: Census counting that is actually comparable to the ≥96 floor

`29-SIZING.md` counted **unique `(model, field_path, kind)` triples**, one dedupe scope per corpus
file. The live run must count the same unit or criterion 5 compares two different things:

- The walker's `DecodeScope` dedupe is **per HTTP response** (Lock 5/6). The same `Movimiento.fecha`
  `missing` divergence seen across 8 endpoints emits 8 records.
- `idempotent_by_title=True` collapses those to **one finding**, but only if the title is identical —
  and the recommended title embeds `[{surface}]`, so sync and async produce two findings for one
  triple.
- Therefore: **count the census from `DivergenceHandler.seen`** (distinct `(slug, model, field_path,
  kind)`), not from the finding count and not from `FINDING=N`.

Report both numbers in `33-CENSUS.md` and label them:

| Package | Floor (29-SIZING) | Live distinct triples | Live SHAPE findings written | Verdict |
|---------|------------------:|----------------------:|----------------------------:|---------|
| higyrus-client | ≥ 22 | … | … | within / exceeds → re-scope |
| matriz-client | ≥ 24 | … | … | … |
| market-data-client | ≥ 50 | … | … | … |
| iol-client | N/A (was un-modelled at sizing time; **now typed** — first measurable census) | … | … | first-ever number, no floor to contrast |
| ambito-financiero-client | N/A (zero model classes — D-12) | expect 0 | expect 0 | smoke only |

**iol is the one package whose floor does not exist.** `29-SIZING.md` reported it `N/A, not zero`
because it had no `models.py`; Phase 30 (TYP-01) then gave it one. Phase 33 produces iol's *first*
census number, and there is no ratified budget to contrast it against. The re-scope rule in
`29-SIZING.md` ("exceeding the floor requires explicit re-scope with every deferred finding routed to
a named destination phase") cannot mechanically apply to iol. State that explicitly rather than
inventing a floor.

### Anti-Patterns to Avoid

- **Editing any `_decode.py` copy.** `tools/check_decode_intactness.py` normalizes the five copies to
  a single hash and asserts it equals a pinned `CANONICAL_DIGEST`. Any edit — even applied uniformly
  to all five — fails the `lint` CI job until the digest is re-pinned, and re-pinning is a
  deliberate, reviewable act that this phase has no mandate for.
- **Adding `except Exception` to `main_matriz.py` or `main_higyrus.py`.** AST-gated (CONTEXT D-06).
- **Keeping the hand-rolled `HigyrusDecodeError` catch in `probe_get_health_sync`/`_async`.** It mints
  its own fid and its own title, so it produces a second finding for a divergence the handler already
  wrote. Delete it (D-07) — do not "keep it for belt and braces".
- **Reporting "criterion 4 PASS" from a run whose findings are all `OPEN`.** `verify_cycle_closure`
  filters to `CONFIRMED`/`FIXED` only; it returns `(True, [])` today for all five packages, and for
  ambito and higyrus that PASS is **vacuous** (their findings are `EXPECTED`/`NO-FIX`, which the
  filter skips). Criterion 4 is only meaningful after triage promotes real Phase 33 divergences.
- **Writing regression tests under `verification/`.** That directory has never executed in CI (see
  P-9). A `Regression:` link pointing there resolves structurally in `verify_cycle_closure` — the
  check is regex-over-text, not collection — but the test would never actually run on a PR.
- **Deriving the census from `FINDING=N` in the driver SUMMARY.** That counter increments on every
  `_next_fid()` call, including ones `append_finding` silently discards (P-3).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Divergence dedupe within one response | A per-probe `set` of seen fields | `_decode.DecodeScope` (already runs) | Lock 5/6 already collapse `(model, field_path, kind)` per response, and the collapse is what makes the list-element case tractable. A second layer would double-count. |
| Cross-run finding dedupe | Reading the findings markdown and diffing | `append_finding(idempotent_by_title=True)` | Built for this exact case (HARN-08/10); handles the operator-prose round-trip (`extra_bullets`, D-23) that a hand-rolled writer would destroy. |
| Preserving operator triage prose | Re-serializing the findings file | `append_finding` preservation path (`_replace_art_block`) | CR-01: any non-`OPEN` status short-circuits to an in-place ART refresh precisely to avoid the lossy round-trip. |
| Fid allocation | A per-driver counter starting at 0 | `max_existing_fid(pkg)` + one shared allocator | Three drivers hand-roll it today and all three are broken against their own committed findings files (P-3). |
| Regression-link validation | A bespoke "does this test exist" check | `verification.cycle_report.verify_cycle_closure` | Already handles path-traversal defence, repo-root confinement, `OSError` on read, and `async def` matching. |
| Type-name vocabulary in records | A `type_of()` helper | `type(x).__name__` via `_name_of` | Lock 1 D-06 explicitly forbids introducing a helper — the record's type strings must stay byte-identical to `schema_of`'s so the floor and the census are directly contrastable. |
| Redacting exception text into findings | Inline f-strings at each site | `main_iol.py::_redacted_exc` (that driver) / the 6-key type-not-value contract (everywhere) | AD-30-09-01: 32 inline sites are 32 independent decisions that drift; that is how the original leak gap was born. |
| Secret loading | Reading `.env` by hand | `load_dotenv()` as already called at package import | Works today for all four credentialed packages — but see P-13 for the `python -c` trap. |

**Key insight:** every "helper" this phase might be tempted to write already exists, hardened by a
named review finding, in `verification/`. The genuinely new code is **one handler, two ContextVars
and one decorator** — under ~150 lines. If a plan proposes materially more new machinery than that,
it is rebuilding something that shipped in Phases 11/29.

---

## Durable & Runtime State Inventory

> This phase is not a rename, but it **writes to durable and live state** outside the source tree.
> The same discipline applies: after every source edit lands, what state still carries a stale value?

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Committed findings files | `.planning/verification/{ambito-financiero,higyrus,iol,matriz,market-data}-client-findings.md` — 1 / 2 / 2 / 10 / 66 existing findings, statuses `EXPECTED`(20) `NO-FIX`(8) `FIXED`(51) `OPEN`(1). matriz `F-03…F-08` are already the S-4 `extra` findings the handler will re-discover under different titles. | Seed fid allocators (P-3). Decide up front whether the handler's title convention should intentionally match matriz's existing `.instrument_detail.<key>: wire emite, model ignora (info)` titles to absorb them, or whether duplicate-by-different-title is accepted and triaged. **This is a plan-time decision, not a runtime accident.** |
| Committed schema snapshots | `.planning/verification/schemas/` — 43 files. matriz declares **17** `_SCHEMA_FILES` entries but only **8** exist on disk; iol 4/4; higyrus 5/5; market-data 25. | The 9 missing matriz files (orders/positions/account-report) take the **write-once** branch on a successful live run and will appear as new committed artifacts. That is criterion-4 "reconciliation" — expect new files, not just diffs. `_write_or_check_schema` calls `_next_fid()` on drift, so it shares the P-3 hazard. |
| Live vendor state (mutations) | `main_market_data.py` destructive symbol + holiday cycle against `develop`, gated by `MARKET_DATA_VERIFY_MUTATING=1` **and** hostname match. matriz driver is **read-only** (no order-entry probes — verified: all 46 probes are `get_*` / `error_*` / snapshot). higyrus, iol, ambito read-only. | Pass 2 (strict) must run with the mutation gate OFF so the destructive cycle fires once per session, not twice. |
| Credentials / env | `.env` present with all required keys in higyrus (8 keys), iol (3), matriz (8), market-data (4). Absent in ambito (by design — no auth) and wallets (out of scope). | Pre-flight must prove **authentication**, not just presence (D-13). See Environment Availability. |
| Gitignored capture staging | `.planning/verification/captures/` — **empty today**, gitignored (`.gitignore:51`). | This is the correct home for the Literal-census raw payloads. Raw wire must land here and nowhere else (C-4). |
| Build artifacts / installed packages | `.venv` is healthy (`python3.12 -> uv-managed cpython-3.12`); `uv.lock` unchanged (no new deps). | None — no reinstall needed. |
| CI-pinned digests | `tools/check_decode_intactness.py::CANONICAL_DIGEST` pins the 5 `_decode.py` copies. | **None expected** — if a plan proposes touching `_decode.py`, the digest re-pin becomes a required, reviewable task. |

---

## Common Pitfalls

### P-1 — The `extra` divergence kind is dropped before any handler runs (33% of the floor)

**What goes wrong:** The live census reports ~2/3 of the expected divergences and looks like good news.
**Why it happens:** `_logging.attach()` adds a `NullHandler` to `logging.getLogger("<pkg>")` but never
sets a level. The logger is `NOTSET`, so its effective level is inherited from root = `WARNING`. Lock 3
emits `extra`-kind divergences at `INFO`. Nothing in the five drivers calls `setLevel` — grep across
`packages/*/src/*/*.py`, `main_*.py` and `verification/*.py` found `setLevel` only inside docstrings.
**Evidence (executed):**

```
level: 0  effective: WARNING
isEnabledFor(INFO):    False
isEnabledFor(WARNING): True
```

`29-SIZING.md` hit the same trap during the offline run and worked around it explicitly ("level `DEBUG`
so `INFO`-level `extra` records are not dropped"). **`extra` is 32 of the 96 floor records — 33%, and
it is 18 of matriz's 24 and 14 of market-data's 50.**
**How to avoid:** `logging.getLogger(name).setLevel(logging.INFO)` inside the install context manager,
restored on exit. Never touch root.
**Warning signs:** a live census with `extra == 0` for matriz or market-data. Both floors are
`extra`-dominant; a zero there is the tell.

### P-2 — Any exception inside the handler is silently swallowed by the walker

**What goes wrong:** `append_finding` raises (invalid slug, `ValueError` on a bad `class_`/`status`,
a `title` containing `\n` — it validates all three; or an `OSError` on the findings file), the record
is lost, and **nothing anywhere reports it**. The driver's SUMMARY is unaffected.
**Why it happens:** `_decode._emit` is `with contextlib.suppress(Exception): _LOGGER.warning(...)`
(Lock 9 — a deliberate guarantee that the decoder never crashes on divergences it merely reports). A
custom `Handler.emit` that raises propagates through `callHandlers` → `Logger.handle` → `_log` → into
that `suppress`.
**Evidence (executed):** a handler raising `RuntimeError` inside `emit` produced **zero output** and
zero exception under the `suppress`.
**How to avoid:** the handler wraps its own body in `try/except Exception` and appends to a
`self.errors` list; the driver prints `len(handler.errors)` in the SUMMARY and a non-zero value fails
the run. Do **not** rely on `handleError` alone — it writes to stderr and is invisible in a long
transcript.
**Warning signs:** finding counts that do not match `len(handler.seen)`.

### P-3 — Three drivers never seed the fid allocator; their first N findings are silently discarded

**What goes wrong:** `main_higyrus.py`, `main_matriz.py` and `main_ambito_financiero.py` start
`_fid_counter = 0` and emit `F-01, F-02, …`. Their committed findings files already hold:

| Driver | Existing fids | Statuses | Consequence of a colliding re-emit |
|--------|---------------|----------|------------------------------------|
| `main_matriz.py` | `F-01 … F-10` | 7 `NO-FIX`, 2 `EXPECTED`, 1 `FIXED` — **all non-OPEN** | **The first 10 findings of every matriz run are a silent no-op** while `main()` still counts them in `FINDING=N`. |
| `main_higyrus.py` | `F-01`, `F-02` | `EXPECTED`, `NO-FIX` | Same — first 2 findings silently lost. |
| `main_ambito_financiero.py` | `F-01` | `EXPECTED` | First finding silently lost (low impact — D-12 expects zero). |

**Why it happens:** `append_finding`'s CR-01 preservation path short-circuits on any non-`OPEN` status
without writing. `main_iol.py` and `main_market_data.py` already carry the fix (`_seed_fid_counter()`
via `max_existing_fid`, D-16/D-24) and `max_existing_fid`'s own docstring describes this exact failure
mode. The other three never inherited it.
**How to avoid:** add `_seed_fid_counter()` to the three unseeded drivers (copy `main_iol.py:190-213`
verbatim), and give the handler and the driver a **single shared allocator** — pass the driver's
`_next_fid` into `divergence_capture(next_fid=...)`. Two independently-seeded counters in one package
would collide with each other on the second finding.
**Warning signs:** `FINDING=N` in the SUMMARY that does not match the number of new `### F-` blocks in
the findings file. Make this a post-run assertion in the plan.

### P-4 — Strict-mode survival is *not* uniform; three drivers already survive but misclassify

**What goes wrong:** The plan sizes "add the decode error to the exception tuple" as five identical
edits and is surprised by the shape of the result in three of them.
**Why it happens:** measured `except Exception` counts per driver:

| Driver | `except Exception` | `_RESIDUAL_PROBE_EXCEPTIONS` | Strict-mode behaviour today |
|--------|-------------------:|------------------------------|-----------------------------|
| `main_higyrus.py` | **0** (AST-gated) | tuple, **no** `HigyrusDecodeError` | **Dies** on first strict divergence. |
| `main_matriz.py` | **0** (AST-gated) | tuple, **no** `PrimaryDecodeError` | **Dies** on first strict divergence. |
| `main_iol.py` | 12 | n/a | **Survives** — already has an `IOLDecodeError` branch in `_redacted_exc:326`; classification per handler. |
| `main_market_data.py` | 55 | n/a | **Survives** — but `_finding_for_exc:334` maps it to `ERROR-MAP`, and its title `f"{name}: {type(exc).__name__} inesperado"` is **unique per probe**, so `idempotent_by_title` cannot dedupe it. One spurious ERROR-MAP finding per affected probe. |
| `main_ambito_financiero.py` | 6 | n/a | **Survives** — D-12 expects zero divergences anyway. |

CONTEXT D-05 ("ningún manejo de excepciones existente en ningún driver lo captura hoy") is accurate
for higyrus and matriz only.
**How to avoid:** two distinct tasks, not one. (a) higyrus + matriz: extend the exception tuple / apply
the decorator so the driver survives. (b) iol + market-data + ambito: intercept the decode error
**before** the generic `except Exception` so it becomes a `SHAPE` finding with a deterministic title,
not an `ERROR-MAP` with a per-probe one.
**Warning signs:** a market-data run whose `ERROR-MAP` count jumps by tens.

### P-5 — A single `@probe(endpoint=…)` mislabels multi-endpoint probes

**What goes wrong:** `endpoint` in the finding's `diff` names the wrong URL, making the finding
un-triageable.
**Why it happens:** several probes touch more than one endpoint inside one `try`. Verified example:
`main_market_data.py::probe_health_sync` calls `get_health()` **and** `get_health_feed()` and writes
two snapshots (`/health`, `/health/feed`). Its async mirror does the same.
**How to avoid:** the decorator sets a *default*; provide a small re-binding helper
(`with endpoint_scope("/health/feed"): ...`) for the multi-endpoint probes, and audit which probes
need it. `_ENDPOINT_TEMPLATES` maps *client functions*, not probes — for market-data (D-03) key the
new dict by client function and have the helper look it up, which also avoids duplicating the URL
strings already inlined at the `_write_schema_snapshot` call sites.
**Warning signs:** a finding whose `field_path` belongs to a model the named endpoint never returns.

### P-6 — The `Literal` census cannot come from the divergence stream

**What goes wrong:** the plan schedules "read the SHAPE findings to build the Literal census" and it
returns empty.
**Why it happens:** `_decode.walk_field:521-534` — with `literal_enforced=False` (all five `POLICY`
constants), an out-of-set value of the correct runtime type returns **before** the sink call.
`29-DLOCK-RESPONSE-LITERAL.md:140-142` claims otherwise; the shipped code is authoritative.
**How to avoid:** Pattern 5 — a separate script over raw wire / captures.
**Warning signs:** `33-LITERALS.md` with an empty observed-values table.

### P-7 — `verify_cycle_closure` PASSes vacuously

**What goes wrong:** criterion 4 is reported green from a run in which the gate inspected nothing.
**Why it happens:** the filter is `status in ("CONFIRMED", "FIXED")`. Measured today, all five packages
return `(True, [])` — but the number of findings actually inspected is: ambito **0**, higyrus **0**,
iol **1**, matriz **1**, market-data **50**. Two of the five PASS entirely vacuously **right now**.
Additionally, a finding present only in the `## Index` (no detail block) is not returned by
`_iter_findings` at all.
**How to avoid:** report, per package, both `verify_cycle_closure(pkg)` **and** the count of
`CONFIRMED`/`FIXED` findings it inspected, and require the second number to have increased by the
number of Phase 33 fixes. CONTEXT D-11 is the rule; this is its measurement.
**Warning signs:** a criterion-4 PASS with an unchanged inspected-count.

### P-8 — Regression tests placed where CI never runs them

**What goes wrong:** a `Regression:` link resolves, `verify_cycle_closure` PASSes, and the test never
executes on a PR.
**Why it happens:** the CI `test` job runs `pytest packages/${{ matrix.package }}` — an explicit path
that overrides `testpaths`. `verification/` therefore **has never executed in CI**, a fact recorded
three times in `ci.yml`'s own comments. `verify_cycle_closure` validates the link by regex over file
text (`def <test_name>(` substring), so it cannot tell the difference.
**How to avoid:** every regression test for a Phase 33 fix goes in `packages/<pkg>/tests/`, and the
`Regression:` value uses `packages/<pkg>/tests/<file>.py::<test_name>` — the convention
`cycle_report.py`'s docstring already prescribes.
**Warning signs:** a `Regression:` path starting with `verification/`.

### P-9 — `verification/divergences.py` escapes both mypy and the pre-commit hook

**What goes wrong:** the new module ships untyped and mypy-strict violations surface later.
**Why it happens:** `[tool.mypy] files` lists only the six `packages/*/src` roots; the pre-commit mypy
hook is scoped `files: ^packages/.*/src/`. Neither reaches `verification/` or `main_*.py`.
**How to avoid:** add an explicit `uv run mypy verification` step to the plan's own verification
commands (local, not necessarily CI), and hold the module to the same `strict` bar by hand. Ruff
*does* cover it (`ruff check .`), so line-length/quote/import conventions are enforced.
**Warning signs:** `Any` leaking into the handler's `record` attribute reads without a documented
`# type: ignore[attr-defined]`.

### P-10 — `load_dotenv()` silently loads nothing under `python -c`

**What goes wrong:** a pre-flight one-liner reports credentials missing, the operator concludes the
`.env` files are broken, and the phase stalls on a phantom.
**Why it happens:** `python-dotenv.find_dotenv()` walks up from the **calling frame's file**; when
`__main__` has no `__file__` (a `-c` invocation, a REPL) it falls back to `os.getcwd()`, and there is
no `.env` at the repo root.
**Evidence (executed):** `uv run --package higyrus-client python -c "import higyrus_client; …"` →
`HIGYRUS_USER set: False`. The same imports from a real `.py` file → **all 11 variables `SET`** across
all four credentialed packages.
**How to avoid:** the pre-flight is a `.py` file, invoked as `uv run --package <pkg> python <file>.py`.
**Warning signs:** a `SKIPPED <pkg>: missing …` line for a package whose `.env` demonstrably has the key.

### P-11 — Two-pass runs double-fire market-data's destructive cycle

**What goes wrong:** the `develop` symbol/holiday cycle runs twice in one session; a lingering active
test symbol surfaces as `last_error` in `/health/feed` and skews the health baseline (the driver's own
comment at `main_market_data.py:3358-3362` documents exactly this ordering hazard).
**How to avoid:** pass 2 runs with `MARKET_DATA_VERIFY_MUTATING` unset. Pass 2's purpose is proving the
raise fires, not coverage.

### P-13 — `verification/` is RED today and takes ~14 minutes; it is not a usable phase gate as-is

**What goes wrong:** the plan adds `verification/test_divergences.py` and gates a wave on
`uv run pytest verification`, which then fails for reasons that have nothing to do with Phase 33 —
or, worse, a real Phase 33 regression hides inside a pre-existing red baseline.
**Why it happens:** the directory has **never run in CI** (P-8), so nothing has kept it green.
**Measured (executed, full run):**

```
19 failed, 362 passed, 19 errors in 828.19s (0:13:48)
```

**Root cause isolated (executed):** `verification/test_matriz_sweep_snapshot.py` alone accounts for
**17 of the 19 failures and 17 of the 19 errors** — one parametrized test over 17 matriz probes,
running in 0.05s:

```
verification/test_matriz_sweep_snapshot.py:260: in test_matriz_probe_envelope_shape_preserved
    result, _payload = probe_fn()
E   TypeError: probe_get_segments() missing 1 required positional argument: 'client'
```

The test still calls the probes with **zero arguments** — it predates the Phase 15 driver migration
(REFAC-05) that threaded a single `client` instance as a parameter into every probe. It rotted the
moment the driver changed and nobody noticed, **because `verification/` never runs in CI**. The 17
paired `ERROR`s are teardown fallout: `pytest_httpx._assert_options` asserts "mocked but not
requested" because the probe never fired. One root cause, 34 red entries.

**This is the canary for Phase 33's own refactor.** Phase 33 wraps ~130 probes in a decorator. Any
harness test that calls a probe directly is exposed to exactly this rot, and CI will not catch it.
The remaining ~2 failures / ~2 errors live elsewhere and were not isolated (Open Question 4); the
full-summary re-run was still executing when this document closed.

**How to avoid:**
- Capture the **exact failing set as a baseline** in a Wave 0 task (`pytest verification -q --tb=no -rfE`)
  and treat only *new* failures as regressions.
- Do **not** make a full `pytest verification` run a per-task gate — 14 minutes per commit is not
  viable. Gate on `pytest packages` (what CI enforces) plus a targeted
  `pytest verification/test_divergences.py verification/test_main_drivers_bare_except.py -q`.
- Decide explicitly whether repairing the 19+19 is in scope. It is **not** part of LIVE-TYP-01 and
  should be routed to a named destination phase rather than absorbed silently — the same re-scope
  discipline `29-SIZING.md` imposes on divergences. Note the cost is small and the value is high:
  `test_matriz_sweep_snapshot.py` needs one fixture change (construct a `Client` and pass it), and
  fixing it restores a 17-endpoint envelope-shape guard over the exact matriz surface Phase 33 is
  about to census.
- **Audit every harness test that calls a `probe_*` function directly** before applying the
  decorator, and re-run those tests after — that is the failure mode this baseline demonstrates.

**Warning signs:** a plan whose verification command is `uv run pytest` unqualified.

### P-12 — Market-closed captures make S-5 unresolvable

**What goes wrong:** matriz's `MarketDataSnapshot.LA/.SE/.OI/.CL` come back `null` again and the run
cannot distinguish "legitimate market-closed shape" from "modelling error", so S-5 is re-deferred.
**Why it happens:** the existing matriz corpus was captured outside a session (`29-SIZING.md` S-5:
`BI` and `OF` are empty lists).
**How to avoid:** schedule the matriz pass-1 run inside an ARG trading session and populate the ART
block's `Market hours note` (`append_finding(market_hours=...)`) for that run. If a session run is not
possible, say so and route S-5 to a named destination phase — never mark it resolved from a closed-market
capture.

---

## Code Examples

### Verifying the logger-level trap (reproduce P-1)

```python
# Source: executed against CPython in this environment
import logging
lg = logging.getLogger("higyrus_client")
lg.addHandler(logging.NullHandler())          # what _logging.attach() does today
print(lg.level, logging.getLevelName(lg.getEffectiveLevel()))  # 0 WARNING
print(lg.isEnabledFor(logging.INFO))                            # False  <-- extras dropped
```

### ContextVar visibility inside `Handler.emit` (basis for Pattern 3)

```python
# Source: executed against CPython in this environment
import contextvars, logging
var = contextvars.ContextVar("ep", default=None)
seen = []

class H(logging.Handler):
    def emit(self, record):
        seen.append((record.__dict__.get("field_path"), var.get()))

lg = logging.getLogger("demo"); lg.setLevel(logging.INFO); lg.addHandler(H())
tok = var.set("/api/health")
lg.info("decode divergence", extra={"field_path": ".x"})
var.reset(tok)
lg.info("decode divergence", extra={"field_path": ".y"})
# seen == [('.x', '/api/health'), ('.y', None)]
```

### The reserved-key trap the 6-key registry exists to dodge

```python
# Source: executed — confirms 29-AGGREGATION-CONTRACT.md Lock 1
logging.getLogger("demo").info("m", extra={"module": "boom"})
# KeyError: "Attempt to overwrite 'module' in LogRecord"
```

### Seeding the fid allocator (the fix the three drivers are missing)

```python
# Source: main_iol.py:190-220 — copy verbatim into main_higyrus / main_matriz / main_ambito_financiero
from verification.findings import append_finding, max_existing_fid

_fid_counter: int = 0

def _seed_fid_counter() -> None:
    """Raise the allocator above every fid already committed (D-16/D-24)."""
    global _fid_counter
    _fid_counter = max_existing_fid(_PKG)

def _next_fid() -> str:
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"
```

Call order inside `main()` (verified in `main_market_data.py:3319-3324`):
`require_env(...)` → `write_findings(_PKG)` → `_seed_fid_counter()` → first probe.

### The regression-test template for an in-cycle fix

```python
# Source: packages/higyrus-client/tests/test_decode.py:870+ (shape), pytest-httpx
from __future__ import annotations

from pytest_httpx import HTTPXMock

import higyrus_client


def test_movimiento_fecha_missing_is_reported_not_substituted(httpx_mock: HTTPXMock) -> None:
    """Regression for F-NN — <finding title>."""
    httpx_mock.add_response(json={"token": "t"})           # auth
    httpx_mock.add_response(json=[{"idMovimientos": None}])  # the divergent wire shape
    ...
```

Then link it from the finding so `verify_cycle_closure` resolves it:

```
- **Regression:** packages/higyrus-client/tests/test_decode.py::test_movimiento_fecha_missing_is_reported_not_substituted
```

### Reading the current cycle-closure state (baseline for criterion 4)

```bash
# Source: executed — all five currently (True, []); ambito & higyrus vacuously so
uv run python -c "
import sys; sys.path.insert(0,'.')
from verification.cycle_report import verify_cycle_closure
for p in ['ambito-financiero-client','higyrus-client','iol-client','matriz-client','market-data-client']:
    print(p, verify_cycle_closure(p))"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact on this phase |
|--------------|------------------|--------------|----------------------|
| `SafeModel._coerce` silently substitutes typed zeros | `_decode.walk_field` / `walk_model` report every substitution on the package logger, and raise under `STRICT_DECODE` | Phase 29 (DEC-01) | The entire premise of Phase 33. `[VERIFIED: _decode.py]` |
| `iol-client` returns `dict[str, Any]` — no models, `N/A` at sizing time | `iol_client.models` ships `Punta`, `Cotizacion`, `Instrumento`, `Titulo` | Phase 30 (TYP-01) | **iol has no ratified floor.** Phase 33 produces its first census number; the ≥96 total does not include it. |
| `higyrus.get_health` / market-data health+calendar-write return bare dicts | Typed via TYP-02 models | Phase 31 | Adds decode sites (and divergences) that post-date the ≥96 floor — expect the live number to exceed it for reasons unrelated to defect discovery. |
| `matriz-client` has **no** `aio.py` (async only via `ws_client` or a thread executor) | matriz **has** an async surface — `main_matriz.py:2101` constructs `AsyncClient()` and 20+ `probe_*_async` functions exist | ≤ Phase 32 | **`CLAUDE.md`'s ARCHITECTURE section is stale on this point.** C-3 (mirror sync/async) applies to matriz fixes too. |
| `verification/` intended to run in CI | It never has — cross-package gates were relocated to `tools/*.py` steps in the `lint` job | Phases 29/31/32 | Regression tests must live under `packages/**/tests/` (P-8). |
| market-data live verification depends on an operator-paste token workaround (Phase 23) | `.env` with the four Auth0 variables is present and loads | ≤ Phase 32 | Confirms CONTEXT D-13. The Phase 23 fallback remains the documented escape hatch if the creds are expired. |

**Deprecated / superseded:**

- `29-DLOCK-RESPONSE-LITERAL.md:140-142` ("the observable divergence stream is the census-gathering
  mechanism") — **superseded by the shipped walker**; the `Literal` branch emits nothing for an
  out-of-set value of correct runtime type. Use Pattern 5 instead. CONTEXT D-08 already reflects this.
- The hand-rolled `HigyrusDecodeError` catch in `probe_get_health_sync`/`_async` — superseded by the
  shared mechanism (CONTEXT D-07); delete, do not replicate.
- `29-SIZING.md`'s ROADMAP-criterion-5 corpus (`verification/snapshots/`) — those are four
  public-surface `.txt` files with no payloads; the real corpus is `.planning/verification/schemas/`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `.env` credentials, though present and loadable, actually authenticate against the live vendors today. | Environment Availability, D-13 | The whole census SKIPs. **This is exactly why the plan needs a pre-flight task before any counting task** — do not assume. Fallback: Phase 23's operator-paste path per package. |
| A2 | `develop` (market-data) is reachable from the run environment (VPN / IP allowlist). | Environment Availability | Every market-data probe degrades to `NO-DATA`/`SKIPPED`; the ≥50 floor cannot be contrasted. The driver already classifies `httpx.ConnectError`/`ConnectTimeout` as `NO-DATA` rather than crashing, so the failure is graceful but the criterion is unmet. |
| A3 | The matriz run can be scheduled inside an ARG trading session to resolve S-5. | P-12 | S-5 (`MarketDataSnapshot.LA/.SE/.OI/.CL`) stays undecidable and must be routed to a named destination phase rather than closed. |
| A4 | The live census will **exceed** the ≥96 floor (the blind-spot argument in `29-SIZING.md` points only upward) and will therefore trigger the explicit re-scope path. | Pattern 6 | If it comes in *under* the floor, that is a signal the census is losing records (P-1/P-2/P-3), **not** that the packages are clean. Plan a task that investigates an under-floor result rather than accepting it. |
| A5 | The handler's title convention (`{model}{field_path}: {kind} (declared=…, observed=…) [{surface}]`) is the right dedupe identity. | Pattern 1 | Titles are the cross-run dedupe key and are effectively permanent once written. Including `[{surface}]` doubles the finding count relative to the triple count; excluding it loses criterion 1's surface requirement in the title (though `surface` remains its own column). **Recommend confirming with the operator before the first live write** — a wrong choice is expensive to unwind across 96+ findings. |
| A6 | Absorbing matriz's existing `F-03…F-08` (`NO-FIX`, S-4 `extra` keys) into the handler's output via a matching title is preferable to writing six near-duplicate findings. | Durable State Inventory | Either choice is defensible; the risk is making it *accidentally* at runtime instead of deliberately at plan time. |
| A7 | `MARKET_LIBS_STRICT_DECODE` (or equivalent) is an acceptable new env-var name for the two-pass flag. | Pattern 4 | Naming only; low risk. Note it must not collide with the existing `VERIFY_HIGYRUS_BAD_CREDS` / `MARKET_DATA_VERIFY_MUTATING` conventions. |
| A8 | *(Retired — measured, see P-13.)* The `verification/` suite is **not** green: `19 failed, 362 passed, 19 errors in 828s`. This is a pre-existing red baseline, not an assumption. | P-13 | — |

---

## Open Questions

1. **Does `.planning/verification/matriz-client-findings.md` `F-03…F-08` get absorbed or duplicated?**
   - What we know: those six findings are hand-written `NO-FIX` records of exactly the S-4 `extra` keys
     the handler will re-emit; their titles (`.instrument_detail.securityIdSource: wire emite, model
     ignora (info)`) do not match any deterministic handler-generated title.
   - What's unclear: whether the operator wants six new `OPEN` SHAPE findings alongside six existing
     `NO-FIX` ones.
   - Recommendation: surface as a plan-time decision task with a default of "write the new ones and
     triage them to `NO-FIX` referencing the originals" — mechanical, auditable, no title gymnastics.

2. **What is iol's census budget, given `29-SIZING.md` reports it `N/A, not zero`?**
   - What we know: iol had no `models.py` at sizing time; Phase 30 gave it four models. The re-scope
     rule is written against per-package floors that iol does not have.
   - What's unclear: whether criterion 5 requires a floor for iol at all.
   - Recommendation: report iol's number as a **first measurement with no prior budget**, explicitly
     excluded from the `≥96` contrast. Do not back-fill a floor — that would be an estimate, and
     `29-SIZING.md` is emphatic that these are floors, never estimates.

3. **Do Phase 31's new decode sites (higyrus `Health`, market-data `Health`/`HealthFeed`/calendar-write)
   inflate the live number above the floor for non-defect reasons?**
   - What we know: those endpoints were `N/A — unmodelled dict` rows in the sizing corpus and are typed
     now.
   - Recommendation: tag TYP-02-origin divergences separately in `33-CENSUS.md` so the re-scope
     conversation distinguishes "newly visible because newly typed" from "newly discovered defect".

4. **What are the remaining ~2 failures and ~2 errors in `verification/`, and is repairing them in scope?**
   - What we know: the full run is `19 failed, 362 passed, 19 errors in 828s`. **17 failures + 17
     errors are isolated to one file** — `test_matriz_sweep_snapshot.py`, a single parametrized test
     calling `probe_*()` with no `client` argument, stale since the Phase 15 driver migration. The
     remaining ~2+~2 were not enumerated (the full-summary re-run had not finished when this document
     closed).
   - What's unclear: whether the residual few mask a real defect in the strict-decode path.
   - Recommendation: Wave 0 task — capture the baseline with `pytest verification -q --tb=no -rfE`,
     commit the list as a phase artifact, and route repairs to a **named** destination phase.
     LIVE-TYP-01 does not include "make `verification/` green"; pretending otherwise is scope creep,
     and ignoring it silently is the false-clean failure mode this milestone exists to remove.

5. **Should `verification/divergences.py` be enrolled in `[tool.mypy] files`?**
   - What we know: it is currently outside both mypy scopes (P-9).
   - Recommendation: out of scope for LIVE-TYP-01 (enrollment-list reconciliation was GATE-TYP-01/D-16's
     job and is closed). Run `uv run mypy verification` as a local plan verification step and note the
     gap as a carry-forward.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | every driver invocation | ✓ | 0.11.3 | — |
| CPython 3.12 (`.venv`) | workspace | ✓ | 3.12.11 (`.venv/bin/python` → uv-managed) | 3.13 also supported |
| `pytest` | regression tests | ✓ | 9.0.3 | — |
| `httpx` | transport | ✓ | 0.28.1 | — |
| `pytest-httpx` | mocked regressions | ✓ | installed (dev dep) | — |
| `higyrus-client` creds (`HIGYRUS_USER/PASSWORD/BASE_URL/CLIENT_ID`) | criterion 1 | ✓ present & loading | — | Phase 23 operator-paste path |
| `iol-client` creds (`IOL_USER/PASSWORD/BASE_URL`) | criterion 1 | ✓ present & loading | — | idem |
| `matriz-client` creds (`PRIMARY_USER/PASSWORD/BASE_URL/ACCOUNT` + 4 sample vars) | criterion 1 | ✓ present & loading | — | idem |
| `market-data-client` creds (4 Auth0 vars) | criterion 1 | ✓ present & loading | — | idem |
| `ambito-financiero-client` creds | criterion 1 | n/a by design (no auth) | — | — |
| Live vendor endpoints (IOL, Higyrus, MATBA ROFEX) | criterion 1 | **unverified** | — | None — a SKIP means the criterion is unmet for that package |
| market-data `develop` host (VPN / allowlist) | criterion 1 | **unverified** | — | Driver degrades to `NO-DATA`, not a crash |
| ARG trading session window | S-5 resolution (P-12) | **schedule-dependent** | — | Route S-5 to a named destination phase |

**Missing dependencies with no fallback:** none at the tooling level.
**Unverifiable from this environment:** credential *validity* and vendor *reachability*. Both are
runtime facts, not install facts.

**Pre-flight recipe (satisfies CONTEXT D-13; note P-10 — must be a real `.py` file):**

```python
# scripts/preflight_33.py  (may be uncommitted)
from __future__ import annotations
import sys
sys.path.insert(0, ".")
import higyrus_client, iol_client, matriz_client, market_data_client

for name, login in [
    ("higyrus-client", lambda: higyrus_client.Client().login()),
    ("iol-client", lambda: iol_client.Client().login()),
    ("matriz-client", lambda: matriz_client.Client().login()),
    ("market-data-client", lambda: market_data_client.Client().login()),
]:
    try:
        login()
        print(f"{name}: AUTH OK")
    except Exception as exc:                # noqa: BLE001 — pre-flight only, never a driver
        print(f"{name}: AUTH FAIL {type(exc).__name__}")   # never print the exception body
```

Run: `uv run python scripts/preflight_33.py`. **No census number counts as valid until every
in-scope package prints `AUTH OK`.** Never print exception bodies — vendor error bodies plausibly
carry account identifiers (`main_iol.py::_redacted_exc` documents this).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio (`asyncio_mode = "auto"`) + pytest-httpx |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `pythonpath = ["."]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run pytest packages/<pkg> -q` |
| Full suite command | `uv run pytest packages -q` (this is what CI runs, per-package × py3.12/3.13) |
| **CI reality** | The CI `test` job runs `pytest packages/${{ matrix.package }}` — an explicit path that **overrides `testpaths`**. `verification/` and `tests/` have never executed in CI. |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-TYP-01 (c1) | Handler maps a 6-key record to a `SHAPE` finding with the right slug/surface | unit | `uv run pytest verification/test_divergences.py -q` | ❌ Wave 0 |
| LIVE-TYP-01 (c1) | Handler raises **nothing** out of `emit`, and records the failure in `errors` | unit | same file, `::test_emit_never_raises` | ❌ Wave 0 |
| LIVE-TYP-01 (c1) | Install CM raises each package logger to `INFO` and restores on exit; `logging.root` untouched | unit | same file, `::test_install_sets_level_and_restores` | ❌ Wave 0 |
| LIVE-TYP-01 (c1) | `INFO`-kind (`extra`) records reach the handler | unit | same file, `::test_extra_kind_is_captured` | ❌ Wave 0 |
| LIVE-TYP-01 (c1) | Endpoint/surface ContextVars are visible inside `emit` and reset after the probe | unit | same file, `::test_probe_context_binding` | ❌ Wave 0 |
| LIVE-TYP-01 (c1) | Live strict run per package, both surfaces | **manual — live API** | `MARKET_LIBS_STRICT_DECODE=1 uv run --package <pkg> python main_<x>.py` | n/a (operator/agent-run) |
| LIVE-TYP-01 (c2) | One mocked regression per confirmed fix, mirrored sync+async | unit | `uv run pytest packages/<pkg>/tests/test_<fix>.py -q` | ❌ per fix |
| LIVE-TYP-01 (c2) | No sync/async drift introduced by a fix | unit | `uv run pytest packages/<pkg>/tests/test_surface_parity.py -q` | ✅ exists |
| LIVE-TYP-01 (c3) | `Literal` census produced and DT-07 closure documented | **manual — artifact review** | `33-LITERALS.md` present with a populated observed-values table | ❌ Wave 0 artifact |
| LIVE-TYP-01 (c3) | matriz's 4 `Literal` aliases still decode without enforcement (D-09 not violated) | unit | `uv run pytest packages/matriz-client/tests/test_decode.py packages/matriz-client/tests/test_types.py -q` | ✅ exists |
| LIVE-TYP-01 (c4) | `verify_cycle_closure` PASS **non-vacuously** per package | unit | new `verification/test_cycle_closure_phase33.py` asserting `(True, [])` **and** inspected-count ≥ N | ❌ Wave 0 |
| LIVE-TYP-01 (c4) | Schema snapshots reconciled (no unexplained drift findings) | manual — artifact review | diff of `.planning/verification/schemas/` after the run | n/a |
| LIVE-TYP-01 (c5) | Live census contrasted with the ≥96 floor; excess re-scoped to named phases | **manual — artifact review** | `33-CENSUS.md` present with the per-package table and a named destination for every deferred finding | ❌ Wave 0 artifact |
| CI non-regression | Bare-except AST gate still green for matriz + higyrus | unit | `uv run pytest verification/test_main_drivers_bare_except.py -q` | ✅ exists |
| CI non-regression | Single-Client AST gate still green ×5 | unit | `uv run pytest verification/ -q -k uses_single_client_instance` | ✅ exists |
| CI non-regression | `_decode.py` intactness digest unchanged | script | `uv run python tools/check_decode_intactness.py` | ✅ exists |
| CI non-regression | Surface types + uniform structure gates | script | `uv run python tools/check_surface_types.py && uv run python tools/check_uniform_structure.py` | ✅ exists |

### Sampling Rate

- **Per task commit:** `uv run ruff check . && uv run ruff format --check . && uv run pytest packages/<pkg> -q`
- **Per wave merge:** `uv run pytest packages -q` + `uv run python tools/check_decode_intactness.py` +
  `uv run python tools/check_surface_types.py` + `uv run mypy` + targeted
  `uv run pytest verification/test_divergences.py verification/test_main_drivers_bare_except.py -q`
- **Phase gate:** full CI-equivalent green (lint + pre-commit + mypy + `pytest packages` ×2 Python
  versions) **plus** `verify_cycle_closure` non-vacuous ×5 **plus** the two new artifacts
  (`33-CENSUS.md`, `33-LITERALS.md`) before `/gsd-verify-work`.

> **Do not gate on an unqualified `uv run pytest` or on a full `pytest verification` run.** The
> `verification/` directory is red today (`19 failed, 362 passed, 19 errors in 828s`) and takes ~14
> minutes — see P-13. Baseline it in Wave 0; compare against the baseline, not against zero.

### Wave 0 Gaps

- [ ] `verification/test_divergences.py` — handler mapping, non-raising `emit`, level install/restore,
      `extra`-kind capture, ContextVar binding (covers criterion 1's mechanism)
- [ ] `verification/test_cycle_closure_phase33.py` — non-vacuity assertion for criterion 4
- [ ] AST-gate extension (optional but recommended): assert every `probe_*` in the five drivers carries
      the context decorator — the anti-vacuity pattern `test_main_*_uses_single_client_instance.py`
      already establishes
- [ ] Post-run consistency assertion: `FINDING=N` in the SUMMARY == new `### F-` blocks in the findings
      file (catches P-3 regressions)
- [ ] **Red-baseline capture** for `verification/` (`pytest verification -q --tb=no -rfE` → committed
      artifact) so Phase 33 regressions are distinguishable from the 19 failures / 19 errors that are
      already there (P-13)
- [ ] Framework install: **none needed** — pytest/pytest-httpx/pytest-asyncio all present

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Unchanged — each package's existing `login()` / `_ensure_token()`. Phase 33 adds only a **read-only pre-flight** that must never print exception bodies or token material. |
| V3 Session Management | no | No sessions; tokens are per-process module state, unchanged. |
| V4 Access Control | partial | The market-data mutation double gate (`MARKET_DATA_VERIFY_MUTATING=1` **and** hostname match) must remain intact; pass 2 deliberately runs with it off. `verification/test_main_market_data_no_gate_bypass.py` is the guard. |
| V5 Input Validation | yes | `append_finding` validates `class_`, `status`, single-line `title`, and `_PKG_SLUG_RE` on `pkg` (path-traversal defence, WR-04). The handler must feed it validated values — and note that a `ValueError` from any of these is swallowed by P-2. |
| V6 Cryptography | no | No new crypto. `.env` handling unchanged. |
| V7 Error Handling & Logging | **yes — primary** | This phase's entire deliverable is a logging pipeline that writes to a **git-committed** artifact. See threat table. |
| V12 File & Resources | yes | `findings_path` confines writes under `.planning/verification/`; `cycle_report._regression_is_resolvable` rejects `..` and absolute paths and confines resolution to the repo root. Do not bypass either. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Wire values (account IDs, CUIT, instrument identifiers) leaking into a committed findings file | Information Disclosure | **The 6-key record carries type names and our own source identifiers, never values** (Lock 1 + Lock 11). The handler must compose `expected`/`actual`/`diff`/`title` **only** from those six keys plus the endpoint/surface it set itself. Never add the wire value, never widen the record. |
| An `extra`-kind `field_path` whose final segment is a payload-supplied key that happens to be identifier-shaped (a CUIT, an account number) | Information Disclosure | Lock 11's CR-04 amendment: `_decode._safe_key` neutralizes every char outside `[0-9A-Za-z_-]` to `?` and truncates to 64. Sanitization stops injection and inflation, **not** identifier disclosure. Consumers needing suppression filter on `divergence == "extra"` — a single stable predicate the handler can expose as an option. |
| Log injection (newline forging an extra line / a `.` forging a fake decode site) | Tampering | Same `_safe_key` sanitization, upstream in `_decode.py`. Do not re-derive a path in the handler. |
| Credential leakage through a raised exception's body reaching a finding | Information Disclosure | `main_iol.py::_redacted_exc` is that driver's single authorized exception→text boundary (AD-30-09-01); keep the decode-error exemption (its four attributes are certified type-and-path only, T-29-36). For the pre-flight, print only the exception **class name**. |
| Raw wire captured for the Literal census entering git | Information Disclosure | Write only via `verification.capture.capture` → `.planning/verification/captures/`, which is gitignored (`.gitignore:51`). The census **report** may be committed; the payloads may not. |
| Path traversal via a package slug or a `Regression:` path | Tampering | `_PKG_SLUG_RE` (WR-04) and `_regression_is_resolvable` (T-5-06). Both already implemented — use them, do not reimplement. |
| Hijacking a consumer's logging configuration | Tampering / DoS | Attach to `logging.getLogger("<pkg>")` only; never `logging.root`; restore the prior level on exit. Guarded three ways: ruff `LOG` rules, the CI `lint-logging` grep, and `verification/test_logging_root_unchanged.py`. |
| Destructive market-data probes firing twice under the two-pass runner | Tampering (data integrity on `develop`) | Pass 2 runs with `MARKET_DATA_VERIFY_MUTATING` unset (P-11). |
| Silent security-relevant failure inside the handler | Repudiation | P-2's `errors` tally, surfaced in the SUMMARY. A logging pipeline that can fail invisibly cannot be trusted as an audit record. |

---

## Sources

### Primary (HIGH confidence — read from the working tree today, or executed)

- `packages/higyrus-client/src/higyrus_client/_decode.py` (594 lines, read in full) — walker, `POLICY`,
  `DecodeScope`, `STRICT_DECODE`, `_emit`'s `contextlib.suppress`, the `Literal` branch (`:521-534`)
- `verification/findings.py` (706 lines, read in full) — `append_finding`, `idempotent_by_title`,
  preservation short-circuit, `max_existing_fid`, `_PKG_SLUG_RE`
- `verification/cycle_report.py` (176 lines, read in full) — `verify_cycle_closure`, the
  `CONFIRMED`/`FIXED` filter, `_regression_is_resolvable`
- `verification/schema.py`, `verification/env_gate.py`, `verification/capture.py`,
  `verification/__init__.py`, `verification/test_main_drivers_bare_except.py`,
  `verification/test_main_higyrus_uses_single_client_instance.py`,
  `verification/test_logging_root_unchanged.py`
- `main_higyrus.py`, `main_iol.py`, `main_matriz.py`, `main_market_data.py`,
  `main_ambito_financiero.py` — probe counts (19/15/46/43/7 = 130), `_ENDPOINT_TEMPLATES`,
  `_RESIDUAL_PROBE_EXCEPTIONS`, `except Exception` counts (0/12/0/55/6), fid seeding, `_SCHEMA_FILES`,
  `_write_or_check_schema` / `_write_schema_snapshot`, `probe_health_sync`'s two endpoints
- `packages/higyrus-client/src/higyrus_client/client.py` — `strict_decode` kwarg, `_request:375`
  binding, `with_options:229`
- `packages/matriz-client/src/matriz_client/{models,types}.py` — the 7 RESPONSE `Literal` fields and
  the 9 aliases
- `packages/iol-client/src/iol_client/{types,models,_core}.py` — the empty `types.py` placeholder,
  `Titulo.mercado`/`Titulo.plazo`, `parse_get_instruments_by_type_response`
- `.github/workflows/ci.yml`, `pyproject.toml`, `.pre-commit-config.yaml`,
  `tools/check_decode_intactness.py`, `.gitignore`
- `.planning/phases/29-decoder-observable/{29-SIZING.md, 29-AGGREGATION-CONTRACT.md,
  29-DLOCK-RESPONSE-LITERAL.md}`
- `.planning/phases/33-.../33-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`,
  `.planning/future-plans/tipado_homogeneo.md`, `./CLAUDE.md`
- **Executed checks** (CPython): logger effective level / `isEnabledFor(INFO)`; ContextVar visibility
  inside `Handler.emit`; reserved-key `KeyError`; handler exception swallowed by
  `contextlib.suppress`; `verify_cycle_closure` ×5; `load_dotenv` resolution under `python -c` vs a
  real `.py` file; `uv`/`pytest`/`httpx` versions; findings-file fid and status inventory; matriz
  schema file count 17 declared vs 8 on disk; **full `uv run pytest verification` run —
  `19 failed, 362 passed, 19 errors in 828.19s`**

### Secondary (MEDIUM confidence)

- `.planning/phases/{30,31,32}/*-CONTEXT.md`, `*-PATTERNS.md` — conventions and precedents referenced
  but not re-verified line by line in this session

### Tertiary (LOW confidence)

- `CLAUDE.md`'s ARCHITECTURE section — **known stale** on matriz async support (it states matriz has no
  `aio.py`; the driver constructs an `AsyncClient` and 20+ async probes exist). Treat that section as
  documentation lag, not as a constraint.
- Skills `spike-findings-market-libs` and `spike-findings-codegen-market-libs` — inspected for
  relevance per the task brief; **neither applies to this phase** (TokenStore/refresh-policy from
  Phase 10, and the permanently-archived codegen NO-GO).

**No external documentation lookup was required or performed:** this phase adds no third-party
dependency, and every design constraint is a signed in-repo artifact.

---

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — zero new dependencies; every module is stdlib or already committed, with
  installed versions read from the live workspace.
- Architecture: **HIGH** — the handler contract is a signed artifact (Lock 10) and the three additions
  (level raise, self-guarding `emit`, shared fid allocator) are each backed by an executed reproduction.
- Pitfalls: **HIGH** — P-1, P-2, P-10, P-13 reproduced by execution; P-3, P-4, P-5, P-7, P-8, P-9,
  P-11 measured directly from the working tree; P-6 read at the source line; P-12 sourced from
  `29-SIZING.md` S-5. The only partial gap is the full enumeration of P-13's 19 failures / 19 errors
  (Open Question 4) — the count and the dominant failure are measured; the long tail is not.
- Live-run outcomes (credential validity, reachability, actual census volume): **LOW by nature** — see
  Assumptions A1–A4. These are runtime facts no research pass can settle.

**Research date:** 2026-08-26
**Valid until:** 2026-09-25 (30 days — internal codebase, stable; re-verify if any driver, `_decode.py`
copy, or findings file is edited before planning)
