# Phase 26: Calendar write - Pattern Map

**Mapped:** 2026-07-31
**Files analyzed:** 5 modificados (src) + 3 modificados (tests) + 2 nuevos (tests) = 10 artefactos
**Analogs found:** 9 / 10 (el único sin análogo: el guard de path-safety D-18)

Todos los análogos viven dentro de `packages/market-data-client/` — la fase es una extensión
puramente aditiva de un solo paquete, así que cada excerpt es same-package, same-role,
same-data-flow (exact match). **Prohibido** tomar patrones de otro paquete (no-shared-internals,
CLAUDE.md); la única excepción es un patrón de **test** (`packages/iol-client/tests/test_transport.py`)
que se copia como forma de test, no como código importado.

Esta fase es la **segunda superficie de mutación** detrás del gate de Phase 25: casi todo símbolo
nuevo tiene un 1:1 shipeado. Precedente de forma y profundidad:
`.planning/phases/25-mutating-gate-symbols-write/25-PATTERNS.md`.

## File Classification

| Archivo nuevo/modificado | Rol | Data flow | Análogo más cercano | Match |
|---|---|---|---|---|
| `src/market_data_client/_core.py` (+5 builders) | pure builder | request-response | `build_create_symbol_request` (`_core.py:394-409`), `build_segments_request` (`_core.py:502-515`), `build_update_symbol_request` (`_core.py:429-447`) | exact |
| `src/market_data_client/_core.py` (+1 parser passthrough) | pure parser | transform (wire → dict) | `parse_calendar_config_response` (`_core.py:733-746`) — **NO** `parse_health_response` (`_core.py:273-278`, no tolerante) | role-match |
| `src/market_data_client/_core.py` (`__all__`) | barrel | — | `_core.py:71-98` (lista ordenada, 28 nombres) | exact |
| `src/market_data_client/models.py` (+3 request models) | model (serialize-OUT) | transform (dataclass → wire dict) | `NewSymbol` / `NewSymbols` / `SymbolPatch` (`models.py:197-252`) | exact |
| `src/market_data_client/models.py` (import de `_params`) | import | — | `_core.py:479` (`_params.drop_none(...)`) — **primer uso en `models.py`** | partial |
| `src/market_data_client/client.py` (+5 métodos +5 shims) | stateful shell (sync) | request-response | `create_symbol` / `create_symbols` / `update_symbol` (`client.py:539-574`), shims (`client.py:764-776`) | exact |
| `src/market_data_client/aio.py` (espejo) | stateful shell (async) | request-response | `aio.py:552-585`, shims (`aio.py:773-785`) | exact |
| `src/market_data_client/__init__.py` (+8 nombres) | package barrel | — | bloque de imports + `__all__` (`__init__.py:39-113`) | exact |
| `tests/test_calendar_write.py` (NUEVO) | test | request-response | `tests/test_symbols_write.py` (archivo completo, 168 líneas) | exact |
| `tests/test_calendar_write_async.py` (NUEVO) | test | request-response | `tests/test_symbols_write_async.py` (archivo completo, 154 líneas) | exact |
| `tests/test_core.py` (EXTENDER) | test | builder-spec | `test_build_create_symbol_request_posts_serialized_body` (`test_core.py:323-332`) | exact |
| `tests/test_models.py` (EXTENDER) | test | transform | `test_new_symbols_empty_raises_value_error` (`test_models.py:191-209`) | exact |
| `tests/test_public_surface_market_data.py` (EXTENDER) | test | — | `_NEW_PUBLIC_NAMES` / `_MUTATION_METHODS` (`test_public_surface_market_data.py:23-33`) | exact |
| Test no-retry dispatch-level (D-15) | test | request-response | `packages/iol-client/tests/test_transport.py:41-52` (marker) + `tests/test_transport.py:97-98` (monkeypatch sleep) | role-match |
| `tests/conftest.py` | fixture | — | **NO TOCAR** — el reset del gate ya existe (`conftest.py:44-55` sync, `71-80` async) | reuso |

---

## Pattern Assignments

### `_core.py` — builders con body ya serializado (3 nuevos)

**Aplica a:** `build_set_calendar_config_request`, `build_preview_calendar_config_request`,
`build_add_holidays_request`.

**Análogo:** `packages/market-data-client/src/market_data_client/_core.py:394-409`

```python
def build_create_symbol_request(state: _ClientState, json_body: dict[str, Any]) -> RequestSpec:
    """Pure: build spec for ``POST /symbols`` (single symbol create, MUT-MD-01).

    ``idempotent=True`` (DM-03 — retry-safe per spec; revalidated live in
    Phase 27); ``authenticated=True``. ``json_body`` is the already-serialized
    ``NewSymbol.to_dict()`` (the payload, not state).
    """
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="POST",
        path="/symbols",
        json_body=json_body,
        idempotent=True,
        endpoint_name="create_symbol",
        authenticated=True,
    )
```

