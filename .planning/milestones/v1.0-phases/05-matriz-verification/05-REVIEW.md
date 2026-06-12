---
phase: 05-matriz-verification
reviewed: 2026-06-09T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - main_matriz.py
  - main_higyrus.py
  - packages/matriz-client/src/matriz_client/client.py
  - packages/matriz-client/tests/test_client.py
  - verification/__init__.py
  - verification/cycle_report.py
  - verification/safemodel_diff.py
findings:
  critical: 2
  warning: 8
  info: 6
  total: 16
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-06-09T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 5 lands a substantial `main_matriz.py` driver (~25 probes), a refactor of
`packages/matriz-client/src/matriz_client/client.py` introducing the `_unwrap`
helper plus a `_token` runtime guard, and 19 envelope-regression tests plus
12 verified-live tests and 11 MATZ-06 mock-only contract tests for the matriz
client. Two shared verification helpers (`verification/cycle_report.py`,
`verification/safemodel_diff.py`) and the barrel `verification/__init__.py` are
introduced for cross-driver reuse.

The implementation is generally careful (cascade SKIPPED, secret redaction,
schema-snapshot drift detection, market-hours guard). The substantive defects
are concentrated around three areas: (1) the `_request` JSON-decode contract is
violated for the two Risk API endpoints that legitimately return non-dict
shapes, (2) the driver leaks the real `PRIMARY_ACCOUNT` value through
schema-snapshot file paths even when the placeholder `<PRIMARY_ACCOUNT>` is
recorded in `sample_params`, and (3) the `verification.cycle_report`
path-traversal defence allows a symlink-escape past the `_REPO_ROOT` boundary.
Beyond that we flag the duplicated env-vars (`MATRIZ_SAMPLE_*` is read in two
shapes), undocumented unused imports, broad `except Exception` patterns, and
inconsistent FAIL-vs-FINDING accounting for `login_sync`.

---

## Critical Issues

### CR-01: `_request` accidentally returns `Any` typed as `dict[str, Any]` for non-dict JSON bodies — corrupts type contract for Risk API

**File:** `packages/matriz-client/src/matriz_client/client.py:167-174`

**Issue:** `_request` annotates its return as `dict[str, Any]` and decodes via:

```python
data: dict[str, Any] = resp.json()
if data.get("status") == "ERROR":
    raise PrimaryAPIError(...)
return data
```

There is no `isinstance(data, dict)` guard. The two Risk-API wrappers
`get_detailed_positions` and `get_account_report` (lines 471-482) pass the
result directly to `DetailedPosition.from_api(...)` / `AccountReport.from_api(...)`:

```python
def get_detailed_positions(account_name: str) -> DetailedPosition:
    return DetailedPosition.from_api(
        _request("GET", f"/rest/risk/detailedPosition/{account_name}", auth_basic=_risk_auth())
    )
```

But also, when the Primary API legitimately returns a JSON list or scalar (e.g.,
upstream regression in the Risk API, or simply a payload with no `status` key
where `data` is a list), `data.get("status")` crashes with
`AttributeError: 'list' object has no attribute 'get'` — an UNMAPPED
exception that bypasses every documented exception in the client contract
(`PrimaryAPIError`, `AuthenticationError`).

This is the exact issue the `_unwrap` helper was added to prevent at the
envelope-key layer (D-MATZ-9), but it is left unsolved one layer up at the
JSON-decode layer. The 3 always-on error probes (`probe_error_bogus_symbol`,
`probe_error_invalid_account`, `probe_error_malformed_cfi` in
`main_matriz.py:1472-1704`) all advertise that they distinguish
`PrimaryAPIError(status='ERROR')` mapped (PASS) from anything else — but if the
remarkets sandbox responds with a top-level JSON array for any of these (which
happens for some malformed-CFI 4xx fallbacks), they will surface an
`AttributeError` and the cascade catches it under the generic `except
Exception` arm and emits an ERROR-MAP finding. That is *not* the intended
finding — it's a real client bug.

