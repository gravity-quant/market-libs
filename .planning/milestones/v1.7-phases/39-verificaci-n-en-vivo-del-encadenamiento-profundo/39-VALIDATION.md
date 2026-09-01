---
phase: 39
slug: verificaci-n-en-vivo-del-encadenamiento-profundo
status: validated
nyquist_compliant: false
not_verifiable_retroactively: 4
audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7
audit_baseline_head: 6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5
frozen_tree_verified: true
wave_0_complete: false
created: 2026-08-29
updated: 2026-08-31
last_audited: 2026-08-31
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx 0.34+, pytest-cov |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run --frozen python -m pytest -q verification/test_main_<pkg>_deep_chain.py` |
| **Full suite command** | `uv run --frozen python -m pytest -q packages/<pkg>` (per package, mirrors CI) |
| **Estimated runtime** | ~30s per package unit suite; live driver runs are separate (network-bound, minutes) |

---

## Sampling Rate

- **After every task commit:** `uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen mypy` + the touched deep-chain lock (AST test)
- **After every plan wave:** `uv run --frozen python -m pytest -q packages/<touched-pkg>` + the full explicit `verification/` allowlist from `ci.yml:80-84`, **including newly appended files**
- **Before `/gsd-verify-work`:** all 6 packages × py3.12/3.13 green, plus the widened `verification/` allowlist green
- **Max feedback latency:** ~30s (unit/AST tests); live-run verification is manual/measured, not part of the fast loop

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 39-01-01 | TBD | 0 | LIVE-NOBJ-01 (SC-1 classification, D-01) | — | New skip line matches `_ENV_SKIP`; `SKIPPED (mutating, guard off)` still does not | unit | `pytest -q verification/test_main_verify_classification.py` | ❌ Wave 0 | ✅ (VN 2026-08-31) |
| 39-01-02 | TBD | 0 | LIVE-NOBJ-01 (SC-1 classification shape, D-01/Pitfall 2) | — | Emitted skip line shape (colon-present) mirrors market-data precedent | unit | `pytest -q verification/test_main_<pkg>_skip_line_shape.py` | ❌ Wave 0 | ✅ (VN 2026-08-31) |
| 39-01-03 | TBD | 0 | LIVE-NOBJ-01 (D-02 allowlist) | T-39-01 | D-MATZ-33 exact-equality allowlist admits `bbsa.matrizoms.com.ar`, rejects substring/userinfo spoofing variants | unit | `pytest -q verification/test_main_matriz_deep_chain.py::test_d_matz_33_allowlist` (or dedicated file) | ❌ Wave 0 | ✅ (VN 2026-08-31) |
| 39-01-04 | TBD | 0 | LIVE-NOBJ-01 (SC-3 non-vacuous closure, D-09) | — | `verify_cycle_closure` PASS requires positive probe-count evidence per package, not absence of findings | unit | `pytest -q verification/test_cycle_closure_phase33.py` | ✅ exists (currently red — stale `_CENSUS` path; repoint + extend) | ✅ (VN 2026-08-31) |
| 39-02-01 | TBD | 1 | LIVE-NOBJ-01 (SC-1 iol, D-03) | — | `probe_get_quote_{sync,async}` / `probe_get_instruments_by_type_{sync,async}` dereference `.puntas.*` inside `try` body, above a floor | unit (AST) | `pytest -q verification/test_main_iol_deep_chain.py` | ❌ Wave 1 | ✅ (VN 2026-08-31) |
| 39-02-02 | TBD | 1 | LIVE-NOBJ-01 (SC-1 higyrus, D-04) | — | Chosen posiciones probe builds `Posicion.from_api` and dereferences `.parking[...]`, both surfaces, zero extra HTTP calls | unit (AST) | `pytest -q verification/test_main_higyrus_deep_chain.py` | ❌ Wave 1 | ✅ (VN 2026-08-31) |
| 39-02-03 | TBD | 1 | LIVE-NOBJ-01 (SC-1 matriz, D-05) | — | `probe_get_market_data{,_async}` dereference all 6 aliases off `MarketDataSnapshot`, inside `try` body, both surfaces (sync + async) | unit (AST) | `pytest -q verification/test_main_matriz_deep_chain.py` | ❌ Wave 1 | ✅ (VN 2026-08-31) |
| 39-02-04 | TBD | 1 | LIVE-NOBJ-01 (SC-1 ámbito, D-06 declared absence) | — | ámbito still declares zero model classes / empty `__all__` | unit (AST) | `pytest -q verification/test_cycle_closure_phase33.py::_ambito_declares_zero_models` | ✅ exists | ✅ (VN 2026-08-31) |
| 39-02-05 | TBD | 1 | LIVE-NOBJ-01 (SC-2 edge cases, D-12) | — | No chain raises `AttributeError`/`TypeError` on empty/absent/204/null mocked payloads | unit (mocked) | `pytest -q packages/<pkg>/tests/test_deep_chain_edges.py` | ❌ Wave 1 | ✅ (VN 2026-08-31) |
| 39-03-01 | TBD | 2 | LIVE-NOBJ-01 (SC-3 in-cycle fix, D-08) | — | Each CONFIRMED divergence found live is fixed with sync+async mirror and pinned by a mocked regression | unit (mocked) | `pytest -q packages/<pkg>/tests/` | ❌ per-fix (unknown until live run) | ✅ (VN 2026-08-31) |
| 39-03-02 | TBD | 2 | LIVE-NOBJ-01 (SC-4 census, D-10/D-11) | — | `39-CENSUS.md` exists, uses `(slug, model, field_path, kind)` triple unit, separates Null-Object-policy collapse from real fixes, cites source columns | manual (artifact review) | — | ❌ Wave 2 | ⬜ histórico |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⬜ histórico (VERIFIED-HISTORICALLY, auditoría 2026-08-31) · ⬜ no re-verificable (NOT-VERIFIABLE-RETROACTIVELY, auditoría 2026-08-31)*

---

## Wave 0 Requirements

- [ ] `verification/test_main_verify_classification.py` — covers SC-1 classification (D-01): env-skip→SKIPPED, new measured-skip→SKIPPED, rc!=0→FAILED, else RAN; market-data + wallets unaffected
- [ ] `verification/test_main_matriz_skip_line_shape.py` / `verification/test_main_higyrus_skip_line_shape.py` — covers the colon-shape contract (Pitfall 2), mirrors `test_main_market_data_skip_line_shape.py`
- [ ] `verification/test_main_iol_deep_chain.py` — AST lock for SC-1 (D-03)
- [ ] `verification/test_main_higyrus_deep_chain.py` — AST lock for SC-1 (D-04)
- [ ] `verification/test_main_matriz_deep_chain.py` — AST lock for SC-1 (D-05), including the D-02 allowlist behavior
- [ ] `packages/<pkg>/tests/test_deep_chain_edges.py` ×3 (iol, higyrus, matriz) — mocked empty/absent/204 edge-case coverage for SC-2
- [ ] **`.github/workflows/ci.yml:80-84`** — append every new `verification/` file to the explicit allowlist in the same commit that adds it, or the lock is inert (documented Phase 36 defect, WR-01)
- [ ] `verification/test_cycle_closure_phase33.py` — repoint stale `_CENSUS` path to `.planning/milestones/v1.6-phases/33-…/33-CENSUS.md`, extend for D-09 non-vacuity
- [ ] Framework install: none required (all dependencies already pinned in `uv.lock`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Status |
|----------|-------------|------------|--------------------|--------|
| Live driver run per in-scope package (iol, higyrus, matriz, ambito) reports PASS/SKIPPED with measured cause and named destination | LIVE-NOBJ-01 (SC-1) | Depends on live third-party API availability, DNS, and market-hours state at execution time — not reproducible in a mocked unit test | Run `uv run --package <pkg> python main_<pkg>.py`; inspect stdout classification line and `.planning/verification/<pkg>-findings.md` | ⬜ no re-verificable |
| matriz D-12 market-closed vs. mis-modelled discrimination | LIVE-NOBJ-01 (SC-2) | Requires running inside (or explicitly outside, with the `LA.date` staleness guard) an ARG trading-session window | Run matriz driver during/outside session hours; record window and guard outcome in `39-CENSUS.md` | ⬜ no re-verificable |
| Census contrast against `33-CENSUS.md` and `29-SIZING.md`, with Null-Object-collapse vs. real-fix split | LIVE-NOBJ-01 (SC-4) | Requires cross-referencing multiple historical artifacts and applying judgment documented in `35-RETIRED-TRIPLES.md`; not a pass/fail unit assertion | Author `39-CENSUS.md` per the D-10/D-11 method; cross-check triple-dump (Pattern 4, seam 1) against findings-file parse (seam 2) | ⬜ no re-verificable |
| D-02 operator checkpoint (hostname allowlist widening) | LIVE-NOBJ-01 (security) | Security-policy-adjacent change requires explicit human sign-off per project precedent (D-08/D-18), not just automated test passage | Confirm operator sign-off is recorded in code comment + phase report before merging the allowlist change (already given 2026-08-29, memory `project_matriz_bbsa_sandbox.md` — must still be surfaced as a blocking checkpoint per `mode: yolo` override note in RESEARCH.md Security Domain) | ⬜ no re-verificable |

*Status: la columna se agrega en la auditoría 2026-08-31. `⬜ no re-verificable` =
`NOT-VERIFIABLE-RETROACTIVELY` (R-07): la conducta exigía red viva de terceros, una ventana de
sesión de mercado, un juicio cruzado sobre artefactos históricos o un checkpoint humano fechado, y
ninguna de las cuatro se re-deriva hoy. Ninguna fila manual lleva `✅`.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (fast loop); live-run and census steps are explicitly manual per above
- [ ] `nyquist_compliant: true` set in frontmatter
- [x] Audit 2026-08-31: 15 filas dispuestas (10 VERIFIED-NOW / 1 VERIFIED-HISTORICALLY / 4 NOT-VERIFIABLE-RETROACTIVELY); 0 archivos de lock nuevos; nyquist_compliant sigue en false

**Approval:** pending

---

## Validation Audit 2026-08-31

Auditoría Nyquist retroactiva de la Phase 39, corrida a mano contra el árbol congelado de v1.7
según el contrato `41-AUDIT-CONTRACT.md` (Phase 41, NYQ-01). Estado de entrada: `status: draft`,
`nyquist_compliant: false`, 15 filas sin disponer — las 11 del `## Per-Task Verification Map`, todas
en `⬜ pending`, más las 4 de `## Manual-Only Verifications`, que ni siquiera tenían columna de
estado (se le agrega una en esta auditoría); **sin subagente** — la auditoría lee y dispone, no
repara (D-06a).

