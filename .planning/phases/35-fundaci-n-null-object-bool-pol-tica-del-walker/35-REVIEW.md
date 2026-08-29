---
phase: 35-fundaci-n-null-object-bool-pol-tica-del-walker
reviewed: 2026-08-29T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - packages/ambito-financiero-client/src/ambito_financiero_client/_decode.py
  - packages/ambito-financiero-client/tests/test_decode.py
  - packages/ambito-financiero-client/tests/test_null_object.py
  - packages/higyrus-client/src/higyrus_client/_decode.py
  - packages/higyrus-client/src/higyrus_client/models.py
  - packages/higyrus-client/tests/test_decode.py
  - packages/higyrus-client/tests/test_null_object.py
  - packages/iol-client/src/iol_client/_decode.py
  - packages/iol-client/src/iol_client/models.py
  - packages/iol-client/tests/test_decode.py
  - packages/iol-client/tests/test_null_object.py
  - packages/market-data-client/src/market_data_client/_decode.py
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/tests/test_core.py
  - packages/market-data-client/tests/test_decode.py
  - packages/market-data-client/tests/test_null_object.py
  - packages/matriz-client/src/matriz_client/_decode.py
  - packages/matriz-client/src/matriz_client/models.py
  - packages/matriz-client/tests/test_decode.py
  - packages/matriz-client/tests/test_null_object.py
  - packages/wallets-client/tests/test_null_object.py
  - tools/check_decode_intactness.py
findings:
  critical: 0
  warning: 10
  info: 5
  total: 15
status: issues_found
---

# Phase 35: Code Review Report

**Reviewed:** 2026-08-29
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

I re-ran every mechanical check this phase claims and all of them pass: `uv run pytest packages -q`
(1947 passed), `ruff check .` + `ruff format --check .`, `uv run mypy` plus the six per-package
`mypy packages/*/tests` legs, and all four v1.6 gates (`check_decode_intactness`,
`check_surface_types`, `check_uniform_structure`, `surface_parity`) exit 0. The five `_decode.py`
copies do reduce to one normalized hash matching the bumped `CANONICAL_DIGEST`.

I then attacked the four named invariants directly and could not falsify them:

- the list-site silence gates on `if value is not None:` — an **identity** test, not truthiness
  (verified: `{"hojas": "garbage"}` still emits `type` and still raises under `strict_decode`);
- `empty()` is a direct `walk_model(cls, {}, sink=SILENT_SINK)` in all four hierarchies — never
  `cls.from_api(None)`;
- `bool(X.from_api(None)) is False` and one perturbed field flips truthy across all shipped rosters;
- the model-site collapse cannot swallow an optional field's null: the `Union` arm returns before
  `_is_model` for every `T | None`, and I confirmed the change does not over-reach — a top-level
  `None` body still emits `non_dict`, a `str`/`list` where a model is declared still emits
  `non_dict`, and a `dict` where a list is declared still emits `type`.

**I found no provable correctness, security, or data-loss defect. There are no BLOCKERs.**

What I did find is a substantial and consistent **documentation-versus-code drift**: the phase
edited `_decode.py`'s docstrings in all five copies but left four `models.py` module docstrings and
four per-model/per-function docstrings asserting the *retired* contract — including two that were
the recorded justification for a nullability decision (T-31-17). I verified each of those claims is
now empirically false. Beyond that, three of the phase's own new/inverted tests are weaker than
they read: the criterio-5 alias pair is now vacuously `[] == []` in four packages, and matriz's two
inverted assertions use negative membership where the other four packages use equality.

There are no structural findings to reconcile (no `<structural_findings>` block was supplied).

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Four `models.py` module docstrings assert a reporting contract the walker no longer has

**Files:**
- `packages/higyrus-client/src/higyrus_client/models.py:22-30`
- `packages/iol-client/src/iol_client/models.py:24-30`
- `packages/market-data-client/src/market_data_client/models.py:39-49`
- `packages/matriz-client/src/matriz_client/models.py:15-19`

**Issue:** Each of the four says, in some wording, that *every* substituted default now emits a
record — e.g. higyrus: "each substitution now emits a structured divergence record on the
`higyrus_client` logger"; iol: "Every substitution emits a structured divergence record"; matriz:
"additionally reports every substituted default as a structured record". After NOBJ-02 that is
false for two whole substitution classes (null/absent on a non-optional list link and on a
non-optional model link). The `_decode.py` docstrings were amended for exactly this reason in all
five copies; the `models.py` twins that make the same claim were not. A reader of the shipped
wheel gets the pre-35 contract.

