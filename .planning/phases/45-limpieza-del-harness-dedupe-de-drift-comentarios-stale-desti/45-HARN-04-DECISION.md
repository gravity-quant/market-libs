# Phase 45 — HARN-04: destino de `verification/` de matriz, decisión escrita y fechada

**Fecha:** 2026-09-01 · **Requisito:** `HARN-04` · **Planes:** 45-04 (este documento), 45-05 (el
edit consolidado de `.github/workflows/ci.yml`, D-11)
**Fuente de decisión:** `45-CONTEXT.md` D-08 (aceptada por el operador, *"Yes, proceed"*) y su
**D-08 ENMENDADA** del checkpoint post-research del 2026-09-01, que resuelve Q3 y convierte el rol
de canario en una transferencia REAL (con enrolamiento) en vez de un renombre del abandono.

Este archivo es la evidencia del **criterio 3** de la fase — *"decisión escrita y fechada"*, literal
en `ROADMAP.md`. Todo lo que afirma está **medido en la corrida del plan 45-04** y la medición está
pegada con su comando y su salida; nada se hereda de un reporte. Donde una cifra difiere de la
heredada, se dice explícitamente cuál corrige a cuál.

**Alcance de seguridad:** este documento cita únicamente nombres de test, fids, rutas del repo y
conteos. Cero credenciales, cero base URLs de vendor, cero payloads (T-45-18).

---

## 0. Mediciones de esta corrida

**M1 — el estado rojo pre-existente de los 2 archivos en cuestión.**

```
$ uv run pytest -q verification/test_matriz_sweep_snapshot.py \
                   verification/test_main_matriz_login_fail_uniformity.py
19 failed, 3 passed, 19 errors in 0.13s
```

Reproduce exactamente lo que predijo `PITFALLS.md` Pitfall 12 y midió `45-RESEARCH.md` Hallazgo 7.
Causa raíz **única** para las 38 filas rojas: los dos archivos llaman a los probes de
`main_matriz.py` **sin el argumento `client`** — la firma pre-migración `REFAC-05` de la Phase 15.

**M2 — el transferee del canario `probe_context`.**

```
$ uv run pytest -q verification/test_probe_context_coverage.py
6 passed in 0.09s
```

Precondición verificada antes de enrolarlo: pasa solo, 6/6. Confirma el 6/6 que midió research y
que `45-PATTERNS.md` reconfirmó.

**M3 — el censo de `verification/`, medido HOY (antes de que el plan 45-05 lo mueva).**

```
$ ls verification/test_*.py | wc -l
      53
$ # conteo del allowlist explícito del job `lint` de .github/workflows/ci.yml (líneas 80-93)
13
```

| Medida | `41-ROLLUP.md` (heredado) | **HEAD, 2026-09-01** |
|---|---|---|
| Archivos `verification/test_*.py` en disco | 52 | **53** |
| Enrolados en el allowlist del job `lint` | 12 | **13** |
| **Inertes** (en disco, no enrolados) | 40 | **40** |

**Este censo 53 / 13 / 40 corrige el 52 / 12 / 40** que `45-CONTEXT.md` D-10 y `41-ROLLUP.md`
arrastraban. El delta viene de la Phase 42-01 (`7cc103a`), que agregó
`verification/test_literal_census_venue_gate.py` **y** su línea de allowlist en el mismo cambio. El
número que importa —**40 inertes**— no se movió.

---

## 1. Decisión

Se **aceptan como deuda formalmente documentada, y NO se reparan**, los dos archivos:

- `verification/test_matriz_sweep_snapshot.py` (17 FAILED + 17 ERROR)
- `verification/test_main_matriz_login_fail_uniformity.py` (2 FAILED + 2 ERROR)

**Aceptar la deuda NO implica borrar.** No hay `git rm` en esta fase. Los 2 archivos quedan en
disco, cada uno con un puntero en su docstring de módulo a este documento y a su fecha. Esa es
precisamente la razón por la que los **3 tests que hoy pasan dentro de ellos no se pierden**: siguen
existiendo, siguen corriendo en local, y su cobertura —tal como se audita en la sección 2, ítem
(3)— es de todos modos cero cobertura de producción no cubierta por otro lado.

