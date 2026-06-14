---
phase: 09-deferred-bug-fixes
type: security-audit
asvs_level: 1
block_on: high
status: SECURED
threats_total: 20
threats_closed: 20
threats_open: 0
unregistered_flags: 0
audited_on: 2026-06-13
auditor: gsd-security-auditor
---

# Phase 09 — Security Audit (deferred bug fixes)

Verifies that every declared threat mitigation across the four sub-plans
(09-01, 09-02, 09-03, 09-04) is present in the implemented code. Audit is
read-only against the implementation tree at HEAD; SECURITY.md is the
single artifact produced.

## Audit Scope

| Plan  | Wave | Subject                                              | Threats audited |
|-------|------|------------------------------------------------------|-----------------|
| 09-01 | 1    | iol refresh_token lifecycle regression tests (BUG-03)| T-09-01-01..03 + SC |
| 09-02 | 1    | higyrus BUG-02 triage + BUG-04 multi-account + D-09  | T-09-02-01..05 + SC |
| 09-03 | 2    | matriz BUG-01 hybrid CFI guard                       | T-09-03-01..04 + SC |
| 09-04 | 3    | green-gate consolidation                             | T-09-04-01..04 + SC |

## Threat Verification (mitigate)

| Threat ID    | Category                  | Disposition | Evidence (file:line)                                                                                          | Result |
|--------------|---------------------------|-------------|---------------------------------------------------------------------------------------------------------------|--------|
| T-09-01-01   | Information Disclosure    | mitigate    | `packages/iol-client/src/iol_client/_logging.py:46-47,68-69` (`_REFRESH_TOKEN_URLENC_RE` + `_REFRESH_TOKEN_JSON_RE` applied in `_redact`); CI rule `.github/workflows/ci.yml:42-48` (`grep -rnE 'logging\.basicConfig\s*\(' packages/*/src/`); tests use synthetic seeds `seed-refresh-XYZ` / `STABLE-REFRESH` / `OLD-REFRESH` / `REVOKED-REFRESH` only (`test_refresh_token_lifecycle.py:51,94,148,187`) | CLOSED |
| T-09-01-02   | Tampering                 | mitigate    | Explicit per-test seeding `state.refresh_token = "<seed>"` (`test_refresh_token_lifecycle.py:51,94,148,187`; async mirror lines 57,97,142,174); autouse `_configure_sync` / `_configure_async` cleanup in `packages/iol-client/tests/conftest.py` (referenced by both test modules)                  | CLOSED |
| T-09-02-01   | Information Disclosure    | mitigate    | `packages/higyrus-client/src/higyrus_client/_logging.py:56` `_CUIT_QUERY_RE = re.compile(r"(cuit=)\d+")` applied in `_redact` (line 75); probe-scope try/finally restoration of `client.event_hooks` in `main_higyrus.py:270-282` (sync) and `319-327` (async)                                          | CLOSED |
| T-09-02-02   | Authorization Bypass      | mitigate    | `_state.account_id` removed (`grep -n "account_id" packages/higyrus-client/src/higyrus_client/_state.py packages/iol-client/src/iol_client/_state.py` → 0 hits); mocked regression `packages/higyrus-client/tests/test_multi_account.py:38-62` asserts 2 wire requests with paths `/5208/` and `/9999/` | CLOSED |
| T-09-02-03   | Tampering                 | mitigate    | (a) grep `account_id` in both `_state.py` files = 0; (b) `RequestSpec.account_id` + `request.extensions["account_id"]` intact in `packages/higyrus-client/src/higyrus_client/_core.py:117,132,310,353,408`; (c) Phase 8 logging/transport tests reported GREEN in 09-02-SUMMARY.md (`uv run pytest packages/higyrus-client/tests/test_logging.py packages/higyrus-client/tests/test_transport.py` → 34 passed) | CLOSED |
| T-09-03-01   | Input Validation Bypass   | mitigate    | `packages/matriz-client/src/matriz_client/_core.py:81` `_CFI_ISO_RE = re.compile(r"\A[A-Z]{6}\Z")` (anchors `\A...\Z`, not `^...$` — WR-01 hardened); line 467-469 `if not isinstance(cfi_code, str) or (cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.match(cfi_code))` (WR-02 hardening); raises `PrimaryAPIError(status="ERROR", description="CFI inválido: ...")` (line 470-477). Parametric test coverage: trailing newline (`ESXXXX\n`), trailing space, leading space, `None`, `123`, `[]` in `tests/test_core.py:368-377` | CLOSED |
| T-09-03-02   | Information Disclosure    | mitigate    | `_core.py:473-474` description format = f-string echoing the caller's `{cfi_code!r}` + literal regex constant `"(no es str, o no está en CFICode Literal, ni matchea ^[A-Z]{6}$)"`. No server state, file paths, credentials, or token material in the description text | CLOSED |
| T-09-04-01   | Spoofing                  | mitigate    | `.planning/phases/09-deferred-bug-fixes/09-VALIDATION.md` `Green-Gate Evidence` section (Steps 1-11) lines 195-272 captures pytest summary, ruff/format/mypy outputs, lint-imports, cross-leak sentinel, lint-logging refined grep, snapshot zero-diff, matriz aio.py LOC + `_atransport.py` absence, F-09/F-02 grep, test-count delta. Frontmatter `status: approved`, `approved_by: operator`, `approved_on: 2026-06-13` (lines 4-11) set AFTER evidence capture | CLOSED |
| T-09-04-02   | Tampering                 | mitigate    | `09-VALIDATION.md:206-216` Step 8 explicit snapshot zero-diff gate: `uv run pytest verification/test_public_surface.py -x` → `4 passed`. 09-04-SUMMARY.md Self-Check row "Snapshot zero-diff GREEN (4 passed)" confirms public surface unchanged | CLOSED |
| T-09-04-03   | Tampering                 | mitigate    | `test ! -e packages/matriz-client/src/matriz_client/_atransport.py` → file absent (verified via Bash test, exit 0, output "ABSENT"). Recorded in `09-VALIDATION.md:218-225` Step 9 "atransport ABSENT OK" + 09-04-SUMMARY.md row "matriz `_atransport.py` ABSENT — YES" | CLOSED |

