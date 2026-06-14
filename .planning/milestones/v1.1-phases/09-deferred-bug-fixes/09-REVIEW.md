---
phase: 09-deferred-bug-fixes
reviewed: 2026-06-13T19:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - main_higyrus.py
  - packages/higyrus-client/src/higyrus_client/_state.py
  - packages/iol-client/src/iol_client/_state.py
  - packages/matriz-client/src/matriz_client/_core.py
  - packages/higyrus-client/tests/test_multi_account.py
  - packages/iol-client/tests/test_refresh_token_lifecycle.py
  - packages/iol-client/tests/test_refresh_token_lifecycle_async.py
  - packages/matriz-client/tests/test_core.py
  - packages/matriz-client/tests/test_client.py
findings:
  critical: 0
  blocker: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-06-13T19:00:00Z
**Depth:** standard (per-file analysis con checks Python 3.12+)
**Files Reviewed:** 9 (4 source + 5 test/driver)
**Status:** issues_found (4 Warning + 6 Info; 0 Blocker)

## Summary

Revisión adversarial del trabajo de Phase 9 (deferred bug fixes BUG-01..04 + cross-package `_state.account_id` cleanup). Los cambios son **conservadores y bien aislados**: la fix BUG-01 vive en un único builder (`_core.build_get_instruments_by_cfi_request`), BUG-03 son solo tests sin tocar `src/`, BUG-04 agrega 1 test + 1 probe + cleanup cross-package del campo `_state.account_id` no usado, y la migración del driver al patrón `_get_default()._state.base_url` es mecánica.

**No se detectaron BLOCKERs** (lógica, seguridad, o riesgo de pérdida de datos). El guard hybrid Literal+regex de matriz BUG-01 es correcto en su intención y los tests parametricos cubren los 3 buckets esperados.

**Hallazgos relevantes:**
- **WR-01 (matriz CFI guard):** `re.match(r"^[A-Z]{6}$", s)` acepta `"ESXXXX\n"` (regex `$` matchea antes de `\n` final). Cualquier caller que pase un string con whitespace final bypassa el guard.
- **WR-02 (matriz CFI guard):** Si un caller hace `cast(CFICode, None)` (o pasa cualquier non-str via bypass de tipos), `_CFI_ISO_RE.match(None)` levanta `TypeError`, NO el `PrimaryAPIError` documentado en el contrato. El test parametrico no cubre este caso.
- **WR-03 (main_higyrus.py docstring):** El docstring del módulo enumera 18 probes pero ahora hay 19 (multi_account_iteration agregado en Phase 9). `HIGYRUS_SAMPLE_CUENTAS` tampoco aparece en la sección "Variables de entorno". Drift docs vs código.
- **WR-04 (iol-client _state.py docstring):** El docstring sigue diciendo que `refresh_token` "is forward-declared for schema consistency across packages (RESEARCH.md Per-Package Divergence Matrix). Phase 6 `Client.__init__` does NOT accept it as a kwarg (D-13)." pero el `configure()` SÍ lo acepta como kwarg desde Phase 6 / D-IOL-10 (verificable en `client.py:438`, `aio.py:425`). El docstring está parcialmente desactualizado.

El resto son Info: orden estético de exports, comments duplicados, imports locales en función, regex pattern no usa `re.fullmatch`/`\Z` consistentemente, etc.

## Warnings

### WR-01: CFI regex `$` anchor acepta trailing newline en input

**File:** `packages/matriz-client/src/matriz_client/_core.py:79`
**Issue:** El regex `_CFI_ISO_RE = re.compile(r"^[A-Z]{6}$")` usado con `_CFI_ISO_RE.match(cfi_code)` acepta input con `\n` final, porque en Python `re` el `$` matchea EITHER end-of-string OR before-trailing-`\n` por default (sin `re.MULTILINE`). Test reproducible:

```python
>>> import re
>>> r = re.compile(r"^[A-Z]{6}$")
>>> bool(r.match("ESXXXX\n"))
True
```

Esto significa que un operator-supplied CFI con whitespace residual (e.g. desde una CSV mal trimmed, o desde un copy-paste en un notebook) bypassa el guard y emite la request al wire con `CFICode=ESXXXX%0A`. La fix Phase 9 BUG-01 pretende cerrar exactamente el caso "client propaga CFI malformado al wire sin levantar excepción" — este edge case no está cubierto.

