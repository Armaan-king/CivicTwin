# CivicTwin — Team Handoff

> **Purpose:** let the frontend and the backend be built in parallel, starting today, without
> either side waiting on the other.
>
> **Today's split:** frontend is being built now. Everything else — simulation engine, graph,
> runtime agents, data pipeline, calibration — is open for teammates to pick up.
>
> **Read this first, then `docs/scenario-v1.md`.** This file tells you what to build and in
> what order. That file tells you exactly what the thing does, and it is locked.

---

# 1. What CivicTwin is, in sixty seconds

A planner proposes removing two bus stops. The headline metric improves — average journey
time drops. CivicTwin simulates the change across 2,000 synthetic Singapore residents wired
into a dependency graph, and finds that **one subgroup is severely harmed**: elderly,
mobility-constrained residents who lose reliable polyclinic access.

Then it finds something a spreadsheet never would. A working-age daughter, with no mobility
limitation, living nowhere near a removed stop, is *also* severely harmed — because she now
drives her mother to the clinic and misses work. That harm exists only because the graph
models who depends on whom.

CivicTwin then generates alternatives, re-simulates them, publishes one for public
consultation, and compares predicted support against real responses to show where its own
assumptions were wrong.

**The one-line version:** aggregate metrics hide people; CivicTwin finds them before rollout.

---

# 2. Where truth lives

Do not duplicate content between these. Each has one job.

| File | Owns |
|---|---|
| `goal.md` | Product intent, scope, success criteria, non-goals. **Ask before editing.** |
| `AGENTS.md` | Rules for coding agents (Claude Code, Codex). Read section 10B before touching reference repos. |
| `README.md` | Setup, install, run |
| **`docs/scenario-v1.md`** | **The locked V1 spec. Canonical for every transport detail.** |
| `docs/architecture.md` | System design, API shapes, prior art (section 22) |
| `docs/simulation.md` | General modelling rules |
| `docs/evaluation.md` | Validation, metrics, required results |

Decisions carry stable IDs — **A1**, **F3**, **G2**, **N2**. Use them in commits and PRs
("implements F1.6") so a reviewer can find the reasoning without asking.

**Precedence:** `goal.md` > `scenario-v1.md` > everything else.

---

# 3. The contract (read this before writing any code)

The frontend is being built today against data the backend does not produce yet. The only
thing that makes that safe is **both sides coding to the same fixture**.

> **Rule: the fixture is the contract.** Frontend renders `data/fixtures/demo_run.json`.
> Backend produces a byte-compatible file. Neither side invents a field without changing this
> section first.

**Both transports are live.** `lib/config.ts` reads one env var:

```bash
VITE_TRANSPORT=fixture npm run dev   # committed run, no backend needed (default)
VITE_TRANSPORT=http npm run dev      # talks to FastAPI on :8000
```

Same shapes either way. A badge in the top bar shows which is active, so nobody demos
cached data believing it is live. Writes are refused loudly under the fixture transport
rather than faked (`NotAvailableOffline`), because a submit button that silently does
nothing is worse than one that says why.

## 3.1 Core types

```ts
type Severity = "none" | "moderate" | "high";
type AgeBand   = "<18" | "18-34" | "35-54" | "55-64" | "65-74" | "75+";
type Mobility  = "none" | "mild" | "moderate" | "severe";

interface Persona {
  persona_id: string;              // "p_0184"
  age_band: AgeBand;
  home_subzone: string;
  household_id: string;
  household_role: string;
  income_band: "low" | "mid" | "high";
  employment_status: "employed" | "unemployed" | "retired" | "student";

  mobility_level: Mobility;
  max_walk_m: number;              // 250 | 500 | 800 | 1200  (C3)
  transfer_tolerance: number;
  work_start_time: string | null;  // "08:30"
  has_car_access: boolean;
  is_caregiver: boolean;

  inconvenience_tolerance: number; // 0..1
  switching_propensity: number;    // 0..1
  baseline_trust: number;          // 0..1

  narrative: string;               // pre-generated, cached, synthetic (C5)
  xy: [number, number];            // projected position for rendering
}

interface PersonaOutcome {
  persona_id: string;
  severity: Severity;              // F3
  walk_distance_m: number;
  journey_time_min: number;
  essential_trips_completed: number;
  essential_trips_total: number;
  accessibility_status: "ok" | "degraded" | "unreachable";
  second_order: boolean;           // true if harmed via CARES_FOR — the money shot
}
```

`second_order` exists so the UI can find demo beat 5 without re-deriving it from the event
graph. Backend sets it when **F3** clause 4 fires.

