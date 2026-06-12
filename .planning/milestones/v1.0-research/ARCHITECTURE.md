# Architecture Research

**Domain:** Live-API verification harness for a uv-workspace monorepo of Python HTTP client libraries
**Researched:** 2026-05-26
**Confidence:** HIGH (grounded in the existing codebase map and read of the actual source/scripts; no external lookups needed — this is an internal-structure decision, not an ecosystem survey)

> Scope note: "Architecture" here means **how to structure the verification effort/harness**, not the architecture of the client libraries (already documented in `.planning/codebase/ARCHITECTURE.md`). This document builds on that map and does not redefine it.

---

## Standard Architecture

### System Overview

The harness is a **thin per-package driver** layered on top of the unchanged client libraries. It has three distinct concerns that must not bleed into each other: (1) *exercising* the live surface, (2) *fixing* the client, (3) *locking in* the fix with a mock.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    VERIFICATION DRIVERS (repo root)                    │
│   main_iol.py   main_higyrus.py   main_matriz.py   main_ambito_*.py    │
│   ─ exercise FULL public surface, sync (client.py) + async (aio.py)    │
│   ─ read-only by default; mutating calls gated behind a flag           │
│   ─ emit a structured findings record (call / expected / actual / cls) │
└───────────┬───────────────────────────────────────────┬──────────────┘
            │ imports (unmodified)                        │ writes
            ▼                                             ▼
┌────────────────────────────┐              ┌────────────────────────────┐
│   CLIENT LIBRARIES          │              │   FINDINGS RECORD           │
│   packages/<pkg>/src/...     │  finding →   │   .planning/verification/   │
│   client.py  +  aio.py       │   FIX        │   <pkg>-findings.md         │
│   (the system under test)    │ ◀──────────  │   (per-run, human-readable) │
└────────────┬───────────────┘              └─────────────┬──────────────┘
             │ live HTTP (httpx)                            │ each fix →
             ▼                                              ▼
┌────────────────────────────┐              ┌────────────────────────────┐
│  EXTERNAL FINANCIAL APIs     │             │  REGRESSION TESTS (mocked)  │
│  IOL · Higyrus · Primary     │  capture →   │  packages/<pkg>/tests/      │
│  Ámbito (no auth)            │  payload     │  test_client.py /           │
│                              │              │  test_async_client.py       │
└──────────────────────────────┘             │  (pytest-httpx, frozen)     │
                                              └─────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Verification driver** (`main_<pkg>.py`) | Exercise the full public surface live; classify each result; print a readable transcript; emit a findings record | Plain script, no new deps; sync block + `asyncio.run()` async block; helper `check()` wrapper |
| **Credential gate** | Detect whether a package's creds are present; skip the whole package cleanly if not (Ámbito always runs) | `os.getenv` checks at top of each driver, or `configure()`-then-probe; explicit `SKIPPED (no creds)` line |
| **Read-only / mutating gate** | Run read-only calls by default; require an explicit opt-in for `new_order`/`replace_order`/`cancel_order` (matriz) | Env var `VERIFY_MUTATING=1` (or CLI flag); destructive block prints `SKIPPED (mutating, set VERIFY_MUTATING=1)` |
| **Findings record** | Durable, human-readable log of what was called, expected vs actual, and a discrepancy class | Markdown file per package under `.planning/verification/` |
| **Client fix** | Correct the divergence in `client.py` **and** mirror in `aio.py` (dual-surface invariant) | Edit within the package only — no cross-package deps |
| **Regression test** | Freeze the real payload as a `pytest-httpx` mock so the bug cannot return | New `test_*` in the package's existing `tests/`, with a `Regression:` docstring |

The **boundary that matters most**: the driver is *disposable scaffolding* that may stay messy; the client fix and the regression test are *durable artifacts* that must pass mypy strict + ruff (line-length 100) + CI. Keep findings/driver code out of the package wheels (root scripts are never distributed — confirmed in STRUCTURE.md).

---

## Recommended Project Structure

```
market-libs/
├── main_ambito_financiero.py   # driver: get_dollar_banco_nacion (sync+async), no creds
├── main_higyrus.py             # driver: health, cuentas, movimientos, posiciones (sync+async)
├── main_iol.py                 # driver: quote, historical, instruments, by_type (sync+async)
├── main_matriz.py              # driver: read-only REST surface + GATED order surface (sync only)
│
├── packages/<pkg>/.env         # per-package creds (gitignored; never logged)
├── packages/<pkg>/.env.example # template (committed)
│
├── packages/<pkg>/tests/       # regression tests land HERE (existing convention)
│   ├── test_client.py          #   ← add regression test (sync)
│   └── test_async_client.py    #   ← mirror regression test (async)
│
└── .planning/
    └── verification/           # NEW: findings records (committed, no secrets)
        ├── iol-findings.md
        ├── higyrus-findings.md
        ├── matriz-findings.md
        └── ambito-findings.md
```

