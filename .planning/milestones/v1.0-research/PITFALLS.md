# Pitfalls Research

**Domain:** Live-API verification of Python HTTP client libraries for Argentine financial services (iol-client, higyrus-client, matriz-client/Primary, ambito-financiero-client)
**Researched:** 2026-05-26
**Confidence:** HIGH (codebase-grounded + verified external facts on reMarkets sandbox and MATBA ROFEX market hours)

> Scope reminder: this milestone exercises the full public sync+async surface of four clients **against live APIs**, finds client-vs-service divergences, and fixes them with mocked regression tests. The vehicle is the root `main_*.py` scripts. Every pitfall below is specific to *verifying* against live financial services — not generic test advice.

---

## Critical Pitfalls

### Pitfall 1: Accidentally placing or canceling REAL orders during verification

**What goes wrong:**
`matriz-client` exposes `new_order`, `replace_order`, and `cancel_order` (`client.py` L244/285/298), all hitting Primary's `/rest/order/*` endpoints. "Exercising the full public surface" reads as "call every function" — including the order-entry mutations. If verification runs against a production Primary base URL (or, for IOL later, any future order endpoints), a verification script can submit a live order, replace it, or cancel a third party's order by `clOrdId`. Even on remarkets sandbox, blindly placing orders pollutes the simulated book and risk position, making other reads (`get_order_status`, positions, account report) non-deterministic for the rest of the run. The Primary order endpoints are invoked via **GET with query params** (`_get("/rest/order/newSingleOrder", ...)`), so they look deceptively like read calls — a reviewer skimming the script may not realize a GET is a mutation.

**Why it happens:**
- The thin-client design makes a destructive call syntactically identical to a read.
- "Full surface coverage" is interpreted literally, without classifying read vs. write.
- `matriz-client` defaults to `https://api.remarkets.primary.com.ar` (sandbox), which lulls one into treating all order calls as safe — but `PRIMARY_BASE_URL` can be overridden to prod via `.env`, and the same script then becomes destructive.

**How to avoid:**
- **Classify every public function as READ or WRITE before writing any verification code.** Mutations: `new_order`, `replace_order`, `cancel_order` (matriz). Everything else in the four clients is read-only (this is verifiable: iol/higyrus/ambito have no mutation endpoints).
- **Hard guardrail in `main_matriz.py`:** require an explicit opt-in env flag (e.g. `MATRIZ_ALLOW_ORDERS=1`) before any order mutation runs; default OFF. Without the flag, skip mutations and log "SKIPPED (write op, guard off)".
- **Assert sandbox before any mutation:** verify the resolved `matriz_client.client._base_url` contains `remarkets` and raise/abort otherwise. Never run order mutations against a non-remarkets host in this milestone.
- For order mutations on sandbox: place a far-from-market limit order (price well away from last trade, small qty), capture the response, then **immediately cancel by the returned `clOrdId`**, and only cancel IDs this script created — never cancel by an arbitrary/looked-up ID.
- Document in PROJECT scope that production order entry is explicitly out of scope for verification.

**Warning signs:**
- A `main_*.py` calls `new_order`/`cancel_order` with no surrounding guard or base-URL assertion.
- `PRIMARY_BASE_URL` in `.env` does not contain `remarkets`.
- `cancel_order` is called with a `clOrdId` not produced earlier in the same run.

**Phase to address:**
Verification-design / safety-harness phase, *before* any matriz live run. The order-mutation guardrail and read/write classification must land first.

---

### Pitfall 2: IOL password-grant brute-force lockout from repeated runs

**What goes wrong:**
IOL ignores the `refresh_token` and re-sends `grant_type=password` (username+password) on every token acquisition and every expiry (`iol-client/client.py` L85-108, `aio.py` L88-111). The access token TTL is only ~900 s (15 min). A long full-surface verification run, or several iterations during a fix-and-re-verify loop, repeatedly POSTs the real password to `/token`. IOL or an upstream WAF can interpret many password grants from one IP in a short window as a brute-force attempt and **lock the real trading account** — a far worse outcome than a failed test.

**Why it happens:**
- The client architecture forces a password grant on each refresh (known concern). Verification amplifies the call count: sync + async surfaces each trigger their own `login()` (independent module state), and re-running scripts during the fix loop multiplies it.
- 15-min TTL means even a single thorough run that takes >15 min re-authenticates mid-run.
- Developers assume auth is "free" and call `login()` redundantly or `configure()` (which resets the cached token, forcing re-login) more than necessary.

