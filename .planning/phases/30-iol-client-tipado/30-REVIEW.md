---
phase: 30-iol-client-tipado
reviewed: 2026-08-21T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - main_iol.py
  - verification/test_main_iol_raw_wire_drift.py
findings:
  critical: 1
  warning: 10
  info: 0
  total: 11
status: issues_found
---

# Phase 30: Code Review Report (re-review after gap-closure 30-07)

**Reviewed:** 2026-08-21T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Scope: the current state of `main_iol.py` and
`verification/test_main_iol_raw_wire_drift.py`, with emphasis on the 30-07 change
that replaced the `is None` / `payload is None` sentinels in `probe_field_type_map`
and `probe_schema_snapshot` with `key in raw_wire` / `key not in raw_wire`
membership tests.

**The BLOCKER is genuinely fixed, and the fix is correct and complete on the
consumer side.** I traced every branch of both probes:

| input | probe 12 | probe 13 |
|---|---|---|
| key absent | no branch taken, `checked` omits it | `skipped`, no write |
| `None` body | `not isinstance(None, dict/list)` → SHAPE finding | `schema_of(None) == "NoneType"` ≠ baseline → SHAPE finding, no overwrite |
| `[]` / `{}` / scalar | routed to the non-dict / non-list SHAPE branch | compared against baseline |
| dict/list | field-mapped as before | compared as before |

The `elif "get_instruments_by_type" in raw_wire` correctly attaches to
`if isinstance(envelope, dict)`, so "present and non-dict" (including `None`)
reports and "absent" stays silent — no off-by-one, no branch left unreachable.
`checked` and the per-endpoint gates are now the same predicate, so the PASS
detail is truthful by construction.

**Falsification performed, not assumed.** I created a detached worktree at the
diff base, dropped the new test file in, and ran it against the pre-fix driver:
3 of the 5 new tests fail RED there
(`..._treats_captured_null_body_as_shape_defect` ×2 and
`test_a_single_null_bodied_endpoint_is_enough_for_both_probes`), with exactly the
false `PASS` the fix removes. Those three are real regression locks. `ruff check`
and `ruff format --check` are clean on both files; 17/17 tests pass on HEAD.

**What the re-review found:**

- One **BLOCKER** carried over unfixed: `_capture_raw_wire` writes the entire
  unredacted upstream error body into a **git-tracked** findings artifact, while
  its own docstring promises the opposite (`git ls-files` confirms
  `.planning/verification/iol-client-findings.md` is tracked).
- The 5th new test (`..._pass_detail_never_names_an_uncaptured_endpoint`) is
  **tautological** — I proved its assertion holds on the exact pathological
  pre-fix output it claims to prohibit. It cannot go red.
- The 4th new test **codifies a known defect as a desired invariant**: it asserts
  probe 13 returns `PASS` when every capture failed, which is prior WR-01
  (probe 13 has no anti-vacuity seeding). A future fix of WR-01 now breaks a test.
- One **residual null-vs-absent conflation on the producer side**: a `200` with a
  non-JSON/empty body makes `resp.json()` raise inside the capture `try`, so the
  key goes absent and probe 13 *skips* it — the same "endpoint answered but the
  body is degenerate" case the fix addressed, one layer up.
- Prior WR-03/WR-06/WR-08/WR-10 remain open in `main_iol.py` and are re-reported
  because the file is in scope; WR-08 is extended with new evidence
  (`cantidadOperaciones` is `"int"` in one committed baseline and `"float"` in
  another — the drift corpus is value-dependent, so live findings are noise).

---

## Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: `_capture_raw_wire` writes the unredacted upstream error body into a git-tracked artifact

**Severity:** BLOCKER
**File:** `main_iol.py:324-337` (emitter), `main_iol.py:264-265` (the contradicted docstring)

**Issue:**
The capture failure handler reports `actual=repr(exc)`:

```python
        except Exception as exc:
            fid = _next_fid()
            append_finding(
                _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                title=f"captura de wire crudo falló en {func_name}",
                ...
                actual=repr(exc),
```

The exception reaching that handler is built by
`_core.raise_for_response` (`_core.py:122-127`), which passes `resp.text` — the
**entire** error response body — into `IOLAPIError.__init__`, which stores it in
`Exception.args` (`exceptions.py:13-16`). `repr()` therefore embeds the body
verbatim:

```python
>>> repr(IOLAPIError(500, '{"cuenta":"123456","detalle":"..."}'))
'IOLAPIError(\'[500] {"cuenta":"123456","detalle":"..."}\')'
```

