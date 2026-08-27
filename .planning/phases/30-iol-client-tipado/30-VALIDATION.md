---
phase: 30
slug: iol-client-tipado
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-19
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (pytest-asyncio auto, pytest-httpx) |
| **Config file** | `pyproject.toml` (root — `[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest packages/iol-client/tests/ -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30 seconds (package) / ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/iol-client/tests/ -q`
- **After every plan wave:** Run `uv run pytest -q` + `uv run mypy packages/iol-client/src packages/iol-client/tests` + `uv run ruff check .`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 30-01-T1 | 30-01 | 1 | TYP-01 | T-30-01, T-30-SC | `models.py` no abre canal de salida propio (allowlist de imports por AST); registros tipo-y-ruta | unit + typecheck | `uv run pytest packages/iol-client/tests/test_models.py -q` | ❌ Wave 0 | ⬜ pending |
| 30-01-T2 | 30-01 | 1 | TYP-01 | T-30-03 | `_decode.py` intacto; sin modo estricto | unit + typecheck | `uv run pytest packages/iol-client -q && uv run mypy packages/iol-client/src packages/iol-client/tests` | ✅ | ⬜ pending |
| 30-01-T3 | 30-01 | 1 | TYP-01 | T-30-04 | fixture RED no-vacua en ambas direcciones | static + unit | `uv run pytest packages/iol-client/tests/test_typed_surface_red.py -q && uv run mypy packages/iol-client/tests` | ❌ Wave 0 | ⬜ pending |
| 30-02-T1 | 30-02 | 2 | TYP-01 | T-30-01 | sin overrides de `from_api`; sin canal de salida nuevo | unit | `uv run pytest packages/iol-client/tests/test_models.py -q` | ✅ (tras 30-01) | ⬜ pending |
| 30-02-T2 | 30-02 | 2 | TYP-01 | T-30-06, T-30-07 | guard de forma **levanta**; dedupe por scope per-response | unit | `uv run pytest packages/iol-client/tests/test_core.py -q && uv run lint-imports` | ✅ | ⬜ pending |
| 30-02-T3 | 30-02 | 2 | TYP-01 | — | aserciones migradas sin perder fuerza | unit | `uv run pytest packages/iol-client -q -p no:randomly` | ✅ | ⬜ pending |
| 30-03-T1 | 30-03 | 3 | TYP-01 | T-30-01 | modelo sin canal de salida; `__all__` ordenado | unit | `uv run pytest packages/iol-client/tests/test_models.py -q` | ✅ | ⬜ pending |
| 30-03-T2 | 30-03 | 3 | TYP-01 | T-30-09, T-30-05 | mocks alineados al schema vivo; centinelas intactos | unit | `uv run pytest packages/iol-client -q` | ✅ | ⬜ pending |
| 30-03-T3 | 30-03 | 3 | TYP-01 | T-30-08 | no-lista levanta, lista vacía no; 16/16 firmas por introspección | unit + typecheck | `uv run pytest packages/iol-client -q && uv run mypy packages/iol-client/src packages/iol-client/tests` | ✅ | ⬜ pending |
| 30-04-T1 | 30-04 | 4 | TYP-01 | T-30-10, T-30-11 | probes **no-vacuos**; `to_dict()` sólo a la reducción de formas; baselines byte-idénticos | integration | `uv run pytest verification/ -q -k iol && git diff --exit-code .planning/verification/schemas/iol-client/` | ✅ | ⬜ pending |
| 30-04-T2 | 30-04 | 4 | TYP-01 | T-30-12 | snapshot regenerado por script, idempotente | golden | `uv run pytest verification/test_public_surface.py -q` | ✅ | ⬜ pending |
| 30-04-T3 | 30-04 | 4 | TYP-01 | T-30-13, T-30-SC | ruptura notificada; sin bump ni cambio de lockfile | doc + static | `uv run python -c "import iol_client; assert iol_client.__version__ == '0.2.0'" && git diff --exit-code uv.lock` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

La infraestructura de test existe y ya corre en CI — `packages/iol-client/tests/` está en la matriz (py3.12 + py3.13) y lo typechequea el loop de mypy de `ci.yml:85`. No hace falta instalar framework ni tocar `conftest.py`.

Los dos archivos de test que **no existen todavía** los crea la Wave 1 dentro del plan 30-01, antes de cualquier tarea que dependa de ellos:

- [ ] `packages/iol-client/tests/test_models.py` — construcción de los 4 modelos contra los schemas capturados, polimorfismo de `puntas` en sus 3 formas, round-trip `to_dict()` contra los baselines committeados, asimetría `int`/`float` de `cantidadOperaciones` (30-01 T1; ampliado en 30-02 T1 y 30-03 T1)
- [ ] `packages/iol-client/tests/test_typed_surface_red.py` — fixture RED de typecheck en la forma con `pytest.raises`, no-vacua en ambas direcciones (30-01 T3)
- [ ] `test_core.py` — caso de respuesta no-lista que levanta, para serie histórica (30-02 T2) e instrumentos (30-03 T3)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live wire confirmation of `puntas` element shape in `get_quote` | TYP-01 (carry-forward) | Captured sample was `[]`; only the live API can confirm — deferred to Phase 33 strict run | Run `main_iol.py` with credentials in Phase 33 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
