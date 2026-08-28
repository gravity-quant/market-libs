---
phase: 29-decoder-observable
plan: 03
subsystem: api
tags: [decoder, observability, logging, contextvars, redaction, security, dual-sync-async]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    plan: 02
    provides: "The canonical `_decode.py` walker with `STRICT_DECODE` / `DECODE_SCOPE` ContextVars and `open_request_scope()` — defined and tested but never called; this plan is the call site"
  - phase: 29-decoder-observable
    plan: 01
    provides: "29-AGGREGATION-CONTRACT.md locks 6 (scope bound at `_request`), 11 (redaction posture) and 12 (filter recursion bounds)"
provides:
  - "`_ClientState.strict_decode: bool = False` — the higyrus decode-mode carrier, never env-backed, never a module global"
  - "`strict_decode: bool | None = None` on `Client.__init__`, `AsyncClient.__init__`, `client.configure` and `aio.configure` — the four public entry points"
  - "The two bind sites: `Client._request` and `AsyncClient._request` bind `STRICT_DECODE` + a fresh `open_request_scope()` as their first two statements, with no reset"
  - "`_redact_nested` / `_scan_record_dict` — the bounded recursive `record.__dict__` scan, marker-delimited for Plan 09's cross-package hash"
  - "The in-package decoder-path caplog sentinel (T-29-14), relocated from `verification/` where CI never runs it"
affects: [29-04, 29-05, 29-06, 29-07, 29-08, 29-09, 33-driver-runs]

actuals:
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "ContextVar bound at the transport boundary with deliberate `.set()`-without-reset, because the value is read AFTER the binding function returns (the parser decodes the response the method handed back)"
    - "Flag on the shared `_ClientState` rather than the instance `__slots__`, so a `with_options` view inherits the parent's mode and its later mutations"
    - "`None`-sentinel carry-forward on `configure`, so an unrelated `configure(base_url=...)` cannot silently reset a security-relevant opt-in"
    - "Marker-comment-delimited source region (`# --- decode-intactness: generic-scan begin/end ---`) as the unit of cross-package byte-identity, letting a package-specific pre-scan sit legitimately outside the compared region"
    - "Identity-preserving container rebuild: return the ORIGINAL object when no leaf changed, so a fix that adds traversal does not add allocation for the common no-match case"

key-files:
  created: []
  modified:
    - packages/higyrus-client/src/higyrus_client/_state.py
    - packages/higyrus-client/src/higyrus_client/client.py
    - packages/higyrus-client/src/higyrus_client/aio.py
    - packages/higyrus-client/src/higyrus_client/_logging.py
    - packages/higyrus-client/tests/test_decode.py
    - packages/higyrus-client/tests/test_logging.py
    - verification/snapshots/higyrus-client-surface.txt

key-decisions:
  - "`configure(strict_decode=...)` carries forward rather than resetting: higyrus's `configure` builds a NEW `Client` copying the current values, and a security-relevant opt-in that a later `configure(base_url=...)` silently cleared would be Pitfall 5 in a mode flag. This mirrors market-data's `mutating_allowed` sentinel semantics even though the two functions mutate state differently."
  - "The generic scan was extracted into a module-level `_scan_record_dict(record)` so that the constants, the recursive helper and the loop form ONE contiguous marker-delimited region. A helper left outside the markers would be excluded from Plan 09's hash — which is exactly the code most worth pinning."
  - "The bounded walk returns the caller's original container when nothing beneath it changed, so records whose extras carry no marker keep object identity exactly as before the fix — the traversal costs a comparison, not an allocation."
  - "The caplog sentinel literal deliberately carries NO redaction marker (`s3cr3t-decode-sentinel-9f2c4b`, not `Bearer …`). A marker-bearing sentinel would be rescued by `_redact` and the test would prove something about the filter; a marker-free one proves what lock 11 actually claims — that the RECORD CONTRACT, not the filter, is what keeps wire values out."
  - "An `autouse` pristine-context fixture was added to `test_decode.py` (see Deviations): the no-reset discipline is correct in production but makes the sync test context inherit the last request's scope, which silently deduped a later assertion into emptiness purely on test order."

