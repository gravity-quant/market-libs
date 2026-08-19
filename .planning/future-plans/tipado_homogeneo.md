# Plan de milestone — `v1.6 · Tipado homogéneo de la superficie pública`

> Plan futuro (no ejecutado). Redactado 2026-08-18 a partir de un relevamiento del código en
> `a1f3e22` (v1.5 archivado). Continúa la numeración de v1.5 (última fase = 28) → **empieza en
> Phase 29**. No hay milestone abierto: `.planning/PROJECT.md` sigue apuntando a v1.5.

**Objetivo:** que las seis librerías expongan un **contrato de tipos idéntico y verificable por
máquina** — cero `Any`/`dict[str, Any]` en la superficie pública de datos, una única decodificación
de política **observable**, parámetros de dominio como `Literal`, y gates de CI que sostengan la
homogeneidad sin recurrir a código compartido entre paquetes.

**Core value:** que sea **imposible cometer un typo al consumir la lib** (acceso por atributo
verificado por mypy, no por string) y que **ninguna divergencia con la API en vivo sea silenciosa**
— hoy `SafeModel.from_api()` es tolerante *y* silencioso, y un campo que desaparece se convierte en
`0.0` sin que nadie se entere, lo cual contradice de frente el Core Value del proyecto.

## Evidencia del relevamiento (medido, no estimado)

### Superficie de datos sin tipar — el desvío está concentrado

| Paquete | Versión | Funciones de datos sin tipar |
|---------|---------|------------------------------|
| `iol-client` | 0.2.0 | **4 — toda su superficie**: `get_quote` (`dict[str, Any]`), `get_historical_quotes` (`list[dict[str, Any]]`), `get_instruments` (`Any`), `get_instruments_by_type` (`list[dict[str, Any]]`) |
| `market-data-client` | 0.4.0 | **4 (ops)**: `get_health`, `get_health_feed`, `add_holidays`, `delete_holiday` → `dict[str, Any]` |
| `higyrus-client` | 0.2.0 | **1 (ops)**: `get_health` → `dict[str, Any]` |
| `matriz-client` | 0.2.0 | 0 |
| `ambito-financiero-client` | 0.2.0 | 0 |
| `wallets-client` | 0.2.0 | 0 (stub sin endpoints reales) |

`ambito` y `matriz` están limpios: sus `-> Any` son **todos dunders** (`__reduce__`,
`__deepcopy__`, `__getattr__`) y el único `-> dict[str, Any]` de matriz es
`_matriz_legacy_request`, el wrapper deprecado de back-compat para las probes de `main_matriz.py`
(Pitfall 7). `ambito.get_dollar_banco_nacion` ya devuelve `float`.

Cada función de iol multiplica por 4 (método sync + shim sync + método async + shim async) → **16
firmas** a migrar en `iol-client`, más los parsers en `_core.py`.

### Asimetría estructural

- `models.py` existe en 3 de 6 paquetes (`higyrus`, `matriz`, `market-data`) con `SafeModel` +
  `_coerce` **duplicados verbatim** (~90 LOC × 3, per la constraint de no-shared-internals).
- `types.py` (aliases `Literal`) existe **sólo** en `matriz`.
- `iol-client` es el único paquete con superficie de datos y **sin** `models.py`.

### Verificaciones empíricas que fundamentan las decisiones

Corridas el 2026-08-18 en entorno aislado (`uv run --with … --no-project`):

- **`TypedDict` NO alcanza.** mypy 1.x `--strict` reporta `q["typo"]` sobre un `TypedDict`
  (`typeddict-item`, con sugerencia "Did you mean…") y reporta el typo de atributo sobre una
  dataclass (`attr-defined`), pero **NO reporta `q.get("typo")`**. `main_iol.py` lee los resultados
  justamente con `.get(...)` → `TypedDict` daría cobertura falsa sobre el estilo de acceso real.
  **Sólo el acceso por atributo está protegido en todos los casos.**
- **`msgspec` 0.21.1 decodifica directo a dataclasses `frozen=True, slots=True`** del stdlib, sin
  heredar de `msgspec.Struct`: `msgspec.json.decode(bytes, type=Quote)`,
  `msgspec.json.decode(bytes, type=list[Quote])` y `msgspec.convert(dict, type=Quote)` (compatible
  con `resp.json()`). Errores con ruta exacta: `` Expected `float`, got `str` - at `$.ultimoPrecio` ``
  y `` Object missing required field `ultimoPrecio` ``. Campos extra desconocidos se ignoran por
  default (configurable).
