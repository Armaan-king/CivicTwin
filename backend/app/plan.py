"""The Intervention Planner, as a model call. J1.

`interventions.candidates()` returned five hand-written objects with hand-written
rationales and hand-picked cost indices, parameterised for one closure in one town. The
system map said so, and the honest answer to "are these hard-coded for Ang Mo Kio?" was
yes. This is the swap the architecture document scoped: the action space was already
closed and typed, so a planner that selects and parameterises within it is a substitution
rather than a rewrite.

**What the model is allowed to decide, and what it is not.**

It decides which of the five actions to propose, which stops each one serves, how often,
who is eligible, and why. It decides nothing else. Every quantity it would otherwise have
to guess is computed and handed to it: which stops closed, which stops survive nearby and
how far away they are, which service runs where, how many residents are clinic-dependent
and mobility-limited. `AGENTS.md` §10 bans a model from distances and geometry, and a
model asked for the distance between two bus stops returns a plausible number rather than
a measured one.

**Why this is safe to let a model do, when routing is not.** Three guards, in order:

1. The tool schema fixes `kind` to five values, so an invented action cannot be returned.
2. `validate()` checks every parameter `run_candidate` will reach into -- real stop ids,
   open stops, an operable headway -- and rejects rather than raising.
3. Whatever survives is **re-simulated by the same engine over the same residents with
   the same seeds**. A bad proposal becomes a bad number on the comparison screen, not a
   confident claim. Nothing here is scored on the model's say-so.

So the worst case is a weak alternative that visibly loses, which is a normal outcome for
a planner and one the screen already renders.

Written to `data/runs/interventions-{town}.json` by `scripts/plan_interventions.py` and
loaded from there at request time. Same shape as the remedy classifier: the demo makes no
call, and `test_orchestrator` asserts it.
"""
from __future__ import annotations

import json
import pathlib

from pydantic import BaseModel, Field

from app.geography import Geography, distance_m
from app.interventions import BUDGET_CEILING, KINDS, Candidate, _nearest_surviving
from app.population import Population

RUNS = pathlib.Path(__file__).resolve().parents[2] / "data" / "runs"


class PlannedIntervention(BaseModel):
    """One proposal. `kind` is constrained by the tool schema, not by hope."""

    kind: str
    #: a short label for the comparison screen
    name: str = Field(min_length=3, max_length=80)
    #: why this helps, in the planner's own words, for a human reading the options
    rationale: str = Field(min_length=10, max_length=400)
    #: what `run_candidate` needs. Validated before anything is simulated.
    params: dict = Field(default_factory=dict)
    #: operating cost relative to the service before the policy. Above the ceiling is a
    #: legitimate answer: it is rejected with a reason rather than silently trimmed, and
    #: the rejected row is part of what the screen shows.
    estimated_cost_index: float = Field(ge=0.5, le=3.0)


class InterventionPlan(BaseModel):
    interventions: list[PlannedIntervention] = Field(default_factory=list)


PLANNER_SYSTEM = """You are a transport planner proposing alternatives to a bus policy that
has already been simulated. You are choosing from a fixed menu; you are not inventing
policy instruments.

The five actions, and the parameters each one needs:

    retain_stop_peak     Keep the closing stop(s) open at certain hours.
                         params: {"stops": [stop ids], "hours": "07:00-09:30, 17:00-19:30"}

    add_shuttle_feeder   A new small bus linking specific stops.
                         params: {"serves": [stop ids], "headway_min": number}
                         Add "vehicles": n only if it needs a bigger fleet.

    reroute_feeder       Send an existing service past different stops.
                         params: {"add": [stop ids], "drop": [stop ids]}

    targeted_support     Door-to-door or subsidised transport for named residents.
                         params: {"eligible": "a phrase", "n_eligible": number}

    phase_rollout        Close some stops now and defer others.
                         params: {"close_now": [stop ids], "defer": [stop ids]}

Rules, all of them load-bearing:

- Use ONLY stop ids from the facts you are given. Do not invent an id, and do not guess
  one from a name. Every id is checked and a proposal naming an unknown stop is thrown out.
- A `serves` or `add` list may NEVER contain a closed stop. Serving the stop the policy
  closed undoes the policy: harm drops to zero and it scores as a brilliant intervention
  while being the original service with a new label.
- Do not calculate distances, journey times or how many people benefit. You have not been
  given what you would need and an estimate here is a fabrication. Say what you propose;
  the simulator measures what it does.
- `estimated_cost_index` is your honest estimate of operating cost relative to the service
  before the policy, where 1.0 is unchanged. The declared ceiling is %(ceiling).2f.
- **Propose at least one alternative you expect to cost too much or to lose.** A slate
  where everything looks good is not a comparison. An option rejected on cost, or one that
  helps the harmed group while stranding somebody else, is more useful to a human deciding
  than five safe variations, and the trade-off is the reason the comparison screen exists.
- Propose between four and six. Vary the `kind`: five shuttles is one idea five times.

`rationale` is read by a person choosing between these. Say what it does and who it is
for, not that it is promising.
""" % {"ceiling": BUDGET_CEILING}


