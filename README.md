# CivicTwin

**A policy looks fine on average. CivicTwin finds the people it quietly breaks.**

Close two bus stops and the mean journey across a town gets *faster*. That number is true,
and it is the number a transport plan is approved on. Underneath it, a handful of residents
lose the only stop they can reach, and a handful more — who were never near the closure at
all — start driving a parent to a clinic and missing the start of their own shift.

CivicTwin is a simulator for exactly that gap. It builds a synthetic town from real open
transport data, puts a proposed policy to every resident in it, and asks each one what the
change does to them. The residents answer for themselves; the system counts what they said.

---

## 1. The idea, in one mechanism

CivicTwin is not really a transport tool. It detects a pattern that recurs wherever an
institution optimises an aggregate:

> **a threshold, a dependency, and someone who absorbs a loss that was not theirs.**

Change the nouns and it is clinic consolidation, benefits digitisation, school catchment
redraws, appointment systems, tariff restructuring. Transport is how the mechanism is
proved, not what the product is about.

The three parts matter together:

- **A threshold** — a walk that crosses what someone can manage, a trip that stops being
  reachable within the time they have.
- **A dependency** — someone whose journey is made by another person.
- **An absorbed loss** — the carer takes on the trip, and the cost lands on a person the
  policy never touched and no impact assessment counted.

An average cannot express that. Neither can a survey, because the person absorbing the loss
often does not think of themselves as affected until they hear what happened to someone
else.

---

## 2. What makes the answers trustworthy

The obvious objection to simulating people with a language model is that it will simply
make things up. CivicTwin's architecture is largely an answer to that objection.

### Facts are looked up. Consequences are reasoned.

This is the line the whole system is built around.

Code computes everything factual: the walking distance from a flat to a bus stop, which
services call there, which stop remains once one closes, how much longer the journey takes,
who lives in which household. These are geometry and lookup, and a model asked to compute a
distance will invent a plausible one.

The resident decides what those facts *mean*. Whether 503 metres instead of 183 is an
inconvenience or the end of a weekly hospital trip is a judgement about a life, and that
judgement is the product.

```
  computed by code                    decided by the resident
  ─────────────────                   ───────────────────────
  walk distance, journey time         severity: none / moderate / high
  which stop closes, what is left     what they do about it
  who lives with whom                 whether the essential trip still happens
  the social graph                    support for the policy
```

### Every claim carries its receipts

Each resident is handed a numbered list of facts about their own life, and nothing else:

```
[p_0524:f1]  r0  Your nearest bus stop is Blk 700B (54241), about 135 m walk from home.
[p_0524:f2]  r0  Services calling at Blk 700B: 130, 132, 133, 136, 138, 265.
[p_0524:f6]  r0  You have mild difficulty walking. You would not normally walk more
                 than about 800 m to a stop.
[p_0524:f7]  r1  Blk 700B is the stop you use. It is closing.
[p_0524:f8]  r1  The nearest stop that stays open is Opp Al-Muttaqin Mque (54031),
                 about 360 m from home. That is +225 m compared with now.
```

Their answer must cite the fact ids it reasoned from. A conclusion citing a fact the
resident was never given is **rejected and counted**, never displayed. The count is
reported on screen next to the results.

The guard is stricter than it first appears, in three ways that each closed a real hole:

- **Scoped to the round.** A resident reasoning in round 1 may cite only what they had been
  told by round 1. Checking against every fact they would *ever* hold let a turn cite
  something revealed two rounds later.
- **A citation must be capable of supporting the claim.** Being 72 and having no car were
  both true before anyone proposed anything, so they cannot establish that the policy did
  something. A claim of harm has to reach at least one fact about the policy itself.
- **Identity is validated, not repaired.** A batch that comes back for the wrong residents
  is refused. Overwriting the ids would silently attach twelve residents' reasoning to the
  wrong twelve people, which still looks like evidence.

### Nobody is counted as unharmed by default

A resident who was never asked is **unknown**, not unaffected. A resident who was asked and
whose answer failed the grounding guard is unknown too — a third state, and the run reports
all three separately:

```json
"coverage": {
  "population": 2000, "cohort": 818, "evaluated": null,
  "unevaluated": null, "ungrounded": null, "unexplained_moves": null
}
```

`population` and `cohort` are configuration and are exact. The rest are filled in by a
run and are shown here as nulls rather than as plausible-looking figures: quoting an
evaluation result nobody measured is the specific thing `AGENTS.md` §21 forbids, and a
README is not exempt from it.

