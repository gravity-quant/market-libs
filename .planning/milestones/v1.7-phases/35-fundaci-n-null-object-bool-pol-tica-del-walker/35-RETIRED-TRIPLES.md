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
`None` takes `_decode.py:448-452`, whose kind comes from `_kind_of(None)` → `"missing"`
(`_decode.py:369-373`). A non-`Optional` **model**-typed field carrying `None` takes the
WR-02 branch at `_decode.py:504-505`, which emits the literal kind `"missing"` attributed to
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
| iol-client | *(no model)* | *(no non-`Optional` model/list field exists today)* | *(nothing retired)* | no — 29-SIZING.md:114-117 records iol as **N/A, not zero**: the package had no `models.py` at sizing time | no — 33-CENSUS.md:69 measured iol live at 0 distinct triples, an inspected zero, not an absence | **Explicit zero with a reason.** `Cotizacion.puntas` and `Titulo.puntas` were declared `Optional` at `242b9f3` (today `iol_client/models.py:235` and `iol_client/models.py:334`), so they took the walker's `Union` early return at `_decode.py:440-446` and never emitted a link-level divergence at all. They became non-`Optional` links in **Phase 38**, which is when this package starts participating in this disposition — see `## Phase 38 addendum` at the end of this file |
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

---

## Expected subtraction per package

The middle term of Phase 39's arithmetic. **"Triples retired" is the intersection of the
main table with a measured census — not the row count.** A listed field only retires a
triple if that triple was actually being emitted; 28 of the 35 rows intersect no ratified
floor at all.

| package | floor (records column) | floor (distinct-triples column) | triples retired by NOBJ-02 | expected post-35 baseline | column this row counts against |
|---|---|---|---|---|---|
| `higyrus-client` | ≥ 22 | 22 | **2** in both columns | **≥ 20** records / **20** distinct triples | **both, and they agree** — three files, three disjoint models, no cross-file overlap (33-CENSUS.md:50) |
| `iol-client` | N/A — not zero | N/A — not zero | **0** | N/A — unchanged, and N/A is not a baseline of zero | **neither** — there is no floor to subtract from (29-SIZING.md:166) |
| `market-data-client` | ≥ 50 | 22 | **0** in both columns | **≥ 50** records / **22** distinct triples, both unchanged; the live census of **24** (33-CENSUS.md:70) is likewise unchanged | **both, and the answer is 0 in each** |
| `matriz-client` | ≥ 24 | 14 | **6** records / **5** distinct triples | **18** records / **9** distinct triples | **both, and they DIFFER** — S-3's link is one triple recorded in two corpus files (29-SIZING.md:145-146), so it subtracts 2 from the records column and 1 from the distinct column; S-5's four each subtract 1 from both |
| `ambito-financiero-client` | N/A — no models to walk | N/A | **0 by enumeration** | N/A | **neither** — the package declares zero model classes |
| `wallets-client` | N/A — no models to walk | N/A | **0 by enumeration** | N/A | **neither** — the package declares zero model classes and has no walker |

**`iol-client` — the zero is a fact about `Optional`, not a fact about quality.** iol retires
nothing in this phase because its two order-book links, `Cotizacion.puntas`
(`iol_client/models.py:235`) and `Titulo.puntas` (`iol_client/models.py:334`), were declared
`Optional` at `242b9f3`. An `Optional` field takes the walker's `Union` early return
(`_decode.py:440-446`), which returns `None` and never calls the sink, so those fields were
not emitting a link-level divergence for NOBJ-02 to stop emitting. They become non-`Optional`
links in **Phase 38** (ROADMAP.md:114), and that is the phase in which this package starts
participating in this disposition and its zero stops being zero. Written as a bare `0`, or
omitted from the table, this row would read as "iol was already clean" — a different claim,
and a false one: iol had no `models.py` at sizing time at all (29-SIZING.md:166,
"**Not applicable, not zero**").

**Phase 38 has since landed, and the last clause above did not hold: the zero stayed zero.**
The two links are non-`Optional` at HEAD, so they now take the NOBJ-02 collapse arms instead
of the `Union` early return — but they emitted nothing before and they emit nothing now, so
**0** triples were retired, in both columns. The roster grew by two field rows; the
arithmetic did not move. Measured, with the reason spelled out, in `## Phase 38 addendum` at
the end of this file — read it before using iol's row in any subtraction.