## 3.2 Graph

```ts
type NodeKind = "Person" | "Household" | "Stop" | "Service"
              | "Subzone" | "Workplace" | "School" | "Polyclinic";

type EdgeKind = "LIVES_IN" | "MEMBER_OF" | "USES" | "WORKS_AT"
              | "STUDIES_AT" | "NEEDS" | "CARES_FOR" | "SERVES" | "ROUTES_TO";

interface GraphNode { id: string; kind: NodeKind; label: string; xy: [number, number]; }
interface GraphEdge { source: string; target: string; kind: EdgeKind; attrs?: Record<string, unknown>; }
```

Directed. `CARES_FOR` is asymmetric — see **D2**.

## 3.3 Events

Nine kinds, no more (**H2**). `cause` chains to an upstream `event_id`; that chain is what
root-cause tracing walks.

```ts
type EventKind =
  | "ROUTE_UNAVAILABLE" | "WALK_DISTANCE_INCREASED" | "TRANSFER_ADDED"
  | "TRAVEL_TIME_INCREASED" | "ACCESSIBILITY_THRESHOLD_EXCEEDED"
  | "ESSENTIAL_ACCESS_DEGRADED" | "CAREGIVER_SUPPORT_TRIGGERED"
  | "WORK_ARRIVAL_MISSED" | "TRIP_ABANDONED";

interface SimEvent {
  event_id: string;
  round: 0 | 1 | 2 | 3;            // B1 — propagation depth, NOT days
  persona_id: string;
  kind: EventKind;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  cause: string | null;            // upstream event_id
}
```

## 3.4 Metrics — exactly six (I1)

```ts
interface Metrics {
  avg_journey_time_delta: number;      // negative = improvement
  severe_harm_count: number;
  essential_trip_completion: number;   // 0..1
  walk_distance_p90: number;
  subgroup_disparity: number;
  operating_cost_index: number;        // baseline = 1.00
}

interface SubgroupMetrics {            // four axes, no cross-tabs (I4)
  age_band:      Record<string, Metrics>;
  mobility_level:Record<string, Metrics>;
  home_subzone:  Record<string, Metrics>;
  is_caregiver:  Record<string, Metrics>;
}
```

Every subgroup row must carry an `n`. A metric on a cohort of 6 is not a finding.

## 3.5 Interventions — five types (J1)

```ts
type InterventionKind =
  | "retain_stop_peak" | "add_shuttle_feeder" | "reroute_feeder"
  | "targeted_support" | "phase_rollout";

interface Intervention {
  intervention_id: string;
  kind: InterventionKind;            // planner selects, never invents
  params: Record<string, unknown>;
  rationale: string;
  target_finding_id: string;
  valid: boolean;
  validation_errors: string[];
  estimated_cost_index: number;      // relative, never currency (J3)
}
```

## 3.6 Feedback and calibration

```ts
interface Feedback {
  response_id: string;
  support: 1|2|3|4|5;                // the ONLY calibration target
  perceived_fairness: 1|2|3|4|5;
  clarity_of_explanation: 1|2|3|4|5;
  confidence_in_delivery: 1|2|3|4|5;
  expected_personal_impact: -2|-1|0|1|2;
  comment: string | null;
  cohort: { age_band?: AgeBand; home_subzone?: string; mobility_level?: Mobility } | null;
  is_seeded: boolean;                // MUST be surfaced in the UI (K3)
}

interface CalibrationRow {
  cohort_axis: string; cohort_value: string;
  predicted_support: number; observed_support: number;
  signed_error: number; n: number;
  flagged: boolean;                  // |error| > 10pp AND n adequate (L2)
}
```

## 3.7 Endpoints

```text
GET   /api/scenario                        scenario meta + policy
POST  /api/runs                            start a run  -> {run_id}
GET   /api/runs/{id}                       full SimulationResult
POST  /api/runs/{id}/rounds/stream         NDJSON, see architecture.md 5.1
POST  /api/runs/{id}/rounds                non-streaming fallback
GET   /api/runs/{id}/impacts               ImpactFinding[]
GET   /api/runs/{id}/impacts/{fid}/trace   root-cause event chain
POST  /api/runs/{id}/interventions         generate 5, validate, simulate top 3 (J2)
POST  /api/compare                         baseline vs alternatives
POST  /api/consultations                   publish (requires human approval)
GET   /api/consultations/{id}
POST  /api/consultations/{id}/feedback
GET   /api/consultations/{id}/analysis     PCS + themes + subgroup
GET   /api/runs/{id}/calibration           CalibrationRow[]
```

