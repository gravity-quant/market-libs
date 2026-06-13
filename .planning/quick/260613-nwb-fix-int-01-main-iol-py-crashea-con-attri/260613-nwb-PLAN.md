---
quick_id: 260613-nwb
type: execute
wave: 1
depends_on: []
files_modified:
  - main_iol.py
autonomous: true
requirements:
  - INT-01  # Integration finding from .planning/v1.1-INTEGRATION-CHECK.md (Phase 11 LIVE-01 prerequisite)
must_haves:
  truths:
    - "main_iol.py no usa el atributo legacy `_base_url` (denied por _DENIED_LEGACY en iol_client.client y iol_client.aio)"
    - "Las 15 probes del driver leen base_url vía el accessor post-refactor `_get_default()._state.base_url`, espejando el patrón ya probado en main_ambito_financiero.py y main_higyrus.py"
    - "`uv run ruff check main_iol.py` pasa sin warnings"
    - "`python -c \"import ast; ast.parse(open('main_iol.py').read())\"` no levanta SyntaxError"
    - "`grep -c 'iol_client\\.client\\._base_url\\|aio\\._base_url' main_iol.py` devuelve 0"
  artifacts:
    - path: "main_iol.py"
      provides: "Driver de verificación en vivo de iol-client con accessor post-refactor"
      contains: "_get_default()._state.base_url"
  key_links:
    - from: "main_iol.py (cada probe)"
      to: "iol_client.client._get_default()._state.base_url / aio._get_default()._state.base_url"
      via: "lectura de atributo Python (no HTTP)"
      pattern: "_get_default\\(\\)\\._state\\.base_url"
---

<objective>
Eliminar el `AttributeError` reportado en INT-01 (`.planning/v1.1-INTEGRATION-CHECK.md`) reemplazando las 15 lecturas de `iol_client.client._base_url` y `aio._base_url` en `main_iol.py` por el accessor post-refactor `_get_default()._state.base_url`, que es el patrón ya consolidado en `main_ambito_financiero.py` y `main_higyrus.py`.

Purpose: Desbloquear LIVE-01 (Phase 11) eliminando el blocker del driver `main_iol.py`. Tras Phase 6, `iol_client.client.__getattr__` rechaza explícitamente `_base_url` vía `_DENIED_LEGACY = frozenset({"_user", "_password", "_base_url"})` (mismo set en `aio.py`), por lo que cada uno de los 15 accesos en el driver levanta `AttributeError` antes de que cualquier `try/except` lo pueda contener — el driver crashea sin completar ni un probe.

Output: `main_iol.py` editado, sin cambios en ningún paquete bajo `packages/iol-client/`. La fase de verificación es estática (parse + lint + grep de patrones); no requiere credenciales ni network access.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/v1.1-INTEGRATION-CHECK.md
@./CLAUDE.md
@main_iol.py
@main_ambito_financiero.py
@main_higyrus.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Reemplazar las 15 lecturas de `_base_url` en main_iol.py por `_get_default()._state.base_url`</name>
  <files>main_iol.py</files>
  <action>
Editar `main_iol.py` para sustituir cada uso del atributo legacy denied por el accessor post-refactor, sin cambios en ningún otro archivo (la fix es entry-point-only, los paquetes bajo `packages/iol-client/` son intocables).

Reemplazos exactos (cada uno aparece UNA vez en su línea — usar Edit por línea o un sed equivalente, validando que el conteo total final coincide):

1. En 12 sitios (líneas 191, 265, 408, 559, 695, 894, 962, 1195, 1270, 1410 — todas las probes sync + `probe_parity_sync_async` + `probe_field_type_map` + `probe_schema_snapshot` + `probe_refresh_token` + `probe_auth_401`):
   - DE: `base_url = iol_client.client._base_url`
   - A:  `base_url = iol_client.client._get_default()._state.base_url`

2. En 5 sitios (líneas 226, 343, 487, 620, 805 — los 5 probes async):
   - DE: `base_url = aio._base_url`
   - A:  `base_url = aio._get_default()._state.base_url`

