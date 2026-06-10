# Phase 6: Compat Safety Net + Client Class Skeleton - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 6-Compat Safety Net + Client Class Skeleton
**Areas discussed:** Shim depth, Plan split, Public-surface snapshot mechanism, Client.__init__ signature, load_dotenv timing, pkg.login() back-compat, Higyrus hooks + matriz X-Auth-Token, Pickle contract

---

## Shim depth

### Q1: Profundidad de shim de compat en client.py / aio.py por paquete

| Option | Description | Selected |
|--------|-------------|----------|
| Solo __getattr__ + migrar conftest | PEP 562 puro read-only: pkg.client._token forwarda a _default()._state.token. Las autouse fixtures cambian a pkg.configure(token='SYNC-sentinel', token_expires_at=...). 1 sola pieza de magic-method; conftest migration es bounded. | ✓ |
| ModuleType subclass __getattr__+__setattr__ | Subclase de types.ModuleType. Soporta lectura Y escritura: monkeypatch.setattr(pkg.client, "_token", ...) sobrevive verbatim. Más sutil; ruff/mypy strict pueden necesitar # type: ignore. | |
| Híbrido: __getattr__ + descriptor proxy | Variables module-level como _token = LegacyAttr("token") que internamente leen/escriben default client. Costo: mantener descriptor por cada attr legacy. | |

**User's choice:** Solo __getattr__ + migrar conftest (Recomendado).

### Q2: ¿Qué atributos legacy forwarda el __getattr__?

| Option | Description | Selected |
|--------|-------------|----------|
| Solo token-related | _token, _token_ts (iol), _token_expires_at, _token_lock (aio). Resto raisea AttributeError. | ✓ |
| Todos los globals actuales | Forwardar _token, _token_ts, _token_expires_at, _user, _password, _base_url, _client, _token_lock. Maximiza back-compat. | |
| Minimal: solo _token | Forces clean-up agresivo; riesgo de romper algo no testeado. | |

**User's choice:** Solo token-related (Recomendado).
**Notes:** Ver D-02 — `_client` SÍ se forwarda como excepción adicional, para preservar el patrón de `main_higyrus.py` que muta `pkg.client._client.event_hooks`. Decisión refinada durante área 7.

### Q3: ¿DeprecationWarning al leer atributos legacy?

| Option | Description | Selected |
|--------|-------------|----------|
| Silent forwarding | Sin warnings. El shim es invisible. v1.1 target es zero-noise non-breaking. | ✓ |
| DeprecationWarning con stacklevel=2 | warnings.warn(...) en cada read. Da señal a downstream pero contamina tests. | |
| Opt-in via env var MARKET_LIBS_DEPRECATIONS=1 | Silent by default; warning solo con env var set. | |

**User's choice:** Silent forwarding (Recomendado).

---

## Plan split

### Q1: ¿Cómo dividimos Phase 6 en planes?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 plan REFAC-01 + 4 planes REFAC-02 | Plan 1: golden snapshot + fixture guard × 4 pkgs (tests-only). Plans 2-5: ambito, iol, higyrus, matriz — cada uno introduce Client/AsyncClient + _state.py + shim + migra conftest. 5 planes, 5 commits atómicos. | ✓ |
| 4 planes (1 por paquete) full-stack | Cada paquete tiene su plan con REFAC-01 piece + REFAC-02 piece. Más acoplado; menos paralelismo. | |
| 1 plan REFAC-01 + 1 plan REFAC-02 monolítico | Mínimo plan count; commit gigante. Imposible bisectar. | |
| 1 plan REFAC-01 + 4 planes REFAC-02 + 1 plan migration | Variante: separar conftest migration al final. Requiere shim que soporte ambos simultaneously. | |

**User's choice:** 1 plan REFAC-01 + 4 planes REFAC-02 (Recomendado).

### Q2: Snapshot ownership cuando REFAC-02 AGREGA Client/AsyncClient

| Option | Description | Selected |
|--------|-------------|----------|
| Snapshot baseline frozen + diff allowlist | REFAC-01 freeza estado PRE-refactor. Cada REFAC-02 actualiza snapshot del paquete tocado AÑADIENDO entradas pero NUNCA removiendo. | ✓ |
| Snapshot regenerado por paquete refactorizado | Cada REFAC-02 regenera snapshot; commit muestra diff completo (added/removed/changed). Requiere review humano disciplinado. | |
| Solo API top-level (sin _token, _client) | Solo snapshotea __all__ + signatures. Cubre menos pero más simple. | |

