---
phase: 01-safety-harness-verification-infrastructure
verified: 2026-05-27T03:30:00Z
status: passed
score: 5/5 must-haves verificados
overrides_applied: 0
---

# Fase 01: Safety Harness & Verification Infrastructure — Informe de Verificacion

**Objetivo de la fase:** Toda convencion de seguridad e infraestructura de verificacion esta en su lugar y
probada — credenciales nunca se filtran, mutaciones nunca disparan por accidente, y cada fase posterior tiene
un formato de hallazgos listo, un pipeline live-payload→fixture, y un marker de test offline-limpio.

**Verificado:** 2026-05-27T03:30:00Z
**Estado:** PASSED
**Re-verificacion:** No — verificacion inicial

---

## Logro del Objetivo

### Verdades Observables

| #  | Verdad | Estado | Evidencia |
|----|--------|--------|-----------|
| 1  | `main_*.py` con env vars faltantes imprime `SKIPPED <pkg>: missing X, Y` y sale 0 sin bloquear los demas (HARN-01) | VERIFICADO | `env -u IOL_USER -u IOL_PASSWORD uv run --package iol-client python main_iol.py` → `SKIPPED iol-client: missing IOL_USER, IOL_PASSWORD` + exit 0; idem wallets. Patron en los 4 drivers con creds. |
| 2  | Mutaciones de matriz son inalcanzables por defecto: `VERIFY_MUTATING=1` AND host exacto `api.remarkets.primary.com.ar` (HARN-02) | VERIFICADO | `mutation_gate.py` usa `urlsplit(base).hostname != _SANDBOX_HOST` (CR-02 hostname exacto, no substring). Test de bypass con URL de prod retorna False. Default sin flag → `SKIPPED (mutating, guard off)`. |
| 3  | Helper de redaccion cableado en todos los drivers: tokens/passwords nunca impresos completos (HARN-03) | VERIFICADO | `redact("supersecret-token")` → `"supe…"`. `safe_print` enmascara secretos >=4 chars + patron Bearer (WR-03). `main_iol.py` usa `redact(token)` (ya no `token[:12]`). `CR-01`: `anonymize` sanea subarboles PII completos via `_scrub`. |
| 4  | `@pytest.mark.live` registrado en `conftest.py` raiz + flag `--live` que excluye tests en vivo por defecto (HARN-04) | VERIFICADO | `uv run pytest` → `145 passed, 1 deselected`. `uv run pytest --live` → `1 passed` (live probe). `--strict-markers` limpio en toda la coleccion. |
| 5  | Formato de hallazgos clasificado y pipeline live-payload→fixture-anonimizado existen y estan documentados (HARN-05, HARN-06) | VERIFICADO | `.planning/verification/FINDINGS-TEMPLATE.md` contiene los 7 tipos (SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT) y el ciclo OPEN→CONFIRMED→FIXED+EXPECTED/NO-FIX. Pipeline: `capture()` → staging gitignored `.planning/verification/captures/` → `anonymize()` preserva formato (decimal AR `"1.415,00"` intacto bajo clave no-PII). `git check-ignore` confirma captures/ gitignored. |

**Puntuacion:** 5/5 verdades verificadas

---

### Artefactos Requeridos

