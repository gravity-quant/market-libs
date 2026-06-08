---
phase: 04-higyrus-verification
verified: 2026-06-08T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 4: Higyrus Verification — Verification Report

**Phase Goal:** The Higyrus client is fully verified end-to-end on both surfaces using mandatory raw-payload diffing against declared model fields (defeating the `SafeModel.from_api` false-pass trap), with the known async `drop_none` deviation confirmed or denied, error and empty-data paths verified, account data anonymized in fixtures, and each confirmed bug fixed in both surfaces with regression tests.

**Verified:** 2026-06-08T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification (previous verifier socket-errored before writing this file)

**Note on MVP mode declaration:** ROADMAP.md declares `mode: mvp` for Phase 4 but the phase goal is not in User Story format (`gsd-sdk query user-story.validate` returns `valid: false`). Verification proceeds under the standard goal-backward methodology (not MVP-mode user-flow tables), treating the 5 Success Criteria from ROADMAP.md as the contract. This was discussed with the user via the project context noting "MVP rule: la fase pasa aun sin findings CONFIRMED" (Plan 04-03 SUMMARY).

## Goal Achievement

### Observable Truths (Success Criteria from ROADMAP.md)

| #  | Truth                                                                                                                                                                                                                                                                                          | Status     | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | The auth flow (login + lazy-auth) is verified live on both surfaces, and the 5 endpoints are exercised sync and async with raw payloads retained (HIGY-01, HIGY-02)                                                                                                                            | ✓ VERIFIED | `main_higyrus.py` exposes 18 named probes including `probe_login_sync`, `probe_login_async`, plus 10 endpoint probes (5 × 2 surfaces). Live run documented in 04-02 SUMMARY: `PASS=16 FAIL=0 SKIPPED=1 FINDING=1`. Timestamp in schemas: `2026-06-08T02:03:51+00:00`. All 18 probe functions discoverable via `dir(main_higyrus)`.                                                                                                                                                                                                                                                                                                       |
| 2  | Each endpoint's raw `resp.json()` is diffed bidirectionally against the model's declared fields (`get_type_hints`) — flagging both wire keys the model ignores and model fields the wire drops — so a non-raising `from_api` never counts as a pass (HIGY-03)                                  | ✓ VERIFIED | `_diff_safemodel_bidirectional` helper present at `main_higyrus.py:234`, exercises recursive descent into nested SafeModel + `list[SafeModel]` via `typing.get_type_hints`. `probe_field_type_map` (probe 14) detected drift → emitted F-01 EXPECTED (`Posicion.disponibleAjustado` FCI-conditional). Mocked tolerance invariant present: `test_safemodel_from_api_typed_defaults` + async mirror, located under `# ------ Verified live (Phase 4) ------` section.                                                                                                                                                                      |
| 3  | The `assert isinstance(raw, list/dict)` behavior is verified live and flagged as a candidate fix to a typed `HigyrusAPIError`, the `"errors"`-key error path is confirmed on a bad request, and empty/204 responses yield an empty list (not crash, not `None`) (HIGY-04, HIGY-05, HIGY-07)    | ✓ VERIFIED | HIGY-04 fix applied: `grep -c "assert isinstance"` returns 0 in both `client.py` and `aio.py`; 5 sites each replaced with `raise HigyrusAPIError(status_code=0, errors=[{"title":"shape mismatch", "detail":...}])`. Docstring sentinel documented in `exceptions.py` ("o 0 si el error fue detectado client-side"). HIGY-05: `probe_errors_envelope_sync`/`probe_errors_envelope_async` both PASS in live run. HIGY-07: `test_get_movimientos_empty_path_returns_list`, `test_get_posiciones_empty_path_returns_list`, plus async mirrors verify empty path → `[]`. 10 regression tests for HIGY-04 under `# ------ Regressions ------`. |
| 4  | Sync↔async parity is verified, including the known `drop_none` deviation in the async `_request`, which is confirmed or denied (HIGY-06)                                                                                                                                                       | ✓ VERIFIED | `probe_parity_sync_async` (probe 13) PASS in live run with `query='fechaDesde=08/05/2026&fechaHasta=07/06/2026'` matching sync↔async. Wire query capture uses `event_hooks` (post-WR-05 fix) in `_capture_sync_query_string` / `_capture_async_query_string`. Mocked equivalent: `test_get_movimientos_drop_none_emits_only_required_params` + async mirror confirm identical query emission. `drop_none` deviation: confirmed equivalent (deviation harmless under current wire shape).                                                                                                                                                  |
| 5  | Every discrepancy is classified in `.planning/verification/higyrus-findings.md` with account data anonymized before any fixture is committed, a schema snapshot is committed, and each confirmed bug is fixed in both surfaces with paired mocked regression tests; the mocked suite + mypy strict + ruff pass green | ✓ VERIFIED | `.planning/verification/higyrus-client-findings.md` committed with F-01 EXPECTED + F-02 OPEN classified per D-08/D-09 lifecycle. 5 schema snapshots committed in `.planning/verification/schemas/higyrus-client/` with envelope D-21 (6 keys); `schema` blobs contain ONLY type names (`str`, `int`, `float`, `NoneType`) — PII-free per T-4-SC. `sample_params` contains `id_cuenta=5208` as operational metadata (audited in 04-02 SUMMARY retrospective). HIGY-04 + wire encoding bugs both fixed dual sync+async with regression tests. `uv run pytest packages/higyrus-client -q` → 51 passed; mypy strict + ruff check + format clean. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                                                                       | Expected                                                          | Status     | Details                                                                                                                                                |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `packages/higyrus-client/src/higyrus_client/client.py`                         | HIGY-04 fix: 5 typed raises; wire encoding fix (urlencode + safe="/") | ✓ VERIFIED | grep: `assert isinstance == 0`, `shape mismatch == 5`, `status_code=0 == 5`, `urlencode == 2`, `safe="/" == 1`, `doseq=True` present                  |
| `packages/higyrus-client/src/higyrus_client/aio.py`                            | Mirror of sync surface                                            | ✓ VERIFIED | Same grep counts as client.py — dual sync/async invariant preserved                                                                                    |
| `packages/higyrus-client/src/higyrus_client/exceptions.py`                     | D-HIGY-8 sentinel docstring                                       | ✓ VERIFIED | Contains `o 0 si el error fue detectado client-side (e.g., shape mismatch tras un 2xx exitoso)` — no new subclass introduced                          |
| `packages/higyrus-client/tests/test_client.py`                                 | 3 sections: Verified live (Phase 4), Regressions, Wire encoding   | ✓ VERIFIED | All 3 dividers present at lines 145, 250, 317. 5 HIGY-04 regression tests + 6 Verified-live invariants + 1 wire encoding test                          |
| `packages/higyrus-client/tests/test_async_client.py`                           | Mirror with same 3 sections                                       | ✓ VERIFIED | All 3 dividers present at lines 65, 179, 246. 5 async regressions + 7 async invariants + 1 wire encoding test                                          |
| `main_higyrus.py`                                                              | 18 named probes + 2 Pattern-1 helpers + 2 Pattern-2 helpers + `_AsyncResults` dataclass + cascade flag + resolved_cuenta | ✓ VERIFIED | 18 probes discoverable via reflection; all 6 named helpers (`_diff_safemodel_bidirectional`, `_capture_sync_query_string`, `_capture_async_query_string`, `_AsyncResults`, `_resolved_cuenta`, `_auth_failed`) present |
| `packages/higyrus-client/.env.example`                                         | 4 new optional Phase 4 vars (D-HIGY-14)                           | ✓ VERIFIED | `HIGYRUS_SAMPLE_CUENTA`, `HIGYRUS_SAMPLE_TIPO_CUENTA`, `HIGYRUS_SAMPLE_NIVEL`, `VERIFY_HIGYRUS_BAD_CREDS` all present                                  |
| `.planning/verification/schemas/higyrus-client/get-health.json`                | DRIFT-01 mirror baseline                                          | ✓ VERIFIED | Envelope D-21 (6 keys); schema `{status: str}` — PII-free                                                                                              |
| `.planning/verification/schemas/higyrus-client/get-listado-cuentas.json`       | DRIFT-01 mirror baseline                                          | ✓ VERIFIED | Envelope D-21; schema `[]` (F-02 NO-DATA OPEN documented)                                                                                              |
| `.planning/verification/schemas/higyrus-client/get-movimientos.json`           | DRIFT-01 mirror baseline                                          | ✓ VERIFIED | Envelope D-21; 22 keys typed (12 `str`, 1 `float`, 9 `NoneType`) — PII-free                                                                            |
| `.planning/verification/schemas/higyrus-client/get-posicion-valuada.json`      | DRIFT-01 mirror baseline                                          | ✓ VERIFIED | Envelope D-21; 21 keys typed — PII-free                                                                                                                |
| `.planning/verification/schemas/higyrus-client/get-posiciones.json`            | DRIFT-01 mirror baseline                                          | ✓ VERIFIED | Envelope D-21; 19 keys typed — PII-free                                                                                                                |
| `.planning/verification/higyrus-client-findings.md`                            | Phase 4 findings (skeleton + classified findings)                 | ✓ VERIFIED | 2 findings: F-01 SHAPE/EXPECTED (`Posicion.disponibleAjustado` FCI-conditional) + F-02 NO-DATA/OPEN (listado=0 deferred). Cosmetic: header has typo `higyrus-client-client` (documented in 04-03 SUMMARY) |

