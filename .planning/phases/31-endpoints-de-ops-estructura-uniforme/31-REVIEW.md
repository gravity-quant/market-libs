---
phase: 31-endpoints-de-ops-estructura-uniforme
reviewed: 2026-08-25T00:00:00Z
depth: deep
files_reviewed: 38
files_reviewed_list:
  - .github/workflows/ci.yml
  - main_higyrus.py
  - main_market_data.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/models.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/types.py
  - packages/ambito-financiero-client/tests/test_decode.py
  - packages/higyrus-client/src/higyrus_client/__init__.py
  - packages/higyrus-client/src/higyrus_client/_core.py
  - packages/higyrus-client/src/higyrus_client/aio.py
  - packages/higyrus-client/src/higyrus_client/client.py
  - packages/higyrus-client/src/higyrus_client/models.py
  - packages/higyrus-client/src/higyrus_client/types.py
  - packages/higyrus-client/tests/test_async_client.py
  - packages/higyrus-client/tests/test_client.py
  - packages/higyrus-client/tests/test_core.py
  - packages/iol-client/src/iol_client/types.py
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/src/market_data_client/_core.py
  - packages/market-data-client/src/market_data_client/aio.py
  - packages/market-data-client/src/market_data_client/client.py
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/src/market_data_client/types.py
  - packages/market-data-client/tests/test_async_client.py
  - packages/market-data-client/tests/test_calendar_write.py
  - packages/market-data-client/tests/test_calendar_write_async.py
  - packages/market-data-client/tests/test_client.py
  - packages/market-data-client/tests/test_core.py
  - packages/market-data-client/tests/test_decode.py
  - packages/market-data-client/tests/test_mutation_gate_ast.py
  - packages/market-data-client/tests/test_public_surface_market_data.py
  - packages/market-data-client/tests/test_transport.py
  - packages/market-data-client/tests/test_v040_request_pin.py
  - packages/market-data-client/tests/test_with_options.py
  - packages/market-data-client/tests/test_with_options_async.py
  - packages/wallets-client/src/wallets_client/models.py
  - packages/wallets-client/src/wallets_client/types.py
  - tools/check_uniform_structure.py
  - verification/snapshots/higyrus-client-surface.txt
findings:
  critical: 2
  warning: 7
  info: 3
  total: 12
status: issues_found
---

# Phase 31: Code Review Report

**Reviewed:** 2026-08-25
**Depth:** deep
**Files Reviewed:** 38
**Status:** issues_found

## Summary

The phase does what it says on the surfaces I could mechanically verify: no cross-package
import was introduced (`lint-imports` clean; a manual grep of every `packages/*/src/<pkg>/*.py`
for a sibling-package import returns nothing), the two published holiday builders still carry
`idempotent is True`, the emitted requests are pinned raw-bytes on both surfaces, and
`_ensure_mutation_allowed()` is still the first executable statement of all 16 gated call sites.
`ruff check`, `ruff format --check`, `lint-imports` and 988 tests are green. The nullability
verdict also holds up against the committed captures: I diffed each of the four capture schemas
leaf-for-leaf against the declarations and the only two `NoneType` leaves
(`ingestor.last_error`, `ingestor.pipeline.last_write_error`) are exactly the two `| None`
fields declared — no Optional is hiding an observed divergence.

Two findings are load-bearing against the phase's own stated goals rather than against style:

1. `main_higyrus.py` never calls the typed `get_health()` on either surface, so the higyrus
   half of TYP-02 has zero live-verification coverage — this is the one package where the
   phase's core value (an accurate live divergence census) is now structurally unreachable.
   The phase's own market-data plan established the correct both-things pattern in the same
   cycle and higyrus did not receive it.
2. The two holiday parsers claim, in bold, that no tolerance branch raises. Under
   `strict_decode=True` — the mode Phase 33 runs the drivers in — all four branches raise
   `MarketDataDecodeError`, on a mutation whose server-side effect has already been committed.
   The claim is asserted in docstrings, restated in a test-module comment, and pinned by a
   parametrized test that never enables the mode where it is false.

The rest are quality/observability defects: a divergence record that erases the observed type,
two models missing from `models.__all__`, a driver metric that became a constant, and a
verbatim-copied docstring that repeats a statement the same file already declares wrong.

