---
phase: 22-instruments-symbols-read-calendar-read-modelos
verified: 2026-07-30T11:43:03Z
status: passed
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 22: Instruments + symbols(read) + calendar(read) + modelos Verification Report

**Phase Goal:** Cubrir la superficie de datos de referencia de lectura (instruments, segments, symbols, calendar) con modelos tipados — sync AND async, collections guarded 204/None→[], calendar/config as a single typed object; mocked tests green; sync/async parity.
**Verified:** 2026-07-30T11:43:03Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Merged from ROADMAP.md success criteria and both plans' `must_haves.truths` (22-01, 22-02).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `Instrument, Segment, Symbol, CalendarDay, CalendarConfig` deserialize partial/None/extra-key payloads without raising | ✓ VERIFIED | `models.py:204-274` — 5 plain `SafeModel` subclasses, no custom `from_api`; `test_reference_models.py` exercises `{}`, `None`, extra-key payloads for all 5, independently re-run: 8/8 pass |
| 2 | Reference models carry NO `received_at` field (D-05) | ✓ VERIFIED | `grep "def from_api"` in `models.py` shows only `SafeModel` (base) and `MarketDataSnapshot` override it — the 5 reference models use the inherited version; `test_reference_models_have_no_received_at` parametrized over all 5 models, passes |
| 3 | The 5 builders emit `RequestSpec(method=GET, authenticated=True, idempotent=True)` with distinct `endpoint_name` | ✓ VERIFIED | `_core.py:383-508` — `build_instruments_request` (`endpoint_name="instruments"`), `build_segments_request` (`"segments"`), `build_symbols_request` (`"symbols"`), `build_calendar_request` (`"calendar"`), `build_calendar_config_request` (`"calendar_config"`), all `authenticated=True, idempotent=True`; asserted in `test_reference_core.py` builder tests |
| 4 | Filter serialization drops None but preserves falsy (`active=False`, `offset=0`, empty string); empty dict collapses to `params=None` | ✓ VERIFIED | `_params.drop_none` reused (`packages/market-data-client/.../_params.py`); `test_builder_instruments_falsy_preserved_none_dropped`, `test_builder_symbols_preserves_active_false`, `test_builder_instruments_all_none_collapses_to_none` pass |
| 5 | Collection parsers return `[]` on a 204 or null body (D-06) | ✓ VERIFIED | `_core.py:570-632` — 4 collection parsers each: `if not resp.content: return []` then `if raw is None: return []`; `test_parse_*_response_null_and_204_return_empty` (x4) pass |
| 6 | `parse_calendar_config_response` returns a single `CalendarConfig`; empty body yields `CalendarConfig.from_api(None)` without raising (D-07) | ✓ VERIFIED | `_core.py:635-648`; `test_parse_calendar_config_response_empty_body_tolerant_default` and `test_parse_calendar_config_response_returns_single_object` pass |
| 7 | `get_instruments, get_segments, get_symbols, get_calendar, get_calendar_config` exist on `Client` (sync) and `AsyncClient` (async) | ✓ VERIFIED | `client.py:435-497` (5 methods), `aio.py:449-511` (5 `async def` methods); independently re-run smoke checks (`hasattr` + `inspect.iscoroutinefunction`) both exit 0 |
| 8 | Each endpoint has a module-level shim delegating to the default client, sync and async | ✓ VERIFIED | `client.py:625-673` (5 sync shims via `_get_default()`), `aio.py:637-685` (5 async shims via `await _get_default()`) |
| 9 | `get_calendar_config` returns a single `CalendarConfig`; the other four return `list[Model]` | ✓ VERIFIED | Return-type annotations confirmed on method + shim in both `client.py` and `aio.py`; `test_get_calendar_config_returns_single_object` / async twin assert `isinstance(result, CalendarConfig)` and `not isinstance(result, list)` |
| 10 | Sync and async signatures/behaviour are identical except `await` (D-08 dual parity) | ✓ VERIFIED | Side-by-side comparison of `client.py:435-497` vs `aio.py:449-511` — identical kwarg names/types/defaults/return types, bodies differ only by `await`; `test_reference_async_client.py` mirrors every `test_reference_client.py` test 1:1 |
| 11 | `with_options(max_retries=N)` threads through these calls for free via the existing `_request` | ✓ VERIFIED | New methods call `self._request(spec)` exactly like the unchanged `get_market_data`; `_request` (unchanged, `client.py:289+`) reads `self._max_retries` into `req.extensions["max_attempts"]` regardless of which method invoked it — no method-specific override added |
| 12 | Query params encode with httpx-native bool encoding; Bearer is injected on the authenticated GET | ✓ VERIFIED | `test_get_instruments_sends_bearer_and_encodes_params` asserts `req.headers["Authorization"] == "Bearer test-token"`, `req.url.params.get("include_expired") == "true"`, `.get("only_outright") == "false"`; async twin identical |
| 13 | All four CI gates (ruff / format / mypy strict / pytest) are green for the package | ✓ VERIFIED | Independently re-run (not trusting SUMMARY): `ruff check` → "All checks passed!"; `ruff format --check` → "27 files already formatted"; `mypy --strict` → "Success: no issues found in 27 source files"; `pytest` → "134 passed in 0.19s" |

