"""Contrato de clasificación de ``main_verify._run_driver``, pinneado (D-01).

``main_verify.py`` decide RAN / SKIPPED / FAILED por la FORMA de una línea del
hijo, y tres detalles de ese contrato son load-bearing y fáciles de romper sin
darse cuenta:

1. **Sólo se escanea ``result.stdout``.** ``_run_driver`` itera
   ``result.stdout.splitlines()`` y nunca mira ``stderr``. Por eso el aborto
   histórico de ``main_matriz.py`` —que escribía a ``stderr`` y salía con
   código 1— se clasificaba ``FAILED``: la línea existía, pero en el stream
   equivocado. La corrección de D-01 mueve esa línea a **stdout**.
2. **Los dos puntos son load-bearing.** El patrón es ``^SKIPPED \\S.*:``. La
   línea del mutation gate (``SKIPPED (mutating, guard off)``) NO los lleva a
   propósito: un read sweep exitoso con el gate de mutaciones apagado no puede
   clasificar al PAQUETE ENTERO como skip (WR-01).
3. **El código de salida no puede ser distinto de cero.** Un driver que emite
   la línea SKIPPED y además sale != 0 igual clasifica ``SKIPPED`` (la línea
   gana), pero el contrato del harness es salida limpia: ``sys.exit(0)``.

El regex clasificador se IMPORTA de ``main_verify`` en vez de re-declararse, así
que si el clasificador cambia este lock lo sigue. Las dos formas nuevas de D-01
se leen de sus drivers (``main_matriz`` / ``main_higyrus``) en vez de
re-declararse acá, así que si un driver cambia su texto a algo que el
clasificador ya no matchea, este lock enrojece.

``_run_driver`` no se invoca: lanza subprocesos ``uv run`` reales contra APIs en
vivo. Lo que se pinea es su ENTRADA (el regex) y su tabla de drivers.
"""

from __future__ import annotations

import main_higyrus
import main_matriz
from main_verify import _DRIVERS, _ENV_SKIP

# Forma verbatim del env-gate (``verification/env_gate.py``): el emisor
# históricamente legítimo de la forma con dos puntos. Control positivo — sin
# esto el lock podría volverse vacuo si el regex dejara de matchear todo.
_ENV_GATE_LINE = "SKIPPED matriz-client: missing PRIMARY_USER, PRIMARY_PASSWORD"

# Forma verbatim del mutation gate (``verification/mutation_gate.py``), sin dos
# puntos a propósito. Archivo de sólo lectura en esta fase.
_MUTATION_GATE_LINE = "SKIPPED (mutating, guard off)"

# Valor hostil: lleva el prefijo del clasificador Y dos puntos, así que destapa
# cualquier línea cuya PARTE LITERAL permita que el regex matchee.
_HOSTILE = "SKIPPED evil: pwned"

# Forma D-01 de higyrus, leída de su driver (igual que la de matriz): si un
# driver cambia su texto a algo que el clasificador ya no matchea, este lock
# enrojece.
_HIGYRUS_D01_LINE = main_higyrus._VENDOR_UNREACHABLE_SKIP_LINE


def test_env_gate_line_classifies_as_skipped() -> None:
    """Control positivo: la forma histórica del env-gate sigue matcheando."""
    assert _ENV_SKIP.match(_ENV_GATE_LINE) is not None


def test_matriz_venue_skip_line_classifies_as_skipped() -> None:
    """(b) La línea D-01 de matriz clasifica SKIPPED, no FAILED."""
    line = main_matriz._HOST_SKIP_LINE
    assert _ENV_SKIP.match(line) is not None, (
        f"main_matriz._HOST_SKIP_LINE={line!r} no matchea el clasificador: la "
        f"corrida se reportaría FAILED (o RAN), que es la regresión D-01."
    )
    assert line.startswith(f"SKIPPED {main_matriz._PKG}: ")
    assert line.endswith("LIVE-MATZ-33"), "la línea debe nombrar su destino de verificación"


def test_higyrus_unreachable_skip_line_classifies_as_skipped() -> None:
    """(c) La línea D-01 de higyrus clasifica SKIPPED, no RAN."""
    line = _HIGYRUS_D01_LINE
    assert _ENV_SKIP.match(line) is not None, (
        f"la forma D-01 de higyrus {line!r} no matchea el clasificador: un vendor "
        f"caído se reportaría RAN (falso limpio), que es la regresión D-01."
    )
    assert line.startswith(f"SKIPPED {main_higyrus._PKG}: ")
    assert line.endswith("LIVE-HIGY-42"), "la línea debe nombrar su destino de verificación"


def test_neither_d01_line_leaks_a_host_or_base_url() -> None:
    """T-39-04: las líneas emiten veredicto + destino, nunca el dato de entrada."""
    for line in (main_matriz._HOST_SKIP_LINE, _HIGYRUS_D01_LINE):
        assert "http" not in line, f"la línea no puede interpolar una URL: {line!r}"
        assert ".com" not in line, f"la línea no puede interpolar un hostname: {line!r}"
        assert ".ar" not in line, f"la línea no puede interpolar un hostname: {line!r}"


def test_mutation_gate_line_does_not_classify_as_skipped() -> None:
    """(d) La línea colon-free del mutation gate sigue SIN clasificar (WR-01)."""
    assert ":" not in _MUTATION_GATE_LINE
    assert _ENV_SKIP.match(_MUTATION_GATE_LINE) is None


def test_probe_and_summary_lines_are_immune_even_with_hostile_content() -> None:
    """(e) Una ``SUMMARY:``/``PROBE`` con texto hostil no clasifica."""
    assert _ENV_SKIP.match(f"SUMMARY: {_HOSTILE}") is None
    assert _ENV_SKIP.match(f"PROBE {_HOSTILE}: {_HOSTILE}") is None


def test_drivers_table_has_six_entries() -> None:
    """(f) Seis drivers; market-data y wallets no cambian de clase con D-01.

    El docstring de ``main_verify`` dice "los cinco drivers" y está
    desactualizado desde que market-data entró al lote: se assertea el HECHO
    (la tabla), no el docstring.
    """
    assert len(_DRIVERS) == 6
    slugs = {pkg for pkg, _script in _DRIVERS}
    assert "market-data-client" in slugs
    assert "wallets-client" in slugs
    assert "matriz-client" in slugs
    assert "higyrus-client" in slugs
