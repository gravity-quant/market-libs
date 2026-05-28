"""Tests del harness de verificación: anonymize + Denylist (HARN-06/D-10).

Estos tests prueban la propiedad central del pipeline de anonimización:

- Las claves PII del denylist se reemplazan por un valor sintético de la *misma
  forma* (dígitos->0, letras->x) o por un reemplazo explícito.
- Los valores no-PII relevantes para el formato (p.ej. el decimal AR ``"1.415,00"``)
  se preservan verbatim, de modo que el fixture anonimizado todavía reproduce el bug.
- El recorrido es recursivo: claves PII a cualquier profundidad se reemplazan.
"""

from __future__ import annotations

from verification.anonymize import Denylist, anonymize


def test_pii_key_replaced_with_same_shape_synthetic() -> None:
    """Test 1: una clave PII se reemplaza por un sintético de misma longitud (dígitos->0)."""
    deny = Denylist("higyrus", frozenset({"idCuenta"}))
    result = anonymize({"idCuenta": "12345", "x": 1}, deny)
    assert result["idCuenta"] == "00000"
    assert result["x"] == 1


def test_format_relevant_non_pii_value_preserved_verbatim() -> None:
    """Test 2: un decimal AR bajo clave NO denylisted se conserva tal cual."""
    deny = Denylist("amb", frozenset({"idCuenta"}))
    result = anonymize({"idCuenta": "12345", "monto": "1.415,00"}, deny)
    assert result["idCuenta"] == "00000"
    assert result["monto"] == "1.415,00"


def test_explicit_replacement_overrides_synthetic() -> None:
    """Test 3: un replacement explícito se usa en lugar del sintético calculado."""
    deny = Denylist(
        "higyrus",
        frozenset({"idCuenta"}),
        replacements={"idCuenta": "ANON-0001"},
    )
    result = anonymize({"idCuenta": "12345"}, deny)
    assert result["idCuenta"] == "ANON-0001"


def test_recursive_walk_replaces_denylisted_keys_at_any_depth() -> None:
    """Test 4: dicts/listas anidados se recorren; claves PII se reemplazan en profundidad."""
    deny = Denylist("higyrus", frozenset({"cuit", "titular"}))
    payload = {
        "cuentas": [
            {"cuit": "20304050607", "titular": "Juan Perez", "saldo": "1.000,50"},
            {"cuit": "27101112139", "titular": "Ana Gomez", "saldo": "2.500,00"},
        ],
        "meta": {"titular": "Empresa SA"},
    }
    result = anonymize(payload, deny)
    assert result["cuentas"][0]["cuit"] == "00000000000"
    assert result["cuentas"][0]["titular"] == "xxxx xxxxx"
    assert result["cuentas"][0]["saldo"] == "1.000,50"
    assert result["cuentas"][1]["cuit"] == "00000000000"
    assert result["meta"]["titular"] == "xxxxxxx xx"


def test_synthetic_preserves_scalar_types() -> None:
    """Los sintéticos preservan el tipo: int->0, float->0.0, bool igual."""
    deny = Denylist("x", frozenset({"a", "b", "c", "d"}))
    result = anonymize({"a": 42, "b": 3.14, "c": True, "d": False}, deny)
    assert result["a"] == 0
    assert result["b"] == 0.0
    assert result["c"] is True
    assert result["d"] is False


def test_dict_value_under_pii_key_is_fully_scrubbed() -> None:
    """CR-01: un dict bajo una clave PII NO debe sobrevivir verbatim.

    Antes del fix, ``_synthetic`` caía al ``return value`` para contenedores y la
    PII anidada se filtraba intacta. Ahora todo el subárbol se sanea.
    """
    deny = Denylist("higyrus", frozenset({"titular"}))
    result = anonymize({"titular": {"nombre": "Juan Perez", "dni": "12345"}}, deny)
    assert result["titular"] == {"nombre": "xxxx xxxxx", "dni": "00000"}
    # La PII original nunca aparece en la salida.
    assert "Juan Perez" not in str(result)
    assert "12345" not in str(result)


def test_list_value_under_pii_key_is_fully_scrubbed() -> None:
    """CR-01: una lista bajo una clave PII se sanea hoja por hoja, sin filtrar PII."""
    deny = Denylist("higyrus", frozenset({"titulares"}))
    result = anonymize({"titulares": ["Juan Perez", "Ana Gomez"]}, deny)
    assert result["titulares"] == ["xxxx xxxxx", "xxx xxxxx"]
    assert "Juan Perez" not in str(result)
    assert "Ana Gomez" not in str(result)
