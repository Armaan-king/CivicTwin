# CivicTwin

> **Stress-test change before people live with the consequences.**

CivicTwin is an agentic AI platform for stress-testing proposed public-policy changes against a graph-connected synthetic population before those changes reach the real world.

The system simulates how a policy may affect different people, identifies unintended or unequal consequences, proposes alternative interventions, re-simulates those alternatives, and then allows a selected proposal to be exposed to real users through a public consultation dashboard. Real feedback can then be compared with simulated expectations to identify model error and improve future calibration.

---

## Project Status

**Current stage:** Hackathon MVP / V1  
**Primary vertical:** Public Policy  
**Implementation scope:** One strong public-policy scenario  
**Long-term vision:** A reusable decision digital-twin platform for multiple institutional environments

The current product direction is defined in [`goal.md`](./goal.md).

Coding-agent instructions are defined in [`AGENTS.md`](./AGENTS.md).

---

## Core Product Loop

```text
POLICY PROPOSAL
      ↓
SYNTHETIC POPULATION
      ↓
DEPENDENCY / SOCIAL GRAPH
      ↓
SIMULATION
      ↓
IMPACT AUDIT
      ↓
ROOT-CAUSE ANALYSIS
      ↓
ALTERNATIVE INTERVENTIONS
      ↓
RE-SIMULATION
      ↓
SCENARIO COMPARISON
      ↓
PUBLIC CONSULTATION
      ↓
REAL FEEDBACK
      ↓
CALIBRATION
```

CivicTwin is not intended to be a one-shot chatbot or a system that autonomously decides public policy.

It is a **decision-support and policy stress-testing platform**.

---

## Repository Documentation

| File | Purpose |
|---|---|
| [`goal.md`](./goal.md) | Product intent, V1 scope, success criteria, user journeys, non-goals |
| [`AGENTS.md`](./AGENTS.md) | Instructions for Claude Code, Codex, and other coding agents |
| [`README.md`](./README.md) | Repository overview, setup, local development, run instructions |
| [`docs/architecture.md`](./docs/architecture.md) | Technical architecture, component responsibilities, data flow |
| [`docs/simulation.md`](./docs/simulation.md) | Persona model, graph model, simulation rules, intervention mechanics |
| [`docs/evaluation.md`](./docs/evaluation.md) | Validation strategy, metrics, backtesting, calibration, experiment design |
| [`docs/scenario-v1.md`](./docs/scenario-v1.md) | **Locked V1 scenario spec** — Singapore bus stop rationalisation. Canonical for all transport-scenario details |
| [`HANDOFF.md`](./HANDOFF.md) | **Team handoff** — frozen frontend/backend contract, workstreams, non-negotiables. Start here if you are joining |

The intent of this split is to keep context layered rather than duplicating the entire project specification into one file.

---

## Proposed Technology Stack

The exact implementation may evolve, but the current preferred stack is:

### Frontend

- React / Next.js
- TypeScript
- Graph visualization library
- Charting library

### Backend

- Python
- FastAPI

### Agent Orchestration

- LangGraph

### LLM

- Claude through Amazon Bedrock

### Graph / Simulation

- NetworkX for the MVP
- Normal Python logic for deterministic simulation
- Explicit probability/rule models for behavioral simulation

### AWS

Prefer low-cost/serverless services where needed:

- Amazon Bedrock
- AWS Lambda
- DynamoDB on-demand
- S3
- Bedrock AgentCore only if it materially improves deployment or demo quality

The hackathon AWS budget is intentionally small, so the system should avoid always-on infrastructure and unnecessary high-volume LLM calls.

---

## Expected Repository Shape

This is the target shape, not a requirement to create empty directories prematurely:

```text
CivicTwin/
├── goal.md
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── graph/
│   │   ├── simulation/
│   │   ├── interventions/
│   │   ├── feedback/
│   │   ├── calibration/
│   │   ├── schemas/
│   │   └── main.py
│   └── tests/
│
├── frontend/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── fixtures/
│
├── scripts/
│
└── docs/
    ├── architecture.md
    ├── simulation.md
    └── evaluation.md
```

---

## Local Setup

The implementation is not final yet, so these commands describe the intended development workflow rather than a guaranteed completed repository.

### 1. Clone the repository

```bash
git clone <repository-url>
cd CivicTwin
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it.

**macOS / Linux**

```bash
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

Once `requirements.txt` or `pyproject.toml` exists:

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy:

```bash
cp .env.example .env
```

Expected variables may include AWS credentials or Bedrock configuration.

Do not commit `.env`.

Hackathon AWS credentials may expire and should not be treated as permanent secrets.

### 5. Start backend

Expected pattern:

```bash
uvicorn backend.app.main:app --reload
```

### 6. Start frontend

From the frontend directory:

```bash
npm install
npm run dev
```

Exact commands should be updated once the implementation stabilizes.

---

## Development Priorities

The implementation should prioritize the visible end-to-end story:

1. One public-policy scenario.
2. Structured synthetic personas.
3. A graph that materially affects outcomes.
4. Baseline policy simulation.
5. Automatic impact auditing.
6. Root-cause / propagation explanation.
7. Alternative intervention generation.
8. Re-simulation.
9. Before/after comparison.
10. Public consultation.
11. Real feedback aggregation.
12. Simulated-vs-real calibration.

A smaller, reliable implementation of this complete loop is preferred over multiple incomplete domains.

---

## Example Demo Story

A suitable demo could be:

> A policymaker proposes a public-policy change. CivicTwin simulates its effects across a synthetic population. The overall metric improves, but one subgroup suffers a severe accessibility loss. CivicTwin traces the cause, proposes several mitigation strategies, re-simulates them, and identifies a better trade-off. The improved proposal is published for public feedback. Real users reveal an overlooked constraint, and CivicTwin shows that its synthetic model was poorly calibrated for that subgroup.

The exact scenario remains an open product decision.

---

## Product Boundaries

CivicTwin is not designed for:

- election manipulation,
- voter persuasion,
- political microtargeting,
- propaganda optimization,
- covert profiling,
- automated denial of public services,
- autonomous enactment of public policy.

Synthetic population results must not be presented as certain predictions of real human behavior.

---

## Documentation Workflow

When the project evolves:

- Product decisions belong in `goal.md`.
- Coding-agent behavior belongs in `AGENTS.md`.
- Setup/run changes belong here.
- Technical system design belongs in `docs/architecture.md`.
- Simulation mechanics belong in `docs/simulation.md`.
- Experimental methodology and results belong in `docs/evaluation.md`.
- Locked V1 scenario details belong in `docs/scenario-v1.md`.

Avoid copying the same section into every file.

---

## Current Open Decisions

The V1 scenario is **locked**: Singapore public-bus stop rationalisation. The demo scenario,
datasets, persona schema, graph relationships, simulation rules, intervention search space,
“better off” metrics, consultation questions, calibration method, and live-versus-precomputed
split are all specified in [`docs/scenario-v1.md`](./docs/scenario-v1.md).

Remaining before implementation — see `docs/scenario-v1.md` §14.1:

- exact LTA DataMall dataset and field names,
- exact SingStat table identifiers for subzone × age band,
- the study area, once the selection rule is applied to real figures,
- whether LTA walking-distance planning guidance supports the locked metre thresholds.

See [`goal.md`](./goal.md) for the product-level list, some of which `docs/scenario-v1.md`
now answers for the transport scenario.

---

## North-Star Idea

> **CivicTwin gives policymakers a safer environment to learn before real people bear the cost of the experiment.**