The cohort is 818 rather than the whole town because asking two thousand residents is
mostly waste: a stop closure reaches about forty of them directly. It is built from three
strata — 43 whose own stop closes, 175 tied to one of them by household or care, and a
600-strong stratified comparison group that exists so every rate has a denominator and
every subgroup cell clears the n ≥ 30 floor. The comparison budget is the number that
moves if you want more reportable subgroups; the population is not.

Every rate the product shows travels with the denominator it was computed over. A subgroup
too small to support a claim is reported as *insufficient evidence* — never as zero
disparity, which is the same number wearing a finding's clothes.

---

## 3. The loop

```
        ┌──────────────────────────────────────────────────────────────┐
        │                                                              │
   POLICY ──► SIMULATE ──► IMPACT ──► VOICES ──► OPTIONS ──► CONSULT ──┘
   plain      the world     who was    why, in    what to     ask real
   English    changes       harmed     their      do about    people
                                       words      it              │
                                                                  ▼
                                                               LEARN
                                                          what the model
                                                             got wrong
```

**Policy.** A planner writes a proposal in plain English. A model reads it into a typed
`PolicyChange` — which stops, which service, which constraints — and the interface shows
that reading back before anything runs, marking every field the model assumed rather than
was told. The words then decide the study area: a proposal naming stops in Bedok resolves
to Bedok, because those stop names exist there and nowhere else. A proposal naming nowhere
we hold data for is refused rather than quietly run against a default town.

**Simulate.** The network changes. Distances, routes and journey times are recomputed
against the real stop geometry, and the change is revealed in four stages — the corridor as
it runs today, the stops closing, residents adjusting, and the full picture including the
second-order effects that only appear once households react.

**Impact.** Findings ranked by severity, then by how many people they touch. Severity
outranks headcount deliberately: four carers missing work is listed above seventeen people
walking further, because the argument of the product is that the small severe number is the
one an average hides.

**Voices.** Every evaluated resident, in their own words, with the facts they reasoned from
attached. This is the screen a metric cannot replace: *"the policy closes Blk 700B, which is
my normal stop and the one I use for trips to Ang Mo Kio Community Hosp."*

**Options.** Five typed interventions — the planner selects and parameterises, it never
invents a type. Each valid candidate is re-evaluated over the same residents with the same
seeds, so a difference is attributable to the intervention rather than to reshuffled
randomness. Residents also author remedies of their own during deliberation, and those go
through the same validator with no exemption.

**Consult.** The chosen option goes to a public feedback form: support, fairness, clarity,
confidence, and a free-text field.

**Learn.** Predicted support against reported support, per cohort, and the gap between them.

---

## 4. Two things the loop does that are unusual

### Residents author the remedies

Harmed residents are asked one further question during the deliberation they were already
paying for:

> *What would make this workable for you?*

Answers are clustered, mapped onto the typed action space where one fits, and carried with
the count of residents who asked for it. They then face the same validator as any planner
candidate — and frequently fail it, which is itself the finding. The remedy residents ask
for most often is a shuttle, and a shuttle needs a vehicle, and the policy declares no fleet
increase.

**What the action space cannot express is reported, not dropped:**

```
31 residents asked for something this model cannot simulate
   "somewhere to sit and wait"            14
   "a shelter over the new walk"          11
   "a different appointment time"          6
```

A model that quietly discarded those would be hiding the gap between what it can represent
and what people actually need. That gap belongs on the screen.

### The consultation names who it will fail to hear

Turnout is not uniform and it is not random. The residents most affected are often least
able to respond: the oldest, the least mobile, the ones already spending spare hours caring
for someone else. CivicTwin models both halves — severity per resident, and turnout weighted
by stake and capacity — so it can multiply them:

```
blind_spot = severity × (1 − expected_response_rate)
```

reported as cohorts with counts. It is the one output a ministry could act on the same
afternoon, because it names who to go and find. It is also the honest counterweight to a
public confidence score, which can only ever describe the people who replied.

---

## 5. How the pieces fit

```
  SURFACE                 BOUNDARY              REASONING            WORLD
  what a person sees      typed + validated     judgement            facts, never judged
  ──────────────────      ─────────────────     ──────────────       ───────────────────
  Policy input       ┐                      ┌─ Policy interpreter    Geography (LTA)
  Simulation stages  │                      │  reads the proposal    Population (2,000)
  Impact audit       ├──► FastAPI ──────────┤                        Dependency graph
  Resident voices    │    Pydantic on       ├─ Deliberation agent    Social graph
  Intervention lab   │    every boundary    │  residents decide      Routing + distances
  Consultation       │                      │                        Metrics
  Calibration        ┘                      └─ LLMClient             Interventions
                                               one seam to any       Consultation model
                                               model provider
```

