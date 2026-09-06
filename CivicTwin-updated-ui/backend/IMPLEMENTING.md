# Implementing the CivicTwin backend

Read `../HANDOFF.md` first for the workstreams. This file is the narrower question:
**what is actually built here, what is a stub, and how do you know when you are done.**

---

## The one trap

`scripts/make_fixture.py` contains functions called `build_population()`,
`assign_care_edges()`, `simulate()` and `metrics_for()`.

**That is not the engine. Do not extend it.**

It exists to generate a shape-correct demo fixture so the frontend could be built before
any backend existed. It cuts corners the real engine must not: no NetworkX graph, no
shortest-path computation, no real stop geometry, exposure is a per-subzone probability
rather than a consequence of distance.

The real engine goes in `backend/app/simulation/`, `backend/app/graph/` and
`backend/app/agents/`, and it must satisfy `tests/test_contract.py`.

What *is* worth lifting from that script is the **seeding discipline** and the
**structure of the rules**, both of which are specified in `docs/scenario-v1.md`:

```python
def persona_rng(key: str) -> random.Random:
    digest = hashlib.sha256(f"{SCENARIO_SEED}:{key}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))
```

Per-persona derived streams, never one sequential RNG. This is decision **G2**, and it is
what makes a baseline-vs-intervention delta causal instead of reshuffled noise.

---

## What is real, and what is a stub

| Thing | State |
|---|---|
| `app/schemas/run.py` | **Real.** The typed target. Build against these models. |
| `app/schemas/policy.py` | **Real.** |
| `app/services/llm.py` | **Real.** Mock and Bedrock adapters, retries, telemetry. |
| `app/agents/policy_interpreter.py` | **Real.** The one agent that exists. |
| `app/main.py` routes and status codes | **Real.** Shapes and error semantics are settled. |
| `load_run()` in `app/main.py` | **STUB.** Reads the fixture. This is the function you replace. |
| `submit_feedback` | **STUB.** Validates, returns an id, persists nothing. W7. |
| `apply_calibration` | **STUB.** Returns the decision, records nothing. W7. |
| `app/simulation/`, `app/graph/`, `app/interventions/`, `app/calibration/` | **Do not exist yet.** |

Anything marked STUB has a `W#` marker in the source saying which workstream owns it.

---

## Definition of done

```bash
cd backend
python -m pytest tests -q
```

`tests/test_contract.py` calls `load_run()` and asserts the invariants the product
depends on. It does not care whether the run came from a fixture or a real engine, so it
is the same bar before and after you swap the body. **38 tests pass today.**

A sample of what it holds you to, and why each one matters:

- `max_walk_m` matches the declared mobility mapping. **C3** is a spec, not a hint.
- `CARES_FOR` edges stay inside one household and one subzone. A carer who lives
  elsewhere makes the dependency meaningless.
- `CARES_FOR` is asymmetric. Harm propagates to the carer, never back (**D2**).
- Every `cause` id resolves, and points backwards in round order. An unresolvable cause
  makes a root-cause trace unprovable, and `evaluation.md` §9's Grounded Explanation Rate
  uncomputable.
- The second-order chain is at least 3 deep and passes through
  `DEPENDENCY_ABSORBED`. If this fails, the cascade never fired and the product's
  central claim has no evidence.
- Second-order victims have `mobility_level == "none"`. That is the whole claim: harmed
  through someone else, not by their own walk.
- Rejected interventions carry `metrics: None`. Scoring something never simulated would be
  inventing a result.
- Nothing is flagged in calibration on `n < 30`, and the proposed adjustment is never
  `applied` without a human (**L2**, **L3**).

**Do not weaken an assertion to make an implementation pass.** If the spec genuinely
changed, change `docs/scenario-v1.md` first, then the test, then the code.

---

## Where the seams already are

**Swapping the engine.** Replace the body of `load_run()`. Keep the return type
`SimulationRun`. Validation happens there, so an engine that drifts from the contract
fails loudly at the boundary rather than quietly in the browser. It costs about 10 ms for
2,000 personas, which is worth paying.

**Adding an agent.** Follow `agents/policy_interpreter.py`. Never call Bedrock directly;
go through `LLMClient.structured()`, which returns a validated Pydantic model or raises.
That gives you mocking, one place to swap models, token and latency recording, and schema
validation on every output (`architecture.md` §15, `AGENTS.md` §7).

**Running without AWS.** `LLM_PROVIDER` defaults to `mock`. The whole suite runs with no
credentials, which `AGENTS.md` §20 requires. `LLM_PROVIDER=bedrock` switches adapters;
nothing else changes.

**Failure semantics are already decided.** Keep them.

```
422  the input was understood but produced nothing simulable  -> the planner can fix it
502  the model itself is unreachable or misbehaving           -> not the planner's fault
503  no run available at all
404  unknown run id
```

Never convert a failed model call into plausible-looking output (`AGENTS.md` §18).

---

## Known gaps you are inheriting

- **`_run_cache` is a module-level global.** Fine for one fixture, wrong the moment runs
  are per-request. Replace with a store when `load_run()` becomes real.
- **CORS is hardcoded** to `localhost:5173`. Tighten before this leaves a laptop.
- **The mock's canned response is keyed on the string `"Ang Mo Kio"`** appearing in the
  prompt. Brittle by design, and only there so the API demos without credentials.
- **`app/api/` is an empty package.** Routes currently live in `main.py`. Split them out
  when there are enough to justify it, not before.
- **No persistence layer at all.** `architecture.md` §11 proposes S3 plus DynamoDB with a
  local JSON adapter. Nothing is built.