**`ambito-financiero-client` and `wallets-client` — absent by enumeration, not by
cleanliness.** Neither package declares a single response model, so neither can contribute a
row: there is no non-`Optional` model-typed or list-typed field in either. The evidence is
the two deliberately-empty `models.py` module docstrings (D-05, `35-CONTEXT.md:43-47`).
ámbito's states that its single endpoint parses a scraped Argentine-format decimal straight
into a `float`, that the package "declares **no response models today** (Phase 31, D-11)",
and that the absence of a `SafeModel` base is "deliberately absent, and not an oversight".
wallets' states that the package is still a stub with no verifiable endpoints and that it
carries the Phase 29 decoder exemption (`29-WALLETS-EXEMPTION.md`) — it has no `_decode.py`
to import a walker from, so a base class copied there for cosmetic uniformity would raise
`ImportError` on import. `33-CENSUS.md:67` records ámbito's live census as "**Cero afirmado,
no inferido**". A future reader must not read either absence as a gap in this ledger.

---

## How Phase 39 should use this

**Mechanics.** Phase 39's live census is a set of distinct 4-tuples
`(slug, model, field_path, kind)` taken from `DivergenceHandler.seen`, the same unit as
`33-CENSUS.md` and the same unit as this file. The expected relationship is
`census_39 ≈ census_33 − retired_here − fixed_in_36_37_38`, and this ledger supplies the
middle term: **higyrus 2, iol 0, market-data 0, matriz 5** against the distinct-triples
column (matriz 6 against the records column). Compute the term as a set intersection of the
main table with the census being contrasted, matching on `(slug, field_path)` and reading
`kind` from this file rather than from `29-SIZING.md` — see the kind caveat above.

**The failure mode this exists to prevent.** If the middle term is not subtracted
explicitly, every triple the policy stopped recording is silently credited to quality work.
The census number falls, nobody can say why, and the milestone reports a clean bill of
health it did not earn — which is precisely the false clean v1.6 was built to eliminate
(ROADMAP.md:131, Phase 39 criterio 4). The drop must be split into "N disappeared because
the policy stopped recording them" and "M disappeared because we fixed them", and the split
is only auditable if N is written down before the run rather than reconstructed after it.

**What a NON-balancing subtraction means.** It is a finding to investigate, not a rounding
error, and it must be written up rather than absorbed. The two most likely causes, in the
order to check them: **(b) a unit-column mix-up** — a distinct-triple count contrasted
against a records floor, or matriz's 6-vs-5 read off the wrong column — check this first,
because it costs nothing and is the single most common way these two artefacts have been
misread; and **(a) a field reachable on the live wire in a shape the static roster did not
anticipate**, which is a real finding about the models and belongs in the phase's findings
file with a named destination.

---

## Method and limits

**Method.** The roster is an introspection of `typing.get_type_hints` over the 52 shipped
model classes of the four packages that have them, selecting every field whose annotation is
a model type or a `list[...]` and is **not** `Optional`. It is measurement, not inference,
and over the declared-annotation axis it is exhaustive at `242b9f3`: no non-`Optional`
model/list annotation shipped at that commit is missing from the table.

**The blind spot.** Being an introspection of annotations, it is blind to everything that is
not a declared annotation. Value-level divergences — out-of-set enumeration values under the
D-09 RESPONSE-`Literal` lock, `NaN`/`Infinity`, range and format violations, cross-field
inconsistency — are outside it by construction (29-SIZING.md:311-337 catalogues the same
blind spot for the floor it produced).

**Direction of the error, and why it is the safe one.** The blindness is one-directional and
it does not run through the retired set: value-level divergences are never retired by
NOBJ-02, so no retirement can hide inside the blind spot. What the ledger under-describes is
the **census population** — it can speak about shape divergences and about nothing else, so
it always accounts for less of the census than the census contains. On the retired set
itself the file errs the other way, by **over-listing candidates**: it names 35 fields of
which only 7 intersect any ratified floor, and a field that never diverged live retires
nothing. That is the safe direction for this artefact, because over-listing can only make
Phase 39 attribute *more* of a drop to the policy and *less* to real fixes — an understated
credit for quality work, which is visible in the arithmetic and correctable. The opposite
error, under-listing, would leave policy-driven disappearances unaccounted and let them be
read as fixes: it would manufacture the false clean instead of exposing it.

