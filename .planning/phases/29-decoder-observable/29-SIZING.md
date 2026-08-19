# Phase 29 — Divergence sizing floor (D-06 / D-08)

**Status:** measurement complete — **awaiting operator ratification**
**Run date:** 2026-08-19
**Source tree:** branch `milestone/v1.5-mutations` @ `32cc4a3` + Phase 29 Plans 01-09
**Corpus:** `.planning/verification/schemas/` — 43 type-only JSON schema files
**Engine:** the shipped `_decode.py` walker in observable mode, reached through each
package's own `_core.parse_*`
**Companion artifacts:** `29-AGGREGATION-CONTRACT.md` (record vocabulary, dedupe key),
`29-SEMANTICS-MATRIX.md` (per-package policy), `29-DLOCK-RESPONSE-LITERAL.md` (D-09).

This number is a **floor**, never an estimate. Every per-package figure below is written
as a lower bound with the `≥` form. Two packages have no `models.py` and are reported
**N/A with a written reason** — never as zero, because a zero reads as clean and a false
clean is the exact failure mode this milestone exists to eliminate.

---

## Method

### The corpus the roadmap names is the wrong one

ROADMAP criterion 5 points at `verification/snapshots/`. That directory holds four
public-surface `.txt` files with **no payloads in them** — there is nothing there to
walk. `.planning/verification/captures/` is empty. Per D-08 the run is re-based onto
`.planning/verification/schemas/`, the 43 type-only JSON files the live drivers write
(ambito 1 / higyrus 5 / iol 4 / matriz 8 / market-data 25). Each file carries
`endpoint`, `client_function`, `captured_at`, `base_url`, `sample_params` and a
type-only `schema` object produced by `verification/schema.py::schema_of`.

A type-only corpus supports a **keyset-and-type** floor and nothing more. That is
exactly what a floor should be, and it is why the blind-spot section below is not
optional.

### The five steps

1. **Map all 43 files.** For each file resolve the owning package, the response parser
   that handles that endpoint, and the model class the parser produces. `client_function`
   in the corpus is often a *probe* name rather than an API function name, so automatic
   resolution succeeds for well under half the corpus. Every probe-named row below was
   resolved by reading the driver that wrote the file (`main_market_data.py`,
   `main_matriz.py`, `main_higyrus.py`, `main_iol.py`, `main_ambito_financiero.py`) and
   following the client method it called through to `_core.parse_*`. Where no model
   exists the row is marked **N/A with a specific reason**. All 43 files have a row; the
   row count is asserted by the script (`assert len(files) == 43`, plus a two-way set
   difference between corpus keys and mapping keys), not eyeballed.
2. **Synthesize a witness payload** by inverting `schema_of`: a mapping becomes a mapping
   of the same keys with synthesized values; a one-element sequence becomes a one-element
   sequence of a synthesized element; an empty sequence stays empty; a scalar type name
   becomes that type's zero value (`"str"`→`""`, `"int"`→`0`, `"float"`→`0.0`,
   `"bool"`→`False`, `"NoneType"`→`None`).
3. **Route every witness through the owning package's own parser.** The witness is wrapped
   in `httpx.Response(200, json=witness, request=...)` and handed to `_core.parse_*`. The
   script **never re-derives which payload key holds the rows** — that re-derivation is how
   a previously shipped envelope-unwrap bug happened in this repo, and the package's own
   parser already encodes the live-verified answer. Routing through the parser also makes
   the number directly comparable with the live census Phase 33 runs (D-06).
4. **Decode in observable mode with a counting handler** attached to the package logger
   (`higyrus_client` / `matriz_client` / `market_data_client`), level `DEBUG` so `INFO`-level
   `extra` records are not dropped. A fresh `open_request_scope()` is bound per file, so the
   dedupe set never leaks across files. The count is of **unique** divergence records: the
   walker already collapses repeats within a scope on the `(model, field_path, kind)` triple
   (aggregation contract lock 5).
