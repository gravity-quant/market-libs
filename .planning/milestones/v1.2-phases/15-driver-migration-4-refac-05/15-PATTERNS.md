# Phase 15: Driver Migration × 4 (REFAC-05) - Pattern Map

**Mapped:** 2026-06-24
**Files analyzed:** 8 (4 drivers MODIFIED + 4 AST tests CREATED)
**Analogs found:** 8 / 8 (every file has a concrete in-repo analog)

> Read-only analysis. No source files were modified. This document maps each new/modified
> file to its closest existing analog with copy-ready excerpts and exact line references.

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `main_ambito_financiero.py` (MOD) | driver/script | request-response | itself (in-place mechanical refactor) | self / exact |
| `main_iol.py` (MOD) | driver/script | request-response | `main_ambito_financiero.py` (simplest precedent) | exact |
| `main_higyrus.py` (MOD) | driver/script | request-response | `main_iol.py` (same sync+async interleave) | exact |
| `main_matriz.py` (MOD) | driver/script | request-response (async-only `aio`) | `main_iol.py` `_async_main`/batch | exact |
| `verification/test_main_ambito_financiero_uses_single_client_instance.py` (NEW) | test (AST guard) | static-analysis | `verification/test_main_drivers_bare_except.py` | exact (only AST-walker in repo) |
| `verification/test_main_iol_uses_single_client_instance.py` (NEW) | test (AST guard) | static-analysis | `verification/test_main_drivers_bare_except.py` | exact |
| `verification/test_main_higyrus_uses_single_client_instance.py` (NEW) | test (AST guard) | static-analysis | `verification/test_main_drivers_bare_except.py` | exact |
| `verification/test_main_matriz_uses_single_client_instance.py` (NEW) | test (AST guard) | static-analysis | `verification/test_main_drivers_bare_except.py` | exact |

