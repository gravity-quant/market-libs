---
phase: 36-market-data-client-market-data-tipado-revocacion-de-la-fase-33
reviewed: 2026-08-29T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - main_market_data.py
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/tests/test_core.py
  - packages/market-data-client/tests/test_decode.py
  - packages/market-data-client/tests/test_market_data_chain.py
  - packages/market-data-client/tests/test_models.py
  - packages/market-data-client/tests/test_null_object.py
  - packages/market-data-client/tests/test_public_surface_market_data.py
  - packages/market-data-client/tests/test_snapshot_no_data_row.py
  - verification/test_main_market_data_deep_chain.py
findings:
  critical: 2
  warning: 6
  info: 0
  total: 8
status: issues_found
---

# Phase 36: Code Review Report

**Reviewed:** 2026-08-29
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 36 turns `MarketDataSnapshot.market_data` from a `dict[str, Any] | None`
passthrough into the typed Null Object `MarketDataEntries` (+ `BookLevel` /
`EntryValue` + six read-only aliases), revokes the Phase 33 widening on the two
chain links, retires `_mapping_value` / `_apply_mapping_policy`, and adds an AST
lock demanding the driver consume the chain.

Baseline health was verified, not assumed: `pytest` (711 passed), `ruff check`,
`ruff format --check`, `mypy` over the phase's files, `check_decode_intactness`,
`check_uniform_structure`, `check_surface_types` and `lint-imports` all pass. The
decode digest did not move, which is the load-bearing claim of the mapping
retirement.

The defects are not in the model layer — that layer is well-tested and behaves as
documented. They are at the seams the phase opened and did not re-check:

1. Making `market_data` a nested `SafeModel` silently switched on recursion in
   `verification/safemodel_diff.py`, which now manufactures FALSE-PASS findings
   for exactly the links Phase 35's NOBJ-02 policy just declared legitimate. This
   was reproduced, not inferred.
2. The regression fixtures that claim to mirror the committed
   `get-latest.json` baseline do not: the real no-data row still raises under
   `strict_decode`, and the test asserting the opposite passes only because its
   fixture was populated in two fields the baseline sends as `null`. Also
   reproduced.
3. The SC-5 structural lock the phase delivered lives under `verification/`,
   which CI never executes — the workflow's own comments say so.

## Structural Findings (fallow)

No `<structural_findings>` block was supplied with this review request.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: SHAPE-diff now fabricates `model-only` findings for the six non-optional Null Object links

**File:** `main_market_data.py:698` (skip set), `main_market_data.py:115`
(`_ENDPOINT_OPTIONAL`), with `packages/market-data-client/src/market_data_client/models.py:329-338`
and `verification/safemodel_diff.py:144-160`

**Issue:**
Before this phase `market_data` was declared `dict[str, Any] | None`, so
`_nested_safemodel_class` returned `None` and `diff_safemodel_bidirectional`
stopped at the opaque dict. Declaring it `MarketDataEntries` turns recursion on.
Six of the ten roster fields — `BI`, `OF` (`list[BookLevel]`) and `CL`, `LA`,
`OI`, `SE` (`EntryValue`) — are **non-optional**, so `_is_optional` is `False` for
them and every row whose `market_data` object omits an entry key yields a
`model-only` tuple, which `_emit_shape` writes to the append-only ledger as a
`SHAPE` / FALSE-PASS-risk finding.

Reproduced against the shipped code:

```
$ python -c "... diff_safemodel_bidirectional(row, MarketDataSnapshot) ..."
('',              'model-only', 'received_at')   # suppressed by _CLIENT_STAMPED
('.market_data',  'model-only', 'BI')
('.market_data',  'model-only', 'CL')
('.market_data',  'model-only', 'OF')
('.market_data',  'model-only', 'OI')
('.market_data',  'model-only', 'SE')
```
(row = a `/marketdata` item carrying only `LA` under `market_data`.)

Two things make this a blocker rather than cosmetic noise:

- It **directly contradicts the policy this milestone just adopted.** NOBJ-02
  (`_decode.py:478-503`) states that a null or absent value on a non-optional
  list or nested-model link is a legitimate payload shape that "emits NOTHING".
  The driver's differ classifies the same absence as a FALSE-PASS-risk defect.
  The two halves of the phase disagree about the same fact.
