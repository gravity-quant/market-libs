# Research Summary — v1.2 Architecture + Auth/Ergonomics Carry-forwards

**Project:** market-libs — Verificación en vivo de clientes
**Synthesized:** 2026-06-14
**Confidence:** HIGH (stack, features, pitfalls) | MEDIUM (codegen integration — spike-gated)
**Source reports:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Executive Summary

v1.2 closes two clusters of residual debt from v1.1: (1) structural sync/async duplication — migrating the four `main_*.py` drivers from the PEP 562 shim to direct `Client()`/`AsyncClient()` instantiation, and optionally eliminating the dual `client.py`/`aio.py` maintenance burden via unasync codegen; (2) auth/ergonomics carry-forwards — IOL OAuth refresh_token disk persistence (extending v1.1 BUG-03 from in-process to cross-process), plus `Client.from_env()` and `client.with_options(max_retries=N)` across all four packages. The four parallel researchers converged on a clear stack (unasync 0.6.0 spike-gated, platformdirs for IOL disk cache, no keyring, no cryptography in v1.2), clear feature categorization (driver migration + with_options + IOL persistence are table stakes; from_env is optional alias; codegen needs spike-before-plan; LIVE re-verification is table stake), and a 5-phase build order derived from the dependency DAG.

The single largest architectural unknown is codegen: whether unasync's token-replacement approach handles all four packages cleanly — especially matriz's 852-LOC `aio.py` with its 3-way `TokenStore` concurrency primitive — or whether the overhead exceeds the LOC-dedup payoff at this repo's 4-package scale. The PROJECT.md spike-before-plan flag is active and must be honored before Phase 3 planning commits. All other v1.2 features have high-confidence patterns validated against anthropic/openai SDK source, msal-extensions, and the v1.1 codebase. The 4 HIGHEST-RISK pitfalls do not fail CI unless specific regression tests are written in the same phase that introduces the feature.

---

## Stack Additions for v1.2

| Library | Version | Dep Type | Scope | Role | Rationale |
|---------|---------|----------|-------|------|-----------|
| **unasync** | `>=0.6.0,<0.7` | dev-only | All 4 packages | Token-replacement codegen: generate `client.py` from `aio.py` | Used by httpcore/elasticsearch-py/urllib3; per-package `Rule(fromdir, todir)` matches no-shared-internals; spike-gated |
| **platformdirs** | `>=4.0,<5` | runtime — iol-client ONLY | iol-client | Cross-platform user-data-dir for IOL refresh_token disk cache | Zero deps, MIT, 22KB wheel, PEP 561 typed |
| **stdlib** (`os`, `json`, `pathlib`, `fcntl`) | — | built-in | iol-client | File I/O, 0600 chmod, fcntl inter-process locking | No new dep |
| **libcst** | `>=1.8.0,<2` | dev-only (FALLBACK ONLY) | — | AST codemod fallback if unasync spike fails on matriz | 1.8.6 Nov 2025, MIT, py.typed |

**Explicit rejects:**

| Rejected | One-line reason |
|----------|----------------|
| keyring | Headless CI requires null-backend (no-op); macOS first-read GUI prompt blocks unattended drivers; Linux needs SecretStorage+jeepney |
| cryptography (Fernet) | Adds C-extension dep without changing trust boundary while `.env` already holds stronger credentials in plaintext; defer to v1.3 |
| ast-grep | Rust CLI binary — breaks Python-tools-only CI invariant |
| comby | Does not support indentation-sensitive languages per their own docs |
| Jinja2/Mako | Template maintenance > per-endpoint source; unasync token-replacement is closer to the problem |
| syrupy/pytest-snapshot | Dep overhead for 4-driver × small golden files; pytest capsys + pathlib suffices |

---

## Feature Landscape

