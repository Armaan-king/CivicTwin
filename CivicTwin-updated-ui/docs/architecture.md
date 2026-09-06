# CivicTwin — Technical Architecture

> This document defines the intended implementation architecture for CivicTwin V1.  
> Product scope and goals live in [`../goal.md`](../goal.md).  
> Coding-agent behavior lives in [`../AGENTS.md`](../AGENTS.md).

---

# 1. Architectural Objective

The architecture must support one complete CivicTwin workflow:

```text
Policy Input
   ↓
Scenario Construction
   ↓
Synthetic Population + Dependency Graph
   ↓
Baseline Simulation
   ↓
Impact Audit
   ↓
Root-Cause Analysis
   ↓
Intervention Generation
   ↓
Alternative Simulation
   ↓
Scenario Comparison
   ↓
Human Review
   ↓
Public Consultation
   ↓
Feedback Analysis
   ↓
Calibration
```

The system should be:

- modular,
- reproducible,
- explainable,
- inexpensive to run,
- reliable enough for a live hackathon demo,
- extensible without implementing multiple verticals now.

---

# 2. Core Architectural Principles

## 2.1 Separate World Modeling From Agent Orchestration

CivicTwin has two different “graphs”:

### Population / Dependency Graph

Represents the simulated world:

- people,
- households,
- services,
- locations,
- infrastructure,
- dependencies,
- social connections.

### LangGraph Execution Graph

Represents CivicTwin’s runtime AI workflow:

- policy interpretation,
- simulation,
- impact auditing,
- intervention planning,
- feedback analysis,
- calibration.

These must remain conceptually and technically separate.

---

## 2.2 Keep Deterministic Logic Outside the LLM

Use normal code for:

- graph traversal,
- shortest paths,
- accessibility calculations,
- capacity constraints,
- threshold checks,
- metrics,
- schedule conflicts,
- aggregation,
- scoring.

Use LLMs for:

- policy language interpretation,
- qualitative reasoning,
- intervention ideation,
- explanation,
- feedback theme extraction.

---

## 2.3 Structured State First

All important runtime objects should use typed schemas.

Examples:

- `PolicyProposal`
- `PolicyChange`
- `Persona`
- `EnvironmentState`
- `ImpactFinding`
- `Intervention`
- `SimulationRun`
- `ScenarioMetrics`
- `CitizenFeedback`
- `CalibrationResult`

Natural-language explanations should be attached to structured objects, not substitute for them.

---

# 3. High-Level System Diagram

```text
┌──────────────────────────────┐
│       Policymaker UI         │
│  Scenario / Audit / Compare  │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│          API Layer           │
│         FastAPI              │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────────────────────────┐
│              CivicTwin Orchestrator              │
│                    LangGraph                     │
│                                                  │
│  Policy Interpreter → Scenario Builder           │
│          ↓                                       │
│  Simulation Controller                           │
│          ↓                                       │
│  Impact Auditor → Root-Cause Analyzer            │
│          ↓                                       │
│  Intervention Planner → Validator                │
│          ↓                                       │
│  Alternative Simulation → Comparator             │
└──────────┬─────────────────────┬─────────────────┘
           │                     │
           ▼                     ▼
┌───────────────────┐   ┌──────────────────────────┐
│ Simulation Engine │   │      LLM / Bedrock       │
│ Python + NetworkX │   │         Claude           │
└─────────┬─────────┘   └──────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────┐
│ Data / State                                     │
│                                                  │
│ Scenario data                                    │
│ Population snapshots                             │
│ Graph state                                      │
│ Run artifacts                                    │
│ Feedback                                         │
│ Calibration history                              │
└──────────┬───────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────┐
│    Public Consultation UI    │
│ Proposal + Real Feedback     │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ Feedback Analysis /          │
│ Simulation Calibration       │
└──────────────────────────────┘
```

---

# 4. Main Components

## 4.1 Frontend

Two logical experiences:

### Policymaker Interface

