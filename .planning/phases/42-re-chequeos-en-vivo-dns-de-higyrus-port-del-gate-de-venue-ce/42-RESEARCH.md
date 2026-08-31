# Phase 42: Re-chequeos en vivo — DNS de higyrus + port del gate de venue + censo `Literal` de matriz - Research

**Researched:** 2026-08-31
**Domain:** Verificación en vivo interna al repo — port de un gate de seguridad, re-sonda de red, censo de vocabulario y captura de wire fresco. **Cero dependencias externas nuevas.**
**Confidence:** HIGH (todos los hallazgos verificados por ejecución directa de herramientas contra HEAD en esta sesión)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Venue gate port (criterio 1)**

- **D-01:** `scripts/literal_census_33.py` importa `main_matriz._VENUE_ALLOWLIST` y
  `main_matriz._venue_token` directamente (reemplazando el `if "remarkets" not in base:` stale de
  la línea 192) — NO se duplica el dict con un test de igualdad separado. El test de "single
  source" es de identidad de objeto (`is`), no de contenido (`==`): con import, la divergencia
  entre sitios es estructuralmente imposible en vez de sólo detectada por un pin test. `main_matriz`
  es importable sin costo: cero side-effects fuera de `if __name__ == "__main__":` (línea 3162), ya
  lo importan 8 archivos de `verification/` a nivel de test, y `pythonpath = ["."]`
  (`pyproject.toml:109`) hace innecesario cualquier `sys.path` hack.
- **D-02:** El checkpoint humano bloqueante del criterio 1 se enmarca como **confirmación de
  fidelidad del port** — "¿el port reusa fielmente la lógica ya aprobada en D-02 de la Phase 39?" —
  no como una re-autorización de bbsa desde cero. `bbsa.matrizoms.com.ar` ya es un host autorizado
  a nivel de sistema (Phase 39 D-02, `39-CONTEXT.md`); lo que es nuevo es que
  `literal_census_33.py` específicamente nunca hizo una llamada de red hasta ahora. Precedente de
  forma: `.planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-01-PLAN.md:87-141`
  — `<task type="checkpoint:human-verify" gate="blocking-human">`, cero archivos tocados, el
  operador transcribe "approved" verbatim en el SUMMARY, gatea la siguiente task.
- **D-03 (falsification test):** El test de spoofing es un archivo nuevo que espeja
  `verification/test_main_matriz_skip_line_shape.py:24-40`, que ya ejercita `main_matriz._venue_token`
  contra un sufijo hostil (`<host>.attacker.example`) y la variante userinfo
  (`https://<host>@attacker.example`) — se reusa el mismo patrón de casos contra
  `literal_census_33.py`'s uso importado.

**Alcance de iol en la corrida (criterio 2, indirectamente)**

- **D-04:** La corrida en vivo de la Phase 42 llama a `census_matriz()` directamente (no `main()`
  sin modificar, que también dispara `census_iol()`). Credenciales de IOL están presentes en
  `packages/iol-client/.env`, así que `main()` sin cambios SÍ ejecutaría `census_iol()` de verdad —
  pero DT-07 (el requisito que `census_iol()` sirve) ya está **CERRADO**
  (`.planning/STATE.md:405`, censo vivo de 33-06 sobre 2191 filas) y LIVE-02 nombra únicamente los 5
  campos de matriz. Ejecutar `census_iol()` de nuevo es tráfico en vivo contra IOL sin ningún
  criterio de éxito de esta fase que lo consuma.
- **Forma del cambio (discreción del planner):** llamar a `census_matriz()` desde afuera del script
  (sin tocar `main()`/`literal_census_33.py` más allá del port D-01), o agregar un flag
  `--matriz-only` a `main(argv)` espejando el patrón existente de `--selftest` (línea 355) — ambas
  formas satisfacen D-04 igual de bien; el planner elige.

**Re-chequeo de higyrus (criterio 2)**

- **D-05:** El re-chequeo corre el driver completo `main_higyrus.py` (no `scripts/preflight_33.py`).
  Sólo el driver completo sobrescribe `.planning/verification/run-evidence/higyrus-client.json` con
  un `captured_at` fresco vía `write_run_evidence()` — es la única prueba durable y timestampeada de
  "re-confirmado en esta sesión". `preflight_33.py` imprime pero no persiste nada en disco.
- **D-06:** Si higyrus sigue `SKIPPED` tras esta corrida, el destino `LIVE-HIGY-33` se renombra a
  `LIVE-HIGY-42` — el criterio 2 lo exige literalmente ("destino renombrado") y la convención de
  nombres embebe la fase de origen (`LIVE-MATZ-33` sigue el mismo patrón). Sitios a tocar:
  `main_higyrus.py` (`_VENDOR_UNREACHABLE_SKIP_LINE`, `_VENDOR_UNREACHABLE_EVIDENCE`),
  `main_matriz.py` (`_CYCLE_CLOSURE_DESTINATION["higyrus-client"]`), y ~8 archivos de test que
  pinnean el string literal `"LIVE-HIGY-33"` (`verification/test_cycle_closure_phase33.py`,
  `verification/test_main_higyrus_skip_line_shape.py`,
  `verification/test_main_verify_classification.py`, `verification/test_run_evidence.py`,
  `verification/test_main_higyrus_deep_chain.py`). Si el DNS resuelve limpio esta vez, el rename es
  moot — la rama SKIPPED nunca dispara.
- **Nota de redacción (no bloquea, informa al planner):** `_vendor_unreachable_reason` (contiene
  `f"...{type(exc).__name__}: {exc}"`, potencialmente con el hostname sin resolver) se setea pero
  nunca se imprime ni persiste — es una decisión de redacción ya lockeada (D-HIGY-15). "Excepción y
  diagnóstico citados" (criterio 2) tiene que salir de la prosa del propio reporte de la sesión, no
  del stdout/evidence committeado del driver, igual que el diagnóstico original `socket.gaierror`
  de `LIVE-HIGY-33` en el backlog fue prosa del operador, no output del driver.

**Lectura fresca del wire de market-data-client (criterio 5)**

- **D-07:** El mecanismo es `verification.capture.capture(...)` en los dos puntos donde
  `main_market_data.py` ya tiene el JSON crudo en mano (probes de instruments ~línea 975-980,
  segments ~línea 1004) — el mismo patrón que `literal_census_33.py` ya usa para matriz/iol. **NO**
  se reusa `_write_schema_snapshot` para este propósito: es write-once / no-overwrite-on-drift por
  diseño (D-25) y por lo tanto no puede producir un artefacto fechado en esta sesión — los baselines
  committeados (`get-instruments.json`, `get-segments.json`) están fechados 2026-07-31 (confirmado
  vía `git log`) y seguirían así sin cambio aunque el driver corra hoy.
- **D-08 (abierto para planning, no para discuss):** `capture()` no se auto-timestampea. Se necesita
  o bien un envelope wrapper (espejando la forma `{"captured_at": ..., ...}` que ya usa
  `_write_schema_snapshot`) o una cita explícita del timestamp en el SUMMARY del plan. El requisito
  en sí —evidencia fechada que Phase 43 pueda citar como no-stale— está LOCKED; la forma concreta
  queda a discreción del planner.

### Claude's Discretion

- Forma exacta del cambio D-04 (llamada externa a `census_matriz()` vs. flag `--matriz-only`).
- Forma exacta del envelope/timestamp de D-08 (wrapper JSON vs. cita en SUMMARY).
- Si el DNS de higyrus resuelve limpio en esta corrida, D-06 (rename) no aplica — el planner no
  necesita ramificar el plan para ambos casos por adelantado; el resultado de D-05 decide en
  ejecución si D-06 dispara.

### Deferred Ideas (OUT OF SCOPE)

Ninguna — el análisis se mantuvo dentro del boundary de la fase. La re-confirmación de DT-07 (censo
iol) queda explícitamente NO absorbida en esta fase (D-04) por estar ya cerrada y fuera del texto
de LIVE-02; si algún futuro audit la cuestiona, es una fase/corrida separada.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **LIVE-01** | Re-chequear la conectividad DNS de `higyrus-client` y producir un resultado medido — resuelto, o `SKIPPED` con causa re-confirmada (nunca un silencio) | § Pre-flight Medido de LIVE-01 (DNS medido HOY: **NO resuelve**), § Verified Code Sites → `main_higyrus.py`, § Pitfall 1 (rama `ConnectTimeout` no cubierta), § Runtime State Inventory (rename `LIVE-HIGY-33`) |
| **LIVE-02** | Correr el censo de valores `Literal` de RESPONSE de `matriz-client` contra el sandbox `bbsa`, con el allowlist exacto de hostname portado primero desde `main_matriz.py` | § Verified Code Sites → `literal_census_33.py` / `main_matriz.py`, § Code Examples (port + test de spoofing), § Pitfall 2 (CI enrollment), § Pitfall 5 (falta el header venue+timestamp del criterio 3) |
</phase_requirements>

## Summary

Esta fase no tiene dominio técnico externo: no instala paquetes, no adopta librerías, no toca la
superficie pública de ningún cliente. Todo el riesgo está en **sitios de código exactos y en el
orden de las operaciones**. Por eso esta investigación es un censo verificado de esos sitios —
cada línea, firma y comportamiento reportado abajo fue confirmado ejecutando herramientas contra
HEAD en esta sesión, no recordado.

**Tres hallazgos cambian la forma del plan y no están en CONTEXT.md:**

1. **El DNS de higyrus sigue sin resolver — medido hoy.** `socket.getaddrinfo()` sobre el host de
   `HIGYRUS_BASE_URL` devuelve `gaierror: [Errno 8] nodename nor servname provided, or not known`.
   Y se verificó que httpx 0.28.1 mapea exactamente ese fallo a `httpx.ConnectError` con ese mismo
   mensaje. Es decir: la rama `_vendor_unreachable` de `main_higyrus.py:669` **va a disparar**, el
   veredicto va a ser `SKIPPED`, y **la rama de rename D-06 está viva**. El planner puede planificar
   el rename como camino principal (con el camino "resolvió" como contingencia, no al revés).
2. **El criterio 3 exige un header de venue + timestamp que el censo hoy no emite.** `_report()`
   (`scripts/literal_census_33.py:154`) imprime una línea por path y nada más — no hay encabezado.
   Ningún D-lock de CONTEXT.md cubre esto. Es un cambio de código adicional, obligatorio, en el
   mismo archivo del port D-01.
3. **Un test nuevo bajo `verification/` es INERTE salvo que se lo agregue a mano a la allowlist
   explícita de `.github/workflows/ci.yml:79-92`.** Es el defecto WR-01 que el code review de la
   Phase 36 ya encontró una vez. El test de falsificación del criterio 1 no está "entregado" hasta
   que esa línea existe.

Adicionalmente: `capture()` escribe a `.planning/verification/captures/`, que está **gitignored**
(`.gitignore:53`), y `main_market_data.py` **no** escribe run-evidence. Así que sin una decisión
explícita de D-08, el criterio 5 termina produciendo evidencia que existe sólo en el working tree
del ejecutor y sin fecha adentro del archivo.

