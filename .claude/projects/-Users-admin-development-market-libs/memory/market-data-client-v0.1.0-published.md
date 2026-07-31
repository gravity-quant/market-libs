---
name: market-data-client-v0.1.0-published
description: market-data-client v0.1.0 is the 6th monorepo package, prepared for publication via the per-package release tag market-data-client-v0.1.0
metadata:
  type: project
---

`market-data-client` v0.1.0 is the **6th** package in the `market-libs` monorepo, published
through the existing per-package release pipeline (`release.yml`, tag `market-data-client-v0.1.0`).

**What Phase 24 landed (release prep):**
- Added `market-data-client` to the CI test matrix (`.github/workflows/ci.yml` `matrix.package`),
  so py3.12 + py3.13 `pytest` + coverage jobs now run for the package (D-01).
- Documented the 6th package across the monorepo docs (`CLAUDE.md`): Workspace Structure bullet,
  the CI/CD "6 packages" count, and a `market_data_client` Component Responsibilities row, plus
  the `<pkg>.aio` / `<pkg>.models` meta-rows updated to acknowledge it (D-04).
- Validated (not regenerated) the lockfile and version metadata: `uv.lock` already lists the
  workspace member, `pyproject.toml` registers `market-data-client = { workspace = true }`, and the
  package version is aligned at `0.1.0` (pyproject + `__version__`) — so `release.yml`'s
  version-match gate passes (D-03, D-11, SC-1).

**Package facts:**
- Import name: `market_data_client`; domain: market data / primary-extractor.
- Transport: HTTP sync + async (`client.py` + `aio.py`); auth: Auth0 client-credentials.
- Public surface: `get_health`, `get_health_feed`, `get_calendar`, `get_calendar_config`,
  `get_instruments`, `get_segments`, `get_symbols`, `get_latest`, `get_latest_batch`,
  `get_market_data`; SafeModels (`CalendarConfig`, `Instrument`, `MarketDataSnapshot`, …);
  exception hierarchy `MarketDataError` → `MarketDataAPIError` → `MarketDataAuthError` /
  `MarketDataRateLimitError`.

**Not resolved here:** the Phase 23 Wave 2 live verification remains paused pending Auth0
credentials + develop VPN access — see `phase-23-wave2-pending-creds.md`. Release prep does not
depend on live access.