### Key Link Verification

| From                                                | To                                                       | Via                                                                                | Status   | Details                                                                                                       |
| --------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------- |
| `client.py::get_health` (and 4 more)                | `exceptions.HigyrusAPIError`                             | `raise HigyrusAPIError(status_code=0, errors=[{"title":"shape mismatch", ...}])`   | ✓ WIRED  | 5 raises present in sync; verified by `grep -c "raise HigyrusAPIError" == 5`                                  |
| `aio.py::get_health` (and 4 more)                   | `exceptions.HigyrusAPIError`                             | Same pattern                                                                       | ✓ WIRED  | 5 raises present in async; mirror byte-identical to sync                                                      |
| `client.py::_request`                               | `urllib.parse.urlencode + quote`                         | `urlencode(clean_params, doseq=True, quote_via=quote, safe="/")` pre-attached to URL | ✓ WIRED  | Import present at line 31; usage at line 190. Same in `aio.py` at lines 24 + 213                              |
| `test_client.py::Regressions section`               | `HigyrusAPIError`                                        | `with pytest.raises(HigyrusAPIError) as exc_info: ...; exc_info.value.status_code == 0` | ✓ WIRED  | 6 occurrences of `exc_info.value.status_code == 0` in test_client.py; 5 in test_async_client.py              |
| `main_higyrus.py::probe_*`                          | `verification.findings.append_finding`                   | Module-level import                                                                | ✓ WIRED  | `append_finding` imported and invoked from probes                                                             |
| `main_higyrus.py::probe_field_type_map`             | `_diff_safemodel_bidirectional`                          | Recursive call with `get_type_hints`                                               | ✓ WIRED  | Function defined at line 234; called from probe 14                                                            |
| `main_higyrus.py::probe_parity_sync_async`          | `httpx.Client.event_hooks` / `httpx.AsyncClient.event_hooks` | `_capture_sync_query_string` / `_capture_async_query_string` via event_hooks       | ✓ WIRED  | Post-WR-05 fix: `event_hooks` used in lieu of bound-method monkey-patch (9 references)                        |
| `main_higyrus.py::probe_auth_401`                   | `higyrus_client.configure(password=...)`                 | `try/finally` injection with `_INVALID` suffix                                     | ✓ WIRED  | Present; opt-in via `VERIFY_HIGYRUS_BAD_CREDS=1`                                                              |

