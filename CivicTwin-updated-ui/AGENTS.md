# AGENTS.md — CivicTwin Repository Instructions

> This file contains instructions for coding agents such as Claude Code, Codex, and other autonomous development tools working in the CivicTwin repository.
>
> Product goals, scope, user journeys, product architecture, acceptance criteria, and non-goals are defined in `goal.md`.
>
> **Read `goal.md` before making product or architectural decisions.**

---

## 1. Instruction Priority

When working in this repository:

1. Preserve the product intent in `goal.md`.
2. Follow the locked scenario specification in `docs/scenario-v1.md` for anything touching the
   V1 transport scenario. It is canonical: where it and `docs/simulation.md`,
   `docs/architecture.md`, or `docs/evaluation.md` disagree on a transport detail,
   `scenario-v1.md` wins. Where it conflicts with `goal.md`, `goal.md` wins.
3. Follow the existing repository architecture unless there is a clear reason to improve it.
4. Prefer a reliable end-to-end hackathon demo over broad feature coverage.
5. Do not expand V1 beyond the Public Policy vertical and the locked scenario unless explicitly instructed.
6. Do not silently change product assumptions that are identified as open questions in `goal.md`, or
   decisions marked LOCKED in `docs/scenario-v1.md`.

If implementation details conflict with product goals, product goals win.

---

## 2. General Working Style

Before changing code:

- inspect the repository,
- understand existing modules and conventions,
- identify the smallest coherent change,
- check relevant tests,
- avoid unnecessary rewrites.

Prefer incremental changes over large speculative refactors.

Do not create architecture merely because it may be useful later.

Do not add empty abstractions, placeholder modules, or premature plugin systems unless they serve the current MVP.

---

## 3. Decision Heuristics

When several implementations are viable, prefer the option that is:

1. easier to explain,
2. easier to demo,
3. easier to test,
4. modular without being over-engineered,
5. consistent with the CivicTwin core loop.

**Determinism is no longer a tie-breaker.** V2 simulates the population with reasoning
agents (`goal.md` §15), so a preference for deterministic implementations would argue
against the architecture. What replaced it as the safeguard is *groundedness*: an agent
may only reason from facts it was given, and a conclusion citing anything else is rejected
rather than displayed.

Conventional algorithms are still right for **retrieving world facts** — distances,
nearest stops, who is in which household. They are no longer used to decide consequences.

---

## 4. Scope Discipline

The V1 scope is:

```text
CivicTwin
   ↓
Public Policy
   ↓
ONE strong scenario
```

Do not independently add:

- Corporate HR,
- Education,
- Healthcare,
- NGO environments,
- multiple complete policy domains,
- nation-scale simulation,
- complex reinforcement learning,
- unnecessary distributed systems.

Future extensibility may influence clean interfaces, but should not dominate the MVP.

---

## 5. Product-Agent vs Coding-Agent Terminology

The repository contains **runtime agents** that are part of CivicTwin itself, such as:

- Policy Interpreter,
- Impact Auditor,
- Intervention Planner,
- Feedback Analyst.

Those are product concepts defined in `goal.md`.

This file governs **coding agents** working on the repository.

Do not confuse the two.

---

## 6. Code Quality

Prefer:

- typed interfaces,
- explicit data models,
- small modules with clear responsibilities,
- deterministic business logic,
- meaningful names,
- focused functions,
- clear error handling.

Avoid:

- giant prompt-driven functions,
- business rules hidden inside prose prompts,
- fragile string parsing,
- duplicated domain logic,
- silent exception swallowing,
- unexplained magic constants.

Where Python is used, use Pydantic or equivalent typed schemas for structured agent outputs when appropriate.

---

## 7. Structured Agent Outputs

Any runtime-agent output that drives program logic should use a defined schema.

Examples include:

- normalized policy changes,
- impact findings,
- interventions,
- validation results,
- feedback classifications,
- calibration results.

Do not make critical application behavior depend on parsing unconstrained prose.

Human-facing explanations may be natural language, but machine-facing outputs should be structured.

---

## 8. Agent Simulation

The population is simulated by reasoning agents. Each resident decides for itself what a
policy does to it, in rounds, having seen what its neighbours concluded in the round
before.

