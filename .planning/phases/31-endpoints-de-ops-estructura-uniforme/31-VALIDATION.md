---
phase: 31
slug: endpoints-de-ops-estructura-uniforme
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-23
reconciled: 2026-08-23
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx 0.36.2 |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run pytest packages/market-data-client -q` (≈25s) |
| **Full suite command** | `uv run pytest packages/market-data-client packages/higyrus-client -q` (baseline: 699 passed / 36s) |
| **Estimated runtime** | ~36 seconds (full suite); ~25s (quick) |

CI-equivalent: `uv run pytest packages/<pkg>` per matrix leg — note this excludes `verification/`. Phase gate must additionally run `uv run pytest -q` (full repo, including `verification/`) locally, since G-1 (stale higyrus public-surface snapshot) lives there and CI never runs it.

---

## Sampling Rate

- **After every task commit:** `uv run pytest packages/<touched-package> -q` + `uv run ruff check .`
- **After every plan wave:** `uv run pytest packages/market-data-client packages/higyrus-client -q` (baseline **699**, expect ≥699 after) + `uv run python tools/check_decode_intactness.py` + `uv run python tools/check_uniform_structure.py`
- **Before `/gsd-verify-work`:** Full local suite **including `verification/`** (`uv run pytest -q`) must be green, plus `uv run mypy` and `uv run mypy packages/market-data-client/src` (D-13 local-only acceptance step, not CI-enforced).
- **Max feedback latency:** ~40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 31-01-T1 | 31-01 | 1 | TYP-02 | T-31-01 / V4 | Mutating-gate first-executable-statement AST guard, in-package, non-vacuous by SET EQUALITY against the 8-name roster | unit (AST) | `uv run pytest packages/market-data-client/tests/test_mutation_gate_ast.py -q` | ❌ new file | ⬜ pending |
| 31-01-T1 | 31-01 | 1 | TYP-02 | T-31-02 / V4 | Neither holiday builder changes `idempotent=` (stays `True`, D-20) — direct `RequestSpec.idempotent is True` assertion | unit | `uv run pytest packages/market-data-client/tests/test_mutation_gate_ast.py -q` | ❌ new (same file) | ⬜ pending |
| 31-01-T2 | 31-01 | 1 | TYP-02 | T-31-03 / V13 | Byte-identical v0.4.0 request pin for `add_holidays`/`delete_holiday`, sync + async, raw-bytes tuple equality | unit | `uv run pytest packages/market-data-client/tests/test_v040_request_pin.py -q` | ❌ new file | ⬜ pending |
| 31-02-T1 | 31-02 | 1 | TYP-03 | T-31-06 | Uniform-structure gate exists, reads its roster from disk, and was OBSERVED RED listing all 7 missing files | script | `uv run python tools/check_uniform_structure.py` (expect exit 1 at T1) | ❌ new | ⬜ pending |
| 31-02-T2 | 31-02 | 1 | TYP-03 | T-31-07 / T-31-08 | All 6 packages have `models.py` + `types.py`; wallets' pair imports nothing; ámbito's surface golden unmoved | script + golden | `uv run python tools/check_uniform_structure.py && uv run pytest -q` | ❌ new | ⬜ pending |
| 31-02-T2 | 31-02 | 1 | TYP-03 | T-31-09 | `check_decode_intactness.py` stays green and UNEDITED (wallets still exempt) | script | `uv run python tools/check_decode_intactness.py` | ✅ exists | ⬜ pending |
| 31-02-T2 | 31-02 | 1 | TYP-03 | — | New near-empty modules pass strict typecheck + lint | typecheck/lint | `uv run mypy && uv run ruff check . && uv run ruff format --check .` | ✅ existing CI | ⬜ pending |
| 31-03-T1 | 31-03 | 1 | TYP-02 | T-31-12 / T-31-16 | `Health` declared from the live capture, no Optional, no `from_api` override; `to_dict()` copied verbatim, no cross-package import | unit | `uv run pytest packages/higyrus-client -q && uv run mypy packages/higyrus-client/src` | ✅ extend | ⬜ pending |
| 31-03-T2 | 31-03 | 1 | TYP-02 | T-31-11 / V7 | `higyrus.get_health` returns `Health` on 4 sites; guard keeps its exact `title`/`detail` strings; decoration perturbs no decode test | unit | `uv run pytest packages/higyrus-client/tests/test_decode.py -q && uv run mypy packages/higyrus-client/src` | ✅ re-assert | ⬜ pending |
| 31-03-T3 | 31-03 | 1 | TYP-02 | T-31-13 | higyrus 204/empty → zero-valued `Health`; non-dict still raises `HigyrusAPIError(status_code=0, ...)`; strict-mode behavior MEASURED and pinned | unit | `uv run pytest packages/higyrus-client/tests/test_core.py -k health -q` | ✅ re-mock | ⬜ pending |
| 31-03-T3 | 31-03 | 1 | TYP-02 | T-31-14 / V8 | higyrus public surface golden regenerated (G-1) — LOCAL ONLY, CI never runs `verification/` | golden | `uv run pytest verification/test_public_surface.py -q` | ✅ needs regen | ⬜ pending |
| 31-03-T3 | 31-03 | 1 | TYP-02 | T-31-15 | higyrus driver health probes stay wire-visible (already raw via `_raw_request_sync`; docstring corrected) | inspection + suite | `uv run pytest -q` | ✅ no functional change | ⬜ pending |
| 31-04-T1 | 31-04 | 2 | TYP-02 | T-31-17 | Nullability of the 9 under-determined health-feed fields decided at a BLOCKING checkpoint, not by the planner | checkpoint | `git status --porcelain packages/market-data-client/src/` empty at gate | n/a | ⬜ pending |
| 31-04-T2 | 31-04 | 2 | TYP-02 | T-31-20 | 6 health models, 3 nesting levels populated; no `from_api` override; no mapping field; every Optional justified in its docstring | unit | `uv run pytest packages/market-data-client/tests/test_core.py packages/market-data-client/tests/test_decode.py -q` | ✅ extend | ⬜ pending |
| 31-04-T3 | 31-04 | 2 | TYP-02 | T-31-19 / V7 | Both health parsers gain a non-dict guard whose message carries the TYPE NAME only | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k health -q` | ❌ new (no guard today) | ⬜ pending |
| 31-04-T3 | 31-04 | 2 | TYP-02 | T-31-21 / T-31-22 | `get_health`/`get_health_feed` return `Health`/`HealthFeed` on 8 sites; 31-01's gates re-run green after the shell edits | unit | `uv run pytest packages/market-data-client -q` | ✅ re-mock | ⬜ pending |
| 31-04-T3 | 31-04 | 2 | TYP-02 | T-31-18 / V8 | market-data driver health probes snapshot RAW WIRE via `_raw_via_request_*`, not a model projection (G-3) | inspection + suite | `uv run pytest -q` | ✅ helpers exist | ⬜ pending |
| 31-05-T1 | 31-05 | 3 | TYP-02 | — | `add_holidays` returns `AddHolidaysResult` with `days: list[CalendarDay]` (reused, not duplicated); `deleted` is `bool` not `int` | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k "add_holidays or delete_holiday" -q` | ✅ re-mock | ⬜ pending |
| 31-05-T2 | 31-05 | 3 | TYP-02 | T-31-28 | `parse_calendar_write_response` split in two, T-26-13 tolerance preserved as `Model.from_api(None)` on all 4 branches (G-4) | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k "add_holidays or delete_holiday" -q` | ❌ new | ⬜ pending |
| 31-05-T2 | 31-05 | 3 | TYP-02 | T-31-24 / T-31-25 / T-31-26 | Criterion 2 + 3 proof: 31-01's pin and guard pass with an EMPTY `git diff` after the mutation-method edits | unit | `uv run pytest packages/market-data-client/tests/test_v040_request_pin.py packages/market-data-client/tests/test_mutation_gate_ast.py -q` | ✅ from 31-01 | ⬜ pending |
| 31-05-T3 | 31-05 | 3 | TYP-02 | T-31-27 | ~96 lines re-mocked to live shapes; refusal matrix semantically intact (zero requests on refusal) | unit | `uv run pytest packages/market-data-client/tests/test_calendar_write.py packages/market-data-client/tests/test_calendar_write_async.py -q` | ✅ re-mock | ⬜ pending |
| 31-05-T3 | 31-05 | 3 | TYP-02 | T-31-29 | delete probes carry an explicit drift-blindness carry-forward routing Phase 33 to the divergence census | inspection | `uv run pytest -q` | ✅ accepted risk | ⬜ pending |
| 31-05-T3 | 31-05 | 3 | TYP-02, TYP-03 | — | **Phase gate**: no untyped-mapping return across all 5 endpoints × 2 surfaces × (method, shim) | typecheck + suite | `uv run pytest -q && uv run mypy && uv run mypy packages/market-data-client/src && uv run python tools/check_uniform_structure.py && uv run python tools/check_decode_intactness.py` | ⚠️ md not CI-enrolled (D-13) | ⬜ pending |

