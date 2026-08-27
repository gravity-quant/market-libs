---
phase: 31-endpoints-de-ops-estructura-uniforme
verified: 2026-08-25T10:30:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Confirm the CR-02 semantic decision: silencing the strict_decode RAISE (not the divergence record) for the non-dict tolerance branch of `parse_add_holidays_response` / `parse_delete_holiday_response`, on the grounds that a published mutation's server-side write has already committed by the time the anomalous ACK is parsed."
    expected: "A human with authority over the Phase 33 live-strict-mode plan agrees that (a) suppressing only the raise (never the divergence record) is the correct trade-off for a MUTATION already published in v0.4.0, and (b) the narrow scope — only the terminal non-dict branch, NOT a well-shaped dict whose fields diverge — is exactly right and won't need revisiting once Phase 33 runs the drivers in strict mode against develop."
    why_human: "This is a judgment call about acceptable API/operational behavior (swallow-and-log vs. raise-and-lose-the-ack on a state-changing endpoint), not a fact verifiable by static inspection. The code and tests faithfully implement the decision as documented (confirmed: `_decode.STRICT_DECODE.set(False)` scoped to the single non-dict branch in both `parse_add_holidays_response` and `parse_delete_holiday_response`, `_emit()` still runs before the disposition so the divergence record is preserved, and a new test `test_calendar_write_parsers_still_raise_under_strict_when_a_field_diverges` proves a well-shaped dict with a diverging field still raises). What cannot be verified from the codebase is whether this is the policy the team actually wants going into Phase 33 — the fix report itself (31-REVIEW-FIX.md, closing notes) explicitly flags this as needing human confirmation before the phase proceeds."
    result: "APPROVED by operator sebadlf, 2026-08-25, via /gsd-plan-phase 31 auto-advance execution session. Confirmed: (a) suppressing only the raise (never the divergence record) is the correct trade-off for this published mutation, and (b) the narrow terminal-non-dict-branch scope is correct."
---

# Phase 31: Endpoints de ops + estructura uniforme — Verification Report

**Phase Goal:** Los 5 endpoints de ops que todavía devuelven `dict[str, Any]` devuelven modelos
tipados, y los 6 paquetes presentan la misma estructura de archivos para que el próximo endpoint
nazca con lugar donde vivir.
**Verified:** 2026-08-25
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP success criterion) | Status | Evidence |
|---|---|---|---|
| 1 | `higyrus.get_health` + `market-data.get_health`/`get_health_feed`/`add_holidays`/`delete_holiday` return typed models, sync AND async, zero `dict[str, Any]` in signatures/shims | ✓ VERIFIED | 20 signature sites confirmed by grep (4 higyrus + 16 market-data): `higyrus_client/client.py:450`, `client.py:602`, `aio.py:442`, `aio.py:608` all `-> Health`; `market_data_client/client.py:429,435,685,718` + `client.py:837,842,969,974` + `aio.py:438,444,694,728` + `aio.py:844,849,976,981` all `-> Health`/`HealthFeed`/`AddHolidaysResult`/`DeleteHolidayResult`. No bare `dict[str, Any]` return remains on any of the 5 endpoints. |
| 2 | Byte-identical request test for `add_holidays`/`delete_holiday` (method, URL, query, headers, body) vs. the v0.4.0 request, sync AND async | ✓ VERIFIED | `packages/market-data-client/tests/test_v040_request_pin.py` (181 lines) pins raw-bytes 4-tuples for both endpoints, both surfaces; `user-agent` derived from `httpx.__version__` (not hard-pinned) so a `uv.lock` bump doesn't redden it for an unrelated reason. Ran directly: 9/9 tests pass (`test_mutation_gate_ast.py` + `test_v040_request_pin.py`). Re-run after every subsequent plan per 31-05's own acceptance discipline, confirmed still green at HEAD. |
| 3 | Mutating gate intact: `_ensure_mutation_allowed()` remains the first executable statement of all 8 mutation methods (both shells), no builder's `idempotent=` flag touched | ✓ VERIFIED | `test_mutation_gate_ast.py` asserts the DISCOVERED method-name set EQUALS the 8-name roster (non-vacuous by construction, `test_every_mutation_method_is_discovered_in_shell`) and that the gate call is the first statement in each (`test_gate_is_first_executable_statement_in_every_mutation_method`). Both holiday builders confirmed `idempotent=True` at `_core.py:774,886`; stale `client.py`/`aio.py` docstring claiming `False` was corrected (grep confirms no remaining "idempotent=False" claim in either add_holidays docstring). Test run: pass. |
| 4 | All 6 packages carry `models.py` + `types.py` under `src/<pkg>/`, verified by a CI existence check | ✓ VERIFIED | `ls` confirms 12 files present across all 6 packages. `tools/check_uniform_structure.py` (165 lines, disk-enumerated via `iterdir`, no hardcoded package roster) run directly: exit 0, "all 6 packages... carry `models.py`, `types.py`". Wired into `.github/workflows/ci.yml`'s `lint` job as the `uniform-structure` step (confirmed at `ci.yml:56-60`), mirroring the `decode-intactness` step pattern exactly as required. `wallets-client`/`ambito-financiero-client` modules confirmed docstring-only, `__all__: list[str] = []`, zero imports beyond `from __future__ import annotations` — `check_decode_intactness.py` still green (Check D unaffected), and both packages import cleanly (`import wallets_client` / `import ambito_financiero_client` succeed). |