Batch (mismo shape, otro path) — `_core.py:412-426` `build_create_symbols_request`
(`path="/symbols/batch"`, `endpoint_name="create_symbols"`, `idempotent=True`).

**Valores a instanciar (paths e `idempotent` LOCKED por D-01/D-04):**

| Builder | `method` | `path` | `idempotent` | `endpoint_name` |
|---|---|---|---|---|
| `build_set_calendar_config_request` | `"PUT"` | `"/calendar/config"` | `True` | `"set_calendar_config"` |
| `build_preview_calendar_config_request` | `"POST"` | `"/calendar/config/preview"` | `True` | `"preview_calendar_config"` |
| `build_add_holidays_request` | `"POST"` | `"/calendar/holidays"` | **`False`** ⚠ | `"add_holidays"` |

⚠ `build_add_holidays_request` es el **único análogo divergente**: los tres builders de Phase 25
son `idempotent=True`. `RequestSpec.idempotent` ya defaultea a `False` (`_core.py:128`) — **no
omitir el kwarg**: escribirlo explícito `idempotent=False`, es load-bearing (D-04) y el default
implícito lo haría invisible en el diff.

---

### `_core.py` — builder zero-kwarg sin body (1 nuevo)

**Aplica a:** `build_delete_calendar_config_request`.

**Análogo:** `packages/market-data-client/src/market_data_client/_core.py:502-515`

```python
def build_segments_request(state: _ClientState) -> RequestSpec:
    """Pure: build spec for ``GET /instruments/segments`` (D-01, no params).

    Same authenticated/idempotent contract as ``build_instruments_request`` but
    takes no filter kwargs — ``params`` stays ``None``.
    """
    del state  # state-independent
    return RequestSpec(
        method="GET",
        path="/instruments/segments",
        idempotent=True,
        endpoint_name="segments",
        authenticated=True,
    )
```

Análogo intra-calendar aún más cercano (mismo recurso, GET): `build_calendar_config_request`
(`_core.py:567-580`) — copiar su docstring/shape y cambiar `method="GET"` → `"DELETE"`.

**A instanciar:** `method="DELETE"`, `path="/calendar/config"`, `idempotent=True`,
`endpoint_name="delete_calendar_config"`. **`json_body` se OMITE** (queda en su default `None`).
Nunca `json_body={}` — con httpx 0.28.1 emite `b"{}"` + `Content-Type: application/json`
(RESEARCH Pitfall 1, verificado).

---

### `_core.py` — builder con path-param (1 nuevo) + guard D-18

**Aplica a:** `build_delete_holiday_request`.

**Análogo (interpolación de path):** `packages/market-data-client/src/market_data_client/_core.py:429-447`

```python
def build_update_symbol_request(
    state: _ClientState, symbol_id: str, json_body: dict[str, Any]
) -> RequestSpec:
    """Pure: build spec for ``PATCH /symbols/{symbol_id}`` (MUT-MD-01).

    ``symbol_id`` is interpolated RAW into the path for Phase 25 — percent-encoding
    for ids containing ``/`` (e.g. ``"DLR/DIC26"``) is D-08 / Pitfall 4, explicitly
    deferred to Phase 27. ``idempotent=True`` (DM-03), ``authenticated=True``;
    ``json_body`` is the already-serialized ``SymbolPatch.to_dict()``.
    """
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="PATCH",
        path=f"/symbols/{symbol_id}",
        json_body=json_body,
        idempotent=True,
        endpoint_name="update_symbol",
        authenticated=True,
    )
```

**A instanciar:** firma `(state: _ClientState, day: str) -> RequestSpec`; `method="DELETE"`,
`path=f"/calendar/holidays/{day}"`, **sin `json_body`**, `idempotent=True`,
`endpoint_name="delete_holiday"`.

> **⚠ SIN ANÁLOGO EN EL REPO — el guard de path-safety D-18.**
> Ningún builder shipeado valida su path-param: `build_update_symbol_request` interpola
> `symbol_id` RAW y lo documenta como deuda diferida (línea 434-436, arriba). Es decir, el
> precedente in-package es exactamente lo que D-18 **prohíbe** repetir. El planner debe escribir
> este guard desde cero (~3 líneas), **antes** del `return RequestSpec(...)`:
> - `ValueError` si `day` es vacío o contiene `/`, `?`, `#` o `..`.
> - El `ValueError` pelado sí tiene precedente de forma: `NewSymbols.__post_init__`
>   (`models.py:230-233`) — jerarquía `MarketData*` reservada para errores de contrato del
>   servidor (D-12).
> - Debe aparecer en el bloque `<threat_model>` del plan que posea este builder
>   (`security_block_on: "high"`, RESEARCH Open Question 1: `day="../config"` normaliza a
>   `DELETE /api/calendar/config`, verificado con httpx 0.28.1).
> - El guard es estrictamente más angosto que `urllib.parse.quote()` → **D-03 sigue valiendo**
>   byte a byte; no es validación de formato → **D-13 sigue valiendo** (`"2026-13-45"` pasa el
>   guard y va al `422`).

