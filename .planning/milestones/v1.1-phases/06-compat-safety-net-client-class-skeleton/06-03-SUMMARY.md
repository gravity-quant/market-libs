---
phase: 06-compat-safety-net-client-class-skeleton
plan: 03
subsystem: ambito-financiero-client
tags: [refactor, client-class, pep562, async, pitfall-2, b7-no-lock, b8-shared-helper, ambito]

# Dependency graph
requires:
  - phase: 06-compat-safety-net-client-class-skeleton
    provides: Plan 06-02 per-package guard file packages/ambito-financiero-client/tests/test_fixture_reaches_production.py (still green after refactor)
  - phase: 06-compat-safety-net-client-class-skeleton
    provides: Plan 06-01 public-surface snapshot baseline (D-06 invariant; this plan regenerates the ambito snapshot adding Client + AsyncClient)
provides:
  - "ambito_financiero_client.Client (sync) and ambito_financiero_client.AsyncClient (async) classes with per-instance _ClientState"
  - "PEP 562 read-only __getattr__ shim in client.py and aio.py forwarding `_client` only (D-02 ambito row)"
  - "Module-level back-compat delegators: configure(), get_dollar_banco_nacion(), _request, aclose preserved with v1.0 signatures"
  - "B7 divergence pattern locked in: AsyncClient.__slots__ = ('_state',) only — no _client_lock for ambito (resolves checker B7)"
  - "B8 shared helper pattern locked in: aio.py imports _raise_for_response from client.py via explicit re-export alias (resolves checker B8)"
  - "Regenerated verification/snapshots/ambito-financiero-client-surface.txt — adds Client + AsyncClient (D-06 zero-removal invariant preserved)"
  - "Driver migration template: main_ambito_financiero.py reads via `pkg.client._get_default()._state.*` instead of removed legacy globals"
affects:
  - 06-04-PLAN (iol refactor) — pattern template for Client class + PEP 562 shim; B7/B8 do NOT apply to iol (it HAS auth, HAS token refresh race, MUST use asyncio.Lock)
  - 06-05-PLAN (higyrus refactor) — pattern template; same B7/B8 non-applicability as iol
  - 06-06-PLAN (matriz refactor) — pattern template; matriz aio.py is stub-only per Open Q #1
  - Phase 7 (_core.py dedup) — Client/AsyncClient skeleton is the base shape that _core.py will consolidate

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@dataclass(slots=True) _ClientState per package (NOT frozen — http_client lazily mutated)"
    - "field(default_factory=_env_*) for env-var defaults (honors env changes AFTER import; not class-definition time)"
    - "Client/AsyncClient with __slots__=('_state',) for memory + typo safety"
    - "Module-level lazy default singleton: `_default_client: Client | None = None` + `_get_default()` lazy constructor"
    - "configure() carry-forward semantics: kwarg=None preserves prior _default state (RESEARCH.md Open Q #5)"
    - "PEP 562 read-only __getattr__ allow-list pattern: explicit constant `_FORWARDED_HTTP_CLIENT = '_client'`, all other names raise AttributeError"
    - "__reduce__ + __deepcopy__ raise TypeError loudly (D-23) — catches multiprocessing.spawn-style silent corruption"
    - "Redacted __repr__: ambito reduces to base_url + user_agent + client_open boolean (no creds/token to mask)"
    - "Shared stateless helper across sync/async via explicit re-export alias (`from X import y as y`) for mypy --strict implicit_reexport compatibility"
    - "Module-level `_request` thin delegator preserved as a back-compat seam so existing tests and drivers' monkeypatch and direct-call sites keep working without rewrites"

key-files:
  created:
    - "packages/ambito-financiero-client/src/ambito_financiero_client/_state.py"
    - "packages/ambito-financiero-client/tests/test_client_class.py"
  modified:
    - "packages/ambito-financiero-client/src/ambito_financiero_client/client.py"
    - "packages/ambito-financiero-client/src/ambito_financiero_client/aio.py"
    - "packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py"
    - "main_ambito_financiero.py"
    - "verification/snapshots/ambito-financiero-client-surface.txt"

