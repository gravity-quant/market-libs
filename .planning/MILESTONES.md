# Milestones

## v1.3 Codegen Single-Source (libcst) (Closed: 2026-07-03 — signed NO-GO)

**Phases completed:** 1 phase (18; Phase 19 REFAC-06 DROPPED), 3 plans, 7 tasks
**Git range:** `6d3b749` (docs: start milestone v1.3) → `1333d5f` (docs(phase-18): auto-close todo), 2026-07-02 → 2026-07-03 (23 commits)
**Source delta:** 0 production files — **zero footprint**. The entire milestone lived under `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/` with `libcst` invoked ephemerally (`uv run --with libcst`, never added to dev deps per D-05).

**Outcome:** Signed **NO-GO** (`sebadlf`, 2026-07-03). CODEGEN-01 resolved; REFAC-06 permanently shelved; Phase 19 dropped; duplicate `client.py`/`aio.py` transport shells accepted as a structural feature. A valid, guaranteed milestone deliverable per D-08 (the milestone delivered a signed architectural decision, not code). libcst is a partial gain over unasync — it closes item 4 (`ruff check` I001 + ASYNC1xx) that SPIKE-005 could not — but two independent tools now reach the same strict-D-04 NO-GO for the same content-absence / source-shape-asymmetry root cause.

**Key accomplishments:**

- Stood up the SPIKE-006 libcst spike tree and landed the ~60% inherited D-RIGOR-02 harness — item 10a matriz construct audit (0 unresolved / 959 LOC, verbatim audit.py), item 8 @generated marker via libcst Module.header (STRICT PASS, all 4 commands exit 0), and item 10b matriz 4-file deny-list sha256 byte-identity under per-module libcst scope — with the libcst supply-chain gate operator-approved and libcst kept ephemeral.
- Authored the genuinely-new core of SPIKE-006 — five pure libcst `CSTTransformer` subclasses + an impure driver that transform the un-migrated ámbito `aio.py` into a candidate sync `client.py` — and captured the honest D-RIGOR-02 gate transcript: item 4 (GO-det, `ruff check`) now PASSES (the item unasync failed), but items 1 and 6 (GO-det) FAIL for the exact SPIKE-005 source-shape root cause — `_validate_max_retries` def + `load_dotenv` bootstrap are content-absent from `aio.py` and cannot be synthesized by any pure transform — a signed same-root-cause NO-GO that is a valid, guaranteed deliverable (D-04/D-08), reached without editing `aio.py` or reading `client.py` as a donor.
- Operator-signed SPIKE-006 NO-GO (sebadlf, 2026-07-03) — 7 PASS / 3 FAIL on the 10-item D-RIGOR-02 gate (items 1/3/6 FAIL, same content-absence root cause as SPIKE-005) → REFAC-06 permanently shelved, Phase 19 dropped, zero production footprint.

**Known deferred items at close:** 0 (pre-close artifact audit clear — all artifact types clean). No milestone audit was run: with 2/2 requirements resolved and a spike-only milestone that shipped no code, the signed NO-GO is itself the complete deliverable.

---

## v1.2 Architecture + Auth/Ergonomics Carry-forwards (Shipped: 2026-06-25)

