"""Policy Interpreter: natural language in, validated PolicyChange out.

architecture.md 8.1. The LLM earns its place here because this is language
interpretation. It does not compute anything: no distances, no thresholds, no metrics.

On failure this raises. The API turns that into a 422 telling the planner to correct the
text or use the structured form, which is the visible-failure path AGENTS.md 18 requires.
"""
from __future__ import annotations

from app.schemas.policy import PolicyChange
from app.services.llm import LLMClient, LLMOutputInvalid

SYSTEM = """You convert a transport policy proposal into a structured PolicyChange.

Rules:
- Only use stop ids and service ids that appear in the proposal or the provided network.
- If a phrase could match more than one stop, do not guess: leave the field empty and say
  so in the reading.
- Anything you filled in that the author did not state must be marked assumed: true.
- Never invent a constraint the author did not express.

Respond with a single JSON object matching the PolicyChange schema. No prose, no fences."""


class PolicyInterpretationFailed(RuntimeError):
    def __init__(self, detail: str, raw: str | None = None):
        super().__init__(detail)
        self.detail = detail
        self.raw = raw


def interpret(text: str, llm: LLMClient) -> PolicyChange:
    prompt = f"PROPOSAL:\n{text.strip()}\n\nReturn the PolicyChange JSON."
    try:
        change = llm.structured(PolicyChange, SYSTEM, prompt, max_tokens=1200)
    except LLMOutputInvalid as exc:
        raise PolicyInterpretationFailed(
            "The interpreter did not return a valid PolicyChange.", exc.raw) from exc

    # a schema-valid but empty change would simulate nothing, so refuse it here
    m = change.modifications
    if not m.remove_stops and m.add_express_segment is None and m.frequency_delta_pct == 0:
        raise PolicyInterpretationFailed(
            "No concrete change was found in that proposal. Name the stops or the service.")
    return change
