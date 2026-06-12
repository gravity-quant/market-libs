# Phase 4: Higyrus Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 04-higyrus-verification
**Areas discussed:** Manejo de PII, SafeModel diff bidireccional (HIGY-03), `assert isinstance` fix in-cycle vs deferred (HIGY-04), Selección de sample (cuenta, fechas, params)

---

## Manejo de PII (datos de cuenta reales)

### Sub-pregunta 1: ¿Qué artefactos quedan committeable en `.planning/verification/`?

| Option | Description | Selected |
|--------|-------------|----------|
| Solo schemas (mirror Phase 2/3) | `schema_of()` claves+tipos PII-free; tests con valores sintéticos inline; no fixtures committeables | ✓ |
| Schemas + fixtures anonimizadas committeables | Schemas + payloads anonimizados via `verification.anonymize` cargados por tests | |
| Solo schemas + denylist explícita en repo | Schemas + `verification/denylists/higyrus_client.py` exportable; captures gitignored | |

**User's choice:** Solo schemas (mirror Phase 2/3) — Recomendado
**Notes:** Preserva consistencia con el patrón establecido en Phases 2-3. El roadmap SC#5 dice "account data anonymized in fixtures" pero el operador prioriza no introducir tech debt nuevo en denylists. `verification.capture()` queda disponible para captures/ gitignored.

### Sub-pregunta 2: ¿Qué imprime el driver `main_higyrus.py` a stdout cuando recibe payloads con PII?

| Option | Description | Selected |
|--------|-------------|----------|
| Solo conteos + shape, nunca valores | `PROBE x: PASS (3 cuentas, list[dict])` sin contenido; máxima seguridad | ✓ |
| Conteos + sample con `safe_print` y secrets extendido | Imprime primer item pero pasa por safe_print con todos los valores PII enumerados como secrets | |
| Conteos + sample con campos PII explícitamente nulled | `_strip_pii(model)` antes de imprimir; lista de campos PII por modelo | |

**User's choice:** Solo conteos + shape, nunca valores — Recomendado
**Notes:** El operador puede leer `captures/` gitignored si necesita datos crudos. Más seguro contra leaks accidentales (grep de logs, screenshots).

---

## SafeModel diff bidireccional (HIGY-03)

### Sub-pregunta 1: ¿Hasta qué profundidad recorrer el diff bidireccional?

| Option | Description | Selected |
|--------|-------------|----------|
| Recursivo en nested models | Baja a DisposicionesGenerales, Domicilio[], etc.; helper de ~30 LOC | ✓ |
| Solo top-level + sanity de presencia en nested | Solo Cuenta/Movimiento/Posicion/PosicionValuada; nested solo presence | |
| Recursivo + type drift check | Recursivo + chequeo de `type(payload[k])` vs declared hint | |

**User's choice:** Recursivo en nested models — Recomendado
**Notes:** Captura field-drop en nested (donde más probable está el silent default — la doc PDF documenta inconsistente, los nested son menos verificados). El type drift check queda deferred porque `_coerce` lo absorbe silenciosamente.

### Sub-pregunta 2: ¿Dónde vive el helper de diff bidireccional?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline en `main_higyrus.py` (driver-local) | Función privada en el driver; YAGNI, Phase 5 copia si confirma | ✓ |
| Promover a `verification/safemodel_diff.py` ahora | Primitivo exportado por barrel; reusable directamente para Phase 5 | |
| Extender `verification/schema.py` con `schema_diff_model()` | Agrupar con `schema_of` existente | |

**User's choice:** Inline en `main_higyrus.py` (driver-local) — Recomendado
**Notes:** Consistente con D-IOL-14 (`_ASSUMED_FIELDS` vivían en `main_iol.py`). Se promueve cuando Phase 5/Matriz confirme compatibilidad de modelos.

### Sub-pregunta 3: ¿Cómo emite el driver findings de `_diff_safemodel_bidirectional`?

| Option | Description | Selected |
|--------|-------------|----------|
| Un finding por discrepancia, ambas direcciones | Mirror D-IOL-15; granularidad fina; ciclo OPEN→CONFIRMED→FIXED filtra ruido | ✓ |
| Un finding por endpoint, agregado | Menos findings pero resolución parcial complicada (todo o nada) | |
| Solo dirección B (FALSE PASS) como finding; dirección A como log info | Reduce ruido pero pierde trazabilidad de wire-only keys nuevos | |

