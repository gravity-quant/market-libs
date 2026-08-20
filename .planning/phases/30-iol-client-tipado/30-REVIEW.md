---
phase: 30-iol-client-tipado
reviewed: 2026-08-20T19:45:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - main_iol.py
  - packages/iol-client/README.md
  - packages/iol-client/src/iol_client/__init__.py
  - packages/iol-client/src/iol_client/_core.py
  - packages/iol-client/src/iol_client/aio.py
  - packages/iol-client/src/iol_client/client.py
  - packages/iol-client/src/iol_client/models.py
  - packages/iol-client/tests/test_async_client.py
  - packages/iol-client/tests/test_client.py
  - packages/iol-client/tests/test_core.py
  - packages/iol-client/tests/test_decode.py
  - packages/iol-client/tests/test_fixture_reaches_production.py
  - packages/iol-client/tests/test_models.py
  - packages/iol-client/tests/test_refresh_token_lifecycle_async.py
  - packages/iol-client/tests/test_refresh_token_lifecycle.py
  - packages/iol-client/tests/test_typed_surface_red.py
  - verification/snapshots/iol-client-surface.txt
  - verification/test_logging_no_token_leak.py
  - verification/test_main_iol_raw_wire_drift.py
  - verification/test_retry_401_reauth.py
  - verification/test_retry_after_cap.py
  - verification/test_sync_async_isolation.py
findings:
  critical: 1
  warning: 10
  info: 0
  total: 11
status: issues_found
---

# Phase 30: Code Review Report (RE-REVIEW after gap closure)

**Reviewed:** 2026-08-20T19:45:00Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

**Both prior BLOCKERs are genuinely fixed, and the fixes are sound on the paths
they cover.**

