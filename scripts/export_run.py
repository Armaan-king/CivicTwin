"""Write a finished deliberation out as something a person can read. P5 · LOCKED.

    python scripts/export_run.py

Two artefacts, because they answer different questions:

    data/runs/deliberation.json   the record. Every resident, every turn, every citation,
                                  the coverage counts and the metrics. This is what belongs
                                  in the annex of whatever document a decision is written into.
    data/runs/deliberation.md     the reading. The same run as prose, ordered by who moved most.

A policymaker's question is "what did this do to people", and a per-person account answers
it in a way a metric cannot -- which is why P5 requires the export rather than leaving the
deliberation as a log.

**This costs nothing after a completed run.** Every batch is cached on a content hash (P4),
so a replay is served from disk: same residents, same turns, no model calls. If the cache
is cold it will call the model instead, and says so.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend"))

import app.config  # noqa: E402  loads the root .env
from app.aggregate import aggregate, support_comparison  # noqa: E402
from app.cohort import MIN_CELL, reportable_cells  # noqa: E402
from app.deliberate import deliberate  # noqa: E402
from app.engine import study_area  # noqa: E402
from app.metrics import disparity_pp, metrics_for, subgroup_metrics  # noqa: E402
from app.population import build_population  # noqa: E402
from app.remedies import cluster_remedies, collect_remedies, resident_candidates  # noqa: E402
from app.services.llm import build_deliberation_client  # noqa: E402
from app.social import build_social_graph  # noqa: E402
from app.world import build_world  # noqa: E402

POLICY = ("Close bus stops 54241 and 54248 on Ang Mo Kio Ave 3 and let service 265 run "
          "non-stop between them. No extra buses, no budget increase.")


def markdown(run, agg, pop, metrics, remedies, policy_text) -> str:
    cov = run.coverage()
    by_id = pop.by_id()
    out: list[str] = []
    w = out.append

    w("# CivicTwin - resident deliberation")
    w("")
    w("**The population is synthetic.** It is generated from Singapore open transport data "
      "and demographic distributions. No resident here is a real person.")
    w("")
    w("## The policy")
    w("")
    w("> " + policy_text)
    w("")
    w("## What this run can and cannot speak for")
    w("")
    strata = ", ".join(f"{k} {v}" for k, v in cov["strata"].items())
    w(f"- **{cov['population']}** residents in the study area")
    w(f"- **{cov['cohort']}** asked to reason ({strata})")
    w(f"- **{cov['evaluated']}** produced an account that survived the grounding guard")
    w(f"- **{cov['unevaluated']}** were never asked. They are *unknown*, not unaffected.")
    w(f"- **{cov['ungrounded']}** were asked and said nothing that could be checked")
    w(f"- {run.rejected} turns rejected; {cov.get('unexplained_moves', 0)} changed course "
      "without saying why (kept, and counted)")
    w("")
    w(f"Model `{run.model}` - {run.calls} calls, {run.cached} from cache, {run.seconds:.0f}s")
    w("")
    w("## What they decided")
    w("")
    w("| metric | value |")
    w("|---|---|")
    for key, value in metrics.items():
        w(f"| `{key}` | {value} |")
    w("")
    w(f"Every rate above is over **{metrics['n']} evaluated residents**, "
      f"not over {cov['population']}.")
    w("")

    if remedies.mapped or remedies.unmappable:
        w("## What residents said would help")
        w("")
        for c in remedies.mapped:
            w(f"- **{c.count}** asked for {c.label} -> `{c.action_type}`")
            for ex in c.examples[:2]:
                w(f'  - "{ex}"')
        if remedies.unmappable:
            w("")
            w("Asked for something this model cannot represent, which is a finding rather "
              "than a gap to hide:")
            w("")
            for u in remedies.unmappable:
                w(f"- **{u.count}** - {u.label}")
                for ex in u.examples[:2]:
                    w(f'  - "{ex}"')
        w("")

    w("## The residents")
    w("")
    for v in run.ordered():
        if not v.turns:
            continue
        p = by_id.get(v.persona_id)
        if p is not None:
            mobility = p.mobility_level if p.mobility_level != "none" else "no"
            who = f"{p.age_band}, {p.employment_status}, {mobility} difficulty walking"
        else:
            who = ""
        final = v.turns[-1]
        w(f"### {v.name} - `{v.persona_id}`")
        w("")
        w(f"*{who}*")
        w("")
        w(f"**{final.response}**, severity **{final.severity}**, "
          f"support {v.turns[0].position:.2f} -> {final.position:.2f}")
        w("")
        for t in v.turns:
            w(f"- **Round {t.round}** - {t.reasoning}")
            if t.changed_because:
                w(f"  - *changed because:* {t.changed_because}")
            if t.influenced_by:
                w(f"  - *moved by:* `{t.influenced_by}`")
            if t.absorbing_for:
                w(f"  - *taking on the journey of:* `{t.absorbing_for}`")
            if t.remedy:
                w(f'  - *what would help:* "{t.remedy}"')
            cites = ", ".join(f"`{g}`" for g in t.grounded_in) or "-"
            w(f"  - *grounded in:* {cites}")
        w("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/runs")
    ap.add_argument("--name", default="deliberation")
    ap.add_argument("--policy", default=POLICY)
    args = ap.parse_args()

    geo, closed, _ = study_area()
    pop = build_population(geo)
    world = build_world(pop, geo, closed)
    social = build_social_graph(pop)

    print("replaying the deliberation (served from cache where available)...", flush=True)
    run = deliberate(pop, world, args.policy, build_deliberation_client(), social=social)
    if run.calls:
        print(f"note: {run.calls} batches were NOT cached and called the model", flush=True)

    agg = aggregate(run, pop)
    outcomes = list(agg.outcomes.values())
    metrics = metrics_for(outcomes)
    sub = subgroup_metrics(pop, agg.outcomes)
    cells = reportable_cells(pop, list(agg.outcomes))
    remedies = cluster_remedies(collect_remedies(run))

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "policy": args.policy,
        "model": run.model,
        "is_synthetic": True,
        "coverage": run.coverage(),
        "cost": {"calls": run.calls, "cached": run.cached, "seconds": run.seconds,
                 "rejected_turns": run.rejected, "failed_batches": run.failed_batches},
        "metrics": {
            "overall": metrics,
            "subgroup": sub,
            "subgroup_disparity_pp": disparity_pp(sub),
            "min_cell": MIN_CELL,
            "insufficient_cells": {a: [k for k, n in c.items() if n < MIN_CELL]
                                   for a, c in cells.items()},
        },
        "support_comparison": [
            r for axis in ("age_band", "mobility_level", "is_caregiver")
            for r in support_comparison(pop, agg.declared_support, agg.outcomes, axis)
        ],
        "second_order": [{"carer": c, "for": d} for c, d in sorted(agg.absorbing.items())],
        "remedies": {
            "asked": remedies.asked(), "silent": remedies.silent,
            "mapped": [{"action_type": c.action_type, "label": c.label, "count": c.count,
                        "residents": c.residents, "examples": c.examples}
                       for c in remedies.mapped],
            "unmappable": [{"label": u.label, "count": u.count, "residents": u.residents,
                            "examples": u.examples} for u in remedies.unmappable],
        },
        "candidates": [
            {"intervention_id": c.intervention_id, "kind": c.kind, "name": c.name,
             "params": c.params, "rationale": c.rationale,
             "estimated_cost_index": c.estimated_cost_index,
             "metrics": None, "evaluated": False}
            for c in resident_candidates(remedies, set(closed))
        ],
        "voices": [v.model_dump() for v in run.ordered()],
    }

    j = out_dir / f"{args.name}.json"
    m = out_dir / f"{args.name}.md"
    j.write_text(json.dumps(record, indent=1), encoding="utf-8")
    m.write_text(markdown(run, agg, pop, metrics, remedies, args.policy), encoding="utf-8")

    cov = run.coverage()
    print(f"\nwrote {j} ({j.stat().st_size // 1024} KB)")
    print(f"wrote {m} ({m.stat().st_size // 1024} KB)")
    print(f"\n{cov['evaluated']} residents evaluated of {cov['population']}; "
          f"{cov['unevaluated']} unevaluated (unknown, not unaffected)")
    print("severity:", dict(Counter(t.severity for v in run.voices.values()
                                    for t in v.turns)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
