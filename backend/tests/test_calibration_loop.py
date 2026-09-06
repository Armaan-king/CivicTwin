"""Calibration proposes, a human decides, and an approved correction actually corrects.

L3 forbids automatic parameter updates. What it requires instead is that the decision is
recorded, that history is retained either way, and -- the part that makes any of it
meaningful -- that approving a correction changes the model's prediction rather than
merely being noted.
"""
from __future__ import annotations

import pytest

from app import calibration_state as cs
from app.consultation import predicted_support, walk_cost_key
from app.engine import build_run, study_area
from app.population import build_population
from app.schemas.run import SimulationRun
from app.simulation import Outcome


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "STATE", tmp_path / "calibration_state.json")
    yield


def test_nothing_is_in_force_until_a_human_approves():
    assert cs.applied() == {}


def test_an_approved_correction_lowers_the_prediction_on_that_road_only():
    geo, closed, _ = study_area()
    pop = build_population(geo, 400)
    road = "Ang Mo Kio Ave 3"
    here = next(p for p in pop.personas if p.home_subzone == road)
    elsewhere = next(p for p in pop.personas if p.home_subzone != road)
    o = Outcome(persona_id=here.persona_id, walk_distance_m=500)
    o2 = Outcome(persona_id=elsewhere.persona_id, walk_distance_m=500)
    fix = {walk_cost_key(road): 1.56}

    assert predicted_support(here, o, fix) < predicted_support(here, o)
    assert predicted_support(elsewhere, o2, fix) == predicted_support(elsewhere, o2)


def test_approving_the_proposal_reduces_the_error_it_was_derived_from():
    """The loop, end to end. This is the claim the calibration screen makes."""
    before = SimulationRun.model_validate(build_run())
    worst = min(before.consultation.calibration, key=lambda c: c.signed_error)
    proposal = before.consultation.proposed_adjustment

    assert worst.flagged, "the demo scenario must start with a flagged cohort"
    assert proposal.status == "awaiting_human_approval"
    assert proposal.parameter == walk_cost_key(worst.cohort_value)

    cs.record(cs.Decision(parameter=proposal.parameter, value=float(proposal.to),
                          approved=True, prompted_by_error_pp=worst.signed_error,
                          cohort=worst.cohort_value))

    after = SimulationRun.model_validate(build_run())
    same = next(c for c in after.consultation.calibration
                if c.cohort_value == worst.cohort_value)
    assert abs(same.signed_error) < abs(worst.signed_error), "the correction did not correct"
    assert same.n == worst.n, "the same respondents, or it is not a comparison"


def test_the_proposal_is_derived_from_the_error_not_a_constant():
    """A number a person is asked to approve has to come from the evidence.

    It was 1.35 for a while, which looked plausible beside a 14-point gap and was related
    to it only by coincidence.
    """
    run = SimulationRun.model_validate(build_run())
    worst = min(run.consultation.calibration, key=lambda c: c.signed_error)
    proposal = run.consultation.proposed_adjustment
    expected = round(1.0 + abs(worst.signed_error) / 100 * 4, 2)
    assert proposal.to == expected


def test_a_rejection_is_recorded_and_changes_nothing():
    cs.record(cs.Decision(parameter="walk_cost_multiplier[X]", value=1.5, approved=False,
                          prompted_by_error_pp=-12.0, cohort="X"))
    assert cs.applied() == {}
    assert len(cs.history()) == 1
    assert cs.history()[0]["approved"] is False


def test_history_survives_an_approval_being_withdrawn():
    p = "walk_cost_multiplier[X]"
    cs.record(cs.Decision(parameter=p, value=1.5, approved=True,
                          prompted_by_error_pp=-14.0, cohort="X"))
    assert cs.applied() == {p: 1.5}
    cs.record(cs.Decision(parameter=p, value=1.5, approved=False,
                          prompted_by_error_pp=-14.0, cohort="X"))
    assert cs.applied() == {}, "withdrawing must remove it from force"
    assert len(cs.history()) == 2, "but both rulings stay on the record"
