# Phase 9: Deferred Bug Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 09-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 9-Deferred Bug Fixes
**Areas discussed:** BUG-01 detection mechanism, BUG-04 API surface choice, BUG-02 investigation depth
**Areas skipped (operator delegated to Claude):** Plan slicing + live re-verification scope

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| BUG-01 detection mechanism | Cómo detectar CFI inválido en runtime (Literal vs regex vs detect-empty); dónde vive el guard (builder vs parser) y qué excepción se levanta. | ✓ |
| BUG-04 API surface choice | Per-call vs constructor-level vs both para multi-account; define si `_state.account_id` queda load-bearing. | ✓ |
| BUG-02 investigation depth | Quick triage vs deep root-cause vs defer; el outcome (fix code o doc-only) depende del root cause. | ✓ |
| Plan slicing + live re-verification scope | Per-bug vs per-package slicing; matriz-only live vs defer all live a Phase 11. | (delegated) |

**User's choice:** Discutir las primeras 3; la 4ta delegada al per-package serial idiom Phase 6/7/8 baseline.

---

## BUG-01 detection mechanism

### Sub-question 1: ¿Dónde y cómo se hace el guard de CFI inválido?

| Option | Description | Selected |
|--------|-------------|----------|
| Literal-set check en el builder | `if cfi_code not in get_args(CFICode): raise PrimaryAPIError`. Pros: alineado con tipo, zero false positives, falla pre-HTTP. Cons: cerrado al set fijo de 9 CFIs. | ✓ |
| Regex ISO 10962 en el builder | `^[A-Z]{6}$` regex. Pros: tolerante a CFIs futuros. Cons: NO valida semánticamente (ZZZZZZ pasa pero sigue inválido para Primary). | |
| Detect 200 OK + empty instruments en el parser | `if not raw['instruments']: raise`. PROBLEMA: false positives en CFIs válidos con cero matches. Listado solo para descartar. | |

**User's choice:** Literal-set check en el builder
**Notes:** Implica deviation explícito del literal de ROADMAP (`_core.raise_for_response()`) — documentado en 09-CONTEXT.md D-02. La excepción levantada (`PrimaryAPIError(status="ERROR")`) preserva el contrato observable del probe `error_malformed_cfi`.

### Sub-question 2: Forward-compatibility cuando Primary agrega un CFI nuevo

| Option | Description | Selected |
|--------|-------------|----------|
| Strict reject — hay que updatear types.py | Cualquier CFI fuera del set actual = error. Pros: contrato 100% alineado con tipo, regression trivial. Cons: requiere lib update para CFIs nuevos. | |
| Hybrid — Literal stricter + regex como fallback | Literal set OR `^[A-Z]{6}$` regex; lo demás raise. Pros: tolera Primary agregando CFIs sin breaking change. Cons: regla más compleja, 3 buckets de test. | ✓ |
| Strict reject + ADR para extension policy | Strict reject + documentar process en CONTEXT.md. Pros: contrato claro. Cons: ninguno extra vs A. | |

**User's choice:** Hybrid — Literal stricter + regex como fallback
**Notes:** Regression test cubre 3 buckets explícitamente (literal-known, regex-forward-compat, malformed). El planner final paramétriza los inputs.

---

## BUG-04 API surface choice

### Sub-question 1: ¿Cómo expone higyrus multi-account iteration?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-call only (status quo, mantener) | `client.get_X(id_cuenta=Y)` per-call. `_state.account_id` queda unused. Pros: zero change. Cons: ROADMAP success #4 dice "Client(account_id=X) OR per-call" — esta opción elige solo el OR derecho. | ✓ |
| Constructor default + per-call override (recomendado) | `Client(account_id='5208')` set default; per-call override. Pros: ergonómico para single-tenant. Cons: 4 builders cambian signature, snapshot público se updatea. | |
| Constructor-only (instancia 1 por cuenta) | `Client(account_id='5208')`, no kwarg per-call. BREAKING — 277 tests revientan; descartable. | |

**User's choice:** Per-call only (status quo, mantener)
**Notes:** Operator elige el OR derecho del literal ROADMAP success #4. Nada que añadir a la API pública; cero ripple downstream.

### Sub-question 2: BUG-04 cleanup — `_state.account_id` forward-declared

| Option | Description | Selected |
|--------|-------------|----------|
| Remove `_state.account_id` de higyrus + iol | Field muerto post-D-08; clean removal + docstring update. | ✓ |
| Keep `_state.account_id` (defer constructor pattern a v1.2) | Mantener unused + docstring "reservado para v1.2". | |
| Keep + wirearlo como hint solo en logs | Client(account_id=) guardado en state + propagado a `request.extensions` para log correlation; no afecta routing. | |

**User's choice:** Remove `_state.account_id` de higyrus + iol
**Notes:** Cross-package cleanup; iol también tenía el field forward-declared (Phase 6 D-13 con cross-package shape consistency). Plan 09-02 lo elimina en ambos paquetes como parte del higyrus commit (deviation atomic-per-package documentada en D-11 nota).

