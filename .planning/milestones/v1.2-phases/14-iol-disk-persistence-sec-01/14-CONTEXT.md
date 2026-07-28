# Phase 14: IOL Disk Persistence (SEC-01) - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 14 entrega persistencia en disco del `refresh_token` de IOL para que un
operator que reinicia `main_iol.py` saltee el password grant cuando exista un
`refresh_token` válido en disco, **sin** leakearlo a logs ni perderlo bajo
concurrencia multi-proceso. **Single-package scope:** iol-client only — los
otros 3 paquetes no se tocan, ni en código ni en `pyproject.toml`.

**Surface delivered:**

- `Client(token_cache_path=Path(...))` opt-in kwarg + `IOL_TOKEN_CACHE_PATH`
  env var override + `platformdirs.user_data_dir("iol-client", "market-libs")`
  default cuando ambos son None y `CI != "true"`.
- `iol_client._token_cache` módulo nuevo: `load(path) -> dict | None`,
  `save(path, refresh_token, *, acquired_at)`, `delete(path)`,
  todos POSIX-locked vía `fcntl.flock`, todos atomic vía write-then-rename.
- `iol_client.Client._ensure_token()` y `iol_client.AsyncClient._ensure_token()`
  cargan el refresh_token desde disco en `__init__` si el path existe, y
  escriben en disco después de cada `_refresh()` exitoso.
- Anti-Pitfall 8 cleanup: en `_refresh()` 401 → password fallback, el código
  borra el disk token ANTES del password grant (idempotent: delete-if-exists,
  nunca delete-then-fail).

**Critical merge gates (3 tests, anti-Pitfalls 7/8/9, money-on-the-line):**

- **Anti-Pitfall 7 (caplog no-leak):** `test_disk_persistence_never_logs_token`
  ejercita el lifecycle completo (write-on-rotate → read-on-init → write-fail
  OSError → corrupt-file read) con `caplog.set_level(DEBUG, logger="iol_client")`,
  asserta que el sentinel `REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210` NO
  aparece en ningún record's `message`, `args`, ni `repr(extra)`.
- **Anti-Pitfall 9 (multi-process race):** `test_disk_token_write_under_concurrent_processes`
  spawnea 20 writer threads concurrentes (cada uno abre el archivo, toma `fcntl.flock`,
  escribe, hace atomic rename, cierra) y asserta que el archivo final contiene
  EXACTAMENTE 1 token válido (sin interleaving, sin truncation, sin double-write).
- **Anti-Pitfall 8 (failed-refresh cleanup):** `test_disk_token_deleted_on_refresh_401`
  seedea disco con `STALE-REFRESH-TOKEN`, mockea IOL respondiendo 401 al refresh,
  asserta que el disco después contiene el FRESH password-grant token (no el stale).

**CI safety (anti-Pitfall 10):** cuando `os.environ.get("CI") == "true"` Y el
operator NO pasó `token_cache_path` explícito (kwarg o env var), el `__init__`
rechaza el default-path silenciosamente — `_state.token_cache_path` queda en
None y el cache se deshabilita completo. Previene que CI runners shared dejen
tokens leakeados en `~/.local/share/iol-client/`.

**Phase 14 NO entrega:**

- Disk persistence para otros 3 paquetes — solo iol tiene OAuth refresh_token.
  ámbito/higyrus/matriz NO ganan `token_cache_path` kwarg. D-T4 negative.
- Encrypted-at-rest token storage — `0600` POSIX permissions es el threat model
  asumido. Defer a v1.3+ si surge requirement.
- Windows ACL equivalente al `0600` POSIX — el proyecto es Python 3.12+ targeted
  a Linux/macOS, CI matriz también Ubuntu. En Windows el `chmod` es no-op (Python
  documenta esto); el disk cache funcionará pero sin file permissions sealing.
- TTL del refresh_token (rotación proactiva) — IOL no documenta TTL de
  refresh_tokens en el cliente. El cleanup-on-401 (anti-Pitfall 8) es la
  invalidación canónica. `acquired_at` field se persiste para audit/debug, NO
  para gate de validez.
- Quarantine de corrupt files (`refresh_token.corrupt-<ts>.json`) — D-C1
  rejecta esta opción a favor de "log + treat as None".
- Driver migration de `main_iol.py` para consumir `token_cache_path` directamente
  — Phase 15 (REFAC-05) decide. Phase 14 entrega solo el surface.
- Live re-verification del path completo — Phase 17 LIVE-03 re-verifica que
  el disk cache no introdujo regresiones observables contra IOL real.

**Carry-forward de Phase 13 (con_options × disk cache, ya validado):**

- View `client.with_options(max_retries=10)` comparte `_state.refresh_token`
  y `_state.token_cache_path` con el parent. Si el view dispara un 401 → refresh
  → disk write, el parent ve el token actualizado vía shared `_state`.
- Anti-Pitfall 14 mutation gate sigue siendo la autoridad — `with_options(max_retries=10)`
  NO afecta la mutación-gate eval order en `RetryTransport`. Phase 13 garantía.
- view `_is_view=True` → `close()` / `aclose()` no-op → NO borra el disk file.
  Solo el parent's `close()` puede impactar el lifecycle del disco (y por D-V1
  Phase 13 tampoco lo hace; el disk file es persistente por design).

**Carry-forward de v1.1 (no se re-toca):**