**Auditor:** Phase 41 (`/gsd-execute-phase 41`, plan 41-06) — auditoría de lectura y disposición
**Árbol auditado:** commit de `v1.7` `37a83fe693a303a551f4374f48fe6fc5521804f7`; HEAD de la sesión
de auditoría `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`; identidad probada con
`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 (diff vacío)

| Metric | Count |
|--------|-------|
| Filas auditadas (denominador) | 15 |
| VERIFIED-NOW | 10 |
| VERIFIED-HISTORICALLY | 1 |
| NOT-VERIFIABLE-RETROACTIVELY | 4 |
| Correcciones de comando | 1 |
| Archivos de test nuevos escritos | 0 |
| Filas NOT ENFORCED en CI | 5 |
| Suite de re-ejecución de esta sesión | las 7 suites de `verification/` citadas por el mapa, juntas → `78 passed in 0.39s` |

### Disposición por fila

| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| 39-r01 · 39-01-01 | VERIFIED-NOW | `uv run pytest -q verification/test_main_verify_classification.py` → `7 passed in 0.04s` | job `lint`, allowlist explícita `ci.yml:81-92` |
| 39-r02 · 39-01-02 | VERIFIED-NOW | `uv run pytest -q verification/test_main_matriz_skip_line_shape.py` → `19 passed in 0.06s`; `uv run pytest -q verification/test_main_higyrus_skip_line_shape.py` → `8 passed in 0.08s` | job `lint`, allowlist explícita `ci.yml:81-92` (los dos archivos enrolados) |
| 39-r03 · 39-01-03 | VERIFIED-NOW (comando corregido) | Original `uv run pytest -q verification/test_main_matriz_deep_chain.py -k allowlist` → `9 deselected in 0.01s`, exit **5**, cero tests pasados. Corregido `uv run pytest -q verification/test_main_matriz_skip_line_shape.py` → `19 passed in 0.06s`, exit 0; los tres locks de allowlist de ese archivo fueron leídos y assertan la conducta original (detalle en `### Correcciones de comando`) | job `lint`, allowlist explícita `ci.yml:81-92` |
| 39-r04 · 39-01-04 | VERIFIED-NOW | `uv run pytest -q verification/test_cycle_closure_phase33.py` → `21 passed in 0.07s` | job `lint`, allowlist explícita `ci.yml:81-92` |
| 39-r05 · 39-02-01 | VERIFIED-NOW | `uv run pytest -q verification/test_main_iol_deep_chain.py` → `6 passed in 0.05s` | job `lint`, allowlist explícita `ci.yml:81-92` |
| 39-r06 · 39-02-02 | VERIFIED-NOW | `uv run pytest -q verification/test_main_higyrus_deep_chain.py` → `8 passed in 0.09s` | job `lint`, allowlist explícita `ci.yml:81-92` |
| 39-r07 · 39-02-03 | VERIFIED-NOW | `uv run pytest -q verification/test_main_matriz_deep_chain.py` → `9 passed in 0.10s` | job `lint`, allowlist explícita `ci.yml:81-92` |
| 39-r08 · 39-02-04 | VERIFIED-NOW | El node-id del mapa nombra `_ambito_declares_zero_models`, que es un **helper privado y no un test**: pytest sale **exit 4** (error de uso) con `no tests ran in 0.01s`. Ejecutado el selector de archivo `uv run pytest -q verification/test_cycle_closure_phase33.py -k ambito` → `2 passed, 19 deselected in 0.01s` — `test_cycle_closure_is_green[ambito-financiero-client]` y `test_cycle_closure_is_not_vacuous[ambito-financiero-client]`, ambos vía ese mismo helper, que asserta 0 clases de modelo y `__all__` vacío | job `lint`, allowlist explícita `ci.yml:81-92` |
| 39-r09 · 39-02-05 | VERIFIED-NOW | `uv run pytest -q packages/iol-client/tests/test_deep_chain_edges.py packages/higyrus-client/tests/test_deep_chain_edges.py packages/matriz-client/tests/test_deep_chain_edges.py` → `50 passed in 0.14s` | job `test`, `ci.yml:133-166` |
| 39-r10 · 39-03-01 | VERIFIED-NOW | `uv run pytest -q packages/matriz-client/tests/test_instruments_flat_identifier_shape.py` → `13 passed in 0.03s` — la regresión mockeada de la única divergencia CONFIRMED de la fase (F-43/F-44), fijada en el sitio compartido de `_core.py` que recorren `client.py` y `aio.py` | job `test`, `ci.yml:133-166` |
| 39-r11 · 39-03-02 | VERIFIED-HISTORICALLY | Revisión de artefacto (R-06), no re-derivada: `39-CENSUS.md` existe en disco (430 líneas) y `39-VERIFICATION.md` verdad #8 lo cita como cumplida — *"El censo contrasta explícitamente contra la Fase 33 y el piso de `29-SIZING.md`, separando colapso-de-política vs corrección real"* → `✓ VERIFIED` | **NOT ENFORCED (por naturaleza)** — revisión de documento |
| 39-m01 · (manual-only fila 1) | NOT-VERIFIABLE-RETROACTIVELY | Evidencia parcial superviviente: los 4 envelopes fechados de `.planning/verification/run-evidence/` (`captured_at` 2026-08-30 UTC = sesión del 2026-08-29 ART) con sus sondas ejecutadas — `iol-client.json` 15, `matriz-client.json` 50, `ambito-financiero-client.json` 7, `higyrus-client.json` 0 con su causa medida registrada; más las transcripciones de `39-07-SUMMARY.md`. **Por qué no basta:** un envelope prueba que la corrida ocurrió y con qué conteo, no que la conducta observada sea re-derivable hoy; re-derivarla exigiría abrir tráfico contra una API financiera de terceros, que R-08 prohíbe | **NOT ENFORCED (por naturaleza)** — corrida de driver en vivo |
| 39-m02 · (manual-only fila 2) | NOT-VERIFIABLE-RETROACTIVELY | Evidencia parcial superviviente: `39-CENSUS.md` § "Casos límite de D-12", que declara la ventana de la corrida (sábado 2026-08-29 23:34 ART / 2026-08-30 02:41 UTC, mercado ARG **cerrado**) y el discriminador efectivamente aplicado (la guarda de antigüedad D-MATZ-5 preexistente, no una lectura del reloj). **Por qué no basta:** discriminar mercado cerrado de modelado incorrecto exige la respuesta real de una ventana de sesión de negociación concreta, y esa ventana no se recrea a voluntad; el artefacto documenta el resultado del juicio, no lo vuelve reproducible | **NOT ENFORCED (por naturaleza)** — ventana de sesión de mercado |
| 39-m03 · (manual-only fila 3) | NOT-VERIFIABLE-RETROACTIVELY | Evidencia parcial superviviente: `39-CENSUS.md` §§ "Contraste contra la Fase 33 y contra el piso ratificado" y "El split que SC-4 exige (D-11)", más los censos históricos que contrasta (`33-CENSUS.md`, `29-SIZING.md`) y el addendum de Phase 39 de `35-RETIRED-TRIPLES.md`. **Por qué no basta:** el contraste es un juicio cruzado sobre artefactos históricos, no una aserción pass/fail; re-correrlo hoy re-ejecutaría el criterio del auditor sobre los mismos documentos, no la conducta que la fase verificó | **NOT ENFORCED (por naturaleza)** — juicio cruzado sobre artefactos |
| 39-m04 · (manual-only fila 4) | NOT-VERIFIABLE-RETROACTIVELY | Evidencia parcial superviviente: el sign-off del operador del 2026-08-29 registrado en el comentario de política de `main_matriz.py:118-121` y en `39-CONTEXT.md`, ya citado por la propia fila manual-only de este archivo. **Por qué no basta:** un checkpoint humano fechado no se re-deriva — re-obtenerlo produciría un sign-off nuevo del 2026-08-31, no evidencia de la decisión del 2026-08-29 —; y lo que el checkpoint autorizó es una decisión de política, no una aserción ejecutable | **NOT ENFORCED (por naturaleza)** — checkpoint humano |

