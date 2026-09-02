---
phase: 42
slug: re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-31
closed: 2026-08-31
---

> **Base de los tres flags de arriba (no son flips mecánicos).** `wave_0_complete: true` porque los
> **cinco** ítems de § Wave 0 Requirements quedaron efectivamente cerrados en disco (ver esa
> sección, cada uno con su evidencia). `nyquist_compliant: true` porque **toda** fila del mapa de
> abajo que declara un comando automatizado tuvo ese comando **re-ejecutado en la sesión del plan
> 42-06** —no heredado de un SUMMARY— y las **dos** filas `manual-only` (censo en vivo y checkpoint
> humano bloqueante) están registradas **como tales**, con su evidencia nombrada, en vez de
> reportarse como cobertura automatizada. Si alguna fila hubiera quedado sin re-ejecutar, el flag
> correcto sería `false`.

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

Los `TBD` de la columna `Plan` quedaron re-apuntados a los planes reales (`42-01` … `42-06`) y las
filas `⬜ pending` cerradas con su resultado **medido en la sesión del plan 42-06**.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 42-01-T1 | 42-01 | 1 | LIVE-02 crit.1 | T-42-01 | Gate rechaza `…bbsa.matrizoms.com.ar.attacker.example` | unit | `uv run pytest -q verification/test_literal_census_venue_gate.py` | ✅ | ✅ green — **21 passed**, re-ejecutado 2026-08-31 |
| 42-01-T1 | 42-01 | 1 | LIVE-02 crit.1 | T-42-01 | Gate rechaza variante userinfo `…@attacker.example` | unit | ídem | ✅ | ✅ green — mismo run, caso parametrizado |
| 42-01-T1 | 42-01 | 1 | LIVE-02 crit.1 | T-42-01 | Single-source: ambos sitios comparten la misma referencia (`is`, no `==`) | unit | ídem | ✅ | ✅ green — pin de identidad sobre `_venue_token` y `_VENUE_ALLOWLIST` |
| 42-01-T1 | 42-01 | 1 | LIVE-02 crit.1 | T-42-01 | Ninguna comparación `in`/`not in`/`endswith` sobre literal de host (AST) | unit | ídem | ✅ | ✅ green — walk AST restringido a `census_matriz`, con control positivo |
| 42-01-T1 | 42-01 | 1 | LIVE-02 crit.1 | — | El test corre en CI (no es inerte — Pitfall 2) | lint | `grep -c "test_literal_census_venue_gate.py" .github/workflows/ci.yml` | ✅ | ✅ green — **`1`** (`ci.yml:92`), allowlist 12 → 13 rutas |
| 42-01-T2 | 42-01 | 1 | LIVE-02 crit.3 | — | El censo emite venue + timestamp en el header | unit (offline) | `uv run python scripts/literal_census_33.py --selftest` (asertar línea `CENSUS-HEADER`) | ✅ | ✅ green — `SELFTEST: PASS`, exit `0`, re-ejecutado 2026-08-31 |
| 42-02-T1 | 42-02 | 2 | LIVE-02 crit.3 | — | Valores observados de los 5 campos Literal | **manual-only** | — *(no automatizable: depende de datos de mercado en vivo el día de la corrida)* | N/A | ✅ **manual-only, ejecutado y evidenciado** — `CENSUS-HEADER venue=bbsa captured_at=2026-08-31T21:11:53.196947+00:00`, exit `0`; 4 campos `MEDIDO` + `ordType` `NO MEDIBLE EN ESTA CORRIDA` con causa medida → `42-CENSUS.md`, `42-02-SUMMARY.md` |
| 42-01-T3 | 42-01 | 1 | LIVE-02 crit.1 | T-42-03 | Autorización humana **antes** de la primera llamada de red | **manual-only** | — *(no automatizable por diseño: es la autorización misma)* | N/A | ✅ **manual-only, ejecutado y evidenciado** — checkpoint `gate="blocking-human"`, respuesta del operador `Approved` transcrita verbatim con su procedencia en `42-01-SUMMARY.md:96-108`; cero llamadas de red antes de esa verificación |
| 42-03-T2 | 42-03 | 2 | LIVE-01 crit.2 | — | Veredicto de higyrus clasifica `SKIPPED`, no `RAN`/`FAILED` | unit | `uv run pytest -q verification/test_main_verify_classification.py verification/test_main_higyrus_skip_line_shape.py` | ✅ | ✅ green — **15 passed**, re-ejecutado 2026-08-31 (pins actualizados por el rename D-06) |
| 42-05-T1 | 42-05 | 3 | LIVE-01 crit.2 | — | Sobre lleva causa + destino renombrado (`LIVE-HIGY-42`) | unit | `uv run pytest -q verification/test_run_evidence.py verification/test_cycle_closure_phase33.py` | ✅ | ✅ green — **46 passed**, re-ejecutado 2026-08-31 |
| 42-05-T1 | 42-05 | 3 | LIVE-01 crit.2 | T-42-17 | Historia congelada (`33-CENSUS.md`) NO se tocó | unit | `uv run pytest -q verification/test_cycle_closure_phase33.py` (líneas 250-252 intactas) | ✅ | ✅ green — incluido en las 46; `grep -c 'LIVE-HIGY-33'` sobre el archivo = **2** (conteo asimétrico: `3` o `0` serían defecto) |
| 42-03-T2 | 42-03 | 2 | LIVE-01 crit.2 | T-42-10 | Re-chequeo dejó evidencia fechada hoy | integration | script que lee `run-evidence/higyrus-client.json` y asevera `captured_at` de hoy | ✅ | ✅ green — `2026-08-31T21:38:57.229188+00:00`, `today == True`, `skipped: vendor host unreachable (DNS) — LIVE-HIGY-42` |
| 42-ALL | 42-01…06 | todas | crit.4 | T-42-02 | `mutation_gate.py` byte-idéntico | lint | `test "$(git hash-object verification/mutation_gate.py)" = 6bdaec006cc16f7c8dbfac41701712a9085c691b` | ✅ | ✅ green — hash idéntico al cierre de la fase |
| 42-04-T2 | 42-04 | 2 | crit.5 | T-42-14 | Lectura fresca `/instruments` + `/segments`, fechada hoy | integration | verificar existencia + `captured_at` de hoy en envelope de `captures/` | ✅ | ✅ green — `21:27:42.854194+00:00` / `21:27:43.256969+00:00`, 7 claves cada uno, `today == True`; `git status` de `captures/` vacío (gitignored) |
| 42-06-T2 | 42-06 | 4 | Todos | — | Los 4 gates de CI verdes | lint+type | `uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen mypy && uv run pytest -q <13 rutas de la allowlist>` | ✅ | ✅ green — `All checks passed!` · `279 files already formatted` · `Success: no issues found in 75 source files` · **`150 passed`, 0 failed** (baseline 129 → 150, N=+21) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Filas: 15 · ⬜ pending: 0 · ❌ red: 0 · manual-only declaradas como tales: 2.**