**Note on D-04 layout:** CONTEXT D-04 says ONE test per driver. The closest analog
(`test_main_drivers_bare_except.py`) parametrizes ONE test function over a `_DRIVERS` list.
The planner may either (a) keep 4 separate files named `test_main_<pkg>_uses_single_client_instance.py`
(matches the ROADMAP SC#1 naming `test_main_<pkg>_uses_single_client_instance`), or (b) collapse to one
parametrized file. **Recommended: 4 files** — the ROADMAP names them per-pkg and D-05 requires per-driver
constructor-style pinning, which is cleaner as a per-file constant than a parametrize lookup table.

---

## Pattern Assignments

### `verification/test_main_<pkg>_uses_single_client_instance.py` (test, AST guard) ×4

**Analog:** `verification/test_main_drivers_bare_except.py` — the ONLY AST-walker in the repo.
Read in full (52 lines); copy its complete idiom.

**Module header + `_REPO_ROOT` + parametrize idiom** (`test_main_drivers_bare_except.py:17-29`):
```python
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVERS = ["main_matriz.py", "main_higyrus.py"]


@pytest.mark.parametrize("driver", _DRIVERS)
def test_no_bare_except_in_driver(driver: str) -> None:
```
Note: `_REPO_ROOT = Path(__file__).resolve().parent.parent` — the test lives in `verification/`,
so `.parent.parent` reaches the repo root where the `main_*.py` drivers live.

**`ast.parse` + `ast.walk` body** (`test_main_drivers_bare_except.py:39-51`):
```python
tree = ast.parse((_REPO_ROOT / driver).read_text(encoding="utf-8"))
bare_sites: list[tuple[int, str]] = []
for node in ast.walk(tree):
    if not isinstance(node, ast.ExceptHandler):
        continue
    if node.type is None:
        bare_sites.append((node.lineno, "<bare except:>"))
        continue
    if isinstance(node.type, ast.Name) and node.type.id == "Exception":
        bare_sites.append((node.lineno, "except Exception"))
assert not bare_sites, f"{driver} has {len(bare_sites)} bare-except site(s): {bare_sites}"
```

**ADAPT for Phase 15** — the new test counts `Client()` / `AsyncClient()` constructor CALLS and asserts
`≤ 2` per driver. The walker iterates `ast.Call` nodes and inspects `node.func`:

```python
# CONSTRUCTOR-STYLE MATCHING (D-05) — match BOTH forms:
_CTOR_NAMES = {"Client", "AsyncClient"}
ctor_sites: list[tuple[int, str]] = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    func = node.func
    # bare:   `Client(...)` / `AsyncClient(...)`  -> ast.Name(id=...)
    if isinstance(func, ast.Name) and func.id in _CTOR_NAMES:
        ctor_sites.append((node.lineno, func.id))
    # module-qualified: `iol_client.Client(...)` -> ast.Attribute(attr=...)
    elif isinstance(func, ast.Attribute) and func.attr in _CTOR_NAMES:
        ctor_sites.append((node.lineno, func.attr))
assert len(ctor_sites) <= 2, f"{driver}: expected <=2 Client/AsyncClient ctors, got {ctor_sites}"
```

**CRITICAL (D-05 — false-green trap):** The walker MUST match the SAME constructor style the driver
actually emits. If the plan makes the driver use module-qualified `iol_client.Client(...)`
(`ast.Attribute`) but the walker only checks `ast.Name`, the gate counts ZERO ctors and passes
vacuously. **The plan MUST pin the import/construction style per driver and the walker MUST cover it.**
The excerpt above covers BOTH styles, so it is safe regardless of which the plan picks — but the plan
should still document the chosen style so the count is meaningful.

**`with_options()` is NOT a constructor (D-04):** `client.with_options(max_retries=N)` parses as
`ast.Call(func=ast.Attribute(attr="with_options"))` — `attr` is `"with_options"`, not in `_CTOR_NAMES`,
so it is correctly NOT counted. Views stay unlimited.

**Optional `FunctionDef` scoping (Claude's Discretion / D-05 tail):** whole-file `ast.walk` is the
analog's default and is sufficient IF no module-level helper constructs a `Client`. If the plan adds a
threading helper that itself constructs (it should NOT — D-01 puts construction in `main()`/`_async_main()`),
scope the walk to the `main()` / `_async_main()` `ast.FunctionDef` bodies instead. Inspect the final driver
shape before deciding; default to whole-file.

---

### `main_ambito_financiero.py` (driver, sync+async; SIMPLEST — migrate FIRST per D-11)

**Analog:** itself (in-place mechanical refactor). 734 LOC, 7 probes, 1 async probe.

**Current import block** (`main_ambito_financiero.py:48-54`) — module-qualified alias style:
```python
import httpx
from verification import safe_print, schema_of, write_findings
from verification.findings import append_finding

import ambito_financiero_client as ambito
from ambito_financiero_client import aio
from ambito_financiero_client._parsing import parse_ar_decimal
```
The package exports `Client` and `AsyncClient` from the flat namespace
(`ambito_financiero_client/__init__.py:50-51`). Plan adds EITHER
`from ambito_financiero_client import Client, AsyncClient` (bare → `ast.Name`) OR constructs
`ambito.Client(...)` / `ambito.AsyncClient(...)` (module-qualified → `ast.Attribute`). **Pin one.**

**Current probe signature — NO client param** (`main_ambito_financiero.py:131`, sync; `:219`, async):
```python
def probe_happy_sync(today: dt.date) -> tuple[ProbeResult, list[list[str]] | None]:
    ...
    base_url = ambito.client._get_default()._state.base_url  # post-refactor accessor  # :141
    ...
        resp = ambito.client._request("GET", path)  # :150  -> migrate to client._request(...)
```
```python
async def probe_happy_async(today: dt.date) -> tuple[ProbeResult, float | None]:
    ...
    base_url = aio._get_default()._state.base_url  # post-refactor accessor  # :228
    ...
        resp = await aio._request("GET", path)  # :235  -> await aclient._request(...)
```

**Migration per D-01/D-03 (mechanical 1:1):**
- Add `client` (sync) / `aclient` (async) parameter to each `probe_*` signature.
- `ambito.client._get_default()._state.<attr>` → `client._state.<attr>` (8 code reads; see counts below).
- `ambito.client._request(...)` → `client._request(...)`; `aio._request(...)` → `aclient._request(...)`.
- Public wrapper calls `ambito.get_dollar_banco_nacion(...)` (`:458`, `:580`) → `client.get_dollar_banco_nacion(...)`.

**`_state` read sites** (`main_ambito_financiero.py`): `:141, :228, :318, :375, :456, :510, :575, :576`
= **8 code reads** (matches CONTEXT "~8"). **DO NOT rewrite docstring occurrences** `:561, :563`
(operator-facing prose, D-03 explicitly leaves these intact).

**`_async_main` + `aclose` structure (the template all 4 drivers share)**
(`main_ambito_financiero.py:661-679`):
```python
async def _async_main(today: dt.date) -> tuple[ProbeResult, float | None]:
    try:
        result, precio_async = await probe_happy_async(today)
    finally:
        with contextlib.suppress(Exception):
            await aio.aclose()          # MIGRATE -> await aclient.aclose()
    return result, precio_async
```
Post-migration: construct `aclient = AsyncClient()` (or `ambito.AsyncClient()`) at the TOP of
`_async_main`, thread it into `probe_happy_async(today, aclient)`, and call `await aclient.aclose()` in
the `finally`. The single-`asyncio.run` invariant is already in place (`:701`).

**`main()` invocation pattern** (`main_ambito_financiero.py:687-701`):
```python
def main() -> None:
    today = dt.date.today()
    write_findings(_PKG)
    results: list[ProbeResult] = []
    result_happy_sync, rows_sync = probe_happy_sync(today)      # -> probe_happy_sync(today, client)
    results.append(result_happy_sync)
    result_happy_async, precio_async = asyncio.run(_async_main(today))   # AsyncClient lives inside
    results.append(result_happy_async)
    ...
```
Post-migration: construct `client = Client()` (or `ambito.Client()`) once near the top of `main()`,
thread it as a parameter into every sync probe call. Sync `Client` and async `AsyncClient` are SEPARATE
instances (D-02) — NEVER share the sync `httpx.Client` into the async coroutine.

---

### `main_iol.py` (driver, sync+async; migrate SECOND — contains the CRITICAL write-site)

**Analog:** `main_ambito_financiero.py` migration above (same sync-probe + single-`asyncio.run` shape).
1675 LOC, 15 probes.

**Current import block** (`main_iol.py:74-78`):
```python
from verification import require_env, safe_print, schema_of, write_findings
from verification.findings import append_finding

import iol_client
from iol_client import IOLAPIError, IOLAuthError, aio
```
`Client`/`AsyncClient` exported at `iol_client/__init__.py:55-56`. Add `from iol_client import Client, AsyncClient`
(bare) OR construct `iol_client.Client(...)` (module-qualified). **Pin one for the AST walker.**

**Public call sites** — sync `iol_client.get_X(...)`, async `await aio.get_X(...)`:
- `iol_client.login()` `:193`; `await aio.login()` `:228`
- `iol_client.get_quote(...)` `:267`; `await aio.get_quote(...)` `:345`
- `iol_client.get_historical_quotes(...)` `:413`; `await aio.get_historical_quotes(...)` `:491`
- `iol_client.get_instruments(...)` `:561, :757, :1296`; `await aio.get_instruments(...)` `:622`
- `iol_client.get_instruments_by_type(...)` `:697`; `await aio.get_instruments_by_type(...)` `:807`
- raw transport `iol_client.client._request(...)` `:972`

`Client` exposes all these methods: `login` (`iol_client/client.py:359`), `get_quote` (`:497`),
`get_historical_quotes` (`:512`), `get_instruments` (`:532`), `get_instruments_by_type` (`:541`) —
drop-in for `iol_client.get_X(...)` → `client.get_X(...)`.

**`_state` read sites** (17 total — matches CONTEXT "iol 17"):
`:191, :226, :265, :343, :408, :487, :559, :620, :695, :805, :894, :962, :1195, :1270, :1294 (WRITE), :1415`
plus module-attr reads at `:1271` (`iol_client.client._refresh_token`) and `:1287`
(`iol_client.client._token`).

**CRITICAL write-site (D-03) — `main_iol.py:1261-1296` `probe_refresh_token`:**
```python
def probe_refresh_token() -> ProbeResult:
    ...
    base_url = iol_client.client._get_default()._state.base_url               # :1270 -> client._state.base_url
    refresh_before = iol_client.client._refresh_token                        # :1271 -> client._state.refresh_token
    ...
    token_before = iol_client.client._token                                  # :1287 -> client._state.token
    # INT-01 idiom (quick task 260613-nwb): write via _get_default()._state.X
    iol_client.client._get_default()._state.token_expires_at = 0.0           # :1294 -> client._state.token_expires_at = 0.0
    try:
        iol_client.get_instruments("argentina")                              # :1296 -> client.get_instruments("argentina")
```
The forced-refresh write at `:1294` and the subsequent `get_instruments` read at `:1296` MUST operate on
the **same threaded `client` instance** — otherwise the write is a no-op against the wrong object and the
forced-refresh regression is silenced (a real regression passes unseen). This is the most sensitive single
line in the phase.

**Module-attr allowlist confirmation:** `iol_client/client.py:725` maps `"_refresh_token": "refresh_token"`,
so `iol_client.client._refresh_token` (`:1271`) and `_token` (`:1287`) correspond to
`client._state.refresh_token` / `client._state.token` on the migrated instance.

**`_async_main` batch** (`main_iol.py:1511-1548`) — multiple async probes share one `asyncio.run`;
`await aio.aclose()` at `:1537` in `finally` → `await aclient.aclose()`. Construct `aclient = AsyncClient()`
at the top of `_async_main`, thread into all 5 async probes. `main()` `:1556-1584` constructs `client`
once and threads it into every sync probe.

---

### `main_higyrus.py` (driver, sync+async; migrate THIRD — most probes)

**Analog:** `main_iol.py` migration (identical sync N / async N+1 interleave; same single-`asyncio.run`).
2458 LOC, ~19 probes.

**Current import block** (`main_higyrus.py:107-110`):
```python
import higyrus_client
from higyrus_client import HigyrusAPIError, HigyrusAuthError, HigyrusClientError, aio
from higyrus_client._params import format_bool, format_date
from higyrus_client.models import (...)
```
`Client`/`AsyncClient` at `higyrus_client/__init__.py:76-77`. Add bare import OR construct
`higyrus_client.Client(...)`. **Pin one.**

**Public + raw-transport call sites:** `higyrus_client.login()` `:464`; `await aio.login()` `:517`;
`higyrus_client.client._request(...)` `:576, :743, :990`; `higyrus_client.get_movimientos(...)` `:318`;
`await aio._request(...)` `:649, :889`; `await aio.get_movimientos(...)` `:371`.
`Client` exposes the same methods (`higyrus_client/client.py:96` class; `get_*`/`login` methods present).

**Method-on-default to migrate** — `main_higyrus.py:343`:
```python
await aio._get_default()._ensure_http_client()   # -> await aclient._ensure_http_client()
```
This is a method CALL on the async default, not just a `_state` read — migrate to the threaded `aclient`.

**`_state` read sites** (19 total — matches CONTEXT "~19"):
`:462, :515, :574, :647, :741, :887, :986, :1090, :1204, :1318, :1451, :1558, :1666, :1713, :1879, :1950,
:2036, :2137, :2421`. (Mixed sync `higyrus_client.client._get_default()._state` and async
`aio._get_default()._state`.)

**`_async_main` batch** (`main_higyrus.py:2214-2275`, single `asyncio.run` at `:2394`):
`await aio.aclose()` at `:2275` → `await aclient.aclose()`. Note the docstring at `:2225` flags an
existing `configure()`/`_token`-reset interaction — D-03 is a mechanical `_state`-access swap and does NOT
touch `configure()`. `main()` at `:2296`/`:2394` constructs `client` once and threads into sync probes.

---

### `main_matriz.py` (driver; ASYNC-only `aio` surface; migrate FOURTH — TokenStore-sensitive)

**Analog:** `main_iol.py` `_async_main` batch (matriz has a full `aio.py` at
`packages/matriz-client/src/matriz_client/aio.py`, 40KB — CONTEXT's "no aio.py" note is stale; the
async surface DOES exist and the driver uses `aio.get_X`). 2283 LOC.

**Current import block** (`main_matriz.py:79-84`):
```python
import matriz_client as primary
from matriz_client import PrimaryAPIError, aio
from matriz_client.client import _request as _matriz_request
from matriz_client.client import _risk_auth
from matriz_client.exceptions import AuthenticationError
from matriz_client.models import (...)
```
`Client`/`AsyncClient` at `matriz_client/__init__.py:112,117`. Add bare import OR construct
`primary.Client(...)` / `primary.AsyncClient(...)`. **Pin one.**

**Sync `main()` `_base_url` read — DISTINCT from `_state` idiom** (`main_matriz.py:2079-2080`):
```python
base = primary.client._base_url      # PEP 562 module attr, NOT _state -> client._state.base_url
if "remarkets" not in base:
```
This sync read happens directly in `main()` (safety hostname assert). It migrates to
`client._state.base_url` on the sync `Client` constructed in `main()`. (Sync surface also uses
`primary.login()` `:464`, `primary.get_market_data(...)` `:1138`, `primary.get_active_orders(...)` `:1216`,
`primary.get_instruments_by_cfi(...)` `:1295` → `client.get_X(...)`; `Client` methods at
`matriz_client/client.py:113` class, `login` `:307`, `get_segments` `:494`, etc.)

**Async `_state` read sites** (6 total — matches CONTEXT "matriz 6 async"):
`:1468, :1524, :1606, :1779, :1855, :1931` — all `aio._get_default()._state.base_url`.
Migrate each to `aclient._state.base_url`.

**`_ainvoke` helper pattern (matriz-specific — the lambda-wrapped async call)**
(`main_matriz.py:1524-1560`, plus call-sites `:1565-1738`):
```python
base_url = aio._get_default()._state.base_url            # :1524 -> aclient._state.base_url
result = await coro_factory()
...
async def probe_get_segments_async() -> ProbeResult:
    return await _ainvoke("get_segments_async", aio.get_segments)   # -> thread aclient through _ainvoke
```
The async probes pass `aio.get_X` (or `lambda: aio.get_X(args)`) into `_ainvoke`. Migration must thread
`aclient` so these resolve to `aclient.get_X` / `lambda: aclient.get_X(args)`. **Claude's Discretion (D-01
tail):** the threading mechanism (signature param on `_ainvoke` + each `probe_*_async`, vs a closure
capturing `aclient`) is the planner's call, provided the AST gate counts exactly one `AsyncClient()` ctor.

**`_async_main` batch** (`main_matriz.py:2011-2047`): 22 async probes, single `asyncio.run`,
`await aio.aclose()` at `:2046` → `await aclient.aclose()`. Construct `aclient = AsyncClient()` once at the
top of `_async_main`. **CRITICAL (anti-Pitfall 1):** matriz TokenStore is a 3-way concurrency primitive —
constructing >1 `AsyncClient` risks TokenStore corruption / OAuth churn. This is exactly why the
`≤ 2 ctors` gate exists. `main()` at `:2055` constructs the sync `client` once.

---

## Shared Patterns

### Library `Client` / `AsyncClient` constructors (all-optional kwargs → bare drop-in)

**Source (sync):** `iol_client/client.py:31-70`, `higyrus_client/client.py:104-144`,
`matriz_client/client.py:127-166`, `ambito_financiero_client/client.py:77`.
**Source (async):** `iol_client/aio.py:97-118`, `matriz_client/aio.py:155-194`,
`higyrus_client/aio.py`, `ambito_financiero_client/aio.py:30` (export).
**Apply to:** all 4 driver `main()` (sync) and `_async_main()` (async).

Every `__init__` takes ONLY optional keyword args and builds an env-driven `_ClientState()`:
```python
# iol_client/client.py:31,46
def __init__(self, *, base_url=None, username=None, password=None, token=None, ...):
    self._state = _ClientState()        # :46  env-driven defaults when kwargs omitted
    if base_url is not None:
        self._state.base_url = base_url.rstrip("/")
    ...
```
Therefore **bare `Client()` / `AsyncClient()` (no args) is a direct drop-in for `_get_default()`** — the
no-arg constructor reproduces the env-driven default singleton's state (D-01/D-10: minimal construction,
no `with_options`/`from_env` showcasing). Public methods on the instance (`client.get_quote(...)`,
`client.login()`, `aclient.get_segments()`) replace the top-level `pkg.get_X(...)` delegators 1:1.

