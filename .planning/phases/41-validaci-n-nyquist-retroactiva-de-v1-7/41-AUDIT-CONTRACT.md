---
phase: 41
kind: audit-contract
created: 2026-08-31
audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7
audit_baseline_head: 6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5
frozen_tree_verified: true
---

# Phase 41 — Contrato de auditoría

> Documento autoritativo de la fase. Los cinco planes de la Wave 2 (41-02..41-06) y el plan de
> cierre (41-07) **no toman decisiones de formato ni de disposición**: las toman de aquí. Un
> ejecutor de la Wave 2 debe poder producir su artefacto leyendo sólo este archivo más su propio
> `{N}-VALIDATION.md`.

---

## 1. Identidad del árbol auditado

La auditoría retroactiva de las fases 35–39 sólo tiene valor si el árbol de fuente que se
re-ejecuta hoy es **el mismo** que shipeó en v1.7. Si fuente de v1.8 aterrizara antes de que las
cinco disposiciones queden escritas, cada evidencia `VERIFIED-NOW` estaría atribuida al árbol
equivocado y el criterio 1 del ROADMAP quedaría no re-verificable por terceros.

### 1.1 Los dos SHA de atribución

| Clave | Valor | Cómo se obtuvo |
|-------|-------|----------------|
| `audited_commit_sha` | `37a83fe693a303a551f4374f48fe6fc5521804f7` | `git rev-parse v1.7^{commit}` |
| `audit_baseline_head` | `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5` | `git rev-parse HEAD` (sesión de auditoría, 2026-08-31) |
| `frozen_tree_verified` | `true` | `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → **exit 0** |

**`audited_commit_sha` es el commit, no el objeto-tag.** `v1.7` es un tag **anotado**
(`git cat-file -t v1.7` → `tag`), de modo que `git rev-parse v1.7` a secas devuelve el *objeto-tag*
(`c4dc6ea…`), no el commit. Declarar ese valor en los cinco artefactos haría el criterio 1 no
re-verificable por cualquiera que re-corriese la comprobación. **La única forma admitida de
resolver el tag en esta fase es `git rev-parse v1.7^{commit}`.** Si el valor resuelto difiere de
`37a83fe693a303a551f4374f48fe6fc5521804f7`, el plan **aborta**: toda la medición de
`41-RESEARCH.md` queda invalidada y hay que re-medir.

**`audit_baseline_head` se captura una sola vez, aquí, y se copia literal.** El HEAD se mueve con
cada commit de la fase; si cada plan lo re-capturase, los seis artefactos declararían seis valores
distintos y el conjunto sería ilegible. Los planes 41-02..41-07 **copian** el literal de esta
tabla, no lo re-derivan.

### 1.2 La prueba de identidad del árbol

```bash
git diff --quiet v1.7 HEAD -- . ':(exclude).planning'
# exit code: 0   ← ejecutado 2026-08-31 en la sesión de auditoría
```

El pathspec de exclusión `':(exclude).planning'` es **obligatorio**: `.planning/` churnea
legítimamente durante toda la fase (cada commit de auditoría escribe ahí), y sin excluirlo la
prueba fallaría siempre y por una razón irrelevante. Lo que la prueba afirma es exactamente:
*ningún byte de fuente de producto, de `.github/`, de `tools/`, de `verification/` ni de
`packages/` cambió entre el tag `v1.7` y el HEAD de esta sesión.*

Si el comando sale distinto de 0 en cualquier momento de la fase: **ABORTAR**. Significa que fuente
de v1.8 aterrizó antes de que la auditoría cerrara, lo que invalida la atribución entera. No se
continúa, y no se "documenta la excepción": la excepción no existe, la fase se re-planifica contra
un árbol nuevo.

### 1.3 Criterio 1 es un invariante continuo, no un gate de una sola vez

Esta comprobación **no** se corre una vez al principio y se olvida. Se re-verifica:

1. Al inicio de **cada** plan de la Wave 2 (41-02, 41-03, 41-04, 41-05, 41-06), antes de escribir.
2. Al final de **cada** tarea de la Wave 2, como parte de su bloque `<verify><automated>`.
3. Otra vez en el cierre (41-07), como parte del gate de contención de alcance.

El motivo: la Wave 2 corre en paralelo con el resto de la vida del repo. La ventana en la que un
commit de fuente puede colarse no es el instante inicial, es toda la duración de la fase.

### 1.4 Versiones de herramienta medidas en esta sesión

Todas las evidencias `VERIFIED-NOW` de las fases 35–39 se producen con estas versiones. Se declaran
para que un tercero pueda reproducir la corrida, y porque **hay bookkeeping stale que nombrar**.

| Herramienta | Versión medida (2026-08-31) | Comando |
|-------------|-----------------------------|---------|
| `uv` | 0.11.3 (45da18ac3 2026-04-01 aarch64-apple-darwin) | `uv --version` |
| `pytest` (vía uv) | 9.0.3 | `uv run pytest --version` |
| `mypy` | 1.20.2 (compiled: yes) | `uv run mypy --version` |
| `ruff` | 0.15.12 | `uv run ruff --version` |
| `git` | 2.39.5 (Apple Git-154) | `git --version` |
| `node` | v24.15.0 | `node --version` |

**Hallazgo de bookkeeping a nombrar, no a corregir en silencio:** la tabla `## Test Infrastructure`
de `35-VALIDATION.md` declara **pytest 8.3**. El real es **9.0.3**. Esa fila es stale desde antes de
esta fase. Se **nombra** en la sección `### Hallazgos de bookkeeping` del artefacto de la Phase 35
(§5, bloque 6); no se reescribe la tabla histórica sin dejar constancia del cambio. El mismo trato
aplica a cualquier otra versión stale que aparezca en los cinco archivos.