**Score:** 13/13 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/market-data-client/src/market_data_client/models.py` | 5 reference SafeModel dataclasses, `class CalendarConfig` present | ✓ VERIFIED | All 5 classes present (`Instrument`, `Segment`, `Symbol`, `CalendarDay`, `CalendarConfig`), each `@dataclass(frozen=True, slots=True)` inheriting `SafeModel`, in sorted `__all__` |
| `packages/market-data-client/src/market_data_client/_core.py` | 5 builders + 5 parsers, `def build_instruments_request` present | ✓ VERIFIED | All 10 functions present, `__all__` alphabetically sorted, imports the 5 models |
| `packages/market-data-client/tests/test_reference_models.py` | from_api tolerance tests for the 5 new models | ✓ VERIFIED | 8 tests, all pass |
| `packages/market-data-client/tests/test_reference_core.py` | builder param-serialization + parser guard tests | ✓ VERIFIED | 17 tests, all pass |
| `packages/market-data-client/src/market_data_client/client.py` | 5 sync methods + 5 module-level sync shims, `def get_instruments` present | ✓ VERIFIED | 10 occurrences (5 methods, 5 shims); `get_calendar_config` annotated `-> CalendarConfig` |
| `packages/market-data-client/src/market_data_client/aio.py` | 5 async methods + 5 module-level async shims, `async def get_instruments` present | ✓ VERIFIED | 10 occurrences; all coroutine functions confirmed via `inspect.iscoroutinefunction` |
| `packages/market-data-client/src/market_data_client/__init__.py` | re-exports of the 5 sync shims + 5 model classes, `get_instruments` present | ✓ VERIFIED | All 10 names present in sorted `__all__` (independently checked via import + assert) |
| `packages/market-data-client/tests/test_reference_client.py` | sync end-to-end param-encoding + Bearer tests | ✓ VERIFIED | 5 tests covering all 5 endpoints, all pass |
| `packages/market-data-client/tests/test_reference_async_client.py` | async parity tests mirroring the sync suite | ✓ VERIFIED | 5 tests, exact async twins of the sync suite, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_core.py` | `models.py` | parsers call `Model.from_api` on decoded rows | ✓ WIRED | `Instrument.from_api(item)` (and 4 siblings) confirmed in parser bodies |
| `_core.py` | `_params.py` | builders funnel filter kwargs through `drop_none` | ✓ WIRED | `_params.drop_none({...})` confirmed in all 4 filterable builders |
| `client.py` | `_core.py` | methods build spec then parse via `_core` | ✓ WIRED | `_core.build_instruments_request(...)` → `self._request(spec)` → `_core.parse_instruments_response(resp)` triple confirmed for all 5 methods |
| `aio.py` | `_core.py` | async methods `await self._request` then parse via `_core` | ✓ WIRED | Identical triple with `await self._request(spec)` confirmed for all 5 methods |
| `__init__.py` | `client.py` | package re-exports the sync shims | ✓ WIRED | `get_calendar_config` (and 4 siblings) imported from `market_data_client.client` and listed in `__all__` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full package test suite | `uv run --package market-data-client pytest packages/market-data-client -q` | `134 passed in 0.19s` | ✓ PASS |
| ruff lint | `uv run ruff check packages/market-data-client` | `All checks passed!` | ✓ PASS |
| ruff format | `uv run ruff format --check packages/market-data-client` | `27 files already formatted` | ✓ PASS |
| mypy strict | `uv run mypy packages/market-data-client` | `Success: no issues found in 27 source files` | ✓ PASS |
| Sync method/shim existence | `python -c "import market_data_client.client as c; assert all(hasattr(...))"` | exit 0 | ✓ PASS |
| Async method/shim coroutine-ness | `python -c "import market_data_client.aio as a; assert all(inspect.iscoroutinefunction(...))"` | exit 0 | ✓ PASS |
| `__init__.py` re-export completeness | `python -c "import market_data_client as m; assert all(n in m.__all__ ...)"` | exit 0 | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes exist in this repository and none are declared in the PLAN/SUMMARY files. Step 7c: SKIPPED (no probes applicable — this phase is a Python library, not a migration/tooling phase).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| REF-MD-01 | 22-01, 22-02 | El consumidor puede leer datos de referencia — `GET /instruments`, `/instruments/segments`, `/symbols`, `/calendar`, `/calendar/config` — devueltos como modelos tipados, sync y async | ✓ SATISFIED | All 5 endpoints implemented sync+async with typed models, parity tests, CI green; REQUIREMENTS.md marks REF-MD-01 `[x]` and traceability table maps it to "Phase 22 — Complete" |

