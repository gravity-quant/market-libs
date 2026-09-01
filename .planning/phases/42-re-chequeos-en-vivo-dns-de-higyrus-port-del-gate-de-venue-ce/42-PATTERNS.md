# Phase 42: Re-chequeos en vivo — DNS de higyrus + port del gate de venue + censo `Literal` de matriz - Pattern Map

**Mapped:** 2026-08-31
**Files analyzed:** 11 (2 nuevos de código/test, 1 config, 4 scripts de raíz modificados, 5 tests de pin, 2 artefactos doc)
**Analogs found:** 10 / 11

> Esta fase **no crea superficie nueva de librería**. Todo el trabajo es cableado y orden sobre
> código de raíz (`main_*.py`, `scripts/`, `verification/`) que ya existe. Por eso casi todos los
> analogs son **exactos** — el patrón a copiar ya está escrito en el repo, muchas veces en el
> archivo hermano del que se toca.

## File Classification

| New/Modified File | Nuevo/Mod | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|-----------|------|-----------|----------------|---------------|
| `verification/test_literal_census_venue_gate.py` | NUEVO | test (guard/lock) | transform (AST) + request-response puro (predicado) | `verification/test_main_matriz_skip_line_shape.py` | **exact** |
| `scripts/literal_census_33.py` | MOD | script/CLI + gate de acceso | request-response → transform → stdout | `main_matriz.py` (`_venue_token`/`_VENUE_ALLOWLIST`) + el propio archivo (`--selftest`, `capture()`) | **exact** |
| `.github/workflows/ci.yml` | MOD | config (CI) | batch | el propio bloque `run:` líneas 79-92 | **exact** |
| `main_market_data.py` | MOD | driver de verificación | file-I/O (dump de wire crudo) | `_write_schema_snapshot` (`:457-522`, envelope) + `census_matriz()` (`literal_census_33.py:212-214`, uso de `capture`) | **exact** |
| `main_higyrus.py` | MOD (rename) | driver de verificación | request-response → veredicto stdout | `main_matriz.py:151-165` (constantes de skip/destino) | **exact** |
| `main_matriz.py` | MOD (rename, 1 línea) | driver de verificación | — | sí mismo (`_CYCLE_CLOSURE_DESTINATION:162-165`) | **exact** |
| `verification/test_main_higyrus_skip_line_shape.py` | MOD (pin) | test | transform | `verification/test_main_matriz_skip_line_shape.py` | **exact** |
| `verification/test_main_verify_classification.py` | MOD (pin) | test | transform | ídem | **exact** |
| `verification/test_run_evidence.py` | MOD (pin) | test | file-I/O | ídem | **exact** |
| `verification/test_cycle_closure_phase33.py` | MOD (pin parcial) | test | transform | ídem — **⚠ línea 250 NO se toca** | **exact** |
| `verification/test_main_higyrus_deep_chain.py` | MOD (docstring) | test | — | ídem | role-match |
| `42-CENSUS.md` (artefacto de salida) | NUEVO | doc/artefacto | batch | `.planning/milestones/v1.6-phases/33-…/33-CENSUS.md` | role-match |
| `42-WIRE-READ.md` (artefacto committeado, D-08/Q1(b)) | NUEVO | doc/artefacto | batch | envelope de `_write_schema_snapshot` (`main_market_data.py:474-480`) | **partial — sin analog directo** |
| Task de checkpoint dentro de `42-0X-PLAN.md` | NUEVO | plan (checkpoint) | event-driven (gate humano) | `39-01-PLAN.md:87-141` | **exact** |

---

## Pattern Assignments

### `verification/test_literal_census_venue_gate.py` (test, NUEVO)

**Analog:** `verification/test_main_matriz_skip_line_shape.py` (269 líneas, leído íntegro)

**Imports pattern** (`:26-36`) — copiar tal cual, cambiando el target:
```python
from __future__ import annotations

import ast
from pathlib import Path

import main_matriz
import pytest
from main_verify import _ENV_SKIP          # sólo si el test nuevo también valida forma de stdout

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_matriz.py"                 # ← cambiar a: scripts/literal_census_33.py
```
Notas: `from __future__ import annotations` es obligatorio (convención uniforme del repo).
Los imports de raíz funcionan sin `sys.path` hack gracias a `pythonpath = ["."]`
(`pyproject.toml:109`). Para el módulo del script: `import scripts.literal_census_33 as census`
(namespace package, sin `__init__.py` — verificado en RESEARCH).

