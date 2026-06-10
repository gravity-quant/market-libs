# Project Research Summary

**Project:** market-libs — Live-API Verification Cycle
**Domain:** Live verification of Python HTTP client libraries against Argentine financial APIs
**Researched:** 2026-05-26
**Confidence:** HIGH (all four research files grounded in direct codebase reading; LOW only on undocumented Ambito wire format)

## Executive Summary

This milestone is a live-API verification cycle for four of the five client packages in the `market-libs` monorepo: `iol-client`, `higyrus-client`, `matriz-client` (sync REST only), and `ambito-financiero-client`. The goal is to exercise the full public sync+async surface of each client against real financial services, detect client-vs-service divergences, and close the loop immediately with a fix and a mocked regression test. No architectural refactors are in scope — only bug detection and the tests that lock in each fix.

The recommended approach is to extend the existing root `main_*.py` scripts into full-surface verification drivers, run them in ascending order of risk (ambito first, matriz last), and use a three-layer investigation stack: `vcrpy`+`pytest-recording` to capture real payloads, `genson`+`jsonschema` to infer and validate response shapes for untyped dict clients, and raw-payload diffing against model type hints for the `SafeModel`/`from_api` clients. All findings feed into hand-authored `pytest-httpx` regression tests following the existing codebase convention. Live tests are gated behind an opt-in `@pytest.mark.live` + `--live` flag so CI is never touched.

The key risks are: (1) `SafeModel.from_api` tolerance silently swallowing real divergences in higyrus and matriz — a false-pass trap requiring raw wire payload diffing against declared model fields, not just checking that no exception was raised; (2) IOL's password-grant-on-every-refresh being amplified by verification loops, risking account lockout; (3) accidental live order placement in matriz, which uses GET requests for mutations (deceptively read-like) and must be hard-gated behind an explicit env var; and (4) Argentine locale parsing (`"1.415,00"`) and market-hours non-determinism producing false positives if verification runs outside ART trading hours without context labeling.

## Key Findings

### Recommended Stack

The codebase already provides the permanent regression layer (`pytest-httpx` 0.36.2, `pytest-asyncio` 0.24+ with `asyncio_mode=auto`). The verification adds only dev/workspace dependencies that never enter any package's runtime closure. `vcrpy` 8.1.1 (the first version with a correct httpx body-handling fix) paired with `pytest-recording` 0.13.4 handles live capture; `genson` 1.3.0 infers JSON Schema from untyped dict payloads; `jsonschema` 4.26.0 validates and produces precise error paths; `pydantic` 2.13.4 is used only inside verification scripts to express the "contract the client assumes" and diff it against reality; `deepdiff` 8.x provides human-readable structural diffs; `anyio` 4.13.0 (already a transitive dep of httpx) enables a single parametrized test body to drive both the sync and async surfaces without duplication. The key principle: vcrpy/genson/jsonschema are transient investigation tools; `pytest-httpx` tests are the permanent deliverable. Do NOT introduce `respx` — it would fragment a codebase that is 100% `pytest-httpx`.