- **Pydantic v2 descartado** por dos razones concretas además del peso: coerciona **lenient** por
  default (`"123.5"` → `123.5` silenciosamente — exactamente la divergencia a cazar) y agregaría
  `pydantic-core` a seis wheels cuyo perfil de deps hoy es mínimo (`httpx`, `python-dotenv`,
  `tenacity`, `platformdirs` en iol).

### Vector de typos hoy abierto en los parámetros

`iol.get_quote` declara `mercado: str = "bcba"` y `plazo: str = "t2"` → `mercado="bcaba"` pasa mypy
y falla recién contra el servidor. El patrón correcto ya existe en el mismo archivo
(`InstrumentType = Literal[...]`, `client.py:62-69`) y en `matriz/types.py`.

## Decisiones bloqueadas (D-locks)

| ID | Decisión |
|----|----------|
| DT-01 | `msgspec` es **decoder interno únicamente** — NUNCA aparece en firmas públicas. Las funciones siguen devolviendo dataclasses `frozen=True, slots=True` del stdlib, así que ningún tipo de terceros se filtra a los consumidores de los wheels. Verificado empíricamente (ver evidencia). |
| DT-02 | **Política observable** (elegida por el operator 2026-08-18): la divergencia de forma se emite **estructurada por el logger del paquete** (el `RedactingFilter` ya está activo) y **no es fatal en runtime**; los drivers `main_*.py` corren en **modo estricto** (divergencia → finding). El cambio es *silencioso → observable*, NO *tolerante → fatal*. Razón: estricto puro cambia corrección silenciosa por indisponibilidad ruidosa en un cliente de datos de mercado en vivo. |
| DT-03 | **Sin código compartido entre paquetes** (constraint locked del monorepo). El helper de decode se **copia verbatim** en los 6 paquetes, igual que hoy `SafeModel`/`_coerce` (3×) y `_params.drop_none` (Phase 21-02, D-03). NO se crea un `market-libs-core`: el costo no es esfuerzo, es acoplar los ciclos de release de seis wheels publicables independientemente. |
| DT-04 | **Sin codegen sync/async.** REFAC-06 está **permanentemente archivado** (unasync SPIKE-005 v1.2 Phase 12 + libcst SPIKE-006 v1.3 Phase 18, dos NO-GO firmados por el mismo root cause de content-absence bajo el bar D-02). La paridad sync/async se **AFIRMA con un test de introspección**, no se genera. Ese test es el sustituto afirmativo de REFAC-06. |
| DT-05 | `Model.from_api(payload)` se **preserva como constructor público** de modelos (back-compat con los tests y consumidores existentes); cambia su **implementación interna**, no su firma. Evita churn masivo en las suites de los 3 paquetes que ya tienen modelos. |
| DT-06 | **Cero `Any`/`dict[str, Any]`** en retornos de funciones exportadas en `__all__`. Exentos y explícitamente excluidos por el gate: dunders (`__reduce__`, `__deepcopy__`, `__getattr__`), helpers internos con `_` (incluido `_matriz_legacy_request`) y los `_request` de transporte que devuelven `httpx.Response`. |
| DT-07 | Parámetros de dominio enum-like → `Literal` (patrón `matriz/types.py` + `iol.InstrumentType`). **El conjunto de valores sale de la verificación en vivo, nunca de suposiciones** — un `Literal` incompleto rompe llamadas legítimas. |
| DT-08 | **Bumps de semver por paquete afectado**, documentados en el README changelog de cada uno. `iol-client` 0.2.0 → **0.3.0** es source-breaking (dict → modelo) bajo minor de 0.x, con callout explícito (precedente: v0.2.0 de market-data y el D-01/D-03 de Phase 28-01). Los paquetes cuya superficie no cambie NO se re-publican. |
| DT-09 | El **gate de superficie** (AST) y el **test de paridad** son entregables de primera clase, no nice-to-have: sin ellos la homogeneización se degrada en tres releases, porque no hay código compartido que la imponga. |

## Requisitos → fases

