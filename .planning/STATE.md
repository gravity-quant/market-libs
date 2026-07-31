---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: market-data-client mutaciones
status: planning
last_updated: "2026-07-31T19:22:56.326Z"
last_activity: 2026-07-31
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-31 after v1.4 milestone close)

**Core value:** Cada divergencia entre un cliente y su API en vivo debe ser detectada, documentada y corregida. (v1.5 extiende `market-data-client` v0.2.0 —solo lectura— con la superficie de **escritura** de la API primary-extractor: symbols + calendar, detrás de un mutating-gate de seguridad load-bearing, verificada en vivo de forma segura contra develop, y publicada v0.3.0.)

**Current focus:** v1.5 roadmap creado (Phases 25-28) — next: `/gsd-plan-phase 25` (Mutating-gate + Symbols write)

## Current Position

Phase: 25 (Mutating-gate + Symbols write) — Not started
Plan: —
Status: Roadmap complete, awaiting phase planning
Last activity: 2026-07-31 — v1.5 roadmap created (Phases 25-28, 5/5 requirements mapped)

## Performance Metrics

**Velocity (v1.0 archived):**

- Total plans completed: 76 (v1.0)
- Total tasks completed: 27 (v1.0)
- v1.0 duration: 2026-05-28 → 2026-06-10 (~13 days, 5 phases)

**By Phase (v1.0):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 01    | 4     | Complete | Safety harness baseline |
| 02    | 3     | Complete | Ámbito (smallest blast radius) |
| 03    | 3     | Complete | IOL (OAuth refresh_token) |
| 04    | 4     | Complete | Higyrus (largest surface; 24+ regressions) |
| 05    | 4     | Complete | Matriz (sync only; 19 regressions; DRIFT-02 closure) |

**By Phase (v1.1 shipped 2026-06-14):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 06    | 7     | Complete | Compat safety net + Client/AsyncClient classes + PEP 562 shim (REFAC-01/02) |
| 07    | 6     | Complete | `_core.py` extraction + import-linter contracts (REFAC-03 + CR-03/05; LOC drop partial, v1.2 carry-forward) |
| 08    | 6     | Complete | `tenacity` retries + full-jitter backoff + mutation gate + `RedactingFilter` (RELY-01..04 + LOG-01..03) |
| 09    | 4     | Complete | 4 deferred bug fixes (BUG-01..04, 2 operator overrides) |
| 10    | 4     | Complete | matriz `aio.py` 852 LOC + TokenStore 3-way + `_atransport.py` (REFAC-04 + LIVE-02) |
| 11    | 3     | Complete | findings.py append-only + 6 CR fixes + LIVE-01 final gate × 4 packages (HARN-07..10 + CR-01/02/04/06/07/08 + LIVE-01) |

- v1.1 duration: 2026-06-11 → 2026-06-14 (~3.5 days, 6 phases, 30 plans, 52 tasks)
- v1.1 git stats: 179 commits, 307 files changed, +76,286 / −3,538 LOC
- Test suite: 277 (v1.0 close) → 907/908 (v1.1 close) on Python 3.12 local
- Quick tasks: 3 (260611-u0v, 260613-nwb, 260614-de5)

**By Phase (v1.2 shipped 2026-06-25):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 12    | 4/3   | Complete | Codegen tool-choice spike (unasync vs libcst) — **NO-GO** (3/8 D-RIGOR-01 FAIL, source-shape asymmetry); REFAC-06 → v1.3; REFAC-06 (spike) |
| 13    | 5     | Complete | `with_options(max_retries=N)` × 4 packages; CRITICAL matriz mutation-gate merge gate (new_order under 503 = exactly 1 request); ERG-01 |
| 14    | 3     | Complete | IOL `_token_cache.py` + platformdirs + fcntl.flock + 0600 + caplog no-leak + failed-refresh cleanup; SEC-01 |
| 15    | 5/4   | Complete | Driver migration × 4; ONE Client per main() AST guard; probe-name stability vs LIVE-01 71bf201; REFAC-05 |
| 16    | -     | Dropped  | Codegen Single-Source — DROPPED per Phase 12 NO-GO; REFAC-06 → v1.3 |
| 17    | 3     | Complete | Final LIVE-01-equivalent gate × 4 packages; cycle closure × 4 PASS; 0-BLOCKER audit; LIVE-03 |

