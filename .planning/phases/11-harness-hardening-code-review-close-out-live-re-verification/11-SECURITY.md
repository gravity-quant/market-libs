---
phase: 11-harness-hardening-code-review-close-out-live-re-verification
type: security-audit
asvs_level: 1
block_on: high
status: SECURED
threats_total: 21
threats_closed: 21
threats_open: 0
threats_npm_pip_na: 3
unregistered_flags: 0
audited_on: 2026-06-14
auditor: gsd-security-auditor
---

# Phase 11 — Security Audit (harness hardening + code review close-out + live re-verification)

Verifica que cada mitigación de amenaza declarada en los 3 sub-planes
(11-01, 11-02, 11-03) está presente en el código implementado. La
auditoría es read-only contra el árbol de implementación; este
`11-SECURITY.md` es el único artefacto producido por el auditor.

Cada threat ID se ubica por su disposición (`mitigate` / `accept`) y se
verifica por grep / inspección en el archivo declarado en su plan de
mitigación. `register_authored_at_plan_time: true` — el auditor verifica
mitigaciones existentes, no busca nuevas amenazas.

## Audit Scope

| Plan  | Wave | Subject                                                                            | Threats audited     |
|-------|------|------------------------------------------------------------------------------------|---------------------|
| 11-01 | 1    | `verification/findings.py` append-only + idempotent_by_title (HARN-07/08/09/10)    | T-11-01..06 + T-11-SC |
| 11-02 | 1    | Code review close-out (CR-01/02/04/06/07/08)                                       | T-11-07..12 + T-11-SC |
| 11-03 | 2    | LIVE-01 acceptance bar + operator checkpoint                                       | T-11-13..18 + T-11-SC |

Total: **21 threats** (18 plan-specific + 3 × T-11-SC supply-chain identical reuse).
Dispositions: **mitigate=16**, **accept=3**, **n/a=3** (T-11-SC × 3 — no new
dependencies; `uv.lock` unchanged across all 3 plans; pyproject.toml diff
limited to `[tool.ruff] extend-exclude` housekeeping per CR-08).

## Threat Verification (mitigate)