**Fix:** Mirror the `_decode.py` amendment into each of the four, e.g.

```rst
What is new is *reporting*: each substitution now emits a structured divergence
record on the ``higyrus_client`` logger — except the two collapses Phase 35 /
NOBJ-02 declares legitimate (a null or absent value on a non-optional list- or
model-typed field, which substitutes ``[]`` / the empty instance silently).
```

---

### WR-02: Two market-data model docstrings state a per-field disposition that is now empirically false

**File:** `packages/market-data-client/src/market_data_client/models.py:1065-1068`, `:1164-1165`

**Issue:** `Health` documents "an absent `auth` key yields the ZERO-VALUED `HealthAuth` **plus a
`missing` divergence record**", and `FeedIngestor` documents "`market` and `pipeline` are
non-optional nested models, so an absent key yields the zero-valued instance **plus a `missing`
record**". Both are now wrong. Measured:

```
Health.from_api({"status": "ok"})            -> records: []      (was [(".auth", "missing")])
FeedIngestor.from_api({"connected": True})   -> 12 scalar `missing` records, none for
                                                 `.market` or `.pipeline`
Health.from_api({"status":"ok"}) under STRICT_DECODE -> no raise (previously fatal)
```

The corresponding test assertion in `tests/test_core.py` *was* inverted; the docstrings that
describe the same behaviour were not.

**Fix:** Rewrite both to the new disposition and note the strict-mode consequence:

```rst
:attr:`auth` is declared as the non-optional nested :class:`HealthAuth`, so an
absent ``auth`` key yields the ZERO-VALUED ``HealthAuth`` and — since Phase 35 /
NOBJ-02 — emits NOTHING and is not fatal under ``strict_decode``. Ask
``if health.auth:`` rather than relying on the census to surface it.
```

---

### WR-03: `_mapping_value` docstrings claim parity with "every other axis" that no longer holds, and the resulting three-way asymmetry is undocumented in shipped source

**Files:**
- `packages/matriz-client/src/matriz_client/models.py:122-124`
- `packages/market-data-client/src/market_data_client/models.py:147-151`

**Issue:** Both say reporting "matches what the walker emits for any other substituted default —
`missing` when the payload carried nothing, `type` otherwise — so lock 2's kind, lock 3's WARNING
level and lock 4's strict disposition all apply here exactly as they do on every other axis." That
is no longer true. Measured on matriz `InstrumentDetail`:

```
{"tickPriceRanges": None, "orderTypes": None, "segment": None}
  -> records: [('InstrumentDetail', '.tickPriceRanges', 'missing', 'dict', 'NoneType')]
  -> under strict: MatrizDecodeError on .tickPriceRanges only
```

Three collection kinds, three different dispositions for the same "the wire sent null / nothing"
event: `list` → silent, nested model → silent, `dict` → WARNING record + strict-fatal. The carve-out
is deliberate (35-RETIRED-TRIPLES.md D-03c) and both sides are pinned by tests, but nothing in the
shipped source states it side by side, so a consumer reading `_decode.py`'s "the two collapses
Phase 35 / NOBJ-02 declares legitimate" has no way to learn that a third collection kind does the
opposite.

**Fix:** Amend both `_mapping_value` docstrings to state the delta explicitly, e.g. "Since Phase 35
this axis is deliberately NOT aligned with the walker's list/model collapse (D-03c): a null or
absent mapping still reports `missing` and is still fatal under strict mode. Phase 36 retires this
machinery." Add the same one-liner to the `_decode.py` docstring bullet so the shipped walker
names the exception it does not cover.

---

### WR-04: The T-31-17 nullability rationale is invalidated for model- and list-typed fields but left in place

**File:** `packages/market-data-client/src/market_data_client/models.py:1026-1036`

**Issue:** The "NULLABILITY VERDICT (option-b / Restraint)" block justifies declaring nine
under-determined fields non-nullable with: "a wrong non-null guess surfaces LOUDLY in Phase 33's
strict driver run ... whereas an over-declared `Optional` would SILENTLY and permanently hide that
field from the divergence census." After NOBJ-02 the non-null declaration *also* hides it silently
for every model-typed and list-typed field. That covers at least `Health.auth`,
`HealthFeed.ingestor`, `FeedIngestor.market`, `FeedIngestor.pipeline`, `AddHolidaysResult.days`,
`CalendarConfigPreview.market_after`, `CalendarConfig.warnings` and `CalendarConfigPreview.warnings`
— i.e. the declaration no longer buys the detection it was chosen for. Phase 39's live census will
under-count against Phase 33's baseline for exactly these links, and the comment that would have
warned the next reader now argues the opposite of what the code does.