5. **Aggregate** per package and per file, split by divergence kind.

### One deviation from the plan's stated method, and why

The plan assumed the corpus uniformly stores the **raw wire envelope**. That holds for
market-data — `main_market_data.py::_write_schema_snapshot` is fed the raw response body,
so `get-instruments.json` really is `{catalogue, count, items[], limit, offset, total}`.
It does **not** hold for matriz: `main_matriz.py` stores the **already-unwrapped**
collection, because each probe returns `raw["segments"]` / `raw["instruments"]` /
`raw["marketData"]` rather than `raw` (verified at `main_matriz.py:602`, `:2229`,
`:1479`). Handing a matriz witness straight to `parse_get_*_response` therefore raised
`PrimaryAPIError: missing envelope key` on all eight files and produced a floor of zero —
a silent undercount of exactly the kind this report exists to prevent.

Resolution: the matriz witness is put **back inside** its envelope before the real parser
sees it, under the key **read verbatim out of the owning parser's own source** with a
regex over `inspect.getsource(parser)` matching `unwrap(data, "<key>", path)`. The key is
never guessed and never inferred from the payload. The package still owns the answer to
"which key holds the rows"; the script only reads that answer out of the package instead
of receiving it pre-applied. Every matriz witness still routes through the real parser,
so the prohibition and the comparability guarantee both hold. The re-envelope key used for
each matriz file is recorded in the mapping table.

### Reproducing the run

```
uv run python <scratch>/sizing.py
```

The script is throwaway and is deliberately **not committed** — the deliverable is this
report. Its complete method is specified in the five steps above plus the mapping table
below, which is the only part that required reading the drivers. The witness synthesizer
and the counting handler are ten lines each; the `SUMMARY` records the exact invocation
and the scratch path used for this run.

---

## Mapping table — all 43 corpus files

`Count` is the number of unique divergence records emitted by the shipped walker for that
file. `—` means the row is N/A (no model to walk).

