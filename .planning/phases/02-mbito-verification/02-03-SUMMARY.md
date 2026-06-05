---
phase: 02-mbito-verification
plan: 03
subsystem: verification
tags: [verification, tests, live-run, schema-snapshot, drift-baseline, ambito-financiero-client]

# Dependency graph
requires:
  - phase: 02-01
    provides: append_finding helper (D-10) — usado por el driver para emitir el finding ANTI-BOT EXPECTED durante el live run
  - phase: 02-02
    provides: main_ambito_financiero.py reescrito con 7 probes — el driver ejecutado en Task 3.2
provides:
  - Sección "# ------ Verified live (Phase 2) ------" en test_client.py + test_async_client.py con invariantes D-08 mockeados (AMB-01..AMB-04)
  - Sección "# ------ Regressions ------" agregada (vacía, lista para FIXED findings opportunistic)
  - DRIFT-01 baseline schema snapshot `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` committeado al repo
  - Phase 2 findings file `.planning/verification/ambito-financiero-client-findings.md` committeado con 1 finding ANTI-BOT EXPECTED (AMB-06)
  - Live verification de AMB-01..AMB-06 contra mercados.ambito.com (precio observado: 1455 ARS/USD el 2026-06-05; comportamiento del cliente coincide con expectativas; cero bugs detectados)
affects: [Phases 3-5 — patrón replicable de driver+findings+schema-snapshot por paquete]

# Tech tracking
tech-stack:
  added: []  # solo agregamos tests + artefactos generados; sin nuevas deps
  patterns:
    - Verified-live tests sección con dividers verbatim (D-09)
    - DRIFT-01 baseline snapshot lifecycle (no overwrite + finding on drift, D-25)

key-files:
  created:
    - .planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json
    - .planning/verification/ambito-financiero-client-findings.md
    - .planning/phases/02-mbito-verification/02-03-SUMMARY.md
  modified:
    - packages/ambito-financiero-client/tests/test_client.py
    - packages/ambito-financiero-client/tests/test_async_client.py

key-decisions:
  - "Live run confirmó zero bugs: shape list[list[str]] correcto, header verbatim ['Fecha','Compra','Venta'], parse_ar_decimal('1.435,00') == 1435.0, NoDataError para fecha futura, schema [['str']] estable"
  - "AMB-06 anti-bot verificado terminal como ANTI-BOT EXPECTED (server retorna 403 con UA python-httpx — la defensa funciona como espera)"
  - "Segunda corrida confirmó D-25 drift detection: 'schema sin drift' contra baseline ya committeado"
  - "Sección Regressions queda vacía en este ciclo (nota MVP del contexto: opportunistic only)"

patterns-established:
  - "Verified live (Phase X) test section: dividers verbatim `# ------ Verified live (Phase X) ------` y `# ------ Regressions ------` en test_client.py + test_async_client.py — espejo D-06/D-09 para todos los paquetes en Phases 3-5"
  - "Baseline schema snapshot lifecycle: primera corrida escribe envelope D-21 completo; corridas siguientes comparan y emiten finding SHAPE OPEN si hay drift, NO sobreescriben (D-25)"
  - "Findings file lifecycle: `write_findings` crea esqueleto idempotente (D-03), `append_finding` refresca ART block y agrega rows preservando status humano (D-10)"

requirements-completed: [AMB-01, AMB-02, AMB-03, AMB-04, AMB-05, AMB-06, DRIFT-01]

# Metrics
duration: 25min
completed: 2026-06-05
---

# Phase 02 Plan 03: Verified-live tests + live driver run + DRIFT-01 baseline commit

**AMB-01..AMB-06 verificados en vivo contra mercados.ambito.com; cero bugs detectados; baseline DRIFT-01 + Phase 2 findings file committeados al repo.**

## Performance

