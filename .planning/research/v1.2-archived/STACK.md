# Stack Research — v1.2 Architecture + Auth/Ergonomics Carry-forwards

**Domain:** Python HTTP client libraries (4 verifiable packages in a uv monorepo) — additions for sync/async single-source codegen, secure IOL refresh_token disk persistence, and tooling support for driver migration.
**Researched:** 2026-06-14
**Confidence:** HIGH (versions verified via PyPI + Context7; rationale grounded in v1.1 architectural constraints).
**Scope:** STACK ADDITIONS ONLY — locked v1.0/v1.1 stack (Python 3.12+, uv, httpx, tenacity 9.1.4, pytest+pytest-httpx, ruff `E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID/LOG`, mypy strict, import-linter v2.11, hatchling) is NOT under review and is preserved verbatim from the v1.0/v1.1 archive.

---

## TL;DR Decision Matrix

| Subquestion | Recommendation | Confidence | Why (one-liner) |
|-------------|----------------|------------|-----------------|
| 1. Sync/async dedup (codegen tooling) | **`unasync` 0.6.0** as dev-only build-helper, executed via `hatch-build-scripts` (or a thin per-package `tool.hatch.build.hooks.custom`); async-first source under `_aio/`, generated sync under `_sync/` checked into git for reviewability | HIGH (token-replacement + battle-tested by httpcore/elasticsearch-py/trio; spike validates per-package fit) | The only mature library purpose-built for sync↔async codegen in the httpx ecosystem; preserves the "no shared internals" constraint because each of 4 packages runs its own `Rule(fromdir=..., todir=...)`; zero runtime dep (dev-only). Final pick remains gated on the Phase-level spike per `spike-before-plan`. |
| 2. Codegen fallback if `unasync` rejected | **`libcst` 1.8.6** for AST-level rewrites OR pure-Python templating (no library — stdlib `string.Template` + Jinja2 dev-only) | MEDIUM | `libcst` has `py.typed`, MIT, active (1.8.6 Nov 2025, supports Py 3.9-3.14); it's the next-step-up if `unasync`'s token-replacement is too coarse for matriz's complex shells. Heavier (~5MB wheel + pyyaml dep). Use only if spike disqualifies `unasync`. |
| 3. IOL refresh_token disk persistence | **`platformdirs` 4.10.0 + stdlib (`cryptography` deferred)** — store refresh_token as `0600` file under `platformdirs.user_data_dir("iol-client")/refresh_token.json`; no encryption at-rest in v1.2 (developer-machine / CI threat model only — matches how `.env` files already live on disk). Encryption with `cryptography.fernet` deferred to v1.3 unless threat model expands. | HIGH | platformdirs is zero-deps, MIT, `requires-python>=3.10`, 22KB wheel — cheapest portability win. The IOL credentials already live in `packages/iol-client/.env` (plaintext, 0644 by default); adding a 0600 token cache file is a strict improvement without raising the bar for the rest of the package. |
| 4. IOL refresh_token disk persistence — IF threat model demands encryption | **`cryptography>=43,<50` Fernet** (NOT `keyring`) | MEDIUM | Fernet (AES-128-CBC + HMAC-SHA256) gives at-rest encryption with a key derived from a user-provided passphrase or `IOL_TOKEN_ENCRYPTION_KEY` env var. Adds C-extension dep (`cffi`) but no GUI/D-Bus runtime requirement → works in CI. `keyring` is rejected for v1.2 because (a) headless CI needs `PYTHON_KEYRING_BACKEND=null` workaround that defeats the purpose, (b) Linux requires `SecretService` / `jeepney` system deps, (c) macOS Keychain access prompts interactively on first read, breaking the `main_iol.py --live` driver flow. |
| 5. Driver migration tooling (`main_*.py` rewrite × 4) | **No new tool** — use stdlib `ast` walk for migration verification + golden snapshot tests via existing pytest. `libcst` codemod is an option ONLY if the rewrite scales to >50 mechanical sites per file. | HIGH | Phase 11 already validated AST-walk regression-guards (CR-06 narrowed 27 sites of `except Exception` via AST). Same pattern works for INT-01 idiom enforcement on the migrated drivers. Adding a codemod library for one-shot driver migration is over-investment. |
| 6. mypy strict compatibility of all additions | All preserve mypy strict | HIGH | `unasync` is dev-only (not imported at runtime); `platformdirs` has inline annotations (verified via Context7 + PyPI classifier `Typing :: Typed`); `cryptography` ships type stubs in 43+; `keyring` declared typing support in jaraco/keyring NEWS (2024-2025 changelog entries). |
| 7. Ruff `LOG` rule set compatibility | All preserve | HIGH | None of the additions emit log calls. The Phase 8 `LOG001..LOG015` enforcement (root-logger-call) is unaffected. |

---

## Recommended Stack Additions

### Cluster 1 — Codegen / Driver Migration (Arquitectura sync/async dedup)