| Artefacto | Descripcion | Estado | Detalle |
|-----------|-------------|--------|---------|
| `conftest.py` | Hooks pytest: `--live`, marker `live`, deselect-by-default | VERIFICADO | `pytest_addoption`, `pytest_configure`, `pytest_collection_modifyitems` presentes. Bootstrap `sys.path` para que `verification/` sea importable. |
| `verification/__init__.py` | Barrel exportando los helpers publicos | VERIFICADO | `__all__` contiene `require_env`, `redact`, `safe_print`, `mutating_allowed`, `schema_of`, `anonymize`, `Denylist`, `capture`, `new_findings`, `write_findings`. Sin `pyproject.toml`, no es workspace member. |
| `verification/redaction.py` | `redact()` + `safe_print()` con guarda de secreto vacio (HARN-03) | VERIFICADO | `len(secret) >= 4` guard presente (1 match). Patron Bearer adicional (`_BEARER = re.compile`). `__all__ = ["redact", "safe_print"]`. |
| `verification/env_gate.py` | `require_env()` emitiendo linea SKIPPED verbatim (HARN-01) | VERIFICADO | f-string verbatim presente. 0 ocurrencias de `raise` o `sys.exit`. `__all__ = ["require_env"]`. |
| `verification/mutation_gate.py` | `mutating_allowed()` doble gate VERIFY_MUTATING=1 + host remarkets (HARN-02) | VERIFICADO | `urlsplit(base).hostname != _SANDBOX_HOST` (CR-02 hostname exacto). Import perezoso de `matriz_client` dentro de la funcion. `__all__ = ["mutating_allowed"]`. |
| `verification/schema.py` | `schema_of()` snapshot claves+tipos, PII-free por construccion (HARN-06/D-12) | VERIFICADO | `schema_of({"b": "1.415,00", "a": 5})` → `{"a": "int", "b": "str"}`. Sin valores en el output. |
| `verification/capture.py` | `capture()` escribe payloads crudos al staging gitignored (HARN-06/D-11) | VERIFICADO | Ruta resuelta relativa al modulo, no al cwd. Escribe exclusivamente en `.planning/verification/captures/`. |
| `verification/anonymize.py` | `Denylist` + `anonymize()` reemplazo PII preservando formato (HARN-06/D-10) | VERIFICADO | `@dataclass(frozen=True, slots=True)`. `_scrub()` para subarboles PII (CR-01). Decimal AR `"1.415,00"` intacto bajo clave no-PII. Sin Faker (stdlib `re`). |
| `verification/findings.py` | Helper plantilla de hallazgos (HARN-05/D-07/08/09) | VERIFICADO | `FINDING_CLASSES` (7 clases), `STATUS_LIFECYCLE` (5 estados). `new_findings()` + `write_findings()` exportados. |
| `.planning/verification/FINDINGS-TEMPLATE.md` | Plantilla documentada de hallazgos (HARN-05) | VERIFICADO | Encabezado ART, tabla indice, 7 clases fijas, ciclo de estados, pipeline dos etapas con revision humana obligatoria. Sin campo de severidad. |
| `.gitignore` | Entrada que excluye `.planning/verification/captures/` (HARN-06) | VERIFICADO | Linea `.planning/verification/captures/` en `.gitignore`. `git check-ignore .planning/verification/captures/probe.json` → exit 0. |
| `main_iol.py` | Driver IOL gateado + redactado | VERIFICADO | `require_env("iol-client", ["IOL_USER", "IOL_PASSWORD"])`. `redact(token)` (ya no `token[:12]`). |
| `main_higyrus.py` | Driver Higyrus gateado + redactado | VERIFICADO | `require_env("higyrus-client", ["HIGYRUS_USER", "HIGYRUS_PASSWORD", "HIGYRUS_BASE_URL"])`. `safe_print` con secrets resueltos. |
| `main_matriz.py` | Driver Matriz gateado + redactado + mutation-gated | VERIFICADO | `require_env(["PRIMARY_USER", "PRIMARY_PASSWORD"])`. `mutating_allowed()` guarda rama mutante. |
| `main_wallets.py` | Driver Wallets gateado + redactado | VERIFICADO | `require_env("wallets-client", ["WALLETS_TOKEN", "WALLETS_BASE_URL"])`. |
| `main_ambito_financiero.py` | Driver Ambito — sin require_env (API publica, sin creds) | VERIFICADO | Ausencia de `require_env(` confirmada por grep. Intencional segun el plan. |
| `main_verify.py` | Runner agregado RAN/SKIPPED/FAILED (HARN-01/D-14) | VERIFICADO | `subprocess` por driver. Regex `_ENV_SKIP = re.compile(r"^SKIPPED \S.*:")` distingue env-skip de mutation-skip (WR-01/WR-02). Nunca re-emite stdout crudo. |
| `packages/ambito-financiero-client/tests/test_harness_live_probe.py` | Test `@pytest.mark.live` de ejemplo (HARN-04) | VERIFICADO | `1 deselected` por defecto, `1 passed` con `--live`. |
| `packages/ambito-financiero-client/tests/test_harness_redaction.py` | Tests unitarios redact/safe_print (HARN-03) | VERIFICADO | Cubre: prefix+ellipsis, empty/short guard, safe_print masking, Bearer masking. |
| `packages/ambito-financiero-client/tests/test_harness_env_gate.py` | Tests unitarios require_env (HARN-01) | VERIFICADO | Cubre: all-missing, partial, all-present, no-raise contract. |
| `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py` | Tests unitarios mutating_allowed (HARN-02) | VERIFICADO | Cubre: flag-off, flag-on+remarkets, adversarial prod-URL bypass, valor no-"1". |
| `packages/ambito-financiero-client/tests/test_harness_schema.py` | Tests unitarios schema_of + capture (HARN-06) | VERIFICADO | Cubre: dict ordenado, list, nested scalars, ruta gitignored. |
| `packages/ambito-financiero-client/tests/test_harness_anonymize.py` | Tests unitarios anonymize (HARN-06) | VERIFICADO | Cubre: PII replaced, decimal AR preservado, explicit replacement, recursion. |

