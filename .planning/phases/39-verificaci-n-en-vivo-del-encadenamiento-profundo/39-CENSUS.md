# 39-CENSUS.md — el censo en vivo de la Fase 39, contrastado contra la Fase 33 y contra el piso ratificado

**Esta corrida reporta menos divergencias que el piso ratificado, y ése es exactamente el
resultado que más fácil se lee mal.** Un censo que baja de 14 a 7 sin decir por qué es el
artefacto que esta fase existe para no producir: la política Null Object de la Phase 35 dejó de
**registrar** un subconjunto de divergencias, y si ese subconjunto no se resta explícitamente,
cada triple que la política silenció se acredita en silencio a trabajo de calidad que nadie hizo
(ROADMAP Phase 39 criterio 4 / SC-4). Por eso este documento enumera la **población completa** —
no sólo las violaciones—, reporta cada cero **por enumeración con su causa nombrada**, y parte la
baja en dos columnas separadas y sumables antes de reportar cualquier total.

La otra forma de fallar acá no es sub-medir: es **re-derivar una unidad ligeramente distinta de
la del artefacto contra el que hay que comparar**, produciendo un número que parece un resultado
y es un error de traducción. La sección `## Unidad y método` existe para cerrar esa puerta antes
de la primera resta.

---

## Unidad y método

**La unidad de este censo es la 4-tupla distinta `(slug, model, field_path, kind)` tomada de
`DivergenceHandler.seen`** (`verification/divergences.py:136,165`). Es literalmente la unidad que
declaró `33-CENSUS.md` (`## Method`, líneas 13-17) y literalmente la unidad que declaró
`35-RETIRED-TRIPLES.md` (`## Counting unit`, líneas 3-6). La identidad es deliberada: la Fase 39
hace una **diferencia de conjuntos**, nunca una traducción.

**Las dos unidades que este censo rechaza, y por qué:**

| Unidad rechazada | Por qué no es comparable |
|---|---|
| El `FINDING=N` de la línea `SUMMARY` del driver | Cuenta **probes** cuyo `ProbeResult.status` es `FINDING`, no divergencias. matriz reporta `FINDING=7` y `DIVERGENCES=7` en esta corrida por coincidencia numérica, no por identidad de unidad (`33-CENSUS.md:28-30`). |
| El conteo crudo de bloques `### F-` del findings-file | El título embebe la superficie (`[sync]` / `[async]`), así que la identidad de dedupe cross-run es de seis componentes y un mismo triple se escribe **una vez por superficie** — el factor ~2× que `33-CENSUS.md:21-27` documentó. Además el archivo es append-only y arrastra findings escritos a mano en fases anteriores, que el walker nunca emitió. |

### Las dos costuras y su acuerdo

**Costura 1 — los sobres de evidencia de corrida.** `.planning/verification/run-evidence/<slug>.json`,
escritos por `verification/run_evidence.py` con `triples=sorted(handler.seen)`. Comando ejecutado y
salida verbatim:

```
$ ls .planning/verification/run-evidence/
ambito-financiero-client.json
higyrus-client.json
iol-client.json
matriz-client.json

$ uv run --frozen python -c "import json,pathlib,sys; ps=sorted(pathlib.Path('.planning/verification/run-evidence').glob('*.json')); [print(p.name, json.loads(p.read_text())['n_triples'], json.loads(p.read_text())['probes_executed']) for p in ps]; sys.exit(0 if ps else 1)"
ambito-financiero-client.json 0 7
higyrus-client.json 0 0
iol-client.json 0 15
matriz-client.json 7 50
$ echo $?
0
```

**Costura 2 — parseo de títulos `SHAPE` del ledger.** Los títulos que emite
`DivergenceHandler.emit` tienen formato fijo
(`verification/divergences.py:176` — `f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]"`),
así que son parseables y deduplicables por `(model, field_path, kind)`. Ésta es la costura con la
que se construyó el censo de la Fase 33, y por lo tanto la que hace comparables los dos artefactos.

| Paquete | Costura 1 (`handler.seen`) | Costura 2 (títulos `SHAPE` deduplicados) | ¿Acuerdan? |
|---|---:|---:|---|
| `ambito-financiero-client` | **0** | **0** | sí — 1 bloque en el ledger, clase `ANTI-BOT`, cero bloques `SHAPE` |
| `higyrus-client` | **0** (SKIPPED, 0 probes) | **0** | sí — el único bloque `SHAPE` es `F-01`, título escrito a mano en la Phase 4, fuera de la población del walker |
| `iol-client` | **0** | **0** | sí — el único bloque `SHAPE` es `F-01`, título escrito a mano en la Phase 3, fuera de la población del walker |
| `matriz-client` | **7** | **9** | **no — delta de +2, explicado abajo** |

