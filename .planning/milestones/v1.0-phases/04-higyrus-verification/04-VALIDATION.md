---
phase: 4
slug: higyrus-verification
status: closed
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-06
audited: 2026-06-10
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Synthesized from `04-RESEARCH.md` §Validation Architecture (Dimension 8).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ + pytest-httpx 0.34+ + pytest-asyncio 0.24+ + pytest-cov 6.0+ |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, `--strict-markers`, `--import-mode=importlib`) |
| **Quick run command** | `uv run pytest -q packages/higyrus-client/tests` |
| **Full suite command** | `uv run pytest -q && uv run mypy && uv run ruff check && uv run ruff format --check` |
| **Estimated runtime** | ~30 s (quick) / ~2-3 min (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q packages/higyrus-client/tests`
- **After every plan wave:** Run `uv run pytest -q && uv run mypy && uv run ruff check && uv run ruff format --check`
- **Before `/gsd-verify-work`:** Full suite must be green AND live driver run must have been operator-observed (PROBE summary captured in `.planning/verification/higyrus-client-findings.md`).
- **Max feedback latency:** 30 seconds (quick), 180 seconds (full)

---

## Per-Task Verification Map

> Plan/task IDs assigned to the 3-plan horizontal layout from `04-RESEARCH.md` §MVP Slice Composition.
> `04-01` = HIGY-04 fix + 10 regression tests; `04-02` = driver rewrite + live run; `04-03` = Verified-live tests + commit baseline.
> Threat refs cross-reference Phase 3 inherited mitigations (T-3-NN) and Phase 4 net-new threats (T-4-NN) catalogued in `04-RESEARCH.md` §Security Domain.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | HIGY-04 | T-4-08 | sync `get_health` raises `HigyrusAPIError(0)` on non-dict payload | unit (regression) | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_health_raises_on_list_payload` | ✅ exists | ✅ green |
| 04-01-02 | 01 | 1 | HIGY-04 | T-4-08 | sync `get_movimientos`/`get_listado_cuentas`/`get_posiciones`/`get_posicion_valuada` raise on dict-when-list-expected (and vice versa) | unit (regression) | `uv run pytest -q packages/higyrus-client/tests/test_client.py -k raises_on_` | ✅ exists | ✅ green (5 passed) |
| 04-01-03 | 01 | 1 | HIGY-04 | T-4-08 | async surface mirrors 5 regressions in `test_async_client.py` | unit (regression) | `uv run pytest -q packages/higyrus-client/tests/test_async_client.py -k raises_on_` | ✅ exists | ✅ green (5 passed) |
| 04-01-04 | 01 | 1 | HIGY-04 | — | `HigyrusAPIError.status_code` docstring documents the `0` sentinel for client-side shape mismatch | source assertion | `grep -q "o 0 si el error fue detectado" packages/higyrus-client/src/higyrus_client/exceptions.py` (corrected from `status_code=0` literal — actual D-HIGY-8 sentinel uses Spanish prose) | ✅ exists | ✅ green |
| 04-02-01 | 02 | 2 | HIGY-01 | T-3-04 / T-4-01 | live `login()` upfront on both surfaces; cascade SKIPPED on failure | live driver invariant | `uv run --package higyrus-client python main_higyrus.py` PROBE 1+2 PASS or all downstream SKIPPED | ✅ exists | Manual-Only ✅ verified (04-02 SUMMARY: probe_login_sync/async PASS at 2026-06-08T02:03:51Z; D-05 — not in pytest CI) |
| 04-02-02 | 02 | 2 | HIGY-02 | T-3-09 / T-4-02 | 5 happy-path probes (`get_health`, `get_listado_cuentas`, `get_movimientos`, `get_posicion_valuada`, `get_posiciones`) PASS sync+async with stdout = counts + shape only (no values) | live driver invariant | `uv run --package higyrus-client python main_higyrus.py` PROBE happy_*_sync/async PASS | ✅ exists | Manual-Only ✅ verified (04-02 SUMMARY: 10 endpoint probes PASS; D-05) |
| 04-02-03 | 02 | 2 | HIGY-03 | T-4-03 / T-4-SC | `_diff_safemodel_bidirectional` recursive walk emits zero `model \ wire` findings OR all emissions are OPEN with classifier=`SHAPE` | live driver invariant | `uv run --package higyrus-client python main_higyrus.py` PROBE field_type_map PASS or FINDING (OPEN) | ✅ exists | Manual-Only ✅ verified (04-02 SUMMARY: F-01 EXPECTED Posicion.disponibleAjustado FCI-conditional; D-05) |
| 04-02-04 | 02 | 2 | HIGY-06 | T-4-05 | live param capture for sync vs async `get_movimientos` (and 1 more) yields identical `httpx.URL.query` strings — confirms or denies `drop_none` deviation | live driver invariant | `uv run --package higyrus-client python main_higyrus.py` PROBE parity_sync_async PASS or FINDING SYNC-ASYNC-DRIFT (OPEN) | ✅ exists | Manual-Only ✅ verified (04-02 SUMMARY: parity_sync_async PASS, query=`fechaDesde=08/05/2026&fechaHasta=07/06/2026`; D-05) |
| 04-02-05 | 02 | 2 | HIGY-05 | T-3-13 / T-4-06 | live `probe_errors_envelope` (invalid id_cuenta) returns `HigyrusAPIError` with populated `errors=[{title, detail}]` | live driver invariant | `uv run --package higyrus-client python main_higyrus.py` PROBE errors_envelope_*_sync/async PASS | ✅ exists | Manual-Only ✅ verified (04-02 SUMMARY: errors_envelope_sync/async PASS; D-05) |
| 04-02-06 | 02 | 2 | HIGY-07 | T-4-04 | empty `[]` payload (or 204) yields empty list (no None, no crash) — verified live in any of the 3 list endpoints | live driver invariant | `uv run --package higyrus-client python main_higyrus.py` PROBE happy_* PASS with detail `(0 items — empty path verified)` | ✅ exists | Manual-Only ✅ verified (04-02 SUMMARY: get_listado_cuentas returned 0 items with empty path traversed; F-02 NO-DATA OPEN documented; D-05) |
| 04-02-07 | 02 | 2 | HIGY-AUTH | T-3-04 / T-4-07 | opt-in `probe_auth_401` (single-shot, no retry) when `VERIFY_HIGYRUS_BAD_CREDS=1` returns 401 and `try/finally` restores real password | live driver invariant | `VERIFY_HIGYRUS_BAD_CREDS=1 uv run --package higyrus-client python main_higyrus.py` PROBE auth_401 PASS | ✅ exists | Manual-Only (opt-in gate not exercised in 04-02 final run — SKIPPED status documented; probe code present in main_higyrus.py and try/finally restore wired; D-05) |
| 04-02-08 | 02 | 2 | DRIFT-01 | T-4-SC | 5 schema snapshots written to `.planning/verification/schemas/higyrus-client/<endpoint>.json` with envelope D-21 and no-overwrite-on-drift D-25 | source assertion | `test $(ls .planning/verification/schemas/higyrus-client/*.json \| wc -l) -eq 5` | ✅ 5 files | ✅ green (5 schemas committed in 20afad5, envelope D-21 6-key verified) |
| 04-02-09 | 02 | 2 | (driver) | T-3-10 / T-3-14 / T-4-01 | `safe_print(text, secrets=[HIGYRUS_USER, HIGYRUS_PASSWORD, _token])` invoked from every stdout line; bearer regex covers reflected tokens | source assertion | `grep -q 'safe_print' main_higyrus.py && grep -q 'secrets=\[' main_higyrus.py` | ✅ exists | ✅ green (`safe_print` invoked 4×; `secrets=[HIGYRUS_USER, HIGYRUS_PASSWORD, _sync_token_snapshot, _async_token_snapshot]` present) |
| 04-03-01 | 03 | 3 | HIGY-02 | T-3-09 | mocked Verified-live lock: full URL + query string for `get_listado_cuentas` (`?estado=alta`) and HIGY-06 `get_movimientos` query | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_listado_cuentas_url_con_estado_alta` (corrected from `test_verified_live_url_<endpoint>` placeholder) | ✅ exists | ✅ green |
| 04-03-02 | 03 | 3 | HIGY-03 | T-4-03 | mocked: `Cuenta.from_api({})` returns model with all-typed-defaults; idem for `Movimiento`, `Posicion`, `PosicionValuada` | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_safemodel_from_api_typed_defaults` (corrected from `test_safemodel_partial_payload_typed_defaults` placeholder) | ✅ exists | ✅ green |
| 04-03-03 | 03 | 3 | HIGY-05 | T-3-13 | mocked: 400 response with `{timestamp, errors:[{title,detail}]}` envelope → `HigyrusAPIError(status_code, errors, timestamp)` populated | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_errors_envelope_parsed_on_4xx` (corrected from `test_errors_envelope_parsed`) | ✅ exists | ✅ green (extended beyond pre-existing login-only coverage per VALIDATION note) |
| 04-03-04 | 03 | 3 | HIGY-06 | T-4-05 | mocked: sync vs async `drop_none(params)` for `get_movimientos` emit identical `httpx.URL.params` query strings | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_movimientos_drop_none_emits_only_required_params` + async mirror (corrected from `_emits_only_two_params` placeholder) | ✅ exists | ✅ green (sync + async both pass) |
| 04-03-05 | 03 | 3 | HIGY-07 | T-4-04 | mocked: 204 (no body) and `[]` returns `[]` (not `None`, not crash) for the 3 list endpoints | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py -k "empty_path_returns_list or 204_devuelve_lista_vacia"` (extended per VALIDATION note: now covers `get_movimientos`, `get_posiciones` in addition to pre-existing `get_listado_cuentas`) | ✅ exists | ✅ green (3 tests pass) |
| 04-03-06 | 03 | 3 | (commit) | T-3-09 | commit baseline: 5 schema snapshots + `higyrus-client-findings.md` (PII-free by construction) + appended `.env.example` rows | source assertion | `git ls-files .planning/verification/schemas/higyrus-client/ .planning/verification/higyrus-client-findings.md` (retroactive: original `git diff HEAD~1..HEAD` is time-bounded — replaced with files-tracked check since baseline was committed in `20afad5` and HEAD has advanced) | ✅ exists | ✅ green (6 files tracked in git: 5 schemas + findings.md) |
| 04-03-07 | 03 | 3 | (gate) | — | full suite green + ruff format check + mypy strict pass | unit | `uv run pytest -q && uv run mypy packages/higyrus-client verification && uv run ruff check . && uv run ruff format --check .` | ✅ green | ✅ green (277 passed; mypy clean in 19 source files; ruff check + format clean) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All Wave 0 dependencies have been created and committed (verified 2026-06-10):

- [x] `packages/higyrus-client/tests/test_client.py` — `# ------ Regressions ------` section with 5 HIGY-04 sync regression tests (Plan 1, commit `b71a0a3`)
- [x] `packages/higyrus-client/tests/test_async_client.py` — `# ------ Regressions ------` section with 5 HIGY-04 async regression tests (Plan 1, commit `b71a0a3`)
- [x] `packages/higyrus-client/tests/test_client.py` — `# ------ Verified live (Phase 4) ------` section with HIGY-02/03/05/06/07 unit invariants (Plan 3, commit `9d87347`)
- [x] `packages/higyrus-client/tests/test_async_client.py` — `# ------ Verified live (Phase 4) ------` section, async mirror (Plan 3, commit `9d87347`)
- [x] `main_higyrus.py` — full rewrite per D-HIGY-10 with 18 named probes (Plan 2, commit `cd68e01`)
- [x] `.planning/verification/schemas/higyrus-client/{get-health,get-listado-cuentas,get-movimientos,get-posicion-valuada,get-posiciones}.json` — 5 snapshots committed in `20afad5`
- [x] `.planning/verification/higyrus-client-findings.md` — committed in `20afad5`
- [x] `packages/higyrus-client/.env.example` — optional rows per D-HIGY-14 (`HIGYRUS_SAMPLE_CUENTA`, `HIGYRUS_SAMPLE_TIPO_CUENTA`, `HIGYRUS_SAMPLE_NIVEL`, `VERIFY_HIGYRUS_BAD_CREDS`) (Plan 2, commit `4fef970`)

*Note:* No framework install required. The autouse fixtures in `packages/higyrus-client/tests/conftest.py` (which precharge `_token`) work as-is for the new tests; no harness modification.

---

## Manual-Only Verifications

The verification cycle is intentionally live-driver-led; the live invariants below are the load-bearing signal of the phase and cannot be replaced by mocks.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live `login()` returns Bearer token from real Higyrus and lazy-auth caches it | HIGY-01 | The `login()` flow exercises the real `POST /api/login` against Higyrus' production-or-staging; the token format and TTL behavior cannot be mocked without re-implementing the API contract. | Set `HIGYRUS_USER`, `HIGYRUS_PASSWORD`, `HIGYRUS_BASE_URL` in `.env`; run `uv run --package higyrus-client python main_higyrus.py`; confirm PROBE 1+2 PASS with stdout `PROBE probe_login_sync: PASS` and `PROBE probe_login_async: PASS`. |
| Bidirectional diff finds zero `model \ wire` keys (or only documented OPEN findings) | HIGY-03 | The shape of the wire is what we are validating; mocking the diff target defeats the purpose. | Same driver run; confirm `PROBE field_type_map: PASS` or `PROBE field_type_map: FINDING F-NN (OPEN)` with each finding classified `SHAPE`. |
| sync↔async parity confirms or denies the `drop_none` deviation | HIGY-06 | The deviation is suspected at the live HTTP layer; the only sound check is to capture `httpx.URL.query` on both surfaces and compare. | Same driver run; confirm `PROBE parity_sync_async: PASS` or `FINDING SYNC-ASYNC-DRIFT F-NN (OPEN)`. |
| Errors envelope is preserved when the real Higyrus returns 4xx | HIGY-05 | The envelope format (`{timestamp, errors:[{title, detail}]}`) is what the client must parse; a mock cannot exercise the real envelope nuances. | Same driver run; confirm PROBE errors_envelope_*_sync/async PASS with `e.errors[0]` having `"title"` and `"detail"` keys. |
| Empty/204 path returns `[]` (not `None`, not crash) in live | HIGY-07 | Confirms the live wire behavior matches the cached test invariant; live 204 is hard to provoke (depends on operator data). | Same driver run; if `cuentas[0]` has 0 movimientos in the 30-day window, PROBE prints `(0 items — empty path verified)`. |
| Opt-in 401 single-shot leaves no token/credential corruption | HIGY-AUTH | The single-shot test deliberately corrupts the password and restores it; only the operator can authorize this gated run. | `VERIFY_HIGYRUS_BAD_CREDS=1 uv run --package higyrus-client python main_higyrus.py`; confirm PROBE auth_401 PASS and immediate next session passes login normally. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (mapped above)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (live driver invariants count as the per-plan sample, not the per-task sample — the 10 HIGY-04 regressions in Plan 1 give per-task automated coverage for Wave 1; Plan 3's appended unit tests give per-task automated coverage for Wave 3)
- [x] Wave 0 covers all ❌ W0 references above (10 file/section gaps) — now all ✅
- [x] No watch-mode flags (`pytest -q` only; `pytest --watch` explicitly excluded)
- [x] Feedback latency < 30 s (quick) / 180 s (full) — measured 0.55s for full repo suite (277 tests)
- [x] `nyquist_compliant: true` set in frontmatter once Wave 0 is complete and the per-task verify map is populated by the planner

**Approval:** ✅ approved 2026-06-10 (retroactive close-out audit; phase closed via milestone v1.0 audit `a72c0e0`)

---

## Audit Trail

### 2026-06-10 — Retroactive close-out audit

**Auditor stance:** FORCE — every row treated as unverified until commands re-ran green.

**Gaps presented:** 19 rows in the Per-Task Verification Map were marked `⬜ pending` with the `❌ W0` File-Exists annotation despite the phase being closed (VERIFICATION.md status=passed, score=5/5) and the milestone v1.0 audit recording 35/35 requirements satisfied.

**Resolved:** 19/19

**Breakdown by status:**

| Status | Count | Rows |
|--------|-------|------|
| ✅ green (re-verified pytest/grep this audit) | 11 | 04-01-01, 04-01-02, 04-01-03, 04-01-04, 04-02-08, 04-02-09, 04-03-01, 04-03-02, 04-03-03, 04-03-04, 04-03-05, 04-03-06, 04-03-07 (13 actually) |
| Manual-Only ✅ verified (live-driver, operator-observed per 04-02 SUMMARY) | 6 | 04-02-01, 04-02-02, 04-02-03, 04-02-04, 04-02-05, 04-02-06 |
| Manual-Only (opt-in, code wired but flag not exercised) | 1 | 04-02-07 (HIGY-AUTH 401 — opt-in via `VERIFY_HIGYRUS_BAD_CREDS=1`, SKIPPED in 04-02 final run by design) |

**Escalated:** 0 (no implementation bugs found)

**Corrections to original `automated_command` placeholders applied during audit (test names existed in source under different names than the original VALIDATION.md draft anticipated; replacements are minimal-edit re-aliases, not weakened assertions):**

1. `04-01-04` — original `grep -q 'status_code=0' exceptions.py` was the wrong literal. D-HIGY-8 sentinel is documented as Spanish prose `o 0 si el error fue detectado client-side ...`. Corrected to `grep -q "o 0 si el error fue detectado"`. The docstring is present and verifies; the original literal `status_code=0` only appears at the `__init__` arg site, not in the docstring narrative.
2. `04-03-01` — placeholder `test_verified_live_url_<endpoint>` replaced with actual name `test_get_listado_cuentas_url_con_estado_alta`.
3. `04-03-02` — placeholder `test_safemodel_partial_payload_typed_defaults` replaced with actual `test_safemodel_from_api_typed_defaults`.
4. `04-03-03` — placeholder `test_errors_envelope_parsed` replaced with actual `test_errors_envelope_parsed_on_4xx`.
5. `04-03-04` — placeholder `_emits_only_two_params` replaced with actual `_emits_only_required_params` (sync) + async mirror.
6. `04-03-05` — `-k 204_devuelve_lista_vacia` extended to `-k "empty_path_returns_list or 204_devuelve_lista_vacia"` to cover the additional `get_movimientos` + `get_posiciones` extensions (per the original VALIDATION note that mandated the extension).
7. `04-03-06` — original `git diff --stat HEAD~1..HEAD ...` is time-bounded and no longer valid since the baseline commit `20afad5` is 20+ commits in the past. Replaced with retroactive equivalent `git ls-files .planning/verification/schemas/higyrus-client/ .planning/verification/higyrus-client-findings.md` (verifies the same artifacts are tracked).

**Test-run evidence captured during audit:**

| Check | Command | Result |
|-------|---------|--------|
| higyrus-client suite | `uv run pytest packages/higyrus-client -q` | 51 passed |
| Full repo suite | `uv run pytest -q` | 277 passed, 1 deselected |
| mypy strict | `uv run mypy packages/higyrus-client verification` | Success: no issues found in 19 source files |
| ruff check | `uv run ruff check .` | All checks passed |
| ruff format | `uv run ruff format --check .` | 71 files already formatted |
| Schema count | `ls .planning/verification/schemas/higyrus-client/*.json \| wc -l` | 5 |
| Schemas tracked in git | `git ls-files .planning/verification/schemas/higyrus-client/` | 5 files tracked |
| Findings tracked in git | `git ls-files .planning/verification/higyrus-client-findings.md` | 1 file tracked |
| Driver probe code present | inspect `main_higyrus.py` for 18 named probes, `_diff_safemodel_bidirectional`, `_capture_*_query_string`, `_auth_failed`, `_resolved_cuenta` | All present (per 04-VERIFICATION.md row-by-row) |

**Live-driver rows (Manual-Only) — verification provenance:** The 04-02 SUMMARY documents the operator-observed checkpoint on 2026-06-08T02:03:51Z with `SUMMARY: PASS=16 FAIL=0 SKIPPED=1 FINDING=1`. The 5 committed schemas carry consistent `captured_at` timestamps corroborating that run. The Manual-Only classification follows D-05 (live-driver invariants are not part of the pytest CI suite — they are operator-run only).

**Frontmatter mutation:** `wave_0_complete: false → true`, `nyquist_compliant: false → true`, `status: draft → closed`, `audited: 2026-06-10` added.

**No red rows. No escalations. Audit closes Phase 4 VALIDATION.md in alignment with the closed phase state recorded in 04-VERIFICATION.md and the milestone v1.0 audit.**
