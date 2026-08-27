---
phase: 34-releases-por-paquete
reviewed: 2026-08-27T22:10:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - packages/market-data-client/README.md
  - packages/iol-client/pyproject.toml
  - packages/iol-client/src/iol_client/__init__.py
  - packages/market-data-client/pyproject.toml
  - packages/market-data-client/src/market_data_client/__init__.py
  - uv.lock
  - .gitignore
  - packages/market-data-client/tests/test_models.py
  - .claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md
findings:
  critical: 1
  warning: 5
  info: 2
  total: 8
status: issues_found
---

# Phase 34: Code Review Report

**Reviewed:** 2026-08-27T22:10:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Release-prep phase: two version bumps (iol-client 0.2.0→0.3.0, market-data-client 0.4.0→0.5.0),
a changelog promotion, a lockfile refresh, one mypy narrowing fix in a test, a `.gitignore` entry,
and a refreshed agent-facing release memory doc.

**What holds up under verification:**

- Version strings are consistent across all four surfaces. `iol_client.__version__ == "0.3.0"` ==
  `packages/iol-client/pyproject.toml:3` == `uv.lock:384`; `market_data_client.__version__ ==
  "0.5.0"` == `packages/market-data-client/pyproject.toml:3` == `uv.lock:488`.
- The tags exist and point where the memory doc claims: `market-data-client-v0.5.0` and
  `iol-client-v0.3.0` both resolve to `a89fa456`, the PR #12 merge on `origin/main`. Prior-release
  hashes in the doc (`5d0825d`, `7b0e0b2`, `ea92dd8`) all match their tags, and the dates check out
  once read as UTC (v0.4.0 tagged `2026-08-11 21:17 -0300` = 2026-08-12 UTC, as documented).
- `uv lock --check` passes; the lock diff is exactly the two workspace-member version lines, no
  third-party re-resolution.
- The `test_models.py` narrowing fix is **correct and genuinely required**, not cargo cult. I
  reproduced the underlying mypy error in isolation (`assert m["BI"] == 1` on a
  `dict[str, Any] | None` → `Value of type "dict[str, Any] | None" is not indexable` under
  `--strict`). It does not mask a bug: the payload under test explicitly supplies `market_data`, so
  a `None` there would be a parse regression, and the added assert turns that regression into a
  clear assertion failure instead of a `TypeError`. Narrowing coverage is complete — line 121 and
  122 are the only two index sites on a widened field in the whole package outside `models.py`.
- `.gitignore` addition is effective and correctly scoped (`git check-ignore -v .gsd/` →
  `.gitignore:46`). The research-cache files committed alongside it contain no credential-shaped
  strings.
- Full gate is green: 609 market-data tests, 272 iol tests, `mypy` clean on both packages, `ruff
  check` clean.

**Where it fails:** the phase updated the *changelog* to say v0.5.0 is released but left the
*install instructions* in the same README pinned to v0.4.0, so the README now actively hands
consumers the API-incompatible predecessor of the release it announces. Secondary: the release
memory doc contains a scope claim that contradicts its own break list, the MEMORY.md index still
advertises v0.4.0, and iol-client — the other package shipped by this phase — got no memory doc, no
install path, and has no test binding `__version__` to its `pyproject.toml`.

## Critical Issues

### CR-01: README publishes v0.5.0 but instructs consumers to install v0.4.0

**File:** `packages/market-data-client/README.md:15` and `packages/market-data-client/README.md:24`
**Issue:** This phase's diff on this file changed the changelog heading from
`### v0.5.0 — sin publicar todavía` to `### v0.5.0`, removing the "not yet published" caveat, but
left both install commands pinned to the previous release:

```
line 15: ...market-libs.git@market-data-client-v0.4.0#subdirectory=packages/market-data-client
line 24: .../download/market-data-client-v0.4.0/market_data_client-0.4.0-py3-none-any.whl
```

A consumer who reads the v0.5.0 changelog (seven documented source breaks: four dict→model changes
plus SC-1/SC-2/SC-3) and then runs the copy-paste install two screens above gets **v0.4.0**. This
fails silently, not loudly: the `market-data-client-v0.4.0` tag and its release wheel both exist, so
the install succeeds and the mismatch only surfaces later as `TypeError: 'dict' object has no
attribute 'status'`-class breakage when the consumer writes the `health.status` the changelog told
them to write — or, worse, as the truthiness flip the changelog itself flags at lines 141-143, which
does not raise at all.

