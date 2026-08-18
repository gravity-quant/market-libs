---
phase: 28-release-prep-publish-v0-3-0
reviewed: 2026-08-12T00:46:15Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - .claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md
  - packages/market-data-client/README.md
  - packages/market-data-client/pyproject.toml
  - packages/market-data-client/src/market_data_client/__init__.py
  - uv.lock
findings:
  critical: 3
  warning: 5
  info: 4
  total: 12
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-08-12T00:46:15Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 28 shipped a release-prep/publish change set: version bumps to `0.4.0` (pyproject,
`__init__.__version__`, `uv.lock`), a new Spanish `### v0.4.0` README changelog section, and a
six-region refresh of the agent-facing release memory.

**What verifies clean (checked, not assumed):**

- Version strings agree everywhere: `pyproject.toml:3` = `0.4.0`, `__init__.py:134` = `0.4.0`,
  `uv.lock:488` = `0.4.0`, imported `market_data_client.__version__` = `0.4.0` (runtime-checked).
- `uv lock --check` resolves clean; `tomllib` parses `pyproject.toml` without error.
- Every provenance claim in the memory file is true: tag `market-data-client-v0.4.0` resolves to
  `5d0825d11e88c0…`, that commit is `Merge pull request #10`, `release.yml` run `31549711805`
  succeeded with `headSha=5d0825d`, and both release assets exist with exactly the names cited
  (`market_data_client-0.4.0-py3-none-any.whl`, `market_data_client-0.4.0.tar.gz`).
- Prior-release facts check out: v0.3.1 → `7b0e0b2` / PR #9 / 2026-08-01; v0.3.0 → `ea92dd8` /
  PR #8 / 2026-07-31.
- The `CalendarDay` field-replacement callout is present in both README and memory, and matches
  `models.py:528-532` (`day`, `closed`, `description`, `open_time`, `close_time`).
- The "eight new public names" claim is exact — all eight are in `__init__.__all__`; all five
  calendar functions have `aio` module shims (`aio.py:914-936`) and are correctly *not* in the
  flat namespace.
- No credentials or secrets appear in any reviewed file.

**Key concerns:** the release notes make three claims that the shipped code contradicts — the most
serious being a **safety guardrail claim about destructive calendar mutations that the
implementation does not provide**. The README also documents a public API (`get_marketdata`) that
does not exist in any version of this package, and the memory *index* that routes agents to this
release file still advertises v0.2.0 as latest, so the six-region refresh is reachable only by
readers who bypass the index.

## Critical Issues

### CR-01: Release notes claim a `confirm` guardrail that covers 3 of 5 calendar-write endpoints — and misstates its semantics on the other 2

**File:** `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md:25-27`
(twin text at `packages/market-data-client/README.md:76-77`)

**Issue:** Immediately after enumerating all five calendar-write functions and all five endpoints,
both files assert:

> "The `confirm` guardrail is exposed explicitly with default `False`, so real market configuration
> is never persisted implicitly."

Traced against the implementation, this is false on two axes:

1. **Coverage.** `confirm` is a field of `MarketHoursIn` only (`models.py:307`). `HolidayIn`
   (`models.py:351-355`) and `HolidaysIn` have no `confirm`; `build_delete_calendar_config_request`
   (`_core.py:729-746`) and `build_delete_holiday_request` (`_core.py:761+`) take no confirmation
   argument at all (`grep -n confirm _core.py` returns zero matches in any builder). So
   `add_holidays` (persisting upsert), `delete_holiday` (destructive) and `delete_calendar_config`
   ("reset to defaults" — destructive) have **no** `confirm` gate.
2. **Semantics.** Even where `confirm` exists, it is not a persistence gate. `client.py:607-612`
   states it outright: *"it is a required SECOND OPINION — not a force flag: the server demands it
   only when the requested window produces warnings."* A warning-free `MarketHoursIn` is persisted
   by `PUT /calendar/config` with `confirm=False`.

This is agent-facing memory whose whole purpose is to be acted on autonomously. An agent that
believes "nothing persists implicitly, `confirm` defaults to `False`" can call
`delete_calendar_config()` or `add_holidays(...)` on a real market calendar expecting a second gate
that does not exist. The only real gate on those three endpoints is the mutating-gate
(`mutating_allowed=True` + `expected_host`), which the same paragraph mentions separately.

**Fix:** Scope the sentence to the endpoints and semantics that actually hold — memory version:

```markdown
  The `confirm` guardrail is a field of `MarketHoursIn` (default `False`), so it rides
  `set_calendar_config` / `preview_calendar_config` only. It is a *second opinion*, not a
  persistence gate: the server demands it only when the requested window produces warnings — a
  warning-free config is written with `confirm=False`. `delete_calendar_config`, `add_holidays`
  and `delete_holiday` have NO `confirm` argument; for those three the opt-in mutating-gate
  (`mutating_allowed=True` + `expected_host`) is the only guard.
```

Mirror the same correction in the Spanish README bullet (`README.md:76-77`).

### CR-02: README usage examples call `get_marketdata()`, which does not exist in the package

**File:** `packages/market-data-client/README.md:22` and `packages/market-data-client/README.md:30`

**Issue:** Both the sync and the async "Uso" snippets — the only executable examples in the README —
call a symbol that has never existed:

```python
snapshots = market_data_client.get_marketdata()   # line 22
snapshots = await aio.get_marketdata()            # line 30
```

Runtime-verified against the shipped 0.4.0 tree:
`hasattr(market_data_client, "get_marketdata")` → `False`;
`hasattr(aio, "get_marketdata")` → `False`;
`grep -rn "get_marketdata" src/` → zero matches. The real name is `get_market_data`
(`client.py:797`, `aio.py:807`), which is also what `__init__.__all__` exports. Both snippets raise
`AttributeError` verbatim. Additionally `get_market_data` is filtered — copying line 22 as the
first call a new consumer makes is a guaranteed failure.

This is pre-existing (the diff only appended the changelog), but `readme = "README.md"` in
`pyproject.toml:5` means this file is the long_description embedded in the
`market_data_client-0.4.0` wheel and sdist that this phase published — the phase shipped it.

**Fix:**

```python
# Sync
import market_data_client

snapshots = market_data_client.get_market_data()

# Async
from market_data_client import aio

snapshots = await aio.get_market_data()
```

Then run the snippets (or add a doc-example smoke test) before the next release rather than
re-shipping them unexecuted.

### CR-03: Memory index still advertises v0.2.0 as the latest release — two releases stale

**File:** `.claude/projects/-Users-admin-development-market-libs/memory/MEMORY.md:2`

**Issue:** The memory directory refreshed by this phase has an index file that was not touched:

> `- [market-data-client releases](market-data-client-releases.md) — latest published is v0.2.0
>   (LIVE-MD-01 fixes; v0.1.0 superseded/buggy); install via git subdir @ tag or GitHub Release
>   wheel, not PyPI`

`MEMORY.md` is the routing surface an agent reads first; it now directly contradicts the file it
links to (which correctly says v0.4.0). An agent that stops at the index — the normal cheap path —
recommends v0.2.0, i.e. a build that predates both the mutating-gate/symbols-write surface and the
`get_latest_batch` envelope fix. That fix is not cosmetic: v0.2.0's `get_latest_batch` silently
returns N *empty* `MarketDataSnapshot`s, so the stale index actively routes consumers into a known
data-correctness bug. The phase brief's own acceptance bar ("no stale v0.3.x claims presented as
latest") is violated one directory level up, and the stale claim is worse than v0.3.x.

**Fix:**

```markdown
- [market-data-client releases](market-data-client-releases.md) — latest published is v0.4.0
  (calendar write MUT-MD-02 + live-verified mutation fixes LIVE-MUT-01; v0.1.0 superseded/buggy,
  v0.2.0/v0.3.0/v0.3.1 superseded); install via git subdir @ tag or GitHub Release wheel, not PyPI
```

Better: make the index line derive from the target file's frontmatter `description`, or add a
release-checklist step that greps `MEMORY.md` for the package name whenever a release memory is
refreshed — this file went stale for two consecutive releases, so the manual step is not holding.

## Warnings

### WR-01: README v0.4.0 section contradicts itself — "read surface intact" vs. a breaking read-model removal

**File:** `packages/market-data-client/README.md:65` vs `packages/market-data-client/README.md:86-90`

