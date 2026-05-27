# Feature Research

**Domain:** Live-API verification of HTTP financial-API client libraries (market-libs monorepo)
**Researched:** 2026-05-26
**Confidence:** HIGH (grounded in direct reading of `.planning/codebase/` + client source)

> "Features" here = the categories of **verification checks** a thorough live verification of
> a financial-API client must perform. Not product features. Table stakes = checks the cycle
> MUST run or it is incomplete. Differentiators = high-value verification techniques.
> Anti-features = verification actions to deliberately AVOID (especially destructive/live-mutating).

## Feature Landscape

### Table Stakes (Verification the cycle MUST cover)

Skip any of these and the verification is incomplete — a real client/server divergence could slip through.

| Check | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Auth flow — first call** | Every client (except Ámbito) authenticates lazily on first call; if auth is broken nothing else runs | LOW | iol=OAuth2 password grant; higyrus=Bearer via `POST /api/login`; matriz=`X-Auth-Token` via `POST /auth/getToken`. Verify `login()` AND lazy auth via a plain endpoint call without explicit `login()`. |
| **Token caching (no re-auth per call)** | Token is cached in module globals with TTL; a second call must reuse it, not re-login | MEDIUM | Assert auth endpoint hit only once across N calls (count requests / observe latency / log). iol TTL=900s−60s buffer; higyrus/matriz=23h. |
| **Token refresh after expiry** | TTL math (`time.time()` based) decides re-auth; off-by-one or skew makes tokens never/always refresh | MEDIUM | Hard to trigger live within a 15-min run (iol) and impossible in a single run for 23h tokens (higyrus/matriz). Verify the TTL boundary logic with a **mocked** clock; live-verify only the iol 900s path opportunistically. |
| **Happy-path call of every public endpoint** | The core of the cycle — exercise the full public surface sync + async | MEDIUM | iol: `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type`. higyrus: `get_health`, `get_listado_cuentas`, `get_movimientos`, `get_posicion_valuada`, `get_posiciones`. matriz READ-ONLY: segments, all/byCFI/bySegment/detail(s) instruments, market data, trades, order *reads*, risk positions/report. ambito: `get_dollar_banco_nacion`. |
| **Response shape/type conformance** | Does the client's *assumed* shape match reality? This is the headline risk for dict-returning iol and the `from_api`/`SafeModel` clients | HIGH | iol returns raw `dict`/`list` with zero validation — capture real payload keys/types and compare to what callers assume. matriz/higyrus models silently coerce — must compare model fields against raw payload to detect drops. |
| **Error-path mapping (401/403/429/5xx → typed exception)** | `_raise_for_response()` maps status→exception in every client; a wrong/missing mapping mis-signals to callers | MEDIUM | Live triggering of 401 is feasible (bad credentials via `configure()`). 403/429/5xx are hard to force live without abuse → verify those with **mocked** regression tests, not live. 401 live is a legitimate quick check. |
| **Application-level error detection (payload-embedded)** | matriz raises `PrimaryAPIError` on `{"status":"ERROR"}`; higyrus parses `"errors"` key — these are NOT HTTP errors | MEDIUM | Trigger live by querying a bogus symbol / invalid account. Confirm the typed exception fires and carries the server's error detail. |
| **Decimal / Argentine-locale number parsing** | Ámbito returns `"1.415,00"` strings parsed by `parse_ar_decimal()` (strip `.`, swap `,`→`.`) | LOW | Verify the real wire format still matches the parser's assumption (thousands `.`, decimal `,`). A format change (e.g. server switches to `1415.00`) silently corrupts the value. matriz/iol numbers are JSON numbers — verify they arrive as numbers not strings. |
| **Date format handling** | iol historical uses path `{desde:%Y-%m-%d}/{hasta:%Y-%m-%d}`; ambito formats a date into the URL; matriz trades take `date`/`dateFrom`/`dateTo` strings | LOW | Verify the server accepts the emitted format and the response dates parse back. Confirm timezone/locale of returned dates. |
| **Empty / no-data / 204 responses** | Real endpoints return empty lists (no movements, market closed, instrument with no series); ambito raises `NoDataError` on empty rows | MEDIUM | Drive each list endpoint to a known-empty case. Confirm empty list (not crash, not `None`), and that ambito's `NoDataError` fires for a date with no quote. |
| **List vs object response discrimination** | higyrus `assert isinstance(raw, list/dict)` and iol's `data.get("titulos", [])` assume a container shape | MEDIUM | If the server returns an object where the client expects a list (or wraps the list in a new envelope key), higyrus `assert` becomes `AssertionError` (or silently passes under `-O`) and iol returns `[]`. Verify the real container shape per endpoint. |
| **Sync vs async parity (same shape both surfaces)** | Logic is duplicated across `client.py`/`aio.py`; CONCERNS flags higyrus async `_request` already deviates in `drop_none` handling | HIGH | For every iol/higyrus/ambito endpoint, call sync and async against live and assert structurally-equal results. matriz has no `aio.py` → sync-only (out of scope async). This is where duplicated-logic bugs hide. |
| **Empty/missing-credential pre-flight** | Clients raise `AuthError` before any HTTP call when credentials are blank | LOW | `configure()` with empty user/password and assert the right exception fires before network I/O. |