Patrón fuente (verificado): `main_ambito_financiero.py:141` usa `ambito.client._get_default()._state.base_url` y `main_ambito_financiero.py:228` usa `aio._get_default()._state.base_url`. `main_higyrus.py:411` usa `higyrus_client.client._get_default()._state.base_url` y `main_higyrus.py:464` usa `aio._get_default()._state.base_url`. Los accessors `_get_default()` están definidos en `packages/iol-client/src/iol_client/client.py:423` y `packages/iol-client/src/iol_client/aio.py:410`, y `_state.base_url` es el field público del `_ClientState` dataclass.

Restricciones:
- NO modificar ningún archivo dentro de `packages/iol-client/`.
- NO renombrar variables locales (`base_url` queda igual).
- NO mover la asignación dentro de un `try/except` ni cambiar el flujo de control — sólo cambiar el RHS de la asignación.
- NO tocar los otros accesos a `iol_client.client.*` o `aio.*` que NO sean `_base_url` (ej. `iol_client.client._refresh_token`, `iol_client.client._token`, `iol_client.client._token_expires_at`, `iol_client.client._password`, `iol_client.client._request`, `aio.aclose`, `aio._refresh_token`, `aio._client`, etc. — esos siguen funcionando vía PEP 562 shim o son atributos públicos).
- NO agregar `# type: ignore`, comentarios explicativos extra, ni reformatear líneas adyacentes.

Tras los reemplazos, el conteo `grep -c 'iol_client\.client\._base_url\|aio\._base_url' main_iol.py` debe dar exactamente `0` y `grep -c '_get_default()._state.base_url' main_iol.py` debe dar exactamente `15`.
  </action>
  <verify>
    <automated>uv run ruff check main_iol.py &amp;&amp; python -c "import ast; ast.parse(open('main_iol.py').read())" &amp;&amp; test "$(grep -c 'iol_client\.client\._base_url\|aio\._base_url' main_iol.py)" = "0" &amp;&amp; test "$(grep -c '_get_default()._state.base_url' main_iol.py)" = "15"</automated>
  </verify>
  <done>
- `main_iol.py` no contiene NINGUNA ocurrencia de `iol_client.client._base_url` ni de `aio._base_url`.
- `main_iol.py` contiene exactamente 15 ocurrencias de `_get_default()._state.base_url`.
- `uv run ruff check main_iol.py` pasa (exit 0).
- `python -c "import ast; ast.parse(open('main_iol.py').read())"` parsea sin SyntaxError.
- No se modificó ningún archivo bajo `packages/iol-client/` ni ningún otro `main_*.py`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Probe-import smoke + verificación cruzada con los drivers fuente (ambito + higyrus)</name>
  <files>main_iol.py</files>
  <action>
Verificación estática adicional sin requerir credenciales ni network:

1. **Smoke import:** ejecutar `uv run --package iol-client python -c "import importlib.util, pathlib; spec = importlib.util.spec_from_file_location('main_iol', pathlib.Path('main_iol.py').resolve()); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('IMPORT_OK')"`. Esto importa `main_iol.py` como módulo, ejecutando todo a top-level (imports, defs, constantes) sin llamar a `main()`. Si la importación falla por cualquier `AttributeError` u otro error de carga, la fix está incompleta.

2. **Cross-driver pattern check:** confirmar que el patrón final en `main_iol.py` matchea byte-a-byte el usado en los drivers de referencia:
   - `grep -c 'iol_client\.client\._get_default()\._state\.base_url' main_iol.py` debe ser `10`.
   - `grep -c 'aio\._get_default()\._state\.base_url' main_iol.py` debe ser `5`.
   - Suma: 15.

3. **Negative grep — denied legacy clear:** `grep -E 'iol_client\.client\._base_url|^[^#]*\baio\._base_url\b' main_iol.py` no debe matchear ninguna línea. (El segundo branch excluye comentarios para evitar falsos positivos si en el futuro se documenta el patrón histórico.)