### `_state` direct access (replaces the INT-01 `_get_default()._state` idiom)

**Source:** every `Client`/`AsyncClient` stores per-instance state on `self._state` (a `_ClientState`):
`iol_client/client.py:46`, `matriz_client/aio.py:168`, `higyrus_client/client.py:118`,
`matriz_client/client.py:140`.
**Apply to:** every `_get_default()._state.<attr>` read (and the one write at `main_iol.py:1294`).

Mechanical 1:1 swap (D-03):
```text
ambito.client._get_default()._state.base_url   ->  client._state.base_url
aio._get_default()._state.base_url             ->  aclient._state.base_url
iol_client.client._refresh_token               ->  client._state.refresh_token   (allowlist client.py:725)
iol_client.client._token                       ->  client._state.token
iol_client.client._get_default()._state.token_expires_at = 0.0
                                               ->  client._state.token_expires_at = 0.0   (WRITE — same instance!)
primary.client._base_url                       ->  client._state.base_url
```

### Finding-title / probe-name stability (D-06 — CRITICAL merge gate)

**Source:** `verification/findings.py:192` (`_DETAIL_HEADER_RE` parses `### F-NN -- <title>`) +
`:595-603` (content-addressed dedupe by title).
**Apply to:** every `append_finding(...)` call inside every migrated probe — DO NOT touch them.

