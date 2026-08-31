<!-- planner-discipline-allow: LIVE-HIGY-33 -->

# Phase 42 — Cierre: disposición de los cinco criterios de éxito

**Producido:** 2026-08-31 (plan 42-06)
**Fase:** `42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce`
**Requisitos:** LIVE-01, LIVE-02
**Denominador:** los **cinco** criterios de éxito de `.planning/ROADMAP.md § Phase 42` (líneas 105-109)

> Este documento existe porque "la fase corrió" no es lo mismo que "los cinco criterios están
> satisfechos". Cada criterio recibe **exactamente una** disposición con **evidencia nombrada**
> (archivo:línea, comando + salida medida, o el SUMMARY que la registra). **Cero filas sin disponer.**

---

## 1. Disposición de los cinco criterios

Vocabulario de disposición:

- **`SATISFECHO`** — el criterio pedía una cosa y esa cosa ocurrió.
- **`SATISFECHO POR LA VÍA DECLARADA`** — el criterio admite **explícitamente** una salida
  alternativa (`o queda SKIPPED con la causa re-confirmada`, `o declara qué campo no se pudo medir y
  por qué`) y ésa fue la que ocurrió. **No es un satisfecho de segunda**: es la rama que el criterio
  contempla, y la evidencia demuestra que se recorrió con medición, no con silencio.
- **`NO SATISFECHO`** — no ocurrió. *(Cero filas en esta fase.)*

