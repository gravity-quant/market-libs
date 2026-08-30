"""WR-06 regression — the SHAPE-diff can see inside a mapping.

Phase 37 closed three rosters behind a mapping: ``TickPriceRange``
(``InstrumentDetail.tickPriceRanges``), ``InstrumentPositionReport``
(``DetailedPosition.report``, at depth TWO) and ``DetailedAccountReport``
(``AccountReport.detailedAccountReports``). Those fields used to be
``dict[str, Any]`` passthroughs where every vendor key reached the caller; they
are closed dataclasses now, so keys outside the roster are DISCARDED.

The models disclose that loss and argue it is detectable, with *"widening the
roster is the right answer once a live run MEASURES one of those keys"*. The
Phase 37 code review found that remedy unreachable:
``verification/safemodel_diff.py::_nested_safemodel_class`` handled bare models,
``list[Model]`` and ``Optional[...]`` and had **no mapping branch**, so all three
models sat behind a shape the differ could not descend. They were structurally
invisible to ``diff_safemodel_bidirectional``, i.e. to probe 20 of
``main_matriz.py``, i.e. to the only mechanism that would ever measure them. The
docstrings promised a feedback loop that was not wired.

This module is the lock on the loop being wired. It asserts, against the
COMMITTED VENDOR SAMPLE rather than a paraphrase, that the deferred subtrees the
rosters drop are now reported as ``wire-only`` — the direction that says "the
vendor sends this and the model does not declare it".

The falsification half matters as much as the positive: an absent NON-optional
mapping field must still be reported ``model-only``. That is what distinguishes
the mapping branch from the LINK skip Phase 36's CR-01 installed. A mapping is
NOT a Null Object link: matriz's mapping axis emits a ``missing`` divergence for
an absent mapping field, so the differ reporting it AGREES with the decoder,
which is the whole standard the LINK skip was measured against.

Identifiers are synthesised or taken from the committed vendor doc (C-4); no
live capture of either Risk endpoint exists in this repo and none can be
produced while ``LIVE-MATZ-33`` stands.
"""

from __future__ import annotations

from typing import Any

from matriz_client.models import AccountReport, DetailedPosition, InstrumentDetail
from verification.safemodel_diff import diff_safemodel_bidirectional

# ``report[contractType][symbol]`` per documentation/Primary-API.md:1707-1790.
# ``detailedPositions`` (``:1710-1744``) is the subtree D-07 deferred to Phase 39.
_DETAILED_POSITION: dict[str, Any] = {
    "account": "REM7374",
    "totalDailyDiffPlain": -184777,
    "totalMarketValue": 60240,
    "lastCalculation": 1669996294136,
    "report": {
        "FUTURE_OPTION_CALL": {
            "SOJ.ROS/MAY23 380 C": {
                "instrumentInitialSize": -2,
                "instrumentFilledSize": 0,
                "instrumentCurrentSize": -2,
                "detailedPositions": [],
            }
        }
    },
}

# ``detailedAccountReports[key]`` per documentation/Primary-API.md:1817-1895.
# ``currencyBalance`` (``:1828-1868``) and ``availableToOperate`` (``:1869-1888``)
# are the two subtrees D-07 deferred.
_ACCOUNT_DATA: dict[str, Any] = {
    "accountName": "REM7374",
    "detailedAccountReports": {
        "0": {
            "settlementDate": 1669950000000,
            "currencyBalance": {},
            "availableToOperate": {},
        }
    },
}


def _wire_only(payload: dict[str, Any], model_cls: type) -> set[tuple[str, str]]:
    """``(path, key)`` for the ``wire-only`` direction — "vendor sends, model drops"."""
    return {
        (path, key)
        for path, direction, key in diff_safemodel_bidirectional(payload, model_cls)
        if direction == "wire-only"
    }


def _model_only(payload: dict[str, Any], model_cls: type) -> set[tuple[str, str]]:
    """``(path, key)`` for the ``model-only`` direction — the FALSE-PASS-risk one."""
    return {
        (path, key)
        for path, direction, key in diff_safemodel_bidirectional(payload, model_cls)
        if direction == "model-only"
    }


def test_the_differ_descends_two_levels_of_open_keys_into_report() -> None:
    """``DetailedPosition.report`` is ``dict[str, dict[str, Model]]`` — depth TWO.

    Before WR-06 this returned nothing at all below ``.report``: the leaf model
    was two mapping levels down and the differ had no branch for either.
    """
    assert (".report{}{}", "detailedPositions") in _wire_only(_DETAILED_POSITION, DetailedPosition)


def test_the_differ_descends_one_level_into_detailed_account_reports() -> None:
    """``AccountReport.detailedAccountReports`` is ONE level, and both deferred keys show."""
    found = _wire_only(_ACCOUNT_DATA, AccountReport)
    assert (".detailedAccountReports{}", "currencyBalance") in found
    assert (".detailedAccountReports{}", "availableToOperate") in found


def test_the_differ_descends_into_tick_price_ranges() -> None:
    """The third mapping-carried roster, ``InstrumentDetail.tickPriceRanges``."""
    payload = {
        "symbol": "DLR/DIC23",
        "tickPriceRanges": {"0": {"lowerLimit": 1.0, "tick": 0.01, "vendorNew": 7}},
    }
    assert (".tickPriceRanges{}", "vendorNew") in _wire_only(payload, InstrumentDetail)


def test_an_absent_mapping_field_is_still_reported_model_only() -> None:
    """The falsification half: a mapping is NOT a Null Object LINK.

    Phase 36's CR-01 skips direction A for a non-optional nested model or
    ``list[Model]``, because NOBJ-02 makes an absent LINK a legitimate payload
    shape that emits NOTHING — reporting it would contradict the decoder. That
    justification does not transfer to a mapping: matriz's mapping axis emits a
    ``missing`` divergence for an absent mapping field, so reporting it here
    AGREES with the decoder.

    Folding WR-06's mapping branch into ``_nested_safemodel_class`` — the
    one-line shape the review sketched — would have silently suppressed these.
    That is why the mapping arm is a separate predicate.
    """
    without_report = {k: v for k, v in _DETAILED_POSITION.items() if k != "report"}
    assert ("", "report") in _model_only(without_report, DetailedPosition)


def test_an_empty_mapping_yields_nothing_like_an_empty_list() -> None:
    """No element to sample means no finding — the same rule ``list[Model]`` follows."""
    payload = dict(_DETAILED_POSITION, report={})
    below_report = {
        (p, k) for p, k in _wire_only(payload, DetailedPosition) if p.startswith(".rep")
    }
    assert below_report == set()