Nota: NO ejecutamos `uv run --package iol-client python main_iol.py` completo porque (a) requeriría credenciales reales `IOL_USER` / `IOL_PASSWORD`, (b) gatillaría HTTP calls contra `api.invertironline.com`, y (c) consumiría rate-limit / un intento contra el server. La fix es puramente un swap de path de atributo verificable estáticamente; el live run pertenece a LIVE-01 (Phase 11).
  </action>
  <verify>
    <automated>uv run --package iol-client python -c "import importlib.util, pathlib; spec = importlib.util.spec_from_file_location('main_iol', pathlib.Path('main_iol.py').resolve()); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('IMPORT_OK')" | grep -q '^IMPORT_OK$' &amp;&amp; test "$(grep -c 'iol_client\.client\._get_default()\._state\.base_url' main_iol.py)" = "10" &amp;&amp; test "$(grep -c 'aio\._get_default()\._state\.base_url' main_iol.py)" = "5"</automated>
  </verify>
  <done>
- `main_iol.py` importa como módulo sin levantar `AttributeError` (`IMPORT_OK` impreso).
- 10 ocurrencias de `iol_client.client._get_default()._state.base_url` (las 10 probes sync que lo usaban).
- 5 ocurrencias de `aio._get_default()._state.base_url` (las 5 probes async que lo usaban).
- Suma de patrones nuevos = 15 = conteo original de patrones legacy = paridad demostrada.
  </done>
</task>

</tasks>

<verification>
Verificación end-to-end del quick task:

1. **Parse:** `python -c "import ast; ast.parse(open('main_iol.py').read())"` no levanta SyntaxError.
2. **Lint:** `uv run ruff check main_iol.py` pasa.
3. **Cero ocurrencias legacy:** `grep -c 'iol_client\.client\._base_url\|aio\._base_url' main_iol.py` = 0.
4. **15 ocurrencias post-refactor:** `grep -c '_get_default()._state.base_url' main_iol.py` = 15 (10 sync + 5 async).
5. **Import smoke:** importar `main_iol.py` como módulo no levanta `AttributeError`.
6. **No collateral changes:** `git diff --stat` muestra UNICAMENTE `main_iol.py` modificado; ningún archivo bajo `packages/` aparece en el diff.

Note explícito sobre el alcance de la verificación: NO se ejecuta `main()` completo (requeriría credenciales `IOL_USER`/`IOL_PASSWORD` reales y haría HTTP calls contra `api.invertironline.com`). Eso pertenece a LIVE-01 (Phase 11). El INT-01 reportado en `v1.1-INTEGRATION-CHECK.md` es un `AttributeError` puramente de path de atributo Python, verificable estáticamente.
</verification>

<success_criteria>
- INT-01 cerrado: `main_iol.py` ya no levanta `AttributeError` por `_base_url` denied en `iol_client.client` o `iol_client.aio`.
- LIVE-01 (Phase 11) desbloqueado por este lado — el driver puede al menos iniciar; si falla downstream, será por credenciales/network/server, no por el shim Phase 6.
- Patrón consistente entre los tres drivers principales (`main_ambito_financiero.py`, `main_higyrus.py`, `main_iol.py`) — todos usan `_get_default()._state.base_url`.
- No regressions en CI: ningún cambio en `packages/`, por lo tanto el suite 782-tests no se ve afectado (los drivers `main_*.py` no son parte del test suite, confirmado por INT-01 audit).
</success_criteria>

<output>
Crear `.planning/quick/260613-nwb-fix-int-01-main-iol-py-crashea-con-attri/260613-nwb-SUMMARY.md` al cerrar el quick task con:
- Diff resumido (15 líneas cambiadas en `main_iol.py`).
- Evidencia de los 4 checks de verification (ast.parse, ruff, grep counts, import smoke).
- Nota: INT-01 cerrado; LIVE-01 (Phase 11) avanza.
- Actualizar `.planning/STATE.md` "Quick Tasks Completed" con la fila correspondiente.
</output>
