# 38-CENSUS.md — the NOBJ-AUD-01 field-by-field census of higyrus, ámbito and wallets

**All three packages measure `0` violations, and that is exactly the situation in which a report
is most likely to be worthless.** Three empty tables read as a clean bill of health nobody
earned — the false clean this milestone exists to eliminate. ROADMAP SC-2 and SC-4 forbid it by
name, so this census enumerates the **full candidate population** rather than only the
violations, and the two packages whose zero comes from having no models at all are reported as
**zero by enumeration**, with the cause named, rather than as clean.

---

## Scope

NOBJ-AUD-01 covers exactly three packages: `higyrus-client`, `ambito-financiero-client` and
`wallets-client` (`REQUIREMENTS.md:33`). Three other packages of this workspace are audited
elsewhere and their absence from the tables below is **not** a gap:

| Package | Where it is audited | Status |
|---|---|---|
| `iol-client` | NOBJ-IOL-01 — plans `38-01` / `38-03` of this same phase | closed in this phase |
| `market-data-client` | Phase 36 | closed |
| `matriz-client` | Phase 37 | closed |

The one place matriz appears below is the SC-3 closing grep, which is workspace-wide by
construction (`packages/*/src/*/models.py`) and must be reported over all six packages.

---

## The gate run every disposition cell cites

Every disposition in this file is a transcription of one executed run of the widened gate, not a
reading of source. The run, verbatim:

```
$ uv run python tools/check_surface_types.py
surface types: 6 packages, 186 `__all__` names, 336 definitions scanned, 442 fields scanned, 13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1), 0 violations
$ echo $?
0
```

