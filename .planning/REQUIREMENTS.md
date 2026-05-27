# Requirements: market-libs — Verificación en vivo de clientes

**Defined:** 2026-05-26
**Core Value:** Cada divergencia entre un cliente y su API en vivo debe ser detectada, documentada y corregida.

## v1 Requirements

Requisitos para este ciclo de verificación. Cada uno mapea a una fase del roadmap.
Convención transversal: todo fix de lógica se aplica espejado en `client.py` y `aio.py`,
y se acompaña de un test de regresión mockeado (`pytest-httpx`) siguiendo `Regression: ... (issue #NNN)`.

### Infraestructura de verificación (HARN)

- [ ] **HARN-01**: Cada driver `main_*.py` valida sus env vars requeridas al iniciar y, si faltan, imprime `SKIPPED <pkg>: missing X, Y` sin bloquear a los demás
- [ ] **HARN-02**: Las llamadas mutantes (órdenes de matriz) quedan detrás de un flag opt-in (`VERIFY_MUTATING`) y de un assert de base URL sandbox (remarkets); por defecto no se ejecutan en vivo
- [ ] **HARN-03**: Helper de redacción que impide imprimir credenciales o tokens completos en stdout, logs o reportes (solo prefijo redactado)
- [ ] **HARN-04**: Marker `@pytest.mark.live` registrado + flag `--live` que separa los tests en vivo de los mockeados, manteniendo el CI offline y determinístico
- [ ] **HARN-05**: Registro de hallazgos clasificado por tipo (SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT) en `.planning/verification/<pkg>-findings.md`
- [ ] **HARN-06**: Pipeline que convierte un payload real capturado en vivo en fixture de test de regresión mockeado, con anonimización de PII antes de commitear

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
- [ ] **HIGY-02**: Barrido happy-path de `get_health`, `get_listado_cuentas`, `get_movimientos`, `get_posicion_valuada`, `get_posiciones` reteniendo payload, sync y async
- [ ] **HIGY-03**: Diff bidireccional de claves del payload crudo vs campos declarados de cada modelo (detección de field-drop silencioso por `SafeModel.from_api`)
- [ ] **HIGY-04**: Verificar en vivo la discriminación list/object (`assert isinstance(raw, list/dict)`); si rompe, corregir a un `HigyrusAPIError` tipado en vez de `AssertionError`
- [ ] **HIGY-05**: Verificar el parsing de error por clave `"errors"` en vivo (request inválido)
- [ ] **HIGY-06**: Verificar paridad sync↔async, incluyendo la deviación conocida de `drop_none` en el `_request` async
- [ ] **HIGY-07**: Verificar los paths de respuesta vacía / 204 (lista vacía, no crash, no `None`)

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

Qué fase cubre cada requisito. Se completa durante la creación del roadmap.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARN-01..06 | TBD | Pending |
| IOL-01..07 | TBD | Pending |
| HIGY-01..07 | TBD | Pending |
| MATZ-01..07 | TBD | Pending |
| AMB-01..06 | TBD | Pending |
| DRIFT-01..02 | TBD | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 35 ⚠️

---
*Requirements defined: 2026-05-26*
*Last updated: 2026-05-26 after initial definition*
