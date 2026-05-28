# market-libs — Verificación en vivo de clientes

## What This Is

Ciclo de verificación exhaustiva de las librerías cliente del monorepo `market-libs`.
El objetivo es ejercitar la API pública completa de cada cliente verificable —en sus
superficies **sync** (`client.py`) y **async** (`aio.py`)— contra las **APIs financieras
en vivo**, detectar bugs y discrepancias entre el comportamiento del cliente y lo que
devuelve el servicio real, y corregirlos en el mismo ciclo. El vehículo de verificación
son los scripts `main_*.py` de la raíz, hoy mínimos, que se extienden para cubrir toda
la superficie de cada paquete.

Alcance: 4 de los 5 paquetes — `iol-client`, `higyrus-client`, `matriz-client` y
`ambito-financiero-client`.

## Core Value

Confianza de que cada cliente refleja fielmente el comportamiento real de su API: cada
divergencia entre el cliente y el servicio en vivo debe ser detectada, documentada y
corregida.

## Requirements

### Validated

<!-- Inferido del codebase existente (ver .planning/codebase/). -->

- ✓ Monorepo uv con 5 paquetes cliente HTTP independientes y publicables — existing
- ✓ Superficie sync (`client.py`) en los 5 paquetes — existing
- ✓ Superficie async (`aio.py`) en iol, higyrus, ambito, wallets — existing
- ✓ Estrategias de auth por paquete (OAuth2 IOL, Bearer Higyrus, X-Auth-Token Matriz/Primary, sin auth Ámbito) — existing
- ✓ Jerarquía de excepciones tipadas por paquete — existing
- ✓ Refresco de token perezoso con caché y TTL por paquete — existing
- ✓ Suites de pytest con HTTP mockeado (`pytest-httpx`), sync y async — existing
- ✓ CI en GitHub Actions (ruff, mypy strict, pytest; matriz 3.12/3.13) — existing
- ✓ Scripts `main_*.py` de smoke-test manual (login + 1-2 funciones) — existing
- ✓ Harness de verificación en vivo: gate de credenciales (`require_env`), doble gate de mutación (`mutating_allowed`, hostname remarkets exacto), redacción (`redact`/`safe_print` + patrón Bearer), marker `@pytest.mark.live` con `--live`, formato de hallazgos clasificado y pipeline payload→anonimización→fixture (HARN-01..06) — Validado en Phase 1 (2026-05-28)

### Active

<!-- Foco de este ciclo. Hipótesis hasta verificar contra la API real. -->

- [ ] Ejercitar la superficie pública completa sync+async de `iol-client` contra IOL en vivo
- [ ] Ejercitar la superficie pública completa sync+async de `higyrus-client` contra Higyrus en vivo
- [ ] Ejercitar la superficie pública sync (REST) de `matriz-client` contra Primary/remarkets en vivo
- [ ] Ejercitar la superficie pública completa sync+async de `ambito-financiero-client` contra la API pública en vivo
- [ ] Documentar cada bug/discrepancia hallado (cliente vs respuesta real de la API)
- [ ] Corregir cada bug detectado, acompañado de un test de regresión mockeado

### Out of Scope

<!-- Límites explícitos con su razón, para no re-incorporarlos. -->

- `wallets-client` — stub sin endpoints reales y con URL placeholder; nada que verificar en vivo
- Superficie async de `matriz-client` — no existe `aio.py`; su "async" es solo la capa WebSocket
- Streaming WebSocket de `matriz-client` — capa basada en thread daemon; fuera de alcance este ciclo
- Publicación a PyPI — no forma parte de la verificación
- Refactors arquitectónicos (clase `Client` por instancia, deduplicación sync/async, retries/backoff, logging estructurado) — tech debt conocido, no es el foco de este ciclo

## Context

- **Estado de testing actual:** todos los tests son unitarios con HTTP mockeado (`pytest-httpx`). No hay tests de integración ni E2E contra APIs reales. Los `main_*.py` son el único contacto con servicios en vivo y hoy apenas cubren `login()` + 1-2 funciones por cliente. De ahí la necesidad de verificación en vivo: nada confirma hoy que los clientes coincidan con el comportamiento real de las APIs.
- **Superficie por cliente (a ejercitar):**
  - `iol-client`: `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type` (sync + async). No tiene modelos tipados — devuelve `dict` crudo, lo que facilita discrepancias silenciosas de forma.
  - `higyrus-client`: cuentas, movimientos, posiciones, health (sync + async). Usa `SafeModel`/`from_api` tolerante.
  - `matriz-client`: segments, instruments, market data, órdenes (sync REST). Modelos `from_api`. Verifica también el chequeo de `"status": "ERROR"` del payload de Primary.
  - `ambito-financiero-client`: cotizaciones FX (sync + async). Sin auth; depende de un User-Agent de navegador hardcodeado (frágil ante anti-bot).
- **Credenciales:** Ámbito no requiere auth. IOL/Higyrus/Matriz requieren `.env` por paquete (`packages/<pkg>/.env`, con `.env.example` de plantilla). Matriz apunta por defecto a remarkets (sandbox).
- **Convención de regresión existente:** el codebase ya marca tests de regresión con referencia al bug (ej. `"""Regression: ... (issue #102)."""`); los fixes de este ciclo deben seguir esa convención.
- **Mapa de codebase disponible:** `.planning/codebase/` (ARCHITECTURE, STACK, STRUCTURE, TESTING, CONCERNS, CONVENTIONS, INTEGRATIONS).

## Constraints

- **Tech stack**: Python 3.12+, uv, httpx (sync+async), pytest+pytest-httpx, ruff, mypy strict — toda extensión y fix debe respetar el stack y pasar el CI existente.
- **Arquitectura**: estado singleton a nivel de módulo; sin código compartido entre paquetes (por diseño). Los fixes se aplican dentro de cada paquete, sin introducir dependencias cruzadas.
- **Dual sync/async**: cualquier fix de lógica debe espejarse en `client.py` y `aio.py` del mismo paquete (deuda conocida: la lógica está duplicada).
- **Seguridad**: las credenciales viven en `.env` por paquete; nunca commitear `.env` ni exponer credenciales en logs, reportes o tests.
- **Dependencias externas en vivo**: la verificación depende de la disponibilidad y el estado real de servicios de terceros; resultados pueden variar por horario de mercado, datos disponibles o rate limits.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Verificar contra APIs en vivo (no mock) | El objetivo es detectar divergencias reales cliente-vs-servicio, que el mock oculta | — Pending |
| Vehículo = scripts `main_*.py` extendidos | Ya existen como smoke-test manual; extenderlos cubre toda la superficie sin nueva infraestructura | — Pending |
| Cubrir sync + async | Ambas superficies pueden divergir; la lógica está duplicada y puede haber bugs solo en una | — Pending |
| Reportar y arreglar en el mismo ciclo | El usuario quiere cerrar el loop: hallazgo → corrección | — Pending |
| Cada fix con test de regresión mockeado | Evita que el bug regrese; sigue la convención existente del codebase | — Pending |
| Excluir `wallets-client` | Es un stub sin endpoints reales ni servicio verificable | — Pending |
| Excluir WebSocket/async de matriz | Capa thread-based sin contraparte async; fuera de foco | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-28 after Phase 1 (Safety Harness & Verification Infrastructure) completion*
