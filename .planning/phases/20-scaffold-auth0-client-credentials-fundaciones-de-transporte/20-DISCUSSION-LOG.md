# Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-29
**Phase:** 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
**Mode:** assumptions
**Areas analyzed:** Module Decomposition, Auth0 Token Lifecycle, Health Anonymous Path, Transport/Retry/Logging/Concurrency

## Assumptions Presented

### Module Decomposition & File Set for Phase 20
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Mirror iol private-module layout; OMIT `_token_cache.py`; NO `models.py`/`types.py`; Auth0 builder/parser in `_core.py` | Confident | D-04 defers disk cache (drops `platformdirs` iol carries at `pyproject.toml:25`); response models slated for Phases 21/22 (D-05) |

### Auth0 client_credentials Token Lifecycle
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Single-grant flow: one `build_token_request` + one `parse_token_response`, no `refresh_token` state/logic; `_ensure_token()` re-runs grant; TTL = `time.time()+expires_in-buffer` (~60s buffer) with fallback for absent `expires_in` | Likely | iol refresh apparatus (`client.py:405-427`, CR-01) exists only because IOL password grant issues refresh_token; client_credentials issues none; iol already derives TTL from `expires_in` (`_core.py:194`) |

### Health Endpoints (anonymous path) & Client-Class Surface Scope
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `/health*` need unauthenticated request path (no Authorization, no `_ensure_token()`); `with_options(max_retries=N)` deferred to Phase 21 | Likely | Source plan: health "sin auth" (line 21); iol `Client._request` (`client.py:445`) unconditionally auths; `with_options` slotted under Phase 2 (line 78) |

### Transport, Retry, Logging & Concurrency Reuse
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Mirror iol transport verbatim (retryable set, `wait_exponential_jitter`, `Retry-After` 60s cap, mutation gate); swap redaction to `client_secret`; use `asyncio.Lock` double-checked NOT matriz `TokenStore`; no `RefreshPolicy` | Confident | iol `_transport.py:54-61` is shared canary baseline; matriz TokenStore scoped to 3-way incl. WS daemon thread (deferred); `RedactingFilter` per-package by design (`_logging.py:40-70`) |

## Corrections Made

No assumptions were rejected. Two open sub-decisions within Likely assumptions were resolved by the user:

### Auth0 Token Lifecycle — `expires_in` absent fallback
- **Original assumption:** TTL fallback when `expires_in` is missing (open: 900s iol vs ~1h vs fail-loud)
- **User decision:** **~1 hour (3600s)** — conservative middle ground; avoids iol's 900s hourly-re-auth churn on ~24h Auth0 tokens, and avoids failing loudly.

### Health Anonymous Path — implementation shape
- **Original assumption:** unauthenticated health path (open: `authenticated` flag vs dedicated `_request_anonymous` shell)
- **User decision:** **`authenticated: bool = True` flag on the request spec** — single code path, health passes `authenticated=False`.

## External Research

None performed. Auth0 `client_credentials` is a standard OAuth2 grant fully coverable by iol-derived
patterns. Live-environment facts (develop tenant's actual `expires_in`, whether `/health*` truly
accepts anonymous requests) are deferred to Phase 23 verification, not research gaps blocking Phase 20.
