# 41-ROLLUP.md — cierre cross-fase de la auditoría Nyquist retroactiva de v1.7

**El número que este documento produce —54 de 62 filas `VERIFIED-NOW`— es exactamente el que más
fácil se lee mal.** Leído rápido dice "las cinco fases de v1.7 están cubiertas". No dice eso. Dice
que el *bookkeeping* de esas cinco fases estaba stale y hoy está descrito, y que **8 de las 62 filas
siguen sin cobertura re-derivable**: 4 sólo se sostienen citando un artefacto fechado que nadie puede
volver a producir, y 4 exigían una sesión de mercado en vivo que no vuelve. Un `VERIFIED-HISTORICALLY`
no es una verificación: es una cita. Un `NOT-VERIFIABLE-RETROACTIVELY` no es una verificación: es una
deuda declarada. Sumarlos al 54 para reportar "62/62 dispuestas" es correcto sobre el criterio 2 —
cero filas sin disponer— y falso sobre cualquier lectura de cobertura. Y por debajo de eso hay un
segundo piso: **13 de las 62 filas no tienen ninguna superficie de enforcement en CI**, y **40 de los
52 locks de `verification/` no corren en ninguna pata del pipeline**. Un lock que no corre no cuenta
como cobertura.

La otra forma de fallar acá no es sub-medir: es **re-derivar una unidad de conteo ligeramente distinta
de la que usan los cinco artefactos auditados**, produciendo un número que parece un resultado y es un
error de traducción. Por eso la sección `## Unidad de conteo` va **antes** de la primera suma, y por eso
esta fase rechaza por su número los dos denominadores plausibles y equivocados.

> **Índice secundario, no fuente de verdad (D-01).** Este archivo **no** es autoritativo. Los
> artefactos autoritativos son los cinco `{N}-VALIDATION.md` de v1.7 (Phases 35, 36, 37, 38, 39), cada
> uno con su propia sección `## Validation Audit 2026-08-31`, y el contrato
> `41-AUDIT-CONTRACT.md`. Todo número de este documento se **deriva** de esas cinco tablas por
> extracción acotada, nunca se declara a mano. Si este archivo y un `{N}-VALIDATION.md` discrepan,
> **gana el `{N}-VALIDATION.md`** y este archivo está roto.

---

## Unidad de conteo

**La unidad de este cierre es la fila de disposición con clave ordinal `{N}-r{NN}` / `{N}-m{NN}`**
(`41-AUDIT-CONTRACT.md § 2.3`), tomada de la sección `### Disposición por fila` de cada uno de los
cinco artefactos. `r` numera las filas del `## Per-Task Verification Map` en su orden de aparición;
`m` numera las del `## Manual-Only Verifications`. `{NN}` es siempre de dos dígitos.

**Por qué la clave ordinal y no el Task ID original.** Los Task IDs de los mapas **no son únicos**: en
`37-VALIDATION.md` el ID `37-01-xx` aparece 3 veces y `37-03-xx` 5 veces. Sin una clave ordinal no hay
forma mecánica de probar "exactamente una disposición por fila", que es literalmente lo que pide el
criterio 2. La clave ordinal es la unidad contable; el Task ID original es contexto humano y viaja en
la misma celda tras un `·`.

**El denominador es 62**, con este desglose canónico:

```
Phase 35 :  12 filas de mapa reconstruidas  +  1 fila manual-only   =  13
Phase 36 :  11 filas de mapa                +  0 filas manual-only  =  11
Phase 37 :  14 filas de mapa                +  0 filas manual-only  =  14
Phase 38 :   8 filas de mapa                +  1 fila manual-only   =   9
Phase 39 :  11 filas de mapa                +  4 filas manual-only  =  15
                                                                      ----
                                            TOTAL DEL CRITERIO 2  =  62
```

Desglose canónico citado en toda la fase: **13 / 11 / 14 / 9 / 15**. Aritmética de comprobación:
56 filas de mapa + 6 filas manual-only = 62.

**Los dos denominadores equivocados, rechazados por su número:**