**Docstring de módulo** (`:1-24`) — el analog abre con un docstring largo que declara (a) qué lock
es, (b) las dos capas del test, (c) qué NO se toca (`mutation_gate.py`). Espejar esa estructura:
el docstring es parte del entregable en este repo, no decoración.

**Pin de allowlist** (`:205-215`) — adaptar a pin de **identidad** (D-01 exige `is`, no `==`):
```python
def test_venue_allowlist_has_exactly_the_two_known_hosts() -> None:
    """Dos entradas y ninguna más: ampliar el allowlist es una decisión humana (D-02)."""
    allowlist = main_matriz._VENUE_ALLOWLIST
    assert set(allowlist) == {
        "api.remarkets.primary.com.ar",
        "api.bbsa.matrizoms.com.ar",
    }, (
        "el allowlist D-MATZ-33 tiene exactamente dos hosts confirmados por el "
        "operador; cualquier agregado requiere un checkpoint humano nuevo (P-05)."
    )
    assert len(allowlist) == 2
```
→ El test nuevo agrega encima:
```python
assert census._venue_token is main_matriz._venue_token
assert census._VENUE_ALLOWLIST is main_matriz._VENUE_ALLOWLIST
```

**Tabla de spoofing** (`:218-244`) — **13 casos, copiar verbatim** (están en HEAD, ya validados):
```python
@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("api.remarkets.primary.com.ar", "remarkets"),
        ("https://api.remarkets.primary.com.ar", "remarkets"),
        ("api.bbsa.matrizoms.com.ar", "bbsa"),
        ("https://api.bbsa.matrizoms.com.ar", "bbsa"),
        ("https://api.bbsa.matrizoms.com.ar/", "bbsa"),               # trailing slash
        ("api.bbsa.matrizoms.com.ar.attacker.example", None),         # sufijo hostil
        ("https://api.bbsa.matrizoms.com.ar.attacker.example", None),
        ("https://api.bbsa.matrizoms.com.ar@attacker.example", None), # userinfo
        ("https://api.remarkets.primary.com.ar@attacker.example", None),
        ("api.primary.com.ar", None),                                 # producción
        ("https://api.primary.com.ar", None),
        ("", None),                                                   # fail-closed
        ("https://[oops/api", None),
    ],
)
def test_venue_token_resolves_by_exact_hostname(base_url: str, expected: str | None) -> None:
    """Igualdad exacta de hostname; nunca substring ni sufijo (T-39-01)."""
    assert main_matriz._venue_token(base_url) == expected
```
En el test nuevo el sujeto es `census._venue_token(base_url)` — misma tabla, otro sitio de acceso.
Los comentarios inline de cada bloque de casos (`# Sufijo hostil: un ``in`` o un ``endswith`` lo
dejarían pasar.`) son parte del patrón; conservarlos.

**Aserción AST anti-substring** (`:247-268`) — el corazón del criterio 1:
```python
def test_no_substring_membership_check_over_a_host_literal() -> None:
    """El chequeo por pertenencia de substring no puede volver al driver.

    Aserción por AST, no por ``grep``: el comentario que documenta POR QUÉ el
    chequeo viejo era inseguro cita su código, y un grep sobre el fuente no
    distingue la cita del código vivo.
    """
    offenders: list[int] = []
    for node in ast.walk(_driver_tree()):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(op, ast.In | ast.NotIn) for op in node.ops):
            continue
        left = node.left
        if isinstance(left, ast.Constant) and isinstance(left.value, str):
            offenders.append(node.lineno)
    assert not offenders, (
        f"{_DRIVER}: comparación por pertenencia de substring sobre un literal en "
        f"la(s) línea(s) {offenders}; el gate D-MATZ-33 debe usar igualdad exacta "
        f"de hostname — ``https://api.remarkets.primary.com.ar.attacker.example`` "
        f"pasaría un ``in``."
    )
```
**⚠ Divergencia obligatoria (RESEARCH Q4):** copiado tal cual sobre `literal_census_33.py` este
test da **falso positivo** en `main():355` (`if "--selftest" in argv:`). El helper `_driver_tree()`
(`:53-54`) debe reemplazarse por un walk restringido al `FunctionDef` de `census_matriz`:
```python
def _census_matriz_tree() -> ast.FunctionDef:
    tree = ast.parse(_TARGET.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "census_matriz":
            return node
    raise AssertionError("census_matriz no encontrada — el lock quedaría vacuo")
```
El `raise AssertionError` en el else es parte del patrón: el analog nunca deja que un lock se
vuelva vacuo por no encontrar su sujeto (mismo espíritu que `_MIN_PRINT_SITES = 2` en `:47`).

