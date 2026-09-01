---
phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
reviewed: 2026-09-01T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - tools/check_surface_types.py
  - main_market_data.py
  - main_iol.py
  - main_higyrus.py
  - main_matriz.py
  - main_ambito_financiero.py
  - verification/test_drift_dedupe_falsification.py
  - verification/test_main_matriz_skip_line_shape.py
  - verification/test_matriz_sweep_snapshot.py
  - verification/test_main_matriz_login_fail_uniformity.py
  - .github/workflows/ci.yml
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 45: Code Review Report

**Reviewed:** 2026-09-01
**Depth:** standard
**Files Reviewed:** 10 source files + 1 decision doc read for cross-reference
**Status:** issues_found (info-only; no blockers or warnings)

## Summary

This phase adds an intra-process dedupe guard for schema/type-drift findings at 7 sites
across the 5 root-level `main_*.py` drivers, consolidates a 5-entry CI allowlist addition
in `.github/workflows/ci.yml`, and documents (rather than fixes) two pre-existing broken
`verification/` test files via a dated decision doc.

I verified the dedupe mechanism site-by-site against the actual diff (`git diff fe323d6~1
98393eb`, not just the file contents) rather than trusting the extensive inline commentary,
and traced each site's no-op contract independently of the shipped AST locks:

- **`main_market_data.py`** (`_write_schema_snapshot`, 1 site): dedupe key `(client_function,
  digest)` checked before `_next_fid()`; no-op is a bare `return` (matches the `-> None`
  contract).
- **`main_higyrus.py`** (`_write_or_check_schema`, 1 site) and **`main_matriz.py`**
  (`_write_or_check_schema`, 1 site): dedupe key checked before `_next_fid()`; no-op returns
  `("PASS", "<file> drift ya reportado en esta corrida")` — correctly a 2-tuple, and the
  detail deliberately does not start with `"escrito"` so the caller's
  `elif detail.startswith("escrito")` branch can't misclassify it as a freshly-written
  baseline. matriz's key correctly uses `file_path.name` (which embeds the venue token from
  `_schema_path`), not `func_name`, avoiding a real cross-venue collision that a naive
  `func_name`-only key would have produced.
- **`main_ambito_financiero.py`** (`probe_schema_snapshot`, 1 site): dedupe key checked
  before `_next_fid()`; no-op returns `ProbeResult("schema_snapshot", "PASS", ...)`, matching
  the function's `ProbeResult` return type.