| # | Enunciado abreviado | Disposición | Evidencia nombrada |
|---|---------------------|-------------|--------------------|
| **criterio 1** | `scripts/literal_census_33.py` decide el venue por **igualdad exacta de hostname** contra el mismo `_VENUE_ALLOWLIST` que `main_matriz.py` (nunca substring/`endswith`/`in`), con test que falsifica el superstring de spoofing y pinnea la fuente única; el widening autorizado en checkpoint humano **bloqueante** antes de que salga tráfico | **SATISFECHO** | `scripts/literal_census_33.py:90` → `from main_matriz import _VENUE_ALLOWLIST, _venue_token`; gate portado en `:234` (`venue = _venue_token(base)` / `if venue is None:`), misma posición pre-`login()`. `verification/test_literal_census_venue_gate.py` (272 líneas) — **21 nodos, 21 passed** re-ejecutados en esta sesión; incluye el superstring hostil `api.bbsa.matrizoms.com.ar.attacker.example → None`, la variante userinfo `…@attacker.example → None`, producción `api.primary.com.ar → None`, fail-closed ante cadena vacía y ante base URL imparseable, el pin de identidad `census._venue_token is main_matriz._venue_token`, y la aserción **AST** anti-substring restringida al `FunctionDef` de `census_matriz` con su control positivo. Enrolado en CI: `.github/workflows/ci.yml:92` (`grep -c` = **1**). Checkpoint `gate="blocking-human"` respondido por el operador `Approved`, transcrito verbatim en `42-01-SUMMARY.md:96-108` con su procedencia declarada (operador en sesión; **no** derivado de `auto_advance`, `yolo` ni `human_verify_mode`). Gates TDD: `test(...)` `7cc103a` (RED) precede a `feat(...)` `99fb17c` (GREEN). Registro: `42-01-SUMMARY.md`. |
| **criterio 2** | `higyrus-client` produce un resultado **medido**: o resuelve y corre, o queda `SKIPPED` con la causa **re-confirmada en esta sesión** (excepción y diagnóstico citados, no heredados de la Phase 39) y con el destino `LIVE-HIGY-33` renombrado — nunca un cero ni un silencio | **SATISFECHO POR LA VÍA DECLARADA** (rama `SKIPPED con causa re-confirmada`, admitida literalmente por el criterio) | **Mitad (a) — causa re-medida hoy:** `socket.gaierror` en resolución DNS y `httpx.ConnectError` en `login()`, ambos con el errno `[Errno 8] nodename nor servname provided, or not known` citado verbatim tras pasar un **guard de contención** case-insensitive (hostname / base URL / netloc nunca impresos; leak-check CLEAN sobre los 4 artefactos de la sesión). La comparación contra la Phase 39 es de **clase de excepción medida**, no de prosa: `httpx.ConnectError` medido hoy **==** `httpx.ConnectError` heredado. Driver corrido **dos veces** en la sesión (42-03 `21:20:38`, 42-05 `21:38:57`, ~18 min de separación, veredicto coincidente — descarta un fallo transitorio de resolución), `DRIVER_EXIT = 0` las dos, una única línea a stdout `SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-42` que matchea `_ENV_SKIP` (`^SKIPPED \S.*:`). Sobre `.planning/verification/run-evidence/higyrus-client.json`: `captured_at 2026-08-31T21:38:57.229188+00:00`, `probes_executed 0` **acompañado** de `skipped` no nulo con causa **y** destino — no es un cero silencioso (D-13). Regenerado **por corrida real**, nunca por edición: diff de 2 líneas, orden de operaciones commiteado (`f75145c` rename → corrida → `102c972`). Ledger `higyrus-client-findings.md` byte-idéntico (`a6ca519a…` antes y después). **Mitad (b) — destino renombrado:** `LIVE-HIGY-33` → `LIVE-HIGY-42` en los **14 sitios vivos** (11 de código + 3 de prosa, 7 archivos, commit atómico `f75145c`); conteo remanente **asimétrico** verificado = **2** en `verification/test_cycle_closure_phase33.py:250-252` (`3` sería un sitio vivo sin renombrar; `0` sería historia congelada rota). Registro: `42-03-SUMMARY.md`, `42-05-SUMMARY.md`. |
| **criterio 3** | El censo reporta los valores observados de los cinco campos `Literal` de RESPONSE (`marketId`, `cficode`, `currency`, `orderTypes`, `ordType`) con **venue y timestamp en el encabezado**, **o declara explícitamente qué campo no se pudo medir y por qué**; y el D-lock (b) de v1.6 queda **reafirmado, no revocado** | **SATISFECHO POR LA VÍA DECLARADA** (4 campos `MEDIDO` + 1 `NO MEDIBLE EN ESTA CORRIDA` con causa declarada, salida que el criterio admite en su propia redacción) | Encabezado verbatim de la corrida autoritativa: `CENSUS-HEADER venue=bbsa captured_at=2026-08-31T21:11:53.196947+00:00 allowlist_size=2`, emitido **antes de la primera request** por `_census_header()` (`scripts/literal_census_33.py:189-208`, llamado en `:248`). El `venue=bbsa` **sale de `_venue_token(base)`** —el mismo objeto que decidió el gate— así que el header no puede mentir sobre contra qué se midió; `allowlist_size` es un **conteo**, nunca un hostname (T-42-04). Comando: `uv run python scripts/literal_census_33.py --matriz-only`, exit **`0`** medido con `$?` directo (no sobre `tee`), veredicto `CENSUS: matriz=RAN iol=NOT-REQUESTED (--matriz-only)`. **8 paths sobre 3 de 5 endpoints.** Disposición campo por campo — cero filas sin disponer: `marketId` **MEDIDO** (1 valor, `ROFX`), `cficode` **MEDIDO** (**15** valores), `currency` **MEDIDO** (2: `ARS`, `USD`), `orderTypes` **MEDIDO** (**6** valores), `ordType` **NO MEDIBLE EN ESTA CORRIDA** — causa **medida, no supuesta**: los dos endpoints de órdenes respondieron `status: OK` con la colección `orders` **presente y de longitud 0** (verificado inspeccionando la forma del payload capturado, para distinguir "colección vacía" de "campo ausente" y de "SKIP del gate"); `PRIMARY_ACCOUNT` presente y los dos endpoints **sí** se ejercitaron. **No se rellenó con nada**: emitir una orden habría sido una mutación, copiar el conjunto declarado habría sido evidencia fabricada. **D-lock (b) EN VIGOR y reforzado por medición**: el vendor emite **8 valores fuera de los alias declarados** (6 en `CFICode`, 2 en `OrderType`) que el stream de divergencias **no** reporta — con enforcement, una sola corrida de lectura habría fallado sobre 9675 instrumentos. El script emite `CENSUS-DLOCK` en runtime antes de la primera request, así que la declaración no depende de que alguien la escriba después. Registro: `42-CENSUS.md` (210 líneas), `42-02-SUMMARY.md`. |
| **criterio 4** | `verification/mutation_gate.py` queda **byte-idéntico** y el order entry sigue fail-closed bajo `bbsa`: el widening es del gate de **lectura** del censo, jamás del de mutación | **SATISFECHO** | `git hash-object verification/mutation_gate.py` = **`6bdaec006cc16f7c8dbfac41701712a9085c691b`**, medido al cierre de esta fase (comando re-ejecutado en la sesión del plan 42-06) e idéntico al valor pinneado en cada `<verify>` de los planes 42-01 … 42-05. El archivo **no se modificó en ninguna task de la fase**. Cero órdenes emitidas, cero mutaciones, `VERIFY_MUTATING` sin setear en la corrida del censo, `MARKET_DATA_VERIFY_MUTATING` sin setear en la de market-data (los 18 probes mutantes salieron `SKIPPED (mutating, guard off)` y `mutation_gate_refusal_sync`/`_async` confirmaron el rechazo con `0 HTTP, 0 Auth0`). Sin barrido de 4xx (D-10 / P-05). Pinneado además de forma no-vacua por `verification/test_literal_census_venue_gate.py` (con control positivo bajo remarkets), enrolado en CI. Registro: `42-01/02/03/04/05-SUMMARY.md`, todos con el mismo hash. |
| **criterio 5** | La corrida deja en disco una **lectura fresca del wire** de `/instruments` y `/segments` de `market-data-client`, **fechada en esta sesión**, base de evidencia de la Phase 43 — y el baseline committeado del 2026-07-31 queda **explícitamente marcado como no-autoritativo** para SHAPE-01 | **SATISFECHO** | Corrida en vivo real contra `develop`: `SUMMARY: PASS=23 FAIL=0 SKIPPED=18 FINDING=2 DIVERGENCES=18 HANDLER_ERRORS=0`, exit **0**, con `PROBE instruments_sync: PASS instruments=50` y `PROBE segments_sync: PASS segments=4` — ningún probe de los dos endpoints devolvió `FINDING`, así que la captura salió de una lectura real (fabricarla a mano estaba explícitamente prohibido, T-42-16). Dos envelopes de **7 claves** con `captured_at` de esta sesión, re-verificados hoy: `/instruments` → `2026-08-31T21:27:42.854194+00:00`; `/instruments/segments` → `2026-08-31T21:27:43.256969+00:00`. **La mitad que importa:** `42-WIRE-READ.md` (286 líneas) es un artefacto **committeado** y PII-free que sobrevive a otro clone / worktree / `git clean -xdf` — la captura cruda vive sólo en `.planning/verification/captures/` (gitignored, `git status --porcelain` **vacío**), y una evidencia gitignored **no existe** para la fase consumidora. PII-freeness **verificada programáticamente**: toda hoja de los dos bloques JSON pertenece a `{str,int,float,bool,NoneType,dict,list}` (cero hojas no-conformes) y cada bloque es byte-igual al `schema` de su envelope. Marca de **NO AUTORITATIVO** sobre el baseline del 2026-07-31 escrita en `42-WIRE-READ.md § 3` con su razón mecánica (write-once, D-25); los dos baselines siguen con `captured_at 2026-07-31T16:49:30/31` y **no** aparecen en `git status` (T-42-15 verificado, no asumido). Delta de claves contra el baseline: **VACÍO** en los dos modelos — reportado como **resultado de la re-medición**, y explícitamente **no** como reversión de la marca de no-autoritatividad. Registro: `42-WIRE-READ.md`, `42-04-SUMMARY.md`. |