| Req | Descripción | Fase |
|-----|-------------|------|
| DEC-01 | Decoder único de política observable (`msgspec` interno + emisión estructurada de divergencias + modo estricto para drivers), copiado verbatim en los 6 paquetes; `_coerce` reemplazado preservando `from_api` | 29 |
| TYP-01 | `iol-client` tipado: `models.py` nuevo + 4 funciones de datos × sync/async × método/shim + `mercado`/`plazo` como `Literal` | 30 |
| TYP-02 | Modelos para los 5 endpoints de ops (`higyrus.get_health`; `market-data.get_health`/`get_health_feed`/`add_holidays`/`delete_holiday`) | 31 |
| TYP-03 | Estructura uniforme: `models.py` + `types.py` presentes en los 6 paquetes (aun mínimos, incluido el stub `wallets-client`) | 31 |
| GATE-TYP-01 | Gates de homogeneidad en CI: check AST de superficie + test de paridad sync/async por introspección + cierre de **D-16** (enrolar `market-data-client` en mypy `files`, import-linter `root_packages`, `ci.yml:85` + contrato `_core`) | 32 |
| LIVE-TYP-01 | Verificación en vivo de la nueva decodificación en los 4 paquetes verificables + fixes de divergencias in-cycle | 33 |
| PUB-TYP-01 | Releases por paquete afectado (bump + changelog + PR + tag + GitHub Release) | 34 |

## Roadmap (6 fases — continúa la numeración de v1.5; empieza en Phase 29)

### Phase 29 — Decoder observable (DEC-01) *(load-bearing, PRIMERO)*
- `msgspec` a runtime deps de los 6 paquetes; helper de decode copiado verbatim por paquete
  (DT-03), con dos modos: **observable** (default de runtime) y **estricto** (drivers).
- Reemplaza `_coerce` en los 3 paquetes con `SafeModel`, preservando la firma `from_api` (DT-05).
  La tolerancia deja de ser silenciosa: cada sustitución emite una divergencia estructurada por el
  logger del paquete, que ya pasa por `RedactingFilter` (nunca loguear payloads con credenciales).
- Tests mockeados: campo faltante, tipo equivocado, campo extra, payload no-dict, `None`/204;
  modo observable NO levanta y emite exactamente un registro; modo estricto levanta con la ruta del
  campo; el logger no filtra credenciales (sentinel `caplog` como en SEC-01).
- **Merge gate:** las suites de los 3 paquetes con modelos siguen verdes **sin cambios de tests**
  (prueba de que `from_api` mantuvo el contrato).
- Espeja el patrón de v1.5: la pieza load-bearing se construye primero y se testea adversarialmente.

### Phase 30 — `iol-client` tipado (TYP-01) *(primera superficie que ejercita el decoder end-to-end)*
- `models.py` nuevo en `iol-client` (el único paquete con datos y sin modelos), con los modelos de
  cotización, serie histórica e instrumentos; campos wire en camelCase verbatim (convención
  `N815`-exenta ya establecida).
- Las 16 firmas migradas (4 funciones × método/shim × sync/async) + los parsers de `_core.py`.
- `mercado` y `plazo` → `Literal` con el conjunto **derivado de la verificación en vivo** (DT-07);
  si el set no se puede cerrar con evidencia, queda `str` y se documenta como carry-forward.
- `main_iol.py` migrado de `.get(...)` a acceso por atributo (6 sitios detectados).
- Breaking sobre la superficie pública de iol → alimenta DT-08.

### Phase 31 — Endpoints de ops + estructura uniforme (TYP-02, TYP-03)
- Modelos para los 5 endpoints de health/ops; los de `market-data` (`add_holidays`,
  `delete_holiday`) son **mutaciones ya publicadas en v0.4.0** → verificar que el modelo no rompa
  el contrato del gate de mutación.
- `models.py` + `types.py` en los 6 paquetes, aun mínimos: `ambito` y `wallets` los reciben vacíos
  pero presentes, para que la estructura sea idéntica y el próximo endpoint nazca con lugar donde
  vivir.

### Phase 32 — Gates de homogeneidad + D-16 (GATE-TYP-01)
- **Gate de superficie:** script AST que recorre `__all__` de los 6 paquetes y falla si alguna
  función exportada anota `Any`/`dict[str, Any]` como retorno, con las exenciones de DT-06.
- **Test de paridad sync/async:** introspección comparando nombres públicos y `get_type_hints()`
  entre `client.py` y `aio.py` por paquete (DT-04). Debe ser **no-vacuo** — precedente Phase 15
  WR-01/WR-02, donde un guard vacuo pasó sin verificar nada.
- **D-16:** enrolar `market-data-client` en el `files` de mypy del root (`pyproject.toml:97`, hoy 5
  paquetes), en `root_packages` de import-linter (hoy 4) y en el loop mypy-tests de `ci.yml:85`
  (hoy 5); **escribir el contrato de import-linter de `market_data_client._core`** (los otros 4
  paquetes ya tienen el suyo). Está en el backlog "Deferred to v1.6+" desde Phase 24.

