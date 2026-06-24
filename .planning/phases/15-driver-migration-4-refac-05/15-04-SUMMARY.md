---
phase: 15-driver-migration-4-refac-05
plan: 04
subsystem: verification-drivers
tags: [refac-05, driver-migration, matriz, async, tokenstore, ast-guard, stability-gate, tdd]
requires: ["15-03"]
provides:
  - "main_matriz.py single-client invariant (1 sync Client + 1 async AsyncClient)"
  - "verification/test_main_matriz_uses_single_client_instance.py AST guard"
  - "15-STABILITY-GATE.md (Criterion #2 + #4 final gate)"
affects:
  - main_matriz.py
  - verification/test_main_matriz_uses_single_client_instance.py
tech-stack:
  added: []
  patterns: ["threaded-client-instance", "ainvoke-aclient-threading", "ast-ctor-guard"]
key-files:
  created:
    - verification/test_main_matriz_uses_single_client_instance.py
    - .planning/phases/15-driver-migration-4-refac-05/15-STABILITY-GATE.md
  modified:
    - main_matriz.py
decisions:
  - "Threaded aclient as an explicit param on _ainvoke + each probe_*_async (not a module closure) so the AST gate counts exactly one AsyncClient ctor"
  - "Left the diagnostic sync sweep-probe `primary.client._base_url` reads untouched (out of plan scope; those probes call module-level _matriz_request, not primary.get_X, and construct no client)"
metrics:
  duration: "~22m"
  completed: "2026-06-24"
  tasks: 3
  files_changed: 3
status: complete
---

# Phase 15 Plan 04: matriz Driver Migration + Final Stability Gate Summary

