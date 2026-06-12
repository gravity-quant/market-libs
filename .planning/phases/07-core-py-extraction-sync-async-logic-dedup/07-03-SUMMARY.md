---
phase: 07-core-py-extraction-sync-async-logic-dedup
plan: 03
subsystem: refactor
tags: [phase-07, iol, oauth, refresh-token, refac-03, _core, transport-shell, b8, cr-01]

# Dependency graph
requires:
  - phase: 07-core-py-extraction-sync-async-logic-dedup
    plan: 01
    provides: "iol_client/_core.py placeholder + import-linter contract + cross-leak sentinel test"
provides:
  - "iol_client/_core.py with RequestSpec (iol-shape with data field), raise_for_response, token_is_fresh, build_login_request, parse_login_response, build_refresh_request, parse_refresh_response, and 4 endpoint builder/parser pairs"
  - "iol_client/client.py collapsed to transport shell — login/_refresh/_ensure_token consume _core primitives, endpoint methods are 3-liner shells, D-04 alias preserves B8 identity"
  - "iol_client/aio.py collapsed to async transport shell — mirrors sync shape with await + per-instance asyncio locks; B8 alias imports raise_for_response from _core directly"
  - "iol_client/tests/test_core.py — 37 unit tests covering builders/parsers/auth-flow/CR-01"
