---
phase: 37-matriz-client-dicts-residuales-tipados-alias
reviewed: 2026-08-29T16:59:50Z
depth: deep
files_reviewed: 11
files_reviewed_list:
  - packages/matriz-client/src/matriz_client/__init__.py
  - packages/matriz-client/src/matriz_client/_core.py
  - packages/matriz-client/src/matriz_client/models.py
  - packages/matriz-client/tests/test_async_queries.py
  - packages/matriz-client/tests/test_core.py
  - packages/matriz-client/tests/test_decode.py
  - packages/matriz-client/tests/test_models.py
  - packages/matriz-client/tests/test_null_object.py
  - packages/matriz-client/tests/test_surface_types_red.py
  - tools/check_surface_types.py
  - verification/snapshots/matriz-client-surface.txt
findings:
  critical: 2
  warning: 8
  info: 6
  total: 16
status: issues_found
---

# Phase 37: Code Review Report

**Reviewed:** 2026-08-29T16:59:50Z
**Depth:** deep
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the five landed plans of Phase 37 across the matriz-client package, the
cross-package surface gate, and the regenerated public-surface snapshot. Baseline
health is good: `uv run pytest packages/matriz-client` is 556 passed,
`ruff check` / `ruff format --check` / `mypy --strict` are clean, and
`tools/check_surface_types.py` reports `0 violations`. The reviewed code itself is
carefully written and heavily documented.

The defects are at the seams, and two of them are load-bearing:

1. **The strict-unwrap change in `_core.py` was applied to the client but not to
   `main_matriz.py`**, the live verification driver that is this project's stated
   Core Value. Six sites in the driver still assert the exact belief 37-01
   falsified, and probe 20 (`field_type_map`) now diffs the model against the
   *enveloped* body. This is a live, deterministic defect that will fabricate a
   storm of SHAPE findings on the next real run.
2. **The new field dimension of `check_surface_types.py` does not hold its own
   stated contract.** Four distinct `dict[str, Any]` shapes — including
   `dict[str, dict[str, Any]]`, the exact nesting shape 37-03 introduced, and
   `Union[dict[str, Any], None]`, the exact bypass the code claims to have closed
   — pass the gate. All four were verified by executing the predicate.

Underneath those, the new mapping axis in `models.py` has three reachable-by-a-
future-field correctness holes (`Mapping[str, X]`, bare `dict`, and
`Optional[dict[str, X]]`) and one observability hole (lock 5's dedupe collapse is
defeated by open payload keys — measured at 1000 log records for a 500-symbol
`report`). None of the four is triggered by a *shipped* model today, which is why
they are WARNINGs rather than BLOCKERs, but the `Mapping[str, X]` case is
actively steered into by the gate itself.

Every finding below was verified by executing code, not by reading alone.

## Critical Issues

### CR-01: `main_matriz.py` still assumes the Risk endpoints have no envelope — 37-01's fix was applied to the client only

**File:** `main_matriz.py:1266-1287`, `main_matriz.py:1294-1315`, `main_matriz.py:1353-1354`
(also `main_matriz.py:472-473`, `:499`, `:514-515`, `:525`)

**Issue:**
Plan 37-01 changed `_core.parse_get_detailed_positions_response` and
`parse_get_account_report_response` to unwrap `detailedPosition` / `accountData`
(`packages/matriz-client/src/matriz_client/_core.py:918-920`, `:955-957`). The live
verification driver was not updated with it. Both probes still pass
`envelope_key=None`:

```python
# main_matriz.py:1269-1270
Risk API HTTP Basic Auth. **SIN envelope key (D-07)** — el payload raíz es
el dict completo.
...
return _envelope_probe(..., envelope_key=None, ...)
```

With `envelope_key=None`, `_envelope_probe` returns the **raw envelope body** to
the caller (`main_matriz.py:514-532`). That body is then stored in `payloads` and
fed to the shape differ at `main_matriz.py:1353-1354`:

```python
("detailed_position", payloads.get("get_detailed_positions"), DetailedPosition),
("account_report",    payloads.get("get_account_report"),    AccountReport),
```

`diff_safemodel_bidirectional` compares the payload's key set against the model's
field set (`verification/safemodel_diff.py:141-166`). It will now see
`{"status", "detailedPosition"}` on the wire versus
`{account, totalDailyDiffPlain, totalMarketValue, report, lastCalculation}` on the
model, and emit **seven fabricated SHAPE findings** for `detailed_position` plus a
comparable set for `account_report` — five of them titled
`"model declara, wire no emite (FALSE PASS riesgo)"`, which is precisely the class
of false finding this milestone exists to eliminate. Probes 18 and 19 will still
report `PASS` while validating the wrong shape, and the `PrimaryAPIError` handler
at `main_matriz.py:496-500` will print `"200 OK con dict raíz (sin envelope key,
D-07)"` as the *expected* shape if the new `unwrap` ever fires.

The stale belief also survives verbatim in six prose sites (`:473`, `:499`,
`:515`, `:525`, `:1269`, `:1297`), so the phase corrected two of the three places
the wrong claim lived.

**Fix:** Flip both probes to the envelope form and delete the `envelope_key=None`
branch's D-07 justification, mirroring `probe_get_positions`:

```python
# main_matriz.py — probe_get_detailed_positions
    return _envelope_probe(
        client,
        "get_detailed_positions",
        f"/rest/risk/detailedPosition/{_PRIMARY_ACCOUNT}",
        envelope_key="detailedPosition",   # Phase 37 D-03 strict-unwrap
        auth_basic_fn=client._risk_auth,
        pass_detail=lambda _: "account received",
    )

# main_matriz.py — probe_get_account_report
        envelope_key="accountData",        # Phase 37 D-03 strict-unwrap
```

and update the four `_envelope_probe` docstring/message sites (`:472-473`, `:499`,
`:515`, `:525`) plus the two probe docstrings (`:1268-1270`, `:1296-1298`) to cite
`documentation/Primary-API.md:1701-1703` and `:1817-1819` the way `_core.py` now
does. A regression test in `packages/matriz-client/tests/` cannot cover this —
add the assertion to the driver-lock list in `.github/workflows/ci.yml:80-83`, or
at minimum grep-assert that no `envelope_key=None` call site remains for a Risk
path.

---

### CR-02: the new field dimension of the surface gate has four provable false negatives, including the shape this phase itself introduced

**File:** `tools/check_surface_types.py:551-584` (`_field_annotation_is_untyped_mapping`),
`tools/check_surface_types.py:528-548` (`_strip_optional`),
`tools/check_surface_types.py:713-737` (`_field_candidates_for`)

**Issue:**
The module docstring states the contract as *"No field declared in the body of an
exported class may be annotated as an untyped mapping"* (`:12-14`) and explicitly
claims the optional hole is closed: *"leaving the hole open would have made
`| None` a one-token bypass of the whole field dimension"* (`:536-538`). Executing
the predicate over candidate annotations falsifies all of that:

```
'dict[str, Any]'            -> True    (caught)
'dict[str, Any] | None'     -> True    (caught)
'Optional[dict[str, Any]]'  -> True    (caught)
'Union[dict[str, Any], None]' -> False  <-- MISSED
'dict[str, dict[str, Any]]'   -> False  <-- MISSED
"'dict[str, Any]'" (quoted)   -> False  <-- MISSED
'dict[str, "Any"]'            -> False  <-- MISSED
'defaultdict[str, Any]'       -> False  <-- MISSED
'dict'  (unparameterised)     -> False  <-- MISSED
```

Each is a real hole, and two of them matter concretely:

- **`dict[str, dict[str, Any]]`.** This is the *exact* container shape 37-03
  introduced for `DetailedPosition.report`. `_field_annotation_is_untyped_mapping`
  matches only the annotation's own shape (`:576-584`), never its subtree, so a
  future author who types the outer level and leaves the inner one `Any` — the
  single most likely partial migration — ships green.