Scoped to one package at a time (`scan_surface_types(root)` with a root holding only that
package's `packages/` entry — the D-04 injectable seed), the same run gives the per-package
figures this census is built on:

| Package | `__all__` names | definitions | **fields** | exempted | by reason | violations |
|---|---:|---:|---:|---:|---|---:|
| `higyrus-client` | 31 | 52 | **142** | 5 | dunder 4, serialize-out 1 | **0** |
| `ambito-financiero-client` | 10 | 26 | **0** | 4 | dunder 4 | **0** |
| `wallets-client` | 5 | 2 | **0** | 0 | — | **0** |

The higyrus `142` is the cross-check the plan asks for: the independent stdlib-`ast` inventory
below sums to `142` across `15` field-carrying classes, and the gate's own `fields` counter for
higyrus alone reports `142`. The two agree exactly; there is no disagreement to report.

---

## Main table A — higyrus link and collection candidates, per field

Granularity: **per field**. Every model-typed, list-of-model-typed and mapping-typed field
across the 15 field-carrying classes, with its annotation as written in
`packages/higyrus-client/src/higyrus_client/models.py`.

| Package | Class | Field | Annotation | Category | Disposition | Evidence |
|---|---|---|---|---|---|---|
| higyrus-client | `Posicion` | `parking` | `list[Parking]` | list-of-model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:316` |
| higyrus-client | `Administrador` | `agente` | `Agente` | model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:436` |
| higyrus-client | `Administrador` | `operador` | `Operador` | model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:437` |
| higyrus-client | `Administrador` | `sucursal` | `Sucursal` | model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:438` |
| higyrus-client | `Cuenta` | `disposicionesGenerales` | `DisposicionesGenerales` | model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:462` |
| higyrus-client | `Cuenta` | `domicilios` | `list[Domicilio]` | list-of-model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:463` |
| higyrus-client | `Cuenta` | `personasRelacionadas` | `list[PersonaRelacionada]` | list-of-model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:464` |
| higyrus-client | `Cuenta` | `mediosComunicacion` | `list[MedioComunicacion]` | list-of-model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:465` |
| higyrus-client | `Cuenta` | `cuentasBancarias` | `list[CuentaBancaria]` | list-of-model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:466` |
| higyrus-client | `Cuenta` | `administrador` | `Administrador` | model link | Already non-optional; no action required | gate run above, `0 violations`; `models.py:467` |
| higyrus-client | `Movimiento` | `idMovimientos` | `list[int]` | list-of-scalar collection | Already non-optional; typed element, so D-01b's `list[Any]` allowance is not even reached | gate run above, `0 violations`; `models.py:284` |
| higyrus-client | *(all 15 classes)* | *(none)* | *(none declared)* | mapping-typed field | **Zero by enumeration** — the AST scan finds no field whose annotation mentions `dict[` anywhere in this module; the workspace-wide mapping grep below returns no higyrus field row either | AST inventory, `mapping fields: []`; mapping grep output below |

**11 per-field rows**, of which 10 are links (5 model-typed, 5 list-of-model-typed) and 1 is a
typed scalar collection. The 12th row records the mapping candidate count as a measured zero
rather than by omitting the category.

---

## Main table B — higyrus scalar leaves, per class

Granularity: **per class** aggregate, as RESEARCH Open Question 3 recommends. Each row gives the
count of scalar-leaf fields in that class and a single disposition citing D-NO-03, the policy
that permits an optional arm on a scalar. These rows plus the per-field rows above sum to the
142 total.

| Package | Class | Field | Annotation | Category | Disposition | Evidence |
|---|---|---|---|---|---|---|
| higyrus-client | `SafeModel` | — (0 fields) | — | base class, no fields | Exported but declares no field; contributes 0 to the 142 | AST inventory, `SafeModel 0` |
| higyrus-client | `Health` | 1 scalar leaf | `str` | scalar leaf | Permitted by D-NO-03; and none of the 1 carries an optional arm at all | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `PosicionValuada` | 21 scalar leaves | `str` / `float` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `Parking` | 4 scalar leaves | `str` / `int` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `Movimiento` | 21 scalar leaves | `str` / `float` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `Posicion` | 19 scalar leaves | `str` / `float` / `int` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `DisposicionesGenerales` | 15 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `Domicilio` | 6 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `PersonaRelacionada` | 13 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `MedioComunicacion` | 7 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `CuentaBancaria` | 5 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `Agente` | 2 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `Operador` | 3 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `Sucursal` | 2 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |
| higyrus-client | `Administrador` | 0 scalar leaves | — | scalar leaf | All 3 of its fields are links, already rowed above | AST inventory, `Administrador 3 3 0 0 0 0` |
| higyrus-client | `Cuenta` | 12 scalar leaves | `str` | scalar leaf | Permitted by D-NO-03; none carries an optional arm | AST inventory; `optional-bearing fields: []` |

**The arithmetic, so the population is provably complete:**

```
10 link fields (table A)
 + 1 list-of-scalar field (table A)
 + 131 scalar leaves (table B: 1+21+4+21+19+15+6+13+7+5+2+3+2+0+12)
 = 142 fields across 15 field-carrying classes
```

`142` is also what the gate's own `fields` counter reports for `higyrus-client` alone. The
D-NO-03 allowance is cited on every scalar row, but it is **not load-bearing here**: the AST
scan reports `optional-bearing fields: []` — not one higyrus field carries an optional arm in
any of the three legal spellings. The allowance is quoted so the policy is visible, not because
this package leans on it.

---

## The public-return half

Granularity: **per function, per surface**. Every public domain function in the three packages,
on both the sync (`client.py`) and async (`aio.py`) surfaces where both exist.

| Package | Surface | Function | Return annotation | Category | Disposition | Evidence |
|---|---|---|---|---|---|---|
| higyrus-client | `client.py` | `configure` | `None` | scalar/void | Typed; no untyped mapping exposed | gate run, `0 violations`; `client.py:548` |
| higyrus-client | `client.py` | `login` | `str` | scalar leaf | Typed; no untyped mapping exposed | gate run, `0 violations`; `client.py:598` |
| higyrus-client | `client.py` | `get_health` | `Health` | model | Typed model return; no action required | gate run, `0 violations`; `client.py:602` |
| higyrus-client | `client.py` | `get_movimientos` | `list[Movimiento]` | list-of-model | Typed model return; no action required | gate run, `0 violations`; `client.py:606` |
| higyrus-client | `client.py` | `get_posicion_valuada` | `list[PosicionValuada]` | list-of-model | Typed model return; no action required | gate run, `0 violations`; `client.py:623` |
| higyrus-client | `client.py` | `get_listado_cuentas` | `list[Cuenta]` | list-of-model | Typed model return; no action required | gate run, `0 violations`; `client.py:647` |
| higyrus-client | `client.py` | `get_posiciones` | `list[Posicion]` | list-of-model | Typed model return; no action required | gate run, `0 violations`; `client.py:661` |
| higyrus-client | `aio.py` | `configure` | `None` | scalar/void | Typed; mirrors the sync surface | gate run, `0 violations`; `aio.py:540` |
| higyrus-client | `aio.py` | `login` | `str` | scalar leaf | Typed; mirrors the sync surface | gate run, `0 violations`; `aio.py:604` |
| higyrus-client | `aio.py` | `get_health` | `Health` | model | Typed model return; mirrors the sync surface | gate run, `0 violations`; `aio.py:608` |
| higyrus-client | `aio.py` | `get_movimientos` | `list[Movimiento]` | list-of-model | Typed model return; mirrors the sync surface | gate run, `0 violations`; `aio.py:612` |
| higyrus-client | `aio.py` | `get_posicion_valuada` | `list[PosicionValuada]` | list-of-model | Typed model return; mirrors the sync surface | gate run, `0 violations`; `aio.py:629` |
| higyrus-client | `aio.py` | `get_listado_cuentas` | `list[Cuenta]` | list-of-model | Typed model return; mirrors the sync surface | gate run, `0 violations`; `aio.py:653` |
| higyrus-client | `aio.py` | `get_posiciones` | `list[Posicion]` | list-of-model | Typed model return; mirrors the sync surface | gate run, `0 violations`; `aio.py:667` |
| ambito-financiero-client | `client.py` | `configure` | `None` | scalar/void | Typed; no untyped mapping exposed | gate run, `0 violations`; `client.py:281` |
| ambito-financiero-client | `client.py` | `get_dollar_banco_nacion` | `float` | scalar leaf | The package's only domain function; a parsed scalar, no envelope to model | gate run, `0 violations`; `client.py:341` |
| ambito-financiero-client | `aio.py` | `configure` | `None` | scalar/void | Typed; mirrors the sync surface | gate run, `0 violations`; `aio.py:227` |
| ambito-financiero-client | `aio.py` | `get_dollar_banco_nacion` | `float` | scalar leaf | Same scalar return; mirrors the sync surface | gate run, `0 violations`; `aio.py:303` |
| wallets-client | `client.py` | `configure` | `None` | scalar/void | The **only** exported callable; see the stub qualification below — this is not a domain function | gate run, `0 violations`; `client.py:39` |
| wallets-client | `aio.py` | `configure` | `None` | scalar/void | Same; wallets exposes **zero** domain functions on either surface | gate run, `0 violations`; `aio.py:36` |
| wallets-client | both | *(no domain function)* | *(none)* | domain return | **Zero by enumeration** — `__all__` (`__init__.py:22-28`) is 4 exception classes plus `configure`; there is no endpoint to return anything | `__init__.py:22-28`; AST export scan |

**7 higyrus exports × 2 surfaces, 2 ámbito exports × 2 surfaces, 0 wallets domain functions.**
No public return in any of the three packages exposes `dict[str, Any]` or `list[dict[str, Any]]`
— the second half of ROADMAP SC-3.

### Members the gate exempted — cited, not re-opened (D-09)

| Package | Member | Reason (verbatim from the run's taxonomy) | Disposition | Evidence |
|---|---|---|---|---|
| higyrus-client | `SafeModel.to_dict` | `serialize-out` | Cites the gate's existing exemption; **no fix proposed and the decision is not re-opened**. The escape hatch it serves is documented at `packages/iol-client/README.md:189-199` with its known lossiness | per-package scan: `exempted_by_reason = (('dunder', 4), ('serialize-out', 1))` |
| higyrus-client | 4 dunder members | `dunder` | Cites the gate's existing exemption; no fix proposed | per-package scan: `dunder 4` |
| ambito-financiero-client | 4 dunder members | `dunder` | Cites the gate's existing exemption; no fix proposed | per-package scan: `exempted_by_reason = (('dunder', 4),)` |
| wallets-client | *(none)* | — | Nothing was exempted here because nothing reached the gate that needed it | per-package scan: `exempted = 0` |

Workspace-wide the taxonomy has exactly four named reasons — `dunder 13, private-helper 1,
serialize-out 9, ws-catch-all 1` — reproduced verbatim from the run at the top of this file. The
single `private-helper` hit is a **matriz method** (`Client._matriz_legacy_request`), not a
module-level function in any of the three packages audited here.

### Members that are out of the gate's candidate set — unreachable, not exempted

These are **not exemptions.** The gate resolves candidates from each package's exported surface
outward, so a member absent from every `__all__` is never reached and never adjudicated. Calling
it "exempted" would overstate how much the gate actually decided. This corrects CONTEXT D-09,
which describes the taxonomy as "`to_dict()` serialize-out ×9, legacy `_request` shims ×2" — the
`×2` module-level `_request` shims do not appear in the taxonomy at all, because they are out of
the gate's candidate set.

| Package | Member | Why unreachable | Disposition | Evidence |
|---|---|---|---|---|
| higyrus-client | `client._request` (`client.py:678`) | Absent from `__all__`; `_resolve_export` never reaches it | Out of the gate's candidate set — **not** exempted. Would be a violation if exported: its return carries an untyped mapping arm | AST export scan: `not-in-__all__`; signature below |
| higyrus-client | `aio._request` (`aio.py:684`) | Absent from `__all__` | Out of the gate's candidate set — **not** exempted; same untyped-mapping return as the sync twin | AST export scan: `not-in-__all__`; signature below |
| ambito-financiero-client | `client._request` (`client.py:326`) | Absent from `__all__` | Out of the gate's candidate set — **not** exempted; returns a concrete `httpx.Response` anyway | AST export scan: `not-in-__all__` |
| ambito-financiero-client | `aio._request` (`aio.py:285`) | Absent from `__all__` | Out of the gate's candidate set — **not** exempted; returns a concrete `httpx.Response` | AST export scan: `not-in-__all__` |
| wallets-client | `client._request` (`client.py:57`) | Absent from `__all__` | Out of the gate's candidate set — **not** exempted; returns a concrete `httpx.Response` | AST export scan: `not-in-__all__` |
| wallets-client | `aio._request` (`aio.py:73`) | Absent from `__all__` | Out of the gate's candidate set — **not** exempted; returns a concrete `httpx.Response` | AST export scan: `not-in-__all__` |

The two higyrus signatures, verbatim, since their annotation is the one that would matter if the
member were ever exported:

```python
# packages/higyrus-client/src/higyrus_client/client.py:678
def _request(...) -> dict[str, Any] | list[Any] | None: ...
# packages/higyrus-client/src/higyrus_client/aio.py:684
async def _request(...) -> dict[str, Any] | list[Any] | None: ...
```

This mirrors the gate's own recorded blast-radius note about the internal request-spec dataclass
(`tools/check_surface_types.py:304-313`): unreachable-today members are documented, not
pre-banned, and anyone who adds one to an `__all__` must re-check the gate first.

---

## The enumerated zeros

### `ambito-financiero-client` — zero by enumeration, not zero by cleanliness

Measured, not inherited:

```
$ grep -c '^class ' packages/ambito-financiero-client/src/ambito_financiero_client/models.py
0
$ wc -l packages/ambito-financiero-client/src/ambito_financiero_client/models.py
      27 packages/ambito-financiero-client/src/ambito_financiero_client/models.py
$ grep -n 'class' packages/ambito-financiero-client/src/ambito_financiero_client/models.py
11:declare its response shape, instead of a model class appearing in ``client.py``
16:in this package by Phase 29's design, and a base class with no subclass would be
```

`models.py` declares **zero classes** and is 27 lines of module docstring plus
`__all__: list[str] = []`. The two `class` tokens the file contains occur **in prose**, on lines
11 and 16 — confirmed above rather than assumed. The package's single endpoint parses a scraped
Argentine-format decimal straight into a `float`, so there is no envelope to model.

`35-RETIRED-TRIPLES.md` already records this absence, and this census cites that paragraph
rather than re-deriving it: *"`ambito-financiero-client` and `wallets-client` — absent by
enumeration, not by cleanliness."* At the current HEAD that paragraph is at **lines 169-180** of
`.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md` — see
the discrepancy table below for why this file does not write the `184-197` its own plan cited.

### `wallets-client` — zero by enumeration, and a stub besides

Measured the same way:

```
$ grep -c '^class ' packages/wallets-client/src/wallets_client/models.py
0
$ wc -l packages/wallets-client/src/wallets_client/models.py
      27 packages/wallets-client/src/wallets_client/models.py
$ grep -n 'class' packages/wallets-client/src/wallets_client/models.py
(no output — not even a prose occurrence)
```

**ROADMAP SC-4 requires the stub condition be recorded explicitly rather than reported as a
green.** The qualification, in full:

- **No domain function exists.** `wallets_client.__all__` (`__init__.py:22-28`) carries four
  exception classes — `WalletsAPIError`, `WalletsAuthError`, `WalletsClientError`,
  `WalletsRateLimitError` — plus `configure`. Nothing else. There is no endpoint to call.
- **It holds the Phase 29 decoder exemption**, written up in
  `.planning/milestones/v1.6-phases/29-decoder-observable/29-WALLETS-EXEMPTION.md`, and it has
  **no `_decode.py`** for the walker to live in. Its `models.py` docstring records that copying a
  `SafeModel` base here for cosmetic uniformity would raise `ImportError` on import.
- **Its 10 passing tests exercise config and exception plumbing only.** They prove nothing about
  model cleanliness, because there are no models. The gate's own per-package scan agrees from the
  other direction: `definitions = 2`, `fields = 0`, `exempted = 0`, `violations = ()`.

So wallets' `0 violations` is a **zero by enumeration** over an empty population, twice over — no
models to be dirty and no endpoints to return anything. It is not evidence of quality work, and
it must never be quoted bare.

---

## SC-3 closing evidence — commands executed, output verbatim

ROADMAP SC-3 requires *"el resultado se reporta con el comando ejecutado y su salida, no como
afirmación"*. Both greps below were run at this phase's HEAD; the output is pasted, not
described.

### Grep 1 — optional wrappers on model fields, minus the scalar leaves D-NO-03 permits

```bash
grep -nE '^\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*.*(\| None|Optional\[|Union\[)' packages/*/src/*/models.py \
  | grep -vE ':\s*(str|int|float|bool)\s*\| None'
```

```
packages/matriz-client/src/matriz_client/models.py:532:    marketId: MarketId | None = None
packages/matriz-client/src/matriz_client/models.py:552:    marketSegmentId: SegmentId | None = None
packages/matriz-client/src/matriz_client/models.py:553:    marketId: MarketId | None = None
packages/matriz-client/src/matriz_client/models.py:561:    cficode: CFICode | None = None
packages/matriz-client/src/matriz_client/models.py:607:    cficode: CFICode | None = None
packages/matriz-client/src/matriz_client/models.py:619:    currency: Currency | None = None
packages/matriz-client/src/matriz_client/models.py:660:    ordType: OrderType | None = None
packages/matriz-client/src/matriz_client/models.py:661:    side: Side | None = None
packages/matriz-client/src/matriz_client/models.py:662:    timeInForce: TimeInForce | None = None
packages/matriz-client/src/matriz_client/models.py:669:    status: OrderStatus | None = None
```

**10 lines, all in `packages/matriz-client/src/matriz_client/models.py`.** Every one is an
optional arm on a `Literal` type alias — `MarketId`, `SegmentId`, `CFICode`, `Currency`,
`OrderType`, `Side`, `TimeInForce`, `OrderStatus` — i.e. a scalar-set leaf permitted by D-NO-03.
Zero hits in higyrus, ámbito or wallets. Before plan `38-01` this grep returned 12; the two that
disappeared are iol's `Cotizacion.puntas` and `Titulo.puntas`.

### Grep 2 — the `dict[...]`-on-fields half

```bash
grep -nE '^\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*.*dict\[' packages/*/src/*/models.py
```

```
packages/higyrus-client/src/higyrus_client/models.py:139:        wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
packages/iol-client/src/iol_client/models.py:162:        wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
packages/market-data-client/src/market_data_client/models.py:228:        wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
packages/market-data-client/src/market_data_client/models.py:551:        out: dict[str, Any] = {"symbols": self.symbols}
packages/matriz-client/src/matriz_client/models.py:321:    decoded: dict[Any, Any] = {}
packages/matriz-client/src/matriz_client/models.py:345:    cls: type[Any], kwargs: dict[str, Any], *, sink: _decode.DecodeScope
packages/matriz-client/src/matriz_client/models.py:456:    __dataclass_fields__: ClassVar[dict[str, Any]]
packages/matriz-client/src/matriz_client/models.py:629:    tickPriceRanges: dict[str, TickPriceRange] = field(default_factory=dict)
packages/matriz-client/src/matriz_client/models.py:902:    report: dict[str, dict[str, InstrumentPositionReport]] = field(default_factory=dict)
packages/matriz-client/src/matriz_client/models.py:970:    detailedAccountReports: dict[str, DetailedAccountReport] = field(default_factory=dict)
packages/matriz-client/src/matriz_client/models.py:1032:    raw: dict[str, Any] = field(default_factory=dict)
```

**The raw grep returns 11 lines and over-reports by 6.** The indentation pattern cannot tell a
class-body field from a local variable in a method body, so the hits were classified by AST —
resolving each line's enclosing `ClassDef` and `FunctionDef` — into four buckets:

| Bucket | Count | Lines | Disposition |
|---|---:|---|---|
| Fully typed value parameter (a real field) | 3 | matriz `:629`, `:902`, `:970` | No action — the value type is named, so the annotation says something |
| Dunder `ClassVar` mapping (a real field) | 1 | matriz `:456` (`_SafeModel.__dataclass_fields__`) | Cites the gate's `dunder` exemption; no fix proposed |
| The one declared exemption (a real field) | 1 | matriz `:1032` (`UnknownFrame.raw`) | Cites `_FIELD_EXEMPTIONS["UnknownFrame.raw"] = "ws-catch-all"`; a payload whose shape is by definition unknown |
| **Not fields at all** | 6 | higyrus `:139`, iol `:162`, market-data `:228` and `:551` (locals inside `to_dict`); matriz `:321` and `:345` (a local and a parameter inside the module-level `_mapping_value` / `_apply_mapping_policy`) | Out of scope — a census that does not separate these over-reports by 6 |

**Zero of the 11 is a mapping-typed field in any of the three packages this census audits.** The
single higyrus hit (`:139`) is a local variable inside `SafeModel.to_dict`; ámbito and wallets
contribute no line at all, having no `models.py` content to match.

### The four suite baselines, run at this HEAD

| Suite | Command | Output |
|---|---|---|
| iol-client | `uv run --package iol-client pytest packages/iol-client -q` | `292 passed in 16.08s` |
| higyrus-client | `uv run --package higyrus-client pytest packages/higyrus-client -q` | `289 passed in 38.79s` |
| ambito-financiero-client | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client -q` | `208 passed, 1 deselected in 12.95s` |
| wallets-client | `uv run --package wallets-client pytest packages/wallets-client -q` | `10 passed in 0.02s` |

---

## Discrepancies named rather than absorbed

Where a prior artifact's number disagrees with a measured one, this census writes the **measured**
one and names the disagreement. It never carries an unsourced count into an SC-3 claim.

| # | Prior artifact says | Measured here | What this census writes | Command that settles it |
|---|---|---|---|---|
| 1 | CONTEXT D-11 (`38-CONTEXT.md:125-128`) says **11** `Literal`-alias optional leaves in matriz — then lists exactly 10 line numbers | **10** distinct lines: `532, 552, 553, 561, 607, 619, 660, 661, 662, 669` | **10**, with the grep output pasted above. RESEARCH F-9 flagged the same gap; no 11th line exists in any of the six packages | Grep 1, above |
| 2 | CONTEXT D-09 (`38-CONTEXT.md:98-103`) describes the exemption taxonomy as "`to_dict()` serialize-out ×9, legacy `_request` shims ×2" | `dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1` — four reasons, and no `×2` bucket for module-level `_request` | The taxonomy verbatim from the run. The module-level `_request` helpers are **out of the gate's candidate set**, not exempted; the single `private-helper` is a matriz method | `uv run python tools/check_surface_types.py` |
| 3 | Plan `38-04` and RESEARCH F-8 (`38-RESEARCH.md:461`) cite `35-RETIRED-TRIPLES.md:184-197` for the enumerated-absence paragraph | At HEAD the paragraph is at **169-180**; line 184 is the heading `## How Phase 39 should use this`. Before plan `38-03` it began at 161, so the citation was already stale when written | **169-180**, verified by reading the file | `awk 'NR>=169 && NR<=180' .planning/phases/35-.../35-RETIRED-TRIPLES.md` |
| 4 | CONTEXT D-09 cites the `to_dict()` escape hatch at `packages/iol-client/README.md:150-161` | The section `**Escape hatch: `to_dict()`**` is at **189-199** — plan `38-03` inserted the `## Unreleased — BREAKING` callout at line 5, shifting everything below it | **189-199** | reading `packages/iol-client/README.md` |

Discrepancies 3 and 4 are the same defect class plan `38-03` fixed inside
`35-RETIRED-TRIPLES.md`: a line reference measured at one HEAD and quoted at another. They are
recorded here rather than propagated.

---

## Method and limits — no number in this file is an estimate

Every figure above is either quoted from a cited line of an artifact or derived by counting the
rows of a table that transcribes an executed run. The runs, named:

1. **The gate invocation** — `uv run python tools/check_surface_types.py`, exit 0, whose summary
   line is reproduced verbatim at the top of this file. Plus three per-package invocations of
   `scan_surface_types(root)` against a root holding a single package, which is where the
   per-package `fields` / `exempted` / `exempted_by_reason` figures come from.
2. **The two SC-3 greps**, pasted above with their literal commands and their full output.
3. **The four package suites**, with their `-q` tail lines pasted above.
4. **A throwaway stdlib-`ast` inventory** over
   `packages/higyrus-client/src/higyrus_client/models.py`, which produced the per-class field
   counts, the link/mapping/scalar split, `optional-bearing fields: []` and `mapping fields: []`.

**On the introspection method.** The higyrus inventory was produced by parsing the module with
stdlib `ast`, deliberately **not** by importing `higyrus_client` and **not** by
`get_type_hints`. Importing any client module in this workspace runs `load_dotenv()` and
constructs an HTTP client at import time — exactly the discipline `tools/check_surface_types.py`
enforces on itself so a CI `lint` step cannot read a `.env`. The same discipline applies to a
one-off count. The snippet is **not committed**: this repo already carries three `tools/` gates
and does not need a fourth for a measurement taken once. No credential value appears anywhere in
this file.

**What this census does not measure.** It is a **static annotation** audit. It says what the
declarations are, not what the live wire sends. A field correctly declared `list[Parking]` that
never receives a `parking` key on the wire is green here and is a Phase 39 question. Nothing in
this file was written into `.planning/verification/` — those ledgers are machine-written between
`BEGIN AUTO-GENERATED` / `END AUTO-GENERATED` markers with a run-scoped ID/Class/Surface/Status
schema and an OPEN→FIXED lifecycle, and a static census has no run context to put in them (D-07).

---

## How Phase 39 should use this

**The failure mode this artifact prevents.** Phase 39 runs a **live** census over
`DivergenceHandler.seen`. That census will come back smaller than the static population written
down here. Without this file, that drop cannot be split into *"disappeared because the Null
Object policy stopped recording it"* and *"disappeared because it was fixed"* — and an
unsplittable drop reads as quality work nobody did. That is the same false clean
`35-RETIRED-TRIPLES.md` was built to block, one level up: there the risk was an unsubtracted
middle term, here it is an unwritten starting population.

**What to compare against.** For higyrus, the starting population is `142` fields across `15`
classes, of which `10` are links and `0` are optional in any spelling. For ámbito and wallets the
starting population is `0` — and it is `0` **by enumeration**, so a live census returning `0` for
either of them confirms nothing and must not be counted as a pass. For wallets specifically,
carry the stub qualification forward: no domain function, the Phase 29 decoder exemption, no
`_decode.py`.

**Where the retired-triples arithmetic lives — not here.** The accounting Phase 39 needs for its
subtraction is the `## Phase 38 addendum` section of
`.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md`: **2
field rows added to the roster, 0 triples retired in both columns, the middle term
(higyrus 2, iol 0, market-data 0, matriz 5 distinct / matriz 6 records) unchanged.** Read it
there rather than restating it here — the cross-reference is deliberately asymmetric, and that
addendum's §4 points back to this file for everything else.

---

*Phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets — plan 38-04*
*Requirement: NOBJ-AUD-01 — ROADMAP Phase 38 success criteria 2, 3 and 4*
*All measurements taken at HEAD `3d13b06`, 2026-08-29*
