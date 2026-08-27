"""RED fixture for TYP-01: an attribute typo must be rejected, statically and at runtime.

This file is the executable form of the phase's guarantee. It lives under
``packages/iol-client/tests/`` because that path is what the CI mypy loop
typechecks (``ci.yml``, "mypy (tests por paquete)"); it deliberately does
**not** live in ``main_iol.py``, which mypy never sees (the global ``files``
setting covers ``packages/*/src`` only).

No mypy subprocess is spawned. D-10 rules that out explicitly: it would be new
machinery and ~10s of CI for a guarantee the existing typecheck job already
enforces on this very file.
"""

from __future__ import annotations

import pytest

from iol_client.models import Cotizacion


def test_attribute_typo_is_rejected_statically_and_at_runtime() -> None:
    """Both legs of TYP-01, pinned on one misspelled attribute.

    **Static leg.** mypy flags ``ultimoPrecioo`` as an undefined attribute and
    the ``type: ignore`` on that line absorbs it. The ignore is the *assertion*,
    not a suppression: under ``warn_unused_ignores = true``
    (``pyproject.toml``), the day that attribute starts resolving — because
    someone added it, or because ``Cotizacion`` stopped being a typed model and
    went back to being a dict — mypy reports the ignore as unused and **fails**.
    The fixture therefore cannot rot into a no-op; it is auto-invalidating in
    both directions.

    **Runtime leg.** ``slots=True`` on the dataclass means the same typo raises
    ``AttributeError`` instead of returning ``None``. Without the
    ``pytest.raises`` wrapper this file would simply turn the CI test matrix
    red, since ``packages/iol-client`` is in it and pytest executes the typo
    for real.

    Non-vacuity was verified by hand in both directions before this file was
    committed; the observations are recorded in ``30-01-SUMMARY.md``.
    """
    quote = Cotizacion.from_api({"ultimoPrecio": 1.0})

    with pytest.raises(AttributeError):
        _ = quote.ultimoPrecioo  # type: ignore[attr-defined]

    assert quote.ultimoPrecio == 1.0
