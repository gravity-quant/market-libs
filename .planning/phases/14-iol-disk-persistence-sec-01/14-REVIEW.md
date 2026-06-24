---
phase: 14-iol-disk-persistence-sec-01
reviewed: 2026-06-23T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - packages/iol-client/src/iol_client/_token_cache.py
  - packages/iol-client/src/iol_client/_state.py
  - packages/iol-client/src/iol_client/client.py
  - packages/iol-client/src/iol_client/aio.py
  - packages/iol-client/pyproject.toml
  - .pre-commit-config.yaml
  - verification/test_iol_disk_persistence.py
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-06-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the SEC-01 IOL refresh-token disk-persistence implementation: the new
`_token_cache.py` helper, the `token_cache_path` field on `_ClientState`, and the
sync/async wiring in `client.py` / `aio.py`. The core file-I/O helper is well
constructed: `fcntl.flock` locking, atomic write-then-rename via `os.replace`, 0600
perms applied to the tempfile before the rename, and a corrupt-file recovery path
that logs only `type(exc).__name__`. Token-leak-via-logging is genuinely contained,
the concurrent-write integrity gate is satisfied, and the sync/async wiring is a
faithful mirror.

However, there is one BLOCKER: **`configure()` clears the in-memory
`refresh_token` on credential rotation but leaves the stale token on disk and never
clears `token_cache_path`, so the very next `_ensure_token()` reloads the old
user's refresh token from disk** — silently defeating the documented "configure()
resets cached token" invariant and risking cross-identity authentication. The
remaining findings are robustness/consistency concerns around the disk-cache
lifecycle.

## Critical Issues

### CR-01: `configure()` credential rotation is undone by disk reload — stale/cross-identity refresh token re-used

**File:** `packages/iol-client/src/iol_client/client.py:613-619` (and `aio.py:613-617`); reload at `client.py:408-411` / `aio.py:408-411`
**Issue:**
`configure(password=...)` resets in-memory auth state to force re-auth:

```python
if password is not None:
    client._state.password = password
    client._state.token = None
    client._state.refresh_token = None      # cleared in MEMORY only
    client._state.token_expires_at = 0.0
```

It does **not** delete the disk file and does **not** clear/replace
`token_cache_path`. The default client (`_get_default()`) has
`token_cache_path` set to the platformdirs default whenever `CI != "true"`, so disk
persistence is on by default for the module-level API.

On the next request, `_ensure_token()` runs:

```python
if self._state.refresh_token is None and self._state.token_cache_path is not None:
    loaded = _token_cache.load(self._state.token_cache_path)
    if loaded is not None:
        self._state.refresh_token = loaded["refresh_token"]   # reloads OLD token
```

Because `configure()` set `refresh_token = None`, this branch fires and
**repopulates the just-cleared refresh token from disk**, then `_refresh()` is
attempted with it. Concrete failure:

1. User A authenticates → A's refresh token persisted to disk.
2. `iol_client.configure(username="B", password="passB")` → memory cleared, disk
   still holds A's token.
3. Next call → disk reload installs A's refresh token → `_refresh()` succeeds if A's
   token is still valid on the server → **the "user B" session is authenticated as
   user A.**

This nullifies the credential-rotation invariant the function's own docstring
promises ("la invariante legacy 'configure() resetea token cacheado' se preserva")
and is an authentication/identity-confusion hazard. The bug exists symmetrically in
`client.py` and `aio.py`.

**Fix:** On password rotation, delete the disk cache in lockstep with clearing the
in-memory token (mirroring the anti-Pitfall-8 cleanup already done in
`_ensure_token`). For example, in both `configure()` implementations:

```python
if password is not None:
    client._state.password = password
    client._state.token = None
    client._state.refresh_token = None
    client._state.token_expires_at = 0.0
    # SEC-01: rotating credentials must also evict the on-disk refresh token,
    # otherwise _ensure_token() reloads the prior identity's token from disk.
    if client._state.token_cache_path is not None:
        _token_cache.delete(client._state.token_cache_path)
```