**How to avoid:**
- **Authenticate once per surface per run.** Call `login()` (or let the first call lazy-auth) exactly once for sync and once for async; do not call `configure()` repeatedly mid-run (it nulls `_token` and forces re-auth).
- **Keep IOL runs short and batched** so the full surface completes inside one 15-min token window; avoid tight re-run loops against IOL.
- **Add deliberate spacing / a small backoff between IOL runs**, not between every endpoint.
- Treat `IOLAuthError`/`IOLRateLimitError` as a STOP signal — abort the run immediately rather than retrying the password grant in a loop.
- Consider verifying the *refresh_token fix itself* (it is a known concern: store and use `grant_type=refresh_token`) as part of this milestone so future runs stop spamming the password grant.

**Warning signs:**
- More than a handful of `POST /token` calls in one run.
- `401/403` from `/token` after several attempts (early lockout signal).
- Verification script calls `configure()` inside a loop.

**Phase to address:**
IOL verification phase. The "auth once, fail fast, no retry-on-auth" rule belongs in the shared verification harness and is mandatory before the first IOL live run.

---

### Pitfall 3: Treating empty/absent live data as a client bug (market-hours & calendar non-determinism)

**What goes wrong:**
The real financial APIs only return meaningful data when the market is open. MATBA ROFEX trades roughly **10:00–17:30 ART, Mon–Fri**, closed on BYMA/Argentine holidays; IOL quotes and Ámbito FX series are likewise time- and calendar-dependent. Outside trading hours, on weekends, or on holidays, live endpoints legitimately return empty lists, stale snapshots, `null` prices, or zero-volume market data. A verification run that happens at 21:00 ART on a Saturday will see "empty" responses and either (a) flag the client as buggy when it is correct, or (b) the tolerant model layer silently fills zeros and the verifier records a false "pass". Worse, **sandbox (remarkets) runs 24x7 with simulated data**, so a check that passes against sandbox at midnight will not reproduce against the prod calendar — masking the asymmetry.

**Why it happens:**
- Verification is run whenever the developer is working, not aligned to ART market hours.
- The Argentine market calendar (Carnival, Día de la Memoria 24-mar, movable national holidays, US holidays affecting cross-listed data) is non-obvious and easy to forget.
- reMarkets always answers, hiding the "no data outside hours" behavior that prod exhibits.

**How to avoid:**
- **Record run context with every finding:** wall-clock time in `America/Argentina/Buenos_Aires`, day-of-week, and whether the market was open. A finding without this context is not actionable.
- **Distinguish "empty because closed" from "empty because broken."** An empty list / null price during a closed session is expected — only treat it as a discrepancy if the *shape* is wrong (e.g. a field the client requires is missing) or if the same call returns a malformed structure.
- **For prod-facing data (IOL, Ámbito), run at least one pass during ART market hours** so price-bearing fields are actually populated; do not draw conclusions about price parsing from a closed-session run.
- **Do not assert on specific data values** (prices, quantities) in live verification — only on response *shape*, *types*, and *parsing correctness*. Value assertions are inherently flaky against live markets.
- Maintain a tiny known-holiday awareness in the run log so closed-day runs are labeled.

**Warning signs:**
- A "discrepancy" report where the only issue is empty/null data, with no shape mismatch.
- Findings logged on a weekend/holiday/after-hours timestamp.
- Identical call returns data in one run and empty in another, with no client change.

**Phase to address:**
All live-verification phases. The run-context logging convention and the "shape-not-value" rule are harness-level and must precede the first run.

---

### Pitfall 4: Tolerant parsing silently swallowing real discrepancies (the false-pass trap)

**What goes wrong:**
`higyrus-client` uses `SafeModel.from_api` (`models.py`), which **never raises** on missing or wrong-type fields: `str`→`""`, `int`→`0`, `float`→`0.0`, `bool`→`False`, `list`→`[]`, nested model→empty instance. `matriz-client` models also use `from_api`. The entire point of this milestone is to detect client-vs-service divergence — but tolerant parsing is engineered to *hide exactly that*. If the live API renames a field, changes a type (e.g. `cantidad` arrives as a string `"−21936.48"` instead of float), or drops a key, `from_api` substitutes a safe default and returns a fully-formed object. A verifier that only checks "did it return a model without throwing?" gets a green light while the data is silently wrong. This is the single most likely way for this milestone to *appear* successful while missing the discrepancies it exists to find.

