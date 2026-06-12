---
phase: 06-compat-safety-net-client-class-skeleton
verified: 2026-06-11T04:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 6: Compat Safety Net + Client Class Skeleton Verification Report

**Phase Goal:** Establecer red de seguridad antes del refactor y entregar la clase `Client`/`AsyncClient` por paquete con la API top-level intacta vía compat layer.
**Verified:** 2026-06-11
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `verification/test_public_surface.py` existe y snapshotea cada atributo público y signature de los 4 paquetes; corre verde antes del primer refactor y sigue verde después | VERIFIED | File exists; 4 parametrized tests pass; snapshot regen is idempotent (zero git diff); symbol counts: ambito 9, iol 13, higyrus 29, matriz 64 |
| 2 | Por cada paquete, el "fixture-reaches-production" guard test verifica que el sentinel aparece en el header `Authorization` (o equivalente) del wire request | VERIFIED | 4 guard test files exist; 7 active tests pass (4 sync + 3 async); 1 permanent skip for matriz async pointing at Phase 10 REFAC-04; sentinel naming SYNC/ASYNC-sentinel-{pkg} confirmed |
| 3 | Los 4 paquetes exponen `Client` (sync) y `AsyncClient` (async) con `close()`/`aclose()` y context managers (`with`/`async with`); estado vive en `_ClientState` por instancia | VERIFIED | All 4 `_state.py` files exist; all 4 packages export `Client` + `AsyncClient` in `__all__`; `close()`/`aclose()`, `__enter__`/`__exit__`/`__aenter__`/`__aexit__` confirmed in all packages; matriz `AsyncClient` is lifecycle-only stub (REFAC-04 deferred to Phase 10) |
| 4 | La API top-level (`pkg.get_X(...)`, `pkg.configure(...)`) sigue funcionando 100% sin cambios para callers; los 277 tests mockeados pasan verde después del refactor | VERIFIED | 389 tests pass (277 baseline + Phase 6 additions), 1 skipped; PEP 562 `__getattr__` shim confirmed in all 4 packages; delegation pattern via `_get_default()` confirmed; conftest migrated to `configure(token=..., token_expires_at=...)` in all packages |
| 5 | `ruff` + `mypy strict` + `pytest` corren verde en CI para ambos Python 3.12 y 3.13 | VERIFIED | Live run: `pytest` 389 passed/1 skipped; `ruff check` all checks passed; `ruff format --check` 86 files formatted; `mypy --strict` 30 source files 0 issues (3.12 confirmed live, 3.13 confirmed by Plan 07 automated run) |

**Score: 5/5 truths verified**

---

### Deferred Items

