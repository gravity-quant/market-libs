# Project Research Summary

**Project:** market-libs — v1.1 Tech Debt Cleanup
**Domain:** Python HTTP client library monorepo refactor (4 packages: iol, higyrus, ambito, matriz)
**Researched:** 2026-06-10
**Confidence:** HIGH

## Executive Summary

The v1.1 milestone is a structured architectural cleanup of four verified financial API clients. All five refactor axes (Client class per instance, sync/async logic dedup, retries with backoff/jitter, structured logging, and driver harness hardening) have well-established, high-confidence patterns in the Python SDK ecosystem. The canonical reference is the openai/anthropic SDK shape: a `Client` dataclass holding instance state, a lazy module-level default backing backward-compatible top-level functions, and a mirrored `AsyncClient` in `aio.py` with independent state. This pattern preserves the existing `pkg.get_quote(...)` call style while unlocking per-instance state needed by the HIGY multi-account and IOL refresh_token fixes.

The dominant execution risk is not technical uncertainty — every recommendation is verified against official sources — it is the mechanical complexity of applying each change across four independent packages while maintaining 277 mocked tests. The single most dangerous trap is the `monkeypatch.setattr(pkg.client, "_token", ..., raising=False)` fixture pattern: after the refactor, these writes silently land on a dead address unless a PEP 562 `__getattr__` shim (or conftest migration to `configure(token=...)`) is in place before the first package ships. A golden public-surface snapshot test must be written and passing before any package is touched.

The phase order is fully determined by dependency: Client class skeleton first (unlocks everything), then `_core.py` dedup (unlocks both the retry `RequestSpec.idempotent` field and the safe creation of matriz `aio.py`), then retries/logging/matriz-aio in parallel (independent after dedup), then bug fixes (cheapest post-dedup because each fix lands once in `_core.py` instead of twice), then driver harness, then live re-verification. Each deferred bug fix is strictly easier after the dedup refactor — applying them before `_core.py` exists would require touching both `client.py` and `aio.py` per package.

## Key Findings

### Recommended Stack

The v1.0 stack (Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict) is unchanged. The only runtime addition is `tenacity>=9.1.0,<10` added to each of the four packages' `pyproject.toml`. Tenacity wins over httpx-retries and hand-rolled transport because it (a) works identically as a decorator on both sync and async callables, (b) ships `py.typed` for mypy strict, (c) has zero runtime dependencies, and (d) gives per-call `idempotent` gate control that a transport-level approach cannot express cleanly given the existing exception hierarchy.

Structured logging uses stdlib `logging` only — no structlog, no loguru. Library code must never call `logging.basicConfig()` or add handlers beyond `NullHandler`. All credential redaction logic is duplicated per-package in `_logging.py` (the `verification/redaction.py` module is harness-only and not importable from published packages). The Client class, sync/async dedup, and all bug fixes require zero new dependencies — they are pure design pattern work.

**Core technologies (additions only):**
- `tenacity>=9.1.0,<10`: retry decorator for 5xx/429/connection errors — only option with per-call mutating gate, `py.typed`, and zero deps
- `stdlib logging` with `NullHandler`: structured library logging — zero deps, follows Python HOWTO mandate for library code
- `@dataclass(slots=True) Client`: instance state pattern — zero deps, preserves v1.0 module-level convenience API via compat layer
- `_core.py` pure helpers per package: sync/async dedup target — zero deps, transport-agnostic builders and parsers

### Expected Features

The five axes decompose into a clear P1/P2 stack. Everything in P1 must land in v1.1; P2 items are ergonomic additions that do not block the milestone.

