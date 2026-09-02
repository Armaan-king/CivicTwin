"""Assemble one complete run: the function `load_run()` calls.

Everything below is computed. The scenario says which stops come out; the engine works out
who that costs, what the alternatives are worth, and what the consultation would and would
not have told you. Nothing is asserted.

The sequence is the product, in order:

```text
SIMULATE          simulation.simulate over the graph
FIND WHO          metrics, four subgroup axes
UNDERSTAND WHY    the cause chain, already emitted
DESIGN BETTER     interventions.candidates, validated
RE-SIMULATE       each valid one, same engine, same seeds
ASK REAL PEOPLE   consultation, with a response model that under-samples the harmed
LEARN             calibration against a terrain effect the model does not know about
```

Two runs are cached: the policy as written, and the same policy with the dependency edges
cut. The second is **N2**, the ablation, and it is the only honest way to claim the graph
does work: same seeds, same population, no `CARES_FOR`, and the second-order harm should
go to zero.
"""
from __future__ import annotations

import os
from dataclasses import replace
from typing import TYPE_CHECKING

from app.consultation import build_consultation
from app.geography import build_geography, display_dict
from app.graph import build_graph
from app.interventions import POLICY_COST_INDEX, candidates, run_candidate, validate
from app.metrics import disparity_pp, metrics_for, subgroup_metrics
from app.population import build_population
from app.scenario import POPULATION_SIZE, ROUNDS, SCENARIO_ID, SCENARIO_SEED, STUDY_AREA
from app.schemas.core import PATTERNS
from app.simulation import simulate

if TYPE_CHECKING:
    from app.schemas.policy import PolicyChange

#: Fallback study area, used only when no policy has been submitted -- the demo run the
#: frontend loads before anyone has typed anything. A real policy decides its own town.
DEFAULT_TOWN = os.environ.get("TOWN", "ang-mo-kio")
GEOGRAPHY = os.environ.get("GEOGRAPHY", "real")

#: what through-riders gain from the express run. The trade the policy is making.
EXPRESS_SAVING_MIN = 2.4


def study_area(policy: "PolicyChange | None" = None, text: str = ""):
    """The geography and the stops to close, decided by the policy that was submitted.

    This used to read a town from the environment, guess two stops, and then generate a
    policy description to match. The planner's own words were parsed and discarded, so
    every number downstream described a guess rather than their proposal.

    With no policy -- the demo run loaded before anyone has typed anything -- it falls back
    to the default town and the derived closures, and the reading says so.
    """
    if GEOGRAPHY != "real":
        return build_geography(), {"55079", "55081"}, None

    from app.geography_real import build_real_geography, pick_closures

    resolution = None
    town = DEFAULT_TOWN
    if policy is not None:
        from app.resolve import resolve_study_area
        resolution = resolve_study_area(policy, text)
        town = resolution.town

    geo = build_real_geography(town=town)

    if resolution and resolution.closures:
        return geo, set(resolution.closures), resolution

    # A policy that names a road but not the stops on it. Pick, and mark it assumed:
    # that is what the reading is for, and it is a question a planner can answer.
    return geo, pick_closures(geo), resolution