**One boundary to the model.** Every call goes through `LLMClient.structured()`, which
returns a validated Pydantic object or raises. Nothing downstream parses prose. That single
seam is where retries, token accounting, latency, caching and provider choice live — so
swapping a local model for a hosted one is a configuration change, not a refactor.

**One definition of every metric.** Six numbers — journey time delta, severe harm count,
essential trip completion, 90th-percentile walk, subgroup disparity, operating cost index —
computed in one place and read by every screen, so a number shown twice cannot disagree with
itself. Reported at overall *and* subgroup level together, always with `n`.

**Two graphs, deliberately different shapes.** Opinion travels along an undirected social
graph: neighbours on the same road, similar stage of life. Dependency is a *directed*
`CARES_FOR` edge, because harm propagates from the person who lost their stop to the carer
who absorbs the journey, and never back. Making that edge symmetric would run the cascade in
both directions and invent harm.

**Reproducible where it can be, replayable where it cannot.** Every seeded stream is derived
per key — `hash(scenario_seed, persona_id)` — never drawn sequentially, so persona 1847 draws
the same numbers under every scenario and a measured difference is causal rather than
reshuffled noise. The town, the graph, the responses and the metrics rebuild identically on
any machine. The one thing a seed cannot reproduce is a language model at temperature 0.8, so
every batch is cached on a content hash: a completed run replays exactly, for free, forever.

---

## 6. The data underneath

**The transport network is real.** Stops, routes and services come from Singapore's LTA
DataMall under the Singapore Open Data Licence, fetched into `data/lta/<town>/` with
provenance recorded alongside. Nothing about the network is invented: the study area derives
its interchange, its essential destinations and its feeder services from the extract rather
than from constants, which is what lets the same code run against another town.

**The population is synthetic, and labelled as such everywhere it appears.** Two thousand
residents are generated household-first — so a carer cannot live across the estate from the
mother they drive — with age, mobility, employment, income, car access and walking tolerance
drawn from published distributions. Care relationships are calibrated against the SMU Centre
for Research on Successful Ageing survey of Singapore caregivers rather than guessed.

The distinction is load-bearing: **a real network, a synthetic population, and never a claim
that a synthetic resident is a real person.**

---

## 7. Human judgement is a boundary, not a suggestion

Nothing consequential happens without a person.

Calibration compares what the model predicted against what people reported, per cohort, and
flags a gap wider than 10 percentage points — with the response count beside it, so a gap
driven by four replies is visibly a gap driven by four replies. When it finds one, it
identifies the likely cause from the consultation's own free text and proposes a specific,
scoped correction:

```
Ang Mo Kio Ave 3    predicted 67%    reported 53%    −14.1 pts    n = 92

  what the model missed:  the covered walkway ends partway and there is a slope.
                          The model costed the distance and not the walk.
  proposed:               walk_cost_multiplier[Ang Mo Kio Ave 3]   1.00 → 1.56
  status:                 awaiting human approval
```

The size of the correction comes from the size of the error — a 14.1-point over-prediction
is 0.56 Likert points, and the multiplier is whatever closes that over the walk those
residents actually face. A number a person is asked to approve should be derived from the
evidence that prompted it, or the approval is theatre.

Approve it and the model is corrected where it was wrong, and nowhere else:

```
  Ang Mo Kio Ave 3     −14.1 pts   flagged        ──approve──►   −7.1 pts   not flagged
  every other cohort    unchanged                                 unchanged
```

It does not fall to zero, and it should not: the correction is derived from the aggregate
gap, so it under-corrects the residents with the longest walks. A loop that landed exactly
on zero would mean the answer had been fitted rather than learned.

Nothing is ever self-applied. A model that adjusts its own parameters because it was
contradicted is a model nobody can audit, so the boundary is explicit: calibration proposes,
a person rules, and the decision is recorded either way — a rejection as carefully as an
approval, because knowing a change was put to someone and turned down is part of the audit
trail rather than the absence of one.

The same principle governs the rest: an intervention is selected by a person, never enacted
by the system; a rejected candidate carries no metrics at all, because scoring something that
was never evaluated would be inventing a result.

---