**Control de no-vacuidad** (`:195-197`) — el analog cierra cada capa con un control positivo:
```python
def test_env_gate_form_still_matches() -> None:
    """Control positivo: el guard no es vacuo — la forma del env-gate SÍ matchea."""
    assert _ENV_SKIP.match("SKIPPED matriz-client: missing PRIMARY_USER") is not None
```
Espejar con un control positivo propio (p.ej. que el AST walker SÍ detecta un `in` inyectado en
un snippet sintético, o que `census_matriz` fue efectivamente encontrada).

---

### `scripts/literal_census_33.py` (script/CLI, MOD)

**Analogs:** `main_matriz.py:228-247` (la política) + el propio archivo (la forma de import y el CLI)

**Import pattern** — copiar la forma exacta de la línea 72 (post-`sys.path.insert` de `:68-70`):
```python
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from verification.capture import capture  # noqa: E402
from main_matriz import _VENUE_ALLOWLIST, _venue_token  # noqa: E402   # ← NUEVO
```
`# noqa: E402` es **obligatorio**: `E402` no está en `per-file-ignores` de `pyproject.toml`.
La forma `from main_matriz import ...` (no `import main_matriz` + uso calificado) es la que
habilita el pin de identidad `is` del test.

**Gate — reemplazo del sitio stale** (`:190-201` en HEAD, la condición cambia, **la posición no**):
```python
    client = Client()
    base = client._state.base_url
    if "remarkets" not in base:                      # ← REMOVER (substring, inseguro)
        # No se imprime la URL: el criterio de no-fuga del pre-flight (nunca una
        # URL resuelta) manda acá también. La causa queda igualmente nombrada.
        _skip(
            "matriz-client",
            "base URL fuera de política (D-MATZ-33: la verificación es remarkets-only)",
        )
        with contextlib.suppress(Exception):
            client.close()
        return False
```
→ forma portada (preservando **literalmente** el comentario de no-fuga, el `_skip`, el
`contextlib.suppress(Exception)` y el `return False`):
```python
    venue = _venue_token(base)          # igualdad exacta de hostname, fail-closed
    if venue is None:
        _skip("matriz-client", "base URL fuera del allowlist D-MATZ-33 (verificación sandbox-only)")
        with contextlib.suppress(Exception):
            client.close()
        return False
```
**Invariante a preservar (Pattern 2 de RESEARCH):** el gate corre después de `Client()` (que no
hace IO) y **antes** de `login()` y de todo request. El docstring de `census_matriz` (`:176-180`)
lo declara: *"un SKIP no debe costar ni un round trip contra un host fuera de política"*. Mover el
gate es una regresión de seguridad aunque el predicado sea correcto.

**Header de censo (criterio 3 — código nuevo, sin analog exacto)** — modelar sobre la forma de
`_report`/`_skip` (`:154-167`): funciones módulo-nivel, prefijo en MAYÚSCULAS, un `print` por
línea, sin logging:
```python
def _report(pkg: str, endpoint: str, acc: dict[str, list[tuple[str, str]]]) -> None:
    """Imprime una línea por path observado: endpoint, filas, tipos y valores distintos."""
    if not acc:
        print(f"{pkg} {endpoint}: NO TARGET FIELD PRESENT IN PAYLOAD")
        return
    for path in sorted(acc):
        ...
        print(f"{pkg} {endpoint} {path}: rows={len(entries)} types={types} distinct={distinct}")


def _skip(pkg: str, reason: str) -> None:
    print(f"{pkg}: SKIPPED — {reason}")
```
El `_census_header(venue)` nuevo sigue exactamente ese molde (docstring de una línea con el
porqué, `print` con prefijo `CENSUS-HEADER` / `CENSUS-DLOCK`), y el venue sale de
`_venue_token(base)` — nunca hardcodeado.

**Uso de `capture()`** (`:212-214`, ya existente — es el patrón que `main_market_data.py` debe copiar):
```python
            raw = client._request(spec).json()
            capture("matriz", f"census-{endpoint}", raw)
            _report("matriz-client", endpoint, collect_paths(raw, _MATRIZ_KEYS))
```