- **`Union[dict[str, Any], None]`.** `_strip_optional` handles `ast.BinOp | None`
  and `Optional[...]` (`:540-547`) but not `Union[X, None]`, which is the third
  legal spelling of the same thing. Note that `models._strip_optional`
  (`packages/matriz-client/src/matriz_client/models.py:86-92`) *does* accept
  `typing.Union`, so the runtime and the gate disagree on what "optional" means.
- **Quoted annotations.** `payload: "dict[str, Any]"` parses to `ast.Constant`;
  `_base_name` returns `None` and the predicate short-circuits. Legal Python and
  common for forward refs.
- **Bare `dict`.** States strictly *less* than `dict[str, Any]` yet is spared,
  because the predicate requires an `ast.Subscript`. See WR-02 for what this
  shape also does at runtime.

Two structural holes compound these:

- `_field_candidates_for` (`:731-737`) collects only the **direct class body**'s
  `AnnAssign` nodes. An exported dataclass inheriting `payload: dict[str, Any]`
  from a base that is not itself in `__all__` is invisible. Today the only
  inheriting exported dataclass in the workspace is `matriz_client.OrderReport`,
  whose base `Order` *is* exported, so this is latent — but the ratchet does not
  cover it.
- The gate resolves candidates from `__all__` outward only. A `dict[str, Any]`
  field on a non-exported class that is nonetheless the **declared element type**
  of an exported mapping field is unreachable. Phase 37 avoided this by adding
  `TickPriceRange` / `InstrumentPositionReport` / `DetailedAccountReport` to
  `__all__`, but nothing enforces that a future element model be exported.

**Fix:** Make the predicate recursive over mapping value parameters, accept
`Union[..., None]` and string annotations, and reject an unparameterised mapping
base:

```python
def _field_annotation_is_untyped_mapping(annotation: ast.expr) -> bool:
    inner = _strip_optional(annotation)
    if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
        try:                                     # quoted forward ref
            inner = ast.parse(inner.value, mode="eval").body
        except SyntaxError:
            return True                          # unparseable == uninspectable
        inner = _strip_optional(inner)
    if _is_any(inner):
        return True
    if isinstance(inner, ast.Name) and inner.id in _MAPPING_BASES:
        return True                              # bare `dict` says nothing
    if not isinstance(inner, ast.Subscript):
        return False
    if _base_name(inner.value) not in _MAPPING_BASES:
        return False
    parameters = inner.slice.elts if isinstance(inner.slice, ast.Tuple) else [inner.slice]
    # RECURSE on the value parameter: dict[str, dict[str, Any]] is untyped too.
    return len(parameters) == 2 and _field_annotation_is_untyped_mapping(parameters[1])
```

and extend `_strip_optional` to peel `Union[X, None]`:

```python
    if isinstance(annotation, ast.Subscript) and _base_name(annotation.value) == "Union":
        arms = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
        non_none = [a for a in arms if not _is_none(a)]
        if len(non_none) == 1:
            return _strip_optional(non_none[0])
```

Add each shape above as a RED case in
`packages/matriz-client/tests/test_surface_types_red.py`; the existing suite
currently pins only the three shapes that already pass. Note that recursing the
value parameter keeps `list[Any]` spared, so D-01b's out-of-scope narrowness
contract (`test_a_list_of_any_field_is_spared_...`) still holds — verify by
re-running the gate over the real tree, which must stay at `0 violations`.

## Warnings

### WR-01: the gate's mapping vocabulary and the runtime mapping axis disagree — `Mapping[str, X]` green-lights a type lie

**File:** `tools/check_surface_types.py:226` (`_MAPPING_BASES`),
`packages/matriz-client/src/matriz_client/models.py:99-101` (`_is_mapping`)

**Issue:** The gate accepts `dict`, `Dict`, `Mapping`, `MutableMapping` as mapping
bases *specifically* so "the ratchet cannot be bypassed by spelling the same
untyped mapping as `Mapping[str, Any]`" (`:224-226`). The runtime axis recognises
only `dict`:

