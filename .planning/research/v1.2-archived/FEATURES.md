# Feature Research — v1.2 Architecture + Auth/Ergonomics Carry-forwards

**Domain:** Python HTTP client libraries (financial APIs) — driver migration to class instances, sync/async dedup via codegen, OAuth refresh-token disk persistence, cross-package `from_env()` + `with_options()` ergonomics
**Researched:** 2026-06-14
**Confidence:** HIGH (cross-referenced anthropic SDK source + openai SDK docs + unasync/unasyncd + psycopg3 codegen + msal/google-auth/authlib/requests-oauthlib + AzureAD msal-extensions + Python keyring)
**Scope note:** This document covers ONLY v1.2 NEW features. v1.0 + v1.1 already-built capabilities (verification harness, `Client`/`AsyncClient` classes with `_ClientState`, PEP 562 shim, `_core.py` builders/parsers, `RetryTransport`, `RedactingFilter`, append-only findings, matriz `aio.py`, IOL refresh_token in-instance lifecycle) are out of scope — see `.planning/research/v1.0-v1.1-archived/FEATURES.md` for the historical record.

---

## Executive Summary — What This Research Establishes

The six v1.2 target features split cleanly into two clusters:

**Cluster 1 (Arquitectura sync/async dedup, 3 features):**
1. Driver migration × 4 packages — table-stake correction of v1.1 architectural debt; pattern is well-known (side-by-side run + golden snapshot diff).
2. unasync/codegen single-source — **table stake for the SDK ecosystem at this layer of maturity** (psycopg3, httpcore, elastic-py, urllib3 all use it), but **a differentiator for this repo specifically** given the "no shared internals between packages" constraint and the already-shipped `_core.py` decoupling. Recommended **spike-before-plan** as PROJECT.md flags; spike outcome may demote this to anti-feature for v1.2 if the maintenance overhead exceeds the dedup payoff at 4-package scale.
3. Final live re-verification — table stake (LIVE-01-equivalent gate, already validated in v1.1 Phase 11).