### Differentiators (High-value verification techniques)

Not strictly required for a pass/fail, but they catch the silent, expensive bugs that simple happy-path smoke tests miss.

| Check | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Type-discrepancy detection for dict-returning clients** | iol returns unvalidated `dict[str, Any]` — the single highest-value technique for iol. Build a field→observed-type map from the live payload and compare to documented/assumed shape | HIGH | Catches "IOL renamed a field / changed number→string / nested an object" that otherwise reaches callers as wrong data. Feeds directly into deciding whether iol needs a model layer (CONCERNS: "Medium priority" gap). |
| **Silent field-drop detection (SafeModel/from_api clients)** | higyrus `SafeModel` and matriz `from_api` substitute typed zero-defaults for missing/wrong-type fields and IGNORE extra keys — a renamed server field becomes `""`/`0`/`0.0` with NO error | HIGH | Compare raw `resp.json()` keys against the model's declared fields. Flag: (a) payload keys the model never reads (silent drop), (b) model fields absent from payload (silent default). This is higyrus's and matriz's headline risk. |
| **Response drift / snapshot diffing** | Capture a structural snapshot (keys + value types, not values) of each live response; diff against a committed baseline to detect API evolution over time | MEDIUM | Values change every call (prices), so snapshot the *schema* not the data. Enables re-running the cycle later to catch drift. Pairs with mocked regression fixtures — a captured real payload becomes the mock fixture. |
| **Live payload → regression fixture capture** | Each real response captured during the live run becomes the mock body for the regression test that locks in the fix | MEDIUM | Closes the cycle's loop (finding→fix→mocked regression) cheaply and authentically; follows the existing `"""Regression: ... (issue #NNN)."""` convention. |
| **Status-`ERROR` envelope coverage (matriz)** | matriz's `_request` checks `data.get("status") == "ERROR"` on EVERY response — verify it fires across multiple distinct error conditions, not just one | MEDIUM | Bogus symbol, invalid account, malformed param. Confirms the envelope check generalizes and that the success path doesn't falsely trip it. |
| **Anti-bot resilience probe (ambito)** | Ámbito 403s the default `python-httpx` UA; the client spoofs Chrome 124 (a 2024 string). Verify the spoof still works and document the exact failure mode if it stops | MEDIUM | If Ámbito tightens detection the client "silently breaks with no clear error" (CONCERNS). Verify a real call succeeds AND that a deliberately-wrong UA reproduces the 403 → confirms the workaround is what's load-bearing. |
| **Container-key envelope verification (matriz/iol)** | matriz unwraps `["order"]`/`["orders"]`/`["marketData"]`/`["trades"]`/`["positions"]`; iol unwraps `["titulos"]` — a missing key raises `KeyError`, not a typed error | MEDIUM | Verify each envelope key exists in the real response. A renamed envelope key is a `KeyError` leak (not mapped to the package's exception hierarchy) — candidate fix. |

### Anti-Features (Verification actions to deliberately AVOID)

These look like "thorough" verification but are destructive, abusive, or unreliable. Do NOT do them.

| Anti-Check | Why Tempting | Why Problematic | Do Instead |
|---------|---------------|-----------------|-------------|
| **Placing / replacing / canceling REAL orders live** (`new_order`, `replace_order`, `cancel_order`) | "Full surface coverage" implies exercising order mutation | Mutating endpoints move real money/positions even on remarkets sandbox; a bug or wrong account could create unwanted exposure or pollute the account. matriz order mutation is **explicitly high-risk-to-test-live** | Verify only order **read** paths live (status/history/actives/filled/all/byExecId). For mutation, verify request *construction* (params/serialization) and response *parsing* against **mocked** Primary responses. Flag mutation paths as "verified by mock only". |
| **Hammering endpoints to "stress test" rate limits** | Want to confirm 429 mapping fires live | Triggers real rate-limit/lockout; IOL re-auths via password grant each refresh (CONCERNS) so repeated runs risk **brute-force lockout** of the real account | Verify 429→`RateLimitError` with a **mocked** 429. Keep live runs to a single pass per endpoint; add a small inter-call delay; never loop. |
| **Logging or printing credentials/tokens in scripts or reports** | Easy debugging of auth issues | `.env` secrets and bearer tokens leaking into stdout/CI logs/`.planning` reports is a security incident (PROJECT constraint: never expose credentials) | Print only a redacted token prefix (existing `main_iol.py` does `token[:12]...`). Never log `_password`/`_user`/full token. Keep `.env` gitignored. |
| **Asserting on live market-data *values* (prices, quantities)** | Seems like a strong correctness check | Values are non-deterministic and market-hours dependent; the test is flaky and proves nothing about the client | Assert on **shape/type/presence**, not values. Snapshot the schema, not the numbers. |
| **Depending on market-hours-only data with no guard** | Run the same script anytime | Market data, active orders, fresh quotes return empty/stale outside trading hours → false "bug" reports | Treat empty-when-closed as a valid outcome; gate value-bearing assertions behind a market-open check or accept empty as pass. Pick endpoints (instrument lists, segments, historical) that work off-hours for the always-run path. |
| **Auto-fixing the ambito User-Agent by chasing live browser versions during the cycle** | UA looks stale (Chrome 124) | Turns verification into an open-ended maintenance chase; the real deliverable is *detecting* fragility, not tracking Chrome releases | Verify current UA works; if broken, document and bump to a current string + named constant (CONCERNS fix approach). Don't build UA auto-rotation. |
| **Introducing retries/backoff/logging "while we're in here"** | Live flakiness invites it | Out of scope (PROJECT: "Refactors... retries/backoff, structured logging — not the focus"); expands the cycle and risks masking real divergences | Note transient failures and re-run manually. Keep fixes scoped to genuine client/server divergences + their mocked regression tests. |

## Feature Dependencies

```
[Auth flow — first call]
    └──requires──> nothing (entry point; gates everything else per client)

[Token caching] ──requires──> [Auth flow]
[Token refresh] ──requires──> [Token caching]   (TTL math; mock-verify boundary)

[Happy-path every endpoint] ──requires──> [Auth flow]
        └──enables──> [Response shape/type conformance]
        └──enables──> [List vs object discrimination]
        └──enables──> [Empty/204 response handling]
        └──enables──> [Container-key envelope verification]

[Response shape/type conformance]
        └──enables──> [Type-discrepancy detection]   (iol, dict clients)
        └──enables──> [Silent field-drop detection]  (higyrus/matriz from_api)
        └──enables──> [Response drift / snapshot diffing]
        └──enables──> [Live payload → regression fixture capture]

[Error-path mapping] ──pairs-with──> [Application-level error detection]
        (HTTP status path AND payload-embedded status:ERROR / errors key)

[Sync vs async parity] ──requires──> [Happy-path every endpoint] run on BOTH surfaces
        (N/A for matriz — sync only)

[Live payload capture] ──feeds──> [Mocked regression test]  (closes finding→fix loop)

[Anti-bot probe] ──conflicts-with──> [Hammering endpoints]   (probe once, never loop)
[Order-read verification] ──replaces──> [Order-mutation live test]  (mutation = mock only)
```

### Dependency Notes

- **Everything per-client gates on auth.** Verify `login()` and lazy-auth-on-first-call before any endpoint sweep; a broken auth flow blocks the whole package's verification.
- **Shape conformance is the parent of all the differentiator checks.** You can't detect type drift, silent field drops, or snapshot drift without first capturing the real response shape — so the happy-path sweep must *retain* payloads, not just assert success.
- **Sync/async parity requires running the same sweep twice** (sync `client.py` + async `aio.py`) and comparing. This doubles the iol/higyrus/ambito surface and is where the known duplicated-logic divergence (higyrus async `drop_none`) will surface.
- **Live capture and mocked regression are two ends of one pipeline:** the real payload you capture during the live run becomes the fixture body for the regression test that locks in each fix.
- **Order-mutation (matriz) is intentionally excluded from live and replaced by mock-only verification of construction + parsing.** This is a conflict resolution: full surface coverage vs. do-no-harm — do-no-harm wins.

## MVP Definition

### Run This (cycle-complete minimum)

The verification cycle is not complete without these. Per client, sync + async (matriz sync only).

- [ ] **Auth: login() + lazy-auth-on-first-call** — gates everything; verifies the package's auth strategy against the live service.
- [ ] **Happy-path sweep of every in-scope public endpoint, retaining the raw payload** — the core deliverable.
- [ ] **Response shape/type conformance vs. client assumptions** — the headline risk; especially iol (raw dict) and from_api silent-default clients.
- [ ] **401 error-path live (bad creds) + payload-error live (bogus symbol/account)** — confirms the typed-exception mapping and matriz `status:ERROR` / higyrus `errors` handling.
- [ ] **Decimal/locale + date parsing on ambito (and number-typing on iol/matriz)** — cheap, high-signal for AR-locale corruption.
- [ ] **Empty/no-data path per list endpoint + ambito `NoDataError`** — confirms empty ≠ crash.
- [ ] **Sync vs async parity (iol/higyrus/ambito)** — surfaces duplicated-logic divergence.
- [ ] **Each confirmed bug → mocked regression test** following the existing `Regression: ... (issue #NNN)` convention.

### Add When Time Allows (high-value, not strictly blocking)

- [ ] **Type-discrepancy map for iol** — trigger: decide whether iol needs a model layer.
- [ ] **Silent field-drop diff for higyrus/matriz** — trigger: any model field that comes back default-valued on live data.
- [ ] **Schema snapshot baselines committed** — trigger: want repeatable drift detection on future re-runs.
- [ ] **Container-key envelope checks (KeyError-leak audit)** — trigger: any `["key"]` unwrap that isn't wrapped in the package exception hierarchy.
- [ ] **Ambito anti-bot probe (good UA passes / bad UA reproduces 403)** — trigger: confirm the spoof is load-bearing and current.

### Deliberately Defer / Out of Scope

- [ ] **403/429/5xx live triggering** — mock-only; live triggering risks lockout (anti-feature).
- [ ] **Order mutation live (new/replace/cancel)** — mock-only verification of construction+parsing; never live.
- [ ] **matriz async / WebSocket verification** — no `aio.py`; out of scope this cycle.
- [ ] **Token-refresh-after-23h live** — impossible in a single run; mock the TTL boundary instead.
- [ ] **Retries/backoff/logging additions** — tech debt, not this cycle.

## Feature Prioritization Matrix

| Check | Bug-Detection Value | Verification Cost | Priority |
|---------|------------|---------------------|----------|
| Auth flow + lazy auth | HIGH | LOW | P1 |
| Happy-path sweep (all endpoints, retain payload) | HIGH | MEDIUM | P1 |
| Response shape/type conformance | HIGH | HIGH | P1 |
| 401 + payload-error (status:ERROR / errors) live | HIGH | LOW | P1 |
| AR-decimal + date parsing (ambito/iol/matriz) | HIGH | LOW | P1 |
| Empty/no-data + ambito NoDataError | MEDIUM | LOW | P1 |
| Sync vs async parity (iol/higyrus/ambito) | HIGH | HIGH | P1 |
| Mocked regression per fix | HIGH | MEDIUM | P1 |
| Type-discrepancy map (iol dict) | HIGH | HIGH | P2 |
| Silent field-drop diff (higyrus/matriz) | HIGH | HIGH | P2 |
| Schema snapshot baselines | MEDIUM | MEDIUM | P2 |
| Container-key envelope audit | MEDIUM | MEDIUM | P2 |
| Ambito anti-bot probe | MEDIUM | MEDIUM | P2 |
| Token caching (no re-auth per call) | MEDIUM | MEDIUM | P2 |
| Token refresh / TTL boundary (mocked) | MEDIUM | MEDIUM | P3 |
| Empty-credential pre-flight | LOW | LOW | P3 |
| 403/429/5xx mapping (mocked) | MEDIUM | LOW | P3 |
| Order mutation construction (mocked, never live) | MEDIUM | MEDIUM | P3 |

**Priority key:** P1 = cycle is incomplete without it · P2 = high-value, run if time · P3 = mock-only or nice-to-have.

## Per-Client Verification Specifics

### iol-client — `dict` drift is the key risk
- **Surface (sync + async):** `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type`.
- **Headline risk:** returns raw `dict`/`list[dict]` with **zero validation** (`get_instruments` even returns bare `Any`). Field rename / number→string / re-nesting reaches callers as silently-wrong data.
- **Must do:** build observed field→type map from live payloads; verify `get_instruments_by_type` actually finds the `["titulos"]` envelope key; verify date-path format on `get_historical_quotes`; confirm number fields arrive as JSON numbers.
- **Watch:** sync uses password grant on every refresh (CONCERNS) — do NOT loop calls long enough to force repeated re-auth (lockout risk).

### higyrus-client — silent field drops are the key risk
- **Surface (sync + async):** `get_health`, `get_listado_cuentas`, `get_movimientos`, `get_posicion_valuada`, `get_posiciones`.
- **Headline risk:** `SafeModel.from_api` substitutes `""`/`0`/`0.0`/`[]`/`None` for missing/wrong-type fields and **ignores extra payload keys** — server renames vanish silently.
- **Must do:** diff raw `resp.json()` keys vs. each model's declared fields (both directions); verify the `assert isinstance(raw, list/dict)` holds on live data (it raises `AssertionError`, or silently passes under `-O` — candidate fix to a typed `HigyrusAPIError`); verify `errors`-key error parsing fires on a bad request; check async `_request` `drop_none` parity (known deviation).

### matriz-client — read-only live; mutation is mock-only
- **Surface (sync REST, read-only live):** `get_segments`, `get_all_instruments`, `get_instruments_details`, `get_instrument_detail`, `get_instruments_by_cfi`, `get_instruments_by_segment`, `get_market_data`, `get_trades`, order *reads* (`get_order_status`/`history`/`active`/`filled`/`all`/`by_exec_id`), risk `get_positions`/`get_detailed_positions`/`get_account_report`.
- **Headline risk:** `from_api` silent defaults (same as higyrus) + `["order"]`/`["orders"]`/`["marketData"]`/`["trades"]`/`["positions"]` envelope-key `KeyError` leaks not in the exception hierarchy.
- **Must do:** verify `status:"ERROR"` → `PrimaryAPIError` fires across several error conditions; verify each envelope key exists live; field-drop diff on models; market-data assertions on shape only (market-hours dependent).
- **HIGH-RISK — FLAG, do NOT run live:** `new_order`, `replace_order`, `cancel_order` mutate the (sandbox) account. Verify request construction + response parsing with **mocked** Primary payloads only. Note: Primary accepts order submit over **GET** (upstream quirk, not a bug) — preserve that in the mock.

### ambito-financiero-client — anti-bot fragility is the key risk
- **Surface (sync + async):** `get_dollar_banco_nacion(date)`.
- **Headline risk:** no auth; relies on a hardcoded Chrome-124 User-Agent (Ámbito 403s `python-httpx`). If Ámbito tightens bot detection the client "silently breaks with no clear error."
- **Must do:** verify a real call succeeds with current UA; verify `parse_ar_decimal` against the live `"1.415,00"` format (catch a server switch to plain `1415.00`); verify `NoDataError` fires for a no-quote date (the existing `main_ambito_financiero.py` already exercises this); verify response is the expected `list[list[str]]` shape; verify sync/async parity.
- **Probe (P2):** confirm a deliberately-wrong UA reproduces the 403 — proves the spoof is load-bearing. Do NOT loop (anti-bot may IP-ban).

## Sources

- `.planning/PROJECT.md` — cycle scope, surfaces per client, constraints (HIGH)
- `.planning/codebase/ARCHITECTURE.md` — auth strategies, request paths, error handling, SafeModel/from_api pattern (HIGH)
- `.planning/codebase/CONCERNS.md` — known gaps/bugs = prime verification targets (iol dict drift, higyrus async `drop_none` deviation, ambito UA fragility, asserts under `-O`, iol password-grant lockout risk) (HIGH)
- `.planning/codebase/INTEGRATIONS.md` — endpoints, auth mechanisms, env vars per service (HIGH)
- Direct source read: `iol_client/client.py`, `higyrus_client/models.py` + `client.py`, `matriz_client/client.py`, `ambito_financiero_client/client.py` + `_parsing.py`, root `main_*.py` (HIGH)

---
*Feature research for: live-API verification of Argentine financial HTTP client libraries*
*Researched: 2026-05-26*