## Critical Issues

### CR-01: The higyrus driver never exercises the typed `get_health()` — TYP-02's tracer slice has no live coverage

**File:** `main_higyrus.py:609-681` (sync), `main_higyrus.py:696-770` (async)

**Issue:** Plan 31-03 retyped `get_health()` → `Health` across the parser and four signature
sites, and the project's core value is that the driver exercises the public surface against the
live API so divergences are detected. But `probe_get_health_sync` / `probe_get_health_async`
only call `_raw_request_sync(client, "GET", "/api/health")` /
`_raw_request_async(...)`. A grep for any call of the public wrapper across the whole driver
returns nothing:

```
$ grep -n "client.get_health\|aio.get_health\|higyrus_client.get_health\|\.get_health(" main_higyrus.py
610:    """Probe 3: ``higyrus_client.get_health()`` (HIGY-02). WR-03 single call.   # docstring only
```

Before this phase the bypass was justified and the docstring said so: *"el wrapper... devuelve
el mismo dict pero sin diferencia observable"*. That premise is now false — the wrapper builds a
`Health` through `_decode.walk_model`, emits divergence records on the `higyrus_client` logger,
and raises `HigyrusDecodeError` under `strict_decode=True`. The docstring was rewritten to
explain why the SNAPSHOT must come from the raw wire, which is correct, but the wrapper call was
never added back. Consequence: Phase 33's strict live run will produce zero divergence evidence
for `Health` and for `parse_get_health_response`, and the 204/empty-body strict-raise delta that
31-03 deliberately measured and documented can never be observed against the real service.

The same phase solved this exact problem correctly for market-data — `probe_health_sync` calls
the typed wrapper AND re-fires the raw spec (`main_market_data.py:640-644`). higyrus got the
docstring but not the code.

**Fix:** mirror the market-data pattern — keep the raw capture for the snapshot, add the typed
call so the surface is actually exercised:

```python
    try:
        health = client.get_health()            # exercise the TYPED public surface
        raw = _raw_request_sync(client, "GET", "/api/health")   # raw wire for the snapshot
    except HigyrusAuthError as exc:
        ...
```

and thread `health.status` (or a count) into the PASS detail so the typed path is observably
reached. Mirror it in `probe_get_health_async`.

---

### CR-02: The holiday parsers' "none of them raises" invariant is false under `strict_decode`, on already-committed mutations

**File:** `packages/market-data-client/src/market_data_client/_core.py:1171-1178`,
`packages/market-data-client/src/market_data_client/_core.py:1204-1211`

**Issue:** Both parsers normalize every tolerance branch to `Model.from_api(None)`. `from_api`
routes `None` through `_decode.walk_model`, whose non-dict arm calls
`scope(model, path, "non_dict", ...)`. `non_dict` is not in `_INFO_KINDS`, so under
`STRICT_DECODE=True` the sink raises `MarketDataDecodeError` (`_decode.py:205-221`). Measured:

```
$ _decode.STRICT_DECODE.set(True)
add_holidays    empty -> RAISED MarketDataDecodeError ... observed NoneType
add_holidays    null  -> RAISED MarketDataDecodeError
add_holidays    list  -> RAISED MarketDataDecodeError
delete_holiday  empty/null/list -> RAISED MarketDataDecodeError
```

This contradicts, verbatim, the invariant the phase declared and repeated in four places:

- `_core.py:1153` — *"All four branches survive here... **None of them raises.**"*
- `_core.py:1191` — *"...and none of them raises. This is a MUTATION published in v0.4.0; a
  raise here would be a behaviour change, not a typing change."*
- `client.py`/`aio.py` `add_holidays` docstrings — *"tolerancia D-07 / T-26-13, preservada"*
- `tests/test_core.py:660-666` — the G-4 block comment asserting the same thing.

The replaced `parse_calendar_write_response` did NO decoding at all, so `strict_decode` could
never affect it. The delta is therefore real and new, and it lands on the worst possible shape:
`add_holidays` / `delete_holiday` are mutations, so the raise happens AFTER the server has
already committed the write — the caller loses the acknowledgement and cannot tell whether the
holiday was upserted. `ROADMAP.md:193` schedules Phase 33 to run `main_market_data.py` in strict
mode against develop, so this is imminent, not hypothetical.

