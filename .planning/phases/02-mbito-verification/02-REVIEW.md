---
phase: 02-mbito-verification
reviewed: 2026-06-05T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - main_ambito_financiero.py
  - packages/ambito-financiero-client/tests/test_async_client.py
  - packages/ambito-financiero-client/tests/test_client.py
  - packages/ambito-financiero-client/tests/test_findings_helper.py
  - verification/__init__.py
  - verification/findings.py
findings:
  critical: 2
  warning: 7
  info: 6
  total: 15
status: issues_found
---

# Phase 02 — mbito-verification: Code Review Report

**Reviewed:** 2026-06-05T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the Phase 2 deliverables: the rewritten live driver `main_ambito_financiero.py`,
the extended `verification/findings.py` (`append_finding` D-10), its barrel re-export,
the unit-test suite for the helper, and the mocked sync/async smoke tests.

High-level posture is solid: probes are well-named, exception handling is local per
probe (D-04), the schema snapshot honors D-25 (no overwrite on drift), and the anti-bot
probe correctly uses `try/finally` for D-15. However adversarial inspection surfaces
two BLOCKERs and several WARNINGs:

1. The findings parser drops free-form text inside the `## Detalle por hallazgo`
   section that does not match the strict bullet regex (titles with backticks,
   multi-line bodies). The `append_finding` round-trip is therefore lossy and can
   silently strip human-promoted Regression notes, contradicting the D-10 invariant
   asserted in `test_append_finding_preserves_human_promoted_status`.
2. The "title" regex on the `### F-NN -- <title>` header line treats `--` as the
   separator. Any title containing `--` (very common for shape findings like
   "expected list -- actual dict") is split silently. Combined with serialization
   only writing the title that comes back from the regex, the round-trip mangles
   titles.

Other notable issues: dead code (unreachable `exc.args[0]` fallback in
`probe_antibot`), tests that no-op silently for some cases, a parity probe whose
`delta` field crashes on non-numeric subtypes, and `aio.aclose()` being mis-coupled
to a sync probe that runs *after* `asyncio.run(...)` returns (so any subsequent
`aio.*` call from a future probe added on top would silently re-open a client and
leak it).

## Critical Issues

### CR-01: `_parse_findings` silently strips unknown content during round-trip — D-10 status preservation invariant is weaker than advertised

**File:** `verification/findings.py:156-286`, `verification/findings.py:289-344`

**Issue:**
`_parse_findings` only captures *known* bullets (`Expected`, `Actual`, `Diff`,
`Regression`). When a human edits the findings file to promote a status to
`CONFIRMED`/`FIXED`/`EXPECTED`/`NO-FIX`, they typically also add prose notes,
links, repro steps, or extra bullets such as:

```markdown
### F-02 -- shape drift
**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `CONFIRMED`

- **Expected:** ...
- **Actual:** ...
- **Diff:** ...
- **Regression:** F-02
- **Notes:** confirmé esto el 2026-06-04 contra prod; ver thread en Slack
- **Repro:** `python main_ambito_financiero.py`

Plain-text paragraph with the triage decision rationale.
```

After the next driver run, `append_finding(... fid="F-02", status="OPEN" ...)`:

1. Detects `status != "OPEN"` in the existing finding (line 408), so it short-circuits.
2. *But still* re-serializes the file via `_serialize_findings` (line 409).
3. `_serialize_findings` only writes Expected/Actual/Diff/(Regression) bullets and
   no prose — every non-matching bullet and every free-form paragraph is lost.

This contradicts the docstring guarantee:
> "si el `fid` existe con status promovido por humano (CONFIRMED/FIXED/EXPECTED/NO-FIX),
> el finding NO se toca".

The finding *body* IS being touched on every re-run. The `test_append_finding_preserves_human_promoted_status`
test (line 100-146) does not catch this because it only edits the **Status** field
in the Index and meta line — it never adds prose, so the round-trip looks lossless.

This is a BLOCKER because Phase 2 will use this helper repeatedly across multiple
live runs and human triage cycles. Any annotations a human adds when promoting a
finding to `CONFIRMED` will be silently erased by the next driver run — exactly
the user trust failure mode D-10 was supposed to prevent.

**Fix:**
Choose one:

(a) **Skip serialization entirely on the preservation path** (minimal change):
```python
if fid in existing and existing[fid].status != "OPEN":
    # Only refresh the ART block in-place; do not re-serialize finding bodies.
    text = _replace_art_block(text, art)  # new helper
    path.write_text(text, encoding="utf-8")
    return path
```

