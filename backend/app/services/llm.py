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

import httpx
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


@dataclass
class CompletionResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class Completion(Protocol):
    """Anything that can turn a prompt into text. Kept deliberately tiny.

    `schema` is the JSON Schema the caller will validate against. Most providers ignore it
    -- they are told the shape in the system prompt and asked nicely. A provider that can
    constrain decoding to a grammar uses it instead, which is the difference between a
    small local model returning valid output and returning `{"voices": []}`.
    """

    name: str

    def complete(self, system: str, prompt: str, max_tokens: int,
                 schema: dict | None = None) -> str | CompletionResult: ...


class MockCompletion:
    """Deterministic canned responses, keyed by a marker in the prompt.

    Lets the whole agent layer, its retries and its failure paths be tested with no
    network and no credentials.
    """

    name = "mock"

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, prompt: str, max_tokens: int,
                 schema: dict | None = None) -> str:
        self.calls.append((system, prompt))
        for marker, response in self.responses.items():
            if marker in prompt:
                return response
        # no canned answer: behave like a model that understood nothing concrete, so the
        # caller's own guard rejects it rather than the transport blowing up
        return json.dumps({
            "objective": "", "modifications": {}, "constraints": {}, "reading": [],
        })


class ChatCompletion:
    """An OpenAI-shaped chat API, over the existing HTTP dependency.

    xAI and Groq speak the identical wire format -- same request body, same
    `finish_reason`, same `usage` keys -- so one adapter serves both and only the host
    and the key name differ. They are separate companies with confusingly similar
    names: Grok is xAI's model, Groq is an inference provider running open weights.
    A key for one is rejected by the other, so `key_env` is part of the provider.
    """

    def __init__(self, model_id: str, temperature: float = 0.0, *,
                 base_url: str = "https://api.x.ai/v1/chat/completions",
                 key_env: str = "XAI_API_KEY"):
        self.name = model_id
        self.temperature = temperature
        self.base_url = base_url
        self.key_env = key_env

    def complete(self, system: str, prompt: str, max_tokens: int,
                 schema: dict | None = None) -> CompletionResult:
        api_key = os.getenv(self.key_env, "").strip()
        if not api_key:
            raise LLMError(
                f"No model key: set {self.key_env} in the project root .env "
                "and restart the backend.")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = httpx.post(
                self.base_url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.name,
                    "messages": messages,
                    "temperature": self.temperature,
                    "reasoning_effort": "low",
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Do not echo request headers or arbitrary provider response bodies.
            raise LLMError(
                f"The model API returned HTTP {exc.response.status_code}. "
                f"Check {self.key_env}, access to {self.name}, credits and rate limits."
            ) from None
        except httpx.RequestError:
            raise LLMError("The model API could not be reached or timed out. Please retry.") from None
        try:
            data = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if choice.get("finish_reason") != "stop" or not isinstance(content, str) or not content.strip():
                raise ValueError("incomplete response")
            usage = data.get("usage", {})
            return CompletionResult(content, int(usage.get("prompt_tokens", 0)),
                                    int(usage.get("completion_tokens", 0)))
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise LLMError("The model returned an incomplete or invalid response. Please retry.") from None


class OllamaCompletion:
    """A local model through Ollama's native API, with grammar-constrained decoding.

    Ollama exposes two endpoints. The OpenAI-compatible one takes
    `response_format: {"type": "json_object"}`, which *asks* for JSON; the native one takes
    `format: <json schema>` and constrains generation so the sampled tokens cannot leave
    the schema. On an 8B model that is the whole difference: asked politely for a batch of
    twelve residents it returns `{"voices": []}`, and constrained it returns twelve
    residents.

    Two limits of that grammar, both handled by the caller rather than here:

    - It enforces types and required fields, not numeric ranges. `minimum`/`maximum` ride
      along in the schema but are not compiled into the grammar, so `position: -1` can
      still arrive against a `ge=0` field. The Pydantic model rejects it and `structured()`
      retries. It is never clamped -- a clamped value is a number the resident did not say.
    - A schema-valid but *empty* answer is still empty. `{"voices": []}` satisfies any
      grammar that makes the list optional; the deliberation agent rejects it explicitly.

    No API key: the endpoint is on the loopback interface.
    """

    #: Ollama keeps a model resident for a few minutes; a cold load on an 8 GB card is
    #: slow enough to look like a hang, and a whole run is many minutes of calls.
    TIMEOUT = 900.0

    #: The context window, which Ollama will NOT infer from the model.
    #:
    #: deepseek-r1:8b advertises 131072 tokens; Ollama serves it at 8192 unless told
    #: otherwise, and `num_predict` is drawn from that same window rather than added to
    #: it. A batch of twelve residents fills 8192 with prompt, leaving no room to
    #: generate, so every batch came back truncated and every batch was correctly
    #: rejected -- a whole run of 28 batches producing nothing, with the guards working
    #: perfectly and the cause two layers down. Sized to fit beside 5.2 GB of weights on
    #: an 8 GB card; raise it if the card is bigger.
    #:
    #: 8192 rather than more, and the ceiling is the card, not the model. Raising this to
    #: 16384 grew the resident set to 9.6 GB against 8 GB of VRAM, Ollama offloaded 31% of
    #: the layers to CPU, and throughput fell by roughly an order of magnitude while
    #: looking, from the outside, exactly like a hang. The prompt is made to fit by
    #: shrinking the batch (`DELIBERATION_BATCH_SIZE`), not by growing the window.
    NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

    def __init__(self, model_id: str, temperature: float = 0.0,
                 base_url: str = "http://localhost:11434/api/chat"):
        self.name = model_id
        self.temperature = temperature
        self.base_url = base_url

    def complete(self, system: str, prompt: str, max_tokens: int,
                 schema: dict | None = None) -> CompletionResult:
        body: dict[str, Any] = {
            "model": self.name,
            "messages": (
                ([{"role": "system", "content": system}] if system else [])
                + [{"role": "user", "content": prompt}]
            ),
            "options": {
                "temperature": self.temperature,
                "num_predict": max_tokens,
                "num_ctx": self.NUM_CTX,
            },
            # DeepSeek-R1 emits a <think> block that is not JSON and breaks parsing.
            # Ollama strips it into its own field when thinking is switched off.
            "think": False,
            "stream": False,
        }
        if schema:
            body["format"] = schema

        try:
            response = httpx.post(self.base_url, json=body, timeout=self.TIMEOUT)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Ollama returned HTTP {exc.response.status_code}. Is `ollama serve` "
                f"running, and has `{self.name}` been pulled?"
            ) from None
        except httpx.RequestError:
            raise LLMError(
                f"Ollama at {self.base_url} could not be reached. Start it with "
                "`ollama serve`."
            ) from None

        try:
            data = response.json()
            content = data["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty content")
            # Ollama reports counts, not billing. Recorded so a local run still shows what
            # it cost in tokens and time.
            return CompletionResult(content,
                                    int(data.get("prompt_eval_count", 0)),
                                    int(data.get("eval_count", 0)))
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise LLMError("Ollama returned an incomplete response. Please retry.") from None


