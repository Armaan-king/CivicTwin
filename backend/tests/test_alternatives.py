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
             "response": resp, "grounded_in": facts[pid]} for pid in ids]})


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
