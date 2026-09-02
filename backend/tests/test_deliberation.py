"""The deliberation loop, and the guard that makes it evidence.

Each test uses its own policy text. The cache is keyed on the prompt, so a shared string
lets one test serve another from cache and quietly assert nothing.

The stub here exercises plumbing and nothing else. It never reaches a screen: `deliberate()`
refuses a mock provider outright, and these tests reach past that refusal deliberately, to
check the loop rather than to manufacture residents. `AGENTS.md` §20.
"""
from __future__ import annotations

import json

import pytest

from app.agents.deliberation import check_grounding
from app.deliberate import NoModelConfigured, deliberate
from app.engine import study_area
from app.population import build_population
from app.schemas.deliberation import AgentTurn
from app.services.llm import LLMClient
from app.social import build_social_graph
from app.world import build_world


class StubCompletion:
    """Returns schema-valid JSON built from the prompt it was handed.

    It reads the resident ids and fact ids out of the prompt, so a turn it produces is
    grounded by construction. That is the point: it tests that the loop wires facts to
    residents and residents to their neighbours, not that a model writes well.
    """

    name = "stub"

    def __init__(self):
        self.prompts: list[str] = []

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
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
        return json.dumps({
            "persona_ids": ids,
            "turns": [
                {"round": 1, "position": 0.3, "confidence": 0.7,
                 "reasoning": "Stub round view.", "severity": "moderate",
                 "response": "adapting", "grounded_in": facts[pid][:2]}
                for pid in ids
            ],
        })


@pytest.fixture(scope="module")
def small():
    geo, closed = study_area()
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
    assert len(run.voices) == len(pop.personas)
    assert run.participation[0] == len(pop.personas)
    assert run.participation[1] == len(pop.personas), "round 1 is everyone"
    assert all(len(v.turns) >= 2 for v in run.voices.values())


def test_identity_never_comes_from_the_model(small):
    """The model is told persona ids and must not be trusted to hand them back."""
    pop, world, social = small
    run = deliberate(pop, world, "identity policy", LLMClient(StubCompletion()), social=social)
    for pid, v in run.voices.items():
        assert v.persona_id == pid


def test_residents_are_shown_their_neighbours(small):
    """Without this the run is two thousand monologues, not a deliberation."""
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


# ---------------------------------------------------------------- the grounding guard
def test_a_fabricated_fact_is_caught():
    turn = AgentTurn(round=1, position=0.2, confidence=0.6, reasoning="My stop closed.",
                     severity="high", response="giving_up", grounded_in=["p_0001:f99"])
    assert check_grounding(turn, {"p_0001:f1"}, set())


def test_an_invented_neighbour_is_caught():
    turn = AgentTurn(round=1, position=0.2, confidence=0.6, reasoning="Ah Seng told me.",
                     severity="none", response="unaffected",
                     grounded_in=["p_0001:f1"], influenced_by="p_9999")
    assert check_grounding(turn, {"p_0001:f1"}, {"p_0002"})


def test_absorbing_for_a_stranger_is_caught():
    """The second-order claim is the product. A resident may not invent who they carry."""
    turn = AgentTurn(round=3, position=0.1, confidence=0.8, reasoning="I drive her now.",
                     severity="high", response="absorbing",
                     grounded_in=["p_0001:f1"], absorbing_for="p_7777")
    assert check_grounding(turn, {"p_0001:f1"}, {"p_0002"})


def test_harm_claimed_from_nothing_is_caught():
    turn = AgentTurn(round=1, position=0.1, confidence=0.9, reasoning="This ruins me.",
                     severity="high", response="giving_up", grounded_in=[])
    assert check_grounding(turn, {"p_0001:f1"}, set())


def test_a_grounded_turn_passes():
    turn = AgentTurn(round=1, position=0.3, confidence=0.6,
                     reasoning="The stop I use is closing and the next is 380 m further.",
                     severity="moderate", response="adapting",
                     grounded_in=["p_0001:f7", "p_0001:f8"], influenced_by="p_0002")
    assert check_grounding(turn, {"p_0001:f7", "p_0001:f8"}, {"p_0002"}) == []
