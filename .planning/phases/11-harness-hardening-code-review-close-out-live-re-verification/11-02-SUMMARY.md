---
phase: 11-harness-hardening-code-review-close-out-live-re-verification
plan: 02
subsystem: code-review-closeout
tags:
  - code-review
  - closeout
  - thread-safety
  - bare-except
  - ruff
  - housekeeping
  - CR-01
  - CR-02
  - CR-04
  - CR-06
  - CR-07
  - CR-08
requires:
  - "Phase 5 v1.0 code review report (CR-01..08; CR-03 + CR-05 ya cerrados en Phases 7/9)"
  - "Plan 11-01 (findings.py append-only + idempotent_by_title) — landed en base"
  - "Existing 4 baseline `<pkg>-findings.md` files (Phase 5 close-out commit `4d48e07`)"
provides:
  - "CR-07 cerrado: main_higyrus.py `_capture_*_query_string` thread-safe via `threading.Lock` (sync) + `asyncio.Lock` (async) wrapper alrededor de la mutación read-modify-write de `httpx.Client.event_hooks`"
  - "CR-06 cerrado: 27 bare `except Exception` sites narrowed (10 matriz + 17 higyrus) a `_RESIDUAL_PROBE_EXCEPTIONS` tuple module-level"
  - "CR-04 cerrado: `_first_dict` 3-branch distinguishability con `fname=` kwarg; emit SHAPE finding en wrong_type case"
  - "CR-02 cerrado: `probe_login_sync` retorna `ProbeResult.status='FINDING'` (was `'FAIL'`) en ambos sitios (AuthenticationError + residual)"
  - "CR-01 cerrado: `probe_schema_snapshot` `sample_params` placeholders alineados al estilo `{name}` que ya usan los path templates"
  - "CR-08 cerrado: `[tool.ruff] extend-exclude` para spike artifacts (108 errores PRE-EXISTENTES eliminados); `ruff check .` exit 0 across full repo"
affects:
  - "main_matriz.py — 10 bare except sites narrowed, _first_dict ampliado con fname=, probe_login_sync FAIL→FINDING, probe_schema_snapshot sample_params aligned"
  - "main_higyrus.py — 17 bare except sites narrowed, _capture_sync/_async_query_string thread-safe con locks"
  - "pyproject.toml — [tool.ruff] extend-exclude para spike artifacts"
  - "verification/ — 5 nuevos archivos de test (15 test cases total)"
tech-stack:
  added:
    - "ninguno (sin nuevas dependencias — stack Python 3.12+ / httpx / pytest preservado)"
  patterns:
    - "Module-level `_RESIDUAL_PROBE_EXCEPTIONS` tuple en ambos drivers para narrowing consistente sin DRY violation per-paquete"
    - "Lock-based thread-safety: `threading.Lock` module-level (sync) + lazy `asyncio.Lock` via helper getter (async) — alternativa a per-request hook injection que requeriría refactor invasivo"
    - "`fname=` opt-in kwarg pattern para backwards-compat en `_first_dict`: callers que no pasan fname obtienen el comportamiento legacy"
    - "Placeholder-everywhere sample_params (CR-01 Option B): `{name}` style en vez de `<NAME>` style; el envelope no leak PII"
    - "AST-walk parametric × N drivers regression test (CR-06 RED): `verification/test_main_drivers_bare_except.py` fails RED on cualquier nuevo bare except"
key-files:
  created:
    - "packages/higyrus-client/tests/test_event_hooks_thread_safety.py — 3 tests CR-07 (concurrent sync, concurrent async, single-thread sanity)"
    - "verification/test_main_drivers_bare_except.py — 2 cases parametric (matriz + higyrus) CR-06 AST guard"
    - "verification/test_main_matriz_first_dict.py — 5 tests CR-04 (ok, no_data, wrong_type list-elem, wrong_type non-list, backwards-compat silent)"
    - "verification/test_main_matriz_login_fail_uniformity.py — 2 tests CR-02 (AuthenticationError + non-Auth path)"
    - "verification/test_main_matriz_schema_snapshot_alignment.py — 3 tests CR-01 (no `<XXX>` literals, account_id symmetry risk probes, account_id query probes)"
    - ".planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-02-SUMMARY.md"
  modified:
    - "main_matriz.py — 10 bare except narrowed (CR-06) + _first_dict 3-branch + fname kwarg (CR-04) + probe_login_sync FAIL→FINDING ×2 sites (CR-02) + probe_schema_snapshot sample_params placeholder-everywhere (CR-01) + 5 call-sites _first_dict en probe_field_type_map updated to pass fname="
    - "main_higyrus.py — `_capture_*_query_string` wrapped en lock (CR-07) + 17 bare except narrowed (CR-06) + 2 import additions (threading) + module-level _RESIDUAL_PROBE_EXCEPTIONS tuple"
    - "pyproject.toml — [tool.ruff] extend-exclude para .claude/skills/spike-findings-market-libs/sources/** + .planning/spikes/** (CR-08)"