- BUG-03 in-instance refresh_token lifecycle (`refresh→success`, `refresh→401→password`,
  `preserve-on-omit`, `rotate-on-provide`) — Phase 14 EXTIENDE estos 4 paths × disco
  pero NO modifica la lógica in-memory.
- LOG-02 `RedactingFilter` per-package sobre `logging.getLogger("iol_client")` con
  NullHandler — `_token_cache.py` usa `logging.getLogger(__name__)` (= `iol_client._token_cache`)
  para heredar el filter automáticamente (anti-Pitfall 7 mitigation source).
- `_refresh_policy.py` fail-cache TTL — Phase 14 NO toca; el cleanup-on-401 path
  reseta el cache vía la API existente.

</domain>

<decisions>
## Implementation Decisions

### File format on disk

- **D-F1: JSON con metadata mínima.** El archivo `refresh_token.json` contiene:

  ```json
  {
    "version": 1,
    "refresh_token": "<token-string>",
    "acquired_at": 1718450000.0
  }
  ```

  - `version`: int, hoy siempre `1`. Forward-compat para v1.3+ si necesitamos
    rotar el schema (encryption-at-rest, multiple tokens cacheados, etc.).
  - `refresh_token`: el string opaco que IOL devuelve. Único campo sensible.
  - `acquired_at`: Unix timestamp (float, segundos) — momento del refresh exitoso
    que produjo este token. Útil para audit ("¿de cuándo es este token?") pero
    NO se usa para gate de validez (IOL no documenta TTL cliente).

  Sin trailing newline necesario (es JSON, no plain text). Encoding UTF-8.
  Tamaño esperado: ~200-300 bytes.

### Sync/async file I/O coverage

- **D-A1: `_token_cache.py` expone helpers sync; `aio.py` los invoca vía `asyncio.to_thread`.**
  - `iol_client._token_cache.load(path: Path) -> dict | None` — abre, flock LOCK_SH,
    lee, parsea JSON, devuelve dict o None.
  - `iol_client._token_cache.save(path: Path, refresh_token: str, *, acquired_at: float) -> None`
    — crea parent dir 0700 si no existe, escribe a tempfile, flock LOCK_EX sobre el
    tempfile, atomic `os.replace(tempfile, path)`, chmod 0600.
  - `iol_client._token_cache.delete(path: Path) -> None` — `path.unlink(missing_ok=True)`
    bajo flock LOCK_EX si el archivo existe.
  - `client.py` los invoca sync directamente; `aio.py` los invoca vía
    `await asyncio.to_thread(_token_cache.load, path)`. Un solo code path
    (DRY), evita aiofiles dep extra, fcntl.flock sigue siendo POSIX syscall sync.
  - Bloqueo en `_aensure_token()`: aceptable. El TokenStore primitive no aplica
    a iol (es matriz-only); el flock+I/O se mide en microsegundos vs network refresh
    en cientos de ms. Documentar en docstring.
  - `asyncio.to_thread` no respeta cancellation para syscalls bloqueantes — si el
    operator cancela el await mientras el thread tiene flock + escritura, el thread
    completa (el flock se libera on close). Documentar en `_token_cache.py` module
    docstring.

### Corrupt-file recovery policy

- **D-C1: Log warning + treat as None + fall to password grant. NO se borra.**
  - Cuando `load()` encuentra el archivo pero falla a parsearlo:
    - JSON inválido (`json.JSONDecodeError`)
    - Campos ausentes (`refresh_token` o `version` o `acquired_at`)
    - `version != 1` (forward-incompat)
    - `refresh_token` no es str o es empty
  - El helper devuelve `None` silenciosamente Y loggea exactamente UN warning:

    ```python
    logger.warning(
        "ignoring unreadable token cache at %s (%s); falling back to password grant",
        path, type(exc).__name__,
    )
    ```

  - Crítico: el log line NO incluye `exc` ni `repr(exc.args)` ni el contenido del
    archivo — solo `type(exc).__name__` y el path. Anti-Pitfall 7 mitigation.
  - NO se borra el archivo: dejarlo para forensics manual. El próximo
    `_refresh()` exitoso lo sobrescribe vía atomic write-rename (idempotent).
  - Esto es consistente con el cleanup-on-401 path (que SÍ borra), porque ese
    borrado es response al server invalidating el token, mientras que corrupt-file
    es indeterminate state.
  - Edge case: si el operator pasa `token_cache_path=Path(...)` apuntando a un
    archivo que no es JSON ni va a serlo (e.g., directorio, dispositivo), `load()`
    captura el `OSError` y devuelve None igualmente. NO se intenta recovery del
    path config — eso es operator error y se loggea como warning.

### Plan slicing (3 plans, tests-first cross-cutting)

