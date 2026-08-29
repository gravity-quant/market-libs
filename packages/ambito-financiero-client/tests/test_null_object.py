"""Null Object contract for ``ambito_financiero_client`` — NOBJ-01, Phase 35.

ROADMAP Phase 35 criterio 1 asks the six paquetes of this workspace to answer
the truthiness question. This paquete's answer is that it has **no response
model to ask** — its single endpoint returns a scraped Argentine-format decimal
parsed straight into a ``float``, so there is no envelope to model, and a base
class with no subclass would be dead weight on a published wheel (D-05, and the
argument is written out in full in ``src/ambito_financiero_client/models.py``'s
module docstring; this file pins the property, that module explains it).

An emptiness that is merely *not contradicted* is the failure mode this
milestone exists to eliminate. So the zero is asserted as a POSITIVE structural
property of the shipped module — no class definitions, an empty ``__all__``, and
imports limited to the ``__future__`` flag — and never as an empty
``parametrize`` list, which pytest skips in silence, nor as a lower bound that
any roster whatsoever would satisfy.

The second half of the file is the criterio-5 ``@property`` alias invariant
(D-16). It belongs here even though this paquete ships no models, for exactly
the reason ``test_decode.py`` already argues about the walker copy itself:
dormant is not the same as unverified. The module-local fixtures below exist so
the dormant copy is exercised anyway, and the invariant phases 36-38 depend on
is retired in this paquete along with the rest.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import logging
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Self, get_type_hints

import pytest

from ambito_financiero_client import _decode, models
from ambito_financiero_client._decode import POLICY, DecodeScope, walk_model

_MESSAGE = "decode divergence"


@pytest.fixture(autouse=True)
def _pristine_decode_context() -> Iterator[None]:
    """Start every test in this module with an unbound decode mode and scope.

    Copied from ``test_decode.py`` for the same reason it exists there: once any
    test in the session drives a real ``_request``, the sync test context keeps
    that request's ``DECODE_SCOPE`` (and possibly ``STRICT_DECODE``) bound, and
    a later bare decode would either join a stale dedupe set or raise under an
    inherited strict mode — turning assertions in this module green-or-red
    purely on test ORDER.
    """
    mode = _decode.STRICT_DECODE.get()
    scope = _decode.DECODE_SCOPE.get()
    _decode.STRICT_DECODE.set(False)
    _decode.DECODE_SCOPE.set(None)
    try:
        yield
    finally:
        _decode.STRICT_DECODE.set(mode)
        _decode.DECODE_SCOPE.set(scope)


# ---------------------------------------------------------------------------
# Criterio 1 — the empty roster, asserted as a property
# ---------------------------------------------------------------------------


def test_the_package_declares_no_response_models_by_decision() -> None:
    """D-05: the emptiness is a decision, and this is where it is executable.

    Three independent statements of the same property, because any one of them
    alone could be satisfied by an accident:

    1. the shipped module's AST carries zero class definitions;
    2. its ``__all__`` is the empty list, so nothing is published from it;
    3. it imports nothing beyond the mandatory ``__future__`` flag — the walker
       is dormant in this paquete by design and the module does not reach for it.

    The reason, from ``models.py``'s own docstring: the single endpoint here
    returns a scraped Argentine-format decimal parsed straight into a ``float``.
    There is no envelope to model, and a base class with no subclass would be
    dead weight on a published wheel.
    """
    source = pathlib.Path(inspect.getfile(models)).read_text(encoding="utf-8")
    tree = ast.parse(source)

    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert classes == []

    assert models.__all__ == []

    imported = [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]
    assert [n.module for n in imported if isinstance(n, ast.ImportFrom)] == ["__future__"]
    assert [n for n in imported if isinstance(n, ast.Import)] == []


# ---------------------------------------------------------------------------
# Module-local fixtures for the criterio-5 pair (D-16)
#
# Same convention ``test_decode.py`` established for this paquete: a frozen
# slotted dataclass whose ``from_api`` delegates to ``walk_model``. Nothing in
# ``src/`` constructs one; they exist so the dormant walker copy is driven.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Model:
    """Base carrying the ``from_api`` shape a typed surface here would take."""

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Decode ``payload`` into an instance, reporting every divergence."""
        return cls(**walk_model(cls, payload, policy=POLICY))


@dataclass(frozen=True, slots=True)
class _Leaf(_Model):
    """Nested leaf shared by both halves of the alias pair."""

    simbolo: str
    dias: int


@dataclass(frozen=True, slots=True)
class _AliasShaped(_Model):
    """The exact shape phases 36-38 introduce: wire fields + a read-only alias."""

    LA: _Leaf
    BI: list[_Leaf]

    @property
    def last(self) -> _Leaf:
        """Human-facing alias over the wire-named field (D-16)."""
        return self.LA


@dataclass(frozen=True, slots=True)
class _AliasFree(_Model):
    """The identical wire fields, with no property alias — the control."""

    LA: _Leaf
    BI: list[_Leaf]


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Every divergence record captured so far, in emission order."""
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


def _walk(
    cls: type,
    payload: Any,
    caplog: pytest.LogCaptureFixture,
) -> tuple[Any, list[logging.LogRecord]]:
    """Walk ``payload`` into ``cls`` with a fresh scope, returning instance + records."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
        kwargs = walk_model(cls, payload, policy=POLICY, sink=DecodeScope())
    return cls(**kwargs), _divergences(caplog)


def _records(records: list[logging.LogRecord]) -> list[tuple[str, str, str, str]]:
    """Project records onto the four class-independent contract keys.

    The ``model`` key is deliberately excluded: the pair below compares an
    alias-carrying class against its alias-free twin, and those two necessarily
    disagree on their own class name and on nothing else.
    """
    return [
        (r.field_path, r.divergence, r.declared_type, r.observed_type)  # type: ignore[attr-defined]
        for r in records
    ]


# ---------------------------------------------------------------------------
# Criterio 5 — @property aliases are invisible to the walker (D-16)
# ---------------------------------------------------------------------------


def test_property_aliases_are_invisible_to_get_type_hints() -> None:
    """``get_type_hints`` returns the declared fields and nothing else."""
    hints = get_type_hints(_AliasShaped)

    assert set(hints) == {f.name for f in dataclasses.fields(_AliasShaped)}
    assert "last" not in hints


def test_adding_a_property_alias_does_not_change_the_divergence_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The alias cannot fabricate a divergence nor suppress one (criterio 5).

    The invariant asserted is EQUALITY between the alias-carrying class and its
    alias-free twin, never an absolute record count: plan 35-05 changes what the
    walker emits for a non-optional link carrying nothing, and this test must
    survive that change untouched. If it ever reddens, the alias itself became
    visible to the walker — which is the only thing it is here to detect.
    """
    shaped, shaped_records = _walk(_AliasShaped, {}, caplog)
    free, free_records = _walk(_AliasFree, {}, caplog)

    assert _records(shaped_records) == _records(free_records)
    assert shaped.LA == free.LA
    assert shaped.BI == free.BI
    assert shaped.last is shaped.LA