*Disposiciones: `VERIFIED-NOW` = comando re-ejecutado en esta sesión, verde, con conteo distinto de
cero · `VERIFIED-HISTORICALLY` = artefacto fechado citado, no re-derivable ·
`NOT-VERIFIABLE-RETROACTIVELY` = requería red en vivo, ventana de mercado o checkpoint humano no
reproducible. Calificadores: `(comando corregido)` R-02 · `(ruta corregida)` R-03 ·
`(comando redactado retroactivamente)` R-04.*

**Sobre la cuarta columna.** Las **siete** suites de `verification/` que el mapa de esta fase cita
—clasificación, las dos de forma de línea de skip, cierre de ciclo y las tres de cadena profunda—
están **todas** dentro del allowlist explícito de CI, porque la propia Phase 39 cerró ese defecto
(fix WR-01). Las dos filas que corren suites bajo `packages/` mapean al job `test`. Por lo tanto el
conteo de 5 filas `NOT ENFORCED` de esta fase **no viene de sus locks**: viene de su fila de
revisión de censo y de sus cuatro filas manuales, que por naturaleza no tienen superficie de CI.

### Correcciones de comando

Una sola, y es la **segunda y última** corrección autorizada por R-02 en toda la Phase 41
(la primera fue `37-r11`).