patterns-established:
  - "When a ContextVar carries a mode read after the setter returns, the absence of a reset is a documented invariant with its rationale in a source comment — not an omission a future reader should 'fix' with try/finally"
  - "Test isolation for `.set()`-without-reset carriers belongs in an autouse fixture that snapshots and restores both vars, not in per-test cleanup"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "Strict mode is reachable from all four public entry points and lands on the shared `_ClientState`"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "packages/higyrus-client/tests/test_decode.py::test_strict_mode_from_constructor, ::test_strict_mode_from_configure"
        status: pass
      - kind: command
        ref: "inspect.signature() reports `strict_decode` in Client, AsyncClient, configure and aio.configure — all four True"
        status: pass
    human_judgment: false
  - id: D2
    description: "The mode travels by ContextVar bound at the top of both `_request` implementations, from `_ClientState` — never an env var, never a module global"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_bound_by_request, test_async_request_binds_mode"
        status: pass
      - kind: command
        ref: "grep -c '_decode\\.STRICT_DECODE\\.set' → 1 in client.py and 1 in aio.py; same counts for `_decode.open_request_scope`; `strict_decode` declared as a plain `bool = False` with no `default_factory`"
        status: pass
    human_judgment: false
  - id: D3
    description: "The bind carries no reset — after `_request` returns, the mode and scope are still bound, because the decode has not happened yet"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_no_reset_after_request (also asserts the scope is the SAME object, so every model from one response dedupes together — lock 6)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A `with_options` view inherits the parent's mode and its later mutations"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_view_inherits (asserts `view._state is parent._state`, that a parent mutation is visible through the view, and that `strict_decode` is in neither class's `__slots__`)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The module-level `_request` shim binds the mode through delegation — evidence that binding on the method alone covers every path"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_strict_mode_bound_by_module_shim"
        status: pass
    human_judgment: false
  - id: D6
    description: "Each response gets a fresh decode scope — a process-lifetime scope is rejected (lock 6)"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_request_binds_a_fresh_scope_per_response (two requests, two distinct scope objects)"
        status: pass
    human_judgment: false
  - id: D7
    description: "The RedactingFilter scan reaches string leaves nested inside dict, list and tuple values, preserving container type and dict keys"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_nested_container_string_leaf_redacted, test_nested_list_and_tuple_leaves_redacted, test_untouched_containers_keep_object_identity"
        status: pass
    human_judgment: false
  - id: D8
    description: "The traversal is bounded at depth 4 and 64 entries per container (lock 12), both as named constants with the rationale in source"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_recursion_depth_bounded (asserts `_MAX_SCAN_DEPTH == 4`, that a container at the bound is untouched and a leaf within it is redacted), test_wide_container_skipped (asserts `_MAX_SCAN_ENTRIES == 64` and both sides of the boundary)"
        status: pass
    human_judgment: false
  - id: D9
    description: "A credential literal on the decoder path reaches none of `getMessage()`, `str(record.args)` or `record.__dict__`"
    requirement: "DEC-01"
    verification:
      - kind: test
        ref: "test_decode_sentinel_never_leaks_credential (binds a fresh scope first so the dedupe set cannot make the assertion vacuous; asserts >= 2 divergence records were actually emitted)"
        status: pass
    human_judgment: true
    rationale: "The test proves one marker-free sentinel does not appear on the three surfaces for one divergent payload. It cannot prove that no future emitter branch introduces a value-carrying key — that guarantee is structural (lock 1's six keys are all type names, paths, package names, model names or kinds) and needs a human reading `_emit` to confirm. The sentinel is the tripwire, not the proof."
  - id: D10
    description: "matriz's ordering invariant survives the fix: any package-specific pre-scan stays ABOVE the generic scan"
    requirement: "DEC-01"
    verification:
      - kind: manual
        ref: "The generic scan is now a single `_scan_record_dict(record)` call at the END of `filter()`, with a comment stating the pre-scan MUST stay above it. matriz's `_logging.py` is untouched by this plan (Wave 4 transcribes the region)."
        status: pass
    human_judgment: true
    rationale: "higyrus has no package-specific pre-scan block, so the invariant is asserted here only by construction and comment. The real test is Wave 4's matriz transcription, where the `auth_basic` split must sit above the marker region and the hashed region must still match."

