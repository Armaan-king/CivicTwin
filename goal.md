# CivicTwin — Project Goals

> **Project status:** Hackathon MVP / V1  
> **Primary vertical:** Public Policy  
> **Product type:** Agentic AI decision-simulation and public-feedback platform  
> **Working tagline:** **Stress-test change before people live with the consequences.**

---

## 1. Purpose of This File

This file defines **what CivicTwin is, why it exists, what V1 must accomplish, what is in scope, what is out of scope, and how success will be judged**.

It is the source of truth for product direction.

Implementation-process instructions for Claude Code, Codex, or other coding agents belong in `AGENTS.md`, not here.

Within this document, the word **agent** refers to an AI agent that is part of the CivicTwin product/runtime unless explicitly stated otherwise.

---

# 2. Product Definition

## CivicTwin

**CivicTwin is an agentic AI platform for stress-testing public-policy changes against a graph-connected synthetic population before those changes reach the real world.**

It simulates how a proposed intervention may affect different people over time, detects unintended or unequal consequences, proposes alternative interventions, re-simulates those alternatives, and allows the strongest candidate to be exposed to real users through a public-feedback dashboard.

Real feedback is then compared with simulated outcomes so CivicTwin can quantify where its assumptions were wrong, improve calibration, and give policymakers richer evidence before a human makes the final decision.

---

# 3. One-Sentence Product Definition

> **CivicTwin simulates how proposed public policies propagate through a synthetic population, identifies who may be unintentionally harmed, automatically tests alternative interventions, and validates the strongest proposal against real citizen feedback before a policymaker makes the final decision.**

---

# 4. Core Product Philosophy

CivicTwin exists because **aggregate metrics can hide people**.

A policy may improve the average outcome while creating severe negative consequences for a smaller subgroup.

CivicTwin therefore should not only ask:

> “Will this policy work?”

It should ask:

> **“Will this policy work, for whom, who may be left behind, why, and can we design a better version before rollout?”**

The platform should optimize for:

- earlier discovery of unintended consequences,
- subgroup visibility,
- second-order impact discovery,
- transparent trade-offs,
- human oversight,
- explainability,
- calibration against real-world feedback.

CivicTwin must not be positioned as an oracle that predicts society with certainty.

It is a **decision-support and policy stress-testing system**.

---

# 5. Core Hackathon Thesis

The hackathon requires a solution that **plans, acts, and adapts over time**.

CivicTwin should demonstrate that explicitly:

```text
Policy Proposal
      ↓
Construct Simulation World
      ↓
Simulate
      ↓
Observe Outcomes
      ↓
Audit Impact
      ↓
Identify Failure Modes
      ↓
Plan Alternatives
      ↓
Re-Simulate
      ↓
Compare Outcomes
      ↓
Select Candidate
      ↓
Public Consultation
      ↓
Observe Real Feedback
      ↓
Measure Prediction Error
      ↓
Calibrate / Adapt
```

The project should feel unmistakably **agentic**.

It should not collapse into:

- a chatbot,
- a policy summarizer,
- a static dashboard,
- a one-shot recommendation engine,
- a simple survey application,
- a collection of disconnected LLM calls.

---

# 6. V1 Product Scope

## 6.1 Primary Vertical

The first CivicTwin vertical is:

# **Public Policy**

The product should be framed as a public-policy decision digital twin, not as a transport-only tool and not as a simulator for every organization.

## 6.2 Hackathon Demonstration

The hackathon prototype should implement **one public-policy scenario extremely well**.

Possible scenarios include:

- public transport network changes,
- public-service workflow changes,
- urban development or temporary closures,
- emergency evacuation planning,
- community-resource allocation,
- public-health communication,
- social-assistance delivery,
- infrastructure access changes.

The final scenario should be chosen based on:

- data availability,
- ease of validation,
- visual demo quality,
- measurable human impact,
- graph relevance,
- feasibility within hackathon time.

## 6.3 Scope Principle

> **Build narrowly. Architect broadly.**

Public Policy is the V1 vertical.

One policy scenario is the V1 implementation.

Other institutional environments are future expansion opportunities, not MVP requirements.

---

# 7. Long-Term Product Vision

Long term, CivicTwin may become a general decision digital-twin platform.

Conceptually:

```text
CivicTwin Core
    │
    ├── Public Policy          ← V1
    │   ├── Transport
    │   ├── Housing
    │   ├── Public Services
    │   ├── Emergency Planning
    │   └── Urban Development
    │
    ├── Corporate HR          ← Future
    ├── Educational Policy    ← Future
    ├── Healthcare Operations ← Future
    ├── NGOs / Community      ← Future
    └── Other Institutions    ← Future
```

