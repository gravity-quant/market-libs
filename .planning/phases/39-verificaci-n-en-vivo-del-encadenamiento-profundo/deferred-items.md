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