### Data-Flow Trace (Level 4)

Phase 4 deliverables are not user-facing dynamic components — they are: (a) library code modifications, (b) a verification driver (`main_higyrus.py`) that emits stdout lines + writes JSON/MD files, (c) tests, and (d) committed artifacts. Data flow verification:

| Artifact                                  | Data Variable                  | Source                                          | Produces Real Data | Status      |
| ----------------------------------------- | ------------------------------ | ----------------------------------------------- | ------------------ | ----------- |
| `main_higyrus.py::probe_*` ProbeResults   | `result: ProbeResult`          | Direct call to live Higyrus API via `higyrus_client` | Yes (live run on 2026-06-08T02:03:51Z documented; 16 PASS) | ✓ FLOWING   |
| `schemas/higyrus-client/*.json`           | `schema` blob                  | `schema_of(payload)` from live `resp.json()`    | Yes (real types from real wire payload of 5208 account) | ✓ FLOWING   |
| `higyrus-client-findings.md`              | F-01, F-02 entries             | `append_finding(...)` from probes               | Yes (classified per D-08/D-09; written by live run) | ✓ FLOWING   |

### Behavioral Spot-Checks

| Behavior                                                                                       | Command                                                                                                | Result                                            | Status |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------- | ------ |
| `main_higyrus.py` module importable and exposes 18 probes                                      | `uv run python -c "import main_higyrus as m; print(len([n for n in dir(m) if n.startswith('probe_')]))"` | `18`                                              | ✓ PASS |
| All 6 named helpers present                                                                    | `python -c "import main_higyrus as m; print(all(hasattr(m, h) for h in [...]))"`                        | `True` for all                                    | ✓ PASS |
| HIGY-04 fix applied: 0 `assert isinstance` remaining in client.py and aio.py                   | `grep -c "assert isinstance" client.py aio.py`                                                         | `0` each                                          | ✓ PASS |
| Wire encoding fix applied: literal `/` preserved                                               | `grep -c 'safe="/"' client.py aio.py`                                                                  | `1` each                                          | ✓ PASS |
| Sentinel `status_code=0` documented in exceptions.py                                           | `grep "o 0 si el error fue detectado" exceptions.py`                                                   | match                                             | ✓ PASS |
| higyrus-client test suite green                                                                | `uv run pytest packages/higyrus-client -q`                                                             | `51 passed`                                       | ✓ PASS |
| Whole-repo test suite green (no cross-phase regression)                                        | `uv run pytest -q`                                                                                     | `232 passed, 1 deselected`                        | ✓ PASS |
| Per-package mypy strict                                                                        | `uv run mypy packages/higyrus-client`                                                                  | `Success: no issues found in 9 source files`      | ✓ PASS |
| ruff check + format                                                                            | `uv run ruff check && ruff format --check packages/higyrus-client main_higyrus.py`                     | `All checks passed`, `10 files already formatted` | ✓ PASS |
| Live driver run executed at least once (operator-observed checkpoint Plan 04-02 Task 2.3)      | Schema timestamps `2026-06-08T02:03:51+00:00` consistent across 5 files                                | Artifacts committed; SUMMARY 04-02 documents `PASS=16 FAIL=0 SKIPPED=1 FINDING=1` | ✓ PASS (operator-observed) |

