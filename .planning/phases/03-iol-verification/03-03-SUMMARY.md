---
phase: 03-iol-verification
plan: 03
subsystem: iol-verification-baseline
tags: [verification, tests, invariants, live-run, schema-commit, checkpoint, drift-01-mirror]
requires:
  - "03-01: cliente IOL con _refresh_token + _refresh()/_refresh_unlocked() + _ensure_token fallback (sync+async)"
  - "03-02: main_iol.py reescrito con 15 probes nombrados en orden D-IOL-5 (driver listo para invocar)"
  - "packages/iol-client/.env (gitignored) con credenciales reales IOL_USER + IOL_PASSWORD"
provides:
  - "Sección `# ------ Verified live (Phase 3) ------` con 4 invariantes IOL-04 espejados en test_client.py + test_async_client.py (D-IOL-21)"
  - ".planning/verification/iol-client-findings.md — F-01 OPEN registrado (SHAPE, both) tras primer live run"
  - "4 schema snapshots DRIFT-01 mirror en .planning/verification/schemas/iol-client/ con envelope D-21"
  - "Pitfall 2 envelope `titulos` capturado en get-instruments-by-type.json"
affects:
  - "Driver run manual one-shot contra api.invertironline.com — sin retries (Pitfall 9, CONCERNS.md lockout risk)"
  - "Suite pytest: 195 passed (+6 vs baseline 189), 1 deselected (live marker), 0 regresiones"
tech-stack:
  added: []
  patterns:
    - "Verified-live mocked tests: pytest_httpx con URL exacta `/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2` para IOL-02"
    - "Verified-live mocked test envelope titulos: `httpx_mock.add_response(json={'titulos': [...]})` para IOL-04 envelope unwrap"
    - "Mirror dual sync/async espejado: 4 tests por surface (URL exacta + envelope titulos + ultimoPrecio numeric + date format day>12)"
    - "Sección `# ------ Regressions ------` (Plan 03-01) preservada verbatim — Verified-live se appendea sin tocar regression tests"
    - "First-run baseline: schemas y findings se commitean tal cual produjo el driver (D-25 no-overwrite-on-drift se activará en runs futuros)"
key-files:
  created:
    - ".planning/verification/iol-client-findings.md"
    - ".planning/verification/schemas/iol-client/get-quote.json"
    - ".planning/verification/schemas/iol-client/get-historical-quotes.json"
    - ".planning/verification/schemas/iol-client/get-instruments.json"
    - ".planning/verification/schemas/iol-client/get-instruments-by-type.json"
  modified:
    - "packages/iol-client/tests/test_client.py (+49 líneas, sección Verified live Phase 3)"
    - "packages/iol-client/tests/test_async_client.py (+49 líneas, espejo async)"
decisions:
  - "F-01 (SHAPE, get_quote sin clave `simbolo`) queda OPEN per directiva del checkpoint humano (D-04 mirror). Es asunción incorrecta del driver, no bug del cliente — el wrapper `iol_client.get_quote()` devuelve el payload crudo y el server simplemente no incluye `simbolo` en la respuesta (input ≠ output). El finding queda como evidencia honesta de la asunción equivocada en `_ASSUMED_QUOTE_FIELDS` del driver. Si se quiere refinar, Plan 03-04 opportunistic puede relajar la asunción."
  - "VERIFY_IOL_BAD_CREDS=1 NO se ejecutó en este live run baseline. probe_auth_401 emite SKIPPED, registrado en el SUMMARY del findings file. El usuario puede correrlo manualmente más tarde para promover el finding EXPECTED de IOL-05."
  - "El header del findings file dice `# Findings: iol-client-client` (doble `-client`) — cosmético, viene del helper `write_findings(pkg)` con prefijo. No se considera bug bloqueante para Phase 3; correcciones cosméticas pueden ir a una fase futura."
  - "Single-shot live run: el driver corrió 1 sola vez exit 0. Sin retries (Pitfall 9 lockout risk). Si una segunda corrida fuera necesaria, sería un evento separado con su propia decisión humana."