---

## Wave 0 Requirements

- [x] `verification/test_literal_census_venue_gate.py` — nuevo, cubre criterio 1 (spoofing + identidad + AST). **Entregado:** 272 líneas, 21 nodos verdes, commit `7cc103a` (RED).
- [x] Línea nueva en `.github/workflows/ci.yml:79-92` para enrolar el test anterior — sin esto es INERTE (Pitfall 2 de la investigación). **Entregado:** `ci.yml:92`, allowlist 12 → 13 rutas, en el **mismo commit** que creó el archivo; `grep -c` = `1`.
- [x] Aserción del header (`CENSUS-HEADER venue=… captured_at=…`) dentro de `_selftest()` de `scripts/literal_census_33.py` — cubre criterio 3 offline. **Entregado:** `_census_header_lines()` / `_census_header()` (`:189-208`), `_selftest()` extendido, `SELFTEST: PASS` re-ejecutado hoy.
- [x] Pin de byte-identidad de `verification/mutation_gate.py` por blob hash (`6bdaec006cc16f7c8dbfac41701712a9085c691b`) — cubre criterio 4 de forma no-vacua. **Entregado:** pin dentro del lock **con control positivo bajo remarkets** (no vacuo); hash verificado idéntico al cierre de la fase.
- [x] Actualización de los pins vivos de `LIVE-HIGY-33` (condicional a D-06; DNS confirmado roto esta sesión así que el rename es el camino esperado) — sin tocar `verification/test_cycle_closure_phase33.py:250` (historia congelada del 33-CENSUS.md). **Entregado:** D-06 **disparó** (veredicto medido `SKIPPED`, no calendario); 14 sitios vivos renombrados en el commit atómico `f75145c`; `grep -c 'LIVE-HIGY-33'` sobre `test_cycle_closure_phase33.py` = **2** (las de `:250-252`, intactas).
- [x] Framework install: ninguno — pytest ya presente y configurado. **Confirmado:** `git diff --exit-code -- uv.lock` exit `0`; cero comandos de package manager en toda la fase.