**Two limits with named destinations.** First, this file scopes to the disposition of
**Phase 35** against the classes shipped at `242b9f3`. Phases 36, 37 and 38 introduce new
non-`Optional` links (market-data's `market_data` Null Object, matriz's typed report fields,
iol's two order-book links); the triples those retire are **not** in this ledger and belong
to their own phases' accounting. Second, higyrus and matriz have no measured live census to
intersect with — `LIVE-HIGY-33` (DNS) and `LIVE-MATZ-33` (the remarkets-only policy assert,
which is not to be worked around) — so their retired counts above are intersections with the
`29-SIZING.md` floor only, and Phase 39 must record them `SKIPPED` with measured cause and
named destination rather than as a zero that reads as clean.

---

## Phase 38 addendum

**Everything above scopes to the disposition of Phase 35 against the classes shipped at
`242b9f3`, and this addendum changes none of it** — not the 35-row main table, not the "Row
accounting" equality with `35-CONTEXT.md:112-116`, and not the subtraction table. It is the
accounting the "Two limits with named destinations" paragraph above says Phase 38 owes its
own phase: the numbers, measured at Phase 38's HEAD, for the two iol links that the main
table's explicit-zero row names as future participants.

### 1. Field rows added to the NOBJ-02 disposition: 2

Same seven-column shape as the main table, so Phase 39 can union them without translating.
They are **additions to the roster**, not replacements for the iol explicit-zero row, which
stays exactly where it is (see §2 for why the two statements are consistent).

| slug | model | field_path | kind retired | in the 29-SIZING floor? | measured in 33-CENSUS? | note |
|---|---|---|---|---|---|---|
| iol-client | Cotizacion | `.puntas` (`list[Punta]`) | missing | no — 29-SIZING.md:114-117 records iol as **N/A, not zero**: the package had no `models.py` at sizing time | no — 33-CENSUS.md:69 measured iol live at 0 distinct triples, an inspected zero, not an absence | list link. Non-`Optional` since Phase 38 (`iol_client/models.py:235`); its collapse arm is the list branch at `_decode.py:448-452` |
| iol-client | Titulo | `.puntas` (`Punta`) | missing | no — same reason: N/A, not zero (29-SIZING.md:114-117) | no — same inspected zero (33-CENSUS.md:69) | model link. Non-`Optional` since Phase 38 (`iol_client/models.py:334`); its collapse arm is the WR-02 branch at `_decode.py:504-505` |

### 2. Triples retired: 0 — in the records column and in the distinct-triples column alike

**And the zero is not a claim that iol was already clean.** A field retires a triple only if
that triple was actually being emitted. Under the **pre**-Phase-38 `Optional` declaration
these two fields took the walker's `Union` early return (`_decode.py:440-446`), which returns
`None` without ever calling the sink — nothing was emitted for NOBJ-02 to stop emitting.
Under the **post**-Phase-38 non-`Optional` declaration they take the NOBJ-02 collapse arms
instead (`_decode.py:448-452` for the list, `_decode.py:504-505` for the model), which
construct `[]` / `Punta.empty()` with `SILENT_SINK` — and still emit nothing. Two different
branches, the same observable output: zero records, before and after.

**The invariance is the finding.** It is a measured result about which branch runs, not an
absence of measurement, and not a verdict on iol's data quality. The misreading this
paragraph exists to block is the one the main table's explicit-zero row already warns about:
a bare `0` read as "iol was clean". iol's floor is `N/A — not zero` (29-SIZING.md:166,
"**Not applicable, not zero**") and its live census zero (33-CENSUS.md:69) was inspected, not
assumed. Neither becomes a baseline of zero because of this addendum.

### 3. Phase 39's middle term is unchanged

**higyrus 2, iol 0, market-data 0, matriz 5** against the distinct-triples column, and
**matriz 6** against the records column — identical to the values the "Mechanics" paragraph
of `## How Phase 39 should use this` supplies. Compute the term exactly as that paragraph
prescribes (set intersection on `(slug, field_path)`, `kind` read from this file and not from
`29-SIZING.md`); nothing about the formula or its inputs moved. The two rows in §1 join the
intersection's **left-hand set** and intersect no measured census, so they contribute 0.

Phase 38 changed the **roster**, not the **arithmetic**. A subtraction that comes out
different because of these two rows has a bug in it, not a finding.

### 4. Where the rest of Phase 38's audit lives

The full higyrus / ámbito / wallets annotation audit — the one that carries Phase 38's own
per-package numbers rather than its contribution to this ledger — is the phase-local artefact
`.planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md`. This
addendum is deliberately the narrow half: only what Phase 39's subtraction needs. The pointer
is recorded in both places, asymmetrically — `38-CENSUS.md` cross-references this addendum for
the retired-triples accounting rather than duplicating it, and this addendum points there for
everything else.

---

## Phase 39 addendum

**Everything above this heading is unchanged.** No number, no row and no paragraph of the main
table, the "Row accounting" equality, the subtraction table or the Phase 38 addendum has been
rewritten. This section only **adds**: it is the first time the predictions this file makes were
put in front of live wire data and given the chance to be wrong.

