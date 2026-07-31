---
name: market-data-client-releases
description: market-data-client latest published release is v0.2.0 (LIVE-MD-01 fixes); v0.1.0 is superseded/buggy. Install via git subdirectory or the GitHub Release wheel — not on PyPI.
metadata:
  type: project
---

`market-data-client` is the **6th** package in the public `gravity-quant/market-libs` monorepo
(subdirectory `packages/market-data-client`). Distribution name `market-data-client`, import
`market_data_client`. **Not published to PyPI** — the pipeline (`release.yml`, tag `*-client-v*`)
only creates GitHub Releases with wheel + sdist.

**Latest published: `market-data-client-v0.2.0`** (2026-07-31, tag on merge commit `5903f75`).
This is the release to install — it carries the LIVE-MD-01 fixes. **`v0.1.0` is superseded/buggy**
(pre-live-verification) — do not recommend it.

**v0.2.0 breaking changes vs v0.1.0** (why it's a minor bump, from the first real credentialed
develop sweep):
- `get_latest(symbol=...)` is now **required** (develop returns 422 without it; OpenAPI `required=True`).
- `MarketDataSnapshot` reconciled vs the real wire: `marketId`→`market_id`; added `active`,
  `market_data` (dict passthrough), `staleness_seconds`, `note`; the invented `MarketDataEntry` retired.
- `CalendarConfig` reconciled: dropped invented `businessDays`; added `open`/`close`/`enabled`/
  `editable`/`env_bypass`/`pre_open_minutes`/`source`/`updated_at`/`updated_by`/`warnings`.
- Fixed `parse_market_data_response` envelope-unwrap — `get_market_data` now reads `items[]`.

**Install (repo is PUBLIC, no auth needed):**
- git, pinned to tag (recommended): `uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.2.0#subdirectory=packages/market-data-client"` (pip: `pip install "git+…@market-data-client-v0.2.0#subdirectory=packages/market-data-client"`).
- release wheel: `pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.2.0/market_data_client-0.2.0-py3-none-any.whl"`.

**Runtime config (env / .env):** `MARKET_DATA_CLIENT_ID`, `MARKET_DATA_CLIENT_SECRET`,
`MARKET_DATA_AUDIENCE`, `MARKET_DATA_AUTH0_TOKEN_URL` (absolute Auth0 URL, correct tenant),
optional `MARKET_DATA_BASE_URL` (defaults to develop). Python ≥3.12. Deps: httpx, python-dotenv, tenacity.

The fixes shipped as post-v1.4-close follow-up quick tasks `260731-j93` (symbol) + `260731-jim`
(models/envelope) + `260731-l4s` (v0.2.0 bump); see STATE.md Quick Tasks Completed. Related:
[[phase-23-wave2-pending-creds]] (now resolved — creds were supplied and the live sweep ran).