| # | Feature | Category | Complexity | v1.2 dependency | Reference |
|---|---------|----------|------------|-----------------|-----------|
| 1 | Driver migration × 4 (`main_*.py` → `Client()`) | Table stake | M per pkg | None; precedes codegen | Anthropic examples never use module-level helpers |
| 2 | unasync/codegen single-source | Differentiator (spike-gated — may defer v1.3) | L | Phase 0 spike; runs AFTER driver migration | psycopg3; unasync (urllib3/httpcore); unasyncd (libcst) |
| 3 | Final live re-verification × 4 (LIVE-01-equivalent) | Table stake | S | Features 1 + 2 complete | v1.1 LIVE-01 Phase 11 |
| 4 | IOL refresh_token disk persistence | Table stake for OAuth flows | M-L | v1.1 BUG-03 + TokenStore lock pattern | msal-extensions PersistedTokenCache; google-auth fcntl |
| 5 | `Client.from_env()` × 4 | Optional alias — OPERATOR DECISION | S | No-op on v1.1 `_ClientState` env defaults | NOT industry standard; 7-SDK survey: all use implicit env fallback in constructor |
| 6 | `client.with_options(max_retries=N)` × 4 | Table stake | M | Requires RetryTransport per-request extension refactor | anthropic `copy()`/`with_options()`; openai `with_options()` |

**Feature 5 note:** The industry survey (anthropic, openai, stripe, mistral, groq, cohere, google-genai) found ZERO SDKs shipping a separate `from_env()` classmethod. All use implicit env fallback in the constructor — which v1.1 already implements. Ship `from_env()` as a 5-line documented alias ONLY if the operator wants the IDE autocomplete discoverability win.

---

## Architecture Integration — 5 Most Consequential Decisions

1. **PEP 562 shim + top-level delegators stay forever.** Driver migration eliminates the driver's dependency on the shim but zero library-side symbols can be removed (harness `mutation_gate.py:55` + `test_async_configure_resource_warning.py:66-71` still use them). LOC drop comes from codegen, not from removing back-compat surface.

2. **B8 identity invariant must survive codegen.** `aio._raise_for_response is client._raise_for_response is _core.raise_for_response` (at `iol_client/client.py:78`) must be emitted as a literal alias `_raise_for_response = _core.raise_for_response` — never a thunk. Tests files are NEVER codegen targets.

3. **ONE Client per `main()` run — never per probe.** Constructing a new `Client()` per probe triggers N OAuth handshakes (IOL rate-limit risk), bypasses the shared TokenStore 3-way concurrency primitive (matriz corruption risk), and breaks finding correlation. Shape: `client = Client.from_env(max_retries=2)` at top of `main()`, passed to each probe as positional arg.

4. **matriz `_token_store.py` is OFF-LIMITS to codegen.** The 3-way concurrency primitive (`threading.Lock` callable from sync REST, asyncio context via `asyncio.to_thread`, and ws_client daemon thread) has structurally different sync/async paths no token-replacement codegen can synthesize. Must be in the codegen deny-list with a pre-commit hook.

5. **`with_options()` requires `_transport.RetryTransport` per-request `max_attempts` extension.** The cached `httpx.Client` has `max_attempts` baked into its Transport at construction. A `with_options(max_retries=N)` view must thread the new cap via `request.extensions["max_attempts"]` (mirror of the v1.1 `idempotent` extension pattern, ~15 LOC per package in `_transport.py` + `_atransport.py`).

---

## Watch Out For — 4 HIGHEST-RISK Pitfalls

**Pitfall 4 — Codegen breaks B8 identity** (phase: codegen spike + per-package)
If codegen emits a thunk `def _raise_for_response(resp): return _core.raise_for_response(resp)` instead of the alias `_raise_for_response = _core.raise_for_response`, the `is` check becomes False. The B8 identity test must run FIRST in CI. Regression test: parametrized over all 4 packages, asserts identity across `aio`, `client`, `_core`.

**Pitfall 5 — Codegen overwrites by-hand edits** (phase: codegen spike)
Pre-commit hook runs codegen with `aio.py` as source of truth → operator's parallel hand-edit to `client.py` is silently overwritten. Prevention: generated-file marker `# @generated by unasync from aio.py — DO NOT EDIT` at top of file; CI job `make codegen && git diff --exit-code` as a separate job; pre-commit hook rejects `client.py` edits when marker is present and `aio.py` is not in the same commit.

