# Spike Manifest

## Idea

Validar qué primitiva de lock satisface el contrato de un **TokenStore 3-way** (compartido entre sync REST + asyncio REST + `ws_client` daemon thread) sin bloquear el event loop ni perder atomicidad. Este era el highest-uncertainty item de Phase 10 (`matriz aio.py` creation + TokenStore) en el milestone v1.1, y debía resolverse antes de `/gsd-plan-phase 10`.

El contexto concreto: `matriz-client` hoy tiene `client.py` (sync REST) + `ws_client.py` (daemon thread con `websocket-client`) y NO tiene `aio.py`. Phase 10 introduce `aio.py` (async REST surface). Las 3 superficies comparten un único bearer token (TTL ~23h) que debe refreshearse atómicamente. El refresh es expensive y mutating — exactamente 1 ocurrencia ante N llamadas concurrentes con token expirado.

**Resultado: la pregunta está resuelta. Spike 001c (DCL) es el ganador.**

## Requirements (validados)

Decisiones que emergieron del spiking y son **non-negotiables** para el real build en Phase 10:

- **No agregar dependencies a `matriz-client`** — stdlib es suficiente. `aiologic` y similares quedan en backlog si aparece complejidad nueva.
- **El TokenStore debe poder llamarse desde sync code SIN exigir que el caller conozca el asyncio loop** — confirmado: sync callers usan `with state_lock:` directamente.
- **Refresh exactamente 1 vez** ante N callers concurrentes con token expirado — validado con 205 callers concurrentes (Spike 002).
- **Event loop no bloqueado > 5ms** — validado rigurosamente con `test_loop_freedom.py` (115 ticks de unrelated work durante refresh de 100ms).
- **`threading.Lock` como source-of-truth + `asyncio.Lock` lazy per-loop como coordinación local** — el patrón ganador.

## Constraints (descubiertos durante el spiking)

- **`asyncio.Lock` NO puede compartirse entre loops** — confirmado con `RuntimeError: Task got Future attached to a different loop` en Spike 001b. La librería stdlib enforce loop-binding y no es flexible.
- **`asyncio.Lock` es loop-local incluso entre `asyncio.run()` secuenciales** — sólo funciona por suerte cuando es uncontended cache-hit; bajo contención fragmenta.
- **`asyncio.to_thread` (Python 3.9+) es la pieza clave** que permite que un sync refresh corra sin bloquear el event loop, manteniendo `threading.Lock` como la primitiva atomizadora cross-context.
- **`_async_locks` dict tiene leak monotónico** en long-running apps con loop churn — flag conocida; mitigation TBD en Phase 10 plan (accept vs bounded LRU).

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001a | tokenstore-threading-lock-to_thread | comparison | `threading.Lock` + async usa `asyncio.to_thread` | ✓ VALIDATED | concurrency, threading, asyncio |
| 001b | tokenstore-asyncio-lock-run_threadsafe | comparison | `asyncio.Lock` + sync usa `run_coroutine_threadsafe` | ✗ INVALIDATED | landmine, asyncio, loop-binding |
| 001c | tokenstore-double-checked-locking | comparison | DCL: `threading.Lock` (state) + per-loop `asyncio.Lock` (coord) | ✓ **WINNER** | dcl, matriz-pattern, winner |
| 002 | tokenstore-3way-integration-stress | standard | 100+100+5 callers × 2 phases (cold + TTL expiry) usando 001c | ✓ VALIDATED | stress, integration, phase-10-ready |
| 003 | tokenstore-refresh-policy | standard | RefreshPolicy decorator (retry + exp backoff + fail-cache + transient/permanent classification) composed with 001c | ✓ VALIDATED | refresh-policy, retry, backoff, dos-prevention |
| 005 | codegen-tool-choice | standard | unasync 0.6.0 round-trip + B8 identity + matriz construct audit + deny-list intact | TBD | codegen, unasync, phase-12 |

## SPIKE-005 sub-experiments

| Sub | Name | Type | Plan | Validates |
|-----|------|------|------|-----------|
| 001a | ambito-round-trip | comparison | 12-01 | Byte-identical round-trip (modulo `ruff format`) + B8 identity preserved on the ámbito canary. |
| 001b | ambito-marker-future-compat | standard | 12-02 | `@generated` marker comment compatible with `from __future__ import annotations` (ruff check + ruff format --check + mypy --strict + ast.parse all exit 0). |
| 001c | matriz-construct-audit | enumeration | 12-02 | Every async-only construct in matriz aio.py 852 LOC classified — zero TBD/REVIEW/DENY-LIST-VIOLATION rows (D-SCOPE-02 merge gate). |
| 001d | matriz-deny-list-config | standard | 12-02 | Per-file `Rule(fpath_list=aio.py-only)` honors deny-list — sha256 of `_token_store.py`, `_refresh_policy.py`, `ws_client.py` identical pre/post unasync run. |

## Head-to-Head Comparison

| Property | 001a | 001b | 001c (WINNER) |
|----------|------|------|---------------|
| Hot-path async latency (cached read) | ~50µs (thread hop) | ~5µs (native) | ~5µs (cached fast path) |
| Loop free during refresh | ✓ | ✓ | ✓ |
| Sync caller complexity | trivial | heavy (bridge w/ start/stop) | trivial |
| 3-way integration | ✓ | ✗ multi-loop breaks | ✓ |
| Cross-loop atomicity | ✓ | ✗ | ✓ |
| Memory cost | none | small (bridge thread) | tiny (`_async_locks` dict) |
| Matriz pattern continuity | low | low | **high** (matches existing token refresh DCL) |
| Total LOC | ~40 | ~70 | ~80 |

## Forward References

- **Phase 10** (`matriz aio.py` + TokenStore creation): blocker is now resolved. Plan can proceed knowing the primitive choice and key constraints.
- **Phase 9** (deferred bugs, BUG-03 IOL refresh_token persistence): the DCL pattern is applicable but **NOT identical** — IOL has a refresh_token concept on top of bearer token. Phase 9 can reuse the locking PATTERN but state shape will differ.
- **`_async_locks` leak handling**: deferred to Phase 10 planning. Recommended approach is "accept the leak, document it" because the per-entry size is microscopic and most realistic use cases have <10 distinct loops over the lifetime of a Client instance.

## Conventions Followed

- **Stack**: Python 3.12 stdlib only (`threading`, `asyncio`, `dataclasses`, `time`).
- **Test framework**: Each spike runs its own `test_*.py` file via `python3` directly — no pytest in these spikes (intentionally lightweight, easy to read top-to-bottom).
- **Observability**: Each spike uses a thread-safe `LOG` list with ISO timestamps + category tags. Not currently exported but available for future runtime introspection.
- **Spike code lives in `.planning/spikes/NNN-name/`** — **NEVER copied to `packages/*/src/`**. The pattern is what carries forward; the code is reference-only.

## Next Steps

1. **Run `/gsd-spike --wrap-up`** (optional) to package these findings into a `.claude/skills/spike-findings-tokenstore/` skill that the planner will auto-discover when `/gsd-plan-phase 10` runs.
2. **Continue with `/gsd-discuss-phase 7`** for Phase 7 (`_core.py` extraction) — Phase 10 dependency on this spike is now cleared.
3. **When ready for Phase 10**: run `/gsd-discuss-phase 10` → the gsd-planner will pick up `.planning/spikes/MANIFEST.md` + spike READMEs + this file automatically as RESEARCH inputs.