### Structure Rationale

- **Drivers stay at root as `main_<pkg>.py`** — this is the existing, sanctioned vehicle (PROJECT.md Key Decision: "Vehículo = scripts `main_*.py` extendidos"). They are run with `uv run --package <pkg> python main_<name>.py`, which resolves the correct package's `.env` and import name. Reusing them avoids inventing new infrastructure and keeps the "no shared code between packages" constraint intact — each driver imports exactly one package.
- **`.planning/verification/` for findings** — separates the *durable evidence trail* from the *disposable driver code*. Committed so the roadmap/orchestrator and future milestones can read what was verified. Must contain **no credentials and no raw tokens** (Constraint: never expose creds in reports/logs).
- **Regression tests live in the package's own `tests/`** — TESTING.md is explicit: `test_client.py` (sync) + `test_async_client.py` (async), with autouse `configure()`+monkeypatch fixtures already in each `conftest.py`. The fix's regression test slots straight into that, no new test layout.

---

## Architectural Patterns

### Pattern 1: Per-package driver script (NOT a shared runner, NOT a pytest live-suite)

**What:** Each `main_<pkg>.py` is a self-contained driver that imports one package, exercises its full sync surface, then its full async surface, and emits one findings record. There is deliberately **no** shared harness module.

**When to use:** This monorepo specifically — because "no shared code between packages" is a hard design constraint (ARCHITECTURE.md: "No shared library… intentionally duplicated to keep each publishable package self-contained"). A shared runner would introduce the first cross-package import in the repo.

