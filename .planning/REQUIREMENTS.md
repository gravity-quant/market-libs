# Requirements: market-libs — Verificación en vivo de clientes

**Defined:** 2026-05-26
**Core Value:** Cada divergencia entre un cliente y su API en vivo debe ser detectada, documentada y corregida.

## v1 Requirements

Requisitos para este ciclo de verificación. Cada uno mapea a una fase del roadmap.
Convención transversal: todo fix de lógica se aplica espejado en `client.py` y `aio.py`,
y se acompaña de un test de regresión mockeado (`pytest-httpx`) siguiendo `Regression: ... (issue #NNN)`.

### Infraestructura de verificación (HARN)

- [x] **HARN-01**: Cada driver `main_*.py` valida sus env vars requeridas al iniciar y, si faltan, imprime `SKIPPED <pkg>: missing X, Y` sin bloquear a los demás
- [x] **HARN-02**: Las llamadas mutantes (órdenes de matriz) quedan detrás de un flag opt-in (`VERIFY_MUTATING`) y de un assert de base URL sandbox (remarkets); por defecto no se ejecutan en vivo
- [x] **HARN-03**: Helper de redacción que impide imprimir credenciales o tokens completos en stdout, logs o reportes (solo prefijo redactado)
- [x] **HARN-04**: Marker `@pytest.mark.live` registrado + flag `--live` que separa los tests en vivo de los mockeados, manteniendo el CI offline y determinístico
- [x] **HARN-05**: Registro de hallazgos clasificado por tipo (SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT) en `.planning/verification/<pkg>-findings.md`
- [x] **HARN-06**: Pipeline que convierte un payload real capturado en vivo en fixture de test de regresión mockeado, con anonimización de PII antes de commitear

### Verificación iol-client (IOL)

- [ ] **IOL-01**: Verificar contra IOL en vivo el flujo de auth (`login()` explícito + lazy-auth en la primera llamada), sync y async
- [ ] **IOL-02**: Barrido happy-path de `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type` reteniendo el payload crudo, sync y async
- [ ] **IOL-03**: Construir un mapa campo→tipo observado del `dict` crudo y compararlo con lo que asumen los callers (detección de deriva de forma)
- [ ] **IOL-04**: Verificar en vivo la clave de envoltura `["titulos"]`, el formato de fecha del path histórico y que los campos numéricos llegan como JSON number (no string)
- [ ] **IOL-05**: Verificar el mapeo del error 401 en vivo (credenciales inválidas vía `configure()`)
- [ ] **IOL-06**: Verificar paridad estructural sync↔async para cada endpoint
- [ ] **IOL-07**: Implementar `grant_type=refresh_token` con fallback a password grant en `client.py` y `aio.py`, con tests que cubran refresh exitoso y fallback

### Verificación higyrus-client (HIGY)

- [ ] **HIGY-01**: Verificar contra Higyrus en vivo el flujo de auth (login + lazy-auth), sync y async
- [x] **HIGY-02**: Barrido happy-path de `get_health`, `get_listado_cuentas`, `get_movimientos`, `get_posicion_valuada`, `get_posiciones` reteniendo payload, sync y async
- [x] **HIGY-03**: Diff bidireccional de claves del payload crudo vs campos declarados de cada modelo (detección de field-drop silencioso por `SafeModel.from_api`)
- [ ] **HIGY-04**: Verificar en vivo la discriminación list/object (`assert isinstance(raw, list/dict)`); si rompe, corregir a un `HigyrusAPIError` tipado en vez de `AssertionError`
- [x] **HIGY-05**: Verificar el parsing de error por clave `"errors"` en vivo (request inválido)
- [x] **HIGY-06**: Verificar paridad sync↔async, incluyendo la deviación conocida de `drop_none` en el `_request` async
- [x] **HIGY-07**: Verificar los paths de respuesta vacía / 204 (lista vacía, no crash, no `None`)

### Verificación matriz-client (MATZ)

- [ ] **MATZ-01**: Verificar contra Primary/remarkets en vivo el flujo de auth (login + lazy-auth), sync REST
- [ ] **MATZ-02**: Barrido happy-path read-only de toda la superficie REST (segments, instruments en sus variantes, market data, trades, order *reads*, risk positions/report) reteniendo payload
- [ ] **MATZ-03**: Diff de claves del payload crudo vs campos de los modelos `from_api` (field-drop)
- [ ] **MATZ-04**: Verificar en vivo la existencia de las claves de envoltura (`order`/`orders`/`marketData`/`trades`/`positions`); un `KeyError` no mapeado a la jerarquía de excepciones es candidato a fix
- [ ] **MATZ-05**: Verificar cobertura de `{"status":"ERROR"}` → `PrimaryAPIError` en varias condiciones de error distintas (símbolo bogus, cuenta inválida, param malformado)
- [ ] **MATZ-06**: Verificación mock-only de la construcción de request + parsing de respuesta de `new_order`/`replace_order`/`cancel_order` — nunca en vivo (preservar el quirk de submit por GET en el mock)
- [ ] **MATZ-07**: Assertions de market data solo sobre forma/tipo/presencia (no sobre valores), con guarda de horario de mercado para los paths que dependen de sesión abierta