| Threat ID | Category               | Disposition | Evidence (file:line)                                                                                                                                                                                                                                                                                                                                                                                                       | Result |
|-----------|------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| T-11-01   | Tampering              | mitigate    | `verification/findings.py` BEGIN/END state machine: `grep -c "BEGIN AUTO-GENERATED" verification/findings.py` = 5 (constant in `new_findings`, parse matcher, serialize emitter, doc, tests); `grep -c "END AUTO-GENERATED"` = 5. `_ParsedFile.operator_prefix / operator_suffix` campos presentes (15 ocurrencias). 4 baseline files migrados (1 marker pair cada uno). Test `verification/test_findings_append_only.py::test_markers_present_in_freshly_written_file` GREEN. Back-compat: parser default `in_auto_zone=True` para files sin markers. | CLOSED |
| T-11-02   | Tampering              | mitigate    | `verification/test_findings_append_only.py::test_operator_bullets_inside_findings_survive` GREEN (N=3 re-runs); preservation guard pre-existente en `findings.py:473` (`existing[fid].status != "OPEN"`) intacto. Evidence operacional in vivo: `.planning/verification/iol-client-findings.md:37-50` — F-02 operator bullets (`**Classification:** PROBE_STALE`, `**Rationale:**`, `**Resolution:**`, `**Regression:**`, `**Operator signoff:** sebadlf, 2026-06-14`) sobreviven byte-identical post live re-run. ASVS L1 V5.                | CLOSED |
| T-11-03   | Tampering              | mitigate    | `verification/findings.py:573-574` invariant preservado: `if "\n" in title or "\r" in title: raise ValueError(...)`. Comparación `existing_finding.title == title` opera sobre strings de una sola línea validados. `idempotent_by_title=True` lookup honra el invariante (no inyección de salto de línea posible).                                                                                                       | CLOSED |
| T-11-06   | Tampering              | mitigate    | 4 baseline files migrados con `Edit` (no `Write`); `git diff --stat HEAD~3 HEAD~1 -- .planning/verification/` reporta 4 files changed, 8 insertions(+) (solo BEGIN + END markers, cero deletions) per 11-01-SUMMARY.md. Round-trip parse confirmado: `operator_prefix` lines ≥ 10 + `findings_count` ≥ 1 por archivo (tabla en 11-01-SUMMARY.md:101-107).                                                                  | CLOSED |
| T-11-07   | Tampering              | mitigate    | `main_higyrus.py:217` `_event_hooks_lock_sync = threading.Lock()` + `:221-226` `_get_event_hooks_lock_async()` lazy `asyncio.Lock`; `:308` `with _event_hooks_lock_sync:` rodea read-modify-write de `client.event_hooks` en `_capture_sync_query_string`; `:363` `async with _get_event_hooks_lock_async():` espejo async. Test `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` (3 tests GREEN — concurrent sync + concurrent async + single-thread sanity). ASVS L1 V7.                                                       | CLOSED |
| T-11-08   | Repudiation            | mitigate    | AST walk `python -c "import ast; ..."` reporta `matriz_bare_count=0` + `higyrus_bare_count=0`. Test `verification/test_main_drivers_bare_except.py` parametric × 2 drivers GREEN. Idiom `class_="ERROR-MAP"` preservado: `grep -c 'class_="ERROR-MAP"' main_matriz.py` = 34, `... main_higyrus.py` = 28. `type(exc).__name__` propagado en `title` field — diagnostic trail type-accurate. ASVS L1 V7.                | CLOSED |
| T-11-09   | Information Disclosure | mitigate    | `main_matriz.py:205` `def _first_dict(payload: Any, *, fname: str | None = None) -> dict[str, Any] | None:` con 3-branch distinguishability (ok/no_data/wrong_type); wrong_type emite SHAPE finding via `append_finding`. Test `verification/test_main_matriz_first_dict.py` (5 tests GREEN — ok, no_data, wrong_type element, wrong_type non-list, backwards-compat fname=None silent). ASVS L1 V5.       | CLOSED |
| T-11-10   | Tampering              | mitigate    | `main_matriz.py:1392-1416` `sample_params` placeholder-everywhere (`{symbol}`, `{segment_id}`, `{account_id}`, `{cl_ord_id}`, `{proprietary}`, `{exec_id}`, `ESXXXX`) consistentes con `_ENDPOINT_TEMPLATES` path style. Comentario inline `:1378-1391` documenta CR-01 Option B (envelope NUNCA leak PII; el envelope documenta SHAPE, no valor). Test `verification/test_main_matriz_schema_snapshot_alignment.py` (3 tests GREEN). ASVS L1 V5. | CLOSED |
| T-11-11   | Information Disclosure | mitigate    | `main_matriz.py:484` `return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN): AuthenticationError")` + `:503` `return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN): {type(exc).__name__}")` — ambos sites `FAIL` flipped a `FINDING`. `grep -c 'ProbeResult("login_sync", "FAIL"' main_matriz.py` = 0. Test `verification/test_main_matriz_login_fail_uniformity.py` (2 tests GREEN). ASVS L1 V7. | CLOSED |
| T-11-12   | Tampering              | mitigate    | `pyproject.toml:46-49` `extend-exclude = [".claude/skills/spike-findings-market-libs/sources/**", ".planning/spikes/**"]` — scope estrecho. Comentario inline `:42-45` documenta CR-08 rationale. `packages/*/src/`, `verification/`, `main_*.py` NO excluidos; ruff sigue enforcing style allí (verificado por `uv run ruff check .` exit 0 incluyendo todos los main_*.py + drivers).                                | CLOSED |
| T-11-13   | Information Disclosure | mitigate    | `packages/matriz-client/src/matriz_client/_logging.py:123` `RedactingFilter` class definida; Phase 8 LOG-02 invariant INTACT. Test `verification/test_logging_no_token_leak.py` GREEN (5 passed) per 11-VALIDATION.md:173. Grep auto-detection en `/tmp/phase11-live-*.log` (11 files): patrones `Bearer [A-Za-z0-9._-]{20,}`, `X-Auth-Token: ...`, `password=...`, `refresh_token=...` returnan 0 ocurrencias en todos los logs. `/tmp/phase11-live-blockers.log` empty (0 bytes). ASVS L1 V7. | CLOSED |
| T-11-14   | Tampering              | mitigate    | Plan 11-01 regression test `verification/test_findings_append_only.py` (4 tests GREEN) enforces operator content preservation. Preflight `/tmp/phase11-preflight.log` confirmó 4 BEGIN/END markers pre-run. Task 2 driver runs usaron HARN-07-compliant `append_finding`. 4 findings.md post-live-runs preservan markers + operator content (evidence: iol F-02 operator bullets at lines 37-50 preserved through Task 4 closure commit).                                                            | CLOSED |
| T-11-16   | Tampering              | mitigate    | `verification/test_sync_async_isolation.py:45` parametric incluye `("matriz_client", "X-Auth-Token", "")` — cross-leak sentinel extension Phase 10. Test GREEN: 9 passed per 11-VALIDATION.md:171. Live paridad sync↔async PASS (matriz: 19 paired, divergences=0) per 11-03-SUMMARY.md:90. ASVS L1 V3.5.2.                                                                                                              | CLOSED |
| T-11-18   | Spoofing               | mitigate    | Task 1 preflight (`/tmp/phase11-preflight.log`) verificó `.env` presence × 3 paquetes auth-gated; `.env` files git-ignored (verified: `git check-ignore packages/iol-client/.env packages/higyrus-client/.env packages/matriz-client/.env` reporta los 3 paths). Operator dispositions captured in 11-VALIDATION.md frontmatter distinguen credentials-wrong de API-behavior-changed (iol F-02 dispositioned as PROBE_STALE, not credential failure).                                              | CLOSED |
| T-11-15   | Repudiation (trip-wire)| accept (with fire-and-mitigation evidence) | T-11-15 trip-wire SI disparó por diseño: live re-run reveló iol F-02 (`_token_expires_at no se renovó`). Operator analysis (11-VALIDATION.md:222-260) confirmó PROBE_STALE (NOT client bug) — `main_iol.py:1289` escribía `iol_client.client._token_expires_at = 0.0` creando atributo módulo que SHADOWED PEP 562 `__getattr__`. Inline fix aplicado (INT-01 idiom, `main_iol.py:1289-1294`): `iol_client.client._get_default()._state.token_expires_at = 0.0`. Re-run PASS. Operator signoff: sebadlf, 2026-06-14. Single-operator solo developer per CLAUDE.md — frontmatter edit + git commit son el approval signal (no multi-party trust). | CLOSED |

