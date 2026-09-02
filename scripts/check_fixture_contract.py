"""Assert the fixture satisfies every field the frontend reads.

This is not a render test. It proves the data contract holds, which is where a
fixture-backed UI actually breaks: a missing key throws at runtime and the screen
goes blank with a green build behind it.

    python scripts/check_fixture_contract.py
"""
from __future__ import annotations

import json
import pathlib
import sys

FIX = pathlib.Path(__file__).resolve().parent.parent / "data" / "fixtures" / "demo_run.json"
fails: list[str] = []
checks = 0


def need(cond: bool, what: str) -> None:
    global checks
    checks += 1
    if not cond:
        fails.append(what)


d = json.loads(FIX.read_text(encoding="utf-8"))

# ---- Hero
need(isinstance(d.get("personas"), list) and d["personas"], "Hero: personas[]")
need(d["metrics"]["overall"]["severe_harm_count"] >= 0, "Hero: severe_harm_count")
need(any(o["second_order"] for o in d["outcomes"]), "Hero: at least one second-order victim")
need(all(len(p["xy"]) == 2 for p in d["personas"]), "Hero/Field: every persona has xy")

# ---- PolicyInput
p = d["policy"]
need(bool(p.get("text")), "PolicyInput: policy.text")
need(len(p.get("reading", [])) >= 3, "PolicyInput: reading steps")
need(any(s["assumed"] for s in p["reading"]), "PolicyInput: at least one flagged assumption")
need(len(p.get("resolved_entities", [])) >= 1, "PolicyInput: resolved_entities")
need(isinstance(p["modifications"]["remove_stops"], list), "PolicyInput: remove_stops")

# ---- Simulation: the trace must actually chain
by_id = {e["event_id"]: e for e in d["events"]}
leaf = next((e for e in d["events"] if e["kind"] == "OBLIGATION_MISSED"), None)
need(leaf is not None, "Simulation: a OBLIGATION_MISSED leaf exists")
if leaf:
    chain, cur, guard = [], leaf, set()
    while cur and cur["event_id"] not in guard:
        guard.add(cur["event_id"])
        chain.append(cur)
        cur = by_id.get(cur["cause"]) if cur["cause"] else None
    need(len(chain) >= 3, f"Simulation: chain depth >= 3 (got {len(chain)})")
    kinds = [e["kind"] for e in reversed(chain)]
    need("DEPENDENCY_ABSORBED" in kinds, "Simulation: chain passes through the carer")
    need(all(e["cause"] is None or e["cause"] in by_id for e in d["events"]),
         "Simulation: every cause id resolves")

# ---- ImpactAudit
sub = d["metrics"]["subgroup"]
for band in ["18-34", "35-54", "55-64", "65-74", "75+"]:
    need(band in sub["age_band"], f"ImpactAudit: age band {band}")
need("True" in sub["is_caregiver"] and "False" in sub["is_caregiver"],
     "ImpactAudit: is_caregiver True/False keys")
need(sub["is_caregiver"]["True"]["severe_harm_rate"]
     > sub["is_caregiver"]["False"]["severe_harm_rate"],
     "ImpactAudit: carers worse off than non-carers (the whole finding)")
need(all(m["n"] > 0 for m in sub["age_band"].values()), "ImpactAudit: every cohort has n")
need(isinstance(d["metrics"]["subgroup_disparity_pp"], (int, float)),
     "ImpactAudit: subgroup_disparity_pp")

# ---- InterventionLab
alts = d["interventions"]
valid = [a for a in alts if a["valid"]]
need(len(valid) >= 2, "InterventionLab: at least two simulated alternatives")
need(all(a["metrics"] is not None for a in valid), "InterventionLab: valid alts carry metrics")
need(all(a["metrics"] is None for a in alts if not a["valid"]),
     "InterventionLab: rejected alts are NOT scored")
need(all(a["validation_errors"] for a in alts if not a["valid"]),
     "InterventionLab: every rejection states why")
need(any((a.get("newly_harmed_elsewhere") or 0) > 0 for a in valid),
     "InterventionLab: one alt moves harm rather than removing it")
need(all(a["metrics"]["severe_harm_count"] <= d["metrics"]["overall"]["severe_harm_count"]
         for a in valid), "InterventionLab: no alt is worse than baseline on severe harm")

# ---- Calibration
c = d["consultation"]
need(c["response_count"] == len(c["responses"]), "Calibration: response_count matches")
need(set(c["pcs"]["components"]) >= {"support", "perceived_fairness",
                                     "clarity_of_explanation", "confidence_in_delivery"},
     "Calibration: all four PCS components")
need(c["is_representative"] is False, "Calibration: representativeness disclaimed")
need(any(r["flagged"] for r in c["calibration"]), "Calibration: one cohort flagged")
need(all(r["n"] >= 30 for r in c["calibration"] if r["flagged"]),
     "Calibration: nothing flagged on a thin cohort")
need(any(r["n"] < 30 for r in c["calibration"]),
     "Calibration: a thin cohort exists to show the guard working")
ov = next(r for r in c["calibration"] if r["cohort_axis"] == "overall")
need(abs(ov["signed_error"]) < 10,
     "Calibration: overall stays under the flag line (the 'looked fine' story)")
need(all(r["persona_id"] in {x["persona_id"] for x in d["personas"]} for r in c["responses"]),
     "Calibration: every response links to a real persona")
need(all(r["is_seeded"] for r in c["responses"]), "Calibration: seeded responses labelled")
need(c["proposed_adjustment"]["status"] == "awaiting_human_approval",
     "Calibration: adjustment is not auto-applied")

# ---- Consultation
need(any(r["comment"] for r in c["responses"]), "Consultation: a comment to surface")
need(bool(c["discovered_constraint"]["note"]), "Consultation: discovered constraint")

# ---- provenance
need(d["is_synthetic"] is True, "Provenance: run marked synthetic")
need(bool(d.get("study_area")), "Provenance: study_area")

print(f"{checks - len(fails)}/{checks} contract checks passed")
if fails:
    print("\nFAILED:")
    for f in fails:
        print(f"  - {f}")
    sys.exit(1)
print("every field the frontend reads is present and internally consistent")
