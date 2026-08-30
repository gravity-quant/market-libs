---
phase: 36
slug: market-data-client-market-data-tipado-revocaci-n-de-la-fase
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-29
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ con pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (raíz del monorepo) |
| **Quick run command** | `uv run pytest packages/market-data-client -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~1 segundo para `market-data-client` (663 tests medidos); workspace completo ~1810 tests |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/market-data-client -q` + `uv run ruff check packages/market-data-client main_market_data.py`
- **After every plan wave:** Run `uv run mypy` (src global) + `uv run mypy packages/market-data-client/tests` + `uv run python tools/check_decode_intactness.py`
- **Before `/gsd-verify-work`:** Full suite must be green — `uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py`, then `uv run pre-commit run --all-files`, then `uv run mypy` + per-package test loop, then `uv run pytest -q`
- **Max feedback latency:** ~1 segundo (quick command)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 0 | NOBJ-MD-01 | — | Cadena `snapshot.market_data.last.price` etc. no lanza con 4 payloads × 2 superficies (SC-1) | unit + integration | `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x` | ❌ W0 | ⬜ pending |
| 36-01-02 | 01 | — | NOBJ-MD-01 | — | Cadena compila bajo mypy strict (SC-1) | static | `uv run mypy packages/market-data-client/src packages/market-data-client/tests` | ✅ | ⬜ pending |
| 36-01-03 | 01 | — | NOBJ-MD-01 | — | `MarketDataEntries`/`BookLevel`/`EntryValue` con forma + 6 alias (SC-2) | unit | `uv run pytest packages/market-data-client/tests/test_models.py -k entries -x` | ✅ (extender) | ⬜ pending |
| 36-01-04 | 01 | — | NOBJ-MD-01 | — | Alias invisibles al walker; roster Null Object `>= 16` → 19 | unit (parametrizado) | `uv run pytest packages/market-data-client/tests/test_null_object.py -x` | ✅ | ⬜ pending |
| 36-02-01 | 02 | — | NOBJ-MD-02 | — | `entries`/`market_data` sin `None` en anotación (SC-2/SC-3) | unit (introspección de hints) | `uv run pytest packages/market-data-client/tests/test_models.py -k field_set -x` | ✅ (extender) | ⬜ pending |
| 36-02-02 | 02 | — | NOBJ-MD-02 | — | `LatestRequest.entries` default `[]`, `to_dict` omite clave vacía | unit | `uv run pytest packages/market-data-client/tests/test_models.py -k latest_request -x` | ✅ | ⬜ pending |
| 36-02-03 | 02 | — | NOBJ-MD-02 | — | Fila no-data: `bool(market_data) is False` + `note` poblado, sync/async, strict/no-strict (SC-4) | integration | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -x` | ✅ (migrar) | ⬜ pending |
| 36-02-04 | 02 | — | NOBJ-MD-02 | — | Wrong-type sigue divergiendo y fatal en strict | integration | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -k wrong_typed -x` | ✅ | ⬜ pending |
| 36-03-01 | 03 | 0 | NOBJ-MD-02 | — | Maquinaria de mapping ausente del paquete, aserción no vacua (SC-5) | unit (introspección negativa + positiva) | `uv run pytest packages/market-data-client/tests/test_models.py -k mapping_machinery -x` | ❌ W0 | ⬜ pending |
| 36-03-02 | 03 | — | NOBJ-MD-02 | — | Hash de `_decode.py` no se movió (SC-5) | gate de CI | `uv run python tools/check_decode_intactness.py` | ✅ | ⬜ pending |
| 36-03-03 | 03 | 0 | NOBJ-MD-02 | — | Driver consume por encadenamiento profundo en sitios reales (SC-5) | AST / grep | planner decide: AST reutilizando precedente 30-09, o assertion en el plan | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/market-data-client/tests/test_market_data_chain.py` — matriz de 4 payloads × 2 superficies de SC-1 (wire real de `get-market-data.json`, `market_data` ausente, `market_data: null`, `market_data: {}`); por caso: cadena no lanza, set de divergencias, `bool(market_data)`. Valores esperados medidos — ver RESEARCH.md F-1.
- [ ] `test_models.py -k mapping_machinery` — aserción de ausencia de maquinaria de mapping, emparejada con una aserción positiva (p. ej. `from_api` sigue inyectando `received_at`, roster `SafeModel` sigue en 19) para evitar un verde vacuo.
- [ ] Lock AST del driver para SC-5 (encadenamiento profundo en `main_market_data.py`) — reutilizar precedente 30-09 si el planner opta por AST.
- [ ] Helper `_strip_optional` módulo-local en `test_core.py` y `test_decode.py` (3 sitios) — prerequisito de las ediciones del censo de tests, no test propio.

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