key-decisions:
  - "B7 lock-less AsyncClient locked in: ambito has no auth and no token refresh race, so the asyncio.Lock pattern from PATTERNS.md Section 7 is unnecessary. Documented in _state.py docstring + AsyncClient._ensure_http_client docstring with the T-06-13 acceptable-leak rationale. Future readers immediately see why ambito diverges from iol/higyrus/matriz."
  - "B8 shared _raise_for_response via explicit re-export alias `from ambito_financiero_client.client import _raise_for_response as _raise_for_response` in aio.py — satisfies mypy --strict implicit_reexport while preserving the import path that callers (including the B8 enforcement test) use."
  - "Module-level `_request` delegator preserved post-refactor (NOT removed) so existing test_client.py sites (`ambito.client._request(...)`) and driver call sites keep working. The PEP 562 shim is read-only and cannot intercept calls to a name that needs to be mutable (monkeypatch.setattr) — keeping `_request` as a thin delegator is the simplest seam."
  - "Driver `main_ambito_financiero.py` migrated to read via `pkg.client._get_default()._state.<field>` instead of the removed legacy globals (`_base_url`, `_DEFAULT_USER_AGENT`). This is a Rule 3 (blocking-issue) deviation — the refactor proximately broke the driver and test_driver_invariants.py would fail to import. Minimal diff: 7 sites total (6 sync + 1 async)."
  - "configure() carry-forward (RESEARCH.md Open Q #5): unset kwargs preserve prior `_default_client._state.<field>` instead of resetting. Matches v1.0 semantics where `ambito.configure(base_url='X')` without `user_agent=` left the user_agent untouched."
  - "snapshot regeneration via the existing `verification/regen_snapshots.py` script: only ambito's surface text file changed (D-06 invariant verified by manual diff — 2 entries added, 0 removed)."

patterns-established:
  - "Per-package Client/AsyncClient skeleton with _ClientState dataclass — pattern template that Plans 06-04/05/06 will replicate for iol/higyrus/matriz with their own per-package divergences (token, lock, refresh_token, etc.)."
  - "PEP 562 forwarder allow-list: a single constant naming each forwarded attribute; the __getattr__ body is a small if-chain that ends in `raise AttributeError`. T-06-01 mitigation is structural (no dynamic forwarding)."
  - "Two-task atomic per-package commit: Task 1 lands sync + _state.py + test scaffolding; Task 2 lands async + __init__.py re-export + snapshot regen. Together they constitute the per-package refactor (D-05) even though committed in two pieces."

requirements-completed: [REFAC-02]

# Metrics
duration: ~14 min
completed: 2026-06-11
---

# Phase 06 Plan 03: Ambito Client Class Skeleton + PEP 562 Shim Summary

**First per-package skeleton landed: `ambito_financiero_client.Client` (sync) + `AsyncClient` (async) with per-instance `_ClientState`, PEP 562 read-only `__getattr__` shim, carry-forward `configure()` semantics, redacted `__repr__`, pickle/deepcopy bans, and snapshot regeneration — all 4 ambito test suites + the cross-package public-surface guard + the Plan 06-02 fixture-reaches-production guard pass against the refactored client.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-06-11 (worktree-agent-a0aa6b8c5bb8e6854 wave 1)
- **Tasks:** 2
- **Files created:** 2 (`_state.py`, `tests/test_client_class.py`)
- **Files modified:** 5 (`client.py`, `aio.py`, `__init__.py`, `main_ambito_financiero.py`, `ambito snapshot`)

## Accomplishments

