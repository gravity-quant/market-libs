---
phase: 01
slug: safety-harness-verification-infrastructure
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-28
---

# Phase 01 — Security

> Contrato de seguridad de la fase: registro de amenazas, riesgos aceptados y traza de auditoría.
> Registro autorizado en tiempo de plan (los 4 PLANs traen bloque `<threat_model>`); auditado en modo verificación por gsd-security-auditor.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| credential value → stdout/log/report | Un token/password cargado de env puede pasar a un print/log; punto de fuga (HARN-03) | Credenciales (alta sensibilidad) |
| live test → CI runner | Un test `@pytest.mark.live` nunca debe ejecutar en CI por defecto (HARN-04) | Ejecución contra API real |
| env (.env/shell) → driver run | Credenciales faltantes/parciales deben producir un SKIP limpio, nunca una corrida parcial (HARN-01) | Credenciales / control de flujo |
| driver → live mutating endpoint | El alta/cancelación de órdenes debe ser inalcanzable salvo opt-in explícito + sandbox (HARN-02) | Operación destructiva |
| `configure(base_url=...)` override → mutation guard | Un override de base URL a prod no debe colarse por el gate | Configuración de target |
| child driver stdout → aggregate runner | El runner no debe re-emitir stdout crudo del hijo (puede contener credencial) | Salida potencialmente sensible |
| live payload (raw PII) → git | Un payload real con IDs/CUIT/nombres nunca debe llegar a una ubicación committeable (HARN-06) | PII |
| anonymized fixture → committed test | Un fixture committeado bajo `packages/<pkg>/tests/` no debe contener PII real (HARN-06/D-10) | PII anonimizada |
| schema snapshot → committed file | Un snapshot de esquema debe ser PII-free por construcción (D-12) | Solo claves+tipos |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-01-01 | Information Disclosure | `redact()` / sitios de print | mitigate | `redact(value, keep=4)` → prefijo + elipsis; el valor completo nunca es alcanzable desde el retorno (`verification/redaction.py`) | closed |
| T-01-02 | Information Disclosure | `safe_print()` (2ª capa) | mitigate | Enmascara cualquier secreto conocido (≥4 chars) en el texto; segunda capa estructural ante un print de dict crudo (`verification/redaction.py`) | closed |
| T-01-03 | Reliability / output corruption | `safe_print()` con secreto vacío/corto | mitigate | Guard `len(secret) >= 4` evita el wedge de `str.replace("", marker)` (concourse #4656) (`verification/redaction.py`) | closed |
| T-01-04 | Tampering (test scope) | marker `live` por defecto | mitigate | Deselect-by-default en `pytest_collection_modifyitems`; `--strict-markers` registra el marker. Behavioral: `145 passed, 1 deselected` (`conftest.py`) | closed |
| T-01-05 | Tampering / Elevation | `mutating_allowed()` | mitigate | Doble gate: `VERIFY_MUTATING == "1"` AND hostname del sandbox; default `False` + `SKIPPED (mutating, guard off)` (`verification/mutation_gate.py`) | closed |
| T-01-06 | Tampering (prod misconfig) | fuente de base-URL en el guard | mitigate | Lee `matriz_client.client._base_url` en vivo al momento del guard (no constante). **Endurecido CR-02:** hostname exacto vía `urlsplit().hostname == "api.remarkets.primary.com.ar"`; la forma substring explotable está ausente | closed |
| T-01-07 | Reliability / fail-safe | `require_env()` | mitigate | Devuelve `bool`, nunca lanza/sale; imprime verbatim `SKIPPED <pkg>: missing X, Y` (`verification/env_gate.py`) | closed |
| T-01-08 | Information Disclosure | lectura de `_base_url` privado | accept | Lectura de estado de módulo solo para decidir el gate; nunca se imprime (A2). Ver Accepted Risks | closed |
| T-01-09 | Information Disclosure | destino de `capture()` | mitigate | Payloads crudos solo a `.planning/verification/captures/`, gitignored; `git check-ignore` confirma (`verification/capture.py`, `.gitignore`) | closed |
| T-01-10 | Information Disclosure | `anonymize()` + review manual | mitigate | `Denylist` reemplaza claves PII. **Endurecido CR-01:** `_scrub` sanea recursivamente contenedores bajo claves denylisted (ningún dict/list sobrevive verbatim). Review humano obligatorio documentado en `FINDINGS-TEMPLATE.md` | closed |
| T-01-11 | Information Disclosure | `schema_of()` | mitigate | Snapshot de claves + nombres de tipo, nunca valores; PII-free por construcción (`verification/schema.py`) | closed |
| T-01-12 | Tampering (false-pass) | preservación de formato en anonymize | mitigate | Valores no-PII relevantes (decimal AR, número-vs-string) preservados para que el fixture aún reproduzca el bug (`verification/anonymize.py`) | closed |
| T-01-13 | Information Disclosure | prints de credenciales en drivers | mitigate | Todo token/cred por `redact()`; dicts por `safe_print(text, secrets)`; `main_iol.py` usa `redact(token)` (el `token[:12]` crudo eliminado) | closed |
| T-01-14 | Information Disclosure | agregación de stdout en `main_verify.py` | mitigate | Imprime solo el estado por paquete (RAN/SKIPPED/FAILED); nunca re-emite el stdout crudo del hijo | closed |
| T-01-15 | Tampering | path de mutación en `main_matriz.py` | mitigate | Rama de mutación gateada por `mutating_allowed()`; alta de órdenes nunca corre en vivo (Out of Scope) | closed |
| T-01-16 | Reliability / fail-safe | env gate del driver + continuación del runner | mitigate | Cada driver `sys.exit(0)` ante creds faltantes; el runner captura (`check=False` + `OSError`) y continúa, nunca se detiene (D-14) | closed |
| T-01-SC | Tampering (supply chain) | instalaciones npm/pip/cargo | accept | Cero dependencias nuevas; `tech-stack.added: []` en los 4 SUMMARYs; `uv.lock` sin cambios. Ver Accepted Risks | closed |

*Status: open · closed*
*Disposition: mitigate (implementación requerida) · accept (riesgo documentado) · transfer (terceros)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-08 | El mutation gate lee `matriz_client.client._base_url` (estado privado) solo para la decisión de gating por hostname; el valor nunca se imprime ni se loguea (A2). No se lee ni imprime credencial alguna en ese sitio. | Sebastián de la Fuente | 2026-05-28 |
| AR-02 | T-01-SC | La fase no introduce ninguna dependencia: solo stdlib (`re`, `dataclasses`, `json`, `pathlib`, `subprocess`, `urllib`), `pytest` ya presente y paquetes del workspace ya instalados. Faker fue rechazado explícitamente (A4). `uv.lock` sin cambios; RESEARCH Package Legitimacy Audit = none. | Sebastián de la Fuente | 2026-05-28 |

*Los riesgos aceptados no resurgen en auditorías futuras.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-28 | 17 | 17 | 0 | gsd-security-auditor (opus) |

**Notas de la auditoría:**
- Modo verificación (registro autorizado en tiempo de plan): se verificó que cada mitigación existe en el código actual; no se escanearon amenazas nuevas.
- Confirmados en código los dos endurecimientos del code review (`01-REVIEW.md`): CR-02 (hostname exacto en `mutation_gate.py`) y CR-01 (`_scrub` en `anonymize.py`). Sin la corrección CR-02, T-01-05/T-01-06 habrían quedado OPEN (la mitigación planeada usaba substring explotable).
- Sin flags de amenaza no mapeados: los 4 SUMMARYs mapean limpiamente al registro; 01-04 declara "Sin threat flags nuevos".
- Suite offline: `145 passed, 1 deselected`. `block_on: high` — sin findings high/blocker abiertos.

---

## Sign-Off

- [x] Todas las amenazas tienen disposición (mitigate / accept / transfer)
- [x] Riesgos aceptados documentados en el Accepted Risks Log (AR-01, AR-02)
- [x] `threats_open: 0` confirmado
- [x] `status: verified` en frontmatter

**Approval:** verified 2026-05-28