- **D-P1: 3 plans — tests-first cross-cutting (Plan 1 RED en HEAD) + sync impl
  (Plan 2) + async impl + green gate (Plan 3).**

  - **Plan 1 — Cross-cutting tests + dep (tests-first, RED en HEAD):**
    - Agrega `platformdirs >=4.0,<5` a `packages/iol-client/pyproject.toml`
      `[project.dependencies]` (NO al root, NO a otros paquetes).
    - Crea `verification/test_iol_disk_persistence.py` con los 3 CRITICAL merge
      gate tests + esqueleto para los 8+ regression tests:
      - `test_disk_persistence_never_logs_token` (anti-Pitfall 7, caplog DEBUG, sentinel guard)
      - `test_disk_token_write_under_concurrent_processes` (anti-Pitfall 9, 20 threads + flock)
      - `test_disk_token_deleted_on_refresh_401` (anti-Pitfall 8, stale → 401 → password)
      - 8 regression tests = 4 BUG-03 lifecycle paths × {sync, async}:
        - `test_disk_token_loaded_on_init_skips_password_<sync/async>`
        - `test_disk_token_written_after_successful_refresh_<sync/async>`
        - `test_disk_token_preserved_when_no_kwarg_<sync/async>`
        - `test_disk_token_rotated_on_explicit_path_<sync/async>`
    - Tests RED en HEAD por D-P1 idiom (no existe `Client(token_cache_path=...)`
      todavía; Plan 2-3 los flippean GREEN).
    - NO toca `client.py` / `aio.py` / `_state.py` — solo `pyproject.toml`,
      tests, y crea `verification/test_iol_disk_persistence.py`.
    - CI gate config: `os.environ["CI"]=="true"` check entra en Plan 2 (donde
      vive el `_token_cache.py` con la default-path resolution).

  - **Plan 2 — `_token_cache.py` + sync Client integration:**
    - Crea `packages/iol-client/src/iol_client/_token_cache.py` con:
      - `_resolve_default_path()` — usa platformdirs cuando `CI != "true"`;
        devuelve None cuando CI.
      - `load(path) -> dict | None` con corrupt-recovery por D-C1.
      - `save(path, refresh_token, *, acquired_at)` con atomic write-rename +
        flock LOCK_EX + chmod 0600 + parent dir 0700.
      - `delete(path)` idempotent con flock LOCK_EX.
    - Modifica `iol_client/_state.py` agregando `token_cache_path: Path | None = None`
      field (similar al precedent de Phase 13 D-T3 `client_max_retries` matriz-only;
      acá iol-only). NO se agrega a otros paquetes.
    - Modifica `Client.__init__`: acepta `token_cache_path: Path | None = None`
      kwarg; resolve precedence: explicit kwarg → `os.environ.get("IOL_TOKEN_CACHE_PATH")`
      → `_resolve_default_path()` (None si CI). Setea `self._state.token_cache_path`.
    - Modifica `Client._ensure_token()`: si `_state.token_cache_path` existe y
      `_state.refresh_token is None`, llama `_token_cache.load(path)` y popula
      `_state.refresh_token` desde el dict si éxito.
    - Modifica `Client._refresh()`: después del refresh exitoso, llama
      `_token_cache.save(path, new_refresh_token, acquired_at=time.time())`.
      Después del 401 → password fallback, llama `_token_cache.delete(path)`
      antes del password grant (anti-Pitfall 8 cleanup).
    - Tests sync de Plan 1 deben quedar GREEN al finalizar Plan 2. Async siguen RED.
    - Acceptance: `uv run --package iol-client pytest packages/iol-client/tests/` + sync rows
      de `verification/test_iol_disk_persistence.py` GREEN.

  - **Plan 3 — Async Client integration + consolidated green gate:**
    - Modifica `iol_client/aio.py`: `AsyncClient.__init__` mirror del sync —
      acepta `token_cache_path` kwarg, resolve precedence idéntica, setea
      `self._state.token_cache_path`. `_aensure_token()` y `_arefresh()`
      llaman al sync helper vía `asyncio.to_thread(_token_cache.load|save|delete, ...)`.
    - Mirror exacto del sync (Phase 13 D-V3 idiom: cero divergencia surface).
    - Async rows de los 8 regression tests + cross-cutting CRITICAL gates pasan a GREEN.
    - **Consolidated green gate** (Plan 5 idiom de Phase 13):
      - `uv run pytest` full monorepo: ≥ 981 passing (973 baseline Phase 13 post-fix
        + ≥ 8 regression tests Phase 14 = 981 mínimo)
      - `uv run ruff check` exits 0
      - `uv run ruff format --check` exits 0
      - `uv run mypy` (project config) exits 0
      - `uv run lint-imports` exits 0 (verificar no import-linter regression de
        nuevo módulo `_token_cache.py`)
      - `pre-commit run --all-files` exits 0
    - Snapshot: `verification/snapshots/iol-client-surface.txt` se regenera. El
      `Client.__init__` ahora tiene un kwarg extra `token_cache_path` — el
      snapshot enumerator probablemente capture el cambio si walk el signature
      (D-V5 Phase 13 documentó que el enumerator solo walks `__all__` module-level
      names; el `Client.__init__` signature depende del implementation del enumerator,
      a confirmar en planning). Si el snapshot diff es cero, se documenta tal cual
      Phase 13 lo hizo.

- **D-P2: cross-cutting tests viven en `verification/`, NO en `packages/iol-client/tests/`.**
  Los 3 CRITICAL merge gates + 8 regression tests son tests del shape
  inter-iol (disk cache es state que persiste cross-process y cross-instance),
  no del Client individual. Vive en `verification/test_iol_disk_persistence.py`
  (archivo nuevo, separado del existing `verification/test_logging_no_token_leak.py`
  de v1.1 LOG-02 que tiene scope más amplio). Sigue idiom Phase 13 D-P2.

