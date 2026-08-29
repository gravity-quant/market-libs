# 35-RETIRED-TRIPLES.md — the divergence triples the Null Object policy retires from the census

**Counting unit.** The distinct 4-tuple `(slug, model, field_path, kind)` taken from
`DivergenceHandler.seen` — literally the unit defined by `33-CENSUS.md` (`## Method`,
`33-CENSUS.md:13-17`). The unit is deliberately identical so that Phase 39 performs a **set
difference** against this file and never a translation.

**Disposition applied (NOBJ-02).** A `null` or absent value on a **non-`Optional`
model-typed or list-typed** field collapses to the empty instance / `[]` **and stops being
recorded**. The walker keeps returning exactly the value it returns today; what changes is
that the sink is no longer called for that case.

**What this disposition does NOT retire.** Wrong-typed values (a `str` where a model is
declared, a `dict` where a list is declared) keep emitting `type` / `non_dict` and stay
fatal under strict mode; `extra` wire keys; `missing` on scalar leaves (`str`/`int`/`float`/
`bool`), including scalar leaves nested inside list elements; the top-level `non_dict`
record for a `None`/204 body (D-03a); and the mapping axis of `dict[str, Any]` that lives
in `models.py` rather than in the walker (D-03c).

**Provenance.** Roster measured **2026-08-28** by introspecting `typing.get_type_hints`
over the 52 shipped model classes of the four packages that have them, against
`HEAD = 242b9f3` (`35-RESEARCH.md` §F-10, marked `[VERIFIED]`, and §Metadata). The roster is
still valid at `HEAD = 235506b`: plan 35-01 modified `higyrus_client/models.py` by adding two
**methods** (`empty()`, `__bool__`) and no field, so no annotation in the roster moved.

---

## Why every row's retired kind is `missing`

Read from the shipped walker, not inferred. A non-`Optional` **list**-typed field carrying
`None` takes `_decode.py:443-445`, whose kind comes from `_kind_of(None)` → `"missing"`
(`_decode.py:363-367`). A non-`Optional` **model**-typed field carrying `None` takes the
WR-02 branch at `_decode.py:482-484`, which emits the literal kind `"missing"` attributed to
the **outer** model at the outer field path. Both are the branches NOBJ-02 silences, so the
`kind` component of every retired 4-tuple below is `missing`.