**Flag CLI (si el planner elige `--matriz-only`, D-04)** — patrón existente en `main()` (`:353-362`):
```python
def main(argv: list[str]) -> int:
    """Corre el censo (o el self-test offline con ``--selftest``)."""
    if "--selftest" in argv:
        return _selftest()
    ran_matriz = census_matriz()
    ran_iol = census_iol()
    print(f"CENSUS: matriz={'RAN' if ran_matriz else 'SKIPPED'} iol={'RAN' if ran_iol else 'SKIPPED'}")
    return 0 if (ran_matriz and ran_iol) else 1
```
**Trampa:** con `--matriz-only`, `ran_iol=False` haría exit 1 en una corrida exitosa. El exit code
debe redefinirse en esa rama (retorno temprano, como hace `--selftest`).

**Extensión de `_selftest()` (criterio 3 offline)** — patrón de aserción del analog (`:339-347`):
acumular en `ok: bool`, imprimir `SELFTEST FAIL <detalle>` por cada fallo, cerrar con
`print("SELFTEST:", "PASS" if ok else "FAIL")` y `return 0 if ok else 1`. La aserción nueva del
header se agrega con esa misma forma, no con `assert`.

---

### `.github/workflows/ci.yml` (config, MOD)

**Analog:** el propio bloque `run:` (`:79-92`) — allowlist explícita de 12 rutas, mantenida a mano.
El comentario de `:70-78` explica por qué (WR-01 / HARN-VERIF-01) y **debe leerse antes de editar**.

```yaml
        run: |
          uv run pytest -q \
            verification/test_main_market_data_deep_chain.py \
            ...
            verification/test_cycle_closure_phase33.py
```
**Cambio:** agregar `\` al final de la última línea actual y una línea nueva
`            verification/test_literal_census_venue_gate.py` con la misma indentación (12 espacios).

**Verificación del patrón** — precedente verbatim en `39-01-PLAN.md:251`:
```bash
grep -c "verification/test_literal_census_venue_gate.py" .github/workflows/ci.yml
```

---

### `main_market_data.py` (driver, MOD — criterio 5 / D-07)

**Analogs:** `_write_schema_snapshot` (`:457-522`, la forma del envelope) + `literal_census_33.py:213`
(la forma de llamar a `capture`).

**Import** — `capture` NO está importado hoy. El bloque `from verification import (...)` está en
`:60-68`, top-level, sin `sys.path` hack ni `noqa` (a diferencia del script). Agregar ahí:
`from verification.capture import capture`.

**Envelope pattern** (`:472-480`) — la forma exacta a espejar en el payload de `capture()`:
```python
    actual_schema = schema_of(raw)
    schema_file = _SCHEMA_DIR / f"{client_function.replace('_', '-')}.json"
    envelope: dict[str, Any] = {
        "endpoint": endpoint,
        "client_function": client_function,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "base_url": base_url,
        "schema": actual_schema,
    }