live-run:
  driver: "uv run --package iol-client python main_iol.py"
  target: "https://api.invertironline.com"
  timestamp: "2026-06-06T14:56:08.192584+00:00"
  exit_code: 0
  summary:
    pass: 13
    fail: 0
    skipped: 1
    finding: 1
  probes:
    - "login_sync: PASS (_token cached, _refresh_token cached)"
    - "login_async: PASS (_token cached, _refresh_token cached)"
    - "get_quote_sync: PASS (ultimoPrecio=7215.0)"
    - "get_quote_async: PASS (ultimoPrecio=7215.0)"
    - "get_historical_quotes_sync: PASS (len=2502)"
    - "get_historical_quotes_async: PASS (len=2502)"
    - "get_instruments_sync: PASS (type=list)"
    - "get_instruments_async: PASS (type=list)"
    - "get_instruments_by_type_sync: PASS (sample acciones len=96; 6 InstrumentType OK)"
    - "get_instruments_by_type_async: PASS (sample acciones len=96)"
    - "parity_sync_async: PASS (4 endpoints, drift=0)"
    - "field_type_map: FINDING F-01 OPEN — get_quote payload no incluye `simbolo`"
    - "schema_snapshot: PASS (4 written, 0 matched, 0 skipped)"
    - "refresh_token: PASS (refresh path verified — token rotated; _refresh_token=rotated)"
    - "auth_401: SKIPPED (opt-in via VERIFY_IOL_BAD_CREDS=1)"
verification:
  ruff_check: "All checks passed"
  ruff_format: "8 files already formatted"
  mypy_strict: "Success: no issues found in 8 source files"
  pytest: "195 passed, 1 deselected — 0 regresiones"
risks-deferred:
  - "F-01 finding queda OPEN — promoverlo a EXPECTED/NO-FIX en una sesión futura o relajarlo en Plan 03-04 opportunistic."
  - "probe_auth_401 nunca se ejercitó en vivo (opt-in deliberado). Plan 03-04 opportunistic podría correrlo si el equipo quiere registrar el EXPECTED de IOL-05."
  - "Header cosmético del findings file (`iol-client-client`) — corrección menor, candidato para fase posterior."
requirements-completed:
  - "IOL-01: login flow verificado in-vivo (sync + async)"
  - "IOL-02: URL exacta de get_quote verificada in-vivo + mocked Verified-live test"
  - "IOL-03: field→type map ejercitado para los 4 endpoints sin discrepancias críticas (F-01 es asunción del driver)"
  - "IOL-04: envelope `titulos` capturado + invariantes mockeados en Verified-live (URL + envelope + numeric type + date format)"
  - "IOL-05: probe_auth_401 implementado opt-in (no ejercitado en este run baseline; Pitfall 9 risk-aware)"
  - "IOL-06: parity sync↔async ejercitada — 0 drift en los 4 endpoints"
  - "IOL-07: fix verificado in-vivo via probe_refresh_token (token rotated; cubierto por Plan 03-01 + 03-02 in-cycle)"
artifacts-committed:
  - ".planning/verification/iol-client-findings.md (1095 B)"
  - ".planning/verification/schemas/iol-client/get-quote.json (840 B)"
  - ".planning/verification/schemas/iol-client/get-historical-quotes.json (1029 B)"
  - ".planning/verification/schemas/iol-client/get-instruments.json (337 B)"
  - ".planning/verification/schemas/iol-client/get-instruments-by-type.json (1114 B)"
checkpoint-resolution: "Approved — commit tal cual con F-01 OPEN (user choice del checkpoint humano de Task 3.2)"
---

# Plan 03-03: IOL Live Run + Verified-live Tests + Baseline Commit

## Resumen

Cierre de Phase 3 (`iol-verification`). El driver de Plan 03-02 se invocó una única vez contra `api.invertironline.com` con credenciales reales y produjo el baseline DRIFT-01 mirror para `iol-client`: 4 schema snapshots con envelope D-21 + findings file con esqueleto y un único finding (F-01 OPEN, asunción del driver). Antes del live run, los 4 invariantes IOL-04 quedaron mockeados en `# ------ Verified live (Phase 3) ------` (sync + async espejado, D-IOL-21). El checkpoint humano (Task 3.2) verificó los 5 artefactos antes del commit.

## Self-Check: PASS