**Cluster 2 (Auth/Token persistence + Client ergonomics, 3 features):**
4. IOL refresh_token disk persistence — table stake for OAuth refresh_token flows; well-established pattern (msal SerializableTokenCache + msal-extensions PersistedTokenCache, requests-oauthlib `token_updater` callback, authlib `update_token`). Cross-platform recommendation: encrypted via OS keychain (keyring) with JSON file fallback (0600 + advisory lock).
5. `Client.from_env()` × 4 packages — **NOT** the dominant industry convention. Anthropic, OpenAI, Mistral, Groq all do **implicit env-fallback in the constructor** (`Anthropic()` reads `ANTHROPIC_API_KEY` when no kwarg provided). A separate `from_env()` classmethod exists in some Java/Go SDKs but is rare in Python. **Decision required:** ship explicit `from_env()` classmethod as documented sugar OR follow the dominant `Client()` implicit env-fallback that v1.0/v1.1 already implement via `load_dotenv()`. Recommended path: **expose `from_env()` as an explicit alias for discoverability**, internally just calls `cls()` since `_ClientState.__init__` already reads env-via-dotenv (today's behavior, preserved).
6. `client.with_options(max_retries=N)` × 4 packages — **table stake** for modern Python SDKs (anthropic ships `copy()`/`with_options()` as alias; openai ships the same). Pattern is shallow-copy of the Client, share underlying `httpx.Client` + token cache + `_ClientState` references, override only the changed kwargs.

The single most important finding: **`with_options()` and `from_env()` should NOT mutate or recreate the underlying httpx.Client.** v1.1's existing `Client(http_client=...)` injection + `_state.http_client` lazy-create pattern is the right substrate. The new `with_options()` should produce a new `Client` instance that **shares** the same `httpx.Client` and `_ClientState` references (anthropic SDK explicitly: `http_client = http_client or self._client`; token cache shared unless credentials changed).

The single most important pitfall to bake in: **disk-persisted refresh_token across processes is a concurrent-write hazard.** Two parallel processes (driver + REPL, or two driver runs against the same `.env`) both refresh on token expiry, only one of the new refresh_tokens lands on disk, the other process's in-memory refresh becomes immediately invalid. msal-extensions solves this with a file lock + auto-reload-on-modification. v1.2 should adopt the same recipe; the v1.1 `TokenStore` 3-way concurrency primitive in matriz is the in-process precedent.

---

## Feature 1 — Driver Migration × 4 packages (`main_*.py` → `Client`/`AsyncClient` instances)

**Goal:** Rewrite `main_ambito.py`, `main_iol.py`, `main_higyrus.py`, `main_matriz.py` to construct and consume `Client(...)` / `AsyncClient(...)` instances directly instead of calling the top-level `pkg.get_X(...)` shim functions. Closes v1.1 SC#3 LOC-drop residual (iol -5.1%, matriz client.py -20%).

### 1.1 Table Stakes

| Sub-feature | Why Expected | Complexity | Reference impl |
|---|---|---|---|
| Drivers instantiate `Client(...)` / `AsyncClient(...)` once at top of `main()` | Today's drivers call module-level `iol_client.get_X(...)` which delegates through PEP 562 shim to `_get_default()` — an extra indirection that exists ONLY to preserve back-compat for external consumers. The driver itself has zero reason to use the shim. | M (per package) | Internal pattern; aligns with anthropic example apps which never use module-level helpers, always explicit `Anthropic()`. |
| Driver explicitly closes / uses context manager | v1.1 already exposes `with Client() as c: ...` and `async with AsyncClient() as c: ...`. Drivers should follow the documented lifecycle. | S | Same as v1.1 Client class (Phase 6). |
| Single shared instance per surface (sync/async) per driver | The v1.0/v1.1 model is "one logical session per driver run with cached token". A new `Client()` per probe would defeat token caching and explode auth load. | S | Reuse the same `client` across all 15-25 probes (matches today's behavior since the singleton was shared). |
| INT-01 idiom replaced with direct instance access | After migration, `iol_client.client._get_default()._state.base_url` becomes `client._state.base_url` directly. The 15+ INT-01 sites in `main_iol.py` collapse to instance reads. | S | Pattern documented in v1.1 quick-task 260613-nwb. |
| Driver retains `--live` gate, redaction, mutation_gate semantics | These are v1.0 invariants, package-instance change must not regress them. | S | No-op; harness `verification/*` is independent. |
| Side-by-side run before cutover (driver-vs-driver diff) | Standard CLI-migration pattern (golden master / snapshot). Run old driver, capture findings.md + schemas + summary; run new driver against same env, diff. Zero-diff = green. | S | Industry-standard golden snapshot pattern: capture output, persist, diff on rewrite. v1.0/v1.1 already use schema snapshots for the API itself; this extends the pattern to driver output. |
| Per-package serial migration order | v1.0/v1.1 pattern: ámbito (smallest) → iol → higyrus → matriz (largest). Each package isolated, errors don't cascade. | S | PROJECT.md decision row "Per-package serial pattern". |

### 1.2 Differentiators

| Sub-feature | Value | Complexity | Notes |
|---|---|---|---|
| Keep bare `main_*.py` smoke-test variant + class-based comprehensive driver | Some operators want a "literally just `Client().login()`" 5-line smoke-test for ops/health-check; others want the 25-probe comprehensive driver. Two files per package (e.g., `main_iol_smoke.py` + `main_iol.py`) covers both. | M | NOT recommended for v1.2 — adds 8 files to the repo. Defer; the `main_*.py` smoke variant was the v1.0 starting point and there's no operator requirement to bring it back. |
| Run sync + async in a single `main()` with interleaved probes (LIVE-02 matriz pattern) | v1.1 Phase 10 LIVE-02 paired 19 probes sync/async in one `asyncio.run()`. Same pattern applies to the other 3 drivers. | M | Already done in `main_matriz.py`; remaining 3 drivers may or may not follow. Not table stake — current driver shape works fine. |

### 1.3 Anti-Features

| Anti-feature | Why rejected for v1.2 | Alternative |
|---|---|---|
| Rewriting driver as pytest test suite | Driver is operator-driven manual cycle, not CI-test. v1.0/v1.1 ratified `main_*.py` as the operator entry point with classified findings + schema snapshots. Rewriting as pytest would lose the operator-readable summary output, the classification taxonomy, and the cycle baseline. | Keep driver shape as `main_*.py` with the v1.1 `verification/findings.py` append-only API. |
| Breaking the top-level `pkg.get_X(...)` shim during migration | Driver migration is internal; the PEP 562 shim exists for **external** consumers. Removing the shim would be a major version break. PROJECT.md "Non-breaking constraint" explicit. | Driver migrates to instance API; shim stays. External callers unaffected. |
| Single mega-driver `main.py` calling all 4 packages | Cross-package coupling violates the "no shared internals" constraint and breaks per-package serial. | Keep 4 separate `main_*.py` files. |
| Parametrized driver via CLI flags (`--probe-set basic|comprehensive`) | Adds CLI surface that nobody asked for; complicates operator workflow. | Drivers stay as fixed probe sets; operator overrides via env vars (already supported: `VERIFY_IOL_BAD_CREDS=1` etc.). |

**Dependencies:** v1.1 `Client`/`AsyncClient` classes (Phase 6), `_ClientState` (Phase 6), PEP 562 shim (Phase 6), `verification/findings.py` append-only (Phase 11). Mocked vs live: migration uses live (LIVE-01-equivalent gate at end of milestone).

**Reference behavior:** anthropic-sdk-python `examples/` directory always uses explicit `Anthropic()` instantiation, never module-level helpers. Same target shape.

---

## Feature 2 — unasync/codegen Single-Source Sync/Async

**Goal:** Eliminate the structural dual-maintenance of `client.py` + `aio.py` per package — generate one from the other at build time (or via pre-commit hook). v1.1 Phase 7 collapsed both surfaces to transport shells calling `_core.py`, but each package still has TWO shells.

### 2.1 Table Stakes (in the broader ecosystem)

| Sub-feature | Why Expected | Complexity | Reference impl |
|---|---|---|---|
| Async-first single source, sync generated from async | psycopg3 documented pattern (AST-based codegen tool maintained in-tree). httpcore + urllib3 + elasticsearch-py use unasync (async source → sync emit) at build time. | M-L | [psycopg3 async-to-sync article](https://www.psycopg.org/articles/2024/09/23/async-to-sync/) — AST-based, "uses it to maintain the Psycopg 3 codebase". |
| Build-time generation, generated file checked into git | Standard practice — keeps `pip install` simple, allows reviewers to read both surfaces. unasync `setup.py cmdclass`; unasyncd `pre-commit` hook. | S-M | unasync default workflow (`build_py` hook). |
| Token-based OR AST/libcst-based transform | unasync = token-based, simple but limited. unasyncd = libcst-based, handles `AsyncExitStack → ExitStack`, per-function exclusions. | M-L for unasyncd | [unasyncd 0.10.0 (Jan 2026)](https://pypi.org/project/unasyncd/) supports per-file exclusions, docstring transforms, fully-qualified name disambiguation. |
| Per-block/per-function exclusion mechanism | Sync-only or async-only blocks need a way to opt out (e.g., `_token_store.py` 3-way concurrency primitive cannot be auto-generated). | M | unasyncd: `# unasyncd: skip` comments. unasync: no native support; requires file-level separation. |

### 2.2 Differentiator (for THIS repo at THIS scale)

| Sub-feature | Value | Complexity | Notes |
|---|---|---|---|
| Adopt **unasyncd** as build tool for the 4 packages | Eliminates the "fix in client.py and aio.py" dual-edit burden that caused v1.0/v1.1 bugs (envelope keys, %2F encoding, refresh_token path). | L (per-package wiring + test infrastructure changes) | **Spike required.** v1.1's `_core.py` extraction already moved 80% of duplication out; the remaining shells are ~30-50 LOC per endpoint. Net savings: ~150-300 LOC across 4 packages. Cost: a generator + per-package config + CI integration + reviewer cognitive load + "regenerate vs hand-edit" debug confusion. |
| Adopt **unasync** (simpler, token-based) | Less infrastructure overhead; matches httpcore/elastic-py pattern | M | Cannot handle matriz `TokenStore` 3-way concurrency primitive cleanly (threading vs asyncio differ structurally). Likely requires hybrid: unasync for "thin shells", hand-maintained for `_token_store.py` / `_refresh_policy.py`. |

### 2.3 Anti-Features (likely outcomes of the spike)

| Anti-feature | Why may be rejected for v1.2 | Alternative |
|---|---|---|
| Sync-first source, async generated | Async semantics (await placement, async context managers, async iterators) cannot be **introduced** by codegen — you can only **remove** them. Industry consensus: async is the source of truth. | If adopted at all, async-first. |
| Mixing codegen with hand-maintained per-package | Splits maintenance into "what's gen'd vs what's hand-edited" — reviewers can't tell at a glance which file is which. Error-prone. | All-or-nothing per package; OR mark generated files with a `# DO NOT EDIT — generated from ...` header at the top. |
| Adopting unasync/unasyncd in v1.2 without a spike | PROJECT.md explicitly flagged spike-before-plan. v1.1 RETROSPECTIVE confirmed spike-before-plan worked (TokenStore Phase 10). Skipping the spike risks delivering 4× the work for marginal LOC dedup. | Run a focused 1-2 day spike on iol-client (single package): generate aio.py from client.py (or vice versa); measure LOC delta, CI-time delta, reviewer-effort delta. Decide go/no-go for the other 3 packages. |
| Replacing `_core.py` builders/parsers with codegen | `_core.py` is already pure, already shared between client.py + aio.py, already protected by import-linter contracts. It's not the duplication target. | Codegen targets the transport shells (`client.py` ↔ `aio.py`), not `_core.py`. |
| Auto-generating `_token_store.py` (matriz) | The 3-way concurrency primitive has structurally different sync/async paths (threading.Lock callable from asyncio context). Generator cannot synthesize the `asyncio.to_thread` offload. | Hand-maintained, with `# unasyncd: skip` or file-level exclusion. |

**Recommendation:** **DIFFERENTIATOR with mandatory spike.** Do not commit to v1.2 codegen adoption without a spike on iol-client showing measurable LOC reduction + sustainable maintenance overhead. PROJECT.md spike-before-plan flag is already activated; honor it. Likely v1.2 outcome: spike validates feasibility but operator decides codegen-overhead > dedup-payoff at 4-package scale, and feature is deferred to v1.3 or rejected.

**Dependencies:** v1.1 `_core.py` per package (Phase 7), v1.1 `_transport.py`/`_atransport.py` (Phase 8 + 10), v1.1 matriz `aio.py` (Phase 10). Mocked vs live: codegen verified by mocked test parity (sync + async tests must produce identical results); LIVE-01-equivalent re-verification at milestone end.

**Reference behavior:** [psycopg3 generator script (AST-based)](https://www.psycopg.org/articles/2024/09/23/async-to-sync/); [unasync (token-based, urllib3/httpcore/elastic-py)](https://github.com/python-trio/unasync); [unasyncd (libcst-based, more powerful)](https://pypi.org/project/unasyncd/).

---

## Feature 3 — Final Live Re-Verification × 4 packages (LIVE-01-equivalent gate)

**Goal:** Run all 4 migrated drivers against live APIs at milestone close; operator dispositions; no new findings outside the in-cycle classified set.

### 3.1 Table Stakes

| Sub-feature | Why Expected | Complexity | Reference impl |
|---|---|---|---|
| Run `main_*.py` × 4 in `--live` mode | Closes the loop on driver migration: behavior observed live = behavior before migration. | S | v1.1 Phase 11 LIVE-01 already ran this gate; v1.2 repeats post-driver-migration. |
| Operator disposition CONFIRMED/FIXED/EXPECTED/NO-FIX per finding | v1.0 taxonomy carried forward through v1.1. | S | `verification/findings.py` API. |
| Schema snapshots compared to baseline (no drift) | DRIFT-01 mirror pattern. v1.0/v1.1 cycles. | S | `.planning/verification/schemas/<pkg>/*.json`. |
| Cycle closure marker (no new findings = no_new_findings disposition) | v1.1 Phase 11 ratified this disposition. | S | Operator records in PHASE-VERIFICATION.md / VALIDATION.md frontmatter. |

### 3.2 Differentiators

| Sub-feature | Value | Complexity | Notes |
|---|---|---|---|
| Quantitative driver-output diff: old vs new run (golden master) | Side-by-side comparison demonstrates the migration didn't drift the observable behavior. | M | Capture findings.md hash, schema hashes, summary line counts on pre-migration baseline; compare to post-migration. Best-practice "golden snapshot test on the CLI tool". |

### 3.3 Anti-Features

| Anti-feature | Why rejected | Alternative |
|---|---|---|
| Promoting driver runs to CI (live every commit) | Live APIs have rate limits, business-hours dependencies, credentials in CI = risk. v1.0 ratified `@pytest.mark.live` + `--live` opt-in for exactly this reason. | Operator-driven gate at milestone close; mocked tests in CI. |
| Auto-classifying findings without operator | v1.0/v1.1 explicitly operator-driven; v1.1 BUG-02 (NO-FIX bucket (a) after live N=3 triage) is the canonical example of why human judgment is required. | Operator classifies; driver only writes raw observation. |

**Dependencies:** Feature 1 (drivers migrated), v1.1 `verification/findings.py` (Phase 11), v1.1 schema snapshot baseline (DRIFT-01).

---

## Feature 4 — IOL refresh_token Disk Persistence

**Goal:** Persist the IOL OAuth `refresh_token` to disk so that across-process restarts (driver re-runs, CLI exits, REPL session ends) the next login can use the refresh path instead of re-prompting password grant. v1.1 BUG-03 closed the in-instance lifecycle; this closes the cross-process leg.

### 4.1 Table Stakes

| Sub-feature | Why Expected | Complexity | Reference impl |
|---|---|---|---|
| Token cache abstraction (interface, not concrete class) | Industry pattern: msal `TokenCache` base + `SerializableTokenCache` + msal-extensions `PersistedTokenCache`. Pluggable backends. | M | [msal.token_cache.SerializableTokenCache](https://learn.microsoft.com/en-us/python/api/msal/msal.token_cache.serializabletokencache). |
| OS keychain integration (preferred backend) | Most secure cross-platform: macOS Keychain, Windows Credential Manager, Linux Secret Service. v1.1 spike-findings memory cites "secure token storage" as the goal. | M | [Python `keyring` package](https://keyring.readthedocs.io/) — system-credential-store via stable cross-platform API. Used by google-cloud-sdk, AzureCLI (via msal-extensions), GitHub CLI, others. |
| JSON file fallback (when keyring unavailable) | Headless servers, CI, Docker without keyring daemon. Standard fallback pattern. | M | Encrypted via msal-extensions `PersistedTokenCache` (Windows DPAPI / macOS Keychain / Linux LibSecret). For market-libs simpler fallback: plain JSON with 0600 + advisory lock. |
| File locking on read/write | **Critical:** two processes refreshing the same refresh_token race the disk write; whichever lands last "wins" and the other process's in-memory refresh_token becomes invalid. msal-extensions uses portalocker. requests-oauthlib `token_updater` callback recommends file lock. | M | msal-extensions: "Concurrent data access will be coordinated by a file lock mechanism". |
| Auto-reload on file mtime change | Process A refreshes → writes new refresh_token. Process B should detect the file change and reload before its next refresh, instead of using the stale in-memory copy. | M | msal-extensions `PersistedTokenCache` "includes a file lock, and auto-reload behavior under the hood". |
| 0600 file permissions on POSIX | Standard secret-storage discipline. | S | All OAuth SDKs and SSH `id_rsa` ratify the convention. |
| Configurable cache path with sane default | Default to `~/.cache/iol-client/token.json` (XDG cache spec) OR `$XDG_DATA_HOME/iol-client/token.json` for persisted secrets. Allow override via env or kwarg. | S | google-cloud-sdk uses `~/.config/gcloud/`; msal-extensions uses `~/.cache/{appname}` on Linux. |
| Refresh_token rotation on success preserved (v1.1 D-IOL-10 conditional-rotation) | IOL server MAY rotate the refresh_token on each `/token` POST. v1.1 BUG-03 CR-01 preserves the cached refresh_token when the server omits a new one. This invariant carries to disk: write new refresh_token only if the server returned a non-None value. | S | v1.1 `_core.parse_refresh_response` already returns `Optional[str]`. |
| Tests cover the 4 lifecycle paths from v1.1 BUG-03 | (a) refresh success → token + refresh_token persisted; (b) refresh 401 → fallback to password grant + new refresh_token persisted; (c) server returns no new refresh_token → preserve cached; (d) server rotates → write rotated. | M | v1.1 added 8 regression tests (4 sync + 4 async) for the in-instance lifecycle; v1.2 mirrors the same 4 paths on disk persistence. |
| Disk persistence is opt-in (env var or kwarg) | Default behavior unchanged for callers who don't want disk-touch. **Tests** especially must not accidentally create disk caches. | S | `Client(token_cache=DiskTokenCache(...))` explicit; or env var `IOL_TOKEN_CACHE_PATH`. |

### 4.2 Differentiators

| Sub-feature | Value | Complexity | Notes |
|---|---|---|---|
| Pluggable `TokenCache` interface (abstract base) | Lets advanced users substitute Redis, database, custom storage. | M | msal pattern. P2 — useful but not required for v1.2 since IOL is the only refresh_token-bearing package. |
| Encrypted-at-rest fallback for the JSON file (when keyring unavailable) | Defense-in-depth on shared filesystems. | L | msal-extensions provides this. v1.2: rely on keyring as primary (encrypted by OS) + 0600 JSON as fallback (unencrypted but file-locked). |
| Multi-user / multi-tenant key namespace | If a host has multiple IOL accounts (one per OS user), keyring entries scoped by username already. JSON file path should include username when `~/.cache/iol-client/{user}.json`. | S | Convention: cache key = `(service="iol-client", username=IOL_USER)` for keyring; for JSON, filename derived from username hash. |
| Token expiration metadata persisted alongside refresh_token | Avoid wasteful "try refresh, get 401, fall back to password" on a known-expired token. Persist `token_expires_at` + cached `access_token`. | S | All major SDKs do this; msal `SerializableTokenCache` schema includes expiry. |

### 4.3 Anti-Features

| Anti-feature | Why rejected | Alternative |
|---|---|---|
| Plaintext refresh_token in `.env` file | CLAUDE.md security constraint: "nunca commitear .env ni exponer credenciales en logs, reportes o tests". Operator may write the long-lived refresh_token to `.env` thinking it's the same as password, but `.env` is committed-adjacent and shows up in shell history. | Disk cache lives **outside** the repo (in `~/.cache/iol-client/` or keyring). Never read refresh_token from `.env`. |
| Refresh_token logged on acquisition / refresh / failure | v1.1 `RedactingFilter` already redacts; disk persistence must not bypass. Disk write is OK; log lines about disk write must not include the secret value. | Logger emits `auth.refreshed event=disk_write` with no token value; redact in formatter as belt-and-suspenders. |
| Persisting access_token on disk | Short-lived (15 min IOL TTL); risk/benefit poor — disk-cached access_token may already be expired by the time the next process loads it. | Persist refresh_token only (+ optionally `token_expires_at` for the access_token, which lets the new process know whether the cached access_token is fresh enough to skip auth). |
| Disk persistence ON by default | Surprises tests and users who don't expect file-system side effects. v1.0/v1.1 default = ephemeral in-process. | Opt-in via kwarg `Client(token_cache=...)` or env `IOL_TOKEN_CACHE_PATH=...`. |
| Inter-process IPC token broker daemon | Way over-engineered for a 1-user OAuth client. msal-extensions file lock + auto-reload is the right granularity. | File lock + auto-reload. |
| Cross-package shared cache (one cache for all 4 packages) | iol, higyrus, matriz, ámbito use different auth flows. Sharing a cache across them violates the "no shared internals" architectural constraint. | Per-package cache file. Only `iol-client` gets the disk-persistence feature in v1.2 because only IOL has OAuth refresh_token. Other packages: deferred. |

**Dependencies:** v1.1 `_ClientState.refresh_token` (Phase 6), v1.1 `_core.parse_refresh_response` (Phase 7), v1.1 BUG-03 in-instance lifecycle tests (Phase 9), v1.1 `RedactingFilter` (Phase 8 LOG-01), v1.1 `_TokenStore` 3-way concurrency primitive (Phase 10 — pattern reusable for the disk lock). New runtime dep: **`keyring` (Apache-2.0, py.typed)** — adds 1 dep to iol-client only. Mocked vs live: lifecycle paths (a)-(d) tested mocked + 1 live end-to-end pass.

**Reference behaviors:**
- [msal.token_cache.SerializableTokenCache](https://learn.microsoft.com/en-us/python/api/msal/msal.token_cache.serializabletokencache) — base serialization interface; **does NOT persist on its own** (callers wire serialize/deserialize).
- [msal-extensions PersistedTokenCache](https://github.com/AzureAD/microsoft-authentication-extensions-for-python) — disk persistence + file lock + auto-reload + OS-specific encryption (DPAPI/Keychain/LibSecret).
- [requests-oauthlib `token_updater` callback](https://requests-oauthlib.readthedocs.io/en/latest/examples/real_world_example_with_refresh.html) — callback fires on auto-refresh; caller writes to disk.
- [google.oauth2.credentials.Credentials](https://googleapis.dev/python/google-auth/1.7.2/reference/google.oauth2.credentials.html) — refresh_token + token_uri + client_id + client_secret required; persistence is caller responsibility.
- [Python `keyring`](https://keyring.readthedocs.io/) — system-keyring abstraction.

---

## Feature 5 — `Client.from_env()` Classmethod × 4 packages

**Goal:** Explicit, discoverable factory that reads credentials + base_url from environment. Today's behavior: `Client()` already reads env via `load_dotenv()` + `_ClientState` defaults. The proposal asks whether a separate `from_env()` is needed.

### 5.1 What the Ecosystem Actually Does (FINDING)

| SDK | Constructor reads env? | `from_env()` classmethod? | Env var convention |
|---|---|---|---|
| anthropic-sdk-python | YES (implicit when no kwarg) | NO | `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, …(6+ env vars enumerated in source) |
| openai-python | YES (implicit) | NO | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_ORG_ID` |
| stripe-python | YES (`stripe.api_key = os.environ.get(...)` module-level) | NO | `STRIPE_API_KEY` |
| mistralai | YES (`api_key=os.getenv("MISTRAL_API_KEY", "")`) | NO | `MISTRAL_API_KEY` |
| groq-python | YES (`api_key=os.environ.get("GROQ_API_KEY")`) | NO | `GROQ_API_KEY` |
| cohere | YES (implicit) | NO | `CO_API_KEY` |
| google-genai | YES (implicit, via ADC) | NO | `GOOGLE_API_KEY`, ADC path |

**Conclusion:** `from_env()` classmethod is **NOT** the dominant Python SDK convention. The dominant convention is **implicit env fallback in the constructor**. The market-libs v1.0/v1.1 implementation already does this (via `load_dotenv()` + `_ClientState` defaults).

### 5.2 Table Stakes (implicit env fallback — already implemented in v1.1)

| Sub-feature | Status in v1.1 | Notes |
|---|---|---|
| `Client()` (no kwargs) reads env vars and constructs default state | ✓ implemented (Phase 6) | `_ClientState` `__post_init__` calls `os.getenv(...)` for `IOL_USER`/`IOL_PASSWORD`/`IOL_BASE_URL` (and equivalents per package). |
| `load_dotenv()` called at module import time | ✓ implemented (v1.0, preserved) | Every package's `client.py` calls `load_dotenv()` at module level. |
| Explicit kwargs override env | ✓ implemented (Phase 6) | `Client(base_url=...)` wins over env. |
| `configure(base_url=...)` mutates the default-client state without rebuild | ✓ implemented (v1.0 preserved through Phase 6) | Pattern stable; tests rely on it. |
| Missing required env vars raise typed `<Pkg>AuthError` on first auth call | ✓ implemented (lazy — error at login(), not at Client() construction) | Convention matches anthropic/openai (constructor doesn't raise; first call does). |

### 5.3 Differentiator (v1.2 proposal: explicit `from_env()` as documented sugar)

| Sub-feature | Value | Complexity | Notes |
|---|---|---|---|
| `Client.from_env()` classmethod that returns `cls()` (just an alias) | Discoverability — appears in IDE autocomplete; signals intent in code review (`Client.from_env()` is clearly env-based, `Client()` is ambiguous). | S | Implementation: 5 lines per package. `@classmethod def from_env(cls) -> Self: return cls()`. Documented in docstring as "explicit alias for the implicit env-fallback constructor". |
| `Client.from_env(prefix="IOL")` with explicit prefix | Some apps want `IOL_PROD_USER` / `IOL_STAGING_USER` discriminated by prefix. | M | NOT recommended for v1.2 — env vars are hardcoded per package; multi-env separation belongs to the caller (use multiple `.env` files + `dotenv_path=`). |
| `Client.from_env(env_file="...")` | Some apps want to point at a specific `.env` file. | M | NOT recommended for v1.2 — `python-dotenv` already supports this via `load_dotenv(dotenv_path=...)` which the caller can invoke before `Client.from_env()`. |
| `Settings`/`BaseSettings` pydantic-style validation | Type-safe env var loading with validation. | L | NOT recommended for v1.2 — adds pydantic to runtime deps of 4 publishable wheels, violates "no shared deps" constraint and "zero-dep additions" preference (v1.1 added only tenacity, which is zero-deps). |
| `Client.from_env()` raises if required env vars missing (vs deferring to first call) | Anthropic explicitly defers ("constructor doesn't raise"); openai same. Fail-fast variant is non-standard. | S | NOT recommended for v1.2 — diverges from ecosystem convention; v1.0 behavior (deferred AuthError on `login()`) is correct. |
| Keyring fallback for credentials in `from_env()` | If `IOL_USER`/`IOL_PASSWORD` not in env, try `keyring.get_password("iol-client", "credentials")`. | M | NOT recommended for v1.2 — keyring scope is the refresh_token disk persistence (Feature 4); extending to primary password adds complexity for marginal gain. Defer to v1.3. |

### 5.4 Anti-Features

| Anti-feature | Why rejected | Alternative |
|---|---|---|
| Removing the implicit env fallback in the bare `Client()` constructor | Backwards-incompatible. v1.1 PEP 562 shim relies on `_get_default()` constructing from env. | Keep implicit fallback; add `from_env()` as alias only. |
| `from_env(strict=True)` raising on missing env (default fail-fast) | Diverges from ecosystem convention; surprises callers; breaks lazy-auth pattern of v1.0/v1.1. | Keep lazy (raises on first `login()`); doc the behavior. |
| Per-package different `from_env()` signatures | Ergonomic mismatch across the 4 packages. | All 4 packages expose identical `Client.from_env() -> Self`. |
| `from_env()` reading credentials from outside `.env` (e.g., `~/.config/iol-client.toml`) | Out of scope for v1.2; conflates Feature 4 (token disk persistence) with credential discovery. | v1.2: `from_env()` reads env vars only (which dotenv populates). Future: separate `from_config_file()` if needed. |

**Conclusion:** `from_env()` is **NOT table stakes** (ecosystem convention is implicit env fallback in constructor, which v1.1 already does). Recommend ship it as a **documented alias** for discoverability — low-cost addition that doesn't break anything but doesn't enable anything new either. Operator decision required: do we want to ship the alias, or just document that `Client()` reads env (status quo)?

**Dependencies:** v1.1 `Client` constructor with optional kwargs (Phase 6), v1.1 `_ClientState` defaults from env (Phase 6), `load_dotenv()` module-level (v1.0). Mocked vs live: tests verify `from_env()` returns equivalent instance to `Client()` with matching env vars set.

**Reference behavior:** anthropic-sdk-python `Anthropic()` constructor (NO `from_env()`); openai-python `OpenAI()` constructor (NO `from_env()`).

---

## Feature 6 — `client.with_options(max_retries=N)` per-call Override × 4 packages

**Goal:** Operator can override `max_retries` (or other client options) for a single call without mutating the long-lived `Client` or instantiating a new one with full credential re-pass.

### 6.1 Table Stakes

| Sub-feature | Why Expected | Complexity | Reference impl |
|---|---|---|---|
| `with_options()` returns a new `Client` instance | Anthropic + OpenAI both. Method signature: `with_options(**kwargs) -> Self`. Implementation: clone state, override kwargs, return new instance. NOT a mutating method. | M | [anthropic-sdk-python `copy()`/`with_options()`](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_client.py). |
| `copy()` is an alias for `with_options()` | Anthropic explicit. OpenAI ships `with_options()`. | S | `with_options = copy` (anthropic). v1.2 recommendation: ship both names. |
| New instance **shares** the underlying `httpx.Client` (when not overridden) | Anthropic: `http_client = http_client or self._client`. Avoids tearing down + rebuilding the connection pool for an option-flip. | M | Anthropic explicit; same recipe. |
| New instance **shares** the token cache / `_ClientState` (when credentials unchanged) | Anthropic: token cache passed via `_extra_kwargs` when `credentials is NotGiven`. Avoids re-auth for a `max_retries` flip. | M | Anthropic explicit. For market-libs: share `_state` reference when credential kwargs not changed. |
| New instance gets a fresh `_state` (with fresh token cache) when credentials change | Anthropic: skips the `_token_cache` reuse when `credentials=` is explicitly passed. | M | Same. v1.2: if `with_options(username=...)` or `password=` provided, build fresh `_ClientState`. |
| Overridable kwargs at least: `max_retries`, `timeout`, `base_url`, `http_client` | These are the per-call-tunable surface. | M | Anthropic supports all four + headers + query + middleware. |
| Per-call usage pattern: `client.with_options(max_retries=5).get_quote("GGAL")` | Fluent. Anthropic ships this exact shape. | S | Operator recipe documented. |
| `with_options(max_retries=N)` does NOT re-trigger token fetch | Critical: shared token cache means no auth round-trip for an options flip. | S | Inherits from shared `_state` reference. |
| Validation of `max_retries` int + non-negative | v1.1 WR-06 already enforces this on the constructor; `with_options()` inherits the same `_validate_max_retries()` helper. | S | Reuse v1.1 helper. |

### 6.2 Differentiators

| Sub-feature | Value | Complexity | Notes |
|---|---|---|---|
| Per-call timeout via `with_options(timeout=30.0)` | Useful for one-off batch calls (e.g., bulk historical_quotes). | S | Cheap; same code path as max_retries override. v1.2 recommendation: ship together. |
| Per-call headers via `with_options(default_headers={...})` | Custom user-agent, trace-ID per probe. | M | NOT recommended for v1.2 — `default_headers` substrate doesn't exist in `_ClientState` today; adding it is a separate change. Defer. |
| Per-call `http_client=` override | Already supported on constructor; with_options should propagate. | S | Inherits trivially from clone semantics. |
| `client.with_options(max_retries=0).new_order(...)` for matriz mutating calls | Operator-controllable "no retry" for mutating ops, complementing the v1.1 mutation gate. | S | Cross-cuts Feature 6 + v1.1 retry layer (which already disables retry for `idempotent=False`). Marginal utility since `idempotent=False` already prevents retry. |
| Weak references in clones (anthropic SDK does this) | Avoid memory leaks when many short-lived clones are created. | M | NOT recommended for v1.2 — typical use case is 1-2 clones per driver run, not thousands. Premature optimization. Document as future consideration if usage patterns demand it. |

### 6.3 Anti-Features

| Anti-feature | Why rejected | Alternative |
|---|---|---|
| `with_options()` mutates `self` in place | Would surprise callers; violates the ecosystem convention. | Returns new instance. |
| `with_options()` creates a fresh `httpx.Client` per call | Wasteful: tearing down a connection pool to flip `max_retries` is absurd. | Share underlying `httpx.Client`; new `_max_retries` field on the clone. |
| `with_options()` resets the token cache | Forces re-auth on every option flip; defeats purpose. | Share token cache when credentials unchanged. |
| `with_options()` accepting arbitrary `**kwargs` | Silent typos (`with_options(max_retires=5)` no-ops) | Explicit signature: `with_options(*, max_retries: int | None = None, timeout: ... = None, base_url: ... = None, http_client: ... = None) -> Self`. |
| `with_options()` chained mutation across multiple endpoints in same call site | Confusing semantics; what if intermediate calls produce side effects? | One clone per logical scope; if multi-endpoint, bind to a local: `c = client.with_options(max_retries=5); c.get_quote(...); c.get_instruments(...)`. |
| Per-call retry that ignores the mutation gate | Would let operator override the v1.1 "no retry on mutating ops" invariant via `with_options(max_retries=5).new_order(...)`. | v1.1 mutation gate is enforced at the **transport** (`request.extensions["idempotent"]`), NOT at the client. `with_options(max_retries=N)` increases attempts only for requests where the transport decides retry-eligibility. Mutating ops with `idempotent=False` still see 0 retries regardless of `max_retries=99`. **This invariant must be preserved and documented.** |
| Per-call override of `idempotent` flag | Same as above — only path to override mutation gate is the existing `mutating_allowed` double-gate in `verification/`, not the client. | No. |

**Dependencies:** v1.1 `Client.__init__` with `max_retries` + `http_client` kwargs (Phase 8 RELY-01..04), v1.1 `_ClientState` (Phase 6), v1.1 `_validate_max_retries` helper (Phase 8 WR-06), v1.1 `RetryTransport`/`AsyncRetryTransport` with idempotent gate (Phase 8 + 10). Mocked vs live: `with_options(max_retries=0)` mocked test (no retry on transient 5xx), `with_options(max_retries=5)` mocked test (5 retries observed), per-call clone identity test (`client is not client.with_options(max_retries=5)`).

**Reference behavior:**
- [anthropic-sdk-python `copy()`/`with_options()`](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_client.py) — shallow clone, shared http_client + token cache, override kwargs.
- [openai-python `client.with_options(max_retries=5, timeout=30.0)`](https://github.com/openai/openai-python/discussions/795) — same pattern.

---

## Feature Categorization Summary (one-line per feature)

| # | Feature | Category | Complexity | Reference impl |
|---|---|---|---|---|
| 1 | Driver migration × 4 → `Client`/`AsyncClient` instances | **Table stake** | M per package | Internal pattern; anthropic examples never use module-level helpers |
| 2 | unasync/codegen single-source sync/async | **Differentiator** (mandatory spike) | L | psycopg3 codegen; unasync (urllib3/httpcore/elastic-py); unasyncd (libcst) |
| 3 | Final live re-verification × 4 | **Table stake** | S | v1.1 LIVE-01 (Phase 11) |
| 4 | IOL refresh_token disk persistence | **Table stake** for OAuth refresh-token flow | M-L | msal-extensions PersistedTokenCache; keyring; requests-oauthlib token_updater |
| 5 | `Client.from_env()` × 4 | **Optional alias** (NOT industry table stake) | S | NO ecosystem convention; anthropic/openai/mistral/groq use implicit env fallback in constructor — v1.1 already does this |
| 6 | `client.with_options(max_retries=N)` × 4 | **Table stake** for modern Python SDKs | M | anthropic `copy()`/`with_options()`; openai `with_options()` |

---

## Feature Dependencies

```
[Feature 1: Driver migration]
    └──prerequisite──> [Feature 3: Final live re-verification]
                              (drivers must be migrated before final gate)

[Feature 1: Driver migration]
    └──independent of──> [Feature 2: unasync/codegen]
                              (driver-level migration vs library-internal codegen)

[Feature 2: unasync/codegen]
    └──spike-before-plan──> [decision: adopt v1.2 / defer v1.3 / reject]
                              (PROJECT.md flag active)

[Feature 4: IOL disk persistence]
    └──builds on──> [v1.1 BUG-03 in-instance lifecycle]
                              (Phase 9 closed in-process; v1.2 closes cross-process)
    └──reuses pattern──> [v1.1 _TokenStore Phase 10]
                              (file lock + concurrent access)

[Feature 5: from_env() alias]
    └──no-op on top of──> [v1.1 _ClientState env defaults]
                              (purely documentation)

[Feature 6: with_options()]
    └──builds on──> [v1.1 Client.__init__ kwargs (Phase 8)]
                              (max_retries + http_client constructor kwargs already exist)

[Feature 6: with_options()]
    └──must preserve──> [v1.1 mutation gate (Phase 8 RELY-01..04)]
                              (per-call max_retries cannot override idempotent=False)
```

---

## MVP Definition (v1.2 = this milestone)

### Must Land In v1.2

- [ ] **Feature 1** (table stake): Driver migration × 4 packages. Per-package serial ámbito → iol → higyrus → matriz. Each migration closes with a side-by-side run (old driver vs new driver) producing zero observable-behavior diff (mocked + smoke-live). Closes v1.1 SC#3 LOC-drop residual.
- [ ] **Feature 3** (table stake): Final live re-verification × 4 packages at milestone close (LIVE-01-equivalent). Operator disposition; no new findings outside in-cycle classified set.
- [ ] **Feature 4** (table stake): IOL refresh_token disk persistence with keyring backend + JSON file fallback + file lock + auto-reload + 0600 + opt-in. 8+ regression tests covering the 4 lifecycle paths from v1.1 BUG-03 mirrored on disk.
- [ ] **Feature 6** (table stake): `client.with_options(max_retries=N, timeout=..., base_url=..., http_client=...)` × 4 packages. Shallow clone, shared `_state` + `http_client` when not overridden. Returns new instance. `copy()` alias. Per-call retries preserve mutation gate invariant.

### Spike-Before-Plan (decision pending)

- [ ] **Feature 2** (differentiator with mandatory spike): unasync/codegen single-source sync/async. Spike on iol-client only; measure LOC delta, CI-time delta, reviewer-effort delta. Operator go/no-go before v1.2 phase planning commits.

### Optional / Documentation Sugar

- [ ] **Feature 5** (optional alias): `Client.from_env()` classmethod that calls `cls()`. Pure discoverability; no functional change. Ship if operator wants the discoverability win; skip if operator considers it noise (v1.1 implicit env fallback is already industry standard).

### Defer To v1.3+ (already documented in PROJECT.md)

- [ ] prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff)
- [ ] `matriz_client.ws_client` live verification (WebSocket layer)
- [ ] `wallets-client` scope extension
- [ ] Retry observability polish (Idempotency-Key, request_id UUID, max_elapsed_seconds, findings.toml)
- [ ] ERR-01/ERR-02 mocked error mapping
- [ ] Disk persistence for higyrus/matriz/ambito auth tokens (only IOL has refresh_token in v1.2)
- [ ] Pluggable `TokenCache` interface beyond keyring + JSON (Redis, DB)
- [ ] Pydantic `BaseSettings` integration for env var loading

### Future / Reject

- [ ] Single mega-driver `main.py` cross-package (anti-feature — violates "no shared internals")
- [ ] Driver promoted to CI live tests (anti-feature — rate-limit hazard, business-hours dependency)
- [ ] Sync-first codegen (anti-feature — async semantics can only be removed, not added)
- [ ] Plaintext refresh_token in `.env` (anti-feature — security violation)
- [ ] `with_options()` mutating `self` in place (anti-feature — violates ecosystem convention)
- [ ] `from_env(strict=True)` fail-fast variant (anti-feature — diverges from ecosystem; constructor convention is lazy auth)

---

## Confidence Assessment

| Feature | Confidence | Reason |
|---|---|---|
| 1. Driver migration | HIGH | Internal pattern; v1.1 quick-task 260613-nwb already demonstrated INT-01 idiom; LIVE-01 gate (Phase 11) validated the live-rerun cycle |
| 2. unasync/codegen | MEDIUM | Tooling exists and is well-documented (unasync, unasyncd, psycopg3 codegen); fit-for-purpose at THIS repo's 4-package scale is uncertain — hence spike-before-plan flag is correct |
| 3. Live re-verification | HIGH | v1.1 Phase 11 LIVE-01 directly precedented; just repeats the gate post-migration |
| 4. IOL disk persistence | HIGH | Pattern well-established (msal-extensions, requests-oauthlib, google-auth + keyring); v1.1 BUG-03 in-instance lifecycle + v1.1 TokenStore Phase 10 concurrency primitive already validated; only new dep is `keyring` (mature, used by AzureCLI/gcloud-sdk) |
| 5. `from_env()` | HIGH | Industry survey unambiguous: NOT the convention (anthropic, openai, mistral, groq, cohere, stripe all use implicit env fallback). v1.1 already implements implicit fallback. Recommendation is shipping the alias for discoverability only |
| 6. `with_options()` | HIGH | Anthropic source code inspected; openai docs confirmed; pattern is shallow-clone-share-underlying-http_client. Implementation maps cleanly to v1.1 `_ClientState` + `_max_retries` substrate |

---

## Open Questions for Phase-Level Research

These should be revisited when planning the specific phases:

1. **Feature 2 spike outcome** — go/no-go decision and which tool (unasync token-based vs unasyncd libcst-based vs custom psycopg-style). Spike scope: iol-client only; measure LOC + CI + reviewer-effort. Operator decision required before phase commits.
2. **Feature 4 keyring fallback policy** — when keyring backend unavailable (e.g., headless Linux without secret-service daemon), should the JSON fallback be silent (transparent degrade) or require explicit opt-in (`Client(token_cache=DiskTokenCache(path=..., backend="json"))`)? Recommend explicit opt-in — silent disk write of secrets surprises ops.
3. **Feature 4 cache path default** — `~/.cache/iol-client/token.json` (XDG cache) vs `~/.local/share/iol-client/token.json` (XDG data). XDG cache is "regenerable" semantically; refresh_token is "regenerable via password grant" → cache wins. Operator decision needed.
4. **Feature 5 ship-or-skip** — does the operator want the `from_env()` alias for discoverability, or is "Client() reads env" documented well enough already? Low-cost either way.
5. **Feature 6 overridable kwarg surface** — minimum: `max_retries`. Beyond that: `timeout`, `base_url`, `http_client`. Anthropic ships all 4 + headers + query + middleware. v1.2 scope decision: ship the minimum 4 (matching anthropic core), or trim to just `max_retries` (PROJECT.md title)?
6. **Feature 4 vs Feature 6 interaction** — does `client.with_options(token_cache=DiskTokenCache(...))` make sense? Semantically: swapping token cache on an existing instance is weird (when does the swap take effect? on next refresh? immediately?). Recommend: token cache is a constructor-only kwarg (not in `with_options()` signature).
7. **Feature 1 driver-output golden snapshot tool** — does v1.2 ship a generic diff harness, or is operator-eye comparison sufficient? v1.1 used operator-eye. Recommend same: capture findings.md hash + summary line counts in PHASE-VERIFICATION.md, no separate tooling.

---

## Sources

- [Anthropic Python SDK `_client.py` (main)](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_client.py) — constructor env fallback, `copy()`/`with_options()` implementation, env var enumeration
- [Anthropic Python SDK Client Architecture — DeepWiki](https://deepwiki.com/anthropics/anthropic-sdk-python/4-client-architecture) — `copy()` aliased as `with_options()` semantics
- [Anthropic Python SDK docs — Claude API Docs](https://platform.claude.com/docs/en/api/sdks/python) — ANTHROPIC_API_KEY default behavior
- [OpenAI Python SDK — discussions on with_options + timeouts](https://github.com/openai/openai-python/discussions/795) — per-request `max_retries` + `timeout` override pattern
- [OpenAI Python SDK PyPI](https://pypi.org/project/openai/) — `client.with_options(max_retries=5).chat.completions.create(...)` documented
- [OpenAI Python SDK feature request — Add Logging Between Retries for with_options](https://community.openai.com/t/add-logging-between-retries-for-with-options-max-retries-in-openai-python-client/1271021) — confirms `with_options(max_retries=...)` API surface
- [Stripe Python — StripeClient migration guide v8](https://github.com/stripe/stripe-python/wiki/Migration-guide-for-v8-(StripeClient)) — `max_network_retries` constructor + `options={"idempotency_key": ...}` per-call
- [Stripe Idempotency Keys](https://docs.stripe.com/api/idempotent_requests) — auto-generated for retries
- [unasync (python-trio)](https://github.com/python-trio/unasync/) — token-based async→sync transform, build-time, used by urllib3/httpcore/elasticsearch-py
- [unasyncd 0.10.0](https://pypi.org/project/unasyncd/) — libcst-based, per-file exclusions, AsyncExitStack→ExitStack, docstring transforms
- [psycopg3 Automatic async-to-sync code conversion](https://www.psycopg.org/articles/2024/09/23/async-to-sync/) — AST-based in-tree generator
- [Seth Larson — Designing Libraries for Async and Sync I/O](https://sethmlarson.dev/designing-libraries-for-async-and-sync-io) — async-first source of truth recommendation
- [Combining sync and async Python code — DRY package](https://spwoodcock.dev/blog/2025-02-python-dry-async/) — unasync `_async`/`_sync` folder layout
- [DEP Draft: Unasyncify Codegen — Django Forum](https://forum.djangoproject.com/t/dep-draft-request-for-shepherd-unasyncify-codegen/36038) — wider ecosystem context
- [MSAL Python `SerializableTokenCache`](https://learn.microsoft.com/en-us/python/api/msal/msal.token_cache.serializabletokencache) — base interface, "does not actually persist the cache on disk"
- [msal-extensions PersistedTokenCache](https://github.com/AzureAD/microsoft-authentication-extensions-for-python) — file-lock + auto-reload + cross-platform encryption (DPAPI/Keychain/LibSecret)
- [A Python MSAL Token Cache for Confidential Clients — DEV](https://dev.to/425show/a-python-msal-token-cache-for-confidential-clients-29c9) — implementation walkthrough
- [requests-oauthlib `token_updater` callback](https://requests-oauthlib.readthedocs.io/en/latest/examples/real_world_example_with_refresh.html) — auto-refresh + callback persistence pattern
- [requests-oauthlib developer interface](https://requests-oauthlib.readthedocs.io/en/latest/api.html) — `OAuth2Session(auto_refresh_url=..., auto_refresh_kwargs=..., token_updater=...)`
- [google.oauth2.credentials.Credentials](https://googleapis.dev/python/google-auth/1.7.2/reference/google.oauth2.credentials.html) — refresh_token + token_uri + client_id + client_secret required
- [Authlib OAuth Clients docs](https://docs.authlib.org/en/v1.1.0/client/) — Refresh & Auto Update Token signals
- [Python `keyring`](https://keyring.readthedocs.io/) — cross-platform credential store
- [keyring — Securely Storing Credentials in Python (Medium)](https://medium.com/@forsytheryan/securely-storing-credentials-in-python-with-keyring-d8972c3bd25f) — keyring usage walkthrough
- [Python Keyring Backends 2025](https://johal.in/python-keyring-backends-secretservice-windows-credential-manager-support-2025/) — current backend support
- [Anthropic Python SDK source on PyPI](https://pypi.org/project/anthropic/) — API reference and version baseline
- [groq-python](https://github.com/groq/groq-python) — implicit env fallback pattern reference
- [mistralai 1.0.x on PyPI](https://pypi.org/project/mistralai/1.0.3) — implicit env fallback pattern reference
- [httpx Environment Variables](https://github.com/encode/httpx/blob/master/docs/environment_variables.md) — confirms httpx itself does NOT read `base_url` from env (caller responsibility)
- [httpx Clients](https://www.python-httpx.org/advanced/clients/) — `httpx.Client(base_url=..., transport=...)` substrate that v1.1 already uses

---

*Feature research for: market-libs v1.2 Architecture + Auth/Ergonomics Carry-forwards*
*Researched: 2026-06-14*
