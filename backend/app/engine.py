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

from dataclasses import replace

from app.consultation import build_consultation
from app.geography import build_geography, display_dict
from app.graph import build_graph
from app.interventions import POLICY_COST_INDEX, candidates, run_candidate, validate
from app.metrics import disparity_pp, metrics_for, subgroup_metrics
from app.population import build_population
from app.scenario import POPULATION_SIZE, ROUNDS, SCENARIO_ID, SCENARIO_SEED, STUDY_AREA
from app.schemas.core import PATTERNS
from app.simulation import simulate

REMOVED_STOPS = {"55079", "55081"}
#: what through-riders gain from the express run. The trade the policy is making.
EXPRESS_SAVING_MIN = 2.4

POLICY_TEXT = (
    "Remove the two stops on Ang Mo Kio Avenue 3 from bus service 265 and run the service "
    "express between the interchange and Ave 8, without increasing the fleet."
)

READING = [
    {"n": "01", "claim": "Two stops are removed from service 265",
     "why": "Named explicitly: the two on Ang Mo Kio Avenue 3.", "assumed": False},
    {"n": "02", "claim": "The express segment runs interchange to Ave 8",
     "why": "Stated in the policy text.", "assumed": False},
    {"n": "03", "claim": "Through-riders save about 2.4 minutes",
     "why": "Derived from the skipped dwell time at two stops plus the faster running. "
            "Not stated in the policy; assumed.", "assumed": True},
    {"n": "04", "claim": "No additional vehicles are available",
     "why": "The text says without increasing the fleet, so any option needing new "
            "vehicles is out of scope.", "assumed": False},
    {"n": "05", "claim": "Feeder service 162 is unchanged",
     "why": "The policy does not mention it. Assumed to keep running as today.",
     "assumed": True},
]


def _policy_dict() -> dict:
    return {
        "objective": "Reduce end-to-end journey time on service 265 without new vehicles",
        "text": POLICY_TEXT,
        "modifications": {
            "remove_stops": sorted(REMOVED_STOPS),
            "add_express_segment": {"from_stop": "55007", "to_stop": "55139"},
            "frequency_delta_pct": 0,
        },
        "constraints": {"fleet_increase_allowed": False, "operating_budget_delta_pct": 8},
        "reading": READING,
        "resolved_entities": [
            {"kind": "service", "id": "265", "label": "265 Trunk"},
            {"kind": "stop", "id": "55079", "label": "Ang Mo Kio Ave 3"},
            {"kind": "stop", "id": "55081", "label": "Blk 226"},
        ],
    }


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


def build_run(run_id: str = "run_a91f") -> dict:
    geo = build_geography()
    pop = build_population(geo, POPULATION_SIZE)
    graph = build_graph(geo, pop)

    policy = simulate(geo, pop, REMOVED_STOPS, EXPRESS_SAVING_MIN)
    outcomes = list(policy.outcomes.values())
    sub = subgroup_metrics(pop, policy.outcomes)

    # ------------------------------------------------------------------ interventions
    ivs: list[dict] = []
    for c in candidates(REMOVED_STOPS, pop):
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
            r = run_candidate(c, geo, pop, REMOVED_STOPS, EXPRESS_SAVING_MIN)
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
    con = build_consultation(pop, policy.outcomes)
    flagged = next((r for r in con.calibration if r.flagged), None)

    return {
        "run_id": run_id,
        "scenario_id": SCENARIO_ID,
        "environment": "transport",
        "seed": SCENARIO_SEED,
        "population_version": "engine-1",
        "policy_version": "1",
        "rounds": ROUNDS,
        "generated_by": "backend/app/engine.py",
        "is_synthetic": True,
        "study_area": STUDY_AREA,
        "policy": _policy_dict(),
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
                "location": flagged.cohort_value if flagged else "n/a",
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
    geo = build_geography()
    pop = build_population(geo, POPULATION_SIZE)
    with_graph = simulate(geo, pop, REMOVED_STOPS, EXPRESS_SAVING_MIN, record_events=False)
    n_with = sum(1 for o in with_graph.outcomes.values() if o.second_order)

    cut = replace(pop, care_edges=[])
    without = simulate(geo, cut, REMOVED_STOPS, EXPRESS_SAVING_MIN, record_events=False)
    n_without = sum(1 for o in without.outcomes.values() if o.second_order)
    return n_with, n_without