requirements_completed: [CR-01, CR-02, CR-04, CR-06, CR-07, CR-08]
decisions:
  - "D-CR-01 honored: per-CR atomic commits (9 commits total — 2 para CR-07 RED+GREEN, 3 para CR-06 RED+GREEN×2, 1 cada para CR-04/CR-02/CR-01 RED+GREEN single, 1 para CR-08 chore)"
  - "D-CR-02 honored: CR-07 + CR-06 = RED-first (TDD); CR-04 + CR-02 + CR-01 = RED+GREEN single-commit con mocked driver-level tests; CR-08 = ruff-only gate (no regression test)"
  - "D-CR-03 honored: orden risk-first CR-07 → CR-06 → CR-04 → CR-02 → CR-01 → CR-08"
  - "CR-07 fix path = lock OR per-request injection: elegido lock (sync + async) por minimal blast radius. Per-request injection via `http_client=` kwarg requería reconstruir transport+auth interno del default Client (descartado per 11-PATTERNS.md:277-285)"
  - "CR-06 narrowing tuple incluye `PrimaryAPIError` en matriz (descubierto durante verificación de CR-02 — ver Deviations Rule 1) — el pre-fix blanket `Exception` capturaba `PrimaryAPIError` no-Auth, el narrowing residual debe preservarlo"
  - "CR-01 Option B (placeholder-everywhere) > Option A (live resolution + redaction): el envelope NUNCA leak PII, todo es `{name}` placeholder. Más simple, más seguro, mismo invariante de simetría"
metrics:
  duration: "~35 min (1 wave parallel executor agent)"
  completed: "2026-06-14"
  task_count: "4 tasks (CR-07 RED+GREEN, CR-06 RED+matriz+higyrus, CR-04+CR-02+CR-01 single each, CR-08 chore)"
  commit_count: "9 atomic commits"
  test_delta: "+15 new test cases (892 baseline → 907 final)"
  bare_except_delta: "29 → 0 (10 matriz + 19 higyrus pre-fix; 0 post-fix)"
  ruff_error_delta: "108 → 0 (all from spike artifacts; CR-08 extend-exclude resolves)"
---

# Phase 11 Plan 02: Code Review Close-out (CR-01/02/04/06/07/08) — Summary

## One-liner

Los 6 code review concerns pendientes (CR-01/02/04/06/07/08) cerrados via 9 atomic commits — `event_hooks` thread-safety con locks (CR-07), 27 bare except sites narrowed (CR-06), `_first_dict` 3-branch (CR-04), `probe_login_sync` FAIL→FINDING uniformity (CR-02), schema snapshot `sample_params` placeholder-everywhere (CR-01), spike artifacts ruff exclusion (CR-08). 15 nuevos test cases. Full ruff/mypy/pytest gates exit 0.

## Per-task atomic commits (D-CR-01 honored — 9 commits)

| Task | Commit | Description |
|------|--------|-------------|
| 1.RED | `c855666` | test(11-02): CR-07 RED — event_hooks thread-safety regression |
| 1.GREEN | `f0ca84d` | fix(11-02): CR-07 — main_higyrus.py event_hooks thread-safety |
| 2.RED | `9e0e611` | test(11-02): CR-06 RED — bare except AST guard for main_*.py drivers |
| 2.GREEN matriz | `2d1b920` | fix(11-02): CR-06 GREEN matriz — narrow 10 bare except sites |
| 2.GREEN higyrus | `0c26bd5` | fix(11-02): CR-06 GREEN higyrus — narrow 17 bare except sites |
| 3.CR-04 | `aa41a83` | fix(11-02): CR-04 — _first_dict distinguishes no_data/wrong_type/ok |
| 3.CR-02 | `bc4acc1` | fix(11-02): CR-02 — probe_login_sync FAIL→FINDING uniformity |
| 3.CR-01 | `383d000` | fix(11-02): CR-01 — probe_schema_snapshot sample_params vs path alignment |
| 4.CR-08 | `023dd29` | chore(11-02): CR-08 + spike artifacts ruff exclusion |

## Test count delta

**Before (post-Plan 11-01 baseline):** 892 passed, 1 deselected.

**After (post-Plan 11-02):** 907 passed, 1 deselected. Delta = **+15 new test cases**.

