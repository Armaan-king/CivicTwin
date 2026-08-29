# CivicTwin — Simulation Model and Rules

> This document defines how CivicTwin should represent synthetic people, graphs, policies, state transitions, interventions, and outputs.  
> It is intentionally separate from the implementation architecture.

---

# 1. Simulation Objective

The purpose of the CivicTwin simulation is not to perfectly predict human behavior.

It is to create a **transparent, testable, heterogeneous synthetic environment** where a proposed public-policy change can be stress-tested for:

- overall effects,
- subgroup effects,
- severe negative consequences,
- dependency cascades,
- bottlenecks,
- second-order effects,
- intervention trade-offs.

The simulation must support comparison between a baseline policy and alternative interventions.

---

# 2. Simulation Philosophy

Use the simplest model that can credibly demonstrate the intended phenomenon.

The simulation should combine:

```text
Structured Personas
        +
Environment State
        +
Dependency Graph
        +
Deterministic Rules
        +
Probabilistic / Behavioral Rules
        +
Selective LLM Reasoning
```

The LLM is not the simulation engine.

---

# 3. Core Simulation Entities

## 3.1 Persona

A persona represents a synthetic affected individual.

Conceptual representation:

```text
Persona {
    id
    attributes
    needs
    constraints
    preferences
    resources
    dependencies
    behavioral_parameters
    current_state
}
```

The selected scenario determines which fields actually matter.

---

# 4. Persona Layers

Each persona should conceptually have four layers.

## 4.1 Identity / Context

Examples:

- age band,
- occupation,
- household type,
- income band,
- district / area,
- employment status,
- student status.

## 4.2 Functional Constraints

Examples:

- mobility limitations,
- work schedule,
- caregiving responsibilities,
- transport access,
- time budget,
- affordability thresholds,
- digital accessibility.

## 4.3 Behavioral Profile

Examples:

- inconvenience tolerance,
- switching propensity,
- trust,
- risk tolerance,
- preference for familiar services,
- responsiveness to peer behavior.

Behavioral attributes should be explicit and scenario-relevant.

## 4.4 Network / Dependencies

Examples:

- household relationships,
- workplace,
- school,
- transport dependency,
- public service dependency,
- caregiver connection,
- neighborhood.

---

# 5. Persona Generation

Personas should preferably be generated from:

1. public distributions,
2. documented synthetic distributions,
3. scenario fixtures,
4. manually designed archetypes for demo testing.

For hackathon V1, a hybrid is acceptable:

```text
Public aggregate data
      +
Synthetic distribution rules
      +
A small number of deliberately designed edge-case personas
```

Edge-case personas are useful for verifying that the simulation catches known failure modes.

---

# 6. Synthetic Population

The population is:

```text
P = {p1, p2, ..., pn}
```

The size should be large enough to expose distributional effects but small enough for fast local simulation.

For V1, likely orders of magnitude:

- hundreds,
- low thousands,
- possibly several thousand if computation remains fast.

Population size is not itself a quality metric.

---

# 7. Dependency Graph

Let:

```text
G = (V, E)
```

Nodes may include:

- personas,
- households,
- locations,
- services,
- transport nodes,
- institutions,
- resources.

Edges represent dependencies or relationships.

Example:

```text
Persona A
  │
  ├── LIVES_IN ──> Zone C
  ├── USES ──────> Bus Stop C
  ├── NEEDS ─────> Clinic
  └── CARES_FOR ─> Persona B
```

Graph relationships should matter to actual outcomes.

---

# 8. Edge Attributes

Edges may store:

- weight,
- distance,
- frequency,
- strength,
- capacity,
- dependency criticality,
- travel time,
- trust,
- direction.

Only include attributes used by the selected scenario.

---

# 9. Policy Representation

A policy should be converted into structured changes.

Conceptual:

```text
PolicyChange {
    id
    objective
    affected_entities
    modifications
    constraints
    rollout_parameters
}
```

Example:

```json
{
  "id": "route_consolidation_v1",
  "objective": "reduce average travel time and operating cost",
  "modifications": {
    "remove_stops": ["B", "C"],
    "add_express_segment": true
  },
  "constraints": {
    "fleet_increase": 0
  }
}
```

---

# 10. Environment State

At timestep `t`:

```text
S_t = {
    persona states,
    graph state,
    resource state,
    service state,
    policy state
}
```

The policy produces an external change:

```text
Δ_t
```

Then:

```text
S_(t+1) = F(S_t, Δ_t, rules, randomness)
```

Not every scenario needs explicit timesteps. If one-pass propagation is sufficient, do not add fake temporal complexity.

---

# 11. Deterministic Rules