The repository is now self-contradictory on the install path: the release memory doc
(`market-data-client-releases.md:142-143`) documents the v0.5.0 URLs; the README documents v0.4.0.

**Fix:**
```diff
-uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.4.0#subdirectory=packages/market-data-client"
+uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.5.0#subdirectory=packages/market-data-client"

-pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.4.0/market_data_client-0.4.0-py3-none-any.whl"
+pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.5.0/market_data_client-0.5.0-py3-none-any.whl"
```

Structurally, this pin is hand-maintained in two places and drifted exactly once — consider a test
in `packages/market-data-client/tests/` that greps the README for `market-data-client-v<X>` and
asserts it equals `[project].version`, in the same spirit as the existing
`test_version_metadata.py`.

## Warnings

### WR-01: Memory doc's scope note contradicts its own break list on the mutation surface

**File:** `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md:17-18`
and `:116-119`
**Issue:** Line 17-18 states "**Nothing about the mutation surface or the mutating-gate changed in
this release.**" and lines 116-119 repeat it: "as of v0.5.0 the mutation surface is still symbols +
calendar, unchanged since v0.4.0 ... What v1.6 adds is on the **read/ops** side".

Both claims are contradicted by the same document at lines 21-23, which lists `add_holidays →
AddHolidaysResult` and `delete_holiday → DeleteHolidayResult` among the four source breaks.
`add_holidays` and `delete_holiday` **are** calendar mutations. Their return type changed from
`dict[str, Any]` to a typed model on both surfaces and in both sync and async.

This is the highest-consequence sentence in an agent-facing recall document: an agent or consumer
that trusts "nothing about the mutation surface changed" will scope its migration audit to
`get_health` / `get_health_feed` call sites and skip exactly the two mutation call sites hit by the
truthiness flip the doc warns about at lines 33-35 — the one break the doc explicitly says mypy will
not catch for you.

**Fix:** narrow the claim to what is actually true — the *set* of mutating operations and the gate
semantics are unchanged, the *return types* of two of them are not:

> The set of mutating operations and the mutating-gate semantics are unchanged in this release.
> Two calendar mutations, `add_holidays` and `delete_holiday`, DO change their return type
> (dict → `AddHolidaysResult` / `DeleteHolidayResult`) — audit those call sites too.

### WR-02: MEMORY.md index still advertises v0.4.0 as the latest published release

**File:** `.claude/projects/-Users-admin-development-market-libs/memory/MEMORY.md:2`
**Issue:** The phase refreshed `market-data-client-releases.md` to v0.5.0 but did not refresh the
index entry that points at it, which still reads "latest published is v0.4.0 (calendar write
MUT-MD-02 + live-verified mutation fixes LIVE-MUT-01; ... v0.2.0/v0.3.0/v0.3.1 superseded)". The
index is the cheap surface a recall agent reads first; it now disagrees with both the document body
and the document's own frontmatter `description`, which correctly says v0.5.0. Whichever surface an
agent samples decides which version it recommends.

**Fix:** update the index line to mirror the refreshed frontmatter:
```markdown
- [market-data-client releases](market-data-client-releases.md) — latest published is v0.5.0
  (SOURCE-BREAKING: four ops endpoints dict→typed models + three live-verified shape fixes;
  v0.2.0/v0.3.0/v0.3.1/v0.4.0 superseded, v0.1.0 buggy); install via git subdir @ tag or GitHub
  Release wheel, not PyPI
```
Since this file is derived from the reviewed doc, it belongs to the same change set even though it
was not in the submitted file list.

### WR-03: iol-client README tells consumers to `uv add iol-client` — the package is not on PyPI

**File:** `packages/iol-client/README.md:7`
**Issue:** This phase published `iol-client` v0.3.0 (a 16-signature dict→model source break, per the
README changelog at line 112), but the package's only install instruction is `uv add iol-client`.
Per `CLAUDE.md` and `.github/workflows/release.yml`, the pipeline creates GitHub Releases only and
**does not publish to PyPI**. I verified the name is unregistered: `GET
https://pypi.org/pypi/iol-client/json` → `404` (same for `market-data-client`).