The platform vision is intentionally broader than the hackathon build.

V1 should prove the core CivicTwin loop before additional environments are attempted.

---

# 8. Primary Users

## 8.1 Policymaker / Decision Maker

Possible users include:

- policy analysts,
- urban planners,
- government service designers,
- public-sector program managers,
- infrastructure planners,
- municipal decision makers.

Primary need:

> “Before I launch this change, I want to understand who may be affected, where unexpected consequences may emerge, what alternatives exist, and whether real public feedback validates or challenges our assumptions.”

## 8.2 Citizen / Affected User

The citizen-facing experience should let a real person:

- understand what is changing,
- understand why it is changing,
- inspect predicted effects,
- see who may be negatively affected,
- understand which alternatives were tested,
- provide structured feedback,
- provide qualitative lived-experience feedback,
- challenge assumptions in the simulation.

## 8.3 Human Reviewer / Administrator

A reviewer may be responsible for:

- configuring scenarios,
- selecting datasets,
- reviewing generated interventions,
- approving public publication,
- moderating feedback,
- inspecting calibration results.

---

# 9. End-to-End User Journey

## 9.1 Policymaker Journey

1. Create or load a policy scenario.
2. Describe the proposed change.
3. Select or define the affected population.
4. Configure objectives and constraints.
5. Run the baseline simulation.
6. Inspect:
   - overall outcomes,
   - subgroup outcomes,
   - high-severity effects,
   - graph propagation,
   - root causes.
7. Generate candidate interventions.
8. Re-simulate alternatives.
9. Compare trade-offs.
10. Choose a candidate for public consultation.
11. Publish a transparent public-facing proposal.
12. Collect real citizen feedback.
13. Compare simulated responses with observed responses.
14. Inspect public-confidence metrics and subgroup disagreement.
15. Make the final human decision.

## 9.2 Citizen Journey

1. Open the public proposal.
2. Read a plain-language summary.
3. Understand:
   - what changes,
   - why,
   - predicted benefits,
   - predicted harms,
   - affected groups,
   - alternatives tested.
4. Submit structured feedback.
5. Optionally submit free-text lived-experience feedback.
6. See clearly that feedback contributes evidence rather than functioning as a simple popularity vote.

---

# 10. CivicTwin Core Loop

The product should preserve this sequence:

```text
INPUT POLICY
    ↓
CONSTRUCT WORLD STATE
    ↓
SIMULATE
    ↓
AUDIT IMPACT
    ↓
EXPLAIN CAUSES
    ↓
GENERATE INTERVENTIONS
    ↓
VALIDATE INTERVENTIONS
    ↓
RE-SIMULATE
    ↓
COMPARE
    ↓
PUBLIC CONSULTATION
    ↓
REAL FEEDBACK
    ↓
CALIBRATION
```

This is the heart of CivicTwin.

---

# 11. Synthetic Personas

Synthetic personas remain a **first-class part of CivicTwin**.

However, simulation must not reduce to:

> “Ask an LLM to pretend to be a person.”

Each persona should have structured state.

Conceptually:

```text
Persona {
    id
    demographics
    location
    household_context
    socioeconomic_context
    mobility
    schedule
    preferences
    needs
    dependencies
    constraints
    behavioural_attributes
    current_state
    network_links
}
```

The exact schema should depend on the chosen policy scenario.

Example:

```text
Persona 1847

Age: 67
Employment: Retired
Household: Lives alone
Mobility: Limited
Income band: Lower
Digital literacy: Low
Transport dependency: Public transport

Needs:
- weekly clinic access
- grocery access

Constraints:
- walking distance <= 500m preferred
- avoids multi-transfer journeys

Dependencies:
- Bus Route 14
- local clinic
- daughter for emergency transport
```

---

# 12. Persona Design Principles

Personas should be:

- diverse enough to reveal subgroup effects,
- structured,
- inspectable,
- reproducible,
- derived from real distributions where possible,
- generated under explicit constraints,
- deterministic enough for debugging,
- clearly identified as synthetic.

CivicTwin should avoid:

- unsupported psychological certainty,
- demographic stereotyping,
- presenting synthetic people as exact replicas of citizens,
- opaque persona behavior,
- unnecessarily expensive LLM-per-person simulation.

---

# 13. Population and Dependency Graph

CivicTwin should model affected people as part of a graph:

```text
G = (V, E)
```

Potential node types:

- Person
- Household
- Workplace
- School
- Hospital
- Public Service
- Transport Node
- Route
- Neighborhood
- Community Center
- Institution
- Public Resource

Potential edge types:

- `LIVES_IN`
- `WORKS_AT`
- `STUDIES_AT`
- `DEPENDS_ON`
- `USES`
- `CARES_FOR`
- `CONNECTED_TO`
- `LOCATED_NEAR`
- `REQUIRES`
- `SERVES`
- `ROUTES_TO`
- `SUPPORTED_BY`

The graph should materially influence simulation or impact analysis.

It is not merely a visualization.

---

# 14. Second-Order Consequence Discovery

One of CivicTwin’s core differentiators is detecting consequences that arise through dependencies.

Example:

```text
Bus stop removed
       ↓
Longer journey
       ↓
Clinic access degrades
       ↓
Family member provides transport
       ↓
Family member misses work
       ↓
Household impact
```

The product should surface not just the final negative outcome, but also the **propagation path that produced it**.

---

# 15. Simulation Model

The simulation engine should separate different kinds of reasoning.

## 15.1 Deterministic / Structural Effects

Examples:

- travel distance,
- service capacity,
- eligibility constraints,
- schedule conflicts,
- queue length,
- walking thresholds,
- resource limits,
- dependency availability.

These should be computed using deterministic code or conventional algorithms whenever possible.

## 15.2 Probabilistic / Behavioral Effects

Examples:

- likelihood of adopting an alternative,
- response to inconvenience,
- social influence,
- trust changes,
- willingness to switch channels.

These may use:

- rules,
- probability models,
- calibrated heuristics,
- lightweight statistical models,
- selective LLM reasoning.

## 15.3 LLM Role

LLMs should be used where language interpretation or complex qualitative reasoning adds value, such as:

- converting policy text into structured scenario changes,
- generating structured persona descriptions from distributions,
- explaining consequence chains,
- proposing alternative interventions,
- classifying citizen feedback,
- extracting newly discovered constraints,
- producing public-facing plain-language explanations,
- reasoning as each synthetic resident about how the policy lands on them.

> **V1 direction.** The last item is now a core capability, not an optional one. Every
> persona produces a validated `BehaviorAssessment` grounded in their own record, and the
> result is a screen in its own right. Volume, caching and the honesty constraints are in
> [`docs/scenario-v1.md`](./docs/scenario-v1.md) §6A.

LLMs should not be used for calculations that deterministic code can perform more reliably.

---

# 16. Runtime Agent Architecture

CivicTwin may use a controlled multi-agent architecture.

These are **product/runtime agents**, not coding assistants.

## 16.1 Policy Interpreter

Purpose:

- transform policy text into structured scenario changes,
- identify affected entities,
- extract relevant parameters.

## 16.2 Scenario Builder

Purpose:

- construct the target population,
- instantiate the graph,
- validate that the scenario contains enough information to simulate.

## 16.3 Simulation Controller

Purpose:

- execute the simulation,
- manage timesteps or rounds,
- record state transitions,
- return reproducible run artifacts.

## 16.4 Impact Auditor

Purpose:

- identify overall outcomes,
- subgroup disparities,
- severe negative impacts,
- bottlenecks,
- unexpected patterns.

## 16.5 Root-Cause / Propagation Analyzer

Purpose:

- trace dependency paths that explain an outcome,
- identify critical graph nodes and edges,
- turn structural paths into understandable explanations.

## 16.6 Intervention Planner

Purpose:

- generate bounded candidate policy modifications,
- generate mitigation measures,
- preserve the original policy objective where possible.

## 16.7 Intervention Validator

Purpose:

- reject structurally invalid or constraint-breaking alternatives before simulation.

## 16.8 Scenario Comparator

Purpose:

- compare baseline and alternative scenarios,
- expose trade-offs,
- avoid pretending there is always one objectively correct policy.

## 16.9 Public Feedback Analyst

Purpose:

- aggregate structured responses,
- extract major qualitative themes,
- identify new constraints,
- compare observed and simulated responses.

## 16.10 Calibration Module

Purpose:

- measure discrepancy between simulation and real feedback,
- identify poorly calibrated subgroups,
- update explicit behavioral assumptions where appropriate,
- preserve calibration history.

---

# 17. Orchestration

LangGraph is a strong candidate for runtime orchestration.

Important distinction:

- **Population graph** models people, institutions, infrastructure, and dependencies.
- **LangGraph** models the execution flow of CivicTwin’s AI/runtime agents.

Conceptual flow:

```text
START
  ↓
interpret_policy
  ↓
build_scenario
  ↓
validate_scenario
  ↓
simulate
  ↓
audit_impact
  ↓
analyse_causes
  ↓
generate_interventions
  ↓
validate_interventions
  ↓
simulate_alternatives
  ↓
compare_scenarios
  ↓
human_review
  ↓
publish_for_feedback
  ↓
analyse_feedback
  ↓
calibrate
  ↓
END
```

---

# 18. Intervention Search

CivicTwin must not stop at detecting harm.

Its core value is:

> **Find and test better alternatives.**

Candidate interventions may include:

- parameter changes,
- phased rollout,
- exemptions,
- targeted support,
- alternative routes,
- additional capacity,
- communication changes,
- scheduling changes,
- targeted service support.

Interventions should be machine-readable and re-simulatable.

Example:

```json
{
  "intervention_id": "alt_02",
  "type": "retain_peak_hour_stop",
  "changes": {
    "stop_c_active": true,
    "active_hours": ["07:00-10:00", "17:00-20:00"]
  },
  "estimated_operational_cost": 0.18
}
```

---

# 19. Scenario Comparison

CivicTwin should expose trade-offs instead of hiding them.

Example:

| Metric | Original | Alt A | Alt B | Alt C |
|---|---:|---:|---:|---:|
| Average benefit | 72 | 77 | 81 | 79 |
| Severe negative impact | 8% | 4% | 2% | 3% |
| Vulnerable subgroup impact | 15% | 8% | 4% | 5% |
| Relative cost | 1.0x | 1.1x | 1.3x | 1.15x |
| Implementation complexity | Low | Medium | High | Medium |

CivicTwin may recommend a candidate, but should explain the trade-off rather than present the result as objective truth.

---

# 20. “Better Off” Objective

CivicTwin needs a measurable interpretation of **better off**.

Potential metric families include:

- overall outcome improvement,
- severe-harm reduction,
- subgroup disparity reduction,
- accessibility improvement,
- service reach,
- waiting-time reduction,
- successful completion rate,
- public understanding,
- public confidence,
- implementation cost.

Conceptually:

```text
maximize:
    overall_benefit

while minimizing:
    severe_harm
    subgroup_disparity
    implementation_cost
    service_friction
```

One possible configurable utility representation:

```text
Utility =
    w1 * OverallBenefit
  - w2 * SevereHarm
  - w3 * Inequality
  - w4 * Cost
```

If weights are used, they must be:

- explicit,
- configurable,
- visible,
- never hidden inside an LLM prompt.

> **V1 binding.** For the locked transport scenario the canonical metric set is the six
> metrics in [`docs/scenario-v1.md`](./docs/scenario-v1.md) §7 (decision I1). The families
> listed above are a menu to select from, not a set to implement.

---

# 21. Public Consultation Layer

After simulation iterations, a selected candidate can be published to a citizen-facing dashboard.

The consultation page should answer:

1. What is changing?
2. Why is the change being proposed?
3. Who is predicted to be affected?
4. What possible negative effects were detected?
5. Which alternatives were tested?
6. Why was this candidate selected?
7. What assumptions does the simulation rely on?
8. How can the citizen respond?

The public layer should be understandable without technical or AI knowledge.

---

# 22. Real Public Feedback

CivicTwin should not reduce public consultation to:

```text
👍 Support
👎 Oppose
```

Structured feedback may include:

- support / acceptance,
- perceived fairness,
- clarity / understanding,
- confidence in implementation,
- expected personal impact.

Qualitative feedback should also be supported.

Example:

> “The simulator does not account for the steep hill between the proposed shuttle stop and our block.”

The system should be capable of turning that into a possible model update:

```text
New constraint:
steep walking route

Potentially affected:
mobility-constrained residents in Zone C
```

This can trigger a recommendation to re-simulate.

---

# 23. Public Confidence Score

Working concept:

# **Public Confidence Score (PCS)**

PCS must be presented as a summary of observed consultation responses, not as objective truth.

Possible dimensions:

```text
PCS =
    w1 * support
  + w2 * perceived_fairness
  + w3 * trust
  + w4 * understanding
```

The dashboard should also expose:

- sample size,
- component metrics,
- subgroup breakdown,
- uncertainty,
- major disagreement clusters.

> **V1 ruling.** PCS is computed and stored, but never rendered without its component
> metrics, the response count, and the subgroup spread on the same screen. This reconciles
> the required capability in §29 with the warning below and in `docs/evaluation.md` §12.
> See [`docs/scenario-v1.md`](./docs/scenario-v1.md) §9 (decision K4).

