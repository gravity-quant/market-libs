---
status: complete
phase: 34-releases-por-paquete
source: [34-01-SUMMARY.md, 34-02-SUMMARY.md, 34-03-SUMMARY.md]
started: 2026-08-27T23:11:41Z
updated: 2026-08-27T23:16:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Confirm the two public releases are correct end-to-end
expected: |
  - `pip install` from `https://github.com/gravity-quant/market-libs/releases/download/iol-client-v0.3.0/iol_client-0.3.0-py3-none-any.whl`
    succeeds in a fresh Python 3.12 venv and `iol_client.__version__` reports `0.3.0`.
  - `pip install` from `https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.5.0/market_data_client-0.5.0-py3-none-any.whl`
    succeeds and `market_data_client.__version__` reports `0.5.0`.
  - The three Phase-33 shape fixes are live in the installed package: `CalendarConfigPreview` exists
    and `preview_calendar_config` is present on the client; `MarketDataSnapshot.from_api(None).market_data`
    is `None`; `Symbol.from_api(None).updated_at` is `None`.
result: pass
source: automated
note: |
  Verified live by Claude in a scratch `uv venv --python 3.12`, installing both wheels directly from
  the public GitHub Releases (not from local source) and asserting the version strings and the three
  SC-1/SC-2/SC-3 behavior changes via a Python one-liner against the installed package. Output:
    iol_client version: 0.3.0
    market_data_client version: 0.5.0
    CalendarConfigPreview class methods present (from_api, to_dict, valid, warnings, ...)
    MarketDataSnapshot.market_data default (via from_api(None)): None
    Symbol.updated_at default: None
    client has preview_calendar_config: True
  This is exactly the class of check Claude should automate rather than ask a human to run — see
  gsd-core/references/checkpoints.md golden rule 1.

### 2. GitHub Release pages look right to you
expected: |
  Visiting https://github.com/gravity-quant/market-libs/releases/tag/iol-client-v0.3.0 and
  https://github.com/gravity-quant/market-libs/releases/tag/market-data-client-v0.5.0 shows the
  correct package, version, generated release notes, and both a .whl and .tar.gz asset attached.
result: pass

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