- The phase's **own fixtures** treat a partial `market_data` as a producible
  vendor shape: `tests/test_snapshot_no_data_row.py:77` (`_POPULATED_ROW` carries
  only `BI`) and `tests/test_market_data_chain.py:138` (`_MD_EMPTY` carries `{}`).
  So the trigger is not hypothetical; the Phase 39 live run writes these into
  `.planning/verification/market-data-client-findings.md`, which is committed to
  git and is the artifact the milestone's divergence census is measured from.

The driver's existing suppression sets are key-based and path-agnostic, so
extending them is not safe either — `_CLIENT_STAMPED | _ENDPOINT_OPTIONAL |
_DEPRECATED_ALIAS` would start suppressing a genuine `BI` omission on any other
model. The fix belongs in the differ, where the link/leaf distinction lives.

**Fix:** teach `diff_safemodel_bidirectional` the same link rule the walker
already applies — a non-optional field whose declared type is a nested
SafeModel-like or `list[SafeModel-like]` is a Null Object link, and its absence
is not a divergence:

```python
# verification/safemodel_diff.py, Direction A loop
for key in sorted(model_keys - wire_keys):
    hint = hints[key]
    if _is_optional(hint):
        continue
    # NOBJ-02 (Phase 35): a Null Object LINK collapses to its empty instance /
    # [] and is NOT a divergence. Only scalar LEAVES can be a false pass.
    if _nested_safemodel_class(hint) is not None:
        continue
    yield (path, "model-only", key)
```

and add a driver-level regression row asserting that
`_emit_shape(partial_market_data_row, MarketDataSnapshot, ...)` returns `0`.

---

### CR-02: the no-data-row regression fixtures do not match the baseline they cite; the real row still raises under `strict_decode`

**File:** `packages/market-data-client/tests/test_snapshot_no_data_row.py:61-69`
and `:140-158`; `packages/market-data-client/tests/test_market_data_chain.py:119-130`

**Issue:**
`test_snapshot_no_data_row.py:59-60` states the fixture is *"the exact shape of
the committed get-latest.json baseline"*, and the module docstring says the row
carries *"`symbol` + `note` and `null` everywhere else"*. The committed baseline
`.planning/verification/schemas/market-data-client/get-latest.json` is:

```json
{"active":"NoneType","market_data":"NoneType","market_id":"NoneType",
 "note":"str","received_at":"NoneType","staleness_seconds":"NoneType","symbol":"str"}
```

The fixture instead sets `"market_id": "ZZZ"` and `"active": False` — the two
fields the baseline sends as `null`. `test_market_data_chain.py`'s `_MD_NULL`
(described at `:119-121` as "the shape of the no-data row of get-latest.json")
does the same.

`MarketDataSnapshot.market_id` is `str` and `.active` is `bool`, both
non-optional scalar **leaves**, so the walker reports `missing` and strict mode
raises. Reproduced against the real baseline shape:

```
$ python -c "STRICT_DECODE=True; MarketDataSnapshot.from_api(real_row, received_at=1.0)"
RAISED: MarketDataDecodeError decode divergence in MarketDataSnapshot.market_id:
        declared str, observed NoneType
```

Consequences:

- `test_no_data_row_is_not_fatal_under_strict_decode` (and its async twin) is
  the test the module calls *"the assertion with teeth"*. Against the payload it
  claims to represent it would be red. It is green only because the fixture was
  populated.
- `test_market_data_chain.py`'s header claims the matrix covers *"the FOUR
  payloads the vendor can actually produce"*. It covers three producible shapes
  and one synthetic one; the measured no-data row is absent from the matrix.
- The `MarketDataEntries` docstring
  (`models.py:325-326`) claims the chain answers *"for every payload the vendor
  can produce"*. That claim is unverified for the one payload the repo has
  actually measured.

The model change itself is fine — the chain does stay walkable — but the phase's
regression guard does not demonstrate it against the real row, and Phase 39's
strict pass will raise on `.market_id` / `.active` with nothing in the repo
having predicted it.