**Primary recommendation:** Ordenar el plan en cuatro waves estrictamente secuenciales —
(0) checkpoint `gate="blocking-human"` → (1) port del gate + header + test de spoofing + línea de
CI, todo offline y verificable sin red → (2) corridas en vivo (higyrus primero, censo matriz
después, market-data al final) → (3) rename condicional + artefactos. Ninguna llamada de red antes
de que el gate portado esté verde y enrolado en CI.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Decisión de venue (¿se puede tocar este host?) | Script de verificación de raíz (`main_matriz.py`) | — | `main_matriz._venue_token` es la única fuente; el script de censo la importa, nunca la re-declara (D-01) |
| Gate de mutación (¿se puede emitir una orden?) | Harness (`verification/mutation_gate.py`) | — | Gate **independiente** del de lectura; remarkets-only por diseño; criterio 4 lo declara byte-idéntico |
| Sonda de red / veredicto de corrida | Driver de raíz (`main_higyrus.py`) | Harness (`verification/run_evidence.py`) | El driver mide; el harness persiste el sobre timestampeado |
| Clasificación del veredicto | Harness (`main_verify.py::_ENV_SKIP`) | — | Regex `^SKIPPED \S.*:` sobre stdout; los dos puntos son load-bearing |
| Censo de vocabulario RESPONSE | Script (`scripts/literal_census_33.py`) | Cliente (`matriz_client._core` builders) | El censo lee el **wire crudo**, nunca el stream de divergencias (el branch `Literal` de `walk_field` retorna temprano) |
| Captura de wire crudo | Harness (`verification/capture.py`) | — | Único hogar legal del payload crudo: staging gitignored (C-4 / D-11) |
| Snapshot de schema committeable | Driver (`main_market_data._write_schema_snapshot`) | — | Write-once / no-overwrite-on-drift (D-25) — **por diseño no sirve** para evidencia fresca |
| Enforcement de los locks | CI (`.github/workflows/ci.yml` job `lint`, allowlist explícita) | — | `verification/` nunca corre entero en CI; enrolamiento a mano |

## Project Constraints (from CLAUDE.md)

Directivas actionables extraídas de `./CLAUDE.md` que el planner debe honrar:

| # | Directiva | Impacto en esta fase |
|---|-----------|----------------------|
| C-1 | Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict — todo cambio debe pasar el CI existente | Los 4 gates (`ruff check`, `ruff format --check`, `mypy`, `pytest`) deben quedar verdes; ver § Validation Architecture para los comandos exactos |
| C-2 | Sin código compartido entre paquetes (por diseño) | **NO violada por D-01**: `scripts/` y `main_*.py` son scripts de raíz, no `packages/`. La restricción aplica a `packages/`. Verificado: `mypy.files` (pyproject.toml:97) cubre sólo `packages/*/src` |
| C-3 | Cualquier fix de lógica debe espejarse en `client.py` y `aio.py` del mismo paquete | **No aplica**: esta fase no toca ningún `packages/*/src`. Si eso cambia, es scope creep |
| C-4 | Credenciales en `.env` por paquete; nunca commitear `.env` ni exponer credenciales en logs, reportes o tests | Refuerza T-39-04: las líneas SKIPPED no interpolan hostname ni base URL. El hostname de higyrus **no se transcribe** en ningún artefacto committeado, incluido este RESEARCH.md |
| C-5 | Las dependencias externas en vivo pueden variar por horario de mercado, datos disponibles o rate limits | El censo puede devolver conjuntos vacíos para `ordType` si no hay órdenes en la cuenta bbsa — eso es "no se pudo medir y por qué", explícitamente admitido por el criterio 3 |
| C-6 | GSD Workflow Enforcement: nada de edits fuera de un comando GSD | Ya satisfecho: esta fase corre bajo `/gsd-plan-phase` → `/gsd-execute-phase` |

**Project skills:** 3 skills presentes (`spike-findings-market-libs`, `spike-findings-codegen-market-libs`,
`senior-prompt-engineer`). Ninguna es relevante para esta fase — la primera cubre el TokenStore de
matriz de la Phase 10, la segunda es un NO-GO de codegen, la tercera es genérica de prompting.
Ninguna aporta reglas que restrinjan este plan. `[VERIFIED: ls .claude/skills/]`

---

## Verified Code Sites

> Esto es el núcleo de esta investigación. Cada fila fue confirmada leyendo HEAD en esta sesión.
> El planner puede escribir `<read_first>` y `<action>` citando estas líneas sin re-derivar nada.

### `main_matriz.py` (3162 líneas)

| Símbolo | Línea | Forma verificada |
|---------|-------|------------------|
| Comentario D-02 (rationale del allowlist) | `115-138` | Documenta igualdad exacta, sufijo hostil, userinfo, P-05, y que `mutation_gate.py` no se toca |
| `_VENUE_ALLOWLIST: dict[str, str]` | `139-142` | `{"api.remarkets.primary.com.ar": "remarkets", "api.bbsa.matrizoms.com.ar": "bbsa"}` |
| `_HOST_SKIP_LINE` | `151` | Literal de módulo, sin interpolación |
| `_HOST_SKIP_EVIDENCE` | `156` | Literal de módulo |
| `_CYCLE_CLOSURE_DESTINATION` | `162-165` | `{"higyrus-client": "LIVE-HIGY-33", "matriz-client": "LIVE-MATZ-33"}` ← **sitio de rename D-06** |
| `_cycle_closure_destination(pkg) -> str` | `169-171` | |
| `_cycle_closure_verdict(pkg, *, probes, evidence, ok, missing) -> tuple[str, str]` | `174-225` | keyword-only tras `pkg` |
| `def _venue_token(base_url: str) -> str \| None` | `228-247` | `urlsplit`; re-parsea como `//{base_url}` si no hay netloc; `except ValueError → None`; `host is None → None`; `return _VENUE_ALLOWLIST.get(host)` |
| `if __name__ == "__main__":` | `3162` | Confirmado: **cero side-effects de import**. `import main_matriz` mide **0.11 s**. `[VERIFIED: uv run python]` |

### `scripts/literal_census_33.py` (367 líneas)

| Símbolo | Línea | Forma verificada |
|---------|-------|------------------|
| `_REPO_ROOT` + `sys.path.insert(0, ...)` | `68-70` | **Ya existe.** Cualquier `import main_matriz` nuevo va DESPUÉS de esta línea |
| `from verification.capture import capture  # noqa: E402` | `72` | Patrón exacto a espejar para el import nuevo (E402 no está en per-file-ignores) |
| `__all__ = ["collect_paths", "main"]` | `74` | |
| `_MATRIZ_KEYS` | `80` | `frozenset({"marketId","cficode","currency","orderTypes","ordType"})` — los 5 campos del criterio 3, exactos |
| `collect_paths(node, ...)` | `99` | |
| `_report(pkg, endpoint, acc) -> None` | `154-163` | Imprime `f"{pkg} {endpoint} {path}: rows=… types=… distinct=…"`. **No emite header** ← gap del criterio 3 |
| `_skip(pkg, reason) -> None` | `166-167` | |
| `census_matriz() -> bool` | `175-233` | |
| **Gate stale** `if "remarkets" not in base:` | **`192`** | ← **el sitio del port D-01** |
| `client = Client()` / `base = client._state.base_url` | `190-191` | El gate corre ANTES de login y de cualquier request |
| `census_iol() -> bool` | `241` | |
| `--selftest` handling | `355-356` | `if "--selftest" in argv: return _selftest()` — patrón a espejar para `--matriz-only` |
| `main(argv: list[str]) -> int` | `353-362` | `return 0 if (ran_matriz and ran_iol) else 1` ← **ojo**: con `--matriz-only` el exit code debe redefinirse o `ran_iol=False` daría exit 1 en una corrida exitosa |
| `if __name__ == "__main__":` | `365` | |

**Verificado:** `uv run python scripts/literal_census_33.py --selftest` sale **PASS** en HEAD.
El walker no es un canal muerto. `[VERIFIED: ejecución]`

**Verificado:** `import scripts.literal_census_33` funciona como namespace package (no hay
`__init__.py`, no hace falta) con `pythonpath=["."]` bajo pytest. **Ningún test existente lo hace
todavía** — el test de spoofing sería el primero. `[VERIFIED: uv run python + grep]`

### `main_higyrus.py` (3050 líneas)

| Símbolo | Línea | Forma verificada |
|---------|-------|------------------|
| `_auth_failed` / `_auth_failure_reason` (cascade D-HIGY-10) | `225-226` | |
| Comentario D-01 Phase 39 | `228-235` | |
| `_vendor_unreachable` / `_vendor_unreachable_reason` | `236-237` | |
| `_VENDOR_UNREACHABLE_SKIP_LINE` | `244-246` | `"SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-33"` ← **rename D-06** |
| `_VENDOR_UNREACHABLE_DETAIL` | `249` | `"vendor host unreachable (DNS)"` — **sin** destino, no se renombra |
| `_VENDOR_UNREACHABLE_EVIDENCE` | `254` | `"vendor host unreachable (DNS) — LIVE-HIGY-33"` ← **rename D-06** |
| Rama `except httpx.ConnectError` (sync) | `669-684` | Setea ambos globales; **no** llama `append_finding`; devuelve `ProbeResult(..., "SKIPPED", ...)` |
| Rama `except httpx.ConnectError` (async) | `753-757` | Espejo exacto de la sync |
| `except _RESIDUAL_PROBE_EXCEPTIONS` | `685+` | Va DESPUÉS — invertir el orden deja la rama `ConnectError` inalcanzable |
| Corte temprano `if _vendor_unreachable:` en `main()` | `2908-2923` | `print(_VENDOR_UNREACHABLE_SKIP_LINE)` → `write_run_evidence(...)` → `sys.exit(0)` |
| `write_run_evidence(...)` (rama skip) | `2916-2922` | `_PKG`, `driver="main_higyrus.py"`, `triples=[]`, `counts={}`, `skipped=_VENDOR_UNREACHABLE_EVIDENCE` |
| `write_run_evidence(...)` (rama normal) | `3042` | |
| Comentarios que citan `LIVE-HIGY-33` en prosa | `1886`, `2052` | **Comentarios, no constantes** — el planner decide si los renombra (recomendado: sí, describen el bloqueo vigente) |
| `if __name__ == "__main__":` | `3050` | |

### `verification/run_evidence.py`

```python
def write_run_evidence(
    slug: str,
    *,
    driver: str,
    triples: Iterable[tuple[str, str, str, str]],
    counts: Mapping[str, int],
    skipped: str | None = None,
) -> Path:
```
Líneas `97-104`. El envelope (líneas `125-134`) incluye
`"captured_at": dt.datetime.now(dt.UTC).isoformat()` y **reemplaza** el archivo entero.
**D-05 confirmado:** es el único mecanismo que produce un artefacto committeado y fechado en esta
sesión para higyrus. `[VERIFIED: lectura de fuente]`

### `verification/capture.py`

```python
def capture(pkg: str, endpoint: str, payload: Any) -> Path:
    # -> .planning/verification/captures/{pkg}-{endpoint}.json
```
Líneas `42-51`. `write_text(json.dumps(payload, indent=2, ensure_ascii=False))` — **sobrescribe,
sin envelope, sin timestamp adentro del archivo**. El directorio está en `.gitignore:53`.
**D-07/D-08 confirmados exactamente como los describe CONTEXT.md.** `[VERIFIED: lectura de fuente]`

### `main_market_data.py` (3782 líneas)

