"""The LLM boundary must fail visibly and never need live AWS."""
import json
import pytest
from pydantic import BaseModel

from app.agents.policy_interpreter import PolicyInterpretationFailed, interpret
from app.services.llm import LLMClient, LLMOutputInvalid, MockCompletion


class Shape(BaseModel):
    value: int


def test_structured_output_is_validated():
    llm = LLMClient(MockCompletion({"go": '{"value": 7}'}))
    assert llm.structured(Shape, "", "go").value == 7


def test_fenced_json_is_accepted():
    llm = LLMClient(MockCompletion({"go": '```json\n{"value": 3}\n```'}))
    assert llm.structured(Shape, "", "go").value == 3


def test_malformed_output_raises_rather_than_guessing():
    llm = LLMClient(MockCompletion({"go": "sorry, I could not do that"}), max_attempts=2)
    with pytest.raises(LLMOutputInvalid):
        llm.structured(Shape, "", "go")


def test_retries_then_gives_up():
    mock = MockCompletion({"go": "not json"})
    llm = LLMClient(mock, max_attempts=3)
    with pytest.raises(LLMOutputInvalid):
        llm.structured(Shape, "", "go")
    assert len(mock.calls) == 3


def test_interpreter_refuses_a_change_that_would_simulate_nothing():
    empty = json.dumps({"objective": "", "modifications": {}, "constraints": {}, "reading": []})
    llm = LLMClient(MockCompletion({"vague": empty}))
    with pytest.raises(PolicyInterpretationFailed):
        interpret("vague proposal with no stops named", llm)


def test_interpreter_returns_a_typed_change():
    llm = LLMClient(MockCompletion({"Ang Mo Kio": json.dumps({
        "objective": "cut journey time",
        "modifications": {"remove_stops": ["55079"], "frequency_delta_pct": 0},
        "constraints": {"fleet_increase_allowed": False, "operating_budget_delta_pct": 0},
        "reading": [{"n": "01", "claim": "c", "why": "w", "assumed": False}],
    })}))
    change = interpret("Remove a stop on Ang Mo Kio Avenue 3", llm)
    assert change.modifications.remove_stops == ["55079"]


# ---------------------------------------------------------------- replay
def test_a_repeated_call_is_served_from_disk_without_the_model():
    """The demo's whole basis: a run replays for free.

    The deliberation had this from the start; interpretation did not, so a demo could read
    hundreds of residents off disk in seconds and then sit for fifteen minutes on the one
    call that reads the policy. AGENTS.md 22 permits replaying a cached run precisely
    because it is a real run shown again.
    """
    from app.services.llm import LLMClient

    class CountingStub:
        name = "counting"

        def __init__(self):
            self.calls = 0

        def complete(self, system, prompt, max_tokens, schema=None):
            self.calls += 1
            return '{"value": 42}'

    stub = CountingStub()
    client = LLMClient(stub)
    assert client.structured(Shape, "sys", "go").value == 42
    assert stub.calls == 1
    assert client.structured(Shape, "sys", "go").value == 42
    assert stub.calls == 1, "the second call reached the model instead of the cache"


def test_a_different_prompt_is_not_served_the_cached_answer():
    from app.services.llm import LLMClient

    class Echo:
        name = "echo"

        def __init__(self):
            self.seen = []

        def complete(self, system, prompt, max_tokens, schema=None):
            self.seen.append(prompt)
            return '{"value": %d}' % len(self.seen)

    stub = Echo()
    client = LLMClient(stub)
    assert client.structured(Shape, "sys", "first").value == 1
    assert client.structured(Shape, "sys", "second").value == 2
    assert len(stub.seen) == 2


def test_caching_can_be_switched_off():
    """Tests of the transport must exercise the transport."""
    from app.services.llm import LLMClient

    class CountingStub:
        name = "nocache"

        def __init__(self):
            self.calls = 0

        def complete(self, system, prompt, max_tokens, schema=None):
            self.calls += 1
            return '{"value": 1}'

    stub = CountingStub()
    client = LLMClient(stub, cache=False)
    client.structured(Shape, "sys", "go")
    client.structured(Shape, "sys", "go")
    assert stub.calls == 2
