# Phase 14 Discussion Log

**Date:** 2026-06-15
**Phase:** 14 - IOL Disk Persistence (SEC-01)
**Mode:** discuss (default)

This log captures the discussion that produced `14-CONTEXT.md`. Used for audits
and retrospectives only — NOT consumed by downstream agents (researcher, planner,
executor).

## Domain boundary presented

Persistir el `refresh_token` de IOL en disco para que `main_iol.py` saltee el
password grant entre reinicios, sin leakearlo a logs ni perderlo bajo concurrencia
multi-proceso. Single-package scope: iol-client only.

**Pre-locked by ROADMAP/REQUIREMENTS/research (no se discutió):**

- API surface: `Client(token_cache_path=Path(...))` + `IOL_TOKEN_CACHE_PATH` env +
  `platformdirs.user_data_dir("iol-client", "market-libs")` default
- Concurrency: `fcntl.flock` POSIX
- Permisos: `chmod 0600` archivo + `0700` parent dir
- CI safety: `os.environ["CI"]=="true"` rechaza default
- Atomic write-then-rename
- Cleanup on 401: borra disk token
- Logging: `logging.getLogger("iol_client.*")` namespace para `RedactingFilter`
- 3 CRITICAL merge gates (sentinel `REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210`,
  20-thread flock race, failed-refresh cleanup)
- `platformdirs >=4.0,<5` solo en iol-client pyproject
- Phase 13 D-V4 view comparte `_state` (refresh_token y token_cache_path) con parent

## Gray areas presented for selection

Cuatro áreas presentadas (multiSelect):

1. ☑ **Formato del archivo en disco** — JSON shape, metadata fields, forward-compat
2. ☑ **Cobertura sync vs async** — sync helpers + `asyncio.to_thread` wrapper vs aiofiles vs sync-block
3. ☑ **Corrupt-file recovery policy** — log + None vs log + delete vs quarantine vs raise
4. ☑ **Plan slicing + cross-cutting tests** — 2 vs 3 vs 4 plans

**Selected:** las 4 áreas (full discussion).

## Decisions captured

### Área 1 — File format on disk (D-F1)

**Question:** ¿Qué shape de JSON guarda el _token_cache en disco?

**Options presented:**

- A. JSON con metadata (`{version: 1, refresh_token, acquired_at}`) — **Recomendado**
- B. JSON minimalista (`{refresh_token}`)
- C. Plain text (just the token string)

**User selected:** A.

**Rationale captured in CONTEXT.md `<decisions>` D-F1:**

- `version: 1` para forward-compat (v1.3+ encryption-at-rest, multiple tokens, etc.)
- `acquired_at` para audit ergonomics, NO usado como TTL gate (IOL no documenta TTL cliente)
- UTF-8, sin trailing newline, ~200-300 bytes

### Área 2 — Sync/async coverage (D-A1)

**Question:** ¿Cómo iol_client/aio.py interactúa con el disk cache?

**Options presented:**

- A. `asyncio.to_thread` sobre helpers sync — **Recomendado**
- B. `aiofiles` para I/O async puro
- C. I/O sync directo en `_aensure_token` (bloquea event loop)

**User selected:** A.

**Rationale captured in CONTEXT.md `<decisions>` D-A1:**

- `_token_cache.py` expone solo helpers sync (`load`, `save`, `delete`)
- `client.py` los invoca directamente
- `aio.py` los invoca vía `await asyncio.to_thread(_token_cache.{load,save,delete}, ...)`
- DRY (un solo code path), evita dep aiofiles
- `fcntl.flock` es sync syscall; no hay async port
- Bloqueo aceptable: flock + I/O ~microsegundos, vs network refresh ~cientos de ms
- Cancellation semantics: `asyncio.to_thread` no cancela el thread; documentado

### Área 3 — Corrupt-file recovery (D-C1)

**Question:** ¿Cómo recovera `_token_cache` cuando el archivo existe pero es corrupto?

**Options presented:**

- A. Log warning + treat as None + fall to password (NO se borra) — **Recomendado**
- B. Log + delete + fall to password
- C. Log + quarantine to `.corrupt-<ts>.json` + fall to password
- D. Raise `IOLClientError`

**User selected:** A.

**Rationale captured in CONTEXT.md `<decisions>` D-C1:**

