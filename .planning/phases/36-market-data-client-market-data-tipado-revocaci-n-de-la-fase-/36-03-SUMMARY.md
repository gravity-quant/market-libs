---
phase: 36
plan: 03
subsystem: verification-harness
tags: [driver, sc-5, ast-lock, deep-chain, d-09, form-a, null-objects, tdd]
requires:
  - "market_data_client.models.MarketDataEntries / BookLevel / EntryValue + the six @property aliases (Plan 36-02)"
  - "MarketDataSnapshot.market_data typed as MarketDataEntries, never None (Plan 36-02, D-04)"
  - "main_market_data.py's D-09 per-probe try ladder and its single sanctioned exception renderer (_finding_for_exc / _redacted_exc)"
provides:
  - "verification/test_main_market_data_deep_chain.py — four structural locks over the parsed driver (probe names, consumption, try-guard, non-vacuity floor of 24)"
  - "Deep-chain consumption at the four real read-probe sites of main_market_data.py (ROADMAP SC-5, second half)"
  - "packages/market-data-client/tests/test_null_object.py on form A prose, with the vacuous mapping-field test retitled to the property it actually holds"
affects:
  - "Phase 39 (LIVE-NOBJ-01) — the live run now EXERCISES the chain, so a missing/renamed wire key surfaces in-cycle instead of passing green behind a row count"
  - "Phase 40 (PUB-NOBJ-01) — the breaking market_data shape change and the three additive names still await the bump and the old→new migration table"
tech-stack:
  added: []
  patterns:
    - "AST lock that PARSES the driver rather than importing it (precedent 30-09 / AD-30-09-01, sibling test_main_market_data_postprocess_guarded.py)"
    - "try-BODY-only protection set: except/else/finally deliberately excluded, because the D-09 ladder does not cover them"
    - "non-vacuity floor constant in the _MIN_GUARDED_CALLS idiom, so a gutted driver reddens instead of passing"
    - "retitle-not-retire for a test whose subject moved but whose property survived"
key-files:
  created:
    - verification/test_main_market_data_deep_chain.py
  modified:
    - main_market_data.py
    - packages/market-data-client/tests/test_null_object.py
decisions:
  - "_ENDPOINT_OPTIONAL is RESOLVED as unchanged on measured evidence — CONTEXT's open discretion item is closed, not carried forward"
  - "The new lock ships FOUR tests, not one: probe-name presence, consumption, try-guard and non-vacuity are separable failures and a single test would report only the first"
  - "The historical 'form B' mentions are kept as narration in test_null_object.py, matching the additive-record convention models.py already carries — the claim of membership is what was removed"
  - "test_the_model_roster_is_not_vacuous left untouched: its >= 16 bound already absorbed the growth to 19"
metrics:
  duration: ~18 min (excl. the 13m49s verification sweep run in parallel)
  tasks: 3
  files: 3
  tests_before: 707 (market-data-client) / 29 (market-data driver locks)
  tests_after: 707 (market-data-client) / 33 (market-data driver locks)
  completed: 2026-08-29
status: complete
---

# Phase 36 Plan 03: driver deep-chain consumption + form A prose close-out — Summary

`main_market_data.py` now SPENDS the typed chain — `s.market_data.last.price`,
`len(s.market_data.bids)`, `…settlement/close/open_interest.price` — on every snapshot it
fetches, at all four real read-probe sites, inside the D-09 `try`, and a four-part AST lock makes
a silent reversion to a row count impossible.

## What was built

### Task 1 — the RED lock (`a6e5f6e`)

`verification/test_main_market_data_deep_chain.py`, 180 lines, **four** tests. It parses the
driver (`grep -c 'import main_market_data'` → `0`) because `main_market_data.py` has import-time
side effects, which is why every sibling driver lock in that directory parses too.

| Test | What it forbids |
|---|---|
| `test_the_four_read_probes_are_present_by_name` | a rename of any of the four probes (LIVE-01 / REFAC-05 keys downstream findings on them) |
| `test_every_read_probe_consumes_the_typed_market_data_chain` | a probe that counts rows — it would pass green with every link broken, because `len()` never touches `market_data` |
| `test_every_chained_access_sits_inside_the_probe_try_body` | a dereference in `except` / `else` / `finally` or after the ladder — uncaught there, so a `None` link would crash the run to FAILED |
| `test_the_deep_chain_lock_is_not_vacuous` | thinning the consumption down to a token access (`_MIN_CHAINED_ACCESSES = 24` = four probes × six aliases) |