---

### Verificacion de Key Links

| Desde | Hacia | Via | Estado | Detalle |
|-------|-------|-----|--------|---------|
| `conftest.py` | coleccion pytest | `pytest_addoption` + `pytest_configure` + `pytest_collection_modifyitems` | WIRED | `config.getoption("--live")` presente. `pytest_deselected` llamado cuando no se pasa `--live`. |
| `main_iol.py` | `verification.require_env` | `from verification import require_env` + `if not require_env(...): sys.exit(0)` | WIRED | Importado y usado en `main()`. |
| `main_matriz.py` | `verification.mutating_allowed` | `from verification import mutating_allowed` + `if mutating_allowed():` | WIRED | Importado y usado como guarda de rama mutante. |
| `verification/mutation_gate.py` | `matriz_client.client._base_url` | Import perezoso dentro de `mutating_allowed()` + `urlsplit(base).hostname` | WIRED | Import lazy post-flag-check. Estado de modulo leido en vivo. |
| `verification/env_gate.py` | `os.getenv` | Presencia de `os.getenv(n)` para cada nombre en `names` | WIRED | Lista comprehension `[n for n in names if not os.getenv(n)]`. |
| `verification/capture.py` | `.planning/verification/captures/` | `pathlib.Path` write_text al directorio gitignored | WIRED | Ruta resuelta relativa al modulo (no al cwd). |
| `verification/anonymize.py` | `Denylist` | Recorrido recursivo dict/list con check `k not in deny.keys` | WIRED | `_scrub()` para subarboles PII completos (CR-01). |
| `main_verify.py` | cinco drivers `main_*.py` | `subprocess.run(["uv", "run", "--package", pkg, "python", script])` | WIRED | Lista `_DRIVERS` con los 5 pares (paquete, script). Nunca re-emite stdout crudo del hijo. |

---

### Trazado de Flujo de Datos (Nivel 4)

Los artefactos de esta fase son tooling de infraestructura (no componentes que rendericen datos dinamicos de una API en vivo). El flujo que se verifica es el pipeline de seguridad:

| Artefacto | Variable de datos | Fuente | Produce datos reales | Estado |
|-----------|------------------|--------|---------------------|--------|
| `redaction.py::safe_print` | `masked` (texto con secretos enmascarados) | `secrets` list filtrada (>=4 chars) + patron `_BEARER` | Si — comportamiento verificado con capsys + prueba behavioral | FLOWING |
| `mutation_gate.py::mutating_allowed` | `base` (URL base resuelta en vivo) | `matriz_client.client._base_url` (estado de modulo en el momento del guard) | Si — estado resuelto en tiempo de ejecucion, no constante | FLOWING |
| `anonymize.py::anonymize` | payload anonimizado | `Denylist` + `_synthetic()` / `_scrub()` para subarboles | Si — decimal AR preservado, claves PII sustituidas por sinteticos | FLOWING |
| `capture.py::capture` | ruta del archivo escrito | `_CAPTURES_DIR` resuelto relativo al modulo | Si — escribe a staging gitignored, ruta verificada por test | FLOWING |

---

### Spot-Checks de Comportamiento