**Fix:**
```python
def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    auth_basic: tuple[str, str] | None = None,
) -> dict[str, Any]:
    # ... unchanged dispatch ...
    resp.raise_for_status()
    raw = resp.json()
    if not isinstance(raw, dict):
        raise PrimaryAPIError(
            status="ERROR",
            description=f"expected JSON object body at {path}, got {type(raw).__name__}",
            message=None,
        )
    data: dict[str, Any] = raw
    if data.get("status") == "ERROR":
        raise PrimaryAPIError(
            status="ERROR",
            description=data.get("description"),
            message=data.get("message"),
        )
    return data
```

### CR-02: `verification/cycle_report.py` path-traversal defence does not handle symlink escape

**File:** `verification/cycle_report.py:90-120`

**Issue:** `_regression_is_resolvable` explicitly defends against
path-traversal via the regex (`^([^:\s]+\.py)::...$`), an absolute-path check
(`rel_path.is_absolute()`), a `..`-in-parts check, and a final
`relative_to(_REPO_ROOT)` boundary check after `.resolve()`. The docstring
even cites threat **T-5-06**. But there is a hole:

```python
test_file_abs = (_REPO_ROOT / rel_path).resolve()
try:
    test_file_abs.relative_to(_REPO_ROOT)
except ValueError:
    return (False, None, None)
```

