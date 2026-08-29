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