| Denominador incorrecto | De dónde sale | Por qué se rechaza |
|------------------------|---------------|--------------------|
| **51** | Suma de las filas *tal como estaban escritas* antes de la auditoría: 2 + 11 + 14 + 9 + 15 | Cuenta la fila placeholder de la Phase 35 (`(filled by planner)`) como **una sola unidad**. Disponerla certificaría "1/1, 100 %" sin haber auditado nada. Sus 12 bloques `<verify><automated>` reales se reconstruyeron desde `35-01..05-PLAN.md` y se dispusieron individualmente (D-05) |
| **25** | Los 5 criterios de éxito × 5 fases del `v1.7-ROADMAP.md` | D-03 los excluye explícitamente. Ya fueron cerrados en su momento por los `{N}-VERIFICATION.md`; re-auditarlos sería otra fase, no ésta |

**Método de extracción.** Cada conteo de este documento sale de acotar la tabla entre la línea
`### Disposición por fila` y la línea de leyenda `*Disposiciones:`, y contar dentro de ese rango las
líneas que empiezan con `| {N}-r` o `| {N}-m`. El acotamiento es **obligatorio**: el bloque de
métricas, que va más arriba en el mismo archivo, también contiene los tres tokens de disposición, y
sin acotar cada conteo se duplicaría. Ése es el motivo por el que `41-AUDIT-CONTRACT.md § 5.2` fija
el orden de bloques con las métricas **antes** de la tabla.

---

## Criterio 2 — la aritmética, derivada

| Fase | Filas | VERIFIED-NOW | VERIFIED-HISTORICALLY | NOT-VERIFIABLE-RETROACTIVELY | Suma | ¿Suma = filas? |
|------|-------|--------------|------------------------|------------------------------|------|----------------|
| 35 | 13 | 12 | 1 | 0 | 13 | ✅ |
| 36 | 11 | 11 | 0 | 0 | 11 | ✅ |
| 37 | 14 | 14 | 0 | 0 | 14 | ✅ |
| 38 | 9 | 7 | 2 | 0 | 9 | ✅ |
| 39 | 15 | 10 | 1 | 4 | 15 | ✅ |
| **Total** | **62** | **54** | **4** | **4** | **62** | ✅ |

`54 + 4 + 4 = 62`. `13 + 11 + 14 + 9 + 15 = 62`. Los dos caminos cierran contra el mismo número.

**Por qué la igualdad `suma == filas` prueba las dos mitades del criterio 2 de una vez.** Si alguna
fila hubiera quedado sin disponer, no aportaría ningún token y la suma sería **menor** que el conteo
de filas. Si alguna llevara dos disposiciones, aportaría dos tokens y la suma sería **mayor**. La
igualdad exacta, verificada por fase y no sólo en el total, es simultáneamente la prueba de *cero
filas sin disponer* y de *cero filas con doble disposición*. Un gate sólo sobre el total sería más
débil: dos errores de signo opuesto en fases distintas se cancelarían.

**Anti-vacuidad (`41-AUDIT-CONTRACT.md § 6.2`).** Sobre los mismos cinco rangos acotados, las líneas
que reportan tests descartados sin reportar ningún test ejecutado suman **0**. El chequeo importa
porque una corrida de pytest que sólo descarta sale con código 5, no imprime ninguna línea de falla, y
pegada en un reporte se lee limpia mientras nada corrió. Filas con descarte parcial
(`2 passed, 72 deselected`) son válidas; lo prohibido es el descarte total.

**Cero correcciones aplicadas por este cierre.** El gate de la tarea 1 de `41-07` es de lectura: sólo
habría tocado un artefacto si un conteo no cerraba, y en ese caso habría corregido el artefacto, nunca
el número esperado. No hizo falta: las cinco tablas cerraron a la primera contra la distribución
prevista en `41-AUDIT-CONTRACT.md § 2.4` (54 / 4 / 4), que era un control de sanidad y no una cuota.

---

## Criterio 3 — ningún flag pasó a `true`, y la evidencia lo sostiene

