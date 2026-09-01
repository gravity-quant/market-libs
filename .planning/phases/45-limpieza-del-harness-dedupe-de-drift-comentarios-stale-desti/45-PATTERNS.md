# Phase 45: Limpieza del harness — Pattern Map

**Mapped:** 2026-09-01
**Files analyzed:** 10 (5 drivers, 2 verification tests existentes, 1 test nuevo, `tools/check_surface_types.py`, `ci.yml`, 1 artefacto de decisión)
**Analogs found:** 10 / 10 (todo lo que esta fase necesita ya existe en el repo — ver `45-RESEARCH.md § Don't Hand-Roll`)

> **Nota de autoridad:** este documento sigue el **checkpoint de resolución post-research** de
> `45-CONTEXT.md` (D-01/D-05/D-08/D-10 ENMENDADAS). La clave de dedupe es **`(func, digest)`** —
> sin `surface`. Las cifras de `check_surface_types.py` son **187 / 337 / 467**, re-medidas en
> HEAD durante este mapeo (comando abajo).

---

## File Classification

| Archivo (nuevo/modificado) | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `main_market_data.py:509-521` (drift) | driver / probe helper | event-driven (emisión de finding) | `verification/divergences.py:167-181` (dedupe) + `main_market_data.py:492-506` (forma del call site) | exact |
| `main_iol.py:1753-1766` (schema drift) | driver / probe helper | event-driven | `main_market_data.py` drift site (mismo autor, mismo shape) | exact |
| `main_higyrus.py:589-601` (schema drift) | driver / probe helper | event-driven | `main_iol.py:1753-1766` (**byte-idéntico salvo el fid**) | exact |
| `main_matriz.py:583-596` (schema drift) | driver / probe helper | event-driven | `main_higyrus.py:589-601` (idéntico; sólo `surface="sync"` y `_schema_path()`) | exact |
| `main_ambito_financiero.py:607-619` (schema drift) | driver / probe helper | event-driven | `main_iol.py:1753-1766` (título literal, no f-string) | exact |
| `main_iol.py:1617` / `:1685` (type drift ×2) | driver / probe inline | event-driven | `main_iol.py:1601-1613` (sitio hermano `missing assumed key`) | exact |
| `main_market_data.py:1541-1542` (D-09) | driver / parity probe | transform (comparación) | `packages/market-data-client/.../models.py:870-895` (`Segment`) | exact |
| `verification/test_drift_dedupe_falsification.py` **(nuevo, D-04)** | test (driver lock) | request-response mockeado + AST | `verification/test_finding_count_consistency.py` (aislamiento + fail-first arm) + `verification/test_main_matriz_risk_envelope_keys.py` (lock de driver) | exact |
| `tools/check_surface_types.py:45-62` (D-05) | config / gate docstring | — (prosa) | `verification/test_probe_context_coverage.py:1-35` (docstring con alcance fechado) | role-match |
| `.github/workflows/ci.yml:80-93` (D-06/D-10/D-11) | config / CI | batch | la propia lista (extensión, no reemplazo) | exact |
| `45-HARN-04-DECISION.md` **(nuevo, D-08)** | artefacto de decisión | — | `.planning/phases/43-.../43-DISPOSITION.md` | exact |

---

## Pattern Assignments

### Sitios de drift (7) — drivers `main_*.py` (driver, event-driven)

**Analog primario del mecanismo:** `verification/divergences.py:130-181`
**Analog de la forma del call site:** el propio código de cada driver (abajo, verbatim de HEAD)

#### Forma actual — `main_market_data.py:509-521` (el ÚNICO de los 7 que puede duplicar in-process)

```python
    if committed.get("schema") == actual_schema:
        return
    fid = _next_fid()                                    # ← ORDEN A CORREGIR (D-03)
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface=surface,
        status="OPEN",
        title=f"schema drift en {client_function}",       # ← content-free
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="baseline schema difiere; NO se sobreescribe (D-25)",
        base_url=base_url,
    )
```

