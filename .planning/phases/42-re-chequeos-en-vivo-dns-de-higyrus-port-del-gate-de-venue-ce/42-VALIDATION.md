---
phase: 42
slug: re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-31
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8.3 + pytest-asyncio ≥0.24 + pytest-httpx ≥0.34 |
| **Config file** | `pyproject.toml:102-121` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run --frozen pytest -q verification/test_literal_census_venue_gate.py` |
| **Full suite command** | `uv run pytest -q <las 12 rutas de la allowlist de ci.yml:81-92>` — este es el comando que refleja CI, NO `pytest -q` a secas |
| **Estimated runtime** | ~1 second (baseline medido: 129 passed in 0.55s) |

**Nota crítica:** `mypy` scope es `files = packages/*/src` únicamente — `scripts/`, `main_*.py`, `verification/` quedan fuera del gate global de tipos (`pyproject.toml:97`).

---

## Sampling Rate

- **After every task commit:** `uv run --frozen ruff check . && uv run --frozen pytest -q verification/test_literal_census_venue_gate.py`
- **After every plan wave:** las 12 rutas de la allowlist de `ci.yml` (baseline 129 passed, comparar 129 → 129+N sin regresiones) + `ruff format --check` + `mypy`
- **Before `/gsd-verify-work`:** los 4 gates de CI completos verdes (`ruff check`, `ruff format --check`, `mypy`, `pytest -q` sobre la allowlist) + `--selftest` PASS + los 3 artefactos en disco fechados hoy
- **Max feedback latency:** ~1 second (quick command)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 42-01-TBD | TBD | 1 | LIVE-02 crit.1 | T-42-01 | Gate rechaza `…bbsa.matrizoms.com.ar.attacker.example` | unit | `uv run pytest -q verification/test_literal_census_venue_gate.py` | ❌ W0 | ⬜ pending |
| 42-01-TBD | TBD | 1 | LIVE-02 crit.1 | T-42-01 | Gate rechaza variante userinfo `…@attacker.example` | unit | ídem | ❌ W0 | ⬜ pending |
| 42-01-TBD | TBD | 1 | LIVE-02 crit.1 | T-42-01 | Single-source: ambos sitios comparten la misma referencia (`is`, no `==`) | unit | ídem | ❌ W0 | ⬜ pending |
| 42-01-TBD | TBD | 1 | LIVE-02 crit.1 | T-42-01 | Ninguna comparación `in`/`not in`/`endswith` sobre literal de host (AST) | unit | ídem | ❌ W0 | ⬜ pending |
| 42-01-TBD | TBD | 1 | LIVE-02 crit.1 | — | El test corre en CI (no es inerte — Pitfall 2) | lint | `grep -c "test_literal_census_venue_gate.py" .github/workflows/ci.yml` | ❌ W0 | ⬜ pending |
| 42-02-TBD | TBD | 2 | LIVE-02 crit.3 | — | El censo emite venue + timestamp en el header | unit (offline) | `uv run python scripts/literal_census_33.py --selftest` (asertar línea `CENSUS-HEADER`) | ❌ W0 | ⬜ pending |
| 42-02-TBD | TBD | 3 | LIVE-02 crit.3 | — | Valores observados de los 5 campos Literal | manual-only | corrida en vivo contra bbsa | N/A | ⬜ pending |
| 42-03-TBD | TBD | 3 | LIVE-01 crit.2 | — | Veredicto de higyrus clasifica `SKIPPED`, no `RAN`/`FAILED` | unit | `uv run pytest -q verification/test_main_verify_classification.py verification/test_main_higyrus_skip_line_shape.py` | ✅ (actualizar por rename) | ⬜ pending |
| 42-03-TBD | TBD | 4 | LIVE-01 crit.2 | — | Sobre lleva causa + destino renombrado (`LIVE-HIGY-42`) | unit | `uv run pytest -q verification/test_run_evidence.py verification/test_cycle_closure_phase33.py` | ✅ (actualizar por rename) | ⬜ pending |
| 42-03-TBD | TBD | 4 | LIVE-01 crit.2 | — | Historia congelada (`33-CENSUS.md`) NO se tocó | unit | `uv run pytest -q verification/test_cycle_closure_phase33.py` (línea 250 intacta) | ✅ | ⬜ pending |
| 42-03-TBD | TBD | 3 | LIVE-01 crit.2 | — | Re-chequeo dejó evidencia fechada hoy | integration | `.py` script que lee `run-evidence/higyrus-client.json` y asevera `captured_at` de hoy | ❌ W0 (opcional) | ⬜ pending |
| 42-04-TBD | TBD | 2 | crit.4 | T-42-02 | `mutation_gate.py` byte-idéntico | lint | `test "$(git hash-object verification/mutation_gate.py)" = 6bdaec006cc16f7c8dbfac41701712a9085c691b` | ❌ W0 | ⬜ pending |
| 42-05-TBD | TBD | 3 | crit.5 | — | Lectura fresca `/instruments` + `/segments`, fechada hoy | integration | verificar existencia + `captured_at` de hoy en envelope de `captures/` | ❌ W0 | ⬜ pending |
| 42-ALL | ALL | 4 | Todos | — | Los 4 gates de CI verdes | lint+type | `uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen mypy && uv run pytest -q <allowlist>` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `verification/test_literal_census_venue_gate.py` — nuevo, cubre criterio 1 (spoofing + identidad + AST)
- [ ] Línea nueva en `.github/workflows/ci.yml:79-92` para enrolar el test anterior — sin esto es INERTE (Pitfall 2 de la investigación)
- [ ] Aserción del header (`CENSUS-HEADER venue=… captured_at=…`) dentro de `_selftest()` de `scripts/literal_census_33.py` — cubre criterio 3 offline
- [ ] Pin de byte-identidad de `verification/mutation_gate.py` por blob hash (`6bdaec006cc16f7c8dbfac41701712a9085c691b`) — cubre criterio 4 de forma no-vacua
- [ ] Actualización de los pins vivos de `LIVE-HIGY-33` (condicional a D-06; DNS confirmado roto esta sesión así que el rename es el camino esperado) — sin tocar `verification/test_cycle_closure_phase33.py:250` (historia congelada del 33-CENSUS.md)
- [ ] Framework install: ninguno — pytest ya presente y configurado

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Valores observados de los 5 campos `Literal` de RESPONSE (`marketId`, `cficode`, `currency`, `orderTypes`, `ordType`) | LIVE-02 crit.3 | Depende de datos de mercado en vivo el día de la corrida — no reproducible determinísticamente | Correr `scripts/literal_census_33.py`'s `census_matriz()` contra bbsa en esta sesión, leer el `_report()` output, citar venue+timestamp en el SUMMARY del plan |
| Checkpoint humano bloqueante de fidelidad del port (criterio 1) | LIVE-02 crit.1 | Autorización de tráfico en vivo requiere confirmación humana explícita antes de la primera llamada de red — no automatizable por diseño | `<task type="checkpoint:human-verify" gate="blocking-human">`, operador transcribe "approved" verbatim en el SUMMARY |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s (quick command)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
