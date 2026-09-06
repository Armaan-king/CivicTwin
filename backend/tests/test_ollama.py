"""The local adapter's failure paths, none of which had a test.

Every one of these presents as a hang or an empty page to a user, so the error has to say
what to do about it.
"""
from __future__ import annotations

import httpx
import pytest

from app.services.llm import LLMClient, LLMError, OllamaCompletion
from pydantic import BaseModel


class Shape(BaseModel):
    value: int


def reply(content='{"value": 7}', **extra):
    body = {"message": {"content": content}, "prompt_eval_count": 20, "eval_count": 5}
    body.update(extra)
    return body


def test_the_schema_is_sent_as_a_grammar_not_a_suggestion(monkeypatch):
    """The whole reason this adapter uses the native endpoint."""
    seen = {}

    def post(url, **kw):
        seen["url"] = url
        seen["body"] = kw["json"]
        return httpx.Response(200, json=reply(), request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    LLMClient(OllamaCompletion("deepseek-r1:8b")).structured(Shape, "sys", "go")
    assert seen["url"].endswith("/api/chat"), "the OpenAI-compatible endpoint has no grammar"
    assert seen["body"]["format"]["title"] == "Shape"
    assert seen["body"]["think"] is False, "R1 emits <think> blocks that are not JSON"


def test_the_context_window_is_set_explicitly(monkeypatch):
    """Ollama serves 8192 regardless of what the model advertises, and num_predict comes
    out of that same window rather than adding to it."""
    seen = {}
    monkeypatch.setattr(httpx, "post", lambda url, **kw: (
        seen.update(kw["json"]),
        httpx.Response(200, json=reply(), request=httpx.Request("POST", url)))[1])
    LLMClient(OllamaCompletion("m")).structured(Shape, "", "go", max_tokens=500)
    assert seen["options"]["num_ctx"] == 8192
    assert seen["options"]["num_predict"] == 500


def test_an_unreachable_server_says_how_to_start_it(monkeypatch):
    def boom(url, **kw):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(LLMError, match="ollama serve"):
        OllamaCompletion("m").complete("", "go", 10)


def test_a_missing_model_says_to_pull_it(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(
        404, text="model not found", request=httpx.Request("POST", url)))
    with pytest.raises(LLMError, match="pulled"):
        OllamaCompletion("deepseek-r1:8b").complete("", "go", 10)


@pytest.mark.parametrize("body", [reply(content=""), reply(content=None), {}])
def test_an_empty_answer_is_an_error_not_a_result(monkeypatch, body):
    """An empty completion that is treated as output silently shrinks the population."""
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(
        200, json=body, request=httpx.Request("POST", url)))
    with pytest.raises(LLMError, match="incomplete"):
        OllamaCompletion("m").complete("", "go", 10)


def test_local_token_counts_are_recorded(monkeypatch):
    """A local run costs no money and still has to report what it cost (AGENTS.md 19)."""
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(
        200, json=reply(), request=httpx.Request("POST", url)))
    result = OllamaCompletion("m").complete("", "go", 10)
    assert (result.input_tokens, result.output_tokens) == (20, 5)


def test_no_api_key_is_required(monkeypatch):
    """The endpoint is on loopback; demanding a key would be theatre."""
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(
        200, json=reply(), request=httpx.Request("POST", url)))
    assert OllamaCompletion("m").complete("", "go", 10).text == '{"value": 7}'