Core screens:

- dashboard,
- scenario builder,
- simulation view,
- impact audit,
- intervention lab,
- scenario comparison,
- publication flow,
- feedback analysis,
- calibration results.

### Citizen Interface

Core screens:

- proposal summary,
- predicted impact,
- affected groups,
- alternatives considered,
- assumptions,
- structured feedback,
- qualitative feedback.

The same frontend application may serve both experiences with separate routes.

---

# 5. Backend API

Recommended:

- Python
- FastAPI
- Pydantic schemas

Responsibilities:

- scenario CRUD,
- simulation execution,
- run status,
- impact results,
- intervention generation,
- scenario comparison,
- consultation publication,
- feedback submission,
- feedback analysis,
- calibration retrieval.

Possible route structure:

```text
POST   /scenarios
GET    /scenarios/{id}
POST   /scenarios/{id}/simulate
GET    /runs/{run_id}
GET    /runs/{run_id}/impacts
POST   /runs/{run_id}/interventions
POST   /scenarios/{id}/compare
POST   /consultations
GET    /consultations/{id}
POST   /consultations/{id}/feedback
GET    /consultations/{id}/analysis
GET    /scenarios/{id}/calibration
```

This is directional, not frozen.

## 5.1 Streaming round contract

The three propagation rounds of `scenario-v1.md` **B1** are streamed, not returned as one
blob, so the UI can show the dependency cascade propagating rather than appearing fully
formed. Transport is NDJSON, one JSON object per line:

```text
POST /api/runs/{run_id}/rounds/stream

{"type":"round_start","round":1,"active":["p_0184", "..."]}
{"type":"event","round":1,"persona_id":"p_0184",
 "event":"THRESHOLD_EXCEEDED","before":{},"after":{},"cause":null}
{"type":"event","round":2,"persona_id":"p_0921",
 "event":"DEPENDENCY_ABSORBED","before":{},"after":{},"cause":"evt_00417"}
{"type":"assessment","round":1,"persona_id":"p_0184","outcome_category":"abandon_trip",
 "support":2,"explanation":"...","contributing_factors":["walk 1240m","max 500m"],"cached":false}
{"type":"round_complete","round":1,"changed":["p_0184"],"snapshot":{}}
{"type":"complete","run_id":"run_...","snapshot":{}}
```

Only personas whose state changed materially appear in `changed` - at 2,000 personas the
full state is too large to push every round. The `cause` field carries the upstream event
id, which is what makes the chain traversable for root-cause tracing and for the Grounded
Explanation Rate in `evaluation.md` section 9.

A non-streaming `POST /api/runs/{run_id}/rounds` returning the final snapshot must exist
alongside it, as the fallback path and for tests.

---

# 6. Domain Layer

The backend should keep product logic out of route handlers.

Suggested logical modules:

```text
app/
├── agents/
├── graph/
├── simulation/
├── interventions/
├── feedback/
├── calibration/
├── schemas/
├── services/
└── api/
```

Each module should own one clear responsibility.

---

# 7. Environment Abstraction

The architecture should support an environment abstraction without building a plugin framework prematurely.

Conceptual interface:

```python
class EnvironmentPack(Protocol):
    name: str

    def persona_schema(self): ...
    def build_graph(self, population, resources): ...
    def apply_policy(self, state, policy): ...
    def step(self, state, timestep): ...
    def compute_metrics(self, state): ...
    def validate_intervention(self, intervention): ...
```

For V1, only one Public Policy scenario implementation is required.

This abstraction exists to reduce hard-coded coupling, not to support multiple complete verticals immediately.

---

# 8. Runtime Agent Responsibilities

## 8.1 Policy Interpreter

Input:
- natural-language policy proposal,
- optional structured configuration.

Output:
- normalized `PolicyChange`.

The output must be schema validated.

---

## 8.2 Scenario Builder

Input:
- normalized policy,
- environment configuration,
- data sources.