Los 2 archivos **tampoco se enrolan** en el allowlist de CI. D-10 condicionaba su enrolamiento a que
D-08 se revirtiera a *"reparar"*, y D-08 no se revirtió.

---

## 2. Los TRES ítems que D-08 exige, respondidos POR ARCHIVO

### `verification/test_matriz_sweep_snapshot.py`

**(1) ¿Asevera algo que ningún test enrolado en CI asevera?** — **No.** Es el caso más fuerte
posible: el archivo declara su propia supersession **in-code**. El docstring del test verde
`test_matriz_risk_probes_unwrap_their_envelope_key` (líneas 310-313) dice, verbatim:

> *"No se debilita nada al invertirlo: la aserción sigue siendo igual de estricta, sólo que ahora
> exige la forma correcta. El lock estructural completo (incluido que `_envelope_probe` ya no
> ACEPTA `None`) vive en `verification/test_main_matriz_risk_envelope_keys.py`, **que además corre
> en CI**."*

Ese archivo superseder, `verification/test_main_matriz_risk_envelope_keys.py`, **está enrolado** en
el allowlist explícito del job `lint` de `.github/workflows/ci.yml` (línea 83) — verificado en esta
corrida. La supersession no es una inferencia de este documento: es una afirmación escrita dentro
del propio archivo que se acepta como deuda, corroborada contra el allowlist real.

**(2) Rol de canario de `probe_context`** — **TRANSFERIDO** (ver sección 2.3 abajo, común a los dos
archivos).

**(3) Los 3 tests que hoy pasan** — los **tres** están en este archivo. Nombrados uno por uno, con
destino:

| Test verde | Qué asevera | Destino |
|---|---|---|
| `test_matriz_sweep_snapshot_count_matches_18_minus_cfi_sanity` | `len(_PROBE_FIXTURES) == 17` — la consistencia interna de una **tabla de fixtures que vive dentro del propio archivo** | Auto-referencial: si el archivo se retirara, la aserción se quedaría sin sujeto. Su pérdida costaría **cero cobertura de producción**. Y no se pierde: el archivo queda en disco |
| `test_matriz_envelope_probe_helper_exists` | `callable(main_matriz._envelope_probe)` — que el helper existe | **Subsumido** por la capa 1 de `test_main_matriz_risk_envelope_keys.py` (enrolado): *"`_envelope_probe` ya no ACEPTA `envelope_key=None` (el parámetro es `str` requerido)"*. Un parámetro requerido implica que el helper existe — la capa enrolada es **estrictamente más fuerte** |
| `test_matriz_risk_probes_unwrap_their_envelope_key` | por grep del source: las 2 risk probes citan `envelope_key="detailedPosition"` / `="accountData"` | **Subsumido** por la capa 3 del mismo test enrolado (*"las dos risk probes citan exactamente las keys que `_core` desenvuelve"*), y el propio test lo declara en su docstring (cita verbatim arriba) |

### `verification/test_main_matriz_login_fail_uniformity.py`

**(1) ¿Asevera algo que ningún test enrolado en CI asevera?** — **Sí, exactamente una cosa**, y este
documento se niega a redondearla a la *"respuesta esperada"* de D-08 (*"nada adicional medido"*),
que para este archivo **no se sostiene** (`45-RESEARCH.md` Hallazgo 9):

> `probe_login_sync` devuelve `FINDING`, **no** `FAIL` — la uniformidad de taxonomía que fijó CR-02
> de la Phase 11.

Dos precisiones que hacen la disposición aceptable de todos modos:

- **La conducta está PRESENTE y verificada en HEAD.** `main_matriz.py:807` devuelve
  `ProbeResult("login_sync", "FINDING", ...)` dentro del handler de `AuthenticationError`, con el
  comentario `# Phase 11 CR-02` inmediatamente encima. Lo que se acepta como deuda es la **ausencia
  de un guardián de regresión**, no un defecto abierto.