**User's choice:** Un finding por discrepancia, ambas direcciones — Recomendado
**Notes:** Si la primera corrida emite 30 findings es OK. Path qualifier completo (e.g., `.cuenta.administrador.operador.idExterno`). La clasificación humana ex-post decide cuáles son bugs reales.

---

## `assert isinstance` fix in-cycle vs deferred (HIGY-04)

### Sub-pregunta 1: ¿HIGY-04 se trata como fix de fase obligatorio o se difiere?

| Option | Description | Selected |
|--------|-------------|----------|
| Fix de fase obligatorio (mirror IOL-07 dual) | 10 sites de `assert` → `raise HigyrusAPIError`; 10 regression tests | ✓ |
| Finding OPEN + fix opportunistic (MVP Phase 2 mirror) | Driver detecta y documenta; fix solo si live confirma violación real | |
| Fix con deprecation path (2 ciclos) | Warning ahora, raise en próximo cycle | |

**User's choice:** Fix de fase obligatorio (mirror IOL-07 dual) — Recomendado
**Notes:** El fix es trivial, el riesgo de regresión bajo, y `AssertionError` no es API contract documentado. Callers que catchean `AssertionError` deberían haber catcheado el base class `HigyrusClientError`.

### Sub-pregunta 2: ¿Qué `status_code` y forma usa el `HigyrusAPIError` cuando shape mismatch?

| Option | Description | Selected |
|--------|-------------|----------|
| `status_code=0` sentinel + errors envelope sintético | Patrón común: 0 indica «no hubo error HTTP, el cliente lo generó» | ✓ |
| Nueva subclase `HigyrusShapeError(HigyrusAPIError)` | Explícito pero agrega clase al `__all__` público | |
| Pass-through `resp.status_code` real (200) | Técnicamente preciso pero confunde a callers que asumen status >= 400 | |

**User's choice:** `status_code=0` sentinel + errors envelope sintético — Recomendado
**Notes:** Mantiene la jerarquía existente sin agregar subclases. Documentar el sentinel `0` en el docstring de `HigyrusAPIError.status_code`.

---

## Selección de sample (cuenta, fechas, params)

### Sub-pregunta 1: ¿De dónde sale el `id_cuenta` que usa el driver?

| Option | Description | Selected |
|--------|-------------|----------|
| Primer item del listado live + env var override opcional | `cuentas[0].id` resuelto en runtime; `HIGYRUS_SAMPLE_CUENTA` overrride | ✓ |
| Env var obligatoria `HIGYRUS_SAMPLE_CUENTA` | Validada via require_env; explícita y reproducible | |
| Iterar TODAS las cuentas del listado | Máxima cobertura pero semántica de findings cross-cuenta compleja | |

**User's choice:** Primer item del listado live + env var override opcional — Recomendado
**Notes:** El sample siempre existe en el sandbox real. Funciona aunque el operador cambie de tenant. Multi-cuenta sweep queda deferred.

### Sub-pregunta 2: ¿Qué rangos de fecha usa el driver?

| Option | Description | Selected |
|--------|-------------|----------|
| Movimientos: últimos 30 días calendario; PosicionValuada: hoy a hoy | Maximiza probabilidad de payload no vacío; snapshot del día | ✓ |
| 5 días hábiles back (mirror exacto D-IOL-19) | Mirror IOL pero movimientos en cuentas reales son sparse | |
| 90 días calendario | Máxima cobertura pero posibles paginations o limits | |

**User's choice:** Movimientos: últimos 30 días calendario; PosicionValuada: hoy a hoy — Recomendado
**Notes:** Movimientos sparse necesitan más rango para que el diff bidireccional (HIGY-03) tenga shape para inspeccionar. HIGY-07 (empty path) se loggea como PASS, no FAIL.

### Sub-pregunta 3: ¿Cómo dispara el driver el path de error `"errors"` envelope (HIGY-05) y el probe 401?