**Why it happens:**
- The success criterion "the call returned a typed object" is satisfied even when the payload is wrong, because tolerance is by design.
- Zero-valued defaults look like legitimate empty data (compounding Pitfall 3 — a closed-market zero and a parse-failure zero are indistinguishable at the model layer).
- The verifier trusts the model instead of the raw wire payload.

**How to avoid:**
- **Verify against the raw payload, not the parsed model.** Capture the raw JSON (`resp.json()`) for each endpoint and diff its keys/types against what the model expects (field names + declared type hints). Use `get_type_hints(Model)` to compare declared fields vs. actual wire keys.
- **Flag, per response:** (a) wire keys present that the model ignores (model is stale / incomplete), (b) model fields whose wire value is missing or whose type does not match the hint (would have been silently defaulted). These are the discrepancies the milestone must capture.
- **For higyrus specifically:** instrument or wrap `from_api` during verification to log every field that fell back to a default, so silent substitutions surface as findings rather than disappearing.
- **Do not let a non-raising `from_api` count as a pass.** A pass requires: no unexpected wire keys, no missing modeled keys, and types matching hints.
- Note the model docstrings already record sandbox-verified shape quirks (e.g. `cantidad` is float, dates are `dd/mm/yyyy` not ISO) — cross-check live prod against those notes; a mismatch there is a finding.

**Warning signs:**
- A higyrus/matriz endpoint "passes" but every numeric field is `0`/`0.0` and every string is `""`.
- Verification only catches exceptions and never inspects field contents.
- Raw payloads are never captured, so there is nothing to diff against.

**Phase to address:**
Higyrus and matriz verification phases. The raw-payload-diff technique is the core verification method for the model-bearing clients and must be the defined approach before those runs.

---

### Pitfall 5: Credential and account-data leakage into logs, output, and committed fixtures

**What goes wrong:**
Two leak vectors, both acute in this domain:
1. **Tokens/credentials in `main_*.py` output.** Credentials live in module globals (`_user`, `_password`, `_token`) and are trivially readable (`module._password`, `module._token`). A verification script that prints responses, prints the configured client state, or dumps an exception body can emit a live Bearer token / `X-Auth-Token` or even the password. The `IOLAuthError`/`PrimaryAPIError` constructors take `resp.text`, and auth-endpoint error bodies can echo request context.
2. **Real account data baked into regression fixtures.** Each fix must ship a mocked regression test. The natural workflow is "capture the live payload, paste it into the test." But higyrus `Cuenta`/`PosicionValuada`/`Movimiento` payloads contain **account numbers, CBUs, balances (`valuacion`), positions, holder names, addresses, related persons**. IOL/Primary order and position responses contain account identifiers and proprietary IDs. Committing a captured real payload into a fixture leaks PII/financial data into git history permanently.

**Why it happens:**
- Print-debugging is the fastest way to inspect live responses, and tokens ride along in headers/bodies.
- "Use a real captured payload as the fixture" feels like the most faithful regression test.
- No logging framework exists (all output is ad-hoc `print`), so there is no redaction layer.

**How to avoid:**
- **Never print tokens, passwords, or full auth responses.** Print only a redacted shape summary (key names + types), never values for sensitive fields. Add a tiny `redact()` helper used by every print in `main_*.py`.
- **Never print the configured credential globals.** If echoing config, mask (`IOL_USER=se***`).
- **Anonymize every captured payload before it becomes a fixture.** Replace account numbers, CBUs, names, addresses, balances, and IDs with synthetic but type-correct values. The fixture must preserve *shape and types* (the regression-relevant part), not real data.
- **Keep `.env` gitignored** (already the convention) and confirm no `.env` is staged.
- **Scan the diff before committing fixtures** for digits that look like account numbers/CBUs/amounts and for anything resembling a token.

**Warning signs:**
- `print(resp.json())` / `print(token)` / `print(client._password)` anywhere.
- A fixture JSON containing realistic CBUs, balances, or holder names.
- Exception messages printed verbatim from auth endpoints.

**Phase to address:**
Harness/safety phase (redaction helper + print discipline) up front; reinforced in every fix phase where regression fixtures are authored (anonymization gate before commit).

---

### Pitfall 6: Sandbox-vs-production shape asymmetry on matriz/Primary

**What goes wrong:**
`matriz-client` defaults to **remarkets** (sandbox). reMarkets is a hyper-realistic *simulation* that runs 24x7, but its responses can differ from production in field presence, instrument universe, value ranges, and the population of optional fields. Verifying solely against remarkets can (a) pass on a shape that prod actually emits differently, and (b) miss prod-only fields/errors — and the reverse if one later points at prod. Because remarkets always answers, it also hides the market-hours behavior prod shows (ties to Pitfall 3). Any "verified" conclusion is only valid for the environment it was run against, and that environment must be stated.