| # | Corpus file | Package | Parser | Model | Count | Kinds | Note / N/A reason |
| - | ----------- | ------- | ------ | ----- | ----: | ----- | ----------------- |
| 1 | `ambito-financiero-client/get-dollar-banco-nacion` | ambito-financiero | `parse_get_dollar_banco_nacion_response` | **N/A** | — | — | No `models.py` in the package; the parser returns a bare `float`, so there is no declared keyset to compare a wire keyset against. |
| 2 | `higyrus-client/get-health` | higyrus | `parse_get_health_response` | **N/A** | — | — | Parser returns `dict[str, Any]`; the health payload is unmodelled until Phase 31 TYP-02. |
| 3 | `higyrus-client/get-listado-cuentas` | higyrus | `parse_get_listado_cuentas_response` | `Cuenta` | 0 | — | Empty capture (`schema: []`) — the live wire returned no rows, so there is nothing to walk. Not evidence of a clean model. |
| 4 | `higyrus-client/get-movimientos` | higyrus | `parse_get_movimientos_response` | `Movimiento` | 9 | missing 9 | |
| 5 | `higyrus-client/get-posicion-valuada` | higyrus | `parse_get_posicion_valuada_response` | `PosicionValuada` | 11 | missing 11 | |
| 6 | `higyrus-client/get-posiciones` | higyrus | `parse_get_posiciones_response` | `Posicion` | 2 | missing 2 | |
| 7 | `iol-client/get-quote` | iol | `parse_get_quote_response` | **N/A** | — | — | No `models.py` in `iol-client`; the parser returns `dict[str, Any]`. Typed surface arrives in Phase 30 (TYP-01). |
| 8 | `iol-client/get-historical-quotes` | iol | `parse_get_historical_quotes_response` | **N/A** | — | — | No `models.py` in `iol-client`; returns `list[dict[str, Any]]` (Phase 30 TYP-01). |
| 9 | `iol-client/get-instruments` | iol | `parse_get_instruments_response` | **N/A** | — | — | No `models.py` in `iol-client`; returns `Any` (Phase 30 TYP-01). |
| 10 | `iol-client/get-instruments-by-type` | iol | `parse_get_instruments_by_type_response` | **N/A** | — | — | No `models.py` in `iol-client`; returns `list[dict[str, Any]]` (Phase 30 TYP-01). |
| 11 | `market-data-client/get-health` | market-data | `parse_health_response` | **N/A** | — | — | Parser returns `dict[str, Any]`; the health payload is unmodelled (TYP-02). |
| 12 | `market-data-client/get-health-feed` | market-data | `parse_health_response` | **N/A** | — | — | Same parser, same unmodelled `dict[str, Any]` contract (TYP-02). |
| 13 | `market-data-client/get-market-data` | market-data | `parse_market_data_response` | `MarketDataSnapshot` | 0 | — | Envelope `{count, items[], limit, offset, total}` unwrapped by the parser via `items`. Zero divergences on a fully-populated capture. |
| 14 | `market-data-client/get-latest` | market-data | `parse_latest_response` | `MarketDataSnapshot` | 4 | missing 4 | Bare-list no-data shape (`note` row). |
| 15 | `market-data-client/get-instruments` | market-data | `parse_instruments_response` | `Instrument` | 1 | non_dict 1 | **Structural — see finding S-1.** The parser iterates the body directly; the recorded body is an envelope. |
| 16 | `market-data-client/get-segments` | market-data | `parse_segments_response` | `Segment` | 1 | non_dict 1 | **Structural — see finding S-1.** Same shape, envelope key `segments`. |
| 17 | `market-data-client/get-symbols` | market-data | `parse_symbols_response` | `Symbol` | 0 | — | Bare-list read shape; parser's D-11 discrimination handles it. |
| 18 | `market-data-client/get-symbols-probe-prefix-sync` | market-data | `parse_symbols_response` | `Symbol` | 0 | — | Probe name. Driver `main_market_data.py:1469` → `client.get_symbols(prefix=_PROBE_PREFIX)`. |
| 19 | `market-data-client/get-symbols-probe-prefix-async` | market-data | `parse_symbols_response` | `Symbol` | 0 | — | Probe name. Driver `main_market_data.py:1781` → `aclient.get_symbols(prefix=_PROBE_PREFIX)`. |
| 20 | `market-data-client/create-symbol-sync-response` | market-data | `parse_symbols_response` | `Symbol` | 4 | extra 2 + missing 2 | Probe name. Driver `:1412` → `client.create_symbol(new_symbol)`. Flat write-ack row. |
| 21 | `market-data-client/create-symbol-async-response` | market-data | `parse_symbols_response` | `Symbol` | 4 | extra 2 + missing 2 | Probe name. Driver `:1732` → `aclient.create_symbol(new_symbol)`. |
| 22 | `market-data-client/create-symbols-batch-sync-response` | market-data | `parse_symbols_response` | `Symbol` | 3 | extra 1 + missing 2 | Probe name. Driver `:1566` → `client.create_symbols(new_symbols)`. Batch envelope unwrapped via `items`. |
| 23 | `market-data-client/create-symbols-batch-async-response` | market-data | `parse_symbols_response` | `Symbol` | 3 | extra 1 + missing 2 | Probe name. Driver `:1869` → `aclient.create_symbols(new_symbols)`. |
| 24 | `market-data-client/update-symbol-sync-response` | market-data | `parse_symbols_response` | `Symbol` | 3 | extra 1 + missing 2 | Probe name. Driver `:1668` → `client.update_symbol(row_id, patch)`. |
| 25 | `market-data-client/update-symbol-async-response` | market-data | `parse_symbols_response` | `Symbol` | 3 | extra 1 + missing 2 | Probe name. Driver `:1965` → `aclient.update_symbol(row_id, patch)`. |
| 26 | `market-data-client/get-calendar` | market-data | `parse_calendar_response` | `CalendarDay` | 0 | — | Envelope `{config, coverage, days[], market}` unwrapped via `days` (D-12). |
| 27 | `market-data-client/get-calendar-year-2099-sync` | market-data | `parse_calendar_response` | `CalendarDay` | 0 | — | Probe name. Driver `:2421` → `client.get_calendar(year=_HOLIDAY_YEAR)`. |
| 28 | `market-data-client/get-calendar-year-2099-async` | market-data | `parse_calendar_response` | `CalendarDay` | 0 | — | Probe name. Driver `:2609` → `aclient.get_calendar(year=_HOLIDAY_YEAR)`. |
| 29 | `market-data-client/get-calendar-config` | market-data | `parse_calendar_config_response` | `CalendarConfig` | 0 | — | The single non-collection reference parser (D-07). |
| 30 | `market-data-client/preview-calendar-config-sync-response` | market-data | `parse_calendar_config_response` | `CalendarConfig` | 12 | extra 3 + missing 9 | **Structural — see finding S-2.** Probe name. Driver `:2139` → `client.preview_calendar_config(echo)`. |
| 31 | `market-data-client/preview-calendar-config-async-response` | market-data | `parse_calendar_config_response` | `CalendarConfig` | 12 | extra 3 + missing 9 | **Structural — see finding S-2.** Probe name. Driver `:2216` → `aclient.preview_calendar_config(echo)`. |
| 32 | `market-data-client/add-holidays-sync-response` | market-data | `parse_calendar_write_response` | **N/A** | — | — | Parser returns `dict[str, Any]` by design (D-06/D-16): the live OpenAPI declares the calendar-write `200` as a bare untyped object. Typing it is TYP-02's job. |
| 33 | `market-data-client/add-holidays-async-response` | market-data | `parse_calendar_write_response` | **N/A** | — | — | Same parser, same untyped write-ack contract (TYP-02). |
| 34 | `market-data-client/delete-holiday-sync-response` | market-data | `parse_calendar_write_response` | **N/A** | — | — | Same parser, same untyped write-ack contract (TYP-02). |
| 35 | `market-data-client/delete-holiday-async-response` | market-data | `parse_calendar_write_response` | **N/A** | — | — | Same parser, same untyped write-ack contract (TYP-02). |
| 36 | `matriz-client/get-segments` | matriz | `parse_get_segments_response` | `Segment` | 0 | — | Witness re-enveloped under `segments` (key read from the parser's own source). |
| 37 | `matriz-client/get-all-instruments` | matriz | `parse_get_all_instruments_response` | `Instrument` | 0 | — | Re-enveloped under `instruments`. Nested `instrumentId` present — contrast rows 38-39. |
| 38 | `matriz-client/get-instruments-by-cfi-esxxxx` | matriz | `parse_get_instruments_by_cfi_response` | `Instrument` | 3 | extra 2 + non_dict 1 | **Structural — see finding S-3.** Probe name `get_instruments_by_cfi_ESXXXX`; real function is `get_instruments_by_cfi` (`main_matriz.py:1454`). Re-enveloped under `instruments`. |
| 39 | `matriz-client/get-instruments-by-segment` | matriz | `parse_get_instruments_by_segment_response` | `Instrument` | 3 | extra 2 + non_dict 1 | **Structural — see finding S-3.** Re-enveloped under `instruments`. |
| 40 | `matriz-client/get-instruments-details` | matriz | `parse_get_instruments_details_response` | `InstrumentDetail` | 7 | extra 7 | **Structural — see finding S-4.** Re-enveloped under `instruments`. |
| 41 | `matriz-client/get-instrument-detail` | matriz | `parse_get_instrument_detail_response` | `InstrumentDetail` | 7 | extra 7 | **Structural — see finding S-4.** Re-enveloped under `instrument` (singular). |
| 42 | `matriz-client/get-market-data` | matriz | `parse_get_market_data_response` | `MarketDataSnapshot` | 4 | non_dict 4 | **Structural — see finding S-5.** Re-enveloped under `marketData`. |
| 43 | `matriz-client/get-trades` | matriz | `parse_get_trades_response` | `Trade` | 0 | — | Empty capture (`schema: []`) — no trades on the wire in the capture window. Not evidence of a clean model. |

**Coverage:** 43 rows for 43 files. 30 rows are mapped to a parser and a model; 13 rows
are **N/A** with a written reason (4 iol, 1 ambito, 6 market-data unmodelled `dict`
returns, 1 higyrus unmodelled `dict` return, and — counted within those — the four
calendar-write acks). No file is silently absent.

---

## Floor table — the per-package lower bound

| Package | Floor | Files walked | Files N/A | Basis |
| ------- | ----- | -----------: | --------: | ----- |
| `higyrus-client` | **≥ 22** | 4 | 1 | 3 files contributed records; 1 file was an empty capture. |
| `matriz-client` | **≥ 24** | 7 | 0 | 5 files contributed records; 1 empty capture, 1 clean. |
| `market-data-client` | **≥ 50** | 19 | 6 | 9 files contributed records; 10 files clean or empty. |
| `iol-client` | **N/A** | 0 | 4 | **Not applicable, not zero.** The package has no `models.py`; every parser returns `dict[str, Any]` / `list[dict[str, Any]]` / `Any`, so there is no declared keyset for the walker to compare a wire keyset against. A typed surface arrives in Phase 30 (TYP-01); the floor for iol can only be measured after that. Reporting `≥ 0` here would read as "iol is clean", which is precisely the false clean this milestone exists to eliminate. |
| `ambito-financiero-client` | **N/A** | 0 | 1 | **Not applicable, not zero.** No `models.py`; `parse_get_dollar_banco_nacion_response` returns a bare `float`. There is no model, therefore no model-versus-wire comparison to make. Same reasoning as iol: a zero would read as clean. |
| **Total (modelled packages)** | **≥ 96** | 30 | 13 | |

Read every figure as *at least this many distinct divergences exist on the shapes we have
captured*. The true live number is higher for the reasons in the blind-spot section.

---

## Breakdown by kind

| Package | missing | type | extra | non_dict | Floor |
| ------- | ------: | ---: | ----: | -------: | ----: |
| `higyrus-client` | 22 | 0 | 0 | 0 | ≥ 22 |
| `matriz-client` | 0 | 0 | 18 | 6 | ≥ 24 |
| `market-data-client` | 34 | 0 | 14 | 2 | ≥ 50 |
| **Total** | **56** | **0** | **32** | **8** | **≥ 96** |

Each row sums to that package's floor: 22+0+0+0 = 22; 0+0+18+6 = 24; 34+0+14+2 = 50.

**The dominant class is `missing` — 56 of 96, 58%.** Every one of those 56 is the same
shape of defect: **a field the model declares as a non-`Optional` scalar (or list, or
nested model) arrives as `null` on the wire, and the decoder silently substitutes a typed
zero** — `""` for `str`, `0.0` for `float`, `[]` for `list`. A consumer reading
`posicion.precio` gets `0.0` and cannot distinguish "the price is zero" from "the API sent
no price". That substitution is exactly what Phase 29 makes observable and it is already
the majority of the floor on a corpus of 43 type-only captures.

`extra` (32, 33%) is second and is **informational by policy** — aggregation contract lock
3 emits it at `INFO`, lock 4 never raises on it. An extra wire key is normal vendor API
growth.

`non_dict` (8, 8%) is small in count and large in consequence: each one means an entire
nested model decoded to all-defaults.

**`type` is zero, and that is a property of the method, not of the code.** The witness
carries typed *zero values* synthesized from the corpus's type names, so the only way a
`type` divergence can appear is if the corpus recorded a type name that differs from the
declared type. It never did in this corpus. On the live wire, `type` divergences are
whatever the real values produce — this floor says nothing about them.

**Strict-mode split.** Under aggregation contract lock 4, `missing` / `type` / `non_dict`
raise in strict mode and `extra` does not. Of the 96 records, **64 are strict-fatal**
(higyrus 22, market-data 36, matriz 6) and 32 are `INFO`-level `extra`. Phase 33's strict
driver run should expect to be stopped by the first of those 64 on each affected endpoint.

---

## Structural findings

Five rows show the model and the wire disagreeing **structurally** rather than
incidentally. Each is a candidate finding for the live-verification phase, named with its
package and field. None is fixed here — Plan 10 modifies no package source.

### S-1 — `market-data`: `parse_instruments_response` and `parse_segments_response` do not unwrap the recorded envelope

- **Package:** `market-data-client`
- **Files:** `get-instruments.json` (captured 2026-07-31), `get-segments.json` (2026-07-31)
- **Wire (recorded):** `GET /instruments` → `{catalogue{…}, count, items[…], limit, offset, total}`;
  `GET /instruments/segments` → `{catalogue{…}, segments[…]}`
- **Client:** both parsers end in `[Model.from_api(item) for item in raw]` with **no
  envelope unwrap** (`_core.py:926-940`, `:942-956`).
- **Consequence:** iterating a JSON object iterates its **keys**, so every row decodes
  from a `str` and the parser returns one all-default `Instrument` / `Segment` per
  envelope key. The walker reports it as `non_dict Instrument .`/`non_dict Segment .`
  (deduped to one record per model — the record count of 1 understates the blast radius
  badly).
- **Precedent:** this is the identical failure mode already fixed twice in this package —
  `parse_symbols_response` (D-11, F-41/F-51) and `parse_calendar_response` (D-12). Both
  fix docstrings describe exactly this symptom.
- **Caveat:** it is possible the server introduced the envelope after the client was
  written. Either way the captured live shape and the shipped parser disagree today.
- **Route to:** Phase 33, live re-verification of `GET /instruments` and
  `GET /instruments/segments` before any fix lands.

### S-2 — `market-data`: `preview_calendar_config` is typed `CalendarConfig` but the wire returns a preview envelope

- **Package:** `market-data-client`
- **Files:** `preview-calendar-config-sync-response.json`,
  `preview-calendar-config-async-response.json` (both 2026-08-01)
- **Wire (recorded):** `{market_after{is_open, local_time, next_transition, reason,
  session_close, session_open, state}, requires_confirmation, valid, warnings[]}`
- **Client:** `preview_calendar_config` reuses `parse_calendar_config_response`
  unmodified (`client.py:661-679`), which calls `CalendarConfig.from_api(raw)`.
- **Consequence:** nine declared `CalendarConfig` fields (`open`, `close`, `enabled`,
  `editable`, `env_bypass`, `pre_open_minutes`, `source`, `timezone`, `updated_by`) are
  absent from the preview body and collapse to typed zeros, while three real preview
  fields (`valid`, `requires_confirmation`, `market_after`) are discarded. The caller
  receives a `CalendarConfig` that is almost entirely fabricated, and the one field that
  survives is `warnings`.
- **Route to:** Phase 33 / TYP-02 — the preview response wants its own model.

### S-3 — `matriz`: `Instrument.instrumentId` is absent on the byCFICode and bySegment endpoints, where `marketId`/`symbol` arrive flattened

- **Package:** `matriz-client`
- **Files:** `get-instruments-by-cfi-esxxxx.json`, `get-instruments-by-segment.json`
  (both 2026-06-10)
- **Wire (recorded):** `[{marketId: str, symbol: str}]` — flat
- **Contrast:** `get-all-instruments.json` records
  `[{cficode: str, instrumentId: {marketId, symbol}}]` — nested
- **Client:** all three endpoints decode into the same `Instrument` model
  (`models.py:264-268`), whose `instrumentId: InstrumentId` is non-`Optional`.
- **Consequence:** for `get_instruments_by_cfi` and `get_instruments_by_segment` the
  nested `instrumentId` is missing on every row and collapses to `InstrumentId.empty()`,
  while the two fields that carry the actual identity are reported as `extra` and
  **discarded**. A consumer reading `inst.instrumentId.symbol` after either call gets an
  empty value on every row, silently. This is the highest-consequence finding in the set.
- **Route to:** Phase 33 — confirm on the live wire, then Phase 30/31 model work.

### S-4 — `matriz`: `InstrumentDetail` does not declare seven fields the wire sends

- **Package:** `matriz-client`
- **Files:** `get-instrument-detail.json`, `get-instruments-details.json` (both 2026-06-10)
- **Undeclared wire keys:** `securityId`, `securityIdSource`, `securityType`, `settlType`,
  `strike`, `symbol`, `underlying`
- **Consequence:** informational by policy (`extra` → `INFO`, never fatal), but it is 14 of
  matriz's 24 records and it means seven live fields — including `strike` and `underlying`,
  which are load-bearing for derivatives — are invisible to consumers.
- **Route to:** Phase 31 (TYP-03) model surface work; not a defect, a coverage gap.

### S-5 — `matriz`: four `MarketDataSnapshot` entry fields are declared non-`Optional` nested models but arrive `null`

- **Package:** `matriz-client`
- **File:** `get-market-data.json` (2026-06-10)
- **Fields:** `.LA`, `.SE`, `.OI`, `.CL` — declared `MarketDataEntryValue`, recorded as
  `NoneType`
- **Consequence:** each collapses to an all-default nested model. Note the capture was
  taken outside an active trading session (`BI` and `OF` are empty lists), so this may be
  the legitimate market-closed shape rather than a modelling error — which is itself the
  argument for declaring them `Optional`.
- **Route to:** Phase 33 — recapture during market hours, then decide `Optional` vs. defect.

### Also worth naming (not structural, but the dominant silent-substitution sites)

| Package | Model | Fields arriving `null` against a non-`Optional` declaration |
| ------- | ----- | ---------------------------------------------------------- |
| higyrus | `PosicionValuada` | `fecha`, `comprobante`, `precio`, `administrador`, `cartera`, `mercado`, `segmento`, `sesion`, `tipoTitulo`, `monedaCotizacion`, `idMovimiento` (11) |
| higyrus | `Movimiento` | `fechaConcertacion`, `tipoTitulo`, `tipoTituloAgente`, `tipoOperacion`, `tipoEspecie`, `valuacion`, `factorizacion`, `concepto`, `idMovimientos` (9) |
| higyrus | `Posicion` | `disponibleAjustado`, `parking` (2) |
| market-data | `MarketDataSnapshot` | `market_id`, `active`, `entries`, `staleness_seconds` (4, on the no-data `get-latest` shape) |
| market-data | `Symbol` | `created_at`, `updated_at` (absent from every write-ack body) |
| market-data | `CalendarConfig` | the 9 fields listed in S-2 |

---

## Blind spot — what a type-only corpus structurally cannot see

**This floor is blind to every value-level divergence.** The corpus stores type *names*,
never values, by construction (that is what makes it safe to keep in the repository), and
the witness payloads are synthesized typed zeros. The classes of divergence that are
therefore invisible to this run:

- **Non-finite numbers.** A `float` field carrying `NaN` or `Infinity` reduces to the type
  name `"float"` in the corpus and to `0.0` in the witness. Indistinguishable from a
  healthy number here; a real problem on the live wire.
- **Enumeration values outside a declared set.** D-09 decodes RESPONSE `Literal` fields as
  `str` and reports an out-of-set value as a divergence rather than enforcing membership.
  The corpus records only `"str"`, and the witness supplies `""`, so **no out-of-set value
  can ever be produced by this run**. Every one of matriz's nine `types.py` aliases
  (`Side`, `OrderType`, `TimeInForce`, `MarketId`, `SegmentId`, `CFICode`,
  `MarketDataEntry`, `OrderStatus`, `Currency`) is untested by this floor.
- **Range, format and encoding violations** — a date string that is not a date, a negative
  quantity, a truncated identifier, a mis-encoded accent. All reduce to `"str"`.
- **Cross-field inconsistency** — a total that does not equal the sum of its parts. The
  walker is per-field and would not see it even with real values.
- **Heterogeneous collections.** `schema_of` reduces a sequence to *the first element's*
  reduction. If row 1 is complete and row 4,000 is missing a field, the corpus records
  only row 1's shape. The floor sees the best row, never the worst.
- **Endpoints with no capture at all.** Two files are empty captures
  (`higyrus/get-listado-cuentas`, `matriz/get-trades`) and every matriz order/position
  endpoint has no schema file, so their divergences cannot be in this number.

These are precisely the classes D-09 defers to Phase 33's live census. **The floor
therefore understates the live number by an unknown margin, and the margin is in one
direction only: upward.**

---

## Freshness of the evidence

Read from each file's `captured_at` field. Run date 2026-08-19.

| Package | Oldest capture | Newest capture | Age of oldest | Files |
| ------- | -------------- | -------------- | ------------- | ----: |
| `ambito-financiero-client` | 2026-06-02 | 2026-06-02 | ~11 weeks | 1 |
| `iol-client` | 2026-06-06 | 2026-06-06 | ~10.5 weeks | 4 |
| `higyrus-client` | 2026-06-08 | 2026-06-08 | ~10 weeks | 5 |
| `matriz-client` | 2026-06-10 | 2026-06-10 | ~10 weeks | 8 |
| `market-data-client` | 2026-07-31 | 2026-08-01 | ~2.5 weeks | 25 |

Three of the five corpora are roughly ten weeks old. **Staleness weakens the floor's
currency but not its validity as a lower bound.** A divergence recorded ten weeks ago
either still exists — in which case the floor holds — or was fixed upstream, in which
case that specific divergence is gone but nothing about the count of *newly appeared*
divergences is knowable from stale evidence either. The bound is a bound on what we have
seen, not a prediction; the live census is what makes it current. Note also that matriz's
capture is a market-closed snapshot (S-5), which shapes which divergences it could
contain at all.

---

## Consequence — this number is the declared budget

**The per-package floors published above become the declared budget for the
live-verification phase (Phase 33): higyrus `≥ 22`, matriz `≥ 24`, market-data `≥ 50`,
iol and ambito not measurable until their typed surfaces exist.** Phase 33's live census
measures itself against these numbers, and it can do so directly without translation
because both runs emit the same six-key record through the same walker with the same
`(model, field_path, kind)` dedupe triple (D-06, aggregation contract locks 1 and 5).

The milestone's largest standing risk is that years of silent tolerance have hidden an
unknown volume of divergences and that the first strict run uncovers all of them at once
and overruns the milestone. This measurement is the agreed mitigation. If Phase 33's live
census **exceeds** these floors — which it will, since the blind spot only points upward —
that overrun requires an **explicit re-scope**: the excess findings are triaged, and every
deferred finding is routed to a **named destination phase** with its package and field
recorded. Deferring a finding to "later" without a named destination, or silencing it by
narrowing the walker, is not an available option; that would reintroduce exactly the
false clean this milestone exists to remove.

---

## Ratification

The operator must ratify this floor before it is treated as a downstream budget. Until the
signature line below is filled, no phase may cite these numbers as a committed budget.

Signed:
Date:
Decision recorded:
