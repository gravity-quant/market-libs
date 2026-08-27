---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
artifact: red-baseline
measured_at_sha: 0a9fdae36519d6231dfb27c4ee538ec35f658862
measured_on: 2026-08-26
command: "uv run pytest verification -q --tb=no -rfE"
---

# Phase 33 — Red baseline de `verification/` (P-13)

`verification/` **nunca ha corrido en CI**: el job `test` pasa una ruta explícita
(`pytest packages/${{ matrix.package }}`) que anula el `testpaths` de
`pyproject.toml`. Su estado rojo de hoy es **rot pre-existente**, no una regresión
de la Phase 33.

Este artefacto existe para que esa distinción sea mecánica y no una cuestión de
memoria: cualquier corrida futura de `verification/` se compara contra ESTOS
números y ESTA lista de node ids, nunca contra cero. Sin la línea base, una
regresión introducida por esta fase quedaría escondida entre 19 fallas que ya
estaban ahí — un falso limpio, exactamente lo que este milestone existe para
eliminar.

## Línea de resumen exacta

```
19 failed, 368 passed, 19 errors in 830.31s (0:13:50)
```

Medido el **2026-08-26** sobre el SHA **`0a9fdae`**
(`0a9fdae36519d6231dfb27c4ee538ec35f658862`), con el commit de tests de la Task 3
de este plan ya aplicado.

> **Sobre los 368 passed:** `33-RESEARCH.md` (P-13) y `33-VALIDATION.md` reportan
> `19 failed, 362 passed, 19 errors in 828s` como la medición previa. El delta de
> **+6 passed** son exactamente los seis casos nuevos de
> `verification/test_divergences.py` (cinco nombres, uno de ellos parametrizado
> ×2) que este plan agrega. **Los conteos de falla y de error no se movieron:
> 19 y 19 antes, 19 y 19 después.** Ése es el número que importa acá.

## Causa raíz dominante — un solo defecto explica el 100% del rojo

Las 19 fallas y los 19 errores se reparten en **dos archivos**, y ambos tienen la
**misma** causa raíz:

| Archivo | FAILED | ERROR |
|---|---:|---:|
| `verification/test_matriz_sweep_snapshot.py` | 17 | 17 |
| `verification/test_main_matriz_login_fail_uniformity.py` | 2 | 2 |
| **Total** | **19** | **19** |

Los dos llaman a los probes de `main_matriz.py` **directamente y sin argumentos**:

```
TypeError: probe_get_segments() missing 1 required positional argument: 'client'
TypeError: probe_login_sync() missing 1 required positional argument: 'client'
```

Los probes de `main_matriz.py` reciben un `client` **desde la migración de drivers
de la Phase 15** (REFAC-05, un único `Client` construido en `main()` y pasado como
parámetro a cada probe). Estos dos archivos de test se quedaron en la firma
pre-migración. Nunca enrojecieron nada porque `verification/` no corre en CI.

Cada caso cuenta **dos veces** — una FAILED y una ERROR — porque el `TypeError`
impide que la request llegue a dispararse y, en el teardown, `pytest_httpx`
asevera que toda respuesta mockeada fue efectivamente pedida:

```
AssertionError: The following responses are mocked but not requested:
  - Match any request on https://api.test/rest/segment/all
```

## Estos dos archivos son el CANARIO del refactor de esta misma fase

`verification/test_matriz_sweep_snapshot.py` y
`verification/test_main_matriz_login_fail_uniformity.py` invocan a los probes
**directamente**, no a través de `main()`. Eso los vuelve el detector natural de
cualquier cambio en la firma o en el envoltorio de un probe de matriz — que es
precisamente lo que hacen los planes **33-02** y **33-03** al aplicar el decorador
`probe_context` sobre `main_matriz.py`.

**Obligación explícita para 33-02 y 33-03:** re-correr

```
uv run pytest verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py -q --tb=no -rfE
```

después de aplicar el decorador y **comparar contra 17/17 y 2/2**. Un número
distinto NO es "más del rojo que ya estaba": es señal de que el decorador cambió
algo observable en la superficie del probe. `functools.wraps` preserva `__name__`
y `__wrapped__`, pero no vuelve a un wrapper `*args, **kwargs` indistinguible de
la función original ante una llamada mal formada.