| File | Tests | Cases | CR closed |
|------|-------|-------|-----------|
| `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` | 3 | 3 | CR-07 |
| `verification/test_main_drivers_bare_except.py` | 1 fn × 2 drivers | 2 | CR-06 |
| `verification/test_main_matriz_first_dict.py` | 5 | 5 | CR-04 |
| `verification/test_main_matriz_login_fail_uniformity.py` | 2 | 2 | CR-02 |
| `verification/test_main_matriz_schema_snapshot_alignment.py` | 3 | 3 | CR-01 |
| **Total** | **14 fns** | **15 cases** | **5 CRs (CR-08 no test)** |

Plan acceptance criterion (`+12 new test cases`): **15 delivered (25% sobre plan)**.

## AST guard evidence (CR-06)

```text
$ uv run pytest verification/test_main_drivers_bare_except.py -q
.. 2 passed in 0.04s
```

Pre-fix counts (asserted by RED commit `9e0e611`):
- `main_matriz.py`: **10** bare `except Exception as exc:` sites
- `main_higyrus.py`: **17** bare `except Exception` sites (post-CR-07 already narrowed 2)

Post-fix counts (asserted by GREEN commits `2d1b920` + `0c26bd5`):
- `main_matriz.py`: **0** bare sites
- `main_higyrus.py`: **0** bare sites
- **Total delta: 27 sites narrowed**

Existing `class_="ERROR-MAP"` finding-emission idiom preserved:
- `grep -c 'class_="ERROR-MAP"' main_matriz.py` = **34**
- `grep -c 'class_="ERROR-MAP"' main_higyrus.py` = **28**

## Ruff baseline shift (CR-08)

**Pre-fix:**
```text
$ uv run ruff check .
Found 108 errors.
[*] 66 fixable with the `--fix` option (32 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

**Post-fix (with `extend-exclude`):**
```text
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
148 files already formatted

