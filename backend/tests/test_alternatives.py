"""Only evaluated alternatives receive outcome scores."""
from __future__ import annotations

import json

import pytest

from app.alternatives import closures_under, evaluate
from app.deliberate import deliberate
from app.engine import study_area
from app.interventions import Candidate, validate
from app.population import build_population
from app.services.llm import LLMClient
from app.social import build_social_graph
from app.world import build_world


class Stub:
    """Declares harm under the policy and none once the stop is retained.

    Keyed on the alternative marker in the prompt, so the two runs differ for a reason
    rather than by luck.
    """

    name = "stub"

    def complete(self, system, prompt, max_tokens, schema=None):
        ids = [l.split()[1] for l in prompt.splitlines() if l.startswith("RESIDENT ")]
        facts = {
            pid: [w.strip("[]") for w in
                  prompt.split(f"RESIDENT {pid}\n")[1].split("\n\n")[0].split()
                  if w.startswith("[") and w.endswith("]")]
            for pid in ids
        }
        relieved = "ALTERNATIVE UNDER CONSIDERATION" in prompt
        sev, resp = ("none", "unaffected") if relieved else ("high", "giving_up")
        if "OpeningBatch" in prompt:
            return json.dumps({"voices": [
                {"persona_id": pid, "name": "Tan Wei Ming", "summary": "s",
                 "turns": [{"round": 0, "position": 0.5, "confidence": 0.5,
                            "reasoning": "Only heard it will be faster.",
                            "severity": "none", "response": "unaffected",
                            "grounded_in": facts[pid][:1]}]} for pid in ids]})
        return json.dumps({"turns": [
            {"persona_id": pid, "round": 1, "position": 0.2, "confidence": 0.8,
             "reasoning": "The stop I use is closing.", "severity": sev,
             "response": resp, "grounded_in": facts[pid],
             "changed_because": "the policy landed"} for pid in ids]})


@pytest.fixture(scope="module")
def world():
    geo, closed, _ = study_area()
    pop = build_population(geo, 120)
    w = build_world(pop, geo, closed)
    social = build_social_graph(pop)
    run = deliberate(pop, w, "alternatives policy", LLMClient(Stub()),
                     social=social, limit=8)
    return geo, closed, pop, social, run


def keep_candidate(closed):
    return Candidate(intervention_id="r1", kind="retain_stop_peak",
                     name="keep the stop open at the times I travel",
                     params={"stop_ids": sorted(closed), "hours": ["07:00-09:30"]},
                     rationale="4 residents asked for this.", estimated_cost_index=0.99)


def test_a_rejected_candidate_is_never_scored(world):
    geo, closed, pop, social, run = world
    c = Candidate(intervention_id="r2", kind="add_shuttle_feeder", name="a shuttle",
                  params={"vehicles": 1}, rationale="asked for", estimated_cost_index=1.12)
    validate(c, fleet_increase_allowed=False)
    assert c.valid is False

    result = evaluate(c, run, pop, geo, closed, "policy", LLMClient(Stub()), social)
    assert result.metrics is None, "a rejected candidate must carry no metrics"
    assert result.severe_harm_delta is None
    assert "rejected by the validator" in result.skipped


def test_an_action_the_world_cannot_model_is_not_scored_as_neutral(world):
    """Scoring an unrepresentable change as 'no difference' would be a fabricated result."""
    geo, closed, pop, social, run = world
    c = Candidate(intervention_id="r3", kind="targeted_support", name="fare help",
                  params={"cohort": "harmed"}, rationale="asked for",
                  estimated_cost_index=1.03)
    validate(c, fleet_increase_allowed=False)
    result = evaluate(c, run, pop, geo, closed, "policy", LLMClient(Stub()), social)
    assert result.metrics is None
    assert "not scored rather than scored as neutral" in result.skipped


def test_a_feasible_alternative_is_re_deliberated_and_scored(world):
    geo, closed, pop, social, run = world
    c = keep_candidate(closed)
    validate(c, fleet_increase_allowed=False)
    assert c.valid

    result = evaluate(c, run, pop, geo, closed, "policy", LLMClient(Stub()), social)
    assert result.skipped is None
    assert result.metrics is not None, "a feasible alternative must be scored"
    assert result.run is not None and result.run.voices

    # the residents said the harm went away, so the delta must show it
    assert result.compared_over > 0
    assert result.severe_harm_delta is not None
    assert result.severe_harm_delta < 0, "retaining the stop removed declared harm"