| Option | Description | Selected |
|--------|-------------|----------|
| Dos probes separados: `errors_envelope` always-on + `auth_401` opt-in | `get_movimientos('INVALID-ID', ...)` always-on; bad-creds opt-in | ✓ |
| Probe único `errors_envelope` con bad-cuenta-id (sin auth_401) | Solo bad-id; confiamos en cobertura IOL Phase 3 | |
| Probe único opt-in `bad_creds` (cubre 401 + envelope) | Un solo probe ejercita ambos pero acopla las verificaciones | |

**User's choice:** Dos probes separados: `errors_envelope` always-on + `auth_401` opt-in — Recomendado
**Notes:** `errors_envelope` no requiere opt-in (no risk de lockout). `auth_401` mirror exacto D-IOL-1/D-IOL-2 con `VERIFY_HIGYRUS_BAD_CREDS=1`, configure password+'_INVALID' + try/finally restore.

### Sub-pregunta 4: ¿Cómo se eligen `tipo_cuenta` y `nivel` para `get_posicion_valuada`?

| Option | Description | Selected |
|--------|-------------|----------|
| Env vars con defaults razonables + finding si falla | `HIGYRUS_SAMPLE_TIPO_CUENTA` (default 'propia'), `HIGYRUS_SAMPLE_NIVEL` (default 'detalle'); PARAM finding si rechaza | ✓ |
| Inspeccionar la docs PDF para extraer valores documentados | Hardcoded; preciso pero PDF tiene artefactos OCR (acentos donde wire usa ASCII) | |
| Skip probe_get_posicion_valuada si params no resueltos | Conservador pero deja HIGY-02 incompleto (4/5 endpoints cubiertos) | |

**User's choice:** Env vars con defaults razonables + finding si falla — Recomendado
**Notes:** Permite a Phase 4 ejecutarse aunque los defaults no apliquen. Si Higyrus rechaza, el finding lista valores documentados (refiriendo a la PDF) para que el operador setee la env var correcta. Cubrimiento de HIGY-02 garantizado.

---

## Claude's Discretion

- Texto exacto de líneas verbatim del summary final (los conteos por estado siguen el formato Phase 2: `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N`).
- Estructura interna de `_diff_safemodel_bidirectional` (iterativo vs recursivo, con `yield from` vs lista acumulada, etc.) y el formato exacto del `path` qualifier.
- Tactic exacta de la cascade SKIPPED tras `login()` failure (mirror D-IOL-3): flag module-level vs wrapper decorator vs early-return en cada probe.
- Cómo el probe 13 (`probe_parity_sync_async`) inspecciona los params emitidos para verificar la deviation del `drop_none` (HIGY-06).
- Si `probe_get_listado_cuentas_sync` usa `estado="alta"` o no filtra.
- Sub-clasificación de findings dirección A (info) vs dirección B (FALSE PASS) en el `detail` field.
- Timing del check `Optional[T]` en `_diff_safemodel_bidirectional` (los models actuales no usan `T | None` pero podrían en el futuro).
- Si agregar plausibility bounds en `cantidad` de Movimiento (discrecionalmente NO se agregan en Phase 4).

## Deferred Ideas

- Iterar TODAS las cuentas del listado (multi-cuenta sweep) — semántica de findings cross-cuenta compleja.
- Fixtures committeable anonimizadas via `verification.anonymize` — defer hasta decisión de cycle futuro.
- Promover `_diff_safemodel_bidirectional` a `verification/safemodel_diff.py` — YAGNI hasta Phase 5/Matriz confirmar compatibilidad.
- Type drift check (wire string vs model float) — `_coerce` lo absorbe silenciosamente.
- Plausibility bounds en `cantidad` de Movimiento y Posicion — Phase 4 valida shape únicamente.
- `probe_get_listado_cuentas` con `tipo_cuenta` u otros filtros — combinatoria de filtros queda deferred.
- Test de auth-once discipline mockeado — verificación del fixture, no del cliente.
- `HigyrusShapeError(HigyrusAPIError)` subclase — defer si patrón se vuelve común en Phase 5.
- Refactor a clase Client por instancia / dedup sync-async — fuera de scope del ciclo de verificación.
- DRIFT-02 informe consolidado per-package — anclado a Phase 5.