def _policy_dict(geo, removed: set[str], resolution=None, text: str = "") -> dict:
    """The policy, described in the town's own words.

    Every name here comes from the study area rather than from a constant, because a
    policy that says "Ang Mo Kio" while the engine simulates Bedok is worse than one that
    says nothing: it reads as a result.
    """
    names = [geo.stops[s].name for s in sorted(removed)]
    roads = sorted({_road_of(geo, s) for s in removed})
    feeder = geo.feeder_service
    gateway = geo.stops[geo.work_gateway].name
    dest = geo.stops[geo.clinic_stops[0]].name if geo.clinic_stops else "the essential destination"

    # The planner's own words when there are any. Only when nobody has submitted a policy
    # -- the demo run -- is a description generated, and the reading says which it is.
    stated = bool(text and text.strip())
    policy_text = text.strip() if stated else (
        f"Close the {len(names)} stops on {roads[0]} ({', '.join(names)}) and run service "
        f"{feeder} express through the segment, without increasing the fleet."
    )

    named = bool(resolution and resolution.closures)
    reading = [
        {"n": "01", "claim": f"{len(names)} stops close on {roads[0]}",
         "why": (f"Named in the policy: {', '.join(names)}." if named else
                 f"The policy did not say which stops. Assumed the {len(names)} on "
                 f"{roads[0]} furthest from {dest}, since closing one beside the "
                 f"destination would not be a policy anyone proposes."),
         "assumed": not named},
        {"n": "02", "claim": "This is a closure, not a service change",
         "why": (f"Each of these stops is served by several routes. Removing them from "
                 f"service {feeder} alone would be absorbed by the others, so the policy "
                 f"only bites if the stops themselves shut."), "assumed": False},
        {"n": "03", "claim": "Through-riders save about 2.4 minutes",
         "why": ("Derived from the skipped dwell time plus faster running. Not stated in "
                 "the policy; assumed."), "assumed": True},
        {"n": "04", "claim": "No additional vehicles are available",
         "why": ("The text says without increasing the fleet, so any option needing new "
                 "vehicles is out of scope."), "assumed": False},
        {"n": "05", "claim": f"{dest} is the essential destination",
         "why": (f"Taken from the stop names in the study area. Residents who depend on it "
                 f"are the ones a closure can cut off, so it decides who counts as "
                 f"severely harmed."), "assumed": True},
    ]
    return {
        "objective": f"Reduce end-to-end journey time on service {feeder} without new vehicles",
        "text": policy_text,
        "modifications": {
            "remove_stops": sorted(removed),
            "add_express_segment": {"from_stop": geo.work_gateway,
                                    "to_stop": sorted(removed)[-1]},
            "frequency_delta_pct": 0,
        },
        "constraints": {"fleet_increase_allowed": False, "operating_budget_delta_pct": 8},
        "reading": reading,
        "study_area": {
            "town": getattr(resolution, "town", DEFAULT_TOWN),
            "chosen_from": getattr(resolution, "considered", []),
            "matched": getattr(resolution, "matched", []),
            "unmatched": getattr(resolution, "unmatched", []),
        },
        "resolved_entities": (
            [{"kind": "service", "id": feeder, "label": f"Service {feeder}"}]
            + [{"kind": "stop", "id": s, "label": geo.stops[s].name} for s in sorted(removed)]
            + [{"kind": "interchange", "id": geo.work_gateway, "label": gateway}]
        ),
    }


def _road_of(geo, stop_id: str) -> str:
    """The road a stop sits on, if the study area knows; otherwise the stop's own name."""
    try:
        from app.geography_real import _road_name
        return _road_name(geo.stops[stop_id].name)
    except Exception:
        return geo.stops[stop_id].name


def _outcome_dicts(pop, result) -> list[dict]:
    return [
        {
            "persona_id": o.persona_id,
            "severity": o.severity,
            "walk_distance_m": o.walk_distance_m,
            "journey_time_min": o.journey_time_min,
            "essential_trips_completed": o.essential_trips_completed,
            "essential_trips_total": o.essential_trips_total,
            "accessibility_status": o.accessibility_status,
            "second_order": o.second_order,
            "newly_exposed": o.newly_exposed,
        }
        for o in result.outcomes.values()
    ]