**Aritmética de cierre:** 5 criterios enumerados · 2 `SATISFECHO` · 3 `SATISFECHO POR LA VÍA
DECLARADA` · 0 `NO SATISFECHO` · **0 filas sin disponer**. 2 + 3 + 0 = 5 = denominador.

---

## 2. Requisitos

| Requisito | Estado | Evidencia que lo sostiene |
|-----------|--------|---------------------------|
| **LIVE-01** — *Re-chequear la conectividad DNS de `higyrus-client` y producir un resultado medido — resuelto, o `SKIPPED` con causa re-confirmada (nunca un silencio)* | **COMPLETO** (por la vía "causa re-confirmada") | Las **dos mitades** del criterio 2 entregadas y verificadas: (a) resultado medido con clase de excepción citable y sobre fechado → `42-03-SUMMARY.md`; (b) destino `LIVE-HIGY-33` renombrado a `LIVE-HIGY-42` en los 14 sitios vivos con el sobre regenerado por corrida → `42-05-SUMMARY.md`. Los planes 42-03 y 42-05 **deliberadamente no lo marcaron completo** (cada uno entregó una mitad); el cierre formal es este plan, que lo lleva en su frontmatter. `.planning/verification/run-evidence/higyrus-client.json` con `captured_at 2026-08-31T21:38:57.229188+00:00`. |
| **LIVE-02** — *Correr el censo de valores `Literal` de RESPONSE de `matriz-client` contra el sandbox `bbsa`, con el allowlist exacto de hostname portado primero desde `main_matriz.py`* | **COMPLETO** | El orden que el requisito exige se respetó: **primero** el port del allowlist (42-01, `99fb17c`), **después** el censo (42-02). `CENSUS-HEADER venue=bbsa captured_at=2026-08-31T21:11:53.196947+00:00`, `42-CENSUS.md` con los 5 campos dispuestos. Marcado ya `[x]` en `REQUIREMENTS.md:13` / `:61` por los planes 42-01, 42-02 y 42-04. |

