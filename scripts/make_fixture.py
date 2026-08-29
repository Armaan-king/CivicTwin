"""Generate the demo fixture: the contract the frontend renders and the engine must reproduce.

    ####################################################################
    #  THIS IS NOT THE SIMULATION ENGINE. DO NOT EXTEND IT.
    #
    #  It generates a shape-correct fixture so the frontend could be
    #  built before any backend existed. It deliberately cuts corners the
    #  real engine must not: no NetworkX graph, no shortest paths, no
    #  stop geometry, and exposure is a per-subzone probability rather
    #  than a consequence of distance.
    #
    #  The engine belongs in backend/app/simulation/ and must satisfy
    #  backend/tests/test_contract.py. See backend/IMPLEMENTING.md.
    #
    #  What IS worth taking from here is the seeding discipline below.
    ####################################################################

W1 from HANDOFF.md. Shape-correct, not simulation-correct. The real engine replaces the
numbers later; nothing about the shape changes when it does.

Two rules from scenario-v1.md drive the structure here:

  G2  persona_seed = hash(scenario_seed, persona_id). Never a sequential stream, so a
      persona draws the same numbers under every policy variant and a baseline-vs-
      intervention delta is causal rather than reshuffled randomness.

  L1  Predicted support is an explicit function of three persona quantities. The observed
      responses carry a terrain penalty the prediction function does NOT have, which is
      why calibration finds a real, attributable error rather than an injected one.

    python scripts/make_fixture.py
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import random

SCENARIO_SEED = 4471
POPULATION = 2000
BASELINE_JOURNEY_MIN = 46
WALK_SPEED_M_PER_MIN = 78          # ~4.7 km/h, an older resident on a covered walkway
BASE_WALK_M = 380
REMOVED_STOP_PENALTY_M = 860
EXPRESS_SAVING_MIN = 7

OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "fixtures" / "demo_run.json"

AGE_BANDS = ["<18", "18-34", "35-54", "55-64", "65-74", "75+"]
AGE_WEIGHTS = [0.16, 0.21, 0.30, 0.15, 0.11, 0.07]
MOBILITY = ["none", "mild", "moderate", "severe"]
MAX_WALK_M = {"none": 1200, "mild": 800, "moderate": 500, "severe": 250}
INCOME = ["low", "mid", "high"]
SUBZONES = ["AMK Ave 3", "AMK Ave 10", "Cheng San", "Townsville", "Kebun Baru"]
SUBZONE_W = [0.30, 0.22, 0.19, 0.16, 0.13]

MOBILITY_BY_AGE = {
    "<18":   [0.98, 0.02, 0.00, 0.00],
    "18-34": [0.97, 0.03, 0.00, 0.00],
    "35-54": [0.93, 0.06, 0.01, 0.00],
    "55-64": [0.84, 0.12, 0.03, 0.01],
    "65-74": [0.62, 0.24, 0.11, 0.03],
    "75+":   [0.38, 0.29, 0.24, 0.09],
}
CLINIC_P = {"<18": 0.04, "18-34": 0.06, "35-54": 0.14, "55-64": 0.33, "65-74": 0.62, "75+": 0.88}

BASE_EXPOSURE = {"AMK Ave 3": 0.86, "Kebun Baru": 0.44, "Cheng San": 0.28,
                 "Townsville": 0.12, "AMK Ave 10": 0.06}


def persona_rng(key: str) -> random.Random:
    digest = hashlib.sha256(f"{SCENARIO_SEED}:{key}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def pick(rng, options, weights):
    return rng.choices(options, weights=weights, k=1)[0]


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


# ----------------------------------------------------------------- population
def build_population():
    people = []
    for i in range(POPULATION):
        pid, hid = f"p_{i:04d}", f"h_{i // 3:04d}"
        rng = persona_rng(pid)
        home = pick(persona_rng(hid), SUBZONES, SUBZONE_W)   # households live together

        age = pick(rng, AGE_BANDS, AGE_WEIGHTS)
        mob = pick(rng, MOBILITY, MOBILITY_BY_AGE[age])
        income = pick(rng, INCOME, [0.34, 0.48, 0.18])
        employed = age in ("18-34", "35-54", "55-64") and rng.random() < 0.82
        student = age == "<18"
        car_p = {"low": 0.04, "mid": 0.14, "high": 0.41}[income]   # COE-driven, see A3

        people.append({
            "persona_id": pid, "age_band": age, "home_subzone": home, "household_id": hid,
            "household_role": "child" if student else "adult",
            "income_band": income,
            "employment_status": "student" if student else ("employed" if employed else (
                "retired" if age in ("65-74", "75+") else "unemployed")),
            "mobility_level": mob, "max_walk_m": MAX_WALK_M[mob],
            "transfer_tolerance": 0 if mob == "severe" else rng.choice([1, 1, 2]),
            "work_start_time": "09:00" if employed else None,
            "has_car_access": rng.random() < car_p,
            "is_caregiver": False,
            "inconvenience_tolerance": round(rng.betavariate(5, 5), 3),
            "switching_propensity": round(rng.betavariate(4, 6), 3),
            "baseline_trust": round(rng.betavariate(5, 4), 3),
            "needs_clinic": rng.random() < CLINIC_P[age],
            "xy": [round(rng.uniform(0, 1), 4), round(rng.uniform(0, 1), 4)],
        })
    return people


def assign_care_edges(people):
    """Directed and asymmetric. Harm propagates to the carer, never back. D2."""
    households = {}
    for p in people:
        households.setdefault(p["household_id"], []).append(p)

    edges = []
    for members in households.values():
        dependants = [m for m in members
                      if m["mobility_level"] in ("moderate", "severe") and m["needs_clinic"]]
        carers = [m for m in members
                  if m["mobility_level"] == "none" and m["employment_status"] == "employed"]
        for d in dependants:
            if not carers:
                continue
            carers[0]["is_caregiver"] = True
            edges.append({"source": carers[0]["persona_id"], "target": d["persona_id"],
                          "kind": "CARES_FOR", "attrs": {"criticality": "high"}})
    return edges


# ----------------------------------------------------------------- engine stand-in
def simulate(people, care_edges, variant="baseline", record_events=False):
    """Run one policy variant. Same personas, same per-persona seeds, every time."""
    outcomes, events, eid = {}, [], 0
    by_id = {p["persona_id"]: p for p in people}

    for p in people:
        rng = persona_rng(p["persona_id"] + ":sim")            # identical across variants
        exposure = BASE_EXPOSURE[p["home_subzone"]]
        walk_penalty = REMOVED_STOP_PENALTY_M
        newly = False

        if variant == "retain_stop_peak":
            exposure *= 0.38                 # stop reopens at peak; off-peak still loses it
        elif variant == "add_shuttle_feeder":
            walk_penalty = 300               # feeder shortens the walk rather than removing exposure
        elif variant == "reroute_feeder":
            if p["home_subzone"] in ("AMK Ave 3", "Kebun Baru"):
                exposure *= 0.55
            elif p["home_subzone"] == "AMK Ave 10":
                exposure, newly = 0.34, True  # helps the corridor, pushes riders onto Ave 10

        affected = rng.random() < exposure
        walk = BASE_WALK_M + (walk_penalty if affected else 0) + int(rng.uniform(-90, 140))
        walk_min = max(0.0, (walk - BASE_WALK_M) / WALK_SPEED_M_PER_MIN)
        journey = BASELINE_JOURNEY_MIN - EXPRESS_SAVING_MIN + walk_min + rng.uniform(-2.5, 2.5)

        severity, status = "none", "ok"
        if affected and walk > p["max_walk_m"] * 1.5:
            severity, status = "high", "unreachable"
        elif affected and walk > p["max_walk_m"]:
            severity, status = "moderate", "degraded"
        if p["needs_clinic"] and status == "unreachable":
            severity = "high"

        outcomes[p["persona_id"]] = {
            "persona_id": p["persona_id"], "severity": severity,
            "walk_distance_m": walk, "journey_time_min": round(journey, 1),
            "essential_trips_completed": 0 if (p["needs_clinic"] and severity == "high") else 1,
            "essential_trips_total": 1 if p["needs_clinic"] else 0,
            "accessibility_status": status, "second_order": False,
            "newly_exposed": newly and severity != "none",
        }

        if record_events and severity != "none":
            eid += 1
            events.append({"event_id": f"evt_{eid:05d}", "round": 1, "persona_id": p["persona_id"],
                           "kind": "ACCESSIBILITY_THRESHOLD_EXCEEDED",
                           "before": {"walk_distance_m": BASE_WALK_M},
                           "after": {"walk_distance_m": walk}, "cause": None})
            if p["needs_clinic"] and severity == "high":
                eid += 1
                events.append({"event_id": f"evt_{eid:05d}", "round": 1, "persona_id": p["persona_id"],
                               "kind": "ESSENTIAL_ACCESS_DEGRADED",
                               "before": {"accessibility_status": "ok"},
                               "after": {"accessibility_status": status},
                               "cause": events[-1]["event_id"]})

    # rounds 2 and 3: the carer absorbs it, then breaches her own constraint. B1, F3 clause 4.
    for e in care_edges:
        if outcomes[e["target"]]["severity"] != "high":
            continue
        carer, co = by_id[e["source"]], outcomes[e["source"]]
        if record_events:
            trigger = next((ev for ev in events if ev["persona_id"] == e["target"]
                            and ev["kind"] == "ESSENTIAL_ACCESS_DEGRADED"), None)
            eid += 1
            events.append({"event_id": f"evt_{eid:05d}", "round": 2, "persona_id": e["source"],
                           "kind": "CAREGIVER_SUPPORT_TRIGGERED",
                           "before": {"providing_transport": False},
                           "after": {"providing_transport": True},
                           "cause": trigger["event_id"] if trigger else None})
        if carer["work_start_time"]:
            if record_events:
                eid += 1
                events.append({"event_id": f"evt_{eid:05d}", "round": 3, "persona_id": e["source"],
                               "kind": "WORK_ARRIVAL_MISSED",
                               "before": {"arrival": "08:44"}, "after": {"arrival": "09:26"},
                               "cause": events[-1]["event_id"]})
            co["severity"] = "high"
            co["second_order"] = True
    return outcomes, events



# ----------------------------------------------------------------- geography
# A stand-in street grid so both visuals read from data rather than scattering marks.
# Replaced wholesale when real LTA stop coordinates land (M1); nothing downstream
# knows the difference because the shape stays the same.
GRID_COLS, GRID_ROWS = 12, 8
BLOCK, ROAD = 78, 26            # metres-ish, in a local plan coordinate space


def build_geography(people):
    """Blocks, roads, the corridor and its stops. Deterministic from the scenario seed."""
    rng = persona_rng("geography")

    # subzones occupy contiguous bands of the grid, the way estates actually do
    bands = {}
    per = GRID_COLS // len(SUBZONES) + 1
    for i, z in enumerate(SUBZONES):
        bands[z] = range(i * per, min((i + 1) * per, GRID_COLS))

    blocks = []
    for zone, cols in bands.items():
        for cx in cols:
            for ry in range(GRID_ROWS):
                if rng.random() < 0.12:          # a park, a carpark, a school field
                    continue
                blocks.append({
                    "block_id": f"b_{cx:02d}_{ry:02d}",
                    "subzone": zone,
                    "x": cx * (BLOCK + ROAD),
                    "y": ry * (BLOCK + ROAD),
                    "w": BLOCK - rng.choice([0, 0, 8, 14]),
                    "h": BLOCK - rng.choice([0, 0, 8, 14]),
                    "storeys": rng.choice([8, 10, 10, 12, 12, 14, 16, 18]),
                    "residents": [],
                })

    by_zone = {}
    for b in blocks:
        by_zone.setdefault(b["subzone"], []).append(b)
    for p in people:
        pool = by_zone.get(p["home_subzone"]) or blocks
        home = pool[persona_rng(p["household_id"] + ":block").randrange(len(pool))]
        home["residents"].append(p["persona_id"])
        p["block_id"] = home["block_id"]

    span_x = GRID_COLS * (BLOCK + ROAD)
    span_y = GRID_ROWS * (BLOCK + ROAD)

    roads = ([{"x1": c * (BLOCK + ROAD) - ROAD / 2, "y1": 0,
               "x2": c * (BLOCK + ROAD) - ROAD / 2, "y2": span_y, "kind": "minor"}
              for c in range(GRID_COLS + 1)]
             + [{"x1": 0, "y1": r * (BLOCK + ROAD) - ROAD / 2,
                 "x2": span_x, "y2": r * (BLOCK + ROAD) - ROAD / 2, "kind": "minor"}
                for r in range(GRID_ROWS + 1)])

    # the corridor: an arterial running the length of the estate
    corridor_y = 3 * (BLOCK + ROAD) - ROAD / 2
    roads.append({"x1": 0, "y1": corridor_y, "x2": span_x, "y2": corridor_y, "kind": "arterial"})

    stops, sid = [], 55000
    for i in range(9):
        sid += 7 + i
        stops.append({
            "stop_id": str(sid),
            "x": round(70 + i * (span_x - 140) / 8, 1),
            "y": corridor_y,
            "removed": False,
            "name": f"Ave {i + 1}",
        })
    for s in stops:
        if s["stop_id"] in ("55079", "55081"):
            s["removed"] = True
    # the fixture's policy names 55079 and 55081, so guarantee those two exist
    stops[3]["stop_id"], stops[3]["removed"], stops[3]["name"] = "55079", True, "Ang Mo Kio Ave 3"
    stops[4]["stop_id"], stops[4]["removed"], stops[4]["name"] = "55081", True, "Blk 226"
    stops[0]["name"] = "Interchange"

    return {
        "span": [span_x, span_y],
        "blocks": [{k: v for k, v in b.items() if k != "residents"} | {"population": len(b["residents"])}
                   for b in blocks],
        "roads": roads,
        "stops": stops,
        "route": [[s["x"], s["y"]] for s in stops],
        "polyclinic": {"x": round(span_x * 0.14, 1), "y": round(span_y * 0.82, 1)},
    }


# ----------------------------------------------------------------- metrics
def metrics_for(subset, outcomes):
    if not subset:
        return None
    o = [outcomes[p["persona_id"]] for p in subset]
    severe = sum(1 for x in o if x["severity"] == "high")
    walks = sorted(x["walk_distance_m"] for x in o)
    total = sum(x["essential_trips_total"] for x in o)
    done = sum(x["essential_trips_completed"] for x in o if x["essential_trips_total"])
    return {
        "n": len(o),
        "avg_journey_time_delta": round(
            sum(x["journey_time_min"] for x in o) / len(o) - BASELINE_JOURNEY_MIN, 2),
        "severe_harm_count": severe,
        "severe_harm_rate": round(severe / len(o), 4),
        "essential_trip_completion": round(done / total, 4) if total else None,
        "walk_distance_p90": walks[int(len(walks) * 0.9) - 1],
    }


def subgroup_metrics(people, outcomes):
    out = {}
    for axis in ("age_band", "mobility_level", "home_subzone"):
        out[axis] = {v: metrics_for([p for p in people if p[axis] == v], outcomes)
                     for v in sorted({p[axis] for p in people})}
    out["is_caregiver"] = {str(v): metrics_for([p for p in people if p["is_caregiver"] == v], outcomes)
                           for v in (True, False)}
    return out


def disparity(sub):
    """Spread between best and worst reported age cohort, in percentage points. I3."""
    rates = [m["severe_harm_rate"] for m in sub["age_band"].values() if m and m["n"] >= 50]
    return round((max(rates) - min(rates)) * 100, 1) if rates else 0.0


# ----------------------------------------------------------------- interventions
INTERVENTIONS = [
    {"intervention_id": "alt_01", "kind": "retain_stop_peak", "name": "Peak-hour stop retention",
     "params": {"stop_id": "55079", "hours": ["07:00-10:00", "17:00-20:00"]},
     "rationale": "Keeps the stop open when the clinic and work trips actually happen.",
     "valid": True, "validation_errors": [], "estimated_cost_index": 1.06},
    {"intervention_id": "alt_02", "kind": "add_shuttle_feeder", "name": "Zone C shuttle feeder",
     "params": {"from_subzone": "AMK Ave 3", "to_stop": "55009", "headway_min": 20},
     "rationale": "Shortens the walk instead of restoring the stop.",
     "valid": True, "validation_errors": [], "estimated_cost_index": 1.31},
    {"intervention_id": "alt_03", "kind": "reroute_feeder", "name": "Reroute service 262",
     "params": {"service_id": "262", "via_stop": "55081"},
     "rationale": "Uses an existing feeder rather than adding vehicles.",
     "valid": True, "validation_errors": [], "estimated_cost_index": 0.97},
    {"intervention_id": "alt_04", "kind": "targeted_support",
     "name": "Subsidised transport for flagged residents",
     "params": {"cohort": "mobility_moderate_severe", "subsidy_type": "point_to_point"},
     "rationale": "Bypasses the network for the people who lost access.",
     "valid": False,
     "validation_errors": ["operating_budget_delta_pct must stay 0; this needs +14%"],
     "estimated_cost_index": 1.14},
    {"intervention_id": "alt_05", "kind": "phase_rollout", "name": "Phased rollout over two quarters",
     "params": {"delay_weeks": 26, "stages": 2},
     "rationale": "Delays the change so residents can adjust.",
     "valid": False,
     "validation_errors": ["defers harm without reducing it; final-state harm is unchanged"],
     "estimated_cost_index": 1.00},
]


# ----------------------------------------------------------------- consultation
COMMENTS = [
    ("The covered walkway stops at Blk 226. Past that you are in the sun or the rain the whole "
     "way, and there is a slope. My mother will not do it.", "AMK Ave 3", "55-64", "moderate"),
    ("Faster to the interchange in the morning, which I do notice. But my neighbour who uses a "
     "walking frame simply cannot get to the new stop.", "AMK Ave 3", "35-54", "none"),
    ("Nobody asked the people who take the 265 to the polyclinic on a Tuesday.",
     "Kebun Baru", "65-74", "mild"),
    ("Saves me about five minutes each way. I support it.", "AMK Ave 10", "18-34", "none"),
    ("I will end up driving my father, which means I am late for work twice a week.",
     "AMK Ave 3", "35-54", "none"),
]


def build_consultation(people, outcomes):
    """Predicted support from L1. Observed carries a terrain penalty L1 does not model.

    That gap is the point: the calibration error has a cause the model is missing,
    rather than a bias someone typed in.
    """
    g0, g1, g2, g3 = 0.15, 1.9, 0.055, 1.25          # declared, not fitted. G3.
    rng = random.Random(SCENARIO_SEED ^ 0xC0FFEE)

    def predicted(p):
        o = outcomes[p["persona_id"]]
        impact = o["journey_time_min"] - (BASELINE_JOURNEY_MIN - EXPRESS_SAVING_MIN)
        return sigmoid(g0 + g1 * (p["baseline_trust"] - 0.5) - g2 * impact
                       - g3 * (1 if o["severity"] == "high" else 0))

    # the walkway gap is a property of the WALK, not of the walker. anyone routed onto that
    # stretch meets it; a mobility limitation only makes it worse. this is the constraint the
    # prediction function above does not have, and the reason calibration finds a real error.
    TERRAIN = {"none": 0.13, "mild": 0.26, "moderate": 0.45, "severe": 0.58}

    def observed(p):
        base = predicted(p)
        o = outcomes[p["persona_id"]]
        made_the_walk = (p["home_subzone"] == "AMK Ave 3"
                         and o["walk_distance_m"] > BASE_WALK_M + 200)
        terrain = TERRAIN[p["mobility_level"]] if made_the_walk else 0.0
        if p["is_caregiver"]:
            terrain += 0.10
        return max(0.02, min(0.98, base - terrain + rng.uniform(-0.06, 0.06)))

    # self-selected respondents, skewed toward the affected corridor as real ones are
    def turnout(p):
        w = 18 if p["home_subzone"] == "AMK Ave 3" else 10
        if p["age_band"] in ("65-74", "75+"):
            w = int(w * 2.1)          # older residents turn out for their own bus route
        if p["mobility_level"] in ("moderate", "severe"):
            w = int(w * 1.8)
        return w

    pool = [p for p in people for _ in range(turnout(p))]
    sample = rng.sample(pool, k=318)

    responses = []
    for i, p in enumerate(sample):
        s = observed(p)
        responses.append({
            "response_id": f"r_{i:04d}", "persona_id": p["persona_id"],
            "support": max(1, min(5, round(1 + s * 4))),
            "perceived_fairness": max(1, min(5, round(1 + (s * 0.8 + rng.uniform(-.1, .2)) * 4))),
            "clarity_of_explanation": max(1, min(5, round(rng.uniform(3.2, 4.8)))),
            "confidence_in_delivery": max(1, min(5, round(rng.uniform(1.9, 3.7)))),
            "expected_personal_impact": max(-2, min(2, round((s - 0.5) * 4))),
            "comment": None,
            "cohort": {"age_band": p["age_band"], "home_subzone": p["home_subzone"],
                       "mobility_level": p["mobility_level"]},
            "is_seeded": True,
        })
    for j, (text, zone, age, mob) in enumerate(COMMENTS):
        responses[j]["comment"] = text
        responses[j]["cohort"] = {"age_band": age, "home_subzone": zone, "mobility_level": mob}

    rows = []

    by_pid = {p["persona_id"]: p for p in people}

    def row(label, axis, value, _members=None):
        """Predicted and observed over the SAME respondents.

        Comparing a population-wide prediction against a self-selected sample would
        measure who turned up, not where the model is wrong. L2 wants model error.
        """
        pool = ([r for r in responses if r["cohort"].get(axis) == value] if axis
                else list(responses))
        if not pool:
            return
        pred = sum(predicted(by_pid[r["persona_id"]]) for r in pool) / len(pool)
        obs = sum((r["support"] - 1) / 4 for r in pool) / len(pool)
        err = round((obs - pred) * 100, 1)
        rows.append({"cohort_axis": axis or "overall", "cohort_value": label,
                     "predicted_support": round(pred * 100, 1),
                     "observed_support": round(obs * 100, 1),
                     "signed_error": err, "n": len(pool),
                     "flagged": abs(err) > 10 and len(pool) >= 30})

    row("Overall", None, None, people)
    for band in ["18-34", "35-54", "55-64", "65-74", "75+"]:
        row(f"Age {band}", "age_band", band, [p for p in people if p["age_band"] == band])
    for mob in ["moderate", "severe"]:
        row(f"Mobility {mob}", "mobility_level", mob,
            [p for p in people if p["mobility_level"] == mob])
    row("AMK Ave 3", "home_subzone", "AMK Ave 3",
        [p for p in people if p["home_subzone"] == "AMK Ave 3"])

    def component(field):
        vals = [r[field] for r in responses]
        return round((sum(vals) / len(vals) - 1) / 4 * 100)

    comps = {k: component(k) for k in
             ("support", "perceived_fairness", "clarity_of_explanation", "confidence_in_delivery")}

    return {
        "responses": responses, "response_count": len(responses), "is_representative": False,
        # score never ships without its components. K4.
        "pcs": {"score": round(sum(comps.values()) / len(comps)), "components": comps},
        "calibration": rows,
        "discovered_constraint": {
            "type": "sheltered_walkway_gap", "location": "AMK Ave 3",
            "affects": ["mobility moderate", "mobility severe"],
            "source": "consultation comment",
            "note": "The model treats every 500 m of walk as equivalent. This one is not.",
        },
        "proposed_adjustment": {
            "parameter": "baseline_trust weight", "from": 0.42, "to": 0.29,
            "status": "awaiting_human_approval",     # never auto-applied. L3.
        },
    }


POLICY_READING = [
    {"n": "01", "claim": "You want to cut journey time and running cost.",
     "why": "Read from 'run non-stop' and 'no extra buses'. Both become objectives it scores against.",
     "assumed": False},
    {"n": "02", "claim": "Two stops come out of service 265.",
     "why": "'The two stops on Ang Mo Kio Avenue 3' matched exactly two stops on that road served "
            "by 265. Three matches would have stopped and asked.", "assumed": False},
    {"n": "03", "claim": "The fleet cannot grow.",
     "why": "'No extra buses' is a hard constraint, not a preference. Any alternative needing more "
            "vehicles is rejected before it is simulated.", "assumed": False},
    {"n": "04", "claim": "One thing was assumed.",
     "why": "You did not say when the express segment runs. It assumed all day. Change it if that "
            "is wrong.", "assumed": True},
]


def main():
    people = build_population()
    care_edges = assign_care_edges(people)
    outcomes, events = simulate(people, care_edges, "baseline", record_events=True)

    overall = metrics_for(people, outcomes)
    sub = subgroup_metrics(people, outcomes)

    alts = []
    for spec in INTERVENTIONS:
        entry = dict(spec)
        if spec["valid"]:
            o2, _ = simulate(people, care_edges, spec["kind"])   # identical seed. simulation.md 23.
            entry["metrics"] = metrics_for(people, o2)
            entry["carers_harmed"] = sum(1 for x in o2.values() if x["second_order"])
            entry["newly_harmed_elsewhere"] = sum(1 for x in o2.values() if x.get("newly_exposed"))
            entry["subgroup_disparity_pp"] = disparity(subgroup_metrics(people, o2))
        else:
            entry["metrics"] = None
        alts.append(entry)

    geography = build_geography(people)   # also stamps block_id onto each persona
    consultation = build_consultation(people, outcomes)

    doc = {
        "run_id": "run_a91f", "scenario_id": "scenario_sg_bus_v1", "seed": SCENARIO_SEED,
        "population_version": "fixture-1", "policy_version": "1", "rounds": 3,
        "generated_by": "scripts/make_fixture.py", "is_synthetic": True,
        "study_area": "Ang Mo Kio",
        "policy": {
            "text": ("Remove the two stops on Ang Mo Kio Avenue 3 from bus service 265 and run "
                     "non-stop between the interchange and the Avenue 10 stop. No extra buses, "
                     "the fleet stays the same size."),
            "objective": "reduce journey time and operating cost",
            "modifications": {"remove_stops": ["55079", "55081"],
                              "add_express_segment": {"from_stop": "55009", "to_stop": "55101"},
                              "frequency_delta_pct": 0},
            "constraints": {"fleet_increase_allowed": False, "operating_budget_delta_pct": 0},
            "reading": POLICY_READING,
            "resolved_entities": [
                {"label": "Ang Mo Kio Ave 3", "ref": "stop 55079"},
                {"label": "Blk 226 Ang Mo Kio Ave 3", "ref": "stop 55081"},
                {"label": "Service 265", "ref": "42 stops affected"},
            ],
        },
        "personas": people, "graph": {"edges": care_edges},
        "geography": geography,
        "outcomes": list(outcomes.values()), "events": events,
        "metrics": {"overall": overall, "subgroup": sub,
                    "subgroup_disparity_pp": disparity(sub), "operating_cost_index": 0.94},
        "interventions": alts,
        "consultation": consultation,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")

    second = sum(1 for x in outcomes.values() if x["second_order"])
    flagged = [r for r in consultation["calibration"] if r["flagged"]]
    print(f"wrote {OUT.name}")
    print(f"  personas {len(people)}   edges {len(care_edges)}   events {len(events)}")
    print(f"  mean journey {overall['avg_journey_time_delta']:+.1f} min   "
          f"severe {overall['severe_harm_count']}   second-order {second}")
    print(f"  interventions {sum(1 for a in alts if a['valid'])} valid / {len(alts)} generated")
    print(f"  responses {consultation['response_count']}   PCS {consultation['pcs']['score']}   "
          f"flagged {len(flagged)}")
    for r in flagged:
        print(f"    {r['cohort_value']:18s} pred {r['predicted_support']:5.1f}  "
              f"obs {r['observed_support']:5.1f}  err {r['signed_error']:+6.1f}  n={r['n']}")


if __name__ == "__main__":
    main()