---

### `_core.py` — parser reusado verbatim (config trio, D-05)

**Análogo = reuso literal, cero código nuevo:** `packages/market-data-client/src/market_data_client/_core.py:733-746`

```python
def parse_calendar_config_response(resp: httpx.Response) -> CalendarConfig:
    """Pure: parse ``GET /calendar/config`` → a single ``CalendarConfig`` (D-07).
    ...
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return CalendarConfig.from_api(None)
    raw = resp.json()
    return CalendarConfig.from_api(raw)
```

`set_calendar_config`, `delete_calendar_config` y `preview_calendar_config` lo llaman **sin
modificarlo**. No agregar entradas a `__all__` por esto (ya está en `_core.py:87`).

---

### `_core.py` — parser passthrough tolerante (1 NUEVO, holiday pair)

**⚠ El análogo que CONTEXT.md nombra NO sirve.** D-06/D-07 dicen "en el estilo de
`parse_health_response`". El código shipeado (`_core.py:273-278`) es:

```python
def parse_health_response(resp: httpx.Response) -> dict[str, Any]:
    """Pure: parse a health response → JSON dict (D-03: no SafeModel here)."""
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    return data
```

**No es tolerante** (medido en RESEARCH): body `b""` → `json.JSONDecodeError` (error crudo de
stdlib, fuera de la jerarquía `MarketDataError`); body `b"null"` → `None` y `b"[]"` → `list`,
ambos mintiendo contra la anotación `dict[str, Any]` (mypy no lo atrapa porque `resp.json()` es
`Any`). **Copiar el orden body-consume-then-raise de acá, NO la ausencia de guards.**

**Análogo correcto para la tolerancia:** `parse_calendar_config_response` (`_core.py:741-746`,
arriba) + el guard de colección de `parse_symbols_response` (`_core.py:706-713`). El parser nuevo
combina ambos:

```python
def parse_calendar_write_response(resp: httpx.Response) -> dict[str, Any]:
    """Pure: parse a calendar-write 200 → dict passthrough tolerante (D-06/D-07)."""
    resp.read()                       # ← orden de parse_health_response
    raise_for_response(resp)
    if not resp.content:              # ← guard de parse_calendar_config_response
        return {}
    raw = resp.json()
    if not isinstance(raw, dict):     # ← guard de tipo (raw None / list / escalar)
        return {}
    return raw
```

**Uno solo** para `add_holidays` y `delete_holiday` (RESEARCH Open Question 2 resuelta: mismo
contrato, misma tolerancia, menos superficie).

**⛔ Nunca** reusar `parse_calendar_response` (`_core.py:716-730`) ni importar `CalendarDay`:
el par está roto contra el wire real (D-16, verificado → 4 objetos all-default). Cualquier
aparición de `CalendarDay` en el diff de Phase 26 es un defecto.

---

### `_core.__all__`

**Análogo:** `_core.py:71-98` — lista ordenada alfabéticamente (28 nombres). Insertar en orden
(ruff `RUF022`), no al final:
`build_add_holidays_request`, `build_delete_calendar_config_request`,
`build_delete_holiday_request`, `build_preview_calendar_config_request`,
`build_set_calendar_config_request`, `parse_calendar_write_response`.

---

### `models.py` — 3 request models frozen con `to_dict()`

**Análogo:** `packages/market-data-client/src/market_data_client/models.py:197-237`

```python
@dataclass(frozen=True, slots=True)
class NewSymbol:
    """Typed request body element for a symbol create (D-09 / D-10).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    ``market_id`` is defaulted, non-nullable, and ALWAYS emitted (D-10). ...
    """

    symbol: str
    market_id: str = "ROFX"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict — both keys always present (D-10)."""
        return {"symbol": self.symbol, "market_id": self.market_id}


@dataclass(frozen=True, slots=True)
class NewSymbols:
    """... Enforces the client-side 1-500 batch-size guard in :meth:`__post_init__`,
    raising a plain :class:`ValueError` (NOT a ``MarketData*`` error — that hierarchy
    is reserved for server contract errors, D-11) before any spec build or HTTP
    dispatch. The ``ValueError``-only ``__post_init__`` reads but never mutates
    fields, so it is valid on a frozen dataclass without ``object.__setattr__``.
    """

    symbols: list[NewSymbol]

    def __post_init__(self) -> None:
        """Enforce the 1-500 batch-size bound (D-11) — plain ValueError."""
        if not 1 <= len(self.symbols) <= 500:
            raise ValueError(f"NewSymbols requires 1-500 symbols, got {len(self.symbols)}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{"symbols": [each element's to_dict()]}``."""
        return {"symbols": [s.to_dict() for s in self.symbols]}
```