Deterministic rules should handle effects that are directly calculable.

Examples:

- route removal changes shortest path,
- walking distance exceeds threshold,
- service capacity is exceeded,
- appointment time conflicts with work,
- eligibility condition is not met,
- required resource is unavailable.

Example:

```python
if new_walking_distance > persona.max_walking_distance:
    persona.accessibility_status = "degraded"
```

These rules should be transparent and testable.

---

# 12. Probabilistic Rules

Some behavior cannot be deterministically inferred.

Example:

```text
Probability of switching to alternative route =
    f(additional_time,
      number_of_transfers,
      familiarity,
      mobility,
      cost)
```

A simple logistic or rule-based probability may be more appropriate than an LLM.

All behavioral parameters should be documented.

---

# 13. Social / Network Influence

For scenarios where behavior spreads through networks:

```text
influence_i(t) =
    Σ_j w_ij * state_j(t)
```

Then:

```text
behavior_i(t+1) =
    f(persona_i,
      intervention,
      environment,
      influence_i(t))
```

Do not include social influence if the selected scenario does not need it.

Dependency graphs are still valuable even without persuasion dynamics.

---

# 14. LLM-Assisted Persona Reasoning

LLM reasoning should be selective.

Appropriate example:

Known facts:

```text
- travel time increased from 22 to 58 minutes
- transfers increased from 1 to 3
- persona has limited mobility
- persona historically avoids multi-transfer journeys
```

LLM task:

> Determine the most plausible qualitative response category and explain which structured facts drove the result.

The LLM should not invent new facts.

Output should use a schema such as:

```text
BehaviorAssessment {
    outcome_category
    likelihood
    contributing_factors
    explanation
}
```

---

# 15. Simulation Event Log

Meaningful state changes should produce events.

Conceptual:

```text
SimulationEvent {
    timestep
    entity_id
    event_type
    before
    after
    cause
}
```

Examples:

- `ROUTE_UNAVAILABLE`
- `TRAVEL_TIME_INCREASED`
- `CAPACITY_EXCEEDED`
- `ACCESSIBILITY_THRESHOLD_EXCEEDED`
- `DEPENDENCY_TRIGGERED`
- `SERVICE_ABANDONED`
- `HOUSEHOLD_SUPPORT_REQUIRED`

These events enable root-cause explanations.

---

# 16. Outcomes

Outcomes should exist at multiple levels.

## 16.1 Persona Outcome

Examples:

- travel time,
- service access,
- cost,
- missed appointments,
- accessibility status,
- inconvenience score.

## 16.2 Subgroup Outcome

Aggregate persona outcomes by meaningful groups.

Examples:

- age band,
- mobility status,
- neighborhood,
- income band,
- caregiver status.

Subgroups should be selected because they matter to the scenario.

## 16.3 System Outcome

Examples:

- average benefit,
- operating cost,
- capacity utilization,
- total severe harm count,
- total service completion.

---

# 17. Severe Impact

CivicTwin should explicitly model high-severity outcomes.

Example:

```text
severity = HIGH if:
    essential_service_access_lost == true
OR
    mobility_threshold_exceeded by large margin
OR
    critical schedule dependency fails
```

Severe impact should not disappear inside average metrics.

---

# 18. Disparity

A simple disparity measure may compare subgroup outcome against overall outcome.

Example:

```text
Disparity(group) =
    Outcome(group) - Outcome(overall)
```

Or compare worst and best groups.

The exact measure should match the selected scenario.

---

# 19. Root-Cause Tracing

Given a harmful outcome, trace through:

1. the policy change,
2. direct graph dependency,
3. state transition,
4. secondary dependency,
5. final impact.

Example:

```text
Stop C removed
    ↓
direct route lost
    ↓
walking distance rises
    ↓
mobility constraint violated
    ↓
clinic access becomes unreliable
```

This trace should be based on recorded events/graph paths.

---

# 20. Intervention Representation

Interventions must be structured.

Conceptual:

```text
Intervention {
    id
    name
    rationale
    changes
    target_problem
    expected_tradeoffs
    estimated_cost
}
```

The intervention should modify the same simulation model as the original policy.

---

# 21. Intervention Generation

The Intervention Planner may use an LLM to propose candidates from:

- detected harm,
- root cause,
- original objective,
- hard constraints.

Example:

```text
Original objective:
reduce route operating cost

Detected harm:
Zone C mobility-constrained residents lose clinic access

Constraints:
no additional full bus route
```

Possible candidates:

- retain one peak-hour stop,
- run limited shuttle,
- reroute an existing feeder service.

---

# 22. Intervention Validation

