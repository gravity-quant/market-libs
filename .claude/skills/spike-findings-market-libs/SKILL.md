---
name: spike-findings-market-libs
description: Implementation blueprint from spike experiments. Requirements, proven patterns, and verified knowledge for building market-libs (specifically the Phase 10 matriz TokenStore for 3-way concurrent token sharing across sync REST + async REST + ws_client daemon thread). Auto-loaded during implementation work.
---

<context>
## Project: market-libs

market-libs es un monorepo de clientes Python para servicios financieros argentinos
(iol-client, higyrus-client, matriz-client, ambito-financiero-client, wallets-client).
Las spikes pre-Phase 10 resuelven la primitiva de lock para un TokenStore compartido
entre 3 contextos concurrentes: sync REST callers, async REST callers (posiblemente en
loops user-owned), y un daemon thread de fondo (`ws_client` con `websocket-client`).

Phase 10 del milestone v1.1 introduce `aio.py` en matriz-client + el TokenStore.
Antes de planificar Phase 10 era necesario validar QUÉ primitiva de concurrencia
funciona en los 3 contextos sin bloquear el event loop ni perder atomicidad. Los
spikes resuelven esa pregunta de forma definitiva.

Spike sessions wrapped: 2026-06-12
</context>

<requirements>
## Requirements

Decisiones non-negotiables que emergieron durante el spiking y deben honrarse en el real build de Phase 10:

- **Stdlib only** — no agregar dependencies a `matriz-client` (es publishable wheel). Toolbox: `threading`, `asyncio`, `dataclasses`, `time`. Quedan excluidas librerías como `aiologic` / `aiotools`.
- **Sync callers no deben necesitar conocer el asyncio loop.** Los métodos sync (`Client.get_X(...)` desde main thread, `ws_client` daemon thread) llaman `store.get_sync()` directamente — sin `asyncio.run_coroutine_threadsafe`, sin loop reference, sin bridge thread.
- **Refresh exactamente 1 vez** ante N callers concurrentes con token expirado — validado a 205 callers (100 sync + 100 async + 5 daemon). Atomicidad garantizada incluso entre múltiples event loops.
- **Event loop NO bloqueado > 5ms** durante refresh. El refresh es sync (~50-500ms para llamadas de red reales) y debe correr en `asyncio.to_thread` para no starvear el loop. Validado rigurosamente: 115 ticks de unrelated work durante 100ms refresh window.
- **Cross-loop atomicity vía `threading.Lock`** (loop-agnostic source of truth). `asyncio.Lock` se usa SOLO lazy-per-loop como coordinación local — nunca shared entre loops (este es el landmine que descalifica el patrón pure-asyncio).

</requirements>

<findings_index>
## Feature Areas

| Area | Reference | Key Finding |
|------|-----------|-------------|
| TokenStore 3-way (sync + asyncio + daemon thread) | references/tokenstore-3way.md | Double-Checked Locking pattern: `threading.Lock` (state, cross-loop atomic) + per-loop lazy `asyncio.Lock` (intra-loop herd prevention) + `asyncio.to_thread` (free the loop during refresh). 205-caller stress test passes con 1 refresh, 0 errors, P95 cached async read < 0.01ms. |

## Source Files

Original spike source files are preserved in `sources/` for complete reference:

- `sources/001a-tokenstore-threading-lock-to_thread/` — baseline alternative (VALIDATED)
- `sources/001b-tokenstore-asyncio-lock-run_threadsafe/` — invalidated approach (landmine: cross-loop asyncio.Lock binding)
- `sources/001c-tokenstore-double-checked-locking/` — **winning pattern (THE PATTERN)**
- `sources/002-tokenstore-3way-integration-stress/` — 205-caller stress validation

</findings_index>

<metadata>
## Processed Spikes

- 001a-tokenstore-threading-lock-to_thread (VALIDATED, comparison)
- 001b-tokenstore-asyncio-lock-run_threadsafe (INVALIDATED, comparison — landmine documented)
- 001c-tokenstore-double-checked-locking (VALIDATED, comparison — winner)
- 002-tokenstore-3way-integration-stress (VALIDATED, standard — production-ready under stress)
</metadata>
