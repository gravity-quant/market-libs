---
name: market-data-client-releases
description: market-data-client latest published release is v0.5.0 (minor on a 0.x line, but SOURCE-BREAKING — four ops endpoints (get_health, get_health_feed, add_holidays, delete_holiday) stop returning dicts and return typed models, plus three shape fixes on already-published models verified live against develop). v0.2.0/v0.3.0/v0.3.1/v0.4.0 superseded; v0.1.0 buggy. Install via git subdirectory or the GitHub Release wheel — not on PyPI.
metadata:
  type: project
---

`market-data-client` is the **6th** package in the public `gravity-quant/market-libs` monorepo
(subdirectory `packages/market-data-client`). Distribution name `market-data-client`, import
`market_data_client`. **Not published to PyPI** — the pipeline (`release.yml`, tag `*-client-v*`)
only creates GitHub Releases with wheel + sdist.

**Latest published: `market-data-client-v0.5.0`** (2026-08-27, tag on merge commit `a89fa45`,
PR #12, `release.yml` run `33118800550`). This is the release to install. It is a **minor** over
v0.4.0 — it types the four ops endpoints and corrects three model shapes against the live wire.
**It is SOURCE-BREAKING**: seven source breaks in total — four dict→model changes plus three shape
changes on models that already existed (detailed below). The set of mutating operations and the
mutating-gate semantics are unchanged in this release — but two of the four dict→model breaks
(`add_holidays`, `delete_holiday`) ARE calendar mutations whose return type changed; see below.

**v0.5.0 adds (v1.6 Phases 31 + 33 — TYP-02/TYP-03 + LIVE-TYP-01):**
- **Four ops endpoints stop returning dictionaries and return typed models:** `get_health` →
  `Health`, `get_health_feed` → `HealthFeed`, `add_holidays` → `AddHolidaysResult`,
  `delete_holiday` → `DeleteHolidayResult`. Each changes on **both surfaces** (class method and
  module shim) and in **both sync and async**. Access moves from `health["status"]` to
  `health.status`; subscripting the result now raises `TypeError` because the models are not
  subscriptable. Eight new models are exported in the package `__all__` and in
  `market_data_client.models.__all__` — `Health`, `HealthAuth`, `HealthFeed`, `FeedIngestor`,
  `FeedMarket`, `FeedPipeline`, `AddHolidaysResult`, `DeleteHolidayResult` — all frozen + `slots`,
  built via `SafeModel.from_api()`. **Escape hatch:** `to_dict()` reprojects any of them to the flat
  dict, which is what `len()` / `isinstance` call sites want; it is NOT a valid input to a schema
  snapshot, because the walker has already coerced every declared field and dropped every
  undeclared key.
- **The truthiness flip the typechecker does not catch:** an empty dict is falsy, a dataclass
  instance is **always** truthy. Any `if not result:` branch guarding one of these four calls
  silently stops firing. mypy does not flag it — this is the one break you must grep for by hand.
- **Three shape fixes on already-published models** (verified live against develop in Phase 33):
  - **SC-1** — `preview_calendar_config` returns `CalendarConfigPreview`, not `CalendarConfig`.
    `POST /calendar/config/preview` never returned a configuration; it returns a dry-run envelope.
    Nine fields `CalendarConfig` declared were absent from the wire and were being filled with
    zero-values, while three real envelope fields — `valid`, `requires_confirmation` and
    `market_after` — were discarded as undeclared. Only `warnings` matched by name, which is exactly
    what made the defect invisible in review. `CalendarConfigPreview` and its nested `PreviewMarket`
    are new public names. The intended flow is unchanged (preview → inspect `warnings` → reissue
    `set_calendar_config(..., confirm=True)`), but the verdict now arrives typed instead of
    reconstructed.
  - **SC-2** — `MarketDataSnapshot.entries`, `.market_data` and `.staleness_seconds` are now
    `| None`. All three were declared non-optional and arrive `null` on the **no-data** row of
    `GET /marketdata/latest`: for a symbol the feed never delivered, the server sends `symbol` and
    `note` populated and `null` everywhere else. They remain required constructor arguments in the
    same positions — only the annotation widens. Code that indexed or iterated `entries` /
    `market_data` without a `None` check now fails mypy, and `staleness_seconds` is no longer safe
    for direct arithmetic. The widening admits `None` and nothing else: a wrong-typed value is still
    a divergence and still fatal under `strict_decode`.
  - **SC-3** — `Symbol.created_at` and `.updated_at` are now `str | None` (were `str = ""`).
    `Symbol` serves four endpoints with three body shapes and only `GET /symbols` sends both
    timestamps; the acks of `POST /symbols`, `POST /symbols/batch` and `PATCH /symbols/{symbol_id}`
    send neither. The old declaration fabricated two empty strings on every write — indistinguishable
    from a real row with blank timestamps — and made every write fatal under `strict_decode`.
- **Tolerance preserved on the two already-published mutations:** an absent, `null`, list or scalar
  body from `add_holidays` / `delete_holiday` still degrades to the zero-valued result rather than
  raising — **including under `strict_decode`** — so an already-published mutation never answers an
  anomalous ACK with an exception raised after the write was committed. The divergence is still
  recorded on the `market_data_client` logger.

**v0.4.0 added (v1.5 Phases 26-27 — MUT-MD-02 + LIVE-MUT-01), carried forward into v0.5.0:**
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

**v0.3.1 fixed (quick task `260731-t9o`), carried forward into v0.5.0:** `get_latest_batch` returned empty `MarketDataSnapshot`s.
`parse_latest_response` (`_core.py`, shared by sync + async) assumed the batch
`POST /marketdata/latest` returned a bare list, but the server returns an envelope
`{"requested","count","not_found","server_time","items":[...]}` — it iterated the dict KEYS instead
of `items[]`, yielding N empty snapshots. Fixed by unwrapping `items` (same pattern as sibling
`parse_market_data_response`), preserving the single-`get_latest` bare-list path; a dict without
`items` degrades to `[]`. This closes the WR-01 read-path gap flagged in the Phase 25 review — the
live response shape (which WR-01 was waiting on) was confirmed here. Two mis-mocked client-level batch
tests (which hid the bug) were corrected to the real envelope.

**v0.3.0 added (v1.5 Phase 25 — GATE-MD-01 + MUT-MD-01), carried forward into v0.5.0:**
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

**Scope note:** as of v0.5.0 the *set* of mutating operations and the mutating-gate semantics are
unchanged since v0.4.0 — still **symbols + calendar**, still behind the same opt-in mutating-gate
(`mutating_allowed=True` + a matching `expected_host`); the default client still refuses every
mutation with zero HTTP requests and zero Auth0 round-trips. **But two calendar mutations DO change
return type in this release:** `add_holidays` → `AddHolidaysResult` and `delete_holiday` →
`DeleteHolidayResult` (dict → typed model, same truthiness-flip hazard as the read-side breaks —
audit those call sites too). What v1.6 mainly adds is on the **read/ops** side: that surface is now
**typed**, and it was exercised **in STRICT DECODE mode against the live API** under LIVE-TYP-01
(v1.6 Phase 33) — which is precisely what surfaced the three shape divergences (SC-1, SC-2, SC-3)
now fixed above.
Strict decode raises on a missing, wrong-typed or non-dict field but **never** on extra wire keys, so
legitimate upstream field growth stays informational. The mutation surfaces were previously
exercised live against develop under LIVE-MUT-01 (v1.5 Phase 27) using dedicated test identifiers
and a create → verify → revert cleanup. Measured end state, still current: zero ACTIVE residue — the
calendar was fully restored (0 probe holidays), and the six `GSDPROBE/*` symbol rows remain
permanently `active=false` because the live API has NO `DELETE /symbols` (the only revert is
`PATCH active=false`). The identifiers are stable, not timestamped, so the residue is capped at
exactly six rows; `grep GSDPROBE/` is the handle for them.

**Prior releases:** `v0.4.0` (2026-08-12, tag on merge commit `5d0825d`, PR #10) = calendar-write
surface (MUT-MD-02) + live-verified mutation fixes (LIVE-MUT-01) + the documented `CalendarDay` field
replacement — superseded by v0.5.0, which keeps all of it. `v0.3.1` (2026-08-01, tag on merge commit
`7b0e0b2`, PR #9) = `get_latest_batch` envelope-unwrap fix. `v0.3.0` (2026-07-31, tag `ea92dd8`,
PR #8) = first mutation surface (symbols write + mutating-gate).
`v0.2.0` (2026-07-31) = read surface reconciled against live develop (LIVE-MD-01):
`get_latest(symbol=…)` required; `MarketDataSnapshot` `marketId`→`market_id` + `active`/`market_data`/
`staleness_seconds`/`note`; `CalendarConfig` reconciled; `parse_market_data_response` envelope-unwrap.
v0.5.0 keeps all of this. **`v0.1.0` is superseded/buggy** (pre-live-verification) — do not recommend it.

**Install (repo is PUBLIC, no auth needed):**
- git, pinned to tag (recommended): `uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.5.0#subdirectory=packages/market-data-client"` (pip: `pip install "git+…@market-data-client-v0.5.0#subdirectory=packages/market-data-client"`).
- release wheel: `pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.5.0/market_data_client-0.5.0-py3-none-any.whl"`.

**Runtime config (env / .env):** `MARKET_DATA_CLIENT_ID`, `MARKET_DATA_CLIENT_SECRET`,
`MARKET_DATA_AUDIENCE`, `MARKET_DATA_AUTH0_TOKEN_URL` (absolute Auth0 URL, correct tenant),
optional `MARKET_DATA_BASE_URL` (defaults to develop). Mutations additionally require
`mutating_allowed=True` + a matching `expected_host`. Python ≥3.12. Deps: httpx, python-dotenv, tenacity.

Related: [[phase-23-wave2-pending-creds]] (resolved — creds supplied, live sweep ran).