**La discrepancia de matriz, con su causa, antes de seguir.** Los dos triples que la costura 2 ve
y la costura 1 no son `(Instrument, .marketId, extra)` y `(Instrument, .symbol, extra)` —
`F-43` y `F-44`, ambos con status `FIXED`. Se emitieron en el pase **pre-fix** de esta misma
corrida autoritativa; el sobre de evidencia se escribió **post-fix**
(`captured_at: 2026-08-30T02:49:48`), después de que `_core._normalize_instrument_element`
aterrizara. El ledger es append-only y conserva la emisión; el sobre es una foto puntual y ya no
la contiene. **Ninguna de las dos costuras está mal: el delta ES el fix in-cycle**, y se contabiliza
como tal en la columna de corrección real más abajo. Es la lectura que la corrida documenta
(`39-07-SUMMARY.md`: `DIVERGENCES=9` → post-fix `DIVERGENCES=7`).

**Segunda observación de costura, de forma y no de conteo — el factor ~2× no se materializó.**
El ledger de matriz contiene **9 bloques `SHAPE` de título mecánico para 9 triples, los 9 con
`[async]`** y ninguno con `[sync]`; verificado también contra el historial (`git grep -c` sobre
`3280cd2`, `19f8265` y `eeefe73` devuelve `9` en los tres). El factor observado es **1×**, no el
~2× que `33-CENSUS.md:21-27` documentó. Esto **no mueve la aritmética** —la unidad del censo es
`handler.seen`, que no lleva superficie— pero un lector futuro que aplique la conversión ~2× de la
Fase 33 al ledger de matriz obtendría un número equivocado. Queda declarado como asimetría medida,
con causa **no determinada en esta fase** y destino nombrado `HARN-VERIF-01` (deuda de harness,
`39-…/deferred-items.md`). No se inventa una causa para cerrarla.

**Los 22 bloques `SHAPE` de matriz que la costura 2 no parsea no son una pérdida.** Son títulos
escritos por el probe `field_type_map` (`main_matriz.py:1628`), con formato propio
(`.instrument_detail.securityId: wire emite, model ignora (info)`), y por definición no pertenecen
a la población del walker. La costura 2 está restringida a títulos emitidos por el walker; eso es
alcance declarado, no discrepancia.

---

## Alcance y fuera de alcance

Cuatro paquetes medidos. Para cada excluido, **dónde** se audita en su lugar — un fuera-de-alcance
sin destino no es una exclusión, es un agujero.

| Paquete | En alcance | Dónde se audita | Estado |
|---|---|---|---|
| `iol-client` | **sí** | esta fase | RAN |
| `higyrus-client` | **sí** | esta fase | SKIPPED — `LIVE-HIGY-33` |
| `matriz-client` | **sí** | esta fase | RAN (venue bbsa) |
| `ambito-financiero-client` | **sí** | esta fase | RAN |
| `market-data-client` | no | **Phase 36** (D-07). `main_market_data.py` está ausente de `git diff --name-only` de toda la fase, y su ledger quedó byte-idéntico | cerrado en Phase 36 |
| `wallets-client` | no | **Phase 38**, `38-CENSUS.md` — stub: cero funciones de dominio, cero clases de modelo, exención de decoder de la Phase 29, sin `_decode.py` | cerrado en Phase 38 |

---

## Corrida: clasificación por paquete

Un renglón por paquete con clasificación, causa medida, destino nombrado y la línea `SUMMARY`
transcrita verbatim. **El conteo de probes distinto de cero es la evidencia positiva de que el
driver corrió**: un driver que nunca corrió mostraría los mismos ceros de divergencias **y** un
conteo de probes en cero — el mismo argumento que hizo el test de cierre de ciclo de la Fase 33 al
transcribir la línea de ámbito palabra por palabra.

