# Phase 39: Verificación en vivo del encadenamiento profundo - Pattern Map

**Mapped:** 2026-08-29
**Files analyzed:** 13 (5 new, 8 modified)
**Analogs found:** 12 / 13

Every file this phase touches has a precedent **inside this repo**. Nothing here is a new
architecture: three new AST locks copy one green precedent verbatim, two new skip-shape guards
copy another, three mocked edge-case suites copy a third, and every driver edit is an insertion
inside an existing probe body whose surrounding shape must not change.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `verification/test_main_iol_deep_chain.py` (NEW) | test (AST lock) | transform (source → AST assertions) | `verification/test_main_market_data_deep_chain.py` | **exact** |
| `verification/test_main_higyrus_deep_chain.py` (NEW) | test (AST lock) | transform | `verification/test_main_market_data_deep_chain.py` | **exact** |
| `verification/test_main_matriz_deep_chain.py` (NEW) | test (AST lock) | transform | `verification/test_main_market_data_deep_chain.py` | **exact** |
| `verification/test_main_matriz_skip_line_shape.py` (NEW) | test (AST lock) | transform | `verification/test_main_market_data_skip_line_shape.py` | **exact** |
| `verification/test_main_higyrus_skip_line_shape.py` (NEW) | test (AST lock) | transform | `verification/test_main_market_data_skip_line_shape.py` | **exact** |
| `verification/test_main_verify_classification.py` (NEW) | test (unit, subprocess-free) | request-response (stdout → classification) | `verification/test_main_market_data_skip_line_shape.py` (imports `_ENV_SKIP`) | role-match |
| `packages/{iol,higyrus,matriz}-client/tests/test_deep_chain_edges.py` (NEW ×3) | test (mocked HTTP) | request-response | `packages/market-data-client/tests/test_snapshot_no_data_row.py` | **exact** |
| `main_iol.py` (MOD — D-03) | driver probe body | request-response | its own `probe_get_quote_sync` (`:637-729`) | **exact (self)** |
| `main_higyrus.py` (MOD — D-01 + D-04) | driver probe body + exit path | request-response | `main_higyrus.py:335-377` + D-01 shape from `env_gate.require_env` | **exact (self)** |
| `main_matriz.py` (MOD — D-02 + D-05 + D-09) | driver main gate + probe body | request-response | `main_matriz.py:2556-2566`, `:1006-1046`; D-09 from `main_market_data.py:3375-3412` | **exact** |
| `main_verify.py` (MOD — D-01) | harness runner | request-response (stdout scan) | itself, `:45-81` | **exact (self)** |
| `verification/test_cycle_closure_phase33.py` (MOD) | test | transform | itself (`_CENSUS` repoint at `:83-89`) | **exact (self)** |
| `.github/workflows/ci.yml` (MOD) | config | batch | `ci.yml:79-84` explicit allowlist | **exact (self)** |
| `.planning/phases/39-…/39-CENSUS.md` (NEW) | doc artifact | — | `38-CENSUS.md`, `33-CENSUS.md`, `35-RETIRED-TRIPLES.md` | role-match |

---

## Pattern Assignments

### `verification/test_main_{iol,higyrus,matriz}_deep_chain.py` (test, AST lock) — D-03/D-04/D-05

**Analog:** `verification/test_main_market_data_deep_chain.py` (269 lines, all 6 tests green).
Its own docstring names Phase 39 as its intended consumer. **Copy the module structure verbatim**
and change only the four module constants + the chain root attribute.

**Module header / imports** (`:29-42`) — no third-party imports, parse never import:
```python
from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

_ALIAS_NAMES = frozenset({"bids", "offers", "last", "settlement", "close", "open_interest"})
```

**The two copy-verbatim helpers** (`:91-121`) — do not re-derive these:
```python
def _protected_node_ids(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[int]:
    """Only the protected ``try`` body counts -- except/else/finally deliberately excluded."""
    protected: set[int] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                for descendant in ast.walk(stmt):
                    protected.add(id(descendant))
    return protected


def _chain_reaches(node: ast.expr, attribute: str) -> bool:
    """True if the receiver chain under ``node`` passes through ``.<attribute>``."""
    current: ast.expr | None = node
    while current is not None:
        if isinstance(current, ast.Attribute):
            if current.attr == attribute:
                return True
            current = current.value
        elif isinstance(current, ast.Subscript):
            current = current.value
        elif isinstance(current, ast.Call):
            current = current.func
        else:
            return False
    return False
```