(b) **Preserve raw section bodies** in `_ParsedFile` (carry the original text slice
per finding) and emit it verbatim during serialization when the finding has a
preserved status.

(c) **At minimum**, document that the file is fully owned by the helper after the
first `append_finding` call and that human triage notes must live *outside* the
per-finding sections (e.g., a `## Triage Log` at the bottom that the parser ignores
and the serializer appends verbatim). Add a parser test for this property.

The current behavior plus the misleading docstring is a Tampering risk
(T-2-01 in the threat model) that the implementation does not actually mitigate.

---

### CR-02: `_DETAIL_HEADER_RE` mis-parses any finding title containing `--`

**File:** `verification/findings.py:145`

**Issue:**
```python
_DETAIL_HEADER_RE = re.compile(r"^###\s+(?P<fid>F-[^\s]+)\s+--\s+(?P<title>.*?)\s*$")
```

The literal separator is `--`. Many real finding titles will contain `--`, e.g.,
the very title strings the driver itself generates encourage this — `expected
list[list[str]] -- actual dict`, `UA inválido -- recibió 403`, etc. With
`(?P<title>.*?)\s*$`, the non-greedy quantifier anchored to end-of-line backtracks
to the longest match, so a title `foo -- bar -- baz` is captured whole as the
title. So far so good.

