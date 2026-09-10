"""Read the flagged cohort's comments and cache what they appear to be saying.

    python scripts/discover_constraint.py --town ang-mo-kio

One model call per town, cached to `data/runs/constraint-<town>.json` and loaded by the
engine thereafter. Nothing is generated at request time, so the demo cannot depend on a
model being reachable.

**What this proves, and what it does not.** On the seeded population the terrain effect is
ours, and one canned comment names a slope outright -- so a model reading those comments
is partly reading back a sentence this repository wrote. The mechanism is real and would
work on real consultation text; the discovery on demo data is a fixture exercising it, and
the cached file says so.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.consultation import build_consultation, constraint_path, discover_constraint
from app.engine import DEFAULT_TOWN, EXPRESS_SAVING_MIN, study_area_for_town, _road_of
from app.population import build_population
from app.services.llm import build_client
from app.simulation import simulate


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--town", default=DEFAULT_TOWN)
    ap.add_argument("--force", action="store_true", help="regenerate even if cached")
    args = ap.parse_args()

    path = constraint_path(args.town)
    if path.exists() and not args.force:
        print(f"already cached: {path}")
        print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=1))
        return 0
    if args.force:
        path.unlink(missing_ok=True)

    geo, closed = study_area_for_town(args.town)
    pop = build_population(geo, 2000)
    result = simulate(geo, pop, closed, EXPRESS_SAVING_MIN)
    road = _road_of(geo, sorted(closed)[0])
    con = build_consultation(pop, result.outcomes, road)

    flagged = next((r for r in con.calibration if r.flagged), None)
    if flagged is None:
        print("no cohort is flagged: nothing to explain, and nothing will be invented.")
        return 0
    cohort = flagged.cohort_value
    comments = [r.comment for r in con.responses
                if r.comment and (r.cohort or {}).get("home_subzone") == cohort]
    print(f"flagged cohort : {cohort}  ({flagged.signed_error:+.1f} pp, n={flagged.n})")
    print(f"comments to read: {len(comments)}")
    if not comments:
        print("no free text from this cohort: no reading is possible.")
        return 0

    payload = discover_constraint(args.town, cohort, comments,
                                  llm=build_client(temperature=0.0))
    print(json.dumps(payload, indent=1))
    print(f"\ncached: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