- v1.2 duration: 2026-06-14 → 2026-06-25 (5 phases, 18 plans, 40 tasks); shipped via PR #2
- Test suite: 907 (v1.1 close) → ≥989 (v1.2 close) on Python 3.12 + 3.13

**By Phase (v1.4 shipped 2026-07-31):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 20    | 6     | Complete | Scaffold + Auth0 client-credentials + transport foundations; AUTH-MD-01 + CORE-MD-01 |
| 21    | 4     | Complete | Market data read surface + models (`received_at` client-stamped); MD-01 |
| 22    | 2     | Complete | Reference-data read surface + 5 models; REF-MD-01 |
| 23    | 2     | Complete | Live-verification apparatus (`main_market_data.py`) + D-09 hardening; LIVE-MD-01 |
| 24    | 2     | Complete | Release prep + publish `market-data-client-v0.1.0`; PUB-MD-01 |

- v1.4 duration: 2026-07-29 → 2026-07-31 (5 phases, 16 plans, 36 tasks); package released v0.1.0 → v0.2.0

**By Phase (v1.5 planned):**

| Phase | Plans | Status      | Requirements | Notes |
|-------|-------|-------------|--------------|-------|
| 25    | ?     | Not started | GATE-MD-01 + MUT-MD-01 | Mutating-gate load-bearing (opt-in `mutating_allowed` + env gate + no-retry de no-idempotentes, `MarketDataMutationNotAllowedError`) construido PRIMERO; symbols write (`POST /symbols`, `POST /symbols/batch`, `PATCH /symbols/{id}`) es la primera superficie que lo ejercita. Dual sync/async vía `_core.py`. |
| 26    | ?     | Not started | MUT-MD-02 | Calendar write (`PUT`/`DELETE /calendar/config`, `POST /calendar/config/preview`, `POST /calendar/holidays`, `DELETE /calendar/holidays/{day}`); `confirm` guardrail default False; depende del gate de Phase 25. |
| 27    | ?     | Not started | LIVE-MUT-01 | Verificación en vivo destructiva-pero-segura contra develop (create→verify→revert, identificadores dedicados), revalida idempotencia DM-03, fixes in-cycle sync/async. Depende de 25 + 26. |
| 28    | ?     | Not started | PUB-MUT-01 | Release prep + publish `market-data-client-v0.3.0` (minor bump no-breaking). Depende de 27. |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.5 Roadmap]: Phase numbering CONTINUES from v1.4 (last phase = 24) — v1.5 starts at **Phase 25** (does NOT reset). Sequential `phase_naming` per config.json. Granularity `coarse` → 4 phases, 1:1 con requisitos salvo Phase 25 (GATE-MD-01 + MUT-MD-01 combinados: el gate es load-bearing y symbols es la primera superficie que lo ejercita end-to-end).
- [v1.5 Roadmap]: 4 fases lineales (25 gate+symbols → 26 calendar → 27 live verification → 28 publish). Phase 25 construye el mutating-gate PRIMERO (mitigación primaria del riesgo central = mutación accidental); Phases 26 y 27 dependen del gate. NO paralelizan: 25 es prerequisito estricto de 26, y 27 necesita ambas superficies (25 + 26).
- [v1.5 Roadmap]: Verificación en vivo (Phase 27) es **destructiva** a diferencia de v1.4 (solo lectura) → obligatorio cleanup + identificadores de prueba dedicados (DM-06); nunca toca config real sin `confirm`. La idempotencia por-endpoint (DM-03) se revalida en vivo antes de confiar el retry-behavior. Plan fuente: `.planning/future-plans/market_data_mutations.md`.
- [v1.4 Roadmap]: Phase numbering CONTINUES from v1.3 — v1.3 allocated Phases 18-19 (19 dropped), so v1.4 starts at **Phase 20** (avoids collision with the dropped Phase 19 reference). Sequential `phase_naming`.
- [v1.4 Scope]: Paquete `market-data-client` (import `market_data_client`) — nombre con sufijo `-client` OBLIGATORIO por el regex de `release.yml`. Solo lectura; mutaciones + streaming SSE + disk token cache + JWT signature validation diferidos a v1.5+ (REQUIREMENTS § v2). Auth = Auth0 client_credentials. Plan fuente: `.future_plans/market_data.md`.
- [v1.4 Roadmap]: 5 fases lineales (20 scaffold+auth → 21 market data → 22 reference data → 23 live verification → 24 publish); Phases 21 y 22 pueden paralelizar (ambas dependen solo de 20). 6 requisitos, 1:1 con fases salvo Phase 20 (AUTH-MD-01 + CORE-MD-01).