### 1.5 Estado de partida del árbol de locks

Medido en esta sesión, y usado como línea base del criterio 4 (D-08: se esperan **cero** archivos
de test nuevos):

| Medida | Valor de partida | Comando |
|--------|------------------|---------|
| Archivos `verification/test_*.py` | **52** | `ls verification/test_*.py \| wc -l` |
| De ésos, enrolados en el allowlist de CI | **12** | `ci.yml:81-92` |
| `git status --porcelain verification/` | vacío | — |

Los tres valores deben ser idénticos al cierre de la fase (41-07 los re-mide). Un 53 sería la señal
de que la contingencia de D-08 se disparó.

---

## 2. Denominador y claves de fila (D-03 + D-05)

### 2.1 El denominador del criterio 2 es 62

```
Phase 35 :  12 filas de mapa reconstruidas  +  1 fila manual-only   =  13
Phase 36 :  11 filas de mapa                +  0 filas manual-only  =  11
Phase 37 :  14 filas de mapa                +  0 filas manual-only  =  14
Phase 38 :   8 filas de mapa                +  1 fila manual-only   =   9
Phase 39 :  11 filas de mapa                +  4 filas manual-only  =  15
                                                                      ----
                                            TOTAL DEL CRITERIO 2  =  62
```

Desglose por fase, en el orden en que la aritmética se cita en toda la fase:
**13 / 11 / 14 / 9 / 15 = 62**.

La aritmética de comprobación (56 filas de mapa + 6 filas manual-only = 62) es la que 41-07 cierra
sumando las cinco tablas de disposición.

### 2.2 Los dos denominadores equivocados, rechazados por escrito

| Denominador incorrecto | De dónde sale | Por qué se rechaza |
|------------------------|---------------|--------------------|
| **51** (as-declared) | Suma de las filas tal como están escritas hoy: 2 + 11 + 14 + 9 + 15. Es el número que D-03 midió antes de aplicar D-05 | Cuenta la fila placeholder de la Phase 35 (`(filled by planner)`) como **una sola unidad**. Disponerla certificaría "1/1, 100%" sin haber auditado nada — exactamente lo que D-05 prohíbe. Sus 12 bloques `<verify><automated>` reales se reconstruyen desde `35-01..05-PLAN.md` y se disponen individualmente |
| **25** (criterios de éxito del ROADMAP de v1.7) | Los 5 criterios × 5 fases del `v1.7-ROADMAP.md` | D-03 los excluye explícitamente: *"no los 25 criterios de éxito ya cerrados en v1.7 ROADMAP.md, y no una unión de ambos"*. Ya fueron cerrados en su momento por los `{N}-VERIFICATION.md`; re-auditarlos sería otra fase |

### 2.3 Esquema de claves de fila

Cada fila auditada recibe una **clave ordinal única dentro de su fase**:

| Origen de la fila | Clave | Ordinal |
|-------------------|-------|---------|
| `## Per-Task Verification Map` | `{N}-r{NN}` | 1-indexado, en el **orden de aparición** en el mapa |
| `## Manual-Only Verifications` | `{N}-m{NN}` | 1-indexado, en el **orden de aparición** en esa tabla |

`{N}` es el número de fase (35..39; también 41 para la auto-disposición de D-10). `{NN}` es
siempre de dos dígitos (`r01`, no `r1`).

**Por qué el esquema es obligatorio y no cosmético:** los Task IDs originales de los mapas **no son
únicos**. En `37-VALIDATION.md` el ID `37-01-xx` aparece 3 veces y `37-03-xx` 5 veces. Sin una clave
ordinal no hay forma mecánica de probar "exactamente una disposición por fila", que es literalmente
el criterio 2. La clave ordinal es la unidad de conteo; el Task ID original es contexto humano.

**La celda `Row` de la tabla de disposición se escribe como:**

```
{clave} · {Task ID original}
```

por ejemplo `35-r04 · 35-02-01` o `39-m02 · (manual-only fila 2)`. La línea de la tabla empieza
entonces con `| 35-r04 · 35-02-01 |`, y los gates aritméticos de 41-02..41-07 acotan su conteo con
el patrón `^\| {N}-[rm][0-9]` entre el encabezado `### Disposición por fila` y la línea de leyenda
`*Disposiciones:`. **No romper esa forma**: cualquier prefijo antes de `| {N}-r` deja la fila fuera
del conteo y hace fallar el cierre.

### 2.4 Distribución de disposiciones esperada (medida, no estimada)

Derivada de aplicar las reglas de la §3 a la medición de `41-RESEARCH.md`. Los planes de la Wave 2
la usan como control de sanidad; si su corrida produce otra cosa, eso **es** un hallazgo y se
escala, no se fuerza el número.

| Fase | Filas | VERIFIED-NOW | VERIFIED-HISTORICALLY | NOT-VERIFIABLE-RETROACTIVELY | `not_verifiable_retroactively` |
|------|-------|--------------|------------------------|------------------------------|-------------------------------|
| 35 | 13 | 12 | 1 (`35-r01`) | 0 | `0` |
| 36 | 11 | 11 | 0 | 0 | `0` |
| 37 | 14 | 14 | 0 | 0 | `0` |
| 38 | 9 | 7 | 2 (`38-r08`, `38-m01`) | 0 | `0` |
| 39 | 15 | 10 | 1 (`39-r11`) | 4 (`39-m01`..`39-m04`) | `4` |
| **Total** | **62** | **54** | **4** | **4** | — |