## Accepted Risks (verbatim from threat register)

These items were declared `accept` at plan time and are recorded here
without re-audit, per the dispositions in `<threat_model>` blocks of
plans 11-01..03.

| Threat ID | Category               | Plan  | Acceptance Rationale (verbatim from PLAN.md)                                                                                                                                                                                                                                                                                                                                       |
|-----------|------------------------|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| T-11-04   | Information Disclosure | 11-01 | Existing Phase 8 RedactingFilter discipline (LOG-02) cubre logged content; findings files son operator-curated y contienen solo structured fields. No new exposure surface en Phase 11.                                                                                                                                                                                            |
| T-11-05   | Denial of Service      | 11-01 | `idempotent_by_title` lookup es O(N) en existing findings list; N ≤ 100 per package en práctica (Phase 5 baseline tiene < 20 findings per pkg). No throughput issue.                                                                                                                                                                                                              |
| T-11-17   | Denial of Service      | 11-03 | Phase 8 tenacity retries (RELY-01..04) manejan transient rate limits; permanent downtime = checkpoint hold + operator re-runs at next market open per CLAUDE.md constraint ("resultados pueden variar por horario de mercado"). Verificable: live runs Task 2 completaron sin timeout (sumario en /tmp/phase11-live-summary.log + 11-VALIDATION.md tabla LIVE-01 Evidence).         |

## n/a Dispositions (Package Legitimacy Gate not triggered)

