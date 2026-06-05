---
phase: 02-mbito-verification
verified: 2026-06-05T23:30:00Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
---

# Phase 2: Ámbito Verification — Verification Report

**Phase Goal:** Ejercitar la API pública de `ambito-financiero-client` (sync + async) contra `mercados.ambito.com`, detectar discrepancias entre el cliente y el servicio en vivo, lockear los invariantes con tests mockeados, y commitear la baseline DRIFT-01 (schema snapshot). Verificación viva de AMB-01..AMB-06 + DRIFT-01.
**Verified:** 2026-06-05T23:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                           | Status     | Evidence                                                                                                   |
|----|------------------------------------------------------------------------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------|
| 1  | `append_finding(...)` exposes D-10 semantics and is re-exported via barrel (CR-01/CR-02/WR-04 hardened)         | ✓ VERIFIED | `verification/findings.py:403` — function present; fix commit 4f22c6d added `_replace_art_block`, single-line title guard, pkg slug validation |
| 2  | `verification/__init__.py` re-exports `append_finding` in `__all__` alphabetically                             | ✓ VERIFIED | `verification/__init__.py:32,41` — `from verification.findings import append_finding, ...`; `"append_finding"` at line 41 |
| 3  | `main_ambito_financiero.py` has 7 named probes (D-01..D-26) in correct D-13 order                              | ✓ VERIFIED | All 10 module callables confirmed: `probe_happy_sync`, `probe_happy_async`, `probe_parity_sync_async`, `probe_parse_decimal_adversarial`, `probe_no_data`, `probe_schema_snapshot`, `probe_antibot`; antibot is last |
| 4  | `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` committed (DRIFT-01)    | ✓ VERIFIED | File exists with D-21 envelope: `endpoint`, `client_function`, `captured_at`, `base_url`, `sample_date`, `schema=[["str"]]`; committed in `6af5b83` |
| 5  | `.planning/verification/ambito-financiero-client-findings.md` committed with F-01 ANTI-BOT EXPECTED (AMB-06)   | ✓ VERIFIED | File contains `# Findings: ambito-financiero-client-client`, ART block with `https://mercados.ambito.com`, Index row `F-01 | ANTI-BOT | sync | EXPECTED`; committed in `6af5b83` |
| 6  | `test_client.py` and `test_async_client.py` have `# ------ Verified live (Phase 2) ------` + `# ------ Regressions ------` sections | ✓ VERIFIED | Both files confirmed: sync has 3 Phase 2 tests (AMB-01/02/03); async has mirror 3 tests; both have Regressions placeholder |
| 7  | Full suite green at 181 passed (was 157 pre-Phase 2)                                                            | ✓ VERIFIED | `uv run pytest -q` → **181 passed, 1 deselected** (the 1 deselected is the live-marker test, not a failure) |
| 8  | CR-01/CR-02/WR-01/WR-03/WR-04/IN-03 fixed in-cycle with regression tests                                       | ✓ VERIFIED | Fix commits `4f22c6d` (CR-01, CR-02, WR-04) and `2fef232` (WR-01, WR-03, IN-03) confirmed; `test_findings_helper.py` has regression tests for CR-01/CR-02/WR-04; `test_driver_invariants.py` has regression tests for WR-01/WR-03/IN-03 — all 6 pass |
| 9  | Live verification: `precio=1455.0` observed 2026-06-05, `schema sin drift`, exit code 0 (D-04 honored)         | ✓ VERIFIED | SUMMARY.md ground truth: Run 2 output `PROBE happy_sync: PASS precio=1455.0`, `PROBE schema_snapshot: PASS schema sin drift`, `SUMMARY: PASS=6 FAIL=0 SKIPPED=0 FINDING=1`; commit `6af5b83` message confirms `sync==async=1455.0` |
| 10 | No regression of the 157 pre-Phase-2 test baseline                                                              | ✓ VERIFIED | 181 total passed > 157 baseline; `uv run pytest -q` exits 0 |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact                                                                                      | Expected                                              | Status     | Details                                                                          |
|-----------------------------------------------------------------------------------------------|-------------------------------------------------------|------------|----------------------------------------------------------------------------------|
| `verification/findings.py`                                                                    | `def append_finding` with D-10 invariants             | ✓ VERIFIED | 494 lines; `append_finding` at line 403; `_replace_art_block`, `_parse_findings`, `_serialize_findings` private helpers; CR-01/CR-02/WR-04 hardened |
| `verification/__init__.py`                                                                    | Re-exports `append_finding` in `__all__`              | ✓ VERIFIED | 50 lines; `append_finding` imported at line 32, listed in `__all__` at line 41 |
| `packages/ambito-financiero-client/tests/test_findings_helper.py`                            | >= 6 unit tests for D-10 invariants                   | ✓ VERIFIED | 12 test functions: 9 original + 3 regression tests for CR-01/CR-02/WR-04 |
| `main_ambito_financiero.py`                                                                   | 7 named probes + summary + D-26 safe_print            | ✓ VERIFIED | 728 lines; 7 probes confirmed; `asyncio.run` once; no `time.sleep`; 2 `safe_print` calls |
| `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json`       | D-21 envelope with `schema:[["str"]]`                 | ✓ VERIFIED | Committed `6af5b83`; 6 keys present; `schema=[["str"]]`; not gitignored |
| `.planning/verification/ambito-financiero-client-findings.md`                                | Header + ART block + F-01 ANTI-BOT EXPECTED           | ✓ VERIFIED | Committed `6af5b83`; header `# Findings: ambito-financiero-client-client`; ART timestamp `2026-06-05T22:37:10Z`; F-01 EXPECTED |
| `packages/ambito-financiero-client/tests/test_client.py`                                     | Phase 2 section + Regressions section                 | ✓ VERIFIED | Lines 59/101: both dividers present; 3 Verified-live tests (AMB-01/02/03) |
| `packages/ambito-financiero-client/tests/test_async_client.py`                               | Phase 2 section + Regressions section (async mirror)  | ✓ VERIFIED | Lines 45/86: both dividers present; 3 Verified-live async tests |
| `packages/ambito-financiero-client/tests/test_driver_invariants.py`                          | Regression tests for WR-01/WR-03/IN-03                | ✓ VERIFIED | 6 tests: WR-03 x2, WR-01 x2, IN-03 x1, sanity x1 — all 6 pass |