El test parametrico `test_get_instruments_by_cfi_validates_cfi_code` no incluye un caso con trailing newline/space.

**Fix:** Usar `re.fullmatch` (semánticamente más claro) o reemplazar `$` por `\Z` (matchea solo end-of-string, NUNCA antes de `\n`):

```python
# Opción A: re.fullmatch (recomendado — explicit intent)
_CFI_ISO_RE = re.compile(r"[A-Z]{6}")  # sin anchors, fullmatch los implica
# ...
if cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.fullmatch(cfi_code):

# Opción B: \Z anchor
_CFI_ISO_RE = re.compile(r"\A[A-Z]{6}\Z")
```

Agregar test case en `test_core.py::test_get_instruments_by_cfi_validates_cfi_code`:

```python
("ESXXXX\n", True),  # trailing newline rejected
("ESXXXX ", True),    # trailing space rejected
(" ESXXXX", True),    # leading space rejected
```

---

### WR-02: CFI guard `re.match(None)` levanta `TypeError`, no `PrimaryAPIError`

**File:** `packages/matriz-client/src/matriz_client/_core.py:462`
**Issue:** La línea:

```python
if cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.match(cfi_code):
```

Si un caller hace `cast(CFICode, None)` (el mismo bypass mecanism que el guard pretende cubrir, según docstring del propio builder), entonces:
- `None not in _CFI_LITERAL_VALUES` → `True` (short-circuit no se aplica porque `not in` no es `not (… in)` con None; corregimos: `None not in frozenset[str]` es `True`)
- `_CFI_ISO_RE.match(None)` → `TypeError: expected string or bytes-like object`

El test paramétrico cubre `""` (empty) pero no `None`, ni int (`123`), ni list. El contrato observable (docstring `raise PrimaryAPIError(status="ERROR")`) NO se cumple para esos inputs — el caller ve un `TypeError` opaco fuera de la jerarquía de excepciones del paquete.

Reproducer (mypy strict NO captura este path porque `cast(CFICode, None)` evade type-checks):

```python
from typing import cast
from matriz_client.types import CFICode
from matriz_client._core import build_get_instruments_by_cfi_request
from matriz_client._state import _ClientState
build_get_instruments_by_cfi_request(_ClientState(), cast(CFICode, None))
# TypeError: expected string or bytes-like object
```

**Fix:** Agregar guard de tipo antes del check de regex:

```python
if not isinstance(cfi_code, str) or (
    cfi_code not in _CFI_LITERAL_VALUES and not _CFI_ISO_RE.match(cfi_code)
):
    raise PrimaryAPIError(
        status="ERROR",
        description=(
            f"CFI inválido: {cfi_code!r} "
            "(no es str, o no está en CFICode Literal, ni matchea ^[A-Z]{6}$)"
        ),
        message=None,
    )
```

Y extender el test parametrico:

```python
@pytest.mark.parametrize(
    ("cfi", "expect_raise"),
    [
        # ... casos existentes ...
        (None, True),      # type: ignore[list-item]
        (123, True),       # type: ignore[list-item]
        ([], True),        # type: ignore[list-item]
    ],
)
```

---

### WR-03: `main_higyrus.py` docstring desactualizado vs código (probe 19 missing)

**File:** `main_higyrus.py:9-30, 36-45`
**Issue:** El docstring del módulo:

1. Enumera **18 probes** (líneas 13-30) numerados 1-18. Phase 9 agregó `probe_multi_account_iteration` como probe 19 (registrado en `_D_HIGY_10_ORDER` línea 168). La lista del docstring no fue actualizada — para alguien leyendo el módulo cold, el código declara 19 probes pero el contrato documental dice 18.
2. La sección "Variables de entorno" (líneas 36-45) lista `HIGYRUS_SAMPLE_CUENTA` (singular), pero NO menciona el nuevo `HIGYRUS_SAMPLE_CUENTAS` (plural, CSV) introducido por Plan 09-02 Task 2. El probe lo lee como override-source #1; sin el docstring un operator no sabe que existe.

**Fix:**