| Paquete | Clasificación | Línea `SUMMARY` verbatim | Probes | `HANDLER_ERRORS` | Causa medida / destino |
|---|---|---|---:|---:|---|
| `iol-client` | **RAN** | `SUMMARY: PASS=14 FAIL=0 SKIPPED=1 FINDING=0 DIVERGENCES=0 HANDLER_ERRORS=0` | 15 | **0** | Cero por inspección real; el canal quedó probado vivo en la Fase 33 (17 triples sintéticos) |
| `ambito-financiero-client` | **RAN** | `SUMMARY: PASS=6 FAIL=0 SKIPPED=1 FINDING=0 DIVERGENCES=0 HANDLER_ERRORS=0` | 7 | **0** | Cero por enumeración: el paquete declara cero clases de modelo (ver `## Ausencia medida de ámbito`) |
| `matriz-client` | **RAN** (venue bbsa) | `SUMMARY: PASS=39 FAIL=0 SKIPPED=4 FINDING=7 DIVERGENCES=9 HANDLER_ERRORS=0` → post-fix `DIVERGENCES=7` | 50 | **0** | Primer censo en vivo de matriz de todo el proyecto; `LIVE-MATZ-33` desbloqueado por la ampliación D-02 del allowlist a bbsa |
| `higyrus-client` | **SKIPPED** | `SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-33` | **0** | n/a | Host del vendor irresoluble por DNS, **re-sondeado en esta sesión**, no asumido. Destino `LIVE-HIGY-33` |

**El gate duro se cumplió: `HANDLER_ERRORS=0` en las tres corridas que produjeron `SUMMARY`.** Un
valor distinto de cero invalidaría el censo de esa corrida (`33-CENSUS.md:283-285`). El censo no se
construyó sobre un pipeline que falló en silencio.

---

## Contraste contra la Fase 33 y contra el piso ratificado

Con la columna de unidad nombrada en **cada** término, y con la resta hecha en el orden que manda
`35-RETIRED-TRIPLES.md` (`## What a NON-balancing subtraction means`): **primero** el error de
columna de unidad, **después** la hipótesis de hallazgo real. El término medio de matriz está
expresado en las dos columnas a la vez (6 registros / 5 triples distintos) y leer la equivocada
rompe la suma en silencio.

| Paquete | Piso 29-SIZING (registros) | Piso equiv. (triples distintos) | Censo Fase 33 | Censo Fase 39 (en vivo) | Columna que se usa |
|---|---|---|---|---:|---|
| `ambito-financiero-client` | **N/A — no cero** | N/A | 0 (afirmado, no inferido) | **0** | ninguna — no hay piso del que restar |
| `iol-client` | **N/A — no cero** (`29-SIZING.md:166`) | N/A | 0 (inspección real) | **0** | ninguna — no hay piso del que restar |
| `higyrus-client` | ≥ 22 | 22 | SKIPPED — sin medición | **UNMEASURED** — SKIPPED, 0 probes | ambas, y coinciden (tres archivos, tres modelos disjuntos) |
| `matriz-client` | ≥ 24 | 14 | **UNMEASURED** — no existe censo de la Fase 33 | **7** | ambas, y **DIFIEREN** — ver la resta abajo |

### Los dos términos que NO son derivables — declarados `UNMEASURED`, nunca plegados en "corregido"

**`UNMEASURED` #1 — el término medio de retiro de las Fases 36 y 37 no existe como artefacto.**
Verificado por listado de directorio: no hay `36-RETIRED-*.md` ni `37-RETIRED-*.md`. El ledger de
la Phase 35 acota su alcance a las clases del commit `242b9f3` y desestima explícitamente los
eslabones nuevos de 36/37/38 como *"contabilidad de sus propias fases"*
(`35-RETIRED-TRIPLES.md`, `## Two limits with named destinations`). La Fase 38 pagó su deuda con su
addendum; **36 y 37 no**. Lo derivable y lo no derivable, separados:

| Fase | Roster de eslabones nuevos (derivable de CONTEXT) | Triples retirados (¿derivable?) |
|---|---|---|
| 36 (`market-data`) | `MarketDataSnapshot.market_data: MarketDataEntries`, `MarketDataSnapshot.entries: list[str]`, `MarketDataEntries.BI`/`.OF: list[BookLevel]`, `.LA`/`.SE`/`.CL`/`.OI: EntryValue`, `LatestRequest.entries: list[str]` (D-01/D-04/D-06 de `36-CONTEXT.md`) | **`UNMEASURED`** — `market-data-client` está fuera del alcance de esta fase por D-07 y no corrió; no hay censo en vivo con el cual intersecar |
| 37 (`matriz`) | `InstrumentDetail.tickPriceRanges: dict[str, TickPriceRange]`, `DetailedPosition.report: dict[str, dict[str, InstrumentPositionReport]]`, `AccountReport.detailedAccountReports: dict[str, DetailedAccountReport]` (D-05/D-07 de `37-CONTEXT.md`; `AccountReport.portfolio` queda hoja escalar por D-02 y no es eslabón) | **0 medido en esta corrida** — los tres se ejercitaron en vivo (`get_instrument_detail`, `get_detailed_positions`, `get_account_report`, los tres en `PASS`) y ninguno aparece entre los 7 triples medidos. Pero el **estado previo** es `UNMEASURED`: matriz no tiene censo de la Fase 33 con el cual comparar, así que no es decidible si estaban emitiendo antes |

