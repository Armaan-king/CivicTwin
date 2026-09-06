"""One documented scale, because L2 reports percentage points and the inputs disagree."""
from __future__ import annotations

import pytest

from app.aggregate import support_comparison
from app.engine import study_area
from app.population import build_population
from app.simulation import Outcome
from app.support_scale import fraction_to_likert, likert_to_fraction, signed_error_pp


@pytest.mark.parametrize("likert,fraction", [(1, 0.0), (2, 0.25), (3, 0.5), (4, 0.75), (5, 1.0)])
def test_the_likert_endpoints_are_anchored(likert, fraction):
    """Neutral must land on 0.5.

    Dividing by 5 rather than mapping the endpoints would put a Likert 3 at 0.6 and bias
    every signed error toward apparent opposition.
    """
    assert likert_to_fraction(likert) == fraction


def test_the_conversion_is_reversible():
    for likert in (1, 2, 3, 4, 5):
        assert fraction_to_likert(likert_to_fraction(likert)) == float(likert)


def test_values_outside_the_scale_are_clamped_not_extrapolated():
    assert likert_to_fraction(0.2) == 0.0
    assert likert_to_fraction(9.0) == 1.0


def test_signed_error_keeps_its_direction():
    """Overestimating support is a different finding from underestimating it."""
    assert signed_error_pp(0.70, 0.50) == 20.0
    assert signed_error_pp(0.50, 0.70) == -20.0


def test_comparison_marks_cohorts_below_the_floor_as_insufficient():
    """A gap driven by a cell of six is noise dressed as a finding (L2, I3)."""
    geo, closed, _ = study_area()
    pop = build_population(geo, 200)
    declared = {p.persona_id: 0.3 for p in pop.personas}
    outcomes = {p.persona_id: Outcome(persona_id=p.persona_id) for p in pop.personas}
    rows = support_comparison(pop, declared, outcomes, axis="age_band")
    assert rows, "no cohorts compared"
    for row in rows:
        assert row["sufficient"] == (row["n"] >= 30)
        assert row["n"] > 0
    assert sum(r["n"] for r in rows) == len(pop.personas)


def test_both_predictions_are_produced_so_they_can_disagree():
    """P3's whole point: keep the logistic *and* the reasoning, and report the gap."""
    geo, closed, _ = study_area()
    pop = build_population(geo, 120)
    # residents flatly opposed; the frozen logistic knows nothing about why
    declared = {p.persona_id: 0.0 for p in pop.personas}
    outcomes = {p.persona_id: Outcome(persona_id=p.persona_id) for p in pop.personas}
    rows = support_comparison(pop, declared, outcomes)
    assert all(r["declared_support"] == 0.0 for r in rows)
    assert all(r["frozen_support"] > 0.0 for r in rows), "the logistic must still speak"
    assert all(r["divergence_pp"] > 0 for r in rows), "and the disagreement must be visible"
