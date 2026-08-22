---
phase: 30-iol-client-tipado
reviewed: 2026-08-22T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - main_iol.py
  - verification/test_main_iol_raw_wire_drift.py
findings:
  critical: 1
  warning: 7
  info: 3
  total: 11
status: issues_found
---

# Phase 30: Code Review Report (re-review after gap-closure 30-08)

**Reviewed:** 2026-08-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Scope: `main_iol.py` and `verification/test_main_iol_raw_wire_drift.py` at HEAD
(`912f651`), with the 30-08 diff (`8ccbb94..912f651`) as the focus. That diff is
tiny in the driver (one `except` branch) and large in the test file (a new
section 9 plus rewrites of two tests).

### Verdict on the three items 30-08 was written to close

| item | claim | verdict |
|---|---|---|
| CR-01 (BLOCKER) | `_capture_raw_wire`'s except branch no longer leaks the upstream body | **Closed at that site, but the vulnerability class is still live at 30 other sites in the same file** — see CR-01 below |
| WR-01 (tautological test) | PASS-detail test now genuinely falsifiable | **Closed.** `expected_checked` is a per-case literal, no longer re-derived from `raw_wire`; `_names_in_pass_detail` hard-fails on a format change instead of degrading to `set()`. One residual gap (WR-04). |
| WR-02 (over-pinning) | `snapshot.status == "PASS"` relaxed to `!= "FINDING"` | **Closed as a test change**, and the skipped-set assertion actually got *stronger* (exact set equality replaced a substring check that had a real `get_instruments` / `get_instruments_by_type` prefix collision). But the defect the relaxation was written to accommodate was never filed — see WR-01 below. |

I verified the except-branch redaction by tracing every `append_finding` kwarg in
that branch: `title`/`expected` interpolate only `func_name` (a literal from a
hardcoded `specs` list), `diff` and `actual` interpolate only
`type(exc).__name__` and `getattr(exc, "status_code", None)`, and `base_url` is
client configuration, not wire. No `repr()`/`str()` of the exception survives.
The five new section-9 tests are genuinely RED against the pre-fix code (the
exact-equality assertion on `actual` cannot pass against
`IOLAPIError('[500] …')`), and the fixtures are offline (`MockTransport`, token
pre-seeded so `_ensure_token` never fires, injected `http_client` so no
`RetryTransport` wrapping and therefore exactly one call per endpoint).

`ruff check`, `ruff format --check`, and `mypy --strict` are clean on both files;
all 22 tests in the drift file pass.

### What the fix missed

The reasoning 30-08 wrote down is correct and general: *`_core.raise_for_response`
puts `resp.text` verbatim into the exception message, and a finding is a durable
git-tracked artifact.* The fix applied that reasoning to exactly one of the 31
places in `main_iol.py` where an exception is stringified into a finding. I
confirmed the leak empirically against the current HEAD (mock 500 with a planted
account-shaped marker, driving three untouched probes):

```
F-01 get_quote_sync recibió APIError inesperado -> LEAKED KWARGS: ['actual']
    actual = IOLAPIError('[500] {"cuenta": "ZZ-CUENTA-9999-ZZ", "detalle": "boom"}')
F-02 get_instruments_sync recibió APIError inesperado -> LEAKED KWARGS: ['actual']
F-03 refresh path causó APIError inesperado -> LEAKED KWARGS: ['actual']
```

`.planning/verification/iol-client-findings.md` is git-tracked (`git ls-files`
confirms), and `append_finding` applies **no** redaction — `safe_print`'s
`secrets` list guards stdout only and never touches the findings file. So the
BLOCKER as a *class* is not closed; it was closed at one address.

## Critical Issues

### CR-01: CR-01's redaction is site-local — 30 other `append_finding` call sites still write the full upstream HTTP error body to a git-tracked file

**File:** `main_iol.py:381, 416, 453, 468, 483, 540, 555, 570, 610, 628, 646, 689, 707, 725, 759, 774, 789, 822, 837, 852, 899, 917, 935, 1024, 1042, 1060, 1572, 1587, 1742`

**Issue:** Every one of those lines is `actual=repr(exc)` inside a probe's
exception handler, and every one of them calls `append_finding`, which writes
`- **Actual:** <value>` verbatim into `.planning/verification/iol-client-findings.md`
(`verification/findings.py:556-566`), a git-tracked file.

`_core.raise_for_response` (`packages/iol-client/src/iol_client/_core.py:114-127`)
constructs `IOLAuthError(resp.status_code, resp.text)` /
`IOLRateLimitError(...)` / `IOLAPIError(...)`, and `IOLAPIError.__init__`
(`exceptions.py:12-16`) does `super().__init__(f"[{status_code}] {message}")`.
So `repr(exc)` **is** the upstream response body, prefixed by the status. This is
the identical mechanism 30-08's own docstring describes, and 30-08's own test
fixture models the risk correctly by planting its marker *"en posición de
cuenta"* — i.e. the plan already knows IOL error bodies carry account
identifiers.