**Destino nombrado:** `NOBJ-RETIRE-3637` — etiqueta de bookkeeping siguiendo la convención ya
vigente (`LIVE-HIGY-33` / `LIVE-MATZ-33` / `LIVE-NOBJ-01` / `LIVE-POS-39`), a saldar con un
addendum al ledger de la Phase 35 con la misma forma que el de la Fase 38, en el cierre del
milestone v1.7. **No es una decisión nueva de alcance**: es el registro de una deuda que ya
existía y que esta fase encuentra, no crea.

**`UNMEASURED` #2 — matriz no tiene censo de la Fase 33, así que su resta contra la Fase 33 no es
computable.** La Fase 33 registró matriz `SKIPPED — base URL fuera de política` (el assert
D-MATZ-33 de `main_matriz.py`, sin override, exit 1), y por lo tanto **matriz no aportó ni un
triple al censo de la Fase 33** (`33-CENSUS.md:71,118-137`). Esta fase produce el **primer censo en
vivo de matriz de todo el proyecto**. El único contraste disponible es el piso ratificado de
`29-SIZING.md`, y ese contraste lleva un caveat que no se puede omitir:

> **Caveat de venue.** El piso de matriz se midió contra un corpus de **remarkets** (capturas
> 2026-06-10, filas 36-43 de la tabla de corpus de `29-SIZING.md`). Esta corrida se ejecutó contra
> el venue **bbsa** (`LIVE-MATZ-33` desbloqueado por la ampliación D-02 del allowlist). Son dos
> venues distintos del mismo vendor. La comparación se hace igual porque es el único contraste que
> existe, pero **se declara explícitamente y no se hace en silencio**. El contra-argumento medido
> que la sostiene: el único defecto de forma que esta corrida encontró (F-43/F-44) se confirmó en
> los **dos** venues del allowlist —baseline remarkets 2026-06-10 y captura bbsa 2026-08-30—, así
> que ese hallazgo al menos no es deriva entre venues. Los 7 triples restantes no tienen esa
> doble confirmación.

### La resta de matriz, término por término, con la columna nombrada

Piso de matriz descompuesto fila por fila desde la tabla de corpus de `29-SIZING.md`
(filas 38/39 `Instrument`: `extra 2 + non_dict 1` cada una; filas 40/41 `InstrumentDetail`:
`extra 7` cada una; fila 42 `MarketDataSnapshot`: `non_dict 4`):

| Término | Columna de registros | Columna de triples distintos |
|---|---:|---:|
| Piso ratificado `29-SIZING.md` | **24** | **14** |
| − retirados por colapso de política (NOBJ-02, `35-RETIRED-TRIPLES.md` `## Expected subtraction`) | −6 | −5 |
| = línea base esperada post-Phase-35 | 18 | **9** |
| − cerrados por corrección real en esta fase (F-43/F-44, `_core._normalize_instrument_element`) | −4 | −2 |
| = **esperado en vivo** | **14** | **7** |
| **medido en vivo (`handler.seen`)** | *(el harness no produce esta columna)* | **7** |

**La resta cierra exacta en las dos columnas.** Los 14 registros esperados son los 7 `extra` de
`InstrumentDetail` × las 2 filas de corpus (40/41) — la misma conversión 7↔14 que
`33-CENSUS.md:51` documentó para esas filas. La columna de registros **no** se contrasta contra
una medición en vivo porque el harness no la produce: `handler.seen` es un conjunto de tuplas
distintas por construcción. Contrastar los 7 triples medidos contra el piso de 24 registros
fabricaría un "por debajo del piso" que es puro error de unidad — el falso negativo que
`33-CENSUS.md:55-59` prohíbe.

---