| Fila | Comando original | Resultado real | Comando corregido | Resultado |
|------|------------------|----------------|-------------------|-----------|
| `39-r03` | `uv run pytest -q verification/test_main_matriz_deep_chain.py -k allowlist` | `9 deselected in 0.01s` — exit **5**, selección vacía, **cero** tests pasados | `uv run pytest -q verification/test_main_matriz_skip_line_shape.py` | `19 passed in 0.06s` — exit 0 |

La conducta que la fila declara —*el allowlist de hostname de la política D-MATZ-33 admite el host
conocido por igualdad exacta y rechaza las variantes de spoofing por superstring y por userinfo*—
vive en `verification/test_main_matriz_skip_line_shape.py`, no en el archivo de cadena profunda que
el mapa nombra. Antes de re-apuntar se leyó el **cuerpo** de sus tres locks de allowlist (no sólo
sus nombres), y los tres assertan esa conducta:

- `test_venue_allowlist_has_exactly_the_two_known_hosts` — asserta que el allowlist tiene
  exactamente los dos hosts confirmados por el operador y ninguno más (`len(allowlist) == 2`), de
  modo que ensancharlo obliga a un checkpoint humano nuevo.
- `test_venue_token_resolves_by_exact_hostname` — parametrizado con **13** casos medidos que
  ejercitan el predicado de resolución de venue: los dos hosts conocidos con y sin esquema, la
  barra final, la variante de **superstring de sufijo** (`…attacker.example` colgado del host
  conocido) rechazada, la variante de **userinfo** (el host conocido en la parte de usuario,
  siendo `attacker.example` el host real) rechazada, el host de producción rechazado, y el
  fail-closed ante cadena vacía y ante basura no parseable.