**Distinción que este documento deja escrita:** *LIVE-01 completo ≠ `LIVE-HIGY-42` cerrado.* El
requisito pedía **un resultado medido**, y hay uno. El ítem de backlog pide los **22 triples
contrastados**, y siguen sin contrastar.

---

## 3. Resultado de los 4 gates de CI

Medidos en la sesión del plan 42-06, sobre HEAD tras el commit de la Task 1 (`84bc48d`).

| # | Gate | Comando exacto | Salida medida |
|---|------|----------------|---------------|
| 1 | Lint | `uv run --frozen ruff check .` | `All checks passed!` |
| 2 | Formato | `uv run --frozen ruff format --check .` | `279 files already formatted` |
| 3 | Tipos | `uv run --frozen mypy` | `Success: no issues found in 75 source files` |
| 4 | Tests | `uv run pytest -q` sobre las **13** rutas de la allowlist de `.github/workflows/ci.yml:80-92` | **`150 passed in 0.54s`**, **`0 failed`**, exit `0` |

**El gate 4 es el comando que refleja CI, no `pytest -q` a secas.** El job `test` de `ci.yml` pasa
rutas explícitas que **pisan** `testpaths`, así que `verification/` nunca corre entero en CI: un lock
que no está en esa lista está verde en local y **muerto** en CI (WR-01 / T-42-06). Las 13 rutas:

```
verification/test_main_market_data_deep_chain.py      verification/test_main_higyrus_skip_line_shape.py
verification/test_safemodel_diff_null_object_links.py verification/test_run_evidence.py
verification/test_main_matriz_risk_envelope_keys.py   verification/test_main_iol_deep_chain.py
verification/test_safemodel_diff_mapping_recursion.py verification/test_main_higyrus_deep_chain.py
verification/test_main_verify_classification.py       verification/test_main_matriz_deep_chain.py
verification/test_main_matriz_skip_line_shape.py      verification/test_cycle_closure_phase33.py
                                                      verification/test_literal_census_venue_gate.py
```