```rst
17. ``probe_errors_envelope_async``            — espejo async (HIGY-05).
18. ``probe_multi_account_iteration``          — Phase 9 BUG-04, CSV ``HIGYRUS_SAMPLE_CUENTAS`` o live fallback.
19. ``probe_auth_401``                         — opt-in vía ``VERIFY_HIGYRUS_BAD_CREDS=1`` (HIGY-AUTH, D-HIGY-10 #18).
```

Y agregar a env vars:

```rst
- ``HIGYRUS_SAMPLE_CUENTAS`` (opcional; CSV ``"A,B"`` para multi_account_iteration probe; Phase 9 BUG-04).
```

---

### WR-04: `iol-client _state.py` docstring desactualizado sobre `refresh_token` kwarg en `configure()`

**File:** `packages/iol-client/src/iol_client/_state.py:25-30`
**Issue:** El docstring dice:

> The ``refresh_token`` field is forward-declared for schema consistency
> across packages (RESEARCH.md Per-Package Divergence Matrix). Phase 6
> ``Client.__init__`` does NOT accept it as a kwarg (D-13).
> ``refresh_token`` is mutated by ``Client.login()`` / ``_refresh()``
> internally.

Esto era cierto en Phase 6, pero Phase 6 D-IOL-10 / Phase 8 ya agregaron `refresh_token` como kwarg de `configure()` (verificar `client.py:438` y `aio.py:425`):

```python
def configure(
    ...
    refresh_token: str | None = None,
    ...
)
```

El docstring queda misleading: implica que solo `login()`/`_refresh()` lo mutan internamente, pero callers pueden inyectarlo via `configure(refresh_token=...)` también (lo cual los tests de `test_refresh_token_lifecycle.py` Phase 9 podrían incluso haber usado pero eligen direct-state-write).

**Fix:** Actualizar el docstring:

```python
"""
The ``refresh_token`` field is set/cleared by:

1. ``Client.login()`` / ``Client._refresh()`` internally (con CR-01
   conditional rotation guard — preserva el cacheado si el server omite).
2. ``configure(refresh_token=...)`` como kwarg público (Phase 6 D-IOL-10
   carry-forward; Phase 8 lo agregó al ``Client.__init__`` formal).

NOTE: ``Client.__init__`` SÍ acepta ``refresh_token`` desde Phase 8 — el
D-13 forward-decl ya no aplica.
"""
```

(Verificar también si `Client.__init__` realmente lo acepta — si no, ajustar la nota.)

## Info

### IN-01: Regex inválido podría usarse en otros campos en el futuro

**File:** `packages/matriz-client/src/matriz_client/_core.py:79`
**Issue:** El pattern `^[A-Z]{6}$` está bien para CFI ISO 10962 hoy, pero el comentario justificándolo (`# Pattern S5: compile-once regex + frozenset...`) no explica POR QUÉ es exactamente 6 mayúsculas. Si en el futuro alguien lee este código sin contexto y agrega un nuevo CFI con guion (e.g. `"DBXXFR"` ya está en el Literal, pero un hipotético `"AB-CFR"` no matchearía), debería entender que `_CFI_LITERAL_VALUES` es el escape hatch.

**Fix:** Comentario más educativo:

```python
# CFI ISO 10962: exactamente 6 caracteres alfanuméricos en mayúscula (sin
# guiones, sin lowercase, sin dígitos). Si el estándar agrega nuevos códigos
# que NO encajan en este pattern, agregarlos al Literal CFICode y _CFI_LITERAL_VALUES
# los absorbe (escape hatch para outliers).
_CFI_ISO_RE = re.compile(r"\A[A-Z]{6}\Z")
```

---

### IN-02: Import local de `cast` + `CFICode` dentro del test function

**File:** `packages/matriz-client/tests/test_client.py:791-793`
**Issue:** El test `test_get_instruments_by_cfi_raises_primary_api_error_on_malformed_cfi` importa:

```python
from typing import cast
from matriz_client.types import CFICode
```

dentro del cuerpo de la función. Otros tests en el archivo importan al top-level. Inconsistencia estilística con el resto del codebase (PEP 8 prefiere imports top-level).

**Fix:** Mover ambos imports a la top de `test_client.py`:

```python
from typing import cast

# ... otros imports ...
from matriz_client.types import CFICode
```

Si el comentario del executor era evitar circular-import o keep-local-scope, documentarlo explicitamente en una nota al lado del import.

---

