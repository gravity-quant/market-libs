---
phase: 04-higyrus-verification
reviewed: 2026-06-07T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - main_higyrus.py
  - packages/higyrus-client/src/higyrus_client/client.py
  - packages/higyrus-client/src/higyrus_client/aio.py
  - packages/higyrus-client/src/higyrus_client/exceptions.py
  - packages/higyrus-client/tests/test_client.py
  - packages/higyrus-client/tests/test_async_client.py
  - packages/higyrus-client/.env.example
findings:
  critical: 4
  warning: 5
  info: 3
  total: 12
status: issues_found
---

# Phase 04: Code Review Report — higyrus-verification

**Reviewed:** 2026-06-07T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Plan 04-04 refactored `_request` in `client.py` and `aio.py` to pre-attach the
query string using `urlencode(clean_params, quote_via=quote, safe="/")`. The
intent (preserve literal `/` in `dd/mm/yyyy` date values so the Higyrus IIS
backend does not reject `%2F` with `400 "formato dd/mm/yyyy"`) is correct, but
the refactor dropped `urllib.parse.urlencode`'s `doseq=True`, which silently
breaks `list[str]` parameters that worked before. `get_listado_cuentas(id_cuenta=[…])`
now sends a single `idCuenta=%5B%27a%27%2C%20%27b%27%5D` blob instead of the
repeated `idCuenta=a&idCuenta=b` query semantics that httpx applied previously.
This regression is mirrored in `aio.py`, untested, and undocumented.

Additionally the new `main_higyrus.py` driver (2241 lines, 18 probes) does not
catch unexpected exceptions from `aio.login()` / `higyrus_client.login()` —
both probes catch only `HigyrusAuthError`, so a 403 / 429 / 500 / network
failure on login propagates out of the probe and aborts the whole driver
before the SUMMARY line is emitted. Probe 13's sync side has the same
exposure (the async side IS wrapped). The driver also issues
`incluirParking="false"` (lowercase) directly through `_request` for probes
11 and 12, contradicting the documented capitalized wire format that the
public `get_posiciones()` uses and that `test_get_posiciones_envia_booleano_capitalizado`
locks down.

Finally, the wire-encoding regression-tests (`test_request_preserves_literal_slash_in_query`
in both test files) use a `re.compile(r"^https://api\.test/api/cuentas/5208/movimientos\?.*")`
matcher that does not verify the unencoded `/` is present in the **path**
the matcher accepts; they only assert that `%2F` is not in the captured
query string. The regression bar is correctly set, but the assertion is
weaker than the test name implies.

## Critical Issues

### CR-01: `_request` regression — `list[str]` query params no longer split into repeated keys

**File:** `packages/higyrus-client/src/higyrus_client/client.py:184` (mirror in `packages/higyrus-client/src/higyrus_client/aio.py:209`)

**Issue:** Plan 04-04 replaced the implicit httpx params encoding with
`query = urlencode(clean_params, quote_via=quote, safe="/")`. The call omits
`doseq=True`, so when a value in `clean_params` is a `list[str]`
(`get_listado_cuentas(id_cuenta=["A","B"])` is the only documented call site
that exercises this), `urllib.parse.urlencode` falls back to
`quote(str(value))` and emits

```text
idCuenta=%5B%27A%27%2C+%27B%27%5D
```

instead of the previously emitted `idCuenta=A&idCuenta=B`. The Higyrus API
will either reject the literal `['A', 'B']` string with a 400 or silently
filter on a non-existent ID — both are wire-incorrect. The regression exists
in sync **and** async, is not exercised by any test, and is not mentioned in
plan 04-04 or its SUMMARY.

**Fix:**

```python
# client.py:184 and aio.py:209
query = urlencode(clean_params, doseq=True, quote_via=quote, safe="/")
```

Add a paired regression test (sync + async) that calls
`get_listado_cuentas(id_cuenta=["A","B"])` and asserts the captured
`request.url.query` contains `idCuenta=A&idCuenta=B` (no `%5B`, no `%27`).

---

### CR-02: `probe_login_sync` / `probe_login_async` only catch `HigyrusAuthError`, leak everything else and crash `main()`

**File:** `main_higyrus.py:427-454` and `main_higyrus.py:457-484`

**Issue:** Both probe wrappers narrowly catch `HigyrusAuthError`. The login
codepath can legitimately raise:

- `HigyrusAuthorizationError` (403, distinct sibling of `HigyrusAuthError` in
  the exception hierarchy — `exceptions.py:51`),