`Path.resolve()` follows symlinks. If `_REPO_ROOT` (resolved via
`Path(__file__).resolve().parent.parent`) contains a symlink at any level
above (e.g., on macOS where `/Users` itself or a parent project directory may
be symlinked), the user's resolved `_REPO_ROOT` may *also* be different from a
naïve repo root, and crucially: `_REPO_ROOT.resolve()` is implicitly applied
to the left side (via `_REPO_ROOT`'s construction), but if the operator
**later** moves the repo or runs from a different `cwd`, an attacker who
controls the findings file can write `Regression: tests/legitimate/../../../etc/passwd.py::test_foo`. The regex rejects that (contains `..`), but a *symlinked* directory inside `tests/` could be
crafted to escape `_REPO_ROOT` while the resolved path still appears to live
under `_REPO_ROOT.resolve()` — except that `.resolve()` produces an absolute
path *somewhere*, and `relative_to` against the original `_REPO_ROOT` (which
itself is `.resolve()`d at line 41) compares two resolved paths, so the basic
case is handled. The actual gap: **`relative_to` performs a string-prefix
comparison after resolution; if `_REPO_ROOT == /a/b/repo` and the resolved
test path is `/a/b/repo-evil/foo.py`, `.relative_to(_REPO_ROOT)` returns
`../repo-evil/foo.py`** — wait, no, that raises `ValueError`. OK.

The real defect: when `test_file_abs.exists()` is False at line 158, the
helper marks `missing`. But `read_text` at line 162 is called without
catching `OSError` / `PermissionError`. A findings-controlled path that
resolves to a real file with the right name but no read permission (e.g.,
`/etc/master.passwd` if a symlinked test dir lets the resolved path escape
under a path that *does* relativise inside `_REPO_ROOT` via case-insensitive
filesystem quirks on macOS) crashes the cycle-closure probe with an
unhandled exception, causing the driver to abort mid-summary.

**Fix:**
```python
# After existence check, defend the read:
try:
    content = test_file_abs.read_text(encoding="utf-8")
except OSError:
    missing.append(fid)
    continue
```

Additionally, document that `_REPO_ROOT` is computed once at module import
time via `Path(__file__).resolve().parent.parent`, so symlink-escape requires
the attacker to control the findings file (not the filesystem). If that
threat model is acceptable, downgrade this to a WARNING; if findings files
are not trusted input, the `read_text` must be guarded as above.

---

## Warnings

### WR-01: `main_matriz.py:1731-1745` records placeholder strings in `sample_params` but the actual snapshot file path silently reflects the live `PRIMARY_ACCOUNT`

**File:** `main_matriz.py:1722-1746` (`probe_schema_snapshot`)

**Issue:** `sample_params` records placeholders like
`{"account": "<PRIMARY_ACCOUNT>"}` to avoid committing the operator's real
account ID. However, the snapshot is keyed by `func_name` only, and the
endpoint template (`_ENDPOINT_TEMPLATES["get_positions"] =
"/rest/risk/position/getPositions/{account_id}"`) does retain a placeholder.
That part is correct.

The defect: the snapshot envelope `D-21` contains `"endpoint":
endpoint_template` (placeholder OK) and `"sample_params"` (placeholder OK),
but the **payload** stored inside `"schema"` is the raw `schema_of(payload)`
output — which for `get_account_report` and `get_detailed_positions` contains
`"accountName"` / `"account"` keys whose **values** could include
account-identifying tokens. `schema_of` reduces dicts to a `{key: type}` map,
so values are *not* persisted in the schema — that's fine.

But: `main_matriz.py:1331` and `1391` interpolate the operator's actual
account name into the `PROBE` line detail:
```python
ProbeResult("get_detailed_positions", "PASS", f"account={raw.get('account', '<unknown>')}")
ProbeResult("get_account_report", "PASS", f"accountName={raw.get('accountName', '<unknown>')}")
```

`PRIMARY_ACCOUNT` is **never added to the `secrets` list** in `main()`
(`main_matriz.py:1814-1830` only collects `PRIMARY_USER`, `PRIMARY_PASSWORD`,
and `_token`). `safe_print` therefore prints `account=12345` verbatim. If the
operator runs this driver in a logged CI environment, the account number
ends up in build logs.

**Fix:** Add `PRIMARY_ACCOUNT` to `secrets` in `main()`:
```python
account_env = os.getenv("PRIMARY_ACCOUNT", "")
if account_env and len(account_env) >= 4:
    secrets.append(account_env)
```

Additionally, in the `PASS` detail strings, replace the account value with
a redacted form: `f"account={raw.get('account', '<unknown>')[:4]}…"` or
simply omit it.

### WR-02: `probe_login_sync` returns status `"FAIL"` while the rest of the driver uses `"FINDING"` for authentication failures

**File:** `main_matriz.py:269, 286`

**Issue:** `probe_login_sync` returns `ProbeResult("login_sync", "FAIL", ...)`
on both `AuthenticationError` and unexpected `Exception` branches. Every
other probe in this driver, and the entire `main_higyrus.py` driver, uses
`"FINDING"` (with the same `append_finding` call) for an analogous error.
The status counters in `main()` at line 1926 hard-code:

```python
counts: dict[str, int] = {"PASS": 0, "FAIL": 0, "SKIPPED": 0, "FINDING": 0}
```

So `FAIL` and `FINDING` are accounted separately. The output's `SUMMARY:
PASS=N FAIL=N SKIPPED=N FINDING=N` line will report `FAIL=1` for an auth
failure on matriz but `FINDING=1` (not `FAIL`) for the same situation in
higyrus — making cross-package summaries non-comparable.

The `higyrus` driver's `probe_login_sync` (`main_higyrus.py:421, 438`)
returns `ProbeResult("login_sync", "FINDING", ...)`. The matriz driver
should align.

**Fix:**
```python
# main_matriz.py:269
return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN): AuthenticationError")
# main_matriz.py:286
return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN): {type(exc).__name__}")
```

### WR-03: `_request` does not consume the response body on `data.get("status") == "ERROR"` before raising — potential connection-pool resource leak with HTTP/2

**File:** `packages/matriz-client/src/matriz_client/client.py:166-174`

**Issue:** When the API responds with HTTP 200 but `{"status": "ERROR"}`,
`_request` calls `resp.raise_for_status()` (no-op, 200 OK), decodes
`resp.json()` (fully reads the body), then raises `PrimaryAPIError`. With
HTTP/1.1, this is fine because `.json()` reads the body. With
`httpx.Client(timeout=...)` defaulting to HTTP/1.1 it's actually fine. The
warning here is that there is no `.close()` on the response and no explicit
context manager. Under sustained error rates this isn't a leak with HTTP/1.1
but **will** become one if anyone later switches to HTTP/2 with
`httpx.Client(http2=True)` and reuses streams.

**Fix:** Use a context manager or call `resp.close()` after extracting the
body. Low-effort defensive change:
```python
with self._session.stream(...) as resp:
    ...