- **D-P3: Atomic write-then-rename con `os.replace`.**
  El `save()` helper escribe a `<path>.tmp.<pid>.<randhex>`, hace flock LOCK_EX,
  fsync, close, chmod 0600, y luego `os.replace(tmp, path)` que es atomic on POSIX
  (man rename(2): "If newpath already exists, it will be atomically replaced").
  Esto garantiza que la lectura concurrente NUNCA ve un archivo truncado o
  parcialmente escrito. Plan 2 detail.

### Claude's Discretion

El planner decide:

- **Ubicación exacta de `_resolve_default_path()`.** Recommend: top-level helper
  en `_token_cache.py` (módulo-level function), invocado desde `Client.__init__`.
  Alternativas: helper privado dentro de `_state.py` (cerca del field), o classmethod
  en Client (más visible). Recommendation: `_token_cache.py` para co-locación con
  el resto de la disk-cache logic.

- **`_token_cache.save()` signature: `refresh_token` arg vs full dict.**
  Recommend: tomar `refresh_token: str, *, acquired_at: float` por args explícitos
  (más type-safe que un dict opaco; mypy strict catches misnamed fields). El helper
  construye el dict internamente.

- **`acquired_at` source.** Recommend: `time.time()` invocado dentro del `save()`
  helper (no del caller) — single source of truth, evita drift entre sync/async
  callers.

- **Atomic tempfile naming.** Recommend: `<path>.tmp.<pid>.<randhex>` para evitar
  colisión cuando dos procesos hacen save concurrente (que NO debería pasar bajo
  flock, pero defense in depth).

- **Permission setup order.** Recommend: chmod 0600 sobre el TEMPFILE antes del
  `os.replace`, así el archivo final tiene los permisos desde el primer momento
  (no hay window donde el archivo es 0644 antes de chmod). Parent dir 0700 se
  setea con `os.makedirs(parent, mode=0o700, exist_ok=True)` o `parent.chmod(0o700)`
  defensivo si ya existe.

- **`platformdirs` usage exact.** Recommend: `platformdirs.user_data_dir("iol-client",
  "market-libs")` con appauthor=`market-libs`. Sobre macOS produce
  `~/Library/Application Support/market-libs/iol-client/`; sobre Linux ignora el
  appauthor y produce `~/.local/share/iol-client/`. Estos son los paths
  documentados en REQUIREMENTS.md §SEC-01.

- **CI detection scope.** Recommend: usar solo `os.environ.get("CI") == "true"`
  como el de facto standard (GitHub Actions, GitLab CI, CircleCI, Travis, Drone,
  Bitbucket Pipelines, AWS CodeBuild todos lo setean). NO se complica con detección
  de TRAVIS/JENKINS/etc específicos. Documentado.

- **Logger naming inside `_token_cache.py`.** Recommend: `logger = logging.getLogger(__name__)`
  → produce `iol_client._token_cache` que hereda del `RedactingFilter` instalado en
  `iol_client` por v1.1 LOG-02. Anti-Pitfall 7 mitigation source.

- **Test sentinel exact format.** Locked en SC #1: `REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210`.
  Plan 1 lo usa verbatim.

- **20 thread count for concurrency test.** Locked en SC #2: 20 threads. Plan 1 lo usa
  verbatim. NOTA implementación: `concurrent.futures.ThreadPoolExecutor(max_workers=20)`
  con 20 `submit()` calls — cada uno abre el archivo, flock, escribe, rename, cierra.
  El assert final lee el archivo, parsea JSON, valida que `refresh_token` sea
  exactamente uno de los 20 tokens generados (no interleaved).

- **`__repr__` de Client con disk cache info.** El Client `__repr__` ya redacta
  password (Phase 6 D-18). Recommend NO incluir `token_cache_path` en el `__repr__`
  por privacidad (el path puede revelar el username via `~/.../iol-client/`).
  Si se quiere debugging ergonomics, agregar un método explícito
  `Client.cache_info() -> dict` opcional. Defer (no scope Phase 14).

### Folded Todos

- **`spike-codegen-libcst-v1.3.md`** (score 0.6, area: codegen) — NO se folda.
  Phase 14 no toca codegen; el spike es para v1.3 driver-migration cross-pkg
  parity. Reviewed but deferred.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & milestone v1.2

- `.planning/PROJECT.md` — v1.2 milestone goals; "IOL refresh_token disk persistence
  — secure token storage para el único paquete con OAuth refresh_token; cierra el
  carry-forward de v1.1 BUG-03 (in-instance only)."
- `.planning/REQUIREMENTS.md` §SEC-01 — full spec con anti-Pitfalls 7/8/9/10 mitigations
  enumerados explícitamente y los 4 BUG-03 lifecycle paths que el regression test
  suite debe cubrir × disk.
- `.planning/ROADMAP.md` §"Phase 14: IOL Disk Persistence (SEC-01)" — los 5 SC
  oficiales (3 CRITICAL merge gates + path/permissions/CI spec + 8 regression tests
  + platformdirs dep scope).

### Research (v1.2 PITFALLS, fuente de los 4 anti-Pitfalls)

- `.planning/research/PITFALLS.md` §Pitfall 7 — token leak via new disk-persistence
  log sites bypassing `RedactingFilter`. **Mitigation D-C1 + Plan 1 caplog DEBUG
  sentinel test source.**