- **Duration:** ~25 min (Task 3.1 + Task 3.2 live runs + Task 3.3 commit + SUMMARY)
- **Started:** 2026-06-02T23:47:05Z (Wave 3 dispatch)
- **Completed:** 2026-06-05T22:38:00Z (post-checkpoint AMB-06 run + baseline commit)
- **Tasks:** 3/3 (3.1 test sections, 3.2 live driver run + checkpoint humano "approved + run AMB-06", 3.3 atomic baseline commit)
- **Files modified:** 2 test files (104 líneas append); 2 artefactos generados+commiteados

## Accomplishments

### Task 3.1 — Verified-live test sections (D-08, D-09)

Append a `packages/ambito-financiero-client/tests/test_client.py` + `tests/test_async_client.py`:

- Divider `# ------ Verified live (Phase 2) ------`
- Tests sync (3):
  - `test_get_dollar_banco_nacion_emite_url_dia_gt_12` — locking de URL `/dolarnacion/historico-general/YYYY-MM-DD/YYYY-MM-DD` con día > 12 (AMB-03)
  - `test_parse_ar_decimal_formato_real` — `parse_ar_decimal("1.415,00") == 1415.0` unit test puro (AMB-02)
  - `test_get_dollar_banco_nacion_shape_list_of_list_str` — shape `list[list[str]]` con header verbatim (AMB-01)
- Tests async espejo (3): mismo set con `await aio.get_dollar_banco_nacion(...)` (D-06)
- Divider `# ------ Regressions ------` vacía (placeholder per D-07 lifecycle)

Suite: 172 passed (6 nuevos + 166 baseline).

### Task 3.2 — Live driver run (checkpoint humano)

Driver ejecutado dos veces contra `mercados.ambito.com`:

**Run 1 (default, sin VERIFY_ANTIBOT):**
```
PROBE happy_sync: PASS precio=1445.0
PROBE happy_async: PASS precio=1445.0
PROBE parity_sync_async: PASS sync==async=1445.0
PROBE parse_decimal: PASS venta=1445.0
PROBE no_data: PASS NoDataError para 2026-08-01
PROBE schema_snapshot: PASS escrito get-dollar-banco-nacion.json
PROBE antibot: SKIPPED (opt-in via VERIFY_ANTIBOT=1)
SUMMARY: PASS=6 FAIL=0 SKIPPED=1 FINDING=0
```

**Run 2 (VERIFY_ANTIBOT=1, una sola vez per D-13/D-14):**
```
PROBE happy_sync: PASS precio=1455.0
PROBE happy_async: PASS precio=1455.0
PROBE parity_sync_async: PASS sync==async=1455.0
PROBE parse_decimal: PASS venta=1455.0
PROBE no_data: PASS NoDataError para 2026-08-04
PROBE schema_snapshot: PASS schema sin drift
PROBE antibot: FINDING F-01 (EXPECTED)
SUMMARY: PASS=6 FAIL=0 SKIPPED=0 FINDING=1
```

Observaciones:
- D-02 verbatim respetado (líneas `PROBE <name>: <status> <detail>`)
- D-13 orden honrado (antibot último)
- D-04 honrado (exit 0 en ambas corridas)
- D-25 confirmado: segunda corrida compara contra baseline y reporta `schema sin drift` sin sobreescribir
- D-14 honrado: anti-bot one-shot, sin loops
- D-24 confirmado: fecha futura del probe `no_data` cambió (2026-08-01 → 2026-08-04) porque el driver deriva de `today + 60d`
- Precio observado cambió entre runs (1445 → 1455) — normal, BNA actualiza durante el día

**Checkpoint humano:** usuario respondió "approved + run AMB-06" → corrida adicional one-shot del anti-bot probe → commit de la baseline.

### Task 3.3 — Atomic baseline commit

Commit `6af5b83` (`feat(02-03): commit DRIFT-01 baseline schema + Phase 2 findings`) con dos archivos:

- `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json` — envelope D-21 con 6 keys: `endpoint`, `client_function`, `captured_at` (2026-06-02T23:55:09Z), `base_url` (https://mercados.ambito.com), `sample_date` (2026-06-01), `schema` (`[["str"]]`)
- `.planning/verification/ambito-financiero-client-findings.md` — header `# Findings: ambito-financiero-client-client`, ART block con Timestamp + base_url real, Index row + sección detalle para F-01 ANTI-BOT sync EXPECTED

## Requirements Satisfied (live verification + locked tests)

| Req | Verified in vivo | Test mockeado |
|-----|------------------|---------------|
| AMB-01 (shape list[list[str]] + header verbatim) | PROBE happy_sync PASS | `test_get_dollar_banco_nacion_shape_list_of_list_str` |
| AMB-02 (parse_ar_decimal "1.415,00" → 1415.0) | PROBE parse_decimal PASS | `test_parse_ar_decimal_formato_real` |
| AMB-03 (URL día > 12) | PROBE happy_sync URL emitida correctamente | `test_get_dollar_banco_nacion_emite_url_dia_gt_12` |
| AMB-04 (NoDataError para fecha sin datos) | PROBE no_data PASS | `test_get_dollar_banco_nacion_sin_datos_levanta` (pre-existente, sigue verde) |
| AMB-05 (parity sync↔async) | PROBE parity_sync_async PASS (sync==async=1455.0) | sync+async test files paralelos (D-06) |
| AMB-06 (anti-bot) | PROBE antibot FINDING F-01 EXPECTED — 403 con UA python-httpx; defensa funciona terminal | (no mocked test — comportamiento del server, no del cliente) |
| DRIFT-01 (schema snapshot) | `get-dollar-banco-nacion.json` committeado; segunda corrida confirma "sin drift" (D-25) | (no aplica — DRIFT-01 es contract con futuras corridas) |

## Self-Check: PASSED

- [x] Task 3.1 commit `bbf047f`: test sections agregadas; 172 passed
- [x] Task 3.2 live run #1: 6 PASS + 1 SKIPPED, exit 0, artefactos generados
- [x] Task 3.2 live run #2 (AMB-06): 6 PASS + 1 FINDING EXPECTED, exit 0
- [x] Task 3.3 commit `6af5b83`: baseline (schema + findings) committeados; .gitignore preserva captures/
- [x] Full suite post-merge: 172 passed, 0 regressions
- [x] STATE.md / ROADMAP.md NO modificados directamente (orchestrator owns)

## Deviations

1. **Cherry-pick recovery (Rule 3 — Blocker workaround).** Durante el merge del worktree de Wave 3 al main, una modificación copy-back de un hook causó que `git merge --ff-only` abortara con "local changes would be overwritten" y posteriormente el branch worktree-agent-* fue deleted accidentalmente. Recovery: identifiqué el commit dangling (`9c7ea25`) vía `git fsck --lost-found`, validé que las unstaged changes en main eran idénticas (`git diff 9c7ea25 -- ... | wc -l = 0`), descarté unstaged duplicates, cherry-pick'eé el commit (`bbf047f` en main con misma metadata). Sin pérdida de trabajo, sin reescritura de history.

2. **Edit/Write tool failure noted por executor (Rule 3 — Blocker workaround).** Per el executor's deviation note in checkpoint return: Edit/Write tools reportaron éxito pero el contenido no se escribía a disco para `test_client.py` durante Task 3.1. Workaround: heredoc shell write `cat > file << PYEOF ... PYEOF`. Resultado verificable vía `wc -l`, `grep`, `pytest`. Commit final `bbf047f` con contenido correcto. Causa raíz no identificada en ese moment; posible bug de cache en este harness session.

## Next Phase Recommendations

- Phase 3 (IOL) puede reusar este lifecycle exact: driver con probes nombrados + write_findings + append_finding + schema snapshots por endpoint.
- El placeholder de Regressions queda listo para futuros FIXED findings opportunistic (Phase 3-5 o iteraciones posteriores).
- AMB-06 finding F-01 ANTI-BOT EXPECTED ya está committeado en `ambito-financiero-client-findings.md` — futuras corridas con `VERIFY_ANTIBOT=1` actualizarán el ART block y reidentificarán F-01 (idempotente por fid, D-10).
