"""The contract any implementation must satisfy.

These tests do not care whether a run came from the fixture or from a real engine. They
call `load_run()` and assert the invariants the product depends on. When W3 to W7 replace
the body of that function, this file is the definition of done: green means the engine
produces something the frontend can render and the docs can defend.

Add to this file when the spec adds an invariant. Do not weaken an assertion to make an
implementation pass.
"""
from __future__ import annotations

import pytest

from app.main import load_run
from app.schemas.run import SimulationRun


@pytest.fixture(scope="module")
def run() -> SimulationRun:
    return load_run()


# ---------------------------------------------------------------- provenance
def test_run_is_labelled_synthetic(run: SimulationRun):
    """AGENTS.md 16. Synthetic data is never passed off as real."""
    assert run.is_synthetic is True
    assert run.study_area


def test_run_is_reproducible_by_declaration(run: SimulationRun):
    """goal.md 34. A run that cannot be identified cannot be reproduced or compared."""
    assert run.seed
    assert run.population_version and run.policy_version and run.scenario_id


# ---------------------------------------------------------------- population
def test_every_persona_has_an_outcome(run: SimulationRun):
    assert {p.persona_id for p in run.personas} == {o.persona_id for o in run.outcomes}


def test_max_walk_matches_the_declared_mobility_mapping(run: SimulationRun):
    """scenario-v1.md C3. The metre mapping is the spec, not a suggestion."""
    expected = {"none": 1200, "mild": 800, "moderate": 500, "severe": 250}
    for p in run.personas:
        assert p.max_walk_m == expected[p.mobility_level], p.persona_id


def test_severe_mobility_tolerates_no_transfers(run: SimulationRun):
    for p in run.personas:
        if p.mobility_level == "severe":
            assert p.transfer_tolerance == 0, p.persona_id


# ---------------------------------------------------------------- the graph
def test_care_edges_are_within_a_household(run: SimulationRun):
    """A carer who lives elsewhere makes the dependency meaningless."""
    by_id = {p.persona_id: p for p in run.personas}
    for e in run.graph.edges:
        if e.kind != "CARES_FOR":
            continue
        assert by_id[e.source].household_id == by_id[e.target].household_id
        assert by_id[e.source].home_subzone == by_id[e.target].home_subzone


def test_care_edges_are_asymmetric(run: SimulationRun):
    """D2. Harm propagates to the carer, never back."""
    pairs = {(e.source, e.target) for e in run.graph.edges if e.kind == "CARES_FOR"}
    for a, b in pairs:
        assert (b, a) not in pairs, f"{a} and {b} care for each other"


def test_every_edge_endpoint_exists(run: SimulationRun):
    ids = {p.persona_id for p in run.personas}
    for e in run.graph.edges:
        assert e.source in ids and e.target in ids


# ---------------------------------------------------------------- the events
def test_every_cause_id_resolves(run: SimulationRun):
    """H2. An unresolvable cause makes a root-cause trace unprovable."""
    ids = {e.event_id for e in run.events}
    for e in run.events:
        assert e.cause is None or e.cause in ids, e.event_id


def test_causes_point_backwards_in_round_order(run: SimulationRun):
    by_id = {e.event_id: e for e in run.events}
    for e in run.events:
        if e.cause:
            assert by_id[e.cause].round <= e.round, e.event_id


def test_every_second_order_chain_is_deep_and_crosses_a_person(run: SimulationRun):
    """The finding the product exists to surface. B1 depth, F3 clause 4, D2 direction.

    Checks every chain rather than one arbitrary leaf. The previous version read
    `leaves[0]`, so it passed or failed on event ordering: two of this run's three chains
    satisfied it and the first one did not.

    What every chain must contain is `DEPENDENCY_ABSORBED`, and it must cross from one
    person to another at that link. That crossing *is* the claim. The route into it is
    not: a dependant who loses the trip outright arrives through `ESSENTIAL_ACCESS_LOST`
    rather than `THRESHOLD_EXCEEDED`, and that is the same finding by a shorter road
    (**B1**).
    """
    by_id = {e.event_id: e for e in run.events}
    leaves = [e for e in run.events if e.kind == "OBLIGATION_MISSED"]
    assert leaves, "no carer ever missed their shift; the cascade did not fire"

    for leaf in leaves:
        chain, cursor, seen = [], leaf, set()
        while cursor and cursor.event_id not in seen:
            seen.add(cursor.event_id)
            chain.append(cursor)
            cursor = by_id.get(cursor.cause) if cursor.cause else None

        assert len(chain) >= 3, f"{leaf.event_id}: chain only {len(chain)} deep"

        kinds = [e.kind for e in chain]
        assert "DEPENDENCY_ABSORBED" in kinds, f"{leaf.event_id}: nobody absorbed anything"

        # the crossing: the absorbed event belongs to the carer, its cause to somebody else
        absorbed = next(e for e in chain if e.kind == "DEPENDENCY_ABSORBED")
        assert absorbed.cause, f"{leaf.event_id}: absorption came from nowhere"
        upstream = by_id[absorbed.cause]
        assert upstream.persona_id != absorbed.persona_id, (
            f"{leaf.event_id}: harm never crossed between two people, so it is not "
            f"second-order at all"
        )
        assert leaf.persona_id == absorbed.persona_id, (
            f"{leaf.event_id}: the person who missed their obligation is not the one who "
            f"absorbed the trip"
        )