The test suite pins the false version: `test_calendar_write_parsers_preserve_the_t2613_tolerance`
(`tests/test_core.py:700-722`) parametrizes all four branches but never sets `STRICT_DECODE`.
Note the asymmetry — the higyrus sibling plan hit the identical situation and handled it
correctly, with an explicit measured test
(`packages/higyrus-client/tests/test_core.py:...test_parse_get_health_response_empty_body_raises_under_strict_decode`)
plus a docstring paragraph naming the delta. market-data got neither.

**Fix:** pick one and make code, docs and tests agree. The lower-risk option preserves the
declared invariant by keeping the mutation acknowledgement out of strict mode's reach:

```python
    resp.read()
    raise_for_response(resp)
    raw = resp.json() if resp.content else None
    if not isinstance(raw, dict):
        # T-26-13: a published mutation must not turn an anomalous ACK into an
        # exception AFTER the write committed — silence the sink for this branch.
        token = _decode.STRICT_DECODE.set(False)
        try:
            return AddHolidaysResult.from_api(raw)
        finally:
            _decode.STRICT_DECODE.reset(token)
    return AddHolidaysResult.from_api(raw)
```

If instead the strict raise is intended, delete the four "none of them raises" claims, document
the exception-after-commit consequence in both shell docstrings, and add the strict-mode
parametrization to `test_calendar_write_parsers_preserve_the_t2613_tolerance` so the real
contract is pinned.

## Warnings

### WR-01: The holiday parsers erase the observed type from the divergence record

**File:** `packages/market-data-client/src/market_data_client/_core.py:1176-1178`,
`packages/market-data-client/src/market_data_client/_core.py:1209-1211`

**Issue:** `if not isinstance(raw, dict): return AddHolidaysResult.from_api(None)` throws `raw`
away before handing it to the walker. `walk_model` reports
`scope(model, path, "non_dict", model, type(payload).__name__)`, so a JSON **list** body is
recorded as `observed_type="NoneType"`, a JSON **string** body as `NoneType`, and a JSON
**number** body as `NoneType`. Verified: a `b"[]"` body emits
`declared=AddHolidaysResult / observed=NoneType`. The census loses the one fact it exists to
capture — what the vendor actually sent — and Phase 33 will freeze that wrong `(model,
field_path, kind)` identity into its findings. `parse_health_response` two hundred lines above
gets this right (`f"expected dict, got {type(raw).__name__}"`).

**Fix:** pass the real payload through; `walk_model` already handles any non-dict:

```python
    raw = resp.json()
    if not isinstance(raw, dict):
        return AddHolidaysResult.from_api(raw)   # observed_type == "list" / "str" / "int"
    return AddHolidaysResult.from_api(raw)
```

which collapses to a single `return AddHolidaysResult.from_api(raw)`. Same for the delete half.
Add a test asserting `records[0].observed_type == "list"` for a `b"[]"` body.

---

### WR-02: `AddHolidaysResult` and `DeleteHolidayResult` are missing from `models.__all__`

**File:** `packages/market-data-client/src/market_data_client/models.py:90-111`

**Issue:** The six health models were added to `models.__all__`; the two mutation-result models
were not. Verified:

```
$ python -c "from market_data_client import models; print({'AddHolidaysResult','DeleteHolidayResult'} - set(models.__all__))"
{'AddHolidaysResult', 'DeleteHolidayResult'}
```

CONVENTIONS mandates *"Explicit `__all__` list with all public names"*. `from
market_data_client.models import *` silently omits the two classes that this plan's own tests
and `_core.py` import by name. `test_public_surface_market_data.py` only inspects the package
`__all__`, so nothing catches it.

**Fix:** insert both names in ASCII sort order (RUF022 requires it):

```python
__all__ = [
    "AddHolidaysResult",
    "CalendarConfig",
    "CalendarDay",
    "DeleteHolidayResult",
    "FeedIngestor",
    ...
]
```

and extend `test_public_surface_market_data.py` to assert `models.__all__` covers every
`SafeModel` subclass declared in the module.

