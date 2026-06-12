"""Tests del harness de verificación: schema_of (D-12) y capture (HARN-06/D-11).

Estos tests prueban estructuralmente la propiedad PII-safe del pipeline:

- ``schema_of`` reduce cualquier payload a claves + nombres de tipo, nunca valores.
- ``capture`` escribe el payload crudo SÓLO bajo el staging gitignored
  ``.planning/verification/captures/`` (la ruta cruda nunca es committeable).

Viven bajo ``packages/<pkg>/tests/`` porque ``testpaths=["packages"]`` no colecta
``verification/``; el módulo ``verification`` se resuelve porque la raíz del repo
está en ``sys.path`` (Patrón 1 de la investigación).
"""

from __future__ import annotations

from pathlib import Path

from verification.capture import capture
from verification.schema import schema_of


def test_schema_of_dict_returns_keys_and_type_names_sorted() -> None:
    """Test 1: un dict se reduce a {clave: nombre-de-tipo}, ordenado, sin valores."""
    result = schema_of({"b": "1.415,00", "a": 5})
    assert result == {"a": "int", "b": "str"}
    # Ningún valor del payload aparece en el resultado (PII-free por construcción).
    assert "1.415,00" not in result.values()
    assert 5 not in result.values()


def test_schema_of_list_uses_first_element_and_handles_empty() -> None:
    """Test 2: una lista usa el primer elemento como muestra; vacía -> []."""
    assert schema_of([{"x": 1}]) == [{"x": "int"}]
    assert schema_of([]) == []


def test_schema_of_nested_and_scalars_reduce_recursively() -> None:
    """Test 3: dict/list anidados reducen recursivamente; escalares -> nombre de tipo."""
    payload = {"outer": {"items": [{"price": 1.5, "name": "AL30"}], "flag": True}}
    assert schema_of(payload) == {
        "outer": {"flag": "bool", "items": [{"name": "str", "price": "float"}]}
    }
    assert schema_of(1.5) == "float"
    assert schema_of(None) == "NoneType"


def test_capture_writes_under_gitignored_staging_dir(tmp_path: Path) -> None:
    """Test 4: capture escribe bajo .planning/verification/captures/ (gitignored)."""
    payload = {"sample": "value", "n": 1}
    path = capture("ambito", "dollar", payload)
    try:
        # (a) La ruta devuelta vive bajo el staging gitignored.
        parts = path.parts
        assert ".planning" in parts
        assert "verification" in parts
        assert "captures" in parts
        # El staging dir es el ancestro inmediato del archivo.
        assert path.parent.name == "captures"
        assert path.parent.parent.name == "verification"
        # (b) El archivo se escribió con el nombre <pkg>-<endpoint>.json.
        assert path.name == "ambito-dollar.json"
        assert path.exists()
    finally:
        # No dejar el probe en disco (de todas formas está gitignored).
        if path.exists():
            path.unlink()