**User's choice:** Snapshot baseline frozen + diff allowlist (Recomendado).

### Q3: Test cadence por REFAC-02 plan

| Option | Description | Selected |
|--------|-------------|----------|
| Tests del paquete + golden snapshots de los 4 | uv run pytest packages/<pkg>/ + uv run pytest verification/test_public_surface.py. Cubre paquete tocado + safety net global. | ✓ |
| Tests de los 4 paquetes en cada plan | uv run pytest completo (277 tests baseline). Más lento, zero-risk. | |
| Solo paquete tocado; confiar en CI matrix | Tests rápidos pre-commit; full suite solo en CI. Ventana de breakage. | |

**User's choice:** Tests del paquete + golden snapshots de los 4 (Recomendado).

### Q4: ¿Conftest migration en mismo commit que Client/shim o posterior?

| Option | Description | Selected |
|--------|-------------|----------|
| Mismo commit atómico | 1 commit = _state.py + Client/AsyncClient + shim + migración conftest + remoción globals legacy. Mínimo rollback footprint. | ✓ |
| Pre-commit: migrar conftest primero | Primer commit migra conftest a configure(token=...) usando current globals. Segundo commit agrega Client/shim. Requiere configure() ya extendido. | |
| Post-commit: Client+shim primero (dual-state), conftest después | Primer commit: Client + shim forwarding lecturas, globals como source of truth. Segundo: flip + migrate. Escape-hatch parcial. | |

**User's choice:** Mismo commit atómico (Recomendado).

---

## Public-surface snapshot mechanism

### Q1: Formato/storage del golden snapshot

| Option | Description | Selected |
|--------|-------------|----------|
| Text file per-pkg committeado | verification/snapshots/<pkg>-surface.txt con una línea por símbolo público sorted. Git diff humano. | ✓ |
| JSON file per-pkg committeado | JSON estructurado (parseable, machine-comparable, harder-to-read diff). | |
| Hash digest committeado | SHA256 por paquete. Mínimo footprint pero el diff no dice qué cambió. | |
| Runtime introspection sin file | El test calcula surface al vuelo vs lista hardcoded. Zero file maintenance pero test grueso. | |

**User's choice:** Text file per-pkg committeado (Recomendado).

### Q2: Scope del snapshot

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level + submodules públicos | __all__ + signature de cada función/clase exportada + atributos de submodules expuestos (pkg.client, pkg.aio, pkg.models, pkg.exceptions). NO metes _token, _client. | ✓ |
| Surface completa incluyendo privados accesibles via shim | Registra _token, _token_ts, _token_expires_at, _token_lock. Snapshots más largos. | |
| Solo __all__ + signatures | Lo más estricto; deja agujeros (pkg.aio.aclose si no está en __all__). | |

**User's choice:** Top-level + submodules públicos (Recomendado).

### Q3: ¿Dónde vive el test snapshot?

| Option | Description | Selected |
|--------|-------------|----------|
| verification/test_public_surface.py | Single file en harness, sweep × 4 paquetes en una corrida. | ✓ |
| packages/<pkg>/tests/test_public_surface.py (1 per pkg) | Cada paquete owns su test. Replica boilerplate 4×. | |

**User's choice:** verification/test_public_surface.py (Recomendado).

### Q4: ¿Cómo se regeneran snapshots intencionalmente?

| Option | Description | Selected |
|--------|-------------|----------|
| Script verification/regen_snapshots.py + commit del diff | uv run python verification/regen_snapshots.py actualiza los 4 archivos. Operador commitea el diff. Forensic-localizable. | ✓ |
| Pytest fixture --update-snapshots como syrupy | uv run pytest --update-snapshots. Requiere implementar fixture sin syrupy. | |
| Hardcoded en el test, sin regen tooling | Operator edita archivo a mano. Cero tooling pero costo cognitivo. | |

**User's choice:** Script verification/regen_snapshots.py + commit del diff (Recomendado).

### Q5: Scope del fixture-reaches-production guard