$ uv run mypy --strict
Success: no issues found in 50 source files
```

All 108 pre-existing errors came from `.claude/skills/spike-findings-market-libs/sources/**` and `.planning/spikes/**` — production source code (`packages/*/src/`, `verification/`, `main_*.py`) is NOT excluded; ruff continues to enforce style there.

## CR-07 fix path elected: lock (sync + async)

Per `11-PATTERNS.md:277-285`, dos alternativas:

1. **Per-request hook injection** (`http_client=` kwarg pasando un fresh `httpx.Client(event_hooks={"request": [_spy]})`) — preferred per planner, pero requería reconstruir transport+auth+base_url interno del default Client. Radio de impacto excesivo.
2. **Lock-based serialization** — `threading.Lock` module-level (sync) + lazy `asyncio.Lock` via helper getter (async) wrap el read-modify-write de `client.event_hooks`. ~30 LOC delta.

**Elegido: opción 2.** El contrato de regresión (post-concurrent-call hooks byte-idénticos a pre-call) se satisface idénticamente con ambas alternativas. El lock es minimal blast radius y testable de forma robusta.

## Risk-first order honored (D-CR-03)

Phase 11 D-CR-03 prescribe el orden:
```
CR-07 (event_hooks thread-safety)  ← más riesgoso, primero
→ CR-06 (29 bare excepts narrowed)
→ CR-04 (_first_dict 3-branch)
→ CR-02 (FAIL→FINDING uniformity)
→ CR-01 (schema snapshot alignment)
→ CR-08 (ruff format + spike-artifacts exclude)  ← cosmetic, último
```

Commit log evidencia el orden exacto.

## Carry-forward invariants Phase 6-10 (todos GREEN)

| Phase | Invariant | Test | Status |
|-------|-----------|------|--------|
| 6 | Fixture-reaches-production guard | `packages/*/tests/test_*_fixture_*.py` | GREEN |
| 7 | Import-linter contracts | `lint-imports` job + `_core.py` no importa transport | GREEN |
| 8 | Pitfall #4 mutation gate (cross-pkg) | `verification/test_retry_mutation_gate.py` | GREEN |
| 8 | RedactingFilter (no token leak) | `verification/test_logging_no_token_leak.py` | GREEN |
| 8 | Logging root unchanged (B8 lock-in) | `verification/test_logging_root_unchanged.py` | GREEN |
| 9 | BUG-01..04 regression | `packages/matriz-client/tests/test_core.py`, `packages/higyrus-client/tests/test_multi_account.py` | GREEN |
| 10 | Matriz async cross-leak sentinel | `verification/test_sync_async_isolation.py` | GREEN |
| 11-01 | Findings append-only + idempotent_by_title | `verification/test_findings_append_only.py`, `verification/test_findings_dedupe_by_title.py` | GREEN |

**Final aggregate:** `uv run pytest -q` → **907 passed, 1 deselected in 164.29s** (Python 3.12).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CR-06 narrowing regression: `PrimaryAPIError` no atrapado en login residual catch-all**

- **Found during:** Task 3 / CR-02 verification — el test `test_probe_login_sync_returns_FINDING_on_unexpected_exception` falló porque un 500 desde el wire mapea a `PrimaryAPIError` (base class, no `AuthenticationError`), y el catch-all residual narrowed (CR-06 GREEN matriz commit `2d1b920`) NO incluía `PrimaryAPIError` en `_RESIDUAL_PROBE_EXCEPTIONS`. Pre-fix el `except Exception` blanket lo atrapaba; post-narrowing residual se propagaba descontrolado.
- **Issue:** El contrato semántico del catch-all residual era "capturar todo lo que NO sea `AuthenticationError`", incluido `PrimaryAPIError` no-Auth. La narrowing inicial olvidó este caso.
- **Fix:** Agregado `PrimaryAPIError` a `_RESIDUAL_PROBE_EXCEPTIONS` en `main_matriz.py`. Comentario documenta la razón explícita.
- **Files modified:** `main_matriz.py` (tuple definition).
- **Commit:** `bc4acc1` (folded en CR-02 atomic commit; mismo file que CR-02).

### Auth gates

None — Plan 11-02 es enteramente offline (no live HTTP). Live re-verification es Plan 11-03 (LIVE-01 final gate, separado de este plan).

## Known Stubs

None. Plan 11-02 es un close-out de code review concerns: todos los fixes son completos, no se introduce ningún componente con datos placeholder o wiring incompleto.

## Threat Flags

None — los 6 fixes son refactors de safety internos de los drivers de verificación. No se introducen:
- nuevos endpoints / network surface
- nuevos auth paths
- nuevos file-access patterns
- nuevos schema changes en trust boundaries

El threat register del plan (`T-11-07..T-11-12 + T-11-SC`) cubre todos los riesgos identificados; cada `mitigate` disposition tiene su test correspondiente GREEN.

## Self-Check: PASSED

### Files created (exist)
- `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` — FOUND
- `verification/test_main_drivers_bare_except.py` — FOUND
- `verification/test_main_matriz_first_dict.py` — FOUND
- `verification/test_main_matriz_login_fail_uniformity.py` — FOUND
- `verification/test_main_matriz_schema_snapshot_alignment.py` — FOUND
- `.planning/phases/11-.../11-02-SUMMARY.md` — FOUND (este archivo)

### Commits exist in branch
- `c855666` (CR-07 RED) — FOUND
- `f0ca84d` (CR-07 GREEN) — FOUND
- `9e0e611` (CR-06 RED) — FOUND
- `2d1b920` (CR-06 GREEN matriz) — FOUND
- `0c26bd5` (CR-06 GREEN higyrus) — FOUND
- `aa41a83` (CR-04 RED+GREEN) — FOUND
- `bc4acc1` (CR-02 RED+GREEN) — FOUND
- `383d000` (CR-01 RED+GREEN) — FOUND
- `023dd29` (CR-08 chore) — FOUND

### Acceptance criteria met
- AST guard test `verification/test_main_drivers_bare_except.py` PASSES for both `main_matriz.py` AND `main_higyrus.py` (0 bare sites each) — PASS
- `verification/test_main_matriz_first_dict.py` has 5 tests; all GREEN — PASS
- `verification/test_main_matriz_login_fail_uniformity.py` has 2 tests; all GREEN — PASS
- `verification/test_main_matriz_schema_snapshot_alignment.py` has 3 tests; all GREEN — PASS
- `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` has 3 tests; all GREEN — PASS
- `grep -c 'ProbeResult("login_sync", "FAIL"' main_matriz.py` returns 0 — PASS (`grep -c "ProbeResult(.login_sync., .FAIL." main_matriz.py` = 0)
- `grep -c 'ProbeResult("login_sync", "FINDING"' main_matriz.py` returns ≥ 2 — PASS (2 sites flipped)
- `grep -c "fname" main_matriz.py` returns ≥ 6 (signature + 5 call-sites + diagnostic mentions) — PASS (8 occurrences)
- `grep -c "extend-exclude" pyproject.toml` returns 1 — PASS
- `grep -c "spike-findings-market-libs\|\.planning/spikes" pyproject.toml` returns 2 — PASS
- `uv run ruff check .` exits 0 — PASS (was 108 errors)
- `uv run ruff format --check .` exits 0 — PASS
- `uv run mypy --strict` exits 0 — PASS
- `uv run pytest -q` → 907 passed (vs 892 baseline = +15 new tests) — PASS

### NO modifications to STATE.md / ROADMAP.md (parallel executor invariant)
- `git status .planning/STATE.md` — clean (no modifications)
- `git status .planning/ROADMAP.md` — clean (no modifications)
- Orchestrator owns these writes per parallel_execution contract.
