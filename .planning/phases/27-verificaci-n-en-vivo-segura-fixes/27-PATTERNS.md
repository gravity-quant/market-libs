# Phase 27: Verificación en vivo segura + fixes - Pattern Map

**Mapped:** 2026-08-01
**Files analyzed:** 11 (5 modificados en el harness/driver, 4 en el paquete, 2+ tests nuevos)
**Analogs found:** 10 / 11 (1 sin analog: el gate driver-side destructivo)

> **Regla transversal de este repo (CLAUDE.md):** todo fix de lógica se espeja en `client.py`
> **y** `aio.py`. La duplicación es por diseño (codegen shelved). Cada asignación de patrón
> de abajo lista **las dos** ubicaciones con su offset real.

## File Classification

| Archivo nuevo/modificado | Role | Data flow | Analog más cercano | Match |
|---|---|---|---|---|
| `verification/findings.py` (preservar bullets extra) | utility (harness compartido) | file-I/O / transform | sí mismo: `_parse_findings` (`:373-416`) ↔ `_serialize_findings` (`:487-505`) | exact (self-symmetric) |
| `verification/test_findings_append_only.py` (test nuevo de preservación) | test | file-I/O | `verification/test_findings_append_only.py:38-60` (`_seed_with_operator_content` + `monkeypatch _FINDINGS_DIR`) | exact |
| `main_market_data.py` — `_seed_fid_counter` | utility (driver) | file-I/O | `main_market_data.py:99-107` (`_fid_counter` / `_next_fid`) + `verification/findings.py:187-200` (regexes de fid) | exact |
| `main_market_data.py` — gate driver-side | config/guard | request-response (decisión pura) | **NO hay analog destructivo** — ver § No Analog Found. Lo más cercano: `verification/mutation_gate.py:42-62` (forma a generalizar) + `client.py:259-285` (idioma de comparación correcto) | partial |
| `main_market_data.py` — probes de mutación sync | controller (probe) | request-response | `probe_symbols_sync` (`main_market_data.py:479-501`), `probe_market_data_sync` (`:364-395`) | exact |
| `main_market_data.py` — probes de mutación async | controller (probe) | request-response | `probe_health_async` (`main_market_data.py:332-356`) + `_async_main` (`:911-943`) | exact |
| `main_market_data.py` — `probe_cycle_closure` | controller (probe terminal) | batch/validation | `main_matriz.py:2243-2272` | exact |
| `main_market_data.py` — finding EXPECTED terminal (D-06/D-17) | controller | event | `main_matriz.py:2273-2299` (`idempotent_by_title=True`) | exact |
| `_core.py` — `parse_symbols_response`, `parse_calendar_response` | service (parser puro) | transform | `parse_latest_response` (`_core.py:796-830`) / `parse_market_data_response` (`:780-793`) | exact |
| `_core.py`/`client.py`/`aio.py` — `symbol_id: int \| str` | model/signature | request-response | `build_update_symbol_request` (`_core.py:436-455`) + shells `client.py:567` / `aio.py:578` | exact |
| `models.py` — `Symbol.id`, `CalendarDay` retipado | model | transform | `models.py:435-448` / `:449-461`; `CalendarConfig` (`:463+`) es el precedente de "modelo ya reconciliado contra el wire real" | exact |
| `packages/market-data-client/tests/test_*_write*.py` (regresiones) | test | request-response | `tests/test_symbols_write.py:45-70`, `tests/test_calendar_write.py:610-651` | exact |

---

## Pattern Assignments

### 1. `verification/findings.py` — preservar bullets humanos (bloqueante D-23)

**Analog:** el propio par parse/serialize (simetría a mantener). El bug es que el parser
retiene todos los bullets pero el modelo sólo transporta cuatro.

**Dónde se pierde** (`verification/findings.py:382-387` guarda todo, `:399-403` descarta):

```python
            bullet_match = _DETAIL_BULLET_RE.match(line)
            if bullet_match is not None:
                label = bullet_match.group("label").strip()
                value = bullet_match.group("value").strip()
                bullets_by_fid.setdefault(current_fid, {})[label] = value
                continue
```