- `test_no_substring_membership_check_over_a_host_literal` — asserta **por AST** (no por grep, para
  no confundir el comentario que cita el código viejo con código vivo) que ninguna comparación de
  pertenencia de substring sobre un literal de host vuelve al driver.

El `-k allowlist` del mapa falla porque ningún test de `test_main_matriz_deep_chain.py` lleva esa
subcadena en su nombre: los 9 tests del archivo se descartan íntegros y pytest sale limpio, sin
imprimir ninguna línea de falla. Ese es exactamente el modo de falla que la regla anti-vacuidad de
la §6.2 del contrato existe para atrapar.

### Las cuatro filas no re-verificables

Las cuatro filas de `## Manual-Only Verifications` quedan `NOT-VERIFIABLE-RETROACTIVELY` por R-07,
según la resolución de OQ#1 escrita en la §3.1 del contrato de auditoría. Cada una es irrecuperable
por un motivo distinto y nombrado: `39-m01` por **red viva de terceros** (la corrida de driver por
paquete depende de disponibilidad, DNS y estado de mercado del momento); `39-m02` por **ventana de
sesión de mercado** (la discriminación entre mercado cerrado y modelado incorrecto sólo se produce
dentro de una sesión concreta); `39-m03` por **juicio cruzado sobre artefactos históricos** (no es
una aserción pass/fail); `39-m04` por **sign-off humano fechado** (re-obtenerlo produciría una
decisión nueva, no evidencia de la vieja).