`verification.findings.append_finding` (`findings.py:583-598`) performs no
redaction — only `safe_print` redacts, and only for stdout. The string lands
verbatim in `.planning/verification/iol-client-findings.md`, which
`git ls-files .planning/verification/` confirms is **tracked in the repository**.

This contradicts three statements at once:

1. The function's own docstring, `main_iol.py:264-265`: *"el body crudo alimenta
   `schema_of` y nada más. Ningún argumento de `append_finding` recibe un body."*
   The docstring is false about the code directly beneath it.
2. `exceptions.py:40-42` (T-29-36): *"tipos y rutas, **jamás** un valor del wire
   — los payloads de IOL llevan identificadores de cuenta y de instrumento."*
3. CLAUDE.md: *"nunca commitear `.env` ni exponer credenciales en logs, reportes
   o tests."*

This was reported as WR-02 in the prior review and was not addressed by 30-07.
It is classified BLOCKER here rather than WARNING because the sink is a
version-controlled file (exfiltration is permanent and distributed on push, not
transient like stdout), the emitting code path is authenticated against a real
brokerage API, and the failure is silent — nothing in the run signals that a body
was written.

**Fix:** report type and status only, never the message:

```python
        except Exception as exc:
            fid = _next_fid()
            status_code = getattr(exc, "status_code", None)
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title=f"captura de wire crudo falló en {func_name}",
                expected=f"200 OK con el body crudo de {func_name} para schema_of",
                actual=f"{type(exc).__name__} status_code={status_code!r}",
                diff=f"type={type(exc).__name__}",
                base_url=base_url,
            )
```

and add an offline test asserting no `append_finding` argument from this path
contains the response body (feed a mocked `500` with a marker string in the body
and assert the marker appears in no recorded kwarg).

---

### Warnings

#### WR-01: `test_probe_field_type_map_pass_detail_never_names_an_uncaptured_endpoint` is tautological — it cannot fail

**File:** `verification/test_main_iol_raw_wire_drift.py:512-549`; predicate under test at `main_iol.py:1363-1367`

**Issue:** The test asserts

```python
named = [name for name in _FIELD_MAPPED_ENDPOINTS if name in result.detail]
assert all(name in raw_wire for name in named)
```

against a detail string built from

```python
checked = [name for name in ("get_quote", "get_historical_quotes",
                             "get_instruments_by_type") if name in raw_wire]
```

`checked` **is** the membership predicate the test then re-asserts, and no name in
`_FIELD_MAPPED_ENDPOINTS` is a substring of another, so `named == checked ⊆
raw_wire.keys()` holds for every possible input. The only assertion that can fail
is `result.status == "PASS"`.

Its docstring claims otherwise: *"El caso patológico que este invariante prohíbe
es el medido contra el código pre-fix — un PASS nombrando tres endpoints sin haber
inspeccionado ninguno."* I ran that exact case against the pre-fix driver in a
detached worktree:

```
PRE-FIX result: ProbeResult(name='field_type_map', status='PASS',
    detail='3 endpoints checked (get_quote, get_historical_quotes,
             get_instruments_by_type), no drift')
named: ['get_quote', 'get_historical_quotes', 'get_instruments_by_type']
invariant all(name in raw_wire): True
```

The pathological output **satisfies** the invariant. The test does not lock the
regression it names, and none of its four params includes a null body — the input
class the whole fix is about.

**Fix:** assert the stronger property the docstring intends — that a named
endpoint was actually *inspected*, not merely present — by having the probe return
the inspected set, or by asserting equality against the expected set instead of a
subset relation, plus a null-body param:

```python
@pytest.mark.parametrize(
    ("raw_wire", "expected_checked"),
    [
        ({}, set()),
        ({"get_quote": _clean_body()}, {"get_quote"}),
        ({"get_quote": _clean_body(), "get_historical_quotes": []},
         {"get_quote", "get_historical_quotes"}),
        ({"get_instruments": _clean_body()}, set()),   # captured but not field-mapped
    ],
)
def test_pass_detail_names_exactly_the_inspected_endpoints(raw_wire, expected_checked, client):
    result = main_iol.probe_field_type_map(client, raw_wire, [])
    named = {n for n in ("get_quote", "get_historical_quotes",
                         "get_instruments_by_type", "get_instruments")
             if n in result.detail}
    assert named == expected_checked, result.detail
```

Note the added `get_instruments` member: the current `named` comprehension cannot
observe the `id="endpoint_no_field_mapeado"` param's stated intent ("no debe
aparecer nombrado en el detalle") because `get_instruments` is not in
`_FIELD_MAPPED_ENDPOINTS` at all — that param asserts nothing today.

