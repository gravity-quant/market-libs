---
phase: quick-260731-jim
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/src/market_data_client/_core.py
  - main_market_data.py
  - packages/market-data-client/tests/test_models.py
  - packages/market-data-client/tests/test_reference_models.py
  - packages/market-data-client/tests/test_market_data.py
autonomous: true
requirements: [LIVE-MD-01]

must_haves:
  truths:
    - "MarketDataSnapshot fields match the real /marketdata and /marketdata/latest wire: market_id (not marketId), plus active, market_data, staleness_seconds, note; entries is list[str]"
    - "CalendarConfig fields match the real /calendar/config wire: no businessDays; open/close/enabled/editable/env_bypass/pre_open_minutes/source/timezone/updated_by/warnings/updated_at present"
    - "received_at stays client-stamped and injected via the from_api override (D-01) — a wire received_at never overrides the injected stamp"
    - "get_market_data unwraps the envelope items[] into snapshots (was iterating envelope keys)"
    - "market-data-client passes ruff check, ruff format --check, mypy strict, and pytest"
    - "The SHAPE-diff residual for MarketDataSnapshot and CalendarConfig on a live re-run is ~0 (endpoint-union sparse fields note/entries are suppressed like received_at)"
  artifacts:
    - path: "packages/market-data-client/src/market_data_client/models.py"
      provides: "Reconciled MarketDataSnapshot + CalendarConfig; MarketDataEntry removed"
      contains: "market_id"
    - path: "packages/market-data-client/src/market_data_client/_core.py"
      provides: "Envelope items[] unwrap in parse_market_data_response"
      contains: "items"
    - path: "main_market_data.py"
      provides: "SHAPE probe unwraps items[] and suppresses endpoint-union fields"
  key_links:
    - from: "packages/market-data-client/src/market_data_client/_core.py"
      to: "packages/market-data-client/src/market_data_client/models.py"
      via: "parse_market_data_response calls MarketDataSnapshot.from_api on each envelope item"
      pattern: "MarketDataSnapshot.from_api"
    - from: "main_market_data.py"
      to: "packages/market-data-client/src/market_data_client/models.py"
      via: "_emit_shape diffs raw wire item against MarketDataSnapshot / CalendarConfig"
      pattern: "_emit_shape"
---

<objective>
Reconcile the market-data-client `MarketDataSnapshot` and `CalendarConfig` SafeModels
against the REAL develop wire payloads captured in the LIVE-MD-01 schema snapshots,
closing the 36 SHAPE findings from the first credentialed live sweep.

Root-cause breakdown of the 36 findings (from the captured snapshots):
- `/marketdata/latest` MarketDataSnapshot: 7 field mismatches × 2 surfaces (sync+async) = 14
- `/calendar/config` CalendarConfig: 11 field mismatches × 2 surfaces = 22
- Total = 36. (`/marketdata` contributed 0 because the envelope made the probe's raw
  sample `None` — a silent validation gap this plan also closes.)

Purpose: The client must faithfully reflect the live API (project Core Value). The current
models invent shapes (`marketId`, nested `MarketDataEntry`, `businessDays`) that match no
wire payload, and `get_market_data` iterates the response envelope's KEYS instead of its
`items[]`.

Output: Reconciled models, an envelope-aware parser, an updated SHAPE probe, and regression
tests that pin the new shapes against payloads mirroring the captured snapshots. The operator
re-runs the live sweep afterward (this plan needs NO live credentials).
</objective>