- **`main_iol.py`** (3 sites: 2 inline loop branches in `probe_field_type_map`, 1 in
  `_write_or_check_schema`): the two loop sites use `continue` (skipping
  `finding_fids.append`, preserving the probe's own FINDING/PASS accounting) and the helper
  site uses the same tuple-return no-op as higyrus/matriz.

For every site, fid allocation (`_next_fid()`) is placed strictly after the `drift_key in
_seen_drift_keys` check, and each `_seen_drift_keys` set is a separate module-level object
per driver (no accidental cross-package sharing, consistent with `CLAUDE.md`'s "no shared
code between packages" constraint).

I also independently ran the numbers the phase's artifacts claim rather than accepting them
at face value:

- `uv run python tools/check_surface_types.py` → `187 __all__ names, 337 definitions
  scanned, 467 fields scanned` — matches the `587641f` docstring update exactly (no stale
  figures left in the "Measured 2026-09-01" block).
- `git show d6b34f0 -- .github/workflows/ci.yml` → confirms the allowlist edit is a single
  clean 5-line addition to the existing explicit list, no restructuring, no new job (`grep -c
  '^  [a-z-]*:$'` unchanged).
- `uv run pytest -q verification/test_matriz_sweep_snapshot.py
  verification/test_main_matriz_login_fail_uniformity.py` → `19 failed, 3 passed, 19 errors`,
  exactly matching `45-HARN-04-DECISION.md` M1.
- The 18 CI-enrolled `verification/` locks (including the 5 new ones and
  `test_drift_dedupe_falsification.py` itself) all pass (`181 passed`).
- `ruff check` and `mypy` are clean on all 6 reviewed Python source files.
- `git status --porcelain .planning/verification/` is empty after running the dedupe test
  suite, confirming the fixtures' isolation claim (no writes to the committed findings
  ledger).

No BLOCKER or WARNING findings survived this level of scrutiny — the dedupe contract is
correctly per-site rather than copy-pasted uniformly, and every load-bearing claim in the
decision doc and file docstrings checks out against a live run. The three findings below are
informational observations for a future reader, not defects that need to block this ship.

## Info

### IN-01: Two of `main_iol.py`'s three dedupe guards cannot currently collapse anything in a live run

**File:** `main_iol.py:1651-1657` and `main_iol.py:1729-1735`
**Issue:** The two inline dedupe guards inside `probe_field_type_map` key on
`f"get_quote:{key}"` / `f"get_historical_quotes[0]:{key}"` where `key` comes from iterating
`_ASSUMED_QUOTE_FIELDS.items()` (1 entry: `ultimoPrecio`) and
`_ASSUMED_HISTORICAL_FIELDS.items()` (2 entries, but `probe_field_type_map` is invoked
exactly once in `main()`: `main_iol.py:2331`). Since each key is visited exactly once per
process, the `if drift_key in _seen_drift_keys` branch can never be entered in a real
`main()` run today — it only fires if the surrounding function is invoked more than once
within the same process (as the falsification test's arm 4/5 does directly, not via a
duplicate live invocation). This is not incorrect — the guard is harmless and structurally
consistent with the other 5 sites — but it is presently defensive/unreachable code in
production rather than exercising a real duplicate-suppression scenario, unlike the
market-data/higyrus/matriz/ambito sites which do collapse a measured real duplication (sync
vs async comparing the same baseline).
**Fix:** No action required. If `_ASSUMED_QUOTE_FIELDS`/`_ASSUMED_HISTORICAL_FIELDS` grow to
contain a repeated logical divergence path (e.g., the same field checked from two call
sites), this guard becomes load-bearing; until then, a one-line comment noting "currently
unreachable in `main()`, guards against future multi-invocation" would save a future reader
from re-deriving this via git-archaeology.

### IN-02: `_seen_drift_keys` / `_drift_digest` are byte-for-byte duplicated across 5 files

**File:** `main_market_data.py:369`, `main_iol.py:267`, `main_higyrus.py:329`,
`main_matriz.py:406`, `main_ambito_financiero.py:145` (plus their `_drift_digest` twins)
**Issue:** The dedupe primitive (a `set[tuple[str, str]]` plus a SHA-256 digest helper) is
copy-pasted verbatim into all 5 drivers. This is explicitly called out and justified in every
copy's own comment ("Copia local deliberada... CLAUDE.md prohíbe código compartido entre
unidades"), and it does match this repo's documented architecture (no shared library between
packages, `packages/*/client.py` duplication is the established pattern). Flagging only so it
is visible in a code-quality pass; it is not something this review is asking to be changed
given the project's explicit constraint.
**Fix:** No action required — this is the correct amount of duplication under this repo's
stated no-shared-code convention.

### IN-03: `test_main_matriz_skip_line_shape.py`'s "exactly 3 call sites" floor/ceiling doesn't count the shared decode-error return path

**File:** `verification/test_main_matriz_skip_line_shape.py:296-349` vs.
`main_matriz.py:809-814` (the `on_decode_error=_shape_probe_result` wiring on
`probe_login_sync`)
**Issue:** `_probe_result_calls` only matches `ProbeResult(<literal>, ...)` calls where the
first argument is an `ast.Constant`. `probe_login_sync` is also decorated with
`decode_error=MatrizDecodeError, on_decode_error=_shape_probe_result`; on a decode error,
`probe_context` calls `_shape_probe_result("probe_login_sync", "sync", exc)`, which builds
`ProbeResult(name, "FINDING", detail)` where `name` is a **variable** (`probe_name.
removeprefix("probe_")`), not a literal. This 4th logical return path for `login_sync` is
invisible to the AST scan and is not counted toward `_LOGIN_PROBE_CALL_SITES = 3`. It happens
to be harmless today because it also returns `"FINDING"`, so it can't violate
`_LOGIN_PROBE_STATUSES = {FINDING, PASS}` — but the test's stated intent ("techo de triage":
a new return status "no debería" go un-noticed) is not actually watertight against a decode-
error path returning a third status value, since that path is structurally invisible to this
particular AST walk.
**Fix:** No action required for this phase (the decode-error path is a pre-existing,
independently-locked mechanism — `verification/test_probe_context_coverage.py` covers
`probe_context`'s decode-error wiring generically). Worth a one-line docstring note in
`test_main_matriz_skip_line_shape.py` acknowledging that the 3-site census is scoped to
direct literal returns inside `probe_login_sync` and does not claim to enumerate every status
`login_sync` can produce via the decorator's decode-error branch.

---

_Reviewed: 2026-09-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