**Fix:** Add a Phase 35 amendment to the block stating that the loud/silent argument survives only
for **scalar** leaves and for wrong-typed values, and that model/list links are now silent on null
regardless of the `| None` decision. Cross-reference `35-RETIRED-TRIPLES.md` so the Phase 39
comparison is done against the retired-triples subtraction rather than against the raw Phase 33
number.

---

### WR-05: The criterio-5 `@property`-alias test is now vacuous in four packages

**Files:**
- `packages/higyrus-client/tests/test_null_object.py:258-275`
- `packages/iol-client/tests/test_null_object.py` (same test)
- `packages/market-data-client/tests/test_null_object.py:297-314`
- `packages/matriz-client/tests/test_null_object.py:314-331`
- `packages/ambito-financiero-client/tests/test_null_object.py:192-209`

**Issue:** The test's stated job is "the alias cannot fabricate a divergence nor suppress one", and
it asserts `_records(shaped_records) == _records(free_records)`. Both fixtures declare exactly two
fields — `LA: _Leaf` (nested model) and `BI: list[_Leaf]` — which are precisely the two shapes
NOBJ-02 just silenced. Verified:

```
walk_model(_AliasShaped, {}, ...) -> records: []
                                     kwargs: {'LA': _Leaf(nombre='', dias=0), 'BI': []}
```

The comparison is now `[] == []` on every one of the five copies. The docstring anticipates that
plan 35-05 "changes what the walker emits for a non-optional link carrying nothing" and concludes
the test "must survive that change untouched" — it survived by becoming unable to fail. The only
substance left is `shaped.LA == free.LA` / `shaped.BI == free.BI` / `shaped.last is shaped.LA`.

**Fix:** Give both fixtures a scalar field so the record lists are non-empty on both sides, and
assert non-emptiness so the test cannot silently re-vacate:

```python
@dataclass(frozen=True, slots=True)
class _AliasShaped(SafeModel):
    titulo: str          # scalar leaf — still reports `missing`, so the pair is non-vacuous
    LA: _Leaf
    BI: list[_Leaf]
    ...

# in the test:
assert shaped_records, "fixture must produce at least one record or this test is vacuous"
assert _records(shaped_records) == _records(free_records)
```

---

### WR-06: matriz's two inverted assertions are strictly weaker than the four peer packages'

**File:** `packages/matriz-client/tests/test_decode.py:532`, `:1266`

**Issue:** Of the 11 inverted assertions, nine assert equality against `[]`. matriz's two assert
negative membership:

```python
assert (".rows", "missing") not in _pairs(caplog)                      # :532
assert ("_Nested", ".leaf", "missing") not in triples                   # :1266
```

Both would stay green if the walker started emitting a *different* record at the same site — e.g.
`(".rows", "type")` or `("_Nested", ".leaf", "type")` — which is exactly the mis-scoped-silencing
failure mode the phase's own new tripwire tests were written to catch. The companion tripwire
`test_wrong_typed_list_field_still_reports_type` deliberately uses equality "so a second, spurious
record would fail it too"; these two do not get that protection. `_Nested.tag` is `str | None`, so
the record list is empty in both cases and the equality form is available.

**Fix:** Use the same equality form as the other four packages:

```python
assert _pairs(caplog) == []                                             # :532
assert triples == []                                                    # :1266  (drops the
                                                                        #  separate non_dict check,
                                                                        #  which it subsumes)
```

---

### WR-07: The 11th inverted assertion carries none of the phase's documentation discipline

**File:** `packages/market-data-client/tests/test_core.py:1052-1060`

**Issue:** Ten of the eleven inversions gained a "Phase 35, NOBJ-02 / D-13: this assertion was
inverted deliberately, not weakened" paragraph and, in most cases, a renamed test. This one changed
`[(".auth", "missing")]` to `[]` with no docstring change and no rename. The remaining docstring —
"A declared non-optional nested model is NEVER `None` — it is the zero instance" — is still true but
says nothing about the record assertion, so a future reader has no in-file signal that the empty
list is a decision rather than a weakening. That is precisely the "assertion nobody can tell was
deliberate" failure the other ten guard against.

**Fix:** Add the same paragraph and rename to match the peers:

```python
def test_health_from_api_missing_auth_yields_zero_valued_nested_model_silently(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A declared non-optional nested model is NEVER ``None`` — it is the zero instance.

    Phase 35, NOBJ-02 / D-13: the records assertion was inverted deliberately,
    not weakened. The returned VALUE below is byte-unchanged.
    """
```

