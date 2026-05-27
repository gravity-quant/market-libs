# Findings: <pkg>-client

> Plantilla de hallazgos clasificados (HARN-05 / D-07 / D-08 / D-09 / D-10 / D-11).
> Las fases 2-5 copian este archivo a `.planning/verification/<pkg>-findings.md`
> (uno por cliente verificado) y lo completan durante la verificacion en vivo.
> **No hay campo de severidad** (D-08): un hallazgo se clasifica por *clase* y se
> sigue por *estado*, no por gravedad.

## Run Context (ART)

El encabezado ART (Ambiente . Run . Timestamp) deja registro reproducible de
*contra que* se corrio la verificacion. Las APIs en vivo cambian con el horario de
mercado y los datos disponibles, asi que sin este contexto un hallazgo no es
reproducible.

- **Timestamp:** `<ISO-8601>` -- p.ej. `2026-05-27T14:32:05-03:00`
- **Resolved base URL / env:** `<url>` (`<remarkets|prod|public>`) -- la URL base
  *resuelta* del cliente al momento de correr (no la constante por defecto; leer
  el estado de modulo `<pkg>_client.client._base_url`).
- **Market hours note:** `<abierto|cerrado>` -- afecta los paths que dependen de la
  sesion de mercado (cotizaciones intradia, libros de ordenes, etc.).

## Index

Una fila por hallazgo. El estado refleja el punto del ciclo de vida (ver abajo).

| ID   | Class            | Surface | Status    |
|------|------------------|---------|-----------|
| F-01 | SHAPE            | sync    | OPEN      |
| F-02 | SYNC-ASYNC-DRIFT | both    | CONFIRMED |

- **ID:** `F-NN`, correlativo por archivo.
- **Surface:** `sync` | `async` | `both` (que superficie del cliente expone el bug).

## Clases fijas (D-09)

El conjunto de clases es **fijo** -- todo hallazgo cae en exactamente una:

| Class              | Que captura |
|--------------------|-------------|
| `SHAPE`            | La forma/tipos del payload real difieren de lo que el cliente asume (claves faltantes, tipo distinto, anidamiento inesperado). |
| `AUTH`             | Flujo de autenticacion: token, refresh, scopes, expiracion, headers de auth. |
| `ERROR-MAP`        | El cliente mapea mal un error de la API (status HTTP o `"status": "ERROR"` del payload) a la excepcion equivocada (o ninguna). |
| `PARAM`            | Un parametro de request se serializa/nombra/formatea distinto de lo que la API espera. |
| `SYNC-ASYNC-DRIFT` | La logica de `client.py` y `aio.py` divergio: el bug aparece en una superficie y no en la otra (deuda conocida: logica duplicada). |
| `NO-DATA`          | La API responde sin datos (204, lista vacia, `null`) en un path donde el cliente espera contenido. |
| `ANTI-BOT`         | Defensas anti-bot del servicio (User-Agent, rate limit, challenge) rompen al cliente -- relevante sobre todo en `ambito-financiero-client`. |

## Ciclo de estados (D-08)

```
OPEN  ->  CONFIRMED  ->  FIXED
                              \
                               (terminales alternativos)  EXPECTED  |  NO-FIX
```

- **OPEN:** discrepancia observada, todavia sin confirmar que sea un bug real.
- **CONFIRMED:** reproducida y entendida; es un bug del cliente (no un dato puntual).
- **FIXED:** corregido en `client.py` **y** en `aio.py` (ambas superficies, por la
  deuda de logica duplicada) **y** acompanado de un test de regresion mockeado
  enlazado (ver convencion de regresion abajo).
- **EXPECTED** *(terminal)*: la divergencia es el comportamiento esperado/correcto;
  no se corrige nada (se documenta para no re-abrirla).
- **NO-FIX** *(terminal)*: bug real pero deliberadamente no corregido este ciclo
  (con la razon documentada).

## Detalle por hallazgo

Una seccion por cada fila del indice.

### F-01 -- <titulo>

**Class:** `SHAPE` . **Surface:** `sync` . **Status:** `OPEN`

> Estado: uno de OPEN -> CONFIRMED -> FIXED, o terminal EXPECTED / NO-FIX.

- **Expected:** <lo que el cliente asume (forma, tipo, codigo, parametro)>
- **Actual:** <lo que devolvio la API en vivo>
- **Diff:** <campos/tipos/codigos divergentes -- el delta concreto>
- **Regression:** `<test path>` . `Regression: ... (issue #NNN)`

> **Convencion de regresion** (existente en el codebase): el test de regresion
> mockeado lleva un docstring con la referencia al bug, p.ej.
> `"""Regression: CL viene como objeto {price, size, date}, no como float (issue #102)."""`.
> Un hallazgo solo llega a `FIXED` cuando existe ese test enlazado.

## Pipeline de captura -> anonimizacion -> fixture (D-10 / D-11)

Los fixtures de regresion salen de payloads reales, pero **ningun payload crudo con
PII puede entrar a git**. El pipeline es de **dos etapas** con una **revision humana
obligatoria** en el medio:

```
1. captura cruda      verification.capture.capture(pkg, endpoint, raw)
                      -> .planning/verification/captures/<pkg>-<endpoint>.json   [GITIGNORED]

2. anonimizacion      verification.anonymize.anonymize(raw, Denylist(...))
                      -> reemplaza las CLAVES PII por sinteticos de igual forma,
                         preservando los valores no-PII relevantes para el formato
                         (p.ej. el decimal AR "1.415,00") para que el bug se reproduzca

   --- REVISION HUMANA OBLIGATORIA (D-10) ---
   un humano confirma que no queda PII real antes de mover/commitear el fixture

3. fixture committeable  packages/<pkg>/tests/fixtures/<...>.json   [committeable]
```

- **Garantia de construccion (D-11):** el directorio `.planning/verification/captures/`
  esta en `.gitignore`, asi que el payload crudo nunca es committeable por construccion
  (probado con `git check-ignore`).
- **Preservacion de formato (D-10):** solo las *claves* del `Denylist` reciben un valor
  sintetico; los formatos no-PII (decimal AR, numero-vs-string del JSON, claves de
  envelope) se conservan verbatim para que el fixture anonimizado siga reproduciendo el bug.
- **Snapshot de esquema (D-12):** `verification.schema.schema_of` produce un snapshot de
  claves + tipos (nunca valores), PII-free por construccion; el primero se commitea en la
  Fase 2 (DRIFT-01).
