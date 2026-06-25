---
phase: 17-final-live-re-verification-4-live-03
slug: final-live-re-verification-4-live-03
status: approved
nyquist_compliant: true
phase_status: ready_for_close
requirements_closed:
  - REFAC-05
  - SEC-01
  - ERG-01
  - LIVE-03
operator_dispositions:
  ambito: no_new_findings
  iol: no_new_findings (RAN en vivo; F-01 pre-existente OPEN/SHAPE re-confirmado, D-05; sin fid nuevo)
  higyrus: SKIPPED-EXPECTED (login host no resoluble por DNS desde el entorno; excepción documentada, D-02)
  matriz: SKIPPED-EXPECTED (abort de seguridad — URL no-remarkets; fuera de alcance del ciclo, remarkets-only, D-02)
baseline_commit: verification-cycle-2026-Q2
head_commit: 71bf201
head_commit_at_pre_fill: 83ea7c5
created: 2026-06-24
updated: 2026-06-25
operator_signoff_date: 2026-06-25
operator_signoff_by: sebadlf (Sebastián de la Fuente)
operator_signoff_run_logs:
  - /tmp/phase17-live-ambito.log
  - /tmp/phase17-live-iol.log
  - /tmp/phase17-live-higyrus.log
  - /tmp/phase17-live-matriz.log
  - /tmp/phase17-verify-aggregate.log
---

# Phase 17 — LIVE-03 Final Live Re-verification Closure (Operator-Approved)

> **STATUS: APPROVED by operator (sebadlf, 2026-06-25).**
> The operator provisioned per-package `.env` credentials and the gate ran the 4 verifiable
> drivers live + the `main_verify.py` aggregate cross-check.
>
> **ámbito RAN** (no auth) and **iol RAN** (operator creds) — both clean, ZERO new findings.
> **higyrus** and **matriz** could not complete live verification due to `.env` target
> configuration (higyrus base URL unresolvable from this environment; matriz base URL not a
> remarkets sandbox). Both are dispositioned as **documented EXPECTED exceptions (D-02)** that do
> NOT block the gate or the milestone — matriz non-remarkets is explicitly out-of-cycle-scope.
>
> **ZERO new findings across all 4 packages** (every findings-file AUTO-GENERATED zone is
> byte-stable; only run-context timestamps changed). `verify_cycle_closure × 4` = PASS. The D-07
> new-finding branch was **not triggered**. iol F-01 re-confirmed **OPEN** as a documented baseline
> carry-forward (D-05); no terminal finding was re-opened.

---

## LIVE-03 Evidence

**Baseline:** cycle `verification-cycle-2026-Q2` + v1.1 LIVE-01 head `71bf201`
**Head at pre-fill:** `83ea7c5` (post Phase 14 SEC-01 + Phase 15 REFAC-05 migrations; Phase 16 codegen DROPPED per SPIKE-005 NO-GO)

**Run commands (per-package serial idiom — ámbito → iol → higyrus → matriz; logs under /tmp, payloads never echoed):**

- `uv run --package ambito-financiero-client python main_ambito_financiero.py > /tmp/phase17-live-ambito.log 2>&1`
- `uv run --package iol-client python main_iol.py > /tmp/phase17-live-iol.log 2>&1`
- `uv run --package higyrus-client python main_higyrus.py > /tmp/phase17-live-higyrus.log 2>&1`
- `uv run --package matriz-client python main_matriz.py > /tmp/phase17-live-matriz.log 2>&1`
- `uv run python main_verify.py > /tmp/phase17-verify-aggregate.log 2>&1` (aggregate RAN/SKIPPED/FAILED cross-check; redaction preserved)

**Acceptance bar (operator-gated per D-01; RAN/SKIPPED column per D-02):**