**Score:** 4/4 truths verified (0 present-behavior-unverified)

### Code Review Closure (31-REVIEW.md → 31-REVIEW-FIX.md, 9 findings)

A deep code review found 2 Critical + 7 Warning issues after initial execution. All 9 are confirmed
fixed in the current source (commits `275ad1a`..`bf04b2f`, all present in `git log` on the current
branch, HEAD `e46cb75`):

| # | Finding | Status | Evidence |
|---|---|---|---|
| CR-01 | higyrus driver never exercised typed `get_health()` — TYP-02 tracer had zero live coverage | ✓ FIXED | `main_higyrus.py:649-650,748-749` now call `client.get_health()` / `await aclient.get_health()` alongside the raw capture; dedicated `except HigyrusDecodeError` branch added on both surfaces (grep confirms `HigyrusDecodeError` imported and handled). |
| CR-02 | Holiday parsers' "none of them raises" claim was false under `strict_decode` (mutation ACK lost after commit) | ✓ FIXED, flagged for human sign-off | `_core.py:1206-1219` (add) / `:1252-1266` (delete) scope-silence `STRICT_DECODE` for the terminal non-dict branch only; divergence record still emitted (`_emit` runs before the disposition). New tests `test_calendar_write_parsers_do_not_raise_under_strict_decode` and `test_calendar_write_parsers_still_raise_under_strict_when_a_field_diverges` both pass. **See Human Verification** — this is a semantic/policy decision, not a mechanical fact. |
| WR-01 | Holiday parsers erased the observed type in divergence records (always `NoneType`) | ✓ FIXED | Payload now reaches `from_api` verbatim (`raw = resp.json() if resp.content else None`) instead of a literal `None` substitution; new parametrized test `test_calendar_write_parsers_record_the_type_actually_observed` (5 body shapes × 2 parsers) passes. |
| WR-02 | `AddHolidaysResult`/`DeleteHolidayResult` missing from `models.__all__` | ✓ FIXED | Both present in `models.py:91,94` (ASCII sorted); new guard `test_models_dunder_all_covers_every_safemodel_subclass` derives the expected set from `vars(models)` rather than a second hand list. Passes. |
| WR-03 | `public_keys=` in holiday probes was a compile-time constant (always 3) | ✓ FIXED | `main_market_data.py:2433,2664` now report `wire_keys={len(raw) if isinstance(raw, dict) else -1}` sourced from the raw re-fire, not `len(created.to_dict())`. |
| WR-04 | `to_dict()` docstring repeated a claim the module already declares wrong | ✓ FIXED | Both copies (`market_data_client/models.py:209`, `higyrus_client/models.py:72`) now state explicitly "It is **NOT** a valid input to `verification.schema.schema_of`". |
| WR-05 | `market_data_client._core` import-boundary claimed in docstring but unenforced | ✓ FIXED | `lint-imports` run directly: "Contracts: 5 kept, 0 broken" — `market_data_client._core does not depend on transport modules` now present alongside the 4 pre-existing contracts. |
| WR-06 | CI never type-checked the market-data test suite (~900 new lines) | ✓ FIXED | `ci.yml`'s "mypy (tests por paquete)" loop now includes `market-data-client` (`ci.yml:92-99`). Ran directly: `uv run mypy packages/market-data-client/tests` → "Success: no issues found in 27 source files". |
| WR-07 | Breaking dict→model change shipped under an already-released version with no changelog | ✓ FIXED | Both `packages/market-data-client/README.md` and `packages/higyrus-client/README.md` gained a "### vX.Y.0 — sin publicar todavía" changelog section documenting the 5 retyped endpoints and 9 newly exported models; higyrus's README previously had no `## Changelog` section at all — one was created. |