**R-09** (`41-AUDIT-CONTRACT.md § 4.1`) exige tres condiciones simultáneas para mover
`nyquist_compliant` de `false` a `true`: (a) 100 % de filas `VERIFIED-NOW` **plano**, (b) cero
`VERIFIED-HISTORICALLY` y cero `NOT-VERIFIABLE-RETROACTIVELY`, (c) cero filas con calificador de
corrección (`comando corregido`, `ruta corregida`, `comando redactado retroactivamente`).

| Fase | VN plano / filas | (a) | (b) | (c) correcciones | ¿R-09? | Falla por |
|------|------------------|-----|-----|------------------|--------|-----------|
| 35 | 10 / 13 | ✗ | ✗ (1 VH) | ✗ (2) | **NO** | (a), (b), (c) |
| 36 | 10 / 11 | ✗ | ✓ | ✗ (1) | **NO** | (a), (c) |
| 37 | 13 / 14 | ✗ | ✓ | ✗ (1) | **NO** | (a), (c) |
| 38 | 7 / 9 | ✗ | ✗ (2 VH) | ✓ (0) | **NO** | (a), (b) |
| 39 | 9 / 15 | ✗ | ✗ (1 VH + 4 NVR) | ✗ (1) | **NO** | (a), (b), (c) |

**Ninguna de las cinco califica.** Coincide con la predicción de D-09, pero llega por medición: las
Phases 36 y 37 habrían calificado bajo una R-09 de dos condiciones, y no califican porque su contrato
de verificación tuvo que ser **reparado por su propio auditor** para poder correr (`36-r11` cerró con
un comando redactado retroactivamente que la fase nunca declaró; `37-r11` cerró con un selector muerto
re-apuntado). Una fase así no es Nyquist-compliant; es una fase cuyo bookkeeping estaba roto y hoy
está descrito. Ésa es la razón de existir de la condición (c).

**Gates de front-matter, medidos sobre los cinco archivos:**

| Gate | Resultado |
|------|-----------|
| Archivos con `nyquist_compliant: true` | **0** de 5 |
| Archivos con `status: validated` | **5** de 5 |
| Archivos con la clave `not_verifiable_retroactively` presente | **5** de 5 |
| Valores de esa clave | cuatro en `0`, uno en `4` (Phase 39) |
| Casillas de sign-off preexistentes tildadas retroactivamente sobre el flag | **0** en los 5 |
| Valores distintos de `audited_commit_sha` | **1** (`37a83fe693a303a551f4374f48fe6fc5521804f7`) |
| Valores distintos de `audit_baseline_head` | **1** (`6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`) |
| Valores distintos de `frozen_tree_verified` | **1** (`true`) |

La clave `not_verifiable_retroactively` es la forma en que se cumple el criterio 3b. Va en los cinco
archivos, incluso donde vale `0`: un `0` explícito afirma *"esta fase no retiene ninguno"*, que es
información; su ausencia no afirma nada. La única fase que retiene ítems no re-verificables —la
Phase 39, con 4— lo dice en su propio front-matter en vez de reportarse limpia.

La casilla preexistente `- [ ] nyquist_compliant: true set in frontmatter` quedó **sin tildar** en los
cinco. Tildarla retroactivamente es la misma especie de lavado que el criterio 3 prohíbe, aunque el
flag en sí no se hubiera movido.

---

## Enforcement en CI — el hallazgo que este rollup existe para no tapar

### Filas sin superficie de enforcement, por fase

| Fase | Filas | Filas `NOT ENFORCED` | Origen |
|------|-------|----------------------|--------|
| 35 | 13 | **5** | `surface_parity.py` como script (no aparece en `ci.yml`), las dos filas de ruta corregida sobre artefactos de `.planning/`, el paso RED de TDD, y la fila manual-only |
| 36 | 11 | **0** | las 11 caen sobre `pytest` de paquete, `mypy` o locks allowlisted |
| 37 | 14 | **0** | ídem |
| 38 | 9 | **3** | `regen_snapshots.py` + su `git diff`, la fila de confirmación humana fechada, y la fila manual-only de revisión de documento |
| 39 | 15 | **5** | la fila de contraste de censo y las 4 manual-only en vivo |
| **Total** | **62** | **13** | — |