**Los 5 ítems sustantivos + el de infraestructura quedaron cerrados en disco, no por afirmación.**
Ésa es la base de `wave_0_complete: true`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Valores observados de los 5 campos `Literal` de RESPONSE (`marketId`, `cficode`, `currency`, `orderTypes`, `ordType`) | LIVE-02 crit.3 | Depende de datos de mercado en vivo el día de la corrida — no reproducible determinísticamente | Correr `scripts/literal_census_33.py`'s `census_matriz()` contra bbsa en esta sesión, leer el `_report()` output, citar venue+timestamp en el SUMMARY del plan |
| Checkpoint humano bloqueante de fidelidad del port (criterio 1) | LIVE-02 crit.1 | Autorización de tráfico en vivo requiere confirmación humana explícita antes de la primera llamada de red — no automatizable por diseño | `<task type="checkpoint:human-verify" gate="blocking-human">`, operador transcribe "approved" verbatim en el SUMMARY |

**Resultado de las dos verificaciones manual-only** (2026-08-31, ejecutadas — no diferidas):

| Behavior | Ejecutada | Evidencia |
|----------|-----------|-----------|
| Valores observados de los 5 campos `Literal` | **Sí** — plan 42-02 | `CENSUS-HEADER venue=bbsa captured_at=2026-08-31T21:11:53.196947+00:00 allowlist_size=2`, exit `0`, `matriz=RAN`; 8 paths sobre 3 endpoints; 4 campos `MEDIDO`, `ordType` `NO MEDIBLE EN ESTA CORRIDA` con causa medida sobre el payload capturado. → `42-CENSUS.md`, `42-02-SUMMARY.md` |
| Checkpoint humano bloqueante | **Sí** — plan 42-01 Task 3 | Escrito `gate="blocking-human"` (nunca `gate="blocking"` a secas); respuesta del operador `Approved` transcrita verbatim en `42-01-SUMMARY.md:96-108`, con procedencia declarada: **no** derivada de `auto_advance`, **no** de `mode: yolo`, **no** de `human_verify_mode: "end-of-phase"`. Cero llamadas de red antes de esa verificación. |

**Estas dos filas NO se cuentan como cobertura automatizada.** Están declaradas `manual-only` en el
mapa de arriba precisamente para que `nyquist_compliant: true` no se apoye en ellas.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 13 de 15 filas con comando automatizado; las 2 restantes declaradas `manual-only` con su evidencia
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — cada plan de la fase cerró con las 13 rutas de la allowlist verdes
- [x] Wave 0 covers all MISSING references — los 5 ítems `❌ W0` del mapa original existen hoy en disco
- [x] No watch-mode flags — ningún comando de este mapa usa `--watch`
- [x] Feedback latency < 1s (quick command) — `21 passed in 0.03s`; suite completa de 13 rutas en `0.54s`
- [x] `nyquist_compliant: true` set in frontmatter — **con la base escrita en la nota del front-matter**, no por flip mecánico

**Approval:** cerrada el 2026-08-31 por el plan 42-06. Disposición completa de los 5 criterios de
éxito de la fase en `42-CLOSURE.md`.

---

## Validation Audit 2026-09-02

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

No gaps: all 15 rows already carry a re-executed automated command or a correctly-declared
`manual-only` disposition with named evidence (0 pending, 0 red). This audit's only action was
normalizing `status: complete` → `status: validated` in front-matter so `/gsd-audit-milestone`'s
classification matrix (draft vs. validated) reads this phase correctly as COMPLIANT — no test or
evidence content changed.