La evidencia parcial superviviente **no se descarta** y está nombrada en la celda de cada fila: los
cuatro envelopes fechados con su conteo de sondas, las transcripciones de `39-07-SUMMARY.md`, las
dos secciones pertinentes de `39-CENSUS.md`, y el sign-off registrado en el comentario de política
del driver de matriz.

**Rationale de la resolución, registrado para que no se re-litigue.** `41-RESEARCH.md` propuso en su
primera pregunta abierta partir el bloque —tres filas a `VERIFIED-HISTORICALLY` apoyándose en que
los envelopes existen en disco, y sólo una a `NOT-VERIFIABLE-RETROACTIVELY`—. Se resuelve **en
contra** de esa lectura, por dos razones. Primero, D-04 nombra estas cuatro filas **por su nombre**
como el arquetipo del marcador `NOT-VERIFIABLE-RETROACTIVELY`; ante un conflicto entre el texto de
una decisión lockeada y una inferencia posterior del research, gana la decisión. Segundo, en una
auditoría la dirección segura es **sub-declarar**: un `VERIFIED-HISTORICALLY` de más es una garantía
falsa que se propaga aguas abajo a quien lea este archivo, mientras que un
`NOT-VERIFIABLE-RETROACTIVELY` de más sólo pide trabajo futuro. Los envelopes fechados prueban que
la corrida **ocurrió** y con qué conteo; no prueban que la conducta sea **reproducible**, y es la
reproducibilidad lo que la vara de R-06 exige para citar un artefacto como evidencia histórica
suficiente.

**Ninguna de las dos superficies de esta fase se re-corrió contra la red.** Ningún `main_*.py` fue
ejecutado por esta auditoría (R-08).

### Hallazgos de bookkeeping