- `HigyrusRateLimitError` (429),
- `HigyrusAPIError` (any other non-2xx mapped by `_raise_for_response`),
- `httpx.HTTPStatusError` (raised by `resp.raise_for_status()` in
  `client.py:116` / `aio.py:128` for 5xx responses that bypass
  `_raise_for_response`),
- `httpx.ConnectError` / `TimeoutException` (transient network failures —
  these are highly plausible against a live broker backend),
- `HigyrusAuthError(status_code=0)` — actually a subclass, **is** caught.

Any of the above propagates past the probe, out of `_async_main` (whose
`finally` only runs `aclose()` and does NOT swallow the exception), out of
`asyncio.run(...)` in `main()`, and crashes the driver before the 18
`PROBE …` lines or the `SUMMARY:` line are emitted. The downstream
findings files are also left half-written. This breaks the cascade SKIPPED
contract documented in the module docstring and in D-HIGY-10.

**Fix:** Widen the catch to the package base class and a generic fallback,
and set `_auth_failed` for every failure mode so the cascade fires:

```python
# main_higyrus.py:435 — sync
try:
    higyrus_client.login()
except HigyrusClientError as exc:  # base class — covers AuthError, AuthorizationError, RateLimit, APIError
    _auth_failed = True
    _auth_failure_reason = f"sync login: {type(exc).__name__}: {exc}"
    ...
except Exception as exc:  # network / transport
    _auth_failed = True
    _auth_failure_reason = f"sync login: unexpected {type(exc).__name__}: {exc}"
    ...
```

Mirror in `probe_login_async` at line 465. Import `HigyrusClientError`.

---

### CR-03: `probe_parity_sync_async` propagates network errors out of `main()`

**File:** `main_higyrus.py:1581`

**Issue:**

```python
sync_q = _capture_sync_query_string(resolved_cuenta, fecha_desde, fecha_hasta)
```

`_capture_sync_query_string` (line 299) only catches `HigyrusAPIError` inside
its body — any `httpx.ConnectError`, `httpx.TimeoutException`, or other
non-API exception escapes through the `finally` (which only restores the
patched method) and propagates into `probe_parity_sync_async`, which has no
guard, then into `main()`. The async sibling **is** wrapped at lines
2072-2077; the sync side is asymmetric and crashes the driver mid-run.

**Fix:** Wrap the call in a generic `try/except Exception` that records the
failure as a SKIPPED probe with reason, mirroring the async wrapper:

```python
# main_higyrus.py:1581
try:
    sync_q = _capture_sync_query_string(resolved_cuenta, fecha_desde, fecha_hasta)
except Exception as exc:
    return ProbeResult(
        "parity_sync_async",
        "SKIPPED",
        f"sync capture failed: {type(exc).__name__}",
    )
```

(Or, more consistently, broaden the `except HigyrusAPIError` inside
`_capture_sync_query_string` to `except Exception` so the helper has the
same contract as its async sibling.)

---

### CR-04: Driver sends `incluirParking="false"` (lowercase), public API + tests require `"False"`

**File:** `main_higyrus.py:1378` and `main_higyrus.py:1480`

**Issue:** Probes 11 and 12 call `_request` directly with
`params={"fecha": ..., "incluirParking": "false"}`. The documented Higyrus
wire format is the capitalized Python `str(bool)` output (`"True"` / `"False"`)
— see `_params.py:42-50` ("Booleans travel as capitalized `"True"` / `"False"`")
and the locked regression `test_get_posiciones_envia_booleano_capitalizado`
(`tests/test_client.py:132-142`) which sends `incluirParking=True` and
asserts `incluirParking=True` in the URL. The driver bypassing the public
function is therefore sending an **invalid bool literal** to the live
Higyrus API. The server may treat unknown `incluirParking` values as
`True` (default), silently producing the wrong dataset and making the probe
report a misleading PASS.

**Fix:** Use the same capitalization the public API uses (and ideally call
the public API directly instead of `_request`):

```python
# main_higyrus.py:1378 and :1480
"incluirParking": "False",
```

Or, preferably:

```python
raw = higyrus_client.client._request(
    "GET",
    f"/api/cuentas/{resolved_cuenta}/posiciones",
    params={
        "fecha": format_date(today),
        "incluirParking": format_bool(False),
    },
)
```

(`format_bool` is already imported via `higyrus_client._params` and would
make the driver self-consistent with the public surface.)

## Warnings

### WR-01: `login()` (sync + async) calls `resp.raise_for_status()` for non-401 errors → leaks `httpx.HTTPStatusError`

**File:** `packages/higyrus-client/src/higyrus_client/client.py:114-116` and `packages/higyrus-client/src/higyrus_client/aio.py:126-128`

**Issue:**

```python
if resp.status_code == 401:
    _raise_for_response(resp)
resp.raise_for_status()
```