```
`dt` ya está importado como `datetime as dt`. `schema_of(raw)` es el helper PII-free (keys+types)
— es lo único que puede ir a un artefacto **committeado**; el `raw` sólo va a `captures/`.

**Sitios de inserción** — dentro del `try`, junto al `_write_schema_snapshot` existente:
```python
        raw = _raw_via_request_sync(
            client,
            _core.build_instruments_request(
                client._state, include_expired=True, only_outright=False, offset=0
            ),
        )
        # D-09: post-procesado dentro del try.
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, Instrument, "Instrument", "sync", base_url)
        _write_schema_snapshot(
            endpoint=_ENDPOINT_TEMPLATES["get_instruments"],
            client_function="get_instruments",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
```
(`probe_instruments_sync:968-994`; el espejo de segments es `probe_segments_sync:997-1022`,
`raw` en `:1004`, snapshot en `:1010-1016`.)

**Invariante D-09 a respetar:** todo post-procesado va **dentro del `try`**, y el `except Exception`
degrada a finding (`_finding_for_exc`), nunca crashea. El `capture()` nuevo va dentro del `try`,
al lado del `_write_schema_snapshot`, no después.

---

### `main_higyrus.py` / `main_matriz.py` (drivers, MOD — rename D-06 condicional)

**Analog:** el bloque de constantes de `main_higyrus.py:239-254` es a la vez el sitio y el patrón.

```python
# Línea verbatim que el driver emite a STDOUT cuando el vendor no es alcanzable.
# Literal a propósito: ``main_verify.py`` clasifica por la forma
# ``^SKIPPED \S.*:`` (los dos puntos son load-bearing) y no interpolar el
# hostname ni la base URL es lo que evita que el veredicto filtre el dato de
# entrada (T-39-04).
_VENDOR_UNREACHABLE_SKIP_LINE = (
    "SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-33"   # ← rename
)

# Causa medida que viaja en el ``ProbeResult`` del login (no en la línea SKIPPED).
_VENDOR_UNREACHABLE_DETAIL = "vendor host unreachable (DNS)"                 # ← NO se toca

# Causa medida + destino nombrado que viaja en el sobre de evidencia de corrida
# (Phase 39 D-09). Es la línea SKIPPED sin su prefijo de veredicto: ni hostname
# ni base URL, igual que ella (T-39-04/T-39-10).
_VENDOR_UNREACHABLE_EVIDENCE = "vendor host unreachable (DNS) — LIVE-HIGY-33"  # ← rename
```
Reglas del patrón que el rename **no debe romper**: (1) literal de módulo, cero interpolación;
(2) el prefijo `SKIPPED <slug>:` con dos puntos load-bearing; (3) el destino va al final tras `— `;
(4) `_VENDOR_UNREACHABLE_DETAIL` no lleva destino y por lo tanto no se renombra.

`main_matriz.py:162-165` — mismo patrón del lado del mapa de destinos:
`_CYCLE_CLOSURE_DESTINATION = {"higyrus-client": "LIVE-HIGY-33", "matriz-client": "LIVE-MATZ-33"}`.

**Orden de operaciones (Runtime State Inventory):** renombrar la constante → correr el driver →
commitear el `run-evidence/higyrus-client.json` regenerado. Editar el JSON a mano fabricaría
evidencia.

**⚠ NO TOCAR:** `verification/test_cycle_closure_phase33.py:250-252` asevera contra
`33-CENSUS.md` en `.planning/milestones/v1.6-phases/` — historia congelada (Phase 41).

---

### Task de checkpoint (dentro del PLAN, criterio 1 / D-02)

**Analog:** `.planning/milestones/v1.7-phases/39-…/39-01-PLAN.md:87-141` — copiar la estructura completa:

```xml
<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 1: Checkpoint de seguridad — ampliación del allowlist D-MATZ-33 (D-02)</name>
  <files>(ninguno — checkpoint humano bloqueante, no escribe código)</files>
  <read_first>...</read_first>
  <action>
    Presentar al operador el alcance exacto del cambio antes de escribir una línea de código:
    ... Esperar respuesta explícita. No derivar la aprobación de la configuración de avance
    automático. Transcribir la respuesta verbatim en el SUMMARY del plan y detener el plan si
    la respuesta no es una aprobación.
  </action>
  <what-built>
    Nada todavía. Este checkpoint precede al cambio de código y es **bloqueante e
    incolapsable**: `mode: yolo` y `auto_advance: true` están activos en
    `.planning/config.json` y NO aplican acá ...
  </what-built>
  <how-to-verify>1..5 (incluye el riesgo residual A1 declarado)</how-to-verify>
  <resume-signal>Escribir "approved" para habilitar el cambio de allowlist, o describir objeciones</resume-signal>
  <verify><automated>test -f ... &amp;&amp; grep -q "bbsa.matrizoms.com.ar" ...</automated></verify>
  <acceptance_criteria>
    - El operador responde explícitamente en esta sesión; la aprobación NO se deriva de
      `auto_advance` ni del `mode: yolo`.
    - La respuesta queda transcrita verbatim en el SUMMARY del plan.
  </acceptance_criteria>
  <done>Aprobación humana explícita registrada, o el plan se detiene acá.</done>
</task>
```
**Los atributos son load-bearing:** `type="checkpoint:human-verify"` + `gate="blocking-human"`.
`gate="blocking"` a secas ya se auto-aprobó dos veces bajo yolo en este proyecto.
Diferencia de encuadre para la Phase 42 (D-02 de CONTEXT): el checkpoint es **confirmación de
fidelidad del port**, no re-autorización de bbsa desde cero.

---

## Shared Patterns

### 1. Estilo de módulo (aplica a TODO archivo Python tocado o creado)
**Source:** uniforme en el repo — `verification/test_main_matriz_skip_line_shape.py:26`,
`scripts/literal_census_33.py`, `main_*.py`
```python
"""Docstring de módulo: qué lock/driver es, por qué existe, qué NO toca."""

from __future__ import annotations
```
`from __future__ import annotations` es mandatorio y uniforme. Ruff: line-length 100, comillas
dobles, 4 espacios. `E501` ignorado globalmente; `E402` **no** — `# noqa: E402` explícito para
imports post-`sys.path`.

### 2. No-fuga de hostname / base URL en veredictos (T-39-04, C-4)
**Source:** `main_higyrus.py:239-254`, `scripts/literal_census_33.py:193-198`
**Apply to:** todo `print`/`_skip`/constante de veredicto de esta fase.
Las líneas de veredicto son **literales de módulo sin interpolación**. La causa se nombra; el dato
de entrada nunca. El comentario que explica el porqué viaja pegado a la constante.

### 3. Fail-closed por igualdad exacta de hostname
**Source:** `main_matriz.py:228-247` (`_venue_token`)
**Apply to:** `scripts/literal_census_33.py` (importado, no re-declarado)
Maneja ya: sin esquema (re-parseo `//{base_url}`), userinfo, trailing slash, `ValueError` → `None`,
`host is None` → `None`, host no listado → `None`. **No hand-rollear ningún `endswith`/`in`/regex.**

### 4. Cleanup del cliente en toda rama de salida
**Source:** `scripts/literal_census_33.py:199-201` y `:230-232`
```python
        with contextlib.suppress(Exception):
            client.close()
```
Presente tanto en la rama de skip como en el `finally`. El port debe conservar ambas.

### 5. Control de no-vacuidad en cada guard
**Source:** `test_main_matriz_skip_line_shape.py:47` (`_MIN_PRINT_SITES = 2`), `:195-197`
(control positivo del clasificador), `literal_census_33.py:315-321` (`_selftest`)
**Apply to:** el test nuevo y la extensión del selftest.
Todo lock nuevo lleva una aserción que falla si el lock dejó de tener sujeto. Un verde no puede
significar "no inspeccioné nada".

### 6. Aserción por AST, nunca por grep, sobre fuente Python
**Source:** `test_main_matriz_skip_line_shape.py:53-54` y `:247-268`
**Apply to:** el test anti-substring del criterio 1.
Razón: los comentarios/docstrings citan el código viejo inseguro; un grep no distingue la cita del
código vivo. (`literal_census_33.py:38-44` menciona "remarkets-only" en prosa.)

### 7. Envelope timestampeado para artefactos de evidencia
**Source:** `main_market_data.py:474-480`, `verification/run_evidence.py:125-134`
```python
{"endpoint": ..., "client_function": ..., "captured_at": dt.datetime.now(dt.UTC).isoformat(),
 "base_url": ..., "schema": schema_of(raw)}
```
**Apply to:** el payload de `capture()` en `main_market_data.py` (D-08) y a `42-WIRE-READ.md`.
`captured_at` UTC ISO siempre; payload crudo **sólo** a `captures/` (gitignored); a git sólo
`schema_of()` (keys+types, PII-free por construcción).

### 8. Enrolamiento manual en CI para todo test bajo `verification/`
**Source:** `.github/workflows/ci.yml:70-92`
**Apply to:** `verification/test_literal_census_venue_gate.py`.
`testpaths` local ≠ allowlist de CI. Sin la línea, el test es INERTE (WR-01).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `42-WIRE-READ.md` (artefacto committeado del criterio 5) | doc | batch | No existe hoy ningún markdown committeado que reporte una lectura fresca de wire con `captured_at` + marca de baseline no-autoritativo. **Lo más cercano** es el envelope JSON de `_write_schema_snapshot` (`main_market_data.py:474-480`) — usar su forma de campos (`endpoint`, `client_function`, `captured_at`, `base_url`, `schema`) como esqueleto de las secciones del documento. `main_market_data.py` tampoco escribe `write_run_evidence`, así que no hay analog del lado del harness. |

Parcial: `42-CENSUS.md` tiene analog de forma en `.planning/milestones/v1.6-phases/33-…/33-CENSUS.md`,
pero ese archivo es **historia congelada** — se copia su forma, jamás se edita (romperia el guard
de `test_cycle_closure_phase33.py:250`).

---

## Metadata

**Analog search scope:** `main_*.py` (raíz), `scripts/`, `verification/`, `.github/workflows/`,
`.planning/milestones/v1.7-phases/39-*/`
**Files read this session:** `verification/test_main_matriz_skip_line_shape.py` (:1-60, :195-269),
`scripts/literal_census_33.py` (:60-239, :300-366), `main_market_data.py` (:455-524, :965-1023),
`main_higyrus.py` (:236-257), `.github/workflows/ci.yml` (:70-95), `39-01-PLAN.md` (:85-144)
**Pattern extraction date:** 2026-08-31
