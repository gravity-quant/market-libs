---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
plan: 02
subsystem: testing
tags: [edge-cases, null-object, deep-chain, pytest-httpx, sync-async-parity, ci]

# Dependency graph
requires:
  - phase: 38-...
    provides: "Cotizacion.puntas → list[Punta] y Titulo.puntas → Punta Null Object (NOBJ-IOL-01)"
  - phase: 37-...
    provides: "los 6 alias de MarketDataSnapshot (bids/offers/last/settlement/close/open_interest, NOBJ-MTZ-02)"
  - phase: 35-...
    provides: "la política NOBJ-02 del walker: null/ausente sobre un eslabón no-opcional colapsa a vacío sin divergencia"
provides:
  - "Red mockeada que hace SC-2 falsificable con independencia del estado del mercado, del DNS de higyrus y del sandbox bbsa"
  - "Las 4 cadenas profundas de la fase (iol ×2, higyrus ×1, matriz ×6 alias) pinneadas contra los 4 casos límite de D-12 en sync y async"
  - "Única cobertura en el repo de la rama POBLADA de Posicion.parking (el driver pide incluirParking en falso)"
  - "Medición explícita de la asimetría de tolerancia a 204: higyrus sí, iol y matriz no"
affects: [39-03, 39-04, 39-05, 39-06, 39-07, 39-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Aserción con dientes por contextmanager: _no_chain_break() falla el test ante AttributeError/TypeError y deja pasar el resto, siempre acompañada de una aserción de VALOR"
    - "Resumen de cadena (_summarize) que desreferencia LOS SEIS alias en todos los casos y se compara contra un dict esperado completo — no una muestra ni un smoke test"
    - "Fila degenerada = baseline committeado verbatim; fila aisladora = baseline + hojas escalares pobladas, con el hecho DECLARADO en el comentario (CR-02)"
    - "Control poblado obligatorio por cadena (T-39-08) como antídoto al verde por colapso incondicional"

key-files:
  created:
    - packages/iol-client/tests/test_deep_chain_edges.py
    - packages/higyrus-client/tests/test_deep_chain_edges.py
    - packages/matriz-client/tests/test_deep_chain_edges.py
    - .planning/phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/deferred-items.md
  modified: []

key-decisions:
  - "Las tres suites viven bajo packages/<pkg>/tests/ y no bajo verification/: es el único árbol que el job test de CI corre de verdad, así que entran a CI en 3.12 y 3.13 sin tocar ci.yml"
  - "iol y matriz NO toleran 204/cuerpo vacío (json.JSONDecodeError escapa la jerarquía tipada); higyrus sí. La asimetría se assertea por tipo exacto y se difiere como D39-01/D39-02 en vez de arreglarse: es cambio de superficie, fuera del alcance de un plan que sólo crea tests"
  - "Titulo.puntas se cubre aparte de Cotizacion.puntas porque la cadena tiene otra FORMA: atributo directo sin guarda vs subscript detrás de una guarda de veracidad"
  - "El caso mercado-cerrado se assertea como 'el modelo NO discrimina antigüedad' — el discriminador vive en main_matriz.py, y dejarlo escrito es lo que evita que una fase futura lo busque en el modelo"

patterns-established:
  - "Un helper de aserción con dientes se copia por paquete, nunca se importa cruzado (política no-shared-code del repo)"
  - "Cuando una constante de fixture puebla algo que el baseline manda vacío, el comentario lo declara y dice por qué"

requirements-completed: [LIVE-NOBJ-01]

# Metrics
duration: 38min
completed: 2026-08-29
status: complete
---

# Phase 39 Plan 02: Casos límite mockeados del encadenamiento profundo Summary

**Tres suites nuevas —una por paquete— que pinnean las cuatro cadenas profundas de la fase (`Cotizacion.puntas`, `Titulo.puntas`, `Posicion.parking` y los seis alias de `MarketDataSnapshot`) contra los cuatro casos límite de D-12 en `client.py` **y** `aio.py`, con control poblado por cadena para que un verde no pueda venir de un colapso incondicional.**

## Performance

- **Duration:** ~38 min
- **Tasks:** 3 (las tres de código, sin checkpoint)
- **Files created:** 4 (3 suites + `deferred-items.md`)
- **Files modified:** 0 archivos de código fuente — el plan declaró `files_modified` con sólo los tres tests y se respetó al pie

## Accomplishments

- **50 tests nuevos** (18 iol + 14 higyrus + 18 matriz), verdes en Python **3.12 y 3.13**, corriendo dentro del job `test` de CI sin tocar `.github/workflows/ci.yml` — el job ya hace `pytest packages/<pkg>` para los seis paquetes de la matriz.
- La propiedad SC-2 queda **falsificable con independencia de la corrida en vivo**: no depende de que el mercado esté abierto, de que el DNS de higyrus resuelva ni de que el sandbox bbsa responda. Esa era la razón de existir del plan y se cumple.
- La rama **poblada** de `Posicion.parking` queda cubierta por primera y única vez en el repo: el driver pide `incluirParking` en falso en sus dos sitios de llamada (`main_higyrus.py:1796` y `:1909`), así que ninguna corrida en vivo —ni siquiera una exitosa— podría producirla.
- Los **seis** alias de matriz se desreferencian en **todos** los casos, no en una muestra, y el control assertea identidad por `is` contra el campo wire: un alias que copiara o cacheara pasaría un `==` y se pone rojo.
- La asimetría de tolerancia a 204 entre los tres paquetes queda **medida y asertada**, no asumida.

## Task Commits

1. **Task 1: iol — matriz de casos límite de `.puntas` en ambas superficies** — `267732d` (test)
2. **Task 2: higyrus — matriz de casos límite de `Posicion.parking` en ambas superficies** — `ff1e732` (test)
3. **Task 3: matriz — matriz de casos límite de los 6 alias de `MarketDataSnapshot`** — `64ce8dd` (test)

_Las tres tareas son test-only (`files_modified` no incluye ningún archivo fuente), así que el gate MVP+TDD de tarea behavior-adding no aplica: no hay `<behavior>` sobre archivos de código a los que anteponer un RED. El RED equivalente es estructural — las suites fallarían hoy si Phase 35/37/38 no hubieran aterrizado la política Null Object, y el control poblado de cada suite es lo que impide que pasen por colapso._

## Files Created

- **`packages/iol-client/tests/test_deep_chain_edges.py`** (18 tests) — cubre las **dos** formas de `.puntas`, que son distintas y por eso van separadas:
  - `Cotizacion.puntas` (`list[Punta]`): lista vacía / clave ausente / `null` explícito ⇒ `[]`, `bool(...) is False`, subscript sólo detrás de la guarda de veracidad, iteración sin `TypeError`.
  - `Titulo.puntas` (`Punta` singular, Null Object): clave ausente / `null` ⇒ `titulo.puntas.precioCompra` se evalúa **sin guarda** y devuelve `0.0`, con `bool(...) is False`.
  - Controles poblados para ambas cadenas; `204` asertado por tipo exacto; envelope `titulos` ausente ⇒ cero filas sin `TypeError` al iterar.
- **`packages/higyrus-client/tests/test_deep_chain_edges.py`** (14 tests) — `Posicion.parking` por **construcción directa** (`Posicion.from_api`, nunca `Posicion(field=value)`) y por la **ruta tipada completa del cliente**, en sync y async. El docstring del módulo deja escrito que higyrus no tiene mitad en vivo en esta fase (`LIVE-HIGY-33`, vendor sin resolución DNS) y que por eso esta suite es la evidencia, no un complemento. El `204` se corresponde con la rama `status_code == 204 or not resp.content → None` que `main_higyrus._raw_request_sync` replica.
- **`packages/matriz-client/tests/test_deep_chain_edges.py`** (18 tests) — cinco casos (`listas vacías`, `claves ausentes`, `null explícito`, `204`, `mercado cerrado`) × dos superficies, cada uno comparando un **resumen completo de los seis alias** contra un dict esperado. Más: identidad por `is` en el control, `LA.date` viejo devuelto tal cual, y `{"marketData": null}` sigue siendo `PrimaryAPIError` tipado (WR-05).
- **`.planning/phases/.../deferred-items.md`** — D39-01 y D39-02 (la ausencia de tolerancia a 204 en iol y matriz).

## Decisions Made

- **Las tres suites bajo `packages/`, no bajo `verification/`.** El job `test` de CI corre `pytest packages/<pkg>` para los seis paquetes en 3.12 y 3.13; `verification/` sólo corre por allowlist explícita en el job `lint`. Ubicarlas bajo `packages/` es lo que hace que entren a CI sin editar `ci.yml` — y por lo tanto lo que permitió que este plan paralelizara con `39-01`, que sí lo edita.
- **`Titulo.puntas` merece su propio bloque de tests.** El plan lo pedía y la razón se confirmó al leer el modelo: la cadena singular se desreferencia **siempre**, sin subscript ni guarda que corte. Un test que sólo cubriera `Cotizacion.puntas` dejaría sin cubrir exactamente el caso donde no hay guarda que salve.
- **El caso 204 se assertea por tipo exacto (`type(exc.value) is json.JSONDecodeError`), no por `pytest.raises` genérico.** Un `pytest.raises(Exception)` habría pasado con cualquier cosa, incluido un `AttributeError` — que es precisamente lo que D-12 prohíbe. El tipo exacto es lo que convierte el test en un lock del comportamiento actual: el día que iol o matriz ganen tolerancia a 204, estos cuatro tests son los primeros en ponerse rojos.
- **La fila aisladora de matriz declara que puebla las cuatro hojas escalares.** `OP`/`HI`/`LO`/`TV` se pueblan a propósito para que los únicos candidatos a levantar sean los seis eslabones-objeto — misma técnica que `_LINKS_ONLY_NO_DATA_ROW` del análogo de market-data. Se dice en el comentario en vez de esconderse, que es la lección literal de CR-02.
- **`_no_chain_break` es copia local en cada paquete.** El repo no tiene paquete compartido por diseño; importar el helper desde otro paquete introduciría el acoplamiento cruzado que la política prohíbe. Cada copia lo declara en su docstring.
- **El caso "mercado cerrado" assertea una NO-propiedad del modelo.** Lo que se pinnea es que `MarketDataSnapshot` **no** discrimina antigüedad: devuelve el `LA.date` viejo tal cual. El discriminador vive en `main_matriz.py`. Dejarlo escrito es lo que evita que una fase futura lo busque en el modelo y concluya que falta.

## Deviations from Plan

Ninguna que requiriera aplicar las Reglas 1-4. El plan se ejecutó como está escrito.

Dos ajustes menores dentro de lo que el plan ya contemplaba:

1. **El caso 204 de iol y de matriz resultó ser `json.JSONDecodeError`, no un error tipado del paquete.** El plan lo anticipó con un condicional ("si el cliente levanta un error tipado propio, assertear ese error tipado explícitamente"). La rama que se cumplió fue la otra, y se resolvió como el plan pide en espíritu: assertear el tipo **exacto** medido y verificar explícitamente que no es `AttributeError` ni `TypeError`. Registrado como D39-01/D39-02 en `deferred-items.md`, **no arreglado**: darle tolerancia a 204 a iol o a matriz es un cambio de comportamiento de un paquete publicado y el plan declaró `files_modified` con sólo los tres tests. La deuda además ya estaba escrita en el docstring de `iol_client._core._parse_list_or_raise`; lo nuevo es la medición y el lock.
2. **`RUF003` sobre el signo `×` en un comentario.** Ruff rechaza el carácter de multiplicación por ambigüedad; se reescribió el comentario. Sin efecto sobre el contenido.

**Total deviations:** 0 auto-fixes de las Reglas 1-4. Cero dependencias nuevas (T-39-SC): `pytest-httpx` y `pytest-asyncio` ya estaban pinneados en `uv.lock`, que no se tocó.

## Issues Encountered

- **`uv run --python 3.13` recreó el `.venv` del workspace.** Para verificar el criterio de la sección `<verification>` ("las tres pasan en 3.12 y 3.13") corrí `uv run --frozen --python 3.13 pytest`, y `uv` reemplazó `.venv` por un entorno 3.13 sin los paquetes del workspace (`ModuleNotFoundError: iol_client`). Se detectó en la misma corrida y se restauró con `uv sync --all-packages --all-extras --dev --frozen --python 3.12`; la verificación 3.13 se rehizo en un entorno aislado vía `UV_PROJECT_ENVIRONMENT` apuntando a un directorio de scratch. `.venv` está gitignorado y ningún archivo versionado se vio afectado (`git status` limpio salvo el `deferred-items.md` sin trackear). Nota para planes futuros de esta fase: **usar `UV_PROJECT_ENVIRONMENT` para cualquier corrida cross-version**, nunca `--python` a secas sobre el `.venv` del repo.

## Verificación

| Criterio | Comando | Resultado |
|---|---|---|
| Suite iol nueva ≥ 8 tests | `pytest -q packages/iol-client/tests/test_deep_chain_edges.py` | **18 passed** |
| Suite higyrus nueva ≥ 8 tests | `pytest -q packages/higyrus-client/tests/test_deep_chain_edges.py` | **14 passed** |
| Suite matriz nueva ≥ 10 tests | `pytest -q packages/matriz-client/tests/test_deep_chain_edges.py` | **18 passed** |
| Paquete iol completo | `pytest -q packages/iol-client` | 311 passed |
| Paquete higyrus completo | `pytest -q packages/higyrus-client` | 303 passed |
| Paquete matriz completo | `pytest -q packages/matriz-client` | 596 passed |
| Success criteria del plan | `pytest -q packages/iol-client packages/higyrus-client packages/matriz-client` | **1210 passed** |
| Lint + formato + tipos | `ruff check . && ruff format --check . && mypy` | 0 / 272 formateados / 75 archivos sin issues |
| `LIVE-HIGY-33` presente en la suite de higyrus | `grep -c 'LIVE-HIGY-33' …` | 1 |
| Identidad por `is` en la suite de matriz | `grep -c ' is snap\.' …` | 12 |
| Python 3.13 (matriz de CI) | `UV_PROJECT_ENVIRONMENT=… uv run --python 3.13 pytest` sobre las 3 suites | **50 passed** |
| Ninguna suite importa un `main_*.py` | `grep -n "main_" …` | sólo menciones en docstrings, cero imports |
| Ninguna suite depende de red | inspección: todo pasa por `HTTPXMock` | confirmado |
| Deletions en los 3 commits de tarea | `git diff --diff-filter=D` × 3 | ninguna |
| `ci.yml` intacto | `git status` | no modificado (el job `test` ya cubre `packages/<pkg>`) |

## Known Stubs

Ninguno.

## Threat Flags

Ninguno. El plan declaró tres amenazas y las tres quedan dispuestas como estaba previsto:

- **T-39-07 (Information Disclosure).** Todos los identificadores de las fixtures son sintetizados: `AAA1`, `CTA-0001`, `XX0000000001`, `AAA/ZZZ26`, `TITULO SINTETICO SA`, `ESPECIE SINTETICA`. Ningún valor observado de un venue real entró al repo — los baselines committeados son keys-and-types-only por construcción, así que no había valores que copiar aunque se hubiera querido.
- **T-39-08 (Repudiation).** Control poblado en las tres suites, con aserción de **valor** y no sólo de "no lanza". En matriz además se compara el resumen completo de los seis alias contra un dict esperado, así que un alias que devolviera lo de otro campo también falla.
- **T-39-SC (Tampering).** Cero dependencias instaladas; `uv.lock` sin tocar.

No se introdujo endpoint, path de auth, acceso a archivos ni cambio de esquema en ningún borde de confianza: las tres suites son archivos de test que no salen a la red.

## Next Phase Readiness

- **SC-2 tiene su mitad mockeada completa.** Las corridas en vivo de los planes siguientes pueden reportar `SKIPPED` por mercado cerrado, por DNS o por política sin que la propiedad de D-12 quede sin evidencia.
- **Predicho para 39-07 / 39-08:** la asimetría de tolerancia a 204 (D39-01/D39-02 en `deferred-items.md`). Si la corrida en vivo de iol o matriz topa con un 204, el `json.JSONDecodeError` resultante **no** es un descubrimiento nuevo ni una divergencia del censo — está medido acá y su disposición ya está escrita.
- **Insumo para el censo de 39-07:** estas suites no producen registros de divergencia (los casos degenerados toman la rama de colapso NOBJ-02, que no emite). Eso es consistente con la política de la Phase 35 y es parte de lo que el censo debe declarar como "bajó por política", no "bajó por corrección".
- **Sin cambios en:** ningún archivo fuente de ningún paquete, `ci.yml`, `uv.lock`, ni los ledgers de findings.

## Self-Check: PASSED

Los 4 archivos declarados existen en disco y los 3 hashes de commit de tarea (`267732d`, `ff1e732`, `64ce8dd`) existen en el historial.

---
*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo*
*Completed: 2026-08-29*