# Metrics
duration: 9min
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 03: Wiring the decoder into the client Summary

**The tracer slice closes: `Client(strict_decode=True)` now reaches the walker through a ContextVar bound at the top of both `_request` implementations, a divergence in observable mode is a structured record, and a marker-free credential literal provably reaches none of the three `LogRecord` surfaces on the decoder path.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-19T02:18:56Z
- **Completed:** 2026-08-19T02:28:17Z
- **Tasks:** 2
- **Files modified:** 0 created, 7 modified

## Accomplishments

- **The mode is reachable, and only from where it should be.** `strict_decode` is a plain `bool = False` on `_ClientState` — no `field(default_factory=_env_...)` sits next to it despite every credential field around it using one, because an environment-variable carrier is explicitly forbidden (T-29-16). It is settable from exactly four typed entry points: `Client(...)`, `AsyncClient(...)`, `configure(...)` and `aio.configure(...)`.
- **The carrier crosses a boundary no parameter could.** The decoder is called from ~30 pure parser functions that hold no reference to a `Client`; threading a `strict` argument through them would break the preserved `from_api(payload)` contract. `_request` binds `_decode.STRICT_DECODE.set(self._state.strict_decode)` plus a fresh `open_request_scope()` as its first two statements, and each asyncio task carries its own context copy, so interleaved tasks in different modes never see each other's bind.
- **The absence of a reset is now a documented invariant, not an omission.** `_request` returns the `httpx.Response`; the decode happens afterwards, in the parser. A `try`/`finally` reset would unbind the mode before the decoder ever reads it. Both `_request` docstrings and both bind-site comments say so, and `test_no_reset_after_request` pins it — including the stronger claim that the scope object after return is the SAME one, which is what makes lock 6's collapse fire across every element of a top-level `list[Model]` parse.
- **A view cannot silently run a different mode than its parent (T-29-17).** The flag lives on the shared `_ClientState`, never in `Client.__slots__`; `test_strict_mode_view_inherits` asserts `view._state is parent._state`, that a parent mutation is visible through the view, and that the name is absent from both classes' `__slots__`.
- **The module-level `_request` shim needs no bind of its own, and that is proven rather than assumed.** `test_strict_mode_bound_by_module_shim` drives the legacy shim against a mocked transport and asserts the mode is bound afterwards — evidence that the shim delegates *through* the `Client` method, not around it.
- **The filter now reaches leaves it never could.** The `record.__dict__` scan inspected only values that were already strings, so a marker-bearing string nested inside a dict, list or tuple value shipped intact to every downstream handler (T-29-13). The replacement walks containers within lock 12's bounds, rebuilds them with redacted leaves, preserves dict keys and container type, and returns the caller's original object when nothing beneath it changed.
- **The bounds are real and both sides of each boundary are tested.** Depth 4 and 64 entries, as named constants with the latency-amplifier / CPU-sink rationale in a source comment (T-29-15). `test_wide_container_skipped` asserts a 65-entry container is skipped AND a 64-entry one is still walked; `test_recursion_depth_bounded` asserts a container at the bound is untouched AND a leaf inside the bound is redacted.
- **The security claim is now made by the artifact that can actually carry it.** The module docstring states plainly that marker anchoring is deliberately unchanged, that no change to this filter makes a wire value safe to log, and that the record contract (lock 1 + lock 11) is the primary control. The sentinel test uses a credential literal with **no** redaction marker, so its absence is evidence about the record schema rather than about `_redact`.