- Smallest blast-radius package fully refactored to the Client/AsyncClient pattern. `_state.py` exposes a `@dataclass(slots=True) _ClientState` with `base_url`, `user_agent`, `http_client`; field defaults are read via `default_factory` so env vars set AFTER import are honored. The dataclass is deliberately mutable (`http_client` is lazy-created and zeroed on close).
- Sync `Client` and async `AsyncClient` ship with `__slots__ = ("_state",)`, `__enter__/__exit__/close()` (idempotent) and `__aenter__/__aexit__/aclose()` (idempotent) plus redacted `__repr__`. `__reduce__` and `__deepcopy__` raise `TypeError` loudly (D-23) so `multiprocessing.spawn` workers fail fast instead of silently corrupting the TCP pool.
- `configure()` (sync + async) implements carry-forward semantics per RESEARCH.md Open Q #5: unset kwargs preserve the prior `_default_client._state.<field>`. Matches v1.0 behavior where `configure(base_url='X')` did NOT clobber `user_agent`.
- PEP 562 read-only `__getattr__` shim per CONTEXT.md D-01/D-02: only `_client` is forwarded (resolves to `_get_default()._state.http_client`); reads of any other legacy global (`_base_url`, `_user_agent`, etc.) raise `AttributeError`. T-06-01 mitigation enforced by `test_pep_562_shim_raises_for_unknown` + async mirror.
- **B7 divergence locked in (resolves checker B7):** `AsyncClient.__slots__` is `("_state",)` only — NO `_client_lock`. Ambito has no auth and no token refresh race, so the `asyncio.Lock` pattern used by iol/higyrus/matriz is unnecessary. `_ensure_http_client` lazy-creates without locking. Acceptable-leak rationale documented in both the dataclass docstring and the method docstring (T-06-13: bounded by process lifetime; low-frequency FX polling).
- **B8 shared helper pattern locked in (resolves checker B8):** `aio.py` imports `_raise_for_response` from `client.py` via the explicit re-export alias `from ambito_financiero_client.client import _raise_for_response as _raise_for_response`. NOT duplicated. The alias form satisfies `mypy --strict`'s `implicit_reexport=False` without breaking the public import path. The B8 invariant is structurally enforced by `test_aio_imports_raise_for_response_from_client` (identity check: `sync_helper is async_helper`).
- `Client` and `AsyncClient` re-exported from the top-level `ambito_financiero_client` namespace (alphabetical insertion in `__all__`). All v1.0 top-level surface (`configure`, `get_dollar_banco_nacion`, exception classes) preserved verbatim.
- Public-surface snapshot `verification/snapshots/ambito-financiero-client-surface.txt` regenerated via `python verification/regen_snapshots.py`: D-06 invariant verified — 2 entries ADDED (`Client`, `AsyncClient`), 0 baseline entries removed.
- Plan 06-02's fixture-reaches-production guard for ambito (sync + async) re-runs green against the refactored client with NO test code changes — the guard already used `configure(base_url=...)` which has no token semantics for ambito.

## Task Commits

Each task was committed atomically:

1. **Task 1: `_state.py` + sync `Client` + PEP 562 sync shim + sync test_client_class.py + driver sync migration** — `07fbcec` (refactor)
2. **Task 2: `AsyncClient` (no lock) + aio PEP 562 shim + `__init__.py` re-exports + AsyncClient test mirrors + snapshot regen + driver async migration** — `78fecfc` (refactor)

## Files Created/Modified