### Phase 33 — Verificación en vivo + fixes (LIVE-TYP-01)
- Corre los drivers en **modo estricto** contra las APIs reales (ámbito, iol, higyrus, matriz;
  market-data contra develop con las creds Auth0 del operator).
- Cierra los `Literal` de DT-07 con evidencia real.
- **Expectativa explícita:** este es el momento donde aparecen las divergencias que la tolerancia
  silenciosa venía ocultando. Toda divergencia se documenta como finding y se corrige in-cycle,
  espejada sync/async, con test de regresión mockeado (convención v1.0-v1.5).
- Cycle closure PASS por paquete.

### Phase 34 — Releases por paquete (PUB-TYP-01)
- Bump + README changelog + `uv.lock` refresh **sólo** de los paquetes cuya superficie cambió.
- PR → CI verde (matriz 6 paquetes × py3.12/3.13) → merge con merge-commit real (nunca squash:
  orfanaría los SHAs que los SUMMARY cross-referencian, D-11 de Phase 28-02) → tag por paquete →
  `release.yml` → GitHub Release con wheel + sdist.
- Ops irreversibles detrás de checkpoint humano explícito (precedente D-18 de v1.5: dos gates
  independientes, nunca colapsados).

## Riesgos / notas

- **`msgspec` es una extensión en C.** Entra a seis wheels cuyo perfil de deps hoy es puro-Python
  (`httpx`, `python-dotenv`, `tenacity`, `platformdirs`). Hay wheels prebuilt para CPython 3.12/3.13
  en las plataformas del CI, pero un consumidor en una plataforma sin wheel necesitaría compilador.
  Evaluar en Phase 29 si conviene declararlo `extra` opcional con fallback al `_coerce` actual.
- **Riesgo de descubrimiento masivo en Phase 33.** La tolerancia silenciosa actual puede estar
  ocultando divergencias acumuladas en 3 paquetes; la primera corrida estricta podría destapar
  muchas de golpe y desbordar el scope del milestone. Mitigación: correr el modo estricto de forma
  exploratoria **al final de Phase 29** (antes de comprometer las fases 30-32) para dimensionar el
  volumen real.
- **Breaking de superficie pública en paquetes ya publicados.** `iol-client` 0.2.0 y
  `market-data-client` 0.4.0 tienen consumidores; el cambio dict → modelo es source-breaking. DT-08
  lo encuadra en minor de 0.x con callout, pero conviene relevar quién consume iol antes de Phase 30.
- **`Literal` incompleto es peor que `str`.** Cerrar el set de `mercado`/`plazo` con suposiciones
  rompería llamadas legítimas; DT-07 exige evidencia live y acepta dejarlo en `str` si no se cierra.
- **La duplicación 6× del decoder es deliberada** (DT-03) pero real: un fix en el helper hay que
  aplicarlo seis veces. Es el mismo trade-off ya aceptado para `SafeModel`, `_transport`,
  `_logging` y `_validate_max_retries`.
- **Nota operativa (no del milestone):** el `.venv/` del repo apunta a un intérprete inexistente
  (`.venv/bin/python3 -> python` colgado) y `uv` no puede recrearlo porque `.venv/lib` está tomado
  por un proceso. Las verificaciones de este plan se corrieron en entornos aislados
  (`uv run --no-project`). Conviene cerrar el proceso y re-sincronizar antes de arrancar.

## Fuera de alcance de v1.6

- **Pydantic v2** como validador — descartado por coerción lenient por default (enmascara
  divergencias) + peso en seis wheels. Ver evidencia.
- **`TypedDict`** como mecanismo de tipado — descartado empíricamente: mypy no detecta typos vía
  `.get()`, que es el estilo de acceso real de los drivers.
- **Paquete interno compartido** (`market-libs-core`) — descartado por DT-03: acoplaría los ciclos
  de release de seis wheels independientes.
- **Codegen single-source sync/async** (REFAC-06) — permanentemente archivado (DT-04); no re-abrir
  sin una clase de herramienta que sintetice constructs content-absent, o una decisión de relajar
  D-02.
- **`wallets-client`** más allá de recibir `models.py`/`types.py` vacíos — sigue stub sin endpoints
  reales ni servicio verificable.
- Carry-forwards del monorepo que siguen en backlog: prod-vs-remarkets (D-MATZ-27),
  `matriz_client.ws_client` live verification, token encryption at-rest, streaming SSE
  (`STREAM-MD-01`), disk token cache de market-data (`SEC-MD-01`), validación de firma JWT
  (`SEC-MD-02`).
