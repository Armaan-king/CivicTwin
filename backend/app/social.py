"""Who hears whom. The layer that makes residents a population rather than a spreadsheet.

CivicTwin's dependency graph carries *harm*: directed `CARES_FOR` edges, along which a
closure lands on somebody the policy never touched. This is the other graph, and it carries
*opinion*: undirected, built on the things that actually put two people in earshot of each
other in an estate.

Adapted from PropSim's `social_graph.py`, which is the best idea in that project. Their
edges are demographic homophily plus an engagement-driven degree, with bridges added so the
graph stays connected. Ours adds the two ties an estate really runs on — the same household
and the same road — because a bus stop closing is discussed at the lift lobby before it is
discussed anywhere else.

Why it matters: without it every resident reasons alone, reaches their own conclusion, and
the run produces two thousand parallel monologues. Opinion is social. A resident whose
neighbour lost the hospital trip should move even if their own journey did not change, and
that movement is the difference between a survey and a deliberation.
"""
from __future__ import annotations

import networkx as nx

from app.population import Population
from app.rng import derived_rng

#: How many people one resident actually hears from. Low, deliberately: a person does not
#: have forty political conversations about a bus stop. PropSim scales degree by political
#: engagement; ours uses the same idea with the trust scalar we already sample.
BASE_DEGREE = 3
MAX_DEGREE = 8

#: Ties, strongest first. The order matters: household before road before demographic
#: similarity, because that is the order in which people actually influence each other.
HOUSEHOLD_WEIGHT = 1.0
ROAD_WEIGHT = 0.6
SIMILAR_WEIGHT = 0.35


def build_social_graph(pop: Population) -> nx.Graph:
    """Undirected. Opinion travels both ways, unlike harm."""
    g = nx.Graph()
    by_household: dict[str, list[str]] = {}
    by_road: dict[str, list[str]] = {}
    for p in pop.personas:
        g.add_node(p.persona_id)
        by_household.setdefault(p.household_id, []).append(p.persona_id)
        by_road.setdefault(p.home_subzone, []).append(p.persona_id)

    # everyone in a household hears everyone else in it
    for members in by_household.values():
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                g.add_edge(a, b, weight=HOUSEHOLD_WEIGHT, tie="household")

    # a carer and the person they care for talk, whatever else is true
    for e in pop.care_edges:
        g.add_edge(e.carer, e.dependent, weight=HOUSEHOLD_WEIGHT, tie="care")

    index = {p.persona_id: p for p in pop.personas}
    for p in pop.personas:
        rng = derived_rng(f"{p.persona_id}:social")
        want = BASE_DEGREE + int((MAX_DEGREE - BASE_DEGREE) * p.baseline_trust)
        if g.degree(p.persona_id) >= want:
            continue

        # neighbours on the same road, preferring people at a similar stage of life,
        # which is how acquaintance actually forms in a housing estate
        pool = [q for q in by_road.get(p.home_subzone, []) if q != p.persona_id]
        rng.shuffle(pool)
        pool.sort(key=lambda q: _similarity(index[q], p), reverse=True)

        for q in pool:
            if g.degree(p.persona_id) >= want:
                break
            if g.has_edge(p.persona_id, q) or g.degree(q) >= MAX_DEGREE:
                continue
            same_band = index[q].age_band == p.age_band
            g.add_edge(p.persona_id, q,
                       weight=ROAD_WEIGHT if same_band else SIMILAR_WEIGHT,
                       tie="road")

    return g


def _similarity(a, b) -> float:
    """Crude and deliberate: shared life stage, work status, and dependence on the trip."""
    score = 0.0
    if a.age_band == b.age_band:
        score += 1.0
    if a.employment_status == b.employment_status:
        score += 0.5
    if a.needs_clinic == b.needs_clinic:
        score += 0.5
    if a.is_caregiver and b.is_caregiver:
        score += 0.75
    return score


def neighbours(g: nx.Graph, persona_id: str, limit: int = 5) -> list[str]:
    """The people whose view this resident is exposed to, strongest ties first."""
    if persona_id not in g:
        return []
    ranked = sorted(g[persona_id].items(), key=lambda kv: -kv[1].get("weight", 0))
    return [n for n, _ in ranked[:limit]]


def stats(g: nx.Graph) -> dict:
    degrees = [d for _, d in g.degree()]
    components = list(nx.connected_components(g))
    return {
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
        "mean_degree": round(sum(degrees) / max(len(degrees), 1), 2),
        "isolated": sum(1 for d in degrees if d == 0),
        "components": len(components),
        "largest_component": max((len(c) for c in components), default=0),
    }