- `.planning/research/PITFALLS.md` §Pitfall 8 — stale token after out-of-band
  rotation. **Mitigation cleanup-on-401 path + Plan 1 `test_disk_token_deleted_on_refresh_401`.**
- `.planning/research/PITFALLS.md` §Pitfall 9 — multi-process race two parallel
  `main_iol.py --live` runs clobber each other. **Mitigation `fcntl.flock` + Plan 1
  20-thread test.**
- `.planning/research/PITFALLS.md` §Pitfall 10 — file permissions 0600 noop on
  Windows + unsafe on shared CI runners. **Mitigation `os.environ["CI"]=="true"`
  refuses default-path + chmod 0600 on POSIX + parent 0700.**
- `.planning/research/PITFALLS.md` §"`with_options` × disk persistence" — interacción
  Phase 13 × Phase 14 (view comparte `_state.refresh_token` y `_state.token_cache_path`).
- `.planning/research/STACK.md` — `platformdirs >=4.0,<5` rationale (cross-platform
  XDG/macOS resolution); NO nuevas runtime deps fuera de iol-client.
- `.planning/research/ARCHITECTURE.md` — buscar §"IOL disk persistence" si existe;
  si no, planner consulta el shape de `_state.py` actual y mapea el field nuevo
  `token_cache_path: Path | None` (Phase 13 D-T3 precedent matriz-only).

### Prior phase (Phase 13 — `with_options` view + shared `_state`, direct dependency)

- `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/13-CONTEXT.md`
  — D-V1 (view `_is_view=True` lifecycle no-op); D-V4 (view comparte `_state`
  snapshot al momento del constructor — relevante porque `token_cache_path` se
  setea en `Client.__init__` y los views lo heredan); D-T1..T6 matriz-only
  carve-out pattern (Phase 14 sigue el mismo patrón con `client_max_retries` →
  `token_cache_path` iol-only).
- `.planning/phases/13-cross-package-ergonomics-with-options-max-retries-n/13-SUMMARY.md`
  files (5 SUMMARY.md uno por wave) — confirman el shape de `_state.py` que
  Phase 14 EXTIENDE.

### Prior phase (v1.1 BUG-03, base lifecycle que Phase 14 EXTIENDE × disco)

- `.planning/milestones/v1.1-phases/04-bug-03-iol-refresh-token/` (si existe — el planner
  confirma path) — los 4 paths del v1.1 BUG-03 in-instance lifecycle que Phase 14
  EXTIENDE: `refresh→success`, `refresh→401→password`, `preserve-on-omit`,
  `rotate-on-provide`. Phase 14 los REPITE × {sync, async, disk} = 8 regression
  tests mínimo.

### Prior phase (v1.1 LOG-02 RedactingFilter, anti-Pitfall 7 mitigation source)

- `.planning/milestones/v1.1-phases/09-log-02-redacting-filter/` (si existe — el planner
  confirma path) — el `RedactingFilter` instalado en `logging.getLogger("iol_client")`
  con NullHandler. Phase 14 `_token_cache.py` usa `logging.getLogger(__name__)`
  (= `iol_client._token_cache`) para heredar el filter automáticamente.
- `verification/test_logging_no_token_leak.py` — existing v1.1 LOG-02 test;
  Phase 14 EXTIENDE el coverage con el nuevo `test_disk_persistence_never_logs_token`
  en archivo nuevo `verification/test_iol_disk_persistence.py` para scope separation.

### Codebase maps (vigentes; actualizadas Phase 11)

- `.planning/codebase/ARCHITECTURE.md` §"Module-Level State Pattern" — `_state.py`
  per-paquete; Phase 14 agrega `token_cache_path: Path | None` al iol `_state.py`
  (mirror del Phase 13 matriz-only `client_max_retries: int` carve-out).
- `.planning/codebase/CONVENTIONS.md` — `from __future__ import annotations` mandatory,
  double quotes, line=100, no relative imports, no wildcard imports.
- `.planning/codebase/TESTING.md` — pytest-httpx pattern + autouse fixtures con
  `configure(token=...)`. Phase 14 + monkeypatch para `IOL_TOKEN_CACHE_PATH` y
  `CI` env vars + `tmp_path` para tempdir aislado.

### Forward references (Phase 15, 17 — no leer todavía)

- `.planning/ROADMAP.md` §"Phase 15: Driver Migration × 4" — `main_iol.py` migra
  para consumir `Client(token_cache_path=...)` directly cuando refactoriza. Phase 14
  NO toca el driver.