def test_the_comparison_is_over_the_same_residents(world):
    """A delta across two different groups of people is not a delta."""
    geo, closed, pop, social, run = world
    c = keep_candidate(closed)
    validate(c, fleet_increase_allowed=False)
    result = evaluate(c, run, pop, geo, closed, "policy", LLMClient(Stub()), social)
    assert result.compared_over <= len(run.evaluated)
    assert set(result.aggregation.outcomes) <= set(run.evaluated)


def test_retaining_the_stop_reopens_it_in_the_world(world):
    geo, closed, pop, social, run = world
    c = keep_candidate(closed)
    assert closures_under(c, closed) == set()
    other = Candidate(intervention_id="r4", kind="phase_rollout", name="gradual",
                      params={"delay_weeks": 12}, rationale="", estimated_cost_index=1.01)
    assert closures_under(other, closed) == set(closed), "phasing does not reopen a stop"


# --------------------------------------------------------------- model-produced params
#
# Everything below exists because the candidates stopped being written by hand. Each case
# is a way `run_candidate` used to raise instead of rejecting, taking the whole run with
# it rather than one alternative.

def _candidate(kind: str, params: dict, cost: float = 1.0):
    from app.interventions import Candidate
    return Candidate(intervention_id="iv_x", kind=kind, name="x", params=params,
                     rationale="x", estimated_cost_index=cost)


def test_the_kind_list_matches_the_contract():
    """Two lists that must agree and are never compared is how one of them grows.

    `KINDS` is what a planner may choose. `ALL_KINDS` is what the contract permits, and it
    adds "combined" -- the engine stacking two of the five. The planner must never be able
    to propose one, so the gap between the lists is asserted rather than assumed.
    """
    from typing import get_args

    from app.interventions import ALL_KINDS, KINDS
    from app.schemas.run import InterventionKind

    assert set(ALL_KINDS) == set(get_args(InterventionKind))
    assert set(KINDS) < set(ALL_KINDS)
    assert "combined" not in KINDS, "a planner could propose a combination"


def test_an_invented_action_is_rejected_not_raised():
    from app.interventions import validate

    c = validate(_candidate("build_a_railway", {}), fleet_increase_allowed=False)
    assert not c.valid
    assert "not one of the five actions" in " ".join(c.validation_errors)


def test_a_missing_parameter_is_rejected_rather_than_a_keyerror():
    """`run_candidate` does `c.params["serves"]` with no guard behind it."""
    from app.interventions import validate

    c = validate(_candidate("add_shuttle_feeder", {"headway_min": 20}),
                 fleet_increase_allowed=False)
    assert not c.valid
    assert "'serves'" in " ".join(c.validation_errors)


def test_invented_stop_ids_are_rejected():
    from app.engine import DEFAULT_TOWN, study_area_for_town
    from app.interventions import validate

    geo, removed = study_area_for_town(DEFAULT_TOWN)
    c = validate(_candidate("add_shuttle_feeder",
                            {"serves": ["99999"], "headway_min": 20}),
                 fleet_increase_allowed=False, geo=geo, removed=removed)
    assert not c.valid
    assert "do not exist" in " ".join(c.validation_errors)


def test_a_candidate_may_not_call_at_the_stop_the_policy_closed():
    """Otherwise harm goes to zero and the baseline is scored as a brilliant fix."""
    from app.engine import DEFAULT_TOWN, study_area_for_town
    from app.interventions import validate

    geo, removed = study_area_for_town(DEFAULT_TOWN)
    c = validate(_candidate("add_shuttle_feeder",
                            {"serves": sorted(removed), "headway_min": 20}),
                 fleet_increase_allowed=False, geo=geo, removed=removed)
    assert not c.valid
    assert "closed stop" in " ".join(c.validation_errors)


def test_an_inoperable_headway_is_rejected():
    from app.interventions import validate

    for headway in (0, 1, 600, "soon"):
        c = validate(_candidate("add_shuttle_feeder",
                                {"serves": ["54009"], "headway_min": headway}),
                     fleet_increase_allowed=False)
        assert not c.valid, f"headway {headway!r} was accepted"


def test_nothing_invalid_is_ever_simulated():
    """The guarantee the whole screen rests on: a rejection carries no metrics."""
    from app.engine import DEFAULT_TOWN, build_run

    for row in build_run()["interventions"]:
        if not row["valid"]:
            assert row["metrics"] is None
    assert DEFAULT_TOWN