**Must have (P1 — table stakes):**
- `Client` class per package with `close()`/`aclose()`, sync and async context managers, instance-scoped state (base_url, credentials, token, http client) — unblocks multi-account and refresh_token persistence
- Lazy module-level default client backing existing top-level functions verbatim — non-breaking is non-negotiable for a minor version bump
- `_core.py` per package: transport-agnostic builders/parsers for every endpoint; `raise_for_response`, `unwrap_envelope`, auth-flow helpers — the dedup target that eliminates the "logic duplicated" known debt
- `aio.py` for `matriz-client` mirroring the REST surface with independent async state — parity with the other three packages
- Retry on 408/409/429/5xx plus connection errors; default max 2 retries; full-jitter exponential backoff; `Retry-After` header honored (capped at 60s); GET-only by default (POST/PATCH never retried without explicit `idempotent=True`)
- `mutation_gate` check before any POST/PATCH retry — mandated by PROJECT.md; prevents duplicate orders on matriz
- Per-package `logging.getLogger("<pkg>")` with `NullHandler` in `__init__.py`; DEBUG/INFO/WARNING/ERROR level map; redacted `extra={}` structured fields
- `verification/findings.py` append-only with BEGIN/END zone parser; content-addressed dedup by finding ID; operator fields (Classification/Rationale/Regression/Resolution) preserved verbatim across re-runs
- Four deferred bug fixes: F-09 matriz ERROR-MAP (single `_core.raise_for_response` fix, both surfaces free), F-02 higyrus `get_listado_cuentas=0`, IOL refresh_token persistence, HIGY multi-account iteration
- WR-01..WR-08 code review concern close-out (8 driver/harness items from Phase 5 review)

**Should have (P2 — differentiators):**
- `client.with_options(max_retries=N)` per-call override (anthropic/openai pattern)
- Pluggable `http_client=` kwarg for test injection without monkeypatching
- `Client.from_env()` classmethod for explicit env-reading
- `request_id` UUID per `_request()` invocation threaded through retry log records
- Account-id in logging `extra` for higyrus/matriz multi-account disambiguation
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders

**Defer to v1.2+:**
- Generated-code parity tooling (one source, two emit paths via unasync/codegen)
- Automatic Idempotency-Key for retried POSTs
- `findings.toml` machine-readable side-file
- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff)
- WebSocket live verification for `matriz_client.ws_client`

### Architecture Approach

Each package gets five new private modules (`_state.py`, `_core.py`, `_transport.py`, `_atransport.py`, `_logging.py`) that are replicated four times independently — the no-shared-internals constraint is preserved. `client.py` and `aio.py` become thin transport shells (~30-50 LOC per endpoint) that call shared pure helpers in `_core.py`, differing only at the `httpx.Client.send()` vs `await httpx.AsyncClient.send()` boundary. The critical backward-compat mechanism is a PEP 562 `__getattr__` shim at module level that routes `pkg.client._token` reads to `_DEFAULT._state.token`, preserving existing `monkeypatch.setattr` semantics via a conftest migration to `configure(token=...)`.

**Major components:**
1. `Client` / `AsyncClient` (per package in `client.py` / `aio.py`) — instance-scoped state, transport lifecycle, context manager, compat delegators
2. `_core.py` (per package) — pure `RequestSpec` builders and response parsers, `raise_for_response`, `unwrap_envelope`, token freshness check; no I/O, no side effects
3. `_transport.py` / `_atransport.py` (per package) — `RetryTransport(httpx.HTTPTransport)` subclass; status-based and connection-error retry with full-jitter backoff; mutation-aware via `request.extensions["idempotent"]`
4. `_state.py` (per package) — `@dataclass _ClientState` holding base_url, credentials, token, expiry, refresh_token
5. `_logging.py` (per package) — `logging.getLogger("<pkg>")` + `NullHandler` + `RedactingFilter` with inline Bearer/header redaction logic
6. `verification/findings.py` (harness, one instance) — append-only BEGIN/END zone writer with content-addressed dedup and operator-field preservation

### Critical Pitfalls

1. **`monkeypatch.setattr(..., raising=False)` silently breaks 277 tests after Client refactor** — write the "fixture reaches production" guard test (assert fixture-set token appears in wire Authorization header) BEFORE the first package ships; implement the PEP 562 `__getattr__` shim or migrate conftest to `configure(token=...)` in Phase 0.

2. **Retry decorator blindly retries POST mutations, causing duplicate orders** — apply `idempotent: bool = False` kwarg to every `_request` call; GET endpoints tag `idempotent=True` explicitly; add regression test asserting exactly ONE outgoing request for any mutating POST against a mocked 503.

