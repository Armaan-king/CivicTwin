"""The rules, tested directly.

`test_contract.py` asserts the run is well-formed. It would still pass if the engine
computed nothing and returned plausible constants, which is exactly what the fixture used
to do. These tests assert the rules themselves: that reassignment happens, that seeding is
positional-order-independent, that the dependency edge is what produces second-order harm,
and that removing stops makes things worse for the people near them.
"""
from __future__ import annotations

import pytest

from app.geography import build_geography, distance_m
from app.graph import TransitNetwork, build_graph, journey_for, walk_m
from app.population import build_population
from app.rng import derived_rng
from app.scenario import (
    DETOUR_FACTOR, MAX_WALK_M, SCENARIO_SEED, WALK_CEILING_MULTIPLIER,
)
from app.simulation import simulate

REMOVED = {"55079", "55081"}


@pytest.fixture(scope="module")
def world():
    geo = build_geography()
    return geo, build_population(geo)


# ---------------------------------------------------------------- G2 seeding
def test_seeds_depend_on_the_key_and_not_on_call_order():
    """The whole point of G2. A persona draws the same numbers whenever it is asked."""
    first = [derived_rng(f"p_{i}").random() for i in range(5)]
    second = [derived_rng(f"p_{i}").random() for i in reversed(range(5))][::-1]
    assert first == second


def test_a_different_scenario_seed_gives_a_different_stream():
    assert derived_rng("p_0").random() != derived_rng("p_0", SCENARIO_SEED + 1).random()


def test_the_whole_run_is_reproducible(world):
    geo, pop = world
    a = simulate(geo, pop, REMOVED, 2.4, record_events=False)
    b = simulate(geo, build_population(geo), REMOVED, 2.4, record_events=False)
    assert [o.severity for o in a.outcomes.values()] == [o.severity for o in b.outcomes.values()]


# ---------------------------------------------------------------- F1 journey rules
def test_walkable_distance_applies_the_declared_detour_factor():
    """F1.2. The constant is declared, so it must actually be the one in use."""
    assert walk_m((0, 0), (100, 0)) == pytest.approx(distance_m((0, 0), (100, 0)) * DETOUR_FACTOR)


def test_nobody_is_routed_beyond_their_physical_ceiling(world):
    """People stretch past what they said they would walk. They do not stretch forever."""
    geo, pop = world
    net = TransitNetwork(geo)
    solved = net.solve(geo.clinic_stops)
    for p in pop.personas:
        if not p.needs_clinic:
            continue
        j = journey_for(p, p.xy, geo.polyclinic, net, solved)
        if j.reachable:
            assert j.walk_m <= p.max_walk_m * WALK_CEILING_MULTIPLIER + 1, p.persona_id


def test_severe_mobility_is_never_given_a_transfer(world):
    geo, pop = world
    net = TransitNetwork(geo)
    solved = net.solve(geo.clinic_stops)
    for p in pop.personas:
        if p.mobility_level != "severe" or not p.needs_clinic:
            continue
        j = journey_for(p, p.xy, geo.polyclinic, net, solved)
        assert j.transfers == 0, p.persona_id


def test_max_walk_comes_from_the_declared_mapping(world):
    _, pop = world
    for p in pop.personas:
        assert p.max_walk_m == MAX_WALK_M[p.mobility_level]


# ---------------------------------------------------------------- D3 reassignment
def test_removing_a_stop_forces_a_re_search(world):
    """D3, and the easiest thing in the system to get quietly wrong.

    A person who keeps their `USES` edge to a removed stop never experiences the removal,
    no harm is detected, and the audit silently returns nothing. So: nobody may still be
    boarding at a stop that no longer exists.
    """
    geo, pop = world
    after = TransitNetwork(geo, removed=REMOVED)
    solved = after.solve(geo.clinic_stops)
    for p in pop.personas:
        if not p.needs_clinic:
            continue
        j = journey_for(p, p.xy, geo.polyclinic, after, solved)
        assert j.origin_stop not in REMOVED, p.persona_id


def test_removing_stops_never_improves_a_journey(world):
    """Taking a stop away cannot make a journey faster.

    Stated on time, not on walk, because the router optimises time: losing a stop can
    leave someone with a slightly shorter walk and a longer trip, and that is correct
    behaviour rather than a bug. Time is the invariant a reduced network must respect.
    """
    geo, pop = world
    base, after = TransitNetwork(geo), TransitNetwork(geo, removed=REMOVED)
    sb, sa = base.solve(geo.clinic_stops), after.solve(geo.clinic_stops)
    for p in pop.personas:
        if not p.needs_clinic:
            continue
        b = journey_for(p, p.xy, geo.polyclinic, base, sb)
        a = journey_for(p, p.xy, geo.polyclinic, after, sa)
        if b.reachable and a.reachable:
            assert a.time_min >= b.time_min - 0.01, p.persona_id


# ---------------------------------------------------------------- D2, F3 the cascade
def test_second_order_harm_disappears_without_the_dependency_edges(world):
    """N2, the ablation. The only honest way to claim the graph does work.

    Same seeds, same population, no `CARES_FOR`. If this does not go to zero, the
    second-order finding was coming from somewhere else and the claim is false.
    """
    from dataclasses import replace

    geo, pop = world
    with_edges = simulate(geo, pop, REMOVED, 2.4, record_events=False)
    n_with = sum(1 for o in with_edges.outcomes.values() if o.second_order)
    assert n_with > 0, "the cascade never fired, so the ablation proves nothing"

    without = simulate(geo, replace(pop, care_edges=[]), REMOVED, 2.4, record_events=False)
    assert sum(1 for o in without.outcomes.values() if o.second_order) == 0


def test_harm_travels_to_the_carer_and_never_back(world):
    """D2. An undirected graph would run the cascade both ways and produce nonsense."""
    geo, pop = world
    r = simulate(geo, pop, REMOVED, 2.4)
    absorbed = {e.persona_id for e in r.events if e.kind == "DEPENDENCY_ABSORBED"}
    carers = {e.carer for e in pop.care_edges}
    dependents = {e.dependent for e in pop.care_edges}
    assert absorbed <= carers
    assert not (absorbed & (dependents - carers))


def test_the_population_graph_carries_every_declared_edge_type(world):
    """D1, D2. Conditional edges, so sparsity is expected; absence of a type is not."""
    geo, pop = world
    g = build_graph(geo, pop)
    kinds = {d["kind"] for _, _, d in g.edges(data=True)}
    assert {"LIVES_IN", "MEMBER_OF", "WORKS_AT", "STUDIES_AT",
            "NEEDS", "CARES_FOR", "SERVES", "ROUTES_TO"} <= kinds


# ---------------------------------------------------------------- the policy bites
def test_the_policy_harms_somebody(world):
    """A scenario that hurts nobody proves nothing about a tool for finding who is hurt."""
    geo, pop = world
    r = simulate(geo, pop, REMOVED, 2.4)
    assert sum(1 for o in r.outcomes.values() if o.severity == "high") > 0


def test_doing_nothing_harms_nobody(world):
    """The control. Harm must come from the policy, not from the simulation running."""
    geo, pop = world
    r = simulate(geo, pop, removed=set(), express_saving_min=0.0)
    assert all(o.severity == "none" for o in r.outcomes.values())
    assert r.events == []
