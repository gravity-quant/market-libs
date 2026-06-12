---
name: spike-findings-market-libs
description: Implementation blueprint from spike experiments. Requirements, proven patterns, and verified knowledge for building market-libs (specifically the Phase 10 matriz TokenStore for 3-way concurrent token sharing + refresh policy with retry/backoff/fail-cache for auth-server DOS prevention). Auto-loaded during implementation work.
---

<context>
## Project: market-libs

market-libs es un monorepo de clientes Python para servicios financieros argentinos
(iol-client, higyrus-client, matriz-client, ambito-financiero-client, wallets-client).
Las spikes pre-Phase 10 resuelven dos blockers arquitectónicos:

1. **Lock primitive para TokenStore 3-way** — qué primitiva de concurrencia funciona
   safely en sync REST + async REST + ws_client daemon thread. Resuelto en Spike 001c
   (Double-Checked Locking con `threading.Lock` + per-loop `asyncio.Lock`).

2. **Refresh policy** — cómo manejar refresh failures sin DOSear el auth server.
   Resuelto en Spike 003 (decorator con retry + exp backoff + fail-cache).

Phase 10 del milestone v1.1 introduce `aio.py` en matriz-client + el TokenStore.
Estos dos blockers están **completamente resueltos** vía spiking; Phase 10 puede
planificarse sin nuevos blockers arquitectónicos.

Spike sessions wrapped: 2026-06-12 (initial 4 spikes), 2026-06-12 (003 appended)
</context>

<requirements>
## Requirements

Decisiones non-negotiables que emergieron durante el spiking y deben honrarse en el real build de Phase 10:

### TokenStore (lock primitive) — from Spikes 001a/b/c/002

- **Stdlib only** — no agregar dependencies a `matriz-client` (es publishable wheel). Toolbox: `threading`, `asyncio`, `dataclasses`, `time`, `random`, `typing`. Quedan excluidas librerías como `aiologic` / `aiotools`.
- **Sync callers no deben necesitar conocer el asyncio loop.** Los métodos sync (`Client.get_X(...)` desde main thread, `ws_client` daemon thread) llaman `store.get_sync()` directamente — sin `asyncio.run_coroutine_threadsafe`, sin loop reference, sin bridge thread.
- **Refresh exactamente 1 vez** ante N callers concurrentes con token expirado — validado a 205 callers (100 sync + 100 async + 5 daemon). Atomicidad garantizada incluso entre múltiples event loops.
- **Event loop NO bloqueado > 5ms** durante refresh. El refresh es sync (~50-500ms para llamadas de red reales) y debe correr en `asyncio.to_thread` para no starvear el loop. Validado rigurosamente: 115 ticks de unrelated work durante 100ms refresh window.
- **Cross-loop atomicity vía `threading.Lock`** (loop-agnostic source of truth). `asyncio.Lock` se usa SOLO lazy-per-loop como coordinación local — nunca shared entre loops (este es el landmine que descalifica el patrón pure-asyncio).

### RefreshPolicy (retry semantics) — from Spike 003

- **NO retry para permanent errors (401/403/400)** — propagación inmediata. Retrying wrong credentials nunca succeeds y waste el time del auth server.
- **Retry para transient errors (5xx, network timeouts)** con bounded attempts (default 3 retries, configurable).
- **Respetar el server's `Retry-After` para 429** vía `RateLimitedRefreshError.retry_after_seconds`.
- **Fail-cache después de exhausted retries**. Cachea el último exception por una ventana configurable (default 30s). Llamadas subsiguientes dentro de la ventana raise el exception cacheado **SIN** llamar refresh_fn. **Este es el DOS prevention.**
- **Permanent errors NO se fail-cachean.** Por design — cachear delays el inevitable AND bloquea credential-update recovery por `fail_cache_s` segundos.
- **El refresh adapter debe mapear** httpx exceptions → `RefreshError` subclasses correctamente. **Esta classification es el contrato pluggable.**
- **Separation of concerns**: TokenStore = lock semantics; RefreshPolicy = retry semantics. **No combinar** en una clase única.

</requirements>

<findings_index>
## Feature Areas

| Area | Reference | Key Finding |
|------|-----------|-------------|
| TokenStore 3-way (sync + asyncio + daemon thread) | references/tokenstore-3way.md | Double-Checked Locking pattern: `threading.Lock` (state, cross-loop atomic) + per-loop lazy `asyncio.Lock` (intra-loop herd prevention) + `asyncio.to_thread` (free the loop during refresh). 205-caller stress test passes con 1 refresh, 0 errors, P95 cached async read < 0.01ms. |
| Refresh policy (retry + backoff + fail-cache) | references/refresh-policy.md | Decorator over `refresh_fn`. Transient/Permanent/RateLimited classification via exception types. **Fail-cache prevents auth-server DOS** — validated: 10 concurrent sync callers post-failure → 0 new auth server hits. Permanent errors propagate immediately (no retry, no fail-cache). |

## Source Files

Original spike source files are preserved in `sources/` for complete reference:

- `sources/001a-tokenstore-threading-lock-to_thread/` — baseline alternative (VALIDATED)
- `sources/001b-tokenstore-asyncio-lock-run_threadsafe/` — invalidated approach (landmine: cross-loop asyncio.Lock binding)
- `sources/001c-tokenstore-double-checked-locking/` — **winning lock pattern**
- `sources/002-tokenstore-3way-integration-stress/` — 205-caller stress validation
- `sources/003-tokenstore-refresh-policy/` — **winning retry pattern** (composes with 001c)

</findings_index>

<integration_blueprint>
## Phase 10 Integration Blueprint

Both feature areas compose cleanly:

```python
# packages/matriz-client/src/matriz_client/_token_store.py (Phase 10)

from ._refresh_policy import RefreshPolicy
from ._refresh import MatrizRefresh  # adapter: httpx → RefreshError subclasses
from ._refresh_errors import (
    PermanentRefreshError, TransientRefreshError, RateLimitedRefreshError
)


def build_token_store(state, *, max_retries=3, fail_cache_s=30.0):
    """Build a Phase-10 TokenStore composed with retry policy."""
    adapter = MatrizRefresh(
        http_client=state.http_client,
        base_url=state.base_url,
        username=state.username,
        password=state.password,
    )
    policy = RefreshPolicy(
        max_retries=max_retries,
        base_backoff_s=1.0,
        max_backoff_s=30.0,
        jitter=0.25,
        fail_cache_s=fail_cache_s,
    )
    return TokenStore(
        ttl_seconds=23 * 3600,  # matriz tokens
        refresh_fn=policy.wrap(adapter),
    )
```

This composition is **production-ready**. The unknowns that remain are
Phase-10-plan decisions (not architectural):

1. **Adapter location**: `_refresh.py` or inside `_token_store.py`?
2. **Policy params via `configure()`**: should users override `max_retries` / `fail_cache_s`?
3. **`_async_locks` dict leak**: accept-and-document, bounded LRU, or `WeakValueDictionary`?

</integration_blueprint>

<metadata>
## Processed Spikes

- 001a-tokenstore-threading-lock-to_thread (VALIDATED, comparison)
- 001b-tokenstore-asyncio-lock-run_threadsafe (INVALIDATED, comparison — landmine documented)
- 001c-tokenstore-double-checked-locking (VALIDATED, comparison — winner: lock primitive)
- 002-tokenstore-3way-integration-stress (VALIDATED, standard — 205-caller production-ready under stress)
- 003-tokenstore-refresh-policy (VALIDATED, standard — winner: retry policy, fail-cache prevents DOS)
</metadata>