Empirically confirmed at HEAD (script above): `probe_get_quote_sync`,
`probe_get_instruments_sync` and `probe_refresh_token` all emit findings whose
`actual` contains the entire 500 body. `probe_refresh_token` (line 1587) is the
worst instance: it fires after a deliberately forced token expiry on a real
authenticated call. `probe_auth_401` (line 1742) is the second worst: its
handler runs immediately after a login attempt made with
`IOL_PASSWORD + "_INVALID"`, so whatever the token endpoint echoes back lands in
git unredacted — and unlike the stdout path, no `secrets` list is consulted.

None of these are hypothetical branches: they are the ordinary failure path of a
live verification run against a third-party API whose availability the project
charter explicitly calls unreliable.

**Fix:** Extract the redaction that 30-08 wrote inline and apply it at every
site, so the invariant is one function rather than 31 independent decisions:

```python
def _redacted_exc(exc: BaseException) -> str:
    """Clase + status code, jamás el mensaje (que carga el body upstream).

    T-30-08-01 / T-29-36. Único renderizador de excepciones permitido en un
    argumento de ``append_finding``.
    """
    return f"{type(exc).__name__} status_code={getattr(exc, 'status_code', None)!r}"
```

then replace `actual=repr(exc)` with `actual=_redacted_exc(exc)` at all 29 sites,
and `_auth_failure_reason = f"sync login: {exc}"` (lines 371, 406) with
`_redacted_exc(exc)` (see WR-02). Add a lint-level lock so the pattern cannot
come back — a test that greps the driver source is enough and is cheap:

```python
def test_no_probe_stringifies_an_exception_into_a_finding() -> None:
    src = Path(main_iol.__file__).read_text(encoding="utf-8")
    offenders = [
        i for i, line in enumerate(src.splitlines(), 1)
        if re.search(r"(repr\(exc\)|str\(exc\)|\{exc\})", line)
    ]
    assert offenders == [], f"exception stringified into a finding at lines {offenders}"
```

Alternatively (defence in depth, and the more robust option): make
`verification.findings.append_finding` reject any argument value that is not
already redacted — e.g. refuse values matching the exception-repr shape — so the
guarantee holds for the other four `main_*.py` drivers too rather than only for
this one.

## Warnings

### WR-01: `probe_schema_snapshot` reports PASS when every wire capture failed — the test file documents the defect but nobody filed it

**File:** `main_iol.py:1477-1524` (probe), `main_iol.py:1901-1907` (call site),
`verification/test_main_iol_raw_wire_drift.py:528-537` (the acknowledgement)

**Issue:** Probe 13 receives `raw_wire` but **not** `capture_fids`, unlike probe
12 (`main_iol.py:1180`, "Anti-vacuidad (T-30-06-05)"). When all four captures
raise, `raw_wire == {}`, every target takes the `skipped` branch, `finding_fids`
stays empty, and the probe returns
`ProbeResult("schema_snapshot", "PASS", "written=[] matched=[] skipped=[…]")`.
`main()` then counts that toward `n_pass` in the SUMMARY line. A probe that
inspected nothing reports success — the exact failure mode T-30-06-05 was
written to eliminate, present in the sibling probe.

The rewritten WR-02 test comment names this precisely ("un defecto separado y
todavía abierto") and deliberately weakens its assertion to avoid cementing it.
Weakening the test was the right call; leaving the defect unrecorded outside a
test comment was not — a comment in a test file is not a tracked defect.

**Fix:** Thread the seed the same way probe 12 does:

```python
def probe_schema_snapshot(
    client: Client, today: dt.date, raw_wire: dict[str, Any], capture_fids: list[str]
) -> ProbeResult:
    ...
    finding_fids: list[str] = list(capture_fids)   # anti-vacuidad, espejo del probe 12
```

and at the call site `probe_schema_snapshot(client, today, raw_wire, capture_fids)`.
Then tighten the test back to `== "FINDING"` for the total-capture-failure case
and keep `!= "FINDING"` only for the genuinely-empty-input case.

### WR-02: the login cascade reason embeds the upstream 401 body and is printed for every downstream probe

**File:** `main_iol.py:371, 406` (assignment); `437, 524, 590, 669, 743, 806, 882, 1003, 1100, 1177, 1449, 1535, 1679` (consumers); `1934` (sink)

**Issue:** `_auth_failure_reason = f"sync login: {exc}"` renders
`str(IOLAuthError)` = `[401] <full token-endpoint response body>`. That string is
interpolated into `ProbeResult.detail` for **every** downstream SKIPPED probe and
printed by `safe_print` at line 1934. `safe_print`
(`verification/redaction.py:43-61`) replaces only the enumerated `secrets`
(`IOL_USER`, `IOL_PASSWORD`, the cached refresh token) and masks
`Bearer <token>`; an arbitrary error body containing account identifiers or an
`error_description` echoing submitted data passes through untouched, once per
skipped probe, into terminal output and CI logs.

Less severe than CR-01 (stdout, not a versioned artifact) but the same root
cause, in the same file, untouched by 30-08.

**Fix:**

```python
_auth_failure_reason = f"sync login: {_redacted_exc(exc)}"
```

(same helper as CR-01), mirrored at line 406 for the async surface.

### WR-03: the redaction destroys the only actionable content of `IOLDecodeError`, which was already wire-safe by construction

**File:** `main_iol.py:336, 346`

**Issue:** The new `actual` is `f"{type(exc).__name__} status_code={status_code!r}"`.
For an `IOLDecodeError` — a live possibility here, since `_capture_raw_wire`
calls `client._request` which binds strict-decode state — that renders exactly
`IOLDecodeError status_code=None`, and the operator receives a durable OPEN
finding with no way to reproduce, triage, or close it.

`IOLDecodeError` carries `field_path`, `declared_type`, `observed_type` and
`model`, and its own docstring
(`packages/iol-client/src/iol_client/exceptions.py:41-46`) states these are
"tipos y rutas, **jamás** un valor del wire" — i.e. this is the one exception
class the T-29-36 rule already declares safe to report in full. The blanket
redaction over-applies to it. (In practice `_capture_raw_wire` runs no parser, so
this is a latent rather than an everyday path — but the handler is `except
Exception` and claims to cover it, and the comment at line 335 names
`IOLDecodeError` explicitly.)

**Fix:** Special-case the class whose attributes are contractually type-only:

```python
if isinstance(exc, IOLDecodeError):
    actual = (
        f"IOLDecodeError model={exc.model} path={exc.field_path} "
        f"declared={exc.declared_type} observed={exc.observed_type}"
    )
else:
    actual = f"{type(exc).__name__} status_code={getattr(exc, 'status_code', None)!r}"
```

### WR-04: the PASS-detail parser never checks the count, which is the number an operator actually reads

**File:** `verification/test_main_iol_raw_wire_drift.py:548-560, 583-613`

**Issue:** `_names_in_pass_detail` captures `(\d+)` in group 1 and then discards
it, returning only the parsed name set. `probe_field_type_map` renders both
(`main_iol.py:1383`: `f"{len(checked)} endpoints checked ({...}), no drift"`).
A regression that decoupled the count from the list — e.g.
`"3 endpoints checked (get_quote), no drift"` — passes every case in the
parametrization. Since the stated purpose of the WR-01 rewrite is that the PASS
detail is *truthful*, leaving the numeral unasserted reintroduces a slice of the
tautology the rewrite removed.

Secondary: `(.*)` in the pattern is greedy and unanchored within the group, so a
future endpoint name containing `), no drift` would silently mis-parse. Low risk,
but `([^)]*)` costs nothing.

**Fix:**

```python
match = re.fullmatch(r"(\d+) endpoints checked \(([^)]*)\), no drift", detail)
assert match is not None, f"el detalle no matchea el formato esperado: {detail!r}"
names = set() if match.group(2) == "ninguno" else set(match.group(2).split(", "))
assert int(match.group(1)) == len(names), (
    f"el conteo del detalle no coincide con los nombres: {detail!r}"
)
return names
```

### WR-05: `probe_get_quote_sync` writes a raw wire value into a durable finding, contradicting the discipline the same file asserts

**File:** `main_iol.py:507`

**Issue:** `actual=f"ultimoPrecio={ultimo!r}"` puts a value read straight off the
wire into the git-tracked findings file. The file's own stated rule
(`main_iol.py:265-272`, and T-29-36) is "tipos y rutas, jamás un valor del wire".
A closing price for GGAL is public data, so the exposure is small — but the rule
this violates is precisely the one 30-08 was written to enforce, and an exception
carved out by convenience rather than by contract is how the rule erodes. The
neighbouring `bad_types` finding (line 979) shows the disciplined form: it
reports type names only.

**Fix:** Report the classification rather than the value; the bound is already in
`expected`:

```python
actual=f"ultimoPrecio fuera de bounds (magnitud={'0 o negativo' if ultimo <= _PRICE_MIN else 'excede _PRICE_MAX'})",
```

or, if the numeral is genuinely needed for triage, state that decision explicitly
in the docstring as a scoped exception to T-29-36 instead of leaving it silent.

### WR-06: `getattr(exc, "status_code", None)` is duck-typed with no constraint, so `!r` renders whatever it finds

**File:** `main_iol.py:336`

**Issue:** The handler is `except Exception`, so it accepts every exception type
reachable from `client._request` + `resp.json()` — present and future, from
`iol_client`, `httpx`, and the stdlib. The redaction's correctness rests on the
unstated assumption that any object exposing `.status_code` exposes an `int`.
Nothing enforces it; `{status_code!r}` will happily render a string. The two
regression tests pin exactly two classes (`IOLAPIError`, `httpx.ConnectError`),
so the invariant is asserted by example rather than by construction.

Narrow today. It matters because this is the one function in the file that is
supposed to be provably leak-free, and a leak here is durable.

**Fix:**

```python
raw_status = getattr(exc, "status_code", None)
status_code = raw_status if isinstance(raw_status, int) else None
```

### WR-07: the acknowledged `DecodeScope` leak in `_capture_raw_wire` is still untested and its safety argument is order-dependent

**File:** `main_iol.py:318-323, 324`

**Issue:** Each of the four `client._request(spec)` calls binds a fresh
`DecodeScope` (`client.py:460-461`) that no decorated parser ever retires,
because no parser runs inside the capture. The in-code comment states the
correctness argument honestly — it is unreachable *only* because probes 12 and 13
perform no `from_api`, and the next `_request` (probe 14) rebinds — and then
declares it out of scope.

I traced and confirm the argument holds at HEAD: probes 12 and 13 use `schema_of`
exclusively, and `_decode.current_sink()` treats a stale open scope as usable, so
a standalone `from_api` inserted between capture and probe 14 would silently
share one dedupe set across unrelated responses — a false-clean decode, which is
the exact failure mode Phase 29's lock 6 exists to prevent.

The problem is that a correctness argument resting on "no one reorders the
driver" has no enforcement. This diff added five tests to the file and none of
them locks it.

**Fix:** Either retire the scope explicitly in the capture loop:

```python
finally:
    _decode.DECODE_SCOPE.set(None)
```

or add a test that fails if a `from_api` call appears between the
`_capture_raw_wire` call site and the probe-14 call site in `main()`. Retiring
the scope is preferable — it removes the ordering constraint rather than
documenting it.

## Info

### IN-01: `diff` now carries no information not already in `actual`

**File:** `main_iol.py:346-347`

**Issue:** After the fix, `actual=f"{type(exc).__name__} status_code=…"` and
`diff=f"type={type(exc).__name__}"` — `diff` is a strict subset of `actual`. The
tests pin both (`test_capture_failure_finding_reports_only_the_exception_type_and_status_code`
asserts each separately), so the redundancy is now locked in. Two fields that
always agree is a maintenance trap: the next change has to update both or they
diverge silently.

**Fix:** Give `diff` its distinct role — the endpoint whose capture failed and
why it matters downstream, e.g.
`diff=f"{func_name} sin body crudo; probes 12/13 no pueden atestiguar su forma"`.

### IN-02: the marker tests detect one planted string, not "a body leaked"

**File:** `verification/test_main_iol_raw_wire_drift.py:653-655, 681-694`

**Issue:** `_offending_kwargs` searches for `_WIRE_BODY_MARKER` only. The
synthetic error body also contains `"detalle": "boom"`; a partial leak that
emitted only that substring would pass the marker tests. The exact-equality
assertion in `test_capture_failure_finding_reports_only_the_exception_type_and_status_code`
does close this hole — but only for `actual`, and only for the 500 case; the
`ConnectError` test and the partial-failure test rely on the marker alone.

**Fix:** Plant the marker in every field of the synthetic body (`detalle`,
`mensaje`) rather than in one, so any substring of the body trips the check.

### IN-03: `_clean_body()` runs at import time inside `pytest.param`, so a bad baseline breaks collection rather than one test

**File:** `verification/test_main_iol_raw_wire_drift.py:566-580`

**Issue:** The parametrize list calls `_clean_body()` at module import, which
reads and `json.loads` the committed baseline and indexes `_TYPE_SAMPLES` with no
default. A missing, malformed, or newly-typed baseline raises during collection —
the whole file errors out with a `KeyError`/`FileNotFoundError` traceback instead
of a single named test failure carrying the diagnostic the fixture helpers were
written to provide.

**Fix:** Use `pytest.lazy_fixture`-style indirection or build the bodies inside
the test body from a fixture, so baseline problems surface as a failure in one
test with a readable message.

---

_Reviewed: 2026-08-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
