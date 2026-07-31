---
phase: 23-verificaci-n-en-vivo-contra-develop-fixes
reviewed: 2026-07-30T21:40:29Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - main_market_data.py
  - main_verify.py
  - verification/test_main_market_data_uses_single_client_instance.py
findings:
  critical: 1
  warning: 5
  info: 0
  total: 6
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-07-30T21:40:29Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the 6th verification driver (`main_market_data.py`), the aggregate
runner (`main_verify.py`), and the AST single-Client guard test. The driver is
carefully structured for the D-09 "never crash → never FAILED" contract on the
HTTP path, but the contract has a real hole: **all SHAPE-diff, schema-snapshot,
and finding-emission code runs OUTSIDE each probe's `try/except`**, and those
paths can raise (corrupt committed baseline → `JSONDecodeError`, disk `OSError`,
newline-in-title `ValueError`). An exception there is uncaught all the way up
through `main()` and flips `main_verify` to FAILED — the exact outcome D-09
forbids. This is the one BLOCKER. The remaining findings are robustness/quality:
the AST guard is weaker than its stated invariant, the no-data probe records a
finding on the expected happy path while silently PASSing the anomalous case,
and the per-run fid counter can silently clobber human-promoted findings.

Credential-leak / redaction review is clean: `safe_print(..., secrets=[])` only
prints synthetic detail strings (never raw payloads), `schema_of` is PII-free by
construction (keys+types only), and the Auth0 grant posts the secret in a form
body (not a URL), so `repr(exc)` written to findings does not surface it.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: D-09 never-FAILED contract is broken — post-request processing runs outside the per-probe `try/except`

**File:** `main_market_data.py:346-359` (and every read probe: `362-383`, `385-409`, `412-434`, `437-458`, `461-493`; async mirrors `625-638`, `651-661`, `680-690`, `707-717`, `731-741`, `759-778`)

**Issue:**
Every read probe wraps only the HTTP calls in `try/except Exception` and then
performs SHAPE-diff (`_emit_shape`) and schema-snapshot (`_write_schema_snapshot`)
*after* the `except` block. Both of those helpers can raise, and nothing catches
them:

- `_write_schema_snapshot` at `main_market_data.py:201` calls
  `json.loads(schema_file.read_text(...))` on the committed baseline. A baseline
  that is corrupt, partially written by an interrupted prior run, hand-edited, or
  carrying merge-conflict markers raises `json.JSONDecodeError`.
- `mkdir` / `write_text` / `read_text` (lines 194-201) raise `OSError` on any
  disk/permission problem.
- `append_finding` (called by both helpers) raises `ValueError` if a title ever
  contains `\n`/`\r` (findings.py:573) — a wire field name flowing into the SHAPE
  title (`_emit_shape`, line 263) is server-controlled — and `OSError` on write.

`main()` uses `try: ... finally: with contextlib.suppress(Exception): client.close()`
(lines 908-925) — the `finally` only cleans up; it does **not** catch. Same for
`_async_main` (lines 866-878). So a raise in the post-`except` region propagates:
probe → `main()` → uncaught → traceback → exit code != 0 →
`main_verify._run_driver` returns `"FAILED"` (main_verify.py:79-80). This is
precisely the classification D-09 says market-data-client must NEVER receive.

This is a genuine deviation from the established sibling pattern: in
`main_ambito_financiero.py` the `append_finding` SHAPE emission lives *inside*
the probe `try` block (see main_ambito_financiero.py:155-168), so a failure to
write is still absorbed by the probe's exception ladder.

**Fix:** Move all post-request processing inside the probe's exception isolation,
e.g. wrap the SHAPE-diff + snapshot in the same `try` (or a dedicated nested
guard) so any failure degrades to a finding/SKIP instead of crashing:

```python
try:
    snapshots = client.get_market_data(active=True)
    raw = _raw_via_request_sync(
        client, _core.build_market_data_request(client._state, active=True)
    )
    sample = raw[0] if isinstance(raw, list) and raw else None
    if isinstance(sample, dict):
        _emit_shape(sample, MarketDataSnapshot, "MarketDataSnapshot", "sync", base_url)
        entries = sample.get("entries")
        if isinstance(entries, list) and entries:
            _emit_shape(entries[0], MarketDataEntry, "MarketDataEntry", "sync", base_url)
    _write_schema_snapshot(
        endpoint="/marketdata", client_function="get_market_data",
        raw=raw, base_url=base_url, surface="sync",
    )
except Exception as exc:  # D-09: nothing in the probe may escape
    return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
return ProbeResult(name, "PASS", f"snapshots={len(snapshots)}")
```

Additionally harden `_write_schema_snapshot` so a corrupt committed baseline is
treated as drift/finding rather than an exception (catch `json.JSONDecodeError`
around line 201). As defense-in-depth, wrap the `main()` orchestration body in a
top-level `except Exception` that records a finding and still `sys.exit(0)`, so
the driver can never exit non-zero on an unhandled path.

## Warnings

### WR-01: AST single-Client guard is weaker than the invariant it claims to enforce

**File:** `verification/test_main_market_data_uses_single_client_instance.py:44-55`

