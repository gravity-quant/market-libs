---
phase: 01-safety-harness-verification-infrastructure
reviewed: 2026-05-28T00:12:15Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - conftest.py
  - main_higyrus.py
  - main_iol.py
  - main_matriz.py
  - main_verify.py
  - main_wallets.py
  - packages/ambito-financiero-client/tests/test_harness_anonymize.py
  - packages/ambito-financiero-client/tests/test_harness_env_gate.py
  - packages/ambito-financiero-client/tests/test_harness_live_probe.py
  - packages/ambito-financiero-client/tests/test_harness_mutation_gate.py
  - packages/ambito-financiero-client/tests/test_harness_redaction.py
  - packages/ambito-financiero-client/tests/test_harness_schema.py
  - pyproject.toml
  - verification/__init__.py
  - verification/anonymize.py
  - verification/capture.py
  - verification/env_gate.py
  - verification/findings.py
  - verification/mutation_gate.py
  - verification/redaction.py
  - verification/schema.py
findings:
  critical: 2
  warning: 5
  info: 4
  total: 11
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-28T00:12:15Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Se revisó el harness de verificación en vivo (`verification/`), los drivers `main_*.py`, el `conftest.py` raíz, la configuración del workspace y los tests del harness. La arquitectura general es sólida y la mayoría de las garantías de seguridad están bien implementadas: `redact`/`safe_print` cubren el guard de secreto vacío/corto (Pitfall 3), `require_env` no lanza ni sale, `capture` aterriza sólo en el staging gitignored, y la lectura en vivo del `_base_url` para el mutation gate es correcta.

Sin embargo, dos garantías de seguridad-críticas del enunciado fallan en casos límite reales:

1. **La anonimización de PII (HARN-06/D-10) deja pasar PII verbatim** cuando una clave del denylist contiene un `dict` o `list` como valor — `_synthetic` cae al `return value` final y devuelve el contenedor sin tocar. La promesa "sólo las claves denylisted reciben un sintético" se rompe para PII anidada.

2. **El mutation gate (HARN-02/D-16) es bypasseable por substring**: `"remarkets" not in base` permite mutar contra cualquier URL que contenga la cadena en host, path o query, lo que debilita el fail-closed para operaciones destructivas.

Además, un bug de correctitud notable: el runner agregado **clasifica erróneamente como SKIPPED** una corrida matriz exitosa, porque la línea `SKIPPED (mutating, guard off)` del mutation gate colisiona con el prefijo `SKIPPED ` que usa el clasificador.

## Critical Issues

### CR-01: `anonymize` deja pasar PII verbatim cuando la clave denylisted tiene valor dict/list

**File:** `verification/anonymize.py:60`, `verification/anonymize.py:69-81`
**Issue:** En `anonymize`, cuando una clave está en `deny.keys` el valor se reemplaza por `_synthetic(k, v)` y **no se recurre**. Pero `_synthetic` sólo sanea escalares (`str`/`int`/`float`/`bool`); para cualquier otro tipo cae al `return value` final y devuelve el valor **sin modificar**. Si una clave PII contiene un sub-objeto o lista con PII anidada, esa PII se filtra verbatim al fixture supuestamente anonimizado. Ejemplo verificado:

```python
deny = Denylist("higyrus", frozenset({"titular"}))
anonymize({"titular": {"nombre": "Juan Perez", "dni": "12345"}}, deny)
# -> {"titular": {"nombre": "Juan Perez", "dni": "12345"}}   # PII INTACTA
```

Esto rompe la garantía central de HARN-06/D-10 ("sólo las claves denylisted reciben un sintético" y "el fixture anonimizado nunca debe contener PII real"). El pipeline de dos fases confía en esta etapa antes de la revisión humana, y un objeto/lista bajo una clave PII se considera anonimizado cuando no lo está. El test `test_synthetic_preserves_scalar_types` sólo cubre escalares, así que el bug no está cubierto.
**Fix:** Cuando una clave está denylisted y no hay reemplazo explícito, si el valor es contenedor hay que decidir explícitamente: o bien anonimizar el contenedor completo (recursión "todo PII"), o bien escalar/redactar. Lo más seguro es no permitir que un contenedor sobreviva intacto bajo una clave PII:

```python
def anonymize(payload: Any, deny: Denylist) -> Any:
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for k, v in payload.items():
            if k in deny.keys:
                if k in deny.replacements:
                    out[k] = deny.replacements[k]
                elif isinstance(v, (dict, list)):
                    # Contenedor bajo clave PII: anonimizar TODO recursivamente,
                    # no devolverlo verbatim.
                    out[k] = _scrub_container(v)
                else:
                    out[k] = _synthetic(k, v)
            else:
                out[k] = anonymize(v, deny)
        return out
    if isinstance(payload, list):
        return [anonymize(x, deny) for x in payload]
    return payload
```

Como mínimo, `_synthetic` debe garantizar que NUNCA devuelve un contenedor con PII original (p.ej. recursión sobre dict/list saneando todas las hojas).

### CR-02: El mutation gate es bypasseable por coincidencia de substring `remarkets`