**Phases completed:** 5 phases (12-15, 17; Phase 16 dropped), 18 plans, 40 tasks
**Git range:** `74b22bf` (docs(12): capture phase context) → `a7dbc8f` (ship v1.2 — PR #2), 2026-06-14 → 2026-06-25
**Source delta:** 43 files changed, +3,364 / −531 LOC (packages + drivers + pyproject)

**Key accomplishments:**

- **Phase 12 — Codegen tool-choice spike (REFAC-06, NO-GO):** SPIKE-005 ran unasync round-trip on the ámbito canary + a matriz worst-case construct audit (109 rows, 0 unresolved); the strict D-RIGOR-01 8-item evidence checklist returned **3/8 FAIL — all tracing to a single root cause (source-shape asymmetry between v1.1 sync-first `aio.py` and async-first codegen), 0 unfixable hunks** — so the operator signed NO-GO and REFAC-06 was cleanly deferred to v1.3 with a libcst handoff scope + auto-loaded findings skill.
- **Phase 13 — `client.with_options(max_retries=N)` × 4 packages (ERG-01):** a shallow-clone Client view that shares the underlying `httpx.Client` + `_ClientState` (no resource leak, no re-auth) and threads the override via `request.extensions['max_attempts']` mirroring the v1.1 mutation-gate pattern; the CRITICAL merge gate proves matriz `new_order` under 503 executes **EXACTLY 1 outgoing request regardless of `max_retries=10`** (anti-Pitfall 14, duplicate-order money-on-the-line).
- **Phase 14 — IOL refresh_token disk persistence (SEC-01):** `iol_client/_token_cache.py` with atomic write-then-rename, `fcntl.flock` inter-process locking, 0600 perms, `platformdirs` default path (iol-client only), and CI-refuses-default-path; the three CRITICAL gates land GREEN across sync + async — caplog no-leak sentinel, 20-thread concurrent-write race, and failed-refresh disk cleanup — with `asyncio.to_thread` dispatch for the async mirror.
- **Phase 15 — Driver migration × 4 (REFAC-05):** every `main_*.py` now constructs **exactly one `Client()` / `AsyncClient()` per `main()` run** with all probes threaded through that single instance (ámbito → iol → higyrus → matriz), guarded by a RED-first AST single-Client regression test per driver; probe names / finding titles stay byte-stable vs the v1.1 LIVE-01 baseline `71bf201`, closing the v1.1 iol/matriz LOC-drop residual.
- **Phase 17 — Final live re-verification × 4 (LIVE-03):** operator dispositions captured for ambito/iol/higyrus/matriz, schema snapshot vs baseline `verification-cycle-2026-Q2` clean, `verify_cycle_closure × 4` PASS (iol F-02 FIXED→regression-linked), REQUIREMENTS.md traceability flipped to Complete for REFAC-05/SEC-01/ERG-01/LIVE-03, 0-BLOCKER integration audit, pytest final ≥989 / CI matrix green on Python 3.12 + 3.13.

**Known deferred items at close:** 6 (see STATE.md Deferred Items — 4 stale v1.1-era quick-task status files, the intentional REFAC-06→v1.3 libcst spike todo, and the Phase 15 operator UAT gap superseded by the Phase 17 LIVE-03 gate). REFAC-06 deferred to v1.3.

---

## v1.1 Tech Debt Cleanup (Shipped: 2026-06-14)

**Phases completed:** 6 phases, 30 plans, 52 tasks

**Key accomplishments:**

- Public-surface snapshot test (`inspect.signature` over `__all__`) sweeping ambito/iol/higyrus/matriz with W3-pinned text golden files, deterministic regen script, and Phase 6 entry-baseline (281 tests / 95% coverage / git_sha-anchored) committed BEFORE any per-package Client class refactor lands.
- Per-package guard tests proving that a sentinel monkeypatched onto each module-level `_token` reaches the wire-level `Authorization` (iol/higyrus) / `X-Auth-Token` (matriz) header — and that `configure(base_url=...)` reaches the wire URL for the no-auth ambito case — with 7 passing + 1 matriz-async permanent skip.
- First per-package skeleton landed: `ambito_financiero_client.Client` (sync) + `AsyncClient` (async) with per-instance `_ClientState`, PEP 562 read-only `__getattr__` shim, carry-forward `configure()` semantics, redacted `__repr__`, pickle/deepcopy bans, and snapshot regeneration — all 4 ambito test suites + the cross-package public-surface guard + the Plan 06-02 fixture-reaches-production guard pass against the refactored client.
- Phase 6 CI matrix proven green end-to-end on Python 3.12 AND 3.13 (389 passed, 1 skipped on each) — mutation_gate audit PASSED unchanged.
- Instalación + configuración de `import-linter` v2.11 con 4 forbidden contracts declarativos + 4 `_core.py` placeholders + runtime cross-leak guard parametrizado — las dos CI gates de Phase 7 (REFAC-03) quedan operativas antes del primer refactor.
- Extracción mecánica del patrón `_core.py + transport shell` aplicado a `ambito_financiero_client` como canary del refactor Phase 7 — validó el patrón completo (RequestSpec + builders + parsers + raise_for_response moved + D-04 alias + B8 identity + 3-liner endpoint shells) con drop agregado de 31.2% LOC en client+aio y zero regresión.
- iol `_core.py` extracts OAuth password-grant + refresh-token auth-flow as pure builders/parsers (with CR-01 conditional rotation preserved structurally) plus 4 endpoint builder/parser pairs; transport shells (client.py + aio.py) collapse to 3-liner endpoint methods, D-04 alias preserves B8 identity.
- Wave-3 consolidation plan that gathers evidence the 5 Phase 7 ROADMAP success

criteria are satisfied across the full gate matrix and produces a single
`07-VALIDATION.md` with `nyquist_compliant: partial` (honest 4/5 PASS + 1
PARTIAL signal; the LOC-drop deviation in criterion #3 is documented in
Plans 07-03 and 07-05 SUMMARYs; operator decides at the Task 2 human-verify
checkpoint whether 'partial' is acceptable for phase close-out).

- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- 8 mocked regression tests (4 sync + 4 async) lockean los 4 paths del `_state.refresh_token` lifecycle en `iol-client` — CR-01 conditional rotation guard + D-IOL-10 refresh→password fallback + D-IOL-09 async double-checked locking quedan fijados sin tocar `_core.py` / `client.py` / `aio.py` / `_state.py`.
- Per-call `id_cuenta` regression test (mocked 2-cuentas) + driver probe with CSV override + cross-package `_state.account_id` cleanup + BUG-02 quick-triage closure (bucket a NO-FIX) + Phase 6 migration drift repair (shim hardening).
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:

---

## v1.0 Verification cycle (Shipped: 2026-06-10)

**Phases completed:** 5 phases, 18 plans, 27 tasks

**Key accomplishments:**

- Root conftest live/offline split (`--live` deselect-by-default), the importable non-published `verification/` package, and defense-in-depth `redact`/`safe_print` credential masking — all unit-proven including the empty-secret corruption guard.
- Two stdlib-only hard safety gates — a credential `require_env` emitting the verbatim `SKIPPED <pkg>: missing X, Y` line, and a `mutating_allowed` double-gate (`VERIFY_MUTATING=1` AND a live-resolved `remarkets` base URL) that fails safe even against a prod-URL bypass — each TDD-proven.
- AMB-01..AMB-06 verificados en vivo contra mercados.ambito.com; cero bugs detectados; baseline DRIFT-01 + Phase 2 findings file committeados al repo.
- OAuth2 `grant_type=refresh_token` with fallback to password grant implemented in IOL client `client.py` + `aio.py` dual surfaces, plus 4+4 pytest-httpx regression tests locking the four code paths (login capture, refresh success, refresh→password fallback, both fail).
- Fix dual sync+async: `_request` ahora pre-attachea el query string con `urlencode(... safe="/")` para preservar `/` literal en el wire, evitando que Higyrus IIS rechace el formato `dd/mm/yyyy` con HTTP 400.
- Live run contra remarkets PASS=17/FAIL=0/SKIPPED=9/FINDING=2; suite mockeada Phase 5 lockea 12 invariantes Verified-live + 11 MATZ-06 mock-only contract con 3 sentinels GET-quirk §6.3; cycle_closure × 4 pkgs PASS confirma DRIFT-02 helper promotion funcionando end-to-end
- DRIFT-02 baseline canónico creado: 4 findings files con `## Cycle Closure` + `CYCLE-REPORT.md` consolidando 14 findings / 18 schemas / 4 paquetes; `verify_cycle_closure × 4` reporta 3 PASS (ámbito/iol/higyrus sin CONFIRMED/FIXED) + 1 FAIL (matriz F-09 deferred) — la FAIL es la señal DRIFT-02 activa por diseño

---