#### WR-02: the new invariant test cements probe 13's false `PASS` on a total capture failure

**File:** `verification/test_main_iol_raw_wire_drift.py:488-509`; defect at `main_iol.py:1424-1428`, `main_iol.py:1508-1512`

**Issue:** `test_absent_capture_is_still_distinguishable_from_a_null_body`
asserts:

```python
snapshot = main_iol.probe_schema_snapshot(client, _TODAY, {})
assert snapshot.status == "PASS", repr(snapshot)
```

`raw_wire == {}` in a live run means **all four captures failed**. Probe 13 has no
`capture_fids` parameter and no anti-vacuity seeding (unlike probe 12,
`main_iol.py:1168`), so it reports `PASS written=[] matched=[] skipped=[...]`
having verified zero snapshots. That was prior WR-01, still open — and 30-07 has
now written it down as a desired invariant, so the recommended fix (thread
`capture_fids` into probe 13, or return `SKIPPED` when `written` and `matched` are
both empty) will make this test fail. A regression lock that pins a known defect
raises the cost of fixing it.

Secondary defect in the same test:

```python
for name in tmp_schema_all:
    assert name in snapshot.detail
```

This is substring matching on a repr, and `"get_instruments"` is a prefix of
`"get_instruments_by_type"` — the exact hazard the sibling test at line 455-460
calls out and defends against with exact set equality. If probe 13 ever skipped
only `get_instruments_by_type`, this loop would still pass for `get_instruments`.

**Fix:** decide the desired probe-13 behavior first. If total capture failure must
not be `PASS`, change the probe and re-point the test at `SKIPPED`:

```python
def probe_schema_snapshot(client, today, raw_wire, capture_fids) -> ProbeResult:
    finding_fids: list[str] = list(capture_fids)
    ...
    if not written and not matched:
        return ProbeResult("schema_snapshot", "SKIPPED", f"sin captura: {skipped!r}")
```

and replace the substring loop with `assert set(...) == set(tmp_schema_all)` over
a parsed skipped list.

#### WR-03: residual null-vs-absent conflation — a non-JSON `200` body is filed as "capture failed"

**File:** `main_iol.py:309-339`

**Issue:** The fix corrected the three consumers, but the producer still collapses
two distinct outcomes into "absent":

```python
        try:
            resp = client._request(spec)
            if resp.is_error:
                _raise_for_response(resp)
            raw_by_endpoint[func_name] = resp.json()      # <-- inside the try
        except Exception as exc:
            ...  # ERROR-MAP finding, key left absent
```

`resp.json()` raises `json.JSONDecodeError` on a `200` with an empty body, an HTML
error page, or a truncated payload. That is *the endpoint answering with a body
outside contract* — a SHAPE defect of exactly the class this harness exists to
catch — but it is filed as `class_="ERROR-MAP"` and the key goes **absent**, so
probe 13 routes it to `skipped` and probe 12 never inspects it. The documented
contract ("ausente = la captura levantó") is honored literally while the semantic
distinction the 30-07 fix restored is lost one layer up.

**Fix:** separate transport failure from decode failure:

```python
        try:
            resp = client._request(spec)
            if resp.is_error:
                _raise_for_response(resp)
        except Exception as exc:
            ...  # ERROR-MAP, key stays absent (transport/status failure)
            continue
        try:
            raw_by_endpoint[func_name] = resp.json()
        except ValueError:
            fid = _next_fid()
            append_finding(
                _PKG, fid=fid, class_="SHAPE", surface="sync", status="OPEN",
                title=f"{func_name} devolvió un cuerpo no-JSON",
                expected="body JSON decodificable",
                actual=f"content_type={resp.headers.get('content-type')!r} len={len(resp.content)}",
                diff="el endpoint contestó, pero el cuerpo no es JSON",
                base_url=base_url,
            )
            capture_fids.append(fid)
```

(Note the `actual=` deliberately carries no body — see CR-01.)

#### WR-04: a degenerate payload silently becomes the new baseline when the file is missing

**File:** `main_iol.py:1397-1404`

**Issue:** `_write_or_check_schema` takes its **write** branch whenever the
baseline file does not exist, records the observed shape as the new reference
truth, and returns `PASS`:

```python
    if not file_path.exists():
        file_path.write_text(json.dumps(envelope, ...) + "\n", encoding="utf-8")
        return ("PASS", f"escrito {file_path.name}")
```

With a null body that writes `"schema": "NoneType"` and reports `PASS` — the
precise failure the fix was meant to eliminate, reachable through a different
door (a new endpoint added to `_SCHEMA_FILES`, a hand-deleted or never-generated
baseline, a fresh `_SCHEMA_DIR`). The test suite is *aware* of this: the
`tmp_schema_all` fixture docstring (lines 218-224) names it as risk T-30-07-03 and
contains it — but only inside the fixture. Production has no equivalent guard.