Do not show only:

```text
Policy Score: 78/100
```

without context.

---

# 24. Simulated vs Real Response

This is one of CivicTwin’s central features.

After public consultation:

```text
Simulated Response
        vs
Observed Response
```

Example:

| Group | Simulated Support | Real Support | Error |
|---|---:|---:|---:|
| Overall | 74% | 71% | -3 |
| Age 65+ | 67% | 48% | -19 |
| Students | 82% | 85% | +3 |
| Zone C | 61% | 55% | -6 |

CivicTwin should be able to state:

> “The simulation substantially overestimated support among residents aged 65+.”

This is useful evidence.

The product should explicitly communicate:

> **Synthetic populations are hypotheses that must be validated against real people.**

---

# 25. Calibration

Real feedback should improve future simulations.

Conceptually:

```text
Synthetic Prediction
        ↓
Real Feedback
        ↓
Prediction Error
        ↓
Calibration Update
        ↓
Future Simulation
```

For V1, calibration may remain intentionally simple.

A sufficient MVP could:

- store predicted and observed metrics,
- compute subgroup error,
- maintain configurable behavioral weights,
- flag poorly calibrated cohorts,
- show calibration history.

Sophisticated online learning is not required for V1.

---

# 26. Explainability

Every major finding and recommendation should be inspectable.

Example impact explanation:

```text
Why was this group flagged?

Route 14 stop removed
    ↓
Walking distance +1.1 km
    ↓
Mobility threshold exceeded
    ↓
Clinic accessibility degrades
```

Example intervention explanation:

```text
Why recommend Peak-Hour Stop Retention?

- reduces severe impact by 63%
- retains most efficiency gains
- lower operational cost than permanent restoration
- benefits the most affected subgroup
```

No important recommendation should exist only as opaque LLM prose.

---

# 27. Human-in-the-Loop Boundary

CivicTwin must not autonomously enact public policy.

Human approval is required before:

- publishing a proposal,
- selecting a final intervention,
- changing high-level policy objective weights,
- treating consultation results as consequential decision inputs,
- presenting simulation outputs as official forecasts.

CivicTwin is a decision-support system.

The policymaker remains responsible for the actual decision.

---

# 28. Safety and Governance Boundaries

CivicTwin is not intended for:

- election manipulation,
- voter persuasion,
- political microtargeting,
- individual-level political influence,
- propaganda optimization,
- automated discrimination,
- automated denial of public services,
- automated policy enactment,
- covert profiling.

Subgroup analysis should be used for **impact auditing and fairness**, not targeting.

Sensitive attributes, when used at all, require care and clear justification.

---

# 29. MVP Capabilities

The V1 prototype should prove the full CivicTwin loop.

Required capabilities:

### Scenario Input
Create or load one public-policy scenario.

### Synthetic Population
Generate or load varied personas.

### Dependency Graph
Represent meaningful relationships between people, services, institutions, or infrastructure.

### Baseline Simulation
Run the proposed policy against the population.

### Impact Analysis
Show aggregate and subgroup outcomes.

### Impact Audit
Automatically surface at least one significant negative or unequal effect.

### Root-Cause Explanation
Show why the effect occurred through a traceable dependency chain.

### Intervention Generation
Generate multiple candidate mitigations or policy alternatives.

### Re-Simulation
Run alternatives through the same simulation engine.

### Scenario Comparison
Compare baseline and alternatives using meaningful metrics.

### Public Consultation
Publish or preview a selected candidate.

### Real Feedback
Collect structured and qualitative responses.

### Public Confidence
Aggregate observed feedback responsibly.

### Calibration
Compare simulated and observed responses.

### Persona Deliberation
Every synthetic resident reasons about the policy as it lands on them, streamed as it is
produced and exportable as evidence. See `docs/scenario-v1.md` §6A.

### Agentic Adaptation
Demonstrate a visible plan → act → observe → adapt cycle.

---

# 30. Reference Demo Story

A strong demo could follow this pattern:

```text
1. A planner proposes a public-policy change.

2. CivicTwin creates or loads a synthetic affected population.

3. The graph-based simulation runs.

4. The policy improves the headline metric.

5. The Impact Auditor discovers that one subgroup experiences severe harm.

6. Root-cause analysis traces the dependency chain causing the issue.

7. CivicTwin proposes multiple interventions.

8. Alternatives are re-simulated.

9. One alternative preserves most of the original benefit while sharply reducing harm.

10. The policymaker publishes that candidate for consultation.

11. Real users submit feedback.

12. Feedback reveals an overlooked real-world constraint.

13. CivicTwin compares simulated and observed responses.

14. The model is flagged as poorly calibrated for one subgroup.

15. The policymaker receives a richer evidence package before making the final decision.
```