- **Esa fila de deuda quedó CERRADA por la Task 1 del plan 45-04** — cierre de Q4 por
  implementación, no por descarte. El test que la cierra es
  `test_login_sync_probe_returns_finding_never_fail`, y vive en
  **`verification/test_main_matriz_skip_line_shape.py`**, un archivo que **YA estaba enrolado** en
  el allowlist del job `lint` (`ci.yml:86`). No se enroló ningún archivo nuevo y no se reparó nada
  para conseguirlo.

  El lock es por **AST**, no por substring del fuente: asevera (i) que hay exactamente 3 call sites
  de `ProbeResult("login_sync", ...)` —piso de no-vacuidad y techo de triage—, (ii) que el conjunto
  de sus statuses es exactamente `{FINDING, PASS}`, y (iii) que el `except AuthenticationError` de
  `probe_login_sync` devuelve status `FINDING`. Un `assert "<literal>" not in source` habría sido
  auto-invalidante: el docstring del propio test cita el literal prohibido.

**(2) Rol de canario de `probe_context`** — **TRANSFERIDO** (ver 2.3).

**(3) Los 3 tests que hoy pasan** — este archivo tiene **CERO** tests verdes (2 FAILED + 2 ERROR).
Los 3 verdes están todos en `test_matriz_sweep_snapshot.py`, contabilizados arriba.

### 2.3 — El rol de canario de `probe_context`: TRANSFERIDO, con enrolamiento nombrado

El rol de canario existe porque estos 2 archivos **invocan los probes directamente**, no vía
`main()`, y por eso son los únicos que ejercitan en runtime el seam `probe_context`
(`HARN-VERIF-01`, planes 33-02/33-03).

**Disposición: TRANSFERIDO a `verification/test_probe_context_coverage.py`.**

Y —esto es lo que D-08 ENMENDADA agrega y lo que este documento está obligado a nombrar— la
transferencia se sostiene en un **enrolamiento concreto**: `verification/test_probe_context_coverage.py`
**se agrega al allowlist explícito del job `lint` de `.github/workflows/ci.yml` en esta misma fase**,
dentro del **edit consolidado del plan 45-05** (D-11: todos los edits de `ci.yml` de la fase llegan
en un solo cambio). Precondición ya verificada en esta corrida: **`6 passed`** (M2 arriba).

Por qué el enrolamiento es la parte load-bearing y no un detalle: `45-RESEARCH.md` Hallazgo 10 midió
que ninguno de los 13 archivos enrolados hoy referencia `probe_context`
(`test_main_matriz_deep_chain.py` y `test_main_matriz_risk_envelope_keys.py` son enteramente
AST/`inspect` y **no invocan ningún probe en runtime**), y que el transferee natural era él mismo
inerte — su propio docstring cierra con *"**Alcance:** `verification/` no corre en CI (ver
`33-BASELINE.md`); esto es un gate local de fase."* El hallazgo lo dice literalmente: **transferir el
rol a un archivo que también es inerte no es una transferencia, es renombrar el abandono.** D-08
ENMENDADA lo resuelve con enrolamiento real, y este documento lo declara nombrando archivo + plan +
job, no sólo el archivo.

Cuando 45-05 aterrice, el censo de M3 pasa de 13 a 18 enrolados y de 40 a 35 inertes.

---

## 3. Alcance NO reparado, y su razón

Reparar los 2 archivos significaría **re-derivar expectativas mockeadas para conducta que ya fue
verificada EN VIVO contra el vendor real** a lo largo de 4 milestones (Phases 33 / 35 / 37 / 39).
Eso es evidencia más débil reemplazando evidencia más fuerte, a escala de 4 milestones de alcance —
y precisamente el modo de falla que este proyecto existe para eliminar.

La rama *"reparar"* queda **diferida**, no descartada para siempre. Si algún día se toma:

- necesita **presupuesto declarado por adelantado** y su propia sub-fase, con el mismo cuidado de
  mirror sync/async que cualquier fix de harness — nunca una re-escritura apurada de mocks;
- la estimación heredada de **"38 firmas de argumento"** (`45-CONTEXT.md` D-08) **NO fue re-medida
  en esta fase** y **debe re-medirse antes de planificarla**. Escribirla acá como si fuera un dato
  de esta corrida sería exactamente la clase de cifra stale que esta fase existe para cerrar.

---