Contexto que el planner necesita: `_write_schema_snapshot(endpoint, client_function, raw, base_url, surface)`
(`main_market_data.py:459-465`), `actual_schema = schema_of(raw)` (`:473`), baseline elegido
**sólo por `client_function`** (`:474`) — por eso sync y async comparan contra el mismo archivo y
producen el mismo `actual_schema`, que es exactamente lo que la clave `(func, digest)` colapsa
(22 → 11).

#### Forma actual — `main_iol.py:1753-1766` / `main_higyrus.py:589-601` / `main_matriz.py:583-596`

Los tres son **el mismo bloque**; difieren sólo en `surface` (`"both"`, `"both"`, `"sync"`) y en
cómo resuelven `file_path`:

```python
    committed = json.loads(file_path.read_text(encoding="utf-8"))
    if committed.get("schema") == actual_schema:
        return ("PASS", f"{file_path.name} sin drift")
    fid = _next_fid()                                    # ← ORDEN A CORREGIR (D-03)
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface="both",
        status="OPEN",
        title=f"Schema drift en {func_name}",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="comparar expected vs actual; NO se sobreescribe baseline (D-25)",
        base_url=base_url,
    )
    return ("FINDING", f"{fid}|{file_path.name}")
```

**Contrato de retorno a preservar:** estos tres helpers devuelven `tuple[str, str]`
(`("PASS"|"FINDING", detalle)`). El no-op del dedupe **no puede `return` desnudo** acá — tiene que
devolver una tupla. Forma sugerida: `return ("PASS", f"{file_path.name} drift ya reportado")`.
Es la diferencia estructural más importante contra `main_market_data.py`, cuyo helper devuelve
`None` y donde `return` desnudo sí es correcto.

`main_ambito_financiero.py:607-619` es el mismo bloque con `title="Schema drift en get_dollar_banco_nacion"`
(literal, sin f-string) y retorno `ProbeResult("schema_snapshot", "FINDING", f"{fid} (OPEN) — NO sobreescribe")`.
El no-op ahí devuelve un `ProbeResult`, análogo al de `:605` (`ProbeResult(..., "PASS", "schema sin drift")`).

#### Forma actual — los 2 sitios de type drift, `main_iol.py:1617` y `:1685`

```python
                elif observed[key] != expected_type:
                    fid = _next_fid()
                    append_finding(
                        _PKG,
                        fid=fid,
                        class_="SHAPE",
                        surface="both",
                        status="OPEN",
                        title=f"type drift on `{key}` in get_quote",
                        expected=f"`{key}`: {expected_type}",
                        actual=f"`{key}`: {observed[key]}",
                        diff=f"tipo observado != asumido para `{key}`",
                        base_url=base_url,
                    )
                    finding_fids.append(fid)
```

**Diferencia estructural crítica:** estos dos sitios están **inline dentro de un bucle**, no en un
helper, y **acumulan `finding_fids.append(fid)`** — lista que alimenta el `ProbeResult` final
(`if finding_fids: return ProbeResult(...)`, `:1700`). El no-op del dedupe acá es `continue`
(o simplemente no entrar a la rama), y **no debe** hacer `finding_fids.append`. Ese `finding_fids`
es el conteo que P-3 protege conceptualmente: si el fid no se quema, no se acumula.
`:1685` es idéntico con `observed_row` / `get_historical_quotes[0]`.

#### Patrón a APLICAR (RESEARCH § Pattern 2, con la clave ENMENDADA por D-01)

Junto a `_fid_counter` en cada driver (`main_market_data.py:335`, `main_iol.py:212`,
`main_higyrus.py:220`, `main_matriz.py:353`, `main_ambito_financiero.py:98`):

```python
_seen_drift_keys: set[tuple[str, str]] = set()
```

En el sitio de drift, **antes** de `_next_fid()`:

```python
    key = (client_function, _drift_digest(actual_schema))   # D-01 ENMENDADA: SIN surface
    if key in _seen_drift_keys:
        return                       # no-op: NINGÚN fid consumido (D-03)
    _seen_drift_keys.add(key)
    fid = _next_fid()                # ← el fid se asigna DESPUÉS de la decisión
    append_finding(..., fid=fid, title=f"schema drift en {client_function}", ...)
```

Por qué **no** `idempotent_by_title=True` en la rama drift (medido, `RESEARCH § Hallazgo 3`): el
scan por título de `append_finding` corre **antes** de la guarda de status humano
(`verification/findings.py:664-670`, ver excerpt abajo), así que bajo
`schema drift en get_market_data` —donde conviven F-37 `EXPECTED`, F-74 `NO-FIX` y F-203 `OPEN`—
un drift nuevo haría no-op contra el bloque terminal y desaparecería de la cola OPEN. Ese es
Pitfall 9 con fids concretos.

**Contrato a NO romper:** la ladder D-09 (`_finding_for_exc` en cada driver) — un no-op de dedupe
sigue siendo un camino sin excepción. Y el título humano **no cambia**, así que el round-trip del
parser de `findings.py` y la invariante CR-02 de título single-line (`findings.py:640-642`) quedan
intactos.

---

### `main_market_data.py:1541-1542` (driver, transform) — D-09

**Analog:** `packages/market-data-client/src/market_data_client/models.py:870-895` (la definición de `Segment`).

**Forma actual:**
```python
    try:
        ids_sync = sorted(s.marketSegmentId for s in seg_sync)
        ids_async = sorted(s.marketSegmentId for s in seg_async)
    except Exception as exc:  # D-09: la comparación nunca crashea el driver
        return _finding_for_exc(exc, name=name, surface="both", base_url=base_url)
```

**Fix:** `s.segment` en ambas líneas. Ambos campos son `str`; `sorted()`, `set()` y los `len()` de
los mensajes de abajo siguen funcionando sin cambios. Sin espejo sync/async (es un dereference de
driver, no de `client.py`/`aio.py`).

**Verificación:** `uv run mypy main_market_data.py` — hoy levanta los 2 errores
(`"Segment" has no attribute "marketSegmentId"`); después del fix debe quedar limpio en esas líneas.
Ningún gate de CI apunta a los drivers de la raíz (Q5, declarar por escrito en el cierre).

---

### `verification/test_drift_dedupe_falsification.py` (nuevo, test / driver lock)

**Analogs (dos, complementarios):**

1. **`verification/test_finding_count_consistency.py`** — aislamiento + estructura de dos brazos.
   Copiar su patrón de monkeypatch del directorio de findings (obligatorio: ningún test toca
   `.planning/verification/`):
   ```python
   monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
   ```
   y su contador de bloques:
   ```python
   _DETAIL_HEADER_RE = re.compile(r"^### F-", re.MULTILINE)
   ```
   Su docstring (`:1-35`) es el modelo de redacción: nombra el arm de colapso **y** el arm de
   control, y explica por qué sin el segundo el primero no prueba nada. El test de D-04 tiene el
   mismo requisito literal (`CONTEXT § Specific Ideas`: el docstring debe nombrar el escenario que
   NO debe colapsar).

2. **`verification/test_main_matriz_risk_envelope_keys.py:1-60`** — cómo un lock **de driver** se
   escribe y por qué vive en `verification/` y no en `packages/*/tests/`. Usa `import main_matriz`
   + `inspect.signature` + `ast` sobre `Path(main_matriz.__file__)`. Su docstring declara
   explícitamente que corre desde la lista del job `lint`.

**Reset de estado de driver entre tests** (imprescindible, si no los tests se contaminan): los
fixtures existentes ya hacen `main_matriz._fid_counter = 0`
(`verification/test_main_matriz_login_fail_uniformity.py:38-40`). El test nuevo debe resetear
**también** `_seen_drift_keys` de cada driver que toque.

