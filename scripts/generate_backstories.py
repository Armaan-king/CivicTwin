"""Generate the per-town backstory store. One bulk spend, then free forever.

    python scripts/generate_backstories.py --dry-run          # cost, and one sample prompt
    python scripts/generate_backstories.py --cohort           # just the ~360 who deliberate
    python scripts/generate_backstories.py                    # the whole town

`--dry-run` calls nothing. It builds the real prompts, prints one of them in full and
estimates the spend, because a project with thirty dollars of credit should be able to see
the bill before it agrees to it.

The store is written per town to `data/personas/<town>.json` after every batch, so an
interrupted run resumes where it stopped rather than buying the first two thirds again.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _common import refuse_if_running

from app.backstory import (BATCH_SIZE, SYSTEM, _prompt, build_backstories, load,
                           path_for)
from app.engine import DEFAULT_TOWN, study_area_for_town, study_area
from app.graph import TransitNetwork
from app.population import build_population
from app.scenario import POPULATION_SIZE
from app.services.llm import build_client

#: Rough Bedrock Haiku 4.5 rates, USD per million tokens. Only used to print an estimate
#: before spending; the real bill is the console's. Override if your rates differ.
USD_IN, USD_OUT = 1.00, 5.00

#: Tokens per character, English prose with JSON. Crude on purpose -- this is a budget
#: sanity check, not accounting.
CHARS_PER_TOKEN = 4


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--town", default=DEFAULT_TOWN)
    ap.add_argument("--size", type=int, default=POPULATION_SIZE)
    ap.add_argument("--cohort", action="store_true",
                    help="only the residents who actually deliberate")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap the number generated, for a cheap first look")
    ap.add_argument("--dry-run", action="store_true",
                    help="print one prompt and the estimated cost; call nothing")
    ap.add_argument("--review-only", action="store_true",
                    help="rewrite the review file from the existing store; call nothing")
    ap.add_argument("--allow-concurrent", action="store_true",
                    help="start even if another generation run is already going")
    args = ap.parse_args()

    if not (args.dry_run or args.review_only):
        if not args.allow_concurrent:
            refused = refuse_if_running("generate_backstories", "generation run")
            if refused:
                return refused
        missing = preflight()
        if missing:
            print("\n".join([
                "",
                f"No credentials: {missing}",
                "",
                "Fill one of these in the project root .env and run again:",
                "  A. AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY"
                "  (+ AWS_SESSION_TOKEN if temporary)",
                "  B. AWS_BEARER_TOKEN_BEDROCK   (a Bedrock API key)",
                "",
                "Nothing was called and nothing was spent.",
            ]))
            return 2

    geo, closed = study_area_for_town(args.town)
    pop = build_population(geo, args.size)
    print(f"town {args.town}: {len(pop.personas)} residents, "
          f"{len(pop.care_edges)} care relationships")

    only = None
    if args.cohort:
        from app.cohort import select_cohort
        from app.social import build_social_graph
        from app.world import build_world
        world = build_world(pop, geo, closed)
        cohort = select_cohort(pop, world, build_social_graph(pop))
        only = cohort.ids
        print(f"cohort: {len(only)} ({cohort.strata()})")
    if args.limit:
        base = only if only is not None else [p.persona_id for p in pop.personas]
        only = base[:args.limit]
        print(f"capped to {len(only)}")

    if args.review_only:
        n = write_review(args.town, pop, geo)
        print(f"review written for {n} residents: {review_path(args.town)}")
        return 0

    have = load(args.town)
    keep = set(only) if only is not None else None
    todo = [p for p in pop.personas
            if (keep is None or p.persona_id in keep) and p.persona_id not in have]
    print(f"{len(have)} already written, {len(todo)} to generate")
    if not todo:
        print(f"nothing to do. store: {path_for(args.town)}")
        return 0

    if args.dry_run:
        return dry_run(todo, geo, pop, args.town)

    seen = [0]

    def progress(done: int, total: int, error: str | None) -> None:
        if done < 0:                     # a retry notice, not a completed batch
            print(f"    {error}", flush=True)
            return
        seen[0] += 1
        note = f"  FAILED: {error}" if error else ""
        # `done` is the whole store and `total` was the todo count -- different
        # denominators, so a resumed run printed "740/119". Report both plainly.
        print(f"  batch {seen[0]}: store {done}, {total} queued this run{note}", flush=True)

    build_backstories(pop, geo, args.town, build_client(temperature=0.7),
                      only=only, on_batch=progress)
    print(f"done. store: {path_for(args.town)}")
    from app.backstory import write_meta
    m = write_meta(args.town, args.size)
    print(f"coverage: {m['generated']}/{m['population']} residents "
          f"({m['covers']}){' - demo store' if m['is_demo_store'] else ''}")
    n = write_review(args.town, pop, geo)
    print(f"review for {n} residents: {review_path(args.town)}")
    return 0


def preflight() -> str:
    """What is missing, in one line, before anything is charged for."""
    import os
    if os.getenv("AWS_BEARER_TOKEN_BEDROCK", "").strip():
        return ""
    have_id = bool(os.getenv("AWS_ACCESS_KEY_ID", "").strip())
    have_secret = bool(os.getenv("AWS_SECRET_ACCESS_KEY", "").strip())
    if have_id and have_secret:
        return ""
    gaps = [n for n, v in (("AWS_ACCESS_KEY_ID", have_id),
                           ("AWS_SECRET_ACCESS_KEY", have_secret)) if not v]
    return ", ".join(gaps) + " are empty, and no AWS_BEARER_TOKEN_BEDROCK is set"


def review_path(town: str) -> pathlib.Path:
    return path_for(town).with_name(f"{town}-review.md")


def write_review(town: str, pop, geo) -> int:
    """The generated life beside the record it was generated from.

    Side by side on purpose. The failure mode of this whole approach is a biography that
    reads beautifully and contradicts the record it came from -- a retiree given a job, a
    resident with no car who drives -- and that is invisible unless the source is next to
    it. A reviewer should be able to catch one without opening a second file.
    """
    from app.backstory import load
    from app.graph import TransitNetwork
    from app.backstory import _brief

    have = load(town)
    if not have:
        return 0
    by_id = pop.by_id()
    net = TransitNetwork(geo)

    out = [
        f"# Backstory review - {town}",
        "",
        "**These residents are synthetic.** They are generated from Singapore open "
        "transport data and demographic distributions. No resident here is a real person.",
        "",
        f"{len(have)} residents. Each generated life is shown beside the record it was "
        "generated from, so a biography that contradicts its own source is visible "
        "without opening another file.",
        "",
        "What to look for: a retiree given a job, a household with no car who drives, a "
        "resident whose years in the estate exceed their age, a stop or service that is "
        "not in their record, or two neighbours who read as the same person.",
        "",
        "---",
        "",
    ]
    for pid in sorted(have):
        b, p = have[pid], by_id.get(pid)
        if p is None:
            continue
        out += [
            f"## {b.name} - {b.occupation}  `{pid}`",
            "",
            f"*{b.voice}* - {b.years_in_estate} years on {p.home_subzone}",
            "",
            f"**Routine.** {b.routine}",
            "",
            f"**Depends on.** {b.depends_on}",
            "",
            "<details><summary>the record this was generated from</summary>",
            "",
            "```",
            _brief(p, geo, net, pop),
            "```",
            "</details>",
            "",
            "---",
            "",
        ]
    review_path(town).write_text("\n".join(out), encoding="utf-8")
    return len(have)


def dry_run(todo, geo, pop, town: str) -> int:
    """What this would cost, and what one call would actually say."""
    net = TransitNetwork(geo)
    batches = [todo[i:i + BATCH_SIZE] for i in range(0, len(todo), BATCH_SIZE)]
    sample = _prompt(batches[0], geo, net, pop, town)

    # every call carries the system prompt and the JSON schema alongside its residents
    in_chars = sum(len(_prompt(b, geo, net, pop, town)) for b in batches)
    in_chars += len(SYSTEM) * len(batches)
    in_tok = in_chars / CHARS_PER_TOKEN
    # ~180 tokens of biography per resident, plus JSON scaffolding
    out_tok = len(todo) * 210

    cost = in_tok / 1e6 * USD_IN + out_tok / 1e6 * USD_OUT

    print("\n" + "=" * 70)
    print("SAMPLE PROMPT (batch 1 of %d)" % len(batches))
    print("=" * 70)
    print(sample[:3000] + ("\n... [truncated]" if len(sample) > 3000 else ""))
    print("=" * 70)
    print(f"\n{len(batches)} calls, {len(todo)} residents")
    print(f"  input  ~{in_tok/1000:>8.1f}k tokens")
    print(f"  output ~{out_tok/1000:>8.1f}k tokens (estimated)")
    print(f"  cost   ~${cost:>8.2f}  at ${USD_IN}/M in, ${USD_OUT}/M out")
    print("\nNothing was called. Drop --dry-run to generate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
