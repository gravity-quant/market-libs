---
phase: 13-cross-package-ergonomics-with-options-max-retries-n
fixed_at: 2026-06-15T00:00:00Z
review_path: .planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/13-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 7
skipped: 1
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-06-15
**Source review:** `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/13-REVIEW.md`
**Iteration:** 1

**Summary:**

- Findings in scope: 8 (3 warnings + 5 info, per `--all` scope flag)
- Fixed: 7
- Skipped (resolved-by-other-fix): 1
- Test baseline: **973 passed, 1 deselected** (Phase 13 baseline was 970 — net +3 from
  regression tests added for WR-01 + WR-03).

## Fixed Issues

### WR-01: Higyrus/iol async `with_options` does not share `_client_lock` with parent

**Files modified:**

- `packages/higyrus-client/src/higyrus_client/_state.py`
- `packages/higyrus-client/src/higyrus_client/aio.py`
- `packages/iol-client/src/iol_client/_state.py`
- `packages/iol-client/src/iol_client/aio.py`
- `packages/higyrus-client/tests/test_async_client.py` (new regression test)
- `packages/iol-client/tests/test_async_client.py` (new regression test)

**Commit:** `4e6c503`

**Applied fix:** Option A from the review — moved `_client_lock` from per-instance
`__slots__` onto the shared `_state` dataclass (`_ClientState.client_lock`), mirroring
the existing `token_lock` pattern. With the lock living on shared state, any
`with_options` view automatically observes the SAME `asyncio.Lock` instance as the
parent (the view shares the entire `_state` reference). The buggy
`view._client_lock = self._client_lock` snapshot-by-value line was deleted; the
`_ensure_client_lock()` helpers in both `higyrus_client.aio` and `iol_client.aio` now
read/write `self._state.client_lock`. Docstrings updated to describe the new shape.
Added one regression test per package
(`test_with_options_async_view_shares_client_lock_with_parent`) that constructs the
view BEFORE the parent materializes its async lock, then asserts both surfaces resolve
to the same `Lock` instance via `_ensure_client_lock()` and `_state.client_lock`.

### WR-02: Matriz `_aensure_token` swap-comment overstates lock guarantee

**Files modified:** `packages/matriz-client/src/matriz_client/aio.py`

**Commit:** `503a108`

**Applied fix:** Comment-only correction. Replaced the stale "swap is safe because it
runs inside the TokenStore lock" assertion (which was false — the swap happens BEFORE
`TokenStore.get_async()` acquires its lock) with an honest "CONCURRENCY NOTE (Phase 13
WR-02 corrected)" that describes the actual semantics: the lazy-init block runs
unprotected, the `is None` check makes the race rare (post-first-call short-circuits
all subsequent arrivals), the swap is symmetric via the `try/finally` so a stray
collision does not corrupt subsequent reads, and the note flags exactly when this
contract would break (if `MatrizRefresh` ever took ownership of the borrowed
`httpx.Client`).

### WR-03: Matriz sync vs async transport diverge on `auth_basic` redaction mechanism

**Files modified:**

- `packages/matriz-client/src/matriz_client/_transport.py`
- `packages/matriz-client/tests/test_transport.py` (new regression test)

**Commit:** `f9605dc`

**Applied fix:** Aligned the sync `RetryTransport` to the async `AsyncRetryTransport`
pattern (defense-in-depth). The sync transport now performs the D-22 inline split at
the emit site for BOTH the WARNING retry record and the ERROR exhausted-retries record
— it sets `extra["auth_basic_user"] = user` + `extra["auth_basic_password"] = "***"`
directly and never sets the raw `extra["auth_basic"]` tuple. The package's
`RedactingFilter` tuple-split branch remains in place as a fallback for any future
call-site that passes the raw tuple, but the transport itself is now symmetric and
leak-resistant to handler attachment order. Added regression test
`test_auth_basic_tuple_split_in_sync_warning_log_record` mirroring the existing async
T8 test from `test_atransport.py`.

### IN-01: Single-line `if X: return` with `noqa`+`fmt: skip` repeated 8 times

**Files modified (9 files — 8 single-line guards + 1 ruff-format cleanup of the
WR-03 file caught by the same pass):**

- `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py`
- `packages/ambito-financiero-client/src/ambito_financiero_client/client.py`
- `packages/higyrus-client/src/higyrus_client/aio.py`
- `packages/higyrus-client/src/higyrus_client/client.py`
- `packages/iol-client/src/iol_client/aio.py`
- `packages/iol-client/src/iol_client/client.py`
- `packages/matriz-client/src/matriz_client/aio.py`
- `packages/matriz-client/src/matriz_client/client.py`
- `packages/matriz-client/src/matriz_client/_transport.py` (drop-by — collapse a
  `ruff format`-only multi-line `if` that the formatter wanted on one line)

**Commit:** `54db09d`

**Applied fix:** Expanded all 8 `if getattr(self, "_is_view", False): return  # noqa:
E701  # fmt: skip` single-liners into the conventional two-line form
(`if getattr(...): \n    return`). Dropped both `noqa: E701` and `# fmt: skip` comments
at every site. Symmetrical now across all 4 packages × 2 surfaces.