- `.planning/ROADMAP.md` §"Phase 17: Final Live Re-verification × 4 (LIVE-03)" —
  re-verifica que disk cache no introdujo regresiones observables contra IOL real.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_ClientState` mutable dataclass iol** (Phase 6 D-13 + Phase 13 fix-WR-01 que
  hoisteó `client_lock` al state).
  `packages/iol-client/src/iol_client/_state.py`. Phase 14 agrega field nuevo
  `token_cache_path: Path | None = None`. Mirror del precedent Phase 13 D-T3
  matriz-only `client_max_retries`. NO se duplica a otros paquetes (iol-only).

- **`Client.__init__` iol** (Phase 6 D-13 + Phase 13 ERG-01 con `_is_view` slot).
  `packages/iol-client/src/iol_client/client.py:127`. Phase 14 agrega kwarg
  `token_cache_path: Path | None = None` justo después de `refresh_token`. La
  resolución de precedencia (kwarg → env var → default platformdirs / None si CI)
  va dentro del `__init__` body.

- **`Client._ensure_token()` sync + `AsyncClient._aensure_token()` async** iol
  (Phase 6 + Phase 8 + Phase 13). El sync llama `_token_cache.load()` al primer
  acceso si `_state.refresh_token is None and _state.token_cache_path is not None`;
  el async llama vía `asyncio.to_thread`.

- **`Client._refresh()` sync + `AsyncClient._arefresh()` async** iol (Phase 6 D-14 +
  v1.1 BUG-03). El sync después del refresh exitoso llama
  `_token_cache.save(path, new_refresh_token, acquired_at=time.time())`; después del
  401 → password fallback llama `_token_cache.delete(path)` antes del password grant.
  Async mirror vía `asyncio.to_thread`.

- **`RedactingFilter` instalado en `logging.getLogger("iol_client")` con NullHandler**
  (v1.1 LOG-02). `packages/iol-client/src/iol_client/_logging.py`. Phase 14 NO
  modifica el filter — el módulo nuevo `_token_cache.py` usa
  `logger = logging.getLogger(__name__)` (`iol_client._token_cache`) que hereda el
  filter automáticamente. Anti-Pitfall 7 mitigation source.

- **`verification/test_logging_no_token_leak.py`** (v1.1 LOG-02). Phase 14 NO lo
  extiende — los disk-cache caplog assertions viven en archivo nuevo
  `verification/test_iol_disk_persistence.py` para scope separation (idiom Phase 13
  D-P2).

- **`verification/snapshots/iol-client-surface.txt`** (Phase 6 D-06 + Phase 8 D-28 +
  Phase 13 D-V5). Phase 14 NO agrega entries module-level (no top-level export); si
  el snapshot enumerator captura el `Client.__init__` signature, el `token_cache_path`
  kwarg aparecerá. Planner confirma el behavior del enumerator y documenta.

### Established Patterns

- **Single-package serial delivery con per-package field carve-out** — Phase 13 D-T3
  matriz-only `client_max_retries`. Phase 14 mirror con iol-only `token_cache_path`.
  No se duplica a otros paquetes.

- **Tests-first cross-cutting (Plan 1 RED en HEAD)** — Phase 8 D-21 / Phase 13 D-P1.
  Phase 14 sigue.

- **Atomic write-then-rename con tempfile + `os.replace`** — pattern POSIX estándar.
  Phase 14 lo usa en `_token_cache.save()`.

- **`fcntl.flock` LOCK_EX para mutating + LOCK_SH para reading** — pattern POSIX
  estándar. Phase 14 lo aplica con context manager wrapper para garantizar
  release-on-exception.

- **`from __future__ import annotations` mandatory** — toda nueva código. Phase 14
  sigue.

- **`logging.getLogger(__name__)` namespacing** — v1.1 LOG-02 idiom. Phase 14
  `_token_cache.py` sigue.

### Integration Points

- **`packages/iol-client/src/iol_client/_token_cache.py` — NUEVO módulo:**

  ```python
  """IOL refresh_token disk persistence helpers.

  Sync API consumed directly by Client; AsyncClient invokes via asyncio.to_thread.
  All file I/O is fcntl.flock-locked and atomic via write-then-rename. Logger
  inherits RedactingFilter from logging.getLogger('iol_client').
  """
  from __future__ import annotations

  import fcntl
  import json
  import logging
  import os
  import secrets
  import time
  from pathlib import Path
  from typing import Any

  import platformdirs

  logger = logging.getLogger(__name__)  # iol_client._token_cache

  _SCHEMA_VERSION = 1


  def _resolve_default_path() -> Path | None:
      """Return platformdirs default path, or None if CI=true (anti-Pitfall 10)."""
      if os.environ.get("CI") == "true":
          return None
      base = Path(platformdirs.user_data_dir("iol-client", "market-libs"))
      return base / "refresh_token.json"


  def load(path: Path) -> dict[str, Any] | None: ...
  def save(path: Path, refresh_token: str, *, acquired_at: float) -> None: ...
  def delete(path: Path) -> None: ...
  ```

  ~120-180 LOC. Solo iol-client. NO se exporta en `__init__.py` (módulo interno
  con underscore prefix).

- **`packages/iol-client/src/iol_client/_state.py` — agrega field:**

  ```python
  @dataclass(slots=True)
  class _ClientState:
      ...
      token_cache_path: Path | None = None
  ```

  ~1 LOC. iol-only (D-T4 negative para los otros 3 paquetes — mirror Phase 13).

- **`packages/iol-client/src/iol_client/client.py` — modifica `Client.__init__` +
  `_ensure_token` + `_refresh`:**

  - `__init__`: agrega `token_cache_path: Path | None = None` kwarg justo después
    de `refresh_token`. Resuelve precedencia y setea `self._state.token_cache_path`.
    ~10 LOC.
  - `_ensure_token`: if disk cache habilitado y refresh_token in-memory es None,
    llama `_token_cache.load(path)` y popula. ~5 LOC.
  - `_refresh`: después del éxito, llama `_token_cache.save(...)`; después del 401
    → password fallback, llama `_token_cache.delete(...)` ANTES del password grant.
    ~5 LOC.

  Total ~20 LOC sync.

- **`packages/iol-client/src/iol_client/aio.py` — mirror sync:**

  Mismas modificaciones pero los calls a `_token_cache.{load,save,delete}` se
  envuelven en `await asyncio.to_thread(...)`. ~25 LOC async.

- **`packages/iol-client/pyproject.toml` — agrega dep:**

  ```toml
  [project]
  dependencies = [
      ...
      "platformdirs>=4.0,<5",
  ]
  ```

  ~1 LOC. SOLO iol-client (root + otros 3 paquetes pyproject.toml unchanged).

- **`verification/test_iol_disk_persistence.py` — NUEVO archivo Phase 14 Plan 1:**

  Los 3 CRITICAL merge gates + 8 regression tests (4 BUG-03 paths × {sync, async}).
  ~250-350 LOC. Usa `tmp_path` para isolated temp dir, `monkeypatch.setenv` para
  `IOL_TOKEN_CACHE_PATH` y `CI`, `httpx_mock` para IOL endpoints, `caplog` para
  sentinel guard. NO toca el `verification/test_logging_no_token_leak.py` existente.

- **No nuevas runtime deps fuera de iol-client.** Phase 14 NO toca root `pyproject.toml`
  ni los otros 3 packages.

- **`pre-commit run --all-files`** debe pasar al final del Plan 3 (consolidated gate).

</code_context>

<specifics>
## Specific Ideas

- **D-F1 JSON shape exacta del disk file:**

  ```json
  {
    "version": 1,
    "refresh_token": "<opaque-IOL-refresh-token-string>",
    "acquired_at": 1718450000.0
  }
  ```

- **D-C1 corrupt-recovery log line exacto (anti-Pitfall 7 compliant):**

  ```python
  logger.warning(
      "ignoring unreadable token cache at %s (%s); falling back to password grant",
      path, type(exc).__name__,
  )
  # NUNCA incluir exc, exc.args, ni file contents en el log.
  ```

- **D-A1 sync helpers + async wrapper:**

  ```python
  # _token_cache.py (sync, used by client.py directly)
  def save(path: Path, refresh_token: str, *, acquired_at: float) -> None: ...

  # aio.py (async wrapper)
  async def _arefresh(self):
      ...
      await asyncio.to_thread(
          _token_cache.save,
          self._state.token_cache_path,
          new_refresh_token,
          acquired_at=time.time(),
      )
  ```

- **Atomic write-then-rename pattern (D-P3, planner uses verbatim):**

  ```python
  def save(path: Path, refresh_token: str, *, acquired_at: float) -> None:
      path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
      tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{secrets.token_hex(4)}"
      try:
          with open(tmp, "w", encoding="utf-8") as f:
              fcntl.flock(f.fileno(), fcntl.LOCK_EX)
              json.dump(
                  {"version": _SCHEMA_VERSION, "refresh_token": refresh_token, "acquired_at": acquired_at},
                  f,
              )
              f.flush()
              os.fsync(f.fileno())
          os.chmod(tmp, 0o600)
          os.replace(tmp, path)
      except Exception:
          tmp.unlink(missing_ok=True)
          raise
  ```

- **D-P2 CRITICAL caplog test shape (anti-Pitfall 7):**

  ```python
  # verification/test_iol_disk_persistence.py
  SENTINEL = "REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210"

  def test_disk_persistence_never_logs_token(tmp_path, caplog, httpx_mock):
      """Anti-Pitfall 7 — token leak via new disk-persistence log sites.

      Exercises write-on-rotate → read-on-init → write-fail OSError → corrupt-file
      read paths with caplog DEBUG. The sentinel MUST NEVER appear in any log
      record's message, args, or repr(extra).
      """
      caplog.set_level(logging.DEBUG, logger="iol_client")
      path = tmp_path / "refresh_token.json"

      # 1. write-on-rotate
      _token_cache.save(path, SENTINEL, acquired_at=1718450000.0)

      # 2. read-on-init
      loaded = _token_cache.load(path)
      assert loaded["refresh_token"] == SENTINEL

      # 3. write-fail OSError (parent dir made read-only)
      ro_dir = tmp_path / "ro"
      ro_dir.mkdir()
      ro_dir.chmod(0o500)
      try:
          _token_cache.save(ro_dir / "rt.json", SENTINEL, acquired_at=1.0)
      except OSError:
          pass  # expected
      finally:
          ro_dir.chmod(0o700)  # cleanup so pytest can delete tmp

      # 4. corrupt-file read
      path.write_text('{"version": 1, "refresh_token":')  # JSON inválido
      result = _token_cache.load(path)
      assert result is None

      # SENTINEL must not appear ANYWHERE
      for record in caplog.records:
          assert SENTINEL not in record.getMessage()
          assert SENTINEL not in repr(record.args or ())
          for k, v in record.__dict__.items():
              if isinstance(v, str):
                  assert SENTINEL not in v
  ```

- **D-P2 CRITICAL multi-process race test shape (anti-Pitfall 9):**

  ```python
  def test_disk_token_write_under_concurrent_processes(tmp_path):
      """Anti-Pitfall 9 — 20 concurrent threads each write via fcntl.flock.

      The final file must contain EXACTLY one valid token (no interleaving,
      no truncation, no double-write corruption).
      """
      path = tmp_path / "refresh_token.json"
      tokens = [f"token-{i:02d}-{secrets.token_hex(8)}" for i in range(20)]

      with ThreadPoolExecutor(max_workers=20) as ex:
          futures = [
              ex.submit(_token_cache.save, path, t, acquired_at=float(i))
              for i, t in enumerate(tokens)
          ]
          for f in futures:
              f.result()  # propagate exceptions

      loaded = _token_cache.load(path)
      assert loaded is not None
      assert loaded["version"] == 1
      assert loaded["refresh_token"] in tokens  # exactly one winner
      # Verify file integrity: no extra bytes, no truncation
      raw = path.read_bytes()
      assert raw == json.dumps(loaded).encode("utf-8")
  ```

- **D-P2 CRITICAL failed-refresh cleanup test shape (anti-Pitfall 8):**

  ```python
  def test_disk_token_deleted_on_refresh_401(tmp_path, monkeypatch, httpx_mock):
      """Anti-Pitfall 8 — stale token deleted before password fallback.

      Seeds disk with STALE-REFRESH-TOKEN. IOL returns 401 on refresh. Client
      MUST delete the stale token from disk, do password grant, write FRESH
      token to disk.
      """
      import iol_client

      path = tmp_path / "refresh_token.json"
      _token_cache.save(path, "STALE-REFRESH-TOKEN", acquired_at=1.0)

      # Mock IOL: refresh 401, password grant success
      httpx_mock.add_response(
          url="https://api.invertironline.com/token",
          method="POST",
          status_code=401,
          match_content=b"grant_type=refresh_token",
      )
      httpx_mock.add_response(
          url="https://api.invertironline.com/token",
          method="POST",
          json={"access_token": "fresh-access", "refresh_token": "FRESH-REFRESH-TOKEN"},
          match_content=b"grant_type=password",
      )

      client = iol_client.Client(
          username="u", password="p",
          token_cache_path=path,
      )
      client._ensure_token()  # triggers refresh → 401 → cleanup → password

      loaded = _token_cache.load(path)
      assert loaded is not None
      assert loaded["refresh_token"] == "FRESH-REFRESH-TOKEN"
      assert loaded["refresh_token"] != "STALE-REFRESH-TOKEN"
  ```

- **Commit message patterns (Plans 1-3):**

  - Plan 1: `feat(verification): cross-cutting iol disk persistence tests + platformdirs dep (SEC-01)`
  - Plan 2: `feat(iol-client): _token_cache.py + Client(token_cache_path) sync integration (SEC-01)`
  - Plan 3: `feat(iol-client): AsyncClient(token_cache_path) + Phase 14 green gate (SEC-01)`

- **LOC delta estimate:**

  ```
  packages/iol-client/src/iol_client/_token_cache.py: +150 (new module)
  packages/iol-client/src/iol_client/_state.py: +1 (token_cache_path field)
  packages/iol-client/src/iol_client/client.py: +20 (init + _ensure_token + _refresh)
  packages/iol-client/src/iol_client/aio.py: +25 (mirror via asyncio.to_thread)
  packages/iol-client/pyproject.toml: +1 (platformdirs dep)
  verification/test_iol_disk_persistence.py: +300 (3 CRITICAL gates + 8 regression tests)
  TOTAL: ~500 LOC for Phase 14
  ```

</specifics>

<deferred>
## Deferred Ideas

- **Encrypted-at-rest token storage** (e.g., `keyring`, `cryptography.Fernet`,
  OS keychain integration) — defer a v1.3+ si surge requirement. El threat model
  Phase 14 asume `0600` POSIX permissions como suficiente para single-user dev
  machines y CI runners locked.
- **Windows ACL equivalente al 0600 POSIX** — el proyecto target es Linux/macOS;
  defer a si/cuando Windows entre en scope.
- **TTL del refresh_token con rotación proactiva** — IOL no documenta TTL cliente;
  el cleanup-on-401 (anti-Pitfall 8) es la invalidación canónica. `acquired_at`
  field se persiste para audit pero no se usa como gate. v1.3 si surge.
- **Quarantine de corrupt files** (`refresh_token.corrupt-<ts>.json`) — D-C1
  rechaza explícitamente. v1.3 si surge requirement de forensics estructurado.
- **Disk persistence para otros 3 paquetes** — solo iol tiene OAuth refresh_token.
  Defer permanentemente.
- **Driver migration de `main_iol.py` para consumir `token_cache_path`** —
  Phase 15 REFAC-05 decide adoption por driver.
- **`client.with_options(token_cache_path=...)` per-call override** — Phase 13
  scope-lock `with_options` a `max_retries` only por PROJECT.md:40. Defer a v1.3+.
- **`Client.cache_info() -> dict`** inspect method para debug ergonomics —
  Claude's Discretion lo rejecta por scope; v1.3 si UX feedback.
- **TRAVIS/JENKINS/etc CI detection** — defer; el `CI==true` de facto standard
  cubre todos los runners modernos.
- **Multi-token cache** (e.g., cache de tokens para múltiples users IOL en el
  mismo machine) — fuera de scope total; v1.3+ si surge requirement.

### Reviewed Todos (not folded)

- **`spike-codegen-libcst-v1.3.md`** (score 0.6) — score borderline pero el todo
  es para v1.3 driver-migration cross-pkg parity, NO para Phase 14 iol-only disk
  persistence. NO se folda.

</deferred>

---

*Phase: 14-IOL Disk Persistence (SEC-01)*
*Context gathered: 2026-06-15*