Tercer precedente (modelo de un solo campo): `SymbolPatch` (`models.py:240-252`).

**Mapeo directo:**
- `MarketHoursIn` ← `NewSymbol` (defaults siempre emitidos; `confirm: bool = False` es el
  análogo exacto de `market_id: str = "ROFX"` — defaulted, no nullable, siempre en el wire, D-09).
- `HolidaysIn` ← `NewSymbols` (bound 1–500 en `__post_init__`, `ValueError` pelado, wrapper
  `{"days": [...]}`). El mensaje debe conservar el substring `"1-500"`: los tests existentes
  matchean por ahí (`test_models.py:194`, `:200`).
- `HolidayIn` ← `NewSymbol` para la forma, pero es el **primero con campos nullable**.

**⚠ Delta real vs. Phase 25 (D-11 / discrepancia X4):** `NewSymbol.to_dict()` construye el dict a
mano y **NO** pasa por `drop_none` — `models.py` **hoy no importa `_params`** (verificado:
`models.py:37-41` sólo importa stdlib). Phase 26 introduce ese import por primera vez en ese
archivo. El call-site exacto a copiar es el de `_core.py:479-491`:

```python
    params = _params.drop_none(
        {
            "q": q,
            "segment": segment,
            ...
        }
    )
```

`drop_none` (`_params.py:22-28`) **preserva falsy-pero-no-`None`**:

```python
def drop_none(params: dict[str, Any]) -> dict[str, Any]:
    """Return ``params`` without keys whose value is ``None``.

    Preserves falsy-but-not-None values (``False``, ``0``, ``""``) because
    those are legitimate API inputs.
    """
    return {k: v for k, v in params.items() if v is not None}
```

→ `HolidayIn("2026-12-25").to_dict() == {"day": "2026-12-25", "closed": True, "description": ""}`
(`open_time`/`close_time` desaparecen; `closed=True` y `description=""` se emiten).
`MarketHoursIn.to_dict()` rutea por `drop_none` aunque sea no-op (consistencia, D-11).
`HolidaysIn.to_dict()` **no** lo usa (wrapper puro, igual que `NewSymbols`).

**Sin ciclo de import** (verificado en RESEARCH Pitfall 6): `_params.py` sólo importa `typing`;
la cadena queda `_core → models → _params`. Import a ubicar tras los `from dataclasses/typing`
(ruff `I001`): `from market_data_client import _params`.

**`models.__all__`** (`models.py:43-55`): insertar `"HolidayIn"`, `"HolidaysIn"`,
`"MarketHoursIn"` en orden alfabético.

---

### `client.py` — 5 métodos gated (shell sync)

**Análogo:** `packages/market-data-client/src/market_data_client/client.py:539-574`

```python
    def create_symbol(self, new_symbol: NewSymbol) -> list[Symbol]:
        """Gated ``POST {base_url}/symbols`` → tolerant ``list[Symbol]`` (MUT-MD-01).

        ``_ensure_mutation_allowed()`` is the LITERAL FIRST statement (before the
        builder, before ``self._request``, before any token fetch) so a refused
        mutation emits ZERO HTTP + ZERO Auth0 grant (D-04/D-05). A ``422`` flows
        through the existing ``_core.raise_for_response`` unchanged (D-12). ...
        """
        self._ensure_mutation_allowed()
        spec = _core.build_create_symbol_request(self._state, new_symbol.to_dict())
        resp = self._request(spec)
        return _core.parse_symbols_response(resp)
```

Método con path-param (para `delete_holiday`) — `client.py:565-574`:

```python
    def update_symbol(self, symbol_id: str, patch: SymbolPatch) -> list[Symbol]:
        self._ensure_mutation_allowed()
        spec = _core.build_update_symbol_request(self._state, symbol_id, patch.to_dict())
        resp = self._request(spec)
        return _core.parse_symbols_response(resp)
```

**Gate consumido sin cambios** — `client.py:257-283` (`_ensure_mutation_allowed`): dos patas
(`mutating_allowed` + match exacto `urlsplit(base_url).hostname == expected_host`), lectura pura
de estado, cero HTTP. Phase 26 **no lo toca**.

**Las 5 firmas (nombres LOCKED por DM/ROADMAP):**

