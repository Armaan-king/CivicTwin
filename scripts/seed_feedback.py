"""Stage demo consultation submissions, marked as demo data.

    python scripts/seed_feedback.py --n 40

Every row is written with `source: "demo-seed"`, which is not cosmetic. A file of invented
submissions that the interface counts as real replies is the exact claim this product
exists to object to, so the provenance travels with each response and any screen reporting
a "real" count can say how many were staged.

The distribution is deliberately not flat. Residents on the road the closures sit on are
more negative, carers more negative still, and the unaffected are mildly positive -- which
is the shape a real consultation takes and the shape calibration has to be able to see.
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.consultation import FEEDBACK, record_feedback
from app.engine import DEFAULT_TOWN, study_area_for_town
from app.population import build_population

AGAINST = [
    "The new stop is much further and I have shopping to carry.",
    "Nobody asked the people who actually use that stop.",
    "The walk itself is the problem, not the distance on a map.",
    "I take my mother to her appointment. This makes that my problem, not the bus company's.",
    "There is no shelter on the new route and it rains most afternoons.",
    "Fine for people who are already fast on their feet.",
]
MIXED = [
    "Hard to say without seeing the new timetable.",
    "I understand why, I just do not think they costed the walk.",
    "Depends whether the buses really do come more often.",
    None,
]
FOR = [
    "Faster into town in the morning, which helps me.",
    "Sensible if the buses really do run more often.",
    "The old route had too many stops.",
    None,
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--town", default=DEFAULT_TOWN)
    ap.add_argument("--clear", action="store_true", help="drop existing demo rows first")
    args = ap.parse_args()

    path = FEEDBACK / "c1.jsonl"
    if args.clear and path.exists():
        kept = [ln for ln in path.read_text(encoding="utf-8").splitlines()
                if ln.strip() and '"source": "demo-seed"' not in ln]
        path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        print(f"cleared demo rows, kept {len(kept)} real submissions")

    geo, closed = study_area_for_town(args.town)
    pop = build_population(geo, 2000)
    # the road the closures sit on: its residents are the ones with something to say
    affected_road = geo.blocks[0]["subzone"]
    for b in geo.blocks:
        if any(s in closed for s in geo.stops):
            affected_road = b["subzone"]
            break

    rng = random.Random(20260910)
    people = rng.sample(pop.personas, min(args.n, len(pop.personas)))
    counts = {"against": 0, "mixed": 0, "for": 0}

    for p in people:
        on_road = p.home_subzone == affected_road
        lean = -1.4 if on_road else 0.0
        if p.is_caregiver:
            lean -= 0.6
        if p.mobility_level in ("moderate", "severe"):
            lean -= 0.5
        support = max(1, min(5, round(rng.gauss(3.6 + lean, 0.8))))
        pool = AGAINST if support <= 2 else (MIXED if support == 3 else FOR)
        counts["against" if support <= 2 else "mixed" if support == 3 else "for"] += 1
        record_feedback("c1", {
            "support": support,
            "perceived_fairness": max(1, min(5, support + rng.choice([-1, 0, 0, 1]))),
            "clarity_of_explanation": max(1, min(5, round(rng.gauss(3.2, 0.9)))),
            "confidence_in_delivery": max(1, min(5, round(rng.gauss(3.0, 1.0)))),
            "expected_personal_impact": -2 if support <= 2 else (0 if support == 3 else 1),
            "comment": rng.choice(pool),
            "cohort": {"age_band": p.age_band, "mobility_level": p.mobility_level,
                       "home_subzone": p.home_subzone,
                       "is_caregiver": str(p.is_caregiver)},
            "source": "demo-seed",
        })

    print(f"seeded {len(people)} demo submissions for {args.town}")
    print(f"  against {counts['against']}   unsure {counts['mixed']}   for {counts['for']}")
    print(f"  file: {path}")
    print("  every row carries source='demo-seed' and is counted apart from real replies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