---

### WR-03: `public_keys=` in the holiday driver probes is now a compile-time constant

**File:** `main_market_data.py:2425`, `main_market_data.py:2653`

**Issue:** `f"...public_keys={len(created.to_dict())}..."`. Before this phase `created` was the
raw wire dict, so `len(created)` was a genuine observation of how many keys the server sent.
`AddHolidaysResult` declares exactly three fields, and `dataclasses.asdict` reproduces the
declaration, so `len(created.to_dict())` is **always 3** — it can no longer differ no matter
what the wire does. The probe's own docstring calls `to_dict()` *"la proyección de wire"*, which
is precisely the CR-01 misconception the same phase documents at
`models.py:70-78` and in the FA-09 carry-forward warning 90 lines below. A Phase 33 operator
reading `public_keys=3` will read it as evidence about the wire.

**Fix:** the probe already re-fires the raw request for the snapshot — count that instead, and
say which side it came from:

```python
        raw_add = _raw_via_request_sync(client, _core.build_add_holidays_request(...))
        ...
        f"{_HOLIDAY_SYNC}; wire_keys={len(raw_add) if isinstance(raw_add, dict) else -1} "
        f"saved={created.saved} refire_status={refire.status_code}",
```

Mirror at line 2653. If the count must stay declaration-derived, rename it to
`model_fields=` so it stops claiming to be a wire observation.

---

### WR-04: `SafeModel.to_dict()`'s docstring repeats a claim the same file declares wrong

**File:** `packages/market-data-client/src/market_data_client/models.py:202-216`,
`packages/higyrus-client/src/higyrus_client/models.py:67-81`

**Issue:** Both copies say *"and the adapter the verification harness feeds to
`verification.schema.schema_of`"*. The market-data module docstring 130 lines above
(`models.py:70-78`) states that this wording *"is now known to be WRONG for a snapshot site"*
and that *"every driver schema-snapshot site must keep feeding RAW WIRE"*; the higyrus module
docstring carries the same correction. Nobody reading `to_dict()` at its definition sees the
correction, and the phase already produced two real instances of the mistake it warns about
(the FA-09 drift-blind delete snapshot, and WR-03 above). Copying a known-false sentence
verbatim into two more packages guarantees a third instance.

**Fix:** replace the second clause in both copies:

```python
        """Re-project the model as the plain wire dict (D-08).

        Escape hatch for the dict -> model break of Phase 30: use it for
        ``len()`` / ``isinstance`` call sites ONLY. It is **NOT** a valid input
        to ``verification.schema.schema_of`` — the walker has already coerced
        every non-optional field to its declared type and dropped every
        undeclared key, so a type change, an added key and a removed key are all
        three invisible (Phase 30 CR-01). Schema-snapshot sites must feed RAW WIRE.
        """
```

---

### WR-05: `market_data_client._core` has no import-boundary contract despite its docstring claiming one

**File:** `pyproject.toml:140-146` (config), asserted at
`packages/market-data-client/src/market_data_client/_core.py:12-15`

**Issue:** `_core.py`'s module docstring states *"NO imports desde `market_data_client.client`
ni `market_data_client.aio` — `_core` permanece IO-free y desacoplado de los shells (import
boundary)"*. `[tool.importlinter].root_packages` lists only `ambito_financiero_client`,
`iol_client`, `higyrus_client`, `matriz_client`; there are four `_core` contracts and none is
for market-data. `lint-imports` reports *"Contracts: 4 kept"* — so the boundary market-data's
docstring calls enforced is unenforced. This phase added ~155 lines to that exact file
(two new parsers, two rewritten ones), which is when a boundary is most likely to slip.

**Fix:**

```toml
[tool.importlinter]
root_packages = [
    "ambito_financiero_client",
    "iol_client",
    "higyrus_client",
    "matriz_client",
    "market_data_client",
]

[[tool.importlinter.contracts]]
name = "market_data_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["market_data_client._core"]
forbidden_modules = ["market_data_client.client", "market_data_client.aio"]
```

---

### WR-06: CI never type-checks the market-data test suite this phase grew by ~900 lines

**File:** `.github/workflows/ci.yml:92-99`