**Pitfall 7 — Token leak via new disk log sites** (phase: IOL disk persistence)
`iol_client/_token_cache.py` introduces new log sites. If the logger is outside the `iol_client.*` namespace, the v1.1 `RedactingFilter` does NOT apply. Prevention: logger MUST use `logging.getLogger(__name__)` from inside `packages/iol-client/src/iol_client/`; never log `exc` on write failure — only `type(exc).__name__`; regression test asserts sentinel substring absent from all caplog records across sync + async disk lifecycle paths.

**Pitfall 14 — `with_options(max_retries=N)` bypasses mutation gate** (phase: with_options × 4 packages)
`client.with_options(max_retries=10).new_order(...)` could allow 10 retry attempts on a non-idempotent matriz call, voiding the v1.1 Pitfall 4 duplicate-order prevention. This is money-on-the-line. Prevention: `RetryTransport.handle_request` checks `request.extensions.get("idempotent", False)` FIRST and enforces exactly-1-attempt for non-idempotent calls regardless of `max_attempts`. CRITICAL regression test: asserts exactly 1 outgoing request for `client.with_options(max_retries=10).new_order(...)` on a 503 response.

---

## Suggested Phase Decomposition

**5 phases total** (reduces to 4 if codegen spike → defer-to-v1.3):

### Phase 0: Spike — Codegen Tool Selection
PROJECT.md spike-before-plan flag is active. Prove unasync round-trip on ambito first (smallest, no auth), then attempt matriz. Outputs: go/no-go decision; per-package `Rule` config; B8 preservation proof; ruff format-stability proof; mypy strict pass on generated file; codegen deny-list for `_token_store.py`. **Research flag: YES — this IS the research phase for Feature 2.**

### Phase 1: Cross-Package Ergonomics (`from_env()` + `with_options()`)
Serial order: ambito → higyrus → matriz → iol (iol last because it interacts with disk cache in Phase 2a). Delivers `from_env()` + `with_options(max_retries=N)` + `Client._is_view` flag + `RetryTransport` per-request `max_attempts` extension × 4 packages. Must land mutation gate invariant test before Phase 1 merge. **Research flag: NO.**

### Phase 2a (parallel with 2b): IOL Disk Persistence
IOL-only. Delivers `iol_client/_token_cache.py`; opt-in `Client(token_cache_path=...)` kwarg; lazy disk read in `_ensure_token()`; atomic write on `login()`/`_refresh()` rotation; `fcntl.flock`; chmod 0600; CI detection guard; 8+ regression tests (4 v1.1 BUG-03 lifecycle paths × disk). Adds `platformdirs>=4.0,<5` to iol-client runtime deps. **Research flag: NO.**

### Phase 2b (parallel with 2a): Driver Migration × 4
Serial order: ambito → iol → higyrus → matriz. Probe names UNCHANGED (finding-title stability). AST regression-guard `test_main_<pkg>_uses_single_client_instance` per driver. Per-package LIVE smoke at end of each sub-package migration. Closes LOC-drop residual (iol -5.1%, matriz -20%). **Research flag: NO for ambito/iol/higyrus; CONDITIONAL for matriz (TokenStore interaction needs per-phase scoping audit).**

### Phase 3: Codegen Single-Source (conditional on Phase 0 go/no-go)
Targets `client.py`/`aio.py` transport shells ONLY. Serial order: ambito → iol → higyrus → matriz. Generated-file `@generated` marker; CI `lint-codegen` verify-clean job; B8 identity test as FIRST CI test; `_token_store.py` in deny-list. If Phase 0 → defer-to-v1.3, this phase is DROPPED. **Research flag: NO — reads Phase 0 spike report.**

### Phase 4: Final Live Re-verification × 4 (LIVE-01-equivalent gate)
Operator dispositions; no new findings outside in-cycle classified set; schema snapshot comparison; cycle closure markers; milestone audit. Mirrors v1.1 Phase 11 exactly. **Research flag: NO.**