Before simulation:

- ensure referenced entities exist,
- ensure hard constraints are respected,
- ensure parameters are valid,
- ensure intervention can be applied to environment state.

Do not simulate malformed LLM output.

---

# 23. Re-Simulation

Each intervention should be evaluated under comparable conditions.

Use:

- same population,
- same environment,
- same random seed where appropriate,
- same metric definitions.

This improves fairness of comparison.

---

# 24. Scenario Comparison

For each scenario:

```text
ScenarioResult {
    aggregate_metrics
    subgroup_metrics
    severe_impacts
    cost
    implementation_complexity
}
```

Comparison should expose trade-offs.

Do not collapse everything into one score unless the weights are explicit.

---

# 25. Better-Off Metrics

The exact metrics depend on the scenario.

A generic conceptual objective:

```text
maximize:
    overall_benefit

minimize:
    severe_harm
    disparity
    cost
```

If a combined utility is used:

```text
Utility =
    w1 * OverallBenefit
  - w2 * SevereHarm
  - w3 * Disparity
  - w4 * Cost
```

Weights must be configurable and visible.

---

# 26. Public Consultation Simulation Expectations

Before public consultation, CivicTwin may produce an expected response distribution.

This expected response is not “truth.”

It is a hypothesis generated by the synthetic population.

Example:

```text
Expected:
Overall support = 74%
Age 65+ support = 67%
Zone C support = 61%
```

Observed citizen feedback will later be compared against this.

---

# 27. Real Feedback as New Evidence

A citizen comment may reveal a constraint absent from the model.

Example:

> “The proposed stop is uphill and not practical for wheelchair users.”

Feedback analysis can generate:

```text
DiscoveredConstraint {
    type: terrain_accessibility
    location: Zone C
    affected_group: mobility_constrained
    source: citizen_feedback
}
```

This should not automatically modify the model without review.

It can be proposed as a new scenario input for re-simulation.

---

# 28. Calibration

Let:

```text
ŷ_g = simulated outcome for group g
y_g = observed feedback/outcome for group g
```

Then:

```text
error_g = y_g - ŷ_g
```

V1 may track:

- absolute error,
- signed error,
- mean absolute error,
- subgroup-specific error.

Calibration may update explicit behavioral parameters.

Do not let an LLM silently “learn” new behavior without recording what changed.

---

# 29. Randomness

All stochastic simulation should expose a seed.

Recommended:

```text
seed = scenario_seed
```

Record it with every run.

For scenario comparisons, preserve seed alignment where possible.

---

# 30. Simulation Integrity Rules

The simulator should obey these principles:

1. Do not invent unavailable data during a run.
2. Keep deterministic and probabilistic logic separate.
3. Record material state changes.
4. Keep parameters inspectable.
5. Use stable seeds for testing.
6. Label synthetic outputs clearly.
7. Do not equate simulated personas with real citizens.
8. Do not make unsupported causal claims.
9. Prefer explicit assumptions over hidden model behavior.
10. Keep simulation fast enough for the demo.

---

# 31. Scenario-Specific Configuration

The final V1 scenario should eventually define:

```text
persona schema
population distribution
graph schema
policy schema
hard rules
behavior rules
intervention types
metrics
severity thresholds
feedback questions
calibration targets
```

These details should be added to this file once the scenario is selected.

> **Status.** The V1 scenario is locked as Singapore public-bus stop rationalisation.
> All of the above are specified in [`scenario-v1.md`](./scenario-v1.md), which is the
> canonical source for the transport scenario. Where §32 below and `scenario-v1.md`
> disagree, `scenario-v1.md` wins.

---

# 32. Candidate V1 Example: Transport Policy

This remains an example, not a final commitment.

Possible persona fields:

- home zone,
- age,
- occupation,
- mobility,
- work start time,
- household role,
- primary transport mode,
- max walking distance,
- transfer tolerance.

Graph:

```text
Person → Household
Person → Stop
Stop → Route
Route → Station
Person → Workplace
Person → Clinic
Person → School
```

Policy:

> Remove two stops and introduce an express segment.

Metrics:

- average travel time,
- severe access loss,
- walking distance,
- missed critical trips,
- subgroup disparity,
- operating cost.

This scenario is attractive because the effects are intuitive and highly visual.

---

# 33. Future Simulation Extensions

Not required for V1:

- agent-based simulation frameworks,
- discrete-event simulation engines,
- Monte Carlo sensitivity analysis,
- multi-objective optimization,
- learned behavioral models,
- graph neural networks,
- reinforcement learning,
- live infrastructure feeds.

Coding agents may recommend such tools only when they solve a concrete emerging need.