**What was measured, against what, in what unit.** The live run of 2026-08-30
(`2026-08-29 23:34 ART`, ARG market closed) drove four packages against their real APIs. The unit
is the same distinct 4-tuple `(slug, model, field_path, kind)` from `DivergenceHandler.seen` that
this file has used throughout — read from `.planning/verification/run-evidence/<slug>.json`, one
envelope per slug, cross-checked against a `SHAPE`-title parse of the four findings ledgers. The
full arithmetic, both seams and every zero's cause lives in
`.planning/phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-CENSUS.md`; this addendum
carries only the retired-triples half, mirroring the Phase 38 addendum's narrow shape.

### 1. Result per package

| package | triples this ledger predicted retired | confirmed absent live | reappeared | live census (distinct triples) | verdict |
|---|---:|---:|---:|---:|---|
| `matriz-client` | **5** distinct / **6** records | **5** / **6** | **0** | **7** | **Prediction confirmed against real wire data — the first time it could be falsified** |
| `higyrus-client` | **2** in both columns | *not testable* | *not testable* | **UNMEASURED** — 0 probes | `SKIPPED`, vendor host unreachable by DNS, re-probed this session. Destination `LIVE-HIGY-33` |
| `iol-client` | **0** in both columns | **0**, and the zero was inspected | **0** | **0** (15 probes) | Phase 38 addendum §2's invariance held live |
| `market-data-client` | **0** in both columns | *out of scope* | *out of scope* | *not run* | Out of Phase 39's scope by D-07; audited in Phase 36 |
| `ambito-financiero-client` | **0 by enumeration** | **0** | **0** | **0** (7 probes) | Zero classes declared; measured, not assumed |
| `wallets-client` | **0 by enumeration** | *no run* | *no run* | *n/a* | Stub; audited in `38-CENSUS.md` |

**Zero triples reappeared, in any package that ran.** None of the five matriz fields this ledger
lists as retired — `Instrument.instrumentId` and `MarketDataSnapshot.LA` / `.SE` / `.OI` / `.CL` —
appears among the seven triples the live run recorded. The seven recorded triples are exactly
`InstrumentDetail`'s seven `extra` wire keys, which this ledger never claimed to retire.

### 2. The subtraction balanced exactly, in both columns

Using this file's middle term for matriz and no other input:

```
14  floor, distinct-triples column (29-SIZING.md rows 38-42, decomposed row by row)
− 5  retired by NOBJ-02 (this file, ## Expected subtraction per package)
− 2  closed by a real in-cycle fix in Phase 39 (F-43 / F-44)
= 7  measured live — and 7 is what handler.seen holds

24  floor, records column
− 6  retired by NOBJ-02 (this file, matriz's records column)
− 4  real fix (the same two triples, each recorded in two corpus files)
= 14 expected records ≡ the 7 InstrumentDetail extras × corpus rows 40/41
```

Both columns close with no residue. Per this file's own instruction, the unit-column check was run
**first** and found nothing: matriz's `6 records / 5 distinct` was read off the correct column, and
the five rows whose floor label is the pre-WR-02 `non_dict` were matched on `(slug, field_path)`
with `kind` read from here rather than from `29-SIZING.md`.

### 3. The prediction held — and the silence it predicted was hiding a real defect

This is the finding of the addendum, and it is not a comfortable one.

This ledger predicted that `Instrument.instrumentId` would stop being recorded, because a `null` or
absent value on that non-`Optional` model-typed link collapses to `InstrumentId.empty()` and the
sink is no longer called. **That is exactly what the live run observed** — and the wire shape that
produced the silence turned out to be a client defect of total data loss:
`/rest/instruments/byCFICode` and `/rest/instruments/bySegment` return the identifier **flat**
(`{marketId, symbol}`), not nested under `instrumentId` as `/rest/instruments/all` does. On that
shape the policy collapsed the missing link silently while the only data the wire carried was
discarded as `extra`: **386 and 9160 `Instrument` objects with `marketId=None, symbol=None,
cficode=None`** — 100% of the payload of two public methods, lost without a divergence, on all four
surfaces. Confirmed in **both** venues of the allowlist (remarkets baseline 2026-06-10, bbsa capture
2026-08-30), so it is a client defect and not venue drift.

The correct reading, and the one this ledger's `## What a NON-balancing subtraction means` section
argues for: **the retirement is not the defect, and the defect is not a failure of the retirement.**
The policy did what NOBJ-02 says it does. What the episode demonstrates is that a retired triple
buys the milestone silence, and silence is only safe while something else is looking — here it was
the live run, and nothing else could have been. No mocked suite found it in three phases.