**Los dos brazos obligatorios (D-04):**
- (a) misma divergencia repetida dentro de una corrida → 1 bloque `### F-`
- (b) divergencia **distinta** sobre el **mismo** endpoint dentro de la misma corrida → 2 bloques.
  Bajo la clave `(func, digest)` este brazo cubre exactamente el caso sync≠async.

**Extender, no reemplazar** `verification/test_findings_dedupe_by_title.py`: ese archivo prueba el
contrato genérico de `idempotent_by_title` sobre 4 paquetes parametrizados y su docstring declara
alcance "HARN-08 / HARN-10". Recomendación del research: archivo nuevo, para no hacer mentir ese
docstring.

---

### `tools/check_surface_types.py:45-62` (config / docstring) — D-05 ENMENDADA

**Forma actual (verbatim, HEAD):**
```
was measured rather than suspected. **Before Phase 37** this gate printed::

    surface types: 6 packages, 183 `__all__` names, 330 definitions scanned,
    13 constant/alias exports, 23 exempted (dunder 13, private-helper 1,
    serialize-out 9), 0 violations
...
being read as checking. **After Phase 37**, over a tree whose fields have since
been typed::

    surface types: 6 packages, 186 `__all__` names, 330 definitions scanned,
    442 fields scanned, 13 constant/alias exports, 24 exempted (dunder 13,
    private-helper 1, serialize-out 9, ws-catch-all 1), 0 violations
```

**Acción (D-05 ENMENDADA):**
- **`:47`** — dejar `183 / 330` **sin tocar** (cita histórica byte-idéntica de `00ffb2f~1`);
  sólo agregar el pin de commit al framing: `**Before Phase 37** (medido en ``00ffb2f~1``) this gate printed::`
- **`:58`** — reemplazar el bloque congelado por el valor medido hoy, y fecharlo/pinnearlo.
  **Las tres cifras están stale, no una.**

**Valor re-medido durante este mapeo** (`uv run python tools/check_surface_types.py`, HEAD `22bc8ed`):
```
surface types: 6 packages, 187 `__all__` names, 337 definitions scanned, 467 fields scanned,
13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9,
ws-catch-all 1), 0 violations
```
→ `186→187`, `330→337`, `442→467`. **No escribir `336`.** El planner debe re-correr el gate antes
de escribir el número (el árbol puede haberse movido).

**Analog de framing** — `verification/test_probe_context_coverage.py:1-35`, cuyo docstring cierra
con una sección `**Alcance:**` explícita. El defecto de `:58` es exactamente la ausencia de esa
sección.

---

### `.github/workflows/ci.yml:80-93` (config / CI) — D-06 + D-10 ENMENDADA + D-11

**Analog:** la propia lista. Es una **extensión**, en **un solo** cambio consolidado (D-11).
Patrón lockeado (Phase 32 D-05 / Phase 42-01): step dentro del job `lint`, **nunca** job nuevo.

**Forma actual (`:80-93`):**
```yaml
        run: |
          uv run pytest -q \
            verification/test_main_market_data_deep_chain.py \
            ... (13 archivos)
            verification/test_literal_census_venue_gate.py
```

**Archivos a agregar (5):**
| Archivo | Origen | Precondición verificada |
|---|---|---|
| `verification/test_public_surface.py` | D-06 / IN-06 | 4 passed standalone (Hallazgo 6) |
| `verification/test_finding_count_consistency.py` | D-10 | — |
| `verification/test_findings_dedupe_by_title.py` | D-10 | 12 passed (research) |
| `verification/test_drift_dedupe_falsification.py` (nuevo) | D-04 | lo entrega esta fase |
| `verification/test_probe_context_coverage.py` | **D-08/D-10 ENMENDADAS** | **6 passed — re-verificado en este mapeo** (`uv run pytest -q` → `6 passed in 0.10s`) |

