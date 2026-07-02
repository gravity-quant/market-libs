# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
- 🚧 **v1.3 Codegen Single-Source (libcst)** — Phases 18-19 (in progress) — spike-gated REFAC-06 (SPIKE-006 GO/NO-GO)

## Phases

<details>
<summary>✅ v1.0 Verification cycle (Phases 1-5) — SHIPPED 2026-06-10</summary>

- [x] Phase 1: Safety Harness & Verification Infrastructure (4/4 plans) — completed 2026-05-28
- [x] Phase 2: Ámbito Verification (3/3 plans) — completed 2026-06-05
- [x] Phase 3: IOL Verification (3/3 plans) — completed 2026-06-06
- [x] Phase 4: Higyrus Verification (4/4 plans) — completed 2026-06-08
- [x] Phase 5: Matriz Verification (4/4 plans) — completed 2026-06-10 (DRIFT-02 cycle closure baseline `verification-cycle-2026-Q2`)

Full details: [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
Requirements archive: [`milestones/v1.0-REQUIREMENTS.md`](./milestones/v1.0-REQUIREMENTS.md)
Audit: [`milestones/v1.0-MILESTONE-AUDIT.md`](./milestones/v1.0-MILESTONE-AUDIT.md)

</details>

<details>
<summary>✅ v1.1 Tech Debt Cleanup (Phases 6-11) — SHIPPED 2026-06-14</summary>

- [x] Phase 6: Compat Safety Net + Client Class Skeleton (7/7 plans) — completed 2026-06-11 — `Client`/`AsyncClient` per package + PEP 562 compat shim; REFAC-01/02
- [x] Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup (6/6 plans) — completed 2026-06-12 — pure builders/parsers + import-linter contracts; REFAC-03 + CR-03/05
- [x] Phase 8: Retries, Backoff, Structured Logging (6/6 plans) — completed 2026-06-13 — `tenacity` full-jitter + mutation gate + `RedactingFilter`; RELY-01..04 + LOG-01..03
- [x] Phase 9: Deferred Bug Fixes (4/4 plans) — completed 2026-06-13 — BUG-01..04 (2 operator overrides)
- [x] Phase 10: matriz `aio.py` Creation + TokenStore (4/4 plans) — completed 2026-06-14 — 852 LOC async REST + `TokenStore` 3-way concurrency + `_atransport.py`; REFAC-04 + LIVE-02
- [x] Phase 11: Harness Hardening + Code Review Close-out + Live Re-verification (3/3 plans) — completed 2026-06-14 — append-only findings + idempotent dedupe + LIVE-01 final gate × 4 packages (iol F-02 fixed inline); HARN-07..10 + CR-01/02/04/06/07/08 + LIVE-01

Full details: [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
Requirements archive: [`milestones/v1.1-REQUIREMENTS.md`](./milestones/v1.1-REQUIREMENTS.md)
Audit: [`milestones/v1.1-MILESTONE-AUDIT.md`](./milestones/v1.1-MILESTONE-AUDIT.md)
Phase artifacts: [`milestones/v1.1-phases/`](./milestones/v1.1-phases/)

</details>

<details>
<summary>✅ v1.2 Architecture + Auth/Ergonomics Carry-forwards (Phases 12-17) — SHIPPED 2026-06-25</summary>

- [x] Phase 12: Codegen Spike (4/3 plans) — completed 2026-06-14 — SPIKE-005 unasync vs libcst on ámbito canary + matriz worst-case; **NO-GO** (strict D-RIGOR-01 reading, 3/8 items FAIL, source-shape asymmetry, 0 unfixable hunks); REFAC-06 deferred to v1.3; REFAC-06 (spike-gated)
- [x] Phase 13: Cross-Package Ergonomics `with_options(max_retries=N)` (5/5 plans) — completed 2026-06-15 — shared-view clone + `request.extensions["max_attempts"]`; CRITICAL matriz mutation-gate merge gate (new_order under 503 = exactly 1 request); ERG-01
- [x] Phase 14: IOL Disk Persistence (3/3 plans) — completed 2026-06-24 — `_token_cache.py` + `platformdirs` + atomic write + `fcntl.flock` + 0600 + failed-refresh cleanup + caplog no-leak; SEC-01
- [x] Phase 15: Driver Migration × 4 (5/4 plans) — completed 2026-06-24 — ONE `Client()`/`AsyncClient()` per `main()` + AST regression-guard × 4 + probe-name stability vs LIVE-01 `71bf201`; REFAC-05
- ~~Phase 16: Codegen Single-Source — DROPPED 2026-06-14 (Phase 12 NO-GO); REFAC-06 → v1.3~~
- [x] Phase 17: Final Live Re-verification × 4 (3/3 plans) — completed 2026-06-25 — operator dispositions ambito/iol/higyrus/matriz + cycle closure × 4 PASS + traceability flip + 0-BLOCKER integration audit; LIVE-03

Full details: [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
Requirements archive: [`milestones/v1.2-REQUIREMENTS.md`](./milestones/v1.2-REQUIREMENTS.md)

</details>

### 🚧 v1.3 Codegen Single-Source (libcst) — Phases 18-19 (in progress)

- [ ] **Phase 18: libcst Codegen Tool-Choice Spike (SPIKE-006)** — RESEARCH FLAG / spike-before-plan; evaluate `libcst >=1.8.0,<2` against the `D-RIGOR-02` 10-item gate on the ámbito v1.2-head canary + matriz audit/deny-list inheritance → signed **GO/NO-GO** (CODEGEN-01). ALWAYS runs; guaranteed milestone deliverable.
- [ ] **Phase 19: Codegen Single-Source × 4 Packages (REFAC-06)** — **CONDITIONAL on Phase 18 GO — DROPPED if NO-GO**; single-source `client.py`/`aio.py` transport shells (ámbito → iol → higyrus → matriz) via libcst with `@generated` marker + CI `lint-codegen` verify-clean + B8 identity preserved.

> **Milestone note — spike-gated conditional structure.** v1.3 honors locked decision **D-NOGO-01** (v1.2 Phase 12 NO-GO). Phase 18 (SPIKE-006) runs FIRST and is the milestone's *guaranteed* deliverable: it produces a signed GO/NO-GO regardless of outcome. Phase 19 (REFAC-06) is implemented **only if** Phase 18 returns GO. If the 3 previously-failing gate items (1 byte-identical, 4 ruff-check import-order, 6 mocked-suite-green) FAIL again under libcst, **REFAC-06 is shelved permanently** — the duplicate `client.py`/`aio.py` shells become an accepted structural feature and the milestone closes on the signed NO-GO. This mirrors the v1.2 Phase 16 "DROPPED if Phase 12 NO-GO" precedent exactly. Per the in-cycle verification convention (REQUIREMENTS.md), no full live re-run × 4 is planned: byte-identical generated output means wire behavior is unchanged by construction, so the D-RIGOR-02 item-1 (byte-identical) + item-6 (mocked suite green) gates fold milestone-close verification into Phase 19.

## Phase Details (v1.3)

### Phase 18: libcst Codegen Tool-Choice Spike (SPIKE-006)
**Goal**: Produce a signed GO/NO-GO decision on whether `libcst >=1.8.0,<2` (AST-level codemod) can single-source the sync/async transport shells — evaluated against the `D-RIGOR-02` 10-item gate on the ámbito canary in its **v1.2-head shape (NOT migrated)** plus inheritance of the matriz construct audit + deny-list intactness. This is a **RESEARCH FLAG / spike-before-plan** phase (same pattern as v1.2 Phase 12); it ALWAYS runs and its signed decision is the milestone's guaranteed deliverable.
**Depends on**: Nothing (first v1.3 phase; builds on the v1.2 Phase 12 NO-GO learnings — `Skill("spike-findings-codegen-market-libs")` auto-loads them)
**Requirements**: CODEGEN-01
**Success Criteria** (what must be TRUE):
  1. The operator holds a **signed GO/NO-GO decision** (`DECISION.md`) with a recorded per-item verdict for every one of the 10 `D-RIGOR-02` gate items.
  2. The **3 GO-determining items** — item 1 (byte-identical round-trip vs hand-written `client.py`, no source migration), item 4 (`ruff check` clean incl. single-line import-order), item 6 (ámbito mocked suite green vs generated, no circular self-import) — each have a captured PASS/FAIL transcript against the **un-migrated ámbito v1.2-head canary**.
  3. The **8 inherited SPIKE-005 items** (B8 identity, `@generated` marker × `from __future__ import annotations`, `ruff format --check`, `mypy --strict`, `lint-imports` 4 contracts) plus the **2 new libcst-specific items** (item 9 CSTTransformer purity `CSTNode → CSTNode`, item 10 matriz audit + deny-list intactness under `libcst.MetadataWrapper`) each have a recorded verdict.
  4. The matriz deny-list files (`_token_store.py`, `_refresh_policy.py`, `_refresh.py`, `ws_client.py`) are re-verified sha256-byte-identical pre/post — confirmed OUT of codegen scope (spike CONFIRMS, does not renegotiate).
  5. On **GO**: per-package CSTTransformer drafts (import-direction normalizer, single-line import-order normalizer, docstring localizer) exist as the Phase 19 handoff artifact. On **NO-GO**: REFAC-06 is marked permanently shelved and the milestone closes on the signed NO-GO.
**Plans**: TBD

### Phase 19: Codegen Single-Source × 4 Packages (REFAC-06)
**Goal**: **CONDITIONAL on Phase 18 GO.** If SPIKE-006 returns GO, single-source the `client.py`/`aio.py` transport shells of the 4 verifiable packages (ámbito → iol → higyrus → matriz) via libcst codegen — with a `@generated` marker, a CI `lint-codegen` verify-clean job, and B8 identity preserved — so the structural sync/async duplication is eliminated without changing observable wire behavior. **DROPPED entirely if Phase 18 returns NO-GO**: REFAC-06 is shelved permanently, the duplicate shells are accepted as a structural feature, and the milestone closes on the signed NO-GO.
**Depends on**: Phase 18 (GO decision)
**Requirements**: REFAC-06
**Success Criteria** (what must be TRUE):
  1. Running the codegen entrypoint (`make codegen` / `uv run --with libcst scripts/codegen.py` or equivalent) regenerates all 8 transport shells **byte-identically**; `make codegen-check` → `git diff --exit-code` passes clean in CI (a hand-edit over a generated file FAILS CI — anti-Pitfall 5).
  2. Each generated `client.py`/`aio.py` carries the `@generated by libcst` marker (PEP 263/236) and passes `ruff format`/`ruff check`/`mypy --strict`/`import-linter` (4 contracts) clean across all 8 files.
  3. The **B8 identity** test (`client._raise_for_response is aio._raise_for_response is _core.raise_for_response`) passes and runs FIRST in CI (anti-Pitfall 4 — no thunk-wrapper).
  4. The mocked pytest-httpx suites (sync + async) pass green against the generated code for all 4 packages — the primary wire-behavior verification per the in-cycle convention.
  5. The matriz deny-list files (`_token_store.py`, `_refresh_policy.py`, `_refresh.py`, `ws_client.py`) remain untouched (sha256-identical); codegen applies ONLY to the `client.py`/`aio.py` transport shells; `libcst >=1.8.0,<2` lands in root `[dependency-groups] dev` (dev-only, no runtime dep changes).
**Plans**: TBD

## Progress

| Phase                                                       | Milestone | Plans | Status      | Completed  |
|-------------------------------------------------------------|-----------|-------|-------------|------------|
| 1. Safety Harness & Verification Infrastructure             | v1.0      | 4/4   | Complete    | 2026-05-28 |
| 2. Ámbito Verification                                      | v1.0      | 3/3   | Complete    | 2026-06-05 |
| 3. IOL Verification                                         | v1.0      | 3/3   | Complete    | 2026-06-06 |
| 4. Higyrus Verification                                     | v1.0      | 4/4   | Complete    | 2026-06-08 |
| 5. Matriz Verification                                      | v1.0      | 4/4   | Complete    | 2026-06-10 |
| 6. Compat Safety Net + Client Class Skeleton                | v1.1      | 7/7   | Complete    | 2026-06-11 |
| 7. `_core.py` Extraction — Sync/Async Logic Dedup           | v1.1      | 6/6   | Complete    | 2026-06-12 |
| 8. Retries, Backoff, Structured Logging                     | v1.1      | 6/6   | Complete    | 2026-06-13 |
| 9. Deferred Bug Fixes                                       | v1.1      | 4/4   | Complete    | 2026-06-13 |
| 10. matriz `aio.py` Creation + TokenStore                   | v1.1      | 4/4   | Complete    | 2026-06-14 |
| 11. Harness Hardening + Code Review + Live Re-verification  | v1.1      | 3/3   | Complete    | 2026-06-14 |
| 12. Codegen Spike                                           | v1.2      | 4/3   | Complete    | 2026-06-14 |
| 13. Cross-Package Ergonomics (`with_options`)               | v1.2      | 5/5   | Complete    | 2026-06-15 |
| 14. IOL Disk Persistence                                    | v1.2      | 3/3   | Complete    | 2026-06-24 |
| 15. Driver Migration × 4                                    | v1.2      | 5/4   | Complete    | 2026-06-24 |
| 16. Codegen Single-Source (DROPPED — Phase 12 NO-GO)        | v1.2      | -     | Dropped     | 2026-06-14 |
| 17. Final Live Re-verification × 4                          | v1.2      | 3/3   | Complete    | 2026-06-25 |
| 18. libcst Codegen Tool-Choice Spike (SPIKE-006)            | v1.3      | 0/?   | Not started | -          |
| 19. Codegen Single-Source × 4 (CONDITIONAL on Phase 18 GO)  | v1.3      | 0/?   | Not started | -          |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2 milestone audits deferred sections)*

### Deferred to v1.4+ (from v1.3 planning)

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff — still deferred through v1.0/v1.1/v1.2/v1.3)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread)
- `cryptography.fernet` token encryption at-rest (operator authorization required; threat-boundary expansion)
- Code-review CR-01 v1.2 Phase 14 (`configure()` no limpia el on-disk token cache de IOL)
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)

### Now active in v1.3

- **REFAC-06** — codegen single-source for `client.py`/`aio.py` transport shells × 4 packages. Was deferred at v1.2 close (Phase 12 unasync NO-GO, source-shape asymmetry); now the v1.3 milestone via a `libcst >=1.8.0,<2` AST-level spike (Phase 18 SPIKE-006) that gates the conditional Phase 19 implementation. See `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md` + `.planning/todos/pending/spike-codegen-libcst-v1.3.md`.

### Deferred to v1.2+ (from v1.1 planning — REFAC-05/SEC-01/ERG-01 shipped in v1.2)

- Automatic `Idempotency-Key` header para retried POSTs
- `findings.toml` machine-readable side-file
- `Client.from_env()` classmethod for explicit env-reading (SKIPPED v1.2 — industry survey found ZERO SDKs with this pattern; implicit env fallback already exists)
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2 requirements del v1.0 backlog