<details>
<summary>v1.3 decisions (milestone closed 2026-07-03, archived for reference)</summary>

- [v1.3 Roadmap]: Phase numbering CONTINUES from v1.2 (last phase = 17) — v1.3 starts at Phase 18 (does NOT reset). Sequential `phase_naming` per config.json.
- [v1.3 Roadmap]: Spike-gated conditional structure mirrors v1.2 (Phase 12 spike + conditional Phase 16). Phase 18 (SPIKE-006) is spike-before-plan and the guaranteed deliverable; Phase 19 (REFAC-06) is CONDITIONAL — DROPPED entirely if Phase 18 returns NO-GO, in which case REFAC-06 is shelved permanently per D-NOGO-01 and the milestone closes on the signed NO-GO.
- [v1.3 Roadmap]: The 3 GO-determining gate items are D-RIGOR-02 item 1 (byte-identical round-trip, no source migration), item 4 (ruff check clean incl. single-line import-order), item 6 (mocked suite green vs generated, no circular self-import) — all trace to the single unasync root cause (source-shape asymmetry). libcst must close all 3 for GO.
- [v1.3 Roadmap]: No standalone milestone-close / live re-verification phase. Per the in-cycle verification convention, byte-identical generated output means wire behavior is unchanged by construction; the D-RIGOR-02 item-1 + item-6 gates fold verification into Phase 19. Milestone kept tight (REFAC-06-only) — other v1.3 candidates (prod-vs-remarkets, ws_client live, token encryption) stay in backlog.
- [v1.3 Roadmap]: Matriz deny-list (`_token_store.py`/`_refresh_policy.py`/`_refresh.py`/`ws_client.py`) is OUT of codegen scope in BOTH phases — the spike CONFIRMS (sha256-byte-identical under MetadataWrapper), it does NOT renegotiate. Codegen applies ONLY to `client.py`/`aio.py` transport shells.
- [Phase 18]: SPIKE-006 001a: libcst closes mechanical asymmetries (items 4/5/7/9 PASS) but items 1/6 FAIL on content-absence (_validate_max_retries def + dotenv bootstrap absent from aio.py) — same SPIKE-005 root cause; aggregate NO-GO
- [Phase 18]: Item-9 purity scoped to transformer CLASSES; impure driver owns cross-module/scope orchestration (flagged for operator ratification in Plan 03 DECISION.md)
- [Phase 18 / 18-03]: SPIKE-006 **signed NO-GO** (sebadlf, 2026-07-03) — 7 PASS / 3 FAIL (items 1/3/6) → strict D-04 NO-GO. libcst is a partial gain over unasync (closes item 4 `ruff check` / ASYNC1xx) but cannot cross the content-absence boundary without a forbidden source migration (D-02). Two independent tools now reach the same NO-GO for the same root cause.
- [Phase 18 / 18-03]: **REFAC-06 PERMANENTLY shelved; Phase 19 DROPPED**; duplicate `client.py`/`aio.py` transport shells accepted as a structural feature. v1.3 milestone closes on the signed NO-GO (run `/gsd-complete-milestone`).

</details>