## Accepted Risks (verbatim from threat register)

These items were declared `accept` at plan time and are recorded here without
re-audit, per the dispositions in `<threat_model>` blocks of plans 09-01..04.

| Threat ID    | Category               | Plan   | Acceptance Rationale (verbatim from PLAN.md) |
|--------------|------------------------|--------|----------------------------------------------|
| T-09-01-03   | Authentication Bypass  | 09-01  | Tests assume `_ensure_token()` refresh path executes when `state.token_expires_at == 0.0` — documented invariant in `client.py:277` (Phase 6 D-IOL-10) + `aio.py:259`. If a future edit breaks this invariant, the 4 lifecycle tests fail immediately (forensic-localizable). |
| T-09-01-SC   | Supply-chain           | 09-01  | No new packages installed. All dependencies (`pytest`, `pytest-httpx`, `pytest-asyncio`, `httpx`) already in `uv.lock` post-Phase-8 audit. |
| T-09-02-04   | Information Disclosure | 09-02  | `HIGYRUS_SAMPLE_CUENTAS` CSV: cuenta IDs are not secrets (no PII directly), but operator should avoid committing `.env`. `.gitignore` already excludes `.env`. |
| T-09-02-05   | Tampering              | 09-02  | F-02 finding manual edit; Phase 11 HARN-07/09 will provide BEGIN/END zone parser + operator-field preservation. Plan 09-02 trusts manual convention. |
| T-09-02-SC   | Supply-chain           | 09-02  | No new packages installed. |
| T-09-03-03   | Spoofing               | 09-03  | F-09 finding manual edit; Phase 11 HARN-07/09 will provide BEGIN/END zone parser. Plan 09-03 trusts manual convention. |
| T-09-03-04   | Tampering              | 09-03  | Single-site fix bypass via direct `httpx.Request` outside the builder is out of scope — public contract is that `Client.get_instruments_by_cfi` / `get_instruments_by_cfi` pass through the builder. |
| T-09-03-SC   | Supply-chain           | 09-03  | No new packages installed. All deps (`re` stdlib, `typing.get_args` stdlib, `pytest`) already in `uv.lock`. |
| T-09-04-04   | Information Disclosure | 09-04  | Green-gate evidence section captures pytest/ruff/mypy output — does NOT include `.env` reads. RedactingFilter (Phase 8 D-10) active if pytest runs trigger DEBUG. |
| T-09-04-SC   | Supply-chain           | 09-04  | No new packages installed. |

