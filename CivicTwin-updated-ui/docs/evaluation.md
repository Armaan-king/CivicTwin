# CivicTwin — Evaluation and Validation Plan

> This document defines how CivicTwin should be evaluated as a technical system and as a policy stress-testing prototype.

---

# 1. Evaluation Objective

CivicTwin must be evaluated on more than whether the demo “looks intelligent.”

The project should provide evidence for four questions:

1. **Does the system function reliably?**
2. **Does the simulation reveal meaningful differences across people/groups?**
3. **Can the agentic intervention loop improve outcomes under the configured objective?**
4. **How well do synthetic expectations align with real or historical evidence?**

---

# 2. Evaluation Layers

Use four distinct layers:

```text
A. Runtime / Agent Reliability
B. Simulation Quality
C. Intervention Effectiveness
D. Real-World Calibration / Validation
```

Each answers a different question.

---

# 3. Runtime / Agent Reliability

These metrics evaluate the software and agent orchestration.

Possible metrics:

| Metric | Meaning |
|---|---|
| Schema validation rate | % of runtime-agent outputs that pass typed validation |
| Tool-call success rate | % of tool/service calls that complete successfully |
| Workflow completion rate | % of end-to-end runs that finish without manual repair |
| Intervention validity rate | % of generated interventions that pass validator |
| Retry count | Number of model/tool retries per run |
| Latency | Time per agent step and total workflow |
| Token usage | LLM tokens consumed per workflow |
| Estimated cost | Approximate Bedrock cost per run |
| Loop discipline | Iterations before completion / hard-cap breaches |

The hackathon should show a small number of concrete measurements rather than an enormous benchmark suite.

---

# 4. Simulation Quality

Simulation quality is scenario-specific.

Potential metrics include:

- average outcome,
- median outcome,
- worst-decile outcome,
- severe-harm count,
- subgroup disparity,
- accessibility,
- waiting time,
- travel time,
- unmet need,
- capacity overload,
- service completion,
- adoption rate.

The final selected scenario should define a compact metric set.

> **Ruling (V1 transport scenario).** The canonical metric set is the six metrics
> fixed in [`scenario-v1.md`](./scenario-v1.md) §7 (decision I1). The list above is a
> menu to select from, not a set to implement. Where this document, `simulation.md`,
> and `goal.md` list overlapping metric families, `scenario-v1.md` wins for the
> transport scenario.

---

# 5. Distributional Evaluation

CivicTwin’s core thesis depends on the idea that averages can hide harm.

Therefore every simulation should report:

```text
Overall Metric
+
Subgroup Metrics
+
Worst-Affected Cohorts
+
High-Severity Cases
```

Example:

```text
Average travel time: -4%

Age 65+: +22%
Mobility-constrained: +31%
Zone C: +38%

Severe accessibility loss: 143 personas
```

This is more important than maximizing one average score.

---

# 6. Graph Value Evaluation

One important research question is whether the graph adds value.

Where feasible, run an ablation:

## Model A
Independent personas with no dependency propagation.

## Model B
Graph-connected personas with dependencies.

Compare:

- number of second-order effects detected,
- outcome distribution,
- historical fit if available,
- qualitative plausibility,
- root-cause explainability.

A good result would show that the graph reveals consequences that isolated personas miss.

---

# 7. Intervention Effectiveness

For each generated candidate, compare against baseline.

Example:

| Metric | Baseline | Intervention |
|---|---:|---:|
| Avg benefit | 72 | 79 |
| Severe harm | 143 | 41 |
| Vulnerable subgroup disparity | 15% | 5% |
| Relative cost | 1.00x | 1.12x |

Useful derived measures:

```text
Severe Harm Reduction =
    (baseline_harm - intervention_harm) / baseline_harm
```

```text
Disparity Reduction =
    baseline_disparity - intervention_disparity
```

The system should show whether the intervention improves outcomes while preserving the original policy objective.

---

# 8. Intervention Quality

Generated interventions should be evaluated for:

- validity,
- relevance to detected root cause,
- compatibility with policy constraints,
- simulation feasibility,
- diversity,
- cost awareness.

A simple hackathon metric:

```text
Intervention Validity Rate =
valid_interventions / generated_interventions
```

Human review can also score relevance on a small sample.

---

# 9. Root-Cause Explanation Quality

The system should not merely generate convincing prose.

An explanation should be supported by recorded evidence.

Possible evaluation:

For each flagged impact:

- does a graph/event path exist?
- does the explanation mention only facts present in the run?
- does the path terminate in the reported outcome?
- can a reviewer inspect the supporting data?

A useful metric:

```text
Grounded Explanation Rate =
supported_explanations / audited_explanations
```

---

# 10. Reproducibility

For deterministic or seeded runs:

```text
same scenario
+ same policy
+ same population version
+ same seed
+ same parameters
→ same or acceptably equivalent result
```

Test:

- repeated runs,
- metric equality/tolerance,
- intervention comparison stability.

---

# 11. Calibration Against Real Feedback

This is one of CivicTwin’s strongest evaluation opportunities.

For group `g`:

```text
simulated_g = predicted response
observed_g = actual consultation response
```

Error:

```text
error_g = observed_g - simulated_g
```

Useful metrics:

### Mean Absolute Error

```text
MAE = mean(|observed_g - simulated_g|)
```

### Subgroup Error

Report error by cohort.

### Reasoning versus baseline

Both the logistic (**L1**) and the per-persona assessment (**P1**) predict support, so
calibration reports the error of each against observed responses.

```text
MAE(logistic)   vs   MAE(reasoning)
```

A structured curve beating a language model on a cohort, or losing to it, is a result worth
reporting either way. It is also the cheapest evidence that the reasoning pass earns its
runtime.

### Signed Bias

Useful for showing consistent over- or under-estimation.

Example:

| Group | Simulated | Real | Error |
|---|---:|---:|---:|
| Overall | 74% | 71% | -3 |
| Age 65+ | 67% | 48% | -19 |
| Students | 82% | 85% | +3 |
| Zone C | 61% | 55% | -6 |

The important insight may be:

> The model is fairly close overall but badly calibrated for one subgroup.

That is exactly the kind of hidden error CivicTwin should reveal.

---

# 12. Public Confidence Score Evaluation

If CivicTwin uses a Public Confidence Score, never evaluate only the headline score.

Track components such as:

- support,
- perceived fairness,
- understanding,
- trust/confidence,
- expected personal impact.

Also report:

- response count,
- subgroup response count,
- disagreement,
- missing data,
- sample limitations.

The score should not imply statistical representativeness unless representativeness has actually been established.

> **Ruling (V1).** PCS is computed and stored, but the UI must never render the
> headline score without its component metrics, the response count, and the subgroup
> spread on the same screen. The score is a way into the components, never a verdict.
> This reconciles the required "Public Confidence" capability in `goal.md` §29 with
> the warning against bare scores in `goal.md` §23 and §12 above.
> See [`scenario-v1.md`](./scenario-v1.md) §9 (decision K4).

---

# 13. Qualitative Feedback Evaluation

The Feedback Analyst may extract:

- themes,
- concerns,
- new constraints,
- affected groups.

A small manually labeled test set can evaluate:

- theme classification accuracy,
- constraint extraction correctness,
- hallucination rate.

For hackathon scale, even 20–50 labeled example comments may be enough to demonstrate method.

---

# 14. Backtesting

If historical policy data exists, backtesting is highly valuable.

Workflow:

```text
Historical Pre-Change State
        ↓
Historical Policy Change
        ↓
Run CivicTwin Without Using Outcome
        ↓
Synthetic Predicted Outcome
        ↓
Compare
        ↓
Observed Historical Outcome
```

Potential metrics:

- aggregate error,
- subgroup error,
- ranking correlation,
- direction-of-change accuracy.

Do not tune on the test outcome and then present the same outcome as independent validation.

---

# 15. Baselines

Useful baselines may include:

### Baseline 1 — Aggregate-only model
No personas, only average assumptions.

### Baseline 2 — Independent personas
Personas exist but no graph dependencies.

### Baseline 3 — No intervention agent
Detect harm but do not generate alternatives.

CivicTwin should demonstrate what each additional layer contributes.

Not every baseline is mandatory for the hackathon.

---

# 16. Sensitivity Analysis

If time allows, vary important simulation assumptions.

Examples:

- behavioral thresholds,
- adoption probabilities,
- graph edge strengths,
- population composition.

Question:

> Does the recommendation completely change under small parameter variation?

If yes, CivicTwin should surface that uncertainty.

A robust recommendation should not depend on a tiny hidden parameter change.

---

# 17. Uncertainty

CivicTwin should distinguish:

- deterministic results,
- stochastic estimates,
- LLM-generated qualitative judgments.

Where multiple stochastic runs are used, report:

- mean,
- range,
- confidence interval if appropriate.

Do not fake statistical confidence when only one synthetic run exists.

---

# 18. Fairness / Distributional Checks

Because the platform analyzes public impact, evaluation should include:

- worst-affected subgroup,
- disparity before/after intervention,
- whether one group’s improvement comes at extreme cost to another,
- severe-impact count.

The goal is not to enforce a universal fairness formula.

The goal is to make distributional trade-offs visible.

---

# 19. Performance Evaluation

Measure:

- population size,
- simulation time,
- alternative count,
- total workflow latency,
- frontend response time.

For the demo, target a simulation that feels interactive.

If a realistic full run is too slow, use precomputed results only as a fallback and keep the actual simulation implementation available.

---

# 20. Cost Evaluation

Record approximate:

- LLM calls per run,
- tokens,
- Bedrock cost,
- AWS service cost where measurable.

The project should be able to explain why it does not call a powerful model for every persona at every timestep.

---

# 21. Demo Evaluation Dataset

The team should maintain a deterministic demo fixture.

Recommended fixture contents:

```text
scenario
population seed
persona distribution
graph
baseline policy
known vulnerable cohort
known candidate interventions
sample citizen feedback
expected metric ranges
```

This fixture ensures demo repeatability.

---

# 22. Unit Tests

Prioritize deterministic logic:

- schema validation,
- persona generation constraints,
- graph construction,
- path/dependency analysis,
- state transition rules,
- metric calculations,
- intervention validation,
- calibration formulas.

---

# 23. Integration Tests

At least a few tests should cover:

```text
Policy
→ Scenario
→ Simulation
→ Audit
→ Intervention
→ Re-Simulation
→ Comparison
```

Use mocked Bedrock responses where appropriate.

The test suite should not require live AWS access.

---

# 24. End-to-End Test

One deterministic end-to-end test should verify the main CivicTwin loop.

Example assertion set:

```text
baseline simulation completes
harmful subgroup detected
root cause exists
>= 2 valid interventions generated
alternative simulation completes
at least one alternative reduces harm
consultation can be created
feedback can be submitted
calibration metric can be computed
```

---

# 25. Hackathon Evaluation Story

The final presentation should ideally show a compact evidence chain:

```text
1. Baseline policy:
   overall metric improves.

2. CivicTwin discovers:
   subgroup harm.

3. Graph trace explains:
   why.

4. Agent proposes:
   multiple interventions.

5. Re-simulation shows:
   harm reduced by X%.

6. Public feedback reveals:
   a real constraint or disagreement.

7. Calibration shows:
   synthetic expectation error for subgroup Y.
```

This demonstrates:

- benefit,
- technical depth,
- agentic behavior,
- transparency,
- adaptation.

---

# 26. Results Reporting Template

For each experiment:

```text
Experiment:
Question:
Scenario version:
Population version:
Seed:
Policy:
Intervention:
Metrics:
Result:
Interpretation:
Limitations:
```

This keeps evaluation reproducible.

---

# 27. Limitations Section

The final project should openly state:

- synthetic people are not real people,
- behavioral assumptions may be wrong,
- real consultation samples may be unrepresentative,
- public data may be incomplete,
- graph structure may omit important relationships,
- observed correlation is not necessarily causation,
- the system supports decisions rather than replacing policymakers.

Acknowledging these limits makes the project more credible.

---

# 28. Minimum Evaluation Required for V1

Before submission, aim to have at least:

1. one deterministic end-to-end scenario,
2. one baseline vs intervention comparison,
3. one subgroup disparity result,
4. one graph-based root-cause explanation,
5. one runtime reliability metric,
6. one simulated-vs-observed calibration example,
7. one clearly stated limitation,
8. one graph-vs-independent-persona ablation result.

Anything beyond that is a bonus.

> **Ruling (V1).** Item 8 was previously filed under §29 Stretch Evaluation. It is
> promoted to required: it costs one configuration flag and one extra run, and it is
> the only direct evidence for the core research question in §6 and `goal.md` §44.1
> ("can graph-connected synthetic populations surface second-order effects that
> independent personas miss?"). See [`scenario-v1.md`](./scenario-v1.md) §12
> (decision N2).

---

# 29. Stretch Evaluation

If time remains:

- historical backtest,
- sensitivity analysis,
- multiple stochastic seeds,
- qualitative feedback benchmark,
- intervention human-rating study.

These should not block the MVP.