---

### WR-08: WR-02's "decode site that does not exist" defect is still live, and the new comment now endorses it

**Files:** all five `_decode.py` copies, e.g.
`packages/higyrus-client/src/higyrus_client/_decode.py:478-506`

**Issue:** The Phase 29 WR-02 rationale — retained verbatim inside the new Phase 35 comment — argues
that a `non_dict` record "attributed to the NESTED class at a path rooted in the outer decode" is
"a `(model, field_path)` pair naming a decode site that does not exist, which lock 10 then freezes
into a Phase 33 finding identity". The new paragraph immediately above it then blesses exactly that
shape for the non-null case: "A genuinely non-dict, non-null payload ... still earns its record with
the nested-model attribution". Measured:

```
Health.from_api({"status":"ok","auth":"garbage"}) -> [('HealthAuth', '.auth', 'non_dict')]
Health.from_api({"status":"ok","auth":[]})        -> [('HealthAuth', '.auth', 'non_dict')]
```

`HealthAuth` has no field `.auth`; the pair still names a nonexistent decode site, and lock 10 will
still freeze it into a finding identity. The `value is None` guard *is* load-bearing (removing it
would restore the record for the null case too), so the claim that the classification order
survives is defensible — but the defect WR-02 named is now permanently unaddressed for the whole
wrong-typed half, with the argument against it quoted approvingly two paragraphs away.

**Fix:** Either re-attribute the non-null nested case to the outer model — `sink(model, path,
"type", _name_of(hint), type(value).__name__)` before recursing with `SILENT_SINK`, which keeps the
strict raise and gives lock 10 a real decode site — or, if the current attribution is intended,
delete the WR-02 counter-argument from the comment and record the decision, because as written the
same block argues both ways. Note that changing the record shape requires re-running the intactness
gate and bumping `CANONICAL_DIGEST`.

---

### WR-09: `bool()` on the publicly exported base class now raises `TypeError`

**Files:** `packages/higyrus-client/src/higyrus_client/models.py:95-118`,
`packages/iol-client/src/iol_client/models.py:114-137`

**Issue:** `SafeModel` is in both `higyrus_client.__all__` and `iol_client.__all__`. Before Phase 35
`bool(SafeModel())` was `True` and total. Now:

```
SafeModel.empty()   -> TypeError: must be called with a dataclass type or instance
bool(SafeModel())   -> TypeError: must be called with a dataclass type or instance
```

`__bool__` runs a full `walk_model` (`dataclasses.fields` + `get_type_hints` + recursive nested
construction) and propagates anything it raises. This is the same class of regression `_decode._emit`
lock 9 exists to prevent — "a library that previously substituted silently must not begin crashing"
— applied to a dunder that arbitrary consumer code invokes implicitly via `if model:`. The exposure
is narrow (nobody instantiates the abstract base in practice, and any subclass decodable by
`from_api` is also `empty()`-able, since `from_api` already calls `hints_for`), which is why this is
a WARNING and not a BLOCKER.

**Fix:** Make the failure explicit and package-scoped rather than an opaque stdlib `TypeError`:

```python
def __bool__(self) -> bool:
    if not dataclasses.is_dataclass(type(self)):
        raise TypeError(
            f"{type(self).__name__} is the abstract SafeModel base; truthiness is "
            "only defined for frozen-dataclass subclasses"
        )
    return self != type(self).empty()
```

(or mark the base `abstract`/non-instantiable, or drop `SafeModel` from `__all__`.)

---

### WR-10: The D-09 truthiness caveat is documented in four docstrings but pinned by no test, and the one test that touches it is green only on a path the shipped client never takes

**Files:**
- `packages/market-data-client/tests/test_null_object.py:229-245`
- `packages/market-data-client/src/market_data_client/models.py:286-293` (and the three peer
  `__bool__` docstrings)

**Issue:** All four `__bool__` docstrings rest on the D-09 caveat that a model stamping a
client-side value after the walk "differs from its `empty()` and is therefore truthy even when the
wire carried nothing at all". The test suite asserts only the opposite half:
`bool(MarketDataSnapshot.from_api(None)) is False`, which holds solely because the `received_at`
keyword defaults to `0.0` on that path. The shipped client never takes it —
`_core.py:928` and `:966` both call `MarketDataSnapshot.from_api(item, received_at=received_at)`
with a `time.time()` stamp — so the flagship model of `market-data-client` is unconditionally truthy
in production. The test docstring honestly labels its own green as "structural, not semantic", which
is an accurate description of a test that cannot fail for the reason it claims to check, and nothing
pins the semantic half.

