"""Merge two deliberation runs into one, recording which model spoke for whom.

    python scripts/merge_deliberations.py \
        --base data/runs/deliberation-ang-mo-kio-818.json \
        --overlay data/runs/deliberation-ang-mo-kio-218.json

Why this exists rather than one run at one quality: the account sustains roughly 2-3k
Sonnet tokens a minute, which is fine for the short backstory prompts and is not fine for
the deliberation, whose prompts are three times larger. A full 818-resident Sonnet
deliberation needs about nine and a half hours of quota; the same run on Claude 3 Haiku
took twenty-one minutes.

So the residents are split by what they contribute. The 43 whose own stop closes and the
175 tied to one of them by household or care are where every finding lives, and they get
the better model. The 600-strong stratified comparison group exists to give those findings
a denominator -- its job is to be counted, not quoted -- and Haiku's turns do that job
exactly as well.

**Each voice records which model produced it, and the merged file reports the split.**
Two models in one dataset is defensible; two models in one dataset that reads as one is
not, and any screen quoting a resident should be able to say who wrote them.
"""
from __future__ import annotations

import argparse
import json
import pathlib


def load(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def repeat_rate(voices: list[dict]) -> float:
    """Share of turns after the first that are byte-identical to the one before."""
    exact = total = 0
    for v in voices:
        for i, t in enumerate(v["turns"][1:], 1):
            total += 1
            if t["reasoning"] == v["turns"][i - 1]["reasoning"]:
                exact += 1
    return exact / total if total else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="the wider, cheaper run")
    ap.add_argument("--overlay", required=True, help="the better run, which wins")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base, overlay = load(args.base), load(args.overlay)
    if base["town"] != overlay["town"]:
        raise SystemExit(f"different towns: {base['town']} vs {overlay['town']}")

    by_id = {v["persona_id"]: (v, base["model"]) for v in base["voices"]}
    replaced = kept = 0
    for v in overlay["voices"]:
        pid = v["persona_id"]
        prior = by_id.get(pid)
        # **Only overwrite with an at-least-as-complete account.**
        #
        # A better model is not a better answer if it stopped early. The overlay run died
        # partway, so many of its residents hold only a round-0 turn -- the view they had
        # *before the policy landed*, where severity is "none" by construction. Blindly
        # preferring the newer model replaced finished four-round accounts with those
        # openings and silently deleted the findings: severe harm fell from 103 to 80 and
        # absorbed journeys from 26 to 21, with nothing in the output indicating that
        # twenty-three harmed residents had just been overwritten by their own earlier
        # selves.
        #
        # Completeness is the last round reached, then turn count. A truncated overlay
        # voice is discarded and the base account stands.
        def reach(voice):
            return (max((t["round"] for t in voice["turns"]), default=-1),
                    len(voice["turns"]))
        if prior is not None and reach(v) < reach(prior[0]):
            kept += 1
            continue
        if prior is not None:
            replaced += 1
        by_id[pid] = (v, overlay["model"])

    merged = []
    for v, model in by_id.values():
        v = dict(v)
        v["model"] = model          # per voice, so a screen can attribute a quote
        merged.append(v)
    merged.sort(key=lambda v: v["persona_id"])

    from_overlay = [v for v in merged if v["model"] == overlay["model"]]
    from_base = [v for v in merged if v["model"] == base["model"]]

    out = {
        "town": base["town"],
        "policy": base["policy"],
        "merged_from": {
            "base": {"file": args.base, "model": base["model"],
                     "voices": len(from_base),
                     "exact_repeat_rate": round(repeat_rate(from_base), 3)},
            "overlay": {"file": args.overlay, "model": overlay["model"],
                        "voices": len(from_overlay),
                        "exact_repeat_rate": round(repeat_rate(from_overlay), 3)},
        },
        "why_split": (
            "The account sustains ~2-3k Sonnet tokens/min, so a full-cohort Sonnet "
            "deliberation needs ~9.5 hours. The affected residents and their household "
            "and care ties -- where every finding lives -- were run on Sonnet. The "
            "stratified comparison group, whose job is to supply denominators rather "
            "than quotes, kept its Haiku turns."
        ),
        "overlay_voices_discarded_as_truncated": kept,
        "coverage": dict(base["coverage"], evaluated=len(merged)),
        "cost_usd": round(base.get("cost_usd", 0) + overlay.get("cost_usd", 0), 4),
        "voices": merged,
    }
    path = pathlib.Path(args.out or
                        pathlib.Path(args.base).with_name(
                            f"deliberation-{base['town']}-merged.json"))
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"merged {len(merged)} voices -> {path}")
    print(f"  {overlay['model'].split('.')[-1][:24]:26} {len(from_overlay):>4} voices  "
          f"repeats {repeat_rate(from_overlay):.0%}   ({replaced} replaced)")
    if kept:
        print(f"  {'':26} {kept:>4} overlay voices discarded as less complete than the base")
    print(f"  {base['model'].split('.')[-1][:24]:26} {len(from_base):>4} voices  "
          f"repeats {repeat_rate(from_base):.0%}")
    print(f"  combined cost ${out['cost_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