### Phase Ordering Rationale

- Spike first: codegen approach is the single architectural unknown; planning Phase 3 without it is gamble-planning.
- Ergonomics before driver migration: `from_env()` simplifies Phase 2b driver migrations from `require_env(...)` + `Client()` dance to a single validated call.
- IOL disk persistence parallel with driver migration: independent files, zero overlap.
- Driver migration before codegen: migrated drivers validate the public method surface; API gaps surface locally before codegen masks them.
- LIVE gate last: single cost, validates all features simultaneously.
- Per-package serial within each phase (ambito → iol → higyrus → matriz): v1.0/v1.1 validated pattern.

---

## Open Questions / Spike Candidates

1. **unasync vs libcst go/no-go for matriz:** can token-replacement handle `asyncio.Lock` → `threading.Lock`, `async with`, `async def __aenter__`, `_get_async_lock()`? Or does matriz's 852-LOC `aio.py` require libcst AST-level rewrites?
2. **Codegen marker syntax:** does `# @generated by unasync...` at line 1 conflict with ruff's `from __future__ import annotations` requirement?
3. **ruff extend-exclude for generated files:** do generated `_sync/` files trigger `ASYNC1xx` rule violations?
4. **`from_env()` ship-or-skip:** operator decision; low-cost either way.
5. **IOL disk cache path:** `user_data_dir` (platformdirs persistent) vs `user_cache_dir` (XDG: regenerable). ARCHITECTURE recommendation: `user_data_dir`.
6. **CI Python 3.13 baseline confirmation:** v1.1 RETROSPECTIVE flagged this deferred 3× phases. Must confirm v1.1 baseline (`71bf201`) is green on 3.13 BEFORE Phase 1 lands (Pitfall 17).

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified via PyPI + Context7; keyring/cryptography rejection grounded in official headless CI docs |
| Features | HIGH | 7-SDK survey unambiguous on `from_env()`; `with_options()` confirmed via anthropic source inspection; IOL disk persistence pattern confirmed via msal-extensions + requests-oauthlib |
| Architecture | HIGH (codegen: MEDIUM) | v1.1 architecture fully validated (907 tests + LIVE-01 × 4); codegen invariants clearly defined; tool choice TBD via spike |
| Pitfalls | HIGH | All 17 pitfalls rooted in shipped v1.1 code with exact file:line citations; 4 HIGHEST-RISK have concrete regression test patterns |

**Overall: HIGH for Cluster 2 (ergonomics + IOL disk); MEDIUM for Cluster 1 (codegen)**

### Gaps to Address

- **Codegen tool choice:** Phase 0 spike is the gate. Roadmapper should treat Phase 3 as conditional.
- **CI Python 3.13 baseline confirmation:** must be confirmed pre-Phase-1 as `human_verification_pending` item.
- **`with_options()` `_transport` refactor scope:** ~15 LOC per package in `_transport.py` + `_atransport.py`; Phase 1 plan must scope it explicitly.
- **IOL disk cache path (`user_data_dir` vs `user_cache_dir`):** operator decision at Phase 2a plan time.
- **`from_env()` ship-or-skip:** operator decision before Phase 1 plan.

---

### Roadmap Implications Summary

- **Estimated phase count:** 5 (Spike + 3 work phases + LIVE gate); reduces to 4 if codegen deferred.
- **Per-package serial pattern carries forward:** ambito → iol → higyrus → matriz within each phase.
- **Spike flag placement:** Phase 0 (mandatory, hard go/no-go output for Phase 3).
- **Live gate placement:** Phase 4 (milestone close); per-package LIVE smoke at end of each Phase 2b sub-package.
- **In-cycle bug pattern carries forward:** findings from Phase 2b migrations or Phase 4 are classified and closed with regression tests in the same phase.
- **Parallelization opportunity:** Phase 2a (IOL disk) and Phase 2b (driver migration) can run as concurrent waves.