## El split que SC-4 exige (D-11): colapso de política vs. corrección real

Dos columnas separadas y sumables, más una tercera para lo que sigue abierto. **Ninguna triple
queda sin columna.**

### matriz-client — las 14 triples del piso, cada una en exactamente una columna

| # | `model` + `field_path` | `kind` | Colapso de política (Phase 35 / NOBJ-02) | Corrección real | Sigue abierto |
|---|---|---|:--:|:--:|:--:|
| 1 | `Instrument.instrumentId` | missing (pre-WR-02: `non_dict`) | ✅ **S-3** | | |
| 2 | `MarketDataSnapshot.LA` | missing (pre-WR-02: `non_dict`) | ✅ **S-5** | | |
| 3 | `MarketDataSnapshot.SE` | missing (pre-WR-02: `non_dict`) | ✅ **S-5** | | |
| 4 | `MarketDataSnapshot.OI` | missing (pre-WR-02: `non_dict`) | ✅ **S-5** | | |
| 5 | `MarketDataSnapshot.CL` | missing (pre-WR-02: `non_dict`) | ✅ **S-5** | | |
| 6 | `Instrument.marketId` | extra | | ✅ **Phase 39 / 39-07** — `F-43`, `_core._normalize_instrument_element`, commits `5674da1` (RED) / `9453acc` (GREEN) | |
| 7 | `Instrument.symbol` | extra | | ✅ **Phase 39 / 39-07** — `F-44`, mismo fix, mismo sitio único, espejo sync/async por REFAC-03 | |
| 8 | `InstrumentDetail.securityId` | extra | | | ✅ `F-29` NO-FIX |
| 9 | `InstrumentDetail.securityIdSource` | extra | | | ✅ `F-30` NO-FIX |
| 10 | `InstrumentDetail.securityType` | extra | | | ✅ `F-31` NO-FIX |
| 11 | `InstrumentDetail.settlType` | extra | | | ✅ `F-32` NO-FIX |
| 12 | `InstrumentDetail.strike` | extra | | | ✅ `F-33` NO-FIX |
| 13 | `InstrumentDetail.symbol` | extra | | | ✅ `F-34` NO-FIX |
| 14 | `InstrumentDetail.underlying` | extra | | | ✅ `F-35` NO-FIX |
| | **Totales (triples distintos)** | | **5** | **2** | **7** |
| | **Totales (registros)** | | **6** | **4** | **14** |

Las 7 de la tercera columna son wire-superset tolerado por diseño: el vendor manda claves que el
modelo no declara, la política las reporta como `extra` no-fatal (lock 3/4), y quedan
**reportadas, no silenciadas**. El operador las firmó `NO-FIX` en el checkpoint de 39-07.

**Nota de `kind` (caveat cargante de la resta).** Las filas 1-5 llevan en `29-SIZING.md` la
etiqueta pre-WR-02 `non_dict` atribuida a la clase anidada, mientras el walker de hoy las
etiqueta `missing` sobre el modelo externo. Para esas cinco filas el 4-tuple del piso y el de hoy
difieren en **dos** componentes (`model` y `kind`), así que el emparejamiento se hizo sobre
`(slug, field_path)` y el `kind` se leyó de `35-RETIRED-TRIPLES.md`, no de `29-SIZING.md` — es
exactamente el procedimiento que ese ledger prescribe.

### higyrus-client — las 22 triples del piso, cada una en exactamente una columna

| Grupo | Triples | Colapso de política | Corrección real | Sigue abierto |
|---|---:|:--:|:--:|---|
| `Movimiento.idMovimientos` (`list[int]`) | 1 | ✅ NOBJ-02 | | |
| `Posicion.parking` (`list[Parking]`) | 1 | ✅ NOBJ-02 | | |
| `Movimiento` (8 hojas escalares restantes), `PosicionValuada` (11), `Posicion.disponibleAjustado` (1) | 20 | | **0 — no hay medición** | ✅ **`UNMEASURED`** — SKIPPED por DNS, destino **`LIVE-HIGY-33`** |
| **Total** | **22** | **2** | **0** | **20** |

Los 2 retirados por política son la predicción del ledger, **no una medición**: esta corrida no
pudo falsificarla porque higyrus no corrió. Se registra como predicción pendiente de verificación,
no como resultado. Los 20 restantes son `UNMEASURED`, no cero: un cero afirmaría limpieza que
ninguna medición respalda.

### iol-client — cero en las tres columnas, con la causa de cada cero