**Preservar sin tocar** el comentario de `:69-78` — es la razón escrita por la que la lista es
explícita y no `pytest verification/`. Cambiarla a `pytest verification/` enrolaría 40 archivos
nunca corridos: prohibido por D-10, `STACK.md:212` y Pitfall 12.

**Censo a re-declarar por escrito en el cierre:** **53 en disco / 13 enrolados / 40 inertes** en
HEAD (no 52/12/40 de `41-ROLLUP.md`). Tras esta fase: 54 / 18 / 36.

---

### `45-HARN-04-DECISION.md` (nuevo, artefacto de decisión) — D-08

**Analog:** `.planning/phases/43-.../43-DISPOSITION.md`

**Patrón de header a copiar:**
```markdown
# Phase 43 — Disposición campo por campo, evidencia medida y seguimiento

**Fecha:** 2026-09-01 · **Requisitos:** `SHAPE-01`, `HARN-02` · **Planes:** 43-01, 43-02, 43-03
**Fuente de forma:** ...

Este archivo es la evidencia de los criterios 1, 2, 3 y 5 de la fase. Todo lo que afirma está
**medido en la corrida de este plan** y la medición está pegada; nada se hereda de un reporte.
```
La fecha en el header satisface literalmente "decisión escrita y **fechada**" (criterio 3 del ROADMAP).

**Contenido mínimo lockeado — una fila por archivo, tres ítems cada una:**

| Ítem | `test_matriz_sweep_snapshot.py` | `test_main_matriz_login_fail_uniformity.py` |
|---|---|---|
| (1) ¿asevera algo que CI no? | **No.** Superseded in-code — citar verbatim el docstring del propio test verde: *"El lock estructural completo … vive en `verification/test_main_matriz_risk_envelope_keys.py`, que además corre en CI"* (enrolado en `ci.yml:83`) | **Sí, una:** `probe_login_sync` devuelve `FINDING`, no `FAIL`. Conducta presente y verificada en HEAD (`main_matriz.py:807`). Se acepta la ausencia de guardián de regresión, no un defecto abierto |
| (2) rol de canario `probe_context` | **TRANSFERIDO** a `verification/test_probe_context_coverage.py`, **enrolado en CI en esta misma fase** (D-08 ENMENDADA) — nombrar el enrolamiento, no sólo el archivo | ídem |
| (3) los 3 tests verdes | Los 3 están acá: `..._count_matches_18_minus_cfi_sanity` (auto-referencial: `len(_PROBE_FIXTURES)==17` sobre una tabla del propio archivo), `..._envelope_probe_helper_exists`, `..._risk_probes_unwrap_their_envelope_key`. Los 2 últimos subsumidos; el 1ro pierde su sujeto si el archivo se retira → cero cobertura de producción perdida | **Cero** tests verdes |

**Además:** cerrar Q4 por escrito (o los ~3 grep-asserts sobre el ya-enrolado
`verification/test_main_matriz_skip_line_shape.py`, o el descarte explícito) y declarar Q5
(gap de mypy sobre los 5 drivers de la raíz) con destino nombrado en el backlog v1.9.

**Nota:** "aceptar deuda documentada" **no implica `git rm`**. Es compatible con dejar los 2
archivos en disco con un puntero al documento de decisión (`RESEARCH § Anti-Patterns`).

---

## Shared Patterns

### `append_finding` — el orden interno que gobierna todo (leer antes de tocar la rama drift)

**Source:** `verification/findings.py:664-680`
**Apply to:** los 7 sitios de drift + el test de D-04

```python
    # HARN-08/10 — content-addressed dedupe by title (opt-in via kwarg).
    if idempotent_by_title:
        for existing_finding in findings_list:
            if existing_finding.title == title:
                path.write_text(_replace_art_block(text, art), encoding="utf-8")
                return path

    # CR-01: Preservación de status promovido por humano.
    if fid in existing and existing[fid].status != "OPEN":
        path.write_text(_replace_art_block(text, art), encoding="utf-8")
        return path
```