| Comportamiento | Comando | Resultado | Estado |
|----------------|---------|-----------|--------|
| IOL SKIPPED con creds faltantes | `env -u IOL_USER -u IOL_PASSWORD uv run --package iol-client python main_iol.py` | `SKIPPED iol-client: missing IOL_USER, IOL_PASSWORD` + exit 0 | PASS |
| Wallets SKIPPED con creds faltantes | `env -u WALLETS_TOKEN -u WALLETS_BASE_URL uv run --package wallets-client python main_wallets.py` | `SKIPPED wallets-client: missing WALLETS_TOKEN, WALLETS_BASE_URL` + exit 0 | PASS |
| Mutation gate SKIPPED sin flag | `env -u VERIFY_MUTATING uv run --package matriz-client python -c "from verification.mutation_gate import mutating_allowed; mutating_allowed()"` | `SKIPPED (mutating, guard off)` | PASS |
| Live probe deseleccionado por defecto | `uv run pytest packages/ambito-financiero-client/tests/test_harness_live_probe.py -q` | `1 deselected` + exit 5 (ninguno seleccionado) | PASS |
| Live probe seleccionado con --live | `uv run pytest .../test_harness_live_probe.py --live -q` | `1 passed` | PASS |
| Suite offline completa | `uv run pytest -q` | `145 passed, 1 deselected` | PASS |
| Todos los tests del harness | `uv run pytest packages/ambito-financiero-client/tests/test_harness_*.py -q` | `28 passed, 1 deselected` | PASS |
| `schema_of` sin valores en output | `schema_of({"b": "1.415,00", "a": 5})` → `{"a": "int", "b": "str"}` | Sin valores reales, solo tipos | PASS |
| Decimal AR preservado por `anonymize` | `anonymize({"idCuenta": "12345", "monto": "1.415,00"}, Denylist(...))` → `idCuenta == "00000"`, `monto == "1.415,00"` | PII sustituida, formato preservado | PASS |
| `captures/` gitignored | `git check-ignore .planning/verification/captures/probe.json` | Imprime la ruta, exit 0 | PASS |
| `redact()` nunca expone valor completo | `redact("supersecret-token")` → `"supe…"` | Solo prefijo + elipsis | PASS |
| Guarda secreto vacio en `safe_print` | `safe_print("hello world", ["", "ab"])` → `"hello world\n"` | Sin insercion del marcador entre caracteres | PASS |

---

### Cobertura de Requisitos

| Requisito | Plan | Descripcion | Estado | Evidencia |
|-----------|------|-------------|--------|-----------|
| HARN-01 | 01-02, 01-03 | Env gate con linea SKIPPED verbatim; drivers salen 0 sin bloquear | SATISFECHO | `require_env()` probado. 4 drivers gateados. `main_verify.py` nunca se detiene ante SKIPPED. |
| HARN-02 | 01-02, 01-03 | Llamadas mutantes de Matriz detrás de doble gate opt-in + sandbox | SATISFECHO | `mutating_allowed()` con hostname exacto (CR-02). Gate cableado en `main_matriz.py`. Bypass con URL de prod falla safe. |
| HARN-03 | 01-01, 01-03 | Helper de redaccion que impide imprimir credenciales completas | SATISFECHO | `redact()` + `safe_print()`. Patron Bearer adicional (WR-03). `main_iol.py` ya no imprime `token[:12]`. Anonymize sanea subarboles PII (CR-01). |
| HARN-04 | 01-01 | `@pytest.mark.live` registrado + `--live` flag; CI offline determinista | SATISFECHO | `conftest.py` con 3 hooks. `145 passed, 1 deselected` offline; `1 passed` con `--live`. `--strict-markers` limpio. |
| HARN-05 | 01-04 | Registro de hallazgos clasificado con las 7 clases y ciclo de estados | SATISFECHO | `FINDINGS-TEMPLATE.md` con encabezado ART, 7 clases fijas, ciclo OPEN→CONFIRMED→FIXED+terminales. `findings.py` con `FINDING_CLASSES` y `STATUS_LIFECYCLE`. |
| HARN-06 | 01-04 | Pipeline capture→anonimizar→fixture con PII-safety por construccion | SATISFECHO | `capture()` al staging gitignored. `anonymize()` con `Denylist` preservando formato. Manual review gate documentado. `schema_of()` PII-free. |

---

### Anti-Patrones Encontrados

Ninguno encontrado. Escaneo realizado sobre los archivos modificados/creados en la fase:

| Archivo | Patron | Severidad | Impacto |
|---------|--------|-----------|---------|
| — | Sin `TBD`, `FIXME`, `XXX` no referenciados | — | — |
| — | Sin stubs (`return null`, `return {}`, `return []` como implementacion final) | — | — |
| — | Sin prints de credenciales (`token[:12]` eliminado en `main_iol.py`) | — | — |

> Los marcadores `TODO` en los archivos de plantilla son intencionales (son el contenido de la plantilla, no deuda de codigo).

---

### Verificacion Humana Requerida

No se identificaron items que requieran verificacion humana. Todos los comportamientos criticos de seguridad son verificables estaticamente o por comportamiento offline.

---

### Resumen de Gaps

No hay gaps. Las 5 verdades observables estan verificadas al nivel 1 (existencia), nivel 2 (sustantiva — no stub), nivel 3 (cableada) y nivel 4 (datos fluyendo). Los 6 requisitos HARN-01 a HARN-06 estan satisfechos. Los 4 fixes de code review (CR-01, CR-02, WR-01/WR-02, WR-03) estan incorporados en el codigo actual.

---

*Verificado: 2026-05-27T03:30:00Z*
*Verificador: Claude (gsd-verifier)*