**Probe-lookup + chained-access extraction** (`:124-147`):
```python
def _probe_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in _READ_PROBES:
            found[node.name] = node
    return found


def _chained_accesses(func) -> list[ast.Attribute]:
    return [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Attribute)
        and node.attr in _ALIAS_NAMES
        and _chain_reaches(node.value, "market_data")
    ]


def _driver_ast() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))
```

**The five test bodies to replicate** (`:150-268`), each with its full explanatory assert message:
1. `test_the_..._read_probes_are_present_by_name` — probe-name stability (findings are keyed on names).
2. `test_every_read_probe_consumes_the_typed_..._chain` — at least one real dereference per probe.
3. `test_every_chained_access_sits_inside_the_probe_try_body` — the D-09 never-FAILED contract
   (Pitfall 10); uses `_protected_node_ids`.
4. `test_the_deep_chain_lock_is_not_vacuous` — aggregate floor derived, never re-typed:
   `_MIN_CHAINED_ACCESSES = sum(_MIN_CHAINED_ACCESSES_BY_PROBE.values())`.
5. `test_each_probe_meets_its_own_floor` + `test_every_fetched_collection_is_chained` — WR-06:
   a per-probe floor plus a per-fetched-collection structural assertion, because an aggregate
   floor can be met 18/2/2/2.

**Per-file constants to substitute:**

| File | `_DRIVER` | chain root for `_chain_reaches` | `_ALIAS_NAMES` | `_READ_PROBES` |
|---|---|---|---|---|
| `test_main_iol_deep_chain.py` | `main_iol.py` | `puntas` | `{"precioCompra", "precioVenta", …}` | `probe_get_quote_{sync,async}`, `probe_get_instruments_by_type_{sync,async}` |
| `test_main_higyrus_deep_chain.py` | `main_higyrus.py` | `parking` (or chosen link) | `{"diasParking", …}` | the posiciones probes, both surfaces |
| `test_main_matriz_deep_chain.py` | `main_matriz.py` | the `MarketDataSnapshot` local | the **6** aliases, copied verbatim from the analog | `probe_get_market_data{,_async}` |

Note for iol (from RESEARCH Code Examples): `Cotizacion.puntas` is a **list** (`iol_client/models.py:235`)
while `Titulo.puntas` is a **singular `Punta` Null Object** (`:334`) — the lock must tolerate both
`quote.puntas[0].precioCompra` (Subscript, handled by `_chain_reaches`) and `titulos[0].puntas.precioCompra`.

For matriz the 6 aliases are `@property` views (`matriz_client/models.py:755-783`) and therefore
invisible to `walk_model` — dereferencing them adds **no** decode path and cannot change the
divergence count. The lock is pure observation, exactly as in the analog.

---

### `verification/test_main_{matriz,higyrus}_skip_line_shape.py` (test, AST lock) — D-01 / Pitfall 2

**Analog:** `verification/test_main_market_data_skip_line_shape.py` (201 lines).

**The load-bearing import — import the classifier, never re-declare it** (`:26`):
```python
from main_verify import _ENV_SKIP
```

**Hostile-render machinery** (`:31-40`, `:63-103`) — copy `_module_str_constants`, `_render`,
`_print_payloads` verbatim; they statically render every `print`/`safe_print` first argument,
substituting a hostile value into every f-string hole:
```python
_PRINTERS = frozenset({"safe_print", "print"})
_HOSTILE = "SKIPPED evil: pwned"
_MIN_PRINT_SITES = 2
```

**Positive + negative control** (`:146-153`) — this is what makes the guard non-vacuous:
```python
assert _ENV_SKIP.match(hostile_line) is None
assert _ENV_SKIP.match(f"SUMMARY: {_HOSTILE}") is None
# Control positivo: el guard NO es vacuo — la forma del env-gate SÍ matchea.
assert _ENV_SKIP.match("SKIPPED market-data-client: missing MARKET_DATA_CLIENT_ID")
```

**Inversion for Phase 39.** The analog asserts *no* driver line matches `_ENV_SKIP`. D-01
deliberately introduces exactly one intentional matching line per driver, so the matriz/higyrus
copies invert the final assertion: **exactly one** rendered line matches, it is the D-01 skip
line, and `_MUTATING_SKIP_DETAIL` (colon-free) still does not (`:132-143`).

---

