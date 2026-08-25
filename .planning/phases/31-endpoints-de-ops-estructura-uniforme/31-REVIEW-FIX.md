---
phase: 31-endpoints-de-ops-estructura-uniforme
fixed_at: 2026-08-25T10:05:00Z
review_path: .planning/phases/31-endpoints-de-ops-estructura-uniforme/31-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 31: Code Review Fix Report

**Fixed at:** 2026-08-25
**Source review:** `.planning/phases/31-endpoints-de-ops-estructura-uniforme/31-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (2 Critical + 7 Warning; the 3 Info findings were out of scope for this pass)
- Fixed: 9
- Skipped: 0

All fixes were applied in an isolated git worktree, committed one per finding, and
fast-forwarded onto `milestone/v1.5-mutations`. The Info findings IN-01, IN-02 and
IN-03 were **not** touched — `fix_scope` was `critical_warning`.

## Fixed Issues

### CR-01: The higyrus driver never exercises the typed `get_health()`

**Files modified:** `main_higyrus.py`
**Commit:** `275ad1a`
**Applied fix:** Added `client.get_health()` / `await aclient.get_health()` to
`probe_get_health_sync` / `probe_get_health_async`, **alongside** the existing
`_raw_request_*` capture — the raw capture is kept because the driver's
schema-snapshot site must keep feeding raw wire (G-3 / Phase 30 CR-01), which the
rewritten docstrings now state as a two-numbered-things contract rather than as a
justification for the bypass.

Two things the review's snippet did not cover, both required for the fix to be
safe under the strict-mode run it exists to enable:

- `HigyrusDecodeError` is **not** a subclass of `HigyrusAPIError` nor a member of
  `_RESIDUAL_PROBE_EXCEPTIONS`, so under `strict_decode=True` it would have escaped
  the probe boundary and crashed the driver instead of producing evidence. Added a
  dedicated `except HigyrusDecodeError` branch on both surfaces emitting a `SHAPE`
  finding carrying `model` / `field_path` / `declared` / `observed` (all type names
  and paths, never wire values).
- The PASS detail threads `typed={type(health).__name__}` rather than
  `health.status`: the probe's own D-HIGY-2 rule is that the detail emits counts,
  never wire content, and the market-data probe's `status={health.status}` pattern
  would have violated it. The type name still proves the typed path was reached,
  because the probe cannot get there if the typed call raised.

### CR-02: The holiday parsers' "none of them raises" invariant was false under `strict_decode`

**Files modified:** `packages/market-data-client/src/market_data_client/_core.py`,
`packages/market-data-client/src/market_data_client/client.py`,
`packages/market-data-client/src/market_data_client/aio.py`,
`packages/market-data-client/tests/test_core.py`
**Commit:** `c749864`
**Applied fix:** Took **option A** (the review's lower-risk option) — silence the
strict *disposition* for the terminal non-dict branch only, preserving the declared
T-26-13 invariant on a mutation already published in v0.4.0.

Evidence gathered before choosing, rather than assumed:

- `_decode.DecodeScope.__call__` emits the divergence record via `_emit()` **before**
  the strict raise, so suppressing the raise does **not** suppress the record. The
  divergence remains fully observable on the `market_data_client` logger.
- `ROADMAP.md` Phase 33 success criterion 1 requires every divergence to enter the
  findings pipeline **via a logging handler** (`verification/divergences.py`). It does
  not require a raise. Option A therefore costs the Phase 33 census nothing — which
  is what made it safe against the project's core value of not hiding divergences.

Scope of the suppression is deliberately narrow and is now pinned: a well-shaped
`dict` acknowledgement whose **fields** diverge still raises under strict mode, like
every other parser in the file.

Code, `_core` docstrings, the `client.py` / `aio.py` `add_holidays` + `delete_holiday`
docstrings and the `test_core.py` G-4 block comment were all rewritten together so
none of them restates a claim the others contradict. Two new tests:
`test_calendar_write_parsers_do_not_raise_under_strict_decode` (the tolerance, in the
mode where it used to be false) and
`test_calendar_write_parsers_still_raise_under_strict_when_a_field_diverges` (its scope).

### WR-01: The holiday parsers erase the observed type from the divergence record

**Files modified:** `packages/market-data-client/src/market_data_client/_core.py`,
`packages/market-data-client/tests/test_core.py`
**Commit:** `3611e77`
**Applied fix:** Both parsers now hand the payload to `from_api` verbatim
(`raw = resp.json() if resp.content else None`) instead of substituting a literal
`None`, so `walk_model`'s `non_dict` record carries `observed_type` of `list` / `str`
/ `int`, and `NoneType` only for a genuinely absent or `null` body. The returned
*value* is unchanged — any non-dict yields the same zero-valued instance — so the
existing `out == model_cls.from_api(None)` tolerance assertions still hold.

Committed **before** CR-02 so the two remain independently reviewable, even though
they compose on the same lines: WR-01 restructures the branch, CR-02 then wraps it.
New parametrized test `test_calendar_write_parsers_record_the_type_actually_observed`
covers five body shapes × both parsers.

### WR-02: `AddHolidaysResult` / `DeleteHolidayResult` missing from `models.__all__`

**Files modified:** `packages/market-data-client/src/market_data_client/models.py`,
`packages/market-data-client/tests/test_public_surface_market_data.py`
**Commit:** `ad80657`
**Applied fix:** Both names inserted in ASCII sort order (RUF022 clean). Rather than
adding them to a second hand-maintained list, the new guard
`test_models_dunder_all_covers_every_safemodel_subclass` **derives** the expected set
from `vars(models)` — the failure mode being covered is precisely "somebody added a
model and forgot a list", so a list-based check would have been able to repeat it.

### WR-03: `public_keys=` in the holiday driver probes is a compile-time constant

**Files modified:** `main_market_data.py`
**Commit:** `28c910f`
**Applied fix:** Replaced `public_keys={len(created.to_dict())}` with
`wire_keys={len(raw) if isinstance(raw, dict) else -1} saved={created.saved}` in both
the sync and async holiday probes, sourced from the raw re-fire the probes already
perform for the snapshot. Both docstrings were corrected: the previous text described
`to_dict()` as "la proyección de wire", which is the same misconception the phase
documents at `models.py` and warns about in its FA-09 carry-forward.

### WR-04: `SafeModel.to_dict()`'s docstring repeats a claim the same file declares wrong

**Files modified:** `packages/market-data-client/src/market_data_client/models.py`,
`packages/higyrus-client/src/higyrus_client/models.py`
**Commit:** `7073937`
**Applied fix:** Replaced the "and the adapter the verification harness feeds to
`verification.schema.schema_of`" clause in both copies with the correction each
module's own docstring already carries 130 lines above, at the definition where a
reader actually meets it. Confirmed first that no byte-identity gate covers
`models.py` across packages (the five-copies rule applies to `_decode.py`).

### WR-05: `market_data_client._core` has no import-boundary contract

**Files modified:** `pyproject.toml`
**Commit:** `22393c9`
**Applied fix:** Added `market_data_client` to `[tool.importlinter].root_packages` and
the fifth `forbidden` contract. `lint-imports` now reports **5 kept, 0 broken** (was
"4 kept" while `_core.py`'s docstring claimed the boundary was enforced).

### WR-06: CI never type-checks the market-data test suite

**Files modified:** `.github/workflows/ci.yml`,
`packages/market-data-client/tests/test_core.py`,
`packages/market-data-client/tests/test_decode.py`,
`packages/market-data-client/tests/test_reference_core.py`
**Commit:** `60e4d97`
**Applied fix:** Added `market-data-client` to the "mypy (tests por paquete)" loop.
It failed with 4 errors, so — per the finding's own instruction — the errors were
fixed rather than the leg left out:

- two `Need type annotation for "body"` (`test_core`, `test_reference_core`)
- a `comparison-overlap` on the off-`Literal` runtime value, which is the assertion's
  own point; `cast(Any, ...)` makes that explicit and the added comment says so
- `hints_for(cls)` `arg-type` (`lru_cache` wants `Hashable`), mirrored to the
  `cast(Any, ...)` the same function's other call site already used

`mypy packages/market-data-client/tests` → 27 files, no issues.

### WR-07: Breaking return-type change ships under an already-released version, no changelog

**Files modified:** `packages/market-data-client/README.md`,
`packages/higyrus-client/README.md`
**Commit:** `bf04b2f`
**Applied fix:** Took the **record-it-now** option rather than bumping versions,
because ROADMAP Phase 34 explicitly owns the bump, the tag and the release gates, and
`iol-client`'s README already establishes the repo's shape for this: its `### v0.3.0`
changelog block documenting the dict→modelo break is written while its own
`pyproject.toml` still says `0.2.0`.

