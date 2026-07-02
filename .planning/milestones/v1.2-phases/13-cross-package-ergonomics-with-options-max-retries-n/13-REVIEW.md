---
phase: 13-cross-package-ergonomics-with-options-max-retries-n
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - packages/ambito-financiero-client/src/ambito_financiero_client/_atransport.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_transport.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/aio.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/client.py
  - packages/ambito-financiero-client/tests/test_async_client.py
  - packages/ambito-financiero-client/tests/test_client.py
  - packages/ambito-financiero-client/tests/test_client_class.py
  - packages/higyrus-client/src/higyrus_client/_atransport.py
  - packages/higyrus-client/src/higyrus_client/_transport.py
  - packages/higyrus-client/src/higyrus_client/aio.py
  - packages/higyrus-client/src/higyrus_client/client.py
  - packages/higyrus-client/tests/test_async_client.py
  - packages/higyrus-client/tests/test_client.py
  - packages/iol-client/src/iol_client/_atransport.py
  - packages/iol-client/src/iol_client/_transport.py
  - packages/iol-client/src/iol_client/aio.py
  - packages/iol-client/src/iol_client/client.py
  - packages/iol-client/tests/test_async_client.py
  - packages/iol-client/tests/test_client.py
  - packages/matriz-client/src/matriz_client/_atransport.py
  - packages/matriz-client/src/matriz_client/_state.py
  - packages/matriz-client/src/matriz_client/_transport.py
  - packages/matriz-client/src/matriz_client/aio.py
  - packages/matriz-client/src/matriz_client/client.py
  - packages/matriz-client/tests/test_async_client.py
  - packages/matriz-client/tests/test_client.py
  - packages/matriz-client/tests/test_with_options.py
  - verification/test_with_options.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-06-15
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

Phase 13 delivers the cross-package `with_options(max_retries=N)` ergonomic surface across 4 packages × sync/async = 8 surfaces. The implementation is largely consistent and the critical invariants are upheld:

- **Mutation gate (Anti-Pitfall 14)** is preserved: the eval order in every `_transport.py` and `_atransport.py` checks `idempotent` FIRST and `max_attempts` SECOND, so `client.with_options(max_retries=10).new_order(...)` on matriz still emits exactly 1 wire request under 503. Verified by `verification/test_with_options.py::test_with_options_does_not_bypass_mutation_gate_matriz`.
- **Resource sharing (Anti-Pitfall 13)** is preserved: view shares `_state.http_client`, `_state.token`, and (matriz) `_state.token_store`. `view.close()/aclose()/__exit__/__aexit__` short-circuit via the `_is_view` guard.
- **D-T1/D-T3 TokenStore isolation** is correctly threaded — matriz reads `state.client_max_retries` (not `self._max_retries`) in both sync `_ensure_token` and async `_aensure_token`.
- **D-T6 three-site coverage** (login + Risk path + Token path, sync + async) is implemented and tested.
- **Validation** is duplicated 4× per the "no shared internals" constraint; rejects negative ints, floats, and booleans.
- **mypy strict + ruff** are green per the Plan gates (no findings on style/types worth flagging beyond what's below).

The findings below cluster around two themes:

1. **Concurrency contract mismatch** for higyrus/iol async views: `view._client_lock` is captured by value at `with_options(...)` time, not by reference. If the view is constructed BEFORE the parent triggers its first `_ensure_http_client`, parent and view end up with DIFFERENT `asyncio.Lock` instances guarding the SAME shared `_state.http_client`, opening a small race window for duplicate `httpx.AsyncClient` allocation. The docstring at higyrus aio.py:214-219 explicitly claims they share a single lock — implementation contradicts the contract.

2. **Test hygiene** in 3 async tests that construct `AsyncClient` without `await client.aclose()`. These do NOT leak (no http_client materialized) but emit a `ResourceWarning` under `-W error::ResourceWarning` and weaken the read.

3. **Style/quality nits**: 8 instances of single-line `if X: return` with double `noqa`+`fmt: skip` annotations across the 4 packages; documentation drift in matriz `_aensure_token` swap-comment that overstates the lock guarantee.

## Critical Issues

None.

## Warnings

### WR-01: Higyrus/iol async `with_options` does not share `_client_lock` with parent — race on first `_ensure_http_client`

**Classification:** WARNING
**Files:**
- `packages/higyrus-client/src/higyrus_client/aio.py:235`
- `packages/iol-client/src/iol_client/aio.py:269`

**Issue:** Both higyrus's and iol's async `with_options` write `view._client_lock = self._client_lock` — this captures the VALUE of `self._client_lock` at view-construction time, not a reference. Python `__slots__` instance attributes are independent; assigning to `parent._client_lock` later does NOT propagate to `view._client_lock`.

Scenario:
1. `parent = AsyncClient(...)` — `parent._client_lock = None`.
2. `view = parent.with_options(max_retries=5)` — `view._client_lock = None` (snapshot).
3. Concurrent first-callers: coroutine A awaits `parent.get_movimientos(...)` and coroutine B awaits `view.get_movimientos(...)`.
4. Parent's `_ensure_client_lock()` creates `Lock1` and assigns to `parent._client_lock`.
5. View's `_ensure_client_lock()` creates `Lock2` and assigns to `view._client_lock`.
6. Both coroutines acquire DIFFERENT locks → both pass the inner `is httpx.AsyncClient` check on the SHARED `_state.http_client` → both build a new `httpx.AsyncClient` → one wins the final `self._state.http_client = new_client` assignment; the other one's `httpx.AsyncClient` leaks (TCP pool + SSL context not closed).

The higyrus docstring at `aio.py:214-219` explicitly claims:

> The view inherits ``self._client_lock`` from the parent at view-construction time via ``__new__`` (it would be ``None`` if the parent has not yet opened its async client lock). The view's first async call triggers the same double-checked locking through the parent's lock if both are awaited on the same loop.

The second sentence ("through the parent's lock") is false. Each instance has its own `_client_lock` slot and they diverge after view construction.

This is a Phase 13 regression of the existing `_client_lock` race protection — pre-Phase-13, only the parent existed and parent's lock protected its own `_ensure_http_client`. Now views share `_state.http_client` but not the lock that protects it.

Note: ambito and matriz async clients have NO `_client_lock` at all (B7 / Plan 10-02 explicit decisions), so this finding is higyrus + iol only.

**Fix:** Make the view's `_client_lock` slot reference the parent's slot via a holder, or move the lock to `_state` (cross-instance shared). Option A — `_state` migration (preferred, mirrors `_state.token_lock`):

```python
# In _state.py (per package):
@dataclass(slots=True)
class _ClientState:
    ...
    client_lock: asyncio.Lock | None = None  # NEW, lazy

# In aio.py _ensure_client_lock:
def _ensure_client_lock(self) -> asyncio.Lock:
    if self._state.client_lock is None:
        self._state.client_lock = asyncio.Lock()
    return self._state.client_lock

# Remove _client_lock from __slots__ and __init__.
# Remove view._client_lock = self._client_lock from with_options.
```

Option B — keep the slot but make the view ALWAYS materialize the parent's lock at view-construction:

```python
def with_options(self, *, max_retries: int) -> Self:
    _validate_max_retries(max_retries)
    # Materialize parent's lock so the view inherits a non-None Lock,
    # not a None snapshot.
    parent_lock = self._ensure_client_lock()
    view = type(self).__new__(type(self))
    view._state = self._state
    view._max_retries = max_retries
    view._is_view = True
    view._client_lock = parent_lock  # SAME object as parent
    return view
```

Option B has the downside that `with_options` becomes implicitly loop-bound (the lock is created at view construction time, not at first await). Option A is the clean fix.

Also: update the `with_options` docstring at higyrus aio.py:214-219 to match the actual implementation (or to match Option A if applied).

### WR-02: Matriz `_aensure_token` swap-comment overstates lock guarantee

**Classification:** WARNING
**File:** `packages/matriz-client/src/matriz_client/aio.py:358-370`

**Issue:** The comment claims the `_state.http_client` swap during TokenStore lazy-init is protected by `TokenStore.get_async()`'s per-loop asyncio.Lock:

> The swap of ``self._state.http_client`` below is safe because this entire ``if self._state.token_store is None`` lazy-init block executes inside the per-loop asyncio.Lock acquired by ``TokenStore.get_async()`` before ``_aensure_token`` returns.

But reading the code flow: the `if self._state.token_store is None:` check (line 348) and the swap (lines 357-378) happen BEFORE `await self._state.token_store.get_async()` (line 380). The TokenStore lock is acquired only AFTER the store has been built — so the swap is NOT inside the TokenStore's lock. Two concurrent coroutines on the same loop, both hitting `_aensure_token` for the first time on a state instance, could both observe `token_store is None`, both swap `_state.http_client`, both build a TokenStore, and one wins the final assignment.

Phase 13 expands the surface area of this latent race because views share `_state.token_store` — view callers are an additional concurrent-arrival source. The race window is narrow (lazy-init runs at most once per `_state` instance because subsequent calls find `token_store is not None`), but the comment misleads future maintainers about the guarantee.

**Fix:** Either (a) move the swap+build inside the TokenStore lock (preferred but invasive — currently the lock is internal to TokenStore), or (b) correct the comment to honestly describe the actual concurrency contract. Minimum-viable docs fix:

```python
# CONCURRENCY NOTE:
# This lazy-init block runs BEFORE the TokenStore lock is acquired, so
# the swap of self._state.http_client is NOT protected by the TokenStore.
# Race window is narrow — once a TokenStore is built, the `is None` check
# short-circuits all subsequent callers. Concurrent first-arrival
# coroutines on the same loop may both swap+build; the loser's TokenStore
# is GC'd silently. Acceptable today because views share _state.token_store
# (Phase 13 D-T2) and a stray swap collision does not corrupt subsequent
# reads — but if MatrizRefresh ever takes ownership of the http_client it's
# handed, this becomes a real bug.
```

### WR-03: Matriz sync vs async transport diverge on `auth_basic` redaction mechanism

**Classification:** WARNING
**Files:**
- `packages/matriz-client/src/matriz_client/_transport.py:206-208, 229-231`
- `packages/matriz-client/src/matriz_client/_atransport.py:131-139, 160-164`

**Issue:** The sync `RetryTransport` stuffs the raw `auth_basic` tuple into `extra["auth_basic"]` and relies on the `matriz_client` package logger's `RedactingFilter` (D-22) to split + redact the password before the record reaches downstream handlers. The async `AsyncRetryTransport` does the split INLINE at the emit site, setting `extra["auth_basic_user"]` + `extra["auth_basic_password"]="***"` directly — never adding `extra["auth_basic"]`.

Both end up redacted in normal operation, so this is not a leak today. But:
1. If a consumer attaches a handler BEFORE the package's `RedactingFilter` (handler installed at e.g. `logging.getLogger().addHandler(...)` root), the sync path leaks the raw password into that handler and the async does not. The two surfaces should be symmetric.
2. The `RedactingFilter` test coverage exercises the sync split path; the async path silently bypasses it, weakening the guarantee that any future filter rule change (e.g., add a new D-22 field) applies to async too.
3. The sync→async diverge is a dual-surface invariant violation per the project constraints in CLAUDE.md ("cualquier fix de lógica debe espejarse en `client.py` y `aio.py`").

**Fix:** Pick one mechanism and apply uniformly. Recommendation: keep the inline split (async style) and apply to sync too — it's defense-in-depth (the value never leaves the transport unredacted), and it preserves filter independence. Update sync `_transport.py:206-208` and `_transport.py:229-231` to mirror the async block:

```python
if (
    auth_basic is not None
    and isinstance(auth_basic, tuple)
    and len(auth_basic) == 2
):
    user, _password = auth_basic
    if isinstance(user, str):
        extra["auth_basic_user"] = user
        extra["auth_basic_password"] = "***"
```

Then remove the `extra["auth_basic"] = auth_basic` line and check that the matriz `RedactingFilter` test suite still passes (the filter's tuple-split path will become dead code — fine, just document).

## Info

### IN-01: Single-line `if X: return` with `noqa`+`fmt: skip` repeated 8 times — readability cost

**Classification:** INFO
**Files (8 occurrences):**
- `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py:96`
- `packages/ambito-financiero-client/src/ambito_financiero_client/client.py:124`
- `packages/higyrus-client/src/higyrus_client/aio.py:147`
- `packages/higyrus-client/src/higyrus_client/client.py:167`
- `packages/iol-client/src/iol_client/aio.py:144`
- `packages/iol-client/src/iol_client/client.py:181`
- `packages/matriz-client/src/matriz_client/aio.py:214`
- `packages/matriz-client/src/matriz_client/client.py:185`

**Issue:** Each of these is:

```python
if getattr(self, "_is_view", False): return  # noqa: E701  # fmt: skip
```

This collapses a 2-line if onto 1 line, then suppresses both ruff's `E701` (multi-statement-on-one-line) AND the formatter (`# fmt: skip`). The 8 occurrences each cost 2 suppressions + a slightly opaque expression for one saved line. Other than visual compactness, there's no functional benefit.

The double-suppression also creates a "tail of comments" that's easy to corrupt during refactor (e.g., a future edit drops `# fmt: skip` and ruff format expands the line, drifting from the 7 other sites).

**Fix:** Expand to the conventional 2-line form across all 8 sites:

```python
if getattr(self, "_is_view", False):
    return
```

No noqa. No fmt: skip. Symmetrical across packages.

### IN-02: Test `test_with_options_chaining_inner_wins_local_async` (ambito) creates AsyncClient without `aclose()`

**Classification:** INFO
**Files:**
- `packages/ambito-financiero-client/tests/test_async_client.py:133-139`
- `packages/ambito-financiero-client/tests/test_async_client.py:142-147`
- `packages/ambito-financiero-client/tests/test_async_client.py:150-158`

**Issue:** These three async tests construct `aio.AsyncClient()` but never `await client.aclose()`. The first one (`chaining_inner_wins_local_async`) never even triggers `_ensure_http_client`, so no resource is allocated — but pytest's `-W error::ResourceWarning` (or future tighter pytest config) would catch this if the underlying `httpx.AsyncClient` ever did materialize. The pattern is also inconsistent with the matriz async test suite which DOES call `await client.aclose()` at the end of each non-context-managed test (e.g., `test_with_options_async_view_login_request_carries_max_attempts_extension` in `tests/test_with_options.py`).

**Fix:** Add `await client.aclose()` at the end of each (or use `async with aio.AsyncClient() as client:`). Mirror the matriz pattern for consistency:

```python
async def test_with_options_chaining_inner_wins_local_async() -> None:
    client = aio.AsyncClient()
    try:
        view = client.with_options(max_retries=5).with_options(max_retries=10)
        assert view._max_retries == 10
        assert client._max_retries == 2
        assert view._state is client._state
    finally:
        await client.aclose()
```

### IN-03: Magic number `9_999_999_999.0` repeated as `token_expires_at` sentinel across all per-package tests

**Classification:** INFO
**Files (~12 occurrences across):**
- `packages/iol-client/tests/test_client.py`
- `packages/iol-client/tests/test_async_client.py`
- `packages/higyrus-client/tests/test_client.py`
- `packages/higyrus-client/tests/test_async_client.py`
- `packages/matriz-client/tests/test_client.py`
- `packages/matriz-client/tests/test_async_client.py`
- `verification/test_with_options.py:99,108,117`

**Issue:** Each test that pre-seeds a non-expiring token passes `token_expires_at=9_999_999_999.0`. The value is a Unix epoch around the year 2286 — well beyond any test horizon. But it's a bare magic number repeated across the codebase with no symbolic name. Future tightening of `token_is_fresh` semantics (e.g., reject expiry > now + 100 years as suspicious) would silently break all these tests.

**Fix:** Define a module-level test constant (per package, since no shared internals):

```python
# At top of each test_*.py:
_NEVER_EXPIRES = 9_999_999_999.0  # ~year 2286, well beyond any test horizon

# Then in tests:
token_expires_at=_NEVER_EXPIRES,
```

Or move to a conftest.py fixture if the test suite has one. Low priority — works correctly today.

### IN-04: Matriz `_aensure_token` does in-function import of `_get_sync_default`

**Classification:** INFO
**File:** `packages/matriz-client/src/matriz_client/aio.py:353`

**Issue:** Inside `_aensure_token`, the code does:

```python
from matriz_client.client import _get_default as _get_sync_default
```

This is a deliberate lazy import to avoid a circular-import hazard at module load time (`client.py` imports from `aio.py`? Actually no, it doesn't — but the import-cycle concern was clearly historical). The import is also conditional on the lazy-init branch (`if self._state.token_store is None:`), so it runs at most once per state instance. Still, in-function imports cost a couple of dict lookups per call and surprise readers.

**Fix:** Move to module level if no actual circular-import exists at the top of the file:

```python
# At top of matriz_client/aio.py:
from matriz_client.client import _get_default as _get_sync_default
```

If a cycle does exist, leave the in-function import but add a comment explaining the cycle. Low priority — works.

### IN-05: `view._client_lock = self._client_lock` comment in iol does not match implementation surface (Phase 13 D-V3 mirror claim)

**Classification:** INFO
**File:** `packages/iol-client/src/iol_client/aio.py:266-269`

**Issue:** The comment immediately above the assignment claims:

> Phase 13 D-V3 mirror: share parent's _client_lock so the view's first call goes through the SAME asyncio.Lock as the parent (no second lock per view; preserves the per-loop binding).

This is the same incorrect claim as WR-01 — captured by value, not by reference. Same finding, surfaces in iol's comments too. Reading this comment, a maintainer would believe parent and view share a lock — but a future bug could break the per-loop binding when one of them creates a fresh lock.

**Fix:** Update the comment to match the actual semantics (snapshot at construction time; if parent had not yet created a lock, view will create its own on first call). Or apply the WR-01 fix (move lock to `_state`) and delete this assignment + comment entirely.

---

_Reviewed: 2026-06-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