- [x] Sección Verified-live agregada a test_client.py + test_async_client.py (commit ca3e837)
- [x] Sección `# ------ Regressions ------` de Plan 03-01 preservada intacta
- [x] Driver corrido exactamente una vez contra api.invertironline.com (no retries — Pitfall 9)
- [x] 5 artefactos commiteados al repo (commit 620b2f9)
- [x] Pitfall 2 envelope `titulos` capturado en get-instruments-by-type.json
- [x] D-IOL-7/22 safe_print con secrets dinámicos verificado (live stdout no expuso credenciales)
- [x] D-IOL-11 refresh_token in-vivo verificación: PASS (token rotated)
- [x] Checkpoint humano Task 3.2 cumplido (D-04 mirror)
- [x] mypy strict + ruff check + ruff format + pytest TODOS verdes
- [x] No regresiones — 195 passed (+6 vs 189 baseline antes de wave 3)
- [x] `.env` NO commiteado al repo (verificado vía `git check-ignore`)
- [x] STATE.md / ROADMAP.md no tocados desde el worktree (orchestrator-owned)

## Live-Run Outcome (verbatim driver stdout)

```
PROBE login_sync: PASS _token cached, _refresh_token=<cached>
PROBE login_async: PASS _token cached, _refresh_token=<cached>
PROBE get_quote_sync: PASS ultimoPrecio=7215.0
PROBE get_quote_async: PASS ultimoPrecio=7215.0
PROBE get_historical_quotes_sync: PASS len=2502
PROBE get_historical_quotes_async: PASS len=2502
PROBE get_instruments_sync: PASS type=list
PROBE get_instruments_async: PASS type=list
PROBE get_instruments_by_type_sync: PASS sample=acciones len=96; 6 types OK
PROBE get_instruments_by_type_async: PASS sample=acciones len=96
PROBE parity_sync_async: PASS 4 endpoints, drift=0, skipped=0
PROBE field_type_map: FINDING F-01 (OPEN)
PROBE schema_snapshot: PASS written=['get_quote', 'get_historical_quotes', 'get_instruments', 'get_instruments_by_type'] matched=[] skipped=[]
PROBE refresh_token: PASS refresh path verified — token rotated, _refresh_token=rotated
PROBE auth_401: SKIPPED (opt-in via VERIFY_IOL_BAD_CREDS=1)
SUMMARY: PASS=13 FAIL=0 SKIPPED=1 FINDING=1
```

## F-01 Disposition

`F-01 — missing assumed key 'simbolo' in get_quote` queda **OPEN** per dirección del checkpoint humano (Approved — commit tal cual). Justificación documentada en el SUMMARY: el wrapper `iol_client.get_quote()` devuelve el payload crudo sin asumir nada; el server simplemente no incluye `simbolo` en la respuesta (es el input). La asunción incorrecta vive en `_ASSUMED_QUOTE_FIELDS` del driver (`main_iol.py`), no en el cliente. No requiere fix del cliente. Un Plan 03-04 opportunistic podría refinar el `_ASSUMED_QUOTE_FIELDS` del driver — fuera del alcance de Phase 3.

## Commits

| SHA | Subject | Files |
|-----|---------|-------|
| ca3e837 | `test(03-03): add Verified live (Phase 3) invariants for IOL-02 + IOL-04 (D-IOL-21)` | test_client.py (+49), test_async_client.py (+49) |
| 620b2f9 | `feat(03-03): commit IOL live-run baseline — findings + 4 schema snapshots (DRIFT-01 mirror)` | iol-client-findings.md, 4 × *.json |

(El commit del SUMMARY.md se aplica como parte del cierre del plan.)

## Phase 3 Cierre

Con este plan, Phase 3 cumple:

- **IOL-01..07** verificado in-vivo (IOL-07 verificado in-cycle Plan 03-01 + 03-02; IOL-05 implementado opt-in pero no ejercitado en este run)
- **DRIFT-01 mirror** cumplido con 4 schemas committeados
- **D-IOL-21** Verified-live invariants espejados (4 sync + 4 async)
- **Pitfall 2 envelope** confirmado en wire format
- **Convención dual sync/async** mantenida en todo el plan

Phase 3 → próxima fase 4 (Higyrus verification).