### Verificación ambito-financiero-client (AMB)

- [ ] **AMB-01**: Verificar una llamada real exitosa con el User-Agent actual, sync y async
- [ ] **AMB-02**: Verificar `parse_ar_decimal` contra el formato real `"1.415,00"` (detectar un cambio del server a `1415.00`)
- [ ] **AMB-03**: Verificar el formato de fecha emitido en la URL y que la respuesta llega con la forma esperada (`list[list[str]]`)
- [ ] **AMB-04**: Verificar que `NoDataError` se dispara para una fecha sin cotización
- [ ] **AMB-05**: Verificar paridad sync↔async
- [ ] **AMB-06**: Probe anti-bot — confirmar que el UA correcto pasa y que un UA deliberadamente inválido reproduce el 403 (sin loops, riesgo de IP-ban)

### Detección de drift y cierre (DRIFT)

- [ ] **DRIFT-01**: Commitear snapshots de schema estructural (claves + tipos, no valores) por endpoint verificado, para detección de drift en corridas futuras
- [ ] **DRIFT-02**: Producir un informe de hallazgos por paquete (cliente vs respuesta real) y dejar cada bug confirmado corregido con su test de regresión mockeado

## v2 Requirements

Reconocidos pero diferidos; no entran en el roadmap de este ciclo.

### Cobertura mock de bordes de error (ERR)

- **ERR-01**: Verificación mockeada del mapeo 403/429/5xx → excepción tipada en cada cliente (no se dispara en vivo por riesgo de lockout)
- **ERR-02**: Verificación mockeada del límite de TTL de token (refresh tras expiración) con reloj simulado, para los tokens de 23h (higyrus/matriz)

## Out of Scope

Excluido explícitamente para evitar scope creep.

| Feature | Reason |
|---------|--------|
| `wallets-client` | Stub sin endpoints reales ni servicio verificable |
| Superficie async de `matriz-client` | No existe `aio.py`; su async es solo la capa WebSocket |
| Verificación de WebSocket streaming (matriz) | Capa thread-based; fuera de alcance este ciclo |
| Disparar 403/429/5xx en vivo | Riesgo de rate-limit/lockout de cuentas reales (anti-feature) |
| Colocar/cancelar órdenes reales en vivo | Mueve dinero/posiciones aun en sandbox; se verifica solo por mock |
| Divergencia prod-vs-sandbox de matriz | Solo se verifica contra remarkets por seguridad; gap registrado para downstream |
| Retries/backoff y logging estructurado | Tech debt fuera del foco; podría enmascarar divergencias reales |
| Refactor a clase `Client` por instancia / dedup sync-async | Cambio arquitectónico breaking, no es el foco de este ciclo |
| Publicación a PyPI | No forma parte de la verificación |

## Traceability

Qué fase cubre cada requisito. Completado durante la creación del roadmap.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARN-01 | Phase 1 | Complete |
| HARN-02 | Phase 1 | Complete |
| HARN-03 | Phase 1 | Complete |
| HARN-04 | Phase 1 | Complete |
| HARN-05 | Phase 1 | Complete |
| HARN-06 | Phase 1 | Complete |
| AMB-01 | Phase 2 | Pending |
| AMB-02 | Phase 2 | Pending |
| AMB-03 | Phase 2 | Pending |
| AMB-04 | Phase 2 | Pending |
| AMB-05 | Phase 2 | Pending |
| AMB-06 | Phase 2 | Pending |
| DRIFT-01 | Phase 2 | Pending |
| IOL-01 | Phase 3 | Pending |
| IOL-02 | Phase 3 | Pending |
| IOL-03 | Phase 3 | Pending |
| IOL-04 | Phase 3 | Pending |
| IOL-05 | Phase 3 | Pending |
| IOL-06 | Phase 3 | Pending |
| IOL-07 | Phase 3 | Pending |
| HIGY-01 | Phase 4 | Pending |
| HIGY-02 | Phase 4 | Complete |
| HIGY-03 | Phase 4 | Complete |
| HIGY-04 | Phase 4 | Pending |
| HIGY-05 | Phase 4 | Complete |
| HIGY-06 | Phase 4 | Complete |
| HIGY-07 | Phase 4 | Complete |
| MATZ-01 | Phase 5 | Pending |
| MATZ-02 | Phase 5 | Pending |
| MATZ-03 | Phase 5 | Pending |
| MATZ-04 | Phase 5 | Pending |
| MATZ-05 | Phase 5 | Pending |
| MATZ-06 | Phase 5 | Pending |
| MATZ-07 | Phase 5 | Pending |
| DRIFT-02 | Phase 5 | Pending |

**Note on DRIFT (cross-cutting):** DRIFT-01 (schema snapshots) is anchored to Phase 2 and DRIFT-02 (per-package findings report + fix-with-regression-test) to Phase 5, but each client phase (2–5) produces its own structural schema snapshot, classified findings file, and mocked regression tests as part of its definition of "done."

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-26*
*Last updated: 2026-05-26 after roadmap creation (traceability mapped)*
