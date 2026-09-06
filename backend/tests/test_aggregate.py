"""Outcomes are built from what residents declared, and only for residents who spoke."""
from __future__ import annotations

from app.aggregate import aggregate, declared_support_by_cohort
from app.deliberate import DeliberationRun
from app.engine import study_area
from app.population import build_population
from app.schemas.deliberation import AgentTurn, AgentVoice
from app.simulation import Outcome


def voice(pid, severity="none", response="unaffected", position=0.5, absorbing_for=None):
    return AgentVoice(persona_id=pid, name="Tan Wei Ming", summary="", turns=[
        AgentTurn(round=1, severity=severity, response=response, position=position,
                  confidence=0.7, reasoning="Because of the closure.",
                  grounded_in=[f"{pid}:f4"], absorbing_for=absorbing_for)])


def run_with(voices, population=2000, cohort=None):
    run = DeliberationRun(model="test")
    run.population = population
    run.voices = {v.persona_id: v for v in voices}
    run.cohort = cohort or [v.persona_id for v in voices]
    run.cohort_strata = {"affected": len(run.cohort), "tied": 0, "comparison": 0}
    return run


def small_pop():
    geo, closed, _ = study_area()
    return build_population(geo, 60)


def test_severity_comes_from_the_resident_not_from_a_rule():
    pop = small_pop()
    pid = pop.personas[0].persona_id
    agg = aggregate(run_with([voice(pid, severity="high", response="giving_up")]), pop)
    assert agg.outcomes[pid].severity == "high"
    assert agg.outcomes[pid].adaptation == "abandon_trip"


def test_a_resident_who_was_never_asked_has_no_outcome():
    """Absent from the denominator, never counted as unharmed.

    This is the rule the whole coverage story rests on: unevaluated is unknown.
    """
    pop = small_pop()
    spoke, silent = pop.personas[0].persona_id, pop.personas[1].persona_id
    agg = aggregate(run_with([voice(spoke)], population=len(pop.personas)), pop)
    assert spoke in agg.outcomes
    assert silent not in agg.outcomes
    assert agg.coverage["evaluated"] == 1
    assert agg.coverage["unevaluated"] == len(pop.personas) - 1


def test_a_resident_whose_turns_were_all_rejected_has_no_outcome():
    pop = small_pop()
    pid = pop.personas[0].persona_id
    empty = AgentVoice(persona_id=pid, name="X", summary="", turns=[])
    agg = aggregate(run_with([empty]), pop)
    assert agg.outcomes == {}


def test_an_essential_trip_is_lost_only_when_the_resident_says_so():
    pop = small_pop()
    needer = next(p for p in pop.personas if p.needs_clinic)
    pid = needer.persona_id

    gave_up = aggregate(run_with([voice(pid, severity="high", response="giving_up")]), pop)
    assert gave_up.outcomes[pid].essential_trips_completed == 0
    assert gave_up.outcomes[pid].accessibility_status == "lost"

    coping = aggregate(run_with([voice(pid, severity="moderate", response="adapting")]), pop)
    assert coping.outcomes[pid].essential_trips_completed == 1
    assert coping.outcomes[pid].accessibility_status == "ok"


def test_computed_geometry_survives_the_join():
    """Distances stay computed. The resident judges what they mean, not how far they are."""
    pop = small_pop()
    pid = pop.personas[0].persona_id
    geom = {pid: Outcome(persona_id=pid, walk_distance_m=493, baseline_walk_m=218,
                         journey_time_delta_min=4.5)}
    agg = aggregate(run_with([voice(pid, severity="moderate")]), pop, geometry=geom)
    o = agg.outcomes[pid]
    assert (o.walk_distance_m, o.baseline_walk_m, o.journey_time_delta_min) == (493, 218, 4.5)
    assert o.severity == "moderate", "geometry must not overwrite the declaration"


def test_absorbing_is_recorded_as_a_second_order_outcome():
    pop = small_pop()
    a, b = pop.personas[0].persona_id, pop.personas[1].persona_id
    agg = aggregate(run_with([voice(a, severity="high", response="absorbing",
                                    absorbing_for=b)]), pop)
    assert agg.outcomes[a].second_order is True
    assert agg.absorbing[a] == b


def test_declared_support_carries_its_denominator():
    pop = small_pop()
    voices = [voice(p.persona_id, position=0.2) for p in pop.personas[:5]]
    agg = aggregate(run_with(voices), pop)
    by_age = declared_support_by_cohort(pop, agg.declared_support, "age_band")
    assert by_age, "no cohorts returned"
    for cell in by_age.values():
        assert cell["n"] >= 1
        assert 0.0 <= cell["mean_support"] <= 1.0
    assert sum(c["n"] for c in by_age.values()) == 5


def test_metrics_read_the_declared_outcomes_unchanged():
    """`metrics.py` is untouched by the pivot: only the provenance of two fields changed."""
    from app.metrics import metrics_for

    pop = small_pop()
    needers = [p for p in pop.personas if p.needs_clinic][:4]
    voices = [voice(p.persona_id, severity="high", response="giving_up") for p in needers]
    agg = aggregate(run_with(voices), pop)
    m = metrics_for(list(agg.outcomes.values()))
    assert m["n"] == 4
    assert m["severe_harm_count"] == 4
    assert m["essential_trip_completion"] == 0.0