`_protected_node_ids` collects only nodes reachable from a `try` **body**, for exactly the reason
`test_main_market_data_postprocess_guarded.py` states for its own helpers. `_chain_reaches` walks
the receiver chain down through `Attribute` / `Subscript` / `Call`, so `len(s.market_data.bids)`
counts as a chained access rather than escaping through the `len()` call node.

| Task 1 criterion | Result |
|---|---|
| RED for exactly one reason | `AssertionError: read probe(s) ['probe_latest_async', 'probe_latest_sync', 'probe_market_data_async', 'probe_market_data_sync'] carry NO deep-chain access` + `found only 0 … expected >= 24` — not an import error, not a parse error |
| `ruff check` / `ruff format --check` | All checks passed / already formatted |
| `mypy verification/test_main_market_data_deep_chain.py` | Success: no issues found in 1 source file |
| `grep -c 'import main_market_data'` | **0** |
| the nine pre-existing driver locks | **29 passed** — undisturbed |

### Task 2 — the GREEN source change (`847f368`)

Four edits, one per probe, structural mirrors of each other (C-3). Immediately after the fetch and
still inside the `try`:

```python
        chained = [
            (
                s.symbol,
                s.market_data.last.price,
                len(s.market_data.bids),
                len(s.market_data.offers),
                s.market_data.settlement.price,
                s.market_data.close.price,
                s.market_data.open_interest.price,
            )
            for s in snapshots
        ]
```

The `ProbeResult` detail gains a `chained={len(chained)}` term — a **count only**. The tuple stays
a local and is never rendered, which is the T-36-03-01 mitigation: no symbol, price or identifier
reaches a findings file that is committed to git forever. With an empty result list the
comprehension is a no-op and the probe still returns PASS; zero snapshots is not a failure. Each
site carries a `# D-09 / SC-5:` comment in the idiom already used there, stating both that the
chaining is deliberately inside the `try` and why counting rows is not consumption.

