"""The round loop: F1 rules, F3 severity, G1 adaptation, and the cause chain.

Four rounds, per **B1**. Each round only reads state the previous round wrote, and every
event carries the `event_id` of the one that caused it. That chain is not decoration: it is
what makes a root cause provable, what the audit renders as a readable path, and what
`evaluation.md` §9's Grounded Explanation Rate is computed from. An event with an
unresolvable cause is a defect, not a rounding error.

```text
round 0   baseline journeys, no events
round 1   the network changed under them   PATH_UNAVAILABLE, EFFORT_INCREASED,
                                           FRICTION_ADDED, DURATION_INCREASED,
                                           THRESHOLD_EXCEEDED
round 2   what that costs them             ESSENTIAL_ACCESS_LOST, SERVICE_ABANDONED
round 3   who else pays                    DEPENDENCY_ABSORBED, OBLIGATION_MISSED
```

Round 3 is the whole product. A person with no mobility limitation, living nowhere near a
removed stop, is classified as severely harmed because of who they care for. **N2**
measures exactly this by running the same policy with the dependency edges cut.

No LLM is called anywhere in this module (`AGENTS.md` §10). One stochastic component only,
in `adapt()`, per **G1**.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.geography import Geography
from app.graph import Journey, TransitNetwork, journey_for
from app.population import Persona, Population
from app.rng import derived_rng
from app.scenario import (
    BETA,
    MODERATE_JOURNEY_DELTA,
    P_SWITCH_GIVEN_CAR,
    P_SWITCH_GIVEN_NO_CAR,
    SEVERE_WALK_MULTIPLIER,
)

#: the gateway out of the estate. work trips are journeys to here, not to the CBD, because
#: what a local stop removal changes is how you reach the interchange.
WORK_GATEWAY = "55007"


@dataclass
class Event:
    event_id: str
    round: int
    persona_id: str
    kind: str
    before: dict
    after: dict
    cause: str | None = None


@dataclass
class Outcome:
    persona_id: str
    severity: str = "none"
    walk_distance_m: int = 0
    journey_time_min: float = 0.0
    #: after minus baseline, in minutes. negative is an improvement. this is the number
    #: the policy is sold on, and the reason an average can improve while people fall off
    #: a cliff underneath it.
    journey_time_delta_min: float = 0.0
    essential_trips_completed: int = 0
    essential_trips_total: int = 0
    accessibility_status: str = "ok"
    second_order: bool = False
    newly_exposed: bool = False
    adaptation: str = "continue_transit"


@dataclass
class SimResult:
    outcomes: dict[str, Outcome]
    events: list[Event]
    baseline: dict[str, dict[str, Journey]] = field(default_factory=dict)
    after: dict[str, dict[str, Journey]] = field(default_factory=dict)


def adapt(person: Persona, base: Journey, now: Journey, key: str) -> str:
    """The one stochastic component in the deterministic layer. G1.

    Everything else in this module is a pure function of graph state. Keeping randomness
    to a single logistic is what lets you point at one function and say this and only this
    is where chance enters, which is what makes seeded reproducibility testable rather
    than hoped for.
    """
    if not now.reachable:
        return "abandon_trip"
    d_time = (now.time_min - base.time_min) / max(base.time_min, 1.0)
    z = (
        BETA["intercept"]
        + BETA["journey_delta"] * max(0.0, d_time)
        + BETA["transfers"] * max(0, now.transfers - base.transfers)
        + BETA["walk_ratio"] * (now.walk_m / max(person.max_walk_m, 1))
        - BETA["tolerance"] * person.inconvenience_tolerance
        - BETA["car_access"] * (1.0 if person.has_car_access else 0.0)
    )
    p_adapt = 1 / (1 + math.exp(-z))
    rng = derived_rng(f"{person.persona_id}:adapt:{key}")
    if rng.random() >= p_adapt:
        return "continue_transit"
    p_switch = P_SWITCH_GIVEN_CAR if person.has_car_access else P_SWITCH_GIVEN_NO_CAR
    return "switch_to_car" if rng.random() < p_switch else "abandon_trip"


def _destinations(geo: Geography, p: Persona) -> dict[str, tuple[tuple[float, float], list[str], bool]]:
    """(destination xy, stops that serve it, is_essential) per trip this person makes."""
    trips: dict[str, tuple[tuple[float, float], list[str], bool]] = {}
    if p.needs_clinic:
        trips["clinic"] = (geo.polyclinic, geo.clinic_stops, True)
    if p.employment_status == "employed":
        trips["work"] = (geo.stops[WORK_GATEWAY].xy, [WORK_GATEWAY], False)
    return trips


def _journeys(geo: Geography, pop: Population, net: TransitNetwork) -> dict[str, dict[str, Journey]]:
    solved_cache: dict[tuple[str, ...], dict] = {}
    out: dict[str, dict[str, Journey]] = {}
    for p in pop.personas:
        out[p.persona_id] = {}
        for name, (dest_xy, dest_stops, _) in _destinations(geo, p).items():
            key = tuple(dest_stops)
            if key not in solved_cache:
                solved_cache[key] = net.solve(list(dest_stops))
            out[p.persona_id][name] = journey_for(p, p.xy, dest_xy, net, solved_cache[key])
    return out


def simulate(
    geo: Geography,
    pop: Population,
    removed: set[str],
    express_saving_min: float = 0.0,
    record_events: bool = True,
) -> SimResult:
    """Run one policy variant to completion.

    `removed` is the set of stop ids the policy takes out. `express_saving_min` is what
    the remaining riders gain from the faster run, which is the trade the policy is
    actually making and the reason the mean journey time can improve while individuals
    fall off a cliff.
    """
    base_net = TransitNetwork(geo)
    after_net = TransitNetwork(geo, removed=removed)
    base = _journeys(geo, pop, base_net)
    now = _journeys(geo, pop, after_net)

    by_id = pop.by_id()
    outcomes = {p.persona_id: Outcome(persona_id=p.persona_id) for p in pop.personas}
    events: list[Event] = []
    counter = [0]

    def emit(round_: int, pid: str, kind: str, before: dict, after: dict,
             cause: str | None = None) -> str:
        counter[0] += 1
        eid = f"e_{counter[0]:05d}"
        if record_events:
            events.append(Event(eid, round_, pid, kind, before, after, cause))
        return eid

    # ---------------------------------------------------------------- round 1 and 2
    #: per person, the event id that best explains their state, for round 3 to point at
    anchor: dict[str, str] = {}
    #: dependents who can no longer make the clinic trip unaided. Losing access outright
    #: is the obvious case; a walk past what this person said they can manage is the
    #: commoner one, and it is exactly when a household member starts driving them.
    needs_help: set[str] = set()

    for p in pop.personas:
        trips = _destinations(geo, p)
        o = outcomes[p.persona_id]
        o.essential_trips_total = sum(1 for _, _, ess in trips.values() if ess)
        o.essential_trips_completed = o.essential_trips_total

        worst_walk, worst_time, cause_id = 0.0, 0.0, None
        deltas: list[float] = []
        for name, (_, _, essential) in trips.items():
            b, n = base[p.persona_id][name], now[p.persona_id][name]
            if not b.reachable:
                continue

            # round 1 -- the network changed under them
            if b.origin_stop in removed:
                cause_id = emit(1, p.persona_id, "PATH_UNAVAILABLE",
                                {"stop_id": b.origin_stop, "trip": name},
                                {"stop_id": n.origin_stop, "trip": name})
            if not n.reachable:
                eid = emit(2, p.persona_id, "ESSENTIAL_ACCESS_LOST" if essential
                           else "SERVICE_ABANDONED",
                           {"reachable": True, "trip": name},
                           {"reachable": False, "trip": name}, cause_id)
                o.accessibility_status = "unreachable" if essential else o.accessibility_status
                if essential:
                    o.essential_trips_completed -= 1
                    needs_help.add(p.persona_id)
                anchor[p.persona_id] = eid
                worst_walk = max(worst_walk, float(p.max_walk_m) * 2)
                continue

            if n.walk_m > b.walk_m + 1:
                cause_id = emit(1, p.persona_id, "EFFORT_INCREASED",
                                {"walk_distance_m": round(b.walk_m)},
                                {"walk_distance_m": round(n.walk_m)}, cause_id)
            if n.transfers > b.transfers:
                cause_id = emit(1, p.persona_id, "FRICTION_ADDED",
                                {"transfers": b.transfers}, {"transfers": n.transfers}, cause_id)
            ride_time = max(0.0, n.time_min - express_saving_min)
            if ride_time > b.time_min + 0.5:
                cause_id = emit(1, p.persona_id, "DURATION_INCREASED",
                                {"journey_time_min": round(b.time_min, 1)},
                                {"journey_time_min": round(ride_time, 1)}, cause_id)
            if n.walk_m > p.max_walk_m:
                cause_id = emit(1, p.persona_id, "THRESHOLD_EXCEEDED",
                                {"walk_distance_m": round(b.walk_m),
                                 "max_walk_m": p.max_walk_m},
                                {"walk_distance_m": round(n.walk_m),
                                 "max_walk_m": p.max_walk_m}, cause_id)
                anchor[p.persona_id] = cause_id
                if essential:
                    needs_help.add(p.persona_id)

            # round 2 -- what that costs them. G1 decides, once, per trip.
            choice = adapt(p, b, n, name)
            if choice == "abandon_trip":
                o.adaptation = "abandon_trip"
                eid = emit(2, p.persona_id, "ESSENTIAL_ACCESS_LOST" if essential
                           else "SERVICE_ABANDONED",
                           {"trip": name, "completed": True},
                           {"trip": name, "completed": False}, cause_id)
                anchor[p.persona_id] = eid
                if essential:
                    o.essential_trips_completed -= 1
                    o.accessibility_status = "unreachable"
                    needs_help.add(p.persona_id)
            elif choice == "switch_to_car" and o.adaptation == "continue_transit":
                o.adaptation = "switch_to_car"

            worst_walk = max(worst_walk, n.walk_m)
            worst_time = max(worst_time, ride_time)
            deltas.append(ride_time - b.time_min)
            if n.walk_m > b.walk_m and o.accessibility_status == "ok" and n.walk_m > p.max_walk_m:
                o.accessibility_status = "degraded"

        o.walk_distance_m = round(worst_walk)
        o.journey_time_min = round(worst_time, 2)
        o.journey_time_delta_min = round(sum(deltas) / len(deltas), 3) if deltas else 0.0

    # ---------------------------------------------------------------- round 3
    # the dependency cascade. harm travels along CARES_FOR, and only in that direction.
    for edge in pop.care_edges:
        if edge.dependent not in needs_help:
            continue
        carer = by_id[edge.carer]
        o = outcomes[edge.carer]
        cause = anchor.get(edge.dependent)
        absorbed = emit(3, edge.carer, "DEPENDENCY_ABSORBED",
                        {"absorbing_for": None},
                        {"absorbing_for": edge.dependent, "criticality": edge.criticality},
                        cause)
        o.second_order = True

        # the trip they absorb has to come out of their own day
        work = now[edge.carer].get("work")
        detour = now[edge.dependent].get("clinic")
        cost = (detour.time_min if detour and detour.reachable else 25.0) + 12.0
        if carer.work_start_time and work and work.reachable:
            emit(3, edge.carer, "OBLIGATION_MISSED",
                 {"arrives_by": carer.work_start_time, "slack_min": 0},
                 {"arrives_by": carer.work_start_time,
                  "late_by_min": round(cost, 1), "reason": "absorbed a clinic trip"},
                 absorbed)
            o.accessibility_status = "degraded" if o.accessibility_status == "ok" else o.accessibility_status

    # ---------------------------------------------------------------- F3 severity
    for p in pop.personas:
        outcomes[p.persona_id].severity = severity_for(p, outcomes[p.persona_id], base, now)

    return SimResult(outcomes=outcomes, events=events, baseline=base, after=now)


def severity_for(p: Persona, o: Outcome, base: dict, now: dict) -> str:
    """F3, and every headline number in the product resolves to this predicate.

    Four ways to be severely harmed. The fourth is where the graph pays off: a person with
    no mobility limitation, living nowhere near a removed stop, classified as severely
    harmed because of who they care for.
    """
    if o.accessibility_status == "unreachable":
        return "high"
    if o.walk_distance_m > p.max_walk_m * SEVERE_WALK_MULTIPLIER:
        return "high"
    if o.essential_trips_completed < o.essential_trips_total:
        return "high"
    if o.second_order:
        return "high"

    if o.walk_distance_m > p.max_walk_m:
        return "moderate"
    worst = 0.0
    for name, b in base.get(p.persona_id, {}).items():
        n = now[p.persona_id].get(name)
        if b.reachable and n and n.reachable and b.time_min > 0:
            worst = max(worst, (n.time_min - b.time_min) / b.time_min)
    if worst > MODERATE_JOURNEY_DELTA:
        return "moderate"
    return "none"
