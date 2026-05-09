"""Helpers de parsing compartidos entre el cliente sync y async."""

from __future__ import annotations


def parse_ar_decimal(value: str) -> float:
    """Convierte un decimal en formato argentino (`"1.415,00"`) a float."""
    return float(value.replace(".", "").replace(",", "."))
