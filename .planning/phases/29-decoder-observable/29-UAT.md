---
status: complete
phase: 29-decoder-observable
source: [29-VERIFICATION.md]
started: 2026-08-19T00:00:00Z
updated: 2026-08-19T00:00:00Z
---

## Current Test

number: 1
name: WR-04 — decisión sobre campos opcionales-por-default ante `missing`
expected: |
  Decisión del operator: los campos con default de dataclass (market-data `Symbol.id`/`market_id`/`created_at`/`updated_at`; los `default_factory=X.empty()` de matriz) hoy emiten WARNING `missing` en payloads normales y son fatales en modo estricto. Confirmar si ese comportamiento queda como está (los campos genuinamente nullables se declaran `| None` con evidencia viva en F33) o si el walker debe tratar default-presente como opcional.
awaiting: resolved

## Tests

### 1. WR-04 — campos opcionales-por-default ante `missing`
expected: Decisión registrada (comportamiento actual confirmado, o cambio de política parametrizada, o diferido a F33 con destino nombrado)
result: passed — operator (sebadlf, 2026-08-19) eligió "Mantener estricto": missing = divergencia aunque exista default; los campos genuinamente nullables se declaran `| None` con evidencia viva en F33 (se corrige la declaración, no el decoder).

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