## Task Commits

1. **Task 1: `strict_decode` carrier — state field, four entry points, two bind sites** — `357b686` (feat)
2. **Task 2: `RedactingFilter` two-part fix + decoder-path caplog sentinel** — `3c27864` (fix)

## Files Created/Modified

- `packages/higyrus-client/src/higyrus_client/_state.py` — `strict_decode: bool = False` in the class body (the dataclass is `slots=True`, so a runtime `setattr` would fail), with a comment in the register of market-data's `mutating_allowed` block citing D-03 and D-14 and the docstring's field list extended.
- `packages/higyrus-client/src/higyrus_client/client.py` — `strict_decode` kwarg on `Client.__init__` and `configure`; the two-statement bind at the top of `_request` with its no-reset rationale; `_decode` added to the package import.
- `packages/higyrus-client/src/higyrus_client/aio.py` — the verbatim async mirror of all three changes, plus a note that each asyncio task carries its own ContextVar copy.
- `packages/higyrus-client/src/higyrus_client/_logging.py` — `_MAX_SCAN_DEPTH = 4`, `_MAX_SCAN_ENTRIES = 64`, `_redact_nested` and `_scan_record_dict`, all inside one contiguous `# --- decode-intactness: generic-scan begin/end ---` region; `filter()` now ends with a single `_scan_record_dict(record)` call carrying the pre-scan ordering comment. `_REDACTION_MARKERS` and the `_redact` pass chain are byte-unchanged.
- `packages/higyrus-client/tests/test_decode.py` (+208 lines) — 8 new tests plus the autouse pristine-context fixture.
- `packages/higyrus-client/tests/test_logging.py` (+152 lines, **0 deleted** — append-only, verified with `git diff --numstat`) — 6 new tests.
- `verification/snapshots/higyrus-client-surface.txt` — regenerated by `verification/regen_snapshots.py`; four signature lines changed (`Client`, `AsyncClient`, `configure`, and the async `configure` via its own module). The other three package snapshots regenerated byte-identically.

## Decisions Made

- **`configure(strict_decode=...)` carries forward.** higyrus's `configure` replaces the default client with a NEW `Client` copying current values, unlike market-data's `configure` which mutates state in place. Carrying the flag forward gives the same observable semantics as market-data's `None` sentinel: `configure(base_url=...)` after `configure(strict_decode=True)` does not reset the opt-in. `test_strict_mode_from_configure` asserts exactly that sequence. Note the asymmetry with `token`, which higyrus's `configure` deliberately does NOT carry forward.
- **The generic scan became a module-level function.** The plan asked for a marker-delimited scan region hashed across five copies. Leaving the recursive helper and the two bound constants outside the markers would exclude the most important code from that hash, and a nested `def` inside `filter()` would rebuild a closure on every log record on a hot path. Extracting `_scan_record_dict` makes constants + helper + loop one contiguous region, and `filter()`'s call site keeps matriz's ordering invariant explicit.
- **Identity is preserved when nothing matched.** `_redact_nested` compares rebuilt children by `is` and returns the original container when all are unchanged, so this fix does not turn every logged `extra` container into a fresh allocation.
- **The sentinel carries no redaction marker.** A `Bearer …`-shaped sentinel would be redacted by `_redact` and the test would silently become a filter test. The marker-free literal is the honest form of the lock 11 claim.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cross-test scope leak turned a Plan 02 assertion green-to-empty**