| Método | Firma sync | Builder | Parser |
|---|---|---|---|
| `set_calendar_config` | `(self, config: MarketHoursIn) -> CalendarConfig` | `build_set_calendar_config_request(self._state, config.to_dict())` | `parse_calendar_config_response` |
| `delete_calendar_config` | `(self) -> CalendarConfig` | `build_delete_calendar_config_request(self._state)` | `parse_calendar_config_response` |
| `preview_calendar_config` | `(self, config: MarketHoursIn) -> CalendarConfig` | `build_preview_calendar_config_request(self._state, config.to_dict())` | `parse_calendar_config_response` |
| `add_holidays` | `(self, holidays: HolidaysIn) -> dict[str, Any]` | `build_add_holidays_request(self._state, holidays.to_dict())` | `parse_calendar_write_response` |
| `delete_holiday` | `(self, day: str) -> dict[str, Any]` | `build_delete_holiday_request(self._state, day)` | `parse_calendar_write_response` |

`preview_calendar_config` lleva `self._ensure_mutation_allowed()` igual (D-14, sin carve-out);
la excepción read-safe se **documenta en el docstring**, no se implementa.

**Sección/comentario:** replicar el divisor de `client.py:535-537`
(`# Public endpoint methods — symbols writes (gated, ...)`) con el equivalente calendar.

---

### `aio.py` — espejo async

**Análogo:** `packages/market-data-client/src/market_data_client/aio.py:552-585`

```python
    async def create_symbol(self, new_symbol: NewSymbol) -> list[Symbol]:
        """Gated ``POST {base_url}/symbols`` → ``list[Symbol]`` tolerante (D-15).

        Espejo async: ``_ensure_mutation_allowed()`` es la PRIMERA sentencia
        (no-awaited), antes del builder, de ``await self._request`` y de cualquier
        token fetch — un refusal emite CERO HTTP + CERO grant a Auth0 (D-04/D-05).
        """
        self._ensure_mutation_allowed()
        spec = _core.build_create_symbol_request(self._state, new_symbol.to_dict())
        resp = await self._request(spec)
        return _core.parse_symbols_response(resp)
```

**La divergencia sync/async es exactamente ésta y sólo ésta** (comparar con `client.py:539-552`):
1. `async def` en la firma.
2. `resp = await self._request(spec)` (una sola línea awaited).
3. `self._ensure_mutation_allowed()` sigue siendo **no-awaited** (es sync, lectura pura de estado)
   y sigue siendo la primera sentencia literal.
4. Docstrings del shell async están en castellano; los del shell sync en inglés — mantener esa
   convención por archivo.

`aio._ensure_mutation_allowed` está en `aio.py:215-240` (idéntico al sync).

---

### Shims module-level (5 sync + 5 async)

**Análogos:** `client.py:764-776` y `aio.py:773-785`

```python
def create_symbol(new_symbol: NewSymbol) -> list[Symbol]:
    """Top-level shim: delega al default Client (gated)."""
    return _get_default().create_symbol(new_symbol)
```

```python
async def create_symbol(new_symbol: NewSymbol) -> list[Symbol]:
    """Shim async top-level: delega al default AsyncClient (gated)."""
    return await _get_default().create_symbol(new_symbol)
```

Un shim por método × 2 shells = 10. Los shims sync entran al namespace plano vía `__init__.py`;
los async **NO** se re-exportan (viven bajo `aio`) — enforced por
`test_public_surface_market_data.py:76-85`.

---

### `__init__.py` — 8 nombres nuevos

**Análogo:** `packages/market-data-client/src/market_data_client/__init__.py:40-57` (import block
desde `client`, alfabético con `# noqa: E402`), `:65-76` (import block desde `models`), y `:81-113`
(`__all__` — PascalCase antes que snake_case por orden ASCII).

```python
from market_data_client.client import (  # noqa: E402
    Client,
    _get_default,
    configure,
    create_symbol,
    create_symbols,
    ...
)
from market_data_client.models import (  # noqa: E402
    CalendarConfig,
    ...
    NewSymbol,
    NewSymbols,
    ...
)
```

**A agregar (8):** modelos `HolidayIn`, `HolidaysIn`, `MarketHoursIn`; shims sync
`add_holidays`, `delete_calendar_config`, `delete_holiday`, `preview_calendar_config`,
`set_calendar_config` — en los dos import blocks correspondientes **y** en `__all__`, todos en
orden alfabético dentro de su grupo (ruff `RUF022`, RESEARCH Pitfall 8).

**No tocar `__version__`** (`__init__.py:118`, hoy `"0.3.1"`) — el bump es Phase 28.

---

### `tests/test_calendar_write.py` (NUEVO) — espejo de `test_symbols_write.py`

**Análogo:** `packages/market-data-client/tests/test_symbols_write.py` (archivo entero).

Header + helper del gate (`test_symbols_write.py:18-37`) — copiar tal cual, cambiando sólo los
imports de modelos:

```python
from __future__ import annotations

import json as _json

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import MarketDataAPIError, MarketDataMutationNotAllowedError
from market_data_client.models import NewSymbol, NewSymbols, SymbolPatch

_BASE = "https://market-data-develop.test/api"
_TOKEN_URL = "https://auth.test/oauth/token"
# El host que el conftest siembra en base_url (NO el default develop bbsa).
_CONFTEST_HOST = "market-data-develop.test"


def _open_gate() -> None:
    """Abre el gate del singleton default para el host del conftest."""
    market_data_client.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)
```

**Happy path con body** (`test_symbols_write.py:45-61`):

```python
def test_create_symbol_sends_bearer_and_body(httpx_mock: HTTPXMock) -> None:
    """``create_symbol`` POSTea ``/symbols`` con el body snake_case y el Bearer."""
    _open_gate()
    httpx_mock.add_response(
        method="POST",
        status_code=201,
        json=[{"symbol": "DLR/DIC26", "marketId": "ROFX"}],
    )

    result = market_data_client.client._get_default().create_symbol(NewSymbol("DLR/DIC26"))

    assert isinstance(result, list)
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/symbols"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {"symbol": "DLR/DIC26", "market_id": "ROFX"}
```

El assert de body para `set_calendar_config` **es** el criterio 2 del ROADMAP: debe incluir
`"confirm": False` explícito en el dict esperado.

**Path con `/api` prefijo:** notar `req.url.path == "/api/symbols"` — el `base_url` del conftest
ya trae `/api`. Los paths esperados son `/api/calendar/config`,
`/api/calendar/config/preview`, `/api/calendar/holidays`, `/api/calendar/holidays/2026-12-25`.

**`422` → typed** (`test_symbols_write.py:98-104`):

```python
def test_create_symbol_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` fluye por el ``raise_for_response`` existente → ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().create_symbol(NewSymbol("BAD"))
```

**Refusal adversarial** (`test_symbols_write.py:112-121`) — replicar ×5 métodos, incluido
`preview_calendar_config` (la prueba de que D-14 no tiene carve-out):

```python
def test_create_symbol_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """Gate OFF por default + token FORZADO-vencido → refused, 0 HTTP y 0 grant Auth0."""
    # Forzar el token vencido: si el gate NO cortara primero, ``_ensure_token``
    # dispararía un POST a Auth0 — la ausencia de ese POST prueba el short-circuit.
    market_data_client.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        market_data_client.client._get_default().create_symbol(NewSymbol("DLR/DIC26"))

    assert httpx_mock.get_requests() == []