**Fix:** refuse to seed a baseline from a degenerate observation:

```python
    if not file_path.exists():
        if actual_schema in (None, "NoneType", [], {}):
            fid = _next_fid()
            append_finding(_PKG, fid=fid, class_="SHAPE", surface="both", status="OPEN",
                           title=f"baseline ausente y forma degenerada en {func_name}",
                           expected="una forma poblada para sembrar el baseline",
                           actual=json.dumps(actual_schema, ensure_ascii=False),
                           diff="no se siembra baseline desde un cuerpo nulo/vacío",
                           base_url=base_url)
            return ("FINDING", f"{fid}|{file_path.name}")
        file_path.write_text(...)
```

#### WR-05: `schema_of` types are value-dependent, so live drift findings are unclosable noise

**File:** `main_iol.py:1388` (`_write_or_check_schema`), `main_iol.py:129-135` (`_ASSUMED_*`), via `verification/schema.py:38-39`

**Issue:** `schema_of` returns `type(payload).__name__`, so a JSON number's
declared type depends on whether that particular response happened to carry a
fractional part, and a list's schema depends on whether it happened to be
populated. The committed corpus proves this empirically — the **same field** is
typed differently across two baselines captured from the same API:

```
get-quote.json               : "cantidadOperaciones": "int",  "descripcionTitulo": "str",      "puntas": []
get-instruments-by-type.json : "cantidadOperaciones": "float"
get-historical-quotes.json   : "descripcionTitulo": "NoneType", "puntas": "NoneType"
```

Consequences on every live run:

- Probe 13 emits `Schema drift en <endpoint>` whenever any `float`-recorded field
  arrives as a whole number, whenever an optional field arrives null, and whenever
  a list arrives empty — OPEN findings no upstream change can ever close.
- Probe 12 emits `type drift on ultimoPrecio` for the same reason, because
  `_ASSUMED_QUOTE_FIELDS["ultimoPrecio"] == "float"` while `1234` decodes to
  `int`.

