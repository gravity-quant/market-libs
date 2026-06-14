# Phase 10 Discussion Log

**Date:** 2026-06-13
**Phase:** 10-matriz-aio-py-creation-tokenstore
**Mode:** discuss (default — no flags)
**Audience:** Phase 10 retrospective / forensic audit reference. NOT consumed by downstream agents — they read `10-CONTEXT.md` only.

---

## Gray Areas Presented to User

Domain boundary stated: "Crear `matriz_client.AsyncClient` con full REST mirror (22 endpoints) + `TokenStore` 3-way concurrent + `_atransport.py` + migración de `ws_client.py` + paridad live sync↔async."

Carrying-forward summary presented (locked decisions from Phase 6-9 + spike-findings skill):
- Lock primitive: Double-Checked Locking (Spike 001c)
- RefreshPolicy semantics (Spike 003)
- Stdlib only
- Sync callers no event loop knowledge
- ttl 23h
- PEP 562 shim back-compat
- pytest-asyncio fixtures pattern iol
- AsyncRetryTransport mirror iol `_atransport.py`
- NO tocar `_state.py:55 account_id` (ORP-01 Phase 11 CR-08)
- NO re-arquitectar `ws_client.py` daemon-thread
- 1 commit atómico por plan
- `from __future__ import annotations` mandatory

4 candidate gray areas presented via AskUserQuestion (multiSelect):

1. **Layout de archivos TokenStore/RefreshPolicy** — spike blueprint sugiere 3 files separados; convention market-libs es `_*.py` chico-y-focused.
2. **Exposición de policy knobs vía `configure()`** — qué knobs de los 5 (max_retries, fail_cache_s, base_backoff_s, max_backoff_s, jitter) exponer en public API.
3. **`_async_locks` dict lifecycle** — leak management para per-loop locks.
4. **Entry point para live verification (LIVE-02)** — `main_matriz.py --async` vs `verify_async()` vs script separado.

**User selected:** 1, 2, 3 (skipped 4).

---

## Area 1: Layout de archivos TokenStore/RefreshPolicy

**Question asked:** "¿Cómo distribuímos TokenStore + RefreshPolicy + adapter + errors en archivos?"

**Options presented:**

- **A. 4 archivos (máxima cohesión)** — `_token_store.py` + `_refresh_policy.py` + `_refresh.py` (adapter) + `_refresh_errors.py` (3 exception subclasses). +5 files / +~530 LOC.
- **B. 3 archivos (errors inline en refresh)** — `_token_store.py` + `_refresh_policy.py` + `_refresh.py` (incluye RefreshError subclasses al top). +4 files.
- **C. 2 archivos (adapter+errors inline en TokenStore)** — `_token_store.py` (todo junto: store + adapter + errors) + `_refresh_policy.py`. +3 files.
- **D. 1 archivo concentrado** — `_token_store.py` (todo: store + policy + adapter + errors). +2 files.

**User selection:** A. 4 archivos (máxima cohesión).

**Captured as:** D-01 (file layout) + D-02 (TokenStore en `_token_store.py`, NO en `_state.py`).

**Notes:**
- ROADMAP literal "(en `_state.py` o `_token_store.py`)" se resuelve a `_token_store.py` por la elección A (separación cohesiva).
- Spike blueprint composition pattern (`build_token_store(state, max_retries, fail_cache_s)`) traceable as-is con la decisión.
- 5 archivos nuevos finales (4 above + `_atransport.py` Phase 8 D-25 carve-out).

---

## Area 2: Exposición de policy knobs vía `configure()`

**Question asked:** "¿Qué policy knobs exponemos en el public API (configure() + AsyncClient.__init__)?"

**Options presented:**

- **A. Solo `max_retries` (status quo Phase 8)** — Recomendado. Resto hardcoded a defaults validados por el spike.
- **B. `max_retries` + `fail_cache_s`** — Los dos knobs operacionalmente significativos para DOS-prevention.
- **C. Los 4 knobs completos** — Full control. API surface +5 params nuevos.
- **D. Solo via `build_token_store()` interno (sin public override)** — `configure()` no toca knobs del store. Sigue Phase 8 max_retries piggyback.

**User selection:** A. Solo `max_retries` (status quo Phase 8) (Recomendado).

**Captured as:** D-03 (max_retries reuse) + D-04 (ttl_seconds hardcoded).

**Notes:**
- Defaults internals: `fail_cache_s=30.0`, `base_backoff_s=1.0`, `max_backoff_s=30.0`, `jitter=0.25`.
- v1.2 backlog si emerge demanda real de tuning (logs operacionales podrían surface need de `fail_cache_s` mayor en deployments con auth flakey).
- ttl_seconds=23*3600 NO se expone (cambiar TTL sin coordinar con server es bug).

---

## Area 3: `_async_locks` dict lifecycle

**Question asked:** "¿Cómo manejamos el lifecycle del per-loop _async_locks dict?"