So the documented install fails today, and the name is unclaimed — if anyone registers `iol-client`
on PyPI, this instruction becomes a supply-chain foot-gun that silently installs a third party's
code into a fintech client's environment. The project already recognises this exact hazard: the
market-data README calls it out verbatim at lines 9-11 ("si algún día ese nombre aparece en PyPI, no
sería este paquete"). iol-client, the other package this phase released, has no equivalent warning
and no working install path at all.

**Fix:** mirror the market-data README's install block, pinned to the tag this phase pushed:
```markdown
> **Este paquete NO está publicado en PyPI.** El pipeline de release sólo crea GitHub Releases
> (wheel + sdist). Un `uv add iol-client` a secas falla — y si algún día ese nombre aparece en
> PyPI, no sería este paquete.

uv add "iol-client @ git+https://github.com/gravity-quant/market-libs.git@iol-client-v0.3.0#subdirectory=packages/iol-client"
```

### WR-04: iol-client v0.3.0 shipped with no release memory doc, unlike its sibling

**File:** `.claude/projects/-Users-admin-development-market-libs/memory/` (directory) — compare
`market-data-client-releases.md:1-6`
**Issue:** The phase released two packages and wrote a memory doc for one. There is no
`iol-client-releases.md` and no MEMORY.md entry for iol-client, even though iol-client v0.3.0 is
itself source-breaking — the market-data doc leans on it as precedent (`README.md:128-129`: "mismo
criterio y misma forma que la ruptura dict→modelo de `iol-client` v0.3.0"), and the same truthiness
flip applies to all 16 signatures. An agent asked "what version of iol-client should I install and
what breaks?" has no in-repo record, and no install path either (WR-03).

**Fix:** add `iol-client-releases.md` following the sibling's frontmatter schema (`name`,
`description`, `metadata.type: project`), recording: latest published `iol-client-v0.3.0` (tag on
`a89fa45`, PR #12); the dict→model break across the 16 signatures with the truthiness-flip warning;
the not-on-PyPI install instructions; and a MEMORY.md index line.

### WR-05: iol-client has no test binding `__version__` to `pyproject.toml`

**File:** `packages/iol-client/src/iol_client/__init__.py:87` and
`packages/iol-client/pyproject.toml:3`
**Issue:** This phase hand-edited the version in two separate files per package. market-data-client
has `tests/test_version_metadata.py`, added by a prior review as WR-04, which pins
`__version__` against both `pyproject.toml:[project].version` and the installed distribution
metadata. iol-client has no such test (`ls packages/iol-client/tests/` — 16 test modules, none
covering version metadata).

The publish gate does not close this either: `release.yml:47` extracts the version with
`awk -F\" '/^version[[:space:]]*=/{print $2; exit}' "packages/$PACKAGE/pyproject.toml"` and compares
it to the tag — `__init__.__version__` is never checked. A future release that edits only
`pyproject.toml` ships a wheel whose `iol_client.__version__` lies about itself, in exactly the
field consumers quote in bug reports. This phase happened to get both edits right; nothing verified
that.

**Fix:** copy `packages/market-data-client/tests/test_version_metadata.py` into
`packages/iol-client/tests/`, substituting the package name and distribution name:
```python
assert iol_client.__version__ == _declared_version()
assert iol_client.__version__ == _dist_version("iol-client")
```

## Info

### IN-01: Stale module docstring in test_models.py contradicts the file's own assertions

**File:** `packages/market-data-client/tests/test_models.py:5-7`
**Issue:** The module docstring still says `from_api` tolerates `{}` / `None` "substituting typed
zero-defaults and ``entries == []``". Since SC-2 widened `entries` to `list[str] | None`, the file's
own tests assert the opposite at lines 50, 55 and 65 (`assert snap.entries is None`). Each of those
call sites got an explanatory inline comment; the docstring that states the superseded contract at
the top of the file did not. This phase touched the same file for the narrowing fix without
catching it.

**Fix:** amend line 7 to read `...substituting typed zero-defaults for every field still declared
non-Optional; since 0.5.0 (SC-2) ``entries`` stays ``None`` rather than collapsing to ``[]``.`

### IN-02: Release memory doc records a v1.6 release under a v1.5-named branch/PR without comment

**File:** `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md:13-14`
**Issue:** The doc attributes v0.5.0 to "PR #12" whose source branch is `milestone/v1.5-mutations`
(verified: `a89fa45` = "Merge pull request #12 from gravity-quant/milestone/v1.5-mutations"), while
attributing the content to "v1.6 Phases 31 + 33" at line 20. Both statements are accurate, but the
mismatch is left unexplained and is a future-archaeology trap: someone reconstructing which
milestone shipped what will find v1.6 content merged from a v1.5-labelled branch. Note the tags,
hashes and dates themselves all verify clean.

**Fix:** one clause at line 13 — "PR #12 (branch still named `milestone/v1.5-mutations`; the v1.6
work continued on it)".

---

_Reviewed: 2026-08-27T22:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