This is the noise class `main_iol.py:120-128` itself argues against (*"ruido que
entrena al operador a ignorar el archivo de findings"*). Prior WR-08 covered only
the empty-list case; the int/float and Optional-null cases are additional and, per
the corpus above, more frequent.

**Fix:** normalize numeric leaves and treat "no sample" as not-comparable before
comparing, e.g. in `_write_or_check_schema`:

```python
def _normalize(schema: Any) -> Any:
    if schema in ("int", "float"):
        return "number"
    if isinstance(schema, dict):
        return {k: _normalize(v) for k, v in schema.items()}
    if isinstance(schema, list):
        return [_normalize(schema[0])] if schema else []
    return schema

if _normalize(committed.get("schema")) == _normalize(actual_schema):
    return ("PASS", f"{file_path.name} sin drift")
```

plus an explicit "empty list / null optional = cardinality, not shape" rule
mirroring `_core.py:403`. If instead the noise is accepted deliberately, say so in
the probe docstring so an operator reads the finding as expected.

#### WR-06: unreachable `is_error` guard in `_capture_raw_wire`, with a comment that states the opposite of the truth

**File:** `main_iol.py:317-321` *(repeat of prior WR-03 — still open)*

**Issue:**

```python
            resp = client._request(spec)
            # ``Client._request`` (D-03) devuelve el response crudo sin levantar;
            # replicamos el raise-on-error del shim module-level legacy.
            if resp.is_error:
                _raise_for_response(resp)
```

`Client._request` (`client.py:485-509`) calls `_raise_for_response(resp)` on every
response and only intercepts `IOLAuthError` for its one re-auth retry, then calls
`_raise_for_response` again. A response that *returns* from `_request` therefore
can never satisfy `resp.is_error`. The guard is dead and the comment asserting
`_request` "devuelve el response crudo sin levantar" is factually wrong — a future
maintainer will trust the comment over the code.

**Fix:** delete the comment and the two guard lines; add one line noting that
`_request` already raises the typed exception the `except Exception` below catches.

#### WR-07: `_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE` is dead, and the backing invariant covers one of the two live dicts

**File:** `main_iol.py:136-138`, `main_iol.py:116-128`; `verification/test_main_iol_raw_wire_drift.py:364-381` *(repeat of prior WR-06 — still open)*

**Issue:** Confirmed by grep across the repo: `_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE`
appears exactly once, at its own definition. Probe 12 hardcodes `"titulos"`
instead, so editing the constant changes nothing.

The comment at `main_iol.py:120-128` states that **every** entry of **these dicts**
must be backed by the committed baseline, and names
`test_assumed_quote_fields_are_all_present_in_committed_baseline` as the offline
enforcer — but that test walks only `_ASSUMED_QUOTE_FIELDS`.
`_ASSUMED_HISTORICAL_FIELDS` (`fechaHora`, `ultimoPrecio`), which probe 12 does
consume at line 1322, is unenforced. It happens to match
`get-historical-quotes.json` today; the gap is what let the deleted `"simbolo"`
entry reach production the first time.

**Fix:** delete the dead constant (or read it in the envelope branch), and
parametrize the invariant over both live dicts:

```python
@pytest.mark.parametrize(
    ("assumed", "baseline_name", "unwrap"),
    [
        (main_iol._ASSUMED_QUOTE_FIELDS, "get-quote.json", lambda s: s),
        (main_iol._ASSUMED_HISTORICAL_FIELDS, "get-historical-quotes.json", lambda s: s[0]),
    ],
)
def test_assumed_fields_are_all_present_in_committed_baseline(assumed, baseline_name, unwrap):
    schema = unwrap(json.loads((_BASELINE_DIR / baseline_name).read_text())["schema"])
    assert not [k for k in assumed if k not in schema]
    assert not {k: (v, schema[k]) for k, v in assumed.items() if schema[k] != v}
```

#### WR-08: in-band string protocol between `_write_or_check_schema` and probe 13

**File:** `main_iol.py:1381-1421` (producer), `main_iol.py:1495-1501` (consumer)

**Issue:** The helper returns `(status, detail)` where `detail` is parsed three
different ad-hoc ways by the caller:

```python
        if status == "FINDING":
            fid, fname = detail.split("|", 1)      # ValueError if the format drifts
        elif detail.startswith("escrito"):          # magic prefix
            written.append(func_name)
        else:                                       # everything else = "matched"
            matched.append(func_name)
```

A human-readable string is doing the work of a return type. Any change to the
`f"escrito {file_path.name}"` wording silently reclassifies writes as matches
(inflating the `matched` list in the PASS detail — the same class of untruthful
detail that T-30-06-05 exists to prevent), and a change to the `|` separator
raises `ValueError` mid-run.

**Fix:** return a small enum/dataclass instead of a parsed string:

```python
@dataclass(frozen=True, slots=True)
class SchemaCheck:
    outcome: str          # "written" | "matched" | "drift"
    fid: str | None
    file_name: str
```

#### WR-09: probe 12's two field-map blocks are copy-paste duplicates inside a ~230-line function

**File:** `main_iol.py:1254-1284` and `main_iol.py:1322-1352`

**Issue:** `probe_field_type_map` spans `main_iol.py:1142-1372`. The `get_quote`
and `get_historical_quotes[0]` field-map loops are structurally identical —
same missing-key branch, same type-drift branch, same five `append_finding`
kwargs — differing only in the observed dict, the assumed dict, and the wording.
Two copies of a rule that must stay in lockstep is exactly how the assumed-field
checks drift apart; the `_ASSUMED_HISTORICAL_FIELDS` enforcement gap in WR-07 is
the same duplication showing up in the test layer.

**Fix:** extract one helper and call it twice:

```python
def _check_assumed(
    observed: dict[str, Any], assumed: dict[str, str], where: str, base_url: str
) -> list[str]:
    fids: list[str] = []
    for key, expected_type in assumed.items():
        if key not in observed:
            ...  # missing-key finding, title f"missing assumed key `{key}` in {where}"
        elif observed[key] != expected_type:
            ...  # type-drift finding, title f"type drift on `{key}` in {where}"
    return fids
```

#### WR-10: probe 12's envelope finding ships a stale source reference describing removed behavior

**File:** `main_iol.py:1194` *(repeat of prior WR-10 — still open)*

**Issue:**

```python
diff="client.py:254 hace data.get('titulos', []) y devuelve [] silenciosamente",
```

committed verbatim into every finding this branch emits. Both halves are wrong:
the code lives at `_core.py:455` (`client.py:254` is inside `_ensure_http_client`),
and post-CR-02 the parser **raises** on a non-dict envelope and on a non-list
`titulos` — only the genuinely-missing-key path still returns `[]`. An operator
reading a live finding is pointed at a silent-degradation bug that no longer
exists, at a line that never contained it.

**Fix:**

```python
diff="_core.py:455 hace raw.get('titulos', []) y devuelve [] cuando la clave falta",
```

---

_Reviewed: 2026-08-21T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