```

**Host mismatch** (`test_symbols_write.py:144-156`) y **shim module-level**
(`test_symbols_write.py:159-168`) — copiar shape.

**Test DELETE sin body (sin análogo directo — assert nuevo, ya verificado en RESEARCH):**
`assert req.content == b""` + `assert "content-type" not in req.headers` (D-02).

---

### Test no-retry a nivel dispatch (D-15) — dos análogos parciales

**No existe** un test dispatch-level de `idempotent=False` en este paquete (los asserts de
`idempotent` en `tests/test_core.py` son builder-level). Se compone de dos piezas:

**(a) Marker + shape** — `packages/iol-client/tests/test_transport.py:41-52` (otro paquete; se
copia la **forma del test**, no código importado):

```python
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_non_idempotent_request_passes_through(httpx_mock: HTTPXMock) -> None:
    """D-01: idempotent=False MUST bypass the retry loop entirely (1 wire request)."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(client, idempotent=False)
    resp = client.send(req)

    assert resp.status_code == 503
    assert len(httpx_mock.get_requests()) == 1
```

El marker es obligatorio: sin él, pytest-httpx falla en teardown por respuestas no consumidas
(RESEARCH Pitfall 4).

**(b) Monkeypatch de `time.sleep`** — `packages/market-data-client/tests/test_transport.py:97-98`
(in-package):

```python
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))
```

Sin esto el control positivo `idempotent=True` duerme ~4,4 s reales (Pitfall 5). Bonus: `sleeps`
se vuelve un assert extra — `assert sleeps == []` en el caso no idempotente.

**Comportamiento gateado** (código shipeado, no tocar) — `_transport.py:157-160`:

```python
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        # D-01 mutation gate: non-idempotent → pass-through with no retry loop.
        if not request.extensions.get("idempotent", False):
            return super().handle_request(request)
```

---

### `tests/test_calendar_write_async.py` (NUEVO)

**Análogo:** `packages/market-data-client/tests/test_symbols_write_async.py:1-50`. Deltas exactos
vs. el sync: import `from market_data_client import ..., aio`; `_open_gate()` usa
`aio.configure(...)`; los tests son `async def` planos (`asyncio_mode="auto"`, sin decorador);
el target es `await aio._get_default().<método>(...)`.

---

### `tests/test_core.py` (EXTENDER) — specs de builder

**Análogo:** `packages/market-data-client/tests/test_core.py:323-332`

```python
def test_build_create_symbol_request_posts_serialized_body() -> None:
    state = _ClientState()
    body = {"symbol": "DLR/DIC26", "market_id": "ROFX"}
    spec = _core.build_create_symbol_request(state, body)
    assert spec.method == "POST"
    assert spec.path == "/symbols"
    assert spec.json_body == body
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "create_symbol"
```

Asserts net-new sin precedente en el paquete: `spec.idempotent is False` (para
`build_add_holidays_request` — la única aserción `False` del paquete) y `spec.json_body is None`
(para los dos DELETE). Sumar también la tolerancia del parser passthrough nuevo
(body vacío / `null` / no-dict ⇒ `{}`) y el guard D-18 (`pytest.raises(ValueError)` para
`day` vacío / `"../config"` / `"a/b"` / `"x?y=1"`).

---

### `tests/test_models.py` (EXTENDER)

**Análogo:** `packages/market-data-client/tests/test_models.py:191-209`

```python
def test_new_symbols_empty_raises_value_error() -> None:
    """Lower-bound guard: an empty batch raises a plain ValueError (NOT a
    MarketData* error) before any dispatch (D-11)."""
    with pytest.raises(ValueError, match="1-500"):
        NewSymbols([])


def test_new_symbols_over_500_raises_value_error() -> None:
    """Upper-bound guard: 501 symbols raises a plain ValueError before dispatch."""
    with pytest.raises(ValueError, match="1-500"):
        NewSymbols([NewSymbol(f"S{i}") for i in range(501)])


def test_new_symbols_boundary_1_and_500_construct() -> None:
    """Exactly 1 and exactly 500 symbols construct successfully."""
    one = NewSymbols([NewSymbol("ONLY")])
    assert len(one.symbols) == 1
    full = NewSymbols([NewSymbol(f"S{i}") for i in range(500)])
    assert len(full.symbols) == 500
```

Copiar el trío (vacío / 501 / boundary 1 y 500) para `HolidaysIn`, más los `to_dict()` de los tres
modelos (defaults verbatim de la OpenAPI; drop de `open_time`/`close_time` `None`; preservación
de `closed=True` y `description=""`). Análogo del assert `to_dict()`: `test_models.py:154-188`.

---

### `tests/test_public_surface_market_data.py` (EXTENDER)

**Análogo:** `packages/market-data-client/tests/test_public_surface_market_data.py:23-33`

```python
_NEW_PUBLIC_NAMES = (
    "MarketDataMutationNotAllowedError",
    "NewSymbol",
    "NewSymbols",
    "SymbolPatch",
    "create_symbol",
    "create_symbols",
    "update_symbol",
)

_MUTATION_METHODS = ("create_symbol", "create_symbols", "update_symbol")
```

Sólo hay que extender las dos tuplas: `_NEW_PUBLIC_NAMES` +8 (`"HolidayIn"`, `"HolidaysIn"`,
`"MarketHoursIn"`, `"add_holidays"`, `"delete_calendar_config"`, `"delete_holiday"`,
`"preview_calendar_config"`, `"set_calendar_config"`); `_MUTATION_METHODS` +5. Las cuatro pruebas
existentes (importabilidad, `__all__`, paridad de métodos de clase, ubicación de shims) cubren
automáticamente las entradas nuevas — **no escribir pruebas nuevas acá**.

---

## Shared Patterns

### Gate de mutación (aplicar a los 5 métodos × 2 shells)
**Fuente:** `client.py:257-283` / `aio.py:215-240` — **consumir sin modificar**.

```python
    def _ensure_mutation_allowed(self) -> None:
        if not self._state.mutating_allowed:
            raise MarketDataMutationNotAllowedError(
                "Mutación rechazada: seteá mutating_allowed=True (constructor o configure())."
            )
        expected = self._state.expected_host
        actual = urlsplit(self._state.base_url).hostname
        if expected is not None and actual != expected:
            raise MarketDataMutationNotAllowedError(
                f"Mutación rechazada: host de base_url {actual!r} != expected_host {expected!r}."
            )
```

Regla de invocación (D-14): **literal primera sentencia**, no-awaited también en `aio.py`.

### Manejo de errores (aplicar a todos los parsers nuevos)
**Fuente:** `_core.py:138-150` — **sin cambios**; el `422` ya cae en el `resp.is_error`.

```python
def raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise MarketDataAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise MarketDataRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise MarketDataAPIError(resp.status_code, resp.text)
```

Orden obligatorio en cada parser (D-07): `resp.read()` → `raise_for_response(resp)` → decode.

### Pureza de `_core` (aplicar a los 5 builders)
`del state  # state-independent (payload comes via json_body)` como primera línea del cuerpo,
tras el docstring — precedente en los 5 builders shipeados citados arriba. Cero I/O, cero
chequeo de política en `_core`.

### Reset del gate entre tests
**Fuente:** `tests/conftest.py:44-55` (sync) y `:71-80` (async), fixtures autouse:

```python
    market_data_client.configure(
        base_url="https://market-data-develop.test/api",
        ...
        mutating_allowed=False,
        expected_host="market-data-develop.bbsa.com.ar",
    )
```

**No agregar fixtures nuevas** — los tests nuevos usan el helper local `_open_gate()`
(`test_symbols_write.py:35-37`). `conftest.py` no se toca.

---

## No Analog Found

| Artefacto | Rol | Data flow | Razón |
|---|---|---|---|
| Guard de path-safety en `build_delete_holiday_request` (D-18) | validación en builder | request-response | Ningún builder del repo valida su path-param; `build_update_symbol_request` interpola RAW y lo documenta como deuda (`_core.py:434-436`). El único precedente reusable es la **forma** del `ValueError` pelado (`models.py:230-233`). Código nuevo, con `<threat_model>` obligatorio |
| Assert `spec.idempotent is False` (builder-level) | test | — | Los 3 builders mutadores de Phase 25 son `idempotent=True`; no hay assert `False` en el paquete |
| Test dispatch-level no-retry (D-15) | test | request-response | El único del monorepo está en **otro** paquete (`packages/iol-client/tests/test_transport.py:41-52`) y opera sobre `RetryTransport` directo, no end-to-end sobre un método público. Se compone con el monkeypatch de sleep de `tests/test_transport.py:97-98` |

---

## Discrepancias CONTEXT.md ↔ código shipeado (el planner NO debe planificar contra estos)

| # | Claim de CONTEXT.md | Realidad verificada | Qué hacer |
|---|---|---|---|
| X1 | "Package to extend (market-data-client **v0.2.0**)" | `__version__ = "0.3.1"` (`__init__.py:118`) | No bumpear en Phase 26. El target de Phase 28 ya no es `v0.3.0` |
| X2 | D-16: arreglar `get_calendar` "junto al gap WR-01 ya arrastrado" | WR-01 **ya cerrado** en v0.3.1 (`_core.py:619-653` unwrappea `items`) | Phase 27 sólo carga el bug de `get_calendar` |
| X3 | D-06/D-07: passthrough "en el estilo de `parse_health_response`" | `parse_health_response` (`_core.py:273-278`) **no es tolerante**: raise en body vacío, anotación mentirosa en `null`/`[]` | **Parser nuevo**, no reuso — ver sección arriba |
| X4 | "`_params.drop_none` — ya importado en el paquete" | Cierto en `_core.py`, pero `models.py` **no importa `_params`** (`models.py:37-41`) | 1 import nuevo en `models.py`; sin ciclo (verificado) |
| X5 | ROADMAP: "Phase 26 paraleliza con 25" | 25 es prerequisito estricto y ya está completa | Sin impacto |
| X6 | Los 4 gates incluyen mypy sobre este paquete vía `uv run mypy` | `[tool.mypy] files` **excluye** `packages/market-data-client/src`; la cobertura viene del hook pre-commit | Gate mypy explícito: `uv run mypy packages/market-data-client/src` |
| X7 | El loop mypy por-paquete de CI cubre los tests | El loop (`ci.yml:84`) itera sólo los 5 paquetes viejos | No arreglar errores mypy pre-existentes en tests; tampoco agregar nuevos |
| X8 | `import-linter` protege el boundary `_core` | `[tool.importlinter] root_packages` no lista este paquete | El boundary IO-free es **convención, no gate** — mantenerlo por disciplina |
| X9 | (no mencionado) | `AsyncClient.__init__` acepta `token`/`token_expires_at`/`http_client`; `Client.__init__` no | Asimetría pre-existente — **no tocar los constructores** |
| X10 | D-01: "los builders reciben `json_body` ya serializado" | Cierto para los 3 de Phase 25, **pero** el builder análogo de Phase 20 `build_latest_batch_request` llama `latest_request.to_dict()` adentro | Seguir el precedente **Phase 25** (serializar en el shell), no el de Phase 20 |

---

## Metadata

**Analog search scope:** `packages/market-data-client/src/market_data_client/`,
`packages/market-data-client/tests/`, `packages/iol-client/tests/test_transport.py` (sólo forma
de test), `.planning/phases/25-mutating-gate-symbols-write/25-PATTERNS.md`
**Files scanned:** 14 (6 src + 7 tests + 1 pattern map previo)
**Pattern extraction date:** 2026-07-31