**Options presented:**

- **A. Accept-and-document (process-lifetime)** — Recomendado. `_async_locks: dict[int, asyncio.Lock]` keyed por `id(loop)`. NO cleanup. ~80B leaked per dead loop. Production (1 loop) = 0 leak; tests = ~63KB CI total; multi-loop apps anti-pattern documentado.
- **B. WeakKeyDictionary keyed by loop** — `weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock]`. Cleanest semantic + auto-GC; complexity de asyncio loop weakref edge cases.
- **C. Explicit cleanup via `aclose()` + atexit** — AsyncClient.aclose() limpia su entry. Push lifecycle al caller.

**User selection:** A. Accept-and-document (process-lifetime) (Recomendado).

**Captured as:** D-05 (`_async_locks` lifecycle).

**Notes:**
- Tradeoff documented inline en TokenStore docstring + nota operacional en `.planning/codebase/CONCERNS.md` (Plan 10-01 escribe).
- v1.2 backlog si el perfil de memoria muestra growth real (improbable per spike validation, 0 leak detected con 205-caller stress test).
- Alternativas rechazadas (B, C) preservadas en `<deferred>` section por si emerge use case.

---

## Area 4: Entry point para live verification (LIVE-02)

**Question:** Was offered as a candidate gray area.

**User decision:** NOT selected for discussion.

**Resolution:** Captured as D-06 (Claude's discretion).

**Recommendation by orchestrator (inherits if planner doesn't override):**
- Seguir el patrón `main_iol.py` — probes sync + async interleaved en el mismo `main()`, sin flag.
- Each existing sync probe gains an async paired probe.
- Outcome reporter compara sync↔async y reporta PASS/FAIL/DRIFT per probe.
- WebSocket-dependent probes skip async con razón documentada.

Rationale: paridad sync↔async es el verdadero outcome de LIVE-02; interleaving los expone juntos; match con `main_iol.py` reduce cognitive load cross-driver; no flag necesario.

Planner puede revisar y proponer alternativa si encuentra signal técnico en el código que justifique flag-based (e.g., async probes triplican runtime y operador quiere on-demand).

---

## Claude's Discretion (additional items captured in CONTEXT.md)

- Field naming: `token_store` (no leading underscore) en `_state.py`.
- Adapter class name: `MatrizRefresh` (spike blueprint).
- AsyncClient `_aensure_token` impl: usa `get_async()` nativo del store (no `asyncio.to_thread` doble-hop).
- AsyncClient PEP 562 shim: NO agrega denials nuevos (back-compat preservado).
- `token_store` lazy init en `_get_default()`, no constructor injection (matches Phase 6 idiom).
- `test_async_client.py` layout: split por concern (auth, queries, mutations) — affinity con sync test structure.
- Probe async naming: `probe_X_async()` suffix idiom (match `main_iol.py`).
- Snapshot diff documentation en Plan 10-04 VALIDATION.md: full diff inline.
- TokenStore `_async_locks` tradeoff documentation: docstring inline + CONCERNS.md entry.

---

## Plan Slicing Captured (D-07)

4 planes en wave orchestration:

- **Plan 10-01 (Wave 1):** TokenStore + RefreshPolicy + adapter + errors primitive + unit/stress tests. Standalone testable. 1 commit.
- **Plan 10-02 (Wave 2):** `_atransport.py` + AsyncClient full REST surface + async tests. 1 commit.
- **Plan 10-03 (Wave 3):** State wiring + sync/async/ws_client migration + cross-thread integration test. 1 commit.
- **Plan 10-04 (Wave 4):** Live verification paridad + green gate + snapshot regen + 3 skips flipped. 1 commit.

---

## Deferred Ideas Captured

Stored in `10-CONTEXT.md <deferred>` section. Highlights:

- WeakKeyDictionary cleanup para `_async_locks` (v1.2 if growth matters)
- Explicit aclose() lifecycle (v1.2 if Pitfall #12 emerges as blocker)
- `fail_cache_s` / `base_backoff_s` / `max_backoff_s` / `jitter` public expose (v1.2 if tuning need surfaces)
- TokenStore reuso en iol/higyrus (probably NO — no 3-way pressure)
- AsyncClient explicit token_store injection (v1.2 if testing patterns demand)
- Generated-code dual-emit (v1.2+)
- `MATRIZ_SAMPLE_INSTRUMENTS` env var (v1.2 if needed)
- Live verification del WebSocket layer (v1.2+)
- `Client.from_env()` (REQUIREMENTS Future)
- `Client.with_options()` per-call override (REQUIREMENTS Future)
- disk persistence del matriz token (acceptable for now)
- prod-vs-remarkets verification (D-MATZ-27, v1.2)
- TODO `matriz-driver-findings-file-handling` reviewed but NOT folded (Phase 11 HARN-07/08/10 scope).

---

*Discussion log written for human reference (audit/retrospective). CONTEXT.md is the authoritative input for the planner.*