- Triggered by: JSON inválido, campos ausentes, `version != 1`, refresh_token no es str
- Log line: `"ignoring unreadable token cache at %s (%s); falling back to password grant"` con
  solo path y `type(exc).__name__`. NUNCA incluye exc, args, ni file contents (anti-Pitfall 7)
- NO se borra el archivo — dejarlo para forensics manual
- Next successful `_refresh()` lo sobrescribe vía atomic write-rename
- Edge: si path apunta a directorio/device, captura `OSError` y devuelve None

### Área 4 — Plan slicing (D-P1)

**Question:** ¿Cuántos plans y cómo se slicen?

**Options presented:**

- A. 3 plans: tests-first cross-cutting + sync impl + async impl + green gate — **Recomendado**
- B. 2 plans: impl combined + tests + gate
- C. 4 plans: tests + sync + async + cleanup-policy separado

**User selected:** A.

**Rationale captured in CONTEXT.md `<decisions>` D-P1:**

- Plan 1 — Tests-first cross-cutting (RED en HEAD):
  - `verification/test_iol_disk_persistence.py` con 3 CRITICAL merge gates + 8 regression tests
  - `platformdirs >=4.0,<5` agregado a `packages/iol-client/pyproject.toml`
- Plan 2 — `_token_cache.py` + sync Client integration:
  - Nuevo módulo `_token_cache.py` con `load`, `save`, `delete` helpers
  - `_state.py` agrega `token_cache_path: Path | None = None` field
  - `Client.__init__` + `_ensure_token` + `_refresh` modifications
  - Tests sync flip RED → GREEN
- Plan 3 — Async + consolidated green gate:
  - `AsyncClient` mirror via `asyncio.to_thread`
  - Tests async flip RED → GREEN
  - Consolidated gate: pytest ≥981, ruff, mypy, lint-imports, pre-commit
- Atomic per-plan; Phase 13 D-P1 idiom validado

## Scope creep redirected

(none — user stayed within Phase 14 boundary)

## Folded todos

(none folded — `spike-codegen-libcst-v1.3.md` review identificado como off-scope para Phase 14)

## Reviewed todos (not folded)

- `spike-codegen-libcst-v1.3.md` (score 0.6, area: codegen) — para v1.3 driver-migration
  cross-pkg parity, NO para Phase 14 iol-only disk persistence.

## Deferred ideas captured

Ver `14-CONTEXT.md` `<deferred>` section. Resumen:

- Encrypted-at-rest token storage (defer a v1.3+)
- Windows ACL equivalente al 0600 (Linux/macOS target only)
- TTL del refresh_token con rotación proactiva (no documentado por IOL)
- Quarantine de corrupt files (D-C1 rejecta)
- Disk persistence para otros 3 paquetes (solo iol tiene OAuth refresh_token)
- Driver migration `main_iol.py` para token_cache_path (Phase 15 decide)
- `with_options(token_cache_path=...)` per-call override (Phase 13 scope-lock)
- `Client.cache_info()` inspect method (v1.3 si UX feedback)
- TRAVIS/JENKINS/etc CI detection (`CI==true` de facto standard suficiente)
- Multi-token cache para múltiples users IOL (v1.3+ si requirement)

## Claude's Discretion items (planner decides)

Ver `14-CONTEXT.md` `<decisions>` § "Claude's Discretion". Resumen:

- Ubicación exacta de `_resolve_default_path()` (recomendado: top-level en `_token_cache.py`)
- `save()` signature: `refresh_token: str, *, acquired_at: float` (vs dict opaco)
- `acquired_at` source: `time.time()` dentro del `save()` helper
- Atomic tempfile naming: `<path>.tmp.<pid>.<randhex>`
- Permission setup order: chmod 0600 sobre tempfile ANTES del `os.replace`
- `platformdirs` usage: `user_data_dir("iol-client", "market-libs")` con appauthor
- CI detection scope: `os.environ.get("CI") == "true"` solo (de facto standard)
- Logger naming: `logging.getLogger(__name__)` → `iol_client._token_cache`
- Test sentinel format: locked en SC #1 (verbatim)
- 20-thread test implementation: `ThreadPoolExecutor(max_workers=20)` con `secrets.token_hex`
- `__repr__` de Client con disk cache info: NO (privacidad path), defer

---

*Discussion completed: 2026-06-15*