This story should fit comfortably within the hackathon demo window.

---

# 31. V1 Non-Goals

Do not attempt to build:

- all public-policy domains,
- Corporate HR simulation,
- education simulation,
- healthcare simulation,
- a national-scale digital twin,
- perfect behavioral science,
- fully autonomous policy optimization,
- election forecasting,
- political persuasion tooling,
- a massive distributed multi-agent system,
- complex reinforcement learning,
- production-grade public identity verification,
- production-grade consultation moderation,
- sophisticated representativeness weighting unless core V1 is already complete.

These are outside the MVP.

---

# 32. Extensibility Model

Future extensibility should come from a reusable environment abstraction.

Conceptually:

```text
EnvironmentPack {
    name
    persona_schema
    node_types
    edge_types
    simulation_rules
    intervention_types
    outcome_metrics
    constraints
    data_sources
    feedback_questions
}
```

V1 should implement only the Public Policy environment needed for the selected scenario.

A plugin marketplace or multiple environment packs are not V1 goals.

---

# 33. Technology Direction

This is directional and may evolve if implementation constraints demand it.

## Backend
- Python
- FastAPI or another lightweight API layer

## Runtime Agent Orchestration
- LangGraph

## LLM
- Claude through Amazon Bedrock

Model strategy:
- cheaper/faster model for frequent structured operations,
- stronger model selectively for difficult reasoning.

## AWS
Where useful:
- Amazon Bedrock
- Lambda
- DynamoDB on-demand
- S3
- Bedrock AgentCore if it materially improves deployment

The hackathon budget is small, so architecture should remain serverless and cost-conscious.

## Graph
For MVP:
- NetworkX or equivalent in-process graph library

A heavyweight graph database is unnecessary unless a concrete need emerges.

## Frontend
Likely:
- React / Next.js
- TypeScript
- graph visualization
- charts
- polished dashboard UI

---

# 34. Simulation Reproducibility

Every simulation run should ideally be identifiable by:

```text
run_id
scenario_id
seed
population_version
policy_version
environment_version
simulation_parameters
model_version
timestamp
outputs
metrics
```

Randomness should support a fixed seed.

Wherever possible, the same scenario, seed, and configuration should produce reproducible results.

---

# 35. Run Evidence

A simulation run should preserve enough information to explain and compare outcomes:

- input policy,
- normalized policy structure,
- population configuration,
- graph snapshot or reference,
- simulation seed,
- state transitions,
- aggregate metrics,
- subgroup metrics,
- generated interventions,
- comparison results,
- feedback aggregates,
- calibration results.

This supports debugging, evaluation, explanation, and demo credibility.

---

# 36. Data Strategy

Prefer:

- public datasets,
- open government data,
- synthetic datasets generated from documented distributions,
- scenario fixtures,
- open transport/demographic/service data where useful.

Synthetic data must be labeled synthetic.

If real data is used:

- document its source,
- document limitations,
- avoid exposing personal data,
- aggregate where possible.

---

# 37. Evaluation Strategy

CivicTwin needs explicit evaluation.

## 37.1 Agentic-System Metrics

Possible metrics:

- structured-output validity,
- intervention validity,
- tool-call success,
- task-completion rate,
- loop completion,
- latency,
- token cost.

## 37.2 Simulation Metrics

Scenario-specific examples:

- severe-harm count,
- subgroup disparity,
- accessibility,
- waiting time,
- capacity overload,
- unmet need,
- travel-time change,
- service reach,
- intervention cost.

## 37.3 Calibration Metrics

Compare simulation with observed public feedback using metrics such as:

- mean absolute error,
- subgroup error,
- support prediction error,
- ranking correlation,
- fairness-perception error.

## 37.4 Graph Ablation

Where feasible:

```text
Independent personas
vs
Graph-connected personas
```

This can test whether explicit network/dependency modeling adds value.

---

# 38. Backtesting

If a suitable historical scenario and outcome dataset can be found, CivicTwin should support backtesting.

Ideal structure:

```text
Known Pre-Change State
        ↓
Known Historical Intervention
        ↓
Run CivicTwin
        ↓
Predicted Outcome
        ↓
Compare
        ↓
Observed Historical Outcome
```

The project should not claim real predictive accuracy without validation.

---

# 39. Hackathon Success Criteria

The submission should score well by demonstrating:

## Benefits
A measurable improvement for affected people.