**Kind caveat, and it is load-bearing for the subtraction.** `29-SIZING.md`'s corpus run
predates WR-02 (`36b79e2` "publish per-package divergence sizing floor" is **not** a
descendant of `2c31790` "WR-02 report an absent nested-model key as missing on the outer
model" — verified with `git merge-base --is-ancestor`). Before WR-02 the walker recursed
unconditionally and recorded these as `non_dict` **attributed to the nested class**. That is
why `29-SIZING.md:145-146` and `:149` label matriz's five model-link records `non_dict`
while today's shipped walker labels the same wire `missing` on the outer model. For those
five rows the floor's 4-tuple and today's 4-tuple differ in **two** components (`model` and
`kind`), so Phase 39 must match them on `(slug, field_path)` and read the `kind` from this
file, not from `29-SIZING.md`.

---

## Main table — the 35 retired fields

35 field rows, plus one explicit zero row for `iol-client`. Every cell in the two
provenance columns carries a citation, a reasoned `no`, or `UNKNOWN`; none is blank.

| slug | model | field_path | kind retired | in the 29-SIZING floor? | measured in 33-CENSUS? | note |
|---|---|---|---|---|---|---|
| higyrus-client | Administrador | `.agente` (`Agente`) | missing | no — reachable only under `Cuenta.administrador`, and the one `Cuenta` corpus file is an empty capture (29-SIZING.md:110) | SKIPPED — 33-CENSUS.md:68, vendor unreachable by DNS; no measurement, not zero | chain link two levels below the account detail response |
| higyrus-client | Administrador | `.operador` (`Operador`) | missing | no — same empty-capture reason (29-SIZING.md:110) | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | chain link |
| higyrus-client | Administrador | `.sucursal` (`Sucursal`) | missing | no — same empty-capture reason (29-SIZING.md:110) | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | chain link |
| higyrus-client | Cuenta | `.disposicionesGenerales` (`DisposicionesGenerales`) | missing | no — 29-SIZING.md:110, `get-listado-cuentas` is an empty capture (count 0), so `Cuenta` was never walked | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | model link |
| higyrus-client | Cuenta | `.domicilios` (`list[Domicilio]`) | missing | no — empty capture, 29-SIZING.md:110 | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | list link |
| higyrus-client | Cuenta | `.personasRelacionadas` (`list[PersonaRelacionada]`) | missing | no — empty capture, 29-SIZING.md:110 | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | list link |
| higyrus-client | Cuenta | `.mediosComunicacion` (`list[MedioComunicacion]`) | missing | no — empty capture, 29-SIZING.md:110 | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | list link |
| higyrus-client | Cuenta | `.cuentasBancarias` (`list[CuentaBancaria]`) | missing | no — empty capture, 29-SIZING.md:110 | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | list link |
| higyrus-client | Cuenta | `.administrador` (`Administrador`) | missing | no — empty capture, 29-SIZING.md:110 | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | the link that makes the three `Administrador` rows above reachable |
| higyrus-client | Movimiento | `.idMovimientos` (`list[int]`) | missing | **yes** — 29-SIZING.md:303 (one of `Movimiento`'s 9 `missing`) and 29-SIZING.md:111 (corpus row 4, `missing 9`) | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | **floor member.** 1 record and 1 distinct triple (single corpus file) |
| higyrus-client | Posicion | `.parking` (`list[Parking]`) | missing | **yes** — 29-SIZING.md:304 (`Posicion`: `disponibleAjustado`, `parking`) and 29-SIZING.md:113 (corpus row 6, `missing 2`) | SKIPPED — 33-CENSUS.md:68; no measurement, not zero | **floor member.** 1 record and 1 distinct triple. Its sibling `.disponibleAjustado` is a scalar and keeps emitting |
| iol-client | *(no model)* | *(no non-`Optional` model/list field exists today)* | *(nothing retired)* | no — 29-SIZING.md:114-117 records iol as **N/A, not zero**: the package had no `models.py` at sizing time | no — 33-CENSUS.md:69 measured iol live at 0 distinct triples, an inspected zero, not an absence | **Explicit zero with a reason.** `Cotizacion.puntas` and `Titulo.puntas` are declared `Optional` today (`iol_client/models.py:154`, `:242`), so they take the walker's `Union` early return at `_decode.py:431-435` and never emitted a link-level divergence at all. They become non-`Optional` links in **Phase 38**, which is when this package starts participating in this disposition |
| market-data-client | AddHolidaysResult | `.days` (`list[CalendarDay]`) | missing | no — 29-SIZING.md:139-142 (corpus rows 32-35) records the calendar-write acks as N/A untyped `dict`; the model arrived in Phase 31 | yes, measured and non-divergent — 33-CENSUS.md:151, the four calendar-write acks ran with the mutation gate OPEN and produced 0 triples | list link |
| market-data-client | CalendarConfig | `.warnings` (`list[Any]`) | missing | no — `CalendarConfig` was walked (29-SIZING.md:136-138) but `.warnings` is not among S-2's 12 divergent paths; 29-SIZING.md:255 names it as the one field that survives | yes, measured and non-divergent — 33-CENSUS.md:212-213 lists the 12 live paths and `.warnings` is not one of them | list link |
| market-data-client | CalendarConfigPreview | `.market_after` (`PreviewMarket`) | missing | no — the model did not exist at sizing time; the preview envelope was walked as `CalendarConfig` (29-SIZING.md:137-138) | no — the class was created by the 33-07 fix **after** the census run; `.market_after` appears in the census only as an `extra` on `CalendarConfig` (33-CENSUS.md:213) | model link on a class newer than both source artefacts |
| market-data-client | CalendarConfigPreview | `.warnings` (`list[Any]`) | missing | no — same reason: class newer than the corpus (29-SIZING.md:137-138) | no — same reason: class newer than the census run (33-CENSUS.md:204-218) | list link |
| market-data-client | FeedIngestor | `.market` (`FeedMarket`) | missing | no — 29-SIZING.md:119 (corpus row 12) is N/A, `get-health-feed` returned an unmodelled `dict` | yes, measured and non-divergent — `FeedIngestor` produced 3 live triples (33-CENSUS.md:159-161) and `.market` is not one of them | model link |
| market-data-client | FeedIngestor | `.pipeline` (`FeedPipeline`) | missing | no — 29-SIZING.md:119, corpus row 12 is N/A | yes, measured and non-divergent — not among `FeedIngestor`'s 3 live triples (33-CENSUS.md:159-161) | model link |
| market-data-client | Health | `.auth` (`HealthAuth`) | missing | no — 29-SIZING.md:118 (corpus row 11) is N/A, `get-health` returned an unmodelled `dict` | yes, measured and non-divergent — 33-CENSUS.md:149, `Health` produced **0** live triples | model link. This is the one that reddens the 11th test in the F-4b red set |
| market-data-client | HealthFeed | `.ingestor` (`FeedIngestor`) | missing | no — 29-SIZING.md:119, corpus row 12 is N/A | yes, measured and non-divergent — `HealthFeed`'s only live triple is `.symbols_never_delivered` (`extra`), 33-CENSUS.md:150,158 | model link |
| matriz-client | ExecutionReportFrame | `.orderReport` (`OrderReport`) | missing | no — the 43-file corpus holds no WebSocket frame capture; 29-SIZING.md:143-150 (rows 36-43) are all REST | SKIPPED — 33-CENSUS.md:71, base URL out of policy (D-MATZ-33); no measurement, not zero | WS frame link |
| matriz-client | Instrument | `.instrumentId` (`InstrumentId`) | missing | **yes** — 29-SIZING.md:145-146 (corpus rows 38 and 39, `non_dict 1` each) and S-3 at 29-SIZING.md:258-273 | SKIPPED — 33-CENSUS.md:220-229, S-3 is `COULD-NOT-DECIDE`; no measurement, not zero | **floor member, `S-3`** — "the highest-consequence finding in the set" (29-SIZING.md:272). **2 records / 1 distinct triple** (same triple in two corpus files). Kind label in the floor is the pre-WR-02 `non_dict`; see the kind caveat above |
| matriz-client | InstrumentDetail | `.instrumentId` (`InstrumentId`) | missing | no — `InstrumentDetail` was walked (29-SIZING.md:147-148, rows 40/41) but all 7 of its records are `extra` (S-4's undeclared wire keys); the link itself was present on the wire | SKIPPED — 33-CENSUS.md:231-238, S-4 is `COULD-NOT-DECIDE`; no measurement, not zero | model link |
| matriz-client | InstrumentDetail | `.segment` (`Segment`) | missing | no — same: not among the 7 `extra` records of rows 40/41 (29-SIZING.md:147-148) | SKIPPED — 33-CENSUS.md:71; no measurement, not zero | model link |
| matriz-client | InstrumentDetail | `.orderTypes` (`list[Literal[...]]`) | missing | no — same: not among the 7 `extra` records of rows 40/41 (29-SIZING.md:147-148) | SKIPPED — 33-CENSUS.md:71; no measurement, not zero | list link whose elements stay `str` under the D-09 RESPONSE-`Literal` lock |
| matriz-client | InstrumentDetail | `.timesInForce` (`list[Literal[...]]`) | missing | no — same: not among the 7 `extra` records of rows 40/41 (29-SIZING.md:147-148) | SKIPPED — 33-CENSUS.md:71; no measurement, not zero | list link, same D-09 note |
| matriz-client | MarketDataFrame | `.instrumentId` (`InstrumentId`) | missing | no — no WebSocket frame capture exists in the corpus (29-SIZING.md:143-150) | SKIPPED — 33-CENSUS.md:71; no measurement, not zero | WS frame link |
| matriz-client | MarketDataFrame | `.marketData` (`MarketDataSnapshot`) | missing | no — no WebSocket frame capture exists in the corpus (29-SIZING.md:143-150) | SKIPPED — 33-CENSUS.md:71; no measurement, not zero | WS frame link |
| matriz-client | MarketDataSnapshot | `.BI` (`list[MarketDataLevel]`) | missing | no — walked at 29-SIZING.md:149 (row 42) but the capture carried `BI: []`, an empty list rather than `null` (29-SIZING.md:293-295), so no record was emitted | SKIPPED — 33-CENSUS.md:240-255, S-5 is `COULD-NOT-DECIDE` twice over; no measurement, not zero | list link. The empty list is the market-closed shape, not a clean one |
| matriz-client | MarketDataSnapshot | `.OF` (`list[MarketDataLevel]`) | missing | no — same empty-list reason (29-SIZING.md:293-295) | SKIPPED — 33-CENSUS.md:240-255; no measurement, not zero | list link |
| matriz-client | MarketDataSnapshot | `.LA` (`MarketDataEntryValue`) | missing | **yes** — 29-SIZING.md:149 (row 42, `non_dict 4`) and S-5 at 29-SIZING.md:286-296 | SKIPPED — 33-CENSUS.md:240-255, undecidable without a run AND without an open-session window; no measurement, not zero | **floor member, `S-5`.** 1 record / 1 distinct triple. Pre-WR-02 kind label; see the kind caveat |
| matriz-client | MarketDataSnapshot | `.SE` (`MarketDataEntryValue`) | missing | **yes** — 29-SIZING.md:149 and S-5 at 29-SIZING.md:286-296 | SKIPPED — 33-CENSUS.md:240-255; no measurement, not zero | **floor member, `S-5`.** 1 record / 1 distinct triple |
| matriz-client | MarketDataSnapshot | `.OI` (`MarketDataEntryValue`) | missing | **yes** — 29-SIZING.md:149 and S-5 at 29-SIZING.md:286-296 | SKIPPED — 33-CENSUS.md:240-255; no measurement, not zero | **floor member, `S-5`.** 1 record / 1 distinct triple |
| matriz-client | MarketDataSnapshot | `.CL` (`MarketDataEntryValue`) | missing | **yes** — 29-SIZING.md:149 and S-5 at 29-SIZING.md:286-296 | SKIPPED — 33-CENSUS.md:240-255; no measurement, not zero | **floor member, `S-5`.** 1 record / 1 distinct triple |
| matriz-client | Order | `.instrumentId` (`InstrumentId`) | missing | no — 29-SIZING.md:336 records that every matriz order/position endpoint has no schema file at all, so no order response was ever walked | SKIPPED — 33-CENSUS.md:71; no measurement, not zero | model link on an order-entry response |
| matriz-client | OrderReport | `.instrumentId` (`InstrumentId`) | missing | no — same: no order-endpoint capture exists (29-SIZING.md:336) | SKIPPED — 33-CENSUS.md:71; no measurement, not zero | model link, reached from REST and from WS execution reports |

**Row accounting:** higyrus-client 11, iol-client 0 field rows (one explicit zero row),
market-data-client 8, matriz-client 16 — **35 field rows**, matching the D-17 count in
`35-CONTEXT.md:112-116`. `ambito-financiero-client` and `wallets-client` contribute no rows;
their absence is enumerated, not assumed, in the subtraction section below.

**No cell above is `UNKNOWN`.** Every one of the 70 provenance cells resolved against a
committed artefact. That is a result of the search, not a target it was written to hit: the
two candidates for `UNKNOWN` were `CalendarConfigPreview`'s two fields, and both resolved
positively to *"the class is newer than both source artefacts"*, which is a stronger and
more useful statement than not knowing.

---

## Unit warning — the two columns are not interchangeable

`29-SIZING.md`'s per-package floors are **sums of RECORDS across the 43 corpus files**: its
`Count` column is "the number of unique divergence records emitted by the shipped walker for
that file" (`29-SIZING.md:103-104`), unique *within* a file and summed *across* files.
`33-CENSUS.md`'s numbers are **DISTINCT 4-tuples** from `handler.seen`, where the same
`(model, field_path, kind)` appearing in two files counts once. `33-CENSUS.md:37-53`
established the conversion and the numbers do differ:

| Package | floor as records | equivalent in distinct triples | origin of the gap (33-CENSUS.md:48-53) |
|---|---:|---:|---|
| `higyrus-client` | ≥ 22 | 22 | three files, three disjoint models — no overlap |
| `matriz-client` | ≥ 24 | 14 | corpus rows 38/39 repeat 3 triples; rows 40/41 repeat 7 |
| `market-data-client` | ≥ 50 | 22 | rows 20-25 share `Symbol`'s triples; rows 30/31 share `CalendarConfig`'s 12 |

Subtracting a distinct-triple count from a records floor fabricates a shortfall that does
not exist — the false negative `33-CENSUS.md:55-59` prohibits, in the direction that reports
loss where there is none and buries the real question. **Every row of the subtraction table
below therefore names the column it counts against**, and where the two columns give
different answers (matriz: 6 records vs. 5 distinct triples) both are written out.

No number in this file is an estimate: each is either quoted from a cited line of
`35-RESEARCH.md` §F-10, `29-SIZING.md` or `33-CENSUS.md`, or derived by counting the rows of
the table above, which is itself a transcription of a `[VERIFIED]` introspection run.