- **Found during:** Task 1, on the first full-package run.
- **Issue:** `test_real_model_missing_float_still_defaults_and_now_reports` (a Plan 02 test, untouched by this plan) started failing with `assert [] == [('.precio', 'missing')]`. Cause: with the bind now live, every `_request` in `test_client.py` leaves a `DECODE_SCOPE` bound in the sync test context. `test_decode.py` runs later in the same context, so a bare `PosicionValuada.from_api(...)` joined the stale scope, whose `(model, field_path, kind)` triple had already been seen — the record was correctly deduped away. The failure was purely a function of test ORDER; the test passed in isolation.
- **Why this is not a design defect:** in production the same discipline is correct and intended. Every request rebinds a fresh scope *before* any decode from that response happens, so a real decode never joins a stale scope. The exposure exists only for a bare `Model.from_api()` issued after a request in the same context — which lock 6 already describes as reusing the bound scope.
- **Fix:** an `autouse` fixture in `test_decode.py` that snapshots both ContextVars, sets a pristine (`False`, `None`) state for the test, and restores on teardown. Its docstring records the whole mechanism so the next reader does not mistake it for boilerplate.
- **Files modified:** `packages/higyrus-client/tests/test_decode.py`
- **Commit:** `357b686`

**2. [Rule 3 - Blocking] `configure` does not carry the token forward, so the shim test could not authenticate**

- **Found during:** Task 1.
- **Issue:** `test_strict_mode_bound_by_module_shim` calls `higyrus_client.configure(strict_decode=True)` and then drives the module-level `_request`. Because `configure` builds a fresh `Client` and passes `token=token` (i.e. `None`) rather than carrying it forward, the new default client had no token and attempted a real login against the mocked transport, raising `HigyrusAuthError: No token in login response`.
- **Fix:** the test re-seeds `token` / `token_expires_at` in the same `configure` call, exactly as `conftest.py` does. No production change — the carry-forward asymmetry between `token` and credentials is pre-existing and deliberate.
- **Files modified:** `packages/higyrus-client/tests/test_decode.py`
- **Commit:** `357b686`

### Additions beyond the plan's test list

Two tests were added beyond the seven the plan enumerated, both cheap and both pinning a lock the plan's list left implicit:

- `test_request_binds_a_fresh_scope_per_response` — lock 6's rejection of a process-lifetime scope, asserted at the `_request` boundary rather than only at `open_request_scope`.
- `test_untouched_containers_keep_object_identity` — pins the identity-preserving rebuild, so a future simplification that always allocates would be caught.

## Issues Encountered

- None beyond the two auto-fixed items above. `ruff format` reflowed the appended test blocks once in each file; both were reformatted before commit and `ruff format --check .` reports 204 files already formatted.

## Verification

- `uv run pytest packages/higyrus-client -q --no-cov` — **207 passed**.
- `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` — **925 passed** (872 pre-existing + 39 from Plan 02 + 14 new here).
- `uv run pytest packages/higyrus-client/tests/test_decode.py -q --no-cov` — 47 passed (39 + 8).
- `uv run pytest packages/higyrus-client/tests/test_logging.py -q --no-cov` — 18 passed (12 + 6).
- `uv run pytest verification/test_public_surface.py verification/test_logging_no_token_leak.py -q --no-cov` — 9 passed.
- `uv run mypy packages/higyrus-client/src` — Success: no issues found in 12 source files.
- `uv run ruff check .` — All checks passed. `uv run ruff format --check .` — 204 files already formatted.
- `uv run lint-imports` — Contracts: 4 kept, 0 broken.
- `grep -c '_decode\.STRICT_DECODE\.set'` — 1 in `client.py`, 1 in `aio.py`. Same counts for `_decode.open_request_scope`. Both are the first two statements of each `_request` body, neither in a `finally`.
- `inspect.signature(...)` — `strict_decode` present in `Client`, `AsyncClient`, `higyrus_client.configure` and `higyrus_client.aio.configure`: four `True`.
- `grep -c 'strict_decode' _state.py` — 2 (declaration + docstring entry); the declaration is a plain `bool = False` with no `default_factory`.
- Marker lines: `decode-intactness: generic-scan begin` ×1 and `... end` ×1 in `_logging.py`.
- `git diff --numstat HEAD -- packages/higyrus-client/tests/test_logging.py` before commit — `152  0` — **0 deleted lines**, append-only confirmed.
- `git diff` on `_logging.py` shows no hunk touching `_REDACTION_MARKERS` or any `_redact` pass; the only lines mentioning `_REDACTION_MARKERS` are the new helper and the removed old loop condition.
- `git diff --diff-filter=D --name-only` on both commits — empty; no files deleted.
- Snapshot regen: `git status --porcelain verification/snapshots/` after `regen_snapshots.py` showed only `higyrus-client-surface.txt`; the other three regenerated byte-identically.

