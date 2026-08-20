---
phase: 30-iol-client-tipado
reviewed: 2026-08-20T03:50:27Z
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
  - packages/iol-client/tests/test_refresh_token_lifecycle.py
  - packages/iol-client/tests/test_refresh_token_lifecycle_async.py
  - packages/iol-client/tests/test_typed_surface_red.py
  - verification/snapshots/iol-client-surface.txt
  - verification/test_logging_no_token_leak.py
  - verification/test_retry_401_reauth.py
  - verification/test_retry_after_cap.py
  - verification/test_sync_async_isolation.py
  - packages/iol-client/src/iol_client/_decode.py (read-only context; intactness gate)
findings:
  critical: 2
  warning: 8
  info: 4
  total: 14
status: issues_found
---

# Phase 30: Code Review Report

**Reviewed:** 2026-08-20T03:50:27Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

The typed surface itself is well built. The 16 signature migrations are complete
and consistent across the four axes (method/shim × sync/async), the sync↔async
mirroring is exact, `__version__` correctly stays at `"0.2.0"`, `_decode.py` is
byte-unchanged, no RESPONSE field gained a `Literal`, `mercado`/`plazo` stay
`str`, `from_api(payload)` is preserved, no cross-package imports were added, and
the divergence records are type-not-value (no credential exposure). 237 tests
pass.

The defects are all at the **boundaries** the phase created, and the two most
serious ones are in the same place: the seam between the new typed models and the
verification harness that this whole milestone exists to serve.

The headline finding is CR-01. The `_as_wire()` adapter added to `main_iol.py`
normalizes models back to dicts so `schema_of` keeps working — but it normalizes
them through the model's *declared* shape, which is a constant. The result is
that the DRIFT-01 snapshot probe, whose entire job is detecting divergence
between the client and the live API, now detects **zero of the four drift classes
it detected before this phase**. Verified empirically, not inferred (proof in the
finding). CLAUDE.md's stated Core Value is "cada divergencia entre el cliente y
el servicio en vivo debe ser detectada"; after Phase 30 the driver cannot detect
type drift, added keys, or removed keys on 3 of its 4 endpoints.

CR-02 is a shape-validation gap the phase walked past while explicitly reasoning
about shape validation two functions above it: `parse_get_instruments_by_type_response`
iterates an unvalidated `titulos` value and manufactures N all-default `Titulo`
rows from a string or a dict, and crashes with a bare `AttributeError` on a
top-level list body.

Beyond that: a proven mypy hole in `_parse_list_or_raise` that undercuts TYP-01's
static guarantee at exactly one call boundary, several now-dead assertions in the
driver, silent zeroing of `int`-declared quantity fields, and README changelog
statements that do not match the code.

---

## Critical Issues

### CR-01: `_as_wire()` renders the DRIFT-01 schema-drift probes structurally blind

**File:** `main_iol.py:194-223` (definition); `main_iol.py:1132`, `main_iol.py:1169`, `main_iol.py:1333` (call sites)
**Severity:** BLOCKER

**Issue:**
`_as_wire()` projects a model back to a dict via `SafeModel.to_dict()`
(`dataclasses.asdict`). But by the time a model exists, `_decode.walk_field` has
already forced every non-optional field to its declared type (`POLICY` has
`scalar_passthrough=False`) and discarded every undeclared wire key. `schema_of`
applied to that projection is therefore a **constant function of the model
declaration**, not a function of the wire.

`probe_schema_snapshot` (`main_iol.py:1333`) compares that constant against the
committed 2026-06-06 baselines for `get_quote`, `get_historical_quotes` and
`get_instruments` — 3 of the 4 snapshots. `probe_field_type_map`
(`main_iol.py:1132`, `1169`) does the same for its assumed-field checks.

Verified against the real committed baseline
(`.planning/verification/schemas/iol-client/get-quote.json`) with a valid payload
mutated one field at a time:

```
                              raw wire detects   model projection detects
ultimoPrecio  float -> str          True                  False
laminaMinima  int   -> float        True                  False
new key "simbolo" added             True                  False
key "montoOperado" removed          True                  False
```