### Sub-question 3: BUG-04 live regression — ≥2 cuentas

| Option | Description | Selected |
|--------|-------------|----------|
| Sí — 2+ cuentas reales disponibles | El `.env` higyrus tiene ≥2 cuentas activas; driver itera dinámicamente o usa `HIGYRUS_SAMPLE_CUENTAS` override. | ✓ |
| Solo 1 cuenta real — mockear la 2da | Mocked cubre ambos paths; live solo la real (5208). Success criteria parcial. | |
| Solo 1 cuenta y BUG-02 bloquea la iteración | Hardcoded + mockeado; live full gated en BUG-02 resolution. | |

**User's choice:** Sí — 2+ cuentas reales disponibles
**Notes:** Probe usa `get_listado_cuentas()` si non-empty O `HIGYRUS_SAMPLE_CUENTAS` env var CSV como fallback. No bloquea BUG-02 — BUG-04 cierra con o sin el listado dinámico funcionando.

---

## BUG-02 investigation depth

| Option | Description | Selected |
|--------|-------------|----------|
| Quick triage + classify (recomendado) | Live re-run con Phase 8 DEBUG logging; comparar vs smoke pre-Phase-4; classify outcome en 3 buckets (transient NO-FIX, FIXED-by-environment, client-side fix). Time-box 1 plan. | ✓ |
| Deep root-cause + Higyrus support contact | Script aislado replay + Higyrus support; potential blocker en respuesta externa. Probable scope creep. | |
| Defer BUG-02 a v1.2 + cerrar como OPEN-ACCEPTED | Documentar requiere Higyrus team; regression mockeado mínimo; live BLOCKED. Cierra como FINDING OPEN. | |

**User's choice:** Quick triage + classify (recomendado)
**Notes:** Outcome decide path:
- (a) Reproducible + transient → NO-FIX (Phase 8 retries amortiguan)
- (b) NO reproducible → FIXED-by-environment
- (c) Reproducible + client-side root cause → fix en `_core.py`

El plan documenta los 3 buckets inline para que el executor pueda clasificar sin re-discusión.

---

## Claude's Discretion

- **Plan slicing + live re-verification scope:** delegado por el operator. Aplico per-package serial idiom Phase 6/7/8: 4 planes (Wave 1: iol + higyrus paralelos; Wave 2: matriz; Wave 3: green gate). Live scope = bug-driven (higyrus live para BUG-02/04, matriz live para BUG-01, no live para iol BUG-03 o ámbito). Full × 4 live re-verification queda en Phase 11 LIVE-01.

- **Layout tests sync/async (Plan 09-01):** recomiendo 2 archivos separados (`test_refresh_token_lifecycle.py` + `..._async.py`) sobre paramétrización por surface. Planner final decide.

- **Probe naming (`main_higyrus.py` BUG-04):** `probe_multi_account_iteration` como default; planner verifica idiom existente del driver.

- **`HIGYRUS_SAMPLE_CUENTAS` format:** CSV (`"5208,9999"`) como default (compatibilidad `.env`).

- **Live re-run matriz dentro del Plan 09-03:** step manual operator-executed (riesgo de mutating gate + matriz blast radius); plan documenta comando y probes esperados PASS.

- **Mocked regression test BUG-01 ubicación:** `packages/matriz-client/tests/test_core.py` extend (affinity con el builder).

- **Resolution: line format en findings:** free-text con marker `(a)/(b)/(c)` para forensic-localizable.

- **`_state.account_id` removal — si rompe test preexistente:** extend Plan 09-02 (mantiene atomic).

- **Verbosidad del finding update post-fix:** mínimo + 1-2 lines rationale.

---

## Deferred Ideas

(Capturados en 09-CONTEXT.md `<deferred>` section. Resumen ejecutivo:)

- `Client(account_id=X)` constructor pattern para higyrus + iol (v1.2 if UX feedback)
- Constructor con `account_id` solo para log correlation (rechazado en Phase 9)
- Disk persistence IOL refresh_token cross-process (v1.2)
- Literal-runtime-validation pattern para MarketId/SegmentId/Side/OrderType/TimeInForce (v1.2 / v1.3 si emerge similar bug)
- Higyrus support contact para BUG-02 deep root-cause (v1.2 polish si triage no resuelve)
- BUG-02 isolated replay script + multi-session capture (v1.2)
- `HIGYRUS_SAMPLE_CUENTAS` promote a `verification/env_gate.py` registry (v1.2)
- Probe-scoped DEBUG logging via context manager helper (v1.2 si pattern se repite)
- Sub-loggers por concern `<pkg>.refresh`, `<pkg>.auth` (v1.2 si BUG-02 DEBUG noise inmanejable)
- Per-test `httpx-mock` factory for refresh flow (v1.2 si duplicación emerge)