Examples:
- fewer severely harmed personas,
- reduced subgroup disparity,
- improved accessibility,
- better policy transparency,
- improved public understanding.

## Originality
Core differentiators:
- graph-connected synthetic personas,
- second-order consequence detection,
- agentic intervention search,
- re-simulation,
- real public feedback,
- simulation calibration.

## Effectiveness
One complete public-policy scenario must work end to end.

## Technical Quality
The system should visibly contain:
- a structured simulation,
- graph reasoning,
- bounded agentic orchestration,
- re-simulation,
- clear metrics,
- reproducible runs,
- explainable outputs.

## Presentation
The value should be understandable within the first minute of the demo.

The demo should show rather than merely describe:
- the policy,
- the population,
- the discovered harm,
- the alternative,
- the improved outcome,
- the real-feedback loop.

---

# 40. Demo Priority

When trade-offs are necessary, prioritize capabilities that strengthen the visible CivicTwin story.

High-value demo features include:

- population/network visualization,
- impact propagation,
- affected subgroup highlighting,
- baseline vs alternative comparison,
- root-cause paths,
- public consultation,
- simulated-vs-real comparison,
- calibration error.

Low-value V1 work includes:

- complex account management,
- large generic admin panels,
- many policy domains,
- invisible infrastructure sophistication,
- broad platform features without demo relevance.

---

# 41. Suggested Product Screens

## Policymaker Experience

### Dashboard
- simulations
- status
- high-level metrics
- create scenario

### Scenario Builder
- proposal
- target population
- policy parameters
- objectives
- constraints

### Simulation View
- graph
- timeline
- aggregate outcomes
- subgroup outcomes

### Impact Audit
- affected groups
- severity
- root-cause chains
- anomalies

### Intervention Lab
- generated alternatives
- reruns
- scenario comparison

### Publish
- candidate selection
- public summary
- consultation preview

### Feedback Analysis
- Public Confidence Score
- subgroup breakdown
- qualitative themes
- simulated-vs-real comparison
- calibration warnings

## Citizen Experience

### Proposal Page
- plain-language explanation
- predicted impact
- affected groups
- alternatives tested
- assumptions
- feedback form

---

# 42. Product Claims

Appropriate language:

- stress-test,
- simulate,
- explore,
- estimate,
- identify possible unintended consequences,
- compare scenarios,
- surface trade-offs,
- decision support.

Avoid unsupported claims such as:

- predict exactly,
- guarantee,
- know what citizens will do,
- prove this policy is best,
- replace public consultation,
- replace policymakers.

---

# 43. Key Differentiators

## Versus Traditional Surveys

Traditional consultation captures real opinions but typically evaluates a proposal after it has already been designed.

CivicTwin adds:

- pre-consultation stress testing,
- structured synthetic populations,
- graph-based impact propagation,
- alternative intervention generation,
- re-simulation.

## Versus Traditional Forecasting

Traditional models may estimate aggregate outcomes.

CivicTwin adds:

- persona-level heterogeneity,
- subgroup analysis,
- dependency graphs,
- qualitative explanations,
- public-feedback calibration.

## Versus Generic LLM Chatbots

Chatbots respond to questions.

CivicTwin:

- maintains structured world state,
- runs simulations,
- audits outcomes,
- plans interventions,
- re-simulates,
- compares scenarios,
- learns from observed feedback.

## Versus PropSim-Style Opinion Simulation

The inspiration is networked synthetic agents.

CivicTwin extends:

```text
Simulation → Prediction
```

into:

```text
Simulation
→ Impact Audit
→ Intervention
→ Re-Simulation
→ Public Validation
→ Calibration
```

The goal is not primarily to forecast opinion.

The goal is to **improve a decision before real people bear its consequences**.

---

# 44. Core Research Questions

CivicTwin should help answer:

1. Can graph-connected synthetic populations surface second-order policy effects that independent personas miss?
2. Can an agentic planner generate useful interventions after harmful outcomes are detected?
3. Can re-simulation reduce negative subgroup outcomes while preserving the original policy objective?
4. How closely do simulated responses match real consultation feedback?
5. Which population groups are most poorly calibrated?
6. Can observed feedback improve future simulation quality?
7. Can CivicTwin explain why an outcome occurred, not merely report that it occurred?

---

# 45. Open Product Questions

> **Status.** These are resolved for the locked V1 transport scenario in
> [`docs/scenario-v1.md`](./docs/scenario-v1.md), which fixes the scenario, datasets,
> persona schema, graph relationships, deterministic and probabilistic rules, metrics,
> intervention space, consultation questions, calibration method, and the
> live-versus-precomputed split. Four items remain open — see its §14.1. The list below
> stays as the product-level checklist for any future scenario.

