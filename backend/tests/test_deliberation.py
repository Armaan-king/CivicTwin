"""The deliberation loop: does it wire facts to residents, and residents to neighbours.

Each test uses its own policy text. The cache is keyed on the prompt, so a shared string
lets one test serve another from cache and quietly assert nothing.

The stub here exercises plumbing and nothing else. It never reaches a screen: `deliberate()`
refuses a mock provider outright, and these tests reach past that refusal deliberately, to
check the loop rather than to manufacture residents. `AGENTS.md` §20.

The groundedness guard itself is tested in `test_grounding.py`, and batch integrity in
`test_batch_integrity.py`.
"""
from __future__ import annotations

import json

import pytest

from app.deliberate import NoModelConfigured, deliberate
from app.engine import study_area
from app.population import build_population
from app.services.llm import LLMClient
from app.social import build_social_graph
from app.world import build_world


class StubCompletion:
    """Returns schema-valid JSON built from the prompt it was handed.

    It reads the resident ids and fact ids out of the prompt, so a turn it produces is
    grounded by construction -- including the policy facts, without which a turn claiming
    any impact is rejected for resting only on things that were true beforehand.
    """

    name = "stub"

    def __init__(self):
        self.prompts: list[str] = []

    def complete(self, system: str, prompt: str, max_tokens: int, schema=None) -> str:
        self.prompts.append(prompt)
        ids = [line.split()[1] for line in prompt.splitlines() if line.startswith("RESIDENT ")]
        facts = {
            pid: [w.strip("[]") for w in prompt.split(f"RESIDENT {pid}\n")[1].split("\n\n")[0].split()
                  if w.startswith("[") and w.endswith("]")]
            for pid in ids
        }
        if "OpeningBatch" in prompt:
            return json.dumps({"voices": [
                {"persona_id": pid, "name": f"Resident {pid[-3:]}", "summary": "stub",
                 "turns": [{"round": 0, "position": 0.6, "confidence": 0.5,
                            "reasoning": "Stub opening view.", "severity": "none",
                            "response": "unaffected",
                            "grounded_in": facts[pid][:1]}]}
                for pid in ids
            ]})
        return json.dumps({"turns": [
            {"persona_id": pid, "round": 1, "position": 0.3, "confidence": 0.7,
             "reasoning": "Stub round view.", "severity": "moderate",
             "response": "adapting", "grounded_in": facts[pid],
             "changed_because": "the policy landed"}
            for pid in ids
        ]})


@pytest.fixture(scope="module")
def small():
    geo, closed, _ = study_area()
    pop = build_population(geo, 120)
    world = build_world(pop, geo, closed)
    return pop, world, build_social_graph(pop)


def test_a_mock_provider_is_refused(small):
    """The failure that let a whole feature ship switched off. It must be loud."""
    from app.services.llm import MockCompletion

    pop, world, social = small
    with pytest.raises(NoModelConfigured):
        deliberate(pop, world, "refusal policy", LLMClient(MockCompletion()), social=social)


def test_the_loop_produces_a_turn_per_round(small):
    pop, world, social = small
    stub = StubCompletion()
    run = deliberate(pop, world, "turns policy", LLMClient(stub), social=social)
    assert run.voices, "nobody deliberated"
    assert run.participation[0] == len(run.voices)
    assert run.participation[1] == len(run.cohort), "round 1 is the whole cohort"
    assert all(len(v.turns) >= 2 for v in run.voices.values())


def test_every_voice_is_filed_under_the_id_the_model_returned(small):
    """Identity is validated, not overwritten.

    The loop matches each returned voice to the resident it names. Anything it cannot
    match is refused rather than relabelled, so a voice present here is one the model
    actually attributed to that resident.
    """
    pop, world, social = small
    run = deliberate(pop, world, "identity policy", LLMClient(StubCompletion()), social=social)
    for pid, v in run.voices.items():
        assert v.persona_id == pid