| Technology | Version | Dep Type | Purpose | Why Recommended | Risks |
|------------|---------|----------|---------|-----------------|-------|
| **unasync** (CANDIDATE — spike-gated) | `>=0.6.0,<0.7` (current 0.6.0, released 2024-05-03) | DEV-ONLY (dependency-group `dev` in root `pyproject.toml`) | Async-first source generation: write `_aio/<endpoint>.py` once, generate `_sync/<endpoint>.py` at build time via token replacement (`async def`→`def`, `await`→``, `AsyncClient`→`Client`, `AsyncIterator`→`Iterator`, custom rules per package) | (1) Used in production by `httpcore`, `elasticsearch-py`, `trio` (`hip`) — the same httpx ecosystem we're already in. (2) Per-package `Rule(fromdir, todir, additional_replacements={...})` matches the "no shared internals" constraint exactly. (3) Token-based, not AST-based — predictable, debuggable, ~150 LOC source; dev failure modes are obvious. (4) MIT OR Apache-2.0 dual license. (5) Zero runtime dep — the generated code has no `unasync` import. | (a) Token replacement breaks on whitespace-sensitive patterns (rare in httpx clients). (b) No `py.typed` marker, but it never runs in the typed application surface (dev-only). (c) Hatchling integration is custom (build hook + `cmdclass_build_py` is setuptools-only) — pattern is: commit both `_aio/` AND `_sync/` to git + run `unasync` in pre-commit or a `Makefile` target + CI gate `lint-codegen` that re-runs and asserts no diff. **(d) Spike-before-plan flag is ACTIVE per PROJECT.md — final adoption gated on the Phase-level spike report.** |
| **libcst** (FALLBACK if unasync rejected) | `>=1.8.0,<2` (current 1.8.6, released Nov 2025) | DEV-ONLY | AST-level codemod for sync/async dedup; alternative if token replacement is too coarse for matriz (which has `TokenStore` + `_refresh_policy` + `aio.py` 852 LOC with non-trivial branching) | Instagram-maintained, MIT, `py.typed` present, supports Python 3.9-3.14 (including 3.13 free-threading classifier), 48 releases — actively developed. CST preserves whitespace/comments which matters for review of generated code. | Heavier than unasync: pulls `pyyaml>=5.2` (already transitive in our env via pre-commit), ~5MB wheel. Imperative API is more code to write per transformation rule (~3× LOC vs unasync). Use only if spike disqualifies unasync. |
| **ast-grep / comby** (REJECTED) | — | — | Pattern-match-and-rewrite tools — DSL-based | Rejected: `comby` does not support indentation-sensitive languages like Python (per their own docs); `ast-grep` is Rust-based CLI, not a Python library — adds a non-Python tool to the dev workflow and breaks the "pre-commit + ruff + mypy" CI invariant. |

### Cluster 2 — Secure Token Storage (IOL refresh_token Disk Persistence)

| Technology | Version | Dep Type | Purpose | Why Recommended | Risks |
|------------|---------|----------|---------|-----------------|-------|
| **platformdirs** | `>=4.0,<5` (current 4.10.0, released 2026-05-28) | RUNTIME — `packages/iol-client/pyproject.toml` ONLY | Cross-platform user-data-dir resolution: `platformdirs.user_data_dir("iol-client", appauthor="market-libs")` returns `~/Library/Application Support/iol-client` (macOS), `~/.local/share/iol-client` (Linux/XDG), `%LOCALAPPDATA%\market-libs\iol-client` (Windows) | (1) Zero runtime deps (verified `requires_dist: null` on PyPI). (2) MIT, 22KB wheel. (3) `requires-python>=3.10` — well within our `>=3.12`. (4) PEP 561 typed (Context7 confirms). (5) Industry-standard idiom for "where do I drop a cache file?" — pip, virtualenv, pytest, black all use it. | None. The downside is that platformdirs gives you a *path*, not a security model — file permissions are still your responsibility. We commit to `os.chmod(path, 0o600)` + `os.makedirs(..., mode=0o700, exist_ok=True)` on the directory. |
| **stdlib only** (`os`, `json`, `pathlib`) | — | RUNTIME | File I/O + permission bits for the refresh_token cache file | Threat model = developer machine + CI runners; the IOL credentials (`username`, `password`) already live in `packages/iol-client/.env` (plaintext, default 0644). Adding a 0600 token file is a Pareto improvement without introducing a heavier security primitive that doesn't match the existing posture. JSON envelope: `{"refresh_token": "...", "issued_at": <epoch>, "schema_version": 1}`. | None — stdlib `json` + `pathlib` are already universal. |
| **cryptography** (DEFERRED to v1.3 unless threat model expands) | `>=43,<50` (current 49.0.0) | RUNTIME — `packages/iol-client/pyproject.toml` ONLY, if adopted | Fernet symmetric encryption of refresh_token at-rest, keyed off `IOL_TOKEN_ENCRYPTION_KEY` env var | If a future v1.3+ requirement says "encrypt the token at rest because the host disk is untrusted", `cryptography.fernet.Fernet` is the answer: AES-128-CBC + HMAC-SHA256, built-in timestamping, `MultiFernet` for key rotation. Apache-2.0 OR BSD-3-Clause. Cross-platform (Windows, macOS, Linux x86_64/arm64). | Pulls `cffi>=2.0.0` (C extension) — adds ~5MB wheel + build-from-source risk on niche platforms (none in our CI matrix: GitHub-hosted Ubuntu + Python 3.12/3.13 both have prebuilt wheels). `py.typed` status not explicitly marked in metadata but inline annotations + stubs land in 43+. Do NOT add unless the operator authorizes a threat-model expansion. |
| **keyring** (REJECTED) | 25.7.0 | — | OS-native credential store wrapper (macOS Keychain, Linux Secret Service, Windows Credential Locker) | **Rejected for v1.2.** Detailed reasoning: (a) **CI headless gap** — headless Linux runners (GitHub Actions Ubuntu) lack a D-Bus session, so `SecretService` backend fails; the workaround is `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` which is a no-op store (defeats the purpose). (b) **macOS first-read prompt** — Keychain prompts the user GUI-interactively the first time a script reads a secret; this breaks `uv run python main_iol.py --live` running unattended. (c) **Linux runtime deps** — pulls `SecretStorage>=3.2 + jeepney>=0.4.2` as Linux-conditional deps; we'd be locking the IOL wheel to a transitive tree that doesn't ship from PyPI as pure-Python. (d) **macOS shared-key risk** — per keyring's own docs, "any Python script or application can access secrets created by keyring from that same Python executable without prompting" — same trust boundary as a 0600 file, without the portability. | n/a — not adopted. |