<execution_context>
@/Users/admin/development/market-libs/.claude/gsd-core/workflows/execute-plan.md
@/Users/admin/development/market-libs/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/verification/schemas/market-data-client/get-market-data.json
@.planning/verification/schemas/market-data-client/get-latest.json
@.planning/verification/schemas/market-data-client/get-calendar-config.json
@packages/market-data-client/src/market_data_client/models.py
@packages/market-data-client/src/market_data_client/_core.py
@main_market_data.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Reconcile MarketDataSnapshot, retire MarketDataEntry, unwrap the envelope</name>
  <files>packages/market-data-client/src/market_data_client/models.py, packages/market-data-client/src/market_data_client/__init__.py, packages/market-data-client/src/market_data_client/_core.py</files>
  <behavior>
    - MarketDataSnapshot.from_api on a `/marketdata` item (envelope items[0] shape) parses:
      symbol:str, market_id:str, active:bool, entries:list[str] (e.g. ["BI","OF"]),
      market_data:dict passthrough (BI/OF -> list of {price,size}; CL/LA/SE -> dict;
      HI/LO/OP -> int; OI/TV -> null), staleness_seconds:float; received_at is the injected stamp.
    - MarketDataSnapshot.from_api on a `/marketdata/latest` no-data item parses:
      symbol set, note:str present, and the null fields collapse tolerantly
      (active -> False, market_data -> None, market_id -> "", staleness_seconds -> 0.0,
      entries -> []); received_at is still the injected stamp, NOT the wire null.
    - A decoy `"received_at"` key in the payload is ignored; the injected kwarg wins (D-01).
    - parse_market_data_response unwraps an envelope dict `{count, items:[...], ...}` into
      per-item snapshots, still tolerates a bare-list body and a null/empty body (-> []).
  </behavior>
  <action>
    In models.py, replace the MarketDataSnapshot field block with (in this order, so the one
    defaulted field is last): symbol: str; market_id: str; active: bool; entries: list[str];
    market_data: dict[str, Any]; staleness_seconds: float; received_at: float; note: str | None = None.
    Remove the old `marketId` and change `entries` from `list[MarketDataEntry]` to `list[str]`.
    KEEP the existing `from_api` override verbatim (it iterates `fields(cls)`, injects
    `received_at` from the keyword bypassing `_coerce`, and routes every other field through
    `_coerce`) — this is the D-01 fidelity contract and must not change. `Any` is already imported.

    Delete the MarketDataEntry dataclass entirely (its entryType/price/size shape matches no wire
    payload — the wire `entries` is a list of entry-type code strings; this is the same class of
    invented model as the `businessDays` field being dropped in Task 2, per the "do NOT over-model"
    directive). Remove the "MarketDataEntry" string from the models `__all__` list. Update the two
    module-docstring sentences that reference MarketDataEntry (the nested-rows note near the top and
    the "mirror the MarketDataEntry precedent" line above the reference models) to reference the
    SafeModel base / MarketDataSnapshot instead — do not leave a dangling class name in prose.

    In __init__.py, remove MarketDataEntry from the `from market_data_client.models import (...)`
    block and from the top-level `__all__` list. Do NOT touch the other exported model names.

    In _core.py `parse_market_data_response`, after the null-body guard, unwrap the envelope: if the
    decoded body is a dict, take its `items` value (defaulting to an empty list) as the row source;
    if it is already a list, use it as-is; otherwise use an empty list. Guard that the row source is
    a list before iterating. Build snapshots via `MarketDataSnapshot.from_api(item, received_at=received_at)`
    over that row source. Leave `parse_latest_response` on its bare-list path (the `/latest` wire is a
    bare list, not an envelope) — only its downstream model changed, absorbed by from_api tolerance.
    Do NOT touch the four reference-data parsers or the calendar-config parser here.

    Scope discipline: only MarketDataSnapshot is renamed. The `marketId` field on Instrument, Segment,
    Symbol, CalendarDay, and LatestRequest is OUT OF SCOPE (no snapshots captured for those endpoints) —
    leave them exactly as-is.
  </action>
  <verify>
    <automated>cd packages/market-data-client && uv run --package market-data-client python -c "import market_data_client as m; from market_data_client.models import MarketDataSnapshot as S; f={x.name for x in __import__('dataclasses').fields(S)}; assert 'market_id' in f and 'marketId' not in f and f>={'active','market_data','staleness_seconds','note','entries','received_at','symbol'}, f; assert 'MarketDataEntry' not in m.__all__; s=S.from_api({'symbol':'GGAL','received_at':999.0,'entries':['BI','OF']}, received_at=1234.5); assert s.received_at==1234.5 and s.entries==['BI','OF']; print('ok')"</automated>
  </verify>
  <done>MarketDataSnapshot has market_id (no marketId), active/market_data/staleness_seconds/note, entries:list[str]; MarketDataEntry is gone from models.py, models `__all__`, and __init__ (`__all__` + import); parse_market_data_response unwraps items[]; received_at injection is unchanged; ruff + mypy strict pass on the package src.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Reconcile CalendarConfig against the /calendar/config wire</name>
  <files>packages/market-data-client/src/market_data_client/models.py</files>
  <behavior>
    - CalendarConfig.from_api on the captured get-calendar-config.json shape parses every wire
      field: open, close (str); enabled, editable, env_bypass (bool); pre_open_minutes (int);
      source, timezone, updated_by (str); warnings (list, wire sends []); updated_at (str | None,
      wire sends null -> None).
    - CalendarConfig.from_api(None) and ({}) do not raise (D-07): every field takes its tolerant
      default (str -> "", bool -> False, int -> 0, list -> [], updated_at -> None).
    - CalendarConfig carries NO received_at (D-05 reference data) — it stays a plain SafeModel
      built via the inherited from_api (no override).
  </behavior>
  <action>
    In models.py, replace the CalendarConfig field block (drop `businessDays`, keep `timezone`) with,
    in this order so the one defaulted field is last: open: str; close: str; enabled: bool;
    editable: bool; env_bypass: bool; pre_open_minutes: int; source: str; timezone: str;
    updated_by: str; warnings: list[Any]; updated_at: str | None = None. Use `list[Any]` for warnings
    so unknown-shaped warning items pass through `_coerce` untouched rather than being coerced to "".
    Keep the class a plain frozen(slots) SafeModel subclass with NO from_api override and NO
    received_at. Update the docstring to state the wire config shape (drop any businessDays mention).
    `Any` is already imported.
  </action>
  <verify>
    <automated>cd packages/market-data-client && uv run --package market-data-client python -c "from market_data_client.models import CalendarConfig as C; f={x.name for x in __import__('dataclasses').fields(C)}; assert 'businessDays' not in f and f=={'open','close','enabled','editable','env_bypass','pre_open_minutes','source','timezone','updated_by','warnings','updated_at'}, f; c=C.from_api({'open':'11:00','close':'17:00','enabled':True,'editable':False,'env_bypass':False,'pre_open_minutes':10,'source':'db','timezone':'America/Argentina/Buenos_Aires','updated_at':None,'updated_by':'sys','warnings':[]}); assert c.open=='11:00' and c.enabled is True and c.pre_open_minutes==10 and c.updated_at is None and c.warnings==[]; e=C.from_api(None); assert e.timezone=='' and e.enabled is False and not hasattr(e,'received_at'); print('ok')"</automated>
  </verify>
  <done>CalendarConfig field set equals the wire field set (no businessDays), from_api parses the full config, from_api(None) yields tolerant defaults, no received_at; ruff + mypy strict pass.</done>
