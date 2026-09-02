# Milestones

## v1.8 Cierre de deuda post-v1.7 (Shipped: 2026-09-02)

**Phases completed:** 5 phases, 24 plans, 58 tasks

**Key accomplishments:**

- Contrato de auditoría de 8 secciones que fija denominador 62, claves ordinales de fila, nueve reglas de disposición y el esqueleto exacto de la sección `## Validation Audit`, sobre un árbol de v1.7 probado idéntico al tag (`37a83fe6`) con diff vacío.
- Las 13 filas de la Phase 35 quedan dispuestas con evidencia nombrada — el mapa que shipeó con una sola fila placeholder se reconstruyó en 12 filas reales desde los cinco archivos de plan, se re-ejecutaron 11 de ellas más la manual-only contra el árbol congelado de v1.7 (todas verdes), el único paso RED de TDD se dispuso históricamente en vez de reportarse como rojo, y `nyquist_compliant` sigue en `false` por evidencia medida.
- 1. [Rule 1 - Bug] El plan dice "las nueve filas de pytest sobre `packages/market-data-client/tests/`"; son ocho
- Las 14 filas del mapa de la Phase 37 quedan dispuestas bajo clave ordinal `37-r01`..`37-r14` con evidencia re-ejecutada esta sesión contra el árbol congelado de v1.7; el selector muerto `-k alias_surfaces` (0 de 74 seleccionados, exit 5) queda re-apuntado a los dos tests que sí cubren la conducta, con ambos comandos escritos; `nyquist_compliant` sigue en `false` con rationale que dice por qué 14 verdes no bastan.
- Las 9 filas de la Phase 38 —8 de mapa más 1 manual-only— quedan dispuestas 7 / 2 / 0: siete con evidencia re-ejecutada esta sesión contra el árbol congelado de v1.7, y dos de revisión de documento sostenidas por la confirmación humana fechada `2026-08-29T22:04:57Z` que ya existía en disco, no por un juicio nuevo; el regenerador de snapshots se corrió y dejó el árbol byte-idéntico; `nyquist_compliant` sigue en `false` por la condición (b) de R-09.
- Las 15 filas de la Phase 39 dispuestas 10/1/4 contra el árbol congelado de v1.7 con cero tráfico de red, y el criterio 3b anclado por `not_verifiable_retroactively: 4` — la única de las cinco fases que declara en su propio front-matter que retiene ítems no re-verificables.
- Las 62 filas de las cinco fases de v1.7 cierran contra su denominador con 54 verificadas ahora, 4 históricas y 4 no re-verificables, cero flags movidos a `true`, cero locks nuevos, los 40 preexistentes sin enrolar declarados inertes y ruteados a la Phase 45, y el árbol de fuente de v1.7 sin cambiar ni un byte de punta a punta.
- `scripts/literal_census_33.py` deja el substring-match `if "remarkets" not in base:` y pasa a decidir el venue por igualdad exacta de hostname contra el MISMO objeto que publica `main_matriz.py`, pinneado por identidad (`is`) y por 13 casos de spoofing en un lock enrolado en CI, más el header `CENSUS-HEADER`/`CENSUS-DLOCK` antes de la primera request y el flag `--matriz-only`.
- La mitad abierta del plan 33-06 quedó medida: `matriz-client` censó 8 paths sobre 3 endpoints contra `bbsa` detrás del gate portado, con venue y timestamp en el encabezado, y el resultado es lo contrario de un conjunto prolijo — el vendor emite 6 CFI codes y 2 tipos de orden que los alias declarados no contienen, así que el D-lock (b) de la Phase 29 sale de esta fase reafirmado con una razón medida en vez de una razón de principio.
- La alcanzabilidad del vendor de higyrus quedó MEDIDA hoy —`socket.gaierror` en resolución y `httpx.ConnectError` en `login()`, ambos con el errno `[Errno 8] nodename nor servname provided, or not known` citado verbatim y probado libre de leak— y el driver completo corrió dejando un sobre de evidencia con `captured_at` de esta sesión y veredicto `SKIPPED` con causa medida, nunca un cero silencioso.
- `main_market_data.py` instrumentado con `capture()` + envelope timestampeado en los dos probe sites de reference, corrido en vivo contra `develop` (exit 0, `MARKET_DATA_VERIFY_MUTATING` sin setear), produciendo dos capturas fechadas `2026-08-31T21:27Z` en el staging gitignored y `42-WIRE-READ.md` committeado y PII-free que marca el baseline del 2026-07-31 como NO AUTORITATIVO para SHAPE-01 — con el baseline write-once intacto y el payload crudo fuera de git.
- El destino nombrado del bloqueo de higyrus pasó a llevar la fase que más recientemente lo midió (`LIVE-HIGY-42`) en los 14 sitios vivos y sólo ahí —la aserción contra el censo congelado de v1.6 conserva sus 2 ocurrencias del nombre viejo, verificado por conteo exacto— y el sobre de evidencia lleva el destino nuevo porque una segunda corrida real lo reescribió, cuyo veredicto coincidió con la primera medición de la sesión.
- El backlog deja de arrastrar una afirmación verificada falsa a otro milestone —la entrada `LIVE-MATZ-33` ya no dice que el script tenía el gate listo, y las entradas forward-looking de higyrus llevan el destino renombrado con la causa re-medida de hoy— mientras la historia congelada queda byte-idéntica; y los cinco criterios de éxito de la fase reciben una disposición explícita con evidencia nombrada, cero filas sin disponer, sobre los 4 gates de CI verdes.
- `Instrument` gana los 6 campos wire-only medidos mas `active` nullable y espeja `market_id` sobre su alias camelCase deprecado; `Segment` se reemplaza por `{segment, live_instruments}` y `get_segments()` deja de devolver filas enteramente vacias.
- `ingestor.subscription` deja de ser un `extra` opaco y pasa a ser `FeedSubscription`, un modelo anidado de 15 campos que el walker sí camina; las otras cuatro claves medidas se declaran con el tipo que su evidencia respalda, y el payload medido del 2026-08-31 decodifica con CERO records de divergencia.
- La Phase 43 queda cerrada con evidencia ejecutada en vez de afirmada: `43-DISPOSITION.md` documenta la disposición de los 17 campos con cero filas sin disponer, mide el antes/después de `get_segments()` corriendo la forma pre-fix contra la actual, prueba D-14 por identidad de objeto función, y registra los 4 jobs de CI en verde sin bump de versión en ninguno de los tres sitios.
- `market-data-client` queda en `0.7.0` en los cuatro sitios de versión, con `FeedSubscription` re-exportado (superficie 186 → 187), un changelog `### v0.7.0` de dos tablas de migración separadas, `uv.lock` refrescado por un único run con churn `1 1`, los 15 checks de CI espejados en verde localmente y la branch pública `milestone/v1.8-cierre-deuda-post-v1.7` empujada por fast-forward — sin PR, sin tag y sin merge.
- PR #16 (market-data-client 0.6.0 → 0.7.0) merged into `origin/main` via a real two-parent merge commit after explicit operator approval at the D-08(a) checkpoint; no tag created.
- `market-data-client-v0.7.0` annotated tag pushed on the live-re-resolved merge commit; public GitHub Release carries wheel + sdist; installed-distribution deep chain against the public wheel passes; other five packages' tag counts unchanged; phase-close gate-authorship audit closed at 0/2.
- El docstring del gate de superficie pasa de tres cifras congeladas a un registro reproducible (histórico pinneado a `00ffb2f~1`, vigente fechado 187 / 337 / 467), `probe_parity` vuelve a comparar segments en vez de salir siempre por la rama de excepción, e `IN-05` deja de figurar como deuda pendiente.
- El driver de market-data deja de escribir dos bloques `### F-` por una sola divergencia de schema —sync y async colapsan bajo la clave `(func, digest)`— sin poder tragarse una divergencia distinta sobre el mismo endpoint y sin quemar un fid en el no-op, con las tres propiedades pineadas por un test de falsificación cuya no-vacuidad está demostrada.
- Los 7 sitios de drift de D-02 quedan cerrados con cuatro formas distintas de no-op —una por contrato de retorno— y un lock por AST sobre los 5 drivers que pinea tanto el orden (guarda antes del fid) como la forma, con las dos violaciones demostradas en rojo por separado.
- Criterio 1 — el dedupe colapsa lo repetido y NO colapsa lo distinto.

---

## v1.7 API tipada con Null Objects (Shipped: 2026-08-30)

**Phases completed:** 6 phases, 28 plans, 56 tasks

**Key accomplishments:**

- **Null Object foundation** (Phase 35): `SafeModel.__bool__`/`empty()` copied verbatim across the 4 base-class hierarchies of all 6 packages; the `_decode` walker collapses `null`/absent on a non-optional model/list field to an empty instance without a divergence record, while a wrong-typed value still diverges and stays fatal under `strict_decode`. Zero public-surface changes; all 4 v1.6 CI gates stayed green.
- **`market-data-client` `market_data` fully typed** (Phase 36): `MarketDataEntries`/`BookLevel`/`EntryValue` replace `dict[str, Any] | None`, with 6 ergonomic alias properties (`last`/`bids`/`offers`/`settlement`/`close`/`open_interest`); the Phase 33 `| None` widening on chain-link fields is surgically revoked by field role.
- **`matriz-client` residual dicts typed + shared aliases** (Phase 37): `tickPriceRanges`, `AccountReport.report`/`detailedAccountReports`/`portfolio` typed against real payloads (sole exemption `UnknownFrame.raw`); the same 6 alias properties land on `MarketDataSnapshot`, shared verbatim by REST and WS frames.
- **`iol-client` `puntas` Null Object + full audit of the rest** (Phase 38): `Cotizacion.puntas` → `list[Punta]`, `Titulo.puntas` → `Punta` Null Object; higyrus/ámbito/wallets audited field-by-field with a fully-dispositioned census (142 higyrus fields/15 classes independently AST-derived, zero undisposed rows).
- **Live deep-chain verification found a real data-loss bug** (Phase 39): matriz's `byCFICode`/`bySegment` endpoints were silently dropping the flat instrument identifier — ~9160 instruments without a symbol — fixed in-cycle in `_core` with sync/async mirror + 13 regression tests. The D-MATZ-33 gate was widened from substring-match to an exact-hostname allowlist, unblocking the first real live matriz run since v1.0.
- **4 breaking releases published under double human gate** (Phase 40): `market-data-client` 0.6.0, `iol-client` 0.4.0, `matriz-client` 0.3.0, `higyrus-client` 0.3.0 — real two-parent merge commit `8e0013f`, changelog callout + migration table per package, verified post-publication by installing from the 4 public wheels (re-confirmed independently at milestone close via a retroactive `40-VERIFICATION.md`, 22/22 must-haves).