| Threat ID | Category  | Plan  | Rationale                                                                                                                                                                                                |
|-----------|-----------|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| T-11-SC   | Tampering | 11-01 | NO new dependencies. All changes internal Python source edits. Existing uv.lock unchanged. `git diff 5b689d0..HEAD --stat -- '*.toml' 'uv.lock'` reporta solo pyproject.toml +8 lines (CR-08 extend-exclude). |
| T-11-SC   | Tampering | 11-02 | NO new dependencies. Same audit as 11-01 — `[tool.ruff] extend-exclude` housekeeping only.                                                                                                              |
| T-11-SC   | Tampering | 11-03 | NO new dependencies en Plan 11-03. Solo edits docs (VALIDATION.md, SUMMARY, CYCLE-REPORT) + live re-runs (driver-side mutations a findings.md).                                                          |

## Phase 8/9/10 Controls Reused (verified intact)

| Control                                                            | File                                                                                                       | Status |
|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|--------|
| matriz `RedactingFilter` (Phase 8 LOG-02)                          | `packages/matriz-client/src/matriz_client/_logging.py:123`                                                  | INTACT |
| `verification/test_logging_no_token_leak.py` (Phase 8 LOG-02)      | `verification/test_logging_no_token_leak.py`                                                               | GREEN  |
| `verification/test_logging_root_unchanged.py` (Phase 8 LOG-01)     | `verification/test_logging_root_unchanged.py`                                                              | GREEN  |
| Cross-leak sentinel (Phase 7 D-10 + Phase 10 matriz extension)     | `verification/test_sync_async_isolation.py:45` (matriz_client parametric entry)                            | GREEN  |
| Pitfall #4 mutation gate (no retry on POST cross-package)           | `verification/test_retry_mutation_gate.py`                                                                 | GREEN  |
| Fixture-reaches-production guard (Phase 6 Pitfall #1, 4 packages)  | `packages/*/tests/test_fixture_reaches_production.py`                                                      | GREEN  |
| Import-linter contracts (`_core.py` no importa `client.py`/`aio.py`) | `lint-imports` job — 4 contracts kept, 0 broken                                                          | GREEN  |
| BUG-01..04 regression (Phase 9)                                    | `packages/{matriz,higyrus,iol}-client/tests/test_*.py`                                                     | GREEN  |
| matriz async cross-leak sentinel (Phase 10)                        | `verification/test_sync_async_isolation.py::test_*matriz*`                                                 | GREEN  |

## Unregistered Flags

**None.**

3 SUMMARY files (`11-01-SUMMARY.md`, `11-02-SUMMARY.md`, `11-03-SUMMARY.md`)
contienen sección `## Threat Flags` cada uno; todos declaran "None" o un
mapeo explícito a una amenaza existente del register:

- `11-01-SUMMARY.md:176-178`: `None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. The marker contract (HARN-07) is a docs-format change within an existing operator-curated artifact, already covered by T-11-01 / T-11-02 / T-11-06.`
- `11-02-SUMMARY.md:210-218`: `None — los 6 fixes son refactors de safety internos de los drivers de verificación. No se introducen nuevos endpoints / network surface / auth paths / file-access patterns / schema changes. El threat register del plan (T-11-07..T-11-12 + T-11-SC) cubre todos los riesgos.`
- `11-03-SUMMARY.md:54`: `threat_flags: []  # No new threats surfaced during execution; T-11-15 (probe-stale revealed wire issue) was the trigger threat — mitigated by operator-gated checkpoint (D-LIVE-01 design)`.

Las deviaciones documentadas en cada SUMMARY (`Deviations from Plan`) fueron
auditadas y NO introducen nueva superficie de ataque:

- Plan 11-01 Dev #1 (Rule 1 — ART block frozen in operator_prefix path) — pure
  serialization fix; preserva los invariantes existentes (CR-01 preservation
  guard, CR-02 single-line title, ART block refresh). Cubierto por T-11-01.
- Plan 11-02 Dev #1 (Rule 1 — `PrimaryAPIError` ausente en `_RESIDUAL_PROBE_EXCEPTIONS`)
  — CR-06 narrowing regression descubierta durante CR-02 verification; fix
  agregó `PrimaryAPIError` al tuple. Cubierto por T-11-08.
- Plan 11-03 fix inline iol F-02 (INT-01 idiom en `main_iol.py:1289`) — driver
  edit (no client.py change); cubierto por T-11-15 trip-wire mitigation evidence.

## Adversarial-Stance Findings

Starting hypothesis (todas las threats OPEN hasta que grep pruebe el control).
Resultado: el patrón de mitigación de cada `mitigate` threat fue localizado en
el archivo declarado por el mitigation plan; cada match incluye `file:line`
arriba. Ninguna mitigation aceptada solo en documentación; cada match es un
grep real en código de producción o tests.

**Trip-wire dispositions:**

- **T-11-15 trip-wire SI disparó** (por diseño, no por fallo) — la live
  re-verification reveló iol F-02 (`_token_expires_at no se renovó`).
  Operator-gated checkpoint (D-LIVE-01) procesó la disposición correctamente:
  root cause confirmed PROBE_STALE (NOT client bug), inline fix aplicado
  (INT-01 idiom, `main_iol.py:1289-1294`), re-run PASS, operator signoff
  registrado en 11-VALIDATION.md frontmatter (`operator_signoff_date: 2026-06-14`,
  `operator_signoff_by: sebadlf`). La trip-wire es accept-con-evidencia-de-disparo;
  el operator-gated checkpoint funcionó como mitigation transversal.

**Blocking-regression auto-detectors per D-LIVE-01:**

| Gate | Source | Result |
|------|--------|--------|
| (a) Wire URL changes sync vs async | `verification/test_sync_async_isolation.py` | GREEN (9 passed) |
| (b) Probe outcome flips PASS→FAIL para PRE-baseline FIDs | Diff scan `/tmp/phase11-live-diff-<pkg>.log` | ZERO (blockers log empty) |
| (c) Credential leak en logs | `verification/test_logging_no_token_leak.py` + grep | GREEN (5 passed) + grep clean (0 matches en 11 log files) |

`/tmp/phase11-live-blockers.log` empty/0-bytes (confirmed) — cero blocking
regressions detected.

Las 3 `accept` dispositions están registradas verbatim arriba con sus rationales
del PLAN.md original. Las 3 `n/a` (T-11-SC × 3 plans) están registradas porque
ningún Plan en Phase 11 introdujo nuevas dependencias (solo `pyproject.toml`
+8 lines de `[tool.ruff] extend-exclude` — housekeeping, no package install).

## Summary

- **21 de 21 threats** resolve to CLOSED (16 mitigate verificadas + 3 accepted
  risk registrados + 3 n/a Package Legitimacy Gate × 3 plans, mismo T-11-SC ID).
- **0 BLOCKER**.
- **0 `unregistered_flag`** warnings (3 SUMMARY files declaran "None" o cero
  threat_flags; deviaciones auditadas y mapeadas a threat IDs existentes).
- **Phase 6/7/8/9/10 carry-forward controls** (Pitfall #1 fixture-reaches-production,
  import-linter contracts, mutation gate Pitfall #4, RedactingFilter LOG-02,
  cross-leak sentinel including matriz async extension, BUG-01..04 regression)
  permanecen INTACT + GREEN.
- **T-11-15 trip-wire** SI disparó (por diseño, reveló iol F-02 PROBE_STALE);
  operator-gated checkpoint procesó la disposición (inline fix INT-01 idiom +
  re-run PASS + operator signoff sebadlf 2026-06-14 en 11-VALIDATION.md frontmatter).
- **LIVE-01 acceptance bar PASSED** — 4 paquetes live re-runs vs baseline
  4d48e07, zero blocking regressions, operator dispositions captured per
  D-LIVE-01 (ámbito/higyrus/matriz `no_new_findings`; iol `F-02 FIXED`).
- **CI green final**: ruff (0 errors post-CR-08 extend-exclude vs 108
  pre-existing), ruff format (148 files clean), mypy strict (50 source files,
  0 issues), lint-imports (4/4 kept), pytest 907 × Python 3.12 + 3.13.
- **Milestone v1.1 ready to ship** desde perspectiva de auditoría de seguridad.