1. **La columna `File Exists` del mapa quedó congelada en su estado de plan-time.** Nueve de las
   once celdas siguen marcadas `❌` con su etiqueta de wave (`Wave 0`, `Wave 1`, `Wave 2`,
   `per-fix`), que es lo que valía **antes** de ejecutar la fase. Medido hoy: las once superficies
   que esas filas verifican existen en disco y corren verde — las ocho suites de test citadas más
   el artefacto `39-CENSUS.md`. La columna es registro de plan-time y **no se reescribe**; se
   nombra acá.

2. **El rango de líneas del allowlist de CI citado en este archivo está desactualizado.** La
   sección `## Sampling Rate` y la lista de `## Wave 0 Requirements` citan **`ci.yml:80-84`**. El
   rango real medido hoy es **`ci.yml:81-92`** — 12 archivos —, ensanchado por el propio fix WR-01
   de esta fase (commit `0f45508`). Verificado:
   `grep -n 'verification/test_main_market_data_deep_chain.py' .github/workflows/ci.yml` cae en la
   línea **81**, que es la primera entrada del bloque, y el bloque cierra en la **92**. Las
   secciones históricas de Wave 0 **no se editan**: el rango correcto queda escrito acá.

3. **Hallazgo transversal de enforcement — 40 locks de `verification/` no corren en CI.** Medido en
   esta sesión: `ls verification/test_*.py | wc -l` → **52** archivos calzan el patrón de test; el
   allowlist explícito de `ci.yml:81-92` enrola **12**; los **40** restantes **no se ejecutan en
   ningún job**. Es rot invisible por construcción, porque `verification/` nunca corrió como
   directorio en CI. El conteo se **reporta y no se arregla acá**: el edit consolidado del
   allowlist de `.github/workflows/ci.yml` es trabajo de la **Phase 45** (HARN-04), y tocar
   `.github/` en esta fase rompería el invariante de árbol congelado del criterio 1. Ninguna de las
   siete suites que el mapa de la Phase 39 cita está entre esos 40: las siete están enroladas.

4. **El node-id de la fila `39-r08` nombra un helper privado, no un test.** El mapa declara
   `verification/test_cycle_closure_phase33.py::_ambito_declares_zero_models`, y
   `_ambito_declares_zero_models` es una función auxiliar del módulo, no un caso de test: pytest
   sale **exit 4** (error de uso) con `no tests ran in 0.01s`. Es **otro modo de falla** que el de
   la §R-02, cuyo disparador es un selector `-k` que colecciona 0 tests y sale con **exit 5**; por
   eso esta fila **no** consume una tercera corrección R-02 y se dispone `VERIFIED-NOW` **plano**.
   La conducta declarada —ámbito sigue declarando cero clases de modelo y `__all__` vacío— sí está
   cubierta, por los dos casos parametrizados que atraviesan ese mismo helper. Es, de todos modos,
   la misma clase de defecto: un contrato de verificación que apunta a algo que no se puede
   ejecutar.

5. **Versión de herramienta.** La tabla `## Test Infrastructure` declara `pytest 8.3+`, que sigue
   siendo verdadera como piso; la versión efectivamente usada en esta auditoría es **pytest
   9.0.3** sobre **uv 0.11.3**. Se deja constancia sin reescribir la tabla histórica.

### Escalaciones

Ninguna. La única fila con selección vacía de esta fase es `39-r03`, que cae limpiamente en R-02 y
es la segunda —y última— corrección autorizada del contrato; no apareció una tercera. El defecto de
node-id de `39-r08` se evaluó explícitamente contra el disparador de R-02 y **no** lo satisface
(exit 4 por error de uso, no exit 5 por selección vacía), así que se registra como hallazgo de
bookkeeping y no como escalación. El conteo de 40 locks sin enrolar tampoco es una escalación de
esta fase: es un hallazgo transversal con destino ya nombrado en la Phase 45.
Cero archivos de test nuevos; cero escalaciones.

Veredicto de auditoría: **Phase 39 queda PARTIAL** — status draft → validated,
nyquist_compliant sigue en false. R-09 falla por **(b)** —1 fila `VERIFIED-HISTORICALLY` más
**4 filas `NOT-VERIFIABLE-RETROACTIVELY`**— y por **(c)** —1 corrección de comando, `39-r03`—.
Esta es la única de las cinco fases auditadas que retiene ítems no re-verificables, y su
front-matter lo declara con `not_verifiable_retroactively: 4` en vez de reportarse limpia.