| Símbolo | Línea | Forma verificada |
|---------|-------|------------------|
| Bloque `from verification import (...)` | `60-68` | **`capture` NO está importado** — hay que agregar `from verification.capture import capture` (los imports son top-level, sin `noqa` necesario acá) |
| `_ENDPOINT_TEMPLATES["get_instruments"]` | `138` | `"/instruments"` |
| `_ENDPOINT_TEMPLATES["get_segments"]` | `139` | `"/instruments/segments"` |
| `_write_schema_snapshot(*, endpoint, client_function, raw, base_url, surface)` | `457-522` | Write-once en `482-487`; en drift emite finding SHAPE y **nunca** sobrescribe (`508-522`) |
| `probe_instruments_sync(client)` | `968-994` | `raw` disponible en **`975-980`**; `_write_schema_snapshot` en `985-991` ← **sitio de `capture()` D-07** |
| `probe_segments_sync(client)` | `997-1022` | `raw` disponible en **`1004`**; `_write_schema_snapshot` en `1010-1016` ← **sitio de `capture()` D-07** |
| `probe_instruments_async(aclient)` | `1332`, raw en `1340` | Espejo async — el planner decide si también captura (criterio 5 no lo exige) |
| `probe_segments_async(...)` | `1363` | Ídem |
| `main() -> None` | `3648` | **Sin argv, sin flags.** No hay forma de correr un subconjunto de probes |
| `write_run_evidence` | — | **AUSENTE.** No existe `run-evidence/market-data-client.json` |
| `if __name__ == "__main__":` | `3782` | |

### `verification/mutation_gate.py` — criterio 4 (byte-idéntico)

**Pin verificable para el plan:**

```
git blob SHA-1: 6bdaec006cc16f7c8dbfac41701712a9085c691b
tamaño:         5877 bytes
_SANDBOX_HOST:  "api.remarkets.primary.com.ar"   (línea 73)
```

Verificación automatizada sugerida para el `<verify>` del plan:
```bash
test "$(git hash-object verification/mutation_gate.py)" = 6bdaec006cc16f7c8dbfac41701712a9085c691b
```
Esto es más fuerte que `git diff --exit-code`: prueba identidad de contenido contra un valor
literal escrito en el plan, no contra "lo que sea que estuviera en el índice".
`[VERIFIED: git hash-object]`

### `verification/test_main_matriz_skip_line_shape.py` — el patrón a espejar (D-03)

269 líneas, dos capas. Lo relevante para el port:

| Test | Línea | Qué hace |
|------|-------|----------|
| `test_venue_allowlist_has_exactly_the_two_known_hosts` | `205-215` | `set(allowlist) == {...}` + `len == 2` |
| `test_venue_token_resolves_by_exact_hostname` | `218-244` | **13 casos parametrizados** — la tabla completa está abajo en § Code Examples |
| `test_no_substring_membership_check_over_a_host_literal` | `247-268` | Aserción por **AST**, no grep: recorre `ast.Compare` buscando `In`/`NotIn` con `ast.Constant` string a la izquierda. Distingue la cita en el comentario del código vivo |

**El test AST del substring es directamente portable a `scripts/literal_census_33.py`** cambiando
`_DRIVER = "main_matriz.py"` por la ruta del script. Es la aserción que falsifica exactamente el
`if "remarkets" not in base:` que se está removiendo — si vuelve, el test se pone rojo.

---

## Pre-flight Medido de LIVE-01 (medición nueva, hecha en esta sesión)

> Esto es una **medición**, no una predicción. El planner debería tratarla como el estado esperado
> y planificar el rename D-06 como camino principal.

**Medición 1 — resolución DNS del host de higyrus (2026-08-31):**

```
packages/higyrus-client/.env  → existe
claves presentes: HIGYRUS_BASE_URL, HIGYRUS_CLIENT_ID, HIGYRUS_PASSWORD,
                  HIGYRUS_SAMPLE_CUENTA, HIGYRUS_SAMPLE_NIVEL,
                  HIGYRUS_SAMPLE_TIPO_CUENTA, HIGYRUS_USER, VERIFY_HIGYRUS_BAD_CREDS
esquema: https
socket.getaddrinfo(host) → gaierror: [Errno 8] nodename nor servname provided, or not known
```

El hostname **no se transcribe acá** por política T-39-04 / C-4. Las tres credenciales que el
driver necesita están presentes: **es alcanzabilidad, no auth** — idéntico diagnóstico al de
Phase 33 y Phase 39. `[VERIFIED: python3 socket.getaddrinfo]`

**Medición 2 — mapeo del fallo a la jerarquía de httpx (httpx 0.28.1 instalado):**

```
httpx.Client().post("https://<host-inexistente>.invalid/login")
  → httpx.ConnectError('[Errno 8] nodename nor servname provided, or not known')
  → isinstance(exc, httpx.ConnectError) is True
```

MRO verificado en la versión instalada:
```
ConnectError    < NetworkError      < TransportError < RequestError < HTTPError
ConnectTimeout  < TimeoutException  < TransportError < RequestError < HTTPError
issubclass(httpx.ConnectTimeout, httpx.ConnectError)  →  False
```
`[VERIFIED: uv run python -c, httpx 0.28.1]`

**Conclusión para el planner:**

1. La rama `main_higyrus.py:669 except httpx.ConnectError` **va a disparar**. El veredicto va a ser
   `SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-33` y `sys.exit(0)`.
2. Por lo tanto **D-06 (rename) está vivo** y debe planificarse, no diferirse a "por si acaso".
3. El diagnóstico citable para el criterio 2 —"excepción y diagnóstico citados, no heredados de la
   Phase 39"— es exactamente: `httpx.ConnectError: [Errno 8] nodename nor servname provided, or
   not known`, con la observación de que en macOS ese mensaje de errno **no incluye el hostname**,
   así que citarlo verbatim en el reporte no viola T-39-04. Esa es una mejora sobre lo que
   CONTEXT.md asumía (que la cita tendría que ser prosa parafraseada por miedo al leak).
4. **La rama NO cubierta sigue abierta:** si el host empezara a resolver pero colgara, el fallo
   sería `httpx.ConnectTimeout`, que NO es subclase de `ConnectError`, cae en
   `_RESIDUAL_PROBE_EXCEPTIONS` y produce un `FINDING`/`AUTH OPEN` en un ledger versionado en vez
   de un `SKIPPED`. Es el gap WR-02 documentado en la Phase 39. Ver § Pitfall 1.

**Medición 3 — credenciales y venue de matriz:**

```
packages/matriz-client/.env → existe
PRIMARY_BASE_URL host  = api.bbsa.matrizoms.com.ar   (∈ _VENUE_ALLOWLIST → token "bbsa")
PRIMARY_USER set       = True
PRIMARY_PASSWORD set   = True
PRIMARY_ACCOUNT set    = True    ← los endpoints de órdenes (ordType) SÍ van a correr
main_matriz._venue_token("https://api.bbsa.matrizoms.com.ar") → "bbsa"
```
`[VERIFIED: script .py real bajo uv run --package matriz-client]`

**Medición 4 — credenciales de market-data e iol:**

```
packages/market-data-client/.env → MARKET_DATA_AUDIENCE, MARKET_DATA_AUTH0_TOKEN_URL,
                                   MARKET_DATA_CLIENT_ID, MARKET_DATA_CLIENT_SECRET  (4/4)
packages/iol-client/.env        → IOL_BASE_URL, IOL_PASSWORD, IOL_USER  (confirma D-04:
                                   census_iol() SÍ correría de verdad si no se lo evita)
```
`[VERIFIED: lectura de claves, sin transcribir valores]`

### Trampa de resolución de `.env` (P-10) — verificada empíricamente

`load_dotenv()` se llama a nivel de módulo dentro del árbol de cada paquete
(`matriz_client/_state.py:33`, `matriz_client/client.py:57`, `higyrus_client/client.py:57`,
`market_data_client/client.py:85`). `find_dotenv()` camina hacia arriba desde el archivo del frame
llamador, así que encuentra `packages/<pkg>/.env`. **Pero** si `__main__` no tiene `__file__`
—es decir, con `python -c`— `find_dotenv` cae a `os.getcwd()`, y no hay `.env` en la raíz del repo.

Demostrado en esta sesión:

| Invocación | `base_url` resuelto | `PRIMARY_USER` |
|------------|---------------------|----------------|
| `uv run --package matriz-client python -c "..."` | `https://api.remarkets.primary.com.ar` ❌ (default) | `False` ❌ |
| `uv run --package matriz-client python <archivo.py>` | `https://api.bbsa.matrizoms.com.ar` ✅ | `True` ✅ |

**Implicación directa:** todo `<verify>` o `<action>` del plan que necesite credenciales o el venue
real **debe invocar un archivo `.py`, nunca `python -c`**. Un `-c` reportaría "credenciales
ausentes" fabricadas por el modo de invocación — y peor, un `Client()` bajo `-c` apunta al
**default remarkets**, no a bbsa. Esta es exactamente la P-10 que el docstring de
`literal_census_33.py:46-49` documenta, confirmada al pie de la letra.
`[VERIFIED: ejecución comparativa]`

---

## Standard Stack

**Cero dependencias nuevas.** Esta fase no instala, no actualiza y no adopta ninguna librería.

### Ya presente y usado por esta fase

| Componente | Versión verificada | Rol en esta fase |
|------------|--------------------|------------------|
| `httpx` | 0.28.1 | Jerarquía de excepciones que decide la rama de veredicto de higyrus |
| `pytest` | ≥8.3 (configurado en `pyproject.toml:102-121`) | Test de falsificación del criterio 1 |
| `ruff` | ≥0.7 | Gate de CI; `E402` **no** está en `per-file-ignores` → `# noqa: E402` explícito |
| `mypy` | ≥1.13 strict | `files` cubre sólo `packages/*/src` (`pyproject.toml:97`) → `scripts/` y `main_*.py` **fuera** del gate global |
| `python-dotenv` | ≥1.0 | Resolución de `.env` — ver la trampa P-10 arriba |
| stdlib `ast` | 3.12 | Aserción anti-substring del test de spoofing |
| stdlib `urllib.parse.urlsplit` | 3.12 | Motor de `_venue_token` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `import main_matriz` desde el script (D-01) | Duplicar el dict + un pin test de `==` | **Rechazado por D-01.** El import hace la divergencia estructuralmente imposible; el pin test sólo la detecta después del hecho |
| `capture()` en `main_market_data.py` (D-07) | Un script standalone `scripts/fresh_wire_42.py` que llama los builders y captura | Más barato (evita 113 KB de churn en el ledger de findings) pero **contradice D-07**, que está LOCKED. Ver § Open Questions Q3 |
| `_write_schema_snapshot` para evidencia fresca | — | **Imposible por diseño** (write-once, D-25). Confirmado en `main_market_data.py:482-487` |
| `scripts/preflight_33.py` para el re-chequeo de higyrus | — | **Rechazado por D-05**: imprime pero no persiste. Confirmado: 5010 bytes, sin `write_run_evidence` |

## Package Legitimacy Audit

**N/A — esta fase no instala ningún paquete externo.**

No hay cambios en `pyproject.toml` de ningún paquete, ni en `uv.lock`, ni ninguna llamada a
`uv add` / `pip install` / `npm install`. Verificado: los 5 criterios de éxito del ROADMAP se
satisfacen íntegramente con la stdlib de Python 3.12 y las dependencias ya lockeadas.

