# Pitfalls Research — v1.2 Architecture + Auth/Ergonomics Carry-forwards

**Domain:** Driver migration × 4 + unasync/codegen single-source + IOL refresh_token disk persistence + cross-package ergonomics (`Client.from_env()`, `client.with_options()`)
**Researched:** 2026-06-14
**Confidence:** HIGH (rooted in v1.1 shipped architecture + RETROSPECTIVE lessons + existing code state of `packages/iol-client/src/iol_client/client.py` + `main_iol.py` INT-01 idiom + v1.1 archived PITFALLS.md)

## Scope

These pitfalls are SPECIFIC to v1.2 features over the already-shipped v1.1 architecture. v1.1 mitigations that are now CODIFIED (PEP 562 shim, `_core.py` extraction, `RetryTransport` mutation gate, per-package `RedactingFilter`, `TokenStore` 3-way concurrency, append-only `verification/findings.py` with BEGIN/END zones, exactly-one 401 re-auth, `Retry-After` cap 60s) are NOT re-derived here — they are assumed as the baseline. See `.planning/research/v1.0-v1.1-archived/PITFALLS.md` for the v1.1 mitigation catalog.

The v1.2 features layered on top:

- 4 driver migrations (`main_ambito` → `main_iol` → `main_higyrus` → `main_matriz`) from PEP-562-shim-mediated module-level calls to direct `Client()`/`AsyncClient()` instance methods. Drivers currently total ~7150 LOC and lean on `_get_default()._state.<attr>` (INT-01 idiom) for state inspection.
- unasync/codegen single-source for `client.py` ↔ `aio.py` parity (eliminate the ~850 LOC duplicated 4×).
- IOL `refresh_token` disk persistence (extends v1.1 BUG-03 lifecycle from in-instance to cross-process).
- `Client.from_env()` classmethod × 4 packages (anthropic/openai SDK ergonomic).
- `client.with_options(max_retries=N)` per-call override × 4 packages.

---

## HIGHEST-RISK PITFALLS (CRITICAL test required before phase merge)

These four are flagged because they can silently produce wrong behavior that does not fail CI:

| # | Pitfall | Risk Class | Why Critical |
|---|---------|-----------|--------------|
| 4 | Codegen breaks B8 identity (`aio._raise_for_response is client._raise_for_response is _core.raise_for_response`) | Silent invariant break | The identity check is enforced by an existing test; a wrong-shape codegen import (`from _core import raise_for_response as _raise_for_response` vs `_raise_for_response = _core.raise_for_response`) fails the test silently if the test is ALSO regenerated. v1.1 D-04 lesson. |
| 5 | Codegen overwrites by-hand edit when operator edits BOTH `client.py` and `aio.py` in a single commit | Lost work + sync/async divergence | The race occurs at the next `pre-commit` regen. Without a marker-comment guard + CI verify-clean check, the by-hand edit silently vanishes. urllib3/elasticsearch-py mainstream practice. |
| 7 | `refresh_token` disk persistence creates new log sites that bypass `RedactingFilter` | Token leak | Disk-write path is a new log site (`writing refresh_token to <path>`); if the path-write logger is not under `iol_client.*` namespace, the v1.1 LOG-02 `RedactingFilter` doesn't filter it. v1.1 LOG-02 + Pitfall 7 lesson carries forward. |
| 14 | `client.with_options(max_retries=10).new_order(...)` retries a mutating call | Duplicate orders | The mutation gate at v1.1 Phase 8 lives in `RetryTransport` via `request.extensions["idempotent"]`. If `with_options(max_retries=10)` creates a NEW RetryTransport that doesn't honor the idempotent extension, the v1.1 Pitfall 4 mitigation is voided. Hard-fail on the first matriz live test. |

The remaining pitfalls below are CRITICAL-adjacent (Pitfalls 1, 9, 15, 17) but have either lower probability or partial existing mitigation. All HIGHEST-RISK pitfalls require a regression test landed in the SAME phase that introduces the feature.

---

## Cluster 1 — Driver Migration Pitfalls (Phases: Driver migration × 4)

### Pitfall 1: State leak between probes — per-instance state defeats the cross-probe singleton expectation

**Symptom:**
Currently each driver script does:
```python
base_url = iol_client.client._get_default()._state.base_url
iol_client.login()                        # cached on _default_client
iol_client.get_quote("GGAL")              # reuses cached token
```
After migration:
```python
client = iol_client.Client()              # ← probe 1 instance
client.login()
client.get_quote("GGAL")

client2 = iol_client.Client()             # ← probe 2 instance (NEW token)
client2.get_quote("AL30")                 # ← triggers ANOTHER password grant
```
Two probes = two password grants = two refresh_tokens issued by IOL. For an OAuth provider, this looks like a credential brute-force pattern. The IOL `probe_auth_401` opt-in test (`VERIFY_IOL_BAD_CREDS=1`) consumes one bad-creds attempt; if probes are per-instance, each refresh_token rotation creates a NEW server-side OAuth session that the next probe's instance loses.

For matriz: even worse. If each probe creates a fresh `Client()`, the `RetryTransport` mutation-gate state is per-instance. A `new_order` probe followed by a `cancel_order` probe (both per-instance) lose the request-id correlation that the operator-readable findings file expects. Worse: if probe N's `new_order` times out and retries on a fresh `Client()` instance because probe N+1 just created one, the v1.1 Pitfall 4 mutation gate doesn't help — the `RetryTransport` is fresh and has no idempotency context.

**Risk:** OAuth provider lockout (IOL), refresh_token churn (IOL), duplicate-order risk (matriz), broken deterministic state for the append-only findings file (all 4 drivers).

**Prevention:**
1. **Driver pattern: ONE `Client()` per driver run, NOT per probe.** Construct at top of `main()`, pass to each probe as `client: iol_client.Client` parameter. Lifecycle managed via `with Client() as c:` context manager (already implemented in v1.1 for all 4 packages).
2. **Lint rule + integration check:** grep CI guard `grep -c "Client()" main_*.py` — must equal 1 per driver (for sync; +1 if async client is also constructed once). Document in commit message; enforce with a `verification/test_drivers_one_client_per_run.py` AST-walker test.
3. **State-inspection idiom migration:** replace 15+ sites of `_get_default()._state.base_url` with `client._state.base_url`. The INT-01 idiom (`_get_default()._state.<attr>`) was a v1.1 transition pattern; v1.2 drivers should use `client._state.<attr>` directly. The PEP 562 shim REMAINS for backwards-compat callers, but drivers (internal repo code) should not depend on it.

**Phase that owns:** Phase 1 (`main_ambito` canary), Phase 2 (`main_iol`), Phase 3 (`main_higyrus`), Phase 4 (`main_matriz`). Phase 1 establishes the pattern; phases 2-4 reuse.

**Test pattern (CRITICAL for matriz Phase 4):**
```python
def test_main_matriz_uses_single_client_instance():
    """v1.2 driver migration: enforce one Client() per main() run."""
    src = (REPO_ROOT / "main_matriz.py").read_text()
    tree = ast.parse(src)
    constructor_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr in {"Client", "AsyncClient"}
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "matriz_client"
    ]
    # 1 sync + 1 async = 2 expected
    assert len(constructor_calls) <= 2, (
        f"{[ast.unparse(c) for c in constructor_calls]} — "
        "Each probe must reuse the single Client() instance constructed in main()"
    )
```

**v1.1 lesson:** INT-01 idiom emerged because `_default_client` is a process-wide singleton; multiple probes share state. v1.2 must NOT regress to per-probe instantiation. Source: `main_iol.py:1289` + RETROSPECTIVE Key Lesson #6 ("INT-01 idiom now documented pattern").

---

### Pitfall 2: Regression invisibility — driver migration regenerates findings file from scratch, losing operator dispositions

**Symptom:**
The LIVE-01 gate at v1.1 Phase 11 compared baseline (`4d48e07`) findings against head findings using the append-only `verification/findings.py` BEGIN/END zone parser. The contract: re-running `main_*.py` preserves the operator-set Classification/Rationale/Regression/Resolution fields.

After driver migration, every probe is now `client.get_X(...)` instead of `iol_client.get_X(...)`. If the migrating developer thinks "the findings file is auto-generated, let me regen from scratch" → operator dispositions are LOST. The next LIVE-01 gate at v1.2 milestone close compares head vs head (no v1.1 baseline preserved) — false PASS.