---

# 4. Workstreams

Ordered by dependency. **W1 unblocks everyone — do it first.**

### W1 · Fixture + schemas — *blocks all other work*
Pydantic models for every type in section 3, plus a committed
`data/fixtures/demo_run.json` with plausible values. It does not need to come from a real
simulation yet — it needs to be **shape-correct**, so the frontend can render today and the
engine can be swapped in behind it later.
**Done when:** frontend renders the full demo from the fixture with no backend running.

### W2 · Data pipeline (M1–M3)
LTA DataMall bus stops/services for one corridor; SingStat subzone × age band; polyclinic
locations. Trim, process, vendor into `data/fixtures/` with a provenance file (source URL,
retrieval date, licence, trimming applied). Keep the download script; the demo never runs it.
**Verify actual field names against current docs — do not trust names in our specs.**
**Done when:** a processed fixture exists and the study-area rule in **A3** has been applied
to real figures.

### W3 · Population + graph (C1–C5, D1–D4)
Sample 2,000 personas from W2 distributions. Build the `DiGraph`. Conditional edges per
**D4** — uniform edges destroy the subgroup variance the whole product depends on.
**Done when:** graph stats printed, `CARES_FOR` edges exist, seeded runs reproduce exactly.

### W4 · Simulation engine (F1, F3, G1, G2, B1) — *the core*
Seven deterministic rules, one logistic, four propagation rounds. No LLM anywhere in this
module.
**Watch out for D3:** stop assignment must be **recomputed after the policy applies**. If a
persona keeps their original `USES` edge to a removed stop, no harm is ever detected and the
audit silently returns nothing. This is the single easiest thing to get wrong.
**Done when:** unit tests cover all seven rules; same seed produces identical output.

### W5 · Impact audit + root cause
Rank findings, compute the six metrics across four cohort axes, walk the `cause` chain to
produce traces. Deterministic — no model call.
**Done when:** at least one `second_order: true` persona is detected and its trace resolves
end to end.

### W6 · Runtime agents (E2, J1, J2, L1)
Policy Interpreter, Intervention Planner, Intervention Validator, Feedback Analyst. Bedrock
behind an interface so tests mock it. Pydantic-validated output; visible failure, never a
silent plausible fallback.
**Done when:** the suite passes with zero live Bedrock access.

### W7 · Consultation + calibration (K1–K4, L1–L3)
Feedback form, seeded response set, PCS, calibration table. `is_seeded` must be visible in
the UI. Calibration proposes, never auto-applies.
**Done when:** one cohort shows a flagged calibration error with its `n` beside it.

### W8 · Frontend — *built*
Seven screens, all reading the fixture through `lib/api.ts`. What remains:
- `startRun` and `streamRounds` are implemented in the client but no screen calls them.
  Wiring the policy screen to `POST /api/runs` and the round scrubber to the NDJSON
  stream is the next frontend job.
- No frontend tests. The backend has 38; the frontend has none.
- The deliberation screen (**P5**) is not built. It is the one screen that answers "what did
  this do to people" in their own words, and it is where W10's output lands.
- `/impact` was restructured to two zones. The other screens got the spacing pass but not
  the same information-architecture rethink; `/interventions` and `/calibration` are the
  two most likely to still feel dense.

### W10 · Persona deliberation (P1-P5) — *new, and now core*
The agent that makes every resident reason about the policy, plus the screen that shows it.

- `app/agents/persona_voice.py`: a `BehaviorAssessment` per persona, grounded strictly in
  their record and event trace. It categorises and explains; it never introduces a fact.
- Batched and concurrent behind the existing `LLMClient`. Roughly 2,040 calls for a
  2,000-persona run, about two minutes at 20 concurrent.
- Cached on `sha256(persona_id, policy_version, round, model_id, prompt_version)`, so a
  replay costs nothing and the demo never waits on a model.
- Streamed as `assessment` frames on the existing NDJSON round endpoint.
- Export as JSON and Markdown.

**Done when:** a full pass completes, replays from cache with zero calls, and no assessment
cites a fact absent from its persona's record. That last one is a test, not a hope.

### W9 · Evaluation (N1, N2)
Eight required results from `evaluation.md` section 28, including the **N2** ablation.
**Done when:** results file exists with run ids, and the ablation shows N second-order cases
with the graph, 0 without.

---

# 5. Frontend notes

**Stack as actually built:** Vite + React + TypeScript, plain CSS with custom properties,
`react-router-dom`, and `three` for the hero only (code-split, ~514 kB, never loaded by the
other routes). No Tailwind: the design is a small bespoke token set and a build plugin
earned nothing. No Mapbox or deck.gl, per **13.2**.

