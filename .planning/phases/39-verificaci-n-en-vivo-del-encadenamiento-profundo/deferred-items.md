# Phase 39 — Deferred items

Hallazgos fuera del alcance del plan que los descubrió, registrados para que la
fase siguiente los encuentre predichos en vez de redescubrirlos.

---

## D39-01 — iol: `204` / cuerpo vacío escapa la jerarquía `IOLClientError`

- **Descubierto en:** 39-02 Task 1 (suite `packages/iol-client/tests/test_deep_chain_edges.py`).
- **Medido:** `parse_get_quote_response`, `parse_get_instruments_by_type_response` y
  `_parse_list_or_raise` de `iol_client._core` hacen `resp.read()` →
  `raise_for_response(resp)` (204 es éxito, no levanta) → `resp.json()`, que sobre un
  cuerpo vacío levanta `json.decoder.JSONDecodeError`. La excepción **no** es
  `IOLClientError` ni ninguna de sus subclases, así que un caller que envuelve las
  llamadas en `except IOLClientError` no la atrapa.
- **Contraste:** higyrus sí tolera 204 — `higyrus_client._core._parse_list_or_raise`
  devuelve `[]` cuando `status_code == 204 or not body`. matriz tiene la misma
  ausencia de tolerancia que iol (`parse_envelope_response` también termina en
  `resp.json()`).
- **Por qué NO se arregla acá:** el plan 39-02 declara `files_modified` con **sólo**
  los tres archivos de test; darle tolerancia a 204 a iol es un cambio de
  comportamiento del paquete publicado. La decisión de alcance ya está registrada
  en el docstring de `iol_client._core._parse_list_or_raise` ("copiar el helper de
  higyrus metería una tolerancia a 204 que iol hoy no tiene — un cambio de
  comportamiento fuera del alcance de este plan"), o sea que esto **no es un
  descubrimiento nuevo**, es la misma deuda con una medición encima.
- **No queda en silencio:** `test_quote_204_empty_body_does_not_break_the_chain`
  (y su gemelo async) assertea el tipo exacto de la excepción. El día que iol gane
  la tolerancia, esos dos tests son los primeros en ponerse rojos.
- **Propiedad D-12 igualmente satisfecha:** `json.JSONDecodeError` es subclase de
  `ValueError`; no es `AttributeError` ni `TypeError`, así que la cadena profunda no
  se rompe — no llega a haber modelo que desreferenciar.
- **Destino sugerido:** milestone posterior, junto con la decisión de si la
  tolerancia a 204 debe ser uniforme entre los 6 paquetes o una política por
  paquete (el eje "never harmonize" de `29-SEMANTICS-MATRIX.md` sugiere lo segundo).

---

## D39-02 — matriz: `204` / cuerpo vacío escapa la jerarquía `MatrizClientError`

- **Descubierto en:** 39-02 Task 3 (suite `packages/matriz-client/tests/test_deep_chain_edges.py`).
- **Medido:** `matriz_client._core.parse_envelope_response` consume el body, pasa el
  status check (204 es éxito) y llama `resp.json()`, que levanta
  `json.decoder.JSONDecodeError`. No es `PrimaryAPIError`.
- **Mismo razonamiento de alcance y misma disposición que D39-01.** Asertado
  explícitamente en `test_market_data_204_empty_body_does_not_break_the_chain`.

---

## D39-03 — `append_finding` de los probes NO es content-addressed cross-run

- **Descubierto en:** 39-07 Task 1, corriendo el driver de matriz dos veces (el plan
  pide correr cada driver individualmente **y después** `main_verify.py`, que los
  vuelve a correr a todos).
- **Premisa falsificada:** el plan 39-07 afirma —y el 39-01 lo asumía— que "la
  deduplicación por título es content-addressed cross-run". **Lo es sólo donde el
  llamador lo pide.** `verification/findings.py:597` declara
  `idempotent_by_title: bool = False` y los ~40 call sites de probe de los drivers
  usan el default; el único sitio que lo activa es el finding terminal
  (`main_matriz.py:3071`, HARN-10). Como `_seed_fid_counter()` sube el contador por
  encima del máximo fid ya registrado (D-16/D-24), **cada re-corrida re-emite cada
  finding no-terminal bajo un fid nuevo**, duplicando su bloque.
- **Medido:** dos corridas consecutivas de `main_matriz.py` produjeron 16 bloques
  duplicados por título (F-57..F-59 de F-16..F-18, F-61..F-66 de F-03..F-08,
  F-67..F-70 de F-19..F-22, F-106..F-108 de F-53..F-55). El par F-02 / F-10
  (`prod-vs-remarkets divergence acknowledged`), que existía en el ledger desde antes
  de esta fase, es el mismo síntoma con años de antigüedad. Una corrida de
  `main_verify.py` agregó además 40+ bloques `OPEN` duplicados al ledger de
  `market-data-client`, un paquete que D-07 declara fuera de alcance.
- **Cómo se manejó en 39-07:** los ledgers se restauraron a su estado previo y se
  produjo **una sola** corrida autoritativa por paquete, de modo que el censo del
  39-08 no herede duplicados que son un artefacto del procedimiento de ejecución y no
  una medición. El ledger de `market-data-client` quedó byte-idéntico (D-07).
- **Por qué NO se arregla acá:** activar `idempotent_by_title=True` en los call sites
  de probe toca los cuatro `main_*.py` —ninguno está en `files_modified` del plan, y
  `main_market_data.py` está explícitamente prohibido por D-07— y tiene un tradeoff
  real: un finding cuyo **contenido** cambia con el título igual dejaría de
  actualizarse. Es una decisión de diseño del harness, no un fix mecánico.
- **Destino sugerido:** deuda de harness junto a `HARN-VERIF-01`. Elevado al operador
  en el checkpoint de la Task 3 del plan 39-07.
- **Resuelto por el operador (checkpoint Task 3, 2026-08-30, respuesta verbatim
  "Approved"):** confirmado **fuera de alcance de la Phase 39**, tracked acá junto a
  `HARN-VERIF-01`. No es una divergencia entre cliente y API —es una propiedad del
  harness de verificación— así que D-08 no aplica y no requiere destino nombrado de
  fase. Se mantiene la mitigación de procedimiento ya aplicada: una sola corrida
  autoritativa por paquete.

---

## D39-04 — un mock que codificaba una forma que el vendor no emite

- **Descubierto en:** 39-07 Task 2, al escribir la regresión de F-43/F-44.
- **Medido:** `packages/matriz-client/tests/test_client.py::test_get_instruments_by_segment_url_invariant_phase5`
  mockea `/rest/instruments/bySegment` con el elemento **anidado**
  (`{"instrumentId": {...}, "cficode": ...}`). Los baselines en vivo de los dos
  venues registran el elemento **plano** (`{marketId, symbol}`) desde 2026-06-10. El
  test pasaba en verde mientras el método perdía el 100% de su payload en producción.
- **Por qué importa más allá de este bug:** es el modo de falla que justifica la fase.
  Una suite mockeada sólo puede confirmar la forma que quien la escribió supuso; sólo
  la corrida en vivo la falsifica. El mock **no** se corrigió en 39-07 porque su
  aserción declarada es la URL, no la forma del elemento, y la forma real ya quedó
  pinneada por `test_instruments_flat_identifier_shape.py` contra las capturas.
- **Destino sugerido:** barrido de mocks contra los baselines committeados — un guard
  que compare la forma de cada payload mockeado contra
  `.planning/verification/schemas/` cerraría esta clase entera.
