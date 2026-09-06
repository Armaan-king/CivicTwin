"""The whole deliberation against the local model, with every guard live."""
import json, time, app.config
from app.services.llm import build_deliberation_client
from app.engine import study_area
from app.population import build_population
from app.world import build_world
from app.social import build_social_graph
from app.deliberate import deliberate
from app.aggregate import aggregate
from app.metrics import metrics_for
from app.remedies import cluster_remedies, collect_remedies, resident_candidates
from app.interventions import validate

TEXT = ("Close bus stops 54241 and 54248 on Ang Mo Kio Ave 3 and let service 265 run "
        "non-stop between them. No extra buses, no budget increase.")
geo, closed, _ = study_area()
pop = build_population(geo); world = build_world(pop, geo, closed)
social = build_social_graph(pop)
print(f"START population={len(pop.personas)} closed={sorted(closed)}", flush=True)

d = deliberate(pop, world, TEXT, build_deliberation_client(), social=social, limit=12)
print(f"RESULT model={d.model} calls={d.calls} cached={d.cached} rejected={d.rejected} "
      f"failed={d.failed_batches} {d.seconds:.0f}s", flush=True)
print("COVERAGE " + json.dumps(d.coverage()), flush=True)
print("PARTICIPATION " + json.dumps({str(k): v for k, v in d.participation.items()}), flush=True)

agg = aggregate(d, pop)
print("METRICS " + json.dumps(metrics_for(list(agg.outcomes.values()))), flush=True)

rep = cluster_remedies(collect_remedies(d))
print(f"REMEDIES asked={rep.asked()} mapped={[(c.action_type, c.count) for c in rep.mapped]} "
      f"unmappable={[(c.label, c.count) for c in rep.unmappable]}", flush=True)
for c in resident_candidates(rep, closed):
    validate(c, fleet_increase_allowed=False)
    print(f"  CANDIDATE {c.kind} valid={c.valid} errors={c.validation_errors}", flush=True)

print("VOICES", flush=True)
for v in d.ordered()[:4]:
    print(f"--- {v.persona_id} {v.name}", flush=True)
    for t in v.turns:
        print(f"  r{t.round} {t.response:<12} sev={t.severity:<8} pos={t.position:.2f} "
              f"grounded={t.grounded_in}", flush=True)
        print(f"     {t.reasoning[:180]}", flush=True)
        if t.remedy:
            print(f"     REMEDY: {t.remedy}", flush=True)
print("DONE", flush=True)