- **Packages removed due to [SLOP] verdict:** ninguno (no se evaluó ninguno — no aplica)
- **Packages flagged as suspicious [SUS]:** ninguno

Si el planner introdujera una dependencia nueva, sería scope creep — el milestone v1.8 se define
explícitamente como "sin superficie nueva" (`REQUIREMENTS.md:4`).

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────── WAVE 0: checkpoint (cero red, cero archivos) ───┐
                    │  gate="blocking-human"  ·  operador transcribe "approved"       │
                    └───────────────────────────────┬─────────────────────────────────┘
                                                    │ (bloquea todo lo de abajo)
                                                    ▼
   ┌────────────────────────── WAVE 1: cambios offline, verificables sin red ─────────────────┐
   │                                                                                          │
   │   main_matriz.py                        scripts/literal_census_33.py                     │
   │   ┌───────────────────────┐  import     ┌──────────────────────────────┐                 │
   │   │ _VENUE_ALLOWLIST      │◄────────────│ (línea 192) gate portado      │                 │
   │   │ _venue_token()        │◄────────────│ + header venue/timestamp      │                 │
   │   └───────────────────────┘  identidad  │ + [--matriz-only | ext. call] │                 │
   │              ▲                 (is)     └──────────────────────────────┘                 │
   │              │                                        ▲                                   │
   │   verification/test_literal_census_venue_gate.py ──────┘                                   │
   │        · 13 casos: sufijo hostil, userinfo, producción, basura                             │
   │        · aserción AST: ningún `in`/`not in` sobre literal string                           │
   │        · identidad: census._venue_token is main_matriz._venue_token                        │
   │              │                                                                             │
   │              └──► .github/workflows/ci.yml:79-92  (allowlist explícita) ◄── SIN ESTO,     │
   │                                                                           EL TEST ES INERTE│
   │   verification/mutation_gate.py  ── NO SE TOCA ── blob 6bdaec00… (criterio 4)              │
   └──────────────────────────────────────────┬───────────────────────────────────────────────┘
                                              │ (los 4 gates de CI verdes)
                                              ▼
   ┌───────────────────── WAVE 2: corridas en vivo (orden estricto) ──────────────────────────┐
   │                                                                                          │
   │  (a) uv run python main_higyrus.py                                                       │
   │        DNS ──gaierror──► httpx.ConnectError ──► _vendor_unreachable = True                │
   │        └─► stdout: "SKIPPED higyrus-client: … — LIVE-HIGY-33"  (main_verify._ENV_SKIP)     │
   │        └─► write_run_evidence() ──► .planning/verification/run-evidence/higyrus-client.json│
   │                                     {captured_at: <HOY>, probes_executed: 0, skipped: …}   │
   │        └─► sys.exit(0)                                                                     │
   │                                                                                            │
   │  (b) censo matriz (SÓLO matriz — D-04)                                                     │
   │        Client() ─► base_url=bbsa ─► _venue_token() = "bbsa"  ✅ pasa el gate                │
   │        ├─ get_segments / get_all_instruments / get_instruments_details                      │
   │        └─ get_active_orders / get_all_orders        (PRIMARY_ACCOUNT presente)              │
   │              cada raw ──► capture("matriz", …) ──► captures/ (gitignored)                   │
   │              cada raw ──► collect_paths(_MATRIZ_KEYS) ──► _report() ──► stdout               │
   │                                                                                            │
   │  (c) uv run python main_market_data.py     (driver completo — no tiene flags)               │
   │        probe_instruments_sync  raw@975 ──► capture(...) ──► lectura fresca /instruments      │
   │        probe_segments_sync     raw@1004 ─► capture(...) ──► lectura fresca /segments         │
   │        _write_schema_snapshot ──► NO sobrescribe el baseline 2026-07-31 (D-25)               │
   └──────────────────────────────────────────┬───────────────────────────────────────────────┘
                                              ▼
   ┌───────────────── WAVE 3: rename condicional + artefactos ────────────────────────────────┐
   │  si (a) dio SKIPPED  ──►  LIVE-HIGY-33 → LIVE-HIGY-42  (sólo sitios VIVOS; ver inventario) │
   │  42-CENSUS.md: header venue+timestamp, 5 campos, D-lock (b) reafirmado                     │
   │  marca explícita: baseline 2026-07-31 NO AUTORITATIVO para SHAPE-01                        │
   └────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 1: Single source por import, no por pin test

**What:** Cuando dos sitios deben compartir una política, el segundo **importa** al primero en vez
de re-declararla y testear igualdad.
**When to use:** Siempre que la divergencia entre copias sería un fallo de seguridad silencioso.
**Why it's better here:** Un pin test de `==` detecta la divergencia *después* de que alguien la
introdujo, y sólo si el test corre en CI (que, en `verification/`, no es automático — ver Pitfall 2).
Un import la hace imposible. El test pasa de ser un *detector* a ser un *pin de identidad*
(`assert a is b`), que es una aserción mucho más fuerte y que no puede pasar por la razón
equivocada.

### Pattern 2: Gate antes del login, no después

**What:** El chequeo de venue corre **antes** de cualquier request y antes de `login()`.
**Where:** Ya es la forma actual — `census_matriz()` líneas `190-201`: construye el `Client`
(que no hace IO), lee `_state.base_url`, decide, y si sale `_skip()` cierra el cliente sin haber
emitido nada. El docstring de la función (`176-180`) lo declara explícitamente: *"un SKIP no debe
costar ni un round trip contra un host fuera de política"*.
**Preservar:** el port D-01 cambia la *condición*, no la *posición*. Mover el gate después del
login sería una regresión de seguridad aunque el predicado fuera correcto.

### Pattern 3: Dos gates independientes (lectura vs. mutación)

`_venue_token` / `_VENUE_ALLOWLIST` gobierna **lectura** y admite bbsa.
`verification/mutation_gate.py::_SANDBOX_HOST` gobierna **mutación** y es remarkets-only.
Son deliberadamente distintos: ampliar el primero deja el order entry fail-closed bajo bbsa **sin
cambio de código** (T-39-02). Criterio 4 pinnea esto como byte-identidad.

### Pattern 4: Aserción por AST, no por grep

`test_no_substring_membership_check_over_a_host_literal` (líneas `247-268`) usa `ast.walk` porque
el comentario que documenta *por qué* el chequeo viejo era inseguro **cita el código viejo**, y un
grep no distingue la cita del código vivo. Este es el patrón correcto para "esta forma no puede
volver". El port a `literal_census_33.py` hereda el mismo problema: el docstring del script
(líneas `38-44`) menciona "remarkets-only" en prosa.

### Anti-Patterns to Avoid

- **`endswith` / `in` "rápido" para el gate:** deja pasar `…bbsa.matrizoms.com.ar.attacker.example`.
  Es exactamente la debilidad que la Phase 39 D-02 removió y que el criterio 1 exige falsificar.
- **Re-declarar el allowlist en el script:** contradice D-01 y crea la tercera copia de la política.
- **Mover el gate después de `Client()`/`login()`:** convierte un SKIP en un round trip contra un
  host fuera de política.
- **Agregar el test bajo `verification/` sin la línea de `ci.yml`:** el test es INERTE (WR-01).
- **Usar `python -c` en un `<verify>` que necesite credenciales:** P-10 — reporta credenciales
  ausentes fabricadas y apunta el `Client()` a **remarkets** en vez de bbsa.
- **Renombrar `LIVE-HIGY-33` en artefactos históricos congelados:** rompe el guard de
  `test_cycle_closure_phase33.py:250` y viola la premisa de la Phase 41. Ver § Runtime State Inventory.
- **Tratar el censo como licencia para promover a `Literal`:** D-lock (b) de la Phase 29 sigue
  vigente. Criterio 3 lo dice explícitamente.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decidir si un host es seguro | Un `if` nuevo, un `endswith`, un regex de hostname | `main_matriz._venue_token()` **importado** | Ya maneja: sin esquema, userinfo, trailing slash, URL imparseable, `host is None`. 13 casos ya pinneados |
| Timestamp de la corrida de higyrus | Un `print(datetime.now())` en el driver | `write_run_evidence()` | Ya escribe `captured_at` UTC ISO y **reemplaza** el envelope (T-39-12) |
| Volcado de payload crudo | Un `open().write(json.dumps())` nuevo | `verification.capture.capture()` | Único hogar legal del wire crudo: staging gitignored (C-4 / D-11 / T-33-32) |
| Clasificar el veredicto del driver | Parsear stdout con un regex propio | `main_verify._ENV_SKIP` (importado) | El patrón `^SKIPPED \S.*:` es load-bearing; re-declararlo es la tercera copia |
| Extraer valores distintos del wire | Un walker nuevo | `collect_paths(node, keys)` | Ya recolecta **por path**, no por nombre suelto — `Segment.marketId` e `InstrumentId.marketId` no se mezclan. Y tiene `--selftest` que prueba que no es un canal muerto |
| Renderizar las líneas de print del driver a su peor caso | Un grep sobre el fuente | El helper AST de `test_main_matriz_skip_line_shape.py:53-136` | Ya sustituye un valor hostil en cada hueco de f-string y falla si algún print es no-analizable |

**Key insight:** Cada uno de estos ya existe porque una fase anterior lo construyó *después* de que
la versión hand-rolled fallara. Todo lo que esta fase necesita ya está escrito; el trabajo es de
**cableado y orden**, no de construcción.

## Runtime State Inventory

> Esta fase **sí** es una fase de rename (D-06: `LIVE-HIGY-33` → `LIVE-HIGY-42`). Inventario
> completo de estado que un grep de archivos no encuentra por sí solo.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | `.planning/verification/run-evidence/higyrus-client.json:9` — archivo **committeado en git** cuyo campo `skipped` contiene el literal `"vendor host unreachable (DNS) — LIVE-HIGY-33"` y `captured_at: 2026-08-30T02:41:21` | **Se regenera solo**: la corrida D-05 lo sobrescribe con `_VENDOR_UNREACHABLE_EVIDENCE` (ya renombrado) y `captured_at` fresco. **No editar a mano** — hacerlo antes de la corrida produciría evidencia fabricada. El orden importa: renombrar la constante → correr el driver → commitear el JSON regenerado |
| **Live service config** | **Ninguno.** No hay servicios externos con configuración fuera de git. Los 3 vendors involucrados (higyrus, MATBA ROFEX bbsa, market-data/Auth0) son consumidos, no configurados por este repo. Verificado: no hay n8n/Datadog/Cloudflare/Tailscale en el repo |
| **OS-registered state** | **Ninguno.** No hay tareas programadas, servicios de systemd/launchd, ni procesos pm2. Los drivers se invocan a mano vía `uv run`. Verificado: sin referencias en `.github/`, sin archivos `.plist`/`.service` |
| **Secrets/env vars** | **Ninguno afectado por el rename.** Los 4 `.env` involucrados usan nombres de variables que no contienen `LIVE-HIGY`. Verificado: claves de `higyrus-client/.env` = `HIGYRUS_{BASE_URL,CLIENT_ID,PASSWORD,USER,SAMPLE_*}`, `VERIFY_HIGYRUS_BAD_CREDS` |
| **Build artifacts** | **Ninguno.** Nada se compila ni se instala; el rename es de strings en scripts de raíz y tests, ninguno empaquetado. `packages/higyrus-client` **no cambia de versión** en esta fase |

