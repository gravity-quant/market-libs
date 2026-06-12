# External Integrations

**Analysis Date:** 2026-05-27

## APIs & External Services

**Argentine Stock Broker (Invertir Online):**
- Service: Invertir Online (IOL) REST API
  - Package: `packages/iol-client/`
  - SDK/Client: `httpx` (custom thin wrapper)
  - Auth: OAuth 2.0 password grant — `POST /token` with `grant_type=password`; token cached at module level, auto-refreshed 60 s before 900 s expiry
  - Default base URL: `https://api.invertironline.com`
  - Env vars: `IOL_USER` (required), `IOL_PASSWORD` (required), `IOL_BASE_URL` (optional)
  - Endpoints used: `/token`, `/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion`, `/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/...`, `/api/v2/{pais}/Titulos/Cotizacion/Instrumentos`, `/api/v2/Cotizaciones/{type}/{pais}/Todos`
  - Sync client: `packages/iol-client/src/iol_client/client.py`
  - Async client: `packages/iol-client/src/iol_client/aio.py`

**Financial Back-Office (Higyrus / AUNESA):**
- Service: Higyrus REST API (financial operations platform)
  - Package: `packages/higyrus-client/`
  - SDK/Client: `httpx` (custom thin wrapper)
  - Auth: Proprietary Bearer token — `POST /api/login` with JSON body `{clientId, username, password}`; token valid 24 h, cached and refreshed after 23 h
  - Default base URL: `https://cliente.aunesa.com/Irmo` (from `.env.example`)
  - Env vars: `HIGYRUS_BASE_URL` (required), `HIGYRUS_USER` (required), `HIGYRUS_PASSWORD` (required), `HIGYRUS_CLIENT_ID` (optional)
  - Endpoints used: `/api/login`, `/api/health`, `/api/cuentas/{id}/movimientos`, `/api/cuentas/{id}/posicionValuada`, `/api/cuentas/listadoCuentas`, `/api/cuentas/{id}/posiciones`
  - Sync client: `packages/higyrus-client/src/higyrus_client/client.py`
  - Async client: `packages/higyrus-client/src/higyrus_client/aio.py`

**Derivatives Exchange (MATBA ROFEX / Primary API):**
- Service: MATBA ROFEX Primary API v1.21 (REST + WebSocket)
  - Package: `packages/matriz-client/`
  - SDK/Client: `httpx` for REST, `websocket-client` for WebSocket
  - Auth (REST): Token-based — `POST /auth/getToken` with headers `X-Username` / `X-Password`; token in `X-Auth-Token` header, valid 24 h, refreshed after 23 h
  - Auth (Risk API, REST): HTTP Basic Auth — credentials sent directly on each request
  - Auth (WebSocket): Reuses cached REST token sent as `X-Auth-Token` header on connection
  - Default base URL: `https://api.remarkets.primary.com.ar`
  - Env vars: `PRIMARY_USER` (required), `PRIMARY_PASSWORD` (required), `PRIMARY_BASE_URL` (optional)
  - REST endpoints used: `/auth/getToken`, `/rest/segment/all`, `/rest/instruments/all`, `/rest/instruments/details`, `/rest/instruments/detail`, `/rest/instruments/byCFICode`, `/rest/instruments/bySegment`, `/rest/order/newSingleOrder`, `/rest/order/replaceById`, `/rest/order/cancelById`, `/rest/order/id`, `/rest/order/allById`, `/rest/order/actives`, `/rest/order/filleds`, `/rest/order/all`, `/rest/order/byExecId`, `/rest/marketdata/get`, `/rest/data/getTrades`, `/rest/risk/position/getPositions/{account}`, `/rest/risk/detailedPosition/{account}`, `/rest/risk/accountReport/{account}`
  - WebSocket: connects to `wss://` equivalent of base URL; sends JSON frames for market data subscription (`smd`), order report subscription (`os`), new order (`no`), cancel order (`co`)
  - REST client: `packages/matriz-client/src/matriz_client/client.py`
  - WebSocket client: `packages/matriz-client/src/matriz_client/ws_client.py`

**Financial News Portal (Ámbito Financiero):**
- Service: Ámbito Financiero public market data API (no auth required)
  - Package: `packages/ambito-financiero-client/`
  - SDK/Client: `httpx` with browser User-Agent override (API returns 403 on `python-httpx/...` UA)
  - Auth: None — public API
  - Default base URL: `https://mercados.ambito.com`
  - Env vars: `AMBITO_BASE_URL` (optional override)
  - Endpoints used: `/dolarnacion/historico-general/{from}/{to}`
  - Sync client: `packages/ambito-financiero-client/src/ambito_financiero_client/client.py`
  - Async client: `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py`

**Wallets Platform:**
- Service: Wallets REST API (internal/private service)
  - Package: `packages/wallets-client/`
  - SDK/Client: `httpx` (custom thin wrapper)
  - Auth: Static Bearer token — sent as `Authorization: Bearer {token}` on every request; no login flow
  - Default base URL: `https://api.wallets.example` (placeholder — real URL set via env)
  - Env vars: `WALLETS_BASE_URL` (required), `WALLETS_TOKEN` (required)
  - Endpoints: Not yet defined (stub client with `_request()` helper only)
  - Sync client: `packages/wallets-client/src/wallets_client/client.py`
  - Async client: `packages/wallets-client/src/wallets_client/aio.py`

## Data Storage

**Databases:**
- None — these are stateless HTTP client libraries; no database connections

**File Storage:**
- None

**Caching:**
- In-process module-level token caching only (Python module globals `_token`, `_token_ts`, `_token_expires_at`)
- No external cache (Redis, memcached, etc.)

## Authentication & Identity

**Auth patterns by package:**

| Package | Mechanism | Token Lifetime | Auto-Refresh |
|---------|-----------|----------------|--------------|
| `iol-client` | OAuth 2.0 password grant (Bearer) | 900 s (15 min) | Yes, 60 s before expiry |
| `higyrus-client` | Proprietary Bearer (`POST /api/login`) | 24 h | Yes, after 23 h |
- `matriz-client` | Custom header token (`X-Auth-Token`, `POST /auth/getToken`) | 24 h | Yes, after 23 h |
| `wallets-client` | Static Bearer token (no login flow) | N/A | No |
| `ambito-financiero-client` | None (public API) | N/A | N/A |

All packages expose a `configure()` function to override credentials at runtime and reset the cached token.

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry, Datadog, or similar

**Logs:**
- None — packages raise typed exceptions; no internal logging framework used
- Each package defines a custom exception hierarchy (e.g., `IOLAPIError`, `IOLAuthError`, `IOLRateLimitError`)

## CI/CD & Deployment

**Hosting:**
- GitHub (source) + GitHub Releases (artifact distribution)
- Not published to PyPI

**CI Pipeline:**
- GitHub Actions: `.github/workflows/ci.yml` (lint, pre-commit, typecheck, test matrix)
- GitHub Actions: `.github/workflows/release.yml` (build + release on tag push)

## Webhooks & Callbacks

**Incoming:**
- None — these are client libraries, not servers

**Outgoing:**
- WebSocket streaming callbacks in `matriz-client` (user-registered Python callables):
  - `on_message: Callable[[PrimaryWsMessage], None]` — fires for each incoming frame
  - `on_error: Callable[[Exception], None]` — fires on WebSocket errors
  - `on_close: Callable[[], None]` — fires on connection close
  - Registered via `ws_connect()` in `packages/matriz-client/src/matriz_client/ws_client.py`

## Environment Configuration

**Required env vars by package:**

`iol-client`:
- `IOL_USER` — IOL account username
- `IOL_PASSWORD` — IOL account password
- `IOL_BASE_URL` — (optional) override for `https://api.invertironline.com`

`higyrus-client`:
- `HIGYRUS_BASE_URL` — API base URL (e.g., `https://cliente.aunesa.com/Irmo`)
- `HIGYRUS_USER` — login username
- `HIGYRUS_PASSWORD` — login password
- `HIGYRUS_CLIENT_ID` — (optional) tenant identifier sent in login body

`matriz-client`:
- `PRIMARY_USER` — Primary API username
- `PRIMARY_PASSWORD` — Primary API password
- `PRIMARY_BASE_URL` — (optional) override for `https://api.remarkets.primary.com.ar`

`wallets-client`:
- `WALLETS_BASE_URL` — API base URL
- `WALLETS_TOKEN` — static Bearer token

`ambito-financiero-client`:
- `AMBITO_BASE_URL` — (optional) override for `https://mercados.ambito.com`

**Secrets location:**
- Per-package `.env` files (gitignored)
- `.env.example` templates committed to each package directory
- GitHub Actions secrets for CI (not enumerated; CI uses `uv.lock` only, no service credentials)

---

*Integration audit: 2026-05-27*