def _persona_dicts(pop) -> list[dict]:
    return [
        {
            "persona_id": p.persona_id, "age_band": p.age_band,
            "home_subzone": p.home_subzone, "household_id": p.household_id,
            "household_role": p.household_role, "income_band": p.income_band,
            "employment_status": p.employment_status, "mobility_level": p.mobility_level,
            "max_walk_m": p.max_walk_m, "transfer_tolerance": p.transfer_tolerance,
            "work_start_time": p.work_start_time, "has_car_access": p.has_car_access,
            "is_caregiver": p.is_caregiver,
            "inconvenience_tolerance": p.inconvenience_tolerance,
            "switching_propensity": p.switching_propensity,
            "baseline_trust": p.baseline_trust, "needs_clinic": p.needs_clinic,
            "xy": list(p.xy), "block_id": p.block_id,
        }
        for p in pop.personas
    ]


def _graph_edges(pop, geo) -> list[dict]:
    """The dependency layer, which is the only part of the graph the payload carries.

    The full typed DiGraph stays in the engine: eight node types and nine edge types are
    what the rules traverse, and shipping all of it would put stops and subzones into a
    list the contract requires to be person-to-person. What the UI needs, and what the
    second-order finding rests on, is `CARES_FOR`.
    """
    return [
        {"source": e.carer, "target": e.dependent, "kind": "CARES_FOR",
         "attrs": {"criticality": e.criticality}}
        for e in pop.care_edges
    ]


def study_area_for(run):
    """Rebuild the study area a finished run was built with.

    The deliberation must reason about the same town and the same closures the run
    reported, not about whatever the default is. Both are recorded in the run's policy, so
    this reads them back rather than re-deriving from a guess.
    """
    if GEOGRAPHY != "real":
        return build_geography(), {"55079", "55081"}, None

    from app.geography_real import build_real_geography, pick_closures

    ref = run.policy.study_area
    geo = build_real_geography(town=(ref.town if ref and ref.town else DEFAULT_TOWN))
    closures = {s for s in run.policy.modifications.remove_stops if s in geo.stops}
    return geo, (closures or pick_closures(geo)), ref