### Mapa de sitios de `LIVE-HIGY-33` — RENOMBRAR vs. NO TOCAR

> **Este es el hallazgo de mayor riesgo del rename.** CONTEXT.md D-06 dice "~8 archivos de test
> que pinnean el string". El conteo real es **11 ocurrencias en 6 archivos vivos**, y **una de
> ellas NO debe renombrarse** porque asevera sobre un artefacto histórico congelado.

**RENOMBRAR (estado vivo, forward-looking):**

| Archivo | Línea | Contenido |
|---------|-------|-----------|
| `main_higyrus.py` | `245` | `_VENDOR_UNREACHABLE_SKIP_LINE` (constante) |
| `main_higyrus.py` | `254` | `_VENDOR_UNREACHABLE_EVIDENCE` (constante) |
| `main_matriz.py` | `163` | `_CYCLE_CLOSURE_DESTINATION["higyrus-client"]` |
| `verification/test_main_higyrus_skip_line_shape.py` | `170` | `assert line.endswith("LIVE-HIGY-33")` |
| `verification/test_main_verify_classification.py` | `79` | `assert line.endswith("LIVE-HIGY-33")` |
| `verification/test_run_evidence.py` | `211`, `217`, `218` | envelope sintético + 2 asserts |
| `verification/test_cycle_closure_phase33.py` | `385`, `392` | `_cycle_closure_verdict` con envelope sintético + `detail.count(...) == 1` |
| `verification/test_cycle_closure_phase33.py` | `482` | `assert _cycle_closure_destination("higyrus-client") == "LIVE-HIGY-33"` |

**NO TOCAR — historia congelada (renombrar acá rompe el guard y viola la premisa de la Phase 41):**

| Archivo | Línea | Por qué |
|---------|-------|---------|
| `verification/test_cycle_closure_phase33.py` | **`250-252`** | ⚠️ Asevera `"LIVE-HIGY-33" in census` donde `census = _CENSUS.read_text()` y `_CENSUS` (líneas `91-98`) apunta a `.planning/milestones/v1.6-phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-CENSUS.md` — un **artefacto histórico congelado de v1.6**. El string en ese documento describe lo que era verdad el 2026-08-27 y debe quedarse. Renombrar la aserción la haría fallar; renombrar el documento falsificaría historia |
| `.planning/milestones/**` (todo) | — | Árbol congelado de v1.6/v1.7. La Phase 41 auditó contra él |
| `.planning/PROJECT.md` | `29`, `78`, `278`, `417` | Párrafos históricos de fases completadas (v1.6 F33, v1.7 F39) |
| `.planning/STATE.md` | `171`, `241`, `405`, `412`, `541`, `542` | Log de decisiones — inmutable por convención |

**AMBIGUO — decisión explícita del planner (recomendación entre paréntesis):**

| Archivo | Línea | Naturaleza | Recomendación |
|---------|-------|------------|---------------|
| `main_higyrus.py` | `1886`, `2052` | Comentarios en prosa que citan el bloqueo **vigente** | **Renombrar** — describen el presente, no el pasado |
| `packages/higyrus-client/tests/test_deep_chain_edges.py` | `5` | Docstring que cita el plan 39-01 | **No tocar** — cita un plan histórico por nombre |
| `verification/test_main_higyrus_deep_chain.py` | `36` | Docstring: *"the inherited blocker `LIVE-HIGY-33` is still standing"* | **Renombrar o reescribir** — afirma un estado presente que esta fase cambia |
| `.planning/ROADMAP.md` | `210` | Entrada de backlog **abierta** | **Renombrar + anotar** el resultado de esta corrida |
| `.planning/PROJECT.md` | `174`, `286` | "Next milestone" / requisito abierto | **Renombrar** — son forward-looking |
| `.planning/research/ARCHITECTURE.md`, `PITFALLS.md` | varias | Research de v1.8, describe HEAD | Coherente actualizarlo; **no bloqueante** |

**Verificación sugerida para el `<verify>` del rename:**
```bash
# El guard de historia congelada sigue verde (prueba que 33-CENSUS.md no se tocó):
uv run pytest -q verification/test_cycle_closure_phase33.py
# Ninguna constante VIVA quedó con el nombre viejo:
! grep -n "LIVE-HIGY-33" main_higyrus.py main_matriz.py
```

## Common Pitfalls

### Pitfall 1: LIVE-01 marcado "resuelto" (o "igual de bloqueado") sobre una causa raíz distinta

**What goes wrong:** Dos errores simétricos.
*(a) Falso "sigue bloqueado, misma causa":* si el host empieza a resolver pero **cuelga** (VPN
half-open, firewall que dropea), el fallo es `httpx.ConnectTimeout`, que —**verificado en httpx
0.28.1 en esta sesión**— NO es subclase de `ConnectError`. Cae en `_RESIDUAL_PROBE_EXCEPTIONS`,
produce un `AUTH OPEN` en un ledger versionado, y `main_verify.py` lo clasifica `FINDING`/`FAILED`,
no `SKIPPED`. Quien lea el resumen ve "sigue fallando" y re-estampa la misma causa sobre evidencia
que no la sostiene.
*(b) Falso "resuelto":* que el DNS resuelva **no es** resolución. El entregable real de
`LIVE-HIGY-33` son los **22 triples sin contrastar** (`Movimiento` 9, `PosicionValuada` 11,
`Posicion` 2) del piso de `29-SIZING.md`.

**Why it happens:** La entrada del backlog es prosa ("DNS aún sin resolver"), así que re-sondear
se siente como una pregunta sí/no. No lo es: codifica una **clase de excepción medida** y un
**objetivo numérico de censo**.

**How to avoid:**
- Fijar el criterio de aceptación *antes* de la corrida como dos hechos independientes: (a) el
  tipo/errno de excepción **de esta corrida**, transcrito verbatim, comparado contra `gaierror`;
  (b) los 22 triples contrastados, o una declaración explícita de que no lo fueron.
- **Decidir antes de correr** si se amplía la rama a `ConnectTimeout` (cerrando el gap WR-02) o
  si se re-declara fuera de alcance. **No** descubrirlo a mitad de corrida y parchear el
  clasificador para que la salida se lea linda.
- **Nota de alcance:** el criterio 2 del ROADMAP pide un *resultado medido*, no los 22 triples.
  El planner debe decir esto explícitamente en el reporte para que nadie lea "LIVE-01 cumplido"
  como "LIVE-HIGY-33 cerrado". Son cosas distintas.

**Warning signs:** Cualquier frase "re-sondeado, sigue bloqueado" sin un tipo de excepción pegado.
Una clasificación `FINDING`/`FAILED` en higyrus donde los dos milestones anteriores dieron `SKIPPED`.
`[CITED: .planning/research/PITFALLS.md:36-78]` `[VERIFIED: httpx 0.28.1 MRO]`

### Pitfall 2: El lock del criterio 1 queda verde en local pero INERTE en CI

**What goes wrong:** `verification/` tiene **52** archivos `test_*.py`; `ci.yml:79-92` corre **12**,
en una **allowlist explícita mantenida a mano**. `pyproject.toml:106` incluye `verification` en
`testpaths`, así que `pytest` local los levanta a todos automáticamente — pero CI pasa paths
explícitos que pisan `testpaths`. Los dos entornos discrepan **por diseño**, y la discrepancia es
invisible desde un verde local.

**Why it happens:** El comentario sobre la allowlist (`ci.yml:75-78`) dice literalmente *"cada
guard nuevo se agrega a esta lista a mano"*, porque `verification/` arrastra rojo pre-existente
(HARN-VERIF-01). Es fácil de olvidar y no hay nada que lo recuerde.

**How to avoid:** La task que crea el test de spoofing debe **también** editar `ci.yml` y su
`<verify>` debe probarlo:
```bash
grep -c "verification/test_literal_census_venue_gate.py" .github/workflows/ci.yml
```
Precedente exacto: el `<automated>` de `39-01-PLAN.md:251` ya usa
`grep -c test_main_matriz_skip_line_shape.py .github/workflows/ci.yml`.

**Warning signs:** Un SUMMARY que reporta `pytest ... passed` sin mencionar `ci.yml`. Un plan que
cita `testpaths` como prueba de cobertura de CI.
`[VERIFIED: ci.yml:79-92 leído; ls verification/test_*.py]` `[CITED: PITFALLS.md:209-238]`

### Pitfall 3: El censo se lee como licencia para promover a `Literal`

**What goes wrong:** El censo mide *qué valores manda el vendor*. Es una medición. El **D-lock (b)**
firmado de la Phase 29 dice que los campos RESPONSE **nunca** se cierran como `Literal` en esta
línea de trabajo. Un censo que vuelve con un conjunto chico y prolijo invita exactamente a la
promoción que el lock prohíbe — y la promoción haría fatal un valor no visto del vendor.

Dos trampas secundarias en el mismo ítem:
- **Sobre-generalización de venue.** `api.bbsa.matrizoms.com.ar` es un sandbox **distinto** de
  remarkets. Un vocabulario medido en bbsa es el vocabulario **de bbsa**. Reportarlo como "el
  vocabulario RESPONSE de matriz" sobre-generaliza desde una sola venue. *Esta es la razón exacta
  por la que el criterio 3 exige venue en el header.*
- **Una corrección adeudada con dueño nombrado.** `29-DLOCK-RESPONSE-LITERAL.md:140-142` afirma que
  el stream de divergencias es el mecanismo del censo; no lo es (el branch `Literal` de
  `walk_field` retorna temprano con `literal_enforced=False` y nunca llama al sink — ver
  `matriz_client/_decode.py:541`). Ese párrafo está en un artefacto **firmado**, así que la
  corrección pertenece al firmante, **no** a quien corra el censo.

**How to avoid:** Escribir la salida del censo como un inventario de valores con **venue +
timestamp en el header**, y una línea explícita de que D-lock (b) sigue en vigor y este artefacto
no lo revoca. Rutear la corrección de `29-DLOCK` como su propia edición firmada por el operador.
`[CITED: .planning/research/PITFALLS.md:129-166]` `[VERIFIED: _decode.py:541]`

### Pitfall 4: El checkpoint colapsa bajo `mode: yolo` + `auto_advance: true`