## 4. Q5 — el gap de gate de mypy sobre los drivers de la raíz

**Declarado por escrito, con la medición pegada, y NO cerrado en esta fase.**

`45-CONTEXT.md` Q5 (resuelto con la recomendación del research): apuntar mypy a los drivers de la
raíz dentro de esta fase es scope creep de tamaño no medido; se declara con destino nombrado.

**La medición.** mypy apuntado **a mano** a un driver de la raíz sí lo analiza:

```
$ uv run mypy main_matriz.py
Success: no issues found in 1 source file
```

Fue exactamente así como se detectó `DRV-MD-SEG-43` (`45-RESEARCH.md` Hallazgo 12:
`main_market_data.py:1541-1542` dereferenciaba `Segment.marketSegmentId`, campo que la Phase 43
removió). Ese defecto ya está **corregido** en HEAD por el plan 45-01 (`4039551`), y por eso
`uv run mypy main_market_data.py` hoy también sale limpio — pero el defecto vivió sin detectarse
porque **ningún gate de CI apunta ahí**, y el gate sigue sin apuntar. Las tres piezas de la
medición:

```
$ # pyproject.toml:97 — el `files` de mypy del root
files = ["packages/higyrus-client/src", "packages/wallets-client/src",
         "packages/matriz-client/src", "packages/iol-client/src",
         "packages/ambito-financiero-client/src", "packages/market-data-client/src"]

$ # .pre-commit-config.yaml, hook mypy
files: ^packages/.*/src/

$ # .github/workflows/ci.yml:123-124 — el job `typecheck` invoca mypy sin argumentos
- name: mypy (src global)
  run: uv run mypy

$ uv run mypy          # config-driven, tal como lo corre CI
Success: no issues found in 75 source files
```

Los seis paths del `files` son todos `packages/*/src`; el hook de pre-commit está scoped al mismo
prefijo; y el job `typecheck` de CI invoca `uv run mypy` sin argumentos, así que hereda ese `files`.
Los 75 source files que analiza **no incluyen ninguno de los `main_*.py` de la raíz**. Además, el
lock de deep-chain de market-data (`verification/test_main_market_data_deep_chain.py:147`) **parsea
el driver por AST sin importarlo**, así que tampoco lo ejercita bajo un type checker.

**Conclusión: ningún gate de CI mira los 5 drivers `main_*.py` de la raíz** (13.370 líneas entre los
cinco).

**Esta fase arregla el sitio y NO cierra el gate.** Apuntar mypy a 5 archivos de miles de líneas
dentro de una fase de limpieza es scope creep de tamaño no medido: no hay medición de cuántos
errores nuevos levantaría, y una fase que se propone dejar de mentir sobre su alcance no puede
abrirse un frente cuyo tamaño no midió. **Destino nombrado: entrada de backlog v1.9**, que el plan
45-05 agrega al `ROADMAP.md`.

---

## 5. Censo de `verification/` y re-declaración de D-10

El censo medido hoy es **53 en disco / 13 enrolados / 40 inertes** (M3), y **corrige el 52 / 12 / 40**
heredado de `41-ROLLUP.md` y repetido en `45-CONTEXT.md` D-10.

**Se enrolan en el allowlist de CI, en esta fase, ÚNICAMENTE los archivos que HARN-01 / HARN-03 /
HARN-04 tocan directamente** (todos vía el edit consolidado del plan 45-05, D-11):

| Archivo | Por qué |
|---|---|
| `verification/test_public_surface.py` | D-06 — cierra `IN-06` (HARN-03) |
| `verification/test_finding_count_consistency.py` | Para que el criterio 2 de HARN-01 (*"el invariante de fids sigue verde"*) signifique algo en CI y no sólo en local |
| `verification/test_findings_dedupe_by_title.py` | Primitiva existente que HARN-01 consume; hoy inerte pese a estar ya escrita |
| `verification/test_drift_dedupe_falsification.py` | El test de falsificación nuevo de D-04 |
| `verification/test_probe_context_coverage.py` | D-08 ENMENDADA / D-10 ENMENDADA — el transferee del canario (sección 2.3) |

