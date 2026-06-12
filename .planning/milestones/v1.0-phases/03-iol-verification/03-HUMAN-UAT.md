---
status: partial
phase: 03-iol-verification
source: ["03-VERIFICATION.md"]
started: "2026-06-06T17:35:00Z"
updated: "2026-06-06T17:35:00Z"
---

## Current Test

[awaiting human testing]

## Tests

### 1. Verificación in-vivo de IOL-05 — probe_auth_401 con credenciales inválidas

**expected:** Ejecutar UNA SOLA VEZ `VERIFY_IOL_BAD_CREDS=1 uv run --package iol-client python main_iol.py` y observar que la última línea de probes incluya:

```
PROBE auth_401: FINDING F-NN (EXPECTED)
```

Más una entrada nueva en `.planning/verification/iol-client-findings.md` con:
- **Class:** `AUTH`
- **Status:** `EXPECTED`
- **Surface:** `sync`
- **status_code:** `401`

El driver debe terminar exit 0. El `IOL_PASSWORD` debe quedar restaurado al original tras el `finally` (verificable inspectando que un re-login sync funcione si lo intentás manualmente — no parte del test).

**Pre-condition:** `packages/iol-client/.env` con `IOL_USER` + `IOL_PASSWORD` reales presentes (gitignored, ya configurado).

**Post-condition (cuando lo corras y pase):**
1. Marcar `result: pass` en la entrada de abajo
2. Actualizar el frontmatter de este archivo: `status: partial` → `status: complete`
3. Actualizar el frontmatter de `03-VERIFICATION.md`: `status: human_needed` → `status: passed`
4. Commit ambos: `docs(03): mark IOL-05 live opt-in verified by human`

**result:** [pending]

**why_human:** Pitfall 9 (CONCERNS.md L25-29) — el password grant con credenciales inválidas puede gatillar lockout silencioso de la cuenta IOL real. La automatización del executor no puede correr esto sin supervisión humana porque:
- Cada retry consume un intento de bad-creds contra producción
- Si el run anterior dejó el contador cerca del threshold, una segunda corrida puede lockear la cuenta
- La decisión de cuándo correrlo depende del contexto operacional del usuario (cuántos intentos ya consumió esa sesión, horario de la cuenta, etc.)

Por D-IOL-1 y la convención de Pitfall 9, IOL-05 es **opt-in deliberado por humano** y queda fuera del scope automatizable. La implementación en `main_iol.py:1380-1462` (`probe_auth_401`) está completa y verificada por code review (CR-03 ya fixed: `probe_auth_401` no destruye `_refresh_token` cacheado).

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps

(ninguno — el phase está estructuralmente completo, solo falta el opt-in live de IOL-05)