def test_the_canonical_chain_occurs_somewhere(run: SimulationRun):
    """B1's named chain: a threshold breached, absorbed, and paid for.

    Not required of every chain, but it must happen. If no dependant anywhere breached a
    walking threshold before someone absorbed their trip, the threshold model is doing no
    work and the metre mapping in C3 is decoration.
    """
    by_id = {e.event_id: e for e in run.events}
    for leaf in (e for e in run.events if e.kind == "OBLIGATION_MISSED"):
        kinds, cursor, seen = set(), leaf, set()
        while cursor and cursor.event_id not in seen:
            seen.add(cursor.event_id)
            kinds.add(cursor.kind)
            cursor = by_id.get(cursor.cause) if cursor.cause else None
        if {"THRESHOLD_EXCEEDED", "DEPENDENCY_ABSORBED"} <= kinds:
            return
    raise AssertionError(
        "no chain runs THRESHOLD_EXCEEDED -> DEPENDENCY_ABSORBED -> OBLIGATION_MISSED"
    )


def test_second_order_victims_were_not_harmed_directly(run: SimulationRun):
    """The whole claim: harmed through someone else, not by their own walk."""
    by_persona = {p.persona_id: p for p in run.personas}
    victims = [o for o in run.outcomes if o.second_order]
    assert victims, "no second-order victims, so the graph proved nothing"
    for o in victims:
        assert by_persona[o.persona_id].mobility_level == "none"
        assert by_persona[o.persona_id].is_caregiver


# ---------------------------------------------------------------- patterns
def test_the_run_names_its_environment(run: SimulationRun):
    """The seam is only honest if a reader never has to assume which one ran."""
    from app.environments import registered
    assert run.environment in registered()


def test_all_four_harm_patterns_ship_with_the_run(run: SimulationRun):
    """The breadth claim, in the payload rather than the pitch.

    A number about bus stops travels only if the shape underneath it is named. These
    descriptions are what the UI renders, so a run that omits them makes every finding
    domain-locked.
    """
    from app.schemas.core import PATTERNS
    assert set(run.harm_patterns) == set(PATTERNS)
    for key, p in run.harm_patterns.items():
        assert p.pattern == key
        assert p.also_seen_in, f"{key} names no other policy area"


# ---------------------------------------------------------------- metrics
def test_every_reported_cohort_carries_its_n(run: SimulationRun):
    """evaluation.md 12. A rate without a denominator is not a finding."""
    sub = run.metrics.subgroup
    for axis in (sub.age_band, sub.mobility_level, sub.home_subzone, sub.is_caregiver):
        for m in axis.values():
            assert m.n > 0


def test_severe_counts_agree_between_outcomes_and_metrics(run: SimulationRun):
    counted = sum(1 for o in run.outcomes if o.severity == "high")
    assert run.metrics.overall.severe_harm_count == counted


def test_carers_are_worse_off_than_non_carers(run: SimulationRun):
    """If this fails the dependency model is doing nothing and N2 has no result."""
    c = run.metrics.subgroup.is_caregiver
    assert c["True"].severe_harm_rate > c["False"].severe_harm_rate


# ---------------------------------------------------------------- interventions
def test_rejected_interventions_are_never_scored(run: SimulationRun):
    """Scoring something that was never simulated would be inventing a result."""
    for i in run.interventions:
        if not i.valid:
            assert i.metrics is None
            assert i.validation_errors, f"{i.intervention_id} rejected without a reason"


def test_valid_interventions_are_all_simulated(run: SimulationRun):
    valid = [i for i in run.interventions if i.valid]
    assert len(valid) >= 2
    assert all(i.metrics is not None for i in valid)


def test_intervention_kinds_stay_inside_the_action_space(run: SimulationRun):
    """J1. The planner selects and parameterises; it never invents a type."""
    allowed = {"retain_stop_peak", "add_shuttle_feeder", "reroute_feeder",
               "targeted_support", "phase_rollout"}
    assert {i.kind for i in run.interventions} <= allowed


# ---------------------------------------------------------------- calibration
def test_nothing_is_flagged_on_a_thin_cohort(run: SimulationRun):
    """L2. Both conditions, always: a big error AND enough responses."""
    for r in run.consultation.calibration:
        if r.flagged:
            assert r.n >= 30, f"{r.cohort_value} flagged on n={r.n}"
            assert abs(r.signed_error) > 10


def test_every_response_links_to_a_real_persona(run: SimulationRun):
    ids = {p.persona_id for p in run.personas}
    for r in run.consultation.responses:
        assert r.persona_id in ids


def test_seeded_responses_are_labelled(run: SimulationRun):
    assert all(r.is_seeded for r in run.consultation.responses)


def test_representativeness_is_disclaimed(run: SimulationRun):
    assert run.consultation.is_representative is False


def test_public_confidence_ships_with_its_components(run: SimulationRun):
    """K4. The score is never returned bare."""
    pcs = run.consultation.pcs
    assert set(pcs.components) >= {
        "support", "perceived_fairness", "clarity_of_explanation", "confidence_in_delivery"}


def test_calibration_is_never_auto_applied(run: SimulationRun):
    """L3. A human decides, always."""
    assert run.consultation.proposed_adjustment.status == "awaiting_human_approval"