(For `aio.configure`, which is synchronous, calling the blocking `_token_cache.delete`
directly is acceptable — `delete` is a single `unlink`. If the executor-thread
convention must be preserved, document why a sync delete in a sync `configure()` is
safe.) Additionally consider letting `configure()` accept `token_cache_path=` so the
disk target can be repointed/disabled at runtime, since today there is no way to turn
disk persistence off for the default client except via the `CI` env var.

## Warnings

### WR-01: On-disk refresh token has no staleness/TTL check — `acquired_at` is recorded but never consulted

**File:** `packages/iol-client/src/iol_client/_token_cache.py:94,105`; consumers `client.py:408-411`, `aio.py:408-411`
**Issue:** `load()` parses and returns `acquired_at`, but neither `_ensure_token`
nor `_aensure_token` ever reads it. A refresh token persisted weeks ago is loaded and
attempted unconditionally. The failure mode is "soft" (a stale token yields a 401,
which triggers the delete-and-password-fallback path), but it means every cold start
after a long idle pays a guaranteed failed-refresh round-trip, and the recorded
`acquired_at` is effectively dead data on the read path. If the intent was to bound
on-disk token age, that check is missing.
**Fix:** Either (a) consult `acquired_at` against a documented max age in
`_ensure_token`/`_aensure_token` and skip/delete tokens older than the bound, or
(b) drop `acquired_at` from the schema if no consumer will ever use it, to avoid
implying a guarantee that does not exist. Document the chosen behavior.

### WR-02: `mkdir(mode=0o700)` does not tighten an already-existing parent directory

**File:** `packages/iol-client/src/iol_client/_token_cache.py:120`
**Issue:** `path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)` only applies
`mode=0o700` when the directory is *created*. If the parent already exists with
looser permissions (e.g. a world-readable `~/.local/share/iol-client` created by an
earlier tool or an operator-supplied `IOL_TOKEN_CACHE_PATH` pointing into a shared
dir), the mode is silently left as-is. The final token file is 0600, so the secret
bytes are protected, but the directory-perm guarantee the docstring asserts
("Parent dir is created 0700") is conditional.
**Fix:** After `mkdir`, explicitly assert/repair the directory mode when persistence
is security-sensitive, or narrow the docstring to "created 0700 *if absent*; not
re-chmod'd if pre-existing." Note that os.chmod on an operator-supplied directory may
be undesirable — at minimum tighten the docstring so the guarantee is not overstated.

### WR-03: `IOL_TOKEN_CACHE_PATH` override bypasses the `CI=true` anti-persistence guard

**File:** `packages/iol-client/src/iol_client/client.py:165-171`, `aio.py:132-138`
**Issue:** `_resolve_default_path()` returns `None` when `CI=true` (anti-Pitfall 10,
no secret persistence on shared CI runners). But the precedence logic resolves the
explicit env override *before* and independently of that guard:

```python
_env_cache_path = os.environ.get("IOL_TOKEN_CACHE_PATH")
if token_cache_path is not None:
    self._state.token_cache_path = token_cache_path
elif _env_cache_path:
    self._state.token_cache_path = Path(_env_cache_path)   # honored even on CI
else:
    self._state.token_cache_path = _token_cache._resolve_default_path()
```