**Core technologies:**
- `vcrpy` 8.1.1: record real HTTP pairs as cassettes — only version with correct httpx body handling; async streaming caveat (issue #597) does not apply since all clients use non-streaming JSON
- `pytest-recording` 0.13.4: pytest integration for vcrpy (`@pytest.mark.vcr`, `--record-mode`, `--block-network`)
- `genson` 1.3.0 + `jsonschema` 4.26.0: infer schema from live dict payloads, validate with precise error paths — essential for iol-client which has no typed models
- `pydantic` 2.13.4: declare assumed endpoint shapes in verification scripts only; dev-only, never added to package runtime deps
- `deepdiff` 8.x: structural diff between client dict and raw payload; catches silent shape drift in iol
- `anyio` 4.13.0: unified sync/async parametrized test driver
- `@pytest.mark.live` + `--live` CLI flag: opt-in gating so live tests never run in CI; must be registered in root `conftest.py` (strict-markers is already on)

### Expected Features (Verification Checks)

**Must have (table stakes) — P1, cycle is incomplete without these:**
- Auth flow: `login()` + lazy-auth-on-first-call for each client (gates everything else per client)
- Happy-path sweep of every in-scope public endpoint, retaining the raw payload
- Response shape/type conformance vs. client assumptions (headline risk: iol raw dict; higyrus/matriz SafeModel silent defaults)
- 401 live (bad creds) + application-level error live (bogus symbol → `status:ERROR` / `errors` key)
- AR-decimal (`"1.415,00"`) and date format verification on ambito; number-type verification on iol/matriz
- Empty/no-data path per list endpoint + `ambito NoDataError`
- Sync vs async parity for iol, higyrus, ambito (surfaces known higyrus `drop_none` deviation)
- Mocked regression test per confirmed bug, following `Regression: ... (issue #NNN)` convention

**Should have (high-value, run when time allows) — P2:**
- Type-discrepancy map for iol (field→observed-type from live payload vs. what callers index into)
- Silent field-drop diff for higyrus/matriz (wire keys the model ignores; model fields the wire drops)
- Schema snapshot baselines committed (enables future drift detection on re-runs)
- Container-key envelope audit (`["titulos"]`, `["order"]`, `["marketData"]` — KeyError leak candidates)
- Ambito anti-bot probe (confirm good UA passes; deliberately-wrong UA reproduces 403)
- Token caching verification (auth endpoint hit only once across N calls per surface)

**Deliberately out of scope / defer:**
- 403/429/5xx live triggering — mock-only; live triggering risks lockout
- matriz order mutation (`new_order`, `replace_order`, `cancel_order`) live — mock-only for request construction and response parsing
- matriz async / WebSocket — no `aio.py`; explicitly excluded per PROJECT.md
- Token refresh after 23h TTL live — impossible in a single run; mock the TTL boundary
- Architectural refactors (typed models for iol, dedup of sync/async, retries/backoff, logging)

### Architecture Approach

The harness is a thin per-package driver pattern: one `main_<pkg>.py` per client, each importing exactly one package and exercising its full public surface (sync block, then async block via `asyncio.run()`). A root-level `_verify.py` helper (`check()`/`Findings`/`redact()`) provides the transcript/findings plumbing without creating any cross-package coupling — the packages themselves never import it. Findings go to `.planning/verification/<pkg>-findings.md` (committed, no secrets). Fixes land in `client.py` + `aio.py` (always paired). Regression tests land in the package's existing `tests/` directory following `TESTING.md` conventions. The boundary that matters most: drivers are disposable scaffolding; client fixes and regression tests are durable artifacts that must pass mypy strict + ruff + CI.

**Major components:**
1. **Verification drivers** (`main_iol.py`, `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py`) — exercise full public surface live; emit structured findings; include credential gate (skip cleanly when `.env` absent) and mutation gate (`VERIFY_MUTATING=1` for matriz order endpoints only with sandbox assertion)
2. **Findings records** (`.planning/verification/<pkg>-findings.md`) — per-run, per-discrepancy log: endpoint, discrepancy class (SHAPE / AUTH / ERROR-MAP / PARAM / SYNC-ASYNC-DRIFT / NO-DATA / ANTI-BOT), captured payload (anonymized), fix reference, regression test reference, status (OPEN → FIXED → TESTED)
3. **Client fixes** (`packages/<pkg>/src/.../client.py` + `aio.py`) — dual-surface paired edits; no cross-package deps; must pass existing CI
4. **Regression tests** (`packages/<pkg>/tests/test_client.py` + `test_async_client.py`) — `pytest-httpx` mocks using anonymized captured payload as fixture body; `Regression:` docstring with finding ID

**Suggested verification order (risk-ascending):** ambito (no auth, 1 fn) → iol (raw dict, highest shape risk) → higyrus (SafeModel tolerance, known async deviation) → matriz (largest surface, only destructive endpoints).

### Critical Pitfalls

1. **Tolerant parsing false-pass (higyrus/matriz)** — `SafeModel.from_api` never raises; missing/renamed wire fields silently become `""`/`0`/`0.0`. A "no exception" check is useless. Always diff raw `resp.json()` against model `get_type_hints()`: flag wire keys the model ignores AND model fields absent from wire. A pass requires both directions to match.

2. **Accidental live order placement (matriz)** — `new_order`/`replace_order`/`cancel_order` use GET requests, looking deceptively read-like. Hard gate with `VERIFY_MUTATING=1` env var; assert base URL contains `remarkets` before any mutation; cancel immediately using the same run's returned `clOrdId`. Never against production.

3. **IOL password-grant lockout** — IOL ignores the refresh token and POSTs the real password on every token acquisition. Sync + async surfaces each have independent module state, triggering separate `login()` calls; re-running during a fix loop multiplies this. Auth once per surface per run; never call `configure()` mid-loop; treat `IOLAuthError` / `IOLRateLimitError` as an immediate STOP signal, not a retry trigger.

4. **Market-hours non-determinism producing false findings** — Primary trades ~10:00–17:30 ART Mon–Fri; IOL and Ámbito are calendar-dependent. Empty lists and null prices outside trading hours are NOT bugs. Record ART wall-clock time and open/closed status with every finding; assert on shape/types only, never on data values. Run at least one pass during ART market hours for price-bearing endpoints.

5. **Credential and account-data leakage** — Bearer tokens and `X-Auth-Token` values ride in module globals and exception bodies; higyrus/iol payloads contain CBUs, balances, account numbers, holder names. Use a `redact()` helper in all `main_*.py` print calls; anonymize every payload before it becomes a regression fixture; scan the staged diff before committing.

6. **Sandbox-vs-production shape asymmetry (matriz)** — reMarkets runs 24x7 with simulated data; prod may have different field populations and error-path behavior. Label every matriz finding with the environment (`remarkets`). Record the prod gap as an explicit open question in the findings record.

7. **Argentine locale parsing errors masking as correctness** — `parse_ar_decimal` (`replace(".", "").replace(",", ".")`) silently corrupts a dot-decimal input by ×100. Verify with values ≥ 1000; sanity-check magnitude against an independent reference. Pick date samples with day > 12 to make `dd/mm` vs `mm/dd` ambiguity visible.

## Implications for Roadmap

Based on combined research, the recommended phase structure climbs the risk/complexity curve, validates the harness on the safest target first, and leaves the only destructive surface for last.

### Phase 1: Safety Harness and Verification Infrastructure

**Rationale:** Every subsequent phase depends on the harness being correct and safe. Pitfalls 1–5 all require conventions (redaction helper, print discipline, opt-in mutation gate, run-context logging, credential gating) to be in place before any live API is touched. Getting this wrong on a later phase is costly to recover from.

**Delivers:** Extended `main_*.py` scripts with credential gate and mutation gate (`VERIFY_MUTATING=1` + sandbox URL assertion for matriz); `_verify.py` helper with `check()`/`Findings`/`redact()`; `.planning/verification/` directory with per-package findings record template; `@pytest.mark.live` registered in root `conftest.py`; run-context timestamp convention (ART TZ, open/closed flag); dev-dependency additions (`vcrpy`, `pytest-recording`, `genson`, `jsonschema`, `pydantic`, `deepdiff`) added to root `pyproject.toml` dev group.

**Addresses:** Credential gate, mutation gate, run-context logging, opt-in `live` marker
**Avoids:** Pitfalls 1 (order mutation), 2 (IOL lockout — auth-once rule established), 3 (market-hours — context convention), 5 (credential leakage — redact() in place)

### Phase 2: Ambito Financiero Verification

**Rationale:** No authentication, one public function, sync + async, always available (historical data has no market-hours dependency). Validates the entire driver → finding → fix → regression-test loop end-to-end on the lowest-risk target. If the harness has a flaw it surfaces here before credentials are involved.

**Delivers:** `main_ambito_financiero.py` fully extended; `get_dollar_banco_nacion` verified sync + async; AR-decimal parser verified with values ≥ 1000 and adversarial edge cases; `NoDataError` path confirmed; anti-bot UA probe (P2 — confirm good UA passes, deliberately-wrong UA reproduces 403); any bugs fixed with mocked regression tests in `ambito-financiero-client/tests/`.

**Addresses:** AR-decimal + date parsing, empty/no-data path, sync/async parity, anti-bot fragility check
**Avoids:** Pitfall 7 (locale parsing — adversarial samples), Pitfall 3 (historical data is off-hours safe)
**Research flags:** Standard patterns — no deeper research needed. Ambito wire format is the only unknown; genson inference handles it. One-pass only against the live API (Pitfall 3: don't loop).

### Phase 3: IOL Client Verification

**Rationale:** Small surface (4 read functions), no mutation endpoints, but the highest silent-shape risk in the codebase — iol returns raw `dict`/`list[dict]` with zero validation. Doing IOL before higyrus/matriz builds genson+jsonschema workflow skill on an all-read surface before introducing model-tolerance complexity.

**Delivers:** `main_iol.py` fully extended; `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type` verified sync + async; genson-inferred schema baselines captured; `["titulos"]` envelope key confirmed present in live response; number fields confirmed as JSON numbers (not strings); 401-live error path confirmed with bad creds; sync/async parity confirmed; type-discrepancy map built (P2); bugs fixed with mocked regression tests in `iol-client/tests/`. Run completed within one 15-min token window.

**Addresses:** Response shape/type conformance (iol raw dict), auth flow + lazy-auth, 401 error path, sync/async parity, token caching
**Avoids:** Pitfall 2 (IOL lockout — auth once, fail-fast on auth error, no tight loops), Pitfall 3 (market-hours context labeling on every finding)
**Research flags:** IOL wire format is MEDIUM confidence — genson is the authority. If the refresh-token bug (CONCERNS) surfaces as a lockout risk during this phase, fixing it is an in-scope addendum.

### Phase 4: Higyrus Client Verification

**Rationale:** Medium surface (5 functions), Bearer auth (simpler than IOL OAuth), but introduces `SafeModel.from_api` tolerance — the false-pass trap. By this phase the raw-payload-diff technique is established from IOL. The known async `drop_none` deviation (higyrus CONCERNS) is a guaranteed sync/async parity finding.

**Delivers:** `main_higyrus.py` fully extended; all 5 public read functions verified sync + async; raw wire payload diffed against each model's `get_type_hints()` in both directions; `errors`-key error path confirmed on a bad request; `assert isinstance(raw, list/dict)` behavior noted and flagged as a candidate fix (bare `AssertionError` is not in the exception hierarchy); known `drop_none` async deviation confirmed or denied; account data in fixtures anonymized before commit; bugs fixed with mocked regression tests in `higyrus-client/tests/`.

**Addresses:** Silent field-drop diff (SafeModel), sync/async parity (known drop_none deviation), empty/no-data paths, error-path mapping
**Avoids:** Pitfall 4 (false-pass from SafeModel — raw-payload diff is mandatory, not optional), Pitfall 5 (CBUs/balances/holder names in fixtures must be anonymized)
**Research flags:** Standard technique (raw-payload diff against get_type_hints). SafeModel pattern is documented in the codebase. No external research needed.

### Phase 5: Matriz Client Verification

**Rationale:** Largest surface (~17 read functions + 3 order mutations), sync-only (no async pairing), the only destructive surface. Doing it last means: the harness is proven on three other clients; the mutation gate is battle-tested; the developer has maximum familiarity with the findings workflow before touching the highest-risk surface.

**Delivers:** `main_matriz.py` fully extended with read-only surface and gated mutation block; all read-only endpoints verified against remarkets; `from_api` silent field-drop audit (both directions — same technique as higyrus); `"status":"ERROR"` → `PrimaryAPIError` path exercised across multiple distinct error conditions (bogus symbol, invalid account, malformed param); each envelope key (`["order"]`, `["orders"]`, `["marketData"]`, `["trades"]`, `["positions"]`) confirmed present; order mutation (`new_order`/`replace_order`/`cancel_order`) verified by mock only (request construction + response parsing, including the GET-as-write quirk); bugs fixed with mocked regression tests in `matriz-client/tests/`; every finding labeled `remarkets`; prod gap recorded as explicit open question.

**Addresses:** Silent field-drop diff (from_api), status:ERROR envelope coverage, container-key envelope audit, order mutation mock verification, sandbox/prod asymmetry labeling
**Avoids:** Pitfall 1 (accidental live order placement — hard gated + sandbox assertion), Pitfall 4 (false-pass from from_api), Pitfall 6 (sandbox/prod gap explicitly labeled)
**Research flags:** Primary `"status":"ERROR"` error contract must be exercised deliberately — do not assume happy-path sandbox data will trigger it. The prod vs remarkets shape gap is unresolved; record it as an open roadmap question.

### Phase Ordering Rationale

- **Phase 1 (Harness) before everything:** credential gating, mutation gating, redaction, and run-context conventions apply to all four clients; they must be in place before any live call
- **Ambito first:** no auth, no market-hours risk for historical data, 1 function — validates the full loop (driver → finding → fix → regression) at minimum cost
- **IOL second:** highest shape risk (raw dict, no models), all-read surface — establishes the genson/jsonschema schema-inference workflow before model complexity
- **Higyrus third:** introduces SafeModel tolerance (false-pass risk) and a known async deviation — applies raw-payload-diff technique from IOL
- **Matriz last:** largest surface, only destructive endpoints, sandbox-only scope — maximum caution after the harness is proven on three clients

### Research Flags

Phases needing careful execution technique (not additional external research):
- **Phase 3 (IOL):** Wire format is MEDIUM confidence; genson inference from the live run is the only authority. IOL sandbox (`api-sandbox.invertironline.com`) can be used for read-only quote endpoints to reduce exposure; prod is safe for read-only but must not be looped.
- **Phase 5 (Matriz):** Primary `status:ERROR` error-path coverage must be deliberate (not incidental). Prod vs remarkets shape gap is unresolved and must be explicitly recorded as an open question for future milestones.

Phases with standard patterns:
- **Phase 2 (Ambito):** technique is straightforward; the only unknown is the Ambito wire format, which genson handles automatically
- **Phase 4 (Higyrus):** raw-payload-diff technique is established by Phase 3; SafeModel internals are documented in the codebase map

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All tools confirmed against PyPI on 2026-05-26; version compatibility verified; no conflicts with existing repo stack (httpx, pytest, pytest-asyncio, ruff, mypy strict) |
| Features | HIGH | Derived from direct source reading of all four client packages, CONCERNS.md, INTEGRATIONS.md, and PROJECT.md; verification check list corresponds to actual code paths |
| Architecture | HIGH | Per-package driver is the sanctioned vehicle per PROJECT.md Key Decision; structure derived from STRUCTURE.md, TESTING.md, and ARCHITECTURE.md; component boundaries are unambiguous |
| Pitfalls | HIGH (client internals) / MEDIUM (external services) | Client internals (SafeModel tolerance, IOL password grant, AR-locale parsing) verified from source; market hours verified from official MATBA ROFEX/BYMA sources; Ambito wire format and Primary prod-vs-sandbox shapes are MEDIUM — only knowable by running the verification |

**Overall confidence:** HIGH for the verification approach, tool choices, and phase structure. MEDIUM for the exact wire shapes of gated/undocumented APIs (IOL field names, Primary prod shapes, Ambito response schema) — which is the motivation for this cycle.

### Gaps to Address

- **IOL exact wire format:** No public field-level schema for `Cotizacion` and related payloads — genson inference during the live run is the only authority. Treat any divergence as a real finding, not a stale-docs issue.
- **Ambito response schema:** Completely undocumented; field names are known only from the client source and third-party scrapers. The live run is the spec.
- **Primary prod vs remarkets shape differences:** This milestone verifies remarkets only (safety constraint). Prod-only field variations are an explicit open gap; record in the matriz findings record for future milestone planning.
- **IOL token refresh fix scope:** The known `refresh_token` issue (IOL ignores it, always uses password grant) is a CONCERNS item. If the IOL verification phase reveals lockout risk is material, fixing the refresh-token flow is a valid in-scope fix for that phase — it is a client bug, not an architectural change.

## Sources

### Primary (HIGH confidence)
- `.planning/codebase/ARCHITECTURE.md` — client auth strategies, request paths, dual sync/async, SafeModel/from_api pattern
- `.planning/codebase/CONCERNS.md` — known gaps and bugs: iol dict drift, higyrus async `drop_none`, ambito UA fragility, assert-under-`-O`, IOL password-grant lockout risk
- `.planning/codebase/INTEGRATIONS.md` — endpoints, auth mechanisms, env vars, response shapes per service
- `.planning/codebase/TESTING.md` — pytest-httpx conventions, configure+monkeypatch fixtures, `Regression:` docstring convention
- `.planning/codebase/STRUCTURE.md` — monorepo layout, where `main_*.py` and tests live
- Direct source read of all four client packages (`client.py`, `aio.py`, `models.py`, `_parsing.py`, `__init__.py`)
- PyPI version checks 2026-05-26: vcrpy 8.1.1, pytest-recording 0.13.4, pydantic 2.13.4, jsonschema 4.26.0, genson 1.3.0, anyio 4.13.0, pytest-httpx 0.36.2, deepdiff 8.x

### Secondary (MEDIUM confidence)
- `invertironline.com/documentacion-api`, `api-sandbox.invertironline.com` — IOL v2 OAuth2 auth, 15-min token TTL, sandbox existence; field-level payload schema is gated
- `github.com/matbarofex/pyRofex` README — reMarkets sandbox vs LIVE, function signatures, dict return convention, `status:ERROR` pattern
- reMarkets official site, Primary API Hub — sandbox 24x7 hyper-realistic simulation, `X-Auth-Token` in response header (not body)
- Matba-Rofex Horarios de Negociación, BYMA Calendario Bursátil, TradingHours.com BYMA — trading hours ~10:00–17:30 ART Mon–Fri, Argentine holiday calendar

### Tertiary (LOW confidence)
- `mercados.ambito.com` — no public API documentation found (verified negative); field names known only from client source + third-party scrapers. Live capture is the only authoritative spec.
- Third-party aggregators (dolarapi, esjs-dolar-api) — confirm Ambito returns JSON arrays with buy/sell values; field names not authoritatively documented

---
*Research completed: 2026-05-26*
*Ready for roadmap: yes*