- **CR-01 (prior)** — `probe_field_type_map` and `probe_schema_snapshot` no
  longer receive `_as_wire(model)`. `_capture_raw_wire()` re-captures the raw
  body of all four endpoints through the real `_core` builders, and both probes
  are now pure functions of that dict. The `get_instruments_by_type` baseline is
  the full envelope (`schema` top-level key is `titulos`), so feeding the raw
  envelope is like-for-like against the committed corpus — verified. `_as_wire`
  now has exactly one call site (`probe_parity_sync_async`), as its docstring
  claims. The three drift classes are detected again; the regression lock in
  `verification/test_main_iol_raw_wire_drift.py` is well-constructed (fixtures
  *derived* from the committed baseline rather than transcribed, plus a canary
  that asserts the projection's blindness so the rationale cannot silently rot).
- **CR-02 (prior)** — the two shape guards in
  `parse_get_instruments_by_type_response` are correct, the message carries the
  type name only, `{}` and `{"titulos": []}` still yield `[]`, and the async test
  proves the guard reaches `aio` through the shared `_core` parser rather than a
  duplicated copy. 251 tests pass, ruff and format are clean.

**The re-review found one new BLOCKER in the replacement code.** The fix
distinguishes "captured" from "not captured" by testing `is None`, but a captured
JSON `null` body *is* `None` — the exact confusion `_capture_raw_wire`'s own
docstring says it exists to prevent ("ausente, no `None`, para que aguas abajo no
se pueda confundir 'no capturado' con 'capturado como null'"). Reproduced: an
upstream returning `200` + `null` on all four endpoints makes probe 12 emit
`PASS — 3 endpoints checked (get_quote, get_historical_quotes,
get_instruments_by_type), no drift` while inspecting none of them, probe 13 emit
`PASS`, and the run produce **zero findings**. That is the same false-clean
signal CR-01 existed to remove, narrowed to the null-body case, and the PASS
detail is now actively false — which is precisely what T-30-06-05 forbids.

Beyond that: probe 13 has no anti-vacuity seeding at all (PASS with zero
snapshots verified); `_capture_raw_wire` writes an unredacted upstream error body
into the committed findings artifact while its docstring asserts the opposite;
the entire CR-01 regression lock is never executed by CI; and `_capture_raw_wire`
itself — the load-bearing new function — has no direct test.

Prior WR-01/WR-03/WR-04/WR-05/WR-07/WR-08 and IN-01/IN-03/IN-04 were re-checked
and are unchanged; per the re-review scope they are not re-reported. Prior IN-02
**is** re-reported (WR-10) because this closure escalated it: the stale text now
describes behavior the same commit removed.

---

## Critical Issues

### CR-01: a captured JSON `null` body is indistinguishable from a failed capture — both drift probes report a false PASS

**Severity:** BLOCKER
**File:** `main_iol.py:307-339` (`_capture_raw_wire` contract), `main_iol.py:1169-1173`, `main_iol.py:1225`, `main_iol.py:1280`, `main_iol.py:1356-1360` (probe 12), `main_iol.py:1463-1468` (probe 13)

**Issue:**
`_capture_raw_wire` stores `raw_by_endpoint[func_name] = resp.json()`. When the
endpoint answers `200` with a JSON `null` body, that stores the Python value
`None` — the same value every downstream consumer uses as its "capture failed"
sentinel:

```python
# main_iol.py:1169-1173, 1225, 1280 — probe 12
quote_raw = raw_wire.get("get_quote")
...
if quote_raw is not None:          # null body -> branch skipped, no finding
envelope: Any = raw_wire.get("get_instruments_by_type")
...
elif envelope is not None:         # null body -> no finding

# main_iol.py:1463-1468 — probe 13
payload = raw_wire.get(func_name)
if payload is None:
    skipped.append(func_name)      # null body -> silently "skipped"
    continue
```

This directly contradicts the contract `_capture_raw_wire` states for itself
(`main_iol.py:240-243`): *"Un endpoint cuya captura levantó queda **ausente** del
dict — ausente, no `None`, para que aguas abajo no se pueda confundir 'no
capturado' con 'capturado como null'."* The producer honors the contract; all
three consumers throw it away by testing `is None` instead of membership.

Worse, probe 12's anti-vacuity detail line uses a *different* predicate than its
own checks:

```python
# main_iol.py:1356-1360
checked = [name for name in (...) if name in raw_wire]
```

`in raw_wire` is true for a null-bodied endpoint, so the PASS message names
endpoints the probe skipped. Reproduced against the real driver:

```
$ raw = {"get_quote": None, "get_historical_quotes": None,
         "get_instruments": None, "get_instruments_by_type": None}
probe 12 -> PASS  '3 endpoints checked (get_quote, get_historical_quotes,
                   get_instruments_by_type), no drift'
probe 13 -> PASS  "written=[] matched=[] skipped=['get_quote', ...]"
findings emitted: 0
```

`schema_of(None) == "NoneType"`, which differs from every committed baseline, so
probe 13 *should* have raised four SHAPE drift findings. It raised none. A `200`
+ `null` body is not exotic for this API family (the same value flows into
`Cotizacion.from_api(None)`, which `_decode.walk_model`'s `non_dict` branch
handles explicitly), and it is exactly the kind of degenerate upstream response a
drift harness exists to catch. The plan's stated rule — *"Un probe cuyo insumo
nunca llegó no atestigua nada"* — is inverted here: the input **did** arrive, and
the probe attests falsely that it checked it.

**Fix:** make the sentinel unambiguous and use membership everywhere, so `None`
is a value like any other:

```python
# main_iol.py — probe 12
if "get_quote" in raw_wire:
    quote_raw = raw_wire["get_quote"]
    if not isinstance(quote_raw, dict):
        ...  # existing non-dict SHAPE finding now also fires for a null body

if "get_instruments_by_type" in raw_wire:
    envelope = raw_wire["get_instruments_by_type"]
    if isinstance(envelope, dict):
        ...
    else:
        ...  # existing "tipo top-level no-dict" finding (drop the `is not None` gate)

checked = [name for name in (...) if name in raw_wire]   # now truthful

# main_iol.py — probe 13
for func_name, sample_params in targets:
    if func_name not in raw_wire:
        skipped.append(func_name)
        continue
    payload = raw_wire[func_name]
    ...
```

Add the null-body case to `verification/test_main_iol_raw_wire_drift.py` as a
fourth drift label — `{"get_quote": None}` must produce a SHAPE finding from both
probes, and probe 12's PASS detail must never name an endpoint it skipped.

---

## Warnings

### WR-01: `probe_schema_snapshot` reports PASS when zero snapshots were verified

**File:** `main_iol.py:1417-1421` (signature), `main_iol.py:1490-1500`

**Issue:** T-30-06-05's anti-vacuity seeding was applied to probe 12
(`finding_fids: list[str] = list(capture_fids)`, `main_iol.py:1168`) but not to
probe 13, which never receives `capture_fids`. With every capture failed
(`raw_wire == {}`) the probe returns:

```
ProbeResult(name='schema_snapshot', status='PASS',
            detail="written=[] matched=[] skipped=['get_quote', 'get_historical_quotes',
                    'get_instruments', 'get_instruments_by_type']")
```

Verified by direct invocation. The same reasoning the plan applied to probe 12
applies verbatim here: a snapshot probe that compared nothing must not report
PASS. In combination with CR-01 the two probes produce a completely clean run
against a completely uninformative capture.

**Fix:** thread `capture_fids` into probe 13 and seed `finding_fids` with it, or
at minimum return `SKIPPED` when `written` and `matched` are both empty:

```python
def probe_schema_snapshot(client, today, raw_wire, capture_fids) -> ProbeResult:
    ...
    finding_fids: list[str] = list(capture_fids)
    ...
    if not written and not matched:
        return ProbeResult("schema_snapshot", "SKIPPED", f"sin captura: {skipped!r}")
```

### WR-02: `_capture_raw_wire` writes the unredacted upstream error body into the committed findings artifact

**File:** `main_iol.py:324-337`

**Issue:** The failure handler emits `actual=repr(exc)`. `_raise_for_response`
constructs `IOLAPIError(resp.status_code, resp.text)`, so the repr embeds the
**entire** error response body:

```python
>>> repr(IOLAPIError(500, '{"cuenta":"123456","detalle":"saldo 1.000.000"}'))
'IOLAPIError(\'[500] {"cuenta":"123456","detalle":"saldo 1.000.000"}\')'
```

`verification.findings.append_finding` performs no redaction (only `safe_print`
does, and only for stdout), so that string lands verbatim in
`.planning/verification/iol-client-findings.md`, a committed artifact. This
contradicts three things at once: the function's own docstring
(`main_iol.py:264-265`, *"el body crudo alimenta `schema_of` y nada más. Ningún
argumento de `append_finding` recibe un body"*), the project's type-not-value
rule for reports (`exceptions.py:40-42`, T-29-36: *"tipos y rutas, **jamás** un
valor del wire — los payloads de IOL llevan identificadores de cuenta"*), and
CLAUDE.md (*"nunca … exponer credenciales en logs, reportes o tests"*).

The rest of the driver uses the same `repr(exc)` pattern, so this is not novel —
but this is the one call site whose docstring explicitly promises otherwise, and
it is new code.

**Fix:** report the type and status only, never the message:

```python
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            append_finding(
                _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                title=f"captura de wire crudo falló en {func_name}",
                expected=f"200 OK con el body crudo de {func_name} para schema_of",
                actual=f"{type(exc).__name__} status_code={status!r}",
                diff=f"type={type(exc).__name__}",
                base_url=base_url,
            )
```

### WR-03: dead `is_error` guard in `_capture_raw_wire`, with a factually wrong comment

**File:** `main_iol.py:317-321`

**Issue:**

```python
resp = client._request(spec)
# ``Client._request`` (D-03) devuelve el response crudo sin levantar;
# replicamos el raise-on-error del shim module-level legacy.
if resp.is_error:
    _raise_for_response(resp)
```

`Client._request` (`client.py:485-509`) calls `_raise_for_response(resp)` on
every response and only catches `IOLAuthError` (to re-auth once, then re-raise).
Every error status therefore raises *inside* `_request`; a returned response can
never satisfy `resp.is_error`. The guard is unreachable and the comment asserting
`_request` "devuelve el response crudo sin levantar" is false. A future reader
maintaining the capture path will trust the comment over the code.

**Fix:** delete both the comment and the guard, and note that `_request` already
raises the typed exception the `except Exception` block below catches. (The
identical dead guard in the legacy shims `client.py:733-734` / `aio.py:747-748`
is pre-existing and out of this scope, but shares the root cause.)

### WR-04: the entire CR-01 regression lock is never executed by CI

**File:** `verification/test_main_iol_raw_wire_drift.py:26-30`

**Issue:** The CI `test` job runs `pytest packages/${{ matrix.package }}`
(`.github/workflows/ci.yml:119-123`), so `verification/` is never collected —
only the root `testpaths` used in a local full-suite run collects it. The seven
tests that are the *only* automated protection for the BLOCKER just fixed
therefore cannot go red in CI. Compounding it, `main_iol.py` is outside mypy's
`files` list (`pyproject.toml:97`, `packages/*/src` only), so the 427 changed
driver lines are neither typechecked nor CI-tested.

The file's docstring acknowledges the gap and declares it out of plan scope —
correct as process, but it leaves a fixed BLOCKER guarded by nothing a merge gate
can observe. That deserves to be recorded as a risk rather than absorbed as a
note.

**Fix:** add a cross-package CI step alongside the existing cross-package
lint-logging job (`ci.yml:42-52`, already documented as *"Cross-package por
naturaleza: NO va al job `test`"*):

```yaml
      - name: harness tests (verification/, cross-package)
        run: uv run pytest verification -q
```

### WR-05: `_capture_raw_wire` — the function the whole fix rests on — has no direct test

**File:** `main_iol.py:237-339`; `verification/test_main_iol_raw_wire_drift.py`

**Issue:** All seven new tests drive `probe_field_type_map` /
`probe_schema_snapshot` with a **synthetic** `raw_wire` dict. Nothing exercises
`_capture_raw_wire` itself, so none of its behaviors are locked:

- that it builds specs via `_core.build_*` (the docstring's stated reason the
  capture cannot mask a builder drift) rather than hardcoded paths;
- that a failing endpoint leaves the key **absent** rather than `None` — the very
  contract CR-01 above shows the consumers break;
- that one endpoint failing does not abort the other three;
- that an `ERROR-MAP` finding is emitted and its fid returned in `capture_fids`;
- that the `get_historical_quotes` window matches probe 13's `sample_params`.

A regression that reintroduced `_as_wire` *inside* `_capture_raw_wire` would be
caught only by test 1 (`..._passes_raw_wire_through_unmodified`), which spies on
`_write_or_check_schema` and never touches the capture path.

**Fix:** add an `httpx_mock`-driven test on `_capture_raw_wire` covering the
4-endpoint happy path (asserting the four request URLs match
`_core.build_*_request(...)` output) and a per-endpoint failure that asserts
`func_name not in raw_by_endpoint` plus one `ERROR-MAP` fid returned.

### WR-06: `_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE` is dead, and the WR-02 backing invariant covers only one of the two live dicts

**File:** `main_iol.py:136-138`; `verification/test_main_iol_raw_wire_drift.py:296-313`

**Issue:** Two defects in the same block:

1. `_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE = {"titulos": "list"}` is never read
   (confirmed by grep: the only occurrence is its own definition). Probe 12
   hardcodes `if "titulos" not in envelope` and the list check instead. A future
   editor changing the constant will change nothing.
2. The comment introducing the block (`main_iol.py:120-128`) says *"**toda**
   entrada de **estos dicts** debe estar sostenida por el baseline committeado"*
   and points at the offline enforcement test — but
   `test_assumed_quote_fields_are_all_present_in_committed_baseline` only walks
   `_ASSUMED_QUOTE_FIELDS`. `_ASSUMED_HISTORICAL_FIELDS` (`fechaHora`,
   `ultimoPrecio`) is unenforced. It happens to be correct against
   `get-historical-quotes.json` today, so this is a coverage gap, not a live
   defect — but it is precisely the gap that let the deleted `"simbolo"` entry
   survive into production the first time.

**Fix:** delete `_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE` (or read it in probe 12),
and parametrize the invariant test over both dicts:

```python
@pytest.mark.parametrize(
    ("assumed", "baseline_name", "unwrap"),
    [
        (main_iol._ASSUMED_QUOTE_FIELDS, "get-quote.json", lambda s: s),
        (main_iol._ASSUMED_HISTORICAL_FIELDS, "get-historical-quotes.json", lambda s: s[0]),
    ],
)
def test_assumed_fields_are_all_present_in_committed_baseline(assumed, baseline_name, unwrap):
    ...
```

### WR-07: `{"titulos": null}` raises while `{}` returns `[]` — undocumented, untested asymmetry in the new guard

**File:** `packages/iol-client/src/iol_client/_core.py:455-459`

**Issue:** `raw.get("titulos", [])` only supplies the default when the key is
**absent**; an explicit JSON `null` yields `None`, which the new value guard
rejects. Reproduced:

```
{"titulos": null}  -> IOLAPIError: [0] shape mismatch: 'titulos' expected list, got NoneType
{}                 -> []
{"titulos": []}    -> []
```

The docstring introduces its enumeration with *"The two behaviors this function
now distinguishes"* and lists exactly two — missing-key-yields-`[]` and
wrong-typed-value-raises. There are three, and the third is the one a reader is
most likely to get wrong, because everywhere else in this package `null` and
`missing` are deliberately collapsed (`_decode._kind_of(None) == "missing"`). It
is also the plausible wire encoding of "no instruments of this type", which makes
it a cardinality signal being treated as a shape defect — the distinction this
same docstring closes on. No test covers it in either direction.

This is not a regression (the pre-guard code raised a bare `TypeError` on the
same input), so WARNING rather than BLOCKER — but the behavior must be chosen
deliberately, stated, and pinned.

**Fix:** decide and encode. If `null` should behave like a missing key:

```python
    titulos = raw.get("titulos") or []
```
(then a `0`/`""`/`False` value degrades too — probably not wanted), or explicitly:

```python
    titulos = raw.get("titulos", [])
    if titulos is None:          # explicit null == absent: no rows, same as missing key
        titulos = []
    if not isinstance(titulos, list):
        raise IOLAPIError(0, f"shape mismatch: 'titulos' expected list, got {type(titulos).__name__}")
```

Either way add the third bullet to the docstring and a test for
`{"titulos": null}` next to the existing string/dict cases in `test_core.py`.

### WR-08: the reworked snapshot probe reports cardinality as drift

**File:** `main_iol.py:1381` (`_write_or_check_schema`), via `verification/schema.py:38-39`

**Issue:** `schema_of([]) == []` while the committed
`get-historical-quotes.json` baseline is `[{...20 keys...}]`. Any live run whose
`get_historical_quotes` window comes back empty — a suspended or delisted symbol,
an extended holiday, an upstream hiccup — emits `Schema drift en
get_historical_quotes` with `expected` = the 20-key schema and `actual` = `[]`,
an OPEN SHAPE finding no upstream change can ever clear. Same for
`get_instruments` if it ever answers `[]`.

This is the exact noise class the same gap-closure commit retired elsewhere
(a5ab7d4, WR-02/WR-06: *"ruido que entrena al operador a ignorar el archivo de
findings"*), and it contradicts the shape-not-cardinality doctrine that
`_core.py:403` and `main_iol.py:947-952` both state. It is behaviorally
pre-existing, but the probe was rewritten in this closure without addressing it.

**Fix:** treat an empty top-level list as "no sample" rather than as a schema, in
`_write_or_check_schema`:

```python
    actual_schema = schema_of(raw_payload)
    if actual_schema == [] and committed_schema_is_a_populated_list:
        return ("PASS", f"{file_path.name} sin muestra (lista vacía) — no comparable")
```

or record the decision explicitly in the probe docstring so the finding is read
as expected noise.

### WR-09: README changelog version does not match the shipped version, and omits the CR-02 behavior change

**File:** `packages/iol-client/README.md` (Changelog); `packages/iol-client/src/iol_client/__init__.py:87`; `packages/iol-client/pyproject.toml:3`

**Issue:** Two documentation defects in the artifact consumers read:

1. The changelog heading is `### v0.3.0` and describes the dict→model break as
   shipped, while both `__version__` and `pyproject.toml` say `"0.2.0"`. The
   release workflow validates the git tag against `pyproject.toml`, so the
   version a consumer can actually install is `0.2.0` — the changelog names a
   release that does not exist. (The prior review recorded `__version__` staying
   at `0.2.0` as *correct*; whichever side is right, the two must agree.)
2. The "Cambio de forma en el listado de instrumentos" section documents only
   `get_instruments` raising. The CR-02 closure added two more raising paths on a
   **different** public function — `get_instruments_by_type` now raises
   `IOLAPIError` for a non-dict envelope and for a non-list `titulos`. That is a
   public behavior change landed in this same release with no changelog entry. A
   consumer with an `except (KeyError, TypeError)` around that call migrates
   incorrectly.

**Fix:** reconcile the heading with `pyproject.toml`/`__version__` (bump both to
`0.3.0`, or retitle the section `### Unreleased`), and add:

> - `get_instruments_by_type` también **levanta** `IOLAPIError` si el cuerpo no
>   es un dict envelope o si `titulos` no es una lista. Un envelope sin la clave
>   `titulos`, y `{"titulos": []}`, siguen devolviendo `[]`.

### WR-10: probe 12's envelope finding ships a stale source reference that now describes removed behavior

**File:** `main_iol.py:1187`

**Issue:**

```python
diff="client.py:254 hace data.get('titulos', []) y devuelve [] silenciosamente",
```

Two things are wrong, and this string is committed verbatim into every finding
the branch emits:

- The cited location is wrong — that code lives at `_core.py:455`;
  `client.py:254` is inside `_ensure_http_client`.
- Post-CR-02 the described behavior no longer exists for the case that matters.
  The parser now **raises** on a non-dict envelope and on a non-list `titulos`;
  only the genuinely-missing-key path still returns `[]`.

This was IN-02 in the prior review and was scoped out, but the same closure that
was scoped to fix CR-02 made the text describe behavior it removed — an operator
reading a live finding is pointed at a silent-degradation bug that has been
fixed. That escalation is why it is re-reported at WARNING.

**Fix:**

```python
diff="_core.py:455 hace raw.get('titulos', []) y devuelve [] cuando la clave falta",
```

---

_Reviewed: 2026-08-20T19:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
