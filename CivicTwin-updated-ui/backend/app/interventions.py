"""The five typed actions, validated then re-simulated. J1, J2.

The action space is closed. A planner selects and parameterises; it never invents a type
(**J1**). That is what makes an alternative checkable: every candidate reduces to a
concrete change to the network or the population, and the engine runs it exactly as it ran
the policy.

Nothing here scores a candidate it did not simulate. A rejected candidate carries
`metrics: None`, because giving it a number would be inventing a result, and
`test_contract.py` asserts it.

The comparison is deliberately not a single utility score. Three of these alternatives beat
the policy on severe harm; they disagree about who pays for it, and collapsing that into one
number is precisely the move that produced the original policy.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from app.geography import Geography, Service, distance_m
from app.population import Population
from app.simulation import SimResult, simulate

#: what the policy as written costs to run, relative to the service before it. Removing
#: stops and running express is cheaper, which is why it was proposed.
POLICY_COST_INDEX = 0.94

#: the constraint the policy declares. A candidate above this is rejected, not scored.
BUDGET_CEILING = 1.08


@dataclass
class Candidate:
    intervention_id: str
    kind: str
    name: str
    params: dict
    rationale: str
    estimated_cost_index: float
    valid: bool = True
    validation_errors: list[str] = field(default_factory=list)
    #: None until simulated, and stays None if invalid
    result: SimResult | None = None


def _with_service(geo: Geography, service: Service) -> Geography:
    g = copy.copy(geo)
    g.services = dict(geo.services)
    g.services[service.service_id] = service
    return g


def candidates(removed: set[str], pop: Population, geo: Geography) -> list[Candidate]:
    """The five, parameterised for this scenario.

    `reroute_feeder` is here because an alternative that only ever looks good is not a
    comparison. Rerouting the feeder onto the affected corridor helps the people the policy
    hurt and strands the people at the end of the line it used to serve, in a subzone the
    original policy never touched. That trade is the reason this screen exists.
    """
    assisted = [p.persona_id for p in pop.personas
                if p.needs_clinic and p.mobility_level in ("moderate", "severe")]
    clinic = geo.clinic_stops[0]
    feeder = geo.services[geo.feeder_service]
    # An alternative serves the stops *around* a closure, never the closure itself. Letting
    # a shuttle call at a closed stop makes every such candidate a quiet undo of the
    # policy: harm goes to exactly zero, which looks like a brilliant intervention and is
    # really just the baseline wearing a hat.
    nearby = _nearest_surviving(geo, removed, per_closure=2)
    # the two stops on the feeder furthest from the destination it is being moved toward:
    # rerouting has to cost somebody their service, and this names who.
    dropped = sorted(
        (s for s in dict.fromkeys(feeder.stops) if s not in removed and s not in nearby),
        key=lambda s: -distance_m(geo.stops[s].xy, geo.stops[clinic].xy),
    )[:2]
    return [
        Candidate(
            intervention_id="iv_retain_peak",
            kind="retain_stop_peak",
            name="Retain both stops at peak",
            params={"stops": sorted(removed), "hours": "07:00-09:30, 17:00-19:30"},
            rationale="Keep the express saving off-peak and give the corridor back during "
                      "the commute.",
            estimated_cost_index=1.02,
        ),
        Candidate(
            intervention_id="iv_shuttle",
            kind="add_shuttle_feeder",
            name="Clinic shuttle on the affected corridor",
            params={"serves": [*nearby, clinic, geo.work_gateway], "headway_min": 20},
            rationale="A small vehicle linking the stops either side of the closure to the "
                      "hospital and the interchange, sized for the trips the policy broke.",
            estimated_cost_index=1.06,
        ),
        Candidate(
            intervention_id="iv_reroute",
            kind="reroute_feeder",
            name=f"Reroute service {geo.feeder_service} onto the corridor",
            params={"add": nearby, "drop": dropped},
            rationale="No new vehicles. The feeder calls at the stops either side of the "
                      "closure instead of the far end of its loop.",
            estimated_cost_index=0.95,
        ),
        Candidate(
            intervention_id="iv_support",
            kind="targeted_support",
            name="Assisted transport for clinic-dependent residents",
            params={"eligible": "mobility-limited with an essential clinic trip",
                    "n_eligible": len(assisted)},
            rationale="Door-to-door booking for the residents whose walk the policy pushed "
                      "past what they can manage.",
            estimated_cost_index=1.05,
        ),
        Candidate(
            intervention_id="iv_phase",
            kind="phase_rollout",
            name="Close one stop, keep the other",
            params={"close_now": sorted(removed)[:1], "defer": sorted(removed)[1:]},
            rationale="Half the closure. The remaining stop keeps the corridor within reach "
                      "of the residents who cannot walk to the next one.",
            estimated_cost_index=0.97,
        ),
        Candidate(
            intervention_id="iv_fleet",
            kind="add_shuttle_feeder",
            name="Full shuttle network, 10-minute headway",
            params={"serves": "all four subzones", "headway_min": 10, "vehicles": 6},
            rationale="Cover every subzone at commuter frequency.",
            estimated_cost_index=1.34,
        ),
    ]


def _nearest_surviving(geo: Geography, removed: set[str], per_closure: int) -> list[str]:
    """The stops a closure pushes people onto. Never a closed stop."""
    out: list[str] = []
    for closed in sorted(removed):
        here = geo.stops[closed].xy
        alts = sorted((s for s in geo.stops.values() if s.stop_id not in removed),
                      key=lambda s: distance_m(s.xy, here))
        for s in alts[:per_closure]:
            if s.stop_id not in out:
                out.append(s.stop_id)
    return out


def validate(c: Candidate, fleet_increase_allowed: bool) -> Candidate:
    """J2. A candidate is checked before it is run, and a rejection states why."""
    errors: list[str] = []
    if c.estimated_cost_index > BUDGET_CEILING:
        errors.append(
            f"operating cost index {c.estimated_cost_index:.2f} exceeds the declared "
            f"ceiling of {BUDGET_CEILING:.2f}"
        )
    if c.kind == "add_shuttle_feeder" and c.params.get("vehicles", 0) > 0 \
            and not fleet_increase_allowed:
        errors.append("requires additional vehicles; the policy declares no fleet increase")
    c.validation_errors = errors
    c.valid = not errors
    return c


def run_candidate(
    c: Candidate, geo: Geography, pop: Population, removed: set[str], express_saving_min: float
) -> SimResult | None:
    """Re-simulate one alternative. The same engine, the same seeds, a different network."""
    if not c.valid:
        return None

    if c.kind == "retain_stop_peak":
        return simulate(geo, pop, removed, express_saving_min,
                        retained_peak=frozenset(removed))

    if c.kind == "targeted_support":
        assisted = frozenset(p.persona_id for p in pop.personas
                             if p.needs_clinic and p.mobility_level in ("moderate", "severe"))
        return simulate(geo, pop, removed, express_saving_min, assisted=assisted)

    if c.kind == "add_shuttle_feeder":
        serves = [s for s in c.params["serves"]] if isinstance(c.params["serves"], list) else []
        shuttle = Service("S1", "S1 Clinic Shuttle",
                          headway_min=float(c.params["headway_min"]), stops=serves)
        # the closure stands. the shuttle is an extra service through the stops around it.
        g = _with_service(geo, shuttle)
        return simulate(g, pop, removed, express_saving_min)

    if c.kind == "reroute_feeder":
        old = geo.services[geo.feeder_service]
        kept = [s for s in old.stops if s not in c.params["drop"]]
        insert_at = max(1, len(kept) - 1)
        stops = kept[:insert_at] + list(c.params["add"]) + kept[insert_at:]
        g = _with_service(geo, Service(old.service_id, old.name, old.headway_min, stops))
        return simulate(g, pop, removed, express_saving_min)

    if c.kind == "phase_rollout":
        return simulate(geo, pop, set(sorted(removed)[:1]), express_saving_min)

    raise ValueError(f"no runner for intervention kind {c.kind!r}")