**This reverses the previous rule in this section**, which forbade an LLM call per citizen
per round. That prohibition was correct for a rules engine with a narration layer on top.
It is wrong for a deliberation, and it kept the product's central feature switched off.

What is required instead:

- **Ground every conclusion.** An agent is given its own record, the world facts around it,
  and its neighbours' last positions. It may reason only from those. A conclusion citing a
  fact it was not given is rejected and counted, never rendered.
- **Look facts up, do not reason them out.** Distances, which stop closed, who lives with
  whom: retrieved and handed to the agent. A model asked to compute a distance will invent
  a plausible one.
- **Bound the rounds.** Four. Unbounded deliberation is how an agent system becomes a bill.
- **Batch.** Residents per call, not a call per resident.
- **Cache by content hash.** Same resident, same facts, same neighbours, same prompt: no
  second call. A replay of a run costs nothing.
- **Record what a run cost.** Calls, tokens, latency, cache hits, rejected conclusions.

What stays banned is the unbounded shape: every resident, every round, uncached, with no
ceiling and no record of what it cost.

## 9. Reproducibility

Agent runs are **not bit-reproducible, and the write-up must say so.** Two runs of the
same policy will differ. What is guaranteed instead:

- a **replay** is exact, because it is served from the content-hash cache,
- the **world state** is fully reproducible from the seed: same residents, same network,
  same social graph, every time,
- every conclusion carries the facts it was reasoned from, so a result can be *explained*
  even when it cannot be re-derived.

Runs should preserve enough metadata to replay or explain results.

Where applicable, record:

- run ID,
- scenario ID,
- random seed,
- policy version,
- population version,
- environment version,
- simulation parameters,
- model identifier,
- metrics.

Tests involving stochastic behavior should use fixed seeds.

---

## 10. LLM Usage

Preferred hackathon path:

- Claude via Amazon Bedrock.

Use cheaper models for frequent structured tasks where sufficient.

Use stronger models selectively for tasks such as:

- difficult policy interpretation,
- intervention reasoning,
- explanation generation.

Do not use LLMs for:

- arithmetic,
- shortest-path calculations,
- distance and geometry,
- data aggregation,
- counting outcomes into metrics.

These are all **world facts and tallies**. They are retrieved or counted and handed to the
agents, who then decide what they mean. Judging consequence, severity, adaptation and
opinion is exactly what the agents are for, and that judgement is no longer to be moved
back into code.

Prompts should be centralized or versioned where practical.

---


## 10A. Framework and Library Recommendations

Coding agents should proactively suggest frameworks, libraries, SDKs, and developer tools when they would materially improve the implementation.

Recommendations should be made when they can help with:

- reliability,
- development speed,
- testing,
- observability,
- graph processing,
- simulation,
- agent orchestration,
- structured outputs,
- visualization,
- data handling,
- deployment,
- cost control,
- demo quality.

When suggesting a framework or library:

1. Explain the concrete problem it solves in CivicTwin.
2. Prefer mature, actively maintained, well-documented options.
3. Prefer lightweight dependencies over heavyweight platforms when both solve the problem adequately.
4. Consider compatibility with the existing stack before recommending a new dependency.
5. Consider hackathon time, learning curve, runtime cost, and deployment complexity.
6. Avoid adding a dependency solely because it is popular or technically impressive.
7. Distinguish between:
   - **recommended now**,
   - **useful if a specific need appears**,
   - **future/production-scale option**.
8. If the existing implementation is already simpler and sufficient, say so rather than recommending unnecessary migration.
9. Before introducing a major framework, database, infrastructure service, or architectural dependency, explain the trade-offs and get explicit approval if it would materially change the project architecture.
10. When several reasonable options exist, compare them briefly and recommend one.

Examples of areas where suggestions may be useful:

- graph algorithms and network analysis,
- agent orchestration,
- simulation/event engines,
- schema validation,
- state management,
- graph/network visualization,
- charts and dashboards,
- API frameworks,
- testing,
- observability and tracing,
- caching,
- AWS deployment,
- dataset processing.

The objective is not to minimize dependencies at all costs. The objective is to use **the smallest set of high-value tools that makes CivicTwin faster to build, easier to understand, more reliable, and more impressive to demonstrate**.

## 10B. Reference Repositories

Two external repositories are referenced as prior art and analysed in
`docs/architecture.md` section 22:

- **PropSim** (`derekmu8/propsim`) - the origin of the CivicTwin idea. Orchestration and
  streaming patterns are adopted; its LLM-per-agent-per-round engine is deliberately not.
- **Cortexia** (`yajat009/Cortexia`) - frontend inspiration only, specifically its
  human-figure population rendering.

**Neither repository carries a LICENSE file, so both are all-rights-reserved by default.**

- Read them, learn the architecture, reimplement the pattern.
- **Never copy source code, prompt text, or configuration from either repository into this
  project**, including partial functions or lightly edited variants.
- Do not add either as a dependency, submodule, or vendored directory.

Where a pattern from one of them is used, `docs/architecture.md` section 22 records what was
taken and what was rejected. Extend that section rather than reintroducing the discussion
elsewhere.

## 11. Cost Constraints

The hackathon AWS budget is limited.

Prefer:

- Amazon Bedrock on demand,
- Lambda,
- DynamoDB on demand,
- S3,
- local/in-process graph computation.

Avoid without explicit justification:

- always-on EC2,
- RDS,
- NAT Gateway,
- load balancers,
- OpenSearch,
- provisioned throughput,
- long-lived expensive endpoints,
- an **expensive** model on the per-resident deliberation. That pass is the bulk of the
  spend, so it runs on the cheap model, batched, bounded to four rounds, and cached by
  content hash. Reserve the strong model for the few calls that need it: interpreting a
  policy, and writing the explanation a human reads.
- any agent loop without a round ceiling and a recorded cost.

Cache or reuse results where appropriate.

---

## 12. Graph Implementation

For the MVP, prefer a lightweight in-process graph such as NetworkX unless requirements clearly demand otherwise.

The population/dependency graph must affect real application logic.

Do not build a graph visualization that has no connection to the simulation or impact-analysis pipeline.

Do not introduce a heavyweight graph database solely for perceived sophistication.

---

## 13. LangGraph

If LangGraph is used:

- keep nodes single-purpose,
- keep shared state typed and explicit,
- make conditional routing understandable,
- bound all loops,
- prevent uncontrolled agent recursion,
- store large artifacts outside prompt state when appropriate.

The execution graph should be explainable from a single diagram.

---

## 14. Human-in-the-Loop

Preserve human approval boundaries defined in `goal.md`.

Do not implement autonomous enactment of policy decisions.

Require explicit human action before consequential steps such as publication or final selection where the product flow expects it.

---

## 15. Safety and Product Boundaries

Do not add functionality for:

- election manipulation,
- voter persuasion,
- political microtargeting,
- propaganda optimization,
- automated denial of public services,
- covert profiling,
- discriminatory targeting.

If a feature materially changes these boundaries, stop and request explicit product direction rather than assuming.

---

## 16. Data Handling

Prefer public, open, or synthetic data.

For any external dataset:

- document the source,
- preserve licensing/source notes when relevant,
- document assumptions,
- do not fabricate provenance.

Synthetic data must be clearly labeled as synthetic.

Do not expose personally identifiable information.

---

## 17. Secrets and Environment Variables

Never hard-code credentials.

Keep secrets in environment variables.

Maintain:

- `.env.example`
- `.gitignore`

Do not commit `.env`.

Do not print credentials into logs.

AWS access credentials may expire and should not be treated as permanent configuration.

---

## 18. Error Handling

Failures should be visible and diagnosable.

Prefer:

- explicit validation failures,
- useful error messages,
- bounded retries,
- clear fallback behavior.

Avoid silently converting a failed agent/tool call into apparently valid output.

If an LLM call fails, the application should fail gracefully or use an explicit fallback.

---

## 19. Observability

Where practical, capture:

- runtime agent invoked,
- model used,
- tool calls,
- latency,
- token usage,
- retry count,
- validation errors,
- loop iterations,
- simulation duration,
- run status.

Observability should support debugging and hackathon evaluation without becoming an infrastructure project of its own.

---

## 20. Testing Priorities

Prioritize tests for the parts that are still deterministic, because the agents are not:

- persona schema validation,
- world-fact retrieval: distances, nearest stop, what a closure removes,
- graph construction and dependency direction,
- metrics and aggregation over agent outputs,
- intervention validation,
- calibration calculations.

