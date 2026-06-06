---
phase: 03-iol-verification
verified: 2026-06-06T17:30:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Ejecutar probe_auth_401 con VERIFY_IOL_BAD_CREDS=1 contra api.invertironline.com"
    expected: "PROBE auth_401: FINDING F-NN (EXPECTED), status_code=401 en el findings file; exit 0"
    why_human: "IOL-05 requiere verificación en vivo de la excepción 401 con credenciales inválidas. Pitfall 9 prohíbe ejecución automática sin supervisión humana (riesgo de lockout). El probe está implementado y opt-in; la verificación en vivo queda pendiente de que el equipo lo corra deliberadamente."
---

# Phase 3: IOL Verification — Verification Report

**Phase Goal:** The IOL client — the highest silent-shape risk in the codebase (raw `dict`, zero validation) — is fully verified end-to-end on both surfaces with retained payloads and an observed field→type map, the auth and 401 paths are confirmed without lockout risk, and the known `refresh_token` bug is fixed in both surfaces with regression tests.
**Verified:** 2026-06-06T17:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Auth flow (`login()` + lazy-auth) verificado en vivo sync y async con auth-once discipline; superficie de lectura completa (`get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type`) ejercitada con raw payloads retenidos (IOL-01, IOL-02) | ✓ VERIFIED | `03-03-SUMMARY.md` live-run output: todos los probes 1-10 PASS con exit 0; 4 schema snapshots escritos en disco y commiteados |
| 2  | Mapa campo→tipo observado construido y comparado contra asunciones del caller; clave de envelope `["titulos"]` confirmada presente en el wire; campos numéricos llegan como JSON number (IOL-03, IOL-04) | ✓ VERIFIED | `probe_field_type_map` FINDING F-01 (OPEN) documenta que `simbolo` no está en el payload de `get_quote` (asunción del driver, no bug del cliente); `get-instruments-by-type.json` contiene `"titulos"` en el top-level del schema (Pitfall 2 envelope verificado); `test_get_quote_url_exacta_con_query_string` lockea `isinstance(ultimoPrecio, int\|float)` |
| 3  | Path 401 implementado y opt-in sin riesgo de lockout; paridad estructural sync↔async confirmada en los 4 endpoints (IOL-05, IOL-06) | ✓ VERIFIED (parcial — ver human_needed) | `probe_parity_sync_async` PASS `4 endpoints, drift=0`; `probe_auth_401` implementado con try/finally CR-03, opt-in `VERIFY_IOL_BAD_CREDS=1`, single-shot sin sleep. La verificación in-vivo de IOL-05 NO se ejecutó (Pitfall 9 — ver human_verification) |
| 4  | `grant_type=refresh_token` con fallback a password grant implementado en `client.py` y `aio.py`; tests cubren refresh exitoso, fallback, ambos fallan, login captura; fix verificado in-vivo (IOL-07) | ✓ VERIFIED | `client.py:122-152` `_refresh()` + `aio.py:125-159` `_refresh_unlocked()`; `_ensure_token()` con rama refresh→password en ambas superficies; 8 regression tests en sección `# ------ Regressions ------`; `probe_refresh_token` PASS "token rotated, _refresh_token=rotated" en live run |
| 5  | Toda discrepancia clasificada en `iol-client-findings.md`; 4 schema snapshots committeados; cada bug confirmado (CR-01/02/03) corregido en ambas superficies con regression tests mockeados; suite + mypy strict + ruff verdes (IOL-03..07, DRIFT-01) | ✓ VERIFIED | Commits `620b2f9` (5 artefactos), `e80bc35` (CR-01), `82ea256` (CR-02), `0cae4e6` (CR-03); `uv run pytest -q` → 198 passed, 1 deselected; mypy: "Success: no issues found in 7 source files"; ruff: "All checks passed" |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/iol-client/src/iol_client/client.py` | `_refresh_token` singleton, `_refresh()`, `_ensure_token` fallback | ✓ VERIFIED | L55 `_refresh_token: str | None = None`; L122 `def _refresh()`; L155-166 `_ensure_token` con rama refresh→password. CR-01 fix: `login()` preserva cached refresh_token cuando server lo omite |
| `packages/iol-client/src/iol_client/aio.py` | Mirror async: `_refresh_token`, `_refresh_unlocked()`, double-checked locking | ✓ VERIFIED | L37 `_refresh_token: str | None = None`; L125 `async def _refresh_unlocked()`; L168-182 `_ensure_token` con rama refresh dentro del `_token_lock`. Pitfall 6 anti-deadlock confirmado (solo `await client.post` directo) |
| `packages/iol-client/tests/test_client.py` | Sección `# ------ Regressions ------` con 4 tests sync IOL-07 + sección `# ------ Verified live (Phase 3) ------` con 3 invariantes | ✓ VERIFIED | Divider Verified live (pos 3162) precede a Regressions (pos 5223); 4 tests refresh + 3 invariantes IOL-04 presentes; 3 tests CR adicionales (CR-01/CR-03) |
| `packages/iol-client/tests/test_async_client.py` | Espejo async de ambas secciones | ✓ VERIFIED | Divider Verified live (pos 1856) precede a Regressions (pos 3972); 4 tests async refresh + 3 invariantes async |
| `main_iol.py` | 15 probes nombrados en orden D-IOL-5 | ✓ VERIFIED | 15 funciones `probe_*` confirmadas; `asyncio.run` count=1; `time.sleep` ausente; `VERIFY_IOL_BAD_CREDS` presente; `_INVALID` presente; `contextlib.suppress` presente |
| `.planning/verification/iol-client-findings.md` | Esqueleto + F-01 OPEN del live run | ✓ VERIFIED | Archivo commiteado (commit `620b2f9`); contiene `# Findings: iol-client-client`, `## Run Context (ART)`, F-01 SHAPE OPEN documentado |
| `.planning/verification/schemas/iol-client/get-quote.json` | Envelope D-21 con 6 keys | ✓ VERIFIED | 6 keys presentes (`endpoint`, `client_function`, `captured_at`, `base_url`, `sample_params`, `schema`); schema contiene `ultimoPrecio: "float"` |
| `.planning/verification/schemas/iol-client/get-historical-quotes.json` | Envelope D-21 | ✓ VERIFIED | 6 keys presentes |
| `.planning/verification/schemas/iol-client/get-instruments.json` | Envelope D-21 | ✓ VERIFIED | 6 keys presentes |
| `.planning/verification/schemas/iol-client/get-instruments-by-type.json` | Envelope D-21 con `"titulos"` en top-level del schema (Pitfall 2) | ✓ VERIFIED | `schema` es dict con key `"titulos"` en top-level — `schema_of` capturó el envelope crudo (NO la lista unwrapped del wrapper) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `client.py::_ensure_token` | `client.py::_refresh` | `if _refresh_token: try: _refresh(); return except IOLAuthError: pass` | ✓ WIRED | L159-165 confirman el patrón; `if _refresh_token:` gate + `except IOLAuthError: pass` fallback presente |
| `aio.py::_ensure_token` | `aio.py::_refresh_unlocked` | `await _refresh_unlocked()` dentro de `_token_lock` | ✓ WIRED | L175-180 dentro del `async with _token_lock:` block; solo llama `await _refresh_unlocked()` |
| `test_client.py::test_refresh_token_success_path` | `iol_client.client._refresh_token` | `monkeypatch.setattr(iol_client.client, '_refresh_token', ...)` | ✓ WIRED | L149 confirma el setattr; L170 afirma el resultado post-call |
| `test_async_client.py::test_async_refresh_token_success_path` | `iol_client.aio._refresh_token` | `monkeypatch.setattr(aio, '_refresh_token', ...)` | ✓ WIRED | L119 confirma; L140 afirma post-call |
| `main_iol.py::probe_refresh_token` | `iol_client.client._refresh_token + _token + _token_expires_at` | atributo directo read/write | ✓ WIRED | Líneas ~1261-1390 leen `_refresh_token`, fuerzan `_token_expires_at = 0.0`, verifican cambios post-call |
| `main_iol.py` | `verification.findings.append_finding` | `from verification.findings import append_finding` | ✓ WIRED | 48 call sites en el driver; import presente |

