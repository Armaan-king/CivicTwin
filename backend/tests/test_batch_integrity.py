"""A schema-valid answer is not necessarily an answer.

Both providers this project can use are documented to fail in ways that pass validation.
DeepSeek's API docs warn it "may occasionally return empty content"; an 8B local model
asked for twelve residents without a grammar returns `{"voices": []}`. Counting either as
a result silently shrinks the population and reports the survivors as if they were
everyone.
"""
from __future__ import annotations

import json

import pytest

from app.agents.deliberation import DeliberationFailed, run_opening, run_round
from app.schemas.deliberation import AgentTurn, AgentVoice, DeliberationBatch, OpeningBatch
from app.services.llm import LLMClient


class Canned:
    """Returns exactly the payload given, so the plumbing is what is under test."""

    name = "canned"

    def __init__(self, payload):
        self.payload = payload

    def complete(self, system, prompt, max_tokens, schema=None):
        return json.dumps(self.payload)


def client(payload) -> LLMClient:
    return LLMClient(Canned(payload), max_attempts=1)


def voice(pid: str) -> dict:
    return {"persona_id": pid, "name": "Tan Wei Ming", "summary": "",
            "turns": [{"round": 0, "position": 0.5, "confidence": 0.5,
                       "reasoning": "Nothing has changed for me yet.",
                       "grounded_in": [f"{pid}:f1"]}]}


def test_an_empty_opening_batch_is_refused():
    with pytest.raises(DeliberationFailed, match="expected 3"):
        run_opening("prompt", client({"voices": []}), expected=3)


def test_a_short_opening_batch_is_refused():
    """Nine residents returned for twelve asked is nine residents, not twelve."""
    payload = {"voices": [voice(f"p_000{i}") for i in range(2)]}
    with pytest.raises(DeliberationFailed, match="returned 2 voices, expected 3"):
        run_opening("prompt", client(payload), expected=3)


def test_a_complete_opening_batch_passes():
    payload = {"voices": [voice(f"p_000{i}") for i in range(3)]}
    batch = run_opening("prompt", client(payload), expected=3)
    assert [v.persona_id for v in batch.voices] == ["p_0000", "p_0001", "p_0002"]


def turn(rnd=1) -> dict:
    return {"round": rnd, "position": 0.4, "confidence": 0.6,
            "reasoning": "I walk further now.", "grounded_in": ["x:f1"]}


def test_a_round_batch_for_the_wrong_residents_is_refused():
    """The failure that used to be silently repaired by overwriting the id.

    Assigning our id over the model's cannot detect a reordered batch, it relabels one --
    and twelve residents' reasoning attached to the wrong twelve people still looks like
    evidence.
    """
    payload = {"turns": [turn(), turn()], "persona_ids": ["p_0002", "p_0001"]}
    with pytest.raises(DeliberationFailed, match="wrong residents, or in the wrong order"):
        run_round("prompt", client(payload), expected_ids=["p_0001", "p_0002"])


def test_a_round_batch_with_a_missing_resident_is_refused():
    payload = {"turns": [turn()], "persona_ids": ["p_0001"]}
    with pytest.raises(DeliberationFailed, match="returned 1 turns, expected 2"):
        run_round("prompt", client(payload), expected_ids=["p_0001", "p_0002"])


def test_a_matching_round_batch_passes():
    payload = {"turns": [turn(), turn()], "persona_ids": ["p_0001", "p_0002"]}
    batch = run_round("prompt", client(payload), expected_ids=["p_0001", "p_0002"])
    assert batch.persona_ids == ["p_0001", "p_0002"]


def test_the_schema_is_offered_to_a_provider_that_can_constrain_decoding():
    """`structured()` must hand the schema down, or the local grammar never engages.

    Without this the Ollama adapter falls back to asking politely, which is the mode that
    returns an empty batch.
    """
    seen = {}

    class Recorder(Canned):
        def complete(self, system, prompt, max_tokens, schema=None):
            seen["schema"] = schema
            return json.dumps(self.payload)

    LLMClient(Recorder({"voices": []}), max_attempts=1).structured(
        OpeningBatch, "sys", "prompt")
    assert seen["schema"]["title"] == "OpeningBatch"
    assert "voices" in seen["schema"]["properties"]


def test_the_grammar_schema_pins_how_many_residents_may_be_returned():
    """Grammar constrains the shape of a value, not how many of them there are.

    An unbounded array is a legal place to keep going, and a small model obligingly does:
    asked for four residents it returned thirty-nine and spent 508 seconds on it. The
    count check caught that, but the cheaper fix is to make the sampler unable to run past
    the end.
    """
    from app.services.llm import exact_items

    schema = exact_items(OpeningBatch, "voices", 6)
    assert schema["properties"]["voices"]["minItems"] == 6
    assert schema["properties"]["voices"]["maxItems"] == 6
    # the Pydantic model itself is untouched: validation still accepts any length, and the
    # explicit count check remains the thing that rejects a wrong one
    assert OpeningBatch(voices=[]).voices == []


def test_the_pinned_schema_is_what_reaches_the_provider():
    seen = {}

    class Recorder(Canned):
        def complete(self, system, prompt, max_tokens, schema=None):
            seen["schema"] = schema
            return json.dumps(self.payload)

    payload = {"voices": [voice(f"p_000{i}") for i in range(3)]}
    run_opening("prompt", LLMClient(Recorder(payload), max_attempts=1), expected=3)
    assert seen["schema"]["properties"]["voices"]["maxItems"] == 3


def test_a_round_batch_pins_its_turn_count_too():
    seen = {}

    class Recorder(Canned):
        def complete(self, system, prompt, max_tokens, schema=None):
            seen["schema"] = schema
            return json.dumps(self.payload)

    payload = {"turns": [turn(), turn()], "persona_ids": ["p_0001", "p_0002"]}
    run_round("prompt", LLMClient(Recorder(payload), max_attempts=1),
              expected_ids=["p_0001", "p_0002"])
    assert seen["schema"]["properties"]["turns"]["maxItems"] == 2


def test_the_grammar_makes_citations_mandatory():
    """A field with a default is optional in the schema, and a sampler reads that as
    permission to omit it.

    Given that permission `deepseek-r1:8b` did something worse than omit it: it wrote the
    fact ids into the prose -- "as per p_0120:f3" -- so the reasoning read as grounded
    while `grounded_in` was empty and every turn was correctly rejected.
    """
    from app.services.llm import exact_items, require_citations

    schema = require_citations(exact_items(OpeningBatch, "voices", 4))
    turn_def = schema["$defs"]["AgentTurn"]
    assert "grounded_in" in turn_def["required"]
    assert turn_def["properties"]["grounded_in"]["minItems"] == 1
    assert "default" not in turn_def["properties"]["grounded_in"]


def test_requiring_citations_leaves_the_python_model_alone():
    """The grammar obliges the model to cite. The guard still judges the citations, and
    an empty list stays constructible so the guard can be tested against one."""
    from app.schemas.deliberation import AgentTurn

    t = AgentTurn(round=1, position=0.5, confidence=0.5, reasoning="x", grounded_in=[])
    assert t.grounded_in == []