These must be resolved as the prototype is designed:

- Which public-policy scenario is the final V1 demo?
- Which datasets are available?
- What population size is appropriate?
- Which persona fields are essential?
- Which graph relationships materially affect the simulation?
- Which effects are deterministic?
- Which effects are probabilistic?
- Where is Claude genuinely necessary?
- Which metrics define “better off” for the selected scenario?
- Which interventions are valid?
- How should implementation cost be represented?
- How will public feedback be collected?
- How simple can V1 calibration be while remaining meaningful?
- What historical data can support validation or backtesting?
- Which demo steps should be live and which may be deterministic/precomputed?

---

# 46. V1 Acceptance Criteria

The MVP is successful when a reviewer can:

## Scenario
- create or load a public-policy scenario,
- inspect the policy parameters.

## Population
- view a diverse synthetic population,
- inspect individual personas.

## Graph
- see meaningful dependencies between personas and relevant resources/infrastructure.

## Simulation
- run a baseline simulation,
- obtain reproducible results.

## Audit
- see at least one automatically detected subgroup or second-order impact,
- inspect why the impact occurred.

## Intervention
- generate multiple candidate interventions,
- re-simulate them.

## Comparison
- compare baseline and alternatives with meaningful metrics.

## Consultation
- publish or preview a selected proposal,
- submit citizen feedback.

## Feedback
- aggregate structured feedback,
- identify themes from qualitative responses.

## Calibration
- compare simulated response with observed feedback,
- show at least one discrepancy/calibration metric.

## Agentic Behavior
- visibly demonstrate planning, action, observation, and adaptation.

---

# 47. Hackathon Definition of Done

CivicTwin is submission-ready when:

- the end-to-end demo works reliably,
- one public-policy scenario is fully supported,
- baseline and alternative simulations run,
- the system surfaces a meaningful unintended impact,
- intervention generation works,
- scenario comparison is understandable,
- the public feedback loop works,
- simulated-vs-real comparison is visible,
- at least one evaluation result is available,
- the system’s limitations are stated clearly,
- the architecture can be explained in one diagram,
- the demo fits comfortably within the submission time,
- future expansion is presented as roadmap rather than unfinished scope.

---

# 48. North-Star Product Narrative

The final story should remain simple:

> Institutions make decisions that affect large populations, but unintended consequences are often discovered only after rollout.

> CivicTwin lets policymakers test a proposed change against a synthetic, graph-connected population first.

> It identifies who may be left behind, explains why, generates alternative interventions, and re-simulates them.

> The strongest candidate can then be shown to real citizens.

> CivicTwin compares synthetic expectations with real feedback, revealing where its assumptions were wrong and improving future simulations.

> AI does not make the final policy decision.

> **It gives policymakers a safer environment to learn before the public bears the cost of the experiment.**

---

# 49. North-Star Vision

CivicTwin should ultimately make institutional decision-making more:

- anticipatory,
- transparent,
- inclusive,
- evidence-driven,
- explainable,
- adaptive.

Long-term aspiration:

> **Before an important change affects real people, CivicTwin should make it possible to ask: “Who might this hurt, what are we missing, and can we test a better version first?”**

---

# 50. North-Star Metric

A useful long-term conceptual metric is:

# **Prevented Negative Impact**

How much severe or disproportionate negative impact can CivicTwin identify and help reduce **before real-world rollout**?

Supporting metrics may include:

- high-severity population reduction,
- subgroup disparity reduction,
- unintended consequences surfaced,
- intervention improvement,
- calibration error,
- consultation participation,
- public understanding.

---

# 51. Final Scope

For V1:

```text
CivicTwin
   ↓
Public Policy
   ↓
ONE strong policy scenario
```

Not:

```text
CivicTwin
 ├── Government
 ├── HR
 ├── Education
 ├── Healthcare
 ├── NGOs
 └── Everything
```

Those remain future expansion opportunities.

The objective is to prove that the CivicTwin loop is:

- useful,
- technically credible,
- measurable,
- explainable,
- memorable.

The defining sequence is:

```text
SIMULATE
    ↓
FIND WHO IS LEFT BEHIND
    ↓
UNDERSTAND WHY
    ↓
DESIGN A BETTER INTERVENTION
    ↓
RE-SIMULATE
    ↓
ASK REAL PEOPLE
    ↓
LEARN
```

That is CivicTwin.