(3 Info findings — IN-01/02/03 — were explicitly out of the fix pass's declared scope
(`fix_scope: critical_warning`) and are not phase-blocking.)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `tools/check_uniform_structure.py` | Stdlib-only cross-package existence gate | ✓ VERIFIED | 165 lines, disk-enumerated (`iterdir`), no hardcoded roster, run directly → exit 0 |
| `packages/higyrus-client/src/higyrus_client/models.py` (`Health`) | `@dataclass(frozen=True, slots=True)` subclass of higyrus's `SafeModel`, 1 field `status: str` | ✓ VERIFIED | Confirmed class definition + docstring citing the live capture; re-exported in `__init__.py` and `verification/snapshots/higyrus-client-surface.txt` |
| `packages/market-data-client/src/market_data_client/models.py` (6 health models + 2 mutation-result models) | `Health`, `HealthAuth`, `HealthFeed`, `FeedIngestor`, `FeedMarket`, `FeedPipeline`, `AddHolidaysResult`, `DeleteHolidayResult` | ✓ VERIFIED | All 8 classes present; nullability matches the reported checkpoint decision exactly — only `FeedIngestor.last_error` and `FeedPipeline.last_write_error` are `str \| None`, all other 7 under-determined fields (`last_frame_at`, `started_at`, `last_write_at`, `next_transition`, `session_open`, `session_close`, `last_business_day`, `newest_received_at`, `oldest_received_at`) declared `str` |
| `packages/market-data-client/src/market_data_client/_core.py` parsers | `parse_health_response`→`Health`, `parse_health_feed_response`→`HealthFeed`, `parse_add_holidays_response`→`AddHolidaysResult`, `parse_delete_holiday_response`→`DeleteHolidayResult`, all `@_decode._response_parser`-decorated | ✓ VERIFIED | All 4 functions present, decorated, dispatched from both `client.py` and `aio.py` |
| 7 docstring-only `models.py`/`types.py` placeholders | `__all__: list[str] = []`, zero imports beyond `__future__` | ✓ VERIFIED | Confirmed content of `wallets_client/{models,types}.py`; same pattern in ambito |
| `.github/workflows/ci.yml` `uniform-structure` step | New step in existing `lint` job, mirrors `decode-intactness` | ✓ VERIFIED | `ci.yml:56-60` |
| `[tool.importlinter]` 5th contract | `market_data_client._core` forbidden-dependency contract | ✓ VERIFIED | `lint-imports` → 5 kept, 0 broken |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `higyrus_client/client.py` / `aio.py` | `higyrus_client/_core.py` | `_core.parse_get_health_response(...)` | ✓ WIRED | Both call sites confirmed |
| `market_data_client/client.py` / `aio.py` | `market_data_client/_core.py` | `_core.parse_health_response` / `parse_health_feed_response` / `parse_add_holidays_response` / `parse_delete_holiday_response` | ✓ WIRED | All 8 call sites (4 parsers × 2 shells) confirmed |
| `.github/workflows/ci.yml` (`lint` job) | `tools/check_uniform_structure.py` | new `uniform-structure` step | ✓ WIRED | Confirmed at `ci.yml:56-60` |
| `market_data_client/models.py` (`AddHolidaysResult.days`) | `market_data_client/models.py` (`CalendarDay`) | reuses shipped model, no parallel element type | ✓ WIRED | `days: list[CalendarDay]` confirmed, no new element model declared |

### Behavioral Spot-Checks / Test Execution

