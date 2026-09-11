"""The run, as an explicit graph of single-purpose nodes.

`AGENTS.md` §13 sets the terms for using LangGraph and this follows them: nodes do one
thing, the shared state is typed, routing is visible, and nothing loops without a bound.

**What this is, stated plainly, because the distinction is easy to blur.** Ten nodes run
in order and **two** of them call a model: the Policy Interpreter, which reads a proposal
into a typed change, and the Deliberation, where residents reason. The other eight are
deterministic Python -- geometry, routing, tallies, arithmetic -- and wrapping a pure
function in a graph node does not make it an agent.

Counted here rather than asserted, because the first draft of this docstring said nine
nodes and three models, and `describe()` reported ten and two. The numbers come from
`PIPELINE` now, which is also what executes. The value here is not that the pipeline became intelligent; it is
that the pipeline became *visible*: every stage reports whether it ran, how long it took,
what it produced, and whether a model was involved.

That last part is the point. `build_run()` does all of this already, in one function, and
gives back a finished object with no account of how it was assembled. A reviewer asking
"what is the AI actually doing here?" deserves an answer more specific than "some of it".

The deterministic nodes delegate to the same functions `build_run()` calls, so this is a
second view of one pipeline rather than a second implementation of it. If the two ever
disagree, the answer is not to reconcile them but to delete this one.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

#: Whether a node reasons or computes. The honest label for a slide.
Kind = Literal["model", "deterministic"]


@dataclass
class NodeReport:
    """What one stage did. Recorded whether it succeeded or not."""

    name: str
    kind: Kind
    ms: int = 0
    ok: bool = True
    detail: str = ""
    error: str | None = None


@dataclass
class RunState:
    """The shared state, typed and explicit, as §13 requires.

    Large artefacts stay out of it: the state carries the population and the simulation
    result because later nodes genuinely need them, and it does not carry prompts,
    transcripts or cached batches, which belong on disk.
    """

    policy_text: str = ""
    town: str = ""
    policy: Any = None
    geo: Any = None
    pop: Any = None
    closures: set[str] = field(default_factory=set)
    simulation: Any = None
    metrics: dict = field(default_factory=dict)
    causes: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    scored: list = field(default_factory=list)
    deliberation: Any = None
    consultation: Any = None
    calibration: list = field(default_factory=list)
    reports: list[NodeReport] = field(default_factory=list)

    def record(self, name: str, kind: Kind, started: float,
               detail: str = "", error: str | None = None) -> None:
        self.reports.append(NodeReport(
            name=name, kind=kind, ms=int((time.monotonic() - started) * 1000),
            ok=error is None, detail=detail, error=error))


# --------------------------------------------------------------------------- nodes
def interpret_policy(state: RunState) -> RunState:
    """MODEL. Plain English into a typed PolicyChange."""
    t0 = time.monotonic()
    from app.agents.policy_interpreter import interpret
    from app.services.llm import build_client
    try:
        if state.policy_text.strip():
            state.policy = interpret(state.policy_text, build_client())
            detail = f"{len(state.policy.modifications.remove_stops)} stops named"
        else:
            detail = "no proposal submitted; the prepared scenario stands"
        state.record("Policy Interpreter", "model", t0, detail)
    except Exception as exc:                      # noqa: BLE001 - reported, not swallowed
        state.record("Policy Interpreter", "model", t0, error=str(exc)[:160])
    return state


def build_scenario(state: RunState) -> RunState:
    """DETERMINISTIC. The town, its residents, and the graph joining them."""
    t0 = time.monotonic()
    from app.engine import DEFAULT_TOWN, study_area_for_town
    from app.graph import build_graph
    from app.population import build_population
    from app.scenario import POPULATION_SIZE
    state.town = state.town or DEFAULT_TOWN
    state.geo, state.closures = study_area_for_town(state.town)
    state.pop = build_population(state.geo, POPULATION_SIZE)
    build_graph(state.geo, state.pop)
    state.record("Scenario Builder", "deterministic", t0,
                 f"{len(state.pop.personas)} residents, {len(state.pop.care_edges)} care edges")
    return state


def run_simulation(state: RunState) -> RunState:
    """DETERMINISTIC. Route every resident before and after, and emit the event chain."""
    t0 = time.monotonic()
    from app.engine import _simulate_cached
    state.simulation = _simulate_cached(state.geo, state.pop, state.closures)
    state.record("Simulation Controller", "deterministic", t0,
                 f"{len(state.simulation.events)} events")
    return state


def audit_impact(state: RunState) -> RunState:
    """DETERMINISTIC. The six metrics, overall and by subgroup."""
    t0 = time.monotonic()
    from app.metrics import disparity_pp, metrics_for, subgroup_metrics
    outcomes = list(state.simulation.outcomes.values())
    sub = subgroup_metrics(state.pop, state.simulation.outcomes)
    state.metrics = {"overall": metrics_for(outcomes), "subgroup": sub,
                     "subgroup_disparity_pp": disparity_pp(sub)}
    severe = sum(1 for o in outcomes if o.severity == "high")
    state.record("Impact Auditor", "deterministic", t0, f"{severe} severely harmed")
    return state


def trace_root_causes(state: RunState) -> RunState:
    """DETERMINISTIC. Walk each leaf event back to what caused it."""
    t0 = time.monotonic()
    by_id = {e.event_id: e for e in state.simulation.events}
    chains = []
    for leaf in (e for e in state.simulation.events if e.kind == "OBLIGATION_MISSED"):
        chain, cursor, seen = [], leaf, set()
        while cursor and cursor.event_id not in seen:
            seen.add(cursor.event_id)
            chain.append(cursor.kind)
            cursor = by_id.get(cursor.cause) if cursor.cause else None
        chains.append(list(reversed(chain)))
    state.causes = chains
    state.record("Root-Cause Analyzer", "deterministic", t0,
                 f"{len(chains)} chains traced to a root")
    return state


def plan_interventions(state: RunState) -> RunState:
    """DETERMINISTIC. Five typed actions, parameterised for this town, then validated."""
    t0 = time.monotonic()
    from app.interventions import candidates, validate
    state.candidates = list(candidates(state.closures, state.pop, state.geo))
    for c in state.candidates:
        validate(c, fleet_increase_allowed=False)
    valid = sum(1 for c in state.candidates if c.valid)
    state.record("Intervention Planner", "deterministic", t0,
                 f"{len(state.candidates)} candidates, {valid} valid")
    return state


def compare_interventions(state: RunState) -> RunState:
    """DETERMINISTIC. Re-simulate each valid candidate over the same residents."""
    t0 = time.monotonic()
    from app.engine import _interventions_for
    # `_interventions_for`'s fourth argument is the *simulation result*, not the
    # interpreted policy -- engine.py names that local `policy`, which is what led me to
    # pass the wrong object here and take the node down with an AttributeError.
    state.scored = _interventions_for(state.geo, state.pop, state.closures,
                                      state.simulation)
    scored = sum(1 for r in state.scored if r.get("metrics"))
    state.record("Comparator", "deterministic", t0, f"{scored} alternatives scored")
    return state


def deliberate_population(state: RunState) -> RunState:
    """MODEL. Residents reason about the policy, in rounds, from their own facts.

    Served from a recorded run. Deliberating live takes twenty minutes at this account's
    quota, so a node that blocked on it would make the graph unusable for the thing the
    graph exists to show.
    """
    t0 = time.monotonic()
    from app.deliberate import load_recorded
    text = state.policy.text if state.policy is not None else state.policy_text
    state.deliberation = load_recorded(state.town, text or None)
    if state.deliberation is None:
        state.record("Deliberation", "model", t0,
                     "no recording for this policy; residents unevaluated")
    else:
        state.record("Deliberation", "model", t0,
                     f"{len(state.deliberation.voices)} residents reasoned")
    return state


def analyse_feedback(state: RunState) -> RunState:
    """DETERMINISTIC. Who replied, what they said, and who will not reply."""
    t0 = time.monotonic()
    from app.consultation import build_consultation
    from app.deliberate import recorded_words
    from app.engine import _road_of
    road = _road_of(state.geo, sorted(state.closures)[0]) if state.closures else ""
    state.consultation = build_consultation(state.pop, state.simulation.outcomes, road,
                                            words=recorded_words(state.closures))
    real = sum(1 for r in state.consultation.responses if not r.is_seeded)
    state.record("Feedback Analyst", "deterministic", t0,
                 f"{len(state.consultation.responses)} responses, {real} from people")
    return state


def calibrate(state: RunState) -> RunState:
    """DETERMINISTIC. Predicted against reported, per cohort, gated at n >= 30."""
    t0 = time.monotonic()
    state.calibration = state.consultation.calibration
    flagged = [r for r in state.calibration if r.flagged]
    state.record("Calibration", "deterministic", t0,
                 f"{len(flagged)} cohort(s) flagged of {len(state.calibration)}")
    return state


#: The pipeline, in order. Nine nodes; the two marked "model" are the only ones that
#: reason. Declared as data so the diagram and the execution cannot drift apart.
PIPELINE: list[tuple[str, Kind, Callable[[RunState], RunState]]] = [
    ("Policy Interpreter", "model", interpret_policy),
    ("Scenario Builder", "deterministic", build_scenario),
    ("Simulation Controller", "deterministic", run_simulation),
    ("Impact Auditor", "deterministic", audit_impact),
    ("Root-Cause Analyzer", "deterministic", trace_root_causes),
    ("Intervention Planner", "deterministic", plan_interventions),
    ("Comparator", "deterministic", compare_interventions),
    ("Deliberation", "model", deliberate_population),
    ("Feedback Analyst", "deterministic", analyse_feedback),
    ("Calibration", "deterministic", calibrate),
]


def build_graph_app():
    """Compile the pipeline into a LangGraph StateGraph.

    Linear today, and honestly so: every node depends on the one before it, so there is
    no branch to draw. LangGraph earns its place by making the state typed and the stages
    addressable rather than by routing cleverly, and the moment a node becomes
    conditional -- re-simulating only when an intervention is selected, say -- the edge
    goes here and nowhere else.
    """
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(RunState)
    for name, _kind, fn in PIPELINE:
        graph.add_node(name, fn)
    graph.add_edge(START, PIPELINE[0][0])
    for (a, _, _), (b, _, _) in zip(PIPELINE, PIPELINE[1:]):
        graph.add_edge(a, b)
    graph.add_edge(PIPELINE[-1][0], END)
    return graph.compile()


def run_pipeline(policy_text: str = "", town: str = "") -> RunState:
    """Execute the graph and return the state, reports included."""
    app = build_graph_app()
    result = app.invoke(RunState(policy_text=policy_text, town=town))
    # LangGraph hands back a mapping of the state's fields
    return result if isinstance(result, RunState) else RunState(**result)


def describe() -> dict:
    """The graph as data, for the diagram and for anyone asking what runs."""
    return {
        "nodes": [{"name": n, "kind": k, "doc": (f.__doc__ or "").strip().split("\n")[0]}
                  for n, k, f in PIPELINE],
        "edges": [{"from": a[0], "to": b[0]} for a, b in zip(PIPELINE, PIPELINE[1:])],
        "model_backed": sum(1 for _, k, _ in PIPELINE if k == "model"),
        "deterministic": sum(1 for _, k, _ in PIPELINE if k == "deterministic"),
        "note": ("Nodes that call a model are marked `model`. The rest are deterministic "
                 "Python -- geometry, routing, tallies, arithmetic -- and are nodes in an "
                 "orchestration graph rather than agents."),
    }