**Issue:**
The walker lumps `Client` and `AsyncClient` into one `_CTOR_NAMES` set and
asserts `1 <= len(ctor_sites) <= 2` over the combined count. The docstring claims
it enforces "EXACTLY one sync `Client` + EXACTLY one async `AsyncClient`", but the
assertion accepts any total of 1 or 2. A regressed driver that constructs two
sync `Client()` and zero `AsyncClient()` (count = 2) — or one `Client` twice —
PASSES GREEN despite violating the single-instance-per-surface invariant. The
merge-blocking guard gives false assurance for exactly the failure mode it exists
to catch.

**Fix:** Count per class and assert each is exactly 1:

```python
from collections import Counter
counts = Counter(name for _, name in ctor_sites)
assert counts["Client"] == 1 and counts["AsyncClient"] == 1, (
    f"{_DRIVER} must construct exactly one Client and one AsyncClient: {ctor_sites}"
)
```

### WR-02: `probe_no_data` records a finding on the expected result and silently PASSes the anomalous one

**File:** `main_market_data.py:543-566` (and async mirror `781-804`)

**Issue:**
For the bogus prefix `__no_such_symbol__` the *expected* correct behavior is an
empty list. But the probe emits an OPEN `NO-DATA` finding whenever the list is
empty (line 551 `if not snapshots:`) and returns `PASS` only when snapshots are
non-empty. Two consequences:
1. Every normal run appends a permanent OPEN finding for the happy path, adding
   recurring noise to the ledger.
2. The genuinely anomalous case — develop returning data for a non-existent
   symbol prefix (a real echo/anti-bot/filter bug worth catching) — is silently
   classified `PASS` and never surfaced.

The logic is effectively inverted relative to what a diagnostic should flag.

**Fix:** Treat empty-for-bogus-prefix as `PASS` (correct behavior) and surface
non-empty as the finding:

```python
if snapshots:
    fid = _next_fid()
    append_finding(_PKG, fid=fid, class_="NO-DATA", surface="sync", status="OPEN",
        title=f"prefix inexistente {_NO_DATA_PREFIX!r} devolvió datos",
        expected="lista vacía", actual=f"snapshots={len(snapshots)}",
        diff="server no filtró un prefix inexistente", base_url=base_url)
    return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
return ProbeResult(name, "PASS", "prefix inexistente -> [] (correcto)")
```

### WR-03: `_next_fid()` is per-process and order-dependent — findings can silently clobber each other across runs

**File:** `main_market_data.py:94-101` (usage throughout)

**Issue:**
`_fid_counter` resets to 0 every process and `_next_fid()` assigns `F-01, F-02,
…` in *conditional* emission order (SHAPE only on divergence; NO-DATA/AUTH/
ERROR-MAP only on failures). So `F-01` in run A (a SHAPE finding) and `F-01` in
run B (a NO-DATA crash finding, because a different probe failed first) refer to
different things. `append_finding` dedupes by fid and, if the existing `F-01` was
promoted by a human (CONFIRMED/FIXED/EXPECTED/NO-FIX), it **preserves the old
finding and silently discards the new one** (findings.py:610-612). A real new
divergence can therefore be dropped because its counter value collided with a
prior, unrelated, human-triaged finding — a missed-detection / findings-data-loss
risk. (This matches the sibling `main_ambito_financiero.py` pattern, so it is a
codebase-wide convention, but it is still latent data loss.)

**Fix:** Use content-addressed dedupe (`append_finding(..., idempotent_by_title=True)`,
already supported per findings.py:551-561) or derive stable fids from
`(class_, surface, title)` rather than a run-local sequential counter.

### WR-04: aggregate runner has no per-subprocess timeout — a wedged driver hangs the whole batch

**File:** `main_verify.py:61-66`

**Issue:**
`subprocess.run([...], capture_output=True, text=True, check=False)` has no
`timeout`. The docstring promises the runner "never stops" and always continues
to the next package, but a driver that hangs (e.g. a socket that neither connects
nor resets before any client-side cap, or a probe path without a timeout) blocks
`main_verify` indefinitely, defeating the aggregate guarantee.

**Fix:** Pass a bounded `timeout=` and treat `subprocess.TimeoutExpired` as
`FAILED` (or a dedicated `TIMEOUT`) without stopping the batch:

```python
try:
    result = subprocess.run([...], capture_output=True, text=True,
                            check=False, timeout=600)
except subprocess.TimeoutExpired:
    print("   timeout")
    return "FAILED"
except OSError as exc:
    ...
```

### WR-05: schema-drift SHAPE findings are false-positive-prone on market-variable payloads

**File:** `main_market_data.py:170-216` (via `verification/schema.py:37-39`)

**Issue:**
`schema_of` samples only the first list element. Live market payloads vary
row-to-row (nullable/optional fields present in some rows, absent in others), so
the committed baseline can legitimately differ from a later run's first element,
producing an OPEN `SHAPE` drift finding that reflects sampling variance rather
than a real schema change. Over repeated runs this accumulates noise in the
market-data findings ledger.

**Fix:** Union keys/types across a bounded sample of list elements before
snapshotting/diffing, or document the first-element-sampling limitation and dedupe
drift findings by content (`idempotent_by_title=True`) so variance does not
re-open the same finding each run.

---

_Reviewed: 2026-07-30T21:40:29Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