Output:
- population,
- dependency graph,
- initial state,
- scenario metadata.

---

## 8.3 Simulation Controller

Input:
- scenario state,
- policy,
- random seed,
- simulation parameters.

Output:
- final state,
- state transitions,
- metrics,
- event log.

It should call the simulation engine rather than ask an LLM to “simulate society.”

---

## 8.4 Impact Auditor

Input:
- baseline metrics,
- subgroup metrics,
- event log,
- graph state.

Output:
- ranked `ImpactFinding` objects.

Each finding should contain:

- affected group,
- severity,
- metric change,
- evidence,
- explanation,
- confidence / caveat where appropriate.

---

## 8.5 Root-Cause Analyzer

Input:
- impact finding,
- graph,
- relevant state transitions.

Output:
- dependency/propagation path,
- explanation.

It should ground explanations in actual graph or state evidence.

---

## 8.6 Intervention Planner

Input:
- original objective,
- harmful outcomes,
- constraints,
- root causes.

Output:
- bounded list of structured `Intervention` candidates.

The LLM may generate ideas, but each candidate must be validated.

---

## 8.7 Intervention Validator

Checks:

- schema validity,
- scenario compatibility,
- hard constraints,
- policy invariants,
- simulation feasibility.

Invalid candidates are rejected before re-simulation.

---

## 8.8 Scenario Comparator

Compares:

- baseline,
- alternatives,
- subgroup outcomes,
- severe harm,
- cost,
- implementation complexity,
- configured objectives.

It should expose trade-offs rather than hide them behind a single score.

---

## 8.8a Persona Deliberation

Input:
- a persona's structured record,
- their event trace for this round,
- the policy in plain language.

Output:
- a validated `BehaviorAssessment` (`scenario-v1.md` **P2**).

Runs once per persona, and again only where a later round changed their situation. Batched
and concurrent, cached by content hash, and streamed to the client as it completes. The
prompt carries the facts; the model categorises and explains. It must not introduce a fact
the record does not contain.

## 8.9 Feedback Analyst

Input:
- structured citizen feedback,
- qualitative comments.

Output:
- aggregate metrics,
- subgroup differences,
- themes,
- newly surfaced constraints,
- possible re-simulation triggers.

---

## 8.10 Calibration Module

Input:
- simulated expectations,
- observed public feedback.

Output:
- error metrics,
- poorly calibrated cohorts,
- recommended parameter updates,
- calibration history.

V1 can keep this simple and explicit.

---

# 9. LangGraph Runtime Flow

A reasonable initial graph:

```text
START
  ↓
interpret_policy
  ↓
build_scenario
  ↓
validate_scenario
  ↓
simulate_baseline
  ↓
audit_impact
  ↓
analyse_root_causes
  ↓
generate_interventions
  ↓
validate_interventions
  ↓
simulate_alternatives
  ↓
compare_scenarios
  ↓
HUMAN REVIEW
  ↓
publish_consultation
  ↓
analyse_feedback
  ↓
calibrate
  ↓
END
```

Potential conditional branches:

```text
invalid scenario
      → return for correction

no material negative impact
      → comparison / human review

invalid intervention
      → discard candidate

feedback reveals new constraint
      → optional re-simulation
```

All automated loops must have hard limits.

---

# 10. Simulation Engine Boundary

The simulation engine should behave like a normal software subsystem.

Conceptual signature:

```python
result = simulate(
    environment=environment,
    population=population,
    graph=graph,
    policy=policy,
    seed=seed,
    parameters=parameters,
)
```

Returned result should include:

```text
SimulationResult
├── run_id
├── final_state
├── event_log
├── aggregate_metrics
├── subgroup_metrics
├── persona_outcomes
└── diagnostics
```

See [`simulation.md`](./simulation.md) for the modeling rules.

---

# 11. Persistence

V1 storage should remain simple.

Possible split:

### S3
For:
- datasets,
- large snapshots,
- exported run artifacts,
- static consultation assets.