Added a "sin publicar todavía" section to each README listing the retyped endpoints
(4 on market-data, 1 on higyrus), the newly exported models (8 and 1), the truthiness
flip, and the `to_dict()` escape hatch with its non-`schema_of` caveat. Each section
states the operational warning explicitly: a wheel built from HEAD carries metadata
saying `0.4.0` / `0.2.0` while exposing an API incompatible with those releases.
`higyrus-client`'s README had **no** `## Changelog` section at all; one was created
(placed at the end, matching `iol-client`), and the missing `Health` was added to its
public-models list.

## Verification

Run against the fixed tree before the report was written:

| Gate | Result |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 231 files already formatted |
| `mypy` (global src) | 62 source files, no issues |
| `mypy packages/market-data-client/tests` | 27 source files, no issues |
| `lint-imports` | 5 kept, 0 broken |
| `pytest packages/higyrus-client packages/market-data-client` | 809 passed |
| `pytest` (all 6 packages) | 1682 passed, 1 deselected |
| `pytest tests/` | 2 passed |
| `pytest verification/` | 19 pre-existing failures, **0 new** |

The 19 `verification/` failures (17 in `test_matriz_sweep_snapshot.py`, 2 in
`test_main_matriz_login_fail_uniformity.py`) were confirmed pre-existing by running
the same suite against the pre-fix baseline commit `87dcef0` in a scratch worktree
and diffing the failure sets: the "new failures" set is **empty**. They concern the
matriz driver, which none of these 9 commits touches.

