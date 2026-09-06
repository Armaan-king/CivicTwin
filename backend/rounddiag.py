"""Why did round 1 fail? Measure the prompt, then capture the raw failure."""
import json, time, httpx, app.config
from app.schemas.deliberation import DeliberationBatch, AgentTurn
from app.agents.deliberation import ROUND_SYSTEM, round_prompt, BATCH_SIZE
from app.services.llm import exact_items, require_citations
from app.engine import study_area
from app.population import build_population
from app.world import build_world
from app.social import build_social_graph
from app.cohort import select_cohort

TEXT = ("Close bus stops 54241 and 54248 on Ang Mo Kio Ave 3 and let service 265 run "
        "non-stop between them. No extra buses, no budget increase.")
geo, closed, _ = study_area()
pop = build_population(geo); world = build_world(pop, geo, closed)
c = select_cohort(pop, world, build_social_graph(pop), comparison=0)
ids = list(c.ids[:3])
index = {p.persona_id: p for p in pop.personas}
group = [(index[pid], world[pid]) for pid in ids]

prev = {pid: AgentTurn(round=0, position=0.6, confidence=0.5,
                       reasoning="I have only heard buses will be faster.",
                       grounded_in=[f"{pid}:f1"]) for pid in ids}
heard = {ids[0]: [(ids[1], prev[ids[1]])]} if len(ids) > 1 else {}
prompt = round_prompt(group, 1, prev, heard, TEXT)
print(f"BATCH_SIZE={BATCH_SIZE} round prompt = {len(prompt)} chars (~{len(prompt)//4} tokens)", flush=True)

schema = require_citations(exact_items(DeliberationBatch, "turns", len(ids)))
t = time.time()
r = httpx.post("http://localhost:11434/api/chat", json={
    "model": "deepseek-r1:8b",
    "messages": [{"role": "system", "content": ROUND_SYSTEM},
                 {"role": "user", "content": prompt}],
    "format": schema,
    "options": {"temperature": 0.8, "num_predict": 4000, "num_ctx": 8192},
    "think": False, "stream": False}, timeout=1200)
d = r.json()
txt = d.get("message", {}).get("content", "")
print(f"DONE {time.time()-t:.0f}s prompt_tokens={d.get('prompt_eval_count')} "
      f"eval={d.get('eval_count')} reason={d.get('done_reason')}", flush=True)
print("RAW:", txt[:400], flush=True)
try:
    b = DeliberationBatch.model_validate_json(txt)
    print(f"PARSED turns={len(b.turns)} persona_ids={b.persona_ids}", flush=True)
    for t in b.turns:
        print(f"   {t.persona_id} sev={t.severity} resp={t.response} "
              f"pos={t.position} grounded={t.grounded_in} remedy={t.remedy!r}", flush=True)
    print(f"EXPECTED ids={ids}", flush=True)
    print("IDS MATCH" if b.persona_ids == ids else "IDS MISMATCH <-- the failure", flush=True)
except Exception as e:
    print("INVALID:", str(e)[:600], flush=True)
