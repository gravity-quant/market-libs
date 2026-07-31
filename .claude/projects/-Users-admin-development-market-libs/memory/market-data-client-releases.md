---
name: market-data-client-releases
description: market-data-client latest published release is v0.3.0 (symbols write + mutating-gate, non-breaking over v0.2.0 read surface). v0.2.0 read-only superseded; v0.1.0 buggy. Install via git subdirectory or the GitHub Release wheel — not on PyPI.
metadata:
  type: project
---

`market-data-client` is the **6th** package in the public `gravity-quant/market-libs` monorepo
(subdirectory `packages/market-data-client`). Distribution name `market-data-client`, import
`market_data_client`. **Not published to PyPI** — the pipeline (`release.yml`, tag `*-client-v*`)
only creates GitHub Releases with wheel + sdist.

**Latest published: `market-data-client-v0.3.0`** (2026-07-31, tag on merge commit `ea92dd8`,
PR #8, `release.yml` run `30673218876`). This is the release to install. It is a **non-breaking
minor** over v0.2.0 — it only ADDS the first mutation surface behind an opt-in safety gate; the
v0.2.0 read surface is unchanged.

**v0.3.0 adds (v1.5 Phase 25 — GATE-MD-01 + MUT-MD-01):**
- **Mutating-gate (opt-in, refuse-by-default):** a default `Client()`/`AsyncClient()` refuses every
  mutation with the new typed `MarketDataMutationNotAllowedError` (⊂ `MarketDataError`) and emits
  **zero HTTP requests and zero Auth0 round-trips**. Enable with `mutating_allowed=True` (constructor
  or `configure()`), plus a second **exact-hostname** env gate (`expected_host`) so a mutation can't
  fire against an unexpected `base_url`. The flag lives on shared state, so `with_options()` views
  inherit it; `configure()` uses a `bool | None` sentinel so a later `configure(base_url=…)` can't
  silently reset a prior opt-in. Dual sync/async.
- **Symbols write:** `create_symbol` (`NewSymbol`), `create_symbols` (batch 1–500, `NewSymbols`),
  `update_symbol` (`SymbolPatch`) — sync and async, typed request-models → JSON, tolerant `SafeModel`
  responses, `422` → typed error; all three dispatched as idempotent per spec.

**Scope note:** v0.3.0 carries **symbols-write only**. Calendar mutations (MUT-MD-02, Phase 26) and
the live verification (LIVE-MUT-01, Phase 27) were NOT yet done when v0.3.0 shipped — it was released
early on explicit operator request, out of the planned Phase-28 order. Symbols mutations have only
been exercised against mocked tests, never live develop. Calendar write would land as a later minor.

**Known read-path gap (pre-existing, unfixed as of v0.3.0):** `parse_latest_response` (`get_latest`)
still lacks the dict-envelope unwrap + `isinstance` guard that its sibling `parse_market_data_response`
got in v0.2.0 — a `{items:[…]}` or scalar body would mis-parse. Flagged as WR-01 in Phase 25 review;
fix deferred to the live reconciliation (Phase 27) since the correct shape needs live confirmation.

**Prior releases:** `v0.2.0` (2026-07-31) = read surface reconciled against live develop (LIVE-MD-01):
`get_latest(symbol=…)` required; `MarketDataSnapshot` `marketId`→`market_id` + `active`/`market_data`/
`staleness_seconds`/`note`; `CalendarConfig` reconciled; `parse_market_data_response` envelope-unwrap.
v0.3.0 keeps all of this. **`v0.1.0` is superseded/buggy** (pre-live-verification) — do not recommend it.

**Install (repo is PUBLIC, no auth needed):**
- git, pinned to tag (recommended): `uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.3.0#subdirectory=packages/market-data-client"` (pip: `pip install "git+…@market-data-client-v0.3.0#subdirectory=packages/market-data-client"`).
- release wheel: `pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.3.0/market_data_client-0.3.0-py3-none-any.whl"`.

**Runtime config (env / .env):** `MARKET_DATA_CLIENT_ID`, `MARKET_DATA_CLIENT_SECRET`,
`MARKET_DATA_AUDIENCE`, `MARKET_DATA_AUTH0_TOKEN_URL` (absolute Auth0 URL, correct tenant),
optional `MARKET_DATA_BASE_URL` (defaults to develop). Mutations additionally require
`mutating_allowed=True` + a matching `expected_host`. Python ≥3.12. Deps: httpx, python-dotenv, tenacity.

Related: [[phase-23-wave2-pending-creds]] (resolved — creds supplied, live sweep ran).