**Fix:** make the fixture the baseline, and split the assertion so the surviving
leaf divergence is stated rather than hidden:

```python
# the committed get-latest.json shape, verbatim
_NO_DATA_ROW: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": None,
    "active": None,
    "market_data": None,
    "received_at": None,
    "staleness_seconds": None,
    "note": "sin datos para el simbolo",
}

def test_no_data_row_links_are_never_fatal_under_strict_decode(...):
    """The two LINKS collapse silently; the two over-declared LEAVES still raise."""
    with pytest.raises(MarketDataDecodeError) as exc:
        ...   # strict client
    assert exc.value.field_path in {".market_id", ".active"}   # NOT .market_data / .entries
```

and either widen `market_id` / `active` by field role (they are leaves with
nothing to point at on this row — the same D-NO-03 argument that kept
`staleness_seconds | None`), or file them explicitly as a deferred item so
Phase 39 does not rediscover them as a surprise.

## Warnings

### WR-01: the SC-5 structural lock delivered by this phase never runs in CI

**File:** `verification/test_main_market_data_deep_chain.py:1-181`;
`.github/workflows/ci.yml:129-133`

**Issue:** the `test` job runs `pytest packages/${{ matrix.package }}`, an
explicit path that overrides `testpaths = ["packages", "tests", "verification"]`
(`pyproject.toml:106`). No other job touches `verification/`. The workflow states
this itself three times (`ci.yml:53-54`, `:58-59`, `:63-64`: *"el job `test` pasa
un path explícito que pisa `testpaths`, así que ese directorio nunca corrió en
CI"*), which is why the three cross-package gates were implemented as `lint`
steps instead. The new deep-chain lock — the entire mechanism preventing a future
refactor from reverting the probes to row counts — was placed in the one
directory that is guaranteed not to execute. It is inert.

**Fix:** either add a `lint`-job step following the established precedent, e.g.

```yaml
      - name: deep-chain lock (Phase 36 SC-5 — el driver consume la cadena tipada)
        run: uv run pytest verification/test_main_market_data_deep_chain.py -q
```

or re-express it as `tools/check_deep_chain.py` alongside the other three
cross-cutting gates. This is a known repo-wide gap (backlog `HARN-VERIF-01`), but
shipping a new guard into it makes the gap load-bearing for this phase.

---

### WR-02: the ten-key roster silently drops any entry type outside it, on a field that used to be a passthrough

**File:** `packages/market-data-client/src/market_data_client/models.py:310-338`

**Issue:** `market_data` was `dict[str, Any]` — every key the vendor sent was
readable. It is now a closed ten-field dataclass, so an eleventh key is
**discarded**: the value never reaches the caller and the only signal is an
`extra` record at `logging.INFO` on a logger that ships a `NullHandler`
(`__init__.py:35-38`), i.e. invisible unless the consumer configured handlers.

This is not speculative. `matriz-client`, which reads the same upstream Primary
feed, declares four more entry types on its twin model —
`packages/matriz-client/src/matriz_client/models.py:424-427` (`IV`, `EV`, `NV`,
`ACP`). The docstring's D-02 rationale ("this paquete declares what its own
capture measured") is defensible for *typing*, but the consequence is data loss
on a published read surface, not merely an untyped field.

**Fix:** either widen the roster to matriz's fourteen (the four extras are all
`float | None`, cost is four lines and no behaviour change when absent), or keep
the ten and add an explicit escape hatch so nothing is unreachable:

```python
    @property
    def unknown(self) -> dict[str, Any]:
        """Entry types outside the declared roster — see the ``extra`` records."""
```
backed by a captured-extras field. At minimum, promote the `extra` record for
this container from INFO to WARNING so it is not silent by default.

---

### WR-03: stale cross-package contract in `matriz_client.models` now asserts a synchronization that no longer exists

**File:** `packages/matriz-client/src/matriz_client/models.py:115-120`

**Issue:** the shipped docstring of matriz's `_mapping_value` still reads:

> *"market-data declares a mapping field too (`MarketDataSnapshot.market_data`)
> and never received the compensating pass ... `market_data_client.models` now
> carries a verbatim copy of this function and of `_apply_mapping_policy`; **the
> two must stay identical**."*