**Why it happens:**
- Sandbox is the safe default and 24x7 availability makes it the path of least resistance.
- The simulated environment is "hyper-realistic," so it is easy to assume parity with prod.
- The Primary application-level error contract (`"status": "ERROR"`) and edge cases may surface differently or not at all in sandbox.

**How to avoid:**
- **Label every matriz finding with the environment** (`remarkets` vs prod) — never an unlabeled "verified."
- **Scope this milestone's matriz verification to remarkets sandbox** (consistent with safety: it is the only environment where order mutations are acceptable). Explicitly note that prod-only shape divergences are *not* covered, so downstream planning knows the gap.
- **Exercise the Primary error path deliberately:** craft a call that triggers `"status": "ERROR"` (e.g. invalid instrument / bad params) to verify the client's `PrimaryAPIError` mapping, since happy-path sandbox data may never exercise it.
- Cross-reference model docstrings that say "Verified against sandbox on 2026-04-24" — those are sandbox claims; treat prod as unverified.

**Warning signs:**
- A matriz "verified" note with no environment label.
- The `"status": "ERROR"` branch is never exercised during the run.
- Assumptions that a sandbox-present field is guaranteed in prod.

**Phase to address:**
Matriz verification phase. Environment-labeling and the deliberate error-path probe are part of that phase's success criteria; the prod gap is recorded as an open question for the roadmap.

---

### Pitfall 7: Argentine-locale parsing errors masquerading as (or hiding) correctness

**What goes wrong:**
Argentine formatting uses **decimal comma and thousands dot** (`"1.415,00"` → 1415.00), **dates as `dd/mm/yyyy`** (and `dd/mm/yyyy HH:MM:SS`), and times in **`America/Argentina/Buenos_Aires` (UTC−3)**. `ambito-financiero-client._parsing.parse_ar_decimal` does `value.replace(".", "").replace(",", ".")` — correct for `"1.415,00"` but it will **silently corrupt** an input that already uses a dot-decimal (e.g. if the API ever returns `"1415.00"`, this yields `141500.0`) or an integer string. higyrus stores dates verbatim as `dd/mm/yyyy` strings (no parsing) — so any consumer that assumes ISO is wrong, but the *client* looks fine. A verifier who only checks "did it parse to a float" can miss a 100x error, and a `dd/mm` vs `mm/dd` confusion (e.g. `03/04` = 3 April, not 4 March) can pass for 12 days of the month and fail silently otherwise.

