"""CR-01 regression — the SHAPE-diff must not fabricate findings for Null Object LINKS.

Phase 36 turned ``MarketDataSnapshot.market_data`` from an opaque
``dict[str, Any] | None`` into the typed Null Object ``MarketDataEntries``. That
switched RECURSION ON inside :func:`verification.safemodel_diff.diff_safemodel_bidirectional`
for a field where it had never run, and six of the ten roster keys — ``BI`` /
``OF`` (``list[BookLevel]``) and ``CL`` / ``LA`` / ``OI`` / ``SE``
(``EntryValue``) — are NON-optional. Every ``/marketdata`` row whose
``market_data`` object omits an entry type therefore yielded a ``model-only``
tuple, which ``main_market_data._emit_shape`` writes to the append-only ledger as
a ``SHAPE`` / FALSE-PASS-risk finding.

That directly contradicted the policy the same milestone had just adopted:
NOBJ-02 (Phase 35, ``_decode.py``) states that a ``null`` or absent value on a
NON-optional list or nested-model link is a legitimate payload shape that
collapses to ``[]`` / the empty instance and **emits NOTHING**. The decoder and
the differ disagreed about the same fact, and the differ's half was the one that
lands in ``.planning/verification/market-data-client-findings.md`` — the
committed artifact the milestone's divergence census is measured from.

The fix lives in the differ, where the LINK/LEAF distinction lives, and NOT in
the driver's suppression sets: those are key-based and path-agnostic, so
extending them would start suppressing a genuine ``BI`` omission on any other
model.

Every test below has a falsification half: a scalar LEAF absence must still be
reported, otherwise the fix would have traded a false positive for a false pass.
Identifiers are synthesised (C-4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from market_data_client import MarketDataSnapshot
from market_data_client.models import EntryValue, SafeModel
from verification.safemodel_diff import diff_safemodel_bidirectional

# A ``/marketdata`` item carrying ONLY ``LA`` under ``market_data`` — the row the
# review reproduced against. Every snapshot LEAF the wire really sends is
# present, so the only thing left to diff is the entry roster.
_PARTIAL_MARKET_DATA_ROW: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": True,
    "entries": ["LA"],
    "market_data": {"LA": {"date": 20990101, "price": 10, "size": 1}},
    "staleness_seconds": 1.5,
    "note": None,
}


def _model_only(payload: dict[str, Any], model_cls: type) -> list[tuple[str, str, str]]:
    """Only the ``model-only`` tuples — the FALSE-PASS-risk direction."""
    return [t for t in diff_safemodel_bidirectional(payload, model_cls) if t[1] == "model-only"]


# Synthetic two-level pair for the depth falsification below. Declared at MODULE
# level on purpose: ``from __future__ import annotations`` makes every annotation
# a string, and ``get_type_hints`` resolves it against the module globals — a
# function-local dataclass would raise ``NameError`` there.


@dataclass(frozen=True, slots=True)
class _Leafy(SafeModel):
    """A scalar LEAF next to a Null Object LINK, at depth one."""

    required_leaf: str
    link: EntryValue


@dataclass(frozen=True, slots=True)
class _Outer(SafeModel):
    """Envelope whose only field is the nested :class:`_Leafy`."""

    nested: _Leafy


# ---------------------------------------------------------------------------
# Differ level — the six non-optional roster links
# ---------------------------------------------------------------------------


def test_absent_entry_types_are_not_model_only_divergences() -> None:
    """The six non-optional roster LINKS never yield a ``model-only`` tuple.

    Before the fix this row produced five: ``BI``, ``CL``, ``OF``, ``OI``, ``SE``
    at path ``.market_data``.
    """
    nested = [t for t in _model_only(_PARTIAL_MARKET_DATA_ROW, MarketDataSnapshot) if t[0]]

    assert nested == []


def test_a_fully_empty_market_data_object_is_still_silent() -> None:
    """``market_data: {}`` — the shape ``test_market_data_chain._MD_EMPTY`` pins."""
    row = {**_PARTIAL_MARKET_DATA_ROW, "market_data": {}, "entries": []}

    assert [t for t in _model_only(row, MarketDataSnapshot) if t[0]] == []


def test_an_absent_market_data_key_is_not_a_divergence_either() -> None:
    """The LINK itself is a link: omitting ``market_data`` outright is legitimate."""
    row = {k: v for k, v in _PARTIAL_MARKET_DATA_ROW.items() if k != "market_data"}

    assert ("", "model-only", "market_data") not in _model_only(row, MarketDataSnapshot)


# ---------------------------------------------------------------------------
# Falsification — a scalar LEAF is still a false-pass risk
# ---------------------------------------------------------------------------


def test_an_absent_scalar_leaf_is_still_reported() -> None:
    """The half that must NOT be amnestied: ``market_id`` is a ``str`` LEAF.

    ``walk_field`` substitutes a typed zero for it, which the caller cannot tell
    apart from data — that is exactly what ``model-only`` exists to surface.
    """
    row = {k: v for k, v in _PARTIAL_MARKET_DATA_ROW.items() if k != "market_id"}

    assert ("", "model-only", "market_id") in _model_only(row, MarketDataSnapshot)


def test_a_leaf_absent_inside_the_nested_container_is_still_reported() -> None:
    """LEAF/LINK is decided per field, not per depth — the rule survives recursion."""
    tuples = _model_only({"nested": {}}, _Outer)

    assert (".nested", "model-only", "required_leaf") in tuples
    assert (".nested", "model-only", "link") not in tuples


# ---------------------------------------------------------------------------
# Driver level — what actually reaches the committed findings ledger
# ---------------------------------------------------------------------------


@pytest.fixture
def captured_findings(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Intercept ``append_finding`` so no test ever writes the committed ledger."""
    import main_market_data

    captured: list[dict[str, Any]] = []

    def _fake_append_finding(pkg: str, **kwargs: Any) -> None:
        captured.append({"pkg": pkg, **kwargs})

    monkeypatch.setattr(main_market_data, "append_finding", _fake_append_finding)
    return captured


def test_emit_shape_returns_zero_for_a_partial_market_data_row(
    captured_findings: list[dict[str, Any]],
) -> None:
    """CR-01, stated at the site that writes the ledger: zero findings, zero writes."""
    import main_market_data

    emitted = main_market_data._emit_shape(
        _PARTIAL_MARKET_DATA_ROW,
        MarketDataSnapshot,
        "MarketDataSnapshot",
        "sync",
        "https://market-data-develop.test/api",
    )

    assert emitted == 0
    assert captured_findings == []


def test_emit_shape_still_reports_an_absent_scalar_leaf(
    captured_findings: list[dict[str, Any]],
) -> None:
    """Non-vacuity of the guard above: the driver did not simply stop emitting."""
    import main_market_data

    row = {k: v for k, v in _PARTIAL_MARKET_DATA_ROW.items() if k != "market_id"}

    emitted = main_market_data._emit_shape(
        row,
        MarketDataSnapshot,
        "MarketDataSnapshot",
        "sync",
        "https://market-data-develop.test/api",
    )

    assert emitted == 1
    assert "market_id" in captured_findings[0]["title"]