```python
def _is_mapping(tp: Any) -> bool:
    return get_origin(_strip_optional(tp)) is dict
```

`get_origin(Mapping[str, X])` is `collections.abc.Mapping`, not `dict`. Measured
consequence:

```
AbcMap.from_api({"m": {"0": {"tick": 1}}})  ->  AbcMap(m={'0': {'tick': 1}})   # raw dicts
AbcMap.from_api({})                         ->  AbcMap(m=None)                 # not {}
```

The values arrive as raw payload dicts under a `Mapping[str, Leaf]` annotation —
the exact type lie the `_mapping_value` docstring says the phase exists to remove
(`models.py:174-182`) — and an absent field yields `None`, breaking both the
module docstring's "missing dicts become `{}`" guarantee (`models.py:5-6`) and any
`.items()` / `.values()` chain. The trap is worse than passive: a developer whose
`Mapping[str, Any]` field is *reddened by the gate* will naturally "fix" it to
`Mapping[str, Model]`, which turns the gate green and the runtime broken.

**Fix:** Align the two vocabularies. Either widen `_is_mapping` (preferred, since
the gate already blesses the aliases):

```python
_MAPPING_ORIGINS = (dict, collections.abc.Mapping, collections.abc.MutableMapping)

def _is_mapping(tp: Any) -> bool:
    return get_origin(_strip_optional(tp)) in _MAPPING_ORIGINS
```

or narrow `_MAPPING_BASES` to `{"dict", "Dict"}` and add a *separate* gate rule
that bans `Mapping`/`MutableMapping` field annotations outright in matriz. Pin
whichever with a test in `test_decode.py` next to the other mapping-axis cases.

---

### WR-02: a bare `dict` field annotation bypasses the mapping axis entirely and yields `None` on absence

**File:** `packages/matriz-client/src/matriz_client/models.py:99-101`, `:104-119`

**Issue:** `_element_hint`'s docstring claims *"A legacy bare `dict[str, Any]` and
an unparameterised `dict` both answer `Any`"* (`:113-116`). The unparameterised
half never happens: `_is_mapping(dict)` is `False`, so `_apply_mapping_policy`
never visits the field and `_element_hint` is never called for it. Measured:

```
models._is_mapping(dict)                      -> False
Bare.from_api({"meta": "garbage"})            -> Bare(meta='garbage')
Bare.from_api({})                             -> Bare(meta=None)
```

So a bare `dict` field silently (a) skips the `{}` container fallback, (b) skips
the divergence report, (c) passes garbage through, and (d) answers `None` for an
absent key — while also passing the surface gate (see CR-02). Three of the four
guarantees the module docstring makes for a mapping field are void for this
spelling, and nothing anywhere says so.

**Fix:** Treat an unparameterised mapping base as a mapping in `_is_mapping`
(`get_origin(dict)` is `None`, so add an explicit `tp is dict` arm), and correct
the `_element_hint` docstring, which currently documents a code path that cannot
be reached:

```python
def _is_mapping(tp: Any) -> bool:
    stripped = _strip_optional(tp)
    return stripped is dict or get_origin(stripped) is dict
```

Combine with CR-02's bare-`dict` gate arm so the annotation is banned at the gate
*and* handled correctly if it slips in via a non-exported class.

---

### WR-03: `Optional[dict[str, X]]` is force-collapsed to `{}` and emits a spurious `missing` divergence that is fatal under strict mode

**File:** `packages/matriz-client/src/matriz_client/models.py:99-101`, `:204-206`,
`:252-261`

**Issue:** `_is_mapping` strips `Optional` before testing (`:100-101`), so an
optional mapping field enters `_apply_mapping_policy`. `walk_field` has already
correctly returned `None` for it (`_decode.py:436-444`: *"Optional[T] / T | None:
explicit opt-in to nullable — a missing value stays None ... and is NOT a
divergence"*), and `_mapping_value` then overwrites that:

```
OptMap.from_api({})          -> OptMap(m={})   + WARNING "decode divergence" (missing)
OptMap.from_api({"m": None}) -> OptMap(m={})   + WARNING "decode divergence" (missing)
```

Two defects in one: the declared-nullable field can never hold `None`, and a
legitimate null on an explicitly-nullable field is reported as a `missing`
divergence — which `DecodeScope.__call__` (`_decode.py:209-225`) makes **fatal**
under `strict_decode`, so a strict driver run would crash on a well-formed
payload. No shipped model declares an optional mapping today, which is the only
reason this is not live.

**Fix:** Preserve the nullable opt-in by testing optionality before applying the
axis:

```python
def _is_optional(tp: Any) -> bool:
    return get_origin(tp) in (Union, types.UnionType) and type(None) in get_args(tp)

# in _apply_mapping_policy
        if _is_mapping(hint):
            if _is_optional(hint) and kwargs[f.name] is None:
                continue          # nullable opt-in: None stays None, no record
            kwargs[f.name] = _mapping_value(...)
```

Add the two cases above to `test_decode.py`'s "Mapping axis" section, which
currently exercises only non-optional mapping fields.

---

### WR-04: mapping keys enter `field_path`, defeating lock 5's dedupe collapse — measured 1000 records for one 500-symbol `report`

**File:** `packages/matriz-client/src/matriz_client/models.py:207-227`

**Issue:** `_mapping_value` builds each element's path as
`f"{path}.{_decode._safe_key(key)}"` (`:209`). The walker deliberately does the
opposite for list elements — `path=f"{path}[]"` with no index — precisely so that
*"N identically-diverging rows of an unbounded catalogue read collapse into one
record"* (`_decode.py:170-180`, lock 5). An open-keyed mapping is the same
unbounded axis: `report[contractType][symbol]` is keyed by *data*, not by schema.
Measured over a 500-symbol `report` where each leaf carries the vendor's
`detailedPositions` key (present in **every** vendor sample, `Primary-API.md:1710`):

```
records emitted: 1000
sample paths: ['.report.FUT.SYM0.vendorNew', '.report.FUT.SYM0.instrumentInitialSize',
               '.report.FUT.SYM1.vendorNew']
```

Two facts about the same field produce 1000 log records and 1000 entries in
`DecodeScope._seen`, where the equivalent `list[Model]` shape produces 2. This is
not hypothetical: `test_report_deferred_detailedPositions_is_one_non_fatal_extra`
proves the `detailedPositions` extra fires for every leaf, so every real
`get_detailed_positions` call floods the package logger proportionally to the
account's position count.

**Fix:** Decide explicitly whether a mapping key is a *schema* segment or a *data*
segment, and make the choice visible. The consistent-with-lock-5 answer is to use
an index-free segment for the dedupe triple while keeping the real key in the
record for locatability — or, if the key genuinely aids diagnosis, cap the
distinct keys per path:

```python
    for key, item in value.items():
        # Lock 5: an open-keyed mapping is an unbounded axis, exactly like a list.
        # The dedupe segment carries no key, so N identically-diverging entries
        # collapse into one record.
        item_path = f"{path}{{}}"
```

Whichever is chosen, update the `_mapping_value` docstring — it currently
discusses keys only for the lock-11 sanitisation reason (`:198-202`) and never
addresses the lock-5 interaction — and add a test asserting the record count for
an N-key mapping is O(1) rather than O(N).

---

### WR-05: the strict-unwrap behaviour change rests entirely on vendor documentation, with no live capture and no diagnostic path

**File:** `packages/matriz-client/src/matriz_client/_core.py:900-920`, `:945-957`

**Issue:** Both Risk parsers now raise `PrimaryAPIError` when the envelope key is
absent. The only evidence for the key names is the committed vendor doc; the
models' own docstrings state the position unambiguously: *"no live observation of
this payload exists anywhere in this repo, and none can be produced while
`LIVE-MATZ-33` stands"* (`models.py:676-681`, `:751-758`). Confirmed —
`.planning/verification/schemas/matriz-client/` holds eight captures and neither
Risk endpoint is among them.

The prior behaviour on a shape mismatch was a silent all-defaults model; the new
behaviour is a hard failure on the only two endpoints in the package with zero
live verification. The disposition was ratified by the operator, so this is not a
process objection — but three things make the residual risk larger than it needs
to be:

- there is no fallback or self-describing diagnostic: `unwrap`'s message
  (`_core.py:233-238`) says *"missing envelope key 'detailedPosition'"* but never
  lists the keys the body **did** carry, which is the single datum an operator
  would need to distinguish "vendor uses a different key" from "vendor changed the
  shape";
- the driver that would have discovered the truth is itself broken (CR-01);
- no test covers `{"status":"OK","detailedPosition": null}`, which passes `unwrap`
  and silently produces an all-defaults model — reintroducing the very failure
  mode strict-unwrap was adopted to eliminate.

**Fix:** Include the observed key set in the `unwrap` failure so a live run is
self-diagnosing, and add the null-envelope regression:

```python
def unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=(
                f"missing envelope key '{key}' in response from {endpoint} "
                f"(body carried: {sorted(data)})"
            ),
            message=None,
        )
    return data[key]
```

```python
def test_risk_parsers_on_a_null_envelope_value_do_not_read_as_an_empty_account() -> None:
    resp = _make_response(json_body={"status": "OK", "detailedPosition": None})
    result = _core.parse_get_detailed_positions_response(resp, "REM7374")
    assert bool(result) is False   # decide + pin: empty model, or raise
```

---

### WR-06: the closed Risk rosters discard the bulk of both payloads, and the project's own shape-differ cannot see inside a mapping

**File:** `packages/matriz-client/src/matriz_client/models.py:668-722` (`InstrumentPositionReport`),
`:747-790` (`DetailedAccountReport`)

**Issue:** `DetailedPosition.report` and `AccountReport.detailedAccountReports`
were `dict[str, Any]` passthroughs where every vendor key reached the caller. They
are now closed three-field and one-field dataclasses. Against the committed vendor
sample that means:

- `report[...][...]` drops `detailedPositions` — a ~21-field array whose elements
  each carry an 8-field `detailedDailyDiff` (`Primary-API.md:1710-1744`);
- `detailedAccountReports[...]` drops `currencyBalance` (a 9-currency
  `{consumed, available}` map, `:1828-1868`) and `availableToOperate` (a `cash`
  object with its own 9-key `detailedCash` map plus four siblings, `:1869-1888`),
  keeping only `settlementDate`.

The models disclose this and argue the loss is detectable via `extra` divergences,
with *"widening the roster is the right answer once a live run MEASURES one of
those keys"* (`:702-703`). That remedy is not currently reachable:
`verification/safemodel_diff.py::_nested_safemodel_class` (`:78-99`) handles bare
models, `list[Model]` and `Optional[...]` — it has **no `dict` branch**. All three
models introduced this phase sit behind a mapping and are therefore structurally
invisible to `diff_safemodel_bidirectional`, i.e. to probe 20, i.e. to the only
mechanism that would ever "measure" the missing keys. `models.py:702-703` promises
a feedback loop that does not exist.

Compounding: this is a data-loss behaviour change on a published wheel surface
(`matriz-client` 0.2.0) with no CHANGELOG in the repo and no version movement in
this phase.

**Fix:** Give the differ a mapping branch so the new rosters are actually
reachable by the live driver, sampling one entry the way `list[Model]` already
does:

```python
# verification/safemodel_diff.py
    if origin is dict:
        args = get_args(hint)
        if len(args) == 2:
            return _nested_safemodel_class(args[1])   # recurses for dict[str, dict[str, M]]
```

plus a matching recursion arm in `diff_safemodel_bidirectional` that descends the
first mapping value. Until that lands, replace the "once a live run MEASURES one
of those keys" sentence in both model docstrings with a pointer to the actual
mechanism (the `extra` records in the append-only findings ledger), so the
docstring does not promise a loop that is not wired.

---

### WR-07: the `private-helper` exemption applied to fields is a one-token bypass of the whole field dimension

**File:** `tools/check_surface_types.py:476-489` (`_is_exempt`),
`tools/check_surface_types.py:765` (`_adjudicate_field`)

**Issue:** `_adjudicate_field` falls back to `_is_exempt(member)`, whose
`private-helper` rule spares *"any single-underscore-prefixed member"* on the
grounds that it is *"reachable only as a method of an exported class; no `__all__`
in any package contains an underscore-prefixed name"* (`:124-126`). That reasoning
is a method's, not a field's. A dataclass field named `_payload` is an `__init__`
parameter, an instance attribute, and it appears verbatim in
`verification/snapshots/*.txt` — it is unambiguously on the exported surface. So
`_payload: dict[str, Any]` silences the entire new dimension with one character,
and `test_a_private_field_is_absorbed_by_the_existing_taxonomy`
(`test_surface_types_red.py:380-392`) enshrines that as correct.

**Fix:** Split the taxonomy so the field dimension does not inherit the method
rule:

```python
def _is_field_exempt(qualified: str, member: str) -> str | None:
    """Field exemptions. Deliberately NOT `_is_exempt`: a dataclass field named
    ``_x`` is an ``__init__`` parameter and an instance attribute, so the
    method-oriented ``private-helper`` rule does not transfer to it."""
    return _FIELD_EXEMPTIONS.get(qualified)
```

and invert the test above to assert that `_cache: dict[str, Any]` **reddens**.
Confirm the real tree stays at `0 violations` afterwards.

---

### WR-08: the depth-2 nesting precondition is guarded per-class by hand, so a new mapping-carrying leaf model gets no guard at all

**File:** `packages/matriz-client/tests/test_decode.py:537-592`,
`packages/matriz-client/tests/test_models.py:344`, `:384`

**Issue:** `_apply_mapping_policy` reaches top-level fields only
(`models.py:236-243`); a mapping field on a model reached through
`walk_field`'s nested-model branch is silently skipped. The stated guard is
`test_no_mapping_carrying_model_is_ever_a_nested_field_type`, but its
`nested_types` collection walks exactly one level of `__args__`
(`test_decode.py:571-581`), so for
`report: dict[str, dict[str, InstrumentPositionReport]]` the `__args__` are
`(str, dict[str, InstrumentPositionReport])` and the leaf model never enters the
set. The test says so itself (`:583-592`) and hands the job to two hand-written
per-class assertions (`test_models.py:344`, `:384`) that enumerate today's two
depth-2 models by name.

That is not a guard, it is a checklist. The moment plan 39 (`LIVE-NOBJ-01`) adds
the deferred `detailedPositions` / `currencyBalance` / `availableToOperate`
subtrees — which are themselves open-keyed maps, i.e. exactly the shape that
would carry a mapping field at depth 2 — nothing fails, and the mapping axis
silently skips them.

**Fix:** Make the walk depth-agnostic instead of naming classes:

```python
def _model_types_in(hint: Any) -> Iterator[type]:
    inner = models._strip_optional(hint)
    if isinstance(inner, type) and dataclasses.is_dataclass(inner) and issubclass(inner, _SafeModel):
        yield inner
        return
    for arg in get_args(inner):
        yield from _model_types_in(arg)

nested_types = {
    c.__name__
    for cls in shipped
    for hint in _decode.hints_for(cls).values()
    for c in _model_types_in(hint)
}
```

This subsumes both per-class assertions and closes F-11 option (b) at test cost
only, with no production change.

## Info

### IN-01: the gate's own recorded output is stale by six definitions

**File:** `tools/check_surface_types.py:34-36`

**Issue:** The "After Phase 37" block claims `330 definitions scanned`. The actual
output is `336` — the six `@property` aliases 37-05 added to `MarketDataSnapshot`
are `FunctionDef` nodes in the class body and are counted by `_candidates_for`.
The block was written by 37-04 and not refreshed by 37-05. Only floors are
asserted (`test_surface_types_red.py:427`), so nothing catches the drift.

**Fix:** Update the docstring to the measured
`336 definitions scanned, 442 fields scanned`, and note that the definition count
now includes property getters so a future reader does not re-derive the delta.

---

### IN-02: dead defensive branch in `_SafeModel.from_api`

**File:** `packages/matriz-client/src/matriz_client/models.py:345-347`

**Issue:**

```python
_apply_mapping_policy(
    cls, kwargs, sink=sink if isinstance(data, dict) else _decode.SILENT_SINK
)
```

The `else` arm is unreachable: the `return cls.empty()` four lines above
(`:335-340`) already fires for every non-dict `data` while
`POLICY.non_dict_model == "empty_classmethod"`, which
`test_policy_constant_is_matriz_row_of_the_semantics_matrix` pins as a constant.
The lock-8 comment justifies a branch that cannot execute.

**Fix:** Either drop the conditional and pass `sink`, or keep it and say in the
comment that it is defence-in-depth for a `POLICY` flip rather than a live path.

---

### IN-03: `_FIELD_EXEMPTIONS` keys are class-qualified but not package-qualified

**File:** `tools/check_surface_types.py:257-259`

**Issue:** The table is keyed `"UnknownFrame.raw"`. The docstring's whole argument
for not putting it in `_is_exempt` is that a bare `raw` *"would spare every member
named `raw` in all six packages"* (`:233-236`) — but a class named `UnknownFrame`
in a second package gets the same free pass. The gate already threads
`package_dir.name` into every violation message (`:769`), so the key could be
fully qualified at no cost.

**Fix:** Key on `f"{package}.{qualified}"` and update
`test_the_catch_all_frame_exemption_absorbs_a_real_hit_and_is_counted`, which
currently exercises a synthetic `fake-client` package and would otherwise stop
matching.

---

### IN-04: unreachable arm in `_is_none`

**File:** `tools/check_surface_types.py:521-526`

**Issue:** `_base_name(node) == "None"` can only match `ast.Name(id="None")`,
which no Python 3 parser produces — `None` is a keyword and always parses to
`ast.Constant`, handled by the branch above it.

**Fix:** Delete the second arm, or add a comment stating it is a py2-era
defensive remnant so a reader does not go looking for the shape that reaches it.

---

### IN-05: `matriz_client` is the only package whose `__init__.py` declares no `__version__`

**File:** `packages/matriz-client/src/matriz_client/__init__.py:109-184`

**Issue:** The project conventions call for *"`__version__` string"* in each
package `__init__.py`, and the other five packages have one; matriz has none and
`__all__` does not list it. `__init__.py` was modified this phase (three model
names added), so the gap is in scope.

**Fix:**

```python
__version__ = "0.2.0"
```

and add `"__version__"` to `__all__`, matching the sibling packages. Note the
surface snapshot will need regenerating.

---

### IN-06: the test validating the regenerated surface snapshot does not run in CI

**File:** `verification/snapshots/matriz-client-surface.txt`

**Issue:** This phase regenerated the snapshot (correctly — `pytest -q
verification/test_public_surface.py` passes locally, 4 passed). But
`.github/workflows/ci.yml:80-83` runs an **explicit two-file list** from
`verification/`, and `test_public_surface.py` is not on it. The snapshot is
therefore an unvalidated artifact in CI: a stale or hand-edited one — which its
own header warns against — would ship green. The `check_surface_types.py`
docstring documents this same `verification/`-never-runs fact at `:66-72`.

**Fix:** Add `verification/test_public_surface.py` to the explicit list in the
`lint` job, alongside the two market-data driver locks already there.

---

_Reviewed: 2026-08-29T16:59:50Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