| Columna | Valor | Causa medida |
|---|---:|---|
| Colapso de política | **0** | `Cotizacion.puntas` y `Titulo.puntas` pasaron a no-`Optional` en la Phase 38, así que hoy toman las ramas de colapso NOBJ-02 en vez del early-return de `Union` — pero **no emitían antes y no emiten ahora**. La invariancia es el hallazgo (`35-RETIRED-TRIPLES.md` `## Phase 38 addendum` §2) |
| Corrección real | **0** | Ningún fix de iol en esta fase; la zona AUTO-GENERATED del ledger quedó byte-idéntica |
| Sigue abierto | **0 en la población del walker** | `DIVERGENCES=0` con 15 probes: cero por inspección, no por ausencia de observación. `F-01` se contabiliza aparte (ver `## Arrastre explícito`) |

### ambito-financiero-client y wallets-client

**0 por enumeración en las tres columnas.** Ninguno declara una sola clase de modelo, así que
ninguno tiene un campo no-`Optional` de tipo modelo o lista que la política pueda retirar, ni una
divergencia de forma que corregir. La ausencia está enumerada, no supuesta.

---

## Ausencia medida de ámbito (D-06)

`ambito_financiero_client` **no declara ninguna clase de modelo y exporta un roster vacío por
decisión deliberada de fases anteriores** (Phase 31 D-11, Phase 29 D-05), y **por eso** no hay
cadena de modelo que ejercitar en este paquete. Medido, no heredado:

```
$ grep -c '^class ' packages/ambito-financiero-client/src/ambito_financiero_client/models.py
0
$ wc -l packages/ambito-financiero-client/src/ambito_financiero_client/models.py
      27 packages/ambito-financiero-client/src/ambito_financiero_client/models.py
```

El módulo son 27 líneas de docstring más `__all__: list[str] = []`. El docstring declara la
ausencia como deliberada — *"Deliberately absent, and not an oversight: there is no `SafeModel`
base here and no import of `ambito_financiero_client._decode`"* — y esa declaración está asertada
por `verification/test_cycle_closure_phase33.py` (21 passed a este HEAD).

**No se inventó un modelo para tener algo que encadenar.** Hacerlo repetiría el anti-patrón que la
Phase 37 prohibió por escrito ("modelo inventado presentado como observado"). El endpoint único de
ámbito parsea un decimal en formato argentino directo a `float`; no hay sobre que modelar.

**Y sin embargo el resultado no es una ausencia de medición:** la línea `SUMMARY` de ámbito es
`SUMMARY: PASS=6 FAIL=0 SKIPPED=1 FINDING=0 DIVERGENCES=0 HANDLER_ERRORS=0` con **7 probes
ejecutados**. Cero divergencias con conteo de probes distinto de cero es un **resultado
estructural**: el paquete se ejercitó de punta a punta y no había nada que el walker pudiera
encontrar, porque no hay declaración contra la cual comparar el wire.

---

## Casos límite de D-12: qué mitad cubrió cada uno

**Ventana horaria de la corrida declarada: sábado 2026-08-29, 23:34 ART (2026-08-30 02:41 UTC) —
mercado ARG CERRADO**, fuera de toda sesión de negociación. Ningún número de esta corrida proviene
de una sesión de trading activa.

**El discriminador usado fue la guarda de antigüedad ya existente (D-MATZ-5), no una inferencia:**
`/rest/marketdata/get` devolvió las siete entradas (`BI,OF,LA,OP,CL,SE,OI`) en `null`, así que `LA`
no es un dict y la rama de antigüedad de `LA.date` **no se ejecutó**; el camino que aplicó fue el
de `LA` ausente/nula. Un `null` de mercado cerrado no se distingue de un error de modelado por
inspección — eso es el pitfall P-12 — y por eso el discriminador es la guarda existente y no una
lectura del reloj.