So a CI environment that also has `IOL_TOKEN_CACHE_PATH` set (e.g. inherited from a
developer's `.env`) will persist a refresh token to disk on the CI runner, defeating
the anti-Pitfall-10 protection. This may be intentional ("explicit override wins"),
but it is not documented as a deliberate carve-out and is a plausible secret-leak path
on shared runners.
**Fix:** Decide and document the precedence explicitly. If the `CI` guard should be a
hard floor, gate the env override too:

```python
if os.environ.get("CI") == "true":
    self._state.token_cache_path = None
elif token_cache_path is not None:
    ...
```

If "explicit override always wins" is intended, state that in the module docstring's
`CI` note (which currently implies CI universally disables default-path persistence).

### WR-04: Async cold-start disk read runs outside `token_lock`, allowing redundant reads and a benign refresh-token race

**File:** `packages/iol-client/src/iol_client/aio.py:408-411`
**Issue:** The disk load in `_aensure_token` is deliberately placed outside the
`token_lock` ("per-cold-instance one-time work that does not need the lock"). Under N
concurrent first-callers on a cold instance, all N can observe `refresh_token is None`
and each dispatch a `to_thread` disk read before any sets the field. The reads are
idempotent so the outcome is correct, but it is N redundant thread-pool dispatches and
a write-write race on `self._state.refresh_token` (last writer wins; values are equal
so harmless). It is not a correctness bug today, but it is an undocumented divergence
from the careful double-checked-locking discipline applied everywhere else in this
file.
**Fix:** Either move the disk read inside the existing `token_lock` critical section
(with a re-check of `refresh_token is None`), or add a comment explicitly stating the
race is benign because all readers load identical bytes. Prefer the former for
consistency with the rest of the OAuth flow.

### WR-05: Disk save failure inside `_refresh`/`login` will propagate and abort an otherwise-successful auth

**File:** `packages/iol-client/src/iol_client/client.py:374-379,397-402`; `aio.py:356-362,387-393`
**Issue:** After a successful token refresh, `save()` is called unguarded:

```python
if self._state.token_cache_path is not None and self._state.refresh_token is not None:
    _token_cache.save(self._state.token_cache_path, self._state.refresh_token,
                      acquired_at=time.time())
return token
```

`save()` re-raises any `OSError` (read-only dir, disk full, permission change). That
exception escapes `login()`/`_refresh()` and aborts the call even though the in-memory
auth already succeeded and the access token is usable. A disk-persistence convenience
failure thus turns into a hard auth failure for the caller. (The verification suite
itself exercises a read-only-dir `OSError` from `save` in
`test_disk_persistence_never_logs_token`, confirming `save` does raise.)
**Fix:** Treat disk persistence as best-effort on the write path: wrap the `save()`
call in a try/except that swallows `OSError` and logs a sanitized warning (type name
only, consistent with the `load` recovery path), so a cache-write failure degrades to
"works without persistence" rather than breaking auth. If fail-hard is intended,
document that disk-write failure is a fatal auth error.

## Info

### IN-01: `load()` indexing in verification test lacks a `None` guard

**File:** `verification/test_iol_disk_persistence.py:71`
**Issue:** `assert loaded["refresh_token"] == SENTINEL` indexes `loaded` without first
asserting `loaded is not None`. If `load()` regressed to return `None`, the test would
raise `TypeError: 'NoneType' object is not subscriptable` instead of a clean assertion
failure, obscuring the actual contract being tested. Other tests in the file
(lines 120-123, 173-175) do guard with `assert loaded is not None` first.
**Fix:** Add `assert loaded is not None` before the indexing access, matching the
pattern used by the concurrent-write and 401-cleanup tests.

### IN-02: `save()` catches `BaseException` for cleanup — verify intent vs. masking

**File:** `packages/iol-client/src/iol_client/_token_cache.py:137-139`
**Issue:** `except BaseException: tmp.unlink(missing_ok=True); raise` correctly
unlinks the tempfile on `KeyboardInterrupt`/`SystemExit` as well as ordinary
exceptions, and re-raises — so it does not swallow control-flow exceptions. This is
defensible (guarantees no orphaned tmp file), but `BaseException` catches are worth an
explicit comment so a future reader does not "fix" it to `Exception` and reintroduce
tmp-file leakage on interrupt.
**Fix:** Add a one-line comment explaining the `BaseException` is intentional (cleanup
+ unconditional re-raise, never swallows).

### IN-03: `acquired_at` written by callers via `time.time()` rather than inside `save()`

**File:** `packages/iol-client/src/iol_client/client.py:378`, `aio.py:361`, etc.
**Issue:** Each call site reads `time.time()` and passes `acquired_at=` into `save()`.
The stated rationale ("keeps the save() helper pure/deterministic") is reasonable, but
it duplicates the timestamp-acquisition logic across four call sites and leaves room
for a future call site to forget it or pass an inconsistent value. Combined with
WR-01 (the value is never read), this is low-impact.
**Fix:** If `acquired_at` is retained (see WR-01), consider centralizing the
`time.time()` default inside `save()` with an optional override, or leave as-is and
note the determinism trade-off in the helper docstring.

---

_Reviewed: 2026-06-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