Migrated `main_matriz.py` (the riskiest, TokenStore-sensitive driver) to construct
exactly one sync `Client()` in `main()` and one async `AsyncClient()` in
`_async_main()`, threading both through every probe; then closed the two phase-level
gates — zero finding-title/fid drift across all 4 drivers (Criterion #2) and the
≥907-test baseline (Criterion #4, attested at 988 collected).

## What Was Built

**Task 1 (TDD RED→GREEN):** `verification/test_main_matriz_uses_single_client_instance.py`
— AST walker asserting `1 <= (Client|AsyncClient) ctor Calls <= 2` in `main_matriz.py`,
matching both `ast.Name` (bare) and `ast.Attribute` (module-qualified) ctor spellings
(D-05). Committed RED first (un-migrated driver constructs 0 → fails `01d0efc`), then
GREEN after migration (count == 2). The `<= 2` upper bound is the TokenStore-corruption
mitigation (anti-Pitfall 1): caps the async surface at exactly one `AsyncClient`.

**Task 2 (migration `d1927f5`):**
- Import: `from matriz_client import AsyncClient, Client, PrimaryAPIError` (bare,
  pinned per D-05); removed the now-unused `aio` import.
- `main()`: constructs `client = Client()` once. Sync hostname-safety read
  `primary.client._base_url` → `client._state.base_url`; the `if "remarkets" not in base`
  assert preserved intact. Token read `getattr(primary.client, "_token", None)` →
  `getattr(client._state, "token", None)`.
- 4 sync public-call probes (`probe_login_sync`, `probe_error_bogus_symbol`,
  `probe_error_invalid_account`, `probe_error_malformed_cfi`) gained a `client`
  param; their `primary.login()` / `primary.get_market_data(...)` /
  `primary.get_active_orders(...)` / `primary.get_instruments_by_cfi(...)` calls →
  `client.get_X(...)`; their diagnostic `base_url` reads → `client._state.base_url`.
- `_async_main()`: constructs `aclient = AsyncClient()` ONCE; threads it into all 22
  async probes; `await aio.aclose()` → `await aclient.aclose()`.
- 6 async `_state` reads `aio._get_default()._state.base_url` → `aclient._state.base_url`.
- `_ainvoke` gained an `aclient` first param; every `probe_*_async` passes `aclient`
  and resolves its `aio.get_X` factory to `aclient.get_X`.
- `append_finding(...)` `title=`/`fid=`/`class_=`/`surface=` literals **untouched**
  (D-06) — the residual `aio.*` text in the diff is confined to those finding-title
  string literals.

**Task 3 (stability gate `9067f55`):** `15-STABILITY-GATE.md` records the STATIC
`git diff 71bf201..HEAD` over the 4 committed findings files scoped to
title/fid/probe-name lines → **zero drift**; and the ≥907-test collection attestation
(988 collected).

## Verification Results

| Check | Result |
|-------|--------|
| AST guard `test_main_matriz_uses_single_client_instance` | GREEN (count == 2) |
| All 4 driver AST guards + bare-except walker | 6 passed |
| `ruff check main_matriz.py` | All checks passed |
| `ruff format --check main_matriz.py` | clean (after format pass) |
| `mypy main_matriz.py` (strict, `--package matriz-client`) | Success: no issues |
| matriz package unit suite | 322 passed |
| `_get_default()` CODE sites in driver | 0 |
| `client._state.base_url` occurrences | 11 (hostname read + threaded sync probes) |
| `AsyncClient()` ctor in driver | exactly 1 (TokenStore invariant held) |
| Criterion #2 (static title/fid diff vs 71bf201) | PASS — zero drift |
| Criterion #4 (collection count) | PASS — 988 ≥ 907 |

## Criterion #2 detail (final cross-driver gate)

`git diff 71bf201..HEAD` over the 4 findings files: only `iol-client-findings.md`
differs. Its delta is (a) a Run-Context timestamp (non-deterministic live data, out
of scope per D-07) and (b) an `F-02 OPEN → FIXED` **Status** disposition committed in
Phase 11 (`4d2d23e`), a changed-classification finding (out of scope per D-06). The
`### F-02 -- …` title header and the `fid=F-02` id are byte-identical. **ZERO**
`### F-NN --` title/fid/probe-name header lines changed across all 4 files. No Phase 15
wave altered any finding literal — the migrations changed only client acquisition.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed now-unused `aio` import**
- **Found during:** Task 2 (post-migration `ruff check`).
- **Issue:** After threading `aclient` everywhere, `aio` was no longer referenced in
  code (only in finding-title string literals), so ruff F401 failed.
- **Fix:** Removed `aio` from the `from matriz_client import …` line.
- **Files modified:** main_matriz.py
- **Commit:** d1927f5

### Scope notes (not deviations)

- The diagnostic `primary.client._base_url` reads inside the read-sweep probes
  (`probe_get_segments`, `probe_get_all_instruments`, etc. — lines 357/528/582/702/781/
  1063 and helper sites 240/257/887) were intentionally **left as-is**: those probes
  call the module-level `_matriz_request` (not `primary.get_X`) and construct no
  client, so they are out of the plan's migration scope. They are module-attr reads,
  not `_get_default()` idioms, and do not affect the AST ctor count.

## Operator-Deferred Items

- **Per-package LIVE smoke (D-11, Criterion #4 supplement):** matriz live smoke
  (`uv run --package matriz-client python main_matriz.py` against remarkets) is
  operator-driven and requires `MATRIZ_USERNAME` / `MATRIZ_PASSWORD`. The matriz
  `.env` is **absent** in this execution environment, so the live smoke could not run
  here — recorded as operator-deferred (not a plan failure). The milestone-final live
  re-verification is Phase 17 (LIVE-03). No credentials were logged or committed.

## Threat Mitigations Applied

- **T-15-02 (TokenStore corruption):** exactly one `AsyncClient()` constructed in
  `_async_main`; the `<= 2`-ctor AST gate enforces it.
- **T-15-06 (remarkets→prod switch):** sync hostname read migrated to
  `client._state.base_url` with the `if "remarkets" not in base` assert preserved.
- **T-15-01 (credential disclosure):** no credential literal touched; `.env` stays
  uncommitted; migration changed only client acquisition.

## Self-Check: PASSED

All created files present on disk; all 4 commits (`01d0efc`, `d1927f5`, `9067f55`,
`7d7afd6`) reachable in git history.