Fixed in-cycle in Phase 39 plan `39-07` (`_core._normalize_instrument_element`, the single site both
shells traverse under REFAC-03; commits `5674da1` RED / `9453acc` GREEN, 13 regressions under
`packages/matriz-client/tests/`). The two triples it closed — `Instrument.marketId` and
`Instrument.symbol`, both `extra` — belong in the **real-fix** column, never in the policy column,
and `39-CENSUS.md` puts them there.

### 4. matriz's first live census, with its venue caveat

**Phase 39 produced the first live census of `matriz-client` in the project's history.** Every
earlier attempt recorded `SKIPPED`: the Phase 33 run aborted on the D-MATZ-33 remarkets-only
hostname assert before its first probe, so `33-CENSUS.md` carries no matriz number at all and
S-3/S-4/S-5 were left `COULD-NOT-DECIDE`. The block was cleared by widening the allowlist to the
bbsa hostname (Phase 39 D-02) — **the policy assert was widened deliberately and by name, never
worked around.**

Two consequences this ledger must carry forward rather than let a future reader infer:

- **The Phase 33 subtraction term for matriz is `UNMEASURED` and always will be.** There is no
  Phase 33 matriz census to difference against; the counterfactual is not derivable from any
  committed artefact. The only available contrast is the ratified floor.
- **The ratified floor was measured against a different venue.** `29-SIZING.md`'s matriz rows come
  from a **remarkets** corpus captured 2026-06-10; this run executed against **bbsa**. Same vendor,
  different venue. The comparison is made because it is the only one that exists, and it is
  declared here rather than performed silently. The one measured counterweight: the single defect
  the run found was confirmed in both venues, so at least that finding is not venue drift. The
  seven surviving `InstrumentDetail` `extra` triples carry no such double confirmation.

### 5. The account Phase 38 left open for Phase 39 — named and closed

**The open account is `## Phase 38 addendum` §3, "Phase 39's middle term is unchanged".** That
section asserted, without the ability to test it, that the middle term this ledger supplies —
**higyrus 2, iol 0, market-data 0, matriz 5 distinct / matriz 6 records** — was unmoved by Phase
38's two new roster rows, and warned that *"a subtraction that comes out different because of these
two rows has a bug in it, not a finding."*

**Closed, and the assertion held.** Phase 39 ran the subtraction with exactly those values as
inputs and it balanced to the measured live count with no residue (§2 above). Phase 38's two new
rows — `Cotizacion.puntas` and `Titulo.puntas` — contributed **0**, as §3 predicted: iol ran live
with 15 probes and `DIVERGENCES=0`, so the two rows joined the intersection's left-hand set and
intersected no emitted triple. The invariance claimed in §2 of that addendum is now a measured
result against live wire, not a branch-level argument.

**No number in any previous section of this file was found incorrect by this run.** Had one been,
it would be corrected here with its correction stated, not edited in place.

### 6. The debt this addendum does NOT pay, with its destination

**Phases 36 and 37 still owe their own retirement accounting.** The `## Two limits with named
destinations` section above scopes this ledger to Phase 35's disposition against the classes shipped
at `242b9f3` and routes the new non-`Optional` links of Phases 36, 37 and 38 to "their own phases'
accounting". Phase 38 paid with the addendum above. **36 and 37 have not**, and a directory listing
confirms no `36-RETIRED-*.md` or `37-RETIRED-*.md` exists.

What Phase 39 could derive, it derived; what it could not, it marked `UNMEASURED` rather than
folding into "fixed":

- **Phase 37 (`matriz`)** — the three new mapping-typed links (`InstrumentDetail.tickPriceRanges`,
  `DetailedPosition.report`, `AccountReport.detailedAccountReports`) were all exercised live and
  retired **0** triples in this run. Their **pre-Phase-37 state is `UNMEASURED`**, because matriz has
  no Phase 33 census to compare against.
- **Phase 36 (`market-data`)** — entirely **`UNMEASURED`**. The package is out of Phase 39's scope by
  D-07 and did not run; there is no live census to intersect with its roster.

**Destination: `NOBJ-RETIRE-3637`**, to be settled with an addendum to this file in the same shape
as the Phase 38 one, at the v1.7 milestone close. It is a bookkeeping label following the
`LIVE-HIGY-33` / `LIVE-MATZ-33` / `LIVE-NOBJ-01` / `LIVE-POS-39` convention already in use — not a
new scope or security decision. **This ledger therefore carries no undischarged debt into Phase 40
that is not written down here by name.**

*Measured at HEAD `89dabec`, 2026-08-30. Source of every number: the four run-evidence envelopes,
`39-CENSUS.md`, and `39-07-SUMMARY.md`.*