**Issue:** The section header asserts *"(features nuevas, minor bump — la superficie de lectura
v0.2.0 sigue intacta)"*, and 20 lines later the same section is titled **"Breaking changes"** and
states that `CalendarDay` removed `date`, `marketId` and `isBusinessDay` with no compatibility
aliases. `CalendarDay` is the return element of `get_calendar()` — it *is* read surface. A reader
who trusts the header stops before the breaking block. The memory file compounds the divergence by
never using the word "breaking" for the same change (`memory:35-41` calls it a "field
replacement... documented"), while the README calls it a breaking change — so the two artifacts
disagree on severity of the same change.

**Fix:** Qualify the header and align the two files, e.g.
`"(features nuevas, minor bump — la superficie de lectura v0.2.0 sigue intacta EXCEPTO CalendarDay,
ver abajo)"`, and use one consistent label ("reemplazo de campos / field replacement") in both
README and memory.

### WR-02: Memory's "no live market configuration was left mutated" omits six permanent rows in develop

**File:** `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md:65-70`

**Issue:** The Scope note says the live LIVE-MUT-01 exercise used *"dedicated test identifiers and a
create → verify → revert cleanup, so no live market configuration was left mutated."* Phase 27's own
summary is explicit that this is not the whole picture
(`.planning/phases/27-verificaci-n-en-vivo-segura-fixes/27-04-SUMMARY.md:100-105`):

> "There is **no `DELETE /symbols`** in the live spec … the only revert is `PATCH active=false` and
> every identifier leaves one permanently inactive row in develop's catalogue, forever."

The measured end state (`27-06-SUMMARY.md:27`) is "6 filas GSDPROBE/ todas active=false, 0 días en
2099" — zero *active* residue, not zero residue. The memory's compression loses two facts a future
agent needs: that develop's symbol catalogue permanently carries six `GSDPROBE/*` rows, and that the
prefix is the greppable handle for them.

**Fix:** Replace the tail of the sentence with the measured state:

```markdown
…using dedicated test identifiers and a create → verify → revert cleanup. Measured end state: zero
ACTIVE residue — the calendar was fully restored (0 probe holidays), and the six `GSDPROBE/*`
symbol rows remain permanently `active=false` because the API has no `DELETE /symbols`
(grep `GSDPROBE/` to find them).
```

### WR-03: README install instructions point at PyPI, where this package does not exist

**File:** `packages/market-data-client/README.md:9-13`

**Issue:** The Instalación block is `uv add market-data-client`. The memory file states, twice
(frontmatter and body), that the package is **not published to PyPI** — the pipeline only creates
GitHub Releases. Verified: `https://pypi.org/pypi/market-data-client/json` → **404**. So the README's
primary install command fails today, and it directly contradicts the memory's install section
(`memory:80-82`), which this phase just rewrote to carry the v0.4.0 tag and wheel URL. The unclaimed
public name is also a standing dependency-confusion vector: whoever registers `market-data-client` on
PyPI first inherits every reader who follows this README.

Note: the same `uv add <name>` line exists in all six package READMEs, so this is a repo-wide
convention issue rather than a Phase-28 regression — but Phase 28 is the release that publishes
this README inside the wheel.

**Fix:**

```bash
# git, pinned to tag (recommended)
uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.4.0#subdirectory=packages/market-data-client"

# o, dentro del workspace:
uv sync
```

Add an explicit "no está en PyPI" line so a reader does not substitute a same-named PyPI package.

### WR-04: Nothing binds `__init__.__version__` to `pyproject.toml`; the release gate checks only the latter

**File:** `packages/market-data-client/src/market_data_client/__init__.py:134` and
`packages/market-data-client/pyproject.toml:3`

**Issue:** The version lives in two hand-edited places, and the publish gate validates only one:
`.github/workflows/release.yml:46-47` compares the git tag against the `pyproject.toml` version and
never reads `__version__`. No test asserts the two agree (`grep -rn "__version__" packages/*/tests`
→ zero matches). They happen to agree at `0.4.0` this time, but a future release that edits only
`pyproject.toml` will pass CI, pass the tag check, and ship a wheel where
`importlib.metadata.version("market-data-client")` and `market_data_client.__version__` disagree —
a lie in exactly the field consumers use for bug reports. This phase's process was a manual dual
edit, which is the failure mode.

**Fix:** Either derive it, so drift is structurally impossible:

```python
from importlib.metadata import version as _pkg_version

__version__ = _pkg_version("market-data-client")
```

or, if the literal is preferred, pin it with a test:

```python
def test_version_matches_pyproject() -> None:
    import tomllib, pathlib, market_data_client
    pyproject = tomllib.loads(
        (pathlib.Path(__file__).parents[1] / "pyproject.toml").read_text()
    )
    assert market_data_client.__version__ == pyproject["project"]["version"]
```

### WR-05: README documents none of the mutation surface it just released — including how to enable it

**File:** `packages/market-data-client/README.md:33-45` (Autenticación / env vars) and `:15-31` (Uso)

**Issue:** v0.3.0 and v0.4.0 are entirely about the write surface, yet the README body still
describes a read-only client. The env-var list stops at `MARKET_DATA_BASE_URL`; there is no mention
anywhere outside the changelog of `mutating_allowed=True`, of `expected_host`, or of the fact that a
default `Client()` refuses every mutation with `MarketDataMutationNotAllowedError` and zero HTTP
traffic. A consumer who installs v0.4.0 for calendar write reads the README, sees no write API, and
either concludes the feature is absent or hits the typed refusal with no documented remedy — the
remedy exists only in the agent-facing memory file, which consumers do not have.

**Fix:** Add a short "Mutaciones (opt-in)" section after Autenticación covering the two gates, the
typed error, and one worked example, e.g.:

```python
from market_data_client import Client, MarketHoursIn

with Client(mutating_allowed=True, expected_host="market-data-develop.bbsa.com.ar") as c:
    preview = c.preview_calendar_config(MarketHoursIn(open_time="11:00", close_time="17:00", timezone="America/Argentina/Buenos_Aires"))
    # inspeccionar preview.warnings, luego re-emitir con confirm=True si corresponde
```

## Info

### IN-01: "cuatro routes" / "all four routes" undercounts the five call sites it then enumerates

**File:** `packages/market-data-client/README.md:79` and
`.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md:29`

**Issue:** Both say `update_symbol(symbol_id)` was widened "across all four routes (the `_core`
request builder, `Client`, `AsyncClient` and both module shims)". "Both module shims" is two, so the
enumeration lists five sites — and `grep -rn "symbol_id:"` finds exactly five (`_core.py:437`,
`client.py:567`, `client.py:889`, `aio.py:578`, `aio.py:899`). The count is wrong; a future auditor
using it as a checklist will stop one site short.

**Fix:** "across all five call sites" (or drop the number and keep the enumeration).

### IN-02: The v0.4.0 date is the UTC release timestamp, 11 days after the PR #10 merge it is attached to

**File:** `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md:13-14`

**Issue:** "**Latest published: `market-data-client-v0.4.0`** (2026-08-12, tag on merge commit
`5d0825d`, PR #10, …)". PR #10 merged `2026-08-01T22:14:22Z`; the GitHub Release was created
`2026-08-12T00:18:19Z`. The date is defensible (the file dates prior releases by release timestamp
too) but it is glued to a merge-commit/PR clause dated eleven days earlier, and in the repo's local
timezone (UTC-3) the release happened on 2026-08-11 — so this file will disagree by one day with
every local-time artifact of the same event.

**Fix:** Disambiguate: "(released 2026-08-12 UTC; PR #10 merged 2026-08-01, tag on merge commit
`5d0825d`)".

### IN-03: Phase directory is named for v0.3.0 while the phase published v0.4.0

**File:** `.planning/phases/28-release-prep-publish-v0-3-0/` (directory name)

**Issue:** The phase that tagged and published `market-data-client-v0.4.0` lives in a directory
named `28-release-prep-publish-v0-3-0`. Every artifact inside (including this review) is therefore
filed under a version it did not ship. Grep-by-version over `.planning/phases/` will miss it.

**Fix:** Out of code scope and renaming may break existing references — at minimum add a one-line
note at the top of `28-PLAN.md`/tracking that the directory name predates the re-point to v0.4.0
(commit `679d07f` re-pointed the roadmap but not the directory).

### IN-04: `pyproject.toml` ships no `[project.urls]` and uses the deprecated table form of `license`

**File:** `packages/market-data-client/pyproject.toml:8` and the file as a whole

**Issue:** `license = { text = "MIT" }` is the pre-PEP-639 table form (the SPDX string
`license = "MIT"` is the current spelling, with `license-files` for the file itself). More
practically, there is no `[project.urls]` block — for a package distributed exclusively as a git URL
and a GitHub Release asset, the wheel metadata carries no pointer back to the repo, the release page
or the changelog, so a consumer holding only the `.whl` has no trail. Same shape across all six
packages, so this is a monorepo-wide cleanup, not a Phase-28 regression.

**Fix:**

```toml
license = "MIT"

[project.urls]
Homepage = "https://github.com/gravity-quant/market-libs"
Repository = "https://github.com/gravity-quant/market-libs"
Changelog = "https://github.com/gravity-quant/market-libs/blob/main/packages/market-data-client/README.md#changelog"
```

---

_Reviewed: 2026-08-12T00:46:15Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
