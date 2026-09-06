"""The whole cohort, for real. 467 residents: 44 affected, 183 tied, 240 comparison."""
import json, time, app.config
from app.services.llm import build_deliberation_client
from app.engine import study_area
from app.population import build_population
from app.world import build_world
from app.social import build_social_graph
from app.deliberate import deliberate
from app.aggregate import aggregate, support_comparison
from app.metrics import metrics_for, subgroup_metrics, disparity_pp
from app.cohort import MIN_CELL, reportable_cells
from app.remedies import cluster_remedies, collect_remedies
from collections import Counter

TEXT = ("Close bus stops 54241 and 54248 on Ang Mo Kio Ave 3 and let service 265 run "
        "non-stop between them. No extra buses, no budget increase.")
geo, closed, _ = study_area()
pop = build_population(geo); world = build_world(pop, geo, closed)
social = build_social_graph(pop)
print(f"START population={len(pop.personas)} closed={sorted(closed)}", flush=True)

seen = [0]
def progress(voice, rnd):
    seen[0] += 1
    if seen[0] % 25 == 0:
        print(f"PROGRESS {seen[0]} turns, round {rnd}, {time.strftime('%H:%M:%S')}", flush=True)

d = deliberate(pop, world, TEXT, build_deliberation_client(), social=social, on_voice=progress)

print(f"RESULT calls={d.calls} cached={d.cached} rejected={d.rejected} "
      f"unexplained={d.unexplained_moves} failed={d.failed_batches} {d.seconds:.0f}s", flush=True)
print("COVERAGE " + json.dumps(d.coverage()), flush=True)
print("PARTICIPATION " + json.dumps({str(k): v for k, v in d.participation.items()}), flush=True)

agg = aggregate(d, pop)
outcomes = list(agg.outcomes.values())
sub = subgroup_metrics(pop, agg.outcomes)
print("METRICS " + json.dumps(metrics_for(outcomes)), flush=True)
print(f"DISPARITY {disparity_pp(sub)} pp", flush=True)
cells = reportable_cells(pop, list(agg.outcomes))
print("INSUFFICIENT " + json.dumps({a: [k for k, n in c.items() if n < MIN_CELL]
                                    for a, c in cells.items()}), flush=True)
print("SEVERITY " + json.dumps(dict(Counter(
    t.severity for v in d.voices.values() for t in v.turns))), flush=True)
print("RESPONSE " + json.dumps(dict(Counter(
    t.response for v in d.voices.values() for t in v.turns))), flush=True)
print("SUPPORT " + json.dumps(support_comparison(pop, agg.declared_support, agg.outcomes)), flush=True)
rep = cluster_remedies(collect_remedies(d))
print(f"REMEDIES asked={rep.asked()} silent={rep.silent} "
      f"mapped={[(c.action_type, c.count) for c in rep.mapped]} "
      f"unmappable={[(u.label, u.count) for u in rep.unmappable]}", flush=True)
print(f"SECOND_ORDER {len(agg.absorbing)} residents absorbing for someone", flush=True)
print("DONE", flush=True)