3. **`_core.py` accidentally re-imports from `client.py` or `aio.py`, re-coupling sync/async state** — add a CI grep or import-linter rule that bans `_core.py` from importing either surface; use distinct sentinel tokens for sync/async fixtures to surface cross-leak as a test failure.

4. **matriz `aio.py` created by copy-paste before `_core.py` exists, enshrining the tech debt the milestone aims to eliminate** — hard prerequisite: `_core.py` extraction must complete for at least one package before `aio.py` is written; PR checklist must confirm no duplicate `_unwrap` or `_raise_for_response` in both files.

5. **Library calls `logging.basicConfig()` or adds handlers to root logger, hijacking downstream apps' log config** — add a CI grep rule banning `logging.basicConfig` and `logging.root` from `packages/*/src/`; add a regression test asserting `logging.root.handlers` is unchanged after importing any package.

6. **401 retry storm: expired token causes N retries with the same stale header** — handle 401 explicitly in `_request()` with exactly one re-auth attempt (clear token, call `_ensure_token()`, retry once); never include `AuthError` in the retry decorator's `retry_on=` tuple.

## Implications for Roadmap

Based on research, the dependency DAG fully determines phase order. Six phases are suggested.

### Phase 0: Compat Safety Net and Golden Tests
**Rationale:** Without a public-surface snapshot and a "fixture reaches production" guard test, there is no trustworthy way to verify that subsequent phases don't break callers or the 277-test suite. This is the prerequisite for all refactor work.
**Delivers:** `verification/test_public_surface.py` snapshotting every module attribute and function signature; "fixture reaches production" guard test per package; conftest migration plan for `configure(token=...)` documented; monkeypatch sentinel differentiation (SYNC-sentinel vs ASYNC-sentinel) in place.
**Addresses:** Pitfall 1 (silent monkeypatch breakage), Pitfall 18 (weakened tests during refactor)
**Avoids:** Any refactor landing without a verifiable non-breaking baseline
**Research flag:** Standard patterns — no phase research needed.

### Phase 1: Client Class Skeleton + Back-Compat Layer (4 packages)
**Rationale:** Every other axis depends on the Client class existing. The HIGY multi-account fix and IOL refresh_token fix both require instance-scoped state. Process: iol first (canonical, has refresh_token), then higyrus, ambito, matriz.
**Delivers:** `Client` and `AsyncClient` per package with `_state.py`, `close()`/`aclose()`, context managers; `configure()` extended to accept `token`/`token_expires_at` for test fixtures; PEP 562 `__getattr__` shim routing `_token` reads to default instance; all 277 tests green.
**Addresses:** Axis A (Client class), Pitfall 2 (configure scope), Pitfall 11 (pickle), Pitfall 12 (atexit async)
**Research flag:** Standard patterns (openai/anthropic SDK reference). No phase research needed.

### Phase 2: `_core.py` Extraction — Sync/Async Logic Dedup (4 packages)
**Rationale:** `_core.py` is the prerequisite for both the retry `RequestSpec.idempotent` field (Phase 3) and the safe creation of `matriz_client.aio` (Phase 4). Eliminates the root cause of the higyrus envelope-unwrap class of bugs.
**Delivers:** `_core.py` per package with pure builders, parsers, `raise_for_response`, `unwrap_envelope`; `client.py` and `aio.py` become thin shells; CI import-linter rule banning `_core.py` → `client.py`/`aio.py` imports.
**Addresses:** Axis B (sync/async dedup), Pitfall 3 (re-coupling), Pitfall 8 (copy-paste matriz precondition)
**Research flag:** Standard patterns. No phase research needed.

### Phase 3: Retries, Backoff, and Structured Logging (4 packages, parallelizable)
**Rationale:** Both land after Phase 2 and are independent of each other. Grouped because each retry attempt emits a WARNING log record — one pass avoids touching the same files twice.
**Delivers:** `RetryTransport` / `AsyncRetryTransport` with full-jitter exponential backoff, `Retry-After` honoring (capped 60s), `idempotent` extension gate; `_logging.py` with `NullHandler`, `RedactingFilter`, structured `extra={}`; regression tests for no-token-in-caplog and no-retry-on-POST.
**Addresses:** Axis C (retries), Axis D (logging), Pitfalls 4, 5, 6, 7, 13, 14, 15, 16, 17, 29
**Research flag:** Standard patterns. No phase research needed.

