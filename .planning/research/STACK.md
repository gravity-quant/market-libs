# Stack Research

**Domain:** Live-API verification of Python HTTP client libraries (sync `httpx.Client` + async `httpx.AsyncClient`) against third-party financial APIs, with response-shape/behavior discrepancy detection and mocked regression tests.
**Researched:** 2026-05-26
**Confidence:** HIGH for tooling choices; MEDIUM/LOW for real-API surface specifics (financial APIs are gated or undocumented — see "Real API Surfaces" section and confidence flags).

> **Scope note:** This file recommends the stack for *doing the verification*. It deliberately does **not** re-derive the libraries the clients are already built on (httpx, python-dotenv, websocket-client) — those are documented in `.planning/codebase/STACK.md`. Everything below is additive and must coexist with: Python 3.12+, uv workspace, httpx >=0.27, pytest 8.3+, pytest-httpx 0.36+, pytest-asyncio 0.24+ (`asyncio_mode = "auto"`), ruff, mypy strict.

---

## TL;DR — Prescriptive Summary

1. **Keep `pytest-httpx` for all regression fixtures.** It is already the repo standard and every existing test uses it. Do **not** introduce `respx` — it solves the same problem and would split the codebase's mocking idiom for zero benefit.
2. **Record live responses with `vcrpy` (8.1.1) + `pytest-recording` (0.13.4)** during the verification runs, *as a capture mechanism only*. The recorded cassettes are the raw material from which you hand-author the minimal `pytest-httpx` regression tests. Do **not** ship VCR cassettes as the permanent regression suite — convert findings to focused `pytest-httpx` tests that match the existing TESTING.md conventions.
3. **Detect shape discrepancies with `genson` (1.3.0) + `jsonschema` (4.26.0)**, not pydantic. `genson` infers a JSON Schema from the live payload; `jsonschema` validates subsequent payloads against it and against any schema you assert the client *assumes*. This is the right tool for `iol-client`, which returns raw `dict` with no typed models — there is no model to validate against, so you validate against an inferred/asserted schema instead.
4. **Use `pydantic` (2.13.4) tactically and only inside the verification scripts** (`main_*.py`) to declare "what the client documents/assumes this endpoint returns" and get a precise diff when reality diverges. It is **not** added to any package's runtime dependencies (that would be an architectural change, explicitly out of scope per PROJECT.md).
5. **Exercise sync + async with one parametrized driver** using a thin adapter + `pytest.mark.parametrize(["sync","async"])` and `anyio` (4.13.0) to run the async branch. This avoids the duplication the codebase already suffers from in `client.py`/`aio.py`.
6. **Gate live tests behind an opt-in `live` marker + `--live` CLI flag** so the existing CI (mock-only) is never touched. Live verification is run manually, on demand, with real `.env` credentials.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `vcrpy` | 8.1.1 | Record real HTTP request/response pairs from the live verification runs into cassettes (YAML/JSON) | Standard Python "record & replay" tool; 8.x specifically fixed httpx binary-body handling. Lets you capture exact real-service payloads once, then mine them for regression fixtures and schema baselines without hammering live APIs repeatedly. Supports **both** `httpx.Client` and `httpx.AsyncClient` via its httpx stub. |
| `pytest-recording` | 0.13.4 | pytest integration for vcrpy: `@pytest.mark.vcr`, `--record-mode`, per-test cassette dirs, `--block-network` | Cleaner than raw `vcr.use_cassette` decorators; gives a `--record-mode=once/none/rewrite` switch so the *same* test records on first live run and replays offline thereafter. Adds `--block-network` to guarantee no accidental live calls in replay mode. |
| `genson` | 1.3.0 | Infer a JSON Schema from a live response payload (the "what the service actually returns" baseline) | The verification's hardest target is `iol-client`'s raw-`dict` returns. There is no typed model to compare against, so the only objective baseline is a schema *derived from real data*. `genson` builds that schema automatically and can merge multiple samples (e.g. several symbols / market days) into one tolerant schema. |
| `jsonschema` | 4.26.0 | Validate every subsequent live payload (and the client's assumed shape) against the inferred/asserted schema; report exactly which path diverged | Reference implementation of JSON Schema for Python, draft 2020-12 support. Produces precise error paths (`$.cotizacion.puntas[0].precioCompra`) — ideal for a discrepancy report. Pairs naturally with `genson` (genson emits schemas jsonschema consumes). |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | 2.13.4 | Declare the *expected/assumed* response shape for an endpoint in the verification script and diff it against the live payload with rich error locations | Use in `main_*.py` only, for endpoints where you can write down the contract the client implicitly assumes (field names, types, nullability). Best for `matriz-client` and `higyrus-client` which already have `from_api` models — Pydantic models there double as an executable spec of those models' assumptions. **Do not** add to any package's `pyproject.toml` runtime deps. |
| `anyio` | 4.13.0 | Run the async branch of a parametrized sync/async test from a single test body | Already a transitive dep of httpx. Use `anyio.from_thread`/`anyio.run` or the `@pytest.mark.anyio` plugin to invoke `aio.*` coroutines inside a parametrized test so one test function covers both surfaces. The repo's `asyncio_mode = "auto"` also already supports plain `async def test_*`, so anyio is only needed for the *unified* sync+async driver. |
| `deepdiff` | 8.x (latest) | Structural diff between the client's returned `dict` and the raw payload, or between two recorded cassettes across runs | Optional but high-value for the discrepancy report: produces human-readable "values_changed / dictionary_item_added / type_changes" output. Useful for spotting silent shape drift in `iol-client` (raw dict) and detecting when a live response no longer matches a committed cassette. |
| `pytest-httpx` | 0.36.2 | The permanent regression-test mocking layer (already in repo) | Already the standard. Every fix lands with a `pytest-httpx` regression test, following `.planning/codebase/TESTING.md` exactly (full `url=` with query string, `match_headers`, `httpx_mock.get_requests()` inspection). No change — listed here to make explicit that it is the *destination* format for findings. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest `live` marker + `--live` flag | Opt-in gating so live tests never run in CI | Register `live: requires real third-party API credentials/network` in root `[tool.pytest.ini_options] markers`. Add `pytest_addoption(--live)` + `pytest_collection_modifyitems` in a **root** `conftest.py` to skip `@pytest.mark.live` unless `--live` is passed. `--strict-markers` is already on, so the marker must be registered or collection fails (good — prevents typos). |
| `--record-mode` (pytest-recording) | Controls record vs replay of cassettes | `--record-mode=once` for first live capture; `--record-mode=none` (default in CI/replay) to forbid new recordings; `--record-mode=rewrite` to refresh a stale cassette. |
| vcrpy `filter_headers` / `filter_query_parameters` / `before_record_response` | Scrub credentials out of cassettes before they touch disk | **Mandatory** given PROJECT.md's "never commit `.env` / never expose credentials" constraint. Filter `authorization`, `x-auth-token`, `x-username`, `x-password`, and IOL `/token` request bodies (`password`, `username`). Verify each cassette is clean before committing. |
| Discrepancy report (`.planning/` markdown) | Capture findings before fixing | One row per discrepancy: endpoint, surface (sync/async), client-assumed shape, live-observed shape, jsonschema/deepdiff evidence, severity, fix + regression-test reference. Feeds the "report → fix → mocked regression test" loop. |

---

## Installation

These are **dev/workspace dependencies only** — add to the root `pyproject.toml` `[dependency-groups] dev` (or `[tool.uv] dev-dependencies`), never to a package's runtime deps.

```bash
# Recording + replay of live responses
uv add --dev vcrpy pytest-recording

# Schema inference + validation (discrepancy detection for raw-dict clients)
uv add --dev genson jsonschema

# Expected-shape specs in verification scripts + structural diffing
uv add --dev pydantic deepdiff

# anyio is already present (httpx transitive dep); pin explicitly if you want the unified driver
uv add --dev anyio
```

Already present (no action): `httpx`, `pytest`, `pytest-httpx`, `pytest-asyncio`, `pytest-cov`, `python-dotenv`.

---

## How the Pieces Fit Together (verification workflow)

```
                       LIVE RUN (manual, real .env, opt-in --live)
  main_*.py / live test ──httpx──> real API
        │                            │
        │   pytest-recording + vcrpy │  records request+response
        ▼                            ▼
  client returns dict/model     cassette (.yaml, creds scrubbed)
        │                            │
        │ genson infers schema ◄─────┘  (one or many samples merged)
        ▼
  jsonschema.validate(live_payload, inferred_or_assumed_schema)
  + deepdiff(client_dict, raw_payload)
  + pydantic.model_validate(raw_payload)   # where a model spec exists
        │
        ▼
  DISCREPANCY REPORT  (endpoint, sync/async, assumed vs observed, evidence)
        │
        ▼ fix client.py AND aio.py (mirror the fix — known duplication)
        ▼
  REGRESSION TEST  (pytest-httpx, mock the real payload slice that broke,
                    docstring references the finding, e.g. issue #NN)
```

Key principle: **vcrpy/genson/jsonschema are the *investigation* layer (transient, run on demand). pytest-httpx is the *permanent* layer (committed, runs in CI).** Cassettes are scaffolding; the hand-authored `pytest-httpx` test is the deliverable.

### Exercising sync + async with minimal duplication

The codebase duplicates logic across `client.py` and `aio.py`, so both surfaces can diverge independently — verifying both is non-negotiable (PROJECT.md). To avoid writing every check twice, wrap each surface in a uniform callable and parametrize:

```python
# Conceptual — one test body, both surfaces.
import anyio
import pytest

@pytest.mark.live
@pytest.mark.parametrize("surface", ["sync", "async"])
def test_get_quote_shape(surface: str) -> None:
    if surface == "sync":
        payload = iol_client.get_quote("GGAL")
    else:
        payload = anyio.run(aio.get_quote, "GGAL")
    jsonschema.validate(payload, QUOTE_SCHEMA)   # genson-inferred or asserted
```

`anyio.run(...)` lets a single sync-style parametrized test drive the async coroutine without a second `async def`. For pure-async-only tests the repo's existing `asyncio_mode = "auto"` plain `async def test_*` style still works — use the unified driver specifically for the shape/discrepancy checks that must be identical across both surfaces.

---

## Real API Surfaces (verified facts vs assumptions)

> Distinguishing verified facts from assumptions per the quality gate. Financial APIs here are either **credential-gated** (IOL, Primary, Higyrus) or **undocumented internal** (Ámbito), so much of the response shape is only knowable by running the live verification — which is precisely this milestone's job.

### IOL — Invertir Online API v2 — MEDIUM confidence on surface

- **Verified:** Public API exists; interactive docs at `api.invertironline.com` and a developer portal at `developers.invertironline.com`. Auth is OAuth2-style bearer token valid **15 minutes** with a refresh token (matches the client's 900 s + 60 s-early-refresh logic). Source: invertironline.com/documentacion-api, invertironline.com/api.
- **Verified (new fact useful for this milestone):** A **sandbox** exists at `api-sandbox.invertironline.com` — "you can use a sandbox testing environment before operating in a real environment." This lets you exercise order-adjacent surfaces safely; for read-only quote/instrument endpoints (the client's actual surface) the live prod environment is read-only and safe. Consider pointing `IOL_BASE_URL` at the sandbox where possible.
- **Verified:** API covers real-time and historical quotation series for acciones, bonos, opciones, cauciones, futuros, monedas, cheques — consistent with the client's `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type`.
- **Assumption (must verify live):** Exact JSON field names/types of the `Cotizacion` payload. Public search did not expose the field list; the client returns the raw dict untyped, so **the inferred genson schema from the live run is the only authoritative shape.** This is the single highest-value discrepancy target.
- **Caveat:** "All actions impact the REAL environment" and the API is BETA with "potential endpoint modifications" — endpoints may have drifted since the client was written. Treat any divergence as a real finding, not a client bug, until confirmed.

### MATBA ROFEX / Primary API (remarkets sandbox) — MEDIUM confidence

- **Verified:** Official reference implementation is `pyRofex` (matbarofex/pyRofex on GitHub). Free **reMarkets sandbox** account at the Remarket site; LIVE requires emailing `mpi@primary.com.ar`. The client's default `https://api.remarkets.primary.com.ar` is the sandbox — correct for safe verification including order placement.
- **Verified:** pyRofex exposes `get_segments`, `get_all_instruments`, `get_instruments` (by CFI/segment), `get_market_data`, order routing — matching the client's REST endpoint list in INTEGRATIONS.md.
- **Verified (behavioral):** "All functions return a dict of the JSON response." The client's check for `"status": "ERROR"` in the payload aligns with Primary's documented pattern of returning a `status` field rather than relying solely on HTTP status — **verify the exact error envelope live**, as this is a known client behavior to confirm.
- **Assumption (must verify live):** Exact market-data and instrument field shapes. Detailed schemas live behind `clientes.primary.com.ar/docs/`, the sandbox apidoc (`assets/apidoc/trading/index.html`), and Postman collections — not fully scrapeable here. The remarkets sandbox itself is the authoritative source; capture with vcrpy.
- **Scope reminder:** Only the **sync REST** surface is in scope (no `aio.py`; WebSocket excluded per PROJECT.md).

### Ámbito Financiero — LOW confidence on surface (no public docs)

- **Verified (negative):** There is **no public API documentation** for `mercados.ambito.com`. It is an undocumented internal endpoint that backs the ambito.com historical-quote pages. Third-party aggregators (e.g. dolarapi / esjs-dolar-api, Castrogiovanni20/api-dolar-argentina) scrape it, confirming it returns JSON arrays of historical quotes with buy/sell ("compra"/"venta") values — but field names are not authoritatively documented anywhere public.
- **Verified (from the client itself, per INTEGRATIONS.md):** Endpoint path `/dolarnacion/historico-general/{from}/{to}`; **no auth**; **requires a browser `User-Agent`** (the API returns 403 on `python-httpx/...`). This UA dependency is fragile against anti-bot changes — flag any 403 during verification as a potential breakage, not a client bug.
- **Assumption (must verify live):** Exact field names (`fecha`, `compra`, `venta`, `valor`, `variacion`?) and date format. genson-infer from the live response; the client's parsing assumptions are the thing under test.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `pytest-httpx` (regression) | `respx` | If the repo had no existing mocking convention. respx has nicer route/pattern matching and auto-asserts routes were called, but adopting it would fragment a codebase that is 100% pytest-httpx. Not worth it here. |
| `vcrpy` + `pytest-recording` (capture) | `respx` + manual capture; `pytest-vcr` | `pytest-vcr` is older/less maintained than `pytest-recording`. respx can replay recorded data but isn't a recorder. vcrpy+pytest-recording is the current standard record/replay combo. |
| `genson` + `jsonschema` (raw-dict shape detection) | `pydantic` alone | Use pydantic alone when an endpoint has a *known, stable* contract you can hand-write. For `iol-client`'s untyped dicts where the contract is unknown, you need schema *inference* first — pydantic can't infer a model from data without extra codegen (`datamodel-code-generator`). |
| `pydantic` (expected-shape spec in scripts) | `typeguard` | `typeguard` runtime-checks values against type hints — useful if you already had `TypedDict`/dataclass hints for IOL responses (you don't; it returns bare dict). pydantic gives richer validation + error paths and the repo author already uses dataclass `from_api` models elsewhere, so pydantic is the closer mental model. Reach for typeguard only if you want to validate against existing `from_api` dataclasses without rewriting them. |
| `anyio.run` unified driver | Two separate `async def`/`def` tests | When a behavior genuinely differs between surfaces (rare), write them separately. For identical shape/contract checks, the unified driver halves the code and guarantees both surfaces are held to the same assertion. |
| `genson` | `datamodel-code-generator` | Use `datamodel-code-generator` if you decide to *generate typed models* for IOL from the inferred schema (a possible follow-up, but that is an architectural change — out of scope this milestone). genson stops at the schema, which is all verification needs. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `respx` | Duplicates `pytest-httpx` (already the repo standard for httpx mocking); introducing it fragments the test idiom for no functional gain. | Keep `pytest-httpx` 0.36.2. |
| `requests` / `responses` / `requests-mock` | The clients use `httpx`, not `requests`. `responses` cannot intercept httpx traffic. | `pytest-httpx` (mock), `vcrpy` (record — works with httpx). |
| Adding `pydantic` to any package's **runtime** dependencies | PROJECT.md explicitly excludes architectural refactors (typed models, dedup) this milestone. Runtime pydantic would change the public API and shipped wheels. | Use pydantic **only** inside `main_*.py` / dev test code as an executable spec. |
| Committing VCR cassettes as the permanent test suite | Cassettes are bulky, can leak credentials if scrubbing is imperfect, and drift silently. The repo's regression convention is focused `pytest-httpx` tests with bug references. | Convert each finding to a minimal hand-authored `pytest-httpx` regression test per TESTING.md. Treat cassettes as transient scaffolding (gitignore them, or keep a curated few only if genuinely needed). |
| `vcrpy < 8.0` for httpx | Versions 6.0.2/7.x had documented httpx issues (UnicodeDecodeError on playback, binary-body corruption). 8.x fixed httpx body handling. | `vcrpy >= 8.1.1`. Note: async httpx *streaming* still has a known rough edge (issue #597), but the clients here use non-streaming JSON requests, so this does not apply. |
| `pytest-vcr` (the older plugin) | Less maintained; `pytest-recording` is the actively maintained successor with better record-mode controls and `--block-network`. | `pytest-recording` 0.13.4. |
| Running live tests in CI | Live APIs are credential-gated, rate-limited, and market-hours/data dependent (PROJECT.md constraint). CI must stay deterministic and offline. | Opt-in `@pytest.mark.live` + `--live` flag; CI runs `pytest` (no `--live`) and skips them. |
| Putting real credentials in cassettes or reports | Hard security constraint (PROJECT.md). | vcrpy `filter_headers`/`filter_post_data_parameters`/`before_record_response`; never log tokens. |

---

## Stack Patterns by Variant

**If the client returns raw, untyped `dict` (iol-client):**
- Use `genson` to infer a schema from one-or-many live samples, then `jsonschema.validate` every payload + `deepdiff` between the client's dict and the raw httpx response.
- Because there is no model, the *only* assertion of "correctness" is "does the live shape match what the client's downstream code indexes into?" — so also grep the client for the dict keys it reads and assert those keys exist in the live schema.

**If the client has `from_api` / `SafeModel` parsing (higyrus, matriz):**
- Write a `pydantic` model in the verification script mirroring what `from_api` assumes, then `model_validate(live_payload)`. A validation error = a discrepancy between the model's assumption and reality (e.g. the `issue #102` "CL is an object, not a float" class of bug).
- Also confirm `SafeModel`'s tolerance doesn't *hide* a real shape change (tolerant parsing can mask divergence — assert on actual field values, not just "it didn't crash").

**If the client has both sync and async surfaces (iol, higyrus, ambito):**
- Drive both through the parametrized `["sync","async"]` unified test so any divergence between `client.py` and `aio.py` surfaces immediately. Every logic fix must be mirrored in both files (PROJECT.md).

**If the service is undocumented / anti-bot-sensitive (ambito):**
- Capture the exact live response with vcrpy first (it's the only spec), and treat 403/UA failures as findings about fragility, not as the client being wrong.

**If the service has a sandbox (iol api-sandbox, matriz remarkets):**
- Prefer the sandbox base URL for any write-adjacent surface; remarkets is already the matriz default and is safe for order routing.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `vcrpy 8.1.1` | `httpx >=0.27`, Python >=3.10 | 8.x is the first line with the httpx body-handling fix. Non-streaming JSON requests (this repo's usage) are fully supported, sync and async. |
| `pytest-recording 0.13.4` | `vcrpy 8.x`, `pytest 8.3+` | Provides `@pytest.mark.vcr`, `--record-mode`, `--block-network`. |
| `genson 1.3.0` | `jsonschema 4.26.0` | genson emits Draft-7-style schemas that jsonschema validates out of the box; specify `Draft202012Validator` explicitly if you want the newest dialect. |
| `jsonschema 4.26.0` | Python 3.12/3.13 | Draft 2020-12 supported; precise error paths via `iter_errors`. |
| `pydantic 2.13.4` | Python 3.12/3.13, mypy strict | v2 is 5-50x faster than v1; ships a mypy plugin if you want strict-mode coverage of the spec models. Dev-only here. |
| `anyio 4.13.0` | `httpx >=0.27` (already transitive) | No version conflict; httpx already depends on anyio. |
| `pytest-httpx 0.36.2` | `pytest 8.3+`, `httpx >=0.27`, `pytest-asyncio 0.24+` | Unchanged repo standard; the destination format for all regression tests. |
| `deepdiff 8.x` | Python 3.12/3.13 | Pure-python; no conflict. Optional. |

All additions are dev/test-only and do not alter any package's shipped wheel or runtime dependency closure — preserving the "no shared code between packages / no architectural change" constraint.

---

## Sources

- `/kevin1024/vcrpy` (Context7) — record modes, `filter_headers`/`filter_query_parameters`/`before_record_response` credential scrubbing, global `vcr.VCR` config. HIGH confidence.
- vcrpy 8.1.1 PyPI + Read the Docs changelog — httpx fix in 8.x, async-streaming caveat (issue #597). HIGH confidence (versions verified live against PyPI 2026-05-26).
- pytest-recording 0.13.4 (PyPI, kiwicom/pytest-recording GitHub) — `@pytest.mark.vcr`, `--record-mode`, `--block-network`. HIGH confidence.
- PyPI version checks (2026-05-26): vcrpy 8.1.1, pytest-recording 0.13.4, respx 0.23.1, pydantic 2.13.4, jsonschema 4.26.0, typeguard 4.5.2, pytest-httpx 0.36.2, genson 1.3.0, anyio 4.13.0. HIGH confidence.
- Pydantic docs + community guides — pydantic v2 performance, "pydantic does not validate against arbitrary JSON Schema; use jsonschema for that" separation of concerns. HIGH confidence.
- Simon Willison TIL + pythontutorials.net + pytest docs — opt-in integration marker pattern (`--integration`/`pytest_collection_modifyitems`), `-m "not integration"`. MEDIUM-HIGH confidence (multiple corroborating sources).
- invertironline.com/documentacion-api, /api; developers.invertironline.com; api-sandbox.invertironline.com — IOL v2 auth (15-min bearer + refresh), sandbox existence, covered instrument classes. MEDIUM confidence on capabilities; LOW on exact field shapes (gated docs).
- github.com/matbarofex/pyRofex (README) — reMarkets sandbox vs LIVE, function list, "returns dict of JSON response". MEDIUM confidence; exact schemas behind gated docs/Postman. The client's `"status":"ERROR"` check aligns with Primary's documented status-field pattern but must be confirmed live.
- mercados.ambito.com — **no public API docs found** (verified negative). Field shape known only from the client code (INTEGRATIONS.md: `/dolarnacion/historico-general/{from}/{to}`, no auth, browser-UA required). LOW confidence on response shape — live capture is the only authority.

---
*Stack research for: live-API verification of httpx-based Python financial API clients*
*Researched: 2026-05-26*