And, above all, the **groundedness guard**: an agent conclusion citing a fact it was not
given must be rejected. Test it by planting one. A guard nobody has watched fail is not a
guard.

For runtime-agent behavior:

- validate schemas,
- test failure paths,
- mock model calls where appropriate,
- keep a small number of integration tests for real agent flows.

**A mock must not be able to stand in for a run.** Mocked deliberation is for exercising
plumbing. It may never produce output that reaches a screen looking like resident
reasoning: without a model the run fails loudly. This rule exists because the opposite was
built, and a whole feature sat switched off behind a silent fallback while appearing to
work.

Do not make the entire test suite dependent on live Bedrock access.

---

## 21. Evaluation Support

Where practical, preserve artifacts that allow the team to compute:

- schema-validation rate,
- intervention-validity rate,
- tool success,
- task completion,
- latency,
- token cost,
- subgroup outcomes,
- calibration error.

Do not invent evaluation results.

If a result is based on synthetic fixtures rather than real validation, label it clearly.

---

## 22. Demo Reliability

The hackathon demo is a first-class engineering requirement.

The critical path should:

- work reproducibly,
- avoid unnecessary external dependencies,
- have graceful fallbacks,
- complete within a short time,
- avoid expensive or slow loops.

A cached run may be replayed for demo reliability, and should be: the content-hash cache
makes a replay exact and free. What may **not** happen is generating substitute text when
no model is available. A replay is a real run shown again; a template is a fake, and the
line between them is not a matter of labelling.

---

## 23. UI Priorities

Prioritize screens that make the CivicTwin loop visible:

- policy input,
- population view,
- graph propagation,
- impact audit,
- intervention comparison,
- public consultation,
- feedback/calibration comparison.

Do not spend disproportionate time on:

- complex authentication,
- settings,
- generic admin pages,
- unrelated dashboard widgets.

The UI should make the core story obvious without requiring a technical explanation.

---

## 24. Repository Organization

Follow the repository’s existing layout.

If starting from a minimal repository, a reasonable direction is:

```text
/
├── goal.md
├── AGENTS.md
├── README.md
├── .env.example
├── backend/
├── frontend/
├── data/
├── tests/
├── scripts/
└── docs/
```

Do not create directories until they have a real purpose.

Architecture-specific documentation may live under `docs/` once needed.

---

## 25. Documentation Boundaries

Use:

- `goal.md` for product goals, scope, product architecture, success criteria, and non-goals.
- `AGENTS.md` for instructions to coding agents.
- `README.md` for installation, setup, running, and high-level repository overview.
- `docs/architecture.md` for detailed implementation architecture if needed.
- `docs/simulation.md` for simulation rules/modeling details if needed.
- `docs/evaluation.md` for evaluation methodology/results if needed.

Avoid turning `goal.md` into a coding handbook.

Avoid turning `AGENTS.md` into a product-spec duplicate.

---

## 26. Change Discipline

Do not rewrite entire modules unless necessary.

Before a significant refactor:

1. identify the concrete problem,
2. inspect dependent modules,
3. preserve behavior,
4. update tests,
5. keep the change scoped.

Do not introduce a new framework solely because it is fashionable.

---

## 27. Open Product Questions

If work requires resolving a product question listed as open in `goal.md`, do not silently make a permanent decision unless the answer is obvious from existing code or explicit instructions.

Prefer:

- implementing behind a configurable interface,
- recording the assumption,
- or asking for direction when the decision materially changes product behavior.

---

## 28. Mocking and Placeholders

Mock integrations are acceptable during hackathon development when a real integration is unavailable.

However:

- mark mocked data clearly,
- keep interfaces realistic,
- do not describe a mocked external API as live,
- do not fabricate third-party access.

A mock should help prove the product flow without creating a false claim.

---

## 29. Definition of a Good Change

A good repository change should improve one or more of:

- the end-to-end CivicTwin loop,
- simulation quality,
- graph reasoning,
- impact detection,
- intervention generation,
- explainability,
- public feedback,
- calibration,
- evaluation,
- demo reliability.

If a proposed change does none of these, question whether it belongs in V1.

---

## 30. Final Coding-Agent Rule

The repository should converge toward a **small, reliable, measurable, explainable CivicTwin prototype**, not toward the largest architecture possible.

Keep the product sequence recognizable:

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

Everything else is secondary.