### Phase 4: Deferred Bug Fixes (leveraging `_core.py`)
**Rationale:** Each fix becomes a single-location change in `_core.py` that propagates to both surfaces for free. Doing them before Phase 2 would require dual-file changes per package.
**Delivers:** F-09 matriz ERROR-MAP fix; F-02 higyrus `get_listado_cuentas=0`; IOL refresh_token persistence; HIGY multi-account iteration. One regression test per fix.
**Addresses:** 4 deferred findings from v1.0 verification cycle
**Research flag:** Mostly standard. If IOL refresh_token includes disk persistence (vs in-memory only), phase-level research on secure token storage warranted.

### Phase 5: matriz `aio.py` Creation
**Rationale:** Depends on Phase 2 (`_core.py` for matriz) and Phase 3 (retry/logging infrastructure). Hardest sub-task is the three-way token store shared among sync Client, AsyncClient, and ws_client daemon thread.
**Delivers:** Full `AsyncClient` in `matriz_client/aio.py`; `TokenStore` class with `threading.Lock` usable from all three contexts; `main_matriz.py` extended with async probes; pytest-asyncio fixtures following iol-client conftest pattern.
**Addresses:** Axis B completion (matriz parity), Pitfalls 8, 9, 19, 25
**Research flag:** NEEDS phase-level research. The three-way concurrent token store (asyncio event loop + sync thread + ws daemon thread with threading.Lock) is the single most complex piece of v1.1 and should be spiked before planning.

### Phase 6: Driver Harness Hardening and Live Re-verification
**Rationale:** Harness changes don't depend on package refactors but benefit from the test stability that structural work provides. Live re-verification is the final gate.
**Delivers:** `verification/findings.py` append-only with BEGIN/END zone parser and content-addressed dedup; D-MATZ-27 fixed; WR-01..WR-08 each closed with regression test where applicable; all `main_*.py` driver re-runs idempotent; live smoke passes for all four packages including new matriz async surface.
**Addresses:** Axis E (findings append-only), Pitfalls 10, 20, 21, 22, 23, 24, 26, 30
**Research flag:** Standard patterns. Per-WR triage at planning time (some items are docs, some are code).

### Phase Ordering Rationale

- Phase 0 is a hard prerequisite for all refactor work: no trustworthy non-breaking signal without golden surface snapshot.
- Phase 1 before Phase 2: `_core.py` extraction is cleanest when the Client shell already exists to receive the wired-in pure calls.
- Phase 2 before Phase 3: `RequestSpec.idempotent` field required by `RetryTransport`; endpoint metadata must be centralized first.
- Phase 2 before Phase 5: `_core.py` for matriz must exist before `aio.py` is created or copy-paste antipattern (Pitfall 8) is inevitable.
- Phase 3 and Phase 4 can run in parallel after Phase 2; neither blocks the other.
- Phase 5 requires both Phase 2 and Phase 3 (retry/logging infrastructure needed for the new module).
- Phase 6 is last: driver harness fixes and live re-verification are the integration gate after all structural work.

### Research Flags

Phases needing deeper research during planning:
- **Phase 5 (matriz `aio.py`):** The three-way token store (sync/async/daemon-thread) with `threading.Lock` callable from asyncio context needs a spike before planning. This is the single architectural unknown in v1.1.

Phases with standard patterns (no phase research needed):
- **Phase 0:** Test scaffolding — well-established.
- **Phase 1:** Client class + compat layer — fully documented in openai/anthropic SDK reference.
- **Phase 2:** `_core.py` pure helper extraction — httpx-native pattern; no unknowns.
- **Phase 3:** tenacity + stdlib logging — both verified via Context7 + PyPI; all configuration patterns documented.
- **Phase 4:** Bug fixes in `_core.py` — straightforward post-dedup application.
- **Phase 6:** Driver harness — WR items are well-scoped from Phase 5 code review.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | tenacity 9.1.4 verified via Context7 + PyPI + source (py.typed confirmed); stdlib logging from official Python HOWTO; all alternatives explicitly evaluated and rejected with reasons |
| Features | HIGH | Cross-confirmed against anthropic, openai, stripe SDK shapes; retry status codes from RFC 9110 + MDN; idempotency gate from PROJECT.md constraint |
| Architecture | HIGH | Built on validated v1.0 architecture (277 tests + live verification); PEP 562 `__getattr__` stable since Python 3.7; all pattern decisions have concrete code sketches |
| Pitfalls | HIGH | Rooted in existing codebase (CONCERNS.md, TESTING.md, Phase 5 WR-01..WR-08 review); each pitfall has a concrete prevention mechanism and regression test pattern |