### IN-02: Ambito async tests create AsyncClient without `aclose()`

**Files modified:** `packages/ambito-financiero-client/tests/test_async_client.py`

**Commit:** `1deb7e4`

**Applied fix:** Wrapped the 3 named tests
(`test_with_options_chaining_inner_wins_local_async`,
`test_with_options_async_repr_shows_view_prefix`,
`test_with_options_async_invalid_max_retries_raises_value_error`) in `try` / `finally:
await client.aclose()` blocks, matching the existing matriz async test pattern. None
of these tests trigger HTTP-client materialization, so the fix is hygiene-only — but
it removes the `ResourceWarning` exposure under `-W error::ResourceWarning` and keeps
the pattern uniform across packages.

### IN-03: Magic number `9_999_999_999.0` repeated as `token_expires_at` sentinel

**Files modified:**

- `packages/higyrus-client/tests/conftest.py`
- `packages/iol-client/tests/conftest.py`
- `packages/matriz-client/tests/conftest.py`
- `verification/test_with_options.py`

**Commit:** `c148426`

**Applied fix:** Introduced a module-level `NEVER_EXPIRES = 9_999_999_999.0` constant
in each `conftest.py` (with a docstring noting the year ~2286 sentinel) and
`_NEVER_EXPIRES` (file-private) in `verification/test_with_options.py`. Updated the
autouse fixtures and the cross-cutting helpers to reference the constant. Per the
review's "low priority — works correctly today" guidance, legacy in-test usages of
the literal across the broader test suites were left untouched — the constants are
now importable for new test sites and the v1.3 sweep can complete the rollout.

### IN-04: Matriz `_aensure_token` does in-function import of `_get_sync_default`

**Files modified:** `packages/matriz-client/src/matriz_client/aio.py`

**Commit:** `a7ae9fb`

**Applied fix:** Hoisted the `from matriz_client.client import _get_default as
_get_sync_default` import to the module level (next to the existing module-level
`from matriz_client.client import _validate_max_retries` line). Verified no
circular-import hazard exists: `matriz_client.client` does NOT import from
`matriz_client.aio`. The in-function import was a historical defensive pattern with
no concrete rationale anymore. The lazy-init block now reads cleaner and skips the
per-call dict-lookup cost. Updated the in-line comment to flag that the historical
pattern was removed.

## Skipped Issues

### IN-05: `view._client_lock = self._client_lock` comment in iol does not match implementation

**File:** `packages/iol-client/src/iol_client/aio.py:266-269`

**Reason:** Resolved as a side effect of the WR-01 fix. The WR-01 commit (`4e6c503`)
deleted the entire `view._client_lock = self._client_lock` assignment from iol's
`with_options` (the lock now lives on `_state` and is automatically inherited by the
view via `view._state = self._state`). The misleading "Phase 13 D-V3 mirror: share
parent's `_client_lock`" comment was rewritten in the same commit to describe the
new correct semantics ("SHARE — anti-Pitfall 13 (incl. `client_lock`; Phase 13 WR-01
fix moved the lock onto `_state` so view and parent acquire the SAME `asyncio.Lock`
on first `_ensure_http_client`)"). No separate commit needed for IN-05 because the
condition the finding describes no longer exists in the code.

**Original issue:** The comment claimed parent and view share a lock — but with the
old code, they captured by value, not by reference. The fix in WR-01 made the claim
TRUE (lock is shared via `_state`), so the comment update happened at the same site
in the same commit.

## Regression Verification

After all 7 commits, the following gates were re-run from the worktree on top of all
fix commits:

- `uv run ruff check .` → All checks passed!
- `uv run ruff format --check .` → 151 files already formatted
- `uv run mypy packages/*/src` → Success: no issues found in 50 source files
- `uv run pytest -q` → **973 passed, 1 deselected in 923.68s**

The Phase 13 baseline was 970 passing; we now have 973 (net +3 from the new
regression tests added for WR-01 and WR-03). All ROADMAP SC#1..SC#5 invariants
remain green (the CRITICAL `test_with_options_does_not_bypass_mutation_gate_matriz`
merge gate is part of the 973 passing).

## Decisions Preserved

Per `<phase_constraints>`, the following were NOT changed by any fix:

- The mutation gate (`extensions["idempotent"]`) eval order in
  `handle_request`/`handle_async_request` — still FIRST, BEFORE
  `extensions["max_attempts"]`.
- The view shape (`type(self).__new__(type(self))` + share `_state` + override
  `_max_retries` + set `_is_view=True`).
- The matriz `_state.client_max_retries` field semantics (D-T3 + D-T1 isolation).
- `_is_view` membership in `__slots__` on every package's Client/AsyncClient.
- D-D1 (no driver `main_*.py` modifications) — no `main_*.py` was touched.

The WR-01 fix DID remove `_client_lock` from the `__slots__` of higyrus and iol
`AsyncClient` (hoisting it to `_state.client_lock`), but `_is_view` membership is
preserved on all 8 surfaces.

---

_Fixed: 2026-06-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