### Cluster 3 — Driver Migration (`main_*.py` × 4)

| Technology | Status | Why |
|------------|--------|-----|
| **stdlib `ast`** | KEEP — already in use | Phase 11 CR-06 already used AST walks to narrow 27 sites of `except Exception` into typed exception clauses. Re-use the same pattern to enforce the INT-01 idiom (`_get_default()._state.<attr>` access) across migrated drivers. Zero new deps. |
| **pytest snapshot tests** | NEW — pure pytest | Adopt the convention `tests/drivers/test_main_<pkg>_smoke.py::test_envelope_matches_golden` that runs `main_<pkg>.main(["--dry-run"])` and snapshot-compares the output. Pure pytest with `pytest-httpx` mocking the upstream API. No new deps required. |
| **syrupy / pytest-snapshot** (REJECTED) | — | Adds a runtime dep for snapshot management; pytest's own `caplog` + `capsys` + golden file fixture is sufficient at this scale (~2000 LOC × 4 drivers). |
| **libcst codemod** for the driver rewrite (CONDITIONAL) | OPTIONAL — only if mechanical site count >50 per driver | Phase 11 INT-01 hotfix already migrated 15 sites in `main_iol.py` manually + 1 PROBE_STALE inline. If v1.2's driver migration also stays under ~50 sites per driver, manual edits + Edit-tool review remains cheaper than writing+testing a libcst codemod script. **If the spike audits the drivers and reports >50 sites/file: revisit libcst.** |

### Development Tools — No Changes from v1.1

| Tool | Status |
|------|--------|
| `ruff >=0.7` (rule sets `E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID/LOG`) | UNCHANGED — covers all v1.2 additions. `unasync`-generated files go under `_sync/` and stay inside the ruff src globs; we may need to extend `extend-exclude` ONLY if a generated file has known violations the source `_aio/` does not (test in spike). |
| `mypy >=1.13` strict | UNCHANGED — `platformdirs` is typed; `cryptography` (if adopted) types are bundled; `unasync` is dev-only and not type-checked at runtime. |
| `pytest >=8.3` + `pytest-asyncio >=0.24` + `pytest-httpx >=0.34` | UNCHANGED — `_sync/` AND `_aio/` directories both get test coverage; `pytest-httpx` mocks both paths via httpx mock invariant. |
| `import-linter >=2.11,<3` | UNCHANGED — extend the existing `forbidden` contracts to also forbid `_sync.*` from importing `_aio.*` (and vice versa) if we go with the unasync `_aio/` + `_sync/` layout. Declarative + CI-enforced, same Phase 7 pattern. |
| `tenacity 9.1.4` | UNCHANGED — already runtime dep × 4 packages from v1.1. |
| `pre-commit >=4.0` | UNCHANGED — add a single new hook `pre-commit run unasync-regen` if we adopt unasync; otherwise unchanged. |

---

## Installation

### Per-package pyproject.toml changes

```toml
# packages/iol-client/pyproject.toml — IOL ONLY for token persistence
dependencies = [
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "tenacity>=9.1.0,<10",
    "platformdirs>=4.0,<5",       # NEW — v1.2 BUG-03 closure (IOL refresh_token disk persistence)
    # "cryptography>=43,<50",      # DEFERRED to v1.3 unless threat-model expansion authorized
]
```

The other three packages (`ambito-financiero-client`, `higyrus-client`, `matriz-client`) get NO new runtime deps in v1.2.

### Root pyproject.toml dev-dependency changes

```toml
# pyproject.toml [dependency-groups] dev
dev = [
    "ruff>=0.7",
    "mypy>=1.13",
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "pytest-asyncio>=0.24",
    "pytest-httpx>=0.34",
    "pre-commit>=4.0",
    "import-linter>=2.11,<3",
    "unasync>=0.6.0,<0.7",         # NEW — v1.2 codegen (CANDIDATE, spike-gated)
    # "libcst>=1.8.0,<2",           # FALLBACK ONLY if spike disqualifies unasync
]
```

### Commands to apply

```bash
# Runtime dep (IOL only)
uv add --package iol-client "platformdirs>=4.0,<5"

# Dev dep (root, workspace-wide)
uv add --dev "unasync>=0.6.0,<0.7"

# Re-lock the workspace
uv sync --all-packages --all-extras --dev --frozen
```

---

## Subquestion-by-Subquestion Rationale

### 1. Sync/Async Single-Source Codegen — Why `unasync` (spike-gated)

#### Candidates Evaluated