```python
# verification/findings.py:599-603  — idempotent_by_title dedupe
if idempotent_by_title:
    for existing_finding in findings_list:
        if existing_finding.title == title:
            path.write_text(_replace_art_block(text, art), encoding="utf-8")
            return path   # no-op except ART refresh — finding stays byte-identical
```
The migration changes ONLY how the client is acquired (the call target + the source of the `base_url=`
value) — it NEVER changes the `title=` / `fid=` / `class_=` / `surface=` / probe-name string literals
passed to `append_finding(...)`. Identical titles ⇒ dedupe path ⇒ byte-identical BEGIN/END auto-zones ⇒
`git diff baseline..HEAD -- .planning/verification/*-findings.md` reports zero title/fid changes (gate
verified STATICALLY per D-07; no live re-run — `actual=`/`diff=` bytes are non-deterministic and out of
scope until Phase 17). `append_finding`'s `title` must stay single-line (`findings.py:573` raises on `\n`).

### `_async_main` + `await aclient.aclose()` lifecycle (D-02 separation)

**Source pattern:** `main_ambito_financiero.py:661-679` (canonical), mirrored at `main_iol.py:1511-1548`,
`main_higyrus.py:2214-2275`, `main_matriz.py:2011-2047`.
**Apply to:** all 4 `_async_main()` bodies.