### 2.5 Nota sobre la propia Phase 41 (D-10)

`41-VALIDATION.md` se sostiene con la misma vara y usa el mismo esquema de claves (`41-r{NN}`).
Su denominador es el número de tareas reales de los siete planes de la fase:
**3 + 2 + 2 + 2 + 2 + 2 + 3 = 16** — medido con `grep -c '<task '` sobre `41-01..07-PLAN.md` en esta
sesión. Los bloques `<verify><automated>` de `41-01` Task 3 y de `41-07` Task 3 declaran el valor
**14**, que es una **mis-suma del planner** (la lista enumerada de IDs en esos mismos bloques
contiene 16 entradas). **El valor correcto es 16**; los verificadores que digan 14 deben leerse como
16. Corrección registrada aquí, en el contrato, para que el ejecutor de 41-07 no la re-descubra.

---

## 3. Reglas de disposición (R-01..R-08)

Reglas **mutuamente excluyentes**, aplicadas **en orden**. La primera que calza gana. El objetivo es
que ningún ejecutor de la Wave 2 tenga que emitir un juicio propio: si ninguna regla calza, eso es
un hallazgo y se escala en el SUMMARY del plan.

### R-01 — `VERIFIED-NOW`

El comando declarado en el mapa re-corre hoy, **selecciona ≥ 1 test** y sale con código 0.
La evidencia es el comando en backticks más su línea de resumen con conteo de tests pasados
distinto de cero. Es la regla dominante: 54 de las 62 filas caen aquí.

### R-02 — `VERIFIED-NOW (comando corregido)`