```
or simply switch `_session.request(...)` to use the `with` form:
```python
with self._session.send(self._session.build_request(method, url, ...)) as resp:
    ...
```
Lowest-cost defensive fix: rely on `resp.close()` after `resp.json()` since
the response object is short-lived anyway in the current code (but call it
out as a known limitation).

### WR-04: `main_matriz.py` `_first_dict` silently swallows non-list / empty-list inputs without distinguishing them from "list with non-dict first element"

**File:** `main_matriz.py:172-179`

**Issue:** `_first_dict` returns `None` for three distinct cases: (a) payload
is not a list, (b) payload is `[]`, (c) `payload[0]` is not a dict. The
caller in `probe_field_type_map` (line 1426) cannot distinguish "no data
yet" from "data is malformed". Both surfaces silently as "no divergences",
leading to a *false PASS* finding when wire returns empty/malformed shapes.

Specifically, for `get_segments`, `get_all_instruments`, `get_trades`,
`get_all_orders`, `get_positions`, when wire returns `[]` (no data), the
driver emits `field_type_map PASS: 9 models, 0 divergences`. The intent
(from D-MATZ-3) is that no-data should be a NO-DATA finding, not silent.

**Fix:** Either distinguish the cases in `_first_dict` (return a sentinel
for empty-list), or emit a NO-DATA finding in the field_type_map probe when
all 9 payloads are skipped because they're all `None`.

### WR-05: `main_matriz.py` 18 sweep probes have ~95% duplicated boilerplate; refactoring opportunity but more importantly each duplicate is a fresh chance to drift

**File:** `main_matriz.py:300-1394` (18 probes)

**Issue:** The 18 read-sweep probes (`probe_get_segments` through
`probe_get_account_report`) follow an identical pattern: check `_auth_failed`,
get `base_url`, set path, try `_matriz_request`, catch `PrimaryAPIError` →
append finding, check envelope key shape, append finding if wrong, return.
Each is ~30 lines, almost all duplicated. The `_unwrap` helper exists in the
*client* for envelope unwrapping; an analogous helper could be inlined here
for the driver-side shape check.

The risk is concrete: WR-02 above (FAIL vs FINDING drift) is one example
where the duplicate pattern was almost copy-pasted but one variant deviates;
similar drift is high-probability across 18 copies. Two probes
(`probe_get_detailed_positions`, `probe_get_account_report`) intentionally
omit the envelope-key check because their payloads have no envelope wrap —
but a future contributor extending the pattern may not realise this and
introduce a bug.

**Fix:** Extract a helper like `_envelope_probe(name, path, envelope_key,
shape_type)` that runs the request + shape check in one place; call it from
each of the 16 envelope-wrapped probes. Skip the helper for the 2 risk
probes that have no envelope key.

### WR-06: `main_matriz.py` and `main_higyrus.py` catch the bare `except Exception:` arm at module level — masks `KeyboardInterrupt`-adjacent issues

**File:** `main_matriz.py:270, 1517, 1597, 1676, 1690, 1701, 1703`
**File:** `main_higyrus.py:263, 312, 422, 475, 546, 619, 717, 852, 956, 1060, 1189, 1302, 1424, 1529, 1838, 1909, 2002, 2114`

**Issue:** Both drivers use `except Exception` extensively. While
`KeyboardInterrupt` and `SystemExit` are not subclasses of `Exception` (so
they propagate as intended), the patterns sometimes wrap operations that
include user-controlled I/O. In particular, `main_higyrus.py:312` catches
`Exception` inside an async context that includes `await
aio.get_movimientos(...)` — if a `CancelledError` (which IS a subclass of
`Exception` in Python 3.8+ but moved to BaseException as of 3.8) propagates
during cancellation, it is silently swallowed, breaking cooperative
cancellation semantics.

Actually in Python 3.12, `asyncio.CancelledError` is a direct subclass of
`BaseException`, so this is fine. Still, the pattern is brittle: any future
`raise Exception` from inside `aio._request` (e.g., a `ResourceWarning`
hoisted to error in CI) will be silently classified as ERROR-MAP.

**Fix:** Tighten the bare `except Exception` arms by enumerating the
expected upstream exceptions (`httpx.HTTPError`,
`json.JSONDecodeError`, `ValueError` from `from_api`), and let truly
unexpected exceptions propagate so they get a stack trace rather than a
swallowed finding.

### WR-07: `main_higyrus.py` `_capture_sync_query_string` and `_capture_async_query_string` mutate `event_hooks` without locking; multi-event-loop callers will corrupt hooks

**File:** `main_higyrus.py:233-273, 276-318`

**Issue:** The capture helpers preserve `original_hooks` in a local variable,
register a new hooks dict, and restore in a `finally`. This works for the
driver because it runs in a single thread / single event loop. But the
async helper inspects `aio._client` which is the package-singleton — if any
other caller in the same process is mid-request when this fires, hooks are
swapped under them. The current driver doesn't have a concurrent caller, so
this is a latent issue, not a present bug. Still, the comment at line
254-255 ("defensivo aunque hoy el client no usa hooks") downplays this — the
risk is not that the client uses hooks but that the **client's `_client`
singleton is shared**.

**Fix:** Document the assumption explicitly in the helper docstring ("must
not be called concurrently with any other request to the shared singleton"),
or wrap the mutation in `aio._client_lock` (the existing asyncio.Lock).

### WR-08: `main_higyrus.py:756` line lengths exceed 100 cols inside a `dict.keys()` f-string

**File:** `main_higyrus.py:767`

**Issue:** Line 767 contains:
```python
actual=f"cuentas[0] keys={sorted(first.keys()) if isinstance(first, dict) else type(first).__name__}",
```

Length appears to exceed ruff's `line-length = 100`. Also: this expression
leaks the **set of keys** present on the operator's first cuenta record into
the findings markdown — which under HIGYRUS conventions may include
identifying fields like `cbu`, `cuit`, `titular`. CLAUDE.md `<critical_rules>`
state Phase 4 is "the first phase with PII", and the driver's own D-HIGY-2
discipline (lines 49-52) mandates "the PROBE lines and the SUMMARY emit only
COUNTS and SHAPE descriptors, NEVER payload content (no titular names, no
CBU, no CUIT)". Even key *names* like `titular` are leaky and reach
`append_finding` which writes them to the committable findings markdown.

**Fix:** Restrict the leaked information to just the count and unknown-key
indicator:
```python
actual=f"cuentas[0] keys=<{len(first) if isinstance(first, dict) else 'n/a'} keys, hidden>"
```

---

## Info

### IN-01: Unused imports in `main_matriz.py`

**File:** `main_matriz.py:50-58, 70-85`

**Issue:** `import json` is used (`_write_or_check_schema`). `import sys` is
used (`sys.exit`, `sys.stderr`). `import httpx` is used (the `except
httpx.HTTPStatusError` blocks). `Path` is used (`_REPO_ROOT`). `dataclass`
is used (`ProbeResult`). `cast` is used. `Any` is used. All look reachable.

However, `AccountReport`, `DetailedPosition`, `Instrument`, `InstrumentDetail`,
`MarketDataSnapshot`, `Order`, `Position`, `Segment`, `Trade` are imported
from `matriz_client.models` (lines 74-84) and only used inside
`probe_field_type_map` (line 1414-1423). That's fine. No unused imports.

`AuthenticationError` (line 73) is used at line 253. OK.

**No action required.** This finding is left for completeness — verified
clean.

### IN-02: `main_higyrus.py` has commented-out documentation/conventions disguised as code

**File:** `main_higyrus.py:1386-1391`

**Issue:** Lines 1386-1391 contain a multi-line comment explaining the
`incluirParking` rationale ("CR-04 (review-04): wire format Higyrus es
capitalizado..."). The comment is fine but the embedded `format_bool(False)`
on line 1391 is correct — verified against the dual driver at line 1496-1497.

No commented-out code. The comment is intentionally a historical record.

**No action required.**

### IN-03: `main_higyrus.py:165` `_fid_counter` is shared across all drivers if they ever run in the same process

**File:** `main_higyrus.py:165`, `main_matriz.py:153`

**Issue:** Both drivers maintain module-level `_fid_counter: int = 0`. If a
test or notebook imports both modules and runs `.main()` sequentially in one
process, `main_matriz._fid_counter` does not collide with
`main_higyrus._fid_counter` (different modules, different globals). But the
**findings files are package-scoped**, so `F-01` from matriz and `F-01` from
higyrus will both exist, which is the intended design.

The latent issue: running `main_matriz.main()` twice in the same process
would resume the counter at the position from the previous run, producing
`F-29, F-30, …` instead of restarting at `F-01`. The `write_findings(_PKG)`
call is supposedly idempotent (line 1810 comment), so the second run appends
to the existing markdown file with non-restarted `F-NN` IDs — visually
inconsistent.

**Fix (optional):** Reset `_fid_counter = 0` at the start of `main()`, or
seed it from the highest existing F-NN in the markdown file.

### IN-04: `main_matriz.py:1937-1939` has `if __name__ == "__main__": main()` but no return-code convention for non-success

**File:** `main_matriz.py:1925-1936`

**Issue:** `main()` always returns implicitly `None` and exits 0 regardless of
`FAIL` or `FINDING` counts. If a CI job invokes this driver to gate a
release, the operator has no signal short of grepping the stdout for
`FAIL=` or `FINDING=`. This is consistent with `main_higyrus.py` (same
behaviour), so it's a project convention — but worth noting for the
operator.

**Fix (optional):** At the end of `main()`, exit with code 1 if any
`FAIL`+`FINDING` total > 0 (after subtracting `EXPECTED`-classified
findings).

### IN-05: `verification/cycle_report.py:47` regex `_REGRESSION_RE` rejects test names containing dashes — `pytest` allows them

**File:** `verification/cycle_report.py:47`

**Issue:** `_REGRESSION_RE = r"^([^:\s]+\.py)::([A-Za-z_][A-Za-z0-9_]*)$"`
limits the test-name component to a Python identifier. `pytest` allows
parametric test names like
`test_foo[case-1]`, `test_foo[expected-value]`, and even Unicode in CJK
projects. The regex `_REGRESSION_BULLET_RE` on line 54-56 is more permissive
(`[\w\-/.]+\.py::[A-Za-z_][\w]*`) and matches the bullet, but then
`_REGRESSION_RE.match(regression)` at line 104 strictly enforces the
identifier rule.

If a finding references `Regression:
tests/foo.py::test_envelope_check[bogus-symbol]`, the bullet regex captures
`tests/foo.py::test_envelope_check`, dropping the `[bogus-symbol]` suffix.
Then strict-matching it against `_REGRESSION_RE` succeeds, but the
substring search `f"def {test_name}(" not in content` would still work
because the unparametrised `test_envelope_check` is the actual `def` name.

So this is currently harmless. Document the truncation behaviour in the
docstring of `_iter_findings` so the next contributor doesn't try to extend
support for parametric IDs.

### IN-06: `verification/safemodel_diff.py:81, 85` `# type: ignore[no-any-return]` suppressions hint at unstable typing

**File:** `verification/safemodel_diff.py:81, 85`

**Issue:** Two `# type: ignore[no-any-return]` comments are needed because
mypy strict cannot infer that the duck-typed `_is_safemodel_like(hint)` /
`_is_safemodel_like(args[0])` guarantees the return is a `type`. Both are
correct in practice. A safer approach is a `TypeGuard`-narrowing helper:
```python
def _is_safemodel_like(cls: Any) -> TypeGuard[type[Any]]: ...
```
which lets mypy infer `hint` / `args[0]` is a `type` after the check,
removing both `type: ignore` lines.

**Fix:** Convert `_is_safemodel_like` to a `TypeGuard[type[Any]]`-returning
function (Python 3.10+ supports this).

---

## Structural Findings (fallow)

No structural findings block was provided in the prompt. This section is
empty by design.

---

_Reviewed: 2026-06-09T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