Only 401 is funneled through `_raise_for_response`. Any other non-2xx (403,
429, 500, …) escapes as `httpx.HTTPStatusError`, violating the exception
hierarchy contract documented in `exceptions.py` (the package promises that
callers can catch at `HigyrusClientError`). This contributes to CR-02 above
but is independently a defect in the library itself.

**Fix:**

```python
if not resp.is_success:
    _raise_for_response(resp)
```

Remove the explicit `raise_for_status()` call.

---

### WR-02: `_request` accepts `json_body=None` and forwards `json=None` to httpx

**File:** `packages/higyrus-client/src/higyrus_client/client.py:189` and `packages/higyrus-client/src/higyrus_client/aio.py:214`

**Issue:**

```python
resp = _client.request(method, url, json=json_body, headers=...)
```

When `json_body=None`, this is **not** equivalent to omitting `json`. httpx
treats `json=None` as the literal payload `null` (sending
`Content-Type: application/json` with body `null`). For GET endpoints (all
current callers) this happens to be tolerated by the Higyrus backend, but
the wire shape on the GET requests now includes a JSON body. The previous
behaviour (before the refactor that introduced this signature) was to call
`_client.get(...)` which sent no body. This is a wire-format regression
that could trip stricter servers or HTTP middleware.

**Fix:** Conditionally pass `json`:

```python
kwargs: dict[str, Any] = {"headers": {"Authorization": f"Bearer {token}"}}
if json_body is not None:
    kwargs["json"] = json_body
resp = client.request(method, url, **kwargs)
```

Mirror in `aio.py`.

---

### WR-03: Driver's safe-print redaction silently drops short passwords/usernames

**File:** `main_higyrus.py:2138-2140`

**Issue:**

```python
secrets: list[str] = [
    v for v in (os.getenv("HIGYRUS_USER"), os.getenv("HIGYRUS_PASSWORD")) if v and len(v) >= 4
]
```

The `len(v) >= 4` threshold is arbitrary and silent. A short password (e.g.,
`"abc"`) is NEVER added to the redaction list, so it can appear verbatim in
any later `safe_print` output, including in repr(exc) of a HigyrusAuthError
that contains a base64 echo of the credentials. This is also asymmetric
with how Higyrus production passwords are policy-set (no minimum at the
library layer).

**Fix:** Either drop the threshold or apply it ONLY to the username
substring (passwords should always be redacted regardless of length, and a
short-but-real password is the worst case to leave unmasked). Log a stderr
warning when a credential is excluded so the operator can detect the gap.

```python
user = os.getenv("HIGYRUS_USER", "")
password = os.getenv("HIGYRUS_PASSWORD", "")
secrets: list[str] = []
if password:
    secrets.append(password)  # always redact, regardless of length
if user and len(user) >= 4:
    secrets.append(user)
elif user:
    print(f"WARNING: HIGYRUS_USER='{user[:1]}…' too short to redact; check stdout discipline", file=sys.stderr)
```

---

### WR-04: `_async_main` finally-block reads `result_login` only by virtue of try-completion order — fragile to future edits

**File:** `main_higyrus.py:2057-2095`

**Issue:** The `return _AsyncResults(...)` after `finally` references
`result_login`, `result_health`, `result_listado`, `result_movs`, `result_pv`,
`result_pos`, `result_errors`, `async_query`, `async_token_snapshot`. If any
of the probes that currently rely on broad `except Exception` clauses to
return a `ProbeResult` is refactored to raise (or if a new probe is added
without a top-level catch), the finally block runs `aclose()` and the
exception propagates **past** the return, but a future reader who adds a
post-finally fallback may hit `UnboundLocalError` on `result_login`.

The pattern is also inconsistent with how the sync side at `main()` handles
ordering (each probe assigns its result independently and a SKIPPED is
synthesized at presentation time, line 2223-2226). The async wrapper has
no such defensive synthesis.

**Fix:** Initialise every local that the `_AsyncResults` constructor
references BEFORE the `try:`, so a partially-completed run can still
return a partial `_AsyncResults` from a `finally:` reorganisation
without UnboundLocalError. Default to a SKIPPED `ProbeResult` carrying
"(not executed)" detail.

```python
async def _async_main(today, resolved_cuenta):
    sentinel = lambda name: ProbeResult(name, "SKIPPED", "(not executed)")
    result_login = sentinel("login_async")
    result_health = sentinel("get_health_async")
    health_raw: dict[str, Any] | None = None
    result_listado = sentinel("get_listado_cuentas_async")
    listado_raw: list[dict[str, Any]] | None = None
    result_movs = sentinel("get_movimientos_async")
    result_pv = sentinel("get_posicion_valuada_async")
    result_pos = sentinel("get_posiciones_async")
    result_errors = sentinel("errors_envelope_async")
    async_query: str | None = None
    async_token_snapshot: str | None = None
    try:
        ...
```