## Phase 8 Controls Reused (verified intact)

| Control                                              | File                                                              | Status |
|------------------------------------------------------|-------------------------------------------------------------------|--------|
| iol `RedactingFilter` (refresh_token redaction D-10) | `packages/iol-client/src/iol_client/_logging.py:46-49,68-70`     | INTACT |
| higyrus `RedactingFilter` (cuit + JSON token D-10)   | `packages/higyrus-client/src/higyrus_client/_logging.py:53-56,74-75` | INTACT |
| matriz `RedactingFilter` (X-Auth-Token + auth_basic) | `packages/matriz-client/src/matriz_client/_logging.py:58-78,99-104` | INTACT |
| CI grep rule blocking logging.basicConfig            | `.github/workflows/ci.yml:42-48`                                  | INTACT |
| Cross-leak sentinel test                             | `verification/test_sync_async_isolation.py`                       | EXISTS, GREEN per 09-VALIDATION.md Step 6 |

## Unregistered Flags

None. No SUMMARY file (09-01-SUMMARY.md, 09-02-SUMMARY.md, 09-03-SUMMARY.md,
09-04-SUMMARY.md) contains a `## Threat Flags` section, and no new attack
surface emerged that lacks a threat-register mapping. The cross-package
`_state.account_id` cleanup (D-09), the hybrid CFI guard (BUG-01), and the
refresh-token regression tests (BUG-03) are all covered by explicit threat IDs
above.

## Out-of-Scope Note (informational)

09-02-SUMMARY.md and 09-04-SUMMARY.md document an out-of-scope but necessary
Phase 6 migration drift repair in `main_higyrus.py` (commits `67ca550`,
`c1371fb`). This driver-only refactor migrates 21 sites to
`_get_default()._state.base_url` / `_get_default()._ensure_http_client()`
and does NOT change package source. The Phase 6/7 shim contract is
explicitly preserved (the regression `test_pep_562_shim_raises_for_legacy_credential_names`
holds). No new threat surface; logged here for completeness.

## Adversarial-Stance Findings

Starting hypothesis (all threats OPEN until grep proves the control). Result:
every mitigation pattern was located in the file declared by the mitigation
plan. No mitigation accepted purely on documentation; every match is a file:line
above. Non-mitigation dispositions (`accept`) are recorded verbatim with their
plan-time rationales — no transfer dispositions in this phase.

## Summary

- **20 of 20 threats** resolve to CLOSED (10 mitigate verified + 10 accepted risk recorded).
- **0 BLOCKER**.
- **0 unregistered_flag** warnings.
- Phase 8 security controls (RedactingFilter per package + CI grep rule + cross-leak sentinel) remain intact.
- Snapshot zero-diff explicit gate verified at `09-VALIDATION.md` Step 8.
- matriz `_atransport.py` invariant (Phase 8 D-25) holds: file absent.
- Phase 9 ready to ship from a security-audit perspective.