**Los ~35 archivos `verification/test_*.py` restantes SIGUEN INERTES y quedan formalmente FUERA DE
ALCANCE de v1.8.** La razón, declarada y no silenciada: `PITFALLS.md` advierte explícitamente contra
*"enrolar `verification/` en bloque"* — convertiría una limpieza acotada en un yak-shave de alcance
no medido, con el precedente ya escrito para mypy (*"Enrolamiento mypy completo de `verification/`
… no forma parte de HARN-04"*, `REQUIREMENTS.md § Out of Scope`). La **"declaración inerte"** que la
Phase 41 dejó pendiente de ruteo queda **satisfecha por esta re-declaración explícita**, no por
enrolamiento total.

Y, repetido acá porque es la consecuencia directa de la decisión de la sección 1:
`verification/test_matriz_sweep_snapshot.py` y
`verification/test_main_matriz_login_fail_uniformity.py` **NO se enrolan**. D-10 lo condicionaba a
que D-08 se revirtiera a *"reparar"*; no se revirtió.

Si algún día se quiere cobertura de CI sobre todo el directorio, es candidato a un milestone propio
con presupuesto medido, no un efecto colateral de esta decisión.

---

## 6. Dos límites de alcance que esta fase declara en vez de silenciar

**6.1 — `test_public_surface.py` enrolado es una red PARCIAL.** Enrolarlo cierra `IN-06`
literalmente, pero sus snapshots cubren **4 de los 6 paquetes**: **no** incluyen
`market-data-client` ni `wallets-client` (`45-RESEARCH.md` Hallazgo 6). Un lector futuro **no debe
leer** *"public surface enrolado en CI"* como cobertura total de superficie pública. Cerrar esa
brecha —extender los snapshots a los 2 paquetes faltantes— no forma parte de v1.8.

**6.2 — Las 4 ramas hermanas `missing assumed key …` de `main_iol.py`.** Comparten **exactamente el
mismo hazard** de título key-scoped que los 7 sitios que D-02 sí manda corregir en HARN-01, y D-02
las dejó fuera **a propósito**. Se declaran acá como el mismo hazard, **fuera de alcance de esta
fase**, para que su ausencia del diff de HARN-01 no se lea como que no existen o como que ya
estaban cubiertas.

---

## Trazabilidad

| Ítem de decisión | Dónde se cumple |
|---|---|
| Criterio 3 del ROADMAP: *"decisión escrita y fechada"* | Header de este documento (2026-09-01) |
| D-08 ítem (1), por archivo | § 2, una subsección por archivo |
| D-08 ítem (2), canario, con enrolamiento nombrado | § 2.3 (archivo + plan 45-05 + job `lint` de `ci.yml`) |
| D-08 ítem (3), los 3 verdes uno por uno | § 2, tabla de `test_matriz_sweep_snapshot.py` |
| Q4 (fila de deuda de login) | § 2, segundo archivo — **cerrado por implementación** en `verification/test_main_matriz_skip_line_shape.py` (plan 45-04, Task 1) |
| Q5 (gap de mypy sobre drivers de la raíz) | § 4 — declarado, medido, destino v1.9 vía plan 45-05 |
| D-10 re-declaración de los inertes | § 5, con el censo 53 / 13 / 40 de esta corrida |
| Límites de alcance no silenciados | § 6.1 y § 6.2 |
| Censo POST-fase, medido tras el edit consolidado | § 7 (agregado por el plan 45-05, 2026-09-01) |

---

## 7. Censo post-fase — medido después del edit consolidado de `ci.yml` (plan 45-05)

*Agregado por el plan **45-05** el **2026-09-01**, después de que el edit consolidado de D-11
(commit `d6b34f0`) aterrizara. Las cifras de abajo son **medidas en esa corrida**, no proyectadas
desde § 2.3 ni desde el handoff de 45-04.*

**Los comandos y su salida:**

```
$ ls verification/test_*.py | wc -l
      54
$ grep -c 'verification/test_.*\.py' .github/workflows/ci.yml
18
$ git log --oneline 6b9b3b6..HEAD -- .github/workflows/ci.yml | wc -l
1
```

**La aritmética, antes → después:**

| Medida | § 0 / M3 (plan 45-04) | Al ARRANCAR el plan 45-05 | **Después del edit (HEAD)** |
|---|---|---|---|
| Archivos `verification/test_*.py` en disco | 53 | **54** | **54** |
| Enrolados en el allowlist del job `lint` | 13 | 13 | **18** |
| **Inertes** (en disco, no enrolados) | 40 | **41** | **36** |

**El delta de disco 53 → 54 se explica, no se redondea.** El archivo nuevo es
`verification/test_drift_dedupe_falsification.py`, creado por el plan **45-02** (`bda2bec`, la puerta
RED del TDD de HARN-01) y extendido a 6 arms por el plan **45-03** (`a573a91`). Nació **después** de
la medición M3 de § 0, que corrió en el plan 45-04 — de ahí que la proyección *"53 / 13 / 40 → 53 /
18 / 35"* del final de § 2.3 quede **corregida por esta sección a 54 / 13 / 41 → 54 / 18 / 36**. El
enrolamiento sí fue de **+5 exactos**, como estaba declarado; lo que se movió es la base de disco,
porque la propia fase agregó un archivo. Esta corrección es del mismo tipo que la que § 0 le hizo al
`52 / 12 / 40` de `41-ROLLUP.md`: se escribe lo medido y se nombra la causa del delta.

**Los 5 enrolados son exactamente los 5 de la tabla de § 5** (verificado por grep sobre el YAML, 5/5
presentes). No se enroló ningún otro archivo, no se creó ningún job nuevo (`grep -c '^  [a-z-]*:$'`
→ **5**, idéntico a la línea base) y el comentario que explica por qué la lista es **EXPLÍCITA**
(`ci.yml:76-78`) quedó intacto (`grep -c 'Es una lista EXPLÍCITA'` → 1).

### Re-declaración de los inertes (D-10), con la cifra post-fase

**Los 36 archivos `verification/test_*.py` que quedan en disco y NO corren en CI siguen INERTES y
formalmente FUERA DE ALCANCE de v1.8.** Esto se re-declara acá por escrito, con la cifra medida
después del edit, precisamente para que no se lea como un silencio:

- **Por qué no se enrolan en bloque:** `PITFALLS.md` advierte explícitamente contra *"enrolar
  `verification/` en bloque"*. Ese directorio arrastra rojo pre-existente —los **19 failed / 19
  errors** de M1, de los 2 archivos que la § 1 acepta como deuda— así que un `pytest verification/`
  pondría rojo el job `lint` **del repo entero** el mismo día que se escribiera. Convertiría una
  limpieza acotada en un yak-shave de alcance no medido, con el precedente ya escrito para mypy
  (*"Enrolamiento mypy completo de `verification/` … no forma parte de HARN-04"*,
  `REQUIREMENTS.md § Out of Scope`).
- **Qué se enroló entonces:** únicamente los archivos que **HARN-01 / HARN-03 / HARN-04 tocan
  directamente** en esta fase (tabla de § 5). Ni uno más.
- **Los 2 archivos de la § 1 siguen sin enrolarse**, coherente con que D-08 no se revirtió a
  *"reparar"*.
- **La "declaración inerte" que la Phase 41 dejó ruteada a esta fase** (`41-ROLLUP.md:160-276`) queda
  **satisfecha por esta re-declaración explícita y medida**, no por enrolamiento total. Un lock que
  no corre sigue sin contarse como cobertura — y ahora los que no corren están contados: son 36.
- **Si algún día se quiere cobertura de CI sobre todo el directorio**, es candidato a un milestone
  propio con presupuesto medido, no un efecto colateral de esta decisión.

### El canario de `probe_context`: la transferencia de § 2.3 dejó de ser una promesa

`verification/test_probe_context_coverage.py` **corre en CI desde `d6b34f0`** (línea nueva del
allowlist del job `lint`). Precondición re-verificada en la corrida del plan 45-05, no heredada de
M2:

```
$ uv run pytest -q verification/test_probe_context_coverage.py
6 passed in 0.11s
```

Ésa es la diferencia, nombrada por D-08 ENMENDADA, entre **transferir el rol de canario** y
**renombrar el abandono** (`45-RESEARCH.md` Hallazgo 10).