### Delta contra el baseline

| Punto de medición | Rutas | `passed` | `failed` |
|-------------------|------:|---------:|---------:|
| **Baseline en HEAD, pre-fase** (`42-RESEARCH.md § Validation Architecture`) | 12 | **129** | 0 |
| Cierre del plan 42-01 | 13 | 150 | 0 |
| Cierre del plan 42-03 | 13 | 150 | 0 |
| Cierre del plan 42-05 | 13 | 150 | 0 |
| **Cierre de la fase (plan 42-06)** | **13** | **150** | **0** |

**Delta: `129 → 150` (N = +21), `0 failed`.** Los 21 nodos nuevos son exactamente el contenido de
`verification/test_literal_census_venue_gate.py` (10 tests no parametrizados + 13 casos
parametrizados de `test_venue_token_resolves_by_exact_hostname` − 2 = 21). El conteo se mantuvo
constante en 150 desde el plan 42-01 **como corresponde**: los planes 42-02 … 42-06 no agregaron ni
quitaron tests; 42-05 sólo cambió el literal que 11 de ellos aseveran.

### Gate adicional del `<verification>` de la fase

| Comando | Salida |
|---------|--------|
| `uv run python scripts/literal_census_33.py --selftest` | `SELFTEST: PASS`, exit `0` |

---

## 4. Inventario de artefactos fechados

| Artefacto | Ruta | `captured_at` / fecha | Estado en git |
|-----------|------|-----------------------|---------------|
| Sobre de evidencia de higyrus | `.planning/verification/run-evidence/higyrus-client.json` | `2026-08-31T21:38:57.229188+00:00` | **Committeado** (`102c972`) |
| Captura de wire — `/instruments` | `.planning/verification/captures/market-data-wire-instruments-42.json` | `2026-08-31T21:27:42.854194+00:00` | **Gitignored por diseño** (`.gitignore:53`) — presente en el working tree, 7 claves |
| Captura de wire — `/instruments/segments` | `.planning/verification/captures/market-data-wire-segments-42.json` | `2026-08-31T21:27:43.256969+00:00` | **Gitignored por diseño** — presente en el working tree, 7 claves |
| Censo `Literal` de matriz | `.planning/phases/42-…/42-CENSUS.md` | header `2026-08-31T21:11:53.196947+00:00`, venue `bbsa` | **Committeado** (`30898ff`), 210 líneas |
| Lectura fresca del wire | `.planning/phases/42-…/42-WIRE-READ.md` | envelopes `2026-08-31T21:27Z` | **Committeado** (`cac158a`), 286 líneas |
| Este documento de cierre | `.planning/phases/42-…/42-CLOSURE.md` | 2026-08-31 | **Committeado** (plan 42-06) |

Colateral gitignored de la corrida del censo, presente en el working tree y **no** recuperable de
git por diseño (C-4 / D-11): los 5 dumps `.planning/verification/captures/matriz-census-*.json`
(~11,6 MB de payload crudo). `git status --porcelain -- .planning/verification/captures/` está
**vacío**, que es la prueba de que el crudo no rozó git.

**Regla que esta fase deja establecida:** todo criterio que pida "evidencia fresca en disco" se
satisface con un artefacto **committeado**, nunca sólo con un archivo bajo un directorio gitignored
— la evidencia gitignored no existe para la fase consumidora.

---

## 5. Pins de seguridad al cierre