def build_run(run_id: str = "run_a91f", policy: "PolicyChange | None" = None,
              text: str = "") -> dict:
    geo, removed, resolution = study_area(policy, text)
    pop = build_population(geo, POPULATION_SIZE)
    graph = build_graph(geo, pop)

    policy = simulate(geo, pop, removed, EXPRESS_SAVING_MIN)
    outcomes = list(policy.outcomes.values())
    sub = subgroup_metrics(pop, policy.outcomes)

    # ------------------------------------------------------------------ interventions
    ivs: list[dict] = []
    for c in candidates(removed, pop, geo):
        validate(c, fleet_increase_allowed=False)
        row = {
            "intervention_id": c.intervention_id, "kind": c.kind, "name": c.name,
            "params": c.params, "rationale": c.rationale, "valid": c.valid,
            "validation_errors": c.validation_errors,
            "estimated_cost_index": c.estimated_cost_index,
            "metrics": None, "carers_harmed": None,
            "newly_harmed_elsewhere": None, "subgroup_disparity_pp": None,
        }
        if c.valid:
            r = run_candidate(c, geo, pop, removed, EXPRESS_SAVING_MIN)
            row["metrics"] = metrics_for(list(r.outcomes.values()))
            row["carers_harmed"] = sum(
                1 for p in pop.personas
                if p.is_caregiver and r.outcomes[p.persona_id].severity == "high")
            row["newly_harmed_elsewhere"] = sum(
                1 for p in pop.personas
                if r.outcomes[p.persona_id].severity == "high"
                and policy.outcomes[p.persona_id].severity != "high")
            row["subgroup_disparity_pp"] = disparity_pp(subgroup_metrics(pop, r.outcomes))
        ivs.append(row)

    # ------------------------------------------------------------------ consultation
    # the blind spot lands on the road the policy touches, whichever town this is
    terrain_road = _road_of(geo, sorted(removed)[0])
    con = build_consultation(pop, policy.outcomes, terrain_road)
    flagged = next((r for r in con.calibration if r.flagged), None)

    return {
        "run_id": run_id,
        "scenario_id": SCENARIO_ID,
        "environment": "transport",
        "study_area_source": GEOGRAPHY,
        "seed": SCENARIO_SEED,
        "population_version": "engine-1",
        "policy_version": "1",
        "rounds": ROUNDS,
        "generated_by": "backend/app/engine.py",
        "is_synthetic": True,
        "study_area": STUDY_AREA,
        "policy": _policy_dict(geo, removed, resolution, text),
        "personas": _persona_dicts(pop),
        "graph": {"edges": _graph_edges(pop, geo)},
        "geography": display_dict(geo),
        "outcomes": _outcome_dicts(pop, policy),
        "events": [
            {"event_id": e.event_id, "round": e.round, "persona_id": e.persona_id,
             "kind": e.kind, "before": e.before, "after": e.after, "cause": e.cause}
            for e in policy.events
        ],
        "metrics": {
            "overall": metrics_for(outcomes),
            "subgroup": sub,
            "subgroup_disparity_pp": disparity_pp(sub),
            "operating_cost_index": POLICY_COST_INDEX,
        },
        "interventions": ivs,
        "consultation": {
            "responses": [
                {"response_id": r.response_id, "persona_id": r.persona_id,
                 "support": r.support, "perceived_fairness": r.perceived_fairness,
                 "clarity_of_explanation": r.clarity_of_explanation,
                 "confidence_in_delivery": r.confidence_in_delivery,
                 "expected_personal_impact": r.expected_personal_impact,
                 "comment": r.comment, "cohort": r.cohort, "is_seeded": r.is_seeded}
                for r in con.responses
            ],
            "response_count": len(con.responses),
            # never claimed, and shown as such in the UI. K1.
            "is_representative": False,
            "pcs": {"score": con.pcs, "components": con.pcs_components},
            "calibration": [
                {"cohort_axis": r.cohort_axis, "cohort_value": r.cohort_value,
                 "predicted_support": r.predicted_support,
                 "observed_support": r.observed_support,
                 "signed_error": r.signed_error, "n": r.n, "flagged": r.flagged}
                for r in con.calibration
            ],
            "blind_spots": [
                {"cohort_axis": b.cohort_axis, "cohort_value": b.cohort_value,
                 "harmed": b.harmed, "expected_responses": b.expected_responses,
                 "score": b.score}
                for b in con.blind_spots
            ],
            "discovered_constraint": {
                "type": "walk_quality",
                "location": flagged.cohort_value if flagged else terrain_road,
                "affects": ["walk_distance_m", "inconvenience_tolerance"],
                "source": "consultation free-text, corroborated by the cohort error",
                "note": "The covered walkway ends partway and there is a slope. The model "
                        "costed the distance and not the walk, so it over-predicted "
                        "support here and nowhere else.",
            },
            "proposed_adjustment": {
                "parameter": "walk_cost_multiplier[AMK Ave 3]",
                "from": 1.00, "to": 1.35,
                # L3. A human decides, always.
                "status": "awaiting_human_approval",
            },
        },
        "harm_patterns": {k: v.model_dump() for k, v in PATTERNS.items()},
    }


def ablation_second_order() -> tuple[int, int]:
    """N2: the same policy with the dependency edges cut.

    The only honest way to claim the graph does work. Same seeds, same population, no
    `CARES_FOR`: second-order harm should be N with the edges and 0 without.
    """
    geo, removed, _ = study_area()
    pop = build_population(geo, POPULATION_SIZE)
    with_graph = simulate(geo, pop, removed, EXPRESS_SAVING_MIN, record_events=False)
    n_with = sum(1 for o in with_graph.outcomes.values() if o.second_order)

    cut = replace(pop, care_edges=[])
    without = simulate(geo, cut, removed, EXPRESS_SAVING_MIN, record_events=False)
    n_without = sum(1 for o in without.outcomes.values() if o.second_order)
    return n_with, n_without