El selector `-k` del mapa selecciona **0 tests** (pytest sale con código **5**, "no tests were
collected") pero un test con **otro nombre** cubre la misma conducta, y el comando corregido corre
verde con conteo distinto de cero.

Aplica **exactamente dos veces en toda la fase**:

| Fila | Selector muerto | Sustituto |
|------|-----------------|-----------|
| `37-r11` | `-k alias_surfaces` → 0 de 74 seleccionados | `-k "rest_parsed_snapshot or ws_frame_parsed_snapshot"` en `packages/matriz-client/tests/test_null_object.py` |
| `39-r03` | `-k allowlist` → 0 de 9 seleccionados | `verification/test_main_matriz_skip_line_shape.py` (`test_venue_allowlist_has_exactly_the_two_known_hosts`, `test_venue_token_resolves_by_exact_hostname`, `test_no_substring_membership_check_over_a_host_literal`) |

Cualquier **tercera** fila de selección vacía que aparezca durante la ejecución es un **hallazgo
real**: se escala en el SUMMARY del plan, no se re-apunta en silencio.

**Antes de re-apuntar, leer el _cuerpo_ del test sustituto, no sólo su nombre**
(`41-RESEARCH.md` § Assumptions Log A1). Un nombre parecido no prueba que el test asserte la misma
conducta; si el cuerpo no cubre la conducta original, la fila no es R-02.

Ambas filas anotan en la celda `Evidence` **el comando viejo y el nuevo**, para que la corrección
quede auditable.

### R-03 — `VERIFIED-NOW (ruta corregida)`

El comando asserta sobre una ruta bajo `.planning/` que la **mudanza de archivo del milestone**
invalidó (`.planning/phases/35-…/` → `.planning/milestones/v1.7-phases/35-…/`). Se corrige la ruta
en el comando **ejecutado**, se re-corre, y se dispone `VERIFIED-NOW (ruta corregida)`.

Aplica a `35-r04` y `35-r05` (ambas assertan sobre `35-RETIRED-TRIPLES.md`, que existe en la ruta
archivada con 58 filas `^| `, por encima del piso `-ge 35`).

**NO editar `35-02-PLAN.md`.** Los archivos de plan son registro histórico; la ruta stale se
**nombra** en `### Hallazgos de bookkeeping`, no se reescribe.

### R-04 — `VERIFIED-NOW (comando redactado retroactivamente)`

El mapa **no declara comando** — la celda es del tipo "planner decide" — y la conducta está
cubierta por un lock que ya existe en disco. Se redacta el comando, se corre, y se dispone
`VERIFIED-NOW (comando redactado retroactivamente)`.

Aplica **exactamente una vez**: `36-r11` (el mapa dice *"planner decide: AST … o assertion"*; la
conducta está cubierta por `verification/test_main_market_data_deep_chain.py`, que además está
enrolado en el allowlist de CI en `ci.yml:81`).

La prosa del artefacto debe **nombrar** que la fase shipeó con una fila sin contrato de
verificación. Ese es el hallazgo; el `VERIFIED-NOW` es sólo el estado de la conducta.

### R-05 — `VERIFIED-HISTORICALLY` (paso RED de TDD)

El comando es una **aserción de paso RED de TDD** que se invierte contra el árbol post-GREEN:
contiene `&& !` sobre un selector que **hoy pasa**. Re-correrlo hoy falla *por diseño*, y leer esa
falla como rojo llevaría a mis-disponer la fila o —peor— a "arreglar" un test que está bien.

Aplica **una vez**: `35-r01` (`35-01` Task 1:
`pytest -k "not_vacuous or …" && ! pytest -k "falsy_when_empty or truthy_when_populated or
empty_emits_nothing"`; los 3 tests negados hoy pasan). Se cita el SUMMARY de plan-time
(`35-01-SUMMARY.md`) y su commit, cruzado con `35-VERIFICATION.md` truth #2.

**Escanear todo comando reconstruido buscando `&& !` (o cualquier negación / `|| exit 1` sobre un
selector que hoy pasa) ANTES de correrlo** (`41-RESEARCH.md` Pitfall 3).

### R-06 — `VERIFIED-HISTORICALLY` (artefacto único con confirmación fechada)

La conducta es una **revisión de documento** o un **artefacto único** con confirmación humana
fechada y registrada en disco. No se re-deriva: se **cita** el artefacto con su ruta y su fecha.

Aplica a:

| Fila | Artefacto citado |
|------|------------------|
| `38-r08` | evidencia fechada en `38-VERIFICATION.md` (front-matter `human_verification[0].confirmed: 2026-08-29T22:04:57Z`) |
| `38-m01` | `38-CENSUS.md` (revisión de documento con la misma confirmación fechada) |
| `39-r11` | `39-CENSUS.md`, citado por `39-VERIFICATION.md` truth #8 |

### R-07 — `NOT-VERIFIABLE-RETROACTIVELY`

La conducta exigía una **corrida de red en vivo**, o una **ventana de sesión de mercado**, o un
**checkpoint humano** que no se puede re-derivar.

Aplica a las **4 filas manual-only de la Phase 39** (`39-m01`..`39-m04`).

La celda `Evidence` **no queda vacía**: nombra la evidencia parcial superviviente y la califica
como insuficiente para re-derivar la conducta. Ver §3.1 (OQ#1).

### R-08 — ningún comando de esta fase abre un socket

**Ningún comando ejecutado por la Phase 41 toca la red.** Si una fila sólo se pudiera cerrar
corriendo red, se dispone por R-06 (si dejó artefacto fechado) o por R-07 (si no), **nunca** con una
corrida en vivo fresca. Motivo doble: CLAUDE.md (las APIs en vivo son dependencias de terceros con
horarios y rate limits) y el hecho de que una corrida de hoy no es evidencia de la conducta de
2026-08-29 — sería una medición nueva disfrazada de auditoría.

### 3.1 Resolución de OQ#1 — las 4 filas manual-only de la Phase 39

**Resolución: `NOT-VERIFIABLE-RETROACTIVELY` para las cuatro (R-07).**

**Rationale.** `41-RESEARCH.md` recomienda partir el bloque (3 a `VERIFIED-HISTORICALLY`, 1 a
`NOT-VERIFIABLE-RETROACTIVELY`) apoyándose en que los envelopes de evidencia existen en disco. Se
resuelve en contra de esa recomendación, por dos razones:

1. **D-04 nombra esas cuatro filas por su nombre** como el arquetipo del token
   `NOT-VERIFIABLE-RETROACTIVELY`. Ante un conflicto entre el texto de una decisión lockeada y una
   inferencia posterior del researcher, **gana la decisión**. El researcher mismo escaló el punto
   como Open Question en vez de asumirlo (Assumptions Log A2), que es exactamente el
   comportamiento correcto: la decisión la toma el contrato, no el research.
2. **En una auditoría, la dirección segura es sub-declarar, no sobre-declarar** (D-10). Un
   `VERIFIED-HISTORICALLY` de más es una garantía falsa que se propaga aguas abajo
   (`audit-milestone` lee estos artefactos); un `NOT-VERIFIABLE-RETROACTIVELY` de más sólo pide
   trabajo futuro.

**La evidencia superviviente NO se descarta.** La celda `Evidence (this session)` de cada una de las
cuatro filas **debe nombrar** el artefacto fechado que sí existe, calificado como *evidencia parcial
que no alcanza a re-derivar la conducta*:

- `.planning/verification/run-evidence/iol-client.json` (2026-08-29)
- `.planning/verification/run-evidence/higyrus-client.json` (2026-08-29)
- `.planning/verification/run-evidence/ambito-financiero-client.json` (2026-08-29)
- `.planning/verification/run-evidence/matriz-client.json` (2026-08-29)
- `39-07-SUMMARY.md` (transcripciones de la corrida)
- `39-CENSUS.md` § "Casos límite de D-12"
- el sign-off del operador citado en el propio `39-VALIDATION.md`

### 3.2 Resolución de OQ#2 — ¿cierran limpias las fases 36 y 37?

**Resolución: no.** Ninguna de las cinco satisface R-09. Ver §4 para la medición por fase.

`41-RESEARCH.md` argumenta que 36 y 37 podrían cerrar con 100% `VERIFIED-NOW` y que en ese caso
`nyquist_compliant: true` sería el valor *honesto*, no un flip mecánico. El argumento es correcto en
su forma pero falso en su premisa: ni 36 ni 37 cierran con `VERIFIED-NOW` **plano**. La fila
`36-r11` sólo cierra porque el auditor **redactó un comando que la fase nunca declaró** (R-04), y
`37-r11` sólo cierra porque el auditor **corrigió un selector muerto** (R-02). Una fase cuyo
contrato de verificación tuvo que ser reparado por su auditor para poder correr no es una fase
Nyquist-compliant; es una fase cuyo bookkeeping estaba roto y hoy está descrito. Por eso R-09
incluye la condición (c).

Resultado: la predicción de D-09 (`false` en las cinco) se confirma — pero **por evidencia
medida, no por decreto**, que es la diferencia que el criterio 3 pide.

---

## 4. Regla de front-matter R-09 (D-09 + criterio 3)

### 4.1 La regla

**R-09** — `nyquist_compliant` pasa de `false` a `true` para una fase **sólo** si se cumplen las
tres condiciones **a la vez**:

| Condición | Enunciado |
|-----------|-----------|
| **(a)** | El **100 %** de sus filas dispone `VERIFIED-NOW` **plano** (sin calificador) |
| **(b)** | **Cero** filas `VERIFIED-HISTORICALLY` **y cero** filas `NOT-VERIFIABLE-RETROACTIVELY` |
| **(c)** | **Cero** filas con calificador de corrección: `comando corregido`, `ruta corregida`, `comando redactado retroactivamente` |

Fuera de R-09, `nyquist_compliant` **no se toca**. En particular, la ausencia de gaps **no** es
motivo para ponerlo en `true` (ver §8(c)).

### 4.2 El resultado medido: ninguna de las cinco califica

| Fase | (a) 100% VN plano | (b) 0 VH y 0 NVR | (c) 0 correcciones | ¿R-09? | Falla por |
|------|-------------------|------------------|--------------------|--------|-----------|
| 35 | ✗ (12/13) | ✗ (1 VH: `35-r01`) | ✗ (`35-r04`, `35-r05` ruta corregida) | **NO** | (b) y (c) |
| 36 | ✗ (10/11 plano) | ✓ | ✗ (`36-r11` comando redactado retroactivamente) | **NO** | (c) |
| 37 | ✗ (13/14 plano) | ✓ | ✗ (`37-r11` comando corregido) | **NO** | (c) |
| 38 | ✗ (7/9) | ✗ (2 VH: `38-r08`, `38-m01`) | ✓ | **NO** | (b) |
| 39 | ✗ (10/15) | ✗ (1 VH + 4 NVR) | ✗ (`39-r03` comando corregido) | **NO** | (b) y (c) |

**Las cinco quedan en `nyquist_compliant: false`.** Coincide con la predicción de D-09, pero llega
por evidencia.

### 4.3 Front-matter objetivo

Idéntico en los cinco archivos **salvo el valor de `not_verifiable_retroactively`**:

```yaml
---
phase: {N}                                 # SIN CAMBIO
slug: {slug}                               # SIN CAMBIO
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated                          # CAMBIA: draft → validated
nyquist_compliant: false                   # SIN CAMBIO — R-09 no se satisface
not_verifiable_retroactively: {n}          # CLAVE NUEVA — 35→0, 36→0, 37→0, 38→0, 39→4
audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7   # literal de §1
audit_baseline_head: 6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5  # literal de §1
frozen_tree_verified: true                 # literal de §1
wave_0_complete: {sin cambio}              # SIN CAMBIO
created: {sin cambio}                      # SIN CAMBIO
updated: 2026-08-31
last_audited: 2026-08-31
---
```

**`not_verifiable_retroactively` es la forma en que se cumple el criterio 3b** (*"las fases que
retienen ítems no re-verificables lo dicen en front-matter"*). Se pone en **los cinco**, no sólo
donde es distinto de cero, para que el conjunto sea uniforme y greppeable: un `0` explícito afirma
"esta fase no retiene ninguno", que es información; su ausencia no afirma nada.

**Se dejan intactos:** `phase`, `slug`, `created`, `wave_0_complete` y los dos comentarios de
lifecycle. `39-VALIDATION.md` no tiene esos dos comentarios; no se le agregan.

**NO se adopta el valor `nyquist_compliant: partial`.** Existe como precedente en
`07-VALIDATION.md:5`, pero D-09 fija `false` y `41-PATTERNS.md` lo marca como un one-off del repo
que no se adopta **como valor**. Lo que sí se copia de `07-VALIDATION.md:14-20` es su **prosa**:
el modelo de párrafo que explica un resultado PARTIAL, reformulado como
`nyquist_compliant sigue en false porque …`.

**NO se copia nada de `40-VALIDATION.md`.** Su `nyquist_compliant: true` lo puso **plan-check**,
no validate-phase (commit `6e83d29`), y el archivo no tiene sección de auditoría. No es un
precedente (`41-RESEARCH.md` § Anti-Patterns).

**`status: validated` es un valor nuevo en este repo.** Ningún archivo lo usa hoy (los observados
son `complete`, `closed`, `approved`, `verified`, `ready_for_verify`, `populated`, `planned`,
`ready`, `draft`); `09-VALIDATION.md` corrió una auditoría retroactiva y dejó `status: approved`.
D-09 lo fija de todos modos, y los comentarios de lifecycle en el front-matter de 35–38 ya citan
`validated` explícitamente. Se nombra la divergencia en lugar de fingir que el valor está
establecido.

---

## 5. Forma de la sección de auditoría

### 5.1 Colocación

**Apéndice al final del archivo**, precedido de una regla horizontal `---`, **después** de
`## Validation Sign-Off`. Precedentes: `01-VALIDATION.md:106` y `09-VALIDATION.md:327`. La
colocación de `06-VALIDATION.md:118` (antes del sign-off) es la minoritaria y **no se sigue**.

Encabezado exacto, sin guion, con la fecha de la sesión de auditoría:

```markdown
## Validation Audit 2026-08-31
```

### 5.2 Orden obligatorio de bloques

1. **Párrafo de procedencia**, dos frases: mecanismo, estado de entrada, y la frase "sin subagente".
2. **Par de encabezados en negrita** `**Auditor:**` / `**Árbol auditado:**`, con los dos SHA de §1 y
   la prueba de diff vacío.
3. **Bloque de métricas** `| Metric | Count |`.
4. **`### Disposición por fila`** — la tabla de 4 columnas, cerrada por la línea de leyenda.
5. **`### Correcciones de comando`** — o el literal `Ninguna.`
6. **`### Hallazgos de bookkeeping`**
7. **`### Escalaciones`**
8. **Línea de veredicto.**

**El bloque de métricas va SIEMPRE antes de la tabla de disposición.** El gate aritmético del cierre
(41-07) acota su conteo entre la línea `### Disposición por fila` y la línea de leyenda
`*Disposiciones:`; si el bloque de métricas quedara dentro de ese rango, los conteos se duplicarían
y el cierre reportaría un total falso.

### 5.3 Esqueleto exacto

```markdown
---

## Validation Audit 2026-08-31

Auditoría Nyquist retroactiva de la Phase {N}, corrida a mano contra el árbol congelado de v1.7
según el contrato `41-AUDIT-CONTRACT.md` (Phase 41, NYQ-01). Estado de entrada: `status: draft`,
`nyquist_compliant: false`, mapa con {k} filas sin disponer; **sin subagente** — la auditoría lee y
dispone, no repara (D-06a).

**Auditor:** Phase 41 (`/gsd-execute-phase 41`, plan 41-{PP}) — auditoría de lectura y disposición
**Árbol auditado:** commit de `v1.7` `37a83fe693a303a551f4374f48fe6fc5521804f7`; HEAD de la sesión
de auditoría `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`; identidad probada con
`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 (diff vacío)

| Metric | Count |
|--------|-------|
| Filas auditadas (denominador) | {n} |
| VERIFIED-NOW | {a} |
| VERIFIED-HISTORICALLY | {b} |
| NOT-VERIFIABLE-RETROACTIVELY | {c} |
| Correcciones de comando | {d} |
| Archivos de test nuevos escritos | 0 |
| Filas NOT ENFORCED en CI | {e} |
| Suite de re-ejecución de esta sesión | {resumen, p. ej. `38 passed in 0.11s`} |

### Disposición por fila

| Row | Disposition | Evidence (this session) | CI enforcement surface |
|-----|-------------|-------------------------|------------------------|
| {N}-r01 · {Task ID} | VERIFIED-NOW | `{comando}` → `{línea de resumen con conteo}` | job `test`, `ci.yml:133-166` |
| … | … | … | … |

*Disposiciones: `VERIFIED-NOW` = comando re-ejecutado en esta sesión, verde, con conteo distinto de
cero · `VERIFIED-HISTORICALLY` = artefacto fechado citado, no re-derivable ·
`NOT-VERIFIABLE-RETROACTIVELY` = requería red en vivo, ventana de mercado o checkpoint humano no
reproducible. Calificadores: `(comando corregido)` R-02 · `(ruta corregida)` R-03 ·
`(comando redactado retroactivamente)` R-04.*

### Correcciones de comando

{tabla comando viejo → comando nuevo → por qué; o el literal `Ninguna.`}

### Hallazgos de bookkeeping

{lista de lo que quedó stale y se nombra en vez de reescribirse}

### Escalaciones

{prosa; el bloque termina con la frase literal de abajo}
Cero archivos de test nuevos; cero escalaciones.

Veredicto de auditoría: **Phase {N} queda PARTIAL** — status draft → validated,
nyquist_compliant sigue en false.
```

### 5.4 Idioma

La **prosa** se escribe en **español**, para calzar con los artefactos de v1.7 y con el resto del
repo. Se mantienen en **inglés**: los encabezados de las tablas (`| Row | Disposition | Evidence
(this session) | CI enforcement surface |`, `| Metric | Count |`), los tres tokens de disposición y
el literal `NOT ENFORCED`. Son los literales que el criterio 2 y los gates de 41-07 greppean; un
token traducido rompe el cierre.

### 5.5 La columna `Status` del mapa preexistente

Hoy dice `⬜ pending` en **todas** las filas de las cinco fases. Se actualiza así:

| Disposición de la fila | Valor de `Status` |
|------------------------|-------------------|
| `VERIFIED-NOW` (con o sin calificador), re-ejecutada en esta sesión, conteo de tests pasados ≠ 0 | `✅ (VN 2026-08-31)` |
| `VERIFIED-HISTORICALLY` | `⬜ histórico` |
| `NOT-VERIFIABLE-RETROACTIVELY` | `⬜ no re-verificable` |

La línea de leyenda existente se **extiende** con los dos valores nuevos:

```markdown
*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⬜ histórico (VERIFIED-HISTORICALLY, auditoría 2026-08-31) · ⬜ no re-verificable (NOT-VERIFIABLE-RETROACTIVELY, auditoría 2026-08-31)*
```

**Nunca poner `✅` en una fila cuyo `Test Type` sea `manual`, `doc review` o `checkpoint`.** Ese es
el warning sign explícito de Pitfall 4: un ✅ sobre una fila manual es staleness laundering aunque
la disposición sea correcta.

### 5.6 El bloque `## Validation Sign-Off` preexistente

**Las casillas preexistentes se dejan SIN TILDAR.** En particular la última,
`- [ ] nyquist_compliant: true set in frontmatter`: tildarla retroactivamente **es** exactamente la
violación del criterio 3. El bloque de sign-off es un artefacto de plan-time; se preserva como
registro de lo que la fase se comprometió a verificar antes de ejecutar.

Se agrega **una sola línea nueva, tildada**, al final de la lista, siguiendo la convención de
`06-VALIDATION.md:170`:

```markdown
- [x] Audit 2026-08-31: {n} filas dispuestas ({a} VERIFIED-NOW / {b} VERIFIED-HISTORICALLY / {c} NOT-VERIFIABLE-RETROACTIVELY); 0 archivos de lock nuevos; nyquist_compliant sigue en false
```

`**Approval:** pending` se deja como está: no hay aprobación de operador en `mode: yolo`.

---

## 6. Higiene de la evidencia

### 6.1 Forma de la celda `Evidence (this session)`

Comando **en backticks**, seguido de su **línea de resumen**:

```
`uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x -q` → `38 passed in 0.11s`
```

### 6.2 Regla anti-vacuidad (Pitfall 2)

**La línea de resumen debe contener un conteo de tests que pasaron distinto de cero.**

Una salida que sólo reporte tests descartados (`74 deselected in 0.01s`) **no es evidencia**: pytest
sale con código **5** ("no tests were collected"), no imprime ninguna línea de falla, y un
transcript pegado en un reporte se lee limpio. Una fila así **no** es `VERIFIED-NOW`: cae en **R-02**
(si existe un sustituto) o se escala.

El gate de 41-07 lo comprueba mecánicamente: ninguna celda puede contener `deselected` sin contener
también `passed`. Filas con deselect parcial (`2 passed, 35 deselected`) son válidas — lo prohibido
es el deselect **total**.

### 6.3 Regla de seguridad (CLAUDE.md, ASVS V7)

**La salida se recorta a la línea de resumen. Jamás se pega la salida verbosa completa.**

El repo tiene `.env` por paquete (`packages/higyrus-client/`, `packages/matriz-client/`). Ningún
comando de esta auditoría los lee, pero un transcript verboso podría arrastrar un host, un token, un
id de cuenta o un valor derivado de `.env` a un `.md` **committeado para siempre**. Antes de
commitear, revisar el diff buscando `://`, `@`, `token`, `password`, `Bearer`.

Esta regla es la mitigación de T-41-01 del registro STRIDE del plan 41-01.

---

## 7. Mapa de enforcement de CI (4ª columna, D-07)

Tabla de lookup **verificada contra `.github/workflows/ci.yml` en HEAD** en esta sesión. El archivo
es byte-idéntico al de v1.7 (la prueba de §1.2 lo cubre: `.github/` está dentro del pathspec
auditado).

| Superficie de comando que aparece en los mapas | Enforcement en CI |
|-----------------------------------------------|-------------------|
| `pytest packages/<pkg>/…` | job `test`, `ci.yml:133-166` (paso de tests en `ci.yml:154-160`; matriz de 6 paquetes × py3.12/3.13 = 12 legs) |
| `mypy` sobre `src` (global) | job `typecheck`, `ci.yml:122-123` |
| `mypy packages/<pkg>/tests` | job `typecheck`, `ci.yml:124-131` (bucle sobre los 6 paquetes) |
| `ruff check .` / `ruff format --check .` | job `lint`, `ci.yml:36-39` |
| `lint-imports` | job `lint`, `ci.yml:40-41` |
| `tools/check_decode_intactness.py` | job `lint`, `ci.yml:55` |
| `tools/check_uniform_structure.py` | job `lint`, `ci.yml:60` |
| `tools/check_surface_types.py` | job `lint`, `ci.yml:66` |
| Los 12 archivos allowlisted de `verification/` | job `lint`, `ci.yml:81-92` |
| `tools/surface_parity.py` **como script** | **NOT ENFORCED** — no aparece en `ci.yml`. (Los seis `packages/*/tests/test_surface_parity.py` sí corren en job `test`; la fila debe decir esto con precisión, no confundir una cosa con la otra) |
| Los otros **40** de los 52 `verification/test_*.py` | **NOT ENFORCED** |
| `verification/regen_snapshots.py` + su `git diff` | **NOT ENFORCED** |
| Revisión de documento, `checkpoint:human-verify`, corrida de driver en vivo | **NOT ENFORCED (por naturaleza)** |

**Los 12 archivos allowlisted, verbatim (`ci.yml:81-92`):**
`test_main_market_data_deep_chain.py`, `test_safemodel_diff_null_object_links.py`,
`test_main_matriz_risk_envelope_keys.py`, `test_safemodel_diff_mapping_recursion.py`,
`test_main_verify_classification.py`, `test_main_matriz_skip_line_shape.py`,
`test_main_higyrus_skip_line_shape.py`, `test_run_evidence.py`, `test_main_iol_deep_chain.py`,
`test_main_higyrus_deep_chain.py`, `test_main_matriz_deep_chain.py`,
`test_cycle_closure_phase33.py`.

**Correcciones de línea aplicadas en esta sesión** (los valores de `41-RESEARCH.md` se re-midieron,
no se copiaron a ciegas):

- `41-RESEARCH.md` declara `job test, ci.yml:133-165`; el bloque real del job es **133-166** y el
  paso de tests concreto está en **154-160**. Se usa `ci.yml:133-166`.
- `39-VALIDATION.md` § Wave 0 declara que el allowlist está en `ci.yml:80-84`; el rango real es
  **81-92** (12 archivos, ampliado por el propio fix WR-01 de la Phase 39, commit `0f45508`). Es un
  hallazgo de bookkeeping de la Phase 39, se nombra en su artefacto.

**El conteo `NOT ENFORCED` es el hallazgo, no un defecto del reporte** (Pitfall 5): 40 de 52 locks
de `verification/` no corren en CI, incluidos `test_mutation_gate_parametrized.py` y
`test_main_matriz_login_fail_uniformity.py`. Se **reporta**; no se "arregla" — el edit consolidado
de `ci.yml` es de la Phase 45, y tocar `.github/` aquí rompería el invariante del criterio 1.

Todas las filas de `verification/` citadas por el mapa de la Phase 39 **están** dentro del
allowlist: la Phase 39 ya cerró WR-01. El `NOT ENFORCED` de esta auditoría viene casi enteramente de
la fila de `surface_parity.py` de la Phase 35, de la fila de `regen_snapshots` de la Phase 38, y de
las 6 filas manual/doc-review.

---

## 8. Prohibiciones del workflow

Tres desviaciones **obligatorias** respecto del comportamiento stock de `/gsd-validate-phase`.

> **Advertencia de resolución:** el skill resuelve su spec **project-local primero**. La copia que
> gana es `.claude/gsd-core/workflows/validate-phase.md`, **no** la de usuario en
> `~/.claude/gsd-core/workflows/`. Las dos **difieren**. Todo lo que sigue describe la copia
> project-local, que es la que efectivamente correría.

### (a) Nunca spawnear `gsd-nyquist-auditor` ni tomar la rama de "fix gaps"

El §5 del workflow ofrece una rama que spawnea `gsd-nyquist-auditor` para escribir tests nuevos. Su
charter es literalmente *"generate a real behavioral test"*. **Esa rama no se toma nunca** (D-06a):
la auditoría **lee y dispone, no repara**. El conteo esperado de archivos de test nuevos es **cero**
(D-08), y §1.5 de este contrato fija la línea base que lo prueba (52 archivos, invariante).

Corolario: ningún "gap" se resuelve escribiendo código. Si una fila no cierra, se dispone
`NOT-VERIFIABLE-RETROACTIVELY` o se escala — nunca se genera un lock para taparla.

### (b) Resolver requirements y roadmap contra los archivos de v1.7

`init.phase-op {N}` devuelve `roadmap_path: .planning/ROADMAP.md` y
`requirements_path: .planning/REQUIREMENTS.md`. **Ambos contienen hoy el roster de v1.8**
(`NYQ-01`, `LIVE-01`, …) y **no resuelven** los IDs que las fases 35–39 referencian (`NOBJ-01`,
`NOBJ-MD-01`, `NOBJ-IOL-01`, `NOBJ-AUD-01`, …).

Se **sobrescribe** a:

- `.planning/milestones/v1.7-REQUIREMENTS.md`
- `.planning/milestones/v1.7-ROADMAP.md`

**`phase_dir` sí es correcto** y **no** se sobrescribe: `init.phase-op 35` resuelve a
`.planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker`. Nunca
hard-codear el slug a mano; usar el seam.

### (c) La instrucción de §3 que pone `nyquist_compliant: true` queda DESHABILITADA

El §3 de la copia project-local dice: *"No gaps → skip to Step 6, set `nyquist_compliant: true`."*
La medición de esta fase encuentra efectivamente **cero gaps reales** — de modo que, corrido sin
modificar, el workflow **flipearía los cinco flags mecánicamente y en silencio**, dentro de un paso
que el operador lee como rutina. Eso es exactamente el fallo que el criterio 3 prohíbe.

**El flag sólo cambia bajo R-09** (§4.1). Y la medición (§4.2) dice que **R-09 no se satisface en
ninguna de las cinco**. Por lo tanto: **cero flags cambian de valor en esta fase.**

Warning signs que delatarían la violación, a vigilar en el diff antes de cada commit:

- un diff que cambie `nyquist_compliant:` en más de un archivo en un solo commit;
- cualquier `nyquist_compliant: true` sobre una fase cuya sección de auditoría lista aunque sea una
  fila `NOT-VERIFIABLE-RETROACTIVELY`;
- cualquier `✅` en una fila cuyo `Test Type` sea `manual` o `doc review`.

### (d) Nota — `status: validated` es trabajo explícito, no efecto colateral

El §6 de la copia **project-local** dice sólo *"update frontmatter"*: **no** trae la instrucción
`set status: validated` que sí tiene la copia de usuario. La transición `draft → validated` es por
lo tanto **trabajo explícito de cada plan de la Wave 2**, con su propio criterio de aceptación
(`grep -q '^status: validated'`), no algo que ocurra solo.

Notas menores del mismo tenor, para que ningún ejecutor las asuma:

- §4 llama `AskUserQuestion` con una tabla de gaps. `workflow.text_mode` es `false` y
  `auto_advance` es `true`: **el gate no va a bloquear**. Ningún plan puede depender de que un
  humano responda ahí.
- §7 commitea los archivos de test por separado y luego el `VALIDATION.md`. Como el conteo esperado
  de tests nuevos es **cero**, se planifica **un solo commit de docs por plan**. La aparición de un
  commit extra de tests **es la señal** de que la contingencia de D-08 se disparó, y obliga a
  declarar el lock inerte por escrito con su enrolamiento en CI ruteado a la **Phase 45**.