---

### WR-05: `_capture_sync_query_string` / `_capture_async_query_string` use `# type: ignore[method-assign]` to monkey-patch httpx, racing future httpx versions

**File:** `main_higyrus.py:322,332,359,364`

**Issue:** Both helpers patch `_client.request` on a live `httpx.Client` /
`httpx.AsyncClient` instance. The mypy hints are suppressed, and the patch
relies on httpx routing every `post`/`get`/`request` call through the same
bound method. If httpx ever introduces a different code path (e.g., a
batch API or a separately-bound `send`), the spy will silently miss the
request and `captured["query"]` will stay empty — which `probe_parity_sync_async`
will report as a SKIPPED with "ningún query capturado" without flagging
the silent capture failure.

**Fix:** Prefer httpx's official `event_hooks={"request": [spy]}` API,
which is stable across versions:

```python
def _spy(req: httpx.Request) -> None:
    captured["query"] = req.url.query.decode()

original_hooks = aio._client.event_hooks
aio._client.event_hooks = {"request": [_spy]}
try:
    await aio.get_movimientos(...)
finally:
    aio._client.event_hooks = original_hooks
```

This removes the type-ignore and the assumption that `request` is the
single dispatch point.

## Info

### IN-01: Duplicate logic between `client.py` and `aio.py` makes 04-04's refactor easy to skew

**File:** `packages/higyrus-client/src/higyrus_client/client.py:165-200` and `packages/higyrus-client/src/higyrus_client/aio.py:191-225`

**Issue:** The `_request` body is byte-for-byte identical in the two files
modulo `async/await`. CLAUDE.md acknowledges this duplication as known
debt ("dual sync/async lock-step"). Any fix for CR-01 / WR-01 / WR-02
must therefore be applied to both files, and the test-suite must continue
to mirror. The driver's `probe_parity_sync_async` is the only safeguard
against drift, and it relies on a brittle monkey-patch (see WR-05).

**Fix (longer-term):** Extract a `_compose_request_url(base, path, params)`
helper into `_params.py` (the only module already shared by sync+async)
so the URL-composition logic has a single source of truth. Body/headers
stay duplicated, but the URL bug surface shrinks.

---

### IN-02: `test_request_preserves_literal_slash_in_query` does not assert the path itself is unencoded

**File:** `packages/higyrus-client/tests/test_client.py:320-340` and `packages/higyrus-client/tests/test_async_client.py:249-269`

**Issue:** The matcher

```python
re.compile(r"^https://api\.test/api/cuentas/5208/movimientos\?.*")
```

would match a URL with `%2F` in the **query** portion as long as the
path is intact. The assertions then check the query string for absence
of `%2F`. If a future regression encodes `/` in the path (e.g., in the
`id_cuenta` argument), the test still passes. Tighten the matcher to a
literal URL (no regex) so the path encoding is also locked.

**Fix:**

```python
httpx_mock.add_response(
    url="https://api.test/api/cuentas/5208/movimientos?fechaDesde=08/05/2026&fechaHasta=07/06/2026",
    method="GET",
    json=[],
)
```

(Drop the `re.compile`; rely on pytest-httpx's exact-URL match which
already canonicalises the query order via `httpx.URL`.)

---

### IN-03: `HigyrusAuthorizationError` and `HigyrusAuthError` (and friends) imported but unused in `tests/test_async_client.py`

**File:** `packages/higyrus-client/tests/test_async_client.py:14-17`

**Issue:** The import list includes `HigyrusAuthError`, `HigyrusAuthorizationError`,
`Posicion`, `PosicionValuada` — but `HigyrusAuthError` is only used by
`test_async_request_propaga_auth_error` (line 35) and `HigyrusAuthorizationError`
by `test_async_request_propaga_authorization_error` (line 40). `Posicion`
and `PosicionValuada` are imported but never referenced (the
`test_async_safemodel_from_api_typed_defaults` test creates them via
`Posicion.from_api({})` / `PosicionValuada.from_api({})` — actually they
ARE used). Confirm via ruff `F401`:

```bash
uv run ruff check packages/higyrus-client/tests/test_async_client.py
```

If the CI's `F401` is silent, the rule is configured to permit them via
`__init__.py` re-exports; otherwise this is a real F401.

**Fix:** Drop the unused names; let ruff `F401` enforce.

---

_Reviewed: 2026-06-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