**Why it happens:**
- The naive `replace` parser has no validation and assumes the input is always Argentine-formatted.
- `dd/mm` and `mm/dd` look identical for day ≤ 12, so wrong interpretation passes most of the time.
- Timezone is implicit; comparing a live timestamp against `datetime.now()` (likely UTC or the runner's TZ) drifts by 3 hours.

**How to avoid:**
- **Verify the decimal parser against adversarial live values:** values ≥ 1000 (exercises the thousands dot), exactly one decimal place, and watch for any prod value lacking a comma — if `parse_ar_decimal` ever receives a dot-decimal it produces a 100x error; flag that as a discrepancy/bug to fix.
- **Sanity-check magnitudes** of parsed FX rates against an independent reference order-of-magnitude (not exact value) to catch the ×100 / ÷100 class of bug.
- **For dates, pick verification samples with day > 12** so `dd/mm` vs `mm/dd` ambiguity actually surfaces; confirm the client preserves/parses `dd/mm/yyyy` as documented.
- **Do all time comparisons in `America/Argentina/Buenos_Aires`** explicitly (zoneinfo), never in the runner's local/UTC time.

**Warning signs:**
- A parsed FX rate off by exactly 100×/1000×.
- Date fields where day and month are both ≤ 12 (ambiguity invisible).
- `parse_ar_decimal` receiving a value with no comma.

**Phase to address:**
Ámbito verification phase (decimal parser) and higyrus verification phase (date strings). Locale-aware sample selection is part of each phase's verification design.

---

## Technical Debt Patterns

Shortcuts that seem reasonable during verification but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Assert on live data *values* (specific prices/qty) | Looks like a strong check | Flaky forever; breaks every market move; false bug reports | Never — assert on shape/types only |
| Paste real captured payload straight into a fixture | Faithful regression | Permanent PII/financial-data leak in git history | Never — anonymize first |
| `print(resp.json())` for debugging | Fast inspection | Token/credential/account leak in logs/CI output | Only via a redaction helper |
| Verify matriz only on remarkets, label as "verified" | Safe + 24x7 | Prod shape divergences silently uncovered | OK if explicitly labeled "sandbox-only" + gap recorded |
| Trust `from_api` not raising = endpoint OK | Quick green | Silently swallows the exact divergences this milestone seeks | Never — diff raw payload vs model |
| Re-run IOL verification in a tight loop | Faster iteration | Password-grant spam → account lockout | Never — auth once, space runs |
| Leave sync `httpx.Client` instances unclosed across runs | No teardown code | Socket/FD leak in long multi-package runs; `aio` loop-binding errors | OK for a short single run; add cleanup for long runs |
| Fix logic in `client.py` only, not `aio.py` | Half the work | Divergence between sync/async (known: higyrus `drop_none` already diverges) | Never — mirror every fix to both |

---

## Integration Gotchas

Common mistakes when connecting to these specific external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| IOL `/token` | Re-authenticating per call / per `configure()`; retrying on 401 | Auth once per surface; fail fast on auth error; never loop the password grant |
| Primary `/rest/order/*` | Calling order mutations because "GET ≠ dangerous" | These GETs are writes; gate behind explicit flag + sandbox assertion |
| Primary getToken | Reading token from body | Token is returned in the `X-Auth-Token` **response header**, not the JSON body |
| Primary app errors | Only checking HTTP status | Primary returns HTTP 200 with `{"status":"ERROR"}`; verify that branch deliberately |
| Ámbito | Assuming the hardcoded Chrome UA will keep working | UA is a fragile anti-bot workaround (Chrome 124, 2024); a 403 means detection tightened, not a code bug |
| Ámbito | Assuming `python-httpx/...` UA works | It returns 403; verification must use the browser UA the client already sets |
| Higyrus | Treating a returned model as proof of correct data | Tolerant `from_api` defaults silently; diff raw payload vs declared hints |
| All sync clients | Leaving the module-level `httpx.Client` open across a long batch run | Add/use a `close()` (none exists today) or `atexit`; one pool per package per process |
| All async clients | Reusing cached `aio` `_client` across event loops | `await aio.aclose()` between loops; `configure()` recreates it |

---

## Performance / Reliability Traps

Patterns that work for a quick smoke test but fail across a full-surface, multi-run verification.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Looping endpoints with no spacing | 429s, `IOLRateLimitError`, throttling, possible IP ban | Sequential calls, small spacing, no concurrency storms; honor 429 as STOP | As soon as a full surface is hammered repeatedly |
| Run exceeds IOL's 15-min token window | Mid-run re-auth → extra password grants | Keep IOL runs short/batched; don't reset token mid-run | Long full-surface runs |
| Unclosed sync `httpx.Client` across many runs | FD/socket growth, eventual connection errors | Explicit close / context manager / `atexit` | Long-lived or repeated in-process runs |
| Clock skew vs token TTL (`time.time()`) | Fresh token treated as expired (NTP/VM resume) → spurious re-auth | Be aware; run on a clock-stable host; `max(0, now - ts)` if on snapshot-prone VMs | VM suspend/resume, NTP corrections during a run |
| Concurrent async tasks sharing one pool | Token thundering-herd on first call (mitigated by lock), pool contention | Don't blast high concurrency in verification; one sequential pass per surface | High-concurrency verification (unnecessary here) |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Printing tokens / `X-Auth-Token` / Bearer | Live session token leaks to logs/CI; account takeover window | Redaction helper; never print auth values |
| Printing `_password` / config globals | Real trading-account password in plaintext output | Mask credentials; never echo globals |
| Committing real payloads as fixtures | CBUs, balances, holder names, account IDs leak permanently into git | Anonymize to type-correct synthetic data before commit |
| Echoing auth error bodies verbatim | Auth endpoint responses may carry request context/identifiers | Log status + redacted summary, not raw body |
| Running order mutations against prod | Real money: unintended live orders/cancels | Sandbox-only assertion + explicit opt-in flag |
| Looping the IOL password grant | Brute-force detection → real account lockout | Auth once; fail-fast on auth errors |
| Staging a `.env` | Per-package real credentials committed | Confirm `.env` gitignored; check staged diff |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces for *this* milestone.

- [ ] **Endpoint "passes":** Often missing a raw-payload diff — verify field names + types against the model's `get_type_hints`, not just "no exception thrown".
- [ ] **Empty response handling:** Often missing market-context labeling — verify whether empty = closed-market (expected) vs broken (finding), with ART timestamp recorded.
- [ ] **Sync verified:** Often missing the async mirror — verify `aio.py` was exercised independently (separate module state) and any fix landed in both files.
- [ ] **Matriz "verified":** Often missing the environment label and the `"status":"ERROR"` path — verify it says "remarkets" and the error branch was exercised.
- [ ] **Regression fixture:** Often missing anonymization and the bug reference — verify no real account data and a `Regression: ... (issue #N)` docstring per existing convention.
- [ ] **Decimal/date parsing:** Often missing adversarial samples — verify ≥1000 values and day>12 dates were used.
- [ ] **Ámbito "works":** Often missing the fragility note — a pass today says nothing about tomorrow; record that a future 403 is anti-bot, not a regression.
- [ ] **Order mutation test:** Often missing cleanup — verify any sandbox order placed was canceled by its own returned `clOrdId`.

---

## Recovery Strategies

When pitfalls occur despite prevention.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Real order placed (matriz prod) | HIGH | Immediately cancel by returned `clOrdId`; verify via `get_order_status`; notify account owner; freeze prod runs |
| IOL account locked | HIGH | Stop all IOL runs; contact IOL support to unlock; implement refresh_token before resuming |
| Token/credential printed in committed output/CI | HIGH | Rotate the credential (change password / revoke token) immediately; scrub log; treat as compromised |
| Real payload committed as fixture | HIGH | Rewrite git history (filter-repo) before push, or rotate exposed account context; anonymize and recommit |
| False "pass" from tolerant parsing | MEDIUM | Re-run with raw-payload diff method; re-open the supposedly-verified endpoints |
| Findings logged without market context | LOW | Re-run during ART market hours; re-label; discard value-based "discrepancies" |
| Ámbito 403 mid-verification | LOW | Recognize as anti-bot tightening, not a bug; update UA constant; note fragility, don't "fix" parsing |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Destructive orders (P1) | Verification-harness / safety phase (before any matriz live run) | Read/write classification exists; order calls gated by flag + `remarkets` assertion; placed orders self-canceled |
| IOL lockout (P2) | IOL verification phase | Auth-once enforced; no retry-on-auth; runs spaced; `POST /token` count is low |
| Market-hours non-determinism (P3) | All live phases (convention set in harness phase) | Every finding carries ART timestamp + open/closed; shape-not-value asserts |
| Tolerant parsing false-pass (P4) | Higyrus + matriz phases | Raw payload diffed against model hints; defaulted fields logged as findings |
| Credential/data leakage (P5) | Harness phase + every fix phase | Redaction helper used; fixtures anonymized; staged diff scanned; `.env` not staged |
| Sandbox vs prod asymmetry (P6) | Matriz phase | Findings labeled `remarkets`; `"status":"ERROR"` path exercised; prod gap recorded |
| Locale parsing (P7) | Ámbito + higyrus phases | Adversarial decimal/date samples used; magnitude sanity-check; ART timezone for all time math |

---

## Sources

- Codebase map (authoritative for client internals): `.planning/codebase/CONCERNS.md`, `ARCHITECTURE.md`, `INTEGRATIONS.md`; source files `iol-client/client.py`, `matriz-client/client.py`, `higyrus-client/models.py`, `ambito-financiero-client/_parsing.py` — HIGH confidence (read directly).
- reMarkets sandbox is a 24x7 hyper-realistic simulation; getToken returns the token in the `X-Auth-Token` response header — [reMarkets](https://remarkets.primary.ventures/), [Primary API Hub](https://apihub.primary.com.ar/) — MEDIUM-HIGH confidence (official sources, corroborates codebase).
- MATBA ROFEX trading hours ~10:00–17:30 ART, Mon–Fri; BYMA/Argentine holiday calendar — [Matba-Rofex Horarios de Negociación](https://matbarofex.com.ar/horario_de_negociacion), [BYMA Calendario Bursátil](https://www.byma.com.ar/en/market/calendario-bursatil), [BYMA Market Hours & Holidays 2026 — TradingHours.com](https://www.tradinghours.com/markets/byma) — MEDIUM confidence (multiple sources agree).
- IOL OAuth2 password grant with ignored refresh_token, 900 s TTL — codebase + `.planning/codebase/CONCERNS.md` — HIGH confidence.

---
*Pitfalls research for: live-API verification of Argentine financial HTTP client libraries*
*Researched: 2026-05-26*