## Prohibitions status

Both plan prohibitions were carried as `flagged-unverified` and are now satisfied:

- *"Divergence records must NEVER contain a wire value — the `RedactingFilter` fix is defense in depth only."* — Satisfied and stated where it matters. The module docstring of `_logging.py` now says explicitly that no change to the filter makes a wire value safe to log and names the record contract as the primary control. `test_decode_sentinel_never_leaks_credential` uses a marker-free literal precisely so the filter cannot be credited for the result.
- *"The strict-decode flag must NEVER be read from an environment variable or stored in a module-level global."* — Satisfied structurally. `strict_decode` is a plain `bool = False` on `_ClientState` (no `_env_strict_decode` factory exists, and `grep` finds no such name), and the only other carrier is the `_decode.STRICT_DECODE` ContextVar, whose per-task copy semantics are the reason it was chosen. No module-level `_strict_decode` global exists in either transport module.

## Known Stubs

None. Every symbol this plan touched is called on a live path: both bind sites run on every request, `_scan_record_dict` runs on every log record, and `strict_decode` is read by the bind. `SILENT_SINK` remains the one deliberately-unreferenced constant in higyrus production code, documented as such in Plan 02 and unchanged here.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access and no schema at a trust boundary. The three boundaries it does touch (consumer → `Client`, `_request` → decoder context, `extra=` → filter) are all enumerated in the plan's own threat register as T-29-13 through T-29-18, and each has a named mitigation and a test above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Wave 4 (Plans 04-07) is unblocked and now has two things to transcribe, not one.** Beyond `_decode.py`, each package needs: the `_ClientState.strict_decode` field, the four `strict_decode` kwargs, the two `_request` binds, and the marker-delimited generic-scan region in `_logging.py`. The per-package deltas remain the package name, the `POLICY` assignment, the `_LOGGER_NAME` literal and the decode exception.
- **Carried forward for matriz (Plan 05/07):** matriz's `filter()` has a D-22 `auth_basic` pre-scan whose comment states it must run BEFORE the generic scan. The transcription must place that block above the `# --- decode-intactness: generic-scan begin ---` marker so the hashed region stays byte-identical. matriz also has no `aio.py`, so it has one bind site rather than two — Plan 05 should say so explicitly rather than let a grep-count criterion fail.
- **Carried forward for Plan 09 (intactness gate):** the region to hash in `_logging.py` is the text strictly between the two marker lines, and the markers themselves appear exactly once per file. The gate should assert both the single-hash property and the marker-count property, since a copy that silently drops a marker would otherwise hash an empty or runaway region.
- **Carried forward for every package's test suite:** the autouse pristine-decode-context fixture is not optional test hygiene once the bind is live. Any package whose test suite drives `_request` and then asserts on divergence records needs it, or assertions will pass and fail on test order.
- **No blockers.**

## Self-Check: PASSED

Modified files verified present on disk: `_state.py`, `client.py`, `aio.py`, `_logging.py`, `tests/test_decode.py`, `tests/test_logging.py`, `verification/snapshots/higyrus-client-surface.txt`. Both task commits verified present in git history: `357b686`, `3c27864`.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*