| Library | Version | py.typed | Approach | Used By | Runtime Dep? | Verdict |
|---------|---------|----------|----------|---------|--------------|---------|
| **unasync** | 0.6.0 (2024-05-03) | NO (dev-only, doesn't matter) | Token replacement (`tokenize-rt`-based) | httpcore, elasticsearch-py, trio (hip) | NO (dev-only) | **PRIMARY CANDIDATE** |
| **libcst** | 1.8.6 (Nov 2025) | YES | Concrete syntax tree, codemod API | Instagram, mypy ecosystem | NO if dev-only | **FALLBACK** |
| **ast-grep** | n/a (Rust CLI) | n/a | DSL-based, multi-language | various non-Python tooling | NO | REJECTED (non-Python tool, breaks pre-commit invariant) |
| **comby** | n/a (Go CLI) | n/a | Structural pattern match | non-Python | NO | REJECTED (Python indent-sensitive is unsupported per their own docs) |
| **Jinja2 / Mako templates** | (current) | — | Template-driven codegen from a single specification source | — | YES if runtime; NO if dev-only | REJECTED (writing a per-endpoint template is more work than writing a per-endpoint pure helper; templates abstract over Python source you'd need to read either way) |
| **Roll-our-own AST rewriter** | — | — | Stdlib `ast` + `astor` (or `ast.unparse`) | — | NO | REJECTED (we'd be re-implementing unasync's `0.6.0` output) |

#### Why `unasync` wins (subject to spike)

1. **It's the ecosystem-native answer.** `httpcore` and `elasticsearch-py` are both in our same world (httpx-shaped HTTP clients with dual sync/async surfaces). `httpcore` ships a tiny custom `unasync.py` script that does the same thing — token replacement. If httpcore (built by the same people who build httpx) chose this approach, the bar to deviate is high.

2. **Per-package `Rule` isolation matches our "no shared internals" constraint.** Each package gets its own `tools/codegen.py` (or similar) that invokes `unasync.unasync_files()` with a `Rule(fromdir="src/<pkg>/_aio/", todir="src/<pkg>/_sync/", additional_replacements={"AsyncClient": "Client", "asyncio.Lock": "threading.Lock", ...})`. No shared module across packages.

3. **Token replacement is debugger-friendly.** The generated `_sync/` source is human-readable Python that maps 1:1 to the source `_aio/`. When a bug surfaces in production, you read the generated file directly, not a regenerated-on-import surface (unlike Cython or runtime metaprogramming).

4. **Hatchling integration is a custom build hook, not a deal-breaker.** Unasync's stock integration is via `setuptools` `cmdclass_build_py`. We use `hatchling`. The clean integration path for our world is:
   - Author lives in `src/<pkg>/_aio/` only
   - A `tools/codegen.py` script (per package) runs `unasync` to materialize `src/<pkg>/_sync/`
   - **Commit both `_aio/` AND `_sync/` to git** (reviewable diffs, no surprise codegen at build time)
   - A pre-commit hook + CI job `lint-codegen` re-runs `tools/codegen.py` and `git diff --exit-code` — fails the build if `_sync/` is stale
   - `client.py` becomes a 3-line shim: `from <pkg>._sync.api import *; from <pkg>._sync.api import Client`
   - `aio.py` becomes a 3-line shim: `from <pkg>._aio.api import *; from <pkg>._aio.api import AsyncClient`

   This sidesteps the hatchling integration problem entirely — the build backend never runs `unasync`. Hatchling only ships pre-generated files. Confidence: HIGH (verified via httpcore's `_sync/`+`_async/` source tree on GitHub).

5. **Zero runtime dep.** `unasync` is dev-only. The wheels we publish never import it.

6. **Spike validates per-package edge cases.** Matriz has `TokenStore` (3-way concurrent: threading.Lock + asyncio.Lock + ws_client daemon thread) and `_refresh_policy.py` — patterns that need careful token-replacement rules (e.g., `asyncio.Lock` ↔ `threading.Lock` only in some contexts). The Phase-level spike should:
   - Pick the smallest package (`ambito-financiero-client`) and prove the round-trip generates byte-identical `_sync/api.py` to the v1.1 `client.py` shell (modulo formatting normalized by ruff).
   - Then attempt the largest (matriz) — if matriz needs custom `additional_replacements` beyond what unasync supports cleanly, escalate to libcst.

#### Why libcst is the fallback (not the primary pick)

- **Heavier:** 1.8.6 wheel is ~5MB + pulls `pyyaml>=5.2` (already in our env via pre-commit so net-zero); imperative codemod API is more LOC to write per rule than unasync's declarative `additional_replacements` dict.
- **More power than we need (probably).** httpx + httpcore + elasticsearch-py + trio all picked unasync over libcst for this exact problem. If they didn't need libcst, we probably don't either.
- **Reserve for emergency.** If the unasync spike fails on matriz due to a known limitation (e.g., complex `async with` rewrites), libcst is the next stop. Until then: not adopted.

#### Why ast-grep / comby / Jinja2 are explicit vetoes

- **ast-grep** is a Rust CLI tool. Adds a non-Python binary to the dev workflow. Our pre-commit + CI invariant is "Python tools only" (ruff is also Rust under the hood but ships as a Python wheel — different distribution story).
- **comby** does not support Python (whitespace-sensitive). Per their own comparison docs, indentation-sensitive languages need special handling that comby lacks.
- **Jinja2/Mako templates** would push us to maintain a per-endpoint template that abstracts over Python source you'd still need to read either way. The win is illusory for HTTP client code; unasync's source-level token replacement is closer to the actual problem shape.

---

### 2. Secure IOL refresh_token Disk Persistence — Why `platformdirs` + stdlib (not `keyring`, not `cryptography` in v1.2)

#### Threat Model Statement (Explicit)

**v1.2 threat model assumes:**
- The host machine running `main_iol.py` is **trusted** (developer laptop, CI runner)
- The IOL credentials (`username`, `password`) **already live in `packages/iol-client/.env`** as plaintext with default umask permissions
- The OS user account isolation is the security boundary
- Adversary class = **other local users on the same machine**, not malware running as the same user
- CI environment = **GitHub Actions hosted runners** (ephemeral, no Keychain, no D-Bus session)

**Out of scope for v1.2:**
- Encryption at-rest of a token cached on a machine where `.env` already contains stronger long-lived credentials (`username`+`password`) is **not** a threat-model upgrade — it's theater. Defer.
- Protection against malware running as the same user (would require hardware-backed enclaves — TPM, Secure Enclave — far beyond scope)

#### Candidates Evaluated

| Library | Version | py.typed | Adds Runtime Deps? | Headless CI? | macOS GUI Prompt? | Verdict |
|---------|---------|----------|--------------------|--------------|--------------------|---------|
| **platformdirs + stdlib** | 4.10.0 | YES (PEP 561, MIT) | ZERO new transitive | YES (no system deps) | NO | **WINNER** |
| **cryptography (Fernet)** | 49.0.0 | YES (43+) | YES (`cffi>=2.0.0` — C ext) | YES (prebuilt wheels on cp312/cp313 linux+macos+win) | NO | DEFERRED (re-evaluate if threat model expands) |
| **keyring** | 25.7.0 | YES (recent typing decl per Context7) | YES (Linux: SecretStorage+jeepney; Windows: pywin32-ctypes) | NO (needs `PYTHON_KEYRING_BACKEND=null` workaround = no-op) | YES (first read prompts user) | REJECTED |

#### Why `platformdirs` + stdlib wins for v1.2

1. **Zero runtime deps, MIT, 22KB wheel.** `requires_dist: null` on PyPI (verified). The cheapest possible portability win — gives you the right path on macOS / Linux (XDG) / Windows and that's it.

2. **Threat model match.** The IOL credentials are already in `.env` on disk. A refresh_token cache file at `0600` is a strict improvement: shorter-lived secret, narrower file mode, dedicated location separate from the credentials file. Adding Fernet on top doesn't change the trust boundary (the encryption key has to live somewhere — env var or another file — and that location is the new weakest link).

3. **CI-friendly.** No D-Bus, no Keychain, no GUI prompts. Works identically on hosted GitHub Actions Ubuntu/macOS/Windows runners.

4. **`Client.from_env()` + persistence plays well together.** The IOL `Client` constructor reads:
   - `refresh_token_path: Path | None = None` (default: `platformdirs.user_data_dir("iol-client") / "refresh_token.json"`)
   - `persist_refresh_token: bool = True` (default-on, opt-out for tests)
   - On `_refresh()` success: atomic write (`os.replace` semantics) of `{"refresh_token": "...", "issued_at": <epoch>, "schema_version": 1}` with `os.chmod(path, 0o600)` and `os.makedirs(..., mode=0o700, exist_ok=True)`
   - On `Client.__init__`: read + validate `schema_version`; on missing/invalid → ignore (fall back to env-var `IOL_REFRESH_TOKEN` or initial password login)

5. **Reversible decision.** If a future v1.3 threat-model expansion authorizes encryption, swap in Fernet without changing the file location or the path-resolution API. platformdirs path stays.

#### Why `keyring` was rejected (despite being the textbook answer)

This was the most thoroughly evaluated rejection — keyring is the obvious first answer, so the reasoning must be explicit:

- **Headless CI is broken.** GitHub Actions Ubuntu runners have no D-Bus session running; `SecretService` backend fails on first use. The documented workaround is `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` — which is a no-op store (writes succeed, reads return None). Adopting keyring then setting the null backend in CI means CI has no persistence at all, which defeats the v1.2 goal of "persistence exercised in the live driver run."
- **macOS Keychain prompts on first read.** Per keyring's own docs (and validated via the project's NEWS.rst), the first time a Python process reads from Keychain after a write, macOS shows a GUI prompt asking the user to allow access. `main_iol.py --live` runs unattended; a GUI prompt blocks it.
- **Linux requires system libraries.** `SecretStorage>=3.2 + jeepney>=0.4.2` are Linux-conditional runtime deps. Both are pure-Python, but `SecretStorage` requires a running Secret Service daemon (gnome-keyring or kwallet). Headless Linux machines (servers, containers, CI) don't have this.
- **Doesn't actually improve the trust boundary on macOS.** Per keyring's docs: "any Python script or application can access secrets created by keyring from that same Python executable without prompting." The trust boundary is the *Python interpreter binary*, not the OS user. A 0600 file on macOS gives the same trust boundary (OS user) without the GUI prompt, without the conditional Linux deps, without the headless CI failure mode.
- **Wheel size:** keyring + jeepney + SecretStorage + jaraco.* tree is ~10× the wheel size of platformdirs. We'd be locking the iol-client publishable wheel to a much heavier transitive tree.

If a future milestone needs OS-native credential storage for a *user-facing* CLI tool (where the GUI prompt is feature, not bug), keyring becomes the right answer. For an unattended verification driver: it's wrong.

#### Why `cryptography.fernet` is DEFERRED (not rejected)

- **It's the right answer if the threat model changes.** Fernet is AES-128-CBC + HMAC-SHA256 with built-in versioning and timestamping. `MultiFernet` supports key rotation. It's Apache-2.0 OR BSD-3-Clause. It works headless. It has no GUI prompts.
- **Cost is a C extension via `cffi`.** Prebuilt wheels exist for cp312 + cp313 + Linux/macOS/Windows on the v1.0/v1.1 CI matrix — verified via PyPI download stats. No build-from-source risk on our matrix. But it's still a ~5MB wheel addition.
- **Operator authorization needed.** Adopting Fernet means deciding where the encryption key lives. Options: (a) env var `IOL_TOKEN_ENCRYPTION_KEY` (user has to set it — high friction); (b) derived from machine ID (no real security uplift — anyone with shell access can derive it); (c) hardware-backed key (out of scope). The v1.2 deferral is: **don't introduce a new ceremony for a security uplift that doesn't change the actual trust boundary.**
- **Re-evaluation trigger:** If a future v1.3+ user story is "ship the refresh_token cache between machines" or "guard against backup-leak scenarios", Fernet becomes the right addition. Until then, defer.

---

### 3. Driver Migration Tooling

The v1.2 driver migration rewrites `main_ambito_financiero.py`, `main_iol.py`, `main_higyrus.py`, `main_matriz.py` to:
- Replace `pkg.get_X(...)` top-level calls with `client.get_X(...)` instance method calls
- Replace `_get_default()._state.<attr>` access pattern (where currently used) with direct `client._state.<attr>` access
- Add `Client.from_env()` + `client.with_options(max_retries=N)` adoption sites
- Preserve all existing `verification/findings.py` integration, `--live`, `--async`, mutation gates, redaction filters

#### Recommendation: NO new tool

| Tool | Why Not |
|------|---------|
| **libcst codemod** | Phase 11 INT-01 hotfix migrated 15 sites in `main_iol.py` manually + 1 PROBE_STALE inline. Driver files are ~2000 LOC each, but the migration sites are not uniform mechanical rewrites — each site needs review for the surrounding context (probe metadata, redaction wrappers, `findings.write_finding(...)` integration). Writing+testing a libcst codemod script costs more than 4 careful Edit-tool passes. |
| **syrupy / pytest-snapshot** | Adds runtime dep for snapshot management. Pytest's own `caplog`/`capsys` + golden file fixture under `tests/drivers/golden/` is sufficient. Established convention in Phase 11 driver tests. |
| **rope / bowler** | Both are older Python refactoring libs (rope is GUI-oriented, bowler is Facebook-era libcst predecessor). Neither is actively maintained at the level we want for a v1.2 push. |

#### Recommendation: STDLIB `ast` walk for regression-guards

The Phase 11 CR-06 pattern is the right primitive:

```python
# tests/drivers/test_main_iol_smoke.py — example
import ast
from pathlib import Path

def test_no_top_level_pkg_call_remains_in_main_iol() -> None:
    """v1.2 driver migration regression-guard: main_iol.py must consume Client instances.

    After migration, no top-level `iol_client.get_X(...)` calls should remain — all calls
    go through a Client instance. This guard fails the build if a regression re-introduces
    the singleton call pattern.
    """
    tree = ast.parse(Path("main_iol.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "iol_client"
                and node.func.attr.startswith("get_")
            ):
                raise AssertionError(
                    f"main_iol.py:{node.lineno}: top-level pkg.get_X call detected — "
                    f"migrate to Client instance (v1.2 INT-02 idiom)"
                )
```

This adds zero deps and matches the established Phase 11 CR-06 convention.

---

### 4. mypy strict + Ruff Compatibility Check

| Addition | mypy Strict Impact | Ruff Impact | Mitigation |
|----------|--------------------|-------------|------------|
| **unasync 0.6.0** (dev-only) | None — never imported at runtime, generated code is plain Python type-checked normally | None — generated `_sync/` files go through the same ruff pipeline as hand-written code | None needed. Generated files may need `# noqa: <ruleset>` per-line tags ONLY if a specific rule fires asymmetrically on sync vs async (e.g., `ASYNC` rules don't fire on sync, but ruff is smart enough to skip them). Verify in spike. |
| **platformdirs 4.10.0** | Typed (PEP 561) — verified via Context7 + PyPI classifier `Typing :: Typed` | None | None needed. |
| **cryptography 49.0.0** (if adopted) | Has inline annotations in 43+ — `from cryptography.fernet import Fernet` works in mypy strict | None | None needed (if adopted). |
| **libcst 1.8.6** (fallback, dev-only) | Typed | None | None needed (if adopted). |
| **stdlib `ast`, `os`, `json`, `pathlib`, `platformdirs`** | Bundled in typeshed (mypy 1.13+) | None | None needed. |

**No new type-stub packages required. No `[tool.mypy]` config changes needed.** Phase 8 LOG rule set already covers all logging code paths and is unaffected.

---

### 5. Hatchling Build Pipeline Integration

The v1.0/v1.1 build pipeline is:

```
uv build --package <pkg>
  → hatchling reads packages/<pkg>/pyproject.toml
  → hatchling.build.targets.wheel packages from src/<pkg>/
  → wheel published
```

**v1.2 integration for unasync (recommended pattern):**

```
1. Author writes src/<pkg>/_aio/api.py        ← single source of truth
2. Developer runs tools/codegen.py            ← generates src/<pkg>/_sync/api.py
3. Both directories committed to git           ← reviewable diffs
4. Pre-commit hook: tools/codegen.py + git diff --exit-code  ← prevents stale _sync/
5. CI: separate "lint-codegen" job replays step 4
6. hatchling builds the wheel from the committed src/<pkg>/ tree  ← no build-time codegen
```

This pattern **does NOT require a hatchling build hook**. The build backend stays stock. The codegen lives in the dev workflow.

Alternative (deferred, more invasive): `hatch-build-scripts` plugin to run `tools/codegen.py` at build time. Adds a build-system dep + breaks `pip install -e .` editable mode for codegen consumers. Not recommended for v1.2.

---

## What NOT to Add (Explicit Veto List)

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`keyring`** | Headless CI requires null-backend workaround that defeats the purpose; macOS first-read GUI prompt breaks unattended drivers; Linux conditional deps (SecretStorage+jeepney) won't run on bare CI runners | `platformdirs + stdlib 0600 file` |
| **`cryptography.fernet`** (in v1.2) | Encryption doesn't change the trust boundary while `.env` already holds stronger long-lived credentials in plaintext; adds C extension + key-storage ceremony | Defer to v1.3 unless threat model expands |
| **`ast-grep` (Rust CLI)** | Non-Python binary breaks pre-commit + uv tooling invariant; adds installation friction for contributors | `libcst` if codemod needed; otherwise stdlib `ast` |
| **`comby`** | Does not support indentation-sensitive languages (Python, Haskell) per their own docs | `unasync` or `libcst` |
| **`Jinja2` / `Mako` for codegen** | Templates abstract over Python source you'd need to read anyway; per-endpoint template maintenance is more work than per-endpoint pure-helper extraction | `unasync` direct token replacement |
| **`syrupy` / `pytest-snapshot`** | Adds runtime dep for snapshot management at a scale (4 drivers × small golden files) where stock pytest + `pathlib` is sufficient | pytest `capsys` + golden file fixtures |
| **`pydantic`** for Client config | Already vetoed in v1.1; runtime validation overhead for init-time-only data | `@dataclass(slots=True)` (already in use per `_ClientState`) |
| **`rope` / `bowler`** for driver refactor | Older/unmaintained Python refactoring libs; libcst is the modern equivalent | `libcst` if needed; otherwise manual Edit-tool passes + AST regression-guards |
| **`hatch-build-scripts`** for codegen-at-build-time | Breaks `pip install -e .` editable mode; couples release pipeline to codegen tool availability | Commit `_aio/` AND `_sync/` to git + pre-commit hook + CI gate |

---

## Version Compatibility Matrix

| Addition | Compatible With | Notes |
|----------|-----------------|-------|
| `platformdirs 4.10.0` | `python>=3.10` (we have 3.12+) | Zero transitive deps; PEP 561 typed |
| `platformdirs 4.10.0` | macOS / Linux (XDG) / Windows / Android | Cross-platform path resolution is its sole purpose |
| `platformdirs 4.10.0` | `mypy 1.13` strict | Inline annotations, classifier `Typing :: Typed` |
| `unasync 0.6.0` | `python>=3.8` (we have 3.12+) | Dev-only, dep tree `tokenize-rt + setuptools` (both already in our env via build-system) |
| `unasync 0.6.0` | `hatchling` build backend | Via dev-time codegen pattern (no hatchling plugin); generated files committed |
| `libcst 1.8.6` (fallback) | `python>=3.9` (we have 3.12+) | Dev-only; pulls `pyyaml>=5.2` (already transitive via pre-commit) |
| `cryptography 49.0.0` (deferred) | `python>=3.9,!=3.9.0,!=3.9.1` (we have 3.12+) | Prebuilt wheels for cp312/cp313 on linux/macos/windows verified via PyPI |
| `tenacity 9.1.4` (existing) | All v1.2 additions | No conflict; runtime dep already in place |
| `import-linter 2.11` (existing) | Extended for `_aio` ↔ `_sync` boundary | Add 8 new contracts (forbidden bidirectional × 4 packages) per Cluster 1 |

---

## Integration Risk Audit (v1.2 Constraint Check)

| Constraint | Status with Recommended Stack |
|------------|-------------------------------|
| Cannot break CI (ruff + mypy strict + 907 pytest tests + import-linter) | ✓ All additions are typed or dev-only; ruff rule sets unchanged; import-linter contracts extend additively |
| Cannot break public API on minor bump | ✓ Top-level `pkg.get_X(...)` API preserved via PEP 562 shim from v1.1. New surfaces (`Client.from_env()`, `client.with_options()`) are additive. unasync codegen affects internal `_aio/` + `_sync/` layout only — `client.py`/`aio.py` shims preserve the import surface. |
| Cannot introduce shared internals between packages | ✓ Each package gets its own `tools/codegen.py` (or per-package `unasync.Rule`) + its own `_aio/`/`_sync/` directories. Per-package `pyproject.toml` for `platformdirs` (IOL only). No new shared module. |
| Cannot pull heavy deps with C extensions or wide trees (runtime) | ✓ Only runtime addition is `platformdirs` (22KB, zero deps). C-extension `cryptography` deferred. |
| Must work on Python 3.13 too | ✓ All additions support 3.13: platformdirs 4.10.0 (classifier), unasync 0.6.0 (`>=3.8`), libcst 1.8.6 (classifier including 3.13 free-threading), cryptography 49.0.0 (classifier) |
| Must work in headless CI (GitHub Actions) | ✓ No GUI prompts, no D-Bus dependencies, no Keychain access patterns |
| Per-package serial pattern (ámbito → iol → higyrus → matriz) | ✓ All additions roll out per-package in the v1.0/v1.1 serial order; spike runs on ámbito first (smallest blast radius) and validates before propagating |
| Spike-before-plan flag honored for codegen | ✓ unasync adoption is explicitly spike-gated; libcst is the documented fallback if spike disqualifies it |

---

## Sources

### Context7 (HIGH confidence — authoritative library docs)

- `/jaraco/keyring` — Jaraco Keyring (246 snippets, score 71.67). Fetched: type-declaration support added (NEWS.rst), `AnonymousCredential` model, `store` attribute deprecation. Cross-verified backend behavior on macOS/Linux/Windows.
- `/websites/keyring_readthedocs_io_en` — Python Keyring readthedocs (243 snippets, score 92.67). Cross-verified null-backend / headless CI behavior.

### Official sources / PyPI (HIGH confidence — verified 2026-06-14)

- https://pypi.org/pypi/unasync/json — version 0.6.0 (2024-05-03), deps `tokenize-rt + setuptools`, MIT OR Apache-2.0, requires-python `>=3.8`
- https://pypi.org/pypi/libcst/json — version 1.8.6 (Nov 2025), MIT, requires-python `>=3.9`, deps include `pyyaml>=5.2` (or `pyyaml-ft>=8.0.0` on Py 3.13), classifier `Typing :: Typed`
- https://pypi.org/pypi/keyring/json — version 25.7.0, MIT, requires-python `>=3.9`, Linux deps `SecretStorage>=3.2 + jeepney>=0.4.2`, Windows dep `pywin32-ctypes>=0.2.0`
- https://pypi.org/pypi/cryptography/json — version 49.0.0, Apache-2.0 OR BSD-3-Clause, requires-python `>=3.9 (excluding 3.9.0/3.9.1)`, dep `cffi>=2.0.0`
- https://pypi.org/pypi/platformdirs/json — version 4.10.0 (2026-05-28), MIT, requires-python `>=3.10`, zero deps (`requires_dist: null`), 22743-byte wheel

### Source inspection / GitHub (HIGH confidence)

- https://github.com/python-trio/unasync — confirmed: token-replacement approach, `cmdclass_build_py()` setuptools integration, `Rule(fromdir, todir, additional_replacements={...})` API
- https://github.com/Instagram/LibCST — confirmed: MIT, supports Python 3.0-3.14, 48 releases, latest 1.8.6 (Nov 2025), 129 open issues + 44 PRs (actively maintained)
- https://github.com/jaraco/keyring — confirmed: jaraco-maintained, 1.5k stars, 56 releases, types-keyring not needed (inline typing landed via NEWS.rst entries 2024-2025)
- https://github.com/encode/httpcore — confirmed httpcore uses a custom in-tree `unasync.py` script (`_async/` ↔ `_sync/` directories committed to git) — same pattern recommended here
- https://github.com/encode/httpx/issues/572 — "Supporting Sync. Done right." — confirmed httpx ecosystem direction is unasync-based for sync/async dedup

### Existing codebase context (HIGH confidence — read directly)

- `/Users/sebadlf/development/becerra/market-libs/CLAUDE.md` — v1.2 milestone context
- `/Users/sebadlf/development/becerra/market-libs/.planning/PROJECT.md` — v1.2 scope, spike-before-plan flag for codegen
- `/Users/sebadlf/development/becerra/market-libs/.planning/RETROSPECTIVE.md` — v1.1 lessons: TokenStore spike validated, INT-01 idiom established, structural sync/async duplication identified as v1.2 closure
- `/Users/sebadlf/development/becerra/market-libs/.planning/research/v1.0-v1.1-archived/STACK.md` — v1.0/v1.1 stack baseline (tenacity, ruff/mypy config); NOT under review
- `/Users/sebadlf/development/becerra/market-libs/pyproject.toml` — workspace config, ruff/mypy/import-linter config (per v1.1 close-out)
- `/Users/sebadlf/development/becerra/market-libs/packages/iol-client/pyproject.toml` — package-level dep declaration target for `platformdirs`

### Notes on confidence levels

- **HIGH** for all primary recommendations: `platformdirs` (verified PyPI metadata + Context7 docs + zero-deps confirmed), `unasync` (verified via httpcore + elasticsearch-py + trio production use), rejection of `keyring` (verified via official Headless CI docs + macOS GUI prompt behavior)
- **MEDIUM** for `libcst` fallback ranking (depends on what the spike finds — only relevant if unasync is disqualified)
- **MEDIUM** for `cryptography` deferral (operator may choose to expand threat model; the recommendation here is to NOT pre-emptively adopt)

---

*Stack research for: market-libs v1.2 Architecture + Auth/Ergonomics Carry-forwards*
*Researched: 2026-06-14*
*Confidence: HIGH (primary recommendations) / MEDIUM (fallback paths)*
*Spike-before-plan flag honored for codegen tooling — final pick gated on Phase-level spike report; this Stack narrows the candidate list to unasync (primary) + libcst (fallback) and explicitly vetoes ast-grep/comby/Jinja2*