- [Phase 21-02]: drop_none copiado verbatim en un _params.py nuevo (sin import cross-package); format_date/format_bool omitidos (bool wire-encoding diferido a Phase 23, D-07).
- [Phase 21-02]: parse_latest_response retorna list[MarketDataSnapshot] (provisional) — el batch POST retorna varios simbolos; la forma single-snapshot del GET se reconcilia en Phase 23 via from_api tolerance.
- [Phase ?]: [Phase 21-03]: with_options threads req.extensions['max_attempts']=_max_retries+1 in BOTH _request and _send_auth_request (D-08 load-bearing); mirrors iol, _validate_max_retries copied verbatim (no cross-package import).
- [Phase ?]: [Phase 21-03]: sync read methods + module shims added in client.py only (__init__ re-export deferred to respect files_modified scope); retry count asserted by outgoing-request count, 401 re-auth by token-POST count.
- [Phase 21]: Async with_options mirrors sync as a shared-view clone; per-call max_attempts threaded via req.extensions in both _request and _send_auth_request (load-bearing).
- [Phase 21]: D-09: authenticated async header build spreads spec.headers first and Authorization token last so the fresh token always wins over a decoy spec header.
- [Phase ?]: Phase 22-01: reference SafeModels carry no received_at (D-05); calendar/config is the single non-collection parser with empty-body from_api(None) fallback (D-07)
- [Phase 22]: 22-02: 5 sync + 5 async reference methods dispatch through Plan 01 _core builders/parsers; get_calendar_config returns a single CalendarConfig (D-07), the other four return list[Model]
- [Phase ?]: [Phase 24-01]: Committed the pre-staged uv.lock market-data-client workspace-member registration (D-03/D-11), validated via uv sync --frozen + uv lock --check (both exit 0), not regenerated.
- [Phase ?]: [Phase 24-01]: Left global mypy files, importlinter root_packages, and CI typecheck per-package loop untouched (scope_decisions deferrals) — coverage gaps not CI failures; new package pytest+coverage runs via the matrix edit so CI stays green.
- [Phase ?]: [Phase 24-02]: Merged PR #5 with a true merge commit (gh pr merge --merge) so tag market-data-client-v0.1.0 sits on the distinct merge commit 1ea655d (D-10); release.yml unedited (D-02) matched the tag and published the GitHub Release with wheel + sdist (PUB-MD-01).

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

- spike-codegen-libcst-v1.3.md — the fully-scoped SPIKE-006 spec + D-RIGOR-02 10-item gate; consumed by Phase 18 planning (v1.3 closed).

### Blockers/Concerns

[Issues that affect future work]

- [v1.5 / Phase 27 risk]: La verificación en vivo es **destructiva** (crea/modifica estado en develop) — a diferencia de v1.4 (solo lectura). Requiere identificadores de prueba dedicados + cleanup obligatorio (crear→verificar→revertir, DM-06) y **confirmación del operator sobre qué es seguro tocar en develop** antes de Phase 27. El mutating-gate impide prod. Depende también de creds Auth0 + acceso a develop (mismo standing blocker que v1.4 Phase 23, ya resuelto post-close con creds provistas por el operator).
- [v1.5 / Phase 27 risk]: La **idempotencia real** de los POST de symbols la declara el spec, pero un POST no idempotente reintentado duplicaría estado → se revalida en vivo (DM-03) antes de confiar el retry-behavior. `POST /calendar/holidays` se asume `idempotent=False` (no retry) salvo confirmación live.
- [v1.5 / Phase 26 note]: `PUT /calendar/config` tiene un guardrail `confirm` server-side → el cliente lo expone explícitamente con default `False`; nunca se persiste config real sin `confirm` explícito.

### Quick Tasks Completed