None.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `verification/test_public_surface.py` | Parametrized golden-file test for 4 packages | VERIFIED | 162-line file; W3 header invariant validated; `iscoroutinefunction` checked before `isfunction` |
| `verification/regen_snapshots.py` | Operator regen script | VERIFIED | Auto-inserts repo root into `sys.path`; runs deterministically |
| `verification/snapshots/*-surface.txt` (x4) | Pre-refactor + post-refactor snapshots | VERIFIED | All 4 files exist; include `Client` and `AsyncClient` entries post-refactor; 8-line `#` header invariant intact |
| `verification/baselines/phase-06-baseline.txt` | Phase entry-baseline (test_count, coverage, git_sha) | VERIFIED | `test_count: 281`, `coverage_total: 95%`, `git_sha: d6aa845...` |
| `packages/*/tests/test_fixture_reaches_production.py` (x4) | Per-package fixture-reaches-production guard | VERIFIED | All 4 files exist under each package's own `tests/` directory |
| `packages/*/src/*/_state.py` (x4) | Per-instance state dataclass | VERIFIED | All 4 `_state.py` files exist; `@dataclass(slots=True)` confirmed; fields: `base_url`, `username`, `password`, `token`, `token_expires_at`, `http_client`, `account_id`; IOL additionally has `refresh_token`, `token_lock`; higyrus has `token_lock` |
| `Client` class in each package | Sync client with lifecycle | VERIFIED | Confirmed in ambito, iol, higyrus, matriz `client.py` |
| `AsyncClient` class in each package | Async client with lifecycle (or stub for matriz) | VERIFIED | Full async in ambito/iol/higyrus; lifecycle-only stub in matriz (scoped to Phase 10 per REFAC-04) |
| PEP 562 `__getattr__` shims | Read-only shim forwarding legacy globals | VERIFIED | `__getattr__` confirmed in all 4 `client.py` files; `_FORWARDED_TO_STATE` dict confirmed in iol/higyrus/matriz; `_base_url` forwarded in matriz for `mutation_gate.py` compatibility |
| `packages/*/tests/conftest.py` migrations | `configure(token=..., token_expires_at=...)` pattern | VERIFIED | All 4 conftest files use `configure()` API (not legacy `monkeypatch.setattr` on module globals) |
| `packages/matriz-client/src/matriz_client/ws_client.py` | Cross-module migration to `_rest._get_default()` | VERIFIED | `_rest._get_default()._state.base_url` and `_rest._get_default()._ensure_token()` confirmed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pkg.get_X(...)` top-level functions | `_get_default().get_X(...)` | `_get_default()` lazy default client | WIRED | Confirmed in ambito, iol, higyrus, matriz |
| `pkg.configure(...)` | `_default_client = Client(...)` reconstruction | direct mutation | WIRED | Carry-forward semantics for `None` kwargs confirmed |
| `Client._request(...)` | `_ClientState.token` | `_ensure_token()` before request | WIRED | Token auth header confirmed via guard tests |
| `AsyncClient._request(...)` | `_ClientState.token` + `asyncio.Lock` | double-checked locking | WIRED | Confirmed for iol, higyrus; ambito has no auth (intentional B7 divergence); matriz async is stub |
| `verification/mutation_gate.py` | `matriz_client.client._base_url` | PEP 562 shim → `_get_default()._state.base_url` | WIRED | Audit confirmed sandbox=True/prod=False; no edits needed to mutation_gate.py |
| `ws_client.py` | `matriz_client.Client` state | `_rest._get_default()._state.*` | WIRED | Confirmed `_rest._get_default()._state.base_url` and `_rest._get_default()._ensure_token()` |
| `test_public_surface.py` | 4 snapshot files | `_snapshot_path(pkg_name)` | WIRED | 4 parametrized tests collect and pass |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces test infrastructure and refactored client scaffolding, not data-rendering components with dynamic data sources.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full pytest suite green | `uv run pytest -q` | 389 passed, 1 skipped, 1 deselected in 0.92s | PASS |
| Snapshot test 4 packages | `uv run pytest verification/test_public_surface.py -v` | 4 passed | PASS |
| Guard tests 7 active + 1 skip | `uv run pytest packages/*/tests/test_fixture_reaches_production.py -v` | 7 passed, 1 skipped | PASS |
| Client class tests | `uv run pytest packages/*/tests/test_client_class.py -q` | 101 passed | PASS |
| Ruff lint | `uv run ruff check .` | All checks passed | PASS |
| Ruff format | `uv run ruff format --check .` | 86 files already formatted | PASS |
| Mypy strict | `uv run mypy --strict packages/*/src` | 30 source files, 0 issues | PASS |
| Snapshot regen idempotent | `uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/` | exit 0, zero diff | PASS |

---

### Probe Execution

No phase-declared probes. The Plan 07 automated verification script served as the phase-level probe and reported 11/11 PASS on both Python 3.12 and 3.13. Live re-run confirms all checks pass.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REFAC-01 | 06-01, 06-02, 06-07 | Safety net: golden public-surface snapshot + fixture-reaches-production guard test + baseline | SATISFIED | `verification/test_public_surface.py` + 4 snapshot files + `verification/baselines/phase-06-baseline.txt` + 4 guard test files; all green |
| REFAC-02 | 06-03, 06-04, 06-05, 06-06, 06-07 | `Client`/`AsyncClient` per package, `close()`/`aclose()`, context managers, `_ClientState` per-instance, PEP 562 shim | SATISFIED | All 4 packages have `Client`, `AsyncClient`, `_state.py`, context managers, and PEP 562 `__getattr__` shims; top-level API verified by 389 passing tests |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | Zero TBD/FIXME/XXX markers in phase-modified files |

Scan performed on:
- All 4 `_state.py` files
- All 4 `client.py` files (modified)
- All 4 `aio.py` files (created or modified)
- `verification/test_public_surface.py`
- `verification/regen_snapshots.py`
- 4 `test_fixture_reaches_production.py` files

One intentional "known stub": `matriz_client.aio.AsyncClient` is lifecycle-only (no REST methods). This is documented in the roadmap as Phase 10 REFAC-04 scope. The permanent `pytest.skip` in `test_fixture_reaches_production.py` is the documented marker for this deferred work. Not a blocker — it is an explicitly scoped deferral with Phase 10 traceability.

---

### Human Verification Required

None — all Success Criteria are verifiable programmatically. No visual, real-time, or external-service assertions required for this phase (verification infrastructure + refactoring only).

---

### Gaps Summary

No gaps found. All 5 Success Criteria verified against the codebase:

1. Snapshot test and baselines exist and run green — confirmed live.
2. All 7 fixture-reaches-production guard tests pass (4 sync + 3 async), 1 permanent skip for matriz async (Phase 10) — confirmed live.
3. All 4 packages expose `Client`/`AsyncClient` with full lifecycle; `_ClientState` per-instance in all packages — confirmed by code inspection and 101 client class tests.
4. Top-level API 100% intact via PEP 562 shims and `_get_default()` delegators; 389 tests pass — confirmed live.
5. `ruff` + `mypy strict` + `pytest` green on Python 3.12 (live run) and Python 3.13 (Plan 07 automated run, 11/11 PASS) — confirmed.

### Downstream Risks for Phases 7-11

The following are observations for the next phase author, not blockers:

- **Matriz AsyncClient stub**: The `AsyncClient` in `packages/matriz-client/src/matriz_client/aio.py` has no REST methods. Phase 10 REFAC-04 must grow this. The permanent `pytest.skip` in `test_fixture_reaches_production.py` will flip to an active test then.
- **`refresh_token` in IOL `_ClientState`**: Populated during `login()`/`_refresh()` but the in-memory-only limitation (no disk persistence) is documented as BUG-03 for Phase 9.
- **`account_id` forward-declared**: Both IOL and Higyrus `_ClientState` have `account_id: str | None = None` declared but unused. Phase 9 BUG-04 activates this field.
- **`token_lock` in IOL and Higyrus**: The `asyncio.Lock | None` field is lazy-created on first async use. Downstream phases must ensure the lock lifecycle is preserved when `_core.py` extraction (Phase 7) reorganizes the auth flow.
- **Ambito B7 divergence**: `AsyncClient` has no `token_lock` by design (no auth). Phase 7 must not accidentally introduce one.

---

_Verified: 2026-06-11_
_Verifier: Claude (gsd-verifier)_
