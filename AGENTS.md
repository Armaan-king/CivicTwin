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

1. more deterministic,
2. easier to test,
3. cheaper to run,
4. easier to explain,
5. easier to demo,
6. less likely to hallucinate,
7. modular without being over-engineered,
8. consistent with the CivicTwin core loop.

Use an LLM only when language understanding or qualitative reasoning materially improves the system.

Prefer conventional algorithms for deterministic calculations.

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

## 8. Simulation Rules

Simulation logic must remain inspectable.

Where possible:

- use fixed random seeds,
- separate deterministic rules from probabilistic behavior,
- keep behavioral parameters explicit,
- record the configuration of each run,
- avoid hidden state changes.

Do not simulate every citizen by making an LLM call on every timestep.

**Explicitly required, and therefore permitted:** one reasoning pass per persona, plus
re-reasoning only for personas whose state actually changed in a later round. That is
`scenario-v1.md` §6A, roughly 2,040 calls for a 2,000-persona run rather than 8,000. It is
cached by content hash so a replay costs nothing. What stays banned is the unbounded shape:
every persona, every round, uncached.

The default assumption is that most population evolution should be performed using normal Python logic, graph algorithms, probabilities, and rules.

Use LLM reasoning selectively.

---

## 9. Reproducibility

Simulation runs should preserve enough metadata to reproduce or explain results.

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
- capacity calculations,
- deterministic threshold checks,
- data aggregation,
- metrics that normal code can compute more reliably.

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
- one *expensive-model* call per simulated citizen. The per-persona reasoning pass in
  `docs/scenario-v1.md` §6A uses the cheap model, is bounded at roughly one call per
  resident, and is cached by content hash.

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

Prioritize tests for deterministic logic:

- persona schema validation,
- graph construction,
- graph dependency operations,
- simulation transitions,
- metrics,
- intervention validation,
- scenario comparison,
- calibration calculations.

For runtime-agent behavior:

- validate schemas,
- test failure paths,
- mock model calls where appropriate,
- keep a small number of integration tests for real agent flows.

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

When live generation is risky but the underlying feature is already implemented, deterministic cached fixtures may be used as a fallback for demo reliability, provided this is not presented dishonestly as a fresh model output.

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