def test_residents_are_shown_their_neighbours(small):
    """Without this the run is many monologues, not a deliberation."""
    pop, world, social = small
    stub = StubCompletion()
    deliberate(pop, world, "neighbour policy", LLMClient(stub), social=social)
    later = [p for p in stub.prompts if "ROUND" in p]
    assert later, "no round prompts were built"
    assert any("People you know are saying" in p for p in later)


def test_a_resident_only_sees_their_own_facts(small):
    """A prompt that leaks another resident's facts into this one's block would make
    grounding meaningless: anything cited would validate."""
    pop, world, social = small
    stub = StubCompletion()
    deliberate(pop, world, "isolation policy", LLMClient(stub), social=social)
    for prompt in stub.prompts:
        for block in prompt.split("RESIDENT ")[1:]:
            pid = block.split()[0]
            for line in block.splitlines():
                if line.strip().startswith("[") and ":f" in line:
                    assert line.strip().split("]")[0].lstrip("[").split(":")[0] == pid


def test_caching_means_a_replay_costs_nothing(small):
    pop, world, social = small
    first = deliberate(pop, world, "cache test policy", LLMClient(StubCompletion()), social=social)
    second = deliberate(pop, world, "cache test policy", LLMClient(StubCompletion()), social=social)
    assert first.calls > 0
    assert second.calls == 0, "a replay called the model again"
    assert second.cached > 0


def test_coverage_never_reports_the_unasked_as_unaffected(small):
    """The denominator rule, enforced by the run rather than by the screen.

    A resident nobody asked is unknown. `coverage()` has to be able to say how many that
    is, or a rate over the cohort gets read as a rate over the town.
    """
    pop, world, social = small
    run = deliberate(pop, world, "coverage policy", LLMClient(StubCompletion()), social=social)
    cov = run.coverage()
    assert cov["population"] == len(pop.personas)
    assert cov["evaluated"] == len(run.evaluated)
    assert cov["evaluated"] <= cov["cohort"] <= cov["population"]
    assert cov["unevaluated"] == cov["population"] - cov["evaluated"]
    assert sum(cov["strata"].values()) == cov["cohort"]


def test_a_resident_with_no_opening_view_is_not_asked_to_continue(small):
    """Round 1 follows on from round 0, so it can only include residents who have one.

    A resident whose opening turn failed the grounding guard has nothing to continue from.
    Asking them anyway crashed the loop the first time a real model produced an ungrounded
    opening; with a reliable model round 0 never failed and this never fired.
    """
    from app.deliberate import DeliberationRun, _participants
    from app.schemas.deliberation import AgentTurn, AgentVoice

    pop, world, social = small
    run = DeliberationRun(model="test")
    spoke, silent = pop.personas[0].persona_id, pop.personas[1].persona_id
    run.voices = {spoke: AgentVoice(persona_id=spoke, name="n", summary="", turns=[
        AgentTurn(round=0, position=0.5, confidence=0.5, reasoning="x",
                  grounded_in=[f"{spoke}:f1"])])}
    index = {p.persona_id: p for p in pop.personas[:2]}

    speakers = _participants(run, world, social, 1, index)
    assert spoke in speakers
    assert silent not in speakers, "a resident with no opening view was asked to continue"


def test_replay_only_skips_a_cache_miss_instead_of_calling_the_model(small, monkeypatch):
    """A demo replays a real run from disk; it must not quietly call the model for the
    parts that were never run.

    On a local GPU that turns a page load into hours, and the residents in a missing batch
    must come back as unevaluated -- unknown -- never as unaffected.
    """
    from app import deliberate as D

    pop, world, social = small

    class NeverCalled:
        name = "stub"

        def complete(self, system, prompt, max_tokens, schema=None):
            raise AssertionError("replay-only called the model")

    monkeypatch.setattr(D, "REPLAY_ONLY", True)
    run = D.deliberate(pop, world, "replay only policy", LLMClient(NeverCalled()),
                       social=social, limit=8)
    assert run.calls == 0
    assert run.failed_batches > 0, "the miss must be counted, not hidden"
    cov = run.coverage()
    assert cov["evaluated"] == 0
    assert cov["unevaluated"] == cov["population"]