### Key Link Verification

| From                                    | To                                             | Via                                          | Status     | Details                                                        |
|-----------------------------------------|------------------------------------------------|----------------------------------------------|------------|----------------------------------------------------------------|
| `verification/__init__.py`              | `verification.findings.append_finding`         | `from verification.findings import append_finding` | ✓ WIRED | Line 32 of `__init__.py`; barrel re-export confirmed functional |
| `test_findings_helper.py`               | `verification.findings.append_finding`         | `from verification.findings import append_finding` | ✓ WIRED | Line 25; 12 tests pass |
| `main_ambito_financiero.py`             | `verification.findings.append_finding`         | `from verification.findings import append_finding` | ✓ WIRED | Line 50; `append_finding` called in all 7 probes |
| `main_ambito_financiero.py`             | `verification.write_findings + safe_print + schema_of` | `from verification import ...`           | ✓ WIRED | Line 49 |
| `main_ambito_financiero.py`             | `ambito_financiero_client` sync + `aio`        | `import ambito_financiero_client as ambito; from ambito_financiero_client import aio` | ✓ WIRED | Lines 52-53 |
| `test_client.py`                        | `ambito_financiero_client._parsing.parse_ar_decimal` | `from ambito_financiero_client._parsing import parse_ar_decimal` | ✓ WIRED | Line 19; `test_parse_ar_decimal_formato_real` passes |
| `get-dollar-banco-nacion.json`          | `main_ambito_financiero.py::probe_schema_snapshot` | first live driver run generated this file   | ✓ WIRED | Commit `6af5b83`; second run confirmed "schema sin drift" |

### Behavioral Spot-Checks