### DynamoDB
For:
- scenarios,
- run metadata,
- interventions,
- feedback,
- calibration summaries.

### Local Development
A lightweight local adapter may use:
- JSON,
- SQLite,
- local filesystem.

The application should ideally separate persistence behind repository/service interfaces so local development does not require AWS.

---

# 12. AWS / Bedrock

Claude can be accessed through Amazon Bedrock using AWS credentials.

Likely access methods:

- `boto3` Bedrock Runtime Converse API,
- `ChatBedrockConverse` if using LangChain/LangGraph integration.

Use low-cost models for frequent structured tasks.

Escalate to a stronger model only for reasoning tasks that clearly need it.

Do not assume every AWS sandbox account exposes every Bedrock model; model availability must be verified.

---

# 13. Cost Architecture

The system should be designed around a small hackathon budget.

Preferred:

- serverless/on-demand services,
- local NetworkX computation,
- batched LLM reasoning,
- cached reusable outputs,
- structured prompts,
- deterministic simulation.

Avoid:

- one LLM call per persona per timestep,
- always-on compute,
- managed search clusters,
- unnecessary databases,
- expensive long-running endpoints.

---

# 14. Recommended Framework/Library Categories

Coding agents are encouraged to suggest specific tools when implementation begins.

Potential categories:

### Graph
- NetworkX
- graphology / Cytoscape.js / Sigma.js for visualization

### Backend
- FastAPI
- Pydantic

### Agent Orchestration
- LangGraph

### LLM / AWS
- boto3
- LangChain AWS integration where useful

### Data
- pandas
- NumPy

### Validation / Testing
- pytest
- Hypothesis if property-based testing becomes valuable

### Visualization
A graph library plus a separate chart library may be appropriate.

Selection should be based on actual needs rather than this list.

---

# 15. API/LLM Boundary

All LLM operations should be wrapped behind services/interfaces.

Example:

```python
class PolicyInterpreter:
    async def interpret(self, text: str) -> PolicyChange:
        ...
```

This allows:

- mocking in tests,
- switching models,
- recording token usage,
- validating structured output,
- fallback behavior.

Do not embed raw Bedrock calls throughout business logic.

---

# 16. Event and Audit Log

A simulation should retain an event log useful for:

- explanation,
- debugging,
- impact tracing,
- visualization.

Example:

```text
t=03 persona=1847 event=ROUTE_CHANGED
t=03 persona=1847 travel_time=58m
t=03 persona=1847 mobility_threshold_exceeded=true
t=04 persona=1847 clinic_access=DEGRADED
t=05 persona=826 household_support_action=TRIGGERED
```

The log does not need to store every trivial variable change if that harms performance.

---

# 17. Human Approval Points

At minimum, the architecture should support explicit human approval before:

- publishing a public consultation,
- selecting the final policy recommendation,
- treating calibration updates as authoritative.

The runtime should not silently cross these boundaries.

---

# 18. Failure Handling

Important failure cases:

- Bedrock unavailable,
- invalid structured model output,
- malformed policy input,
- insufficient scenario data,
- simulation crash,
- invalid intervention,
- missing feedback fields,
- calibration impossible due insufficient sample.

The system should:

- fail visibly,
- preserve useful diagnostics,
- retry only bounded transient failures,
- avoid presenting failure output as valid analysis.

---

# 19. Observability

Track where practical:

- request ID,
- scenario ID,
- run ID,
- runtime agent,
- model,
- token usage,
- latency,
- retry count,
- simulation duration,
- validation errors,
- total cost estimate.

This should support evaluation and debugging without becoming an observability project.

---

# 20. Security / Privacy

V1 should avoid storing unnecessary personal information.

Public feedback should preferably use:

- synthetic demo users,
- pseudonymous IDs,
- optional demographic fields only when relevant to subgroup analysis.

Do not require sensitive data unless the selected scenario genuinely needs it.

---

# 21. Future Architecture