13 de 62 filas (21 %) no tienen ninguna pata de CI que las vuelva a romper si la conducta regresa. De
esas 13, seis lo son **por naturaleza** (revisión de documento, checkpoint humano, corrida de driver en
vivo) y no admiten enrolamiento; las otras siete son scripts y locks que sí podrían correr.

### Los tres números del árbol de locks, re-medidos contra el árbol actual

| Medida | Valor | Comando |
|--------|-------|---------|
| Archivos `verification/test_*.py` en disco | **52** | `ls verification/test_*.py \| wc -l` |
| De ésos, enrolados en el allowlist explícito del job `lint` | **12** | `ci.yml:81-92` |
| **Sin enrolar — no corren en ninguna pata de CI** | **40** | 52 − 12 |
| Archivos de test **nuevos** escritos por esta auditoría | **0** | `git status --porcelain verification/` vacío |

Los tres coinciden exactamente con la línea base de `41-AUDIT-CONTRACT.md § 1.5`, capturada antes del
primer artefacto de la fase. Un 53 habría sido la señal de que la contingencia de D-08 se disparó.

---

## Declaración inerte (criterio 4) — ruteo a la Phase 45

**Cero locks nuevos.** El criterio 4 es una cláusula de contingencia, no un entregable: la auditoría
**lee y dispone, no repara** (D-06a). El conteo esperado de archivos de test nuevos era **cero** y el
conteo real es **cero**. Ninguna fila se cerró escribiendo código: las que no cerraron se dispusieron
`VERIFIED-HISTORICALLY` o `NOT-VERIFIABLE-RETROACTIVELY`, que es donde el criterio 4 quiere que caigan.

**Donde el criterio 4 sí muerde es en los locks preexistentes**, y ésta es su declaración formal:

> **Declaración inerte.** De los **52** archivos `verification/test_*.py` presentes en el árbol,
> sólo **12** están enrolados en el allowlist explícito del job `lint` de `.github/workflows/ci.yml`
> (líneas 81-92). Los **40** restantes **no corren en ninguna pata del pipeline** y quedan por la
> presente **declarados inertes**: existen en disco, pasan si se los invoca a mano, y **no cuentan
> como cobertura** para ningún criterio de ningún milestone hasta que estén enrolados. Entre ellos
> hay locks de conducta real —`test_mutation_gate_parametrized.py`,
> `test_main_matriz_login_fail_uniformity.py`— cuya regresión hoy no rompería CI.
>
> **Su enrolamiento queda ruteado al edit consolidado de `ci.yml` de la Phase 45**, cuyo criterio de
> éxito 5 exige que *todos* los edits de `ci.yml` del milestone lleguen en **un** cambio consolidado
> del allowlist con CI verde en las 12 patas de la matriz. La precondición cross-fase ya está
> registrada en `.planning/REQUIREMENTS.md § Traceability`:
> *"Locks generados por el auditor, pendientes de enrolar en CI — producida en Phase 41 (criterio 4),
> consumida por Phase 45 (criterio 5)"*. El requisito que la absorbe es **HARN-03** (cierre del gap
> `IN-06`, archivo de `verification/` fuera del allowlist explícito) junto con **HARN-04** (destino
> del `verification/` de matriz).

**La Phase 41 no edita `.github/workflows/ci.yml`, y eso es deliberado.** Tocarlo aquí rompería el
invariante del criterio 1 —`.github/` está dentro del pathspec auditado— y le robaría a la Phase 45 la
consolidación que su criterio 5 exige. Verificado: `git diff --quiet <baseline> HEAD -- .github/workflows/ci.yml`
sale **0**.

---

## Criterio 5 — contención de alcance, con tres gates

Seis artefactos de validación **más** del repo están hoy en el mismo estado de borrador que las cinco
auditadas —los de las Phases 18, 25, 29, 30, 32 y 33— y ampliarles la auditoría está literalmente a un
`grep` de distancia. Por eso la contención se prueba, no se asume.