## La reparación NO está en el scope de LIVE-TYP-01

Reparar este rot **no** es parte de LIVE-TYP-01 y este plan deliberadamente no lo
intenta:

- El criterio de aceptación de la Phase 33 es el censo de divergencias en vivo,
  la evidencia de `Literal` y el cierre de ciclo — nada de eso depende de que
  estos 19 casos pasen.
- Arreglarlos exige tocar `main_matriz.py` y sus tests en el mismo ciclo en que
  los planes 33-02/33-03 ya los están tocando por otro motivo, y mezclar las dos
  cosas haría imposible atribuir un cambio de conteo a una causa u otra —
  destruyendo justamente el valor de canario descrito arriba.
- `33-VALIDATION.md` lo dice de frente: *"Do not gate on an unqualified
  `uv run pytest` or a full `pytest verification` run"*. Ninguna task de la
  Phase 33 gatea sobre una corrida completa de `verification/`; se gatea sobre
  `pytest packages` (lo que CI realmente exige) más los archivos puntuales de
  `verification/` que esta fase posee.

## Destino nombrado de la reparación

Diferir sin destino no es una opción disponible (P-03). El destino es:

**`HARN-VERIF-01` — reparar las firmas de probe stale de `main_matriz.py` en
`verification/`**, archivado en `.planning/ROADMAP.md` § Backlog →
*"Deferred to v1.7+ (from v1.6)"*, con paquete (`matriz-client`), archivos
(`verification/test_matriz_sweep_snapshot.py`,
`verification/test_main_matriz_login_fail_uniformity.py`) y causa raíz
(parámetro `client` de la migración REFAC-05 de la Phase 15) registrados.

**Por qué un ítem de backlog y no una fase de v1.6:** ninguna de las dos fases que
quedan puede ser el dueño honesto. La Phase 33 es LIVE-TYP-01 y P-13 excluye esta
reparación de su scope por escrito; la Phase 34 es PUB-TYP-01 (releases por
paquete) y meter una reparación de harness en el PR de release repetiría
exactamente el error que la Phase 28 ya rechazó una vez por expandir el diff
(ver el ítem D-16 del mismo backlog). Nombrar una fase que no puede recibirlo
sería una ruta falsa; el ítem de backlog es un destino nombrado, greppable y real.

## Gap adicional medido en este plan — `mypy` sobre `verification/`

`uv run mypy verification` reporta **43 errores en 8 archivos** en este mismo SHA.
Es rot pre-existente de la misma especie: `[tool.mypy] files` sólo lista las seis
raíces `packages/*/src` y el hook de pre-commit está scopeado a
`^packages/.*/src/`, así que `verification/` nunca fue type-checkeado. Los dos
archivos nuevos de este plan (`verification/divergences.py` y
`verification/test_divergences.py`) aportan **0** de esos 43 — verificado por
`uv run mypy verification 2>&1 | grep -cE "^verification/(divergences|test_divergences)\.py"`.
Mismo destino: `HARN-VERIF-01`.

## Lista completa `-rfE` de node ids (19 FAILED + 19 ERROR)

