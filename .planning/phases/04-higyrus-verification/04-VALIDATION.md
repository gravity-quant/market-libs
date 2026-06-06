---
phase: 4
slug: higyrus-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
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
| 04-01-01 | 01 | 1 | HIGY-04 | T-4-08 | sync `get_health` raises `HigyrusAPIError(0)` on non-dict payload | unit (regression) | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_health_raises_on_list_payload` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | HIGY-04 | T-4-08 | sync `get_movimientos`/`get_listado_cuentas`/`get_posiciones`/`get_posicion_valuada` raise on dict-when-list-expected (and vice versa) | unit (regression) | `uv run pytest -q packages/higyrus-client/tests/test_client.py -k raises_on_` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | HIGY-04 | T-4-08 | async surface mirrors 5 regressions in `test_async_client.py` | unit (regression) | `uv run pytest -q packages/higyrus-client/tests/test_async_client.py -k raises_on_` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | HIGY-04 | — | `HigyrusAPIError.status_code` docstring documents the `0` sentinel for client-side shape mismatch | source assertion | `grep -q 'status_code=0' packages/higyrus-client/src/higyrus_client/exceptions.py` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | HIGY-01 | T-3-04 / T-4-01 | live `login()` upfront on both surfaces; cascade SKIPPED on failure | live driver invariant | manual: `uv run --package higyrus-client python main_higyrus.py` PROBE 1+2 PASS or all downstream SKIPPED | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | HIGY-02 | T-3-09 / T-4-02 | 5 happy-path probes (`get_health`, `get_listado_cuentas`, `get_movimientos`, `get_posicion_valuada`, `get_posiciones`) PASS sync+async with stdout = counts + shape only (no values) | live driver invariant | manual: PROBE happy_*_sync/async PASS | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | HIGY-03 | T-4-03 / T-4-SC | `_diff_safemodel_bidirectional` recursive walk emits zero `model \ wire` findings OR all emissions are OPEN with classifier=`SHAPE` | live driver invariant | manual: PROBE field_type_map PASS or FINDING (OPEN) | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 2 | HIGY-06 | T-4-05 | live param capture for sync vs async `get_movimientos` (and 1 more) yields identical `httpx.URL.query` strings — confirms or denies `drop_none` deviation | live driver invariant | manual: PROBE parity_sync_async PASS or FINDING SYNC-ASYNC-DRIFT (OPEN) | ❌ W0 | ⬜ pending |
| 04-02-05 | 02 | 2 | HIGY-05 | T-3-13 / T-4-06 | live `probe_errors_envelope` (invalid id_cuenta) returns `HigyrusAPIError` with populated `errors=[{title, detail}]` | live driver invariant | manual: PROBE errors_envelope_*_sync/async PASS | ❌ W0 | ⬜ pending |
| 04-02-06 | 02 | 2 | HIGY-07 | T-4-04 | empty `[]` payload (or 204) yields empty list (no None, no crash) — verified live in any of the 3 list endpoints | live driver invariant | manual: PROBE happy_* PASS with detail `(0 items — empty path verified)` | ❌ W0 | ⬜ pending |
| 04-02-07 | 02 | 2 | HIGY-AUTH | T-3-04 / T-4-07 | opt-in `probe_auth_401` (single-shot, no retry) when `VERIFY_HIGYRUS_BAD_CREDS=1` returns 401 and `try/finally` restores real password | live driver invariant | manual: `VERIFY_HIGYRUS_BAD_CREDS=1 uv run --package higyrus-client python main_higyrus.py` PROBE auth_401 PASS | ❌ W0 | ⬜ pending |
| 04-02-08 | 02 | 2 | DRIFT-01 | T-4-SC | 5 schema snapshots written to `.planning/verification/schemas/higyrus-client/<endpoint>.json` with envelope D-21 and no-overwrite-on-drift D-25 | source assertion | `test $(ls .planning/verification/schemas/higyrus-client/*.json \| wc -l) -eq 5` | ❌ W0 | ⬜ pending |
| 04-02-09 | 02 | 2 | (driver) | T-3-10 / T-3-14 / T-4-01 | `safe_print(text, secrets=[HIGYRUS_USER, HIGYRUS_PASSWORD, _token])` invoked from every stdout line; bearer regex covers reflected tokens | source assertion | `grep -q 'safe_print' main_higyrus.py && grep -q '_BEARER\|secrets=\[' main_higyrus.py` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | HIGY-02 | T-3-09 | mocked Verified-live lock: full URL + query string for the 3 endpoints with gaps (`get_health`, `get_listado_cuentas`, `get_posicion_valuada`) | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_verified_live_url_<endpoint>` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | HIGY-03 | T-4-03 | mocked: `Cuenta.from_api({})` returns model with all-typed-defaults; idem for `Movimiento`, `Posicion`, `PosicionValuada` | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_safemodel_partial_payload_typed_defaults` | ❌ W0 | ⬜ pending |
| 04-03-03 | 03 | 3 | HIGY-05 | T-3-13 | mocked: 400 response with `{timestamp, errors:[{title,detail}]}` envelope → `HigyrusAPIError(status_code, errors, timestamp)` populated | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_errors_envelope_parsed` | ✅ existing test_client.py:38 (extend coverage to 4xx on any endpoint, not just login) |
| 04-03-04 | 03 | 3 | HIGY-06 | T-4-05 | mocked: sync vs async `drop_none(params)` for `get_movimientos` emit identical `httpx.URL.params` query strings | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_movimientos_drop_none_emits_only_two_params` + async mirror | ❌ W0 | ⬜ pending |
| 04-03-05 | 03 | 3 | HIGY-07 | T-4-04 | mocked: 204 (no body) and `[]` returns `[]` (not `None`, not crash) for the 3 list endpoints | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py -k 204_devuelve_lista_vacia` | ✅ partial (existing `test_get_listado_cuentas_204_devuelve_lista_vacia`); extend to `get_movimientos`, `get_posiciones` |
| 04-03-06 | 03 | 3 | (commit) | T-3-09 | commit baseline: 5 schema snapshots + `higyrus-client-findings.md` (PII-free by construction) + appended `.env.example` rows | source assertion | `git diff --stat HEAD~1..HEAD \| grep -E 'verification/schemas/higyrus-client/.*\.json\|higyrus-client-findings.md\|\.env\.example'` | ❌ W0 | ⬜ pending |
| 04-03-07 | 03 | 3 | (gate) | — | full suite green + ruff format check + mypy strict pass | unit | `uv run pytest -q && uv run mypy && uv run ruff check && uv run ruff format --check` | partial — re-runs after appends | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

The following files/sections do not exist yet and must be created in the appropriate plan before sampling becomes meaningful:

- [ ] `packages/higyrus-client/tests/test_client.py` — append `# ------ Regressions ------` section with 5 HIGY-04 sync regression tests (Plan 1)
- [ ] `packages/higyrus-client/tests/test_async_client.py` — append `# ------ Regressions ------` section with 5 HIGY-04 async regression tests (Plan 1)
- [ ] `packages/higyrus-client/tests/test_client.py` — append `# ------ Verified live (Phase 4) ------` section with HIGY-02/03/05/06/07 unit invariants (Plan 3)
- [ ] `packages/higyrus-client/tests/test_async_client.py` — append `# ------ Verified live (Phase 4) ------` section, async mirror (Plan 3)
- [ ] `main_higyrus.py` — full rewrite per D-HIGY-10 with 18 named probes (Plan 2)
- [ ] `.planning/verification/schemas/higyrus-client/{get-health,get-listado-cuentas,get-movimientos,get-posicion-valuada,get-posiciones}.json` — 5 snapshots generated by Plan 2 live run, committed in Plan 3
- [ ] `.planning/verification/higyrus-client-findings.md` — generated by Plan 2 live run, committed in Plan 3
- [ ] `packages/higyrus-client/.env.example` — append optional rows per D-HIGY-14 (`HIGYRUS_SAMPLE_CUENTA`, `HIGYRUS_SAMPLE_TIPO_CUENTA`, `HIGYRUS_SAMPLE_NIVEL`, `VERIFY_HIGYRUS_BAD_CREDS`) (Plan 2)

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (mapped above)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (live driver invariants count as the per-plan sample, not the per-task sample — the 10 HIGY-04 regressions in Plan 1 give per-task automated coverage for Wave 1; Plan 3's appended unit tests give per-task automated coverage for Wave 3)
- [ ] Wave 0 covers all ❌ W0 references above (10 file/section gaps)
- [ ] No watch-mode flags (`pytest -q` only; `pytest --watch` explicitly excluded)
- [ ] Feedback latency < 30 s (quick) / 180 s (full)
- [ ] `nyquist_compliant: true` set in frontmatter once Wave 0 is complete and the per-task verify map is populated by the planner

**Approval:** pending
