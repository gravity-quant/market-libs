"""D-06 / T-27-06 guard — la config de calendar que PERSISTE es inalcanzable desde el driver.

Decisión del operator (D-06, 2026-08-01): ``main_market_data.py`` ejercita en vivo
**únicamente** ``POST /calendar/config/preview``, documentado por la OpenAPI en
vivo como *"What this window would do, without saving it. **Writes nothing**"*.

El razonamiento no es "por las dudas". ``DELETE /calendar/config`` **resetea a los
defaults del SERVIDOR**; no restaura el valor que había antes. Es decir: un DELETE
no puede funcionar como cleanup de un PUT. Y como ``market_hours`` es una
configuración COMPARTIDA por todo consumidor de develop, un ``PUT`` real la
dejaría alterada sin ninguna ruta de vuelta al valor original. Por eso los dos
endpoints que persisten quedan operator-gated fuera del run en vivo.

Este guard camina el AST del driver y afirma:

1. que **ningún** call site invoca los métodos del cliente ``set_calendar_config``
   / ``delete_calendar_config`` ni sus builders de ``_core``;
2. que esos nombres no aparecen siquiera como acceso a atributo o referencia
   —para que tampoco se puedan alcanzar de forma indirecta (``fn =
   client.set_calendar_config``); y
3. que el guard **no es vacuo**: la superficie de *preview* SÍ está referenciada,
   así que un rename que apagara la vigilancia deja el test en RED en vez de
   pasar sin mirar nada.

La cobertura de ambos endpoints NO desaparece: sigue viva en los tests mockeados
del paquete (``packages/market-data-client/tests/test_calendar_write.py``), y la
limitación queda registrada como finding ``EXPECTED`` por
``probe_expected_put_config_operator_gated``.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

# Métodos públicos del cliente que PERSISTEN configuración de mercado.
_BANNED_CLIENT_METHODS = frozenset({"set_calendar_config", "delete_calendar_config"})

# Sus builders en ``market_data_client._core``: prohibirlos cierra la ruta de
# escape que sería construir el spec a mano y despacharlo con un helper crudo.
_BANNED_BUILDERS = frozenset(
    {"build_set_calendar_config_request", "build_delete_calendar_config_request"}
)

_BANNED = _BANNED_CLIENT_METHODS | _BANNED_BUILDERS

# La superficie que SÍ debe estar presente (no-vacuidad).
_PREVIEW_METHOD = "preview_calendar_config"
_PREVIEW_BUILDER = "build_preview_calendar_config_request"


def _driver_tree() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))


def _called_name(node: ast.Call) -> str | None:
    """Nombre invocado de un ``Call``: ``f(...)`` -> ``f``; ``m.f(...)`` -> ``f``."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _called_names(tree: ast.Module) -> set[str]:
    return {
        name
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and (name := _called_name(node)) is not None
    }


def _referenced_names(tree: ast.Module) -> set[str]:
    """Todo identificador alcanzable: atributos (``x.attr``) y nombres (``attr``).

    Deliberadamente MÁS amplio que los call sites: ``fn = client.set_calendar_config``
    seguido de ``fn(...)`` no sería un ``Call`` con ese nombre, pero sí un
    ``Attribute``. Los strings NO cuentan (un docstring que menciona el endpoint
    no es una ruta de ejecución), que es exactamente la distinción que hace este
    guard preciso en vez de un grep.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    return names


def test_driver_has_no_persisting_config_call_site() -> None:
    """Ningún call site del driver invoca la superficie de config que persiste (D-06)."""
    offenders = sorted(_BANNED & _called_names(_driver_tree()))

    assert not offenders, (
        f"{_DRIVER}: call site a la superficie de config que PERSISTE: {offenders}. "
        f"D-06 la deja operator-gated fuera del run en vivo: DELETE /calendar/config "
        f"resetea a los defaults del servidor y NO restaura el valor previo, así que "
        f"no sirve de cleanup para un PUT, y un PUT real dejaría clobbereada la "
        f"configuración COMPARTIDA de develop. Usá POST /calendar/config/preview."
    )


def test_driver_never_references_the_persisting_config_surface() -> None:
    """Los nombres prohibidos no aparecen ni como atributo ni como referencia."""
    offenders = sorted(_BANNED & _referenced_names(_driver_tree()))

    assert not offenders, (
        f"{_DRIVER}: referencia (atributo o nombre) a la superficie de config que "
        f"PERSISTE: {offenders}. Alcanzarla indirectamente —``fn = "
        f"client.set_calendar_config`` y después ``fn(...)``— evadiría el chequeo de "
        f"call sites, así que también está prohibido (D-06 / T-27-06)."
    )


def test_config_write_guard_is_not_vacuous() -> None:
    """El driver SÍ ejercita el preview: un rename deja este guard en RED, no ciego."""
    tree = _driver_tree()
    called = _called_names(tree)

    assert _PREVIEW_METHOD in called, (
        f"{_DRIVER} debe invocar {_PREVIEW_METHOD}: es el ÚNICO write-path de config "
        f"seguro en vivo (D-06). Sin él este guard no vigilaría nada — pasaría por "
        f"ausencia total de cobertura de config en vez de por cumplimiento."
    )
    assert _PREVIEW_BUILDER in called, (
        f"{_DRIVER} debe invocar {_PREVIEW_BUILDER}: el doble-fire con gate del "
        f"experimento D-19 pasa por el builder, no sólo por el método público."
    )