*Task IDs reconciled against the 5 authored plans on 2026-08-23. Note two deviations from the draft above: (a) the AST guard lives in a NEW `test_mutation_gate_ast.py`, leaving the existing behavioral `test_mutation_gate.py` untouched; (b) the byte-identical pin lives in a NEW `test_v040_request_pin.py` rather than inside the calendar-write files, so that its `git diff` stays empty across plan 31-05's re-mock — which is itself criterion 2's evidence.*

---

## Wave 0 Requirements

All five draft Wave 0 gaps are assigned to a plan. Four of them land in **wave 1** (there is no
separate wave 0 in this phase — the guards are built first, in parallel with the tracer, against
unchanged source, which is the same guarantee); the fifth is a new behavior and correctly lands
with the code that introduces it.

- [ ] **31-01 T2** — Byte-identical request pin (sync + async) for `add_holidays`/`delete_holiday`, in a NEW `tests/test_v040_request_pin.py`. Frozen tuple `(method, str(url), sorted headers, content bytes)` compared as raw bytes. Covers TYP-02 criterion 2 (D-08).
- [ ] **31-01 T1** — Mutating-gate AST guard, in-package at `tests/test_mutation_gate_ast.py` (NOT under `verification/`, which never runs in CI), non-vacuous by set equality. Covers TYP-02 criterion 3 (D-07).
- [ ] **31-01 T1** — Direct builder-flag assertion (`RequestSpec.idempotent is True` on both holiday builders), in the same new file. Criterion 3's second clause (D-20 / G-6).
- [ ] **31-02 T1+T2** — `tools/check_uniform_structure.py` + new `ci.yml` `lint` step, with the RED state OBSERVED before the 7 files exist. Covers TYP-03 criterion 4 (D-12).
- [ ] **31-04 T3** — Non-dict guard for the two market-data health parsers (today's shared `parse_health_response` has none; D-04 requires an equivalent to higyrus's). Lands with the parser split rather than ahead of it, because the guard is a NEW behavior this phase introduces — there is nothing to pin in advance.

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have an `<automated>` verify — 13 of 13 tasks across the 5 plans, including the checkpoint (whose automated check asserts no source was written before the gate resolved)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — every task carries one
- [x] Wave 0 covers all MISSING references (5 gaps above, all assigned)
- [x] No watch-mode flags — every command is a single-shot `uv run`
- [x] Feedback latency < 40s — quick per-package run ≈25s, combined ≈36s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** reconciled against the 5 authored plans 2026-08-23; pending execution.
