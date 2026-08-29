"""The single boundary between CivicTwin and any language model.

architecture.md section 15: no raw Bedrock call may appear in business logic. Everything
goes through `LLMClient.structured()`, which returns a validated Pydantic model or raises.
That gives us four things the docs require:

  - mocking in tests, so the suite never needs live AWS (AGENTS.md section 20)
  - one place to swap models or providers
  - one place to record tokens and latency (AGENTS.md section 19)
  - schema validation on every output, so prose can never drive logic (AGENTS.md section 7)

Failure is visible. A model that returns unparseable output raises `LLMOutputInvalid`
rather than degrading into something that looks like an answer (AGENTS.md section 18).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """The call itself failed: transport, auth, throttling."""


class LLMOutputInvalid(LLMError):
    """The model answered, but not in the shape the caller requires."""

    def __init__(self, raw: str, detail: str):
        super().__init__(f"model output failed validation: {detail}")
        self.raw = raw
        self.detail = detail


@dataclass
class Usage:
    """Per-call record. Aggregated for the evaluation metrics in evaluation.md section 3."""
    model: str
    ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    attempts: int = 1


@dataclass
class Telemetry:
    calls: list[Usage] = field(default_factory=list)

    def record(self, u: Usage) -> None:
        self.calls.append(u)

    @property
    def total_tokens(self) -> int:
        return sum(c.input_tokens + c.output_tokens for c in self.calls)


TELEMETRY = Telemetry()


class Completion(Protocol):
    """Anything that can turn a prompt into text. Kept deliberately tiny."""

    name: str

    def complete(self, system: str, prompt: str, max_tokens: int) -> str: ...


class MockCompletion:
    """Deterministic canned responses, keyed by a marker in the prompt.

    Lets the whole agent layer, its retries and its failure paths be tested with no
    network and no credentials.
    """

    name = "mock"

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        self.calls.append((system, prompt))
        for marker, response in self.responses.items():
            if marker in prompt:
                return response
        # no canned answer: behave like a model that understood nothing concrete, so the
        # caller's own guard rejects it rather than the transport blowing up
        return json.dumps({
            "objective": "", "modifications": {}, "constraints": {}, "reading": [],
        })


class BedrockCompletion:
    """Claude via Amazon Bedrock. Imported lazily so boto3 is optional for tests."""

    def __init__(self, model_id: str, region: str):
        self.name = model_id
        self.model_id = model_id
        self.region = region
        self._client: Any = None

    def _bedrock(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover - depends on the environment
                raise LLMError("boto3 is not installed; pip install -r requirements.txt") from exc
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def complete(self, system: str, prompt: str, max_tokens: int) -> str:
        try:
            res = self._bedrock().converse(
                modelId=self.model_id,
                system=[{"text": system}] if system else [],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0},
            )
        except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
            raise LLMError(f"Bedrock call failed: {exc}") from exc
        return res["output"]["message"]["content"][0]["text"]


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


class LLMClient:
    """Structured output or an exception. Never a plausible-looking fallback."""

    def __init__(self, completion: Completion, max_attempts: int = 2):
        self.completion = completion
        self.max_attempts = max_attempts

    def structured(self, schema: type[T], system: str, prompt: str,
                   max_tokens: int = 1024) -> T:
        last: LLMOutputInvalid | None = None
        started = time.monotonic()

        for attempt in range(1, self.max_attempts + 1):
            raw = self.completion.complete(system, prompt, max_tokens)
            try:
                parsed = schema.model_validate_json(_strip_fence(raw))
            except (ValidationError, ValueError) as exc:
                last = LLMOutputInvalid(raw, str(exc))
                continue

            TELEMETRY.record(Usage(
                model=self.completion.name,
                ms=int((time.monotonic() - started) * 1000),
                attempts=attempt,
            ))
            return parsed

        assert last is not None
        TELEMETRY.record(Usage(model=self.completion.name,
                               ms=int((time.monotonic() - started) * 1000),
                               attempts=self.max_attempts))
        raise last


def build_client() -> LLMClient:
    """Provider comes from the environment. Default is the mock, so nothing needs AWS."""
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "bedrock":
        return LLMClient(BedrockCompletion(
            model_id=os.getenv("BEDROCK_MODEL_ID_FAST",
                               "anthropic.claude-haiku-4-5-20251001-v1:0"),
            region=os.getenv("AWS_REGION", "ap-southeast-1"),
        ))
    return LLMClient(MockCompletion(_DEFAULT_MOCKS))


# The interpreter's canned answer, so the API is demoable end to end with no credentials.
_DEFAULT_MOCKS = {
    "Ang Mo Kio": json.dumps({
        "objective": "reduce journey time and operating cost",
        "modifications": {
            "remove_stops": ["55079", "55081"],
            "add_express_segment": {"from_stop": "55009", "to_stop": "55101"},
            "frequency_delta_pct": 0,
        },
        "constraints": {"fleet_increase_allowed": False, "operating_budget_delta_pct": 0},
        "reading": [
            {"n": "01", "claim": "You want to cut journey time and running cost.",
             "why": "Read from 'run non-stop' and 'no extra buses'.", "assumed": False},
            {"n": "02", "claim": "Two stops come out of service 265.",
             "why": "Matched exactly two stops on that road served by 265.", "assumed": False},
            {"n": "03", "claim": "The fleet cannot grow.",
             "why": "'No extra buses' is a hard constraint, not a preference.", "assumed": False},
            {"n": "04", "claim": "One thing was assumed.",
             "why": "You did not say when the express segment runs. It assumed all day.",
             "assumed": True},
        ],
    }),
}
