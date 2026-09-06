import time, app.config
from app.services.llm import OllamaCompletion, LLMClient
from app.engine import study_area
from app.population import build_population
from app.world import build_world
from app.social import build_social_graph
from app.cohort import select_cohort
from app.agents.deliberation import opening_prompt, run_opening

TEXT = ("Close bus stops 54241 and 54248 on Ang Mo Kio Ave 3 and let service 265 run "
        "non-stop between them. No extra buses, no budget increase.")
geo, closed, _ = study_area()
pop = build_population(geo); world = build_world(pop, geo, closed)
c = select_cohort(pop, world, build_social_graph(pop), comparison=0)
llm = LLMClient(OllamaCompletion("deepseek-r1:8b", temperature=0.8), max_attempts=2)

n = 4
group = [p for p in pop.personas if p.persona_id in set(c.ids[:n])][:n]
prompt = opening_prompt([(p, world[p.persona_id]) for p in group], TEXT)
print(f"START {n} residents, prompt {len(prompt)} chars", flush=True)
t = time.time()
try:
    b = run_opening(prompt, llm, len(group))
    el = time.time() - t
    print(f"RESULT OK {len(b.voices)} voices in {el:.0f}s ({el/n:.0f}s per resident)", flush=True)
    for v in b.voices:
        tn = v.turns[0]
        print(f"  {v.persona_id} | {v.name} | pos={tn.position} conf={tn.confidence} "
              f"sev={tn.severity} grounded={tn.grounded_in}", flush=True)
        print(f"    {tn.reasoning[:160]}", flush=True)
except Exception as e:
    print(f"RESULT FAILED after {time.time()-t:.0f}s: {str(e)[:300]}", flush=True)