El scan por título está **arriba** de la guarda de status humano. Ése es el hecho estructural que
descalifica `idempotent_by_title=True` para la rama drift (títulos endpoint-scoped que ya tienen
bloques `EXPECTED`/`NO-FIX` triageados en el ledger committeado).

### Título portador de identidad + `idempotent_by_title` (el precedente correcto, para NO copiarlo entero)

**Source:** `verification/divergences.py:167-181`
**Apply to:** referencia conceptual para el test de D-04

```python
            _findings.append_finding(
                slug,
                fid=self._next_fid(slug),
                class_="SHAPE",
                surface=surface,
                status="OPEN",
                # Determinístico y portador de identidad: este string ES la
                # clave de dedupe cross-run (33-01-SUMMARY.md, selección
                # ``surface-in-title-write-new``).
                title=f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]",
                expected=f"model declares {declared}",
                actual=f"wire sent {observed}",
                diff=f"{declared} -> {observed} at {model}{path} via {endpoint}",
                idempotent_by_title=True,
            )
```

**Dos aspectos a NO copiar:**
1. `fid=self._next_fid(slug)` **inline como argumento** — asigna el fid antes de la decisión de
   dedupe, exactamente el hazard que D-03 prohíbe. Es tolerable ahí porque la unidad de censo de
   ese handler es `self.seen` (`divergences.py:136,166`), no el conteo de fids — desacople que su
   propio docstring declara (`:121-123`).
2. `idempotent_by_title=True` — ver arriba.

### Allocator de fids (los 5 drivers, forma idéntica)

**Source:** `main_market_data.py:335-353` (`main_iol.py:212-250`, `main_higyrus.py:220-316`,
`main_matriz.py:353-392`, `main_ambito_financiero.py:98-132` son espejos declarados)
**Apply to:** todos los sitios de drift

```python
_fid_counter: int = 0


def _seed_fid_counter() -> None:
    global _fid_counter
    _fid_counter = max_existing_fid(_PKG)


def _next_fid() -> str:
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"
```

`_seen_drift_keys` va **junto a** `_fid_counter` en cada driver (mismo bloque de estado
module-level), y **no** en `verification/findings.py` — ese módulo es append-only por contrato y
darle estado de sesión rompe el aislamiento por `monkeypatch(_FINDINGS_DIR)` del que dependen 4
archivos de test (`STACK.md:219`).

`_seed_fid_counter()` y el dedupe son **ortogonales** — no fusionarlos
(`verification/test_findings_fid_seed.py` documenta que `idempotent_by_title` provably does not
substitute para el seed).

### Aislamiento de tests sobre findings

**Source:** `verification/test_finding_count_consistency.py:60-70` y
`verification/test_findings_dedupe_by_title.py:31`
**Apply to:** el test nuevo de D-04

```python
monkeypatch.setattr("verification.findings._FINDINGS_DIR", tmp_path)
```

Ningún test toca `.planning/verification/`; el gate de aceptación grepea
`git status --porcelain .planning/verification/` después de correrlos.

---

## No Analog Found

Ninguno. Los 10 sujetos tienen analog en el repo. `RESEARCH § Don't Hand-Roll` es explícito:
*"cualquier plan que introduzca un mecanismo nuevo está, con alta probabilidad, sin haber
encontrado el precedente."*

---

## Metadata

**Analog search scope:** `main_*.py` (raíz), `verification/`, `tools/`, `.github/workflows/`,
`packages/market-data-client/src/market_data_client/models.py`, `.planning/phases/43-*/`
**Files scanned:** 14
**Comandos de verificación corridos durante este mapeo:**
- `uv run python tools/check_surface_types.py` → `187 / 337 / 467`, 0 violations
- `uv run pytest -q verification/test_probe_context_coverage.py` → `6 passed in 0.10s`

**Pattern extraction date:** 2026-09-01 (HEAD `22bc8ed`, rama `milestone/v1.8-cierre-deuda-post-v1.7`)