```python
        bullets = bullets_by_fid.get(fid, {})
        expected = bullets.get("Expected", "")
        actual = bullets.get("Actual", "")
        diff = bullets.get("Diff", "")
        regression_raw = bullets.get("Regression")
```

**Modelo a extender** (`verification/findings.py:155-168`) — `@dataclass(frozen=True, slots=True)`,
el campo nuevo (`extra_bullets: dict[str, str]`) debe llevar `field(default_factory=dict)` para
no romper los call-sites posicionales:

```python
@dataclass(frozen=True, slots=True)
class _Finding:
    fid: str
    class_: str
    surface: str
    status: str
    title: str
    expected: str
    actual: str
    diff: str
    regression: str | None = None
```

**Punto de re-emisión** (`verification/findings.py:500-505`) — los bullets extra van **después**
de los cuatro conocidos, en orden de inserción, para que el round-trip sea byte-idéntico:

```python
            out.append(f"- **Expected:** {f.expected}")
            out.append(f"- **Actual:** {f.actual}")
            out.append(f"- **Diff:** {f.diff}")
            if f.regression is not None:
                out.append(f"- **Regression:** {f.regression}")
```

**Regex de bullet ya existente, no tocar** (`verification/findings.py:200`):

```python
_DETAIL_BULLET_RE = re.compile(r"^- \*\*(?P<label>[^:]+):\*\*\s*(?P<value>.*)$")
```

**Test de regresión — analog** `verification/test_findings_append_only.py:38-43` (fixture pattern:
skeleton + monkeypatch del dir):

```python
def _seed_with_operator_content(tmp_path, prefix: str, suffix: str) -> None:
    """Crea el archivo skeleton + inyecta operator prefix arriba y suffix abajo."""
    skeleton = new_findings("test-pkg")
    text = prefix + skeleton + suffix
    (tmp_path / "test-pkg-findings.md").write_text(text, encoding="utf-8")
```

```python
    monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
```

> Nota: el docstring de ese archivo (`:8-11`) **afirma hoy** que los bullets operator sobreviven.
> RESEARCH probó que sólo sobreviven vía el short-circuit no-OPEN (`findings.py:610`), no vía
> re-serialización. El test nuevo debe cubrir el caso "un fid **nuevo** se agrega y los vecinos
> conservan sus bullets".

---

### 2. `main_market_data.py` — allocator de fids seedeado (D-16/D-24)

**Analog exacto a reemplazar** (`main_market_data.py:99-107`):

```python
# Contador module-level para asignar fids deterministicamente F-01, F-02, ...
_fid_counter: int = 0


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"
```

**Por qué muere hoy** — `verification/findings.py:605-612` (el short-circuit que corta antes de
escribir cuando el fid ya existe no-OPEN; el chequeo por título de `:599-603` corre **antes** pero
sólo dedupea títulos ya existentes, por eso `idempotent_by_title=True` **no** resuelve D-16):

```python
    if idempotent_by_title:
        for existing_finding in findings_list:
            if existing_finding.title == title:
                path.write_text(_replace_art_block(text, art), encoding="utf-8")
                return path

    if fid in existing and existing[fid].status != "OPEN":
        path.write_text(_replace_art_block(text, art), encoding="utf-8")
        return path
```

**Regex de fid a espejar** (`verification/findings.py:192` / `verification/cycle_report.py:50`) —
el seed debe parsear los headers de detalle con la misma forma, sin ancho fijo:

```python
_DETAIL_HEADER_RE = re.compile(r"^###\s+(?P<fid>F-[^\s]+)\s+--\s+(?P<title>.*?)\s*$")
```

```python
_FINDING_BLOCK_HEADER_RE = re.compile(r"^### (F-[^\s]+)\b", re.MULTILINE)
```

**Call site** — el seed va inmediatamente después de `write_findings(_PKG)`
(`main_market_data.py:965-966`) y antes del primer `Client()` (`:969`):

```python
    # D-08.3: bootstrap idempotente del findings file (no-op si ya existe).
    write_findings(_PKG)

    # D-02: EXACTAMENTE UN Client sync threadeado a cada probe sync.
    client = Client()
```

