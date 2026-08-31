---
phase: 37
slug: matriz-client-dicts-residuales-tipados-alias
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-29
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]`, `pythonpath = ["."]` |
| **Quick run command** | `uv run --package matriz-client pytest packages/matriz-client/tests -q` |
| **Full suite command** | `uv run --package matriz-client pytest packages/matriz-client/tests -q && uv run mypy packages/matriz-client/src && uv run python tools/check_surface_types.py && uv run python tools/check_decode_intactness.py` |
| **Estimated runtime** | ~26 seconds (488 tests, baseline measured 25.64s) |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package matriz-client pytest packages/matriz-client/tests -q`
- **After every plan wave:** Run full suite command + all four `tools/` gates
- **Before `/gsd-verify-work`:** Full suite must be green (cross-package gate — all six packages' tests)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 37-01-xx | TBD | 1 | NOBJ-MTZ-01 | — | Gate detects a reintroduced `dict[str, Any]` field | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -x` | ❌ Wave 0 | ⬜ pending |
| 37-01-xx | TBD | 1 | NOBJ-MTZ-01 | — | `UnknownFrame.raw` exemption is reachable, not dead code | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -k exempt -x` | ❌ Wave 0 | ⬜ pending |
| 37-01-xx | TBD | 1 | NOBJ-MTZ-01 | — | Gate stays green on the real tree after extension | unit | `pytest packages/iol-client/tests/test_surface_types_red.py::test_gate_is_green_on_the_real_tree -x` | ✅ (floors only) | ⬜ pending |
| 37-02-xx | TBD | 2 | NOBJ-MTZ-01 | — | Enveloped risk body populates `report`/`detailedAccountReports` | unit | `pytest packages/matriz-client/tests/test_core.py -k envelope -x` | ❌ Wave 0 | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | `tickPriceRanges` decodes the baseline into `dict[str, TickPriceRange]` | unit | `pytest packages/matriz-client/tests/test_models.py -k tickPriceRange -x` | ❌ Wave 0 | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | `portfolio` is `None` (not `{}`) on an empty payload | unit | `pytest packages/matriz-client/tests/test_decode.py -k portfolio -x` | ✅ exists, assertion flips | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | Undeclared inner keys surface as non-fatal `extra` divergences | unit | `pytest packages/matriz-client/tests/test_decode.py -k extra -x` | ✅ mechanism tested; needs new-model case | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | Mapping axis routes values through `walk_field` with the shared sink | unit | `pytest packages/matriz-client/tests/test_decode.py -k mapping -x` | ✅ exists, must be extended | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | `_convert` shim still coerces a bare `dict[str, Any]` | unit | `pytest packages/matriz-client/tests/test_decode.py -k convert -x` | ✅ exists, must keep passing | ⬜ pending |
| 37-04-xx | TBD | 4 | NOBJ-MTZ-02 | — | All six aliases return their wire field, identically | unit | `pytest packages/matriz-client/tests/test_null_object.py -k alias -x` | ❌ Wave 0 (fixture case exists) | ⬜ pending |
| 37-04-xx | TBD | 4 | NOBJ-MTZ-02 | — | Aliases work on a REST-parsed and a WS-parsed snapshot | unit | `pytest packages/matriz-client/tests/test_null_object.py -k alias_surfaces -x` | ❌ Wave 0 | ⬜ pending |
| 37-04-xx | TBD | 4 | NOBJ-MTZ-02 | — | Aliases remain invisible to the walker (no divergence delta) | unit | `pytest packages/matriz-client/tests/test_null_object.py::test_adding_a_property_alias_does_not_change_the_divergence_count -x` | ✅ exists — do not rewrite | ⬜ pending |
| 37-xx | TBD | any | SC-4 | — | WS daemon-thread paths stay green incl. per-connection decode mode | unit | `pytest packages/matriz-client/tests/test_ws_client.py packages/matriz-client/tests/test_ws_decode_mode.py -x` | ✅ exists | ⬜ pending |
| 37-xx | TBD | any | SC-3 | — | `mypy --strict` clean over the package | typecheck | `uv run mypy packages/matriz-client/src` | ✅ green today | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/matriz-client/tests/test_surface_types_red.py` — NEW; covers NOBJ-MTZ-01 gate non-vacuity + exemption reachability. Mirror `packages/iol-client/tests/test_surface_types_red.py` structure (`_write_fake_package` helper, `check_surface_types(root=tmp_path)`).
- [ ] Envelope regression cases in `packages/matriz-client/tests/test_core.py` — enveloped body populates; flat body raises `PrimaryAPIError`.
- [ ] Alias assertions on the real `MarketDataSnapshot` in `test_null_object.py`, exercising both a REST-parsed and a WS-frame-parsed instance.
- [ ] `tickPriceRanges` decode case driven from the committed baseline JSON.
- Framework install: **not needed** — pytest/pytest-httpx/mypy/ruff all present and green.

---

## Manual-Only Verifications

*None: all phase behaviors have automated verification. Live-network verification of the three Risk-endpoint fields (`report`, `detailedAccountReports`, `portfolio`) is blocked by policy assert D-MATZ-33 and explicitly deferred to Phase 39 (`LIVE-NOBJ-01`) — not a gap in this phase's own validation contract.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---

## Validation Audit 2026-08-31

Auditoría Nyquist retroactiva de la Phase 37, corrida a mano contra el árbol congelado de v1.7 según
el contrato `41-AUDIT-CONTRACT.md` (Phase 41, NYQ-01). Estado de entrada: `status: draft`,
`nyquist_compliant: false`, mapa con 14 filas sin disponer —cuyos Task ID **no son únicos**, y una de
las cuales lleva un selector `-k` que no selecciona ningún test—; **sin subagente** — la auditoría lee
y dispone, no repara (D-06a).

**Auditor:** Phase 41 (`/gsd-execute-phase 41`, plan 41-04) — auditoría de lectura y disposición
**Árbol auditado:** commit de `v1.7` `37a83fe693a303a551f4374f48fe6fc5521804f7`; HEAD de la sesión
de auditoría `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`; identidad probada con
`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 (diff vacío)

| Metric | Count |
|--------|-------|
| Filas auditadas (denominador) | 14 |
| VERIFIED-NOW | 14 |
| VERIFIED-HISTORICALLY | 0 |
| NOT-VERIFIABLE-RETROACTIVELY | 0 |
| Correcciones de comando | 1 (`comando corregido`, R-02) |
| Archivos de test nuevos escritos | 0 |
| Filas NOT ENFORCED en CI | 0 |
| Suite de re-ejecución de esta sesión | `609 passed in 27.84s` (`uv run pytest packages/matriz-client -q`) |

**Nota de clave:** los Task ID del mapa de esta fase se repiten (`37-01-xx` ×3, `37-03-xx` ×5,
`37-04-xx` ×3, `37-xx` ×2), de modo que la clave ordinal `37-r01`..`37-r14` de la §2.3 del contrato
no es cosmética acá: es la única unidad con la que "exactamente una disposición por fila" es
computable. La celda `Row` lleva la clave, el Task ID original y la posición de la fila en el mapa.

### Disposición por fila

| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| 37-r01 · 37-01-xx (fila 1 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_surface_types_red.py -x -q` → `19 passed in 0.19s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` (paso de tests en `ci.yml:154-160`; leg `matriz-client` de la matriz 6 paquetes × py3.12/3.13) |
| 37-r02 · 37-01-xx (fila 2 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_surface_types_red.py -k exempt -x -q` → `3 passed, 16 deselected in 0.01s`, exit 0 — deselect parcial, no total (§6.2) (R-01) | job `test`, `ci.yml:133-166` |
| 37-r03 · 37-01-xx (fila 3 del mapa) | VERIFIED-NOW | `uv run pytest packages/iol-client/tests/test_surface_types_red.py::test_gate_is_green_on_the_real_tree -x -q` → `1 passed in 0.17s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` (leg `iol-client`; es la única fila del mapa de la Phase 37 que corre en otro paquete) |
| 37-r04 · 37-02-xx (fila 4 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_core.py -k envelope -x -q` → `10 passed, 40 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r05 · 37-03-xx (fila 5 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_models.py -k tickPriceRange -x -q` → `3 passed, 31 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r06 · 37-03-xx (fila 6 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_decode.py -k portfolio -x -q` → `3 passed, 116 deselected in 0.02s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r07 · 37-03-xx (fila 7 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_decode.py -k extra -x -q` → `9 passed, 110 deselected in 0.03s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r08 · 37-03-xx (fila 8 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_decode.py -k mapping -x -q` → `24 passed, 95 deselected in 0.03s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r09 · 37-03-xx (fila 9 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_decode.py -k convert -x -q` → `4 passed, 115 deselected in 0.02s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r10 · 37-04-xx (fila 10 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_null_object.py -k alias -x -q` → `11 passed, 63 deselected in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r11 · 37-04-xx (fila 11 del mapa) | VERIFIED-NOW (comando corregido) | **El comando del mapa no selecciona ningún test.** Original literal del mapa, ejecutado: `uv run pytest packages/matriz-client/tests/test_null_object.py -k alias_surfaces -x -q` → `74 deselected in 0.01s`, **exit 5** ("no tests were collected") — cero pasados, ninguna línea de falla; evidencia vacua por la §6.2, no `VERIFIED-NOW`. La conducta declarada (*"Aliases work on a REST-parsed and a WS-parsed snapshot"*) **sí** está cubierta, por dos tests con otro nombre en el mismo archivo, cuyo **cuerpo fue leído** antes de re-apuntar (no sólo su nombre, Assumptions Log A1): `test_each_alias_returns_the_identical_object_on_a_rest_parsed_snapshot` construye la instantánea con `MarketDataSnapshot.from_api(_REST_MARKET_DATA)` y asserta los seis alias con `is` contra su campo de wire (`bids is BI`, `offers is OF`, `last is LA`, `settlement is SE`, `close is CL`, `open_interest is OI`) — identidad, no igualdad, que es justo lo que distingue una vista de una copia; `test_each_alias_returns_the_identical_object_on_a_ws_frame_parsed_snapshot` reconstruye la misma instantánea por la superficie de WS (`MarketDataFrame.from_api(_WS_FRAME).marketData`), asserta `isinstance(..., MarketDataSnapshot)` y repite las seis identidades. Es decir: la conducta de las dos superficies, y no otra. Comando corregido, ejecutado: `uv run pytest packages/matriz-client/tests/test_null_object.py -k "rest_parsed_snapshot or ws_frame_parsed_snapshot" -x -q` → `2 passed, 72 deselected in 0.01s`, exit 0 (R-02) | job `test`, `ci.yml:133-166` (el archivo sustituto es el mismo `test_null_object.py` del paquete `matriz-client` que el mapa ya citaba; la corrección es de selector, no de superficie de enforcement) |
| 37-r12 · 37-04-xx (fila 12 del mapa) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_null_object.py::test_adding_a_property_alias_does_not_change_the_divergence_count -x -q` → `1 passed in 0.01s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r13 · 37-xx (fila 13 del mapa, SC-4) | VERIFIED-NOW | `uv run pytest packages/matriz-client/tests/test_ws_client.py packages/matriz-client/tests/test_ws_decode_mode.py -x -q` → `35 passed in 0.04s`, exit 0 (R-01) | job `test`, `ci.yml:133-166` |
| 37-r14 · 37-xx (fila 14 del mapa, SC-3) | VERIFIED-NOW | `uv run mypy packages/matriz-client/src` → `Success: no issues found in 17 source files`, exit 0 (R-01) | job `typecheck`, `ci.yml:122-123` (step `mypy (src global)`, que corre `uv run mypy` sobre la config raíz y cubre este `src`) |

*Disposiciones: `VERIFIED-NOW` = comando re-ejecutado en esta sesión, verde, con conteo distinto de
cero · `VERIFIED-HISTORICALLY` = artefacto fechado citado, no re-derivable ·
`NOT-VERIFIABLE-RETROACTIVELY` = requería red en vivo, ventana de mercado o checkpoint humano no
reproducible. Calificadores: `(comando corregido)` R-02 · `(ruta corregida)` R-03 ·
`(comando redactado retroactivamente)` R-04.*