Even subtler: if a probe function is RENAMED (`probe_login_sync` → `probe_login`), the finding ID changes (content-addressed dedupe by title). Re-running produces a NEW finding with NEW IDs that don't match v1.1's IDs. The append-only parser preserves the OLD findings (because they're still in BEGIN/END zone) but ALSO adds the new ones. Operator-visible noise without API regression.

**Risk:** Loss of v1.1 operator dispositions across milestone boundary; baseline drift undetectable.

**Prevention:**
1. **Driver migration is REFACTOR-ONLY for probe identity:** probe names, finding IDs, and finding titles stay constant. Only the BODY of each probe changes (from `iol_client.get_X(...)` to `client.get_X(...)`).
2. **Diff-guard at phase open:** `git diff baseline..HEAD -- .planning/verification/*-findings.md` must show ZERO changes in BEGIN/END zones for unchanged-classification findings. If a probe MUST be renamed, the new probe constructs a finding with the same `title=` and the parser dedupes by title (existing v1.1 HARN-10 mechanism).
3. **Test the parser explicitly survives the migration:** add `verification/test_findings_survives_driver_migration.py`:
   ```python
   def test_findings_preserve_operator_fields_after_probe_signature_change(tmp_path):
       # Write a finding with operator fields set
       f = tmp_path / "iol-client-findings.md"
       write_initial_finding(f, title="F-02 PROBE_STALE", classification="FIXED",
                              rationale="INT-01 idiom applied at main_iol.py:1289")
       # Simulate driver migration: append the SAME finding-by-title via the new code path
       append_finding(f, title="F-02 PROBE_STALE", body="...probe rewritten using client.method()...")
       # Operator fields MUST survive
       text = f.read_text()
       assert "INT-01 idiom applied at main_iol.py:1289" in text
       assert text.count("F-02 PROBE_STALE") == 1
   ```
4. **Operator-anchor pattern:** at the v1.1 → v1.2 milestone boundary, FREEZE the v1.1 findings markdown as the BASELINE for LIVE-01 v2. Any v1.2 re-run that produces a delta surfaces a new finding (operator triages with the same CONFIRMED/FIXED/EXPECTED/NO-FIX taxonomy).

**Phase that owns:** Phase 1 (`main_ambito` canary establishes the migration pattern; the parser test lands here too). Cross-cutting for phases 2-4.

**v1.1 lesson:** HARN-07/08/09 + LIVE-01 INT-01 fix (`main_iol.py:1289`) — the LIVE-01 gate caught a probe-stale because operator fields were preserved across the iol F-02 fix; if the driver regen had wiped fields, the fix would have looked like a new finding. Source: RETROSPECTIVE What Worked #6 + v1.0-v1.1-archived/PITFALLS.md Pitfall 10.

---

### Pitfall 3: Test fixture drift — 907 mocked tests break when `configure()` is bypassed for `Client(...)`

**Symptom:**
The v1.1 mocked test suite (907 tests) uses two patterns to inject state:
```python
# Pattern A (legacy, top-level shim):
iol_client.configure(token="test-token-XYZ", token_expires_at=time.time() + 999)
quote = iol_client.get_quote("GGAL")  # goes through _default_client

# Pattern B (new, instance-based):
client = iol_client.Client(token="test-token-XYZ", token_expires_at=time.time() + 999)
quote = client.get_quote("GGAL")
```

Pattern A is the existing fixture pattern. Pattern B is what the v1.2 BUG-04 D-08 deferred-to-v1.2 `Client(account_id=X)` proposal will require for higyrus. If the migration adds Pattern B WITHOUT preserving Pattern A's invariants, then:
- `monkeypatch.setattr(iol_client.client, "_token", "X")` (legacy) still goes through PEP 562 shim → forwarded to `_default_client._state.token`. Works.
- `monkeypatch.setattr(iol_client.client._get_default()._state, "token", "X")` (INT-01 idiom) works.
- BUT: `monkeypatch.setattr(iol_client.client, "_password", "X")` raises `AttributeError` (v1.1 `_DENIED_LEGACY` block). If any of the 907 tests does this, it's already failing in v1.1; ok.
- The real risk: tests that construct `Client(account_id=X)` (BUG-04 proposal) assume `_state.account_id` exists. v1.1 Phase 9 D-09 REMOVED `_state.account_id` from higyrus AND iol (cross-leak sentinel). So the `Client(account_id=X)` constructor proposed for v1.2 has NO state field to write to. The migration must either re-add `_state.account_id` OR pass `account_id` per-call only (BUG-04 D-08 per-call only locked v1.1).

**Risk:** 30+ tests silently fail on attribute access; or worse, silently succeed by writing to a transient attribute that no production code reads (v1.1 Pitfall 1 regressed).

**Prevention:**
1. **Test count + assertion count baseline:** record 907 + total assertions BEFORE Phase 1 driver migration. After each phase, count MUST be >= 907. Coverage drop > 1% requires explicit justification (v1.1 archived Pitfall 18 carry-forward).
2. **BUG-04 carry-forward audit:** before any phase adds `Client(account_id=X)` constructor, run `grep -n "_state.account_id" packages/` — must return ZERO results (v1.1 Phase 9 D-09 cleanup). Either re-add the field (with documented rationale why D-09 is reversed) OR enforce per-call only (current locked behavior).
3. **Three-way fixture guard:** add `conftest.py` invariant tests:
   ```python
   def test_fixture_three_paths_all_reach_production(monkeypatch, httpx_mock):
       """Path A: configure(token=). Path B: Client(token=). Path C: PEP 562 shim read."""
       # Path A
       iol_client.configure(token="SENTINEL-A")
       assert iol_client.client._token == "SENTINEL-A"  # PEP 562 read

       # Path B
       c = iol_client.Client(token="SENTINEL-B")
       assert c._state.token == "SENTINEL-B"
       # The default singleton is UNAFFECTED
       assert iol_client.client._token == "SENTINEL-A"

       # Path C: writing via PEP 562 shim is now denied (v1.1 D-01 read-only)
       # so attempting to write SENTINEL-C must raise
       with pytest.raises(AttributeError):
           setattr(iol_client.client, "_token", "SENTINEL-C")
   ```

**Phase that owns:** Phase 1 (canary), with audit re-run at every phase merge. The BUG-04 D-08 audit is a Phase 3 (`main_higyrus`) gate.

**v1.1 lesson:** v1.1 archived Pitfall 1 ("monkeypatch silent breakage") + RETROSPECTIVE Patterns Established "PEP 562 compat shim". The shim works for READS; v1.2 must preserve that without re-introducing the write side that v1.1 explicitly chose NOT to support.

---

## Cluster 2 — unasync/codegen Pitfalls (Phases: spike + unasync/codegen migration × 4)

### Pitfall 4: B8 identity invariant breaks via codegen import shape — CRITICAL

**Symptom:**
v1.1 Phase 7 D-04 locked the invariant:
```python
# In aio.py and client.py, both packages must satisfy:
assert aio._raise_for_response is client._raise_for_response is _core.raise_for_response
```
This is enforced by `verification/test_public_surface.py` and is the linchpin of the `_core.py` extraction (single error-mapping codepath).

The naive codegen rewrite `s/from iol_client._core import raise_for_response/from iol_client._core import raise_for_response as _raise_for_response/` produces:
```python
# Generated client.py:
from iol_client._core import raise_for_response as _raise_for_response
```
which creates a NEW module-level binding that IS the same object — so `is` still works. BUT if the codegen emits:
```python
# Generated client.py:
from iol_client import _core
def _raise_for_response(resp):
    return _core.raise_for_response(resp)
```
(wrapping in a thunk for "clarity") → identity breaks. `aio._raise_for_response is client._raise_for_response` becomes False. The existing test catches it.

Worse: if codegen ALSO regenerates the test (because it's templated from `aio.py` test), the test is silently rewritten to compare wrong objects. Codegen-vs-test must be ANTAGONISTIC: tests stay hand-written for the codegen output.

Other identity invariants to preserve (audit before Phase 2 codegen lands):
- `aio.InstrumentType is client.InstrumentType` (iol-client; v1.1 has `aio.py:59` doing `from iol_client.client import InstrumentType`)
- Exception class identity: `aio.IOLAuthError is client.IOLAuthError` (must — both import from `exceptions.py`)
- `Client.__doc__` and `AsyncClient.__doc__` should NOT be identical (otherwise docstrings convey false equivalence to readers)
- Import-linter contracts: 4 forbidden contracts (`_core` cannot import `client`/`aio`); codegen must NOT introduce new violations

**Risk:** Silent breakage of v1.1 Phase 7 SC#1 sentinel. Diverging error-mapping logic in sync vs async. The test exists but does NOT survive a codegen-of-tests pattern.

**Prevention:**
1. **Codegen targets ONLY `aio.py` → `client.py` (or vice versa); test files are NEVER codegen targets.** Lint: pre-commit hook rejects commit if `verification/test_*.py` is in the same commit as a `client.py` regen unless explicitly tagged.
2. **Identity-check test runs FIRST in CI** (before any other test) so the invariant break is the first reported failure, not the 47th.
3. **Codegen template MUST emit `<name> = _core.<name>` aliases for all `_core` re-exports, NEVER thunks.** Document in `codegen-rules.md`; enforce by static analysis of the generated file.
4. **Add a CI assertion:** `python -c "from iol_client import client, aio, _core; assert aio.raise_for_response is client._raise_for_response is _core.raise_for_response"` runs as a separate CI step.

**Phase that owns:** Phase 2 (unasync/codegen spike + Phase 1 canary) MUST verify before any package codegen lands.

**Test pattern (CRITICAL — must land before any package's codegen merges):**
```python
@pytest.mark.parametrize("pkg", ["ambito_financiero_client", "iol_client", "higyrus_client", "matriz_client"])
def test_codegen_preserves_raise_for_response_identity(pkg):
    """v1.1 Phase 7 D-04 (B8) invariant survives codegen."""
    client_mod = importlib.import_module(f"{pkg}.client")
    aio_mod = importlib.import_module(f"{pkg}.aio")
    core_mod = importlib.import_module(f"{pkg}._core")
    assert client_mod._raise_for_response is aio_mod._raise_for_response is core_mod.raise_for_response
```

**v1.1 lesson:** D-04 alias pattern was explicit, not implicit; v1.2 codegen must preserve the explicit shape. Source: `packages/iol-client/src/iol_client/client.py:78` (`_raise_for_response = _core.raise_for_response`) — this exact line is the contract.

---

### Pitfall 5: Concurrent edit race — codegen overwrites by-hand edit when operator edits both `client.py` and `aio.py` in one commit — CRITICAL

**Symptom:**
Codegen runs at pre-commit. Operator hand-edits `client.py:_request` to add a new logging line, and hand-edits `aio.py:_request` the same way. They `git commit`. Pre-commit hook runs codegen with `aio.py` as source of truth → regenerates `client.py` from `aio.py` → if the codegen was run from `aio.py`'s last-committed state (not the staged version), the by-hand edit to `client.py` AND `aio.py` may be partially lost depending on ordering.

Even subtler: codegen reads `aio.py` from the working tree (with operator's edit) and writes `client.py` (overwriting the operator's parallel edit). The OPERATOR EDIT TO `client.py` IS SILENTLY LOST. Operator's commit looks clean; CI passes (both files now match codegen output); but the `client.py` log line is missing.

This is the urllib3 / psycopg / elasticsearch-py pattern and they all use a marker comment + CI verify-clean check.

**Risk:** Silent loss of by-hand edits; sync/async divergence that is invisible until the next time `client.py` is hand-edited.

**Prevention:**
1. **Generated-file marker at top of file:**
   ```python
   # @generated by unasync from aio.py — DO NOT EDIT.
   # To modify, edit aio.py and run `make codegen` (or rely on pre-commit).
   ```
   The marker is the FIRST line below the shebang/encoding comment. Pre-commit hook + CI checks for the marker on every line that should be generated.
2. **Codegen idempotency CI check:** `make codegen && git diff --exit-code packages/*/src/*/client.py` — if running codegen produces a diff against the committed file, CI fails. This catches the case where the operator forgot to run codegen.
3. **Pre-commit hook for `client.py` edits:** if `client.py` is modified BUT `aio.py` is not in the same commit AND the marker is present, the hook refuses the commit with: "client.py is generated from aio.py; edit aio.py instead".
4. **`make codegen-check` runs as separate CI job:** runs the codegen tool and compares output to committed file. Must produce zero diff. Same pattern as psycopg's async-to-sync workflow.

**Phase that owns:** Phase 2 (unasync/codegen spike + initial package). Spike must validate the marker + CI verify-clean pattern before the per-package rollout.

**Test pattern (CRITICAL — CI job, not pytest):**
```yaml
# .github/workflows/codegen-verify.yml
- name: Verify codegen idempotent
  run: |
    make codegen
    if ! git diff --exit-code packages/*/src/*/client.py; then
      echo "ERROR: codegen drift detected. Run 'make codegen' locally and commit." >&2
      exit 1
    fi
```

**Prior-art:** [psycopg async-to-sync codegen](https://www.psycopg.org/articles/2024/09/23/async-to-sync/) (uses pre-commit + verify-clean); urllib3 unasync pipeline; elasticsearch-py unasync; [unasyncd README](https://pypi.org/project/unasyncd/) (proposes marker comments). The market consensus on this is unanimous: marker + verify-clean.

**v1.1 lesson:** RETROSPECTIVE "What Was Inefficient" #1: "Sync/async logic duplication is now structural debt." The whole POINT of v1.2 codegen is to eliminate that — but the codegen itself becomes the new debt surface if hand-edits silently win.

---

### Pitfall 6: Naive textual rewrites miss async-only constructs that don't have direct sync equivalents

**Symptom:**
The minimal codegen pass is `s/async def /def /g; s/await //g; s/AsyncClient/Client/g`. This misses:

| Async-only construct | Naive textual rewrite | Correct rewrite |
|----------------------|----------------------|-----------------|
| `async for x in stream:` | `for x in stream:` — works IF stream is sync-iterable | Fails on `httpx.AsyncClient.stream()`; must rewrite to `client.stream()` sync API |
| `async with client.stream(...) as r:` | `with client.stream(...) as r:` | Works (httpx supports both); but if `client` is `httpx.AsyncClient` it's now a context-manager-error |
| `asyncio.gather(t1, t2)` | `asyncio.gather(...)` left as-is | Must rewrite to sequential calls OR `concurrent.futures.ThreadPoolExecutor` |
| `asyncio.Lock()` | left as-is | Must rewrite to `threading.Lock()` — and the `TokenStore` 3-way primitive (v1.1 `_token_store.py:54`) already provides this; codegen MUST NOT create a parallel implementation |
| `asyncio.sleep(t)` | left as-is | Must rewrite to `time.sleep(t)` |
| `async def __aenter__` | `def __enter__` | Correct in spirit, but `aio.py`'s `__aexit__` calls `await self.aclose()` which becomes `self.aclose()` — only correct if `Client.close()` exists with same semantics |
| `_get_async_lock()` | (whatever the codegen does) | This is the v1.1 D-10 lazy-per-loop helper; sync version must NOT exist (it would create a parallel sync-only lock implementation that races with `TokenStore`'s `threading.Lock`) |

For matriz specifically: `_token_store.py:54` exposes a `threading.Lock` callable from sync REST, ws_client daemon thread, and asyncio context (via `asyncio.to_thread`). If the codegen runs `aio.py` → `client.py` and emits a parallel `threading.Lock` instance in `client.py` (because it doesn't know about `_token_store.py`), the v1.1 Phase 10 architectural lift is voided.

**Risk:** Codegen produces a `client.py` that imports asyncio (dead code) OR re-implements concurrency primitives that already live in `_token_store.py`.

**Prevention:**
1. **Allow-list of patterns the codegen explicitly handles; deny-list of patterns that REQUIRE manual intervention.** The deny-list triggers a hard codegen error with file:line pointer and a suggested manual fix.
2. **`_token_store` is OFF-LIMITS to codegen** — `_token_store.py` is hand-written, NEVER regenerated. Pre-commit hook rejects regen attempts on this file.
3. **Spike-before-plan for the codegen tool choice:** the v1.2 PROJECT.md already calls for a spike. Use the spike to enumerate the matriz `aio.py` patterns (852 LOC) and prove each one survives the codegen pass OR is explicitly hand-overridden.
4. **Codegen tool MUST emit a "transformations applied" report at every run.** The report lists every rule fired and on which line. Operator reviews the report before committing.
5. **Per-package golden file:** for each package, maintain a small "golden input → golden output" file that exercises every rule. CI runs codegen on the golden input and compares to the expected output.

**Phase that owns:** Phase 2 (unasync/codegen spike) — the spike RESEARCH gate. The spike MUST surface every async-only construct in the current 4 packages' `aio.py` files and prove the codegen tool handles them.

**Test pattern:**
```python
def test_codegen_does_not_touch_token_store():
    """_token_store.py is hand-written; codegen must not regenerate it."""
    # Hash before regen
    before = hashlib.sha256(Path("packages/matriz-client/src/matriz_client/_token_store.py").read_bytes()).hexdigest()
    subprocess.check_call(["make", "codegen"])
    after = hashlib.sha256(Path("packages/matriz-client/src/matriz_client/_token_store.py").read_bytes()).hexdigest()
    assert before == after, "_token_store.py is not codegen-targeted"

def test_codegen_report_lists_every_transformation():
    """Operator must see what codegen did."""
    result = subprocess.run(["make", "codegen"], capture_output=True, text=True)
    assert "Transformations applied:" in result.stdout
    assert "async def -> def" in result.stdout
```

**v1.1 lesson:** Phase 10 spike-before-plan (`Skill("spike-findings-market-libs")`) validated the TokenStore primitive; v1.2 codegen must NOT undo that validated architecture. Source: PROJECT.md Auto-loaded Knowledge.

---

## Cluster 3 — IOL refresh_token Disk Persistence Pitfalls (Phase: IOL persistence)

### Pitfall 7: Token leak via new disk-persistence log sites bypassing `RedactingFilter` — CRITICAL

**Symptom:**
v1.1 LOG-02 mandates per-package `RedactingFilter` over `logging.getLogger("iol_client")` with NullHandler. The filter strips Bearer tokens, `password=`, IOL refresh_token patterns, etc.

Adding disk persistence introduces new log sites:
```python
logger.debug("writing refresh_token to %s", token_path)         # path-only, safe
logger.warning("failed to write refresh_token to %s: %s", path, exc)  # exc may contain token
logger.info("loaded refresh_token from %s (age=%ds)", path, age)  # age leaks freshness, ok
```

Risks:
- The `exc` traceback for a disk-write OSError may contain `repr(self._state.refresh_token)` if the persistence helper does `logger.warning("save failed: %r", state)` (the state's `__repr__` ALREADY redacts per v1.1 Phase 7 D-18+T-06-05, but a quick `logger.exception(...)` with `extra={"state": state}` might serialize via `repr(state.refresh_token)` if the helper imports the token field separately).
- The PATH may contain user info: XDG_CONFIG_HOME default is `~/.config`, which expands to `/home/sebadlf/.config/...` — username leaks. On CI runners (`/home/runner/.config/...`) the username is `runner`, less sensitive but still inferable.
- If the persistence helper uses its OWN logger (`logging.getLogger("iol_client.persistence")`), it INHERITS `iol_client`'s RedactingFilter (filters propagate up). If it uses `logging.getLogger("market_libs.persistence")` or any name OUTSIDE `iol_client.*` namespace, NO filter applies.

**Risk:** Refresh token leak to Sentry/CloudWatch/Datadog via DEBUG logs from a downstream consumer that enabled DEBUG on iol_client.

**Prevention:**
1. **Persistence helper logger MUST be under `iol_client.*` namespace.** Specifically: `logging.getLogger("iol_client.persistence")` or `logging.getLogger(__name__)` from a module inside `packages/iol-client/src/iol_client/`.
2. **NEVER log `exc` for token-write failures via `logger.exception()` — only `logger.warning("save failed: %s", type(exc).__name__)`.** The exception type is safe; the message/args may not be.
3. **Path redaction in logs:** the persistence helper logs `pathlib.Path(p).name` (just the filename), NEVER the full path. Operator can find it via documented location.
4. **Regression test mirroring v1.1's no-leak guard:**
   ```python
   def test_disk_persistence_never_logs_token(caplog, tmp_path, monkeypatch):
       """Regression: refresh_token disk write/read lifecycle never logs the token."""
       caplog.set_level(logging.DEBUG, logger="iol_client")
       monkeypatch.setenv("IOL_TOKEN_PATH", str(tmp_path / "iol-token"))

       SENTINEL = "REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210"
       client = iol_client.Client(refresh_token=SENTINEL)
       client._persist_refresh_token()  # whatever the v1.2 API is

       # Force the read path too
       client2 = iol_client.Client()
       client2._load_refresh_token()

       # Force a write failure (raises OSError) to exercise the warning path
       monkeypatch.setattr("pathlib.Path.write_text", lambda *a, **kw: (_ for _ in ()).throw(OSError("disk full")))
       try:
           client._persist_refresh_token()
       except OSError:
           pass

       all_log_text = " ".join(r.getMessage() for r in caplog.records) + " ".join(repr(r.args) for r in caplog.records)
       assert SENTINEL not in all_log_text, "Refresh token leaked into a log record"
   ```

**Phase that owns:** Phase 5 (IOL refresh_token disk persistence) — MUST include the no-leak regression test.

**v1.1 lesson:** LOG-02 + v1.1 archived Pitfall 7. The pattern is: in-library redaction, namespace-correct logger, exception-type-only on failure. Source: `verification/test_logging_no_token_leak.py` already exists; v1.2 extends to cover the disk lifecycle.

---

### Pitfall 8: Stale token after out-of-band rotation — bad disk token not deleted after failed refresh

**Symptom:**
IOL's refresh_token can be invalidated server-side via:
- User changes password in the IOL web UI
- Admin revokes the refresh_token via API
- IOL OAuth2 server rotates refresh_token (the cached one becomes stale per v1.0/v1.1 BUG-03)

The v1.1 in-instance refresh handling (BUG-03) is: 401 on refresh → password fallback. Disk persistence adds: if disk has refresh_token=X and X is stale, EVERY new process loads X, attempts refresh, gets 401, falls back to password — and X is STILL on disk. The next process repeats the cycle. The disk cache becomes a self-defeating cache.

Worse: the password fallback succeeds (IOL issues a fresh refresh_token Y). If the disk-write happens BEFORE the password fallback path, the operator sees X on disk; if AFTER, Y. The implementation MUST clear the disk on refresh failure AND write the new Y on successful password grant.

**Risk:** Every IOL process hits the 401-then-password-fallback path, doubling latency. Worse for unattended scheduled jobs that depend on disk-persisted refresh_token to skip password storage.

**Prevention:**
1. **The disk-token lifecycle is: load → use → on 401: delete disk + clear in-memory → password fallback → write fresh disk.** The delete on 401 is non-negotiable.
2. **Atomic write:** `pathlib.Path(path).write_text(token + "\n")` is not atomic; use `path.with_suffix(".tmp")` write + `os.replace(tmp, path)` for atomic-on-POSIX semantics.
3. **Regression test:**
   ```python
   def test_disk_token_deleted_on_refresh_401(httpx_mock, tmp_path, monkeypatch):
       monkeypatch.setenv("IOL_TOKEN_PATH", str(tmp_path / "iol-token"))
       # Seed disk with a stale refresh token
       (tmp_path / "iol-token").write_text("STALE-REFRESH-TOKEN\n")
       # Server rejects the refresh
       httpx_mock.add_response(url="...token", status_code=401, match_content=b"refresh_token=STALE")
       # Server accepts password grant fallback
       httpx_mock.add_response(url="...token", status_code=200,
                               json={"access_token": "AT", "refresh_token": "FRESH", "expires_in": 900})
       client = iol_client.Client(username="u", password="p")
       client.login()
       # Disk now has FRESH, not STALE
       assert (tmp_path / "iol-token").read_text().strip() == "FRESH"
   ```

**Phase that owns:** Phase 5 (IOL disk persistence).

**v1.1 lesson:** BUG-03 D-IOL-10 lifecycle was: in-instance refresh fallback to password. v1.2 extends to: across-process refresh fallback + disk cleanup. Source: `packages/iol-client/src/iol_client/client.py:282-286` (existing in-instance fallback) — extend to disk.

---

### Pitfall 9: Multi-process race — two parallel `main_iol.py --live` runs clobber each other's refresh_token

**Symptom:**
Operator launches `uv run --package iol-client python main_iol.py --live` in two terminals (or CI matrix runs 3.12 + 3.13 in parallel). Both processes:
1. Load STALE refresh_token X from disk.
2. Both call `_refresh()` → IOL issues two new tokens Y and Z (depending on order).
3. Process A writes Y to disk. Process B writes Z to disk. Disk now has Z; A's in-memory token is Y.
4. Next process loads Z. Process A's Y is orphaned. If IOL rotates refresh on use (some servers do), Y may be the only valid one — A keeps working, but the disk says Z is valid → next process uses Z → fails → falls back to password.

The thrashing is invisible to either process.

**Risk:** Refresh-token churn; intermittent password-fallback latency; correlated CI failures when 3.12 and 3.13 runners share the same `~/.config/iol-client/token` (if the path doesn't include the Python version or runner ID).

**Prevention:**
1. **File lock during write:** `fcntl.flock(f.fileno(), fcntl.LOCK_EX)` on POSIX. Python stdlib only — no portalocker dependency. Lock duration: only the write transaction.
2. **OR (simpler): treat the disk path as PER-PROCESS via `IOL_TOKEN_PATH` env var.** Document: "set `IOL_TOKEN_PATH=/path/to/per-user-token` if running multiple iol_client processes." Default path: `~/.config/iol-client/token` is a single-user assumption.
3. **OR: check `os.environ.get("CI") == "true"` → use `/tmp/iol-token-${PID}` (not persisted across CI runs).** CI runs don't benefit from disk persistence anyway (token re-issued per workflow).
4. **Regression test for the race (mocked):**
   ```python
   def test_disk_token_write_under_concurrent_processes(tmp_path):
       """Two processes refreshing simultaneously: last-writer-wins is acceptable; corruption is not."""
       token_path = tmp_path / "token"
       results = []
       def writer(tok):
           # Simulate the persistence call path
           from iol_client._persistence import write_refresh_token  # v1.2 API
           write_refresh_token(token_path, tok)
           results.append(tok)
       threads = [threading.Thread(target=writer, args=(f"TOKEN-{i}",)) for i in range(20)]
       for t in threads: t.start()
       for t in threads: t.join()
       # File must contain ONE complete token, not a corrupted mix
       contents = token_path.read_text().strip()
       assert contents in [f"TOKEN-{i}" for i in range(20)]
       assert "\n" not in contents or contents.endswith("\n")  # no interleaved writes
   ```

**Prior-art:** [Google google-auth](https://googleapis.dev/python/google-auth/latest/) for Python uses fcntl.flock for token cache file locking. Anthropic/openai SDK doesn't persist tokens to disk (they use API keys); this pitfall is specific to OAuth refresh flows.

**Phase that owns:** Phase 5 (IOL disk persistence).

**v1.1 lesson:** v1.1 introduced `_token_store.py` `threading.Lock` for in-process 3-way concurrency. v1.2 extends to inter-process via fcntl. Same principle (lock-around-critical-section), different scope.

---

### Pitfall 10: File permissions 0600 noop on Windows / unsafe on shared CI runners

**Symptom:**
The v1.2 disk persistence sets `chmod 0600` on the token file:
```python
path.write_text(token); path.chmod(0o600)
```
On Linux/macOS: file is owner-readable only. Safe.
On Windows: chmod is a no-op (Windows uses ACLs); the file is world-readable by default in the user's home dir. The project IS Python 3.12+ on Linux/macOS-targeted, but the CI matrix runs Ubuntu, where 0600 IS meaningful.

CI-specific risks:
- `/tmp/iol-token` is wiped between jobs on GitHub Actions runners → token never persists across runs (fine; defeats the optimization but not a security issue).
- BUT: GitHub Actions cache (`actions/cache@v4`) MAY cache the token file if the path is under a cached directory. The cache is per-PR — token leaks across PRs by different contributors.
- `$XDG_CONFIG_HOME` or `$HOME` defaults: on Ubuntu CI `/home/runner/.config/iol-client/token` is wiped per-job. Safe by default.

**Risk:** Token in CI cache leaking across PRs; on Windows (if support is later added) 0600 noop.

**Prevention:**
1. **Default disk path on CI: REFUSE.** Check `os.environ.get("CI") == "true"` AND `IOL_TOKEN_PATH` is not set → SKIP disk persistence entirely. Log a one-line INFO: "disk persistence disabled on CI".
2. **Default disk path on dev: `${XDG_CONFIG_HOME:-$HOME/.config}/iol-client/token`.** Document the location; ensure parent dir is `mkdir -p` with `mode=0o700`.
3. **Document in README:** "if you cache `~/.config/iol-client/` in CI, you are caching a refresh token; either don't, or set `IOL_TOKEN_PATH=/tmp/some-volatile-path`".
4. **chmod check at write time:** verify `path.stat().st_mode & 0o777 == 0o600` after write; warn (not fail) if not.

**Phase that owns:** Phase 5 (IOL disk persistence).

**Test pattern:**
```python
def test_disk_persistence_skipped_on_ci(monkeypatch, tmp_path):
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("IOL_TOKEN_PATH", raising=False)
    # Persistence call returns early without touching the disk
    from iol_client._persistence import write_refresh_token
    result = write_refresh_token(default_path=tmp_path / "should-not-exist", token="X")
    assert result is None  # or whatever signals "skipped"
    assert not (tmp_path / "should-not-exist").exists()
```

---

## Cluster 4 — `Client.from_env()` Pitfalls (Phase: ergonomics × 4)

### Pitfall 11: `from_env()` re-calls `load_dotenv()` and shadows runtime-set env vars

**Symptom:**
v1.1 packages call `load_dotenv()` at module import (`packages/iol-client/src/iol_client/client.py:68`). This populates `os.environ` from `.env` at import time. After import, runtime code may override:
```python
os.environ["IOL_USER"] = "runtime-override@example.com"
client = iol_client.Client.from_env()  # if from_env() calls load_dotenv() AGAIN, .env wins
```
`python-dotenv`'s `load_dotenv()` by default does NOT override existing env vars (the `override=False` default). So a runtime-set env var SURVIVES a second `load_dotenv()` call. Good.

BUT: on CI runners, env vars come from the workflow YAML, not a `.env` file. There IS no `.env` on CI. `load_dotenv()` is a no-op there → fine.

The risk: someone "fixes" the no-op concern by adding `load_dotenv(override=True)` to `from_env()`. Now runtime overrides are silently dropped.

**Risk:** Hard-to-debug "the env var I set in the test fixture was ignored" bug.

**Prevention:**
1. **`from_env()` does NOT call `load_dotenv()`.** Document: "`from_env()` reads from `os.environ` as-is; module-import `load_dotenv()` already populated `.env`. To force a re-read, call `dotenv.load_dotenv(override=True)` explicitly BEFORE `from_env()`."
2. **`from_env()` implementation is literally:**
   ```python
   @classmethod
   def from_env(cls, **overrides: Any) -> Self:
       return cls(
           username=overrides.get("username") or os.environ.get("IOL_USER"),
           password=overrides.get("password") or os.environ.get("IOL_PASSWORD"),
           base_url=overrides.get("base_url") or os.environ.get("IOL_BASE_URL"),
           **{k: v for k, v in overrides.items() if k not in {"username", "password", "base_url"}},
       )
   ```
3. **Test:**
   ```python
   def test_from_env_does_not_call_load_dotenv(monkeypatch):
       calls = []
       monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: calls.append((a, kw)))
       monkeypatch.setenv("IOL_USER", "from-env-runtime")
       client = iol_client.Client.from_env()
       assert client._state.username == "from-env-runtime"
       assert calls == []  # load_dotenv NOT called
   ```

**Phase that owns:** Phase 6 (ergonomics × 4 packages).

**v1.1 lesson:** v1.1 packages already call `load_dotenv()` once at module import. v1.2 must not double-dip. Source: per-package `client.py` line ~68 (consistent across 4 packages).

---

### Pitfall 12: env var naming drift — IOL_USER (legacy) vs IOL_API_KEY (SDK convention)

**Symptom:**
anthropic SDK uses `ANTHROPIC_API_KEY`. openai uses `OPENAI_API_KEY`. The ergonomic intuition for `Client.from_env()` is "this reads `<PKG>_API_KEY`". But IOL's auth is OAuth2 password grant — there is no "API key". The env vars are `IOL_USER` and `IOL_PASSWORD`. Higyrus is `HIGYRUS_BEARER_TOKEN`. Matriz is `PRIMARY_USERNAME`, `PRIMARY_PASSWORD`, `PRIMARY_ACCOUNT`. Ambito has no auth.

If v1.2 introduces SDK-style env vars in parallel (`IOL_API_KEY` as alias for `IOL_USER+PASSWORD` — but it's not a single value, it's a credential pair), operators are confused by which to set. If v1.2 keeps only the existing names, the `from_env()` ergonomic intuition is wrong.

**Risk:** Operator sets `IOL_API_KEY` thinking it works; `from_env()` silently constructs a Client with no credentials; first API call fails with `IOLAuthError`.

**Prevention:**
1. **Keep existing env var names; document them explicitly in `from_env()` docstring.** No deprecation, no aliasing.
2. **`from_env()` raises a clear error when required vars are missing:**
   ```python
   @classmethod
   def from_env(cls, **overrides) -> Self:
       username = overrides.get("username") or os.environ.get("IOL_USER")
       password = overrides.get("password") or os.environ.get("IOL_PASSWORD")
       missing = []
       if not username: missing.append("IOL_USER")
       if not password: missing.append("IOL_PASSWORD")
       if missing:
           raise IOLAuthError(
               f"Client.from_env() requires environment variables: {missing}. "
               f"Set them in your .env file or shell. "
               f"Note: IOL uses OAuth2 password grant, not an API key."
           )
       return cls(username=username, password=password, ...)
   ```
3. **Test:**
   ```python
   def test_from_env_raises_clear_error_on_missing_vars(monkeypatch):
       monkeypatch.delenv("IOL_USER", raising=False)
       monkeypatch.delenv("IOL_PASSWORD", raising=False)
       with pytest.raises(IOLAuthError, match=r"IOL_USER.*IOL_PASSWORD"):
           iol_client.Client.from_env()
   ```

**Phase that owns:** Phase 6 (ergonomics × 4).

**v1.1 lesson:** RETROSPECTIVE patterns are about CONSISTENCY across packages — don't introduce a new naming convention that the 4 packages can't all follow. Source: STACK.md (each package has its own credentials shape).

---

## Cluster 5 — `with_options()` Pitfalls (Phase: ergonomics × 4)

### Pitfall 13: `with_options()` creates a new Client with its own connection pool — resource leak

**Symptom:**
The naive `with_options()` implementation:
```python
def with_options(self, *, max_retries: int | None = None) -> Self:
    return type(self)(
        base_url=self._state.base_url,
        username=self._state.username,
        password=self._state.password,
        max_retries=max_retries if max_retries is not None else self._max_retries,
    )
```
Each call to `client.with_options(max_retries=0).get_quote(...)` creates a new `Client` object → new `httpx.Client` → new connection pool → potentially new TLS handshake. The new Client is never `close()`d (the chained call doesn't context-manager it). Connection pool leak; FD exhaustion under load.

Anthropic's SDK pattern: `with_options()` returns a NEW client BUT shares the underlying httpx transport. Reference: [`anthropic-sdk-python` source](https://github.com/anthropics/anthropic-sdk-python) — `with_options` calls `self.copy(...)` which clones config but reuses the http client.

**Risk:** FD exhaustion under repeated `with_options(...)` calls; reauth on each new instance (defeats token cache).

**Prevention:**
1. **`with_options()` returns a NEW Client that SHARES `_state.http_client` AND `_state.token` AND `_state.refresh_token`.** Only the per-call options (`max_retries`) differ. Mutate `_max_retries` directly; the underlying transport's `max_attempts` is re-derived per send (passed via `request.extensions` or the transport's configured value).
2. **Architecture detail:** the `RetryTransport.max_attempts` is set at Client construction. To override per-call, EITHER:
   - (a) Add `max_attempts` to `request.extensions` and have `RetryTransport` honor it: `attempts = request.extensions.get("max_attempts", self.max_attempts)`.
   - (b) `with_options()` constructs a new `Client` with a new `RetryTransport(max_attempts=N+1)` but ALIASES the underlying `httpx.HTTPTransport` connection pool — but `httpx.Client` doesn't expose this directly.
   - (a) is simpler and aligns with v1.1's `request.extensions` pattern (used for `idempotent` and `request_id`).
3. **Test the resource lifecycle:**
   ```python
   def test_with_options_shares_http_client(monkeypatch):
       c = iol_client.Client(username="u", password="p")
       http = c._state.http_client  # may be None until first request
       c.login()  # forces http_client creation
       http = c._state.http_client
       assert http is not None
       # with_options returns a new Client but http_client is the SAME object
       c2 = c.with_options(max_retries=0)
       assert c2._state.http_client is http
       assert c2._state.token == c._state.token  # token cache shared
   ```

**Phase that owns:** Phase 7 (`with_options` × 4 packages).

**Prior-art:** [anthropic-sdk-python `with_options()`](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_client.py) — copies config, shares httpx client.

---

### Pitfall 14: `max_retries=N` per-call override interacts wrongly with the mutation gate — CRITICAL

**Symptom:**
v1.1 Phase 8 Pitfall 4 (the duplicate-order risk) is mitigated by the `RetryTransport` mutation gate: when `request.extensions["idempotent"] = False`, the transport refuses to retry regardless of `max_attempts`. matriz `new_order`, `cancel_order`, `replace_order` builders set `idempotent=False` explicitly.

v1.2 introduces `client.with_options(max_retries=10).new_order(...)`. The semantics MUST be:
- `max_retries=10` is the UPPER BOUND on attempts.
- `idempotent=False` is a HARD REFUSAL to retry — overrides any `max_retries` value.
- Caller passing `max_retries=10` on a mutating call → still ONE attempt (mutation gate wins).

If the implementation lets `max_retries=10` bypass the mutation gate ("the operator explicitly asked for 10 retries"), v1.1 Pitfall 4 is voided. Duplicate orders are a real money-on-the-line risk.

The OPPOSITE failure: `with_options(max_retries=0).get_quote(...)` on an idempotent call should respect `max_retries=0` (no retries) AND still NOT re-derive the mutation gate. `max_retries=0` and `idempotent=True` are orthogonal.

**Risk:** Duplicate matriz orders if `with_options` bypasses the mutation gate. Money-on-the-line bug.

**Prevention:**
1. **Mutation gate REMAINS the absolute authority on retry permission.** `with_options(max_retries=N)` only TIGHTENS or LOOSENS the cap for idempotent calls; for non-idempotent calls, the cap is forced to 1 attempt regardless.
2. **Implementation in `RetryTransport`:**
   ```python
   def handle_request(self, request):
       if not request.extensions.get("idempotent", False):
           # MUTATION GATE: ALWAYS exactly 1 attempt, regardless of max_attempts override.
           return self._send_once(request)
       max_attempts = request.extensions.get("max_attempts", self.max_attempts)
       # ... existing retry loop ...
   ```
3. **CRITICAL regression test (must land before Phase 7 merge):**
   ```python
   def test_with_options_max_retries_does_not_bypass_mutation_gate(httpx_mock):
       """v1.1 Pitfall 4 (duplicate orders) survives v1.2 with_options() ergonomic."""
       httpx_mock.add_response(method="POST", status_code=503)  # would normally retry
       client = matriz_client.Client(...)
       client._state.token = "fake"
       with pytest.raises(matriz_client.MatrizAPIError):
           # Caller explicitly asks for 10 retries, but it's a mutating call
           client.with_options(max_retries=10).new_order(...)
       # Mutation gate enforced: exactly ONE outgoing request
       assert len(httpx_mock.get_requests()) == 1
   ```

**Phase that owns:** Phase 7 (`with_options` × 4 packages). The regression test is the merge gate for matriz specifically.

**v1.1 lesson:** Phase 8 Pitfall 4 is the MOST IMPORTANT v1.1 mitigation; v1.2 must not regress it. Source: PROJECT.md Key Decisions row "Mutation gate vía `request.extensions["idempotent"]`".

---

## Cluster 6 — Live Re-verification + Cross-Cutting Pitfalls

### Pitfall 15: Driver migration changes finding IDs even when API behavior is unchanged

**Symptom:**
v1.1 LIVE-01 gate compared baseline (`4d48e07`) findings to head findings via `verification/findings.py`. The findings are content-addressed (dedupe by `idempotent_by_title`). If a probe is RENAMED (`probe_login_sync` → `probe_login` because driver migration unifies sync+async into instance-method calls), the finding ID derived from the probe name changes. Diff is non-empty even though API behavior is identical.

Operator disposition for the old finding (Classification/Rationale/Resolution) doesn't carry forward to the new finding (different title). LIVE-01 v2 gate at v1.2 close shows "all probes new, no baseline match" — false positive.

**Risk:** Operator must re-triage ~40 findings across 4 packages even though zero API behavior changed. Wasted effort + risk of inconsistent triage.

**Prevention:**
1. **Probe NAMES are RENAME-FROZEN for v1.2.** Driver migration changes the BODY of `probe_login_sync` (from `iol_client.login()` to `client.login()`), NOT the function name. Function-name stability = finding-title stability = operator-disposition preservation.
2. **If a rename is unavoidable** (e.g., async/sync unification removes the `_sync` suffix), the driver code MUST emit findings under both the OLD and NEW title for one cycle, with a `migrated_from: <old-title>` marker in the body. Operator marks the OLD finding as "MIGRATED" (new classification value) and v1.3 can clean up.
3. **Lint check:** `grep -c "^def probe_" main_*.py` before and after migration must produce the same count per file. Diff flag for review.
4. **Carry-forward operator dispositions by NAME-OR-MIGRATED-FROM:** extend `findings.py` parser to read both `title:` and `migrated_from:` for matching.

**Phase that owns:** Phase 8 (final live re-verification × 4 packages). The probe-rename audit is a Phase 1 (canary) gate.

**v1.1 lesson:** RETROSPECTIVE Patterns Established: "`verification/findings.py` append-only with BEGIN/END zones + `idempotent_by_title`" — title is the stable key. v1.2 must preserve title stability.

---

### Pitfall 16: Ámbito canary pattern doesn't generalize to higyrus/matriz

**Symptom:**
Ámbito is the smallest driver (734 LOC), no auth, no mutating endpoints. Ámbito's canary migration validates: `Client()` instantiation, `from_env()`, `with_options(max_retries=N)`, probe-by-probe migration. PASS.

Phase 2 attempts iol (1675 LOC, OAuth + refresh_token, 401 re-auth, `probe_auth_401` opt-in). New surface: token cache + refresh + auth-failure cascade. The ámbito canary pattern doesn't cover any of this.

Phase 3 attempts higyrus (2458 LOC, Bearer token + multi-account iteration deferred from BUG-04). The ámbito canary doesn't cover multi-account.

Phase 4 attempts matriz (2283 LOC, X-Auth-Token + 3-way TokenStore + WebSocket daemon thread). The ámbito canary doesn't cover the 3-way primitive.

The canary establishes a FLOOR, not a CEILING — but a planner who treats canary-pattern-as-template will under-scope the later phases.

**Risk:** Phases 3 and 4 silently under-scoped because "we did it in ámbito, this is just replication"; emerge with surprise complexity at execution time.

**Prevention:**
1. **Per-phase scoping audit:** before starting each phase, enumerate the package-specific complexity that the canary did NOT exercise. Document in the phase plan.
2. **Spike-before-plan for matriz Phase 4:** matriz introduces both the 3-way TokenStore interaction AND the WebSocket daemon thread (which reads `_token_store` directly). The driver migration touches the daemon-thread code path. SPIKE this before planning.
3. **Per-phase rollback plan:** if any phase reveals a canary-pattern mismatch, revert + re-spike, don't push through.

**Phase that owns:** Cross-cutting; each phase has its own audit step.

**v1.1 lesson:** RETROSPECTIVE Cross-Milestone Trend #3: "Per-package serial pattern" — ámbito → iol → higyrus → matriz IS the right order (smallest to largest blast radius). v1.0 and v1.1 both replicated it. v1.2 must continue, AND respect that each step UP introduces new complexity.

---

### Pitfall 17: CI Python 3.13 baseline not confirmed at v1.1 close — codegen 3.13-incompat would mis-attribute to v1.2

**Symptom:**
RETROSPECTIVE "What Was Inefficient" #2: "CI Python 3.13 confirmation deferred 3× phases" — at v1.1 close, the 3.13 matrix has NOT received human confirmation that it's green (the matrix RUNS, but the operator hasn't actively checked). If v1.2 Phase 2 introduces a codegen output that uses Python 3.12-only syntax (e.g., `type X = ...` PEP 695 alias statement, which is 3.12+ but with semantic refinements in 3.13; or generic decorator forms), the 3.13 CI break gets blamed on v1.2 — but the underlying baseline is in fact green on 3.13.

**Risk:** v1.2 Phase 2 spends a sprint debugging a "v1.2 broke 3.13" symptom that's actually a v1.1 baseline issue. False attribution wastes effort.

**Prevention:**
1. **v1.2 Phase 1 (or pre-Phase-1) gate: run `gh workflow view` and confirm v1.1 baseline (`71bf201`) is green on Python 3.13.** If not, file as v1.1 carry-forward debt, fix BEFORE Phase 1.
2. **Use `python_version = "3.12"` in mypy config (already in place) but RUN tests on both 3.12 and 3.13.** Ensure tests don't import 3.13-only modules.
3. **Codegen output MUST be 3.12-compatible.** The codegen template should explicitly avoid 3.13-only syntax (e.g., `typing.TypeAliasType`, PEP 696 type-parameter defaults).
4. **Smoke test:** at Phase 2 codegen spike, run `python3.13 -c "import ambito_financiero_client; import iol_client; import higyrus_client; import matriz_client"` against the generated output. Must succeed.

**Phase that owns:** Phase 1 (gate); cross-cutting for all phases.

**v1.1 lesson:** RETROSPECTIVE "What Was Inefficient" #2 + Key Lesson #6 ("`human_verification_pending` pattern in VERIFICATION.md frontmatter"). Use the pattern for v1.2 Phase 1: explicit `human_verification_pending: [{test: "CI Python 3.13 green", expected: "all jobs pass", why_human: "operator confirms GH Actions UI"}]`.

---

## Pitfall-to-Phase Mapping

| # | Pitfall | Phase | Test Pattern | CRITICAL? |
|---|---------|-------|--------------|-----------|
| 1 | State leak between probes (per-instance) | Phase 1 canary + 2/3/4 | `test_main_<pkg>_uses_single_client_instance` AST walker | matriz YES |
| 2 | Regression invisibility (findings regen) | Phase 1 canary, cross-cutting | `test_findings_survives_driver_migration` | |
| 3 | Test fixture drift | Phase 1, audit each phase | `test_fixture_three_paths_all_reach_production` | |
| 4 | Codegen breaks B8 identity | Phase 2 spike + per-pkg | `test_codegen_preserves_raise_for_response_identity` (4-param) | YES |
| 5 | Codegen overwrites by-hand edit | Phase 2 spike | CI job `make codegen && git diff --exit-code` | YES |
| 6 | Async-only constructs in codegen | Phase 2 spike | `test_codegen_does_not_touch_token_store` + golden file | |
| 7 | Token leak via new disk log sites | Phase 5 IOL disk persistence | `test_disk_persistence_never_logs_token` (sentinel substring check) | YES |
| 8 | Stale token after out-of-band rotation | Phase 5 | `test_disk_token_deleted_on_refresh_401` | |
| 9 | Multi-process race | Phase 5 | `test_disk_token_write_under_concurrent_processes` | |
| 10 | File permissions / CI cache | Phase 5 | `test_disk_persistence_skipped_on_ci` | |
| 11 | `from_env` re-calls `load_dotenv` | Phase 6 ergonomics | `test_from_env_does_not_call_load_dotenv` | |
| 12 | env var naming drift | Phase 6 | `test_from_env_raises_clear_error_on_missing_vars` | |
| 13 | `with_options` resource leak | Phase 7 | `test_with_options_shares_http_client` | |
| 14 | `with_options(max_retries)` × mutation gate | Phase 7 | `test_with_options_max_retries_does_not_bypass_mutation_gate` | YES |
| 15 | Driver migration changes finding IDs | Phase 8 LIVE re-verification | probe-rename audit + grep count | |
| 16 | Canary pattern doesn't generalize | Cross-cutting per phase | per-phase scoping audit | |
| 17 | CI Python 3.13 baseline not confirmed | Phase 1 gate | `gh workflow view` | |

---

## Cross-Feature Integration Pitfalls

**Driver migration × findings.py (Pitfalls 1, 2, 15):**
Per-instance `Client()` per probe (Pitfall 1) PLUS regen-from-scratch findings (Pitfall 2) PLUS probe-rename (Pitfall 15) → operator disposition loss is catastrophic. Mitigation: ONE Client per main() run; preserve probe names; freeze findings titles. All three pitfalls share the same root cause (driver shape change) and the same prevention (probe-name + title stability).

**Codegen × `_token_store.py` (Pitfalls 5, 6, 9):**
Codegen at Phase 2 must NOT touch `_token_store.py` (hand-written). Disk persistence at Phase 5 must NOT add a parallel locking primitive (v1.2 inter-process lock is fcntl.flock, separate from `_token_store.py`'s threading.Lock). The two locks live at different scopes (intra-process vs inter-process).

**`with_options(max_retries)` × mutation gate × disk persistence (Pitfalls 8, 14):**
A caller does `client.with_options(max_retries=10).login()`. `login()` is the refresh-or-password-fallback path that touches disk. If `max_retries=10` causes the login retry loop to retry 10 times on 401, and EACH retry wipes the disk-cached refresh_token (Pitfall 8), the disk cache thrashes. Mitigation: `_send_auth_request` already uses `idempotent=True` for `login/refresh` (Phase 8 D-29), but the disk-cleanup-on-401 path must be IDEMPOTENT (delete-if-exists, never delete-then-fail).

**Library logging × disk persistence × `RedactingFilter` (Pitfalls 7, 11):**
Per-package `RedactingFilter` is at `logging.getLogger("iol_client")` scope. Persistence helper at `iol_client.persistence` namespace inherits the filter. BUT: if `from_env()` adds a new log site (`logger.debug("constructed from env: %s", config)`), and `config` contains the password (because env-var-read happens INSIDE `from_env()`), the filter must redact. Add password to the filter's deny-list explicitly; test sentinel substring not in caplog.

**Driver migration × CI 3.13 (Pitfalls 1, 17):**
Driver migration changes `main_*.py` syntax. If the new syntax uses 3.12-only features (positional-only `/`, PEP 695 alias), 3.13 CI may break. Confirm 3.12-compatibility of all driver migrations; the codegen-output 3.13-compat (Pitfall 17) is a separate concern.

---

## "Looks Done But Isn't" Checklist

- [ ] **Driver migration (Phase 1):** ONE `Client()` per `main()` run; AST test landed; INT-01 idiom replaced with `client._state.<attr>`
- [ ] **Driver migration:** probe names UNCHANGED; finding titles UNCHANGED; LIVE-01 baseline match preserved
- [ ] **Driver migration:** 907 test count baseline maintained; assertion count >= baseline
- [ ] **Codegen (Phase 2):** B8 identity check is the FIRST CI test; runs before all others
- [ ] **Codegen:** marker comment `@generated by ... DO NOT EDIT` at top of every generated file
- [ ] **Codegen:** CI job `make codegen && git diff --exit-code` separate from pytest
- [ ] **Codegen:** `_token_store.py` is in the codegen DENY list with a pre-commit hook
- [ ] **Codegen:** golden input/output files per package
- [ ] **IOL disk persistence (Phase 5):** sentinel-substring caplog test landed BEFORE the persistence code
- [ ] **IOL disk persistence:** disk token DELETED on refresh 401; password fallback writes fresh
- [ ] **IOL disk persistence:** fcntl.flock around the write critical section (POSIX)
- [ ] **IOL disk persistence:** `CI=true` → disk persistence SKIPPED unless `IOL_TOKEN_PATH` explicitly set
- [ ] **IOL disk persistence:** chmod 0600 after write; verified by stat check
- [ ] **`from_env` (Phase 6):** does NOT call `load_dotenv`
- [ ] **`from_env`:** raises typed `<Pkg>AuthError` with clear message listing missing env vars
- [ ] **`from_env`:** env var names preserved (no SDK-style API_KEY aliasing)
- [ ] **`with_options` (Phase 7):** SHARES `_state.http_client` and `_state.token` with the parent
- [ ] **`with_options`:** mutation gate REMAINS authoritative — CRITICAL test for matriz `new_order`
- [ ] **`with_options`:** `max_retries` honored as cap-only for idempotent; ignored for non-idempotent
- [ ] **Live re-verification (Phase 8):** probe-rename count per `main_*.py` == 0 (or migration markers used)
- [ ] **Live re-verification:** all 4 dispositions `no_new_findings` OR each new finding has operator classification
- [ ] **Cross-cutting:** v1.1 baseline (`71bf201`) confirmed green on Python 3.13 BEFORE Phase 1 lands

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| 1 (per-probe Client) | LOW | Refactor driver to top-level `Client()`; AST test asserts the fix |
| 2 (findings regen) | HIGH | Restore from baseline `71bf201`; manually merge new findings; re-apply operator dispositions |
| 4 (B8 identity break) | LOW | Revert codegen template; add identity test as CI gate; re-run codegen |
| 5 (lost by-hand edit) | MEDIUM | Recover from git reflog or PR history; add marker comment + verify-clean CI |
| 7 (token leak in logs) | HIGH | Rotate IOL refresh_token AND password IMMEDIATELY; audit Sentry/Datadog/CloudWatch retention; add caplog sentinel test |
| 8 (stale disk token) | LOW | Delete `~/.config/iol-client/token`; v1.2 code path will write a fresh one on next refresh |
| 9 (multi-process race) | LOW | Set `IOL_TOKEN_PATH` per-process; or accept last-writer-wins (cosmetic churn) |
| 14 (with_options bypasses mutation gate) | HIGH | If duplicate matriz orders detected: manual order reversal at MATBA ROFEX; add CRITICAL regression test; refactor `RetryTransport` to make mutation gate FIRST gate |
| 15 (probe rename breaks LIVE-01) | MEDIUM | Add MIGRATED classification; carry forward operator dispositions by `migrated_from:` marker |
| 17 (3.13 break mis-attributed) | LOW | Bisect against v1.1 baseline `71bf201`; if v1.1 also broken, file as carry-forward |

---

## Sources

- `/Users/sebadlf/development/becerra/market-libs/.planning/PROJECT.md` — v1.2 milestone scope, key decisions, current state, RETROSPECTIVE auto-linked
- `/Users/sebadlf/development/becerra/market-libs/.planning/RETROSPECTIVE.md` — v1.1 What Was Inefficient (driver migration as residual), Patterns Established (PEP 562, `_core.py`, mutation gate, INT-01 idiom), Key Lessons (compat shims have half-life, 3.13 confirmation deferred)
- `/Users/sebadlf/development/becerra/market-libs/.planning/research/v1.0-v1.1-archived/PITFALLS.md` — v1.1 mitigations baseline (assumed in place); Pitfalls 1/4/7/9/10 directly extend v1.1 originals
- `/Users/sebadlf/development/becerra/market-libs/CLAUDE.md` — Anti-Patterns (importing aio in sync, mutating module state without configure, sharing aio state across loops); Architectural Constraints (threading, global state, no shared library, no async in matriz pre-v1.1)
- `/Users/sebadlf/development/becerra/market-libs/packages/iol-client/src/iol_client/client.py` — existing OAuth refresh flow (lines 251-289), B8 identity alias (line 78), max_retries validation (lines 83-99), PEP 562 shim (lines 595-614)
- `/Users/sebadlf/development/becerra/market-libs/main_iol.py` — INT-01 idiom (line 1289); 15+ sites of `_get_default()._state.<attr>` access; CR-03 direct mutation pattern (lines 1421-1429); 1675 LOC current driver size
- [psycopg async-to-sync codegen workflow](https://www.psycopg.org/articles/2024/09/23/async-to-sync/) — pre-commit hook + verify-clean CI check is the mainstream pattern
- [unasyncd marker comment pattern](https://pypi.org/project/unasyncd/) — generated-file marker as deception prevention
- [Django DEP draft: Unasyncify Codegen](https://forum.djangoproject.com/t/dep-draft-request-for-shepherd-unasyncify-codegen/36038) — community discussion of marker comments + pre-commit hooks
- [redis-py issue #2119 — async/sync handling discussion](https://github.com/redis/redis-py/issues/2119) — comparison of sync-from-async strategies in production libraries
- Python data model — module-level `__getattr__` (already in use; v1.2 must preserve)
- httpx documentation — `request.extensions` pattern (already used for `idempotent`, `request_id`, `endpoint_name`; extend for per-call `max_attempts` in Pitfall 13/14)
- [anthropic-sdk-python `_client.py` `with_options()`](https://github.com/anthropics/anthropic-sdk-python) — copy-config-share-http-client pattern

---

*Pitfalls research for: market-libs v1.2 Architecture + Auth/Ergonomics Carry-forwards over shipped v1.1 baseline (29/29 reqs, 907 tests, milestone audit `passed`)*
*Researched: 2026-06-14*
*Confidence: HIGH (rooted in shipped v1.1 architecture + RETROSPECTIVE + existing code at exact line refs; cross-referenced against psycopg/urllib3/elasticsearch-py mainstream codegen practice and anthropic SDK ergonomics)*