```python
async def _async_main(...) -> ...:
    aclient = AsyncClient()              # NEW: one AsyncClient per asyncio.run (D-02)
    try:
        ... await probe_*_async(..., aclient) ...
    finally:
        with contextlib.suppress(Exception):   # D-04: teardown failure must not crash exit 0
            await aclient.aclose()       # was: await aio.aclose()
    return ...
```
The sync `Client()` is constructed in `main()` and is a SEPARATE instance — NEVER pass the sync
`httpx.Client` into the async coroutine (CLAUDE.md anti-pattern: event-loop violation). The `≤2 ctors`
gate (1 sync + 1 async) explicitly accommodates this split.

---

## No Analog Found

None. Every modified driver is an in-place refactor of itself, and every new AST test has an exact analog
in `verification/test_main_drivers_bare_except.py`. RESEARCH.md was skipped; it is not needed — all
patterns are concrete in-repo.

---

## Metadata

**Analog search scope:** repo root `main_*.py` drivers; `verification/` (AST test + findings);
`packages/*/src/*/client.py` + `aio.py` + `__init__.py` (Client/AsyncClient surface).
**Files scanned:** 4 drivers, 1 AST-test analog, 1 findings module, 8 library client/aio/init files.
**Constructor-style note (D-05):** all 4 packages export `Client` AND `AsyncClient` from the flat
namespace; all 4 drivers currently use `import <pkg> as <alias>` + `from <pkg> import aio`. NONE currently
import the class — the plan MUST add the import (bare → `ast.Name`, or qualified `alias.Client` →
`ast.Attribute`) and the AST walker MUST match whichever style is chosen. The recommended walker excerpt
above matches BOTH, eliminating the false-green risk.
**Pattern extraction date:** 2026-06-24