Future production-scale possibilities may include:

- dedicated graph database,
- event-driven simulation infrastructure,
- streaming data,
- real public-service APIs,
- identity / representativeness controls,
- more sophisticated calibration models,
- multiple Environment Packs.

These are explicitly future considerations.

The hackathon architecture should prove the concept without building production-scale infrastructure prematurely.

---

# 22. Prior Art and Deliberate Divergences

## 22.1 PropSim

[PropSim](https://github.com/derekmu8/propsim) is the direct inspiration for CivicTwin and
is worth reading before implementing the orchestration layer. It seeds ~120 Californian
voters as Claude-driven agents, wires them into a NetworkX social graph with homophily
bias, and runs 8 rounds of opinion shift against a real ballot proposition, streaming
per-agent reasoning to a D3 force-directed UI.

**Patterns adopted:**

1. **Per-agent history plus per-round aggregate.** A stance history on each agent alongside
   a round snapshot, with one generic aggregation helper computing every cohort axis.
   CivicTwin's equivalent is persona state history plus the four cohort axes of
   `scenario-v1.md` **I4**.
2. **Streaming rounds with progress callbacks.** See section 5.1.
3. **Changed-id diffing** - push only materially changed entities.
4. **Session state with reset-in-place and a fingerprint** to skip redundant reseeding.
5. **Counterfactual as a second config run through the identical pipeline.** CivicTwin uses
   the same mechanism twice: baseline-vs-intervention comparison, and the **N2** graph
   ablation.

## 22.2 Where CivicTwin deliberately diverges

**PropSim's simulation engine is one LLM call per active agent per round** - roughly 530
Haiku calls per run. CivicTwin does not do this, and the difference is not a cost
optimisation but a difference in subject matter.

PropSim simulates *opinion*, which is genuinely linguistic and has no closed form;
delegating persuasion to a model is correct there. CivicTwin simulates *access* - walking
distance, transfer counts, threshold breaches - which is geometry. `scenario-v1.md` **F1**
computes it exactly, and `AGENTS.md` sections 8 and 10 forbid delegating it.

Three further divergences, each a direct requirement elsewhere in these documents:

| PropSim | CivicTwin | Requirement |
|---|---|---|
| Behavioural model lives in a 7-rule system prompt | Explicit logistic (**G1**) and support function (**L1**) | `AGENTS.md` section 6 - no business rules hidden in prose prompts |
| No seeding anywhere; runs not reproducible | Hierarchical per-persona seeds (**G2**) | `goal.md` section 34, `simulation.md` section 23 |
| Undirected social graph | Directed, with asymmetric `CARES_FOR` (**D2**) | Second-order harm must propagate one way only |

A model-authored behavioural rule set also makes calibration impossible: an error cannot be
attributed to a coefficient that does not exist. **L1** exists precisely so that
"we overestimated support among 65+ by 19 points" has a locatable cause.

## 22.3 Cortexia

[Cortexia](https://github.com/yajat009/Cortexia) is referenced for its frontend only - a
population rendered as human figures rather than abstract nodes. The glyph is seven SVG
primitives (shadow ellipse, head circle, torso, two arms, two legs) on a `0 0 64 96`
viewBox, with **state carried by fill colour alone**. That restraint is why hundreds of
figures read as a population instead of visual noise. See `scenario-v1.md` section 13.2.

Its stack (Vite + React + TypeScript + Tailwind + Radix + zustand + Recharts +
framer-motion) is a reasonable model. **Mapbox and deck.gl are deliberately not adopted** -
they require an API token and put a tile fetch on the demo critical path, which `AGENTS.md`
section 22 rules out. The bus route is drawn as SVG directly from GTFS coordinates.

## 22.4 Licensing constraint

**Neither repository carries a LICENSE file.** Under default copyright that is all rights
reserved. Architecture and patterns are not copyrightable; source expression is.

**Reimplement from the pattern. Never copy code from either repository into CivicTwin.**