---

## v1.6 Tipado homogéneo de la superficie pública (Shipped: 2026-08-27)

**Phases completed:** 6 phases, 44 plans, 107 tasks

**Key accomplishments:**

- Three signed policy artifacts — the 6-way `from_api` semantics matrix with per-package `DecodePolicy` constants, a 12-lock aggregation contract resolving strict-on-extra and the dedupe key, and the D-09 lock keeping RESPONSE fields open as `str` — written before any decoder code exists.
- The tracer slice: a new `_decode.py` in higyrus turns every silent type substitution into a six-key structured record on the package logger, adds the extra-wire-key detection `_coerce` structurally could not have, and higyrus's `models.py` now delegates to it without moving a single return value — 872 pre-existing tests green with zero test-file edits.
- The tracer slice closes: `Client(strict_decode=True)` now reaches the walker through a ContextVar bound at the top of both `_request` implementations, a divergence in observable mode is a structured record, and a marker-free credential literal provably reaches none of the three `LogRecord` surfaces on the decoder path.
- D-lock (a) closed with a signed NO-GO: the stdlib hints-cached walker is the sole decode engine, msgspec rejected on a measured 100 ms budget it beat by 4.8x plus five capability probes showing it cannot express observable mode and would violate the signed D-09 Literal lock.
- The tracer slice reproduces in a second package: market-data carries a byte-verbatim walker, `Client(strict_decode=True)` reaches it through a ContextVar bound at the top of both `_request` implementations, and the two model-level exemptions the semantics matrix records — `MarketDataSnapshot`'s client stamp and `Symbol`'s wire-key mirror — survive the delegation with a proof that interleaved async tasks never clobber each other's mode.
- 1. [Rule 2 - Missing critical functionality] The canonical walker has no `dict` branch; matriz declares four mapping fields
- iol and ámbito now carry the same byte-verbatim decode walker as the three packages that have models — and neither of them has a models module, which is the point: a walker that imports cleanly, decodes correctly and reports divergences in a package with no `models.py` beside it is the strongest available evidence that the module has no hidden coupling to one, and that is what makes the verbatim-copy contract enforceable everywhere else.
- matriz's WebSocket daemon thread — the one decode path in the repository that never passes through `_request` and that inherits nothing from the thread that spawned it — now receives the decode mode by an explicit two-halves hand-off, and a strict-mode decode there routes its error instead of killing the connection for every subscriber.
- Five copies of the decode walker now reduce to one canonical hash under eight written normalization rules, five `_logging.py` scan regions reduce to one hash over a marker-delimited region, and the gate runs in the `lint` job — the only CI job on this repo where a cross-package check actually executes — with all four failure modes proven red and reverted green in the same session.
- A ratified per-package divergence floor — higyrus ≥ 22, matriz ≥ 24, market-data ≥ 50, total modelled ≥ 96 — measured by running the shipped walker in observable mode over witness payloads synthesized from the 43-file type-only schema corpus and routed through each package's own response parser, now the declared budget Phase 33's live census must measure itself against.
- `get_quote` now returns a frozen slotted `Cotizacion` end-to-end — model, per-response-scoped parser, 4 signatures, public export — with a RED fixture that fails the typecheck on an attribute typo and cannot rot into a no-op.
- Both list-shaped IOL endpoints now return lists of models across sync and async, and the shared helper that got them there turns an unexpected response shape into a loud `IOLAPIError` instead of the silent empty list this milestone exists to eliminate.
- El endpoint donde la suite y la API más divergían quedó reconciliado en favor de la API: 16 mocks que construían un envelope inexistente ahora reflejan la lista top-level capturada en vivo, el parser que pasaba el payload sin tipar devuelve `list[Instrumento]` y levanta ante cualquier otra forma, y con eso las 16 firmas de `iol-client` están migradas — cero retornos sin tipar en la superficie pública.
- Los tres instrumentos de medición que la migración dict→modelo habría dejado verdes y ciegos —el probe de paridad comparando dos veces el mismo nombre de clase y los dos probes de mapa de campos salteando su bucle entero— quedaron reparados en la frontera con un único adaptador, demostrados no-vacuos por aserción positiva, y respaldados por un round-trip offline que reproduce los 3 baselines committeados byte-idénticos; el README pasó de documentar una API inexistente a registrar la ruptura con su flip de truthiness.
- Task 1 — RED→GREEN shape guards
- `probe_schema_snapshot` y `probe_field_type_map` vuelven a ser función de lo que la API devolvió, no de lo que los modelos declaran: las tres clases de drift que CR-01 probó invisibles (float→str, clave agregada, clave quitada) se detectan de nuevo en los 4 endpoints, y una captura fallida ya no puede reportarse como PASS.
- Both iol drift probes now gate on `raw_wire` key membership instead of on the null sentinel, so a 200-OK JSON `null` body produces 7 SHAPE findings (3 + 4) where it previously produced two false PASSes and zero findings.
- `_capture_raw_wire`'s failure path now reports only the exception's class name and `status_code` (e.g. `IOLAPIError status_code=500`), never `repr(exc)` — closing the BLOCKER where the full upstream error response body (account/instrument identifiers included) was landing verbatim in the git-tracked `iol-client-findings.md` on every capture failure.
- `main_iol._redacted_exc(exc: BaseException) -> str`
- `main_iol.py` deja de destruir su propio entregable (el allocator de fids ahora arranca por encima de los findings ya triageados) y deja de filtrar el body de error upstream por el camino de crash (un `sys.excepthook` redactado que delega en `_redacted_exc` y sigue matando el proceso).
- `_raw_exception_renders` pasa de marcar 3 de 11 formas de fuga a marcar las 11 —incluida `exc.message`, que es literalmente `resp.text`— y el conteo de renderers que matcheaba por nombre se reemplaza por un censo por forma que falsifica las tres bypasses documentadas y prueba, con una igualdad contra el nombre sancionado, que sigue detectando al primero.
- `_redacted_excepthook` —la función escrita para impedir que el body de error upstream llegue a stderr— emitía ese body verbatim en cuanto algo adentro suyo fallaba, porque el contrato de CPython ante un excepthook que levanta es caer al renderer default; ahora la llamada al renderer va adentro de un `try` que bindea un placeholder estático, cada sink va adentro de su propio `contextlib.suppress(BaseException)`, y un tercer detector AST impide que un edit futuro saque cualquiera de los tres guards en silencio.
- El lock que 30-11 amplió sancionaba `getattr` mirando sólo el nombre del callee, con lo cual `getattr(exc, "message", "")` —el body de error upstream verbatim— quedaba tan permitido como el `getattr(exc, "status_code", None)` del renderer sancionado; ahora la decisión se toma sobre el argumento de nombre de atributo con la misma constante que gobierna la escritura directa, `__dict__` entró a esa constante, y el censo de renderers dejó de enumerar qué delegaciones cuentan para enumerar la única que no.
- 1. [Rule 3 — Blocking] Guard discovery scoped to class bodies instead of `ast.walk` over the module
- A stdlib-only `tools/check_uniform_structure.py` wired into the CI `lint` job, enumerating `packages/` from disk, plus the 7 docstring-only modules that give all 6 packages the same `models.py` + `types.py` layout — observed RED with all 7 paths named, then GREEN.
- `higyrus_client.Health` — a one-field frozen `SafeModel` wired end to end: declared from the live capture, decoded through the Phase 29 walker, dispatched on both sync and async shells via one shared parser, re-exported, golden-regenerated, and strict-typechecked by CI.
- Six frozen `SafeModel` classes across three nesting levels, one shared parser split into two decorated and newly-guarded ones, eight signature sites retyped on both shells — and the driver's health schema snapshots kept pointed at the raw wire so the typing change imports no observability regression.
- Both new parsers PRESERVE the T-26-13 tolerance.
- 33 pre-existing strict-mypy errors repaired inside four Phase-29 decode test suites, turning the `typecheck` job green for the first time since 2026-08-18 with zero config changes and zero test removals — 1682 tests still passing.
- A stdlib-AST-only ratchet that walks every `__all__` name (including methods of exported classes) and fails on an untyped return, proven non-vacuous by five automated bounds in the 6×2 CI matrix and wired as a blocking step of the existing `lint` job — 6 packages, 178 `__all__` names, 319 definitions, 23 exempted, 0 violations on today's tree.
- D-09 resuelto a option-a por auto-resolucion al default investigado: `market_data_client.aio.configure` recibira `http_client: httpx.AsyncClient | None = None` en el plan 32-04, con consecuencia semver minor para el re-publish de la Phase 34 — cero archivos fuente tocados por este plan.
- A shared runtime-introspection walker that derives public names from `dir()`/`__module__` rather than `__all__`, compares resolved `get_type_hints()` through a four-rule normalization table, and asserts per-package integer floors on both the surface size and the comparison size — it found exactly one real divergence in the monorepo on its first run, that divergence was demonstrated as a failing test, and it was closed in source without a single test or rule being edited.
- The four enrollment lists now agree in one commit — one substantive edit (`packages/market-data-client/src` into mypy `files`, 62 → 75 source files, zero fixes) plus two deliberate exclusions written down with their structural reasons — and the `market_data_client._core` boundary contract has for the first time in this repository been observed FAILING under a deliberate violation instead of merely reported KEPT.
- All six workspace packages now carry an in-package sync/async parity test that runs in every one of the twelve CI matrix legs — wallets included, on the module axis and with its missing `Client`/`AsyncClient` pair asserted positively rather than skipped — and every `ci.yml` job plus all twelve legs were reproduced locally green, at 1707 passing on both Python 3.12 and 3.13, with the shared walker byte-unchanged.
- El criterio 1 de la Phase 33 pasa de no tener mecanismo a tener uno probado end to end: un record de decode de seis claves emitido por `higyrus_client` dentro de una llamada bindeada aterriza como un finding `SHAPE` con endpoint, modelo, ruta de campo y superficie — y los tres canales de pérdida silenciosa que convertirían una corrida en vivo en un falso limpio quedan cerrados y pineados por falsificación desde el primer commit.
- 1. [Rule 2 - Missing critical] Un solo `_shape_probe_result` habría roto 37 probes bajo modo estricto
- 1. [Rule 3 - Blocking] La firma de helper que el plan especifica ROMPE dos locks AST de `main_iol.py`
- 1. [Rule 1 - Bug] El `<action>` pide un `append_finding(class_="SHAPE")` que duplicaría el finding que el handler ya escribió — y cuyo título es además imposible de componer
- Invocación verbatim
- 1. [Rule 3 - Blocking] El censo de matriz no puede correr sin rodear el gate D-MATZ-33, y rodearlo está prohibido
- Nuevos
- URL y número del PR (12), la salida literal de `gh pr checks 12` con los
- `2026-08-27T21:33:18Z`.

