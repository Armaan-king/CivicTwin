"""The graph, per D1-D4, and the journeys computed over it, per F1.1-F1.4.

Two graphs live here and they do different jobs.

`build_graph()` returns the **population graph**: one `networkx.DiGraph` with typed nodes
and nine typed edges. It is what the audit traverses to find who is harmed through someone
else, and it is the object that makes `CARES_FOR` directedness mean something.

`TransitNetwork` is the **routing graph**: nodes are `(stop, service)` pairs rather than
stops, so a transfer is an explicit edge with a cost and can be counted rather than
guessed. It is rebuilt whenever a policy changes the network, which is the point of
decision **D3**: a person who keeps their old `USES` edge to a removed stop never
experiences the removal, no harm is detected, and the audit silently returns nothing.
Reassignment is not an optimisation, it is the mechanism.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from app.geography import BUS_SPEED_M_PER_MIN, Geography, distance_m
from app.population import Population
from app.scenario import (
    BOARD_PENALTY_MIN,
    DETOUR_FACTOR,
    MOBILITY_WALK_SPEED,
    TRANSFER_PENALTY_MIN,
    WALK_CEILING_MULTIPLIER,
    WALK_SPEED_M_PER_MIN,
)

ORIGIN = ("__origin__", "")
DEST = ("__dest__", "")


def walk_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Straight-line to walkable metres. F1.2.

    The 1.35 detour factor is declared rather than hidden, and it is exactly the kind of
    assumption a resident comment can legitimately attack.
    """
    return distance_m(a, b) * DETOUR_FACTOR


def walk_min(metres: float, mobility: str) -> float:
    return metres / (WALK_SPEED_M_PER_MIN * MOBILITY_WALK_SPEED[mobility])


# ------------------------------------------------------------------ the population graph
def build_graph(geo: Geography, pop: Population) -> nx.DiGraph:
    """Eight node types, nine edge types. D1, D2, D4."""
    g = nx.DiGraph()

    for zone in {p.home_subzone for p in pop.personas}:
        g.add_node(("Subzone", zone), kind="Subzone")
    g.add_node(("Polyclinic", "amk_polyclinic"), kind="Polyclinic")
    g.add_node(("Workplace", "cbd"), kind="Workplace")
    g.add_node(("School", "amk_schools"), kind="School")

    for s in geo.stops.values():
        g.add_node(("Stop", s.stop_id), kind="Stop", removed=s.removed, x=s.x, y=s.y)
    for svc in geo.services.values():
        g.add_node(("Service", svc.service_id), kind="Service", headway_min=svc.headway_min)
        for i, sid in enumerate(svc.stops):
            g.add_edge(("Service", svc.service_id), ("Stop", sid),
                       kind="SERVES", sequence=i, headway_min=svc.headway_min)
        for a, b in zip(svc.stops, svc.stops[1:]):
            if a == b:
                continue
            t = distance_m(geo.stops[a].xy, geo.stops[b].xy) / BUS_SPEED_M_PER_MIN
            g.add_edge(("Stop", a), ("Stop", b), kind="ROUTES_TO",
                       travel_time_min=round(t, 2), service=svc.service_id)
            g.add_edge(("Stop", b), ("Stop", a), kind="ROUTES_TO",
                       travel_time_min=round(t, 2), service=svc.service_id)

    for p in pop.personas:
        g.add_node(("Person", p.persona_id), kind="Person")
        g.add_node(("Household", p.household_id), kind="Household")
        g.add_edge(("Person", p.persona_id), ("Subzone", p.home_subzone), kind="LIVES_IN")
        g.add_edge(("Person", p.persona_id), ("Household", p.household_id), kind="MEMBER_OF")
        # D4: conditional. uniform edges would flatten the population.
        if p.employment_status == "employed":
            g.add_edge(("Person", p.persona_id), ("Workplace", "cbd"),
                       kind="WORKS_AT", arrive_by=p.work_start_time)
        if p.employment_status == "student":
            g.add_edge(("Person", p.persona_id), ("School", "amk_schools"), kind="STUDIES_AT")
        if p.needs_clinic:
            g.add_edge(("Person", p.persona_id), ("Polyclinic", "amk_polyclinic"),
                       kind="NEEDS", trips_per_week=1, essential=True)

    for e in pop.care_edges:
        g.add_edge(("Person", e.carer), ("Person", e.dependent),
                   kind="CARES_FOR", criticality=e.criticality)
    return g


# ------------------------------------------------------------------ the routing graph
@dataclass
class Journey:
    reachable: bool
    walk_m: float = 0.0
    time_min: float = 0.0
    transfers: int = 0
    origin_stop: str | None = None