---

### 3. Gate driver-side (D-01/D-02) — generalizar, no reusar

**Analog A — la forma a generalizar** (`verification/mutation_gate.py:42-62`). Copiar la
**estructura** (dos patas, línea SKIPPED sin dos puntos, fail-closed), **no** el cuerpo:

```python
def mutating_allowed() -> bool:
    """Solo permite mutaciones con flag opt-in Y base URL remarkets (D-16)."""
    if os.getenv("VERIFY_MUTATING") != "1":
        print("SKIPPED (mutating, guard off)")
        return False
    import matriz_client

    base = matriz_client.client._base_url  # estado resuelto en vivo; sólo lectura
    if urlsplit(base).hostname != _SANDBOX_HOST:
        print("SKIPPED (mutating, guard off)")  # host no-sandbox -> nunca mutar
        return False
    return True
```

El defecto de D-01 está en `:53` (`import matriz_client`) + `:55` (`matriz_client.client._base_url`):
la segunda pata valida el `base_url` de **otro paquete**. La generalización toma `base_url` y
`expected_host` **por parámetro**.

**Analog B — el idioma de comparación correcto, in-package Phase 25**
(`packages/market-data-client/src/market_data_client/client.py:276-285`; espejo async en
`aio.py:217`):

```python
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

**Resolución del `base_url` sin agregar ctor sites** (`_state.py:63-65`) — no es un `Call` a
`Client`/`AsyncClient`, así que el AST guard no lo cuenta:

```python
def _env_base_url() -> str:
    """Default-factory for ``base_url``; re-reads env var on each instantiation."""
    return os.getenv("MARKET_DATA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
```

**Constructor a parametrizar — el kwarg ya existe** (`client.py:126-157`, sentinel `None` =
"no cambiar"; el mismo bloque existe en `aio.py`):

```python
    def __init__(
        self,
        *,
        base_url: str | None = None,
        ...
        mutating_allowed: bool | None = None,
        expected_host: str | None = None,
        max_retries: int = 2,
    ) -> None:
```

```python
        if mutating_allowed is not None:
            self._state.mutating_allowed = mutating_allowed
        if expected_host is not None:
            self._state.expected_host = expected_host
```

**Constraint AST a respetar** (`verification/test_main_market_data_uses_single_client_instance.py:44-58`)
— el walker cuenta **tanto** `Client()` bare como `md.Client()` calificado:

```python
        if isinstance(func, ast.Name) and func.id in _CTOR_NAMES:
            ctor_sites.append((node.lineno, func.id))
        elif isinstance(func, ast.Attribute) and func.attr in _CTOR_NAMES:
            ctor_sites.append((node.lineno, func.attr))
    assert 1 <= len(ctor_sites) <= 2, (
        f"{_DRIVER} constructs {len(ctor_sites)} client instance(s) (expected 1..2): {ctor_sites}"
    )
```

**Toggle de `mutating_allowed` para el probe de refusal — precedente in-package**
(`packages/market-data-client/tests/test_mutation_gate.py:137-142`): mutar el field del `_state`
directamente **no** es un ctor site ni un `configure()`:

```python
    client._state.expected_host = None
    client._ensure_mutation_allowed()  # gate abierto: no debe levantar
    client._state.mutating_allowed = False
    with pytest.raises(MarketDataMutationNotAllowedError):
        client._ensure_mutation_allowed()
```

**Default de host ya disponible** (`_state.py:49-55`, `:104-105`):

```python
_DEFAULT_EXPECTED_HOST: str = (
    urlsplit(DEFAULT_BASE_URL).hostname or "market-data-develop.bbsa.com.ar"
)
```

```python
    mutating_allowed: bool = False
    expected_host: str | None = _DEFAULT_EXPECTED_HOST
```

---

### 4. Probes de mutación en `main_market_data.py` (probe, request-response)

**Analog canónico — `probe_symbols_sync`** (`main_market_data.py:479-501`). Este es el template
**literal** que los probes nuevos deben respetar: firma `(client: Client) -> ProbeResult`,
`name` como primera línea, `base_url` capturado **antes** del `try`, todo el post-processing
**dentro** del `try`, `except Exception as exc:  # D-09` como última línea:

```python
def probe_symbols_sync(client: Client) -> ProbeResult:
    """Symbols read sync (``active=False`` falsy filter) + SHAPE-diff + snapshot."""
    name = "symbols_sync"
    base_url = client._state.base_url
    try:
        symbols = client.get_symbols(active=False)
        raw = _raw_via_request_sync(
            client, _core.build_symbols_request(client._state, active=False)
        )
        # D-09: post-procesado dentro del try.
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, Symbol, "Symbol", "sync", base_url)
        _write_schema_snapshot(
            endpoint="/symbols",
            client_function="get_symbols",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        return ProbeResult(name, "PASS", f"symbols={len(symbols)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
```

**Espejo async — misma estructura, `surface="async"`, `aclient._state.base_url`**
(`main_market_data.py:332-356`):

```python
async def probe_health_async(aclient: AsyncClient) -> ProbeResult:
    """Health async: ``get_health`` + ``get_health_feed`` (anónimos, D-09)."""
    name = "health_async"
    base_url = aclient._state.base_url
    try:
        health = await aclient.get_health()
        ...
        return ProbeResult(name, "PASS", "health+feed ok")
    except Exception as exc:  # D-09: aislamiento per-probe (request + post-procesado)
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)
```

**Escalera de excepciones a reusar sin cambios** (`main_market_data.py:129-173`) — devuelve
`SKIPPED` para `ConnectError`/`ConnectTimeout` y `FINDING` para el resto; es lo que sostiene la
invariante "nunca FAILED":

```python
    if isinstance(exc, httpx.ConnectError | httpx.ConnectTimeout):
        fid = _next_fid()
        append_finding(
            _PKG, fid=fid, class_="NO-DATA", surface=surface, status="OPEN",
            title=f"{name}: develop inalcanzable", ...
        )
        return ProbeResult(name, "SKIPPED", "develop inalcanzable")
    class_ = "AUTH" if isinstance(exc, md.MarketDataAuthError) else "ERROR-MAP"
```

**Envelope-unwrap ya presente en un probe** (`main_market_data.py:377-383`) — el mismo shape
guard que los probes de mutación necesitan para localizar el `id` de D-10:

```python
        if isinstance(raw, dict):
            rows = raw.get("items", [])
        elif isinstance(raw, list):
            rows = raw
        else:
            rows = []
        sample = rows[0] if isinstance(rows, list) and rows else None
```

**Despacho crudo — el helper que NO debe usarse con specs de mutación**
(`main_market_data.py:244-258`): `client._request` **no** invoca el gate. El helper nuevo de
mutación debe llamar `_ensure_mutation_allowed()` primero (Pitfall 4 de RESEARCH):

```python
def _raw_via_request_sync(client: Client, spec: RequestSpec) -> Any:
    """Despacha un spec por el shell sync y devuelve el payload JSON CRUDO."""
    resp = client._request(spec)
    return resp.json()


async def _raw_via_request_async(aclient: AsyncClient, spec: RequestSpec) -> Any:
    """Espejo async de :func:`_raw_via_request_sync`."""
    resp = await aclient._request(spec)
    return resp.json()
```

**Snapshot write-once + emisión SHAPE (D-17)** (`main_market_data.py:191-206` escribe la baseline
una sola vez; `:227-241` emite el finding sin sobreescribir):

```python
    _SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    if not schema_file.exists():
        schema_file.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return
```

```python
    if committed.get("schema") == actual_schema:
        return
    fid = _next_fid()
    append_finding(
        _PKG, fid=fid, class_="SHAPE", surface=surface, status="OPEN",
        title=f"schema drift en {client_function}",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="baseline schema difiere; NO se sobreescribe (D-25)",
        base_url=base_url,
    )
```

**Cleanup — el anti-patrón a NO copiar** (`main_market_data.py:940-942` y `:995-997`). D-08 exige
`try/except` que **emite** un finding, no `contextlib.suppress`:

```python
    finally:
        with contextlib.suppress(Exception):
            await aclient.aclose()
```

```python
    finally:
        with contextlib.suppress(Exception):
            client.close()
```

**Registro del probe en el orquestador** (`main_market_data.py:972-986`, sync) y
(`main_market_data.py:919-931`, async, dentro del único `AsyncClient`):

```python
    client = Client()
    results: list[ProbeResult] = []
    seg_sync: list[Segment] | None = None
    try:
        results.append(probe_health_sync(client))
        ...
        async_results, seg_async = asyncio.run(_async_main())
        results.extend(async_results)
        results.append(probe_parity(seg_sync, seg_async, client))
```

```python
    aclient = AsyncClient()
    results: list[ProbeResult] = []
    seg_async: list[Segment] | None = None
    try:
        results.append(await probe_health_async(aclient))
```

> `_async_main()` toma **cero** argumentos hoy (`main_market_data.py:911`). Pasar el booleano del
> gate cambia su firma a `_async_main(mutating: bool)` y el call-site de `:984`.

---

### 5. `probe_cycle_closure` (D-18/D-21)

**Analog exacto** — `main_matriz.py:2243-2272` (probe terminal, emite `ProbeResult` y además un
finding `ERROR-MAP` OPEN cuando falla):

```python
        ok, missing = verify_cycle_closure(pkg)
        status_str = "PASS" if ok else "FAIL"
        detail = "" if ok else f"missing regressions: {', '.join(missing)}"
        results.append(
            ProbeResult(
                f"cycle_closure_{pkg.replace('-', '_')}",
                status_str,
                detail,
            )
        )
        if not ok:
            fid = _next_fid()
            append_finding(
                pkg, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                title=f"cycle closure: {len(missing)} CONFIRMED/FIXED without regression test",
                expected="every CONFIRMED/FIXED finding linked to existing test path",
                actual=f"missing regressions: {', '.join(missing)}",
                diff="see verify_cycle_closure output",
            )
```

**Import a agregar** — `main_market_data.py:48-55` importa de `verification` pero **no**
`verify_cycle_closure`; el analog es `main_matriz.py:76`:

```python
from verification import (
    diff_safemodel_bidirectional,
    safe_print,
    schema_of,
    write_findings,
)
from verification.env_gate import require_env
from verification.findings import append_finding
```

**Formato del bullet que el validador resuelve** (`verification/cycle_report.py:47` +
`:104-120` + `:172-174`) — path relativo a la raíz del repo, sin `..`, terminando en `.py`,
test name identificador Python válido, y el archivo debe contener `def <name>(`:

```python
_REGRESSION_RE = re.compile(r"^([^:\s]+\.py)::([A-Za-z_][A-Za-z0-9_]*)$")
```

```python
    rel_path = Path(test_file_rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        return (False, None, None)

    test_file_abs = (_REPO_ROOT / rel_path).resolve()
```

```python
        # Match both ``def test_x(`` and ``async def test_x(`` via substring.
        if f"def {test_name}(" not in content:
            missing.append(fid)
```

**Filtro de status** (`verification/cycle_report.py:148-151`) — sólo `CONFIRMED`/`FIXED`
participan; el backfill de D-21 apunta exactamente a esos 34:

```python
    for fid, status, regression in _iter_findings(text):
        # Filter: only CONFIRMED and FIXED participate in the check.
        if status not in ("CONFIRMED", "FIXED"):
            continue
```

**Serialización del bullet desde `findings.py`** (`:504-505`) — así se escribe cuando se emite
programáticamente; para un finding ya `FIXED` hay que editarlo a mano por el short-circuit de `:610`:

```python
            if f.regression is not None:
                out.append(f"- **Regression:** {f.regression}")
```

---

### 6. Finding EXPECTED terminal (D-06 operator-gated PUT, D-17 re-baseline)

**Analog exacto** — `main_matriz.py:2273-2299`, el único call-site del repo que usa
`idempotent_by_title=True` (evita duplicar el terminal cross-run con fids distintos):

```python
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface="sync",
        status="EXPECTED",
        title="prod-vs-remarkets divergence acknowledged",
        expected=(
            "verification limited to remarkets sandbox by safety policy "
            "(REQUIREMENTS.md Out of Scope)"
        ),
        actual=(
            "prod (api.primary.com.ar) shape unverified; sandbox shape "
            "committed in .planning/verification/schemas/matriz-client/"
        ),
        diff="N/A (acknowledged limitation, not detected drift)",
        base_url=base,
        idempotent_by_title=True,
    )
```

---

### 7. `_core.py` — `parse_symbols_response` (D-11/D-22) y `parse_calendar_response` (D-12)

**Analog canónico: el fix ya shippeado** `parse_latest_response` (`_core.py:814-830`). D-22 exige
mirror exacto: **conservar** `list[Symbol]`, desenvolver el envelope, collection-guard doble:

```python
    resp.read()
    received_at = time.time()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    if isinstance(raw, dict):
        rows = raw.get("items", [])
    elif isinstance(raw, list):
        rows = raw
    else:
        rows = []
    if not isinstance(rows, list):
        rows = []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in rows]
```

**Sibling idéntico** (`_core.py:780-793`, `parse_market_data_response`) — misma escalera, sin
`received_at` en los parsers de referencia (ver `_core.py:836-842`).

**Lo que hay que corregir — `parse_symbols_response`** (`_core.py:877-890`): itera `raw` directo,
así que un `object` de respuesta de mutación produce un `Symbol` all-default por **clave JSON**:

```python
def parse_symbols_response(resp: httpx.Response) -> list[Symbol]:
    """Pure: parse ``GET /symbols`` → ``list[Symbol]`` (D-05 / D-06).

    Body-consume-then-raise order; a 204 / ``null`` body collapses to ``[]``. No
    ``received_at`` stamp — reference data is unstamped (D-05).
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [Symbol.from_api(item) for item in raw]
```

**`parse_calendar_response`** (`_core.py:893-907`) — mismo defecto, envelope `{config, coverage,
days[], market}`; el unwrap es por `days`, no por `items`:

```python
def parse_calendar_response(resp: httpx.Response) -> list[CalendarDay]:
    """Pure: parse ``GET /calendar`` → ``list[CalendarDay]`` (D-05 / D-06).

    ``CalendarDay`` is treated as a flat list item (D-06 collection), not a
    wrapped object. ...
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [CalendarDay.from_api(item) for item in raw]
```

**Precedente passthrough (alternativa que D-11 dejaba abierta, descartada por D-22 para symbols)** —
`parse_calendar_write_response` (`_core.py:926-940`): una función **nueva** en vez de reusar un
parser de lectura, cuando el body no tiene shape tipable.

**Los 3 shells que consumen estos parsers** — el fix es en `_core.py` (un solo punto), pero
verificar que las 6 llamadas sigan compilando:

| Sync (`client.py`) | Async (`aio.py`) |
|---|---|
| `create_symbol` → `parse_symbols_response` `:554` | `:565` |
| `create_symbols` → `:565` | `:576` |
| `update_symbol` → `:576` | `:587` |
| `get_symbols` → `:535` | `:548` |
| `get_calendar` → `parse_calendar_response` `:582` | `:593` |

Además los shims module-level: `aio.py:885-935` (`create_symbol` … `delete_holiday`) y
`client.py:885+`.

---

### 8. `symbol_id: int | str` (D-09/D-22, Pitfall 8) — 3 sitios + espejo

**Builder puro** (`_core.py:436-455`) — el `del state` y el docstring que menciona el
percent-encoding diferido (que D-09 **disuelve**) están acá:

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

**Shell sync** (`client.py:567-576`):

```python
    def update_symbol(self, symbol_id: str, patch: SymbolPatch) -> list[Symbol]:
        """Gated ``PATCH {base_url}/symbols/{symbol_id}`` → tolerant ``list[Symbol]``.

        Gate-first (D-04/D-05). ``symbol_id`` is interpolated raw for Phase 25
        (percent-encoding of ``/``-bearing ids is D-08, deferred to Phase 27).
        """
        self._ensure_mutation_allowed()
        spec = _core.build_update_symbol_request(self._state, symbol_id, patch.to_dict())
        resp = self._request(spec)
        return _core.parse_symbols_response(resp)
```

**Shell async** (`aio.py:578-587`) — misma firma, `await self._request(spec)`.
**Shim module-level async** (`aio.py:895`), **shim sync** (`client.py:885+`).

**Forma canónica del método mutante a preservar en los 3** (`client.py:551-554`):
`_ensure_mutation_allowed()` → `_core.build_*` → `self._request(spec)` → `parse`.

---

### 9. `models.py` — `Symbol.id` (D-10) y `CalendarDay` retipado (D-12/D-13)

**Analog / target** (`packages/market-data-client/src/market_data_client/models.py:435-461`):

```python
@dataclass(frozen=True, slots=True)
class Symbol(SafeModel):
    """A symbol row from ``GET /symbols``.

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles). ...
    """

    symbol: str
    marketId: str
    active: bool


@dataclass(frozen=True, slots=True)
class CalendarDay(SafeModel):
    """A calendar day row from ``GET /calendar`` (flat list item, D-06). ..."""

    date: str
    marketId: str
    isBusinessDay: bool
```

**Precedente de "modelo reconciliado contra el wire real"** — `CalendarConfig`
(`models.py:463+`), cuyo docstring documenta explícitamente la reconciliación LIVE-MD-01 y usa
`str | None` para nullables. Ese es el estilo de docstring que `CalendarDay` debe adoptar tras
el fix.

**Contrato `SafeModel`** (CLAUDE.md + `models.py`): `@dataclass(frozen=True, slots=True)`,
construcción exclusiva vía `from_api`, defaults tipados (`str → ""`, `bool → False`),
`T | None = None` para nullables opt-in.

**Tests de modelo — analog** (`packages/market-data-client/tests/test_reference_models.py:55-62`):

```python
def test_symbol_from_api_extra_keys_ignored_and_false_preserved() -> None:
    sym = Symbol.from_api({"active": False, "extraKey": 1})
```

```python
def test_calendar_day_from_api_partial_fills_typed_zeros() -> None:
    day = CalendarDay.from_api({"date": "2026-07-30"})
```

> Estos dos tests **referencian los campos viejos** — el fix de D-12 los rompe y hay que
> actualizarlos en la misma edición.

---

### 10. Tests de regresión mockeados (D-15/D-20)

**Analog de dispatch happy-path** (`packages/market-data-client/tests/test_symbols_write.py:34-62`)
— `_open_gate()` vía `configure()` sobre el singleton, `httpx_mock.add_response`, asserts sobre
método/path/Bearer/body:

```python
def _open_gate() -> None:
    """Abre el gate del singleton default para el host del conftest."""
    market_data_client.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)
```

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

**Analog de test a nivel dispatch para un flip de `idempotent=` (D-20)** —
`packages/market-data-client/tests/test_calendar_write.py:610-651`. Contiene el par
negativo/positivo completo, el marker obligatorio y el monkeypatch de `time.sleep`:

```python
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_add_holidays_not_retried_on_repeated_503(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``idempotent=False``: 3x503 encolados → EXACTAMENTE 1 request y 0 sleeps."""
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))
    _open_gate()
    for _ in range(3):
        httpx_mock.add_response(method="POST", status_code=503)

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))

    assert len(httpx_mock.get_requests()) == 1
    assert sleeps == []
```

```python
    assert len(httpx_mock.get_requests()) == 3
    assert len(sleeps) == 2
```

Mismo patrón de `monkeypatch.setattr(time, "sleep", ...)` en `tests/test_transport.py:98`.

**Espejo async obligatorio** — `tests/test_symbols_write_async.py` y
`tests/test_calendar_write_async.py` existen y replican archivo-por-archivo; todo test nuevo sync
necesita su par async (`asyncio_mode = "auto"`, sin decorador).

**Naming de los tests** — deben ser resolubles por `verify_cycle_closure`: el bullet
`Regression: packages/market-data-client/tests/<file>.py::<test_name>` exige que el archivo
contenga literalmente `def <test_name>(`.

---

## Shared Patterns

### Aislamiento D-09 por probe
**Source:** `main_market_data.py:328-329` (y `:394`, `:420`, `:448`, `:500`, `:572`)
**Apply to:** todo probe nuevo, sync y async.
```python
    except Exception as exc:  # D-09: aislamiento per-probe (request + post-procesado)
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
```
`verification/test_main_drivers_bare_except.py:25` limita su scope a `main_matriz.py` y
`main_higyrus.py` — este patrón es legítimo acá.

### Post-processing dentro del `try` (guard AST)
**Source:** `verification/test_main_market_data_postprocess_guarded.py:34-57`
**Apply to:** cada `_emit_shape` / `_write_schema_snapshot` de un probe nuevo.
```python
_GUARDED_HELPERS = frozenset({"_emit_shape", "_write_schema_snapshot"})
_MIN_GUARDED_CALLS = 10
```
```python
    for node in ast.walk(func):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                for descendant in ast.walk(stmt):
                    if isinstance(descendant, ast.Call):
                        protected.add(id(descendant))
```
`except`/`else`/`finally` están **deliberadamente excluidos** — poner un snapshot en el `finally`
del cleanup pone el guard RED.

### Emisión de findings
**Source:** `verification/findings.py:517-532` (firma) — kwargs obligatorios `class_`, `surface`,
`status`, `title`, `expected`, `actual`, `diff`; opcionales `regression`, `base_url`,
`market_hours`, `idempotent_by_title`. `title` debe ser **una sola línea**
(`findings.py:573-574` levanta `ValueError`).
**Apply to:** todos los call-sites nuevos del driver.

### Impresión redactada
**Source:** `main_market_data.py:999-1009`
```python
    for r in results:
        safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=[])
```
Las líneas `PROBE <name>: SKIPPED ...` empiezan con `PROBE`, así que no matchean
`_ENV_SKIP` de `main_verify.py:42`. La línea colon-less `SKIPPED (mutating, guard off)` de
`verification/mutation_gate.py:45` tampoco.

### Espejado sync/async (CLAUDE.md, no negociable)
| Punto de cambio | Sync | Async |
|---|---|---|
| Gate | `client.py:259-285` | `aio.py:217` |
| `create_symbol` | `client.py:541-554` | `aio.py:554-565` |
| `create_symbols` | `client.py:556-565` | `aio.py:567-576` |
| `update_symbol` | `client.py:567-576` | `aio.py:578-587` |
| `get_calendar` | `client.py:578-582` | `aio.py:589-593` |
| `add_holidays` | `client.py:654-675` | `aio.py:666-687` |
| `delete_holiday` | `client.py:677-694+` | `aio.py:689-707+` |
| Shims module-level | `client.py:885+` | `aio.py:885-935` |
| Parsers (colapsan a uno) | `_core.py:877-907` | idem |
| Probes del driver | `probe_*_sync` | `probe_*_async` |
| Tests | `tests/test_symbols_write.py`, `tests/test_calendar_write.py` | `..._async.py` |

---

## No Analog Found

| Archivo / unidad | Role | Data flow | Razón |
|---|---|---|---|
| Gate driver-side destructivo + disciplina de cleanup en `main_market_data.py` | config/guard + controller | request-response | **No existe precedente destructivo en el repo** (D-25, verificado en RESEARCH: ningún driver invoca `mutating_allowed()`; `main_matriz.py` no tiene probes de mutación). El único guard driver-side es `main_matriz.py:2166`, un chequeo **por substring** — el anti-patrón explícitamente documentado en `verification/mutation_gate.py:56-59`. Se diseña en esta fase combinando la **forma** de `mutation_gate.py:42-62` con el **idioma de comparación** de `client.py:276-285`. |
| Probe de residue sweep por prefijo | controller | batch | Sin precedente; RESEARCH da la forma propuesta (`27-RESEARCH.md:1014-1038`), construida sobre el template de probe de § 4. |

---

## Metadata

**Analog search scope:** `main_*.py` (6 drivers, raíz), `verification/` (módulos + 26 tests),
`packages/market-data-client/src/market_data_client/` (`client.py`, `aio.py`, `_core.py`,
`models.py`, `_state.py`), `packages/market-data-client/tests/` (22 archivos).
**Files scanned:** ~20 leídos en detalle
**Pattern extraction date:** 2026-08-01