| Check | Command | Result | Status |
|---|---|---|---|
| Uniform-structure gate | `uv run python tools/check_uniform_structure.py` | exit 0, all 6 packages OK | ✓ PASS |
| Ruff | `uv run ruff check .` | All checks passed | ✓ PASS |
| Ruff format | (implied by CI; not independently re-run — WR-07 fix report confirms 231 files formatted) | — | ✓ PASS (per fix report, consistent with clean ruff check) |
| mypy (global src) | `uv run mypy` | 62 source files, no issues | ✓ PASS |
| mypy (market-data tests, WR-06) | `uv run mypy packages/market-data-client/tests` | 27 source files, no issues | ✓ PASS |
| import-linter (WR-05) | `uv run lint-imports` | 5 kept, 0 broken | ✓ PASS |
| decode-intactness | `uv run python tools/check_decode_intactness.py` | Checks A-D all pass, wallets exempt as documented | ✓ PASS |
| higyrus + market-data test suites | `uv run pytest -q packages/higyrus-client packages/market-data-client` | 809 passed | ✓ PASS |
| Mutation gate + byte pin (plan 31-01 net) | `uv run pytest -q packages/market-data-client/tests/test_mutation_gate_ast.py packages/market-data-client/tests/test_v040_request_pin.py` | 9 passed | ✓ PASS |
| CR-02/WR-01 targeted tests | `uv run pytest -q packages/market-data-client/tests/test_core.py -k "strict_decode or observed_type"` | 8 passed | ✓ PASS |
| WR-02 targeted test | `uv run pytest -q packages/market-data-client/tests/test_public_surface_market_data.py -k dunder_all_covers` | 1 passed | ✓ PASS |
| Untouched packages (iol/ambito/wallets/matriz/tests) | `uv run pytest -q packages/iol-client packages/ambito-financiero-client packages/wallets-client packages/matriz-client tests/` | 875 passed, 1 deselected | ✓ PASS (no regression) |
| `verification/` full suite | `uv run pytest -q verification/` | 19 failed + 19 errors | ⚠️ Matches deferred D-1 exactly (see below) — pre-existing, out of phase scope |

**`verification/` pre-existing failures, independently confirmed:** counted 19 `F` and 19 `E`
markers in the run output, matching `deferred-items.md` D-1's documented count exactly (matriz
probe-signature drift from a pre-Phase-31 `main_matriz.py` refactor). Phase 31 touches no matriz
file (`git status`/plan `files_modified` lists confirm this); `31-REVIEW-FIX.md` independently
diffed the pre-fix baseline (`87dcef0`) against the fixed tree and reported the "new failures" set
as empty. Not a phase 31 gap.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| TYP-02 | 31-01, 31-03, 31-04, 31-05 | 5 ops endpoints return typed models, byte-identical request test for the 2 published mutations, mutating gate intact | ✓ SATISFIED | Truths 1-3 above |
| TYP-03 | 31-02 | 6 packages present uniform `models.py`+`types.py`, CI-checked | ✓ SATISFIED | Truth 4 above |

No orphaned requirements: `REQUIREMENTS.md` maps only TYP-02 and TYP-03 to Phase 31, both are
claimed by the 5 plans' `requirements:` frontmatter. Note (info, not a gap): `REQUIREMENTS.md`'s
Traceability table still shows "Pending" for TYP-02/TYP-03 despite the top checklist marking them
`[x]` — this is a pre-existing doc-lag pattern affecting the whole table (DEC-01/TYP-01 from
already-completed Phases 29-30 show the same stale "Pending"), not something introduced by this
phase.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` debt markers found in any file touched by this phase. No stub returns
(`return null`, `return {}`, empty handlers) in the new models, parsers, or CI script. The
docstring-only `models.py`/`types.py` placeholders in wallets/ambito are an intentional,
plan-declared artifact (D-10/D-11), not an unintentional stub — verified against the plan's own
must-haves rather than flagged as a code smell.

### Human Verification Required

1. **CR-02 semantic decision — silencing strict-mode raise for the non-dict tolerance branch of the two holiday-mutation parsers.**
   - **Test:** Review `_core.py:1206-1219` (`parse_add_holidays_response`) and `:1252-1266` (`parse_delete_holiday_response`), and the rationale documented in both docstrings and in `31-REVIEW-FIX.md`'s CR-02 section.
   - **Expected:** Confirm that suppressing only the RAISE (never the divergence record) for a non-dict acknowledgement on an already-committed mutation is the correct policy heading into Phase 33's live strict-mode run — and that the narrow scope (terminal non-dict branch only; a well-shaped dict with a diverging field still raises, per `test_calendar_write_parsers_still_raise_under_strict_when_a_field_diverges`) is exactly right.
   - **Why human:** This is a policy/business trade-off (swallow-and-log vs. raise-and-lose-the-ack on a mutation), not a fact derivable from static inspection. The implementation faithfully matches what is documented — that part is mechanically verified — but whether it is the right call is outside what code inspection can settle, and the fix report itself flags it as needing sign-off before the phase proceeds.

### Gaps Summary

None. All 4 ROADMAP success criteria and all must-haves declared across the 5 plans are verified
directly against the current source (not inferred from SUMMARY prose). All 9 code-review findings
(2 critical, 7 warning) are confirmed fixed in the working tree, not merely claimed in
`31-REVIEW-FIX.md`. The single human-verification item above (CR-02 policy confirmation) was
presented to and approved by the operator before this phase was marked complete — see `result:` in
the frontmatter.

---

_Verified: 2026-08-25_
_Verifier: Claude (gsd-verifier)_