class TransitNetwork:
    """Routing over `(stop, service)` nodes, so transfers are edges and can be counted.

    Costs to a destination are solved once with a reverse Dijkstra and reused for every
    person, because the network does not depend on who is travelling. What depends on the
    person is only the walk at each end and what they will tolerate, which is F1.6 and
    F1.7 and is applied per person below.
    """

    def __init__(self, geo: Geography, removed: set[str] | None = None,
                 wait_penalty: dict[str, float] | None = None):
        self.geo = geo
        self.removed = removed or set()
        #: extra minutes of waiting at a stop, because fewer runs call there. This is how
        #: an express pattern reaches the stops it does not remove: they keep their name
        #: on the map and lose half their buses.
        self.wait_penalty = wait_penalty or {}
        self.g = nx.DiGraph()
        for svc in geo.services.values():
            live = [s for s in svc.stops if s not in self.removed]
            for a, b in zip(live, live[1:]):
                if a == b:
                    continue
                metres = geo.ride_distances.get(
                    (svc.service_id, a, b), distance_m(geo.stops[a].xy, geo.stops[b].xy))
                t = metres / BUS_SPEED_M_PER_MIN
                self.g.add_edge((a, svc.service_id), (b, svc.service_id),
                                weight=t, transfer=0)
                self.g.add_edge((b, svc.service_id), (a, svc.service_id),
                                weight=t, transfer=0)
        # a transfer is an explicit edge: the walk between berths plus half a headway
        for sid in {s for s, _ in self.g.nodes}:
            here = [n for n in self.g.nodes if n[0] == sid]
            for a in here:
                for b in here:
                    if a == b:
                        continue
                    wait = geo.services[b[1]].headway_min / 2
                    self.g.add_edge(a, b, weight=TRANSFER_PENALTY_MIN + wait, transfer=1)

    def live_stops(self) -> list[str]:
        return [s.stop_id for s in self.geo.stops.values() if s.stop_id not in self.removed]

    def solve(self, dest_stops: list[str]) -> dict[str, dict[tuple[str, str], tuple[float, int]]]:
        """(time, transfers) to each destination stop, from every boarding node.

        Solved per destination rather than collapsed to the nearest one. Collapsing is
        wrong and quietly so: the cheapest stop to ride to may be one this person cannot
        walk away from, and picking it for them hides the alternative that would have
        worked. The clinic is reachable from a trunk stop 760 m away or a feeder stop
        90 m away, and which of those counts depends entirely on who is asking.
        """
        rev = self.g.reverse(copy=False)
        out: dict[str, dict[tuple[str, str], tuple[float, int]]] = {}
        for dest in dest_stops:
            if dest in self.removed:
                continue
            best: dict[tuple[str, str], tuple[float, int]] = {}
            for sink in [n for n in self.g.nodes if n[0] == dest]:
                dist, paths = nx.single_source_dijkstra(rev, sink, weight="weight")
                for node, d in dist.items():
                    path = paths[node]
                    transfers = sum(rev.edges[u, v]["transfer"] for u, v in zip(path, path[1:]))
                    if node not in best or d < best[node][0]:
                        best[node] = (d, transfers)
            if best:
                out[dest] = best
        return out


def journey_for(
    person,
    origin_xy: tuple[float, float],
    dest_xy: tuple[float, float],
    net: TransitNetwork,
    solved: dict[str, dict[tuple[str, str], tuple[float, int]]],
) -> Journey:
    """The best journey this person will actually accept. F1.1-F1.4, F1.6, F1.7.

    Every (boarding stop, service, alighting stop) combination is considered, and one is
    only a candidate if the person can walk both ends of it and tolerate its transfers.
    C3 states a tolerance, not a preference, so an intolerable transfer is excluded rather
    than penalised.
    """
    best = Journey(reachable=False)
    best_time = float("inf")
    budget = person.max_walk_m * WALK_CEILING_MULTIPLIER

    boardable = []
    for sid in net.live_stops():
        w_on = walk_m(origin_xy, net.geo.stops[sid].xy)
        if w_on <= budget:
            boardable.append((sid, w_on))

    for dest, costs in solved.items():
        w_off = walk_m(net.geo.stops[dest].xy, dest_xy)
        if w_off > budget:
            continue
        off_min = walk_min(w_off, person.mobility_level)
        for sid, w_on in boardable:
            if w_on + w_off > budget:
                continue
            for svc in net.geo.serving(sid):
                node = (sid, svc.service_id)
                if node not in costs:
                    continue
                ride, transfers = costs[node]
                if transfers > person.transfer_tolerance:
                    continue
                total = (
                    walk_min(w_on, person.mobility_level)
                    + svc.headway_min / 2
                    + net.wait_penalty.get(sid, 0.0)
                    + BOARD_PENALTY_MIN
                    + ride
                    + off_min
                )
                if total < best_time:
                    best_time = total
                    best = Journey(reachable=True, walk_m=round(w_on + w_off, 1),
                                   time_min=round(total, 2), transfers=transfers,
                                   origin_stop=sid)

    # walking the whole way is still a journey, and for a near neighbour it is the best one
    direct = walk_m(origin_xy, dest_xy)
    if direct <= budget:
        t = walk_min(direct, person.mobility_level)
        if t < best_time:
            best = Journey(reachable=True, walk_m=round(direct, 1),
                           time_min=round(t, 2), transfers=0, origin_stop=None)
    return best