Phase 36 deleted both helpers from market-data. The paragraph now instructs a
future maintainer to keep two functions in sync when one of them does not exist,
and names a market-data field that is no longer a mapping. Nothing in CI checks
docstring claims, so this survives indefinitely and will mislead Phase 37, which
touches exactly this file.

**Fix:** amend the paragraph in `matriz_client/models.py` to record the
retirement, e.g. *"Phase 36 retired market-data's copy together with its
`dict`-declared field (`market_data` is the typed Null Object
`MarketDataEntries` now); this axis is matriz-only again."* Also check
`.planning/.../29-SEMANTICS-MATRIX.md` Section 2, whose `file:line` citation for
market-data's mapping axis is now dangling.

---

### WR-04: `main` carries a second, source-incompatible `0.5.0`

**File:** `packages/market-data-client/src/market_data_client/__init__.py:163`;
`packages/market-data-client/pyproject.toml:3`

**Issue:** `MarketDataSnapshot.market_data` changed from `dict[str, Any] | None`
to `MarketDataEntries`, `MarketDataSnapshot.entries` and `LatestRequest.entries`
lost their `| None`, and `LatestRequest(entries=[]).to_dict()` stopped emitting
the `entries` key. All four are source-breaking, and the version string is still
`0.5.0` — the same version already tagged and released with the previous shape
(`market-data-client-v0.5.0`). Anyone installing from `main` gets an artifact
that claims to be 0.5.0 and is not. `snapshot.market_data["LA"]["price"]` now
raises `TypeError: 'MarketDataEntries' object is not subscriptable`.

Phase 40 owns the coordinated bump by design (`ROADMAP.md:46`, and the migration
table at `:154` names this exact rename), so the deferral is deliberate — but the
window between 36 and 40 spans three more phases with no marker in the package
itself.

**Fix:** set a pre-release marker now so the artifact is self-describing and let
Phase 40 finalise it:

```toml
version = "0.6.0.dev0"    # Phase 40 finalises the coordinated breaking bump
```
(and mirror it in `__version__`). Alternatively add a `CHANGELOG.md`
`## Unreleased — BREAKING` entry so the break is discoverable from the package.

---

### WR-05: `chained={len(chained)}` in the probe detail cannot ever differ from the row count

**File:** `main_market_data.py:873`, `:916`, `:1215`, `:1257`

**Issue:** `chained` is a list comprehension over `snapshots` / `latest` with no
filter, so `len(chained) == len(snapshots)` by construction, always. The rendered
detail — `snapshots=N chained=N` — reads like an independent measurement ("N rows
fetched, N chains successfully walked") in an artifact a human reads to judge a
live run, and it can never report anything else. If the chain broke, the probe
would be a `FINDING` and the line would not render at all.

**Fix:** report something the reader cannot get from the row count, or drop the
token:

```python
non_null = sum(1 for c in chained if c[1] is not None)   # rows with a last price
return ProbeResult(name, "PASS", f"snapshots={len(snapshots)} with_last={non_null}")
```

---

### WR-06: the batch (`POST /marketdata/latest`) decode path ships unexercised while the AST guard reports the probe as covered

**File:** `main_market_data.py:885` and `:1227`

**Issue:** `probe_latest_sync` / `probe_latest_async` fetch two independent
collections of `MarketDataSnapshot` — `latest` (GET) and `batch` (POST body) —
and the Phase 36 chain comprehension iterates only `latest`. `batch` is consumed
by `len()` alone, which is precisely the pattern
`verification/test_main_market_data_deep_chain.py:12-17` was written to forbid
("a probe whose body reads `f"...{len(snapshots)}"` passes green while every link
in the chain is broken"). The guard counts alias dereferences per *function*, not
per fetched collection, so it reports the probe as covered.

**Fix:** chain the batch rows too, and raise the non-vacuity floor accordingly:

```python
chained_batch = [
    (s.symbol, s.market_data.last.price, len(s.market_data.bids)) for s in batch
]
```
then bump `_MIN_CHAINED_ACCESSES` in the AST guard so the added consumption is
itself locked.

---

_Reviewed: 2026-08-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