**The design system is one file:** `src/styles/tokens.css`. Palette, an 8-rung type ramp,
a 6-step spacing scale, controls, and the CRT layers. Change a token there and every screen
follows. Do not introduce a second source of spacing or type values.

**Geography.** `run.geography` carries a generated street grid: 87 blocks, roads, 9 stops,
the corridor and the polyclinic, with every persona assigned to a block. Both visuals read
it, so they can never disagree about where anything is. **It is invented.** Replacing it
with real LTA coordinates (**M1**) changes that object only; no component knows.

Screens, in order of demo value:

1. **Policy input** — plain-language box, structured fallback visible on parse failure
2. **Population + graph** — human figures, fill = severity (**13.2**)
3. **Impact audit** — findings ranked, cohort breakdown, every row carries `n`
4. **Root-cause trace** — the event chain as a readable path
5. **Intervention comparison** — baseline + 3 alternatives, trade-offs exposed
6. **Consultation** — public-facing, plain language, feedback form
7. **Calibration** — predicted vs observed, per cohort, flagged rows

The figure glyph and the caregiver connector are specified in `docs/scenario-v1.md` **13.2**.

**The one screen that must land:** the moment a `HIGH`-severity figure with no mobility
limitation, nowhere near a removed stop, is shown connected to the person they care for.
That is the product. Everything else is supporting material.

---

# 6. Non-negotiables

These are not style preferences. Each traces to a rule in `AGENTS.md` or `goal.md`, and each
one is easy to violate by accident.

1. **No LLM for arithmetic, shortest paths, thresholds, or aggregation.** Deterministic code
   only. (`AGENTS.md` 10)
2. **No LLM call per persona per round.** The only per-persona model call in the system is
   the one-off narrative at population build. (`AGENTS.md` 8)
3. **Everything seeded.** `persona_seed = hash(scenario_seed, persona_id)` — never a single
   sequential RNG stream, or intervention comparisons measure reshuffled noise instead of
   policy. (**G2**)
4. **Structured outputs drive logic; prose never does.** Pydantic-validate every model
   output. (`AGENTS.md` 7)
5. **Weights are visible.** Never inside a prompt. (`goal.md` 20)
6. **Human approval** before publishing a consultation, selecting a final intervention, or
   applying a calibration update. (`goal.md` 27)
7. **Synthetic data is labelled synthetic**, everywhere it appears. Seeded feedback says so
   on its face. (**K3**)
8. **Failures are visible.** No silently converting a failed call into plausible-looking
   output. (`AGENTS.md` 18)
9. **No code copied from PropSim or Cortexia.** Neither has a LICENSE — both are
   all-rights-reserved. Patterns yes, source no. (`AGENTS.md` 10B)
10. **Don't build what isn't asked for.** Capacity modelling, social influence, backtesting,
    and cross-tabs are all deliberately deferred with reasons in **1.3**.

---

# 7. Getting started

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt  # once W1 lands

cp .env.example .env             # AWS / Bedrock config; never commit .env

uvicorn backend.app.main:app --reload
cd frontend && npm install && npm run dev
```

Target layout — **create directories only when they have a real purpose** (`AGENTS.md` 24):

```text
backend/app/{api,agents,graph,simulation,interventions,feedback,calibration,schemas}
backend/tests/
frontend/src/{components,pages,store,lib,types}
data/{raw,processed,fixtures}
scripts/
```

---

# 8. Open items

Four things still unresolved, all in `docs/scenario-v1.md` section 14.1:

1. Exact LTA DataMall dataset and field names — **verify, don't assume** (blocks W2)
2. Exact SingStat table identifiers for subzone × age band (blocks W2)
3. The study area, once **A3**'s selection rule meets real figures (blocks W3)
4. Whether LTA walking-distance guidance supports the **C3** metre thresholds

Declared assumptions that **must** appear in the submission's limitations section are listed
in `scenario-v1.md` 14.2. Do not quietly drop them — `evaluation.md` 27 treats acknowledged
limits as a credibility asset, and the calibration story only makes sense if the assumptions
were stated up front.

---

# 9. If you are a coding agent

Read `AGENTS.md` fully before your first change, then `docs/scenario-v1.md`. `CLAUDE.md`
imports `AGENTS.md` automatically; the scenario spec is not auto-loaded, so read it
explicitly when the work touches simulation, graph, metrics, interventions, feedback, or
calibration.

Do not resolve anything marked **LOCKED** differently, and do not silently settle an item in
section 8 above. Ask.
