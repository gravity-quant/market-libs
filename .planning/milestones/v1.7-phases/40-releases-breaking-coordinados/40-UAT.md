---
status: complete
phase: 40-releases-breaking-coordinados
source: [40-01-SUMMARY.md, 40-02-SUMMARY.md, 40-03-SUMMARY.md]
started: 2026-08-30T19:33:47Z
updated: 2026-08-30T19:52:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. GitHub Releases page shows the four new releases
expected: |
  Visiting https://github.com/gravity-quant/market-libs/releases shows four new entries:
  market-data-client-v0.6.0, iol-client-v0.4.0, matriz-client-v0.3.0, higyrus-client-v0.3.0.
  Each release has a wheel (.whl) and sdist (.tar.gz) asset attached, is not marked draft or
  prerelease, and the tag it points to resolves to the same merge commit on main.
result: pass
verified_by: claude (gh release view, git rev-parse — draft/prerelease flags, exact asset names, and tag anchors all confirmed programmatically)

### 2. PR #15 is merged into main
expected: |
  https://github.com/gravity-quant/market-libs/pull/15 shows state MERGED (not just closed),
  base branch main, and main's tip is the merge commit that PR produced.
result: pass
verified_by: claude (gh pr view — state MERGED, base main, mergeCommit.oid matches origin/main tip exactly)

### 3. Fresh install from the public wheels resolves the new versions
expected: |
  In a clean virtualenv (no prior installs), running `pip install <wheel-url>` (or
  `uv pip install <wheel-url>`) for each of the four public release wheel URLs installs
  successfully and `importlib.metadata.version(...)` / `pkg.__version__` reports 0.6.0 for
  market-data-client, 0.4.0 for iol-client, 0.3.0 for matriz-client, and 0.3.0 for higyrus-client.
result: pass
verified_by: claude (fresh throwaway venv outside repo, installed from public release wheel URLs; __version__ == importlib.metadata.version() for all four, __file__ resolved into venv site-packages)

### 4. READMEs show the breaking changes as dated Changelog entries with migration tables
expected: |
  Opening each of the four package READMEs (market-data-client, iol-client, matriz-client,
  higyrus-client), the `## Changelog` section's first entry is the new version (no more
  "Unreleased — BREAKING" heading), each with a migration table showing what changed and how
  callers should adapt.
result: pass
verified_by: claude (grepped all four READMEs — new version is first Changelog entry, no "Unreleased" string remains, each has a Función/Antes/Ahora-style migration table)

### 5. ambito-financiero-client and wallets-client were not published in this round
expected: |
  On the GitHub Releases page and in `git tag -l`, ambito-financiero-client and wallets-client
  show no new v0.3.0 tag/release — they remain at their last-published v0.2.0, unchanged by
  this release round.
result: pass
verified_by: claude (gh release list + git tag -l — latest release for both is v0.2.0, no v0.3.0 tag exists for either)

### 6. market-data-client's widened market_id/active fields behave as documented for a no-data row
expected: |
  Using the installed market-data-client==0.6.0 package, calling `MarketDataSnapshot.from_api(None)`
  (or hitting a live "no data" market-data response) returns `market_id=None` and `active=None`
  instead of empty-string defaults or a raised error — matching the migration table's documented
  behavior change.
result: pass
verified_by: claude (fresh throwaway venv, installed market-data-client==0.6.0 from public wheel, MarketDataSnapshot.from_api(None).market_id is None and .active is None, no exception raised)

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