| Gate | Qué mide | Resultado |
|------|----------|-----------|
| **1** | Artefactos de validación de v1.7 cambiados desde el HEAD de baseline | **5** — exactamente los de las Phases 35, 36, 37, 38 y 39 |
| **2** | Artefactos de validación **fuera de alcance** en el diff (Phases 18, 25, 29, 30, 32, 33) | **0**. El total de rutas terminadas en `VALIDATION.md` en el diff es **6**: los cinco de v1.7 más el `41-VALIDATION.md` de esta misma fase |
| **3** | La fila de alcance excluido de `REQUIREMENTS.md` que nombra el gap del milestone anterior | **byte-intacta** — hash idéntico al de la misma fila en el commit de baseline |

Además, **ningún archivo fuera de `.planning/` aparece en el diff acumulado de la fase**: cero `.py`,
cero `.yml`, cero `.toml`.

**El matiz que hay que anotar para que nadie salga a buscar lo que no existe:** no hay ninguna entrada
de backlog en `ROADMAP.md` con el nombre literal del gap del milestone anterior. La entrada de backlog
del ROADMAP es la de esta misma fase. El ítem excluido vive **únicamente** como fila de la tabla
`## Out of Scope` de `.planning/REQUIREMENTS.md` (línea 44), que es exactamente donde el criterio 5
dice que está. El gate verifica esa fila, y sólo esa.

---

## Criterio 1 — el invariante de árbol congelado, cerrado

```bash
git diff --quiet v1.7 HEAD -- . ':(exclude).planning'   # exit 0
```

Ejecutado al abrir la fase (`41-01` Task 1), al inicio y al cierre de cada tarea de la Wave 2, y otra
vez aquí, después de que el último de los cinco artefactos quedó escrito. **Sale 0 en todos los
puntos.** El pathspec de exclusión es obligatorio: `.planning/` churnea legítimamente durante toda la
fase, y sin excluirlo la prueba fallaría siempre por una razón irrelevante. Lo que afirma es
exactamente: *ningún byte de `packages/`, `verification/`, `tools/`, `.github/` ni de la raíz cambió
entre el commit del tag `v1.7` y el HEAD de esta sesión.*

Los dos SHA de atribución, idénticos en los seis artefactos:

- `audited_commit_sha`: `37a83fe693a303a551f4374f48fe6fc5521804f7` — el **commit**, resuelto con
  `git rev-parse v1.7^{commit}`, no el objeto-tag (`v1.7` es un tag anotado; `git rev-parse v1.7` a
  secas devuelve el objeto-tag y haría el criterio 1 no re-verificable por terceros).
- `audit_baseline_head`: `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5` — capturado una sola vez en el
  contrato y copiado literal por los seis planes, porque el HEAD se mueve con cada commit de la fase.

El criterio 1 nombra el momento exacto que esta corrida cierra: *"ningún archivo fuente de v1.8 cambió
antes de que el último de los cinco quedara escrito"*. Los cinco ya están escritos y commiteados; esta
corrida cierra la ventana.

---

## Veredicto cross-fase

**Las cinco fases de v1.7 quedan PARTIAL, ninguna quedó limpia, y el conteo cierra.** 62 filas
enumeradas, 62 dispuestas exactamente una vez: **54 `VERIFIED-NOW`**, **4 `VERIFIED-HISTORICALLY`**,
**4 `NOT-VERIFIABLE-RETROACTIVELY`**. Cero `nyquist_compliant` movidos a `true`. Cero locks nuevos, y
los 40 preexistentes sin enrolar declarados inertes con su enrolamiento ruteado a la **Phase 45**. El
alcance quedó en las cinco fases nombradas. El árbol de fuente de v1.7 no cambió ni un byte.

Lo que **no** queda cerrado, dicho acá para que no haya que re-descubrirlo: 8 filas sin cobertura
re-derivable, 13 filas sin enforcement en CI, y 40 locks que no corren. Eso es la entrada de la
Phase 45, no el resultado de ésta.

---

*Rollup producido: 2026-08-31 · Plan `41-07` · índice secundario de
`41-AUDIT-CONTRACT.md` + los cinco `{N}-VALIDATION.md` de v1.7*