### `verification/test_main_verify_classification.py` (test, unit) — D-01

**Analog:** the classifier itself, `main_verify.py:45-81`, plus the import idiom from the
skip-line shape guard.

**The exact contract under test** (`main_verify.py:42`, `:76-81`):
```python
_ENV_SKIP = re.compile(r"^SKIPPED \S.*:")
...
    for line in result.stdout.splitlines():
        if _ENV_SKIP.match(line):
            return "SKIPPED"
    if result.returncode != 0:
        return "FAILED"
    return "RAN"
```
Three facts the test must pin: (a) only **stdout** is scanned — matriz's ABORT currently goes to
`stderr` (Pitfall 4); (b) the colon is load-bearing — `SKIPPED (mutating, guard off)` must stay
unmatched (WR-01); (c) market-data and wallets classification is unchanged (`_DRIVERS` has
**six** entries, not the five its docstring claims).

---

### `packages/{iol,higyrus,matriz}-client/tests/test_deep_chain_edges.py` (test, mocked) — SC-2 / D-08

**Analog:** `packages/market-data-client/tests/test_snapshot_no_data_row.py` (335 lines).
These live under `packages/`, **not** `verification/` — that is the only tree CI's `test` job runs.

**Imports** (`:70-78`):
```python
from __future__ import annotations

from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import BookLevel, MarketDataDecodeError, aio
```

**Fixture pattern — the payload IS the committed baseline, verbatim** (`:80-100`, CR-02):
```python
# ``GET /marketdata/latest`` for a symbol the feed never delivered — the committed
# baseline ``.planning/verification/schemas/market-data-client/get-latest.json``
# VERBATIM ... Only the identifiers are synthesised (C-4).
_NO_DATA_ROW: dict[str, Any] = {
    "active": None, "market_data": None, "market_id": None,
    "note": "sin datos para el simbolo", "received_at": None,
    "staleness_seconds": None, "symbol": "AAA1",
}

# The same row with ONLY the two over-declared LEAVES populated, so the two LINKS
# are the only thing left that could raise.
_LINKS_ONLY_NO_DATA_ROW: dict[str, Any] = {**_NO_DATA_ROW, "market_id": "ZZZ", "active": False}

# A populated row — the non-regression control.
_POPULATED_ROW: dict[str, Any] = {...}
```
Three fixtures, always: the degenerate row, the isolating row, and a populated **control**.
Do not populate a field the baseline sends as `null` — CR-02 found exactly that defect and it
made the "assertion with teeth" green for the wrong reason.

**Edge matrix each of the three files must cover (D-12):** empty list / absent key / explicit
`null` / 204-empty-body — asserting no `AttributeError` and no `TypeError` on any chain, on
**both** surfaces (`import <pkg>` and `from <pkg> import aio`).

---

### `main_iol.py` (driver, request-response) — D-03

**Analog:** its own `probe_get_quote_sync` at `:637-729`. The chain is a **pure add inside the
existing `try`**; the exception ladder must not be reshaped.

**Probe signature + decorator** (`:637-648`):
```python
@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_quote"], surface="sync")
def probe_get_quote_sync(client: Client) -> tuple[ProbeResult, Cotizacion | None]:
    """Probe 3: ``client.get_quote(GGAL)`` (IOL-02).

    WR-03: single HTTP call por probe. WR-01: ``exc.status_code`` typed directo.
    """
    if _auth_failed:
        return (ProbeResult("get_quote_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"), None)
    base_url = client._state.base_url
    try:
        quote = client.get_quote(_SAMPLE_SYMBOL)
```

**Exception ladder to preserve** (`:652-702`) — the ordering is documented and load-bearing:
`IOLAuthError` → `IOLAPIError` → **`IOLDecodeError` ahead of the broad handler (P-4)** →
`except Exception`. The comment at `:682-685` explains why the decode branch must precede the
broad one (two probes on one divergence would produce two titles `idempotent_by_title` cannot
collapse). Reuse `_shape_probe_result_pair(name, surface, _redacted_exc(exc))` for decode.

**Typed-attribute idiom already established** (`:703-711`) — TYP-01, no defensive type guard:
```python
    ultimo = quote.ultimoPrecio
```
D-03 adds alongside it, **inside the same `try` body**:
```python
        book_bid = quote.puntas[0].precioCompra if quote.puntas else None
        n_levels = len(quote.puntas)
```
and at `:1114` / `:1264` (`probe_get_instruments_by_type_{sync,async}`), where `Titulo.puntas`
is a singular Null Object — branch on truthiness, no `None` guard:
```python
        first_bid = titulos[0].puntas.precioCompra if titulos else None
```