**But the round-trip is still wrong:** on serialization (`_serialize_findings`
line 332), the header is rendered as `### {fid} -- {title}`. On the next parse,
the regex now greedily captures `foo -- bar -- baz` correctly (because of the
end anchor)... *unless* a later prose paragraph happens to start with `### F-NN`
(it won't), so the immediate practical risk is low.

However a real bug exists: **titles containing newlines or stripped whitespace
differ between parse and serialize.** `re.match` on a single line means a title
written with a trailing space gets `\s*$` stripped on parse (line 235:
`.group("title").strip()`). Subsequent serialization writes it without that
whitespace. Combined with CR-01, this is one more lossy step.

More concretely: any title generated by the driver that contains a literal
backtick like `'1.415,00' -> float`, will round-trip through the parser. But
markdown will render the backticks; if a human edits the title to add markdown
formatting that includes `\n`, the parse will silently truncate at the first line.

**Fix:**
Use a more robust separator (e.g., `### F-NN: title` or `### F-NN | title`),
or accept the round-trip lossiness and document the constraint. At minimum,
update the regex to reject titles containing `--`-like separators that conflict,
or pin titles to a single-line invariant with an explicit assertion in
`append_finding` (`assert "\n" not in title`).

Recommended minimal fix:
```python
# In append_finding, before serialization:
if "\n" in title or "\r" in title:
    raise ValueError(f"title must be single-line; got {title!r}")
```

This locks the documented invariant and surfaces silently-corrupting inputs.

## Warnings

### WR-01: `probe_antibot` has dead code — `exc.args[0]` fallback never executes

**File:** `main_ambito_financiero.py:570-573`

**Issue:**
```python
status_code = getattr(exc, "status_code", None)
if status_code is None and exc.args:
    status_code = exc.args[0]
if status_code == 403:
```

`AmbitoFinancieroAPIError.__init__` (the parent of `AuthError`) *always* sets
`self.status_code = status_code` (see
`packages/ambito-financiero-client/src/ambito_financiero_client/exceptions.py:13-16`).
So `getattr(exc, "status_code", None)` *always* returns an int — never `None`.
The fallback branch is unreachable.

Worse, if the fallback ever did execute, it would set `status_code = exc.args[0]`,
which the parent constructor formats as `f"[{status_code}] {message}"` — i.e.,
a `str`, not an `int`. The subsequent `== 403` comparison would then silently be
`False` against `"[403] forbidden"`. So the fallback isn't just dead — it's
incorrect.

**Fix:**
Drop the fallback entirely; rely on the typed attribute:
```python
status_code = exc.status_code
if status_code == 403:
    ...
```

---

### WR-02: `parity_sync_async` crashes when `precio_async` is non-numeric

**File:** `main_ambito_financiero.py:338`

**Issue:**
```python
diff=f"delta={venta_sync - precio_async}",
```

`probe_happy_async` returns `precio_async: float | None`. The function signature
of `probe_parity_sync_async` guards `precio_async is None` (line 303) — good.
But there is **no guard for `precio_async` being a non-finite float** (`nan`,
`inf`) or for `venta_sync == nan`. A `nan` propagates: `venta_sync - precio_async`
becomes `nan`, and `venta_sync != precio_async` evaluates `True` because `nan != nan`,
so the probe correctly fires a finding — but the `delta` is `nan`, which is mildly
misleading rather than buggy.

The actual issue: if `parse_ar_decimal` ever raised inside the `aio` happy path
(it won't easily, but consider a venta `"abc"`), the async probe catches it as a
bare `Exception` and reports `precio=None`. Then parity is `SKIPPED`. That's
correct. So this is mostly latent risk.

**However** a real bug: line 327 compares `if venta_sync != precio_async:` —
this is float equality. With the AR-decimal parser, results like `1415.0` are
exact integers as floats. But if Ámbito's wire ever emits a price like
`"1.415,33"`, both sync and async parse the same string, so equality holds.
Still, a tolerance comparison (`abs(diff) < 1e-6`) is more defensible against
float drift introduced by any future server-side rounding.

**Fix:**
```python
if abs(venta_sync - precio_async) > 1e-6:
    ...
    diff=f"delta={venta_sync - precio_async!r}",
```

---

### WR-03: Driver doubles HTTP traffic per probe — happy probes call `_request` and `get_dollar_banco_nacion` separately

**File:** `main_ambito_financiero.py:144-164` and `main_ambito_financiero.py:226-243`

**Issue:**
Both happy probes make **two HTTP calls** for the same data:
1. `resp = ambito.client._request("GET", path)` to capture `rows`.
2. `precio = ambito.get_dollar_banco_nacion(fecha)` to cross-check the wrapper.

This is wasteful but more importantly it elevates IP-ban risk:
`mercados.ambito.com` is a public scraping target. Every driver run produces
2x sync + 2x async hits = 4 GETs to `dolarnacion/historico-general` plus 1 more
for `probe_no_data`. The threat model (T-2-06) explicitly calls out
"Denial of Service against self / IP-ban" — D-14 mitigates this for `probe_antibot`
but the happy probes did not get the same treatment.

The duplicate request also creates a real correctness gap: the second call could
return a *different* `rows` (e.g., the server just updated). Then `precio`
(from call 2) and `rows[1][2]` (from call 1) reflect different snapshots,
and parity/parse_decimal probes test stale data.

**Fix:**
Parse the captured `rows` once and skip the second call:
```python
resp = ambito.client._request("GET", path)
rows = resp.json()
if not isinstance(rows, list) or len(rows) < 2 or rows[0] != _EXPECTED_HEADER:
    ...
_, _, venta = rows[1]
precio = parse_ar_decimal(venta)
```

That removes the doubled traffic, the stale-data risk, and the dependency on
`get_dollar_banco_nacion` to make the probe meaningful (which is fine: AMB-02
is verified by `probe_parse_decimal_adversarial` already).

---

### WR-04: `_isolate_findings_dir` fixture monkeypatches a module global but `_REPO_ROOT` is also derived from it indirectly

**File:** `packages/ambito-financiero-client/tests/test_findings_helper.py:28-31`

**Issue:**
The fixture does:
```python
monkeypatch.setattr(findings, "_FINDINGS_DIR", tmp_path)
```

This works because `findings_path()` reads `_FINDINGS_DIR` from the module namespace
at call time. **However** the tests rely on `_FINDINGS_DIR` being directly equal to
`tmp_path` — there is no test that exercises path traversal protection
(`pkg = "../etc/passwd"` would happily write outside `tmp_path`).

While `pkg` is hardcoded in real call sites, the helper takes arbitrary `str`. A
future driver that accidentally derives `pkg` from a server response, env var,
or CLI argument could be exploited. The helper has no validation:

```python
def findings_path(pkg: str) -> Path:
    return _FINDINGS_DIR / f"{pkg}-findings.md"
```

`Path("/tmp/foo") / "../../etc/passwd-findings.md"` resolves to
`/etc/passwd-findings.md`.

**Fix:**
Validate `pkg` at the top of `append_finding` / `write_findings`:
```python
if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", pkg):
    raise ValueError(f"invalid pkg slug: {pkg!r}")
```

Add a test asserting `append_finding("../etc/passwd", ...)` raises.

---

### WR-05: `probe_no_data` uses local timezone via `dt.date.today()`; "futura" can be ambiguous near midnight UTC vs AR

**File:** `main_ambito_financiero.py:446-449` and `main_ambito_financiero.py:659`

**Issue:**
```python
today = dt.date.today()  # local tz
...
fecha_futura = today + dt.timedelta(days=60)
```

`dt.date.today()` returns the date in the *local* timezone of the machine running
the driver. The server is in Argentina (UTC-3). A driver run from a CI box in
UTC at 02:00 UTC would see "today" as the UTC day, which is the AR day +0
(03:00 AR is the next day in Buenos Aires *before* this point). Edge case.

More importantly: the schema snapshot's `sample_date: fecha.isoformat()` and the
finding bodies that include dates will differ between machines. Two driver runs
on opposite sides of midnight will emit different `_last_business_day(today)`,
producing schema/findings churn that looks like drift.

**Fix:**
Pin the driver to AR-local or UTC explicitly:
```python
import zoneinfo
today = dt.datetime.now(zoneinfo.ZoneInfo("America/Argentina/Buenos_Aires")).date()
```

This also matches what a financial market participant cares about (AR business days).

---

### WR-06: Schema serialization is non-deterministic for `dict` ordering of input — could spuriously trigger D-25 drift

**File:** `verification/schema.py:36` and `main_ambito_financiero.py:503-520`

**Issue:**
`schema_of` for a `dict` returns `{k: schema_of(v) for k, v in sorted(payload.items())}`.
But the snapshot for Ámbito's endpoint is a `list[list[str]]`, not a dict — so
sorting is irrelevant for this endpoint. **However** the comparison
`committed.get("schema") == actual_schema` uses Python dict equality, which is
order-insensitive (good). And `json.loads(...)` of the committed file returns
dicts in insertion order (Python 3.7+). Then `dict == dict` ignores order. So
this is OK for now.

**But**: when `actual_schema` is the schema of a `list`, the comparison is
list-equality (order-sensitive). The schema reduces lists to
`[schema_of(payload[0])]` — only the first element's type. So
`[{"a": "str"}, {"a": "int"}]` reduces to `[{"a": "str"}]`. Drift in element 2
type is silently masked.

For the Ámbito endpoint specifically (`list[list[str]]`), all elements are
`list[str]`, so this lossy reduction is fine. But the schema_of contract is
documented as "claves + tipos" without warning that **heterogeneous list
elements lose drift detection past index 0**. Future packages reusing this
helper will hit this.

**Fix:**
Either document the heterogeneous-list blind spot explicitly in `schema_of`,
or change the contract to reduce to the *set* of element schemas, e.g.:
```python
seen: list[Any] = []
for item in payload:
    s = schema_of(item)
    if s not in seen:
        seen.append(s)
return seen
```

At minimum, add a docstring warning.

---

### WR-07: `parse_ar_decimal` test mirror in `test_async_client.py` is a sync test in an async-test file

**File:** `packages/ambito-financiero-client/tests/test_async_client.py:63-69`

**Issue:**
```python
def test_async_parse_ar_decimal_formato_real() -> None:
```

Under `pytest-asyncio`'s `asyncio_mode = "auto"`, sync test functions are still
run as sync tests — this is fine functionally, but the name `test_async_*`
misleads readers. The test does not exercise `aio` at all; it tests the shared
`_parsing.py` helper. The docstring acknowledges this ("Duplicación literal del
sync por D-09 — mantiene la simetría exacta..."), but the duplication is brittle:
if the sync test ever diverges, this stays stale.

Also: the autouse `_configure_async` fixture (from conftest.py) is async-only
(it `await`s `aio.aclose()`). When applied to a sync test, pytest-asyncio may
still execute the async fixture via event loop, which causes the autouse fixture
to spin up a loop just to tear down an `aio._client` that was never created.
This is wasteful and could mask test isolation bugs.

**Fix:**
Either delete this duplicate (the sync version covers it) and document the
gap explicitly, or rename it `test_parse_ar_decimal_formato_real_in_async_module`
to clarify intent. Best: convert to an async test that actually exercises the
async surface end-to-end via a mocked response — that would justify its
existence under the "Verified live (Phase 2)" section.

## Info

### IN-01: Module-level mutable `_fid_counter` global makes driver non-reentrant

**File:** `main_ambito_financiero.py:73-80`

**Issue:**
`_fid_counter` is a module-level `int` mutated via `global`. If `main()` is ever
called twice in the same process (e.g., from a notebook), F-IDs continue from
the previous run. Findings from run 2 collide with run 1 in the file, and
because `append_finding` is idempotent by `fid`, this *overwrites* run 1's
OPEN findings with run 2's content (assuming both are OPEN). This contradicts
the "preservation" guarantee at a different level.

**Fix:**
Reset `_fid_counter = 0` at the top of `main()`, or scope the counter to
`main()`'s local state and pass it through (cleaner). Alternative: derive `fid`
from a content hash so re-runs deterministically map to the same `fid`.

---

### IN-02: `probe_happy_sync` SHAPE finding uses `repr(rows)` — can be enormous

**File:** `main_ambito_financiero.py:157`

**Issue:**
```python
actual=f"type={type(rows).__name__}, repr={rows!r}",
```

If `rows` is a large JSON payload (Ámbito could return a long historical series
if the date range expanded), `repr` can be megabytes. The finding markdown ends
up unreadable and the diff helpful for triage is buried.

Same in `probe_happy_async` (line 238).

**Fix:**
Truncate `repr`:
```python
repr_str = repr(rows)
if len(repr_str) > 500:
    repr_str = repr_str[:500] + "...<truncated>"
actual=f"type={type(rows).__name__}, repr={repr_str}",
```

---

### IN-03: `aio.aclose()` in `_async_main`'s `finally` runs even when the only failure mode is the probe's own captured exception

**File:** `main_ambito_financiero.py:642-649`

**Issue:**
```python
async def _async_main(today: dt.date) -> tuple[ProbeResult, float | None]:
    try:
        result, precio_async = await probe_happy_async(today)
    finally:
        await aio.aclose()
    return result, precio_async
```

`probe_happy_async` catches all exceptions internally (line 274 catches `Exception`),
so the `try/finally` is effectively `aclose()` always at the end. The `finally`
adds no value beyond what a simple sequential statement would. It also means
if `aclose()` itself raises (e.g., underlying httpx error during cleanup), the
exception silently bubbles out of `asyncio.run(...)` and crashes the driver —
violating D-04 ("driver continúa todos los probes y exit 0 salvo crash inesperado").

**Fix:**
Wrap `aclose()` in its own try/except to honor D-04:
```python
async def _async_main(...):
    try:
        result, precio_async = await probe_happy_async(today)
        return result, precio_async
    finally:
        try:
            await aio.aclose()
        except Exception:
            pass  # D-04: don't crash the driver during cleanup
```

---

### IN-04: `__all__` in `verification/__init__.py` lists `findings_path` indirectly but it is not exported

**File:** `verification/__init__.py:32-49` and `verification/findings.py:44-51`

**Issue:**
`verification/findings.py` exports `findings_path` in its `__all__`, but the
barrel `verification/__init__.py` does NOT re-export `findings_path`. Tests and
the driver have to import it as `from verification.findings import findings_path`,
bypassing the barrel. Inconsistent with the rest of the API.

**Fix:**
Either remove `findings_path` from `findings.__all__` (it's an internal helper)
or re-export it via the barrel. Be consistent.

---

### IN-05: Test `test_async_request_propaga_auth_error` only asserts the exception type — not the status code

**File:** `packages/ambito-financiero-client/tests/test_async_client.py:22-25` and `packages/ambito-financiero-client/tests/test_client.py:22-25`

**Issue:**
```python
async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="unauthorized")
    with pytest.raises(AmbitoFinancieroAuthError):
        await aio._request("GET", "/anything")
```

The mock returns 401 but the assertion just catches `AmbitoFinancieroAuthError`
(which fires on both 401 and 403). If a future change to `_raise_for_response`
mishandled 403 vs 401, this test still passes. The mocked status code is wasted
test signal.

**Fix:**
```python
with pytest.raises(AmbitoFinancieroAuthError) as excinfo:
    await aio._request("GET", "/anything")
assert excinfo.value.status_code == 401
```

Same pattern for `test_request_propaga_rate_limit`.

---

### IN-06: `probe_schema_snapshot`'s `envelope: dict[str, object]` masks `actual_schema` type information

**File:** `main_ambito_financiero.py:504`

**Issue:**
The annotation `dict[str, object]` weakens mypy's ability to track that
`schema` is `list[list[str]]`-shaped (well, `schema_of(list[list[str]])` =
`[["str"]]`). Subsequent `committed.get("schema") == actual_schema` does the
right thing at runtime but is opaque to readers.

**Fix:**
Define a `TypedDict` for the envelope:
```python
class SchemaEnvelope(TypedDict):
    endpoint: str
    client_function: str
    captured_at: str
    base_url: str
    sample_date: str
    schema: Any
```

Or at least narrow to `dict[str, Any]` (consistent with the project's wire-payload
convention).

---

_Reviewed: 2026-06-05T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