No orphaned requirements: REQUIREMENTS.md maps only REF-MD-01 to Phase 22, and both plans declare `requirements: [REF-MD-01]`.

### Anti-Patterns Found

None. Scanned all 9 phase-modified files (`models.py`, `_core.py`, `client.py`, `aio.py`, `__init__.py`, and the 4 new test files) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER`, placeholder-language strings, empty-implementation patterns, and hardcoded-empty stub indicators — zero matches. `format_bool` grep in `_core.py` returns nothing (acceptance criterion honored). No mutation endpoints (`POST/PATCH /symbols*`, `PUT/POST/DELETE /calendar*`) leaked into the read-only scope.

### Human Verification Required

None. This phase is a pure library surface (no UI, no external service to eyeball, no runtime-only behavior); all must-haves are structurally verifiable and were confirmed against the codebase and independently re-run test/lint/type-check commands.

### Gaps Summary

No gaps. All 13 merged must-have truths (ROADMAP success criteria + both plans' `must_haves.truths`) are VERIFIED against actual code, not SUMMARY claims. All artifacts exist, are substantive (no stubs), and are wired end-to-end (model ← parser ← builder ← method ← shim ← `__init__` re-export). Both `client.py` and `aio.py` surfaces are signature-identical except for `await`. All four CI gates were independently re-executed by the verifier (not read from SUMMARY.md) and passed: `ruff check`, `ruff format --check`, `mypy --strict`, `pytest` (134 passed).

**Note (non-blocking, informational):** `.planning/ROADMAP.md` still shows Phase 22 as "Plans: 1/2 plans executed" and the `22-02-PLAN.md` checkbox unchecked, even though `22-02-SUMMARY.md` and git history (`b91c3de`, `9cee57a`, `191a2ca`) confirm Plan 02 completed and shipped. This is a documentation-tracking staleness in ROADMAP.md's own bookkeeping, not a gap in the delivered code — the actual reference-data surface (the phase's real deliverable) is complete, tested, and green. Recommend updating ROADMAP.md's Phase 22 wave annotations to reflect 2/2 plans executed before closing the milestone.

---

*Verified: 2026-07-30T11:43:03Z*
*Verifier: Claude (gsd-verifier)*
