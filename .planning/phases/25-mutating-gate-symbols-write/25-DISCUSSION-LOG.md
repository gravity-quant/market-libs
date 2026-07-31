# Phase 25: Mutating-gate + Symbols write - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-07-31
**Phase:** 25-mutating-gate-symbols-write
**Mode:** assumptions
**Areas analyzed:** Env/host gate mechanics, Gate check location, RequestSpec extension,
Request-model serialization, Batch validation (1–500), Typing + view propagation,
Sync/async parity + exports

## Assumptions Presented

### A. Env/host gate mechanics
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New opt-in `expected_host` on `_ClientState`; exact-hostname (`urlsplit().hostname`) match, default = hostname of `DEFAULT_BASE_URL`; env opt-in stays in Phase-27 harness | Likely | `verification/mutation_gate.py:42-62` (exact-hostname discipline); `_state.py:48,56-58` (base_url env resolution) |

### B. Gate check location
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Private `_ensure_mutation_allowed()` on each shell, called first; zero HTTP + zero Auth0 on refusal; not in `_core`, not in `_request` | Confident | `_core.py:11-16` (IO-free purity, builders `del state`); uniform method shape `client.py:352-497` |

### C. RequestSpec extension for write
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| No structural change — `RequestSpec.method` + `.json_body` exist, `_request` threads `json=spec.json_body`; add 3 builders `idempotent=True` | Confident | `_core.py:119,123`; `client.py:316-322`; `build_latest_batch_request` `_core.py:361-377` |

### D. Request-model serialization
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Frozen `@dataclass(frozen=True, slots=True)` (not SafeModel) + hand-written `to_dict()`; `market_id="ROFX"` sent explicitly | Likely | `LatestRequest.to_dict()` `models.py:160-181`; schema `market_data_mutations.md:39-41` |

### E. Batch validation (1–500)
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Client-side `ValueError` (not typed error) before dispatch; placement in `NewSymbols.__post_init__` | Likely | `_validate_max_retries` `client.py:79-95`; `raise_for_response` `_core.py:135-147`; `exceptions.py` hierarchy |

### F. Typing + view propagation
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `mutating_allowed: bool = False` + `expected_host: str \| None` on shared `_ClientState`; inherits into `with_options` views for free | Confident | `_state.py:77-100` (slots dataclass); `client.py:231-235` (view shares `self._state`); `configure` carry-forward `client.py:543-566` |

### G. Sync/async parity + exports
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Mirror all methods/helper/params in `aio.py`; add new models + exception to `__all__` and `__init__.py` re-exports | Confident | DM-05 / CLAUDE.md; shims `client.py:574-673`, `__init__.py:39-99`; `test_public_surface.py`, `test_sync_async_isolation.py` |

## Corrections Made

No corrections — all assumptions confirmed via "Yes, proceed".

## External Research

Not performed. The three flagged research topics (exact 201/200/422 response shapes, real
server-side POST idempotency, PATCH path encoding for `/`-containing `symbol_id`) all require
live develop access + Auth0 credentials and are **explicitly deferred to Phase 27**
(LIVE-MUT-01) by the source plan. They are not resolvable from the codebase and do not block
Phase 25 planning — tolerant `SafeModel.from_api` parsing absorbs any shape surprise, and
DM-03 locks `idempotent=True` pending live revalidation.
