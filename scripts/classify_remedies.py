"""Classify what residents asked for, and cache it per town.

    python scripts/classify_remedies.py --town ang-mo-kio

Reads the recorded deliberation, pulls every remedy a resident offered, classifies each
onto the fixed five-action space through the model, and writes the result beside the run.
The API loads that cache; nothing is classified at request time.

The regex table in `remedies.py` still runs, and its verdict is stored alongside. Not as
a fallback -- as a second opinion. Where two independent classifiers agree that is
evidence, and where they disagree is exactly what a person should look at.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from app.deliberate import recorded_path
from app.engine import DEFAULT_TOWN
from app.remedies import MAPPING, UNMAPPABLE_KINDS, _match, classify_remedies
from app.services.llm import TELEMETRY, build_client

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "runs"
PRICES = {"anthropic.claude-3-5-sonnet-20240620-v1:0": (3.00, 15.00),
          "anthropic.claude-3-haiku-20240307-v1:0": (0.25, 1.25)}


def remedies_from_run(town: str) -> dict[str, str]:
    path = recorded_path(town)
    if not path.exists():
        raise SystemExit(f"no recorded deliberation for {town}: {path}")
    d = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for v in d["voices"]:
        for t in v["turns"]:
            if t.get("remedy"):
                out[v["persona_id"]] = t["remedy"]
    return out


def regex_verdict(text: str) -> tuple[str | None, str | None]:
    hit = _match(text, MAPPING)
    if hit:
        return hit[0], None
    un = _match(text, UNMAPPABLE_KINDS)
    return (None, un[0]) if un else (None, None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--town", default=DEFAULT_TOWN)
    ap.add_argument("--dry-run", action="store_true", help="count and cost, call nothing")
    args = ap.parse_args()

    remedies = remedies_from_run(args.town)
    print(f"{args.town}: {len(remedies)} residents offered a remedy")

    reg = {pid: regex_verdict(t) for pid, t in remedies.items()}
    reg_mapped = sum(1 for a, _ in reg.values() if a)
    reg_unmap = sum(1 for a, u in reg.values() if not a and u)
    reg_miss = len(reg) - reg_mapped - reg_unmap
    print(f"  regex: {reg_mapped} mapped, {reg_unmap} unmappable, "
          f"{reg_miss} matched nothing ({reg_miss/max(len(reg),1):.0%})")

    if args.dry_run:
        calls = (len(remedies) + 19) // 20
        print(f"\n  would make ~{calls} calls. Nothing was called.")
        return 0

    client = build_client(temperature=0.0, role="deliberation")
    before = len(TELEMETRY.calls)
    result = classify_remedies(remedies, client, on_note=lambda m: print(f"  {m}", flush=True))
    calls = TELEMETRY.calls[before:]
    tin = sum(c.input_tokens for c in calls)
    tout = sum(c.output_tokens for c in calls)
    pin, pout = PRICES.get(client.provider_name, (3.0, 15.0))
    cost = tin / 1e6 * pin + tout / 1e6 * pout

    llm_mapped = sum(1 for c in result.values() if c.action_type)
    llm_unmap = len(result) - llm_mapped
    agree = sum(1 for pid, c in result.items() if c.action_type == reg[pid][0])
    print(f"\n  model: {llm_mapped} mapped, {llm_unmap} unmappable")
    print(f"  agreement with regex: {agree}/{len(result)} = {agree/max(len(result),1):.0%}")
    print(f"  recovered by the model but missed by regex: "
          f"{sum(1 for pid, c in result.items() if c.action_type and not reg[pid][0])}")
    print(f"  cost: ${cost:.3f} over {len(calls)} calls")

    by_action = collections.Counter(c.action_type or "(cannot express)"
                                    for c in result.values())
    print("\n  what residents asked for:")
    for action, n in by_action.most_common():
        print(f"    {action:<22} {n}")

    path = OUT / f"remedies-{args.town}.json"
    path.write_text(json.dumps({
        "town": args.town,
        "model": client.provider_name,
        "residents": len(remedies),
        "agreement_with_regex": round(agree / max(len(result), 1), 3),
        "cost_usd": round(cost, 4),
        # both verdicts, per resident, so a disagreement is inspectable rather than a rate
        "classifications": {
            pid: {"remedy": remedies[pid],
                  "model_action": c.action_type,
                  "model_reason": c.unmappable_reason,
                  "model_quote": c.quote,
                  "regex_action": reg[pid][0],
                  "regex_unmappable": reg[pid][1],
                  "agree": c.action_type == reg[pid][0]}
            for pid, c in sorted(result.items())
        },
    }, indent=1), encoding="utf-8")
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