| Pin | Valor medido al cierre | Cómo se sostiene |
|-----|------------------------|------------------|
| `git hash-object verification/mutation_gate.py` | **`6bdaec006cc16f7c8dbfac41701712a9085c691b`** | Byte-idéntico al valor pinneado en los `<verify>` de los 6 planes. El archivo no se tocó en ninguna task de la fase. |
| `verification/test_literal_census_venue_gate.py` enrolado en CI | `grep -c` sobre `.github/workflows/ci.yml` = **1** (línea `:92`) | El lock **no es inerte**: la allowlist explícita del step "driver locks" pasó de 12 a 13 rutas en el **mismo commit** que creó el archivo (`7cc103a`). |
| El mismo lock, verde | **21 passed**, 0 failed (re-ejecutado en esta sesión) | 13 casos de spoofing + identidad `is` + AST anti-substring con control positivo + pin del gate de mutación con control positivo bajo remarkets. |
| Historia congelada de v1.6 intacta | `grep -c 'LIVE-HIGY-33' verification/test_cycle_closure_phase33.py` = **2** | Criterio **asimétrico**: `3` = sitio vivo sin renombrar, `0` = guard de historia roto. Sólo `2` es PASS. |
| `.planning/milestones/` y `.planning/STATE.md` sin tocar | `git status --porcelain -- .planning/milestones/ .planning/STATE.md` **vacío** | T-42-17. Los párrafos históricos de `PROJECT.md` (`:29`, `:78`, `:278`, `:417`) conservan sus menciones de `LIVE-HIGY-33` — `grep -c` sobre `PROJECT.md` sigue siendo ≥ 1. |

---

## 6. Ausencia de instalación de paquetes

El milestone v1.8 se define explícitamente como **"sin superficie nueva"** (`REQUIREMENTS.md:4`).
Esta fase lo prueba, no lo afirma.

```
$ git diff --stat e1be226..HEAD -- uv.lock packages/*/pyproject.toml pyproject.toml
(salida vacía)   exit 0

$ git diff --exit-code -- uv.lock
(sin diferencias)   exit 0
```

`e1be226` es el commit inmediatamente anterior al primer commit de ejecución de la fase
(`7cc103a`). **Cero dependencias instaladas, actualizadas o adoptadas.** Cero comandos de package
manager ejecutados en toda la fase (`uv sync`, `uv add`, `pip install`, `npm install` — ninguno).
El `42-RESEARCH.md § Package Legitimacy Audit` es **N/A** por construcción: cero paquetes marcados
`[ASSUMED]`, `[SUS]` o `[SLOP]`, porque no hubo ningún paquete que auditar. T-42-SC mitigado por
medición.

Los únicos archivos de fuente que la fase tocó son de **verificación y drivers de raíz**, nunca de
un paquete publicable: `scripts/literal_census_33.py`, `main_higyrus.py`, `main_matriz.py`,
`main_market_data.py`, `.github/workflows/ci.yml` y 6 archivos bajo `verification/`. **Ningún
`packages/*/src/**` cambió**, así que ninguna versión de paquete se movió y no hay nada que
publicar.

---

## 7. Lo que esta fase **NO** cierra

Escrito explícitamente para que nadie lea de más. Cada ítem con destino nombrado.

1. **`LIVE-HIGY-42` (ex `LIVE-HIGY-33`) sigue ABIERTO.** El rename cambió el identificador, **no el
   estado**. Los **22 triples sin contrastar** del piso ratificado de `29-SIZING.md` —`Movimiento`
   (9), `PosicionValuada` (11), `Posicion` (2)— siguen exactamente igual de sin contrastar, porque
   el veredicto volvió a ser `SKIPPED`. **Destino:** backlog de `ROADMAP.md § Deferred to v1.8+`,
   entrada `LIVE-HIGY-42`, hasta que el host resuelva desde una red con acceso (el camino es el de
   operador-corre-y-pega de la Phase 23).