**Issue:** The *"mypy (tests por paquete)"* loop enumerates five packages and omits
`market-data-client`. The pre-existing omission became materially worse here: plan 31-04/31-05
added ~900 lines to `packages/market-data-client/tests/`, including 20+ `# type: ignore[...]`
comments on `LogRecord` attribute reads and several `cast(Any, ...)` calls. None of those is
validated — an ignore that stops being needed, or a `cast` that hides a genuine signature
mismatch, passes silently. The reviewed files include `ci.yml`, and this phase edited it.

**Fix:** add the package to the loop:

```yaml
          for pkg in higyrus-client wallets-client matriz-client iol-client ambito-financiero-client market-data-client; do
```

If it fails today, fix the errors rather than leaving the leg out — that is the whole point of
the per-package loop existing.

---

### WR-07: Breaking return-type change ships under the already-released version 0.4.0, with no changelog entry

**File:** `packages/market-data-client/pyproject.toml:3`, `packages/market-data-client/README.md:123-164`,
`packages/higyrus-client/pyproject.toml:3`

**Issue:** Five published endpoints changed their return type from `dict[str, Any]` to a frozen
dataclass (`get_health`, `get_health_feed`, `add_holidays`, `delete_holiday` on market-data;
`get_health` on higyrus). `market-data-client` remains at `0.4.0` and `higyrus-client` at
`0.2.0`, and both are already tagged and released (`market-data-client-v0.4.0`,
`higyrus-client-v0.2.0`). The README `## Changelog` section is this repo's changelog of record —
`### v0.2.0` there is explicitly headed *"Breaking changes (semver minor bump en línea 0.x)"* —
and it has no entry for this change. Anyone building from HEAD gets a wheel whose metadata says
`0.4.0` and whose API is incompatible with the released `0.4.0`.

**Fix:** either bump both packages in this cycle (`0.5.0` / `0.3.0`) with a `### v0.5.0`
changelog block listing the five retyped endpoints and the eight new exported models, or add an
`### Unreleased (v1.6)` section to both READMEs now so the break is recorded at the moment it is
introduced and the release chore has something to promote.

## Info

### IN-01: `test_health_is_frozen_and_slotted` never asserts slotted

**File:** `packages/higyrus-client/tests/test_core.py:616-620`

**Issue:** The name and docstring promise two properties — *"Frozen: attribute assignment
raises. Slotted: no `__dict__` escape hatch."* — but the body only exercises frozen. A future
edit dropping `slots=True` from `Health` passes this test with its name still claiming coverage.

**Fix:** add the missing assertion:

```python
    assert not hasattr(health, "__dict__")
```

---

### IN-02: `check_uniform_structure.py` carries two unused abstractions

**File:** `tools/check_uniform_structure.py:75-76`, `tools/check_uniform_structure.py:147`

**Issue:** `_fail(message)` is a one-line wrapper that only returns `CheckFailure(message)` and
is called from exactly one site; `checks = (check_uniform_structure,)` builds a single-element
tuple and iterates it, with `len(checks)` interpolated into the failure line. Both are scaffolds
for a plurality that does not exist, in a file whose docstring is 50 lines of rationale for
staying minimal and stdlib-only.

**Fix:** `raise CheckFailure(...)` directly and drop `_fail`; keep the tuple only if a second
check is genuinely queued, otherwise inline the single call.

---

### IN-03: The health probes' raw re-fire bypasses `raise_for_response`

**File:** `main_market_data.py:642-643`, `main_market_data.py:678-683` (via
`main_market_data.py:419-428`)

**Issue:** `_raw_via_request_sync` does `resp = client._request(spec); return resp.json()` with
no status check. The health endpoints are newly routed through it. If the re-fire returns a
5xx with an HTML body, the probe surfaces a `json.JSONDecodeError` through `_finding_for_exc`
instead of the typed `MarketDataAPIError` the first (public) call would have produced — the
finding's `class_` will be wrong. Pre-existing helper behaviour, newly applied to two more
endpoints.

**Fix:** have the helper call `_core.raise_for_response(resp)` before `resp.json()`, so raw
re-fires classify errors identically to the public path.

---

_Reviewed: 2026-08-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