def facts_for(geo: Geography, pop: Population, removed: set[str]) -> str:
    """The world, looked up and written down. The model reasons only from this.

    Every number here is measured by code that already existed. That is the division
    `AGENTS.md` §3 draws: conventional algorithms retrieve world facts, and the agent
    decides what to do about them.
    """
    nearby = _nearest_surviving(geo, removed, per_closure=3)
    feeder = geo.services[geo.feeder_service]
    clinic = geo.clinic_stops[0]
    assisted = sum(1 for p in pop.personas
                   if p.needs_clinic and p.mobility_level in ("moderate", "severe"))

    def describe(stop_id: str, *, ref: str | None = None) -> str:
        s = geo.stops[stop_id]
        line = f"  {stop_id}  {s.name}"
        if ref:
            line += f"  ({distance_m(s.xy, geo.stops[ref].xy):.0f} m from {ref})"
        return line

    closed = sorted(removed)
    lines = [
        "CLOSED BY THE POLICY (never serve these):",
        *(describe(s) for s in closed),
        "",
        "NEAREST SURVIVING STOPS, which is where people are being pushed:",
        *(describe(s, ref=closed[0]) for s in nearby),
        "",
        f"THE HOSPITAL / CLINIC STOP: {clinic}  {geo.stops[clinic].name}",
        f"THE INTERCHANGE: {geo.work_gateway}  {geo.stops[geo.work_gateway].name}",
        "",
        f"THE LOCAL FEEDER SERVICE: {feeder.service_id} ({feeder.name}), every "
        f"{feeder.headway_min:.0f} min, calling at:",
        *(describe(s) for s in dict.fromkeys(feeder.stops)),
        "",
        f"RESIDENTS who are mobility-limited and have an essential clinic trip: {assisted}",
        f"POPULATION in the study area: {len(pop.personas)}",
    ]
    return "\n".join(lines)


def plan(geo: Geography, pop: Population, removed: set[str], llm,
         on_note=None) -> list[Candidate]:
    """Ask the model for alternatives. Returns unvalidated candidates.

    Unvalidated on purpose, exactly as `remedies.py` hands its proposals back: the caller
    runs `validate()` and, only if that passes, simulates. A rejection has to reach the
    screen with its reason attached, so this may not quietly drop anything.
    """
    from app.services.llm import call_with_retries

    facts = facts_for(geo, pop, removed)
    prompt = (
        "The policy closes the stops listed below and lets the express service run "
        "non-stop through the corridor.\n\n"
        f"{facts}\n\n"
        "Propose four to six alternatives, using only these stop ids."
    )
    plan_ = call_with_retries(
        lambda: llm.structured(
            InterventionPlan, PLANNER_SYSTEM, prompt, max_tokens=3000,
            schema_override=_schema_with_kind_enum()),
        on_note=on_note)

    out: list[Candidate] = []
    for i, p in enumerate(plan_.interventions):
        out.append(Candidate(
            intervention_id=f"iv_{i}_{p.kind}",
            kind=p.kind,
            name=p.name,
            params=dict(p.params),
            rationale=p.rationale,
            estimated_cost_index=round(float(p.estimated_cost_index), 2),
        ))
    if on_note:
        on_note(f"planner proposed {len(out)}")
    return out


def _schema_with_kind_enum() -> dict:
    """Pin `kind` to the five actions in the tool schema itself.

    Belt and braces with `validate()`, and worth having both: a constrained schema means
    the model rarely produces an invalid kind, and the validator means it does not matter
    when it does. The prompt alone is not a constraint.
    """
    schema = InterventionPlan.model_json_schema()
    defs = schema.get("$defs", {})
    item = defs.get("PlannedIntervention", {})
    if "kind" in item.get("properties", {}):
        item["properties"]["kind"] = {"type": "string", "enum": list(KINDS),
                                      "description": "one of the five actions"}
    return schema


# ------------------------------------------------------------------------ the cache
def cache_path(town: str) -> pathlib.Path:
    return RUNS / f"interventions-{town}.json"


def load_planned(removed: set[str]) -> tuple[list[Candidate], str] | None:
    """The planner's output for this closure, read back from disk.

    Matched on the closed stop ids rather than on the town, exactly as `recorded_words`
    is: a plan for a different closure is a different question, not a partial answer, and
    serving one would put alternatives on the options screen addressing stops nobody shut.

    Returns the candidates and the model that produced them, because the screen has to be
    able to say which. Falling back to the hand-written list is fine; doing so silently,
    while a slide says the alternatives are planned by a model, is not.
    """
    for path in sorted(RUNS.glob("interventions-*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if set(raw.get("closed") or []) != set(removed):
            continue
        return [Candidate(**c) for c in raw.get("candidates", [])], raw.get("model", "recorded")
    return None