### IN-03: Test parametric label "literal-known x2" pero hay 9 valores en CFICode Literal

**File:** `packages/matriz-client/tests/test_core.py:351-353`
**Issue:** El comentario del bucket "literal-known" en el parametric dice:

```python
# Literal-known bucket (2 valores del Literal CFICode declarado en
# matriz_client.types.CFICode — source of truth para `_CFI_LITERAL_VALUES`).
("ESXXXX", False),
("DBXXXX", False),
```

El Literal `CFICode` tiene 9 valores (`ESXXXX`, `DBXXXX`, `OCASPS`, `OPASPS`, `FXXXSX`, `OPAFXS`, `OCAFXS`, `EMXXXX`, `DBXXFR`). El test cubre solo 2 de los 9 (parametric con 22% del Literal). Tests adicionales no romperán nada y aumentan confianza. Tipico tradeoff entre cobertura y velocidad — actualmente no es un BLOCKER, pero un test parametric debería al menos enumerar los outliers como `OCASPS`, `FXXXSX` que tienen patrones distintos.

**Fix:** Ampliar a los 9 valores con un single `pytest.param(literal_value, False, id=literal_value)`:

```python
*[
    pytest.param(v, False, id=f"literal-{v}")
    for v in ["ESXXXX", "DBXXXX", "OCASPS", "OPASPS", "FXXXSX",
              "OPAFXS", "OCAFXS", "EMXXXX", "DBXXFR"]
],
```

O al menos documentar en el comment que el bucket es una **sample**, no exhaustive.

---

### IN-04: Comentario `D-09 cross-package: account_id removed` duplicado en 2 archivos sin cross-ref

**File:** `packages/higyrus-client/src/higyrus_client/_state.py`, `packages/iol-client/src/iol_client/_state.py`
**Issue:** El field `account_id` fue removido de AMBOS `_state.py`. Pero NO hay comentario o changelog entry indicando que el field existió y fue eliminado en Phase 9 BUG-04 D-09. Si alguien hace `git blame` sobre el archivo en 6 meses, debe ir a buscar el commit `4f0d686` para entender por qué. Podría dejarse un breadcrumb.

**Fix:** Opcional — agregar al docstring de cada `_state.py`:

```python
"""...

History:
    - Phase 9 BUG-04 / D-09: ``account_id`` field removed (unused at runtime;
      per-call ``id_cuenta`` kwarg is the canonical multi-account pattern).
      See commit 4f0d686.
"""
```

(Ojo: si la convención del proyecto evita historial inline en docstrings, ignore.)

---

### IN-05: Test no resetea `state.refresh_token` cuando el conftest no lo limpia explícitamente

**File:** `packages/iol-client/tests/test_refresh_token_lifecycle.py:213-218` (comment block)
**Issue:** El comment final reconoce el riesgo de cross-test contamination de `state.refresh_token`:

> Pitfall 6 note: si tests pasan en isolation pero fallan en suite, podría
> ser contaminación cross-test de ``state.refresh_token`` (autouse fixture en
> conftest.py:25-38 cierra el http_client pero NO resetea explícitamente el
> state.refresh_token; sin embargo, cada test acá lo setea explícitamente al
> inicio, así que el riesgo está mitigado). NO modificar conftest.py en este
> plan (modificación cross-cutting) — defer si emerge.

El analysis es correcto: el conftest hace `configure(base_url="https://api.test", username="", password="")` en teardown; `password=""` (NOT None) hits `if password is not None:` y SÍ limpia `state.refresh_token = None` (`client.py:476`). Así que el riesgo ESTÁ mitigado por la conftest. El comentario es overly cauteloso — podría aclararse.

**Fix:** Refinar el comment para reflejar lo que efectivamente pasa:

```python
# Cross-test isolation: el autouse conftest fixture llama
# ``configure(base_url=..., username="", password="")`` en teardown; el
# branch ``if password is not None:`` (client.py:472) resetea
# state.refresh_token=None además del token. Por eso cada test entra con
# state.refresh_token=None garantizado, y el seed explícito al inicio es
# defensa-en-profundidad, no estrictamente necesario.
```

---

### IN-06: Probe `probe_multi_account_iteration` no captura `HigyrusAuthError` separadamente

**File:** `main_higyrus.py:2108-2126`
**Issue:** El probe captura solo `HigyrusAPIError`:

```python
except HigyrusAPIError as exc:
    fid = _next_fid()
    append_finding(
        ...
        class_="ERROR-MAP",
        ...
    )
```

Pero NO captura `HigyrusAuthError` separadamente (es subclass de `HigyrusAPIError`, así que cae acá — class="ERROR-MAP", lo cual es semánticamente incorrecto para un 401). Los otros probes del mismo driver (e.g. `probe_get_movimientos_sync` líneas 944-957) tienen un `except HigyrusAuthError` específico con `class_="AUTH"`. Por consistencia con el resto del driver, el probe debería distinguir.

Adicionalmente, NO hay `except Exception` para errores de transporte/network (otros probes sí lo tienen). Si Connection refuses o timeout sucede entre iteraciones, el probe propaga la excepción out, abortando el resto del driver.

**Fix:** Agregar los dos handlers para paridad con el patrón establecido del driver:

```python
except HigyrusAuthError as exc:
    fid = _next_fid()
    append_finding(_PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
                   title=f"multi_account: AuthError en get_movimientos({acct})",
                   expected="200 OK con token Bearer", actual=repr(exc),
                   diff=f"status={exc.status_code!r}", base_url=base_url)
    return ProbeResult("multi_account_iteration", "FINDING", f"{fid} (OPEN)")
except HigyrusAPIError as exc:
    # ... existing ...
except Exception as exc:
    fid = _next_fid()
    append_finding(_PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                   title=f"multi_account: unexpected {type(exc).__name__} en get_movimientos({acct})",
                   expected="200 OK", actual=repr(exc),
                   diff=f"type={type(exc).__name__}", base_url=base_url)
    return ProbeResult("multi_account_iteration", "FINDING", f"{fid} (OPEN)")
```

---

## Cross-Cutting Observations (informativos, no findings)

- **Adversarial check de "Phase 6 migration drift":** El SUMMARY 09-02 menciona que `main_higyrus.py` tenía 21 sites legacy de `._base_url` / `aio._ensure_http_client()` que se migraron a `_get_default()._state.base_url` / `_get_default()._ensure_http_client()`. Verifiqué con `grep`: hay aproximadamente 19 references al patrón `_get_default()._state.base_url` o `_get_default()._ensure_http_client()` en `main_higyrus.py`, consistentes con la migración. Cero references a `aio._base_url` o `higyrus_client.client._base_url`. Migración aplicada correctamente.

- **Adversarial check de "shim still exposes `_token` y `_client`":** Las references restantes `higyrus_client.client._token` (línea 2300), `aio._token` (línea 2195), `higyrus_client.client._client` (línea 241), `aio._client` (línea 294-295) NO son legacy drift — son legítimas porque el shim `_FORWARDED_TO_STATE` en `client.py:583-586` y `aio.py:606-612` EXPONE estos atributos (token y http_client) explícitamente como API operacional para drivers/tests. NO son los attrs prohibidos (`_base_url`, `_user`, `_password`, `_client_id`) que el shim documenta como `AttributeError`-must-raise.

- **CR-01 conditional rotation correctness:** Verifiqué `client.py:260` y `aio.py:250` — el guard `if refresh is not None:` está intacto, y los tests Phase 9 (paths 3 y 4) lo lockean bidireccionalmente. La lógica es: parser retorna `None` si server omite/no-string/empty → guard no se ejecuta → cached preserved.

- **Cross-pkg D-09 cleanup verificado:** `grep -c "account_id" packages/{higyrus,iol}-client/src/*/_state.py` retorna 0 en ambos. `RequestSpec.account_id` (Phase 8 D-11) en `_core.py` está intacto en matriz (separate concern). Limpieza correcta.

- **PEP 8 / Style consistency:** Todos los archivos tienen `from __future__ import annotations` como primera import. No detecté wildcard imports ni relativos en los archivos revisados.

- **Tests `match_content=b"..."` pattern (BUG-03):** Los 8 tests (4 sync + 4 async) usan `match_content` para distinguir refresh vs password grant en el mismo URL. El orden de los kwargs en `_core.build_login_request` / `build_refresh_request` produce bytes determinísticos (Python 3.7+ dict-order preserva). Pattern correcto.

---

_Reviewed: 2026-06-13T19:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