### Data-Flow Trace (Level 4)

Los artifacts de este plan no renderizan UI — son módulos Python (cliente HTTP), scripts de verificación, y tests mockeados. El data-flow relevante es el flujo OAuth token → cache → request.

| Artifact | Data Variable | Source | Produce datos reales | Status |
|----------|---------------|--------|----------------------|--------|
| `client.py::_ensure_token` | `_refresh_token` → `_token` | `_refresh()` / `login()` via `POST /token` | Sí (refresh response / password grant) | ✓ FLOWING |
| `aio.py::_ensure_token` | `_refresh_token` → `_token` | `_refresh_unlocked()` / `_login_unlocked()` via `await client.post(...)` | Sí | ✓ FLOWING |
| Test regression tests | mock responses via `httpx_mock.add_response` | `match_content=b"..."` discriminación FIFO | Datos mockeados intencionalmente (unit tests) | ✓ FLOWING (mocked by design) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_refresh_token` existe y es None al iniciar | `python -c "import iol_client.client as m; assert m._refresh_token is None"` | exit 0 | ✓ PASS |
| `_refresh_unlocked` existe y no re-adquiere lock | `python -c "import iol_client.aio as m; import inspect; src = inspect.getsource(m._refresh_unlocked); assert '_request(' not in src and '_ensure_token(' not in src"` | exit 0 | ✓ PASS |
| Suite IOL completa verde | `uv run pytest packages/iol-client -q` | 31 passed | ✓ PASS |
| mypy strict IOL | `uv run mypy packages/iol-client` | Success: no issues found in 7 source files | ✓ PASS |
| ruff IOL | `uv run ruff check packages/iol-client && ruff format --check packages/iol-client` | All checks passed | ✓ PASS |
| Suite completa (regresiones) | `uv run pytest -q` | 198 passed, 1 deselected | ✓ PASS |
| main_iol.py invariantes de seguridad | `time.sleep` ausente, `asyncio.run` count=1, `exc.args[0]` ausente | Verificado | ✓ PASS |
| Pitfall 2: get-instruments-by-type schema tiene `titulos` en top-level | `python -c "import json; d=json.load(open(...)); assert 'titulos' in d['schema']"` | ✓ | ✓ PASS |

### Probe Execution

El plan no tiene `scripts/*/tests/probe-*.sh`. El driver de verificación en vivo (`main_iol.py`) se ejecutó manualmente como parte del Task 3.2 (checkpoint humano aprobado).

| Probe | Comando | Resultado | Status |
|-------|---------|-----------|--------|
| `main_iol.py` (15 probes) | `uv run --package iol-client python main_iol.py` | PASS=13 FAIL=0 SKIPPED=1 FINDING=1; exit 0 | PASS |

SKIPPED = `probe_auth_401` (opt-in deliberado; ver Human Verification). FINDING = F-01 SHAPE OPEN (asunción incorrecta del driver sobre `simbolo` en `get_quote`, no bug del cliente — documentado en el findings file como OPEN per decision del checkpoint humano).

### Requirements Coverage

| Requirement | Plan fuente | Descripción | Status | Evidencia |
|-------------|-------------|-------------|--------|-----------|
| IOL-01 | 03-02, 03-03 | Auth flow (login + lazy-auth) sync y async | ✓ SATISFIED | `probe_login_sync` PASS + `probe_login_async` PASS; `_token` y `_refresh_token` cacheados tras live run |
| IOL-02 | 03-02, 03-03 | Happy-path sweep de 4 endpoints, sync y async | ✓ SATISFIED | Probes 3-10 PASS; 3 invariantes URL exacta + formato de fecha lockados en `Verified live (Phase 3)` |
| IOL-03 | 03-02, 03-03 | Mapa campo→tipo observado vs asunciones del caller | ✓ SATISFIED | `probe_field_type_map` corrió; F-01 documenta la discrepancia (asunción del driver); `schema_of` schemas committeados |
| IOL-04 | 03-02, 03-03 | Clave envelope `["titulos"]`, formato de fecha, campos numéricos como JSON number | ✓ SATISFIED | `get-instruments-by-type.json` schema contiene `"titulos"` en top-level; `test_get_quote_url_exacta_con_query_string` lockea `isinstance(ultimoPrecio, int\|float)`; `test_get_historical_quotes_url_dia_gt_12` lockea formato con day>12 |
| IOL-05 | 03-02, 03-03 | Mapeo del error 401 con credenciales inválidas | NEEDS HUMAN | `probe_auth_401` implementado con try/finally + opt-in `VERIFY_IOL_BAD_CREDS=1` + single-shot; NO ejecutado en vivo (Pitfall 9 lockout risk). El mecanismo existe y es correcto pero la verificación in-vivo queda pendiente |
| IOL-06 | 03-02, 03-03 | Paridad estructural sync↔async para cada endpoint | ✓ SATISFIED | `probe_parity_sync_async` PASS `4 endpoints, drift=0, skipped=0` |
| IOL-07 | 03-01 | `grant_type=refresh_token` con fallback a password grant en client.py y aio.py, con tests | ✓ SATISFIED | `_refresh()` + `_refresh_unlocked()` implementados; 8 regression tests (sync + async); CR-01/02/03 corregidos in-cycle; `probe_refresh_token` PASS "token rotated" en live run |

**IOL-05 nota:** El requirement dice "Verificar el mapeo del error 401 en vivo con credenciales inválidas vía `configure()`". El probe está correctamente implementado (fix CR-03 cambió la implementación a mutación directa de `_password` en lugar de `configure()` para preservar `_refresh_token`). La verificación in-vivo queda como tarea humana explícita.

### Anti-Patterns Found

| File | Línea | Pattern | Severidad | Impacto |
|------|-------|---------|-----------|---------|
| `.planning/verification/iol-client-findings.md` | 1 | Header con `iol-client-client` (doble `-client`) | ℹ️ Info | Cosmético; documentado en `03-03-SUMMARY.md` decisions como no-bloqueante; candidato para corrección futura |

No se encontraron marcadores `TBD`, `FIXME`, `XXX` sin issue de seguimiento en los archivos modificados por esta fase. No se detectaron stubs (return null / return {} / return []) ni placeholders en las implementaciones nuevas.

Los 8 WARNINGs y 4 Infos del code review (03-REVIEW.md) fueron explícitamente diferidos por decisión del usuario. No son blockeantes para el goal de la fase; están documentados en `03-REVIEW-FIX.md`.

### Human Verification Required

#### 1. Verificación in-vivo de IOL-05: path 401 con credenciales inválidas

**Test:** Correr el driver con el flag opt-in:
```
VERIFY_IOL_BAD_CREDS=1 uv run --package iol-client python main_iol.py
```
Solo una vez, sin re-intentos (Pitfall 9 — policy de lockout de IOL desconocida; riesgo al disparar múltiples intentos fallidos).

**Expected:**
- `PROBE auth_401: FINDING F-NN (EXPECTED)` en stdout
- El findings file recibe un nuevo finding con `Class: AUTH | Status: EXPECTED | status_code=401`
- Driver exit 0
- Cuenta de tokens fallidos no alcanza lockout threshold (industry: 3-10; IOL no documentado)

**Why human:** Pitfall 9 (CONCERNS.md) prohíbe ejecución automática de probes que disparan intentos de autenticación fallidos contra cuentas reales. El mecanismo está completamente implementado y correcto (fix CR-03 con mutación directa de `_password` + try/finally restore). Solo requiere supervisión humana para el run único.

### Gaps Summary

No hay gaps bloqueantes. El goal de la fase está logrado: el fix IOL-07 está implementado en ambas superficies con regression tests; la verificación in-vivo confirma que el token rota vía refresh path; los 4 endpoints están cubiertos; el mapa campo→tipo y los 4 schema snapshots están committeados.

IOL-05 es el único ítem que requiere acción humana. Su implementación en el código es correcta y completa. La verificación del comportamiento real (server retorna 401 con creds inválidas → `IOLAuthError.status_code == 401`) requiere el run opt-in deliberado.

---

_Verified: 2026-06-06T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