### Probe Execution

The phase declares 18 driver probes (`PROBE <name>` markers) executed by `main_higyrus.py` against live Higyrus. These require real credentials and external HTTP; they are not bash-runnable from the verifier sandbox. SUMMARY 04-02 documents the final live run: `SUMMARY: PASS=16 FAIL=0 SKIPPED=1 FINDING=1` with the SKIPPED corresponding to opt-in `probe_auth_401` (gated by `VERIFY_HIGYRUS_BAD_CREDS=1`) and FINDING corresponding to F-01 EXPECTED (documented behavior). The 5 schema snapshots have consistent `captured_at` timestamps (`2026-06-08T02:03:51+00:00`), corroborating the live run.

| Probe                       | Command                                                  | Result                                                  | Status |
| --------------------------- | -------------------------------------------------------- | ------------------------------------------------------- | ------ |
| 18 named probes (live run)  | `uv run --package higyrus-client python main_higyrus.py` (operator-run with real creds) | `PASS=16 FAIL=0 SKIPPED=1 FINDING=1` per 04-02 SUMMARY  | ✓ PASS (operator-observed) |

### Requirements Coverage

| Requirement | Source Plan(s)        | Description                                                                                | Status     | Evidence                                                                                                                                                |
| ----------- | --------------------- | ------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HIGY-01     | 04-02                 | Live auth (login + lazy-auth) sync + async                                                 | ✓ SATISFIED | `probe_login_sync` + `probe_login_async` PASS in live run; lazy-auth confirmed by 04-02 SUMMARY                                                          |
| HIGY-02     | 04-02, 04-03          | Live happy-path sweep of 5 endpoints sync + async with raw payloads retained               | ✓ SATISFIED | 10 endpoint probes PASS + URL-verbatim mocked invariants in `# ------ Verified live (Phase 4) ------`                                                    |
| HIGY-03     | 04-02, 04-03          | Bidirectional diff `wire ↔ model.get_type_hints`                                            | ✓ SATISFIED | `_diff_safemodel_bidirectional` recursive helper at `main_higyrus.py:234`; `probe_field_type_map` detected F-01 EXPECTED; mocked tolerance invariant lockea |
| HIGY-04     | 04-01, 04-04          | Fix `assert isinstance` → typed `HigyrusAPIError`                                          | ✓ SATISFIED | 10 sites fixed (5 sync + 5 async); 10 mocked regressions in `# ------ Regressions ------`; sentinel `status_code=0` documented                          |
| HIGY-05     | 04-02, 04-03          | Live `"errors"`-key error path on bad request                                              | ✓ SATISFIED | `probe_errors_envelope_sync`/`probe_errors_envelope_async` both PASS; mocked equivalent `test_errors_envelope_parsed_on_4xx` + async mirror              |
| HIGY-06     | 04-02, 04-03, 04-04   | Sync↔async parity including `drop_none` deviation                                          | ✓ SATISFIED | `probe_parity_sync_async` PASS with identical query strings; mocked `test_get_movimientos_drop_none_emits_only_required_params` + async mirror lockea   |
| HIGY-07     | 04-02, 04-03          | Empty/204 responses yield `[]` (not crash, not `None`)                                     | ✓ SATISFIED | 3 mocked invariants (get_movimientos, get_posiciones empty path) sync + async; verified live in 3 endpoints                                              |