| Package | Pre-baseline status | RAN/SKIPPED | Post-run SUMMARY (redacted) | NEW FIDs vs baseline | Operator disposition |
|---|---|---|---|---|---|
| ámbito-financiero-client | PASS (F-01 EXPECTED) | **RAN** | `PASS=6 FAIL=0 SKIPPED=1 FINDING=0` (schema_snapshot PASS — sin drift) | (none) | `no_new_findings` |
| iol-client | PASS (F-01 OPEN — pre-existing SHAPE; F-02 FIXED) | **RAN** | `PASS=13 FAIL=0 SKIPPED=1 FINDING=1` (`field_type_map: FINDING F-01 (OPEN)` — pre-existing) | (none) | `no_new_findings`; F-01 re-confirmed OPEN (D-05) |
| higyrus-client | PASS (F-01 EXPECTED + F-02 NO-FIX — Phase 9) | **SKIPPED** (auth no completó) | `PASS=0 FAIL=0 SKIPPED=17 FINDING=2` — login `ConnectError` (host no resoluble por DNS); F-01/F-02 re-emitidos = terminales pre-existentes (dedupe-preservados) | (none) | **SKIPPED-EXPECTED (D-02)** — host inalcanzable desde el entorno |
| matriz-client | F-01..F-10 (mix EXPECTED/NO-FIX/FIXED; D-MATZ-27 prod-vs-remarkets EXPECTED) | **SKIPPED** (abort de seguridad) | `ABORT: base URL no-remarkets — verificación remarkets-only por política de seguridad` | (none) | **SKIPPED-EXPECTED (D-02)** — fuera de alcance (remarkets-only) |

**Aggregate cross-check (`main_verify.py`, redacted classification only):**

```
RAN: 3  SKIPPED: 1  FAILED: 1  (total: 5)
RAN      ambito-financiero-client / iol-client / higyrus-client
FAILED   matriz-client          (safety ABORT: base URL no-remarkets — dispositioned SKIPPED-EXPECTED/out-of-scope, D-02)
SKIPPED  wallets-client          (out-of-cycle scope: stub)
```

> **Nota sobre matriz `FAILED` en el runner:** `main_verify.py` clasifica el exit≠0 como `FAILED`,
> pero el exit proviene del **guard de seguridad remarkets-only** (el driver aborta antes de cualquier
> llamada cuando la URL no es un sandbox remarkets). Es una negativa pre-flight a un objetivo
> fuera-de-alcance, NO un fallo de verificación: `verify_cycle_closure("matriz-client")` = `(True, [])`
> y no se mutó ningún finding. Disposición del operador: **SKIPPED-EXPECTED / out-of-scope (D-02)**.

**Per-package log artifacts (paths only — no raw payloads, account numbers, balances, or credentials):**

- `/tmp/phase17-live-ambito.log` (352 bytes — RAN, FINDING=0)
- `/tmp/phase17-live-iol.log` (986 bytes — RAN, FINDING=1 = pre-existing F-01)
- `/tmp/phase17-live-higyrus.log` (2519 bytes — login DNS-unreachable, 17 probes SKIPPED)
- `/tmp/phase17-live-matriz.log` (151 bytes — remarkets-only safety ABORT)
- `/tmp/phase17-verify-aggregate.log` (243 bytes — RAN/SKIPPED/FAILED classification)

**Blocking regressions (NO operator gate — block close if non-zero; results from Plan 17-01 deterministic attestation + this run):**

| Gate | Source | Test / Detection | Result |
|---|---|---|---|
| (a) Wire URL changes sync vs async | 17-01 attestation | `verification/test_sync_async_isolation.py` | **GREEN** (9 passed) |
| (b) Probe outcome flips PASS→FAIL (pre-baseline FIDs) | this run | ámbito/iol `FINDING` = pre-existing only; no findings-file AUTO zone mutated; no new fid | **ZERO** flips |
| (c) Credential leak in logs/docs | 17-01 attestation + this run | `verification/test_logging_no_token_leak.py` + grep over 17-VALIDATION.md | **GREEN** (5 passed; grep clean) |
| (d) Finding-title stability vs `71bf201` (D-06 static) | 17-01 attestation | `git diff 71bf201..HEAD` over `title=`/`fid=`/`class_=` literals in the 4 drivers | **ZERO** changed literals (drivers +584/-344) |

---

## Cycle-Closure Status