**Finding-emission pattern** (`:668-681`) — every new finding uses this exact keyword shape:
`append_finding(_PKG, fid=_next_fid(), class_=…, surface=…, status="OPEN", title=…, expected=…,
actual=_redacted_exc(exc), diff=…, base_url=base_url)`.

---

### `main_higyrus.py` (driver) — D-01 + D-04

**Analog for D-04 (typed chain, zero extra HTTP):** `_raw_request_sync` / `_raw_request_async`
at `:335-377`. Note the mirrored pair — sync and async are byte-for-byte parallel, and any D-04
addition must be added to **both**:
```python
def _raw_request_sync(client, method, path, *, params=None) -> dict | list | None:
    spec = RequestSpec(method=method, path=path, params=params)
    resp = client._request(spec)
    if not resp.is_success:
        raise_for_response(resp)
    if resp.status_code == 204 or not resp.content:
        return None
    body: dict[str, Any] | list[Any] = resp.json()
    return body
```
The 204/empty→`None` branch is the SC-2 edge case already handled — the typed chain added on top
must survive `rows is None`.

**D-04 insertion shape** (RESEARCH Pattern 2 — `Posicion.from_api` routes through the *same*
walker/sink as the client's own parser, so it costs zero HTTP and emits identical records):
```python
rows = _raw_request_sync(client, "GET", path, params=params)   # already there
payloads["get_posiciones"] = rows                               # already there
posiciones = [Posicion.from_api(r) for r in (rows or [])]       # NEW — same walker
n_parking = sum(len(p.parking) for p in posiciones)             # NEW — real chain
first_dias = posiciones[0].parking[0].diasParking if (posiciones and posiciones[0].parking) else None
```
`Posicion.parking: list[Parking]` at `higyrus_client/models.py:316`. Prefer it over
`Cuenta.domicilios` (`:463`): `get_listado_cuentas` returns `[]` live (finding F-02, NO-FIX, 3/3 runs).
CLAUDE.md: construct **only** via `Model.from_api(payload)`, never `Model(field=value)`.

**D-01 insertion shape** — must land **ahead of** the `_RESIDUAL_PROBE_EXCEPTIONS` bracket
(`:144-151`, caught at `:639`/`:703`) so no `append_finding` runs on the unreachable path
(Pitfall 3 — an `AUTH OPEN` finding also reddens `test_cycle_closure_phase33.py`'s
`assert "OPEN" not in statuses`):
```python
    except httpx.ConnectError:
        # Unreachability, not a divergence: no finding is written (Pitfall 3).
        print(f"SKIPPED {_PKG}: vendor host unreachable (DNS) — LIVE-HIGY-33")
        raise SystemExit(0) from None
```

---

### `main_matriz.py` (driver) — D-02 + D-05 + D-09

**D-02 analog:** the current gate at `:2556-2566`, kept in shape, widened to an explicit allowlist
and re-pointed to **stdout** with the colon (Pitfall 4):
```python
    client = Client(strict_decode=_STRICT)

    # D-MATZ-33 belt-and-suspenders hostname assert: prevention contra prod.
    base = client._state.base_url
    if "remarkets" not in base:
        print(f"ABORT: PRIMARY_BASE_URL={base!r} is not a remarkets sandbox URL — …", file=sys.stderr)
        sys.exit(1)
```
becomes exact-equality allowlist + stdout skip line (never `in`/`endswith`; `mutation_gate.py:85-90`
documents the `…com.ar.attacker.example` and userinfo attack classes). `_state.base_url` is
already `rstrip("/")`-normalised, so equality works as written. **Do not touch
`verification/mutation_gate.py`** — its remarkets-only `_SANDBOX_HOST` is what keeps order entry
fail-closed under bbsa, automatically.

Ordering contract to preserve (`:2568-2576`): `write_findings(_PKG)` < `_seed_fid_counter()` <
first probe — the same canonical order as iol/higyrus/market-data.

**D-05 analog:** `probe_get_market_data` at `:1006-1046`. It already extracts the raw dict and has
the market-hours discriminator; the snapshot construction is the gap:
```python
    md = raw.get("marketData")
    if not isinstance(md, dict):
        ...append_finding(class_="SHAPE", ...)
        return (ProbeResult("get_market_data", "FINDING", f"{fid} (OPEN)"), None)
    # D-MATZ-5 market-hours guard: inspecciona LA.date.
    la = md.get("LA")
    detail = f"symbol={_resolved_symbol}, entries={len(md)}"
    if isinstance(la, dict):
        la_date = la.get("date")
        if isinstance(la_date, int):
            stale_ms = int(time.time() * 1000) - la_date
            if stale_ms > 7200000:  # 2h
                ...append_finding(class_="NO-DATA", ...)
                detail = f"{detail} (stale LA.date by {stale_h:.1f}h — shape OK)"
    return (ProbeResult("get_market_data", "PASS", detail), md)
```
This `LA.date` staleness guard is the **D-12 market-closed vs mis-modelled discriminator** —
reuse it, do not invent a second one. The 6-alias dereference goes inside the same `try` body:
```python
    snap = MarketDataSnapshot.from_api(md)   # NEW, same walker, no second HTTP call
    last_px = snap.last.price; n_bids = len(snap.bids); n_offers = len(snap.offers)
    settle_px = snap.settlement.price; close_px = snap.close.price; oi_val = snap.open_interest.price
```
Mirror on the async surface at `:2013-2032` — **matriz has a real `aio.py` with a full
`AsyncClient.get_market_data`** and ~19 `surface="async"` probes; the RESEARCH note supersedes
CONTEXT D-05's REST+WS premise. `ws_client` is imported zero times by the driver.

**D-09 analog:** `main_market_data.py:3375-3412` — harden at the **probe** layer, never inside
`verification/cycle_report.py` (three tests pin its `(True, [])` contract):
```python
@probe_context(endpoint=_NO_ENDPOINT, surface="sync")
def probe_cycle_closure(client: Client) -> ProbeResult:
    name = "cycle_closure"
    base_url = client._state.base_url
    try:
        ok, missing = verify_cycle_closure(_PKG)
        path = findings_path(_PKG)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        n_closed = len(_CLOSED_STATUS_RE.findall(text))
        if ok and n_closed == 0:
            ok = False
            missing = ["<ningún finding CONFIRMED/FIXED: el cierre de ciclo sería vacuo>"]
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    if ok:
        return ProbeResult(name, "PASS", f"{n_closed} CONFIRMED/FIXED con regresión")
    ...append_finding(class_="ERROR-MAP", status="OPEN", ...)
    return ProbeResult(name, "FAIL", f"{fid} (OPEN) missing: {', '.join(missing)}")
```
**Copy the structure, NOT the predicate.** `n_closed == 0 → FAIL` fails ámbito (0) and higyrus (0)
for being clean (Pitfall 6). Substitute the probe-count evidence predicate argued in
`test_cycle_closure_phase33.py:200-225`. matriz's existing 4-package loop at `:2653-2682` is the
cheapest seam — it already covers ámbito/iol/higyrus/matriz.

**Pitfall 5:** the terminal EXPECTED finding at `:2691-2709` ("verification limited to remarkets
sandbox by safety policy") becomes false under D-02 and cites a `REQUIREMENTS.md` row that no
longer exists. Update in the same commit; `idempotent_by_title=True` means a new title creates a
**new** finding, so the superseded one needs an explicit disposition.

---

### `verification/test_cycle_closure_phase33.py` (test, MOD) — D-09

**Analog:** itself. One-line repoint of `_CENSUS` (`:83-89`) from `.planning/phases/33-…/` to
`.planning/milestones/v1.6-phases/33-…/33-CENSUS.md` turns 2 red green. Then extend using the
file's own established idioms: `_PRE_PHASE_BASELINE` / `_PHASE_33_PROMOTIONS` /
`_LOWER_BOUND = {pkg: base + promo}`, plus `_assert_zero_contribution_is_argued` (`:191-254`) —
the pattern that **refuses to write a `>= 0` floor** and demands an argued exemption instead, and
`test_the_two_exemptions_are_the_only_ones` (`:257-268`), which pins the exemption set so a third
package cannot drift into it.

---

### `.planning/phases/39-…/39-CENSUS.md` (doc) — D-10 / D-11

**Analog:** `38-CENSUS.md` — opens by naming the failure mode ("three empty tables read as a clean
bill of health nobody earned"), scopes explicitly with an out-of-scope table naming *where each
excluded package is audited instead*, and transcribes the **verbatim executed command + output +
`echo $?`** that every disposition cell cites. Reuse: enumerate the full candidate population
(not only violations), report structural zeros as **"zero by enumeration"** with the cause named,
and state the unit column explicitly — distinct triples `(slug, model, field_path, kind)` from
`DivergenceHandler.seen`, never `FINDING=N` and never raw findings-file blocks (documented ~2×
per-surface duplication).

---

## Shared Patterns

### Probe declaration + never-FAILED contract (D-09)
**Source:** `main_market_data.py:3375-3396`, `main_iol.py:637-702`, `main_matriz.py:959-1046`
**Apply to:** every driver edit in this phase
```python
@probe_context(endpoint=_ENDPOINT_TEMPLATES["<name>"], surface="sync")
def probe_<name>_sync(client: Client) -> ProbeResult:
    name = "<name>"
    base_url = client._state.base_url
    try:
        ...                                  # ALL deep-chain dereferences go HERE
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
```
Every dereference in the `try` **body** — not `except`/`else`/`finally`. Pinned by
`_protected_node_ids` in each AST lock (Pitfall 10).

### Finding emission (git-committed public artifact — metadata only, never a wire value)
**Source:** `main_iol.py:668-681`, `main_matriz.py:1033-1044`
**Apply to:** any new `append_finding` call
```python
fid = _next_fid()
append_finding(
    _PKG, fid=fid, class_="SHAPE", surface="sync", status="OPEN",
    title="<stable, dedupe key under idempotent_by_title>",
    expected="...", actual=_redacted_exc(exc), diff="...", base_url=base_url,
)
return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
```

### Skip-line shape (D-01 / Pitfall 2)
**Source:** `verification/env_gate.py:32-41`; classifier `main_verify.py:42`
**Apply to:** both new D-01 skip sites
```
SKIPPED <pkg>: <measured cause> — <named destination>
```
**stdout** (only stdout is scanned), colon present, non-space token right after `SKIPPED`,
no `append_finding` on the path. Probe-level skips stay colon-free
(`SKIPPED (mutating, guard off)`).

### Sync/async mirroring (CLAUDE.md, mandatory)
**Source:** `main_higyrus.py:335-359` vs `:362-377`; `main_matriz.py` sync `:959-1046` vs async `:2013-2032`
**Apply to:** D-03, D-04, D-05, and every D-08 in-cycle fix (both `client.py` **and** `aio.py`)

### Module conventions (CLAUDE.md, all new files)
`from __future__ import annotations` first; ruff line-length 100, double quotes, 4 spaces;
no relative or wildcard imports; mypy strict (full annotations on every new helper);
`S101` exempt only under `**/tests/**` — which is why the AST locks live in test files.

### CI wiring (the silent one — Anti-Pattern #1)
**Source:** `.github/workflows/ci.yml:79-84`
```yaml
        run: |
          uv run pytest -q \
            verification/test_main_market_data_deep_chain.py \
            verification/test_safemodel_diff_null_object_links.py \
            verification/test_main_matriz_risk_envelope_keys.py \
            verification/test_safemodel_diff_mapping_recursion.py
```
`verification/` **never** runs as a directory in CI — the `test` job passes an explicit path that
overrides `testpaths`. Every new file under `verification/` must be appended to this hand-maintained
list **in the same commit** or it ships inert. This has already happened once, to this exact kind
of guard (Phase 36 WR-01). Mocked regressions belong under `packages/<pkg>/tests/`, which CI does run.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| triple-dump seam for `handler.seen` (Pattern 4, location undecided) | utility | transform | All four drivers print `DIVERGENCES={len(handler.seen)}` — a **count**. No existing code ever persists the members, which is what D-10's set difference requires. RESEARCH offers two seams (dump `sorted(handler.seen)` to JSON after the `divergence_capture` block; or re-derive by parsing SHAPE titles, `divergences.py:176`) — seam 2 is how `33-CENSUS.md` was actually built and is the cross-check, but neither exists as code. Planner picks; privacy-safe either way (a triple is metadata only). |

---

## Metadata

**Analog search scope:** repo root drivers (`main_*.py`), `verification/`, `packages/*/tests/`,
`packages/*/src/*/models.py`, `.github/workflows/ci.yml`, `.planning/**/*CENSUS*.md`
**Files read in full or in targeted range:** 11
**Pattern extraction date:** 2026-08-29