**Overall confidence:** HIGH

### Gaps to Address

- **Exact redaction regex set for `_logging.py`:** Phase 3 plan must enumerate patterns from `verification/redaction.py` and confirm they cover Bearer, X-Auth-Token, `password=`, IOL refresh_token, and Higyrus JSON `password` field before per-package duplication.
- **TokenStore threading design (Phase 5):** The exact `ThreadingLock`-callable-from-asyncio pattern needs a spike before Phase 5 planning. Simpler alternative (independent token caches per surface, no sharing with ws_client) should be evaluated against the race condition risk.
- **IOL refresh_token disk-persistence scope:** Operator decision at Phase 4 planning — in-memory only (`_ClientState.refresh_token`) is low-risk; disk persistence adds complexity and security surface.
- **WR-01..WR-08 per-item content:** Full concern text lives in `.planning/milestones/v1.0-phases/05-matriz-verification/05-REVIEW.md`. Phase 6 plan must load each WR item and classify as code-fix+test or docs-only.
- **`configure()` return type:** PITFALLS.md recommends returning `Client` (the new default) to clarify scope. Confirm no existing caller `None`-checks the return value before adding.

## Sources

### Primary (HIGH confidence — Context7 + official docs + source inspection)
- `/jd/tenacity` (Context7, 187 snippets, score 82.1) — `wait_exponential_jitter`, `AsyncRetrying`, `retry_if_exception`, coroutine auto-detection
- `/websites/tenacity_readthedocs_io_en` (Context7, 45 snippets, score 86.7) — cross-verified API
- `/will-ockmore/httpx-retries` (Context7, 55 snippets) — evaluated and rejected; transport-level gate limitation documented
- `/hynek/structlog` + `/delgan/loguru` (Context7) — evaluated and rejected; library-as-runtime-dep concern
- Python Logging HOWTO (official) — `NullHandler` mandate, level conventions, don't-log-to-root rule
- AWS Architecture Blog — Exponential Backoff and Jitter — full jitter as recommended default
- RFC 9110 — idempotent methods (GET/HEAD/OPTIONS/PUT/DELETE); POST/PATCH not idempotent
- MDN — Retry-After header (RFC 7231 §7.1.3) — delta-seconds and HTTP-date formats
- Anthropic SDK DeepWiki — retry shape (408/409/429/>=500), 2-attempt default, per-request timeout semantics
- OpenAI SDK DeepWiki — same retry shape; lazy `_ModuleClient` backing top-level helpers
- https://pypi.org/pypi/tenacity/json — version 9.1.4, zero runtime deps, Apache-2.0, requires-python>=3.10
- https://github.com/jd/tenacity — `py.typed` confirmed present

### Secondary (HIGH confidence — existing codebase + validated v1.0 artifacts)
- `.planning/codebase/ARCHITECTURE.md` — v1.0 singleton pattern, monkeypatch fixtures, ws_client token sharing
- `.planning/codebase/TESTING.md` — autouse conftest `monkeypatch.setattr(..., raising=False)` per package
- `.planning/codebase/CONCERNS.md` — module-level singleton issues, no retries/logging
- `.planning/milestones/v1.0-phases/05-matriz-verification/05-REVIEW.md` — WR-01..WR-08 detailed analysis
- `.planning/todos/pending/matriz-driver-findings-file-handling.md` — D-MATZ-27 dedupe requirements
- `.planning/PROJECT.md` — v1.1 milestone scope, constraints, out-of-scope items

---
*Research completed: 2026-06-10*
*Ready for roadmap: yes*