- `FAILED verification/test_main_matriz_login_fail_uniformity.py::test_probe_login_sync_returns_FINDING_on_authentication_error`
- `FAILED verification/test_main_matriz_login_fail_uniformity.py::test_probe_login_sync_returns_FINDING_on_unexpected_exception`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_segments-https://api.test/rest/segment/all-response_json0-PASS-1 segments]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_all_instruments-https://api.test/rest/instruments/all-response_json1-PASS-1 instruments]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_instruments_details-https://api.test/rest/instruments/details-response_json2-PASS-1 instrument details]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_instrument_detail-https://api.test/rest/instruments/detail?symbol=DLR/DIC23&marketId=ROFX-response_json3-PASS-symbol=DLR/DIC23]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_instruments_by_cfi_ESXXXX-https://api.test/rest/instruments/byCFICode?CFICode=ESXXXX-response_json4-PASS-1 ESXXXX instruments]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_instruments_by_segment-https://api.test/rest/instruments/bySegment?MarketSegmentID=DDF&MarketID=ROFX-response_json5-PASS-segment=DDF]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_market_data-https://api.test/rest/marketdata/get?marketId=ROFX&symbol=DLR/DIC23&entries=BI%2COF%2CLA%2COP%2CCL%2CSE%2COI-response_json6-PASS-symbol=DLR/DIC23]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_trades-https://api.test/rest/data/getTrades-response_json7-PASS-1 trades]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_active_orders-https://api.test/rest/order/actives?accountId=TEST-ACCT-01-response_json8-PASS-1 active orders]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_filled_orders-https://api.test/rest/order/filleds?accountId=TEST-ACCT-01-response_json9-PASS-2 filled orders]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_all_orders-https://api.test/rest/order/all?accountId=TEST-ACCT-01-response_json10-PASS-0 total orders]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_order_status-https://api.test/rest/order/id?clOrdId=cl-ord-001&proprietary=PBCP-response_json11-PASS-clOrdId=cl-ord-001]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_order_history-https://api.test/rest/order/allById?clOrdId=cl-ord-001&proprietary=PBCP-response_json12-PASS-1 history rows]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_order_by_exec_id-https://api.test/rest/order/byExecId?execId=exec-001-response_json13-PASS-execId=exec-001]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_positions-https://api.test/rest/risk/position/getPositions/TEST-ACCT-01-response_json14-PASS-1 positions]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_detailed_positions-https://api.test/rest/risk/detailedPosition/TEST-ACCT-01-response_json15-PASS-account received]`
- `FAILED verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_account_report-https://api.test/rest/risk/accountReport/TEST-ACCT-01-response_json16-PASS-accountName received]`
- `ERROR verification/test_main_matriz_login_fail_uniformity.py::test_probe_login_sync_returns_FINDING_on_authentication_error`
- `ERROR verification/test_main_matriz_login_fail_uniformity.py::test_probe_login_sync_returns_FINDING_on_unexpected_exception`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_segments-https://api.test/rest/segment/all-response_json0-PASS-1 segments]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_all_instruments-https://api.test/rest/instruments/all-response_json1-PASS-1 instruments]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_instruments_details-https://api.test/rest/instruments/details-response_json2-PASS-1 instrument details]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_instrument_detail-https://api.test/rest/instruments/detail?symbol=DLR/DIC23&marketId=ROFX-response_json3-PASS-symbol=DLR/DIC23]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_instruments_by_cfi_ESXXXX-https://api.test/rest/instruments/byCFICode?CFICode=ESXXXX-response_json4-PASS-1 ESXXXX instruments]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_instruments_by_segment-https://api.test/rest/instruments/bySegment?MarketSegmentID=DDF&MarketID=ROFX-response_json5-PASS-segment=DDF]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_market_data-https://api.test/rest/marketdata/get?marketId=ROFX&symbol=DLR/DIC23&entries=BI%2COF%2CLA%2COP%2CCL%2CSE%2COI-response_json6-PASS-symbol=DLR/DIC23]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_trades-https://api.test/rest/data/getTrades-response_json7-PASS-1 trades]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_active_orders-https://api.test/rest/order/actives?accountId=TEST-ACCT-01-response_json8-PASS-1 active orders]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_filled_orders-https://api.test/rest/order/filleds?accountId=TEST-ACCT-01-response_json9-PASS-2 filled orders]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_all_orders-https://api.test/rest/order/all?accountId=TEST-ACCT-01-response_json10-PASS-0 total orders]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_order_status-https://api.test/rest/order/id?clOrdId=cl-ord-001&proprietary=PBCP-response_json11-PASS-clOrdId=cl-ord-001]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_order_history-https://api.test/rest/order/allById?clOrdId=cl-ord-001&proprietary=PBCP-response_json12-PASS-1 history rows]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_order_by_exec_id-https://api.test/rest/order/byExecId?execId=exec-001-response_json13-PASS-execId=exec-001]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_positions-https://api.test/rest/risk/position/getPositions/TEST-ACCT-01-response_json14-PASS-1 positions]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_detailed_positions-https://api.test/rest/risk/detailedPosition/TEST-ACCT-01-response_json15-PASS-account received]`
- `ERROR verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_account_report-https://api.test/rest/risk/accountReport/TEST-ACCT-01-response_json16-PASS-accountName received]`