2. **WR-02 (`httpx.ConnectTimeout` fuera de la rama vendor-unreachable de higyrus) queda
   re-declarado FUERA DE ALCANCE.** La decisión se tomó **por escrito en `42-03-PLAN.md` ANTES de
   la corrida** y **no se revisitó después**, precisamente para que no se tomara bajo la presión del
   resultado. `ConnectTimeout` **no** es subclase de `ConnectError` (MRO verificado contra httpx
   0.28.1), así que un host que *resuelve pero cuelga* caería en `_RESIDUAL_PROBE_EXCEPTIONS` y
   produciría `FINDING`/`FAILED` en vez de `SKIPPED` — y la respuesta correcta seguiría siendo
   **reportarlo tal cual**, nunca ampliar la rama a mitad de corrida. Cero líneas del clasificador
   se tocaron. **Destino:** `ROADMAP.md § Deferred to v1.8+`, entrada "Deuda documentada in-code de
   Phase 39 (D39-01..04, WR-02)".

3. **La corrección de `29-DLOCK-RESPONSE-LITERAL.md:140-142` pertenece a su firmante.** La corrida
   del censo confirmó **empíricamente** que el párrafo es falso: 8 valores fuera de conjunto
   atravesaron el decoder **sin emitir un solo record de divergencia**, porque la rama `Literal` de
   `walk_field` retorna temprano con `literal_enforced=False` (`_decode.py:540-549`). El documento
   está **firmado**, así que la corrección es del firmante y quedó **fuera del alcance** de esta
   fase — se nombra en `42-CENSUS.md § 7` sólo para que no se pierda. **Destino:** el firmante del
   D-lock.

4. **SHAPE-01 y HARN-02 son la Phase 43, no ésta.** Esta fase **midió** la forma del wire; no
   corrigió ni un campo de `models.py`. Los **8 valores fuera de los alias `Literal`** de matriz
   (6 `CFICode`, 2 `OrderType`) quedaron **registrados, no aplicados**: ampliar `types.py` es un
   cambio de la forma declarada de un paquete publicado y necesita disposición de semver propia —
   un censo que además muta la superficie que está midiendo deja de ser una medición. **Destino:**
   Phase 43 (SHAPE-01 / HARN-02) para market-data; para matriz, la ventana natural es la fase que
   abra su `types.py`, con presupuesto declarado y **nunca** como efecto lateral.

5. **El churn del ledger de market-data lo limpia HARN-01 en la Phase 45.** La corrida de 42-04
   apendeó **+40 bloques** al ledger, de los cuales **12 son duplicados cosméticos** de títulos que
   ya existían en HEAD. El ledger se commiteó **tal cual salió**, sin edición manual. Es el ruido
   conocido y aceptado (`ROADMAP.md:53`: "ruidoso pero no lossy"), y la decisión de orden del
   milestone es explícita: dedupear **después** de las corridas en vivo, para que el peor caso sea
   "ledger inflado" y no "divergencia perdida". **Destino:** Phase 45 (HARN-01).

**Ítems diferidos descubiertos por esta fase** (registrados en
`.planning/phases/42-…/deferred-items.md`, ninguno cerrado acá):

| ID | Qué es | Destino |
|----|--------|---------|
| **D42-DEF-01** | Exposición **pre-existente** del base URL del vendor en el header de `.planning/verification/higyrus-client-findings.md:5`. No la causó esta sesión (byte-idéntico a HEAD, último commit `fbb69c3`/Phase 17); es un ledger append-only versionado (HARN-07) y la política T-39-04 es **posterior** a ese header. Tres opciones de resolución escritas. | **Phase 45** |
| **D42-DEF-02** | El SHAPE-diff del driver (`_emit_shape`) está **INERTE** para `Instrument` y `Segment`: `sample = raw[0] if isinstance(raw, list) and raw else None` queda en `None` porque el wire devuelve un sobre paginado (`dict`), y el diff se saltea **en silencio**. **Riesgo concreto:** si la Phase 43 usa `_emit_shape` como la medición del "después" del criterio 2, verá cero findings **haya arreglado el modelo o no** — un falso verde. La evidencia no se perdió: el censo de divergencias la produjo completa (F-205…F-218 sync, F-229…F-242 async). | **Phase 43** (advertencia) / **Phase 45** (fix del harness) |

