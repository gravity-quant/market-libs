# Phase 3: IOL Verification — Discussion Log

**Discussed:** 2026-06-06
**Mode:** default (no flags)

## Area Selection

Presented 4 IOL-specific gray areas (phase-2 lifecycle decisions D-01..D-26 carried
forward without re-asking):

1. Lockout safety: probe 401 + auth-once
2. refresh_token + password fallback (IOL-07)
3. Field→tipo map (IOL-03) + drift baseline
4. Endpoint sweep: scope + per-endpoint snapshot

**User selected:** Lockout safety (área 1) — único deep-dive interactivo.

Las otras 3 áreas se capturan como Claude's Discretion en CONTEXT.md con
propuestas concretas basadas en patrones Phase 2 + el código actual del cliente.

## Discussion: Lockout safety (probe 401 + auth-once)

### Q1: ¿Cómo abordar el probe 401 (IOL-05) sin riesgo de lockear la cuenta real?

Options:
- Opt-in gate `VERIFY_IOL_BAD_CREDS=1` (Recommended) — mirror Phase 2 D-12
- Usuario sintético dedicado `IOL_INVALID_USER`
- Skip 401 live — mock-only
- Real user + clearly-wrong password, single-shot, last

**User selected:** Opt-in gate `VERIFY_IOL_BAD_CREDS=1`.

Locked as **D-IOL-1**.

### Q2: Bajo VERIFY_IOL_BAD_CREDS=1, ¿cómo el probe inyecta las creds inválidas?

Options:
- `configure(password=IOL_PASSWORD + "_INVALID")` + try/finally restore (Recommended)
- Env vars dedicadas `IOL_INVALID_USER` + `IOL_INVALID_PASSWORD`
- Inyectar directo a `iol_client.client._password = ...` (bypass configure)

**User selected:** configure + try/finally restore.

Locked as **D-IOL-2** (mirror Phase 2 D-15 pattern).

### Q3: ¿Cómo enforcear 'auth-once discipline' a nivel driver?

Options:
- Una llamada explícita `iol_client.login()` up-front + fail-fast (Recommended)
- Sólo lazy-auth (no login() explícito)
- `login()` explícito sin fail-fast: cada probe maneja `IOLAuthError`

**User selected:** `login()` up-front + fail-fast con cascade SKIPPED.

Locked as **D-IOL-3**.

### Q4: ¿Dónde va el probe 401 en el orden?

Options:
- Último, mirror antibot (D-13) (Recommended)
- Primero, antes de happy probes
- Justo después de `login()` explicit, antes del sweep

**User selected:** Último.

Locked as **D-IOL-4**.

## Claude's Discretion (las 3 áreas no seleccionadas)

Propuestas concretas en CONTEXT.md `<decisions>`:

- **refresh_token + fallback (IOL-07):** D-IOL-8..12 — `_refresh_token` global,
  `_refresh()` privada, `_ensure_token()` con fallback dual, probe in-vivo +
  4 mocked regression tests por surface.
- **Field→tipo map (IOL-03):** D-IOL-13..15 — reuso de `schema_of`, assumptions
  hardcoded en constants module-level, 3 clases de finding (missing, drift,
  unexpected).
- **Endpoint sweep + snapshots (IOL-04):** D-IOL-16..20 — 4 snapshots committeable,
  símbolo fijo GGAL, instrument_type baseline `acciones`, parity estructural
  sync↔async.

## Deferred Ideas

Capturadas en CONTEXT.md `<deferred>`:
- get_quote multi-símbolo, get_instruments_by_type 6-types-drift, refresh_token
  persistido, throttling/rate-limit retries, anonymize() para IOL, anti-bot probe,
  test mockeado de auth-once discipline, plausibility bounds en histórico,
  refactor cliente a clase, DRIFT-02 consolidado.

## Scope Creep — None

User mantuvo focus en el alcance del roadmap. No hubo redirecciones por scope creep.