affects: ["07-04 (higyrus REFAC-03)", "07-05 (matriz REFAC-03)", "07-06 (CI green gate)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Auth-flow factoring (Pattern 5): build_login_request + parse_login_response as pure functions; transport shell orchestrates HTTP between them"
    - "CR-01 structural preservation: parser returns None in refresh slot when server omits/empties; transport shell writes state.refresh_token only when non-None"
    - "D-04 module-level alias = _core.raise_for_response in both client.py and aio.py — both reference same object → B8 identity invariant preserved"
    - "D-03 transport-shell _request(spec) returns raw httpx.Response; raise lives in parser (resp.read() + raise_for_response)"
    - "Back-compat shim _request(method, path, ...) at module level keeps legacy raise-on-error semantic for tests that depend on it"

key-files:
  created:
    - "packages/iol-client/tests/test_core.py — 37 unit tests"
  modified:
    - "packages/iol-client/src/iol_client/_core.py — placeholder → 318 LOC of pure builders/parsers + auth-flow primitives"
    - "packages/iol-client/src/iol_client/client.py — 522 → 490 LOC; class methods collapsed to 3-liner shells; D-04 alias replaces local _raise_for_response definition"
    - "packages/iol-client/src/iol_client/aio.py — 476 → 457 LOC; async mirror of sync collapse"

key-decisions:
  - "CR-01 conditional refresh-token rotation locked structurally: parser API returns Optional[str] (None when server omits); shell writes only when non-None — closes Phase 6 D-05 in pure-helper form"
  - "Top-level _request shim preserves v1.0 raise-on-error contract for back-compat tests; class method Client._request(spec) follows D-03 raw-Response shape"
  - "B8 identity verified at module level: aio._raise_for_response is client._raise_for_response (both = _core.raise_for_response)"

patterns-established:
  - "Pattern 5 (auth-flow factoring): replicable across higyrus/ámbito; matriz adapts to X-Auth-Token + basic auth fallback"
  - "Pattern 7 (CR-01 conditional rotation): parse_X_response returns tuple ending in Optional[str]; shell only writes state when non-None"

requirements-completed: [REFAC-03]

# Metrics
duration: "~6min"
completed: 2026-06-12
---

# Phase 7 Plan 3: iol `_core.py` extraction with auth-flow primitives Summary

**iol `_core.py` extracts OAuth password-grant + refresh-token auth-flow as pure builders/parsers (with CR-01 conditional rotation preserved structurally) plus 4 endpoint builder/parser pairs; transport shells (client.py + aio.py) collapse to 3-liner endpoint methods, D-04 alias preserves B8 identity.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-06-12T13:30:59Z (approx — Task 1 commit 249e43d)
- **Completed:** 2026-06-12T13:36:42Z (Task 2 commit d27d021)
- **Tasks:** 2
- **Files modified:** 3 (1 created: tests/test_core.py; 3 modified: _core.py, client.py, aio.py)

## Accomplishments

- `iol_client/_core.py` (318 LOC): pure module with iol-shape `RequestSpec` (with `data` field for OAuth form-encoded body), `raise_for_response` (moved from client.py — alias preserves B8), `token_is_fresh` helper, full auth-flow factoring (`build_login_request`, `parse_login_response`, `build_refresh_request`, `parse_refresh_response`), and 4 endpoint builder/parser pairs (`get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type`).
- **CR-01 conditional refresh-token rotation preserved structurally**: `parse_login_response` and `parse_refresh_response` return `None` in the refresh slot when the server omits / empties / non-strings the `refresh_token` key; the transport shell writes `state.refresh_token` only when the returned value is non-None.
- `client.py` + `aio.py` collapsed to transport shells: `login()` / `_refresh()` orchestrate HTTP between `_core` builders and parsers; endpoint methods are 3-liner shells (`spec = _core.build_X(state, ...); resp = self._request(spec); return _core.parse_X(resp)`).
- **B8 identity preserved**: `aio._raise_for_response is client._raise_for_response` == `True` because both are module-level aliases pointing to the SAME object (`_core.raise_for_response`). Existing test `test_aio_imports_raise_for_response_from_client` (`packages/iol-client/tests/test_client_class.py:275`) remains green.
- **D-03 transport shell**: `Client._request(spec: RequestSpec) -> httpx.Response` returns raw response; raise lives in the per-endpoint parser (after `resp.read()` + `raise_for_response(resp)`). The legacy module-level shim `iol_client.client._request(method, path, ...)` retains the v1.0 raise-on-error semantic for back-compat with tests that called it directly.
- **PEP 562 shim Phase 6 untouched**: deny-list of `_user` / `_password` / `_base_url` still active; forwarding of `_token` / `_token_expires_at` / `_refresh_token` / `_client` / `_token_lock` still active.
- 37 new unit tests in `tests/test_core.py` covering RequestSpec shape (with frozen invariant), raise_for_response status mapping, token_is_fresh predicate, auth-flow builders/parsers, **dedicated CR-01 tests** (`test_parse_login_response_refresh_token_none_when_missing`, `_when_empty_string`, `_when_non_string`, plus mirror tests for `parse_refresh_response`), endpoint builders path interpolation, endpoint parsers JSON pass-through.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build `iol_client/_core.py` + `tests/test_core.py`** — `249e43d` (feat)
2. **Task 2: Collapse client.py + aio.py to transport shells** — `d27d021` (refactor)

## Files Created/Modified

- `packages/iol-client/src/iol_client/_core.py` (modified — placeholder → 318 LOC) — pure builders/parsers + auth-flow primitives + `raise_for_response` (B8 source of truth) + `token_is_fresh`
- `packages/iol-client/src/iol_client/client.py` (modified — 522 → 490 LOC) — sync transport shell; D-04 alias `_raise_for_response = _core.raise_for_response`; 3-liner endpoint methods
- `packages/iol-client/src/iol_client/aio.py` (modified — 476 → 457 LOC) — async transport shell; D-04 alias via `from iol_client._core import raise_for_response as _raise_for_response` (mypy strict-friendly explicit re-export)
- `packages/iol-client/tests/test_core.py` (created — 371 LOC, 37 tests) — unit tests for the new `_core` module

## Decisions Made

- **CR-01 lockdown via parser API**: instead of duplicating the "only write if non-None" check inline in every login/refresh path, the parser API itself returns `Optional[str]` in slot 3 and the shell writes conditionally. This makes accidental "always overwrite" regressions a type-level impossibility rather than a code-comment discipline.
- **`parse_refresh_response = parse_login_response`**: the IOL server returns the same payload shape for password-grant and refresh-token responses, so the refresh parser delegates to the login parser. Keeps CR-01 honesty flag in one place.
- **Endpoint builder `state` arg unused → `del state`**: per-endpoint builders for iol don't read state (URL is interpolated from args, no per-state defaulting). The arg stays in the signature for cross-paquete consistency (`build_X(state, ...)`) and `del state` documents the no-op intentionally.

## LOC Drop Analysis

```
LOC drop vs Phase 6 baseline:
- client.py: 522 → 490 (-6.1%)
- aio.py:    476 → 457 (-4.0%)
- _core.py:    0 → 318 (NEW)
- Aggregate client+aio: 998 → 947 (-5.1%)   FAIL (<30% threshold)
```

The plan's success-criterion "≥30% LOC drop on `client.py` + `aio.py` aggregate" is structurally unreachable while preserving every other invariant in the plan. Documented as deviation below.

## Verification

- **B8 identity**: `uv run python -c "from iol_client.aio import _raise_for_response as a; from iol_client.client import _raise_for_response as c; assert a is c"` → PASS
- **CR-01 tests dedicated**: 5 tests verify None-slot behavior on missing / empty-string / non-string `refresh_token` for both `parse_login_response` and `parse_refresh_response`
- **Source assertion `if refresh is not None`**: 2 occurrences in client.py (login + _refresh), 2 in aio.py (_login_unlocked + _refresh_unlocked) → 4 total, plan threshold ≥2 → PASS
- **Cross-leak guard**: `uv run pytest verification/test_sync_async_isolation.py -k iol -x` → 2 passed (SYNC-sentinel-iol_client reaches sync Authorization header; ASYNC-sentinel-iol_client reaches async Authorization header)
- **Public surface snapshot**: `uv run pytest verification/test_public_surface.py -k iol -x` → 1 passed, zero diff (D-16)
- **Phase 6 fixture-reaches-production**: `iol` sync + async sentinels green
- **iol package suite**: 96 tests pass (59 baseline + 37 new test_core.py)
- **Full repo suite**: 436 passed, 2 skipped (matriz async REST stubs)
- **lint-imports**: 4 contracts kept, 0 broken
- **mypy strict**: clean (`packages/iol-client/`)
- **ruff check + format**: clean

## Deviations from Plan

### Acknowledged Deviation

**1. [Rule 4 candidate — scope-vs-invariants tension; documented] LOC drop achieved 5.1%, not ≥30%**
- **Found during:** Task 2 (collapse client.py + aio.py)
- **Issue:** The plan's success-criterion specifies "LOC drop ≥30% on client.py + aio.py aggregate vs Phase 6 baseline (998 LOC)" → threshold ≤699 LOC. After collapsing endpoint method bodies to 3-liner shells and moving `_raise_for_response` to `_core`, the aggregate is 947 LOC (-5.1%).
- **Why the threshold is structurally unreachable:** The LOC count is dominated by load-bearing boilerplate that cannot be removed without violating other plan invariants:
  - Top-level back-compat shims (`configure`, `login`, `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type`, `_request`) — ~117 LOC in client.py + ~145 LOC in aio.py. Removing them would break D-16 (public surface snapshot zero diff) and break `iol_client.__init__` re-exports.
  - PEP 562 read-only shims (`_FORWARDED_TO_STATE`, `_FORWARDED_HTTP_CLIENT`, `_DENIED_LEGACY`, `__getattr__`) — ~46 LOC in client.py + ~52 LOC in aio.py. Removing them would break Phase 6 D-01 invariant and the explicit deny-list T-7-AUTH-LEAK mitigation.
  - Class lifecycle methods preserved per D-23 (`__init__`, `__enter__`/`__exit__` or `__aenter__`/`__aexit__`, `close`/`aclose`, `__repr__`, `__reduce__`, `__deepcopy__`, `_ensure_http_client`, `_ensure_token_lock` in aio) — ~90 LOC combined in both classes.
  - Module-level docstrings + per-function docstrings + multi-line typed signatures — mandated by CONVENTIONS.md.
- **What did contract:** The class method bodies that actually changed (the endpoint methods, `login`, `_refresh`, `_ensure_token`, `_request`) collapsed dramatically. E.g., `Client.login()` went from ~32 LOC body (validate creds + build form + POST + check is_error + parse JSON + validate access_token + write state + handle refresh) to ~16 LOC body (`spec = build; resp = http.request(...); token, expires_at, refresh = parse; write state; if refresh is not None: write refresh; return`). Same applies to `_refresh()`, the 4 endpoint methods, and the async mirrors.
- **Decision:** Documented and accepted — the plan threshold reflects an aspirational metric that doesn't account for the dual back-compat surfaces (module-level v1.0 shims + class-based Phase 6 API) + the PEP 562 read-only forwarding shims + the D-23 lifecycle methods. Every other success criterion of the plan (auth-flow factoring, CR-01 preservation, B8 alias, D-16 zero diff, cross-leak guard, lint-imports clean, full test suite green) is met. The 5.1% drop is real (and >50% drop on the actual endpoint method bodies, which is the part the refactor changes).
- **Files modified:** `packages/iol-client/src/iol_client/client.py`, `packages/iol-client/src/iol_client/aio.py`
- **Verification:** All non-LOC criteria pass per acceptance grep + full test suite green.
- **Committed in:** `d27d021` (Task 2)

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test `test_request_propaga_auth_error` + `test_request_propaga_rate_limit` failed initially**
- **Found during:** Task 2 (collapse) — after replacing `Client._request` body to return raw `httpx.Response` (D-03), 3 legacy tests in `packages/iol-client/tests/test_client.py` and `test_async_client.py` broke because they called `iol_client.client._request("GET", "/api/anything")` and expected `IOLAuthError` / `IOLRateLimitError` to raise on 401 / 429.
- **Issue:** D-03 moved the raise into the parser, but the top-level module shim `iol_client.client._request(method, path, ...)` is a back-compat surface; tests that call it directly (not via an endpoint method) expect the v1.0 raise-on-error contract.
- **Fix:** Added `if resp.is_error: _raise_for_response(resp)` to both the sync and async top-level `_request` shims (NOT to the class method `Client._request(spec)`, which still follows D-03). The class method is the new shape; the module-level shim preserves v1.0 behavior for direct callers.
- **Files modified:** `packages/iol-client/src/iol_client/client.py` (top-level `_request` shim), `packages/iol-client/src/iol_client/aio.py` (top-level async `_request` shim)
- **Verification:** 3 failing tests now pass; full iol suite 96 / 96 green.
- **Committed in:** `d27d021` (Task 2 commit — auto-fix landed before the commit so it's part of the same atomic refactor)

---

**Total deviations:** 1 documented (LOC threshold acknowledged unmet), 1 auto-fixed (Rule 3 — legacy shim raise semantics).
**Impact on plan:** LOC threshold is the only success-criterion not met; every other invariant (B8, CR-01, D-04 alias, D-16 public surface, cross-leak guard, lint-imports, mypy strict, full test suite) is green.

## Issues Encountered

- None beyond the deviation documented above. The CR-01 preservation tests in `test_client.py` (`test_login_preserves_cached_refresh_token_when_server_omits`) pass on the new structurally-locked parser API without modification — strong signal that the structural lock is equivalent to the inline check.

## User Setup Required

None — internal refactor.

## Next Phase Readiness

- iol `_core.py` shape is the auth-rich reference implementation for Plans 7-04 (higyrus) and 7-05 (matriz); both can replicate the per-endpoint builder/parser + auth-flow factoring pattern with their respective adaptations:
  - higyrus: `client_id` tenant header + URL-encoded `/` preservation quirk
  - matriz: `X-Auth-Token` header + HTTP Basic Auth fallback for Risk API + envelope-parsing for `status: ERROR` responses
- `_core.RequestSpec` shape per-paquete: ámbito (minimal), iol (with `data` for OAuth form), higyrus (with `json_body` + `url_pre_encoded`), matriz (with `auth_basic`).
- B8 / D-04 alias pattern is now battle-tested in iol (most complex auth flow); higyrus and matriz adopt the exact same module-level `= _core.raise_for_response` shape.

## Self-Check: PASSED

- `packages/iol-client/src/iol_client/_core.py`: FOUND (318 LOC)
- `packages/iol-client/tests/test_core.py`: FOUND (371 LOC)
- `packages/iol-client/src/iol_client/client.py`: FOUND (modified)
- `packages/iol-client/src/iol_client/aio.py`: FOUND (modified)
- Commit `249e43d`: FOUND
- Commit `d27d021`: FOUND

---
*Phase: 07-core-py-extraction-sync-async-logic-dedup*
*Completed: 2026-06-12*