## Notes for the developer

Two things found while fixing that are **not** covered by any Phase 31 finding and
were deliberately left alone:

1. **The per-package mypy-tests CI leg is currently red for three other packages.**
   Adding `market-data-client` (WR-06) makes it green for market-data, but
   `higyrus-client` (2 errors), `matriz-client` (29 errors) and
   `ambito-financiero-client` (2 errors) already fail that same loop at
   `HEAD`. Verified by running the loop against the untouched main repo. They look
   like mypy version drift (`.pre-commit-config.yaml` pins mypy `v1.13.0`, the
   workspace resolves `1.20.2`). This means the `typecheck` job is red independently
   of this phase; it is worth a scoped follow-up.

2. **`packages/higyrus-client/README.md` usage examples reference
   `HigyrusClient` / `AsyncHigyrusClient`,** but the package exports `Client` /
   `AsyncClient`. Pre-existing, unrelated to any finding, not touched.

Also worth flagging for the phase gate: **CR-02 is a semantic change**, not a
syntactic one. Its correctness rests on the judgement that a published mutation's
acknowledgement should not become an exception after the write committed, and that
Phase 33 consumes divergences through the logging handler rather than through
raises. Both premises were checked against `_decode.py` and `ROADMAP.md` and are
documented above, but the decision itself deserves a human confirmation before the
phase proceeds to verification.

---

_Fixed: 2026-08-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