## 8. Running it

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env
```

Choose a model provider in `.env`. The same adapter serves all of them, because they speak
the same OpenAI-shaped chat API — only the host and the key name differ:

| `LLM_PROVIDER` | Model | Key |
|---|---|---|
| `ollama` | anything local, e.g. `deepseek-r1:8b` | none — loopback |
| `deepseek` | `deepseek-v4-flash` | `DEEPSEEK_API_KEY` |
| `groq` | `openai/gpt-oss-120b` | `GROQ_API_KEY` |
| `bedrock` | Claude | AWS credentials |

> **Model access on Bedrock is not uniform.** Which Claude models an account may invoke
> is set by its own permissions and, on an organisation-managed account, by service
> control policies that can deny models the console still lists. Check before assuming:
>
> ```
> aws bedrock list-foundation-models --by-provider anthropic --query "modelSummaries[].modelId"
> ```
>
> Most current Claude models are reachable only through a regional inference profile
> whose id carries a `us.` / `eu.` / `apac.` / `global.` prefix; the bare model id returns
> *"on-demand throughput isn't supported"*. Older models also cap output at 4,096 tokens,
> which is a hard rejection rather than a truncation.

`LLM_PROVIDER_INTERPRETER` overrides the provider for policy interpretation alone.
Interpretation is one call per run against a wide schema where being wrong makes every
downstream number answer a different question; deliberation is hundreds of calls against a
narrow schema where cost dominates. They are different jobs and can use different models.

> **Groq is not Grok.** Different companies, one letter apart. Groq (`gsk_…`) hosts
> open-weight models; Grok (`xai-…`) is xAI's own. Each rejects the other's key.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Health is at http://localhost:8000/health.

**Local models.** Ollama's native endpoint constrains generation to the output schema, which
is what lets a small local model return a valid batch at all. Three settings interact and
each one fails as a hang rather than an error, so they are documented in
`backend/IMPLEMENTING.md`: the context window Ollama serves regardless of what the model
advertises, the fact that the generation budget is drawn from that same window rather than
added to it, and the batch size that has to fit inside both.

**Replay.** `DELIBERATION_REPLAY_ONLY=1` serves the deliberation only from cache, so a demo
cannot accidentally spend hours calling a model for a batch that was never run. A cache miss
is skipped and counted, and the residents in it are reported as unevaluated.

**Export.** `python scripts/export_run.py` writes a finished run to `data/runs/` as JSON for
the record and Markdown for reading — every resident, every turn, every citation, the
coverage counts and the metrics. It replays from cache, so it costs nothing after a run.

Tests: `cd backend && python -m pytest tests -q`.

---

## 9. What the tests are for

The suite concentrates on the parts that must not drift, and above all on the guards:

- **Groundedness, watched failing.** Every guard has a test that plants a specific lie — a
  fabricated fact id, a fact from a round that had not happened yet, a neighbour who never
  spoke, a harm claim resting only on facts that predate the policy — and asserts it is
  caught. *A guard nobody has watched fail is not a guard.*
- **Batch integrity.** A schema-valid answer is not necessarily an answer. An empty batch, a
  short batch and a batch returned for the wrong residents are each refused, because counting
  any of them silently shrinks the population.
- **Numbers are rejected, never clamped.** A value outside its range is refused and retried.
  A clamped value is a number the resident did not say, presented as one they did.
- **The n ≥ 30 floor.** Nothing is flagged on a cohort too small to support it, and a
  calibration change is never applied without a person.
- **A mock cannot stand in for a run.** Without a model the deliberation refuses outright.
  Text that reads like a resident and is not one is worse than an empty page.

---

## 10. Repository

```
backend/app/
  backstory.py      one life per resident, generated once and grounded in a real place
  world.py          the numbered facts handed to each resident, and nothing else
  deliberate.py     the four-round loop: bounded, cached, snapshotted per round
  cohort.py         who reasons — affected, their ties, a stratified comparison
  aggregate.py      resident declarations become the six canonical metrics
  remedies.py       what residents asked for, clustered and mapped
  alternatives.py   re-evaluating an intervention over the same residents
  simulation.py     the fact layer: geometry, routes, journey times
  social.py         undirected opinion graph; CARES_FOR is directed
  consultation.py   who replies, what they say, and who will not reply
  services/llm.py   the single seam to any model provider

frontend/src/
  pages/            one screen per step of the loop
  components/       the map, the hero scene, the system diagram
  lib/naming.ts     every place and service name, derived from the run rather than typed

docs/
  scenario-v1.md    the locked scenario decisions and why each was made
  architecture.md   implementation detail
  evaluation.md     how the run is judged
GOAL.md             product goals, scope, and non-goals
AGENTS.md           instructions for coding agents working here
```

---

## 11. What it is not

Not a prediction of what will happen in Ang Mo Kio. The population is synthetic, the
consultation respondents are synthetic, and the confidence score describes only the people
who replied. Every screen says so on its face.

It is a way of asking a specific question — *who does this quietly break, and who absorbs
the cost on their behalf* — and of showing the working, in the residents' own words, with
the facts each one reasoned from attached.

> **SIMULATE → FIND WHO IS LEFT BEHIND → UNDERSTAND WHY → DESIGN A BETTER
> INTERVENTION → RE-SIMULATE → ASK REAL PEOPLE → LEARN**