**File:** `verification/mutation_gate.py:48-52`
**Issue:** El doble gate decide el sandbox con `if "remarkets" not in base`. Es un chequeo de substring sobre la URL completa (esquema + host + path + query), no sobre el host. Cualquier URL que contenga `remarkets` en cualquier posición habilita la rama mutante con `VERIFY_MUTATING=1`. Casos verificados que pasan el gate indebidamente:

```text
https://remarkets.attacker.example          -> ALLOW
https://api.primary.com.ar/?x=remarkets      -> ALLOW
https://api-remarkets-mirror-prod.example    -> ALLOW
```

Dado que el gate protege operaciones destructivas (alta/cancelación de órdenes) y la base URL se lee de `PRIMARY_BASE_URL` (env, controlable), un valor mal configurado o adversarial que contenga la cadena habilita mutaciones contra un endpoint no-sandbox. Esto contradice el espíritu fail-closed/default-deny de D-16 (Pitfall 5).
**Fix:** Validar el host exacto del sandbox, no un substring de la URL completa:

```python
from urllib.parse import urlsplit

_SANDBOX_HOST = "api.remarkets.primary.com.ar"

base = matriz_client.client._base_url
host = urlsplit(base).hostname or ""
if host != _SANDBOX_HOST:
    print("SKIPPED (mutating, guard off)")  # URL no-sandbox -> nunca mutar
    return False
return True
```

Si se quiere admitir variantes de host de remarkets, usar un allowlist explícito de hostnames y comparar contra `host`, nunca contra la cadena completa.

## Warnings

### WR-01: El runner clasifica como SKIPPED una corrida matriz exitosa (colisión de prefijo `SKIPPED `)

**File:** `main_verify.py:58-61`, `verification/mutation_gate.py:39,50`, `main_matriz.py:49`
**Issue:** `_run_driver` clasifica como `SKIPPED` si **cualquier** línea del stdout del hijo empieza con `"SKIPPED "`. El mutation gate imprime `SKIPPED (mutating, guard off)` en la operación normal (guard apagado por defecto), y `main_matriz.py` invoca `mutating_allowed()` en toda corrida tras haber ejercitado con éxito `get_segments()` y `get_all_instruments()`. Resultado: una corrida matriz que efectivamente RAN se reporta como `SKIPPED` en el resumen agregado, falseando el conteo RAN/SKIPPED (HARN-01/D-14). Verificado: la línea `SKIPPED (mutating, guard off)` dispara la rama SKIPPED.
**Fix:** Detectar sólo la línea del env-gate, que tiene forma `SKIPPED <pkg>: ...` (con dos puntos), no el prefijo genérico:

```python
import re
_ENV_SKIP = re.compile(r"^SKIPPED \S.*:")  # "SKIPPED <pkg>: missing ..."
for line in result.stdout.splitlines():
    if _ENV_SKIP.match(line):
        return "SKIPPED"
return "RAN"
```

Alternativamente, usar un marcador inequívoco distinto entre el env-gate y el mutation gate.

### WR-02: El runner enmascara fallos del driver como RAN (no distingue éxito de crash)

**File:** `main_verify.py:36-61`
**Issue:** `_run_driver` usa `check=False` y nunca inspecciona `result.returncode`. Un driver que crashea (traceback, excepción no atrapada, exit != 0) se clasifica igual que uno exitoso: `RAN`. El docstring lo declara intencional ("aunque haya errores de API en vivo"), pero un crash duro (p.ej. `ImportError`, error de auth no manejado) queda indistinguible de una corrida sana, lo que vacía de valor el resumen agregado: el operador no se entera de que un paquete falló. Esto degrada la observabilidad del harness (HARN-01).
**Fix:** Introducir un tercer estado `FAILED` cuando `returncode != 0` y no hubo SKIPPED de credenciales, manteniendo el "nunca se detiene":

```python
if any(_ENV_SKIP.match(l) for l in result.stdout.splitlines()):
    return "SKIPPED"
if result.returncode != 0:
    return "FAILED"
return "RAN"
```

### WR-03: `main_wallets.py` imprime `resp.text` crudo de `/health`, posible reflejo de credencial fuera del filtro `>= 4`

**File:** `main_wallets.py:36-39`, `verification/redaction.py:30-40`
**Issue:** El driver imprime `resp.text[:200]` vía `safe_print(..., secrets)`, pero `secrets` sólo incluye `WALLETS_TOKEN` si `len >= 4` (filtro en `main_wallets.py:27`), y `safe_print` también descarta secretos de `< 4` chars (`redaction.py:36`). Un token Bearer corto (configuración degenerada o de prueba) no se enmascararía si el endpoint lo reflejara. Además, sólo se redacta el token; si el servicio reflejara otra credencial derivada (p.ej. un header eco), no está en la lista. El riesgo es acotado (tokens reales son largos), de ahí WARNING, no BLOCKER.
**Fix:** Documentar/asegurar el invariante de que los tokens reales son largos, o redactar también valores sospechosos por patrón (p.ej. `Bearer\s+\S+`) además de la lista exacta de secretos, para no depender únicamente del umbral de longitud.

