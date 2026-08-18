---
name: market-data-client-releases
description: market-data-client latest published release is v0.4.0 (minor — calendar-write surface (MUT-MD-02) + live-verified mutation fixes (LIVE-MUT-01), on top of the v0.3.x symbols write + mutating-gate). v0.2.0/v0.3.0/v0.3.1 superseded; v0.1.0 buggy. Install via git subdirectory or the GitHub Release wheel — not on PyPI.
metadata:
  type: project
---

`market-data-client` is the **6th** package in the public `gravity-quant/market-libs` monorepo
(subdirectory `packages/market-data-client`). Distribution name `market-data-client`, import
`market_data_client`. **Not published to PyPI** — the pipeline (`release.yml`, tag `*-client-v*`)
only creates GitHub Releases with wheel + sdist.

**Latest published: `market-data-client-v0.4.0`** (2026-08-12, tag on merge commit `5d0825d`,
PR #10, `release.yml` run `31549711805`). This is the release to install. It is a **minor** over
v0.3.1 — it adds the calendar-write surface and the fixes verified live against develop, and it
carries a documented `CalendarDay` field replacement (detailed below).

**v0.4.0 adds (v1.5 Phases 26-27 — MUT-MD-02 + LIVE-MUT-01):**
- **Calendar write (MUT-MD-02):** eight new public names in the flat `__all__` — the request-models
  `MarketHoursIn`, `HolidayIn`, `HolidaysIn` and the functions `set_calendar_config`,
  `delete_calendar_config`, `preview_calendar_config`, `add_holidays`, `delete_holiday` — over
  `PUT /calendar/config`, `DELETE /calendar/config`, `POST /calendar/config/preview`,
  `POST /calendar/holidays` and `DELETE /calendar/holidays/{day}`. All five functions have async
  counterparts in `market_data_client.aio` (module-level shims, not re-exported into the flat
  namespace, per the monorepo convention). `confirm` is a FIELD of `MarketHoursIn` (default
  `False`), so it rides `set_calendar_config` / `preview_calendar_config` only. It is a *second
  opinion*, NOT a persistence gate: the server demands it only when the requested window produces
  warnings — a warning-free config is written with `confirm=False`. `delete_calendar_config`,
  `add_holidays` and `delete_holiday` have NO `confirm` argument at all. The real guard on the
  whole surface — and the only guard on those three — is the existing opt-in mutating-gate
  (`mutating_allowed=True` + `expected_host`).
- **Live-verified fixes (LIVE-MUT-01):** `update_symbol(symbol_id)` was **widened** from `str` to
  `int | str` across all four routes (the `_core` request builder, `Client`, `AsyncClient` and both
  module shims); `Symbol` gains five **defaulted** fields (`id`, `market_id`, `created_at`,
  `updated_at`, `received_at`); `Symbol.marketId` is **preserved** as a deprecated alias mirrored
  from the wire's `market_id` via a `from_api` override; and the symbols-write response envelope is
  unwrapped while preserving `list[Symbol]`. All strictly additive or widening — no v0.3.1 consumer
  breaks.
- **`CalendarDay` field replacement (strictly breaking, documented, shipped inside a minor):**
  `date`, `marketId` and `isBusinessDay` were **removed** (no compatibility aliases) and replaced
  by `day`, `closed`, `description`, `open_time` and `close_time`, reconciled against develop's
  real wire. It ships in a minor bump because `parse_calendar_response` used to iterate the envelope's keys instead of
  `days[]`: no published consumer could ever have held a populated `CalendarDay`, so the old fields
  were not readable in practice. Called out explicitly so the replacement is discoverable rather
  than silent.

**v0.3.1 fixed (quick task `260731-t9o`), carried forward into v0.4.0:** `get_latest_batch` returned empty `MarketDataSnapshot`s.
`parse_latest_response` (`_core.py`, shared by sync + async) assumed the batch
`POST /marketdata/latest` returned a bare list, but the server returns an envelope
`{"requested","count","not_found","server_time","items":[...]}` — it iterated the dict KEYS instead
of `items[]`, yielding N empty snapshots. Fixed by unwrapping `items` (same pattern as sibling
`parse_market_data_response`), preserving the single-`get_latest` bare-list path; a dict without
`items` degrades to `[]`. This closes the WR-01 read-path gap flagged in the Phase 25 review — the
live response shape (which WR-01 was waiting on) was confirmed here. Two mis-mocked client-level batch
tests (which hid the bug) were corrected to the real envelope.

**v0.3.0 added (v1.5 Phase 25 — GATE-MD-01 + MUT-MD-01), carried forward into v0.4.0:**
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

**Scope note:** as of v0.4.0 the mutation surface is **symbols + calendar**. Both surfaces were
exercised **live against develop** under LIVE-MUT-01 (v1.5 Phase 27) — no longer mocked tests only —
using dedicated test identifiers and a create → verify → revert cleanup. Measured end state: zero
ACTIVE residue — the calendar was fully restored (0 probe holidays), and the six `GSDPROBE/*`
symbol rows remain permanently `active=false` because the live API has NO `DELETE /symbols` (the
only revert is `PATCH active=false`). The identifiers are stable, not timestamped, so the residue
is capped at exactly six rows; `grep GSDPROBE/` is the handle for them. Everything still sits
behind the opt-in mutating-gate
(`mutating_allowed=True` + a matching `expected_host`); the default client still refuses every
mutation with zero HTTP requests and zero Auth0 round-trips.

**Prior releases:** `v0.3.1` (2026-08-01, tag on merge commit `7b0e0b2`, PR #9) = `get_latest_batch`
envelope-unwrap fix — superseded by v0.4.0, which keeps the fix. `v0.3.0` (2026-07-31, tag `ea92dd8`,
PR #8) = first mutation surface (symbols write + mutating-gate).
`v0.2.0` (2026-07-31) = read surface reconciled against live develop (LIVE-MD-01):
`get_latest(symbol=…)` required; `MarketDataSnapshot` `marketId`→`market_id` + `active`/`market_data`/
`staleness_seconds`/`note`; `CalendarConfig` reconciled; `parse_market_data_response` envelope-unwrap.
v0.4.0 keeps all of this. **`v0.1.0` is superseded/buggy** (pre-live-verification) — do not recommend it.

**Install (repo is PUBLIC, no auth needed):**
- git, pinned to tag (recommended): `uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.4.0#subdirectory=packages/market-data-client"` (pip: `pip install "git+…@market-data-client-v0.4.0#subdirectory=packages/market-data-client"`).
- release wheel: `pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.4.0/market_data_client-0.4.0-py3-none-any.whl"`.

**Runtime config (env / .env):** `MARKET_DATA_CLIENT_ID`, `MARKET_DATA_CLIENT_SECRET`,
`MARKET_DATA_AUDIENCE`, `MARKET_DATA_AUTH0_TOKEN_URL` (absolute Auth0 URL, correct tenant),
optional `MARKET_DATA_BASE_URL` (defaults to develop). Mutations additionally require
`mutating_allowed=True` + a matching `expected_host`. Python ≥3.12. Deps: httpx, python-dotenv, tenacity.

Related: [[phase-23-wave2-pending-creds]] (resolved — creds supplied, live sweep ran).