class BedrockCompletion:
    """Claude via Amazon Bedrock. Imported lazily so boto3 is optional for tests."""

    def __init__(self, model_id: str, region: str, temperature: float = 0.0):
        self.name = model_id
        self.model_id = model_id
        self.region = region
        #: Deliberation needs variety. At temperature 0 two thousand residents reason in
        #: one voice, which reads as a template and defeats the point of asking them.
        #: Interpretation still wants 0: there is one right reading of a policy.
        self.temperature = temperature
        self._client: Any = None

    def _bedrock(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover - depends on the environment
                raise LLMError("boto3 is not installed; pip install -r requirements.txt") from exc
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def complete(self, system: str, prompt: str, max_tokens: int,
                 schema: dict | None = None) -> str:
        try:
            res = self._bedrock().converse(
                modelId=self.model_id,
                system=[{"text": system}] if system else [],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": max_tokens,
                                 "temperature": self.temperature},
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

    @property
    def provider_name(self) -> str:
        """Which adapter is behind this client. Callers branch on it to decide whether a
        result is a real model output, and the UI says which it was."""
        return self.completion.name

    def structured(self, schema: type[T], system: str, prompt: str,
                   max_tokens: int = 1024) -> T:
        json_schema = schema.model_json_schema()
        system = f"{system}\n\nReturn JSON matching this schema:\n{json.dumps(json_schema)}"
        last: LLMOutputInvalid | None = None
        started = time.monotonic()
        input_tokens = output_tokens = 0

        for attempt in range(1, self.max_attempts + 1):
            try:
                result = self.completion.complete(system, prompt, max_tokens, json_schema)
            except LLMError:
                TELEMETRY.record(Usage(model=self.completion.name,
                                       ms=int((time.monotonic() - started) * 1000),
                                       input_tokens=input_tokens, output_tokens=output_tokens,
                                       attempts=attempt))
                raise
            if isinstance(result, CompletionResult):
                input_tokens += result.input_tokens
                output_tokens += result.output_tokens
                raw = result.text
            else:
                raw = result
            try:
                parsed = schema.model_validate_json(_strip_fence(raw))
            except (ValidationError, ValueError) as exc:
                last = LLMOutputInvalid(raw, str(exc))
                continue

            TELEMETRY.record(Usage(
                model=self.completion.name,
                ms=int((time.monotonic() - started) * 1000),
                attempts=attempt,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ))
            return parsed

        assert last is not None
        TELEMETRY.record(Usage(model=self.completion.name,
                               ms=int((time.monotonic() - started) * 1000),
                               input_tokens=input_tokens, output_tokens=output_tokens,
                               attempts=self.max_attempts))
        raise last


def build_client(temperature: float = 0.0, role: str = "interpreter") -> LLMClient:
    """Provider comes from the environment. Default is the mock, so nothing needs AWS.

    Two roles, because they are different jobs with different economics, which
    `AGENTS.md` §11 already rules on: run the per-resident deliberation on the cheap model,
    "reserve the strong model for the few calls that need it: interpreting a policy, and
    writing the explanation a human reads."

    That distinction became load-bearing the moment the deliberation moved to a local 8B
    model. Interpretation is one call per run against a wide schema with real stakes -- get
    it wrong and every downstream number answers a question nobody asked -- while
    deliberation is hundreds of calls against a narrow schema where cost dominates. Pointing
    both at the same small local model made policy interpretation the slowest step in the
    system and the least reliable.

    `LLM_PROVIDER_INTERPRETER` overrides the provider for interpretation only. Unset, both
    roles use `LLM_PROVIDER`.

    The mock can drive the API and the interpreter. It cannot drive a deliberation:
    `deliberate()` refuses it outright rather than emitting text that reads like a
    resident and is not one.
    """
    # `.env` files carry empty assignments to document a knob that is not in use, and
    # os.getenv only falls back when a name is absent -- not when it is set to "". Reading
    # the default on empty is what makes `LLM_PROVIDER_INTERPRETER=` mean "unset".
    default = os.getenv("LLM_PROVIDER", "").strip() or "mock"
    override = os.getenv("LLM_PROVIDER_INTERPRETER", "").strip()
    provider = (override if (role == "interpreter" and override) else default).lower()
    if provider in {"grok", "xai"}:
        return LLMClient(ChatCompletion(
            model_id=os.getenv("GROK_MODEL_ID", "grok-4.3"),
            temperature=temperature,
        ))
    if provider == "groq":
        return LLMClient(ChatCompletion(
            model_id=os.getenv("GROQ_MODEL_ID", "openai/gpt-oss-120b"),
            temperature=temperature,
            base_url="https://api.groq.com/openai/v1/chat/completions",
            key_env="GROQ_API_KEY",
        ))
    if provider in {"ollama", "local", "deepseek-local"}:
        return LLMClient(OllamaCompletion(
            model_id=os.getenv("OLLAMA_MODEL_ID", "deepseek-r1:8b"),
            temperature=temperature,
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat"),
        ))
    if provider == "deepseek":
        # Hosted DeepSeek speaks the OpenAI shape. It has no grammar mode -- only
        # `response_format: json_object` -- so it relies on validate-and-retry, and its own
        # docs warn it "may occasionally return empty content".
        return LLMClient(ChatCompletion(
            model_id=os.getenv("DEEPSEEK_MODEL_ID", "deepseek-v4-flash"),
            temperature=temperature,
            base_url="https://api.deepseek.com/chat/completions",
            key_env="DEEPSEEK_API_KEY",
        ))
    if provider == "bedrock":
        return LLMClient(BedrockCompletion(
            model_id=os.getenv("BEDROCK_MODEL_ID_FAST",
                               "anthropic.claude-haiku-4-5-20251001-v1:0"),
            region=os.getenv("AWS_REGION", "ap-southeast-1"),
            temperature=temperature,
        ))
    if provider == "mock":
        return LLMClient(MockCompletion(_DEFAULT_MOCKS))
    raise LLMError(
        f"Unknown LLM_PROVIDER {provider!r}. Use ollama, deepseek, groq, grok, bedrock, "
        "or mock (tests only).")


def build_deliberation_client() -> LLMClient:
    """The client the population reasons with. Warmer, cheaper, and never the mock."""
    return build_client(
        temperature=float(os.getenv("DELIBERATION_TEMPERATURE", "0.8")),
        role="deliberation",
    )


# The interpreter's canned answer, so the API is demoable end to end with no credentials.
_DEFAULT_MOCKS = {
    "Ang Mo Kio": json.dumps({
        "objective": "reduce journey time and operating cost",
        "modifications": {
            # real Ang Mo Kio Ave 3 stop codes, so the canned answer resolves to a real
            # study area. Synthetic codes made every demo request refuse.
            "remove_stops": ["54231", "54239"],
            "add_express_segment": {"from_stop": "54009", "to_stop": "54241"},
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