---

## 8. Precondición entregada a la Phase 43

`REQUIREMENTS.md:82` declara la precondición cross-fase *"Lectura fresca del wire de `/instruments`
+ `/segments` — producida en Phase 42 (criterio 5), consumida por Phase 43 (SHAPE-01)"*. **Está
entregada.**

- **Artefacto:** `.planning/phases/42-…/42-WIRE-READ.md`, **committeado** (`cac158a`, 286 líneas),
  PII-free verificado programáticamente. La Phase 43 puede citarlo sin depender del working tree de
  nadie: sobrevive a otro clone, otro worktree y `git clean -xdf`.
- **`captured_at`:** `/instruments` → `2026-08-31T21:27:42.854194+00:00`; `/instruments/segments` →
  `2026-08-31T21:27:43.256969+00:00`. Los dos **de esta sesión**.
- **Los baselines del 2026-07-31 quedaron marcados NO AUTORITATIVOS** para SHAPE-01, con su razón
  mecánica escrita (`_write_schema_snapshot` es write-once, D-25 — por eso `42-WIRE-READ.md` existe
  como artefacto aparte y no como refresh del baseline). `.planning/verification/schemas/market-data-client/get-instruments.json`
  y `get-segments.json` siguen con `captured_at 2026-07-31T16:49:30/31` y **no** aparecen en
  `git status`: el write-once se comportó según su contrato, verificado y no asumido.
- **El delta contra el baseline es VACÍO en los dos modelos** — el wire no se movió en un mes, así
  que la descripción de `SHAPE-MD-REF-33` queda **re-validada en vivo** y la Phase 43 no necesita
  re-medir la forma. **Un delta vacío es un resultado de la re-medición, no un sustituto de haberla
  hecho, y NO revierte la marca de no-autoritatividad:** lo autoritativo es la medición de **hoy**,
  que resulta coincidir. Un lector apurado que concluya "el baseline coincide, entonces puedo usar
  el baseline" está leyendo mal el criterio 5.
- **Insumo adicional:** la tabla de FIDs de la disposición campo por campo de `Instrument` (9
  triples) y `Segment` (5 triples) × sync/async — F-205…F-218 y F-229…F-242 — alimenta directamente
  el criterio 1 de la Phase 43.
- **Advertencia que la Phase 43 debe leer antes de planificar:** D42-DEF-02 (§ 7). El camino de
  medición que parece obvio para demostrar su criterio 2 hoy no reporta nada para estos dos modelos.
- **Si la Phase 43 necesita los VALORES del wire y no la forma,** tiene que re-correr el driver en
  vivo con su propia autorización humana: el crudo está en `captures/`, gitignored, y no es
  recuperable de git por diseño (C-4 / D-11).

---

## 9. Nota de método sobre este documento

Tres cosas que este cierre hace deliberadamente, y que valen como precedente:

1. **`SATISFECHO POR LA VÍA DECLARADA` no es un eufemismo de "casi".** Es la disposición correcta
   cuando el criterio **enumera** la salida alternativa en su propia redacción (criterio 2:
   *"o queda `SKIPPED` con la causa re-confirmada"*; criterio 3: *"o declara explícitamente qué
   campo no se pudo medir y por qué"*). Colapsarla en `SATISFECHO` a secas borraría la información
   de **cuál** rama se recorrió; colapsarla en `NO SATISFECHO` mentiría en la otra dirección.
2. **Ninguna anotación de este documento sale de una expectativa.** Cada número, timestamp y clase
   de excepción está copiado de una medición registrada en un SUMMARY de la fase o re-ejecutado en
   la sesión del plan 42-06.
3. **La sección § 7 es tan parte del cierre como la § 1.** Un cierre que sólo enumera lo satisfecho
   invita a que la fase siguiente lo lea de más. Éste nombra los cinco ítems que **no** cierra, con
   su destino.

---

*Phase 42 — cerrada el 2026-08-31. Plan 42-06.*