---

## v1.5 market-data-client · mutaciones (Shipped: 2026-08-17)

**Phases completed:** 4 phases (25-28), 17 plans, 63 tasks
**Milestone tag:** `v1.5` · **Package release:** `market-data-client-v0.4.0` (merge commit `5d0825d`, PR #10, release.yml run `31549711805`, GitHub Release with wheel + sdist)
**Source delta:** 42 files, +9,188/−174 LOC (packages/: 27 files, +5,059/−58) · **Package tests:** 392 green; ruff + ruff-format clean; regression gate 387 green

**Key accomplishments:**

- **Mutating-gate default-refuse (Phase 25, GATE-MD-01):** `Client()`/`AsyncClient()` rechazan por defecto toda mutación con cero tráfico HTTP/Auth0 (`MarketDataMutationNotAllowedError`); doble gate opt-in `mutating_allowed` + hostname exacto (`urlsplit().hostname ==`, nunca substring) compuesto en `_ensure_mutation_allowed()`, primer statement literal de cada método de mutación en ambas superficies (AST-verified), heredado por `with_options`.
- **Symbols write (Phase 25, MUT-MD-01):** `create_symbol` / `create_symbols` (batch 1-500) / `update_symbol` sync+async vía builders puros de `_core.py`, modelos de request tipados frozen (`NewSymbol`/`NewSymbols`/`SymbolPatch`), 422→error tipado, test in-package de paridad de superficie pública.
- **Calendar write (Phase 26, MUT-MD-02):** `set_calendar_config` / `delete_calendar_config` / `preview_calendar_config` / `add_holidays` / `delete_holiday` sync+async con `MarketHoursIn`/`HolidayIn`/`HolidaysIn` — 13 nombres públicos nuevos, todos detrás del mismo gate de la Phase 25 (verificado por el integration checker: 8/8 métodos gated 1:1).
- **Verificación en vivo segura (Phase 27, LIVE-MUT-01):** superficie de mutación ejercitada contra develop con identificadores dedicados `GSDPROBE/*` y ciclo create→verify→revert; 5 divergencias corregidas in-cycle (`update_symbol(symbol_id)` str→int|str, 5 campos defaulted de `Symbol`, alias deprecado `Symbol.marketId`, unwrap de envelope symbols-write, reconciliación de campos de `CalendarDay`).
- **Publish v0.4.0 (Phase 28, PUB-MUT-01):** doble gate humano D-18 (merge 2026-08-01, tag push 2026-08-12, nunca colapsados); tag anotado sobre el merge commit real de PR #10; `release.yml` sin editar publicó wheel + sdist; memoria de releases refrescada en 6 regiones; verificador 15/15 contra estado vivo de GitHub.
- **Hardening post-release:** 28-REVIEW (3 critical + 5 warning) corregido 8/8 en commits atómicos — claim falso del guardrail `confirm`, ejemplos `get_marketdata()` del README, índice MEMORY.md 2 releases desactualizado — + `test_version_metadata.py` atando `__version__` a `pyproject`. Audit de milestone: passed (5/5 reqs, 6/6 integración).

**Known deferred at close:**

- El wheel v0.4.0 publicado embebe el README pre-fix; las correcciones llegan en el próximo release. Las líneas de instalación hardcodean el tag por release.
- `28-SECURITY.md` ausente (capability security activa) → `/gsd-secure-phase 28`. `25-VALIDATION.md` en draft (Nyquist TODO). 4 INFO del 28-REVIEW abiertos.
- Deuda pre-existente cross-milestone: `verification/test_matriz_sweep_snapshot.py` (era fase 07) y 66 ítems UAT diferidos (fases 3-27).
- Diferidos a v1.6+: D-16 typecheck coverage (ROADMAP § Backlog); v2: SSE streaming, disk token cache, JWT validation.

---

## v1.4 market-data-client (Shipped: 2026-07-31)

**Phases completed:** 5 phases (20-24), 16 plans, 36 tasks
**Milestone tag:** `v1.4` · **Package release:** `market-data-client-v0.1.0` (merge commit `1ea655d`, GitHub Release with wheel + sdist)
**Source delta:** 31 files, +5,502 LOC (new package) · **Package tests:** 134 green + workspace suites; ruff + ruff-format + mypy-strict clean on py3.12 + py3.13

**Key accomplishments:**

- **Scaffold + Auth0 client-credentials foundations (Phase 20, AUTH-MD-01 + CORE-MD-01):** stood up the 6th monorepo package `market-data-client` mirroring `iol-client` — hatchling/uv metadata + `py.typed`, 4-class typed exception hierarchy, Auth0 `client_credentials` token lifecycle (TTL cache + refresh, `expires_in`) in both sync (`client.py`) and async (`aio.py`, per-loop double-checked `asyncio.Lock`), the pure IO-free `_core.py` (grant builder + token parser + status→exception map + anonymous `/health` builders), full-jitter retry transport pair, `RedactingFilter` credential scrubbing, and `configure()`.
- **Market-data read surface + models (Phase 21, MD-01):** `get_market_data` / `get_latest` / `get_latest_batch` across both surfaces via three pure `_core` builders + parsers; net-new `models.py` with tolerant `SafeModel` `MarketDataSnapshot`/`MarketDataEntry`/`LatestRequest` and client-stamped first-class `received_at`; real `with_options(max_retries=N)` shared-view clone threading `request.extensions["max_attempts"]`. Folded Phase-20 debt D-09 (async header token precedence) + D-10 (permanent 401 re-auth regression tests).
- **Reference-data read surface + models (Phase 22, REF-MD-01):** `get_instruments` / `get_segments` / `get_symbols` / `get_calendar` / `get_calendar_config` across both surfaces via five `_core` builders + parsers; five plain `SafeModel` dataclasses (`Instrument`/`Segment`/`Symbol`/`CalendarDay`/`CalendarConfig`, no `received_at` per D-05); collection endpoints guard 204/null→`[]` (D-06), `calendar/config` returns a single typed model (D-07).
- **Live-verification apparatus + D-09 hardening (Phase 23, LIVE-MD-01):** `main_market_data.py` — the 6th driver — exercises all 10 read endpoints × sync/async through one `Client()` + one `AsyncClient()`, reusing the `verification/` infra (redacted output, write-once schema snapshots, SHAPE-diff, findings lifecycle), gated by `require_env` and wired into `main_verify.py`; a code review + verifier caught and fixed in-cycle a real D-09 never-FAILED defect (post-request processing moved inside each probe's try, locked with a non-vacuous AST regression guard).
- **Release + publish v0.1.0 (Phase 24, PUB-MD-01):** Wave 1 (autonomous) added the package to the `ci.yml` test matrix (py3.12 + py3.13), documented it as the 6th package in CLAUDE.md + MEMORY, and validated lockfile/version alignment (`uv sync --frozen` + `uv lock --check` clean); Wave 2 (gated human go/no-go) opened PR #5, confirmed 15/15 CI green, merged to `main` (`1ea655d`) and pushed tag `market-data-client-v0.1.0`, triggering `release.yml` (unedited, D-02) → GitHub Release with wheel + sdist.

**Known deferred at close (acknowledged by operator — see STATE.md Deferred Items):**

- **LIVE-MD-01 real credentialed sweep — RESOLVED post-close (2026-07-31).** Was deferred at close (apparatus verified 12/12, but no Auth0 creds + VPN in-repo). After the milestone archived, the operator supplied working Auth0 credentials and the real credentialed sweep ran against `market-data-develop.bbsa.com.ar`: full read surface exercised sync+async (`PASS=17`, `market_data snapshots=12`), 9 write-once schema baselines captured (DRIFT-01), and **3 real client-vs-service divergences found and fixed in-cycle** via two follow-up quick tasks — `260731-j93` (`get_latest.symbol` required per OpenAPI/422) and `260731-jim` (`MarketDataSnapshot`/`CalendarConfig` model reconciliation + `parse_market_data_response` envelope-unwrap bug). Final live re-run: 0 real divergences (2 benign NO-DATA EXPECTED). LIVE-MD-01 is now fully satisfied — apparatus **and** real live evidence. Fixes landed post-close on `release/v0.2.0-bump` (not part of the sealed v1.4 tag). See STATE.md Quick Tasks Completed + `.planning/verification/market-data-client-findings.md`.
- **Phase 20 `20-UAT.md`** — surfaced by the pre-close open-artifact audit as a UAT gap; actual status is `passed` with 0 pending scenarios (parser false-positive). No action.
- **v1.5+ deferrals (v2 requirements):** mutations (symbols/calendar POST/PATCH/PUT/DELETE), SSE streaming `GET /marketdata/stream`, on-disk token cache, JWT signature validation (RS256 vs JWKS).

---

## v1.3 Codegen Single-Source (libcst) (Closed: 2026-07-03 — signed NO-GO)

**Phases completed:** 1 phase (18; Phase 19 REFAC-06 DROPPED), 3 plans, 7 tasks
**Git range:** `6d3b749` (docs: start milestone v1.3) → `1333d5f` (docs(phase-18): auto-close todo), 2026-07-02 → 2026-07-03 (23 commits)
**Source delta:** 0 production files — **zero footprint**. The entire milestone lived under `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/` with `libcst` invoked ephemerally (`uv run --with libcst`, never added to dev deps per D-05).

**Outcome:** Signed **NO-GO** (`sebadlf`, 2026-07-03). CODEGEN-01 resolved; REFAC-06 permanently shelved; Phase 19 dropped; duplicate `client.py`/`aio.py` transport shells accepted as a structural feature. A valid, guaranteed milestone deliverable per D-08 (the milestone delivered a signed architectural decision, not code). libcst is a partial gain over unasync — it closes item 4 (`ruff check` I001 + ASYNC1xx) that SPIKE-005 could not — but two independent tools now reach the same strict-D-04 NO-GO for the same content-absence / source-shape-asymmetry root cause.

**Key accomplishments:**

- Stood up the SPIKE-006 libcst spike tree and landed the ~60% inherited D-RIGOR-02 harness — item 10a matriz construct audit (0 unresolved / 959 LOC, verbatim audit.py), item 8 @generated marker via libcst Module.header (STRICT PASS, all 4 commands exit 0), and item 10b matriz 4-file deny-list sha256 byte-identity under per-module libcst scope — with the libcst supply-chain gate operator-approved and libcst kept ephemeral.
- Authored the genuinely-new core of SPIKE-006 — five pure libcst `CSTTransformer` subclasses + an impure driver that transform the un-migrated ámbito `aio.py` into a candidate sync `client.py` — and captured the honest D-RIGOR-02 gate transcript: item 4 (GO-det, `ruff check`) now PASSES (the item unasync failed), but items 1 and 6 (GO-det) FAIL for the exact SPIKE-005 source-shape root cause — `_validate_max_retries` def + `load_dotenv` bootstrap are content-absent from `aio.py` and cannot be synthesized by any pure transform — a signed same-root-cause NO-GO that is a valid, guaranteed deliverable (D-04/D-08), reached without editing `aio.py` or reading `client.py` as a donor.
- Operator-signed SPIKE-006 NO-GO (sebadlf, 2026-07-03) — 7 PASS / 3 FAIL on the 10-item D-RIGOR-02 gate (items 1/3/6 FAIL, same content-absence root cause as SPIKE-005) → REFAC-06 permanently shelved, Phase 19 dropped, zero production footprint.

**Known deferred items at close:** 0 (pre-close artifact audit clear — all artifact types clean). No milestone audit was run: with 2/2 requirements resolved and a spike-only milestone that shipped no code, the signed NO-GO is itself the complete deliverable.

---

## v1.2 Architecture + Auth/Ergonomics Carry-forwards (Shipped: 2026-06-25)

**Phases completed:** 5 phases (12-15, 17; Phase 16 dropped), 18 plans, 40 tasks
**Git range:** `74b22bf` (docs(12): capture phase context) → `a7dbc8f` (ship v1.2 — PR #2), 2026-06-14 → 2026-06-25
**Source delta:** 43 files changed, +3,364 / −531 LOC (packages + drivers + pyproject)

**Key accomplishments:**

- **Phase 12 — Codegen tool-choice spike (REFAC-06, NO-GO):** SPIKE-005 ran unasync round-trip on the ámbito canary + a matriz worst-case construct audit (109 rows, 0 unresolved); the strict D-RIGOR-01 8-item evidence checklist returned **3/8 FAIL — all tracing to a single root cause (source-shape asymmetry between v1.1 sync-first `aio.py` and async-first codegen), 0 unfixable hunks** — so the operator signed NO-GO and REFAC-06 was cleanly deferred to v1.3 with a libcst handoff scope + auto-loaded findings skill.
- **Phase 13 — `client.with_options(max_retries=N)` × 4 packages (ERG-01):** a shallow-clone Client view that shares the underlying `httpx.Client` + `_ClientState` (no resource leak, no re-auth) and threads the override via `request.extensions['max_attempts']` mirroring the v1.1 mutation-gate pattern; the CRITICAL merge gate proves matriz `new_order` under 503 executes **EXACTLY 1 outgoing request regardless of `max_retries=10`** (anti-Pitfall 14, duplicate-order money-on-the-line).
- **Phase 14 — IOL refresh_token disk persistence (SEC-01):** `iol_client/_token_cache.py` with atomic write-then-rename, `fcntl.flock` inter-process locking, 0600 perms, `platformdirs` default path (iol-client only), and CI-refuses-default-path; the three CRITICAL gates land GREEN across sync + async — caplog no-leak sentinel, 20-thread concurrent-write race, and failed-refresh disk cleanup — with `asyncio.to_thread` dispatch for the async mirror.
- **Phase 15 — Driver migration × 4 (REFAC-05):** every `main_*.py` now constructs **exactly one `Client()` / `AsyncClient()` per `main()` run** with all probes threaded through that single instance (ámbito → iol → higyrus → matriz), guarded by a RED-first AST single-Client regression test per driver; probe names / finding titles stay byte-stable vs the v1.1 LIVE-01 baseline `71bf201`, closing the v1.1 iol/matriz LOC-drop residual.
- **Phase 17 — Final live re-verification × 4 (LIVE-03):** operator dispositions captured for ambito/iol/higyrus/matriz, schema snapshot vs baseline `verification-cycle-2026-Q2` clean, `verify_cycle_closure × 4` PASS (iol F-02 FIXED→regression-linked), REQUIREMENTS.md traceability flipped to Complete for REFAC-05/SEC-01/ERG-01/LIVE-03, 0-BLOCKER integration audit, pytest final ≥989 / CI matrix green on Python 3.12 + 3.13.

**Known deferred items at close:** 6 (see STATE.md Deferred Items — 4 stale v1.1-era quick-task status files, the intentional REFAC-06→v1.3 libcst spike todo, and the Phase 15 operator UAT gap superseded by the Phase 17 LIVE-03 gate). REFAC-06 deferred to v1.3.

---

## v1.1 Tech Debt Cleanup (Shipped: 2026-06-14)

**Phases completed:** 6 phases, 30 plans, 52 tasks

**Key accomplishments:**

- Public-surface snapshot test (`inspect.signature` over `__all__`) sweeping ambito/iol/higyrus/matriz with W3-pinned text golden files, deterministic regen script, and Phase 6 entry-baseline (281 tests / 95% coverage / git_sha-anchored) committed BEFORE any per-package Client class refactor lands.
- Per-package guard tests proving that a sentinel monkeypatched onto each module-level `_token` reaches the wire-level `Authorization` (iol/higyrus) / `X-Auth-Token` (matriz) header — and that `configure(base_url=...)` reaches the wire URL for the no-auth ambito case — with 7 passing + 1 matriz-async permanent skip.
- First per-package skeleton landed: `ambito_financiero_client.Client` (sync) + `AsyncClient` (async) with per-instance `_ClientState`, PEP 562 read-only `__getattr__` shim, carry-forward `configure()` semantics, redacted `__repr__`, pickle/deepcopy bans, and snapshot regeneration — all 4 ambito test suites + the cross-package public-surface guard + the Plan 06-02 fixture-reaches-production guard pass against the refactored client.
- Phase 6 CI matrix proven green end-to-end on Python 3.12 AND 3.13 (389 passed, 1 skipped on each) — mutation_gate audit PASSED unchanged.
- Instalación + configuración de `import-linter` v2.11 con 4 forbidden contracts declarativos + 4 `_core.py` placeholders + runtime cross-leak guard parametrizado — las dos CI gates de Phase 7 (REFAC-03) quedan operativas antes del primer refactor.
- Extracción mecánica del patrón `_core.py + transport shell` aplicado a `ambito_financiero_client` como canary del refactor Phase 7 — validó el patrón completo (RequestSpec + builders + parsers + raise_for_response moved + D-04 alias + B8 identity + 3-liner endpoint shells) con drop agregado de 31.2% LOC en client+aio y zero regresión.
- iol `_core.py` extracts OAuth password-grant + refresh-token auth-flow as pure builders/parsers (with CR-01 conditional rotation preserved structurally) plus 4 endpoint builder/parser pairs; transport shells (client.py + aio.py) collapse to 3-liner endpoint methods, D-04 alias preserves B8 identity.
- Wave-3 consolidation plan that gathers evidence the 5 Phase 7 ROADMAP success

criteria are satisfied across the full gate matrix and produces a single
`07-VALIDATION.md` with `nyquist_compliant: partial` (honest 4/5 PASS + 1
PARTIAL signal; the LOC-drop deviation in criterion #3 is documented in
Plans 07-03 and 07-05 SUMMARYs; operator decides at the Task 2 human-verify
checkpoint whether 'partial' is acceptable for phase close-out).

- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- 8 mocked regression tests (4 sync + 4 async) lockean los 4 paths del `_state.refresh_token` lifecycle en `iol-client` — CR-01 conditional rotation guard + D-IOL-10 refresh→password fallback + D-IOL-09 async double-checked locking quedan fijados sin tocar `_core.py` / `client.py` / `aio.py` / `_state.py`.
- Per-call `id_cuenta` regression test (mocked 2-cuentas) + driver probe with CSV override + cross-package `_state.account_id` cleanup + BUG-02 quick-triage closure (bucket a NO-FIX) + Phase 6 migration drift repair (shim hardening).
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:

---

## v1.0 Verification cycle (Shipped: 2026-06-10)

**Phases completed:** 5 phases, 18 plans, 27 tasks

**Key accomplishments:**

- Root conftest live/offline split (`--live` deselect-by-default), the importable non-published `verification/` package, and defense-in-depth `redact`/`safe_print` credential masking — all unit-proven including the empty-secret corruption guard.
- Two stdlib-only hard safety gates — a credential `require_env` emitting the verbatim `SKIPPED <pkg>: missing X, Y` line, and a `mutating_allowed` double-gate (`VERIFY_MUTATING=1` AND a live-resolved `remarkets` base URL) that fails safe even against a prod-URL bypass — each TDD-proven.
- AMB-01..AMB-06 verificados en vivo contra mercados.ambito.com; cero bugs detectados; baseline DRIFT-01 + Phase 2 findings file committeados al repo.
- OAuth2 `grant_type=refresh_token` with fallback to password grant implemented in IOL client `client.py` + `aio.py` dual surfaces, plus 4+4 pytest-httpx regression tests locking the four code paths (login capture, refresh success, refresh→password fallback, both fail).
- Fix dual sync+async: `_request` ahora pre-attachea el query string con `urlencode(... safe="/")` para preservar `/` literal en el wire, evitando que Higyrus IIS rechace el formato `dd/mm/yyyy` con HTTP 400.
- Live run contra remarkets PASS=17/FAIL=0/SKIPPED=9/FINDING=2; suite mockeada Phase 5 lockea 12 invariantes Verified-live + 11 MATZ-06 mock-only contract con 3 sentinels GET-quirk §6.3; cycle_closure × 4 pkgs PASS confirma DRIFT-02 helper promotion funcionando end-to-end
- DRIFT-02 baseline canónico creado: 4 findings files con `## Cycle Closure` + `CYCLE-REPORT.md` consolidando 14 findings / 18 schemas / 4 paquetes; `verify_cycle_closure × 4` reporta 3 PASS (ámbito/iol/higyrus sin CONFIRMED/FIXED) + 1 FAIL (matriz F-09 deferred) — la FAIL es la señal DRIFT-02 activa por diseño

---