**Trade-offs:**
- The three candidate structures and why the driver wins:

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Per-package driver script** (`main_*.py`) | Zero new infra; matches sanctioned vehicle; one package per file = honors "no shared code"; trivially runs the *live* thing the milestone needs; readable transcript output | Boilerplate duplicated across 4 files (acceptable — mirrors the codebase's own duplication ethos) | ✅ **Recommended** |
| **Shared runner** (one harness importing all 4) | DRY transcript/findings logic | Creates the repo's first cross-package coupling; one package's missing creds / import error can break the run for all; violates the self-contained-package principle | ❌ Rejected |
| **pytest "live" suite** gated by marker/env | Reuses pytest + asyncio_mode=auto; structured pass/fail | Live, order-dependent, market-hours-dependent calls are a poor fit for pytest's isolation model; would pollute CI (must be excluded with `-m "not live"`); the milestone's *fixes* already become mocked pytest tests, so a parallel live-pytest layer is redundant; conflates "is the client correct" (verification) with "did the fix stick" (regression) | ❌ Rejected as the primary vehicle |

**A small caveat on the rejection of pytest-live:** if a *minimal* gated live smoke is ever wanted in CI, a `@pytest.mark.live` marker excluded by default (`addopts = "-m 'not live'"`) is the correct shape. But for *this* milestone — exhaustive, exploratory, market-dependent surface-walking that feeds manual bug triage — the script driver is the right tool. Keep the two ideas separate.

**Example:**
```python
# main_iol.py — shape of a driver (read-only client, dict payloads → silent-shape risk)
from __future__ import annotations

import asyncio
import os

import iol_client
from iol_client import aio
from _verify import Findings, check  # see note below on _verify

REQUIRED = ("IOL_USER", "IOL_PASSWORD")


def run_sync(f: Findings) -> None:
    check(f, "get_quote('GGAL')", lambda: iol_client.get_quote("GGAL"),
          expect_keys=("ultimoPrecio", "simbolo"))
    check(f, "get_instruments()", iol_client.get_instruments)
    # ... every public function from __all__


async def run_async(f: Findings) -> None:
    await check(f, "aio.get_quote('GGAL')", lambda: aio.get_quote("GGAL"),
                expect_keys=("ultimoPrecio", "simbolo"), is_async=True)
    # ... mirror every sync call
    await aio.aclose()
```

> **Note on `_verify`:** A tiny `check()`/`Findings` helper is genuinely useful and is the *one* place where "shared code" is tempting. Resolve the tension by keeping it as a **root-level `_verify.py` used only by the root drivers** — it is part of the verification scaffolding, not part of any publishable package, so it does not violate the "no shared code *between packages*" rule (the packages never import it). If even that feels like over-engineering, inline a `check()` function into each driver — the duplication is consistent with the codebase's philosophy and only ~15 lines.

### Pattern 2: Full-surface walk, sync then async, one call per public symbol

**What:** Drive **every** function in the package's `__all__` (minus pure types/exceptions/models). Run the complete sync block, then the complete async block via a single `asyncio.run(run_async(...))`. Pair each sync call with its async twin so divergences between `client.py` and `aio.py` surface immediately.

**When to use:** All four drivers. The dual sync/async surface is the explicit reason this milestone exists ("Ambas superficies pueden divergir; la lógica está duplicada").

**Trade-offs:** Walking the full surface needs *valid inputs* for parameterized calls (a real symbol for `get_quote`, a real `account_id` for matriz order queries, valid dates for higyrus `get_movimientos`). The driver must source these from earlier read-only calls where possible (e.g., pull an instrument symbol from `get_all_instruments()` before calling `get_market_data`), and accept that some calls (e.g., `get_order_status` for a specific `clOrdId`) can only be exercised meaningfully after a mutating call — these stay in the gated block.

The per-package surface to walk (from each `__init__.py`):

| Package | Read-only public functions (always run) | Mutating (gated) | Async? |
|---------|------------------------------------------|------------------|--------|
| **ambito** | `get_dollar_banco_nacion` | — | sync + async |
| **iol** | `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type` (+ `login`) | — | sync + async |
| **higyrus** | `get_health`, `get_listado_cuentas`, `get_movimientos`, `get_posiciones`, `get_posicion_valuada` (+ `login`) | — | sync + async |
| **matriz** | `get_segments`, `get_all_instruments`, `get_instruments_details`, `get_instrument_detail`, `get_instruments_by_cfi`, `get_instruments_by_segment`, `get_market_data`, `get_trades`, `get_positions`, `get_detailed_positions`, `get_account_report`, `get_active_orders`, `get_filled_orders`, `get_all_orders`, `get_order_status`, `get_order_history`, `get_order_by_exec_id` (+ `login`) | `new_order`, `replace_order`, `cancel_order` | **sync only** (no `aio.py`; WS out of scope) |

### Pattern 3: Findings record as the pivot between verification and fixing

**What:** Each run appends to `.planning/verification/<pkg>-findings.md` a structured entry per discrepancy. The record is the artifact that (a) justifies a fix in `client.py` + `aio.py` and (b) carries the captured real payload that becomes the regression-test fixture.

**When to use:** Every discrepancy, every package. This is the data structure that makes the "hallazgo → corrección → test" loop auditable.

**Trade-offs:** Markdown is human-readable and roadmap-friendly but not machine-queryable. Given the scale (4 clients, dozens of functions, expected handful-to-dozens of findings) markdown is the right weight; a JSON log would be over-engineering and risks accidentally serializing a token.

**Discrepancy classification (the key field):**

| Class | Meaning | Typical fix locus |
|-------|---------|-------------------|
| `SHAPE` | Real payload key/type differs from what the client reads (highest risk for iol — raw `dict`, no models) | parsing/model `from_api` or dict-access in client.py + aio.py |
| `AUTH` | Token/header flow wrong against live auth | `login()`/`_ensure_token()` |
| `ERROR-MAP` | Live error status/body not mapped to the right typed exception | `_raise_for_response` / payload `status:ERROR` check |
| `PARAM` | Query/path params built wrong (caught by live 4xx or empty result) | URL/param construction |
| `SYNC-ASYNC-DRIFT` | Sync and async surfaces return different results for the same call | the diverging surface only |
| `NO-DATA` | Not a bug — market closed / no data for inputs (e.g., Ámbito weekend) | none; note and move on |
| `ANTI-BOT` | Ámbito User-Agent rejected | UA handling in client.py + aio.py |

**Example findings entry:**
```markdown
### F-003 · matriz · get_market_data · SHAPE
- **Called:** get_market_data("DLR/MAY26", entries=["BI","OF","LA"])
- **Expected (client assumes):** snapshot.last is a float
- **Actual (live):** "LA" arrives as {"price": 1234.5, "size": 10, "date": ...}
- **Surface:** sync ✗ / async N/A (no aio)
- **Captured payload:** tests/fixtures or inline constant MD_PAYLOAD (token redacted)
- **Fix:** MarketDataSnapshot.from_api — handle object form  → models.py
- **Regression test:** test_market_data_last_as_object (Regression: F-003)
- **Status:** OPEN → FIXED → TESTED
```

---

## Data Flow

### The core loop: live call → finding → fix → regression test

```
[driver runs check() against LIVE API]
        ↓
[compare actual payload vs client's assumption]
        ↓ discrepancy?
   ── no ──→ log PASS line in transcript, continue
   ── yes ─→ [append classified entry to <pkg>-findings.md, capturing real payload (token redacted)]
                  ↓
            [FIX in client.py]  ──mirror──▶  [FIX in aio.py]   (dual-surface invariant)
                  ↓
            [write regression test in test_client.py]  ──mirror──▶  [test_async_client.py]
                  ↓  uses captured payload as pytest-httpx mock
            [uv run pytest packages/<pkg>/ + mypy strict + ruff]  → green
                  ↓
            [mark finding TESTED; re-run driver to confirm live now passes]
```

### Credential & gating flow (per driver, at startup)

```
driver start
   ↓
creds present? (os.getenv of REQUIRED tuple)
   ├─ no  → print "SKIPPED <pkg>: missing IOL_USER, IOL_PASSWORD" → exit 0 cleanly
   └─ yes → run read-only surface (sync, then async)
                ↓
            VERIFY_MUTATING=1 ?
               ├─ no  → print "SKIPPED mutating block (set VERIFY_MUTATING=1)"
               └─ yes → run new_order / replace_order / cancel_order  (matriz, remarkets sandbox only)
```

This satisfies the requirement that **Ámbito runs with zero config while IOL/Higyrus/Matriz self-skip when unconfigured** — each driver is independent, so a missing `.env` in one never blocks another. The skip must be *loud and specific* (name the missing vars), never a silent pass or a stack trace.

### Key Data Flows

1. **Shape-divergence detection (iol especially):** Because iol returns raw `dict`, the driver should assert on *expected keys/types* (`expect_keys=(...)`), not just "did it return". Silent shape drift is the named risk in PROJECT.md ("devuelve `dict` crudo… discrepancias silenciosas de forma").
2. **Payload capture for regression:** When a finding is logged, the *real* JSON (with any token/credential field redacted) is copied into the regression test as an inline constant or `pytest-httpx` `json=` body — matching the existing `ORDER_PAYLOAD = {...}` constant pattern in TESTING.md.
3. **Sync/async pairing:** Each async call is the twin of a sync call; differing results emit a `SYNC-ASYNC-DRIFT` finding and the fix touches only the diverging file.

---

## Suggested Verification Order (easiest-first, dependency-aware)

| Order | Package | Why this position | Auth | Surfaces | Mutating |
|-------|---------|-------------------|------|----------|----------|
| **1** | **ambito** | No auth at all — runs anywhere immediately; tiny surface (1 fn × 2 surfaces); proves the driver/findings/regression loop end-to-end on the lowest-risk target before scaling up | none | sync + async | none |
| **2** | **iol** | Small, well-defined surface (4 read fns); **highest silent-shape risk** (raw dicts, no models) so it benefits most from early, careful shape assertions; OAuth flow is standard | OAuth2 | sync + async | none |
| **3** | **higyrus** | Medium surface (5 fns) with `SafeModel`/`from_api` tolerance — the tolerance can *mask* shape bugs, so verification must assert real field values, not just "no exception"; Bearer auth | Bearer | sync + async | none |
| **4** | **matriz** | Largest surface (~17 read fns + 3 mutating); sync-only (no async twin to pair, simpler in one axis but bigger in another); only package with **destructive** calls → must be done last, with the mutating gate, against **remarkets sandbox** (default base URL), never production | X-Auth-Token | sync only | `new_order`, `replace_order`, `cancel_order` |

**Rationale for the ordering:** climb the difficulty/risk curve so the loop is debugged on Ámbito (no creds, no auth, 1 function) before it meets the riskiest target (matriz's order mutation). Ámbito first also de-risks the *harness itself* — if the findings/fix/regression flow is wrong, you find out on the cheapest package. Matriz last isolates the only destructive surface behind the most caution.

---

## Scaling Considerations

Not a user-scaling problem — this harness runs manually by a developer. The relevant "scale" axis is *surface size and run repeatability*:

| Concern | Approach |
|---------|----------|
| Surface grows (more functions) | Driver's full-surface walk is just a flat list of `check()` calls — append a line per new function; no structural change |
| Market-hours / data variability | Findings must distinguish `NO-DATA` (not a bug) from real discrepancies; re-run at market open if a read returns empty; note timestamp in transcript |
| Rate limits | Drivers are sequential and low-volume by nature; if a `RateLimitError` appears, it is itself a finding (`ERROR-MAP`) confirming the client maps 429 correctly |
| Re-running after a fix | The same driver re-run is the live confirmation step; the mocked regression test is the permanent guard so CI doesn't depend on live APIs |

---

## Anti-Patterns

### Anti-Pattern 1: Building a shared cross-package harness module

**What people do:** Create `harness/runner.py` that imports all four clients and loops over them for DRY-ness.
**Why it's wrong:** Introduces the monorepo's *first* cross-package coupling, directly violating the documented "no shared code between packages / each package self-contained" invariant. One package's missing creds or import error can break the whole run.
**Do this instead:** One `main_<pkg>.py` per package, each importing exactly one package. If transcript/findings helpers are worth sharing, put them in a **root-level `_verify.py`** used only by the (non-distributed) root drivers — the packages never import it.

### Anti-Pattern 2: Fixing `client.py` but forgetting `aio.py` (or vice-versa)

**What people do:** Patch the sync surface where a bug was found, ship it, leave the async mirror divergent.
**Why it's wrong:** The logic is duplicated by design; a fix in one surface without the other re-creates a `SYNC-ASYNC-DRIFT` bug. PROJECT.md makes mirroring a hard constraint.
**Do this instead:** Every logic fix is a paired edit (client.py + aio.py) with a paired regression test (test_client.py + test_async_client.py). Matriz is the exception — sync-only, no `aio.py`.

### Anti-Pattern 3: Running mutating order calls against production / without a gate

**What people do:** Add `new_order(...)` to the matriz driver's main path "to test it."
**Why it's wrong:** Destructive against a real exchange; can place real orders if base URL points at production.
**Do this instead:** Gate all three order mutators behind `VERIFY_MUTATING=1`, assert the base URL is the remarkets sandbox before executing, and pair `new_order` with an immediate `cancel_order` cleanup. Default-skip with a clear `SKIPPED (mutating)` line.

### Anti-Pattern 4: Asserting "no exception" instead of "correct shape"

**What people do:** Treat "the call returned without raising" as a pass — especially dangerous with iol (raw dicts) and higyrus (`SafeModel` swallows missing/wrong-type fields with safe defaults).
**Why it's wrong:** The tolerant deserialization *hides* the exact divergences this milestone exists to find. A `from_api` that silently fills zero-values for a renamed field returns a "valid" object that is wrong.
**Do this instead:** Assert on expected keys/types/values from the live payload; for `SafeModel` packages, check that specific fields are *populated as expected*, not just that an object came back.

### Anti-Pattern 5: Leaking credentials into findings or test fixtures

**What people do:** Paste the full live response (including a token or auth field) into `<pkg>-findings.md` or into a committed regression fixture.
**Why it's wrong:** Findings and tests are committed; tokens/credentials must never be committed or logged (hard security constraint).
**Do this instead:** Redact token/credential fields before recording. Capture only the domain payload needed to reproduce the shape bug.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Ámbito Financiero | Public GET, no auth, hardcoded browser User-Agent | Fragile to anti-bot; weekend/holiday → `NO-DATA` not a bug |
| IOL | OAuth2 password grant; raw `dict` responses | Highest silent-shape risk; assert keys explicitly |
| Higyrus | Bearer via JSON login; `SafeModel.from_api` | Tolerant parsing can mask bugs; assert field values |
| Primary (matriz) | X-Auth-Token header; `from_api` models; `status:ERROR` payload check | remarkets sandbox by default; only destructive surface |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| driver ↔ client package | direct import of one package | never imports a second package; honors self-contained rule |
| driver ↔ findings record | driver writes markdown to `.planning/verification/` | no secrets; committed |
| finding ↔ fix | manual: developer reads finding, edits client.py + aio.py | dual-surface paired edit |
| fix ↔ regression test | captured payload → pytest-httpx mock in package `tests/` | `Regression:` docstring convention |
| harness ↔ CI | none (live) — but regression tests DO run in CI (mocked) | keep live calls out of CI |

---

## Sources

- `.planning/PROJECT.md` — milestone scope, constraints, key decisions (HIGH)
- `.planning/codebase/ARCHITECTURE.md` — client architecture, dual sync/async, no-shared-code invariant (HIGH)
- `.planning/codebase/STRUCTURE.md` — monorepo layout, where `main_*.py` and tests live, env-var naming (HIGH)
- `.planning/codebase/TESTING.md` — pytest-httpx conventions, `configure()`+monkeypatch fixtures, `Regression:` docstring convention (HIGH)
- Read of `main_*.py`, each package `__init__.py` (`__all__` = full public surface), `matriz_client/client.py` signatures, `.env`/`.env.example` files (HIGH)

---
*Architecture research for: live-API verification harness, market-libs monorepo*
*Researched: 2026-05-26*
