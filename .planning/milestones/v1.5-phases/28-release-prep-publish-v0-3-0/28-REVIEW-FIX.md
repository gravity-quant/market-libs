---
phase: 28-release-prep-publish-v0-3-0
fixed_at: 2026-08-17T23:40:00Z
review_path: .planning/phases/28-release-prep-publish-v0-3-0/28-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 28: Code Review Fix Report

**Fixed at:** 2026-08-17T23:40:00Z
**Source review:** `.planning/phases/28-release-prep-publish-v0-3-0/28-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (3 critical + 5 warnings; `fix_scope: critical_warning`, so IN-01..IN-04 were not attempted)
- Fixed: 8
- Skipped: 0

Every claim the review made was re-verified against the shipped code before any prose was
rewritten — `confirm` coverage/semantics by reading `client.py:598-640` and `models.py:285-360`
plus `grep -rn confirm src/`, the public names by importing the built package and checking
`hasattr` / `__all__`, and the gate behaviour by exercising both refusal paths at runtime.
No `.github/workflows/` file, no tag and no publish action was touched; v0.4.0 is already
released and these fixes land on `milestone/v1.5-mutations` for future consumption.

## Fixed Issues

### CR-01: Release notes claim a `confirm` guardrail that does not cover 3 of 5 calendar-write endpoints

**Files modified:** `packages/market-data-client/README.md`, `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md`
**Commit:** `62eed7c`
**Applied fix:** Replaced the false "exposed explicitly with default `False`, so real market
configuration is never persisted implicitly" sentence in both files with the verified semantics:
`confirm` is a field of `MarketHoursIn` only (so it rides `set_calendar_config` /
`preview_calendar_config`), it is a server-demanded second opinion for warning-producing windows
rather than a persistence gate (a warning-free config writes with `confirm=False`), and
`delete_calendar_config` / `add_holidays` / `delete_holiday` take no `confirm` at all — for those
three the opt-in mutating-gate is the only guard.

**Verification beyond re-read:** `grep -rn "confirm" src/` returns zero matches in any `_core.py`
request builder; `MarketHoursIn` is the sole model carrying the field (`models.py:307`);
`client.py:607-612` states the second-opinion semantics verbatim.

### CR-02: README usage examples call `get_marketdata()`, which does not exist

**Files modified:** `packages/market-data-client/README.md`
**Commit:** `cc2187c`
**Applied fix:** Both the sync (line 22) and async (line 30) snippets now call `get_market_data()`.

**Verification beyond re-read:** runtime-checked against the built package —
`hasattr(market_data_client, "get_market_data")` and `hasattr(aio, "get_market_data")` are both
`True`; the old `get_marketdata` spelling is `False` on both surfaces.

### CR-03: Memory index still advertised v0.2.0 as latest

**Files modified:** `.claude/projects/-Users-admin-development-market-libs/memory/MEMORY.md`
**Commit:** `a13dead`
**Applied fix:** Re-pointed the `market-data-client releases` index line to v0.4.0, naming
MUT-MD-02 + LIVE-MUT-01 and marking v0.2.0/v0.3.0/v0.3.1 superseded. Kept the one-line index
format and the existing "git subdir @ tag or GitHub Release wheel, not PyPI" install pointer;
the detail stays in the linked file.

### WR-01: README "read surface intact" contradicted its own breaking `CalendarDay` block

**Files modified:** `packages/market-data-client/README.md`, `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md`
**Commit:** `2adde7d`
**Applied fix:** Qualified the v0.4.0 header ("la superficie de lectura v0.2.0 sigue intacta
**excepto `CalendarDay`**… ver abajo") and aligned both artifacts on a single label and severity —
README's block is now "Reemplazo de campos de `CalendarDay` (breaking en sentido estricto,
documentado y shippeado dentro de un minor)" and the memory bullet reads "`CalendarDay` field
replacement (strictly breaking, documented, shipped inside a minor)". Reflowed the memory
paragraph so the wrap stayed clean.

### WR-02: Memory's "no live market configuration was left mutated" omitted six permanent rows

**Files modified:** `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md`
**Commit:** `fcd26ce`
**Applied fix:** The Scope note now states the measured end state: zero *ACTIVE* residue, the
calendar fully restored (0 probe holidays), and six `GSDPROBE/*` symbol rows permanently
`active=false` because the live API has no `DELETE /symbols` (the only revert is
`PATCH active=false`). Records that the identifiers are stable rather than timestamped — capping
residue at exactly six rows — and that `grep GSDPROBE/` is the handle.

**Verification beyond re-read:** cross-checked against `27-04-SUMMARY.md:100-111` (no
`DELETE /symbols`, stable identifiers, six-row cap) and `27-06-SUMMARY.md` ("residuo probado CERO:
6 filas GSDPROBE/ todas active=false, 0 días en 2099").

### WR-03: README install instructions pointed at PyPI, where the package does not exist

**Files modified:** `packages/market-data-client/README.md`
**Commit:** `f77b1b8`
**Applied fix:** Replaced `uv add market-data-client` with the tag-pinned git install and kept
`uv sync` for in-workspace use, added the GitHub Release wheel as an alternative, and led with an
explicit callout that the package is **not** on PyPI — including the warning that a same-named
PyPI package would not be this one (the dependency-confusion vector the review flagged).

### WR-04: Nothing bound `__init__.__version__` to `pyproject.toml`

**Files modified:** `packages/market-data-client/tests/test_version_metadata.py` (new)
**Commit:** `f0be9de`
**Applied fix:** Added a test module (kept the literal rather than deriving, per the review's
second option, since `release.yml` validates the tag against the `pyproject.toml` literal). Three
tests: the `pyproject.toml` fixture is readable from the package dir, `__version__` equals
`[project].version` read via `tomllib`, and `__version__` equals the installed distribution
metadata (`importlib.metadata.version`) — the value a wheel-only consumer actually observes.
Written in the package's existing style (`from __future__ import annotations`, module docstring
explaining the hole being closed, ruff line-length 100, mypy strict).

### WR-05: README documented none of the mutation surface it released

**Files modified:** `packages/market-data-client/README.md`
**Commit:** `426d23c`
**Applied fix:** New "Mutaciones (opt-in)" section after Autenticación (Spanish, matching the
README's language). Enumerates both write surfaces (symbols from v0.3.0, calendar from v0.4.0)
with their request models, documents both gates — `mutating_allowed` refuse-by-default with
`MarketDataMutationNotAllowedError` and zero HTTP/zero Auth0, plus the exact-hostname
`expected_host` second leg (noting that `None` disables only that leg) — and closes with the
correct `confirm` semantics so it agrees with the CR-01 correction. Includes a worked
preview → inspect warnings → re-issue example.

**Verification beyond re-read:** every name was confirmed present on the flat namespace, in
`__all__` and on `aio`; both refusal paths were exercised at runtime (missing opt-in, and
`expected_host` mismatch) and produced `MarketDataMutationNotAllowedError`; all three README
python blocks were parsed with `ast.parse`, and the example's `MarketHoursIn` construction,
`dataclasses.replace(..., confirm=True)` and `with Client(...)` context-manager usage were
executed.

## Skipped Issues

None — all eight in-scope findings were applied.

Out of scope (`fix_scope: critical_warning`): IN-01 (four/five call-site undercount), IN-02
(v0.4.0 UTC release date vs PR merge date), IN-03 (phase directory named for v0.3.0),
IN-04 (`pyproject.toml` missing `[project.urls]`, deprecated `license` table form). IN-01 and
IN-02 are one-line prose corrections in the same two files touched here and would be cheap to
fold into a follow-up; IN-04 is a monorepo-wide cleanup across all six packages.

## Post-fix verification

Run against the whole package after the last commit:

- `uv run ruff check packages/market-data-client` — All checks passed
- `uv run ruff format --check packages/market-data-client` — 34 files already formatted
- `uv run --package market-data-client pytest -q packages/market-data-client` — **390 passed**
- `uv run mypy packages/market-data-client` — 2 errors, both **pre-existing** and in files not
  touched here (`tests/test_core.py:417`, `tests/test_reference_core.py:412`, both "Need type
  annotation"). Confirmed pre-existing by running mypy against base commit `3140131` in a
  scratch worktree: identical 2 errors. The new test file adds a 34th source file with zero
  new errors.

---

_Fixed: 2026-08-17T23:40:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