Every drift class the probe caught before this phase is now invisible to it. The
`D-25 no-overwrite-on-drift` machinery in `_write_or_check_schema` is intact but
can never fire for those three endpoints.

The compensating channel does exist — `_decode._emit` logs a WARNING record per
divergence — but **`main_iol.py` never consumes it**: the driver imports no
`logging`, installs no handler, and converts no divergence record into an
`append_finding` entry. A live run silently reports `schema_snapshot: PASS` while
the drift records evaporate into `logging.getLogger("iol_client")`'s NullHandler.

**Fix:** feed the snapshot/field-map probes the **raw wire**, and keep the model
only for the typed-access probes. The raw body is already reachable through the
same `Client._request` path `probe_field_type_map` uses for the by_type envelope
(`main_iol.py:1051`):

```python
def probe_schema_snapshot(client, today, quote, historical, instruments, by_type_envelope):
    ...
    # Capture the RAW body once per endpoint for snapshotting; the models
    # returned by the wrappers are for the typed-access probes only.
    raw = client._request(_core.build_get_quote_request(client._state, _SAMPLE_SYMBOL))
    if raw.is_error:
        _raise_for_response(raw)
    status, detail = _write_or_check_schema(
        "get_quote", _ENDPOINT_TEMPLATES["get_quote"], sample_params, raw.json(), base_url
    )
```

At minimum — if the extra HTTP calls are unacceptable — the driver MUST attach a
handler to the `iol_client` logger and convert every `decode divergence` record
into a `SHAPE` finding, so the detection that moved out of `schema_of` lands
somewhere observable:

```python
import logging

class _DivergenceToFinding(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.getMessage() != "decode divergence":
            return
        append_finding(_PKG, fid=_next_fid(), class_="SHAPE", surface="both",
                       status="OPEN", title=f"decode divergence en {record.model}",
                       expected=record.declared_type, actual=record.observed_type,
                       diff=record.field_path, base_url=_BASE_URL)

logging.getLogger("iol_client").addHandler(_DivergenceToFinding())
logging.getLogger("iol_client").setLevel(logging.INFO)
```

Note this is *not* an equivalent replacement for the raw-wire snapshot: a
**removed** key and a `null` on a non-optional field both surface as `missing`,
losing the distinction the snapshot preserved. The raw-wire fix is the correct
one.

---

### CR-02: `parse_get_instruments_by_type_response` fabricates rows from an unvalidated `titulos` and leaks `AttributeError`

**File:** `packages/iol-client/src/iol_client/_core.py:427-431`
**Severity:** BLOCKER

**Issue:**
Phase 30 changed this parser from `return titulos` (a typed lie, but inert) to
`return [Titulo.from_api(fila) for fila in titulos]` — it now **iterates** a value
it never validates. Two distinct failures, both reproduced:

```
titulos = "GGAL"          -> 4 rows, all fields defaulted:  ['', '', '', '']
titulos = {"a":1,"b":2}   -> 2 rows (iterates the dict keys)
body is a top-level list  -> AttributeError: 'list' object has no attribute 'get'
```

The first two manufacture plausible-looking but entirely synthetic financial rows
from a corrupted upstream — exactly the "silent degradation masks a changed or
compromised upstream" failure that `_parse_list_or_raise`'s own docstring
(`_core.py:355-357`) declares this milestone exists to remove, and that the two
sibling parsers were hardened against in the same commit.