### WR-04: Tests del harness acoplados a `packages/ambito-financiero-client/tests/` importan `matriz_client`

**File:** `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py:19`
**Issue:** Los tests genéricos del harness viven bajo el árbol de tests de un único paquete (`ambito-financiero-client`) e importan `matriz_client`. En CI funciona porque `uv sync --all-packages` instala todo antes de `pytest packages/ambito-financiero-client`. Pero el acoplamiento es frágil: ejecutar `pytest packages/ambito-financiero-client` en un entorno donde sólo está instalado ese paquete (lo que el comentario del módulo `test_harness_schema.py:9-11` sugiere como modelo mental) rompe la colección con `ModuleNotFoundError: matriz_client`. Además, estos tests sólo corren en el job de matriz... no: corren sólo en el job de **ambito**, y nunca en los otros cuatro, lo que es un emplazamiento poco evidente para tests transversales del harness.
**Fix:** Mover los tests del harness a una ubicación neutral colectada por `testpaths` (p.ej. `tests/harness/` en la raíz, agregándola a `testpaths`), o documentar explícitamente la dependencia de workspace-sync en el módulo. Si deben quedar bajo un paquete, elegir `matriz-client` (el dueño de la dependencia) en lugar de `ambito`.

### WR-05: `monkeypatch.setattr(..., raising=False)` oculta renombres de `_base_url`

**File:** `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py:30-35,49-54,70-75,88-93`
**Issue:** Todos los parches de `matriz_client.client._base_url` usan `raising=False`, que **crea** el atributo si no existe. Si una refactorización renombra `_base_url` en `matriz_client.client`, estos tests seguirían pasando (parcheando un atributo inexistente), mientras que el código de producción `mutating_allowed` (`mutation_gate.py:48`) leería el atributo real y fallaría con `AttributeError` en vivo. Los tests dejarían de proteger el contrato. Esto es deuda de fiabilidad del test, en scope por afectar la confiabilidad de la suite.
**Fix:** Usar `raising=True` (default) para que el parche falle ruidosamente si el atributo desaparece:

```python
monkeypatch.setattr(matriz_client.client, "_base_url", "https://api.remarkets.primary.com.ar")
```

## Info

### IN-01: `_synthetic` se evalúa siempre aunque exista un reemplazo explícito

**File:** `verification/anonymize.py:60`
**Issue:** `deny.replacements.get(k, _synthetic(k, v))` evalúa `_synthetic(k, v)` de forma eager incluso cuando `k` tiene reemplazo explícito (es el default de `dict.get`, siempre evaluado). No es un bug funcional, pero ejecuta trabajo inútil y, combinado con CR-01, hace menos obvio el flujo.
**Fix:** Ramificar explícitamente: `deny.replacements[k] if k in deny.replacements else _synthetic(k, v)`.

### IN-02: `schema_of` de listas heterogéneas sólo muestrea el primer elemento

**File:** `verification/schema.py:38-39`
**Issue:** Para una lista, el esquema se deriva del primer elemento (`payload[0]`). Si la API devuelve una lista cuyos elementos difieren en claves/tipos (unión de formas, o un primer elemento atípico/null), el drift estructural en elementos posteriores no se detecta. Es una decisión de diseño documentada (D-12, "tipo del primer elemento como muestra"), por eso es Info y no Warning, pero conviene anotar el límite para los snapshots de Fase 2.
**Fix:** Documentar el supuesto de homogeneidad en el docstring; si se necesita, considerar fusionar las formas de todos los elementos (`schema_of` unión de claves) en una iteración futura.

### IN-03: `main_verify.py` ejecuta `main_ambito_financiero.py`, que está fuera del scope de esta revisión

**File:** `main_verify.py:31`
**Issue:** El runner referencia `main_ambito_financiero.py`, que existe en disco pero no está en la lista de archivos revisados de esta fase (no fue tocado o no se incluyó). Si ese driver no aplica los mismos gates de redacción/env, el runner lo ejecutaría igual. No es un defecto del código revisado, pero queda anotado como riesgo de cobertura: conviene verificar que `main_ambito_financiero.py` cumpla los mismos invariantes HARN-03.
**Fix:** Confirmar que `main_ambito_financiero.py` aplica `require_env`/redacción consistentes con el resto, o incluirlo explícitamente en una revisión.

### IN-04: `redact` con `keep` grande respecto al largo del valor degrada a `"…"` silenciosamente

**File:** `verification/redaction.py:25-27`
**Issue:** Si `keep >= len(value)`, `redact` devuelve `"…"` (rama `len(value) <= keep`). Es el comportamiento seguro deseado (no exponer prefijo casi-completo), pero un caller que pase un `keep` mayor al esperado obtiene salida idéntica para valores distintos sin señal de por qué. Comportamiento correcto, sólo poco evidente.
**Fix:** Ninguno requerido; opcionalmente documentar en el docstring que `keep >= len(value)` colapsa a `"…"` por diseño.

---

_Reviewed: 2026-05-28T00:12:15Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