</task>

<task type="auto">
  <name>Task 3: Update the SHAPE probe and regression tests</name>
  <files>main_market_data.py, packages/market-data-client/tests/test_models.py, packages/market-data-client/tests/test_reference_models.py, packages/market-data-client/tests/test_market_data.py</files>
  <action>
    main_market_data.py: remove `MarketDataEntry` from the `from market_data_client import (...)` block.
    Add a module-level constant `_ENDPOINT_OPTIONAL = frozenset({"note", "entries"})` next to
    `_CLIENT_STAMPED`, documented as endpoint-union fields that one endpoint omits by design
    (note absent on /marketdata, entries absent on /marketdata/latest no-data) so their model-only
    absence is expected, not a defect. In `_emit_shape`, extend the model-only skip so it continues
    when the key is in `_CLIENT_STAMPED | _ENDPOINT_OPTIONAL` (keep the existing received_at behavior).
    In BOTH probe_market_data_sync and probe_market_data_async, replace the raw-sample extraction so it
    unwraps the envelope: derive the row list from `raw["items"]` when raw is a dict, else raw when it
    is a list, else empty; set `sample` to the first row or None. Delete the `entries = sample.get("entries")`
    / `_emit_shape(entries[0], MarketDataEntry, ...)` block in both surfaces (entries is now list[str],
    not nested objects). Update the two probe docstrings that say "SHAPE-diff (Snapshot + Entry)" to
    drop the "+ Entry".

    test_models.py: remove the `MarketDataEntry` import and delete
    test_entries_deserialize_as_entry_models_without_received_at. Update
    test_from_api_empty_dict_typed_zero_defaults to assert snap.market_id == "" (not marketId),
    snap.entries == [], snap.active is False, snap.note is None. Keep the received_at injection/decoy
    tests (they still hold). Replace test_entries_partial_or_wrong_type_tolerated with a list[str]
    tolerance case (entries="not-a-list" -> []). Add test_from_api_marketdata_item_parses_new_fields:
    feed a dict mirroring get-market-data.json items[0] (symbol, market_id, active=True, entries=["BI","OF"],
    market_data={"BI":[{"price":1,"size":2}],"CL":{"date":1,"price":3},"HI":4,"OI":None},
    staleness_seconds=1.5, received_at="ignored") with received_at=42.0; assert market_id, active is True,
    entries==["BI","OF"], market_data["BI"][0]["price"]==1 (dict passthrough intact), staleness_seconds==1.5,
    received_at==42.0. Add test_from_api_latest_nodata_item: feed a dict mirroring get-latest.json
    (symbol set, note="no data", active=None, market_data=None, market_id=None, received_at=None,
    staleness_seconds=None) with received_at=7.0; assert note is the string, active is False,
    market_data is None, market_id=="", entries==[], staleness_seconds==0.0, received_at==7.0.

    test_reference_models.py: update test_calendar_config_from_api_none_returns_defaulted_instance to
    drop the businessDays assertion and assert the tolerant defaults on the new fields (timezone=="",
    open=="", enabled is False, pre_open_minutes==0, warnings==[], updated_at is None). Replace
    test_calendar_config_from_api_populated to feed the full get-calendar-config.json shape and assert
    each new field (including updated_at is None from wire null). Keep the parametrized
    test_reference_models_have_no_received_at unchanged.

    test_market_data.py: in test_parse_market_data_response_stamps_received_at_once, wrap the two rows
    in an envelope body `{"count":2,"items":[{...},{...}],"limit":50,"offset":0,"total":2}` (reuse the
    existing fake-response helper), use `market_id` keys, and assert both parsed snapshots share the
    received_at stamp and expose market_id. Add a companion assertion (or a small extra test) that a
    bare-list body still parses (backward-compat). In test_parse_latest_response_stamps_received_at_once,
    change the `marketId` keys to `market_id` and keep the bare-list body; assert the shared stamp.
  </action>
  <verify>
    <automated>cd packages/market-data-client && uv run --package market-data-client ruff check . && uv run --package market-data-client ruff format --check . && uv run --package market-data-client mypy src && uv run --package market-data-client pytest -q && cd /Users/admin/development/market-libs && uv run --package market-data-client python -c "import ast; src=open('main_market_data.py').read(); assert 'MarketDataEntry' not in src and '_ENDPOINT_OPTIONAL' in src; ast.parse(src); print('ok')"</automated>
  </verify>
  <done>Probe unwraps items[] on both surfaces, drops the MarketDataEntry diff, and suppresses note/entries as endpoint-union fields; all three test files pin the reconciled shapes against payloads mirroring the captured snapshots; ruff, ruff format, mypy strict, and pytest all pass for the package; main_market_data.py imports and parses without MarketDataEntry.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| develop API -> client deserialization | Untrusted third-party JSON crosses into SafeModel.from_api |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-qmd-01 | Tampering | MarketDataSnapshot/CalendarConfig.from_api | mitigate | SafeModel `_coerce` tolerates null/wrong-type/missing fields — malformed or hostile payloads collapse to typed defaults, never raise or inject unexpected types |