- **Created:** `packages/ambito-financiero-client/src/ambito_financiero_client/_state.py` — `@dataclass(slots=True) _ClientState` + `_env_*` factories + `_DEFAULT_USER_AGENT` constant.
- **Created:** `packages/ambito-financiero-client/tests/test_client_class.py` — 18 tests total (9 sync + 9 async/mirror) covering lifecycle, pickle/deepcopy ban, repr redaction, configure carry-forward, explicit Client isolation (Pitfall #2), the PEP 562 shim allow-list (T-06-01), the B7 no-lock invariant, and the B8 shared-helper invariant.
- **Modified:** `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` — introduced `Client` class with `__slots__`, lifecycle protocol, redacted `__repr__`, pickle/deepcopy bans, instance methods. Module-level `_default_client` + `_get_default()` + `configure()` (with carry-forward) + `_request` thin delegator + `get_dollar_banco_nacion` delegator. PEP 562 `__getattr__` shim forwarding `_client` only.
- **Modified:** `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` — introduced `AsyncClient` class mirroring sync shape, B7 no-lock `_ensure_http_client`, B8 shared `_raise_for_response` via explicit re-export alias. Module-level `_default_async_client` + `_get_default()` + `configure()` + `_request` async delegator + `aclose()` + `get_dollar_banco_nacion()` delegator. PEP 562 `__getattr__` shim forwarding `_client` only.
- **Modified:** `packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py` — added `AsyncClient` and `Client` to the `from ambito_financiero_client.{client,aio} import …` block and to `__all__` (alphabetical).
- **Modified:** `main_ambito_financiero.py` — migrated 6 sync sites (`ambito.client._base_url`, `_DEFAULT_USER_AGENT`) and 1 async site (`aio._base_url`) to the new public-internal accessor `pkg.<surface>._get_default()._state.<field>`. Comment text updated to reflect the post-refactor accessor.
- **Modified:** `verification/snapshots/ambito-financiero-client-surface.txt` — regenerated via `verification/regen_snapshots.py`. Diff: +2 entries (`AsyncClient`, `Client`), 0 removals.

## Decisions Made

See `key-decisions` frontmatter list for the full rationale of each. Briefly:

- **B7 no-lock AsyncClient** — ambito's slots tuple is `("_state",)` only because there's nothing for the lock to serialize.
- **B8 shared `_raise_for_response`** — imported with the explicit re-export alias so mypy --strict is happy and identity is preserved across the sync/async surfaces.
- **Module-level `_request` delegator preserved** — the cleanest way to keep existing `monkeypatch.setattr(ambito.client, "_request", mock)` sites and direct `ambito.client._request("GET", "/x")` calls working without rewriting every test.
- **Driver migration as Rule 3 (Blocking) deviation** — `main_ambito_financiero.py` reads `ambito.client._base_url` and `ambito.client._DEFAULT_USER_AGENT` from the legacy module-level namespace; the refactor removed both. Migration is in-scope because the failing `test_driver_invariants.py` cannot even import the driver without it.
- **configure() carry-forward (Open Q #5)** — adopted the recommended semantic so `configure(base_url='X')` does not clobber a previously-configured `user_agent`.
- **Snapshot regeneration is per-script, not per-file** — `regen_snapshots.py` rewrites all 4 snapshot files; verified that only the ambito file actually changed (the other 3 packages are unchanged in this plan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Driver `main_ambito_financiero.py` reads removed legacy globals**
- **Found during:** Task 1 (sync side) + Task 2 (async side)
- **Issue:** The refactor removes `_base_url`, `_user_agent`, `_DEFAULT_USER_AGENT` from the module-level namespace (per D-02 ambito row: only `_client` is forwarded by the PEP 562 shim). The driver `main_ambito_financiero.py` reads `ambito.client._base_url` at 6 sites and `ambito.client._DEFAULT_USER_AGENT` at 1 site, plus `aio._base_url` at 1 site (sync = 6 + 1 = 7; async = 1). Without these, `test_driver_invariants.py` fails to import the driver and 4 baseline tests fail.
- **Fix:** Migrated each site to read via the new public-internal accessor `pkg.<surface>._get_default()._state.<field>`. The accessor pattern is stable (it's the same access path the PEP 562 shim uses internally for `_client`) and intentionally minimal — no API surface added, just a different read path.
- **Files modified:** `main_ambito_financiero.py` (7 sites + 1 docstring update for the GOOD_UA pointer).
- **Commits:** `07fbcec` (sync migration in Task 1), `78fecfc` (async migration in Task 2).

**2. [Rule 1 - Bug] Module-level `_request` symbol preserved as thin delegator**
- **Found during:** Task 1
- **Issue:** Existing `packages/ambito-financiero-client/tests/test_client.py` calls `ambito.client._request("GET", "/anything")` to drive the raise-for-status path. After the Client class refactor, `_request` no longer exists at module level — it's an instance method on `Client`. The 2 existing tests + the driver's call sites would all break.
- **Fix:** Added module-level `def _request(method, path, **kwargs)` that delegates to `_get_default()._request(...)`. Same for async (`async def _request(...)` → `await _get_default()._request(...)`). This preserves the back-compat seam for both direct calls and `monkeypatch.setattr(ambito.client, "_request", mock)` patterns (PEP 562 forwarding is read-only and cannot intercept `monkeypatch.setattr`, so a real module-level binding is required).
- **Files modified:** `packages/ambito-financiero-client/src/ambito_financiero_client/client.py`, `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py`.
- **Commit:** `07fbcec` (sync) and `78fecfc` (async).

**3. [Rule 1 - Bug] `_raise_for_response` import required explicit re-export alias for mypy --strict**
- **Found during:** Task 2 (mypy run)
- **Issue:** `from ambito_financiero_client.aio import _raise_for_response` was used in `test_client_class.py::test_aio_imports_raise_for_response_from_client`, but mypy --strict reported "ambito_financiero_client.aio does not explicitly export attribute _raise_for_response  [attr-defined]".
- **Fix:** Changed the import in `aio.py` to `from ambito_financiero_client.client import _raise_for_response as _raise_for_response` (the canonical "explicit re-export" syntax). mypy strict's `implicit_reexport=False` is satisfied, the import path stays stable, and the B8 identity check (`sync_helper is async_helper`) still passes.
- **Files modified:** `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py`.
- **Commit:** `78fecfc`.

## Issues Encountered

None blocking. The three Rule 1/3 issues above are typical drift caused by the refactor and are all in-scope per the deviation rules. No checkpoints reached, no architectural decisions required, no package-install gates triggered.

## Verification

Per the plan's verification section:

- `uv run pytest packages/ambito-financiero-client/tests -q` → **95 passed, 1 deselected** (77 baseline + 18 new test_client_class.py tests).
- `uv run pytest verification/test_public_surface.py -q -k ambito` → **1 passed, 3 deselected** (ambito snapshot matches the regenerated golden file; D-06 invariant preserved).
- `uv run pytest packages/ambito-financiero-client/tests/test_fixture_reaches_production.py -q` → **2 passed** (Plan 06-02's per-package guard; no test edits needed because ambito's no-auth guard already used `configure(base_url=...)`).
- `uv run pytest -q` (full suite) → **306 passed, 1 skipped, 1 deselected** (skip = matriz async stub per Plan 06-02). Zero regressions in other packages.
- `uv run ruff check packages/ambito-financiero-client/ main_ambito_financiero.py` → **All checks passed!**
- `uv run ruff format --check .` → **79 files already formatted**.
- `uv run mypy --strict packages/ambito-financiero-client/src` → **Success: no issues found in 6 source files**.
- `uv run mypy --strict packages/ambito-financiero-client/tests` → **Success: no issues found in 15 source files**.
- **B7 spot-check:** `python -c "from ambito_financiero_client.aio import AsyncClient; print(AsyncClient.__slots__)"` → `('_state',)`.
- **B8 spot-check:** `python -c "from ambito_financiero_client.client import _raise_for_response as s; from ambito_financiero_client.aio import _raise_for_response as a; print(s is a)"` → `True`.

## User Setup Required

None — this plan is autonomous code refactor + tests; `user_setup: []` in the plan frontmatter holds.

## Next Phase Readiness

- Plans 06-04 (iol), 06-05 (higyrus), 06-06 (matriz) can now follow the pattern template established here. The key per-package divergences they will need:
  - iol/higyrus/matriz HAVE auth + token refresh — they MUST use `asyncio.Lock` in `_ensure_http_client` and `asyncio.Lock` for token-refresh serialization (B7 does NOT apply to them).
  - iol/higyrus/matriz have multiple module-level globals to forward via the PEP 562 shim (`_token`, `_token_expires_at`, optionally `_refresh_token` for iol — see D-02 per-package matrix in PATTERNS.md Section 8).
  - The driver migration template is established: `pkg.<surface>._get_default()._state.<field>` is the canonical post-refactor accessor for live-driver read sites.
- Phase 7 (`_core.py` dedup) consolidates the duplicated Client/AsyncClient logic across the 4 packages — Plan 06-03 establishes the base shape that Phase 7 will refactor.

## Threat Flags

None. The refactor touches existing surfaces (sync HTTP, async HTTP, public-surface snapshot, driver invariants test) without introducing any new network endpoint, auth path, or trust boundary. The STRIDE entries in the plan's threat model are all addressed:

- T-06-01 (PEP 562 tampering) → mitigated by allow-list + `test_pep_562_shim_raises_for_unknown` + async mirror.
- T-06-02 (`__repr__` info disclosure) → mitigated by redaction; ambito has no credentials so the redaction reduces to the boolean + non-secret fields.
- T-06-03 (conftest migration) → no migration needed for ambito (no token to monkeypatch); the conftest was already minimal.
- T-06-04 (close()/aclose() idempotency) → enforced by `test_close_is_idempotent` + `test_aclose_is_idempotent`.
- T-06-13 (B7 acceptable leak) → accepted with rationale; bounded by process lifetime.

## Self-Check: PASSED

Verified after writing the SUMMARY:

- `packages/ambito-financiero-client/src/ambito_financiero_client/_state.py` → FOUND
- `packages/ambito-financiero-client/tests/test_client_class.py` → FOUND
- `verification/snapshots/ambito-financiero-client-surface.txt` → FOUND (regenerated; +2 entries vs Plan 06-01 baseline)
- Commit `07fbcec` (Task 1) → present in `git log`
- Commit `78fecfc` (Task 2) → present in `git log`
- Full suite green: `uv run pytest -q` → 306 passed, 1 skipped, 1 deselected.

---
*Phase: 06-compat-safety-net-client-class-skeleton*
*Completed: 2026-06-11*