**REQUIREMENTS.md update needed (informational, not a phase blocker):** REQUIREMENTS.md still shows HIGY-01 and HIGY-04 as `Pending` in the traceability table (lines 116, 119). These statuses are stale — both are SATISFIED per code evidence above. The tracking-file update is a downstream chore (presumably handled by the orchestrator commit step), not a Phase 4 deliverable.

**No orphaned requirements.** Every HIGY-0N is declared in at least one plan's `requirements:` frontmatter.

### Anti-Patterns Found

| File           | Line   | Pattern              | Severity | Impact                                                                                                                                |
| -------------- | ------ | -------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `main_higyrus.py` | 1879   | `XXXXX` literal      | ℹ️ Info  | False positive: `_INVALID_CUENTA_LITERAL = "INVALID-CUENTA-XXXXX"` is a sentinel value for the errors envelope probe, not a debt marker |
| `main_higyrus.py` | 321, 2156 | `TODO` as Spanish word | ℹ️ Info | False positives: "TODO" / "TODOS" in Spanish comments meaning "all" / "every", not debt markers                                       |

No real `TBD`, `FIXME`, or unreferenced debt markers. No stub patterns. No hardcoded empty data in production code paths.

### Code Review Status

Code review (`/gsd-code-review --auto`) converged on 2026-06-08 with status **clean**: 0 Critical, 0 Warning, 3 INFO carryovers (long-term refactor candidates, not blockers):
- IN-01: `client.py` ↔ `aio.py` duplicate logic (known monorepo debt per CLAUDE.md)
- IN-02: `test_request_preserves_literal_slash_in_query` matcher could be more strict
- IN-03: Carryover trace entry from iter-1 (no action — verified clean)

All 4 BLOCKERs + 5 WARNINGs from iter-1, plus 1 regression WARNING (WR-NEW-01) introduced by iter-1 fixes, are RESOLVED.

### Human Verification Required

None. The live driver checkpoint (Plan 04-02 Task 2.3) was completed by the operator on 2026-06-08T02:03:51Z and produced the committed artifacts (5 schemas + findings file) with consistent timestamps. The operator-observed checkpoint is the contract for the live verification; this verifier has no path to re-run against live credentials and does not need to.

The deferred F-02 OPEN (`get_listado_cuentas` returns 0 vs 8771 in pre-phase smoke) is explicitly documented as out-of-scope investigation per 04-02 SUMMARY retrospective and is unblocked by the `HIGYRUS_SAMPLE_CUENTA` override (D-HIGY-11). It is not a phase-blocking gap.

### Gaps Summary

None. All 5 ROADMAP success criteria are verified in code with concrete evidence. All 7 requirements (HIGY-01..07) are SATISFIED. The mocked test suite (51 higyrus-client tests + 232 repo-wide) passes. mypy strict + ruff clean. Live driver artifacts (5 PII-free schemas + 1 classified findings file) committed. All 16 commits cited across the 4 SUMMARYs are present in `git log`.

---

*Verified: 2026-06-08T00:00:00Z*
*Verifier: Claude (gsd-verifier)*