| # | Description | Date | Commits | Directory |
|---|-------------|------|---------|-----------|
| 260611-u0v | Fix CI failures on phase-06-compat-safety-net (snapshot trailing whitespace + iol tests mypy strict + v1.0 archive whitespace) | 2026-06-11 | bc16e26, 2be4e90, 9360cf5 | [260611-u0v-fix-ci-failures-on-phase-06-compat-safet](./quick/260611-u0v-fix-ci-failures-on-phase-06-compat-safet/) |
| 260613-nwb | Fix INT-01: replace denied `_base_url` with `_get_default()._state.base_url` in main_iol.py (15 probes) — closes INT-01, unblocks LIVE-01 (Phase 11) | 2026-06-13 | 3de1940 | [260613-nwb-fix-int-01-main-iol-py-crashea-con-attri](./quick/260613-nwb-fix-int-01-main-iol-py-crashea-con-attri/) |
| 260614-de5 | Fix DOC-01..04 before completing milestone v1.1 — backfill 4 SUMMARY frontmatters + flip REQUIREMENTS.md traceability table 18 rows Open→Complete + emit Phase 10/11 VERIFICATION shims + remove ORP-01 dead `account_id` field from matriz `_state.py` | 2026-06-14 | 9d01d7f, cd946a3 | [260614-de5-fix-doc-01-04-before-completing-mileston](./quick/260614-de5-fix-doc-01-04-before-completing-mileston/) |
| 260614-r1x | Fix v1.1 CI mypy + pre-commit tech debt (mypy-precommit-v1.1-techdebt) — Bucket A: 4 unused `# type: ignore` dropped + `_raise_for_response` added to `aio.__all__`; Bucket B+C: bump `ruff-pre-commit` v0.7.4→v0.15.12; Bucket D: add `tenacity>=9.1.0,<10` to pre-commit mypy `additional_dependencies` | 2026-06-14 | e5ad1c1, 73cb578, c7bf9e9, 2b8ec4a | [260614-r1x-fix-v1-1-ci-mypy-pre-commit-tech-debt-cl](./quick/260614-r1x-fix-v1-1-ci-mypy-pre-commit-tech-debt-cl/) |
| 260731-j93 | Make `symbol` a required kwarg in market-data-client `get_latest` (5 sites: client.py method+shim, aio.py method+shim, `_core.build_latest_request`) + probe updates + sync/async/builder regression tests — closes v1.4 Phase-23 live findings F-01/F-13 (`GET /marketdata/latest` returns 422 without `symbol`; OpenAPI `required=True`). Verified live: driver re-run PASS=19 FINDING=0; 137 pkg tests green | 2026-07-31 | d062761, 36aa94b, 68092d7 | [260731-j93-make-symbol-a-required-kwarg-in-market-d](./quick/260731-j93-make-symbol-a-required-kwarg-in-market-d/) |
| 260731-jim | Reconcile `MarketDataSnapshot` + `CalendarConfig` SafeModels against the real develop wire (LIVE-MD-01 schema snapshots): `marketId`→`market_id`, add `active`/`market_data`/`staleness_seconds`/`note`; drop invented `businessDays`+`MarketDataEntry`, add full `/calendar/config` field set; **fix `parse_market_data_response` envelope-unwrap bug** (iterated envelope keys instead of `items[]`). Closes the 36 live SHAPE findings. Verified live: `market_data snapshots=5→12`, SHAPE divergences gone (only 2 benign NO-DATA remain); 139 pkg tests green | 2026-07-31 | 0852d43, 45c1885, 8c8e494 | [260731-jim-reconcile-market-data-client-marketdatas](./quick/260731-jim-reconcile-market-data-client-marketdatas/) |
| 260731-l4s | Bump `market-data-client` to **v0.2.0** (release prep): version in pyproject + `__version__`, CLAUDE.md workspace bullet, README changelog (breaking changes), `uv.lock` refresh. Minor bump because the post-v0.1.0 LIVE-MD-01 fixes (`get_latest.symbol` required, model reconciliation, envelope-unwrap) broke the public API. On `release/v0.2.0` → PR → tag `market-data-client-v0.2.0`. 139 pkg tests green | 2026-07-31 | 73dda1c | [260731-l4s-bump-market-data-client-to-v0-2-0-releas](./quick/260731-l4s-bump-market-data-client-to-v0-2-0-releas/) |

## Deferred Items

Items acknowledged and carried forward from v1.0 milestone close on 2026-06-10:

| Category | Item | Status | Resolution in v1.1 |
|----------|------|--------|---------------------|
| todo | matriz-driver-findings-file-handling | low priority — driver dedupe + append-only bugs | Resolved in Phase 11 (HARN-07/08/10) |
| uat_gap | 03-HUMAN-UAT.md | partial — legacy HUMAN-UAT from Phase 3 close | N/A — archived under v1.0 |
| uat_gap | 05-HUMAN-UAT.md | partial — 2 ítems satisfied via operator re-run 2026-06-10T15Z | N/A — archived under v1.0 |
| verification_gap | 03-VERIFICATION.md | human_needed — operator-driven validation | N/A — archived under v1.0 |
| verification_gap | 05-VERIFICATION.md | human_needed — operator-driven validation satisfied via re-run | N/A — archived under v1.0 |
| deferred_bug | F-09 matriz ERROR-MAP | DEFERRED in v1.0 Phase 5 | Resolved in Phase 9 (BUG-01) |
| deferred_bug | F-02 higyrus get_listado_cuentas=0 | DEFERRED in v1.0 Phase 4 | Resolved in Phase 9 (BUG-02) |
| deferred_cap | IOL refresh_token persistence | DEFERRED in v1.0 Phase 3 | Resolved in Phase 9 (BUG-03, in-instance only; disk persistence Phase 14 SEC-01) |
| deferred_cap | HIGY multi-account iteration | DEFERRED in v1.0 Phase 4 | Resolved in Phase 9 (BUG-04) |

See `.planning/milestones/v1.0-MILESTONE-AUDIT.md` for the full v1.0 audit context.

### Acknowledged at v1.2 close on 2026-06-25

Items surfaced by `gsd-sdk query audit-open` (6 total) and acknowledged by operator at v1.2 milestone close ("Acknowledge & proceed"). All are intentional deferrals or stale history — none are real blockers:

| Category | Item | Status | Carry-forward |
|----------|------|--------|---------------|
| quick_task | 260611-u0v / 260613-nwb / 260614-de5 / 260614-r1x | SDK reports "missing" — v1.1-era tasks, work landed in git history | False-positive (SDK parser heuristic) — no action |
| todo | spike-codegen-libcst-v1.3.md | pending (high) → **now active** | Became the v1.3 codegen spike (Phase 18 SPIKE-006) per Phase 12 NO-GO (D-NOGO-01) |
| uat_gap | 15-HUMAN-UAT.md | partial — 4 operator-driven live scenarios | Superseded by Phase 17 LIVE-03 final gate (dispositions × 4 in 17-VALIDATION.md) |

See `.planning/milestones/v1.2-ROADMAP.md` and the MILESTONES.md v1.2 entry for full close context.

### Acknowledged at v1.4 close on 2026-07-31

Items acknowledged and deferred by operator at v1.4 milestone close ("Proceed with close"). None are real blockers:

| Category | Item | Status | Carry-forward |
|----------|------|--------|---------------|
| uat_gap | 20-UAT.md | passed — 0 pending scenarios | False-positive (open-artifact audit parser heuristic flags file presence) — no action |
| verification_gap | LIVE-MD-01 real credentialed sweep | **RESOLVED post-close 2026-07-31** — operator supplied Auth0 creds; real sweep ran vs develop (PASS=17, snapshots=12), found+fixed 3 real divergences in-cycle (quick tasks 260731-j93 + 260731-jim), final re-run 0 real divergences | No longer deferred — LIVE-MD-01 satisfied with real live evidence; fixes on `release/v0.2.0-bump` (post-`v1.4`-tag) |
| deferred_cap | MUT-MD-01/02, STREAM-MD-01, SEC-MD-01/02 | v2 requirements (market-data-client) | MUT-MD-01/02 **now active in v1.5** (Phases 25-26); STREAM-MD-01 + SEC-MD-01/02 remain v1.6+ (see ROADMAP Backlog) |

See `.planning/milestones/v1.4-ROADMAP.md` and the MILESTONES.md v1.4 entry for full close context.

## Session Continuity

Last session: 2026-07-31T19:22:56.326Z
Stopped at: v1.5 roadmap created (Phases 25-28)
Resume file: .planning/ROADMAP.md (Phase Details v1.5)

## Operator Next Steps

- Plan the first phase with `/gsd-plan-phase 25` (Mutating-gate + Symbols write)
