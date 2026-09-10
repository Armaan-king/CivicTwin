"""Run the population deliberation for a town and report what it can speak for.

    python scripts/run_deliberation.py --town ang-mo-kio --limit 24   # a cheap look
    python scripts/run_deliberation.py --town ang-mo-kio              # the whole cohort

Every batch is cached on a content hash, so a repeat run costs nothing for the batches
that already succeeded and a demo replays exactly. `DELIBERATION_REPLAY_ONLY=1` serves
only from cache and counts the misses rather than calling.

The numbers printed at the end are the ones that matter and the ones easiest to overstate:
a rate is meaningless without the denominator it was computed over, and a resident nobody
asked is unknown rather than unaffected.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _common import refuse_if_running

from app.cohort import select_cohort
from app.engine import DEFAULT_TOWN, study_area_for_town
from app.population import build_population
from app.scenario import POPULATION_SIZE
from app.services.llm import TELEMETRY, build_deliberation_client
from app.social import build_social_graph
from app.world import build_world

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "runs"

#: Bedrock rates, USD per million tokens, by model. For reporting only; the bill is AWS's.
#:
#: These were a single hardcoded pair for Claude 3 Haiku, so a Sonnet run was costed at
#: Haiku prices and reported twelve times cheaper than it was -- $1.00 against a real
#: $12. A cost figure that silently assumes the wrong model is worse than no cost figure,
#: because it gets believed and acted on.
PRICES = {
    "anthropic.claude-3-haiku-20240307-v1:0": (0.25, 1.25),
    "anthropic.claude-3-5-sonnet-20240620-v1:0": (3.00, 15.00),
}
DEFAULT_PRICE = (3.00, 15.00)          # assume expensive when unknown, never cheap


def price_for(model: str) -> tuple[float, float]:
    return PRICES.get(model, DEFAULT_PRICE)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--town", default=DEFAULT_TOWN)
    ap.add_argument("--size", type=int, default=POPULATION_SIZE)
    ap.add_argument("--limit", type=int, default=0, help="cap the cohort, for a cheap look")
    ap.add_argument("--allow-concurrent", action="store_true")
    args = ap.parse_args()

    if not args.allow_concurrent:
        refused = refuse_if_running("run_deliberation", "deliberation")
        if refused:
            return refused

    from app.deliberate import deliberate

    geo, closed = study_area_for_town(args.town)
    pop = build_population(geo, args.size)
    world = build_world(pop, geo, closed, town=args.town)
    social = build_social_graph(pop)
    cohort = select_cohort(pop, world, social)
    ids = cohort.ids[:args.limit] if args.limit else cohort.ids

    policy = (
        f"Close bus stops {' and '.join(sorted(closed))} and let the feeder service run "
        f"non-stop between them. No extra buses, no budget increase."
    )
    print(f"town {args.town}: {len(pop.personas)} residents, cohort {len(cohort.ids)}"
          f"{f', capped to {len(ids)}' if args.limit else ''}")
    print(f"policy: {policy}\n")

    seen = [0]

    def on_voice(voice, rnd):
        seen[0] += 1
        if seen[0] % 25 == 0:
            print(f"  {seen[0]} turns recorded (round {rnd})", flush=True)

    before = len(TELEMETRY.calls)
    started = time.monotonic()
    run = deliberate(pop, world, policy, build_deliberation_client(),
                     social=social, cohort_ids=ids, on_voice=on_voice)
    calls = TELEMETRY.calls[before:]
    tin = sum(c.input_tokens for c in calls)
    tout = sum(c.output_tokens for c in calls)
    usd_in, usd_out = price_for(run.model)
    cost = tin / 1e6 * usd_in + tout / 1e6 * usd_out

    cov = run.coverage()
    print("\n--- coverage: what this run can and cannot speak for ---")
    for k in ("population", "cohort", "evaluated", "unevaluated", "ungrounded",
              "unexplained_moves"):
        print(f"  {k:18} {cov[k]}")
    print(f"  {'strata':18} {cov['strata']}")

    print("\n--- what it cost, and what it dropped ---")
    print(f"  model            {run.model}")
    print(f"  calls            {run.calls}   cached {run.cached}")
    print(f"  tokens           {tin} in / {tout} out")
    print(f"  cost             ${cost:.3f}   (at ${usd_in}/M in, ${usd_out}/M out)")
    print(f"  seconds          {run.seconds}")
    print(f"  turns rejected   {run.rejected}   (cited a fact they were not given)")
    print(f"  failed batches   {run.failed_batches}")
    print(f"  skipped batches  {run.skipped_batches}   (replay-only cache miss)")
    print(f"  missing voices   {run.missing_voices}")
    if run.failures:
        print(f"\n  first failures:")
        for f in run.failures[:5]:
            print(f"    {f[:160]}")

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"deliberation-{args.town}-{len(ids)}.json"
    path.write_text(json.dumps({
        "town": args.town, "policy": policy, "model": run.model,
        "coverage": cov, "calls": run.calls, "cached": run.cached,
        "rejected": run.rejected, "failed_batches": run.failed_batches,
        "skipped_batches": run.skipped_batches, "missing_voices": run.missing_voices,
        "seconds": run.seconds, "cost_usd": round(cost, 4),
        "participation": run.participation,
        "voices": [v.model_dump() for v in run.ordered()],
    }, indent=1), encoding="utf-8")
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