**What goes wrong:** `.planning/config.json` tiene `"mode": "yolo"` y
`"workflow.auto_advance": true`. Un `<task type="checkpoint" gate="blocking">` se **auto-aprueba**.
El bug de autoría del gate ya se coló **dos veces** en este proyecto (documentado en
`ROADMAP.md:54` y en el texto de PUB-01: *"nunca `gate="blocking"`, que ya se auto-aprobó dos veces
bajo yolo"*).

**How to avoid:** El atributo literal es `gate="blocking-human"` y el tipo es
`checkpoint:human-verify`. Precedente verbatim en
`39-01-PLAN.md:87` → `<task type="checkpoint:human-verify" gate="blocking-human">`, con
`<files>(ninguno — checkpoint humano bloqueante, no escribe código)</files>`,
`<resume-signal>` pidiendo "approved", y `<acceptance_criteria>` que exige transcripción verbatim
en el SUMMARY. El `<what-built>` de ese precedente declara explícitamente que yolo/auto_advance
"NO aplican acá".

**Warning signs:** `gate="blocking"` sin `-human`. Un checkpoint con archivos en `<files>`.
Un SUMMARY sin la respuesta del operador transcrita.
`[VERIFIED: config.json + 39-01-PLAN.md:87-141]`

### Pitfall 5: El criterio 3 pide un header que el censo no emite — y nadie lo nota hasta la verificación

**What goes wrong:** El criterio 3 exige *"con **venue y timestamp en el encabezado**"*.
`_report()` (`literal_census_33.py:154-163`) imprime una línea por path, sin encabezado de ningún
tipo. **Ningún D-lock de CONTEXT.md menciona esto.** Un plan derivado sólo de CONTEXT.md portaría
el gate, correría el censo, y produciría una salida que falla el criterio 3 por una razón
puramente mecánica descubierta en `/gsd-verify-work`.

**How to avoid:** Tratar el header como un **cambio de código explícito** en la misma task del port
D-01. El venue no se hardcodea: sale de `_venue_token(base)`, que el port ya calcula. Ver
§ Code Examples → "Header del censo".

**Warning signs:** Una task de censo cuyo `<action>` sólo dice "reemplazar el gate". Un
`<acceptance_criteria>` que no menciona el header.
`[VERIFIED: lectura de _report()]` `[CITED: ROADMAP.md:108]`

### Pitfall 6: La evidencia del criterio 5 es gitignored y sin fecha adentro

**What goes wrong:** `capture()` escribe a `.planning/verification/captures/`, que está en
`.gitignore:53`. Y `main_market_data.py` **no** llama `write_run_evidence` (verificado: no existe
`run-evidence/market-data-client.json`). Así que la "lectura fresca del wire" del criterio 5
termina siendo: dos archivos JSON, en un directorio ignorado por git, sin `captured_at` adentro,
cuya única fecha es el mtime del filesystem. Si la Phase 43 corre en otro clone, otro worktree, o
después de un `git clean -xdf`, **la evidencia no existe**.

Y el segundo medio-criterio —*"el baseline committeado del 2026-07-31 queda explícitamente marcado
como no-autoritativo"*— no lo satisface ningún archivo gitignored: requiere una marca **committeada**.

**How to avoid (esto es D-08, y es la decisión de planning más consecuente de la fase):**
- Envolver el payload: `capture(pkg, endpoint, {"captured_at": <UTC ISO>, "base_url": …, "payload": raw})`,
  espejando la forma que `_write_schema_snapshot` ya usa (`main_market_data.py:474-480`). Barato,
  y resuelve la fecha.
- **Y además** producir un artefacto **committeado y PII-free** que la Phase 43 pueda citar: p.ej.
  un `42-WIRE-READ.md` con `captured_at`, venue, conteo de filas y el `schema_of(raw)` (keys+types,
  PII-free por construcción — es lo mismo que el baseline guarda), más la línea explícita de que
  `get-instruments.json`/`get-segments.json` (2026-07-31) **no son autoritativos** para SHAPE-01.
- **Nunca** commitear el payload crudo — viola C-4 / D-11 / la premisa entera de `captures/`.

**Warning signs:** Un plan que cita `captures/market-data-instruments.json` como entregable del
criterio 5 sin nada committeado al lado. Una Phase 43 que arranca con "no encuentro la lectura
fresca".
`[VERIFIED: .gitignore:53, capture.py:42-51, ausencia de run-evidence/market-data-client.json]`
`[CITED: PITFALLS.md:320-348]`

### Pitfall 7: El rename de D-06 pisa historia congelada

Cubierto en detalle en § Runtime State Inventory. Resumen: `test_cycle_closure_phase33.py:250`
asevera contra `33-CENSUS.md` en `.planning/milestones/v1.6-phases/` — **no** es un sitio de
rename. Renombrarlo (o renombrar el documento) falsifica historia y rompe la premisa de la Phase 41.

### Pitfall 8: `python -c` en un `<verify>` que necesita credenciales

Cubierto en § Trampa de resolución de `.env` (P-10). Bajo `-c`, `find_dotenv` cae a `os.getcwd()`,
no encuentra `.env`, y `Client()` apunta al **default remarkets**. Medido en esta sesión: la misma
lógica da `remarkets`/`False` bajo `-c` y `bbsa`/`True` desde un archivo `.py`.

## Code Examples

### Port del gate (criterio 1) — la forma que hace testeable la identidad

```python
# scripts/literal_census_33.py — DESPUÉS del sys.path.insert de las líneas 68-70
from verification.capture import capture  # noqa: E402
from main_matriz import _VENUE_ALLOWLIST, _venue_token  # noqa: E402
```

La forma `from main_matriz import ...` (en vez de `import main_matriz` + uso calificado) es la que
habilita el pin de identidad de D-01:

```python
assert scripts.literal_census_33._venue_token is main_matriz._venue_token
assert scripts.literal_census_33._VENUE_ALLOWLIST is main_matriz._VENUE_ALLOWLIST
```

Reemplazo del gate en `census_matriz()` (línea 192):

```python
    client = Client()
    base = client._state.base_url
    venue = _venue_token(base)          # ← igualdad exacta de hostname, fail-closed
    if venue is None:
        # No se imprime la URL: el criterio de no-fuga del pre-flight manda acá también.
        _skip(
            "matriz-client",
            "base URL fuera del allowlist D-MATZ-33 (la verificación es sandbox-only)",
        )
        with contextlib.suppress(Exception):
            client.close()
        return False
```

> **Nota de ruff:** `E501` está ignorado globalmente (`pyproject.toml`), pero `E402` **no** está
> en `per-file-ignores` — el `# noqa: E402` es obligatorio, igual que en la línea 72 existente.
> `[VERIFIED: pyproject.toml:72-74]`

### Header del censo (criterio 3) — el gap que CONTEXT.md no cubre

```python
import datetime as dt

def _census_header(venue: str) -> None:
    """Venue + timestamp: sin esto el censo sobre-generaliza desde una sola venue (Pitfall 3)."""
    stamp = dt.datetime.now(dt.UTC).isoformat()
    print(f"CENSUS-HEADER venue={venue} captured_at={stamp}")
    print(
        "CENSUS-DLOCK: D-lock (b) de la Phase 29 SIGUE EN VIGOR — los campos RESPONSE "
        "NO se cierran como Literal. Este inventario es una MEDICIÓN de una venue, "
        "no una autorización de promoción."
    )
```

Llamado inmediatamente después de resolver `venue` y **antes** del primer request. El token sale de
`_venue_token(base)` — nunca hardcodeado — así que el header no puede mentir sobre contra qué se midió.

### Test de falsificación (criterio 1) — tabla de casos verificada como ya existente

`verification/test_main_matriz_skip_line_shape.py:218-244` ya ejercita estos 13 casos contra
`_venue_token`. El test nuevo los reusa contra el uso importado del script:

```python
# Source: verification/test_main_matriz_skip_line_shape.py:218-244 (verbatim en HEAD)
@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("api.remarkets.primary.com.ar", "remarkets"),
        ("https://api.remarkets.primary.com.ar", "remarkets"),
        ("api.bbsa.matrizoms.com.ar", "bbsa"),
        ("https://api.bbsa.matrizoms.com.ar", "bbsa"),
        ("https://api.bbsa.matrizoms.com.ar/", "bbsa"),          # trailing slash
        ("api.bbsa.matrizoms.com.ar.attacker.example", None),     # ← sufijo hostil (criterio 1)
        ("https://api.bbsa.matrizoms.com.ar.attacker.example", None),
        ("https://api.bbsa.matrizoms.com.ar@attacker.example", None),   # ← userinfo
        ("https://api.remarkets.primary.com.ar@attacker.example", None),
        ("api.primary.com.ar", None),                             # ← producción
        ("https://api.primary.com.ar", None),
        ("", None),                                               # ← fail-closed
        ("https://[oops/api", None),
    ],
)
def test_venue_token_resolves_by_exact_hostname(base_url, expected) -> None:
    assert main_matriz._venue_token(base_url) == expected
```

Y la aserción AST anti-substring, re-apuntada al script (`:247-268` en el original):

```python
_TARGET = _REPO_ROOT / "scripts" / "literal_census_33.py"

def test_no_substring_membership_check_over_a_host_literal() -> None:
    """El gate viejo `if "remarkets" not in base:` no puede volver.

    Por AST, no por grep: el docstring del script cita "remarkets-only" en prosa y
    un grep no distingue la cita del código vivo.
    """
    offenders: list[int] = []
    tree = ast.parse(_TARGET.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(op, ast.In | ast.NotIn) for op in node.ops):
            continue
        if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
            offenders.append(node.lineno)
    assert not offenders, (
        f"literal_census_33.py: pertenencia de substring sobre un literal en {offenders}; "
        f"el gate debe usar igualdad exacta de hostname."
    )
```

> ⚠️ **Cuidado con el falso positivo:** `main()` línea 355 tiene `if "--selftest" in argv:` — es un
> `In` con `ast.Constant` string a la izquierda. **Ese test fallaría sobre el script tal cual está.**
> El original no lo sufre porque `main_matriz.py` no tiene esa forma. Dos salidas: (a) restringir el
> walk al cuerpo de `census_matriz` (`ast.walk` sobre el `FunctionDef`), o (b) exigir además que el
> lado derecho sea un `Name` (`base`), no un argv. El planner debe elegir una explícitamente —
> descubrirlo en ejecución produce el reflejo de "relajar la aserción", que es lo contrario de lo
> que el criterio 1 quiere. `[VERIFIED: literal_census_33.py:355]`

### Envelope timestampeado para `capture()` (D-08, criterio 5)

```python
# main_market_data.py — probe_instruments_sync, tras obtener `raw` (línea ~980)
capture(
    "market-data",
    "wire-instruments-42",
    {
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "endpoint": _ENDPOINT_TEMPLATES["get_instruments"],
        "client_function": "get_instruments",
        "base_url": base_url,
        "n_rows": len(raw) if isinstance(raw, list) else None,
        "payload": raw,
    },
)
```
Forma espejada de `_write_schema_snapshot` (`main_market_data.py:474-480`), que ya usa exactamente
ese envelope. `dt` ya está importado como `datetime as dt` en el driver.

### Línea de CI (criterio 1, Pitfall 2)

```yaml
# .github/workflows/ci.yml — dentro del bloque `run:` de las líneas 79-92
            verification/test_cycle_closure_phase33.py \
            verification/test_literal_census_venue_gate.py
```
Con `<verify><automated>` que lo pruebe:
```bash
grep -c "verification/test_literal_census_venue_gate.py" .github/workflows/ci.yml
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `if "remarkets" not in base:` (substring) | `_venue_token()` por igualdad exacta de hostname vía `urlsplit` | Phase 39 D-02 (2026-08-30) en `main_matriz.py` | **`scripts/literal_census_33.py` sigue en la forma vieja** — ese es el trabajo de esta fase |
| `httpx.ConnectError` → `AUTH OPEN` finding + exit 0 clasificado `RAN` | `_vendor_unreachable` → línea `SKIPPED` a stdout + envelope reescrito + exit 0 | Phase 39 D-01 | Un vendor caído ya no se lee como corrida limpia. **`ConnectTimeout` sigue sin cubrir** (WR-02) |
| Sobre de evidencia que sobrevive a una corrida saltada | `write_run_evidence()` **reemplaza** siempre | Phase 39 D-09 / T-39-12 | D-05 funciona: la corrida produce un `captured_at` fresco por construcción |
| Allowlist duplicado + pin test de `==` | Import directo + pin de identidad `is` | Esta fase (D-01) | Divergencia estructuralmente imposible |

**Deprecado / desactualizado:**
- El backlog `ROADMAP.md:210` (entrada `LIVE-MATZ-33`) **sobreestima** el estado: afirma que el
  script "ya tiene el gate listo para correr contra bbsa". **Verificado falso en HEAD.** El ROADMAP
  ya se auto-corrige en la nota de sizing (`ROADMAP.md:52`), pero la entrada de backlog no se
  actualizó. Vale corregirla en el cierre de esta fase.
- `29-DLOCK-RESPONSE-LITERAL.md:140-142` afirma que el stream de divergencias es el mecanismo del
  censo. Es falso (ver Pitfall 3). **Corrección adeudada al firmante, fuera del alcance de esta
  fase** — no la absorba el planner.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Todo | ✓ | 3.12.11 (venv activo) | — |
| uv | Todo | ✓ | 0.9.0 | — |
| httpx | Drivers | ✓ | 0.28.1 | — |
| pytest + plugins | Test del criterio 1 | ✓ | ≥8.3, asyncio/httpx/cov | — |
| git | Pin de byte-identidad (criterio 4) | ✓ | — | — |
| Credenciales matriz (bbsa) | Criterio 3 | ✓ | 4/4 vars, venue = `bbsa` | — |
| **Resolución DNS de higyrus** | Criterio 2 (rama "resuelve y corre") | **✗** | `gaierror [Errno 8]` | **La rama `SKIPPED` + rename D-06 ES el fallback**, y está en el criterio |
| Credenciales higyrus | Criterio 2 | ✓ | 3/3 presentes (irrelevantes: falla antes) | — |
| Credenciales market-data (Auth0) | Criterio 5 | ✓ | 4/4 vars | — |
| Cuenta bbsa con órdenes | Criterio 3, campo `ordType` | **?** | `PRIMARY_ACCOUNT` seteada; si no hay órdenes, `distinct=[]` | **El criterio 3 ya lo admite**: "declara explícitamente qué campo no se pudo medir y por qué" |
| Mercado abierto | Criterio 3 (datos ricos) | **?** | No determinable ahora | Precedente Phase 39: matriz corrió contra mercado cerrado y produjo 7 eslabones nulos **reales** — evidencia válida |

**Missing dependencies with no fallback:** ninguna. Los 5 criterios son alcanzables hoy.

**Missing dependencies with fallback:**
- DNS de higyrus → la rama `SKIPPED` medida es el resultado válido y esperado (criterio 2 la
  contempla explícitamente). **No es un blocker; es el resultado.**
- Órdenes en bbsa / mercado abierto → conjunto vacío declarado con causa (criterio 3 lo admite).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8.3 + pytest-asyncio ≥0.24 + pytest-httpx ≥0.34 |
| Config file | `pyproject.toml:102-121` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run --frozen pytest -q verification/test_literal_census_venue_gate.py` |
| Full suite command | `uv run --frozen pytest -q` (todo `testpaths`) — **pero ver la nota de CI** |
| **Comando que refleja CI** | `uv run pytest -q <las 12 rutas de ci.yml:81-92>` ← este es el que importa |
| Config relevante | `pythonpath = ["."]`, `--import-mode=importlib`, `--strict-markers`, `asyncio_mode="auto"` |
| `mypy` scope | `files = packages/*/src` **solamente** — `scripts/`, `main_*.py`, `verification/` fuera del gate global (`pyproject.toml:97`) |

**Baseline medido en esta sesión (HEAD, pre-cambios):**
```
uv run pytest -q <las 12 rutas de la allowlist de ci.yml>  →  129 passed in 0.55s
```
Éste es el número contra el que el plan debe comparar: **129 → 129 + N**, sin regresiones.
`[VERIFIED: ejecución]`

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| LIVE-02 / crit.1 | El gate rechaza `…bbsa.matrizoms.com.ar.attacker.example` | unit | `uv run pytest -q verification/test_literal_census_venue_gate.py` | ❌ Wave 0 |
| LIVE-02 / crit.1 | El gate rechaza la variante userinfo `…@attacker.example` | unit | ídem | ❌ Wave 0 |
| LIVE-02 / crit.1 | Ambos sitios comparten **una** fuente (`is`, no `==`) | unit | ídem | ❌ Wave 0 |
| LIVE-02 / crit.1 | Ninguna comparación `in`/`not in` sobre literal de host (AST) | unit | ídem | ❌ Wave 0 |
| LIVE-02 / crit.1 | El lock corre en CI (no es inerte) | lint | `grep -c "test_literal_census_venue_gate.py" .github/workflows/ci.yml` | ❌ Wave 0 |
| LIVE-02 / crit.3 | El censo emite venue + timestamp en el header | unit (offline) | extender `--selftest` para aseverar la línea `CENSUS-HEADER` | ❌ Wave 0 |
| LIVE-02 / crit.3 | El walker no es un canal muerto | smoke | `uv run python scripts/literal_census_33.py --selftest` | ✅ (línea 315) |
| LIVE-02 / crit.3 | Valores observados de los 5 campos | manual-only | corrida en vivo contra bbsa | N/A (no automatizable — es la medición) |
| LIVE-01 / crit.2 | El veredicto de higyrus clasifica `SKIPPED`, no `RAN`/`FAILED` | unit | `uv run pytest -q verification/test_main_verify_classification.py verification/test_main_higyrus_skip_line_shape.py` | ✅ (actualizar por rename) |
| LIVE-01 / crit.2 | El sobre lleva causa + destino renombrado | unit | `uv run pytest -q verification/test_run_evidence.py verification/test_cycle_closure_phase33.py` | ✅ (actualizar por rename) |
| LIVE-01 / crit.2 | La historia congelada (`33-CENSUS.md`) NO se tocó | unit | `uv run pytest -q verification/test_cycle_closure_phase33.py` | ✅ (líneas 243-252) |
| LIVE-01 / crit.2 | El re-chequeo dejó evidencia fechada HOY | integration | `python -c` ❌ → usar un `.py`: leer `run-evidence/higyrus-client.json` y aseverar que `captured_at` es de hoy | ❌ Wave 0 (opcional) |
| crit.4 | `mutation_gate.py` byte-idéntico | lint | `test "$(git hash-object verification/mutation_gate.py)" = 6bdaec006cc16f7c8dbfac41701712a9085c691b` | ❌ Wave 0 |
| crit.5 | Lectura fresca de `/instruments` + `/segments`, fechada | integration | verificar existencia + `captured_at` de hoy en el envelope de `captures/` | ❌ Wave 0 |
| Todos | Los 4 gates de CI verdes | lint+type | `uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen mypy && uv run --frozen pytest -q` | ✅ |

### Sampling Rate

- **Per task commit:** `uv run --frozen ruff check . && uv run --frozen pytest -q verification/test_literal_census_venue_gate.py`
- **Per wave merge:** los 12 archivos de la allowlist de `ci.yml` (baseline 129 passed) + `ruff format --check` + `mypy`
- **Phase gate:** los 4 gates completos verdes + `--selftest` PASS + los 3 artefactos en disco (run-evidence de higyrus fechado hoy, censo con header, captures de market-data fechadas)

### Wave 0 Gaps

- [ ] `verification/test_literal_census_venue_gate.py` — cubre criterio 1 (spoofing + identidad + AST)
- [ ] Línea nueva en `.github/workflows/ci.yml:79-92` — sin esto el test es INERTE (Pitfall 2)
- [ ] Aserción del header (`CENSUS-HEADER venue=… captured_at=…`) dentro de `_selftest()` — cubre criterio 3 offline
- [ ] Pin de byte-identidad de `mutation_gate.py` por blob hash — cubre criterio 4 de forma no-vacua
- [ ] Actualización de los 8 pins vivos de `LIVE-HIGY-33` (condicional a D-06) — **sin tocar la línea 250 de `test_cycle_closure_phase33.py`**
- [ ] Framework install: **ninguno** — pytest ya presente y configurado

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: "high"`
> (`.planning/config.json`). Esta fase **es** una fase de seguridad: modifica un control de acceso
> a red antes de emitir tráfico.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No se toca ningún flujo de auth. Los tokens de los 3 vendors se obtienen por los caminos ya verificados |
| V3 Session Management | no | Sin sesiones de usuario |
| V4 Access Control | **yes** | **Núcleo de la fase.** Dos gates independientes: `_venue_token`/`_VENUE_ALLOWLIST` (lectura, admite bbsa) y `mutation_gate._SANDBOX_HOST` (mutación, remarkets-only). Se portan **sin debilitarse**; el segundo queda byte-idéntico |
| V5 Input Validation | **yes** | `urlsplit` + igualdad exacta de hostname + re-parseo como authority puro cuando falta el esquema. Fail-closed ante `ValueError`, `host is None`, o host no listado |
| V6 Cryptography | no | Nada criptográfico. TLS lo maneja httpx |
| V7 Error Handling & Logging | **yes** | T-39-04: las líneas de veredicto **nunca** interpolan hostname ni base URL. `_vendor_unreachable_reason` se setea pero no se imprime ni persiste (D-HIGY-15) |
| V8 Data Protection | **yes** | C-4 / D-11: el payload crudo con PII vive **exclusivamente** en `captures/`, gitignored. Nunca se commitea |
| V14 Configuration | **yes** | Credenciales por `.env` por paquete, nunca commiteadas. `.env.example` como plantilla |

### Known Threat Patterns for esta stack

| Pattern | STRIDE | Standard Mitigation | Estado |
|---------|--------|---------------------|--------|
| **Sufijo de hostname hostil** (`…bbsa.matrizoms.com.ar.attacker.example`) | Spoofing | Igualdad exacta contra un dict, nunca `in`/`endswith` | Mitigado en `main_matriz`; **el port lo lleva al script** — criterio 1 exige el test de falsificación |
| **Userinfo authority confusion** (`https://<host-ok>@attacker.example`) | Spoofing | `urlsplit(...).hostname` extrae el host REAL | Mitigado; ya en los 13 casos parametrizados |
| **URL sin esquema** (formas históricas de `.env`) | Spoofing | Re-parseo como `//{base_url}` | Mitigado en `_venue_token:239-240` |
| **URL imparseable** (`https://[oops/api`) | DoS / bypass | `except ValueError → None` (fail-closed, nunca crash) | Mitigado |
| **Order entry contra una venue no autorizada** | Tampering | Gate de mutación **independiente**, remarkets-only, sin cambio de código | Mitigado por construcción; criterio 4 lo pinnea por blob hash |
| **Leak de hostname/base URL vía veredicto** | Information Disclosure | Líneas SKIPPED como literales de módulo, sin interpolación; probado por AST rendering al peor caso | Mitigado; los tests de shape lo pinnean |
| **PII cruda en git** | Information Disclosure | `capture()` escribe sólo a `captures/`, gitignored | Mitigado. **Riesgo nuevo de esta fase:** un artefacto committeado del criterio 5 no debe llevar payload crudo — sólo `schema_of()` (keys+types) |
| **Widening auto-aprobado bajo `mode: yolo`** | Elevation of Privilege | `gate="blocking-human"` + `checkpoint:human-verify` | **Riesgo activo** — ver Pitfall 4. Ya se coló dos veces en este proyecto |
| **Credenciales expuestas en logs de la corrida** | Information Disclosure | `safe_print` + lista de `secrets` que el driver redacta | Existente en los drivers; no se toca |

**Riesgo residual declarado (heredado de Phase 39 A1):** la seguridad del sandbox
`api.bbsa.matrizoms.com.ar` es una **aserción del operador**, no verificable por máquina. Es la
mayor dependencia de confianza de esta fase y debe re-declararse en el `<how-to-verify>` del
checkpoint.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | La seguridad y el carácter no-producción del sandbox `api.bbsa.matrizoms.com.ar` (aserción del operador de 2026-08-29, heredada de Phase 39 D-02) | Security Domain | Tráfico de lectura contra un host que no es el sandbox acordado. **Es la razón de ser del checkpoint D-02** |
| A2 | El DNS de higyrus seguirá sin resolver al momento de la ejecución (medido hoy 2026-08-31; podría cambiar entre research y run) | Pre-flight Medido | Si resuelve, D-06 (rename) es moot y el driver corre 18 probes. CONTEXT.md ya lo contempla como discreción del planner. **Riesgo bajo: el plan no debe ramificar por adelantado** |
| A3 | La cuenta bbsa tiene órdenes suficientes para poblar `ordType` en `get_active_orders`/`get_all_orders` | Environment Availability | `distinct=[]` para `ordType` → criterio 3 se satisface por la vía "declara qué campo no se pudo medir y por qué", no por la vía de medición |
| A4 | Correr `main_market_data.py` completo (única forma bajo D-07, no tiene flags) no produce efectos indeseados más allá del churn del ledger de findings (113 KB) y las 22 duplicaciones cosméticas de schema drift que HARN-01 arreglará en Phase 45 | Open Questions Q3 | Un diff grande y ruidoso en `market-data-client-findings.md`. **No es lossy** — el ROADMAP:55 declara explícitamente que el harness de hoy es "ruidoso pero no lossy" y por eso lo vivo va antes que la limpieza |
| A5 | Renombrar los comentarios en prosa de `main_higyrus.py:1886,2052` es deseable (describen el bloqueo vigente, no historia) | Runtime State Inventory | Inconsistencia cosmética. Bajo impacto; el planner puede decidir lo contrario |
| A6 | Los ~8 archivos de test que CONTEXT.md D-06 lista corresponden a las 11 ocurrencias en 6 archivos vivos que este research enumeró | Runtime State Inventory | Si CONTEXT.md contaba archivos que este research no encontró, el rename quedaría incompleto. **Mitigado**: el research enumeró exhaustivamente con `grep -rn` excluyendo `.git`/`.venv`/`milestones` |

**A2 y A3 son no-determinismos del entorno externo**, explícitamente contemplados por CLAUDE.md
(*"resultados pueden variar por horario de mercado, datos disponibles o rate limits"*) y por el
criterio 3 del ROADMAP. No requieren confirmación del usuario antes de planificar.

**A1 requiere re-confirmación del operador** — ése es exactamente el checkpoint D-02.

## Open Questions

1. **Q1 — ¿Cuál es la forma exacta del artefacto committeado del criterio 5? (D-08)**
   - *Lo que sabemos:* `capture()` escribe a un directorio gitignored, sin timestamp interno.
     `_write_schema_snapshot` no puede refrescar (write-once, D-25). `main_market_data.py` no
     escribe run-evidence. El criterio 5 exige además marcar el baseline 2026-07-31 como
     no-autoritativo, lo cual requiere una marca **committeada**.
   - *Lo que no está claro:* si el planner elige (a) sólo envelope + cita en el SUMMARY, o (b)
     envelope + un `42-WIRE-READ.md` committeado con `schema_of()` PII-free.
   - *Recomendación:* **(b)**. Es la única forma en que la Phase 43 puede citar la evidencia sin
     depender del working tree del ejecutor, y la única que satisface la mitad "baseline marcado
     como no-autoritativo". El costo adicional es una task chica.

2. **Q2 — ¿Se amplía la rama `_vendor_unreachable` a `httpx.ConnectTimeout` (gap WR-02)?**
   - *Lo que sabemos:* verificado que `ConnectTimeout` NO es subclase de `ConnectError` en httpx
     0.28.1, así que un host que resuelve-pero-cuelga produce `FINDING`/`FAILED`, no `SKIPPED`.
     La decisión de alcance ya está documentada en el código como deliberada (WR-02, Phase 39).
   - *Lo que no está claro:* si esta fase la cierra o la re-declara fuera de alcance.
   - *Recomendación:* **decidirlo antes de correr, y por escrito.** Como el DNS medido hoy no
     resuelve, `ConnectTimeout` es materialmente improbable en esta corrida — lo que aconseja
     **re-declararlo fuera de alcance con destino nombrado** en vez de ampliar la rama sin
     evidencia de que haga falta. Lo que Pitfall 1 prohíbe es *descubrirlo a mitad de corrida y
     parchear el clasificador para que la salida se lea linda*.

3. **Q3 — ¿Correr `main_market_data.py` entero, o un script targeted?**
   - *Lo que sabemos:* D-07 está LOCKED sobre instrumentar `main_market_data.py`. El driver no
     tiene flags (`main()` sin argv, línea 3648). Correrlo entero toca ~35 sitios de snapshot y
     apendea a un ledger committeado de 113 KB.
   - *Lo que no está claro:* si el operador considera aceptable ese churn.
   - *Recomendación:* **correr entero, respetando D-07.** El churn es ruido conocido y
     explícitamente aceptado por la decisión de orden del ROADMAP:55 (vivo antes que limpieza de
     harness). Un script targeted sería más barato pero contradice un lock. Si el planner igual
     quiere reducir el diff, la salida limpia es commitear el ledger en su propia task atómica.

4. **Q4 — ¿La aserción AST anti-substring cubre el archivo entero o sólo `census_matriz`?**
   - *Lo que sabemos:* `main()` línea 355 tiene `if "--selftest" in argv:`, que dispararía un
     falso positivo si el test recorre el módulo entero (verificado leyendo la fuente).
   - *Recomendación:* restringir el `ast.walk` al `FunctionDef` de `census_matriz` — es el único
     lugar donde el gate puede vivir, y mantiene la aserción estricta sin excepciones ad-hoc.
     **Decidirlo en el plan, no en ejecución** (descubrirlo corriendo invita a relajar la aserción).

5. **Q5 — ¿La entrada de backlog `ROADMAP.md:210` se actualiza en esta fase?**
   - *Lo que sabemos:* la entrada afirma que el script "ya tiene el gate listo", verificado falso;
     el ROADMAP se auto-corrige en la nota de sizing (línea 52) pero la entrada no se tocó.
   - *Recomendación:* actualizarla en la task de cierre. Barato y evita que el próximo milestone
     herede la misma afirmación falsa.

## Sources

### Primary (HIGH confidence — verificado por ejecución de herramientas contra HEAD en esta sesión)

- `main_matriz.py` — leído líneas 110-290; `_VENUE_ALLOWLIST:139`, `_venue_token:228`,
  `_CYCLE_CLOSURE_DESTINATION:162`, `if __name__:3162`
- `scripts/literal_census_33.py` — leído íntegro (367 líneas); gate stale confirmado en `:192`
- `main_higyrus.py` — leído líneas 222-266, 640-690, 2896-2935; grep de `_vendor_unreachable`
- `main_market_data.py` — leído líneas 55-80, 455-524, 955-1024; grep de `_write_schema_snapshot`
- `verification/capture.py`, `verification/run_evidence.py`, `verification/mutation_gate.py`
- `verification/test_main_matriz_skip_line_shape.py` — leído íntegro (269 líneas)
- `.github/workflows/ci.yml:40-93` — allowlist explícita de 12 tests
- `pyproject.toml:72-121` — ruff per-file-ignores, mypy files, pytest ini_options
- `.planning/config.json` — `mode: yolo`, `auto_advance: true`, `security_enforcement: true`
- **Ejecuciones:** `uv run python scripts/literal_census_33.py --selftest` (PASS);
  `uv run pytest -q <12 rutas de ci.yml>` (**129 passed**); `import main_matriz` (0.11 s, sin
  side-effects); `socket.getaddrinfo(higyrus_host)` (**gaierror**); httpx MRO + `ConnectError` real
  contra host inexistente; resolución de `.env` bajo `-c` vs. archivo `.py`;
  `git hash-object verification/mutation_gate.py`; `git log` de los baselines de schema

### Secondary (MEDIUM confidence — artefactos del proyecto, no re-verificados contra código)

- `.planning/ROADMAP.md` §§ Phase 42, notas de sizing 49-56, backlog 210
- `.planning/REQUIREMENTS.md` — LIVE-01, LIVE-02, tabla de dependencias cross-fase
- `.planning/research/PITFALLS.md` — Pitfalls 1, 2, 3, 5, 8 (citados textualmente)
- `.planning/research/SUMMARY.md` § Phase 2
- `.planning/milestones/v1.7-phases/39-…/39-01-PLAN.md:87-141` — precedente del checkpoint
- `.planning/STATE.md`, `.planning/PROJECT.md` — historia y decisiones

### Tertiary (LOW confidence)

Ninguna. **No se hizo ninguna búsqueda web ni consulta a Context7**: esta fase no involucra ninguna
librería externa, ningún API de terceros documentado públicamente, ni ninguna decisión de stack.
Todo lo que había que saber está en el repo, y se verificó ahí directamente — que es una fuente
más fuerte que cualquier documentación. Las únicas dos preguntas que rozaban lo externo (semántica
de `find_dotenv` y jerarquía de excepciones de httpx) se resolvieron **empíricamente contra las
versiones instaladas**, no contra docs, lo cual es estrictamente más autoritativo.

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Sitios de código (líneas, firmas) | **HIGH** | Cada uno leído en HEAD en esta sesión; ninguno recordado |
| Estado del DNS de higyrus | **HIGH** | Medido con `socket.getaddrinfo` hoy + mapeo a httpx probado empíricamente |
| Estado del venue de matriz | **HIGH** | Resuelto desde un archivo `.py` real; `_venue_token` devuelve `"bbsa"` |
| Inventario de rename | **HIGH** | `grep -rn` exhaustivo + inspección de cada sitio para clasificar vivo vs. congelado |
| Enrolamiento en CI | **HIGH** | `ci.yml` leído; los 12 archivos enumerados; baseline 129 passed medido |
| Gaps de criterio (header, artefacto committeado) | **HIGH** | Derivados de leer el código y el ROADMAP lado a lado |
| Disponibilidad de datos en vivo (órdenes, mercado) | **LOW** | No determinable antes de la corrida — flaggeado como A3, y el criterio 3 ya lo contempla |
| Aceptabilidad del churn del ledger de market-data | **MEDIUM** | Inferido de la decisión de orden del ROADMAP:55; flaggeado como A4 y Q3 |

**Research date:** 2026-08-31
**Valid until:** 2026-09-07 (7 días — dos hallazgos dependen de estado externo no-determinista:
la resolución DNS de higyrus y la disponibilidad de datos en bbsa. Los hallazgos de código son
válidos mientras HEAD no se mueva; el `git hash-object` de `mutation_gate.py` es el canario)