| T-qmd-02 | Denial of Service | parse_market_data_response envelope loop | accept | Bounded by the server's `limit`/`items[]` size; no unbounded recursion (market_data is dict passthrough, not recursively modeled); no new install surface |
</threat_model>

<verification>
Run from the repo root:
- `uv run --package market-data-client ruff check .`
- `uv run --package market-data-client ruff format --check .`
- `uv run --package market-data-client mypy src` (from the package dir; strict)
- `uv run --package market-data-client pytest -q`

Operator follow-up (NOT part of this plan, no creds needed here): re-run the live sweep
`uv run --package market-data-client python main_market_data.py` and confirm the SHAPE findings
for MarketDataSnapshot and CalendarConfig drop to ~0.
</verification>

<success_criteria>
- MarketDataSnapshot and CalendarConfig field sets equal their respective captured wire shapes.
- MarketDataEntry is fully removed (models.py, models `__all__`, __init__ import + `__all__`, main_market_data.py).
- received_at remains client-stamped/injected (D-01); a wire/decoy received_at never wins.
- get_market_data parses the envelope items[]; parse_latest_response still parses the bare list.
- ruff, ruff format --check, mypy strict, and pytest all pass for market-data-client.
</success_criteria>

<output>
Create `.planning/quick/260731-jim-reconcile-market-data-client-marketdatas/260731-jim-SUMMARY.md` when done.
</output>