**Fix:** Add the missing falsification so a future change to the stamping cannot flip the semantics
undetected:

```python
def test_a_client_stamped_snapshot_is_truthy_even_on_an_empty_wire() -> None:
    """D-09: emptiness is a FIELD-level question for stamped models."""
    stamped = models.MarketDataSnapshot.from_api(None, received_at=1.0)
    assert bool(stamped) is True
    assert not stamped.entries and not stamped.market_data
```

## Info

### IN-01: Module docstrings still document nested defaults as `X.from_api(None)`, which `empty()` explicitly forbids

**Files:** `packages/higyrus-client/src/higyrus_client/models.py:11`,
`packages/iol-client/src/iol_client/models.py:11`,
`packages/market-data-client/src/market_data_client/models.py:11`

**Issue:** The default table reads "nested `SafeModel` -> `X.from_api(None)` (empty instance)".
The walker actually builds `hint(**walk_model(hint, {}, sink=SILENT_SINK))`, and the `empty()`
docstring twenty lines below says "Phase 35 D-07 prohibits expressing this constructor as
`cls.from_api(None)`". Two adjacent docstrings in the same file now name that construction as both
the behaviour and the prohibited form.

**Fix:** Change the bullet to `nested SafeModel -> X.empty() (the all-defaults instance)`.

---

### IN-02: `_decode.py` docstring under-counts the per-package deltas the gate normalizes

**Files:** all five `_decode.py` copies, e.g.
`packages/higyrus-client/src/higyrus_client/_decode.py:35-39`

**Issue:** "The only per-paquete deltas are the paquete name in this docstring, the `POLICY`
assignment, the `_LOGGER_NAME` literal and the decode exception imported from `exceptions`" — four
items. `tools/check_decode_intactness.py` normalization rule 5 also replaces the two `ContextVar`
name string literals (`"<pkg>_strict_decode"`, `"<pkg>_decode_scope"`), and rule 6 replaces every
remaining occurrence of the import name. Pre-existing, but the file is being edited in this phase.

**Fix:** Add the ContextVar names to the list, or point at the gate's rule list as the authority.

---

### IN-03: "cero cambios de superficie pública" is not true and no gate can check it

**Files:** `packages/{higyrus,iol,market-data}-client/src/*/models.py` (`empty()` classmethod),
`tools/check_surface_types.py`

**Issue:** The phase criterion claims zero public-surface change, but `empty()` is a new public
classmethod on three previously-`empty()`-less hierarchies and `__bool__` is a public behaviour
change on all four. `check_surface_types.py` scans `__all__` names and top-level definitions
(180 names / 324 definitions), not methods, so no gate could have detected either. The claim is
therefore unverified rather than verified-true.

**Fix:** Restate the criterion as "no signature change to any existing public callable", or extend
`surface_parity.py` to snapshot public method names per exported class.

---

### IN-04: The truthiness flip has no documentation home outside docstrings for five of six packages

**Files:** `packages/*/README.md`

**Issue:** No package README mentions `empty()`, `__bool__`, truthiness, or the flip. `if model:`
silently changed meaning for every consumer of the four published hierarchies. ROADMAP Phase 40
covers the coordinated breaking release and Phase 38 criterion 1 names iol's README specifically —
higyrus, market-data and matriz have no named documentation deliverable for the same flip.

**Fix:** Track the README/migration entry for the other three packages explicitly in Phase 40's
per-package migration table, so it is not inherited only by iol.

---

### IN-05: `_perturb` writes type-invalid sentinels into typed fields

**Files:** `packages/{higyrus,iol,market-data,matriz}-client/tests/test_null_object.py`, the
`if cur is None:` branch (e.g. `higyrus .../test_null_object.py:119-120`)

**Issue:** The first branch substitutes the string `"SENTINEL"` into whatever field happens to be
`None` — including `float | None`, `int | None` and `MarketId | None` fields. The resulting instance
could never be produced by the walker, so the truthiness falsification is proven against a value
the wire cannot send. It is sound for an equality-based `__bool__`, but it would silently stop
being sound if `__bool__` ever grew type-aware logic.

**Fix:** Dispatch on the declared hint rather than on the current value, or at minimum use a
type-appropriate sentinel per branch (`1.0` for float-typed, `1` for int-typed, `"SENTINEL"` for
str-typed).

---

_Reviewed: 2026-08-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
