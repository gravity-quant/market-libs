# Deferred Items — Phase 42

Hallazgos fuera del alcance de los planes de esta fase. Se registran acá en vez de
arreglarse, por la regla de límite de alcance: sólo se auto-corrige lo que las tasks
de esta fase causaron.

---

## D42-DEF-01 — Exposición pre-existente del base URL del vendor en `higyrus-client-findings.md`

- **Descubierto en:** plan 42-03, Task 1 (chequeo de no-fuga de la sesión)
- **Archivo:** `.planning/verification/higyrus-client-findings.md`, **línea 5** del header
- **Forma de la línea (valor elidido):** `- Resolved base URL / env: <BASE_URL_ELIDIDA>`
- **Clase:** exposición de dato de entrada del tipo que **T-39-04 / C-4** prohíbe

### Por qué NO se corrigió en esta fase

1. **Es pre-existente, no causado por esta sesión.** `git status --porcelain` sobre el
   archivo es vacío: es byte-idéntico a HEAD. El último commit que lo tocó es `fbb69c3`
   (Phase 17, `test(17-02)`), y el header viene de `e8307a6` (Phase 11, migración
   HARN-07). La corrida de esta fase **no lo modificó** — el corte temprano de
   vendor-unreachable de `main_higyrus.py:2908` sale antes de cualquier `append_finding`.
2. **Es un ledger versionado y append-only por diseño** (HARN-07). Reescribir su header
   a mano sería exactamente la clase de manipulación de evidencia que
   `verification/test_finding_count_consistency.py` y el precedente T-39-12 existen para
   impedir, y arriesga el triage de operador de los 2 findings que el archivo lleva.
3. **La política T-39-04 se escribió en la Phase 39**, después de que este header se
   generara. El archivo es evidencia de la era anterior a la política, no una violación
   nueva de ella.

### Alcance del chequeo de no-fuga que SÍ pasó

Los artefactos **de esta sesión** están limpios (`LEAK-CHECK ... CLEAN`):
`/tmp/42-higyrus-probe.log`, `/tmp/42-higyrus-run.log`,
`.planning/verification/run-evidence/higyrus-client.json`, y el `42-03-SUMMARY.md`.

### Destino sugerido

**Phase 45 (HARN-01 / HARN-03 / HARN-04)** — es la fase que ya tiene mandato para tocar
el harness de findings y que debe decidir por escrito qué se repara y qué se acepta como
deuda. La decisión pendiente es de tres vías, y ninguna es automática:

- **(a) Redactar el header** de los 4 ledgers de `verification/` con un `<REDACTED>`, y
  cambiar `verification/findings.py` para que nunca vuelva a escribir un base URL
  resuelto. Requiere reescribir historia committeada de evidencia → necesita decisión
  humana explícita.
- **(b) Aceptar la deuda formalmente** con su razón escrita: el `.planning/` de este repo
  no es público y el hostname ya vive en `packages/higyrus-client/.env` local.
- **(c) Cambiar sólo `findings.py` hacia adelante** y dejar los headers históricos como
  están, documentando la fecha de corte de la política.

**No decidir esto en la Phase 42** es deliberado: la 42 mide alcanzabilidad en vivo, y
mezclar una redacción de evidencia histórica con una corrida en vivo confunde qué
artefacto respalda qué afirmación.