| Caso límite D-12 | `iol-client` | `higyrus-client` | `matriz-client` | `ambito-financiero-client` |
|---|---|---|---|---|
| **Mercado cerrado** | n/a — ninguna forma de respuesta depende de la sesión | **no producido** (SKIPPED, DNS) | **EN VIVO** — las 7 entradas en `null`; los 6 alias de `MarketDataSnapshot` se desreferenciaron `last=None bids=0 offers=0 settlement=None close=None oi=None`, idéntico en `client.py` y `aio.py`, sin una sola excepción | n/a — el endpoint es un scrape de FX, no una sesión de mercado |
| **Fila sin datos** | **MOCKED** — `test_instruments_by_type_missing_titulos_key_yields_no_rows` | **MOCKED** — `test_get_posiciones_populated_control` + degenerado | **EN VIVO** — `get_trades` → `[]` (`F-13`), `get_positions` → 0 posiciones, `get_all_orders` → 0 órdenes | **EN VIVO** — `PASS=6`, sin filas ausentes |
| **Campo ausente** | **MOCKED** — `test_quote_puntas_degenerate_never_breaks_the_chain`, `test_titulo_puntas_degenerate_dereferences_without_a_guard` | **MOCKED** — `test_posicion_from_api_collapses_parking_to_empty_list` | **EN VIVO** — los 7 `extra` de `InstrumentDetail` son el caso inverso (wire superset); el caso de eslabón ausente lo cubrió el colapso de los 6 alias sobre `null` | n/a — sin modelo, sin campo declarado |
| **Respuesta 204 / vacía** | **MOCKED** — `test_quote_204_empty_body_does_not_break_the_chain` | **MOCKED** — `test_get_posiciones_204_yields_the_empty_shape` | **MOCKED** — `test_market_data_204_empty_body_does_not_break_the_chain`, `test_null_market_data_envelope_raises_a_typed_error` | **no producido** — ningún endpoint devolvió 204 en la ventana |

**Ningún endpoint de ningún paquete devolvió 204 en vivo en esta ventana.** La mitad de ese caso
es íntegramente la suite mockeada del plan 39-02 (`packages/*/tests/test_deep_chain_edges.py`,
16 tests entre los tres paquetes). Eso es cobertura real, y es cobertura **mockeada**: la
distinción queda escrita en vez de colapsada.

---

## Limitaciones de cobertura declaradas

1. **La rama poblada de la cadena de parking de higyrus no se ejercita en vivo.** El probe sigue
   enviando `incluirParking=False` y el plan 39-05 deliberadamente **no** lo cambió: flipearlo
   alteraría la forma de la respuesta y quemaría el baseline write-once de `get_posiciones` por
   deriva de schema, sin ganancia (la mitad en vivo está bloqueada por DNS de todos modos). La
   limitación está transcrita del comentario que el propio driver dejó
   (`main_higyrus.py:1882-1889`). **Evidencia de esa rama: la suite mockeada**
   `packages/higyrus-client/tests/test_deep_chain_edges.py`.
2. **El cierre de ciclo de los cuatro paquetes vive dentro del driver de matriz.** Si matriz sale
   por el gate D-MATZ-33, el loop no corre y **ningún paquete recibe veredicto** — ni siquiera los
   que sí corrieron. Esta corrida no lo sufrió (matriz corrió), pero el acoplamiento es real y
   está anotado en el driver.
3. **La seguridad del sandbox bbsa es una aserción del operador, no verificable por máquina.** El
   allowlist mapea hostnames confirmados-como-no-producción; la confirmación es humana. La
   mitigación es el gate de mutaciones **independiente**: `verification/mutation_gate.py` quedó
   byte-idéntico y sigue fail-closed bajo bbsa, y la lista de probes del sweep no contiene ninguna
   alta, reemplazo ni cancelación de orden.
4. **El factor de duplicación por superficie del ledger de matriz es 1×, no ~2×**, con causa no
   determinada. Destino `HARN-VERIF-01`. No afecta la aritmética (ver `## Unidad y método`).
5. **`market-data-client` está fuera del alcance** por D-07 y no aporta ningún número a este censo;
   se audita en la Phase 36.
6. **Este censo mide divergencias de forma y nada más.** Divergencias de valor —valores fuera de
   conjunto bajo el lock D-09 de RESPONSE-`Literal`, `NaN`/`Infinity`, violaciones de rango o
   formato, inconsistencia entre campos— quedan fuera por construcción, igual que en el piso que
   contrasta.

---

## Arrastre explícito — el finding de base de iol

`F-01` de `iol-client` (`missing assumed key 'simbolo' in get_quote`, clase `SHAPE`, superficie
`both`, status **`OPEN`**) es una divergencia de **hoja escalar**, y la política Null Object
**no** colapsa hojas escalares (`35-RETIRED-TRIPLES.md`, `## What this disposition does NOT
retire`). Contabilizado explícitamente para que su persistencia no se lea como regresión nueva:

- **Sigue `OPEN`** al cierre de esta fase, con destino nombrado **`LIVE-NOBJ-01`** y firma del
  operador (`Operator signoff: sebadlf, 2026-08-30`).
- **No fue re-emitido en esta corrida.** El plan de esta fase anticipaba que lo fuera; la medición
  lo falsifica y se escribe la medición. Dos razones independientes: (a) `F-01` es un finding
  **escrito a mano** en la Phase 3, no un título emitido por el walker, así que no pertenece a la
  población de ninguna de las dos costuras; (b) la divergencia subyacente está materialmente
  resuelta — la Phase 30 retiró `simbolo` de `_ASSUMED_QUOTE_FIELDS` y del modelo `Cotizacion`.
- **Su no-re-emisión NO es un fix declarado y su permanencia NO es una regresión.** El operador
  **no** firmó la promoción a terminal: promover un finding a terminal es firma del operador, no
  del ejecutor, y la firma no se dio. Queda `OPEN` arrastrado, que es la única lectura honesta.

Consecuencia contable: `F-01` **no entra en ninguna de las tres columnas del split**, porque el
split particiona la población del walker y `F-01` no está en ella. Se declara acá para que su
exclusión sea explícita en vez de silenciosa.

---

## Ceros declarados por enumeración — resumen

| Cero | Paquete | Causa nombrada |
|---|---|---|
| 0 triples | `ambito-financiero-client` | Cero clases de modelo (`grep -c '^class '` → 0). Cero por enumeración, con 7 probes de evidencia positiva |
| 0 triples | `iol-client` | Cero por **inspección**: 15 probes, canal probado vivo en la Fase 33 (17 triples sintéticos capturados con el mismo handler) |
| 0 triples | `higyrus-client` | **No es cero: es `UNMEASURED`.** 0 probes, SKIPPED por DNS, destino `LIVE-HIGY-33` |
| 0 retirados por política | `iol-client` | Invariancia medida entre ramas: `Union` early-return antes de la Phase 38, colapso NOBJ-02 después; ninguna de las dos emite |
| 0 retirados por política | `market-data-client` | Fuera de alcance (D-07); el ledger de la Phase 35 ya lo dio en 0 en ambas columnas |
| 0 correcciones reales | `higyrus-client`, `iol-client`, `ambito-financiero-client` | Ningún fix de código en esos tres paquetes en esta fase; el único fix in-cycle fue matriz `_core` |
| 0 errores de handler | los 3 paquetes que corrieron | Gate duro cumplido; el censo no se construyó sobre un pipeline caído |

---

## Método y límites — ningún número de este archivo es una estimación

Cada figura es (a) transcrita de un comando ejecutado cuya salida está pegada arriba, (b) leída de
un sobre de evidencia de corrida en disco, o (c) derivada contando filas de una tabla que a su vez
transcribe una corrida. Las fuentes, nombradas:

1. **Los cuatro sobres de evidencia** — `.planning/verification/run-evidence/*.json`, con el
   comando de lectura y su salida verbatim en `## Unidad y método`.
2. **Los cuatro ledgers de findings** — parseados por título para la costura 2; el conteo de
   bloques y de clases sale del parseo, no de una lectura a ojo.
3. **`33-CENSUS.md`** para el censo de la Fase 33 y para la conversión registros↔triples.
4. **`29-SIZING.md`** (tabla de corpus, filas 36-43) para descomponer el piso de matriz fila por
   fila en vez de citar el total.
5. **`35-RETIRED-TRIPLES.md`** (`## Expected subtraction per package` y `## Phase 38 addendum`)
   para el término medio de colapso de política.
6. **`39-07-SUMMARY.md`** para las líneas `SUMMARY` verbatim, la ventana horaria y la tabla de
   disposición firmada por el operador.

**Redacción.** Este censo transcribe 4-tuplas (metadata de tipo y de path), líneas `SUMMARY` ya
redactadas por `safe_print`, y comandos con su salida. No contiene ningún valor de wire, ninguna
credencial, ningún identificador de cuenta ni ninguna base URL con credenciales embebidas
(T-39-31).

---

*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo — plan 39-08*
*Requisito: LIVE-NOBJ-01 — ROADMAP Phase 39 criterio 4 (SC-4), decisiones D-06 / D-10 / D-11 / D-12*
*Corrida medida: 2026-08-30T02:41:17Z … 02:49:48Z (sábado 2026-08-29 23:34 ART, mercado cerrado)*