The third escapes the `IOLClientError` hierarchy entirely. Every caller
documented to catch `IOLClientError` (`README.md`, the driver's `except
IOLAPIError` ladders) will miss it. `data: dict[str, Any] = resp.json()` at
`_core.py:429` is an unchecked annotation, not a check.

There is no test for either case — `test_core.py` covers only the
missing-key-yields-`[]` path.

**Fix:**

```python
    resp.read()
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise IOLAPIError(0, f"shape mismatch: expected dict envelope, got {type(raw).__name__}")
    titulos = raw.get("titulos", [])
    if not isinstance(titulos, list):
        raise IOLAPIError(0, f"shape mismatch: 'titulos' expected list, got {type(titulos).__name__}")
    return [Titulo.from_api(fila) for fila in titulos]
```

The missing-key-yields-`[]` behavior D-06 deliberately preserves is untouched by
this: `raw.get("titulos", [])` still returns a list.

---

## Warnings

### WR-01: `_parse_list_or_raise` erases the TYP-01 static guarantee at its own boundary

**File:** `packages/iol-client/src/iol_client/_core.py:345` (signature), `383`, `408` (call sites)

**Issue:** The helper is typed `(resp, model_cls: type[Any]) -> list[Any]`. The
callers "narrow" it with an annotated local, but `list[Any]` is assignable to
*any* `list[T]`, so mypy validates nothing. Confirmed against the repo's own
strict config:

```python
result: list[Titulo] = _core._parse_list_or_raise(resp, dict)   # mypy --strict: Success
```

The phase's deliverable is mypy-verified attribute access; here the model class
and the declared return type are decoupled with no checking, and the two
docstrings calling the annotated local "load-bearing" (`_core.py:381`, `406`)
describe a guarantee that does not exist. A future parser wired to the wrong model
class ships green.

**Fix:** PEP 695 generics (already used in this codebase — `_decode._response_parser`
is declared `[**P, R]`):

```python
@_decode._response_parser
def _parse_list_or_raise[T: SafeModel](resp: httpx.Response, model_cls: type[T]) -> list[T]:
    ...
    return [model_cls.from_api(item) for item in raw]
```

Then drop the annotated locals — `return _parse_list_or_raise(resp, Cotizacion)`
typechecks directly, and the wrong-class call above becomes an error.

---

### WR-02: the `get_quote` / `get_historical_quotes` field-type assertions are now unreachable, and one guarantees a permanent false finding

**File:** `main_iol.py:119-126` (assumptions), `main_iol.py:1129-1201` (checks)

**Issue:** Same root cause as CR-01, but a distinct symptom worth its own fix.
Because `observed` is derived from `quote.to_dict()`:

- The `observed[key] != expected_type` branch (`main_iol.py:1150`, `1187`) can
  never be true. `ultimoPrecio` is declared `float`; the walker guarantees a
  `float` reaches the attribute. Dead code.
- The `key not in observed` branch can never be true for a *declared* field.
- `_ASSUMED_QUOTE_FIELDS` (`main_iol.py:119-122`) contains `"simbolo": "str"`,
  but `Cotizacion` declares no `simbolo` field and the committed
  `get-quote.json` baseline has no such key. This branch now fires on **every
  live run, forever**, emitting a permanent `SHAPE` OPEN finding that no upstream
  change can ever clear.

**Fix:** run these checks against the raw wire (see CR-01), and delete the
`"simbolo"` entry — it was never in the corpus:

```python
_ASSUMED_QUOTE_FIELDS: dict[str, str] = {
    "ultimoPrecio": "float",  # IOL-04: numeric, JSON number
}
```

---

### WR-03: `int`-declared quantity fields are silently zeroed by a JSON float

**File:** `packages/iol-client/src/iol_client/models.py:145-146` (`Cotizacion.laminaMinima`, `.lote`), `:225-226` (`Titulo.laminaMinima`, `.lote`)

**Issue:** The strict `int` branch of the walker substitutes `policy.missing_int`
(`0`) when the wire sends a decimal. Reproduced:

```python
Titulo.from_api({"laminaMinima": 100.0, "lote": 50.0})   # -> laminaMinima=0, lote=0
```

`laminaMinima` is a minimum tradeable lot and `lote` a lot size. A consumer
computing `qty * titulo.laminaMinima` gets `0` — a silent wrong answer in a
financial path, not a missing one. Many JSON producers emit `100.0` for a whole
number, so this is not an exotic input.

The models docstring reasons carefully about this asymmetry for
`cantidadOperaciones` (D-04, `models.py:130-135`, `210-213`) and declares the
substitution deliberate there. `laminaMinima` and `lote` were not part of that
analysis and inherited the behaviour by default.

The divergence *is* reported to the `iol_client` logger, so library consumers who
configure logging can see it — which is why this is a WARNING rather than a
BLOCKER. It is invisible to the driver (CR-01).

**Fix:** either declare these `float` (the same widening `Titulo.cantidadOperaciones`
already uses, which accepts `100.0` and `100` alike), or record an explicit
decision in the docstring the way D-04 did for `cantidadOperaciones`, so the
choice is reviewable rather than inherited.

---

### WR-04: `parse_get_quote_response` has no shape guard, asymmetric with its two siblings

**File:** `packages/iol-client/src/iol_client/_core.py:339-341`

**Issue:** `Cotizacion.from_api(resp.json())` accepts any JSON body. A `[]`, a
`null`, or an error string produces an all-zeros `Cotizacion` with
`ultimoPrecio == 0.0`, no exception, and (in default mode) nothing the caller can
branch on — `if quote:` is always true for a dataclass, as the README changelog
itself warns.

In the same commit, `_parse_list_or_raise` gained an explicit `isinstance` guard
with an ASVS V5 rationale for exactly this failure mode. Applying it to the two
list parsers but not the single-object one leaves the security argument
half-implemented. The `non_dict` divergence record fires, but only strict mode
turns it into an error.

**Fix:**

```python
    resp.read()
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise IOLAPIError(0, f"shape mismatch: expected dict, got {type(raw).__name__}")
    return Cotizacion.from_api(raw)
```

---

### WR-05: README changelog states the `to_dict()` round-trip loss backwards

**File:** `packages/iol-client/README.md` (Changelog v0.3.0, "Escape hatch: `to_dict()`")

**Issue:** The changelog says *"Un valor nulo del wire decodificado a un campo
opcional […] no sobrevive la ida y vuelta"*. It does survive, exactly: a wire
`null` on an `Optional` field decodes to `None` and `asdict` keeps the key with
value `None` — which `models.py:85-86` correctly documents as *"``None`` keys are
**kept**"*. The two documents contradict each other.

The genuinely lossy case is the opposite one: a `null` (or a wrong-typed value)
on a **non-optional** field, which becomes `""` / `0` / `0.0` and is
indistinguishable from a real zero after the round-trip. A consumer migrating via
`to_dict()` will guard the case that is safe and miss the case that is not.

Two further omissions in the same section:
- `get_historical_quotes` also gained the raise-on-non-list behaviour, but only
  `get_instruments` is listed under "Cambio de forma".
- `IOLDecodeError` becomes reachable from these four functions for the first time
  under `strict_decode=True` (Phase 29 shipped it with no models to decode). Not
  mentioned.

**Fix:** rewrite the lossy-case sentence to name non-optional fields, add
`get_historical_quotes` to the shape-change list, and add a line on
`IOLDecodeError` under `strict_decode`.

---

### WR-06: an empty instrument-type listing is reported as a shape defect

**File:** `main_iol.py:829-830` (predicate), `main_iol.py:840-842` (finding text)

**Issue:** `if not (isinstance(titulos, list) and titulos and isinstance(titulos[0], Titulo))`
treats an **empty** list as a bad shape. `cauciones` or `letras` returning `[]`
outside market hours — a legitimate response the sibling parser's own docstring
calls valid ("the guard discriminates shape, not cardinality",
`_core.py:402-403`) — emits a spurious `SHAPE` OPEN finding.

The finding text was not migrated with the predicate: `expected="cada
InstrumentType retorna list[dict] no vacía"` and `diff="shape !=list[dict] …"`
still describe the pre-Phase-30 dict world.

**Fix:**

```python
        if not isinstance(titulos, list) or (titulos and not isinstance(titulos[0], Titulo)):
            bad_types.append(f"{itype}: shape={type(titulos).__name__}")
```

and update `expected=` / `diff=` to `list[Titulo]`.

---

### WR-07: `probe_parity_sync_async` retains only a fraction of its discriminating power

**File:** `main_iol.py:980-981`

**Issue:** The `_as_wire` docstring is right that comparing two model instances
directly would collapse to `"Cotizacion" == "Cotizacion"` — but the projection it
substitutes only partially recovers the check. Both sides are `to_dict()` of the
*same* class, so the key set is identical by construction and the leaf type names
are identical for every non-optional field. The comparison can now only differ on
(a) `Optional` fields where one surface saw `null` and the other did not, and (b)
list cardinality (`[]` vs populated). A sync/async divergence in field presence or
scalar type — the drift classes IOL-06 targets — is undetectable.

**Fix:** compare the raw wire on both surfaces (same remedy as CR-01), or
document explicitly in the probe docstring which drift classes it can and cannot
still detect, so a future `PASS` is not read as stronger evidence than it is.

---

### WR-08: `Client._request` binds a `DecodeScope` that is never retired when no parser runs

**File:** `packages/iol-client/src/iol_client/client.py:460-461`; `packages/iol-client/src/iol_client/aio.py:462-463`

**Issue:** `open_request_scope()` binds a scope on every `_request`, but only a
`@_response_parser`-decorated frame retires it (`_decode._response_scope`
`finally`). Raw `_request` callers — the legacy module-level shims
(`client.py:732`, `aio.py:746`) and `main_iol.py:1051` — leave a live,
non-retired scope bound to the context.

Any subsequent standalone `Model.from_api()` on that thread then adopts that
stale scope through `current_sink()` and inherits its dedupe set, which is the
exact "second identical decode reads silently clean" failure lock 6 was written to
prevent. Public standalone `from_api` is a supported entry point (DT-05).

Not reachable in the current driver ordering (the next `_request` re-binds before
any decode), which is why this is a WARNING and not a BLOCKER — but it is
reachable from library code that mixes a raw `_request` with a standalone
`from_api`.

**Fix:** have the raw-`_request` shims retire the scope they bound, e.g. wrap the
shim body in `_decode._response_scope()`, or retire in `Client._request` when it
returns a response no decorated parser will consume.

---

## Info

### IN-01: `SafeModel.from_api` / `to_dict` raise a bare `TypeError` on the exported base class

**File:** `packages/iol-client/src/iol_client/models.py:72-78`, `80-94`

`SafeModel` is in `__init__.__all__` and in the surface snapshot, but it is not a
dataclass. `SafeModel.from_api({})` raises `TypeError: fields() should be called
on dataclass instances` from deep inside `_decode`, and `to_dict()` on a
hypothetical base instance raises similarly from `dataclasses.asdict`. Consider
`raise NotImplementedError` guards, or drop `SafeModel` from `__all__` if it is
only meant as an isinstance target.

### IN-02: stale source reference in a live finding's `diff` text

**File:** `main_iol.py:1091`

`diff="client.py:254 hace data.get('titulos', []) y devuelve [] silenciosamente"`
— that code now lives at `_core.py:430`, and `client.py:254` is inside
`_ensure_http_client`. The reference is committed into every finding this branch
emits. Update to `_core.py:430`.

### IN-03: `to_dict()` is new public API but is invisible to the surface-snapshot guard

**File:** `verification/snapshots/iol-client-surface.txt:11,18-21`

The snapshot records constructor signatures only (`SafeModel : class : ()`), so
`to_dict()` — a documented migration path in the README changelog — can be
renamed or have its signature changed without the snapshot going red. Worth
extending `regen_snapshots.py` to record public methods on exported model classes,
or at least documenting the gap.

### IN-04: the frozen `_decode.py` copy still carries higyrus provenance comments

**File:** `packages/iol-client/src/iol_client/_decode.py:138-140`, `243-244`

`POLICY`'s comment reads *"higyrus-client row of 29-SEMANTICS-MATRIX.md"* and the
`SILENT_SINK` comment reads *"higyrus has no ``empty()`` today"*, in the iol copy.
Correct per the byte-identical intactness gate, and out of scope to change this
phase — but `models.py:32-53` re-ratifies this exact constant for iol without
noting that the constant's own inline comment names a different paquete. A reader
verifying the ratification lands on a contradiction. Worth a forward note in the
intactness-gate documentation.

---

_Reviewed: 2026-08-20T03:50:27Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