| Behavior                                             | Command                                                                   | Result                          | Status  |
|------------------------------------------------------|---------------------------------------------------------------------------|---------------------------------|---------|
| Full test suite passes (181 tests)                   | `uv run pytest -q`                                                        | 181 passed, 1 deselected        | ✓ PASS  |
| findings helper tests green (12 tests)               | `uv run pytest packages/ambito-financiero-client/tests/test_findings_helper.py -v` | 12 passed            | ✓ PASS  |
| driver regression tests green (6 tests)              | `uv run pytest packages/ambito-financiero-client/tests/test_driver_invariants.py -v` | 6 passed            | ✓ PASS  |
| ambito package tests green (75 tests)                | `uv run pytest packages/ambito-financiero-client -q`                     | 75 passed, 1 deselected         | ✓ PASS  |
| mypy strict clean                                    | `uv run mypy verification main_ambito_financiero.py`                     | Success: no issues in 9 files  | ✓ PASS  |
| ruff lint clean                                      | `uv run ruff check verification main_ambito_financiero.py packages/ambito-financiero-client/tests/` | All checks passed | ✓ PASS |
| ruff format clean                                    | `uv run ruff format --check ...`                                         | 22 files already formatted      | ✓ PASS  |
| append_finding barrel import                         | `uv run python -c "from verification import append_finding; import verification; assert 'append_finding' in verification.__all__"` | OK | ✓ PASS |
| 10 driver callables present                          | `uv run python -c "import main_ambito_financiero as m; [getattr(m,p) for p in ...]"` | all 10 entries present | ✓ PASS |
| D-11: exactly one asyncio.run in driver              | `grep -c 'asyncio.run(' main_ambito_financiero.py`                       | 2 (1 in docstring, 1 in code)   | ✓ PASS  |
| D-14: no time.sleep in driver                        | `grep -c 'time.sleep' main_ambito_financiero.py`                         | 0                               | ✓ PASS  |
| Baseline artifacts not gitignored                    | `git check-ignore <schema.json> <findings.md>`                           | exit=1 (NOT ignored)            | ✓ PASS  |
| Live run (precio=1455.0, 2026-06-05, exit 0)         | Human checkpoint in Task 3.2 (D-04 + D-02 observed)                     | 6 PASS + 1 FINDING EXPECTED     | ✓ PASS  |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                  | Status      | Evidence                                                                       |
|-------------|-------------|------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------------|
| AMB-01      | 02-02, 02-03 | Real `get_dollar_banco_nacion` call succeeds sync+async; `list[list[str]]` shape | ✓ SATISFIED | Live run PASS; `test_get_dollar_banco_nacion_shape_list_of_list_str` + async mirror |
| AMB-02      | 02-02, 02-03 | `parse_ar_decimal` verified against `"1.415,00"` format                     | ✓ SATISFIED | `test_parse_ar_decimal_formato_real` (sync+async); `probe_parse_decimal_adversarial` in driver |
| AMB-03      | 02-02, 02-03 | URL format + day > 12 verified                                               | ✓ SATISFIED | `test_get_dollar_banco_nacion_emite_url_dia_gt_12` (sync+async); `_last_business_day_with_day_gt_12` helper |
| AMB-04      | 02-02, 02-03 | `NoDataError` fires for date with no quotation                               | ✓ SATISFIED | Pre-existing `test_get_dollar_banco_nacion_sin_datos_levanta` (green); `probe_no_data` PASS in live run |
| AMB-05      | 02-02, 02-03 | Structural sync↔async parity                                                 | ✓ SATISFIED | `probe_parity_sync_async` PASS live (`sync==async=1455.0`); dual test surface in both test files |
| AMB-06      | 02-02, 02-03 | Anti-bot: correct UA passes, bad UA gets 403 without looping                 | ✓ SATISFIED | `probe_antibot` FINDING F-01 EXPECTED committed; D-14 one-shot, D-12 opt-in confirmed |
| DRIFT-01    | 02-01, 02-02, 02-03 | Schema snapshot committed for verified endpoint                       | ✓ SATISFIED | `get-dollar-banco-nacion.json` committed `6af5b83`; `schema=[["str"]]`; second run "sin drift" |

### Anti-Patterns Found

| File                                      | Pattern                                     | Severity | Impact                                                                 |
|-------------------------------------------|---------------------------------------------|----------|------------------------------------------------------------------------|
| `verification/findings.py`                | No debt markers (TBD/FIXME/XXX/TODO)        | None     | Clean                                                                  |
| `main_ambito_financiero.py`               | No debt markers                             | None     | Clean (WR-01/WR-03 dead-code fixed; IN-03 fixed)                       |
| `test_findings_helper.py`                 | No debt markers                             | None     | Clean                                                                  |
| `test_client.py` / `test_async_client.py` | Regressions section is empty placeholder    | Info     | Expected by design (note MVP: opportunistic only); placeholder comment is explicit |
| `test_driver_invariants.py`               | No debt markers                             | None     | Clean                                                                  |

No TBD, FIXME, or XXX markers found in any Phase 2 modified file. The empty `# ------ Regressions ------` sections are intentional per the MVP note in the plan ("vacío hasta que un finding promovido a CONFIRMED se cierre como FIXED").

### Deferred Warnings from Code Review

The following review items were classified as non-blocking and deferred per `02-REVIEW.md`:

| ID    | Description                                          | Reason Deferred                                                |
|-------|------------------------------------------------------|----------------------------------------------------------------|
| WR-02 | Float equality vs tolerance in parity probe          | Latent; not triggered in vivo; AR-decimal integers are exact |
| WR-05 | Timezone: `dt.date.today()` vs AR/UTC boundary       | Latent for cross-machine runs; not blocking for single-machine driver |
| WR-06 | `schema_of` heterogeneous list blind spot            | Ámbito endpoint is homogeneous `list[list[str]]`; documented concern for Phases 3-5 |
| WR-07 | `test_async_parse_ar_decimal_formato_real` is a sync test | Cosmetic naming issue; passes correctly; D-09 symmetry documented |
| IN-01 | `_fid_counter` non-reentrant across multiple `main()` calls | Single-process driver; not a practical concern |
| IN-02 | `repr(rows)` truncation in SHAPE findings           | Payload is small for Ámbito; cosmetic concern |
| IN-04 | `findings_path` in `findings.__all__` but not in barrel `__all__` | Consistency gap; not blocking |
| IN-05 | Auth tests only assert exception type, not status code | Weak test signal; not causing false passes |
| IN-06 | `envelope: dict[str, object]` masks type info       | Runtime correct; mypy cosmetic concern |

### Human Verification Required

No items remain requiring human verification. The human checkpoint (Task 3.2) was completed and the result was "approved + run AMB-06" with the baseline commit `6af5b83`.

### Gaps Summary

No gaps found. All 10 must-have truths are VERIFIED, all artifacts exist and are substantive (not stubs), all key links are wired, all code review BLOCKERs were fixed in-cycle with regression tests, and the full mocked test suite (181 tests) passes green with mypy strict and ruff clean.

---

## Detailed Verification Evidence Trail

### Truth 1: append_finding D-10 (with post-review hardening)

The function exists at `verification/findings.py:403` with the exact signature from the plan. Three post-review hardening commits are confirmed:

- `4f22c6d`: CR-01 (`_replace_art_block` in-place ART refresh on preservation path), CR-02 (single-line title invariant with ValueError), WR-04 (`_PKG_SLUG_RE` path traversal guard)
- `2fef232`: WR-01 (drop `exc.args[0]` dead-code fallback in antibot), WR-03 (single HTTP call per happy probe), IN-03 (`contextlib.suppress(Exception)` around `aio.aclose()`)

Regression tests for each fix are confirmed passing (12 tests in `test_findings_helper.py`, 6 tests in `test_driver_invariants.py`).

### Truth 3: 7 named probes in D-13 order

Probe order confirmed in `main()` (lines 690-710): `probe_happy_sync` → `probe_happy_async` (via `_async_main`) → `probe_parity_sync_async` → `probe_parse_decimal_adversarial` → `probe_no_data` → `probe_schema_snapshot` → `probe_antibot` (last per D-13).

Source assertions confirmed clean:
- D-11: `asyncio.run(` appears twice in the file — once in a docstring (line 660), once as the actual call (line 694). Exactly one runtime invocation.
- D-14: `time.sleep` count = 0.
- D-26: `safe_print(` count = 2 (one per-probe loop line, one SUMMARY line).

### Truth 7: 181 passed (was 157 pre-Phase 2)

Breakdown of test growth:
- Pre-Phase 2 baseline: 157 tests (per plan context)
- Phase 2 additions: +9 (Plan 02-01: 9 findings helper tests) + 6 (Plan 02-03: 6 Phase 2 Verified-live tests in test_client/test_async_client) + 6 (post-review: test_driver_invariants.py) + 3 (post-review regression tests in test_findings_helper.py) = +24
- Total confirmed: 181 passed ✓

### Truth 9: Live verification ground truth

From `02-03-SUMMARY.md` and commit `6af5b83`:

Run 2 (with VERIFY_ANTIBOT=1, 2026-06-05):
```
PROBE happy_sync: PASS precio=1455.0
PROBE happy_async: PASS precio=1455.0
PROBE parity_sync_async: PASS sync==async=1455.0
PROBE parse_decimal: PASS venta=1455.0
PROBE no_data: PASS NoDataError para 2026-08-04
PROBE schema_snapshot: PASS schema sin drift
PROBE antibot: FINDING F-01 (EXPECTED)
SUMMARY: PASS=6 FAIL=0 SKIPPED=0 FINDING=1
```

Exit code 0 (D-04). D-25 confirmed (second run "schema sin drift" without overwriting). D-13 order honored (antibot last). D-14 honored (one-shot).

---

_Verified: 2026-06-05T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
