"""Have the planner propose alternatives, and cache them per town. J1.

    python scripts/plan_interventions.py --town ang-mo-kio --dry-run
    python scripts/plan_interventions.py --town ang-mo-kio

The five alternatives used to be written by hand in `interventions.py`, parameterised for
one closure in one town. This runs the model planner over the world facts, validates every
proposal, simulates the ones that survive, and writes the result beside the run. The API
loads that cache; nothing is planned at request time and the demo makes no call.

`--dry-run` prints the facts the model would be given and calls nothing, which is the
cheapest way to check that a new town produces a sane brief.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _common import cost_of, refuse_if_running
from app.engine import DEFAULT_TOWN, study_area_for_town
from app.interventions import validate
from app.plan import cache_path, facts_for, plan
from app.population import build_population
from app.scenario import POPULATION_SIZE
from app.services.llm import TELEMETRY, build_client


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--town", default=DEFAULT_TOWN)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the brief and call nothing")
    ap.add_argument("--allow-concurrent", action="store_true")
    args = ap.parse_args()

    if not args.allow_concurrent:
        refused = refuse_if_running("plan_interventions", "planner run")
        if refused is not None:
            return refused

    geo, removed = study_area_for_town(args.town)
    pop = build_population(geo, POPULATION_SIZE)
    print(f"{args.town}: closing {sorted(removed)}, {len(pop.personas)} residents\n")

    if args.dry_run:
        print(facts_for(geo, pop, removed))
        print("\n  nothing was called and nothing was spent.")
        return 0

    client = build_client(temperature=0.3, role="deliberation")
    before = len(TELEMETRY.calls)
    cands = plan(geo, pop, removed, client, on_note=lambda m: print(f"  {m}", flush=True))
    calls = TELEMETRY.calls[before:]
    tin, tout, cost = cost_of(calls, client.provider_name)

    for c in cands:
        validate(c, fleet_increase_allowed=False, geo=geo, removed=removed)

    ok = [c for c in cands if c.valid]
    print(f"\n  {len(cands)} proposed, {len(ok)} valid")
    for c in cands:
        mark = "ok " if c.valid else "REJ"
        print(f"    {mark} {c.kind:<20} {c.name[:44]:<46} cost {c.estimated_cost_index:.2f}")
        for e in c.validation_errors:
            print(f"          - {e}")

    if not ok:
        print("\n  every proposal was rejected. Nothing written: a cache of rejections "
              "would leave the options screen empty with no way to tell why.")
        return 1

    path = cache_path(args.town)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "town": args.town,
        # keyed on the closure as well as the town: a plan for different stops is a
        # different question, and serving it would put alternatives on the screen that
        # address stops nobody shut
        "closed": sorted(removed),
        "model": client.provider_name,
        "cost_usd": round(cost, 4),
        "tokens": {"input": tin, "output": tout},
        "proposed": len(cands),
        "valid": len(ok),
        # rejected candidates are kept, with their reasons. The options screen shows them,
        # and a plan that only records what passed hides how the planner actually did.
        "candidates": [{
            "intervention_id": c.intervention_id, "kind": c.kind, "name": c.name,
            "params": c.params, "rationale": c.rationale,
            "estimated_cost_index": c.estimated_cost_index,
            "valid": c.valid, "validation_errors": c.validation_errors,
        } for c in cands],
    }, indent=1), encoding="utf-8")
    print(f"\n  cost: ${cost:.4f} over {len(calls)} call(s)")
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