| Task 2 criterion | Result |
|---|---|
| the Task 1 lock turns green | **33 passed** over the ten modules (29 pre-existing + the new module's 4) |
| `ruff check` + `ruff format --check main_market_data.py` | All checks passed / already formatted |
| `mypy main_market_data.py` | Success: no issues found in 1 source file — the chain type-checks at the CALL SITE, not only in the library |
| probe names | `grep -c` over the four `name = "…"` literals → **4** |
| `_ENDPOINT_OPTIONAL` | line 115 still `frozenset({"note", "entries"})` |
| `git diff --stat -- .planning/verification/schemas/market-data-client/` | **empty** |
| deep-chain access census | `grep -c 'market_data\.\(last\|bids\|offers\|settlement\|close\|open_interest\)'` → **24** |

`_write_schema_snapshot`, `_raw_via_request_sync` and `_raw_via_request_async` were not touched.
They feed RAW WIRE to the committed baselines on purpose, and after Plan 36-02 `to_dict()` is a
lossy model-shaped projection that must never reach them (Pitfall 9).

### Task 3 — form A prose + the phase gate (`cda7ba3`)

Two prose rewrites and one retitle in `test_null_object.py`, the two items 36-02 flagged for this
plan:

1. **Module docstring.** The form-B paragraph now declares **form A of D-07 since Phase 36 (D-05)**
   — both constructors reach the walker directly, with nothing between — and narrates the
   transition rather than erasing it. The "never harmonize" clause is kept and sharpened: the
   paquetes that carry a pass keep it, and this one must not grow a no-op one back to look
   identical. The deliberate-local-copies paragraph is untouched; it is load-bearing for Plan
   36-01's helper copies.
2. **`test_empty_emits_nothing`.** Its docstring earned the test on form-B grounds. Rewritten on
   the property that survives and is sharper after the transition: `empty()` reaches the *decoding*
   walker directly now, so the only thing keeping a construction with no wire behind it silent is
   the sink it is handed — and with three levels of nested Null Objects
   (`MarketDataSnapshot` → `MarketDataEntries` → `BookLevel`/`EntryValue`) a leaky sink would emit
   one record per declared field per level.
3. **The vacuous test, retitled not retired.**
   `test_empty_and_from_api_agree_on_every_mapping_declared_field` →
   `test_empty_and_from_api_agree_on_the_nested_container_field`. The assertion is byte-identical;
   only the name and docstring moved. Its old name described a mapping-declared field that D-05
   retired, so its green no longer meant what it said — a false-clean of exactly the kind this
   project exists to eliminate. The property it actually holds (the two constructors cannot
   disagree on the nested container) is what makes `bool(snapshot.market_data)` answer about the
   payload rather than about a constructor delta, and a three-level Null Object chain leans on it
   at every level.

`test_the_model_roster_is_not_vacuous` was **not** touched. Its `>= 16` bound already accommodates
the growth to nineteen, and the three new classes are asserted individually by the parametrized
tests (3 classes × 3 roster-parametrized tests = the +9 Plan 36-02 measured).

## The `_ENDPOINT_OPTIONAL` discretion item — RESOLVED, unchanged

CONTEXT left the treatment of `_ENDPOINT_OPTIONAL = frozenset({"note", "entries"})` to the
planner's discretion. **It is resolved as UNCHANGED, on measured evidence, and is not carried
forward.**

- RESEARCH Pitfall 7 / F-6 ran `diff_safemodel_bidirectional` over the committed no-data baseline
  and measured exactly one model-only finding: `[('', 'model-only', 'entries')]`. That constant is
  what suppresses it.
- Removing `entries` from the frozenset would therefore **manufacture a false SHAPE finding on
  every live run** of Phase 39 — a measured outcome, not an argument.
- `market_data` does **not** need adding: the no-data row does carry that key, with a `null`, so
  it never appears as model-only.
- `note` is unrelated to this phase and stays for its own LIVE-MD-01 reason (`/marketdata` omits
  it by design).

The apparent inconsistency (a model field now typed non-optional still being listed as
endpoint-optional) is not one: `_ENDPOINT_OPTIONAL` is a frozenset of **response keys** consumed by
the SHAPE-diff, and the driver's own comment at line 125 already warns against confusing it with
`_ENDPOINT_TEMPLATES`. It says nothing about the model's annotation.

## The inherited `verification/` red — quantified, not absorbed

The full repo-root `verification/` sweep was run end to end at this plan's HEAD, and compared
against the measurement Plan 36-02 recorded in `deferred-items.md`.

| Run | failed | errors | passed | wall clock |
|---|---|---|---|---|
| Before (Plan 36-02, `uv run pytest verification -q`) | 21 | 19 | 385 | 827 s |
| After (this plan, same command) | **21** | **19** | **389** | 829.48 s (13 m 49 s) |
| Δ | **0** | **0** | **+4** | — |

The `+4` is precisely the four tests of `test_main_market_data_deep_chain.py`. **Not one failure or
error changed**, and the roster of failing modules is byte-identical to the one
`deferred-items.md` names: `test_matriz_sweep_snapshot.py` (17 failed + 17 errors, matriz),
`test_main_matriz_login_fail_uniformity.py` (2 failed + 2 errors, matriz), and
`test_cycle_closure_phase33.py::test_cycle_closure_is_not_vacuous` for `ambito-financiero-client`
and `higyrus-client` (2 failed, `FileNotFoundError`).

This phase neither caused nor repaired any of it. Phase 36's whole diff lives in
`packages/market-data-client/`, `main_market_data.py` and `verification/`, and the no-shared-code
constraint (DT-03) means it structurally cannot reach matriz, ámbito or higyrus. `ci.yml` never
exercises this directory — it passes an explicit per-package path — which is why the red has been
able to accumulate unnoticed since Phase 32 (`GATE-TYP-01`). The item stays where 36-02 filed it:
`deferred-items.md`, destined for the Phase 32 CI-gate follow-up or a dedicated `/gsd-audit-fix`
pass. **It is inherited explicitly, not silently.**

## D-09 held on all five artefacts

| Artefact | Check | Result |
|---|---|---|
| `packages/market-data-client/pyproject.toml` | blob hash | `cfb60655efb48907f417efd41b6b28d64499f99f` — unchanged |
| `uv.lock` | blob hash | `5c8ea46c0be875d8634a573a3fb06dba78e8cb8e` — unchanged |
| `__version__` | `grep -c '__version__ = "0.5.0"'` | **1** |
| `CHANGELOG.md` | `git diff --stat` over the plan's commits | empty |
| `README.md` | `git diff --stat` over the plan's commits | empty |

No version bump, no changelog callout, no old→new migration table, no lock refresh, and no live
run against develop. All five are Phase 40 work in full, replicating the v1.6 pattern where one
phase typed and a later one published.

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest packages/market-data-client -q` | **707 passed** in 1.02 s — exactly the count Plan 36-02 established |
| `uv run pytest packages/market-data-client/tests/test_null_object.py -q` | **61 passed** (unchanged; the retitle is not a count change) |
| roster growth reachable | 9 parametrized ids across `BookLevel` / `EntryValue` / `MarketDataEntries` (3 classes × 3 roster-parametrized tests) |
| `uv run pytest packages -q` (all six paquetes) | **1991 passed, 1 deselected** in 90.95 s |
| the ten market-data driver locks | **33 passed** (see deviation 1 on the arithmetic) |
| `uv run ruff check .` / `ruff format --check .` | All checks passed / 262 files already formatted |
| `uv run lint-imports` | Contracts: 5 kept, 0 broken |
| `uv run python tools/check_decode_intactness.py` | Checks A–D pass; digest `a1f00c824348164c` == `CANONICAL_DIGEST` (SC-5's "sin mover el hash") |
| `uv run python tools/check_uniform_structure.py` | clean, all 6 packages |
| `uv run python tools/check_surface_types.py` | **0 violations** |
| `uv run mypy` | Success: no issues found in **75** source files |
| `uv run mypy main_market_data.py` | Success: no issues found in 1 source file |
| `uv run pre-commit run --all-files` | all 9 hooks Passed |
| `_core.py` / `_decode.py` / `client.py` / `aio.py` blobs | `295ce13c` / `5446832d` / `7724342d` / `c4a75c1d` — all four unchanged |
| `git diff --stat -- .planning/verification/schemas/market-data-client/` | **empty** |
| plan scope | `git diff --stat HEAD~3 HEAD` reports exactly the three declared files; zero deletions |

## Deviations from Plan

### Notes on acceptance-criterion arithmetic and literal greps

**1. [Note, not a defect] The ten driver-lock modules report `33 passed`, not `30`.**

- **Found during:** Task 2's gate.
- **Cause:** Task 3's criterion assumed the new module would carry ONE test (29 + 1 = 30). It
  carries **four**, because the four properties fail separately and a single combined test would
  report only the first: a rename, a missing dereference, an unguarded dereference and a thinned
  consumption are four distinct regressions with four distinct fixes.
- **Effect:** strictly stronger than the criterion's intent. The pre-existing count is verified
  untouched at `29 passed` in Task 1's own gate, before the new module was added to the list.
- **Not fixed:** collapsing the four into one to satisfy the arithmetic would trade diagnostic
  precision for a number.

**2. [Note, not a defect] `grep -ci 'form b'` reports `3` for `test_null_object.py` and `1` for
`models.py`, not `0` for both.**

- **Found during:** Task 3's gate.
- **Cause:** the criterion's literal grep is stricter than the truth it encodes. The must-have is
  *"no prose still CLAIMS this package takes form B or runs a mapping pass"* — and none does. Every
  surviving occurrence is historical narration of the transition ("It was form B until then", "the
  form B → form A transition", "the row was written when this paquete was form B") sitting beside
  an explicit declaration of form A.
- **Why not "fixed":** two reasons, both binding.
  1. `models.py` is **not in this plan's `files_modified`**, and the plan's own prohibition says
     not to reach outside the three named files. Its single occurrence
     (`models.py:160`, *"**This is form A of D-07** since Phase 36 (D-05). It was form B until
     then"*) was written by Plan 36-02 for this exact purpose, so the criterion is literally
     unsatisfiable inside this plan's scope.
  2. Erasing the historical mention would contradict the additive-record convention this phase
     has followed throughout — the same reason 36-02 kept the Phase 33 `BREAKING` block beneath
     the `REVOKED IN PART` block rather than deleting it. A record of what each phase decided and
     why is worth more than a grep returning zero.
- **Verified instead, and this is the criterion's actual content:** `grep -n` over every
  occurrence in `packages/market-data-client/` confirms each one is either a declaration of form A,
  a statement about *other* paquetes ("the form-B paquetes keep their pass"), or a past-tense
  narration. Zero present-tense claims of membership remain, and zero prose describes a mapping
  pass as existing.

No Rule 1–4 deviations occurred: no bug was found, no missing critical functionality was added, no
blocker was hit, and no architectural change was needed.

### Scope discipline

`git diff --stat HEAD~3 HEAD` reports exactly the three files the plan declares —
`main_market_data.py`, `verification/test_main_market_data_deep_chain.py`,
`packages/market-data-client/tests/test_null_object.py` — with 283 insertions, 18 deletions and
**zero file deletions**. `_ENDPOINT_OPTIONAL`, `_write_schema_snapshot`, `_raw_via_request_sync` /
`_async`, `_finding_for_exc`, every probe name, all four source-module blobs, `pyproject.toml`,
`uv.lock`, `CHANGELOG.md`, `README.md` and everything under
`.planning/verification/schemas/` are untouched — verified by blob hash or by an empty
`git diff --stat`, never by inspection.

## Handoff notes

**For Phase 39 (`LIVE-NOBJ-01`, live run against develop).** The driver now EXERCISES the chain
rather than counting rows, which changes what the live run can tell you:

- A **missing or renamed wire key** inside `market_data` no longer hides. It arrives as a non-fatal
  `extra` (INFO — never fatal, by the signed Phase 29 decision) and is to be corrected in-cycle
  there. The ten-key roster is D-02's measured scope, and A2 in RESEARCH records it as the
  assumption an eleventh key would falsify.
- A **wrong-typed `market_data`** now reports `("MarketDataEntries", ".market_data", "non_dict")`,
  not the pre-36-02 `("MarketDataSnapshot", ".market_data", "type")`. The disposition is unchanged
  — still fatal under `strict_decode` — but the census must expect the new
  `(model, field_path, kind)` triple.
- The probe detail lines now read `snapshots=N chained=N` / `latest=N batch=N chained=N`. Any run
  where `chained` is lower than the row count means the comprehension raised, which the D-09 ladder
  will have already turned into a FINDING.
- `_ENDPOINT_OPTIONAL` must keep `entries` or every `/marketdata/latest` run emits a false
  `model-only entries` SHAPE finding. Settled here on measured evidence; do not "tidy" it.

**For Phase 40 (`PUB-NOBJ-01`, the publication).** Two parts, and it is **not** purely additive:

- **ADDITIVE:** three new public names — `BookLevel`, `EntryValue`, `MarketDataEntries` — in both
  `models.__all__` and the package `__all__`.
- **SOURCE-BREAKING:** `MarketDataSnapshot.market_data` moves from `dict[str, Any] | None` to
  `MarketDataEntries`, so every consumer subscript (`md["BI"][0]["price"]`) becomes an attribute
  chain (`md.bids[0].price`) and the value widens `int` → `float` on the way.
  `MarketDataSnapshot.entries` and `LatestRequest.entries` stop admitting `None`. The migration
  table wants one vieja→nueva row per accessor, and `main_market_data.py`'s four probes are now the
  canonical worked example of the new form.
- The bump, the CHANGELOG callout, the migration table and the `uv.lock` refresh are all still
  unmade — D-09 assigned them to Phase 40 in full and this plan held the line.

## Known Stubs

None. No hardcoded empty value flows to a consumer, no placeholder text, no unwired data source.
The `chained` locals are computed from live-fetched snapshots at every site and their length is
reported; nothing is mocked, defaulted or short-circuited.

## Threat Flags

None. No new network endpoint, no auth path, no file access pattern, no schema change at a trust
boundary. The register's dispositions held:

- **T-36-03-01** (identifier leaking into a committed findings file) — mitigated. The detail string
  gains a `chained=<int>` COUNT only; the tuple carrying `s.symbol` and the prices stays a local and
  is never rendered. `test_main_market_data_snapshot_identifiers.py` is green.
- **T-36-03-02** (overwriting the live-capture baselines) — mitigated. The snapshot sites are
  untouched and keep feeding raw wire; `git diff --stat` over the schema directory is empty.
- **T-36-03-03** (a second exception renderer) — mitigated. Nothing added accepts, reads or formats
  an exception object; the chained tuple is built from model attributes only. The AST census that
  flags exception-annotated parameters ran in every task gate.
- **T-36-03-04** (chain evaluation crashing the driver to FAILED) — mitigated, and now
  **structurally enforced**: `test_every_chained_access_sits_inside_the_probe_try_body` fails if a
  single dereference escapes the `try` body.
- **T-36-03-05** (loosening the mutating gate) — accepted; only read probes were edited, and
  `test_main_market_data_no_gate_bypass.py` + `test_main_market_data_no_config_write.py` ran green
  in every task gate.
- **T-36-03-SC** (supply chain) — accepted; this plan installs nothing, and both pinned blobs
  (`uv.lock`, `pyproject.toml`) are byte-identical to their phase-start values.

## Self-Check: PASSED

- `verification/test_main_market_data_deep_chain.py` — FOUND (180 lines, contains `ast.parse`)
- `main_market_data.py` — FOUND, contains `market_data.last` (24 alias dereferences total)
- `packages/market-data-client/tests/test_null_object.py` — FOUND, contains
  `test_empty_and_from_api_agree_on_the_nested_container_field`
- Commits `a6e5f6e`, `847f368`, `cda7ba3` — all FOUND in `git log`