| Option | Description | Selected |
|--------|-------------|----------|
| 1 test por paquete sobre header de auth nativo | iol: Authorization=Bearer SYNC-sentinel. higyrus: Authorization=Bearer + body password. matriz: X-Auth-Token. ambito: NO-AUTH → verifica base_url customizado en URL. 4 sync + 4 async = 8 tests. | ✓ |
| + 1 cross-leak guard SYNC vs ASYNC sentinels | Adicional 4 tests con sentinels distintos sync vs async. Detecta cross-coupling (Pitfall #3). 12 tests total. | |
| 1 test omnicomprensivo por paquete parametrizado | Sync, async, auth y cross-leak en un solo test largo. Denso. | |

**User's choice:** 1 test por paquete sobre header de auth nativo (Recomendado).
**Notes:** Cross-leak SYNC vs ASYNC sentinel guard queda diferido a Phase 7 REFAC-03 (donde el roadmap explícitamente lo pide como success-criterion #2).

---

## Client.__init__ signature

### Q1: ¿Qué kwargs expone Client.__init__?

| Option | Description | Selected |
|--------|-------------|----------|
| Solo los de configure() actuales | Phase 6 expone kwargs equivalentes al configure() vigente + extensión token/token_expires_at. _ClientState carries refresh_token/account_id/http_client internamente sin exponerlos. | ✓ |
| Mismos + http_client= para test injection | Adicional http_client kwarg. Pull-forward de P2 backlog útil para Phase 8 retry. | |
| Forward-compatible: + http_client + refresh_token + account_id | Phase 6 ya expone refresh_token (iol) y account_id (higyrus) aunque la lógica de uso esté en Phase 9. | |

**User's choice:** Solo los de configure() actuales (Recomendado).

### Q2: ¿Qué hace pkg.configure() post-refactor?

| Option | Description | Selected |
|--------|-------------|----------|
| Replace _default_client con nueva instancia | configure(**kwargs) descarta default actual y crea Client(**kwargs). Equivalente a v1.0 (reset _token, _client). | ✓ |
| Mutate _default_client._state in-place | configure() edita campos de _default._state. Preserva identidad. Requiere thread-safety. | |
| Hybrid: mutate si existe, build si no | Primera llamada construye; posteriores mutan. | |

**User's choice:** Replace _default_client con nueva instancia (Recomendado).

### Q3: ¿Cuándo se instancia _default_client la primera vez?

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy en primer acceso | _default_client = None al import; cualquier llamada top-level dispara _get_default() que construye Client() leyendo env vars. | ✓ |
| Eager en import | client.py al import construye _default = Client(). Side-effects de import. | |
| Eager sólo cuando configure() corre | _default permanece None hasta primer configure(). Rompe back-compat. | |

**User's choice:** Lazy en primer acceso (Recomendado).

### Q4: AsyncClient.aclose() y cleanup del default async client

| Option | Description | Selected |
|--------|-------------|----------|
| Caller-responsible: docs + context manager | AsyncClient implementa __aenter__/__aexit__ y aclose(). Sin atexit (Pitfall #12). Documentamos convención. | ✓ |
| Warning en __del__ si no se cerró | __del__ emite ResourceWarning. Ruidoso; event loop puede estar cerrado. | |
| Best-effort weakref.finalize | Registra finalizer intentando cerrar. Complejidad sutil. | |

**User's choice:** Caller-responsible: docs + context manager (Recomendado).

### Q5: ¿Cuándo Client raisea si construye sin credenciales?

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy: AuthError en primer call que necesite token | Preserva semántica v1.0. configure() sin args legit; error llega en _ensure_token(). | ✓ |
| Eager: ValueError en __init__ | Construir Client() sin credentials raisea inmediatamente. Rompe configure()-despues-de-import. | |
| Lazy con warning | Lazy + UserWarning si __init__ sin credentials. Ruido sin señal clara. | |

**User's choice:** Lazy: raisea AuthError en primer call que necesite token (Recomendado).

### Q6: Client.__repr__() y credenciales

| Option | Description | Selected |
|--------|-------------|----------|
| Redacta credentials y token | Custom __repr__: base_url + username pero password='***' y token='***'. Consistente con redaction policy. | ✓ |
| @dataclass default repr (expone todo) | Menos código; password y token en plano. Peligroso. | |
| __repr__ minimal (solo class + base_url) | Sin riesgo pero pierde info útil. | |

**User's choice:** Redacta credentials y token (Recomendado).

---

## load_dotenv timing

### Q1: ¿Dónde se llama load_dotenv() post-refactor?

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level al import | Mantenemos behavior v1.0: client.py llama load_dotenv() al import. _ClientState lee env vars como defaults. | ✓ |
| Client.__init__ con load_dotenv lazy | Mover al __init__(). Cambia el behavior observado por callers entre import y primer call. | |
| Ambos: module-level + per-Client opt-out | Module-level + Client(use_dotenv=False). Amplía superficie sin necesidad. | |

**User's choice:** Module-level al import (Recomendado).

---

## pkg.login() back-compat

### Q1: ¿Qué pasa con pkg.login() top-level?

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level shim → default Client.login() | pkg.login() = def login(): return _get_default().login(). Client tiene método .login() ejecutando auth flow contra _state. Back-compat 100%. | ✓ |
| Solo método Client.login() | Remover pkg.login(). Rompe back-compat. | |
| Top-level shim emite DeprecationWarning | Inconsistente con silent forwarding del shim de atributos. | |

**User's choice:** Top-level shim → default Client.login() (Recomendado).

---

## Higyrus hooks + matriz X-Auth-Token

### Q1: main_higyrus.py muta pkg.client._client.event_hooks['request']. ¿Cómo se preserva?

| Option | Description | Selected |
|--------|-------------|----------|
| Shim forwarda _client → _state.http_client | __getattr__ resuelve _client a la httpx.Client real. Caller hace _client.event_hooks['request']=[...] mutando dict in-place. Driver NO se toca en Phase 6. CR-07 queda Phase 11. | ✓ |
| Phase 6 refactora main_higyrus.py | Adelantar CR-07: cambiar driver a Client.http_client property + per-request hook injection. Scope creep. | |
| Shim levanta NotImplementedError en _client | Forzar migración. Rompe el driver. | |

**User's choice:** Shim forwarda _client → _state.http_client (Recomendado).

### Q2: matriz Client.login() lee X-Auth-Token del response HEADER

| Option | Description | Selected |
|--------|-------------|----------|
| Client.login() parsea response.headers['X-Auth-Token'] y store en _state.token | Comportamiento idéntico a v1.0. Zero diferencia de wire. | ✓ |
| Header parsing en _core.py de matriz (forward-looking Phase 7) | Pull-forward de Phase 7 _core.py extraction. Scope creep. | |

**User's choice:** Client.login() parsea response.headers['X-Auth-Token'] y store en _state.token (Recomendado).

---

## Pickle contract

### Q1: Pickle/deepcopy contract de Client (Pitfall #11)

| Option | Description | Selected |
|--------|-------------|----------|
| Raise TypeError en __reduce__ | Client.__reduce__ levanta TypeError documentado. Aplica a AsyncClient. Falla loud antes de errores silenciosos en multiprocessing.spawn. | ✓ |
| Soporte via __getstate__/__setstate__ que dropea http_client | Pickle sí pero strippea http_client. Restored Client construye nuevo http_client. Esconde costo. | |
| Sin definición explícita (implementation-defined) | Default de @dataclass(slots=True). httpx.Client no picklable → TypeError opaco. | |

**User's choice:** Raise TypeError en __reduce__ (Recomendado).

---

## Claude's Discretion

Áreas donde el user deferred a planner/researcher (basado en research):

- Estructura interna exacta de `_state.py` (dataclass shape, slots, default factories).
- Implementación del `_get_default()` (módulo-level function vs cached attribute).
- Convención exacta de sentinels en conftest (mantener distinguibles sync vs async).
- Lugar exacto y format de `regen_snapshots.py` output.
- Si `Client` y `AsyncClient` heredan de un `BaseClient` por paquete o son independientes.

## Deferred Ideas

- Cross-leak SYNC-sentinel vs ASYNC-sentinel guard test → Phase 7 REFAC-03 success-criterion #2.
- `http_client=` kwarg en `Client.__init__` → Phase 8.
- `Client.from_env()` classmethod → backlog.
- `client.with_options(max_retries=N)` per-call override → Phase 8.
- `refresh_token` y `account_id` kwargs en `Client.__init__` → Phase 9 (BUG-03, BUG-04).
- CR-07 lock en `_capture_*_query_string` → Phase 11.
- CR-08 line length en `main_higyrus.py:767` → Phase 11.
- Disk persistence del refresh_token (IOL) → v1.2.
- `Client.__init__` con `use_dotenv=False` opt-out → diferido sin use case.