- `verify_cycle_closure × 4` = **PASS** (`ambito/iol/higyrus/matriz` all return `(True, [])`) — re-confirmed post-live.
- iol `verify_cycle_closure` was greened in Plan 17-01 by linking F-02 (FIXED) to its resolvable in-tree regression `packages/iol-client/tests/test_refresh_token_lifecycle.py::test_refresh_token_success_path_rotates` (additive provenance below the AUTO-GENERATED zone; F-02 status unchanged; D-05 / HARN-09).
- iol F-01 re-confirmed **OPEN** (documented baseline carry-forward, D-05) — non-gating; root-cause deferred (17-CONTEXT Deferred Ideas). iol RAN live (creds provisioned); F-01 re-emitted, no new fid.
- higyrus / matriz F-01..F-NN terminal statuses **preserved** across the live run (append-only + content-addressed dedupe; SC#3). No terminal finding re-opened.
- D-07 new-finding branch **not triggered** — no genuinely-new finding surfaced in any package; no new test/finding files created.
- pytest collection: **989/990** (1 deselected) — meets the Phase 15 ≥ 989 floor (SC#5).

---

## Success Criteria Status

| SC | Criterion | Status |
|---|---|---|
| #1 | Operator dispositions captured for all 4 packages (RAN or SKIPPED-EXPECTED) | ✅ ámbito + iol RAN `no_new_findings`; higyrus + matriz SKIPPED-EXPECTED (D-02) |
| #2 | Schema-drift clean + `verify_cycle_closure × 4` PASS + markers updated | ✅ ámbito schema no-drift; cycle-closure ×4 PASS; D-06 ZERO changed literals |
| #3 | v1.1 LIVE-01 dispositions preserved across migration (append-only + dedupe) | ✅ AUTO-GENERATED zones byte-stable; no terminal finding re-opened |
| #4 | Milestone audit passed + REQUIREMENTS.md traceability flipped | ⏳ Plan 17-03 (next wave) |
| #5 | pytest ≥ Phase 15 baseline (989) + CI green 3.12/3.13 | ⏳ pytest 989/990 here; full CI matrix in Plan 17-03 |

---

## Operator Approval (Granted 2026-06-25)

**Operator:** sebadlf (Sebastián de la Fuente)
**Date:** 2026-06-25
**Decision:** Provisioned credentials and ran the full 4-package live gate. Accepted **higyrus** and
**matriz** as **SKIPPED-EXPECTED (D-02)** — higyrus base URL unresolvable from this environment;
matriz base URL not a remarkets sandbox (out-of-cycle scope, remarkets-only safety policy). **ámbito**
and **iol** verified live and clean with zero new findings.

**LIVE-03 acceptance bar PASSED:**
- Dispositions captured for all 4 packages (SC#1): ámbito `no_new_findings` ✅, iol `no_new_findings`
  (F-01 pre-existing OPEN re-confirmed live, D-05) ✅, higyrus SKIPPED-EXPECTED (D-02) ✅,
  matriz SKIPPED-EXPECTED / out-of-scope (D-02) ✅.
- Zero new findings; `verify_cycle_closure × 4` PASS; D-06 title-stability ZERO changed literals.
- v1.1 LIVE-01 dispositions preserved across the Phase 15 migration (append-only + dedupe; SC#3).

**Phase 17 ready for milestone-closure landing (Plan 17-03): REQUIREMENTS.md traceability flip +
0-BLOCKER integration audit + full CI matrix. Stops short of the PR/merge ship (D-04).**

---

## Evidence Index

| Item | Path |
|---|---|
| Plan | `.planning/phases/17-final-live-re-verification-4-live-03/17-02-PLAN.md` |
| Plan 17-01 SUMMARY (deterministic gate attestation) | `.planning/phases/17-final-live-re-verification-4-live-03/17-01-SUMMARY.md` |
| Live run logs (ámbito + iol RAN; higyrus DNS-skip; matriz remarkets-abort) | `/tmp/phase17-live-{ambito,iol,higyrus,matriz}.log` |
| Aggregate RAN/SKIPPED/FAILED cross-check | `/tmp/phase17-verify-aggregate.log` |

---

*Operator-approved 2026-06-25 (Plan 17-02, operator-driven gate D-01). Plan 17-03 lands milestone
closure, stopping short of ship (D-04).*
