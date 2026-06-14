---
phase: 07-core-py-extraction-sync-async-logic-dedup
verified: 2026-06-12T20:00:00Z
status: complete
resolved_at: 2026-06-14T02:10:00Z
resolved_by: gsd-audit-uat (post-Phase 10) + operator signoff (LOC drop accepted)
operator_signoff:
  test_2_loc_drop_disposition: "accepted — v1.2 driver migration tracks the residual drop"
  signoff_date: 2026-06-14
  signoff_by: sebadlf
score: 5/5 must-haves verified (SC#3 deviation accepted by operator as v1.2 carry-forward)
overrides_applied: 0
human_verification:
  - test: "Confirmar que CI matrix Python 3.12 + 3.13 está verde en el PR de Phase 7 en GitHub"
    expected: "Todos los jobs (lint, pre-commit, typecheck, Tests × pkg × py3.12/3.13) muestran check verde. Excepción documentada: job lint puede ser rojo por pre-existing spike artifacts en .planning/spikes/ y .claude/skills/ — fuera de scope Phase 7, rastreados en deferred-items.md."
    why_human: "La ejecución local sólo valida CPython 3.12.11 en macOS. La matrix CI corre Ubuntu × Python 3.12 + Python 3.13 en paralelo. Fallos de compatibilidad 3.13, normalización de paths OS-specific o locale-sensitive sorting sólo aparecen en CI. Verificación local completa — falta cruce CI remoto."
  - test: "Confirmar que las desviaciones LOC documentadas (iol -5.1%, matriz client.py -20%) son aceptadas como path-forward para v1.2"
    expected: "Operator review de 07-03-SUMMARY sección 'Acknowledged Deviation' + 07-05-SUMMARY sección 'LOC drop target'. Mensaje de aprobación: 'accepted — v1.2 driver migration tracks the residual drop' o 'blocked — extend plans to recover LOC drop'."
    why_human: "Decisión arquitectónica — el verifier no puede resolver si el operador prefiere extender los planes o aceptar la desviación. El SC#3 es PARTIAL (2/4 paquetes PASS, 2 con desviaciones documentadas y aceptadas en sus respectivos SUMMARY.md)."
---

# Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup — Verification Report

**Phase Goal:** Eliminar la duplicación de lógica entre `client.py` y `aio.py` por paquete; ambos quedan como shells de transporte sobre helpers puros en `_core.py`.
**Verified:** 2026-06-12T20:00:00Z
**Status:** human_needed
**Re-verification:** No — verificación inicial.

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | `_core.py` por paquete contiene builders/parsers/auth-flow + no importa `httpx.Client`/`httpx.AsyncClient` ni `client.py`/`aio.py` | VERIFIED | 4 `_core.py` existen con contenido sustantivo (ámbito 147 LOC, iol 318, higyrus 437, matriz 728). `lint-imports` retorna "Contracts: 4 kept, 0 broken". Grep de imports prohibidos en los 4 archivos devuelve cero resultados. |
| SC2 | CI rule import-linter bloquea `_core → client/aio`; sentinel `SYNC-sentinel-<pkg>` vs `ASYNC-sentinel-<pkg>` detecta re-coupling | VERIFIED | `.github/workflows/ci.yml` tiene step `run: uv run lint-imports`. `verification/test_sync_async_isolation.py` ejecutado: 7 passed + 1 skipped (matriz async con reason D-11). Sentinels distintos confirmados en ambas superficies. |
| SC3 | `client.py` y `aio.py` miden ≤30-50 LOC/endpoint group; LOC drop ≥30% vs Phase 6 baseline | PARTIAL | ámbito: 557→383 (-31.2%) PASS. higyrus: 1354→929 (-31.4%) PASS (post review-fix). iol: 998→947 (-5.1%) FAIL (desviación documentada). matriz client.py: 754→603 (-20.0%) FAIL (desviación documentada). 2 de 4 paquetes cumplen target; 2 con desviaciones justificadas en SUMMARYs. Ver sección Deferred Items. |
| SC4 | CR-03 cerrado: `parse_envelope_response` consume body explícitamente antes de raise | VERIFIED | `test_parse_envelope_consumes_body_before_raise` PASSED. Source: línea 193 `resp.read()` antes de línea 194 `raise_for_response(resp)` en `_core.py` de matriz. Orden D-06 confirmado. |
| SC5 | CR-05 cerrado: 18 probes refactorizadas a `_envelope_probe(envelope_key=...)`; 2 risk con `envelope_key=None`; 277+ tests verde | VERIFIED | `grep -c "^def _envelope_probe" main_matriz.py` == 1. `grep -c "_envelope_probe(" main_matriz.py` == 15. `grep -c "envelope_key=None" main_matriz.py` == 3 (2 risk + 1 helper def). 3 probes custom preservadas (`probe_get_segments`, `probe_get_all_instruments`, `probe_get_market_data`). `test_matriz_sweep_snapshot.py` 20/20 PASSED. Suite completa: 527 passed, 2 skipped, 1 deselected. |

**Score:** 4/5 truths verified (SC3 parcial — 2/4 paquetes, desviaciones documentadas)

---

### Deferred Items

Los fallos de SC3 (LOC drop para iol y matriz) están documentados como desviaciones aceptadas en los respectivos SUMMARY.md y son candidatos a resolverse en v1.2. No son items faltantes por omisión; son decisiones arquitectónicas explícitas por invariantes que no podían romperse (back-compat surface, PEP 562 shim, D-16 public snapshot, D-23 lifecycle methods).

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | iol LOC drop: 998→947 (-5.1% vs target ≥30%) | v1.2 (Phase 9 o posterior driver migration) | 07-03-SUMMARY §"Acknowledged Deviation": back-compat shims + PEP 562 + D-23 lifecycle = ~340 LOC no removibles sin romper invariantes Phase 6. v1.2 puede migrar `main_iol.py` al nuevo `Client._request(spec)` API y eliminar la back-compat surface. |
| 2 | matriz client.py LOC drop: 754→603 (-20% vs target ≥30%) | v1.2 (driver migration) | 07-05-SUMMARY §"LOC drop target": 22 delegators + PEP 562 + Pitfall 7 wrappers = ~75 LOC back-compat. Migrar `main_matriz.py` al `Client._request(spec)` API en v1.2 permite drop adicional ~35 LOC → ~570 LOC final. |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` | RequestSpec + builders + parsers + raise_for_response (puro, sin transport) | VERIFIED | 147 LOC. Contiene `class RequestSpec`, `def build_get_dollar_banco_nacion_request`, `def parse_get_dollar_banco_nacion_response`, `def raise_for_response`. Sin imports de `ambito_financiero_client.client` o `.aio`. |
| `packages/iol-client/src/iol_client/_core.py` | RequestSpec (con `data`) + auth-flow + builders + parsers | VERIFIED | 318 LOC. Contiene `build_login_request`, `parse_login_response`, `build_refresh_request`, `parse_refresh_response`, `token_is_fresh`, ≥5 endpoint builders/parsers. Sin imports prohibidos. |
| `packages/higyrus-client/src/higyrus_client/_core.py` | RequestSpec (con `json_body` + `url_pre_encoded`) + URL-encoding quirk encapsulado + auth-flow | VERIFIED | 437 LOC. Contiene `url_pre_encoded` field, `urlencode` con `doseq=True` (4 ocurrencias). `urlencode` NO aparece en `client.py` ni `aio.py` — encapsulación correcta. |
| `packages/matriz-client/src/matriz_client/_core.py` | RequestSpec (`auth_basic`) + `parse_envelope_response` (CR-03) + `unwrap` + auth-flow + builders/parsers | VERIFIED | 728 LOC. Contiene `parse_envelope_response` con orden D-06 (`resp.read()` línea 193, `raise_for_response` línea 194). `unwrap` presente. `auth_basic` field en RequestSpec. |
| `pyproject.toml` | `import-linter>=2.11,<3` en `[dependency-groups] dev` + `[tool.importlinter]` con 4 contracts forbidden | VERIFIED | `grep -c "import-linter>=2.11" pyproject.toml` == 1. `grep -c "\[\[tool.importlinter.contracts\]\]" pyproject.toml` == 4. |
| `.github/workflows/ci.yml` | Step `uv run lint-imports` en job lint | VERIFIED | `grep -c "lint-imports" ci.yml` == 1. Step confirmado presente. |
| `verification/test_sync_async_isolation.py` | Cross-leak sentinel parametrizado: 4 sync + 4 async (matriz async skip con reason D-11) | VERIFIED | Existente. `SYNC-sentinel` aparece 6 veces, `ASYNC-sentinel` 3 veces. `pytest.skip` == 1 con reason "matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore". Ejecución: 7 passed + 1 skipped. |
| `verification/test_matriz_sweep_snapshot.py` | Snapshot guard 18+ probes parametrizado | VERIFIED | 305 LOC, 20 test cases PASSED (17 parametrizados + 3 invariant tests). Incluye `test_matriz_risk_probes_use_envelope_key_none`. |
| `main_matriz.py` | `_envelope_probe` helper + 15 migrations + 2 risk (`envelope_key=None`) + 3 custom probes preservadas | VERIFIED | `grep -c "^def _envelope_probe"` == 1. `grep -c "_envelope_probe("` == 15. `grep -c "envelope_key=None"` == 3. 3 custom probes preservadas por side-effects. |
| `packages/*/tests/test_core.py` (4 archivos) | Unit tests por paquete: ámbito ≥4, iol ≥6, higyrus ≥6, matriz ≥8 | VERIFIED | ámbito 149 LOC, iol 371 LOC, higyrus 435 LOC, matriz 305 LOC. `test_parse_envelope_consumes_body_before_raise` presente y verde en matriz. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_core.py` (4 pkgs) | nunca `client.py`/`aio.py` | import-linter forbidden contract | WIRED | `lint-imports` 4 contracts KEPT, 0 broken. Verificado en runtime. |
| `client.py._raise_for_response` (4 pkgs) | `_core.raise_for_response` | módulo-level alias D-04 | WIRED | `_raise_for_response = _core.raise_for_response` confirmado en ambito, iol, higyrus, matriz. |
| `aio._raise_for_response` (ambito, iol, higyrus) | `_core.raise_for_response` | alias o import explícito D-04 | WIRED | B8 identity verificado: `a_a is a_c == True` para ambito, iol, higyrus. matriz aio.py es stub Phase 6 por diseño. |
| `client.py.Client._request(spec)` | `_core.RequestSpec` | parámetro spec (D-03) | WIRED | `def _request(self, spec: _core.RequestSpec)` confirmado en los 4 `client.py`. También en `aio.py` para ambito, iol, higyrus. |
| `client.py` endpoints | `_core.build_X_request + parse_X_response` | 3-liner shell | WIRED | `grep -n "_core.build_\|_core.parse_"` en cada `client.py` muestra múltiples hits. Análogo en `aio.py`. |
| `main_matriz.py._envelope_probe` | `_core.parse_envelope_response` (via client shell) | back-compat wrapper `_matriz_legacy_request` | WIRED | `callable(main_matriz._envelope_probe)` == True. 15 llamadas al helper en `main_matriz.py`. |
| `parse_envelope_response` CR-03 | `resp.read()` ANTES de `raise_for_response` | línea 193 < 194 en `_core.py` de matriz | WIRED | Líneas verificadas directamente: `resp.read()` L193, `raise_for_response(resp)` L194. |
| `CI .github/workflows/ci.yml` | `uv run lint-imports` | step en job lint | WIRED | Step presente en CI yml. |

---

### Data-Flow Trace (Level 4)

No aplica directamente — esta fase produce módulos de biblioteca (no componentes que renderizan datos dinámicos). La data-flow relevante es el flujo `state → RequestSpec → httpx.Response → typed result`, verificado via los tests de los transport shells y los sentinel tests que confirman que el token correcto llega al wire request.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `lint-imports` 4 contracts | `uv run lint-imports` | "Contracts: 4 kept, 0 broken" exit 0 | PASS |
| B8 alias identity (3 pkgs) | `uv run python -c "assert a_a is a_c..."` | "B8 identity verified for ambito, iol, higyrus" | PASS |
| CR-03 test | `uv run pytest ...::test_parse_envelope_consumes_body_before_raise` | 1 passed | PASS |
| CR-05 sweep snapshot | `uv run pytest verification/test_matriz_sweep_snapshot.py` | 20 passed | PASS |
| Full test suite | `uv run pytest -q` | 527 passed, 2 skipped, 1 deselected | PASS |
| mypy strict | `uv run mypy` | "Success: no issues found in 34 source files" | PASS |
| ruff check (phase scope) | `uv run ruff check packages/ verification/ main_*.py` | "All checks passed!" | PASS |
| Cross-leak sentinel | `uv run pytest verification/test_sync_async_isolation.py` | 7 passed, 1 skipped | PASS |
| Public surface snapshot | `uv run pytest verification/test_public_surface.py` | 4 passed | PASS |

---

### Probe Execution

No existen probe scripts `.sh` declarados para esta fase. Los behavioral spot-checks anteriores cubren el equivalente funcional.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REFAC-03 | 07-01 a 07-06 | `_core.py` por paquete con builders/parsers + shells de transporte + CI rule import-linter | SATISFIED | 4 `_core.py` sustantivos entregados. `lint-imports` 4 contracts KEPT. Transport shells confirmados. 527 tests verde. |
| CR-03 | 07-05 | `_request` de matriz consume body antes de raise cuando `status=="ERROR"` | SATISFIED | `parse_envelope_response` línea 193 `resp.read()` < línea 194 `raise_for_response`. Test guard `test_parse_envelope_consumes_body_before_raise` PASSED. |
| CR-05 | 07-05 | 18 sweep probes refactorizadas a `_envelope_probe(envelope_key=...)` | SATISFIED | 15 calls al helper en `main_matriz.py`. 2 risk probes con `envelope_key=None`. 3 custom probes preservadas. Sweep snapshot 20/20 PASSED. |

**Orphaned requirements:** Ninguno. Los únicos REQ-IDs mapeados a Phase 7 en REQUIREMENTS.md son REFAC-03, CR-03 y CR-05. Los demás (REFAC-01/02/04, BUG-*, HARN-*, LOG-*, RELY-*, CR-01/02/04/06/07/08, LIVE-*) pertenecen a otras fases.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `packages/matriz-client/src/matriz_client/types.py` | 51-58 | Literales `ESXXXX`, `DBXXXX`, `FXXXSX`, `EMXXXX` | INFO | NO es deuda: son valores `Literal[...]` de CFI codes ISO 10962 (identificadores de instrumentos financieros de la industria). Pre-existente al Phase 7. No son marcadores de deuda. |

No se encontraron marcadores de deuda (`TBD`, `FIXME`, `XXX`) en ningún archivo modificado por Phase 7. Los términos `XXXX` en los archivos escaneados son literales de datos financieros (CFI codes), no comentarios TODO.

---

### Human Verification Required

#### 1. CI Matrix Python 3.12 + 3.13

**Test:** Visitar el PR de Phase 7 en GitHub. En la pestaña "Checks", verificar que todos los jobs muestran check verde: `lint`, `pre-commit`, `typecheck`, `Tests · <pkg> · py3.12`, `Tests · <pkg> · py3.13`.

**Expected:** Todos los jobs verdes excepto posiblemente `lint` por los 108 ruff errors pre-existentes en `.planning/spikes/` y `.claude/skills/spike-findings-market-libs/sources/` (no son Phase 7, rastreados en `deferred-items.md`). Si `lint` es rojo únicamente por esos archivos fuera de scope, el veredicto sigue siendo PASS.

**Why human:** La ejecución local sólo valida CPython 3.12.11 en macOS. La matrix CI corre Ubuntu × Python 3.12 + Python 3.13 en paralelo. Ciertos fallos (3.13 wheel resolution, OS path normalization, locale-sensitive sorting) solo aparecen en CI remoto.

#### 2. Decisión sobre desviaciones LOC (SC3 partial)

**Test:** Revisar `07-03-SUMMARY.md` (sección "Acknowledged Deviation" para iol) y `07-05-SUMMARY.md` (sección "LOC drop target" para matriz). Confirmar que las justificaciones técnicas son aceptables para el proyecto.

**Expected:** Operator emite uno de: (a) "accepted — v1.2 driver migration tracks the residual drop" o (b) "blocked — extend plans 07-03/07-05 to recover LOC drop".

**Why human:** SC3 es PARTIAL (2/4 paquetes PASS). Las desviaciones tienen justificaciones técnicas sólidas (invariantes que no pueden romperse sin cambios de scope), pero la decisión de aceptarlas como close-out es del operador, no del verifier.

---

### Gaps Summary

No hay gaps bloqueantes. La única razón para `human_needed` son dos items que requieren decisión del operador:

1. **SC3 parcial** — desviación LOC documentada y justificada; necesita aprobación explícita del operador para cerrar la fase.
2. **CI matrix remota** — verificación local completa, CI remota (Python 3.13) no confirmada por este verifier.

Los 4 ROADMAP Success Criteria restantes (SC1, SC2, SC4, SC5) están VERIFIED con evidencia en codebase. Los 3 REQ-IDs (REFAC-03, CR-03, CR-05) están SATISFIED.

---

### Resolution (post-Phase 10 closure — gsd-audit-uat 2026-06-14)

#### 1. CI Matrix Python 3.12 + 3.13 — ✓ RESUELTO

**Evidence:**
- Local 3.12 + 3.13 capturado durante Phase 10 closure: ambas versiones → 876 passed, 1 deselected (logs `/tmp/phase10-gate/pytest-3{12,13}.log`).
- GitHub Actions CI run `27415270321` (commit `5db0a0d`, 2026-06-12): ✓ Tests × 5 packages × py3.12 + py3.13 = **10/10 jobs GREEN**, ✓ Type check (mypy) GREEN.
- Lint y pre-commit jobs rojo por **108 ruff errors pre-existentes en `.claude/skills/spike-findings-market-libs/sources/*` y `.planning/spikes/*`** (commit 2026-06-13 — spike sources committed for documentation). Confirmado como excepción aceptable por el verifier original ("job lint puede ser rojo por pre-existing spike artifacts ... fuera de scope Phase 7"). Cierre formal en Phase 11 vía `extend-exclude`.

**Status:** ✓ CLOSED. Veredicto sigue siendo PASS — los jobs in-scope (tests + typecheck) son green; lint rojo es no-regresión documentada.

#### 2. Decisión sobre desviaciones LOC (SC3 partial) — ✓ RESUELTO (operator accepted 2026-06-14)

**Operator signoff:** `accepted — v1.2 driver migration tracks the residual drop`
**Signoff by:** sebadlf
**Signoff date:** 2026-06-14
**Context:** Las desviaciones técnicas iol -5.1% y matriz client.py -20% están bien documentadas en `07-03-SUMMARY.md ## Acknowledged Deviation` y `07-05-SUMMARY.md ## LOC drop target` — son consecuencia de la abstracción Client class + transport shells que el refactor introduce (no se puede romper el invariante sin cambio de scope). v1.2 driver migration (separar la lógica de driver de la del shell de transporte) será el ciclo donde el LOC residual cierra de forma orgánica.

**Status:** ✓ CLOSED. SC#3 partial-PASS → SC#3 accepted-PASS con disposition formal.

---

_Verified: 2026-06-12T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Resolved: 2026-06-14T02:10:00Z (gsd-audit-uat post-Phase 10; test 1 closed via CI evidence; test 2 closed via operator signoff — LOC drop accepted as v1.2 carry-forward)_
