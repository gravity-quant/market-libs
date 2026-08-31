---
phase: 35
slug: fundaci-n-null-object-bool-pol-tica-del-walker
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-28
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3 (+pytest-asyncio, pytest-httpx) |
| **Config file** | `pyproject.toml` (root) |
| **Quick run command** | `uv run pytest packages/<pkg>/tests/test_decode.py -q` (per touched package) |
| **Full suite command** | `uv run pytest packages/ -q` (NEVER bare `pytest` — `verification/` hangs >10 min and is red at baseline per HARN-VERIF-01) |
| **Estimated runtime** | ~95 seconds (full packages/ suite: 1749 tests measured) |

---

## Sampling Rate

- **After every task commit:** Run the touched package's `tests/test_decode.py` + `tests/test_models.py`
- **After every plan wave:** Run `uv run pytest packages/ -q` + the 4 gates (`check_decode_intactness.py`, `check_uniform_structure.py`, `check_surface_types.py`, per-package `test_surface_parity.py`)
- **Before `/gsd-verify-work`:** Full suite green + `uv run mypy` clean + `git diff` empty on `verification/snapshots/`
- **Max feedback latency:** ~100 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | NOBJ-01 / NOBJ-02 | — | N/A | unit | see plans | — | ⬜ superada por las 12 filas reconstruidas de abajo — ver `## Validation Audit 2026-08-31` |
| 35-01-01 | 01 | 1 | NOBJ-01 / NOBJ-02 | — | N/A | unit (RED fixture) | `uv run pytest packages/higyrus-client/tests/test_null_object.py -q -k "not_vacuous or invisible_to_get_type_hints or does_not_change_the_divergence_count" && ! uv run pytest packages/higyrus-client/tests/test_null_object.py -q -k "falsy_when_empty or truthy_when_populated or empty_emits_nothing"` | ✅ | ⬜ pending |
| 35-01-02 | 01 | 1 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/higyrus-client -q && uv run mypy packages/higyrus-client/src && uv run ruff check packages/higyrus-client && uv run ruff format --check packages/higyrus-client` | ✅ | ⬜ pending |
| 35-01-03 | 01 | 1 | NOBJ-01 / NOBJ-02 | — | N/A | unit | `uv run pytest packages/higyrus-client/tests/test_decode.py -q -k "wrong_typed_list or still_raises_on_a_wrong_typed_list" && uv run pytest packages/higyrus-client -q` | ✅ | ⬜ pending |
| 35-02-01 | 02 | 1 | NOBJ-02 | — | N/A | static | `test -f .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md && test "$(grep -c '^\| ' .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md)" -ge 35` | ✅ | ⬜ pending |
| 35-02-02 | 02 | 1 | NOBJ-02 | — | N/A | static | `grep -q "iol-client" .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md && grep -q "wallets-client" .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md && grep -qi "phase 39" .planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md` | ✅ | ⬜ pending |
| 35-03-01 | 03 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/iol-client -q && uv run mypy packages/iol-client/src && uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` | ✅ | ⬜ pending |
| 35-03-02 | 03 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/market-data-client -q && uv run mypy packages/market-data-client/src && uv run ruff check packages/market-data-client && uv run ruff format --check packages/market-data-client` | ✅ | ⬜ pending |
| 35-04-01 | 04 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/matriz-client -q && uv run mypy packages/matriz-client/src && uv run ruff check packages/matriz-client && uv run ruff format --check packages/matriz-client` | ✅ | ⬜ pending |
| 35-04-02 | 04 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/ambito-financiero-client -q && uv run mypy packages/ambito-financiero-client/src && uv run ruff check packages/ambito-financiero-client && uv run ruff format --check packages/ambito-financiero-client` | ✅ | ⬜ pending |
| 35-04-03 | 04 | 2 | NOBJ-01 / NOBJ-02 | — | N/A | unit + static | `uv run pytest packages/wallets-client -q && uv run ruff check packages/wallets-client && uv run ruff format --check packages/wallets-client` | ✅ | ⬜ pending |
| 35-05-01 | 05 | 3 | NOBJ-02 | — | N/A | unit + static | `uv run python tools/check_decode_intactness.py && uv run pytest packages -q && uv run ruff check packages/ && uv run ruff format --check packages/ && uv run mypy && uv run mypy packages/market-data-client/src` | ✅ | ⬜ pending |
| 35-05-02 | 05 | 3 | NOBJ-02 | — | N/A | unit + static + snapshot | `uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py && uv run python tools/surface_parity.py && uv run pytest packages -q && uv run pytest tests -q && uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/ && git diff --exit-code pyproject.toml uv.lock` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Nota de reconstrucción (auditoría 2026-08-31, Phase 41 / NYQ-01).** El mapa shipeó con una única
> fila placeholder. Las 12 filas de arriba se reconstruyeron desde los bloques `<verify><automated>`
> de `35-01..05-PLAN.md` (3 + 2 + 2 + 3 + 2 = 12, medido con `grep -c '<automated>'`), en el orden de
> los planes. La fila placeholder se **conserva** como evidencia de que la fase shipeó con el mapa sin
> llenar. Los comandos están transcritos **literales** de su plan de origen, sin corregir: las
> correcciones de ruta se documentan en `### Correcciones de comando` de la sección de auditoría, no
> reescribiendo el comando histórico. (El `\|` de la fila `35-02-01` es sólo el escape de markdown
> para el pipe literal del `grep -c '^| '` original.)

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — pytest + the 4 v1.6 gates already run in CI; new tests slot into existing `tests/test_decode.py` / `tests/test_models.py` per package.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Snapshot byte-identity | NOBJ-02 (criterio 4) | `verification/` never runs in CI | `git diff --exit-code verification/snapshots/` after regen |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
