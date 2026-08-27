---
phase: 32
slug: gates-de-homogeneidad-d-16
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-26
---

# Phase 32 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register built from the `<threat_model>` blocks of all six plans (32-01..32-06),
> all of which were authored at plan time (`register_authored_at_plan_time: true`).
> Preliminary classification at ASVS L1 grep-depth found `threats_open: 0`, so per
> the secure-phase short-circuit rule (threats_open: 0 AND register_authored_at_plan_time:
> true AND asvs_level == 1) this audit skipped the deep-verification auditor subagent.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CI runner → repository source | Typecheck/lint gates read repository source only; no network, no credentials | source code, AST |
| test process → per-package `.env` files | Must never be crossed — `caplog`/parity assertions are type-not-value by construction | none (must stay none) |
| gate process → per-package `.env` files | Gate scripts scan `packages/*/src/**/*.py` via `ast.parse`; never import a package (which would run `load_dotenv()`) | source code paths, symbol names |
| planning artefact → published package surface | D-09 decision record is the control point where a `.planning/` decision becomes authority to change a shipped public API | decision text |
| test process → tracked working tree | One RED fixture (32-05 Task 2) mutates `_core.py` under `try/finally` restore + byte-equality assertion | file bytes (restored) |
| test process → subprocess | `lint-imports` invoked via `shutil.which`, fixed argv, `shell=False` | argv only |
| local reproduction → real CI | Local matrix run is a proxy for the 12-leg GitHub Actions matrix; the gap was named and closed by the real run in this UAT session | CI status |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-32-01 | Information Disclosure | `tools/check_surface_types.py` | low | mitigate | AST/text reads only; import set is a subset of `{ast, sys, pathlib, dataclasses}` (verified) | closed |
| T-32-02 | Information Disclosure | Gate failure annotations on PR | low | mitigate | Messages carry relative paths + symbol names only; no file content outside `packages/*/src` scope | closed |
| T-32-03 | Tampering | Untrusted source parsing | medium | mitigate | `ast.parse` only, never `eval`/`exec`; unparseable file is a `CheckFailure`, never a skip | closed |
| T-32-04 | Repudiation | Gate passing vacuously (phase's own primary threat) | medium | mitigate | 4 independent RED cases (module/class regression, empty scan, unresolvable root) + floor assertions on real-tree scan counts; verified in `32-02-SUMMARY.md` | closed |
| T-32-05 | Tampering | CI wiring made non-blocking | medium | mitigate | No failure-suppression key in `ci.yml`; step placed inside `lint` job — confirmed live in this session's CI run | closed |
| T-32-06 | Denial of Service | Unbounded tree walk | low | accept | Scope is `packages/*/src` in a 6-package monorepo; no untrusted input controls tree size | closed |
| T-32-07 | Information Disclosure | `caplog` assertions in repaired decode tests | low | mitigate | Fixes limited to annotations/ignores/call shape; no assertion prints a wire value; per-package SEC-01 sentinel re-run green | closed |
| T-32-08 | Repudiation | Typecheck gate itself | medium | mitigate | Exact `ci.yml:92-99` per-package loop re-run individually; all 6 packages print `Success: no issues found` | closed |
| T-32-09 | Tampering | `pyproject.toml` strictness policy | medium | mitigate | `git diff --stat -- pyproject.toml` empty across Tasks 1-2 (verified) | closed |
| T-32-10 | Repudiation | D-09 decision record | low | mitigate | SUMMARY names both selected/rejected option and explicit-vs-auto-resolved provenance (`32-03-SUMMARY.md`) | closed |
| T-32-11 | Elevation of Privilege | Scope creep through decision gate | medium | mitigate | Decision scoped to `market_data_client.aio.configure` only; roster expansion explicitly deferred and restated | closed |
| T-32-12 | Tampering | Source files changed during decision-only plan | low | mitigate | `git status --porcelain` over `packages tools .github pyproject.toml` empty (verified) | closed |
| T-32-13 | Information Disclosure | Parity failure messages | low | mitigate | Symbol names + resolved type strings only; type-not-value by construction | closed |
| T-32-14 | Information Disclosure | `load_dotenv()` executed by helper imports | low | accept | Unavoidable for introspection; helper never reads `os.environ`; per-package SEC-01 sentinels remain the credential-leak net | closed |
| T-32-15 | Repudiation | Parity test comparing nothing | medium | mitigate | `compared_hints >= MODULE_LOWER_BOUNDS[package][0]`; `get_type_hints` failures propagate, per-package integer floors | closed |
| T-32-16 | Tampering | Public parameter accepted and discarded | medium | mitigate | AST assertion `http_client` assigned onto `_state.http_client` + runtime hint assertion | closed |
| T-32-17 | Denial of Service | Connection-pool leak from swapping live transport | medium | mitigate | `ResourceWarning` on replacing a different live client, remedy named | closed |
| T-32-18 | Tampering | Scope creep into deferred rosters | low | mitigate | `git status --porcelain -- verification/` empty; deferral recorded with file path | closed |
| T-32-19 | Tampering | Mutating a tracked source file | medium | mitigate | `try/finally` restore + byte-equality assertion + green re-run; `git status --porcelain` empty after suite | closed |
| T-32-20 | Tampering | Subprocess invocation | medium | mitigate | `shutil.which` resolution, fixed single-element argv, `shell=False`, nothing interpolated | closed |
| T-32-21 | Repudiation | RED test passing for the wrong reason | medium | mitigate | Both legs assert contract name + state marker; exit-code-only assertions prohibited | closed |
| T-32-22 | Denial of Service | Gate silently skipping when tool absent | medium | mitigate | Missing `lint-imports` is an assertion failure, never a `pytest.skip` | closed |
| T-32-23 | Information Disclosure | Linter output in test failure message | low | mitigate | Contract names + module paths only; never reads `.env` | closed |
| T-32-24 | Tampering | Configuration scope creep | low | mitigate | `root_packages`/contract blocks unedited; `_PACKAGES` kept 4 entries; 6 rosters untouched | closed |
| T-32-25 | Repudiation | Package passing parity axis vacuously | medium | mitigate | wallets asserts absence positively; 0 skip/xfail across 6 files; non-vacuity demonstrated by injection | closed |
| T-32-26 | Repudiation | Green claim covering less than full matrix | medium | mitigate | Gap named explicitly in SUMMARY; **closed by this UAT session's real GitHub Actions run** (PR #12, run 32968322676 — all 4 jobs + 12 test legs green) | closed |
| T-32-27 | Tampering | Weakening helper to turn a package green | medium | mitigate | `git diff HEAD~1 -- tools/surface_parity.py` = 0 lines; `Normalization rule added` section records no rule added | closed |
| T-32-28 | Information Disclosure | Parity failure messages across 6 packages | low | mitigate | Symbol names + resolved type strings only; per-package SEC-01 sentinels re-run | closed |
| T-32-29 | Information Disclosure | `load_dotenv()` executed by six packages' imports | low | accept | Already true of every existing package test; helper never touches `os.environ` | closed |
| T-32-SC | Tampering | Package-manager installs (uv/pip) — shared across all 6 plans | medium | accept | Zero external packages installed in the whole phase; `uv lock --check` is the first `lint` step and fails on lockfile movement — confirmed green in this session's real CI run | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `high` (workflow.security_block_on) count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

No threat in this register reaches `high` or `critical` severity — the phase adds CI gates and type-parity checks over an already-trusted source tree, with no new network endpoint, auth path, or credential-adjacent surface.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-32-01 | T-32-06 | Unbounded tree walk scoped to `packages/*/src` in a fixed 6-package monorepo; no untrusted input controls size | Plan 32-02 author | 2026-08-26 |
| AR-32-02 | T-32-14, T-32-29 | `load_dotenv()` runs on every existing package test's import; helper never reads `os.environ`; per-package SEC-01 caplog sentinels remain the credential-leak net | Plans 32-04, 32-06 authors | 2026-08-26 |
| AR-32-03 | T-32-SC | Zero external packages installed anywhere in Phase 32; `uv lock --check` enforced as the first `lint` step (verified green in real CI) | Plans 32-01..32-06 authors | 2026-08-26 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-26 | 30 | 30 | 0 | /gsd-secure-phase orchestrator (Claude, ASVS L1, register from PLAN.md threat models) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-26
